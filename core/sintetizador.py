import array
import io
import math
import wave

# ============================================================
# SINTETIZADOR SIMPLES (PYTHON PURO)
# ============================================================
# Gera notas curtas na hora, sem arquivos de áudio (usado pelos
# cantores do Coral dos Ovos). As músicas e os efeitos sonoros do
# jogo são MP3 (ver ferramentas/compor_musicas.py).

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


# ============================================================
# FINALIZAÇÃO
# ============================================================

def para_pcm(buf, pico=0.85):
    """Normaliza e converte para 16 bits."""
    maior = max(1e-6, max(abs(v) for v in buf))
    escala = pico * 32767 / maior
    return array.array("h", (int(v * escala) for v in buf))


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
