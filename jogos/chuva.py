import math
import random

import pygame

from settings import *
from core import ui
from jogos.base import MiniJogo

# ============================================================
# CHUVA DE COMIDA
# ============================================================
# Está chovendo comida na cozinha! O seu ovo fica embaixo, de
# boca aberta, pegando tudo o que cai. Pegar comidas seguidas
# aumenta o COMBO (x2, x3). Cuidado com a PIMENTA (arde!) e com
# a BOMBA (explode!): cada uma tira uma vida.

# Cenário
BANCADA_Y = 430                 # tampo da bancada
PISO_Y = 624                    # começo do piso
CHAO = 668                      # onde o ovo pisa e as comidas caem

# Ovo
ALTURA_OVO = 100
MEIA_LARG = ALTURA_OVO * 0.45
VEL_TECLADO = 560
ACELERACAO = 3200
VEL_MOUSE = 900
BOCA_ABERTA = 2                 # índice da boca "aberta" (formato de O)

# Itens
RAIO_ITEM = 20
TAM_SPRITE = 56
VIDAS = 3
TEMPO_INVENCIVEL = 1.2
TEMPO_ARDIDO = 1.0

# Tipos: pontos (0 = ruim), peso no sorteio dos bons
BONS = [("limao", 1, 34), ("maca", 1, 34), ("melancia", 2, 18), ("bolo", 3, 11),
        ("estrela", 5, 3)]
VALOR = {nome: pontos for nome, pontos, _ in BONS}
RUINS = ("pimenta", "bomba")

TECLAS_ESQ = (pygame.K_LEFT, pygame.K_a)
TECLAS_DIR = (pygame.K_RIGHT, pygame.K_d)


def _vel_queda(t):
    return min(460.0, 170.0 + 4.2 * t)


def _intervalo(t):
    return max(0.36, 1.0 - 0.011 * t)


def _chance_ruim(t):
    return min(0.32, 0.12 + 0.004 * t)


def _multiplicador(combo):
    return 3 if combo >= 10 else 2 if combo >= 5 else 1


# ============================================================
# DESENHO DAS COMIDAS (feito uma vez só, com cache)
# ============================================================

_sprites = {}
Z = 3                           # desenha 3x maior e diminui (fica suave)


def _novo():
    lado = TAM_SPRITE * Z
    return pygame.Surface((lado, lado), pygame.SRCALPHA)


def _maca():
    s = _novo()
    contorno, corpo = (130, 20, 30), (225, 45, 55)
    for cor, extra in ((contorno, 6), (corpo, 0)):
        pygame.draw.circle(s, cor, (62, 96), 44 + extra)
        pygame.draw.circle(s, cor, (106, 96), 44 + extra)
        pygame.draw.circle(s, cor, (84, 116), 42 + extra)
    pygame.draw.circle(s, contorno, (84, 56), 10)                     # covinha
    pygame.draw.ellipse(s, (255, 150, 150), (50, 70, 22, 34))          # brilho
    pygame.draw.line(s, (100, 60, 30), (84, 60), (92, 22), 8)          # cabinho
    folha = [(94, 36), (116, 18), (140, 22), (118, 42)]
    pygame.draw.polygon(s, (70, 170, 60), folha)
    pygame.draw.polygon(s, (40, 110, 40), folha, 3)
    return s


def _melancia():
    s = _novo()
    c = (84, 58)
    for cor, raio in (((30, 100, 40), 76), ((110, 195, 80), 68), ((235, 250, 215), 61),
                      ((240, 60, 80), 55)):
        pygame.draw.circle(s, cor, c, raio, draw_bottom_left=True, draw_bottom_right=True)
    pygame.draw.line(s, (200, 40, 60), (c[0] - 55, c[1]), (c[0] + 55, c[1]), 4)
    for dx, dy in ((-30, 14), (-8, 26), (16, 16), (34, 30), (4, 44), (-24, 38)):
        pygame.draw.ellipse(s, (30, 20, 20), (c[0] + dx - 4, c[1] + dy - 6, 8, 12))
    return s


def _bolo():
    s = _novo()
    # Forminha listrada
    forma = [(38, 100), (130, 100), (114, 156), (54, 156)]
    pygame.draw.polygon(s, (230, 110, 150), forma)
    for i in range(1, 6):
        x1 = 38 + i * 92 / 6
        x2 = 54 + i * 60 / 6
        pygame.draw.line(s, (190, 70, 110), (x1, 100), (x2, 156), 4)
    pygame.draw.polygon(s, (150, 50, 90), forma, 4)
    # Cobertura em camadas
    for cor, extra in (((170, 90, 110), 5), ((255, 215, 230), 0)):
        pygame.draw.ellipse(s, cor, (30 - extra, 72 - extra, 108 + extra * 2, 40 + extra * 2))
        pygame.draw.ellipse(s, cor, (44 - extra, 48 - extra, 80 + extra * 2, 38 + extra * 2))
        pygame.draw.ellipse(s, cor, (60 - extra, 28 - extra, 48 + extra * 2, 30 + extra * 2))
    # Confeitos
    for (x, y), cor in (((56, 84), (80, 160, 240)), ((84, 64), (250, 200, 60)),
                        ((110, 86), (90, 200, 120)), ((76, 96), (240, 90, 90)),
                        ((100, 60), (160, 110, 230))):
        pygame.draw.line(s, cor, (x - 5, y - 3), (x + 5, y + 3), 6)
    # Cereja
    pygame.draw.line(s, (60, 120, 40), (86, 18), (100, 2), 4)
    pygame.draw.circle(s, (130, 10, 20), (84, 22), 14)
    pygame.draw.circle(s, (220, 30, 45), (84, 22), 11)
    pygame.draw.circle(s, (255, 170, 170), (80, 18), 4)
    return s


