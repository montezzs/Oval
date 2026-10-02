import math
import random

import pygame

from settings import *
from core import ui
from jogos.base import MiniJogo

# ============================================================
# CORRIDA DO OVO
# ============================================================
# O ovo sai rolando pela rua do BRINCAR com o TOTÓ correndo
# atrás! Pule hidrantes, cones, caixas e buracos, abaixe dos
# passarinhos e pegue os limões. Quanto mais longe, mais rápido.
#
#   CASCA EXTRA -> escudo que aguenta 1 batida
#   ÍMÃ         -> puxa os limões por 5 segundos
#   TURBO       -> 3 segundos invencível e bem mais rápido

# Cenário
CEU_ALTURA = 560
CALCADA_Y = 560                 # começo da calçada
ASFALTO_Y = 600                 # começo do asfalto
CHAO = 585                      # onde a base do ovo encosta

# Ovo
OVO_X = 220
OVO_ALT = 80
OVO_ALT_BAIXO = 48              # "ovo deitado" ao abaixar
RAIO_ROLAR = 40

# Mundo
VEL_INICIAL = 360.0
ACEL_MUNDO = 8.0                # px/s a mais a cada segundo
VEL_MAX = 820.0
PX_METRO = 40

# Pulo
VEL_PULO = 900.0
GRAVIDADE = 2600.0
GRAV_EXTRA = 3000.0             # abaixar no ar = queda rápida
TEMPO_AR = 2 * VEL_PULO / GRAVIDADE     # ~0.69 s
BUFFER_PULO = 0.1
COYOTE = 0.08
TEMPO_MIN_PULO = 0.1            # soltar antes disso só corta o pulo aqui
TEMPO_ABAIXAR = 0.6

# Obstáculos: (largura, altura)
TAMANHOS = {
    "hidrante": (40, 60),
    "cone": (36, 50),
    "caixa": (60, 60),
    "passaro": (46, 30),
    "bicicleta": (120, 50),
}
Y_PASSARO = CHAO - 73           # centro do passarinho (altura da cabeça)
VEL_PASSARO = 40.0              # voa na sua direção
VEL_BICICLETA = 80.0            # pedala na sua direção

# Power-ups
TEMPO_IMA = 5.0
RAIO_IMA = 200
TEMPO_TURBO = 3.0
TEMPO_PISCA = 1.0               # invencível depois de gastar o escudo/turbo
INTERVALO_PODER = 15.0

TECLAS_PULO = (pygame.K_SPACE, pygame.K_w, pygame.K_UP, pygame.K_RETURN, pygame.K_KP_ENTER)
TECLAS_BAIXO = (pygame.K_s, pygame.K_DOWN)

# Casinhas do BRINCAR: (parede, telhado)
CASAS = [
    ((255, 200, 150), (190, 130, 70)),
    ((255, 235, 60), (255, 230, 230)),
    ((30, 100, 40), (70, 40, 150)),
]
PORTA = (60, 40, 30)

LARG_NUVENS = 2048
LARG_CASAS = 260 * 8

_camadas = {}


def _elipse_rect(cx, cy, a, b, r):
    """A elipse (centro, semi-eixos a/b) encosta no retângulo r?"""
    px = max(r[0], min(cx, r[0] + r[2]))
    py = max(r[1], min(cy, r[1] + r[3]))
    dx = (px - cx) / a
    dy = (py - cy) / b
    return dx * dx + dy * dy < 1.0


# ============================================================
# DESENHOS PRÉ-RENDERIZADOS
# ============================================================

