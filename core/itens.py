import math

import pygame

from settings import *
from core import ui

# ============================================================
# ITENS CONSUMÍVEIS: COMIDAS, SEMENTES E PLANTAS
# ============================================================
# Tudo é desenhado com primitivas e guardado em cache:
#   desenhar_comida(tela, id, centro, tamanho)  ícone da comida
#   icone_semente(id, tamanho)                  pacotinho de sementes
#   desenhar_planta(tela, id, estagio, base, t) planta no canteiro

# ============================================================
# COMIDAS (mercado)
# ============================================================
# efeitos: necessidade -> quanto sobe. `cor` = cor das migalhas.
# `especial`: reação do ovo ao comer (a cena decide o que fazer):
#   "frio" (BRRR), "pimenta" (fica vermelho + foguinho), "confete".

COMIDAS = {
    "limao": dict(nome="LIMÃO", preco=0, efeitos={"fome": 8}, loja=False,
                  cor=(250, 222, 40), especial=None),
    "maca": dict(nome="MAÇÃ", preco=8, efeitos={"fome": 15}, loja=True,
                 cor=(220, 50, 50), especial=None),
    "banana": dict(nome="BANANA", preco=10, efeitos={"fome": 18, "energia": 3}, loja=True,
                   cor=(255, 225, 80), especial=None),
    "leite": dict(nome="LEITE", preco=12, efeitos={"fome": 10, "energia": 10}, loja=True,
                  cor=(245, 245, 255), especial=None),
    "pao_queijo": dict(nome="PÃO DE QUEIJO", preco=12, efeitos={"fome": 22}, loja=True,
                       cor=(240, 200, 120), especial=None),
    "suco_limao": dict(nome="SUCO DE LIMÃO", preco=15,
                       efeitos={"fome": 8, "energia": 15, "diversao": 5}, loja=True,
                       cor=(250, 240, 140), especial=None),
    "sanduiche": dict(nome="SANDUÍCHE", preco=20, efeitos={"fome": 35}, loja=True,
                      cor=(225, 180, 110), especial=None),
    "sorvete": dict(nome="SORVETE", preco=25, efeitos={"fome": 15, "diversao": 20}, loja=True,
                    cor=(255, 160, 200), especial="frio"),
    "pizza": dict(nome="PIZZA", preco=35, efeitos={"fome": 60, "diversao": 5}, loja=True,
                  cor=(255, 200, 80), especial=None),
    "bolo": dict(nome="BOLO", preco=40, efeitos={"fome": 40, "diversao": 20}, loja=True,
                 cor=(255, 170, 200), especial="confete"),
    "pimenta": dict(nome="PIMENTA", preco=10, efeitos={"fome": 5, "diversao": 10}, loja=True,
                    cor=(230, 40, 40), especial="pimenta"),
    "morango": dict(nome="MORANGO", preco=0, efeitos={"fome": 20}, loja=False,
                    cor=(230, 50, 70), especial=None),
    "marshmallow": dict(nome="MARSHMALLOW", preco=0, efeitos={"fome": 10, "diversao": 10},
                        loja=False, cor=(255, 230, 240), especial=None),
    # Vem da ABÓBORA GIGANTE quando o jogador escolhe comer em vez de vender
    "abobora": dict(nome="ABÓBORA GIGANTE", preco=0, efeitos={"fome": 100}, loja=False,
                    cor=(255, 150, 40), especial="confete"),
}

# ============================================================
# SEMENTES (tempo em segundos reais, por estágio completo)
# ============================================================
# colheita: comida (id -> qtd) + moedas. A abóbora tem `escolha`:
# ou as moedas, ou vira comida. A árvore de OVOEDAS dá 5 colheitas.

SEMENTES = {
    "semente_limao": dict(nome="SEMENTE DE LIMÃO", preco=15, tempo=600,
                          colheita=dict(comida={"limao": 3}, moedas=5),
                          cor=(250, 215, 50), planta="LIMOEIRO"),
    "semente_morango": dict(nome="SEMENTE DE MORANGO", preco=30, tempo=1800,
                            colheita=dict(comida={"morango": 3}, moedas=10),
                            cor=(240, 90, 120), planta="MORANGUEIRO"),
    "semente_girassol": dict(nome="SEMENTE DE GIRASSOL", preco=45, tempo=3600,
                             colheita=dict(comida={}, moedas=60),
                             cor=(255, 170, 40), planta="GIRASSOL"),
    "semente_abobora": dict(nome="SEMENTE DE ABÓBORA", preco=90, tempo=10800,
                            colheita=dict(comida={}, moedas=170,
                                          escolha=dict(comida={"abobora": 1})),
                            cor=(120, 190, 80), planta="ABÓBORA GIGANTE"),
    "semente_moedas": dict(nome="SEMENTE DE OVOEDAS", preco=400, tempo=43200,
                           colheita=dict(comida={}, moedas=120), colheitas=5,
                           cor=(150, 110, 220), planta="ÁRVORE DE OVOEDAS"),
}

