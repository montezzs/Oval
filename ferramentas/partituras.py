from ferramentas.compor_musicas import (
    BATERIAS, PASSO, Partitura, ler_progressao, tocar_acomp, tocar_baixo, tocar_bateria,
)

# ============================================================
# PARTITURAS DO OVAL
# ============================================================
# Cada música: tonalidade, instrumentos (General MIDI), estilos de
# baixo/acompanhamento/bateria, progressões e melodias.
#
# Forma padrão: intro (Tema do Oval) - A - B - A' (+ B' se a música
# for rápida). A = a + a[:2] + fimA; B = b + b[:2] + fimB.
# As progressões A e B têm 8 compassos (os 5-6 repetem os 1-2).


def I(programa, vol=100, pan=64, rev=40, cho=0, art=0.92, humano=4, bend=2):
    return dict(programa=programa, vol=vol, pan=pan, rev=rev, cho=cho, art=art,
                humano=humano, bend=bend)


def K(kit=0, vol=100, rev=22):
    return I(kit, vol, 64, rev, 0, 1.0, 2)


# Programas GM (0 = piano)
PIANO, EPIANO, CRAVO, CLAV, CELESTA, GLOCK, CAIXINHA, VIBRAFONE, MARIMBA, XILOFONE = \
    0, 4, 6, 7, 8, 9, 10, 11, 12, 13
SINOS, ORGAO, ORGAO_IGREJA, GAITA = 14, 16, 19, 22
VIOLAO, VIOLAO_ACO, GUIT_LIMPA, GUIT_OVER, GUIT_DIST = 24, 25, 27, 29, 30
BAIXO_AC, BAIXO_DEDO, BAIXO_PALHETA, FRETLESS, SLAP, SLAP2, SYNBAIXO, SYNBAIXO2 = \
    32, 33, 34, 35, 36, 37, 38, 39
CELLO, PIZZ, HARPA, TIMPANO, CORDAS, CORDAS_LENTAS, CORO, VOZ = 42, 45, 46, 47, 48, 49, 52, 53
TROMPETE, TROMBONE, TUBA, SURDINA, TROMPA, METAIS, SYNMETAIS = 56, 57, 58, 59, 60, 61, 62
SAX_TENOR, FAGOTE, CLARINETE, FLAUTA, FLAUTA_PAN, SHAKUHACHI, OCARINA = 66, 70, 71, 73, 75, 77, 79
QUADRADA, SERRA, CALLIOPE = 80, 81, 82
PAD_NEWAGE, PAD_QUENTE, PAD_POLY, PAD_CORO, PAD_SWEEP, ATMOSFERA = 88, 89, 90, 91, 95, 99
BANJO, SHAMISEN, KOTO, KALIMBA, RABECA, STEEL, TAIKO = 105, 106, 107, 108, 110, 114, 116

# Kits de bateria
STANDARD, ROOM, POWER, ELETRONICO, TR808, JAZZ, ESCOVA, ORQUESTRA = 0, 8, 16, 24, 25, 32, 40, 48

BATERIAS.update({
    "neve": dict(k="x.......x.......", s="....x.......x...", b="x.x.x.x.x.x.x.x.",
                 fill=dict(k="x.......x.......", s="....x...x.x.xxxx", b="xxxxxxxxxxxxxxxx")),
    "bolhas": dict(k="x.....x...x.....", c="....x.......x...", j="..x.....x..x..x.",
                   h="x.x.x.x.x.x.x.x.", fill=dict(k="x.....x...x.....", j="..x.....xxxxxxxx")),
})


MUSICAS = {}


def musica(nome, **d):
    MUSICAS[nome] = d


# ============================================================
# CASA E MENUS
# ============================================================

# Casa: aconchegante (piano, celesta, harpa, cordas). O tema A É o
# Tema do Oval, desenvolvido em sequência.
musica(
    "casa", bpm=84, tonica="F5", modo="maior", lufs=-18,
    inst=dict(lead=I(PIANO, 105, 58, 55), sino=I(CELESTA, 92, 76, 60),
              acomp=I(HARPA, 70, 44, 55), pad=I(CORDAS_LENTAS, 62, 64, 70, 30),
              contra=I(CELLO, 66, 84, 55), baixo=I(BAIXO_AC, 78, 64, 25),
              bat=K(ESCOVA, 60)),
    baixo="meio", acomp="arpejo8", centro_acomp=60, bat="calmo", dobra=12,
    reg_contra=(48, 62), vel_bat=0.7,
    perfis={"intro": {"acomp": True}}, melIntro="",
    progA="Fmaj7 | Am7 | Bbmaj7 | C7 | Fmaj7 | Am7 | Bbmaj7 Gm7 | Csus4 C",
    a="C5*2 F5*2 A5*3 G5 F5*2 C6*6 | D6*2 C6*2 A5*4 G5*8 | "
      "F5*2 Bb5*2 D6*3 C6 Bb5*2 F6*6 | E6*2 D6*2 C6*4 Bb5*2 G5*2 E5*4",
    fimA="F5*2 Bb5*2 D6*4 C6*2 Bb5*2 G5*4 | F5*4 G5*4 E5*8",
    progB="Dm7 | Bbmaj7 | Gm7 | C7 | Dm7 | Bbmaj7 | Gm7 C7 | Fmaj7",
    b="A5*6 G5*2 F5*4 E5*2 D5*2 | F5*6 E5*2 D5*8 | Bb4*2 D5*2 F5*2 A5*2 G5*8 | "
      "G5*4 E5*4 C5*4 Bb4*4",
    fimB="D5*2 F5*2 Bb5*4 G5*2 Bb5*2 E5*4 | F5*12 .*4",
)

# Menu de jogos / loja: pop de fliperama (trompete + xilofone)
musica(
    "jogos", bpm=128, tonica="C5", modo="maior",
    inst=dict(lead=I(TROMPETE, 98, 60, 40), sino=I(XILOFONE, 100, 72, 40),
              dobra=I(XILOFONE, 88, 74, 40), acomp=I(GUIT_LIMPA, 74, 40, 35, 20, 0.6),
              pad=I(CORDAS, 50, 64, 50), contra=I(METAIS, 62, 86, 45),
              baixo=I(SLAP, 96, 64, 15), bat=K(STANDARD)),
    baixo="sincopado", acomp="pop", bat="pop", dobra=12,
    progA="C | Am7 | Dm7 G7 | Em7 A7 | C | Am7 | F G | C",
    a="E5*3 G5*3 C6*2 B5*2 C6*2 G5*4 | A5*3 C6*3 E6*2 D6*2 C6*2 A5*4 | "
      "F5*2 A5*2 D6*2 C6*2 B5*2 G5*2 F5*2 D5*2 | E5*4 G5*2 B5*2 C#6*4 A5*4",
    fimA="A5*2 C6*2 F6*2 E6*2 D6*2 B5*2 G5*2 F5*2 | E5*2 G5*2 C6*8 .*4",
    progB="F | G | Em7 | Am7 | F | G | Dm7 | Gsus4 G7",
    b="A5*2 A5*2 G5*2 A5*4 C6*2 A5*4 | B5*2 B5*2 A5*2 B5*4 D6*2 B5*4 | "
      "G5*2 E5*2 B4*2 E5*2 G5*2 B5*2 D6*4 | C6*6 B5*2 A5*8",
    fimB="F5*2 A5*2 D6*2 F6*2 E6*4 D6*4 | C6*4 D6*4 B5*4 G5*4",
)


# ============================================================
# ORIGINAIS
# ============================================================

# Cobrinha: jardim saltitante (marimba + pizzicato + clarinete)
musica(
    "cobrinha", bpm=140, tonica="G5", modo="maior",
    inst=dict(lead=I(MARIMBA, 112, 58, 40, 0, 0.8), sino=I(GLOCK, 90, 72, 45),
              acomp=I(PIZZ, 78, 42, 40), contra=I(CLARINETE, 70, 86, 40),
              baixo=I(BAIXO_DEDO, 92, 64, 15), bat=K(STANDARD, 90)),
    baixo="saltitante", acomp="seminimas", bat="pop", dobra=12, swing=0.12,
    progA="G | Bm7 | Cmaj7 | Am7 D7 | G | Bm7 | Eb D | G",
    a="D5 . G5 . B5*2 A5 B5 D6*2 B5*2 G5*4 | F#5 . A5 . D6*2 C#6 D6 F#6*2 D6*2 B5*4 | "
      "E6*2 D6*2 C6*2 B5*2 G5*2 E5*2 G5*4 | A5*2 C6*2 E6*4 D6*2 C6*2 A5*2 F#5*2",
    fimA="G5*2 Bb5*2 Eb6*4 F#5*2 A5*2 D6*4 | G5*2 . . D5*2 . . G4*4 .*4",
    progB="C | D | Bm7 | Em7 | C | D | Am7 | D7",
    b="E5*3 E5 G5*2 E5*2 C6*4 G5*4 | F#5*3 F#5 A5*2 F#5*2 D6*4 A5*4 | "
      "B5*2 A5*2 F#5*2 D5*2 B4*2 D5*2 F#5*4 | G5*6 F#5*2 E5*8",
    fimB="C6*2 B5*2 A5*2 E5*2 C5*2 E5*2 A5*4 | F#5*4 A5*4 C6*4 D6*4",
)

