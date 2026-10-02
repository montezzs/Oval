import math
import random

import pygame

from settings import *
from core import ui
from jogos.base import MiniJogo

# ============================================================
# DESCIDA NA NEVE
# ============================================================
# O ovo desce a montanha num trenó vermelho (visão de cima, estilo
# SkiFree). Passe entre as BANDEIRAS para ganhar tempo, salte as
# RAMPAS (gire no ar para fazer MANOBRA!) e desvie dos pinheiros,
# pedras, bonecos de neve e troncos. Depois de 2000 m aparece o
# BONECO DE NEVE GIGANTE, que quer o seu ovo de nariz!
#
# A pista é gerada em blocos com um CORREDOR LIVRE que serpenteia:
# sempre existe caminho, e as bandeiras ficam dentro dele.

OVO_Y = 220                     # onde o trenó fica na tela
OVO_ALT = 44
RAIO_OVO = 14                   # colisão do trenó
PX_METRO = 10

# Direção e velocidade
ANGULO_MAX = 70.0
GIRO = 180.0                    # graus por segundo
VEL_BASE = 300.0
VEL_AGACHADO = 700.0
VEL_FREIO = 150.0
ACEL = 380.0
FREADA = 700.0

# Pulos
TEMPO_RAMPA = 0.6
ALTURA_RAMPA = 54
TEMPO_PULINHO = 0.3
ALTURA_PULINHO = 24
RECARGA_PULINHO = 2.0
GIRO_AR = 760.0                 # manobra: graus por segundo no ar

# Batidas
TEMPO_TOMBO = 1.0
TEMPO_INVENCIVEL = 1.0
BATIDAS = 3

# Relógio e bandeiras
TEMPO_INICIAL = 60.0
BONUS_BANDEIRA = 1.5
MULTA_BANDEIRA = 3.0
VAO_BANDEIRA = 140
PONTOS_BANDEIRA = 20
PONTOS_MANOBRA = 100

# Geração
BLOCO = 720
LARG_CORREDOR = [130, 110, 95]          # meia largura por dificuldade (>= 160 px no total)
DENSIDADE = [0.6, 1.0, 1.4]

# Boneco gigante
METROS_BONECO = 2000
AVISO_BONECO = 150              # metros antes: "!" no topo
DIST_BONECO = 230               # nasce esta distância acima do trenó
RAIO_BONECO = 60

TECLAS_ESQ = (pygame.K_LEFT, pygame.K_a)
TECLAS_DIR = (pygame.K_RIGHT, pygame.K_d)
TECLAS_RAPIDO = (pygame.K_DOWN, pygame.K_s)
TECLAS_FREIO = (pygame.K_UP, pygame.K_w)
TECLAS_PULO = (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER)

NEVE = (245, 248, 255)
SOMBRA_NEVE = (220, 230, 245)
RASTRO = (205, 215, 235)

# Obstáculos: raio de colisão
RAIOS = {"pinheiro": 20, "pinheiro_g": 24, "pedra": 18, "boneco": 16, "tronco": 12}


def _suave(t):
    return t * t * (3 - 2 * t)


# ============================================================
# DESENHOS PRÉ-RENDERIZADOS
# ============================================================

_sprites = {}


def _pinheiro(escala):
    lado_l = int(76 * escala)
    alt = int(110 * escala)
    s = pygame.Surface((lado_l, alt), pygame.SRCALPHA)
    cx = lado_l // 2
    # Sombra no chão
    pygame.draw.ellipse(s, (205, 215, 235), (cx - int(30 * escala), alt - int(14 * escala),
                                             int(60 * escala), int(14 * escala)))
    # Tronco
    pygame.draw.rect(s, (110, 70, 40), (cx - int(6 * escala), alt - int(22 * escala),
                                        int(12 * escala), int(16 * escala)))
    # 3 triângulos empilhados (de baixo para cima)
    for i, (larg, topo, base) in enumerate(((36, 40, 88), (29, 22, 62), (21, 4, 40))):
        l, t_, b = larg * escala, topo * escala, base * escala
        cor = (40, 120, 70) if i % 2 == 0 else (30, 90, 55)
        pygame.draw.polygon(s, (20, 60, 40), [(cx, t_ - 2), (cx - l - 2, b + 1), (cx + l + 2, b + 1)])
        pygame.draw.polygon(s, cor, [(cx, t_), (cx - l, b), (cx + l, b)])
        pygame.draw.polygon(s, (60, 150, 90), [(cx, t_ + 4), (cx - l * 0.55, b - 2), (cx - l * 0.15, b - 2)])
        # Neve em cima de cada camada
        pygame.draw.polygon(s, BRANCO, [(cx, t_), (cx - l * 0.35, t_ + (b - t_) * 0.35),
                                        (cx - l * 0.1, t_ + (b - t_) * 0.28),
                                        (cx + l * 0.12, t_ + (b - t_) * 0.38),
                                        (cx + l * 0.35, t_ + (b - t_) * 0.35)])
    return s


def _pedra():
    s = pygame.Surface((52, 38), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (205, 215, 235), (2, 22, 48, 14))
    pygame.draw.ellipse(s, (90, 90, 100), (4, 6, 44, 28))
    pygame.draw.ellipse(s, (130, 130, 140), (6, 6, 40, 24))
    pygame.draw.ellipse(s, (165, 165, 175), (12, 9, 18, 8))
    pygame.draw.ellipse(s, BRANCO, (14, 4, 24, 9))
    return s


