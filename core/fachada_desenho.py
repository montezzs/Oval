import math

import pygame

from core import ui
from core import idioma
from core.idioma import t
from core.fachada import (CATALOGO, cor_parede, cor_porta, cor_telhado, tem_chamine)

# ============================================================
# DESENHO DAS CASAS DA RUA DOS OVOS
# ============================================================
# Tudo em coordenadas LOCAIS (s = 1): origem = centro da base da
# fachada, y para cima é negativo. A escala `s` dá a perspectiva
# (casas do fundo menores). As partes paradas vão para uma Surface
# em cache; as animadas (fumaça, bandeira, balões...) e as luzes da
# noite são desenhadas por cima a cada frame.
#
#   desenhar_casa(tela, ancora, s, casa, cor_ovo, noite, t, ...)
#   desenhar_luzes(tela, ancora, s, casa, cor_ovo, t, dormindo)  (depois do véu da noite)
#   desenhar_lote_vazio(tela, ancora, s, t, hover)
#   desenhar_caminho(tela, p0, p1, largura, estilo)
#   topo(casa) -> y local do ponto mais alto (para a placa do nome)

# Área local de desenho da casa (cabe tudo, inclusive enfeites)
X_MIN, X_MAX = -135, 135
Y_MIN, Y_MAX = -260, 40

TOPO_TELHADO = -172
VIDRO_DIA = (170, 215, 255)
VIDRO_NOITE = (55, 65, 105)
VIDRO_ACESO = (255, 214, 110)
VIDRO_DORMINDO = (40, 50, 90)

POS_JANELAS = ((-42, -70), (42, -70))
X_ITENS = {"esq": -100, "dir": 100}
AGUA_ESQ = (-40, -138)

CORES_FLORES = [(255, 90, 120), (255, 220, 60), (170, 110, 240)]


class Pincel:
    """Desenha em coordenadas locais x escala sobre uma Surface."""

    def __init__(self, sup, ox, oy, s):
        self.sup, self.ox, self.oy, self.s = sup, ox, oy, s

    def p(self, x, y):
        return (round(self.ox + x * self.s), round(self.oy + y * self.s))

    def w(self, largura):
        return max(1, round(largura * self.s)) if largura else 0

    def rect(self, cor, x, y, w, h, larg=0, raio=0):
        r = pygame.Rect(self.p(x, y), (max(1, round(w * self.s)), max(1, round(h * self.s))))
        pygame.draw.rect(self.sup, cor, r, self.w(larg), border_radius=max(0, round(raio * self.s)))
        return r

    def ellipse(self, cor, x, y, w, h, larg=0):
        r = pygame.Rect(self.p(x, y), (max(1, round(w * self.s)), max(1, round(h * self.s))))
        pygame.draw.ellipse(self.sup, cor, r, self.w(larg))
        return r

    def circle(self, cor, x, y, r, larg=0):
        pygame.draw.circle(self.sup, cor, self.p(x, y), max(1, round(r * self.s)), self.w(larg))

    def poly(self, cor, pts, larg=0):
        pygame.draw.polygon(self.sup, cor, [self.p(x, y) for x, y in pts], self.w(larg))

    def line(self, cor, a, b, larg=1):
        pygame.draw.line(self.sup, cor, self.p(*a), self.p(*b), self.w(larg))

    def lines(self, cor, pts, larg=1):
        pygame.draw.lines(self.sup, cor, False, [self.p(x, y) for x, y in pts], self.w(larg))

    def arc(self, cor, x, y, w, h, a0, a1, larg=1):
        r = pygame.Rect(self.p(x, y), (max(2, round(w * self.s)), max(2, round(h * self.s))))
        pygame.draw.arc(self.sup, cor, r, a0, a1, self.w(larg))

    def clip(self, x, y, w, h):
        self.sup.set_clip(pygame.Rect(self.p(x, y), (round(w * self.s) + 1, round(h * self.s) + 1)))

    def sem_clip(self):
        self.sup.set_clip(None)


def _meia_elipse(cx, cy, rx, ry, n=24):
    """Pontos da metade de cima de uma elipse (da esquerda para a direita)."""
    return [(cx - rx * math.cos(math.pi * i / n), cy - ry * math.sin(math.pi * i / n))
            for i in range(n + 1)]


# ============================================================
# PARTES DA CASA
# ============================================================

def _cerca(p, estilo):
    if estilo == "nenhuma":
        return
    for lado in (-1, 1):
        x0, x1 = (70, 125) if lado > 0 else (-125, -70)
        if estilo == "cerca_estacas":
            for x in range(x0, x1 + 1, 9):
                h = 18 + (x * 7) % 7
                p.rect((140, 95, 50), x - 2, -4 - h, 5, h)
                p.rect((110, 70, 35), x - 2, -4 - h, 5, h, 1)
            p.line((120, 120, 120), (x0, -14), (x1, -14), 1)
        elif estilo == "cerca_branca":
            p.rect((245, 245, 245), x0, -18, x1 - x0, 3)
            p.rect((245, 245, 245), x0, -9, x1 - x0, 3)
            for x in range(x0, x1 + 1, 10):
                p.rect((245, 245, 245), x - 3, -26, 6, 22)
                p.poly((245, 245, 245), [(x - 3, -26), (x + 3, -26), (x, -31)])
                p.rect((180, 180, 190), x - 3, -26, 6, 22, 1)
        elif estilo == "cerca_viva":
            p.rect((60, 150, 60), x0, -26, x1 - x0, 24, raio=10)
            for i in range(8):
                p.circle((85, 175, 80), x0 + 5 + i * (x1 - x0 - 10) / 7, -22 + (i % 3) * 6, 4)
            for i in range(3):
                p.circle((255, 255, 255), x0 + 10 + i * 18, -14 - (i % 2) * 6, 2)
        elif estilo == "cerca_ferro":
            p.rect((40, 40, 50), x0, -22, x1 - x0, 2)
            p.rect((40, 40, 50), x0, -8, x1 - x0, 2)
            for x in range(x0, x1 + 1, 8):
                p.rect((40, 40, 50), x - 1, -28, 2, 24)
                p.poly((40, 40, 50), [(x - 3, -28), (x + 3, -28), (x, -34)])
            for x in (x0, x1):
                p.circle((230, 190, 60), x, -30, 2)


