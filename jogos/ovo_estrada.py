import math
import random

import pygame

from settings import *
from core import ui
from jogos.base import MiniJogo

# ============================================================
# OVO NA ESTRADA
# ============================================================
# Pilote o "buggy-casca" (uma meia casca de ovo na cor do seu ovo,
# com rodas!) morro acima e morro abaixo. Cuide da gasolina,
# pegue as moedas da pista (cada uma vale 1 OVOEDA de verdade),
# dê cambalhotas no ar... e não capote, que o ovo racha!
#
# Física simplificada (sem corpo rígido):
#   - no chão o carro "anda sobre o trilho" do terreno: ângulo =
#     inclinação entre as duas rodas, velocidade ao longo da rampa;
#   - se o terreno cai mais rápido que a queda livre, vira projétil;
#   - no ar ←/→ giram o carro; no pouso compara o ângulo do carro
#     com o do terreno.

PASSO = 20                      # distância entre as amostras do terreno
X_INICIO = 200.0
PX_POR_METRO = 40

GRAVIDADE = 1600.0
ACELERACAO = 600.0
FREIO = 600.0
VEL_MAX = 700.0
VEL_RE = -300.0
ATRITO = 40.0                   # rolagem sem acelerar (px/s²)
INCLINACAO_MAX = 50.0           # graus
GIRO_AR = 260.0                 # graus/s (máximo)
ACEL_GIRO = 420.0               # graus/s²: pulinho curto gira pouco
GRACA_DECOLAGEM = 0.2           # s em que a roda de trás ainda pode raspar na rampa

RAIO_RODA = 18
ENTRE_EIXOS = 90                # distância entre as rodas
MEIO_EIXO = ENTRE_EIXOS / 2
ALTURA_OVO = 48

# Pontos do carro em relação ao meio do eixo (x para frente, y para baixo)
LOCAL_CASCA = (0, -22)
LOCAL_OVO = (-6, -50)
LOCAL_CABECA = (-6, -74)

COMBUSTIVEL_MAX = 100.0
GASTO_ACELERANDO = 6.0          # por segundo
GASTO_PARADO = 1.0

# Céu e cenário
CEU = (0, 190, 255)
GRAMA = (80, 200, 60)
GRAMA_BORDA = (40, 150, 40)
TERRA = (140, 100, 60)
MONTANHA = (120, 160, 220)
LARG_FAIXA = 2048

TECLAS_ACELERA = (pygame.K_RIGHT, pygame.K_d)
TECLAS_FREIA = (pygame.K_LEFT, pygame.K_a)

_camadas = {}


