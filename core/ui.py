import math
import random
import re

import pygame

from settings import *
from core import assets

# ============================================================
# TEXTO (COM CACHE)
# ============================================================
# Renderizar texto é caro. Guardamos cada texto já desenhado
# para não precisar renderizar de novo a cada frame.

_cache_texto = {}
_LIMITE_CACHE = 600

# A fonte PressStart2P desenha as MAIÚSCULAS acentuadas com cara
# de minúscula (fica "MúSICA"). Então tiramos o acento só delas.
_SEM_ACENTO = str.maketrans("ÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇÑ",
                            "AAAAAEEEEIIIIOOOOOUUUUCN")

# A fonte também tem ligaduras "fi", "fl", "ff" que espremem as
# duas letras numa célula só ("finca" vira "fnca"). Um ZWNJ
# (caractere invisível) entre elas desfaz a ligadura.
_LIGADURA = re.compile(r"f(?=[a-z])")


def preparar(msg):
    """Ajusta o texto para a fonte do jogo (acentos e ligaduras)."""
    return _LIGADURA.sub("f‌", msg.translate(_SEM_ACENTO))


def texto(msg, tamanho=20, cor=BRANCO, sombra=True):
    """Devolve uma Surface com o texto (com sombra opcional)."""
    chave = (msg, tamanho, cor, sombra)
    sup = _cache_texto.get(chave)

    if sup is not None:
        return sup

    if len(_cache_texto) > _LIMITE_CACHE:
        _cache_texto.clear()

    f = assets.fonte(tamanho)
    msg = preparar(msg)
    frente = f.render(msg, False, cor)

    if sombra:
        desloc = max(2, tamanho // 8)
        sup = pygame.Surface(
            (frente.get_width() + desloc, frente.get_height() + desloc),
            pygame.SRCALPHA
        )
        atras = f.render(msg, False, (0, 0, 0))
        atras.set_alpha(150)
        sup.blit(atras, (desloc, desloc))
        sup.blit(frente, (0, 0))
    else:
        sup = frente

    _cache_texto[chave] = sup
    return sup


def desenhar_texto(tela, msg, pos, tamanho=20, cor=BRANCO,
                   ancora="topleft", sombra=True):
    """Desenha texto. `ancora` pode ser center, midtop, topright..."""
    sup = texto(msg, tamanho, cor, sombra)
    rect = sup.get_rect(**{ancora: pos})
    tela.blit(sup, rect)
    return rect


def centralizado(tela, msg, y, tamanho=20, cor=BRANCO, sombra=True):
    return desenhar_texto(tela, msg, (LARGURA // 2, y), tamanho, cor,
                          "midtop", sombra)


def tamanho_que_cabe(msg, largura_max, tamanhos=(30, 24, 20, 16, 12)):
    """Maior tamanho de fonte (da lista) em que o texto cabe na largura."""
    msg = preparar(msg)
    for tam in tamanhos:
        if assets.fonte(tam).size(msg)[0] <= largura_max:
            return tam
    return tamanhos[-1]


def quebrar_linhas(msg, tamanho, largura_max):
    """Quebra um texto em várias linhas que caibam na largura."""
    f = assets.fonte(tamanho)
    linhas = []

    for paragrafo in msg.split("\n"):
        atual = ""

        for palavra in paragrafo.split(" "):
            teste = palavra if not atual else atual + " " + palavra

            if f.size(preparar(teste))[0] <= largura_max:
                atual = teste
            else:
                if atual:
                    linhas.append(atual)
                atual = palavra

        linhas.append(atual)

    return linhas


# ============================================================
# FORMAS
# ============================================================

_sombras = {}


def painel(tela, rect, cor=UI_FUNDO, borda=UI_BORDA, raio=16,
           espessura=4, sombra=True):
    """Painel arredondado com sombra."""
    rect = pygame.Rect(rect)

    if sombra:
        chave = (rect.w, rect.h, raio)
        s = _sombras.get(chave)
        if s is None:
            if len(_sombras) > 64:
                _sombras.clear()
            s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            pygame.draw.rect(s, (0, 0, 0, 100), s.get_rect(), border_radius=raio)
            _sombras[chave] = s
        tela.blit(s, (rect.x + 6, rect.y + 6))

    pygame.draw.rect(tela, cor, rect, border_radius=raio)

    if espessura:
        pygame.draw.rect(tela, borda, rect, espessura, border_radius=raio)


def gradiente(largura, altura, cor_topo, cor_base):
    """Cria uma Surface com gradiente vertical."""
    sup = pygame.Surface((largura, altura))

    for y in range(altura):
        t = y / max(1, altura - 1)
        cor = misturar(cor_topo, cor_base, t)
        pygame.draw.line(sup, cor, (0, y), (largura, y))

    return sup


def misturar(c1, c2, t):
    """Mistura duas cores (t=0 -> c1, t=1 -> c2)."""
    t = max(0.0, min(1.0, t))
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )


def clarear(cor, qtd=40):
    return tuple(min(255, c + qtd) for c in cor[:3])


def escurecer(cor, qtd=40):
    return tuple(max(0, c - qtd) for c in cor[:3])


_veu_cache = {}


def veu(tela, alpha=160, cor=(0, 0, 0)):
    """Escurece a tela inteira (Surface reaproveitada)."""
    chave = (tela.get_size(), cor)
    s = _veu_cache.get(chave)

    if s is None:
        s = pygame.Surface(tela.get_size())
        s.fill(cor)
        _veu_cache[chave] = s

    s.set_alpha(alpha)
    tela.blit(s, (0, 0))


def coracao(tela, centro, tamanho, cor=(235, 60, 90)):
    """Desenha um coraçãozinho."""
    x, y = centro
    r = tamanho // 4
    pygame.draw.circle(tela, cor, (x - r, y - r // 2), r + 1)
    pygame.draw.circle(tela, cor, (x + r, y - r // 2), r + 1)
    pygame.draw.polygon(tela, cor, [
        (x - 2 * r - 1, y - r // 2 + 1),
        (x + 2 * r + 1, y - r // 2 + 1),
        (x, y + int(r * 1.8)),
    ])


def estrela(tela, centro, raio, cor=AMARELO, angulo=0.0):
    """Desenha uma estrela de 5 pontas."""
    pontos = []

    for i in range(10):
        r = raio if i % 2 == 0 else raio * 0.45
        a = angulo + i * math.pi / 5 - math.pi / 2
        pontos.append((centro[0] + math.cos(a) * r, centro[1] + math.sin(a) * r))

    pygame.draw.polygon(tela, cor, pontos)


def limao(tela, centro, raio, angulo=0.0):
    """Desenha um limão (usado em vários jogos)."""
    sup = limao_sup(raio)

    if angulo:
        sup = pygame.transform.rotate(sup, angulo)

    tela.blit(sup, sup.get_rect(center=centro))


_limao_cache = {}


def limao_sup(raio):
    s = _limao_cache.get(raio)

    if s is not None:
        return s

    w = int(raio * 2.6)
    h = int(raio * 2.3)
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    cx, cy = w // 2, h // 2 + raio // 6

    corpo = pygame.Rect(0, 0, int(raio * 2.2), int(raio * 1.7))
    corpo.center = (cx, cy)

    # Pontinhas do limão
    pygame.draw.circle(s, (230, 200, 20), (corpo.left + 2, cy), max(2, raio // 4))
    pygame.draw.circle(s, (230, 200, 20), (corpo.right - 2, cy), max(2, raio // 4))

    pygame.draw.ellipse(s, (250, 222, 40), corpo)
    pygame.draw.ellipse(s, (190, 160, 10), corpo, max(1, raio // 7))

    # Brilho
    brilho = pygame.Rect(0, 0, int(raio / 1.4), int(raio / 2.6))
    brilho.center = (cx - raio // 3, cy - raio // 3)
    pygame.draw.ellipse(s, (255, 248, 180), brilho)

    # Folha
    folha = [
        (cx + 2, corpo.top + 2),
        (cx + raio * 0.5, corpo.top - raio * 0.5),
        (cx + raio * 0.95, corpo.top - raio * 0.2),
        (cx + raio * 0.35, corpo.top + 3),
    ]
    pygame.draw.polygon(s, (70, 170, 60), folha)
    pygame.draw.line(s, (40, 110, 40), folha[0], folha[2], 1)

    _limao_cache[raio] = s
    return s


_moeda_cache = {}


def moeda(tela, centro, raio, giro=1.0):
    """
    Moeda do jogo (a OVOEDA): dourada, com um ovinho em relevo.
    `giro` (0..1) achata a moeda na horizontal para animar girando.
    """
    s = _moeda_cache.get(raio)
    if s is None:
        d = raio * 2 + 2
        s = pygame.Surface((d, d), pygame.SRCALPHA)
        c = (raio + 1, raio + 1)
        pygame.draw.circle(s, (170, 110, 10), c, raio)
        pygame.draw.circle(s, (255, 196, 40), c, max(1, raio - max(1, raio // 7)))
        pygame.draw.circle(s, (235, 165, 20), c, max(1, int(raio * 0.72)),
                           max(1, raio // 8))
        ovo = pygame.Rect(0, 0, max(2, int(raio * 0.7)), max(3, int(raio * 0.9)))
        ovo.center = (c[0], c[1] + raio // 12)
        pygame.draw.ellipse(s, (255, 226, 120), ovo)
        pygame.draw.ellipse(s, (200, 135, 15), ovo, max(1, raio // 10))
        pygame.draw.circle(s, (255, 250, 210), (c[0] - raio // 2, c[1] - raio // 2),
                           max(1, raio // 5))
        _moeda_cache[raio] = s

    if giro < 0.99:
        w = max(2, int(s.get_width() * abs(giro)))
        s = pygame.transform.smoothscale(s, (w, s.get_height()))
    tela.blit(s, s.get_rect(center=(int(centro[0]), int(centro[1]))))


def desenhar_moedas(tela, qtd, pos, ancora="topleft", tamanho=16):
    """Pílula com o ícone da moeda e a quantidade."""
    sup = texto(f"{qtd}", tamanho, AMARELO)
    raio = tamanho - 2
    r = pygame.Rect(0, 0, sup.get_width() + raio * 2 + 34, max(40, tamanho + 24))
    setattr(r, ancora, pos)
    painel(tela, r, (50, 38, 14), AMARELO, r.h // 2, 3, sombra=False)
    moeda(tela, (r.x + 14 + raio, r.centery), raio)
    tela.blit(sup, sup.get_rect(midleft=(r.x + 22 + raio * 2, r.centery + 1)))
    return r


# ============================================================
# BOTÃO
# ============================================================

class Botao:
    """
    Botão clicável com efeito de hover.

    Use `evento(e)` dentro do loop de eventos: ele devolve True
    quando o botão foi clicado.
    """

    def __init__(self, rect, rotulo, tamanho=18, cor=UI_BOTAO,
                 cor_hover=UI_BOTAO_HOVER, cor_texto=BRANCO):
        self.rect = pygame.Rect(rect)
        self.rotulo = rotulo
        self.tamanho = tamanho
        self.cor = cor
        self.cor_hover = cor_hover
        self.cor_texto = cor_texto
        self.selecionado = False
        self._anim = 0.0

    @property
    def hover(self):
        return self.rect.collidepoint(pygame.mouse.get_pos())

    def evento(self, e):
        return (
            e.type == pygame.MOUSEBUTTONDOWN
            and e.button == 1
            and self.rect.collidepoint(e.pos)
        )

    def atualizar(self, dt):
        alvo = 1.0 if (self.hover or self.selecionado) else 0.0
        self._anim += (alvo - self._anim) * min(1.0, dt * 14)

    def desenhar(self, tela):
        ativo = self._anim
        sobe = int(3 * ativo)
        r = self.rect.move(0, -sobe)

        # Sombra
        pygame.draw.rect(tela, (0, 0, 0), self.rect.move(0, 5), border_radius=12)

        cor = misturar(self.cor, self.cor_hover, ativo)
        pygame.draw.rect(tela, cor, r, border_radius=12)

        # Faixa de brilho em cima
        brilho = pygame.Rect(r.x + 6, r.y + 5, r.w - 12, max(4, r.h // 5))
        pygame.draw.rect(tela, clarear(cor, 28), brilho, border_radius=8)

        borda = misturar(UI_BORDA, UI_DESTAQUE, ativo)
        pygame.draw.rect(tela, borda, r, 3, border_radius=12)

        desenhar_texto(tela, self.rotulo, r.center, self.tamanho,
                       self.cor_texto, "center")


class Menu:
    """
    Lista vertical de botões que funciona com mouse E teclado
    (setas + ENTER).
    """

    def __init__(self, rotulos, centro_x, y, largura=360, altura=58,
                 espaco=16, tamanho=18):
        self.botoes = []

        for i, rot in enumerate(rotulos):
            rect = pygame.Rect(0, 0, largura, altura)
            rect.midtop = (centro_x, y + i * (altura + espaco))
            self.botoes.append(Botao(rect, rot, tamanho))

        self.indice = 0
        self._ultimo_mouse = None

    def evento(self, e):
        """Devolve o índice do botão escolhido (ou None)."""
        if e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_UP, pygame.K_w):
                self.indice = (self.indice - 1) % len(self.botoes)
            elif e.key in (pygame.K_DOWN, pygame.K_s):
                self.indice = (self.indice + 1) % len(self.botoes)
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                return self.indice

        for i, b in enumerate(self.botoes):
            if b.evento(e):
                self.indice = i
                return i

        return None

    def atualizar(self, dt):
        pos = pygame.mouse.get_pos()

        # O mouse só muda a seleção quando realmente se mexe
        if pos != self._ultimo_mouse:
            self._ultimo_mouse = pos
            for i, b in enumerate(self.botoes):
                if b.rect.collidepoint(pos):
                    self.indice = i

        for i, b in enumerate(self.botoes):
            b.selecionado = (i == self.indice)
            b.atualizar(dt)

    def desenhar(self, tela):
        for b in self.botoes:
            b.desenhar(tela)


# ============================================================
# PARTÍCULAS
# ============================================================

class Particulas:
    """Sistema simples de partículas (confete, gotas, poeira...)."""

    def __init__(self):
        self.lista = []

    def explodir(self, pos, cores, qtd=16, vel=220, vida=0.8,
                 tamanho=(3, 7), gravidade=500):
        for _ in range(qtd):
            ang = random.uniform(0, math.tau)
            v = random.uniform(vel * 0.35, vel)
            self.lista.append([
                float(pos[0]), float(pos[1]),
                math.cos(ang) * v, math.sin(ang) * v - vel * 0.3,
                random.uniform(vida * 0.6, vida), vida,
                random.choice(cores),
                random.randint(*tamanho),
                gravidade,
            ])

    def atualizar(self, dt):
        vivas = []

        for p in self.lista:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[3] += p[8] * dt
            p[4] -= dt

            if p[4] > 0:
                vivas.append(p)

        self.lista = vivas

    def desenhar(self, tela, desloc=(0, 0)):
        for p in self.lista:
            t = p[4] / p[5]
            r = max(1, int(p[7] * t))
            pygame.draw.circle(tela, p[6],
                               (int(p[0] + desloc[0]), int(p[1] + desloc[1])), r)

    def limpar(self):
        self.lista.clear()


class TextoFlutuante:
    """Textinhos que sobem e somem (+1, +5, etc)."""

    def __init__(self):
        self.lista = []

    def adicionar(self, msg, pos, cor=AMARELO, tamanho=16):
        self.lista.append([msg, float(pos[0]), float(pos[1]), 1.0, cor, tamanho])

    def atualizar(self, dt):
        for t in self.lista:
            t[2] -= 60 * dt
            t[3] -= dt * 1.2
        self.lista = [t for t in self.lista if t[3] > 0]

    def desenhar(self, tela, desloc=(0, 0)):
        for msg, x, y, vida, cor, tam in self.lista:
            sup = texto(msg, tam, cor)
            if vida < 0.5:
                sup = sup.copy()
                sup.set_alpha(int(255 * vida * 2))
            tela.blit(sup, sup.get_rect(center=(x + desloc[0], y + desloc[1])))
