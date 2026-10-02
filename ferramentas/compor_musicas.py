import json
import os
import random
import re
import subprocess
import sys
import tempfile
import zlib
from concurrent.futures import ThreadPoolExecutor

import mido
import numpy as np

# ============================================================
# COMPOSITOR DE MÚSICAS E EFEITOS DO OVAL
# ============================================================
# Cada faixa é composta em código (ver ferramentas/partituras.py)
# como MIDI, renderizada com FluidSynth + SoundFont General MIDI
# e exportada em MP3 com volume normalizado.
#
#   python ferramentas/compor_musicas.py            -> tudo
#   python ferramentas/compor_musicas.py casa jogos -> só estas
#   python ferramentas/compor_musicas.py --sfx      -> só os efeitos
#   python ferramentas/compor_musicas.py --midi     -> só os .mid
#
# Saída:
#   musicas/trilhas/<id>.mp3      músicas (loop perfeito)
#   musicas/sfx/<nome>.mp3        efeitos sonoros
#   musicas/midi/...              os .mid (abrem no FL Studio)
#
# Notação das melodias (um "passo" = 1/16 de compasso):
#   "C5"     Dó 5 durando 1 passo        "E5*3"  Mi 5 durando 3 passos
#   "."      pausa de 1 passo            ".*4"   pausa de 4 passos
#   "-*2"    estende a nota anterior     "C4+E4+G4*8"  acorde
#   "|"      separa compassos (cada compasso precisa somar 16)

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

_FERRAMENTAS = os.path.join(os.path.dirname(RAIZ), "ferramentas_musica")
FLUIDSYNTH = os.environ.get("OVAL_FLUIDSYNTH", os.path.join(
    _FERRAMENTAS, "fluidsynth", "fluidsynth-v2.6.1-win10-x64-cpp11", "bin", "fluidsynth.exe"))
SOUNDFONT = os.environ.get("OVAL_SOUNDFONT", os.path.join(_FERRAMENTAS, "GeneralUser-GS.sf2"))

PASTA_TRILHAS = os.path.join(RAIZ, "musicas", "trilhas")
PASTA_SFX = os.path.join(RAIZ, "musicas", "sfx")
PASTA_MIDI = os.path.join(RAIZ, "musicas", "midi")

TAXA = 44100
TPQ = 480                   # ticks por semínima
PASSO = TPQ // 4            # 1/16 de compasso
CANAL_BATERIA = 9


# ============================================================
# NOTAS E ACORDES
# ============================================================

_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
_NOMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]


def _classe_e_resto(nome):
    pc = _PC[nome[0].upper()]
    resto = nome[1:]
    while resto and resto[0] in "#b":
        pc += 1 if resto[0] == "#" else -1
        resto = resto[1:]
    return pc, resto


def altura(nome):
    """'C#5' -> número MIDI (73)."""
    pc, resto = _classe_e_resto(nome)
    return 12 * (int(resto) + 1) + pc


def classe(nome):
    return _classe_e_resto(nome)[0] % 12


def nome_nota(midi):
    return f"{_NOMES[midi % 12]}{midi // 12 - 1}"


QUALIDADES = {
    "": [0, 4, 7], "m": [0, 3, 7], "5": [0, 7],
    "7": [0, 4, 7, 10], "m7": [0, 3, 7, 10], "maj7": [0, 4, 7, 11],
    "6": [0, 4, 7, 9], "m6": [0, 3, 7, 9], "add9": [0, 4, 7, 14], "madd9": [0, 3, 7, 14],
    "9": [0, 4, 7, 10, 14], "m9": [0, 3, 7, 10, 14], "maj9": [0, 4, 7, 11, 14],
    "sus4": [0, 5, 7], "sus2": [0, 2, 7], "7sus4": [0, 5, 7, 10],
    "dim": [0, 3, 6], "dim7": [0, 3, 6, 9], "m7b5": [0, 3, 6, 10], "aug": [0, 4, 8],
    "7b9": [0, 4, 7, 10, 13], "mmaj7": [0, 3, 7, 11], "13": [0, 4, 10, 14, 21],
}
_RE_ACORDE = re.compile(r"^([A-G][#b]?)([^/]*)(?:/([A-G][#b]?))?$")


class Acorde:

    def __init__(self, nome):
        m = _RE_ACORDE.match(nome)
        if not m or m[2] not in QUALIDADES:
            raise ValueError(f"acorde desconhecido: {nome}")
        self.nome = nome
        self.raiz = classe(m[1])
        self.intervalos = QUALIDADES[m[2]]
        self.baixo = classe(m[3]) if m[3] else self.raiz

    def classes(self):
        return [(self.raiz + i) % 12 for i in self.intervalos]

    def guias(self):
        """Terça e sétima (ou terça e quinta)."""
        iv = self.intervalos
        out = [i for i in iv if i in (3, 4, 10, 11, 5, 2, 9)]
        if not out:
            out = iv
        return [(self.raiz + i) % 12 for i in out]


def mais_proxima(pc, alvo, lo=0, hi=127):
    """Altura com classe pc mais perto do alvo, dentro de [lo, hi]."""
    melhor = None
    for oit in range(11):
        n = pc + 12 * oit
        if lo <= n <= hi and (melhor is None or abs(n - alvo) < abs(melhor - alvo)):
            melhor = n
    return melhor if melhor is not None else pc + 12 * 4


