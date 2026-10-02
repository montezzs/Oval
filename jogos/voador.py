import math
import random

import pygame

from settings import *
from core import ui
from core.idioma import t
from jogos.base import MiniJogo

# ============================================================
# OVO VOADOR
# ============================================================
# O seu ovo ganhou asinhas! Bata as asas para voar entre as
# colunas de doce num fim de tarde. Cada coluna que você passa
# vale 1 ponto; os limões no meio do caminho valem 3.

CHAO_Y = 640                    # topo do chão
OVO_X = 280
OVO_ALTURA = 48
Y_INICIO = 320

GRAVIDADE = 1500.0
IMPULSO = 500.0                 # velocidade para cima ao bater as asas
QUEDA_MAX = 780.0

# Hitbox do corpo (elipse um pouco menor que o desenho, sem o cabelo)
RAIO_X = 17
RAIO_Y = 20

LARG_COLUNA = 92
LARG_TAMPA = LARG_COLUNA + 20
ALT_TAMPA = 30
PINGOS = 14                     # cobertura escorrendo pela coluna
DIST_COLUNAS = 330              # distância entre um par e o próximo

VEL_INICIAL = 230.0
VEL_MAXIMA = 310.0
ABERTURA_INICIAL = 225
ABERTURA_MINIMA = 170
MAIOR_DIFERENCA = 150           # entre o meio de duas aberturas seguidas
TOPO_MIN = 90                   # a coluna de cima sempre aparece um pouco

LARG_FAIXA = 1536               # largura das camadas que rolam (repete)

TECLAS_ASA = (pygame.K_SPACE, pygame.K_UP, pygame.K_w)

# Doces: (listra, fundo) e coberturas
DOCES = [
    ((230, 60, 70), (255, 250, 245)),      # bengala de natal
    ((255, 120, 175), (255, 245, 250)),    # morango
    ((70, 185, 120), (245, 255, 248)),     # menta
    ((150, 100, 220), (250, 246, 255)),    # uva
]
COBERTURAS = [
    (255, 170, 205),    # glacê rosa
    (130, 78, 46),      # chocolate
    (255, 246, 228),    # chantilly
    (140, 205, 255),    # glacê azul
]

_camadas = {}


# ============================================================
# DESENHOS PRÉ-RENDERIZADOS
# ============================================================

def _coluna_sup(listra, fundo):
    """Corpo do bastão de doce, bem alto (usa-se só um pedaço)."""
    chave = ("coluna", listra)
    sup = _camadas.get(chave)
    if sup is not None:
        return sup

    sup = pygame.Surface((LARG_COLUNA, ALTURA))
    sup.fill(fundo)
    # Listras na diagonal
    for y in range(-LARG_COLUNA, ALTURA + LARG_COLUNA, 40):
        pygame.draw.polygon(sup, listra, [(0, y), (LARG_COLUNA, y - 34),
                                          (LARG_COLUNA, y - 16), (0, y + 18)])
    # Volume: brilho na esquerda e sombra na direita
    luz = pygame.Surface((LARG_COLUNA, ALTURA), pygame.SRCALPHA)
    pygame.draw.rect(luz, (255, 255, 255, 90), (10, 0, 14, ALTURA))
    pygame.draw.rect(luz, (255, 255, 255, 50), (26, 0, 6, ALTURA))
    pygame.draw.rect(luz, (0, 0, 0, 40), (LARG_COLUNA - 26, 0, 26, ALTURA))
    pygame.draw.rect(luz, (0, 0, 0, 30), (LARG_COLUNA - 12, 0, 12, ALTURA))
    sup.blit(luz, (0, 0))
    contorno = ui.escurecer(listra, 90)
    pygame.draw.line(sup, contorno, (1, 0), (1, ALTURA), 3)
    pygame.draw.line(sup, contorno, (LARG_COLUNA - 2, 0), (LARG_COLUNA - 2, ALTURA), 3)

    _camadas[chave] = sup
    return sup


