import math
import random

import pygame

from settings import *
from core import ui
from jogos.base import MiniJogo

# ============================================================
# OVONOIDE
# ============================================================
# Breakout/Arkanoid onde a bola é o SEU OVO! Rebata-o com a
# cama elástica e quebre todos os blocos de doce do fliperama.
#
#   NORMAL   -> 1 batida (10 pts)
#   DURO     -> 2 batidas, racha na primeira (20 pts)
#   METAL    -> indestrutível
#   SURPRESA -> tem o seu ovo desenhado e sempre solta um power-up (30 pts)
#
# Power-ups (cápsulas que caem): GRANDE, GRUDE, MULTI, LENTO, FOGO, VIDA.

# Arena
PAREDE_ESQ = 34
PAREDE_DIR = 990
PAREDE_TOPO = 86

# Grade de blocos
COLS = 12
LINHAS = 8
BLOCO_L = 72
BLOCO_A = 28
VAO = 4
GRADE_X = 58
GRADE_Y = 110

# Cama elástica (raquete)
RAQUETE_Y = 660                 # topo da lona
RAQUETE_L = 130
RAQUETE_GRANDE = 190
RAQUETE_A = 18
VEL_RAQUETE = 700.0
VEL_MOUSE = 1800.0

# Ovo (bola)
OVO_ALT = 32
RAIO = 15
VEL_INICIAL = 420.0
VEL_POR_BLOCO = 12.0
VEL_MAX = 720.0
VEL_POR_FASE = 40.0
VEL_FASE_MAX = 600.0
VY_MIN = 0.35                   # |vy| mínimo (evita loops horizontais)
PASSO_MAX = 8.0                 # subpassos (evita atravessar blocos)
ANGULO_MAX = math.radians(60)
TEMPO_TRAVADO = 12.0            # sem quebrar nada -> ângulo com aleatoriedade

VIDAS = 3
VIDAS_MAX = 5
BONUS_FASE = 500

# Power-ups
VEL_CAPSULA = 160.0
TEMPO_GRANDE = 12.0
PEGADAS_GRUDE = 3
TEMPO_GRUDE = 4.0               # solta sozinho depois disso
TEMPO_LENTO = 10.0
TEMPO_FOGO = 6.0
CHANCE_PODER = 0.12
PODERES = {
    # nome: (cor, rótulo, peso)
    "grande": ((70, 150, 255), "←→", 3.0),
    "grude": ((90, 210, 110), "G", 2.0),
    "multi": ((170, 110, 240), "×3", 2.0),
    "lento": ((80, 220, 230), "L", 2.0),
    "fogo": ((255, 130, 40), "F", 1.5),
    "vida": ((255, 90, 140), "♥", 1.0),
}
NOMES_PODER = {"grande": "CAMA GRANDE!", "grude": "GRUDE!", "multi": "IRMÃOS!",
               "lento": "DEVAGAR...", "fogo": "OVO DE FOGO!", "vida": "+1 VIDA!"}

TECLAS_ESQ = (pygame.K_LEFT, pygame.K_a)
TECLAS_DIR = (pygame.K_RIGHT, pygame.K_d)
TECLAS_LANCAR = (pygame.K_SPACE, pygame.K_UP, pygame.K_w, pygame.K_RETURN, pygame.K_KP_ENTER)

# Cores das linhas (repetindo) e cores nomeadas dos desenhos
CORES_LINHA = [(255, 90, 90), (255, 160, 60), (255, 220, 70), (120, 220, 90),
               (70, 180, 255), (150, 110, 230)]
CORES_LETRA = {
    "r": (255, 90, 90), "o": (255, 160, 60), "y": (255, 220, 70), "g": (120, 220, 90),
    "b": (70, 180, 255), "p": (150, 110, 230), "w": (245, 245, 250), "k": (70, 70, 110),
    "n": (255, 130, 190),
}

# ------------------------------------------------------------
# 10 FASES DESENHADAS (12 x 8)
#   .  vazio          N  normal (cor da linha)   D  duro
#   M  metal          S  surpresa                e  cor do SEU ovo
#   r o y g b p w k n  normal com cor fixa
# ------------------------------------------------------------
FASES = [
    ("CORAÇÃO", [
        ".rrr....rrr.",
        "rrnrr..rrnrr",
        "rrrSrrrrSrrr",
        "rrrrrrrrrrrr",
        ".rrrrrrrrrr.",
        "..rrrrrrrr..",
        "...rrrrrr...",
        ".....DD.....",
    ]),
    ("OVO", [
        "....DDDD....",
        "...DeeeeD...",
        "..DeeeeeeD..",
        "..DeeyyeeD..",
        ".DeeySSyeeD.",
        ".DeeeyyeeeD.",
        "..DeeeeeeD..",
        "...DDDDDD...",
    ]),
    ("CARINHA", [
        "..yyyyyyyy..",
        ".yyyyyyyyyy.",
        "yykkyyyykkyy",
        "yykSyyyySkyy",
        "yyyyyyyyyyyy",
        "yyrryyyyrryy",
        ".yyrrrrrryy.",
        "..yyyyyyyy..",
    ]),
    ("BONÉ DO ROBERT", [
        "....rrrr....",
        "..oooooooo..",
        ".yyyySyyyyy.",
        ".gggggggggg.",
        ".bbbbbbbbbb.",
        ".pppppppppp.",
        ".DDDDDDDDDDD",
        "......DDDDDD",
    ]),
    ("CASINHA", [
        ".....MM.....",
        "....rrrr....",
        "...rrrrrr...",
        "..rrrSSrrr..",
        ".rrrrrrrrrr.",
        "..wwwwwwww..",
        "..wbbwwbbw..",
        "..wwwoowww..",
    ]),
    ("SOL DE ÓCULOS", [
        "o...oyyo...o",
        "..yyyyyyyy..",
        ".yyyyyyyyyy.",
        "ykkkkkkkkkky",
        "yykkkyykkkyy",
        ".yyyyyyyyyy.",
        "..yyrSSryy..",
        "o...oyyo...o",
    ]),
    ("LIMÃO", [
        "......gg....",
        ".....gg.....",
        "...DDDDDD...",
        ".DyyyyyyyyD.",
        "DyyyySSyyyyD",
        ".DyyyyyyyyD.",
        "...DDDDDD...",
        "M..........M",
    ]),
    ("OVO ESCRITO", [
        "NNNNNNNNNNNN",
        ".eee.b.b.eee",
        ".e.e.b.b.e.e",
        ".e.e.b.b.e.e",
        ".eSe.bSb.eSe",
        ".eee..b..eee",
        "............",
        "MM..NNNN..MM",
    ]),
    ("XADREZ", [
        "N.N.N.N.N.N.",
        ".N.N.N.N.N.N",
        "D.D.S.D.D.D.",
        ".D.D.D.S.D.D",
        "N.N.N.N.N.N.",
        ".N.N.N.N.N.N",
        "M.D.D.D.D.D.",
        ".D.D.D.D.D.M",
    ]),
    ("PIRÂMIDE", [
        ".....SS.....",
        "....NNNN....",
        "...NNNNNN...",
        "..DDDDDDDD..",
        ".NNNNSSNNNN.",
        "NNNNNNNNNNNN",
        "DDDDDDDDDDDD",
        "M..........M",
    ]),
]


