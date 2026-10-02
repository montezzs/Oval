from core.idioma import t
import math
import random

import pygame

from settings import *
from core import ui, assets
from jogos.base import MiniJogo

# ============================================================
# MICRO-OVO
# ============================================================
# Estilo "WarioWare": uma sequência de MICROJOGOS de 4 segundos,
# um atrás do outro, cada um com uma ORDEM gigante na tela
# (PEGUE! DESVIE! ESTOURE! PULE!...). Acertou, ganha 1 ponto;
# errou, perde um dos 4 ovos de vida. A cada 5 rodadas tudo
# fica MAIS RÁPIDO. Pontos = rodadas vencidas.
#
# Cada microjogo é uma classe pequena (Micro) com os mesmos
# ganchos do MiniJogo: tecla, clique, mover, atualizar, desenhar.
# O tempo do microjogo corre multiplicado pela velocidade, então
# acelerar = tudo (queda, ponteiro, abelha...) anda mais rápido.

VIDAS = 4
DURACAO = 4.0               # duração de cada microjogo (tempo do micro)
INTRO = 0.7                 # palavra gigante no meio da tela
ESPERA = 0.65               # mostra o resultado antes da transição
TEMPO_ENTRE = 0.8           # tela-transição (acertou/errou, vidas, rodada)
TEMPO_PRIMEIRA = 1.5        # "PREPARE-SE!" do começo
TEMPO_RAPIDO = 1.4          # aviso "MAIS RÁPIDO!"
TEMPO_GAME_OVER = 1.6
RODADAS_POR_NIVEL = 5
NIVEL_INICIAL = [0, 3]      # NORMAL / TURBO
VEL_PASSO = 0.16
VEL_MAX = 2.4

ESQ = (pygame.K_LEFT, pygame.K_a)
DIR = (pygame.K_RIGHT, pygame.K_d)
CIMA = (pygame.K_UP, pygame.K_w)
BAIXO = (pygame.K_DOWN, pygame.K_s)
ACAO = (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER)

TINTA = (26, 18, 40)        # contorno das palavras e desenhos
VERDE_OK = (120, 255, 130)
VERMELHO_ERRO = (255, 100, 110)
CONFETE = [AMARELO, (255, 90, 140), (120, 200, 255), BRANCO, (120, 255, 150)]


def _velocidade(nivel):
    return min(VEL_MAX, 1 + VEL_PASSO * nivel)


def _fmt_vel(v):
    return f"×{v:.1f}".replace(".", ",")


def _limitar(v, a, b):
    return max(a, min(b, v))


# ============================================================
# DESENHOS (pré-renderizados, com cache)
# ============================================================

_sprites = {}
_giros = {}
_fundos_micro = {}
_fundos_entre = {}


def _sprite(chave, criar):
    sup = _sprites.get(chave)
    if sup is None:
        sup = criar()
        _sprites[chave] = sup
    return sup


def _girado(chave, sup, angulo, passo=10):
    """Versão girada de um sprite (ângulo arredondado, com cache)."""
    ang = int(round(angulo / passo)) * passo % 360
    if ang == 0:
        return sup
    k = (chave, ang)
    img = _giros.get(k)
    if img is None:
        if len(_giros) > 300:
            _giros.clear()
        img = pygame.transform.rotate(sup, ang)
        _giros[k] = img
    return img


def _virado(chave, sup):
    """Versão espelhada (com cache)."""
    return _sprite(("virado", chave), lambda: pygame.transform.flip(sup, True, False))


def _desenhar_ovo(tela, jogador, centro, altura, angulo=0.0):
    """Avatar do jogador; girado só em ângulos de 5 em 5 (com cache)."""
    ang = int(round(angulo / 5.0)) * 5 % 360
    if ang == 0:
        return jogador.desenhar(tela, centro, altura)
    chave = ("ovo", jogador.aparencia(), jogador.chave_visual(), altura)
    img = _girado(chave, jogador.avatar(altura), ang, 5)
    tela.blit(img, img.get_rect(center=(int(centro[0]), int(centro[1]))))


