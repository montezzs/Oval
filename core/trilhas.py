import os
import zlib

from settings import *
from core import sintetizador as s

# ============================================================
# TRILHAS SONORAS DOS MINI JOGOS
# ============================================================
# Cada trilha é composta aqui mesmo (notas, baixo, bateria) e
# gerada pelo sintetizador. O arquivo .wav fica salvo em
# musicas/trilhas para não precisar gerar de novo.


# ------------------------------------------------------------
# AJUDANTES DE COMPOSIÇÃO
# ------------------------------------------------------------

def _oitava(nota, n=1):
    return s.transpor(nota, 12 * n)


def baixo_rock(raizes):
    """Raiz e oitava alternando em colcheias."""
    partes = []
    for r in raizes:
        partes.append(f"{r}*2 {_oitava(r)}*2 " * 4)
    return " ".join(partes)


def baixo_pop(acordes):
    """(raiz, quinta) -> padrão pop de 16 passos."""
    partes = []
    for r, q in acordes:
        partes.append(f"{r}*2 {r}*2 {q}*2 {r}*2 {_oitava(r)}*2 {q}*2 {r}*2 {q}*2")
    return " ".join(partes)


def baixo_oompah(acordes):
    """Baixo saltitante (raiz / quinta)."""
    partes = []
    for r, q in acordes:
        partes.append(f"{r}*2 . . {q}*2 . . {r}*2 . . {q}*2 . .")
    return " ".join(partes)


def baixo_tropical(acordes):
    partes = []
    for r, q in acordes:
        partes.append(f"{r}*3 {r} . {r}*2 {q}*2 {r}*3 {q} {_oitava(r)}*2 .")
    return " ".join(partes)


def baixo_misterio(acordes):
    partes = []
    for r, q in acordes:
        partes.append(f"{r}*3 {r} {r}*2 {q}*2 {r}*3 {r} {r}*2 {_oitava(r)}*2")
    return " ".join(partes)


def arpejo16(acordes):
    """Cada acorde (lista de 4 notas) repetido em semicolcheias."""
    return " ".join(" ".join(ac) + " " + " ".join(ac) + " " +
                    " ".join(ac) + " " + " ".join(ac) for ac in acordes)


def arpejo8(acordes):
    """Acorde (4 notas) em colcheias: 1 2 3 2 1 2 3 2."""
    partes = []
    for a, b, c, d in acordes:
        partes.append(f"{a}*2 {b}*2 {c}*2 {b}*2 {a}*2 {b}*2 {d}*2 {b}*2")
    return " ".join(partes)


def acordes_sustentados(acordes):
    return " ".join("+".join(ac) + "*16" for ac in acordes)


def contratempo(acordes):
    """Acorde tocado no contratempo (estilo reggae / praia)."""
    return " ".join(
        f".*2 {'+'.join(ac)}*2 " * 4 for ac in acordes
    )


def _passos(seq):
    total = 0
    for tok in seq.split():
        if tok == "|":
            continue
        _, _, d = tok.partition("*")
        total += int(d) if d else 1
    return total


def compor(bpm, compassos, vozes, bateria=None, vol_bateria=0.6,
           eco=(0.0, 0.0)):
    passo = s.TAXA * 60 / bpm / 4
    total_passos = compassos * 16
    buf = [0.0] * int(total_passos * passo)

    for seq, opcoes in vozes:
        n = _passos(seq)
        if n != total_passos:
            raise ValueError(f"voz com {n} passos (esperado {total_passos}): {seq[:40]}")
        s.sequencia(buf, seq, passo, **opcoes)

    if bateria:
        s.bateria(buf, bateria, passo, vol_bateria)

    if eco[0]:
        s.eco(buf, *eco)

    return buf


# ============================================================
# COMPOSIÇÕES
# ============================================================