def _boneco_pequeno():
    s = pygame.Surface((44, 64), pygame.SRCALPHA)
    contorno = (150, 170, 210)
    pygame.draw.ellipse(s, (205, 215, 235), (4, 52, 36, 11))
    pygame.draw.circle(s, contorno, (22, 42), 16)
    pygame.draw.circle(s, BRANCO, (22, 42), 14)
    pygame.draw.circle(s, contorno, (22, 18), 12)
    pygame.draw.circle(s, BRANCO, (22, 18), 10)
    pygame.draw.circle(s, (30, 30, 40), (18, 16), 2)
    pygame.draw.circle(s, (30, 30, 40), (26, 16), 2)
    pygame.draw.polygon(s, (255, 140, 40), [(22, 19), (22, 23), (31, 21)])
    pygame.draw.rect(s, (220, 60, 60), (12, 27, 20, 5), border_radius=2)
    pygame.draw.rect(s, (40, 40, 50), (14, 2, 16, 8))
    pygame.draw.rect(s, (40, 40, 50), (10, 9, 24, 3))
    for y in (38, 45):
        pygame.draw.circle(s, (40, 40, 50), (22, y), 2)
    return s


def _tronco():
    s = pygame.Surface((96, 32), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (205, 215, 235), (4, 20, 88, 12))
    pygame.draw.rect(s, (90, 55, 30), (6, 6, 84, 22), border_radius=10)
    pygame.draw.rect(s, (130, 85, 50), (8, 8, 80, 16), border_radius=8)
    for x in (24, 46, 68):
        pygame.draw.line(s, (100, 62, 34), (x, 10), (x + 8, 12), 2)
    pygame.draw.ellipse(s, (190, 150, 100), (78, 6, 14, 22))
    pygame.draw.ellipse(s, (130, 85, 50), (81, 11, 8, 12), 2)
    pygame.draw.rect(s, BRANCO, (14, 4, 50, 5), border_radius=3)
    return s


def _treno():
    """Trenó vermelho visto de cima (a frente aponta para baixo)."""
    s = pygame.Surface((44, 62), pygame.SRCALPHA)
    # Esquis (patins) com a ponta curvada na frente
    for x in (4, 34):
        pygame.draw.rect(s, (60, 60, 70), (x, 4, 6, 50), border_radius=3)
        pygame.draw.circle(s, (60, 60, 70), (x + 3, 55), 5, 2)
    pygame.draw.rect(s, (130, 20, 30), (6, 6, 32, 46), border_radius=8)
    pygame.draw.rect(s, (220, 45, 55), (8, 8, 28, 42), border_radius=7)
    for y in (16, 26, 36):
        pygame.draw.line(s, (170, 30, 40), (10, y), (34, y), 2)
    pygame.draw.rect(s, (255, 130, 130), (10, 9, 6, 38), border_radius=3)
    return s


def _sprite(nome):
    s = _sprites.get(nome)
    if s is None:
        s = {"pinheiro": lambda: _pinheiro(1.0), "pinheiro_g": lambda: _pinheiro(1.3),
             "pedra": _pedra, "boneco": _boneco_pequeno, "tronco": _tronco, "treno": _treno}[nome]()
        _sprites[nome] = s
    return s


_camadas = {}


