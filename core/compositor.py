import random

from core import sintetizador as s

# ============================================================
# COMPOSITOR PROCEDURAL
# ============================================================
# Cria uma música inteira a partir de um "estilo" (dicionário).
# Cada mini jogo declara o seu estilo e ganha uma trilha única:
#
#   TRILHA = dict(
#       bpm=128, tom="D", escala="menor",
#       lead="quadrada", duty=0.25, envelope="normal",
#       baixo="rock", onda_baixo="triangulo",
#       acomp="arpejo16", onda_acomp="sino",
#       bateria="rock", energia=0.6, eco=(0.18, 0.2),
#   )
#
# A melodia segue a forma A A' B A (8 compassos), usa notas do
# acorde nos tempos fortes e termina na tônica, então soa como
# "música de verdade" e não como notas aleatórias.

ESCALAS = {
    "maior":              [0, 2, 4, 5, 7, 9, 11],
    "menor":              [0, 2, 3, 5, 7, 8, 10],
    "dorica":             [0, 2, 3, 5, 7, 9, 10],
    "mixolidia":          [0, 2, 4, 5, 7, 9, 10],
    "lidia":              [0, 2, 4, 6, 7, 9, 11],
    "harmonica":          [0, 2, 3, 5, 7, 8, 11],
    "pentatonica":        [0, 2, 4, 7, 9],
    "pentatonica_menor":  [0, 3, 5, 7, 10],
    "blues":              [0, 3, 5, 6, 7, 10],
    "hirajoshi":          [0, 2, 3, 7, 8],
}

# Progressões em graus (0 = I). Cada uma tem 4 acordes (1 por compasso).
PROGRESSOES = {
    "maior": [[0, 4, 5, 3], [0, 5, 3, 4], [0, 3, 4, 4], [0, 3, 0, 4], [5, 3, 0, 4]],
    "menor": [[0, 5, 2, 6], [0, 3, 4, 0], [0, 6, 5, 4], [0, 3, 6, 4], [0, 5, 3, 4]],
}

TONS = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5,
        "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}

_NOMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

BATERIAS = {
    "rock":      {"k": "x...x...x...x...", "s": "....x.......x...", "h": "x.x.x.x.x.x.x.x."},
    "pop":       {"k": "x.......x.x.....", "s": "....x.......x...", "h": "x.x.x.x.x.x.x.x."},
    "disco":     {"k": "x...x...x...x...", "s": "....x.......x...", "h": "..x...x...x...x."},
    "funk":      {"k": "x.....x...x.....", "s": "....x.......x...", "h": "x.xxx.x.x.xxx.x.",
                  "c": "............x..."},
    "reggae":    {"k": "........x.......", "s": "........x.......", "h": "..x...x...x...x."},
    "halftime":  {"k": "x.........x.....", "s": "........x.......", "h": "x.x.x.x.x.x.x.x."},
    "marcha":    {"k": "x...x...x...x...", "s": "..x...x.x.x...x.", "h": ""},
    "breakbeat": {"k": "x.........x..x..", "s": "....x..x.x..x...", "h": "x.xxx.xxx.xxx.xx"},
    "galope":    {"k": "x..x..x.x..x..x.", "s": "....x.......x...", "h": "xxxxxxxxxxxxxxxx"},
    "suave":     {"h": "x...x...x...x..."},
    "taiko":     {"k": "x..x..x...x.x...", "c": "....x.......x..."},
    "samba":     {"k": "x..x....x..x....", "s": "..x..x.x..x..x.x", "h": "xxxxxxxxxxxxxxxx"},
    "baiao":     {"k": "x..x....x..x....", "h": "x.xxx.xxx.xxx.xx", "c": "....x.......x..."},
    "shuffle":   {"k": "x.....x.x.....x.", "s": "....x.......x...", "h": "x..xx..xx..xx..x"},
    "nenhuma":   {},
}

