import math
import random

import pygame

from settings import *
from core import ui
from jogos.base import MiniJogo

# ============================================================
# PINBALL OVO
# ============================================================
# Mesa de pinball vertical onde a BOLA É O SEU OVO!
#
#   PANELAS (bumpers)  -> quicam o ovo com força e tremem
#   LIMÕES (alvos)     -> acendem; os 4 acesos = MULTIPLICADOR +1
#   L-I-M-A-O          -> luzes nos canais de cima (o flipper troca
#                         as luzes de lugar); completou = bônus
#   RAMPA              -> canal na direita que leva o ovo por cima
#                         da mesa e o devolve no flipper esquerdo
#   NINHO              -> segura o ovo 1 s e dispara de novo
#   SALVA-OVO          -> caiu logo depois de lançar? volta uma vez
#
# A física roda em sub-passos pequenos (o ovo anda no máximo
# ~5 px por passo), então nada atravessa nada.

# ------------------------------------------------------------
# GEOMETRIA DA MESA
# ------------------------------------------------------------
MESA_ESQ = 240
MESA_DIR = 784
MESA_TOPO = 40
MESA_BAIXO = ALTURA
DIVISORIA_X = 744                   # parede entre o campo e o canal da mola
CENTRO_X = (MESA_ESQ + DIVISORIA_X) // 2    # 492 (meio do campo)

RAIO = 13                           # raio do ovo (bola)
OVO_ALT = 28                        # altura do avatar desenhado

GRAVIDADE = 1000.0
VEL_MAX = 1900.0
PASSO_MAX = 5.0                     # px por sub-passo (relativo)
SUB_MIN = 1 / 240

QUIQUE_PAREDE = 0.45
QUIQUE_FLIPPER = 0.3
QUIQUE_ALVO = 0.55

# Arcos do topo: (centro, raio, ângulo inicial, ângulo final) em graus
ARCO_ESQ = ((340, 140), 100, 180, 270)
ARCO_DIR = ((664, 160), 120, 270, 360)

# Flippers
PIVO_ESQ = (398, 628)
PIVO_DIR = (984 - 398, 628)         # espelhado no meio do campo
FLIPPER_COMP = 74
FLIPPER_R_PIVO = 11
FLIPPER_R_PONTA = 6
ANG_DESCANSO = math.radians(30)
ANG_LEVANTADO = math.radians(-28)
VEL_SUBIR = 18.0                    # rad/s
VEL_DESCER = 12.0

# Mola (lançador)
MOLA_X = (DIVISORIA_X + MESA_DIR) / 2        # 764
MOLA_Y = 680                        # topo da mola em repouso
MOLA_CURSO = 36
TEMPO_CARGA = 1.0
LANCE_MIN = 620.0
LANCE_MAX = 1780.0

# Panelas (bumpers)
PANELAS = [(410, 220), (574, 220), (492, 305)]
R_PANELA = 26
CHUTE_PANELA = 520.0
SAIDA_PANELA = 680.0
CORES_PANELA = [(230, 70, 70), (70, 140, 235), (80, 190, 90)]

# Alvos-limão
ALVOS = [(358, 452), (446, 405), (538, 405), (626, 452)]
R_ALVO = 14

# Estilingues (triângulos acima dos flippers). O lado A-C chuta.
SLING_ESQ = [(284, 430), (284, 505), (352, 556)]
SLING_DIR = [(984 - x, y) for x, y in SLING_ESQ]
CHUTE_SLING = 520.0

# Canais L-I-M-A-O (postinhos entre eles)
POSTES_X = [348, 396, 444, 492, 540, 588]
POSTE_Y0, POSTE_Y1 = 88, 118
LINHA_ROLLOVER = 106
LETRAS = "LIMAO"

# Ninho (segura o ovo e dispara)
NINHO = (322, 262)
R_NINHO = 15
TEMPO_NINHO = 1.0

# Rampa: entrada na direita (ovo subindo), sai no canal esquerdo
RAMPA_POSTE = ((662, 250), (662, 296))
RAMPA_ENTRADA_Y = 296
RAMPA_X0, RAMPA_X1 = 666, 740
RAMPA_PTS = [(706, 300), (706, 150), (694, 106), (664, 80), (620, 68), (492, 64),
             (364, 68), (318, 82), (284, 110), (266, 150), (262, 200), (262, 300),
             (262, 400)]
VEL_RAMPA = 980.0
LARGURA_RAMPA = 40

DRENO_Y = MESA_BAIXO + 24
TEMPO_SALVA = 6.0
TEMPO_DRENO = 2.0

# Pontos (multiplicados pelo MULT)
PTS_PANELA = 100
PTS_SLING = 20
PTS_ROLLOVER = 200
PTS_ROLLOVER_ACESO = 50
PTS_ALVO = 250
PTS_ALVOS_TODOS = 1500
PTS_NINHO = 1000
PTS_RAMPA = 2000
PTS_LIMAO = 3000
MULT_MAX = 5

TECLAS_ESQ = (pygame.K_LEFT, pygame.K_a, pygame.K_z, pygame.K_LSHIFT)
TECLAS_DIR = (pygame.K_RIGHT, pygame.K_d, pygame.K_SLASH, pygame.K_RSHIFT)
TECLAS_MOLA = (pygame.K_SPACE, pygame.K_DOWN, pygame.K_s)

COR_CAMPO_TOPO = (40, 44, 110)
COR_CAMPO_BAIXO = (18, 20, 58)
COR_TRILHO = (205, 215, 240)
COR_TRILHO_ESC = (70, 76, 120)


# ------------------------------------------------------------
# SEGMENTOS (paredes em forma de cápsula: linha + raio)
# ------------------------------------------------------------

def _pontos_arco(arco, passo=6):
    (cx, cy), r, a0, a1 = arco
    pts = []
    a = a0
    while a <= a1 + 1e-6:
        rad = math.radians(a)
        pts.append((cx + math.cos(rad) * r, cy + math.sin(rad) * r))
        a += passo
    return pts


def _segmento(a, b, r, tipo="parede"):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    folga = r + RAIO + 2
    return (ax, ay, bx, by, r, tipo, dx, dy, dx * dx + dy * dy or 1.0,
            min(ax, bx) - folga, max(ax, bx) + folga, min(ay, by) - folga, max(ay, by) + folga)


def _montar_segmentos():
    segs = []

    def linha(pts, r, tipo="parede"):
        for a, b in zip(pts, pts[1:]):
            segs.append(_segmento(a, b, r, tipo))

    arco_e = _pontos_arco(ARCO_ESQ)
    arco_d = _pontos_arco(ARCO_DIR)
    # Contorno: parede esquerda -> arco -> topo -> arco -> parede direita
    linha([(MESA_ESQ, 540)] + arco_e + arco_d + [(MESA_DIR, MESA_BAIXO + 40)], 2)
    # Divisória do canal da mola
    linha([(DIVISORIA_X, 200), (DIVISORIA_X, MESA_BAIXO + 40)], 4)
    # Guias que levam aos flippers
    linha([(MESA_ESQ, 540), PIVO_ESQ], 3)
    linha([(DIVISORIA_X, 540), PIVO_DIR], 3)
    # Paredes do ralo (embaixo dos pivôs): o ovo não entra sob o avental
    linha([PIVO_ESQ, (PIVO_ESQ[0], MESA_BAIXO + 40)], 3)
    linha([PIVO_DIR, (PIVO_DIR[0], MESA_BAIXO + 40)], 3)
    # Estilingues
    for tri in (SLING_ESQ, SLING_DIR):
        a, b, c = tri
        segs.append(_segmento(a, b, 5))
        segs.append(_segmento(b, c, 5))
        segs.append(_segmento(c, a, 5, "sling"))
    # Postinhos dos canais L-I-M-A-O
    for x in POSTES_X:
        segs.append(_segmento((x, POSTE_Y0), (x, POSTE_Y1), 4))
    # Poste da entrada da rampa
    segs.append(_segmento(*RAMPA_POSTE, 5))
    return segs


SEGMENTOS = _montar_segmentos()


