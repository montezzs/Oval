import math
import random

import pygame

from settings import *
from core import ui
from jogos.base import MiniJogo

# ============================================================
# TOUPEIRAS NA HORTA
# ============================================================
# Toupeiras de óculos estão roubando a horta! O martelo é o seu
# ovo preso numa mola: dê BOINGs nas toupeiras que saem dos
# buracos. Cuidado: os ovinhos bebês da família também espiam
# dos buracos, e neles não pode bater!

COLUNAS_X = [272, 512, 752]
LINHAS_Y = [300, 460, 620]
BURACOS = [(x, y) for y in LINHAS_Y for x in COLUNAS_X]

TECLAS_BURACO = {
    pygame.K_q: 0, pygame.K_w: 1, pygame.K_e: 2,
    pygame.K_a: 3, pygame.K_s: 4, pygame.K_d: 5,
    pygame.K_z: 6, pygame.K_x: 7, pygame.K_c: 8,
    pygame.K_KP7: 0, pygame.K_KP8: 1, pygame.K_KP9: 2,
    pygame.K_KP4: 3, pygame.K_KP5: 4, pygame.K_KP6: 5,
    pygame.K_KP1: 6, pygame.K_KP2: 7, pygame.K_KP3: 8,
}
LETRAS = ["Q", "W", "E", "A", "S", "D", "Z", "X", "C"]
SETAS = {pygame.K_UP: (0, -1), pygame.K_DOWN: (0, 1), pygame.K_LEFT: (-1, 0), pygame.K_RIGHT: (1, 0)}

TEMPO_PARTIDA = 60.0
TEMPO_SUBIR = 0.12
TEMPO_DESCER = 0.14
TOLERANCIA = 0.06           # ainda dá para acertar a toupeira que acabou de sumir
TRAVA_BURACO = 0.1          # cada buraco aceita 1 batida a cada 0.1 s
TEMPO_TONTO = 1.0
HIT_STOP = 0.04
MAX_JUNTAS = 3

ALTURA_SPRITE = 120
LARG_SPRITE = 110
SUBIDA = 104                # quanto a toupeira sobe para fora do buraco

# Dificuldade: multiplicador do tempo visível e chance de bebê
TEMPO_VISIVEL = [1.4, 1.0, 0.75]
CHANCE_BEBE = [0.05, 0.10, 0.15]
META = [800, 1400, 2000]

PONTOS = {"toupeira": 10, "capacete": 25, "dourada": 50, "robert": 100}

TERRA = (120, 80, 45)
SULCO = (100, 65, 35)