# Campo minado: chiptune misterioso e fofo (quadrada + vibrafone)
musica(
    "minado", bpm=112, tonica="A5", modo="harmonica",
    inst=dict(lead=I(QUADRADA, 84, 60, 35, 0, 0.75), sino=I(CELESTA, 95, 70, 55),
              acomp=I(VIBRAFONE, 76, 44, 50), pad=I(PAD_QUENTE, 55, 64, 60),
              contra=I(CELESTA, 64, 86, 55), baixo=I(SYNBAIXO, 90, 64, 10),
              bat=K(ELETRONICO, 85)),
    baixo="pulsante", acomp="arpejo8", bat="chip", dobra=12, reg_contra=(67, 84),
    progA="Am | Fmaj7 | Dm6 | E7 | Am | Fmaj7 | Bm7b5 E7 | Am",
    a="A4*2 . C5 E5*2 . A5 G#5*2 A5*2 E5*4 | F5*2 . A5 C6*2 . F5 E5*2 F5*2 C5*4 | "
      "D5*2 F5*2 A5*2 B5*2 D6*4 C6*2 B5*2 | G#5*4 E5*2 B4*2 D5*4 . E5 G#5*2",
    fimA="F5*2 D5*2 B4*2 A5*2 G#5*2 E5*2 D5*2 B4*2 | A4*4 E5*2 A5*6 .*4",
    progB="Fmaj7 | G | Em7 | Am | Fmaj7 | G | E7sus4 | E7",
    b="C6*2 A5*2 F5*2 E5*2 F5*2 A5*2 C6*4 | D6*2 B5*2 G5*2 F#5*2 G5*2 B5*2 D6*4 | "
      "E6*4 D6*2 B5*2 G5*4 E5*4 | C6*6 B5*2 A5*8",
    fimB="A5*4 B5*4 D6*4 B5*4 | G#5*8 B5*4 E6*4",
)

# Memória: caixinha de música + chiptune
musica(
    "memoria", bpm=100, tonica="C6", modo="maior", lufs=-17,
    inst=dict(lead=I(CELESTA, 112, 58, 55), sino=I(GLOCK, 90, 72, 55),
              dobra=I(GLOCK, 70, 74, 55), acomp=I(QUADRADA, 52, 42, 40, 0, 0.6),
              pad=I(PAD_NEWAGE, 55, 64, 65), contra=I(FLAUTA, 70, 86, 50),
              baixo=I(SYNBAIXO, 84, 64, 10), bat=K(ELETRONICO, 75)),
    baixo="pop", acomp="arpejo8", centro_acomp=64, bat="chip", dobra=12, vel_bat=0.8,
    progA="Cmaj7 | Em7 | Fmaj7 | G7sus4 G7 | Cmaj7 | Em7 | Dm7 Fm6 | Cmaj7",
    a="G5*2 E5*2 C6*4 B5*2 G5*2 E5*4 | G5*2 E5*2 B5*4 A5*2 G5*2 D5*4 | "
      "A5*2 F5*2 C6*4 E6*2 C6*2 A5*4 | G5*4 C6*4 B5*4 F5*4",
    fimA="F5*2 A5*2 C6*2 D6*2 Ab5*4 F5*4 | E5*4 G5*4 C6*8",
    progB="Am7 | D7 | Dm7 | G7 | Am7 | D7 | Fmaj7 Fm6 | G7sus4 G7",
    b="E6*3 D6 C6*2 A5*2 E5*4 G5*4 | F#5*3 G5 A5*2 C6*2 D6*8 | "
      "F6*3 E6 D6*2 A5*2 F5*4 C6*4 | B5*6 A5*2 G5*8",
    fimB="A5*2 C6*2 E6*4 Ab5*2 C6*2 D6*4 | C6*8 B5*4 D6*4",
)

# Vôlei de praia: calipso (steel drum, violão, congas)
musica(
    "volei", bpm=116, tonica="F5", modo="maior",
    inst=dict(lead=I(STEEL, 110, 60, 40), sino=I(MARIMBA, 100, 72, 40),
              dobra=I(MARIMBA, 84, 74, 40), acomp=I(VIOLAO, 80, 40, 35, 0, 0.5),
              contra=I(FLAUTA, 66, 86, 45), baixo=I(BAIXO_DEDO, 92, 64, 15),
              bat=K(STANDARD, 92)),
    baixo="saltitante", acomp="strum", bat="praia", dobra="tercas",
    progA="F | Dm7 | Gm7 | C7 | F | Dm7 | Bb C7 | F",
    a="C5*2 F5*2 . A5*3 G5*2 F5*2 A5*4 | D5*2 F5*2 . A5*3 C6*2 A5*2 F5*4 | "
      "Bb5*2 A5*2 G5*2 D5*2 F5*3 G5 A5*2 Bb5*2 | C6*3 Bb5 G5*2 E5*2 C5*8",
    fimA="D6*2 C6*2 Bb5*2 F5*2 E5*2 G5*2 Bb5*2 C6*2 | A5*3 F5 . C5*3 F5*8",
    progB="Bb | C | Am7 | Dm7 | Bb | C | Gm7 | C7",
    b="D6*2 D6*2 . C6*3 Bb5*2 F5*2 D5*4 | E6*2 E6*2 . D6*3 C6*2 G5*2 E5*4 | "
      "A5*2 C6*2 E6*2 G6*2 E6*4 C6*4 | F6*4 E6*2 D6*2 A5*8",
    fimB="Bb5*2 D6*2 G6*4 F6*2 D6*2 Bb5*4 | C6*2 . E6 G6*4 E6*2 C6*2 Bb5*4",
)

# Chuva de comida: funk de cozinha (metais, clavinet, slap)
musica(
    "chuva", bpm=108, tonica="E5", modo="dorica", swing=0.1,
    inst=dict(lead=I(METAIS, 100, 60, 35, 0, 0.8), sino=I(VIBRAFONE, 96, 72, 45),
              dobra=I(SAX_TENOR, 78, 76, 40), acomp=I(CLAV, 78, 40, 25, 0, 0.5),
              pad=I(ORGAO, 46, 64, 40), baixo=I(SLAP, 100, 64, 10), bat=K(STANDARD)),
    baixo="funk", acomp="funk", bat="funk", dobra=-12, reg_baixo=(28, 40),
    progA="Em7 | A7 | Em7 | A7 | Em7 | A7 | Cmaj7 B7 | Em7",
    a="E5*2 . G5 . A5*2 B5 . D6*2 B5*2 A5 G5 E5 | C#6*2 . E6 . C#6*2 A5 . G5*2 E5*2 . C#5 E5 | "
      "B5 B5 . D6 . B5*2 G5 A5*2 G5*2 E5*4 | G5*2 A5*2 C#6*2 E6*2 G6*4 E6*4",
    fimA="G5*2 B5*2 E6*4 D#6*2 B5*2 A5*2 F#5*2 | E6*2 . . B5*2 . . E5*4 .*4",
    progB="Cmaj7 | Bm7 | Am7 | B7 | Cmaj7 | Bm7 | Am7 D7 | B7sus4 B7",
    b="G6*3 E6*3 B5*2 C6*2 E6*2 G6*4 | F#6*3 D6*3 A5*2 B5*2 D6*2 F#6*4 | "
      "E6*2 C6*2 A5*2 G5*2 A5*2 C6*2 E6*4 | D#6*6 B5*2 F#5*4 A5*4",
    fimB="C6*2 B5*2 A5*2 E5*2 F#5*2 A5*2 C6*2 D6*2 | E6*8 D#6*8",
)

# Pulo nas nuvens: sonhador e ascendente (flauta, harpa, coro)
musica(
    "pulo", bpm=150, tonica="D6", modo="maior",
    inst=dict(lead=I(FLAUTA, 108, 60, 55), sino=I(CELESTA, 96, 72, 60),
              dobra=I(GLOCK, 72, 74, 55), acomp=I(HARPA, 72, 42, 55),
              pad=I(CORO, 56, 64, 70, 20), contra=I(CORDAS, 64, 86, 55),
              baixo=I(BAIXO_DEDO, 88, 64, 15), bat=K(ROOM, 88)),
    baixo="pop", acomp="harpa", centro_acomp=62, bat="pop", dobra=12,
    progA="D | A/C# | Bm7 | Gmaj7 | D | A/C# | Em7 A7 | D",
    a="A4*2 D5*2 F#5*2 A5*6 F#5*2 A5*2 | E5*2 A5*2 C#6*2 E6*6 C#6*2 A5*2 | "
      "D6*4 C#6*2 B5*2 F#5*4 A5*4 | B5*6 A5*2 F#5*4 D5*4",
    fimA="G5*2 B5*2 E6*4 C#6*2 E6*2 G6*4 | F#6*12 .*4",
    progB="Gmaj7 | F#m7 | Em7 | A | Gmaj7 | F#m7 | Bm7 E7 | Asus4 A",
    b="B5*2 D6*2 F#6*4 E6*2 D6*2 B5*4 | A5*2 C#6*2 E6*4 D6*2 C#6*2 A5*4 | "
      "G5*2 B5*2 E6*2 G6*2 F#6*4 E6*4 | C#6*6 B5*2 A5*8",
    fimB="D6*2 F#6*2 B6*4 G#6*2 E6*2 D6*4 | D6*8 C#6*8",
)

# Ovo voador: aventura heroica (trompete, trompa, cordas a galope)
musica(
    "voador", bpm=152, tonica="E5", modo="menor",
    inst=dict(lead=I(TROMPETE, 104, 60, 45), sino=I(GLOCK, 92, 72, 50),
              dobra=I(CORDAS, 82, 74, 50), contra=I(TROMPA, 74, 86, 50),
              acomp=I(CORDAS, 70, 42, 45, 0, 0.45), baixo=I(BAIXO_DEDO, 92, 64, 15),
              timp=I(TIMPANO, 90, 64, 40, 0, 1.0), bat=K(ORQUESTRA)),
    baixo="galope", acomp="power_galope", bat="heroico", dobra=-12,
    extras=[("timp", ["A", "B", "A2", "B2"], "E2*4 . . . . E2*2 . . B1*4")],
    progA="Em | C | D | Bm7 | Em | C | Am7 D | G",
    a="E5*3 B4 E5*2 G5*2 B5*6 A5 G5 | G5*3 E5 G5*2 C6*2 E6*6 D6 C6 | "
      "D6*4 A5*2 F#5*2 A5*4 D6*4 | B5*6 A5 F#5 D5*8",
    fimA="C6*3 B5 A5*2 E5*2 F#5*3 G5 A5*2 D6*2 | G5*2 B5*2 D6*12",
    progB="Cmaj7 | D | Bm7 | Em | Cmaj7 | D | F | B7",
    b="G5*6 C6*2 E6*4 D6*2 C6*2 | A5*6 D6*2 F#6*4 E6*2 D6*2 | D6*4 B5*4 F#5*4 A5*4 | "
      "G5*6 F#5*2 E5*8",
    fimB="A5*4 C6*4 F6*4 E6*2 C6*2 | D#6*8 F#6*4 B5*4",
)


