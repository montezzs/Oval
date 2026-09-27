import math

import pygame

from core import cosmeticos as c
from core.ui import escurecer

# ============================================================
# COSMÉTICOS NOVOS (coleção "Vizinhança")
# ============================================================
# Registrados no catálogo de core/cosmeticos.py quando este módulo
# é importado (o próprio cosmeticos.py importa no final). Mesmas
# regras de desenho: quadro 100x100, corpo do ovo (15,14,67,74).

_item = c._item
_forma = c._forma
_linha = c._linha

NOVOS = {
    # ---------------- CABEÇA ----------------
    "chapeu_palha": _item("CHAPÉU DE PALHA", "cabeca", 65, "COMUM", ("frente",), True),
    "capacete_obra": _item("CAPACETE DE OBRA", "cabeca", 90, "COMUM", ("frente",), True),
    "fones": _item("FONES DE OUVIDO", "cabeca", 260, "INCOMUM", ("frente",), esconde={0}),
    "touca_dino": _item("TOUCA DE DINOSSAURO", "cabeca", 480, "RARO", ("frente",), True),
    "ninho_cabeca": _item("NINHO COM PASSARINHO", "cabeca", 950, "EPICO", ("frente",), True),
    # ---------------- ROSTO ----------------
    "sardas": _item("SARDAS", "rosto", 40, "COMUM", ("frente",)),
    "oculos_3d": _item("ÓCULOS 3D", "rosto", 60, "COMUM", ("frente",)),
    "monoculo": _item("MONÓCULO", "rosto", 180, "INCOMUM", ("frente",)),
    # ---------------- CORPO ----------------
    "avental": _item("AVENTAL DE JARDIM", "corpo", 70, "COMUM", ("corpo",)),
    "mochila": _item("MOCHILA", "corpo", 140, "INCOMUM", ("atras", "frente")),
    "capa_chuva": _item("CAPA DE CHUVA", "corpo", 220, "INCOMUM", ("atras", "frente")),
    "mochila_foguete": _item("MOCHILA-FOGUETE", "corpo", 1100, "EPICO", ("atras",)),
    # ---------------- EFEITOS ----------------
    "aura_bolhas": _item("BOLHAS DE SABÃO", "efeito", 280, "INCOMUM", ()),
    "vagalumes": _item("VAGALUMES", "efeito", 420, "RARO", ()),
    "aura_arco_iris": _item("ARCO-ÍRIS", "efeito", 1900, "LENDARIO", ()),
}


# ============================================================
# CABEÇA
# ============================================================

def _chapeu_palha(sup, ovo):
    palha, borda = (235, 200, 110), (170, 130, 60)
    sup.blit(_forma(c._elipse((12, 14, 74, 13)), palha, borda), (0, 0))

    def trancado(s):
        for x in range(24, 80, 5):
            pygame.draw.line(s, (205, 165, 80), (x, 0), (x - 10, 20), 1)
        s.fill((220, 70, 60), (28, 11, 42, 5))

    sup.blit(_forma(lambda s, cor: pygame.draw.rect(s, cor, (28, 1, 42, 17), border_radius=7),
                    palha, borda, detalhes=trancado), (0, 0))
    pygame.draw.line(sup, (250, 225, 150), (18, 18), (40, 16), 1)


def _capacete_obra(sup, ovo):
    amarelo, escuro = (255, 200, 30), (180, 130, 10)

    def cupula(s, cor):
        pygame.draw.ellipse(s, cor, (24, 2, 50, 36))
        c._apagar_abaixo(s, 20)

    def ressalto(s):
        s.fill((235, 175, 20), (44, 2, 10, 18))
        pygame.draw.arc(s, (255, 235, 140), (30, 6, 36, 26), math.radians(110),
                        math.radians(160), 2)

    sup.blit(_forma(cupula, amarelo, escuro, detalhes=ressalto), (0, 0))
    sup.blit(_forma(lambda s, cor: pygame.draw.rect(s, cor, (18, 16, 62, 7), border_radius=3),
                    amarelo, escuro), (0, 0))


def _fones(sup, ovo):
    pygame.draw.arc(sup, (40, 40, 50), (13, 3, 72, 58), math.radians(15), math.radians(165), 7)
    pygame.draw.arc(sup, (80, 80, 95), (14, 4, 70, 56), math.radians(20), math.radians(160), 4)
    for x, dentro in ((9, 20), (77, 76)):
        sup.blit(_forma(lambda s, cor, x=x: pygame.draw.rect(s, cor, (x, 24, 13, 24), border_radius=5),
                        (230, 70, 90), (150, 30, 50)), (0, 0))
        pygame.draw.rect(sup, (40, 40, 50), (dentro, 27, 3, 18), border_radius=1)
        pygame.draw.line(sup, (255, 150, 170), (x + 3, 28), (x + 3, 36), 1)