ESTAGIOS = ["BROTO", "MUDA", "PLANTA", "PRONTA"]

CONTORNO = (45, 30, 25)


# ============================================================
# AJUDANTES
# ============================================================

def _preparar(sup, rle=False):
    """Converte para o formato da tela; `rle=True` acelera o blit de
    sprites que nunca mudam."""
    if pygame.display.get_surface() is not None:
        sup = sup.convert_alpha()
    if rle:
        sup.set_alpha(255, pygame.RLEACCEL)
    return sup


def _contornar(sup, cor=CONTORNO, grossura=2):
    """Contorno escuro em volta de tudo que não é transparente
    (deixa os ícones legíveis em fundo claro e escuro)."""
    mascara = pygame.mask.from_surface(sup, 40)
    silhueta = mascara.to_surface(setcolor=(*cor, 255), unsetcolor=(0, 0, 0, 0))
    saida = pygame.Surface(sup.get_size(), pygame.SRCALPHA)
    for dx in (-grossura, 0, grossura):
        for dy in (-grossura, 0, grossura):
            if dx or dy:
                saida.blit(silhueta, (dx, dy))
    saida.blit(sup, (0, 0))
    return saida


# ============================================================
# DESENHO DAS COMIDAS (em unidades de uma caixa 40x40)
# ============================================================

class _Pincel:
    """Desenha numa Surface usando coordenadas 0..40 (escala k)."""

    def __init__(self, sup, k):
        self.s = sup
        self.k = k

    def p(self, x, y):
        return (x * self.k, y * self.k)

    def r(self, x, y, w, h):
        return pygame.Rect(round(x * self.k), round(y * self.k), round(w * self.k), round(h * self.k))

    def w(self, v):
        return max(1, round(v * self.k))

    def circulo(self, cor, x, y, raio, larg=0):
        pygame.draw.circle(self.s, cor, self.p(x, y), max(1, raio * self.k),
                           self.w(larg) if larg else 0)

    def elipse(self, cor, x, y, w, h, larg=0):
        pygame.draw.ellipse(self.s, cor, self.r(x, y, w, h), self.w(larg) if larg else 0)

    def poligono(self, cor, pts, larg=0):
        pygame.draw.polygon(self.s, cor, [self.p(*q) for q in pts], self.w(larg) if larg else 0)

    def linha(self, cor, a, b, larg=1):
        pygame.draw.line(self.s, cor, self.p(*a), self.p(*b), self.w(larg))

    def rect(self, cor, x, y, w, h, larg=0, raio=0):
        pygame.draw.rect(self.s, cor, self.r(x, y, w, h), self.w(larg) if larg else 0,
                         border_radius=round(raio * self.k))

    def arco(self, cor, x, y, w, h, a0, a1, larg=1):
        pygame.draw.arc(self.s, cor, self.r(x, y, w, h), a0, a1, self.w(larg))


def _maca(p):
    p.circulo((200, 35, 45), 15, 23, 11)
    p.circulo((200, 35, 45), 25, 23, 11)
    p.circulo((225, 55, 60), 20, 25, 12)
    p.elipse((255, 150, 150), 11, 17, 6, 8)
    p.linha((110, 70, 30), (20, 14), (22, 6), 2.5)
    p.poligono((80, 180, 70), [(22, 10), (29, 5), (33, 8), (26, 12)])


def _banana(p):
    fora, dentro = [], []
    for i in range(13):
        a = math.radians(25 + i * 10)
        fora.append((20 + math.cos(a) * 17, 6 + math.sin(a) * 26))
        dentro.append((20 + math.cos(a) * 12, 7 + math.sin(a) * 18))
    p.poligono((255, 220, 60), fora + dentro[::-1])
    p.poligono((240, 190, 40), dentro[4:10] + [(q[0], q[1] + 2.5) for q in dentro[9:3:-1]])
    p.linha((110, 80, 30), fora[0], dentro[0], 3)
    p.circulo((90, 60, 25), fora[-1][0] + 0.5, fora[-1][1] - 1, 1.6)


def _leite(p):
    p.poligono((250, 250, 255), [(11, 13), (20, 5), (29, 13)])
    p.rect((250, 250, 255), 11, 13, 18, 23)
    p.rect((210, 215, 230), 23, 13, 6, 23)
    p.rect((70, 140, 230), 11, 23, 18, 8)
    p.circulo((250, 250, 255), 17, 27, 2.2)
    p.rect((220, 225, 240), 16, 3, 8, 3)
    p.poligono((230, 232, 245), [(20, 5), (29, 13), (26, 13)])


