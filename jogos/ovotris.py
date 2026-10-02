import math
import random

import pygame

from settings import *
from core import ui
from jogos.base import MiniJogo

# ============================================================
# OVOTRIS
# ============================================================
# Peças feitas de ovinhos caem no galinheiro! O seu ovo pilota
# a peça que está caindo. Complete uma linha e os ovos racham:
# saem pintinhos voando. Quatro linhas de uma vez = OVOTRIS!

COLS = 10
LINHAS = 20
OCULTAS = 2                     # linhas escondidas acima do tabuleiro
TOTAL = LINHAS + OCULTAS
CEL = 32
X0 = 352
Y0 = 56

NIVEIS_INICIAIS = [1, 5, 10]
LINHAS_POR_NIVEL = 10
PONTOS_LINHAS = [0, 100, 300, 500, 800]

LOCK_DELAY = 0.5
LOCK_RESETS = 15
DAS = 0.17
ARR = 0.05
QUEDA_SUAVE = 0.05              # segundos por linha segurando ↓

DUR_PISCAR = 0.15               # linha completa pisca branco
DUR_RACHAR = 0.2                # depois os ovos racham
DUR_OVOTRIS = 1.6
DUR_DANCA = 3.0
DUR_FIM = 1.5

# Rotação com "wall kicks" simples
CHUTES = [(0, 0), (-1, 0), (1, 0), (-2, 0), (2, 0), (0, -1)]

# Peças: caixa, células (estado 0), cor
FORMAS = {
    "I": (4, [(0, 1), (1, 1), (2, 1), (3, 1)], (80, 210, 230)),
    "O": (2, [(0, 0), (1, 0), (0, 1), (1, 1)], (255, 220, 70)),
    "T": (3, [(1, 0), (0, 1), (1, 1), (2, 1)], (170, 100, 220)),
    "S": (3, [(1, 0), (2, 0), (0, 1), (1, 1)], (100, 210, 100)),
    "Z": (3, [(0, 0), (1, 0), (1, 1), (2, 1)], (240, 80, 80)),
    "J": (3, [(0, 0), (0, 1), (1, 1), (2, 1)], (70, 110, 230)),
    "L": (3, [(2, 0), (0, 1), (1, 1), (2, 1)], (255, 150, 50)),
}
TIPOS = "IOTSZJL"
CORES = {t: FORMAS[t][2] for t in TIPOS}


def _gerar_rotacoes():
    """Os 4 estados de cada peça (girando dentro da caixa, como no SRS)."""
    rot = {}
    for t, (n, cels, _) in FORMAS.items():
        estados = [sorted(cels)]
        for _ in range(3):
            estados.append(sorted((n - 1 - y, x) for x, y in estados[-1]))
        rot[t] = estados
    return rot


ROTACOES = _gerar_rotacoes()


def _centrais():
    """Índice da célula mais perto do centro da peça (onde vai o avatar)."""
    cent = {}
    for t, estados in ROTACOES.items():
        cent[t] = []
        for cels in estados:
            mx = sum(x for x, _ in cels) / 4
            my = sum(y for _, y in cels) / 4
            melhor = min(range(4), key=lambda i: ((cels[i][0] - mx) ** 2 + (cels[i][1] - my) ** 2, i))
            cent[t].append(melhor)
    return cent


CENTRAIS = _centrais()

TECLAS_ESQ = (pygame.K_LEFT, pygame.K_a)
TECLAS_DIR = (pygame.K_RIGHT, pygame.K_d)
TECLAS_BAIXO = (pygame.K_DOWN, pygame.K_s)
TECLAS_GIRAR = (pygame.K_UP, pygame.K_w, pygame.K_x)
TECLAS_GIRAR_ANTI = (pygame.K_z, pygame.K_q)
TECLAS_QUEDA = (pygame.K_SPACE,)
TECLAS_SEGURAR = (pygame.K_c, pygame.K_e, pygame.K_LSHIFT, pygame.K_RSHIFT)

# Cenário
COR_TABULEIRO = (25, 20, 35)
COR_GRADE = (40, 35, 55)
COR_PAINEL = (40, 30, 46)
COR_BORDA_PAINEL = (205, 165, 110)
ARCO_IRIS = [(255, 90, 90), (255, 170, 60), (255, 230, 70), (110, 220, 110),
             (80, 180, 255), (170, 120, 255), (255, 120, 200), (255, 230, 70)]

RETANGULO_SEGURAR = pygame.Rect(196, 76, 140, 118)
RETANGULO_DADOS = pygame.Rect(196, 208, 140, 204)
RETANGULO_PROXIMAS = pygame.Rect(688, 76, 140, 318)
PISO_Y = 668


def intervalo_queda(nivel):
    """Segundos por linha no nível."""
    return max(0.05, 0.8 * 0.85 ** (nivel - 1))


# ============================================================
# SPRITES DOS OVINHOS (feitos uma vez)
# ============================================================

_sprites = {}
S = 3                           # desenha 3x maior e reduz


def _pontos_ovo(cx, cy, rx, ry, n=40):
    pts = []
    for i in range(n):
        a = math.tau * i / n
        s = math.sin(a)
        pts.append((cx + rx * math.cos(a) * (1 + 0.08 * s), cy + ry * s))
    return pts