def _touca_dino(sup, ovo):
    verde, barra = (110, 200, 90), (80, 165, 65)
    # espinhos atrás da touca
    for x in (30, 40, 58, 68):
        cy = 22 - 20 * math.sqrt(max(0.0, 1 - ((x - 49) / 31) ** 2))
        pygame.draw.polygon(sup, (200, 140, 20), [(x - 5, cy + 3), (x + 5, cy + 3), (x, cy - 6)])
        pygame.draw.polygon(sup, (255, 200, 60), [(x - 3, cy + 2), (x + 3, cy + 2), (x, cy - 4)])

    def cupula(s, cor):
        pygame.draw.ellipse(s, cor, (18, 2, 62, 42))
        c._apagar_abaixo(s, 24)

    sup.blit(_forma(cupula, verde, (50, 120, 40)), (0, 0))
    sup.blit(_forma(lambda s, cor: pygame.draw.rect(s, cor, (17, 20, 64, 7), border_radius=3),
                    barra, (50, 120, 40)), (0, 0))
    for x in range(22, 78, 7):
        pygame.draw.polygon(sup, (255, 255, 255), [(x, 26), (x + 4, 26), (x + 2, 30)])
    for x in (38, 60):
        pygame.draw.circle(sup, (255, 255, 255), (x, 12), 4)
        pygame.draw.circle(sup, (30, 30, 30), (x + 1, 12), 2)


def _ninho_cabeca(sup, ovo):
    marrom, escuro, claro = (150, 105, 60), (110, 70, 35), (190, 145, 85)
    sup.blit(_forma(c._elipse((24, 8, 50, 16)), marrom, escuro), (0, 0))
    for i in range(12):
        x = 27 + i * 4
        pygame.draw.arc(sup, escuro if i % 2 else claro, (x - 4, 10 + (i % 3), 10, 10),
                        math.radians(200), math.radians(340), 1)
    # passarinho
    azul = (90, 160, 240)
    pygame.draw.circle(sup, (40, 90, 170), (49, 8), 8)
    pygame.draw.circle(sup, azul, (49, 8), 7)
    pygame.draw.circle(sup, (40, 90, 170), (56, 3), 5)
    pygame.draw.circle(sup, azul, (56, 3), 4)
    pygame.draw.polygon(sup, (255, 170, 40), [(59, 2), (64, 4), (59, 5)])
    sup.fill((20, 20, 20), (57, 2, 2, 2))
    pygame.draw.ellipse(sup, (60, 120, 210), (42, 6, 9, 5))


# ============================================================
# ROSTO
# ============================================================

def _sardas(sup, ovo):
    cor = (180, 110, 70)
    for x, y in ((22, 48), (27, 51), (23, 54), (75, 48), (70, 51), (74, 54)):
        pygame.draw.circle(sup, cor, (x, y), 1)
        sup.fill(cor, (x, y, 2, 2))


def _oculos_3d(sup, ovo):
    borda = c._branco(ovo, (150, 150, 160), (110, 110, 125))
    for x, lente in ((20, (230, 50, 60, 170)), (51, (50, 170, 230, 170))):
        vidro = pygame.Surface((27, 15), pygame.SRCALPHA)
        vidro.fill(lente)
        sup.blit(vidro, (x, 28))
        pygame.draw.rect(sup, (250, 250, 250), (x, 28, 27, 15), 3)
        pygame.draw.rect(sup, borda, (x - 1, 27, 29, 17), 1)
    pygame.draw.line(sup, (250, 250, 250), (47, 32), (51, 32), 3)
    pygame.draw.line(sup, borda, (47, 30), (51, 30), 1)


def _monoculo(sup, ovo):
    lente = pygame.Surface((20, 20), pygame.SRCALPHA)
    pygame.draw.circle(lente, (220, 240, 255, 80), (10, 10), 9)
    sup.blit(lente, (53, 25))
    pygame.draw.circle(sup, (160, 120, 30), (63, 35), 11, 1)
    pygame.draw.circle(sup, (220, 180, 60), (63, 35), 10, 3)
    pygame.draw.line(sup, (255, 250, 220), (58, 30), (61, 28), 1)
    for i in range(7):
        f = i / 6
        x = 72 + 8 * f
        y = 44 + 26 * f - 6 * math.sin(f * math.pi)
        sup.fill((220, 180, 60), (round(x), round(y), 2, 2))


