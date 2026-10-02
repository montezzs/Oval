import math
import random

import pygame

from settings import *
from core import ui
from jogos.base import MiniJogo

# ============================================================
# PESCARIA DO OVO
# ============================================================
# O seu ovo está pescando num barquinho feito de meia casca de
# ovo gigante! Desça o anzol, fisgue os peixes e puxe para cima.
# Pescar a mesma espécie seguida vale x1.5. Fuja das águas-vivas
# (elas dão choque na linha!) e procure o BAÚ no fundo do mar.
# São 90 segundos; cada DOURADO dá +5 s no relógio.

# ------------------------------------------------------------
# REGRAS
# ------------------------------------------------------------
SUPERFICIE = 170
AREIA_Y = 690
PROF_MAX = 680
ANZOL_TOPO = SUPERFICIE + 12        # anzol "guardado" logo abaixo da água

VEL_BARCO = 280
BARCO_MIN, BARCO_MAX = 80, 944
VEL_DESCE = 260
VEL_SOBE = 340
VEL_SOBE_SOZINHO = 120

TEMPO_TOTAL = 90.0
BONUS_DOURADO = 5.0
COMBO_MULT = 1.5
TEMPO_CHOQUE = 1.0
TEMPO_POLVO = 1.0
DIST_BAIACU = 60
VEL_ESPANTA = 180                   # anzol mais rápido que isso perto do baiacu: ele incha

POPULACAO = 7                       # sempre pelo menos 6 peixes na tela

# Espécies: pontos, velocidade, faixa de profundidade, tamanho, peso (subida), sorteio
ESPECIES = {
    "sardinha": dict(pts=10, vel=180, faixa=(230, 400), tam=(46, 18), peso=1.0, sorteio=32,
                     nome="SARDINHA"),
    "palhaco": dict(pts=20, vel=120, faixa=(300, 480), tam=(50, 26), peso=0.95, sorteio=24,
                    nome="PALHAÇO"),
    "baiacu": dict(pts=30, vel=70, faixa=(340, 560), tam=(44, 36), peso=0.9, sorteio=16,
                   nome="BAIACU"),
    "polvo": dict(pts=50, vel=55, faixa=(450, 640), tam=(46, 50), peso=0.8, sorteio=12,
                  nome="POLVO"),
    "dourado": dict(pts=100, vel=260, faixa=(550, 650), tam=(74, 30), peso=0.85, sorteio=5,
                    nome="DOURADO"),
    "bota": dict(pts=0, vel=35, faixa=(260, 620), tam=(38, 40), peso=0.9, sorteio=6,
                 nome="BOTA"),
    "bau": dict(pts=200, vel=0, faixa=(668, 668), tam=(70, 50), peso=0.5, sorteio=0,
                nome="BAÚ"),
}

TECLAS_ESQ = (pygame.K_LEFT, pygame.K_a)
TECLAS_DIR = (pygame.K_RIGHT, pygame.K_d)
TECLAS_DESCE = (pygame.K_DOWN, pygame.K_s)
TECLAS_SOBE = (pygame.K_UP, pygame.K_w, pygame.K_SPACE)


def _dist_segmento(p, a, b):
    """Distância do ponto p ao segmento a-b."""
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    comp = dx * dx + dy * dy
    if comp == 0:
        return math.hypot(p[0] - ax, p[1] - ay)
    t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / comp))
    return math.hypot(p[0] - ax - dx * t, p[1] - ay - dy * t)


# ============================================================
# DESENHO DOS BICHOS (feito uma vez só, com cache)
# ============================================================

_sprites = {}
Z = 3                               # desenha 3x maior e diminui (fica suave)


def _olho(s, x, y, r):
    pygame.draw.circle(s, BRANCO, (int(x), int(y)), r)
    pygame.draw.circle(s, (20, 20, 30), (int(x + r * 0.25), int(y)), max(2, int(r * 0.55)))
    pygame.draw.circle(s, BRANCO, (int(x + r * 0.05), int(y - r * 0.3)), max(1, int(r * 0.2)))


def _peixe(s, w, h, cor, costas, rabo_cor=None):
    """Corpo básico de peixe virado para a direita."""
    W, H = s.get_size()
    cx, cy = W // 2 + w * 0.08, H // 2
    rabo_cor = rabo_cor or costas
    rabo = [(cx - w * 0.38, cy), (cx - w * 0.62, cy - h * 0.5), (cx - w * 0.56, cy),
            (cx - w * 0.62, cy + h * 0.5)]
    pygame.draw.polygon(s, ui.escurecer(rabo_cor, 60), [(x, y) for x, y in rabo], 0)
    pygame.draw.polygon(s, rabo_cor, [(x + Z, y) for x, y in rabo])
    corpo = pygame.Rect(0, 0, w * 0.86, h)
    corpo.center = (cx, cy)
    pygame.draw.ellipse(s, ui.escurecer(cor, 90), corpo.inflate(2 * Z, 2 * Z))
    pygame.draw.ellipse(s, cor, corpo)
    return cx, cy, corpo


