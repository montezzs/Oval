import math
import random

import pygame

from settings import *
from core import ui
from jogos.base import MiniJogo

# ============================================================
# OVO NA COLHER
# ============================================================
# A clássica corrida do ovo na colher da festa junina! O seu ovo
# vai numa colher e você precisa andar o mais longe possível sem
# deixar ele cair. Incline a colher para segurar o ovo no meio.
# Pedrinhas, poças, vento, borboletas e passarinhos atrapalham.
# Quanto mais rápido você anda, mais longe chega... e mais o ovo
# sacode!

# ------------------------------------------------------------
# FÍSICA (tudo num lugar só para facilitar o ajuste)
# ------------------------------------------------------------
PIVO = (512, 520)               # centro da concha da colher
MEIA_CONCHA = 75                # concha de 150 x 40
ALTURA_CONCHA = 40
LIMITE_QUEDA = 70               # |s| maior que isso: o ovo cai
ACEL_INCLINACAO = 900           # s'' = 900 * sen(φ) ...
AMORTECIMENTO = 2.0             # ... - 2 * s'
CONCAVA = 0.8                   # a concha é funda: puxa o ovo de leve para o meio
VEL_GIRO = 90.0                 # graus/s ao apertar ←/→
VOLTA_GIRO = 10.0               # graus/s voltando ao 0 sozinho
LIMITE_GIRO = 25.0              # graus

VEL_MIN = 80.0                  # px/s andando
VEL_MAX = 260.0
ACEL_ANDAR = 150.0              # px/s² segurando ↑
FREIO = 260.0                   # px/s² segurando ↓
PX_POR_METRO = 40
METROS_CHECKPOINT = 100
BONUS_CHECKPOINT = 25

SOLAVANCO = 0.8                 # pedrinha: Δs' = ±(0.4..1) * vel * SOLAVANCO
BALANCO_PASSO = 0.14            # sacudida contínua dos passos (proporcional à vel)
FORCA_VENTO = 120.0
TEMPO_VENTO = 3.0
AVISO_VENTO = 1.0
TEMPO_POCA = 1.0
GIRO_POCA = 110.0               # graus/s da oscilação na poça
COCEGAS = 70.0                  # borboleta: ruído na aceleração
TEMPO_BORBOLETA = 2.0
PESO_PASSARINHO = 110.0         # passarinho na ponta da colher
TEMPO_PASSARINHO = 2.0

# ------------------------------------------------------------
# CENÁRIO
# ------------------------------------------------------------
ALTURA_OVO = 60
from core.jogador import BOCA_ABERTA as BOCA_MEDO   # boca em "O"
GRAMA_Y = 562
PISTA_Y = 612
X_PE = 440                      # onde os pés de quem carrega passam pelas coisas do chão
OMBRO = (250, 790)              # o braço vem de fora da tela
PONTA_CABO = (-196, 30)         # onde a mão segura (coordenada local da colher)

TECLAS_ESQ = (pygame.K_LEFT, pygame.K_a)
TECLAS_DIR = (pygame.K_RIGHT, pygame.K_d)
TECLAS_ACEL = (pygame.K_UP, pygame.K_w)
TECLAS_FREIO = (pygame.K_DOWN, pygame.K_s)

CORES_BANDEIRA = [(255, 80, 80), (255, 220, 60), (80, 180, 255), (120, 220, 90)]

# Ladrilhos do cenário que rolam (largura da repetição)
LADO_PISTA = 512
LADO_BANDEIRAS = 512
LADO_BARRACAS = 1024
Y_BARRACAS = 330                # topo do ladrilho das barracas
PARALLAX_BANDEIRAS = 0.25
PARALLAX_BARRACAS = 0.45


def _girar(x, y, ang):
    """Gira o ponto (x, y) pelo ângulo (radianos)."""
    c, s = math.cos(ang), math.sin(ang)
    return x * c - y * s, x * s + y * c


# ============================================================
# LADRILHOS DO CENÁRIO (desenhados uma vez só)
# ============================================================

_ladrilhos = {}


def _ladrilho_pista():
    sup = _ladrilhos.get("pista")
    if sup is not None:
        return sup
    h = ALTURA - PISTA_Y
    sup = pygame.Surface((LADO_PISTA, h))
    sup.fill((190, 140, 90))
    rnd = random.Random(8)
    # Marcas de terra e pedrinhas (desenhadas "dando a volta" para emendar)
    for _ in range(90):
        x, y = rnd.randrange(LADO_PISTA), rnd.randrange(8, h)
        w = rnd.randint(10, 40)
        for dx in (-LADO_PISTA, 0, LADO_PISTA):
            pygame.draw.line(sup, (172, 124, 78), (x + dx, y), (x + dx + w, y), 2)
    for _ in range(60):
        x, y = rnd.randrange(LADO_PISTA), rnd.randrange(10, h - 4)
        r = rnd.randint(2, 4)
        for dx in (-LADO_PISTA, 0, LADO_PISTA):
            pygame.draw.circle(sup, (120, 120, 120), (x + dx, y + 1), r)
            pygame.draw.circle(sup, (150, 150, 150), (x + dx, y), r)
    # Borda da grama por cima da pista
    for x in range(0, LADO_PISTA, 6):
        pygame.draw.line(sup, (70, 160, 60), (x, 0), (x + 3, 6), 3)
    pygame.draw.line(sup, (150, 104, 66), (0, 8), (LADO_PISTA, 8), 2)
    _ladrilhos["pista"] = sup.convert()
    return _ladrilhos["pista"]