def _ovinho(cor, estilo, tam=CEL):
    """
    Um ovinho do tamanho da célula.
    estilo: normal / branco / rachado / cinza / fantasma
    """
    chave = (cor, estilo, tam)
    s = _sprites.get(chave)
    if s is not None:
        return s

    L = CEL * S
    sup = pygame.Surface((L, L), pygame.SRCALPHA)
    cx, cy = L / 2, L / 2 + S * 0.5
    rx, ry = 14 * S, 15 * S                 # elipse 28x30

    if estilo == "fantasma":
        pygame.draw.polygon(sup, (*cor, 55), _pontos_ovo(cx, cy, rx - S, ry - S))
        pygame.draw.polygon(sup, (*ui.clarear(cor, 40), 200), _pontos_ovo(cx, cy, rx - S, ry - S), 2 * S)
    else:
        if estilo == "branco":
            cor = (255, 255, 255)
        elif estilo == "cinza":
            cor = (112, 106, 124)
        contorno = ui.escurecer(cor, 80) if estilo != "branco" else (200, 200, 220)
        pygame.draw.polygon(sup, contorno, _pontos_ovo(cx, cy, rx, ry))
        pygame.draw.polygon(sup, cor, _pontos_ovo(cx, cy, rx - 2 * S, ry - 2 * S))
        # Sombrinha embaixo e brilho em cima
        pygame.draw.polygon(sup, ui.escurecer(cor, 26),
                            _pontos_ovo(cx + 2 * S, cy + 3 * S, rx - 6 * S, ry - 7 * S))
        pygame.draw.polygon(sup, cor, _pontos_ovo(cx - 1 * S, cy - 1 * S, rx - 5 * S, ry - 6 * S))
        brilho = pygame.Surface((L, L), pygame.SRCALPHA)
        pygame.draw.circle(brilho, (255, 255, 255, 120), (int(cx - 5 * S), int(cy - 6 * S)), int(4 * S))
        sup.blit(brilho, (0, 0))
        if estilo == "rachado":
            v = [(cx - 11 * S, cy - 3 * S), (cx - 6 * S, cy + 4 * S), (cx - 1 * S, cy - 4 * S),
                 (cx + 4 * S, cy + 4 * S), (cx + 10 * S, cy - 3 * S)]
            pygame.draw.lines(sup, (20, 14, 20), False, v, int(2.2 * S))
            pygame.draw.line(sup, (20, 14, 20), v[2], (cx - 1 * S, cy - 10 * S), int(1.6 * S))

    s = pygame.transform.smoothscale(sup, (tam, tam))
    if len(_sprites) > 200:
        _sprites.clear()
    _sprites[chave] = s
    return s


