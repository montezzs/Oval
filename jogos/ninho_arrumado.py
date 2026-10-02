import math
import random
from collections import deque

import pygame

from settings import *
from core import ui
from core.cena import tecla_voltar
from jogos.base import MiniJogo

# ============================================================
# NINHO ARRUMADO
# ============================================================
# Os ovinhos bebês se perderam no celeiro! Empurre cada um até
# um ninho de palha (sokoban). O seu ovo é quem empurra; os bebês
# são a família do ovo, dormindo. Você só EMPURRA (não puxa),
# então pense antes para não prender ninguém num canto.
#
# Mapa dos níveis:
#   #  parede (caixote)     .  ninho          $  bebê
#   *  bebê no ninho        @  jogador        +  jogador no ninho
#   ~  gelo (o bebê empurrado desliza até bater)
#   espaço = chão de palha
#
# O "par" de cada nível é o menor número de passos possível,
# calculado por um solver BFS (todos os níveis têm solução).

NIVEIS = [
    # ---------- 1 a 5: aprendendo a empurrar ----------
    ("PRIMEIRO EMPURRÃO", 3, [
        "#######",
        "#@ $ .#",
        "#######",
    ]),
    ("DOIS SONINHOS", 10, [
        "#######",
        "#     #",
        "#@$ $.#",
        "#    .#",
        "#######",
    ]),
    ("LADO A LADO", 8, [
        "#######",
        "#.  . #",
        "# $$  #",
        "#  @  #",
        "#######",
    ]),
    ("VIRANDO A ESQUINA", 9, [
        "######",
        "#@   #",
        "# $  #",
        "##  ##",
        " #  .#",
        " #####",
    ]),
    ("O PORTÃO", 29, [
        "########",
        "# @ #  #",
        "# $  $.#",
        "## ##  #",
        " # .   #",
        " #######",
    ]),
    # ---------- 6 a 12: três bebês ----------
    ("TRÊS IRMÃOS", 25, [
        "#########",
        "#   #   #",
        "# $ . $ #",
        "#.  #  .#",
        "##$ @ ###",
        " #    #  ",
        " ######  ",
    ]),
    ("CORREDOR DO FENO", 29, [
        "#########",
        "#...    #",
        "#  ###  #",
        "# $ $ $ #",
        "#   @   #",
        "#########",
    ]),
    ("A COLUNA", 40, [
        "#########",
        "#  .#   #",
        "#    $  #",
        "### #$###",
        "#..  $  #",
        "#   # @ #",
        "#########",
    ]),
    ("A PORTINHA", 40, [
        " ####### ",
        "##   . ##",
        "# $ #.  #",
        "#  $ $  #",
        "## @# .##",
        " ####### ",
    ]),
    ("VOLTA LONGA", 43, [
        "##########",
        "#@   #   #",
        "# $$   $ #",
        "#  ##### #",
        "#     ...#",
        "##########",
    ]),
    ("ESCONDE-ESCONDE", 48, [
        "  ######",
        "### @ .#",
        "# .  #.#",
        "#  $$  #",
        "## # $ #",
        " #   ###",
        " #####  ",
    ]),
    ("CANTINHO", 52, [
        " ########",
        " #      #",
        "##  # #.#",
        "# .@$$  #",
        "# .$#   #",
        "#   #####",
        "#####    ",
    ]),
    # ---------- 13 a 16: quatro bebês ----------
    ("QUATRO CANTOS", 26, [
        "#########",
        "#.  #  .#",
        "# $   $ #",
        "#  #@#  #",
        "# $   $ #",
        "#.  #  .#",
        "#########",
    ]),
    ("O NINHO GRANDE", 42, [
        "  ########",
        "  #  ..  #",
        "### #..# #",
        "#  $  $  #",
        "# $  @ $ #",
        "#   ##   #",
        "##########",
    ]),
    ("PALHEIRO", 57, [
        "##########",
        "#    #   #",
        "# $$ # $ #",
        "#  $   . #",
        "## #@#.. #",
        " #  #  . #",
        " #########",
    ]),
    ("LABIRINTO DE CAIXOTES", 60, [
        "###########",
        "#  .# @  .#",
        "# .  $#$#.#",
        "#  #    $$#",
        "## #   #  #",
        " #     #  #",
        " ##########",
    ]),
    # ---------- 17 a 20: GELO! ----------
    ("ESCORREGA!", 5, [
        "#########",
        "#@ $~~~.#",
        "#  $~~~.#",
        "#########",
    ]),
    ("LAGO CONGELADO", 33, [
        "#########",
        "#. $~~  #",
        "#  @~~ .#",
        "##$ ~~ ##",
        "#   ~~  #",
        "#########",
    ]),
    ("PISTA DE GELO", 38, [
        "##########",
        "# @~~~~  #",
        "#$ ~##~ .#",
        "#.$~~~~  #",
        "## .  $ ##",
        " ######## ",
    ]),
    ("O GRANDE INVERNO", 32, [
        "###########",
        "#. ~~~~~ .#",
        "#  ~#~#~  #",
        "# $~~~~~$ #",
        "#  ~#@#~  #",
        "# $~~~~~$ #",
        "#. ~~~~~ .#",
        "###########",
    ]),
]

CIMA, BAIXO, ESQ, DIR = (0, -1), (0, 1), (-1, 0), (1, 0)
DIRECOES = (CIMA, BAIXO, ESQ, DIR)

TECLAS = {
    pygame.K_UP: CIMA, pygame.K_w: CIMA,
    pygame.K_DOWN: BAIXO, pygame.K_s: BAIXO,
    pygame.K_LEFT: ESQ, pygame.K_a: ESQ,
    pygame.K_RIGHT: DIR, pygame.K_d: DIR,
}
TECLAS_DESFAZER = (pygame.K_z, pygame.K_BACKSPACE)

# Área do tabuleiro (entre o HUD e a barra de baixo)
AREA_TOPO = 78
AREA_BASE = 656
CEL_MAX = 72

DUR_PASSO = 0.10            # tween de um passo
DUR_GELO = 0.055            # por casa deslizando no gelo
REPETIR_ESPERA = 0.28       # segurar a tecla: começa a repetir
REPETIR_INTERVALO = 0.13
DUR_VITORIA = 2.2

CHAVE_PROGRESSO = "ninho_arrumado_progresso"

# Cores do celeiro
PALHA = (235, 210, 140)
PALHA_RISCO = (215, 185, 110)
CAIXOTE = (140, 95, 55)
TABUA = (110, 70, 40)
NINHO = (150, 110, 60)
GELO = (196, 232, 250)

BOTAO_DESFAZER = pygame.Rect(12, 668, 210, 42)
BOTAO_REINICIAR = pygame.Rect(LARGURA - 222, 668, 210, 42)


# ============================================================
# REGRAS (funções puras: usadas pelo jogo e pelo solver)
# ============================================================

