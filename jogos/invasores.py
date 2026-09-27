import math
import random

import pygame

from settings import *
from core import ui
from jogos.base import MiniJogo

# ============================================================
# INVASORES DA COZINHA
# ============================================================
# Garfos, batedores e panelas marcham para cozinhar o ovo! O seu
# ovo fica em cima da bancada e se defende atirando PIPOCA pela
# cabeça. Os NINHOS de palha seguram as gotas de óleo e a
# FRIGIDEIRA VOADORA às vezes solta um presente (TIRO TRIPLO ou
# ESCUDO). Cada onda nova começa um pouquinho mais baixa.

# Cenário
BANCADA_Y = 672                 # tampo da bancada (onde o ovo pisa)

# Ovo
OVO_Y = 640                     # centro do ovo
ALTURA_OVO = 64
MEIA_LARG = ALTURA_OVO * 0.45
X_MIN, X_MAX = 60, LARGURA - 60
VEL_OVO = 380
VIDAS = 3
TEMPO_CONGELA = 0.8             # a cozinha "congela" quando o ovo é atingido
TEMPO_INVENCIVEL = 1.6

# Tiros
VEL_PIPOCA = 700
MAX_PIPOCAS = 2
RECARGA = 0.2
VEL_GOTA = 220
MAX_GOTAS = 3
RAIO_PIPOCA = 8
RAIO_GOTA = 6

# Formação
COLS = 10
LINHAS = 5
ESP_X = 64
ESP_Y = 52
Y_FORMACAO = 130                # centro da primeira linha
X_FORMACAO = LARGURA // 2 - (COLS - 1) * ESP_X // 2
DESCIDA = 24
DESCIDAS_EXTRAS = 5             # cada onda começa 24 px mais baixa (até 5 vezes)
MARGEM = 18
LINHA_PERIGO = 600              # se a formação chegar aqui, cozinhou o ovo!
VEL_MAX = 240                   # teto da velocidade da formação (px/s)
PASSO_ANIM = 16                 # px andados por "passo" (troca o quadro)
MEIA_W, MEIA_H = 22, 19         # metade da caixa de colisão de um inimigo
TIPOS_LINHA = ["garfo", "batedor", "batedor", "panela", "panela"]
PONTOS_TIPO = {"garfo": 30, "batedor": 20, "panela": 10}

# Ninhos de palha (escudos)
BLOCO = 10
FORMA_NINHO = [
    ".######.",
    "########",
    "########",
    "########",
    "###..###",
    "##....##",
]
NINHO_W = len(FORMA_NINHO[0])
NINHO_H = len(FORMA_NINHO)
NINHO_Y = 516
NINHOS_X = [128, 384, 640, 896]     # centro de cada ninho

# Frigideira voadora
FRIGIDEIRA_Y = 88
VEL_FRIGIDEIRA = 160
VALORES_FRIGIDEIRA = (100, 150, 300)
CHANCE_PRESENTE = 0.6
VEL_PRESENTE = 150
TEMPO_TRIPLO = 8.0

# Cores
PRATA = (200, 200, 215)
PRATA_CLARA = (238, 238, 248)
CONTORNO = (80, 80, 100)
PANELA = (60, 60, 70)
OLEO = (240, 200, 50)

TECLAS_ESQ = (pygame.K_LEFT, pygame.K_a)
TECLAS_DIR = (pygame.K_RIGHT, pygame.K_d)
TECLAS_TIRO = (pygame.K_SPACE, pygame.K_w, pygame.K_UP, pygame.K_RETURN, pygame.K_KP_ENTER)


def _velocidade(vivos, total, onda):
    """
    A formação acelera quando sobra pouca gente (e a cada onda).
    O design pede 40 + 300 x (1 - vivos/50); limitamos em VEL_MAX para
    o último talher ainda ser acertável por uma criança.
    """
    return min(VEL_MAX, 40 + 300 * (1 - vivos / max(1, total))) + 8 * min(onda - 1, 6)


def _intervalo_tiro(onda):
    return max(0.45, 1.25 - 0.1 * (onda - 1))


# ============================================================
# DESENHOS (feitos uma vez só, com cache)
# ============================================================

_sprites = {}
Z = 2                           # desenha 2x maior e diminui (fica suave)
TAM_INIMIGO = (52, 46)


def _rosto(s, cx, cy, e=1.0, sobrancelha=(30, 30, 45)):
    """Olhinhos bravos-fofos (olhando para baixo, para o ovo)."""
    for lado in (-1, 1):
        ex = cx + lado * 9 * e
        pygame.draw.circle(s, (30, 30, 40), (ex, cy), 7.5 * e)
        pygame.draw.circle(s, BRANCO, (ex, cy), 6 * e)
        pygame.draw.circle(s, (20, 20, 30), (ex - lado * 1.2 * e, cy + 1.8 * e), 3.4 * e)
        pygame.draw.circle(s, BRANCO, (ex - lado * 2 * e, cy), 1.2 * e)
        # Sobrancelha brava (inclinada para dentro)
        pygame.draw.line(s, sobrancelha, (cx + lado * 17 * e, cy - 11 * e),
                         (cx + lado * 4 * e, cy - 6 * e), max(2, int(3.4 * e)))
    # Bochechas rosadas (bravos, mas fofos)
    for lado in (-1, 1):
        pygame.draw.ellipse(s, (240, 140, 160), (cx + lado * 16 * e - 4 * e, cy + 6 * e, 8 * e, 5 * e))
    # Boquinha aberta
    pygame.draw.ellipse(s, (90, 20, 40), (cx - 5 * e, cy + 9 * e, 10 * e, 7 * e))


def _braco(s, ombro, mao, cor=PRATA):
    pygame.draw.line(s, CONTORNO, ombro, mao, 9)
    pygame.draw.circle(s, CONTORNO, mao, 7)
    pygame.draw.line(s, cor, ombro, mao, 5)
    pygame.draw.circle(s, cor, mao, 5)