def _tampa_sup(cor, virada=False):
    """Cobertura de bolo no topo da coluna, com pingos e confeitos."""
    chave = ("tampa", cor, virada)
    sup = _camadas.get(chave)
    if sup is not None:
        return sup

    rnd = random.Random(sum(cor))
    sup = pygame.Surface((LARG_TAMPA, ALT_TAMPA + PINGOS), pygame.SRCALPHA)
    contorno = ui.escurecer(cor, 80)
    corpo = pygame.Rect(0, 0, LARG_TAMPA, ALT_TAMPA)

    # Pingos escorrendo (primeiro o contorno, depois a cor)
    pingos = [(14, 10), (34, 6), (58, 13), (80, 8), (98, 11)]
    for px, comp in pingos:
        pygame.draw.rect(sup, contorno, (px - 6, ALT_TAMPA - 8, 12, comp + 8), border_radius=6)
    pygame.draw.rect(sup, contorno, corpo, border_radius=12)
    for px, comp in pingos:
        pygame.draw.rect(sup, cor, (px - 4, ALT_TAMPA - 8, 8, comp + 6), border_radius=4)
    pygame.draw.rect(sup, cor, corpo.inflate(-6, -6), border_radius=10)

    # Brilho e confeitos coloridos
    pygame.draw.rect(sup, ui.clarear(cor, 50), (10, 6, LARG_TAMPA - 40, 5), border_radius=3)
    for _ in range(9):
        x = rnd.randint(10, LARG_TAMPA - 12)
        y = rnd.randint(12, ALT_TAMPA - 8)
        c = rnd.choice([(255, 80, 80), (255, 220, 60), (90, 200, 255), (120, 220, 120),
                        (255, 255, 255)])
        if abs(sum(c) - sum(cor)) < 60:
            c = (80, 60, 160)
        pygame.draw.line(sup, c, (x, y), (x + rnd.choice((-4, 4)), y + 2), 3)

    if virada:
        sup = pygame.transform.flip(sup, False, True)
    _camadas[chave] = sup
    return sup


def _faixa(altura):
    return pygame.Surface((LARG_FAIXA, altura), pygame.SRCALPHA)