def _pao_queijo(p):
    p.circulo((240, 200, 120), 20, 22, 13)
    p.circulo((250, 220, 150), 17, 19, 8)
    for x, y in ((14, 20), (22, 16), (26, 25), (18, 28), (24, 21)):
        p.circulo((205, 150, 70), x, y, 1.6)
    p.elipse((255, 240, 200), 12, 13, 7, 4)


def _suco(p):
    p.linha((240, 60, 60), (24, 20), (31, 3), 2.5)
    p.linha((255, 255, 255), (27.5, 12), (29, 8), 2.5)
    copo = [(11, 12), (29, 12), (27, 36), (13, 36)]
    p.poligono((250, 238, 130), copo)
    p.poligono((255, 250, 200), [(11, 12), (29, 12), (28.5, 16), (11.5, 16)])
    p.linha((255, 255, 240), (14, 18), (15, 33), 1.5)
    p.circulo((250, 222, 40), 11, 12, 5)
    p.circulo((255, 245, 160), 11, 12, 3)


def _sanduiche(p):
    p.elipse((230, 175, 95), 6, 27, 28, 9)
    p.poligono((110, 200, 80), [(5, 25), (9, 22), (13, 26), (17, 22), (21, 26), (25, 22),
                                (29, 26), (33, 22), (35, 26), (35, 28), (5, 28)])
    p.rect((230, 70, 60), 7, 21, 26, 4, raio=2)
    p.poligono((255, 210, 60), [(6, 18), (34, 18), (31, 23), (27, 20), (22, 24), (17, 20), (12, 23)])
    p.elipse((235, 180, 100), 6, 8, 28, 13)
    p.elipse((250, 205, 130), 9, 9, 16, 6)
    for x, y in ((14, 11), (20, 10), (26, 12), (22, 14)):
        p.elipse((255, 250, 225), x, y, 2, 1.4)


def _sorvete(p):
    p.poligono((225, 170, 90), [(12, 20), (28, 20), (20, 38)])
    for i in range(3):
        p.linha((190, 130, 60), (14 + i * 5, 20), (20 + i * 3, 34 - i * 2), 1)
    p.linha((190, 130, 60), (13, 23), (26, 23), 1)
    p.circulo((255, 150, 190), 20, 15, 9)
    p.circulo((255, 150, 190), 13, 19, 4)
    p.circulo((255, 150, 190), 27, 19, 4)
    p.elipse((255, 210, 230), 14, 9, 6, 4)
    p.circulo((220, 30, 50), 21, 6, 2.5)


def _pizza(p):
    p.poligono((255, 205, 90), [(6, 10), (34, 10), (20, 37)])
    p.poligono((255, 225, 120), [(12, 14), (28, 14), (20, 30)])
    p.rect((215, 145, 65), 5, 7, 30, 6, raio=3)
    for x, y in ((14, 15), (24, 17), (19, 25)):
        p.circulo((200, 50, 40), x, y, 3)
        p.circulo((230, 90, 70), x - 0.8, y - 0.8, 1)


def _bolo(p):
    p.poligono((240, 200, 140), [(5, 20), (30, 14), (35, 20), (35, 34), (5, 34)])
    p.rect((255, 245, 245), 5, 25, 30, 3)
    p.poligono((255, 150, 190), [(5, 20), (30, 14), (35, 20)])
    p.rect((255, 150, 190), 5, 18, 30, 4)
    for x in (9, 16, 23, 30):
        p.circulo((255, 150, 190), x, 22, 1.6)
    p.poligono((225, 180, 120), [(30, 14), (35, 20), (35, 34), (30, 34)])
    p.linha((90, 140, 60), (21, 12), (25, 5), 1.5)
    p.circulo((220, 30, 50), 21, 13, 3.5)
    p.circulo((255, 140, 150), 20, 12, 1)


def _pimenta(p):
    pts = []
    for i in range(12):
        f = i / 11
        pts.append((14 + f * 14 + math.sin(f * 3) * 3, 12 + f * 24 - f * f * 4))
    lado = [(q[0] + 7 * (1 - i / 11) ** 0.7, q[1] - 2 * (1 - i / 11)) for i, q in enumerate(pts)]
    corpo = [(q[0] - 3.5 * (1 - i / 11) ** 0.7, q[1]) for i, q in enumerate(pts)]
    p.poligono((225, 35, 35), corpo + lado[::-1])
    p.linha((255, 130, 120), (15, 15), (18, 24), 1.5)
    p.poligono((70, 160, 60), [(11, 12), (22, 10), (19, 14)])
    p.linha((70, 160, 60), (16, 11), (14, 4), 2)


def _morango(p):
    p.circulo((220, 40, 60), 14, 19, 8)
    p.circulo((220, 40, 60), 26, 19, 8)
    p.poligono((220, 40, 60), [(6.5, 21), (33.5, 21), (20, 37)])
    for x, y in ((13, 20), (20, 18), (27, 20), (16, 26), (24, 26), (20, 31), (11, 16), (29, 16)):
        p.elipse((255, 225, 90), x, y, 1.6, 2.2)
    p.poligono((70, 170, 60), [(11, 12), (20, 9), (29, 12), (24, 15), (20, 13), (16, 15)])
    p.linha((70, 170, 60), (20, 10), (21, 4), 2)