def trilha_jogos():
    """Menu de jogos: arcade alegre em Dó maior."""
    C, Am, F, G = ["C4", "E4", "G4", "C5"], ["A3", "C4", "E4", "A4"], \
                  ["F3", "A3", "C4", "F4"], ["G3", "B3", "D4", "G4"]
    melodia = (
        "E5*2 G5*2 C6*3 B5 A5*2 G5*2 E5*4 | "
        "A5*2 C6*2 E6*3 D6 C6*2 B5*2 A5*4 | "
        "F5*2 A5*2 C6*2 A5*2 G5*2 F5*2 E5*2 F5*2 | "
        "G5*3 A5 B5*2 D6*2 G5*8 | "
        "C6*2 . C6 B5*2 C6*2 E6*4 D6*2 C6*2 | "
        "A5*2 . A5 G5*2 A5*2 C6*4 B5*2 A5*2 | "
        "F5*2 G5*2 A5*2 C6*2 D6*2 C6*2 A5*2 F5*2 | "
        "G5*2 B5*2 D6*2 F6*2 E6*4 D6*2 B5*2"
    )
    progressao = [C, Am, F, G] * 2
    baixo = baixo_pop([("C3", "G2"), ("A2", "E3"), ("F2", "C3"), ("G2", "D3")] * 2)
    return compor(132, 8, [
        (melodia, dict(tipo="quadrada", duty=0.25, vol=0.20)),
        (baixo, dict(tipo="triangulo", vol=0.32, envelope="staccato")),
        (arpejo16(progressao), dict(tipo="quadrada", duty=0.125, vol=0.05,
                                    envelope="pluck")),
    ], bateria={"k": "x.......x.x.....", "s": "....x.......x...",
                "h": "x.x.x.x.x.x.x.x."}, vol_bateria=0.55, eco=(0.17, 0.2))


def trilha_cobrinha():
    """Cobrinha: jardim saltitante em Sol maior."""
    G, Em, C, D = ["G4", "B4", "D5", "G5"], ["E4", "G4", "B4", "E5"], \
                  ["C4", "E4", "G4", "C5"], ["D4", "F#4", "A4", "D5"]
    melodia = (
        "D5 . G5 . B5 . G5 . A5 . B5 . D6*2 . . | "
        "E5 . G5 . B5 . E6*2 D6 . B5 . G5*2 . . | "
        "C5 . E5 . G5 . C6*2 B5 . A5 . G5*2 E5*2 | "
        "D5 . F#5 . A5 . D6*2 C6 . A5 . F#5*4 | "
        "B5 . B5 . A5 . G5 . A5 . B5 . G5*4 | "
        "G5 . G5 . F#5 . E5 . F#5 . G5 . E5*4 | "
        "E5 . G5 . C6 . E6 . D6 . C6 . A5 . G5 . | "
        "F#5 . A5 . D6*2 C6 . B5*2 A5*2 F#5*4"
    )
    progressao = [G, Em, C, D] * 2
    baixo = baixo_oompah([("G2", "D3"), ("E2", "B2"), ("C3", "G2"), ("D3", "A2")] * 2)
    return compor(144, 8, [
        (melodia, dict(tipo="quadrada", duty=0.5, vol=0.18, envelope="staccato")),
        (baixo, dict(tipo="triangulo", vol=0.35)),
        (arpejo8(progressao), dict(tipo="sino", vol=0.07, envelope="pluck")),
    ], bateria={"k": "x...x...x...x...", "s": "....x.......x...",
                "h": "..x...x...x...x."}, vol_bateria=0.5, eco=(0.14, 0.18))


