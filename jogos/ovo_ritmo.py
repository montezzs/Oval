import math
import os
import random
import threading

import pygame

from settings import *
from core import ui
from core import sintetizador as sint
from core import trilhas
from jogos.base import MiniJogo

# ============================================================
# OVO NO RITMO
# ============================================================
# Ovinhos coloridos caem em 4 pistas no ritmo da música: aperte a
# seta certa quando o ovinho chegar no receptor! A música é
# composta aqui mesmo (Si bemol menor, 120 BPM, 44 compassos) e o
# mapa de notas sai DA MESMA melodia: cada nota da melodia vira um
# ovinho. O seu ovo dança na pista de disco, com o ROBERT e o TOTÓ
# de fãs.
#
# Sincronia: o relógio do jogo é próprio (t += dt) e é a fonte de
# verdade. Se houver áudio, ele é puxado bem de leve (10%) na
# direção da posição real da música.

ID_JOGO = "ovo_ritmo"
BPM = 120
PASSO = 60 / BPM / 4            # 1/16 de compasso = 0.125 s
LATENCIA = 0.06                 # atraso médio da placa de som

PISTAS_X = [332, 422, 512, 602]
RECEPTOR_Y = 600
CORES_PISTA = [(255, 90, 160), (80, 200, 255), (120, 230, 120), (255, 200, 60)]
ROTULOS = ["←", "↓", "↑", "→"]
PISO_Y = 480
DANCARINO = (820, 520)
ALTURA_DANCARINO = 150

VELOCIDADES = [380, 500, 650]                  # px/s (FÁCIL, MÉDIO, DIFÍCIL)
FOLGA_JANELA = [1.25, 1.0, 0.9]                # janelas mais largas no fácil
J_PERFEITO, J_OTIMO, J_BOM = 0.06, 0.11, 0.17  # segundos (generosas)
PONTOS_JULG = {"PERFEITO": 300, "ÓTIMO": 200, "BOM": 100}
PESO_JULG = {"PERFEITO": 1.0, "ÓTIMO": 0.85, "BOM": 0.6, "ERROU": 0.0}
CORES_JULG = {"PERFEITO": AMARELO, "ÓTIMO": (140, 240, 120), "BOM": (120, 200, 255),
              "ERROU": (255, 110, 110), "SEGUROU!": (255, 170, 230), "SOLTOU!": (255, 150, 120)}
DUR_HOLD_MIN = 6                               # passos (só no DIFÍCIL)

ENERGIA_INICIAL = 60.0

# ------------------------------------------------------------
# TECLAS -> PISTA (← ↓ ↑ →)
# ------------------------------------------------------------
# D é "→" no WASD e "←" no DFJK: decide pelo último jeito usado.
TECLAS_PISTA = {
    pygame.K_LEFT: 0, pygame.K_DOWN: 1, pygame.K_UP: 2, pygame.K_RIGHT: 3,
    pygame.K_a: 0, pygame.K_s: 1, pygame.K_w: 2,
    pygame.K_f: 1, pygame.K_j: 2, pygame.K_k: 3,
    pygame.K_KP4: 0, pygame.K_KP2: 1, pygame.K_KP8: 2, pygame.K_KP6: 3,
}


# ============================================================
# A MÚSICA (melodia escrita à mão)
# ============================================================
# Cada seção: (compassos, acordes (1 por compasso), melodia, bateria, acomp)

ACORDES = {
    "Bbm": ["Bb3", "Db4", "F4", "Bb4"],
    "Gb": ["Gb3", "Bb3", "Db4", "Gb4"],
    "Db": ["Db4", "F4", "Ab4", "Db5"],
    "Ab": ["Ab3", "C4", "Eb4", "Ab4"],
    "F": ["F3", "A3", "C4", "F4"],
}
RAIZES = {"Bbm": "Bb2", "Gb": "Gb2", "Db": "Db3", "Ab": "Ab2", "F": "F2"}

BATERIAS = {
    "intro": {"k": "x...x...x...x...", "h": "..x...x...x...x."},
    "disco": {"k": "x...x...x...x...", "s": "....x.......x...", "h": "..x...x...x...x."},
    "disco2": {"k": "x...x...x...x...", "s": "....x.......x...", "h": "xxx.xxx.xxx.xxx.",
               "c": "............x..."},
    "meio": {"k": "x.........x.....", "s": "........x.......", "h": "x.x.x.x.x.x.x.x."},
}

_A = ("F5*2 F5*2 Db5*2 F5*2 Ab5*3 Gb5 F5*2 Db5*2 | "
      "Gb5*2 Gb5*2 Db5*2 Bb4*2 Db5*4 .*2 Bb4*2 | "
      "F5*2 Ab5*2 Db6*3 C6 Bb5*2 Ab5*2 F5*4 | "
      "Eb5*2 F5*2 Gb5*2 Ab5*2 C6*4 Ab5*2 Eb5*2")
_B = ("Bb5*2 Bb5*2 Bb5*2 Db6*2 Bb5*2 Ab5*2 Gb5*4 | "
      "Ab5*2 Ab5*2 Ab5*2 C6*2 Ab5*2 Gb5*2 F5*4 | "
      "F5 F5 Gb5*2 F5*2 Db5*2 Bb4*4 Db5*2 F5*2 | "
      "Bb5*6 Ab5*2 F5*4 Db5*4 | "
      "Bb5*2 Bb5*2 Bb5*2 Db6*2 Eb6*2 Db6*2 Bb5*4 | "
      "C6*2 C6*2 C6*2 Eb6*2 C6*2 Ab5*2 Eb5*4 | "
      "F5*2 A5*2 C6*2 A5*2 F5*2 A5*2 C6*2 Eb6*2 | ")