def _marshmallow(p):
    p.rect((250, 222, 232), 10, 14, 20, 18)
    p.elipse((250, 222, 232), 10, 27, 20, 9)
    p.elipse((255, 240, 245), 10, 9, 20, 10)
    p.elipse((230, 190, 150), 13, 11, 8, 4)
    p.linha((255, 255, 255), (13, 18), (13, 29), 1.5)


def _limao(p):
    raio = max(2, round(12 * p.k))
    sup = ui.limao_sup(raio)
    p.s.blit(sup, sup.get_rect(center=p.p(20, 21)))


def _abobora(p):
    p.elipse((230, 120, 30), 4, 14, 18, 22)
    p.elipse((230, 120, 30), 18, 14, 18, 22)
    p.elipse((255, 150, 40), 11, 13, 18, 24)
    p.arco((200, 95, 20), 11, 13, 18, 24, 1.9, 4.4, 1.2)
    p.arco((200, 95, 20), 11, 13, 18, 24, -1.2, 1.2, 1.2)
    p.rect((110, 150, 60), 18, 7, 4, 8, raio=1)
    p.elipse((255, 200, 120), 14, 17, 5, 7)


_DESENHOS = {
    "maca": _maca, "banana": _banana, "leite": _leite, "pao_queijo": _pao_queijo,
    "suco_limao": _suco, "sanduiche": _sanduiche, "sorvete": _sorvete, "pizza": _pizza,
    "bolo": _bolo, "pimenta": _pimenta, "morango": _morango, "marshmallow": _marshmallow,
    "limao": _limao, "abobora": _abobora,
}

_comidas_cache = {}