def _chamine(p):
    p.rect((170, 90, 70), 30, -168, 18, 44)
    p.rect((140, 70, 55), 27, -172, 24, 7)
    p.rect((120, 60, 45), 30, -168, 18, 44, 1)


def _telhado(p, estilo, cor):
    borda = ui.escurecer(cor, 50)
    if estilo == "telhado_cogumelo":
        pts = _meia_elipse(0, -104, 88, 68)
        p.poly(cor, pts)
        p.poly(borda, pts, 3)
        for x, y, r in ((-50, -122, 9), (-12, -150, 10), (30, -130, 8), (58, -114, 6), (-28, -114, 6)):
            p.circle((255, 255, 255), x, y, r)
        p.rect(ui.escurecer(cor, 40), -84, -108, 168, 6, raio=3)
        return
    if estilo == "telhado_palha":
        palha = ui.misturar((230, 195, 110), cor, 0.3)
        pts = [(-86, -100), (0, -178), (86, -100)]
        p.poly(palha, pts)
        for x in range(-80, 81, 4):
            topo = -100 - 78 * (1 - abs(x) / 86)
            p.line((200, 160, 80), (x, -102), (x, max(topo + 6, -102 - 22)), 1)
            p.line((200, 160, 80), (x * 0.6, topo * 0.5 - 60), (x * 0.6, topo * 0.5 - 50), 1)
        franja = []
        for i in range(0, 18):
            x = -86 + i * (172 / 17)
            franja.append((x, -100 + (5 if i % 2 else 0)))
        p.lines((180, 140, 60), franja, 2)
        p.poly(ui.escurecer(palha, 50), pts, 2)
        p.circle((255, 255, 255), 0, -128, 10)
        return

    pts = [(-80, -104), (0, -172), (80, -104)]
    p.poly(cor, pts)
    if estilo == "telhado_telhas":
        escura = ui.escurecer(cor, 20)
        linha = 0
        y = -110
        while y > -164:
            meia = 80 * (y + 172) / 68 - 6
            x = -meia
            i = 0
            while x <= meia:
                p.circle(escura if (i + linha) % 2 else cor, x, y, 6)
                p.arc(ui.escurecer(cor, 45), x - 6, y - 6, 12, 12, math.pi, 2 * math.pi, 1)
                x += 12
                i += 1
            y -= 9
            linha += 1
    # Beiral
    p.line(borda, (-84, -101), (0, -174), 4)
    p.line(borda, (84, -101), (0, -174), 4)
    p.poly(borda, pts, 3)


def _janela_do_sotao(p, estilo, vidro):
    if estilo in ("triangulo", "telhado_telhas", "telhado_palha"):
        p.circle(vidro, 0, -128, 8)
        p.circle((255, 255, 255), 0, -128, 10, 3)


def _parede(p, estilo, cor):
    p.rect(cor, -65, -110, 130, 110)
    p.clip(-65, -110, 130, 110)
    if estilo == "parede_madeira":
        esc = ui.escurecer(cor, 30)
        for y in range(-110, 0, 12):
            p.line(esc, (-65, y), (65, y), 2)
            p.rect(esc, -62, y + 5, 2, 2)
            p.rect(esc, 60, y + 5, 2, 2)
    elif estilo == "parede_listras":
        cl = ui.clarear(cor, 35)
        for i, x in enumerate(range(-65, 65, 10)):
            if i % 2:
                p.rect(cl, x, -110, 10, 110)
    elif estilo == "parede_bolinhas":
        cl = ui.clarear(cor, 45)
        for j, y in enumerate(range(-104, 0, 16)):
            for x in range(-60 + (8 if j % 2 else 0), 66, 16):
                p.circle(cl, x, y, 3)
    elif estilo == "parede_tijolo":
        rejunte = (235, 225, 210)
        tijolo = ui.misturar(cor, (200, 110, 80), 0.55)
        p.rect(rejunte, -65, -110, 130, 110)
        for j, y in enumerate(range(-110, 0, 10)):
            x = -65 - (11 if j % 2 else 0)
            while x < 65:
                p.rect(tijolo, x + 1, y + 1, 20, 8)
                x += 22
    elif estilo == "parede_pedra":
        p.rect((90, 90, 100), -65, -110, 130, 110)
        base = ui.misturar(cor, (170, 170, 180), 0.5)
        tamanhos = [18, 24, 14, 20, 22, 16]
        for j, y in enumerate(range(-110, 0, 14)):
            x = -65 - (j % 3) * 6
            k = j
            while x < 65:
                w = tamanhos[k % len(tamanhos)]
                var = ((k * 37) % 25) - 12
                c = tuple(max(0, min(255, v + var)) for v in base)
                p.rect(c, x + 1.5, y + 1.5, w - 3, 11, raio=3)
                x += w
                k += 1
    p.sem_clip()
    p.rect(ui.escurecer(cor, 35), -65, -10, 130, 10)
    p.rect(ui.escurecer(cor, 70), -65, -110, 130, 110, 3)