def voicing(acorde, centro=60, anterior=None, max_notas=4):
    """Acorde fechado perto do centro, com condução de vozes."""
    pcs = acorde.classes()
    if len(pcs) > max_notas:
        # tira a quinta primeiro (ela é a menos importante)
        quinta = (acorde.raiz + 7) % 12
        if quinta in pcs:
            pcs.remove(quinta)
        pcs = pcs[:max_notas]
    candidatos = []
    for rot in range(len(pcs)):
        ordem = pcs[rot:] + pcs[:rot]
        for base in (centro - 7, centro - 2, centro + 3):
            n0 = mais_proxima(ordem[0], base)
            notas = [n0]
            for pc in ordem[1:]:
                n = notas[-1] + 1
                while n % 12 != pc:
                    n += 1
                notas.append(n)
            candidatos.append(notas)

    def custo(v):
        media = sum(v) / len(v)
        c = abs(media - centro) * 0.6 + (v[-1] - v[0]) * 0.15
        if anterior:
            c += sum(abs(a - b) for a, b in zip(sorted(v), sorted(anterior))) * 0.5
        return c

    return min(candidatos, key=custo)


ESCALAS = {
    "maior": [0, 2, 4, 5, 7, 9, 11],
    "menor": [0, 2, 3, 5, 7, 8, 10],
    "dorica": [0, 2, 3, 5, 7, 9, 10],
    "mixolidia": [0, 2, 4, 5, 7, 9, 10],
    "lidia": [0, 2, 4, 6, 7, 9, 11],
    "harmonica": [0, 2, 3, 5, 7, 8, 11],
    "frigia": [0, 1, 3, 5, 7, 8, 10],
}


