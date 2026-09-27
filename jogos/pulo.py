import math
import random

import pygame

from settings import *
from core import ui
from jogos.base import MiniJogo

# ============================================================
# PULO NAS NUVENS
# ============================================================
# O seu ovo quica sozinho de nuvem em nuvem, subindo pelo céu.
# Você só escolhe para que lado ele vai! Quanto mais alto, mais
# o céu muda: dia -> pôr do sol -> noite -> espaço.
#
#   nuvem branca  -> normal
#   nuvem rosa    -> anda de um lado para o outro
#   nuvem de chuva-> se desfaz quando você pisa (não quica!)
#   mola          -> SUPER PULO

GRAVIDADE = 1500.0
VEL_PULO = 840.0
VEL_MOLA = 1500.0
VEL_LADO = 440.0

# Altura máxima de um pulo normal: v² / 2g  (~235 px)
ALTURA_PULO = VEL_PULO ** 2 / (2 * GRAVIDADE)
# Maior distância vertical entre duas nuvens "sólidas" seguidas
# (com margem, para dar tempo de andar para o lado)
MAIOR_VAO = int(ALTURA_PULO * 0.7)

ALTURA_MOLA = 28               # a mola fica em pé em cima da nuvem
OVO_ALTURA = 52
OVO_LARGURA = OVO_ALTURA * 0.9
Y_CHAO = 660                    # topo da grama no começo (coordenada do mundo)
LINHA_CAMERA = ALTURA * 0.4     # a câmera sobe quando o ovo passa daqui
PIXELS_POR_METRO = 10

TECLAS_ESQ = (pygame.K_LEFT, pygame.K_a)
TECLAS_DIR = (pygame.K_RIGHT, pygame.K_d)

# Cores do céu conforme a altura (em metros)
CEU = [
    (0, (126, 204, 250)),       # dia
    (100, (100, 176, 242)),
    (170, (255, 172, 110)),     # pôr do sol
    (230, (234, 112, 150)),
    (310, (44, 48, 112)),       # noite
    (420, (12, 10, 30)),        # espaço
]

# Cores de cada tipo de nuvem: (preenchimento, sombra, contorno)
CORES_NUVEM = {
    "normal": ((255, 255, 255), (214, 228, 246), (140, 162, 200)),
    "movel": ((255, 222, 238), (242, 186, 214), (196, 118, 160)),
    "fragil": ((170, 176, 188), (138, 144, 158), (92, 98, 112)),
    "mola": ((255, 255, 255), (214, 228, 246), (140, 162, 200)),
}

_nuvens_cache = {}
_camadas = {}


def _interpolar(tabela, valor):
    """Cor da tabela [(chave, cor), ...] interpolada no valor."""
    if valor <= tabela[0][0]:
        return tabela[0][1]
    for (a, ca), (b, cb) in zip(tabela, tabela[1:]):
        if valor <= b:
            return ui.misturar(ca, cb, (valor - a) / (b - a))
    return tabela[-1][1]


def _alcance(vao):
    """
    Distância de lado (px) que dá para andar num pulo que sobe `vao`:
    tempo subindo até o topo + tempo caindo do topo até a nuvem,
    vezes a velocidade de lado (com margem de 30%).
    """
    subir = VEL_PULO / GRAVIDADE
    descer = math.sqrt(2 * max(0.0, ALTURA_PULO - vao) / GRAVIDADE)
    return 0.7 * VEL_LADO * (subir + descer)


def _rampa(valor, inicio, fim):
    """0 antes de `inicio`, 1 depois de `fim`, linear no meio."""
    return max(0.0, min(1.0, (valor - inicio) / (fim - inicio)))


# ============================================================
# DESENHOS PRÉ-RENDERIZADOS
# ============================================================