def _nuvem(sup, cx, cy, largura, rnd):
    bolas = []
    n = max(3, largura // 34)
    for i in range(n):
        ox = -largura / 2 + largura * (i + 0.5) / n
        r = rnd.randint(18, 24) if i in (0, n - 1) else rnd.randint(26, 36)
        bolas.append((int(cx + ox), int(cy - r * 0.4), r))
    pygame.draw.ellipse(sup, (225, 240, 252), (cx - largura // 2 - 6, cy - 8, largura + 12, 34))
    for x, y, r in bolas:
        pygame.draw.circle(sup, (225, 240, 252), (x, y + 4), r)
    pygame.draw.ellipse(sup, BRANCO, (cx - largura // 2, cy - 12, largura, 30))
    for x, y, r in bolas:
        pygame.draw.circle(sup, BRANCO, (x, y), r)


def _casa(sup, x, base, parede, telhado, rnd):
    """Casinha 220x230 com telhado triangular."""
    corpo = pygame.Rect(x, base - 230, 220, 230)
    escuro = ui.escurecer(parede, 45)
    pygame.draw.rect(sup, parede, corpo)
    pygame.draw.rect(sup, escuro, corpo, 4)
    # Tijolinhos/textura
    for _ in range(14):
        tx = rnd.randint(corpo.x + 10, corpo.right - 30)
        ty = rnd.randint(corpo.y + 10, corpo.bottom - 20)
        pygame.draw.rect(sup, ui.escurecer(parede, 18), (tx, ty, 18, 7), 1)

    # Telhado
    beiral = [(corpo.x - 18, corpo.y + 2), (corpo.right + 18, corpo.y + 2),
              (corpo.centerx, corpo.y - 84)]
    pygame.draw.polygon(sup, telhado, beiral)
    pygame.draw.polygon(sup, ui.escurecer(telhado, 60), beiral, 4)
    for i in range(1, 4):
        t = i / 4
        y = corpo.y + 2 - 86 * (1 - t)
        meia = (corpo.w / 2 + 18) * t
        pygame.draw.line(sup, ui.escurecer(telhado, 30), (corpo.centerx - meia, y),
                         (corpo.centerx + meia, y), 2)
    # Chaminé
    pygame.draw.rect(sup, (150, 80, 60), (corpo.right - 60, corpo.y - 70, 24, 44))
    pygame.draw.rect(sup, (100, 50, 40), (corpo.right - 60, corpo.y - 70, 24, 44), 3)

    # Porta
    porta = pygame.Rect(corpo.centerx - 26, base - 86, 52, 86)
    pygame.draw.rect(sup, PORTA, porta, border_top_left_radius=26, border_top_right_radius=26)
    pygame.draw.rect(sup, (30, 20, 15), porta, 3, border_top_left_radius=26,
                     border_top_right_radius=26)
    pygame.draw.circle(sup, (240, 200, 90), (porta.right - 12, porta.centery + 6), 4)

    # Janelas
    for jx in (corpo.x + 22, corpo.right - 70):
        jan = pygame.Rect(jx, corpo.y + 34, 48, 44)
        pygame.draw.rect(sup, (170, 220, 255), jan)
        pygame.draw.polygon(sup, (220, 244, 255), [(jan.x, jan.bottom - 10), (jan.x + 20, jan.y),
                                                   (jan.x + 34, jan.y), (jan.x, jan.bottom)])
        pygame.draw.rect(sup, BRANCO, jan, 5)
        pygame.draw.line(sup, BRANCO, (jan.centerx, jan.y), (jan.centerx, jan.bottom), 3)
        pygame.draw.rect(sup, (120, 80, 50), (jan.x - 6, jan.bottom, jan.w + 12, 7))
        for fx in range(jan.x, jan.right, 12):
            pygame.draw.circle(sup, rnd.choice([(255, 110, 140), (255, 230, 90), (190, 120, 255)]),
                               (fx + 4, jan.bottom - 2), 4)


def _criar_camadas():
    if _camadas:
        return _camadas
    rnd = random.Random(12)

    _camadas["ceu"] = ui.gradiente(LARGURA, CEU_ALTURA, (0, 180, 255), (150, 222, 255)).convert()

    # Nuvens (10% da velocidade)
    nuvens = pygame.Surface((LARG_NUVENS, 260), pygame.SRCALPHA)
    for i in range(9):
        cx = int((i + 0.5) * LARG_NUVENS / 9 + rnd.randint(-40, 40))
        cy = rnd.randint(70, 210)
        _nuvem(nuvens, cx, cy, rnd.randint(110, 200), rnd)
    _camadas["nuvens"] = nuvens

    # Casinhas (35% da velocidade)
    casas = pygame.Surface((LARG_CASAS, 340), pygame.SRCALPHA)
    base = 340
    for i in range(8):
        x0 = i * 260
        # Arbusto e poste entre as casas
        pygame.draw.circle(casas, (60, 150, 70), (x0 + 244, base - 18), 22)
        pygame.draw.circle(casas, (80, 175, 80), (x0 + 232, base - 26), 16)
        parede, telhado = CASAS[i % len(CASAS)]
        _casa(casas, x0 + 20, base, parede, telhado, rnd)
        if i % 2 == 0:
            pygame.draw.rect(casas, (90, 90, 100), (x0 + 250, base - 150, 6, 150))
            pygame.draw.rect(casas, (60, 60, 70), (x0 + 240, base - 160, 26, 12), border_radius=4)
            pygame.draw.circle(casas, (255, 240, 170), (x0 + 253, base - 144), 6)
    _camadas["casas"] = casas

    # Chão parado (calçada + asfalto); juntas e faixas são desenhadas rolando
    chao = pygame.Surface((LARGURA, ALTURA - CALCADA_Y))
    chao.fill((170, 170, 170))
    pygame.draw.rect(chao, (190, 190, 190), (0, 0, LARGURA, 6))
    pygame.draw.rect(chao, (20, 20, 20), (0, ASFALTO_Y - CALCADA_Y, LARGURA, ALTURA - ASFALTO_Y))
    pygame.draw.rect(chao, (120, 120, 125), (0, ASFALTO_Y - CALCADA_Y, LARGURA, 8))
    pygame.draw.rect(chao, (90, 90, 95), (0, ASFALTO_Y - CALCADA_Y + 8, LARGURA, 3))
    for _ in range(260):
        x = rnd.randrange(LARGURA)
        y = rnd.randrange(ASFALTO_Y - CALCADA_Y + 12, ALTURA - CALCADA_Y)
        pygame.draw.circle(chao, rnd.choice([(34, 34, 36), (12, 12, 14)]), (x, y), 1)
    _camadas["chao"] = chao.convert()
    return _camadas


_sprites = {}


def _sprite(tipo):
    """Obstáculos desenhados uma vez (cache)."""
    s = _sprites.get(tipo)
    if s is not None:
        return s

    if tipo == "hidrante":
        s = pygame.Surface((40, 60), pygame.SRCALPHA)
        verm, escuro = (220, 50, 50), (140, 25, 30)
        pygame.draw.rect(s, escuro, (2, 50, 36, 10), border_radius=3)
        pygame.draw.rect(s, verm, (7, 16, 26, 38), border_radius=4)
        pygame.draw.rect(s, escuro, (7, 16, 26, 38), 2, border_radius=4)
        pygame.draw.ellipse(s, verm, (6, 2, 28, 22))
        pygame.draw.ellipse(s, escuro, (6, 2, 28, 22), 2)
        pygame.draw.rect(s, escuro, (16, 0, 8, 6), border_radius=2)
        pygame.draw.rect(s, verm, (0, 24, 40, 10), border_radius=4)
        pygame.draw.rect(s, escuro, (0, 24, 40, 10), 2, border_radius=4)
        pygame.draw.circle(s, (240, 200, 90), (20, 29), 5)
        pygame.draw.rect(s, (255, 150, 140), (11, 20, 4, 26), border_radius=2)
    elif tipo == "cone":
        s = pygame.Surface((36, 50), pygame.SRCALPHA)
        lar, escuro = (255, 140, 40), (190, 90, 20)
        pygame.draw.rect(s, escuro, (0, 42, 36, 8), border_radius=2)
        corpo = [(18, 0), (31, 43), (5, 43)]
        pygame.draw.polygon(s, lar, corpo)
        for y1, y2 in ((12, 18), (26, 33)):
            m1 = 13 * y1 / 43
            m2 = 13 * y2 / 43
            pygame.draw.polygon(s, BRANCO, [(18 - m1, y1), (18 + m1, y1), (18 + m2, y2), (18 - m2, y2)])
        pygame.draw.polygon(s, escuro, corpo, 2)
    elif tipo == "caixa":
        s = pygame.Surface((60, 60), pygame.SRCALPHA)
        pap, escuro = (200, 150, 90), (140, 95, 50)
        pygame.draw.rect(s, pap, (0, 0, 60, 60), border_radius=3)
        pygame.draw.rect(s, escuro, (0, 0, 60, 60), 3, border_radius=3)
        pygame.draw.rect(s, (225, 190, 130), (24, 0, 12, 60))
        pygame.draw.line(s, escuro, (3, 14), (57, 14), 2)
        # Setinha "este lado para cima"
        pygame.draw.polygon(s, escuro, [(10, 34), (16, 26), (22, 34)])
        pygame.draw.rect(s, escuro, (14, 34, 4, 12))
        pygame.draw.polygon(s, escuro, [(38, 34), (44, 26), (50, 34)])
        pygame.draw.rect(s, escuro, (42, 34, 4, 12))
    _sprites[tipo] = s
    return s


def _desenhar_passaro(tela, cx, cy, t):
    """Passarinho azul (gordinho) voando para a esquerda, batendo as asas."""
    cx, cy = int(cx), int(cy)
    asa = math.sin(t * 22)
    contorno = (30, 60, 120)
    # Rabo de penas
    for dy in (-6, 0, 6):
        pygame.draw.line(tela, contorno, (cx + 12, cy), (cx + 27, cy - 4 + dy), 6)
        pygame.draw.line(tela, (70, 130, 210), (cx + 12, cy), (cx + 26, cy - 4 + dy), 3)
    # Asa de trás
    ponta = (cx + 4, cy - 4 - 22 * asa)
    pygame.draw.polygon(tela, contorno, [(cx - 6, cy - 4), (cx + 12, cy - 2), ponta])
    # Corpo redondo e cabeça
    pygame.draw.circle(tela, contorno, (cx + 2, cy + 1), 15)
    pygame.draw.circle(tela, (90, 160, 235), (cx + 2, cy + 1), 13)
    pygame.draw.circle(tela, contorno, (cx - 12, cy - 5), 11)
    pygame.draw.circle(tela, (90, 160, 235), (cx - 12, cy - 5), 9)
    pygame.draw.ellipse(tela, (230, 240, 255), (cx - 10, cy + 2, 20, 10))
    # Asa da frente
    ponta = (cx + 2, cy - 2 - 24 * asa)
    pygame.draw.polygon(tela, contorno, [(cx - 6, cy), (cx + 14, cy + 2), ponta])
    pygame.draw.polygon(tela, (150, 205, 255), [(cx - 3, cy), (cx + 11, cy + 1),
                                                (ponta[0] + 1, ponta[1] + 3 * asa)])
    # Bico e olho
    pygame.draw.polygon(tela, (255, 170, 40), [(cx - 19, cy - 8), (cx - 29, cy - 4), (cx - 19, cy - 1)])
    pygame.draw.polygon(tela, (190, 110, 20), [(cx - 19, cy - 8), (cx - 29, cy - 4), (cx - 19, cy - 1)], 1)
    pygame.draw.circle(tela, BRANCO, (cx - 13, cy - 8), 4)
    pygame.draw.circle(tela, (20, 20, 30), (cx - 14, cy - 8), 2)


def _desenhar_toto(tela, x, y_pe, t, correndo=True, lingua=False):
    """O TOTÓ (cachorro caramelo) virado para a direita. x = centro do corpo."""
    x, y_pe = int(x), int(y_pe)
    cor, escuro, contorno = (214, 150, 80), (170, 105, 50), (90, 55, 25)
    fase = t * 16 if correndo else t * 4
    pulo = abs(math.sin(fase)) * 5 if correndo else 0
    y = y_pe - pulo

    # Rabo abanando
    rabo = math.sin(t * 20) * 10
    pygame.draw.line(tela, contorno, (x - 30, y - 38), (x - 50, y - 58 + rabo), 9)
    pygame.draw.line(tela, cor, (x - 30, y - 38), (x - 50, y - 58 + rabo), 5)

    # Pernas (de trás e da frente balançando)
    for px, desloc in ((x - 22, 0.0), (x - 10, math.pi), (x + 12, math.pi * 0.5), (x + 24, math.pi * 1.5)):
        ang = math.sin(fase + desloc) * (0.5 if correndo else 0.05)
        pe = (px + math.sin(ang) * 20, y - 2 - (1 - math.cos(ang)) * 8)
        pygame.draw.line(tela, contorno, (px, y - 26), pe, 10)
        pygame.draw.line(tela, escuro if desloc in (0.0, math.pi) else cor, (px, y - 26), pe, 6)

    # Corpo
    corpo = pygame.Rect(x - 36, y - 52, 72, 34)
    pygame.draw.ellipse(tela, contorno, corpo.inflate(6, 6))
    pygame.draw.ellipse(tela, cor, corpo)
    pygame.draw.ellipse(tela, (240, 205, 150), (x - 18, y - 34, 36, 14))

    # Cabeça
    hx, hy = x + 36, y - 62
    pygame.draw.circle(tela, contorno, (hx, hy), 21)
    pygame.draw.circle(tela, cor, (hx, hy), 18)
    pygame.draw.ellipse(tela, contorno, (hx + 6, hy - 3, 26, 20))
    pygame.draw.ellipse(tela, (240, 205, 150), (hx + 8, hy - 1, 22, 16))
    pygame.draw.circle(tela, (30, 20, 20), (hx + 28, hy + 2), 5)
    pygame.draw.circle(tela, (30, 20, 20), (hx + 6, hy - 6), 4)
    pygame.draw.circle(tela, BRANCO, (hx + 7, hy - 7), 1)
    if lingua:
        pygame.draw.ellipse(tela, (200, 60, 90), (hx + 14, hy + 10, 12, 16))
        pygame.draw.ellipse(tela, (255, 120, 150), (hx + 15, hy + 10, 10, 13))

    # Orelhas balançando
    bal = math.sin(fase * 1.3) * 0.5 if correndo else math.sin(t * 3) * 0.15
    for dx, extra in ((-10, 0.0), (-2, 0.3)):
        a = 0.4 + bal + extra
        base = (hx + dx, hy - 14)
        ponta = (base[0] - math.sin(a) * 22, base[1] + math.cos(a) * 22)
        lado = (base[0] + 9, base[1] + 2)
        pygame.draw.polygon(tela, contorno, [base, ponta, lado])
        pygame.draw.polygon(tela, escuro, [(base[0] + 1, base[1] + 2), (ponta[0] + 1, ponta[1] - 3),
                                           (lado[0] - 2, lado[1])])


def _desenhar_bicicleta(tela, jogador, x, t, chao=CHAO):
    """Bicicleta do ROBERT (x = esquerda, chao = onde as rodas encostam)."""
    y = chao
    r = 17
    giro = t * 14
    rodas = ((x + 20, y - r), (x + 100, y - r))
    for cx, cy in rodas:
        pygame.draw.circle(tela, (30, 30, 40), (cx, cy), r, 4)
        pygame.draw.circle(tela, (150, 150, 160), (cx, cy), 3)
        for k in range(3):
            a = giro + k * math.pi / 3
            dx, dy = math.cos(a) * (r - 3), math.sin(a) * (r - 3)
            pygame.draw.line(tela, (150, 150, 160), (cx - dx, cy - dy), (cx + dx, cy + dy), 1)
    selim = (x + 72, y - 46)
    guidao = (x + 30, y - 52)
    pedal = (x + 62, y - 16)
    cor = (60, 190, 120)
    for a, b in ((rodas[1], selim), (selim, pedal), (pedal, rodas[1]), (pedal, (x + 34, y - 40)),
                 (selim, (x + 34, y - 40)), ((x + 34, y - 40), rodas[0]), (guidao, rodas[0])):
        pygame.draw.line(tela, cor, a, b, 5)
    pygame.draw.line(tela, (30, 30, 40), (guidao[0] - 8, guidao[1]), (guidao[0] + 4, guidao[1] - 4), 5)
    pygame.draw.rect(tela, (40, 40, 50), (selim[0] - 10, selim[1] - 5, 22, 7), border_radius=3)
    # ROBERT pedalando (outra cor e outras partes)
    ap = jogador.aparencia()
    robert = ((ap[0] + 2) % 4, (ap[1] + 3) % 8, (ap[2] + 1) % 3, (ap[3] + 3) % 6)
    jogador.desenhar(tela, (selim[0] - 2, selim[1] - 16), 34, aparencia=robert)


def _desenhar_capsula(tela, tipo, cx, cy, t):
    """Power-up flutuando: bolha com o ícone."""
    cx, cy = int(cx), int(cy + math.sin(t * 4) * 4)
    cores = {"casca": (120, 220, 255), "ima": (255, 110, 110), "turbo": (255, 210, 60)}
    cor = cores[tipo]
    pygame.draw.circle(tela, ui.escurecer(cor, 90), (cx, cy), 21)
    pygame.draw.circle(tela, cor, (cx, cy), 18)
    pygame.draw.circle(tela, ui.clarear(cor, 60), (cx - 7, cy - 7), 5)
    if tipo == "casca":
        pygame.draw.ellipse(tela, BRANCO, (cx - 9, cy - 11, 18, 22))
        pygame.draw.lines(tela, (120, 130, 150), False,
                          [(cx - 9, cy), (cx - 5, cy - 4), (cx - 1, cy + 1), (cx + 3, cy - 4),
                           (cx + 9, cy)], 2)
    elif tipo == "ima":
        pygame.draw.arc(tela, (180, 20, 30), (cx - 10, cy - 10, 20, 22), math.pi, math.tau, 6)
        pygame.draw.rect(tela, (180, 20, 30), (cx - 10, cy - 8, 6, 9))
        pygame.draw.rect(tela, (180, 20, 30), (cx + 4, cy - 8, 6, 9))
        pygame.draw.rect(tela, BRANCO, (cx - 10, cy - 12, 6, 5))
        pygame.draw.rect(tela, BRANCO, (cx + 4, cy - 12, 6, 5))
    else:
        raio = [(cx + 3, cy - 13), (cx - 7, cy + 2), (cx - 1, cy + 2), (cx - 4, cy + 13),
                (cx + 7, cy - 3), (cx + 1, cy - 3)]
        pygame.draw.polygon(tela, (200, 90, 20), raio)
        pygame.draw.polygon(tela, BRANCO, raio, 1)


# ============================================================
# OBSTÁCULO
# ============================================================

class Obstaculo:

    def __init__(self, tipo, x, largura=None):
        self.tipo = tipo
        self.x = float(x)                   # borda esquerda
        if tipo == "buraco":
            self.w, self.h = largura, 0
        else:
            self.w, self.h = TAMANHOS[tipo]
        self.vx = {"passaro": VEL_PASSARO, "bicicleta": VEL_BICICLETA}.get(tipo, 0.0)
        self.fase = random.uniform(0, math.tau)
        self.bob = 0.0
        self.folga = 999.0                  # menor distância até o ovo (para o "UFA!")
        self.passou = False
        self.voando = None                  # [vx, vy, ang, giro, dy] quando é derrubado

    @property
    def direita(self):
        return self.x + self.w

    def rects(self):
        """Caixas de colisão (x, y, w, h)."""
        x = self.x
        if self.tipo == "passaro":
            return [(x + 4, Y_PASSARO - 12 + self.bob, self.w - 8, 24)]
        if self.tipo == "bicicleta":
            return [(x + 4, CHAO - 50, self.w - 8, 50), (x + 56, CHAO - 76, 28, 30)]
        if self.tipo == "hidrante":
            return [(x + 3, CHAO - self.h + 2, self.w - 6, self.h - 2)]
        if self.tipo == "cone":
            return [(x + 6, CHAO - self.h + 4, self.w - 12, self.h - 4)]
        return [(x, CHAO - self.h, self.w, self.h)]


# ============================================================
# JOGO
# ============================================================

class OvoCorredor(MiniJogo):

    ID = "ovo_corredor"
    TITULO = "CORRIDA DO OVO"
    TITULO_CURTO = "CORRIDA"
    DESCRICAO = "O ovo sai rolando pela rua com o TOTÓ atrás! Pule, abaixe e pegue os limões."
    COR = (255, 140, 40)
    INSTRUCOES = [
        "Seu ovo rola pela rua e o TOTÓ vem atrás!",
        "Pule hidrantes, cones, caixas e buracos.",
        "Abaixe dos passarinhos. Pegue LIMÕES (+10)!",
        "Bolhas: CASCA (escudo), ÍMÃ e TURBO.",
        "ESPAÇO/W/↑ ou CLIQUE pula • S/↓ abaixa",
    ]
    OPCOES = None
    MENOR_MELHOR = False
    ROTULO_PONTOS = "PONTOS"
    CONTAGEM = True

    MOEDAS_POR = 40
    MOEDAS_MAX = 45
    MOEDAS_MIN = 2

    # --------------------------------------------------------
    # CENÁRIO: rua do BRINCAR
    # --------------------------------------------------------

    @classmethod
    def criar_fundo(cls, jogador):
        c = _criar_camadas()
        sup = pygame.Surface((LARGURA, ALTURA))
        sup.blit(c["ceu"], (0, 0))
        sup.blit(c["nuvens"], (0, 0))
        sup.blit(c["casas"], (-60, CALCADA_Y - 340))
        sup.blit(c["chao"], (0, CALCADA_Y))
        cls._desenhar_rua(sup, 0)
        return sup

    @staticmethod
    def _desenhar_rua(tela, rolagem):
        """Juntas da calçada e faixas do asfalto (andam a 100%)."""
        off = rolagem % 64
        x = -off
        while x < LARGURA:
            pygame.draw.line(tela, (150, 150, 150), (int(x), CALCADA_Y + 6), (int(x) - 10, ASFALTO_Y), 2)
            x += 64
        off = rolagem % 260
        x = -off
        while x < LARGURA:
            pygame.draw.rect(tela, (255, 230, 60), (int(x), 655, 120, 14))
            x += 260

    @classmethod
    def desenhar_icone(cls, sup, jogador):
        w, h = sup.get_size()
        chao = int(h * 0.8)
        # Hidrante, ovo pulando e o Totó atrás
        hid = pygame.transform.smoothscale(_sprite("hidrante"), (16, 24))
        sup.blit(hid, (int(w * 0.72), chao - 24))
        jogador.desenhar(sup, (w // 2, chao - 38), 34, angulo=-25)
        for i in range(3):
            pygame.draw.line(sup, BRANCO, (w // 2 - 30 - i * 8, chao - 46 + i * 8),
                             (w // 2 - 48 - i * 8, chao - 46 + i * 8), 2)
        ui.limao(sup, (int(w * 0.78), chao - 58), 8)
        ui.limao(sup, (int(w * 0.64), chao - 66), 8)
        mini = pygame.Surface((140, 90), pygame.SRCALPHA)
        _desenhar_toto(mini, 60, 88, 0.3)
        mini = pygame.transform.smoothscale(mini, (56, 36))
        sup.blit(mini, (int(w * 0.08), chao - 35))

    # --------------------------------------------------------
    # PARTIDA
    # --------------------------------------------------------

    def reiniciar(self):
        _criar_camadas()
        self.relogio = 0.0
        self.vel = VEL_INICIAL
        self.vel_atual = VEL_INICIAL
        self.dist = 0.0                 # distância percorrida (pontos)
        self.rolagem = 0.0              # distância visual (continua ao morrer)
        self.bonus = 0
        self.limoes = 0

        # Ovo
        self.y_pe = float(CHAO)
        self.vy = 0.0
        self.no_chao = True
        self.coyote = COYOTE
        self.buffer = 0.0
        self.tempo_pulo = 0.0
        self.cortar = False
        self.cortou = True
        self.abaixar = 0.0
        self.angulo = 0.0
        self.giro_acum = 0.0
        self.squash = 0.0

        # Power-ups
        self.escudo = False
        self.ima = 0.0
        self.turbo = 0.0
        self.pisca = 0.0
        self.prox_poder = INTERVALO_PODER * random.uniform(0.6, 0.8)

        # Mundo
        self.obstaculos = []
        self.limoes_mundo = []          # [x, y]
        self.capsulas = []              # [tipo, x, y]
        self.linhas = []                # linhas de velocidade [x, y, comp]
        self.rastro = []                # rastro do turbo [x, y, vida, cor]
        self.prox_tipo = "hidrante"
        self.dist_prox = 0.0
        self._criar_obstaculo(760.0)
        self.dist_prox -= LARGURA + 20 - 760    # o primeiro já nasce na tela

        # Fim de jogo
        self.morto = False
        self.causa = ""
        self.tempo_morto = 0.0
        self.no_buraco = None
        self.toto_x = 72.0
        self.lambida = 0.0

        self.teclas = set()
        self.mouse_segurando = False

    # --------------------------------------------------------
    # CONTROLES
    # --------------------------------------------------------

    def evento(self, e):
        # Acompanha as teclas em qualquer estado (não "grudam" na pausa)
        if e.type == pygame.KEYDOWN:
            self.teclas.add(e.key)
        elif e.type == pygame.KEYUP:
            self.teclas.discard(e.key)
            if e.key in TECLAS_PULO:
                self._soltar_pulo()
        elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
            self.mouse_segurando = False
            self._soltar_pulo()
        elif e.type == pygame.WINDOWFOCUSLOST:
            self.teclas.clear()
            self.mouse_segurando = False
        super().evento(e)

    def evento_jogo(self, e):
        if self.morto:
            return
        if e.type == pygame.KEYDOWN:
            if e.key in TECLAS_PULO:
                self.buffer = BUFFER_PULO
            elif e.key in TECLAS_BAIXO:
                self.abaixar = TEMPO_ABAIXAR
                if not self.no_chao and self.vy < 0:
                    self.vy = 0.0           # desce na hora
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if not self.botao_pausa.collidepoint(e.pos):
                self.buffer = BUFFER_PULO
                self.mouse_segurando = True

    def _segurando_pulo(self):
        return self.mouse_segurando or any(k in self.teclas for k in TECLAS_PULO)

    def _soltar_pulo(self):
        """Soltou cedo: o pulo fica mais baixo (pulo variável)."""
        if not self._segurando_pulo() and not self.no_chao and self.vy < 0 and not self.cortou:
            self.cortar = True

    @property
    def abaixado(self):
        return self.abaixar > 0 or any(k in self.teclas for k in TECLAS_BAIXO)

    # --------------------------------------------------------
    # LÓGICA
    # --------------------------------------------------------

    def atualizar_jogo(self, dt):
        self.relogio += dt
        if self.morto:
            self._atualizar_morte(dt)
            return

        self.vel = min(VEL_MAX, VEL_INICIAL + ACEL_MUNDO * self.relogio)
        self.vel_atual = self.vel * (1.5 if self.turbo > 0 else 1.0)
        passo = self.vel_atual * dt
        self.dist += passo
        self.rolagem += passo

        # Timers
        self.abaixar = max(0.0, self.abaixar - dt)
        self.squash = max(0.0, self.squash - dt)
        self.ima = max(0.0, self.ima - dt)
        self.pisca = max(0.0, self.pisca - dt)
        if self.turbo > 0:
            self.turbo -= dt
            if self.turbo <= 0:
                self.turbo = 0.0
                self.pisca = TEMPO_PISCA            # não bate logo que acaba
            self._soltar_rastro()

        self._fisica(dt)
        self._mover_mundo(dt, passo)
        self._gerar(passo)
        if not self.morto:
            self._colidir()
        if not self.morto:
            self._coletar(dt)
        self._efeitos(dt)

        self.pontos = int(self.dist / PX_METRO) + self.limoes * 10 + self.bonus

    # ---------------- Ovo ----------------

    def _sobre_buraco(self):
        """Buraco embaixo do ovo (com uma bordinha de tolerância)."""
        for o in self.obstaculos:
            if o.tipo == "buraco" and o.x + 8 <= OVO_X - 6 and OVO_X + 6 <= o.direita - 8:
                return o
        return None

    def _fisica(self, dt):
        self.buffer = max(0.0, self.buffer - dt)
        # Com turbo (ou piscando logo depois) o ovo passa por cima dos buracos
        buraco = None if (self.turbo > 0 or self.pisca > 0) else self._sobre_buraco()

        if self.no_chao:
            self.coyote = COYOTE
            if buraco:
                self.no_chao = False        # começa a cair no buraco
                self.vy = 0.0
        else:
            self.coyote = max(0.0, self.coyote - dt)

        # Pulo (com buffer e coyote time)
        if self.buffer > 0 and (self.no_chao or (self.coyote > 0 and self.vy >= 0)):
            self._pular()

        if not self.no_chao:
            self.tempo_pulo += dt
            if self.cortar and self.tempo_pulo >= TEMPO_MIN_PULO:
                self.cortar = False
                self.cortou = True
                if self.vy < 0:
                    self.vy *= 0.5
            g = GRAVIDADE + (GRAV_EXTRA if self.abaixado else 0.0)
            self.vy += g * dt
            self.y_pe += self.vy * dt

            if self.vy >= 0 and self.y_pe >= CHAO:
                if buraco is None:
                    self._pousar()
                elif self.y_pe > CHAO + 8:
                    self._cair_no_buraco(buraco)

        # Rolar
        self.angulo = (self.angulo - math.degrees(self.vel_atual * dt / RAIO_ROLAR)) % 360
        if self.no_chao:
            self.giro_acum += self.vel_atual * dt
            if self.giro_acum >= math.tau * RAIO_ROLAR:
                self.giro_acum = 0.0
                self.particulas.explodir((OVO_X - 20, CHAO), [(200, 200, 200), (230, 230, 230)],
                                         5, 90, 0.4, (2, 5), 200)

    def _pular(self):
        self.vy = -VEL_PULO
        self.no_chao = False
        self.coyote = 0.0
        self.buffer = 0.0
        self.abaixar = 0.0
        self.tempo_pulo = 0.0
        self.cortou = False
        self.cortar = not self._segurando_pulo()
        self.som("pulo", 0.4)

    def _pousar(self):
        if self.vy > 500:
            self.particulas.explodir((OVO_X, CHAO), [(210, 210, 210), (240, 240, 240)], 8, 120,
                                     0.4, (2, 5), 200)
        self.y_pe = float(CHAO)
        self.vy = 0.0
        self.no_chao = True
        self.squash = 0.12
        self.cortar = False

    def _cair_no_buraco(self, buraco):
        if self.escudo:
            # A casca extra "quica" o ovo para fora do buraco
            self.escudo = False
            self.pisca = TEMPO_PISCA
            self.y_pe = float(CHAO)
            self.vy = -VEL_PULO
            self.tempo_pulo = 0.0
            self.cortou = True
            self.som("boing")
            self.textos.adicionar("UFA! CASCA!", (OVO_X, CHAO - 130), (120, 220, 255), 16)
            self._quebrar_casca()
            return
        self.no_buraco = buraco
        self._morrer("CAIU NO BURACO!")

    def _hitbox(self):
        """Elipse de colisão (80% do corpo): cx, cy, a, b."""
        if self.abaixado:
            h, w = OVO_ALT_BAIXO, OVO_ALT * 0.9 * 1.25
        else:
            h, w = OVO_ALT, OVO_ALT * 0.9
        return OVO_X, self.y_pe - h / 2, w * 0.4, h * 0.4

    # ---------------- Mundo ----------------

    def _mover_mundo(self, dt, passo):
        for o in self.obstaculos:
            o.x -= passo + o.vx * dt
            if o.tipo == "passaro":
                o.bob = math.sin(self.tempo * 5 + o.fase) * 3
            if o.voando:
                v = o.voando
                v[4] += v[1] * dt
                v[1] += 1800 * dt
                o.x += v[0] * dt + passo
                v[2] += v[3] * dt
        self.obstaculos = [o for o in self.obstaculos if o.direita > -80 and
                           (o.voando is None or o.voando[4] < 400)]

        for lim in self.limoes_mundo:
            lim[0] -= passo
        self.limoes_mundo = [l for l in self.limoes_mundo if l[0] > -30]
        for c in self.capsulas:
            c[1] -= passo
        self.capsulas = [c for c in self.capsulas if c[1] > -30]

    def _escolher_tipo(self):
        t = self.relogio
        tipos = [("hidrante", 3.0), ("cone", 3.0), ("caixa", 2.0)]
        if t >= 20:
            tipos.append(("buraco", 2.0))
        if t >= 30:
            tipos.append(("passaro", 2.2))
        if t >= 60:
            tipos.append(("bicicleta", 1.5))
        return random.choices([n for n, _ in tipos], [p for _, p in tipos])[0]

    def _largura_buraco(self):
        # Buracos mais largos quando está rápido (rolando rápido "pula" buraco pequeno)
        return int(random.uniform(90, 160) + (self.vel - VEL_INICIAL) * 0.15)

    def _gerar(self, passo):
        self.dist_prox -= passo
        if self.dist_prox <= 0:
            self._criar_obstaculo(LARGURA + 20 + self.dist_prox)

    def _criar_obstaculo(self, x):
        tipo = self.prox_tipo
        largura = self._largura_buraco() if tipo == "buraco" else None
        o = Obstaculo(tipo, x, largura)
        self.obstaculos.append(o)

        # Escolhe o próximo e a distância até ele (sempre dá para passar)
        prox = self._escolher_tipo()
        v = min(VEL_MAX, self.vel + 16)
        minimo = TEMPO_AR * v * 1.1 + 60
        if "passaro" in (tipo, prox):
            minimo = max(minimo, 1.2 * TEMPO_AR * v + 60)
        if prox == "passaro":
            minimo += VEL_PASSARO * LARGURA / v + 20     # ele voa na sua direção
        elif prox == "bicicleta":
            minimo += VEL_BICICLETA * LARGURA / v + 20
        vao = max(minimo, v * random.uniform(0.9, 1.6))
        self.prox_tipo = prox
        self.dist_prox += o.w + vao

        # Limões em arco por cima (ou por baixo do passarinho)
        if random.random() < 0.45 and self.relogio > 0:
            meio = o.x + o.w / 2
            esp = v * 0.09
            for k in range(-2, 3):
                if tipo == "passaro":
                    y = CHAO - 26
                else:
                    y = CHAO - OVO_ALT / 2 - (155 - 1300 * (0.09 * k) ** 2)
                self.limoes_mundo.append([meio + k * esp, y])

        # No vão: power-up ou uma fileira de limões no chão
        meio_vao = o.x + o.w + vao / 2
        if self.relogio > 0:
            self.prox_poder -= vao / v
            if self.prox_poder <= 0:
                self.prox_poder = INTERVALO_PODER * random.uniform(0.85, 1.15)
                pesos = [3, 3, 2]
                tipo_p = random.choices(["casca", "ima", "turbo"], pesos)[0]
                if tipo_p == "casca" and self.escudo:
                    tipo_p = "ima"
                self.capsulas.append([tipo_p, meio_vao, CHAO - 55])
            elif random.random() < 0.3:
                for k in range(-2, 3):
                    self.limoes_mundo.append([meio_vao + k * 42, CHAO - 40])

    # ---------------- Colisão e coleta ----------------

    def _colidir(self):
        cx, cy, a, b = self._hitbox()
        topo_ovo, pe_ovo = cy - b, cy + b
        invencivel = self.turbo > 0 or self.pisca > 0

        for o in self.obstaculos:
            if o.tipo == "buraco" or o.voando:
                continue
            rects = o.rects()
            # "UFA!": quanto passou raspando enquanto estava em cima/embaixo
            if o.x < cx + a and o.direita > cx - a:
                if o.tipo == "passaro":
                    folga = topo_ovo - (rects[0][1] + rects[0][3])
                else:
                    folga = min(r[1] for r in rects) - pe_ovo
                o.folga = min(o.folga, folga)

            if any(_elipse_rect(cx, cy, a, b, r) for r in rects):
                if self.turbo > 0:
                    self._derrubar(o, "POW!")
                elif invencivel:
                    continue
                elif self.escudo:
                    self.escudo = False
                    self.pisca = TEMPO_PISCA
                    self._derrubar(o, "CASCA!")
                    self._quebrar_casca()
                else:
                    self._morrer("TROMBOU!")
                    return
                continue

            if not o.passou and o.direita < cx - a:
                o.passou = True
                if o.folga <= 12 and not invencivel:
                    self.bonus += 5
                    self.som("ponto", 0.6)
                    self.textos.adicionar("UFA! +5", (OVO_X + 20, CHAO - OVO_ALT - 50),
                                          (255, 240, 150), 14)

    def _derrubar(self, o, texto):
        o.voando = [random.uniform(250, 400), -random.uniform(550, 750), 0.0,
                    random.choice((-1, 1)) * 540, 0.0]
        self.som("bater", 0.8)
        self.tremer(0.12)
        pos = (o.x + o.w / 2, CHAO - max(20, o.h))
        self.particulas.explodir(pos, [BRANCO, AMARELO, (255, 160, 60)], 14, 240, 0.5)
        self.textos.adicionar(texto, (pos[0], pos[1] - 30), AMARELO, 16)

    def _quebrar_casca(self):
        cx, cy, _, _ = self._hitbox()
        self.particulas.explodir((cx, cy), [BRANCO, (230, 235, 245), (200, 210, 225)], 20, 260, 0.7)

    def _coletar(self, dt):
        cx, cy, a, b = self._hitbox()
        vivos = []
        for lim in self.limoes_mundo:
            dx, dy = lim[0] - cx, lim[1] - cy
            dist = math.hypot(dx, dy)
            if self.ima > 0 and dist < RAIO_IMA and dist > 1:
                passo = min(dist, 700 * dt)
                lim[0] -= dx / dist * passo
                lim[1] -= dy / dist * passo
                dist -= passo
            if dist < 36:
                self.limoes += 1
                self.som("moeda", 0.6)
                self.particulas.explodir((lim[0], lim[1]), [(250, 222, 40), (255, 248, 180)], 8, 150, 0.4)
                self.textos.adicionar("+10", (lim[0], lim[1] - 20), AMARELO, 12)
                continue
            vivos.append(lim)
        self.limoes_mundo = vivos

        restantes = []
        for c in self.capsulas:
            if math.hypot(c[1] - cx, c[2] - cy) < 44:
                self._pegar_poder(c[0], (c[1], c[2]))
                continue
            restantes.append(c)
        self.capsulas = restantes

    def _pegar_poder(self, tipo, pos):
        self.som("acerto")
        cores = [self.jogador.cor, self.jogador.cor_clara, BRANCO, AMARELO]
        self.particulas.explodir(pos, cores, 24, 260, 0.7)
        if tipo == "casca":
            self.escudo = True
            nome = "CASCA EXTRA!"
        elif tipo == "ima":
            self.ima = TEMPO_IMA
            nome = "ÍMÃ!"
        else:
            self.turbo = TEMPO_TURBO
            nome = "TURBO!"
        self.textos.adicionar(nome, (pos[0], pos[1] - 60), (255, 240, 150), 20)

    # ---------------- Efeitos ----------------

    def _soltar_rastro(self):
        cx, cy, _, _ = self._hitbox()
        cores = (self.jogador.cor, self.jogador.cor_clara, self.jogador.cor_escura)
        cor = cores[int(self.tempo * 30) % 3]
        self.rastro.append([cx - 30, cy + random.uniform(-18, 18), 0.35, cor])

    def _efeitos(self, dt):
        # Rastro do turbo vai ficando para trás
        for r in self.rastro:
            r[0] -= self.vel_atual * dt * 0.8
            r[2] -= dt
        self.rastro = [r for r in self.rastro if r[2] > 0]

        # Linhas de velocidade
        if self.vel_atual > 650 and not self.morto and random.random() < dt * 14:
            self.linhas.append([LARGURA + 10, random.uniform(90, 540), random.uniform(60, 150)])
        for l in self.linhas:
            l[0] -= self.vel_atual * 1.8 * dt
        self.linhas = [l for l in self.linhas if l[0] + l[2] > 0]

    # ---------------- Fim ----------------

    def _morrer(self, causa):
        self.morto = True
        self.causa = causa
        self.tempo_morto = 0.0
        self.abaixar = 0.0
        self.turbo = 0.0
        self.tremer(0.3)
        self.som("bater")
        cx, cy, _, _ = self._hitbox()
        self.particulas.explodir((cx + 20, cy), [BRANCO, AMARELO, self.jogador.cor], 20, 240, 0.6)
        self.vel_atual = 0.0            # a rua para na hora
        self.linhas.clear()
        self.ima = 0.0

    def _atualizar_morte(self, dt):
        self.tempo_morto += dt
        # A rua está parada; só os efeitos continuam
        for o in self.obstaculos:
            if o.voando:
                v = o.voando
                v[4] += v[1] * dt
                v[1] += 1800 * dt
                o.x += v[0] * dt
                v[2] += v[3] * dt
        self._efeitos(dt)
        self.squash = max(0.0, self.squash - dt)
        # O ovo volta a ficar em pé (para mostrar a carinha)
        ang = (self.angulo + 180) % 360 - 180
        self.angulo = ang * max(0.0, 1 - dt * 6)

        if self.no_buraco is not None:
            # Afunda devagar no buraco
            self.y_pe = min(CHAO + 70, self.y_pe + 160 * dt)
        elif not self.no_chao:
            self.vy += GRAVIDADE * dt
            self.y_pe = min(float(CHAO), self.y_pe + self.vy * dt)
            if self.y_pe >= CHAO:
                self.no_chao = True

        # O Totó alcança e lambe o ovo
        alvo = OVO_X - 80
        if self.no_buraco is not None:
            alvo = min(alvo, self.no_buraco.x - 72)
        if self.toto_x < alvo:
            self.toto_x = min(alvo, self.toto_x + 280 * dt)
        else:
            self.lambida -= dt
            if self.lambida <= 0:
                self.lambida = 0.35
                self.som("ponto", 0.3)
                self.textos.adicionar("♥", (OVO_X - 30 + random.uniform(-10, 10), CHAO - 110),
                                      (255, 110, 150), 16)

        if self.tempo_morto > 2.4:
            metros = int(self.dist / PX_METRO)
            self.terminar(titulo=self.causa, linhas=[f"DISTÂNCIA: {metros} m",
                                                    f"LIMÕES: {self.limoes}",
                                                    f"PONTOS: {self.pontos}"])

    # --------------------------------------------------------
    # DESENHO
    # --------------------------------------------------------

    def _desenhar_cenario(self, tela):
        c = _camadas
        tela.blit(c["ceu"], (0, 0))
        off = -(self.rolagem * 0.1) % LARG_NUVENS
        tela.blit(c["nuvens"], (off - LARG_NUVENS, 0))
        tela.blit(c["nuvens"], (off, 0))
        off = -(self.rolagem * 0.35) % LARG_CASAS
        y = CALCADA_Y - 340
        tela.blit(c["casas"], (off - LARG_CASAS, y))
        tela.blit(c["casas"], (off, y))
        tela.blit(c["chao"], (0, CALCADA_Y))
        self._desenhar_rua(tela, self.rolagem)

    def _desenhar_buraco(self, tela, o):
        r = pygame.Rect(int(o.x), CHAO - 19, int(o.w), 40)
        pygame.draw.ellipse(tela, (90, 90, 95), r.inflate(10, 8))
        pygame.draw.ellipse(tela, (25, 18, 14), r)
        pygame.draw.ellipse(tela, (8, 6, 5), r.inflate(-24, -14).move(0, 4))
        # Plaquinha de aviso
        px = int(o.x) - 18
        pygame.draw.line(tela, (80, 80, 90), (px, CHAO + 4), (px, CHAO - 34), 3)
        pygame.draw.polygon(tela, (255, 210, 40), [(px, CHAO - 56), (px - 14, CHAO - 32), (px + 14, CHAO - 32)])
        pygame.draw.polygon(tela, (40, 30, 20), [(px, CHAO - 56), (px - 14, CHAO - 32), (px + 14, CHAO - 32)], 2)
        pygame.draw.line(tela, (40, 30, 20), (px, CHAO - 49), (px, CHAO - 40), 2)
        pygame.draw.circle(tela, (40, 30, 20), (px, CHAO - 36), 1)

    def _desenhar_obstaculo(self, tela, o):
        if o.tipo == "passaro":
            _desenhar_passaro(tela, o.x + o.w / 2, Y_PASSARO + o.bob, self.tempo + o.fase)
            return
        if o.voando:
            dy = o.voando[4]
            ang = o.voando[2]
        else:
            dy, ang = 0.0, 0.0
        if o.tipo == "bicicleta":
            if o.voando:
                sup = pygame.Surface((o.w + 20, 110), pygame.SRCALPHA)
                self._bicicleta_em(sup, 10)
                sup = pygame.transform.rotate(sup, ang)
                tela.blit(sup, sup.get_rect(center=(int(o.x + o.w / 2), int(CHAO - 45 + dy))))
            else:
                _desenhar_bicicleta(tela, self.jogador, int(o.x), self.tempo)
            return
        sup = _sprite(o.tipo)
        if ang:
            sup = pygame.transform.rotate(sup, ang)
        tela.blit(sup, sup.get_rect(midbottom=(int(o.x + o.w / 2), int(CHAO + dy + 1))))

    def _bicicleta_em(self, sup, x):
        # Desenha a bicicleta numa superfície pequena (para girar ao ser derrubada)
        _desenhar_bicicleta(sup, self.jogador, x, self.tempo, sup.get_height() - 4)

    def _desenhar_ovo(self, tela):
        if self.pisca > 0 and not self.morto and int(self.pisca * 12) % 2 == 0:
            return
        cx, cy, a, b = self._hitbox()

        img = self.jogador.avatar(OVO_ALT)
        ang = self.angulo if not self.morto else self.angulo + math.sin(self.tempo_morto * 12) * 8
        if ang:
            img = pygame.transform.rotate(img, ang)
        sx = sy = 1.0
        if self.abaixado:
            sx, sy = 1.25, OVO_ALT_BAIXO / OVO_ALT
        if self.squash > 0:
            p = math.sin(math.pi * (1 - self.squash / 0.12))
            sx *= 1 + 0.2 * p
            sy *= 1 - 0.25 * p
        if abs(sx - 1) > 0.01 or abs(sy - 1) > 0.01:
            w, h = img.get_size()
            img = pygame.transform.smoothscale(img, (max(1, round(w * sx)), max(1, round(h * sy))))

        centro_y = self.y_pe - OVO_ALT * sy / 2
        rect = img.get_rect(center=(OVO_X, round(centro_y)))

        if self.no_buraco is not None:
            tela.set_clip(pygame.Rect(0, 0, LARGURA, CHAO + 6))
        tela.blit(img, rect)
        tela.set_clip(None)

        # Casca extra: bolha azulada em volta
        if self.escudo:
            raio = int(max(a, b) / 0.4 * 0.62)
            pulso = int(math.sin(self.tempo * 6) * 2)
            pygame.draw.circle(tela, (150, 230, 255), (OVO_X, int(centro_y)), raio + pulso, 3)
            pygame.draw.arc(tela, BRANCO, (OVO_X - raio + 8, int(centro_y) - raio + 8, raio, raio),
                            1.6, 2.8, 3)

        # Ímã: aura vermelha piscando
        if self.ima > 0:
            r = 46 + int(math.sin(self.tempo * 10) * 4)
            pygame.draw.circle(tela, (255, 120, 120), (OVO_X, int(centro_y)), r, 2)

        # Estrelinhas girando (tonto) ao perder
        if self.morto and self.no_buraco is None:
            for i in range(3):
                ang = self.tempo * 5 + i * math.tau / 3
                pos = (OVO_X + math.cos(ang) * 40, centro_y - OVO_ALT / 2 - 12 + math.sin(ang) * 10)
                ui.estrela(tela, pos, 11, (160, 110, 10), self.tempo * 4)
                ui.estrela(tela, pos, 8, AMARELO, self.tempo * 4)

    def desenhar_jogo(self, tela):
        self._desenhar_cenario(tela)

        for o in self.obstaculos:
            if o.tipo == "buraco" and o.x < LARGURA and o.direita > -30:
                self._desenhar_buraco(tela, o)

        # Sombra do ovo (fica menor quando ele sobe)
        altura = max(0.0, CHAO - self.y_pe)
        if self.no_buraco is None and self._sobre_buraco() is None:
            larg = max(20, int(66 - altura * 0.2))
            pygame.draw.ellipse(tela, (120, 120, 125), (OVO_X - larg // 2, CHAO - 5, larg, 10))

        # Limões e power-ups
        for x, y in self.limoes_mundo:
            if -20 < x < LARGURA + 20:
                ui.limao(tela, (x, y + math.sin(self.tempo * 5 + x * 0.02) * 3), 11)
        for tipo, x, y in self.capsulas:
            if -30 < x < LARGURA + 30:
                _desenhar_capsula(tela, tipo, x, y, self.tempo)

        for o in self.obstaculos:
            if o.tipo != "buraco" and o.x < LARGURA + 20:
                self._desenhar_obstaculo(tela, o)

        # Linhas de velocidade e rastro do turbo
        for x, y, comp in self.linhas:
            pygame.draw.line(tela, (235, 248, 255), (int(x), int(y)), (int(x + comp), int(y)), 2)
        for x, y, vida, cor in self.rastro:
            pygame.draw.circle(tela, cor, (int(x), int(y)), max(2, int(vida * 40)))

        self._desenhar_ovo(tela)

        # Totó correndo atrás (ou lambendo o ovo no fim)
        lambendo = self.morto and self.lambida != 0.0
        _desenhar_toto(tela, self.toto_x + (0 if self.morto else math.sin(self.tempo * 1.3) * 10),
                       CHAO + 6, self.tempo, correndo=not lambendo, lingua=lambendo)

        self.particulas.desenhar(tela)
        self.textos.desenhar(tela)

    def desenhar_hud(self, tela):
        caixa = pygame.Rect(12, 12, 420, 48)
        ui.painel(tela, caixa, (20, 24, 40), BRANCO, 12, 3, sombra=False)
        ui.desenhar_texto(tela, f"PONTOS: {self.pontos}", (caixa.x + 16, caixa.centery), 14,
                          AMARELO, "midleft")
        rec = self.recorde()
        if rec is not None:
            ui.desenhar_texto(tela, f"RECORDE: {rec}", (caixa.x + 236, caixa.centery), 12,
                              (180, 200, 255), "midleft")

        # Metros, limões e power-ups ativos
        caixa = pygame.Rect(12, 68, 250, 36)
        ui.painel(tela, caixa, (20, 24, 40), BRANCO, 10, 2, sombra=False)
        ui.desenhar_texto(tela, f"{int(self.dist / PX_METRO)} m", (caixa.x + 12, caixa.centery), 12,
                          (180, 220, 255), "midleft")
        ui.limao(tela, (caixa.x + 150, caixa.centery), 9)
        ui.desenhar_texto(tela, f"×{self.limoes}", (caixa.x + 166, caixa.centery), 12,
                          AMARELO, "midleft")

        x = caixa.right + 12
        ativos = []
        if self.escudo:
            ativos.append(("casca", None))
        if self.ima > 0:
            ativos.append(("ima", self.ima / TEMPO_IMA))
        if self.turbo > 0:
            ativos.append(("turbo", self.turbo / TEMPO_TURBO))
        for tipo, frac in ativos:
            _desenhar_capsula(tela, tipo, x + 20, caixa.centery - 2, 0)
            if frac is not None:
                pygame.draw.rect(tela, (20, 24, 40), (x, caixa.bottom + 2, 40, 6))
                pygame.draw.rect(tela, AMARELO, (x, caixa.bottom + 2, int(40 * frac), 6))
            x += 50