def _suave(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def _normalizar(ang):
    """Ângulo em graus no intervalo [-180, 180)."""
    return (ang + 180.0) % 360.0 - 180.0


# ============================================================
# TERRENO
# ============================================================

class Terreno:
    """
    Alturas amostradas a cada PASSO px, geradas sob demanda:
    soma de 3 senos + ruído suave, com a amplitude crescendo com a
    distância. Duas travas deixam tudo sempre possível:
      - inclinação máxima de 50°;
      - um "carro virtual" acelerando sem parar precisa conseguir
        subir; se a subida ia fazê-lo parar, a rampa fica mais suave.
    """

    CAP_VEL2 = 540.0 ** 2        # velocidade do carro virtual (com folga do máx 700)
    MIN_VEL2 = 280.0 ** 2
    VEL2_POUSO = 150.0 ** 2      # onde o carro pousa ele pode ter perdido quase toda a velocidade

    def __init__(self, semente):
        self.rnd = random.Random(semente)
        self.fases = [self.rnd.uniform(0, math.tau) for _ in range(3)]
        self.nos = [self.rnd.uniform(-1, 1) for _ in range(4)]
        self.rampas = []                   # (início, largura, altura) das rampas de pulo
        self.prox_rampa = 1600.0
        self.ys = [0.0]
        self.vel2 = 300.0 ** 2
        self.vel2_otim = 300.0 ** 2      # o mais rápido que o carro pode estar (p/ achar decolagens)
        self.angulos = []
        self.zona_pouso = -1.0
        self._gerar_ate(200)

    def _ruido(self, x):
        k = int(x // 520)
        while k + 2 >= len(self.nos):
            self.nos.append(self.rnd.uniform(-1, 1))
        t = _suave((x - k * 520) / 520)
        return self.nos[k] + (self.nos[k + 1] - self.nos[k]) * t

    def _desejado(self, x):
        d = max(0.0, x - 500)
        rampa = _suave(d / 900)
        a1 = 25 + min(260, d * 0.005)
        a2 = 6 + min(110, d * 0.0025)
        a3 = min(24, d * 0.0008)
        an = 10 + min(120, d * 0.003)
        f1, f2, f3 = self.fases
        h = (a1 * math.sin(x / 310 + f1) + a2 * math.sin(x / 137 + f2)
             + a3 * math.sin(x / 61 + f3) + an * self._ruido(x))
        return -(h * rampa + self._rampa(x))

    def _rampa(self, x):
        """Rampas de pulo: sobe devagar e cai de repente (lança o carro)."""
        while self.prox_rampa < x + 2000:
            d = self.prox_rampa
            alt = (45 + min(125, d * 0.0028)) * self.rnd.uniform(0.7, 1.0)
            larg = alt * self.rnd.uniform(3.0, 4.2)
            self.rampas.append((d, larg, alt))
            self.prox_rampa = d + larg + self.rnd.uniform(900, 1800) - min(500, d * 0.01)
        for x0, larg, alt in reversed(self.rampas):
            if x0 <= x:
                u = (x - x0) / larg
                if u >= 1:
                    return 0.0
                return alt * (u / 0.72 if u < 0.72 else (1 - u) / 0.28)
        return 0.0

    def _gerar_ate(self, n):
        lim = math.tan(math.radians(INCLINACAO_MAX)) * PASSO
        lim_suave = math.tan(math.radians(16)) * PASSO
        while len(self.ys) <= n:
            i = len(self.ys)
            ant = self.ys[-1]
            dy = max(-lim, min(lim, self._desejado(i * PASSO) - ant))
            vel2 = self._vel2_depois(dy)
            if vel2 < self.MIN_VEL2 and dy < -lim_suave:
                dy = -lim_suave
                vel2 = self._vel2_depois(dy)
            x = i * PASSO
            # Crista onde o carro pode decolar? Então, na zona onde ele
            # pode pousar (talvez devagar), só deixa subidas suaves
            ang = math.degrees(math.atan2(-dy, PASSO))
            self.angulos.append(ang)
            if len(self.angulos) > 5:
                self.angulos.pop(0)
            ds = math.hypot(PASSO, dy)
            self.vel2_otim = max(0.0, min(VEL_MAX ** 2, self.vel2_otim + 2 * (
                ACELERACAO - GRAVIDADE * (-dy / ds) - ATRITO) * ds))
            if max(self.angulos) - ang > 22 and self.vel2_otim > 300.0 ** 2:
                self.zona_pouso = x + 1000
            if x <= self.zona_pouso:
                vel2 = min(vel2, self.VEL2_POUSO)
            self.vel2 = max(0.0, vel2)
            self.ys.append(ant + dy)

    def _vel2_depois(self, dy):
        ds = math.hypot(PASSO, dy)
        seno = -dy / ds                    # > 0 subindo
        return min(self.CAP_VEL2, self.vel2 + 2 * (ACELERACAO - GRAVIDADE * seno - ATRITO) * ds)

    def y(self, x):
        """Altura do chão (y para baixo) em x, com interpolação linear."""
        if x < 0:
            return self.ys[0]
        i = int(x // PASSO)
        if i + 1 >= len(self.ys):
            self._gerar_ate(i + 64)
        t = (x - i * PASSO) / PASSO
        return self.ys[i] + (self.ys[i + 1] - self.ys[i]) * t

    def amostra(self, i):
        if i < 0:
            return self.ys[0]
        if i >= len(self.ys):
            self._gerar_ate(i + 64)
        return self.ys[i]


# ============================================================
# DESENHOS PRÉ-RENDERIZADOS
# ============================================================

def _criar_camadas():
    if "ceu" in _camadas:
        return _camadas
    rnd = random.Random(41)

    ceu = ui.gradiente(LARGURA, ALTURA, CEU, (170, 230, 255))
    _camadas["ceu"] = ceu

    # Montanhas distantes (faixa que emenda)
    mont = pygame.Surface((LARG_FAIXA, 300), pygame.SRCALPHA)
    pontos = [(0, 300)]
    for x in range(0, LARG_FAIXA + 1, 16):
        a = x / LARG_FAIXA * math.tau
        y = 150 - 60 * math.sin(a * 3 + 0.5) - 40 * math.sin(a * 7 + 2) - 18 * math.sin(a * 13)
        pontos.append((x, y))
    pontos.append((LARG_FAIXA, 300))
    pygame.draw.polygon(mont, MONTANHA, pontos)
    # Neve nos picos mais altos
    for x in range(0, LARG_FAIXA, 16):
        a = x / LARG_FAIXA * math.tau
        y = 150 - 60 * math.sin(a * 3 + 0.5) - 40 * math.sin(a * 7 + 2) - 18 * math.sin(a * 13)
        if y < 60:
            pygame.draw.circle(mont, (236, 244, 255), (x, int(y) + 6), 7)
    pontos2 = [(0, 300)]
    for x in range(0, LARG_FAIXA + 1, 16):
        a = x / LARG_FAIXA * math.tau
        y = 210 - 30 * math.sin(a * 5 + 1) - 20 * math.sin(a * 11 + 4)
        pontos2.append((x, y))
    pontos2.append((LARG_FAIXA, 300))
    pygame.draw.polygon(mont, (100, 140, 205), pontos2)
    _camadas["montanhas"] = mont

    # Nuvens
    nuvens = pygame.Surface((LARG_FAIXA, 260), pygame.SRCALPHA)
    for i in range(8):
        cx = int(i * LARG_FAIXA / 8 + rnd.randint(0, 120))
        cy = rnd.randint(30, 220)
        esc = rnd.uniform(0.6, 1.1)
        for dx in (-LARG_FAIXA, 0, LARG_FAIXA):
            for ox, oy, r in ((-40, 6, 26), (-12, -8, 34), (22, -2, 30), (48, 8, 22), (0, 14, 26)):
                pygame.draw.circle(nuvens, (255, 255, 255),
                                   (int(cx + dx + ox * esc), int(cy + oy * esc)), int(r * esc))
    _camadas["nuvens"] = nuvens

    # O SOL de óculos (decoração fixa)
    sol = pygame.Surface((180, 180), pygame.SRCALPHA)
    c = (90, 90)
    for k in range(12):
        a = k / 12 * math.tau
        p1 = (c[0] + math.cos(a) * 58, c[1] + math.sin(a) * 58)
        p2 = (c[0] + math.cos(a) * 84, c[1] + math.sin(a) * 84)
        pygame.draw.line(sol, (255, 210, 60), p1, p2, 6)
    pygame.draw.circle(sol, (255, 200, 40), c, 56)
    pygame.draw.circle(sol, (255, 226, 90), c, 50)
    # Óculos escuros
    for lado in (-1, 1):
        r = pygame.Rect(0, 0, 36, 22)
        r.center = (c[0] + lado * 20, c[1] - 6)
        pygame.draw.ellipse(sol, (30, 30, 40), r)
        pygame.draw.ellipse(sol, (90, 110, 150), (r.x + 6, r.y + 4, 10, 6))
    pygame.draw.line(sol, (30, 30, 40), (c[0] - 4, c[1] - 8), (c[0] + 4, c[1] - 8), 4)
    pygame.draw.arc(sol, (160, 80, 20), (c[0] - 18, c[1] + 2, 36, 26), math.pi + 0.4, math.tau - 0.4, 4)
    _camadas["sol"] = sol
    return _camadas


def _casca_sup(jogador):
    """Carroceria: meia casca de ovo na cor do ovo do jogador (cacheada)."""
    chave = ("casca", jogador.ovo)
    s = _camadas.get(chave)
    if s is not None:
        return s
    w, h = 124, 60
    cor = jogador.cor
    contorno = jogador.cor_contorno
    sup = pygame.Surface((w, h), pygame.SRCALPHA)
    corpo = pygame.Rect(2, -54, w - 4, 112)
    pygame.draw.ellipse(sup, contorno, corpo)
    pygame.draw.ellipse(sup, cor, corpo.inflate(-6, -6))
    # Brilho e faixa decorativa
    pygame.draw.arc(sup, ui.clarear(cor, 80), corpo.inflate(-22, -22), math.pi * 1.1, math.pi * 1.45, 5)
    faixa = ui.misturar(cor, (255, 255, 255), 0.55) if sum(cor) < 600 else (255, 170, 60)
    pygame.draw.arc(sup, faixa, corpo.inflate(-30, -40), math.pi * 1.2, math.pi * 1.8, 5)
    # Borda quebrada (zigue-zague) no topo: apaga o que está acima
    zig = [(0, 0)]
    for i, x in enumerate(range(0, w + 1, 10)):
        zig.append((x, 10 if i % 2 else 18))
    zig.append((w, 0))
    pygame.draw.polygon(sup, (0, 0, 0, 0), zig)
    borda = [(x, y + 1) for x, y in zig[1:-1]]
    pygame.draw.lines(sup, contorno, False, borda, 3)
    # Estrelinha decorativa
    ui.estrela(sup, (w // 2 + 22, 38), 7, AMARELO)
    _camadas[chave] = sup
    return sup


def _desenhar_roda(tela, centro, giro, esc=1.0):
    x, y = int(centro[0]), int(centro[1])
    r = int(RAIO_RODA * esc)
    pygame.draw.circle(tela, (34, 34, 40), (x, y), r)
    pygame.draw.circle(tela, (70, 70, 80), (x, y), r, max(1, int(3 * esc)))
    pygame.draw.circle(tela, (200, 200, 212), (x, y), int(r * 0.52))
    for k in range(3):
        a = giro + k * math.tau / 3
        pygame.draw.line(tela, (110, 110, 124), (x, y),
                         (x + math.cos(a) * r * 0.5, y + math.sin(a) * r * 0.5), max(1, int(3 * esc)))
    pygame.draw.circle(tela, (240, 180, 40), (x, y), max(2, int(4 * esc)))


def _galao(tela, pos, t=0.0):
    x, y = int(pos[0]), int(pos[1] + math.sin(t * 3) * 3)
    corpo = pygame.Rect(0, 0, 30, 38)
    corpo.midbottom = (x, y + 19)
    pygame.draw.rect(tela, (120, 20, 20), corpo.inflate(4, 4), border_radius=6)
    pygame.draw.rect(tela, (220, 40, 40), corpo, border_radius=5)
    pygame.draw.rect(tela, (255, 110, 110), (corpo.x + 4, corpo.y + 5, 5, corpo.h - 10), border_radius=2)
    # Alça e bico
    pygame.draw.rect(tela, (120, 20, 20), (corpo.x + 6, corpo.y - 8, 14, 10), 3, border_radius=3)
    pygame.draw.rect(tela, (60, 60, 60), (corpo.right - 8, corpo.y - 7, 6, 8))
    ui.desenhar_texto(tela, "G", (corpo.centerx + 1, corpo.centery + 2), 14, BRANCO, "center")


# ============================================================
# JOGO
# ============================================================

class OvoEstrada(MiniJogo):

    ID = "ovo_estrada"
    TITULO = "OVO NA ESTRADA"
    TITULO_CURTO = "ESTRADA"
    DESCRICAO = "Pilote o buggy-casca pelos morros, cuide da gasolina e dê cambalhotas. Não capote!"
    COR = (70, 170, 90)
    INSTRUCOES = [
        "Pilote o buggy-casca pelos morros!",
        "Pegue os GALÕES antes da gasolina acabar.",
        "Cada moeda da pista vale 1 OVOEDA de verdade!",
        "No ar ← e → giram: cambalhota vale +50. Não capote!",
        "→/D acelera • ←/A freia e dá ré (mouse: dir./esq.)",
    ]
    TRILHA = dict(bpm=132, tom="E", escala="mixolidia", lead="quadrada", duty=0.5,
                  envelope="normal", baixo="rock", onda_baixo="triangulo",
                  acomp="contratempo", onda_acomp="quadrada", bateria="rock",
                  energia=0.7, eco=(0.12, 0.15))

    MOEDAS_MAX = 30

    # --------------------------------------------------------
    # CENÁRIO
    # --------------------------------------------------------

    @classmethod
    def criar_fundo(cls, jogador):
        c = _criar_camadas()
        sup = c["ceu"].copy()
        sup.blit(c["nuvens"], (0, 20))
        sup.blit(c["montanhas"], (-300, 250))
        sup.blit(c["sol"], (LARGURA - 250, 40))
        # Morrinhos de grama (para a miniatura e a prévia)
        pontos = [(0, ALTURA)]
        for x in range(0, LARGURA + 1, 16):
            y = 520 - 50 * math.sin(x / 190) - 20 * math.sin(x / 70 + 1)
            pontos.append((x, y))
        pontos.append((LARGURA, ALTURA))
        pygame.draw.polygon(sup, TERRA, pontos)
        grama = pontos[1:-1] + [(x, y + 22) for x, y in reversed(pontos[1:-1])]
        pygame.draw.polygon(sup, GRAMA, grama)
        pygame.draw.lines(sup, GRAMA_BORDA, False, pontos[1:-1], 6)
        rnd = random.Random(3)
        for _ in range(60):
            x = rnd.randrange(LARGURA)
            y = 520 - 50 * math.sin(x / 190) - 20 * math.sin(x / 70 + 1) + rnd.randint(40, 200)
            pygame.draw.circle(sup, (110, 78, 45), (x, int(y)), rnd.randint(3, 6))
        return sup

    @classmethod
    def desenhar_icone(cls, sup, jogador):
        w, h = sup.get_size()
        tam = (150, 110)
        tmp = pygame.Surface(tam, pygame.SRCALPHA)
        cls._desenhar_carro_em(tmp, jogador, (tam[0] // 2, 84), 14, 0.3, 0.0)
        esc = min(0.8, (h - 8) / tam[1])
        tmp = pygame.transform.smoothscale(tmp, (int(tam[0] * esc), int(tam[1] * esc)))
        r = tmp.get_rect(midbottom=(w // 2 - 16, h - int(h * 0.12)))
        sup.blit(tmp, r)
        ui.moeda(sup, (w // 2 + 60, h // 2 - 16), 8)
        ui.moeda(sup, (w // 2 + 80, h // 2 - 20), 8)

    @staticmethod
    def _desenhar_carro_em(tela, jogador, centro, angulo, giro_rodas, mola, tempo=0.0,
                           com_ovo=True, rachado=False):
        """
        Desenha o buggy com o meio do eixo em `centro` (coordenadas da tela).
        angulo em graus (positivo = bico para cima).
        """
        a = math.radians(angulo)
        ca, sa = math.cos(a), math.sin(a)
        cx, cy = centro

        def mundo(lx, ly):
            return (cx + lx * ca + ly * sa, cy - lx * sa + ly * ca)

        # Ovo sentado (desenhado antes: a casca fica na frente)
        if com_ovo:
            balanco = math.sin(tempo * 9) * 3
            pos = mundo(LOCAL_OVO[0], LOCAL_OVO[1] + mola)
            jogador.desenhar(tela, pos, ALTURA_OVO, angulo=angulo + balanco)

        # Amortecedores
        for lado in (-1, 1):
            topo = mundo(lado * 34, -10 + mola)
            roda = mundo(lado * MEIO_EIXO, 0)
            pygame.draw.line(tela, (60, 60, 70), topo, roda, 5)

        # Casca
        casca = _casca_sup(jogador)
        rot = pygame.transform.rotate(casca, angulo)
        tela.blit(rot, rot.get_rect(center=mundo(LOCAL_CASCA[0], LOCAL_CASCA[1] + mola + 8)))

        # Rodas
        for lado in (-1, 1):
            _desenhar_roda(tela, mundo(lado * MEIO_EIXO, 0), giro_rodas + lado)

    # --------------------------------------------------------
    # PARTIDA
    # --------------------------------------------------------

    def reiniciar(self):
        _criar_camadas()
        self.terreno = Terreno(random.randrange(1 << 30))
        self.x = X_INICIO
        self.no_chao = True
        self.v = 0.0                    # velocidade ao longo do chão
        self.vx = 0.0                   # no ar
        self.vy = 0.0
        self.angulo = 0.0
        self.w = 0.0                    # giro no ar (graus/s)
        self.giro_acum = 0.0
        self.tempo_ar = 0.0
        self.y = self._y_chao_carro(self.x)[0]
        self.angulo = self._y_chao_carro(self.x)[1]

        self.combustivel = COMBUSTIVEL_MAX
        self.sem_gasolina = 0.0         # tempo desde que acabou
        self.parado = 0.0
        self.bipe = 0.0
        self.max_x = self.x
        self.metros = 0
        self.cambalhotas = 0
        self.moedas_pista = 0

        self.giro_rodas = 0.0
        self.vel_rodas = 0.0
        self.mola = 0.0                 # suspensão visual
        self.vel_mola = 0.0
        self.poeira = 0.0

        self.teclas = set()
        self.mouse_botoes = set()
        self.acelerou = False

        self.capotou = False
        self.fim_motivo = None
        self.t_fim = 0.0
        self.ovo_solto = None

        # Itens na pista
        self.galoes = []                # [x, pego]
        self.moedas = []                # [x, y, pega]
        self.prox_galao = X_INICIO + 900
        self.prox_moedas = X_INICIO + 700
        self._gerar_itens(self.x + 2400)

        self.cam_x = self.x - 300
        self.cam_y = self.y - 420

    def _gerar_itens(self, ate):
        while self.prox_galao < ate:
            self.galoes.append([self.prox_galao, False])
            d = self.prox_galao - X_INICIO
            self.prox_galao += 800 + min(5700, d * 0.07) + random.uniform(-80, 120)
        while self.prox_moedas < ate:
            x0 = self.prox_moedas
            for k in range(5):
                x = x0 + k * 40
                self.moedas.append([x, self._y_chao_carro(x)[0] - 38, False])
            self.prox_moedas += random.uniform(6500, 9000)

    def _y_chao_carro(self, x, angulo=None):
        """(y do meio do eixo, ângulo do chão) com as rodas apoiadas em x."""
        cos_a = math.cos(math.radians(angulo)) if angulo is not None else 1.0
        for _ in range(2):
            xr = x - MEIO_EIXO * cos_a
            xf = x + MEIO_EIXO * cos_a
            yr = self.terreno.y(xr)
            yf = self.terreno.y(xf)
            ang = math.degrees(math.atan2(yr - yf, xf - xr))
            cos_a = math.cos(math.radians(ang))
        return (yr + yf) / 2 - RAIO_RODA, ang

    def _mundo(self, lx, ly):
        a = math.radians(self.angulo)
        ca, sa = math.cos(a), math.sin(a)
        return (self.x + lx * ca + ly * sa, self.y - lx * sa + ly * ca)

    # --------------------------------------------------------
    # ENTRADA
    # --------------------------------------------------------

    def pausar(self):
        super().pausar()
        self.teclas.clear()
        self.mouse_botoes.clear()

    def evento_jogo(self, e):
        if e.type == pygame.KEYDOWN:
            self.teclas.add(e.key)
        elif e.type == pygame.KEYUP:
            self.teclas.discard(e.key)
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button in (1, 3):
            self.mouse_botoes.add(e.button)
        elif e.type == pygame.MOUSEBUTTONUP:
            self.mouse_botoes.discard(e.button)

    def _entrada(self):
        """(acelera, freia) combinando eventos guardados e o teclado real."""
        try:
            k = pygame.key.get_pressed()
            real_a = any(k[t] for t in TECLAS_ACELERA)
            real_f = any(k[t] for t in TECLAS_FREIA)
        except pygame.error:
            real_a = real_f = False
        acel = real_a or any(t in self.teclas for t in TECLAS_ACELERA) or 3 in self.mouse_botoes
        freia = real_f or any(t in self.teclas for t in TECLAS_FREIA) or 1 in self.mouse_botoes
        return acel, freia

    # --------------------------------------------------------
    # LÓGICA
    # --------------------------------------------------------

    def atualizar_jogo(self, dt):
        self._atualizar_mola(dt)
        if self.capotou:
            self._atualizar_capotado(dt)
            return

        acel, freia = self._entrada()
        if self.combustivel <= 0:
            acel = freia = False
        if acel or freia:
            self.acelerou = True

        if self.no_chao:
            self._fisica_chao(dt, acel, freia)
        else:
            self._fisica_ar(dt, acel, freia)
        if self.capotou:
            return

        # Rodas girando
        if self.no_chao:
            self.vel_rodas = self.v / RAIO_RODA
        else:
            alvo = 25.0 if acel else (-12.0 if freia else self.vel_rodas * 0.98)
            self.vel_rodas += (alvo - self.vel_rodas) * min(1.0, dt * 3)
        self.giro_rodas += self.vel_rodas * dt

        # Combustível
        gasto = GASTO_ACELERANDO if (acel or freia) and self.no_chao else GASTO_PARADO
        self.combustivel = max(0.0, self.combustivel - gasto * dt)
        if 0 < self.combustivel < 20:
            self.bipe -= dt
            if self.bipe <= 0:
                self.bipe = 1.0
                self.som("ponto", 0.5)

        # Distância e pontos
        if self.x > self.max_x:
            antes = int((self.max_x - X_INICIO) // (100 * PX_POR_METRO))
            self.max_x = self.x
            depois = int((self.max_x - X_INICIO) // (100 * PX_POR_METRO))
            if depois > antes:
                self.som("bandeira", 0.7)
                self.textos.adicionar(f"{depois * 100} m!", (self.x, self.y - 110), AMARELO, 20)
        self.metros = int((self.max_x - X_INICIO) / PX_POR_METRO)
        self.pontos = self.metros + 50 * self.cambalhotas

        self._pegar_itens()
        self._gerar_itens(self.x + 2400)
        # Limpa itens que ficaram para trás
        if len(self.moedas) > 40:
            self.moedas = [m for m in self.moedas if m[0] > self.x - 1200]
        if len(self.galoes) > 12:
            self.galoes = [g for g in self.galoes if g[0] > self.x - 1200]

        # Sem gasolina: para devagar e acaba
        if self.combustivel <= 0:
            self.sem_gasolina += dt
            if self.no_chao and abs(self.v) < 15:
                self.parado += dt
            else:
                self.parado = 0.0
            if self.parado >= 2.0 or self.sem_gasolina >= 15.0:
                self._acabar("SEM GASOLINA!")

        self._atualizar_camera(dt)

    def _fisica_chao(self, dt, acel, freia):
        _, inc = self._y_chao_carro(self.x, self.angulo)
        seno = math.sin(math.radians(inc))
        a = -GRAVIDADE * seno
        if acel:
            a += ACELERACAO
        elif freia:
            a -= FREIO
        else:
            # rolagem livre: atrito + arrasto
            a -= math.copysign(min(abs(self.v) / dt, ATRITO + abs(self.v) * 0.3), self.v) \
                if abs(self.v) > 0.01 else 0.0
        self.v += a * dt
        self.v = max(VEL_RE, min(VEL_MAX, self.v))

        # Poeira atrás da roda traseira
        if acel and self.v > 60:
            self.poeira -= dt
            if self.poeira <= 0:
                self.poeira = 0.05
                rx, ry = self._mundo(-MEIO_EIXO, RAIO_RODA)
                self.particulas.explodir((rx - 6, ry - 4), [(190, 160, 110), (160, 125, 80), (220, 200, 160)],
                                         2, 90, 0.45, (3, 6), -80)

        cos_i = math.cos(math.radians(inc))
        vx = self.v * cos_i
        vy = -self.v * seno
        novo_x = self.x + vx * dt
        if novo_x < X_INICIO - 100:
            novo_x = X_INICIO - 100
            self.v = max(0.0, self.v)

        # Decolagem: o chão lá na frente cai mais rápido que a queda livre?
        T = 0.08
        y_frente, _ = self._y_chao_carro(self.x + vx * T, inc)
        balistico = self.y + vy * T + 0.5 * GRAVIDADE * T * T
        if abs(self.v) > 150 and y_frente > balistico + 5:
            self.no_chao = False
            self.vx, self.vy = vx, vy
            self.tempo_ar = 0.0
            self.giro_acum = 0.0
            self.w = 0.0
            self.x = novo_x
            self.y = self.y + vy * dt
            return

        self.x = novo_x
        self.y, novo_ang = self._y_chao_carro(self.x, inc)
        # Solavanco visual na suspensão quando a rampa muda
        mudanca = _normalizar(novo_ang - self.angulo)
        self.vel_mola += abs(mudanca) * abs(self.v) * 0.02
        self.angulo = novo_ang

    def _fisica_ar(self, dt, acel, freia):
        self.tempo_ar += dt
        # Giro: → empina (gira para trás), ← abaixa o bico
        if acel or freia:
            alvo = GIRO_AR if acel else -GIRO_AR
        else:
            alvo = self.w * max(0.0, 1 - dt * 1.5)
        passo = ACEL_GIRO * dt * (2.0 if alvo * self.w < 0 else 1.0)
        self.w += max(-passo, min(passo, alvo - self.w))
        self.angulo += self.w * dt
        self.giro_acum += self.w * dt

        self.vy += GRAVIDADE * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.x < X_INICIO - 100:
            self.x = X_INICIO - 100
            self.vx = abs(self.vx) * 0.3

        # Cabeça bateu no chão? Capotou!
        hx, hy = self._mundo(*LOCAL_CABECA)
        if hy >= self.terreno.y(hx):
            self._capotar()
            return

        rodas = [self._mundo(-MEIO_EIXO, 0), self._mundo(MEIO_EIXO, 0)]
        entra = [ry + RAIO_RODA - self.terreno.y(rx) for rx, ry in rodas]
        if self.tempo_ar < GRACA_DECOLAGEM:
            # Logo depois de decolar a roda de trás ainda passa pela
            # beirada da rampa: ela "segura" o carro (não é pouso)
            k = 0 if entra[0] >= entra[1] else 1
            if entra[k] > 0:
                self.y -= entra[k]
                rx = rodas[k][0]
                inclinacao = (self.terreno.y(rx + 3) - self.terreno.y(rx - 3)) / 6
                self.vy = min(self.vy, self.vx * inclinacao)
            return

        # Alguma roda encostou no chão? Pouso!
        if max(entra) >= 0:
            self._pousar()

    def _pousar(self):
        y_chao, inc = self._y_chao_carro(self.x)
        diff = _normalizar(self.angulo - inc)

        # De ponta-cabeça (mais de 110° da vertical): capotou
        if abs(_normalizar(self.angulo)) > 110:
            self._capotar()
            return

        rad = math.radians(inc)
        tangente = self.vx * math.cos(rad) - self.vy * math.sin(rad)
        normal = abs(self.vx * math.sin(rad) + self.vy * math.cos(rad))
        self.no_chao = True
        self.angulo = inc
        self.y = y_chao
        self.v = max(VEL_RE, min(VEL_MAX, tangente))

        if abs(diff) >= 60:
            # Pouso torto: perde velocidade e dá uma chacoalhada
            self.v *= 0.5
            self.tremer(0.2)
            self.som("bater", 0.7)
            self.vel_mola += 260
        elif self.tempo_ar > 0.3:
            self.vel_mola += min(320, normal * 0.5)
            if normal > 350:
                self.tremer(0.1)
                self.som("bater", 0.4)
            else:
                self.som("boing", 0.3)

        # Cambalhotas completas (só vale pousando bem)
        voltas = int((abs(self.giro_acum) + 40) // 360)
        if voltas > 0 and abs(diff) < 60:
            self.cambalhotas += voltas
            self.pontos = self.metros + 50 * self.cambalhotas
            txt = "CAMBALHOTA!" if voltas == 1 else f"{voltas}× CAMBALHOTA!"
            self.textos.adicionar(txt, (self.x, self.y - 120), AMARELO, 20)
            self.textos.adicionar(f"+{50 * voltas}", (self.x, self.y - 90), BRANCO, 16)
            self.som("acerto")
            j = self.jogador
            self.particulas.explodir((self.x, self.y - 60), [AMARELO, BRANCO, j.cor, j.cor_clara], 26, 260)
        self.giro_acum = 0.0
        self.tempo_ar = 0.0

    def _capotar(self):
        """O ovo cai de cabeça e... CRACK!"""
        self.capotou = True
        self.t_fim = 0.0
        ox, oy = self._mundo(*LOCAL_OVO)
        vx = self.vx if not self.no_chao else self.v
        self.ovo_solto = {"x": ox, "y": oy, "vx": vx * 0.4 + 40, "vy": -420.0,
                          "ang": self.angulo, "w": 420.0, "no_chao": False, "t": 0.0}
        self.som("bater")
        self.tremer(0.25)
        if not self.no_chao:
            # O carro continua caindo até o chão
            self.vy = min(self.vy, 200.0)

    def _atualizar_capotado(self, dt):
        self.t_fim += dt
        # Carro de ponta-cabeça caindo e parando
        if not self.no_chao:
            self.vy += GRAVIDADE * dt
            self.x += self.vx * dt * 0.6
            self.y += self.vy * dt
            self.angulo += self.w * dt * 0.5
            # De ponta-cabeça ele descansa em cima da casca
            yc = self.terreno.y(self.x) - (42 if abs(_normalizar(self.angulo)) > 90 else 20)
            if self.y >= yc:
                self.y = yc
                self.no_chao = True
                self.vel_mola += 200
        # Ovo voando até o chão
        o = self.ovo_solto
        if o and not o["no_chao"]:
            o["vy"] += GRAVIDADE * dt
            o["x"] += o["vx"] * dt
            o["y"] += o["vy"] * dt
            o["ang"] += o["w"] * dt
            chao = self.terreno.y(o["x"]) - ALTURA_OVO * 0.42
            if o["y"] >= chao and o["vy"] > 0:
                o["y"] = chao
                o["no_chao"] = True
                o["ang"] = 90 if _normalizar(o["ang"]) > 0 else -90
                j = self.jogador
                self.som("explosao", 0.6)
                self.tremer(0.4)
                self.particulas.explodir((o["x"], o["y"]), [j.cor, j.cor_clara, BRANCO, (255, 220, 90)],
                                         30, 300, 0.9, (3, 7))
                self.textos.adicionar("CRACK!", (o["x"], o["y"] - 70), (255, 90, 70), 32)
        elif o:
            o["t"] += dt
        self._atualizar_camera(dt, alvo_x=o["x"] if o else None, alvo_y=o["y"] if o else None)
        if o and o["no_chao"] and o["t"] > 1.4 or self.t_fim > 5.0:
            self._acabar("CRACK!")

    def _acabar(self, motivo):
        self.fim_motivo = motivo
        self.terminar(venceu=False, titulo=motivo, linhas=[
            f"DISTÂNCIA: {self.metros} m",
            f"CAMBALHOTAS: {self.cambalhotas}",
            f"MOEDAS DA PISTA: {self.moedas_pista}",
        ])

    def calcular_moedas(self, valor, venceu):
        return max(0, min(self.MOEDAS_MAX, self.moedas_pista + self.metros // 200))

    def _pegar_itens(self):
        cx, cy = self._mundo(0, -24)
        hx, hy = self._mundo(*LOCAL_OVO)
        for m in self.moedas:
            if m[2] or abs(m[0] - cx) > 80:
                continue
            if math.hypot(m[0] - cx, m[1] - cy) < 50 or math.hypot(m[0] - hx, m[1] - hy) < 40:
                m[2] = True
                self.moedas_pista += 1
                self.som("moeda", 0.6)
                self.particulas.explodir((m[0], m[1]), [AMARELO, (255, 240, 170)], 8, 140, 0.4, (2, 4))
                self.textos.adicionar("+1", (m[0], m[1] - 20), AMARELO, 14)
        for g in self.galoes:
            if g[1]:
                continue
            gy = self.terreno.y(g[0]) - 30
            # Pega também passando por cima num pulo (mais justo)
            if abs(g[0] - cx) < 56 and gy - 260 < cy < gy + 50:
                g[1] = True
                self.combustivel = COMBUSTIVEL_MAX
                self.bipe = 0.0
                self.som("acerto", 0.8)
                self.particulas.explodir((g[0], gy), [(220, 40, 40), (255, 200, 60), BRANCO], 14, 180, 0.6)
                self.textos.adicionar("GASOLINA!", (g[0], gy - 50), (255, 120, 90), 16)

    def _atualizar_mola(self, dt):
        # Mola amortecida (só visual): a carroceria sobe e desce ~4 px
        self.vel_mola += (-120.0 * self.mola - 9.0 * self.vel_mola) * dt
        self.mola += self.vel_mola * dt
        self.mola = max(-7.0, min(7.0, self.mola))

    def _atualizar_camera(self, dt, alvo_x=None, alvo_y=None):
        velx = self.v if self.no_chao else self.vx
        frente = max(-80.0, min(220.0, velx * 0.3))
        ax = (alvo_x if alvo_x is not None else self.x) - 320 - frente
        ay = (alvo_y if alvo_y is not None else self.y) - 430
        k = min(1.0, dt * 4)
        self.cam_x += (ax - self.cam_x) * k
        self.cam_y += (ay - self.cam_y) * min(1.0, dt * 3)
        # Nunca deixa o carro sair da tela
        sx = self.x - self.cam_x
        sy = self.y - self.cam_y
        if sx > LARGURA - 200:
            self.cam_x = self.x - (LARGURA - 200)
        if sx < 120:
            self.cam_x = self.x - 120
        if sy < 170:
            self.cam_y = self.y - 170
        if sy > ALTURA - 110:
            self.cam_y = self.y - (ALTURA - 110)

    # --------------------------------------------------------
    # DESENHO
    # --------------------------------------------------------

    def _faixa(self, tela, sup, fator, y, extra=0.0):
        off = int(-(self.cam_x * fator + extra)) % LARG_FAIXA
        tela.blit(sup, (off, y))
        tela.blit(sup, (off - LARG_FAIXA, y))

    def desenhar_jogo(self, tela):
        c = _camadas
        tela.blit(c["ceu"], (0, 0))
        self._faixa(tela, c["nuvens"], 0.05, 20, self.tempo * 8)
        tela.blit(c["sol"], (LARGURA - 250, 64))
        ym = int(250 - max(-120, min(160, self.cam_y * 0.08)))
        self._faixa(tela, c["montanhas"], 0.2, ym)
        if ym + 300 < ALTURA:
            pygame.draw.rect(tela, (100, 140, 205), (0, ym + 299, LARGURA, ALTURA - ym - 299))

        self._desenhar_terreno(tela)
        cx, cy = self.cam_x, self.cam_y

        # Placas a cada 100 m
        passo = 100 * PX_POR_METRO
        k0 = max(1, int((cx - 100 - X_INICIO) // passo))
        for k in range(k0, k0 + 3):
            px = X_INICIO + k * passo
            sx = px - cx
            if -80 < sx < LARGURA + 80:
                self._placa(tela, sx, self.terreno.y(px) - cy, f"{k * 100} m")

        # Galões e moedas
        for g in self.galoes:
            sx = g[0] - cx
            if not g[1] and -40 < sx < LARGURA + 40:
                _galao(tela, (sx, self.terreno.y(g[0]) - 30 - cy), self.tempo)
        for m in self.moedas:
            sx = m[0] - cx
            if not m[2] and -20 < sx < LARGURA + 20:
                giro = abs(math.cos(self.tempo * 3 + m[0] * 0.02))
                ui.moeda(tela, (sx, m[1] - cy), 13, max(0.25, giro))

        # Carro e ovo
        centro = (self.x - cx, self.y - cy)
        com_ovo = not self.capotou
        self._desenhar_carro_em(tela, self.jogador, centro, self.angulo, self.giro_rodas,
                                -self.mola, self.tempo, com_ovo)
        if self.capotou and self.ovo_solto:
            self._desenhar_ovo_solto(tela)

        desloc = (-cx, -cy)
        self.particulas.desenhar(tela, desloc)
        self.textos.desenhar(tela, desloc)

        # Dicas
        if self.estado == "jogando" and not self.acelerou:
            if int(self.tempo * 2.5) % 3 != 0:
                ui.desenhar_texto(tela, "SEGURE → PARA ACELERAR!", (LARGURA // 2, 200), 20,
                                  AMARELO, "center")
        if self.estado == "jogando" and self.combustivel <= 0 and not self.capotou:
            if int(self.tempo * 3) % 2 == 0:
                ui.desenhar_texto(tela, "SEM GASOLINA!", (LARGURA // 2, 200), 24,
                                  (255, 110, 90), "center")

    def _desenhar_terreno(self, tela):
        cx, cy = self.cam_x, self.cam_y
        i0 = int((cx - 40) // PASSO)
        i1 = int((cx + LARGURA + 40) // PASSO) + 1
        topo = []
        for i in range(i0, i1 + 1):
            topo.append((i * PASSO - cx, self.terreno.amostra(i) - cy))
        base = ALTURA + 10
        fundo_y = max(base, max(p[1] for p in topo) + 10)
        pygame.draw.polygon(tela, TERRA, topo + [(topo[-1][0], fundo_y), (topo[0][0], fundo_y)])

        # Pedrinhas na terra
        for i in range(i0, i1 + 1):
            h = (i * 2654435761) & 0xFFFF
            if h % 3:
                continue
            sx = i * PASSO - cx + (h >> 4) % 20
            sy = self.terreno.amostra(i) - cy + 40 + (h >> 6) % 150
            if sy < ALTURA + 10:
                r = 3 + (h >> 9) % 4
                pygame.draw.circle(tela, (110, 78, 45), (int(sx), int(sy)), r)
                pygame.draw.circle(tela, (160, 122, 82), (int(sx - 1), int(sy - 1)), max(1, r - 2))

        # Grama por cima com borda escura
        grama = topo + [(x, y + 18) for x, y in reversed(topo)]
        pygame.draw.polygon(tela, GRAMA, grama)
        pygame.draw.lines(tela, GRAMA_BORDA, False, topo, 6)

    def _placa(self, tela, sx, sy, texto):
        x, y = int(sx), int(sy)
        pygame.draw.rect(tela, (100, 64, 34), (x - 4, y - 70, 8, 72))
        r = pygame.Rect(0, 0, 96, 36)
        r.midbottom = (x, y - 60)
        pygame.draw.rect(tela, (90, 56, 28), r.inflate(6, 6), border_radius=6)
        pygame.draw.rect(tela, (190, 140, 80), r, border_radius=5)
        for yy in (r.y + 4, r.bottom - 5):
            pygame.draw.line(tela, (160, 112, 60), (r.x + 5, yy), (r.right - 5, yy), 2)
        ui.desenhar_texto(tela, texto, r.center, 12, (70, 40, 20), "center", False)

    def _desenhar_ovo_solto(self, tela):
        o = self.ovo_solto
        pos = (o["x"] - self.cam_x, o["y"] - self.cam_y)
        self.jogador.desenhar(tela, pos, ALTURA_OVO, angulo=o["ang"])
        if o["no_chao"]:
            # Rachaduras em zigue-zague
            a = math.radians(o["ang"])
            ca, sa = math.cos(a), math.sin(a)
            pts = []
            for lx, ly in ((-18, -4), (-10, 4), (-3, -6), (4, 5), (11, -5), (18, 3)):
                pts.append((pos[0] + lx * ca + ly * sa, pos[1] - lx * sa + ly * ca))
            pygame.draw.lines(tela, (40, 30, 30), False, pts, 3)
            # Estrelinhas de tontura
            for k in range(3):
                ang = self.tempo * 4 + k * math.tau / 3
                ui.estrela(tela, (pos[0] + math.cos(ang) * 30, pos[1] - 34 + math.sin(ang) * 8), 6,
                           AMARELO, ang)

    def desenhar_hud(self, tela):
        # Distância
        caixa = pygame.Rect(12, 12, 170, 48)
        ui.painel(tela, caixa, (20, 24, 40), BRANCO, 12, 3, sombra=False)
        ui.desenhar_texto(tela, f"{self.metros} m", (caixa.x + 16, caixa.centery + 1), 20, AMARELO, "midleft")

        # Gasolina
        caixa2 = pygame.Rect(caixa.right + 10, 12, 230, 48)
        pisca = self.combustivel < 20 and int(self.tempo * 4) % 2 == 0
        ui.painel(tela, caixa2, (90, 20, 20) if pisca else (20, 24, 40),
                  (255, 90, 90) if pisca else BRANCO, 12, 3, sombra=False)
        # bombinha
        bx, by = caixa2.x + 14, caixa2.y + 10
        pygame.draw.rect(tela, (220, 40, 40), (bx, by + 4, 18, 24), border_radius=3)
        pygame.draw.rect(tela, (255, 230, 230), (bx + 4, by + 8, 10, 7))
        pygame.draw.line(tela, (220, 40, 40), (bx + 18, by + 8), (bx + 24, by + 14), 3)
        pygame.draw.line(tela, (220, 40, 40), (bx + 24, by + 14), (bx + 24, by + 24), 3)
        barra = pygame.Rect(caixa2.x + 50, caixa2.y + 15, 164, 18)
        pygame.draw.rect(tela, (50, 54, 70), barra, border_radius=6)
        frac = self.combustivel / COMBUSTIVEL_MAX
        if frac > 0:
            cor = (90, 210, 90) if frac > 0.5 else ((255, 200, 60) if frac > 0.2 else (240, 70, 60))
            cheio = barra.copy()
            cheio.w = max(6, int(barra.w * frac))
            pygame.draw.rect(tela, cor, cheio, border_radius=6)
        pygame.draw.rect(tela, BRANCO, barra, 2, border_radius=6)

        # Moedas da pista
        caixa3 = pygame.Rect(caixa2.right + 10, 12, 120, 48)
        ui.painel(tela, caixa3, (20, 24, 40), BRANCO, 12, 3, sombra=False)
        ui.moeda(tela, (caixa3.x + 24, caixa3.centery), 13)
        ui.desenhar_texto(tela, f"×{self.moedas_pista}", (caixa3.x + 44, caixa3.centery + 1), 14,
                          AMARELO, "midleft")

        # Pontos e recorde
        caixa4 = pygame.Rect(caixa3.right + 10, 12, 240, 48)
        ui.painel(tela, caixa4, (20, 24, 40), BRANCO, 12, 3, sombra=False)
        ui.desenhar_texto(tela, f"PONTOS: {self.pontos}", (caixa4.x + 14, caixa4.y + 10), 12, BRANCO)
        rec = self.recorde()
        ui.desenhar_texto(tela, f"RECORDE: {rec if rec is not None else '--'}",
                          (caixa4.x + 14, caixa4.y + 29), 10, (180, 220, 255))