def icone_comida(comida_id, tamanho):
    """Surface `tamanho` x `tamanho` com a comida (em cache)."""
    tamanho = max(8, int(tamanho))
    chave = (comida_id, tamanho)
    s = _comidas_cache.get(chave)
    if s is not None:
        return s
    desenho = _DESENHOS.get(comida_id)
    grande = tamanho * 2
    base = pygame.Surface((grande, grande), pygame.SRCALPHA)
    if desenho:
        desenho(_Pincel(base, grande / 40))
        base = _contornar(base, CONTORNO, max(2, grande // 36))
    s = _preparar(pygame.transform.smoothscale(base, (tamanho, tamanho)), rle=True)
    if len(_comidas_cache) > 300:
        _comidas_cache.clear()
    _comidas_cache[chave] = s
    return s


def desenhar_comida(tela, comida_id, centro, tamanho):
    """Desenha o ícone da comida (~tamanho px) centrado em `centro`."""
    s = icone_comida(comida_id, tamanho)
    tela.blit(s, s.get_rect(center=(int(centro[0]), int(centro[1]))))


# ============================================================
# PLANTAS (4 estágios)
# ============================================================
# Sprite 110x150 com a base (chão) no ponto (55, 142).

LARG_PLANTA, ALT_PLANTA = 110, 150
BASE_PLANTA = (55, 142)

VERDE = (70, 170, 70)
VERDE_CLARO = (110, 205, 90)
VERDE_ESCURO = (35, 110, 45)
CAULE = (60, 140, 55)


def _folha(s, base, ang, comp, larg, cor=VERDE, veia=True):
    """Folha em gota a partir de `base`, ângulo em graus (0 = pra cima)."""
    a = math.radians(ang)
    dx, dy = math.sin(a), -math.cos(a)
    nx, ny = -dy, dx
    bx, by = base

    def p(f, w):
        return (bx + dx * comp * f + nx * w, by + dy * comp * f + ny * w)

    pts = [(bx, by), p(0.3, larg * 0.7), p(0.6, larg), p(0.85, larg * 0.6), p(1, 0),
           p(0.85, -larg * 0.6), p(0.6, -larg), p(0.3, -larg * 0.7)]
    pygame.draw.polygon(s, cor, pts)
    pygame.draw.polygon(s, VERDE_ESCURO, pts, 1)
    if veia:
        pygame.draw.line(s, VERDE_ESCURO, (bx, by), p(0.85, 0), 1)


def _broto(s, cor_folha=VERDE_CLARO):
    bx, by = BASE_PLANTA
    pygame.draw.line(s, CAULE, (bx, by), (bx, by - 14), 3)
    _folha(s, (bx, by - 12), -60, 14, 5, cor_folha)
    _folha(s, (bx, by - 12), 60, 14, 5, cor_folha)
    pygame.draw.ellipse(s, (95, 60, 30), (bx - 9, by - 3, 18, 6))


def _muda(s, cor_folha=VERDE):
    bx, by = BASE_PLANTA
    pygame.draw.line(s, CAULE, (bx, by), (bx, by - 34), 3)
    _folha(s, (bx, by - 14), -65, 18, 6, cor_folha)
    _folha(s, (bx, by - 20), 60, 20, 6, cor_folha)
    _folha(s, (bx, by - 30), -35, 16, 5, VERDE_CLARO)
    _folha(s, (bx, by - 33), 30, 16, 5, VERDE_CLARO)
    pygame.draw.ellipse(s, (95, 60, 30), (bx - 11, by - 3, 22, 6))


def _arbusto(s, raio=30, cy_off=38):
    bx, by = BASE_PLANTA
    pygame.draw.line(s, (110, 80, 40), (bx, by), (bx, by - cy_off), 5)
    cy = by - cy_off - 6
    for dx, dy, r in ((-18, 6, raio * 0.7), (18, 6, raio * 0.7), (0, -8, raio * 0.8),
                      (-10, -2, raio * 0.7), (10, -2, raio * 0.7)):
        pygame.draw.circle(s, VERDE_ESCURO, (bx + dx, cy + dy), int(r) + 2)
    for dx, dy, r in ((-18, 6, raio * 0.7), (18, 6, raio * 0.7), (0, -8, raio * 0.8),
                      (-10, -2, raio * 0.7), (10, -2, raio * 0.7)):
        pygame.draw.circle(s, VERDE, (bx + dx, cy + dy), int(r))
    for dx, dy in ((-12, -8), (8, -16), (16, 2), (-20, 4)):
        pygame.draw.circle(s, VERDE_CLARO, (bx + dx, cy + dy), 5)
    return cy


def _limoeiro(s, estagio):
    bx = BASE_PLANTA[0]
    if estagio == 2:
        _arbusto(s, 24, 30)
        return
    cy = _arbusto(s, 30, 38)
    for dx, dy in ((-16, 4), (14, -6), (0, 14)):
        ui.limao(s, (bx + dx, cy + dy), 7, -15 if dx < 0 else 10)


def _morangueiro(s, estagio):
    bx, by = BASE_PLANTA
    for ang, comp in ((-70, 30), (70, 30), (-40, 36), (40, 36), (-10, 40), (15, 38)):
        a = math.radians(ang)
        ponta = (bx + math.sin(a) * comp * 0.8, by - math.cos(a) * comp * 0.8)
        pygame.draw.line(s, CAULE, (bx, by), ponta, 2)
        for d in (-22, 0, 22):
            _folha(s, ponta, ang + d, 12, 5, VERDE if d else VERDE_CLARO, False)
    if estagio == 2:
        for dx, dy in ((-20, -24), (18, -30), (2, -40)):
            pygame.draw.circle(s, (255, 255, 250), (bx + dx, by + dy), 4)
            pygame.draw.circle(s, (255, 220, 60), (bx + dx, by + dy), 1)
        return
    for dx, dy in ((-24, -8), (22, -10), (-6, -4), (10, -20)):
        x, y = bx + dx, by + dy
        pygame.draw.polygon(s, (220, 40, 60), [(x - 6, y - 3), (x + 6, y - 3), (x, y + 8)])
        pygame.draw.circle(s, (220, 40, 60), (x - 3, y - 3), 4)
        pygame.draw.circle(s, (220, 40, 60), (x + 3, y - 3), 4)
        for sx, sy in ((-2, -2), (2, 0), (0, 3)):
            pygame.draw.circle(s, (255, 225, 90), (x + sx, y + sy), 1)
        pygame.draw.polygon(s, (60, 150, 50), [(x - 5, y - 6), (x, y - 9), (x + 5, y - 6), (x, y - 4)])


def _girassol(s, estagio):
    bx, by = BASE_PLANTA
    altura = 80 if estagio == 2 else 104
    topo = (bx - 4, by - altura)
    pygame.draw.line(s, CAULE, (bx, by), (bx - 2, by - altura * 0.5), 4)
    pygame.draw.line(s, CAULE, (bx - 2, by - altura * 0.5), topo, 4)
    _folha(s, (bx, by - 26), -70, 26, 9)
    _folha(s, (bx - 1, by - 46), 70, 24, 8)
    if estagio == 2:
        pygame.draw.circle(s, (70, 150, 60), topo, 9)
        for i in range(6):
            a = i / 6 * math.tau
            _folha(s, topo, math.degrees(a), 12, 4, VERDE_CLARO, False)
        pygame.draw.circle(s, (60, 130, 50), topo, 7)
        return
    # Flor: pétalas + miolo (olhando um pouco para a esquerda, onde está o sol)
    cx, cy = topo
    for i in range(14):
        a = i / 14 * math.tau
        ponta = (cx + math.cos(a) * 24, cy + math.sin(a) * 22)
        lado1 = (cx + math.cos(a + 0.22) * 11, cy + math.sin(a + 0.22) * 10)
        lado2 = (cx + math.cos(a - 0.22) * 11, cy + math.sin(a - 0.22) * 10)
        pygame.draw.polygon(s, (255, 205, 40), [lado1, ponta, lado2])
        pygame.draw.polygon(s, (215, 150, 20), [lado1, ponta, lado2], 1)
    pygame.draw.circle(s, (120, 70, 30), (cx - 1, cy), 12)
    pygame.draw.circle(s, (90, 50, 20), (cx - 1, cy), 12, 2)
    for i in range(8):
        a = i / 8 * math.tau
        pygame.draw.circle(s, (160, 105, 50), (int(cx - 1 + math.cos(a) * 6),
                                               int(cy + math.sin(a) * 6)), 1)
    # Carinha feliz
    pygame.draw.circle(s, (30, 20, 10), (cx - 5, cy - 2), 1)
    pygame.draw.circle(s, (30, 20, 10), (cx + 3, cy - 2), 1)
    pygame.draw.arc(s, (30, 20, 10), (cx - 6, cy - 2, 10, 7), math.pi + 0.3, 2 * math.pi - 0.3, 1)


def _abobora_planta(s, estagio):
    bx, by = BASE_PLANTA
    # Rama rasteira com folhas grandes
    pygame.draw.lines(s, CAULE, False, [(bx - 44, by - 2), (bx - 20, by - 8), (bx, by - 4),
                                        (bx + 26, by - 10), (bx + 46, by - 3)], 3)
    for x, ang in ((-34, -30), (-8, 20), (20, -20), (40, 35)):
        _folha(s, (bx + x, by - 6), ang, 22, 10)
    pygame.draw.arc(s, CAULE, (bx + 30, by - 30, 14, 14), 0, 4, 2)
    if estagio == 2:
        r = pygame.Rect(0, 0, 22, 16)
        r.midbottom = (bx + 4, by)
        pygame.draw.ellipse(s, (130, 190, 70), r)
        pygame.draw.ellipse(s, (70, 130, 40), r, 1)
        return
    # ABÓBORA GIGANTE
    cx, base = bx, by
    for dx, larg, cor in ((-18, 40, (230, 120, 30)), (18, 40, (230, 120, 30)),
                          (0, 44, (255, 150, 40))):
        r = pygame.Rect(0, 0, larg, 44)
        r.midbottom = (cx + dx, base)
        pygame.draw.ellipse(s, cor, r)
        pygame.draw.ellipse(s, (170, 80, 15), r, 1)
    pygame.draw.ellipse(s, (255, 200, 120), (cx - 12, base - 36, 8, 14))
    pygame.draw.rect(s, (110, 150, 60), (cx - 3, base - 52, 7, 10), border_radius=2)
    pygame.draw.rect(s, (70, 100, 40), (cx - 3, base - 52, 7, 10), 1, border_radius=2)


def _arvore_moedas(s, estagio, seca=False):
    bx, by = BASE_PLANTA
    tronco = (130, 90, 50) if not seca else (120, 95, 70)
    if estagio == 2:
        pygame.draw.line(s, tronco, (bx, by), (bx, by - 50), 5)
        cy = by - 58
        for dx, dy, r in ((-12, 4, 14), (12, 4, 14), (0, -8, 16)):
            pygame.draw.circle(s, VERDE_ESCURO, (bx + dx, cy + dy), r + 2)
        for dx, dy, r in ((-12, 4, 14), (12, 4, 14), (0, -8, 16)):
            pygame.draw.circle(s, (80, 175, 90), (bx + dx, cy + dy), r)
        pygame.draw.circle(s, (255, 210, 60), (bx + 4, cy - 10), 3)
        return
    pygame.draw.polygon(s, tronco, [(bx - 6, by), (bx + 6, by), (bx + 4, by - 60), (bx - 4, by - 60)])
    pygame.draw.line(s, tronco, (bx, by - 50), (bx - 22, by - 72), 4)
    pygame.draw.line(s, tronco, (bx, by - 56), (bx + 20, by - 80), 4)
    pygame.draw.polygon(s, ui.escurecer(tronco, 50),
                        [(bx - 6, by), (bx + 6, by), (bx + 4, by - 60), (bx - 4, by - 60)], 1)
    if seca:
        for x0, y0, x1, y1 in ((-22, -72, -34, -84), (20, -80, 32, -96), (0, -60, 4, -92)):
            pygame.draw.line(s, tronco, (bx + x0, by + y0), (bx + x1, by + y1), 3)
        for dx, dy in ((-30, -86), (30, -92), (4, -94)):
            pygame.draw.ellipse(s, (170, 130, 70), (bx + dx - 4, by + dy - 2, 8, 5))
        return
    cy = by - 92
    blocos = ((-24, 14, 22), (24, 12, 22), (0, -6, 28), (-14, 0, 20), (14, -2, 20))
    for dx, dy, r in blocos:
        pygame.draw.circle(s, (35, 110, 60), (bx + dx, cy + dy), r + 2)
    for dx, dy, r in blocos:
        pygame.draw.circle(s, (70, 170, 90), (bx + dx, cy + dy), r)
    for dx, dy in ((-18, -4), (10, -20), (26, 6), (-26, 12)):
        pygame.draw.circle(s, (120, 210, 120), (bx + dx, cy + dy), 5)


# Posições (relativas à base) das moedas penduradas na árvore
_MOEDAS_ARVORE = [(-26, -82), (22, -84), (0, -108), (-12, -94), (14, -66)]

_PLANTAS = {
    "semente_limao": _limoeiro,
    "semente_morango": _morangueiro,
    "semente_girassol": _girassol,
    "semente_abobora": _abobora_planta,
    "semente_moedas": _arvore_moedas,
}

_plantas_cache = {}
_brilho_cache = {}


def _sprite_planta(semente_id, estagio, seca=False):
    chave = (semente_id, estagio, seca)
    s = _plantas_cache.get(chave)
    if s is None:
        s = pygame.Surface((LARG_PLANTA, ALT_PLANTA), pygame.SRCALPHA)
        folha = VERDE_CLARO if semente_id != "semente_moedas" else (150, 215, 110)
        if estagio <= 0:
            _broto(s, folha)
        elif estagio == 1:
            _muda(s)
        elif semente_id == "semente_moedas":
            _arvore_moedas(s, estagio, seca)
        else:
            _PLANTAS[semente_id](s, estagio)
        s = _preparar(s, rle=True)
        _plantas_cache[chave] = s
    return s


def _girado(semente_id, estagio, seca, passo):
    """Sprite girado em `passo` graus em volta da base (cache)."""
    chave = (semente_id, estagio, seca, passo)
    s = _plantas_cache.get(chave)
    if s is None:
        base = _sprite_planta(semente_id, estagio, seca)
        # Gira em volta do ponto da base: coloca a base no centro de
        # uma Surface maior, gira, e guarda o deslocamento.
        grande = pygame.Surface((LARG_PLANTA * 2, ALT_PLANTA * 2), pygame.SRCALPHA)
        grande.blit(base, (LARG_PLANTA - BASE_PLANTA[0], ALT_PLANTA - BASE_PLANTA[1]))
        s = pygame.transform.rotate(grande, passo)
        s = _preparar(s, rle=True)
        _plantas_cache[chave] = s
    return s


def _brilho(raio):
    s = _brilho_cache.get(raio)
    if s is None:
        s = pygame.Surface((raio * 2, raio * 2), pygame.SRCALPHA)
        for i in range(8):
            r = int(raio * (1 - i / 8))
            pygame.draw.circle(s, (255, 240, 150, int(14 + i * 10)), (raio, raio), r)
        s = _preparar(s)
        _brilho_cache[raio] = s
    return s


def desenhar_planta(tela, semente_id, estagio, base, t, colheitas_restantes=None):
    """
    Planta do canteiro. `estagio` 0..3 (broto, muda, planta, pronta);
    `base` = (x, y) do chão no meio do canteiro. Estágio 3 brilha e
    mostra um "!" dourado. A árvore de OVOEDAS seca quando
    `colheitas_restantes` chega a 0.
    """
    if semente_id not in SEMENTES:
        return
    estagio = max(0, min(3, int(estagio)))
    bx, by = int(base[0]), int(base[1])
    seca = semente_id == "semente_moedas" and colheitas_restantes is not None \
        and colheitas_restantes <= 0
    pronta = estagio == 3 and not seca

    if pronta:
        pulso = (math.sin(t * 3) + 1) / 2
        raio = 46
        g = _brilho(raio)
        g.set_alpha(int(150 + 100 * pulso))
        cy = by - (60 if semente_id != "semente_abobora" else 22)
        tela.blit(g, (bx - raio, cy - raio))

    # Balanço suave (em passos de 1 grau para usar o cache)
    if estagio == 0 or semente_id == "semente_abobora":
        passo = 0
    else:
        amp = 2.5 if estagio < 3 else 2.0
        passo = int(round(amp * math.sin(t * 1.6 + bx * 0.05)))
    if passo:
        s = _girado(semente_id, estagio, seca, passo)
        tela.blit(s, s.get_rect(center=(bx, by)))
    else:
        s = _sprite_planta(semente_id, estagio, seca)
        tela.blit(s, (bx - BASE_PLANTA[0], by - BASE_PLANTA[1]))

    # Moedas girando na árvore de OVOEDAS pronta
    if pronta and semente_id == "semente_moedas":
        qtd = 5 if colheitas_restantes is None else max(1, min(5, colheitas_restantes))
        ang = math.radians(passo)
        for i, (dx, dy) in enumerate(_MOEDAS_ARVORE[:qtd]):
            x = bx + dx * math.cos(ang) + dy * math.sin(ang)
            y = by - dx * math.sin(ang) + dy * math.cos(ang)
            giro = math.cos(t * 3 + i * 1.3)
            ui.moeda(tela, (x, y + math.sin(t * 2 + i) * 1.5), 7, giro=max(0.15, abs(giro)))

    if pronta:
        topo = {"semente_limao": 96, "semente_morango": 70, "semente_girassol": 146,
                "semente_abobora": 76, "semente_moedas": 138}[semente_id]
        y = by - topo + math.sin(t * 4) * 3
        pygame.draw.circle(tela, (120, 70, 10), (bx, int(y)), 11)
        pygame.draw.circle(tela, (255, 210, 50), (bx, int(y)), 9)
        ui.desenhar_texto(tela, "!", (bx + 1, int(y) + 1), 12, (120, 60, 0), "center", sombra=False)
        # Faíscas
        for i in range(3):
            fase = (t * 0.9 + i / 3) % 1
            a = i * 2.1 + t * 0.5
            px = bx + math.cos(a) * 30
            py = by - 50 - fase * 40
            ui.estrela(tela, (int(px), int(py)), int(1 + 3 * math.sin(fase * math.pi)),
                       (255, 250, 200))


# ============================================================
# ÍCONE DO PACOTINHO DE SEMENTES
# ============================================================

_pacotes = {}


def icone_semente(semente_id, tamanho):
    """Pacotinho de sementes com a planta pronta desenhada."""
    tamanho = max(12, int(tamanho))
    chave = (semente_id, tamanho)
    s = _pacotes.get(chave)
    if s is not None:
        return s

    info = SEMENTES.get(semente_id, {})
    cor = info.get("cor", (200, 200, 200))
    G = 120                      # desenha grande e reduz no fim
    base = pygame.Surface((G, G), pygame.SRCALPHA)
    pacote = pygame.Rect(20, 14, 80, 100)
    pygame.draw.rect(base, cor, pacote, border_radius=6)
    pygame.draw.rect(base, ui.escurecer(cor, 25), (pacote.right - 16, pacote.y, 16, pacote.h),
                     border_top_right_radius=6, border_bottom_right_radius=6)
    # Borda de cima dentada (fechada)
    dentes = [(pacote.x, 22)]
    for i in range(9):
        x = pacote.x + (i + 0.5) * pacote.w / 9
        dentes.append((x, 10))
        dentes.append((pacote.x + (i + 1) * pacote.w / 9, 18))
    dentes += [(pacote.right, 26), (pacote.x, 26)]
    pygame.draw.polygon(base, ui.clarear(cor, 40), dentes)
    pygame.draw.line(base, ui.escurecer(cor, 60), (pacote.x + 2, 26), (pacote.right - 2, 26), 2)
    # Janelinha branca com a planta pronta
    janela = pygame.Rect(30, 32, 60, 58)
    pygame.draw.rect(base, (250, 250, 240), janela, border_radius=8)
    pygame.draw.rect(base, (120, 190, 240), (janela.x, janela.y, janela.w, 30),
                     border_top_left_radius=8, border_top_right_radius=8)
    pygame.draw.rect(base, (130, 90, 50), (janela.x, janela.bottom - 12, janela.w, 12),
                     border_bottom_left_radius=8, border_bottom_right_radius=8)
    planta = _sprite_planta(semente_id, 3) if semente_id in SEMENTES else None
    if planta:
        box = planta.get_bounding_rect()
        recorte = planta.subsurface(box)
        esc = min((janela.w - 8) / box.w, (janela.h - 8) / box.h)
        img = pygame.transform.smoothscale(recorte, (max(1, int(box.w * esc)),
                                                     max(1, int(box.h * esc))))
        base.blit(img, img.get_rect(midbottom=(janela.centerx, janela.bottom - 4)))
        if semente_id == "semente_moedas":
            ui.moeda(base, (janela.centerx - 12, janela.y + 18), 7)
            ui.moeda(base, (janela.centerx + 12, janela.y + 22), 7)
    pygame.draw.rect(base, ui.escurecer(cor, 70), janela, 2, border_radius=8)
    # Sementinhas embaixo
    for i, x in enumerate(range(36, 88, 10)):
        pygame.draw.ellipse(base, (110, 75, 40), (x, 97 + (i % 2) * 4, 7, 5))
    pygame.draw.rect(base, ui.escurecer(cor, 80), pacote, 2, border_radius=6)
    base = _contornar(base, CONTORNO, 3)

    s = _preparar(pygame.transform.smoothscale(base, (tamanho, tamanho)))
    if len(_pacotes) > 100:
        _pacotes.clear()
    _pacotes[chave] = s
    return s