def _estrela():
    s = _novo()
    c = (84, 88)
    pygame.draw.circle(s, (255, 240, 150, 70), c, 80)
    ui.estrela(s, c, 76, (170, 110, 10))
    ui.estrela(s, c, 66, (255, 205, 40))
    ui.estrela(s, (c[0] - 4, c[1] - 6), 34, (255, 240, 150))
    return s


def _pimenta():
    s = _novo()
    pontos = []
    for i in range(14):
        t = i / 13
        x = 48 + t * 84
        y = 58 + t * 70 + math.sin(t * math.pi) * -26
        pontos.append((x, y, 30 - t * 24))
    for cor, extra in (((120, 10, 10), 5), ((220, 35, 30), 0)):
        for x, y, r in pontos:
            pygame.draw.circle(s, cor, (int(x), int(y)), int(r + extra))
    # Brilho
    for x, y, r in pontos[2:9]:
        pygame.draw.circle(s, (255, 130, 110), (int(x - r * 0.2), int(y - r * 0.55)), max(2, int(r * 0.22)))
    # Cabinho verde
    pygame.draw.circle(s, (40, 110, 40), (44, 52), 20)
    pygame.draw.circle(s, (80, 170, 70), (44, 52), 15)
    pygame.draw.line(s, (40, 110, 40), (40, 44), (22, 16), 9)
    return s


def _bomba():
    s = _novo()
    c = (80, 100)
    pygame.draw.circle(s, (15, 15, 25), c, 58)
    pygame.draw.circle(s, (50, 50, 68), c, 52)
    pygame.draw.ellipse(s, (130, 130, 155), (46, 66, 30, 20))
    pygame.draw.rect(s, (15, 15, 25), (62, 30, 40, 26), border_radius=4)
    pygame.draw.rect(s, (120, 120, 135), (66, 34, 32, 18), border_radius=3)
    pygame.draw.lines(s, (190, 150, 90), False, [(82, 32), (88, 18), (102, 10), (116, 12)], 7)
    return s