# ============================================================
# MINI JOGOS NOVOS (SOLO)
# ============================================================

# Corrida do ovo: heroico rápido (metais, guitarra, bateria power)
musica(
    "ovo_corredor", bpm=168, tonica="Bb5", modo="maior",
    inst=dict(lead=I(METAIS, 108, 60, 40), sino=I(GLOCK, 92, 72, 45),
              dobra=I(TROMPA, 80, 76, 45), acomp=I(GUIT_OVER, 64, 40, 25, 0, 0.5),
              pad=I(CORDAS, 60, 64, 50), baixo=I(BAIXO_PALHETA, 96, 64, 10),
              bat=K(POWER)),
    baixo="pulsante", acomp="power", power=True, centro_acomp=52, bat="rapido",
    dobra="tercas", reg_baixo=(34, 46),
    progA="Bb | Ab | Eb | F | Bb | Ab | Gm7 C7 | F",
    a="F5*2 Bb5*2 D6*4 C6*2 D6*2 F6*4 | Eb6*2 C6*2 Ab5*4 Bb5*2 C6*2 Eb6*4 | "
      "G6*4 F6*2 Eb6*2 Bb5*4 G5*4 | A5*2 C6*2 F6*4 Eb6*2 C6*2 A5*4",
    fimA="Bb5*2 D6*2 G6*4 E6*2 G6*2 Bb6*4 | A6*8 F6*4 C6*4",
    progB="Gm | Eb | Bb | F | Gm | Eb | Cm7 | F7",
    b="D6*3 D6*3 Bb5*2 G5*4 Bb5*4 | Eb6*3 Eb6*3 Bb5*2 G5*4 Eb6*4 | "
      "F6*3 F6*3 D6*2 Bb5*4 D6*4 | C6*6 A5*2 F5*8",
    fimB="Eb6*2 D6*2 C6*2 G5*2 Bb5*4 C6*4 | A5*4 C6*4 Eb6*4 F6*4",
)

# Ovonoide: synthwave (serra, arpejos, TR-808)
musica(
    "ovonoide", bpm=138, tonica="C5", modo="menor",
    inst=dict(lead=I(SERRA, 92, 60, 45, 30), sino=I(98, 96, 72, 55),
              dobra=I(QUADRADA, 60, 76, 45), acomp=I(PAD_POLY, 68, 42, 45, 0, 0.6),
              pad=I(PAD_SWEEP, 52, 64, 60), baixo=I(SYNBAIXO2, 94, 64, 10),
              bat=K(TR808)),
    baixo="synth", acomp="arpejo16", centro_acomp=64, bat="synthwave", dobra=12,
    reg_baixo=(28, 40),
    progA="Cm | Abmaj7 | Fm7 | G7sus4 G7 | Cm | Abmaj7 | Dm7b5 G7 | Cm",
    a="C5*2 Eb5*2 G5*2 C6*2 Bb5*3 G5 Eb5*2 G5*2 | C6*3 Ab5 Eb5*2 G5*2 C6*8 | "
      "F5*2 Ab5*2 C6*2 Eb6*2 D6*2 C6*2 Ab5*4 | C6*4 D6*4 B5*4 G5*4",
    fimA="Ab5*2 F5*2 D5*2 F5*2 G5*2 B5*2 D6*2 F6*2 | Eb6*4 C6*4 G5*8",
    progB="Abmaj7 | Bb | Gm7 | Cm | Abmaj7 | Bb | Fm7 | G7",
    b="Eb6*2 . Eb6 . Eb6*2 C6*2 Eb6*2 G6*4 . | F6*2 . F6 . F6*2 D6*2 F6*2 Bb6*4 . | "
      "G6*4 F6*2 D6*2 Bb5*4 D6*4 | C6*12 .*4",
    fimB="Ab5*2 C6*2 F6*4 Eb6*2 C6*2 Ab5*4 | B5*4 D6*4 F6*4 G6*4",
)

# Evolução 2048: puzzle lídio (quadrada, caixinha de música)
musica(
    "ovo_2048", bpm=100, tonica="F5", modo="lidia",
    inst=dict(lead=I(QUADRADA, 84, 60, 40, 0, 0.8), sino=I(CELESTA, 98, 72, 55),
              acomp=I(CAIXINHA, 72, 42, 55), pad=I(PAD_NEWAGE, 52, 64, 65),
              contra=I(VIBRAFONE, 66, 86, 50), baixo=I(SYNBAIXO, 88, 64, 10),
              bat=K(ELETRONICO, 85)),
    baixo="sincopado", acomp="caixinha", centro_acomp=70, bat="chip2", dobra=12,
    reg_contra=(60, 76), vel_bat=0.85,
    progA="Fmaj7 | G/F | Em7 | Am7 | Fmaj7 | G/F | Dm7 Em7 | Fmaj7",
    a="C5*2 C5*2 F5*2 F5*2 A5*4 C6*4 | B4*2 B4*2 D5*2 D5*2 G5*4 B5*4 | "
      "E6*2 D6*2 B5*2 G5*2 E5*4 B5*4 | C6*6 B5*2 A5*8",
    fimA="F5*2 A5*2 D6*4 G5*2 B5*2 E6*4 | E6*4 C6*4 A5*8",
    progB="Dm7 | Em7 | Fmaj7 | G | Dm7 | Em7 | Am7 | G",
    b="A5*3 F5*3 D5*2 F5*2 A5*2 C6*4 | B5*3 G5*3 E5*2 G5*2 B5*2 D6*4 | "
      "E6*2 F6*2 E6*2 C6*2 A5*4 F5*4 | G5*2 A5*2 B5*4 D6*8",
    fimB="C6*2 E6*2 A6*4 G6*2 E6*2 C6*4 | B5*6 A5*2 G5*8",
)

# Mini golfe: jazz leve e preguiçoso (clarinete, piano, contrabaixo)
musica(
    "mini_golfe", bpm=108, tonica="A5", modo="maior", swing=0.28, lufs=-17,
    inst=dict(lead=I(CLARINETE, 106, 60, 45), sino=I(VIBRAFONE, 96, 72, 50),
              dobra=I(FLAUTA, 70, 76, 50), acomp=I(PIANO, 78, 42, 40),
              contra=I(PIZZ, 66, 86, 40), baixo=I(BAIXO_AC, 96, 64, 15),
              bat=K(JAZZ, 82)),
    baixo="caminhando", reg_baixo=(33, 47), acomp="charleston", centro_acomp=60,
    bat="swing", dobra=12, ritmo_contra=4,
    progA="Amaj7 | C#7 | F#m7 | B7 | Amaj7 | C#7 | Bm7 E7 | A6",
    a="E5*2 A5*2 C#6*3 B5 A5*2 E5*6 | E#5*2 G#5*2 B5*3 A5 G#5*2 E#5*6 | "
      "F#5*2 A5*2 C#6*4 E6*4 C#6*4 | D#6*6 C#6*2 B5*4 A5*4",
    fimA="D6*2 C#6*2 B5*2 F#5*2 G#5*2 B5*2 D6*4 | C#6*8 .*2 E5*2 A5*4",
    progB="Dmaj7 | Dm6 | C#m7 | F#7 | Dmaj7 | Dm6 | Bm7 | E7",
    b="F#5*2 A5*2 C#6*4 A5*2 F#5*2 D5*4 | F5*2 A5*2 B5*4 A5*2 F5*2 D5*4 | "
      "E5*2 G#5*2 B5*2 C#6*2 E6*8 | A#5*6 G#5*2 F#5*4 E5*4",
    fimB="D6*4 C#6*2 B5*2 A5*4 F#5*4 | G#5*4 B5*4 D6*4 E6*4",
)

# Atravessa a rua: ska apressado (trompete, guitarra no contratempo)
musica(
    "atravessa", bpm=140, tonica="G5", modo="mixolidia",
    inst=dict(lead=I(TROMPETE, 104, 60, 35), sino=I(XILOFONE, 96, 72, 40),
              dobra=I(TROMBONE, 84, 76, 35), acomp=I(GUIT_LIMPA, 80, 40, 30, 0, 0.4),
              acomp2=I(ORGAO, 56, 84, 35, 0, 0.5), baixo=I(BAIXO_DEDO, 94, 64, 10),
              bat=K(STANDARD)),
    baixo="caminhando", reg_baixo=(31, 45), acomp="contratempo", acomp2="contratempo",
    centro_acomp2=70, bat="ska", dobra=-12,
    progA="G | F | C | D | G | F | C D | G",
    a="D5*2 G5*2 . B5*3 D6*2 B5*2 G5*4 | C5*2 F5*2 . A5*3 C6*2 A5*2 F5*4 | "
      "E5*2 G5*2 C6*2 E6*2 D6*2 C6*2 G5*4 | F#5*2 A5*2 D6*4 C6*2 A5*2 F#5*4",
    fimA="G5*2 E5*2 C5*2 E5*2 F#5*2 A5*2 C6*2 D6*2 | B5*2 . G5 . D5*3 G5*8",
    progB="Em | C | G | D | Em | C | Am7 | D7",
    b="B5*3 B5*3 G5*2 E5*2 G5*2 B5*4 | C6*3 C6*3 G5*2 E5*2 G5*2 C6*4 | "
      "D6*2 B5*2 G5*2 B5*2 D6*2 G6*2 F6*4 | F#6*6 E6*2 D6*8",
    fimB="E6*2 C6*2 A5*2 G5*2 A5*2 C6*2 E6*4 | F#6*4 D6*4 C6*4 A5*4",
)

