import os
import threading
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


# Temas das telas do jogo (tela inicial, rua, loja...). Também
# aparecem na JUKEBOX (seção TEMAS) depois de ouvidos uma vez.
TEMAS = {
    # TELA INICIAL — abertura alegre
    "abertura": dict(bpm=112, tom="C", escala="lidia", lead="quadrada", duty=0.25,
                     envelope="normal", baixo="pop", onda_baixo="triangulo",
                     acomp="arpejo16", onda_acomp="sino", bateria="pop",
                     energia=0.55, eco=(0.2, 0.22), vol_acomp=0.06),
    # VIZINHANÇA (dia) — passeio tranquilo
    "rua_dos_ovos": dict(bpm=100, tom="G", escala="pentatonica", lead="sino",
                         envelope="pluck", baixo="walking", onda_baixo="triangulo",
                         acomp="contratempo", onda_acomp="triangulo", bateria="shuffle",
                         energia=0.4, eco=(0.25, 0.22), vol_bateria=0.35),
    # VIZINHANÇA (noite)
    "rua_noite": dict(bpm=72, tom="A", escala="dorica", lead="seno", envelope="normal",
                      baixo="longo", onda_baixo="seno", acomp="pad", onda_acomp="triangulo",
                      bateria="suave", energia=0.2, eco=(0.35, 0.35),
                      vol_bateria=0.2, vol_lead=0.18),
    # CHUVA
    "dia_de_chuva": dict(bpm=86, tom="E", escala="dorica", lead="triangulo",
                         envelope="normal", baixo="pop", onda_baixo="seno",
                         acomp="arpejo8", onda_acomp="sino", bateria="halftime",
                         energia=0.3, eco=(0.3, 0.3), vol_bateria=0.3),
    # REFORMA
    "maos_a_obra": dict(bpm=124, tom="F", escala="mixolidia", lead="quadrada", duty=0.5,
                        envelope="staccato", baixo="oompah", onda_baixo="triangulo",
                        acomp="chop", onda_acomp="quadrada", bateria="marcha",
                        energia=0.6, eco=(0.12, 0.15)),
    # LOJA
    "vitrine": dict(bpm=104, tom="Ab", escala="maior", lead="sino", envelope="pluck",
                    baixo="sincopado", onda_baixo="triangulo", acomp="contratempo",
                    onda_acomp="sino", bateria="reggae", energia=0.45,
                    eco=(0.22, 0.25), vol_bateria=0.4),
    # NOME + CRIADOR
    "nasce_um_ovo": dict(bpm=96, tom="Db", escala="maior", lead="triangulo",
                         envelope="normal", baixo="pop", onda_baixo="seno",
                         acomp="arpejo8", onda_acomp="sino", bateria="suave",
                         energia=0.35, eco=(0.3, 0.28)),
    # CASA com a luz apagada
    "cancao_de_ninar": dict(bpm=66, tom="F", escala="pentatonica", lead="sino",
                            envelope="pluck", baixo="longo", onda_baixo="seno",
                            acomp="arpejo8", onda_acomp="triangulo", bateria="nenhuma",
                            energia=0.15, eco=(0.4, 0.35), vol_lead=0.18, vol_acomp=0.05),
    # SOL (quintal, de dia)
    "quintal_feliz": dict(bpm=118, tom="A", escala="mixolidia", lead="quadrada", duty=0.125,
                          envelope="pluck", baixo="tropical", onda_baixo="triangulo",
                          acomp="arpejo8", onda_acomp="sino", bateria="baiao",
                          energia=0.5, eco=(0.18, 0.2)),
}

NOMES_TEMAS = {
    "ovein": "TEMA DO OVAL",
    "abertura": "ABERTURA",
    "rua_dos_ovos": "RUA DOS OVOS",
    "rua_noite": "RUA DOS OVOS (NOITE)",
    "dia_de_chuva": "DIA DE CHUVA",
    "maos_a_obra": "MÃOS À OBRA",
    "vitrine": "VITRINE",
    "nasce_um_ovo": "NASCE UM OVO",
    "cancao_de_ninar": "CANÇÃO DE NINAR",
    "quintal_feliz": "QUINTAL FELIZ",
}

DICAS_TEMAS = {
    "cancao_de_ninar": "DICA: APAGUE A LUZ PARA DORMIR",
    "dia_de_chuva": "DICA: ESPERE UM DIA DE CHUVA",
    "rua_noite": "DICA: VISITE A RUA DE NOITE",
    "quintal_feliz": "DICA: VÁ AO QUINTAL DE DIA",
    "vitrine": "DICA: VISITE A LOJA",
    "maos_a_obra": "DICA: REFORME SUA CASA",
}

for _nome, _estilo in TEMAS.items():
    ESTILOS[_nome] = dict(_estilo)


def _assinatura(nome):
    """Muda quando o estilo muda, para regenerar a música."""
    estilo = ESTILOS[nome]
    return f"{zlib.crc32(repr(sorted(estilo.items())).encode()):08x}"[:6]


def arquivo(nome):
    if nome not in TRILHAS and nome in ESTILOS:
        base = f"{nome}_{_assinatura(nome)}.wav"
    else:
        base = nome + ".wav"
    # Trilha que já veio pronta com o jogo? Senão, a pasta das geradas
    pronta = os.path.join(PASTA_TRILHAS, base)
    if PASTA_TRILHAS_GERADAS == PASTA_TRILHAS or os.path.exists(pronta):
        return pronta
    return os.path.join(PASTA_TRILHAS_GERADAS, base)


def existe(nome):
    return nome in TRILHAS or nome in ESTILOS


def gerar(nome):
    os.makedirs(PASTA_TRILHAS_GERADAS, exist_ok=True)

    if nome in TRILHAS:
        buf = TRILHAS[nome]()
    else:
        from core.compositor import compor_estilo
        buf = compor_estilo(ESTILOS[nome], semente=zlib.crc32(nome.encode()))

        # Apaga versões antigas desta trilha
        for arq in os.listdir(PASTA_TRILHAS_GERADAS):
            if arq.startswith(nome + "_") and arq.endswith(".wav"):
                try:
                    os.remove(os.path.join(PASTA_TRILHAS_GERADAS, arq))
                except OSError:
                    pass

    # Grava num temporário e troca: o mixer nunca abre um wav pela metade
    destino = arquivo(nome)
    temp = f"{destino}.{os.getpid()}.tmp"
    s.salvar_wav(temp, s.para_pcm(buf, 0.8))
    os.replace(temp, destino)


# ------------------------------------------------------------
# Geração em segundo plano (se alguma trilha não veio pronta)
# ------------------------------------------------------------

_fila = []
_trava = threading.Lock()
_thread = None
FALHARAM = set()


def _trabalhador():
    global _thread
    while True:
        with _trava:
            if not _fila:
                _thread = None
                return
            nome = _fila.pop(0)
        try:
            if not os.path.exists(arquivo(nome)):
                gerar(nome)
        except Exception:
            FALHARAM.add(nome)


def gerar_em_fundo(nome):
    """Põe a trilha na fila da thread de fundo (não trava a tela)."""
    global _thread
    with _trava:
        if nome in _fila or nome in FALHARAM:
            return
        _fila.append(nome)
        if _thread is None:
            _thread = threading.Thread(target=_trabalhador, daemon=True)
            _thread.start()


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