def grau(tonica, modo, g):
    """Altura MIDI do grau g (0 = tônica; aceita negativos/oitavas)."""
    esc = ESCALAS[modo]
    return altura(tonica) + esc[g % 7] + 12 * (g // 7)


# ------------------------------------------------------------
# TEMA DO OVAL (leitmotif)
# ------------------------------------------------------------
# 5 - 1 - 3 - 2 - 1 - 5'  |  6 - 5 - 3 - 2
# Sobe em "arco" como a casca de um ovo, gira e salta para a
# quinta; a resposta desce e fica suspensa no 2º grau.

MOTIVO = [(-3, 2), (0, 2), (2, 3), (1, 1), (0, 2), (4, 6)]
RESPOSTA = [(5, 2), (4, 2), (2, 4), (1, 8)]
FECHO = [(4, 6), (3, 2), (1, 8)]


def motivo(tonica, modo, partes=("m", "r"), escala_tempo=1, transp=0):
    """Tema do Oval na tonalidade pedida, em notação de passos."""
    blocos = {"m": MOTIVO, "r": RESPOSTA, "f": FECHO}
    toks = []
    for parte in partes:
        for g, d in blocos[parte]:
            toks.append(f"{nome_nota(grau(tonica, modo, g) + transp)}*{d * escala_tempo}")
        toks.append("|")
    return " ".join(toks[:-1])


# ============================================================
# LEITURA DAS SEQUÊNCIAS
# ============================================================

def ler_seq(seq, onde="?"):
    """
    Converte a notação em eventos [(passo, duração, [alturas])].
    Confere se cada compasso (separado por '|') soma 16 passos.
    """
    eventos = []
    pos = 0
    inicio_compasso = 0
    n_compasso = 1
    for tok in seq.split():
        if tok == "|":
            if pos - inicio_compasso != 16:
                raise ValueError(f"{onde}: compasso {n_compasso} com {pos - inicio_compasso} passos")
            inicio_compasso = pos
            n_compasso += 1
            continue
        nome, _, d = tok.partition("*")
        dur = int(d) if d else 1
        if nome == ".":
            pass
        elif nome == "-":
            if eventos:
                p, dd, alts = eventos[-1]
                eventos[-1] = (p, dd + dur, alts)
        else:
            eventos.append((pos, dur, [altura(n) for n in nome.split("+")]))
        pos += dur
    if "|" in seq and pos - inicio_compasso != 16:
        raise ValueError(f"{onde}: compasso {n_compasso} com {pos - inicio_compasso} passos")
    return eventos, pos


def compassos(seq):
    return [c.strip() for c in seq.split("|")]


def juntar(*partes):
    return " | ".join(p.strip(" |") for p in partes if p)


def ler_progressao(prog, passo_inicio, onde="?"):
    """'C | Am F | G*12 G7*4' -> [(passo, duração, Acorde)]."""
    segs = []
    passo = passo_inicio
    for barra in compassos(prog):
        toks = barra.split()
        explicitos = sum(int(t.partition("*")[2]) for t in toks if "*" in t)
        livres = [t for t in toks if "*" not in t]
        resto = 16 - explicitos
        if (livres and resto % len(livres)) or (not livres and resto) or resto < 0:
            raise ValueError(f"{onde}: compasso '{barra}' não soma 16")
        for t in toks:
            nome, _, d = t.partition("*")
            dur = int(d) if d else resto // len(livres)
            segs.append((passo, dur, Acorde(nome)))
            passo += dur
    return segs


def acorde_em(segs, passo):
    for s, d, a in segs:
        if s <= passo < s + d:
            return a
    return segs[-1][2]


# ============================================================
# PARTITURA (eventos MIDI)
# ============================================================

class Partitura:

    def __init__(self, nome, bpm, swing=0.0):
        self.nome = nome
        self.bpm = bpm
        self.swing = swing
        self.canais = {}            # papel -> config
        self.notas = []             # (tick, dur, canal, nota, vel)
        self.extras = []            # (tick, canal, mensagem)
        self.fim = 0                # ticks
        self.rnd = random.Random(zlib.crc32(nome.encode()))

    # --------------------------------------------------------

    def instrumento(self, papel, programa, vol=100, pan=64, rev=40, cho=0, art=0.92,
                    humano=4, canal=None, bend=2):
        if canal is None:
            usados = {c["canal"] for c in self.canais.values()}
            if papel == "bat":
                canal = CANAL_BATERIA
            else:
                canal = next(c for c in range(16) if c != CANAL_BATERIA and c not in usados)
        self.canais[papel] = dict(canal=canal, programa=programa, vol=vol, pan=pan, rev=rev,
                                  cho=cho, art=art, humano=humano, bend=bend)

    def tem(self, papel):
        return papel in self.canais

    def _tick(self, passo, papel):
        t = int(round(passo * PASSO))
        if self.swing and abs(passo - round(passo)) < 1e-6 and int(round(passo)) % 4 == 2:
            t += int(self.swing * 2 * PASSO)
        h = self.canais[papel]["humano"]
        if h:
            t += self.rnd.randint(-h, h)
        return max(0, t)

    def nota(self, papel, passo, dur, alt, vel, art=None):
        cfg = self.canais[papel]
        art = cfg["art"] if art is None else art
        t = self._tick(passo, papel)
        d = max(30, int(dur * PASSO * art))
        vel = max(1, min(127, int(vel + self.rnd.randint(-5, 5))))
        self.notas.append((t, d, cfg["canal"], int(alt), vel))

    def nota_t(self, papel, seg, dur_seg, alt, vel):
        """Nota em segundos (para os efeitos sonoros)."""
        cfg = self.canais[papel]
        t = int(seg * self.bpm / 60 * TPQ)
        d = max(10, int(dur_seg * self.bpm / 60 * TPQ))
        self.notas.append((t, d, cfg["canal"], int(alt), max(1, min(127, int(vel)))))
        self.fim = max(self.fim, t + d)

    def bend_t(self, papel, seg, valor):
        """Pitch bend (-8192..8191) em segundos."""
        cfg = self.canais[papel]
        t = int(seg * self.bpm / 60 * TPQ)
        self.extras.append((t, cfg["canal"], mido.Message(
            "pitchwheel", channel=cfg["canal"], pitch=max(-8192, min(8191, int(valor))))))

    def tocar(self, papel, seq, passo_inicio, vel=92, transp=0, art=None, acento=True,
              onde=None):
        eventos, total = ler_seq(seq, onde or f"{self.nome}/{papel}")
        for p, d, alts in eventos:
            v = vel
            if acento:
                pos = (passo_inicio + p) % 16
                v += 8 if pos == 0 else 4 if pos % 4 == 0 else -3 if pos % 2 else 0
            for a in alts:
                self.nota(papel, passo_inicio + p, d, a + transp, v, art)
        return total

    # --------------------------------------------------------
    # MIDI
    # --------------------------------------------------------

    def midi(self, repeticoes=1, cauda_seg=0.0):
        mid = mido.MidiFile(type=1, ticks_per_beat=TPQ)
        meta = mido.MidiTrack()
        meta.append(mido.MetaMessage("track_name", name=self.nome, time=0))
        meta.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(self.bpm), time=0))
        meta.append(mido.MetaMessage("time_signature", numerator=4, denominator=4, time=0))
        mid.tracks.append(meta)

        fim_total = self.fim * repeticoes + int(cauda_seg * self.bpm / 60 * TPQ)

        for papel, cfg in sorted(self.canais.items(), key=lambda kv: kv[1]["canal"]):
            c = cfg["canal"]
            ev = []
            for r in range(repeticoes):
                base = r * self.fim
                for t, d, canal, n, v in self.notas:
                    if canal != c:
                        continue
                    ev.append((base + t, 1, mido.Message("note_on", channel=c, note=n, velocity=v)))
                    ev.append((base + t + d, 0, mido.Message("note_off", channel=c, note=n, velocity=0)))
                for t, canal, msg in self.extras:
                    if canal == c:
                        ev.append((base + t, 1, msg))
            ev.sort(key=lambda e: (e[0], e[1]))

            tr = mido.MidiTrack()
            tr.append(mido.MetaMessage("track_name", name=papel, time=0))
            if c == CANAL_BATERIA:
                tr.append(mido.Message("control_change", channel=c, control=0, value=120, time=0))
            tr.append(mido.Message("program_change", channel=c, program=cfg["programa"], time=0))
            for cc, val in ((7, cfg["vol"]), (10, cfg["pan"]), (91, cfg["rev"]), (93, cfg["cho"])):
                tr.append(mido.Message("control_change", channel=c, control=cc, value=val, time=0))
            if cfg["bend"] != 2:
                for cc, val in ((101, 0), (100, 0), (6, cfg["bend"]), (38, 0), (101, 127), (100, 127)):
                    tr.append(mido.Message("control_change", channel=c, control=cc, value=val, time=0))
            agora = 0
            for t, _, msg in ev:
                tr.append(msg.copy(time=t - agora))
                agora = t
            tr.append(mido.MetaMessage("end_of_track", time=max(0, fim_total - agora)))
            mid.tracks.append(tr)

        meta.append(mido.MetaMessage("end_of_track", time=fim_total))
        return mid

    def segundos(self, ticks=None):
        return (self.fim if ticks is None else ticks) / TPQ * 60 / self.bpm


# ============================================================
# ACOMPANHAMENTOS
# ============================================================