def _garfo(quadro):
    s = pygame.Surface((TAM_INIMIGO[0] * Z, TAM_INIMIGO[1] * Z), pygame.SRCALPHA)
    dentes = [pygame.Rect(29 + i * 13, 4, 8, 32) for i in range(4)]
    ponte = pygame.Rect(26, 28, 52, 14)
    corpo = pygame.Rect(28, 38, 48, 38)
    cabo = pygame.Rect(45, 70, 14, 20)

    # Braços (alternam para cima e para baixo a cada passo)
    my = 34 if quadro == 0 else 72
    _braco(s, (32, 54), (10, my))
    _braco(s, (72, 54), (94, 106 - my))

    for r in dentes + [ponte, corpo, cabo]:
        pygame.draw.rect(s, CONTORNO, r.inflate(6, 6), border_radius=6)
    for r in dentes + [ponte, corpo, cabo]:
        pygame.draw.rect(s, PRATA, r, border_radius=4)
    for r in dentes:
        pygame.draw.line(s, PRATA_CLARA, (r.x + 2, r.y + 4), (r.x + 2, r.bottom - 2), 2)
    pygame.draw.rect(s, PRATA_CLARA, (corpo.x + 5, corpo.y + 4, 6, 18), border_radius=3)
    _rosto(s, 52, 56, 1.0)
    return s