def _chao_neve():
    """Neve com montinhos (repete na vertical)."""
    if "neve" in _camadas:
        return _camadas["neve"]
    s = pygame.Surface((LARGURA, ALTURA))
    s.fill(NEVE)
    rnd = random.Random(4)
    for _ in range(46):
        w = rnd.randint(60, 180)
        h = rnd.randint(18, 40)
        x, y = rnd.randrange(-40, LARGURA), rnd.randrange(0, ALTURA)
        for dy in (-ALTURA, 0, ALTURA):
            pygame.draw.ellipse(s, SOMBRA_NEVE, (x, y + dy + h // 3, w, h))
            pygame.draw.ellipse(s, NEVE, (x - 4, y + dy, w, h))
    for _ in range(160):
        x, y = rnd.randrange(LARGURA), rnd.randrange(ALTURA)
        pygame.draw.circle(s, (232, 238, 250), (x, y), 1)
    _camadas["neve"] = s
    return s


# ============================================================
# OBJETOS DA PISTA
# ============================================================

class Objeto:

    def __init__(self, tipo, x, y, **extra):
        self.tipo = tipo            # obstáculo, "rampa" ou "bandeira"
        self.x = float(x)
        self.y = float(y)           # mundo (a base do objeto)
        self.passou = False
        self.cor = extra.get("cor", 0)

    @property
    def raio(self):
        return RAIOS.get(self.tipo, 0)

    def encosta(self, x, y, r):
        """Colisão com o trenó (círculo)."""
        if self.tipo == "tronco":
            px = max(self.x - 42, min(x, self.x + 42))
            py = max(self.y - 10, min(y, self.y + 4))
            return (x - px) ** 2 + (y - py) ** 2 < r * r
        if self.tipo in RAIOS:
            return (x - self.x) ** 2 + (y - (self.y - 4)) ** 2 < (r + self.raio) ** 2
        return False


# ============================================================
# JOGO
# ============================================================

class DescidaNeve(MiniJogo):

    ID = "descida_neve"
    TITULO = "DESCIDA NA NEVE"
    TITULO_CURTO = "NEVE"
    DESCRICAO = "O ovo desce a montanha de trenó! Passe nas bandeiras, salte rampas e fuja do boneco gigante."
    COR = (90, 160, 230)
    INSTRUCOES = [
        "Desça de trenó e desvie das árvores e pedras!",
        "Passe ENTRE as bandeiras: +1.5s. Errar: -3s.",
        "Nas RAMPAS, aperte ← → no ar: MANOBRA +100!",
        "Depois de 2000 m... cuidado com o BONECO!",
        "← → virar • ↓ acelerar • ↑ frear • ESPAÇO pula",
    ]
    OPCOES = ["VERDE (FÁCIL)", "AZUL", "PRETA (DIFÍCIL)"]
    MENOR_MELHOR = False
    ROTULO_PONTOS = "PONTOS"
    CONTAGEM = True

    MOEDAS_POR = 120
    MOEDAS_MAX = 25

    # --------------------------------------------------------
    # CENÁRIO
    # --------------------------------------------------------

    @classmethod
    def criar_fundo(cls, jogador):
        return _chao_neve().copy()

    @classmethod
    def desenhar_icone(cls, sup, jogador):
        w, h = sup.get_size()
        for x, y, esc in ((0.12, 0.55, 0.55), (0.86, 0.42, 0.5), (0.78, 0.95, 0.6), (0.2, 1.02, 0.6)):
            p = _sprite("pinheiro")
            p = pygame.transform.smoothscale(p, (int(p.get_width() * esc), int(p.get_height() * esc)))
            sup.blit(p, p.get_rect(midbottom=(int(w * x), int(h * y))))
        for i, cor in enumerate(((230, 60, 60), (60, 110, 230))):
            x = int(w * (0.34 + i * 0.32))
            pygame.draw.line(sup, (80, 80, 90), (x, h - 30), (x, h - 52), 2)
            pygame.draw.polygon(sup, cor, [(x, h - 52), (x + 12, h - 47), (x, h - 42)])
        treno = pygame.transform.rotate(pygame.transform.smoothscale(_sprite("treno"), (26, 36)), 18)
        sup.blit(treno, treno.get_rect(center=(w // 2, h // 2 + 12)))
        jogador.desenhar(sup, (w // 2, h // 2 + 2), 28, angulo=6)

    # --------------------------------------------------------
    # PARTIDA
    # --------------------------------------------------------

    def reiniciar(self):
        _chao_neve()
        self.x = LARGURA / 2
        self.dist = 0.0                 # y do trenó no mundo
        self.angulo = 0.0
        self.vel = VEL_BASE * 0.5
        self.vel_media = VEL_BASE
        self.relogio = TEMPO_INICIAL
        self.bandeiras = 0
        self.manobras = 0
        self.batidas = 0

        self.ar = 0.0                   # tempo que falta no ar
        self.ar_total = 0.0
        self.ar_rampa = False
        self.giro_ar = 0.0
        self.recarga = 0.0
        self.tombo = 0.0
        self.invencivel = 0.0
        self.girando = 0.0              # jato de neve nas curvas

        self.boneco_y = None            # boneco gigante (mundo)
        self.boneco_x = LARGURA / 2
        self.abracado = False
        self.fim = 0.0
        self.motivo = ""

        self.objetos = []
        self.rastro = []                # pontos (x, y_mundo) ou None
        self.ultimo_rastro = 0.0
        self.linhas = []                # linhas de velocidade
        self.flocos = [[random.uniform(0, LARGURA), random.uniform(0, ALTURA), random.uniform(30, 70),
                        random.uniform(0, math.tau), random.choice((2, 2, 3, 4))] for _ in range(70)]

        # Corredor livre: pontos (y, centro) a cada BLOCO
        self.meia = LARG_CORREDOR[self.opcao]
        self.densidade = DENSIDADE[self.opcao]
        self.corredor = [(-BLOCO, self.x), (0.0, self.x)]
        self.gerado_ate = 0.0
        self._gerar()

        self.teclas = set()
        self.mouse_x = None

    def _centro(self, y):
        """Centro do corredor livre na altura y (mundo)."""
        pts = self.corredor
        for (y0, c0), (y1, c1) in zip(pts, pts[1:]):
            if y0 <= y <= y1:
                return c0 + (c1 - c0) * _suave((y - y0) / (y1 - y0))
        return pts[-1][1] if y > pts[-1][0] else pts[0][1]

    def _gerar(self):
        while self.gerado_ate < self.dist + ALTURA + BLOCO:
            y0 = self.gerado_ate
            y1 = y0 + BLOCO
            c0 = self.corredor[-1][1]
            margem = self.meia + 60
            c1 = max(margem, min(LARGURA - margem, c0 + random.uniform(-260, 260)))
            self.corredor.append((y1, c1))
            self._preencher(y0, y1)
            self.gerado_ate = y1
        # Descarta o que já ficou lá para cima
        self.corredor = [p for p in self.corredor if p[0] > self.dist - 2 * BLOCO] or self.corredor[-2:]
        if len(self.corredor) < 2:
            self.corredor.insert(0, (self.corredor[0][0] - BLOCO, self.corredor[0][1]))

    def _preencher(self, y0, y1):
        # Mais obstáculos quanto mais longe
        n = int((9 + min(9, y0 / 4000)) * self.densidade)
        livre_inicio = 520                  # começo da descida sem obstáculos
        novos = []

        # Bandeiras (dentro do corredor) e às vezes uma rampa
        cor = int(y0 / BLOCO) % 2
        for fy in (y0 + 200 + random.uniform(-50, 50), y0 + 560 + random.uniform(-50, 50)):
            if fy < 300:
                continue
            cx = self._centro(fy) + random.uniform(-25, 25)
            cx = max(VAO_BANDEIRA / 2 + 20, min(LARGURA - VAO_BANDEIRA / 2 - 20, cx))
            novos.append(Objeto("bandeira", cx, fy, cor=cor))
            cor = 1 - cor
        if y0 > 600 and random.random() < 0.45:
            ry = y0 + 380
            novos.append(Objeto("rampa", self._centro(ry) + random.uniform(-20, 20), ry))

        # Obstáculos fora do corredor
        tipos = ["pinheiro", "pinheiro", "pinheiro_g", "pedra", "boneco", "tronco"]
        tentativas = 0
        colocados = 0
        while colocados < n and tentativas < n * 12:
            tentativas += 1
            tipo = random.choice(tipos)
            x = random.uniform(20, LARGURA - 20)
            y = random.uniform(y0, y1)
            if y < livre_inicio:
                continue
            meio = 44 if tipo == "tronco" else RAIOS[tipo]
            # Longe do corredor em toda a altura do obstáculo
            if min(abs(x - self._centro(yy)) for yy in (y - 30, y, y + 30)) < self.meia + meio + RAIO_OVO:
                continue
            if any(abs(o.x - x) < 70 and abs(o.y - y) < 70 for o in novos + self.objetos[-40:]):
                continue
            novos.append(Objeto(tipo, x, y))
            colocados += 1
        self.objetos.extend(novos)

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
        super().evento(e)

    def evento_jogo(self, e):
        if e.type == pygame.KEYDOWN:
            if e.key in TECLAS_ESQ + TECLAS_DIR:
                self.mouse_x = None
            elif e.key in TECLAS_PULO:
                self._pulinho()
        elif e.type == pygame.MOUSEMOTION:
            self.mouse_x = float(e.pos[0])
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.mouse_x = float(e.pos[0])
            self._pulinho()

    def _segurando(self, teclas):
        return any(k in self.teclas for k in teclas)

    def _pulinho(self):
        if self.ar > 0 or self.tombo > 0 or self.recarga > 0 or self.fim > 0:
            return
        self._decolar(TEMPO_PULINHO, rampa=False)
        self.recarga = RECARGA_PULINHO
        self.som("pulo", 0.5)

    def _decolar(self, tempo, rampa):
        self.ar = tempo
        self.ar_total = tempo
        self.ar_rampa = rampa
        self.giro_ar = 0.0
        self.rastro.append(None)

    # --------------------------------------------------------
    # LÓGICA
    # --------------------------------------------------------

    @property
    def metros(self):
        return int(self.dist / PX_METRO)

    def atualizar_jogo(self, dt):
        self._flocos(dt)
        if self.fim > 0:
            self.fim -= dt
            if self.boneco_y is not None and self.abracado:
                self.boneco_y += (self.dist + 34 - self.boneco_y) * min(1.0, dt * 6)
                self.boneco_x += (self.x - self.boneco_x) * min(1.0, dt * 6)
            if self.fim <= 0:
                self._terminar()
            return

        self.relogio -= dt
        self.recarga = max(0.0, self.recarga - dt)
        self.invencivel = max(0.0, self.invencivel - dt)

        if self.tombo > 0:
            self.tombo -= dt
            self.vel = 0.0
            if self.tombo <= 0:
                self.tombo = 0.0
                self.angulo = 0.0
                self.invencivel = TEMPO_INVENCIVEL
                if self.batidas >= BATIDAS:
                    self._acabar("3 TOMBOS!", 0.4)
                    return
        else:
            self._dirigir(dt)

        # Movimento
        a = math.radians(self.angulo)
        vy = self.vel * math.cos(a)
        vx = self.vel * math.sin(a)
        y_antes = self.dist
        self.dist += vy * dt
        self.x += vx * dt
        if self.x < 24 or self.x > LARGURA - 24:
            self.x = max(24.0, min(LARGURA - 24.0, self.x))
        self.vel_media += (vy - self.vel_media) * min(1.0, dt / 8.0)

        # No ar
        if self.ar > 0:
            self.ar -= dt
            if self.ar <= 0:
                self._pousar()

        self._bandeiras(y_antes)
        self._colidir()
        self._rastro()
        self._efeitos(dt, vy)
        self._boneco(dt, vy)
        self._gerar()
        self.objetos = [o for o in self.objetos if o.y > self.dist - OVO_Y - 160]

        self.pontos = self.metros // 10 + self.bandeiras * PONTOS_BANDEIRA + self.manobras * PONTOS_MANOBRA

        if self.relogio <= 0 and self.fim <= 0:
            self.relogio = 0.0
            self._acabar("ACABOU O TEMPO!", 0.6)

    def _dirigir(self, dt):
        esq = self._segurando(TECLAS_ESQ)
        dir_ = self._segurando(TECLAS_DIR)
        antes = self.angulo

        if self.ar > 0 and self.ar_rampa:
            # No ar as setas giram o trenó (manobra)
            if esq or dir_:
                self.giro_ar += (dir_ - esq) * GIRO_AR * dt
        elif self.ar <= 0:
            if esq or dir_:
                self.mouse_x = None
                self.angulo += (dir_ - esq) * GIRO * dt
            elif self.mouse_x is not None:
                alvo = max(-ANGULO_MAX, min(ANGULO_MAX, (self.mouse_x - self.x) * 0.35))
                passo = GIRO * dt
                self.angulo += max(-passo, min(passo, alvo - self.angulo))
            self.angulo = max(-ANGULO_MAX, min(ANGULO_MAX, self.angulo))
        self.girando = abs(self.angulo - antes) / max(dt, 1e-6)

        # Velocidade no eixo do trenó
        if self._segurando(TECLAS_RAPIDO):
            alvo = VEL_AGACHADO
        elif self._segurando(TECLAS_FREIO):
            alvo = VEL_FREIO
        else:
            alvo = VEL_BASE
        # De lado o trenó anda mais devagar
        alvo *= 1 - 0.35 * abs(math.sin(math.radians(self.angulo)))
        if self.ar <= 0:
            if self.vel < alvo:
                self.vel = min(alvo, self.vel + ACEL * dt)
            else:
                self.vel = max(alvo, self.vel - FREADA * dt)

    def _pousar(self):
        self.ar = 0.0
        if self.ar_rampa:
            if abs(self.giro_ar) >= 330:
                voltas = int((abs(self.giro_ar) + 30) // 360)
                self.manobras += voltas
                self.som("acerto")
                txt = "MANOBRA!" if voltas == 1 else f"MANOBRA x{voltas}!"
                self.textos.adicionar(txt + f" +{PONTOS_MANOBRA * voltas}", (self.x, OVO_Y - 70), AMARELO, 18)
                cores = [self.jogador.cor, self.jogador.cor_clara, AMARELO, BRANCO]
                self.particulas.explodir((self.x, OVO_Y), cores, 24, 260, 0.7)
            else:
                self.som("pulo", 0.4)
        self.giro_ar = 0.0
        self.particulas.explodir((self.x, OVO_Y + 10), [BRANCO, (225, 235, 250)], 12, 150, 0.5, (2, 5), 300)

    def _bandeiras(self, y_antes):
        for o in self.objetos:
            if o.tipo == "bandeira" and not o.passou and y_antes < o.y <= self.dist:
                o.passou = True
                if abs(self.x - o.x) <= VAO_BANDEIRA / 2:
                    self.bandeiras += 1
                    self.relogio += BONUS_BANDEIRA
                    self.som("moeda", 0.7)
                    lado = 1 if self.x < LARGURA - 260 else -1
                    self.textos.adicionar(f"BANDEIRA +{BONUS_BANDEIRA}s", (self.x + lado * 150, OVO_Y + 10),
                                          (50, 130, 50), 14)
                    self.particulas.explodir((o.x, OVO_Y), [(230, 60, 60), (60, 110, 230), AMARELO], 14, 180, 0.5)
                else:
                    self.relogio -= MULTA_BANDEIRA
                    self.som("erro", 0.6)
                    lado = 1 if self.x < LARGURA - 260 else -1
                    self.textos.adicionar(f"-{int(MULTA_BANDEIRA)}s", (self.x + lado * 120, OVO_Y + 10),
                                          (230, 60, 60), 18)
            elif o.tipo == "rampa" and not o.passou and self.ar <= 0 and self.tombo <= 0:
                if abs(self.x - o.x) < 44 and abs(self.dist - o.y) < 18:
                    o.passou = True
                    self._decolar(TEMPO_RAMPA, rampa=True)
                    self.som("mola", 0.7)

    def _colidir(self):
        if self.ar > 0 or self.tombo > 0 or self.invencivel > 0:
            return
        for o in self.objetos:
            if o.encosta(self.x, self.dist, RAIO_OVO):
                self._bater(o)
                return

    def _bater(self, o):
        self.batidas += 1
        self.tombo = TEMPO_TOMBO
        self.vel = 0.0
        self.tremer(0.25)
        self.som("bater")
        self.rastro.append(None)
        self.particulas.explodir((self.x, OVO_Y), [BRANCO, (220, 230, 245), (200, 215, 240)], 30, 260, 0.8, (3, 7))
        if o.tipo in ("pinheiro", "pinheiro_g"):
            # A neve do pinheiro cai
            self.particulas.explodir((o.x, o.y - self.dist + OVO_Y - 50), [BRANCO], 16, 120, 0.8, (2, 5), 400)
        restam = BATIDAS - self.batidas
        self.textos.adicionar("TOMBOU!" if restam > 0 else "AI!", (self.x, OVO_Y - 60), (230, 70, 70), 18)

    def _rastro(self):
        if self.ar > 0 or self.tombo > 0:
            return
        if self.dist - self.ultimo_rastro >= 8 or not self.rastro:
            self.ultimo_rastro = self.dist
            self.rastro.append((self.x, self.dist, self.angulo))
            if len(self.rastro) > 70:
                del self.rastro[:len(self.rastro) - 70]

    def _flocos(self, dt):
        for f in self.flocos:
            f[1] += f[2] * dt
            f[0] += math.sin(self.tempo + f[3]) * 20 * dt
            if f[1] > ALTURA + 5:
                f[1] = -5
                f[0] = random.uniform(0, LARGURA)

    def _efeitos(self, dt, vy):
        # Jato de neve nas curvas fechadas
        if self.ar <= 0 and self.tombo <= 0 and self.girando > 100 and self.vel > 220:
            lado = -1 if self.angulo > 0 else 1
            self.particulas.explodir((self.x + lado * 18, OVO_Y + 12), [BRANCO, (225, 235, 250)],
                                     2, 140, 0.4, (2, 5), 200)
        # Linhas de velocidade
        if vy > 600 and random.random() < dt * 20:
            x = random.choice((random.uniform(20, 300), random.uniform(724, 1004)))
            self.linhas.append([x, ALTURA + 10, random.uniform(40, 110)])
        for l in self.linhas:
            l[1] -= vy * 1.6 * dt
        self.linhas = [l for l in self.linhas if l[1] + l[2] > 0]

    def _boneco(self, dt, vy):
        if self.boneco_y is None:
            if self.metros >= METROS_BONECO:
                self.boneco_y = self.dist - DIST_BONECO
                self.boneco_x = self.x
                self.som("explosao", 0.5)
                self.textos.adicionar("O BONECO GIGANTE!", (LARGURA // 2, 160), (80, 150, 230), 20)
            return
        # Persegue 20 px/s mais devagar que a sua média, mas não "teleporta"
        # quando você para (no máximo 150 px/s mais rápido que você agora)
        vel = max(120.0, self.vel_media - 20)
        vel = min(vel, max(0.0, vy) + 150)
        self.boneco_y += vel * dt
        # Não deixa ele ficar muito para trás (continua ameaçando)
        self.boneco_y = max(self.boneco_y, self.dist - 400)
        # Vai para o lado onde o ovo está (sem ser instantâneo)
        passo = 260 * dt
        self.boneco_x += max(-passo, min(passo, self.x - self.boneco_x))
        if self.dist - self.boneco_y < RAIO_BONECO + RAIO_OVO and abs(self.x - self.boneco_x) < RAIO_BONECO + 30:
            self.abracado = True
            self.tremer(0.4)
            self.som("explosao", 0.7)
            self._acabar("ABRAÇO GELADO!", 1.6)

    def _acabar(self, motivo, espera):
        self.motivo = motivo
        self.fim = espera
        self.vel = 0.0

    def _terminar(self):
        self.terminar(titulo=self.motivo, linhas=[f"DISTÂNCIA: {self.metros} m",
                                                 f"BANDEIRAS: {self.bandeiras}  MANOBRAS: {self.manobras}",
                                                 f"PONTOS: {self.pontos}"])

    # --------------------------------------------------------
    # DESENHO
    # --------------------------------------------------------

    def _tela_y(self, y):
        return y - self.dist + OVO_Y

    def _desenhar_rastro(self, tela):
        ant = None
        for p in self.rastro:
            if p is None:
                ant = None
                continue
            if ant is not None:
                x0, y0, a0 = ant
                x1, y1, a1 = p
                sy0, sy1 = self._tela_y(y0), self._tela_y(y1)
                if sy1 > -10:
                    for lado in (-1, 1):
                        ox0 = math.cos(math.radians(a0)) * 9 * lado
                        oy0 = -math.sin(math.radians(a0)) * 9 * lado
                        ox1 = math.cos(math.radians(a1)) * 9 * lado
                        oy1 = -math.sin(math.radians(a1)) * 9 * lado
                        pygame.draw.line(tela, RASTRO, (x0 + ox0, sy0 + oy0), (x1 + ox1, sy1 + oy1), 3)
            ant = p

    def _desenhar_bandeira(self, tela, o, sy):
        cor = (230, 60, 60) if o.cor == 0 else (60, 110, 230)
        passou_ok = o.passou and abs(self.x - o.x) <= VAO_BANDEIRA / 2
        for lado in (-1, 1):
            px = int(o.x + lado * VAO_BANDEIRA / 2)
            pygame.draw.ellipse(tela, SOMBRA_NEVE, (px - 8, int(sy) - 3, 16, 6))
            pygame.draw.line(tela, (70, 70, 80), (px, int(sy)), (px, int(sy) - 46), 3)
            onda = math.sin(self.tempo * 6 + lado) * 3
            ponta = (px + 20 * -lado, int(sy) - 38 + onda)
            pygame.draw.polygon(tela, ui.escurecer(cor, 60), [(px, int(sy) - 47), ponta, (px, int(sy) - 29)])
            pygame.draw.polygon(tela, cor, [(px, int(sy) - 45), (ponta[0] + 2 * lado, ponta[1]), (px, int(sy) - 31)])
        if passou_ok:
            ui.estrela(tela, (int(o.x), int(sy) - 20), 8, AMARELO, self.tempo * 3)

    def _desenhar_rampa(self, tela, o, sy):
        r = pygame.Rect(0, 0, 88, 40)
        r.midbottom = (int(o.x), int(sy) + 6)
        pygame.draw.rect(tela, (150, 190, 235), r.move(0, 4), border_radius=8)
        pygame.draw.rect(tela, (200, 225, 250), r, border_radius=8)
        pygame.draw.rect(tela, (120, 160, 220), r, 3, border_radius=8)
        for i in range(3):
            y = r.y + 8 + i * 10
            pygame.draw.polygon(tela, (60, 110, 230), [(r.centerx - 10, y), (r.centerx + 10, y), (r.centerx, y + 7)])

    def _desenhar_objeto(self, tela, o):
        sy = self._tela_y(o.y)
        if o.tipo == "bandeira":
            self._desenhar_bandeira(tela, o, sy)
        elif o.tipo == "rampa":
            self._desenhar_rampa(tela, o, sy)
        else:
            s = _sprite(o.tipo)
            tela.blit(s, s.get_rect(midbottom=(int(o.x), int(sy) + 6)))

    def _desenhar_cachecol(self, tela, x, y, dirx, diry):
        """Cachecol esvoaçando para trás (contra o movimento)."""
        pts = []
        px, py = -diry, dirx                # perpendicular
        for i in range(7):
            d = i * 6
            onda = math.sin(self.tempo * 14 - i * 0.9) * (1.5 + i * 1.2)
            pts.append((x - dirx * d + px * onda, y - diry * d + py * onda))
        pygame.draw.lines(tela, (150, 30, 40), False, pts, 9)
        pygame.draw.lines(tela, (255, 214, 64), False, pts, 6)
        for i in range(1, len(pts), 2):
            pygame.draw.circle(tela, (230, 60, 60), (int(pts[i][0]), int(pts[i][1])), 3)

    def _desenhar_ovo(self, tela):
        x = self.x
        altura = 0.0
        if self.ar > 0 and self.ar_total > 0:
            t = 1 - self.ar / self.ar_total
            altura = math.sin(math.pi * t) * (ALTURA_RAMPA if self.ar_rampa else ALTURA_PULINHO)

        # Sombra (se afasta quando está no ar)
        larg = int(46 - altura * 0.3)
        pygame.draw.ellipse(tela, SOMBRA_NEVE, (int(x) - larg // 2 + int(altura * 0.4), OVO_Y + 10, larg, 14))

        if self.tombo > 0:
            # Virou uma bola de neve com olhos rolando!
            giro = (1 - self.tombo / TEMPO_TOMBO) * 720
            treno = pygame.transform.rotate(_sprite("treno"), 100 + giro * 0.2)
            tela.blit(treno, treno.get_rect(center=(int(x) + 30, OVO_Y + 6)))
            cx, cy = int(x), OVO_Y - 14
            pygame.draw.circle(tela, (150, 170, 210), (cx, cy), 27)
            pygame.draw.circle(tela, BRANCO, (cx, cy), 25)
            pygame.draw.circle(tela, (225, 235, 250), (cx + 6, cy + 8), 12)
            for k in (-1, 1):
                a = math.radians(giro) + k * 0.5
                ex, ey = cx + math.cos(a) * 9, cy + math.sin(a) * 9
                pygame.draw.circle(tela, BRANCO, (int(ex), int(ey)), 6)
                pygame.draw.circle(tela, (20, 20, 30), (int(ex), int(ey)), 3)
            ui.estrela(tela, (cx + math.cos(self.tempo * 6) * 30, cy - 30), 7, AMARELO, self.tempo * 4)
            return

        if self.invencivel > 0 and int(self.invencivel * 12) % 2 == 0:
            return

        escala = 1 + altura / 160
        ang_treno = self.angulo + (self.giro_ar if self.ar_rampa else 0)
        treno = _sprite("treno")
        if escala > 1.01:
            treno = pygame.transform.smoothscale(treno, (int(treno.get_width() * escala),
                                                         int(treno.get_height() * escala)))
        treno = pygame.transform.rotate(treno, ang_treno)
        cy = OVO_Y - altura
        tela.blit(treno, treno.get_rect(center=(int(x), int(cy))))

        a = math.radians(ang_treno)
        dirx, diry = math.sin(a), math.cos(a)
        self._desenhar_cachecol(tela, x - dirx * 8, cy - 16 - diry * 8, dirx, diry)

        # O ovo sentado na parte de trás do trenó (inclina para o lado da
        # curva; gira junto na manobra)
        inclina = -self.angulo * 0.35 + (-self.giro_ar if self.ar_rampa else 0)
        self.jogador.desenhar(tela, (x - dirx * 8, cy - 18 - diry * 6), OVO_ALT * escala, angulo=inclina)
        if self.abracado:
            # Congelando no abraço
            for i in range(3):
                a = self.tempo * 3 + i * math.tau / 3
                ui.estrela(tela, (x + math.cos(a) * 34, cy - 20 + math.sin(a) * 12), 6, (170, 220, 255), a)

    def _desenhar_boneco(self, tela):
        if self.boneco_y is None:
            return
        sy = self._tela_y(self.boneco_y)
        if sy < -40:
            # Fora da tela (lá atrás): setinha de aviso
            if int(self.tempo * 4) % 2 == 0:
                x = LARGURA // 2
                pygame.draw.polygon(tela, (230, 50, 50), [(x - 16, 72), (x + 16, 72), (x, 96)])
                ui.desenhar_texto(tela, "!", (x, 80), 12, BRANCO, "center")
            return
        x = int(self.boneco_x)
        contorno = (140, 170, 220)
        y = int(sy)
        balanco = math.sin(self.tempo * 5) * 4
        # Braços de galho
        for lado in (-1, 1):
            bx = x + lado * 40
            by = y - 88
            mao = (x + lado * (96 + (10 if self.abracado else 0)), by - 30 + balanco * lado)
            pygame.draw.line(tela, (110, 70, 40), (bx, by), mao, 7)
            pygame.draw.line(tela, (110, 70, 40), mao, (mao[0] + lado * 14, mao[1] - 16), 5)
            pygame.draw.line(tela, (110, 70, 40), mao, (mao[0] + lado * 18, mao[1] + 4), 5)
        for r, dy in ((60, 0), (45, -86), (32, -150)):
            pygame.draw.circle(tela, contorno, (x, y + dy), r + 3)
            pygame.draw.circle(tela, BRANCO, (x, y + dy), r)
            pygame.draw.circle(tela, (230, 238, 252), (x + r // 3, y + dy + r // 3), r // 2)
        # Botões
        for dy in (-100, -80, -60):
            pygame.draw.circle(tela, (40, 40, 50), (x, y + dy), 5)
        # Cachecol
        pygame.draw.rect(tela, (60, 170, 110), (x - 36, y - 124, 72, 14), border_radius=7)
        pygame.draw.rect(tela, (60, 170, 110), (x + 14, y - 118, 14, 40), border_radius=6)
        # Rosto: olhos, boca aberta sorrindo e... sem nariz (quer o seu ovo!)
        hy = y - 150
        pygame.draw.circle(tela, (30, 30, 40), (x - 12, hy - 8), 5)
        pygame.draw.circle(tela, (30, 30, 40), (x + 12, hy - 8), 5)
        pygame.draw.circle(tela, BRANCO, (x - 13, hy - 10), 2)
        boca = pygame.Rect(x - 16, hy + 4, 32, 18)
        pygame.draw.ellipse(tela, (60, 20, 40), boca)
        pygame.draw.ellipse(tela, (230, 90, 110), (boca.x + 8, boca.y + 9, 16, 8))
        pygame.draw.circle(tela, (255, 190, 200), (x - 22, hy + 4), 5)
        pygame.draw.circle(tela, (255, 190, 200), (x + 22, hy + 4), 5)

    def desenhar_jogo(self, tela):
        neve = _chao_neve()
        off = -(self.dist % ALTURA)
        tela.blit(neve, (0, off))
        tela.blit(neve, (0, off + ALTURA))

        self._desenhar_rastro(tela)

        # Rampas e bandeiras primeiro (ficam no chão); o resto por altura
        visiveis = [o for o in self.objetos if -60 < self._tela_y(o.y) < ALTURA + 130]
        for o in visiveis:
            if o.tipo == "rampa":
                self._desenhar_objeto(tela, o)
        # (tombando ou no abraço o ovo fica por cima de tudo)
        por_cima = self.tombo > 0 or self.abracado
        ovo_desenhado = por_cima
        for o in sorted((o for o in visiveis if o.tipo != "rampa"), key=lambda o: o.y):
            if not ovo_desenhado and o.y > self.dist + 4:
                self._desenhar_ovo(tela)
                ovo_desenhado = True
            self._desenhar_objeto(tela, o)
        if not ovo_desenhado:
            self._desenhar_ovo(tela)

        self._desenhar_boneco(tela)
        if por_cima:
            self._desenhar_ovo(tela)

        for x, y, comp in self.linhas:
            pygame.draw.line(tela, (222, 230, 247), (int(x), int(y)), (int(x), int(y + comp)), 2)
        for x, y, _, _, tam in self.flocos:
            pygame.draw.circle(tela, BRANCO, (int(x), int(y)), tam)
            pygame.draw.circle(tela, (200, 215, 240), (int(x), int(y)), tam, 1)

        self.particulas.desenhar(tela)
        self.textos.desenhar(tela)

        # Aviso: o boneco está chegando
        if self.boneco_y is None and self.estado == "jogando" and \
                METROS_BONECO - AVISO_BONECO <= self.metros < METROS_BONECO:
            if int(self.tempo * 5) % 2 == 0:
                pygame.draw.circle(tela, (230, 50, 50), (LARGURA // 2, 96), 22)
                pygame.draw.circle(tela, BRANCO, (LARGURA // 2, 96), 22, 3)
                ui.desenhar_texto(tela, "!", (LARGURA // 2 + 2, 98), 24, BRANCO, "center")

    def desenhar_hud(self, tela):
        escuro = (20, 24, 40)
        caixa = pygame.Rect(12, 12, 400, 48)
        ui.painel(tela, caixa, escuro, BRANCO, 12, 3, sombra=False)
        ui.desenhar_texto(tela, f"PONTOS: {self.pontos}", (caixa.x + 16, caixa.centery), 14,
                          AMARELO, "midleft")
        rec = self.recorde()
        if rec is not None:
            ui.desenhar_texto(tela, f"RECORDE: {rec}", (caixa.x + 226, caixa.centery), 12,
                              (180, 200, 255), "midleft")

        # Relógio
        caixa = pygame.Rect(424, 12, 176, 48)
        pouco = self.relogio < 10
        cor = (255, 110, 110) if pouco else BRANCO
        ui.painel(tela, caixa, escuro, cor, 12, 3, sombra=False)
        seg = max(0, math.ceil(self.relogio))
        tam = 20 if pouco and int(self.tempo * 4) % 2 == 0 else 18
        ui.desenhar_texto(tela, f"{seg // 60}:{seg % 60:02d}", caixa.center, tam, cor, "center")

        # Trenós restantes
        caixa = pygame.Rect(0, 12, 150, 48)
        caixa.right = LARGURA - 76
        ui.painel(tela, caixa, escuro, BRANCO, 12, 3, sombra=False)
        mini = pygame.transform.smoothscale(_sprite("treno"), (22, 31))
        for i in range(BATIDAS):
            c = (caixa.x + 32 + i * 43, caixa.centery)
            if i < BATIDAS - self.batidas:
                tela.blit(mini, mini.get_rect(center=c))
            else:
                pygame.draw.line(tela, (110, 110, 130), (c[0] - 8, c[1] - 8), (c[0] + 8, c[1] + 8), 3)
                pygame.draw.line(tela, (110, 110, 130), (c[0] + 8, c[1] - 8), (c[0] - 8, c[1] + 8), 3)

        # Metros e bandeiras
        caixa = pygame.Rect(12, 68, 300, 36)
        ui.painel(tela, caixa, escuro, BRANCO, 10, 2, sombra=False)
        ui.desenhar_texto(tela, f"↓ {self.metros} m", (caixa.x + 12, caixa.centery), 12,
                          (180, 220, 255), "midleft")
        x = caixa.x + 170
        pygame.draw.line(tela, (200, 200, 210), (x, caixa.centery + 9), (x, caixa.centery - 9), 2)
        pygame.draw.polygon(tela, (230, 60, 60), [(x, caixa.centery - 9), (x + 12, caixa.centery - 4),
                                                  (x, caixa.centery + 1)])
        ui.desenhar_texto(tela, f"×{self.bandeiras}", (x + 18, caixa.centery), 12, AMARELO, "midleft")
        if self.recarga <= 0 and self.ar <= 0:
            ui.desenhar_texto(tela, "PULO", (caixa.right - 12, caixa.centery), 10, (140, 230, 140), "midright")
