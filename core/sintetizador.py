import array
import io
import math
import random
import wave

# ============================================================
# SINTETIZADOR CHIPTUNE (PYTHON PURO)
# ============================================================
# Gera músicas e efeitos sonoros no estilo 8-bit, sem precisar
# de numpy nem de arquivos de áudio externos.
#
# Notação das melodias (um "passo" = 1/16 de compasso):
#   "C5"    -> nota Dó na oitava 5 durando 1 passo
#   "E5*3"  -> nota Mi durando 3 passos
#   "."     -> pausa de 1 passo
#   ".*4"   -> pausa de 4 passos
#   "|"     -> separador de compasso (ignorado, só para leitura)

TAXA = 22050

_SEMITONS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def frequencia(nome):
    """Converte 'C#5', 'Bb3', 'A4'... em Hz."""
    letra = nome[0].upper()
    resto = nome[1:]
    semitom = _SEMITONS[letra]

    while resto and resto[0] in "#b":
        semitom += 1 if resto[0] == "#" else -1
        resto = resto[1:]

    oitava = int(resto)
    midi = 12 * (oitava + 1) + semitom
    return 440.0 * 2 ** ((midi - 69) / 12)


def transpor(nome, semitons):
    """Transpõe uma nota em semitons (devolve outro nome)."""
    nomes = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    letra = nome[0].upper()
    resto = nome[1:]
    semitom = _SEMITONS[letra]

    while resto and resto[0] in "#b":
        semitom += 1 if resto[0] == "#" else -1
        resto = resto[1:]

    midi = 12 * (int(resto) + 1) + semitom + semitons
    return f"{nomes[midi % 12]}{midi // 12 - 1}"


# ============================================================
# ONDAS
# ============================================================

def _onda(tipo, fase, duty):
    if tipo == "quadrada":
        return 1.0 if fase < duty else -1.0
    if tipo == "triangulo":
        return 4.0 * abs(fase - 0.5) - 1.0
    if tipo == "serra":
        return 2.0 * fase - 1.0
    # seno / sino
    return math.sin(fase * math.tau)


_tabelas = {}


def _tabela(tipo, duty, tamanho=512):
    """Tabela de um ciclo da onda (muito mais rápido que calcular)."""
    chave = (tipo, duty, tamanho)
    if chave not in _tabelas:
        _tabelas[chave] = _criar_tabela(tipo, duty, tamanho)
    return _tabelas[chave]


def _criar_tabela(tipo, duty, tamanho):
    if tipo == "sino":
        return [
            math.sin(i / tamanho * math.tau) * 0.75
            + math.sin(2 * i / tamanho * math.tau) * 0.25
            for i in range(tamanho)
        ]
    return [_onda(tipo, i / tamanho, duty) for i in range(tamanho)]


# ============================================================
# NOTAS
# ============================================================