def _nuvem_sup(largura, tipo):
    """Nuvem fofinha (cache). O topo 'pisável' fica em y = 12."""
    chave = (largura, tipo)
    sup = _nuvens_cache.get(chave)
    if sup is not None:
        return sup

    cor, sombra, contorno = CORES_NUVEM[tipo]
    rnd = random.Random(largura * 31 + len(tipo))
    sup = pygame.Surface((largura + 16, 50), pygame.SRCALPHA)

    # Bolinhas de cima + base achatada
    n = max(3, largura // 26)
    bolas = []
    for i in range(n):
        cx = 8 + largura * (i + 0.5) / n
        r = rnd.randint(13, 17) if 0 < i < n - 1 else rnd.randint(10, 13)
        bolas.append((cx, 22 - (r - 12) * 0.6, r))
    base = pygame.Rect(8, 16, largura, 24)

    # Contorno (tudo um pouco maior, na cor escura)
    pygame.draw.ellipse(sup, contorno, base.inflate(6, 6))
    for cx, cy, r in bolas:
        pygame.draw.circle(sup, contorno, (int(cx), int(cy)), r + 3)

    pygame.draw.ellipse(sup, cor, base)
    for cx, cy, r in bolas:
        pygame.draw.circle(sup, cor, (int(cx), int(cy)), r)

    # Sombrinha embaixo e brilho em cima
    pygame.draw.ellipse(sup, sombra, (base.x + 6, base.y + 12, base.w - 12, 10))
    for cx, cy, r in bolas[:-1]:
        pygame.draw.circle(sup, ui.clarear(cor, 30), (int(cx - r * 0.35), int(cy - r * 0.35)),
                           max(2, r // 4))

    if tipo == "fragil":
        # Rachadura: vai quebrar!
        meio = 8 + largura // 2
        pontos = [(meio - 2, 8), (meio + 4, 18), (meio - 3, 26), (meio + 3, 36)]
        pygame.draw.lines(sup, contorno, False, pontos, 2)

    _nuvens_cache[chave] = sup
    return sup


def _criar_camadas():
    """Camadas do céu (feitas uma vez só)."""
    if _camadas:
        return _camadas
    rnd = random.Random(7)

    # Brilho do horizonte (clarinho embaixo, transparente em cima)
    brilho = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
    for y in range(ALTURA):
        t = (y / ALTURA) ** 1.6
        pygame.draw.line(brilho, (255, 244, 225, int(150 * t)), (0, y), (LARGURA, y))
    _camadas["brilho"] = brilho

    # Nuvens distantes (translúcidas)
    # (desenhadas opacas; a transparência vem do set_alpha na hora de usar)
    longe = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
    for i in range(8):
        cx = rnd.randrange(LARGURA)
        cy = int(50 + i * (ALTURA - 60) / 8 + rnd.randint(-16, 16))
        largura = rnd.randint(140, 240)
        bolas = []
        for j in range(5):
            ox = int(-largura / 2 + largura * (j + 0.5) / 5) + rnd.randint(-8, 8)
            r = rnd.randint(16, 22) if j in (0, 4) else rnd.randint(24, 34)
            bolas.append((ox, -r // 2, r))
        for dx in (-LARGURA, 0, LARGURA):
            pygame.draw.ellipse(longe, (255, 255, 255, 255),
                                (cx + dx - largura // 2, cy - 12, largura, 28))
            for ox, oy, r in bolas:
                pygame.draw.circle(longe, (255, 255, 255, 255), (cx + dx + ox, cy + oy), r)
    _camadas["longe"] = longe

    # Estrelas
    estrelas = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
    for _ in range(170):
        x, y = rnd.randrange(LARGURA), rnd.randrange(ALTURA)
        c = rnd.choice([(255, 255, 255), (255, 240, 190), (200, 220, 255)])
        if rnd.random() < 0.12:
            ui.estrela(estrelas, (x, y), rnd.randint(4, 6), c, rnd.random())
        else:
            pygame.draw.circle(estrelas, c, (x, y), rnd.choice((1, 1, 2)))
    _camadas["estrelas"] = estrelas

    # Planetinhas
    planetas = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
    # Planeta com anel
    pygame.draw.ellipse(planetas, (230, 200, 140), (130, 150, 150, 36), 5)
    pygame.draw.circle(planetas, (240, 170, 90), (205, 168), 42)
    pygame.draw.circle(planetas, (255, 200, 130), (192, 154), 16)
    pygame.draw.arc(planetas, (230, 200, 140), (130, 150, 150, 36), math.pi, math.tau, 5)
    # Planeta vermelho com crateras
    pygame.draw.circle(planetas, (200, 80, 80), (830, 470), 30)
    pygame.draw.circle(planetas, (170, 60, 64), (820, 480), 7)
    pygame.draw.circle(planetas, (170, 60, 64), (842, 460), 5)
    pygame.draw.circle(planetas, (235, 130, 120), (820, 458), 8)
    # Planeta azul pequeno
    pygame.draw.circle(planetas, (90, 150, 240), (560, 610), 16)
    pygame.draw.circle(planetas, (150, 200, 255), (554, 604), 6)
    _camadas["planetas"] = planetas

    # Brilho do sol (halo)
    # (pygame.draw não mistura alpha: cada anel de dentro sobrescreve com mais alpha)
    halo = pygame.Surface((260, 260), pygame.SRCALPHA)
    for r in range(130, 50, -3):
        a = int(110 * (1 - (r - 50) / 80) ** 2)
        pygame.draw.circle(halo, (255, 250, 210, a), (130, 130), r)
    _camadas["halo"] = halo

    # Chão de grama do começo
    chao = pygame.Surface((LARGURA, 220), pygame.SRCALPHA)
    pygame.draw.ellipse(chao, (120, 190, 90), (-200, 0, 700, 160))
    pygame.draw.ellipse(chao, (110, 180, 84), (420, -10, 820, 180))
    pygame.draw.rect(chao, (96, 170, 72), (0, 30, LARGURA, 190))
    pygame.draw.rect(chao, (80, 150, 60), (0, 30, LARGURA, 8))
    for _ in range(140):
        x, y = rnd.randrange(LARGURA), rnd.randint(44, 210)
        pygame.draw.line(chao, (70, 140, 56), (x, y), (x + rnd.randint(-2, 2), y - 6), 2)
    for _ in range(24):
        x, y = rnd.randrange(LARGURA), rnd.randint(50, 200)
        c = rnd.choice([(255, 120, 150), (255, 230, 90), (255, 255, 255)])
        for dx, dy in ((-3, 0), (3, 0), (0, -3), (0, 3)):
            pygame.draw.circle(chao, c, (x + dx, y + dy), 3)
        pygame.draw.circle(chao, (255, 200, 40), (x, y), 2)
    _camadas["chao"] = chao
    return _camadas


def _desenhar_mola(tela, x, y, aperto=0.0):
    """Molinha vermelha com a base em (x, y). aperto 0..1 comprime."""
    altura = int(ALTURA_MOLA - 14 * aperto)
    topo = y - altura
    pontos = []
    for i in range(7):
        pontos.append((x + (-10 if i % 2 == 0 else 10), y - 3 - i * (altura - 6) / 6))
    pygame.draw.lines(tela, (110, 60, 20), False, pontos, 6)
    pygame.draw.lines(tela, (255, 190, 60), False, pontos, 3)
    pygame.draw.rect(tela, (110, 30, 40), (x - 17, y - 5, 34, 8), border_radius=3)
    pygame.draw.rect(tela, (110, 30, 40), (x - 20, topo - 4, 40, 10), border_radius=4)
    pygame.draw.rect(tela, (240, 70, 80), (x - 18, topo - 3, 36, 6), border_radius=3)
    pygame.draw.line(tela, (255, 170, 170), (x - 14, topo - 2), (x + 6, topo - 2), 2)


# ============================================================
# NUVEM (PLATAFORMA)
# ============================================================

class Nuvem:

    def __init__(self, x, y, largura, tipo, vx=0.0, limao=False, amp=0.0):
        self.x = float(x)           # centro
        self.y = float(y)           # linha onde o ovo pisa
        self.largura = largura
        self.tipo = tipo
        self.vx = vx
        self.limao = limao
        self.aperto = 0.0           # animação da mola / afundar
        # Nuvem que anda: vai e volta entre min_x e max_x
        meia = largura / 2 + 6
        self.min_x = max(meia, x - amp)
        self.max_x = min(LARGURA - meia, x + amp)

    @property
    def solida(self):
        return self.tipo != "fragil"


class PuloNuvens(MiniJogo):

    ID = "pulo"
    MOEDAS_POR = 40
    MOEDAS_MAX = 25
    TITULO = "PULO NAS NUVENS"
    TITULO_CURTO = "PULO NUVENS"
    DESCRICAO = "Seu ovo quica de nuvem em nuvem! Suba pelo céu até chegar no espaço."
    COR = (90, 150, 230)
    INSTRUCOES = [
        "O seu ovo quica sozinho nas nuvens!",
        "Nuvem cinza de chuva se desfaz: cuidado!",
        "A MOLA dá um SUPER PULO. Pegue os LIMÕES!",
        "Não caia lá embaixo!",
        "← → ou A/D (ou o MOUSE) para ir de lado",
    ]

    # --------------------------------------------------------
    # CENÁRIO: céu de dia com nuvens (usado na miniatura)
    # --------------------------------------------------------

    @classmethod
    def criar_fundo(cls, jogador):
        camadas = _criar_camadas()
        sup = ui.gradiente(LARGURA, ALTURA, (96, 172, 242), (170, 222, 252))
        sup.blit(camadas["halo"], (650, -30))
        pygame.draw.circle(sup, (255, 236, 120), (780, 100), 52)
        pygame.draw.circle(sup, (255, 250, 190), (766, 86), 20)
        camadas["longe"].set_alpha(110)
        sup.blit(camadas["longe"], (0, 0))
        for x, y, w, tipo in ((200, 520, 150, "normal"), (560, 400, 130, "movel"),
                              (330, 260, 130, "normal"), (760, 560, 120, "fragil"),
                              (820, 250, 110, "normal")):
            nuvem = _nuvem_sup(w, tipo)
            sup.blit(nuvem, (x - nuvem.get_width() // 2, y - 12))
        sup.blit(camadas["chao"], (0, ALTURA - 60))
        return sup

    @classmethod
    def desenhar_icone(cls, sup, jogador):
        w, h = sup.get_size()
        nuvem = _nuvem_sup(110, "normal")
        nuvem = pygame.transform.smoothscale(nuvem, (nuvem.get_width() * 2 // 3,
                                                     nuvem.get_height() * 2 // 3))
        sup.blit(nuvem, nuvem.get_rect(midtop=(w // 2, h - 30)))
        jogador.desenhar(sup, (w // 2, h // 2 - 4), 42)
        ui.limao(sup, (w // 2 + 58, h // 2 - 26), 11)
        # Risquinhos de movimento (subindo!)
        for dx in (-14, 0, 14):
            y0 = h // 2 + 22 + abs(dx) // 3
            pygame.draw.line(sup, BRANCO, (w // 2 + dx, y0), (w // 2 + dx, y0 + 8), 2)

    # --------------------------------------------------------
    # PARTIDA
    # --------------------------------------------------------

    def reiniciar(self):
        _criar_camadas()
        self.x = LARGURA / 2
        self.y = Y_CHAO - OVO_ALTURA / 2      # centro do ovo (mundo)
        self.vx = 0.0
        self.vy = 0.0
        self.cam_y = 0.0                      # topo da tela (mundo)
        self.nuvens = []
        self.topo_gerado = Y_CHAO             # y da última nuvem sólida
        self.x_ultima = LARGURA / 2
        self.amp_ultima = 0.0
        self.limoes = 0
        self.metros = 0
        self.squash = 0.0
        self.giro = 0.0                       # giro do super pulo
        self.espelhar = False
        self.morto = False
        self.tempo_morto = 0.0
        self.teclas = set()
        self.modo_mouse = False
        self.mouse_x = LARGURA / 2
        self._gerar()

    def _metros_camera(self):
        return max(0.0, -self.cam_y / PIXELS_POR_METRO)

    def _gerar(self):
        """Cria nuvens até um pouco acima do topo da tela."""
        while self.topo_gerado > self.cam_y - 240:
            alt = max(0.0, (Y_CHAO - self.topo_gerado) / PIXELS_POR_METRO)
            t = min(1.0, alt / 320)

            # Distância vertical: cresce com a altura, mas NUNCA passa do pulo
            menor = 62 + 40 * t
            maior = min(MAIOR_VAO, 96 + (MAIOR_VAO - 96) * t)
            vao = random.uniform(menor, maior)
            y = self.topo_gerado - vao

            largura = int(round((128 - 40 * t + random.randint(-10, 10)) / 10) * 10)

            # Tipo da nuvem sólida
            sorteio = random.random()
            tipo, vx, amp = "normal", 0.0, 0.0
            if alt > 20 and sorteio < 0.07:
                tipo = "mola"
                largura = 90
            elif alt > 35 and sorteio < 0.07 + 0.3 * t:
                tipo = "movel"
                vx = random.choice((-1, 1)) * random.uniform(60, 90 + 50 * t)
                # O balanço não pode "roubar" todo o alcance do pulo
                amp = min(random.uniform(70, 150), _alcance(vao) - self.amp_ultima - 60)
                if amp < 40:
                    tipo, vx, amp = "normal", 0.0, 0.0

            # Posição x alcançável a partir da anterior: o quanto dá para
            # andar de lado durante o pulo (descontando o balanço das
            # nuvens que andam, a anterior e esta)
            alcance = _alcance(vao) - self.amp_ultima - amp
            meia = largura / 2 + 10
            x = self.x_ultima + random.uniform(-alcance, alcance)
            if x < meia:
                x = 2 * meia - x            # "rebate" para dentro da tela
            elif x > LARGURA - meia:
                x = 2 * (LARGURA - meia) - x
            x = max(meia, min(LARGURA - meia, x))

            limao = tipo != "mola" and random.random() < 0.2
            self.nuvens.append(Nuvem(x, y, largura, tipo, vx, limao, amp))

            # Nuvem de chuva (armadilha) no meio do caminho
            if alt > 60 and vao > 90 and random.random() < 0.15 + 0.3 * t:
                lf = 100
                yf = y + vao * random.uniform(0.4, 0.6)
                xf = random.uniform(lf / 2 + 10, LARGURA - lf / 2 - 10)
                if abs(xf - x) < 150:
                    xf = (xf + LARGURA / 2) % LARGURA
                    xf = max(lf / 2 + 10, min(LARGURA - lf / 2 - 10, xf))
                self.nuvens.append(Nuvem(xf, yf, lf, "fragil"))

            self.topo_gerado = y
            self.x_ultima = x
            self.amp_ultima = amp

    # --------------------------------------------------------

    def evento(self, e):
        # Solta as teclas mesmo fora do "jogando" (ex: soltou na pausa)
        if e.type == pygame.KEYUP:
            self.teclas.discard(e.key)
        elif e.type == pygame.WINDOWFOCUSLOST:
            self.teclas.clear()
        super().evento(e)

    def evento_jogo(self, e):
        if e.type == pygame.KEYDOWN and e.key in TECLAS_ESQ + TECLAS_DIR:
            self.teclas.add(e.key)
            self.modo_mouse = False
        elif e.type == pygame.MOUSEMOTION:
            self.mouse_x = e.pos[0]
            self.modo_mouse = True
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.mouse_x = e.pos[0]
            self.modo_mouse = True

    def atualizar_jogo(self, dt):
        if self.morto:
            self.tempo_morto += dt
            self.vy += GRAVIDADE * dt
            self.y += self.vy * dt
            if self.tempo_morto > 0.5:
                self.terminar(linhas=[f"ALTURA: {self.metros} m",
                                      f"LIMÕES: {self.limoes}",
                                      f"PONTOS: {self.pontos}"])
            return

        # --- Movimento para os lados ---
        esq = any(k in self.teclas for k in TECLAS_ESQ)
        dir_ = any(k in self.teclas for k in TECLAS_DIR)
        if esq or dir_:
            alvo = (dir_ - esq) * VEL_LADO
            self.vx += (alvo - self.vx) * min(1.0, dt * 10)
        elif self.modo_mouse:
            alvo = max(-VEL_LADO * 1.2, min(VEL_LADO * 1.2, (self.mouse_x - self.x) * 6))
            self.vx += (alvo - self.vx) * min(1.0, dt * 12)
        else:
            self.vx *= max(0.0, 1 - dt * 6)

        if self.vx < -30:
            self.espelhar = True
        elif self.vx > 30:
            self.espelhar = False

        self.x = (self.x + self.vx * dt) % LARGURA

        # --- Nuvens que andam ---
        for n in self.nuvens:
            n.aperto = max(0.0, n.aperto - dt * 4)
            if n.vx:
                n.x += n.vx * dt
                if n.x < n.min_x:
                    n.x, n.vx = n.min_x, abs(n.vx)
                elif n.x > n.max_x:
                    n.x, n.vx = n.max_x, -abs(n.vx)

        # --- Gravidade e quique ---
        pe_antes = self.y + OVO_ALTURA / 2
        self.vy += GRAVIDADE * dt
        self.y += self.vy * dt
        pe = self.y + OVO_ALTURA / 2

        if self.vy > 0:
            self._colidir(pe_antes, pe)

        self.squash = max(0.0, self.squash - dt)
        if self.giro > 0:
            self.giro = max(0.0, self.giro - dt * 600)

        # --- Limões ---
        for n in self.nuvens:
            if n.limao:
                lx, ly = n.x, n.y - 30
                dx = abs(self.x - lx)
                dx = min(dx, LARGURA - dx)
                if dx < 36 and abs(self.y - ly) < 40:
                    n.limao = False
                    self.limoes += 1
                    self.som("moeda")
                    self.particulas.explodir((lx, ly), [(250, 222, 40), (255, 248, 180),
                                                        (120, 200, 60)], 16, 200)
                    self.textos.adicionar("+10", (lx, ly - 20), AMARELO, 14)

        # --- Câmera (só sobe) ---
        if self.y - self.cam_y < LINHA_CAMERA:
            self.cam_y = self.y - LINHA_CAMERA

        # --- Pontos ---
        self.metros = max(self.metros,
                          int((Y_CHAO - (self.y + OVO_ALTURA / 2)) / PIXELS_POR_METRO))
        self.pontos = self.metros + self.limoes * 10

        # --- Nuvens novas / velhas ---
        self._gerar()
        limite = self.cam_y + ALTURA + 80
        self.nuvens = [n for n in self.nuvens if n.y < limite]

        # --- Caiu lá embaixo ---
        if self.y - OVO_ALTURA / 2 > self.cam_y + ALTURA:
            self.morto = True
            self.tempo_morto = 0.0
            self.som("virar", 0.6)

    def _colidir(self, pe_antes, pe):
        """Quica ao cair em cima de uma nuvem (só vindo de cima)."""
        # Chão do começo
        if pe_antes <= Y_CHAO <= pe:
            self._quicar(Y_CHAO, VEL_PULO)
            return

        for n in self.nuvens:
            dx = abs(self.x - n.x)
            dx = min(dx, LARGURA - dx)
            na_mola = n.tipo == "mola" and dx < 30
            linha = n.y - ALTURA_MOLA + 12 if na_mola else n.y
            if not (pe_antes <= linha <= pe):
                continue
            if dx > n.largura / 2 + OVO_LARGURA * 0.3:
                continue

            if n.tipo == "fragil":
                self._quebrar(n)
                continue

            n.aperto = 1.0
            if na_mola:
                self._quicar(linha, VEL_MOLA)
                self.giro = 360.0
                self.som("mola")
                self.particulas.explodir((self.x, n.y), [BRANCO, AMARELO], 14, 220)
            else:
                self._quicar(n.y, VEL_PULO)
            return

    def _quicar(self, y_pe, vel):
        self.y = y_pe - OVO_ALTURA / 2
        self.vy = -vel
        self.squash = 0.18
        if vel <= VEL_PULO:
            self.som("pulo", 0.3)
        self.particulas.explodir((self.x, y_pe), [(255, 255, 255), (220, 232, 250)],
                                 6, 90, 0.4, (2, 4), 200)

    def _quebrar(self, n):
        if n in self.nuvens:
            self.nuvens.remove(n)
        self.som("virar", 0.7)
        _, sombra, contorno = CORES_NUVEM["fragil"]
        self.particulas.explodir((n.x, n.y + 6), [(170, 176, 188), sombra, contorno],
                                 26, 180, 0.8, (4, 9), 300)
        # Gotinhas de chuva
        self.particulas.explodir((n.x, n.y + 14), [(120, 180, 255), (170, 210, 255)],
                                 12, 80, 0.9, (2, 3), 900)

    # --------------------------------------------------------
    # DESENHO
    # --------------------------------------------------------

    def _desenhar_ceu(self, tela):
        camadas = _camadas
        alt = self._metros_camera()
        subida = -self.cam_y

        tela.fill(_interpolar(CEU, alt))

        # Brilho do horizonte (some à noite)
        a = int(255 * (1 - 0.8 * _rampa(alt, 170, 330)) * (1 - _rampa(alt, 330, 420)))
        if a > 0:
            camadas["brilho"].set_alpha(a)
            tela.blit(camadas["brilho"], (0, 0))

        # Estrelas e planetas aparecem quando escurece
        for nome, fator, ini, fim in (("estrelas", 0.05, 230, 330), ("planetas", 0.15, 380, 450)):
            a = int(255 * _rampa(alt, ini, fim))
            if a > 0:
                sup = camadas[nome]
                sup.set_alpha(a)
                off = (subida * fator) % ALTURA
                tela.blit(sup, (0, off - ALTURA))
                tela.blit(sup, (0, off))

        # Sol que se põe (desce devagar) e lua que aparece
        sy = 100 + subida * 0.24
        if sy < ALTURA + 80:
            cor = ui.misturar((255, 236, 120), (255, 120, 60), _rampa(alt, 90, 220))
            tela.blit(camadas["halo"], (800 - 130, int(sy) - 130))
            pygame.draw.circle(tela, cor, (800, int(sy)), 52)
            pygame.draw.circle(tela, ui.clarear(cor, 40), (786, int(sy) - 14), 20)
        ly = -80 + (subida - 2300) * 0.08
        if -80 < ly < ALTURA + 80:
            pygame.draw.circle(tela, (240, 240, 220), (220, int(ly)), 40)
            pygame.draw.circle(tela, (205, 205, 190), (206, int(ly) - 8), 8)
            pygame.draw.circle(tela, (205, 205, 190), (232, int(ly) + 12), 6)
            pygame.draw.circle(tela, (205, 205, 190), (234, int(ly) - 14), 4)

        # Nuvens distantes (somem quando fica escuro)
        a = int(110 * (1 - _rampa(alt, 220, 330)))
        if a > 0:
            sup = camadas["longe"]
            sup.set_alpha(a)
            off = (subida * 0.35) % ALTURA
            tela.blit(sup, (0, off - ALTURA))
            tela.blit(sup, (0, off))

        # Grama do começo
        y_chao = Y_CHAO - 30 - self.cam_y
        if y_chao < ALTURA:
            tela.blit(camadas["chao"], (0, y_chao))

    def _desenhar_ovo(self, tela, x, y):
        """Ovo com amassadinho (squash) e giro, com o PÉ fixo no lugar."""
        k = self.squash / 0.18
        estica = max(0.0, min(1.0, -self.vy / VEL_PULO)) * 0.08 if not self.morto else 0.0
        sx = 1 + 0.24 * k - estica
        sy = 1 - 0.22 * k + estica
        angulo = self.giro if not self.espelhar else -self.giro
        if self.morto:
            angulo = math.sin(self.tempo * 20) * 20

        if abs(sx - 1) < 0.01 and abs(sy - 1) < 0.01:
            self.jogador.desenhar(tela, (x, y), OVO_ALTURA, espelhar=self.espelhar,
                                  angulo=angulo)
            return

        img = self.jogador.avatar(OVO_ALTURA)
        lado = img.get_width()
        escala = lado / 100
        if self.espelhar:
            img = pygame.transform.flip(img, True, False)
        img = pygame.transform.smoothscale(img, (max(1, round(lado * sx)),
                                                 max(1, round(lado * sy))))
        if angulo:
            img = pygame.transform.rotate(img, angulo)

        pe = y + OVO_ALTURA / 2
        cy = pe - OVO_ALTURA * sy / 2
        ovo = self.jogador.OVO_RECT
        dx = (ovo.centerx - 50) * escala * sx * (-1 if self.espelhar else 1)
        dy = (ovo.centery - 50) * escala * sy
        tela.blit(img, img.get_rect(center=(round(x - dx), round(cy - dy))))

    def desenhar_jogo(self, tela):
        self._desenhar_ceu(tela)
        cam = self.cam_y

        # Nuvens
        for n in self.nuvens:
            sy = n.y - cam
            if sy < -60 or sy > ALTURA + 40:
                continue
            sup = _nuvem_sup(n.largura, n.tipo)
            afunda = int(n.aperto * 5)
            tela.blit(sup, (int(n.x - sup.get_width() / 2), int(sy - 12 + afunda)))

            if n.tipo == "mola":
                _desenhar_mola(tela, int(n.x), int(sy + 12 + afunda), n.aperto)
            elif n.tipo == "movel":
                # Setinhas indicando que anda
                ui.desenhar_texto(tela, "←→", (int(n.x), int(sy + 16 + afunda)), 10,
                                  (196, 118, 160), "center", sombra=False)
            elif n.tipo == "fragil":
                # Gotinhas pingando
                for i in range(3):
                    fase = (self.tempo * 1.4 + i * 0.33) % 1.0
                    gx = int(n.x - 26 + i * 26)
                    gy = int(sy + 30 + fase * 22)
                    pygame.draw.line(tela, (120, 180, 255), (gx, gy), (gx, gy + 5), 2)

            if n.limao:
                bal = math.sin(self.tempo * 4 + n.x) * 3
                ui.limao(tela, (n.x, sy - 30 + bal), 12)

        # Ovo (desenhado dos dois lados quando cruza a borda)
        sy = self.y - cam
        self._desenhar_ovo(tela, self.x, sy)
        margem = OVO_LARGURA
        if self.x < margem:
            self._desenhar_ovo(tela, self.x + LARGURA, sy)
        elif self.x > LARGURA - margem:
            self._desenhar_ovo(tela, self.x - LARGURA, sy)

        self.particulas.desenhar(tela, (0, -cam))
        self.textos.desenhar(tela, (0, -cam))

    def desenhar_hud(self, tela):
        super().desenhar_hud(tela)
        caixa = pygame.Rect(12, 66, 220, 36)
        ui.painel(tela, caixa, (20, 24, 40), BRANCO, 10, 2, sombra=False)
        ui.desenhar_texto(tela, f"↑ {self.metros} m", (caixa.x + 12, caixa.centery), 12,
                          (180, 220, 255), "midleft")
        ui.limao(tela, (caixa.right - 62, caixa.centery), 9)
        ui.desenhar_texto(tela, f"×{self.limoes}", (caixa.right - 46, caixa.centery), 12,
                          AMARELO, "midleft")