def _palavra(msg, tam, cor):
    """Texto grosso com contorno escuro (a ORDEM gigante)."""
    msg = t(msg)
    def criar():
        frente = ui.texto(msg, tam, cor, sombra=False)
        contorno = ui.texto(msg, tam, TINTA, sombra=False)
        b = max(3, tam // 12)
        w, h = frente.get_size()
        sup = pygame.Surface((w + b * 2 + b, h + b * 2 + b), pygame.SRCALPHA)
        # Sombra deslocada e contorno em volta
        for dx in range(-b, b + 1, max(1, b // 2)):
            for dy in range(-b, b + 1, max(1, b // 2)):
                sup.blit(contorno, (b + dx + b, b + dy + b))
        for dx in range(-b, b + 1, max(1, b // 2)):
            for dy in range(-b, b + 1, max(1, b // 2)):
                sup.blit(contorno, (b + dx, b + dy))
        sup.blit(frente, (b, b))
        return sup
    return _sprite(("palavra", msg, tam, cor), criar)


def _raios(c1, c2, centro=(LARGURA // 2, 330), n=18):
    """Fundo de raios (a "explosão" das telas de transição)."""
    sup = pygame.Surface((LARGURA, ALTURA))
    sup.fill(c2)
    for i in range(n):
        if i % 2:
            continue
        a0 = i * math.tau / n
        a1 = (i + 1) * math.tau / n
        pontos = [centro,
                  (centro[0] + math.cos(a0) * 1400, centro[1] + math.sin(a0) * 1400),
                  (centro[0] + math.cos(a1) * 1400, centro[1] + math.sin(a1) * 1400)]
        pygame.draw.polygon(sup, c1, pontos)
    # Bolinhas decorativas
    rnd = random.Random(7)
    claro = ui.clarear(c1, 40)
    for _ in range(40):
        x, y = rnd.randrange(LARGURA), rnd.randrange(ALTURA)
        pygame.draw.circle(sup, claro, (x, y), rnd.randint(2, 5))
    pygame.draw.circle(sup, ui.clarear(c1, 25), centro, 190)
    pygame.draw.circle(sup, ui.clarear(c1, 45), centro, 150)
    return sup


CORES_ENTRE = {
    "neutro": ((150, 100, 230), (110, 66, 190)),
    "ganhou": ((100, 210, 120), (60, 165, 90)),
    "perdeu": ((225, 90, 100), (170, 55, 75)),
    "rapido": ((255, 160, 50), (235, 105, 35)),
}


def _fundo_entre(estilo):
    sup = _fundos_entre.get(estilo)
    if sup is None:
        sup = _raios(*CORES_ENTRE[estilo]).convert()
        _fundos_entre[estilo] = sup
    return sup


def _nuvens(sup, lista):
    for x, y in lista:
        for dx, dy, r in ((0, 0, 24), (26, -10, 28), (54, 0, 24), (26, 8, 22)):
            pygame.draw.circle(sup, BRANCO, (x + dx, y + dy), r)


def _azulejos(sup, cor, y0=0, y1=ALTURA, passo=64):
    for x in range(0, LARGURA, passo):
        pygame.draw.line(sup, cor, (x, y0), (x, y1), 2)
    for y in range(y0, y1, passo):
        pygame.draw.line(sup, cor, (0, y), (LARGURA, y), 2)


def _cesta(larg):
    def criar():
        w, h = larg + 20, 96
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        topo, base = 22, h - 4
        corpo = [(10, topo), (w - 10, topo), (w - 10 - larg * 0.1, base), (10 + larg * 0.1, base)]
        pygame.draw.polygon(s, (150, 95, 40), corpo)
        # Trançado
        for y in range(topo + 10, base, 14):
            k = (y - topo) / (base - topo)
            x0 = 10 + larg * 0.1 * k
            pygame.draw.line(s, (110, 68, 28), (x0 + 2, y), (w - x0 - 2, y), 4)
        for i, x in enumerate(range(26, w - 16, 22)):
            pygame.draw.line(s, (185, 125, 60), (x, topo + 6 + (i % 2) * 7), (x, base - 6), 3)
        pygame.draw.polygon(s, TINTA, corpo, 3)
        # Borda de cima
        pygame.draw.rect(s, (200, 140, 70), (4, topo - 8, w - 8, 16), border_radius=8)
        pygame.draw.rect(s, TINTA, (4, topo - 8, w - 8, 16), 3, border_radius=8)
        return s
    return _sprite(("cesta", larg), criar)


def _panela():
    def criar():
        s = pygame.Surface((226, 108), pygame.SRCALPHA)
        c = (113, 54)
        pygame.draw.rect(s, (110, 70, 40), (150, 46, 72, 16), border_radius=7)
        pygame.draw.rect(s, TINTA, (150, 46, 72, 16), 3, border_radius=7)
        pygame.draw.circle(s, TINTA, c, 48)
        pygame.draw.circle(s, (70, 72, 88), c, 45)
        pygame.draw.circle(s, (45, 46, 58), c, 36)
        pygame.draw.arc(s, (150, 155, 175), (c[0] - 38, c[1] - 38, 76, 76),
                        math.radians(100), math.radians(170), 4)
        pygame.draw.circle(s, (120, 120, 140), (c[0] - 16, c[1] - 18), 5)
        return s
    return _sprite("panela", criar)


def _bolha_sup(r):
    def criar():
        lado = r * 2 + 6
        s = pygame.Surface((lado, lado), pygame.SRCALPHA)
        c = (lado // 2, lado // 2)
        pygame.draw.circle(s, (200, 240, 255, 110), c, r)
        pygame.draw.arc(s, (255, 170, 230, 200), (c[0] - r + 4, c[1] - r + 4, 2 * r - 8, 2 * r - 8),
                        math.radians(200), math.radians(300), 4)
        pygame.draw.arc(s, (170, 255, 200, 200), (c[0] - r + 4, c[1] - r + 4, 2 * r - 8, 2 * r - 8),
                        math.radians(300), math.radians(350), 4)
        pygame.draw.circle(s, (255, 255, 255, 235), c, r, 3)
        pygame.draw.ellipse(s, (255, 255, 255, 230), (c[0] - r * 0.6, c[1] - r * 0.62, r * 0.5, r * 0.3))
        pygame.draw.circle(s, (255, 255, 255, 230), (int(c[0] + r * 0.35), int(c[1] - r * 0.5)), max(2, r // 10))
        return s
    return _sprite(("bolha", r), criar)


def _colher():
    def criar():
        s = pygame.Surface((186, 44), pygame.SRCALPHA)
        pygame.draw.rect(s, TINTA, (58, 13, 122, 18), border_radius=9)
        pygame.draw.rect(s, (205, 210, 225), (60, 15, 118, 14), border_radius=7)
        pygame.draw.line(s, (240, 245, 255), (70, 18), (170, 18), 2)
        pygame.draw.ellipse(s, TINTA, (0, 2, 76, 40))
        pygame.draw.ellipse(s, (205, 210, 225), (3, 5, 70, 34))
        pygame.draw.ellipse(s, (160, 165, 185), (10, 12, 50, 20))
        pygame.draw.ellipse(s, (245, 248, 255), (14, 10, 22, 8))
        return s
    return _sprite("colher", criar)


def _mostrador(raio):
    def criar():
        w, h = raio * 2 + 24, raio + 40
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        c = (raio + 12, raio + 12)
        pygame.draw.circle(s, TINTA, c, raio + 10)
        pygame.draw.circle(s, (250, 248, 240), c, raio + 4)
        # Faixa vermelha (onde NÃO pode parar)
        pontos = []
        for i in range(0, 181, 5):
            a = math.radians(180 + i)
            pontos.append((c[0] + math.cos(a) * (raio - 8), c[1] + math.sin(a) * (raio - 8)))
        for i in range(180, -1, -5):
            a = math.radians(180 + i)
            pontos.append((c[0] + math.cos(a) * (raio - 70), c[1] + math.sin(a) * (raio - 70)))
        pygame.draw.polygon(s, (255, 170, 160), pontos)
        # Tracinhos
        for i in range(0, 181, 15):
            a = math.radians(180 + i)
            r0 = raio - 82 if i % 45 == 0 else raio - 78
            pygame.draw.line(s, TINTA, (c[0] + math.cos(a) * r0, c[1] + math.sin(a) * r0),
                             (c[0] + math.cos(a) * (raio - 92), c[1] + math.sin(a) * (raio - 92)),
                             4 if i % 45 == 0 else 2)
        # Metade de baixo transparente + base
        pygame.draw.rect(s, (0, 0, 0, 0), (0, c[1] + 1, w, h))
        pygame.draw.rect(s, TINTA, (0, c[1] - 2, w, 26), border_radius=8)
        pygame.draw.rect(s, (120, 110, 150), (4, c[1] + 2, w - 8, 18), border_radius=6)
        return s
    return _sprite(("mostrador", raio), criar)


def _bolo():
    def criar():
        s = pygame.Surface((280, 190), pygame.SRCALPHA)
        pygame.draw.ellipse(s, TINTA, (0, 152, 280, 36))
        pygame.draw.ellipse(s, (235, 235, 245), (4, 154, 272, 30))
        corpo = pygame.Rect(30, 70, 220, 100)
        pygame.draw.rect(s, TINTA, corpo.inflate(6, 6), border_radius=18)
        pygame.draw.rect(s, (255, 160, 195), corpo, border_radius=16)
        pygame.draw.rect(s, (200, 110, 150), (30, 120, 220, 12))
        # Cobertura escorrendo
        pygame.draw.rect(s, BRANCO, (30, 70, 220, 24), border_radius=14)
        for x in range(44, 244, 26):
            pygame.draw.circle(s, BRANCO, (x, 96), 10)
            pygame.draw.rect(s, BRANCO, (x - 6, 90, 12, 16 + (x * 7) % 14), border_radius=6)
        # Morangos
        for x in range(58, 240, 44):
            pygame.draw.circle(s, (220, 40, 60), (x, 146), 10)
            pygame.draw.circle(s, (255, 230, 120), (x - 3, 143), 2)
            pygame.draw.polygon(s, (70, 170, 60), [(x - 6, 137), (x + 6, 137), (x, 132)])
        return s
    return _sprite("bolo", criar)


def _abelha(quadro):
    def criar():
        s = pygame.Surface((84, 66), pygame.SRCALPHA)
        # Asas
        if quadro == 0:
            pygame.draw.ellipse(s, (210, 240, 255, 190), (24, 0, 22, 30))
            pygame.draw.ellipse(s, (210, 240, 255, 190), (38, 4, 20, 26))
        else:
            pygame.draw.ellipse(s, (210, 240, 255, 190), (18, 14, 30, 14))
            pygame.draw.ellipse(s, (210, 240, 255, 190), (36, 16, 28, 12))
        pygame.draw.polygon(s, TINTA, [(4, 42), (18, 36), (18, 48)])
        corpo = pygame.Rect(14, 22, 52, 38)
        pygame.draw.ellipse(s, TINTA, corpo.inflate(6, 6))
        pygame.draw.ellipse(s, (255, 210, 40), corpo)
        pygame.draw.rect(s, TINTA, (28, 24, 7, 34))
        pygame.draw.rect(s, TINTA, (41, 23, 7, 36))
        # Cabeça
        pygame.draw.circle(s, TINTA, (66, 38), 14)
        pygame.draw.circle(s, (255, 220, 70), (66, 38), 11)
        pygame.draw.circle(s, TINTA, (70, 35), 3)
        pygame.draw.circle(s, (255, 150, 150), (72, 42), 3)
        pygame.draw.line(s, TINTA, (64, 27), (60, 16), 2)
        pygame.draw.circle(s, TINTA, (60, 16), 3)
        return s
    return _sprite(("abelha", quadro), criar)


def _flor():
    def criar():
        s = pygame.Surface((120, 160), pygame.SRCALPHA)
        pygame.draw.line(s, (40, 130, 50), (60, 60), (60, 160), 6)
        pygame.draw.ellipse(s, (70, 170, 60), (60, 100, 40, 18))
        pygame.draw.ellipse(s, (70, 170, 60), (20, 120, 40, 18))
        for i in range(6):
            a = i * math.tau / 6
            p = (60 + math.cos(a) * 24, 54 + math.sin(a) * 24)
            pygame.draw.circle(s, TINTA, p, 19)
            pygame.draw.circle(s, (255, 120, 180), p, 16)
        pygame.draw.circle(s, TINTA, (60, 54), 19)
        pygame.draw.circle(s, (255, 210, 50), (60, 54), 16)
        pygame.draw.arc(s, TINTA, (51, 50, 18, 12), math.pi * 1.1, math.pi * 1.9, 2)
        pygame.draw.circle(s, TINTA, (54, 50), 2)
        pygame.draw.circle(s, TINTA, (66, 50), 2)
        return s
    return _sprite("flor", criar)


def _cacto():
    def criar():
        s = pygame.Surface((96, 96), pygame.SRCALPHA)
        c = (48, 50)
        for i in range(16):
            a = i * math.tau / 16
            pygame.draw.line(s, TINTA, (c[0] + math.cos(a) * 30, c[1] + math.sin(a) * 30),
                             (c[0] + math.cos(a) * 44, c[1] + math.sin(a) * 44), 2)
        pygame.draw.circle(s, TINTA, c, 35)
        pygame.draw.circle(s, (60, 160, 70), c, 32)
        for dx in (-16, 0, 16):
            pygame.draw.ellipse(s, (90, 195, 95), (c[0] + dx - 5, c[1] - 26, 10, 52))
        pygame.draw.circle(s, (255, 110, 170), (c[0], c[1] - 32), 8)
        pygame.draw.circle(s, AMARELO, (c[0], c[1] - 32), 3)
        return s
    return _sprite("cacto", criar)


def _pintinho(quadro):
    def criar():
        s = pygame.Surface((60, 60), pygame.SRCALPHA)
        amarelo, contorno = (255, 222, 70), (200, 140, 20)
        pygame.draw.ellipse(s, contorno, (26, 4, 8, 14))
        pygame.draw.ellipse(s, contorno, (31, 6, 8, 12))
        pygame.draw.circle(s, contorno, (30, 33), 21)
        pygame.draw.circle(s, amarelo, (30, 33), 18)
        if quadro == 0:
            pygame.draw.ellipse(s, contorno, (6, 30, 18, 12))
        else:
            pygame.draw.ellipse(s, contorno, (4, 20, 18, 12))
        pygame.draw.circle(s, (30, 20, 20), (24, 29), 3)
        pygame.draw.circle(s, (30, 20, 20), (38, 29), 3)
        pygame.draw.polygon(s, (255, 140, 40), [(27, 34), (35, 34), (31, 41)])
        pygame.draw.circle(s, (255, 160, 160), (19, 36), 3)
        pygame.draw.circle(s, (255, 160, 160), (43, 36), 3)
        pygame.draw.line(s, (240, 140, 40), (24, 52), (24, 58), 3)
        pygame.draw.line(s, (240, 140, 40), (36, 52), (36, 58), 3)
        return s
    return _sprite(("pintinho", quadro), criar)


def _cama():
    def criar():
        s = pygame.Surface((460, 260), pygame.SRCALPHA)
        # Cabeceira
        pygame.draw.rect(s, TINTA, (36, 0, 388, 170), border_radius=40)
        pygame.draw.rect(s, (170, 110, 70), (40, 4, 380, 162), border_radius=36)
        pygame.draw.rect(s, (140, 85, 50), (70, 30, 320, 110), border_radius=26)
        pygame.draw.circle(s, AMARELO, (230, 60), 14)
        ui.estrela(s, (230, 60), 10, BRANCO)
        # Colchão e travesseiro
        pygame.draw.rect(s, TINTA, (6, 118, 448, 98), border_radius=20)
        pygame.draw.rect(s, (245, 245, 255), (10, 122, 440, 90), border_radius=18)
        pygame.draw.ellipse(s, TINTA, (138, 78, 184, 70))
        pygame.draw.ellipse(s, BRANCO, (142, 82, 176, 62))
        # Estrutura e pés
        pygame.draw.rect(s, TINTA, (0, 196, 460, 36), border_radius=10)
        pygame.draw.rect(s, (170, 110, 70), (4, 200, 452, 28), border_radius=8)
        for x in (20, 416):
            pygame.draw.rect(s, TINTA, (x, 226, 24, 34), border_radius=4)
            pygame.draw.rect(s, (140, 85, 50), (x + 3, 226, 18, 30), border_radius=3)
        return s
    return _sprite("cama", criar)


def _seta(tela, centro, tam, direcao, cor):
    """Seta desenhada (0 cima, 1 direita, 2 baixo, 3 esquerda)."""
    base = [(0, -1), (0.85, -0.05), (0.35, -0.05), (0.35, 0.9), (-0.35, 0.9), (-0.35, -0.05),
            (-0.85, -0.05)]
    pontos = []
    for x, y in base:
        for _ in range(direcao):
            x, y = -y, x
        pontos.append((centro[0] + x * tam / 2, centro[1] + y * tam / 2))
    pygame.draw.polygon(tela, cor, pontos)
    pygame.draw.polygon(tela, TINTA, pontos, 4)


def _ovinho_vida(tela, centro, viva, escala=1.0):
    """Ovinho de vida (inteiro ou rachado)."""
    w, h = int(34 * escala), int(44 * escala)
    r = pygame.Rect(0, 0, w, h)
    r.center = centro
    pygame.draw.ellipse(tela, TINTA, r.inflate(6, 6))
    if viva:
        pygame.draw.ellipse(tela, (255, 250, 235), r)
        pygame.draw.ellipse(tela, BRANCO, (r.x + w * 0.2, r.y + h * 0.14, w * 0.28, h * 0.3))
    else:
        pygame.draw.ellipse(tela, (110, 100, 120), r)
        x0 = r.x + 2
        pts = [(x0, r.centery)]
        for i in range(1, 6):
            pts.append((r.x + w * i / 5, r.centery + (-6 if i % 2 else 6) * escala))
        pygame.draw.lines(tela, TINTA, False, pts, max(2, int(3 * escala)))


# ============================================================
# MICROJOGOS
# ============================================================

class Micro:
    """Um microjogo de ~4 segundos."""

    PALAVRA = "JÁ!"
    DICA = ""
    COR = AMARELO               # cor da palavra
    FUNDO = ((90, 90, 160), (40, 40, 90))
    CURSOR = False              # usa o cursor (mouse ou setas + ESPAÇO)
    SOBREVIVER = False          # acabou o tempo sem errar = venceu

    def __init__(self, jogo, nivel):
        self.jogo = jogo
        self.nivel = nivel
        self.t = 0.0
        self.resultado = None
        self.preparar()

    @property
    def jogador(self):
        return self.jogo.jogador

    @classmethod
    def fundo(cls):
        sup = _fundos_micro.get(cls.__name__)
        if sup is None:
            sup = ui.gradiente(LARGURA, ALTURA, *cls.FUNDO)
            cls.decorar(sup)
            sup = sup.convert()
            _fundos_micro[cls.__name__] = sup
        return sup

    @classmethod
    def decorar(cls, sup):
        pass

    def ganhar(self, pos=None):
        if self.resultado is None:
            self.resultado = True
            self.jogo._resolver(True, pos)

    def perder(self, pos=None):
        if self.resultado is None:
            self.resultado = False
            self.jogo._resolver(False, pos)

    def decidir(self):
        """Acabou o tempo sem ninguém decidir."""
        if self.SOBREVIVER:
            self.ganhar()
        else:
            self.perder()

    # Ganchos
    def preparar(self):
        pass

    def tecla(self, k):
        pass

    def solta(self, k):
        pass

    def clique(self, pos):
        pass

    def solta_clique(self):
        pass

    def mover(self, pos, rel):
        pass

    def atualizar(self, dt):
        pass

    def desenhar(self, tela):
        tela.blit(self.fundo(), (0, 0))

    def desenhar_cursor(self, tela, pos):
        x, y = int(pos[0]), int(pos[1])
        pygame.draw.circle(tela, TINTA, (x, y), 16, 5)
        pygame.draw.circle(tela, BRANCO, (x, y), 14, 3)
        pygame.draw.circle(tela, BRANCO, (x, y), 3)


def _seguir_x(jogo, x, dt, vel, a, b):
    """Anda com ← → (ou segue o mouse)."""
    e = jogo.eixo()[0]
    if e:
        x += e * vel * dt
    elif jogo.mouse:
        x += (jogo.cursor[0] - x) * min(1.0, dt * 14)
    return _limitar(x, a, b)


# ------------------------------------------------------------
# 1. PEGUE! — o limão caindo na cesta
# ------------------------------------------------------------

class Pegue(Micro):
    PALAVRA = "PEGUE!"
    DICA = "← →  OU  MOUSE"
    COR = AMARELO
    FUNDO = ((110, 195, 255), (205, 238, 255))
    Y_CESTA = 628
    CHAO = 668

    @classmethod
    def decorar(cls, sup):
        _nuvens(sup, [(140, 160), (660, 110), (860, 230)])
        pygame.draw.rect(sup, (90, 180, 70), (0, 650, LARGURA, 70))
        pygame.draw.rect(sup, (70, 150, 55), (0, 650, LARGURA, 8))
        rnd = random.Random(4)
        for _ in range(60):
            x = rnd.randrange(LARGURA)
            pygame.draw.line(sup, (60, 140, 50), (x, 660 + rnd.randrange(50)), (x + 3, 652 + rnd.randrange(50)), 2)
        # Limoeiro no canto
        pygame.draw.rect(sup, (120, 80, 45), (40, 360, 30, 300))
        for dx, dy, r in ((55, 330, 80), (0, 380, 60), (110, 380, 60)):
            pygame.draw.circle(sup, (70, 160, 60), (dx + 5, dy), r)
        for x, y in ((30, 330), (90, 300), (100, 400)):
            ui.limao(sup, (x, y), 10)

    def preparar(self):
        self.cx = LARGURA / 2
        self.larg = max(96, 170 - 14 * self.nivel)
        self.lx = random.uniform(160, LARGURA - 160)
        while abs(self.lx - self.cx) < 150:
            self.lx = random.uniform(160, LARGURA - 160)
        self.ly = 140.0
        self.vx = random.choice((-1, 1)) * random.uniform(20, 50 + 35 * self.nivel)
        self.vy = 40.0
        self.ang = 0.0
        self.pego = None

    def atualizar(self, dt):
        if self.resultado is None or self.pego is not None:
            self.cx = _seguir_x(self.jogo, self.cx, dt, 780, 80, LARGURA - 80)
        if self.pego is not None:
            self.lx, self.ly = self.cx + self.pego, self.Y_CESTA - 16
            return
        if self.ly >= self.CHAO:
            return
        self.vy += 95 * dt
        self.lx += self.vx * dt
        self.ly += self.vy * dt
        self.ang += (self.vx * 1.5 + 90) * dt
        if not 50 < self.lx < LARGURA - 50:
            self.vx = -self.vx
            self.lx = _limitar(self.lx, 50, LARGURA - 50)
        borda = self.Y_CESTA - 24
        if (self.resultado is None and borda <= self.ly <= borda + 30
                and abs(self.lx - self.cx) < self.larg / 2 - 4):
            self.pego = self.lx - self.cx
            self.jogo.som("boing", 0.6)
            self.ganhar((self.lx, self.ly - 30))
        elif self.ly >= self.CHAO:
            self.ly = self.CHAO
            self.vx = 0
            self.jogo.particulas.explodir((self.lx, self.CHAO), [(250, 222, 40), (255, 248, 180)],
                                          12, 220, 0.5, (3, 6))
            self.perder((self.lx, self.CHAO - 40))

    def desenhar(self, tela):
        tela.blit(self.fundo(), (0, 0))
        k = _limitar((self.ly - 140) / 520, 0, 1)
        sombra = pygame.Rect(0, 0, 20 + 40 * k, 8 + 6 * k)
        sombra.center = (self.lx, self.CHAO + 6)
        pygame.draw.ellipse(tela, (60, 130, 50), sombra)
        img = _girado("limao", ui.limao_sup(30), self.ang)
        tela.blit(img, img.get_rect(center=(int(self.lx), int(self.ly))))
        cesta = _cesta(self.larg)
        tela.blit(cesta, cesta.get_rect(midtop=(int(self.cx), self.Y_CESTA - 36)))


# ------------------------------------------------------------
# 2. DESVIE! — frigideiras caindo na cozinha
# ------------------------------------------------------------

class Desvie(Micro):
    PALAVRA = "DESVIE!"
    DICA = "← →  OU  MOUSE"
    COR = (255, 140, 90)
    FUNDO = ((255, 238, 205), (245, 205, 150))
    SOBREVIVER = True
    CHAO = 640
    OY = 590
    ALT = 96
    AVISO = 0.4

    @classmethod
    def decorar(cls, sup):
        _azulejos(sup, (240, 215, 170), 0, 640, 56)
        pygame.draw.rect(sup, (150, 90, 60), (0, 640, LARGURA, 80))
        for x in range(0, LARGURA, 80):
            pygame.draw.rect(sup, (170, 105, 70), (x, 640, 40, 40))
            pygame.draw.rect(sup, (170, 105, 70), (x + 40, 680, 40, 40))
        pygame.draw.rect(sup, TINTA, (0, 636, LARGURA, 6))
        # Prateleira de cima (de onde caem as panelas)
        pygame.draw.rect(sup, TINTA, (0, 140, LARGURA, 18))
        pygame.draw.rect(sup, (170, 110, 70), (0, 142, LARGURA, 12))

    def preparar(self):
        self.ox = LARGURA / 2
        self.panelas = []
        qtd = min(7, 3 + self.nivel)
        self.agenda = sorted(0.5 + i * (2.4 / qtd) + random.uniform(0, 0.15) for i in range(qtd))
        self.tonto = 0.0

    def atualizar(self, dt):
        if self.resultado is not False:
            self.ox = _seguir_x(self.jogo, self.ox, dt, 640, 70, LARGURA - 70)
        self.tonto = max(0.0, self.tonto - dt)

        while self.agenda and self.t >= self.agenda[0]:
            self.agenda.pop(0)
            x = _limitar(self.ox + random.uniform(-40, 40), 70, LARGURA - 70)
            self.panelas.append(dict(x=x, y=112.0, vx=0.0, vy=0.0, t=0.0, estado="aviso",
                                     ang=random.uniform(0, 360),
                                     giro=random.choice((-1, 1)) * random.uniform(300, 600)))
            self.jogo.som("tic", 0.4)

        vivas = []
        for p in self.panelas:
            p["t"] += dt
            if p["estado"] == "aviso":
                if p["t"] >= self.AVISO:
                    p["estado"] = "caindo"
            elif p["estado"] in ("caindo", "quicando"):
                p["vy"] += 2600 * dt
                p["y"] += p["vy"] * dt
                p["x"] += p["vx"] * dt
                p["ang"] += p["giro"] * dt
                if (p["estado"] == "caindo" and self.resultado is None
                        and abs(p["x"] - self.ox) < 66 and self.OY - 70 < p["y"] < self.OY + 30):
                    p["estado"] = "quicando"
                    p["vy"] = -760
                    p["vx"] = 320 if p["x"] > self.ox else -320
                    self.tonto = 99
                    self.jogo.textos.adicionar(t("CLANG!"), (self.ox, self.OY - 90), BRANCO, 20)
                    self.jogo.particulas.explodir((self.ox, self.OY - 50), [AMARELO, BRANCO], 16, 300, 0.5)
                    self.perder((self.ox, self.OY - 60))
                elif p["estado"] == "caindo" and p["y"] >= self.CHAO - 12:
                    p["y"] = self.CHAO - 12
                    p["estado"] = "chao"
                    self.jogo.particulas.explodir((p["x"], self.CHAO - 4), [AMARELO, (255, 170, 60), BRANCO],
                                                  10, 260, 0.35, (2, 5))
                    self.jogo.som("bater", 0.5)
                    self.jogo.tremer(0.06)
                if p["y"] > ALTURA + 120:
                    continue
            vivas.append(p)
        self.panelas = vivas

    def desenhar(self, tela):
        tela.blit(self.fundo(), (0, 0))
        img = _panela()
        # Sombras de aviso no chão
        for p in self.panelas:
            if p["estado"] in ("aviso", "caindo"):
                k = _limitar((p["y"] - 112) / (self.CHAO - 112), 0, 1)
                w = 50 + 70 * k
                r = pygame.Rect(0, 0, w, 16)
                r.center = (p["x"], self.CHAO + 4)
                pygame.draw.ellipse(tela, (200, 60, 60) if p["estado"] == "aviso" else (90, 50, 35), r)
        pygame.draw.ellipse(tela, (100, 60, 40), (self.ox - 40, self.CHAO - 4, 80, 14))
        _desenhar_ovo(tela, self.jogador, (self.ox, self.OY), self.ALT,
                      math.sin(self.t * 20) * 10 if self.tonto else 0)
        if self.tonto:
            for k in range(3):
                a = self.t * 7 + k * math.tau / 3
                ui.estrela(tela, (self.ox + math.cos(a) * 40, self.OY - 60 + math.sin(a) * 10), 8, AMARELO, a)
        for p in self.panelas:
            x = p["x"]
            if p["estado"] == "aviso":
                x += math.sin(p["t"] * 70) * 4
            s = _girado("panela", img, p["ang"], 15)
            tela.blit(s, s.get_rect(center=(int(x), int(p["y"]))))


# ------------------------------------------------------------
# 3. ESTOURE! — bolhas de sabão no banheiro
# ------------------------------------------------------------

class Estoure(Micro):
    PALAVRA = "ESTOURE!"
    DICA = "CLIQUE NAS BOLHAS"
    COR = (140, 230, 255)
    FUNDO = ((175, 228, 250), (100, 170, 230))
    CURSOR = True

    @classmethod
    def decorar(cls, sup):
        _azulejos(sup, (200, 240, 255), 0, 600, 64)
        banheira = pygame.Rect(60, 600, LARGURA - 120, 140)
        pygame.draw.rect(sup, TINTA, banheira.inflate(8, 8), border_radius=40)
        pygame.draw.rect(sup, BRANCO, banheira, border_radius=36)
        pygame.draw.rect(sup, (220, 230, 245), (80, 620, LARGURA - 160, 20), border_radius=10)
        for x in range(120, LARGURA - 100, 90):
            pygame.draw.circle(sup, (235, 245, 255), (x, 604), 22)

    def preparar(self):
        n = min(8, 5 + self.nivel // 2)
        self.raio = max(30, 46 - 3 * self.nivel)
        vel = 40 + 22 * self.nivel
        self.bolhas = []
        tentativas = 0
        while len(self.bolhas) < n and tentativas < 400:
            tentativas += 1
            x = random.uniform(140, LARGURA - 140)
            y = random.uniform(200, 560)
            if all(math.hypot(x - b[0], y - b[1]) > self.raio * 2.4 for b in self.bolhas):
                a = random.uniform(0, math.tau)
                self.bolhas.append([x, y, math.cos(a) * vel, math.sin(a) * vel, random.uniform(0, 6)])
        self.total = len(self.bolhas)

    def clique(self, pos):
        for b in reversed(self.bolhas):
            if math.hypot(pos[0] - b[0], pos[1] - b[1]) <= self.raio + 8:
                self.bolhas.remove(b)
                self.jogo.particulas.explodir((b[0], b[1]), [BRANCO, (200, 240, 255), (255, 190, 230)],
                                              14, 260, 0.45, (3, 6), 200)
                self.jogo.textos.adicionar(t("POP!"), (b[0], b[1] - 20), BRANCO, 12)
                self.jogo.som("revelar")
                if not self.bolhas:
                    self.ganhar(pos)
                return

    def atualizar(self, dt):
        r = self.raio
        for b in self.bolhas:
            b[0] += b[2] * dt
            b[1] += b[3] * dt
            b[4] += dt
            if not r + 30 < b[0] < LARGURA - r - 30:
                b[2] = -b[2]
                b[0] = _limitar(b[0], r + 30, LARGURA - r - 30)
            if not 170 + r < b[1] < 600 - r:
                b[3] = -b[3]
                b[1] = _limitar(b[1], 170 + r, 600 - r)

    def desenhar(self, tela):
        tela.blit(self.fundo(), (0, 0))
        img = _bolha_sup(self.raio)
        for b in self.bolhas:
            y = b[1] + math.sin(b[4] * 3) * 6
            tela.blit(img, img.get_rect(center=(int(b[0]), int(y))))
        if self.t > INTRO and self.bolhas:
            ui.desenhar_texto(tela, t("FALTAM {n}", n=len(self.bolhas)), (LARGURA // 2, 680), 14, TINTA, "center",
                              sombra=False)

    def desenhar_cursor(self, tela, pos):
        x, y = int(pos[0]), int(pos[1])
        pygame.draw.line(tela, TINTA, (x, y), (x + 26, y + 26), 6)
        pygame.draw.line(tela, (220, 225, 235), (x, y), (x + 26, y + 26), 3)
        pygame.draw.circle(tela, TINTA, (x + 28, y + 28), 9)
        pygame.draw.circle(tela, (240, 70, 90), (x + 28, y + 28), 7)


# ------------------------------------------------------------
# 4. PULE! — a colher deslizando na mesa
# ------------------------------------------------------------

class Pule(Micro):
    PALAVRA = "PULE!"
    DICA = "ESPAÇO, ↑ OU CLIQUE"
    COR = (130, 255, 150)
    FUNDO = ((255, 228, 175), (250, 190, 125))
    SOBREVIVER = True
    MESA = 606
    OX = 300
    ALT = 90

    @classmethod
    def decorar(cls, sup):
        # Quadro na parede
        pygame.draw.rect(sup, TINTA, (660, 120, 220, 160), border_radius=6)
        pygame.draw.rect(sup, (200, 150, 90), (666, 126, 208, 148), border_radius=4)
        pygame.draw.rect(sup, (150, 210, 255), (682, 142, 176, 116))
        pygame.draw.circle(sup, AMARELO, (820, 176), 18)
        pygame.draw.polygon(sup, (90, 170, 80), [(682, 258), (740, 190), (800, 258)])
        pygame.draw.polygon(sup, (70, 150, 70), [(760, 258), (820, 210), (858, 258)])
        # Toalha xadrez
        pygame.draw.rect(sup, BRANCO, (0, cls.MESA, LARGURA, ALTURA - cls.MESA))
        for x in range(0, LARGURA, 40):
            for y in range(cls.MESA, ALTURA, 40):
                if (x // 40 + (y - cls.MESA) // 40) % 2 == 0:
                    pygame.draw.rect(sup, (230, 80, 80), (x, y, 40, 40))
        pygame.draw.rect(sup, TINTA, (0, cls.MESA - 4, LARGURA, 6))

    def preparar(self):
        self.ox = float(self.OX)
        self.oy = self.MESA - self.ALT / 2
        self.vx = 0.0
        self.vy = 0.0
        self.no_chao = True
        self.caiu = False
        self.ang = 0.0
        self.vel = 420 + 30 * self.nivel
        x = LARGURA + 90 + random.uniform(0, 160)
        self.colheres = [x]
        extras = 0 if self.nivel < 2 else (1 if self.nivel < 5 else 2)
        for _ in range(extras):
            x += random.uniform(420, 500) * self.vel / 420
            self.colheres.append(x)
        # A última colher precisa passar antes do tempo acabar
        limite = self.OX + self.vel * 3.3
        if self.colheres[-1] > limite:
            fator = (limite - self.OX) / (self.colheres[-1] - self.OX)
            self.colheres = [self.OX + (c - self.OX) * fator for c in self.colheres]

    def tecla(self, k):
        if k in ACAO or k in CIMA:
            self._pular()

    def clique(self, pos):
        self._pular()

    def _pular(self):
        if self.no_chao and not self.caiu:
            self.vy = -1000
            self.no_chao = False
            self.jogo.som("pulo")
            self.jogo.particulas.explodir((self.ox, self.MESA), [BRANCO, (240, 220, 200)], 8, 140, 0.35, (3, 6))

    def atualizar(self, dt):
        for i in range(len(self.colheres)):
            self.colheres[i] -= self.vel * dt
        chao = self.MESA - self.ALT / 2
        if not self.no_chao or self.caiu:
            self.vy += 2400 * dt
            self.oy += self.vy * dt
            self.ox += self.vx * dt
            if self.caiu:
                self.ang += 420 * dt
            if self.oy >= chao:
                self.oy = chao
                self.vy = 0
                self.vx = 0
                if not self.no_chao and not self.caiu:
                    self.jogo.particulas.explodir((self.ox, self.MESA), [BRANCO], 6, 120, 0.3, (2, 5))
                self.no_chao = True
        if self.resultado is not None:
            return
        for x in self.colheres:
            if abs(x - self.ox) < 80 + 22 and self.oy + self.ALT / 2 > self.MESA - 26:
                self.caiu = True
                self.no_chao = False
                self.vx = -240
                self.vy = -650
                self.jogo.textos.adicionar(t("TOING!"), (self.ox, self.oy - 70), BRANCO, 18)
                self.perder((self.ox, self.oy - 40))
                return
        if all(x + 90 < self.ox - 40 for x in self.colheres):
            self.ganhar((self.ox, self.oy - 60))

    def desenhar(self, tela):
        tela.blit(self.fundo(), (0, 0))
        alt_pulo = _limitar((self.MESA - self.ALT / 2 - self.oy) / 160, 0, 1)
        sombra = pygame.Rect(0, 0, 70 - 30 * alt_pulo, 12)
        sombra.center = (self.ox, self.MESA + 4)
        pygame.draw.ellipse(tela, (150, 60, 60), sombra)
        img = _colher()
        for x in self.colheres:
            tela.blit(img, img.get_rect(midbottom=(int(x), self.MESA + 4)))
        _desenhar_ovo(tela, self.jogador, (self.ox, self.oy), self.ALT, self.ang)


# ------------------------------------------------------------
# 5. LIMPE! — esfregar o ovo sujo de lama
# ------------------------------------------------------------

class Limpe(Micro):
    PALAVRA = "LIMPE!"
    DICA = "ESFREGUE COM O MOUSE"
    COR = (150, 230, 255)
    FUNDO = ((255, 212, 232), (235, 160, 200))
    CURSOR = True
    CENTRO = (512, 410)
    ALT = 300

    @classmethod
    def decorar(cls, sup):
        _azulejos(sup, (255, 230, 240), 0, 620, 60)
        pygame.draw.rect(sup, (230, 140, 180), (0, 620, LARGURA, 100))
        pygame.draw.rect(sup, TINTA, (0, 616, LARGURA, 6))
        for x in (120, 900):
            for k in range(4):
                pygame.draw.circle(sup, (255, 240, 250), (x + k * 18 - 27, 590 - k * 30), 14 - k * 2, 3)

    def preparar(self):
        n = min(6, 4 + self.nivel // 3)
        cx, cy = self.CENTRO
        self.manchas = []
        tentativas = 0
        while len(self.manchas) < n and tentativas < 500:
            tentativas += 1
            a = random.uniform(0, math.tau)
            rr = math.sqrt(random.random())
            x = cx + math.cos(a) * rr * 95
            y = cy + math.sin(a) * rr * 115
            if all(math.hypot(x - m["x"], y - m["y"]) > 58 for m in self.manchas):
                r = random.uniform(22, 32)
                pedacos = [(random.uniform(-0.6, 0.6) * r, random.uniform(-0.5, 0.5) * r,
                            random.uniform(0.45, 0.75) * r) for _ in range(4)]
                self.manchas.append(dict(x=x, y=y, r=r, suj=1.0, pedacos=pedacos))
        self.espuma = 0.0
        self.dureza = 160           # pixels esfregados por mancha

    def mover(self, pos, rel):
        if self.resultado is not None:
            return
        d = math.hypot(*rel)
        if d <= 0:
            return
        esfregou = False
        for m in self.manchas:
            if m["suj"] > 0 and math.hypot(pos[0] - m["x"], pos[1] - m["y"]) < m["r"] + 28:
                esfregou = True
                m["suj"] -= d / self.dureza
                if m["suj"] <= 0:
                    m["suj"] = 0
                    self.jogo.particulas.explodir((m["x"], m["y"]), [BRANCO, AMARELO, (200, 240, 255)],
                                                  10, 200, 0.4, (2, 5), 100)
                    self.jogo.som("revelar", 0.7)
        if esfregou:
            self.espuma += d
            if self.espuma > 28:
                self.espuma = 0
                self.jogo.particulas.explodir(pos, [BRANCO, (220, 240, 255)], 3, 90, 0.5, (4, 8), -80)
        if all(m["suj"] <= 0 for m in self.manchas):
            self.ganhar((self.CENTRO[0], self.CENTRO[1] - 100))

    def desenhar(self, tela):
        tela.blit(self.fundo(), (0, 0))
        cx, cy = self.CENTRO
        pygame.draw.ellipse(tela, (200, 110, 150), (cx - 110, 596, 220, 30))
        self.jogador.desenhar(tela, (cx, cy + math.sin(self.t * 3) * 4), self.ALT)
        dy = math.sin(self.t * 3) * 4
        for m in self.manchas:
            if m["suj"] <= 0:
                continue
            s = 0.35 + 0.65 * m["suj"]
            cor = ui.misturar((180, 140, 100), (110, 70, 35), m["suj"])
            pygame.draw.circle(tela, cor, (int(m["x"]), int(m["y"] + dy)), int(m["r"] * s))
            for px, py, pr in m["pedacos"]:
                pygame.draw.circle(tela, cor, (int(m["x"] + px * s), int(m["y"] + py * s + dy)), int(pr * s))
        if self.resultado:
            for k in range(5):
                a = self.t * 3 + k * math.tau / 5
                ui.estrela(tela, (cx + math.cos(a) * 170, cy + math.sin(a) * 180), 12, BRANCO, a)

    def desenhar_cursor(self, tela, pos):
        r = pygame.Rect(0, 0, 70, 46)
        r.center = (int(pos[0]), int(pos[1]))
        pygame.draw.rect(tela, TINTA, r.inflate(6, 6), border_radius=12)
        pygame.draw.rect(tela, (255, 220, 70), r, border_radius=10)
        pygame.draw.rect(tela, (90, 190, 110), (r.x, r.y, r.w, 12), border_top_left_radius=10,
                         border_top_right_radius=10)
        for dx, dy in ((-18, 6), (4, 12), (20, 4), (-6, -2)):
            pygame.draw.circle(tela, (220, 170, 40), (r.centerx + dx, r.centery + dy), 4)


# ------------------------------------------------------------
# 6. APERTE! — as setas na ordem (pista de dança)
# ------------------------------------------------------------

TECLA_DIRECAO = {pygame.K_UP: 0, pygame.K_w: 0, pygame.K_RIGHT: 1, pygame.K_d: 1,
                 pygame.K_DOWN: 2, pygame.K_s: 2, pygame.K_LEFT: 3, pygame.K_a: 3}


class Aperte(Micro):
    PALAVRA = "APERTE!"
    DICA = "AS SETAS NA ORDEM"
    COR = (255, 130, 220)
    FUNDO = ((70, 40, 120), (25, 15, 60))
    LADO = 100

    @classmethod
    def decorar(cls, sup):
        # Holofotes
        for x, cor in ((180, (110, 70, 170)), (512, (100, 60, 160)), (840, (110, 70, 170))):
            pygame.draw.polygon(sup, cor, [(x - 20, 0), (x + 20, 0), (x + 160, 620), (x - 160, 620)])
        # Pista de dança
        cores = [(255, 90, 160), (90, 200, 255), (255, 210, 70), (130, 240, 130)]
        for i, x in enumerate(range(0, LARGURA, 64)):
            for j, y in enumerate(range(620, ALTURA, 50)):
                pygame.draw.rect(sup, cores[(i + j * 3) % 4], (x + 2, y + 2, 60, 46))
        pygame.draw.rect(sup, TINTA, (0, 614, LARGURA, 8))
        rnd = random.Random(9)
        for _ in range(30):
            ui.estrela(sup, (rnd.randrange(LARGURA), rnd.randrange(20, 200)), rnd.randint(3, 6), (255, 240, 200))

    def preparar(self):
        self.n = min(6, 2 + self.nivel)
        self.seq = [random.randrange(4) for _ in range(self.n)]
        self.idx = 0
        self.erro = None
        self.pose = None
        self.t_pose = 0.0

    def _centro(self, i):
        total = self.n * self.LADO + (self.n - 1) * 16
        x0 = LARGURA // 2 - total // 2
        return (x0 + i * (self.LADO + 16) + self.LADO // 2, 280)

    def tecla(self, k):
        d = TECLA_DIRECAO.get(k)
        if d is None:
            return
        c = self._centro(self.idx)
        if d == self.seq[self.idx]:
            self.idx += 1
            self.pose = d
            self.t_pose = 0.3
            self.jogo.particulas.explodir(c, CONFETE, 10, 220, 0.4, (3, 6))
            self.jogo.som("ponto", 0.6)
            if self.idx == self.n:
                self.ganhar(c)
        else:
            self.erro = self.idx
            self.perder(c)

    def atualizar(self, dt):
        self.t_pose = max(0.0, self.t_pose - dt)

    def desenhar(self, tela):
        tela.blit(self.fundo(), (0, 0))
        for i, d in enumerate(self.seq):
            c = self._centro(i)
            r = pygame.Rect(0, 0, self.LADO, self.LADO)
            r.center = c
            if i < self.idx:
                fundo, borda, cor = (60, 170, 90), BRANCO, VERDE_OK
            elif i == self.erro:
                fundo, borda, cor = (170, 40, 60), BRANCO, VERMELHO_ERRO
            elif i == self.idx and self.resultado is None:
                pulso = int(4 * abs(math.sin(self.t * 8)))
                r.inflate_ip(pulso * 2, pulso * 2)
                fundo, borda, cor = (60, 50, 110), AMARELO, AMARELO
            else:
                fundo, borda, cor = (45, 35, 80), (140, 120, 190), (170, 150, 220)
            pygame.draw.rect(tela, TINTA, r.inflate(8, 8).move(0, 4), border_radius=18)
            pygame.draw.rect(tela, fundo, r, border_radius=16)
            pygame.draw.rect(tela, borda, r, 4, border_radius=16)
            _seta(tela, c, self.LADO * 0.62, d, cor)
        # O ovo dançando
        dx = dy = ang = 0
        if self.t_pose > 0:
            if self.pose == 0:
                dy = -30
            elif self.pose == 2:
                dy = 12
            elif self.pose == 1:
                dx, ang = 20, -15
            else:
                dx, ang = -20, 15
        else:
            dy = -abs(math.sin(self.t * 6)) * 8
        if self.resultado is False:
            ang = math.sin(self.t * 12) * 10
        _desenhar_ovo(tela, self.jogador, (LARGURA // 2 + dx, 520 + dy), 130, ang)


# ------------------------------------------------------------
# 7. PARE! — o ponteiro no verde
# ------------------------------------------------------------

class Pare(Micro):
    PALAVRA = "PARE!"
    DICA = "NO VERDE! ESPAÇO OU CLIQUE"
    COR = VERDE_OK
    FUNDO = ((255, 242, 205), (250, 200, 130))
    CENTRO = (512, 560)
    RAIO = 250

    @classmethod
    def decorar(cls, sup):
        pygame.draw.rect(sup, (200, 140, 90), (0, 600, LARGURA, 120))
        pygame.draw.rect(sup, TINTA, (0, 596, LARGURA, 6))
        for x in range(40, LARGURA, 120):
            pygame.draw.line(sup, (180, 120, 75), (x, 610), (x + 60, 710), 3)

    def preparar(self):
        self.meio = random.uniform(205, 335)
        self.meia = max(9.0, 15.0 - self.nivel)
        self.fase = random.uniform(0, math.tau)
        # Limite: o ponteiro nunca passa de ~450 graus/s (tempo real)
        self.rapidez = min(2.4 + 0.3 * self.nivel, 5.0 / self.jogo.vel)
        self.parado = False

    @property
    def angulo(self):
        return 180 + 180 * (0.5 - 0.5 * math.cos(self.fase))

    def _ponta(self, r):
        a = math.radians(self.angulo)
        return (self.CENTRO[0] + math.cos(a) * r, self.CENTRO[1] + math.sin(a) * r)

    def tecla(self, k):
        if k in ACAO:
            self._parar()

    def clique(self, pos):
        self._parar()

    def _parar(self):
        if self.parado:
            return
        self.parado = True
        ponta = self._ponta(self.RAIO - 30)
        if abs(self.angulo - self.meio) <= self.meia:
            self.jogo.textos.adicionar(t("NA MOSCA!"), (ponta[0], ponta[1] - 30), VERDE_OK, 16)
            self.ganhar(ponta)
        else:
            self.perder(ponta)

    def decidir(self):
        self.parado = True
        super().decidir()

    def atualizar(self, dt):
        if not self.parado:
            self.fase += self.rapidez * dt

    def desenhar(self, tela):
        tela.blit(self.fundo(), (0, 0))
        cx, cy = self.CENTRO
        img = _mostrador(self.RAIO)
        tela.blit(img, (cx - self.RAIO - 12, cy - self.RAIO - 12))
        # Zona verde
        pontos = []
        a0, a1 = self.meio - self.meia, self.meio + self.meia
        passos = 6
        for i in range(passos + 1):
            a = math.radians(a0 + (a1 - a0) * i / passos)
            pontos.append((cx + math.cos(a) * (self.RAIO - 4), cy + math.sin(a) * (self.RAIO - 4)))
        for i in range(passos, -1, -1):
            a = math.radians(a0 + (a1 - a0) * i / passos)
            pontos.append((cx + math.cos(a) * (self.RAIO - 74), cy + math.sin(a) * (self.RAIO - 74)))
        brilho = self.resultado and int(self.t * 10) % 2 == 0
        pygame.draw.polygon(tela, (180, 255, 180) if brilho else (70, 210, 90), pontos)
        pygame.draw.polygon(tela, TINTA, pontos, 3)
        # Ponteiro
        ponta = self._ponta(self.RAIO - 20)
        cor = VERDE_OK if self.resultado else VERMELHO_ERRO if self.resultado is False else (230, 50, 60)
        pygame.draw.line(tela, TINTA, (cx, cy), ponta, 12)
        pygame.draw.line(tela, cor, (cx, cy), ponta, 7)
        pygame.draw.circle(tela, TINTA, (cx, cy), 22)
        pygame.draw.circle(tela, (230, 50, 60), (cx, cy), 17)
        # Ovinho torcendo do lado
        dy = -abs(math.sin(self.t * 8)) * 10 if self.resultado else 0
        self.jogador.desenhar(tela, (140, 548 + dy), 90)


# ------------------------------------------------------------
# 8. ACHE! — o ovo diferente
# ------------------------------------------------------------

class Ache(Micro):
    PALAVRA = "ACHE!"
    DICA = "O OVO DIFERENTE"
    COR = AMARELO
    FUNDO = ((210, 255, 220), (130, 210, 170))
    CURSOR = True

    @classmethod
    def decorar(cls, sup):
        rnd = random.Random(21)
        for _ in range(26):
            x, y = rnd.randrange(LARGURA), rnd.randrange(ALTURA)
            pygame.draw.circle(sup, (190, 245, 205), (x, y), rnd.randint(10, 30))

    def preparar(self):
        if self.nivel == 0:
            cols, lins = 3, 2
        elif self.nivel <= 2:
            cols, lins = 4, 2
        elif self.nivel <= 4:
            cols, lins = 4, 3
        else:
            cols, lins = 5, 3
        self.alt = 96 if lins == 2 else 78
        limites = [len(assets.OVOS), min(7, len(assets.CABELOS)), len(assets.OLHOS), len(assets.BOCAS)]
        base = [random.randrange(n) for n in limites]
        if self.nivel == 0:
            parte = random.choice((0, 1))
        elif self.nivel < 3:
            parte = random.choice((0, 1, 2, 3))
        else:
            parte = random.choice((1, 2, 3, 3))
        dif = list(base)
        dif[parte] = random.choice([v for v in range(limites[parte]) if v != base[parte]])
        self.normal = tuple(base)
        self.dif = tuple(dif)
        n = cols * lins
        self.alvo = random.randrange(n)
        dx = (LARGURA - 240) / cols
        dy = 400 / lins
        self.posicoes = [(120 + dx * (i % cols + 0.5), 210 + dy * (i // cols + 0.5)) for i in range(n)]
        self.escolha = None

    def clique(self, pos):
        for i, (x, y) in enumerate(self.posicoes):
            r = pygame.Rect(0, 0, self.alt * 0.95, self.alt * 1.2)
            r.center = (x, y)
            if r.collidepoint(pos):
                self.escolha = i
                if i == self.alvo:
                    self.ganhar((x, y - 40))
                else:
                    self.perder((x, y - 40))
                return

    def desenhar(self, tela):
        tela.blit(self.fundo(), (0, 0))
        for i, (x, y) in enumerate(self.posicoes):
            bob = math.sin(self.t * 3 + i * 1.3) * 4
            pygame.draw.ellipse(tela, (100, 170, 130), (x - 36, y + self.alt * 0.45, 72, 16))
            apar = self.dif if i == self.alvo else self.normal
            self.jogador.desenhar(tela, (x, y + bob), self.alt, aparencia=apar)
        if self.resultado is not None:
            x, y = self.posicoes[self.alvo]
            pygame.draw.circle(tela, TINTA, (int(x), int(y)), int(self.alt * 0.75), 8)
            pygame.draw.circle(tela, VERDE_OK, (int(x), int(y)), int(self.alt * 0.75), 4)
            if self.escolha is not None and self.escolha != self.alvo:
                x, y = self.posicoes[self.escolha]
                for s in (-1, 1):
                    pygame.draw.line(tela, TINTA, (x - 30, y - 30 * s), (x + 30, y + 30 * s), 12)
                    pygame.draw.line(tela, VERMELHO_ERRO, (x - 30, y - 30 * s), (x + 30, y + 30 * s), 6)

    def desenhar_cursor(self, tela, pos):
        x, y = int(pos[0]), int(pos[1])
        pygame.draw.line(tela, TINTA, (x + 14, y + 14), (x + 34, y + 34), 10)
        pygame.draw.line(tela, (150, 90, 50), (x + 16, y + 16), (x + 32, y + 32), 5)
        pygame.draw.circle(tela, TINTA, (x, y), 22, 7)
        pygame.draw.circle(tela, (240, 240, 250), (x, y), 19, 3)


# ------------------------------------------------------------
# 9. SOPRE! — a vela do bolo
# ------------------------------------------------------------

class Sopre(Micro):
    PALAVRA = "SOPRE!"
    DICA = "APERTE ESPAÇO RÁPIDO!"
    COR = (255, 180, 90)
    FUNDO = ((90, 60, 115), (40, 25, 60))
    OVO = (290, 470)
    VELA = (700, 420)       # topo do pavio

    @classmethod
    def decorar(cls, sup):
        # Varal de bandeirinhas
        cores = [(255, 90, 120), AMARELO, (110, 200, 255), (130, 230, 130)]
        pontos = [(x, 70 + math.sin(x / 160) * 18) for x in range(0, LARGURA + 1, 16)]
        pygame.draw.lines(sup, (230, 220, 200), False, pontos, 3)
        for i, x in enumerate(range(20, LARGURA, 70)):
            y = 70 + math.sin(x / 160) * 18
            pygame.draw.polygon(sup, cores[i % 4], [(x - 20, y), (x + 20, y), (x, y + 38)])
        # Mesa
        pygame.draw.rect(sup, (150, 95, 60), (0, 590, LARGURA, 130))
        pygame.draw.rect(sup, TINTA, (0, 586, LARGURA, 6))
        for y in range(610, ALTURA, 26):
            pygame.draw.line(sup, (130, 80, 50), (0, y), (LARGURA, y), 2)

    def preparar(self):
        self.precisa = min(15, 7 + self.nivel)
        self.sopros = 0
        self.chama = 1.0
        self.bochecha = 0.0
        self.ventos = []

    def tecla(self, k):
        if k in ACAO:
            self._soprar()

    def clique(self, pos):
        self._soprar()

    def _soprar(self):
        self.sopros += 1
        self.bochecha = 0.14
        for _ in range(3):
            self.ventos.append([self.OVO[0] + 70, self.OVO[1] + random.uniform(-10, 30), 0.0])
        self.jogo.som("asa", 0.6)
        if self.sopros >= self.precisa:
            x, y = self.VELA
            self.jogo.particulas.explodir((x, y - 20), [(150, 150, 160), (200, 200, 210), (110, 110, 120)],
                                          18, 120, 1.0, (5, 10), -160)
            self.jogo.textos.adicionar(t("PARABÉNS!"), (x, y - 120), AMARELO, 18)
            self.ganhar((x, y - 40))

    def atualizar(self, dt):
        alvo = 0.0 if self.resultado else max(0.0, 1 - self.sopros / self.precisa)
        self.chama += (alvo - self.chama) * min(1.0, dt * 12)
        self.bochecha = max(0.0, self.bochecha - dt)
        # Vento voa em direção à vela
        vx, vy = self.VELA[0] - self.OVO[0] - 70, self.VELA[1] - self.OVO[1]
        n = math.hypot(vx, vy)
        for v in self.ventos:
            v[0] += vx / n * 900 * dt
            v[1] += vy / n * 900 * dt
            v[2] += dt
        self.ventos = [v for v in self.ventos if v[2] < 0.4]

    def desenhar(self, tela):
        tela.blit(self.fundo(), (0, 0))
        x, y = self.VELA
        bolo = _bolo()
        tela.blit(bolo, bolo.get_rect(midbottom=(x, 600)))
        # Vela listrada
        pygame.draw.rect(tela, TINTA, (x - 11, y + 4, 22, 90), border_radius=4)
        pygame.draw.rect(tela, (120, 200, 255), (x - 8, y + 6, 16, 86), border_radius=3)
        for k in range(4):
            pygame.draw.line(tela, BRANCO, (x - 8, y + 16 + k * 20), (x + 8, y + 8 + k * 20), 4)
        pygame.draw.line(tela, TINTA, (x, y + 6), (x, y - 4), 3)
        # Chama tremendo (encolhe a cada sopro)
        if self.chama > 0.04:
            tremor = 1 + 0.12 * math.sin(self.t * 40)
            h = 58 * self.chama * tremor
            w = 30 * self.chama
            lado = -self.bochecha * 60
            pygame.draw.ellipse(tela, (255, 140, 40), (x - w / 2 + lado * 0.3, y - h, w, h))
            pygame.draw.ellipse(tela, (255, 235, 120), (x - w / 4 + lado * 0.3, y - h * 0.6, w / 2, h * 0.55))
        # Vento
        for vx, vy, vida in self.ventos:
            pygame.draw.line(tela, (230, 240, 255), (vx - 22, vy), (vx, vy), 4)
        # O ovo soprando (bochechas cheias)
        self.jogador.desenhar(tela, self.OVO, 150)
        if self.bochecha > 0:
            ox, oy = self.OVO
            pygame.draw.circle(tela, (255, 140, 160), (ox - 38, oy + 18), 16)
            pygame.draw.circle(tela, (255, 140, 160), (ox + 38, oy + 18), 16)
        # Barra de sopro
        barra = pygame.Rect(0, 0, 260, 18)
        barra.midtop = (self.OVO[0], 640)
        pygame.draw.rect(tela, TINTA, barra.inflate(8, 8), border_radius=10)
        k = min(1.0, self.sopros / self.precisa)
        pygame.draw.rect(tela, (200, 230, 255), (barra.x, barra.y, max(4, int(barra.w * k)), barra.h),
                         border_radius=8)


# ------------------------------------------------------------
# 10. GUIE! — a abelha até a flor (sem encostar nos cactos)
# ------------------------------------------------------------

class Guie(Micro):
    PALAVRA = "GUIE!"
    DICA = "LEVE A ABELHA ATÉ A FLOR"
    COR = AMARELO
    FUNDO = ((150, 215, 255), (200, 240, 205))

    @classmethod
    def decorar(cls, sup):
        _nuvens(sup, [(120, 140), (560, 100), (840, 180)])
        pygame.draw.ellipse(sup, (140, 210, 120), (-200, 560, 800, 400))
        pygame.draw.ellipse(sup, (120, 195, 105), (400, 590, 900, 400))
        rnd = random.Random(5)
        for _ in range(40):
            x, y = rnd.randrange(LARGURA), rnd.randrange(630, ALTURA)
            pygame.draw.circle(sup, rnd.choice([BRANCO, AMARELO, (255, 150, 200)]), (x, y), 4)

    def preparar(self):
        self.bx, self.by = 130.0, random.uniform(260, 560)
        self.fx, self.fy = 880.0, random.uniform(240, 560)
        n = min(5, 2 + self.nivel)
        mover = self.nivel >= 3
        self.cactos = []
        tentativas = 0
        while len(self.cactos) < n and tentativas < 600:
            tentativas += 1
            x, y = random.uniform(300, 740), random.uniform(190, 630)
            if math.hypot(x - self.bx, y - self.by) < 150 or math.hypot(x - self.fx, y - self.fy) < 140:
                continue
            if all(math.hypot(x - c[0], y - c[1]) > 115 for c in self.cactos):
                vy = random.choice((-1, 1)) * (60 + 20 * self.nivel) if mover else 0
                self.cactos.append([x, y, vy])
        self.esquerda = False
        self.rastro = []
        self.t_rastro = 0.0
        self.tonto = False

    def atualizar(self, dt):
        if self.resultado is None:
            ex, ey = self.jogo.eixo()
            dx = dy = 0.0
            if ex or ey:
                n = math.hypot(ex, ey)
                dx, dy = ex / n * 430 * dt, ey / n * 430 * dt
            elif self.jogo.mouse:
                vx, vy = self.jogo.cursor[0] - self.bx, self.jogo.cursor[1] - self.by
                d = math.hypot(vx, vy)
                if d > 2:
                    passo = min(d, 500 * dt)
                    dx, dy = vx / d * passo, vy / d * passo
            if dx < -0.5:
                self.esquerda = True
            elif dx > 0.5:
                self.esquerda = False
            self.bx = _limitar(self.bx + dx, 40, LARGURA - 40)
            self.by = _limitar(self.by + dy, 150, 680)
        for c in self.cactos:
            c[1] += c[2] * dt
            if not 190 < c[1] < 630:
                c[2] = -c[2]
                c[1] = _limitar(c[1], 190, 630)
        self.t_rastro += dt
        if self.t_rastro > 0.05:
            self.t_rastro = 0.0
            self.rastro.append((self.bx, self.by))
            self.rastro = self.rastro[-12:]
        if self.resultado is not None:
            return
        if math.hypot(self.bx - self.fx, self.by - (self.fy - 20)) < 52:
            self.bx, self.by = self.fx, self.fy - 36
            self.jogo.textos.adicionar(t("MEL!"), (self.fx, self.fy - 90), AMARELO, 18)
            self.ganhar((self.fx, self.fy - 40))
            return
        for c in self.cactos:
            d = math.hypot(self.bx - c[0], self.by - c[1])
            if d < 52:
                self.tonto = True
                self.bx += (self.bx - c[0]) / max(1, d) * 40
                self.by += (self.by - c[1]) / max(1, d) * 40
                self.jogo.textos.adicionar(t("AI!"), (self.bx, self.by - 50), VERMELHO_ERRO, 18)
                self.perder((self.bx, self.by))
                return

    def desenhar(self, tela):
        tela.blit(self.fundo(), (0, 0))
        flor = _flor()
        tela.blit(flor, flor.get_rect(center=(int(self.fx), int(self.fy + 26))))
        cacto = _cacto()
        for x, y, _ in self.cactos:
            tela.blit(cacto, cacto.get_rect(center=(int(x), int(y))))
        for i, (x, y) in enumerate(self.rastro[:-1]):
            if i % 2 == 0:
                pygame.draw.circle(tela, (255, 255, 255), (int(x), int(y + 8)), 3)
        quadro = int(self.t * 22) % 2
        img = _abelha(quadro)
        if self.esquerda:
            img = _virado(("abelha", quadro), img)
        y = self.by + math.sin(self.t * 10) * 3
        tela.blit(img, img.get_rect(center=(int(self.bx), int(y))))
        if self.tonto:
            for k in range(3):
                a = self.t * 7 + k * math.tau / 3
                ui.estrela(tela, (self.bx + math.cos(a) * 30, self.by - 34 + math.sin(a) * 8), 7, AMARELO, a)


# ------------------------------------------------------------
# 11. ACORDE! — chacoalhar a cama do ovo dorminhoco
# ------------------------------------------------------------

class Acorde(Micro):
    PALAVRA = "ACORDE!"
    DICA = "← → ← →  OU CHACOALHE O MOUSE"
    COR = (255, 210, 120)
    FUNDO = ((60, 70, 140), (25, 30, 72))
    OVO = (512, 440)
    ALT = 130

    @classmethod
    def decorar(cls, sup):
        # Janela com lua
        janela = pygame.Rect(760, 90, 200, 170)
        pygame.draw.rect(sup, TINTA, janela.inflate(16, 16), border_radius=8)
        pygame.draw.rect(sup, (20, 24, 60), janela)
        pygame.draw.circle(sup, (255, 245, 190), (820, 150), 34)
        pygame.draw.circle(sup, (20, 24, 60), (836, 140), 30)
        for x, y in ((900, 120), (930, 210), (790, 230)):
            ui.estrela(sup, (x, y), 6, (255, 250, 200))
        pygame.draw.line(sup, TINTA, (janela.centerx, janela.y), (janela.centerx, janela.bottom), 6)
        pygame.draw.line(sup, TINTA, (janela.x, janela.centery), (janela.right, janela.centery), 6)
        # Papel de parede
        for x in range(30, LARGURA, 90):
            for y in range(40, 560, 90):
                if not janela.inflate(40, 40).collidepoint(x, y):
                    pygame.draw.circle(sup, (75, 85, 160), (x + (y // 90) % 2 * 45, y), 6)
        # Chão
        pygame.draw.rect(sup, (120, 80, 60), (0, 590, LARGURA, 130))
        pygame.draw.rect(sup, TINTA, (0, 586, LARGURA, 6))
        for y in range(620, ALTURA, 34):
            pygame.draw.line(sup, (100, 65, 50), (0, y), (LARGURA, y), 3)

    def preparar(self):
        self.precisa = min(16, 8 + self.nivel)
        self.balancos = 0
        self.ultimo = 0
        self.tremor = 0.0
        self.acum = 0.0
        self.zs = []
        self.t_z = 0.0
        self.t_acordou = 0.0

    def tecla(self, k):
        d = -1 if k in ESQ else 1 if k in DIR else 0
        if d and d != self.ultimo:
            self.ultimo = d
            self._chacoalhar()

    def mover(self, pos, rel):
        self.acum += rel[0]
        if abs(self.acum) > 40:
            d = 1 if self.acum > 0 else -1
            self.acum = 0.0
            if d != self.ultimo:
                self.ultimo = d
                self._chacoalhar()

    def _chacoalhar(self):
        self.balancos += 1
        self.tremor = 1.0
        self.jogo.som("virar", 0.5)
        if self.balancos >= self.precisa:
            self.jogo.textos.adicionar(t("BOM DIA!"), (self.OVO[0], self.OVO[1] - 160), AMARELO, 22)
            self.jogo.som("boing")
            self.ganhar((self.OVO[0], self.OVO[1] - 80))

    def atualizar(self, dt):
        self.tremor = max(0.0, self.tremor - dt * 4)
        if self.resultado:
            self.t_acordou += dt
        else:
            self.t_z += dt
            if self.t_z > 0.45:
                self.t_z = 0.0
                self.zs.append([self.OVO[0] + 60, self.OVO[1] - 60, 0.0])
        for z in self.zs:
            z[0] += 30 * dt
            z[1] -= 60 * dt
            z[2] += dt
        self.zs = [z for z in self.zs if z[2] < 1.2]

    def desenhar(self, tela):
        tela.blit(self.fundo(), (0, 0))
        dx = math.sin(self.t * 60) * self.tremor * 14
        cama = _cama()
        tela.blit(cama, cama.get_rect(midtop=(int(self.OVO[0] + dx), 340)))
        ox, oy = self.OVO[0] + dx, self.OVO[1]
        if self.resultado:
            # Acordou! Pula para fora do cobertor
            k = min(1.0, self.t_acordou / 0.25)
            oy -= 90 * k + abs(math.sin(self.t_acordou * 9)) * 20 * k
        self.jogador.desenhar(tela, (ox, oy), self.ALT)
        if not self.resultado:
            # Máscara de dormir
            topo = oy - self.ALT / 2
            mascara = pygame.Rect(0, 0, self.ALT * 0.95, 30)
            mascara.center = (ox, topo + self.ALT * 0.4)
            pygame.draw.rect(tela, TINTA, mascara.inflate(6, 6), border_radius=14)
            pygame.draw.rect(tela, (90, 110, 220), mascara, border_radius=12)
            for s in (-1, 1):
                c = (mascara.centerx + s * 22, mascara.centery - 4)
                pygame.draw.arc(tela, BRANCO, (c[0] - 12, c[1] - 8, 24, 16), math.pi * 1.1, math.pi * 1.9, 3)
        # Cobertor por cima
        cob = pygame.Rect(0, 0, 400, 90)
        cob.midtop = (ox if not self.resultado else self.OVO[0] + dx, self.OVO[1] + 22)
        pygame.draw.rect(tela, TINTA, cob.inflate(8, 8), border_radius=18)
        pygame.draw.rect(tela, (230, 110, 140), cob, border_radius=16)
        pygame.draw.rect(tela, (255, 190, 210), (cob.x, cob.y, cob.w, 18), border_top_left_radius=16,
                         border_top_right_radius=16)
        for i in range(8):
            pygame.draw.circle(tela, (255, 200, 220), (cob.x + 30 + i * 48, cob.y + 50 + (i % 2) * 14), 7)
        for x, y, vida in self.zs:
            tam = 16 if vida < 0.4 else 20
            ui.desenhar_texto(tela, "Z", (x, y), tam, (200, 210, 255), "center")
        # Progresso
        barra = pygame.Rect(0, 0, 300, 18)
        barra.midtop = (LARGURA // 2, 650)
        pygame.draw.rect(tela, TINTA, barra.inflate(8, 8), border_radius=10)
        k = min(1.0, self.balancos / self.precisa)
        pygame.draw.rect(tela, AMARELO, (barra.x, barra.y, max(4, int(barra.w * k)), barra.h), border_radius=8)


# ------------------------------------------------------------
# 12. CONTE! — quantos pintinhos?
# ------------------------------------------------------------

TECLA_OPCAO = {pygame.K_LEFT: 0, pygame.K_a: 0, pygame.K_1: 0, pygame.K_KP1: 0,
               pygame.K_DOWN: 1, pygame.K_s: 1, pygame.K_UP: 1, pygame.K_w: 1,
               pygame.K_2: 1, pygame.K_KP2: 1,
               pygame.K_RIGHT: 2, pygame.K_d: 2, pygame.K_3: 2, pygame.K_KP3: 2}
SETA_OPCAO = ["←", "↓", "→"]


class Conte(Micro):
    PALAVRA = "CONTE!"
    DICA = "QUANTOS PINTINHOS?"
    COR = AMARELO
    FUNDO = ((255, 238, 175), (210, 232, 130))
    MOSTRA = 2.0
    AREA = pygame.Rect(170, 250, 684, 300)

    @classmethod
    def decorar(cls, sup):
        # Cerca
        pygame.draw.rect(sup, (230, 210, 170), (0, 180, LARGURA, 12))
        pygame.draw.rect(sup, (230, 210, 170), (0, 212, LARGURA, 12))
        for x in range(10, LARGURA, 46):
            pygame.draw.rect(sup, TINTA, (x - 2, 158, 22, 90), border_radius=4)
            pygame.draw.rect(sup, (245, 230, 195), (x, 160, 18, 86), border_radius=3)
        pygame.draw.rect(sup, (190, 210, 110), (0, 248, LARGURA, ALTURA - 248))
        rnd = random.Random(13)
        for _ in range(50):
            x, y = rnd.randrange(LARGURA), rnd.randrange(260, ALTURA)
            pygame.draw.line(sup, (160, 190, 90), (x, y), (x + 4, y - 8), 2)

    def preparar(self):
        self.n = random.randint(3, 5 + min(3, self.nivel))
        vel = 40 + 15 * self.nivel if self.nivel >= 2 else 0
        self.pintos = []
        tentativas = 0
        a = self.AREA.inflate(-60, -60)
        while len(self.pintos) < self.n and tentativas < 800:
            tentativas += 1
            x, y = random.uniform(a.left, a.right), random.uniform(a.top, a.bottom)
            if all(math.hypot(x - p[0], y - p[1]) > 78 for p in self.pintos):
                self.pintos.append([x, y, random.uniform(0, 6), random.choice((-1, 1)) * vel])
        self.n = len(self.pintos)
        opcoes = {self.n}
        while len(opcoes) < 3:
            c = self.n + random.choice((-2, -1, 1, 2))
            if c >= 1:
                opcoes.add(c)
        self.opcoes = list(opcoes)
        random.shuffle(self.opcoes)
        self.botoes = []
        for i in range(3):
            r = pygame.Rect(0, 0, 170, 90)
            r.center = (292 + i * 220, 620)
            self.botoes.append(r)
        self.escolha = None

    @property
    def disponivel(self):
        return self.t >= self.MOSTRA

    def tecla(self, k):
        if self.disponivel and k in TECLA_OPCAO:
            self._responder(TECLA_OPCAO[k])

    def clique(self, pos):
        if not self.disponivel:
            return
        for i, r in enumerate(self.botoes):
            if r.collidepoint(pos):
                self._responder(i)
                return

    def _responder(self, i):
        self.escolha = i
        c = self.botoes[i].center
        if self.opcoes[i] == self.n:
            self.ganhar((c[0], c[1] - 60))
        else:
            self.perder((c[0], c[1] - 60))

    def atualizar(self, dt):
        if self.t >= self.MOSTRA:
            return
        a = self.AREA.inflate(-40, -40)
        for p in self.pintos:
            p[0] += p[3] * dt
            p[2] += dt
            if not a.left < p[0] < a.right:
                p[3] = -p[3]
                p[0] = _limitar(p[0], a.left, a.right)

    def desenhar(self, tela):
        tela.blit(self.fundo(), (0, 0))
        coberto = self.disponivel and self.escolha is None and self.resultado is None
        if not coberto:
            for x, y, fase, vx in self.pintos:
                quadro = int(fase * 6) % 2
                img = _pintinho(quadro)
                if vx < 0:
                    img = _virado(("pintinho", quadro), img)
                pulo = abs(math.sin(fase * 7)) * 12
                pygame.draw.ellipse(tela, (160, 185, 90), (x - 18, y + 22, 36, 10))
                tela.blit(img, img.get_rect(center=(int(x), int(y - pulo))))
            if self.resultado is not None:
                ui.desenhar_texto(tela, t("ERAM {n}!", n=self.n), (LARGURA // 2, 230), 20, TINTA, "center",
                                  sombra=False)
        else:
            # Caixote caindo por cima dos pintinhos
            k = min(1.0, (self.t - self.MOSTRA) / 0.15)
            caixa = self.AREA.move(0, -int((1 - k) * 420))
            pygame.draw.rect(tela, TINTA, caixa.inflate(10, 10), border_radius=10)
            pygame.draw.rect(tela, (200, 140, 80), caixa, border_radius=8)
            for y in range(caixa.y + 12, caixa.bottom - 10, 48):
                pygame.draw.rect(tela, (170, 110, 60), (caixa.x + 10, y, caixa.w - 20, 36), border_radius=4)
            pygame.draw.line(tela, (150, 95, 50), caixa.topleft, caixa.bottomright, 10)
            ui.desenhar_texto(tela, "?", caixa.center, 72, AMARELO, "center")
        if self.disponivel:
            for i, r in enumerate(self.botoes):
                escolhido = i == self.escolha
                certo = self.resultado is not None and self.opcoes[i] == self.n
                cor = (60, 170, 90) if certo else (170, 40, 60) if escolhido else (60, 60, 110)
                ui.painel(tela, r, cor, BRANCO if not escolhido else AMARELO, 16, 4)
                ui.desenhar_texto(tela, str(self.opcoes[i]), (r.centerx, r.centery - 8), 32, BRANCO, "center")
                ui.desenhar_texto(tela, SETA_OPCAO[i], (r.centerx, r.bottom - 14), 12, (220, 220, 255), "center")


# ------------------------------------------------------------
# 13. ENCHA! — o copo de leite até a linha
# ------------------------------------------------------------

class Encha(Micro):
    PALAVRA = "ENCHA!"
    DICA = "SEGURE ESPAÇO E SOLTE NA LINHA"
    COR = BRANCO
    FUNDO = ((190, 230, 255), (130, 185, 235))
    COPO = pygame.Rect(432, 250, 160, 330)

    @classmethod
    def decorar(cls, sup):
        _azulejos(sup, (170, 215, 250), 0, 580, 48)
        pygame.draw.rect(sup, (170, 120, 80), (0, 584, LARGURA, 136))
        pygame.draw.rect(sup, TINTA, (0, 580, LARGURA, 8))
        pygame.draw.rect(sup, (200, 150, 100), (0, 588, LARGURA, 14))

    def preparar(self):
        self.meio = random.uniform(0.55, 0.8)
        self.meia = max(0.045, 0.085 - 0.008 * self.nivel)
        self.leite = 0.0
        self.enchendo = False
        self.taxa = 0.36 + 0.045 * self.nivel
        self.derramou = False

    def _na_linha(self):
        return abs(self.leite - self.meio) <= self.meia

    def _superficie(self):
        return (self.COPO.centerx, self.COPO.bottom - self.COPO.h * self.leite)

    def tecla(self, k):
        if k in ACAO:
            self.enchendo = True

    def solta(self, k):
        if k in ACAO:
            self._soltar()

    def clique(self, pos):
        self.enchendo = True

    def solta_clique(self):
        self._soltar()

    def _soltar(self):
        if not self.enchendo:
            return
        self.enchendo = False
        if self._na_linha():
            self.jogo.textos.adicionar(t("NA MEDIDA!"), (self.COPO.centerx, self.COPO.y - 40), VERDE_OK, 16)
            self.ganhar(self._superficie())

    def decidir(self):
        self.enchendo = False
        if self._na_linha():
            self.ganhar(self._superficie())
        else:
            self.perder(self._superficie())

    def atualizar(self, dt):
        if not self.enchendo or self.resultado is not None:
            return
        self.leite += self.taxa * dt
        if self.leite > self.meio + self.meia:
            self.enchendo = False
            self.derramou = True
            x, y = self._superficie()
            self.jogo.particulas.explodir((x, y), [BRANCO, (235, 240, 255)], 16, 260, 0.6, (3, 7))
            self.jogo.textos.adicionar(t("PASSOU!"), (x, y - 40), VERMELHO_ERRO, 18)
            self.perder((x, y))

    def desenhar(self, tela):
        tela.blit(self.fundo(), (0, 0))
        c = self.COPO
        # Fundo do copo
        pygame.draw.rect(tela, (215, 235, 250), c, border_bottom_left_radius=18, border_bottom_right_radius=18)
        # Leite
        h = int(c.h * self.leite)
        if h > 0:
            pygame.draw.rect(tela, (250, 250, 245), (c.x, c.bottom - h, c.w, h),
                             border_bottom_left_radius=18, border_bottom_right_radius=18)
            pygame.draw.ellipse(tela, BRANCO, (c.x, c.bottom - h - 6, c.w, 12))
        # Faixa da medida
        y0 = c.bottom - c.h * (self.meio + self.meia)
        y1 = c.bottom - c.h * (self.meio - self.meia)
        pygame.draw.rect(tela, (120, 230, 140), (c.x - 26, y0, 18, y1 - y0))
        pygame.draw.rect(tela, TINTA, (c.x - 26, y0, 18, y1 - y0), 2)
        for y in (y0, y1):
            for x in range(c.x, c.right, 20):
                pygame.draw.line(tela, (60, 170, 90), (x, y), (x + 10, y), 3)
        seta_y = (y0 + y1) / 2
        pygame.draw.polygon(tela, TINTA, [(c.right + 14, seta_y), (c.right + 44, seta_y - 18),
                                          (c.right + 44, seta_y + 18)])
        pygame.draw.polygon(tela, (120, 230, 140), [(c.right + 20, seta_y), (c.right + 40, seta_y - 12),
                                                    (c.right + 40, seta_y + 12)])
        ui.desenhar_texto(tela, t("LINHA"), (c.right + 52, seta_y), 12, TINTA, "midleft", sombra=False)
        # Contorno do copo
        pygame.draw.rect(tela, TINTA, c.inflate(10, 6), 6, border_bottom_left_radius=22,
                         border_bottom_right_radius=22)
        pygame.draw.line(tela, BRANCO, (c.x + 16, c.y + 20), (c.x + 16, c.bottom - 30), 5)
        # Caixa de leite (inclina para derramar)
        bico = (c.centerx + 16, c.y - 50)
        if self.enchendo:
            pygame.draw.rect(tela, BRANCO, (bico[0] - 5, bico[1], 10, c.bottom - h - bico[1]))
            corpo = [(bico[0], bico[1]), (bico[0] + 60, bico[1] - 70), (bico[0] + 130, bico[1] - 10),
                     (bico[0] + 70, bico[1] + 60)]
        else:
            corpo = [(bico[0] + 30, bico[1] - 120), (bico[0] + 110, bico[1] - 120),
                     (bico[0] + 110, bico[1] + 10), (bico[0] + 30, bico[1] + 10)]
        pygame.draw.polygon(tela, BRANCO, corpo)
        pygame.draw.polygon(tela, TINTA, corpo, 4)
        meio = (sum(p[0] for p in corpo) / 4, sum(p[1] for p in corpo) / 4)
        pygame.draw.circle(tela, (90, 150, 230), (int(meio[0]), int(meio[1])), 18)
        ui.desenhar_texto(tela, "L", meio, 12, BRANCO, "center", sombra=False)
        # Ovinho olhando
        self.jogador.desenhar(tela, (250, 520), 100)


MICROS = [Pegue, Desvie, Estoure, Pule, Limpe, Aperte, Pare, Ache, Sopre, Guie, Acorde, Conte, Encha]


# ============================================================
# O JOGO
# ============================================================

class MicroOvo(MiniJogo):

    ID = "micro_ovo"
    TITULO = "MICRO-OVO"
    TITULO_CURTO = "MICRO-OVO"
    DESCRICAO = "Microjogos de 4 segundos em sequência! Leia a ordem gigante e faça rápido."
    COR = (230, 90, 170)
    INSTRUCOES = [
        "Microjogos de 4 segundos, um atrás do outro!",
        "Leia a ORDEM gigante e faça rápido.",
        "Errou? Perde um ovo. São 4 ovos de vida.",
        "A cada 5 rodadas fica MAIS RÁPIDO!",
        "SETAS/WASD, ESPAÇO e MOUSE",
    ]
    OPCOES = ["NORMAL", "TURBO"]
    ROTULO_PONTOS = "RODADAS"
    CONTAGEM = False            # a tela "PREPARE-SE!" já faz esse papel

    MOEDAS_POR = 1              # 1 moeda por rodada vencida
    MOEDAS_MAX = 40
    MOEDAS_MIN = 1

    # --------------------------------------------------------
    # CENÁRIO
    # --------------------------------------------------------

    @classmethod
    def criar_fundo(cls, jogador):
        return _raios((255, 120, 190), (205, 70, 150))

    @classmethod
    def desenhar_icone(cls, sup, jogador):
        w, h = sup.get_size()
        jogador.desenhar(sup, (w // 2, h // 2 + 8), h * 0.42)
        ui.limao(sup, (w // 2 - int(w * 0.3), h // 2 - int(h * 0.12)), max(6, h // 12), 20)
        # Bombinha com pavio
        b = (w // 2 + int(w * 0.3), h // 2 + int(h * 0.18))
        r = max(6, h // 10)
        pygame.draw.circle(sup, TINTA, b, r + 2)
        pygame.draw.circle(sup, (60, 60, 80), b, r)
        pygame.draw.line(sup, (200, 160, 100), (b[0] + r // 2, b[1] - r), (b[0] + r, b[1] - r * 2), 3)
        ui.estrela(sup, (b[0] + r, b[1] - r * 2), r * 0.6, AMARELO)
        ui.desenhar_texto(sup, "!", (w // 2 + int(w * 0.18), h // 2 - int(h * 0.3)), max(10, h // 6),
                          AMARELO, "center")

    # --------------------------------------------------------
    # PARTIDA
    # --------------------------------------------------------

    def reiniciar(self):
        self.vidas = VIDAS
        self.rodada = 0
        self.nivel = NIVEL_INICIAL[self.opcao]
        self.fase = "entre"
        self.t_fase = 0.0
        self.dur_fase = TEMPO_PRIMEIRA
        self.ultimo = None
        self.micro = None
        self.saco = []
        self.anterior = None
        self.forcar = getattr(self, "forcar", [])   # (testes) sequência fixa
        self.cursor = [LARGURA / 2, 420.0]
        self.mouse = False
        self.seguradas = set()
        self.t_resolvido = 0.0
        self.tique = 99
        self.interagiu = False
        self.maior_vel = self.vel

    @property
    def vel(self):
        return _velocidade(self.nivel)

    def partida_valida(self):
        return self.interagiu

    def pausar(self):
        super().pausar()
        self.seguradas.clear()
        if self.micro is not None and self.micro.resultado is None:
            self.micro.solta(pygame.K_SPACE)
            self.micro.solta_clique()

    def eixo(self):
        s = self.seguradas
        x = (1 if any(k in s for k in DIR) else 0) - (1 if any(k in s for k in ESQ) else 0)
        y = (1 if any(k in s for k in BAIXO) else 0) - (1 if any(k in s for k in CIMA) else 0)
        return x, y

    def _sortear(self):
        if self.forcar:
            return self.forcar.pop(0)
        if not self.saco:
            self.saco = MICROS[:]
            random.shuffle(self.saco)
            if len(self.saco) > 1 and self.saco[-1] is self.anterior:
                self.saco[0], self.saco[-1] = self.saco[-1], self.saco[0]
        cls = self.saco.pop()
        self.anterior = cls
        return cls

    def _novo_micro(self):
        self.rodada += 1
        self.micro = self._sortear()(self, self.nivel)
        self.fase = "micro"
        self.t_fase = 0.0
        self.t_resolvido = 0.0
        self.tique = 99
        if not self.mouse:
            self.cursor = [LARGURA / 2, 420.0]
        self.som("selecionar")

    def _resolver(self, venceu, pos=None):
        """Chamado pelo microjogo quando ele acaba (acerto ou erro)."""
        pos = pos or (LARGURA // 2, 330)
        self.t_resolvido = 0.0
        if venceu:
            self.pontos += 1
            self.som("acerto")
            self.particulas.explodir(pos, CONFETE, 30, 380, 0.9, (3, 7))
            self.textos.adicionar("+1", (pos[0], pos[1] - 30), AMARELO, 22)
        else:
            self.vidas -= 1
            self.som("erro")
            self.tremer(0.35)
            self.particulas.explodir(pos, [(120, 110, 130), VERMELHO_ERRO, BRANCO], 16, 260, 0.6, (3, 6))

    def _fim_micro(self):
        self.ultimo = self.micro.resultado
        self.fase = "entre"
        self.t_fase = 0.0
        if self.vidas <= 0:
            self.dur_fase = TEMPO_GAME_OVER
            self.som("perder", 0.6)
        else:
            self.dur_fase = TEMPO_ENTRE
            if self.ultimo:
                self.particulas.explodir((LARGURA // 2, 300), CONFETE, 24, 420, 0.8, (3, 7))
            else:
                # Casquinhas do ovo de vida que rachou
                x = LARGURA // 2 - 90 * (VIDAS - 1) / 2 + 90 * self.vidas
                self.particulas.explodir((x, 560), [(110, 100, 120), BRANCO], 14, 240, 0.5, (3, 6))
        self.micro = None

    def _fim(self):
        p = self.pontos
        if p >= 25:
            titulo = t("LENDA DOS MICROS!")
        elif p >= 15:
            titulo = t("MANDOU BEM!")
        else:
            titulo = t("ACABARAM OS OVOS!")
        linhas = [t("RODADAS VENCIDAS: {n}", n=p),
                  t("RODADAS JOGADAS: {n}", n=self.rodada),
                  t("VELOCIDADE MÁXIMA: {v}", v=_fmt_vel(self.maior_vel))]
        self.terminar(venceu=p >= 15, valor=p, titulo=titulo, linhas=linhas)

    # --------------------------------------------------------
    # CONTROLES
    # --------------------------------------------------------

    def evento_jogo(self, e):
        if e.type == pygame.KEYDOWN:
            self.seguradas.add(e.key)
            if e.key in ESQ + DIR + CIMA + BAIXO:
                self.mouse = False
        elif e.type == pygame.KEYUP:
            self.seguradas.discard(e.key)
        elif e.type == pygame.MOUSEMOTION:
            self.cursor = [float(e.pos[0]), float(e.pos[1])]
            self.mouse = True
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.cursor = [float(e.pos[0]), float(e.pos[1])]
            self.mouse = True

        m = self.micro
        if self.fase != "micro" or m is None or m.resultado is not None:
            return
        if e.type == pygame.KEYDOWN:
            self.interagiu = True
            if m.CURSOR and e.key in ACAO:
                m.clique(tuple(self.cursor))
            else:
                m.tecla(e.key)
        elif e.type == pygame.KEYUP:
            m.solta(e.key)
        elif e.type == pygame.MOUSEMOTION:
            m.mover(e.pos, e.rel)
            if e.rel != (0, 0):
                self.interagiu = True
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.interagiu = True
            m.clique(e.pos)
        elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
            m.solta_clique()

    # --------------------------------------------------------
    # LÓGICA
    # --------------------------------------------------------

    def atualizar_jogo(self, dt):
        self.t_fase += dt

        if self.fase == "entre":
            if self.t_fase >= self.dur_fase:
                if self.vidas <= 0:
                    self._fim()
                elif self.rodada > 0 and self.rodada % RODADAS_POR_NIVEL == 0:
                    self.nivel += 1
                    self.maior_vel = max(self.maior_vel, self.vel)
                    self.fase = "rapido"
                    self.t_fase = 0.0
                    self.som("levelup")
                    self.tremer(0.15)
                else:
                    self._novo_micro()
            return

        if self.fase == "rapido":
            if self.t_fase >= TEMPO_RAPIDO:
                self._novo_micro()
            return

        m = self.micro
        # Cursor virtual pelas setas (microjogos de mouse)
        if m.CURSOR and m.resultado is None:
            ex, ey = self.eixo()
            if ex or ey:
                n = math.hypot(ex, ey)
                dx, dy = ex / n * 760 * dt, ey / n * 760 * dt
                antes = tuple(self.cursor)
                self.cursor[0] = _limitar(self.cursor[0] + dx, 10, LARGURA - 10)
                self.cursor[1] = _limitar(self.cursor[1] + dy, 10, ALTURA - 10)
                rel = (self.cursor[0] - antes[0], self.cursor[1] - antes[1])
                m.mover(tuple(self.cursor), rel)

        dm = dt * self.vel
        m.t += dm
        m.atualizar(dm)
        if m.resultado is None:
            resta = DURACAO - m.t
            if resta <= 3 and math.ceil(resta) != self.tique:
                self.tique = math.ceil(resta)
                if self.tique > 0:
                    self.som("tic", 0.7)
            if m.t >= DURACAO:
                m.decidir()
        else:
            self.t_resolvido += dm
            if self.t_resolvido >= ESPERA:
                self._fim_micro()

    # --------------------------------------------------------
    # DESENHO
    # --------------------------------------------------------

    def desenhar_jogo(self, tela):
        if self.fase == "micro" and self.micro is not None:
            self._desenhar_micro(tela)
        elif self.fase == "rapido":
            self._desenhar_rapido(tela)
        else:
            self._desenhar_entre(tela)
        self.particulas.desenhar(tela)
        self.textos.desenhar(tela)

    def _desenhar_micro(self, tela):
        m = self.micro
        m.desenhar(tela)

        if m.CURSOR and self.estado == "jogando":
            m.desenhar_cursor(tela, self.cursor)

        self._desenhar_pavio(tela)

        if m.resultado is not None:
            # Carimbo do resultado
            tam = 88 if self.t_resolvido < 0.06 else 72
            msg, cor = ("BOA!", VERDE_OK) if m.resultado else ("OPS!", VERMELHO_ERRO)
            img = _palavra(msg, tam, cor)
            tela.blit(img, img.get_rect(center=(LARGURA // 2, 130)))
        elif m.t < INTRO:
            # A ORDEM gigante (entra "pulando")
            ui.veu(tela, 80)
            tam = 104 if m.t < 0.06 else 92 if m.t < 0.12 else 84
            img = _palavra(m.PALAVRA, tam, m.COR)
            tela.blit(img, img.get_rect(center=(LARGURA // 2, 320)))
            if m.DICA:
                sup = ui.texto(t(m.DICA), 16, BRANCO)
                caixa = sup.get_rect(center=(LARGURA // 2, 420)).inflate(36, 22)
                ui.painel(tela, caixa, (30, 24, 50), m.COR, 14, 3, sombra=False)
                tela.blit(sup, sup.get_rect(center=caixa.center))
        else:
            img = _palavra(m.PALAVRA, 24, m.COR)
            tela.blit(img, img.get_rect(midtop=(LARGURA // 2, 16)))

    def _desenhar_pavio(self, tela):
        """Bomba com pavio queimando (o tempo do microjogo)."""
        m = self.micro
        frac = _limitar(1 - m.t / DURACAO, 0, 1)
        y = ALTURA - 26
        bomba = (40, y)
        x_fim = 70 + (LARGURA - 120) * frac
        if frac > 0:
            pygame.draw.line(tela, TINTA, (62, y), (x_fim, y), 9)
            pygame.draw.line(tela, (225, 190, 130), (62, y), (x_fim, y), 5)
            for x in range(70, int(x_fim), 18):
                pygame.draw.line(tela, (170, 130, 80), (x, y - 2), (x + 6, y + 2), 2)
            if m.resultado is None:
                faisca = 10 + 4 * math.sin(self.tempo * 40)
                ui.estrela(tela, (x_fim, y), faisca, (255, 150, 40), self.tempo * 12)
                ui.estrela(tela, (x_fim, y), faisca * 0.5, (255, 250, 200), -self.tempo * 9)
        resta = DURACAO - m.t
        urgente = resta <= 1 and m.resultado is None
        raio = 22 + (3 if urgente and int(self.tempo * 10) % 2 == 0 else 0)
        pygame.draw.circle(tela, TINTA, bomba, raio + 3)
        pygame.draw.circle(tela, (200, 50, 60) if urgente else (60, 60, 82), bomba, raio)
        pygame.draw.circle(tela, (150, 150, 180), (bomba[0] - 7, bomba[1] - 8), 5)
        pygame.draw.rect(tela, TINTA, (bomba[0] + 12, bomba[1] - 8, 12, 14), border_radius=3)
        if resta <= 3 and m.resultado is None:
            ui.desenhar_texto(tela, str(max(1, math.ceil(resta))), (bomba[0], bomba[1] + 1), 14, BRANCO, "center")

    def _desenhar_vidas(self, tela, centro_y, escala=1.0, espaco=90):
        x0 = LARGURA // 2 - espaco * (VIDAS - 1) / 2
        acabou_de_perder = self.fase == "entre" and self.ultimo is False and self.t_fase < 0.45
        for i in range(VIDAS):
            x = x0 + i * espaco
            viva = i < self.vidas
            dx = 0
            if acabou_de_perder and i == self.vidas:
                dx = math.sin(self.t_fase * 60) * 6
            _ovinho_vida(tela, (int(x + dx), int(centro_y)), viva, escala)

    def _desenhar_entre(self, tela):
        k = self.t_fase
        if self.ultimo is None:
            estilo = "neutro"
        else:
            estilo = "ganhou" if self.ultimo else "perdeu"
        tela.blit(_fundo_entre(estilo), (0, 0))

        # Rodada
        if self.vidas <= 0:
            titulo, cor = "FIM!", VERMELHO_ERRO
        else:
            titulo, cor = t("RODADA {n}", n=self.rodada + 1), AMARELO
        img = _palavra(titulo, 36, cor)
        tela.blit(img, img.get_rect(center=(LARGURA // 2, 100)))

        # O ovo do jogador feliz / triste / esperando
        cx, cy = LARGURA // 2, 330
        if self.ultimo is True:
            dy = -abs(math.sin(k * 9)) * 36
            _desenhar_ovo(tela, self.jogador, (cx, cy + dy), 170)
            for i in range(5):
                a = self.tempo * 3 + i * math.tau / 5
                ui.estrela(tela, (cx + math.cos(a) * 140, cy + dy + math.sin(a) * 110), 12, AMARELO, a)
            msg, cor_msg = "BOA!", VERDE_OK
        elif self.ultimo is False:
            ang = math.sin(k * 7) * 10
            _desenhar_ovo(tela, self.jogador, (cx, cy), 170, ang)
            for s in (-1, 1):
                ty = cy - 10 + (k * 160 + (s + 1) * 20) % 80
                tx = cx + s * 34
                pygame.draw.circle(tela, (120, 190, 255), (int(tx), int(ty)), 7)
                pygame.draw.polygon(tela, (120, 190, 255), [(tx - 6, ty - 2), (tx + 6, ty - 2), (tx, ty - 14)])
            msg, cor_msg = ("ACABOU..." if self.vidas <= 0 else "OPS!"), VERMELHO_ERRO
        else:
            _desenhar_ovo(tela, self.jogador, (cx, cy + math.sin(k * 5) * 6), 170)
            msg, cor_msg = "PREPARE-SE!", BRANCO
        img = _palavra(msg, 32, cor_msg)
        tela.blit(img, img.get_rect(center=(cx, 470)))

        # Vidas
        self._desenhar_vidas(tela, 560)

        ui.desenhar_texto(tela, t("PONTOS: {n}    VELOCIDADE {v}", n=self.pontos, v=_fmt_vel(self.vel)),
                          (LARGURA // 2, 640), 14, BRANCO, "center")

    def _desenhar_rapido(self, tela):
        k = self.t_fase
        tela.blit(_fundo_entre("rapido"), (0, 0))
        # Linhas de velocidade
        for i in range(16):
            y = (i * 47 + 20) % ALTURA
            x = (i * 211 - k * 2200) % (LARGURA + 400) - 200
            pygame.draw.line(tela, (255, 230, 180), (x, y), (x + 180, y), 5)
        tam = 60 if int(k * 8) % 2 == 0 else 56
        img = _palavra("MAIS RÁPIDO!", tam, AMARELO)
        tela.blit(img, img.get_rect(center=(LARGURA // 2, 150)))
        cx = LARGURA // 2 + math.sin(k * 3) * 60
        _desenhar_ovo(tela, self.jogador, (cx, 360 - abs(math.sin(k * 16)) * 20), 160, -12)
        for i in range(3):
            x = cx - 120 - i * 40
            pygame.draw.line(tela, BRANCO, (x, 330 + i * 30), (x - 60, 330 + i * 30), 6)
        img = _palavra(t("VELOCIDADE {v}", v=_fmt_vel(self.vel)), 24, BRANCO)
        tela.blit(img, img.get_rect(center=(LARGURA // 2, 520)))
        self._desenhar_vidas(tela, 610, 0.8, 70)

    def desenhar_hud(self, tela):
        if self.fase != "micro" or self.estado == "fim":
            return
        caixa = pygame.Rect(12, 12, 250, 48)
        ui.painel(tela, caixa, (26, 20, 40), BRANCO, 12, 3, sombra=False)
        ui.desenhar_texto(tela, t("RODADA {n}", n=self.rodada), (caixa.x + 14, caixa.centery), 12, AMARELO, "midleft")
        for i in range(VIDAS):
            _ovinho_vida(tela, (caixa.right - 90 + i * 24, caixa.centery), i < self.vidas, 0.5)