def _limao():
    s = _novo()
    lim = ui.limao_sup(18 * Z)
    s.blit(lim, lim.get_rect(center=(TAM_SPRITE * Z // 2, TAM_SPRITE * Z // 2)))
    return s


_DESENHOS = {"limao": _limao, "maca": _maca, "melancia": _melancia, "bolo": _bolo,
             "estrela": _estrela, "pimenta": _pimenta, "bomba": _bomba}

# Ponta do pavio da bomba em relação ao centro do sprite (já no tamanho final)
PAVIO = ((116 - TAM_SPRITE * Z / 2) / Z, (12 - TAM_SPRITE * Z / 2) / Z)


def _sprite(tipo):
    s = _sprites.get(tipo)
    if s is None:
        s = pygame.transform.smoothscale(_DESENHOS[tipo](), (TAM_SPRITE, TAM_SPRITE))
        _sprites[tipo] = s
    return s


_sombras = {}


def _sombra(largura):
    """Elipse escura semitransparente (com cache por tamanho)."""
    largura = max(6, int(largura) // 2 * 2)
    s = _sombras.get(largura)
    if s is None:
        altura = max(3, largura // 4)
        s = pygame.Surface((largura, altura), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (40, 25, 20, 40 + min(70, largura)), s.get_rect())
        _sombras[largura] = s
    return s


_claroes = {}


def _clarao(raio):
    """Brilho semitransparente da explosão (com cache por tamanho)."""
    raio = max(8, int(raio) // 4 * 4)
    s = _claroes.get(raio)
    if s is None:
        s = pygame.Surface((raio * 2, raio * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (255, 180, 60, 120), (raio, raio), raio)
        pygame.draw.circle(s, (255, 240, 180, 150), (raio, raio), int(raio * 0.7))
        _claroes[raio] = s
    return s


# ============================================================
# ITEM QUE CAI
# ============================================================

class Item:

    def __init__(self, tipo, x, y, vel):
        self.tipo = tipo
        self.x = x
        self.y = y
        self.vel = vel
        self.bom = tipo not in RUINS
        self.fase = random.uniform(0, math.tau)
        self.giro = random.uniform(1.5, 3.0) * random.choice((-1, 1))

    def angulo(self, tempo):
        if self.tipo == "estrela":
            return (tempo * 90 * self.giro) % 360
        if self.tipo == "bomba":
            return math.sin(tempo * self.giro + self.fase) * 10
        return math.sin(tempo * self.giro + self.fase) * 22


# ============================================================
# JOGO
# ============================================================

class ChuvaComida(MiniJogo):

    ID = "chuva"
    MOEDAS_POR = 8
    MOEDAS_MAX = 45
    TITULO = "CHUVA DE COMIDA"
    TITULO_CURTO = "CHUVA"
    DESCRICAO = "Está chovendo comida na cozinha! Pegue tudo de boca aberta e fuja da pimenta e da bomba."
    COR = (230, 110, 70)
    INSTRUCOES = [
        "Pegue as comidas com a boca do seu ovo!",
        "Pegar várias seguidas faz COMBO (x2 e x3).",
        "A ESTRELA vale 5! PIMENTA e BOMBA tiram vida.",
        "SETAS, A D ou o MOUSE para mover",
    ]
    OPCOES = None
    MENOR_MELHOR = False
    ROTULO_PONTOS = "PONTOS"
    CONTAGEM = True

    # --------------------------------------------------------
    # CENÁRIO: cozinha
    # --------------------------------------------------------

    @classmethod
    def criar_fundo(cls, jogador):
        sup = pygame.Surface((LARGURA, ALTURA))
        rnd = random.Random(8)

        # Parede de azulejos
        sup.fill((226, 236, 240))
        lado = 48
        for linha in range(BANCADA_Y // lado + 1):
            for col in range(LARGURA // lado + 1):
                r = pygame.Rect(col * lado, linha * lado, lado, lado)
                cor = (236, 244, 248) if (linha + col) % 2 == 0 else (218, 232, 238)
                pygame.draw.rect(sup, cor, r)
                pygame.draw.rect(sup, (190, 205, 212), r, 2)
        # Faixa decorativa de azulejos azuis
        for col in range(LARGURA // lado + 1):
            r = pygame.Rect(col * lado, 336, lado, lado)
            pygame.draw.rect(sup, (90, 150, 210), r)
            pygame.draw.rect(sup, (190, 205, 212), r, 2)
            pygame.draw.circle(sup, (170, 210, 245), r.center, 10, 3)

        cls._janela(sup, pygame.Rect(LARGURA // 2 - 140, 66, 280, 220))
        cls._armario_alto(sup, pygame.Rect(34, 74, 270, 170))
        cls._armario_alto(sup, pygame.Rect(LARGURA - 304, 74, 270, 170))

        # Relógio de parede e prateleira
        rel = (LARGURA - 170, 292)
        pygame.draw.circle(sup, (60, 60, 80), rel, 30)
        pygame.draw.circle(sup, (255, 250, 240), rel, 25)
        for i in range(12):
            a = i * math.tau / 12
            pygame.draw.circle(sup, (60, 60, 80), (int(rel[0] + math.cos(a) * 20),
                                                   int(rel[1] + math.sin(a) * 20)), 2)
        pygame.draw.line(sup, (40, 40, 60), rel, (rel[0], rel[1] - 16), 3)
        pygame.draw.line(sup, (40, 40, 60), rel, (rel[0] + 11, rel[1] + 4), 3)

        prat = pygame.Rect(70, 300, 210, 12)
        pygame.draw.rect(sup, (150, 100, 60), prat, border_radius=3)
        pygame.draw.rect(sup, (110, 70, 40), prat, 2, border_radius=3)
        for i, cor in enumerate(((240, 180, 60), (200, 90, 70), (120, 180, 90), (230, 230, 240))):
            pote = pygame.Rect(84 + i * 50, 262, 34, 38)
            pygame.draw.rect(sup, cor, pote, border_radius=6)
            pygame.draw.rect(sup, (90, 80, 90), pote, 2, border_radius=6)
            pygame.draw.rect(sup, (150, 100, 60), (pote.x + 3, pote.y - 8, 28, 10), border_radius=3)
            pygame.draw.rect(sup, ui.clarear(cor, 50), (pote.x + 6, pote.y + 8, 5, 20), border_radius=2)

        # Bancada e armários de baixo
        pygame.draw.rect(sup, (150, 96, 58), (0, BANCADA_Y + 22, LARGURA, PISO_Y - BANCADA_Y - 22))
        porta_l = 124
        for i in range(LARGURA // porta_l + 1):
            r = pygame.Rect(8 + i * porta_l, BANCADA_Y + 42, porta_l - 16, PISO_Y - BANCADA_Y - 58)
            pygame.draw.rect(sup, (176, 118, 72), r, border_radius=6)
            pygame.draw.rect(sup, (120, 76, 44), r, 3, border_radius=6)
            pygame.draw.rect(sup, (196, 140, 92), r.inflate(-24, -24), 2, border_radius=4)
            pygame.draw.circle(sup, (230, 200, 120), (r.right - 16, r.centery), 6)
            pygame.draw.circle(sup, (140, 110, 60), (r.right - 16, r.centery), 6, 2)
        pygame.draw.rect(sup, (235, 232, 225), (0, BANCADA_Y, LARGURA, 24))
        pygame.draw.rect(sup, (200, 196, 190), (0, BANCADA_Y + 16, LARGURA, 8))
        pygame.draw.line(sup, (170, 165, 160), (0, BANCADA_Y + 24), (LARGURA, BANCADA_Y + 24), 2)
        for _ in range(40):
            x = rnd.randrange(LARGURA)
            pygame.draw.line(sup, (215, 212, 205), (x, BANCADA_Y + 4),
                             (x + rnd.randint(10, 30), BANCADA_Y + rnd.randint(4, 14)), 1)

        # Coisas em cima da bancada
        cls._chaleira(sup, 150, BANCADA_Y)
        cls._fruteira(sup, LARGURA - 190, BANCADA_Y)
        tabua = pygame.Rect(410, BANCADA_Y - 8, 120, 10)
        pygame.draw.rect(sup, (200, 150, 90), tabua, border_radius=4)
        pygame.draw.rect(sup, (140, 95, 50), tabua, 2, border_radius=4)
        pygame.draw.ellipse(sup, (240, 200, 60), (430, BANCADA_Y - 22, 36, 16))

        # Rodapé e piso xadrez em perspectiva
        pygame.draw.rect(sup, (110, 70, 44), (0, PISO_Y - 8, LARGURA, 8))
        fuga = (LARGURA // 2, PISO_Y - 900)
        linhas_y = [PISO_Y, 640, 660, 684, 720]
        cols = range(-14, 15)
        for li in range(len(linhas_y) - 1):
            y1, y2 = linhas_y[li], linhas_y[li + 1]
            for ci in cols:
                def px(xb, y):
                    return fuga[0] + (xb - fuga[0]) * (y - fuga[1]) / (PISO_Y - fuga[1])
                x_a, x_b = LARGURA // 2 + ci * 56, LARGURA // 2 + (ci + 1) * 56
                pontos = [(px(x_a, y1), y1), (px(x_b, y1), y1), (px(x_b, y2), y2), (px(x_a, y2), y2)]
                cor = (240, 236, 228) if (li + ci) % 2 == 0 else (200, 70, 70)
                pygame.draw.polygon(sup, cor, pontos)
        return sup

    @staticmethod
    def _janela(sup, r):
        # Céu lá fora (recortado no vidro)
        sup.set_clip(r)
        sup.blit(ui.gradiente(r.w, r.h, (110, 180, 240), (200, 232, 250)), r.topleft)
        pygame.draw.circle(sup, (255, 230, 120), (r.right - 50, r.y + 50), 24)
        for cx, cy in ((r.x + 70, r.y + 60), (r.x + 170, r.y + 120)):
            for dx, rr in ((-18, 14), (0, 20), (20, 15)):
                pygame.draw.circle(sup, BRANCO, (cx + dx, cy), rr)
        pygame.draw.ellipse(sup, (110, 180, 100), (r.x - 40, r.bottom - 50, 200, 100))
        pygame.draw.ellipse(sup, (90, 160, 90), (r.x + 120, r.bottom - 40, 220, 100))
        sup.set_clip(None)

        # Moldura
        pygame.draw.rect(sup, (250, 250, 250), r, 12)
        pygame.draw.rect(sup, (160, 170, 180), r, 3)
        pygame.draw.line(sup, (250, 250, 250), (r.centerx, r.y), (r.centerx, r.bottom), 10)
        pygame.draw.line(sup, (250, 250, 250), (r.x, r.centery), (r.right, r.centery), 10)

        # Parapeito com vasinho
        pygame.draw.rect(sup, (235, 235, 240), (r.x - 20, r.bottom - 4, r.w + 40, 14), border_radius=4)
        pygame.draw.rect(sup, (170, 175, 185), (r.x - 20, r.bottom - 4, r.w + 40, 14), 2, border_radius=4)
        vaso = pygame.Rect(r.x + 24, r.bottom - 30, 30, 26)
        pygame.draw.rect(sup, (200, 110, 70), vaso, border_radius=4)
        for dx in (-10, 0, 10):
            pygame.draw.ellipse(sup, (70, 160, 70), (vaso.centerx + dx - 7, vaso.y - 22, 14, 26))

        # Cortinas
        for lado in (-1, 1):
            x0 = r.x - 34 if lado < 0 else r.right - 14
            cortina = pygame.Rect(x0, r.y - 16, 48, r.h + 30)
            pygame.draw.rect(sup, (240, 120, 130), cortina, border_radius=10)
            for i in range(1, 4):
                pygame.draw.line(sup, (210, 90, 105), (cortina.x + i * 12, cortina.y + 4),
                                 (cortina.x + i * 12, cortina.bottom - 6), 2)
            pygame.draw.rect(sup, (180, 70, 90), cortina, 2, border_radius=10)
            pygame.draw.rect(sup, (250, 220, 120), (cortina.x - 2, cortina.centery + 20, 52, 8),
                             border_radius=4)
        pygame.draw.rect(sup, (150, 100, 60), (r.x - 50, r.y - 22, r.w + 100, 8), border_radius=4)

    @staticmethod
    def _armario_alto(sup, r):
        pygame.draw.rect(sup, (0, 0, 0), r.move(4, 6), border_radius=6)
        pygame.draw.rect(sup, (176, 118, 72), r, border_radius=6)
        pygame.draw.rect(sup, (120, 76, 44), r, 3, border_radius=6)
        meia = r.w // 2
        for i in range(2):
            porta = pygame.Rect(r.x + 8 + i * meia, r.y + 8, meia - 16, r.h - 16)
            pygame.draw.rect(sup, (196, 140, 92), porta, border_radius=4)
            pygame.draw.rect(sup, (140, 90, 54), porta, 2, border_radius=4)
            pygame.draw.rect(sup, (210, 160, 110), porta.inflate(-22, -22), 2, border_radius=4)
            px = porta.right - 12 if i == 0 else porta.x + 12
            pygame.draw.circle(sup, (230, 200, 120), (px, porta.bottom - 22), 5)

    @staticmethod
    def _chaleira(sup, x, y):
        corpo = pygame.Rect(x - 34, y - 52, 68, 52)
        pygame.draw.ellipse(sup, (60, 60, 80), corpo.inflate(4, 4))
        pygame.draw.ellipse(sup, (230, 80, 70), corpo)
        pygame.draw.polygon(sup, (230, 80, 70), [(x + 26, y - 30), (x + 56, y - 46), (x + 50, y - 38),
                                                 (x + 28, y - 18)])
        pygame.draw.arc(sup, (60, 60, 80), (x - 24, y - 78, 48, 44), 0, math.pi, 5)
        pygame.draw.ellipse(sup, (255, 170, 160), (x - 22, y - 42, 16, 12))
        pygame.draw.rect(sup, (60, 60, 80), (x - 6, y - 58, 12, 8), border_radius=3)

    @staticmethod
    def _fruteira(sup, x, y):
        # Frutas por cima da tigela
        for dx, dy, cor in ((-22, -44, (240, 200, 50)), (0, -54, (220, 50, 60)),
                            (22, -44, (250, 150, 40)), (-10, -40, (120, 190, 70)),
                            (12, -38, (220, 50, 60))):
            pygame.draw.circle(sup, ui.escurecer(cor, 60), (x + dx, y + dy), 15)
            pygame.draw.circle(sup, cor, (x + dx, y + dy), 13)
            pygame.draw.circle(sup, ui.clarear(cor, 70), (x + dx - 4, y + dy - 4), 3)
        # Tigela (meio círculo apoiado na bancada)
        pygame.draw.circle(sup, (50, 90, 150), (x, y - 38), 44, draw_bottom_left=True,
                           draw_bottom_right=True)
        pygame.draw.circle(sup, (100, 160, 220), (x, y - 38), 40, draw_bottom_left=True,
                           draw_bottom_right=True)
        pygame.draw.line(sup, (50, 90, 150), (x - 44, y - 38), (x + 44, y - 38), 4)

    @classmethod
    def desenhar_icone(cls, sup, jogador):
        w, h = sup.get_size()
        ap = jogador.aparencia()
        aberta = (ap[0], ap[1], ap[2], BOCA_ABERTA)
        jogador.desenhar(sup, (w // 2, h - h * 0.24), h * 0.36, aparencia=aberta)
        for tipo, fx, fy, esc in (("maca", 0.22, 0.26, 0.62), ("estrela", 0.5, 0.18, 0.62),
                                  ("bolo", 0.78, 0.3, 0.62), ("bomba", 0.28, 0.6, 0.55),
                                  ("melancia", 0.74, 0.6, 0.55)):
            s = pygame.transform.smoothscale(_sprite(tipo), (int(TAM_SPRITE * esc), int(TAM_SPRITE * esc)))
            sup.blit(s, s.get_rect(center=(int(w * fx), int(h * fy))))

    # --------------------------------------------------------
    # PARTIDA
    # --------------------------------------------------------

    def reiniciar(self):
        self.x = LARGURA / 2
        self.vx = 0.0
        self.inclinacao = 0.0
        self.esticar = 0.0
        self.vel_esticar = 0.0
        self.alvo_mouse = None
        self.teclas = set()

        self.vidas = VIDAS
        self.combo = 0
        self.maior_combo = 0
        self.itens = []
        self.claroes = []            # brilho das explosões
        self.relogio = 0.0           # tempo de partida (dificuldade)
        self.proximo = 0.8
        self.invencivel = 0.0
        self.ardido = 0.0
        self.fumaca = 0.0
        self.mastigar = 0.0
        self.morto = False
        self.tempo_morto = 0.0

        # Algumas comidas já caindo (e aparecem na prévia)
        for x, y, tipo in ((250, 150, "maca"), (760, 40, "limao"), (430, -60, "melancia")):
            self.itens.append(Item(tipo, x, y, _vel_queda(0)))

    # --------------------------------------------------------
    # CONTROLES
    # --------------------------------------------------------

    def evento(self, e):
        # Acompanha as teclas em qualquer estado (para não "grudar" na pausa)
        if e.type == pygame.KEYDOWN:
            self.teclas.add(e.key)
        elif e.type == pygame.KEYUP:
            self.teclas.discard(e.key)
        elif e.type == pygame.WINDOWFOCUSLOST:
            self.teclas.clear()
        super().evento(e)

    def evento_jogo(self, e):
        if e.type == pygame.MOUSEMOTION:
            # Não segue o mouse quando ele está no botão de pausa
            if not self.botao_pausa.collidepoint(e.pos):
                self.alvo_mouse = e.pos[0]
        elif e.type == pygame.KEYDOWN and e.key in TECLAS_ESQ + TECLAS_DIR:
            self.alvo_mouse = None

    # --------------------------------------------------------
    # LÓGICA
    # --------------------------------------------------------

    @property
    def centro_y(self):
        return CHAO - ALTURA_OVO / 2

    def atualizar_jogo(self, dt):
        self.relogio += dt
        self._mover_ovo(dt)
        self._animar(dt)

        if self.morto:
            self.tempo_morto += dt
            if self.tempo_morto > 1.2:
                self.terminar(linhas=[f"PONTOS: {self.pontos}", f"MAIOR COMBO: {self.maior_combo}"])
        else:
            self.proximo -= dt
            if self.proximo <= 0:
                if self._criar_item():
                    self.proximo = _intervalo(self.relogio) * random.uniform(0.8, 1.2)
                else:
                    self.proximo = 0.1          # sem espaço agora: tenta de novo logo

        self._mover_itens(dt)

        self.claroes = [[x, y, t - dt] for x, y, t in self.claroes if t - dt > 0]

    def _mover_ovo(self, dt):
        if self.morto:
            self.vx *= max(0.0, 1 - dt * 8)
        else:
            direcao = 0
            if any(t in self.teclas for t in TECLAS_ESQ):
                direcao -= 1
            if any(t in self.teclas for t in TECLAS_DIR):
                direcao += 1

            if direcao:
                self.alvo_mouse = None
                alvo = direcao * VEL_TECLADO
            elif self.alvo_mouse is not None:
                # Vai freando ao chegar perto do mouse (sem passar do ponto)
                dist = self.alvo_mouse - self.x
                vel = min(VEL_MOUSE, abs(dist) * 10, math.sqrt(2 * ACELERACAO * abs(dist)) * 0.8)
                alvo = math.copysign(vel, dist)
            else:
                alvo = 0.0

            passo = ACELERACAO * dt
            self.vx += max(-passo, min(passo, alvo - self.vx))

        self.x += self.vx * dt
        minimo, maximo = MEIA_LARG + 10, LARGURA - MEIA_LARG - 10
        if self.x < minimo or self.x > maximo:
            self.x = max(minimo, min(maximo, self.x))
            self.vx = 0.0

    def _animar(self, dt):
        # Inclina na direção do movimento
        alvo = -self.vx / VEL_MOUSE * 14
        self.inclinacao += (alvo - self.inclinacao) * min(1.0, dt * 12)

        # Mola do squash & stretch
        self.vel_esticar += (-300 * self.esticar - 14 * self.vel_esticar) * dt
        self.esticar = max(-1.0, min(1.0, self.esticar + self.vel_esticar * dt))

        self.invencivel = max(0.0, self.invencivel - dt)
        self.mastigar = max(0.0, self.mastigar - dt)
        if self.ardido > 0:
            self.ardido -= dt
            self.fumaca -= dt
            if self.fumaca <= 0:
                self.fumaca = 0.07
                topo = (self.x + random.uniform(-20, 20), CHAO - ALTURA_OVO - 4)
                self.particulas.explodir(topo, [(210, 210, 215), (170, 170, 180), (240, 240, 240)],
                                         2, 70, 0.8, (5, 9), gravidade=-160)

    def _criar_item(self):
        """Cria um item novo sem sobrepor os outros e sem fechar a passagem."""
        t = self.relogio
        ruim = random.random() < _chance_ruim(t)
        if ruim:
            tipo = random.choice(RUINS)
        else:
            tipo = random.choices([n for n, _, _ in BONS], [p for _, _, p in BONS])[0]

        y0 = -TAM_SPRITE / 2
        for _ in range(12):
            x = random.uniform(40, LARGURA - 40)
            ok = True
            for it in self.itens:
                dy = abs(it.y - y0)
                # Não nasce em cima de outro item
                if abs(it.x - x) < 64 and dy < 110:
                    ok = False
                    break
                # Dois itens ruins lado a lado deixam espaço para o ovo passar
                if ruim and not it.bom and dy < 220 and abs(it.x - x) < 200:
                    ok = False
                    break
            if ok:
                self.itens.append(Item(tipo, x, y0, _vel_queda(t)))
                return True
        return False

    def _mover_itens(self, dt):
        cy = self.centro_y
        vivos = []
        for it in self.itens:
            it.y += it.vel * dt

            if not self.morto and self._tocou(it, cy):
                if it.bom:
                    self._pegar(it)
                    continue
                if self.invencivel <= 0:
                    self._machucar(it)
                    continue

            if it.y + RAIO_ITEM * 0.6 >= CHAO:
                self._cair_no_chao(it)
                continue
            vivos.append(it)
        self.itens = vivos

    def _tocou(self, it, cy):
        """Comida boa: só pela boca/topo. Ruim: encostar no ovo."""
        dx = it.x - self.x
        dy = it.y - cy
        if it.bom:
            if dy > ALTURA_OVO * 0.2:          # já passou da boca
                return False
            folga = RAIO_ITEM * 0.3
        else:
            folga = RAIO_ITEM * 0.45
        a = MEIA_LARG + folga
        b = ALTURA_OVO / 2 + folga
        return (dx / a) ** 2 + (dy / b) ** 2 < 1.0

    def _pegar(self, it):
        self.combo += 1
        self.maior_combo = max(self.maior_combo, self.combo)
        mult = _multiplicador(self.combo)
        ganho = VALOR[it.tipo] * mult
        self.pontos += ganho

        self.mastigar = 0.3
        self.vel_esticar -= 5.0
        pos = (it.x, CHAO - ALTURA_OVO - 10)
        cor = AMARELO if ganho > 1 else BRANCO
        self.textos.adicionar(f"+{ganho}", pos, cor, 16 if ganho > 2 else 14)

        cores = {
            "limao": [(250, 222, 40), (255, 248, 180)],
            "maca": [(225, 45, 55), (255, 150, 150)],
            "melancia": [(240, 60, 80), (110, 195, 80)],
            "bolo": [(255, 215, 230), (230, 110, 150)],
            "estrela": [AMARELO, BRANCO, (255, 240, 150)],
        }[it.tipo]
        self.particulas.explodir(pos, cores, 20 if it.tipo == "estrela" else 10, 180, 0.6)

        if it.tipo == "estrela":
            self.som("moeda")
        else:
            self.som("comer", 0.8)

        if self.combo in (5, 10):
            self.textos.adicionar(f"COMBO x{mult}!", (LARGURA // 2, 250), LARANJA, 24)
            self.som("acerto", 0.7)

    def _machucar(self, it):
        self.vidas -= 1
        self.combo = 0
        self.invencivel = TEMPO_INVENCIVEL

        if it.tipo == "pimenta":
            self.ardido = TEMPO_ARDIDO
            self.fumaca = 0.0
            self.som("erro")
            self.textos.adicionar("ARDEU!", (self.x, CHAO - ALTURA_OVO - 30), (255, 110, 80), 16)
            self.particulas.explodir((it.x, it.y), [(255, 80, 40), (255, 180, 60)], 14, 200, 0.5)
            self.tremer(0.12)
        else:
            self.som("explosao", 0.8)
            self.textos.adicionar("BUM!", (it.x, it.y - 30), (255, 150, 60), 20)
            self.particulas.explodir((it.x, it.y), [(255, 170, 40), (255, 90, 30), (255, 240, 120),
                                                    (80, 80, 90)], 40, 340, 0.8, (3, 8))
            self.claroes.append([it.x, it.y, 0.18])
            self.tremer(0.4)
            self.vel_esticar -= 8.0

        if self.vidas <= 0:
            self.vidas = 0
            self.morto = True
            self.tempo_morto = 0.0

    def _cair_no_chao(self, it):
        pos = (it.x, CHAO - 4)
        if it.bom:
            # Comida no chão não tira vida, mas acaba com o combo
            if self.combo >= 3 and not self.morto:
                self.textos.adicionar("COMBO PERDIDO", (it.x, CHAO - 50), (200, 210, 255), 12)
            self.combo = 0
            cores = {
                "limao": [(250, 222, 40)], "maca": [(225, 45, 55)], "melancia": [(240, 60, 80)],
                "bolo": [(255, 215, 230)], "estrela": [AMARELO],
            }[it.tipo]
            self.particulas.explodir(pos, cores + [(255, 255, 255)], 8, 140, 0.4, (2, 5))
        elif it.tipo == "bomba":
            # Bomba no chão só solta fumacinha (o ovo está longe)
            self.particulas.explodir(pos, [(120, 120, 130), (180, 180, 190)], 10, 120, 0.6, (3, 7),
                                     gravidade=-60)
        else:
            self.particulas.explodir(pos, [(220, 35, 30)], 6, 100, 0.4, (2, 4))

    # --------------------------------------------------------
    # DESENHO
    # --------------------------------------------------------

    def _desenhar_ovo(self, tela):
        # Sombra no chão
        s = _sombra(MEIA_LARG * 2.2)
        tela.blit(s, s.get_rect(center=(int(self.x), CHAO + 2)))

        # Pisca enquanto está invencível
        if self.invencivel > 0 and not self.morto and int(self.invencivel * 10) % 2 == 0:
            return

        ap = self.jogador.aparencia()
        if self._boca_aberta():
            ap = (ap[0], ap[1], ap[2], BOCA_ABERTA)
        sup = self.jogador.avatar(ALTURA_OVO, ap)

        e = self.esticar
        sx, sy = 1 - 0.1 * e, 1 + 0.12 * e
        if abs(e) > 0.02:
            w, h = sup.get_size()
            sup = pygame.transform.smoothscale(sup, (max(1, round(w * sx)), max(1, round(h * sy))))

        if self.ardido > 0:
            # Fica vermelho de ardido
            sup = sup.copy()
            sup.fill((255, 100, 100), special_flags=pygame.BLEND_RGB_MULT)
            sup.fill((120, 0, 0), special_flags=pygame.BLEND_RGB_ADD)

        angulo = self.inclinacao
        if self.morto:
            angulo = math.sin(self.tempo_morto * 14) * 18 * max(0.0, 1 - self.tempo_morto / 1.2)
        if abs(angulo) > 0.5:
            sup = pygame.transform.rotate(sup, angulo)

        # O "pé" do ovo fica sempre no chão
        altura = ALTURA_OVO * sy
        tela.blit(sup, sup.get_rect(center=(round(self.x), round(CHAO - altura / 2 - 1))))

    def _boca_aberta(self):
        if self.mastigar > 0 or self.morto:
            return False
        topo = CHAO - ALTURA_OVO
        for it in self.itens:
            if it.bom and 0 < topo - it.y < 190 and abs(it.x - self.x) < 110:
                return True
        return False

    def desenhar_jogo(self, tela):
        tela.blit(self.fundo(self.jogador), (0, 0))
        t = self.tempo

        # Sombras das comidas (crescem quando elas chegam perto)
        for it in self.itens:
            perto = max(0.0, min(1.0, (it.y + 40) / (CHAO + 40)))
            s = _sombra(8 + 34 * perto * perto)
            tela.blit(s, s.get_rect(center=(int(it.x), CHAO + 2)))

        self._desenhar_ovo(tela)

        # Comidas
        for it in self.itens:
            sup = _sprite(it.tipo)
            ang = it.angulo(t)
            if ang:
                sup = pygame.transform.rotate(sup, ang)
            tela.blit(sup, sup.get_rect(center=(round(it.x), round(it.y))))

            if it.tipo == "bomba":
                # Faísca do pavio
                a = math.radians(ang)
                px, py = PAVIO
                fx = it.x + px * math.cos(a) + py * math.sin(a)
                fy = it.y - px * math.sin(a) + py * math.cos(a)
                r = 4 + int(abs(math.sin(t * 20 + it.fase)) * 3)
                pygame.draw.circle(tela, (255, 150, 40), (int(fx), int(fy)), r + 2)
                pygame.draw.circle(tela, (255, 240, 120), (int(fx), int(fy)), r)
            elif it.tipo == "estrela" and int(t * 6 + it.fase) % 3 == 0:
                ui.estrela(tela, (int(it.x + 20), int(it.y - 18)), 5, BRANCO)

        # Clarão das explosões
        for x, y, vida in self.claroes:
            sup = _clarao(30 + (0.18 - vida) * 300)
            tela.blit(sup, sup.get_rect(center=(int(x), int(y))))

        self.particulas.desenhar(tela)
        self.textos.desenhar(tela)

    def desenhar_hud(self, tela):
        # Pontos e recorde no mesmo painel (a parede clara apagaria o texto)
        caixa = pygame.Rect(12, 12, 420, 48)
        ui.painel(tela, caixa, (20, 24, 40), BRANCO, 12, 3, sombra=False)
        ui.desenhar_texto(tela, f"PONTOS: {self.pontos}", (caixa.x + 16, caixa.centery), 14,
                          AMARELO, "midleft")
        rec = self.recorde()
        if rec is not None:
            ui.desenhar_texto(tela, f"RECORDE: {rec}", (caixa.x + 226, caixa.centery), 12,
                              (180, 200, 255), "midleft")

        # Vidas (corações) no canto direito, antes do botão de pausa
        caixa = pygame.Rect(0, 12, 150, 48)
        caixa.right = LARGURA - 76
        ui.painel(tela, caixa, (20, 24, 40), BRANCO, 12, 3, sombra=False)
        for i in range(VIDAS):
            c = (caixa.x + 32 + i * 43, caixa.centery + 1)
            if i < self.vidas:
                ui.coracao(tela, c, 28)
            else:
                ui.coracao(tela, c, 28, (70, 70, 90))

        # Combo embaixo dos pontos
        if self.combo >= 2:
            mult = _multiplicador(self.combo)
            cor = (255, 160, 60) if mult == 3 else AMARELO if mult == 2 else BRANCO
            texto = f"COMBO {self.combo}" + (f"  x{mult}" if mult > 1 else "")
            sup = ui.texto(texto, 14, cor)
            caixa = pygame.Rect(12, 68, sup.get_width() + 28, 34)
            ui.painel(tela, caixa, (20, 24, 40), cor, 10, 2, sombra=False)
            tela.blit(sup, sup.get_rect(midleft=(caixa.x + 14, caixa.centery + 1)))
