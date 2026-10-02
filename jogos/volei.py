import math
import random

import pygame

from settings import *
from core import ui
from core.idioma import t, t as _t
from jogos.base import MiniJogo

# ============================================================
# VÔLEI DE PRAIA
# ============================================================
# Vôlei 1 contra 1 na praia, com vista de lado (estilo "Slime
# Volleyball"). O seu ovo joga do lado esquerdo contra o ROBERT,
# um ovo da CPU com outra cor e outras partes. A bola quica na
# cabeça dos ovos: onde ela bate muda para onde ela vai.
# Quem fizer 7 pontos primeiro vence!

# Cenário
HORIZONTE = 380                 # onde o céu encontra o mar
AREIA_Y = 522                   # começo da areia
CHAO = 628                      # linha onde os ovos pisam (e a bola "cai")
TETO = 104                      # teto invisível (abaixo do placar)

# Rede (um poste com o topo arredondado)
REDE_X = LARGURA // 2
REDE_TOPO = 488
REDE_RAIO = 7

# Bola
BOLA_R = 20
GRAVIDADE_BOLA = 900
VEL_MAX_BOLA = 960
IMPULSO_MIN = 470               # a bola sempre sobe um pouco ao bater no ovo
EMPURRAO_LADO = 240             # quanto a batida "de lado" empurra a bola
VEL_CORTADA = 640
VEL_MAX_SUBIDA = 800
QUIQUE_OVO = 0.72
QUIQUE_REDE = 0.7
QUIQUE_PAREDE = 0.8

# Ovos
ALTURA_OVO = 92
MEIA_LARG = ALTURA_OVO * 0.45   # metade da largura do corpo do ovo
GRAVIDADE_OVO = 2300
PULO = 840
VEL_OVO = 380

CASA_JOGADOR = 230
CASA_CPU = LARGURA - 230
Y_SAQUE = 300
TEMPO_SAQUE = 0.8               # a bola fica parada no ar antes do saque
TEMPO_PONTO = 1.2
PONTOS_VITORIA = 7

SUB_PASSO = 1 / 240             # passos pequenos: a bola não atravessa nada

TECLAS_ESQ = (pygame.K_LEFT, pygame.K_a)
TECLAS_DIR = (pygame.K_RIGHT, pygame.K_d)
TECLAS_PULO = (pygame.K_UP, pygame.K_w, pygame.K_SPACE)

# Jeito da CPU em cada dificuldade
#   vel: velocidade   reacao: tempo entre decisões   erro: erro de mira (px)
#   pulo: chance de pular   forca: força máxima das batidas
#   mira: quanto fica ao lado da bola (mais = bola mais "de lado")
#   cortada: chance de cortar quando pula perto da rede
CPU = [
    {"vel": 210, "reacao": 0.32, "erro": 66, "pulo": 0.25, "forca": 0.76,
     "mira": (4, 22), "cortada": 0.0},                                        # FÁCIL
    {"vel": 300, "reacao": 0.17, "erro": 28, "pulo": 0.55, "forca": 0.92,
     "mira": (8, 34), "cortada": 0.45},                                       # NORMAL
    {"vel": 380, "reacao": 0.07, "erro": 8, "pulo": 0.85, "forca": 1.0,
     "mira": (14, 40), "cortada": 0.85},                                      # DIFÍCIL
]

NOME_CPU = "ROBERT"


def _aparencia_cpu(aparencia):
    """O ROBERT tem sempre outra cor e outras partes que o jogador."""
    ovo, cabelo, olho, boca = aparencia
    return ((ovo + 2) % 4, (cabelo + 3) % 8, (olho + 1) % 3, (boca + 3) % 6)


# ============================================================
# BOLA DE VÔLEI (desenhada uma vez só)
# ============================================================

_sprite_bola = None