def analisar(mapa):
    """Lê o mapa em texto e devolve paredes, ninhos, bebês, gelo e jogador."""
    paredes, ninhos, bebes, gelo = set(), set(), [], set()
    jogador = (1, 1)
    for y, linha in enumerate(mapa):
        for x, ch in enumerate(linha):
            c = (x, y)
            if ch == "#":
                paredes.add(c)
            elif ch in ".*+":
                ninhos.add(c)
            elif ch == "~":
                gelo.add(c)
            if ch in "$*":
                bebes.append(c)
            if ch in "@+":
                jogador = c
    return dict(paredes=paredes, ninhos=ninhos, bebes=bebes, gelo=gelo, jogador=jogador,
                largura=max(len(l) for l in mapa), altura=len(mapa))


def mover(paredes, gelo, bebes, jogador, d):
    """
    Tenta dar um passo na direção d.
    Devolve None (bloqueado) ou (novo_jogador, novos_bebes, empurrao),
    onde empurrao é (de, para) do bebê empurrado ou None.
    `bebes` pode ser set ou frozenset (o resultado é do mesmo tipo).
    """
    alvo = (jogador[0] + d[0], jogador[1] + d[1])
    if alvo in paredes:
        return None
    if alvo not in bebes:
        return alvo, bebes, None
    dest = (alvo[0] + d[0], alvo[1] + d[1])
    if dest in paredes or dest in bebes:
        return None
    # No gelo o bebê continua deslizando até bater (ou sair do gelo)
    while dest in gelo:
        prox = (dest[0] + d[0], dest[1] + d[1])
        if prox in paredes or prox in bebes:
            break
        dest = prox
    return alvo, (bebes - {alvo}) | {dest}, (alvo, dest)


def interior(paredes, inicio):
    """Células de dentro do celeiro (flood fill a partir do jogador)."""
    vistos = {inicio}
    fila = deque([inicio])
    while fila:
        x, y = fila.popleft()
        for dx, dy in DIRECOES:
            n = (x + dx, y + dy)
            if n not in paredes and n not in vistos and -1 <= n[0] <= 40 and -1 <= n[1] <= 40:
                vistos.add(n)
                fila.append(n)
    return vistos


def cantos_mortos(paredes, ninhos, dentro):
    """Casas de canto (fora do ninho): bebê que entra ali nunca mais sai."""
    mortos = set()
    for (x, y) in dentro:
        if (x, y) in ninhos:
            continue
        v = (x, y - 1) in paredes or (x, y + 1) in paredes
        h = (x - 1, y) in paredes or (x + 1, y) in paredes
        if v and h:
            mortos.add((x, y))
    return mortos


def estrelas_de(movimentos, par):
    if movimentos <= par:
        return 3
    if movimentos <= par * 1.5:
        return 2
    return 1


# ============================================================
# SPRITES (desenhados uma vez para cada tamanho de célula)
# ============================================================

_sprites = {}