def _multiplicador(combo):
    return min(5, 1 + combo // 5)


def _formatar_tempo(seg):
    seg = max(0, int(math.ceil(seg)))
    return f"{seg // 60}:{seg % 60:02d}"


# ============================================================
# DESENHOS (pré-renderizados)
# ============================================================

_sprites = {}


def _corpo_toupeira(sup, cor, barriga, tonta=False):
    """Toupeira de óculos redondos, focinho rosa e dentinhos."""
    cx = LARG_SPRITE // 2
    escura = ui.escurecer(cor, 40)
    # Orelhinhas
    pygame.draw.circle(sup, escura, (cx - 32, 30), 10)
    pygame.draw.circle(sup, escura, (cx + 32, 30), 10)
    pygame.draw.circle(sup, (255, 170, 180), (cx - 32, 30), 5)
    pygame.draw.circle(sup, (255, 170, 180), (cx + 32, 30), 5)
    # Corpo (a parte de baixo fica escondida no buraco)
    corpo = pygame.Rect(0, 0, 86, 150)
    corpo.midtop = (cx, 18)
    pygame.draw.ellipse(sup, escura, corpo.inflate(6, 6))
    pygame.draw.ellipse(sup, cor, corpo)
    pygame.draw.ellipse(sup, barriga, (cx - 26, 74, 52, 80))
    pygame.draw.ellipse(sup, ui.clarear(cor, 30), (cx - 26, 26, 22, 12))
    # Óculos
    for dx in (-17, 17):
        pygame.draw.circle(sup, (250, 250, 250), (cx + dx, 50), 12)
        if tonta:
            for s in (-1, 1):
                pygame.draw.line(sup, (30, 20, 20), (cx + dx - 6, 44), (cx + dx + 6, 56), 3)
                pygame.draw.line(sup, (30, 20, 20), (cx + dx + 6, 44), (cx + dx - 6, 56), 3)
                break
        else:
            pygame.draw.circle(sup, (30, 20, 20), (cx + dx + 2, 52), 5)
            pygame.draw.circle(sup, BRANCO, (cx + dx + 3, 50), 2)
        pygame.draw.circle(sup, (30, 30, 40), (cx + dx, 50), 13, 3)
    pygame.draw.line(sup, (30, 30, 40), (cx - 5, 48), (cx + 5, 48), 3)
    # Focinho rosa e dentinhos
    pygame.draw.ellipse(sup, (255, 150, 170), (cx - 13, 62, 26, 17))
    pygame.draw.ellipse(sup, (200, 90, 110), (cx - 5, 63, 10, 6))
    if tonta:
        pygame.draw.ellipse(sup, (60, 20, 30), (cx - 8, 80, 16, 12))
    else:
        pygame.draw.rect(sup, BRANCO, (cx - 6, 78, 5, 8), border_radius=1)
        pygame.draw.rect(sup, BRANCO, (cx + 1, 78, 5, 8), border_radius=1)
        pygame.draw.rect(sup, (170, 150, 150), (cx - 6, 78, 12, 8), 1)
    # Patinhas segurando a beira do buraco
    for dx in (-34, 34):
        pygame.draw.ellipse(sup, escura, (cx + dx - 13, 100, 26, 16))
        pygame.draw.ellipse(sup, ui.clarear(cor, 20), (cx + dx - 11, 101, 22, 12))


def _sprite(tipo):
    """toupeira / tonta / capacete / dourada / dourada_tonta."""
    if tipo in _sprites:
        return _sprites[tipo]
    sup = pygame.Surface((LARG_SPRITE, ALTURA_SPRITE), pygame.SRCALPHA)
    cx = LARG_SPRITE // 2
    if tipo.startswith("dourada"):
        _corpo_toupeira(sup, (240, 190, 40), (255, 230, 130), tipo.endswith("tonta"))
        for x, y in ((cx - 30, 40), (cx + 28, 90)):
            ui.estrela(sup, (x, y), 5, (255, 255, 220))
    else:
        _corpo_toupeira(sup, (130, 95, 80), (170, 135, 115), tipo == "tonta")
    if tipo == "capacete":
        # Capacete de obra amarelo com lanterninha
        pygame.draw.ellipse(sup, (160, 120, 20), (cx - 50, 30, 100, 16))
        casco = pygame.Rect(cx - 42, 4, 84, 56)
        pygame.draw.ellipse(sup, (200, 160, 20), casco.move(0, 2))
        pygame.draw.ellipse(sup, (250, 205, 40), casco)
        pygame.draw.rect(sup, (0, 0, 0, 0), (cx - 50, 36, 100, 30))
        pygame.draw.ellipse(sup, (230, 185, 30), (cx - 50, 30, 100, 12))
        pygame.draw.line(sup, (255, 240, 150), (cx - 24, 12), (cx - 8, 7), 3)
        pygame.draw.rect(sup, (200, 160, 20), (cx - 5, 5, 10, 30))
        pygame.draw.circle(sup, (255, 255, 200), (cx, 20), 6)
        pygame.draw.circle(sup, (180, 150, 60), (cx, 20), 6, 2)
    _sprites[tipo] = sup
    return sup


def _bebe(jogador, aparencia):
    """Ovinho bebê da família (com chupeta) para espiar do buraco."""
    chave = ("bebe", aparencia)
    if chave in _sprites:
        return _sprites[chave]
    sup = pygame.Surface((LARG_SPRITE, ALTURA_SPRITE), pygame.SRCALPHA)
    cx = LARG_SPRITE // 2
    corpo = jogador.desenhar(sup, (cx, 78), 70, aparencia=aparencia)
    # Chupeta
    boca = (cx, corpo.top + int(corpo.h * 0.72))
    pygame.draw.ellipse(sup, (120, 190, 255), (boca[0] - 12, boca[1] - 5, 24, 10))
    pygame.draw.ellipse(sup, (60, 120, 200), (boca[0] - 12, boca[1] - 5, 24, 10), 2)
    pygame.draw.circle(sup, (255, 150, 190), (boca[0], boca[1] + 7), 6, 3)
    # Lacinho
    lx, ly = cx + 20, corpo.top + 6
    pygame.draw.polygon(sup, (255, 110, 170), [(lx, ly), (lx - 11, ly - 7), (lx - 11, ly + 7)])
    pygame.draw.polygon(sup, (255, 110, 170), [(lx, ly), (lx + 11, ly - 7), (lx + 11, ly + 7)])
    pygame.draw.circle(sup, (220, 60, 130), (lx, ly), 4)
    _sprites[chave] = sup
    return sup


def _cabeca_robert():
    if "robert" in _sprites:
        return _sprites["robert"]
    sup = pygame.Surface((LARG_SPRITE, ALTURA_SPRITE), pygame.SRCALPHA)
    cx = LARG_SPRITE // 2
    # Corpo de palito
    pygame.draw.line(sup, (20, 20, 20), (cx, 80), (cx, 130), 4)
    # Cabeção branco
    pygame.draw.circle(sup, (20, 20, 20), (cx, 46), 36)
    pygame.draw.circle(sup, BRANCO, (cx, 46), 33)
    pygame.draw.circle(sup, (20, 20, 20), (cx - 11, 40), 3)
    pygame.draw.circle(sup, (20, 20, 20), (cx + 11, 40), 3)
    pygame.draw.arc(sup, (20, 20, 20), (cx - 18, 36, 36, 26), math.pi * 1.1, math.pi * 1.9, 3)
    pygame.draw.line(sup, (20, 20, 20), (cx - 22, 52), (cx - 19, 58), 2)
    pygame.draw.line(sup, (20, 20, 20), (cx + 22, 52), (cx + 19, 58), 2)
    _sprites["robert"] = sup
    return sup


def _bone(tela, pos, ang):
    """Boné arco-íris do ROBERT."""
    x, y = pos
    sup = pygame.Surface((56, 36), pygame.SRCALPHA)
    cores = [(255, 70, 90), (255, 160, 50), (250, 220, 60), (80, 200, 90)]
    copa = pygame.Rect(6, 4, 40, 34)
    pygame.draw.ellipse(sup, (20, 20, 20), copa.inflate(4, 4))
    for i, c in enumerate(cores):
        faixa = pygame.Rect(copa.x + i * 10, copa.y, 10, copa.h)
        sub = pygame.Surface(copa.size, pygame.SRCALPHA)
        pygame.draw.ellipse(sub, c, sub.get_rect())
        sup.blit(sub, (faixa.x, copa.y), area=pygame.Rect(faixa.x - copa.x, 0, 10, copa.h))
    pygame.draw.rect(sup, (0, 0, 0, 0), (0, 22, 56, 14))
    pygame.draw.ellipse(sup, (255, 90, 150), (26, 16, 30, 10))
    pygame.draw.line(sup, (20, 20, 20), (4, 22), (48, 22), 2)
    img = pygame.transform.rotate(sup, ang)
    tela.blit(img, img.get_rect(center=(int(x), int(y))))


_labio = None


def _labio_buraco():
    """Beirada da frente do buraco (fica por cima da toupeira)."""
    global _labio
    if _labio is not None:
        return _labio
    sup = pygame.Surface((150, 70), pygame.SRCALPHA)
    pygame.draw.ellipse(sup, (150, 100, 60), (7, 13, 136, 56))
    pygame.draw.ellipse(sup, (0, 0, 0, 0), (15, 11, 120, 44))
    pygame.draw.arc(sup, (175, 125, 80), (9, 15, 132, 52), math.pi * 1.15, math.pi * 1.85, 3)
    rnd = random.Random(3)
    for _ in range(9):
        a = rnd.uniform(math.pi * 0.15, math.pi * 0.85)
        px = 75 + math.cos(a) * 64
        py = 41 + math.sin(a) * 25
        pygame.draw.circle(sup, (165, 115, 70), (int(px), int(py)), rnd.randint(4, 7))
    _labio = sup
    return sup


def _poeira():
    return [(170, 130, 90), (140, 100, 60), (200, 170, 130)]


class Toupeira:
    """Um bicho (ou bebê) saindo de um buraco."""

    def __init__(self, buraco, tipo, visivel, aparencia=None):
        self.buraco = buraco
        self.tipo = tipo            # toupeira capacete dourada bebe robert
        self.visivel = visivel      # tempo parado lá fora
        self.aparencia = aparencia
        self.estado = "subindo"     # subindo fora descendo acertada escondida
        self.t = 0.0
        self.vidas = 2 if tipo == "capacete" else 1
        self.subida = 0.0           # 0 = escondida, 1 = toda para fora

    @property
    def acertavel(self):
        if self.estado in ("fora", "escondida"):
            return True
        return self.estado in ("subindo", "descendo") and self.subida > 0.3


class Toupeiras(MiniJogo):

    ID = "toupeiras"
    TITULO = "TOUPEIRAS NA HORTA"
    TITULO_CURTO = "TOUPEIRAS"
    DESCRICAO = "Toupeiras de óculos roubam a horta! Dê BOINGs nelas, mas não acerte os ovinhos bebês."
    COR = (110, 170, 60)
    INSTRUCOES = [
        "Bata nas toupeiras com o seu ovo-martelo!",
        "CAPACETE: 2 batidas. DOURADA: +50 e +3s.",
        "NÃO bata nos ovinhos bebês da família!",
        "Acertos seguidos multiplicam os pontos.",
        "MOUSE, Q W E/A S D/Z X C ou SETAS+ESPAÇO",
    ]
    OPCOES = ["FÁCIL", "NORMAL", "DIFÍCIL"]
    ROTULO_PONTOS = "PONTOS"
    CONTAGEM = True

    MOEDAS_POR = 125            # os pontos passam de 1000 fácil (combo x5)
    MOEDAS_MAX = 16

    # --------------------------------------------------------
    # CENÁRIO: horta com cerca e sol de óculos
    # --------------------------------------------------------

    @classmethod
    def criar_fundo(cls, jogador):
        sup = pygame.Surface((LARGURA, ALTURA))
        rnd = random.Random(12)

        # Céu com nuvens
        sup.blit(ui.gradiente(LARGURA, 150, (110, 196, 255), (150, 220, 255)), (0, 0))
        for x, y, e in ((120, 96, 1.0), (380, 70, 0.8), (640, 108, 0.9)):
            for dx, dy, r in ((0, 0, 20), (22, -8, 24), (46, 0, 20), (22, 6, 18)):
                pygame.draw.circle(sup, BRANCO, (int(x + dx * e), int(y + dy * e)), int(r * e))

        # Sol de óculos (cortado pelo canto)
        sol = (930, 58)
        for r in range(128, 90, -6):
            pygame.draw.circle(sup, ui.misturar((150, 220, 255), (255, 240, 150), (128 - r) / 40),
                               sol, r)
        pygame.draw.circle(sup, (255, 230, 40), sol, 90)
        pygame.draw.circle(sup, (255, 245, 120), (sol[0] - 26, sol[1] - 20), 34)
        pygame.draw.circle(sup, (255, 230, 40), sol, 70)
        for dx in (-30, 26):
            lente = pygame.Rect(0, 0, 48, 30)
            lente.center = (sol[0] + dx, sol[1] + 22)
            pygame.draw.rect(sup, (25, 25, 35), lente, border_radius=10)
            pygame.draw.line(sup, (90, 90, 110), (lente.x + 8, lente.y + 7), (lente.x + 18, lente.y + 7), 3)
        pygame.draw.line(sup, (25, 25, 35), (sol[0] - 6, sol[1] + 16), (sol[0] + 2, sol[1] + 16), 4)
        pygame.draw.arc(sup, (200, 90, 40), (sol[0] - 24, sol[1] + 30, 40, 22), math.pi * 1.1,
                        math.pi * 1.9, 3)

        # Terra com sulcos
        pygame.draw.rect(sup, TERRA, (0, 150, LARGURA, ALTURA - 150))
        for y in range(214, ALTURA, 34):
            pygame.draw.line(sup, SULCO, (0, y), (LARGURA, y), 6)
            pygame.draw.line(sup, (135, 92, 55), (0, y + 5), (LARGURA, y + 5), 2)
        for _ in range(260):
            x, y = rnd.randrange(LARGURA), rnd.randrange(200, ALTURA)
            pygame.draw.circle(sup, rnd.choice([(110, 72, 40), (132, 90, 52)]), (x, y), rnd.randint(1, 3))

        # Cerca branca de estacas pontudas
        pygame.draw.rect(sup, (200, 190, 160), (0, 164, LARGURA, 8))
        pygame.draw.rect(sup, (200, 190, 160), (0, 186, LARGURA, 8))
        for x in range(4, LARGURA, 30):
            estaca = [(x, 200), (x, 160), (x + 11, 148), (x + 22, 160), (x + 22, 200)]
            pygame.draw.polygon(sup, (230, 220, 190), estaca)
            pygame.draw.polygon(sup, (170, 160, 130), estaca, 2)
        pygame.draw.rect(sup, (100, 70, 40), (0, 200, LARGURA, 6))

        # Horta: alfaces e cenouras entre os buracos
        def livre(x, y, folga):
            # Nada de plantas onde as toupeiras aparecem (acima do buraco)
            return all(abs(x - bx) > 80 + folga or not (by - 125 - folga < y < by + 40 + folga)
                       for bx, by in BURACOS)

        plantas = 0
        tentativas = 0
        while plantas < 26 and tentativas < 2000:
            tentativas += 1
            x = rnd.randrange(30, LARGURA - 30)
            y = rnd.randrange(236, ALTURA - 20)
            if not livre(x, y, 12):
                continue
            plantas += 1
            if rnd.random() < 0.55:
                # Alface
                pygame.draw.ellipse(sup, (70, 50, 30), (x - 20, y + 8, 40, 10))
                for dx, dy, r in ((-10, 0, 12), (10, 0, 12), (0, -6, 13), (0, 4, 12)):
                    pygame.draw.circle(sup, (60, 150, 50), (x + dx, y + dy), r)
                for dx, dy, r in ((-5, -2, 8), (6, -1, 8), (0, 2, 7)):
                    pygame.draw.circle(sup, (90, 190, 70), (x + dx, y + dy), r)
                pygame.draw.circle(sup, (150, 220, 120), (x - 2, y - 4), 3)
            else:
                # Cenoura (só o topo aparecendo)
                pygame.draw.polygon(sup, (240, 130, 30), [(x - 8, y), (x + 8, y), (x, y + 18)])
                pygame.draw.polygon(sup, (200, 100, 20), [(x - 8, y), (x + 8, y), (x, y + 18)], 1)
                for dx in (-6, 0, 6):
                    pygame.draw.polygon(sup, (70, 170, 60), [(x + dx - 3, y), (x + dx + 3, y),
                                                             (x + dx * 2, y - 16)])

        # Buracos
        for i, (x, y) in enumerate(BURACOS):
            pygame.draw.ellipse(sup, (90, 58, 32), (x - 70, y - 22, 140, 60))
            pygame.draw.ellipse(sup, (150, 100, 60), (x - 68, y - 28, 136, 56))
            pygame.draw.ellipse(sup, (50, 30, 20), (x - 60, y - 22, 120, 44))
            pygame.draw.ellipse(sup, (30, 18, 12), (x - 50, y - 16, 100, 30))
            ui.desenhar_texto(sup, LETRAS[i], (x - 74, y + 30), 10, (240, 220, 180), "center")
        return sup

    @classmethod
    def desenhar_icone(cls, sup, jogador):
        w, h = sup.get_size()
        for i, x in enumerate((w // 2 - 58, w // 2 + 2, w // 2 + 62)):
            y = h // 2 + 30
            pygame.draw.ellipse(sup, (150, 100, 60), (x - 26, y - 9, 52, 20))
            pygame.draw.ellipse(sup, (50, 30, 20), (x - 22, y - 7, 44, 14))
            if i != 2:
                img = pygame.transform.smoothscale(_sprite("dourada" if i == 1 else "toupeira"), (44, 48))
                sup.blit(img, (x - 22, y - 44), area=pygame.Rect(0, 0, 44, 44))
        jogador.desenhar(sup, (w // 2 + 68, h // 2 - 16), 36, angulo=25)
        pygame.draw.line(sup, (120, 80, 40), (w // 2 + 84, h // 2 - 2), (w // 2 + 100, h // 2 + 22), 5)

    # --------------------------------------------------------
    # PARTIDA
    # --------------------------------------------------------

    def reiniciar(self):
        self.toupeiras = []
        self.tempo_restante = TEMPO_PARTIDA
        self.decorrido = 0.0
        self.proximo = 0.6
        self.combo = 0
        self.maior_combo = 0
        self.acertos = 0
        self.erros = 0
        self.bebes_acertados = 0
        self.tonto = 0.0
        self.hitstop = 0.0
        self.golpe = 1.0                        # 0..1 animação do martelo
        self.trava = [-1.0] * 9                 # último golpe em cada buraco
        self.cursor = 4
        self.teclado = False
        self.mira = (BURACOS[4][0], BURACOS[4][1] - 20)
        self.acabou = False
        self.t_fim = 0.0
        self.tique = 0
        self.estrelas = []                      # estrelinhas de quem levou BOING
        self.lagrimas = []

        # Bebês da família (diferentes do jogador)
        minha = self.jogador.aparencia()
        self.familia = []
        while len(self.familia) < 3:
            ap = (random.randrange(4), random.randrange(6), random.randrange(3), random.randrange(6))
            if ap[:3] != minha[:3] and ap not in self.familia:
                self.familia.append(ap)

        # Prévia: algumas toupeiras já de fora
        if self.estado == "inicio":
            for b, tipo in ((0, "toupeira"), (4, "capacete"), (8, "dourada")):
                m = Toupeira(b, tipo, 99)
                m.estado, m.subida = "fora", 1.0
                self.toupeiras.append(m)

    def comecar(self):
        super().comecar()
        self.toupeiras = []         # tira as toupeiras da prévia

    # --------------------------------------------------------
    # CONTROLES
    # --------------------------------------------------------

    def evento_jogo(self, e):
        if e.type == pygame.MOUSEMOTION:
            if not self.botao_pausa.collidepoint(e.pos):
                self.mira = e.pos
                self.teclado = False
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.mira = e.pos
            self.teclado = False
            self._bater(self._buraco_em(e.pos))
        elif e.type == pygame.KEYDOWN:
            if e.key in TECLAS_BURACO or e.key in SETAS:
                self.teclado = True
            if e.key in TECLAS_BURACO:
                b = TECLAS_BURACO[e.key]
                self.cursor = b
                self.mira = (BURACOS[b][0], BURACOS[b][1] - 20)
                self._bater(b)
            elif e.key in SETAS:
                dx, dy = SETAS[e.key]
                col = max(0, min(2, self.cursor % 3 + dx))
                lin = max(0, min(2, self.cursor // 3 + dy))
                self.cursor = lin * 3 + col
                self.mira = (BURACOS[self.cursor][0], BURACOS[self.cursor][1] - 20)
            elif e.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_KP0):
                self.mira = (BURACOS[self.cursor][0], BURACOS[self.cursor][1] - 20)
                self._bater(self.cursor)

    def _buraco_em(self, pos):
        x, y = pos
        for i, (bx, by) in enumerate(BURACOS):
            if abs(x - bx) < 78 and by - 125 < y < by + 36:
                return i
        return None

    def _bater(self, buraco):
        if self.acabou:
            return
        if self.tonto > 0:
            self.som("erro", 0.3)
            return
        self.golpe = 0.0
        self.som("boing", 0.7)
        if buraco is None:
            return
        if self.decorrido - self.trava[buraco] < TRAVA_BURACO:
            return
        self.trava[buraco] = self.decorrido

        alvo = None
        for m in self.toupeiras:
            if m.buraco == buraco and m.acertavel:
                alvo = m
                break
        bx, by = BURACOS[buraco]
        if alvo is None:
            # Buraco vazio: só levanta poeira e zera o combo
            self.erros += 1
            if self.combo >= 3:
                self.textos.adicionar("COMBO PERDIDO", (bx, by - 60), (220, 210, 255), 12)
            self.combo = 0
            self.particulas.explodir((bx, by), _poeira(), 14, 160, 0.5, (4, 9), gravidade=-40)
            self.som("virar", 0.6)
            return
        self._acertar(alvo)

    def _acertar(self, m):
        bx, by = BURACOS[m.buraco]
        topo = (bx, by - SUBIDA * max(0.4, m.subida) + 10)
        self.hitstop = HIT_STOP

        if m.tipo == "bebe":
            self.pontos = max(0, self.pontos - 20)
            self.combo = 0
            self.bebes_acertados += 1
            self.tonto = TEMPO_TONTO
            self.textos.adicionar("AI! -20", (bx, topo[1] - 20), (255, 120, 140), 18)
            self.lagrimas.append([bx + 14, topo[1] + 40, 0.0, 0.8])
            self.lagrimas.append([bx - 14, topo[1] + 44, -30.0, 0.7])
            self.som("erro")
            self.tremer(0.2)
            m.estado, m.t = "acertada", 0.0
            return

        if m.tipo == "capacete" and m.vidas > 1:
            # Primeira batida: o capacete voa longe
            m.vidas -= 1
            m.tipo = "toupeira_sem_capacete"
            m.estado, m.t = "fora", 0.0
            m.visivel = max(m.visivel, 0.6)
            self.particulas.explodir((bx, topo[1] - 10), [(250, 205, 40), (200, 160, 20), BRANCO],
                                     14, 260, 0.6, (4, 8))
            self.textos.adicionar("PLÉC!", (bx + 30, topo[1] - 20), (255, 230, 120), 14)
            self.som("bater")
            self.tremer(0.08)
            return

        tipo = "capacete" if m.tipo == "toupeira_sem_capacete" else m.tipo
        self.combo += 1
        self.acertos += 1
        self.maior_combo = max(self.maior_combo, self.combo)
        mult = _multiplicador(self.combo)
        ganho = PONTOS[tipo] * mult
        self.pontos += ganho
        texto = f"+{PONTOS[tipo]}" + (f" ×{mult}" if mult > 1 else "")
        cor = AMARELO if tipo in ("dourada", "robert") or mult > 1 else BRANCO
        self.textos.adicionar(texto, (bx, topo[1] - 24), cor, 16 if mult > 1 else 14)
        m.estado, m.t = "acertada", 0.0
        self.estrelas.append([m, 0.0])
        self.tremer(0.1)

        if tipo == "dourada":
            self.tempo_restante += 3.0
            self.textos.adicionar("+3s", (bx, topo[1] - 50), (140, 230, 255), 16)
            self.particulas.explodir(topo, [AMARELO, (255, 250, 200), BRANCO], 26, 280, 0.8)
            self.som("moeda")
        elif tipo == "robert":
            self.textos.adicionar("VALEU, OVO!", (bx, topo[1] - 50), (255, 160, 220), 14)
            self.particulas.explodir(topo, [(255, 70, 90), (255, 160, 50), (250, 220, 60),
                                            (80, 200, 90), (80, 160, 255)], 36, 300, 0.9)
            self.som("acerto")
        else:
            self.particulas.explodir(topo, [AMARELO, BRANCO, (200, 160, 130)], 12, 200, 0.5)
            self.som("bater", 0.9)

        if self.combo in (5, 10, 15, 20):
            self.textos.adicionar(f"COMBO ×{mult}!", (LARGURA // 2, 230), LARANJA, 22)

    # --------------------------------------------------------
    # LÓGICA
    # --------------------------------------------------------

    def atualizar_jogo(self, dt):
        self.golpe = min(1.0, self.golpe + dt / 0.28)
        self.tonto = max(0.0, self.tonto - dt)
        if self.hitstop > 0:
            self.hitstop -= dt
            return

        self.decorrido += dt
        if not self.acabou:
            antes = self.tempo_restante
            self.tempo_restante = max(0.0, self.tempo_restante - dt)
            if self.tempo_restante <= 5 and int(antes) != int(self.tempo_restante):
                self.som("clique", 0.8)
            if self.tempo_restante <= 0:
                self.acabou = True
                self.t_fim = 0.0
                for m in self.toupeiras:
                    if m.estado in ("subindo", "fora"):
                        m.estado, m.t = "descendo", 0.0
                self.textos.adicionar("TEMPO!", (LARGURA // 2, 240), AMARELO, 28)
                self.som("bandeira")
            else:
                self._surgir(dt)
        else:
            self.t_fim += dt
            if self.t_fim > 1.3:
                self._fim()
                return

        self._mover_toupeiras(dt)

        for e in self.estrelas:
            e[1] += dt
        self.estrelas = [e for e in self.estrelas if e[1] < 0.7 and e[0] in self.toupeiras]
        for l in self.lagrimas:
            l[2] += dt * 160
            l[1] += l[2] * dt
            l[3] -= dt
        self.lagrimas = [l for l in self.lagrimas if l[3] > 0]

    def _progresso(self):
        return min(1.0, self.decorrido / TEMPO_PARTIDA)

    def _surgir(self, dt):
        self.proximo -= dt
        if self.proximo > 0:
            return
        p = self._progresso()
        self.proximo = (0.8 - 0.45 * p) * random.uniform(0.8, 1.2)

        ativas = [m for m in self.toupeiras if m.estado != "escondida"]
        if len(ativas) >= MAX_JUNTAS:
            self.proximo = 0.1
            return
        ocupados = {m.buraco for m in self.toupeiras}
        livres = [b for b in range(9) if b not in ocupados and self.decorrido - self.trava[b] > 0.2]
        if not livres:
            self.proximo = 0.1
            return
        buraco = random.choice(livres)

        mult = TEMPO_VISIVEL[self.opcao]
        base = 0.9 - 0.45 * p
        r = random.random()
        chance_bebe = CHANCE_BEBE[self.opcao]
        if r < 0.012 and self.decorrido > 10:
            m = Toupeira(buraco, "robert", 1.3 * mult)
        elif r < 0.012 + chance_bebe:
            m = Toupeira(buraco, "bebe", 1.2 * mult, random.choice(self.familia))
        elif r < 0.072 + chance_bebe:
            m = Toupeira(buraco, "dourada", 0.5 * mult)
        elif r < 0.22 + chance_bebe and self.decorrido > 6:
            m = Toupeira(buraco, "capacete", (base + 0.45) * mult)
        else:
            m = Toupeira(buraco, "toupeira", base * mult)
        self.toupeiras.append(m)
        if m.tipo == "robert":
            self.som("ponto", 0.8)

    def _mover_toupeiras(self, dt):
        vivas = []
        for m in self.toupeiras:
            m.t += dt
            if m.estado == "subindo":
                m.subida = min(1.0, m.t / TEMPO_SUBIR)
                if m.t >= TEMPO_SUBIR:
                    m.estado, m.t = "fora", 0.0
            elif m.estado == "fora":
                m.subida = 1.0
                if m.t >= m.visivel:
                    m.estado, m.t = "descendo", 0.0
            elif m.estado == "acertada":
                if m.t >= 0.45:
                    m.estado, m.t = "descendo", 0.0
                    m.acertada = True
            elif m.estado == "descendo":
                m.subida = max(0.0, 1 - m.t / TEMPO_DESCER)
                if m.t >= TEMPO_DESCER:
                    if getattr(m, "acertada", False) or m.tipo == "bebe" or self.acabou:
                        continue
                    m.estado, m.t = "escondida", 0.0
            elif m.estado == "escondida":
                m.subida = 0.0
                if m.t >= TOLERANCIA:
                    continue
            vivas.append(m)
        self.toupeiras = vivas

    def _fim(self):
        meta = META[self.opcao]
        venceu = self.pontos >= meta
        linhas = [f"PONTOS: {self.pontos}  (META {meta})",
                  f"ACERTOS: {self.acertos}   MAIOR COMBO: {self.maior_combo}"]
        if self.bebes_acertados:
            linhas.append(f"BEBÊS ASSUSTADOS: {self.bebes_acertados}")
        self.terminar(venceu=venceu, titulo="HORTA SALVA!" if venceu else "TEMPO ESGOTADO!",
                      linhas=linhas)

    # --------------------------------------------------------
    # DESENHO
    # --------------------------------------------------------

    def desenhar_jogo(self, tela):
        tela.blit(self.fundo(self.jogador), (0, 0))
        labio = _labio_buraco()

        # Linha por linha (de trás para frente): bichos, beirada, efeitos
        for linha in range(3):
            for m in self.toupeiras:
                if m.buraco // 3 == linha and m.subida > 0:
                    self._desenhar_bicho(tela, m)
            for b in range(linha * 3, linha * 3 + 3):
                bx, by = BURACOS[b]
                tela.blit(labio, (bx - 75, by - 41))

        # Cursor do teclado
        if self.estado == "jogando" and not self.acabou and self.teclado:
            bx, by = BURACOS[self.cursor]
            pulso = int(3 * math.sin(self.tempo * 8))
            r = pygame.Rect(0, 0, 150 + pulso, 64 + pulso)
            r.center = (bx, by + 4)
            pygame.draw.ellipse(tela, (255, 240, 150), r, 3)

        for x, y, _, vida in self.lagrimas:
            pygame.draw.circle(tela, (120, 190, 255), (int(x), int(y)), 5)
            pygame.draw.polygon(tela, (120, 190, 255), [(x - 4, y - 2), (x + 4, y - 2), (x, y - 10)])

        self._desenhar_martelo(tela)
        self.particulas.desenhar(tela)
        self.textos.desenhar(tela)

    def _desenhar_bicho(self, tela, m):
        bx, by = BURACOS[m.buraco]
        topo = by - 113 + (1 - m.subida) * 125
        x = bx - LARG_SPRITE // 2
        clip_antes = tela.get_clip()
        tela.set_clip(pygame.Rect(bx - 80, 0, 160, by + 8).clip(clip_antes))

        tonta = m.estado == "acertada" or (m.estado == "descendo" and getattr(m, "acertada", False))
        if m.tipo == "bebe":
            balanco = math.sin(self.tempo * (30 if tonta else 6)) * (8 if tonta else 4)
            img = _bebe(self.jogador, m.aparencia)
            if balanco:
                img = pygame.transform.rotate(img, balanco)
            tela.blit(img, img.get_rect(center=(bx, topo + ALTURA_SPRITE // 2)))
        elif m.tipo == "robert":
            tela.blit(_cabeca_robert(), (x, topo + 6))
            # Braço acenando com o boné
            ang = math.sin(self.tempo * 10) * 0.5
            ombro = (bx, topo + 96)
            mao = (bx + 36 + math.cos(ang) * 10, topo + 40 + math.sin(ang) * 16)
            pygame.draw.line(tela, (20, 20, 20), ombro, mao, 4)
            _bone(tela, (mao[0] + 6, mao[1] - 12), math.degrees(ang) * 0.8)
        else:
            if m.tipo == "dourada":
                nome = "dourada_tonta" if tonta else "dourada"
            elif m.tipo == "capacete":
                nome = "capacete"
            else:
                nome = "tonta" if tonta else "toupeira"
            img = _sprite(nome)
            if m.estado == "acertada" and m.t < 0.12:
                # Achatada pela batida
                k = 1 - m.t / 0.12
                w = int(LARG_SPRITE * (1 + 0.25 * k))
                h = int(ALTURA_SPRITE * (1 - 0.25 * k))
                img = pygame.transform.scale(img, (w, h))
                tela.blit(img, (bx - w // 2, topo + ALTURA_SPRITE - h))
            else:
                tela.blit(img, (x, topo))
            if m.tipo == "dourada" and not tonta and int(self.tempo * 8) % 2 == 0:
                ui.estrela(tela, (bx + 36, topo + 20), 6, BRANCO, self.tempo * 3)
        tela.set_clip(clip_antes)

        # Estrelinhas girando em cima de quem levou BOING
        if tonta and m.subida > 0.3 and m.tipo != "bebe":
            for k in range(3):
                a = self.tempo * 6 + k * math.tau / 3
                ui.estrela(tela, (bx + math.cos(a) * 30, topo + 10 + math.sin(a) * 8), 7, AMARELO, a)

    def _desenhar_martelo(self, tela):
        if self.estado not in ("jogando", "pausado", "contagem"):
            return
        mx, my = self.mira
        # Batida: desce rápido e volta com mola (squash & stretch)
        g = self.golpe
        if g < 0.25:
            desce = g / 0.25
        else:
            k = (g - 0.25) / 0.75
            desce = math.cos(k * math.pi * 2.5) * (1 - k) * 0.6 if k < 1 else 0.0
            desce = max(-0.3, desce)
        impacto = max(0.0, 1 - abs(g - 0.25) / 0.12) if g < 0.37 else 0.0

        cx = mx
        cy = my - 62 + desce * 48
        angulo = 22 - 22 * max(0.0, desce)
        if self.tonto > 0:
            angulo += math.sin(self.tempo * 18) * 14
            cx += math.sin(self.tempo * 11) * 6

        # Sombra/mira no chão
        pygame.draw.ellipse(tela, (70, 45, 25), (mx - 28, my + 6, 56, 16))
        pygame.draw.ellipse(tela, (255, 240, 150), (mx - 28, my + 6, 56, 16), 2)

        # Haste com mola
        haste_a = (cx + 150, cy - 170)
        haste_b = (cx + 58, cy - 78)
        pygame.draw.line(tela, (70, 40, 20), (haste_a[0] + 3, haste_a[1] + 4),
                         (haste_b[0] + 3, haste_b[1] + 4), 16)
        pygame.draw.line(tela, (200, 60, 60), haste_a, haste_b, 14)
        pygame.draw.line(tela, (255, 130, 120), (haste_a[0] - 4, haste_a[1] - 1),
                         (haste_b[0] - 4, haste_b[1] - 1), 3)
        pygame.draw.circle(tela, (230, 190, 60), (int(haste_b[0]), int(haste_b[1])), 9)
        topo_ovo = (cx + 18, cy - 40)
        voltas = 5
        pontos = []
        for i in range(voltas * 2 + 1):
            t = i / (voltas * 2)
            px = haste_b[0] + (topo_ovo[0] - haste_b[0]) * t
            py = haste_b[1] + (topo_ovo[1] - haste_b[1]) * t
            lado = (11 if i % 2 else -11) if 0 < i < voltas * 2 else 0
            pontos.append((px + lado * 0.7, py + lado * 0.7))
        pygame.draw.lines(tela, (60, 60, 80), False, pontos, 7)
        pygame.draw.lines(tela, (225, 225, 240), False, pontos, 4)

        # O ovo (cabeça do martelo) com squash no impacto
        sup = self.jogador.avatar(72)
        if impacto > 0.02:
            w, h = sup.get_size()
            sup = pygame.transform.smoothscale(sup, (int(w * (1 + 0.35 * impacto)),
                                                     int(h * (1 - 0.3 * impacto))))
        if angulo:
            sup = pygame.transform.rotate(sup, angulo)
        tela.blit(sup, sup.get_rect(center=(int(cx), int(cy))))

        if impacto > 0.3:
            ui.desenhar_texto(tela, "BOING!", (mx + 44, my - 18), 12, BRANCO, "center")
        if self.tonto > 0:
            for k in range(3):
                a = self.tempo * 7 + k * math.tau / 3
                ui.estrela(tela, (cx + math.cos(a) * 34, cy - 44 + math.sin(a) * 9), 6, AMARELO, a)

    def desenhar_hud(self, tela):
        fundo = (26, 22, 18)
        caixa = pygame.Rect(12, 12, 300, 48)
        ui.painel(tela, caixa, fundo, BRANCO, 12, 3, sombra=False)
        ui.desenhar_texto(tela, f"PONTOS: {self.pontos}", (caixa.x + 16, caixa.centery), 14,
                          AMARELO, "midleft")

        if self.combo >= 2:
            mult = _multiplicador(self.combo)
            cor = LARANJA if mult >= 3 else AMARELO if mult == 2 else BRANCO
            texto = f"COMBO {self.combo}" + (f"  ×{mult}" if mult > 1 else "")
            sup = ui.texto(texto, 12, cor)
            c2 = pygame.Rect(12, 66, sup.get_width() + 28, 30)
            ui.painel(tela, c2, fundo, cor, 10, 2, sombra=False)
            tela.blit(sup, sup.get_rect(midleft=(c2.x + 14, c2.centery + 1)))

        # Relógio (pisca e pula nos últimos 10 s)
        relogio = pygame.Rect(0, 12, 150, 48)
        relogio.centerx = LARGURA // 2
        urgente = self.tempo_restante <= 10 and not self.acabou
        pulo = 0
        cor = BRANCO
        if urgente:
            frac = self.tempo_restante % 1.0
            pulo = int(abs(math.sin(frac * math.pi)) * 6)
            cor = (255, 110, 100) if int(self.tempo_restante * 4) % 2 == 0 else AMARELO
        relogio.y -= pulo
        ui.painel(tela, relogio, fundo, cor, 12, 3, sombra=False)
        rc = (relogio.x + 28, relogio.centery)
        pygame.draw.circle(tela, BRANCO, rc, 14)
        pygame.draw.circle(tela, (40, 44, 70), rc, 14, 3)
        ang = -math.pi / 2 + (1 - self.tempo_restante / TEMPO_PARTIDA) * math.tau
        pygame.draw.line(tela, (220, 50, 50), rc, (rc[0] + math.cos(ang) * 9, rc[1] + math.sin(ang) * 9), 2)
        ui.desenhar_texto(tela, _formatar_tempo(self.tempo_restante),
                          (relogio.right - 16, relogio.centery + 1), 16, cor, "midright")

        # Meta e recorde
        meta = META[self.opcao]
        caixa = pygame.Rect(0, 12, 208, 48)
        caixa.right = relogio.right + 20 + 208
        ui.painel(tela, caixa, fundo, BRANCO, 12, 3, sombra=False)
        ok = self.pontos >= meta
        ui.desenhar_texto(tela, f"META: {meta}", (caixa.x + 12, caixa.y + 9),
                          10, (150, 240, 120) if ok else (200, 220, 255))
        rec = self.recorde()
        ui.desenhar_texto(tela, f"RECORDE: {rec if rec is not None else '--'}",
                          (caixa.x + 12, caixa.y + 27), 10, AMARELO)
        if ok:
            ui.estrela(tela, (caixa.right - 20, caixa.centery), 10, AMARELO, self.tempo)
