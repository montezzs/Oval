import math
import random

import pygame

from settings import *
from core import ui
from jogos.base import MiniJogo

# ============================================================
# ATRAVESSA A RUA
# ============================================================
# Por que o ovo atravessou a rua? Para chegar no ninho da
# família! Leve o seu ovo pela calçada, pela rua (cuidado com
# os carros, as bicicletas e o ÔNIBUS VERMELHO), pelo canteiro
# e pelo rio (pulando em troncos, patinhos e vitórias-régias)
# até os 5 ninhos lá em cima.
#
# Faixas (de baixo para cima):
#   0 calçada | 1-4 rua | 5 canteiro | 6-9 rio | 10 margem com ninhos

COLUNAS = 16
CEL = 64                        # largura de uma coluna
FAIXA = 60                      # altura de uma faixa
FAIXAS = 11
Y_TOPO = ALTURA - FAIXAS * FAIXA   # 60: em cima fica o HUD

RUA = (1, 2, 3, 4)
RIO = (6, 7, 8, 9)
TERRA = (0, 5, 10)

NINHOS_X = (96, 304, 512, 720, 928)
RAIO_NINHO = 40

ALTURA_OVO = 44
LARG_OVO = ALTURA_OVO * 0.9
TEMPO_PULO = 0.12
REPETICAO = 0.18
TEMPO_TRAVESSIA = 40.0
VIDAS = 3
ACELERA_NIVEL = 1.15
MAX_FATOR = 2.0

# Vitórias-régias: afundam 1.5 s a cada 4 s
CICLO_VITORIA = 4.0
AFUNDADA = 1.5

TECLAS = {
    pygame.K_UP: (0, 1), pygame.K_w: (0, 1),
    pygame.K_DOWN: (0, -1), pygame.K_s: (0, -1),
    pygame.K_LEFT: (-1, 0), pygame.K_a: (-1, 0),
    pygame.K_RIGHT: (1, 0), pygame.K_d: (1, 0),
}

# Cores do cenário
CALCADA = (170, 170, 170)
ASFALTO = (40, 40, 45)
FAIXA_AMARELA = (255, 230, 60)
CANTEIRO = (80, 200, 80)
RIO_COR = (60, 140, 230)
ONDA = (120, 190, 255)
MARGEM = (60, 170, 70)
TRONCO = (130, 85, 45)
ANEL = (170, 120, 70)
CORES_CARRO = ((60, 120, 230), (255, 200, 40), (120, 200, 90))

# Configuração das faixas: tipo, direção, velocidade, (vão mínimo, vão máximo)
CONFIG = {
    1: ("carro", -1, 95, (230, 340)),
    2: ("onibus", 1, 70, (260, 380)),
    3: ("bici", -1, 210, (280, 400)),
    4: ("carro", 1, 140, (230, 330)),
    6: ("tronco", 1, 75, (70, 128)),
    7: ("patos", -1, 105, (80, 128)),
    8: ("vitorias", 1, 60, (40, 100)),
    9: ("tronco", -1, 125, (80, 128)),
}


def _y_faixa(i):
    """Centro (y) da faixa i."""
    return ALTURA - FAIXA * i - FAIXA // 2


