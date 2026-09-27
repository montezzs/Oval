import math
import random

import pygame

from settings import *
from core import ui
from jogos.base import MiniJogo

# ============================================================
# OVO-MAN
# ============================================================
# Na horta, à noite, o seu ovo come todas as sementes enquanto
# os utensílios de cozinha o perseguem pelo labirinto de
# cerca-viva. Pegue uma PIMENTA: o ovo fica vermelho-fogo e os
# utensílios fogem tremendo (e podem ser comidos!).

COLS = 21
LINHAS = 19
CEL = 32
X0 = 176
Y0 = 96
AREA = pygame.Rect(X0, Y0, COLS * CEL, LINHAS * CEL)

# Labirinto desenhado à mão:
#   #  cerca-viva       .  semente       o  pimenta
#   -  porta da casa    H  casa dos utensílios
#   (espaço) caminho sem semente (o túnel da linha 9)
MAPA = [
    "#####################",
    "#.........#.........#",
    "#o##.####.#.####.##o#",
    "#...................#",
    "#.##.#.#######.#.##.#",
    "#....#....#....#....#",
    "####.####.#.####.####",
    "####.#.........#.####",
    "####.#.###-###.#.####",
    "    ...#HHHHH#...    ",
    "####.#.#######.#.####",
    "####.#.........#.####",
    "####.#.#######.#.####",
    "#.........#.........#",
    "#o##.####.#.####.##o#",
    "#....#.........#....#",
    "#.##.#.###.###.#.##.#",
    "#...................#",
    "#####################",
]

LINHA_TUNEL = 9
INICIO_OVO = (10, 15)
PORTA = (10, 8)
FORA_DA_CASA = (10, 7)          # célula logo acima da porta
CENTRO_CASA = (10, 9)
LUGAR_FRUTA = (10, 11)

PARADO = (0, 0)
CIMA, BAIXO, ESQ, DIR = (0, -1), (0, 1), (-1, 0), (1, 0)
ORDEM = (CIMA, ESQ, BAIXO, DIR)     # desempate da IA (igual ao clássico)

TECLAS = {
    pygame.K_UP: CIMA, pygame.K_w: CIMA,
    pygame.K_DOWN: BAIXO, pygame.K_s: BAIXO,
    pygame.K_LEFT: ESQ, pygame.K_a: ESQ,
    pygame.K_RIGHT: DIR, pygame.K_d: DIR,
}

# Velocidades em células por segundo
VEL_OVO = 7.5
VEL_UTENSILIO = 6.6            # um pouco mais lento que o ovo (justo para crianças)
VEL_ASSUSTADO = 4.0
VEL_TUNEL = 3.5
VEL_OLHOS = 14.0
VEL_CASA = 3.0
MAX_ACELERACAO = 1.35           # +5% por nível, até +35%

BUFFER_CURVA = 0.25             # aperta antes da esquina e ele vira quando der
TOLERANCIA = 4 / CEL            # pode virar até 4 px depois do centro

# Espalhar / perseguir (segundos)
MODOS = [("espalhar", 7), ("perseguir", 20), ("espalhar", 7), ("perseguir", 20),
         ("espalhar", 5), ("perseguir", 20), ("espalhar", 5), ("perseguir", None)]

VIDAS = 3
VIDA_EXTRA = 10000
PONTOS_SEMENTE = 10
PONTOS_PIMENTA = 50
PONTOS_UTENSILIO = [200, 400, 800, 1600]

FRUTAS = [("limao", 100), ("morango", 300), ("bolo", 500)]
TEMPO_FRUTA = 9.0

# Utensílios: nome, cor, lugar na casa, canto do "espalhar", espera para sair
UTENSILIOS = [
    ("frigideira", (235, 60, 60), (10, 7), (COLS - 1, -3), 0.0),
    ("batedeira", (255, 130, 200), (10, 9), (0, -3), 1.5),
    ("ralador", (60, 215, 230), (8, 9), (COLS - 1, LINHAS + 1), 4.5),
    ("espatula", (255, 150, 50), (12, 9), (0, LINHAS + 1), 8.0),
]
NOMES_UTENSILIOS = {"frigideira": "FRIGIDEIRA", "batedeira": "BATEDEIRA",
                    "ralador": "RALADOR", "espatula": "ESPÁTULA"}

AZUL_MEDO = (120, 160, 255)
ALTURA_OVO = 30


def _tela(pos):
    """Centro de uma posição (em células, pode ser fracionária) em pixels."""
    return (X0 + pos[0] * CEL + CEL / 2, Y0 + pos[1] * CEL + CEL / 2)


def _vizinha(cel, d):
    """Célula ao lado (o túnel dá a volta na horizontal)."""
    return ((cel[0] + d[0]) % COLS, cel[1] + d[1])


def _oposta(d):
    return (-d[0], -d[1])


def _parede(cel):
    c, l = cel
    if not 0 <= l < LINHAS:
        return True
    return MAPA[l][c % COLS] in "#H-"


def _no_tunel(cel):
    return cel[1] == LINHA_TUNEL and (cel[0] <= 3 or cel[0] >= COLS - 4)


def _blocos(sup, paredes, margem, cor, desloc=0, origem=(X0, Y0)):
    """Blocos arredondados que se juntam com os vizinhos (a cerca-viva)."""
    meio = CEL // 2
    for c, l in paredes:
        x, y = origem[0] + c * CEL, origem[1] + l * CEL + desloc
        r = pygame.Rect(x + margem, y + margem, CEL - 2 * margem, CEL - 2 * margem)
        pygame.draw.rect(sup, cor, r, border_radius=8)
        if (c + 1, l) in paredes:
            pygame.draw.rect(sup, cor, (x + meio, r.y, CEL, r.h))
        if (c, l + 1) in paredes:
            pygame.draw.rect(sup, cor, (r.x, y + meio, r.w, CEL))
        if {(c + 1, l), (c, l + 1), (c + 1, l + 1)} <= paredes:
            pygame.draw.rect(sup, cor, (x + meio, y + meio, CEL, CEL))


# ============================================================
# SPRITES (desenhados uma vez só)
# ============================================================