def _janela(p, estilo, cx, cy, vidro, moldura=True):
    branco = (255, 255, 255)
    if estilo == "janela_redonda":
        p.circle(vidro, cx, cy, 13)
        if moldura:
            p.line(branco, (cx - 13, cy), (cx + 13, cy), 2)
            p.line(branco, (cx, cy - 13), (cx, cy + 13), 2)
            p.circle(branco, cx, cy, 14, 3)
    elif estilo == "janela_arco":
        p.rect(vidro, cx - 14, cy - 6, 28, 20)
        p.circle(vidro, cx, cy - 6, 14)
        p.rect(vidro, cx - 14, cy - 6, 28, 4)
        if moldura:
            p.arc(branco, cx - 14, cy - 20, 28, 28, 0, math.pi, 3)
            p.line(branco, (cx - 14, cy - 6), (cx - 14, cy + 14), 3)
            p.line(branco, (cx + 14, cy - 6), (cx + 14, cy + 14), 3)
            p.line(branco, (cx - 14, cy + 14), (cx + 14, cy + 14), 3)
            p.line(branco, (cx, cy - 20), (cx, cy + 14), 2)
    elif estilo == "janela_coracao":
        pts = []
        for i in range(33):
            a = 2 * math.pi * i / 32
            x = 16 * math.sin(a) ** 3
            y = -(13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a))
            pts.append((cx + x * 0.85, cy + y * 0.85 - 1))
        p.poly(vidro, pts)
        if moldura:
            p.poly(branco, pts, 3)
    else:   # quadrada / com floreira
        p.rect(vidro, cx - 14, cy - 13, 28, 26)
        if moldura:
            p.line(branco, (cx - 14, cy), (cx + 14, cy), 2)
            p.line(branco, (cx, cy - 13), (cx, cy + 13), 2)
            p.rect(branco, cx - 14, cy - 13, 28, 26, 3)
        if estilo == "janela_floreira" and moldura:
            p.rect((150, 95, 55), cx - 17, cy + 15, 34, 7)
            for i, cor in enumerate(CORES_FLORES):
                fx = cx - 10 + i * 10
                p.circle((60, 150, 60), fx, cy + 14, 3)
                p.circle(cor, fx, cy + 12, 3)


def _porta(p, estilo, cor, cor_ovo):
    borda = ui.escurecer(cor, 55)
    ouro = (255, 214, 64)
    if estilo == "porta_arco":
        p.rect(cor, -16, -42, 32, 42)
        p.circle(cor, 0, -42, 16)
        p.rect(cor, -16, -44, 32, 6)
        p.arc(borda, -16, -58, 32, 32, 0, math.pi, 2)
        p.line(borda, (-16, -42), (-16, 0), 2)
        p.line(borda, (16, -42), (16, 0), 2)
        p.circle(ouro, 9, -24, 3)
    elif estilo == "porta_redonda":
        p.clip(-26, -50, 52, 50)
        p.circle(cor, 0, -24, 24)
        p.circle(borda, 0, -24, 24, 2)
        p.line(borda, (-8, -46), (-8, 0), 1)
        p.line(borda, (8, -46), (8, 0), 1)
        p.sem_clip()
        p.circle(ouro, 0, -24, 4)
    elif estilo == "porta_ovo":
        p.clip(-20, -64, 40, 64)
        p.ellipse(cor, -16, -60, 32, 62)
        p.ellipse(ouro, -16, -60, 32, 62, 3)
        p.sem_clip()
        p.ellipse(cor_ovo, 6, -30, 5, 6)
        p.ellipse(ui.escurecer(cor_ovo, 60), 6, -30, 5, 6, 1)
        p.circle(ouro, 0, -44, 4, 2)
    else:
        p.rect(cor, -16, -54, 32, 54)
        p.rect(borda, -16, -54, 32, 54, 2)
        p.rect(ui.escurecer(cor, 25), -11, -48, 22, 18, 1)
        p.circle(ouro, 9, -27, 3)
    p.rect((190, 190, 195), -22, 0, 44, 5)


def _correio(p, estilo, cor_ovo, carta=False):
    p.rect((120, 80, 40), 52, -18, 4, 26)
    if estilo == "correio_ovo":
        p.ellipse(cor_ovo, 44, -36, 20, 26)
        p.ellipse(ui.escurecer(cor_ovo, 70), 44, -36, 20, 26, 2)
        p.arc((60, 40, 30), 48, -30, 12, 10, 0, math.pi, 2)
        cx = 64
    else:
        p.rect((60, 110, 220), 44, -30, 24, 14, raio=4)
        p.rect((30, 70, 160), 44, -30, 24, 14, 1, raio=4)
        cx = 66
    if carta:
        p.rect((230, 60, 60), cx, -40, 3, 10)
        p.rect((230, 60, 60), cx, -40, 7, 4)
    else:
        p.rect((230, 60, 60), cx - 4, -22, 10, 3)


# ============================================================
# ITENS DE CHÃO
# ============================================================

def _flor(p, x, y, cor, r=3):
    for i in range(5):
        a = i * 2 * math.pi / 5
        p.circle(cor, x + math.cos(a) * r, y + math.sin(a) * r, r * 0.8)
    p.circle((255, 230, 90), x, y, max(1, r * 0.6))