def _criar(tipo):
    info = ESPECIES.get(tipo)
    w, h = info["tam"] if info else (40, 40)
    W, H = (w + 16) * Z, (h + 16) * Z
    s = pygame.Surface((W, H), pygame.SRCALPHA)
    w, h = w * Z, h * Z

    if tipo == "sardinha":
        cx, cy, corpo = _peixe(s, w, h, (180, 200, 220), (120, 140, 180))
        pygame.draw.ellipse(s, (120, 140, 180), (corpo.x + w * 0.1, corpo.y + 2, corpo.w * 0.8, h * 0.4))
        pygame.draw.line(s, (230, 240, 250), (corpo.x + w * 0.1, cy + h * 0.1), (corpo.right - w * 0.1, cy + h * 0.1), Z)
        _olho(s, corpo.right - w * 0.16, cy - h * 0.08, int(h * 0.2))
    elif tipo == "palhaco":
        cx, cy, corpo = _peixe(s, w, h, (255, 140, 40), (230, 110, 30))
        for fx in (0.3, 0.62):
            x = corpo.x + corpo.w * fx
            faixa = pygame.Rect(0, 0, w * 0.1, h * 0.9)
            faixa.center = (x, cy)
            pygame.draw.ellipse(s, (30, 30, 30), faixa.inflate(Z * 2, 0))
            pygame.draw.ellipse(s, BRANCO, faixa)
        pygame.draw.polygon(s, (230, 110, 30), [(cx - w * 0.1, corpo.y + Z), (cx + w * 0.1, corpo.y - h * 0.25),
                                                (cx + w * 0.2, corpo.y + Z * 2)])
        _olho(s, corpo.right - w * 0.14, cy - h * 0.1, int(h * 0.17))
    elif tipo in ("baiacu", "baiacu_inflado"):
        inflado = tipo == "baiacu_inflado"
        cor = (230, 210, 120)
        W2, H2 = s.get_size()
        cx, cy = W2 // 2, H2 // 2
        r = int(min(w, h) * (0.62 if inflado else 0.46))
        if inflado:
            for i in range(14):
                a = i * math.tau / 14
                pygame.draw.polygon(s, (200, 170, 80), [
                    (cx + math.cos(a - 0.14) * r * 0.9, cy + math.sin(a - 0.14) * r * 0.9),
                    (cx + math.cos(a) * r * 1.32, cy + math.sin(a) * r * 1.32),
                    (cx + math.cos(a + 0.14) * r * 0.9, cy + math.sin(a + 0.14) * r * 0.9)])
        else:
            pygame.draw.polygon(s, (200, 170, 80), [(cx - r * 0.9, cy), (cx - r * 1.4, cy - r * 0.5),
                                                    (cx - r * 1.3, cy), (cx - r * 1.4, cy + r * 0.5)])
        pygame.draw.circle(s, (150, 120, 50), (cx, cy), r + Z)
        pygame.draw.circle(s, cor, (cx, cy), r)
        pygame.draw.circle(s, (250, 240, 200), (cx, int(cy + r * 0.35)), int(r * 0.55))
        for dx, dy in ((-0.4, -0.4), (0.0, -0.55), (-0.1, -0.2), (-0.55, 0.0)):
            pygame.draw.circle(s, (170, 140, 60), (int(cx + dx * r), int(cy + dy * r)), max(2, r // 9))
        _olho(s, cx + r * 0.45, cy - r * 0.2, int(r * 0.26))
        pygame.draw.circle(s, (200, 100, 80), (int(cx + r * 0.85), int(cy + r * 0.15)), max(2, r // 8))
    elif tipo == "polvo":
        cor = (230, 100, 160)
        W2, H2 = s.get_size()
        cx, cy = W2 // 2, int(H2 * 0.4)
        for i in range(6):
            x0 = cx - w * 0.3 + i * w * 0.12
            pts = [(x0 + math.sin(k * 0.9 + i) * Z * 3, cy + k * h * 0.09) for k in range(8)]
            pygame.draw.lines(s, ui.escurecer(cor, 60), False, pts, Z * 4)
            pygame.draw.lines(s, cor, False, pts, Z * 3)
        cabeca = pygame.Rect(0, 0, w * 0.8, h * 0.6)
        cabeca.midbottom = (cx, cy + h * 0.12)
        pygame.draw.ellipse(s, ui.escurecer(cor, 80), cabeca.inflate(2 * Z, 2 * Z))
        pygame.draw.ellipse(s, cor, cabeca)
        pygame.draw.ellipse(s, (255, 170, 210), (cabeca.x + w * 0.12, cabeca.y + h * 0.08, w * 0.2, h * 0.12))
        _olho(s, cx - w * 0.14, cabeca.centery + h * 0.06, int(w * 0.1))
        _olho(s, cx + w * 0.14, cabeca.centery + h * 0.06, int(w * 0.1))
    elif tipo == "dourado":
        cx, cy, corpo = _peixe(s, w, h, (255, 210, 40), (240, 150, 30), (255, 150, 40))
        pygame.draw.polygon(s, (255, 150, 40), [(corpo.x + w * 0.2, corpo.y + Z), (corpo.x + w * 0.5, corpo.y - h * 0.3),
                                                (corpo.x + w * 0.6, corpo.y + Z * 2)])
        pygame.draw.ellipse(s, (255, 245, 170), (corpo.x + w * 0.2, corpo.y + h * 0.16, w * 0.4, h * 0.2))
        for k in range(3):
            x = corpo.x + w * (0.25 + k * 0.14)
            pygame.draw.arc(s, (230, 170, 30), (x, cy - h * 0.1, w * 0.12, h * 0.4), -1.2, 1.2, Z)
        _olho(s, corpo.right - w * 0.12, cy - h * 0.1, int(h * 0.17))
    elif tipo == "bota":
        W2, H2 = s.get_size()
        cx, cy = W2 // 2, H2 // 2
        cano = pygame.Rect(cx - w * 0.4, cy - h * 0.5, w * 0.45, h * 0.7)
        pe = pygame.Rect(cx - w * 0.4, cy + h * 0.05, w * 0.9, h * 0.38)
        cor = (120, 80, 50)
        for r in (cano, pe):
            pygame.draw.rect(s, (60, 40, 25), r.inflate(2 * Z, 2 * Z), border_radius=4 * Z)
        pygame.draw.rect(s, cor, cano, border_radius=3 * Z)
        pygame.draw.rect(s, cor, pe, border_radius=4 * Z)
        pygame.draw.rect(s, (60, 40, 25), (pe.x, pe.bottom - h * 0.1, pe.w, h * 0.1), border_radius=2 * Z)
        for k in range(3):
            y = cano.y + h * 0.15 + k * h * 0.15
            pygame.draw.line(s, (230, 220, 200), (cano.x + w * 0.1, y), (cano.right - w * 0.1, y + h * 0.05), Z)
        # Alga presa
        pygame.draw.lines(s, (70, 160, 90), False, [(cano.right, cano.y + h * 0.1), (cano.right + w * 0.1, cano.y),
                                                    (cano.right + w * 0.05, cano.y - h * 0.15)], Z * 2)
    elif tipo in ("bau", "bau_aberto"):
        W2, H2 = s.get_size()
        cx, cy = W2 // 2, H2 // 2
        caixa = pygame.Rect(0, 0, w * 0.9, h * 0.55)
        caixa.midbottom = (cx, cy + h * 0.4)
        tampa = pygame.Rect(0, 0, w * 0.9, h * 0.5)
        tampa.midbottom = (cx, caixa.y + Z * 2)
        if tipo == "bau_aberto":
            pygame.draw.ellipse(s, (255, 230, 90), tampa.inflate(-w * 0.1, 0))
            for k in range(5):
                pygame.draw.circle(s, (255, 200, 40), (int(tampa.x + w * 0.15 + k * w * 0.15), int(tampa.bottom - Z * 3)),
                                   int(w * 0.07))
        else:
            pygame.draw.rect(s, (70, 40, 20), tampa.inflate(2 * Z, 2 * Z), border_top_left_radius=int(h * 0.3),
                             border_top_right_radius=int(h * 0.3))
            pygame.draw.rect(s, (150, 90, 40), tampa, border_top_left_radius=int(h * 0.3),
                             border_top_right_radius=int(h * 0.3))
        pygame.draw.rect(s, (70, 40, 20), caixa.inflate(2 * Z, 2 * Z), border_radius=Z * 2)
        pygame.draw.rect(s, (150, 90, 40), caixa, border_radius=Z * 2)
        for fx in (0.15, 0.85):
            x = caixa.x + caixa.w * fx
            pygame.draw.rect(s, (230, 190, 60), (x - Z * 3, tampa.y + Z * 3, Z * 6, caixa.bottom - tampa.y - Z * 3))
        pygame.draw.rect(s, (230, 190, 60), (cx - w * 0.07, caixa.y - Z * 3, w * 0.14, h * 0.2), border_radius=Z * 2)
        pygame.draw.circle(s, (60, 40, 20), (cx, int(caixa.y + h * 0.05)), Z * 2)

    return pygame.transform.smoothscale(s, (W // Z, H // Z))


def _sprite(tipo, esquerda=False):
    chave = (tipo, esquerda)
    s = _sprites.get(chave)
    if s is None:
        if esquerda:
            s = pygame.transform.flip(_sprite(tipo), True, False)
        else:
            s = _criar(tipo)
        _sprites[chave] = s
    return s


_agua_viva = {}


def _cupula(r):
    s = _agua_viva.get(r)
    if s is None:
        s = pygame.Surface((r * 2 + 4, r + 6), pygame.SRCALPHA)
        pygame.draw.circle(s, (230, 150, 255, 150), (r + 2, r + 4), r, draw_top_left=True, draw_top_right=True)
        pygame.draw.rect(s, (230, 150, 255, 150), (2, r + 2, r * 2, 4), border_radius=2)
        pygame.draw.circle(s, (250, 200, 255, 200), (r + 2, r + 4), r, 2, draw_top_left=True, draw_top_right=True)
        pygame.draw.ellipse(s, (255, 240, 255, 180), (r - r // 2, r // 3, r // 2, r // 3))
        _agua_viva[r] = s
    return s


# ============================================================
# BICHOS DO MAR
# ============================================================

class Peixe:

    def __init__(self, tipo, x, y, direcao):
        info = ESPECIES[tipo]
        self.tipo = tipo
        self.x = float(x)
        self.y0 = float(y)
        self.y = float(y)
        self.dir = direcao
        self.vel = info["vel"] * random.uniform(0.85, 1.15)
        self.fase = random.uniform(0, math.tau)
        self.estado = "nadando"        # nadando, inflado, fugindo
        self.tempo = 0.0
        self.w, self.h = info["tam"]

    @property
    def pontos(self):
        return ESPECIES[self.tipo]["pts"]

    def pode_fisgar(self):
        return self.estado == "nadando"


class AguaViva:

    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.vx = random.choice((-1, 1)) * random.uniform(25, 45)
        self.vy = random.uniform(-20, 20)
        self.fase = random.uniform(0, math.tau)
        self.r = random.randint(17, 21)


class Pescaria(MiniJogo):

    ID = "pescaria"
    TITULO = "PESCARIA DO OVO"
    TITULO_CURTO = "PESCARIA"
    DESCRICAO = "No barquinho-casca, fisgue peixes, fuja das águas-vivas e ache o baú do tesouro em 90 s!"
    COR = (40, 140, 210)
    INSTRUCOES = [
        "Desça o anzol e fisgue peixes! Repetir: x1.5",
        "Água-viva dá choque na linha: o peixe foge!",
        "Baiacu incha com anzol rápido. DOURADO: +5 s",
        "Tem um BAÚ no fundo... mas ele é pesado!",
        "←→ barco • ↓ desce • ↑ sobe • mouse",
    ]
    MOEDAS_POR = 25
    MOEDAS_MAX = 45

    # --------------------------------------------------------
    # CENÁRIO: mar de manhã
    # --------------------------------------------------------

    @classmethod
    def criar_fundo(cls, jogador):
        sup = pygame.Surface((LARGURA, ALTURA))
        rnd = random.Random(15)

        # Céu matinal com sol
        ceu = ui.gradiente(LARGURA, SUPERFICIE, (255, 190, 140), (255, 225, 170))
        sup.blit(ceu, (0, 0))
        halo = pygame.Surface((220, 220), pygame.SRCALPHA)
        for r, a in ((110, 40), (80, 60)):
            pygame.draw.circle(halo, (255, 250, 200, a), (110, 110), r)
        sup.blit(halo, (600 - 110, 110 - 110))
        pygame.draw.circle(sup, (255, 240, 150), (600, 110), 44)
        pygame.draw.circle(sup, (255, 250, 200), (600, 110), 34)
        for cx, cy in ((200, 70), (860, 90)):
            for dx, r in ((-30, 16), (-6, 24), (22, 18), (44, 12)):
                pygame.draw.circle(sup, (255, 245, 235), (cx + dx, cy), r)
        # Ilhazinha no horizonte
        pygame.draw.ellipse(sup, (120, 170, 110), (40, SUPERFICIE - 26, 180, 60))
        pygame.draw.line(sup, (120, 80, 50), (120, SUPERFICIE - 20), (132, SUPERFICIE - 70), 5)
        for a in (-2.5, -1.9, -1.2, -0.6):
            pygame.draw.line(sup, (60, 150, 70), (132, SUPERFICIE - 70),
                             (132 + math.cos(a) * 34, SUPERFICIE - 70 - math.sin(a) * -14 - 8), 5)

        # Mar em gradiente
        mar = ui.gradiente(LARGURA, AREIA_Y - SUPERFICIE, (30, 120, 200), (10, 40, 90))
        sup.blit(mar, (0, SUPERFICIE))

        # Raios de luz
        for comp in (120, 200, 280, 360, 440, 520):
            luz = pygame.Surface((LARGURA, AREIA_Y - SUPERFICIE), pygame.SRCALPHA)
            for x in (120, 330, 520, 760, 930):
                k = comp / 500
                pygame.draw.polygon(luz, (255, 255, 255, 5), [(x - 30, 0), (x + 30, 0), (x + 30 + 120 * k, comp),
                                                               (x - 30 + 70 * k, comp)])
            sup.blit(luz, (0, SUPERFICIE))

        # Rochas no fundo
        for x, w, h in ((60, 160, 70), (330, 110, 50), (760, 200, 80), (960, 120, 60)):
            r = pygame.Rect(0, 0, w, h)
            r.midbottom = (x, AREIA_Y + 20)
            pygame.draw.ellipse(sup, (40, 60, 90), r)
            pygame.draw.ellipse(sup, (55, 80, 110), r.inflate(-20, -20).move(-6, -6))

        # Areia com conchinhas e estrela-do-mar
        pygame.draw.rect(sup, (220, 200, 140), (0, AREIA_Y, LARGURA, ALTURA - AREIA_Y))
        pontos = [(0, AREIA_Y + 4)]
        for x in range(0, LARGURA + 20, 20):
            pontos.append((x, AREIA_Y + 2 + math.sin(x * 0.05) * 3))
        pontos += [(LARGURA, ALTURA), (0, ALTURA)]
        pygame.draw.polygon(sup, (220, 200, 140), pontos)
        pygame.draw.lines(sup, (240, 225, 170), False, pontos[1:-2], 2)
        for _ in range(60):
            x, y = rnd.randrange(LARGURA), rnd.randrange(AREIA_Y + 8, ALTURA)
            pygame.draw.circle(sup, (200, 180, 120), (x, y), 1)
        for _ in range(9):
            x, y = rnd.randrange(20, LARGURA - 20), rnd.randrange(AREIA_Y + 10, ALTURA - 6)
            cor = rnd.choice([(255, 200, 210), (255, 240, 220), (250, 180, 140)])
            pygame.draw.circle(sup, ui.escurecer(cor, 60), (x, y), 7, draw_top_left=True, draw_top_right=True)
            pygame.draw.circle(sup, cor, (x, y), 6, draw_top_left=True, draw_top_right=True)
            for k in range(3):
                pygame.draw.line(sup, ui.escurecer(cor, 50), (x, y), (x - 4 + k * 4, y - 5), 1)
        ex, ey = 880, AREIA_Y + 16
        estrela = [(ex + math.cos(i * math.pi / 5 - math.pi / 2) * (11 if i % 2 == 0 else 5),
                    ey + math.sin(i * math.pi / 5 - math.pi / 2) * (11 if i % 2 == 0 else 5)) for i in range(10)]
        pygame.draw.polygon(sup, (240, 120, 80), estrela)
        pygame.draw.polygon(sup, (190, 80, 50), estrela, 2)
        return sup

    @classmethod
    def desenhar_icone(cls, sup, jogador):
        w, h = sup.get_size()
        esc = h / ALTURA
        sup_y = int(SUPERFICIE * esc) + 4
        bx = int(w * 0.34)
        # Barco-casca
        jogador.desenhar(sup, (bx - 4, sup_y - 8), h * 0.2)
        pontos = [(bx + math.cos(a) * 36, sup_y + math.sin(a) * 20) for a in [i * math.pi / 12 for i in range(13)]]
        pygame.draw.polygon(sup, jogador.cor, pontos)
        pygame.draw.lines(sup, jogador.cor_contorno, False, pontos, 2)
        pygame.draw.line(sup, jogador.cor_contorno, pontos[0], pontos[-1], 2)
        # Vara e linha
        ponta = (bx + 40, sup_y - 24)
        pygame.draw.line(sup, (110, 70, 40), (bx + 12, sup_y - 6), ponta, 3)
        anzol = (bx + 60, int(h * 0.78))
        pygame.draw.line(sup, (240, 240, 240), ponta, anzol, 1)
        pygame.draw.arc(sup, (220, 220, 230), (anzol[0] - 5, anzol[1] - 2, 10, 10), math.pi, math.tau, 2)
        # Peixes
        for tipo, fx, fy, esq in (("palhaco", 0.78, 0.55, True), ("dourado", 0.62, 0.86, False),
                                  ("sardinha", 0.18, 0.66, False)):
            s = _sprite(tipo, esq)
            s = pygame.transform.smoothscale(s, (int(s.get_width() * 0.62), int(s.get_height() * 0.62)))
            sup.blit(s, s.get_rect(center=(int(w * fx), int(h * fy))))

    # --------------------------------------------------------
    # PARTIDA
    # --------------------------------------------------------

    def reiniciar(self):
        self.teclas = set()
        self.mouse = None               # posição segurando o botão do mouse

        self.bx = LARGURA / 2 - 120
        self.lado = 1                   # para onde o barco olha
        self.vel_barco = 0.0
        self.ax = self.bx + 70
        self.ay = float(ANZOL_TOPO)
        self.vel_anzol = 0.0            # velocidade medida (para o baiacu)
        self.fisgado = None             # Peixe no anzol
        self.segura = 0.0               # polvo segurando
        self.choque = 0.0               # anzol paralisado
        self.imune = 0.0
        self.flash = 0.0
        self.puxando = 0.0              # animação de esforço

        self.relogio = TEMPO_TOTAL
        self.decorrido = 0.0
        self.peixes = []
        self.aguas = []
        self.bolhas = []
        self.voando = []                # peixes voando para o barco
        self.pontos_voando = []         # "+20" indo para o HUD
        self.pulso_hud = 0.0
        self.proximo_peixe = 0.0
        self.pescados = 0
        self.ultimo_tipo = None
        self.sequencia = 0
        self.maior_sequencia = 0
        self.bau_pescado = False
        self.aviso_combo = 0.0

        # Baú no fundo
        bau = Peixe("bau", random.choice([random.uniform(140, 380), random.uniform(640, 900)]), 668, 1)
        self.peixes.append(bau)

        # Peixes já nadando (aparecem na prévia)
        for _ in range(POPULACAO):
            self._novo_peixe(na_tela=True)
        for _ in range(2):
            self._nova_agua_viva()

        # Algas e gaivotas
        rnd = random.Random(3)
        self.algas = [(rnd.randrange(20, LARGURA - 20), rnd.randint(60, 150), rnd.uniform(0, math.tau))
                      for _ in range(14)]
        self.gaivotas = [[rnd.uniform(0, LARGURA), rnd.uniform(30, 120), rnd.uniform(20, 40)] for _ in range(3)]

    def _contagem_peixes(self):
        return sum(1 for p in self.peixes if p.tipo not in ("bota", "bau") and p.estado == "nadando")

    def _novo_peixe(self, na_tela=False):
        nomes = [n for n in ESPECIES if ESPECIES[n]["sorteio"] > 0]
        pesos = [ESPECIES[n]["sorteio"] for n in nomes]
        tipo = random.choices(nomes, pesos)[0]
        # No máximo um dourado e uma bota ao mesmo tempo
        if tipo in ("dourado", "bota") and any(p.tipo == tipo for p in self.peixes):
            tipo = "sardinha"
        info = ESPECIES[tipo]
        y = random.uniform(*info["faixa"])
        direcao = random.choice((-1, 1))
        if na_tela:
            x = random.uniform(80, LARGURA - 80)
        else:
            x = -60 if direcao > 0 else LARGURA + 60
        self.peixes.append(Peixe(tipo, x, y, direcao))

    def _nova_agua_viva(self):
        for _ in range(10):
            x, y = random.uniform(100, LARGURA - 100), random.uniform(290, 600)
            if all(math.hypot(a.x - x, a.y - y) > 180 for a in self.aguas):
                break
        self.aguas.append(AguaViva(x, y))

    # --------------------------------------------------------
    # CONTROLES
    # --------------------------------------------------------

    def evento(self, e):
        # Acompanha as teclas em qualquer estado (para não "grudar" na pausa)
        if e.type == pygame.KEYDOWN:
            self.teclas.add(e.key)
        elif e.type == pygame.KEYUP:
            self.teclas.discard(e.key)
        elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
            self.mouse = None
        elif e.type == pygame.WINDOWFOCUSLOST:
            self.teclas.clear()
            self.mouse = None
        super().evento(e)

    def evento_jogo(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if not self.botao_pausa.collidepoint(e.pos):
                self.mouse = e.pos
        elif e.type == pygame.MOUSEMOTION and self.mouse is not None:
            self.mouse = e.pos

    def _apertando(self, teclas):
        return any(t in self.teclas for t in teclas)

    # --------------------------------------------------------
    # LÓGICA
    # --------------------------------------------------------

    @property
    def ponta_vara(self):
        bob = math.sin(self.tempo * 2.2) * 3
        return (self.bx + self.lado * 72, SUPERFICIE - 96 + bob)

    def atualizar_jogo(self, dt):
        self.decorrido += dt
        self.relogio -= dt
        if self.relogio <= 0:
            self.relogio = 0
            self._fim()
            return

        self._mover_barco(dt)
        self._mover_anzol(dt)
        self._mover_bichos(dt)
        self._colisoes()
        self._animar(dt)

    def _mover_barco(self, dt):
        direcao = 0
        if self._apertando(TECLAS_ESQ):
            direcao -= 1
        if self._apertando(TECLAS_DIR):
            direcao += 1
        if direcao == 0 and self.mouse is not None:
            dx = self.mouse[0] - (self.bx + self.lado * 72)
            if abs(dx) > 8:
                direcao = 1 if dx > 0 else -1
        alvo = direcao * VEL_BARCO
        self.vel_barco += max(-1400 * dt, min(1400 * dt, alvo - self.vel_barco))
        self.bx = max(BARCO_MIN, min(BARCO_MAX, self.bx + self.vel_barco * dt))
        if self.bx in (BARCO_MIN, BARCO_MAX):
            self.vel_barco = 0.0
        if direcao:
            self.lado = direcao

    def _mover_anzol(self, dt):
        y_antes, x_antes = self.ay, self.ax
        tx, ty = self.ponta_vara

        # O anzol vai atrás da ponta da vara (com um pouco de atraso)
        self.ax += (tx - self.ax) * min(1.0, dt * 5)

        if self.choque > 0:
            self.choque -= dt
        elif self.fisgado:
            peso = ESPECIES[self.fisgado.tipo]["peso"]
            if self.segura > 0:
                self.segura -= dt
            else:
                vel = VEL_SOBE if (self._apertando(TECLAS_SOBE) or self.mouse is not None) else VEL_SOBE_SOZINHO
                self.ay -= vel * peso * dt
                self.puxando += dt
        else:
            desce = self._apertando(TECLAS_DESCE)
            sobe = self._apertando(TECLAS_SOBE)
            if self.mouse is not None and not (desce or sobe):
                alvo = max(ANZOL_TOPO, min(PROF_MAX, self.mouse[1]))
                if self.mouse[1] < SUPERFICIE:
                    alvo = ANZOL_TOPO
                if alvo > self.ay + 4:
                    desce = True
                elif alvo < self.ay - 4:
                    sobe = True
                if desce:
                    self.ay = min(alvo, self.ay + VEL_DESCE * dt)
                    desce = False
                elif sobe:
                    self.ay = max(alvo, self.ay - VEL_SOBE * dt)
                    sobe = False
            if desce and not sobe:
                self.ay += VEL_DESCE * dt
            elif sobe and not desce:
                self.ay -= VEL_SOBE * dt

        self.ay = max(ANZOL_TOPO, min(PROF_MAX, self.ay))
        if dt > 0:
            self.vel_anzol = math.hypot(self.ay - y_antes, self.ax - x_antes) / dt

        # Chegou na superfície com peixe: pescou!
        if self.fisgado and self.ay <= ANZOL_TOPO + 1:
            self._pescar()

    def _fator(self):
        """Os bichos ficam mais rápidos com o tempo."""
        return 1.0 + 0.3 * min(1.0, self.decorrido / TEMPO_TOTAL)

    def _mover_bichos(self, dt):
        fator = self._fator()
        vivos = []
        for p in self.peixes:
            if p is self.fisgado:
                vivos.append(p)
                continue
            p.tempo += dt
            if p.tipo == "bau":
                vivos.append(p)
                continue
            if p.estado == "inflado":
                p.x += p.dir * 20 * dt
                if p.tempo > 2.0:
                    p.estado, p.tempo = "fugindo", 0.0
            elif p.estado == "fugindo":
                p.x += p.dir * p.vel * 2.4 * dt
            else:
                p.x += p.dir * p.vel * fator * dt
            amp = 4 if p.tipo == "bota" else 10
            p.y = p.y0 + math.sin(p.fase + p.tempo * 1.6) * amp
            if -90 < p.x < LARGURA + 90:
                vivos.append(p)
        self.peixes = vivos

        # Repõe os peixes
        self.proximo_peixe -= dt
        while self._contagem_peixes() < POPULACAO - 1:
            self._novo_peixe()
        if self._contagem_peixes() < POPULACAO and self.proximo_peixe <= 0:
            self._novo_peixe()
            self.proximo_peixe = 0.35

        # Mais águas-vivas com o tempo
        alvo = 2 + int(self.decorrido // 30)
        if len(self.aguas) < min(4, alvo):
            self._nova_agua_viva()
        for a in self.aguas:
            a.fase += dt
            a.x += a.vx * dt
            a.y += (a.vy + math.sin(a.fase * 2.5) * 30) * dt
            if a.x < 60 or a.x > LARGURA - 60:
                a.vx = -a.vx
                a.x = max(60, min(LARGURA - 60, a.x))
            if a.y < 280 or a.y > 620:
                a.vy = -a.vy
                a.y = max(280, min(620, a.y))

        # Bolhas
        if random.random() < dt * 5:
            x, _, _ = random.choice(self.algas)
            self.bolhas.append([x + random.uniform(-10, 10), AREIA_Y - 10, random.randint(2, 5)])
        if self.vel_anzol > 100 and self.ay > SUPERFICIE + 20 and random.random() < dt * 12:
            self.bolhas.append([self.ax + random.uniform(-6, 6), self.ay, random.randint(2, 4)])
        for b in self.bolhas:
            b[1] -= (40 + b[2] * 12) * dt
            b[0] += math.sin(b[1] * 0.05) * 0.4
        self.bolhas = [b for b in self.bolhas if b[1] > SUPERFICIE + 4]

    def _colisoes(self):
        linha_a, linha_b = self.ponta_vara, (self.ax, self.ay)

        # Água-viva na linha: choque!
        if self.imune <= 0:
            for a in self.aguas:
                if _dist_segmento((a.x, a.y + 6), (linha_a[0], max(linha_a[1], SUPERFICIE)), linha_b) < a.r + 4:
                    self._levar_choque(a)
                    break

        if self.fisgado or self.choque > 0:
            return

        for p in self.peixes:
            dx, dy = p.x - self.ax, p.y - self.ay
            # Baiacu se assusta com anzol rápido
            if p.tipo == "baiacu" and p.estado == "nadando" and self.vel_anzol > VEL_ESPANTA \
                    and math.hypot(dx, dy) < DIST_BAIACU:
                p.estado, p.tempo = "inflado", 0.0
                p.dir = 1 if dx > 0 else -1
                self.som("boing", 0.6)
                self.textos.adicionar("PUFF!", (p.x, p.y - 36), (255, 230, 140), 14)
                continue
            if not p.pode_fisgar():
                continue
            if abs(dx) < p.w * 0.5 + 6 and abs(dy) < p.h * 0.5 + 6:
                self._fisgar(p)
                break

    def _fisgar(self, p):
        self.fisgado = p
        self.puxando = 0.0
        self.segura = TEMPO_POLVO if p.tipo == "polvo" else 0.0
        self.som("pulo", 0.6)
        if p.tipo == "bota":
            self.textos.adicionar("ECA!", (p.x, p.y - 30), (190, 230, 160), 16)
        elif p.tipo == "bau":
            self.textos.adicionar("O BAÚ!", (p.x, p.y - 40), AMARELO, 20)
            self.tremer(0.2)
        elif p.tipo == "polvo":
            self.textos.adicionar("SEGURA!", (p.x, p.y - 34), (255, 170, 210), 14)
        else:
            self.textos.adicionar("FISGOU!", (p.x, p.y - 30), BRANCO, 14)
        self.particulas.explodir((self.ax, self.ay), [(200, 230, 255), BRANCO], 8, 120, 0.4, (2, 4), gravidade=-100)

    def _levar_choque(self, a):
        self.choque = TEMPO_CHOQUE
        self.imune = TEMPO_CHOQUE + 0.6
        self.flash = 0.25
        self.tremer(0.15)
        self.som("erro", 0.8)
        self.particulas.explodir((a.x, a.y), [(120, 220, 255), (255, 255, 160), BRANCO], 16, 220, 0.5, (2, 5), 0)
        if self.fisgado:
            p = self.fisgado
            self.fisgado = None
            self.segura = 0.0
            if p.tipo == "bau":
                # O baú volta para o fundo
                p.x, p.y = self.ax, 668
                p.y0 = 668
            else:
                p.x, p.y0 = self.ax, self.ay
                p.estado, p.tempo = "fugindo", 0.0
                p.dir = random.choice((-1, 1))
            self.textos.adicionar("CHOQUE! FUGIU!", (self.ax, self.ay - 40), (140, 220, 255), 16)
        else:
            self.textos.adicionar("CHOQUE!", (self.ax, self.ay - 40), (140, 220, 255), 16)

    def _pescar(self):
        p = self.fisgado
        self.fisgado = None
        self.segura = 0.0
        if p in self.peixes:
            self.peixes.remove(p)
        pos = (self.ax, SUPERFICIE)
        self.particulas.explodir(pos, [(200, 230, 255), BRANCO, (120, 190, 240)], 18, 220, 0.6, (3, 6))
        self.som("bater", 0.4)

        info = ESPECIES[p.tipo]
        ganho = info["pts"]
        texto = f"+{ganho}"
        cor = BRANCO
        if p.tipo == "bota":
            self.sequencia = 0
            self.ultimo_tipo = None
            texto, cor = "ECA! +0", (190, 230, 160)
            self.som("erro", 0.5)
        elif p.tipo == "bau":
            self.bau_pescado = True
            texto, cor = f"TESOURO! +{ganho}", AMARELO
            self.som("vencer", 0.7)
            self.tremer(0.2)
            self.particulas.explodir(pos, [AMARELO, (255, 240, 150), BRANCO], 40, 320, 1.0, (3, 7))
        else:
            if p.tipo == self.ultimo_tipo:
                self.sequencia += 1
                ganho = int(ganho * COMBO_MULT)
                texto, cor = f"+{ganho} x1.5!", (255, 170, 60)
                self.aviso_combo = 1.2
            else:
                self.sequencia = 1
            self.ultimo_tipo = p.tipo
            self.maior_sequencia = max(self.maior_sequencia, self.sequencia)
            if p.tipo == "dourado":
                self.relogio += BONUS_DOURADO
                self.textos.adicionar("+5 s!", (LARGURA - 150, 90), (120, 230, 255), 18)
                self.som("moeda")
                self.particulas.explodir(pos, [AMARELO, (255, 240, 150)], 24, 260, 0.8, (3, 6))
            else:
                self.som("acerto" if ganho >= 30 else "ponto", 0.7)

        self.pontos += ganho
        self.pescados += 1 if p.tipo != "bota" else 0
        self.textos.adicionar(texto, (pos[0], pos[1] - 40), cor, 16 if ganho < 100 else 20)
        # Peixe voa para dentro do barco; os pontos voam para o HUD
        self.voando.append([p.tipo, p.dir < 0, pos[0], pos[1], self.bx, SUPERFICIE - 20, 0.0])
        if ganho > 0:
            self.pontos_voando.append([f"+{ganho}", pos[0], pos[1] - 60, 0.0])

    def _animar(self, dt):
        self.imune = max(0.0, self.imune - dt)
        self.flash = max(0.0, self.flash - dt)
        self.aviso_combo = max(0.0, self.aviso_combo - dt)
        self.pulso_hud = max(0.0, self.pulso_hud - dt)
        if not self.fisgado:
            self.puxando = 0.0

        for v in self.voando:
            v[6] += dt * 2
        self.voando = [v for v in self.voando if v[6] < 1]
        for v in self.pontos_voando:
            v[3] += dt * 1.6
            if v[3] >= 1 and len(v) == 4:
                self.pulso_hud = 0.25
                v.append(True)
        self.pontos_voando = [v for v in self.pontos_voando if v[3] < 1]

        for g in self.gaivotas:
            g[0] += g[2] * dt
            if g[0] > LARGURA + 40:
                g[0] = -40
                g[1] = random.uniform(30, 120)

    def _fim(self):
        linhas = [f"PONTOS: {self.pontos}",
                  f"PEIXES: {self.pescados}  •  COMBO: {self.maior_sequencia}"]
        if self.bau_pescado:
            linhas.append("★ ACHOU O BAÚ! ★")
        self.terminar(titulo="FIM DA PESCARIA!", linhas=linhas)

    # --------------------------------------------------------
    # DESENHO
    # --------------------------------------------------------

    def desenhar_jogo(self, tela):
        tela.blit(self.fundo(self.jogador), (0, 0))
        t = self.tempo

        # Gaivotas
        for x, y, _ in self.gaivotas:
            bate = math.sin(t * 6 + x * 0.01) * 4
            pygame.draw.lines(tela, (60, 50, 60), False, [(x - 14, y - 7 + bate), (x - 6, y - 4), (x, y),
                                                          (x + 6, y - 4), (x + 14, y - 7 + bate)], 3)

        # Algas balançando
        for x, h, fase in self.algas:
            pts = []
            for k in range(8):
                f = k / 7
                pts.append((x + math.sin(t * 1.6 + fase + f * 3) * 10 * f, AREIA_Y + 6 - h * f))
            pygame.draw.lines(tela, (30, 120, 70), False, pts, 6)
            pygame.draw.lines(tela, (40, 160, 90), False, pts, 4)

        # Bolhas
        for x, y, r in self.bolhas:
            pygame.draw.circle(tela, (180, 220, 255), (int(x), int(y)), r, 1)

        # Peixes
        for p in self.peixes:
            if p is not self.fisgado:
                self._desenhar_peixe(tela, p)

        # Águas-vivas
        for a in self.aguas:
            self._desenhar_agua_viva(tela, a)

        self._desenhar_linha(tela)
        self._desenhar_barco(tela)

        # Peixes voando para o barco
        for tipo, esq, x0, y0, x1, y1, k in self.voando:
            x = x0 + (x1 - x0) * k
            y = y0 + (y1 - y0) * k - math.sin(k * math.pi) * 90
            s = _sprite(tipo, esq)
            s = pygame.transform.rotozoom(s, k * 360, 1 - 0.5 * k)
            tela.blit(s, s.get_rect(center=(int(x), int(y))))

        # Onda da superfície
        pts = [(x, SUPERFICIE + math.sin(x * 0.03 + t * 2) * 3) for x in range(0, LARGURA + 16, 16)]
        pygame.draw.lines(tela, (170, 220, 255), False, pts, 3)

        self.particulas.desenhar(tela)
        self.textos.desenhar(tela)

        # Pontos voando para o HUD
        for msg, x, y, k in self.pontos_voando:
            px = x + (150 - x) * k * k
            py = y + (36 - y) * k * k
            ui.desenhar_texto(tela, msg, (int(px), int(py)), 14, AMARELO, "center")

        if self.flash > 0:
            ui.veu(tela, int(self.flash / 0.25 * 110), (80, 200, 255))

        if self.estado == "jogando" and self.aviso_combo > 0 and self.ultimo_tipo:
            nome = ESPECIES[self.ultimo_tipo]["nome"]
            ui.desenhar_texto(tela, f"COMBO {nome} x1.5!", (LARGURA // 2, 216), 16, (255, 180, 70), "center")

    def _desenhar_peixe(self, tela, p):
        if p.tipo == "baiacu" and p.estado == "inflado":
            s = _sprite("baiacu_inflado", p.dir < 0)
        else:
            s = _sprite(p.tipo, p.dir < 0)
        if p.tipo == "bota":
            s = pygame.transform.rotate(s, math.sin(p.tempo * 1.3) * 20)
        tela.blit(s, s.get_rect(center=(int(p.x), int(p.y))))
        if p.tipo == "dourado" and int(self.tempo * 6 + p.fase) % 3 == 0:
            ui.estrela(tela, (int(p.x + 20), int(p.y - 16)), 5, BRANCO)
        if p.tipo == "bau":
            brilho = int(abs(math.sin(self.tempo * 3)) * 3)
            ui.estrela(tela, (int(p.x + 26), int(p.y - 22)), 4 + brilho, (255, 240, 150), self.tempo)

    def _desenhar_agua_viva(self, tela, a):
        t = a.fase
        pulso = 1 + 0.08 * math.sin(t * 5)
        r = a.r
        for k in range(5):
            x0 = a.x - r * 0.7 + k * r * 0.35
            pts = [(x0 + math.sin(t * 4 + k + j * 0.8) * 4, a.y + 6 + j * 7) for j in range(5)]
            pygame.draw.lines(tela, (230, 170, 255), False, pts, 2)
        s = _cupula(r)
        if pulso != 1:
            s = pygame.transform.scale(s, (int(s.get_width() * pulso), int(s.get_height() / pulso)))
        tela.blit(s, s.get_rect(midbottom=(int(a.x), int(a.y + 8))))

    def _desenhar_linha(self, tela):
        ponta = self.ponta_vara
        cor = (255, 255, 160) if self.choque > 0 else (245, 245, 245)
        if self.choque > 0 and int(self.tempo * 20) % 2 == 0:
            # Linha "eletrizada"
            n = 10
            pts = []
            for k in range(n + 1):
                f = k / n
                x = ponta[0] + (self.ax - ponta[0]) * f + (random.uniform(-5, 5) if 0 < k < n else 0)
                y = ponta[1] + (self.ay - ponta[1]) * f
                pts.append((x, y))
            pygame.draw.lines(tela, (120, 220, 255), False, pts, 3)
        pygame.draw.line(tela, cor, ponta, (self.ax, self.ay), 1)

        # Peixe fisgado se debatendo
        if self.fisgado:
            p = self.fisgado
            if p.tipo == "bau":
                s = _sprite("bau")
                tela.blit(s, s.get_rect(midtop=(int(self.ax), int(self.ay) + 4)))
            else:
                ang = 90 + math.sin(self.tempo * 22) * 20
                if p.tipo in ("polvo", "bota"):
                    ang = math.sin(self.tempo * 18) * 20
                s = pygame.transform.rotate(_sprite(p.tipo), ang)
                tela.blit(s, s.get_rect(center=(int(self.ax), int(self.ay + p.w * 0.35))))

        # Anzol (gancho) com chumbinho
        x, y = int(self.ax), int(self.ay)
        pygame.draw.circle(tela, (90, 90, 100), (x, y - 10), 4)
        pygame.draw.line(tela, (210, 210, 220), (x, y - 6), (x, y + 6), 2)
        pygame.draw.arc(tela, (210, 210, 220), (x - 7, y, 10, 12), math.pi, math.tau * 0.98, 2)
        pygame.draw.line(tela, (210, 210, 220), (x - 7, y + 6), (x - 7, y + 2), 2)
        # Boia
        by = SUPERFICIE - 2 + math.sin(self.tempo * 3) * 2
        bx = ponta[0] + (self.ax - ponta[0]) * ((by - ponta[1]) / max(1, self.ay - ponta[1]))
        pygame.draw.circle(tela, (230, 50, 50), (int(bx), int(by)), 6)
        pygame.draw.rect(tela, BRANCO, (int(bx) - 6, int(by) - 1, 12, 7), border_bottom_left_radius=6,
                         border_bottom_right_radius=6)

    def _desenhar_barco(self, tela):
        t = self.tempo
        bob = math.sin(t * 2.2) * 3
        bx, by = self.bx, SUPERFICIE + bob
        lado = self.lado

        # Ovo sentado dentro, fazendo força ao puxar
        altura = 62
        esq = 1.0
        if self.fisgado and self.segura <= 0 and self.choque <= 0:
            esq = 1 + 0.08 * math.sin(self.puxando * 18)
        ap = self.jogador.aparencia()
        centro = (bx - lado * 12, by - 30 - altura * (esq - 1) / 2)
        if esq != 1.0:
            sup = self.jogador.avatar(altura, ap)
            if lado < 0:
                sup = pygame.transform.flip(sup, True, False)
            w, h = sup.get_size()
            sup = pygame.transform.smoothscale(sup, (int(w * (2 - esq)), int(h * esq)))
            tela.blit(sup, sup.get_rect(center=(int(centro[0]), int(centro[1] - 2))))
        else:
            self.jogador.desenhar(tela, centro, altura, espelhar=lado < 0)

        # Vara de pescar
        mao = (bx + lado * 16, by - 22)
        ponta = self.ponta_vara
        pygame.draw.line(tela, (80, 50, 30), mao, ponta, 6)
        pygame.draw.line(tela, (150, 100, 60), mao, ponta, 3)
        pygame.draw.circle(tela, (90, 90, 100), (int(mao[0] + lado * 6), int(mao[1] - 8)), 6)
        pygame.draw.circle(tela, (255, 210, 170), (int(mao[0]), int(mao[1])), 7)

        # Meia casca de ovo (com rachadura em zigue-zague)
        w, h = 180, 92
        cor, contorno = self.jogador.cor, self.jogador.cor_contorno
        baixo = [(bx + math.cos(a) * w / 2, by - 6 + math.sin(a) * h / 2)
                 for a in [i * math.pi / 20 for i in range(21)]]
        topo = []
        for i in range(9):
            x = bx + w / 2 - i * w / 8
            topo.append((x, by - 6 - (14 if i % 2 else 0)))
        casca = baixo + topo[1:-1]
        # Parte de dentro da casca (mais clara) aparecendo atrás dos dentes
        dentro = [(bx + w / 2 - 6, by - 6), (bx - w / 2 + 6, by - 6), (bx - w / 2 + 14, by + 4),
                  (bx + w / 2 - 14, by + 4)]
        pygame.draw.polygon(tela, ui.clarear(cor, 90), dentro)
        pygame.draw.polygon(tela, cor, casca)
        pygame.draw.polygon(tela, contorno, casca, 3)
        # Brilho
        brilho = [(bx + math.cos(a) * (w / 2 - 14), by - 4 + math.sin(a) * (h / 2 - 14))
                  for a in [i * math.pi / 12 for i in range(2, 7)]]
        pygame.draw.lines(tela, ui.clarear(cor, 70), False, brilho, 4)

        # Parte do barco dentro da água fica azulada
        agua = ui.misturar(cor, (30, 120, 200), 0.55)
        tela.set_clip(pygame.Rect(0, SUPERFICIE + 3, LARGURA, 80))
        pygame.draw.polygon(tela, agua, casca)
        pygame.draw.polygon(tela, ui.misturar(contorno, (20, 80, 150), 0.5), casca, 3)
        tela.set_clip(None)

    def desenhar_hud(self, tela):
        caixa = pygame.Rect(12, 12, 420, 48)
        borda = AMARELO if self.pulso_hud > 0 else BRANCO
        ui.painel(tela, caixa, (20, 24, 40), borda, 12, 3, sombra=False)
        ui.desenhar_texto(tela, f"PONTOS: {self.pontos}", (caixa.x + 16, caixa.centery), 14,
                          AMARELO, "midleft")
        rec = self.recorde()
        if rec is not None:
            ui.desenhar_texto(tela, f"RECORDE: {rec}", (caixa.x + 236, caixa.centery), 12,
                              (180, 200, 255), "midleft")

        # Relógio antes do botão de pausa
        caixa = pygame.Rect(0, 12, 170, 48)
        caixa.right = LARGURA - 76
        pouco = self.relogio <= 10
        cor = (255, 110, 110) if pouco and int(self.tempo * 4) % 2 == 0 else BRANCO
        ui.painel(tela, caixa, (20, 24, 40), cor, 12, 3, sombra=False)
        seg = int(math.ceil(self.relogio))
        pygame.draw.circle(tela, cor, (caixa.x + 26, caixa.centery + 1), 12, 3)
        pygame.draw.line(tela, cor, (caixa.x + 26, caixa.centery + 1), (caixa.x + 26, caixa.centery - 6), 3)
        pygame.draw.line(tela, cor, (caixa.x + 26, caixa.centery + 1), (caixa.x + 32, caixa.centery + 1), 3)
        ui.desenhar_texto(tela, f"{seg // 60}:{seg % 60:02d}", (caixa.right - 16, caixa.centery + 1), 16,
                          cor, "midright")

        # Sequência da mesma espécie
        if self.sequencia >= 1 and self.ultimo_tipo:
            nome = ESPECIES[self.ultimo_tipo]["nome"]
            msg = f"ÚLTIMO: {nome}" if self.sequencia < 2 else f"{nome} x{self.sequencia}  (x1.5)"
            sup = ui.texto(msg, 10, (255, 200, 120))
            caixa = pygame.Rect(12, 68, sup.get_width() + 26, 28)
            ui.painel(tela, caixa, (20, 24, 40), (255, 200, 120), 10, 2, sombra=False)
            tela.blit(sup, sup.get_rect(midleft=(caixa.x + 13, caixa.centery + 1)))