SECOES = [
    # Introdução: bateria e baixo, depois notas nos tempos
    (4, ["Bbm", "Gb", "Db", "Ab"],
     ".*16 | .*16 | F4*4 Ab4*4 Db5*4 C5*4 | Eb5*4 C5*4 Ab4*4 Eb4*4",
     "intro", "arpejo16"),
    # A
    (8, ["Bbm", "Gb", "Db", "Ab"] * 2,
     _A + " | "
     "Bb5*2 Ab5*2 F5*2 Db5*2 F5*3 Gb5 F5*2 Db5*2 | "
     "Db5*2 Eb5*2 F5*2 Gb5*2 Bb5*4 Ab5*2 Gb5*2 | "
     "F5*2 Db5*2 Ab4*2 Db5*2 F5 F5 Ab5*2 F5*2 Eb5*2 | "
     "C5*2 Eb5*2 Ab5*4 Gb5*2 F5*2 Eb5*2 C5*2",
     "disco", "arpejo16"),
    # B (refrão)
    (8, ["Gb", "Ab", "Bbm", "Bbm", "Gb", "Ab", "F", "F"],
     _B + "F6*8 Eb6*2 C6*2 A5*4",
     "disco2", "arpejo16"),
    # A' (com semicolcheias)
    (8, ["Bbm", "Gb", "Db", "Ab"] * 2,
     _A + " | "
     "Bb5 Ab5 F5 Db5 Bb5 Ab5 F5 Db5 F5*4 Ab5*4 | "
     "Gb5 F5 Db5 Bb4 Gb5 F5 Db5 Bb4 Db5*4 Gb5*4 | "
     "F5*2 Ab5*2 Db6*2 F6*2 Eb6*2 Db6*2 C6*2 Ab5*2 | "
     "Eb6*6 C6*2 Ab5*4 Eb5*4",
     "disco", "arpejo16"),
    # Ponte (mais calma, notas longas)
    (4, ["Gb", "Ab", "Bbm", "F"],
     "Bb4*8 Db5*8 | C5*8 Eb5*8 | Db5*8 F5*8 | C5*8 A4*4 C5*4",
     "meio", "pad"),
    # B de novo
    (8, ["Gb", "Ab", "Bbm", "Bbm", "Gb", "Ab", "F", "F"],
     _B + "F6*8 Eb6*4 C6*4",
     "disco2", "arpejo16"),
    # Final
    (4, ["Bbm", "Gb", "Ab", "Bbm"],
     "F5*2 Db5*2 Bb4*2 Db5*2 F5*4 Bb5*4 | "
     "Gb5*2 Db5*2 Bb4*2 Db5*2 Gb5*4 Bb5*4 | "
     "Ab5*2 Eb5*2 C5*2 Eb5*2 Ab5*4 C6*4 | "
     "Bb5*8 .*8",
     "disco", "arpejo16"),
]

COMPASSOS = sum(s[0] for s in SECOES)       # 44
DURACAO = COMPASSOS * 16 * PASSO            # 88 s


def _compor_musica():
    """Gera o áudio da música inteira (seção por seção)."""
    buf = []
    for compassos, acordes, melodia, bateria, acomp in SECOES:
        vozes = [
            (melodia, dict(tipo="serra", vol=0.12, envelope="normal")),
            (trilhas.baixo_rock([RAIZES[a] for a in acordes]),
             dict(tipo="triangulo", vol=0.34, envelope="staccato")),
        ]
        notas = [ACORDES[a] for a in acordes]
        if acomp == "pad":
            vozes.append((trilhas.acordes_sustentados([n[:3] for n in notas]),
                          dict(tipo="triangulo", vol=0.08)))
        else:
            vozes.append((trilhas.arpejo16(notas),
                          dict(tipo="quadrada", duty=0.125, vol=0.045, envelope="pluck")))
        buf.extend(trilhas.compor(BPM, compassos, vozes, bateria=BATERIAS[bateria],
                                  vol_bateria=0.5, eco=(0.18, 0.15)))
    return buf


# A trilha deste jogo é composta à mão: registra no dicionário de
# trilhas (sem mexer no arquivo core/trilhas.py)
trilhas.TRILHAS[ID_JOGO] = _compor_musica

_pronta = threading.Event()
_estado_trilha = {"thread": None, "falhou": False}


def _gerar_em_segundo_plano():
    arq = trilhas.arquivo(ID_JOGO)
    try:
        os.makedirs(os.path.dirname(arq), exist_ok=True)
        buf = _compor_musica()
        temp = f"{arq}.{os.getpid()}.tmp"
        sint.salvar_wav(temp, sint.para_pcm(buf, 0.8))
        os.replace(temp, arq)
    except Exception:           # sem música o jogo funciona igual (relógio próprio)
        _estado_trilha["falhou"] = True
    finally:
        _pronta.set()


def _preparar_trilha():
    """Gera o .wav numa thread (a primeira vez demora uns segundos)."""
    if _pronta.is_set() or _estado_trilha["thread"] is not None:
        return
    if os.path.exists(trilhas.arquivo(ID_JOGO)):
        _pronta.set()
        return
    t = threading.Thread(target=_gerar_em_segundo_plano, daemon=True)
    _estado_trilha["thread"] = t
    t.start()


# ============================================================
# MAPA DE NOTAS (derivado da melodia)
# ============================================================

_SEMITONS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
# Grau da escala de Si bemol menor para cada semitom acima de Bb
# (notas de fora da escala vão para o grau vizinho)
_GRAU = {0: 0, 1: 1, 2: 1, 3: 2, 4: 2, 5: 3, 6: 3, 7: 4, 8: 5, 9: 5, 10: 6, 11: 7}


def _midi(nome):
    semi = _SEMITONS[nome[0]]
    resto = nome[1:]
    while resto and resto[0] in "#b":
        semi += 1 if resto[0] == "#" else -1
        resto = resto[1:]
    return 12 * (int(resto) + 1) + semi