_sprites = {}


def _semente_sup():
    s = _sprites.get("semente")
    if s is None:
        s = pygame.Surface((10, 12), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (150, 120, 60), (2, 3, 7, 9))
        pygame.draw.ellipse(s, (255, 230, 150), (1, 1, 7, 9))
        pygame.draw.ellipse(s, (255, 250, 215), (2, 2, 3, 3))
        _sprites["semente"] = s
    return s


def _pimenta_sup():
    s = _sprites.get("pimenta")
    if s is None:
        s = pygame.Surface((28, 30), pygame.SRCALPHA)
        # Corpo curvado (vários círculos seguindo uma curva)
        for i in range(9):
            t = i / 8
            x = 11 + math.sin(t * 2.2) * 5
            y = 9 + t * 17
            r = 7 - t * 4.5
            pygame.draw.circle(s, (150, 20, 20), (int(x) + 1, int(y) + 1), max(2, int(r)))
        for i in range(9):
            t = i / 8
            x = 11 + math.sin(t * 2.2) * 5
            y = 9 + t * 17
            r = 7 - t * 4.5
            pygame.draw.circle(s, (230, 40, 40), (int(x), int(y)), max(1, int(r) - 1))
        pygame.draw.ellipse(s, (255, 150, 140), (7, 6, 4, 7))
        # Cabinho verde
        pygame.draw.rect(s, (60, 150, 50), (6, 3, 11, 4), border_radius=2)
        pygame.draw.line(s, (60, 150, 50), (11, 4), (15, 0), 3)
        _sprites["pimenta"] = s
    return s