def _batedor(quadro):
    s = pygame.Surface((TAM_INIMIGO[0] * Z, TAM_INIMIGO[1] * Z), pygame.SRCALPHA)
    larguras = (18, 40, 62, 84) if quadro == 0 else (12, 34, 56, 78)

    # Braços saindo do cabo
    my = 50 if quadro == 0 else 88
    _braco(s, (44, 74), (14, my))
    _braco(s, (60, 74), (90, 138 - my))

    # 4 arcos de arame
    for w in larguras:
        pygame.draw.ellipse(s, CONTORNO, (52 - w // 2 - 2, 2, w + 4, 70), 7)
    for w in larguras:
        pygame.draw.ellipse(s, PRATA, (52 - w // 2, 4, w, 66), 3)

    # Cabo com anel
    cabo = pygame.Rect(43, 62, 18, 28)
    pygame.draw.rect(s, CONTORNO, cabo.inflate(6, 6), border_radius=6)
    pygame.draw.rect(s, PRATA, cabo, border_radius=5)
    pygame.draw.rect(s, PRATA_CLARA, (cabo.x + 3, cabo.y + 4, 4, 18), border_radius=2)
    pygame.draw.line(s, CONTORNO, (cabo.x, cabo.y + 8), (cabo.right - 1, cabo.y + 8), 2)

    # Cabecinha no meio do batedor
    pygame.draw.circle(s, CONTORNO, (52, 36), 21)
    pygame.draw.circle(s, PRATA, (52, 36), 18)
    pygame.draw.circle(s, PRATA_CLARA, (44, 28), 5)
    _rosto(s, 52, 36, 0.8)
    return s


def _panela(quadro):
    s = pygame.Surface((TAM_INIMIGO[0] * Z, TAM_INIMIGO[1] * Z), pygame.SRCALPHA)
    borda = (160, 160, 185)

    # Alças (sobem e descem a cada passo)
    ay = 40 if quadro == 0 else 54
    for lado in (-1, 1):
        x = 2 if lado < 0 else 86
        alca = pygame.Rect(x, ay if lado < 0 else 94 - ay, 16, 9)
        pygame.draw.rect(s, borda, alca.inflate(4, 4), border_radius=4)
        pygame.draw.rect(s, (90, 90, 105), alca, border_radius=3)

    corpo = pygame.Rect(16, 34, 72, 50)
    pygame.draw.rect(s, borda, corpo.inflate(6, 6), border_radius=12)
    pygame.draw.rect(s, PANELA, corpo, border_radius=10)
    pygame.draw.rect(s, (85, 85, 98), (corpo.x + 6, corpo.y + 8, 6, 30), border_radius=3)

    # Borda da boca e tampa
    aba = pygame.Rect(10, 28, 84, 10)
    pygame.draw.rect(s, borda, aba.inflate(4, 4), border_radius=5)
    pygame.draw.rect(s, (110, 110, 128), aba, border_radius=4)
    tampa = pygame.Rect(22, 12, 60, 22)
    pygame.draw.ellipse(s, borda, tampa.inflate(4, 4))
    pygame.draw.ellipse(s, (95, 95, 112), tampa)
    pygame.draw.ellipse(s, (130, 130, 150), (tampa.x + 8, tampa.y + 4, 22, 7))
    pygame.draw.circle(s, borda, (52, 11), 7)
    pygame.draw.circle(s, (70, 70, 85), (52, 11), 5)

    _rosto(s, 52, 60, 1.05, sobrancelha=(215, 215, 230))
    return s


def _frigideira(quadro):
    """Frigideira voadora (virada para a direita), com asinhas."""
    s = pygame.Surface((100 * Z, 50 * Z), pygame.SRCALPHA)
    # Asinhas batendo
    for lado in (-1, 1):
        cx = 76 + lado * 34
        if quadro == 0:
            asa = [(cx, 44), (cx + lado * 30, 8), (cx + lado * 40, 30)]
        else:
            asa = [(cx, 44), (cx + lado * 36, 56), (cx + lado * 40, 76)]
        pygame.draw.polygon(s, BRANCO, asa)
        pygame.draw.polygon(s, (150, 160, 190), asa, 3)
    # Cabo de madeira
    cabo = pygame.Rect(126, 44, 70, 16)
    pygame.draw.rect(s, (60, 35, 20), cabo.inflate(6, 6), border_radius=8)
    pygame.draw.rect(s, (150, 95, 55), cabo, border_radius=7)
    pygame.draw.circle(s, (60, 35, 20), (184, 52), 4)
    # Panela redonda (vista de lado, meio inclinada)
    corpo = pygame.Rect(20, 26, 112, 60)
    pygame.draw.ellipse(s, (20, 20, 28), corpo.inflate(8, 8))
    pygame.draw.ellipse(s, (55, 55, 68), corpo)
    pygame.draw.ellipse(s, (95, 95, 115), (corpo.x + 10, corpo.y + 6, corpo.w - 20, 22))
    pygame.draw.ellipse(s, (140, 140, 160), (corpo.x + 20, corpo.y + 9, 34, 8))
    _rosto(s, 76, 62, 1.0, sobrancelha=(220, 220, 235))
    return pygame.transform.smoothscale(s, (100, 50))


def _pipoca():
    s = pygame.Surface((26 * Z, 26 * Z), pygame.SRCALPHA)
    c = 26
    bolinhas = ((-9, 3, 11), (9, 3, 11), (0, -8, 12), (-4, 10, 10), (6, 11, 9))
    for dx, dy, r in bolinhas:
        pygame.draw.circle(s, (200, 160, 80), (c + dx, c + dy), r + 2)
    for dx, dy, r in bolinhas:
        pygame.draw.circle(s, (255, 248, 222), (c + dx, c + dy), r)
    pygame.draw.circle(s, (250, 205, 90), (c + 3, c + 11), 6)
    pygame.draw.circle(s, BRANCO, (c - 4, c - 11), 5)
    return pygame.transform.smoothscale(s, (26, 26))


def _gota():
    s = pygame.Surface((16 * Z, 22 * Z), pygame.SRCALPHA)
    pygame.draw.polygon(s, (150, 110, 20), [(16, 0), (4, 26), (28, 26)])
    pygame.draw.circle(s, (150, 110, 20), (16, 30), 13)
    pygame.draw.polygon(s, OLEO, [(16, 4), (7, 26), (25, 26)])
    pygame.draw.circle(s, OLEO, (16, 30), 10)
    pygame.draw.ellipse(s, (255, 250, 200), (9, 24, 6, 9))
    return pygame.transform.smoothscale(s, (16, 22))


def _presente(tipo):
    s = pygame.Surface((34 * Z, 34 * Z), pygame.SRCALPHA)
    c = (34, 34)
    cor = (255, 150, 50) if tipo == "triplo" else (80, 170, 255)
    pygame.draw.circle(s, BRANCO, c, 32)
    pygame.draw.circle(s, cor, c, 27)
    pygame.draw.circle(s, ui.clarear(cor, 70), (24, 22), 8)
    if tipo == "triplo":
        pip = pygame.transform.smoothscale(_pipoca(), (24, 24))
        for dx, dy in ((-14, 6), (14, 6), (0, -10)):
            s.blit(pip, pip.get_rect(center=(c[0] + dx, c[1] + dy)))
    else:
        pygame.draw.circle(s, BRANCO, c, 17, 5)
        pygame.draw.ellipse(s, BRANCO, (26, 22, 16, 22))
        pygame.draw.ellipse(s, (80, 170, 255), (30, 26, 8, 14))
    return pygame.transform.smoothscale(s, (34, 34))


def _escudo():
    s = pygame.Surface((100, 100), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (120, 200, 255, 60), (4, 2, 92, 96))
    pygame.draw.ellipse(s, (170, 225, 255, 200), (4, 2, 92, 96), 4)
    pygame.draw.arc(s, (255, 255, 255, 220), (14, 10, 72, 80), 1.9, 2.9, 4)
    return s


_BLOCOS = []


def _blocos_palha():
    """3 variações do bloquinho de palha 10x10."""
    if not _BLOCOS:
        rnd = random.Random(5)
        for base in ((222, 184, 96), (206, 166, 80), (232, 198, 116)):
            b = pygame.Surface((BLOCO, BLOCO))
            b.fill(base)
            for _ in range(3):
                x = rnd.randrange(BLOCO)
                pygame.draw.line(b, ui.escurecer(base, 50), (x, 0),
                                 (x + rnd.randint(-4, 4), BLOCO), 1)
            pygame.draw.line(b, ui.clarear(base, 30), (0, rnd.randrange(BLOCO)),
                             (BLOCO, rnd.randrange(BLOCO)), 1)
            _BLOCOS.append(b)
    return _BLOCOS


def _sprite(nome, quadro=0):
    chave = (nome, quadro)
    s = _sprites.get(chave)
    if s is None:
        if nome in ("garfo", "batedor", "panela"):
            grande = {"garfo": _garfo, "batedor": _batedor, "panela": _panela}[nome](quadro)
            s = pygame.transform.smoothscale(grande, TAM_INIMIGO)
        elif nome == "frigideira":
            s = _frigideira(quadro)
        elif nome == "pipoca":
            s = _pipoca()
        elif nome == "gota":
            s = _gota()
        elif nome == "escudo":
            s = _escudo()
        else:
            s = _presente(nome)
        _sprites[chave] = s
    return s


# ============================================================
# PEÇAS DO JOGO
# ============================================================

class Inimigo:

    def __init__(self, col, lin):
        self.col = col
        self.lin = lin
        self.tipo = TIPOS_LINHA[lin]
        self.vivo = True


class Tiro:

    def __init__(self, x, y, vx, vy):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.giro = random.uniform(-400, 400)


# ============================================================
# JOGO
# ============================================================

class Invasores(MiniJogo):

    ID = "invasores"
    TITULO = "INVASORES DA COZINHA"
    TITULO_CURTO = "INVASORES"
    DESCRICAO = "Garfos, batedores e panelas marcham para cozinhar o ovo! Defenda-se atirando PIPOCA."
    COR = (90, 110, 190)
    INSTRUCOES = [
        "Os talheres querem cozinhar o seu ovo!",
        "Atire PIPOCA: GARFO 30, BATEDOR 20, PANELA 10.",
        "Os NINHOS de palha seguram as gotas de óleo.",
        "Acerte a FRIGIDEIRA VOADORA: ela solta presentes!",
        "SETAS/A D movem • ESPAÇO/W/↑ atira • MOUSE",
    ]
    OPCOES = None
    MENOR_MELHOR = False
    ROTULO_PONTOS = "PONTOS"
    CONTAGEM = True

    TRILHA = dict(bpm=118, tom="F", escala="menor", lead="serra", envelope="normal",
                  baixo="walking", onda_baixo="quadrada", acomp="pad", onda_acomp="triangulo",
                  bateria="marcha", energia=0.6, eco=(0.18, 0.2))

    MOEDAS_POR = 200
    MOEDAS_MAX = 30

    # --------------------------------------------------------
    # CENÁRIO: cozinha à noite
    # --------------------------------------------------------

    @classmethod
    def criar_fundo(cls, jogador):
        sup = pygame.Surface((LARGURA, ALTURA))
        rnd = random.Random(18)

        # Azulejos em xadrez (escuros para os inimigos aparecerem)
        lado = 48
        for lin in range(ALTURA // lado + 1):
            for col in range(LARGURA // lado + 1):
                r = pygame.Rect(col * lado, lin * lado, lado, lado)
                cor = (60, 70, 110) if (lin + col) % 2 == 0 else (50, 60, 95)
                pygame.draw.rect(sup, cor, r)
                pygame.draw.rect(sup, (42, 50, 82), r, 1)

        # Janela com a lua (canto superior direito)
        jan = pygame.Rect(790, 150, 170, 150)
        sup.set_clip(jan)
        sup.blit(ui.gradiente(jan.w, jan.h, (14, 18, 48), (40, 44, 96)), jan.topleft)
        for _ in range(26):
            x, y = jan.x + rnd.randrange(jan.w), jan.y + rnd.randrange(jan.h)
            pygame.draw.circle(sup, (230, 230, 255), (x, y), rnd.choice((1, 1, 2)))
        lua = (jan.x + 110, jan.y + 52)
        pygame.draw.circle(sup, (70, 70, 110), lua, 34)
        pygame.draw.circle(sup, (250, 245, 210), lua, 28)
        pygame.draw.circle(sup, (225, 220, 180), (lua[0] - 8, lua[1] + 6), 6)
        pygame.draw.circle(sup, (225, 220, 180), (lua[0] + 10, lua[1] - 8), 4)
        pygame.draw.ellipse(sup, (20, 26, 60), (jan.x - 30, jan.bottom - 36, 130, 70))
        pygame.draw.ellipse(sup, (26, 32, 70), (jan.x + 70, jan.bottom - 30, 150, 70))
        sup.set_clip(None)
        pygame.draw.rect(sup, (160, 130, 100), jan, 10)
        pygame.draw.rect(sup, (100, 76, 56), jan, 3)
        pygame.draw.line(sup, (160, 130, 100), (jan.centerx, jan.y), (jan.centerx, jan.bottom), 8)
        pygame.draw.line(sup, (160, 130, 100), (jan.x, jan.centery), (jan.right, jan.centery), 8)
        pygame.draw.rect(sup, (170, 140, 110), (jan.x - 14, jan.bottom - 4, jan.w + 28, 12),
                         border_radius=4)

        # Prateleira com potes (à esquerda)
        prat = pygame.Rect(40, 250, 200, 10)
        pygame.draw.rect(sup, (110, 80, 56), prat, border_radius=3)
        for i, cor in enumerate(((150, 110, 70), (120, 70, 70), (90, 120, 90), (130, 130, 150))):
            pote = pygame.Rect(54 + i * 46, 214, 32, 36)
            pygame.draw.rect(sup, cor, pote, border_radius=6)
            pygame.draw.rect(sup, (36, 36, 56), pote, 2, border_radius=6)
            pygame.draw.rect(sup, (100, 76, 56), (pote.x + 3, pote.y - 7, 26, 9), border_radius=3)
            pygame.draw.rect(sup, ui.clarear(cor, 40), (pote.x + 6, pote.y + 7, 4, 18), border_radius=2)

        # Luminária pendurada com cone de luz amarelada
        cone = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        pygame.draw.polygon(cone, (255, 240, 180, 30), [(482, 66), (542, 66), (800, BANCADA_Y),
                                                        (224, BANCADA_Y)])
        pygame.draw.polygon(cone, (255, 240, 180, 18), [(496, 66), (528, 66), (680, BANCADA_Y),
                                                        (344, BANCADA_Y)])
        sup.blit(cone, (0, 0))
        pygame.draw.line(sup, (30, 30, 40), (512, 0), (512, 40), 3)
        pygame.draw.polygon(sup, (30, 30, 40), [(494, 38), (530, 38), (548, 68), (476, 68)])
        pygame.draw.polygon(sup, (200, 80, 70), [(496, 40), (528, 40), (544, 66), (480, 66)])
        pygame.draw.line(sup, (240, 130, 110), (500, 44), (490, 62), 3)
        pygame.draw.circle(sup, (255, 245, 200), (512, 69), 7)

        # Bancada na base
        pygame.draw.rect(sup, (140, 100, 70), (0, BANCADA_Y, LARGURA, ALTURA - BANCADA_Y))
        pygame.draw.rect(sup, (170, 130, 90), (0, BANCADA_Y, LARGURA, 8))
        pygame.draw.line(sup, (110, 76, 50), (0, BANCADA_Y + 8), (LARGURA, BANCADA_Y + 8), 2)
        for _ in range(30):
            x = rnd.randrange(LARGURA)
            y = rnd.randrange(BANCADA_Y + 14, ALTURA - 4)
            pygame.draw.line(sup, (126, 90, 62), (x, y), (x + rnd.randint(20, 60), y), 1)
        for x in range(0, LARGURA, 256):
            pygame.draw.line(sup, (110, 76, 50), (x, BANCADA_Y + 10), (x, ALTURA), 2)
        return sup

    @classmethod
    def desenhar_icone(cls, sup, jogador):
        w, h = sup.get_size()
        for i, tipo in enumerate(("garfo", "batedor", "panela")):
            s = pygame.transform.smoothscale(_sprite(tipo, i % 2), (40, 35))
            sup.blit(s, s.get_rect(center=(int(w * (0.25 + i * 0.25)), int(h * 0.24))))
        jogador.desenhar(sup, (w // 2, int(h * 0.76)), h * 0.34)
        p = _sprite("pipoca")
        sup.blit(p, p.get_rect(center=(w // 2, int(h * 0.48))))

    # --------------------------------------------------------
    # PARTIDA
    # --------------------------------------------------------

    def reiniciar(self):
        self.x = LARGURA / 2
        self.vx = 0.0
        self.alvo_mouse = None
        self.teclas = set()
        self.mouse_apertado = False
        self.recarga = 0.0
        self.squash = 0.0

        self.vidas = VIDAS
        self.onda = 0
        self.pipocas = []
        self.gotas = []
        self.presentes = []
        self.triplo = 0.0
        self.escudo = False
        self.congelado = 0.0
        self.invencivel = 0.0
        self.morto = False
        self.tempo_morto = 0.0
        self.motivo = ""
        self.abatidos = 0

        self.frigideira = None
        self.proxima_frigideira = random.uniform(20, 30)

        self._montar_ninhos()
        self._nova_onda(entrada=False)

    def _montar_ninhos(self):
        self.blocos = {}
        blocos = _blocos_palha()
        for i in range(len(NINHOS_X)):
            for by, linha in enumerate(FORMA_NINHO):
                for bx, ch in enumerate(linha):
                    if ch == "#":
                        self.blocos[(i, bx, by)] = blocos[(bx * 7 + by * 3 + i) % 3]

    def _nova_onda(self, entrada=True):
        self.onda += 1
        self.inimigos = [Inimigo(c, l) for l in range(LINHAS) for c in range(COLS)]
        self.form_x = float(X_FORMACAO)
        self.form_y = float(Y_FORMACAO + DESCIDA * min(self.onda - 1, DESCIDAS_EXTRAS))
        self.direcao = 1
        self.quadro = 0
        self.andado = 0.0
        self.som_passo = 0.0
        self.tiro_inimigo = 1.5
        self.entrada = 1.0 if entrada else 0.0      # tempo da formação chegando
        self.aviso_onda = 1.6 if entrada else 0.0

    # --------------------------------------------------------
    # CONTROLES
    # --------------------------------------------------------

    def evento(self, e):
        # Acompanha teclas e botão do mouse em qualquer estado
        if e.type == pygame.KEYDOWN:
            self.teclas.add(e.key)
        elif e.type == pygame.KEYUP:
            self.teclas.discard(e.key)
        elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
            self.mouse_apertado = False
        elif e.type == pygame.WINDOWFOCUSLOST:
            self.teclas.clear()
            self.mouse_apertado = False
        super().evento(e)

    def evento_jogo(self, e):
        if e.type == pygame.MOUSEMOTION:
            if not self.botao_pausa.collidepoint(e.pos):
                self.alvo_mouse = max(X_MIN, min(X_MAX, e.pos[0]))
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.mouse_apertado = True
            self._atirar()
        elif e.type == pygame.KEYDOWN:
            if e.key in TECLAS_ESQ + TECLAS_DIR:
                self.alvo_mouse = None
            elif e.key in TECLAS_TIRO:
                self._atirar()

    def _atirar(self):
        if self.morto or self.congelado > 0 or self.recarga > 0:
            return
        limite = MAX_PIPOCAS * (3 if self.triplo > 0 else 1)
        if len(self.pipocas) >= limite:
            return
        topo = OVO_Y - ALTURA_OVO / 2 - 4
        self.pipocas.append(Tiro(self.x, topo, 0, -VEL_PIPOCA))
        if self.triplo > 0:
            for vx in (-170, 170):
                self.pipocas.append(Tiro(self.x, topo, vx, -VEL_PIPOCA))
        self.recarga = RECARGA
        self.squash = 1.0
        self.som("pulo", 0.35)
        self.particulas.explodir((self.x, topo), [(255, 248, 222), (250, 205, 90)], 5, 120, 0.3, (2, 4))

    # --------------------------------------------------------
    # LÓGICA
    # --------------------------------------------------------

    def atualizar_jogo(self, dt):
        self.recarga = max(0.0, self.recarga - dt)
        self.squash = max(0.0, self.squash - dt / 0.12)
        self.aviso_onda = max(0.0, self.aviso_onda - dt)

        if self.morto:
            self.tempo_morto += dt
            if self.tempo_morto > 1.4:
                self.terminar(linhas=[self.motivo, f"PONTOS: {self.pontos}", f"ONDA: {self.onda}"])
            return

        # Hit-stop: a cozinha congela um pouquinho quando o ovo é atingido
        if self.congelado > 0:
            self.congelado -= dt
            return

        self.invencivel = max(0.0, self.invencivel - dt)
        if self.triplo > 0:
            self.triplo = max(0.0, self.triplo - dt)
            if self.triplo == 0:
                self.textos.adicionar("FIM DO TIRO TRIPLO", (self.x, OVO_Y - 70), (200, 210, 255), 10)

        self._mover_ovo(dt)
        if (any(t in self.teclas for t in TECLAS_TIRO) or self.mouse_apertado):
            self._atirar()

        self._mover_pipocas(dt)
        if self.entrada > 0:
            self.entrada = max(0.0, self.entrada - dt)
        else:
            self._mover_formacao(dt)
            self._inimigos_atiram(dt)
        self._mover_gotas(dt)
        self._frigideira(dt)
        self._mover_presentes(dt)

        # Onda limpa!
        if not self.morto and not any(i.vivo for i in self.inimigos):
            self.textos.adicionar("ONDA LIMPA!", (LARGURA // 2, 300), AMARELO, 24)
            self.som("vencer", 0.6)
            self.gotas.clear()
            self._montar_ninhos()
            self._nova_onda()

    def _mover_ovo(self, dt):
        direcao = 0
        if any(t in self.teclas for t in TECLAS_ESQ):
            direcao -= 1
        if any(t in self.teclas for t in TECLAS_DIR):
            direcao += 1
        if direcao:
            self.alvo_mouse = None
            self.vx = direcao * VEL_OVO
        elif self.alvo_mouse is not None:
            dist = self.alvo_mouse - self.x
            self.vx = math.copysign(min(VEL_OVO, abs(dist) * 12), dist)
        else:
            self.vx = 0.0
        self.x = max(X_MIN, min(X_MAX, self.x + self.vx * dt))

    def _mover_pipocas(self, dt):
        vivas = []
        for p in self.pipocas:
            acertou = False
            # Anda em passinhos (não atravessa bloco nem inimigo)
            passos = 3
            for _ in range(passos):
                p.x += p.vx * dt / passos
                p.y += p.vy * dt / passos
                if self._pipoca_acerta(p):
                    acertou = True
                    break
            if acertou or p.y < 30 or p.x < -20 or p.x > LARGURA + 20:
                continue
            vivas.append(p)
        self.pipocas = vivas

    def _pipoca_acerta(self, p):
        # Frigideira voadora
        f = self.frigideira
        if f and abs(p.x - f["x"]) < 44 and abs(p.y - FRIGIDEIRA_Y) < 22:
            self._acertar_frigideira()
            return True

        # Inimigos
        if self.entrada <= 0:
            for ini in self.inimigos:
                if not ini.vivo:
                    continue
                ix, iy = self._pos(ini)
                if abs(p.x - ix) < MEIA_W + 3 and abs(p.y - iy) < MEIA_H + 3:
                    self._abater(ini, ix, iy)
                    return True

        # Ninhos
        if self._bater_ninho(p.x, p.y - RAIO_PIPOCA):
            self.particulas.explodir((p.x, p.y - 6), [(222, 184, 96), (255, 248, 222)], 5, 100, 0.35, (2, 4))
            return True
        return False

    def _pos(self, ini):
        return (self.form_x + ini.col * ESP_X, self.form_y + ini.lin * ESP_Y)

    def _abater(self, ini, x, y):
        ini.vivo = False
        self.abatidos += 1
        valor = PONTOS_TIPO[ini.tipo]
        self.pontos += valor
        self.textos.adicionar(f"+{valor}", (x, y - 24), AMARELO if valor >= 30 else BRANCO, 14)
        cores = [PANELA, (30, 30, 40), (130, 130, 150)] if ini.tipo == "panela" \
            else [PRATA, PRATA_CLARA, (150, 150, 170)]
        self.particulas.explodir((x, y), cores + [(255, 248, 222), (250, 205, 90)], 16, 230, 0.6)
        self.particulas.explodir((x, y), [BRANCO, (255, 250, 200)], 6, 120, 0.3, (2, 4), gravidade=0)
        self.som("acerto", 0.55)

    def _bater_ninho(self, px, py, gota=False):
        """Se o ponto cai num bloco de palha, destrói o bloco."""
        if not (NINHO_Y <= py < NINHO_Y + NINHO_H * BLOCO):
            return False
        for i, cx in enumerate(NINHOS_X):
            x0 = cx - NINHO_W * BLOCO // 2
            if x0 <= px < x0 + NINHO_W * BLOCO:
                bx = int((px - x0) // BLOCO)
                by = int((py - NINHO_Y) // BLOCO)
                if (i, bx, by) in self.blocos:
                    del self.blocos[(i, bx, by)]
                    # O óleo desmancha um pouquinho mais a palha
                    if gota and random.random() < 0.5:
                        self.blocos.pop((i, bx + random.choice((-1, 1)), by), None)
                    return True
        return False

    def _limites(self):
        vivos = [i for i in self.inimigos if i.vivo]
        if not vivos:
            return None
        cmin = min(i.col for i in vivos)
        cmax = max(i.col for i in vivos)
        lmax = max(i.lin for i in vivos)
        return (self.form_x + cmin * ESP_X - MEIA_W, self.form_x + cmax * ESP_X + MEIA_W,
                self.form_y + lmax * ESP_Y + MEIA_H)

    def _mover_formacao(self, dt):
        vivos = sum(1 for i in self.inimigos if i.vivo)
        if vivos == 0:
            return
        vel = _velocidade(vivos, len(self.inimigos), self.onda)
        dx = vel * dt * self.direcao
        self.form_x += dx
        self.andado += abs(dx)
        self.som_passo -= dt

        # Passo: troca o quadro da animação e "pisa" (som baixinho)
        if self.andado >= PASSO_ANIM:
            self.andado -= PASSO_ANIM
            self.quadro = 1 - self.quadro
            if self.som_passo <= 0:
                self.som("bater", 0.18)
                self.som_passo = 0.12

        esq, dir_, baixo = self._limites()
        if dir_ > LARGURA - MARGEM or esq < MARGEM:
            corr = (LARGURA - MARGEM - dir_) if dir_ > LARGURA - MARGEM else (MARGEM - esq)
            self.form_x += corr
            self.direcao *= -1
            self.form_y += DESCIDA
            baixo += DESCIDA

        # Desmancha a palha que a formação encostar
        if baixo > NINHO_Y:
            for ini in self.inimigos:
                if ini.vivo:
                    ix, iy = self._pos(ini)
                    if iy + MEIA_H > NINHO_Y:
                        self._raspar_ninhos(ix, iy)

        if baixo >= LINHA_PERIGO:
            self._morrer("A COZINHA FOI INVADIDA!")

    def _raspar_ninhos(self, ix, iy):
        for chave in list(self.blocos):
            i, bx, by = chave
            x = NINHOS_X[i] - NINHO_W * BLOCO // 2 + bx * BLOCO
            y = NINHO_Y + by * BLOCO
            if x + BLOCO > ix - MEIA_W and x < ix + MEIA_W and y + BLOCO > iy - MEIA_H and y < iy + MEIA_H:
                del self.blocos[chave]

    def _inimigos_atiram(self, dt):
        self.tiro_inimigo -= dt
        if self.tiro_inimigo > 0 or len(self.gotas) >= MAX_GOTAS:
            return
        self.tiro_inimigo = _intervalo_tiro(self.onda) * random.uniform(0.6, 1.25)

        # Só o de baixo de cada coluna atira
        de_baixo = {}
        for ini in self.inimigos:
            if ini.vivo and (ini.col not in de_baixo or ini.lin > de_baixo[ini.col].lin):
                de_baixo[ini.col] = ini
        if not de_baixo:
            return
        atiradores = list(de_baixo.values())
        if random.random() < 0.4:
            atirador = min(atiradores, key=lambda i: abs(self._pos(i)[0] - self.x))
        else:
            atirador = random.choice(atiradores)
        x, y = self._pos(atirador)
        self.gotas.append(Tiro(x, y + MEIA_H, 0, VEL_GOTA))

    def _mover_gotas(self, dt):
        vivas = []
        for g in self.gotas:
            g.y += g.vy * dt
            if self._bater_ninho(g.x, g.y + RAIO_GOTA, gota=True):
                self.particulas.explodir((g.x, g.y + 4), [OLEO, (222, 184, 96)], 6, 100, 0.35, (2, 4))
                continue
            if self._acerta_ovo(g.x, g.y, RAIO_GOTA):
                self._atingido(g)
                continue
            if g.y > BANCADA_Y + 4:
                self.particulas.explodir((g.x, BANCADA_Y), [OLEO, (255, 250, 200)], 5, 90, 0.3, (2, 3))
                continue
            vivas.append(g)
        self.gotas = vivas

    def _acerta_ovo(self, x, y, raio):
        a = MEIA_LARG + raio * 0.5
        b = ALTURA_OVO / 2 + raio * 0.5
        return ((x - self.x) / a) ** 2 + ((y - OVO_Y) / b) ** 2 < 1.0

    def _atingido(self, gota):
        if self.invencivel > 0:
            return
        if self.escudo:
            self.escudo = False
            self.invencivel = 0.6
            self.som("boing", 0.7)
            self.textos.adicionar("ESCUDO!", (self.x, OVO_Y - 70), (150, 210, 255), 14)
            self.particulas.explodir((self.x, OVO_Y - 20), [(170, 225, 255), BRANCO], 18, 200, 0.5)
            return

        self.vidas -= 1
        self.som("erro" if self.vidas > 0 else "explosao", 0.8)
        self.tremer(0.3)
        self.particulas.explodir((gota.x, gota.y), [OLEO, (255, 250, 200), (200, 150, 30)], 22, 240, 0.6)
        self.gotas.clear()
        if self.vidas <= 0:
            self.vidas = 0
            self._morrer("O OVO FOI FRITO!")
        else:
            self.congelado = TEMPO_CONGELA
            self.invencivel = TEMPO_INVENCIVEL
            self.textos.adicionar("ENGORDUROU!", (self.x, OVO_Y - 70), OLEO, 14)

    def _morrer(self, motivo):
        if self.morto:
            return
        self.morto = True
        self.motivo = motivo
        self.tempo_morto = 0.0
        self.tremer(0.4)
        self.som("explosao", 0.7)
        self.particulas.explodir((self.x, OVO_Y), [self.jogador.cor, BRANCO, OLEO], 30, 260)

    # --------------------------------------------------------
    # FRIGIDEIRA E PRESENTES
    # --------------------------------------------------------

    def _frigideira(self, dt):
        f = self.frigideira
        if f is None:
            self.proxima_frigideira -= dt
            if self.proxima_frigideira <= 0 and self.entrada <= 0:
                lado = random.choice((-1, 1))
                self.frigideira = {"x": -60.0 if lado > 0 else LARGURA + 60.0, "dir": lado}
                self.som("asa", 0.5)
            return
        f["x"] += f["dir"] * VEL_FRIGIDEIRA * dt
        if f["x"] < -80 or f["x"] > LARGURA + 80:
            self.frigideira = None
            self.proxima_frigideira = random.uniform(20, 30)

    def _acertar_frigideira(self):
        f = self.frigideira
        valor = random.choice(VALORES_FRIGIDEIRA)
        self.pontos += valor
        self.textos.adicionar(f"+{valor}", (f["x"], FRIGIDEIRA_Y + 30), LARANJA, 18)
        self.particulas.explodir((f["x"], FRIGIDEIRA_Y), [(55, 55, 68), (150, 95, 55), BRANCO, AMARELO],
                                 26, 260, 0.7)
        self.som("moeda")
        self.tremer(0.1)
        if random.random() < CHANCE_PRESENTE:
            tipo = random.choice(("triplo", "escudo"))
            self.presentes.append({"x": max(X_MIN, min(X_MAX, f["x"])), "y": FRIGIDEIRA_Y + 10.0,
                                   "tipo": tipo})
        self.frigideira = None
        self.proxima_frigideira = random.uniform(20, 30)

    def _mover_presentes(self, dt):
        vivos = []
        for p in self.presentes:
            p["y"] += VEL_PRESENTE * dt
            if self._acerta_ovo(p["x"], p["y"], 14):
                self._pegar_presente(p)
                continue
            if p["y"] < BANCADA_Y:
                vivos.append(p)
        self.presentes = vivos

    def _pegar_presente(self, p):
        self.som("moeda", 0.8)
        pos = (self.x, OVO_Y - 70)
        if p["tipo"] == "triplo":
            self.triplo = TEMPO_TRIPLO
            self.textos.adicionar("TIRO TRIPLO!", pos, LARANJA, 16)
        else:
            self.escudo = True
            self.textos.adicionar("ESCUDO!", pos, (150, 210, 255), 16)
        self.particulas.explodir(pos, [self.jogador.cor, AMARELO, BRANCO], 20, 200, 0.6)

    # --------------------------------------------------------
    # DESENHO
    # --------------------------------------------------------

    def desenhar_jogo(self, tela):
        tela.blit(self.fundo(self.jogador), (0, 0))
        t = self.tempo

        # Ninhos de palha
        for (i, bx, by), bloco in self.blocos.items():
            tela.blit(bloco, (NINHOS_X[i] - NINHO_W * BLOCO // 2 + bx * BLOCO, NINHO_Y + by * BLOCO))

        # Formação (chega caindo do alto no começo da onda)
        desloc = -420 * self.entrada * self.entrada
        for ini in self.inimigos:
            if ini.vivo:
                x, y = self._pos(ini)
                s = _sprite(ini.tipo, self.quadro)
                tela.blit(s, s.get_rect(center=(round(x), round(y + desloc))))

        # Frigideira voadora
        f = self.frigideira
        if f:
            s = _sprite("frigideira", int(t * 8) % 2)
            if f["dir"] < 0:
                s = pygame.transform.flip(s, True, False)
            dy = math.sin(t * 5) * 5
            tela.blit(s, s.get_rect(center=(round(f["x"]), round(FRIGIDEIRA_Y + dy))))

        # Presentes caindo (piscando)
        for p in self.presentes:
            s = _sprite(p["tipo"])
            tela.blit(s, s.get_rect(center=(round(p["x"]), round(p["y"]))))
            if int(t * 6) % 2 == 0:
                ui.estrela(tela, (int(p["x"] + 16), int(p["y"] - 16)), 5, BRANCO)

        self._desenhar_ovo(tela)

        # Tiros
        pip = _sprite("pipoca")
        for p in self.pipocas:
            s = pygame.transform.rotate(pip, (t * p.giro) % 360)
            tela.blit(s, s.get_rect(center=(round(p.x), round(p.y))))
        gota = _sprite("gota")
        for g in self.gotas:
            tela.blit(gota, gota.get_rect(center=(round(g.x), round(g.y))))

        self.particulas.desenhar(tela)
        self.textos.desenhar(tela)

        # Aviso de onda nova
        if self.aviso_onda > 0 and self.estado == "jogando":
            ui.desenhar_texto(tela, f"ONDA {self.onda}!", (LARGURA // 2, 360), 32, AMARELO, "center")

        # Tiro triplo: barrinha no canto de baixo
        if self.triplo > 0:
            caixa = pygame.Rect(12, BANCADA_Y + 12, 180, 30)
            ui.painel(tela, caixa, (20, 24, 40), LARANJA, 10, 2, sombra=False)
            ui.desenhar_texto(tela, "TRIPLO", (caixa.x + 12, caixa.centery + 1), 10, LARANJA, "midleft")
            barra = pygame.Rect(caixa.x + 82, caixa.y + 10, 86, 10)
            pygame.draw.rect(tela, (60, 60, 80), barra, border_radius=4)
            barra.w = max(2, int(barra.w * self.triplo / TEMPO_TRIPLO))
            pygame.draw.rect(tela, LARANJA, barra, border_radius=4)

    def _desenhar_ovo(self, tela):
        # Sombra na bancada
        pygame.draw.ellipse(tela, (100, 70, 48), (self.x - 30, BANCADA_Y - 4, 60, 10))

        piscando = self.invencivel > 0 and not self.morto and int(self.invencivel * 12) % 2 == 0
        if piscando and self.congelado <= 0:
            return

        sup = self.jogador.avatar(ALTURA_OVO)
        s = self.squash
        sx, sy = 1 + 0.14 * s, 1 - 0.16 * s
        if s > 0:
            w, h = sup.get_size()
            sup = pygame.transform.smoothscale(sup, (round(w * sx), round(h * sy)))

        # Engordurado: brilho amarelo enquanto pisca
        if self.invencivel > 0 and not self.escudo and self.vidas < VIDAS:
            sup = sup.copy()
            sup.fill((70, 60, 0), special_flags=pygame.BLEND_RGB_ADD)

        angulo = -self.vx / VEL_OVO * 8
        if self.morto:
            angulo = math.sin(self.tempo_morto * 14) * 20 * max(0.0, 1 - self.tempo_morto / 1.4)
        if abs(angulo) > 0.5:
            sup = pygame.transform.rotate(sup, angulo)

        # Pé do ovo na bancada; recua 3 px a cada tiro
        altura = ALTURA_OVO * sy
        cy = BANCADA_Y - altura / 2 + 3 * s
        tela.blit(sup, sup.get_rect(center=(round(self.x), round(cy))))

        # Gotinhas de óleo brilhando no ovo engordurado
        if self.invencivel > 0 and self.vidas < VIDAS and not self.morto:
            for k in range(3):
                a = self.tempo * 3 + k * 2.1
                px = self.x + math.cos(a) * 20
                py = cy - 8 + math.sin(a * 1.3) * 16
                pygame.draw.circle(tela, (255, 240, 120), (round(px), round(py)), 3)

        if self.escudo:
            e = _sprite("escudo")
            pulso = 1 + 0.04 * math.sin(self.tempo * 6)
            lado = round(ALTURA_OVO * 1.45 * pulso)
            e = pygame.transform.smoothscale(e, (lado, lado))
            tela.blit(e, e.get_rect(center=(round(self.x), round(OVO_Y))))

    def desenhar_hud(self, tela):
        caixa = pygame.Rect(12, 12, 420, 48)
        ui.painel(tela, caixa, (20, 24, 40), BRANCO, 12, 3, sombra=False)
        ui.desenhar_texto(tela, f"PONTOS: {self.pontos}", (caixa.x + 16, caixa.centery), 14,
                          AMARELO, "midleft")
        rec = self.recorde()
        if rec is not None:
            ui.desenhar_texto(tela, f"RECORDE: {rec}", (caixa.x + 236, caixa.centery), 12,
                              (180, 200, 255), "midleft")

        # Onda e vidas à direita (antes do botão de pausa)
        caixa = pygame.Rect(0, 12, 280, 48)
        caixa.right = LARGURA - 76
        ui.painel(tela, caixa, (20, 24, 40), BRANCO, 12, 3, sombra=False)
        ui.desenhar_texto(tela, f"ONDA {self.onda}", (caixa.x + 16, caixa.centery), 12,
                          BRANCO, "midleft")
        for i in range(VIDAS):
            c = (caixa.right - 120 + i * 40, caixa.centery + 1)
            ui.coracao(tela, c, 26, (235, 60, 90) if i < self.vidas else (70, 70, 90))
        if self.escudo:
            pygame.draw.circle(tela, (150, 210, 255), (caixa.x + 136, caixa.centery), 11, 3)
