import math
import random

import pygame

from settings import *
from core import ui
from core.idioma import t
from jogos.base import TEMPO_CONTAGEM
from jogos.base_multi import MiniJogoMulti, TECLAS_MOVER, TECLAS_ACAO, CORES_JOGADOR

# ============================================================
# CORRIDA NA RUA (2 JOGADORES)
# ============================================================
# Corrida vista de cima pela RUA DOS OVOS: um circuito fechado
# com curvas, calçadas, casinhas e árvores. Cada jogador pilota um
# kart com o seu ovo em cima. A tela mostra a pista inteira.
#
#   J1: WASD dirige • ESPAÇO turbo • F/Q/E/G usa o item
#   J2: SETAS dirige • ENTER turbo • SHIFT/CTRL DIREITO/. usa o item
#
# Caixas "?" dão CASCA DE BANANA (fica para trás), LIMÃO-FOGUETE
# (voa pela pista atrás do outro) ou TURBO. O turbo da barra
# recarrega com o tempo. Checkpoints invisíveis impedem atalhos.

# ------------------------------------------------------------
# PISTA
# ------------------------------------------------------------

# Pontos de controle do traçado (spline fechada). O 0 é a largada.
CONTROLE = [
    (440, 646), (700, 648), (870, 632), (945, 560), (935, 455),
    (860, 392), (735, 404), (648, 350), (672, 262), (800, 238),
    (905, 205), (900, 142), (760, 132), (560, 140), (425, 175),
    (392, 262), (430, 345), (365, 420), (240, 400), (160, 312),
    (95, 360), (88, 500), (140, 610), (260, 645),
]

ESPACO = 6.0            # distância entre os pontos da linha central
MEIA = 42               # meia largura do asfalto
CALCADA = 15            # largura da calçada (de cada lado)
N_CP = 12               # checkpoints (o 0 é a linha de chegada)
JANELA_CP = 14          # quantos pontos depois do checkpoint ainda valem

# ------------------------------------------------------------
# KART
# ------------------------------------------------------------
R_CARRO = 16
ALT_OVO = 24
VEL_MAX = 300
VEL_CALCADA = 205
VEL_GRAMA = 125
VEL_TURBO = 440
VEL_RE = 110
ACEL = 420
ACEL_TURBO = 900
FREIO = 760
ATRITO_SOLTO = 0.9      # desacelera sem acelerar
GIRO = 3.3              # rad/s em velocidade
ADERENCIA = 9.0
ADERENCIA_DERRAPA = 3.2
TEMPO_TURBO = 1.3
CARGA_TURBO = 5.5       # segundos para encher a barra
TEMPO_RODAR = 1.0       # rodopio na banana / limão
SUB_PASSO = 1 / 120

# Itens
N_BANANAS_MAX = 8
VEL_FOGUETE = 700
VIDA_FOGUETE = 3.0
TEMPO_CAIXA = 3.5
TEMPO_ROLETA = 0.7
ITENS = ["banana", "limao", "turbo"]

METAS = [3, 5]
PASSOS_GIRO = 72

_cache = {}


# ============================================================
# GEOMETRIA DA PISTA (calculada uma vez)
# ============================================================

def _catmull(pts, passos):
    n = len(pts)
    out = []
    for i in range(n):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
        for k in range(passos):
            t = k / passos
            t2, t3 = t * t, t * t * t
            out.append(tuple(
                0.5 * (2 * p1[c] + (-p0[c] + p2[c]) * t
                       + (2 * p0[c] - 5 * p1[c] + 4 * p2[c] - p3[c]) * t2
                       + (-p0[c] + 3 * p1[c] - 3 * p2[c] + p3[c]) * t3)
                for c in (0, 1)))
    return out


def _gerar_pista():
    denso = _catmull(CONTROLE, 30)
    denso.append(denso[0])
    pts = [denso[0]]
    falta = ESPACO
    for a, b in zip(denso, denso[1:]):
        seg = math.dist(a, b)
        pos = 0.0
        while seg - pos >= falta:
            pos += falta
            f = pos / seg
            pts.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f))
            falta = ESPACO
        falta -= seg - pos
    if math.dist(pts[-1], pts[0]) < ESPACO * 0.5:
        pts.pop()
    n = len(pts)
    tang, norm = [], []
    for i in range(n):
        ax, ay = pts[i - 1]
        bx, by = pts[(i + 1) % n]
        dx, dy = bx - ax, by - ay
        d = math.hypot(dx, dy) or 1.0
        tang.append((dx / d, dy / d))
        norm.append((-dy / d, dx / d))
    return pts, tang, norm