# Coral dos ovos: coral suave em Mi bemol (vozes, sinos, órgão)
musica(
    "coral_ovos", bpm=100, tonica="Eb5", modo="maior", lufs=-17,
    inst=dict(lead=I(VOZ, 110, 60, 65), sino=I(SINOS, 90, 72, 60),
              dobra=I(CELESTA, 74, 76, 60), acomp=I(PIANO, 70, 42, 50),
              pad=I(PAD_CORO, 56, 64, 70), contra=I(CORDAS, 62, 86, 60),
              baixo=I(BAIXO_AC, 84, 64, 20), bat=K(ESCOVA, 70)),
    baixo="meio", acomp="arpejo8", bat="calmo", dobra=12, vel_bat=0.75,
    progA="Eb | Bb/D | Cm7 | Ab | Eb | Bb/D | Fm7 Bb7 | Eb",
    a="G5*4 Bb5*4 Eb6*6 D6*2 | F5*4 Bb5*4 D6*6 C6*2 | Eb6*4 D6*2 C6*2 G5*4 Bb5*4 | "
      "C6*6 Bb5*2 Ab5*8",
    fimA="Ab5*4 C6*4 D6*4 F6*4 | Eb6*12 .*4",
    progB="Ab | Bb | Gm7 | Cm7 | Ab | Bb | Fm7 | Bb7",
    b="C5*2 Eb5*2 Ab5*4 G5*2 Eb5*2 C5*4 | D5*2 F5*2 Bb5*4 Ab5*2 F5*2 D5*4 | "
      "Bb4*6 D5*2 G5*8 | Eb5*6 D5*2 C5*8",
    fimB="Ab5*4 G5*2 F5*2 C5*4 Eb5*4 | D5*4 F5*4 Ab5*4 Bb5*4",
)

# Ovo na colher: cômico e cuidadoso (fagote, pizzicato, tuba)
musica(
    "ovo_colher", bpm=120, tonica="D5", modo="mixolidia",
    inst=dict(lead=I(FAGOTE, 108, 60, 40, 0, 0.6), sino=I(GLOCK, 92, 72, 45),
              dobra=I(FLAUTA, 76, 76, 45), acomp=I(PIZZ, 76, 42, 40),
              contra=I(CLARINETE, 64, 86, 40), baixo=I(TUBA, 92, 64, 20),
              bat=K(STANDARD, 85)),
    baixo="oompah", acomp="seminimas", bat="polka", dobra=12, vel_bat=0.85,
    progA="D | C | G | A7 | D | C | G A7 | D",
    a="A4*2 . A4 D5*2 . D5 F#5*2 E5*2 D5*4 | G4*2 . G4 C5*2 . C5 E5*2 D5*2 C5*4 | "
      "B4*2 D5*2 G5*2 B5*2 A5*3 G5 F#5*2 E5*2 | E5*4 C#5*2 A4*2 G5*8",
    fimA="B4*2 D5*2 G5*4 C#5*2 E5*2 A5*4 | F#5*2 . D5 . A4*3 D5*8",
    progB="Bm | G | D | A | Bm | G | Em7 | A7",
    b="F#5*2 F#5*2 G5*2 F#5*2 D5*4 B4*4 | D5*2 D5*2 E5*2 D5*2 B4*4 G4*4 | "
      "A4*2 D5*2 F#5*2 A5*2 C6*4 A5*4 | C#6*6 B5*2 A5*8",
    fimB="G5*2 E5*2 B4*2 E5*2 G5*2 B5*2 D6*4 | C#6*4 A5*4 E5*4 G5*4",
)

# Ovotris: puzzle em Sol menor harmônico (quadrada + cravo)
musica(
    "ovotris", bpm=144, tonica="G5", modo="harmonica",
    inst=dict(lead=I(QUADRADA, 86, 60, 40, 0, 0.85), sino=I(GLOCK, 92, 72, 50),
              acomp=I(CRAVO, 74, 42, 40), contra=I(CORDAS, 60, 86, 50),
              baixo=I(SYNBAIXO, 92, 64, 10), bat=K(ELETRONICO, 90)),
    baixo="oitavas", reg_baixo=(31, 43), acomp="alberti", bat="chip", dobra=12,
    progA="Gm | D7 | Eb | Cm D7 | Gm | D7 | Cm D7 | Gm",
    a="D5*2 G5*2 Bb5*2 A5 G5 F#5*2 G5*2 D5*4 | C5*2 F#5*2 A5*2 G5 F#5 E5*2 F#5*2 D5*4 | "
      "Eb5*2 G5*2 Bb5*2 Eb6*2 D6*2 C6*2 Bb5*4 | G5*2 Eb5*2 C5*4 F#5*2 A5*2 D6*4",
    fimA="Eb5*2 G5*2 C6*4 D6*2 C6*2 A5*2 F#5*2 | G5*4 D5*4 G4*8",
    progB="Bb | F | Gm | D | Bb | F | Cm | D7",
    b="F5*3 F5 Bb5*2 D6*2 C6*2 Bb5*2 F5*4 | C5*3 C5 F5*2 A5*2 G5*2 F5*2 C5*4 | "
      "D5*2 G5*2 Bb5*2 D6*2 G6*4 F#6*4 | F#6*6 E6*2 D6*8",
    fimB="Eb6*2 D6*2 C6*2 G5*2 Eb5*2 G5*2 C6*4 | D6*4 C6*4 A5*4 F#5*4",
)

# Toupeiras na horta: hoedown com blues (gaita, banjo, rabeca)
musica(
    "toupeiras", bpm=126, tonica="F5", modo="mixolidia",
    inst=dict(lead=I(GAITA, 100, 60, 35), sino=I(XILOFONE, 98, 72, 40),
              dobra=I(RABECA, 80, 76, 40), acomp=I(BANJO, 80, 40, 30),
              contra=I(RABECA, 62, 86, 40), baixo=I(BAIXO_AC, 96, 64, 15),
              bat=K(STANDARD, 88)),
    baixo="oompah", acomp="arpejo16", centro_acomp=62, bat="country", dobra=12,
    reg_baixo=(33, 46), ritmo_contra=4,
    progA="F | Bb7 | F | C7 | F | Bb7 | Bb7 C7 | F",
    a="C5*2 F5*2 Ab5 A5*3 C6*2 A5*2 F5*4 | D5*2 F5*2 Ab5*4 F5*2 D5*2 Bb4*4 | "
      "C6*2 C6*2 A5*2 F5*2 G5*2 Ab5 A5 C6*4 | Bb5*4 G5*2 E5*2 C5*8",
    fimA="D6*2 Bb5*2 F5*2 Ab5*2 G5*2 E5*2 C5*2 Bb4*2 | A4*2 . C5 . Eb5*2 F5*8 .",
    progB="Bb | F | Bb | C7 | Bb | F | Dm7 G7 | C7",
    b="F5*2 Bb5*2 D6*2 Bb5*2 Db6 D6*3 Bb5*4 | C6*2 A5*2 F5*2 A5*2 Ab5 A5*3 F5*4 | "
      "D6*2 F6*2 D6*2 Bb5*2 Ab5*2 F5*2 D5*4 | E5*2 G5*2 Bb5*2 C6*2 E6*8",
    fimB="F5*2 A5*2 D6*4 B5*2 D6*2 F6*4 | E6*4 C6*4 Bb5*4 G5*4",
)

# Salto no lago: calmo e atmosférico (flauta de pã, kalimba)
musica(
    "salto_lago", bpm=90, tonica="Db5", modo="maior", lufs=-18,
    inst=dict(lead=I(FLAUTA_PAN, 108, 60, 65), sino=I(98, 92, 72, 70),
              acomp=I(KALIMBA, 80, 42, 55), pad=I(ATMOSFERA, 58, 64, 75, 30),
              contra=I(SHAKUHACHI, 56, 86, 65), baixo=I(FRETLESS, 86, 64, 25),
              bat=K(STANDARD, 70)),
    baixo="raiz", acomp="caixinha", centro_acomp=66, bat="calmo", dobra=None,
    vel_bat=0.65,
    progA="Dbmaj7 | Bbm7 | Gbmaj7 | Ab | Dbmaj7 | Bbm7 | Ebm7 Ab | Db",
    a="Ab5*4 F5*2 Eb5*2 Db5*4 F5*4 | Bb5*6 Ab5*2 F5*8 | Db6*4 Bb5*2 Ab5*2 F5*4 Bb5*4 | "
      "Ab5*6 Bb5*2 Eb5*8",
    fimA="Gb5*2 F5*2 Eb5*4 Eb5*2 F5*2 Ab5*4 | F5*12 .*4",
    progB="Gbmaj7 | Fm7 | Ebm7 | Absus4 Ab | Gbmaj7 | Fm7 | Bbm7 | Absus4 Ab",
    b="Bb5*4 Db6*4 F6*8 | Eb6*4 C6*2 Ab5*2 F5*8 | Gb5*4 Bb5*4 Db6*4 Eb6*4 | Db6*8 C6*8",
    fimB="F5*4 Ab5*4 Bb5*4 Db6*4 | Eb6*8 C6*8",
)