def item_chao(p, item, x, cor_ovo, t=0.0):
    """Desenha um item de chão com a base em (x, 0)."""
    if item == "vaso_flor":
        for i, (dx, h, cor) in enumerate(((-7, 30, CORES_FLORES[0]), (0, 38, CORES_FLORES[1]),
                                          (7, 30, CORES_FLORES[2]))):
            p.line((70, 150, 60), (x + dx * 0.4, -22), (x + dx, -22 - h + 20), 2)
            _flor(p, x + dx, -24 - h + 20, cor)
        p.poly((200, 110, 60), [(x - 12, 0), (x + 12, 0), (x + 15, -20), (x - 15, -20)])
        p.rect((170, 90, 50), x - 17, -24, 34, 5, raio=2)
    elif item == "cacto":
        p.rect((80, 170, 90), x - 8, -44, 16, 44, raio=8)
        p.rect((80, 170, 90), x - 18, -30, 10, 18, raio=5)
        p.rect((80, 170, 90), x + 8, -36, 10, 14, raio=5)
        for dx, dy in ((-3, -34), (3, -22), (-2, -14), (4, -40), (-14, -24), (12, -30)):
            p.circle((250, 250, 250), x + dx, dy, 1)
        p.circle((255, 120, 170), x, -45, 3)
        p.poly((200, 110, 60), [(x - 12, 0), (x + 12, 0), (x + 14, -10), (x - 14, -10)])
    elif item == "flamingo":
        p.line((230, 100, 140), (x, 0), (x, -38), 2)
        p.ellipse((255, 130, 170), x - 12, -46, 24, 14)
        p.lines((255, 130, 170), [(x + 8, -42), (x + 11, -52), (x + 6, -60)], 3)
        p.circle((255, 130, 170), x + 5, -62, 5)
        p.poly((40, 40, 40), [(x + 1, -63), (x - 6, -60), (x + 1, -60)])
        p.circle((20, 20, 20), x + 6, -63, 1)
    elif item == "anao_jardim":
        p.poly((60, 110, 200), [(x - 11, 0), (x + 11, 0), (x + 8, -20), (x - 8, -20)])
        p.circle((255, 210, 170), x, -26, 7)
        p.poly((250, 250, 250), [(x - 7, -24), (x + 7, -24), (x, -12)])
        p.poly((220, 50, 50), [(x - 8, -30), (x + 8, -30), (x + 3, -48)])
        p.circle((240, 150, 130), x, -26, 2)
        piscou = (t % 5) < 0.15
        p.circle((20, 20, 20), x - 3, -29, 1)
        if piscou:
            p.line((20, 20, 20), (x + 2, -29), (x + 4, -29), 1)
        else:
            p.circle((20, 20, 20), x + 3, -29, 1)
    elif item == "canteiro_flores":
        cores = CORES_FLORES + [(255, 255, 255), (255, 150, 60)]
        for i in range(7):
            fx = x - 21 + i * 7
            h = 14 + (i * 5) % 11
            p.line((70, 150, 60), (fx, -8), (fx, -8 - h), 2)
            _flor(p, fx, -8 - h, cores[i % len(cores)], 3)
        p.rect((150, 100, 55), x - 24, -10, 48, 10)
        p.rect((110, 70, 35), x - 24, -10, 48, 10, 1)
        p.rect((90, 60, 40), x - 22, -11, 44, 3)
    elif item == "casinha_passaro":
        p.rect((140, 95, 50), x - 2, -50, 4, 50)
        p.rect((230, 180, 90), x - 12, -72, 24, 22)
        p.poly((190, 70, 60), [(x - 15, -72), (x, -86), (x + 15, -72)])
        p.circle((30, 20, 20), x, -62, 4)
        if (t % 12) > 9:
            p.circle((90, 160, 240), x + 4, -89, 4)
            p.poly((255, 170, 40), [(x + 8, -90), (x + 11, -89), (x + 8, -88)])
    elif item == "abobora_lanterna":
        p.ellipse((255, 140, 30), x - 16, -24, 32, 24)
        p.arc((220, 110, 20), x - 8, -24, 16, 24, math.pi / 2, 3 * math.pi / 2, 1)
        p.arc((220, 110, 20), x - 8, -24, 16, 24, -math.pi / 2, math.pi / 2, 1)
        p.rect((80, 140, 50), x - 2, -28, 4, 6)
        rosto = (70, 40, 10)
        p.poly(rosto, [(x - 9, -15), (x - 4, -15), (x - 6, -19)])
        p.poly(rosto, [(x + 4, -15), (x + 9, -15), (x + 6, -19)])
        p.poly(rosto, [(x - 8, -9), (x + 8, -9), (x, -5)])
    elif item == "poste_luz":
        p.rect((60, 60, 70), x - 2, -84, 4, 84)
        p.arc((60, 60, 70), x, -92, 16, 16, math.pi / 2, math.pi, 3)
        p.poly((40, 40, 50), [(x + 4, -82), (x + 16, -82), (x + 13, -72), (x + 7, -72)])
        p.rect((255, 240, 190), x + 7, -80, 6, 7)
        p.rect((60, 60, 70), x - 6, -4, 12, 4)
    elif item == "banco":
        p.rect((40, 40, 50), x - 22, -18, 3, 18)
        p.rect((40, 40, 50), x + 19, -18, 3, 18)
        p.rect((170, 110, 60), x - 26, -18, 52, 6)
        p.rect((170, 110, 60), x - 26, -34, 52, 5)
        p.rect((170, 110, 60), x - 26, -26, 52, 5)
        p.rect((40, 40, 50), x - 24, -36, 3, 20)
        p.rect((40, 40, 50), x + 21, -36, 3, 20)
    elif item == "arvore":
        p.rect((120, 80, 45), x - 7, -60, 14, 60)
        for cx, cy, r in ((0, -92, 30), (-18, -76, 22), (18, -76, 22)):
            p.circle((70, 170, 70), x + cx, cy, r)
        for cx, cy, r in ((-8, -100, 12), (12, -84, 9), (-20, -80, 8)):
            p.circle((100, 200, 90), x + cx, cy, r)
        for cx, cy in ((-12, -70), (16, -90), (4, -104)):
            p.circle((220, 40, 50), x + cx, cy, 3)
    elif item == "bicicleta":
        for dx in (-16, 16):
            p.circle((40, 40, 50), x + dx, -11, 11, 3)
            for a in range(4):
                ang = a * math.pi / 4
                p.line((150, 150, 160), (x + dx - math.cos(ang) * 9, -11 - math.sin(ang) * 9),
                       (x + dx + math.cos(ang) * 9, -11 + math.sin(ang) * 9), 1)
        quadro = cor_ovo
        p.lines(quadro, [(x - 16, -11), (x - 2, -11), (x + 10, -26), (x - 8, -26), (x - 16, -11)], 3)
        p.line(quadro, (x + 10, -26), (x + 16, -11), 3)
        p.line(quadro, (x - 2, -11), (x - 10, -30), 3)
        p.rect((40, 40, 50), x - 15, -33, 10, 4, raio=2)
        p.line((60, 60, 70), (x + 10, -26), (x + 12, -34), 2)
        p.line((60, 60, 70), (x + 8, -34), (x + 17, -34), 2)
        p.rect((150, 100, 55), x + 12, -32, 12, 8, raio=2)
        _flor(p, x + 16, -34, CORES_FLORES[0], 2)
        _flor(p, x + 21, -35, CORES_FLORES[1], 2)
    elif item == "arbusto_ovo":
        p.ellipse((60, 150, 60), x - 18, -62, 36, 52)
        for i in range(12):
            a = i * 2.4
            p.circle((80, 175, 75), x + math.cos(a) * (6 + i % 4 * 3), -36 + math.sin(a) * (10 + i % 3 * 5), 4)
        p.rect((180, 180, 190), x - 14, -10, 28, 10)
        p.rect((140, 140, 150), x - 14, -10, 28, 10, 1)
    elif item == "espantalho":
        p.line((140, 95, 50), (x, 0), (x, -70), 3)
        p.line((140, 95, 50), (x - 24, -50), (x + 24, -50), 3)
        p.poly((220, 80, 70), [(x - 20, -54), (x + 20, -54), (x + 12, -26), (x - 12, -26)])
        p.line((170, 50, 50), (x - 6, -54), (x - 4, -26), 1)
        p.line((170, 50, 50), (x + 6, -54), (x + 4, -26), 1)
        p.line((170, 50, 50), (x - 16, -40), (x + 16, -40), 1)
        p.circle((230, 200, 140), x, -62, 10)
        for dx in (-4, 4):
            p.line((60, 40, 20), (x + dx - 2, -65), (x + dx + 2, -61), 1)
            p.line((60, 40, 20), (x + dx + 2, -65), (x + dx - 2, -61), 1)
        p.arc((60, 40, 20), x - 5, -62, 10, 6, math.pi, 2 * math.pi, 1)
        p.ellipse((230, 190, 90), x - 16, -73, 32, 7)
        p.rect((230, 190, 90), x - 8, -82, 16, 11, raio=3)
    elif item == "fonte":
        p.ellipse((200, 200, 215), x - 28, -16, 56, 16)
        p.ellipse((110, 190, 250), x - 24, -14, 48, 10)
        p.rect((215, 215, 225), x - 4, -38, 8, 24)
        p.ellipse((200, 200, 215), x - 14, -42, 28, 8)
        for i in range(8):
            fase = (t * 0.9 + i / 8) % 1.0
            lado = -1 if i % 2 else 1
            dx = lado * (4 + fase * 16)
            dy = -44 - 14 * math.sin(fase * math.pi) + fase * 30
            p.circle((170, 220, 255), x + dx, dy, 2)
    else:
        return False
    return True