def _bola_sup():
    global _sprite_bola
    if _sprite_bola is not None:
        return _sprite_bola

    # Desenha 4x maior e diminui no fim (fica suave)
    z = 4
    r = BOLA_R * z
    lado = r * 2 + 2 * z
    c = lado // 2
    desenho = pygame.Surface((lado, lado), pygame.SRCALPHA)
    desenho.fill((255, 252, 240))

    # Gomos coloridos: anéis de círculos grandes cortados pela bola
    azul = (50, 110, 215)
    amarelo = (255, 205, 55)
    for (ox, oy), cor in (((-1.55, 0.0), azul), ((0.8, -1.35), amarelo), ((0.8, 1.35), azul)):
        centro = (c + ox * r, c + oy * r)
        pygame.draw.circle(desenho, cor, centro, int(r * 1.33))
        pygame.draw.circle(desenho, (255, 252, 240), centro, int(r * 1.0))
        pygame.draw.circle(desenho, (70, 70, 90), centro, int(r * 1.33), z)
        pygame.draw.circle(desenho, (70, 70, 90), centro, int(r * 1.0), z)

    # Recorta no formato de círculo
    mascara = pygame.Surface((lado, lado), pygame.SRCALPHA)
    pygame.draw.circle(mascara, (255, 255, 255, 255), (c, c), r)
    desenho.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

    # Contorno e brilho
    pygame.draw.circle(desenho, (40, 40, 60), (c, c), r, 2 * z)
    _sprite_bola = pygame.transform.smoothscale(desenho, (lado // z, lado // z))
    return _sprite_bola


_sombras = {}


def _sombra(largura):
    """Elipse escura semitransparente (com cache por tamanho)."""
    largura = max(8, int(largura) // 2 * 2)
    s = _sombras.get(largura)
    if s is None:
        altura = max(4, largura // 4)
        s = pygame.Surface((largura, altura), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (70, 50, 20, 90), s.get_rect())
        _sombras[largura] = s
    return s


# ============================================================
# FÍSICA DA BOLA (usada no jogo e na previsão da CPU)
# ============================================================

def _mover_bola(b, dt):
    """
    Move a bola b = [x, y, vx, vy] por dt segundos e trata paredes,
    teto e rede. Devolve True se bateu na rede.
    """
    b[3] += GRAVIDADE_BOLA * dt
    b[0] += b[2] * dt
    b[1] += b[3] * dt

    # Paredes
    if b[0] < BOLA_R:
        b[0] = BOLA_R
        b[2] = abs(b[2]) * QUIQUE_PAREDE
    elif b[0] > LARGURA - BOLA_R:
        b[0] = LARGURA - BOLA_R
        b[2] = -abs(b[2]) * QUIQUE_PAREDE

    # Teto invisível
    if b[1] < TETO:
        b[1] = TETO
        b[3] = abs(b[3]) * 0.5

    # Rede: um segmento vertical com raio (cápsula)
    topo = REDE_TOPO + REDE_RAIO
    py = min(max(b[1], topo), CHAO + 100)
    dx = b[0] - REDE_X
    dy = b[1] - py
    dist = math.hypot(dx, dy)
    minimo = BOLA_R + REDE_RAIO
    if dist >= minimo:
        return False

    if dist < 0.001:
        # Caiu exatamente em cima do poste: empurra para o lado de onde veio
        nx, ny = (-1.0 if b[2] > 0 else 1.0), 0.0
    else:
        nx, ny = dx / dist, dy / dist
    b[0] = REDE_X + nx * minimo
    b[1] = py + ny * minimo

    vn = b[2] * nx + b[3] * ny
    if vn < 0:
        b[2] -= (1 + QUIQUE_REDE) * vn * nx
        b[3] -= (1 + QUIQUE_REDE) * vn * ny

    # Não deixa a bola ficar equilibrada no topo da rede
    if ny < -0.85 and abs(b[2]) < 80:
        lado = 1 if dx > 0 else -1 if dx < 0 else random.choice((-1, 1))
        b[2] = 110 * lado
    return True


# ============================================================
# OVO (jogador ou CPU)
# ============================================================

class Ovo:

    def __init__(self, x, minimo, maximo, aparencia, espelhar):
        self.x = x
        self.base = CHAO             # y dos "pés" do ovo
        self.vx = 0.0
        self.vy = 0.0
        self.no_chao = True
        self.minimo = minimo
        self.maximo = maximo
        self.aparencia = aparencia
        self.espelhar = espelhar
        self.esticar = 0.0           # >0 esticado, <0 amassado
        self.vel_esticar = 0.0
        self.espera_toque = 0.0      # evita som repetido

    @property
    def centro_y(self):
        return self.base - ALTURA_OVO / 2

    def pular(self):
        if not self.no_chao:
            return False
        self.vy = -PULO
        self.no_chao = False
        self.vel_esticar += 7.0
        return True

    def mover(self, dt):
        self.x = min(max(self.x + self.vx * dt, self.minimo), self.maximo)
        if not self.no_chao:
            self.vy += GRAVIDADE_OVO * dt
            self.base += self.vy * dt
            if self.base >= CHAO:
                impacto = min(1.0, self.vy / PULO)
                self.base = CHAO
                self.vy = 0.0
                self.no_chao = True
                self.vel_esticar -= 6.0 * impacto

    def animar(self, dt):
        # Mola simples para o squash & stretch
        self.vel_esticar += (-260 * self.esticar - 12 * self.vel_esticar) * dt
        self.esticar = max(-1.0, min(1.0, self.esticar + self.vel_esticar * dt))
        self.espera_toque = max(0.0, self.espera_toque - dt)


# ============================================================
# JOGO
# ============================================================

class Volei(MiniJogo):

    ID = "volei"
    TITULO = "VÔLEI DE PRAIA"
    TITULO_CURTO = "VÔLEI"
    DESCRICAO = "Vôlei de praia contra o ROBERT! Rebata a bola com a cabeça do seu ovo."
    COR = (240, 150, 50)
    INSTRUCOES = [
        "Rebata a bola com a cabeça do seu ovo!",
        "Se a bola cair na areia do ROBERT, ponto seu.",
        "Onde a bola bate no ovo muda o rumo dela.",
        "Quem fizer 7 pontos primeiro vence!",
        "← → ou A D para mover, ↑ W ou ESPAÇO pula",
    ]
    OPCOES = ["FÁCIL", "NORMAL", "DIFÍCIL"]
    MENOR_MELHOR = False
    MOEDAS_MAX = 26

    def calcular_moedas(self, valor, venceu):
        """2 por ponto feito + 6 se venceu, mais valendo nas dificuldades altas."""
        base = 2 * self.placar[0] + (6 if venceu else 0)
        return min(self.MOEDAS_MAX, round(base * (1.0, 1.25, 1.5)[self.opcao]))
    ROTULO_PONTOS = "PONTOS"
    CONTAGEM = True

    # --------------------------------------------------------
    # CENÁRIO: praia com mar, coqueiro e guarda-sol
    # --------------------------------------------------------

    @classmethod
    def criar_fundo(cls, jogador):
        sup = pygame.Surface((LARGURA, ALTURA))
        rnd = random.Random(33)

        # Céu
        sup.blit(ui.gradiente(LARGURA, HORIZONTE, (80, 160, 235), (190, 228, 250)), (0, 0))

        # Sol com brilho
        sol = (830, 170)
        for i, raio in enumerate((92, 76, 62)):
            cor = ui.misturar((190, 228, 250), (255, 240, 170), 0.35 + i * 0.25)
            pygame.draw.circle(sup, cor, sol, raio)
        pygame.draw.circle(sup, (255, 222, 90), sol, 48)
        pygame.draw.circle(sup, (255, 240, 150), (sol[0] - 14, sol[1] - 14), 18)

        # Nuvens
        for nx, ny, esc in ((140, 150, 1.0), (430, 110, 0.8), (640, 200, 0.7), (980, 110, 0.9)):
            for dx, dy, r in ((-30, 6, 22), (0, -6, 30), (32, 4, 24), (58, 10, 16), (-52, 12, 14)):
                pygame.draw.circle(sup, (255, 255, 255), (int(nx + dx * esc), int(ny + dy * esc)),
                                   int(r * esc))
            pygame.draw.rect(sup, (255, 255, 255),
                             (int(nx - 52 * esc), int(ny + 6 * esc), int(112 * esc), int(18 * esc)),
                             border_radius=8)

        # Ilhazinha no horizonte
        pygame.draw.ellipse(sup, (90, 150, 120), (560, HORIZONTE - 14, 150, 30))
        pygame.draw.ellipse(sup, (110, 170, 130), (590, HORIZONTE - 22, 70, 30))

        # Mar
        sup.blit(ui.gradiente(LARGURA, AREIA_Y - HORIZONTE, (40, 130, 200), (70, 190, 210)),
                 (0, HORIZONTE))
        for i in range(10):
            y = HORIZONTE + 8 + i * 13
            for _ in range(8 + i):
                x = rnd.randrange(-40, LARGURA)
                w = rnd.randint(20, 60 + i * 6)
                pygame.draw.line(sup, (120, 205, 235), (x, y), (x + w, y), 2)
        pygame.draw.line(sup, (230, 250, 255), (0, HORIZONTE), (LARGURA, HORIZONTE), 2)

        # Areia com textura
        sup.blit(ui.gradiente(LARGURA, ALTURA - AREIA_Y, (240, 214, 150), (226, 190, 120)),
                 (0, AREIA_Y))
        pygame.draw.rect(sup, (205, 175, 120), (0, AREIA_Y, LARGURA, 10))     # areia molhada
        for _ in range(900):
            x = rnd.randrange(LARGURA)
            y = rnd.randrange(AREIA_Y + 10, ALTURA)
            cor = rnd.choice([(214, 180, 115), (250, 230, 180), (200, 165, 105)])
            pygame.draw.circle(sup, cor, (x, y), rnd.choice((1, 1, 2)))
        for _ in range(8):
            x, y = rnd.randrange(40, LARGURA - 40), rnd.randrange(CHAO + 30, ALTURA - 10)
            pygame.draw.ellipse(sup, (255, 240, 225), (x, y, 10, 7))          # conchinhas
            pygame.draw.ellipse(sup, (210, 150, 130), (x, y, 10, 7), 1)

        # Coqueiro (fora da quadra, à esquerda)
        cls._coqueiro(sup, 62, AREIA_Y + 30)

        # Guarda-sol com toalha (à direita)
        cls._guarda_sol(sup, 952, AREIA_Y + 36)

        # Linhas da quadra (corda azul)
        frente, fundo = CHAO + 22, CHAO - 18
        pygame.draw.line(sup, (40, 90, 200), (24, frente), (LARGURA - 24, frente), 4)
        pygame.draw.line(sup, (60, 110, 210), (60, fundo), (LARGURA - 60, fundo), 3)
        pygame.draw.line(sup, (40, 90, 200), (24, frente), (60, fundo), 3)
        pygame.draw.line(sup, (40, 90, 200), (LARGURA - 24, frente), (LARGURA - 60, fundo), 3)

        # Rede: poste de madeira com rede e topo arredondado
        base_rede = CHAO + 12
        topo = REDE_TOPO
        pygame.draw.ellipse(sup, (200, 165, 105), (REDE_X - 22, base_rede - 6, 44, 12))
        poste = pygame.Rect(REDE_X - REDE_RAIO, topo + REDE_RAIO, REDE_RAIO * 2,
                            base_rede - topo - REDE_RAIO)
        pygame.draw.rect(sup, (235, 235, 240), poste)
        for y in range(poste.top + 6, poste.bottom, 8):
            pygame.draw.line(sup, (150, 150, 165), (poste.left, y), (poste.right - 1, y), 1)
        pygame.draw.line(sup, (150, 150, 165), (REDE_X, poste.top), (REDE_X, poste.bottom), 1)
        pygame.draw.rect(sup, (60, 60, 80), poste, 2)
        pygame.draw.circle(sup, (230, 60, 60), (REDE_X, topo + REDE_RAIO), REDE_RAIO)
        pygame.draw.rect(sup, (230, 60, 60), (REDE_X - REDE_RAIO, topo + REDE_RAIO, REDE_RAIO * 2, 10))
        pygame.draw.circle(sup, (60, 60, 80), (REDE_X, topo + REDE_RAIO), REDE_RAIO, 2)
        pygame.draw.circle(sup, (255, 150, 150), (REDE_X - 2, topo + REDE_RAIO - 2), 2)
        return sup

    @staticmethod
    def _coqueiro(sup, x, y):
        # Tronco curvado feito de gomos
        pontos = []
        for i in range(15):
            t = i / 14
            pontos.append((x + math.sin(t * 1.3) * 60, y - t * 250))
        for i, (px, py) in enumerate(pontos):
            r = 13 - i * 0.35
            pygame.draw.circle(sup, (120, 80, 45), (int(px), int(py)), int(r) + 2)
            pygame.draw.circle(sup, (160, 112, 62), (int(px), int(py)), int(r))
            pygame.draw.line(sup, (120, 80, 45), (px - r, py + 3), (px + r, py + 3), 2)
        topo = pontos[-1]

        # Folhas (arcos pontudos)
        for ang, comp in ((-170, 110), (-135, 95), (-60, 100), (-20, 115), (15, 90), (160, 90),
                          (-95, 70)):
            a = math.radians(ang)
            lado_a, lado_b = [], []
            for i in range(9):
                t = i / 8
                cx = topo[0] + math.cos(a) * comp * t
                cy = topo[1] + math.sin(a) * comp * t + (t * t) * 45
                larg = math.sin(t * math.pi) * 14
                nx, ny = -math.sin(a), math.cos(a)
                lado_a.append((cx + nx * larg, cy + ny * larg))
                lado_b.append((cx - nx * larg * 0.4, cy - ny * larg * 0.4))
            poligono = lado_a + lado_b[::-1]
            pygame.draw.polygon(sup, (50, 140, 60), poligono)
            pygame.draw.polygon(sup, (30, 100, 45), poligono, 2)

        # Cocos
        for dx, dy in ((-8, 6), (8, 8), (0, 14)):
            pygame.draw.circle(sup, (100, 65, 35), (int(topo[0] + dx), int(topo[1] + dy)), 8)
            pygame.draw.circle(sup, (140, 95, 55), (int(topo[0] + dx - 2), int(topo[1] + dy - 2)), 3)

    @staticmethod
    def _guarda_sol(sup, x, y):
        # Toalha listrada
        toalha = pygame.Rect(x - 90, y - 4, 120, 26)
        pygame.draw.rect(sup, (80, 170, 230), toalha, border_radius=4)
        for i in range(0, toalha.w, 20):
            pygame.draw.rect(sup, (255, 255, 255), (toalha.x + i, toalha.y, 10, toalha.h))
        pygame.draw.rect(sup, (40, 110, 170), toalha, 2, border_radius=4)

        # Mastro
        topo = (x - 14, y - 150)
        pygame.draw.line(sup, (90, 90, 100), (x, y + 10), topo, 5)

        # Lona em gomos vermelho/branco
        raio = 92
        n = 8
        for i in range(n):
            a1 = math.pi + i * math.pi / n
            a2 = math.pi + (i + 1) * math.pi / n
            pontos = [topo]
            for k in range(6):
                a = a1 + (a2 - a1) * k / 5
                pontos.append((topo[0] + math.cos(a) * raio, topo[1] + 18 + math.sin(a) * raio * 0.55))
            cor = (230, 60, 60) if i % 2 == 0 else (255, 250, 240)
            pygame.draw.polygon(sup, cor, pontos)
        pygame.draw.line(sup, (150, 40, 40), (topo[0] - raio, topo[1] + 18),
                         (topo[0] + raio, topo[1] + 18), 3)
        pygame.draw.circle(sup, (90, 90, 100), topo, 5)

    @classmethod
    def desenhar_icone(cls, sup, jogador):
        w, h = sup.get_size()
        ap_cpu = _aparencia_cpu(jogador.aparencia())
        jogador.desenhar(sup, (w * 0.25, h * 0.7), h * 0.34)
        jogador.desenhar(sup, (w * 0.75, h * 0.7), h * 0.34, aparencia=ap_cpu, espelhar=True)
        bola = pygame.transform.smoothscale(_bola_sup(), (int(h * 0.16), int(h * 0.16)))
        sup.blit(bola, bola.get_rect(center=(int(w * 0.36), int(h * 0.3))))

    # --------------------------------------------------------
    # PARTIDA
    # --------------------------------------------------------

    def reiniciar(self):
        cfg = CPU[self.opcao]
        self.cfg = cfg
        self.aparencia_cpu = _aparencia_cpu(self.jogador.aparencia())

        limite_rede = REDE_RAIO + MEIA_LARG + 2
        self.ovo = Ovo(CASA_JOGADOR, MEIA_LARG + 6, REDE_X - limite_rede,
                       self.jogador.aparencia(), False)
        self.cpu = Ovo(CASA_CPU, REDE_X + limite_rede, LARGURA - MEIA_LARG - 6,
                       self.aparencia_cpu, True)

        self.placar = [0, 0]             # [jogador, CPU]
        self.pontos = 0
        self.teclas = set()
        self.pulo_pedido = 0.0

        # CPU
        self.cpu_alvo = CASA_CPU
        self.cpu_relogio = 0.0
        self.cpu_erro = 0.0
        self.cpu_mira = 16.0
        self.cpu_decidiu_pulo = False
        self.lado_bola = -1

        self.angulo_bola = 0.0
        self.espera_rede = 0.0
        self._saque(jogador_saca=True)

    def _saque(self, jogador_saca):
        """Põe a bola parada no ar em cima de quem sofreu o ponto."""
        x = CASA_JOGADOR if jogador_saca else CASA_CPU
        self.bola = [float(x), float(Y_SAQUE), 0.0, 0.0]
        self.fase = "saque"
        self.relogio_fase = 0.0
        self.quem_pontuou = None
        for ovo, casa in ((self.ovo, CASA_JOGADOR), (self.cpu, CASA_CPU)):
            ovo.x = casa
            ovo.base = CHAO
            ovo.vx = ovo.vy = 0.0
            ovo.no_chao = True
        self._sortear_erro()

    def _sortear_erro(self):
        self.cpu_erro = random.uniform(-self.cfg["erro"], self.cfg["erro"])
        self.cpu_mira = random.uniform(*self.cfg["mira"])
        self.cpu_decidiu_pulo = False

    # --------------------------------------------------------
    # TECLADO (guardamos as teclas seguradas)
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
        if e.type == pygame.KEYDOWN and e.key in TECLAS_PULO:
            self.pulo_pedido = 0.12       # guarda o pedido um pouquinho

    def _segurando(self, teclas):
        return any(t in self.teclas for t in teclas)

    # --------------------------------------------------------
    # LÓGICA
    # --------------------------------------------------------

    def atualizar_jogo(self, dt):
        self.relogio_fase += dt

        # Controles do jogador
        direcao = 0
        if self._segurando(TECLAS_ESQ):
            direcao -= 1
        if self._segurando(TECLAS_DIR):
            direcao += 1
        self.ovo.vx = direcao * VEL_OVO

        if self.pulo_pedido > 0 or self._segurando(TECLAS_PULO):
            if self.ovo.pular():
                self.som("pulo", 0.7)
                self.pulo_pedido = 0.0
        self.pulo_pedido = max(0.0, self.pulo_pedido - dt)

        self._pensar_cpu(dt)

        # Física em passos pequenos
        passos = max(1, math.ceil(dt / SUB_PASSO))
        h = dt / passos
        for _ in range(passos):
            self.ovo.mover(h)
            self.cpu.mover(h)
            self._fisica_bola(h)

        self.ovo.animar(dt)
        self.cpu.animar(dt)
        self.espera_rede = max(0.0, self.espera_rede - dt)

        # Bola gira conforme anda para os lados
        self.angulo_bola -= math.degrees(self.bola[2] * dt / BOLA_R)

        # Troca de lado: nova chance de erro/pulo para a CPU
        lado = -1 if self.bola[0] < REDE_X else 1
        if lado != self.lado_bola:
            self.lado_bola = lado
            self._sortear_erro()

        if self.fase == "saque" and self.relogio_fase >= TEMPO_SAQUE:
            self.fase = "jogo"
        elif self.fase == "ponto" and self.relogio_fase >= TEMPO_PONTO:
            if max(self.placar) >= PONTOS_VITORIA:
                self._acabar()
            else:
                self._saque(jogador_saca=self.quem_pontuou == 1)

    def _fisica_bola(self, dt):
        b = self.bola

        if self.fase == "saque":
            # Parada no ar até o tempo acabar ou alguém encostar
            if self._colidir_ovo(self.ovo) or self._colidir_ovo(self.cpu):
                self.fase = "jogo"
            return

        if _mover_bola(b, dt) and abs(b[2]) + abs(b[3]) > 250 and self.fase == "jogo":
            if self.espera_rede <= 0:
                self.som("bater", 0.25)
                self.espera_rede = 0.15

        if self.fase == "jogo":
            self._colidir_ovo(self.ovo)
            self._colidir_ovo(self.cpu)
            # O ovo pode ter empurrado a bola contra a parede
            if b[0] < BOLA_R:
                b[0], b[2] = BOLA_R, abs(b[2])
            elif b[0] > LARGURA - BOLA_R:
                b[0], b[2] = LARGURA - BOLA_R, -abs(b[2])

        # Chão (areia)
        if b[1] + BOLA_R >= CHAO:
            b[1] = CHAO - BOLA_R
            if self.fase == "jogo":
                self._ponto(0 if b[0] > REDE_X else 1, b[0])
            # Quica fraquinho na areia e para
            b[3] = -abs(b[3]) * 0.35
            b[2] *= 0.6
            if abs(b[3]) < 60:
                b[3] = 0.0

    def _colidir_ovo(self, ovo):
        """Colisão bola x ovo (o ovo é uma elipse). Devolve True se bateu."""
        b = self.bola
        ea = MEIA_LARG + BOLA_R
        eb = ALTURA_OVO / 2 + BOLA_R
        dx = b[0] - ovo.x
        dy = b[1] - ovo.centro_y
        k = (dx / ea) ** 2 + (dy / eb) ** 2
        if k >= 1.0:
            return False

        # Normal da elipse no ponto de contato
        nx, ny = dx / (ea * ea), dy / (eb * eb)
        n = math.hypot(nx, ny)
        if n < 1e-9:
            nx, ny = 0.0, -1.0
        else:
            nx, ny = nx / n, ny / n

        # Empurra a bola para fora do ovo
        if k < 1e-6:
            b[0], b[1] = ovo.x, ovo.centro_y - eb
        else:
            s = 1.0 / math.sqrt(k)
            b[0] = ovo.x + dx * s + nx * 0.5
            b[1] = ovo.centro_y + dy * s + ny * 0.5

        # Velocidade relativa ao ovo
        rvx, rvy = b[2] - ovo.vx, b[3] - ovo.vy
        vn = rvx * nx + rvy * ny
        if vn >= 0:
            return True

        rvx -= (1 + QUIQUE_OVO) * vn * nx
        rvy -= (1 + QUIQUE_OVO) * vn * ny
        vx = rvx + ovo.vx * 0.9 + nx * EMPURRAO_LADO + random.uniform(-25, 25)
        vy = rvy + min(0.0, ovo.vy) * 0.6

        # Sempre sobe um pouco (se não bateu por baixo do ovo)
        if ny < 0.3:
            vy = min(vy, -IMPULSO_MIN)
        vy = max(vy, -VEL_MAX_SUBIDA)     # sem balões altos demais

        # Bola "parada" em cima da cabeça vai para o lado do adversário
        adversario = 1 if ovo is self.ovo else -1
        if abs(vx) < 60:
            vx += 90 * adversario

        # Limite de velocidade (a CPU fácil bate mais fraquinho)
        forca = self.cfg["forca"] if ovo is self.cpu else 1.0
        limite = VEL_MAX_BOLA * forca
        v = math.hypot(vx, vy)
        if v > limite:
            vx, vy = vx * limite / v, vy * limite / v

        # CORTADA: pulando perto da rede com a bola lá em cima
        if self._pode_cortar(ovo, ny):
            vx = adversario * VEL_CORTADA * forca
            vy = 140.0
            self.textos.adicionar(t("CORTADA!"), (b[0], b[1] - 40), LARANJA, 14)
            self.tremer(0.1)
        b[2], b[3] = vx, vy

        if ovo.espera_toque <= 0:
            self.som("bater", 0.8)
            ovo.espera_toque = 0.12
            self.particulas.explodir((b[0] - nx * BOLA_R, b[1] - ny * BOLA_R),
                                     [BRANCO, (255, 240, 180)], 6, 120, 0.35, (2, 4))
        ovo.vel_esticar -= 2.5
        if ovo is self.cpu:
            self.cpu_decidiu_pulo = False
        return True

    def _pode_cortar(self, ovo, ny):
        if ovo.no_chao or ny > -0.6 or ovo.vy > 200:
            return False
        if abs(ovo.x - REDE_X) > 170 or self.bola[1] > REDE_TOPO - 60:
            return False
        if ovo is self.cpu:
            return random.random() < self.cfg["cortada"]
        return True

    def _ponto(self, quem, x):
        """quem: 0 = jogador, 1 = CPU."""
        self.placar[quem] += 1
        self.pontos = self.placar[0]
        self.quem_pontuou = quem
        self.fase = "ponto"
        self.relogio_fase = 0.0

        cor_areia = [(240, 214, 150), (214, 180, 115), (250, 230, 180)]
        self.particulas.explodir((x, CHAO), cor_areia, 22, 240, 0.6, (2, 5))
        if quem == 0:
            self.som("ponto")
            self.textos.adicionar("+1", (x, CHAO - 60), AMARELO, 20)
        else:
            self.som("erro")
            self.tremer(0.15)

    def _acabar(self):
        p, c = self.placar
        venceu = p > c
        valor = p + (10 if venceu else 0)
        titulo = None if venceu else t("{nome} VENCEU!", nome=NOME_CPU)
        self.terminar(venceu=venceu, valor=valor, titulo=titulo,
                      linhas=[t("PLACAR: {a} x {b}", a=p, b=c), t("PONTOS: {n}", n=valor)])

    # --------------------------------------------------------
    # CPU (ROBERT)
    # --------------------------------------------------------

    def _prever_queda(self):
        """Simula a bola para descobrir onde ela chega na altura da cabeça."""
        b = list(self.bola)
        if self.fase == "saque":
            return b[0]
        altura = CHAO - ALTURA_OVO - BOLA_R * 0.5
        passo = 1 / 60
        for _ in range(240):
            _mover_bola(b, passo)
            if b[3] > 0 and b[1] >= altura:
                break
        return b[0]

    def _pensar_cpu(self, dt):
        cfg = self.cfg
        cpu = self.cpu
        b = self.bola

        if self.fase == "ponto":
            cpu.vx = 0.0
            return

        # Só decide de tempos em tempos (tempo de reação)
        self.cpu_relogio -= dt
        if self.cpu_relogio <= 0:
            self.cpu_relogio = cfg["reacao"]
            queda = self._prever_queda()
            if queda > REDE_X:
                # Fica um pouco à direita da bola para mandá-la para o outro lado
                self.cpu_alvo = queda + self.cpu_mira + self.cpu_erro
            else:
                self.cpu_alvo = CASA_CPU + math.sin(self.tempo) * 30

        dx = self.cpu_alvo - cpu.x
        if abs(dx) > 5:
            cpu.vx = math.copysign(cfg["vel"], dx)
        else:
            cpu.vx = 0.0

        # Pular quando a bola está perto e acima
        if cpu.no_chao and b[0] > REDE_X - BOLA_R and not self.cpu_decidiu_pulo:
            acima = cpu.centro_y - ALTURA_OVO / 2 - b[1]
            if abs(b[0] - cpu.x) < 70 and 40 < acima < 190 and b[3] > -150:
                self.cpu_decidiu_pulo = True
                if random.random() < cfg["pulo"] and cpu.pular():
                    self.som("pulo", 0.35)

    # --------------------------------------------------------
    # DESENHO
    # --------------------------------------------------------

    def _desenhar_ovo(self, tela, ovo):
        # Sombra na areia (menor quanto mais alto)
        altura = CHAO - ovo.base
        s = _sombra(MEIA_LARG * 2.1 * max(0.4, 1 - altura / 300))
        tela.blit(s, s.get_rect(center=(int(ovo.x), CHAO + 2)))

        sup = self.jogador.avatar(ALTURA_OVO, ovo.aparencia)
        if ovo.espelhar:
            sup = pygame.transform.flip(sup, True, False)

        e = ovo.esticar
        if abs(e) > 0.02:
            w, h = sup.get_size()
            sup = pygame.transform.smoothscale(
                sup, (max(1, round(w * (1 - 0.1 * e))), max(1, round(h * (1 + 0.13 * e)))))

        # Posiciona pelo "pé" do ovo (o corpo vai de 14% a 88% da imagem)
        w, h = sup.get_size()
        cx = 0.515 if ovo.espelhar else 0.485
        tela.blit(sup, (round(ovo.x - w * cx), round(ovo.base - h * 0.88)))

    def desenhar_jogo(self, tela):
        tela.blit(self.fundo(self.jogador), (0, 0))
        t = self.tempo

        # Ondas animadas (poucas linhas por frame)
        for i in range(4):
            y0 = HORIZONTE + 22 + i * 30
            fase = t * (0.8 + i * 0.3) + i * 1.7
            pontos = [(x, y0 + math.sin(x * 0.018 + fase) * (2 + i)) for x in range(0, LARGURA + 32, 32)]
            pygame.draw.lines(tela, (170, 225, 245), False, pontos, 2)
        espuma = AREIA_Y - 4 + math.sin(t * 1.3) * 3
        pontos = [(x, espuma + math.sin(x * 0.03 + t * 2) * 3) for x in range(0, LARGURA + 32, 32)]
        pygame.draw.lines(tela, (250, 255, 255), False, pontos, 4)

        # Sombra da bola (menor quanto mais alta)
        b = self.bola
        altura = max(0.0, CHAO - BOLA_R - b[1])
        s = _sombra(BOLA_R * 2.2 * max(0.3, 1 - altura / 520))
        tela.blit(s, s.get_rect(center=(int(b[0]), CHAO + 2)))

        # Ovos
        self._desenhar_ovo(tela, self.ovo)
        self._desenhar_ovo(tela, self.cpu)

        # Bola (piscando parada no ar durante o saque)
        sup = _bola_sup()
        if self.angulo_bola:
            sup = pygame.transform.rotate(sup, self.angulo_bola % 360)
        tela.blit(sup, sup.get_rect(center=(round(b[0]), round(b[1]))))
        if self.fase == "saque" and self.estado == "jogando":
            raio = BOLA_R + 6 + int(abs(math.sin(t * 6)) * 5)
            pygame.draw.circle(tela, BRANCO, (round(b[0]), round(b[1])), raio, 2)

        self.particulas.desenhar(tela)
        self.textos.desenhar(tela)

        # Aviso de ponto
        if self.fase == "ponto" and self.estado == "jogando":
            escala = min(1.0, self.relogio_fase * 6)
            tam = 24 if escala < 1 else 32
            ui.desenhar_texto(tela, _t("PONTO!"), (LARGURA // 2, 210), tam, AMARELO, "center")
            nome = self._nome_jogador() if self.quem_pontuou == 0 else NOME_CPU
            cor = (140, 255, 140) if self.quem_pontuou == 0 else (255, 150, 150)
            ui.desenhar_texto(tela, nome, (LARGURA // 2, 254), 16, cor, "center")

    def _nome_jogador(self):
        return (self.jogador.nome or t("VOCÊ")).strip() or t("VOCÊ")

    def desenhar_hud(self, tela):
        """Placar grande no topo: JOGADOR  3 x 2  ROBERT."""
        p, c = self.placar
        caixa = pygame.Rect(0, 12, 620, 56)
        caixa.centerx = LARGURA // 2
        ui.painel(tela, caixa, (20, 24, 40), BRANCO, 14, 3, sombra=False)

        nome = self._nome_jogador()
        tam = 14 if len(nome) <= 10 else 12
        ui.desenhar_texto(tela, nome, (caixa.centerx - 92, caixa.centery), tam,
                          (140, 255, 140), "midright")
        ui.desenhar_texto(tela, NOME_CPU, (caixa.centerx + 92, caixa.centery), 14,
                          (255, 160, 160), "midleft")
        ui.desenhar_texto(tela, str(p), (caixa.centerx - 34, caixa.centery + 2), 28, AMARELO, "center")
        ui.desenhar_texto(tela, "×", (caixa.centerx, caixa.centery + 2), 20, BRANCO, "center")
        ui.desenhar_texto(tela, str(c), (caixa.centerx + 34, caixa.centery + 2), 28, AMARELO, "center")

        # Dificuldade e "ponto decisivo"
        rotulo = ui.texto(t(self.OPCOES[self.opcao]), 12)
        fundo = pygame.Rect(12, 24, rotulo.get_width() + 20, 32)
        ui.painel(tela, fundo, (20, 24, 40), BRANCO, 10, 2, sombra=False)
        tela.blit(rotulo, rotulo.get_rect(center=fundo.center))
        if self.estado == "jogando" and max(p, c) == PONTOS_VITORIA - 1 and self.fase != "ponto":
            if int(self.tempo * 3) % 2 == 0:
                ui.desenhar_texto(tela, t("PONTO DECISIVO!"), (LARGURA // 2, caixa.bottom + 12), 12,
                                  AMARELO, "midtop")
