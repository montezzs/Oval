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


def texto(msg, tamanho=20, cor=BRANCO, sombra=True, contorno=False):
    """
    Devolve uma Surface com o texto (com sombra opcional).
    `contorno` desenha uma borda escura em volta das letras: deixa
    títulos e números legíveis em cima de qualquer fundo.
    """
    chave = (msg, tamanho, cor, sombra, contorno)
    sup = _cache_texto.get(chave)

    if sup is not None:
        return sup

    if len(_cache_texto) > _LIMITE_CACHE:
        _cache_texto.clear()

    f = assets.fonte(tamanho)
    msg = preparar(msg)
    frente = f.render(msg, False, cor)

    if contorno:
        b = 2 if tamanho >= 24 else 1
        desloc = max(2, tamanho // 8) if sombra else 0
        sup = pygame.Surface(
            (frente.get_width() + b * 2 + desloc, frente.get_height() + b * 2 + desloc),
            pygame.SRCALPHA
        )
        if sombra:
            atras = f.render(msg, False, (0, 0, 0))
            atras.set_alpha(120)
            sup.blit(atras, (b + desloc, b + desloc))
        borda = f.render(msg, False, UI_CONTORNO)
        for dx in (-b, 0, b):
            for dy in (-b, 0, b):
                if dx or dy:
                    sup.blit(borda, (b + dx, b + dy))
        sup.blit(frente, (b, b))
    elif sombra:
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
                   ancora="topleft", sombra=True, contorno=False):
    """Desenha texto. `ancora` pode ser center, midtop, topright..."""
    sup = texto(msg, tamanho, cor, sombra, contorno)
    rect = sup.get_rect(**{ancora: pos})
    tela.blit(sup, rect)
    return rect