def _fruta_sup(tipo):
    chave = "fruta_" + tipo
    s = _sprites.get(chave)
    if s is not None:
        return s
    s = pygame.Surface((34, 34), pygame.SRCALPHA)
    if tipo == "limao":
        ui.limao(s, (17, 18), 12)
    elif tipo == "morango":
        pontos = [(5, 11), (29, 11), (26, 22), (17, 31), (8, 22)]
        pygame.draw.polygon(s, (170, 20, 40), [(x + 1, y + 1) for x, y in pontos])
        pygame.draw.polygon(s, (235, 45, 65), pontos)
        pygame.draw.circle(s, (235, 45, 65), (10, 13), 6)
        pygame.draw.circle(s, (235, 45, 65), (24, 13), 6)
        for x, y in ((11, 15), (17, 13), (23, 15), (14, 21), (20, 21), (17, 26)):
            pygame.draw.circle(s, (255, 230, 120), (x, y), 1)
        for dx in (-7, -3, 0, 3, 7):
            pygame.draw.line(s, (60, 160, 60), (17, 8), (17 + dx, 3 + abs(dx) // 2), 3)
    else:
        # Bolinho com cobertura e cereja
        pygame.draw.rect(s, (150, 90, 50), (5, 16, 24, 14), border_radius=4)
        for x in range(8, 28, 5):
            pygame.draw.line(s, (120, 70, 40), (x, 17), (x, 29), 1)
        pygame.draw.ellipse(s, (255, 170, 210), (3, 8, 28, 13))
        pygame.draw.ellipse(s, (255, 220, 240), (8, 9, 12, 5))
        pygame.draw.circle(s, (220, 30, 50), (17, 7), 5)
        pygame.draw.circle(s, (255, 140, 150), (15, 5), 2)
    _sprites[chave] = s
    return s


def _utensilio_sup(tipo, modo):
    """
    Corpo do utensílio (sem os olhos). modo: "normal", "medo" ou "pisca".
    Os olhos são desenhados na hora, olhando para onde ele vai.
    """
    chave = ("ut", tipo, modo)
    s = _sprites.get(chave)
    if s is not None:
        return s

    s = pygame.Surface((40, 40), pygame.SRCALPHA)
    cor = dict((u[0], u[1]) for u in UTENSILIOS)[tipo]
    metal = (200, 200, 215)
    if modo == "medo":
        cor, metal, escuro = AZUL_MEDO, AZUL_MEDO, (60, 80, 170)
    elif modo == "pisca":
        cor, metal, escuro = (245, 245, 255), (245, 245, 255), (170, 170, 200)
    else:
        escuro = ui.escurecer(cor, 80)

    if tipo == "frigideira":
        # Cabo para cima e à direita
        pygame.draw.line(s, escuro, (28, 16), (38, 5), 7)
        pygame.draw.line(s, cor, (28, 16), (38, 5), 4)
        fundo = (60, 60, 70) if modo == "normal" else cor
        pygame.draw.circle(s, escuro, (17, 23), 15)
        pygame.draw.circle(s, cor, (17, 23), 14)
        pygame.draw.circle(s, fundo, (17, 23), 11)
        if modo == "normal":
            pygame.draw.circle(s, (90, 90, 105), (12, 18), 4)
    elif tipo == "batedeira":
        # Arames do batedor + cabo embaixo
        pygame.draw.rect(s, escuro, (15, 26, 10, 14), border_radius=4)
        pygame.draw.rect(s, cor, (16, 27, 8, 12), border_radius=3)
        pygame.draw.ellipse(s, ui.misturar(cor, BRANCO, 0.55), (6, 1, 28, 30))
        for larg in (28, 18, 8):
            r = pygame.Rect(0, 0, larg, 30)
            r.midtop = (20, 1)
            pygame.draw.ellipse(s, metal if modo == "normal" else escuro, r, 2)
    elif tipo == "ralador":
        # Caixa de ralar (trapézio) com alça
        pygame.draw.rect(s, escuro, (14, 0, 12, 8), 3, border_radius=4)
        corpo = [(10, 7), (30, 7), (35, 38), (5, 38)]
        pygame.draw.polygon(s, escuro, [(x + 1, y + 1) for x, y in corpo])
        pygame.draw.polygon(s, cor, corpo)
        pygame.draw.polygon(s, escuro, corpo, 2)
        for y in range(25, 36, 5):
            for x in range(10 + (y % 2) * 2, 31, 5):
                pygame.draw.circle(s, escuro, (x, y), 1)
    else:
        # Espátula: cabeça larga com frestas + cabo
        pygame.draw.rect(s, (110, 70, 40) if modo == "normal" else escuro, (17, 26, 6, 14),
                         border_radius=2)
        pygame.draw.rect(s, escuro, (5, 1, 30, 27), border_radius=7)
        pygame.draw.rect(s, cor, (6, 2, 28, 25), border_radius=6)
        for x in (12, 20, 28):
            pygame.draw.line(s, escuro, (x, 19), (x, 24), 2)

    # Boca ondulada quando está com medo
    if modo != "normal":
        boca = (255, 255, 255) if modo == "medo" else (230, 60, 60)
        y = 21 if tipo != "batedeira" else 19
        pontos = [(11 + i * 3, y + (2 if i % 2 else 0)) for i in range(7)]
        pygame.draw.lines(s, boca, False, pontos, 2)

    _sprites[chave] = s
    return s


# Onde ficam os olhos em cada utensílio (em relação ao centro 20,20)
OLHOS = {"frigideira": (-3, 0), "batedeira": (0, -6), "ralador": (0, -3), "espatula": (0, -7)}


def _desenhar_olhos(tela, centro, olhar, deslocamento=(0, 0), medo=False):
    cx, cy = centro[0] + deslocamento[0], centro[1] + deslocamento[1]
    for lado in (-1, 1):
        ox = cx + lado * 6
        if medo:
            pygame.draw.circle(tela, (255, 255, 255), (int(ox), int(cy)), 3)
            continue
        olho = pygame.Rect(0, 0, 9, 11)
        olho.center = (int(ox), int(cy))
        pygame.draw.ellipse(tela, (255, 255, 255), olho)
        pygame.draw.ellipse(tela, (40, 40, 60), olho, 1)
        pygame.draw.circle(tela, (30, 40, 110),
                           (int(ox + olhar[0] * 2), int(cy + olhar[1] * 3)), 2)


# ============================================================
# ATORES (ovo e utensílios andam de célula em célula)
# ============================================================

class Ator:
    """
    Anda pela grade: está saindo da célula `cel` na direção `dir`
    e já andou `prog` (0..1) do caminho até a próxima.
    """

    def __init__(self, cel, direcao=PARADO):
        self.cel = cel
        self.dir = direcao
        self.prog = 0.0

    @property
    def pos(self):
        return (self.cel[0] + self.dir[0] * self.prog, self.cel[1] + self.dir[1] * self.prog)

    def inverter(self):
        if self.dir == PARADO:
            return
        if self.prog > 0:
            self.cel = _vizinha(self.cel, self.dir)
            self.prog = 1.0 - self.prog
        self.dir = _oposta(self.dir)


class Utensilio(Ator):

    def __init__(self, tipo, cor, casa, canto, espera):
        super().__init__(casa)
        self.tipo = tipo
        self.cor = cor
        self.casa = casa
        self.canto = canto
        self.espera = espera
        self.assustado = False
        self.estado = "casa"        # casa, saindo, normal, olhos, entrando
        self.sx, self.sy = float(casa[0]), float(casa[1])
        self.caminho = []
        if casa == FORA_DA_CASA:
            # A frigideira já começa do lado de fora
            self.estado = "normal"
            self.dir = ESQ

    @property
    def pos(self):
        if self.estado in ("casa", "saindo", "entrando"):
            return (self.sx, self.sy)
        return super().pos

    def olhar(self):
        if self.estado in ("casa", "saindo", "entrando") and self.caminho:
            alvo = self.caminho[0]
            dx, dy = alvo[0] - self.sx, alvo[1] - self.sy
            if abs(dx) > abs(dy):
                return (1 if dx > 0 else -1, 0)
            return (0, 1 if dy > 0 else -1) if dy else (0, 0)
        return self.dir


# ============================================================
# JOGO
# ============================================================

class OvoMan(MiniJogo):

    ID = "ovo_man"
    TITULO = "OVO-MAN"
    TITULO_CURTO = "OVO-MAN"
    DESCRICAO = "Coma todas as sementes da horta fugindo dos utensílios de cozinha. A PIMENTA vira o jogo!"
    COR = (60, 150, 90)
    INSTRUCOES = [
        "Coma todas as SEMENTES da horta!",
        "Fuja da frigideira, da batedeira, do ralador e da espátula.",
        "Pegue a PIMENTA: eles fogem e você pode comê-los!",
        "Aperte antes da esquina que o ovo vira sozinho.",
        "SETAS ou WASD para mover",
    ]
    OPCOES = None
    MENOR_MELHOR = False
    ROTULO_PONTOS = "PONTOS"
    CONTAGEM = True

    TRILHA = dict(bpm=150, tom="Eb", escala="menor", lead="quadrada", duty=0.25,
                  envelope="staccato", baixo="sincopado", onda_baixo="serra",
                  acomp="arpejo16", onda_acomp="sino", bateria="galope",
                  energia=0.85, eco=(0.1, 0.15))

    MOEDAS_POR = 150
    MOEDAS_MAX = 45

    # --------------------------------------------------------
    # CENÁRIO: horta à noite com cerca-viva
    # --------------------------------------------------------

    @classmethod
    def criar_fundo(cls, jogador):
        sup = ui.gradiente(LARGURA, ALTURA, (8, 12, 36), (30, 22, 58))
        rnd = random.Random(7)

        # Estrelas nas margens
        for _ in range(170):
            x, y = rnd.randrange(LARGURA), rnd.randrange(ALTURA)
            if AREA.inflate(16, 16).collidepoint(x, y):
                continue
            cor = rnd.choice([(255, 255, 255), (200, 210, 255), (255, 240, 180)])
            if rnd.random() < 0.15:
                ui.estrela(sup, (x, y), 4, cor, rnd.random())
            else:
                pygame.draw.circle(sup, cor, (x, y), rnd.choice((1, 1, 2)))

        # Lua
        lua = (88, 190)
        for r, a in ((70, 0.12), (56, 0.2)):
            pygame.draw.circle(sup, ui.misturar((30, 22, 58), (255, 250, 210), a), lua, r)
        pygame.draw.circle(sup, (250, 245, 210), lua, 42)
        for dx, dy, r in ((-12, -8, 8), (14, 10, 6), (6, -18, 4), (-6, 18, 5)):
            pygame.draw.circle(sup, (225, 220, 185), (lua[0] + dx, lua[1] + dy), r)

        # Margem direita: espantalho de galhos e pés de alface
        for i in range(5):
            y = 360 + i * 70
            x = 936 + (i % 2) * 34
            pygame.draw.ellipse(sup, (30, 90, 40), (x - 22, y - 10, 44, 26))
            pygame.draw.ellipse(sup, (70, 160, 70), (x - 18, y - 12, 36, 22))
            pygame.draw.ellipse(sup, (120, 200, 100), (x - 9, y - 9, 18, 12))
        for i in range(4):
            y = 400 + i * 80
            x = 50 + (i % 2) * 60
            pygame.draw.polygon(sup, (200, 100, 30), [(x - 7, y), (x + 7, y), (x, y + 30)])
            for dx in (-6, 0, 6):
                pygame.draw.line(sup, (60, 150, 60), (x, y), (x + dx, y - 14), 3)

        # Solo escuro da horta
        pygame.draw.rect(sup, (40, 30, 25), AREA)
        for _ in range(700):
            x = rnd.randrange(AREA.left, AREA.right)
            y = rnd.randrange(AREA.top, AREA.bottom)
            pygame.draw.circle(sup, rnd.choice([(55, 42, 34), (48, 36, 30), (32, 24, 20)]),
                               (x, y), rnd.choice((1, 1, 2)))

        cls._cerca_viva(sup, rnd)

        # Portinha da casa dos utensílios
        px, py = X0 + PORTA[0] * CEL, Y0 + PORTA[1] * CEL
        pygame.draw.rect(sup, (40, 30, 25), (px, py, CEL, CEL))
        pygame.draw.rect(sup, (255, 190, 220), (px - 2, py + 13, CEL + 4, 6), border_radius=3)
        pygame.draw.rect(sup, (200, 120, 160), (px - 2, py + 13, CEL + 4, 6), 1, border_radius=3)

        # Casa: chão de ladrilho
        casa = pygame.Rect(X0 + 8 * CEL, Y0 + 9 * CEL, 5 * CEL, CEL)
        pygame.draw.rect(sup, (70, 52, 45), casa)
        for i in range(10):
            pygame.draw.rect(sup, (84, 64, 55), (casa.x + i * 16, casa.y + (i % 2) * 16, 16, 16))

        # Setinhas no túnel
        for x in (X0 - 16, AREA.right + 16):
            y = Y0 + LINHA_TUNEL * CEL + CEL // 2
            pygame.draw.circle(sup, (60, 50, 90), (x, y), 12)
            pygame.draw.circle(sup, (120, 110, 170), (x, y), 12, 2)
        return sup

    @staticmethod
    def _cerca_viva(sup, rnd):
        """Paredes: blocos arredondados de cerca-viva que se juntam."""
        paredes = {(c, l) for l in range(LINHAS) for c in range(COLS) if MAPA[l][c] == "#"}

        _blocos(sup, paredes, 3, (20, 70, 35), 3)          # sombra
        _blocos(sup, paredes, 3, (40, 140, 70))            # cerca
        _blocos(sup, paredes, 8, (70, 180, 90), -2)        # topo mais claro

        # Folhinhas
        for c, l in paredes:
            for _ in range(3):
                x = X0 + c * CEL + rnd.randint(6, CEL - 8)
                y = Y0 + l * CEL + rnd.randint(4, CEL - 8)
                cor = rnd.choice([(95, 200, 105), (50, 150, 75), (120, 215, 120)])
                pygame.draw.ellipse(sup, cor, (x, y, 5, 3))
            if rnd.random() < 0.06:
                x = X0 + c * CEL + rnd.randint(8, CEL - 8)
                y = Y0 + l * CEL + rnd.randint(8, CEL - 8)
                cor = rnd.choice([(255, 150, 190), (255, 240, 120), (255, 255, 255)])
                for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
                    pygame.draw.circle(sup, cor, (x + dx, y + dy), 2)
                pygame.draw.circle(sup, (255, 200, 40), (x, y), 1)

    @classmethod
    def desenhar_icone(cls, sup, jogador):
        w, h = sup.get_size()
        y = h // 2 + 8
        semente = _semente_sup()
        for i in range(4):
            sup.blit(semente, (w // 2 - 2 + i * 14, y - 6))
        jogador.desenhar(sup, (w // 2 - 30, y), 40, angulo=-8)
        corpo = pygame.transform.smoothscale(_utensilio_sup("frigideira", "normal"), (46, 46))
        r = corpo.get_rect(center=(w // 2 + 74, y - 4))
        sup.blit(corpo, r)
        _desenhar_olhos(sup, (r.centerx - 3, r.centery + 3), (-1, 0))
        sup.blit(_pimenta_sup(), (w // 2 - 90, y - 44))

    # --------------------------------------------------------
    # PARTIDA
    # --------------------------------------------------------

    def reiniciar(self):
        self.vidas = VIDAS
        self.nivel = 1
        self.ganhou_extra = False
        self.teclas = set()
        self.parada = 0.0           # "hit-stop" ao comer utensílio
        self.flash = 0.0            # flash vermelho da pimenta
        self._montar_nivel()

    def _montar_nivel(self):
        self.sementes = set()
        self.pimentas = set()
        for l, linha in enumerate(MAPA):
            for c, ch in enumerate(linha):
                if ch == "." and (c, l) != INICIO_OVO:
                    self.sementes.add((c, l))
                elif ch == "o":
                    self.pimentas.add((c, l))
        self.total_sementes = len(self.sementes) + len(self.pimentas)
        self.comidas = 0
        self.frutas_saidas = 0
        self.fruta = None
        self.tempo_fruta = 0.0
        self._posicionar()

    def _posicionar(self):
        """Coloca todo mundo no lugar (começo de nível ou depois de perder vida)."""
        self.ovo = Ator(INICIO_OVO)
        self.olhando = ESQ
        self.desejo = None
        self.tempo_desejo = 0.0
        self.balanco = 0.0          # distância andada (para o balanço)
        self.gulp = 0.0
        self.espera_som = 0.0
        self.som_alterna = False
        self.fumaca = 0.0

        self.utensilios = [Utensilio(*u) for u in UTENSILIOS]
        reducao = min(3.0, (self.nivel - 1) * 1.0)
        for u in self.utensilios:
            u.espera = max(0.0, u.espera - reducao)
        self.modo_indice = 0
        self.modo_tempo = 0.0
        self.pimenta = 0.0
        self.combo = 0

        self.fase = "jogo"          # jogo, pronto, morrendo, limpo
        self.tempo_fase = 0.0

    # --------------------------------------------------------
    # ENTRADA
    # --------------------------------------------------------

    def evento(self, e):
        # Guarda as teclas seguradas em qualquer estado (não "grudam" na pausa)
        if e.type == pygame.KEYDOWN:
            self.teclas.add(e.key)
        elif e.type == pygame.KEYUP:
            self.teclas.discard(e.key)
        elif e.type == pygame.WINDOWFOCUSLOST:
            self.teclas.clear()
        super().evento(e)

    def evento_jogo(self, e):
        if e.type == pygame.KEYDOWN and e.key in TECLAS:
            self.desejo = TECLAS[e.key]
            self.tempo_desejo = BUFFER_CURVA
            self._tentar_virar()

    def _segurando(self, direcao):
        return any(k in self.teclas for k, d in TECLAS.items() if d == direcao)

    def _tentar_virar(self):
        """Meia-volta na hora; curva logo depois do centro (tolerância de 4 px)."""
        ovo, d = self.ovo, self.desejo
        if d is None or self.fase != "jogo":
            return
        if ovo.dir != PARADO and d == _oposta(ovo.dir):
            ovo.inverter()
            self.olhando = d
        elif (ovo.dir != PARADO and d != ovo.dir and 0 < ovo.prog <= TOLERANCIA
              and not _parede(_vizinha(ovo.cel, d))):
            ovo.prog = 0.0
            ovo.dir = d
            self.olhando = d

    # --------------------------------------------------------
    # LÓGICA
    # --------------------------------------------------------

    @property
    def aceleracao(self):
        return min(MAX_ACELERACAO, 1.05 ** (self.nivel - 1))

    def atualizar_jogo(self, dt):
        self.flash = max(0.0, self.flash - dt)
        self.gulp = max(0.0, self.gulp - dt)
        self.espera_som = max(0.0, self.espera_som - dt)
        self.tempo_fase += dt

        if self.parada > 0:
            self.parada -= dt
            return

        if self.fase == "pronto":
            if self.tempo_fase >= 1.4:
                self.fase = "jogo"
                self.tempo_fase = 0.0
            return
        if self.fase == "morrendo":
            if self.tempo_fase >= 1.8:
                self._depois_de_morrer()
            return
        if self.fase == "limpo":
            if self.tempo_fase >= 2.0:
                self.nivel += 1
                self._montar_nivel()
                self.fase = "pronto"
                self.tempo_fase = 0.0
            return

        # Buffer de curva: vale enquanto a tecla estiver segurada
        if self.desejo is not None:
            if self._segurando(self.desejo):
                self.tempo_desejo = BUFFER_CURVA
            else:
                self.tempo_desejo -= dt
                if self.tempo_desejo <= 0:
                    self.desejo = None
        self._tentar_virar()

        # Ovo
        antes = self.ovo.pos
        self._avancar(self.ovo, VEL_OVO * self.aceleracao * dt, self._decidir_ovo, self._chegou_ovo)
        depois = self.ovo.pos
        self.balanco += abs(depois[0] - antes[0]) + abs(depois[1] - antes[1])

        # Pimenta e modos
        if self.pimenta > 0:
            self.pimenta -= dt
            if self.pimenta <= 0:
                self.pimenta = 0.0
                for u in self.utensilios:
                    u.assustado = False
            self.fumaca -= dt
            if self.fumaca <= 0:
                self.fumaca = 0.12
                x, y = _tela(self.ovo.pos)
                for lado in (-1, 1):
                    self.particulas.explodir((x + lado * 12, y - 6), [(200, 200, 210), (150, 150, 160)],
                                             1, 40, 0.6, (3, 5), -120)
        else:
            self._atualizar_modo(dt)

        for u in self.utensilios:
            self._mover_utensilio(u, dt)

        # Fruta bônus
        if self.fruta:
            self.tempo_fruta -= dt
            if self.tempo_fruta <= 0:
                self.fruta = None

        self._colisoes()

    def _atualizar_modo(self, dt):
        modo, duracao = MODOS[self.modo_indice]
        if duracao is None:
            return
        self.modo_tempo += dt
        if self.modo_tempo >= duracao:
            self.modo_tempo = 0.0
            self.modo_indice += 1
            # Troca de modo: todo mundo dá meia-volta (o aviso clássico)
            for u in self.utensilios:
                if u.estado == "normal":
                    u.inverter()

    @property
    def modo(self):
        return MODOS[self.modo_indice][0]

    def _avancar(self, ator, dist, decidir, chegou=None):
        """Anda `dist` células, decidindo a direção a cada centro de célula."""
        voltas = 0
        while dist > 1e-9 and voltas < 12:
            voltas += 1
            if ator.prog <= 0:
                ator.prog = 0.0
                nova = decidir(ator)
                if nova == PARADO:
                    ator.dir = PARADO
                    return
                ator.dir = nova
            falta = 1.0 - ator.prog
            if dist < falta:
                ator.prog += dist
                return
            dist -= falta
            ator.cel = _vizinha(ator.cel, ator.dir)
            ator.prog = 0.0
            if chegou and chegou(ator):
                return

    # --- ovo ---

    def _decidir_ovo(self, ovo):
        if self.desejo is not None and not _parede(_vizinha(ovo.cel, self.desejo)):
            self.olhando = self.desejo
            return self.desejo
        if ovo.dir != PARADO and not _parede(_vizinha(ovo.cel, ovo.dir)):
            return ovo.dir
        return PARADO

    def _chegou_ovo(self, ovo):
        cel = ovo.cel
        if cel in self.sementes:
            self.sementes.discard(cel)
            self._comeu(PONTOS_SEMENTE, cel)
        elif cel in self.pimentas:
            self.pimentas.discard(cel)
            self._comeu(PONTOS_PIMENTA, cel)
            self._pegar_pimenta(cel)
        if self.fruta and cel == LUGAR_FRUTA:
            tipo, valor = self.fruta
            self.fruta = None
            self._somar(valor)
            pos = _tela(cel)
            self.textos.adicionar(str(valor), (pos[0], pos[1] - 16), (255, 150, 200), 14)
            self.particulas.explodir(pos, [(255, 120, 150), AMARELO, BRANCO], 18, 180)
            self.som("moeda")
        if self.fase != "jogo":
            return True
        return False

    def _comeu(self, valor, cel):
        self._somar(valor)
        self.comidas += 1
        self.gulp = 0.12
        if self.espera_som <= 0:
            self.espera_som = 0.08
            self.som_alterna = not self.som_alterna
            self.som("comer" if self.som_alterna else "ponto", 0.25)

        # Frutas aparecem 2x por nível
        if self.frutas_saidas < 2 and self.comidas >= self.total_sementes * (0.35 + 0.35 * self.frutas_saidas):
            self.frutas_saidas += 1
            self.fruta = FRUTAS[min(self.nivel, len(FRUTAS)) - 1]
            self.tempo_fruta = TEMPO_FRUTA

        if not self.sementes and not self.pimentas:
            self._nivel_limpo()

    def _somar(self, valor):
        antes = self.pontos
        self.pontos += valor
        if not self.ganhou_extra and antes < VIDA_EXTRA <= self.pontos:
            self.ganhou_extra = True
            self.vidas += 1
            self.som("acerto")
            self.textos.adicionar("+1 VIDA!", (AREA.centerx, AREA.y + 40), (140, 255, 140), 16)

    def _pegar_pimenta(self, cel):
        self.pimenta = max(3.0, 7.0 - (self.nivel - 1))
        self.combo = 0
        self.flash = 0.3
        self.tremer(0.1)
        self.som("acerto", 0.8)
        self.particulas.explodir(_tela(cel), [(230, 40, 40), (255, 150, 60), AMARELO], 20, 200)
        for u in self.utensilios:
            if u.estado != "olhos":
                if u.estado == "normal" and not u.assustado:
                    u.inverter()
                u.assustado = True

    def _nivel_limpo(self):
        self.fase = "limpo"
        self.tempo_fase = 0.0
        self.fruta = None
        self.pimenta = 0.0
        self.som("bandeira")
        self.textos.adicionar("HORTA LIMPA!", (AREA.centerx, _tela(LUGAR_FRUTA)[1]), AMARELO, 20)

    # --- utensílios ---

    def _alvo(self, u):
        ovo = self.ovo.cel
        olhar = self.olhando
        if self.modo == "espalhar":
            return u.canto
        if u.tipo == "frigideira":
            return ovo
        if u.tipo == "batedeira":
            return (ovo[0] + olhar[0] * 4, ovo[1] + olhar[1] * 4)
        if u.tipo == "ralador":
            frig = self.utensilios[0].cel
            p = (ovo[0] + olhar[0] * 2, ovo[1] + olhar[1] * 2)
            return (2 * p[0] - frig[0], 2 * p[1] - frig[1])
        # Espátula: persegue de longe, foge para o canto de perto
        dist = math.hypot(u.cel[0] - ovo[0], u.cel[1] - ovo[1])
        return ovo if dist > 8 else u.canto

    def _decidir_utensilio(self, u):
        opcoes = [d for d in ORDEM if not _parede(_vizinha(u.cel, d))]
        if not opcoes:
            return PARADO
        volta = _oposta(u.dir)
        if len(opcoes) > 1 and volta in opcoes:
            opcoes.remove(volta)
        if u.assustado and u.estado == "normal":
            return random.choice(opcoes)
        alvo = FORA_DA_CASA if u.estado == "olhos" else self._alvo(u)

        def distancia(d):
            c = _vizinha(u.cel, d)
            return (c[0] - alvo[0]) ** 2 + (c[1] - alvo[1]) ** 2
        return min(opcoes, key=distancia)

    def _chegou_utensilio(self, u):
        if u.estado == "olhos" and u.cel == FORA_DA_CASA:
            self._entrar_em_casa(u)
            return True
        return False

    def _entrar_em_casa(self, u):
        u.estado = "entrando"
        u.sx, u.sy = float(FORA_DA_CASA[0]), float(FORA_DA_CASA[1])
        u.caminho = [CENTRO_CASA]
        u.dir = BAIXO
        u.prog = 0.0

    def _mover_utensilio(self, u, dt):
        acel = self.aceleracao
        if u.estado == "casa":
            u.espera -= dt
            u.sy = u.casa[1] + math.sin(self.tempo * 6 + u.casa[0]) * 0.18
            if u.espera <= 0:
                u.estado = "saindo"
                u.caminho = [CENTRO_CASA, FORA_DA_CASA]
            return

        if u.estado in ("saindo", "entrando"):
            dist = VEL_CASA * dt if u.estado == "saindo" else VEL_OLHOS * 0.5 * dt
            while u.caminho and dist > 0:
                alvo = u.caminho[0]
                dx, dy = alvo[0] - u.sx, alvo[1] - u.sy
                d = math.hypot(dx, dy)
                if d <= dist:
                    u.sx, u.sy = float(alvo[0]), float(alvo[1])
                    u.caminho.pop(0)
                    dist -= d
                else:
                    u.sx += dx / d * dist
                    u.sy += dy / d * dist
                    dist = 0
            if not u.caminho:
                if u.estado == "saindo":
                    u.estado = "normal"
                    u.cel = FORA_DA_CASA
                    u.prog = 0.0
                    u.dir = random.choice((ESQ, DIR))
                else:
                    # Voltou para casa: renasce e sai de novo
                    u.estado = "casa"
                    u.assustado = False
                    u.espera = 0.4
                    u.casa = CENTRO_CASA
            return

        if u.estado == "olhos":
            vel = VEL_OLHOS
        elif _no_tunel(u.cel):
            vel = VEL_TUNEL * acel
        elif u.assustado:
            vel = VEL_ASSUSTADO * acel
        else:
            vel = VEL_UTENSILIO * acel
        self._avancar(u, vel * dt, self._decidir_utensilio, self._chegou_utensilio)

    def _colisoes(self):
        if self.fase != "jogo":
            return
        ox, oy = self.ovo.pos
        for u in self.utensilios:
            if u.estado != "normal":
                continue
            ux, uy = u.pos
            dx = abs(ox - ux)
            dx = min(dx, COLS - dx)
            if dx * dx + (oy - uy) ** 2 > 0.55 ** 2:
                continue
            if u.assustado:
                self._comer_utensilio(u)
            else:
                self._morrer()
                return

    def _comer_utensilio(self, u):
        valor = PONTOS_UTENSILIO[min(self.combo, len(PONTOS_UTENSILIO) - 1)]
        self.combo += 1
        self._somar(valor)
        pos = _tela(u.pos)
        self.textos.adicionar(str(valor), (pos[0], pos[1] - 18), (140, 220, 255), 16)
        self.particulas.explodir(pos, [AZUL_MEDO, BRANCO, u.cor], 16, 200)
        self.som("boing")
        self.parada = 0.15
        u.estado = "olhos"
        u.assustado = False
        if u.cel == FORA_DA_CASA and u.prog < 0.05:
            self._entrar_em_casa(u)

    def _morrer(self):
        self.fase = "morrendo"
        self.tempo_fase = 0.0
        self.pimenta = 0.0
        self.fruta = None
        self.tremer(0.3)
        self.som("erro")
        pos = _tela(self.ovo.pos)
        self.particulas.explodir(pos, [AMARELO, BRANCO, (255, 190, 60)], 26, 220)
        self.textos.adicionar("OVO MEXIDO!", (pos[0], pos[1] - 30), AMARELO, 16)

    def _depois_de_morrer(self):
        self.vidas -= 1
        if self.vidas <= 0:
            self.terminar(linhas=[f"PONTOS: {self.pontos}", f"NÍVEL: {self.nivel}"])
            return
        self._posicionar()
        self.fase = "pronto"
        self.tempo_fase = 0.0

    # --------------------------------------------------------
    # DESENHO
    # --------------------------------------------------------

    def desenhar_jogo(self, tela):
        tela.blit(self.fundo(self.jogador), (0, 0))
        t = self.tempo

        # Nível limpo: a cerca pisca branco 3x
        if self.fase == "limpo" and int(self.tempo_fase * 3) % 2 == 0 and self.tempo_fase < 1.8:
            tela.blit(_mascara_paredes(), AREA.topleft)

        # Sementes
        semente = _semente_sup()
        for c, l in self.sementes:
            tela.blit(semente, (X0 + c * CEL + 11, Y0 + l * CEL + 10))

        # Pimentas pulsando
        pim = _pimenta_sup()
        esc = 1.0 + 0.12 * math.sin(t * 7)
        sup = pygame.transform.smoothscale(pim, (int(28 * esc), int(30 * esc)))
        for cel in self.pimentas:
            tela.blit(sup, sup.get_rect(center=_tela(cel)))

        # Fruta bônus (pisca nos últimos 2 segundos)
        if self.fruta and (self.tempo_fruta > 2 or int(t * 8) % 2 == 0):
            fx, fy = _tela(LUGAR_FRUTA)
            f = _fruta_sup(self.fruta[0])
            tela.blit(f, f.get_rect(center=(fx, fy + math.sin(t * 4) * 2)))

        # Utensílios (somem durante a morte do ovo)
        if not (self.fase == "morrendo" and self.tempo_fase > 0.4) and self.fase != "limpo":
            for u in self.utensilios:
                self._desenhar_utensilio(tela, u)

        self._desenhar_ovo(tela)

        self.particulas.desenhar(tela)
        self.textos.desenhar(tela)

        if self.flash > 0:
            ui.veu(tela, int(90 * self.flash / 0.3), (255, 40, 30))

        if self.estado == "jogando" and self.fase == "pronto":
            x, y = _tela(LUGAR_FRUTA)
            ui.desenhar_texto(tela, "PRONTO!", (x, y), 16, AMARELO, "center")

    def _desenhar_ovo(self, tela):
        ovo = self.ovo
        x, y = _tela(ovo.pos)
        espelhar = self.olhando == ESQ

        if self.fase == "morrendo":
            k = self.tempo_fase
            if k < 0.9:
                # Gira cada vez mais rápido e encolhe
                ang = k * k * 1400
                alt = ALTURA_OVO * max(0.2, 1 - k * 0.9)
                self.jogador.desenhar(tela, (x, y), alt, espelhar=espelhar, angulo=ang)
            else:
                self._ovo_mexido(tela, (x, y), min(1.0, (k - 0.9) * 4))
            return

        # Balança enquanto rola; "gulp" ao comer
        andando = ovo.dir != PARADO and self.fase == "jogo"
        ang = math.sin(self.balanco * 2.6) * 12 if andando else 0.0
        inclina = {DIR: -8, ESQ: 8}.get(self.olhando, 0) if andando else 0
        sup = self.jogador.avatar(ALTURA_OVO)
        if self.pimenta > 0:
            sup = self._avatar_pimenta(sup)
        if espelhar:
            sup = pygame.transform.flip(sup, True, False)
        if self.gulp > 0:
            k = math.sin(math.pi * self.gulp / 0.12)
            w, h = sup.get_size()
            sup = pygame.transform.smoothscale(sup, (int(w * (1 + 0.18 * k)), int(h * (1 - 0.16 * k))))
        if ang + inclina:
            sup = pygame.transform.rotate(sup, ang + inclina)
        # Centro do ovo fica um pouco abaixo do centro da imagem
        r = sup.get_rect(center=(round(x), round(y - ALTURA_OVO * 0.06)))
        self._blit_tunel(tela, sup, r)

    def _avatar_pimenta(self, sup):
        """Versão vermelho-fogo do avatar (piscando no fim da pimenta)."""
        if self.pimenta < 2 and int(self.tempo * 8) % 2 == 0:
            return sup
        chave = (id(sup), sup.get_size())
        if getattr(self, "_cache_pimenta", (None,))[0] != chave:
            # Mistura o avatar com uma versão avermelhada (o rosto continua visível)
            vermelho = sup.copy()
            vermelho.fill((255, 70, 40), special_flags=pygame.BLEND_RGB_MULT)
            vermelho.fill((70, 0, 0), special_flags=pygame.BLEND_RGB_ADD)
            vermelho.set_alpha(165)
            quente = sup.copy()
            quente.blit(vermelho, (0, 0))
            self._cache_pimenta = (chave, quente)
        return self._cache_pimenta[1]

    def _blit_tunel(self, tela, sup, r):
        """Desenha e, perto do túnel, repete do outro lado (recortado)."""
        if AREA.left - 4 <= r.left and r.right <= AREA.right + 4:
            tela.blit(sup, r)
            return
        tela.set_clip(AREA)
        tela.blit(sup, r)
        tela.blit(sup, r.move(COLS * CEL if r.centerx < AREA.centerx else -COLS * CEL, 0))
        tela.set_clip(None)

    def _ovo_mexido(self, tela, centro, k):
        """Espiral amarela de ovo mexido."""
        x, y = centro
        r = int(15 * k) + 2
        pygame.draw.ellipse(tela, (255, 250, 235), (x - r - 4, y - r * 0.7, (r + 4) * 2, r * 1.5))
        pontos = []
        for i in range(30):
            a = i * 0.45 + self.tempo * 3
            rr = r * i / 30
            pontos.append((x + math.cos(a) * rr, y + math.sin(a) * rr * 0.75))
        if len(pontos) > 1:
            pygame.draw.lines(tela, (255, 200, 40), False, pontos, 4)
        pygame.draw.circle(tela, (255, 215, 60), (int(x), int(y)), max(2, r // 3))

    def _desenhar_utensilio(self, tela, u):
        x, y = _tela(u.pos)
        olhar = u.olhar()

        # Perto do túnel: desenha dos dois lados, recortado no labirinto
        if u.pos[0] < 0.5 or u.pos[0] > COLS - 1.5:
            tela.set_clip(AREA)
            for desloc in (0, COLS * CEL if x < AREA.centerx else -COLS * CEL):
                self._desenhar_utensilio_em(tela, u, x + desloc, y, olhar)
            tela.set_clip(None)
        else:
            self._desenhar_utensilio_em(tela, u, x, y, olhar)

    def _desenhar_utensilio_em(self, tela, u, x, y, olhar):
        if u.estado in ("olhos", "entrando"):
            sup = None
        elif u.assustado:
            pisca = self.pimenta < 2 and int(self.tempo * 8) % 2 == 0
            sup = _utensilio_sup(u.tipo, "pisca" if pisca else "medo")
            x += math.sin(self.tempo * 50 + u.casa[0]) * 1.5      # tremendo de medo
        else:
            sup = _utensilio_sup(u.tipo, "normal")

        oy = math.sin(self.tempo * 10 + u.casa[0]) * 1.5 if u.estado == "normal" else 0
        dx, dy = OLHOS[u.tipo]
        if sup is not None:
            tela.blit(sup, sup.get_rect(center=(round(x), round(y + oy - 1))))
            _desenhar_olhos(tela, (x, y + oy - 1), olhar, (dx, dy), medo=u.assustado)
        else:
            _desenhar_olhos(tela, (x, y), olhar, (dx, dy))

    def desenhar_hud(self, tela):
        caixa = pygame.Rect(12, 12, 300, 48)
        ui.painel(tela, caixa, (20, 24, 40), BRANCO, 12, 3, sombra=False)
        ui.desenhar_texto(tela, f"PONTOS: {self.pontos}", (caixa.x + 16, caixa.centery), 14,
                          AMARELO, "midleft")
        rec = self.recorde()
        if rec is not None:
            ui.desenhar_texto(tela, f"RECORDE: {rec}", (caixa.right + 16, caixa.centery), 12,
                              (180, 200, 255), "midleft")

        # Nível e vidas (ovinhos) antes do botão de pausa
        mostrar = min(self.vidas, 5)
        largura = 150 + mostrar * 30
        caixa = pygame.Rect(0, 12, largura, 48)
        caixa.right = LARGURA - 76
        ui.painel(tela, caixa, (20, 24, 40), BRANCO, 12, 3, sombra=False)
        ui.desenhar_texto(tela, f"NÍVEL {self.nivel}", (caixa.x + 14, caixa.centery), 12,
                          (140, 255, 160), "midleft")
        for i in range(mostrar):
            self.jogador.desenhar(tela, (caixa.right - 22 - i * 30, caixa.centery + 1), 24)

        # Tempo de pimenta
        if self.estado == "jogando" and self.pimenta > 0:
            larg = int(200 * self.pimenta / max(3.0, 7.0 - (self.nivel - 1)))
            barra = pygame.Rect(0, 0, 204, 14)
            barra.midtop = (LARGURA // 2, 72)
            pygame.draw.rect(tela, (20, 24, 40), barra, border_radius=7)
            pygame.draw.rect(tela, (230, 60, 40), (barra.x + 2, barra.y + 2, larg, 10), border_radius=5)
            pygame.draw.rect(tela, BRANCO, barra, 2, border_radius=7)
            ui.desenhar_texto(tela, "PIMENTA!", (barra.x - 10, barra.centery), 10,
                              (255, 140, 110), "midright")


_mascara = None


def _mascara_paredes():
    """Cerca-viva em branco (para piscar quando a horta fica limpa)."""
    global _mascara
    if _mascara is None:
        _mascara = pygame.Surface(AREA.size, pygame.SRCALPHA)
        paredes = {(c, l) for l in range(LINHAS) for c in range(COLS) if MAPA[l][c] == "#"}
        _blocos(_mascara, paredes, 3, (255, 255, 255, 170), 0, (0, 0))
    return _mascara