# ============================================================
# CORPO
# ============================================================

def _avental(sup, ovo):
    verde, escuro = (110, 170, 90), (70, 120, 55)
    pygame.draw.line(sup, escuro, (33, 76), (22, 60), 2)
    pygame.draw.line(sup, escuro, (65, 76), (76, 60), 2)

    def bolso(s):
        s.fill((90, 140, 70), (40, 83, 18, 8))
        pygame.draw.line(s, (150, 100, 60), (54, 77), (55, 85), 2)

    sup.blit(_forma(c._poligono([(31, 76), (67, 76), (71, 94), (27, 94)]), verde, escuro,
                    detalhes=bolso), (0, 0))
    c._recortar_ovo(sup)


def _mochila_atras(sup, ovo):
    laranja, tampa = (240, 140, 60), (210, 110, 40)

    def detalhes(s):
        s.fill(tampa, (60, 40, 34, 14))
        pygame.draw.rect(s, (255, 214, 64), (74, 50, 6, 5))

    sup.blit(_forma(lambda s, cor: pygame.draw.rect(s, cor, (60, 40, 34, 46), border_radius=9),
                    laranja, (160, 80, 25), detalhes=detalhes), (0, 0))


def _mochila_frente(sup, ovo):
    pygame.draw.line(sup, (160, 80, 25), (77, 50), (70, 86), 5)
    pygame.draw.line(sup, (200, 100, 30), (77, 50), (70, 86), 3)


def _capa_chuva_atras(sup, ovo):
    sup.blit(_forma(c._elipse((10, 2, 78, 54)), (255, 220, 40), (200, 160, 20)), (0, 0))


def _capa_chuva_frente(sup, ovo):
    # Gola embaixo da boca (a capa em si fica atrás do ovo)
    pygame.draw.rect(sup, (255, 220, 40), (28, 80, 42, 8), border_radius=3)
    pygame.draw.rect(sup, (200, 160, 20), (28, 80, 42, 8), 2, border_radius=3)
    pygame.draw.circle(sup, (200, 150, 20), (49, 84), 2)


def _mochila_foguete(sup, ovo):
    for x in (3, 81):
        def tubo(s, cor, x=x):
            pygame.draw.rect(s, cor, (x, 36, 16, 42), border_radius=7)

        def faixa(s, x=x):
            s.fill((220, 50, 60), (x, 52, 16, 6))
            pygame.draw.line(s, (255, 255, 255), (x + 4, 40), (x + 4, 48), 2)

        sup.blit(_forma(tubo, (200, 205, 220), (120, 125, 140), detalhes=faixa), (0, 0))
        pygame.draw.rect(sup, (90, 90, 100), (x + 2, 77, 12, 7), border_radius=2)
        pygame.draw.polygon(sup, (255, 160, 40), [(x + 1, 84), (x + 15, 84), (x + 8, 99)])
        pygame.draw.polygon(sup, (255, 240, 120), [(x + 5, 84), (x + 11, 84), (x + 8, 93)])


# ============================================================
# EFEITOS ANIMADOS
# ============================================================