# ============================================================
# ITENS DO TELHADO
# ============================================================

def item_telhado(p, item, cor_ovo, t=0.0, vento=0.3):
    if item == "antena":
        x, y = AGUA_ESQ
        p.line((100, 100, 110), (x, y), (x, y - 30), 2)
        p.line((100, 100, 110), (x - 12, y - 26), (x + 12, y - 26), 2)
        for dx in (-10, -4, 4, 10):
            p.line((100, 100, 110), (x + dx, y - 26), (x + dx, y - 32), 1)
    elif item == "bandeira":
        p.line((200, 200, 210), (0, -172), (0, -210), 2)
        pts_cima, pts_baixo = [], []
        for i in range(7):
            dx = i * 26 / 6
            onda = math.sin(t * 5 - i * 0.9) * 2.5 * (i / 6)
            pts_cima.append((1 + dx, -208 + onda))
            pts_baixo.append((1 + dx, -192 + onda))
        pts = pts_cima + pts_baixo[::-1]
        p.poly(cor_ovo, pts)
        p.poly(ui.escurecer(cor_ovo, 60), pts, 1)
        meio = pts_cima[3]
        p.ellipse((255, 255, 255), meio[0] - 3, meio[1] + 4, 6, 8)
    elif item == "baloes":
        for i, (bx, by, cor) in enumerate(((-14, -218, (255, 90, 90)), (0, -228, (90, 180, 255)),
                                           (14, -216, (255, 220, 60)))):
            by += math.sin(t * 2 + i) * 3
            p.line((80, 80, 90), (0, -172), (bx, by + 9), 1)
            p.ellipse(cor, bx - 7, by - 9, 14, 18)
            p.circle((255, 255, 255), bx - 3, by - 4, 2)
    elif item == "cata_vento_galo":
        p.line((60, 60, 70), (0, -172), (0, -204), 2)
        p.line((60, 60, 70), (-8, -184), (8, -184), 1)
        ang = t * (1 + vento * 4)
        larg = math.cos(ang)
        cx, cy = 0, -208
        corpo = [(cx - 12 * larg, cy), (cx + 10 * larg, cy - 2), (cx + 12 * larg, cy - 10),
                 (cx + 6 * larg, cy - 8), (cx + 2 * larg, cy - 2), (cx - 8 * larg, cy - 10)]
        p.poly((40, 40, 50), corpo)
        p.line((40, 40, 50), (-10, -172), (10, -172), 1)
    elif item == "pisca_pisca":
        for i, (x, y) in enumerate(_pontos_beiral()):
            p.circle(_COR_PISCA[i % 4], x, y, 3)
    elif item == "painel_solar":
        cx, cy = AGUA_ESQ
        dx, dy = 0.762, -0.648
        nx, ny = -0.648, -0.762
        a = (cx - dx * 18, cy - dy * 18)
        b = (cx + dx * 18, cy + dy * 18)
        c = (b[0] + nx * 12, b[1] + ny * 12)
        d = (a[0] + nx * 12, a[1] + ny * 12)
        p.poly((40, 60, 110), [a, b, c, d])
        for k in (1, 2):
            f = k / 3
            p.line((90, 120, 180), (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f),
                   (d[0] + (c[0] - d[0]) * f, d[1] + (c[1] - d[1]) * f), 1)
        p.line((90, 120, 180), ((a[0] + d[0]) / 2, (a[1] + d[1]) / 2), ((b[0] + c[0]) / 2, (b[1] + c[1]) / 2), 1)
        brilho = (t % 5) / 5
        if brilho < 0.4:
            f = brilho / 0.4
            p.line((200, 220, 255), (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f),
                   (d[0] + (c[0] - d[0]) * f, d[1] + (c[1] - d[1]) * f), 2)
        p.poly((200, 200, 210), [a, b, c, d], 1)
    elif item == "gato_telhado":
        cx, cy = AGUA_ESQ[0] - 4, AGUA_ESQ[1] - 6
        rabo = math.sin(t * 2) * 6
        p.lines((240, 160, 70), [(cx - 14, cy + 2), (cx - 18, cy + 10), (cx - 16 + rabo, cy + 20)], 3)
        p.ellipse((240, 160, 70), cx - 15, cy - 7, 30, 14)
        for k in (-6, 0, 6):
            p.line((200, 120, 40), (cx + k, cy - 6), (cx + k + 1, cy - 2), 1)
        p.circle((240, 160, 70), cx + 14, cy - 8, 8)
        p.poly((240, 160, 70), [(cx + 8, cy - 12), (cx + 10, cy - 20), (cx + 14, cy - 14)])
        p.poly((240, 160, 70), [(cx + 16, cy - 14), (cx + 20, cy - 20), (cx + 21, cy - 11)])
        p.line((60, 40, 20), (cx + 10, cy - 8), (cx + 13, cy - 8), 1)
        p.line((60, 40, 20), (cx + 16, cy - 8), (cx + 19, cy - 8), 1)
    else:
        return False
    return True