def centralizado(tela, msg, y, tamanho=20, cor=BRANCO, sombra=True, contorno=False):
    return desenhar_texto(tela, msg, (LARGURA // 2, y), tamanho, cor,
                          "midtop", sombra, contorno)


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


def sombra_suave(tela, rect, raio=12, desloc=6, alpha=90):
    """
    Sombra arredondada com a borda "esfumada" (3 camadas de alpha).
    Fica mais macia que um retângulo preto chapado.
    """
    rect = pygame.Rect(rect)
    pad = 4
    chave = (rect.w, rect.h, raio, alpha)
    s = _sombras.get(chave)

    if s is None:
        if len(_sombras) > 160:
            _sombras.clear()
        s = pygame.Surface((rect.w + pad * 2, rect.h + pad * 2), pygame.SRCALPHA)
        caixa = s.get_rect()
        pygame.draw.rect(s, (0, 0, 0, alpha // 3), caixa, border_radius=raio + pad)
        pygame.draw.rect(s, (0, 0, 0, alpha * 2 // 3), caixa.inflate(-pad, -pad),
                         border_radius=raio + pad // 2)
        pygame.draw.rect(s, (0, 0, 0, alpha), caixa.inflate(-pad * 2, -pad * 2),
                         border_radius=raio)
        _sombras[chave] = s

    tela.blit(s, (rect.x - pad, rect.y - pad + desloc))


def painel(tela, rect, cor=UI_FUNDO, borda=UI_BORDA, raio=16,
           espessura=4, sombra=True, brilho=True):
    """Painel arredondado com sombra suave e um brilho fino em cima."""
    rect = pygame.Rect(rect)

    if sombra:
        sombra_suave(tela, rect, raio, 6, 100)

    pygame.draw.rect(tela, cor, rect, border_radius=raio)

    # Brilho interno na parte de cima (dá volume, estilo "almofada")
    if brilho and rect.h >= 30 and rect.w >= 40:
        interno = rect.inflate(-espessura * 2 - 2, -espessura * 2 - 2)
        antes = tela.get_clip()
        topo = pygame.Rect(rect.x, rect.y, rect.w, min(rect.h // 2, raio + 6))
        tela.set_clip(topo.clip(antes))
        pygame.draw.rect(tela, clarear(cor, 22), interno, 2,
                         border_radius=max(2, raio - espessura))
        tela.set_clip(antes)

    if espessura:
        pygame.draw.rect(tela, borda, rect, espessura, border_radius=raio)


def botao_base(tela, rect, cor=UI_BOTAO, cor_hover=None, hover=False,
               borda=None, raio=14, destaque=False):
    """
    Base para botões desenhados à mão (com ícone): sombra suave,
    "degrau" embaixo, brilho e borda. Sobe no hover e afunda ao
    apertar. Devolve o Rect onde desenhar o conteúdo.
    """
    rect = pygame.Rect(rect)
    if cor_hover is None:
        cor_hover = clarear(cor, 30)

    apertado = hover and pygame.mouse.get_pressed()[0]
    if apertado:
        r = rect.move(0, 2)
    elif hover:
        r = rect.move(0, -2)
    else:
        r = rect

    sombra_suave(tela, rect, raio, 5, 80)

    c = cor_hover if (hover or destaque) else cor
    if apertado:
        c = escurecer(c, 20)

    pygame.draw.rect(tela, escurecer(c, 45), r.move(0, 3), border_radius=raio)
    pygame.draw.rect(tela, c, r, border_radius=raio)
    faixa = pygame.Rect(r.x + 6, r.y + 4, r.w - 12, max(3, r.h // 6))
    pygame.draw.rect(tela, clarear(c, 24), faixa, border_radius=max(2, raio // 2))

    if borda is None:
        borda = UI_DESTAQUE if hover else UI_BORDA
    pygame.draw.rect(tela, borda, r, 3, border_radius=raio)
    return r


# ============================================================
# EASING (animações mais "macias")
# ============================================================

def suavizar(t):
    """Smoothstep: começa e termina devagar (0..1 -> 0..1)."""
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def sair_rapido(t):
    """Ease-out cúbico: rápido no começo, freia no fim."""
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def quicar(t, forca=1.70158):
    """Ease-out "back": passa um pouquinho do alvo e volta (efeito pop)."""
    t = max(0.0, min(1.0, t))
    t -= 1
    return 1 + (forca + 1) * t ** 3 + forca * t ** 2


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


def check(tela, centro, tamanho=10, cor=(140, 255, 150)):
    """Sinal de "feito" desenhado (a fonte pixelada não tem o ✓)."""
    x, y = centro
    t = tamanho / 2
    pontos = [(x - t, y), (x - t * 0.3, y + t * 0.7), (x + t, y - t * 0.8)]
    pygame.draw.lines(tela, (20, 40, 20), False, [(px + 1, py + 1) for px, py in pontos], 4)
    pygame.draw.lines(tela, cor, False, pontos, 3)


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


# Último valor mostrado em cada pílula de moedas (para o "pop")
_moedas_hud = {}
TEMPO_POP_MOEDAS = 280          # ms


def desenhar_moedas(tela, qtd, pos, ancora="topleft", tamanho=16):
    """
    Pílula com o ícone da moeda e a quantidade. Quando o valor
    sobe, a pílula dá um "pop" (cresce, brilha e solta um brilho).
    """
    agora = pygame.time.get_ticks()
    chave = (tuple(pos), ancora)
    antes = _moedas_hud.get(chave)
    if antes is None:
        antes = (qtd, -TEMPO_POP_MOEDAS)
    elif qtd > antes[0]:
        antes = (qtd, agora)
    else:
        antes = (qtd, antes[1])
    _moedas_hud[chave] = antes
    pop = max(0.0, 1.0 - (agora - antes[1]) / TEMPO_POP_MOEDAS)

    cor = misturar(AMARELO, BRANCO, pop * 0.7)
    sup = texto(f"{qtd}", tamanho, cor, True, True)
    raio = tamanho - 2
    r = pygame.Rect(0, 0, sup.get_width() + raio * 2 + 34, max(40, tamanho + 24))
    setattr(r, ancora, pos)

    cresce = int(6 * pop)
    pilula = r.inflate(cresce * 2, cresce)
    sombra_suave(tela, pilula, pilula.h // 2, 4, 70)
    painel(tela, pilula, UI_MOEDA_FUNDO, misturar(AMARELO, BRANCO, pop * 0.6),
           pilula.h // 2, 3, sombra=False)
    centro_moeda = (r.x + 14 + raio, r.centery)
    moeda(tela, centro_moeda, raio + int(3 * pop))
    tela.blit(sup, sup.get_rect(midleft=(r.x + 22 + raio * 2, r.centery + 1)))

    if pop > 0:
        estrela(tela, (centro_moeda[0] + raio, centro_moeda[1] - raio), 3 + 5 * pop,
                (255, 252, 220), pop * 2)
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
        self._aperto = 0.0          # 1 = mouse segurando o botão
        self._clique = 0.0          # "amassadinha" logo depois do clique

    @property
    def hover(self):
        return self.rect.collidepoint(pygame.mouse.get_pos())

    def evento(self, e):
        clicou = (
            e.type == pygame.MOUSEBUTTONDOWN
            and e.button == 1
            and self.rect.collidepoint(e.pos)
        )
        if clicou:
            self._clique = 1.0
        return clicou

    def atualizar(self, dt):
        alvo = 1.0 if (self.hover or self.selecionado) else 0.0
        self._anim += (alvo - self._anim) * min(1.0, dt * 14)

        apertado = 1.0 if (self.hover and pygame.mouse.get_pressed()[0]) else 0.0
        self._aperto += (apertado - self._aperto) * min(1.0, dt * 22)
        self._clique = max(0.0, self._clique - dt * 5)

    def desenhar(self, tela):
        ativo = self._anim
        aperto = max(self._aperto, self._clique)

        # Hover: sobe e cresce um pouquinho. Apertado: afunda e encolhe.
        sobe = int(3 * ativo - 4 * aperto)
        escala = 0.04 * ativo - 0.05 * aperto
        r = self.rect.inflate(int(self.rect.w * escala), int(self.rect.h * escala))
        r = r.move(0, -sobe)

        # Sombra suave (fica mais curta quando o botão afunda)
        sombra_suave(tela, self.rect, 12, int(7 - 3 * aperto), 95)

        cor = misturar(self.cor, self.cor_hover, ativo)
        if aperto > 0.01:
            cor = escurecer(cor, int(22 * aperto))

        # "Degrau" embaixo: dá a cara de botão fofinho de apertar
        pygame.draw.rect(tela, escurecer(cor, 50), r.move(0, 4), border_radius=12)
        pygame.draw.rect(tela, cor, r, border_radius=12)

        # Faixa de brilho em cima
        brilho = pygame.Rect(r.x + 6, r.y + 5, r.w - 12, max(4, r.h // 5))
        pygame.draw.rect(tela, clarear(cor, 28), brilho, border_radius=8)

        borda = misturar(UI_BORDA, UI_DESTAQUE, ativo)
        pygame.draw.rect(tela, borda, r, 3, border_radius=12)

        desenhar_texto(tela, self.rotulo, r.center, self.tamanho,
                       self.cor_texto, "center", True, True)


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
            # Sobe rápido e vai freando (ease-out)
            t[2] -= (25 + 60 * t[3]) * dt
            t[3] -= dt * 1.2
        self.lista = [t for t in self.lista if t[3] > 0]

    def desenhar(self, tela, desloc=(0, 0)):
        for msg, x, y, vida, cor, tam in self.lista:
            # "Pop" ao nascer: começa maior e encolhe rapidinho
            cresce = int(round(6 * max(0.0, 1.0 - (1.0 - vida) / 0.18)))
            sup = texto(msg, tam + cresce, cor, True, True)
            if vida < 0.5:
                sup = sup.copy()
                sup.set_alpha(int(255 * vida * 2))
            tela.blit(sup, sup.get_rect(center=(x + desloc[0], y + desloc[1])))


# ============================================================
# TOASTS (avisos de conquista / nível, em qualquer tela)
# ============================================================

class Toasts:
    """Painéis que deslizam do canto direito e somem sozinhos."""

    DURACAO = 3.2
    LARGURA_T = 330
    ALTURA_T = 64

    def __init__(self, tocar_som=None):
        self.fila = []
        self.ativos = []            # [titulo, texto, premio, tempo]
        self.tocar_som = tocar_som

    def adicionar(self, titulo, texto, premio="", som="conquista"):
        self.fila.append((titulo, texto, premio, som))

    def atualizar(self, dt):
        # Um novo entra a cada 0,6 s (no máximo 3 na tela)
        if self.fila and len(self.ativos) < 3 and \
                (not self.ativos or self.ativos[-1][3] > 0.6):
            titulo, texto, premio, som = self.fila.pop(0)
            self.ativos.append([titulo, texto, premio, 0.0])
            if self.tocar_som and som:
                self.tocar_som(som)
        for t in self.ativos:
            t[3] += dt
        self.ativos = [t for t in self.ativos if t[3] < self.DURACAO]

    def desenhar(self, tela):
        # Canto de baixo, à direita, empilhando para cima (o topo da
        # tela tem o contador de moedas e os placares dos jogos)
        y = ALTURA - 16 - self.ALTURA_T
        for titulo, texto, premio, t in self.ativos:
            entrada = min(1.0, t / 0.25)
            saida = min(1.0, (self.DURACAO - t) / 0.3)
            k = min(entrada, saida)
            k = 1 - (1 - k) ** 3
            x = LARGURA - int((self.LARGURA_T + 16) * k)
            r = pygame.Rect(x, y, self.LARGURA_T, self.ALTURA_T)
            painel(tela, r, (34, 30, 64), AMARELO, 14, 3)
            # Medalhinha
            c = (r.x + 32, r.centery)
            pygame.draw.circle(tela, (200, 140, 30), c, 20)
            pygame.draw.circle(tela, AMARELO, c, 16)
            estrela(tela, c, 10, (255, 250, 210), t * 3)
            desenhar_texto(tela, titulo, (r.x + 62, r.y + 14), 12, AMARELO, "topleft")
            tam = tamanho_que_cabe(texto, r.w - (130 if premio else 76), (10, 8))
            desenhar_texto(tela, texto, (r.x + 62, r.y + 38), tam, BRANCO, "topleft")
            if premio:
                moeda(tela, (r.right - 58, r.y + 40), 8)
                desenhar_texto(tela, premio, (r.right - 46, r.y + 40), 10, AMARELO, "midleft")
            y -= self.ALTURA_T + 10