def trilha_minado():
    """Campo minado: misterioso, mas fofo, em Lá menor."""
    Am, F, Dm, E = ["A3", "C4", "E4"], ["F3", "A3", "C4"], \
                   ["D3", "F3", "A3"], ["E3", "G#3", "B3"]
    melodia = (
        "A4*2 C5*2 E5*2 A5*4 G5*2 E5*4 | "
        "F5*2 E5*2 C5*2 A4*6 .*4 | "
        "D5*2 F5*2 A5*2 D6*4 C6*2 A5*4 | "
        "B5*2 G#5*2 E5*2 B4*6 G#4*4 | "
        "E5*2 A5*2 C6*2 B5*2 A5*2 E5*2 C5*4 | "
        "F5*2 A5*2 C6*2 A5*2 F5*2 C5*2 A4*4 | "
        "D5*2 F5*2 E5*2 D5*2 C5*2 D5*2 F5*4 | "
        "E5*4 G#5*4 B5*4 E6*4"
    )
    progressao = [Am, F, Dm, E] * 2
    baixo = baixo_misterio([("A2", "E2"), ("F2", "C3"), ("D2", "A2"), ("E2", "B2")] * 2)
    return compor(104, 8, [
        (melodia, dict(tipo="sino", vol=0.30, envelope="pluck")),
        (baixo, dict(tipo="triangulo", vol=0.30, envelope="staccato")),
        (acordes_sustentados(progressao), dict(tipo="triangulo", vol=0.10)),
    ], bateria={"k": "x.........x.....", "s": "........x.......",
                "h": "x.x.x.x.x.x.x.x."}, vol_bateria=0.35, eco=(0.29, 0.3))


def trilha_volei():
    """Vôlei de praia: clima tropical em Fá maior."""
    F, Bb, C, Dm = ["F4", "A4", "C5"], ["Bb3", "D4", "F4"], \
                   ["C4", "E4", "G4"], ["D4", "F4", "A4"]
    melodia = (
        "C5*2 F5*2 A5*2 C6*2 A5*3 G5 F5*4 | "
        "D5*2 F5*2 Bb5*2 D6*2 C6*3 Bb5 A5*4 | "
        "E5*2 G5*2 C6*2 E6*2 D6*3 C6 Bb5*2 G5*2 | "
        "A5*6 G5*2 F5*8 | "
        "D6*2 C6*2 A5*2 F5*2 A5*3 C6 D6*4 | "
        "D6*2 C6*2 Bb5*2 F5*2 Bb5*3 C6 D6*4 | "
        "E6*2 D6*2 C6*2 G5*2 C6*3 D6 E6*4 | "
        "G5*2 A5*2 Bb5*2 C6*2 E6*4 C6*4"
    )
    progressao = [F, Bb, C, F, Dm, Bb, C, C]
    baixo = baixo_tropical([("F2", "C3"), ("Bb2", "F2"), ("C3", "G2"), ("F2", "C3"),
                            ("D2", "A2"), ("Bb2", "F2"), ("C3", "G2"), ("C3", "G2")])
    return compor(120, 8, [
        (melodia, dict(tipo="sino", vol=0.30, envelope="pluck")),
        (baixo, dict(tipo="triangulo", vol=0.32)),
        (contratempo(progressao), dict(tipo="quadrada", duty=0.25, vol=0.07,
                                       envelope="staccato")),
    ], bateria={"k": "x.....x...x.....", "s": "....x.......x...",
                "h": "x.xxx.xxx.xxx.xx"}, vol_bateria=0.45, eco=(0.2, 0.2))


def trilha_pulo():
    """Pulo nas nuvens: sonhador e ascendente em Ré maior."""
    D, A, Bm, G = ["D5", "F#5", "A5", "D6"], ["C#5", "E5", "A5", "C#6"], \
                  ["B4", "D5", "F#5", "B5"], ["G4", "B4", "D5", "G5"]
    melodia = (
        "F#5*6 E5*2 D5*4 A5*4 | "
        "E5*6 F#5*2 E5*4 C#5*4 | "
        "D5*6 E5*2 F#5*4 B5*4 | "
        "A5*6 G5*2 F#5*4 E5*4 | "
        "A5*4 D6*4 C#6*4 A5*4 | "
        "E6*6 C#6*2 A5*8 | "
        "B5*4 D6*4 F#6*4 E6*4 | "
        "D6*6 B5*2 A5*8"
    )
    progressao = [D, A, Bm, G] * 2
    baixo = baixo_rock(["D2", "A2", "B2", "G2"] * 2)
    return compor(150, 8, [
        (melodia, dict(tipo="triangulo", vol=0.32)),
        (arpejo16(progressao), dict(tipo="sino", vol=0.09, envelope="pluck")),
        (baixo, dict(tipo="quadrada", duty=0.5, vol=0.09, envelope="staccato")),
    ], bateria={"k": "x...x...x...x...", "s": "....x.......x...",
                "h": "..x...x...x...x."}, vol_bateria=0.45, eco=(0.2, 0.3))