def _criar_camadas():
    """Céu e camadas do parallax (feitas uma vez só)."""
    if "ceu" in _camadas:
        return _camadas
    rnd = random.Random(12)

    # Céu de fim de tarde com sol grande
    ceu = pygame.Surface((LARGURA, ALTURA))
    meio = int(ALTURA * 0.55)
    ceu.blit(ui.gradiente(LARGURA, meio, (72, 52, 132), (236, 112, 124)), (0, 0))
    ceu.blit(ui.gradiente(LARGURA, ALTURA - meio, (236, 112, 124), (255, 196, 120)), (0, meio))
    halo = pygame.Surface((440, 440), pygame.SRCALPHA)
    for r in range(220, 90, -4):
        a = int(120 * (1 - (r - 90) / 130) ** 2)
        pygame.draw.circle(halo, (255, 236, 170, a), (220, 220), r)
    ceu.blit(halo, (760 - 220, 430 - 220))
    pygame.draw.circle(ceu, (255, 214, 110), (760, 430), 96)
    pygame.draw.circle(ceu, (255, 236, 160), (760, 430), 80)
    pygame.draw.circle(ceu, (255, 248, 210), (730, 398), 26)
    _camadas["ceu"] = ceu

    # Nuvens distantes (iluminadas pelo pôr do sol)
    nuvens = _faixa(320)
    for i in range(9):
        cx = int(i * LARG_FAIXA / 9 + rnd.randint(0, 80))
        cy = rnd.randint(50, 280)
        largura = rnd.randint(120, 220)
        cor = rnd.choice([(255, 206, 196), (250, 182, 190), (255, 224, 206)])
        for dx in (-LARG_FAIXA, 0, LARG_FAIXA):
            pygame.draw.ellipse(nuvens, cor, (cx + dx - largura // 2, cy - 10, largura, 24))
            for j in range(4):
                ox = int(-largura / 2 + largura * (j + 0.5) / 4)
                r = 14 if j in (0, 3) else 22
                pygame.draw.circle(nuvens, cor, (cx + dx + ox, cy - r // 3), r)
    nuvens.set_alpha(170)
    _camadas["nuvens"] = nuvens

    # Colinas distantes (onduladas, emendam no começo/fim da faixa)
    colinas = _faixa(260)
    pontos = [(0, 260)]
    for x in range(0, LARG_FAIXA + 1, 8):
        a = x / LARG_FAIXA * math.tau
        y = 130 - 40 * math.sin(a * 2) - 26 * math.sin(a * 5 + 1) - 12 * math.sin(a * 11)
        pontos.append((x, y))
    pontos.append((LARG_FAIXA, 260))
    pygame.draw.polygon(colinas, (176, 96, 140), pontos)
    _camadas["colinas"] = colinas

    # Cidade (prédios com janelas acesas)
    cidade = _faixa(220)
    x = 0
    predios = []
    while x < LARG_FAIXA - 40:
        w = rnd.randint(46, 90)
        h = rnd.randint(60, 180)
        predios.append((x, w, h))
        x += w + rnd.randint(0, 14)
    cor = (96, 52, 104)
    for px, w, h in predios:
        telhado = rnd.random() < 0.3
        janelas = [(jx, jy) for jy in range(220 - h + 12, 214, 20)
                   for jx in range(px + 8, px + w - 10, 16) if rnd.random() < 0.45]
        # Desenha também uma cópia uma faixa para a esquerda (emenda)
        for dx in (-LARG_FAIXA, 0):
            r = pygame.Rect(px + dx, 220 - h, w, h)
            pygame.draw.rect(cidade, cor, r)
            if telhado:
                pygame.draw.polygon(cidade, cor, [(r.x, r.y), (r.centerx, r.y - 16), (r.right, r.y)])
            for jx, jy in janelas:
                pygame.draw.rect(cidade, (255, 214, 120), (jx + dx, jy, 7, 9))
    _camadas["cidade"] = cidade

    # Chão: grama com listras + terra de biscoito
    chao = pygame.Surface((LARG_FAIXA, ALTURA - CHAO_Y))
    chao.fill((214, 160, 96))
    for x in range(0, LARG_FAIXA, 48):
        pygame.draw.polygon(chao, (200, 144, 84), [(x, 22), (x + 24, 22), (x + 4, 80), (x - 20, 80)])
    for _ in range(60):
        pygame.draw.circle(chao, (176, 118, 66),
                           (rnd.randrange(LARG_FAIXA), rnd.randint(30, 76)), rnd.randint(2, 3))
    pygame.draw.rect(chao, (104, 178, 70), (0, 0, LARG_FAIXA, 20))
    for x in range(0, LARG_FAIXA, 48):
        pygame.draw.polygon(chao, (130, 204, 90), [(x, 0), (x + 24, 0), (x + 12, 20), (x - 12, 20)])
    for x in range(0, LARG_FAIXA, 16):
        pygame.draw.circle(chao, (104, 178, 70), (x + 8, 20), 8)
    pygame.draw.line(chao, (60, 120, 50), (0, 0), (LARG_FAIXA, 0), 3)
    _camadas["chao"] = chao
    return _camadas


def _desenhar_asas(tela, centro, altura, angulo, batida, jogador):
    """
    Duas asinhas (atrás do ovo) na cor clara do ovo.
    `batida` = quanto a asa está levantada (-1 baixo .. 1 cima).
    `angulo` = inclinação do corpo em graus (igual ao do avatar).
    """
    esc = altura / 48
    pena = [(0, -4), (10, -14), (22, -20), (34, -22), (42, -18), (37, -12), (42, -7),
            (35, -2), (38, 3), (28, 6), (17, 7), (6, 6)]
    cor = jogador.cor_clara
    contorno = jogador.cor_contorno
    linha = ui.misturar(cor, contorno, 0.5)

    a = math.radians(angulo)
    ca, sa = math.cos(a), math.sin(a)
    cx, cy = centro

    for lado in (-1, 1):
        # Ombro (em relação ao centro do ovo)
        ox, oy = lado * altura * 0.34, -altura * 0.06
        giro = math.radians(batida * 40) * lado
        cg, sg = math.cos(giro), math.sin(giro)
        pts = []
        for px, py in pena:
            px, py = px * esc * lado, py * esc
            # bate a asa (gira em volta do ombro)
            rx = px * cg + py * sg
            ry = -px * sg + py * cg
            # inclinação do corpo (gira em volta do centro do ovo)
            x, y = ox + rx, oy + ry
            pts.append((cx + x * ca + y * sa, cy - x * sa + y * ca))
        pygame.draw.polygon(tela, cor, pts)
        pygame.draw.polygon(tela, contorno, pts, 2)
        # Divisões das penas
        for i in (5, 7):
            pygame.draw.line(tela, linha, pts[0], pts[i], 2)


# ============================================================
# PAR DE COLUNAS
# ============================================================

class Par:

    def __init__(self, x, centro, abertura, limao):
        self.x = float(x)                 # esquerda do corpo da coluna
        self.centro = centro              # meio da abertura
        self.abertura = abertura
        self.limao = limao
        self.passou = False
        self.listra, self.fundo = random.choice(DOCES)
        self.cobertura = random.choice(COBERTURAS)

    @property
    def topo(self):
        """Onde termina a coluna de cima."""
        return self.centro - self.abertura / 2

    @property
    def base(self):
        """Onde começa a coluna de baixo."""
        return self.centro + self.abertura / 2

    def retangulos(self):
        x = int(self.x)
        topo, base = int(self.topo), int(self.base)
        return [
            pygame.Rect(x, -400, LARG_COLUNA, topo + 400),
            pygame.Rect(x - 10, topo - ALT_TAMPA, LARG_TAMPA, ALT_TAMPA),
            pygame.Rect(x, base, LARG_COLUNA, CHAO_Y - base),
            pygame.Rect(x - 10, base, LARG_TAMPA, ALT_TAMPA),
        ]


def _bate_elipse(cx, cy, rect):
    """A elipse do corpo do ovo encosta no retângulo?"""
    px = max(rect.left, min(cx, rect.right))
    py = max(rect.top, min(cy, rect.bottom))
    return ((px - cx) / RAIO_X) ** 2 + ((py - cy) / RAIO_Y) ** 2 < 1.0


class OvoVoador(MiniJogo):

    ID = "voador"
    MOEDAS_POR = 2
    MOEDAS_MAX = 25
    TITULO = "OVO VOADOR"
    TITULO_CURTO = "OVO VOADOR"
    DESCRICAO = "Seu ovo ganhou asinhas! Voe entre as colunas de doce no pôr do sol."
    COR = (240, 120, 80)
    INSTRUCOES = [
        "O seu ovo ganhou ASINHAS!",
        "Bata as asas para passar entre os doces.",
        "Cada doce vale 1 ponto. LIMÃO vale 3!",
        "Não bata nos doces nem no chão.",
        "ESPAÇO, ↑, W ou CLIQUE para bater as asas",
    ]

    # --------------------------------------------------------
    # CENÁRIO
    # --------------------------------------------------------

    @classmethod
    def criar_fundo(cls, jogador):
        camadas = _criar_camadas()
        sup = camadas["ceu"].copy()
        sup.blit(camadas["nuvens"], (0, 0))
        sup.blit(camadas["colinas"], (0, CHAO_Y - 260))
        sup.blit(camadas["cidade"], (0, CHAO_Y - 220))
        sup.blit(camadas["chao"], (0, CHAO_Y))
        return sup

    @classmethod
    def desenhar_icone(cls, sup, jogador):
        w, h = sup.get_size()
        chao = h * CHAO_Y // ALTURA
        # Um par de colunas de doce pequenininho
        corpo = _coluna_sup(*DOCES[0])
        corpo = pygame.transform.smoothscale(corpo, (26, ALTURA // 4))
        tampa = pygame.transform.smoothscale(_tampa_sup(COBERTURAS[0]), (32, 12))
        x = w - 50
        sup.blit(corpo, (x, 0), (0, 0, 26, 30))
        sup.blit(pygame.transform.flip(tampa, False, True), (x - 3, 26))
        sup.blit(corpo, (x, 84), (0, 0, 26, chao - 84))
        sup.blit(tampa, (x - 3, 84))
        # Ovo com asinhas
        c = (w // 2 - 24, h // 2 - 4)
        _desenhar_asas(sup, c, 34, 12, 0.6, jogador)
        jogador.desenhar(sup, c, 34, angulo=12)
        ui.limao(sup, (x + 13, 58), 8)

    # --------------------------------------------------------
    # PARTIDA
    # --------------------------------------------------------

    def reiniciar(self):
        _criar_camadas()
        self.y = float(Y_INICIO)
        self.vy = 0.0
        self.inclinacao = 0.0             # graus (+ = bico para baixo)
        self.comecou = False              # só cai depois do 1º toque
        self.fase_asa = 0.0
        self.batendo = 0.0                # tempo de asa batendo rápido
        self.desloc = 0.0                 # quanto o cenário já andou
        self.vel = VEL_INICIAL
        self.passados = 0
        self.limoes = 0
        self.morto = False
        self.tempo_morto = 0.0
        self.giro = 0.0
        self.pares = []
        self._novo_par(LARGURA - 200)

    def _novo_par(self, x):
        abertura = max(ABERTURA_MINIMA, ABERTURA_INICIAL - self.passados * 2.5)
        menor = TOPO_MIN + abertura / 2
        maior = CHAO_Y - 70 - abertura / 2
        if self.pares:
            # Alcançável a partir da abertura anterior
            ant = self.pares[-1].centro
            menor = max(menor, ant - MAIOR_DIFERENCA)
            maior = min(maior, ant + MAIOR_DIFERENCA)
        centro = random.uniform(menor, maior)
        limao = random.random() < 0.3
        self.pares.append(Par(x, centro, abertura, limao))

    # --------------------------------------------------------

    def evento_jogo(self, e):
        if (e.type == pygame.KEYDOWN and e.key in TECLAS_ASA) or \
                (e.type == pygame.MOUSEBUTTONDOWN and e.button == 1):
            self._bater_asas()

    def _bater_asas(self):
        if self.morto:
            return
        self.comecou = True
        self.vy = -IMPULSO
        self.batendo = 0.28
        self.som("asa", 0.7)

    def atualizar_jogo(self, dt):
        self.batendo = max(0.0, self.batendo - dt)
        self.fase_asa += dt * (26 if self.batendo > 0 else 5)

        if not self.comecou:
            # Flutuando, esperando o primeiro toque
            self.y = Y_INICIO + math.sin(self.tempo * 3) * 12
            return

        if self.morto:
            self._atualizar_morto(dt)
            return

        # --- Física do ovo ---
        self.vy = min(QUEDA_MAX, self.vy + GRAVIDADE * dt)
        self.y += self.vy * dt
        if self.y - RAIO_Y - 6 < 0:           # teto: só não deixa passar
            self.y = RAIO_Y + 6
            self.vy = max(self.vy, 0.0)
        alvo = max(-25.0, min(60.0, self.vy * 0.075))
        self.inclinacao += (alvo - self.inclinacao) * min(1.0, dt * 10)

        # --- Cenário andando ---
        self.vel = min(VEL_MAXIMA, VEL_INICIAL + self.passados * 3)
        self.desloc += self.vel * dt
        for par in self.pares:
            par.x -= self.vel * dt
        if self.pares[-1].x < LARGURA + 100 - DIST_COLUNAS:
            self._novo_par(self.pares[-1].x + DIST_COLUNAS)
        self.pares = [p for p in self.pares if p.x + LARG_TAMPA > -20]

        # --- Pontos e limões ---
        for par in self.pares:
            if not par.passou and par.x + LARG_COLUNA < OVO_X - RAIO_X:
                par.passou = True
                self.passados += 1
                self.pontos += 1
                self.som("ponto", 0.7)
                self.textos.adicionar("+1", (OVO_X + 46, self.y - 46), BRANCO, 16)
            if par.limao:
                lx, ly = par.x + LARG_COLUNA / 2, par.centro
                if math.hypot(lx - OVO_X, ly - self.y) < 32:
                    par.limao = False
                    self.limoes += 1
                    self.pontos += 3
                    self.som("moeda")
                    self.particulas.explodir((lx, ly), [(250, 222, 40), (255, 248, 180),
                                                        (120, 200, 60)], 18, 200)
                    self.textos.adicionar("+3", (lx, ly - 24), AMARELO, 16)

        # --- Batidas ---
        if self.y + RAIO_Y >= CHAO_Y:
            self.y = CHAO_Y - RAIO_Y
            self._morrer()
            return
        for par in self.pares:
            if par.x - 12 > OVO_X + RAIO_X or par.x + LARG_TAMPA < OVO_X - RAIO_X:
                continue
            if any(_bate_elipse(OVO_X, self.y, r) for r in par.retangulos()):
                self._morrer()
                return

    def _morrer(self):
        self.morto = True
        self.tempo_morto = 0.0
        self.no_chao = self.y + RAIO_Y >= CHAO_Y - 1
        self.vy = 0.0 if self.no_chao else -260.0
        self.tremer(0.35)
        self.som("explosao", 0.6)
        self.som("bater")
        j = self.jogador
        self.particulas.explodir((OVO_X, self.y), [j.cor, j.cor_clara, BRANCO], 26, 240)

    def _atualizar_morto(self, dt):
        self.tempo_morto += dt
        if not self.no_chao:
            # Cai girando até o chão
            self.vy = min(QUEDA_MAX * 1.2, self.vy + GRAVIDADE * dt)
            self.y += self.vy * dt
            self.giro += 540 * dt
            if self.y + RAIO_Y >= CHAO_Y:
                self.y = CHAO_Y - RAIO_Y
                self.no_chao = True
                self.som("bater", 0.6)
        if self.tempo_morto > 0.8 and self.no_chao or self.tempo_morto > 2.0:
            self.terminar(linhas=[t("PONTOS: {n}", n=self.pontos), t("LIMÕES: {n}", n=self.limoes)])

    # --------------------------------------------------------
    # DESENHO
    # --------------------------------------------------------

    def _camada(self, tela, nome, fator, y, extra=0.0):
        sup = _camadas[nome]
        off = int(-(self.desloc * fator + extra)) % LARG_FAIXA
        tela.blit(sup, (off, y))
        tela.blit(sup, (off - LARG_FAIXA, y))

    def desenhar_jogo(self, tela):
        tela.blit(_camadas["ceu"], (0, 0))
        self._camada(tela, "nuvens", 0.05, 0, self.tempo * 6)
        self._camada(tela, "colinas", 0.15, CHAO_Y - 260)
        self._camada(tela, "cidade", 0.35, CHAO_Y - 220)

        # Colunas de doce
        for par in self.pares:
            x = int(par.x)
            if x > LARGURA or x + LARG_TAMPA < -20:
                continue
            corpo = _coluna_sup(par.listra, par.fundo)
            topo, base = int(par.topo), int(par.base)

            # De cima: mostra o fim do bastão, com a cobertura virada
            alt = topo - ALT_TAMPA + 6
            if alt > 0:
                tela.blit(corpo, (x, 0), (0, ALTURA - alt, LARG_COLUNA, alt))
            tela.blit(_tampa_sup(par.cobertura, True), (x - 10, topo - ALT_TAMPA - PINGOS))

            # De baixo
            tela.blit(corpo, (x, base + ALT_TAMPA - 6), (0, 0, LARG_COLUNA, CHAO_Y - base))
            tela.blit(_tampa_sup(par.cobertura), (x - 10, base))

            if par.limao:
                bal = math.sin(self.tempo * 4 + par.x * 0.01) * 4
                ui.limao(tela, (x + LARG_COLUNA / 2, par.centro + bal), 13)

        self._desenhar_ovo(tela)
        self._camada(tela, "chao", 1.0, CHAO_Y)

        self.particulas.desenhar(tela)
        self.textos.desenhar(tela)

        if self.estado == "jogando" and not self.comecou:
            if int(self.tempo * 2.5) % 3 != 0:
                ui.desenhar_texto(tela, t("APERTE ESPAÇO!"), (LARGURA // 2 + 60, 190), 24,
                                  AMARELO, "center")
            ui.desenhar_texto(tela, t("ou clique para voar"), (LARGURA // 2 + 60, 232), 12,
                              BRANCO, "center")

    def _desenhar_ovo(self, tela):
        if self.morto:
            angulo = -self.inclinacao - self.giro
            batida = -0.6
        else:
            angulo = -self.inclinacao
            if self.batendo > 0:
                batida = math.sin(self.fase_asa)
            else:
                batida = 0.25 + math.sin(self.fase_asa) * 0.25  # planando

        y = self.y
        if not self.comecou and self.estado != "jogando":
            # Contagem / prévia: flutua usando o relógio da cena
            y = Y_INICIO + math.sin(self.tempo * 3) * 12
            batida = 0.25 + math.sin(self.tempo * 5) * 0.25

        centro = (OVO_X, y)
        _desenhar_asas(tela, centro, OVO_ALTURA, angulo, batida, self.jogador)
        self.jogador.desenhar(tela, centro, OVO_ALTURA, angulo=angulo)

    def desenhar_hud(self, tela):
        super().desenhar_hud(tela)
        caixa = pygame.Rect(12, 66, 120, 36)
        ui.painel(tela, caixa, (20, 24, 40), BRANCO, 10, 2, sombra=False)
        ui.limao(tela, (caixa.x + 26, caixa.centery), 9)
        ui.desenhar_texto(tela, f"×{self.limoes}", (caixa.x + 44, caixa.centery), 12,
                          AMARELO, "midleft")
