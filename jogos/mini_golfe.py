from core.idioma import t
import math
import random

import pygame

from settings import *
from core import ui
from jogos.base import MiniJogo

# ============================================================
# MINI GOLFE DO OVO
# ============================================================
# O seu ovo é a bolinha! São 9 buracos malucos, vistos de cima,
# com areia, água, moinho, bloco que anda, setas que dão
# velocidade e portais mágicos. Faça o curso com o menor
# número de tacadas (o par total é 27).
#
# Cada buraco é um mapa de 30 x 19 casas de 32 px:
#   #  parede de madeira        .  grama do campo
#   s  areia (freia muito)      w  água (+1 tacada, volta)
#   S  saída (tee)              H  buraco
#   > < ^ v  seta (BOOSTER)     A B  portais (par)
#   X  eixo do moinho           -  grama (vão do moinho)
#   (espaço) fora do campo

CEL = 32
COLS = 30
LINHAS = 19
X0 = (LARGURA - COLS * CEL) // 2          # 32
Y0 = ALTURA - LINHAS * CEL - 16           # 96 (em cima fica o HUD)

# Bolinha (o ovo)
RAIO = 15
ALTURA_OVO = 34

# Física
ATRITO_GRAMA = 220.0
ATRITO_AREIA = 700.0
RESTITUICAO = 0.8
VEL_MAX = 900.0
VEL_PARADO = 8.0
SUBPASSO = 6.0              # px máximos por subpasso (evita atravessar parede)

# Buraco
RAIO_BURACO = 16
VEL_ENTRA = 450.0

# Obstáculos
BOOST = 400.0
VEL_TETO = 1100.0
AMPLITUDE_BLOCO = 80.0
FREQ_BLOCO = 0.5
PA = 90                     # comprimento da pá do moinho
GIRO_MOINHO = math.radians(90)
RAIO_PA = 4
RAIO_EIXO = 10
RAIO_PORTAL = 16

# Mira
GIRO_MIRA = math.radians(120)
GIRO_FINO = math.radians(40)
CICLO_FORCA = 1.6
ARRASTO_MAX = 200           # px de arrasto do mouse = força máxima
LINHA_MIRA = 160

MAX_TACADAS = 8

TECLAS_ESQ = (pygame.K_LEFT, pygame.K_a)
TECLAS_DIR = (pygame.K_RIGHT, pygame.K_d)
TECLAS_TACADA = (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER)
TECLAS_FINO = (pygame.K_LSHIFT, pygame.K_RSHIFT)

# Cores
GRAMA_FORA = (40, 120, 50)
FAIRWAY = (70, 190, 80)
LISTRA = (80, 205, 90)
MADEIRA = (150, 100, 60)
MADEIRA_TOPO = (190, 140, 80)
AREIA = (240, 220, 150)
AREIA_PONTO = (215, 190, 120)
AGUA = (60, 150, 230)
ONDINHA = (140, 200, 255)
BANDEIRA = (230, 60, 60)
TORRE = (220, 220, 230)
PAS = (180, 60, 60)

SETAS = {">": (1, 0), "<": (-1, 0), "^": (0, -1), "v": (0, 1)}
CAMPO = set(".SHABX-") | set(SETAS)

# ============================================================
# OS 9 BURACOS
# ============================================================

BURACOS = [
    # 1 — reta (tutorial)
    dict(par=2, mapa=[
        "", "", "", "", "", "",
        "   ########################",
        "   #......................#",
        "   #......................#",
        "   #..S...............H...#",
        "   #......................#",
        "   #......................#",
        "   ########################",
    ]),
    # 2 — curva em L
    dict(par=3, mapa=[
        "",
        "                  #########",
        "                  #.......#",
        "                  #...H...#",
        "                  #.......#",
        "                  #.......#",
        "                  #.......#",
        "                  #.......#",
        "                  #.......#",
        "                  #.......#",
        "   ################.......#",
        "   #......................#",
        "   #..S...................#",
        "   #......................#",
        "   #......................#",
        "   ########################",
    ]),
    # 3 — muro e anel de areia
    dict(par=3, mapa=[
        "", "", "",
        "  ##########################",
        "  #........................#",
        "  #........................#",
        "  #.........#.....sssss....#",
        "  #.........#....sssssss...#",
        "  #..S......#....ss...ss...#",
        "  #.........#....ss.H.ss...#",
        "  #.........#....ss...ss...#",
        "  #.........#....sss.sss...#",
        "  #........................#",
        "  #........................#",
        "  ##########################",
    ]),
    # 4 — lago no meio
    dict(par=3, mapa=[
        "", "", "", "",
        "   ########################",
        "   #......................#",
        "   #......................#",
        "   #.......wwwwwwww.......#",
        "   #.S.....wwwwwwww....H..#",
        "   #.......wwwwwwww.......#",
        "   #......................#",
        "   #......................#",
        "   ########################",
    ]),
    # 5 — bloco que anda na porta do buraco
    dict(par=3, blocos=[dict(c=14, l=6, w=64, h=32, eixo="x", fase=0.0)], mapa=[
        "",
        "           #######",
        "           #.....#",
        "           #..H..#",
        "           #.....#",
        "        #####...#####",
        "        #...........#",
        "        #...........#",
        "        #...........#",
        "        #...........#",
        "        #...........#",
        "        #...........#",
        "        #...........#",
        "        #.....S.....#",
        "        #...........#",
        "        #############",
    ]),
    # 6 — moinho
    dict(par=3, mapa=[
        "", "", "",
        "   #########################",
        "   #...........#...........#",
        "   #...........#...........#",
        "   #...........#...........#",
        "   #...........#...........#",
        "   #...........-...........#",
        "   #.S.........X........H..#",
        "   #...........-...........#",
        "   #...........#...........#",
        "   #...........#...........#",
        "   #...........#...........#",
        "   #...........#...........#",
        "   #########################",
    ]),
    # 7 — portais
    dict(par=3, mapa=[
        "", "", "", "",
        "  ########    ##############",
        "  #......#    #............#",
        "  #......#    #............#",
        "  #.S..A.#    #.B..#....H..#",
        "  #......#    #............#",
        "  #......#    #............#",
        "  ########    ##############",
    ]),
    # 8 — setas (boosters) em zigue-zague
    dict(par=3, mapa=[
        "", "",
        "   ########################",
        "   #......................#",
        "   #..H...................#",
        "   #......................#",
        "   ##################.....#",
        "                    #^^^^^#",
        "                    #.....#",
        "   ##################.....#",
        "   #........>>............#",
        "   #.S......>>............#",
        "   #........>>............#",
        "   ########################",
    ]),
    # 9 — o grande final: lago, bloco, moinho e areia
    dict(par=4, blocos=[dict(c=22, l=8, w=48, h=32, eixo="x", fase=0.6)], mapa=[
        "",
        "  ##########################",
        "  #......#.................#",
        "  #..s...-.................#",
        "  #.sHs..X.................#",
        "  #..s...-.................#",
        "  #......#.................#",
        "  ################.........#",
        "                 #.........#",
        "  ################.........#",
        "  #........................#",
        "  #........wwwww...........#",
        "  #.S......wwwww...........#",
        "  #........wwwww...........#",
        "  #........................#",
        "  ##########################",
    ]),
]

PAR_TOTAL = sum(b["par"] for b in BURACOS)