# Pescaria: calmo de beira de rio (ocarina, violão, violoncelo)
musica(
    "pescaria", bpm=92, tonica="D5", modo="maior", lufs=-18,
    inst=dict(lead=I(OCARINA, 104, 60, 55), sino=I(VIBRAFONE, 92, 72, 60),
              dobra=I(FLAUTA, 70, 76, 55), acomp=I(VIOLAO, 84, 42, 40),
              pad=I(PAD_QUENTE, 52, 64, 70), contra=I(CELLO, 64, 86, 55),
              baixo=I(FRETLESS, 84, 64, 20), bat=K(ESCOVA, 70)),
    baixo="meio", acomp="arpejo8", centro_acomp=58, bat="calmo", dobra=12,
    reg_contra=(48, 62), vel_bat=0.7,
    progA="Dmaj7 | Gmaj7 | Bm7 | A | Dmaj7 | Gmaj7 | Em7 A7 | D",
    a="F#5*6 A5*2 C#6*4 A5*4 | B5*6 A5*2 F#5*8 | D5*2 F#5*2 A5*4 B5*2 A5*2 F#5*4 | E5*12 .*4",
    fimA="G5*4 F#5*2 E5*2 C#5*4 E5*4 | D5*12 .*4",
    progB="Em7 | F#m7 | Gmaj7 | A | Em7 | F#m7 | Gmaj7 | Asus4 A",
    b="B5*4 G5*4 E5*4 D5*4 | C#6*4 A5*4 F#5*4 E5*4 | D6*6 B5*2 F#6*8 | E6*6 C#6*2 A5*8",
    fimB="B5*4 D6*4 F#6*4 D6*4 | D6*8 C#6*8",
)

# Descida na neve: inverno em movimento (celesta, guizos, trompa)
musica(
    "descida_neve", bpm=132, tonica="Bb5", modo="maior",
    inst=dict(lead=I(CELESTA, 112, 60, 55), sino=I(GLOCK, 92, 72, 55),
              dobra=I(FLAUTA, 82, 76, 55), acomp=I(PIZZ, 76, 42, 45),
              pad=I(CORDAS_LENTAS, 58, 64, 65), contra=I(TROMPA, 68, 86, 55),
              baixo=I(BAIXO_AC, 88, 64, 20), bat=K(ORQUESTRA, 90)),
    baixo="pop", acomp="seminimas", bat="neve", dobra=-12,
    progA="Bb | F/A | Gm7 | Eb F | Bb | F/A | Cm7 F7 | Bb",
    a="F6*2 D6*2 Bb5*2 F5*2 D6*4 Bb5*4 | C6*2 A5*2 F5*2 C5*2 A5*4 F5*4 | "
      "Bb5*2 A5*2 G5*2 D5*2 F5*4 D5*4 | Eb5*2 G5*2 Bb5*4 C6*2 A5*2 F5*4",
    fimA="Eb6*2 C6*2 G5*2 Eb5*2 A5*2 C6*2 Eb6*4 | D6*4 Bb5*4 F5*8",
    progB="Ebmaj7 | Dm7 | Cm7 | F | Ebmaj7 | Dm7 | Gm7 C7 | F7",
    b="G5*4 Bb5*4 D6*4 Eb6*4 | F6*4 D6*4 A5*4 C6*4 | Eb6*4 C6*4 G5*4 Bb5*4 | A5*8 C6*8",
    fimB="Bb5*2 D6*2 G6*4 E6*2 G6*2 Bb6*4 | A6*4 F6*4 Eb6*4 C6*4",
)

# Invasores da cozinha: synth retrô marcial (metais sintéticos, 808)
musica(
    "invasores", bpm=118, tonica="F5", modo="menor",
    inst=dict(lead=I(SYNMETAIS, 100, 60, 40, 20), sino=I(QUADRADA, 80, 72, 45),
              dobra=I(SERRA, 70, 76, 45), acomp=I(SERRA, 62, 42, 35, 0, 0.4),
              pad=I(PAD_SWEEP, 54, 64, 60), baixo=I(SYNBAIXO2, 96, 64, 10),
              bat=K(TR808)),
    baixo="synth", reg_baixo=(29, 41), acomp="contratempo", centro_acomp=62, bat="marcha",
    dobra=12,
    progA="Fm | Db | Bbm | C7 | Fm | Db | Bbm7 C7 | Fm",
    a="F5*3 F5*3 Ab5*2 C6*4 Ab5*4 | F5*3 F5*3 Ab5*2 Db6*4 C6*4 | "
      "Bb5*2 Db6*2 F6*4 Eb6*2 Db6*2 Bb5*4 | C6*4 Bb5*2 G5*2 E5*8",
    fimA="Db6*2 C6*2 Bb5*2 F5*2 E5*2 G5*2 Bb5*2 C6*2 | F5*4 C5*4 F4*8",
    progB="Dbmaj7 | Eb | Cm7 | Fm | Dbmaj7 | Eb | Bbm7 | C7",
    b="Ab5*2 C6*2 F6*4 Eb6*2 C6*2 Ab5*4 | G5*2 Bb5*2 Eb6*4 Db6*2 Bb5*2 G5*4 | "
      "Eb6*3 C6 G5*4 Bb5*4 C6*4 | Ab5*6 G5*2 F5*8",
    fimB="F5*2 Ab5*2 Db6*4 F6*4 Eb6*4 | E6*4 C6*4 G5*4 E5*4",
)

# Liga-ovos: lo-fi chiptune (quadrada suave, Rhodes, swing)
musica(
    "liga_ovos", bpm=104, tonica="E5", modo="maior", swing=0.22, lufs=-17,
    inst=dict(lead=I(QUADRADA, 80, 60, 45, 0, 0.8), sino=I(VIBRAFONE, 96, 72, 55),
              dobra=I(VIBRAFONE, 80, 76, 55), acomp=I(EPIANO, 82, 42, 45, 30),
              pad=I(PAD_QUENTE, 50, 64, 65), baixo=I(BAIXO_DEDO, 90, 64, 15),
              bat=K(ELETRONICO, 85)),
    baixo="sincopado", acomp="bossa", centro_acomp=60, bat="vapor", dobra="tercas",
    progA="Emaj7 | G#m7 | Amaj7 | Am6 | Emaj7 | G#m7 | F#m7 B7 | Emaj7",
    a="B4*2 E5*2 F#5*2 G#5*4 F#5*2 E5*2 B4*2 | D#5*2 F#5*2 G#5*2 B5*4 G#5*2 F#5*2 D#5*2 | "
      "C#6*4 B5*2 A5*2 G#5*4 E5*4 | C6*6 B5*2 A5*4 F#5*4",
    fimA="A5*2 C#6*2 E6*4 D#6*2 B5*2 A5*4 | G#5*4 E5*4 B4*8",
    progB="C#m7 | F#m7 | B | Emaj7 | C#m7 | F#m7 | Amaj7 | B7sus4 B7",
    b="E5*2 G#5*2 B5*2 C#6*2 E6*4 C#6*4 | F#5*2 A5*2 C#6*2 E6*2 F#6*4 E6*4 | "
      "D#6*6 C#6*2 B5*8 | G#5*4 B5*4 D#6*8",
    fimB="C#6*4 E6*4 G#6*4 E6*4 | E6*8 D#6*8",
)

# Lanchonete do ovo: swing de lanchonete (surdina, sax, walking bass)
musica(
    "lanchonete", bpm=150, tonica="Bb5", modo="maior", swing=0.33,
    inst=dict(lead=I(SURDINA, 108, 60, 40), sino=I(VIBRAFONE, 96, 72, 45),
              dobra=I(SAX_TENOR, 86, 76, 40), acomp=I(PIANO, 74, 42, 40, 0, 0.7),
              contra=I(TROMBONE, 62, 86, 40), baixo=I(BAIXO_AC, 100, 64, 15),
              bat=K(JAZZ)),
    baixo="caminhando", reg_baixo=(33, 48), acomp="charleston", centro_acomp=60,
    bat="swing", dobra=-12, reg_contra=(50, 65), ritmo_contra=4,
    progA="Bb6 G7 | Cm7 F7 | Dm7 G7 | Cm7 F7 | Bb6 G7 | Cm7 F7 | Cm7 F7 | Bb6",
    a="D5*2 F5*2 G5*2 Bb5*2 B5*2 D6*2 F6*2 D6*2 | Eb6*3 C6 . G5*3 A5*2 C6*2 F5*2 Eb5*2 | "
      "F5*2 A5*2 C6*2 D6*2 B5*2 G5*2 F5*2 D5*2 | Eb5*2 G5*2 Bb5*4 A5*6 .*2",
    fimA="C6*2 Bb5*2 G5*2 Eb5*2 F5*2 A5*2 C6*2 Eb6*2 | D6*6 Bb5*2 .*8",
    progB="D7 | D7 | G7 | G7 | C7 | C7 | F7 | F7",
    melB="F#5*2 A5*2 C6*2 D6*2 F#6*4 D6*4 | C6*2 A5*2 F#5*2 D5*2 E5*2 F#5*2 A5*4 | "
         "B4*2 D5*2 F5*2 G5*2 B5*4 G5*4 | F5*2 D5*2 B4*2 G4*2 A4*2 B4*2 D5*4 | "
         "E5*2 G5*2 Bb5*2 C6*2 E6*4 C6*4 | Bb5*2 G5*2 E5*2 C5*2 D5*2 E5*2 G5*4 | "
         "A5*4 C6*4 Eb6*8 | D6*2 C6*2 A5*2 F5*2 Eb5*2 C5*2 A4*4",
)

# Ovo-man: fliperama em perseguição (quadrada, slap, metais)
musica(
    "ovo_man", bpm=150, tonica="Eb5", modo="menor",
    inst=dict(lead=I(QUADRADA, 88, 60, 35, 0, 0.8), sino=I(GLOCK, 92, 72, 45),
              acomp=I(SYNMETAIS, 66, 42, 35, 0, 0.5), baixo=I(SLAP2, 98, 64, 10),
              bat=K(ELETRONICO)),
    baixo="funk", reg_baixo=(27, 39), acomp="funk", centro_acomp=62, bat="chip2", dobra=12,
    progA="Ebm | B | Abm | Bb7 | Ebm | B | Abm7 Bb7 | Ebm",
    a="Eb5 . Gb5 . Bb5*2 A5 Bb5 Eb6*2 D6 Eb6 Bb5*4 | D#5 . F#5 . B5*2 A#5 B5 D#6*2 D6 D#6 B5*4 | "
      "Cb6*2 Bb5*2 Ab5*2 Eb5*2 Gb5*2 F5*2 Eb5*4 | D5*2 F5*2 Ab5*2 Bb5*2 D6*4 F6*4",
    fimA="Gb5*2 Ab5*2 Cb6*2 Eb6*2 D6*2 Bb5*2 F5*2 D5*2 | Eb5*2 . . Bb4*2 . . Eb4*4 .*4",
    progB="B | Db | Ebm | Ebm | B | Db | Cm7b5 | Bb7",
    b="F#5*3 F#5*3 D#5*2 B4*4 D#5*4 | Ab5*3 Ab5*3 F5*2 Db5*4 F5*4 | "
      "Bb5*2 Gb5*2 Eb5*2 Gb5*2 Bb5*2 Eb6*2 Gb6*4 | F6*2 Eb6*2 Db6*2 Bb5*2 Gb5*8",
    fimB="Eb6*2 C6*2 Gb5*2 Eb5*2 Gb5*2 Bb5*2 C6*4 | D6*4 Bb5*4 Ab5*4 F5*4",
)