def trilha_chuva():
    """Chuva de comida: funk de cozinha em Mi menor."""
    Em7, A7 = ["E4", "G4", "B4", "D5"], ["A3", "C#4", "E4", "G4"]
    baixo = (
        "E2*2 . E3 . E2 . D3 E2*2 . G2 A2 . B2 . | "
        "A2*2 . A3 . A2 . G3 A2*2 . C#3 D3 . E3 . | "
    ) * 4
    chop = " ".join(
        f". . {'+'.join(ac)} . . {'+'.join(ac)} . . {'+'.join(ac)} . . "
        f"{'+'.join(ac)} . {'+'.join(ac)} . ."
        for ac in [Em7, A7] * 4
    )
    melodia = (
        "B4 . D5 . E5*2 . G5 E5*2 D5 . B4*4 | "
        "A4 . C#5 . E5*2 . G5 F#5*2 E5 . C#5*4 | "
        "E5 E5 . G5 . A5 . B5*3 A5 G5 E5*4 | "
        "G5*2 F#5*2 E5*2 C#5*2 A4*8 | "
        "B5 . B5 . A5 . G5 . E5*2 G5*2 A5*4 | "
        "G5 . G5 . F#5 . E5 . C#5*2 E5*2 A4*4 | "
        "E6*2 D6*2 B5*2 A5*2 G5*2 A5*2 B5*4 | "
        "A5*2 G5*2 F#5*2 E5*2 C#5*2 D5*2 E5*4"
    )
    return compor(112, 8, [
        (melodia, dict(tipo="quadrada", duty=0.25, vol=0.17)),
        (baixo, dict(tipo="serra", vol=0.20, envelope="staccato")),
        (chop, dict(tipo="quadrada", duty=0.5, vol=0.06, envelope="staccato")),
    ], bateria={"k": "x.....x...x.....", "s": "....x.......x...",
                "h": "x.xxx.x.x.xxx.x.", "c": "............x..."},
        vol_bateria=0.55, eco=(0.13, 0.15))


def trilha_memoria():
    """Memória: caixinha de música calma em Dó maior."""
    C, G, Am, F = ["C4", "G4", "E5", "C5"], ["B3", "G4", "D5", "B4"], \
                  ["A3", "E4", "C5", "A4"], ["F3", "C4", "A4", "F4"]
    melodia = (
        "E6*4 D6*2 C6*2 G5*8 | "
        "D6*4 C6*2 B5*2 G5*8 | "
        "C6*4 B5*2 A5*2 E5*4 A5*4 | "
        "A5*4 G5*2 F5*2 C5*8 | "
        "E5*2 G5*2 C6*4 E6*4 D6*4 | "
        "D6*2 B5*2 G5*4 B5*4 D6*4 | "
        "C6*2 E6*2 A6*4 G6*4 E6*4 | "
        "F6*4 E6*2 D6*2 C6*8"
    )
    progressao = [C, G, Am, F] * 2
    pad = acordes_sustentados([["C4", "E4", "G4"], ["B3", "D4", "G4"],
                               ["A3", "C4", "E4"], ["A3", "C4", "F4"]] * 2)
    return compor(88, 8, [
        (melodia, dict(tipo="sino", vol=0.30, envelope="pluck")),
        (arpejo8(progressao), dict(tipo="sino", vol=0.10, envelope="pluck")),
        (pad, dict(tipo="triangulo", vol=0.07)),
    ], bateria={"h": "x...x...x...x..."}, vol_bateria=0.3, eco=(0.34, 0.35))