def _pintinho(tela, x, y, t, escala=1.0):
    """Pintinho voando (bolinha amarela com bico e asinha batendo)."""
    r = int(8 * escala)
    x, y = int(x), int(y)
    pygame.draw.circle(tela, (210, 160, 20), (x, y), r + 1)
    pygame.draw.circle(tela, (255, 222, 60), (x, y), r)
    asa = math.sin(t * 30)
    pygame.draw.ellipse(tela, (240, 190, 40), (x - r - 3, y - 2 - asa * 4 * escala, r, max(3, int(r * 0.9))))
    pygame.draw.ellipse(tela, (240, 190, 40), (x + 3, y - 2 - asa * 4 * escala, r, max(3, int(r * 0.9))))
    pygame.draw.circle(tela, (30, 20, 20), (x + r // 3, y - r // 3), max(1, r // 5))
    pygame.draw.polygon(tela, (255, 140, 30), [(x + r - 1, y - 1), (x + r + 5, y + 1), (x + r - 1, y + 3)])


# ============================================================
# PEÇA
# ============================================================

class Peca:

    def __init__(self, tipo):
        self.tipo = tipo
        self.rot = 0
        n = FORMAS[tipo][0]
        self.x = 4 if n == 2 else 3
        self.y = 0 if tipo == "I" else 1

    def celulas(self, rot=None, x=None, y=None):
        rot = self.rot if rot is None else rot
        x = self.x if x is None else x
        y = self.y if y is None else y
        return [(x + cx, y + cy) for cx, cy in ROTACOES[self.tipo][rot]]


class Ovotris(MiniJogo):

    ID = "ovotris"
    TITULO = "OVOTRIS"
    TITULO_CURTO = "OVOTRIS"
    DESCRICAO = "Peças de ovinhos caem no galinheiro! Complete linhas e os ovos chocam em pintinhos."
    COR = (170, 100, 220)
    INSTRUCOES = [
        "Encaixe as peças de ovinhos e complete LINHAS!",
        "Linha cheia: os ovos chocam e os pintinhos voam.",
        "4 linhas de uma vez = OVOTRIS! Guarde peças com C.",
        "Não deixe a pilha chegar lá em cima!",
        "←→ mover • ↑ girar • ↓ descer • ESPAÇO cair",
    ]
    OPCOES = ["FÁCIL (NÍVEL 1)", "MÉDIO (NÍVEL 5)", "DIFÍCIL (NÍVEL 10)"]

    MOEDAS_POR = 1000
    MOEDAS_MAX = 30

    # --------------------------------------------------------
    # CENÁRIO: galinheiro à noite
    # --------------------------------------------------------

    @classmethod
    def criar_fundo(cls, jogador):
        sup = pygame.Surface((LARGURA, ALTURA))
        rnd = random.Random(11)

        # Parede de tábuas
        sup.fill((120, 80, 50))
        largura_tabua = 52
        for i, x in enumerate(range(0, LARGURA, largura_tabua)):
            tom = (124, 83, 52) if i % 2 else (114, 76, 47)
            pygame.draw.rect(sup, tom, (x, 0, largura_tabua, ALTURA))
            pygame.draw.rect(sup, (90, 55, 30), (x, 0, 3, ALTURA))
            # veios
            for _ in range(4):
                vy = rnd.randrange(0, ALTURA)
                pygame.draw.line(sup, ui.escurecer(tom, 14), (x + rnd.randint(8, 20), vy),
                                 (x + rnd.randint(28, 46), vy + rnd.randint(30, 80)), 2)
            # nós da madeira
            if rnd.random() < 0.5:
                nx, ny = x + rnd.randint(14, 38), rnd.randrange(80, 600)
                pygame.draw.ellipse(sup, (92, 58, 34), (nx - 6, ny - 4, 12, 8))
            # pregos
            for py in (58, 380):
                pygame.draw.circle(sup, (60, 50, 50), (x + 12, py + 2), 3)
                pygame.draw.circle(sup, (170, 170, 180), (x + 12, py), 3)
                pygame.draw.circle(sup, (60, 50, 50), (x + largura_tabua - 12, py + 2), 3)
                pygame.draw.circle(sup, (170, 170, 180), (x + largura_tabua - 12, py), 3)
        # Vigas horizontais
        for vy in (28, 350):
            pygame.draw.rect(sup, (84, 52, 30), (0, vy - 4, LARGURA, 24))
            pygame.draw.rect(sup, (104, 66, 38), (0, vy - 4, LARGURA, 5))

        # Janela redonda com a lua
        jc, jr = (920, 250), 62
        ceu = pygame.Surface((jr * 2, jr * 2), pygame.SRCALPHA)
        for i in range(jr * 2):
            cor = ui.misturar((16, 18, 52), (50, 50, 110), i / (jr * 2))
            pygame.draw.line(ceu, cor, (0, i), (jr * 2, i))
        mascara = pygame.Surface((jr * 2, jr * 2), pygame.SRCALPHA)
        pygame.draw.circle(mascara, (255, 255, 255, 255), (jr, jr), jr)
        for _ in range(14):
            pygame.draw.circle(ceu, (230, 230, 255), (rnd.randrange(8, jr * 2 - 8), rnd.randrange(8, jr + 30)), 1)
        pygame.draw.circle(ceu, (240, 240, 210), (jr + 14, jr - 14), 24)
        pygame.draw.circle(ceu, (28, 30, 72), (jr + 26, jr - 22), 20)
        ceu.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        pygame.draw.circle(sup, (50, 30, 20), (jc[0] + 3, jc[1] + 5), jr + 12)
        pygame.draw.circle(sup, (150, 104, 64), jc, jr + 12)
        sup.blit(ceu, (jc[0] - jr, jc[1] - jr))
        pygame.draw.line(sup, (150, 104, 64), (jc[0] - jr, jc[1]), (jc[0] + jr, jc[1]), 6)
        pygame.draw.line(sup, (150, 104, 64), (jc[0], jc[1] - jr), (jc[0], jc[1] + jr), 6)
        pygame.draw.circle(sup, (100, 66, 38), jc, jr + 12, 3)

        # Poleiro com galinhas dormindo
        pygame.draw.rect(sup, (80, 50, 28), (846, 404, 160, 10), border_radius=4)
        pygame.draw.rect(sup, (80, 50, 28), (852, 404, 8, 60))
        pygame.draw.rect(sup, (80, 50, 28), (990, 404, 8, 60))
        for gx in (888, 956):
            _galinha(sup, gx, 404)

        # Lampião com luz quente
        lx, ly = 100, 150
        brilho = pygame.Surface((320, 320), pygame.SRCALPHA)
        for r in range(160, 0, -8):
            pygame.draw.circle(brilho, (255, 200, 110, int(26 * (1 - r / 160))), (160, 160), r)
        sup.blit(brilho, (lx - 160, ly - 160))
        pygame.draw.line(sup, (40, 30, 30), (lx, 28), (lx, ly - 26), 2)
        pygame.draw.rect(sup, (50, 40, 40), (lx - 14, ly - 28, 28, 8), border_radius=3)
        pygame.draw.rect(sup, (255, 214, 120), (lx - 11, ly - 20, 22, 30), border_radius=6)
        pygame.draw.rect(sup, (255, 245, 200), (lx - 4, ly - 12, 8, 14), border_radius=3)
        pygame.draw.rect(sup, (50, 40, 40), (lx - 11, ly - 20, 22, 30), 2, border_radius=6)
        pygame.draw.rect(sup, (50, 40, 40), (lx - 14, ly + 10, 28, 7), border_radius=3)

        # Palha no chão
        pygame.draw.rect(sup, (200, 168, 92), (0, PISO_Y, LARGURA, ALTURA - PISO_Y))
        for _ in range(700):
            x = rnd.randrange(-10, LARGURA)
            y = rnd.randrange(PISO_Y - 8, ALTURA)
            ang = rnd.uniform(-0.5, 0.5) + (math.pi if rnd.random() < 0.5 else 0)
            comp = rnd.randint(8, 18)
            cor = rnd.choice([(220, 190, 110), (240, 214, 140), (190, 156, 82)])
            pygame.draw.line(sup, cor, (x, y), (x + math.cos(ang) * comp, y + math.sin(ang) * comp * 0.4), 2)

        # Ninho com ovinhos no canto
        nx, ny = 64, PISO_Y + 6
        for cor, dx in (((250, 245, 230), -14), ((200, 150, 100), 0), ((250, 245, 230), 14)):
            pygame.draw.ellipse(sup, ui.escurecer(cor, 60), (nx + dx - 10, ny - 26, 20, 26))
            pygame.draw.ellipse(sup, cor, (nx + dx - 8, ny - 24, 16, 22))
        pygame.draw.ellipse(sup, (150, 110, 50), (nx - 34, ny - 12, 68, 24))
        for i in range(12):
            pygame.draw.arc(sup, (200, 160, 80), (nx - 34 + i * 5, ny - 12, 12, 20), 0, math.pi, 2)

        # Placa de controles
        placa = pygame.Rect(700, 474, 304, 168)
        prego = (placa.centerx, placa.y - 34)
        pygame.draw.line(sup, (60, 40, 30), prego, (placa.x + 50, placa.y + 2), 2)
        pygame.draw.line(sup, (60, 40, 30), prego, (placa.right - 50, placa.y + 2), 2)
        pygame.draw.circle(sup, (60, 50, 50), (prego[0], prego[1] + 2), 4)
        pygame.draw.circle(sup, (170, 170, 180), prego, 4)
        pygame.draw.rect(sup, (50, 32, 20), placa.move(4, 6), border_radius=10)
        pygame.draw.rect(sup, (150, 104, 64), placa, border_radius=10)
        pygame.draw.rect(sup, (100, 66, 38), placa, 3, border_radius=10)
        linhas = [("←→ / A D", "MOVER"), ("↑ / W", "GIRAR"), ("Z / Q", "GIRAR AO CONTRÁRIO"),
                  ("↓ / S", "DESCER"), ("ESPAÇO", "CAIR DE VEZ"), ("C / E", "GUARDAR")]
        for i, (tecla, acao) in enumerate(linhas):
            y = placa.y + 18 + i * 24
            ui.desenhar_texto(sup, tecla, (placa.x + 14, y), 10, (255, 236, 170), "topleft", False)
            ui.desenhar_texto(sup, acao, (placa.x + 104, y), 10, (60, 34, 20), "topleft", False)

        # Tabuleiro com moldura de madeira
        tab = pygame.Rect(X0, Y0, COLS * CEL, LINHAS * CEL)
        sombra = pygame.Surface(tab.inflate(40, 40).size, pygame.SRCALPHA)
        pygame.draw.rect(sombra, (0, 0, 0, 90), sombra.get_rect(), border_radius=14)
        sup.blit(sombra, (tab.x - 14, tab.y - 12))
        pygame.draw.rect(sup, (84, 52, 30), tab.inflate(24, 24), border_radius=10)
        pygame.draw.rect(sup, (150, 104, 64), tab.inflate(18, 18), border_radius=8)
        pygame.draw.rect(sup, (60, 36, 20), tab.inflate(6, 6), border_radius=4)
        pygame.draw.rect(sup, COR_TABULEIRO, tab)
        for c in range(1, COLS):
            pygame.draw.line(sup, COR_GRADE, (X0 + c * CEL, Y0), (X0 + c * CEL, tab.bottom - 1))
        for l in range(1, LINHAS):
            pygame.draw.line(sup, COR_GRADE, (X0, Y0 + l * CEL), (tab.right - 1, Y0 + l * CEL))

        # Painéis laterais
        for r, titulo in ((RETANGULO_SEGURAR, "GUARDADA"), (RETANGULO_PROXIMAS, "PRÓXIMAS"),
                          (RETANGULO_DADOS, None)):
            ui.painel(sup, r, COR_PAINEL, COR_BORDA_PAINEL, 14, 3)
            if titulo:
                ui.desenhar_texto(sup, titulo, (r.centerx, r.y + 12), 10, AMARELO, "midtop")
        return sup

    @classmethod
    def desenhar_icone(cls, sup, jogador):
        w, h = sup.get_size()
        cel = max(12, h // 7)
        cols, linhas = 6, 5
        x0 = w // 2 - cols * cel // 2 - 34
        y0 = (h - linhas * cel) // 2 + 4
        pygame.draw.rect(sup, (84, 52, 30), (x0 - 5, y0 - 5, cols * cel + 10, linhas * cel + 10), border_radius=6)
        pygame.draw.rect(sup, COR_TABULEIRO, (x0, y0, cols * cel, linhas * cel))
        pilha = ["", "", "    O ", "ZZ LIJ", "SZZLTJ"]
        for l, linha in enumerate(pilha):
            for c, ch in enumerate(linha):
                if ch in CORES:
                    sup.blit(_ovinho(CORES[ch], "normal", cel), (x0 + c * cel, y0 + l * cel))
        # Peça T caindo
        for c, l in [(1, 0), (2, 0), (3, 0), (2, 1)]:
            sup.blit(_ovinho(CORES["T"], "normal", cel), (x0 + c * cel, y0 + l * cel))
        # O ovo do jogador torcendo do lado, com pintinhos voando
        jogador.desenhar(sup, (x0 + cols * cel + 44, h // 2 + 10), h * 0.42)
        for i, (dx, dy) in enumerate(((20, -34), (58, -40), (74, -8))):
            _pintinho(sup, x0 + cols * cel + dx, h // 2 + dy, i * 0.4, 1.0)

    # --------------------------------------------------------
    # PARTIDA
    # --------------------------------------------------------

    def reiniciar(self):
        self.grade = [[None] * COLS for _ in range(TOTAL)]
        self.nivel_inicial = NIVEIS_INICIAIS[self.opcao]
        self.nivel = self.nivel_inicial
        self.linhas = 0
        self.ovotris = 0
        self.saco = []
        self.fila = []
        self._encher_fila()
        self.guardada = None
        self.pode_guardar = True
        self.peca = None

        self.fase = "caindo"            # caindo / limpando / fim_jogo
        self.t_fase = 0.0
        self.linhas_cheias = []
        self.acumulado = 0.0
        self.lock_t = 0.0
        self.resets = 0
        self.y_max = 0

        # Teclas seguradas (DAS / ARR / queda suave)
        self.horizontais = []           # direções seguradas, a última manda
        self.das_t = 0.0
        self.arr_t = 0.0
        self.suave = False

        # Efeitos
        self.pintinhos = []
        self.t_ovotris = -10.0
        self.t_danca = -10.0
        self.t_pouso = -10.0
        self.relogio = 0.0

        self._nova_peca()

    def _encher_fila(self):
        while len(self.fila) < 7:
            if not self.saco:
                self.saco = list(TIPOS)
                random.shuffle(self.saco)
            self.fila.append(self.saco.pop())

    def _nova_peca(self, tipo=None):
        """Coloca a próxima peça no topo. Devolve False se não coube (fim)."""
        if tipo is None:
            tipo = self.fila.pop(0)
            self._encher_fila()
        p = Peca(tipo)
        self.peca = p
        self.acumulado = 0.0
        self.lock_t = 0.0
        self.resets = 0
        if not self._cabe(p.celulas()):
            self._perder()
            return False
        # Já desce uma linha para aparecer inteira
        if self._cabe(p.celulas(y=p.y + 1)):
            p.y += 1
        self.y_max = p.y
        return True

    def _cabe(self, celulas):
        for c, l in celulas:
            if c < 0 or c >= COLS or l >= TOTAL:
                return False
            if l >= 0 and self.grade[l][c] is not None:
                return False
        return True

    def _no_chao(self):
        p = self.peca
        return not self._cabe(p.celulas(y=p.y + 1))

    # --------------------------------------------------------
    # CONTROLES
    # --------------------------------------------------------

    def evento(self, e):
        # Solta as teclas em qualquer estado (para não "grudar" na pausa)
        if e.type == pygame.KEYUP:
            self._soltar(e.key)
        elif e.type == pygame.WINDOWFOCUSLOST:
            self._limpar_teclas()
        super().evento(e)

    def pausar(self):
        super().pausar()
        self._limpar_teclas()

    def _limpar_teclas(self):
        self.horizontais = []
        self.suave = False
        self.das_t = self.arr_t = 0.0

    def _soltar(self, key):
        d = -1 if key in TECLAS_ESQ else 1 if key in TECLAS_DIR else 0
        if d:
            ativa = self.horizontais[-1] if self.horizontais else 0
            if d in self.horizontais:
                self.horizontais.remove(d)
            nova = self.horizontais[-1] if self.horizontais else 0
            if nova != ativa:
                self.das_t = self.arr_t = 0.0
        elif key in TECLAS_BAIXO:
            self.suave = False

    def evento_jogo(self, e):
        if e.type != pygame.KEYDOWN:
            return
        k = e.key
        if k in TECLAS_ESQ or k in TECLAS_DIR:
            d = -1 if k in TECLAS_ESQ else 1
            if d in self.horizontais:
                self.horizontais.remove(d)
            self.horizontais.append(d)
            self.das_t = self.arr_t = 0.0
            if self.fase == "caindo":
                self._mover(d)
            return
        if k in TECLAS_BAIXO:
            self.suave = True
            if self.fase == "caindo":
                self._descer(suave=True)
                self.acumulado = 0.0
            return
        if self.fase != "caindo":
            return
        if k in TECLAS_GIRAR:
            self._girar(1)
        elif k in TECLAS_GIRAR_ANTI:
            self._girar(-1)
        elif k in TECLAS_QUEDA:
            self._queda_rapida()
        elif k in TECLAS_SEGURAR:
            self._guardar()

    # --------------------------------------------------------
    # MOVIMENTOS
    # --------------------------------------------------------

    def _depois_de_mexer(self):
        """Movimento/rotação que deu certo: renova o lock delay (limitado)."""
        if self._no_chao() and self.resets < LOCK_RESETS:
            self.lock_t = 0.0
            self.resets += 1

    def _mover(self, d):
        p = self.peca
        if self._cabe(p.celulas(x=p.x + d)):
            p.x += d
            self._depois_de_mexer()
            return True
        return False

    def _girar(self, sentido):
        p = self.peca
        if p.tipo == "O":
            return
        nova = (p.rot + sentido) % 4
        for dx, dy in CHUTES:
            if self._cabe(p.celulas(rot=nova, x=p.x + dx, y=p.y + dy)):
                p.rot, p.x, p.y = nova, p.x + dx, p.y + dy
                self.som("virar", 0.35)
                self._depois_de_mexer()
                return True
        return False

    def _descer(self, suave=False):
        p = self.peca
        if self._cabe(p.celulas(y=p.y + 1)):
            p.y += 1
            if suave:
                self.pontos += 1
            if p.y > self.y_max:
                self.y_max = p.y
                self.resets = 0
                self.lock_t = 0.0
            return True
        return False

    def _linha_fantasma(self):
        p = self.peca
        y = p.y
        while self._cabe(p.celulas(y=y + 1)):
            y += 1
        return y

    def _queda_rapida(self):
        p = self.peca
        destino = self._linha_fantasma()
        distancia = destino - p.y
        p.y = destino
        self.pontos += 2 * distancia
        self.tremer(0.1)
        self.som("bater", 0.6)
        # Poeira na base da peça
        base = max(l for _, l in p.celulas())
        for c, l in p.celulas():
            if l == base:
                x, y = self._px(c, l)
                self.particulas.explodir((x + CEL / 2, y + CEL), [(220, 190, 110), (170, 140, 90), BRANCO],
                                         4, 120, 0.4, (2, 4), 200)
        self._travar()

    def _guardar(self):
        if not self.pode_guardar:
            self.som("erro", 0.3)
            return
        self.pode_guardar = False
        tipo = self.peca.tipo
        self.som("selecionar", 0.5)
        if self.guardada is None:
            self.guardada = tipo
            self._nova_peca()
        else:
            troca, self.guardada = self.guardada, tipo
            self._nova_peca(troca)

    def _travar(self):
        """Grava a peça no tabuleiro e confere as linhas."""
        p = self.peca
        celulas = p.celulas()
        for c, l in celulas:
            if l >= 0:
                self.grade[l][c] = p.tipo
        self.t_pouso = self.relogio
        self.pode_guardar = True

        # Travou (mesmo que um pedaço) acima do tabuleiro: fim
        if any(l < OCULTAS for _, l in celulas):
            self.peca = None
            self._perder()
            return

        cheias = [l for l in range(TOTAL) if all(v is not None for v in self.grade[l])]
        if cheias:
            self.peca = None
            self.linhas_cheias = cheias
            self.fase = "limpando"
            self.t_fase = 0.0
            self.som("acerto" if len(cheias) < 4 else "vencer", 0.7)
        else:
            self.som("bater", 0.3)
            self._nova_peca()

    def _limpar_linhas(self):
        """Tira as linhas cheias, solta os pintinhos e conta os pontos."""
        n = len(self.linhas_cheias)
        for l in self.linhas_cheias:
            for c in range(COLS):
                x, y = self._px(c, l)
                self.pintinhos.append([x + CEL / 2, y + CEL / 2,
                                       random.uniform(-70, 70), random.uniform(-260, -150),
                                       random.uniform(0, 3), 0.0])
        restantes = [linha for i, linha in enumerate(self.grade) if i not in self.linhas_cheias]
        self.grade = [[None] * COLS for _ in range(n)] + restantes
        if len(self.pintinhos) > 80:
            self.pintinhos = self.pintinhos[-80:]

        ganho = PONTOS_LINHAS[n] * self.nivel
        self.pontos += ganho
        self.linhas += n
        meio_y = Y0 + (sum(self.linhas_cheias) / n - OCULTAS) * CEL + CEL / 2
        self.textos.adicionar(f"+{ganho}", (X0 + COLS * CEL / 2, meio_y), AMARELO, 16)

        if n == 4:
            self.ovotris += 1
            self.t_ovotris = self.relogio
            self.t_danca = self.relogio
            self.tremer(0.3)
            self.particulas.explodir((X0 + COLS * CEL / 2, meio_y), ARCO_IRIS + [self.jogador.cor],
                                     50, 360, 1.1)
        else:
            self.particulas.explodir((X0 + COLS * CEL / 2, meio_y), [AMARELO, BRANCO, (255, 240, 170)],
                                     10 * n, 220, 0.7)

        novo_nivel = self.nivel_inicial + self.linhas // LINHAS_POR_NIVEL
        if novo_nivel > self.nivel:
            self.nivel = novo_nivel
            self.som("vencer", 0.5)
            self.textos.adicionar(f"NÍVEL {self.nivel}!", (X0 + COLS * CEL / 2, Y0 + 220), (140, 230, 255), 20)
            if self.relogio - self.t_danca > DUR_DANCA:
                self.t_danca = self.relogio - DUR_DANCA * 0.5
        self.linhas_cheias = []

    def _perder(self):
        self.fase = "fim_jogo"
        self.t_fase = 0.0
        self.tremer(0.35)
        self.som("perder", 0.6)

    # --------------------------------------------------------
    # LÓGICA
    # --------------------------------------------------------

    def atualizar_jogo(self, dt):
        self.relogio += dt
        self._atualizar_pintinhos(dt)

        if self.fase == "limpando":
            self.t_fase += dt
            if self.t_fase >= DUR_PISCAR + DUR_RACHAR:
                self._limpar_linhas()
                self.fase = "caindo"
                self._nova_peca()
            return

        if self.fase == "fim_jogo":
            self.t_fase += dt
            if self.t_fase >= DUR_FIM:
                self.terminar(linhas=[f"PONTOS: {self.pontos}",
                                      f"LINHAS: {self.linhas}",
                                      f"NÍVEL: {self.nivel}" + (f"  •  OVOTRIS: {self.ovotris}"
                                                                 if self.ovotris else "")])
            return

        # ---- Movimento lateral segurando a tecla (DAS / ARR)
        if self.horizontais:
            d = self.horizontais[-1]
            self.das_t += dt
            if self.das_t >= DAS:
                self.arr_t += dt
                while self.arr_t >= ARR and self.fase == "caindo":
                    self.arr_t -= ARR
                    if not self._mover(d):
                        self.arr_t = 0.0
                        break

        # ---- Gravidade (mais rápida segurando ↓)
        intervalo = intervalo_queda(self.nivel)
        if self.suave:
            intervalo = min(intervalo, QUEDA_SUAVE)
        self.acumulado += dt
        while self.acumulado >= intervalo:
            self.acumulado -= intervalo
            if not self._descer(suave=self.suave):
                self.acumulado = 0.0
                break

        # ---- Lock delay
        if self._no_chao():
            self.lock_t += dt
            if self.lock_t >= LOCK_DELAY:
                self._travar()
        else:
            self.lock_t = 0.0

    def _atualizar_pintinhos(self, dt):
        vivos = []
        for p in self.pintinhos:
            p[5] += dt
            p[0] += (p[2] + math.sin(p[5] * 6 + p[4]) * 60) * dt
            p[1] += p[3] * dt
            p[3] -= 40 * dt
            if p[5] < 1.6 and p[1] > -20:
                vivos.append(p)
        self.pintinhos = vivos

    # --------------------------------------------------------
    # DESENHO
    # --------------------------------------------------------

    @staticmethod
    def _px(c, l):
        return X0 + c * CEL, Y0 + (l - OCULTAS) * CEL

    def desenhar_jogo(self, tela):
        tela.blit(self.fundo(self.jogador), (0, 0))

        # Ovos parados
        cinzas = int(self.t_fase / 0.05) if self.fase == "fim_jogo" else 0
        for l in range(OCULTAS, TOTAL):
            linha = self.grade[l]
            y = Y0 + (l - OCULTAS) * CEL
            estilo = "normal"
            if self.fase == "limpando" and l in self.linhas_cheias:
                estilo = "branco" if self.t_fase < DUR_PISCAR else "rachado"
            elif self.fase == "fim_jogo" and TOTAL - l <= cinzas:
                estilo = "cinza"
            for c in range(COLS):
                t = linha[c]
                if t is not None:
                    tela.blit(_ovinho(CORES[t], estilo), (X0 + c * CEL, y))

        # Peça fantasma e peça ativa
        if self.peca is not None and self.fase == "caindo":
            p = self.peca
            fy = self._linha_fantasma()
            if fy != p.y:
                fantasma = _ovinho(CORES[p.tipo], "fantasma")
                for c, l in p.celulas(y=fy):
                    if l >= OCULTAS:
                        tela.blit(fantasma, self._px(c, l))
            sprite = _ovinho(CORES[p.tipo], "normal")
            celulas = p.celulas()
            for c, l in celulas:
                if l >= OCULTAS:
                    tela.blit(sprite, self._px(c, l))
            # O ovo do jogador pilota a peça (na célula central)
            c, l = celulas[CENTRAIS[p.tipo][p.rot]]
            if l >= OCULTAS:
                x, y = self._px(c, l)
                balanco = math.sin(self.relogio * 6) * 6 if self.lock_t == 0 else 0
                self.jogador.desenhar(tela, (x + CEL / 2, y + CEL / 2 + 1), 26, angulo=balanco)

        self._desenhar_paineis(tela)
        self._desenhar_avatar(tela)

        for p in self.pintinhos:
            _pintinho(tela, p[0], p[1], p[5] + p[4])

        self.particulas.desenhar(tela)
        self.textos.desenhar(tela)
        self._desenhar_ovotris(tela)

        if self.fase == "fim_jogo" and self.t_fase > 0.5:
            ui.desenhar_texto(tela, "FIM DA PILHA!", (X0 + COLS * CEL // 2, Y0 + LINHAS * CEL // 2), 20,
                              (255, 130, 130), "center")

    def _desenhar_peca_mini(self, tela, tipo, centro, cel):
        cels = ROTACOES[tipo][0]
        xs = [x for x, _ in cels]
        ys = [y for _, y in cels]
        w = (max(xs) - min(xs) + 1) * cel
        h = (max(ys) - min(ys) + 1) * cel
        x0 = centro[0] - w / 2 - min(xs) * cel
        y0 = centro[1] - h / 2 - min(ys) * cel
        sprite = _ovinho(CORES[tipo], "normal", cel)
        for x, y in cels:
            tela.blit(sprite, (int(x0 + x * cel), int(y0 + y * cel)))

    def _desenhar_paineis(self, tela):
        # Peça guardada
        r = RETANGULO_SEGURAR
        if self.guardada:
            self._desenhar_peca_mini(tela, self.guardada, (r.centerx, r.y + 70), 26)
            if not self.pode_guardar:
                veu = pygame.Surface((r.w - 16, r.h - 40), pygame.SRCALPHA)
                veu.fill((40, 30, 46, 150))
                tela.blit(veu, (r.x + 8, r.y + 32))
        else:
            ui.desenhar_texto(tela, "C / E", (r.centerx, r.y + 70), 12, (150, 130, 150), "center")

        # Próximas 3
        r = RETANGULO_PROXIMAS
        for i, tipo in enumerate(self.fila[:3]):
            cy = r.y + 78 + i * 88
            cel = 26 if i == 0 else 22
            if i > 0:
                pygame.draw.line(tela, (80, 64, 84), (r.x + 20, cy - 44), (r.right - 20, cy - 44), 2)
            self._desenhar_peca_mini(tela, tipo, (r.centerx, cy), cel)

        # Nível / linhas / recorde
        r = RETANGULO_DADOS
        rec = self.recorde()
        itens = [("NÍVEL", str(self.nivel), (140, 230, 255)),
                 ("LINHAS", str(self.linhas), BRANCO),
                 ("RECORDE", str(rec) if rec is not None else "--", AMARELO)]
        for i, (rotulo, valor, cor) in enumerate(itens):
            y = r.y + 16 + i * 64
            ui.desenhar_texto(tela, rotulo, (r.centerx, y), 10, (210, 190, 170), "midtop")
            ui.desenhar_texto(tela, valor, (r.centerx, y + 20), 16, cor, "midtop")

    def _desenhar_avatar(self, tela):
        """O seu ovo no chão do galinheiro, torcendo (e dançando no OVOTRIS!)."""
        cx, base = 190, PISO_Y + 8
        altura = 96
        dt_danca = self.relogio - self.t_danca
        ang = 0.0
        esc_y = 1.0
        if 0 <= dt_danca < DUR_DANCA:
            pulo = abs(math.sin(dt_danca * 9)) * 40
            ang = math.sin(dt_danca * 9) * 18
        else:
            pulo = abs(math.sin(self.tempo * 2.2)) * 6
            if self.fase == "fim_jogo":
                ang = math.sin(self.tempo * 6) * 14
                pulo = 0
        # Achatadinha quando pousa uma peça
        dp = self.relogio - self.t_pouso
        if 0 <= dp < 0.15:
            esc_y = 1 - 0.12 * math.sin(math.pi * dp / 0.15)
        largura_sombra = 70 - pulo * 0.6
        pygame.draw.ellipse(tela, (150, 118, 60), (cx - largura_sombra / 2, base - 8, largura_sombra, 14))
        img = self.jogador.avatar(altura)
        if esc_y < 0.999:
            img = pygame.transform.smoothscale(img, (int(img.get_width() * (2 - esc_y)),
                                                     int(img.get_height() * esc_y)))
        if ang:
            img = pygame.transform.rotate(img, ang)
        centro_y = base - altura / 2 * esc_y - pulo
        tela.blit(img, img.get_rect(center=(cx, int(centro_y))))
        # Notas musicais na dança
        if 0 <= dt_danca < DUR_DANCA:
            for i in range(3):
                fase = (dt_danca * 1.2 + i / 3) % 1
                x = cx - 70 + i * 70 + math.sin(fase * 6) * 8
                y = base - 130 - fase * 70
                cor = ARCO_IRIS[(i * 2 + int(dt_danca * 4)) % len(ARCO_IRIS)]
                pygame.draw.circle(tela, cor, (int(x), int(y)), 6)
                pygame.draw.line(tela, cor, (x + 5, y), (x + 5, y - 20), 3)
                pygame.draw.line(tela, cor, (x + 5, y - 20), (x + 13, y - 14), 3)

    def _desenhar_ovotris(self, tela):
        t = self.relogio - self.t_ovotris
        if not 0 <= t < DUR_OVOTRIS:
            return
        palavra = "OVOTRIS!"
        tam = 32
        larg = sum(ui.texto(ch, tam).get_width() for ch in palavra)
        x = X0 + COLS * CEL / 2 - larg / 2
        y0 = Y0 + 200
        entrada = min(1.0, t / 0.25)
        for i, ch in enumerate(palavra):
            cor = ARCO_IRIS[(i + int(t * 10)) % len(ARCO_IRIS)]
            sup = ui.texto(ch, tam, cor)
            dy = math.sin(t * 10 + i * 0.7) * 10 - (1 - entrada) * 60
            tela.blit(sup, (int(x), int(y0 + dy)))
            x += sup.get_width()

    def desenhar_hud(self, tela):
        caixa = pygame.Rect(12, 12, 324, 48)
        ui.painel(tela, caixa, (20, 24, 40), BRANCO, 12, 3, sombra=False)
        ui.desenhar_texto(tela, f"PONTOS: {self.pontos}", (caixa.x + 16, caixa.centery + 1), 14,
                          AMARELO, "midleft")


def _galinha(sup, x, poleiro_y):
    """Galinha branca dormindo no poleiro."""
    corpo = pygame.Rect(0, 0, 50, 36)
    corpo.midbottom = (x, poleiro_y + 4)
    pygame.draw.ellipse(sup, (120, 110, 110), corpo.inflate(4, 4))
    pygame.draw.ellipse(sup, (245, 240, 232), corpo)
    # rabinho
    pygame.draw.polygon(sup, (245, 240, 232), [(corpo.left + 4, corpo.centery - 4),
                                               (corpo.left - 10, corpo.top - 2),
                                               (corpo.left + 10, corpo.top + 6)])
    # cabeça
    cab = (corpo.right - 8, corpo.top + 4)
    pygame.draw.circle(sup, (120, 110, 110), cab, 13)
    pygame.draw.circle(sup, (245, 240, 232), cab, 11)
    pygame.draw.circle(sup, (220, 50, 50), (cab[0] - 2, cab[1] - 11), 4)
    pygame.draw.circle(sup, (220, 50, 50), (cab[0] + 3, cab[1] - 12), 4)
    pygame.draw.polygon(sup, (255, 160, 40), [(cab[0] + 9, cab[1]), (cab[0] + 16, cab[1] + 3), (cab[0] + 9, cab[1] + 5)])
    pygame.draw.arc(sup, (60, 50, 50), (cab[0] - 1, cab[1] - 4, 8, 6), math.pi, math.tau, 2)
    # asa
    pygame.draw.arc(sup, (200, 190, 180), (corpo.x + 12, corpo.y + 8, 26, 20), math.pi * 1.1, math.pi * 1.9, 2)
    # zzz
    ui.desenhar_texto(sup, "z", (cab[0] + 14, cab[1] - 22), 10, (200, 210, 255), "center", False)
    ui.desenhar_texto(sup, "z", (cab[0] + 22, cab[1] - 34), 12, (200, 210, 255), "center", False)