# Baixo: (passo no compasso, duração, função)
#   r raiz  o oitava  5 quinta  b quinta abaixo  3 terça  7 sétima
#   a aproximação cromática para o próximo acorde
BAIXOS = {
    "raiz": [(0, 16, "r")],
    "meio": [(0, 8, "r"), (8, 8, "r")],
    "pop": [(0, 6, "r"), (6, 2, "r"), (8, 4, "5"), (12, 2, "r"), (14, 2, "o")],
    "oitavas": [(i, 2, "r" if i % 4 == 0 else "o") for i in range(0, 16, 2)],
    "pulsante": [(i, 2, "r") for i in range(0, 16, 2)],
    "dezesseis": [(i, 1, "r") for i in range(16)],
    "galope": [(0, 2, "r"), (2, 1, "r"), (3, 1, "r"), (4, 2, "r"), (6, 1, "r"), (7, 1, "r"),
               (8, 2, "5"), (10, 1, "5"), (11, 1, "5"), (12, 2, "r"), (14, 1, "o"), (15, 1, "a")],
    "oompah": [(0, 3, "r"), (8, 3, "b")],
    "bossa": [(0, 6, "r"), (6, 2, "5"), (8, 6, "5"), (14, 2, "r")],
    "reggae": [(0, 5, "r"), (6, 2, "r"), (10, 2, "5"), (12, 3, "o")],
    "funk": [(0, 3, "r"), (3, 1, "r"), (6, 2, "o"), (8, 2, "r"), (10, 1, "7"), (11, 2, "o"),
             (14, 2, "a")],
    "sincopado": [(0, 3, "r"), (3, 3, "r"), (6, 2, "5"), (8, 3, "r"), (11, 3, "o"), (14, 2, "a")],
    "saltitante": [(0, 2, "r"), (4, 2, "5"), (6, 2, "o"), (8, 2, "r"), (12, 2, "3"), (14, 2, "a")],
    "synth": [(i, 1, "r" if i % 2 == 0 else "o") for i in range(16)],
    "caminhando": None,         # walking bass (ver abaixo)
}

# Acompanhamento: (passo, duração) para acordes ou "arp:<ordem>" para arpejos
ACOMPS = {
    "pad": "segmento",
    "blocos": [(0, 8), (8, 8)],
    "seminimas": [(0, 3), (4, 3), (8, 3), (12, 3)],
    "contratempo": [(2, 2), (6, 2), (10, 2), (14, 2)],
    "pop": [(0, 3), (3, 3), (6, 2), (8, 3), (11, 3), (14, 2)],
    "bossa": [(0, 2), (3, 2), (6, 3), (10, 2), (13, 3)],
    "charleston": [(0, 3), (6, 4), (12, 2)],
    "funk": [(0, 1), (3, 1), (6, 1), (7, 1), (10, 1), (12, 1), (14, 1)],
    "power": [(i, 2) for i in range(0, 16, 2)],
    "power_galope": [(0, 2), (2, 1), (3, 1), (4, 2), (6, 1), (7, 1), (8, 2), (10, 1),
                     (11, 1), (12, 2), (14, 1), (15, 1)],
    "strum": [(0, 3), (3, 3), (6, 2), (8, 2), (10, 2), (12, 2), (14, 2)],
    "arpejo8": ("arp", 2, [0, 1, 2, 3, 2, 1, 2, 3]),
    "arpejo16": ("arp", 1, [0, 1, 2, 3, 4, 3, 2, 1, 0, 1, 2, 3, 4, 3, 2, 1]),
    "alberti": ("arp", 2, [0, 2, 1, 2, 0, 2, 1, 2]),
    "harpa": ("arp", 1, [0, 1, 2, 3, 4, 5, 6, 7, 6, 5, 4, 3, 2, 1, 0, 1]),
    "caixinha": ("arp", 2, [0, 2, 3, 1, 4, 2, 3, 1]),
}

# Bateria: peça -> nota GM
PECAS = {
    "k": 36, "s": 38, "S": 37, "c": 39, "e": 40, "h": 42, "H": 46, "p": 44,
    "r": 51, "R": 53, "C": 49, "Z": 57, "b": 54, "m": 70, "a": 69, "w": 76, "W": 77,
    "g": 81, "o": 56, "q": 62, "Q": 63, "U": 64, "j": 60, "J": 61,
    "t": 50, "T": 47, "f": 43, "F": 41, "v": 75, "z": 55,
}
VEL_GOLPE = {"X": 118, "x": 92, "o": 48}

_FILL_LEVE = dict(k="x.......x.......", s="....x.......x.xx", h="x.x.x.x.x.x.....")
_FILL_ROCK = dict(k="x.......x.......", s="....x...XoXo....", t="............xx..",
                  f="..............xx", h="x.x.x.x.........")
_FILL_MARCIAL = dict(k="x.......x.......", s="X.ooX.ooXoXoXXXX")
_FILL_TOMS = dict(k="x...x...x.......", s="....X...", t="........xx......",
                  T="..........xx....", f="............xxxx")