# Ninho arrumado: aconchego lídio (vibrafone, Rhodes, fretless)
musica(
    "ninho_arrumado", bpm=84, tonica="Ab5", modo="lidia", swing=0.15, lufs=-18,
    inst=dict(lead=I(VIBRAFONE, 110, 60, 55), sino=I(CELESTA, 92, 72, 60),
              dobra=I(PIANO, 72, 76, 55), acomp=I(EPIANO, 76, 42, 50, 30),
              pad=I(PAD_NEWAGE, 52, 64, 70), baixo=I(FRETLESS, 84, 64, 25),
              bat=K(ESCOVA, 70)),
    baixo="meio", acomp="bossa", centro_acomp=60, bat="calmo", dobra=12, vel_bat=0.7,
    progA="Abmaj7 | Bb/Ab | Gm7 | Cm7 | Abmaj7 | Bb/Ab | Fm7 Bb7 | Ebmaj7",
    a="C5*2 Eb5*2 G5*4 Ab5*2 G5*2 Eb5*4 | D5*2 F5*2 Bb5*4 C6*2 Bb5*2 F5*4 | "
      "G5*4 F5*2 D5*2 Bb4*4 D5*4 | Eb5*6 D5*2 C5*8",
    fimA="Ab5*4 C6*4 D6*4 F6*4 | G5*4 Bb5*4 D6*8",
    progB="Fm7 | Gm7 | Abmaj7 | Bb | Fm7 | Gm7 | Abmaj7 | Bbsus4 Bb",
    b="C6*4 Ab5*2 F5*2 Eb5*4 F5*4 | D6*4 Bb5*2 G5*2 F5*4 G5*4 | Eb6*2 D6*2 C6*2 G5*2 Ab5*8 | "
      "F5*6 D5*2 Bb4*8",
    fimB="C6*2 Eb6*2 G6*4 F6*2 D6*2 C6*4 | Eb6*8 D6*8",
)

# Estoura-bolhas: borbulhante (calíope, marimba, bongôs)
musica(
    "estoura_bolha", bpm=120, tonica="F#5", modo="maior",
    inst=dict(lead=I(CALLIOPE, 100, 60, 45), sino=I(CELESTA, 96, 72, 55),
              dobra=I(GLOCK, 70, 76, 50), acomp=I(MARIMBA, 82, 42, 40),
              pad=I(PAD_NEWAGE, 48, 64, 60), baixo=I(SYNBAIXO, 90, 64, 10),
              bat=K(STANDARD, 90)),
    baixo="saltitante", acomp="arpejo8", bat="bolhas", dobra=12,
    progA="F#maj7 | A#m7 | Bmaj7 | Bm6 | F#maj7 | A#m7 | G#m7 C#7 | F#",
    a="C#5 . F#5 . A#5 . C#6*2 A#5*2 F#5*2 C#6*4 | C#5 . E#5 . G#5 . C#6*2 A#5*2 G#5*2 E#5*4 | "
      "D#6*2 C#6*2 B5*2 F#5*2 A#5*4 F#5*4 | D6*6 C#6*2 B5*4 G#5*4",
    fimA="B5*2 D#6*2 F#6*4 E#6*2 C#6*2 B5*4 | A#5*2 . F#5 . C#5*3 F#5*8",
    progB="Bmaj7 | C#7 | A#m7 | D#m7 | Bmaj7 | C#7 | G#m7 | C#7",
    b="F#5*2 B5*2 D#6*2 F#6*2 D#6*2 B5*2 A#5*4 | G#5*2 C#6*2 E#6*2 G#6*2 E#6*2 C#6*2 B5*4 | "
      "A#5*6 G#5*2 E#5*4 C#5*4 | F#5*4 A#5*4 C#6*8",
    fimB="B5*4 D#6*4 F#6*4 D#6*4 | E#6*4 C#6*4 B5*4 G#5*4",
)

# Ovo na estrada: rock de estrada (guitarras gêmeas, órgão)
musica(
    "ovo_estrada", bpm=132, tonica="E5", modo="mixolidia",
    inst=dict(lead=I(GUIT_OVER, 96, 56, 40), sino=I(ORGAO, 80, 72, 40),
              dobra=I(GUIT_OVER, 80, 80, 40), acomp=I(ORGAO, 66, 40, 35),
              baixo=I(BAIXO_PALHETA, 96, 64, 10), bat=K(STANDARD)),
    baixo="oitavas", reg_baixo=(28, 40), acomp="pop", bat="rock", dobra="tercas",
    progA="E | D | A | C D | E | D | A B7 | E",
    a="B4*2 E5*2 G#5*2 B5*4 A5*2 G#5*2 E5*2 | A4*2 D5*2 F#5*2 A5*4 F#5*2 E5*2 D5*2 | "
      "C#5*2 E5*2 A5*4 B5*2 C#6*2 E6*4 | E6*2 D6*2 C6*2 G5*2 F#5*2 A5*2 D6*4",
    fimA="C#6*2 B5*2 A5*2 E5*2 D#5*2 F#5*2 A5*2 B5*2 | E5*12 .*4",
    progB="C#m | A | E | B | C#m | A | F#m7 | Bsus4 B",
    b="E5*4 G#5*4 C#6*6 B5*2 | A5*4 C#6*4 E6*6 D6*2 | E6*4 B5*4 G#5*4 B5*4 | D#6*12 .*4",
    fimB="A5*2 C#6*2 E6*4 F#6*4 E6*4 | E6*8 D#6*8",
)


# ============================================================
# 2 JOGADORES (INTENSOS)
# ============================================================

# Sumô de ovos: taikos, guitarra distorcida e shamisen
musica(
    "sumo_ovo", bpm=128, tonica="D5", modo="menor", lufs=-15,
    inst=dict(lead=I(GUIT_DIST, 92, 56, 35), sino=I(KOTO, 100, 72, 45),
              dobra=I(SHAMISEN, 90, 80, 35), acomp=I(GUIT_DIST, 66, 36, 25, 0, 0.45),
              baixo=I(BAIXO_PALHETA, 98, 64, 10), taiko=I(TAIKO, 110, 64, 45, 0, 1.0),
              bat=K(POWER)),
    baixo="pulsante", reg_baixo=(26, 38), acomp="power", power=True, centro_acomp=50,
    bat="taiko", dobra=12,
    extras=[("taiko", ["A", "B", "A2", "B2"], "D2*2 . . D2 . D2*2 . . D2*2 D2 D2 D2 .")],
    progA="Dm | Bb | Dm | A7 | Dm | Bb | Gm A7 | Dm",
    a="D5*2 D5 E5 F5*2 A5*2 Bb5*2 A5*2 F5*4 | D5*2 D5 E5 F5*2 Bb5*2 A5*2 F5*2 D5*4 | "
      "A5*2 A5 Bb5 A5*2 F5*2 E5*2 D5*2 A4*4 | E5*6 F5*2 E5*4 C#5*4",
    fimA="Bb5*2 A5*2 G5*2 D5*2 E5*2 F5*2 G5*2 A5*2 | D6*4 A5*4 D5*8",
    progB="Bb | C | Dm | Dm | Bb | C | Gm7 | A7",
    b="F5*3 F5*3 D5*2 Bb4*4 D5*4 | G5*3 G5*3 E5*2 C5*4 E5*4 | "
      "A5*2 F5*2 D5*2 F5*2 A5*2 D6*2 F6*4 | E6*2 D6*2 A5*2 F5*2 D5*8",
    fimB="Bb5*4 A5*4 G5*4 F5*4 | E5*4 C#5*4 A4*8",
)

# Hóquei de ovos: metal rápido (guitarras, baixo galopante)
musica(
    "hoquei_ovo", bpm=152, tonica="E5", modo="menor", lufs=-15,
    inst=dict(lead=I(GUIT_DIST, 94, 56, 35), sino=I(SERRA, 84, 72, 40),
              dobra=I(GUIT_DIST, 80, 80, 35), acomp=I(GUIT_DIST, 68, 36, 20, 0, 0.45),
              baixo=I(BAIXO_PALHETA, 100, 64, 10), bat=K(POWER)),
    baixo="galope", reg_baixo=(28, 40), acomp="power_galope", power=True, centro_acomp=52,
    bat="metal", dobra="tercas",
    progA="Em | C | D | B7 | Em | C | Am7 B7 | Em",
    a="E5*2 E5 G5 B5*2 E5*2 D6*2 B5*2 G5*2 A5 B5 | C5*2 C5 E5 G5*2 C5*2 B5*2 G5*2 E5*2 F#5 G5 | "
      "A5*2 F#5*2 D5*2 F#5*2 A5*2 D6*2 C6*2 A5*2 | B5*4 A5*2 F#5*2 D#5*8",
    fimA="C6*2 B5*2 A5*2 E5*2 D#5*2 F#5*2 A5*2 B5*2 | E6*8 B5*4 E5*4",
    progB="C | D | Em | Em | C | D | Bm7 | B7",
    b="G5*4 E5*2 G5*2 C6*4 B5*2 G5*2 | A5*4 F#5*2 A5*2 D6*4 C6*2 A5*2 | "
      "B5*2 G5*2 E5*2 G5*2 B5*2 E6*2 G6*4 | F#6*6 E6*2 B5*8",
    fimB="D6*4 B5*4 F#5*4 A5*4 | D#6*4 F#6*4 A6*4 B6*4",
)