_COR_PISCA = [(255, 90, 90), (255, 220, 60), (90, 200, 255), (120, 230, 120)]


def _pontos_beiral():
    pts = []
    for lado in (-1, 1):
        for i in range(1, 6):
            f = i / 6
            pts.append((lado * 80 * (1 - f), -104 - 68 * f + 3))
    return pts


def topo(casa):
    """y local do ponto mais alto da casa (para a placa do nome)."""
    y = TOPO_TELHADO
    if casa["telhado"] == "telhado_palha":
        y = -178
    enfeite = casa["itens"].get("telhado", "")
    y = min(y, {"bandeira": -212, "baloes": -238, "cata_vento_galo": -214}.get(enfeite, y))
    return y


# ============================================================
# CASA INTEIRA
# ============================================================

_cache = {}
ANIMADOS_CHAO = {"fonte", "anao_jardim", "casinha_passaro"}
ANIMADOS_TELHADO = {"bandeira", "baloes", "cata_vento_galo", "painel_solar", "gato_telhado"}


def _chave(casa, cor_ovo, noite, s, carta, sem_itens):
    return (repr(sorted((k, v if not isinstance(v, dict) else tuple(sorted(v.items())))
                        for k, v in casa.items())), tuple(cor_ovo), noite, round(s, 3), carta, sem_itens)


def _estatica(casa, cor_ovo, noite, s, carta=False, sem_itens=False):
    chave = _chave(casa, cor_ovo, noite, s, carta, sem_itens)
    sup = _cache.get(chave)
    if sup is not None:
        return sup
    if len(_cache) > 200:
        _cache.clear()
    w = round((X_MAX - X_MIN) * s) + 2
    h = round((Y_MAX - Y_MIN) * s) + 2
    sup = pygame.Surface((w, h), pygame.SRCALPHA)
    p = Pincel(sup, -X_MIN * s, -Y_MIN * s, s)

    parede = cor_parede(casa)
    telhado = cor_telhado(casa, cor_ovo)
    vidro = VIDRO_NOITE if noite else VIDRO_DIA

    p.ellipse((165, 212, 145), -125, -10, 250, 28)
    _cerca(p, casa["cerca"])
    if tem_chamine(casa):
        _chamine(p)
    _parede(p, casa["parede"], parede)
    _telhado(p, casa["telhado"], telhado)
    _janela_do_sotao(p, casa["telhado"], vidro)
    for cx, cy in POS_JANELAS:
        _janela(p, casa["janela"], cx, cy, vidro)
    _porta(p, casa["porta"], cor_porta(casa), cor_ovo)
    _correio(p, casa["correio"], cor_ovo, carta)
    if not sem_itens:
        enfeite = casa["itens"].get("telhado", "")
        if enfeite and enfeite not in ANIMADOS_TELHADO:
            item_telhado(p, enfeite, cor_ovo)
        for lado in ("esq", "dir"):
            it = casa["itens"].get(lado, "")
            if it and it not in ANIMADOS_CHAO:
                item_chao(p, it, X_ITENS[lado], cor_ovo)
    _cache[chave] = sup
    return sup