# Ritmos da melodia (1 compasso = 16 passos). Número = duração.
RITMOS = {
    "calmo":   [[4, 4, 4, 4], [8, 4, 4], [4, 4, 8], [6, 2, 8], [4, 2, 2, 8]],
    "medio":   [[2, 2, 4, 2, 2, 4], [4, 2, 2, 4, 4], [2, 2, 2, 2, 8], [3, 1, 4, 2, 2, 4],
                [2, 4, 2, 4, 4]],
    "agitado": [[2, 2, 2, 2, 2, 2, 4], [1, 1, 2, 2, 2, 4, 4], [2, 1, 1, 2, 2, 2, 2, 4],
                [2, 2, 1, 1, 2, 2, 2, 4], [1, 1, 1, 1, 2, 2, 4, 4]],
}


def _nome(midi):
    return f"{_NOMES[midi % 12]}{midi // 12 - 1}"


class _Harmonia:
    """Traduz graus da escala em notas MIDI."""

    def __init__(self, tom, escala):
        self.raiz = 60 + TONS.get(tom, 0)          # oitava 4
        self.escala = ESCALAS.get(escala, ESCALAS["maior"])
        # Para os acordes usamos sempre uma escala de 7 notas
        base = "menor" if 3 in self.escala[:3] else "maior"
        self.escala7 = self.escala if len(self.escala) == 7 else ESCALAS[base]
        self.modo = base

    def grau(self, g, oitava=0):
        """Nota MIDI do grau g (pode ser negativo ou > tamanho)."""
        n = len(self.escala)
        return self.raiz + 12 * (oitava + g // n) + self.escala[g % n]

    def acorde(self, grau, oitava=0):
        """Tríade (3 notas MIDI) sobre um grau da escala de 7 notas."""
        e = self.escala7
        notas = []
        for salto in (0, 2, 4):
            g = grau + salto
            notas.append(self.raiz + 12 * (oitava + g // 7) + e[g % 7])
        return notas


def _melodia_compasso(rnd, harm, acorde, ritmo, grau_atual, final=False):
    """Gera 1 compasso de melodia. Devolve (tokens, último grau)."""
    tokens = []
    n = len(harm.escala)
    notas_acorde = {m % 12 for m in acorde}
    pos = 0

    for i, dur in enumerate(ritmo):
        forte = pos % 4 == 0
        ultimo = final and i == len(ritmo) - 1

        if ultimo:
            # Termina na tônica mais próxima
            alvo = round(grau_atual / n) * n
            grau_atual = alvo
        else:
            passo = rnd.choice([-2, -1, -1, 1, 1, 2, 0, 3, -3])
            candidato = max(-2, min(n + 3, grau_atual + passo))
            # Tempo forte: puxa para uma nota do acorde
            if forte:
                for ajuste in (0, 1, -1, 2, -2):
                    g = candidato + ajuste
                    if harm.grau(g, 1) % 12 in notas_acorde:
                        candidato = g
                        break
            grau_atual = candidato

        # Pausa de vez em quando (não no começo nem no final)
        if 0 < i < len(ritmo) - 1 and not forte and rnd.random() < 0.12:
            tokens.append(f".*{dur}" if dur > 1 else ".")
        else:
            nota = _nome(harm.grau(grau_atual, 1))
            tokens.append(f"{nota}*{dur}" if dur > 1 else nota)
        pos += dur

    return tokens, grau_atual


def compor_estilo(estilo, semente=0):
    """Gera o buffer de áudio de uma trilha a partir do estilo."""
    rnd = random.Random(semente)
    bpm = estilo.get("bpm", 120)
    harm = _Harmonia(estilo.get("tom", "C"), estilo.get("escala", "maior"))
    energia = estilo.get("energia", 0.5)

    # -------- Harmonia (4 acordes, repetidos 2x = 8 compassos)
    prog = rnd.choice(PROGRESSOES[harm.modo])
    graus = prog + prog
    acordes = [harm.acorde(g) for g in graus]

    # -------- Melodia A A' B A
    densidade = "calmo" if energia < 0.35 else ("medio" if energia < 0.7 else "agitado")
    ritmos = RITMOS[densidade]
    frase_a = [rnd.choice(ritmos) for _ in range(2)]
    frase_b = [rnd.choice(ritmos) for _ in range(2)]
    melodia = []
    grau = rnd.choice([0, 2, 4])
    semente_a = rnd.random()

    for c in range(8):
        if c in (0, 1, 6, 7):          # A
            r = frase_a[c % 2]
            sub = random.Random(semente_a + c % 2)
        elif c in (2, 3):              # A'
            r = frase_a[c % 2]
            sub = random.Random(semente_a + 10 + c)
        else:                          # B
            r = frase_b[c % 2]
            sub = random.Random(semente_a + 20 + c)
        tokens, grau = _melodia_compasso(sub, harm, acordes[c], r, grau, final=(c == 7))
        melodia.extend(tokens)

    melodia_seq = " ".join(melodia)

    # -------- Baixo
    tipo_baixo = estilo.get("baixo", "pop")
    baixo = []
    for ac in acordes:
        r = _nome(ac[0] - 24)
        q = _nome(ac[0] - 24 + 7)
        o = _nome(ac[0] - 12)
        if tipo_baixo == "rock":
            baixo.append(f"{r}*2 {o}*2 " * 4)
        elif tipo_baixo == "oompah":
            baixo.append(f"{r}*2 . . {q}*2 . . {r}*2 . . {q}*2 . .")
        elif tipo_baixo == "tropical":
            baixo.append(f"{r}*3 {r} . {r}*2 {q}*2 {r}*3 {q} {o}*2 .")
        elif tipo_baixo == "misterio":
            baixo.append(f"{r}*3 {r} {r}*2 {q}*2 {r}*3 {r} {r}*2 {o}*2")
        elif tipo_baixo == "walking":
            t = _nome(ac[0] - 24 + (3 if harm.modo == "menor" else 4))
            baixo.append(f"{r}*4 {t}*4 {q}*4 {o}*4")
        elif tipo_baixo == "sincopado":
            baixo.append(f"{r}*2 . {o} . {r} . {q} {r}*2 . {q} {o} . {q} .")
        elif tipo_baixo == "longo":
            baixo.append(f"{r}*16")
        else:  # pop
            baixo.append(f"{r}*2 {r}*2 {q}*2 {r}*2 {o}*2 {q}*2 {r}*2 {q}*2")
    baixo_seq = " ".join(baixo)

    # -------- Acompanhamento
    tipo_acomp = estilo.get("acomp", "arpejo8")
    acomp = []
    for ac in acordes:
        a, b, c = (_nome(m) for m in ac)
        d = _nome(ac[0] + 12)
        if tipo_acomp == "arpejo16":
            acomp.append(f"{a} {b} {c} {d} " * 4)
        elif tipo_acomp == "contratempo":
            acomp.append(f".*2 {a}+{b}+{c}*2 " * 4)
        elif tipo_acomp == "pad":
            acomp.append(f"{a}+{b}+{c}*16")
        elif tipo_acomp == "chop":
            x = f"{a}+{b}+{c}"
            acomp.append(f". . {x} . . {x} . . {x} . . {x} . {x} . .")
        elif tipo_acomp == "nenhum":
            acomp.append(".*16")
        else:  # arpejo8
            acomp.append(f"{a}*2 {b}*2 {c}*2 {b}*2 {a}*2 {b}*2 {d}*2 {b}*2")
    acomp_seq = " ".join(acomp)

    from core.trilhas import compor
    vozes = [
        (melodia_seq, dict(tipo=estilo.get("lead", "quadrada"),
                           duty=estilo.get("duty", 0.25),
                           vol=estilo.get("vol_lead", 0.2),
                           envelope=estilo.get("envelope", "normal"))),
        (baixo_seq, dict(tipo=estilo.get("onda_baixo", "triangulo"),
                         duty=0.5, vol=estilo.get("vol_baixo", 0.3),
                         envelope=estilo.get("envelope_baixo", "staccato"))),
    ]
    if tipo_acomp != "nenhum":
        pluck = estilo.get("onda_acomp", "sino") in ("sino", "quadrada") and tipo_acomp != "pad"
        vozes.append((acomp_seq, dict(tipo=estilo.get("onda_acomp", "sino"),
                                      duty=0.125,
                                      vol=estilo.get("vol_acomp", 0.07),
                                      envelope="pluck" if pluck else "normal")))

    bateria = BATERIAS.get(estilo.get("bateria", "pop"), {})
    bateria = {k: v for k, v in bateria.items() if v}

    return compor(bpm, 8, vozes, bateria=bateria or None,
                  vol_bateria=estilo.get("vol_bateria", 0.5),
                  eco=tuple(estilo.get("eco", (0.18, 0.2))))