def _pista(nome):
    """Pista do ovinho: grau da escala % 4 (subir na melodia = andar para a direita)."""
    rel = _midi(nome) - 70
    return (7 * (rel // 12) + _GRAU[rel % 12]) % 4


class Nota:
    __slots__ = ("t", "pista", "fim", "julgada", "segurando", "resultado")

    def __init__(self, t, pista, dur=0.0):
        self.t = t
        self.pista = pista
        self.fim = t + dur          # > t: nota de segurar
        self.julgada = False
        self.segurando = False
        self.resultado = None


def mapa_de_notas(opcao):
    """FÁCIL: tempos fortes. MÉDIO: todos os tempos. DIFÍCIL: tudo + segurar."""
    notas = []
    inicio = 0
    for compassos, _, melodia, _, _ in SECOES:
        passo = 0
        for tok in melodia.split():
            if tok == "|":
                continue
            nome, _, d = tok.partition("*")
            dur = int(d) if d else 1
            if nome != ".":
                pos = passo % 16
                if opcao == 0:
                    entra = pos % 8 == 0
                elif opcao == 1:
                    entra = pos % 4 == 0
                else:
                    entra = True
                if entra:
                    t = (inicio + passo) * PASSO
                    segurar = dur * PASSO - 0.08 if (opcao == 2 and dur >= DUR_HOLD_MIN) else 0.0
                    notas.append(Nota(t, _pista(nome), segurar))
            passo += dur
        inicio += compassos * 16
    return notas


# ============================================================
# DESENHOS
# ============================================================

def _seta(sup, centro, tam, direcao, cor, contorno=None, espessura=0):
    """Seta (0 ← 1 ↓ 2 ↑ 3 →)."""
    base = [(0, -1), (0.85, -0.05), (0.33, -0.05), (0.33, 0.9), (-0.33, 0.9), (-0.33, -0.05),
            (-0.85, -0.05)]
    ang = {0: -math.pi / 2, 1: math.pi, 2: 0.0, 3: math.pi / 2}[direcao]
    c, s = math.cos(ang), math.sin(ang)
    pts = [(centro[0] + (x * c - y * s) * tam, centro[1] + (x * s + y * c) * tam) for x, y in base]
    if contorno:
        pygame.draw.polygon(sup, contorno, pts)
        pts2 = [(centro[0] + (x * c - y * s) * (tam - 3), centro[1] + (x * s + y * c) * (tam - 3))
                for x, y in base]
        pygame.draw.polygon(sup, cor, pts2)
    else:
        pygame.draw.polygon(sup, cor, pts, espessura)


_cache = {}


def _ovinho(pista):
    """A nota: ovinho colorido com a seta."""
    chave = ("ovo", pista)
    if chave in _cache:
        return _cache[chave]
    w, h = 58, 68
    sup = pygame.Surface((w, h), pygame.SRCALPHA)
    cor = CORES_PISTA[pista]
    pygame.draw.ellipse(sup, ui.escurecer(cor, 110), (1, 2, w - 2, h - 2))
    pygame.draw.ellipse(sup, ui.escurecer(cor, 40), (3, 4, w - 6, h - 6))
    pygame.draw.ellipse(sup, cor, (4, 3, w - 10, h - 10))
    pygame.draw.ellipse(sup, ui.clarear(cor, 70), (13, 10, 14, 10))
    _seta(sup, (w // 2 - 1, h // 2 + 3), 17, pista, BRANCO, contorno=(40, 20, 50))
    _cache[chave] = sup
    return sup


def _receptor(pista, aceso):
    chave = ("rec", pista, aceso)
    if chave in _cache:
        return _cache[chave]
    w, h = 70, 80
    sup = pygame.Surface((w, h), pygame.SRCALPHA)
    cor = CORES_PISTA[pista]
    rect = pygame.Rect(3, 3, w - 6, h - 6)
    if aceso:
        pygame.draw.ellipse(sup, ui.misturar(cor, BRANCO, 0.35), rect)
        pygame.draw.ellipse(sup, BRANCO, rect, 4)
        _seta(sup, (w // 2, h // 2 + 3), 20, pista, BRANCO, contorno=ui.escurecer(cor, 90))
    else:
        pygame.draw.ellipse(sup, (20, 10, 34, 200), rect)
        pygame.draw.ellipse(sup, cor, rect, 4)
        _seta(sup, (w // 2, h // 2 + 3), 20, pista, ui.escurecer(cor, 30), espessura=3)
    _cache[chave] = sup
    return sup


def _mancha(cor, raio=90):
    """Mancha de luz redonda (somada ao fundo)."""
    chave = ("luz", cor, raio)
    if chave in _cache:
        return _cache[chave]
    sup = pygame.Surface((raio * 2, raio * 2))
    sup.fill((0, 0, 0))
    for r in range(raio, 0, -6):
        k = (1 - r / raio) ** 1.3 * 0.35
        pygame.draw.circle(sup, tuple(int(c * k) for c in cor), (raio, raio), r)
    _cache[chave] = sup
    return sup


def _camadas_piso():
    """4 camadas de ladrilhos acesos (acendem no tempo, alternando)."""
    if "piso" in _cache:
        return _cache["piso"]
    cores = [(255, 80, 160), (80, 200, 255), (255, 220, 70), (120, 230, 120)]
    camadas = []
    for k in range(4):
        sup = pygame.Surface((LARGURA, ALTURA - PISO_Y), pygame.SRCALPHA)
        for lin in range((ALTURA - PISO_Y) // 32 + 1):
            for col in range(LARGURA // 64 + 1):
                if (col + lin * 3) % 4 != k:
                    continue
                cor = cores[(col + lin) % 4]
                r = pygame.Rect(col * 64 + 3, lin * 32 + 3, 58, 26)
                pygame.draw.rect(sup, (*cor, 130), r, border_radius=4)
                pygame.draw.rect(sup, (255, 255, 255, 70), r.inflate(-30, -16), border_radius=3)
        camadas.append(sup)
    _cache["piso"] = camadas
    return camadas


def _trilhos():
    """Trilhos translúcidos das 4 pistas."""
    if "trilhos" in _cache:
        return _cache["trilhos"]
    x0 = PISTAS_X[0] - 45
    larg = PISTAS_X[3] + 45 - x0
    sup = pygame.Surface((larg, ALTURA), pygame.SRCALPHA)
    sup.fill((10, 5, 20, 110))
    for i, x in enumerate(PISTAS_X):
        pygame.draw.rect(sup, (255, 255, 255, 30), (x - x0 - 38, 0, 76, ALTURA))
        pygame.draw.line(sup, (*CORES_PISTA[i], 70), (x - x0 - 38, 0), (x - x0 - 38, ALTURA), 2)
        pygame.draw.line(sup, (*CORES_PISTA[i], 70), (x - x0 + 37, 0), (x - x0 + 37, ALTURA), 2)
    _cache["trilhos"] = (sup, x0)
    return _cache["trilhos"]


def _nota_musical(tela, pos, tam, cor):
    x, y = int(pos[0]), int(pos[1])
    r = max(3, tam // 4)
    esp = max(2, tam // 8)
    for dx, dy, c in ((2, 2, (20, 10, 30)), (0, 0, cor)):
        pygame.draw.ellipse(tela, c, (x - r - 2 + dx, y - r + dy, r * 2 + 3, r * 2))
        haste = x + r + dx
        pygame.draw.line(tela, c, (haste, y + dy), (haste, y - tam + dy), esp)
        pygame.draw.line(tela, c, (haste, y - tam + dy), (haste + r + 3, y - tam + r + 3 + dy), esp)


def _desenhar_robert(tela, x, pe, fase, braco):
    """ROBERT: palito de cabeção branco e boné arco-íris."""
    pula = abs(math.sin(fase * math.pi)) * 8
    y = pe - pula
    preto = (15, 15, 20)
    joelho = 6 + 6 * abs(math.sin(fase * math.pi))
    pygame.draw.line(tela, preto, (x, y - 48), (x - joelho, y - 24), 4)
    pygame.draw.line(tela, preto, (x - joelho, y - 24), (x - 12, pe), 4)
    pygame.draw.line(tela, preto, (x, y - 48), (x + joelho, y - 24), 4)
    pygame.draw.line(tela, preto, (x + joelho, y - 24), (x + 12, pe), 4)
    pygame.draw.line(tela, preto, (x, y - 100), (x, y - 48), 4)
    for lado in (-1, 1):
        cima = (braco == 0) == (lado < 0)
        mao = (x + lado * 30, y - 128) if cima else (x + lado * 30, y - 66)
        pygame.draw.line(tela, preto, (x, y - 88), mao, 4)
    # Cabeça
    cab = (x, y - 128)
    pygame.draw.circle(tela, preto, cab, 29)
    pygame.draw.circle(tela, BRANCO, cab, 26)
    pygame.draw.circle(tela, preto, (x - 9, y - 128), 3)
    pygame.draw.circle(tela, preto, (x + 9, y - 128), 3)
    pygame.draw.arc(tela, preto, (x - 14, y - 132, 28, 20), math.pi * 1.1, math.pi * 1.9, 3)
    # Boné arco-íris
    cores = [(255, 70, 90), (255, 160, 50), (250, 220, 60), (80, 200, 90)]
    for i, c in enumerate(cores):
        pygame.draw.rect(tela, c, (x - 22 + i * 11, y - 160, 11, 18))
    pygame.draw.rect(tela, preto, (x - 22, y - 160, 44, 18), 2, border_top_left_radius=10,
                     border_top_right_radius=10)
    pygame.draw.ellipse(tela, (255, 90, 150), (x + 8, y - 147, 30, 9))
    pygame.draw.ellipse(tela, preto, (x + 8, y - 147, 30, 9), 1)


def _desenhar_toto(tela, x, pe, fase, braco):
    """TOTÓ: o cachorrinho, dançando em pé com as orelhas balançando."""
    pula = abs(math.sin(fase * math.pi + 1.2)) * 10
    y = pe - pula
    pelo = (205, 145, 85)
    escuro = (120, 72, 40)
    creme = (250, 232, 200)
    contorno = (70, 40, 20)
    # Rabinho abanando
    ang = math.sin(fase * math.tau * 2) * 0.6
    ponta = (x + 16 + math.cos(-0.6 + ang) * 22, y - 44 + math.sin(-0.6 + ang) * 22)
    pygame.draw.line(tela, contorno, (x + 12, y - 40), ponta, 7)
    pygame.draw.line(tela, pelo, (x + 12, y - 40), ponta, 4)
    # Perninhas e patas
    for lado in (-1, 1):
        pygame.draw.line(tela, contorno, (x + lado * 8, y - 34), (x + lado * 10, pe - 6), 8)
        pygame.draw.line(tela, pelo, (x + lado * 8, y - 34), (x + lado * 10, pe - 6), 5)
        pygame.draw.ellipse(tela, contorno, (x + lado * 10 - 10, pe - 11, 20, 11))
        pygame.draw.ellipse(tela, creme, (x + lado * 10 - 8, pe - 10, 16, 8))
    # Corpo e barriga
    pygame.draw.ellipse(tela, contorno, (x - 18, y - 76, 36, 48))
    pygame.draw.ellipse(tela, pelo, (x - 16, y - 74, 32, 44))
    pygame.draw.ellipse(tela, creme, (x - 9, y - 64, 18, 30))
    # Patinhas da frente dançando
    for lado in (-1, 1):
        cima = (braco == 1) == (lado < 0)
        mao = (x + lado * 28, y - 96) if cima else (x + lado * 26, y - 52)
        pygame.draw.line(tela, contorno, (x + lado * 10, y - 64), mao, 7)
        pygame.draw.line(tela, pelo, (x + lado * 10, y - 64), mao, 4)
        pygame.draw.circle(tela, contorno, mao, 7)
        pygame.draw.circle(tela, creme, mao, 5)
    # Coleira
    pygame.draw.rect(tela, (220, 40, 50), (x - 13, y - 78, 26, 6), border_radius=3)
    pygame.draw.circle(tela, (250, 210, 40), (x, y - 71), 4)
    # Cabeça
    cy = y - 96
    pygame.draw.circle(tela, contorno, (x, cy), 22)
    pygame.draw.circle(tela, pelo, (x, cy), 20)
    pygame.draw.ellipse(tela, creme, (x - 12, cy - 2, 24, 16))
    # Orelhas caídas (balançam com o pulo)
    balanco = int(pula * 0.8)
    for lado in (-1, 1):
        orelha = pygame.Rect(0, 0, 14, 26)
        orelha.midtop = (x + lado * 19, cy - 16 + balanco // 2)
        pygame.draw.ellipse(tela, contorno, orelha.inflate(3, 3))
        pygame.draw.ellipse(tela, escuro, orelha)
    # Olhos, focinho e linguinha
    for lado in (-1, 1):
        pygame.draw.circle(tela, (20, 14, 10), (x + lado * 7, cy - 6), 3)
        pygame.draw.circle(tela, BRANCO, (x + lado * 7 + 1, cy - 7), 1)
    pygame.draw.ellipse(tela, (20, 14, 10), (x - 5, cy + 1, 10, 7))
    pygame.draw.ellipse(tela, (255, 120, 150), (x - 4, cy + 10, 8, 9))
    pygame.draw.line(tela, (20, 14, 10), (x, cy + 7), (x, cy + 10), 2)


class OvoRitmo(MiniJogo):

    ID = ID_JOGO
    TITULO = "OVO NO RITMO"
    TITULO_CURTO = "RITMO"
    DESCRICAO = "Ovinhos caem no ritmo da música: aperte a seta certa na hora certa e dance na pista!"
    COR = (200, 80, 220)
    INSTRUCOES = [
        "Aperte a seta quando o ovinho chegar no",
        "receptor lá embaixo, no ritmo da música!",
        "Acertos seguidos multiplicam os pontos.",
        "Errou muito? A energia acaba e a música para.",
        "SETAS, WASD ou D F J K",
    ]
    OPCOES = ["FÁCIL", "MÉDIO", "DIFÍCIL"]
    ROTULO_PONTOS = "PONTOS"
    CONTAGEM = True
    TRILHA = None           # música composta à mão (ver _compor_musica)

    MOEDAS_MAX = 24
    SINCRONIZAR = True      # corrigir o relógio pela posição do áudio

    # --------------------------------------------------------
    # CENÁRIO: discoteca
    # --------------------------------------------------------

    @classmethod
    def criar_fundo(cls, jogador):
        sup = ui.gradiente(LARGURA, ALTURA, (30, 15, 50), (54, 22, 74))
        rnd = random.Random(21)

        # Parede com painéis e estrelinhas
        for x in range(0, LARGURA, 96):
            pygame.draw.rect(sup, (38, 18, 62), (x + 6, 150, 84, PISO_Y - 170), border_radius=10)
            pygame.draw.rect(sup, (60, 30, 90), (x + 6, 150, 84, PISO_Y - 170), 2, border_radius=10)
        for _ in range(40):
            x, y = rnd.randrange(LARGURA), rnd.randrange(0, 150)
            pygame.draw.circle(sup, rnd.choice([(120, 90, 170), (180, 150, 230)]), (x, y), 1)

        # Letreiro de neon
        placa = pygame.Rect(0, 0, 250, 56)
        placa.center = (DANCARINO[0], 212)
        pygame.draw.rect(sup, (20, 8, 30), placa, border_radius=14)
        for k, cor in ((6, (90, 30, 90)), (3, (200, 70, 200)), (0, (255, 150, 250))):
            pygame.draw.rect(sup, cor, placa.inflate(k, k), 2, border_radius=16)
        brilho = ui.texto("OVO DISCO", 20, (150, 40, 140), False)
        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
            sup.blit(brilho, brilho.get_rect(center=(placa.centerx + dx, placa.centery + dy)))
        ui.desenhar_texto(sup, "OVO DISCO", placa.center, 20, (255, 190, 250), "center", False)

        # Caixa de som (direita)
        cx = pygame.Rect(930, 330, 82, 270)
        pygame.draw.rect(sup, (16, 12, 22), cx, border_radius=8)
        pygame.draw.rect(sup, (70, 60, 90), cx, 3, border_radius=8)
        for cy, r in ((380, 26), (470, 34), (560, 26)):
            pygame.draw.circle(sup, (40, 34, 52), (cx.centerx, cy), r)
            pygame.draw.circle(sup, (90, 80, 110), (cx.centerx, cy), r, 3)

        # Piso de ladrilhos (apagados)
        cores = [(255, 80, 160), (80, 200, 255), (255, 220, 70), (120, 230, 120)]
        pygame.draw.rect(sup, (14, 8, 22), (0, PISO_Y, LARGURA, ALTURA - PISO_Y))
        for lin in range((ALTURA - PISO_Y) // 32 + 1):
            for col in range(LARGURA // 64 + 1):
                cor = ui.misturar((20, 10, 30), cores[(col + lin) % 4], 0.16)
                pygame.draw.rect(sup, cor, (col * 64 + 3, PISO_Y + lin * 32 + 3, 58, 26),
                                 border_radius=4)
        pygame.draw.line(sup, (120, 80, 160), (0, PISO_Y), (LARGURA, PISO_Y), 3)

        # Fio do globo
        pygame.draw.line(sup, (150, 150, 170), (DANCARINO[0], 0), (DANCARINO[0], 50), 3)
        return sup

    @classmethod
    def desenhar_icone(cls, sup, jogador):
        w, h = sup.get_size()
        for i in range(4):
            x = w // 2 - 78 + i * 30
            rec = pygame.transform.smoothscale(_receptor(i, False), (28, 32))
            sup.blit(rec, rec.get_rect(center=(x, h - 22)))
            ovo = pygame.transform.smoothscale(_ovinho(i), (24, 28))
            sup.blit(ovo, ovo.get_rect(center=(x, 26 + (i * 23) % 60)))
        jogador.desenhar(sup, (w // 2 + 62, h // 2 + 12), 52, angulo=12)
        pygame.draw.circle(sup, (200, 200, 220), (w // 2 + 62, 18), 14)
        for k in range(-2, 3):
            pygame.draw.line(sup, (240, 240, 255), (w // 2 + 50, 18 + k * 5), (w // 2 + 74, 18 + k * 5), 1)

    # --------------------------------------------------------
    # MÚSICA (própria, com sincronia)
    # --------------------------------------------------------

    def __init__(self, app, menu):
        self._musica_pausada = False
        self._esperando_musica = False
        self.teclas_pista = {}
        self.modo_dfjk = False
        self.mouse_pista = None
        _preparar_trilha()
        super().__init__(app, menu)

    @property
    def musica(self):
        if _pronta.is_set() and not _estado_trilha["falhou"]:
            return self.ID
        return None

    def comecar(self):
        # Espera a música ficar pronta (só na primeira vez que abre o jogo)
        if not _pronta.is_set():
            self._esperando_musica = True
            return
        self._esperando_musica = False
        super().comecar()

    def pausar(self):
        antes = self.estado
        super().pausar()
        if self.estado == "pausado" and antes == "jogando" and self._musica_nossa():
            try:
                pygame.mixer.music.pause()
                self._musica_pausada = True
            except pygame.error:
                pass

    def _musica_nossa(self):
        return self.audio.ativo and self.audio.atual == self.ID and self.audio._proxima is None

    def _despausar_musica(self):
        if self._musica_pausada:
            self._musica_pausada = False
            try:
                pygame.mixer.music.unpause()
            except pygame.error:
                pass

    def sair(self):
        self._despausar_musica()
        super().sair()

    def evento(self, e):
        # Teclas seguradas (para as notas de segurar), em qualquer estado
        if e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_f, pygame.K_j, pygame.K_k):
                self.modo_dfjk = True
            elif e.key in (pygame.K_a, pygame.K_s, pygame.K_w):
                self.modo_dfjk = False
            if e.key == pygame.K_d:
                self.teclas_pista[e.key] = 0 if self.modo_dfjk else 3
            elif e.key in TECLAS_PISTA:
                self.teclas_pista[e.key] = TECLAS_PISTA[e.key]
        elif e.type == pygame.KEYUP:
            self.teclas_pista.pop(e.key, None)
        elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
            self.mouse_pista = None
        elif e.type == pygame.WINDOWFOCUSLOST:
            self.teclas_pista.clear()
            self.mouse_pista = None
        super().evento(e)

    def atualizar(self, dt):
        if self._musica_pausada and self.estado != "pausado":
            self._despausar_musica()
        if self.musica and self.estado in ("inicio", "contagem") and self.audio.ativo:
            self.audio.tocar(self.ID)       # não faz nada se já estiver tocando
            # A música tinha parado (energia zerou): volta a tocar
            if self._musica_nossa() and not self._musica_pausada:
                try:
                    if not pygame.mixer.music.get_busy():
                        self.audio.reiniciar_musica()
                except pygame.error:
                    pass
        if self._esperando_musica and _pronta.is_set() and self.estado == "inicio":
            self.comecar()
        super().atualizar(dt)

    # --------------------------------------------------------
    # PARTIDA
    # --------------------------------------------------------

    def reiniciar(self):
        self.notas = mapa_de_notas(self.opcao)
        self.vel = VELOCIDADES[self.opcao]
        self.folga = FOLGA_JANELA[self.opcao]
        self.fim_musica = max(n.fim for n in self.notas) + 1.6
        self.primeira = 0               # índice da primeira nota não julgada
        self.segurando = []             # notas de segurar em andamento
        self.iniciado = False
        self.t = 5.6 if self.estado == "inicio" else -LATENCIA   # prévia com ovinhos na tela
        self.energia = ENERGIA_INICIAL
        self.combo = 0
        self.maior_combo = 0
        self.contagem = {"PERFEITO": 0, "ÓTIMO": 0, "BOM": 0, "ERROU": 0}
        self.soma_peso = 0.0
        self.julgados = 0
        self.acertos = 0
        self.julgamento = None          # (texto, tempo)
        self.flash = [0.0] * 4
        self.aneis = []                 # [pista, tempo]
        self.caindo = []                # ovinhos que passaram: [x, y, vy, ang, pista]
        self.notinhas = []
        self.pose = None                # (pista, tempo)
        self.tropeco = 0.0
        self.parou = False
        self.t_parou = 0.0
        self.nota_final = "-"

    @property
    def batida(self):
        return max(0.0, self.t) / (PASSO * 4)

    # --------------------------------------------------------
    # CONTROLES
    # --------------------------------------------------------

    def evento_jogo(self, e):
        if self.parou:
            return
        if e.type == pygame.KEYDOWN and e.key in self.teclas_pista:
            self._apertar(self.teclas_pista[e.key])
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            x, y = e.pos
            if y > PISO_Y - 60:
                for i, px in enumerate(PISTAS_X):
                    if abs(x - px) <= 45:
                        self.mouse_pista = i
                        self._apertar(i)
                        break

    def _pista_apertada(self, pista):
        return pista in self.teclas_pista.values() or self.mouse_pista == pista

    def _apertar(self, pista):
        self.flash[pista] = max(self.flash[pista], 0.08)
        self.pose = (pista, 0.0)
        janela = J_BOM * self.folga
        alvo = None
        for i in range(self.primeira, len(self.notas)):
            n = self.notas[i]
            if n.t - self.t > janela:
                break
            if not n.julgada and n.pista == pista and abs(n.t - self.t) <= janela:
                alvo = n
                break
        if alvo is None:
            return              # apertar sem nota não tira nada (bom para crianças)

        erro = abs(alvo.t - self.t)
        if erro <= J_PERFEITO * self.folga:
            julg = "PERFEITO"
        elif erro <= J_OTIMO * self.folga:
            julg = "ÓTIMO"
        else:
            julg = "BOM"
        alvo.julgada = True
        alvo.resultado = julg
        self._registrar(julg)
        self.combo += 1
        self.acertos += 1
        self.maior_combo = max(self.maior_combo, self.combo)
        self.pontos += PONTOS_JULG[julg] * self.multiplicador
        self.energia = min(100.0, self.energia + 2)
        self._efeito_acerto(pista, julg)
        if alvo.fim > alvo.t:
            alvo.segurando = True
            self.segurando.append(alvo)

    @property
    def multiplicador(self):
        c = self.combo
        return 1 if c < 10 else 2 if c < 30 else 3 if c < 50 else 4

    def _registrar(self, julg):
        self.contagem[julg] += 1
        self.soma_peso += PESO_JULG[julg]
        self.julgados += 1
        self.julgamento = (julg if julg != "ERROU" else "ERROU", 0.0)

    def _efeito_acerto(self, pista, julg):
        x = PISTAS_X[pista]
        cor = CORES_PISTA[pista]
        self.flash[pista] = 0.18
        self.aneis.append([pista, 0.0])
        # O ovinho racha: casquinhas + notinha musical
        self.particulas.explodir((x, RECEPTOR_Y), [cor, BRANCO, ui.clarear(cor, 60)],
                                 14 if julg == "PERFEITO" else 9, 240, 0.5, (3, 6))
        self.notinhas.append([x + random.uniform(-10, 10), RECEPTOR_Y - 30, random.uniform(-30, 30),
                              -150, 1.0, cor])

    def _errar(self, nota, caiu=True):
        self._registrar("ERROU")
        if self.combo >= 10:
            self.textos.adicionar("COMBO PERDIDO", (PISTAS_X[1] + 45, RECEPTOR_Y - 190),
                                  (220, 210, 255), 12)
        self.combo = 0
        self.energia = max(0.0, self.energia - 8)
        self.tropeco = 1.0
        self.som("erro", 0.25)
        if caiu:
            y = RECEPTOR_Y - (nota.t - self.t) * self.vel
            self.caindo.append([PISTAS_X[nota.pista], y, self.vel * 0.6, 0.0, nota.pista])
        if self.energia <= 0:
            self._musica_parou()

    def _musica_parou(self):
        self.parou = True
        self.t_parou = 0.0
        self.tremer(0.3)
        self.som("perder", 0.6)
        if self._musica_nossa():
            try:
                pygame.mixer.music.fadeout(600)
            except pygame.error:
                pass

    # --------------------------------------------------------
    # LÓGICA
    # --------------------------------------------------------

    def atualizar_jogo(self, dt):
        if not self.iniciado:
            # Primeiro quadro depois do "VAI!": a música recomeça do zero
            self.iniciado = True
            self.t = -LATENCIA
            if self._musica_nossa():
                self.audio.reiniciar_musica()
        else:
            self.t += dt
            if self.SINCRONIZAR and not self.parou and self._musica_nossa():
                pos = self.audio.posicao_musica()
                if pos is not None:
                    dif = (pos - LATENCIA) - self.t
                    if abs(dif) < 0.25:
                        self.t += dif * 0.1

        self._animar(dt)

        if self.parou:
            self.t_parou += dt
            if self.t_parou > 1.6:
                self._fim(False)
            return

        # Notas que passaram da janela
        janela = J_BOM * self.folga
        while self.primeira < len(self.notas):
            n = self.notas[self.primeira]
            if n.julgada:
                self.primeira += 1
                continue
            if self.t - n.t > janela:
                n.julgada = True
                n.resultado = "ERROU"
                self.primeira += 1
                self._errar(n)
                if self.parou:
                    return
                continue
            break

        # Notas de segurar
        for n in list(self.segurando):
            if self.t >= n.fim:
                n.segurando = False
                self.segurando.remove(n)
                self.pontos += 100 * self.multiplicador
                self.soma_peso += 1.0
                self.julgados += 1
                self.julgamento = ("SEGUROU!", 0.0)
                self._efeito_acerto(n.pista, "PERFEITO")
            elif not self._pista_apertada(n.pista) and self.t < n.fim - 0.12:
                n.segurando = False
                self.segurando.remove(n)
                self.julgados += 1
                self.julgamento = ("SOLTOU!", 0.0)
                self.combo = 0
                self.energia = max(0.0, self.energia - 4)
                if self.energia <= 0:
                    self._musica_parou()
                    return

        if self.t >= self.fim_musica:
            self._fim(True)

    def _animar(self, dt):
        self.flash = [max(0.0, f - dt) for f in self.flash]
        for a in self.aneis:
            a[1] += dt
        self.aneis = [a for a in self.aneis if a[1] < 0.3]
        if self.julgamento:
            self.julgamento = (self.julgamento[0], self.julgamento[1] + dt)
            if self.julgamento[1] > 0.6:
                self.julgamento = None
        if self.pose:
            self.pose = (self.pose[0], self.pose[1] + dt)
            if self.pose[1] > 0.3:
                self.pose = None
        self.tropeco = max(0.0, self.tropeco - dt * 2.5)

        vivos = []
        for c in self.caindo:
            c[2] += 900 * dt
            c[1] += c[2] * dt
            c[3] += 300 * dt
            if c[1] > ALTURA - 20:
                cor = CORES_PISTA[c[4]]
                self.particulas.explodir((c[0], ALTURA - 24), [cor, BRANCO, (255, 220, 60)],
                                         12, 200, 0.5, (3, 7))
                continue
            vivos.append(c)
        self.caindo = vivos

        vivas = []
        for n in self.notinhas:
            n[0] += n[2] * dt + math.sin(n[4] * 10) * 30 * dt
            n[1] += n[3] * dt
            n[4] -= dt * 1.1
            if n[4] > 0:
                vivas.append(n)
        self.notinhas = vivas

    def _precisao(self):
        return self.soma_peso / self.julgados if self.julgados else 0.0

    def _fim(self, completou):
        p = self._precisao()
        if completou:
            self.nota_final = "S" if p >= 0.95 else "A" if p >= 0.85 else "B" if p >= 0.70 else "C"
        else:
            self.nota_final = "-"
        linhas = [f"PONTOS: {self.pontos}" + (f"   NOTA: {self.nota_final}" if completou else ""),
                  f"PRECISÃO: {int(p * 100)}%   COMBO: {self.maior_combo}",
                  f"ACERTOS: {self.acertos}/{len(self.notas)}"]
        self.terminar(venceu=completou, titulo="SHOW COMPLETO!" if completou else "A MÚSICA PAROU!",
                      linhas=linhas)

    def calcular_moedas(self, valor, venceu):
        moedas = self.acertos // 15
        moedas += {"S": 8, "A": 5, "B": 2}.get(self.nota_final, 0)
        if valor > 0:
            moedas = max(moedas, self.MOEDAS_MIN)
        return max(0, min(self.MOEDAS_MAX, moedas))

    # --------------------------------------------------------
    # DESENHO
    # --------------------------------------------------------

    def desenhar_jogo(self, tela):
        tela.blit(self.fundo(self.jogador), (0, 0))
        batida = self.batida
        fase = batida % 1.0
        pulso = max(0.0, 1 - fase * 3) if self.t > 0 and not self.parou else 0.0

        # Manchas de luz passeando pela parede
        for i, cor in enumerate(CORES_PISTA + [(200, 120, 255)]):
            a = self.tempo * (0.35 + i * 0.07) + i * 1.7
            x = 512 + math.cos(a) * (430 - i * 30)
            y = 250 + math.sin(a * 1.3 + i) * 170
            luz = _mancha(cor)
            tela.blit(luz, (int(x) - 90, int(y) - 90), special_flags=pygame.BLEND_RGB_ADD)

        # Piso acende no tempo
        if not self.parou:
            camada = _camadas_piso()[int(batida) % 4]
            camada.set_alpha(int(70 + 150 * pulso))
            tela.blit(camada, (0, PISO_Y))

        self._desenhar_globo(tela, pulso)
        self._desenhar_caixa_som(tela, pulso)

        # Fãs dançando
        braco = int(batida) % 2
        _desenhar_robert(tela, 104, 624, fase, braco)
        _desenhar_toto(tela, 214, 630, fase, braco)

        # Pistas e receptores
        trilho, x0 = _trilhos()
        tela.blit(trilho, (x0, 0))
        for i, x in enumerate(PISTAS_X):
            aceso = self.flash[i] > 0 or (self.estado == "jogando" and self._pista_apertada(i))
            rec = _receptor(i, aceso)
            tela.blit(rec, rec.get_rect(center=(x, RECEPTOR_Y)))
        for pista, t in self.aneis:
            k = t / 0.3
            r = pygame.Rect(0, 0, int(70 + 60 * k), int(80 + 60 * k))
            r.center = (PISTAS_X[pista], RECEPTOR_Y)
            pygame.draw.ellipse(tela, ui.misturar(CORES_PISTA[pista], (40, 20, 60), k), r, 4)

        self._desenhar_notas(tela)

        for x, y, _, ang, pista in self.caindo:
            img = pygame.transform.rotate(_ovinho(pista), ang)
            tela.blit(img, img.get_rect(center=(int(x), int(y))))

        self._desenhar_dancarino(tela, fase)

        for x, y, _, _, vida, cor in self.notinhas:
            _nota_musical(tela, (x, y), 20 if vida > 0.5 else 16, cor)
        self.particulas.desenhar(tela)
        self.textos.desenhar(tela)
        self._desenhar_julgamento(tela)

        if self.parou:
            ui.desenhar_texto(tela, "A MÚSICA PAROU!", (PISTAS_X[1] + 45, 330), 24, (255, 120, 120),
                              "center")

    def _desenhar_notas(self, tela):
        topo = -40
        for n in self.segurando:
            self._desenhar_cauda(tela, n, RECEPTOR_Y)
            ovo = _ovinho(n.pista)
            tela.blit(ovo, ovo.get_rect(center=(PISTAS_X[n.pista], RECEPTOR_Y)))
        for i in range(self.primeira, len(self.notas)):
            n = self.notas[i]
            y = RECEPTOR_Y - (n.t - self.t) * self.vel
            if y < topo:
                break
            if n.julgada:
                continue
            if n.fim > n.t:
                self._desenhar_cauda(tela, n, y)
            ovo = _ovinho(n.pista)
            tela.blit(ovo, ovo.get_rect(center=(PISTAS_X[n.pista], int(y))))

    def _desenhar_cauda(self, tela, n, y_cabeca):
        y_fim = RECEPTOR_Y - (n.fim - self.t) * self.vel
        if y_fim >= y_cabeca:
            return
        x = PISTAS_X[n.pista]
        cor = CORES_PISTA[n.pista]
        r = pygame.Rect(x - 11, int(y_fim), 22, int(y_cabeca - y_fim))
        pygame.draw.rect(tela, ui.escurecer(cor, 90), r.inflate(6, 0), border_radius=11)
        pygame.draw.rect(tela, cor if n.segurando else ui.escurecer(cor, 30), r, border_radius=11)
        pygame.draw.rect(tela, ui.clarear(cor, 60), (x - 4, r.y + 6, 5, max(0, r.h - 12)), border_radius=3)

    def _desenhar_globo(self, tela, pulso):
        cx, cy = DANCARINO[0], 96
        r = 50 + int(3 * pulso)
        pygame.draw.circle(tela, (90, 90, 110), (cx, cy), r + 3)
        pygame.draw.circle(tela, (200, 200, 220), (cx, cy), r)
        giro = self.tempo * 1.2
        for j in range(-4, 5):
            y = cy + j * 10
            meia = math.sqrt(max(0, r * r - (j * 10) ** 2))
            for k in range(14):
                a = giro + k * math.tau / 14 + j * 0.2
                prof = math.cos(a)
                if prof <= 0.1:
                    continue
                x = cx + math.sin(a) * meia
                w = max(2, int(9 * prof * meia / r))
                cor = (240, 240, 255) if (k + j) % 2 == 0 else (160, 160, 190)
                if (k * 7 + j * 3 + int(self.tempo * 6)) % 11 == 0:
                    cor = (255, 255, 200)
                pygame.draw.rect(tela, cor, (int(x - w / 2), y - 4, w, 8))
        pygame.draw.circle(tela, (255, 255, 255), (cx - 18, cy - 20), 7)

    def _desenhar_caixa_som(self, tela, pulso):
        x = 971
        for cy, r in ((380, 18), (470, 24), (560, 18)):
            rr = r + int(4 * pulso)
            pygame.draw.circle(tela, (70, 60, 90), (x, cy), rr)
            pygame.draw.circle(tela, (30, 26, 40), (x, cy), max(3, rr // 3))

    def _desenhar_dancarino(self, tela, fase):
        x, y = DANCARINO
        h = ALTURA_DANCARINO
        dx = 0.0
        dy = 0.0
        ang = 0.0
        sx = sy = 1.0
        # Balanço no tempo da música
        if self.t > 0 and not self.parou:
            sy -= 0.05 * max(0.0, 1 - fase * 2)
            sx += 0.04 * max(0.0, 1 - fase * 2)
            ang = math.sin(self.batida * math.pi) * 4
        if self.pose:
            pista, t = self.pose
            k = math.sin(min(1.0, t / 0.3) * math.pi)
            if pista == 0:
                ang += 16 * k
                dx -= 16 * k
            elif pista == 3:
                ang -= 16 * k
                dx += 16 * k
            elif pista == 1:
                sx += 0.22 * k
                sy -= 0.22 * k
            else:
                dy -= 46 * k
                sy += 0.06 * k
                sx -= 0.04 * k
        if self.tropeco > 0:
            ang += 20 * math.sin(self.tropeco * math.pi)
        if self.parou:
            ang = 12 + math.sin(self.t_parou * 8) * 6

        # Sombra
        pygame.draw.ellipse(tela, (10, 5, 16), (x - 60 + dx * 0.3, y + h / 2 - 4, 120, 20))
        sup = self.jogador.avatar(h)
        w0, h0 = sup.get_size()
        if abs(sx - 1) > 0.01 or abs(sy - 1) > 0.01:
            sup = pygame.transform.smoothscale(sup, (max(1, int(w0 * sx)), max(1, int(h0 * sy))))
        if abs(ang) > 0.5:
            sup = pygame.transform.rotate(sup, ang)
        # O pé do ovo fica no chão (a não ser quando pula)
        centro_y = y + h / 2 - h * sy / 2 + dy
        tela.blit(sup, sup.get_rect(center=(int(x + dx), int(centro_y))))

    def _desenhar_julgamento(self, tela):
        cx = (PISTAS_X[0] + PISTAS_X[3]) // 2
        if self.julgamento:
            texto, t = self.julgamento
            tam = 28 if t < 0.08 else 24
            rotulo = texto + ("!" if texto in ("PERFEITO", "ÓTIMO") else "")
            ui.desenhar_texto(tela, rotulo, (cx, 440 - min(t, 0.1) * 60), tam, CORES_JULG[texto], "center")
        if self.combo >= 5:
            txt = f"{self.combo} COMBO"
            ui.desenhar_texto(tela, txt, (cx, 482), 14, BRANCO, "center")
            if self.multiplicador > 1:
                ui.desenhar_texto(tela, f"×{self.multiplicador}", (cx, 506), 16,
                                  [BRANCO, AMARELO, LARANJA, (255, 110, 200)][self.multiplicador - 1], "center")

    def desenhar_hud(self, tela):
        fundo = (22, 12, 36)
        caixa = pygame.Rect(12, 12, 262, 48)
        ui.painel(tela, caixa, fundo, BRANCO, 12, 3, sombra=False)
        ui.desenhar_texto(tela, f"PONTOS: {self.pontos}", (caixa.x + 14, caixa.centery), 14,
                          AMARELO, "midleft")

        c2 = pygame.Rect(12, 66, 262, 30)
        ui.painel(tela, c2, fundo, (150, 120, 200), 10, 2, sombra=False)
        rec = self.recorde()
        ui.desenhar_texto(tela, f"RECORDE: {rec if rec is not None else '--'}", (c2.x + 14, c2.centery + 1),
                          10, (180, 200, 255), "midleft")
        ui.desenhar_texto(tela, self.OPCOES[self.opcao], (c2.right - 12, c2.centery + 1), 10,
                          (255, 180, 240), "midright")

        # Energia
        c3 = pygame.Rect(12, 102, 262, 34)
        ui.painel(tela, c3, fundo, BRANCO, 10, 2, sombra=False)
        ui.coracao(tela, (c3.x + 20, c3.centery + 1), 18)
        barra = pygame.Rect(c3.x + 38, c3.y + 10, c3.w - 50, 14)
        pygame.draw.rect(tela, (50, 40, 60), barra, border_radius=7)
        e = self.energia / 100
        cor = (120, 230, 120) if e > 0.5 else (255, 210, 70) if e > 0.25 else (255, 90, 90)
        if e > 0:
            pygame.draw.rect(tela, cor, (barra.x, barra.y, max(8, int(barra.w * e)), barra.h),
                             border_radius=7)
        pygame.draw.rect(tela, BRANCO, barra, 2, border_radius=7)

        # Progresso da música
        c4 = pygame.Rect(12, 142, 262, 22)
        ui.painel(tela, c4, fundo, (150, 120, 200), 8, 2, sombra=False)
        prog = max(0.0, min(1.0, self.t / self.fim_musica)) if self.iniciado else 0.0
        pygame.draw.rect(tela, (255, 150, 240), (c4.x + 8, c4.y + 8, int((c4.w - 16) * prog), 6),
                         border_radius=3)
        pygame.draw.rect(tela, (120, 90, 160), (c4.x + 8, c4.y + 8, c4.w - 16, 6), 1, border_radius=3)

    def desenhar(self, tela):
        super().desenhar(tela)
        if self._esperando_musica and self.estado == "inicio":
            caixa = pygame.Rect(0, 0, 520, 60)
            caixa.center = (LARGURA // 2, ALTURA // 2)
            ui.painel(tela, caixa, (28, 32, 56), self.COR, 14, 4)
            pontos = "." * (1 + int(self.tempo * 3) % 3)
            ui.desenhar_texto(tela, f"AFINANDO A MÚSICA{pontos}", (caixa.x + 40, caixa.centery), 14,
                              AMARELO, "midleft")