def _alcancaveis(mapa):
    """
    Todos os blocos quebráveis dá para alcançar? (o metal é parede;
    a bola entra na grade por baixo). Devolve True/False.
    """
    vistos = set()
    fila = [(c, LINHAS) for c in range(COLS)]           # linha "virtual" embaixo da grade
    while fila:
        c, l = fila.pop()
        if (c, l) in vistos:
            continue
        vistos.add((c, l))
        for dc, dl in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nc, nl = c + dc, l + dl
            if 0 <= nc < COLS and 0 <= nl <= LINHAS and (nc, nl) not in vistos:
                if nl < LINHAS and mapa[nl][nc] == "M":
                    continue
                fila.append((nc, nl))
    for l in range(LINHAS):
        for c in range(COLS):
            if mapa[l][c] not in ".M" and (c, l) not in vistos:
                return False
    return True


def _fase_aleatoria(rnd):
    """Fase gerada (espelhada: a metade esquerda copiada na direita)."""
    while True:
        mapa = []
        densidade = rnd.uniform(0.55, 0.85)
        for l in range(LINHAS):
            metade = []
            for c in range(COLS // 2):
                if rnd.random() > densidade:
                    metade.append(".")
                    continue
                s = rnd.random()
                if s < 0.05 and l >= 2:
                    metade.append("M")
                elif s < 0.10:
                    metade.append("S")
                elif s < 0.35:
                    metade.append("D")
                else:
                    metade.append("N")
            mapa.append("".join(metade) + "".join(reversed(metade)))
        blocos = sum(1 for linha in mapa for ch in linha if ch not in ".M")
        metais = sum(linha.count("M") for linha in mapa)
        if blocos >= 24 and metais <= 6 and _alcancaveis(mapa):
            return mapa


def _rect_bloco(c, l):
    return pygame.Rect(GRADE_X + c * (BLOCO_L + VAO), GRADE_Y + l * (BLOCO_A + VAO), BLOCO_L, BLOCO_A)


# ============================================================
# DESENHOS PRÉ-RENDERIZADOS
# ============================================================

_blocos = {}


def _bloco_sup(tipo, cor, rachado=False):
    chave = (tipo, cor, rachado)
    s = _blocos.get(chave)
    if s is not None:
        return s

    s = pygame.Surface((BLOCO_L, BLOCO_A), pygame.SRCALPHA)
    r = s.get_rect()
    if tipo == "M":
        pygame.draw.rect(s, (70, 72, 86), r, border_radius=4)
        pygame.draw.rect(s, (150, 152, 168), r.inflate(-4, -4), border_radius=3)
        pygame.draw.rect(s, (205, 208, 222), (4, 4, BLOCO_L - 8, 6), border_radius=2)
        pygame.draw.rect(s, (110, 112, 126), (4, BLOCO_A - 9, BLOCO_L - 8, 5), border_radius=2)
        for x in (8, BLOCO_L - 9):
            for y in (8, BLOCO_A - 9):
                pygame.draw.circle(s, (90, 92, 104), (x, y), 3)
                pygame.draw.circle(s, (220, 222, 235), (x - 1, y - 1), 1)
    else:
        if tipo == "S":
            cor = (255, 200, 40)
        escuro = ui.escurecer(cor, 50)
        pygame.draw.rect(s, escuro, r, border_radius=5)
        pygame.draw.rect(s, cor, r.inflate(-4, -4).move(0, -1), border_radius=4)
        pygame.draw.rect(s, ui.clarear(cor, 50), (5, 3, BLOCO_L - 10, 6), border_radius=3)
        pygame.draw.rect(s, escuro, (4, BLOCO_A - 7, BLOCO_L - 8, 4), border_radius=2)
        if tipo == "D":
            pygame.draw.rect(s, ui.escurecer(cor, 90), r, 3, border_radius=5)
            pygame.draw.rect(s, ui.clarear(cor, 70), (10, 11, BLOCO_L - 20, 3), border_radius=1)
            if rachado:
                pts = [(22, 2), (30, 11), (26, 16), (36, 26)]
                pygame.draw.lines(s, (40, 30, 40), False, pts, 2)
                pygame.draw.lines(s, (40, 30, 40), False, [(50, 3), (46, 12), (54, 20)], 2)
        elif tipo == "S":
            pygame.draw.rect(s, (255, 250, 200), r.inflate(-2, -2), 2, border_radius=5)
    _blocos[chave] = s
    return s


_fundo_arena = {}


def _estrelas():
    if "estrelas" not in _fundo_arena:
        rnd = random.Random(33)
        _fundo_arena["estrelas"] = [(rnd.randrange(PAREDE_ESQ + 6, PAREDE_DIR - 6),
                                     rnd.randrange(PAREDE_TOPO + 6, 420),
                                     rnd.uniform(1.5, 4.0), rnd.uniform(0, math.tau))
                                    for _ in range(60)]
    return _fundo_arena["estrelas"]


# ============================================================
# BLOCO, OVO E CÁPSULA
# ============================================================

class Bloco:

    def __init__(self, tipo, cor, c, l):
        self.tipo = tipo                    # N D M S
        self.cor = cor
        self.c, self.l = c, l
        self.rect = _rect_bloco(c, l)
        self.vida = 2 if tipo == "D" else 1
        self.brilho = 0.0                   # piscada ao levar batida

    @property
    def quebravel(self):
        return self.tipo != "M"


class Ovo:

    def __init__(self, x, y, aparencia=None):
        self.x = float(x)
        self.y = float(y)
        self.dx = 0.0                       # direção (normalizada)
        self.dy = -1.0
        self.preso = True                   # parado na cama (esperando o lançamento)
        self.grudado = False                # preso pelo GRUDE (solta sozinho)
        self.offset = 0.0                   # posição na cama quando preso
        self.tempo_preso = 0.0
        self.aparencia = aparencia          # None = o próprio jogador
        self.ang = 0.0
        self.squash = 0.0
        self.squash_eixo = "y"


class Capsula:

    def __init__(self, tipo, x, y):
        self.tipo = tipo
        self.x = float(x)
        self.y = float(y)

    @property
    def rect(self):
        return pygame.Rect(int(self.x) - 20, int(self.y) - 10, 40, 20)


# ============================================================
# JOGO
# ============================================================

class Ovonoide(MiniJogo):

    ID = "ovonoide"
    TITULO = "OVONOIDE"
    TITULO_CURTO = "OVONOIDE"
    DESCRICAO = "A bola é o SEU OVO! Rebata-o na cama elástica e quebre os blocos de doce do fliperama."
    COR = (255, 80, 200)
    INSTRUCOES = [
        "A bola é o seu ovo! Não deixe ele cair.",
        "Quebre todos os blocos (o METAL não quebra).",
        "O bloco com o seu ovo sempre solta um PODER!",
        "Onde o ovo bate na cama muda o ângulo.",
        "← → A/D ou MOUSE move • ESPAÇO/CLIQUE lança",
    ]
    OPCOES = None
    MENOR_MELHOR = False
    ROTULO_PONTOS = "PONTOS"
    CONTAGEM = True

    MOEDAS_POR = 270
    MOEDAS_MAX = 30

    # --------------------------------------------------------
    # CENÁRIO: fliperama neon
    # --------------------------------------------------------

    @classmethod
    def criar_fundo(cls, jogador):
        sup = ui.gradiente(LARGURA, ALTURA, (18, 20, 48), (8, 8, 24))

        # Grade em perspectiva no terço de baixo
        grade = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        fuga = (512, 430)
        cor = (255, 80, 200, 90)
        for i in range(-12, 13):
            x_base = 512 + i * 120
            pygame.draw.line(grade, cor, fuga, (x_base, ALTURA), 2)
        for i in range(1, 12):
            t = (i / 11) ** 2
            y = int(fuga[1] + (ALTURA - fuga[1]) * t)
            pygame.draw.line(grade, cor, (0, y), (LARGURA, y), 2)
        # Some perto do horizonte
        pygame.draw.rect(grade, (0, 0, 0, 0), (0, 0, LARGURA, fuga[1] + 2))
        sup.blit(grade, (0, 0))
        for i in range(8):
            y = fuga[1] + i
            pygame.draw.line(sup, ui.misturar((18, 20, 48), (255, 80, 200), 0.5 - i * 0.06),
                             (0, y), (LARGURA, y))

        # Moldura neon da arena
        for largura, cor_m in ((10, (80, 30, 90)), (6, (190, 60, 170)), (2, (255, 170, 240))):
            pygame.draw.line(sup, cor_m, (PAREDE_ESQ - 5, ALTURA), (PAREDE_ESQ - 5, PAREDE_TOPO - 5), largura)
            pygame.draw.line(sup, cor_m, (PAREDE_DIR + 5, ALTURA), (PAREDE_DIR + 5, PAREDE_TOPO - 5), largura)
            pygame.draw.line(sup, cor_m, (PAREDE_ESQ - 5, PAREDE_TOPO - 5), (PAREDE_DIR + 5, PAREDE_TOPO - 5),
                             largura)
        return sup

    @classmethod
    def desenhar_icone(cls, sup, jogador):
        w, h = sup.get_size()
        esc = w / LARGURA
        bl, ba = max(6, int(BLOCO_L * esc * 1.5)), max(4, int(BLOCO_A * esc * 1.5))
        for l in range(3):
            for c in range(6):
                cor = CORES_LINHA[l]
                x = w // 2 - 3 * (bl + 2) + c * (bl + 2)
                pygame.draw.rect(sup, ui.escurecer(cor, 50), (x, 14 + l * (ba + 2), bl, ba), border_radius=2)
                pygame.draw.rect(sup, cor, (x + 1, 14 + l * (ba + 2), bl - 2, ba - 2), border_radius=2)
        jogador.desenhar(sup, (w // 2 + 20, h // 2 + 10), 30, angulo=20)
        cama = pygame.Rect(0, 0, 44, 7)
        cama.midtop = (w // 2 + 4, h - 20)
        pygame.draw.rect(sup, (60, 60, 80), cama.move(0, 3), border_radius=3)
        pygame.draw.rect(sup, AMARELO, (cama.x + 3, cama.y, cama.w - 6, 4), border_radius=2)

    # --------------------------------------------------------
    # PARTIDA
    # --------------------------------------------------------

    def reiniciar(self):
        _estrelas()
        self.fase = 1
        self.vidas = VIDAS
        self.raquete_x = LARGURA / 2
        self.raquete_l = float(RAQUETE_L)
        self.alvo_mouse = None
        self.teclas = set()
        self.afundar = 0.0
        self.afundar_x = 0.0
        self.combo = 0
        self.hitstop = 0.0
        self.grande = 0.0
        self.grude = 0
        self.lento = 0.0
        self.fogo = 0.0
        self.capsulas = []
        self.ultimo_poder = -10.0
        self.cacos = []                 # pedaços de casca quando o ovo cai [x, y, vx, vy, ang, vida, cor]
        self.transicao = 0.0            # pausa entre fases
        self.aviso = 0.0                # nome da fase aparecendo
        self.morto = False
        self.tempo_morto = 0.0
        self._montar_fase()

    def _montar_fase(self):
        if self.fase <= len(FASES):
            nome, mapa = FASES[self.fase - 1]
        else:
            nome, mapa = "SURPRESA", _fase_aleatoria(random.Random())
        self.nome_fase = nome
        self.blocos = []
        self.grade = [[None] * COLS for _ in range(LINHAS)]
        for l, linha in enumerate(mapa):
            for c, ch in enumerate(linha):
                if ch == ".":
                    continue
                if ch in "NDSM":
                    tipo, cor = ch, CORES_LINHA[l % len(CORES_LINHA)]
                elif ch == "e":
                    tipo, cor = "N", self.jogador.cor
                else:
                    tipo, cor = "N", CORES_LETRA[ch]
                b = Bloco(tipo, cor, c, l)
                self.blocos.append(b)
                self.grade[l][c] = b
        self.vel_base = min(VEL_FASE_MAX, VEL_INICIAL + VEL_POR_FASE * (self.fase - 1))
        self.vel = self.vel_base
        self.sem_quebrar = 0.0
        self.aviso = 2.0
        self._novo_ovo()

    def _novo_ovo(self):
        """Um ovo só, grudado no meio da cama."""
        self.ovos = [Ovo(self.raquete_x, RAQUETE_Y - RAIO)]
        self.ovos[0].offset = 0.0
        self.combo = 0
        self.capsulas = []
        self.grude = 0
        self.fogo = 0.0

    def restantes(self):
        return sum(1 for b in self.blocos if b.quebravel)

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
        if e.type == pygame.MOUSEMOTION:
            self.alvo_mouse = float(e.pos[0])
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.alvo_mouse = float(e.pos[0])
            self._lancar()
        elif e.type == pygame.KEYDOWN:
            if e.key in TECLAS_ESQ + TECLAS_DIR:
                self.alvo_mouse = None
            elif e.key in TECLAS_LANCAR:
                self._lancar()

    def _lancar(self):
        if self.morto or self.transicao > 0:
            return
        for o in self.ovos:
            if o.preso:
                self._soltar(o)

    def _soltar(self, o):
        o.preso = False
        o.grudado = False
        # Ângulo depende de onde está na cama (+ um pouquinho de variação)
        frac = max(-1.0, min(1.0, o.offset / (self.raquete_l / 2)))
        a = frac * ANGULO_MAX * 0.8 + random.uniform(-0.2, 0.2)
        o.dx, o.dy = math.sin(a), -math.cos(a)
        o.y = RAQUETE_Y - RAIO - 1
        self.aviso = 0.0
        self.som("pulo", 0.5)

    # --------------------------------------------------------
    # LÓGICA
    # --------------------------------------------------------

    def atualizar_jogo(self, dt):
        self._mover_raquete(dt)
        self._animar(dt)

        if self.morto:
            self.tempo_morto += dt
            if self.tempo_morto > 1.4:
                self.terminar(linhas=[f"FASE: {self.fase}", f"PONTOS: {self.pontos}"])
            return

        if self.transicao > 0:
            self.transicao -= dt
            if self.transicao <= 0:
                self.fase += 1
                self._montar_fase()
            return

        # Hit-stop: congela a bola um instantinho em batidas fortes
        if self.hitstop > 0:
            self.hitstop -= dt
            return

        # Timers dos poderes
        self.grande = max(0.0, self.grande - dt)
        self.lento = max(0.0, self.lento - dt)
        self.fogo = max(0.0, self.fogo - dt)
        self.sem_quebrar += dt
        self.aviso = max(0.0, self.aviso - dt)

        vel = self.vel * (0.7 if self.lento > 0 else 1.0)
        for o in list(self.ovos):
            if o.preso:
                o.tempo_preso += dt
                meia = self.raquete_l / 2 - 6
                o.offset = max(-meia, min(meia, o.offset))
                o.x = self.raquete_x + o.offset
                o.y = RAQUETE_Y - RAIO - self.afundar * 6
                # O grude solta sozinho depois de um tempinho
                if o.grudado and o.tempo_preso > TEMPO_GRUDE:
                    self._soltar(o)
                continue
            self._mover_ovo(o, vel * dt)
            if o.y - RAIO > ALTURA:
                self.ovos.remove(o)
                self._ovo_caiu(o)

        if not self.ovos and not self.morto:
            self._perder_vida()

        self._mover_capsulas(dt)

        if self.restantes() == 0 and self.transicao <= 0:
            self._fase_limpa()

    def _mover_raquete(self, dt):
        esq = any(k in self.teclas for k in TECLAS_ESQ)
        dir_ = any(k in self.teclas for k in TECLAS_DIR)
        if esq or dir_:
            self.alvo_mouse = None
            self.raquete_x += (dir_ - esq) * VEL_RAQUETE * dt
        elif self.alvo_mouse is not None:
            dist = self.alvo_mouse - self.raquete_x
            passo = VEL_MOUSE * dt
            self.raquete_x += max(-passo, min(passo, dist))

        # Cama grande cresce/encolhe devagar
        alvo = RAQUETE_GRANDE if self.grande > 0 else RAQUETE_L
        self.raquete_l += (alvo - self.raquete_l) * min(1.0, dt * 10)

        meia = self.raquete_l / 2
        self.raquete_x = max(PAREDE_ESQ + meia, min(PAREDE_DIR - meia, self.raquete_x))

    def _animar(self, dt):
        self.afundar = max(0.0, self.afundar - dt * 5)
        for o in self.ovos:
            o.squash = max(0.0, o.squash - dt)
            if not o.preso:
                o.ang = (o.ang - o.dx * self.vel * dt * 0.9) % 360
        for b in self.blocos:
            b.brilho = max(0.0, b.brilho - dt * 4)
        for p in self.cacos:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[3] += 900 * dt
            p[4] += p[2] * dt
            p[5] -= dt
        self.cacos = [p for p in self.cacos if p[5] > 0]

        # Ovo de fogo solta chamas
        if self.fogo > 0 and not self.morto:
            for o in self.ovos:
                if not o.preso and random.random() < 0.8:
                    self.particulas.explodir((o.x, o.y), [(255, 120, 30), (255, 200, 60), (255, 80, 20)],
                                             2, 60, 0.4, (3, 6), gravidade=-200)

    # ---------------- Física do ovo ----------------

    def _mover_ovo(self, o, dist):
        passos = max(1, math.ceil(dist / PASSO_MAX))
        d = dist / passos
        for _ in range(passos):
            o.x += o.dx * d
            o.y += o.dy * d

            # Paredes
            if o.x - RAIO < PAREDE_ESQ and o.dx < 0:
                o.x = PAREDE_ESQ + RAIO
                o.dx = -o.dx
                self._quicou(o, "x")
            elif o.x + RAIO > PAREDE_DIR and o.dx > 0:
                o.x = PAREDE_DIR - RAIO
                o.dx = -o.dx
                self._quicou(o, "x")
            if o.y - RAIO < PAREDE_TOPO and o.dy < 0:
                o.y = PAREDE_TOPO + RAIO
                o.dy = -o.dy
                self._quicou(o, "y")

            # Cama elástica
            if o.dy > 0 and RAQUETE_Y - 2 <= o.y + RAIO <= RAQUETE_Y + 12:
                meia = self.raquete_l / 2
                if self.raquete_x - meia - RAIO * 0.6 <= o.x <= self.raquete_x + meia + RAIO * 0.6:
                    self._bater_cama(o)
                    return

            self._colidir_blocos(o)

    def _colidir_blocos(self, o):
        """Colisão círculo x blocos (resolve pelo eixo de menor penetração)."""
        c0 = int((o.x - RAIO - GRADE_X) // (BLOCO_L + VAO))
        c1 = int((o.x + RAIO - GRADE_X) // (BLOCO_L + VAO))
        l0 = int((o.y - RAIO - GRADE_Y) // (BLOCO_A + VAO))
        l1 = int((o.y + RAIO - GRADE_Y) // (BLOCO_A + VAO))
        batidas = []
        for l in range(max(0, l0), min(LINHAS - 1, l1) + 1):
            for c in range(max(0, c0), min(COLS - 1, c1) + 1):
                b = self.grade[l][c]
                if b is None:
                    continue
                r = b.rect
                px = max(r.left, min(o.x, r.right))
                py = max(r.top, min(o.y, r.bottom))
                if (o.x - px) ** 2 + (o.y - py) ** 2 < RAIO * RAIO:
                    batidas.append(b)
        if not batidas:
            return False

        virou_x = virou_y = False
        for b in batidas:
            atravessa = self.fogo > 0 and b.quebravel
            if atravessa:
                b.vida = 1                      # o fogo quebra de uma vez
            else:
                r = b.rect
                pen_x = min(o.x + RAIO - r.left, r.right - (o.x - RAIO))
                pen_y = min(o.y + RAIO - r.top, r.bottom - (o.y - RAIO))
                if pen_x < pen_y:
                    indo = (o.dx > 0 and r.centerx > o.x) or (o.dx < 0 and r.centerx < o.x)
                    if indo and not virou_x:
                        o.dx = -o.dx
                        virou_x = True
                    o.x += -pen_x if r.centerx > o.x else pen_x
                else:
                    indo = (o.dy > 0 and r.centery > o.y) or (o.dy < 0 and r.centery < o.y)
                    if indo and not virou_y:
                        o.dy = -o.dy
                        virou_y = True
                    o.y += -pen_y if r.centery > o.y else pen_y
            self._acertar(b, o)

        if virou_x or virou_y:
            self._quicou(o, "x" if virou_x and not virou_y else "y")
        return True

    def _quicou(self, o, eixo):
        """Depois de cada batida: |vy| mínimo e aleatoriedade anti-trava."""
        o.squash = 0.12
        o.squash_eixo = eixo
        if self.sem_quebrar > TEMPO_TRAVADO:
            self._girar(o, math.radians(random.uniform(-5, 5)))
        self._corrigir_angulo(o)

    @staticmethod
    def _girar(o, a):
        c, s = math.cos(a), math.sin(a)
        o.dx, o.dy = o.dx * c - o.dy * s, o.dx * s + o.dy * c

    @staticmethod
    def _corrigir_angulo(o):
        n = math.hypot(o.dx, o.dy) or 1.0
        o.dx, o.dy = o.dx / n, o.dy / n
        if abs(o.dy) < VY_MIN:
            sinal = 1 if o.dy > 0 else -1
            if o.dy == 0:
                sinal = random.choice((-1, 1))
            o.dy = sinal * VY_MIN
            o.dx = math.copysign(math.sqrt(1 - VY_MIN * VY_MIN), o.dx or 1.0)

    def _bater_cama(self, o):
        meia = self.raquete_l / 2
        frac = max(-1.0, min(1.0, (o.x - self.raquete_x) / meia))
        a = frac * ANGULO_MAX
        o.dx, o.dy = math.sin(a), -math.cos(a)
        if self.sem_quebrar > TEMPO_TRAVADO:
            self._girar(o, math.radians(random.uniform(-5, 5)))
            self._corrigir_angulo(o)
        # Poucos blocos sobrando e nada quebra faz tempo: a cama dá uma
        # "ajudinha" mirando um pouco para um dos blocos que faltam
        if self.sem_quebrar > TEMPO_TRAVADO and self.restantes() <= 4:
            alvos = [b for b in self.blocos if b.quebravel]
            alvo = random.choice(alvos).rect.center
            ax, ay = alvo[0] - o.x, alvo[1] - o.y
            n = math.hypot(ax, ay) or 1.0
            k = 0.85 if self.sem_quebrar > 2 * TEMPO_TRAVADO else 0.6
            o.dx = o.dx * (1 - k) + ax / n * k
            o.dy = min(-0.2, o.dy * (1 - k) + ay / n * k)
            self._corrigir_angulo(o)
        o.y = RAQUETE_Y - RAIO
        o.squash = 0.12
        o.squash_eixo = "y"
        self.afundar = 1.0
        self.afundar_x = o.x - self.raquete_x
        self.combo = 0
        self.som("boing", 0.5)

        if self.grude > 0:
            self.grude -= 1
            o.preso = True
            o.grudado = True
            o.offset = o.x - self.raquete_x
            o.tempo_preso = 0.0

    # ---------------- Blocos ----------------

    def _acertar(self, b, o):
        b.brilho = 1.0
        if not b.quebravel:
            self.som("bater", 0.4)
            return
        b.vida -= 1
        if b.vida > 0:
            # Bloco duro rachou
            self.hitstop = 0.03
            self.som("bater", 0.7)
            self.particulas.explodir(b.rect.center, [b.cor, BRANCO], 5, 120, 0.35, (2, 4))
            return
        self._quebrar(b)

    def _quebrar(self, b):
        self.blocos.remove(b)
        self.grade[b.l][b.c] = None
        self.sem_quebrar = 0.0
        self.combo += 1
        mult = min(self.combo, 4)
        base = {"N": 10, "D": 20, "S": 30}[b.tipo]
        ganho = base * mult
        self.pontos += ganho
        self.vel = min(VEL_MAX, self.vel + VEL_POR_BLOCO)

        cor = (255, 200, 40) if b.tipo == "S" else b.cor
        cx, cy = b.rect.center
        # 8 cacos da cor do bloco
        for i in range(8):
            a = i * math.tau / 8 + random.uniform(-0.3, 0.3)
            v = random.uniform(120, 260)
            self.particulas.lista.append([float(cx), float(cy), math.cos(a) * v, math.sin(a) * v - 80,
                                          0.6, 0.6, random.choice([cor, ui.clarear(cor, 60)]),
                                          random.randint(4, 7), 700])
        texto = f"+{base}" + (f" ×{mult}" if mult > 1 else "")
        self.textos.adicionar(texto, (cx, cy - 10), AMARELO if mult > 1 else BRANCO, 12)
        self.som("ponto", 0.5)
        if self.combo >= 2:
            self.tremer(0.08)

        if b.tipo == "S" or random.random() < CHANCE_PODER:
            self._soltar_capsula(cx, cy)

    def _soltar_capsula(self, x, y):
        tipos = [t for t in PODERES if not (t == "vida" and self.vidas >= VIDAS_MAX)]
        tipo = random.choices(tipos, [PODERES[t][2] for t in tipos])[0]
        self.capsulas.append(Capsula(tipo, x, y))

    def _mover_capsulas(self, dt):
        meia = self.raquete_l / 2
        cama = pygame.Rect(int(self.raquete_x - meia), RAQUETE_Y, int(self.raquete_l), RAQUETE_A)
        vivas = []
        for c in self.capsulas:
            c.y += VEL_CAPSULA * dt
            if c.rect.colliderect(cama):
                self._pegar(c)
                continue
            if c.y - 10 < ALTURA:
                vivas.append(c)
        self.capsulas = vivas

    def _pegar(self, c):
        self.som("acerto")
        cor = PODERES[c.tipo][0]
        self.particulas.explodir((c.x, RAQUETE_Y), [cor, BRANCO, AMARELO], 18, 220, 0.6)
        # Dois poderes seguidos: o texto do segundo fica mais para cima
        recente = self.tempo - self.ultimo_poder < 0.8
        self.ultimo_poder = self.tempo
        y = RAQUETE_Y - (80 if recente else 50)
        x = max(160, min(LARGURA - 160, c.x))
        self.textos.adicionar(NOMES_PODER[c.tipo], (x, y), ui.clarear(cor, 40), 16)
        self.pontos += 5
        if c.tipo == "grande":
            self.grande = TEMPO_GRANDE
        elif c.tipo == "grude":
            self.grude = PEGADAS_GRUDE
        elif c.tipo == "multi":
            self._multiplicar()
        elif c.tipo == "lento":
            self.lento = TEMPO_LENTO
        elif c.tipo == "fogo":
            self.fogo = TEMPO_FOGO
        elif c.tipo == "vida":
            self.vidas = min(VIDAS_MAX, self.vidas + 1)

    def _multiplicar(self):
        """+2 ovos irmãos (mesmo cabelo, outras cores de ovo)."""
        soltos = [o for o in self.ovos if not o.preso]
        base = soltos[0] if soltos else self.ovos[0]
        if base.preso:
            self._soltar(base)
        ap = self.jogador.aparencia()
        cores_usadas = {o.aparencia[0] if o.aparencia else ap[0] for o in self.ovos}
        livres = [i for i in range(4) if i not in cores_usadas] or [(ap[0] + 1) % 4, (ap[0] + 2) % 4]
        for i, giro in enumerate((-0.5, 0.5)):
            if len(self.ovos) >= 9:
                break
            irmao = Ovo(base.x, base.y, (livres[i % len(livres)], ap[1], ap[2], ap[3]))
            irmao.preso = False
            irmao.dx, irmao.dy = base.dx, base.dy
            self._girar(irmao, giro)
            if irmao.dy > 0:
                irmao.dy = -irmao.dy             # nasce subindo
            self._corrigir_angulo(irmao)
            self.ovos.append(irmao)

    # ---------------- Vidas e fases ----------------

    def _ovo_caiu(self, o):
        """O ovo racha lá embaixo."""
        ap = o.aparencia or self.jogador.aparencia()
        from core.jogador import Jogador
        cor = Jogador.cor_do_ovo(ap[0])
        x = max(PAREDE_ESQ + 20, min(PAREDE_DIR - 20, o.x))
        for _ in range(7):
            self.cacos.append([x, ALTURA - 20, random.uniform(-160, 160), random.uniform(-520, -300),
                               random.uniform(0, 360), 1.0, cor])
        self.particulas.explodir((x, ALTURA - 16), [(255, 240, 150), (255, 200, 60), BRANCO], 16, 220, 0.6)
        self.som("virar", 0.7)

    def _perder_vida(self):
        self.vidas -= 1
        self.tremer(0.3)
        self.textos.adicionar("CRACK!", (LARGURA // 2, ALTURA - 120), (255, 150, 120), 24)
        self.som("erro")
        if self.vidas <= 0:
            self.vidas = 0
            self.morto = True
            self.tempo_morto = 0.0
            return
        self.grande = 0.0
        self.lento = 0.0
        self.vel = self.vel_base
        self.sem_quebrar = 0.0
        self._novo_ovo()

    def _fase_limpa(self):
        self.pontos += BONUS_FASE
        self.transicao = 2.0
        self.som("vencer", 0.8)
        self.textos.adicionar(f"FASE LIMPA! +{BONUS_FASE}", (LARGURA // 2, 400), AMARELO, 24)
        cores = [self.jogador.cor, self.jogador.cor_clara, AMARELO, BRANCO]
        for o in self.ovos:
            self.particulas.explodir((o.x, o.y), cores, 30, 320, 1.0)
        self.ovos = []
        self.capsulas = []

    # --------------------------------------------------------
    # DESENHO
    # --------------------------------------------------------

    def _desenhar_estrelas(self, tela):
        t = self.tempo
        for x, y, vel, fase in _estrelas():
            b = math.sin(t * vel + fase)
            if b > -0.3:
                c = int(150 + 105 * max(0.0, b))
                tela.fill((c, c, min(255, c + 20)), (x, y, 2, 2))

    def _desenhar_blocos(self, tela):
        for b in self.blocos:
            sup = _bloco_sup(b.tipo, b.cor, b.tipo == "D" and b.vida == 1)
            tela.blit(sup, b.rect)
            if b.tipo == "S":
                self.jogador.desenhar(tela, (b.rect.centerx, b.rect.centery + 1), 20)
            if b.brilho > 0:
                pygame.draw.rect(tela, BRANCO, b.rect, max(1, int(3 * b.brilho)), border_radius=5)

    def _desenhar_cama(self, tela):
        meia = self.raquete_l / 2
        x0, x1 = int(self.raquete_x - meia), int(self.raquete_x + meia)
        y = RAQUETE_Y
        # Perninhas e barra
        for px in (x0 + 12, x1 - 12):
            pygame.draw.line(tela, (40, 40, 56), (px, y + 10), (px - 6 if px < self.raquete_x else px + 6,
                                                               y + 30), 6)
        barra = pygame.Rect(x0, y + 4, x1 - x0, 14)
        pygame.draw.rect(tela, (60, 60, 80), barra, border_radius=7)
        pygame.draw.rect(tela, (120, 120, 150), (x0 + 6, y + 6, x1 - x0 - 12, 3), border_radius=2)
        # Molinhas
        for i in range(1, 6):
            mx = x0 + (x1 - x0) * i / 6
            pygame.draw.line(tela, (200, 200, 220), (mx, y + 4), (mx, y + 1), 2)
        # Lona amarela que afunda onde o ovo bateu
        sag = 6 * self.afundar
        cx = self.raquete_x + max(-meia + 10, min(meia - 10, self.afundar_x))
        pontos = [(x0 + 4, y), (cx, y + sag), (x1 - 4, y), (x1 - 4, y + 5), (cx, y + 5 + sag), (x0 + 4, y + 5)]
        pygame.draw.polygon(tela, (255, 214, 64), pontos)
        pygame.draw.polygon(tela, (190, 140, 20), pontos, 1)
        pygame.draw.circle(tela, (230, 80, 120), (x0 + 4, y + 3), 5)
        pygame.draw.circle(tela, (230, 80, 120), (x1 - 4, y + 3), 5)

    def _desenhar_ovo(self, tela, o):
        img = self.jogador.avatar(OVO_ALT, o.aparencia)
        if o.ang:
            img = pygame.transform.rotate(img, o.ang)
        if o.squash > 0:
            p = math.sin(math.pi * (1 - o.squash / 0.12))
            if o.squash_eixo == "y":
                sx, sy = 1 + 0.2 * p, 1 - 0.25 * p
            else:
                sx, sy = 1 - 0.25 * p, 1 + 0.2 * p
            w, h = img.get_size()
            img = pygame.transform.smoothscale(img, (max(1, round(w * sx)), max(1, round(h * sy))))
        if self.fogo > 0 and not o.preso:
            pygame.draw.circle(tela, (255, 120, 30), (int(o.x), int(o.y)), RAIO + 5, 3)
        tela.blit(img, img.get_rect(center=(round(o.x), round(o.y))))

    def _desenhar_capsula(self, tela, c):
        cor, rotulo, _ = PODERES[c.tipo]
        r = c.rect
        pygame.draw.rect(tela, ui.escurecer(cor, 90), r.inflate(4, 4), border_radius=10)
        pygame.draw.rect(tela, cor, r, border_radius=10)
        pygame.draw.rect(tela, ui.clarear(cor, 70), (r.x + 6, r.y + 3, r.w - 12, 4), border_radius=2)
        ui.desenhar_texto(tela, rotulo, (r.centerx, r.centery + 1), 10, BRANCO, "center")

    def desenhar_jogo(self, tela):
        tela.blit(self.fundo(self.jogador), (0, 0))
        self._desenhar_estrelas(tela)
        self._desenhar_blocos(tela)
        for c in self.capsulas:
            self._desenhar_capsula(tela, c)
        self._desenhar_cama(tela)

        # Mira pontilhada quando o ovo está esperando na cama
        for o in self.ovos:
            if o.preso and not self.morto:
                frac = max(-1.0, min(1.0, o.offset / (self.raquete_l / 2)))
                a = frac * ANGULO_MAX * 0.8
                for i in range(1, 6):
                    d = 30 + i * 18
                    px = o.x + math.sin(a) * d
                    py = o.y - math.cos(a) * d
                    if int(self.tempo * 6) % 5 != i - 1:
                        pygame.draw.circle(tela, (255, 170, 240), (int(px), int(py)), 3)

        for o in self.ovos:
            self._desenhar_ovo(tela, o)

        for x, y, vx, vy, ang, vida, cor in self.cacos:
            pontos = [(x + math.cos(math.radians(ang + k * 120)) * 9,
                       y + math.sin(math.radians(ang + k * 120)) * 6) for k in range(3)]
            pygame.draw.polygon(tela, cor, pontos)
            pygame.draw.polygon(tela, ui.escurecer(cor, 80), pontos, 1)

        self.particulas.desenhar(tela)
        self.textos.desenhar(tela)

        # Nome da fase
        if self.estado == "jogando" and self.aviso > 0 and not self.morto:
            ui.desenhar_texto(tela, f"FASE {self.fase}", (LARGURA // 2, 440), 24, AMARELO, "center")
            ui.desenhar_texto(tela, self.nome_fase, (LARGURA // 2, 480), 16, (255, 170, 240), "center")
            if any(o.preso for o in self.ovos):
                ui.desenhar_texto(tela, "ESPAÇO ou CLIQUE para lançar", (LARGURA // 2, 520), 12,
                                  BRANCO, "center")

    def desenhar_hud(self, tela):
        caixa = pygame.Rect(12, 12, 420, 48)
        ui.painel(tela, caixa, (20, 24, 40), (255, 80, 200), 12, 3, sombra=False)
        ui.desenhar_texto(tela, f"PONTOS: {self.pontos}", (caixa.x + 16, caixa.centery), 14,
                          AMARELO, "midleft")
        rec = self.recorde()
        if rec is not None:
            ui.desenhar_texto(tela, f"RECORDE: {rec}", (caixa.x + 236, caixa.centery), 12,
                              (180, 200, 255), "midleft")

        # Fase no meio (com os poderes ativos do lado)
        caixa = pygame.Rect(444, 12, 300, 48)
        ui.painel(tela, caixa, (20, 24, 40), (255, 80, 200), 12, 3, sombra=False)
        ui.desenhar_texto(tela, f"FASE {self.fase}", (caixa.x + 16, caixa.centery), 14,
                          (255, 170, 240), "midleft")
        self._desenhar_poderes_ativos(tela, caixa.x + 126, caixa.y + 9)

        # Vidas (mini ovos) antes do botão de pausa
        caixa = pygame.Rect(0, 12, 44 + VIDAS_MAX * 30, 48)
        caixa.right = LARGURA - 76
        ui.painel(tela, caixa, (20, 24, 40), (255, 80, 200), 12, 3, sombra=False)
        for i in range(self.vidas):
            self.jogador.desenhar(tela, (caixa.x + 26 + i * 30, caixa.centery + 1), 24)

    def _desenhar_poderes_ativos(self, tela, x, y):
        """Cápsulas dos poderes ligados, com a barrinha do tempo que falta."""
        ativos = []
        for nome, resto, total in (("grande", self.grande, TEMPO_GRANDE), ("lento", self.lento, TEMPO_LENTO),
                                   ("fogo", self.fogo, TEMPO_FOGO)):
            if resto > 0:
                ativos.append((nome, PODERES[nome][1], resto / total))
        if self.grude > 0:
            ativos.append(("grude", f"G{self.grude}", None))
        for nome, rotulo, frac in ativos:
            cor = PODERES[nome][0]
            r = pygame.Rect(x, y, 38, 20)
            pygame.draw.rect(tela, ui.escurecer(cor, 90), r.inflate(2, 2), border_radius=10)
            pygame.draw.rect(tela, cor, r, border_radius=10)
            ui.desenhar_texto(tela, rotulo, (r.centerx, r.centery + 1), 10, BRANCO, "center")
            if frac is not None:
                pygame.draw.rect(tela, (60, 64, 90), (x + 2, y + 24, 34, 4))
                pygame.draw.rect(tela, cor, (x + 2, y + 24, int(34 * frac), 4))
            x += 43