def _centro(c, l):
    """Centro da casa (c, l) em pixels."""
    return (X0 + c * CEL + CEL / 2, Y0 + l * CEL + CEL / 2)


def _rect(c, l):
    return pygame.Rect(X0 + c * CEL, Y0 + l * CEL, CEL, CEL)


# ============================================================
# MESA: o campo de um buraco + a física da bolinha
# ============================================================
# Fica separado do desenho para poder simular tacadas (testes).

class Mesa:

    def __init__(self, indice):
        self.indice = indice
        dados = BURACOS[indice]
        self.par = dados["par"]
        mapa = [linha.ljust(COLS) for linha in dados["mapa"]]
        mapa += [" " * COLS] * (LINHAS - len(mapa))
        self.mapa = mapa

        self.inicio = self.alvo = (0, 0)
        self.portais = []
        self.moinhos = []
        self.setas = {}             # (c, l) -> (id da região, direção)
        for l, linha in enumerate(mapa):
            for c, ch in enumerate(linha):
                if ch == "S":
                    self.inicio = _centro(c, l)
                elif ch == "H":
                    self.alvo = _centro(c, l)
                elif ch in "AB":
                    self.portais.append((ch, _centro(c, l)))
                elif ch == "X":
                    self.moinhos.append(_centro(c, l))
        self.portais = [p for _, p in sorted(self.portais)]
        self._regioes_setas()

        self.blocos = []
        for b in dados.get("blocos", []):
            cx, cy = _centro(b["c"], b["l"])
            self.blocos.append(dict(x=cx, y=cy, w=b["w"], h=b["h"], eixo=b["eixo"], fase=b["fase"]))

        self.t = 0.0
        self.colocar(self.inicio)

    def _regioes_setas(self):
        regiao = 0
        for l in range(LINHAS):
            for c in range(COLS):
                ch = self.mapa[l][c]
                if ch in SETAS and (c, l) not in self.setas:
                    regiao += 1
                    pilha = [(c, l)]
                    while pilha:
                        cc, ll = pilha.pop()
                        if (cc, ll) in self.setas or not (0 <= cc < COLS and 0 <= ll < LINHAS):
                            continue
                        if self.mapa[ll][cc] != ch:
                            continue
                        self.setas[(cc, ll)] = (regiao, SETAS[ch])
                        pilha += [(cc + 1, ll), (cc - 1, ll), (cc, ll + 1), (cc, ll - 1)]

    def colocar(self, pos):
        self.x, self.y = pos
        self.vx = self.vy = 0.0
        self.regiao = None          # região de seta em que a bola está
        self.no_portal = False      # acabou de sair de um portal
        self.espirrou = False       # já espirrou nesta passada pelo buraco

    # --------------------------------------------------------

    def casa(self, x, y):
        c = int((x - X0) // CEL)
        l = int((y - Y0) // CEL)
        if 0 <= c < COLS and 0 <= l < LINHAS:
            return self.mapa[l][c]
        return " "

    def solida(self, c, l):
        if 0 <= c < COLS and 0 <= l < LINHAS:
            return self.mapa[l][c] in "# "
        return True

    def velocidade(self):
        return math.hypot(self.vx, self.vy)

    def bloco_rect(self, b, t=None):
        t = self.t if t is None else t
        d = AMPLITUDE_BLOCO * math.sin(math.tau * FREQ_BLOCO * t + b["fase"])
        cx = b["x"] + (d if b["eixo"] == "x" else 0)
        cy = b["y"] + (d if b["eixo"] == "y" else 0)
        return (cx - b["w"] / 2, cy - b["h"] / 2, b["w"], b["h"])

    def bloco_vel(self, b):
        v = AMPLITUDE_BLOCO * math.tau * FREQ_BLOCO * math.cos(math.tau * FREQ_BLOCO * self.t + b["fase"])
        return (v, 0.0) if b["eixo"] == "x" else (0.0, v)

    def pa(self, centro, t=None):
        """Pontas da pá do moinho."""
        t = self.t if t is None else t
        a = GIRO_MOINHO * t
        dx, dy = math.cos(a) * PA / 2, math.sin(a) * PA / 2
        return (centro[0] - dx, centro[1] - dy), (centro[0] + dx, centro[1] + dy)

    # --------------------------------------------------------
    # COLISÕES
    # --------------------------------------------------------

    def _empurrar(self, nx, ny, pen, ovx=0.0, ovy=0.0):
        """Tira a bola de dentro e rebate (velocidade relativa ao objeto)."""
        self.x += nx * pen
        self.y += ny * pen
        rvx, rvy = self.vx - ovx, self.vy - ovy
        vn = rvx * nx + rvy * ny
        if vn < 0:
            rvx -= (1 + RESTITUICAO) * vn * nx
            rvy -= (1 + RESTITUICAO) * vn * ny
            self.vx, self.vy = rvx + ovx, rvy + ovy
            return -vn
        return 0.0

    def _circulo_ret(self, rx, ry, rw, rh):
        """Normal e penetração da bola num retângulo (ou None)."""
        px = min(max(self.x, rx), rx + rw)
        py = min(max(self.y, ry), ry + rh)
        dx, dy = self.x - px, self.y - py
        d2 = dx * dx + dy * dy
        if d2 >= RAIO * RAIO:
            return None
        if d2 > 1e-9:
            d = math.sqrt(d2)
            return dx / d, dy / d, RAIO - d
        # Centro dentro do retângulo: sai pelo lado mais perto
        opcoes = [(self.x - rx, -1, 0), (rx + rw - self.x, 1, 0),
                  (self.y - ry, 0, -1), (ry + rh - self.y, 0, 1)]
        dist, nx, ny = min(opcoes)
        return nx, ny, dist + RAIO

    def _paredes(self):
        impacto = 0.0
        c0 = int((self.x - RAIO - X0) // CEL)
        c1 = int((self.x + RAIO - X0) // CEL)
        l0 = int((self.y - RAIO - Y0) // CEL)
        l1 = int((self.y + RAIO - Y0) // CEL)
        for _ in range(2):
            achou = False
            for l in range(l0, l1 + 1):
                for c in range(c0, c1 + 1):
                    if not self.solida(c, l):
                        continue
                    r = self._circulo_ret(X0 + c * CEL, Y0 + l * CEL, CEL, CEL)
                    if r:
                        impacto = max(impacto, self._empurrar(*r))
                        achou = True
            if not achou:
                break
        return impacto

    def _dentro_bloco(self, b):
        return self._circulo_ret(*self.bloco_rect(b))

    def _obstaculos(self):
        impacto = 0.0
        for b in self.blocos:
            r = self._dentro_bloco(b)
            if r:
                ovx, ovy = self.bloco_vel(b)
                impacto = max(impacto, self._empurrar(*r, ovx, ovy))
        for m in self.moinhos:
            # Eixo (fixo)
            dx, dy = self.x - m[0], self.y - m[1]
            d = math.hypot(dx, dy)
            if d < RAIO + RAIO_EIXO:
                if d < 1e-6:
                    dx, dy, d = 1.0, 0.0, 1.0
                impacto = max(impacto, self._empurrar(dx / d, dy / d, RAIO + RAIO_EIXO - d))
            # Pá girando
            r = self._contra_pa(m)
            if r:
                nx, ny, pen, qx, qy = r
                ovx = -GIRO_MOINHO * (qy - m[1])
                ovy = GIRO_MOINHO * (qx - m[0])
                impacto = max(impacto, self._empurrar(nx, ny, pen, ovx, ovy))
        return impacto

    def _contra_pa(self, m):
        (ax, ay), (bx, by) = self.pa(m)
        ex, ey = bx - ax, by - ay
        s = ((self.x - ax) * ex + (self.y - ay) * ey) / (ex * ex + ey * ey)
        s = max(0.0, min(1.0, s))
        qx, qy = ax + ex * s, ay + ey * s
        dx, dy = self.x - qx, self.y - qy
        d = math.hypot(dx, dy)
        if d >= RAIO + RAIO_PA:
            return None
        if d < 1e-6:
            dx, dy, d = -ey, ex, math.hypot(ex, ey)
        return dx / d, dy / d, RAIO + RAIO_PA - d, qx, qy

    def _desentalar(self):
        """Bola presa entre um obstáculo que anda e a parede: escapa de lado."""
        for b in self.blocos:
            if self._dentro_bloco(b):
                rx, ry, rw, rh = self.bloco_rect(b)
                if b["eixo"] == "x":
                    cy = ry + rh / 2
                    self.y = (ry - RAIO - 1) if self.y < cy else (ry + rh + RAIO + 1)
                    self.vx = self.bloco_vel(b)[0] * 0.5
                else:
                    cx = rx + rw / 2
                    self.x = (rx - RAIO - 1) if self.x < cx else (rx + rw + RAIO + 1)
                    self.vy = self.bloco_vel(b)[1] * 0.5
                self._paredes()
        for m in self.moinhos:
            r = self._contra_pa(m)
            if r and r[2] > 3:
                # Passa para o outro lado da pá (ela "varre" por cima)
                nx, ny, pen, qx, qy = r
                self.x = qx - nx * (RAIO + RAIO_PA + 1)
                self.y = qy - ny * (RAIO + RAIO_PA + 1)
                self._paredes()

    # --------------------------------------------------------
    # PASSO DA FÍSICA
    # --------------------------------------------------------

    def passo(self, dt):
        """
        Avança a física. Devolve uma lista de eventos:
        ("parede", força), ("buraco",), ("agua",), ("seta",),
        ("portal", de, para), ("espirrou",), ("fora",)
        """
        eventos = []
        vel = self.velocidade()
        n = max(1, int(math.ceil(vel * dt / SUBPASSO)))
        h = dt / n
        for _ in range(n):
            self.t += h
            # Atrito (areia freia mais)
            vel = self.velocidade()
            if vel > 0:
                atrito = ATRITO_AREIA if self.casa(self.x, self.y) == "s" else ATRITO_GRAMA
                nova = max(0.0, vel - atrito * h)
                self.vx *= nova / vel
                self.vy *= nova / vel

            self.x += self.vx * h
            self.y += self.vy * h

            impacto = self._obstaculos()
            impacto = max(impacto, self._paredes())
            self._desentalar()
            if impacto > 60:
                eventos.append(("parede", impacto))

            ch = self.casa(self.x, self.y)
            if ch in "# ":
                eventos.append(("fora",))
                return eventos
            if ch == "w":
                eventos.append(("agua",))
                return eventos

            # Buraco
            d = math.hypot(self.x - self.alvo[0], self.y - self.alvo[1])
            if d < RAIO_BURACO:
                if self.velocidade() < VEL_ENTRA:
                    eventos.append(("buraco",))
                    return eventos
                if not self.espirrou:
                    self.espirrou = True
                    a = math.radians(random.choice((-15, 15)))
                    ca, sa = math.cos(a), math.sin(a)
                    self.vx, self.vy = self.vx * ca - self.vy * sa, self.vx * sa + self.vy * ca
                    eventos.append(("espirrou",))
            elif d > RAIO_BURACO + 8:
                self.espirrou = False

            # Setas (BOOSTER): soma velocidade uma vez por passada
            c = int((self.x - X0) // CEL)
            l = int((self.y - Y0) // CEL)
            seta = self.setas.get((c, l))
            if seta:
                if seta[0] != self.regiao:
                    self.regiao = seta[0]
                    self.vx += seta[1][0] * BOOST
                    self.vy += seta[1][1] * BOOST
                    vel = self.velocidade()
                    if vel > VEL_TETO:
                        self.vx *= VEL_TETO / vel
                        self.vy *= VEL_TETO / vel
                    eventos.append(("seta",))
            else:
                self.regiao = None

            # Portais: sai no outro com a mesma velocidade
            if len(self.portais) == 2:
                perto = [math.hypot(self.x - p[0], self.y - p[1]) for p in self.portais]
                if self.no_portal:
                    if min(perto) > RAIO_PORTAL + 12:
                        self.no_portal = False
                else:
                    for i in (0, 1):
                        if perto[i] < RAIO_PORTAL:
                            de, para = self.portais[i], self.portais[1 - i]
                            self.x, self.y = para
                            self.no_portal = True
                            eventos.append(("portal", de, para))
                            break

        if self.velocidade() < VEL_PARADO:
            self.vx = self.vy = 0.0
        return eventos

    def tacada(self, angulo, forca):
        v = max(40.0, forca * VEL_MAX)
        self.vx = math.cos(angulo) * v
        self.vy = math.sin(angulo) * v
        self.espirrou = False

    def raio_mira(self, angulo, comprimento=LINHA_MIRA):
        """Pontos da linha de mira, com o 1º rebote nas paredes."""
        x, y = self.x, self.y
        dx, dy = math.cos(angulo), math.sin(angulo)
        pontos = [(x, y)]
        rebote = None
        andou = 0.0
        passo = 4.0
        salvo = (self.x, self.y)
        while andou < comprimento:
            nx, ny = x + dx * passo, y + dy * passo
            self.x, self.y = nx, ny
            normal = None
            c0 = int((nx - RAIO - X0) // CEL)
            c1 = int((nx + RAIO - X0) // CEL)
            l0 = int((ny - RAIO - Y0) // CEL)
            l1 = int((ny + RAIO - Y0) // CEL)
            for l in range(l0, l1 + 1):
                for c in range(c0, c1 + 1):
                    if self.solida(c, l):
                        r = self._circulo_ret(X0 + c * CEL, Y0 + l * CEL, CEL, CEL)
                        if r:
                            normal = r
                            break
                if normal:
                    break
            if normal and rebote is None:
                n_x, n_y, _ = normal
                vn = dx * n_x + dy * n_y
                if vn < 0:
                    dx, dy = dx - 2 * vn * n_x, dy - 2 * vn * n_y
                rebote = (x, y)
                pontos.append((x, y))
                continue
            elif normal:
                break
            x, y = nx, ny
            andou += passo
        pontos.append((x, y))
        self.x, self.y = salvo
        return pontos, rebote


# ============================================================
# DESENHO DO CAMPO (com cache)
# ============================================================

_cache = {}


def _grama_fora():
    s = _cache.get("grama")
    if s is not None:
        return s
    s = pygame.Surface((LARGURA, ALTURA))
    s.fill(GRAMA_FORA)
    rnd = random.Random(7)
    for _ in range(700):
        x, y = rnd.randrange(LARGURA), rnd.randrange(ALTURA)
        pygame.draw.line(s, (34, 104, 44), (x, y), (x + rnd.randint(-2, 2), y - 5), 2)
    for _ in range(90):
        x, y = rnd.randrange(LARGURA), rnd.randrange(ALTURA)
        cor = rnd.choice(((255, 255, 255), (255, 230, 90)))
        pygame.draw.circle(s, cor, (x, y), 3)
        pygame.draw.circle(s, (255, 200, 60) if cor[2] > 200 else (255, 255, 255), (x, y), 1)
    _cache["grama"] = s
    return s


def _listras():
    s = _cache.get("listras")
    if s is not None:
        return s
    s = pygame.Surface((LARGURA, ALTURA))
    s.fill(FAIRWAY)
    for i in range(-ALTURA // 40 - 1, LARGURA // 40 + 2, 2):
        x = i * 40
        pygame.draw.polygon(s, LISTRA, [(x, 0), (x + 40, 0), (x + 40 + ALTURA, ALTURA), (x + ALTURA, ALTURA)])
    _cache["listras"] = s
    return s


def _curso(indice):
    """Campo do buraco (estático) desenhado uma vez só."""
    chave = ("curso", indice)
    s = _cache.get(chave)
    if s is not None:
        return s
    mesa = Mesa(indice)
    mapa = mesa.mapa
    s = _grama_fora().copy()
    listras = _listras()
    rnd = random.Random(indice * 13 + 1)

    def e_parede(c, l):
        return 0 <= c < COLS and 0 <= l < LINHAS and mapa[l][c] == "#"

    # Chão
    for l in range(LINHAS):
        for c in range(COLS):
            ch = mapa[l][c]
            r = _rect(c, l)
            if ch in CAMPO or ch == "w":
                s.blit(listras, r, r)
            if ch == "s":
                pygame.draw.rect(s, AREIA, r)
                for _ in range(6):
                    pygame.draw.circle(s, AREIA_PONTO, (r.x + rnd.randrange(3, 29), r.y + rnd.randrange(3, 29)), 1)
            elif ch == "w":
                pygame.draw.rect(s, AGUA, r)

    # Borda de areia e água um pouco arredondada (contorno mais escuro)
    for l in range(LINHAS):
        for c in range(COLS):
            ch = mapa[l][c]
            if ch not in "sw":
                continue
            r = _rect(c, l)
            borda = (200, 180, 110) if ch == "s" else (40, 110, 190)
            for dc, dl, lado in ((0, -1, (r.topleft, r.topright)), (0, 1, (r.bottomleft, r.bottomright)),
                                 (-1, 0, (r.topleft, r.bottomleft)), (1, 0, (r.topright, r.bottomright))):
                cc, ll = c + dc, l + dl
                viz = mapa[ll][cc] if 0 <= cc < COLS and 0 <= ll < LINHAS else " "
                if viz != ch and viz != "#":
                    pygame.draw.line(s, borda, lado[0], lado[1], 3)

    # Sombra das paredes no chão
    sombra = pygame.Surface((CEL, 6), pygame.SRCALPHA)
    sombra.fill((0, 0, 0, 60))
    for l in range(LINHAS):
        for c in range(COLS):
            if mapa[l][c] == "#" and l + 1 < LINHAS and mapa[l + 1][c] in CAMPO | {"s", "w"}:
                s.blit(sombra, (X0 + c * CEL, Y0 + (l + 1) * CEL))

    # Paredes de madeira: base escura + topo claro contínuo
    for l in range(LINHAS):
        for c in range(COLS):
            if mapa[l][c] == "#":
                pygame.draw.rect(s, MADEIRA, _rect(c, l))
    for l in range(LINHAS):
        for c in range(COLS):
            if mapa[l][c] != "#":
                continue
            r = _rect(c, l)
            x0 = r.x if e_parede(c - 1, l) else r.x + 5
            x1 = r.right if e_parede(c + 1, l) else r.right - 5
            y0 = r.y if e_parede(c, l - 1) else r.y + 4
            y1 = r.bottom if e_parede(c, l + 1) else r.bottom - 6
            pygame.draw.rect(s, MADEIRA_TOPO, (x0, y0, x1 - x0, y1 - y0))
            # Veios da madeira
            if rnd.random() < 0.5:
                yy = rnd.randrange(y0 + 3, max(y0 + 4, y1 - 3))
                pygame.draw.line(s, (170, 120, 66), (x0 + 3, yy), (x1 - 3, yy), 1)
    # Contorno escuro das paredes
    for l in range(LINHAS):
        for c in range(COLS):
            if mapa[l][c] != "#":
                continue
            r = _rect(c, l)
            if not e_parede(c, l - 1):
                pygame.draw.line(s, (110, 70, 40), r.topleft, (r.right - 1, r.top), 2)
            if not e_parede(c, l + 1):
                pygame.draw.line(s, (100, 62, 34), (r.left, r.bottom - 2), (r.right - 1, r.bottom - 2), 3)
            if not e_parede(c - 1, l):
                pygame.draw.line(s, (110, 70, 40), r.topleft, (r.left, r.bottom - 1), 2)
            if not e_parede(c + 1, l):
                pygame.draw.line(s, (110, 70, 40), (r.right - 2, r.top), (r.right - 2, r.bottom - 1), 2)

    # Marcadores da saída (duas bolinhas, como no golfe de verdade)
    x, y = int(mesa.inicio[0]), int(mesa.inicio[1])
    pygame.draw.circle(s, (60, 165, 70), (x, y), 20)
    for dx in (-27, 27):
        pygame.draw.circle(s, (40, 90, 50), (x + dx, y + 2), 5)
        pygame.draw.circle(s, (245, 245, 245), (x + dx, y), 5)

    # Moinho: as paredes dos dois lados do vão viram a casinha branca
    for m in mesa.moinhos:
        c = int((m[0] - X0) // CEL)
        l = int((m[1] - Y0) // CEL)
        for dl in (-2, 2):
            if not e_parede(c, l + dl):
                continue
            r = _rect(c, l + dl).inflate(8, 0)
            pygame.draw.rect(s, (130, 130, 150), r.move(0, 3), border_radius=4)
            pygame.draw.rect(s, TORRE, r, border_radius=4)
            pygame.draw.rect(s, (150, 150, 165), r, 2, border_radius=4)
            # Telhadinho vermelho e janela
            pygame.draw.rect(s, PAS, (r.x + 3, r.y + 3, r.w - 6, 8), border_radius=3)
            pygame.draw.rect(s, (120, 150, 200), (r.centerx - 5, r.y + 15, 10, 10), border_radius=2)
            pygame.draw.line(s, TORRE, (r.centerx, r.y + 15), (r.centerx, r.y + 24), 1)

    # Trilho dos blocos que andam
    for b in mesa.blocos:
        if b["eixo"] == "x":
            y = int(b["y"])
            pygame.draw.line(s, (50, 150, 60), (b["x"] - AMPLITUDE_BLOCO - b["w"] / 2, y),
                             (b["x"] + AMPLITUDE_BLOCO + b["w"] / 2, y), 6)
        else:
            x = int(b["x"])
            pygame.draw.line(s, (50, 150, 60), (x, b["y"] - AMPLITUDE_BLOCO - b["h"] / 2),
                             (x, b["y"] + AMPLITUDE_BLOCO + b["h"] / 2), 6)

    # Buraco
    hx, hy = int(mesa.alvo[0]), int(mesa.alvo[1])
    pygame.draw.circle(s, (230, 240, 230), (hx, hy), RAIO_BURACO + 3)
    pygame.draw.circle(s, (10, 10, 10), (hx, hy), RAIO_BURACO)
    pygame.draw.circle(s, (40, 40, 40), (hx, hy + 3), RAIO_BURACO - 5)

    try:
        s = s.convert()
    except pygame.error:
        pass                    # sem janela (simulação nos testes)
    _cache[chave] = s
    return s


_sombra_bola = None


def _sombra():
    global _sombra_bola
    if _sombra_bola is None:
        _sombra_bola = pygame.Surface((34, 14), pygame.SRCALPHA)
        pygame.draw.ellipse(_sombra_bola, (0, 0, 0, 70), _sombra_bola.get_rect())
    return _sombra_bola


def _nome_resultado(tacadas, par):
    if tacadas == 1:
        return "BURACO EM UM!"
    d = tacadas - par
    if d <= -2:
        return "ÁGUIA!"
    if d == -1:
        return "PASSARINHO!"
    if d == 0:
        return "NO PAR!"
    if d == 1:
        return "QUASE!"
    return "CONSEGUIU!"


def _carinha(tela, centro, humor, raio=11):
    """Carinha do placar: 2 = feliz, 1 = normal, 0 = triste."""
    x, y = int(centro[0]), int(centro[1])
    cor = ((240, 120, 120), (250, 210, 80), (120, 220, 110))[humor]
    pygame.draw.circle(tela, ui.escurecer(cor, 80), (x, y), raio + 2)
    pygame.draw.circle(tela, cor, (x, y), raio)
    pygame.draw.circle(tela, (30, 30, 30), (x - 4, y - 3), 2)
    pygame.draw.circle(tela, (30, 30, 30), (x + 4, y - 3), 2)
    if humor == 2:
        pygame.draw.arc(tela, (30, 30, 30), (x - 6, y - 4, 12, 10), math.pi + 0.3, math.tau - 0.3, 2)
    elif humor == 1:
        pygame.draw.line(tela, (30, 30, 30), (x - 4, y + 4), (x + 4, y + 4), 2)
    else:
        pygame.draw.arc(tela, (30, 30, 30), (x - 6, y + 2, 12, 10), 0.3, math.pi - 0.3, 2)


# ============================================================
# JOGO
# ============================================================

class MiniGolfe(MiniJogo):

    ID = "mini_golfe"
    TITULO = "MINI GOLFE DO OVO"
    TITULO_CURTO = "MINI GOLFE"
    DESCRICAO = "O seu ovo é a bolinha! 9 buracos malucos com moinho, água, areia e portais."
    COR = (70, 170, 80)
    INSTRUCOES = [
        "O seu ovo é a bolinha: acerte os 9 buracos!",
        "Use poucas tacadas. Água custa +1 tacada.",
        "Setas dão velocidade e os portais teletransportam.",
        "← → (ou A D) mira, SHIFT = mira fina",
        "ESPAÇO: segure e solte • MOUSE: puxe e solte",
    ]
    OPCOES = None
    MENOR_MELHOR = True
    ROTULO_PONTOS = "TACADAS"
    CONTAGEM = True

    MOEDAS_MIN = 1

    # --------------------------------------------------------

    @classmethod
    def criar_fundo(cls, jogador):
        return _curso(5).copy()

    @classmethod
    def desenhar_icone(cls, sup, jogador):
        # O fundo é o buraco 6 (moinho): posições convertidas para a miniatura
        w, h = sup.get_size()
        ex, ey = w / LARGURA, h / ALTURA
        mesa = Mesa(5)
        hx, hy = int(mesa.alvo[0] * ex), int(mesa.alvo[1] * ey)
        pygame.draw.line(sup, BRANCO, (hx, hy), (hx, hy - 30), 2)
        pygame.draw.polygon(sup, BANDEIRA, [(hx + 1, hy - 30), (hx + 18, hy - 25), (hx + 1, hy - 20)])
        mx, my = mesa.moinhos[0]
        mx, my = int(mx * ex), int(my * ey)
        pygame.draw.line(sup, PAS, (mx - 10, my - 12), (mx + 10, my + 12), 4)
        pygame.draw.circle(sup, TORRE, (mx, my), 4)
        sx, sy = int(mesa.inicio[0] * ex), int(mesa.inicio[1] * ey)
        for i in range(4):
            pygame.draw.circle(sup, BRANCO, (sx + 18 + i * 9, sy), 2)
        jogador.desenhar(sup, (sx, sy), 22, angulo=-20)

    def calcular_moedas(self, valor, venceu):
        if not venceu:
            return self.MOEDAS_MIN
        base = max(5, min(26, 26 - 2 * (valor - PAR_TOTAL)))
        return base + min(4, 2 * self.em_um)

    # --------------------------------------------------------
    # PARTIDA
    # --------------------------------------------------------

    def reiniciar(self):
        self.placar = []            # tacadas de cada buraco já feito
        self.em_um = 0
        self.teclas = set()
        self._carregar_buraco(0)

    def _carregar_buraco(self, indice):
        self.buraco = indice
        self.mesa = Mesa(indice)
        _curso(indice)
        self.tacadas = 0
        hx, hy = self.mesa.alvo
        sx, sy = self.mesa.inicio
        self.mira = math.atan2(hy - sy, hx - sx)
        # banner, mirar, rolando, agua, caindo, festa (o 1º buraco já tem a contagem)
        self.fase = "banner" if indice > 0 else "mirar"
        self.tempo_fase = 0.0
        self.ultima_parada = self.mesa.inicio
        self.carregando = False
        self.tempo_carga = 0.0
        self.forca = 0.0
        self.arrastando = False
        self.arrasto = ((0, 0), (0, 0))
        self.giro = 0.0
        self.squash = 0.0
        self.pos_queda = (0, 0)
        self.resultado = ""
        self.pontos = sum(self.placar)

    def _mudar_fase(self, fase):
        self.fase = fase
        self.tempo_fase = 0.0

    # --------------------------------------------------------
    # CONTROLES
    # --------------------------------------------------------

    def evento(self, e):
        # Acompanha as teclas em qualquer estado (não "grudam" na pausa)
        if e.type == pygame.KEYDOWN:
            self.teclas.add(e.key)
        elif e.type == pygame.KEYUP:
            self.teclas.discard(e.key)
            if e.key in TECLAS_TACADA and self.estado != "jogando":
                self.carregando = False
        elif e.type == pygame.WINDOWFOCUSLOST:
            self.teclas.clear()
            self.carregando = False
            self.arrastando = False
        elif e.type == pygame.MOUSEBUTTONUP and self.estado != "jogando":
            self.arrastando = False
        super().evento(e)

    def evento_jogo(self, e):
        pode = self.fase == "mirar"
        if e.type == pygame.KEYDOWN and e.key in TECLAS_TACADA:
            if pode and not self.arrastando:
                self.carregando = True
                self.tempo_carga = 0.0
                self.forca = 0.0
        elif e.type == pygame.KEYUP and e.key in TECLAS_TACADA:
            if self.carregando and pode:
                self._tacar(self.mira, self.forca)
            self.carregando = False
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if pode and not self.carregando:
                self.arrastando = True
                self.arrasto = (e.pos, e.pos)
        elif e.type == pygame.MOUSEMOTION and self.arrastando:
            self.arrasto = (self.arrasto[0], e.pos)
            self._mira_mouse()
        elif e.type == pygame.MOUSEBUTTONUP and e.button == 1 and self.arrastando:
            self.arrastando = False
            self.arrasto = (self.arrasto[0], e.pos)
            dx, dy, dist = self._vetor_arrasto()
            if pode and dist > 12:
                self._mira_mouse()
                self._tacar(self.mira, self.forca)

    def _vetor_arrasto(self):
        (x0, y0), (x1, y1) = self.arrasto
        dx, dy = x0 - x1, y0 - y1
        return dx, dy, math.hypot(dx, dy)

    def _mira_mouse(self):
        dx, dy, dist = self._vetor_arrasto()
        if dist > 4:
            self.mira = math.atan2(dy, dx)
        self.forca = min(1.0, dist / ARRASTO_MAX)

    def _tacar(self, angulo, forca):
        self.ultima_parada = (self.mesa.x, self.mesa.y)
        self.mesa.tacada(angulo, forca)
        self.tacadas += 1
        self.pontos = sum(self.placar) + self.tacadas
        self.forca = 0.0
        self._mudar_fase("rolando")
        self.som("bater", 0.4 + 0.5 * forca)

    # --------------------------------------------------------
    # LÓGICA
    # --------------------------------------------------------

    def atualizar_jogo(self, dt):
        self.tempo_fase += dt
        self.squash = max(0.0, self.squash - dt)
        fase = self.fase

        if fase == "banner":
            self.mesa.t += dt
            if self.tempo_fase > 1.3:
                self._mudar_fase("mirar")
            return

        if fase == "mirar":
            fino = any(t in self.teclas for t in TECLAS_FINO)
            giro = (GIRO_FINO if fino else GIRO_MIRA) * dt
            if not self.arrastando:
                if any(t in self.teclas for t in TECLAS_ESQ):
                    self.mira -= giro
                if any(t in self.teclas for t in TECLAS_DIR):
                    self.mira += giro
            if self.carregando:
                self.tempo_carga += dt
                f = (self.tempo_carga % CICLO_FORCA) / CICLO_FORCA
                self.forca = f * 2 if f < 0.5 else 2 - f * 2

        if fase in ("mirar", "rolando"):
            self._fisica(dt)
        elif fase == "agua":
            self.mesa.t += dt
            if int(self.tempo_fase * 12) % 3 == 0:
                x, y = self.mesa.x, self.mesa.y
                self.particulas.explodir((x + random.uniform(-12, 12), y), [(200, 235, 255)], 1, 40, 0.5,
                                         (2, 4), gravidade=-120)
            if self.tempo_fase > 1.1:
                self.tacadas += 1
                self.pontos = sum(self.placar) + self.tacadas
                self.textos.adicionar(t("+1 TACADA"), (self.ultima_parada[0], self.ultima_parada[1] - 30),
                                      (200, 235, 255), 12)
                self.mesa.colocar(self.ultima_parada)
                self._parou()
        elif fase == "caindo":
            self.mesa.t += dt
            if self.tempo_fase > 0.4:
                self._comemorar()
        elif fase == "festa":
            self.mesa.t += dt
            if self.tacadas == 1 and int(self.tempo_fase * 4) != int((self.tempo_fase - dt) * 4):
                cores = [AMARELO, BRANCO, self.jogador.cor, (255, 120, 160), (120, 200, 255)]
                pos = (self.mesa.alvo[0] + random.uniform(-120, 120), self.mesa.alvo[1] + random.uniform(-90, 30))
                self.particulas.explodir(pos, cores, 24, 260, 0.9)
            duracao = 2.6 if self.tacadas == 1 else 1.7
            if self.tempo_fase > duracao:
                self._proximo_buraco()

    def _fisica(self, dt):
        m = self.mesa
        antes = (m.x, m.y)
        eventos = m.passo(dt)
        andou = math.hypot(m.x - antes[0], m.y - antes[1])
        if andou > 0:
            lado = 1 if m.vx >= 0 else -1
            self.giro -= math.degrees(andou / RAIO) * lado

        for ev in eventos:
            tipo = ev[0]
            if tipo == "parede":
                self.squash = 0.12
                self.som("boing" if ev[1] > 250 else "clique", min(1.0, 0.25 + ev[1] / 800))
                if ev[1] > 250:
                    self.particulas.explodir((m.x, m.y), [MADEIRA_TOPO, BRANCO], 6, 120, 0.4, (2, 4))
            elif tipo == "seta":
                self.som("mola", 0.6)
                self.particulas.explodir((m.x, m.y), [AMARELO, BRANCO], 10, 160, 0.4, (2, 4))
            elif tipo == "portal":
                self.som("revelar", 0.8)
                for p in ev[1:]:
                    self.particulas.explodir(p, [(190, 120, 255), (120, 220, 255), BRANCO], 18, 200, 0.6)
            elif tipo == "espirrou":
                self.som("erro", 0.5)
                self.textos.adicionar(t("RÁPIDO DEMAIS!"), (m.alvo[0], m.alvo[1] - 40), (255, 200, 120), 12)
            elif tipo == "agua":
                self._mudar_fase("agua")
                self.som("bater", 0.7)
                self.textos.adicionar(t("GLUB!"), (m.x, m.y - 36), (200, 235, 255), 18)
                self.particulas.explodir((m.x, m.y), [(120, 200, 255), (220, 245, 255), AGUA], 26, 240, 0.7)
                m.vx = m.vy = 0.0
                return
            elif tipo == "fora":
                # Segurança: nunca deve acontecer (as paredes seguram)
                m.colocar(self.ultima_parada)
                self._parou()
                return
            elif tipo == "buraco":
                self.pos_queda = (m.x, m.y)
                m.vx = m.vy = 0.0
                self._mudar_fase("caindo")
                self.som("moeda", 0.9)
                return

        if self.fase == "mirar" and m.velocidade() > 0:
            # Empurrado por um obstáculo (bloco/moinho): rola sem contar tacada
            self._mudar_fase("rolando")
        elif self.fase == "rolando" and m.velocidade() == 0:
            self._parou()

    def _parou(self):
        self._mudar_fase("mirar")
        self.carregando = False
        if self.tacadas >= MAX_TACADAS:
            # Limite: conta 9 e vai para o próximo buraco
            self.tacadas = MAX_TACADAS + 1
            self.pontos = sum(self.placar) + self.tacadas
            self.resultado = "LIMITE DE TACADAS"
            self.som("erro", 0.6)
            self._mudar_fase("festa")
            self.tempo_fase = 0.5

    def _comemorar(self):
        self.resultado = _nome_resultado(self.tacadas, self.mesa.par)
        pos = self.mesa.alvo
        cores = [AMARELO, BRANCO, self.jogador.cor, self.jogador.cor_clara]
        self.particulas.explodir(pos, cores, 40, 320, 1.0)
        if self.tacadas == 1:
            self.em_um += 1
            self.tremer(0.2)
            self.som("vencer", 0.8)
        elif self.tacadas <= self.mesa.par:
            self.som("acerto", 0.8)
        else:
            self.som("ponto", 0.8)
        self._mudar_fase("festa")

    def _proximo_buraco(self):
        self.placar.append(self.tacadas)
        self.pontos = sum(self.placar)
        if len(self.placar) >= len(BURACOS):
            total = self.pontos
            self.terminar(venceu=True, valor=total, titulo=t("CURSO COMPLETO!"),
                          linhas=[t("TOTAL: {n}   (PAR {par})", n=total, par=PAR_TOTAL), "", "", "", ""])
            return
        self._carregar_buraco(len(self.placar))

    # --------------------------------------------------------
    # DESENHO
    # --------------------------------------------------------

    def _desenhar_ovo(self, tela, centro, escala=1.0, angulo=0.0):
        img = self.jogador.avatar(ALTURA_OVO)
        lado = img.get_width()
        sx = sy = escala
        if self.squash > 0:
            k = math.sin(self.squash / 0.12 * math.pi)
            sx, sy = escala * (1 + 0.2 * k), escala * (1 - 0.2 * k)
        if abs(sx - 1) > 0.01 or abs(sy - 1) > 0.01:
            img = pygame.transform.smoothscale(img, (max(1, round(lado * sx)), max(1, round(lado * sy))))
        if angulo:
            img = pygame.transform.rotate(img, angulo)
        tela.blit(img, img.get_rect(center=(round(centro[0]), round(centro[1] - 1))))

    def _desenhar_bandeira(self, tela):
        hx, hy = self.mesa.alvo
        hx, hy = int(hx), int(hy)
        onda = math.sin(self.tempo * 5) * 3
        pygame.draw.line(tela, (60, 60, 60), (hx + 2, hy), (hx + 2, hy - 58), 3)
        pygame.draw.line(tela, BRANCO, (hx, hy), (hx, hy - 60), 3)
        pygame.draw.polygon(tela, BANDEIRA, [(hx + 1, hy - 60), (hx + 30, hy - 52 + onda), (hx + 1, hy - 42)])
        pygame.draw.polygon(tela, (170, 30, 30), [(hx + 1, hy - 60), (hx + 30, hy - 52 + onda), (hx + 1, hy - 42)], 2)

    def _desenhar_objetos(self, tela):
        m = self.mesa
        t = self.tempo

        # Ondinhas da água
        for l in range(LINHAS):
            linha = m.mapa[l]
            for c in range(COLS):
                if linha[c] == "w":
                    x = X0 + c * CEL + (c * 7 + l * 5) % 14 + 2
                    y = Y0 + l * CEL + 10 + int(math.sin(t * 2 + c + l * 1.7) * 4)
                    pygame.draw.arc(tela, ONDINHA, (x, y, 16, 8), 0.4, math.pi - 0.4, 2)

        # Setas (piscam andando na direção)
        for (c, l), (_, (dx, dy)) in m.setas.items():
            r = _rect(c, l)
            pygame.draw.rect(tela, (60, 70, 110), r.inflate(-2, -2), border_radius=4)
            fase = (t * 2.5 - (c * dx + l * dy) * 0.25) % 1
            cor = ui.misturar((255, 220, 60), (255, 120, 40), fase)
            cx, cy = r.center
            p = [(-6, -8), (4, 0), (-6, 8)]
            pts = [(cx + px * dx - py * dy, cy + px * dy + py * dx) for px, py in p]
            pygame.draw.lines(tela, cor, False, pts, 4)

        # Portais (anéis girando)
        for i, (px, py) in enumerate(m.portais):
            cor = (190, 120, 255) if i == 0 else (90, 200, 255)
            for k in range(3):
                raio = int(22 - k * 6 + math.sin(t * 4 + k) * 2)
                pygame.draw.circle(tela, ui.misturar(cor, BRANCO, k * 0.3), (int(px), int(py)), raio, 3)
            for k in range(4):
                a = t * 3 * (1 if i == 0 else -1) + k * math.pi / 2
                pygame.draw.circle(tela, BRANCO, (int(px + math.cos(a) * 16), int(py + math.sin(a) * 16)), 2)

        # Blocos que andam
        for b in m.blocos:
            rx, ry, rw, rh = m.bloco_rect(b)
            r = pygame.Rect(round(rx), round(ry), round(rw), round(rh))
            pygame.draw.rect(tela, (0, 0, 0), r.move(0, 4), border_radius=6)
            pygame.draw.rect(tela, (90, 110, 200), r, border_radius=6)
            pygame.draw.rect(tela, (140, 160, 240), r.inflate(-8, -8), border_radius=4)
            pygame.draw.rect(tela, (40, 50, 120), r, 3, border_radius=6)
            for k in range(-1, 2):
                pygame.draw.line(tela, (230, 230, 80), (r.centerx + k * 12 - 4, r.y + 6),
                                 (r.centerx + k * 12 + 4, r.bottom - 6), 3)

    def _desenhar_moinhos(self, tela):
        m = self.mesa
        for centro in m.moinhos:
            a, b = m.pa(centro)
            cx, cy = int(centro[0]), int(centro[1])
            # Pá (sombra + pá vermelha)
            pygame.draw.line(tela, (0, 0, 0), (a[0] + 3, a[1] + 5), (b[0] + 3, b[1] + 5), 10)
            pygame.draw.line(tela, (120, 30, 30), a, b, 12)
            pygame.draw.line(tela, PAS, a, b, 8)
            # Grade das velas
            for s in (0.15, 0.3, 0.7, 0.85):
                px = a[0] + (b[0] - a[0]) * s
                py = a[1] + (b[1] - a[1]) * s
                pygame.draw.circle(tela, (230, 200, 200), (int(px), int(py)), 2)
            pygame.draw.circle(tela, (100, 100, 115), (cx, cy + 2), RAIO_EIXO + 2)
            pygame.draw.circle(tela, TORRE, (cx, cy), RAIO_EIXO)
            pygame.draw.circle(tela, (150, 150, 165), (cx, cy), 4)

    def _desenhar_bola(self, tela):
        m = self.mesa
        fase = self.fase
        if fase == "caindo":
            s = min(1.0, self.tempo_fase / 0.4)
            ax, ay = self.pos_queda
            hx, hy = m.alvo
            ang = s * math.pi * 3
            raio = (1 - s) * 10
            x = ax + (hx - ax) * s + math.cos(ang) * raio
            y = ay + (hy - ay) * s + math.sin(ang) * raio
            self._desenhar_ovo(tela, (x, y), max(0.05, 1 - s), self.giro + s * 720)
            return
        if fase == "festa":
            if self.tacadas == 1:
                # BURACO EM UM: o ovo pula do buraco dançando!
                hx, hy = m.alvo
                pulo = abs(math.sin(self.tempo_fase * 6)) * 40
                ang = math.sin(self.tempo_fase * 10) * 20
                self._desenhar_ovo(tela, (hx, hy - 10 - pulo), 1.2, ang)
            return
        if fase == "agua":
            x, y = m.x, m.y
            bob = math.sin(self.tempo_fase * 7) * 2
            afunda = min(1.0, self.tempo_fase * 2)
            img = self.jogador.avatar(ALTURA_OVO)
            corte = int(img.get_height() * (0.55 + 0.3 * (1 - afunda)))
            img = img.subsurface((0, 0, img.get_width(), corte))
            tela.blit(img, (round(x - img.get_width() / 2), round(y - img.get_height() * 0.55 + bob + 4)))
            pygame.draw.ellipse(tela, ONDINHA, (int(x - 20), int(y + 2 + bob), 40, 10), 2)
            return

        sombra = _sombra()
        tela.blit(sombra, sombra.get_rect(center=(int(m.x + 3), int(m.y + 14))))
        self._desenhar_ovo(tela, (m.x, m.y), 1.0, self.giro)

    def _desenhar_mira(self, tela):
        m = self.mesa
        pontos, rebote = m.raio_mira(self.mira)
        # Pontilhado
        total = 0.0
        prox = 14.0
        for a, b in zip(pontos, pontos[1:]):
            seg = math.hypot(b[0] - a[0], b[1] - a[1])
            while prox <= total + seg and seg > 0:
                s = (prox - total) / seg
                p = (a[0] + (b[0] - a[0]) * s, a[1] + (b[1] - a[1]) * s)
                pygame.draw.circle(tela, (20, 60, 30), (int(p[0]) + 1, int(p[1]) + 2), 4)
                pygame.draw.circle(tela, BRANCO, (int(p[0]), int(p[1])), 4)
                prox += 12
            total += seg
        if rebote:
            pygame.draw.circle(tela, AMARELO, (int(rebote[0]), int(rebote[1])), 7, 2)
        # Setinha na ponta
        fim = pontos[-1]
        if len(pontos) >= 2:
            a = pontos[-2]
            ang = math.atan2(fim[1] - a[1], fim[0] - a[0])
            pts = [(fim[0] + math.cos(ang) * 8, fim[1] + math.sin(ang) * 8),
                   (fim[0] + math.cos(ang + 2.5) * 8, fim[1] + math.sin(ang + 2.5) * 8),
                   (fim[0] + math.cos(ang - 2.5) * 8, fim[1] + math.sin(ang - 2.5) * 8)]
            pygame.draw.polygon(tela, BRANCO, pts)

    def _desenhar_forca(self, tela):
        m = self.mesa
        f = self.forca
        altura = 90
        x = m.x + 34 if m.x < LARGURA - 90 else m.x - 48
        y = max(Y0 + 4, min(ALTURA - altura - 8, m.y - altura / 2))
        r = pygame.Rect(int(x), int(y), 16, altura)
        pygame.draw.rect(tela, (20, 24, 40), r.inflate(6, 6), border_radius=6)
        if f > 0:
            cor = ui.misturar((80, 220, 80), (255, 220, 50), f * 2) if f < 0.5 else \
                ui.misturar((255, 220, 50), (240, 60, 50), (f - 0.5) * 2)
            h = int((altura - 4) * f)
            pygame.draw.rect(tela, cor, (r.x + 2, r.bottom - 2 - h, r.w - 4, h), border_radius=4)
        pygame.draw.rect(tela, BRANCO, r.inflate(6, 6), 2, border_radius=6)
        if self.arrastando:
            # Elástico do estilingue
            (x0, y0), (x1, y1) = self.arrasto
            dx, dy = x1 - x0, y1 - y0
            pygame.draw.line(tela, (255, 255, 255), (int(m.x), int(m.y)), (int(m.x + dx), int(m.y + dy)), 2)
            pygame.draw.circle(tela, BRANCO, (int(m.x + dx), int(m.y + dy)), 5, 2)

    def desenhar_jogo(self, tela):
        tela.blit(_curso(self.buraco), (0, 0))
        self._desenhar_objetos(tela)

        if self.estado == "jogando" and self.fase == "mirar":
            self._desenhar_mira(tela)
        self._desenhar_bandeira(tela)
        self._desenhar_bola(tela)
        self._desenhar_moinhos(tela)
        if self.estado == "jogando" and self.fase == "mirar" and (self.carregando or self.arrastando):
            self._desenhar_forca(tela)

        self.particulas.desenhar(tela)
        self.textos.desenhar(tela)

        if self.fase == "banner" and self.estado == "jogando":
            self._desenhar_banner(tela)
        elif self.fase == "festa" and self.resultado:
            cor = AMARELO if self.tacadas <= self.mesa.par else BRANCO
            ui.desenhar_texto(tela, t(self.resultado), (LARGURA // 2, Y0 + 40), 28, cor, "midtop")
            ui.desenhar_texto(tela, t("{n} TACADAS" if self.tacadas > 1 else "{n} TACADA", n=self.tacadas),
                              (LARGURA // 2, Y0 + 84), 14, BRANCO, "midtop")

    def _desenhar_banner(self, tela):
        caixa = pygame.Rect(0, 0, 420, 110)
        caixa.center = (LARGURA // 2, ALTURA // 2)
        ui.painel(tela, caixa, (20, 24, 40), self.COR, 16, 4)
        ui.desenhar_texto(tela, t("BURACO {n}", n=self.buraco + 1), (caixa.centerx, caixa.y + 20), 28, AMARELO, "midtop")
        ui.desenhar_texto(tela, t("PAR {n}", n=self.mesa.par), (caixa.centerx, caixa.y + 66), 16, BRANCO, "midtop")

    def desenhar_hud(self, tela):
        caixa = pygame.Rect(12, 12, 330, 48)
        ui.painel(tela, caixa, (20, 24, 40), BRANCO, 12, 3, sombra=False)
        ui.desenhar_texto(tela, t("BURACO {n}/{total}", n=self.buraco + 1, total=len(BURACOS)), (caixa.x + 16, caixa.centery), 14,
                          AMARELO, "midleft")
        ui.desenhar_texto(tela, t("PAR {n}", n=self.mesa.par), (caixa.right - 16, caixa.centery), 12,
                          (180, 220, 255), "midright")

        caixa = pygame.Rect(354, 12, 580, 48)
        ui.painel(tela, caixa, (20, 24, 40), BRANCO, 12, 3, sombra=False)
        cor = BRANCO if self.tacadas < MAX_TACADAS - 1 else (255, 150, 120)
        ui.desenhar_texto(tela, t("TACADAS: {n}", n=self.tacadas), (caixa.x + 16, caixa.centery), 12, cor, "midleft")
        ui.desenhar_texto(tela, t("TOTAL: {n}", n=self.pontos), (caixa.x + 206, caixa.centery), 12, AMARELO, "midleft")
        rec = self.recorde()
        if rec is not None:
            ui.desenhar_texto(tela, t("RECORDE: {v}", v=rec), (caixa.right - 16, caixa.centery), 12,
                              (180, 200, 255), "midright")

    # --------------------------------------------------------
    # FIM: tabela buraco x tacadas x par
    # --------------------------------------------------------

    def _desenhar_fim(self, tela):
        super()._desenhar_fim(tela)
        if len(self.placar) < len(BURACOS):
            return
        x0 = LARGURA // 2 - 262
        y0 = ALTURA // 2 + 10 - 280 + 262
        col = 44
        linhas = [("BURACO", [str(i + 1) for i in range(len(BURACOS))], BRANCO),
                  ("PAR", [str(b["par"]) for b in BURACOS], (180, 220, 255)),
                  ("TACADAS", [str(v) for v in self.placar], AMARELO)]
        for k, (rotulo, valores, cor) in enumerate(linhas):
            y = y0 + k * 26
            ui.desenhar_texto(tela, t(rotulo), (x0, y), 10, cor, "midleft")
            for i, v in enumerate(valores):
                ui.desenhar_texto(tela, v, (x0 + 118 + i * col, y), 12, cor, "center")
        y = y0 + 3 * 26 + 4
        for i, v in enumerate(self.placar):
            par = BURACOS[i]["par"]
            humor = 2 if v <= par else 1 if v == par + 1 else 0
            _carinha(tela, (x0 + 118 + i * col, y), humor)
        pygame.draw.line(tela, (80, 90, 130), (x0 - 4, y0 + 13), (x0 + 118 + 8 * col + 20, y0 + 13), 1)