def desenhar_casa(tela, ancora, s, casa, cor_ovo, noite=False, t=0.0, morador=True,
                  dormindo=False, vento=0.3, carta=False, escala_y=1.0):
    """Desenha a casa com a base da fachada em `ancora`."""
    ax, ay = ancora
    sup = _estatica(casa, cor_ovo, noite, s, carta)
    if escala_y != 1.0:
        if escala_y <= 0.02:
            return
        w, h = sup.get_size()
        sup = pygame.transform.smoothscale(sup, (w, max(1, round(h * escala_y))))
        tela.blit(sup, (round(ax + X_MIN * s), round(ay - (-Y_MIN * s) * escala_y)))
        return
    tela.blit(sup, (round(ax + X_MIN * s), round(ay + Y_MIN * s)))

    p = Pincel(tela, ax, ay, s)
    # Fumaça da chaminé
    if morador and tem_chamine(casa):
        for i in range(3):
            f = (t / 2.4 + i / 3) % 1.0
            x = 39 + f * 10 * (0.5 + vento)
            y = -180 - f * 40
            if dormindo:
                if i == 0:
                    sup_z = ui.texto("z", max(8, round(10 * s)), (235, 235, 240), sombra=False).copy()
                    sup_z.set_alpha(int(220 * (1 - f)))
                    tela.blit(sup_z, p.p(x, y))
            else:
                r = 5 + f * 7
                cor = (235, 235, 240)
                bolha = pygame.Surface((round(r * 2 * s) + 2, round(r * 2 * s) + 2), pygame.SRCALPHA)
                pygame.draw.circle(bolha, (*cor, int(180 * (1 - f))), bolha.get_rect().center,
                                   max(1, round(r * s)))
                tela.blit(bolha, bolha.get_rect(center=p.p(x, y)))
    enfeite = casa["itens"].get("telhado", "")
    if enfeite in ANIMADOS_TELHADO:
        item_telhado(p, enfeite, cor_ovo, t, vento)
    for lado in ("esq", "dir"):
        it = casa["itens"].get(lado, "")
        if it in ANIMADOS_CHAO:
            item_chao(p, it, X_ITENS[lado], cor_ovo, t)


def desenhar_luzes(tela, ancora, s, casa, cor_ovo, t=0.0, dormindo=False, morador=True):
    """Luzes da noite (desenhar DEPOIS do véu escuro)."""
    ax, ay = ancora
    p = Pincel(tela, ax, ay, s)
    if morador:
        vidro = VIDRO_DORMINDO if dormindo else VIDRO_ACESO
        if not dormindo:
            for cx, cy in POS_JANELAS:
                _halo(tela, p.p(cx, cy), 30 * s, (255, 220, 130), 50)
        for cx, cy in POS_JANELAS:
            _janela(p, casa["janela"], cx, cy, vidro)
        _janela_do_sotao(p, casa["telhado"], vidro)
        if dormindo:
            for i in range(3):
                f = (t * 0.5 + i / 3) % 1.0
                z = ui.texto("z", max(8, round((8 + i * 2) * s)), (230, 230, 255), sombra=False).copy()
                z.set_alpha(int(255 * (1 - f)))
                tela.blit(z, p.p(-42 + f * 14, -86 - f * 30))
    itens = casa["itens"]
    for lado in ("esq", "dir"):
        x = X_ITENS[lado]
        if itens.get(lado) == "poste_luz":
            _halo(tela, p.p(x + 10, -76), 44 * s, (255, 240, 180), 35)
            _halo(tela, p.p(x + 10, -76), 24 * s, (255, 240, 180), 70)
            p.rect((255, 250, 210), x + 7, -80, 6, 7)
        elif itens.get(lado) == "abobora_lanterna":
            _halo(tela, p.p(x, -12), 26 * s, (255, 200, 90), 60)
            brilho = (255, 230, 120)
            p.poly(brilho, [(x - 9, -15), (x - 4, -15), (x - 6, -19)])
            p.poly(brilho, [(x + 4, -15), (x + 9, -15), (x + 6, -19)])
            p.poly(brilho, [(x - 8, -9), (x + 8, -9), (x, -5)])
    if itens.get("telhado") == "pisca_pisca":
        for i, (x, y) in enumerate(_pontos_beiral()):
            if math.sin(t * 4 - i * 0.7) > -0.2:
                _halo(tela, p.p(x, y), 8 * s, _COR_PISCA[i % 4], 70)
                p.circle(ui.clarear(_COR_PISCA[i % 4], 40), x, y, 3)
    if casa["janela"] == "janela_coracao" and morador and not dormindo:
        for cx, cy in POS_JANELAS:
            _halo(tela, p.p(cx, cy), 20 * s, (255, 170, 200), 50)


_halos = {}


def _halo(tela, centro, raio, cor, alpha):
    raio = max(2, round(raio))
    chave = (raio, cor, alpha)
    sup = _halos.get(chave)
    if sup is None:
        if len(_halos) > 200:
            _halos.clear()
        sup = pygame.Surface((raio * 2, raio * 2), pygame.SRCALPHA)
        for k in range(4, 0, -1):
            pygame.draw.circle(sup, (*cor, int(alpha * (1 - k / 5))), (raio, raio), round(raio * k / 4))
        _halos[chave] = sup
    tela.blit(sup, (centro[0] - raio, centro[1] - raio))


# ============================================================
# CAMINHO ATÉ A RUA
# ============================================================

def desenhar_caminho(tela, p0, p1, largura, estilo, t=0.0):
    """Quadrilátero de p0 (porta) até p1 (rua) com o estilo da fachada."""
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0
    comp = math.hypot(dx, dy) or 1
    nx, ny = -dy / comp * largura / 2, dx / comp * largura / 2
    pts = [(x0 + nx, y0 + ny), (x1 + nx, y1 + ny), (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)]
    if estilo == "caminho_pedras":
        n = max(2, int(comp / 16))
        for i in range(n):
            f = (i + 0.5) / n
            lado = (1 if i % 2 else -1) * 0.25
            cx, cy = x0 + dx * f + nx * lado, y0 + dy * f + ny * lado
            r = pygame.Rect(0, 0, max(4, largura * 0.55), max(3, largura * 0.32))
            r.center = (cx, cy)
            pygame.draw.ellipse(tela, (180, 180, 190), r)
            pygame.draw.ellipse(tela, (140, 140, 150), r, 1)
        return
    cores = {"terra": (200, 165, 115), "caminho_tijolos": (190, 100, 70),
             "caminho_tapete": (200, 30, 50)}
    if estilo == "caminho_arco_iris":
        faixas = [(255, 90, 90), (255, 180, 60), (255, 230, 70), (100, 210, 110), (90, 160, 255)]
        for i, cor in enumerate(faixas):
            a = -1 + 2 * i / 5
            b = -1 + 2 * (i + 1) / 5
            pygame.draw.polygon(tela, cor, [(x0 + nx * a, y0 + ny * a), (x1 + nx * a, y1 + ny * a),
                                            (x1 + nx * b, y1 + ny * b), (x0 + nx * b, y0 + ny * b)])
        return
    pygame.draw.polygon(tela, cores.get(estilo, (200, 165, 115)), pts)
    if estilo == "caminho_tijolos":
        n = max(2, int(comp / 8))
        for i in range(1, n):
            f = i / n
            cx, cy = x0 + dx * f, y0 + dy * f
            pygame.draw.line(tela, (230, 200, 170), (cx + nx, cy + ny), (cx - nx, cy - ny), 1)
    elif estilo == "caminho_tapete":
        pygame.draw.line(tela, (230, 190, 60), pts[0], pts[1], 2)
        pygame.draw.line(tela, (230, 190, 60), pts[3], pts[2], 2)