def _caixote(cel):
    """Parede: um caixote de madeira com tábuas e X de reforço."""
    sup = pygame.Surface((cel, cel))
    sup.fill(TABUA)
    m = max(2, cel // 16)
    dentro = pygame.Rect(m, m, cel - 2 * m, cel - 2 * m)
    pygame.draw.rect(sup, CAIXOTE, dentro)
    # Tábuas horizontais
    for i in range(1, 3):
        y = m + dentro.h * i // 3
        pygame.draw.line(sup, ui.escurecer(CAIXOTE, 22), (m, y), (cel - m, y), max(1, cel // 28))
    # X de reforço
    g = max(3, cel // 9)
    pygame.draw.line(sup, TABUA, (m + 2, m + 2), (cel - m - 3, cel - m - 3), g)
    pygame.draw.line(sup, TABUA, (cel - m - 3, m + 2), (m + 2, cel - m - 3), g)
    pygame.draw.line(sup, ui.clarear(CAIXOTE, 25), (m + 2, m), (cel - m - 2, m), max(1, cel // 30))
    # Moldura mais escura + pregos
    pygame.draw.rect(sup, (80, 50, 28), sup.get_rect(), max(1, cel // 30))
    for px, py in ((m + 3, m + 3), (cel - m - 4, m + 3), (m + 3, cel - m - 4), (cel - m - 4, cel - m - 4)):
        pygame.draw.circle(sup, (200, 190, 170), (px, py), max(1, cel // 30))
    return sup


def _piso(cel, semente):
    """Chão de palha com risquinhos."""
    sup = pygame.Surface((cel, cel))
    sup.fill(PALHA)
    rnd = random.Random(semente)
    for _ in range(max(4, cel // 7)):
        x = rnd.randint(2, cel - 3)
        y = rnd.randint(2, cel - 3)
        comp = rnd.randint(cel // 8, cel // 4)
        ang = rnd.uniform(-0.6, 0.6)
        pygame.draw.line(sup, PALHA_RISCO, (x, y),
                         (x + math.cos(ang) * comp, y + math.sin(ang) * comp), 2)
    pygame.draw.rect(sup, ui.escurecer(PALHA, 12), sup.get_rect(), 1)
    return sup


def _gelo(cel, semente):
    """Gelo azulado com brilhos e rachadurinhas."""
    sup = pygame.Surface((cel, cel))
    sup.fill(GELO)
    rnd = random.Random(semente)
    for i in range(2):
        x = rnd.randint(0, cel // 2)
        pygame.draw.line(sup, (240, 250, 255), (x, cel - 4), (x + cel // 2, 4), 3 - i)
    for _ in range(2):
        x, y = rnd.randint(4, cel - 5), rnd.randint(4, cel - 5)
        pygame.draw.lines(sup, (160, 205, 235), False,
                          [(x, y), (x + rnd.randint(-8, 8), y + rnd.randint(3, 9)),
                           (x + rnd.randint(-10, 10), y + rnd.randint(10, 16))], 1)
    pygame.draw.rect(sup, (165, 210, 238), sup.get_rect(), 1)
    return sup


def _ninho(cel):
    """Ninho de palha com um ovinho-fantasma pontilhado indicando o alvo."""
    sup = pygame.Surface((cel, cel), pygame.SRCALPHA)
    cx, cy = cel / 2, cel * 0.62
    w, h = cel * 0.84, cel * 0.46
    pygame.draw.ellipse(sup, ui.escurecer(NINHO, 50), (cx - w / 2, cy - h / 2 + 3, w, h))
    pygame.draw.ellipse(sup, NINHO, (cx - w / 2, cy - h / 2, w, h))
    pygame.draw.ellipse(sup, (118, 84, 44), (cx - w * 0.33, cy - h * 0.3, w * 0.66, h * 0.55))
    # Palhinhas na borda
    rnd = random.Random(cel)
    for i in range(16):
        a = i / 16 * math.tau + rnd.uniform(-0.1, 0.1)
        x = cx + math.cos(a) * w * 0.45
        y = cy + math.sin(a) * h * 0.42
        comp = cel * 0.09
        b = a + math.pi / 2 + rnd.uniform(-0.4, 0.4)
        pygame.draw.line(sup, (200, 160, 85), (x - math.cos(b) * comp, y - math.sin(b) * comp),
                         (x + math.cos(b) * comp, y + math.sin(b) * comp), 2)
    # Ovinho-fantasma pontilhado
    ow, oh = cel * 0.27, cel * 0.33
    oy = cy - oh * 0.45
    for i in range(14):
        a = i / 14 * math.tau
        x = cx + math.cos(a) * ow
        y = oy + math.sin(a) * oh * (0.85 if math.sin(a) < 0 else 1.0)
        pygame.draw.circle(sup, (255, 250, 235), (int(x), int(y)), max(1, cel // 30))
    return sup


def _bebe(cel, cor, feliz):
    """Bebê-ovo dormindo (olhos fechados). Feliz = sorrindo no ninho."""
    w, h = int(cel * 0.52), int(cel * 0.62)
    sup = pygame.Surface((w + 4, h + 4), pygame.SRCALPHA)
    r = pygame.Rect(2, 2, w, h)
    contorno = (150, 150, 170) if sum(cor) > 600 else ui.escurecer(cor, 70)
    pygame.draw.ellipse(sup, contorno, r)
    pygame.draw.ellipse(sup, cor, r.inflate(-4, -4))
    # Brilho
    pygame.draw.ellipse(sup, ui.clarear(cor, 70), (r.x + w * 0.2, r.y + h * 0.12, w * 0.24, h * 0.2))
    # Olhos fechados (arcos)
    cx = r.centerx
    oy = r.y + h * 0.5
    olho = max(4, w // 5)
    esp = max(1, cel // 30)
    cor_linha = (40, 30, 30)
    for lado in (-1, 1):
        ox = cx + lado * w * 0.2
        ret = pygame.Rect(0, 0, olho, olho * 0.8)
        ret.center = (ox, oy)
        if feliz:
            pygame.draw.arc(sup, cor_linha, ret, 0.2, math.pi - 0.2, esp + 1)     # ^ ^
        else:
            pygame.draw.arc(sup, cor_linha, ret, math.pi + 0.2, math.tau - 0.2, esp + 1)
    # Bochechas
    for lado in (-1, 1):
        pygame.draw.circle(sup, (255, 150, 160), (int(cx + lado * w * 0.3), int(oy + h * 0.12)),
                           max(2, w // 10))
    # Boquinha
    b = pygame.Rect(0, 0, max(4, w // 4), max(3, h // 8))
    b.center = (cx, oy + h * 0.18)
    if feliz:
        pygame.draw.arc(sup, cor_linha, b, math.pi + 0.3, math.tau - 0.3, esp + 1)
    else:
        pygame.draw.circle(sup, cor_linha, b.center, max(1, w // 16))
    return sup


def _sprites_de(cel):
    s = _sprites.get(cel)
    if s is not None:
        return s
    s = {"caixote": _caixote(cel), "ninho": _ninho(cel)}
    for i in range(4):
        s["piso", i] = _piso(cel, 31 + i)
        s["gelo", i] = _gelo(cel, 57 + i)
    from core.jogador import Jogador
    for i in range(4):
        cor = Jogador.cor_do_ovo(i)
        s["bebe", i, False] = _bebe(cel, cor, False)
        s["bebe", i, True] = _bebe(cel, cor, True)
    brilho = pygame.Surface((cel, cel), pygame.SRCALPHA)
    for k in range(6):
        pygame.draw.circle(brilho, (255, 230, 90, 26 + k * 10), (cel // 2, cel // 2),
                           int(cel * (0.48 - k * 0.04)))
    s["brilho"] = brilho
    if len(_sprites) > 8:
        _sprites.clear()
    _sprites[cel] = s
    return s


def _cor_bebe(i, ovo_jogador):
    """Cor do i-ésimo bebê: as cores da família, menos a do seu ovo."""
    outras = [c for c in range(4) if c != ovo_jogador]
    return outras[i % len(outras)]


def _geometria(dados):
    larg, alt = dados["largura"], dados["altura"]
    cel = min(CEL_MAX, (LARGURA - 64) // larg, (AREA_BASE - AREA_TOPO) // alt)
    x0 = (LARGURA - larg * cel) // 2
    y0 = AREA_TOPO + (AREA_BASE - AREA_TOPO - alt * cel) // 2
    return cel, x0, y0


def _suave(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


class NinhoArrumado(MiniJogo):

    ID = "ninho_arrumado"
    TITULO = "NINHO ARRUMADO"
    TITULO_CURTO = "NINHO"
    DESCRICAO = "Os ovinhos bebês se perderam no celeiro! Empurre cada um até um ninho, sem prender no canto."
    COR = (200, 150, 70)
    INSTRUCOES = [
        "Empurre cada BEBÊ-OVO até um NINHO!",
        "Você só empurra (não puxa): cuidado com os cantos.",
        "Menos passos = mais ★. No GELO o bebê desliza!",
        "SETAS/WASD/clique • Z desfaz • R reinicia",
    ]
    ROTULO_PONTOS = "ESTRELAS"
    CONTAGEM = False

    # Moedas: regra própria (ver calcular_moedas)
    MOEDAS_MAX = 20
    MOEDAS_RECORDE = 0          # cada nível novo já paga bem; sem bônus de recorde

    _miniaturas = {}
    _tabuleiros = {}

    # --------------------------------------------------------
    # CENÁRIO: dentro do celeiro
    # --------------------------------------------------------

    @classmethod
    def criar_fundo(cls, jogador):
        sup = pygame.Surface((LARGURA, ALTURA))
        sup.fill(PALHA)
        rnd = random.Random(8)

        # Parede de tábuas vermelhas no alto
        for x in range(0, LARGURA, 48):
            cor = (160, 62, 48) if (x // 48) % 2 else (172, 70, 54)
            pygame.draw.rect(sup, cor, (x, 0, 48, 120))
            pygame.draw.line(sup, (110, 40, 32), (x, 0), (x, 120), 3)
            for y in (18, 96):
                pygame.draw.circle(sup, (90, 34, 28), (x + 24, y), 2)
        pygame.draw.rect(sup, (96, 60, 34), (0, 112, LARGURA, 14))
        pygame.draw.rect(sup, (126, 84, 48), (0, 112, LARGURA, 4))

        # Chão de palha com muitos risquinhos
        for _ in range(900):
            x, y = rnd.randrange(LARGURA), rnd.randrange(126, ALTURA)
            comp = rnd.randint(6, 16)
            ang = rnd.uniform(-0.7, 0.7)
            cor = rnd.choice([PALHA_RISCO, (225, 196, 120), (245, 224, 165)])
            pygame.draw.line(sup, cor, (x, y), (x + math.cos(ang) * comp, y + math.sin(ang) * comp), 2)

        # Fardos de feno nos cantos
        for bx, by in ((-30, 560), (40, 610), (LARGURA - 150, 570), (LARGURA - 90, 620), (-20, 170),
                       (LARGURA - 110, 160)):
            r = pygame.Rect(bx, by, 150, 90)
            pygame.draw.rect(sup, (170, 135, 60), r.move(4, 6), border_radius=14)
            pygame.draw.rect(sup, (226, 190, 92), r, border_radius=14)
            for i in range(8):
                yy = r.y + 12 + i * 9
                pygame.draw.line(sup, (200, 162, 70), (r.x + 8, yy), (r.right - 8, yy + rnd.randint(-2, 2)), 2)
            for fx in (r.x + 40, r.right - 40):
                pygame.draw.rect(sup, (120, 80, 40), (fx - 3, r.y, 6, r.h))

        # Vinheta suave nas bordas
        veu = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        for i in range(14):
            pygame.draw.rect(veu, (60, 30, 10, 10), (i * 4, i * 4, LARGURA - i * 8, ALTURA - i * 8), 4)
        sup.blit(veu, (0, 0))
        return sup

    @classmethod
    def desenhar_icone(cls, sup, jogador):
        w, h = sup.get_size()
        cel = max(20, min(h // 3, w // 6))
        s = _sprites_de(cel)
        y = h // 2 - cel // 2 + 10
        x0 = w // 2 - cel * 2
        # chão
        for i in range(4):
            sup.blit(s["piso", i], (x0 + i * cel, y))
        sup.blit(s["caixote"], (x0 - cel, y))
        sup.blit(s["caixote"], (x0 + 4 * cel, y))
        sup.blit(s["ninho"], (x0 + 3 * cel, y))
        b = s["bebe", _cor_bebe(0, jogador.ovo), False]
        sup.blit(b, b.get_rect(center=(x0 + int(1.9 * cel), y + cel // 2 + 2)))
        b2 = s["bebe", _cor_bebe(1, jogador.ovo), True]
        sup.blit(s["brilho"], (x0 + 3 * cel, y))
        sup.blit(b2, b2.get_rect(center=(x0 + int(3.5 * cel), y + cel // 2 - 2)))
        jogador.desenhar(sup, (x0 + int(0.8 * cel), y + cel // 2 - 2), cel * 0.85, angulo=-8)

    # --------------------------------------------------------
    # PROGRESSO (níveis liberados e estrelas de cada um)
    # --------------------------------------------------------

    def _progresso(self):
        rec = self.app.save["recordes"]
        p = rec.get(CHAVE_PROGRESSO)
        ok = isinstance(p, dict) and isinstance(p.get("nivel"), int) \
            and isinstance(p.get("estrelas"), list)
        if not ok:
            p = {"nivel": 0, "estrelas": [0] * len(NIVEIS)}
            rec[CHAVE_PROGRESSO] = p
        # Corrige tamanhos/valores estranhos
        est = [e if isinstance(e, int) and 0 <= e <= 3 else 0 for e in p["estrelas"]]
        est = (est + [0] * len(NIVEIS))[:len(NIVEIS)]
        p["estrelas"] = est
        p["nivel"] = max(0, min(len(NIVEIS) - 1, p["nivel"]))
        return p

    def total_estrelas(self):
        return sum(self._progresso()["estrelas"])

    # --------------------------------------------------------
    # PARTIDA (um nível)
    # --------------------------------------------------------

    def reiniciar(self):
        if not hasattr(self, "nivel"):
            self.nivel = self._progresso()["nivel"]
        self.nivel = max(0, min(len(NIVEIS) - 1, self.nivel))
        self.nome_nivel, self.par, mapa = NIVEIS[self.nivel]
        dados = analisar(mapa)
        self.paredes = dados["paredes"]
        self.ninhos = dados["ninhos"]
        self.gelo = dados["gelo"]
        self.dentro = interior(self.paredes, dados["jogador"])
        self.mortos = cantos_mortos(self.paredes, self.ninhos, self.dentro)
        self.cel, self.x0, self.y0 = _geometria(dados)
        self.larg, self.alt = dados["largura"], dados["altura"]
        self.sprites = _sprites_de(self.cel)
        self.tabuleiro = self._tabuleiro()

        self.inicio = (dados["jogador"], tuple(dados["bebes"]))
        self.jog = dados["jogador"]
        self.bebes = list(dados["bebes"])
        self.cores = [_cor_bebe(i, self.jogador.ovo) for i in range(len(self.bebes))]
        self.movimentos = 0
        self.historico = []
        self.olhar_esq = False
        self.fila = []                  # passos esperando (teclado / caminho do mouse)
        self.segurada = None            # [tecla, direcao, tempo] para repetir
        self.mouse = (-100, -100)

        # Animações
        self.anim_jog = None            # [de, para, t, dur]
        self.anim_bebes = {}            # índice -> [de, para, t, dur]
        self.empurrando = 0.0           # inclinação do ovo ao empurrar
        self.dir_empurrao = DIR
        self.pulo_bebe = {}             # índice -> tempo desde que chegou no ninho

        self.fase = "jogando"           # jogando / vitoria
        self.t_fase = 0.0
        self.travado = False
        self.t_travado = 0.0
        self.estrelas_ganhas = 0
        self.estrelas_mostradas = 0
        self._moedas_nivel = 0

    def _tabuleiro(self):
        """Chão, gelo, ninhos e caixotes do nível (cacheado)."""
        chave = (self.nivel, self.cel)
        sup = NinhoArrumado._tabuleiros.get(chave)
        if sup is not None:
            return sup
        cel = self.cel
        s = self.sprites
        sup = pygame.Surface((self.larg * cel + 12, self.alt * cel + 12), pygame.SRCALPHA)

        # Sombra dos caixotes
        for (x, y) in self.paredes:
            pygame.draw.rect(sup, (60, 35, 10, 70), (x * cel + 8, y * cel + 10, cel, cel),
                             border_radius=4)
        for (x, y) in self.dentro:
            pos = (x * cel, y * cel)
            if (x, y) in self.gelo:
                sup.blit(s["gelo", (x * 3 + y) % 4], pos)
            else:
                sup.blit(s["piso", (x + y * 5) % 4], pos)
        # Sombra interna das paredes sobre o chão
        for (x, y) in self.dentro:
            if (x, y - 1) in self.paredes:
                pygame.draw.rect(sup, (90, 60, 20, 60), (x * cel, y * cel, cel, max(3, cel // 10)))
            if (x - 1, y) in self.paredes:
                pygame.draw.rect(sup, (90, 60, 20, 45), (x * cel, y * cel, max(3, cel // 12), cel))
        for (x, y) in self.ninhos:
            sup.blit(s["ninho"], (x * cel, y * cel))
        for (x, y) in self.paredes:
            sup.blit(s["caixote"], (x * cel, y * cel))

        if len(NinhoArrumado._tabuleiros) > 24:
            NinhoArrumado._tabuleiros.clear()
        NinhoArrumado._tabuleiros[chave] = sup
        return sup

    # --------------------------------------------------------
    # ENTRADA
    # --------------------------------------------------------

    def evento_jogo(self, e):
        if self.fase != "jogando":
            return

        if e.type == pygame.KEYDOWN:
            if e.key in TECLAS:
                d = TECLAS[e.key]
                self.fila = self.fila[:1] if self._ocupado() else []
                self.fila.append(d)
                self.segurada = [e.key, d, 0.0]
            elif e.key in TECLAS_DESFAZER:
                self.desfazer()
            elif e.key == pygame.K_r:
                self.reiniciar_nivel()

        elif e.type == pygame.KEYUP:
            if self.segurada and e.key == self.segurada[0]:
                self.segurada = None

        elif e.type == pygame.MOUSEMOTION:
            self.mouse = e.pos

        elif e.type == pygame.MOUSEBUTTONDOWN:
            self.mouse = e.pos
            if e.button == 3:
                self.desfazer()
                return
            if e.button != 1:
                return
            if BOTAO_DESFAZER.collidepoint(e.pos):
                self.desfazer()
            elif BOTAO_REINICIAR.collidepoint(e.pos):
                self.reiniciar_nivel()
            else:
                self._clique_celula(e.pos)

    def _clique_celula(self, pos):
        cx = (pos[0] - self.x0) // self.cel
        cy = (pos[1] - self.y0) // self.cel
        alvo = (int(cx), int(cy))
        if alvo not in self.dentro:
            return
        dx, dy = alvo[0] - self.jog[0], alvo[1] - self.jog[1]
        if abs(dx) + abs(dy) == 1:
            self.fila = [(dx, dy)]
            return
        # Longe: anda até lá sem empurrar ninguém (se der)
        caminho = self._caminho(alvo)
        if caminho:
            self.fila = caminho

    def _caminho(self, alvo):
        ocupado = set(self.bebes)
        if alvo in ocupado or alvo in self.paredes:
            return None
        vindo = {self.jog: None}
        fila = deque([self.jog])
        while fila:
            c = fila.popleft()
            if c == alvo:
                passos = []
                while vindo[c] is not None:
                    ant, d = vindo[c]
                    passos.append(d)
                    c = ant
                return passos[::-1]
            for d in DIRECOES:
                n = (c[0] + d[0], c[1] + d[1])
                if n in vindo or n in self.paredes or n in ocupado or n not in self.dentro:
                    continue
                vindo[n] = (c, d)
                fila.append(n)
        return None

    # --------------------------------------------------------
    # AÇÕES
    # --------------------------------------------------------

    def _ocupado(self):
        return self.anim_jog is not None or bool(self.anim_bebes)

    def _terminar_animacoes(self):
        self.anim_jog = None
        self.anim_bebes.clear()

    def _foto(self):
        return (self.jog, tuple(self.bebes), self.movimentos, self.olhar_esq)

    def _passo(self, d):
        """Executa um passo (a lógica é instantânea; o desenho anima)."""
        r = mover(self.paredes, self.gelo, set(self.bebes), self.jog, d)
        if d[0]:
            self.olhar_esq = d[0] < 0
        if r is None:
            # Bateu: tremidinha e cancela o resto do caminho
            self.fila.clear()
            self.tremer(0.14)
            self.som("bater", 0.35)
            self.empurrando = 0.5
            self.dir_empurrao = d
            return
        novo, _, empurrao = r
        self.historico.append(self._foto())
        if len(self.historico) > 3000:
            self.historico.pop(0)
        self.anim_jog = [self.jog, novo, 0.0, DUR_PASSO]
        self.jog = novo
        self.movimentos += 1

        if empurrao:
            de, para = empurrao
            i = self.bebes.index(de)
            self.bebes[i] = para
            casas = abs(para[0] - de[0]) + abs(para[1] - de[1])
            dur = DUR_PASSO + max(0, casas - 1) * DUR_GELO
            self.anim_bebes[i] = [de, para, 0.0, dur]
            self.empurrando = 1.0
            self.dir_empurrao = d
            self.fila = self.fila[:2]     # empurrou: não continua caminho do mouse
            if casas > 1:
                self.som("virar", 0.5)
            else:
                self.som("pulo", 0.25)
            if para in self.ninhos:
                self.pulo_bebe[i] = -dur
            self._checar_fim()
        self._checar_travado()

    def desfazer(self):
        if self.fase != "jogando" or not self.historico:
            return
        self._terminar_animacoes()
        self.fila.clear()
        self.jog, bebes, self.movimentos, self.olhar_esq = self.historico.pop()
        self.bebes = list(bebes)
        self.som("virar", 0.4)
        self._checar_travado()

    def reiniciar_nivel(self):
        """R: volta ao começo (dá para desfazer o R com Z)."""
        if self.fase != "jogando":
            return
        if self.movimentos == 0 and not self.historico:
            return
        self._terminar_animacoes()
        self.fila.clear()
        self.historico.append(self._foto())
        self.jog, bebes = self.inicio
        self.bebes = list(bebes)
        self.movimentos = 0
        self.som("voltar", 0.6)
        x, y = self._centro(self.jog)
        self.particulas.explodir((x, y), [self.jogador.cor, BRANCO], 10, 120, 0.4, (2, 4))
        self._checar_travado()

    def _checar_fim(self):
        if all(b in self.ninhos for b in self.bebes):
            self.fase = "vitoria"
            self.t_fase = -max([a[3] for a in self.anim_bebes.values()] + [DUR_PASSO])
            self.fila.clear()
            self.segurada = None

    def _checar_travado(self):
        """Detecta travas certas: bebê num canto ou bloco 2x2, ou ninguém empurrável."""
        self.travado = self._esta_travado()
        if not self.travado:
            self.t_travado = 0.0

    def _esta_travado(self):
        if self.fase != "jogando":
            return False
        ocup = set(self.bebes)
        for b in self.bebes:
            if b in self.mortos:
                return True
        # Bloco 2x2 cheio de paredes/bebês com algum bebê fora do ninho
        cheio = self.paredes | ocup
        for b in self.bebes:
            for ox in (-1, 0):
                for oy in (-1, 0):
                    q = [(b[0] + ox + i, b[1] + oy + j) for i in (0, 1) for j in (0, 1)]
                    if all(c in cheio for c in q) and \
                            any(c in ocup and c not in self.ninhos for c in q):
                        return True
        # Algum empurrão possível?
        alcance = {self.jog}
        fila = deque([self.jog])
        while fila:
            c = fila.popleft()
            for d in DIRECOES:
                n = (c[0] + d[0], c[1] + d[1])
                if n not in alcance and n not in self.paredes and n not in ocup and n in self.dentro:
                    alcance.add(n)
                    fila.append(n)
        for b in self.bebes:
            for d in DIRECOES:
                atras = (b[0] - d[0], b[1] - d[1])
                frente = (b[0] + d[0], b[1] + d[1])
                if atras in alcance and frente not in self.paredes and frente not in ocup:
                    return False
        return True

    # --------------------------------------------------------
    # FIM DO NÍVEL
    # --------------------------------------------------------

    def _concluir(self):
        prog = self._progresso()
        antes = prog["estrelas"][self.nivel]
        estrelas = estrelas_de(self.movimentos, self.par)
        self.estrelas_ganhas = estrelas
        self.estrelas_mostradas = 0

        # Moedas: 1ª vez = 5 + 5·estrelas; melhorou = diferença ×5; repetir = 2
        if antes == 0:
            self._moedas_nivel = min(20, 5 + 5 * estrelas)
        elif estrelas > antes:
            self._moedas_nivel = (estrelas - antes) * 5
        else:
            # Repetir nível curtinho não vira fazendinha de moedas
            self._moedas_nivel = 2 if self.tempo_partida >= self.TEMPO_MINIMO else 0

        prog["estrelas"][self.nivel] = max(antes, estrelas)
        prog["nivel"] = max(prog["nivel"], min(len(NIVEIS) - 1, self.nivel + 1))
        self.app.save.salvar()

        ultimo = self.nivel == len(NIVEIS) - 1
        titulo = "TODOS NO NINHO!" if ultimo else f"NÍVEL {self.nivel + 1} COMPLETO!"
        self.terminar(venceu=True, valor=self.total_estrelas(), titulo=titulo,
                      linhas=["", "", f"PASSOS: {self.movimentos}  •  PAR: {self.par}"])

        # Menu de fim próprio: próximo nível / repetir / escolher
        if self.nivel + 1 < len(NIVEIS):
            rotulos = ["PRÓXIMO NÍVEL", "JOGAR DE NOVO", "ESCOLHER NÍVEL"]
        else:
            rotulos = ["JOGAR DE NOVO", "ESCOLHER NÍVEL", "MENU DE JOGOS"]
        self.menu_fim = ui.Menu(rotulos, LARGURA // 2, 420, 340, 54, 12, 16)

    def calcular_moedas(self, valor, venceu):
        return max(0, min(self.MOEDAS_MAX, int(self._moedas_nivel)))

    # --------------------------------------------------------
    # LÓGICA
    # --------------------------------------------------------

    def atualizar_jogo(self, dt):
        self.empurrando = max(0.0, self.empurrando - dt * 4)

        # Animações
        if self.anim_jog:
            self.anim_jog[2] += dt
            if self.anim_jog[2] >= self.anim_jog[3]:
                self.anim_jog = None
        for i in list(self.anim_bebes):
            a = self.anim_bebes[i]
            a[2] += dt
            if a[2] >= a[3]:
                del self.anim_bebes[i]
                if a[1] in self.ninhos:
                    self._chegou_no_ninho(i)
        for i in self.pulo_bebe:
            self.pulo_bebe[i] += dt

        if self.fase == "vitoria":
            self._atualizar_vitoria(dt)
            return

        # Segurar a tecla repete o passo
        if self.segurada:
            k, d, t = self.segurada
            try:
                segurando = pygame.key.get_pressed()[k]
            except (IndexError, pygame.error):
                segurando = False
            if not segurando:
                self.segurada = None
            else:
                self.segurada[2] = t + dt
                if self.segurada[2] >= REPETIR_ESPERA and not self._ocupado() and not self.fila:
                    self.segurada[2] = REPETIR_ESPERA - REPETIR_INTERVALO
                    self.fila.append(d)

        # Próximo passo quando a animação acabou
        if self.fila and self.anim_jog is None:
            self._passo(self.fila.pop(0))

        if self.travado:
            self.t_travado += dt

    def _chegou_no_ninho(self, i):
        x, y = self._centro(self.bebes[i])
        self.som("ponto", 0.8)
        self.particulas.explodir((x, y), [AMARELO, BRANCO, (255, 200, 120)], 12, 150, 0.6, (2, 4))
        self.textos.adicionar("zzz", (x + self.cel * 0.3, y - self.cel * 0.5), BRANCO, 12)

    def _atualizar_vitoria(self, dt):
        antes = self.t_fase
        self.t_fase += dt
        if antes < 0 <= self.t_fase:
            self.som("acerto")
            self.tremer(0.1)
        if self.t_fase >= 0:
            # Confete do ovo
            if int(self.t_fase * 5) != int(antes * 5):
                x = random.uniform(self.x0, self.x0 + self.larg * self.cel)
                y = random.uniform(self.y0, self.y0 + self.alt * self.cel * 0.6)
                self.particulas.explodir((x, y), [AMARELO, (255, 120, 150), (120, 200, 255),
                                                  (140, 230, 120), self.jogador.cor],
                                         18, 260, 1.0, (3, 6))
        if self.t_fase >= DUR_VITORIA:
            self._concluir()

    def atualizar(self, dt):
        super().atualizar(dt)
        # Estrelas aparecendo uma a uma na tela de fim
        if self.estado == "fim" and self.estrelas_mostradas < self.estrelas_ganhas:
            if self.tempo_estado >= 0.5 + self.estrelas_mostradas * 0.4:
                self.estrelas_mostradas += 1
                self.som("moeda", 0.7)

    # --------------------------------------------------------
    # MENUS (seletor de níveis no início e fim de nível)
    # --------------------------------------------------------

    def _layout_seletor(self):
        """Retângulos das setinhas do seletor de nível (tela de início)."""
        y = self._y_seletor
        esq = pygame.Rect(0, 0, 48, 48)
        dirr = pygame.Rect(0, 0, 48, 48)
        esq.center = (LARGURA // 2 - 200, y + 106)
        dirr.center = (LARGURA // 2 + 200, y + 106)
        return esq, dirr

    def _mudar_nivel(self, passo):
        liberado = self._progresso()["nivel"]
        novo = max(0, min(liberado, self.nivel + passo))
        if novo != self.nivel:
            self.nivel = novo
            self.som("clique", 0.6)
            self._preparar()
        else:
            self.som("erro", 0.4)

    def _evento_inicio(self, e):
        if e.type == pygame.KEYDOWN and e.key in (pygame.K_LEFT, pygame.K_a):
            self._mudar_nivel(-1)
            return
        if e.type == pygame.KEYDOWN and e.key in (pygame.K_RIGHT, pygame.K_d):
            self._mudar_nivel(1)
            return
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and hasattr(self, "_y_seletor"):
            esq, dirr = self._layout_seletor()
            if esq.collidepoint(e.pos):
                self._mudar_nivel(-1)
                return
            if dirr.collidepoint(e.pos):
                self._mudar_nivel(1)
                return
        super()._evento_inicio(e)

    def evento(self, e):
        if self.estado != "fim":
            super().evento(e)
            return
        if e.type == pygame.WINDOWFOCUSLOST or self.tempo_estado < 0.6:
            return
        if tecla_voltar(e):
            self.sair_para_menu()
            return
        escolha = self.menu_fim.evento(e)
        if escolha is None:
            return
        rotulo = self.menu_fim.botoes[escolha].rotulo
        if rotulo == "PRÓXIMO NÍVEL":
            self.som("selecionar")
            self.nivel = min(len(NIVEIS) - 1, self.nivel + 1)
            self.comecar()
        elif rotulo == "JOGAR DE NOVO":
            self.som("selecionar")
            self.comecar()
        elif rotulo == "ESCOLHER NÍVEL":
            self.som("selecionar")
            self._montar_menu_inicio()
            self._preparar()
            self._mudar_estado("inicio")
        else:
            self.sair_para_menu()

    # --------------------------------------------------------
    # DESENHO
    # --------------------------------------------------------

    def _centro(self, c):
        return (self.x0 + c[0] * self.cel + self.cel / 2, self.y0 + c[1] * self.cel + self.cel / 2)

    def _pos_anim(self, anim, atual):
        if not anim:
            return self._centro(atual)
        de, para, t, dur = anim
        p = _suave(t / dur)
        a, b = self._centro(de), self._centro(para)
        return (a[0] + (b[0] - a[0]) * p, a[1] + (b[1] - a[1]) * p)

    def desenhar_jogo(self, tela):
        tela.blit(self.fundo(self.jogador), (0, 0))
        # Sombra do tabuleiro todo
        tela.blit(self.tabuleiro, (self.x0, self.y0))

        cel = self.cel
        s = self.sprites
        vitoria = self.fase == "vitoria" and self.t_fase >= 0

        # Personagens ordenados de cima para baixo
        itens = []
        for i, b in enumerate(self.bebes):
            x, y = self._pos_anim(self.anim_bebes.get(i), b)
            itens.append((y, 0, i, x))
        jx, jy = self._pos_anim(self.anim_jog, self.jog)
        itens.append((jy + 0.1, 1, -1, jx))
        itens.sort()

        for y, tipo, i, x in itens:
            if tipo == 0:
                self._desenhar_bebe(tela, i, x, y, vitoria)
            else:
                self._desenhar_ovo(tela, x, y, vitoria)

        # zzz dos bebês que estão dormindo no ninho
        if not vitoria:
            for i, b in enumerate(self.bebes):
                if b in self.ninhos and i not in self.anim_bebes:
                    x, y = self._centro(b)
                    fase = (self.tempo * 0.7 + i * 0.37) % 1.0
                    zx = x + cel * 0.22 + math.sin(fase * 6) * 4
                    zy = y - cel * 0.42 - fase * cel * 0.45
                    tam = 10 if fase < 0.5 else 12
                    sup = ui.texto("z", tam, (70, 60, 120), False)
                    if fase > 0.75:
                        sup = sup.copy()
                        sup.set_alpha(int(255 * (1 - fase) * 4))
                    tela.blit(sup, sup.get_rect(center=(zx, zy)))

        self.particulas.desenhar(tela)
        self.textos.desenhar(tela)

        if self.estado in ("jogando", "pausado"):
            self._desenhar_barra(tela)

    def _desenhar_bebe(self, tela, i, x, y, vitoria):
        cel = self.cel
        s = self.sprites
        b = self.bebes[i]
        no_ninho = b in self.ninhos and i not in self.anim_bebes
        spr = s["bebe", self.cores[i], no_ninho or vitoria]
        dy = 0.0
        if no_ninho:
            tela.blit(s["brilho"], (x - cel / 2, y - cel / 2))
            dy = -cel * 0.08
            t = self.pulo_bebe.get(i)
            if t is not None and 0 <= t < 0.35:
                dy -= math.sin(t / 0.35 * math.pi) * cel * 0.25
        if vitoria:
            dy = -cel * 0.08 - abs(math.sin(self.t_fase * 7 + i * 0.8)) * cel * 0.35

        # Squash ao ser empurrado
        a = self.anim_bebes.get(i)
        if a:
            p = min(1.0, a[2] / a[3])
            k = math.sin(p * math.pi) * 0.18
            horizontal = a[1][1] == a[0][1]
            w, h = spr.get_size()
            if horizontal:
                nw, nh = int(w * (1 + k)), int(h * (1 - k * 0.8))
            else:
                nw, nh = int(w * (1 - k * 0.8)), int(h * (1 + k))
            spr = pygame.transform.smoothscale(spr, (max(2, nw), max(2, nh)))
        # Sombrinha
        pygame.draw.ellipse(tela, (150, 120, 60), (x - cel * 0.22, y + cel * 0.22, cel * 0.44, cel * 0.12))
        tela.blit(spr, spr.get_rect(midbottom=(x, y + cel * 0.3 + dy)))

    def _desenhar_ovo(self, tela, x, y, vitoria):
        cel = self.cel
        altura = cel * 0.74
        ang = 0.0
        dx = dy = 0.0
        if vitoria:
            dy = -abs(math.sin(self.t_fase * 7)) * cel * 0.4
            ang = math.sin(self.t_fase * 7) * 8
        else:
            # Respiração + inclinação ao empurrar
            dy = math.sin(self.tempo * 3) * 1.5
            if self.empurrando > 0:
                d = self.dir_empurrao
                ang = -d[0] * 12 * self.empurrando
                dx = d[0] * cel * 0.06 * self.empurrando
                dy += d[1] * cel * 0.06 * self.empurrando
            if self.anim_jog:
                p = self.anim_jog[2] / self.anim_jog[3]
                dy -= math.sin(p * math.pi) * cel * 0.08
        pygame.draw.ellipse(tela, (150, 120, 60), (x - cel * 0.26, y + cel * 0.26, cel * 0.52, cel * 0.13))
        self.jogador.desenhar(tela, (x + dx, y - cel * 0.04 + dy), altura,
                              espelhar=self.olhar_esq, angulo=ang)

    def _desenhar_barra(self, tela):
        """Botões DESFAZER / REINICIAR e nome do nível (ou aviso de trava)."""
        for r, rot in ((BOTAO_DESFAZER, "Z  DESFAZER"), (BOTAO_REINICIAR, "R  REINICIAR")):
            hover = r.collidepoint(self.mouse)
            destaque = rot.startswith("R") and self.travado and self.t_travado > 0.6 \
                and int(self.tempo * 3) % 2 == 0
            cor = (84, 96, 150) if hover or destaque else (40, 44, 70)
            ui.painel(tela, r, cor, AMARELO if destaque else BRANCO, 12, 3, sombra=False)
            ui.desenhar_texto(tela, rot, r.center, 12, BRANCO, "center")

        centro = (LARGURA // 2, BOTAO_DESFAZER.centery)
        if self.travado and self.t_travado > 0.6 and self.fase == "jogando":
            r = pygame.Rect(0, 0, 560, 40)
            r.center = centro
            ui.painel(tela, r, (120, 60, 30), (255, 190, 90), 12, 3, sombra=False)
            ui.desenhar_texto(tela, "Parece que travou! Aperte R ou Z", centro, 12,
                              (255, 235, 180), "center")
        else:
            ui.desenhar_texto(tela, self.nome_nivel, centro, 12, (90, 55, 25), "center", False)

    def desenhar_hud(self, tela):
        # Nível
        caixa = pygame.Rect(12, 12, 200, 48)
        ui.painel(tela, caixa, (20, 24, 40), BRANCO, 12, 3, sombra=False)
        ui.desenhar_texto(tela, f"NÍVEL {self.nivel + 1}/{len(NIVEIS)}", caixa.center, 14,
                          AMARELO, "center")

        # Passos e par
        caixa2 = pygame.Rect(caixa.right + 10, 12, 190, 48)
        ui.painel(tela, caixa2, (20, 24, 40), BRANCO, 12, 3, sombra=False)
        ui.desenhar_texto(tela, f"PASSOS: {self.movimentos}", (caixa2.x + 14, caixa2.y + 10), 12, BRANCO)
        ui.desenhar_texto(tela, f"PAR: {self.par}", (caixa2.x + 14, caixa2.y + 29), 10, (180, 220, 255))

        # Estrelas que ainda dá para ganhar
        caixa3 = pygame.Rect(caixa2.right + 10, 12, 132, 48)
        ui.painel(tela, caixa3, (20, 24, 40), BRANCO, 12, 3, sombra=False)
        n = estrelas_de(self.movimentos, self.par)
        for k in range(3):
            c = (caixa3.x + 26 + k * 40, caixa3.centery)
            ui.estrela(tela, (c[0] + 1, c[1] + 2), 14, (0, 0, 0))
            ui.estrela(tela, c, 14, AMARELO if k < n else (70, 74, 100))

        # Total de estrelas
        caixa4 = pygame.Rect(caixa3.right + 10, 12, 196, 48)
        ui.painel(tela, caixa4, (20, 24, 40), BRANCO, 12, 3, sombra=False)
        ui.estrela(tela, (caixa4.x + 24, caixa4.centery), 12, AMARELO)
        ui.desenhar_texto(tela, f"{self.total_estrelas()}/{len(NIVEIS) * 3}",
                          (caixa4.x + 44, caixa4.centery + 1), 14, BRANCO, "midleft")

    # --------------------------------------------------------
    # TELA DE INÍCIO (com seletor de níveis)
    # --------------------------------------------------------

    @classmethod
    def _miniatura_nivel(cls, i, jogador, cel):
        chave = (i, cel, jogador.ovo)
        sup = cls._miniaturas.get(chave)
        if sup is not None:
            return sup
        _, _, mapa = NIVEIS[i]
        d = analisar(mapa)
        dentro = interior(d["paredes"], d["jogador"])
        sup = pygame.Surface((d["largura"] * cel, d["altura"] * cel), pygame.SRCALPHA)
        for (x, y) in dentro:
            cor = GELO if (x, y) in d["gelo"] else PALHA
            pygame.draw.rect(sup, cor, (x * cel, y * cel, cel, cel))
        for (x, y) in d["paredes"]:
            r = pygame.Rect(x * cel, y * cel, cel, cel)
            pygame.draw.rect(sup, CAIXOTE, r)
            pygame.draw.rect(sup, TABUA, r, 2)
        for (x, y) in d["ninhos"]:
            pygame.draw.ellipse(sup, NINHO, (x * cel + 2, y * cel + cel * 0.35, cel - 4, cel * 0.5))
        from core.jogador import Jogador
        for k, (x, y) in enumerate(d["bebes"]):
            cor = Jogador.cor_do_ovo(_cor_bebe(k, jogador.ovo))
            r = pygame.Rect(0, 0, cel * 0.6, cel * 0.72)
            r.center = (x * cel + cel / 2, y * cel + cel / 2)
            pygame.draw.ellipse(sup, (60, 50, 50), r.inflate(2, 2))
            pygame.draw.ellipse(sup, cor, r)
        jx, jy = d["jogador"]
        jogador.desenhar(sup, (jx * cel + cel / 2, jy * cel + cel / 2), cel * 0.8)
        cls._miniaturas[chave] = sup
        return sup

    def _desenhar_inicio(self, tela):
        ui.veu(tela, 150)
        topo = 40
        caixa = pygame.Rect(0, topo, 700, ALTURA - topo - 40)
        caixa.centerx = LARGURA // 2
        ui.painel(tela, caixa, (28, 32, 56), self.COR, 22, 5)

        ui.desenhar_texto(tela, self.TITULO, (LARGURA // 2, topo + 28), 30, AMARELO, "midtop")
        self.jogador.desenhar(tela, (caixa.x + 60, topo + 46 + math.sin(self.tempo * 3) * 4), 44)
        self.jogador.desenhar(tela, (caixa.right - 60, topo + 46 + math.cos(self.tempo * 3) * 4),
                              44, espelhar=True)

        y = topo + 92
        for linha in self.INSTRUCOES:
            for sub in ui.quebrar_linhas(linha, 12, caixa.w - 80):
                ui.desenhar_texto(tela, sub, (LARGURA // 2, y), 12, BRANCO, "midtop")
                y += 22
            y += 6

        # ---- Seletor de nível ----
        self._y_seletor = y + 6
        prog = self._progresso()
        liberado = prog["nivel"]
        ys = self._y_seletor
        ui.desenhar_texto(tela, f"NÍVEL {self.nivel + 1} DE {len(NIVEIS)}", (LARGURA // 2, ys), 16,
                          AMARELO, "midtop")
        ui.desenhar_texto(tela, self.nome_nivel, (LARGURA // 2, ys + 24), 10, (180, 200, 255), "midtop")

        # Miniatura do nível
        _, _, mapa = NIVEIS[self.nivel]
        larg, alt = max(len(l) for l in mapa), len(mapa)
        cel = max(8, min(22, 300 // larg, 128 // alt))
        mini = self._miniatura_nivel(self.nivel, self.jogador, cel)
        r = mini.get_rect(center=(LARGURA // 2, ys + 106))
        fundo = r.inflate(20, 16)
        pygame.draw.rect(tela, (70, 48, 28), fundo, border_radius=10)
        pygame.draw.rect(tela, (150, 110, 60), fundo, 3, border_radius=10)
        tela.blit(mini, r)

        # Setas
        esq, dirr = self._layout_seletor()
        for rr, simb, ativo in ((esq, "←", self.nivel > 0), (dirr, "→", self.nivel < liberado)):
            cor = (84, 96, 150) if ativo else (44, 48, 70)
            ui.painel(tela, rr, cor, BRANCO if ativo else (90, 94, 120), 12, 3, sombra=False)
            ui.desenhar_texto(tela, simb, rr.center, 20, BRANCO if ativo else (110, 114, 140), "center")
        # Estrelas deste nível
        feitas = prog["estrelas"][self.nivel]
        ey = fundo.bottom + 20
        for k in range(3):
            c = (LARGURA // 2 - 40 + k * 40, ey)
            ui.estrela(tela, (c[0] + 1, c[1] + 2), 14, (0, 0, 0))
            ui.estrela(tela, c, 14, AMARELO if k < feitas else (70, 74, 100))

        # Total
        y_rec = self.menu_inicio.botoes[0].rect.y - 32
        ui.desenhar_texto(tela, f"★ TOTAL: {self.total_estrelas()} DE {len(NIVEIS) * 3} ★",
                          (LARGURA // 2, y_rec), 14, AMARELO, "midtop")
        self.menu_inicio.desenhar(tela)

    # --------------------------------------------------------
    # TELA DE FIM (estrelas aparecendo uma a uma)
    # --------------------------------------------------------

    def _desenhar_fim(self, tela):
        super()._desenhar_fim(tela)
        caixa_y = ALTURA // 2 + 10 - 280
        y = caixa_y + 246
        for k in range(3):
            c = (LARGURA // 2 - 70 + k * 70, y)
            if k < self.estrelas_mostradas:
                t = self.tempo_estado - (0.5 + k * 0.4)
                esc = min(1.0, t / 0.2) * (1 + 0.3 * math.sin(min(1.0, t / 0.3) * math.pi))
                raio = max(2, int(26 * esc))
                ui.estrela(tela, (c[0] + 2, c[1] + 3), raio, (0, 0, 0))
                ui.estrela(tela, c, raio, AMARELO, math.sin(self.tempo * 3 + k) * 0.1)
            else:
                ui.estrela(tela, c, 26, (70, 74, 100))