def trilha_voador():
    """Ovo voador: aventura acelerada em Mi menor."""
    Em, C, G, D = ["E4", "G4", "B4", "E5"], ["C4", "E4", "G4", "C5"], \
                  ["G4", "B4", "D5", "G5"], ["D4", "F#4", "A4", "D5"]
    melodia = (
        "E5*2 G5*2 B5*4 A5*2 G5*2 F#5*2 G5*2 | "
        "E5*2 G5*2 C6*4 B5*2 A5*2 G5*4 | "
        "D5*2 G5*2 B5*4 D6*4 B5*4 | "
        "A5*4 F#5*4 D5*4 F#5*4 | "
        "B5*2 B5*2 E6*4 D6*2 B5*2 G5*4 | "
        "C6*2 C6*2 E6*4 D6*2 C6*2 G5*4 | "
        "B5*2 D6*2 G6*4 F#6*2 E6*2 D6*4 | "
        "F#6*4 E6*4 D6*4 A5*4"
    )
    progressao = [Em, C, G, D] * 2
    baixo = baixo_rock(["E2", "C2", "G2", "D2"] * 2)
    return compor(160, 8, [
        (melodia, dict(tipo="quadrada", duty=0.5, vol=0.16)),
        (baixo, dict(tipo="triangulo", vol=0.34, envelope="staccato")),
        (arpejo16(progressao), dict(tipo="quadrada", duty=0.125, vol=0.05,
                                    envelope="pluck")),
    ], bateria={"k": "x...x...x...x...", "s": "....x.......x...",
                "h": "xxxxxxxxxxxxxxxx"}, vol_bateria=0.5, eco=(0.19, 0.18))


TRILHAS = {
    "jogos": trilha_jogos,
    "cobrinha": trilha_cobrinha,
    "minado": trilha_minado,
    "volei": trilha_volei,
    "pulo": trilha_pulo,
    "chuva": trilha_chuva,
    "memoria": trilha_memoria,
    "voador": trilha_voador,
}


# Estilos das trilhas procedurais (registrados pelos mini jogos
# que declaram TRILHA = dict(...); ver core/compositor.py)
ESTILOS = {}


def registrar(nome, estilo):
    ESTILOS[nome] = dict(estilo)


def _assinatura(nome):
    """Muda quando o estilo muda, para regenerar a música."""
    estilo = ESTILOS[nome]
    return f"{zlib.crc32(repr(sorted(estilo.items())).encode()):08x}"[:6]


def arquivo(nome):
    if nome not in TRILHAS and nome in ESTILOS:
        return os.path.join(PASTA_TRILHAS, f"{nome}_{_assinatura(nome)}.wav")
    return os.path.join(PASTA_TRILHAS, nome + ".wav")


def existe(nome):
    return nome in TRILHAS or nome in ESTILOS


def gerar(nome):
    os.makedirs(PASTA_TRILHAS, exist_ok=True)

    if nome in TRILHAS:
        buf = TRILHAS[nome]()
    else:
        from core.compositor import compor_estilo
        buf = compor_estilo(ESTILOS[nome], semente=zlib.crc32(nome.encode()))

        # Apaga versões antigas desta trilha
        for arq in os.listdir(PASTA_TRILHAS):
            if arq.startswith(nome + "_") and arq.endswith(".wav"):
                try:
                    os.remove(os.path.join(PASTA_TRILHAS, arq))
                except OSError:
                    pass

    s.salvar_wav(arquivo(nome), s.para_pcm(buf, 0.8))


if __name__ == "__main__":
    # Gera todas as trilhas (fixas + as dos mini jogos):
    #   python -m core.trilhas
    import time

    import pygame
    pygame.init()
    from jogos import JOGOS
    for jogo in JOGOS:
        if getattr(jogo, "TRILHA", None):
            registrar(jogo.ID, jogo.TRILHA)

    for nome in list(TRILHAS) + list(ESTILOS):
        if os.path.exists(arquivo(nome)):
            continue
        t = time.time()
        gerar(nome)
        print(f"{nome}: {time.time() - t:.1f}s")