# Guerra de tinta: funk-metal dórico (metais + guitarra distorcida)
musica(
    "guerra_tinta", bpm=116, tonica="D5", modo="dorica", lufs=-15,
    inst=dict(lead=I(METAIS, 104, 60, 35, 0, 0.8), sino=I(XILOFONE, 96, 72, 40),
              dobra=I(GUIT_DIST, 76, 80, 30), acomp=I(GUIT_DIST, 68, 38, 20, 0, 0.4),
              baixo=I(SLAP, 100, 64, 10), bat=K(POWER)),
    baixo="funk", reg_baixo=(26, 38), acomp="funk", power=True, centro_acomp=52, bat="funk",
    dobra=-12,
    progA="Dm7 | G7 | Dm7 | G7 | Dm7 | G7 | Bbmaj7 C | Dm7",
    a="D5*2 . F5 . A5*2 C6 . A5*2 G5 F5 D5*3 | B4*2 . D5 . G5*2 B5 . G5*2 F5 D5 B4*3 | "
      "A5 A5 . C6 . D6*2 C6 A5*2 G5*2 F5*4 | G5*2 B5*2 D6*2 F6*2 E6*4 D6*4",
    fimA="D6*2 F6*2 A6*4 G6*2 E6*2 C6*4 | D6*2 . . A5*2 . . D5*4 .*4",
    progB="Bbmaj7 | C | Am7 | Dm7 | Bbmaj7 | C | Gm7 | A7",
    b="F5*3 A5*3 D6*2 F6*4 D6*4 | G5*3 C6*3 E6*2 G6*4 E6*4 | "
      "E6*2 C6*2 A5*2 C6*2 E6*2 G6*2 A6*4 | F6*6 E6*2 D6*8",
    fimB="Bb5*2 D6*2 G6*4 F6*2 D6*2 Bb5*4 | C#6*4 E6*4 G6*4 A6*4",
)

# Futebol de ovos: rock de estádio (trompete, coro de torcida, palmas)
musica(
    "futebol_ovo", bpm=140, tonica="D5", modo="maior", lufs=-15,
    inst=dict(lead=I(TROMPETE, 104, 60, 40), sino=I(GLOCK, 92, 72, 45),
              dobra=I(CORO, 92, 76, 55), acomp=I(GUIT_OVER, 66, 38, 25, 0, 0.5),
              pad=I(ORGAO, 46, 64, 40), baixo=I(BAIXO_PALHETA, 98, 64, 10),
              bat=K(ROOM)),
    baixo="oitavas", reg_baixo=(26, 40), acomp="power", power=True, centro_acomp=52,
    bat="torcida", dobra=-12,
    progA="D | F#m | G | A | D | F#m | Em7 A | D",
    a="D5*2 D5*2 F#5*2 A5*4 . A5 F#5*2 D5*2 | C#5*2 C#5*2 F#5*2 A5*4 . A5 F#5*2 C#5*2 | "
      "B4*2 D5*2 G5*2 B5*2 A5*2 G5*2 D5*4 | E5*6 F#5*2 A5*8",
    fimA="G5*2 B5*2 E6*4 C#6*2 E6*2 A5*4 | D6*8 .*2 A5*2 D6*4",
    progB="G | A | Bm | Bm | G | A | Em7 | Asus4 A",
    b="B5*3 B5*3 B5*2 D6*4 B5*4 | C#6*3 C#6*3 C#6*2 E6*4 C#6*4 | "
      "D6*2 C#6*2 B5*2 F#5*2 B5*2 D6*2 F#6*4 | F#6*6 E6*2 D6*8",
    fimB="G5*2 B5*2 D6*2 E6*2 G6*4 E6*4 | D6*8 C#6*8",
)

# Ovo-bomba: tensão eletrônica (serra, baixo pulsante, tique-taque)
musica(
    "ovo_bomba", bpm=140, tonica="C#5", modo="harmonica", lufs=-15,
    inst=dict(lead=I(SERRA, 94, 60, 40, 20), sino=I(GLOCK, 90, 72, 45),
              dobra=I(QUADRADA, 66, 76, 40), acomp=I(GUIT_DIST, 64, 38, 20, 0, 0.4),
              pad=I(PAD_SWEEP, 50, 64, 55), baixo=I(SYNBAIXO, 96, 64, 10),
              bat=K(ELETRONICO)),
    baixo="dezesseis", reg_baixo=(25, 37), acomp="power", power=True, centro_acomp=50,
    bat="rapido", dobra=12,
    extras=[("bat", ["intro", "A", "B", "A2", "B2"], "E5 . . . F5 . . . E5 . . . F5 . . .")],
    progA="C#m | A | F#m | G# | C#m | A | D G#7 | C#m",
    a="C#5*2 . E5 . G#5*2 C#6 . B5*2 G#5*2 E5*3 | A4*2 . C#5 . E5*2 A5 . G#5*2 E5*2 C#5*3 | "
      "F#5*2 A5*2 C#6*2 F#6*2 E6*2 C#6*2 A5*4 | G#5*4 B#5*4 D#6*4 G#6*4",
    fimA="F#5*2 A5*2 D6*4 B#5*2 D#6*2 F#6*4 | C#6*4 G#5*4 C#5*8",
    progB="A | B | G#m7 | C#m | A | B | F#m7 | G#7",
    b="E5*3 E5*3 C#5*2 A5*4 E5*4 | F#5*3 F#5*3 D#5*2 B5*4 F#5*4 | "
      "G#5*2 B5*2 D#6*2 F#6*2 D#6*4 B5*4 | C#6*6 B5*2 G#5*8",
    fimB="A5*2 C#6*2 E6*4 F#6*4 A6*4 | G#6*4 F#6*4 D#6*4 B#5*4",
)


# ============================================================
# OVO NO RITMO (a melodia vem do próprio jogo: o mapa de notas
# sai dela, então o tempo e as notas precisam bater exatamente)
# ============================================================

def montar_ritmo(nome, d):
    from jogos import ovo_ritmo as r

    p = Partitura(nome, r.BPM)
    p.instrumento("lead", **I(SERRA, 100, 60, 40, 20, 0.9, humano=0))
    p.instrumento("dobra", **I(CELESTA, 70, 76, 50, 0, 0.9, humano=0))
    p.instrumento("acomp", **I(PAD_POLY, 64, 42, 40, 0, 0.6))
    p.instrumento("pad", **I(CORDAS, 56, 64, 60, 20))
    p.instrumento("baixo", **I(SYNBAIXO, 98, 64, 10, humano=0))
    p.instrumento("bat", **K(STANDARD))

    passo = 0
    for compassos, acordes, melodia, bateria, acomp in r.SECOES:
        segs = ler_progressao(" | ".join(acordes), passo, f"{nome}/secao")
        tocar_baixo(p, segs, "oitavas", 92, 34, 46)
        tocar_acomp(p, segs, "pad", 58 if acomp == "pad" else 46, 60, "pad")
        if acomp != "pad":
            tocar_acomp(p, segs, "arpejo16", 62, 68, "acomp")
        chave = "ritmo_" + bateria
        BATERIAS[chave] = dict(r.BATERIAS[bateria])
        tocar_bateria(p, passo, compassos, chave, crash=bateria == "disco2", fill=False)
        p.tocar("lead", melodia, passo, 104, onde=f"{nome}/melodia")
        if bateria == "disco2":
            p.tocar("dobra", melodia, passo, 80, transp=12, onde=f"{nome}/dobra")
        passo += compassos * 16

    p.fim = passo * PASSO
    return p


musica("ovo_ritmo", montar=montar_ritmo, loop=False, lufs=-15)


# ============================================================
# EFEITOS SONOROS
# ============================================================
# Cada um devolve (partitura, pico). Tempos em segundos.

EFEITOS = {}


def efeito(func):
    EFEITOS[func.__name__.replace("sfx_", "")] = func
    return func


def _sfx(nome, **inst):
    p = Partitura("sfx_" + nome, 120)
    for papel, cfg in inst.items():
        p.instrumento(papel, **cfg)
    return p


def _glissando(p, papel, ini, dur, de, ate, passos=24, curva=1.0):
    """Pitch bend de 'de' até 'ate' (em -1..1 da faixa do bend)."""
    for k in range(passos + 1):
        t = k / passos
        v = de + (ate - de) * (t ** curva)
        p.bend_t(papel, ini + dur * t, v * 8191)


@efeito
def sfx_clique():
    # "toc" de madeira grave e curto: confortável mesmo repetido muitas vezes
    p = _sfx("clique", a=I(MARIMBA, 100, 64, 12, humano=0))
    p.nota_t("a", 0, 0.06, 67, 70)
    return p, 0.2


@efeito
def sfx_selecionar():
    p = _sfx("selecionar", a=I(MARIMBA, 100, 64, 15, humano=0))
    p.nota_t("a", 0, 0.07, 67, 72)
    p.nota_t("a", 0.05, 0.1, 74, 78)
    return p, 0.26


@efeito
def sfx_voltar():
    p = _sfx("voltar", a=I(MARIMBA, 100, 64, 15, humano=0))
    p.nota_t("a", 0, 0.07, 74, 72)
    p.nota_t("a", 0.05, 0.1, 67, 70)
    return p, 0.24


@efeito
def sfx_comer():
    p = _sfx("comer", a=I(PIZZ, 110, 64, 15, humano=0), bat=K(STANDARD, 110, 5))
    p.nota_t("bat", 0, 0.05, 61, 110)
    p.nota_t("bat", 0.06, 0.05, 60, 90)
    for i, n in enumerate([72, 76, 79, 84]):
        p.nota_t("a", 0.03 * i, 0.12, n, 100)
    return p, 0.8