def _y_guia(x, esquerda=True):
    """Altura da guia (parede inclinada até o flipper) em x."""
    if esquerda:
        (x0, y0), (x1, y1) = (MESA_ESQ, 540), PIVO_ESQ
    else:
        (x0, y0), (x1, y1) = PIVO_DIR, (DIVISORIA_X, 540)
    t = (x - x0) / (x1 - x0)
    return y0 + (y1 - y0) * t


def _comprimentos(pts):
    acum = [0.0]
    for a, b in zip(pts, pts[1:]):
        acum.append(acum[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    return acum


# ============================================================
# DESENHOS PRÉ-RENDERIZADOS
# ============================================================

_cache = {}


def _circulo_alpha(raio, cor, alpha):
    chave = ("c", raio, cor, alpha)
    s = _cache.get(chave)
    if s is None:
        s = pygame.Surface((raio * 2 + 2, raio * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*cor, alpha), (raio + 1, raio + 1), raio)
        _cache[chave] = s
    return s


def _panela_sup(i, aceso):
    """Panela vista de cima (tampa com pegador e cabos)."""
    chave = ("panela", i, aceso)
    s = _cache.get(chave)
    if s is not None:
        return s
    cor = CORES_PANELA[i % len(CORES_PANELA)]
    if aceso:
        cor = ui.clarear(cor, 90)
    lado = (R_PANELA + 14) * 2
    s = pygame.Surface((lado, lado), pygame.SRCALPHA)
    c = lado // 2
    # Cabos (esquerda e direita)
    for sx in (-1, 1):
        cabo = pygame.Rect(0, 0, 16, 10)
        cabo.center = (c + sx * (R_PANELA + 5), c)
        pygame.draw.rect(s, (60, 40, 30), cabo, border_radius=4)
        pygame.draw.rect(s, (110, 80, 60), cabo.inflate(-4, -4), border_radius=3)
    # Corpo
    pygame.draw.circle(s, ui.escurecer(cor, 80), (c, c + 2), R_PANELA)
    pygame.draw.circle(s, cor, (c, c), R_PANELA)
    pygame.draw.circle(s, ui.clarear(cor, 50), (c, c), R_PANELA, 3)
    # Tampa metálica
    tampa = (250, 250, 255) if aceso else (190, 196, 214)
    pygame.draw.circle(s, ui.escurecer(tampa, 50), (c, c + 1), R_PANELA - 7)
    pygame.draw.circle(s, tampa, (c, c), R_PANELA - 8)
    pygame.draw.circle(s, (255, 255, 255), (c - 6, c - 6), 5)
    # Pegador da tampa
    pygame.draw.circle(s, (50, 40, 40), (c, c), 6)
    pygame.draw.circle(s, cor, (c, c), 4)
    if aceso:
        pygame.draw.circle(s, (255, 255, 255), (c, c), R_PANELA + 3, 3)
    _cache[chave] = s
    return s


def _limao_alvo(aceso):
    chave = ("limao", aceso)
    s = _cache.get(chave)
    if s is None:
        s = ui.limao_sup(R_ALVO).copy()
        if not aceso:
            s.fill((120, 120, 150), special_flags=pygame.BLEND_RGB_MULT)
        _cache[chave] = s
    return s


def _rampa_sup():
    """A rampa (transparente) por cima da mesa."""
    s = _cache.get("rampa")
    if s is not None:
        return s
    meia = LARGURA_RAMPA // 2
    xs = [p[0] for p in RAMPA_PTS]
    ys = [p[1] for p in RAMPA_PTS]
    caixa = pygame.Rect(min(xs) - meia - 8, min(ys) - meia - 8, 0, 0)
    caixa.w = max(xs) + meia + 8 - caixa.x
    caixa.h = max(ys) + meia + 8 - caixa.y
    s = pygame.Surface(caixa.size, pygame.SRCALPHA)
    pts = [(x - caixa.x, y - caixa.y) for x, y in RAMPA_PTS]
    # Corpo translúcido
    for a, b in zip(pts, pts[1:]):
        pygame.draw.line(s, (120, 200, 255, 70), a, b, LARGURA_RAMPA)
    for p in pts:
        pygame.draw.circle(s, (120, 200, 255, 70), p, meia)
    # Trilhos dos dois lados
    for lado in (-1, 1):
        borda = []
        for k, p in enumerate(pts):
            a = pts[max(0, k - 1)]
            b = pts[min(len(pts) - 1, k + 1)]
            dx, dy = b[0] - a[0], b[1] - a[1]
            n = math.hypot(dx, dy) or 1.0
            borda.append((p[0] - dy / n * meia * lado, p[1] + dx / n * meia * lado))
        pygame.draw.lines(s, (40, 60, 110, 200), False, [(x + 2, y + 3) for x, y in borda], 5)
        pygame.draw.lines(s, (210, 240, 255, 230), False, borda, 4)
    # Setinhas mostrando o caminho
    acum = _comprimentos(pts)
    total = acum[-1]
    d = 60.0
    while d < total - 30:
        (x, y), (dx, dy) = _ponto_no_caminho(pts, acum, d)
        px, py = -dy, dx
        ponta = (x + dx * 8, y + dy * 8)
        esq = (x - dx * 6 + px * 8, y - dy * 6 + py * 8)
        dir_ = (x - dx * 6 - px * 8, y - dy * 6 - py * 8)
        pygame.draw.lines(s, (255, 255, 255, 150), False, [esq, ponta, dir_], 3)
        d += 70
    _cache["rampa"] = (s, caixa.topleft)
    return _cache["rampa"]


def _ponto_no_caminho(pts, acum, d):
    """Posição e direção (normalizada) a uma distância d do começo."""
    d = max(0.0, min(acum[-1], d))
    for k in range(len(pts) - 1):
        if d <= acum[k + 1] or k == len(pts) - 2:
            seg = (acum[k + 1] - acum[k]) or 1.0
            t = (d - acum[k]) / seg
            (ax, ay), (bx, by) = pts[k], pts[k + 1]
            return (ax + (bx - ax) * t, ay + (by - ay) * t), ((bx - ax) / seg, (by - ay) / seg)
    return pts[-1], (0.0, 1.0)


# ============================================================
# PEÇAS
# ============================================================

class Flipper:

    def __init__(self, pivo, lado):
        self.px, self.py = pivo
        self.lado = lado                                    # -1 esquerdo, 1 direito
        if lado < 0:
            self.descanso, self.levantado = ANG_DESCANSO, ANG_LEVANTADO
        else:
            self.descanso, self.levantado = math.pi - ANG_DESCANSO, math.pi - ANG_LEVANTADO
        self.ang = self.descanso
        self.w = 0.0                                        # velocidade angular (rad/s)
        self.apertado = False

    def mover(self, h):
        alvo = self.levantado if self.apertado else self.descanso
        vel = VEL_SUBIR if self.apertado else VEL_DESCER
        d = alvo - self.ang
        passo = vel * h
        novo = alvo if abs(d) <= passo else self.ang + math.copysign(passo, d)
        self.w = (novo - self.ang) / h
        self.ang = novo

    @property
    def movendo(self):
        return self.ang != (self.levantado if self.apertado else self.descanso)

    def ponta(self):
        return (self.px + math.cos(self.ang) * FLIPPER_COMP,
                self.py + math.sin(self.ang) * FLIPPER_COMP)


class Bola:

    def __init__(self):
        self.x = MOLA_X
        self.y = MOLA_Y - RAIO
        self.vx = 0.0
        self.vy = 0.0
        self.ang = 0.0
        self.modo = "livre"             # livre / ninho / rampa
        self.tempo_modo = 0.0
        self.rampa_pts = None
        self.rampa_acum = None
        self.rampa_d = 0.0
        self.rastro = []
        self.parado = 0.0


# ============================================================
# JOGO
# ============================================================

class PinballOvo(MiniJogo):

    ID = "pinball_ovo"
    TITULO = "PINBALL OVO"
    TITULO_CURTO = "PINBALL"
    DESCRICAO = "Pinball onde a bola é o SEU OVO! Panelas, limões, rampa e ninho valem muitos pontos."
    COR = (120, 70, 220)
    INSTRUCOES = [
        "A bola é o SEU OVO! Não deixe ela cair.",
        "PANELAS quicam • 4 LIMÕES acesos = MULTIPLICADOR",
        "Acenda L-I-M-A-O • suba a RAMPA • ache o NINHO",
        "← → ou A D flippers • SEGURE ESPAÇO e solte",
    ]
    OPCOES = ["3 BOLAS", "5 BOLAS"]
    MENOR_MELHOR = False
    ROTULO_PONTOS = "PONTOS"
    CONTAGEM = True

    TRILHA = dict(bpm=150, tom="A", escala="maior", lead="quadrada", duty=0.25,
                  envelope="staccato", baixo="walking", onda_baixo="triangulo",
                  acomp="contratempo", onda_acomp="quadrada", bateria="shuffle",
                  energia=0.75, eco=(0.18, 0.25), vol_lead=0.15)

    MOEDAS_POR = 2000
    MOEDAS_MAX = 40
    MOEDAS_MIN = 1

    @classmethod
    def formatar(cls, valor):
        return f"{int(valor):,}".replace(",", ".")

    # --------------------------------------------------------
    # CENÁRIO: gabinete de fliperama com a mesa
    # --------------------------------------------------------

    @classmethod
    def criar_fundo(cls, jogador):
        sup = ui.gradiente(LARGURA, ALTURA, (46, 24, 80), (16, 8, 30))
        rnd = random.Random(77)

        # Luzinhas do fliperama no fundo
        for _ in range(90):
            x, y = rnd.randrange(LARGURA), rnd.randrange(ALTURA)
            cor = rnd.choice([(90, 60, 140), (120, 70, 170), (70, 50, 110), (150, 90, 60)])
            pygame.draw.circle(sup, cor, (x, y), rnd.choice((1, 2, 2, 3)))

        # Gabinete (moldura de madeira pintada)
        gab = pygame.Rect(MESA_ESQ - 20, MESA_TOPO - 22, MESA_DIR - MESA_ESQ + 40, ALTURA)
        pygame.draw.rect(sup, (10, 6, 20), gab.move(6, 6), border_radius=40)
        pygame.draw.rect(sup, (150, 40, 110), gab, border_radius=40)
        pygame.draw.rect(sup, (220, 90, 170), gab, 4, border_radius=40)
        for k in range(12):
            y = gab.y + 50 + k * 56
            for x in (gab.x + 9, gab.right - 10):
                pygame.draw.circle(sup, (255, 220, 120) if k % 2 else (255, 150, 200), (x, y), 4)

        # Campo (gradiente recortado pelo contorno da mesa)
        contorno = ([(MESA_ESQ, 540)] + _pontos_arco(ARCO_ESQ, 3)
                    + _pontos_arco(ARCO_DIR, 3)
                    + [(MESA_DIR, MESA_BAIXO), (DIVISORIA_X, MESA_BAIXO), (DIVISORIA_X, 540),
                       PIVO_DIR, (PIVO_DIR[0], MESA_BAIXO), (PIVO_ESQ[0], MESA_BAIXO), PIVO_ESQ])
        campo = ui.gradiente(LARGURA, ALTURA, COR_CAMPO_TOPO, COR_CAMPO_BAIXO).convert_alpha()
        # Padrão de ovinhos no campo
        for _ in range(60):
            x = rnd.randrange(MESA_ESQ, MESA_DIR)
            y = rnd.randrange(MESA_TOPO, ALTURA)
            r = pygame.Rect(0, 0, 10, 13)
            r.center = (x, y)
            pygame.draw.ellipse(campo, (60, 64, 140), r, 2)
        # Ovo gigante no meio (arte da mesa)
        grande = pygame.Rect(0, 0, 230, 290)
        grande.center = (CENTRO_X, 330)
        pygame.draw.ellipse(campo, (52, 56, 132), grande)
        pygame.draw.ellipse(campo, (72, 78, 170), grande, 4)
        mascara = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        pygame.draw.polygon(mascara, (255, 255, 255, 255), contorno)
        campo.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        sup.blit(campo, (0, 0))

        # Avental (área embaixo das guias) com placas
        for pts in ([(MESA_ESQ, 540), PIVO_ESQ, (PIVO_ESQ[0], MESA_BAIXO), (MESA_ESQ, MESA_BAIXO)],
                    [(DIVISORIA_X, 540), PIVO_DIR, (PIVO_DIR[0], MESA_BAIXO),
                     (DIVISORIA_X, MESA_BAIXO)]):
            pygame.draw.polygon(sup, (120, 30, 90), pts)
        ui.desenhar_texto(sup, "OVAL", (300, 660), 14, (255, 210, 120), "center")
        ui.desenhar_texto(sup, "PINBALL", (684, 660), 10, (255, 210, 120), "center")

        # Setas pintadas no campo
        def seta(x, y, ang, cor):
            dx, dy = math.cos(ang), math.sin(ang)
            px, py = -dy, dx
            pts = [(x + dx * 14, y + dy * 14), (x - dx * 8 + px * 10, y - dy * 8 + py * 10),
                   (x - dx * 2, y - dy * 2), (x - dx * 8 - px * 10, y - dy * 8 - py * 10)]
            pygame.draw.polygon(sup, cor, pts)
        for k in range(3):
            seta(706, 380 - k * 26, -math.pi / 2, (90 + k * 50, 200, 255))
        ui.desenhar_texto(sup, "RAMPA", (706, 410), 8, (150, 220, 255), "center")
        ui.desenhar_texto(sup, "NINHO", (NINHO[0], NINHO[1] + 30), 8, (255, 210, 150), "center")
        seta(CENTRO_X, 560, -math.pi / 2, (255, 200, 80))

        # Canal da mola
        pygame.draw.rect(sup, (26, 26, 60), (DIVISORIA_X + 4, 200, MESA_DIR - DIVISORIA_X - 6,
                                             MESA_BAIXO - 200))
        for y in range(230, MOLA_Y - 20, 40):
            pygame.draw.polygon(sup, (70, 70, 130), [(MOLA_X, y - 8), (MOLA_X - 8, y + 4),
                                                     (MOLA_X + 8, y + 4)])

        # Ninho (galhinhos)
        pygame.draw.circle(sup, (60, 40, 30), NINHO, R_NINHO + 8)
        for k in range(14):
            a = k * math.tau / 14
            a2 = a + 1.4
            r1, r2 = R_NINHO + 6, R_NINHO + 2
            pygame.draw.line(sup, (150, 100, 55), (NINHO[0] + math.cos(a) * r1, NINHO[1] + math.sin(a) * r1),
                             (NINHO[0] + math.cos(a2) * r2, NINHO[1] + math.sin(a2) * r2), 3)
        pygame.draw.circle(sup, (25, 16, 12), NINHO, R_NINHO - 2)

        # Paredes (trilhos cromados)
        for seg in SEGMENTOS:
            ax, ay, bx, by, r = seg[:5]
            if seg[5] == "sling":
                continue
            esp = max(6, int(r * 2))
            pygame.draw.line(sup, COR_TRILHO_ESC, (ax + 2, ay + 3), (bx + 2, by + 3), esp)
            pygame.draw.line(sup, COR_TRILHO, (ax, ay), (bx, by), esp)
            for p in ((ax, ay), (bx, by)):
                pygame.draw.circle(sup, COR_TRILHO, (int(p[0]), int(p[1])), esp // 2)

        # Estilingues (triângulos com borracha)
        for tri in (SLING_ESQ, SLING_DIR):
            pygame.draw.polygon(sup, (255, 120, 60), tri)
            pygame.draw.polygon(sup, (255, 190, 90), tri, 3)
            pygame.draw.circle(sup, COR_TRILHO, tri[1], 5)

        # Painéis laterais (placar e controles) - só a moldura
        for caixa in (pygame.Rect(14, 76, 196, 628), pygame.Rect(814, 76, 196, 628)):
            ui.painel(sup, caixa, (24, 18, 48), (180, 110, 255), 16, 4)

        esq = pygame.Rect(14, 76, 196, 628)
        for rot, y in (("PONTOS", 94), ("RECORDE", 160), ("BOLA", 214), ("MULTIPLICADOR", 296),
                       ("BÔNUS", 378), ("LUZES", 442), ("LIMÕES", 522)):
            ui.desenhar_texto(sup, rot, (esq.centerx, y), 10, (190, 160, 255), "midtop")

        dir_ = pygame.Rect(814, 76, 196, 628)
        ui.desenhar_texto(sup, "PINBALL", (dir_.centerx, 100), 20, AMARELO, "midtop")
        ui.desenhar_texto(sup, "OVO", (dir_.centerx, 130), 28, (255, 140, 200), "midtop")
        linhas = [("FLIPPER ESQ.", "← A Z"), ("FLIPPER DIR.", "→ D /"),
                  ("MOLA (SEGURE)", "ESPAÇO ↓")]
        y = 420
        for titulo, teclas in linhas:
            ui.desenhar_texto(sup, titulo, (dir_.centerx, y), 8, (190, 160, 255), "midtop")
            ui.desenhar_texto(sup, teclas, (dir_.centerx, y + 16), 12, BRANCO, "midtop")
            y += 52
        ui.desenhar_texto(sup, "PANELA", (dir_.x + 60, 590), 8, (255, 200, 150), "midleft")
        ui.desenhar_texto(sup, f"{PTS_PANELA}", (dir_.right - 20, 590), 8, BRANCO, "midright")
        ui.desenhar_texto(sup, "RAMPA", (dir_.x + 60, 614), 8, (150, 220, 255), "midleft")
        ui.desenhar_texto(sup, f"{PTS_RAMPA}", (dir_.right - 20, 614), 8, BRANCO, "midright")
        ui.desenhar_texto(sup, "NINHO", (dir_.x + 60, 638), 8, (255, 210, 150), "midleft")
        ui.desenhar_texto(sup, f"{PTS_NINHO}", (dir_.right - 20, 638), 8, BRANCO, "midright")
        ui.desenhar_texto(sup, "LIMÃO", (dir_.x + 60, 662), 8, AMARELO, "midleft")
        ui.desenhar_texto(sup, f"{PTS_ALVO}", (dir_.right - 20, 662), 8, BRANCO, "midright")
        pygame.draw.circle(sup, CORES_PANELA[0], (dir_.x + 40, 590), 9)
        pygame.draw.circle(sup, (200, 205, 220), (dir_.x + 40, 590), 6)
        pygame.draw.line(sup, (150, 220, 255), (dir_.x + 32, 620), (dir_.x + 48, 608), 5)
        pygame.draw.circle(sup, (150, 100, 55), (dir_.x + 40, 638), 8, 3)
        ui.limao(sup, (dir_.x + 40, 662), 9)
        return sup

    @classmethod
    def desenhar_icone(cls, sup, jogador):
        w, h = sup.get_size()
        esc = w / LARGURA
        for i, (x, y) in enumerate(PANELAS):
            c = (int(x * esc), int(y * esc))
            r = max(4, int(R_PANELA * esc))
            pygame.draw.circle(sup, CORES_PANELA[i], c, r)
            pygame.draw.circle(sup, (200, 205, 220), c, max(2, r - 3))
        for lado, (px, py) in ((-1, PIVO_ESQ), (1, PIVO_DIR)):
            a = ANG_LEVANTADO if lado < 0 else math.pi - ANG_DESCANSO
            tx = px + math.cos(a) * FLIPPER_COMP
            ty = py + math.sin(a) * FLIPPER_COMP
            pygame.draw.line(sup, (255, 214, 64), (px * esc, py * esc), (tx * esc, ty * esc),
                             max(3, int(12 * esc)))
        jogador.desenhar(sup, (w * 0.56, h * 0.5), h * 0.17, angulo=25)

    # --------------------------------------------------------
    # PARTIDA
    # --------------------------------------------------------

    def __init__(self, app, menu):
        self.teclas = set()
        super().__init__(app, menu)

    def reiniciar(self):
        self.total_bolas = 5 if self.opcao == 1 else 3
        self.bola_n = 1
        self.flippers = [Flipper(PIVO_ESQ, -1), Flipper(PIVO_DIR, 1)]
        self.carga = 0.0
        self.mola_vis = 0.0             # deslocamento desenhado da mola
        self.mola_volta = 0.0
        self.panela_flash = [0.0] * len(PANELAS)
        self.panela_treme = [0.0] * len(PANELAS)
        self.sling_flash = [0.0, 0.0]
        self.alvos = [False] * len(ALVOS)
        self.alvo_flash = [0.0] * len(ALVOS)
        self.alvos_piscar = 0.0
        self.luzes = [False] * len(LETRAS)
        self.luzes_piscar = 0.0
        self.mult = 1
        self.bonus_bola = 0
        self.melhor_bola = 0
        self.pontos_bola = 0
        self.ninho_espera = 0.0
        self.salva = 0.0
        self.salva_usada = False
        self.saiu_canal = False
        self.ultima_rampa = -99.0
        self.drenou = 0.0
        self.banner = None
        self.esperas = {}               # cooldown dos sons
        self.cacos = []
        self.dica = 0.0
        self._ovo_base = self.jogador.avatar(OVO_ALT).copy()
        self._giros = {}
        self._rampa_acum = _comprimentos(RAMPA_PTS)
        self.bola = Bola()

    def _nova_bola(self):
        self.bola = Bola()
        self.mult = 1
        self.bonus_bola = 0
        self.pontos_bola = 0
        self.alvos = [False] * len(ALVOS)
        self.salva = 0.0
        self.salva_usada = False
        self.saiu_canal = False
        self.carga = 0.0

    # --------------------------------------------------------
    # CONTROLES
    # --------------------------------------------------------

    def evento(self, e):
        if e.type == pygame.KEYDOWN:
            self.teclas.add(e.key)
        elif e.type == pygame.KEYUP:
            self.teclas.discard(e.key)
        elif e.type == pygame.WINDOWFOCUSLOST:
            self.teclas.clear()
            self.carga = 0.0
        super().evento(e)

    def evento_jogo(self, e):
        if e.type == pygame.KEYDOWN:
            if e.key in TECLAS_ESQ:
                self._apertou_flipper(0)
            elif e.key in TECLAS_DIR:
                self._apertou_flipper(1)

    def _apertou_flipper(self, i):
        self._som("asa", 0.3, 0.04)
        # Troca de canal: as luzes L-I-M-A-O andam para o lado
        if self.luzes_piscar <= 0 and any(self.luzes) and not all(self.luzes):
            if i == 0:
                self.luzes = self.luzes[1:] + self.luzes[:1]
            else:
                self.luzes = self.luzes[-1:] + self.luzes[:-1]

    def _segurando(self, teclas):
        return any(k in self.teclas for k in teclas)

    def _na_mola(self, b):
        return b.modo == "livre" and b.x > DIVISORIA_X and b.y + RAIO >= self._topo_mola() - 4

    def _topo_mola(self):
        return MOLA_Y + self.carga * MOLA_CURSO

    def _soltar_mola(self):
        b = self.bola
        carga = self.carga
        self.carga = 0.0
        self.mola_volta = carga
        if b is None or self.drenou > 0 or not self._na_mola(b):
            return
        b.vy = -(LANCE_MIN + (LANCE_MAX - LANCE_MIN) * carga)
        b.vx = 0.0
        b.y = MOLA_Y - RAIO - 1
        self._som("pulo", 0.4 + 0.5 * carga, 0.0)
        self.particulas.explodir((b.x, b.y + RAIO), [BRANCO, (200, 200, 255)], 6, 160, 0.3, (2, 4))

    # --------------------------------------------------------
    # LÓGICA
    # --------------------------------------------------------

    def _som(self, nome, volume=1.0, espera=0.06):
        if self.esperas.get(nome, 0.0) > 0:
            return
        self.esperas[nome] = espera
        self.som(nome, volume)

    def _pontuar(self, base, pos, cor=BRANCO, tam=10, bonus=0):
        ganho = base * self.mult
        self.pontos += ganho
        self.pontos_bola += ganho
        self.bonus_bola += bonus
        if pos is not None:
            self.textos.adicionar(f"+{self.formatar(ganho)}", pos, cor, tam)
        return ganho

    def _banner(self, texto, cor=AMARELO, tempo=1.4, tam=20):
        self.banner = [texto, cor, tempo, tempo, tam]

    def atualizar_jogo(self, dt):
        dt = min(dt, 1 / 30)
        for k in list(self.esperas):
            self.esperas[k] -= dt
        self._animar(dt)

        esq = self._segurando(TECLAS_ESQ)
        dir_ = self._segurando(TECLAS_DIR)
        self.flippers[0].apertado = esq
        self.flippers[1].apertado = dir_

        # Mola
        if self._segurando(TECLAS_MOLA) and self.drenou <= 0:
            self.carga = min(1.0, self.carga + dt / TEMPO_CARGA)
        elif self.carga > 0:
            self._soltar_mola()
        self.mola_volta = max(0.0, self.mola_volta - dt * 8)

        if self.drenou > 0:
            for f in self.flippers:
                f.mover(dt)
            self.drenou -= dt
            if self.drenou <= 0:
                self._proxima_bola()
            return

        b = self.bola
        self.salva = max(0.0, self.salva - dt)
        self.ninho_espera = max(0.0, self.ninho_espera - dt)

        if b.modo == "ninho":
            for f in self.flippers:
                f.mover(dt)
            self._atualizar_ninho(b, dt)
            return
        if b.modo == "rampa":
            for f in self.flippers:
                f.mover(dt)
            self._atualizar_rampa(b, dt)
            return

        # Física em sub-passos
        v = math.hypot(b.vx, b.vy)
        extra = 1500.0 if any(f.movendo for f in self.flippers) else 0.0
        passos = max(math.ceil(dt / SUB_MIN), math.ceil((v + extra) * dt / PASSO_MAX))
        passos = min(passos, 40)
        h = dt / passos
        for _ in range(passos):
            for f in self.flippers:
                f.mover(h)
            if self._fisica(b, h):
                break

        if self.bola is not b or b.modo != "livre":
            return

        # Giro e rastro
        b.ang = (b.ang - b.vx * dt * 1.6) % 360
        b.rastro.insert(0, (b.x, b.y))
        del b.rastro[5:]

        # Saiu do canal da mola: começa o SALVA-OVO
        if not self.saiu_canal and b.x < DIVISORIA_X - RAIO and b.y < 300:
            self.saiu_canal = True
            if not self.salva_usada:
                self.salva = TEMPO_SALVA

        # Ovo parado muito tempo (preso em algum canto): sacudida
        if v < 30 and not self._na_mola(b) and not (esq or dir_):
            b.parado += dt
            if b.parado > 2.5:
                b.parado = 0.0
                b.vx = random.choice((-1, 1)) * random.uniform(120, 220)
                b.vy = -random.uniform(250, 380)
                self.tremer(0.2)
                self.textos.adicionar("SACODE!", (b.x, b.y - 30), (255, 180, 120), 12)
                self._som("bater", 0.6)
        else:
            b.parado = 0.0

    def _animar(self, dt):
        for lista in (self.panela_flash, self.panela_treme, self.sling_flash, self.alvo_flash):
            for k in range(len(lista)):
                lista[k] = max(0.0, lista[k] - dt)
        if self.alvos_piscar > 0:
            self.alvos_piscar -= dt
            if self.alvos_piscar <= 0:
                self.alvos = [False] * len(ALVOS)
        if self.luzes_piscar > 0:
            self.luzes_piscar -= dt
            if self.luzes_piscar <= 0:
                self.luzes = [False] * len(LETRAS)
        if self.banner:
            self.banner[2] -= dt
            if self.banner[2] <= 0:
                self.banner = None
        self.dica += dt
        for p in self.cacos:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[3] += 900 * dt
            p[4] += p[2] * dt
            p[5] -= dt
        self.cacos = [p for p in self.cacos if p[5] > 0]

    # ---------------- Física ----------------

    def _fisica(self, b, h):
        """Um sub-passo. Devolve True se a bola saiu de jogo."""
        b.vy += GRAVIDADE * h
        v = math.hypot(b.vx, b.vy)
        if v > VEL_MAX:
            b.vx *= VEL_MAX / v
            b.vy *= VEL_MAX / v
        y_antes = b.y
        b.x += b.vx * h
        b.y += b.vy * h

        self._colidir_segmentos(b)
        self._colidir_panelas(b)
        self._colidir_alvos(b)
        for f in self.flippers:
            self._colidir_flipper(b, f)
        self._colidir_mola(b)
        self._prender_na_mesa(b)

        # Sensores
        if b.vy > 0 and y_antes < LINHA_ROLLOVER <= b.y:
            self._rollover(b)
        if (b.vy < -250 and y_antes > RAMPA_ENTRADA_Y >= b.y
                and RAMPA_X0 < b.x < RAMPA_X1):
            self._entrar_rampa(b)
            return True
        if self.ninho_espera <= 0 and math.hypot(b.x - NINHO[0], b.y - NINHO[1]) < R_NINHO:
            if math.hypot(b.vx, b.vy) < 1300:
                self._entrar_ninho(b)
                return True
        if b.y > DRENO_Y:
            self._drenar(b)
            return True
        return False

    def _colidir_segmentos(self, b):
        x, y = b.x, b.y
        for seg in SEGMENTOS:
            if x < seg[9] or x > seg[10] or y < seg[11] or y > seg[12]:
                continue
            ax, ay, bx, by, r, tipo, dx, dy, l2 = seg[:9]
            t = ((x - ax) * dx + (y - ay) * dy) / l2
            t = 0.0 if t < 0 else (1.0 if t > 1 else t)
            cx, cy = ax + dx * t, ay + dy * t
            ox, oy = x - cx, y - cy
            d2 = ox * ox + oy * oy
            minimo = RAIO + r
            if d2 >= minimo * minimo:
                continue
            d = math.sqrt(d2)
            if d < 1e-6:
                n = math.sqrt(l2)
                nx, ny = -dy / n, dx / n
            else:
                nx, ny = ox / d, oy / d
            x = cx + nx * minimo
            y = cy + ny * minimo
            vn = b.vx * nx + b.vy * ny
            if vn < 0:
                e = QUIQUE_PAREDE if vn < -60 else 0.0
                b.vx -= (1 + e) * vn * nx
                b.vy -= (1 + e) * vn * ny
                if tipo == "sling" and vn < -80:
                    b.vx += nx * CHUTE_SLING
                    b.vy += ny * CHUTE_SLING
                    lado = 0 if ax < CENTRO_X else 1
                    self.sling_flash[lado] = 0.15
                    self._pontuar(PTS_SLING, (x, y - 20), (255, 190, 120), 10, bonus=5)
                    self._som("mola", 0.5)
                    self.particulas.explodir((cx, cy), [(255, 150, 70), AMARELO], 5, 160, 0.3, (2, 4))
                elif vn < -500:
                    self._som("bater", min(0.5, -vn / 2500), 0.08)
        b.x, b.y = x, y

    def _colidir_panelas(self, b):
        for i, (px, py) in enumerate(PANELAS):
            dx, dy = b.x - px, b.y - py
            minimo = RAIO + R_PANELA
            d2 = dx * dx + dy * dy
            if d2 >= minimo * minimo:
                continue
            d = math.sqrt(d2) or 1.0
            nx, ny = (dx / d, dy / d) if d2 > 1e-9 else (0.0, -1.0)
            b.x = px + nx * minimo
            b.y = py + ny * minimo
            vn = b.vx * nx + b.vy * ny
            if vn < 0:
                b.vx -= 2 * vn * nx
                b.vy -= 2 * vn * ny
            b.vx += nx * CHUTE_PANELA
            b.vy += ny * CHUTE_PANELA
            saida = b.vx * nx + b.vy * ny
            if saida < SAIDA_PANELA:
                b.vx += (SAIDA_PANELA - saida) * nx
                b.vy += (SAIDA_PANELA - saida) * ny
            if self.panela_flash[i] < 0.08:
                self._bateu_panela(i, (px + nx * R_PANELA, py + ny * R_PANELA))
            self.panela_flash[i] = 0.16
            self.panela_treme[i] = 0.3

    def _bateu_panela(self, i, ponto):
        px, py = PANELAS[i]
        self._pontuar(PTS_PANELA, (px, py - 40), AMARELO, 12, bonus=10)
        self._som("boing", 0.55, 0.05)
        self.tremer(0.05)
        cor = CORES_PANELA[i]
        self.particulas.explodir(ponto, [cor, ui.clarear(cor, 80), BRANCO, AMARELO], 10, 260, 0.4,
                                 (2, 5), 200)

    def _colidir_alvos(self, b):
        for i, (ax, ay) in enumerate(ALVOS):
            dx, dy = b.x - ax, b.y - ay
            minimo = RAIO + R_ALVO
            d2 = dx * dx + dy * dy
            if d2 >= minimo * minimo:
                continue
            d = math.sqrt(d2)
            nx, ny = (dx / d, dy / d) if d > 1e-6 else (0.0, 1.0)
            b.x = ax + nx * minimo
            b.y = ay + ny * minimo
            vn = b.vx * nx + b.vy * ny
            if vn < 0:
                e = QUIQUE_ALVO if vn < -60 else 0.0
                b.vx -= (1 + e) * vn * nx
                b.vy -= (1 + e) * vn * ny
                if vn < -120 and self.alvo_flash[i] <= 0:
                    self._acertou_alvo(i)

    def _acertou_alvo(self, i):
        ax, ay = ALVOS[i]
        self.alvo_flash[i] = 0.25
        if self.alvos_piscar > 0:
            self._som("bater", 0.4)
            return
        if not self.alvos[i]:
            self.alvos[i] = True
            self._pontuar(PTS_ALVO, (ax, ay - 30), (255, 240, 120), 12, bonus=50)
            self._som("acerto", 0.6)
            self.particulas.explodir((ax, ay), [(250, 222, 40), (120, 200, 60), BRANCO], 12, 220, 0.5,
                                     (2, 5))
        else:
            self._pontuar(PTS_ALVO // 10, (ax, ay - 30), BRANCO, 10)
            self._som("bater", 0.5)
        if all(self.alvos):
            self.mult = min(MULT_MAX, self.mult + 1)
            self._pontuar(PTS_ALVOS_TODOS, (CENTRO_X, 450), AMARELO, 16, bonus=200)
            self.alvos_piscar = 1.2
            self._banner(f"MULTIPLICADOR ×{self.mult}!", AMARELO, 1.6, 20)
            self._som("conquista", 0.8, 0.3)
            self.tremer(0.2)
            for ax, ay in ALVOS:
                self.particulas.explodir((ax, ay), [(250, 222, 40), BRANCO, (255, 150, 60)], 14, 300, 0.7)

    def _colidir_flipper(self, b, f):
        ax, ay = f.px, f.py
        tx, ty = f.ponta()
        dx, dy = tx - ax, ty - ay
        l2 = dx * dx + dy * dy
        t = ((b.x - ax) * dx + (b.y - ay) * dy) / l2
        t = 0.0 if t < 0 else (1.0 if t > 1 else t)
        cx, cy = ax + dx * t, ay + dy * t
        r = FLIPPER_R_PIVO + (FLIPPER_R_PONTA - FLIPPER_R_PIVO) * t
        ox, oy = b.x - cx, b.y - cy
        d2 = ox * ox + oy * oy
        minimo = RAIO + r
        if d2 >= minimo * minimo:
            return
        d = math.sqrt(d2)
        if d < 1e-6:
            n = math.sqrt(l2)
            nx, ny = dy / n * f.lado, -dx / n * f.lado
            if ny > 0:
                nx, ny = -nx, -ny
        else:
            nx, ny = ox / d, oy / d
        b.x = cx + nx * minimo
        b.y = cy + ny * minimo
        # Velocidade da superfície do flipper no ponto de contato
        px, py = cx - ax, cy - ay
        svx, svy = -f.w * py, f.w * px
        rvx, rvy = b.vx - svx, b.vy - svy
        vn = rvx * nx + rvy * ny
        if vn < 0:
            e = QUIQUE_FLIPPER if vn < -60 else 0.0
            rvx -= (1 + e) * vn * nx
            rvy -= (1 + e) * vn * ny
            b.vx, b.vy = rvx + svx, rvy + svy
            if vn < -500:
                self._som("bater", min(0.5, -vn / 3000), 0.1)

    def _colidir_mola(self, b):
        if b.x <= DIVISORIA_X:
            return
        topo = self._topo_mola()
        if b.y + RAIO > topo:
            b.y = topo - RAIO
            if b.vy > 0:
                b.vy = -b.vy * 0.25 if b.vy > 120 else 0.0
            b.vx = 0.0
            b.x += (MOLA_X - b.x) * 0.2

    def _prender_na_mesa(self, b):
        """Rede de segurança: a bola nunca sai da caixa da mesa."""
        if b.x < MESA_ESQ + RAIO:
            b.x, b.vx = MESA_ESQ + RAIO, abs(b.vx) * 0.4
        elif b.x > MESA_DIR - RAIO:
            b.x, b.vx = MESA_DIR - RAIO, -abs(b.vx) * 0.4
        if b.y < MESA_TOPO + RAIO:
            b.y, b.vy = MESA_TOPO + RAIO, abs(b.vy) * 0.4

    # ---------------- Sensores ----------------

    def _rollover(self, b):
        for k in range(len(LETRAS)):
            if POSTES_X[k] < b.x < POSTES_X[k + 1]:
                cx = (POSTES_X[k] + POSTES_X[k + 1]) // 2
                if self.luzes_piscar > 0 or self.luzes[k]:
                    self._pontuar(PTS_ROLLOVER_ACESO, (cx, LINHA_ROLLOVER + 30), BRANCO, 8)
                    self._som("tic", 0.5)
                    return
                self.luzes[k] = True
                self._pontuar(PTS_ROLLOVER, (cx, LINHA_ROLLOVER + 30), (150, 255, 170), 10, bonus=50)
                self._som("ponto", 0.5)
                self.particulas.explodir((cx, LINHA_ROLLOVER + 24), [(150, 255, 170), BRANCO], 8, 160, 0.4,
                                         (2, 4))
                if all(self.luzes):
                    self._pontuar(PTS_LIMAO, (CENTRO_X, 170), AMARELO, 16, bonus=500)
                    self.luzes_piscar = 1.6
                    self._banner("LIMÃO COMPLETO!", (180, 255, 120), 1.6, 20)
                    self._som("levelup", 0.8, 0.3)
                    self.tremer(0.15)
                return

    def _entrar_rampa(self, b):
        b.modo = "rampa"
        b.tempo_modo = 0.0
        b.rampa_pts = [(b.x, b.y)] + RAMPA_PTS[1:]
        b.rampa_acum = _comprimentos(b.rampa_pts)
        b.rampa_d = 0.0
        combo = self.tempo - self.ultima_rampa < 8.0
        self.ultima_rampa = self.tempo
        pts = PTS_RAMPA * (2 if combo else 1)
        self._pontuar(pts, (706, 260), (150, 220, 255), 14, bonus=300)
        self._banner("COMBO DE RAMPA!" if combo else "RAMPA!", (150, 220, 255), 1.2, 20)
        self._som("revelar", 0.7, 0.2)
        self.particulas.explodir((b.x, b.y), [(150, 220, 255), BRANCO], 12, 220, 0.5, (2, 5))

    def _atualizar_rampa(self, b, dt):
        b.rampa_d += VEL_RAMPA * dt
        (x, y), (dx, dy) = _ponto_no_caminho(b.rampa_pts, b.rampa_acum, b.rampa_d)
        b.x, b.y = x, y
        b.ang = (b.ang - dx * 900 * dt) % 360
        b.rastro.insert(0, (b.x, b.y))
        del b.rastro[5:]
        if b.rampa_d >= b.rampa_acum[-1]:
            b.modo = "livre"
            b.x, b.y = RAMPA_PTS[-1]
            b.vx, b.vy = 0.0, 260.0
            b.rastro = []
            self._som("boing", 0.4)

    def _entrar_ninho(self, b):
        b.modo = "ninho"
        b.tempo_modo = 0.0
        b.vx = b.vy = 0.0
        b.rastro = []
        self._pontuar(PTS_NINHO, (NINHO[0], NINHO[1] - 40), (255, 210, 150), 14, bonus=150)
        self._banner("NINHO!", (255, 210, 150), 1.1, 20)
        self._som("comer", 0.7, 0.2)
        self.particulas.explodir(NINHO, [(150, 100, 55), (255, 220, 150), BRANCO], 14, 200, 0.5, (2, 5))

    def _atualizar_ninho(self, b, dt):
        b.tempo_modo += dt
        b.x += (NINHO[0] - b.x) * min(1.0, dt * 14)
        b.y += (NINHO[1] - b.y) * min(1.0, dt * 14)
        b.ang = math.sin(b.tempo_modo * 30) * 12 % 360
        if b.tempo_modo >= TEMPO_NINHO:
            a = math.radians(random.uniform(15, 35))
            vel = random.uniform(650, 760)
            b.x, b.y = NINHO
            b.vx, b.vy = math.cos(a) * vel, math.sin(a) * vel
            b.modo = "livre"
            self.ninho_espera = 0.8
            self._som("mola", 0.8, 0.1)
            self.tremer(0.12)
            self.particulas.explodir(NINHO, [(255, 220, 150), BRANCO, AMARELO], 16, 280, 0.5, (2, 5))

    def _drenar(self, b):
        x = max(PIVO_ESQ[0], min(PIVO_DIR[0], b.x))
        # SALVA-OVO: caiu logo depois de lançar, volta para a mola
        if self.salva > 0 and not self.salva_usada:
            self.salva_usada = True
            self.salva = 0.0
            self.bola = Bola()
            self.saiu_canal = False
            self._banner("SALVA-OVO!", (120, 255, 170), 1.4, 20)
            self._som("vencer", 0.5, 0.5)
            self.particulas.explodir((x, ALTURA - 20), [(120, 255, 170), BRANCO], 16, 260, 0.6)
            return

        from core.jogador import Jogador
        cor = Jogador.cor_do_ovo(self.jogador.ovo)
        for _ in range(8):
            self.cacos.append([x, ALTURA - 24, random.uniform(-180, 180), random.uniform(-560, -320),
                               random.uniform(0, 360), 1.1, cor])
        self.particulas.explodir((x, ALTURA - 20), [(255, 240, 150), (255, 200, 60), BRANCO], 18, 240, 0.6)
        self._som("erro", 0.8, 0.3)
        self.tremer(0.3)

        bonus = self.bonus_bola * self.mult
        self.pontos += bonus
        self.pontos_bola += bonus
        self.melhor_bola = max(self.melhor_bola, self.pontos_bola)
        if bonus:
            self._banner(f"BÔNUS {self.formatar(self.bonus_bola)} ×{self.mult}", AMARELO, TEMPO_DRENO, 16)
        else:
            self._banner("CRACK!", (255, 150, 120), TEMPO_DRENO, 24)
        self.bola = None
        self.drenou = TEMPO_DRENO

    def _proxima_bola(self):
        self.drenou = 0.0
        if self.bola_n >= self.total_bolas:
            self.terminar(linhas=[f"PONTOS: {self.formatar(self.pontos)}",
                                  f"MELHOR BOLA: {self.formatar(self.melhor_bola)}"])
            return
        self.bola_n += 1
        self._nova_bola()
        self._banner(f"BOLA {self.bola_n}", BRANCO, 1.2, 20)

    # --------------------------------------------------------
    # DESENHO
    # --------------------------------------------------------

    def _ovo_girado(self, ang):
        passo = int((ang % 360) / 10) % 36
        s = self._giros.get(passo)
        if s is None:
            s = pygame.transform.rotate(self._ovo_base, passo * 10)
            self._giros[passo] = s
        return s

    def desenhar_jogo(self, tela):
        tela.blit(self.fundo(self.jogador), (0, 0))
        t = self.tempo

        self._desenhar_luzes(tela, t)

        # Estilingues piscando
        for lado, tri in enumerate((SLING_ESQ, SLING_DIR)):
            if self.sling_flash[lado] > 0:
                pygame.draw.polygon(tela, (255, 240, 180), tri)
                pygame.draw.line(tela, BRANCO, tri[0], tri[2], 5)

        # Ninho com o ovo dentro brilha
        b = self.bola
        if b is not None and b.modo == "ninho":
            raio = R_NINHO + 10 + int(abs(math.sin(t * 12)) * 6)
            tela.blit(_circulo_alpha(raio, (255, 220, 120), 90), (NINHO[0] - raio - 1, NINHO[1] - raio - 1))

        # Alvos-limão
        for i, (ax, ay) in enumerate(ALVOS):
            aceso = self.alvos[i]
            if self.alvos_piscar > 0:
                aceso = int(t * 10) % 2 == 0
            if aceso:
                tela.blit(_circulo_alpha(R_ALVO + 9, (255, 240, 100), 70), (ax - R_ALVO - 10, ay - R_ALVO - 10))
            sup = _limao_alvo(aceso)
            dy = -3 if self.alvo_flash[i] > 0 else 0
            tela.blit(sup, sup.get_rect(center=(ax, ay + dy)))

        # Panelas (tremem quando batem)
        for i, (px, py) in enumerate(PANELAS):
            tr = self.panela_treme[i]
            ox = math.sin(t * 70 + i) * 4 * tr / 0.3 if tr > 0 else 0
            oy = math.cos(t * 55 + i) * 3 * tr / 0.3 if tr > 0 else 0
            if self.panela_flash[i] > 0:
                r = R_PANELA + 16
                tela.blit(_circulo_alpha(r, (255, 240, 180), 110), (px - r - 1, py - r - 1))
            sup = _panela_sup(i, self.panela_flash[i] > 0)
            tela.blit(sup, sup.get_rect(center=(round(px + ox), round(py + oy))))

        self._desenhar_mola(tela)
        for f in self.flippers:
            self._desenhar_flipper(tela, f)

        # SALVA-OVO aceso entre os flippers
        if self.salva > 0 and not self.salva_usada and (self.salva > 2 or int(t * 8) % 2 == 0):
            ui.desenhar_texto(tela, "SALVA-OVO", (CENTRO_X, 700), 8, (120, 255, 170), "center")

        # Bola embaixo da rampa, rampa, bola em cima da rampa
        if b is not None and b.modo != "rampa":
            self._desenhar_bola(tela, b)
        rampa, pos = _rampa_sup()
        tela.blit(rampa, pos)
        if b is not None and b.modo == "rampa":
            self._desenhar_bola(tela, b, em_cima=True)

        for x, y, vx, vy, ang, vida, cor in self.cacos:
            pts = [(x + math.cos(math.radians(ang + k * 120)) * 9,
                    y + math.sin(math.radians(ang + k * 120)) * 6) for k in range(3)]
            pygame.draw.polygon(tela, cor, pts)
            pygame.draw.polygon(tela, ui.escurecer(cor, 80), pts, 1)

        self.particulas.desenhar(tela)
        self.textos.desenhar(tela)
        self._desenhar_banner(tela)

        # Dica da mola
        if (self.estado == "jogando" and b is not None and self._na_mola(b)
                and self.carga == 0 and int(t * 2) % 2 == 0):
            ui.desenhar_texto(tela, "SEGURE ESPAÇO!", (MOLA_X - 60, 610), 8, AMARELO, "center")

    def _desenhar_luzes(self, tela, t):
        for k, letra in enumerate(LETRAS):
            cx = (POSTES_X[k] + POSTES_X[k + 1]) // 2
            aceso = self.luzes[k]
            if self.luzes_piscar > 0:
                aceso = int(t * 10) % 2 == 0
            c = (cx, 138)
            if aceso:
                tela.blit(_circulo_alpha(16, (150, 255, 170), 80), (c[0] - 17, c[1] - 17))
                pygame.draw.circle(tela, (120, 230, 140), c, 11)
                cor = (20, 60, 30)
            else:
                pygame.draw.circle(tela, (40, 50, 90), c, 11)
                cor = (110, 120, 170)
            pygame.draw.circle(tela, (200, 210, 240), c, 11, 2)
            ui.desenhar_texto(tela, letra, (c[0] + 1, c[1] + 1), 10, cor, "center", sombra=False)

    def _desenhar_flipper(self, tela, f):
        ax, ay = f.px, f.py
        tx, ty = f.ponta()
        dx, dy = (tx - ax) / FLIPPER_COMP, (ty - ay) / FLIPPER_COMP
        px, py = -dy, dx
        for cor, extra, desl in (((40, 20, 30), 3, 3), ((230, 60, 80), 2, 0), ((255, 214, 64), 0, 0)):
            r0, r1 = FLIPPER_R_PIVO + extra, FLIPPER_R_PONTA + extra
            pts = [(ax + px * r0, ay + py * r0 + desl), (tx + px * r1, ty + py * r1 + desl),
                   (tx - px * r1, ty - py * r1 + desl), (ax - px * r0, ay - py * r0 + desl)]
            pygame.draw.polygon(tela, cor, pts)
            pygame.draw.circle(tela, cor, (round(ax), round(ay + desl)), r0)
            pygame.draw.circle(tela, cor, (round(tx), round(ty + desl)), r1)
        pygame.draw.line(tela, (255, 245, 180), (ax + px * 4, ay + py * 4 - 3),
                         (tx + px * 2, ty + py * 2 - 2), 2)
        pygame.draw.circle(tela, (120, 90, 30), (round(ax), round(ay)), 4)

    def _desenhar_mola(self, tela):
        puxada = self.carga * MOLA_CURSO
        if self.mola_volta > 0:
            puxada = -self.mola_volta * 8
        topo = MOLA_Y + puxada
        x0 = int(MOLA_X - 15)
        # Molinha em zigue-zague
        pts = []
        n = 8
        for k in range(n + 1):
            y = topo + 8 + (ALTURA - topo - 8) * k / n
            pts.append((MOLA_X + (8 if k % 2 else -8), y))
        pygame.draw.lines(tela, (170, 175, 200), False, pts, 3)
        pygame.draw.rect(tela, (220, 60, 80), (x0, topo, 30, 8), border_radius=3)
        pygame.draw.rect(tela, (255, 170, 180), (x0 + 3, topo + 1, 24, 2))
        # Barra de força
        if self.carga > 0:
            barra = pygame.Rect(MESA_DIR + 8, 480, 10, 200)
            pygame.draw.rect(tela, (30, 20, 50), barra, border_radius=4)
            cheio = int(barra.h * self.carga)
            cor = ui.misturar((120, 255, 120), (255, 80, 60), self.carga)
            pygame.draw.rect(tela, cor, (barra.x, barra.bottom - cheio, barra.w, cheio), border_radius=4)
            pygame.draw.rect(tela, BRANCO, barra, 2, border_radius=4)

    def _desenhar_bola(self, tela, b, em_cima=False):
        # Rastro quando está rápido
        if b.modo == "rampa" or math.hypot(b.vx, b.vy) > 700:
            cor = self.jogador.cor
            for k, (x, y) in enumerate(b.rastro[1:5]):
                r = max(3, RAIO - 2 - k * 2)
                tela.blit(_circulo_alpha(r, cor, 90 - k * 20), (x - r - 1, y - r - 1))
        desl = 10 if em_cima else 4
        tela.blit(_circulo_alpha(RAIO, (0, 0, 20), 80), (b.x - RAIO - 1 + desl, b.y - RAIO - 1 + desl))
        sup = self._ovo_girado(b.ang)
        tela.blit(sup, sup.get_rect(center=(round(b.x), round(b.y))))

    def _desenhar_banner(self, tela):
        if not self.banner or self.estado != "jogando":
            return
        texto, cor, resta, total, tam = self.banner
        entrada = min(1.0, (total - resta) * 6)
        tam_atual = tam if entrada >= 1 else max(8, int(tam * (0.5 + 0.5 * entrada)))
        sup = ui.texto(texto, tam_atual, cor)
        r = sup.get_rect(center=(CENTRO_X, 485))
        ui.painel(tela, r.inflate(30, 22), (24, 18, 48), cor, 12, 3, sombra=False)
        tela.blit(sup, r)

    def desenhar_hud(self, tela):
        cx = 112
        cor_v = AMARELO
        tam = ui.tamanho_que_cabe(self.formatar(self.pontos), 180, (16, 14, 12, 10))
        ui.desenhar_texto(tela, self.formatar(self.pontos), (cx, 124), tam, cor_v, "midtop")
        rec = self.recorde()
        ui.desenhar_texto(tela, self.formatar(rec) if rec is not None else "-", (cx, 180), 12,
                          (180, 200, 255), "midtop")

        # Bolas que faltam (ovinhos)
        ui.desenhar_texto(tela, f"{self.bola_n} / {self.total_bolas}", (cx, 232), 12, BRANCO, "midtop")
        esp = 30
        x0 = cx - (self.total_bolas - 1) * esp / 2
        for k in range(self.total_bolas):
            pos = (x0 + k * esp, 268)
            usada = k < self.bola_n - 1 or (k == self.bola_n - 1 and self.bola is None)
            if usada:
                pygame.draw.circle(tela, (50, 40, 80), (round(pos[0]), round(pos[1])), 8)
            else:
                self.jogador.desenhar(tela, pos, 22)

        # Multiplicador
        cor_m = [(200, 200, 220), AMARELO, (255, 180, 60), (255, 120, 80), (255, 90, 200)][self.mult - 1]
        tam_m = 28 if self.mult > 1 else 24
        ui.desenhar_texto(tela, f"×{self.mult}", (cx, 318), tam_m, cor_m, "midtop")

        ui.desenhar_texto(tela, self.formatar(self.bonus_bola), (cx, 398), 12, (255, 220, 160), "midtop")

        # L-I-M-A-O
        for k, letra in enumerate(LETRAS):
            c = (cx - 64 + k * 32, 476)
            aceso = self.luzes[k] or (self.luzes_piscar > 0 and int(self.tempo * 10) % 2 == 0)
            pygame.draw.circle(tela, (120, 230, 140) if aceso else (40, 50, 90), c, 12)
            pygame.draw.circle(tela, (200, 210, 240), c, 12, 2)
            ui.desenhar_texto(tela, letra, (c[0] + 1, c[1] + 1), 10,
                              (20, 60, 30) if aceso else (110, 120, 170), "center", sombra=False)

        # Limões acesos
        for k in range(len(ALVOS)):
            sup = _limao_alvo(self.alvos[k])
            tela.blit(sup, sup.get_rect(center=(cx - 60 + k * 40, 562)))

        if self.salva > 0 and not self.salva_usada:
            ui.desenhar_texto(tela, "SALVA-OVO", (cx, 610), 10, (120, 255, 170), "midtop")
            barra = pygame.Rect(cx - 60, 630, 120, 6)
            pygame.draw.rect(tela, (40, 50, 70), barra, border_radius=3)
            pygame.draw.rect(tela, (120, 255, 170), (barra.x, barra.y, int(barra.w * self.salva / TEMPO_SALVA),
                                                     barra.h), border_radius=3)

        # Avatar pulando no painel direito
        pulo = abs(math.sin(self.tempo * 3)) * 10
        self.jogador.desenhar(tela, (912, 270 - pulo), 90)
        dicas = ["4 LIMÕES = ×MULT", "SUBA A RAMPA!", "ACHE O NINHO", "ACENDA L-I-M-A-O",
                 "O FLIPPER TROCA AS LUZES"]
        dica = dicas[int(self.tempo / 3) % len(dicas)]
        tam = ui.tamanho_que_cabe(dica, 180, (10, 8))
        ui.desenhar_texto(tela, dica, (912, 356), tam, (255, 220, 160), "midtop")