PISTA, TANG, NORM = _gerar_pista()
N = len(PISTA)
CP_IDX = [k * N // N_CP for k in range(N_CP)]
PX = [p[0] for p in PISTA]
PY = [p[1] for p in PISTA]


def mais_proximo(x, y):
    """(índice, distância lateral com sinal, distância) do ponto da pista mais perto."""
    melhor, bd = 0, 1e18
    for i in range(0, N, 5):
        dx, dy = PX[i] - x, PY[i] - y
        d = dx * dx + dy * dy
        if d < bd:
            bd, melhor = d, i
    base = melhor
    for k in range(-4, 5):
        i = (base + k) % N
        dx, dy = PX[i] - x, PY[i] - y
        d = dx * dx + dy * dy
        if d < bd:
            bd, melhor = d, i
    nx, ny = NORM[melhor]
    lat = (x - PX[melhor]) * nx + (y - PY[melhor]) * ny
    return melhor, lat, math.sqrt(bd)


def ponto_pista(s, lat=0.0):
    """Ponto na pista no índice fracionário s, deslocado `lat` para o lado."""
    s %= N
    i = int(s)
    f = s - i
    j = (i + 1) % N
    x = PX[i] + (PX[j] - PX[i]) * f
    y = PY[i] + (PY[j] - PY[i]) * f
    nx, ny = NORM[i]
    return x + nx * lat, y + ny * lat


def _mascara_pista(extra):
    """Máscara com a faixa da pista engordada `extra` px (para espalhar o cenário)."""
    sup = pygame.Surface((LARGURA, ALTURA))
    sup.fill((0, 0, 0))
    r = MEIA + CALCADA + extra
    for i in range(0, N, 2):
        pygame.draw.circle(sup, (255, 255, 255), (round(PX[i]), round(PY[i])), r)
    sup.set_colorkey((0, 0, 0))
    return pygame.mask.from_surface(sup)


CORES_PAREDE = [(250, 225, 170), (200, 225, 250), (250, 200, 210), (210, 240, 200),
                (240, 240, 235), (255, 215, 150)]
CORES_TELHADO = [(200, 80, 60), (90, 110, 170), (120, 150, 80), (160, 90, 140),
                 (210, 130, 60), (100, 100, 110)]


def cenario():
    """Casas (retângulos sólidos) e árvores (círculos sólidos) ao redor da pista."""
    c = _cache.get("cenario")
    if c is not None:
        return c
    rnd = random.Random(2024)
    livre_casa = _mascara_pista(22)
    livre_arv = _mascara_pista(10)
    ocupado = []
    casas, arvores = [], []

    def cabe(rect, mascara):
        if rect.left < 8 or rect.right > LARGURA - 8 or rect.top < 84 or rect.bottom > ALTURA - 6:
            return False
        for px in (rect.left, rect.centerx, rect.right - 1):
            for py in (rect.top, rect.centery, rect.bottom - 1):
                if mascara.get_at((px, py)):
                    return False
        return not any(rect.colliderect(o) for o in ocupado)

    # Casas primeiro (viradas para a rua mais próxima)
    for _ in range(900):
        w, h = rnd.choice(((64, 50), (56, 46), (72, 54), (50, 58), (46, 60)))
        r = pygame.Rect(rnd.randrange(8, LARGURA - w - 8), rnd.randrange(84, ALTURA - h - 6), w, h)
        if not cabe(r, livre_casa):
            continue
        idx, _, _ = mais_proximo(*r.center)
        casas.append({
            "rect": r,
            "parede": rnd.choice(CORES_PAREDE),
            "telhado": rnd.choice(CORES_TELHADO),
            "rua": (PX[idx], PY[idx]),
            "chamine": rnd.random() < 0.6,
        })
        ocupado.append(r.inflate(26, 26))
        if len(casas) >= 16:
            break

    # Árvores nos buracos que sobraram
    for _ in range(1400):
        raio = rnd.choice((13, 15, 17, 19))
        x, y = rnd.randrange(12, LARGURA - 12), rnd.randrange(90, ALTURA - 10)
        r = pygame.Rect(0, 0, raio * 2, raio * 2)
        r.center = (x, y)
        if not cabe(r, livre_arv):
            continue
        arvores.append((x, y, raio))
        ocupado.append(r.inflate(8, 8))
        if len(arvores) >= 34:
            break

    c = (casas, arvores)
    _cache["cenario"] = c
    return c


# ============================================================
# SPRITES (tudo em cache)
# ============================================================

def _sprite_kart(cor):
    """Kart visto de cima, apontando para a direita (+x)."""
    w, h = 44, 30
    sup = pygame.Surface((w, h), pygame.SRCALPHA)
    pneu = (30, 30, 36)
    for x in (5, w - 15):
        pygame.draw.rect(sup, pneu, (x, 0, 11, 7), border_radius=2)
        pygame.draw.rect(sup, pneu, (x, h - 7, 11, 7), border_radius=2)
    escuro = ui.escurecer(cor, 70)
    pygame.draw.rect(sup, escuro, (1, 5, w - 2, h - 10), border_radius=8)
    pygame.draw.rect(sup, cor, (2, 5, w - 5, h - 12), border_radius=8)
    # Bico e para-choque
    pygame.draw.polygon(sup, ui.clarear(cor, 40), [(w - 12, 9), (w - 2, 12), (w - 2, h - 12), (w - 12, h - 9)])
    pygame.draw.rect(sup, (60, 60, 70), (w - 4, 8, 4, h - 16), border_radius=2)
    # Faixa e aerofólio
    pygame.draw.rect(sup, (255, 255, 255), (8, h // 2 - 2, w - 18, 4))
    pygame.draw.rect(sup, (50, 50, 60), (0, 4, 5, h - 8), border_radius=2)
    pygame.draw.rect(sup, escuro, (2, 5, w - 5, h - 12), 1, border_radius=8)
    return sup


def _kart_girado(i, cor, passo):
    chave = ("kart", i, passo)
    s = _cache.get(chave)
    if s is None:
        base = _cache.get(("kart_base", i))
        if base is None:
            base = _sprite_kart(cor)
            _cache[("kart_base", i)] = base
        s = pygame.transform.rotate(base, -passo * 360 / PASSOS_GIRO)
        _cache[chave] = s
    return s


def _sombra(raio_x, raio_y, alpha=70):
    chave = ("sombra", raio_x, raio_y, alpha)
    s = _cache.get(chave)
    if s is None:
        s = pygame.Surface((raio_x * 2, raio_y * 2), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (0, 0, 0, alpha), s.get_rect())
        _cache[chave] = s
    return s


def _circulo_alpha(raio, cor, alpha):
    chave = ("c", raio, cor, alpha)
    s = _cache.get(chave)
    if s is None:
        s = pygame.Surface((raio * 2 + 2, raio * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*cor, alpha), (raio + 1, raio + 1), raio)
        _cache[chave] = s
    return s


def _sprite_caixa(tam=26):
    chave = ("caixa", tam)
    s = _cache.get(chave)
    if s is None:
        s = pygame.Surface((tam, tam), pygame.SRCALPHA)
        r = s.get_rect()
        pygame.draw.rect(s, (200, 120, 20), r, border_radius=6)
        pygame.draw.rect(s, (255, 200, 60), r.inflate(-4, -4), border_radius=5)
        pygame.draw.rect(s, (255, 235, 150), (4, 4, tam - 8, 5), border_radius=2)
        pygame.draw.rect(s, (140, 80, 10), r, 2, border_radius=6)
        t = ui.texto("?", 14, (120, 60, 10), sombra=False)
        s.blit(t, t.get_rect(center=(tam // 2 + 1, tam // 2 + 1)))
        _cache[chave] = s
    return s


def _sprite_banana(esc=1.0):
    chave = ("banana", esc)
    s = _cache.get(chave)
    if s is None:
        tam = round(30 * esc)
        s = pygame.Surface((tam, tam), pygame.SRCALPHA)
        c = tam / 2
        # Casca aberta: 3 pontas amarelas saindo do meio
        for k in range(3):
            a = -math.pi / 2 + k * math.tau / 3
            ponta = (c + math.cos(a) * c * 0.95, c + math.sin(a) * c * 0.95)
            lado1 = (c + math.cos(a + 0.9) * c * 0.35, c + math.sin(a + 0.9) * c * 0.35)
            lado2 = (c + math.cos(a - 0.9) * c * 0.35, c + math.sin(a - 0.9) * c * 0.35)
            pygame.draw.polygon(s, (250, 215, 50), [lado1, ponta, lado2])
            pygame.draw.polygon(s, (170, 130, 20), [lado1, ponta, lado2], 1)
        pygame.draw.circle(s, (240, 200, 60), (c, c), c * 0.38)
        pygame.draw.circle(s, (110, 80, 30), (c, c), max(2, c * 0.15))
        _cache[chave] = s
    return s


def _sprite_turbo(tam=26):
    chave = ("turbo", tam)
    s = _cache.get(chave)
    if s is None:
        s = pygame.Surface((tam, tam), pygame.SRCALPHA)
        k = tam / 26
        raio = [(15, 1), (4, 14), (12, 14), (9, 25), (22, 10), (14, 10), (19, 1)]
        pts = [(x * k, y * k) for x, y in raio]
        pygame.draw.polygon(s, (255, 140, 30), pts)
        pygame.draw.polygon(s, (255, 230, 90), [(x * 0.8 + 3 * k, y * 0.8 + 2.5 * k) for x, y in pts])
        pygame.draw.polygon(s, (150, 60, 10), pts, 2)
        _cache[chave] = s
    return s


def _limao_girado(raio, angulo):
    passo = int((angulo % 360) / 15) % 24
    chave = ("limao", raio, passo)
    s = _cache.get(chave)
    if s is None:
        s = pygame.transform.rotate(ui.limao_sup(raio), passo * 15)
        _cache[chave] = s
    return s


def icone_item(item, tam=26):
    if item == "banana":
        return _sprite_banana(tam / 30)
    if item == "limao":
        return ui.limao_sup(round(tam * 0.42))
    return _sprite_turbo(tam)


# ============================================================
# PEÇAS
# ============================================================

class Kart:

    def __init__(self, i, x, y, ang):
        self.i = i
        self.x, self.y = x, y
        self.vx = self.vy = 0.0
        self.ang = ang
        self.idx, self.lat, self.dist = mais_proximo(x, y)
        self.chao = "rua"
        self.voltas = -1             # a 1ª passagem pela linha começa a volta 1
        self.prox = N_CP             # próximo checkpoint esperado (N_CP = linha de chegada)
        self.progresso = 0.0
        self.turbo = 0.0             # tempo de turbo ativo
        self.carga = 0.6             # barra de turbo (0..1)
        self.rodar = 0.0             # rodopio (sem controle)
        self.giro_visual = 0.0
        self.item = None
        self.roleta = 0.0
        self.imune = 0.0
        self.contramao = 0.0
        self.pulou = 0.0             # tempo longe do trecho certo (pulou um checkpoint)
        self.tempo_volta = 0.0
        self.melhor_volta = None
        self.chegou = None
        self.espera_som = 0.0
        self.derrapando = False
        self.rodas = None            # posição anterior das rodas de trás (marcas)
        self.entrada = (False, False, 0)

    @property
    def vel(self):
        return math.hypot(self.vx, self.vy)

    def frente(self):
        return math.cos(self.ang), math.sin(self.ang)


class Foguete:

    def __init__(self, dono, s, lat, alvo):
        self.dono = dono
        self.s = float(s)
        self.lat = lat
        self.alvo = alvo
        self.vida = VIDA_FOGUETE
        self.angulo = 0.0
        self.x, self.y = ponto_pista(s, lat)


# ============================================================
# JOGO
# ============================================================

class CorridaRua(MiniJogoMulti):

    ID = "corrida_rua"
    TITULO = "CORRIDA NA RUA"
    TITULO_CURTO = "CORRIDA"
    DESCRICAO = "Kart na Rua dos Ovos! Pegue caixas, jogue bananas e limões e cruze a linha primeiro."
    COR = (230, 90, 60)
    INSTRUCOES = [
        "Complete as voltas na RUA DOS OVOS antes do amigo! Grama e calçada deixam lento.",
        "Caixa ? = BANANA (fica atrás), LIMÃO-FOGUETE (persegue o outro) ou TURBO.",
        "J1: WASD dirige • ESPAÇO turbo • F item",
        "J2: SETAS dirige • ENTER turbo • SHIFT DIREITO item",
    ]
    OPCOES = ["3 VOLTAS", "5 VOLTAS"]
    CONTROLES_J1 = "WASD + ESPAÇO + F"
    CONTROLES_J2 = "SETAS + ENTER + SHIFT"
    CONTAGEM = True

    MOEDAS_PARTIDA = 8
    MOEDAS_VITORIA_J1 = 6
    MOEDAS_MAX = 22

    # --------------------------------------------------------
    # CENÁRIO: a Rua dos Ovos vista de cima
    # --------------------------------------------------------

    @classmethod
    def criar_fundo(cls, jogador):
        sup = pygame.Surface((LARGURA, ALTURA))
        sup.fill((120, 190, 95))
        rnd = random.Random(7)
        # Listras de grama cortada
        for x in range(-ALTURA, LARGURA, 56):
            pygame.draw.polygon(sup, (128, 198, 102), [(x, 0), (x + 28, 0), (x + 28 + ALTURA, ALTURA),
                                                         (x + ALTURA, ALTURA)])
        for _ in range(260):
            x, y = rnd.randrange(LARGURA), rnd.randrange(ALTURA)
            pygame.draw.line(sup, (95, 160, 75), (x, y), (x - 2, y - 5), 2)
            pygame.draw.line(sup, (95, 160, 75), (x, y), (x + 2, y - 5), 2)
        for _ in range(50):
            x, y = rnd.randrange(LARGURA), rnd.randrange(ALTURA)
            pygame.draw.circle(sup, rnd.choice([(255, 255, 255), (255, 230, 90), (255, 140, 180)]),
                               (x, y), 2)

        casas, arvores = cenario()

        # Caminhos das casas até a calçada
        for c in casas:
            r = c["rect"]
            rx, ry = c["rua"]
            pygame.draw.line(sup, (215, 205, 185), r.center, (rx, ry), 14)

        # Calçada (meio-fio claro) e asfalto
        for i in range(N):
            pygame.draw.circle(sup, (175, 175, 180), (round(PX[i]), round(PY[i])), MEIA + CALCADA)
        # Ladrilhos da calçada
        for i in range(0, N, 3):
            for lado in (-1, 1):
                x, y = ponto_pista(i, lado * (MEIA + CALCADA * 0.5))
                pygame.draw.circle(sup, (195, 195, 200), (round(x), round(y)), 3)
        for i in range(N):
            pygame.draw.circle(sup, (70, 72, 82), (round(PX[i]), round(PY[i])), MEIA + 3)
        # Meio-fio vermelho e branco nas curvas fechadas
        for i in range(N):
            t0 = TANG[i - 3]
            t1 = TANG[(i + 3) % N]
            curva = t0[0] * t1[1] - t0[1] * t1[0]
            if abs(curva) > 0.12:
                lado = -1 if curva > 0 else 1   # lado de dentro da curva
                x, y = ponto_pista(i, lado * (MEIA + 2))
                cor = (230, 60, 50) if (i // 3) % 2 == 0 else (250, 250, 250)
                pygame.draw.circle(sup, cor, (round(x), round(y)), 5)
        for i in range(N):
            pygame.draw.circle(sup, (60, 62, 72), (round(PX[i]), round(PY[i])), MEIA - 1)
        # Textura do asfalto
        for _ in range(900):
            i = rnd.randrange(N)
            x, y = ponto_pista(i, rnd.uniform(-MEIA + 4, MEIA - 4))
            pygame.draw.circle(sup, rnd.choice([(68, 70, 80), (54, 56, 64)]), (round(x), round(y)),
                               rnd.choice((1, 1, 2)))
        # Faixa amarela tracejada no meio
        for i in range(0, N, 1):
            if (i // 4) % 2 == 0:
                a = PISTA[i]
                b = PISTA[(i + 1) % N]
                pygame.draw.line(sup, (255, 214, 64), a, b, 3)

        # Linha de chegada quadriculada
        nx, ny = NORM[0]
        tx, ty = TANG[0]
        x0, y0 = PISTA[0]
        q = 7
        linhas = int(MEIA * 2 / q)
        for k in range(linhas):
            for col in range(3):
                lat = -MEIA + k * q
                ax = x0 + nx * lat + tx * (col - 1.5) * q
                ay = y0 + ny * lat + ty * (col - 1.5) * q
                pts = [(ax, ay), (ax + nx * q, ay + ny * q),
                       (ax + nx * q + tx * q, ay + ny * q + ty * q), (ax + tx * q, ay + ty * q)]
                cor = (250, 250, 250) if (k + col) % 2 == 0 else (25, 25, 30)
                pygame.draw.polygon(sup, cor, pts)
        # Marcas do grid de largada
        for lat in (-20, 20):
            for back in (6, 11):
                x, y = ponto_pista(N - back, lat)
                pygame.draw.circle(sup, (235, 235, 240), (round(x), round(y)), 3)

        # Árvores (sombra primeiro)
        for x, y, r in arvores:
            pygame.draw.circle(sup, (80, 130, 65), (x + 5, y + 6), r)
        for c in casas:
            r = c["rect"]
            pygame.draw.rect(sup, (80, 130, 65), r.move(6, 7), border_radius=4)

        # Casas vistas de cima (telhado de duas águas)
        for c in casas:
            cls._desenhar_casa(sup, c)
        for x, y, r in arvores:
            pygame.draw.circle(sup, (55, 135, 60), (x, y), r)
            pygame.draw.circle(sup, (75, 160, 75), (x - r // 4, y - r // 4), int(r * 0.7))
            pygame.draw.circle(sup, (105, 190, 95), (x - r // 3, y - r // 3), int(r * 0.35))

        # Plaquinha da rua
        placa = ui.texto(t("RUA DOS OVOS"), 10, (30, 40, 30), sombra=False)
        x, y = ponto_pista(N * 0.5, -(MEIA + CALCADA + 18))
        pr = placa.get_rect(center=(round(x), round(y))).inflate(14, 10)
        pr.clamp_ip(pygame.Rect(0, 84, LARGURA, ALTURA - 84))
        pygame.draw.rect(sup, (40, 110, 60), pr.move(0, 2), border_radius=4)
        pygame.draw.rect(sup, (230, 245, 230), pr, border_radius=4)
        pygame.draw.rect(sup, (40, 110, 60), pr, 2, border_radius=4)
        sup.blit(placa, placa.get_rect(center=pr.center))
        return sup

    @staticmethod
    def _desenhar_casa(sup, c):
        r = c["rect"]
        telhado = c["telhado"]
        claro = ui.clarear(telhado, 35)
        escuro = ui.escurecer(telhado, 30)
        # Cumeeira ao longo do lado mais comprido
        if r.w >= r.h:
            meio = r.centery
            pygame.draw.rect(sup, claro, (r.x, r.y, r.w, meio - r.y), border_top_left_radius=4,
                             border_top_right_radius=4)
            pygame.draw.rect(sup, escuro, (r.x, meio, r.w, r.bottom - meio), border_bottom_left_radius=4,
                             border_bottom_right_radius=4)
            for yy in range(r.y + 6, r.bottom - 2, 7):
                pygame.draw.line(sup, telhado, (r.x + 3, yy), (r.right - 4, yy), 1)
            pygame.draw.line(sup, ui.escurecer(telhado, 60), (r.x + 2, meio), (r.right - 3, meio), 3)
        else:
            meio = r.centerx
            pygame.draw.rect(sup, claro, (r.x, r.y, meio - r.x, r.h), border_top_left_radius=4,
                             border_bottom_left_radius=4)
            pygame.draw.rect(sup, escuro, (meio, r.y, r.right - meio, r.h), border_top_right_radius=4,
                             border_bottom_right_radius=4)
            for xx in range(r.x + 6, r.right - 2, 7):
                pygame.draw.line(sup, telhado, (xx, r.y + 3), (xx, r.bottom - 4), 1)
            pygame.draw.line(sup, ui.escurecer(telhado, 60), (meio, r.y + 2), (meio, r.bottom - 3), 3)
        pygame.draw.rect(sup, ui.escurecer(telhado, 70), r, 2, border_radius=4)
        if c["chamine"]:
            ch = pygame.Rect(0, 0, 9, 9)
            ch.center = (r.x + r.w * 0.72, r.y + r.h * 0.3)
            pygame.draw.rect(sup, (150, 80, 60), ch)
            pygame.draw.rect(sup, (60, 40, 30), ch.inflate(-4, -4))
        # Porta virada para a rua (um toldo com a cor da parede)
        rx, ry = c["rua"]
        dx, dy = rx - r.centerx, ry - r.centery
        if abs(dx) * r.h > abs(dy) * r.w:
            px = r.right if dx > 0 else r.left
            porta = pygame.Rect(0, 0, 6, 16)
            porta.center = (px, r.centery)
        else:
            py = r.bottom if dy > 0 else r.top
            porta = pygame.Rect(0, 0, 16, 6)
            porta.center = (r.centerx, py)
        pygame.draw.rect(sup, c["parede"], porta, border_radius=2)
        pygame.draw.rect(sup, (60, 50, 40), porta, 1, border_radius=2)

    @classmethod
    def desenhar_icone(cls, sup, jogador):
        w, h = sup.get_size()
        k = h / 200
        for n, (x, cor) in enumerate(((0.36, CORES_JOGADOR[0]), (0.64, CORES_JOGADOR[1]))):
            kart = _sprite_kart(cor)
            kart = pygame.transform.smoothscale(kart, (round(44 * k * 1.6), round(30 * k * 1.6)))
            kart = pygame.transform.rotate(kart, 90)
            sup.blit(kart, kart.get_rect(center=(w * x, h * 0.62)))
            ap = None if n == 0 else ((jogador.ovo + 1) % 4, (jogador.cabelo + 4) % 8,
                                      (jogador.olho + 1) % 3, (jogador.boca + 2) % 6)
            jogador.desenhar(sup, (w * x, h * 0.5), h * 0.26, aparencia=ap, espelhar=(n == 1))

    # --------------------------------------------------------
    # PARTIDA
    # --------------------------------------------------------

    def __init__(self, app, menu):
        self.seguradas = set()
        super().__init__(app, menu)

    def reiniciar(self):
        self.meta = METAS[self.opcao]
        self.karts = []
        for i, lat in ((0, -20), (1, 20)):
            x, y = ponto_pista(N - 8, lat)
            tx, ty = TANG[N - 8]
            self.karts.append(Kart(i, x, y, math.atan2(ty, tx)))
        self.casas, self.arvores = cenario()
        self.caixas = []
        for base in (N * 0.17, N * 0.62):
            for lat in (-24, 0, 24):
                x, y = ponto_pista(base, lat)
                self.caixas.append([x, y, 0.0])      # x, y, tempo até voltar
        self.bananas = []                             # [x, y, dono, idade]
        self.foguetes = []
        self.fase = "corrida"
        self.tempo_fase = 0.0
        self.tempo_corrida = 0.0
        self.vencedor_corrida = None
        self.banner = None
        self._ultimo_numero = None
        self._verde = 0.0
        self._chao = self.fundo(self.jogador).copy()     # recebe as marcas de pneu
        self._ovos = [self.jogador.avatar(ALT_OVO, self.aparencia(i)).copy() for i in (0, 1)]
        self._mini = [self.jogador.avatar(28, self.aparencia(i)).copy() for i in (0, 1)]
        self._ovos_girados = {}
        self._hud_cache = [None, None]

    def _banner(self, texto, cor, tempo, tamanho=24):
        self.banner = [texto, cor, tempo, tamanho, tempo]

    # --------------------------------------------------------
    # TECLADO
    # --------------------------------------------------------

    def evento(self, e):
        if e.type == pygame.KEYDOWN:
            self.seguradas.add(e.key)
        elif e.type == pygame.KEYUP:
            self.seguradas.discard(e.key)
        elif e.type == pygame.WINDOWFOCUSLOST:
            self.seguradas.clear()
        super().evento(e)

    def evento_jogo(self, e):
        if e.type != pygame.KEYDOWN or self.fase != "corrida":
            return
        for i in (0, 1):
            if e.key == TECLAS_ACAO[i][0]:
                self.usar_turbo(i)
            elif e.key in TECLAS_ACAO[i][1:]:
                self.usar_item(i)

    def _controles(self):
        """Por jogador: (acelera, freia, giro -1/0/1)."""
        apertadas = pygame.key.get_pressed()
        seg = self.seguradas
        res = []
        for i in (0, 1):
            m = TECLAS_MOVER[i]

            def s(nome):
                k = m[nome]
                return apertadas[k] or k in seg

            res.append((s("cima"), s("baixo"), (1 if s("dir") else 0) - (1 if s("esq") else 0)))
        return res

    # --------------------------------------------------------
    # TURBO E ITENS
    # --------------------------------------------------------

    def usar_turbo(self, i):
        k = self.karts[i]
        if k.carga < 1.0 or k.rodar > 0 or k.chegou is not None:
            if k.carga < 1.0 and k.turbo <= 0:
                self.som("erro", 0.3)
            return
        k.carga = 0.0
        self._dar_turbo(k)

    def _dar_turbo(self, k):
        k.turbo = TEMPO_TURBO
        fx, fy = k.frente()
        k.vx += fx * 120
        k.vy += fy * 120
        self.som("asa", 0.8)
        self.textos.adicionar(t("TURBO!"), (k.x, k.y - 34), (255, 170, 60), 12)

    def usar_item(self, i):
        k = self.karts[i]
        if k.item is None or k.roleta > 0 or k.rodar > 0 or k.chegou is not None:
            return
        item, k.item = k.item, None
        fx, fy = k.frente()
        if item == "banana":
            if len(self.bananas) >= N_BANANAS_MAX:
                self.bananas.pop(0)
            self.bananas.append([k.x - fx * 30, k.y - fy * 30, i, 0.0])
            self.som("pulo", 0.6)
        elif item == "limao":
            outro = self.karts[1 - i]
            s = k.idx + 3
            self.foguetes.append(Foguete(i, s, max(-MEIA, min(MEIA, k.lat)), outro))
            self.som("explosao", 0.35)
            self.particulas.explodir((k.x + fx * 20, k.y + fy * 20), [(255, 220, 80), BRANCO], 8, 160,
                                     0.3, (2, 4), 0)
        else:
            self._dar_turbo(k)

    def _sortear_item(self, k):
        outro = self.karts[1 - k.i]
        atras = k.progresso < outro.progresso - 20
        pesos = [25, 40, 35] if atras else [50, 30, 20]
        return random.choices(ITENS, pesos)[0]

    def _rodopiar(self, k, motivo):
        if k.rodar > 0 or k.imune > 0:
            return
        k.rodar = TEMPO_RODAR
        k.imune = TEMPO_RODAR + 0.8
        k.turbo = 0.0
        k.vx *= 0.35
        k.vy *= 0.35
        self.tremer(0.2)
        self.som("boing", 0.9)
        self.textos.adicionar(motivo, (k.x, k.y - 34), (255, 230, 90), 12)
        self.particulas.explodir((k.x, k.y), [(250, 222, 40), BRANCO, (255, 160, 60)], 12, 200, 0.5,
                                 (2, 5), 0)

    # --------------------------------------------------------
    # LÓGICA
    # --------------------------------------------------------

    def atualizar(self, dt):
        # Semáforo: um "tic" em cada luz e o apito no VAI!
        if self.estado == "contagem":
            passo = TEMPO_CONTAGEM / 3
            numero = min(3, int(self.tempo_estado / passo))
            if numero != self._ultimo_numero:
                self._ultimo_numero = numero
                self.som("tic", 0.8)
        antes = self.estado
        super().atualizar(dt)
        if antes == "contagem" and self.estado == "jogando":
            self._verde = 1.0
            self.som("bandeira", 0.8)
        self._verde = max(0.0, self._verde - dt)

    def atualizar_jogo(self, dt):
        self.tempo_fase += dt
        if self.banner:
            self.banner[2] -= dt
            if self.banner[2] <= 0:
                self.banner = None
        if self.fase == "corrida":
            self.tempo_corrida += dt

        controles = self._controles()
        for k, c in zip(self.karts, controles):
            if k.chegou is not None or k.rodar > 0:
                c = (False, False, 0)          # rodando ou já chegou: só desliza
            k.entrada = c

        passos = max(1, math.ceil(dt / SUB_PASSO))
        h = dt / passos
        for _ in range(passos):
            for k in self.karts:
                self._fisica_kart(k, h)
            self._colidir_karts(*self.karts, h)

        for k in self.karts:
            self._depois_do_passo(k, dt)
        self._atualizar_itens(dt)
        self._atualizar_posicoes(dt)

        if self.fase == "chegada" and self.tempo_fase >= 1.8:
            self._acabar()

    def _fisica_kart(self, k, h):
        acel, freia, giro = k.entrada
        fx, fy = math.cos(k.ang), math.sin(k.ang)
        rx, ry = -fy, fx
        vl = k.vx * fx + k.vy * fy          # velocidade para a frente
        vt = k.vx * rx + k.vy * ry          # velocidade de lado (derrapagem)

        chao = k.chao
        vmax = VEL_MAX if chao == "rua" else (VEL_CALCADA if chao == "calcada" else VEL_GRAMA)
        if k.turbo > 0:
            vmax = VEL_TURBO if chao == "rua" else max(vmax, VEL_TURBO * 0.7)

        if k.turbo > 0:
            vl += ACEL_TURBO * h
        elif acel:
            vl += (ACEL if vl >= 0 else FREIO) * h
        if freia and k.turbo <= 0:
            if vl > 0:
                vl = max(0.0, vl - FREIO * h) if not acel else vl
            else:
                vl = max(-VEL_RE, vl - ACEL * 0.6 * h)
        if not acel and not freia and k.turbo <= 0:
            vl *= math.exp(-(ATRITO_SOLTO * 2.5 if k.chegou is not None else ATRITO_SOLTO) * h)
        if vl > vmax:
            vl -= (vl - vmax) * min(1.0, 5.0 * h)

        # Virar (proporcional à velocidade; ao contrário na ré)
        if k.rodar > 0:
            k.ang += 11.0 * h
        elif giro:
            fator = max(-1.0, min(1.0, vl / 110))
            if abs(vl) > 200:
                fator *= 1.0 - 0.25 * (abs(vl) - 200) / 240
            k.ang += giro * GIRO * fator * h

        # Aderência: em alta velocidade virando, o kart escorrega
        derrapa = giro != 0 and abs(vl) > 230
        ader = ADERENCIA_DERRAPA if derrapa else ADERENCIA
        if chao == "grama":
            ader *= 0.7
        vt *= math.exp(-ader * h)

        fx, fy = math.cos(k.ang), math.sin(k.ang)
        rx, ry = -fy, fx
        k.vx = fx * vl + rx * vt
        k.vy = fy * vl + ry * vt
        k.x += k.vx * h
        k.y += k.vy * h
        k.derrapando = abs(vt) > 70
        self._colidir_cenario(k)

    def _colidir_cenario(self, k):
        r = R_CARRO
        bateu = 0.0
        # Bordas da tela (ninguém sai do mapa)
        if k.x < r + 2:
            k.x, bateu, k.vx = r + 2, max(bateu, -k.vx), abs(k.vx) * 0.3
        elif k.x > LARGURA - r - 2:
            k.x, bateu, k.vx = LARGURA - r - 2, max(bateu, k.vx), -abs(k.vx) * 0.3
        if k.y < 78 + r:
            k.y, bateu, k.vy = 78 + r, max(bateu, -k.vy), abs(k.vy) * 0.3
        elif k.y > ALTURA - r - 2:
            k.y, bateu, k.vy = ALTURA - r - 2, max(bateu, k.vy), -abs(k.vy) * 0.3

        # Só testa o cenário quando está fora do asfalto (casas/árvores ficam longe)
        if k.dist > MEIA + CALCADA:
            for c in self.casas:
                rect = c["rect"]
                if not rect.inflate(r * 2, r * 2).collidepoint(k.x, k.y):
                    continue
                px = max(rect.left, min(k.x, rect.right))
                py = max(rect.top, min(k.y, rect.bottom))
                dx, dy = k.x - px, k.y - py
                d = math.hypot(dx, dy)
                if d >= r:
                    continue
                if d < 1e-6:
                    # Centro dentro da casa: sai pelo lado mais perto
                    opcoes = [(k.x - rect.left, -1, 0), (rect.right - k.x, 1, 0),
                              (k.y - rect.top, 0, -1), (rect.bottom - k.y, 0, 1)]
                    _, nx, ny = min(opcoes)
                    k.x = px + nx * (r + 1) if nx else k.x
                    k.y = py + ny * (r + 1) if ny else k.y
                    if nx:
                        k.x = (rect.left - r - 1) if nx < 0 else (rect.right + r + 1)
                    if ny:
                        k.y = (rect.top - r - 1) if ny < 0 else (rect.bottom + r + 1)
                else:
                    nx, ny = dx / d, dy / d
                    k.x, k.y = px + nx * r, py + ny * r
                vn = k.vx * nx + k.vy * ny
                if vn < 0:
                    bateu = max(bateu, -vn)
                    k.vx -= 1.4 * vn * nx
                    k.vy -= 1.4 * vn * ny
            for ax, ay, ar in self.arvores:
                dx, dy = k.x - ax, k.y - ay
                minimo = r + ar - 3
                if abs(dx) > minimo or abs(dy) > minimo:
                    continue
                d = math.hypot(dx, dy)
                if d >= minimo:
                    continue
                if d < 1e-6:
                    dx, dy, d = 1.0, 0.0, 1.0
                nx, ny = dx / d, dy / d
                k.x, k.y = ax + nx * minimo, ay + ny * minimo
                vn = k.vx * nx + k.vy * ny
                if vn < 0:
                    bateu = max(bateu, -vn)
                    k.vx -= 1.4 * vn * nx
                    k.vy -= 1.4 * vn * ny

        if bateu > 90 and k.espera_som <= 0:
            k.espera_som = 0.25
            self.som("bater", min(0.8, 0.2 + bateu / 400))
            if bateu > 180:
                self.tremer(0.12)
                self.particulas.explodir((k.x, k.y), [(200, 200, 200), (140, 110, 80)], 6, 140, 0.35,
                                         (2, 4), 0)

    def _colidir_karts(self, a, b, h):
        dx, dy = b.x - a.x, b.y - a.y
        d = math.hypot(dx, dy)
        minimo = R_CARRO * 2
        if d >= minimo:
            return
        if d < 1e-6:
            dx, dy, d = 1.0, 0.0, 1.0
        nx, ny = dx / d, dy / d
        sobra = (minimo - d) / 2
        a.x -= nx * sobra
        a.y -= ny * sobra
        b.x += nx * sobra
        b.y += ny * sobra
        vn = (b.vx - a.vx) * nx + (b.vy - a.vy) * ny
        if vn < 0:
            j = -(1 + 0.6) * vn / 2 + 30        # empurrão extra
            a.vx -= j * nx
            a.vy -= j * ny
            b.vx += j * nx
            b.vy += j * ny
            if -vn > 80 and self.estado == "jogando" and a.espera_som <= 0:
                a.espera_som = b.espera_som = 0.2
                self.som("bater", min(1.0, 0.3 + -vn / 400))
                self.tremer(min(0.3, 0.08 + -vn / 1500))
                meio = ((a.x + b.x) / 2, (a.y + b.y) / 2)
                self.particulas.explodir(meio, [(255, 230, 120), BRANCO, (255, 160, 60)], 10, 220, 0.3,
                                         (2, 4), 0)
        for k in (a, b):
            self._colidir_cenario(k)

    def _depois_do_passo(self, k, dt):
        k.idx, k.lat, k.dist = mais_proximo(k.x, k.y)
        k.chao = "rua" if k.dist <= MEIA else ("calcada" if k.dist <= MEIA + CALCADA else "grama")
        k.espera_som = max(0.0, k.espera_som - dt)
        k.imune = max(0.0, k.imune - dt)
        if k.rodar > 0:
            k.rodar -= dt
            k.giro_visual += dt * 18
        else:
            k.giro_visual = 0.0
        if k.roleta > 0:
            k.roleta -= dt
            if k.roleta <= 0:
                self.som("revelar", 0.5)

        # Turbo: gasta e recarrega (quem está atrás recarrega um pouco mais rápido)
        if k.turbo > 0:
            k.turbo -= dt
            if random.random() < 0.8:
                fx, fy = k.frente()
                self.particulas.explodir((k.x - fx * 22, k.y - fy * 22),
                                         [(255, 150, 40), (255, 220, 90), (150, 150, 160)], 1, 60, 0.4,
                                         (3, 6), -40)
        elif k.chegou is None and self.fase == "corrida":
            outro = self.karts[1 - k.i]
            ritmo = 1.25 if k.progresso < outro.progresso - 30 else 1.0
            antes = k.carga
            k.carga = min(1.0, k.carga + dt / CARGA_TURBO * ritmo)
            if antes < 1.0 <= k.carga:
                self.som("tic", 0.5)

        # Poeira e marcas de pneu
        fx, fy = k.frente()
        rx, ry = -fy, fx
        vel = k.vel
        rodas = [(k.x - fx * 13 + rx * s * 10, k.y - fy * 13 + ry * s * 10) for s in (-1, 1)]
        marca = (k.derrapando and vel > 120) or (k.entrada[1] and vel > 180 and k.turbo <= 0 and
                                                 k.vx * fx + k.vy * fy > 0)
        if marca and k.chao != "grama" and k.rodas is not None:
            for a, b in zip(k.rodas, rodas):
                pygame.draw.line(self._chao, (46, 47, 55), a, b, 3)
        k.rodas = rodas
        if (k.derrapando and vel > 120) or (k.chao == "grama" and vel > 80):
            if random.random() < 0.5:
                cores = [(170, 150, 110), (200, 185, 150)] if k.chao == "grama" else \
                        [(200, 200, 205), (170, 170, 180)]
                p = random.choice(rodas)
                self.particulas.explodir(p, cores, 1, 50, 0.45, (3, 6), -20)

        # Contramão
        tx, ty = TANG[k.idx]
        if k.vx * tx + k.vy * ty < -60 and k.rodar <= 0:
            k.contramao += dt
        else:
            k.contramao = 0.0

        # Checkpoints e voltas
        if k.chegou is None:
            k.tempo_volta += dt
            self._checar_checkpoint(k)

    def _checar_checkpoint(self, k):
        if k.dist > MEIA + CALCADA + 30:
            return
        alvo = 0 if k.prox >= N_CP else CP_IDX[k.prox]
        if (k.idx - alvo) % N >= JANELA_CP:
            return
        if k.prox < N_CP:
            k.prox += 1
            return
        # Linha de chegada
        k.prox = 1
        k.voltas += 1
        if k.voltas <= 0:
            k.tempo_volta = 0.0
            return
        if k.melhor_volta is None or k.tempo_volta < k.melhor_volta:
            k.melhor_volta = k.tempo_volta
        k.tempo_volta = 0.0
        if k.voltas >= self.meta:
            self._cruzou_chegada(k)
        elif k.voltas == self.meta - 1:
            self._banner(t("{nome}: ÚLTIMA VOLTA!", nome=self.nome(k.i)[:10].upper()), CORES_JOGADOR[k.i], 1.6, 16)
            self.som("ponto", 0.8)
        else:
            self.som("moeda", 0.5)
            self.textos.adicionar(t("VOLTA {n}", n=k.voltas + 1), (k.x, k.y - 36), CORES_JOGADOR[k.i], 12)

    def _cruzou_chegada(self, k):
        k.chegou = self.tempo_corrida
        if self.fase != "corrida":
            return
        self.fase = "chegada"
        self.tempo_fase = 0.0
        self.vencedor_corrida = k.i
        self._banner(t("BANDEIRADA!"), AMARELO, 1.8, 32)
        self.som("ponto")
        self.som("explosao", 0.4)
        self.tremer(0.25)
        x, y = PISTA[0]
        for n in range(3):
            self.particulas.explodir((x, y + (n - 1) * 30),
                                     [self.cor(k.i), CORES_JOGADOR[k.i], BRANCO, AMARELO],
                                     18, 380, 1.1, (3, 6), 300)

    def _atualizar_itens(self, dt):
        # Caixas
        for cx in self.caixas:
            if cx[2] > 0:
                cx[2] = max(0.0, cx[2] - dt)
                continue
            for k in self.karts:
                if abs(k.x - cx[0]) < 24 and abs(k.y - cx[1]) < 24:
                    cx[2] = TEMPO_CAIXA
                    self.particulas.explodir((cx[0], cx[1]), [(255, 200, 60), (255, 240, 170), (200, 120, 20)],
                                             10, 200, 0.4, (2, 5), 200)
                    if k.item is None and k.chegou is None:
                        k.item = self._sortear_item(k)
                        k.roleta = TEMPO_ROLETA
                        self.som("moeda", 0.6)
                    else:
                        self.som("clique", 0.5)
                    break

        # Bananas
        for b in self.bananas[:]:
            b[3] += dt
            for k in self.karts:
                if k.i == b[2] and b[3] < 0.6:
                    continue          # quem jogou tem um tempinho para sair de perto
                if abs(k.x - b[0]) < 20 and abs(k.y - b[1]) < 20:
                    self._rodopiar(k, t("ESCORREGOU!"))
                    if b in self.bananas:
                        self.bananas.remove(b)
                    break

        # Limões-foguete: voam pela pista, perseguindo o outro
        passo = VEL_FOGUETE / ESPACO
        for f in self.foguetes[:]:
            f.vida -= dt
            f.s += passo * dt
            f.angulo += dt * 900
            alvo = f.alvo
            frente = (alvo.idx - f.s) % N
            if frente < 60:
                # Mira no lado em que o outro está
                f.lat += (max(-MEIA, min(MEIA, alvo.lat)) - f.lat) * min(1.0, 6 * dt)
            else:
                f.lat *= math.exp(-1.5 * dt)
            f.x, f.y = ponto_pista(f.s, f.lat)
            if random.random() < 0.7:
                self.particulas.explodir((f.x, f.y), [(255, 140, 30), (255, 220, 60), (180, 180, 180)],
                                         1, 40, 0.3, (2, 4), -30)
            acertou = False
            for k in self.karts:
                if k.i == f.dono and f.vida > VIDA_FOGUETE - 0.4:
                    continue
                if abs(k.x - f.x) < 24 and abs(k.y - f.y) < 24:
                    self._rodopiar(k, t("LIMONADA!"))
                    self.som("explosao", 0.5)
                    acertou = True
                    break
            if not acertou:
                for b in self.bananas:
                    if abs(b[0] - f.x) < 18 and abs(b[1] - f.y) < 18:
                        self.bananas.remove(b)
                        self.som("bater", 0.5)
                        acertou = True
                        break
            if acertou or f.vida <= 0:
                self.particulas.explodir((f.x, f.y), [(250, 222, 40), (255, 140, 30), BRANCO], 12, 220,
                                         0.45, (2, 5), 0)
                self.foguetes.remove(f)

    def _atualizar_posicoes(self, dt=0.0):
        for k in self.karts:
            if k.prox >= N_CP:
                ini, fim = CP_IDX[N_CP - 1], N
            else:
                ini, fim = CP_IDX[k.prox - 1], CP_IDX[k.prox]
            rel = (k.idx - ini) % N
            tam = fim - ini
            if tam + JANELA_CP < rel < N // 2 and k.chegou is None:
                k.pulou += dt        # passou do checkpoint sem pegar (atalho / saiu da pista)
            else:
                k.pulou = 0.0
            if rel > tam + JANELA_CP:
                rel = 0              # fora do trecho certo (atalho / contramão)
            k.progresso = k.voltas * N + ini + min(rel, tam)
            if k.chegou is not None:
                k.progresso = 1e9 - k.chegou

    def posicao(self, i):
        a, b = self.karts[i], self.karts[1 - i]
        if a.progresso == b.progresso:
            return 1 if i == 0 else 2
        return 1 if a.progresso > b.progresso else 2

    def _acabar(self):
        v = self.vencedor_corrida
        k = self.karts[v]
        linhas = [t("VOLTAS: {n}   TEMPO: {tempo}", n=self.meta, tempo=self._fmt(k.chegou))]
        melhores = [(kk.melhor_volta, kk.i) for kk in self.karts if kk.melhor_volta is not None]
        if melhores:
            tv, quem = min(melhores)
            linhas.append(t("VOLTA MAIS RÁPIDA: J{j} {s} s", j=quem + 1, s=f"{tv:.1f}".replace(".", ",")))
        self.terminar_multi(v, linhas)

    @staticmethod
    def _fmt(seg):
        seg = max(0.0, seg or 0.0)
        return f"{int(seg // 60)}:{int(seg % 60):02d}"

    # --------------------------------------------------------
    # DESENHO
    # --------------------------------------------------------

    def desenhar_jogo(self, tela):
        tela.blit(self._chao, (0, 0))
        t = self.tempo

        # Caixas (flutuando), bananas
        caixa = _sprite_caixa()
        for n, cx in enumerate(self.caixas):
            if cx[2] > 0:
                if cx[2] < 0.6:
                    pygame.draw.circle(tela, (255, 230, 120), (round(cx[0]), round(cx[1])), 4)
                continue
            dy = math.sin(t * 4 + n) * 2
            tela.blit(_sombra(12, 5), (cx[0] - 12, cx[1] + 8))
            tela.blit(caixa, caixa.get_rect(center=(round(cx[0]), round(cx[1] - 3 + dy))))
        ban = _sprite_banana()
        for b in self.bananas:
            tela.blit(ban, ban.get_rect(center=(round(b[0]), round(b[1]))))

        # Karts
        for k in sorted(self.karts, key=lambda o: o.y):
            self._desenhar_kart(tela, k, t)

        # Foguetes
        for f in self.foguetes:
            tela.blit(_sombra(10, 5), (f.x - 10, f.y + 6))
            s = _limao_girado(10, f.angulo)
            tela.blit(s, s.get_rect(center=(round(f.x), round(f.y - 4))))

        self.particulas.desenhar(tela)
        self.textos.desenhar(tela)

        # Semáforo (contagem) e luz verde no começo
        if self.estado == "contagem" or (self.estado == "jogando" and self._verde > 0):
            self._desenhar_semaforo(tela)

        self._desenhar_banner(tela)

    def _desenhar_kart(self, tela, k, tt):
        cx, cy = round(k.x), round(k.y)
        tela.blit(_sombra(22, 12), (cx - 20, cy - 6))
        ang = k.ang + k.giro_visual
        passo = round(ang / math.tau * PASSOS_GIRO) % PASSOS_GIRO
        kart = _kart_girado(k.i, CORES_JOGADOR[k.i], passo)
        tela.blit(kart, kart.get_rect(center=(cx, cy)))
        # Pisca quando está imune depois de rodar
        if k.imune > 0 and k.rodar <= 0 and int(tt * 12) % 2 == 0:
            return
        # Ovo em cima (sempre de pé; gira no rodopio)
        if k.rodar > 0:
            ovo = self._ovo_girado(k.i, k.giro_visual)
        else:
            ovo = self._ovos[k.i]
        pulo = abs(math.sin(tt * 14)) * 2 if k.vel > 60 and k.chao == "grama" else 0
        tela.blit(ovo, ovo.get_rect(center=(cx, round(cy - 10 - pulo))))
        # Etiqueta J1/J2 e contramão
        if k.pulou > 0.5:
            # Pulou um trecho: seta apontando para o checkpoint que faltou
            alvo = 0 if k.prox >= N_CP else CP_IDX[k.prox]
            ax, ay = PISTA[alvo]
            dx, dy = ax - k.x, ay - k.y
            d = math.hypot(dx, dy) or 1.0
            dx, dy = dx / d, dy / d
            px, py = cx + dx * 36, cy + dy * 36
            seta = [(px + dx * 14, py + dy * 14), (px - dy * 10, py + dx * 10),
                    (px + dy * 10, py - dx * 10)]
            pygame.draw.polygon(tela, (255, 120, 120), seta)
            pygame.draw.polygon(tela, (90, 20, 20), seta, 2)
            if int(tt * 4) % 2 == 0:
                ui.desenhar_texto(tela, t("VOLTE!"), (cx, cy - 44), 8, (255, 120, 120), "center")
        elif k.contramao > 0.8 and int(tt * 4) % 2 == 0:
            ui.desenhar_texto(tela, t("CONTRAMÃO!"), (cx, cy - 44), 8, (255, 120, 120), "center")
        elif self.fase == "corrida":
            o = self.karts[1 - k.i]
            if abs(o.x - k.x) > 44 or abs(o.y - k.y) > 56:
                ui.desenhar_texto(tela, f"J{k.i + 1}", (cx, cy - 38), 8, CORES_JOGADOR[k.i], "center")

    def _ovo_girado(self, i, ang):
        passo = int((math.degrees(ang) % 360) / 30) % 12
        chave = (i, passo)
        s = self._ovos_girados.get(chave)
        if s is None:
            s = pygame.transform.rotate(self._ovos[i], passo * 30)
            self._ovos_girados[chave] = s
        return s

    def _desenhar_semaforo(self, tela):
        caixa = pygame.Rect(0, 0, 170, 60)
        caixa.center = (LARGURA // 2 - 10, 300)
        pygame.draw.rect(tela, (10, 10, 14), caixa.move(4, 5), border_radius=14)
        pygame.draw.rect(tela, (30, 32, 40), caixa, border_radius=14)
        pygame.draw.rect(tela, (80, 84, 100), caixa, 3, border_radius=14)
        if self.estado == "contagem":
            passo = TEMPO_CONTAGEM / 3
            acesas = min(3, int(self.tempo_estado / passo) + 1)
            cores = [(240, 60, 50), (240, 60, 50), (255, 200, 40)]
            for n in range(3):
                c = (caixa.x + 35 + n * 50, caixa.centery)
                if n < acesas:
                    tela.blit(_circulo_alpha(22, cores[n], 90), (c[0] - 23, c[1] - 23))
                    pygame.draw.circle(tela, cores[n], c, 16)
                    pygame.draw.circle(tela, ui.clarear(cores[n], 60), (c[0] - 5, c[1] - 5), 5)
                else:
                    pygame.draw.circle(tela, (60, 60, 70), c, 16)
            ui.desenhar_texto(tela, str(3 - acesas + 1), (caixa.centerx, caixa.bottom + 30), 28,
                              AMARELO, "center")
        else:
            for n in range(3):
                c = (caixa.x + 35 + n * 50, caixa.centery)
                tela.blit(_circulo_alpha(22, (80, 240, 90), 90), (c[0] - 23, c[1] - 23))
                pygame.draw.circle(tela, (80, 240, 90), c, 16)
                pygame.draw.circle(tela, (200, 255, 200), (c[0] - 5, c[1] - 5), 5)
            ui.desenhar_texto(tela, t("VAI!"), (caixa.centerx, caixa.bottom + 30), 28, (120, 255, 130),
                              "center")

    def _desenhar_contagem(self, tela):
        pass            # o semáforo é desenhado no próprio jogo

    def _desenhar_banner(self, tela):
        if not self.banner or self.estado != "jogando":
            return
        texto, cor, resta, tam, total = self.banner
        entrada = min(1.0, (total - resta) * 6)
        tam_atual = tam if entrada >= 1 else max(12, int(tam * (0.6 + 0.4 * entrada)) // 2 * 2)
        sup = ui.texto(texto, tam_atual, cor)
        r = sup.get_rect(center=(LARGURA // 2 - 10, 300))
        ui.painel(tela, r.inflate(36, 24), (20, 24, 40), cor, 14, 3, sombra=False)
        tela.blit(sup, r)

    # --------------------------------------------------------
    # HUD
    # --------------------------------------------------------

    def desenhar_hud(self, tela):
        if not hasattr(self, "karts"):
            return
        for i in (0, 1):
            k = self.karts[i]
            caixa = pygame.Rect(0, 8, 330, 62)
            if i == 0:
                caixa.x = 12
            else:
                caixa.right = LARGURA - 76
            pos = self.posicao(i)
            volta = max(1, min(self.meta, k.voltas + 1))
            chave = (pos, volta, self.meta)
            cache = self._hud_cache[i]
            if cache is None or cache[0] != chave:
                cache = (chave, self._montar_painel(i, caixa.size, pos, volta))
                self._hud_cache[i] = cache
            tela.blit(cache[1], caixa.topleft)

            # Barra do turbo
            barra = pygame.Rect(caixa.x + 150, caixa.y + 40, 110, 12)
            pygame.draw.rect(tela, (50, 50, 70), barra, border_radius=6)
            if k.turbo > 0:
                enche, cor = k.turbo / TEMPO_TURBO, (255, 150, 40)
            else:
                enche = k.carga
                cor = (255, 220, 60) if k.carga >= 1 and int(self.tempo * 6) % 2 == 0 else \
                    ((255, 200, 60) if k.carga >= 1 else (120, 200, 255))
            if enche > 0:
                pygame.draw.rect(tela, cor, (barra.x, barra.y, max(4, int(barra.w * enche)), barra.h),
                                 border_radius=6)
            pygame.draw.rect(tela, BRANCO, barra, 1, border_radius=6)

            # Item
            slot = pygame.Rect(caixa.right - 50, caixa.y + 11, 40, 40)
            item = k.item
            if item is not None:
                if k.roleta > 0:
                    item = ITENS[int(self.tempo * 14) % 3]
                ic = icone_item(item, 28)
                tela.blit(ic, ic.get_rect(center=slot.center))

        # Tempo de corrida no meio
        texto = self._fmt(self.tempo_corrida)
        ui.desenhar_texto(tela, texto, (LARGURA // 2 - 25, 38), 14, BRANCO, "center")

    def _montar_painel(self, i, tamanho, pos, volta):
        sup = pygame.Surface(tamanho, pygame.SRCALPHA)
        c = sup.get_rect()
        ui.painel(sup, c, (20, 24, 40), CORES_JOGADOR[i], 12, 3, sombra=False)
        mini = self._mini[i]
        sup.blit(mini, mini.get_rect(center=(30, c.centery)))
        ui.desenhar_texto(sup, f"{pos}º", (62, c.centery), 24, AMARELO if pos == 1 else (200, 200, 220),
                          "midleft")
        ui.desenhar_texto(sup, self.nome(i)[:10].upper(), (150, 12), 10, CORES_JOGADOR[i], "topleft")
        ui.desenhar_texto(sup, t("VOLTA {n}/{total}", n=volta, total=self.meta), (150, 26), 8, BRANCO, "topleft")
        slot = pygame.Rect(c.right - 50, 11, 40, 40)
        pygame.draw.rect(sup, (40, 44, 64), slot, border_radius=8)
        pygame.draw.rect(sup, (150, 160, 200), slot, 2, border_radius=8)
        ui.desenhar_texto(sup, t("TURBO"), (150 + 55, 55), 6, (200, 210, 240), "center")
        return sup

    # --------------------------------------------------------
    # TELA DE INÍCIO (VS) COMPACTA
    # --------------------------------------------------------

    def _desenhar_inicio(self, tela):
        ui.veu(tela, 150)
        topo = 24
        caixa = pygame.Rect(0, topo, 780, ALTURA - topo - 24)
        caixa.centerx = LARGURA // 2
        ui.painel(tela, caixa, (28, 32, 56), self.COR, 22, 5)

        ui.desenhar_texto(tela, t(self.TITULO), (LARGURA // 2, topo + 20), 28, AMARELO, "midtop")
        ui.desenhar_texto(tela, t("2 JOGADORES"), (LARGURA // 2, topo + 58), 12,
                          (180, 200, 255), "midtop")

        y_ovos = topo + 130
        for i, x in ((0, caixa.x + 150), (1, caixa.right - 150)):
            balanco = math.sin(self.tempo * 3 + i * 1.5) * 4
            kart = _kart_girado(i, CORES_JOGADOR[i], PASSOS_GIRO * 3 // 4)
            tela.blit(kart, kart.get_rect(center=(x, y_ovos + 18)))
            self.desenhar_ovo(tela, i, (x, y_ovos + balanco - 8), 50, espelhar=(i == 1))
            ui.desenhar_texto(tela, self.nome(i), (x, y_ovos + 46), 14, CORES_JOGADOR[i], "midtop")
            ctrl = self.CONTROLES_J1 if i == 0 else self.CONTROLES_J2
            ui.desenhar_texto(tela, t(ctrl), (x, y_ovos + 68), 10, BRANCO, "midtop")
        ui.desenhar_texto(tela, "VS", (LARGURA // 2, y_ovos), 32, AMARELO, "center")

        y = y_ovos + 96
        for linha in self.INSTRUCOES:
            for sub in ui.quebrar_linhas(linha, 10, caixa.w - 50):
                ui.desenhar_texto(tela, sub, (LARGURA // 2, y), 10, BRANCO, "midtop")
                y += 16
            y += 4

        # Itens das caixas
        y += 6
        itens = (("banana", "BANANA"), ("limao", "LIMÃO"), ("turbo", "TURBO"))
        x0 = LARGURA // 2 - 250
        for n, (item, nome) in enumerate(itens):
            x = x0 + n * 180
            ic = icone_item(item, 26)
            tela.blit(ic, ic.get_rect(center=(x, y + 12)))
            ui.desenhar_texto(tela, t(nome), (x + 22, y + 12), 10, AMARELO, "midleft")

        v = self.vitorias()
        y_rec = self.menu_inicio.botoes[0].rect.y - 32

        # Prévia da pista no espaço que sobrar
        y += 34
        espaco = y_rec - 44 - y
        if espaco >= 70:
            altura = min(150, espaco)
            tamanho = (int(altura * LARGURA / ALTURA), altura)
            if getattr(self, "_previa_tam", None) != tamanho:
                self._previa = pygame.transform.smoothscale(self.fundo(self.jogador), tamanho)
                self._previa_tam = tamanho
            r = self._previa.get_rect(midtop=(LARGURA // 2, y))
            pygame.draw.rect(tela, (0, 0, 0), r.inflate(12, 12).move(0, 4), border_radius=10)
            tela.blit(self._previa, r)
            pygame.draw.rect(tela, self.COR, r.inflate(8, 8), 4, border_radius=8)

        ui.desenhar_texto(tela, t("VITÓRIAS  J1 {a} × {b} J2", a=v[0], b=v[1]), (LARGURA // 2, y_rec),
                          14, AMARELO, "midtop")
        ui.desenhar_texto(tela, t("ESCOLHA O NÚMERO DE VOLTAS"), (LARGURA // 2, y_rec - 24), 12,
                          (180, 200, 255), "midtop")
        self.menu_inicio.desenhar(tela)