def _bolha_sprite(r):
    lado = r * 2 + 4
    sup = pygame.Surface((lado, lado), pygame.SRCALPHA)
    pygame.draw.circle(sup, (180, 220, 255, 60), (lado // 2, lado // 2), r)
    pygame.draw.circle(sup, (180, 220, 255, 210), (lado // 2, lado // 2), r, max(1, r // 5))
    pygame.draw.circle(sup, (255, 255, 255), (lado // 2 - r // 3, lado // 2 - r // 3), max(1, r // 4))
    return sup


def _aura_bolhas(tela, cx, cy, h, t, fase):
    if fase != "frente":
        return
    for i in range(5):
        p = (t / 3 + i / 5) % 1
        r = max(2, round((0.05 + 0.01 * (i % 5)) * h))
        x = cx + (-0.45 + 0.22 * i) * h + math.sin(t * 2 + i) * 0.1 * h
        y = cy + 0.3 * h - 1.2 * h * p
        if p > 0.92:
            # estourou: pontinhos
            for k in range(4):
                a = k * math.pi / 2 + 0.6
                tela.fill((210, 235, 255), (round(x + math.cos(a) * r), round(y + math.sin(a) * r), 2, 2))
            continue
        sup = c._sprite(("bolha", r), lambda: _bolha_sprite(r))
        c._blit_centro(tela, sup, (x, y), 255 * min(1.0, p * 6))


def _vagalume_sprite(r, noite=False):
    lado = r * 6 + 2
    sup = pygame.Surface((lado, lado), pygame.SRCALPHA)
    pygame.draw.circle(sup, (230, 255, 120, 60), (lado // 2, lado // 2), r * 3)
    pygame.draw.circle(sup, (230, 255, 120, 110), (lado // 2, lado // 2), r * 2)
    pygame.draw.circle(sup, (250, 255, 190), (lado // 2, lado // 2), r)
    return sup


def _vagalumes(tela, cx, cy, h, t, fase):
    if fase != "frente":
        return
    r = max(1, round(0.025 * h))
    sup = c._sprite(("vagalume", r), lambda: _vagalume_sprite(r))
    for i in range(6):
        a = t * (0.5 + 0.1 * i) + i * 1.1
        x = cx + math.sin(a * 1.3 + i) * 0.6 * h
        y = cy - 0.1 * h + math.sin(a * 0.9 + i * 2) * 0.45 * h
        brilho = max(0.0, math.sin(3 * t + i))
        if brilho > 0.05:
            c._blit_centro(tela, sup, (x, y), 255 * brilho)


_CORES_ARCO = [(255, 90, 90), (255, 180, 60), (255, 230, 70), (100, 210, 110), (90, 160, 255),
               (170, 110, 240)]


def _arco_sprite(h):
    raio_ext = round(0.74 * h)
    faixa = max(2, round(0.02 * h))
    lado_w = raio_ext * 2 + 4
    lado_h = raio_ext + 4
    sup = pygame.Surface((lado_w, lado_h), pygame.SRCALPHA)
    cx, cy = lado_w // 2, raio_ext + 2
    for k, cor in enumerate(_CORES_ARCO):
        r = raio_ext - k * faixa
        pygame.draw.circle(sup, cor, (cx, cy), r, faixa + 1, draw_top_left=True, draw_top_right=True)
    for dx in (-raio_ext + faixa * 3, raio_ext - faixa * 3):
        for ox, oy, rr in ((-5, 0, 6), (0, -3, 7), (6, 0, 6)):
            k = h / 74
            pygame.draw.circle(sup, (250, 250, 255), (cx + dx + ox * k, cy - 4 * k + oy * k), rr * k)
    return sup


def _aura_arco_iris(tela, cx, cy, h, t, fase):
    if fase != "atras":
        return
    sup = c._sprite(("arco", round(h)), lambda: _arco_sprite(h))
    alpha = 190 + 30 * math.sin(t * 2)
    c._blit_centro(tela, sup, (cx, cy - 0.2 * h - sup.get_height() / 2 + 4), alpha)


# ============================================================
# REGISTRO
# ============================================================

DESENHOS = {
    ("chapeu_palha", "frente"): _chapeu_palha,
    ("capacete_obra", "frente"): _capacete_obra,
    ("fones", "frente"): _fones,
    ("touca_dino", "frente"): _touca_dino,
    ("ninho_cabeca", "frente"): _ninho_cabeca,
    ("sardas", "frente"): _sardas,
    ("oculos_3d", "frente"): _oculos_3d,
    ("monoculo", "frente"): _monoculo,
    ("avental", "corpo"): _avental,
    ("mochila", "atras"): _mochila_atras,
    ("mochila", "frente"): _mochila_frente,
    ("capa_chuva", "atras"): _capa_chuva_atras,
    ("capa_chuva", "frente"): _capa_chuva_frente,
    ("mochila_foguete", "atras"): _mochila_foguete,
}

EFEITOS = {
    "aura_bolhas": _aura_bolhas,
    "vagalumes": _vagalumes,
    "aura_arco_iris": _aura_arco_iris,
}

ICONES_EFEITO = {
    "aura_bolhas": (0.46, 0.60, 0.80, 0.62, (0.3, 1.3, 2.2)),
    "vagalumes": (0.46, 0.56, 0.80, 0.56, (0.5, 1.4, 2.6)),
    "aura_arco_iris": (0.46, 0.66, 0.70, 0.66, (0.8,)),
}

c.CATALOGO.update(NOVOS)
c._DESENHOS.update(DESENHOS)
c.EFEITOS = tuple(c.EFEITOS) + tuple(EFEITOS)
c.EFEITOS_EXTRA.update(EFEITOS)
c._ICONE_EFEITO.update(ICONES_EFEITO)