def nota(buf, inicio, n, freq, tipo="quadrada", vol=0.2, duty=0.5,
         envelope="normal", deslize=0.0):
    """
    Soma uma nota no buffer.

    envelope:
      normal   -> ataque rápido, sustenta e solta no fim
      pluck    -> decai (tipo corda beliscada / sininho)
      staccato -> nota curtinha
    deslize: variação de frequência (em oitavas) ao longo da nota
    """
    tab = _tabela(tipo, duty)
    tam = len(tab)
    total = len(buf)

    if envelope == "staccato":
        n = max(1, int(n * 0.55))

    ataque = max(1, int(0.004 * TAXA))
    soltura = max(1, min(n // 3, int(0.05 * TAXA)))

    if envelope == "pluck":
        decai = math.exp(-5.5 / max(1, n))
    else:
        decai = 1.0

    fase = 0.0
    inc = freq * tam / TAXA
    mult_inc = 2 ** (deslize / max(1, n)) if deslize else 1.0
    env_pluck = 1.0
    fim = min(n, total - inicio)

    for i in range(fim):
        if i < ataque:
            e = i / ataque
        elif i > n - soltura:
            e = (n - i) / soltura
        else:
            e = 1.0

        if envelope == "pluck":
            env_pluck *= decai
            e *= env_pluck

        buf[inicio + i] += tab[int(fase) % tam] * e * vol
        fase += inc
        inc *= mult_inc


def sequencia(buf, seq, passo, **kw):
    """Toca uma sequência de notas (ver notação no topo)."""
    pos = 0

    for tok in seq.split():
        if tok == "|":
            continue

        nome, _, d = tok.partition("*")
        dur = int(d) if d else 1
        n = int(dur * passo)

        if nome != ".":
            if "+" in nome:
                # Acorde: "C4+E4+G4"
                partes = nome.split("+")
                vol = kw.get("vol", 0.2) / len(partes) * 1.6
                args = dict(kw, vol=vol)
                for p in partes:
                    nota(buf, pos, n, frequencia(p), **args)
            else:
                nota(buf, pos, n, frequencia(nome), **kw)

        pos += n

    return pos


# ============================================================
# BATERIA
# ============================================================

def _bumbo():
    n = int(0.16 * TAXA)
    fase = 0.0
    out = []
    for i in range(n):
        t = i / n
        f = 150 * (1 - t) + 45 * t
        fase += f / TAXA
        out.append(math.sin(fase * math.tau) * (1 - t) ** 2 * 0.9)
    return out


def _caixa():
    rnd = random.Random(7)
    n = int(0.13 * TAXA)
    out = []
    ant = 0.0
    for i in range(n):
        t = i / n
        ruido = rnd.uniform(-1, 1)
        ant = ant * 0.4 + ruido * 0.6
        tom = math.sin(i * 190 * math.tau / TAXA)
        out.append((ant * 0.55 + tom * 0.3) * (1 - t) ** 2.5)
    return out


def _chimbal():
    rnd = random.Random(3)
    n = int(0.035 * TAXA)
    out = []
    ant = 0.0
    for i in range(n):
        t = i / n
        r = rnd.uniform(-1, 1)
        out.append((r - ant) * 0.35 * (1 - t) ** 3)
        ant = r
    return out


def _clap():
    rnd = random.Random(11)
    n = int(0.12 * TAXA)
    out = []
    for i in range(n):
        t = i / n
        pulso = 1.0 if (i % int(0.012 * TAXA)) < int(0.006 * TAXA) or t > 0.2 else 0.3
        out.append(rnd.uniform(-1, 1) * 0.4 * (1 - t) ** 3 * pulso)
    return out


_BATERIA = {}


def bateria(buf, padrao, passo, vol=1.0):
    """
    padrao: dict com 'k' (bumbo), 's' (caixa), 'h' (chimbal), 'c' (palma)
    Cada um é uma string onde 'x' toca e '.' não toca, um caractere
    por passo. A string se repete até preencher o buffer.
    """
    if not _BATERIA:
        _BATERIA.update(k=_bumbo(), s=_caixa(), h=_chimbal(), c=_clap())

    total = len(buf)

    for peca, ritmo in padrao.items():
        ritmo = ritmo.replace(" ", "").replace("|", "")
        amostra = _BATERIA[peca]
        passos = int(total / passo)

        for p in range(passos):
            if ritmo[p % len(ritmo)] != "x":
                continue
            inicio = int(p * passo)
            for i, v in enumerate(amostra):
                if inicio + i >= total:
                    break
                buf[inicio + i] += v * vol


# ============================================================
# EFEITOS / FINALIZAÇÃO
# ============================================================

def eco(buf, atraso_s=0.18, forca=0.25):
    d = int(atraso_s * TAXA)
    for i in range(d, len(buf)):
        buf[i] += buf[i - d] * forca


def para_pcm(buf, pico=0.85):
    """Normaliza e converte para 16 bits."""
    maior = max(1e-6, max(abs(v) for v in buf))
    escala = pico * 32767 / maior
    return array.array("h", (int(v * escala) for v in buf))


def salvar_wav(caminho, pcm):
    with wave.open(caminho, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(TAXA)
        w.writeframes(pcm.tobytes())


def wav_em_memoria(pcm):
    bio = io.BytesIO()
    with wave.open(bio, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(TAXA)
        w.writeframes(pcm.tobytes())
    bio.seek(0)
    return bio


def buffer_vazio(segundos):
    return [0.0] * int(segundos * TAXA)