BATERIAS = {
    "nenhuma": dict(),
    "calmo": dict(k="x.......x.......", m="..x...x...x...x.", S="........o.......",
                  fill=dict(k="x.......x.......", m="..x...x...xxxxxx")),
    "pop": dict(k="x.......x.x.....", s="....x.......x...", h="x.x.x.x.x.x.x.x.",
                fill=_FILL_LEVE),
    "rock": dict(k="x.....x.x.x.....", s="....X.......X...", h="x.x.x.x.x.x.x.x.",
                 fill=_FILL_ROCK),
    "rapido": dict(k="x.x...x.x.x...x.", s="....X.......X...", h="X.x.X.x.X.x.X.x.",
                   fill=_FILL_ROCK),
    "metal": dict(k="x.xxx.xxx.xxx.xx", s="....X.......X...", r="x.x.x.x.x.x.x.x.",
                  C="x...............", fill=_FILL_TOMS),
    "heroico": dict(k="x..x..x.x..x..x.", s="....X..o....X.oo", h="x.x.x.x.x.x.x.x.",
                    fill=_FILL_MARCIAL),
    "marcha": dict(k="x.......x.......", s="X.oxx.oxX.oxx.ox", fill=_FILL_MARCIAL),
    "disco": dict(k="x...x...x...x...", s="....X.......X...", c="....x.......x...",
                  h="x...x...x...x...", H="..x...x...x...x.", fill=_FILL_LEVE),
    "chip": dict(k="x...x...x...x...", e="....x.......x...", h="x.x.x.x.x.x.x.x.",
                 fill=dict(k="x.......x.......", e="....x...x.x.xxxx")),
    "chip2": dict(k="x.....x.x.......", e="....x.......x..x", h="xoxoxoxoxoxoxoxo",
                  fill=dict(k="x.....x.x.......", e="....x..xx.xxxxxx")),
    "bossa": dict(k="x.....x.x.....x.", S="x..x..x...x..x..", m="xoxoxoxoxoxoxoxo",
                  fill=dict(k="x.....x.x.......", S="x..x..x...x.x.xx", m="xoxoxoxoxoxoxoxo")),
    "swing": dict(r="x...x.x.x...x.x.", p="....x.......x...", k="o.......o.......",
                  s="......o.......o.", fill=dict(r="x...x.x.x.......", s="......o.x..xX.x.",
                                                   k="o.......o......x")),
    "praia": dict(k="x..x....x..x....", S="....x.......x...", m="x.xxx.xxx.xxx.xx",
                  q="..x..x....x.x...", U="x.......x.......",
                  fill=dict(k="x..x....x.......", q="..x..x..xxxxxxxx", m="x.xxx.xxx.xxx.xx")),
    "funk": dict(k="x..x..x...x.x...", s="....X..o.o..X..o", h="xoxoxoxoxoxoxoxo",
                 fill=dict(k="x..x..x.........", s="....X..o.oXoXXXX", h="xoxoxoxo........")),
    "synthwave": dict(k="x.....x...x.....", c="....x.......x...", h="x.x.x.x.x.x.x.x.",
                      fill=dict(k="x.....x...x.....", c="....x...x.x.xxxx")),
    "polka": dict(k="x.......x.......", s="....x.......x...", h="..x...x...x...x.",
                  fill=dict(k="x.......x.......", s="....x...x.x.x.xx")),
    "country": dict(k="x.......x.......", s="ooooXoooooooXooo", fill=_FILL_LEVE),
    "taiko": dict(k="x...x..xx...x...", F="x.....x...x.....", f="......x.....x.x.",
                  s="....X.......X...", fill=dict(k="x.......x.......", F="x.x.x.x.xxxxxxxx",
                                                  f="........x.x.xxxx")),
    "ska": dict(k="x.......x.......", s="....X.......X...", h="..x...x...x...x.",
                fill=_FILL_LEVE),
    "vapor": dict(k="x.......x..x....", c="....x.......x...", h="..x...x...x...x.",
                  m="xxxxxxxxxxxxxxxx", fill=dict(k="x.......x.......", c="....x...x.x.x.x.")),
    "torcida": dict(k="x...x...x...x...", s="....X.......X...", c="....X.......X...",
                    h="x.x.x.x.x.x.x.x.", t="..............x.", fill=_FILL_TOMS),
}