def _coluna(x):
    """Centro da coluna mais próxima."""
    c = max(0, min(COLUNAS - 1, int(x // CEL)))
    return c * CEL + CEL // 2


# ============================================================
# SPRITES (com cache)
# ============================================================

_cache = {}


def _carro(cor):
    """Carrinho visto de lado, virado para a direita (90x46)."""
    chave = ("carro", cor)
    if chave in _cache:
        return _cache[chave]
    s = pygame.Surface((90, 46), pygame.SRCALPHA)
    escura = ui.escurecer(cor, 60)
    # Cabine
    pygame.draw.rect(s, escura, (18, 2, 50, 26), border_radius=10)
    pygame.draw.rect(s, cor, (20, 4, 46, 24), border_radius=9)
    pygame.draw.rect(s, (200, 230, 255), (26, 8, 16, 14), border_radius=3)
    pygame.draw.rect(s, (200, 230, 255), (46, 8, 16, 14), border_radius=3)
    # Corpo
    pygame.draw.rect(s, escura, (2, 18, 86, 20), border_radius=8)
    pygame.draw.rect(s, cor, (4, 20, 82, 16), border_radius=7)
    pygame.draw.rect(s, ui.clarear(cor, 60), (10, 22, 60, 4), border_radius=2)
    pygame.draw.rect(s, (255, 250, 180), (80, 24, 6, 6), border_radius=2)     # farol
    pygame.draw.rect(s, (230, 60, 60), (4, 24, 4, 6))                          # lanterna
    # Rodas
    for x in (22, 68):
        pygame.draw.circle(s, (20, 20, 20), (x, 38), 8)
        pygame.draw.circle(s, (150, 150, 160), (x, 38), 3)
    _cache[chave] = s
    return s


def _onibus():
    """Ônibus vermelho (180x50) como o do quadro da casa."""
    if "onibus" in _cache:
        return _cache["onibus"]
    s = pygame.Surface((180, 50), pygame.SRCALPHA)
    pygame.draw.rect(s, (150, 20, 20), (0, 0, 180, 42), border_radius=10)
    pygame.draw.rect(s, (230, 30, 30), (2, 2, 176, 38), border_radius=9)
    for i in range(6):
        pygame.draw.rect(s, (60, 110, 200), (10 + i * 26, 7, 20, 14), border_radius=3)
        pygame.draw.rect(s, (150, 190, 255), (12 + i * 26, 9, 7, 5), border_radius=2)
    pygame.draw.rect(s, (60, 110, 200), (162, 7, 12, 22), border_radius=3)     # para-brisa
    pygame.draw.rect(s, (255, 230, 120), (2, 26, 176, 5))
    pygame.draw.rect(s, (255, 250, 180), (172, 32, 6, 6), border_radius=2)
    for x in (34, 146):
        pygame.draw.circle(s, (20, 20, 20), (x, 42), 8)
        pygame.draw.circle(s, (150, 150, 160), (x, 42), 3)
    _cache["onibus"] = s
    return s


def _bici(jogador, n):
    """Bicicleta com um ovinho da família pedalando (56x44)."""
    chave = ("bici", n)
    if chave in _cache:
        return _cache[chave]
    s = pygame.Surface((56, 44), pygame.SRCALPHA)
    for x in (12, 44):
        pygame.draw.circle(s, (20, 20, 20), (x, 34), 9, 3)
    cor = ((240, 120, 40), (150, 80, 220), (40, 170, 200))[n % 3]
    pygame.draw.lines(s, cor, False, [(12, 34), (24, 22), (40, 22), (44, 34)], 3)
    pygame.draw.line(s, cor, (24, 22), (28, 34), 3)
    pygame.draw.line(s, (60, 60, 60), (40, 22), (42, 14), 3)
    ap = ((n + 1) % 4, (n * 3 + 2) % 8, n % 3, (n + 2) % 6)
    jogador.desenhar(s, (26, 13), 20, aparencia=ap)
    _cache[chave] = s
    return s


def _tronco(largura):
    chave = ("tronco", largura)
    if chave in _cache:
        return _cache[chave]
    h = 44
    s = pygame.Surface((largura, h), pygame.SRCALPHA)
    pygame.draw.rect(s, (90, 55, 25), (0, 2, largura, h - 2), border_radius=18)
    pygame.draw.rect(s, TRONCO, (0, 0, largura, h - 4), border_radius=18)
    rnd = random.Random(largura)
    for _ in range(largura // 22):
        x = rnd.randint(22, largura - 40)
        y = rnd.randint(8, h - 14)
        pygame.draw.line(s, (100, 62, 30), (x, y), (x + rnd.randint(14, 30), y), 2)
    for x in (4, largura - 30):
        pygame.draw.ellipse(s, ANEL, (x, 3, 26, h - 10))
        pygame.draw.ellipse(s, (130, 85, 45), (x + 6, 10, 14, h - 24), 2)
    _cache[chave] = s
    return s


def _pato():
    if "pato" in _cache:
        return _cache["pato"]
    s = pygame.Surface((50, 44), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (200, 150, 20), (2, 18, 44, 24))
    pygame.draw.ellipse(s, (255, 214, 40), (3, 17, 42, 22))
    pygame.draw.circle(s, (200, 150, 20), (36, 14), 12)
    pygame.draw.circle(s, (255, 214, 40), (36, 13), 11)
    pygame.draw.polygon(s, (255, 130, 40), [(44, 12), (50, 15), (44, 18)])
    pygame.draw.circle(s, (20, 20, 20), (39, 10), 2)
    pygame.draw.ellipse(s, (240, 190, 30), (12, 22, 18, 10))
    _cache["pato"] = s
    return s


def _vitoria():
    if "vitoria" in _cache:
        return _cache["vitoria"]
    s = pygame.Surface((56, 50), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (40, 120, 50), (1, 3, 54, 46))
    pygame.draw.ellipse(s, (70, 180, 80), (3, 4, 50, 42))
    pygame.draw.polygon(s, RIO_COR, [(28, 25), (46, 8), (52, 16)])
    for a in (0.6, 1.8, 2.8, 4.0, 5.2):
        pygame.draw.line(s, (100, 205, 110), (28, 25), (28 + math.cos(a) * 20, 25 + math.sin(a) * 16), 2)
    _cache["vitoria"] = s
    return s


def _flor(tela, c):
    """Florzinha rosa (marca as vitórias-régias que não afundam)."""
    x, y = c
    for a in range(0, 360, 72):
        r = math.radians(a)
        pygame.draw.circle(tela, (255, 150, 190), (int(x + math.cos(r) * 5), int(y + math.sin(r) * 5)), 4)
    pygame.draw.circle(tela, (255, 230, 120), (x, y), 3)


# ============================================================
# COISAS QUE ANDAM NAS FAIXAS
# ============================================================

class Ent:

    def __init__(self, x, largura, tipo, extra=0):
        self.x = x
        self.largura = largura
        self.tipo = tipo
        self.extra = extra          # cor do carro / fase da vitória-régia
        self.buzinou = False


class Faixa:

    def __init__(self, indice, fator, rnd):
        tipo, direcao, vel, (gmin, gmax) = CONFIG[indice]
        self.indice = indice
        self.tipo = tipo
        self.direcao = direcao
        self.vel_base = vel
        self.vel = vel * fator
        self.ents = []

        x = rnd.uniform(-120, 60)
        inicio = x
        n = 0
        while x < inicio + LARGURA + 320:
            if tipo == "carro":
                ent = Ent(x, 90, "carro", CORES_CARRO[(n + indice) % 3])
            elif tipo == "onibus":
                ent = Ent(x, 180, "onibus") if n % 2 == 0 else Ent(x, 90, "carro", CORES_CARRO[n % 3])
            elif tipo == "bici":
                ent = Ent(x, 56, "bici", n)
            elif tipo == "tronco":
                larg = rnd.choice((150, 190, 220)) if indice == 6 else rnd.choice((190, 230, 260))
                ent = Ent(x, larg, "tronco")
            elif tipo == "patos":
                ent = Ent(x, 150, "patos")
            else:
                ent = Ent(x, 168, "vitorias", n * 1.37)
            self.ents.append(ent)
            x += ent.largura + rnd.uniform(gmin, gmax)
            n += 1
        # Só metade das vitórias-régias afunda (as de flor rosa ficam
        # sempre boiando) e as fases são espalhadas: nunca afundam juntas
        if tipo == "vitorias":
            for i, e in enumerate(self.ents):
                e.extra = i * CICLO_VITORIA / len(self.ents) if i % 2 == 0 else None
        self.volta = x - inicio

    def atualizar(self, dt):
        dx = self.vel * self.direcao * dt
        for e in self.ents:
            e.x += dx
            if self.direcao > 0 and e.x > LARGURA:
                e.x -= self.volta
            elif self.direcao < 0 and e.x + e.largura < 0:
                e.x += self.volta
        return dx


def _ciclo_vitoria(ent, t):
    """Posição no ciclo de afundar (0 para as que nunca afundam)."""
    if ent.extra is None:
        return 0.0
    return (t + ent.extra) % CICLO_VITORIA


def _submersa(ent, t):
    return ent.tipo == "vitorias" and _ciclo_vitoria(ent, t) >= CICLO_VITORIA - AFUNDADA


# ============================================================
# JOGO
# ============================================================

class Atravessa(MiniJogo):

    ID = "atravessa"
    TITULO = "ATRAVESSA A RUA"
    TITULO_CURTO = "ATRAVESSA"
    DESCRICAO = "Leve o seu ovo pela rua e pelo rio até os ninhos da família. Cuidado com o ônibus vermelho!"
    COR = (230, 60, 50)
    INSTRUCOES = [
        "Atravesse a RUA e o RIO até os 5 ninhos lá em cima!",
        "Carro frita o ovo! No rio, pule nos troncos.",
        "Vitórias-régias afundam de vez em quando!",
        "Leve o PINTINHO PERDIDO ao ninho: +300!",
        "SETAS ou WASD (ou clique) para pular",
    ]
    OPCOES = None
    MENOR_MELHOR = False
    ROTULO_PONTOS = "PONTOS"
    CONTAGEM = True

    TRILHA = dict(bpm=140, tom="G", escala="mixolidia", lead="quadrada", duty=0.5,
                  envelope="staccato", baixo="oompah", onda_baixo="triangulo",
                  acomp="contratempo", onda_acomp="quadrada", bateria="rock",
                  energia=0.65, eco=(0.12, 0.15))

    MOEDAS_POR = 80
    MOEDAS_MAX = 45
    MOEDAS_MIN = 1

    # --------------------------------------------------------
    # CENÁRIO
    # --------------------------------------------------------

    @classmethod
    def criar_fundo(cls, jogador):
        sup = pygame.Surface((LARGURA, ALTURA))
        sup.fill((28, 30, 44))
        rnd = random.Random(4)

        def faixa_rect(i):
            return pygame.Rect(0, ALTURA - FAIXA * (i + 1), LARGURA, FAIXA)

        # Calçada com juntas
        r = faixa_rect(0)
        pygame.draw.rect(sup, CALCADA, r)
        for x in range(0, LARGURA, 64):
            pygame.draw.line(sup, (140, 140, 145), (x, r.y), (x, r.bottom), 2)
        pygame.draw.line(sup, (140, 140, 145), (0, r.centery), (LARGURA, r.centery), 1)
        pygame.draw.rect(sup, (120, 120, 125), (0, r.y, LARGURA, 6))            # meio-fio

        # Rua
        rua = faixa_rect(4).union(faixa_rect(1))
        pygame.draw.rect(sup, ASFALTO, rua)
        for _ in range(300):
            x, y = rnd.randrange(LARGURA), rnd.randrange(rua.y, rua.bottom)
            pygame.draw.circle(sup, (52, 52, 58), (x, y), 1)
        for i in (1, 2, 3):
            y = ALTURA - FAIXA * (i + 1)
            cor = FAIXA_AMARELA if i == 2 else (200, 200, 200)
            for x in range(10, LARGURA, 80):
                pygame.draw.rect(sup, cor, (x, y - 3, 44, 6))

        # Canteiro com florzinhas
        r = faixa_rect(5)
        pygame.draw.rect(sup, CANTEIRO, r)
        pygame.draw.rect(sup, (120, 120, 125), (0, r.bottom - 6, LARGURA, 6))
        pygame.draw.rect(sup, (120, 120, 125), (0, r.y, LARGURA, 4))
        for _ in range(80):
            x, y = rnd.randrange(LARGURA), rnd.randrange(r.y + 8, r.bottom - 8)
            pygame.draw.line(sup, (60, 170, 60), (x, y), (x + rnd.randint(-2, 2), y - 6), 2)
        for _ in range(26):
            x, y = rnd.randrange(8, LARGURA - 8), rnd.randrange(r.y + 12, r.bottom - 12)
            cor = rnd.choice(((255, 255, 255), (255, 230, 90), (255, 130, 160)))
            for dx, dy in ((-3, 0), (3, 0), (0, -3), (0, 3)):
                pygame.draw.circle(sup, cor, (x + dx, y + dy), 3)
            pygame.draw.circle(sup, (255, 190, 40), (x, y), 2)

        # Rio
        rio = faixa_rect(9).union(faixa_rect(6))
        pygame.draw.rect(sup, RIO_COR, rio)
        for i in RIO:
            y = ALTURA - FAIXA * (i + 1)
            pygame.draw.line(sup, (70, 150, 235), (0, y), (LARGURA, y), 2)

        # Margem com os ninhos
        r = faixa_rect(10)
        pygame.draw.rect(sup, MARGEM, r)
        pygame.draw.rect(sup, (50, 140, 60), (0, r.bottom - 6, LARGURA, 6))
        for _ in range(60):
            x, y = rnd.randrange(LARGURA), rnd.randrange(r.y + 6, r.bottom - 8)
            pygame.draw.line(sup, (40, 130, 50), (x, y), (x + rnd.randint(-3, 3), y - 7), 2)
        # Arbustos entre os ninhos (não dá para pular neles)
        for a, b in zip((0,) + NINHOS_X, NINHOS_X + (LARGURA,)):
            ini = a + (RAIO_NINHO + 6 if a else 0)
            fim = b - (RAIO_NINHO + 6 if b < LARGURA else 0)
            x = ini + 14
            while x < fim - 10:
                pygame.draw.circle(sup, (30, 110, 45), (int(x), r.centery + 6), 17)
                pygame.draw.circle(sup, (45, 140, 55), (int(x), r.centery + 3), 14)
                pygame.draw.circle(sup, (80, 175, 80), (int(x) - 4, r.centery - 2), 5)
                x += 26
        for nx in NINHOS_X:
            cls._ninho(sup, (nx, r.centery + 8))
        return sup

    @staticmethod
    def _ninho(sup, c):
        x, y = c
        pygame.draw.ellipse(sup, (120, 90, 50), (x - 38, y - 16, 76, 34))
        pygame.draw.ellipse(sup, (180, 140, 80), (x - 34, y - 14, 68, 28))
        pygame.draw.ellipse(sup, (110, 80, 40), (x - 24, y - 10, 48, 16))
        rnd = random.Random(x)
        for _ in range(16):
            a = rnd.uniform(0, math.tau)
            px, py = x + math.cos(a) * 32, y + math.sin(a) * 12
            pygame.draw.line(sup, (220, 190, 120), (px, py),
                             (px + math.cos(a + 1.6) * 12, py + math.sin(a + 1.6) * 4), 2)

    @classmethod
    def desenhar_icone(cls, sup, jogador):
        w, h = sup.get_size()
        c = _carro(CORES_CARRO[0])
        c = pygame.transform.smoothscale(c, (54, 28))
        sup.blit(c, (w * 0.08, h * 0.62))
        o = pygame.transform.smoothscale(_onibus(), (100, 28))
        o = pygame.transform.flip(o, True, False)
        sup.blit(o, (w * 0.5, h * 0.7))
        jogador.desenhar(sup, (w // 2, int(h * 0.5)), 30)

    # --------------------------------------------------------
    # PARTIDA
    # --------------------------------------------------------

    def reiniciar(self):
        self.nivel = 1
        self.vidas = VIDAS
        self.relogio = 0.0
        self.ninhos = [False] * 5
        self.total_ninhos = 0
        self.pintinhos = 0
        self.teclas = []            # teclas de direção seguradas (ordem)
        self.pintinho = None
        self.proximo_pintinho = random.uniform(8, 14)
        self.banner = ""
        self.tempo_banner = 0.0
        self._montar_faixas()
        self._nascer()

    def _fator(self):
        return min(MAX_FATOR, ACELERA_NIVEL ** (self.nivel - 1))

    def _montar_faixas(self):
        rnd = random.Random(random.random())
        fator = self._fator()
        self.faixas = {i: Faixa(i, fator, rnd) for i in CONFIG}
        # Deixa a rua "rodando" um pouco para não começar tudo alinhado
        for f in self.faixas.values():
            for _ in range(20):
                f.atualizar(0.05)

    def _nascer(self):
        """Ovo novo na calçada (depois de morrer ou chegar num ninho)."""
        self.x = LARGURA / 2 + CEL / 2
        self.faixa = 0
        self.plataforma = None
        self.pulo = None
        self.fila = None
        self.repete = 0.0
        self.estado_ovo = "vivo"     # vivo, frito, afogado, tempo, ninho
        self.tempo_estado = 0.0
        self.max_faixa = 0
        self.restante = TEMPO_TRAVESSIA
        self.squash = 0.0
        self.bonk = 0.0
        self.espelhar = False
        self.buzina = 0.0

    # --------------------------------------------------------
    # CONTROLES
    # --------------------------------------------------------

    def evento(self, e):
        # Solta as teclas em qualquer estado (para não "grudar" na pausa)
        if e.type == pygame.KEYUP and e.key in self.teclas:
            self.teclas.remove(e.key)
        elif e.type == pygame.WINDOWFOCUSLOST:
            self.teclas.clear()
        super().evento(e)

    def evento_jogo(self, e):
        if e.type == pygame.KEYDOWN and e.key in TECLAS:
            if e.key in self.teclas:
                self.teclas.remove(e.key)
            self.teclas.append(e.key)
            self._pedir(TECLAS[e.key])
            self.repete = REPETICAO
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            ox, oy = self.x, self._y_ovo()
            dx, dy = e.pos[0] - ox, e.pos[1] - oy
            if abs(dx) < 12 and abs(dy) < 12:
                return
            if abs(dy) >= abs(dx):
                self._pedir((0, 1 if dy < 0 else -1))
            else:
                self._pedir((1 if dx > 0 else -1, 0))

    def _pedir(self, direcao):
        if self.estado_ovo != "vivo":
            return
        if self.pulo is None:
            self._pular(direcao)
        else:
            self.fila = direcao          # guarda para quando pousar

    def _pular(self, direcao):
        dx, df = direcao
        f1 = self.faixa + df
        if f1 < 0 or f1 > 10:
            return
        x1 = self.x + dx * CEL
        if dx:
            self.espelhar = dx < 0
        if f1 in TERRA or (df == 0 and self.faixa in TERRA):
            x1 = _coluna(x1)
        x1 = max(CEL / 2, min(LARGURA - CEL / 2, x1))

        if f1 == 10:
            # Só entra num ninho vazio; os arbustos bloqueiam
            alvo = None
            for i, nx in enumerate(NINHOS_X):
                if abs(self.x - nx) <= RAIO_NINHO and not self.ninhos[i]:
                    alvo = nx
            if alvo is None:
                self.bonk = 0.25
                self.som("erro", 0.4)
                return
            x1 = alvo

        self.pulo = [self.x, self.faixa, x1, f1, 0.0]
        self.plataforma = None
        self.som("pulo", 0.35)

    # --------------------------------------------------------
    # LÓGICA
    # --------------------------------------------------------

    def atualizar_jogo(self, dt):
        self.relogio += dt
        self.squash = max(0.0, self.squash - dt)
        self.bonk = max(0.0, self.bonk - dt)
        self.buzina = max(0.0, self.buzina - dt)
        self.tempo_banner = max(0.0, self.tempo_banner - dt)

        moveu = {i: f.atualizar(dt) for i, f in self.faixas.items()}
        self._atualizar_pintinho(dt, moveu)

        if self.estado_ovo != "vivo":
            self._atualizar_morto(dt)
            return

        # Tempo da travessia
        self.restante -= dt
        if self.restante <= 0:
            self.restante = 0
            self._morrer("tempo")
            return

        self.repete -= dt
        if self.pulo is not None:
            self.pulo[4] += dt
            if self.pulo[4] >= TEMPO_PULO:
                self._pousar()
        else:
            # Carregado pelo tronco / pato / vitória-régia
            if self.plataforma is not None:
                self.x += moveu[self.faixa]
                if self.x < 6 or self.x > LARGURA - 6:
                    self._morrer("afogado")
                    return
                if _submersa(self.plataforma, self.relogio):
                    self._morrer("afogado")
                    return
            # Segurar a tecla repete o pulo (a cada 0.18 s)
            if self.teclas and self.repete <= 0:
                self.repete = REPETICAO
                self._pedir(TECLAS[self.teclas[-1]])

        if self.estado_ovo == "vivo":
            self._checar_rua()

    def _faixa_atual(self):
        if self.pulo is not None and self.pulo[4] >= TEMPO_PULO / 2:
            return self.pulo[3]
        return self.pulo[1] if self.pulo is not None else self.faixa

    def _x_atual(self):
        if self.pulo is None:
            return self.x
        x0, _, x1, _, t = self.pulo
        s = min(1.0, t / TEMPO_PULO)
        return x0 + (x1 - x0) * s

    def _y_ovo(self):
        """Centro do ovo na tela (com o arco do pulo)."""
        if self.pulo is None:
            return _y_faixa(self.faixa)
        _, f0, _, f1, t = self.pulo
        s = min(1.0, t / TEMPO_PULO)
        y = _y_faixa(f0) + (_y_faixa(f1) - _y_faixa(f0)) * s
        return y - math.sin(s * math.pi) * 14

    def _checar_rua(self):
        f = self._faixa_atual()
        if f not in RUA:
            return
        x = self._x_atual()
        meia = LARG_OVO * 0.8 / 2
        faixa = self.faixas[f]
        for e in faixa.ents:
            ini, fim = e.x + 5, e.x + e.largura - 5
            if x + meia > ini and x - meia < fim:
                self._morrer("frito")
                return
            # Buzina quando um carro chega perto
            frente = e.x + e.largura if faixa.direcao > 0 else e.x
            dist = (x - meia - frente) if faixa.direcao > 0 else (frente - (x + meia))
            if 0 < dist < 70 and not e.buzinou and self.buzina <= 0 and e.tipo != "bici":
                e.buzinou = True
                self.buzina = 1.2
                self.som("bater", 0.25)
                self.textos.adicionar("BI-BI!", (e.x + e.largura / 2, _y_faixa(f) - 34), BRANCO, 10)
        # Libera a buzina dos carros que já passaram
        for e in faixa.ents:
            if e.buzinou and (e.x > LARGURA or e.x + e.largura < 0):
                e.buzinou = False

    def _pousar(self):
        x0, f0, x1, f1, _ = self.pulo
        self.pulo = None
        self.x = x1
        self.faixa = f1
        self.squash = 0.12

        if f1 in RIO:
            plataforma = None
            for e in self.faixas[f1].ents:
                if e.x - 6 <= x1 <= e.x + e.largura + 6 and not _submersa(e, self.relogio):
                    plataforma = e
                    break
            if plataforma is None:
                self._morrer("afogado")
                return
            self.plataforma = plataforma
            # Pegou o pintinho perdido?
            p = self.pintinho
            if p and p["estado"] == "tronco" and p["ent"] is plataforma \
                    and abs(plataforma.x + p["dx"] - self.x) < 70:
                p["estado"] = "carregado"
                self.textos.adicionar("PINTINHO!", (self.x, _y_faixa(f1) - 40), AMARELO, 14)
                self.som("ponto", 0.8)

        # Faixa nova nesta travessia
        if f1 > self.max_faixa:
            self.max_faixa = f1
            if f1 < 10:
                self.pontos += 10
                self.textos.adicionar("+10", (self.x + 34, _y_faixa(f1) - 20), BRANCO, 10)

        if f1 == 10:
            self._chegou_ninho()
            return

        if self.fila is not None:
            d, self.fila = self.fila, None
            self._pular(d)

    def _chegou_ninho(self):
        i = min(range(5), key=lambda k: abs(NINHOS_X[k] - self.x))
        self.ninhos[i] = True
        self.total_ninhos += 1
        bonus = 200 + int(self.restante) * 5
        self.pontos += bonus
        pos = (NINHOS_X[i], _y_faixa(10))
        self.textos.adicionar(f"+{bonus}", (pos[0], pos[1] + 36), AMARELO, 16)
        for _ in range(6):
            self.particulas.explodir(pos, [(235, 60, 90), (255, 150, 180)], 2, 160, 0.9, (4, 7),
                                     gravidade=-60)
        self.som("vencer" if all(self.ninhos) else "acerto", 0.8)
        if self.pintinho and self.pintinho["estado"] == "carregado":
            self.pontos += 300
            self.pintinhos += 1
            self.textos.adicionar("PINTINHO SALVO! +300", (LARGURA / 2, 200), AMARELO, 16)
            self.pintinho = None
            self.proximo_pintinho = random.uniform(10, 16)
        self.estado_ovo = "ninho"
        self.tempo_estado = 0.0

        if all(self.ninhos):
            self.pontos += 1000
            self.nivel += 1
            self.banner = f"NÍVEL {self.nivel}!  +1000"
            self.tempo_banner = 2.2
            self.particulas.explodir((LARGURA / 2, 200), [AMARELO, BRANCO, self.jogador.cor], 60, 400, 1.2)
            self.tremer(0.2)

    def _morrer(self, como):
        self.estado_ovo = como
        self.tempo_estado = 0.0
        self.x = self._x_atual()
        self.faixa = self._faixa_atual()
        self.pulo = None
        self.fila = None
        self.plataforma = None
        pos = (self.x, _y_faixa(self.faixa))
        if como == "frito":
            self.som("explosao", 0.5)
            self.tremer(0.25)
            self.textos.adicionar("OVO FRITO!", (pos[0], pos[1] - 44), AMARELO, 16)
            self.particulas.explodir(pos, [BRANCO, AMARELO, (255, 240, 200)], 20, 220, 0.6)
        elif como == "afogado":
            self.som("bater", 0.6)
            self.textos.adicionar("GLUB!", (pos[0], pos[1] - 44), (200, 240, 255), 16)
            self.particulas.explodir(pos, [(120, 200, 255), (220, 245, 255)], 24, 240, 0.7)
        else:
            self.som("erro", 0.7)
            self.banner = "ACABOU O TEMPO!"
            self.tempo_banner = 1.4
        if self.pintinho and self.pintinho["estado"] == "carregado":
            self.particulas.explodir(pos, [AMARELO, (255, 240, 150)], 12, 150, 0.6)
            self.textos.adicionar("PIU!", (pos[0] + 30, pos[1] - 20), AMARELO, 10)
            self.pintinho = None
            self.proximo_pintinho = random.uniform(8, 14)

    def _atualizar_morto(self, dt):
        self.tempo_estado += dt
        if self.estado_ovo == "ninho":
            if self.tempo_estado > 0.8:
                if all(self.ninhos):
                    self.ninhos = [False] * 5
                    fator = self._fator()
                    for f in self.faixas.values():
                        f.vel = f.vel_base * fator
                self._nascer()
            return
        if self.tempo_estado > 1.4:
            self.vidas -= 1
            if self.vidas <= 0:
                self.vidas = 0
                self.terminar(linhas=[f"PONTOS: {self.pontos}",
                                      f"NÍVEL: {self.nivel}   NINHOS: {self.total_ninhos}",
                                      f"PINTINHOS SALVOS: {self.pintinhos}"])
            else:
                self._nascer()

    def _atualizar_pintinho(self, dt, moveu):
        p = self.pintinho
        if p is None:
            self.proximo_pintinho -= dt
            if self.proximo_pintinho <= 0:
                faixa = random.choice((6, 9))
                ents = [e for e in self.faixas[faixa].ents if e.tipo == "tronco"]
                # Um tronco que esteja entrando na tela
                visiveis = [e for e in ents if -e.largura < e.x < LARGURA]
                e = random.choice(visiveis or ents)
                self.pintinho = {"estado": "tronco", "ent": e, "faixa": faixa,
                                 "dx": e.largura / 2, "tempo": 16.0}
            return
        if p["estado"] == "tronco":
            p["tempo"] -= dt
            e = p["ent"]
            x = e.x + p["dx"]
            if p["tempo"] <= 0 and (x < -20 or x > LARGURA + 20 or p["tempo"] < -6):
                self.pintinho = None
                self.proximo_pintinho = random.uniform(8, 14)

    # --------------------------------------------------------
    # DESENHO
    # --------------------------------------------------------

    def _ovo(self, tela, centro, sx=1.0, sy=1.0, angulo=0.0, altura=ALTURA_OVO, aparencia=None):
        img = self.jogador.avatar(altura, aparencia)
        lado = img.get_width()
        escala = lado / 100
        if self.espelhar and aparencia is None:
            img = pygame.transform.flip(img, True, False)
        if abs(sx - 1) > 0.01 or abs(sy - 1) > 0.01:
            img = pygame.transform.smoothscale(img, (max(1, round(lado * sx)), max(1, round(lado * sy))))
        if angulo:
            img = pygame.transform.rotate(img, angulo)
        ovo = self.jogador.OVO_RECT
        pe = centro[1] + altura / 2
        cy = pe - altura * sy / 2
        dx = (ovo.centerx - 50) * escala * sx
        dy = (ovo.centery - 50) * escala * sy
        tela.blit(img, img.get_rect(center=(round(centro[0] - dx), round(cy - dy))))

    def _familia(self, i):
        ap = self.jogador.aparencia()
        return ((ap[0] + 1 + i % 3) % 4, (i * 3 + 1) % 8, i % 3, (i + 1) % 6)

    def _desenhar_rio(self, tela):
        t = self.tempo
        for i in RIO:
            y = _y_faixa(i)
            d = CONFIG[i][1]
            for k in range(9):
                x = (k * 121 + t * 30 * d + i * 37) % (LARGURA + 60) - 30
                yy = y + ((k * 17 + i * 11) % 30) - 15
                pygame.draw.arc(tela, ONDA, (int(x), int(yy), 22, 10), 0.3, math.pi - 0.3, 2)

    def _desenhar_ents(self, tela, faixas):
        t = self.relogio
        for i in faixas:
            f = self.faixas[i]
            y = _y_faixa(i)
            for e in f.ents:
                if e.x > LARGURA or e.x + e.largura < 0:
                    continue
                if e.tipo == "carro":
                    s = _carro(e.extra)
                elif e.tipo == "onibus":
                    s = _onibus()
                elif e.tipo == "bici":
                    s = _bici(self.jogador, e.extra)
                elif e.tipo == "tronco":
                    s = _tronco(e.largura)
                    tela.blit(s, s.get_rect(midleft=(int(e.x), y + 2)))
                    continue
                elif e.tipo == "patos":
                    for k in range(3):
                        pato = _pato()
                        if f.direcao < 0:
                            pato = pygame.transform.flip(pato, True, False)
                        bal = math.sin(t * 4 + k) * 2
                        tela.blit(pato, pato.get_rect(midleft=(int(e.x + k * 50), int(y + bal))))
                    continue
                else:
                    c = _ciclo_vitoria(e, t)
                    limite = CICLO_VITORIA - AFUNDADA
                    for k in range(3):
                        cx = int(e.x + 28 + k * 56)
                        if c >= limite:
                            # Afundada: só as bolhas
                            fase = (t * 2 + k * 0.3) % 1
                            pygame.draw.circle(tela, (200, 235, 255), (cx, int(y + 6 - fase * 12)), 4, 1)
                            continue
                        s = _vitoria()
                        if c > limite - 0.6:
                            # Avisando que vai afundar: treme e escurece
                            s = s.copy()
                            s.set_alpha(150 + int(100 * math.sin(t * 20) ** 2))
                            cx += int(math.sin(t * 40 + k) * 2)
                        tela.blit(s, s.get_rect(center=(cx, y)))
                        if e.extra is None and k == 1:
                            _flor(tela, (cx - 6, y - 4))
                    continue
                if f.direcao < 0:
                    s = pygame.transform.flip(s, True, False)
                tela.blit(s, s.get_rect(midleft=(int(e.x), y + 2)))

    def _desenhar_ninhos(self, tela):
        y = _y_faixa(10) + 4
        for i, nx in enumerate(NINHOS_X):
            bal = math.sin(self.tempo * 3 + i) * 2
            if self.ninhos[i]:
                self._ovo(tela, (nx - 14, y - 4), altura=22, aparencia=self._familia(i))
                self._ovo(tela, (nx + 10, y - 8), altura=32, aparencia=self.jogador.aparencia())
                ui.coracao(tela, (nx + 28, int(y - 30 + bal)), 12)
            else:
                self._ovo(tela, (nx, y - 4 + bal), altura=22, aparencia=self._familia(i))

    def _desenhar_pintinho(self, tela, x, y):
        bal = math.sin(self.tempo * 10) * 2
        y = int(y + bal)
        x = int(x)
        pygame.draw.circle(tela, (200, 160, 20), (x, y), 11)
        pygame.draw.circle(tela, (255, 225, 60), (x, y), 10)
        pygame.draw.circle(tela, (255, 225, 60), (x + 6, y - 9), 7)
        pygame.draw.circle(tela, (20, 20, 20), (x + 8, y - 11), 2)
        pygame.draw.polygon(tela, (255, 140, 40), [(x + 12, y - 10), (x + 18, y - 8), (x + 12, y - 6)])
        asa = int(math.sin(self.tempo * 18) * 3)
        pygame.draw.ellipse(tela, (240, 200, 40), (x - 9, y - 4 + asa, 11, 7))

    def _desenhar_ovo(self, tela):
        x = self._x_atual()
        y = self._y_ovo()
        est = self.estado_ovo
        if est == "frito":
            self._ovo_frito(tela, (x, _y_faixa(self.faixa)))
            return
        if est == "afogado":
            bob = math.sin(self.tempo_estado * 6) * 3
            clip = tela.get_clip()
            yf = _y_faixa(self.faixa)
            tela.set_clip(pygame.Rect(0, 0, LARGURA, int(yf + 6)))
            self._ovo(tela, (x, yf + 4 + min(1.0, self.tempo_estado * 3) * 14 + bob),
                      angulo=math.sin(self.tempo_estado * 5) * 14)
            tela.set_clip(clip)
            if int(self.tempo_estado * 8) % 2 == 0:
                pygame.draw.circle(tela, (220, 245, 255), (int(x + 16), int(yf - 6 - (self.tempo_estado * 30) % 20)), 4, 1)
            return
        if est == "ninho":
            return
        ang = 0.0
        if est == "tempo":
            ang = math.sin(self.tempo_estado * 14) * 15
        sx = sy = 1.0
        if self.pulo is not None:
            s = min(1.0, self.pulo[4] / TEMPO_PULO)
            sx, sy = 1 - 0.1 * math.sin(s * math.pi), 1 + 0.14 * math.sin(s * math.pi)
        elif self.squash > 0:
            k = math.sin(self.squash / 0.12 * math.pi)
            sx, sy = 1 + 0.2 * k, 1 - 0.2 * k
        if self.bonk > 0:
            y += math.sin(self.bonk * 40) * 3
        # Sombra
        pygame.draw.ellipse(tela, (0, 0, 0), (int(x - 16), int(_y_faixa(self._faixa_atual()) + 16), 32, 8))
        self._ovo(tela, (x, y), sx, sy, ang)

    def _ovo_frito(self, tela, c):
        x, y = int(c[0]), int(c[1])
        for dx, dy, r in ((-14, 2, 14), (12, 4, 15), (0, -6, 16), (-4, 10, 13), (18, -6, 10), (-20, -6, 10)):
            pygame.draw.circle(tela, (200, 200, 205), (x + dx, y + dy + 1), r + 1)
        for dx, dy, r in ((-14, 2, 14), (12, 4, 15), (0, -6, 16), (-4, 10, 13), (18, -6, 10), (-20, -6, 10)):
            pygame.draw.circle(tela, (250, 250, 250), (x + dx, y + dy), r)
        esc = 1.0 + 0.05 * abs(math.sin(self.tempo_estado * 12))
        r = int(11 * esc)
        pygame.draw.circle(tela, (230, 150, 20), (x, y), r + 2)
        pygame.draw.circle(tela, (255, 200, 30), (x, y), r)
        pygame.draw.circle(tela, (255, 240, 160), (x - 4, y - 4), 3)
        # Estrelinhas de tontura
        for k in range(3):
            a = self.tempo_estado * 5 + k * math.tau / 3
            ui.estrela(tela, (x + math.cos(a) * 24, y - 26 + math.sin(a) * 6), 5, AMARELO)

    def desenhar_jogo(self, tela):
        tela.blit(self.fundo(self.jogador), (0, 0))
        self._desenhar_rio(tela)
        self._desenhar_ents(tela, RIO)
        self._desenhar_ninhos(tela)

        # Pintinho no tronco (anda junto)
        p = self.pintinho
        if p and p["estado"] == "tronco":
            px = p["ent"].x + p["dx"]
            if -20 < px < LARGURA + 20:
                self._desenhar_pintinho(tela, px, _y_faixa(p["faixa"]) - 8)
                if p["tempo"] > 0 and int(self.tempo * 3) % 2 == 0:
                    ui.desenhar_texto(tela, "PIU!", (int(px), _y_faixa(p["faixa"]) - 36), 10,
                                      AMARELO, "center")

        # Ovo frito fica embaixo dos carros
        if self.estado_ovo == "frito":
            self._desenhar_ovo(tela)
        self._desenhar_ents(tela, RUA)
        if self.estado_ovo != "frito":
            self._desenhar_ovo(tela)
            if p and p["estado"] == "carregado" and self.estado_ovo == "vivo":
                lado = 22 if self.espelhar else -22
                self._desenhar_pintinho(tela, self._x_atual() + lado, self._y_ovo() + 8)

        self.particulas.desenhar(tela)
        self.textos.desenhar(tela)

        if self.tempo_banner > 0:
            sup = ui.texto(self.banner, 24, AMARELO)
            caixa = sup.get_rect(center=(LARGURA // 2, _y_faixa(5))).inflate(40, 24)
            ui.painel(tela, caixa, (20, 24, 40), AMARELO, 12, 3, sombra=False)
            tela.blit(sup, sup.get_rect(center=caixa.center))

    def desenhar_hud(self, tela):
        # Faixa do HUD em cima
        pygame.draw.rect(tela, (28, 30, 44), (0, 0, LARGURA, Y_TOPO))

        caixa = pygame.Rect(12, 8, 300, 44)
        ui.painel(tela, caixa, (20, 24, 40), BRANCO, 12, 3, sombra=False)
        ui.desenhar_texto(tela, f"PONTOS: {self.pontos}", (caixa.x + 14, caixa.centery), 14,
                          AMARELO, "midleft")

        caixa = pygame.Rect(320, 8, 136, 44)
        ui.painel(tela, caixa, (20, 24, 40), BRANCO, 12, 3, sombra=False)
        for i in range(VIDAS):
            c = (caixa.x + 26 + i * 42, caixa.centery + 1)
            ui.coracao(tela, c, 26, (235, 60, 90) if i < self.vidas else (70, 70, 90))

        caixa = pygame.Rect(464, 8, 480, 44)
        ui.painel(tela, caixa, (20, 24, 40), BRANCO, 12, 3, sombra=False)
        ui.desenhar_texto(tela, f"NÍVEL {self.nivel}", (caixa.x + 14, caixa.centery), 12,
                          (180, 220, 255), "midleft")
        barra = pygame.Rect(caixa.x + 130, caixa.y + 14, caixa.w - 150, 16)
        pygame.draw.rect(tela, (50, 54, 80), barra, border_radius=8)
        frac = max(0.0, min(1.0, self.restante / TEMPO_TRAVESSIA))
        cor = VERDE if frac > 0.5 else AMARELO if frac > 0.25 else VERMELHO
        if frac > 0:
            pygame.draw.rect(tela, cor, (barra.x, barra.y, max(8, int(barra.w * frac)), barra.h),
                             border_radius=8)
        pygame.draw.rect(tela, BRANCO, barra, 2, border_radius=8)
        rec = self.recorde()
        if rec is not None and self.estado in ("contagem",):
            ui.desenhar_texto(tela, f"RECORDE: {rec}", (LARGURA // 2, _y_faixa(5)), 14, AMARELO, "center")