# ============================================================
# LOTE VAZIO / EM OBRAS
# ============================================================

def _tracejado(tela, a, b, cor, larg=2, traco=8, vao=6):
    dx, dy = b[0] - a[0], b[1] - a[1]
    comp = math.hypot(dx, dy)
    if comp == 0:
        return
    ux, uy = dx / comp, dy / comp
    d = 0.0
    while d < comp:
        e = min(comp, d + traco)
        pygame.draw.line(tela, cor, (a[0] + ux * d, a[1] + uy * d), (a[0] + ux * e, a[1] + uy * e), larg)
        d += traco + vao


def desenhar_lote_vazio(tela, ancora, s, t=0.0, hover=False, em_obras=False):
    ax, ay = ancora
    p = Pincel(tela, ax, ay, s)
    p.rect((190, 150, 100), -95, -14, 190, 24, raio=8)
    for i in range(6):
        x = -80 + i * 32
        p.line((120, 170, 90), (x, -8), (x - 3, -14), 2)
        p.line((120, 170, 90), (x, -8), (x + 3, -14), 2)

    # Casa-fantasma tracejada (os rabiscos do protótipo)
    if hover:
        sup = pygame.Surface((round(170 * s), round(180 * s)), pygame.SRCALPHA)
        q = Pincel(sup, 85 * s, 176 * s, s)
        q.rect((255, 255, 255, 40), -65, -110, 130, 102)
        q.poly((255, 255, 255, 40), [(-80, -104), (0, -172), (80, -104)])
        tela.blit(sup, (ax - 85 * s, ay - 176 * s))
    larg = max(1, round(2 * s))
    seg = [((-65, -8), (-65, -108)), ((65, -8), (65, -108)), ((-80, -104), (0, -172)),
           ((0, -172), (80, -104)), ((-80, -104), (80, -104))]
    for a, b in seg:
        _tracejado(tela, p.p(*a), p.p(*b), (255, 255, 255), larg, max(3, 8 * s), max(2, 6 * s))

    if em_obras:
        # Fita listrada e cones
        for i in range(12):
            x = -70 + i * 12
            cor = (255, 200, 40) if i % 2 == 0 else (40, 40, 40)
            p.poly(cor, [(x, -40), (x + 12, -40), (x + 12, -30), (x, -30)])
        for cx in (-50, 50):
            p.poly((255, 130, 30), [(cx - 10, 0), (cx + 10, 0), (cx + 3, -26), (cx - 3, -26)])
            p.rect((255, 255, 255), cx - 6, -14, 12, 4)
            p.rect((255, 130, 30), cx - 13, -3, 26, 4)
        return

    # Placa +NOVO (balança no hover)
    ang = math.sin(t * 8) * 4 if hover else 0
    esc = 1.1 if hover else 1.0
    placa = _placa_novo(s * esc)
    if ang:
        placa = pygame.transform.rotate(placa, ang)
    tela.blit(placa, placa.get_rect(midbottom=p.p(0, 0)))


_placas = {}


def _placa_novo(s):
    chave = (round(s, 2), idioma.atual())
    sup = _placas.get(chave)
    if sup is None:
        w, h = round(96 * s), round(80 * s)
        sup = pygame.Surface((w, h), pygame.SRCALPHA)
        q = Pincel(sup, 48 * s, 78 * s, s)
        q.rect((120, 80, 40), -22, -46, 5, 46)
        q.rect((120, 80, 40), 17, -46, 5, 46)
        q.rect((255, 248, 230), -44, -76, 88, 34, raio=6)
        q.rect((120, 80, 40), -44, -76, 88, 34, 3, raio=6)
        txt = ui.texto(t("+NOVO"), max(8, round(12 * s)), (60, 160, 60), sombra=False)
        sup.blit(txt, txt.get_rect(center=q.p(0, -59)))
        _placas[chave] = sup
    return sup


# ============================================================
# MINIATURAS (cards da reforma)
# ============================================================

_minis = {}


def miniatura_item(item, parte, cor_ovo, tamanho):
    """Um item de chão / telhado sozinho, cabendo em `tamanho`."""
    chave = (item, parte, tuple(cor_ovo), tamanho)
    sup = _minis.get(chave)
    if sup is not None:
        return sup
    if len(_minis) > 300:
        _minis.clear()
    w, h = tamanho
    sup = pygame.Surface((w, h), pygame.SRCALPHA)
    if parte == "chao":
        s = min(w / 70, h / 110)
        p = Pincel(sup, w / 2, h - 4, s)
        item_chao(p, item, 0, cor_ovo, 0.0)
    else:
        s = min(w / 150, h / 130)
        p = Pincel(sup, w / 2, h + 96 * s, s)
        p.poly((200, 60, 55), [(-80, -104), (0, -172), (80, -104)])
        item_telhado(p, item, cor_ovo, 0.0)
    _minis[chave] = sup
    return sup