def _ladrilho_bandeiras():
    sup = _ladrilhos.get("bandeiras")
    if sup is not None:
        return sup
    sup = pygame.Surface((LADO_BANDEIRAS, 150), pygame.SRCALPHA)
    for fileira, (y0, flecha, fase) in enumerate(((8, 44, 0), (40, 56, LADO_BANDEIRAS // 2))):
        pontos = []
        for i in range(0, LADO_BANDEIRAS + 1, 8):
            x = (i + fase) % LADO_BANDEIRAS
            t = x / LADO_BANDEIRAS
            y = y0 + flecha * 4 * t * (1 - t)
            pontos.append((x, y))
        pontos.sort()
        pygame.draw.lines(sup, (70, 50, 40), False, pontos, 2)
        for k, i in enumerate(range(8, LADO_BANDEIRAS, 26)):
            x = i
            t = ((x - fase) % LADO_BANDEIRAS) / LADO_BANDEIRAS
            y = y0 + flecha * 4 * t * (1 - t)
            cor = CORES_BANDEIRA[(k + fileira) % 4]
            tri = [(x - 9, y), (x + 9, y), (x, y + 22)]
            pygame.draw.polygon(sup, ui.escurecer(cor, 50), [(p[0] + 1, p[1] + 2) for p in tri])
            pygame.draw.polygon(sup, cor, tri)
            pygame.draw.line(sup, ui.clarear(cor, 70), (x - 6, y + 2), (x - 1, y + 13), 2)
    _ladrilhos["bandeiras"] = sup.convert_alpha()
    return _ladrilhos["bandeiras"]


# Barracas: (x, largura, rótulo, cor do telhado)
BARRACAS = [(30, 200, "PIPOCA", (230, 60, 60)), (300, 190, "MILHO", (60, 120, 220)),
            (560, 210, "DOCES", (230, 60, 60))]
FOGUEIRA_X = 880                # dentro do ladrilho das barracas
FOGUEIRA_Y = 238


def _ladrilho_barracas():
    sup = _ladrilhos.get("barracas")
    if sup is not None:
        return sup
    h = GRAMA_Y + 20 - Y_BARRACAS
    sup = pygame.Surface((LADO_BARRACAS, h), pygame.SRCALPHA)
    base = h - 20
    for x, w, rotulo, cor in BARRACAS:
        corpo = pygame.Rect(x, base - 130, w, 130)
        # Postes e fundo
        pygame.draw.rect(sup, (120, 80, 50), (corpo.x + 6, corpo.y, 8, 130))
        pygame.draw.rect(sup, (120, 80, 50), (corpo.right - 14, corpo.y, 8, 130))
        pygame.draw.rect(sup, (250, 235, 200), (corpo.x + 14, corpo.y + 10, w - 28, 70))
        pygame.draw.rect(sup, (200, 180, 150), (corpo.x + 14, corpo.y + 10, w - 28, 70), 2)
        # Balcão de madeira
        balcao = pygame.Rect(corpo.x, base - 50, w, 50)
        pygame.draw.rect(sup, (170, 110, 60), balcao)
        for yy in range(balcao.y + 12, balcao.bottom, 12):
            pygame.draw.line(sup, (140, 90, 50), (balcao.x, yy), (balcao.right, yy), 2)
        pygame.draw.rect(sup, (110, 70, 40), balcao, 3)
        pygame.draw.rect(sup, (200, 140, 80), (balcao.x - 6, balcao.y - 8, w + 12, 10))
        # Toldo listrado vermelho/branco (ou azul/branco)
        toldo = pygame.Rect(corpo.x - 12, corpo.y - 34, w + 24, 36)
        faixas = 8
        fw = toldo.w / faixas
        for i in range(faixas):
            c = cor if i % 2 == 0 else (255, 255, 255)
            pygame.draw.rect(sup, c, (toldo.x + i * fw, toldo.y, fw + 1, toldo.h))
            # Bico do toldo
            cx = toldo.x + i * fw + fw / 2
            pygame.draw.polygon(sup, c, [(toldo.x + i * fw, toldo.bottom - 1),
                                         (toldo.x + (i + 1) * fw, toldo.bottom - 1),
                                         (cx, toldo.bottom + 12)])
        pygame.draw.rect(sup, ui.escurecer(cor, 70), toldo, 2)
        # Placa
        placa = pygame.Rect(0, 0, w - 50, 24)
        placa.midtop = (corpo.centerx, toldo.y - 30)
        pygame.draw.rect(sup, (90, 60, 40), placa.inflate(6, 6), border_radius=6)
        pygame.draw.rect(sup, (255, 230, 150), placa, border_radius=5)
        txt = ui.texto(rotulo, 12, (150, 50, 40), sombra=False)
        sup.blit(txt, txt.get_rect(center=placa.center))
        # Coisinhas no balcão
        for i in range(3):
            px = balcao.x + 30 + i * (w - 60) / 2
            pygame.draw.circle(sup, (255, 240, 200), (int(px), balcao.y - 14), 9)
            pygame.draw.circle(sup, (255, 200, 60), (int(px), balcao.y - 16), 5)
        # Lampadinhas no toldo
        for i in range(6):
            lx = toldo.x + 10 + i * (toldo.w - 20) / 5
            pygame.draw.circle(sup, (255, 240, 150), (int(lx), toldo.bottom + 16), 4)

    # Toras da fogueira (as chamas são animadas)
    fx, fy = FOGUEIRA_X, FOGUEIRA_Y
    pygame.draw.ellipse(sup, (60, 40, 30), (fx - 70, fy - 6, 140, 22))
    for ang in (-24, 24, -8, 8):
        a = math.radians(ang)
        x1, y1 = fx - math.sin(a) * 60, fy + 6
        x2, y2 = fx + math.sin(a) * 10, fy - 50
        pygame.draw.line(sup, (80, 50, 30), (x1, y1), (x2, y2), 12)
        pygame.draw.line(sup, (120, 80, 50), (x1, y1), (x2, y2), 6)
    for dx in (-54, -30, 30, 54):
        pygame.draw.circle(sup, (110, 110, 120), (fx + dx, fy + 8), 9)
        pygame.draw.circle(sup, (150, 150, 160), (fx + dx - 2, fy + 6), 4)
    _ladrilhos["barracas"] = sup.convert_alpha()
    return _ladrilhos["barracas"]


# ============================================================
# COISAS DO CHÃO (pedra e poça)
# ============================================================

class CoisaChao:

    def __init__(self, tipo, x_mundo):
        self.tipo = tipo
        self.x_mundo = x_mundo          # posição no mundo (px percorridos)
        self.y = random.randint(648, 690)
        self.passou = False
        self.forma = [(random.randint(-10, 10), random.randint(-3, 3), random.randint(5, 9))
                      for _ in range(3)]


class OvoColher(MiniJogo):

    ID = "ovo_colher"
    TITULO = "OVO NA COLHER"
    TITULO_CURTO = "COLHER"
    DESCRICAO = "A corrida da festa junina! Ande o mais longe que puder equilibrando o seu ovo na colher."
    COR = (230, 120, 60)
    INSTRUCOES = [
        "Equilibre o ovo na colher e ande o mais longe!",
        "Incline a colher para o ovo voltar ao meio.",
        "Mais rápido = mais metros, mas sacode mais!",
        "Cuidado: pedras, poças, vento e bichinhos!",
        "←→/AD inclina • ↑↓/WS anda • mouse",
    ]
    MOEDAS_POR = 24
    MOEDAS_MAX = 26

    TRILHA = dict(bpm=120, tom="D", escala="mixolidia", lead="quadrada", duty=0.5,
                  envelope="normal", baixo="oompah", onda_baixo="triangulo",
                  acomp="contratempo", onda_acomp="quadrada", bateria="baiao",
                  energia=0.6, eco=(0.12, 0.15))

    # --------------------------------------------------------
    # CENÁRIO: festa junina ao entardecer
    # --------------------------------------------------------

    @classmethod
    def criar_fundo(cls, jogador):
        sup = ui.gradiente(LARGURA, GRAMA_Y, (120, 80, 160), (255, 170, 100))
        rnd = random.Random(5)

        # Estrelinhas aparecendo no alto
        for _ in range(40):
            x, y = rnd.randrange(LARGURA), rnd.randrange(10, 180)
            c = rnd.choice([(255, 255, 230), (230, 220, 255)])
            sup.set_at((x, y), c)
            if rnd.random() < 0.3:
                pygame.draw.circle(sup, c, (x, y), 1)

        # Lua e nuvens rosadas
        pygame.draw.circle(sup, (255, 250, 220), (250, 190), 30)
        pygame.draw.circle(sup, ui.misturar((120, 80, 160), (255, 170, 100), 190 / GRAMA_Y), (264, 180), 27)
        for cx, cy, esc in ((120, 290, 1.0), (470, 230, 1.3), (860, 200, 1.1), (640, 310, 0.8)):
            for dx, dy, r in ((-40, 6, 22), (-12, -6, 30), (22, 0, 26), (50, 8, 18)):
                pygame.draw.circle(sup, (255, 190, 170), (int(cx + dx * esc), int(cy + dy * esc + 4)),
                                   int(r * esc))
            for dx, dy, r in ((-40, 6, 22), (-12, -6, 30), (22, 0, 26), (50, 8, 18)):
                pygame.draw.circle(sup, (250, 170, 170), (int(cx + dx * esc), int(cy + dy * esc + 10)),
                                   int(r * esc * 0.8))

        # Sol se pondo com halo
        halo = pygame.Surface((260, 260), pygame.SRCALPHA)
        for r, a in ((130, 30), (100, 45), (76, 70)):
            pygame.draw.circle(halo, (255, 210, 120, a), (130, 130), r)
        sup.blit(halo, (700 - 130, 400 - 130))
        pygame.draw.circle(sup, (255, 190, 90), (700, 400), 56)
        pygame.draw.circle(sup, (255, 220, 130), (700, 400), 44)

        # Morros e árvores distantes
        pontos = [(0, GRAMA_Y)]
        for x in range(0, LARGURA + 40, 40):
            pontos.append((x, 450 + math.sin(x * 0.008) * 22 + math.sin(x * 0.021) * 10))
        pontos.append((LARGURA, GRAMA_Y))
        pygame.draw.polygon(sup, (140, 90, 150), pontos)
        for _ in range(26):
            x = rnd.randrange(LARGURA)
            y = 470 + rnd.randint(-10, 20)
            r = rnd.randint(14, 26)
            pygame.draw.circle(sup, (110, 70, 130), (x, y), r)
            pygame.draw.rect(sup, (90, 60, 100), (x - 3, y, 6, r + 10))
        # Igrejinha no morro
        ig = pygame.Rect(150, 400, 60, 70)
        pygame.draw.rect(sup, (100, 64, 120), ig)
        pygame.draw.polygon(sup, (100, 64, 120), [(ig.x - 6, ig.y), (ig.centerx, ig.y - 34),
                                                  (ig.right + 6, ig.y)])
        pygame.draw.rect(sup, (100, 64, 120), (ig.centerx - 9, ig.y - 70, 18, 40))
        pygame.draw.line(sup, (100, 64, 120), (ig.centerx, ig.y - 92), (ig.centerx, ig.y - 70), 3)
        pygame.draw.line(sup, (100, 64, 120), (ig.centerx - 7, ig.y - 84), (ig.centerx + 7, ig.y - 84), 3)
        pygame.draw.rect(sup, (255, 210, 120), (ig.centerx - 7, ig.y + 34, 14, 22), border_top_left_radius=7,
                         border_top_right_radius=7)

        # Grama da frente
        final = pygame.Surface((LARGURA, ALTURA))
        final.blit(sup, (0, 0))
        pygame.draw.rect(final, (90, 190, 80), (0, GRAMA_Y, LARGURA, ALTURA - GRAMA_Y))
        for _ in range(300):
            x, y = rnd.randrange(LARGURA), rnd.randrange(GRAMA_Y + 4, PISTA_Y + 10)
            pygame.draw.line(final, (70, 160, 60), (x, y), (x + rnd.randint(-2, 2), y - 6), 2)
        pygame.draw.line(final, (60, 150, 60), (0, GRAMA_Y), (LARGURA, GRAMA_Y), 2)
        return final

    @classmethod
    def desenhar_icone(cls, sup, jogador):
        w, h = sup.get_size()
        # Bandeirinhas no topo
        for i in range(9):
            x = 8 + i * (w - 16) / 8
            t = i / 8
            y = 6 + 14 * 4 * t * (1 - t)
            pygame.draw.polygon(sup, CORES_BANDEIRA[i % 4], [(x - 6, y), (x + 6, y), (x, y + 14)])
        # Colher inclinada com o ovo
        cx, cy = w // 2 + 6, int(h * 0.68)
        ang = math.radians(-8)
        pts = [_girar(math.cos(a) * 46, math.sin(a) * 12, ang) for a in
               [i * math.tau / 24 for i in range(24)]]
        cabo = [_girar(-44, 0, ang), _girar(-96, 12, ang)]
        pygame.draw.line(sup, (120, 120, 140), (cx + cabo[0][0], cy + cabo[0][1]),
                         (cx + cabo[1][0], cy + cabo[1][1]), 9)
        pygame.draw.line(sup, (200, 200, 215), (cx + cabo[0][0], cy + cabo[0][1]),
                         (cx + cabo[1][0], cy + cabo[1][1]), 5)
        pygame.draw.polygon(sup, (200, 200, 215), [(cx + x, cy + y) for x, y in pts])
        jogador.desenhar(sup, (cx - 4, cy - 30), h * 0.36, angulo=10)
        frente = [(cx + x, cy + y) for x, y in pts[:13]]
        pygame.draw.polygon(sup, (200, 200, 215), frente)
        pygame.draw.polygon(sup, (120, 120, 140), [(cx + x, cy + y) for x, y in pts], 2)
        pygame.draw.circle(sup, (255, 210, 170), (int(cx + cabo[1][0]), int(cy + cabo[1][1])), 9)

    # --------------------------------------------------------
    # PARTIDA
    # --------------------------------------------------------

    def reiniciar(self):
        self.teclas = set()
        self.mouse_x = None             # inclinação pelo mouse (None = teclado)
        self.mouse_botoes = set()

        # Colher e ovo
        self.phi = 0.0                  # inclinação da colher (graus)
        self.s = 0.0                    # posição do ovo na colher
        self.vs = 0.0                   # velocidade do ovo na colher
        self.pulo_colher = 0.0          # sacudida visual (pedra)
        self.vel_pulo = 0.0

        # Caminhada
        self.vel = VEL_MIN
        self.dist = 0.0                 # px percorridos
        self.fase_passo = 0.0
        self.checkpoints = 0
        self.proximo_check = METROS_CHECKPOINT * PX_POR_METRO

        # Eventos
        self.coisas = []                # pedras e poças no chão
        self.proximo_evento = 2.5
        self.poca = 0.0                 # tempo restante escorregando
        self.poca_fase = 0.0
        self.vento = 0.0                # tempo restante de vento
        self.aviso_vento = 0.0          # aviso antes do vento
        self.dir_vento = 1
        self.riscos_vento = []
        self.borboleta = None           # dict com estado da borboleta
        self.passarinho = None
        self.ruido = 0.0
        self.tempo_ruido = 0.0

        # Queda
        self.caindo = False
        self.quebrado = False
        self.tempo_queda = 0.0
        self.lento = 0.0
        self.ovo_pos = (0.0, 0.0)
        self.ovo_vel = (0.0, 0.0)
        self.ovo_ang = 0.0
        self.ovo_giro = 0.0
        self.cacos = []
        self.suor = 0.0
        self.festa = 0.0                # plateia comemorando
        self.oooh = 0.0                 # plateia lamentando

    # --------------------------------------------------------
    # CONTROLES
    # --------------------------------------------------------

    def evento(self, e):
        # Acompanha as teclas em qualquer estado (para não "grudar" na pausa)
        if e.type == pygame.KEYDOWN:
            self.teclas.add(e.key)
        elif e.type == pygame.KEYUP:
            self.teclas.discard(e.key)
        elif e.type == pygame.MOUSEBUTTONUP:
            self.mouse_botoes.discard(e.button)
        elif e.type == pygame.WINDOWFOCUSLOST:
            self.teclas.clear()
            self.mouse_botoes.clear()
        super().evento(e)

    def evento_jogo(self, e):
        if e.type == pygame.MOUSEMOTION:
            if not self.botao_pausa.collidepoint(e.pos):
                self.mouse_x = e.pos[0]
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button in (1, 3):
            if not self.botao_pausa.collidepoint(e.pos):
                self.mouse_botoes.add(e.button)
                self.mouse_x = e.pos[0]
        elif e.type == pygame.KEYDOWN and e.key in TECLAS_ESQ + TECLAS_DIR:
            self.mouse_x = None

    def _apertando(self, teclas):
        return any(t in self.teclas for t in teclas)

    # --------------------------------------------------------
    # LÓGICA
    # --------------------------------------------------------

    @property
    def metros(self):
        return int(self.dist / PX_POR_METRO)

    def _fator_eventos(self):
        """A cada 50 m os eventos ficam 10% mais frequentes."""
        return 1.0 + 0.1 * (self.metros // 50)

    def atualizar_jogo(self, dt):
        # Câmera lenta no começo da queda
        if self.caindo and self.lento > 0:
            self.lento -= dt
            dt *= 0.3

        self._andar(dt)
        self._eventos(dt)

        if self.caindo or self.quebrado:
            self._atualizar_queda(dt)
        else:
            self._girar_colher(dt)
            # Sub-passos para a física ficar estável
            passos = max(1, int(math.ceil(dt / (1 / 120))))
            for _ in range(passos):
                self._fisica(dt / passos)
                if abs(self.s) > LIMITE_QUEDA:
                    self._cair()
                    break

        # Mola da sacudida da colher
        self.vel_pulo += (-400 * self.pulo_colher - 16 * self.vel_pulo) * dt
        self.pulo_colher += self.vel_pulo * dt

        self.festa = max(0.0, self.festa - dt)
        self.oooh = max(0.0, self.oooh - dt)

        if not (self.caindo or self.quebrado):
            self.pontos = self.metros + BONUS_CHECKPOINT * self.checkpoints
            self._suar(dt)

    def _andar(self, dt):
        if self.caindo or self.quebrado:
            self.vel = max(0.0, self.vel - 500 * dt)
        else:
            if self._apertando(TECLAS_ACEL) or 1 in self.mouse_botoes:
                self.vel = min(VEL_MAX, self.vel + ACEL_ANDAR * dt)
            if self._apertando(TECLAS_FREIO) or 3 in self.mouse_botoes:
                self.vel = max(VEL_MIN, self.vel - FREIO * dt)

        self.dist += self.vel * dt
        self.fase_passo += dt * math.tau * (0.9 + self.vel / 110)

        # Placa de checkpoint
        if self.dist >= self.proximo_check and not (self.caindo or self.quebrado):
            self.checkpoints += 1
            self.proximo_check += METROS_CHECKPOINT * PX_POR_METRO
            self.festa = 1.6
            self.som("bandeira")
            self.textos.adicionar(f"{self.checkpoints * METROS_CHECKPOINT} m! +{BONUS_CHECKPOINT}",
                                  (LARGURA // 2, 250), AMARELO, 24)
            for x in range(80, LARGURA, 160):
                self.particulas.explodir((x, 120), CORES_BANDEIRA + [BRANCO], 10, 260, 1.2, (3, 6))

    def _girar_colher(self, dt):
        if self.mouse_x is not None:
            alvo = max(-LIMITE_GIRO, min(LIMITE_GIRO, (self.mouse_x - PIVO[0]) / 260 * LIMITE_GIRO))
            passo = VEL_GIRO * 1.5 * dt
            self.phi += max(-passo, min(passo, alvo - self.phi))
        else:
            direcao = 0
            if self._apertando(TECLAS_ESQ):
                direcao -= 1
            if self._apertando(TECLAS_DIR):
                direcao += 1
            if direcao:
                self.phi += direcao * VEL_GIRO * dt
            else:
                # Volta devagar para o 0
                passo = VOLTA_GIRO * dt
                self.phi -= max(-passo, min(passo, self.phi))

        # Poça: a colher escorrega e oscila sozinha
        if self.poca > 0:
            self.poca_fase += dt
            self.phi += GIRO_POCA * math.cos(self.poca_fase * math.tau * 2.5) * dt
        self.phi = max(-LIMITE_GIRO, min(LIMITE_GIRO, self.phi))

    def _fisica(self, dt):
        acel = ACEL_INCLINACAO * math.sin(math.radians(self.phi))
        acel -= AMORTECIMENTO * self.vs
        acel -= CONCAVA * self.s

        # Balanço dos passos: quanto mais rápido, mais sacode
        acel += self.vel * BALANCO_PASSO * math.sin(self.fase_passo * 0.5)

        if self.vento > 0:
            rampa = min(1.0, (TEMPO_VENTO - self.vento) / 0.4, self.vento / 0.4)
            acel += self.dir_vento * FORCA_VENTO * rampa
        if self.borboleta and self.borboleta["fase"] == "pousada":
            acel += self.ruido
        if self.passarinho and self.passarinho["fase"] == "pousado":
            acel += PESO_PASSARINHO

        self.vs += acel * dt
        self.s += self.vs * dt

    def _suar(self, dt):
        """O ovo sua de nervoso quando está perto da borda."""
        if abs(self.s) <= 50:
            return
        self.suor -= dt
        if self.suor <= 0:
            self.suor = 0.12
            x, y = self._pos_ovo()
            lado = random.choice((-1, 1))
            self.particulas.explodir((x + lado * 20, y - 24), [(120, 190, 255), (200, 230, 255)],
                                     1, 90, 0.5, (3, 4))

    # --------------------------------------------------------
    # EVENTOS (pedra, poça, vento, borboleta, passarinho)
    # --------------------------------------------------------

    def _eventos(self, dt):
        vivo = not (self.caindo or self.quebrado)

        # Coisas do chão passando pelos pés
        for c in self.coisas:
            x = self._x_tela(c.x_mundo)
            if not c.passou and x <= X_PE:
                c.passou = True
                if vivo:
                    self._pisar(c)
        self.coisas = [c for c in self.coisas if self._x_tela(c.x_mundo) > -80]

        self.poca = max(0.0, self.poca - dt)
        self.tempo_ruido -= dt
        if self.tempo_ruido <= 0:
            self.tempo_ruido = 0.09
            self.ruido = random.uniform(-COCEGAS, COCEGAS)

        # Vento
        if self.aviso_vento > 0:
            self.aviso_vento -= dt
            if self.aviso_vento <= 0:
                self.vento = TEMPO_VENTO
                self.som("asa", 0.6)
        elif self.vento > 0:
            self.vento -= dt
            if random.random() < dt * 45:
                y = random.randint(140, 540)
                x = -60 if self.dir_vento > 0 else LARGURA + 60
                self.riscos_vento.append([x, y, random.randint(40, 110), random.uniform(700, 1000)])
        for r in self.riscos_vento:
            r[0] += self.dir_vento * r[3] * dt
        self.riscos_vento = [r for r in self.riscos_vento if -200 < r[0] < LARGURA + 200]

        self._atualizar_borboleta(dt)
        self._atualizar_passarinho(dt)

        if not vivo:
            return

        # Sorteio do próximo evento
        self.proximo_evento -= dt
        if self.proximo_evento <= 0:
            self._novo_evento()
            base = 3.2 / self._fator_eventos()
            self.proximo_evento = max(0.9, base * random.uniform(0.7, 1.3))

    def _novo_evento(self):
        no_ar = self.vento > 0 or self.aviso_vento > 0 or self.borboleta or self.passarinho
        if self.metros < 15:
            tipos, pesos = ["pedra"], [1]
        elif no_ar:
            tipos, pesos = ["pedra", "poca"], [3, 1]
        else:
            tipos = ["pedra", "poca", "vento", "borboleta", "passarinho"]
            pesos = [40, 15, 15, 15, 15]
        tipo = random.choices(tipos, pesos)[0]

        if tipo in ("pedra", "poca"):
            x_mundo = self.dist + (LARGURA + 60 - X_PE)
            # Não deixa duas coisas do chão coladas
            if any(abs(c.x_mundo - x_mundo) < 150 for c in self.coisas):
                return
            self.coisas.append(CoisaChao(tipo, x_mundo))
        elif tipo == "vento":
            self.dir_vento = random.choice((-1, 1))
            self.aviso_vento = AVISO_VENTO
            self.som("revelar", 0.6)
        elif tipo == "borboleta":
            lado = random.choice((-1, 1))
            self.borboleta = dict(fase="chegando", t=0.0, x=LARGURA / 2 + lado * 560, y=160.0,
                                  x0=LARGURA / 2 + lado * 560, y0=160.0,
                                  cor=random.choice([(255, 150, 220), (170, 130, 255), (255, 200, 60),
                                                     (120, 210, 255)]))
        else:
            self.passarinho = dict(fase="chegando", t=0.0, x=LARGURA + 60.0, y=150.0,
                                   x0=LARGURA + 60.0, y0=150.0)

    def _x_tela(self, x_mundo):
        return X_PE + (x_mundo - self.dist)

    def _pisar(self, c):
        if c.tipo == "pedra":
            forca = random.uniform(0.4, 1.0) * random.choice((-1, 1))
            self.vs += forca * self.vel * SOLAVANCO
            self.vel_pulo -= 60 + self.vel * 0.5
            self.som("bater", 0.5)
            self.particulas.explodir((X_PE, c.y), [(200, 160, 110), (170, 130, 90)], 8, 120, 0.5, (2, 5))
            if self.vel > 170:
                self.tremer(0.1)
        else:
            self.poca = TEMPO_POCA
            self.poca_fase = 0.0
            self.som("boing", 0.5)
            self.particulas.explodir((X_PE, c.y), [(120, 180, 255), (200, 230, 255)], 12, 160, 0.5, (2, 5))
            self.textos.adicionar("ESCORREGOU!", (PIVO[0], PIVO[1] - 150), (150, 210, 255), 14)

    def _atualizar_borboleta(self, dt):
        b = self.borboleta
        if not b:
            return
        b["t"] += dt
        if b["fase"] == "chegando":
            alvo = self._pos_ovo()
            alvo = (alvo[0], alvo[1] - ALTURA_OVO / 2 - 6)
            k = min(1.0, b["t"] / 1.2)
            b["x"] = b["x0"] + (alvo[0] - b["x0"]) * k
            b["y"] = b["y0"] + (alvo[1] - b["y0"]) * k + math.sin(k * math.pi * 3) * 30
            if k >= 1:
                b["fase"], b["t"] = "pousada", 0.0
                self.textos.adicionar("HIHI!", (alvo[0] + 40, alvo[1] - 20), (255, 180, 230), 14)
        elif b["fase"] == "pousada":
            x, y = self._pos_ovo()
            b["x"], b["y"] = x, y - ALTURA_OVO / 2 - 6
            if b["t"] >= TEMPO_BORBOLETA or self.caindo or self.quebrado:
                b["fase"], b["t"] = "indo", 0.0
                b["x0"], b["y0"] = b["x"], b["y"]
        else:
            b["x"] = b["x0"] + b["t"] * 260
            b["y"] = b["y0"] - b["t"] * 220 + math.sin(b["t"] * 9) * 12
            if b["y"] < -40:
                self.borboleta = None

    def _atualizar_passarinho(self, dt):
        p = self.passarinho
        if not p:
            return
        p["t"] += dt
        ponta = self._ponto_colher(MEIA_CONCHA - 8, -14)
        if p["fase"] == "chegando":
            k = min(1.0, p["t"] / 1.1)
            suave = k * k * (3 - 2 * k)
            p["x"] = p["x0"] + (ponta[0] - p["x0"]) * suave
            p["y"] = p["y0"] + (ponta[1] - p["y0"]) * suave - math.sin(k * math.pi) * 40
            if k >= 1:
                p["fase"], p["t"] = "pousado", 0.0
                self.som("asa", 0.5)
                self.textos.adicionar("PIU!", (ponta[0] + 20, ponta[1] - 40), BRANCO, 14)
        elif p["fase"] == "pousado":
            p["x"], p["y"] = ponta
            if p["t"] >= TEMPO_PASSARINHO or self.caindo or self.quebrado:
                p["fase"], p["t"] = "indo", 0.0
                p["x0"], p["y0"] = p["x"], p["y"]
        else:
            p["x"] = p["x0"] + p["t"] * 380
            p["y"] = p["y0"] - p["t"] * 260
            if p["y"] < -40 or p["x"] > LARGURA + 60:
                self.passarinho = None

    # --------------------------------------------------------
    # QUEDA
    # --------------------------------------------------------

    def _cair(self):
        self.caindo = True
        self.tempo_queda = 0.0
        self.lento = 0.4
        lado = 1 if self.s > 0 else -1
        ang = math.radians(self.phi)
        x, y = self._pos_ovo()
        self.ovo_pos = (x, y)
        vt = self.vs if abs(self.vs) > 60 else lado * 60
        self.ovo_vel = (vt * math.cos(ang) + lado * 40, vt * math.sin(ang) - 160)
        self.ovo_ang = self._angulo_ovo()
        self.ovo_giro = -lado * 260
        self.som("pulo", 0.6)
        self.textos.adicionar("NÃÃÃO!", (x, y - 60), (255, 140, 140), 16)

    def _atualizar_queda(self, dt):
        self.tempo_queda += dt
        if self.caindo:
            x, y = self.ovo_pos
            vx, vy = self.ovo_vel
            vy += 1500 * dt
            x += vx * dt
            y += vy * dt
            self.ovo_pos, self.ovo_vel = (x, y), (vx, vy)
            self.ovo_ang += self.ovo_giro * dt
            if y + ALTURA_OVO / 2 >= 676:
                self._quebrar()
        else:
            # O ovo quebrado fica no chão (o mundo vai parando)
            x, y = self.ovo_pos
            self.ovo_pos = (x - self.vel * dt, y)
            if self.tempo_queda > 1.8:
                self.terminar(linhas=[f"DISTÂNCIA: {self.metros} m",
                                      f"CHECKPOINTS: {self.checkpoints}  •  PONTOS: {self.pontos}"])

    def _quebrar(self):
        self.caindo = False
        self.quebrado = True
        self.tempo_queda = 0.0
        x = self.ovo_pos[0]
        self.ovo_pos = (x, 676 - 16)
        self.tremer(0.3)
        self.som("explosao", 0.5)
        self.som("perder", 0.4)
        self.oooh = 2.0
        self.festa = 0.0
        self.textos.adicionar("CRACK!", (x, 560), (255, 240, 200), 32)
        self.particulas.explodir((x, 670), [(200, 160, 110), (230, 200, 160), (170, 130, 90)],
                                 24, 220, 0.8, (3, 7))
        self.particulas.explodir((x, 660), [self.jogador.cor, BRANCO, (255, 220, 60)], 16, 260, 0.9, (3, 6))
        self.cacos = []
        for _ in range(7):
            self.cacos.append((random.uniform(-70, 70), random.uniform(-6, 12), random.uniform(0, math.tau),
                               random.randint(6, 11)))

    # --------------------------------------------------------
    # GEOMETRIA
    # --------------------------------------------------------

    def _pivo(self):
        """Centro da concha (balança com os passos e com as pedras)."""
        bob = math.sin(self.fase_passo) * (1.5 + self.vel / 70)
        if self.caindo or self.quebrado:
            bob *= 0.3
        return (PIVO[0], PIVO[1] + bob + self.pulo_colher)

    def _ponto_colher(self, x, y):
        px, py = self._pivo()
        gx, gy = _girar(x, y, math.radians(self.phi))
        return (px + gx, py + gy)

    def _pos_ovo(self):
        """Centro do ovo em cima da concha."""
        s = max(-MEIA_CONCHA - 20, min(MEIA_CONCHA + 20, self.s))
        y = -ALTURA_OVO / 2 + 3 + 14 * (s / MEIA_CONCHA) ** 2
        return self._ponto_colher(s, y)

    def _angulo_ovo(self):
        """O ovo inclina junto com a colher e para o lado em que está escorregando."""
        return -self.phi - self.s * 0.35

    # --------------------------------------------------------
    # DESENHO
    # --------------------------------------------------------

    def desenhar_jogo(self, tela):
        tela.blit(self.fundo(self.jogador), (0, 0))
        self._desenhar_camadas(tela)
        self._desenhar_plateia(tela)
        self._desenhar_chao(tela)
        self._desenhar_braco(tela)
        self._desenhar_colher_e_ovo(tela)
        self._desenhar_bichos(tela)

        # Riscos de vento
        for x, y, w, _ in self.riscos_vento:
            pygame.draw.line(tela, (255, 255, 255), (int(x), y), (int(x - self.dir_vento * w), y), 3)
            pygame.draw.line(tela, (220, 230, 255), (int(x - self.dir_vento * w * 0.3), y + 6),
                             (int(x - self.dir_vento * w * 0.9), y + 6), 2)

        self.particulas.desenhar(tela)
        self.textos.desenhar(tela)
        self._desenhar_avisos(tela)

    def _desenhar_camadas(self, tela):
        t = self.tempo
        # Bandeirinhas (parallax lento)
        band = _ladrilho_bandeiras()
        off = -(self.dist * PARALLAX_BANDEIRAS) % LADO_BANDEIRAS
        x = off - LADO_BANDEIRAS
        while x < LARGURA:
            tela.blit(band, (int(x), 0))
            x += LADO_BANDEIRAS

        # Barracas e fogueira
        barr = _ladrilho_barracas()
        off = -(self.dist * PARALLAX_BARRACAS) % LADO_BARRACAS
        for x in (off - LADO_BARRACAS, off):
            tela.blit(barr, (int(x), Y_BARRACAS))
            fx = x + FOGUEIRA_X
            if -80 < fx < LARGURA + 80:
                self._desenhar_chamas(tela, fx, Y_BARRACAS + FOGUEIRA_Y, t)

    @staticmethod
    def _desenhar_chamas(tela, fx, fy, t):
        for i, (cor, esc) in enumerate((((255, 120, 40), 1.0), ((255, 190, 60), 0.7),
                                        ((255, 240, 150), 0.4))):
            for k in range(5):
                dx = (k - 2) * 16 * esc
                h = (70 - abs(k - 2) * 16) * esc * (1 + 0.18 * math.sin(t * 11 + k * 1.7 + i))
                w = 16 * esc + 4
                pygame.draw.polygon(tela, cor, [(fx + dx - w, fy), (fx + dx + w, fy),
                                                (fx + dx + math.sin(t * 7 + k) * 5, fy - h)])
        # Faíscas
        for k in range(4):
            fase = (t * 0.7 + k * 0.25) % 1
            px = fx + math.sin(k * 3 + t * 2) * 30
            py = fy - 60 - fase * 90
            pygame.draw.circle(tela, (255, 220, 120), (int(px), int(py)), 2)

    def _desenhar_plateia(self, tela):
        """Ovos da família torcendo na beira da pista (passam com o mundo)."""
        espaco = 230
        primeiro = int((self.dist - X_PE - 100) // espaco)
        for i in range(primeiro, primeiro + LARGURA // espaco + 3):
            if i < 0:
                continue
            rnd = random.Random(i * 7919)
            x = self._x_tela(i * espaco + rnd.randint(0, 80))
            if not -40 < x < LARGURA + 40:
                continue
            if rnd.random() < 0.3:
                continue
            ap = (rnd.randrange(4), rnd.randrange(8), rnd.randrange(3), rnd.randrange(6))
            altura = rnd.randint(38, 46)
            pe = GRAMA_Y + 36 + rnd.randint(-4, 4)
            dy = 0.0
            ang = 0.0
            if self.festa > 0:
                dy = -abs(math.sin(self.tempo * 9 + i)) * 18
            elif self.oooh > 0:
                ang = math.sin(self.tempo * 6 + i) * 8
            else:
                dy = -abs(math.sin(self.tempo * 4 + i)) * 3
            sombra = pygame.Rect(0, 0, altura, 8)
            sombra.center = (int(x), pe)
            pygame.draw.ellipse(tela, (60, 140, 55), sombra)
            if self.oooh > 0:
                ap = (ap[0], ap[1], ap[2], BOCA_MEDO)
            self.jogador.desenhar(tela, (x, pe - altura / 2 + dy), altura, aparencia=ap, angulo=ang)
            # Bracinhos para cima comemorando
            if self.festa > 0:
                for lado in (-1, 1):
                    bx = x + lado * altura * 0.45
                    pygame.draw.line(tela, (60, 50, 60), (bx, pe - altura * 0.5 + dy),
                                     (bx + lado * 8, pe - altura - 4 + dy), 3)
            if self.oooh > 0 and i % 2 == 0:
                ui.desenhar_texto(tela, "OOOH!", (int(x), int(pe - altura - 22)), 10, BRANCO, "center")

    def _desenhar_chao(self, tela):
        pista = _ladrilho_pista()
        off = -self.dist % LADO_PISTA
        x = off - LADO_PISTA
        while x < LARGURA:
            tela.blit(pista, (int(x), PISTA_Y))
            x += LADO_PISTA

        # Placas de checkpoint
        for k in (self.checkpoints, self.checkpoints + 1):
            if k <= 0:
                continue
            xm = k * METROS_CHECKPOINT * PX_POR_METRO
            x = self._x_tela(xm)
            if -80 < x < LARGURA + 80:
                self._desenhar_placa(tela, x, k * METROS_CHECKPOINT)

        # Pedras e poças
        for c in self.coisas:
            x = int(self._x_tela(c.x_mundo))
            if c.tipo == "pedra":
                pygame.draw.ellipse(tela, (150, 110, 70), (x - 18, c.y + 4, 36, 8))
                for dx, dy, r in c.forma:
                    pygame.draw.circle(tela, (100, 100, 105), (x + dx, c.y + dy), r + 2)
                    pygame.draw.circle(tela, (150, 150, 150), (x + dx, c.y + dy), r)
                    pygame.draw.circle(tela, (200, 200, 205), (x + dx - r // 3, c.y + dy - r // 3),
                                       max(1, r // 3))
            else:
                r = pygame.Rect(0, 0, 110, 24)
                r.center = (x, c.y)
                pygame.draw.ellipse(tela, (120, 90, 60), r.inflate(8, 6))
                pygame.draw.ellipse(tela, (80, 140, 220), r)
                pygame.draw.ellipse(tela, (170, 210, 255), (r.x + 20, r.y + 5, 40, 7))

    def _desenhar_placa(self, tela, x, metros):
        x = int(x)
        pygame.draw.rect(tela, (100, 64, 40), (x - 4, GRAMA_Y - 30, 8, 86))
        placa = pygame.Rect(0, 0, 110, 44)
        placa.midbottom = (x, GRAMA_Y - 20)
        pygame.draw.rect(tela, (80, 50, 30), placa.inflate(6, 6), border_radius=6)
        pygame.draw.rect(tela, (230, 190, 120), placa, border_radius=5)
        ui.desenhar_texto(tela, "★ CHECK ★", (x, placa.y + 12), 10, (150, 50, 40), "center", sombra=False)
        ui.desenhar_texto(tela, f"{metros} m", (x, placa.y + 30), 12, (90, 50, 30), "center", sombra=False)

    def _desenhar_braco(self, tela):
        mao = self._ponto_colher(*PONTA_CABO)
        ox, oy = OMBRO
        dx, dy = mao[0] - ox, mao[1] - oy
        comp = math.hypot(dx, dy) or 1
        ux, uy = dx / comp, dy / comp
        nx, ny = -uy, ux
        larg = 30
        # Manga listrada (faixas perpendiculares ao braço)
        faixas = 9
        for i in range(faixas):
            a = i / faixas
            b = (i + 1) / faixas
            p1 = (ox + dx * a, oy + dy * a)
            p2 = (ox + dx * b, oy + dy * b)
            cor = (230, 70, 80) if i % 2 == 0 else (250, 240, 230)
            if a > 0.72:
                cor = (255, 210, 170)          # pulso
            pygame.draw.polygon(tela, cor, [(p1[0] + nx * larg, p1[1] + ny * larg),
                                            (p2[0] + nx * larg, p2[1] + ny * larg),
                                            (p2[0] - nx * larg, p2[1] - ny * larg),
                                            (p1[0] - nx * larg, p1[1] - ny * larg)])
        # Contorno do braço
        for lado in (-1, 1):
            pygame.draw.line(tela, (120, 60, 50), (ox + nx * larg * lado, oy + ny * larg * lado),
                             (mao[0] + nx * larg * lado, mao[1] + ny * larg * lado), 3)
        # Punho da manga
        p = (ox + dx * 0.72, oy + dy * 0.72)
        pygame.draw.line(tela, (200, 50, 60), (p[0] + nx * (larg + 3), p[1] + ny * (larg + 3)),
                         (p[0] - nx * (larg + 3), p[1] - ny * (larg + 3)), 8)

    def _desenhar_colher_e_ovo(self, tela):
        ang = math.radians(self.phi)
        px, py = self._pivo()

        def pt(x, y):
            gx, gy = _girar(x, y, ang)
            return (px + gx, py + gy)

        # Sombra no chão
        sombra = pygame.Rect(0, 0, 200, 16)
        sombra.center = (PIVO[0], 668)
        pygame.draw.ellipse(tela, (160, 115, 72), sombra)

        # Cabo
        cabo = [pt(-MEIA_CONCHA + 6, -4), pt(PONTA_CABO[0] - 12, PONTA_CABO[1] - 6),
                pt(PONTA_CABO[0] - 12, PONTA_CABO[1] + 6), pt(-MEIA_CONCHA + 6, 6)]
        pygame.draw.polygon(tela, (200, 200, 215), cabo)
        pygame.draw.polygon(tela, (80, 80, 105), cabo, 2)
        pygame.draw.line(tela, (240, 240, 250), pt(-MEIA_CONCHA, -1), pt(PONTA_CABO[0], PONTA_CABO[1] - 3), 2)

        # Concha: parte de trás (o fundo)
        n = 28
        elipse = [(math.cos(i * math.tau / n) * MEIA_CONCHA, math.sin(i * math.tau / n) * ALTURA_CONCHA / 2)
                  for i in range(n)]
        pygame.draw.polygon(tela, (170, 170, 190), [pt(x, y) for x, y in elipse])
        pygame.draw.polygon(tela, (80, 80, 105), [pt(x, y) for x, y in elipse], 3)

        # Ovo
        if not (self.caindo or self.quebrado):
            self._desenhar_ovo_na_colher(tela)

        # Frente da concha (cobre o pé do ovo)
        frente = [(math.cos(i * math.pi / 14) * MEIA_CONCHA, math.sin(i * math.pi / 14) * ALTURA_CONCHA / 2 + 2)
                  for i in range(15)]
        pygame.draw.polygon(tela, (200, 200, 215), [pt(x, y) for x, y in frente])
        pygame.draw.lines(tela, (80, 80, 105), False, [pt(x, y) for x, y in frente], 3)
        brilho = [pt(math.cos(i * math.pi / 10 + 0.5) * (MEIA_CONCHA - 14),
                     math.sin(i * math.pi / 10 + 0.5) * (ALTURA_CONCHA / 2 - 6) + 4) for i in range(5)]
        pygame.draw.lines(tela, (240, 240, 250), False, brilho, 3)

        # Mão segurando o cabo
        mx, my = pt(*PONTA_CABO)
        pygame.draw.circle(tela, (150, 100, 80), (int(mx), int(my)), 21)
        pygame.draw.circle(tela, (255, 210, 170), (int(mx), int(my)), 19)
        for k in range(4):
            fx, fy = pt(PONTA_CABO[0] + 10 - k * 7, PONTA_CABO[1] - 12)
            pygame.draw.circle(tela, (150, 100, 80), (int(fx), int(fy)), 7)
            pygame.draw.circle(tela, (255, 215, 180), (int(fx), int(fy)), 6)
        dx, dy = pt(PONTA_CABO[0] + 16, PONTA_CABO[1] + 6)
        pygame.draw.circle(tela, (150, 100, 80), (int(dx), int(dy)), 8)
        pygame.draw.circle(tela, (255, 215, 180), (int(dx), int(dy)), 7)

        # Ovo caindo / quebrado
        if self.caindo:
            self._desenhar_ovo_solto(tela)
        elif self.quebrado:
            self._desenhar_ovo_quebrado(tela)

    def _aparencia_ovo(self, medo):
        ap = self.jogador.aparencia()
        if medo:
            ap = (ap[0], ap[1], ap[2], BOCA_MEDO)
        return ap

    def _desenhar_ovo_na_colher(self, tela):
        x, y = self._pos_ovo()
        ang = self._angulo_ovo()
        # Cócegas da borboleta: treme
        if self.borboleta and self.borboleta["fase"] == "pousada":
            ang += math.sin(self.tempo * 40) * 4
        medo = abs(self.s) > 40 or self.poca > 0
        self.jogador.desenhar(tela, (x, y), ALTURA_OVO, aparencia=self._aparencia_ovo(medo), angulo=ang)

        # Seta vermelha piscando do lado em que ele vai cair
        if abs(self.s) > 45 and int(self.tempo * 8) % 2 == 0:
            lado = 1 if self.s > 0 else -1
            bx, by = self._ponto_colher(lado * (MEIA_CONCHA + 34), -34)
            pts = [(bx + lado * 18, by), (bx - lado * 4, by - 16), (bx - lado * 4, by - 7),
                   (bx - lado * 20, by - 7), (bx - lado * 20, by + 7), (bx - lado * 4, by + 7),
                   (bx - lado * 4, by + 16)]
            pygame.draw.polygon(tela, (255, 255, 255), pts)
            pygame.draw.polygon(tela, (230, 40, 40), pts, 0)
            pygame.draw.polygon(tela, (255, 255, 255), pts, 2)

    def _desenhar_ovo_solto(self, tela):
        x, y = self.ovo_pos
        self.jogador.desenhar(tela, (x, y), ALTURA_OVO, aparencia=self._aparencia_ovo(True),
                              angulo=self.ovo_ang)

    def _desenhar_ovo_quebrado(self, tela):
        x, y = self.ovo_pos
        x, y = int(x), int(y)
        # Clara e gema esparramadas
        cresce = min(1.0, self.tempo_queda / 0.3)
        clara = pygame.Rect(0, 0, int(130 * cresce) + 20, int(26 * cresce) + 6)
        clara.center = (x, y + 14)
        pygame.draw.ellipse(tela, (250, 250, 240), clara)
        pygame.draw.ellipse(tela, (220, 220, 210), clara, 2)
        pygame.draw.circle(tela, (255, 190, 40), (x + 26, y + 14), int(12 * cresce) + 2)
        pygame.draw.circle(tela, (255, 230, 140), (x + 22, y + 10), max(1, int(4 * cresce)))

        # O ovo deitado, rachado
        corpo = self.jogador.desenhar(tela, (x - 10, y - 4), ALTURA_OVO, aparencia=self._aparencia_ovo(True),
                                      angulo=80)
        cor = (60, 40, 40)
        cx, cy = corpo.center
        pts = [(cx - 30, cy - 6), (cx - 18, cy + 4), (cx - 8, cy - 8), (cx + 4, cy + 6), (cx + 16, cy - 6),
               (cx + 28, cy + 2)]
        pygame.draw.lines(tela, cor, False, pts, 3)
        pygame.draw.line(tela, cor, (cx - 8, cy - 8), (cx - 12, cy - 20), 2)
        pygame.draw.line(tela, cor, (cx + 16, cy - 6), (cx + 20, cy + 14), 2)

        # Caquinhos de casca
        for dx, dy, a, r in self.cacos:
            px, py = x + dx, y + 12 + dy
            tri = [(px + math.cos(a + k * 2.1) * r, py + math.sin(a + k * 2.1) * r * 0.6) for k in range(3)]
            pygame.draw.polygon(tela, self.jogador.cor, tri)
            pygame.draw.polygon(tela, self.jogador.cor_contorno, tri, 1)

    def _desenhar_bichos(self, tela):
        t = self.tempo
        b = self.borboleta
        if b:
            x, y = b["x"], b["y"]
            bate = abs(math.sin(t * (14 if b["fase"] != "pousada" else 6)))
            for lado in (-1, 1):
                w = max(2, int(16 * bate))
                asa = pygame.Rect(0, 0, w, 18)
                if lado < 0:
                    asa.midright = (x, y - 5)
                else:
                    asa.midleft = (x, y - 5)
                pygame.draw.ellipse(tela, b["cor"], asa)
                pygame.draw.ellipse(tela, ui.escurecer(b["cor"], 80), asa, 2)
                asa2 = pygame.Rect(0, 0, max(2, int(11 * bate)), 12)
                if lado < 0:
                    asa2.midright = (x, y + 6)
                else:
                    asa2.midleft = (x, y + 6)
                pygame.draw.ellipse(tela, ui.clarear(b["cor"], 40), asa2)
            pygame.draw.line(tela, (50, 40, 50), (x, y - 10), (x, y + 10), 3)
            pygame.draw.line(tela, (50, 40, 50), (x, y - 10), (x - 5, y - 17), 1)
            pygame.draw.line(tela, (50, 40, 50), (x, y - 10), (x + 5, y - 17), 1)

        p = self.passarinho
        if p:
            x, y = int(p["x"]), int(p["y"])
            olha = -1 if p["fase"] == "pousado" else 1
            pygame.draw.ellipse(tela, (70, 50, 40), (x - 15, y - 12, 30, 22))
            pygame.draw.ellipse(tela, (150, 100, 70), (x - 13, y - 10, 26, 18))
            pygame.draw.ellipse(tela, (240, 200, 160), (x - 7, y - 3, 14, 9))
            pygame.draw.circle(tela, (150, 100, 70), (x + olha * 11, y - 12), 9)
            pygame.draw.circle(tela, BRANCO, (x + olha * 14, y - 14), 3)
            pygame.draw.circle(tela, PRETO, (x + olha * 15, y - 14), 2)
            pygame.draw.polygon(tela, (255, 170, 40), [(x + olha * 19, y - 13), (x + olha * 27, y - 10),
                                                       (x + olha * 19, y - 8)])
            pygame.draw.polygon(tela, (70, 50, 40), [(x - olha * 13, y - 4), (x - olha * 24, y - 10),
                                                     (x - olha * 22, y + 2)])
            if p["fase"] != "pousado":
                bate = math.sin(t * 22) * 14
                pygame.draw.polygon(tela, (110, 70, 50), [(x - 6, y - 6), (x + 6, y - 6), (x, y - 6 - bate)])
            else:
                pygame.draw.line(tela, (255, 170, 40), (x - 3, y + 9), (x - 3, y + 14), 2)
                pygame.draw.line(tela, (255, 170, 40), (x + 4, y + 9), (x + 4, y + 14), 2)

    def _desenhar_avisos(self, tela):
        if self.estado != "jogando":
            return
        # Aviso de vento com bandeirinha
        if self.aviso_vento > 0 or self.vento > 0:
            if self.aviso_vento > 0 and int(self.tempo * 8) % 2 == 1:
                return
            seta = "→" if self.dir_vento > 0 else "←"
            msg = f"VENTO {seta}" if self.dir_vento > 0 else f"{seta} VENTO"
            caixa = pygame.Rect(0, 0, 220, 40)
            caixa.midtop = (LARGURA // 2, 74)
            ui.painel(tela, caixa, (20, 24, 40), (150, 210, 255), 12, 3, sombra=False)
            ui.desenhar_texto(tela, msg, (caixa.centerx + 14, caixa.centery + 1), 14, (150, 210, 255), "center")
            # Bandeirinha tremulando
            bx, by = caixa.x + 22, caixa.y + 8
            pygame.draw.line(tela, BRANCO, (bx, by), (bx, by + 26), 2)
            ond = math.sin(self.tempo * 18) * 3
            d = self.dir_vento
            if d < 0:
                bx = caixa.right - 22
                pygame.draw.line(tela, BRANCO, (bx, by), (bx, by + 26), 2)
            pygame.draw.polygon(tela, (255, 80, 80), [(bx, by), (bx + d * 20, by + 5 + ond), (bx, by + 12)])

    def desenhar_hud(self, tela):
        caixa = pygame.Rect(12, 12, 420, 48)
        ui.painel(tela, caixa, (20, 24, 40), BRANCO, 12, 3, sombra=False)
        ui.desenhar_texto(tela, f"PONTOS: {self.pontos}", (caixa.x + 16, caixa.centery), 14,
                          AMARELO, "midleft")
        rec = self.recorde()
        if rec is not None:
            ui.desenhar_texto(tela, f"RECORDE: {rec}", (caixa.x + 236, caixa.centery), 12,
                              (180, 200, 255), "midleft")

        # Distância e próximo checkpoint
        caixa = pygame.Rect(12, 68, 290, 34)
        ui.painel(tela, caixa, (20, 24, 40), (255, 190, 120), 10, 2, sombra=False)
        falta = max(0, int((self.proximo_check - self.dist) / PX_POR_METRO))
        ui.desenhar_texto(tela, f"{self.metros} m", (caixa.x + 14, caixa.centery + 1), 14, BRANCO, "midleft")
        ui.desenhar_texto(tela, f"★ em {falta} m", (caixa.right - 12, caixa.centery + 1), 10,
                          (255, 210, 150), "midright")

        # Velocímetro (antes do botão de pausa)
        caixa = pygame.Rect(0, 12, 210, 48)
        caixa.right = LARGURA - 76
        ui.painel(tela, caixa, (20, 24, 40), BRANCO, 12, 3, sombra=False)
        ui.desenhar_texto(tela, "VEL", (caixa.x + 14, caixa.centery + 1), 12, BRANCO, "midleft")
        frac = (self.vel - VEL_MIN) / (VEL_MAX - VEL_MIN)
        n = 8
        for i in range(n):
            r = pygame.Rect(caixa.x + 62 + i * 17, caixa.bottom - 12 - (6 + i * 3), 12, 6 + i * 3)
            aceso = frac * n >= i + 0.5 or i == 0
            cor = ui.misturar((90, 220, 90), (255, 80, 60), i / (n - 1)) if aceso else (60, 64, 90)
            pygame.draw.rect(tela, cor, r, border_radius=2)