@efeito
def sfx_moeda():
    p = _sfx("moeda", a=I(CELESTA, 110, 64, 30, humano=0), b=I(GLOCK, 100, 64, 30),
             c=I(112, 70, 64, 40))
    p.nota_t("a", 0, 0.06, 91, 110)         # G6
    p.nota_t("b", 0, 0.06, 91, 80)
    p.nota_t("a", 0.055, 0.45, 96, 120)     # C7 (o "plim")
    p.nota_t("b", 0.055, 0.45, 96, 100)
    p.nota_t("c", 0.11, 0.4, 100, 70)       # brilho (E7)
    return p, 0.8


@efeito
def sfx_pulo():
    p = _sfx("pulo", a=I(QUADRADA, 100, 64, 10, bend=12, humano=0))
    p.bend_t("a", 0, 0)
    p.nota_t("a", 0, 0.17, 67, 100)
    _glissando(p, "a", 0.0, 0.15, 0, 0.75, curva=0.6)
    return p, 0.6


@efeito
def sfx_mola():
    import math
    p = _sfx("mola", a=I(SYNBAIXO2, 110, 64, 10, bend=12, humano=0),
             b=I(OCARINA, 70, 64, 20, bend=12, humano=0))
    p.nota_t("a", 0, 0.5, 55, 110)
    p.nota_t("b", 0, 0.45, 67, 80)
    for k in range(60):
        t = k / 60 * 0.5
        v = (0.35 + 0.25 * t) + 0.18 * math.sin(t * 2 * math.pi * 16) * math.exp(-4 * t)
        p.bend_t("a", t, v * 8191)
        p.bend_t("b", t, v * 8191)
    return p, 0.8


@efeito
def sfx_boing():
    p = _sfx("boing", a=I(SLAP, 110, 64, 10, bend=12, humano=0),
             b=I(MARIMBA, 90, 64, 20, humano=0))
    p.bend_t("a", 0, 0)
    p.nota_t("a", 0, 0.32, 48, 115)
    _glissando(p, "a", 0, 0.1, 0, 1.0, passos=12, curva=0.7)
    _glissando(p, "a", 0.1, 0.2, 1.0, 0.45, passos=16)
    p.nota_t("b", 0.09, 0.15, 72, 80)
    return p, 0.8


@efeito
def sfx_explosao():
    p = _sfx("explosao", bat=K(POWER, 127, 40), t=I(TAIKO, 127, 64, 50, humano=0),
             g=I(127, 110, 64, 50, humano=0), timp=I(TIMPANO, 120, 64, 50, humano=0))
    p.nota_t("bat", 0, 0.5, 35, 127)
    p.nota_t("bat", 0, 0.5, 36, 127)
    p.nota_t("bat", 0.02, 1.2, 49, 120)
    p.nota_t("bat", 0.04, 1.2, 57, 110)
    p.nota_t("t", 0, 0.8, 36, 127)
    p.nota_t("g", 0, 0.6, 40, 127)
    p.nota_t("timp", 0, 1.0, 31, 127)
    p.nota_t("timp", 0.05, 1.0, 38, 110)
    return p, 0.92


@efeito
def sfx_perder():
    import math
    p = _sfx("perder", a=I(TROMBONE, 110, 64, 35, bend=2, humano=0),
             b=I(TUBA, 90, 64, 30, bend=2, humano=0))
    notas = [(0.0, 0.17, 64), (0.19, 0.17, 60), (0.38, 0.17, 57), (0.57, 0.9, 56)]
    for ini, dur, n in notas:
        p.nota_t("a", ini, dur, n, 105)
        p.nota_t("b", ini, dur, n - 12, 90)
    # O último "derrete" tremendo para baixo
    for k in range(50):
        t = k / 50 * 0.9
        v = -0.9 * (t / 0.9) ** 2 + 0.12 * math.sin(t * 2 * math.pi * 7)
        p.bend_t("a", 0.57 + t, v * 8191)
        p.bend_t("b", 0.57 + t, v * 8191)
    return p, 0.8


def _fanfarra(nome, grande):
    """Tema do Oval em Dó, rápido, terminando num acorde (vitória/recorde)."""
    p = _sfx(nome, a=I(TROMPETE, 112, 58, 40, humano=0), b=I(METAIS, 100, 70, 40, humano=0),
             c=I(GLOCK, 90, 64, 45, humano=0), timp=I(TIMPANO, 110, 64, 40, humano=0),
             cordas=I(CORDAS, 90, 64, 50, humano=0), bat=K(ORQUESTRA, 110, 40))
    u = 0.06 if not grande else 0.065
    t = 0.0
    for alt, d in [(67, 2), (72, 2), (76, 3), (74, 1), (72, 2), (79, 4)]:
        p.nota_t("a", t, d * u * 0.95, alt, 112)
        p.nota_t("c", t, d * u, alt + 12, 80)
        t += d * u
    if grande:
        # Sobe mais: A B C' (escada) e explode no acorde
        for alt in (81, 83):
            p.nota_t("a", t, u * 1.9, alt, 115)
            p.nota_t("b", t, u * 1.9, alt - 12, 95)
            p.nota_t("c", t, u * 2, alt + 12, 85)
            t += u * 2
        for k in range(10):
            p.nota_t("bat", k * 0.04 + t - 0.4, 0.04, 38, 60 + k * 5)
    p.nota_t("timp", 0, 0.3, 36, 110)
    fim = 1.1 if grande else 0.7
    acorde = [60, 64, 67, 72] + ([76, 79, 84] if grande else [])
    for n in acorde:
        p.nota_t("b", t, fim, n, 110)
        p.nota_t("cordas", t, fim, n, 90)
    p.nota_t("a", t, fim, 84 if grande else 79, 118)
    p.nota_t("c", t, fim, 96, 90)
    p.nota_t("timp", t, 0.6, 36, 127)
    p.nota_t("bat", t, 1.0, 49, 115)
    if grande:
        p.nota_t("bat", t, 1.0, 57, 105)
    return p


@efeito
def sfx_vencer():
    return _fanfarra("vencer", False), 0.9


@efeito
def sfx_recorde():
    return _fanfarra("recorde", True), 0.95


@efeito
def sfx_compra():
    p = _sfx("compra", bat=K(STANDARD, 110, 20), a=I(GLOCK, 110, 64, 40, humano=0),
             b=I(112, 100, 64, 45, humano=0), c=I(CELESTA, 100, 64, 40, humano=0))
    p.nota_t("bat", 0, 0.05, 75, 110)            # "tlec" da gaveta
    p.nota_t("bat", 0.05, 0.08, 54, 100)
    p.nota_t("bat", 0.12, 0.6, 81, 110)          # "ching!"
    for n in (88, 95, 100):
        p.nota_t("a", 0.12, 0.5, n, 105)
        p.nota_t("b", 0.13, 0.5, n, 90)
    p.nota_t("c", 0.19, 0.4, 100, 100)
    return p, 0.8


@efeito
def sfx_bandeira():
    p = _sfx("bandeira", a=I(PIZZ, 110, 64, 15, humano=0), b=I(MARIMBA, 100, 64, 15, humano=0),
             bat=K(STANDARD, 100, 5))
    p.nota_t("bat", 0, 0.04, 77, 90)
    p.nota_t("a", 0, 0.1, 79, 100)
    p.nota_t("b", 0.04, 0.1, 86, 95)
    return p, 0.6


@efeito
def sfx_revelar():
    p = _sfx("revelar", a=I(XILOFONE, 110, 64, 15, humano=0))
    p.nota_t("a", 0, 0.05, 96, 85)
    return p, 0.45


@efeito
def sfx_virar():
    p = _sfx("virar", bat=K(STANDARD, 110, 10))
    p.nota_t("bat", 0, 0.05, 69, 90)
    p.nota_t("bat", 0.0, 0.04, 76, 70)
    p.nota_t("bat", 0.045, 0.05, 77, 85)
    return p, 0.5


@efeito
def sfx_bater():
    p = _sfx("bater", bat=K(POWER, 120, 10))
    p.nota_t("bat", 0, 0.2, 36, 127)
    p.nota_t("bat", 0, 0.2, 41, 110)
    p.nota_t("bat", 0, 0.1, 38, 55)
    return p, 0.85


@efeito
def sfx_erro():
    p = _sfx("erro", a=I(QUADRADA, 100, 64, 10, humano=0), b=I(CLARINETE, 80, 64, 10, humano=0))
    for ini in (0, 0.14):
        for n in (46, 47):
            p.nota_t("a", ini, 0.1, n, 100)
        p.nota_t("b", ini, 0.1, 58, 80)
    return p, 0.55


@efeito
def sfx_asa():
    p = _sfx("asa", a=I(121, 120, 64, 15, bend=12, humano=0), bat=K(STANDARD, 100, 10))
    p.bend_t("a", 0, -2000)
    p.nota_t("a", 0, 0.13, 72, 120)
    _glissando(p, "a", 0, 0.12, -0.25, 0.5, passos=12)
    p.nota_t("bat", 0.01, 0.06, 69, 90)
    return p, 0.55


@efeito
def sfx_ponto():
    p = _sfx("ponto", a=I(VIBRAFONE, 110, 64, 30, humano=0), b=I(GLOCK, 90, 64, 30, humano=0))
    p.nota_t("a", 0, 0.08, 79, 100)       # 5 -> 1 (pedacinho do Tema do Oval)
    p.nota_t("b", 0, 0.08, 91, 70)
    p.nota_t("a", 0.07, 0.25, 84, 110)
    p.nota_t("b", 0.07, 0.25, 96, 85)
    return p, 0.7


@efeito
def sfx_acerto():
    p = _sfx("acerto", a=I(CELESTA, 110, 64, 35, humano=0), b=I(HARPA, 100, 64, 35, humano=0))
    for i, n in enumerate((84, 88, 91, 96)):
        p.nota_t("a", 0.05 * i, 0.3, n, 105)
        p.nota_t("b", 0.05 * i, 0.3, n - 12, 90)
    return p, 0.7