def tocar_baixo(p, segs, estilo, vel, lo=33, hi=45, papel="baixo"):
    if estilo == "caminhando":
        _baixo_caminhando(p, segs, vel, lo, hi, papel)
        return
    padrao = BAIXOS[estilo]
    for i, (s, d, ac) in enumerate(segs):
        prox = segs[i + 1][2] if i + 1 < len(segs) else segs[0][2]
        r = mais_proxima(ac.baixo, (lo + hi) / 2, lo, hi)
        r = r if r < hi else r - 12
        compasso = (s // 16) * 16
        for off, dur, fn in padrao:
            ps = compasso + off
            if not (s <= ps < s + d):
                continue
            dur = min(dur, s + d - ps)
            if fn == "r":
                n = r
            elif fn == "o":
                n = r + 12
            elif fn == "5":
                n = r + 7
            elif fn == "b":
                n = r - 5 if r - 5 >= lo - 5 else r + 7
            elif fn == "3":
                n = r + ac.intervalos[1]
            elif fn == "7":
                n = r + (ac.intervalos[3] if len(ac.intervalos) > 3 else 10)
            else:   # aproximação
                alvo = mais_proxima(prox.baixo, r, lo, hi + 5)
                n = alvo - 1 if p.rnd.random() < 0.6 else alvo + 1
            p.nota(papel, ps, dur, n, vel + (6 if off == 0 else 0))


def _baixo_caminhando(p, segs, vel, lo, hi, papel):
    ant = None
    for i, (s, d, ac) in enumerate(segs):
        prox = segs[i + 1][2] if i + 1 < len(segs) else segs[0][2]
        tons = ac.classes()
        batidas = d // 4
        for b in range(batidas):
            ps = s + b * 4
            if b == 0:
                n = mais_proxima(ac.baixo, ant if ant else (lo + hi) / 2, lo, hi + 4)
            elif b == batidas - 1:
                alvo = mais_proxima(prox.baixo, ant, lo, hi + 4)
                n = alvo + (-1 if alvo > ant else 1) if abs(alvo - ant) > 1 else alvo + 2
            else:
                n = mais_proxima(tons[(b * 2) % len(tons)], ant + (2 if b % 2 else -1), lo, hi + 4)
            p.nota(papel, ps, 4, n, vel + (6 if b == 0 else 0), art=0.85)
            ant = n


def tocar_acomp(p, segs, estilo, vel, centro=62, papel="acomp", max_notas=4, power=False):
    padrao = ACOMPS[estilo]
    ant = None
    for s, d, ac in segs:
        if power:
            r = mais_proxima(ac.raiz, centro - 5, centro - 12, centro + 6)
            notas = [r, r + 7, r + 12]
        else:
            notas = voicing(ac, centro, ant, max_notas)
            ant = notas
        if padrao == "segmento":
            for n in notas:
                p.nota(papel, s, d, n, vel, art=0.98)
            continue
        compasso = (s // 16) * 16
        if isinstance(padrao, tuple):
            _, passo, ordem = padrao
            arp = notas + [n + 12 for n in notas]
            for k, idx in enumerate(ordem):
                ps = compasso + k * passo
                if s <= ps < s + d:
                    p.nota(papel, ps, passo, arp[idx % len(arp)], vel + (6 if k % 4 == 0 else 0))
            continue
        for off, dur in padrao:
            ps = compasso + off
            if s <= ps < s + d:
                dur = min(dur, s + d - ps)
                acento = 8 if off % 4 == 0 else 0
                for j, n in enumerate(notas):
                    p.nota(papel, ps + (j * 0.08 if estilo == "strum" else 0), dur, n,
                           vel + acento)


def tocar_contra(p, segs, vel, lo=55, hi=72, papel="contra", ritmo=8):
    """Linha de notas-guia (terças/sétimas) com movimento suave."""
    ant = (lo + hi) // 2
    for s, d, ac in segs:
        guias = ac.guias()
        partes = max(1, d // ritmo)
        for k in range(partes):
            cands = [mais_proxima(pc, ant, lo, hi) for pc in guias]
            # evita repetir a mesma nota muitas vezes
            cands.sort(key=lambda n: abs(n - ant) + (3 if n == ant and k else 0))
            n = cands[0]
            p.nota(papel, s + k * ritmo, d // partes, n, vel + (4 if k == 0 else -4), art=0.97)
            ant = n


def tocar_bateria(p, passo_inicio, n_compassos, estilo, intensidade="normal",
                  crash=False, fill=True, vel_mult=1.0):
    padrao = BATERIAS[estilo]
    if not padrao:
        return
    for c in range(n_compassos):
        base = passo_inicio + c * 16
        ultimo = c == n_compassos - 1
        pecas = padrao.get("fill") if (ultimo and fill and "fill" in padrao) else padrao
        for peca, ritmo in pecas.items():
            if peca == "fill":
                continue
            if intensidade == "leve" and peca in ("s", "e", "c", "C", "H", "t", "T", "f", "F"):
                if not ultimo:
                    continue
            for i, ch in enumerate(ritmo):
                if ch == ".":
                    continue
                v = VEL_GOLPE.get(ch, 90) * vel_mult
                if intensidade == "leve":
                    v *= 0.75
                elif intensidade == "forte":
                    v *= 1.08
                p.nota("bat", base + i, 1, PECAS[peca], v, art=1.0)
        if c == 0 and crash:
            p.nota("bat", base, 4, PECAS["C"], 110 * vel_mult, art=1.0)


# ============================================================
# MONTAGEM DE UMA MÚSICA
# ============================================================
# Uma faixa é um dicionário (ver partituras.py):
#   bpm, tonica, modo, swing
#   inst: papel -> dict(programa, vol, pan, rev, cho, art)
#         papéis: lead, sino, contra, acomp, pad, baixo, bat, dobra, extra...
#   baixo/acomp/bat: estilos;  contra: True/False
#   progA/progB (4 ou 8 compassos), a/fimA/b/fimB (melodias)
#   forma: lista de seções (intro, A, B, A2, ponte, B2, ...)

PERFIS = {
    "intro": dict(mel="sino", bat="leve", acomp=False, contra=False, vel=0.82),
    "A": dict(mel="lead", bat="normal", acomp=True, contra=False, vel=0.92),
    "B": dict(mel="lead", bat="normal", acomp=True, contra=True, vel=1.0, crash=True),
    "A2": dict(mel="lead", bat="forte", acomp=True, contra=True, dobra=True, vel=1.05,
               crash=True),
    "B2": dict(mel="lead", bat="forte", acomp=True, contra=True, dobra=True, vel=1.05,
               crash=True),
    "ponte": dict(mel="sino", bat="leve", acomp=False, contra=True, vel=0.85),
}


def _oito(prog):
    c = compassos(prog)
    return prog if len(c) >= 8 else juntar(prog, prog)


def _melodia(d, parte):
    """A = a + 2 primeiros compassos de a + fim."""
    chave = parte.lower()
    if "mel" + parte in d:
        return d["mel" + parte]
    if chave not in d:
        return None
    c = compassos(d[chave])
    fim = d.get("fim" + parte)
    if fim is None:
        return d[chave]
    return juntar(d[chave], juntar(*c[:2]), fim)


def _terca_abaixo(alt, tonica, modo):
    esc = [(classe(tonica) + i) % 12 for i in ESCALAS[modo]]
    for desce in (3, 4, 2, 5):
        if (alt - desce) % 12 in esc and desce in (3, 4):
            return alt - desce
    return alt - 3


def prog_intro(tonica, modo):
    """I - IV - I - V7 (ou i - VI - i - V7 nos modos menores)."""
    t = classe(tonica)
    nome = lambda s: _NOMES[(t + s) % 12]
    if modo in ("maior", "mixolidia", "lidia"):
        return f"{nome(0)} | {nome(5)} | {nome(0)} | {nome(7)}7"
    if modo == "dorica":
        return f"{nome(0)}m | {nome(5)} | {nome(0)}m | {nome(7)}7"
    return f"{nome(0)}m | {nome(8)} | {nome(0)}m | {nome(7)}7"


def montar(nome, d):
    p = Partitura(nome, d["bpm"], d.get("swing", 0.0))
    for papel, cfg in d["inst"].items():
        p.instrumento(papel, **cfg)

    tonica, modo = d["tonica"], d.get("modo", "maior")
    forma = d.get("forma")
    if forma is None:
        forma = ["intro", "A", "B", "A2"]
        if 28 * 4 * 60 / d["bpm"] < 50:         # música rápida: mais um B
            forma.append("B2")
    perfis = {k: dict(v) for k, v in PERFIS.items()}
    for k, v in d.get("perfis", {}).items():
        perfis.setdefault(k, {}).update(v)

    passo = 0
    for sec in forma:
        base = re.sub(r"\d+$", "", sec) if sec not in perfis else sec
        perfil = perfis.get(sec, perfis.get(base, PERFIS["A"]))
        if sec == "intro":
            prog = d.get("progIntro") or prog_intro(tonica, modo)
            mel = d.get("melIntro", motivo(d.get("motivo_tonica", tonica), modo, ("m", "r", "m", "f")))
        elif sec == "ponte":
            prog = d["progPonte"]
            mel = d.get("melPonte")
        else:
            letra = base[0]
            prog = _oito(d["prog" + letra])
            mel = _melodia(d, letra)
        segs = ler_progressao(prog, passo, f"{nome}/{sec}")
        n = (segs[-1][0] + segs[-1][1] - passo) // 16
        vel = perfil.get("vel", 1.0)

        # Baixo
        if p.tem("baixo") and perfil.get("baixo", True):
            estilo_b = d.get("baixo_" + sec, d.get("baixo", "pop"))
            if sec in ("intro", "ponte") and d.get("baixo_suave", True):
                estilo_b = d.get("baixo_intro", "meio")
            lo, hi = d.get("reg_baixo", (33, 45))
            tocar_baixo(p, segs, estilo_b, 88 * vel, lo, hi)

        # Pad
        if p.tem("pad") and perfil.get("pad", True):
            tocar_acomp(p, segs, "pad", 62 * vel, d.get("centro_pad", 60), "pad",
                        max_notas=d.get("notas_pad", 4))

        # Acompanhamento
        if p.tem("acomp") and perfil.get("acomp"):
            tocar_acomp(p, segs, d.get("acomp_" + sec, d.get("acomp", "pop")), 72 * vel,
                        d.get("centro_acomp", 62), "acomp", power=d.get("power", False))

        # Segundo acompanhamento (ex.: guitarra + piano)
        if p.tem("acomp2") and perfil.get("acomp"):
            tocar_acomp(p, segs, d.get("acomp2", "arpejo8"), 66 * vel,
                        d.get("centro_acomp2", 72), "acomp2")

        # Contramelodia
        if p.tem("contra") and perfil.get("contra") and d.get("contra", True):
            lo, hi = d.get("reg_contra", (55, 72))
            tocar_contra(p, segs, 74 * vel, lo, hi, ritmo=d.get("ritmo_contra", 8))

        # Bateria
        if p.tem("bat"):
            estilo_bat = d.get("bat_" + sec, d.get("bat", "pop"))
            tocar_bateria(p, passo, n, estilo_bat, perfil.get("bat", "normal"),
                          crash=perfil.get("crash", False), vel_mult=d.get("vel_bat", 1.0))

        # Melodia
        if mel:
            papel = perfil.get("mel", "lead")
            papel = d.get("mel_" + sec, papel)
            if not p.tem(papel):
                papel = "lead"
            transp = d.get("transp_" + sec, 0)
            p.tocar(papel, mel, passo, 98 * vel, transp=transp, onde=f"{nome}/{sec}")
            if perfil.get("dobra") and d.get("dobra") is not None:
                dobra = d["dobra"]
                papel_d = "dobra" if p.tem("dobra") else "sino"
                if dobra == "tercas":
                    eventos, _ = ler_seq(mel, f"{nome}/{sec}")
                    for ps, dd, alts in eventos:
                        for a in alts:
                            p.nota(papel_d, passo + ps, dd, _terca_abaixo(a + transp, tonica, modo),
                                   80 * vel)
                else:
                    p.tocar(papel_d, mel, passo, 80 * vel, transp=transp + dobra,
                            onde=f"{nome}/{sec}")

        # Camadas extras: (papel, seções, sequência de 1+ compassos repetida)
        for papel, secoes, seq in d.get("extras", []):
            if sec in secoes or base in secoes:
                cs = compassos(seq)
                for k in range(n):
                    p.tocar(papel, cs[k % len(cs)], passo + k * 16, 90 * vel,
                            onde=f"{nome}/{sec}/{papel}")

        passo += n * 16

    p.fim = passo * PASSO
    return p


# ============================================================
# RENDERIZAÇÃO
# ============================================================

def _ler_wav_float(caminho):
    with open(caminho, "rb") as f:
        dados = f.read()
    if dados[:4] != b"RIFF":
        raise ValueError("wav inválido")
    pos = 12
    fmt = None
    while pos < len(dados):
        cid = dados[pos:pos + 4]
        tam = int.from_bytes(dados[pos + 4:pos + 8], "little")
        corpo = dados[pos + 8:pos + 8 + tam]
        if cid == b"fmt ":
            fmt = int.from_bytes(corpo[0:2], "little"), int.from_bytes(corpo[2:4], "little"), \
                int.from_bytes(corpo[14:16], "little")
        elif cid == b"data":
            tipo, canais, bits = fmt
            if tipo == 3 or (tipo == 0xFFFE and bits == 32):
                a = np.frombuffer(corpo, dtype="<f4").astype(np.float64)
            else:
                a = np.frombuffer(corpo, dtype="<i2").astype(np.float64) / 32768
            return a.reshape(-1, canais)
        pos += 8 + tam + (tam & 1)
    raise ValueError("wav sem dados")


def renderizar(mid, pasta_tmp, nome):
    arq_mid = os.path.join(pasta_tmp, nome + ".mid")
    arq_wav = os.path.join(pasta_tmp, nome + ".wav")
    mid.save(arq_mid)
    subprocess.run([
        FLUIDSYNTH, "-ni", "-q", "-F", arq_wav, "-r", str(TAXA), "-g", "0.5",
        "-o", "audio.file.format=float", "-o", "synth.polyphony=1024",
        "-o", "synth.reverb.active=1", "-o", "synth.chorus.active=1",
        "-o", "synth.reverb.room-size=0.62", "-o", "synth.reverb.damp=0.35",
        "-o", "synth.reverb.width=0.9", "-o", "synth.reverb.level=0.75",
        SOUNDFONT, arq_mid,
    ], check=True, capture_output=True)
    return _ler_wav_float(arq_wav)


def _loudness(audio, pasta_tmp, nome):
    """Loudness integrada (LUFS) medida pelo ffmpeg."""
    raw = os.path.join(pasta_tmp, nome + ".f32")
    audio.astype("<f4").tofile(raw)
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-f", "f32le", "-ar", str(TAXA),
                        "-ac", str(audio.shape[1]), "-i", raw, "-af",
                        "loudnorm=print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    bloco = r.stderr[r.stderr.rfind("{"):r.stderr.rfind("}") + 1]
    return float(json.loads(bloco)["input_i"])


def limitar(audio, teto=0.93, joelho=0.75):
    """Limitador suave: nada passa do teto, o resto fica igual."""
    a = np.abs(audio)
    excesso = a > joelho
    if excesso.any():
        faixa = teto - joelho
        comp = joelho + faixa * np.tanh((a[excesso] - joelho) / faixa)
        audio = audio.copy()
        audio[excesso] = np.sign(audio[excesso]) * comp
    return audio


# O LAME atrasa o áudio em 1105 amostras (576 do codificador + 529 do
# decodificador) e o pygame não desconta isso. Sem o quadro Xing e com
# o áudio "girado" para trás, o que se ouve fica no tempo certo (o
# jogo de ritmo depende disso; nos loops só muda a fase).
ATRASO_MP3 = 1105


def exportar_mp3(audio, destino, pasta_tmp, nome, kbps, compensar=True):
    if compensar:
        audio = np.roll(audio, -ATRASO_MP3, axis=0)
    raw = os.path.join(pasta_tmp, nome + "_final.f32")
    audio.astype("<f4").tofile(raw)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "f32le",
                    "-ar", str(TAXA), "-ac", str(audio.shape[1]), "-i", raw,
                    "-c:a", "libmp3lame", "-b:a", f"{kbps}k", "-write_xing", "0", destino],
                   check=True)


def produzir_musica(nome, d, pasta_tmp):
    p = d["montar"](nome, d) if "montar" in d else montar(nome, d)
    os.makedirs(os.path.join(PASTA_MIDI, "trilhas"), exist_ok=True)
    p.midi().save(os.path.join(PASTA_MIDI, "trilhas", nome + ".mid"))

    loop = d.get("loop", True)
    if loop:
        # Toca duas vezes e pega a segunda: o fim (com reverb) já
        # emenda no começo, então o loop fica perfeito
        audio = renderizar(p.midi(repeticoes=2, cauda_seg=3), pasta_tmp, nome)
        n = int(round(p.segundos() * TAXA))
        audio = audio[n:2 * n]
    else:
        audio = renderizar(p.midi(cauda_seg=1), pasta_tmp, nome)
        n = int(round(p.segundos() * TAXA))
        audio = audio[:n]
        if len(audio) < n:
            audio = np.vstack([audio, np.zeros((n - len(audio), audio.shape[1]))])

    alvo = d.get("lufs", -16.0)
    lufs = _loudness(audio, pasta_tmp, nome)
    audio = audio * 10 ** ((alvo - lufs) / 20)
    audio = limitar(audio)
    exportar_mp3(audio, os.path.join(PASTA_TRILHAS, nome + ".mp3"), pasta_tmp, nome, 160)
    return nome, p.segundos()


def produzir_sfx(nome, criar, pasta_tmp):
    p, pico = criar()
    os.makedirs(os.path.join(PASTA_MIDI, "sfx"), exist_ok=True)
    p.midi().save(os.path.join(PASTA_MIDI, "sfx", nome + ".mid"))
    audio = renderizar(p.midi(cauda_seg=1.5), pasta_tmp, "sfx_" + nome)

    # Corta o silêncio do começo e do fim
    nivel = np.abs(audio).max(axis=1)
    ativo = np.nonzero(nivel > nivel.max() * 0.03)[0]
    ini = max(0, ativo[0] - 16)
    fim = min(len(audio), ativo[-1] + int(0.01 * TAXA))
    audio = audio[ini:fim].copy()
    rampa = min(len(audio), int(0.02 * TAXA))
    audio[-rampa:] *= np.linspace(1, 0, rampa)[:, None]

    audio = audio / np.abs(audio).max() * pico
    exportar_mp3(audio, os.path.join(PASTA_SFX, nome + ".mp3"), pasta_tmp, "sfx_" + nome, 128,
                 compensar=False)
    return nome, len(audio) / TAXA


# ============================================================

def main(args):
    from ferramentas import partituras

    so_sfx = "--sfx" in args
    so_midi = "--midi" in args
    nomes = [a for a in args if not a.startswith("--")]

    os.makedirs(PASTA_TRILHAS, exist_ok=True)
    os.makedirs(PASTA_SFX, exist_ok=True)

    musicas = {} if so_sfx else {k: v for k, v in partituras.MUSICAS.items()
                                 if not nomes or k in nomes}
    efeitos = {k: v for k, v in partituras.EFEITOS.items()
               if (so_sfx and not nomes) or k in nomes or (not nomes and not so_sfx)}

    if so_midi:
        for nome, d in musicas.items():
            p = d["montar"](nome, d) if "montar" in d else montar(nome, d)
            os.makedirs(os.path.join(PASTA_MIDI, "trilhas"), exist_ok=True)
            p.midi().save(os.path.join(PASTA_MIDI, "trilhas", nome + ".mid"))
            print(f"{nome}: {p.segundos():.1f}s")
        return

    with tempfile.TemporaryDirectory() as tmp, ThreadPoolExecutor(6) as ex:
        tarefas = [ex.submit(produzir_musica, n, d, tmp) for n, d in musicas.items()]
        tarefas += [ex.submit(produzir_sfx, n, c, tmp) for n, c in efeitos.items()]
        for t in tarefas:
            nome, seg = t.result()
            print(f"{nome}: {seg:.1f}s")


if __name__ == "__main__":
    # Roda pelo módulo importado (o mesmo que partituras.py usa)
    from ferramentas import compor_musicas
    compor_musicas.main(sys.argv[1:])
