import math
import random

import pygame

from settings import *
from core import ui
from core.idioma import t, t as _t
from core.itens import COMIDAS, icone_comida
from jogos.base import MiniJogo

# ============================================================
# OVO COZINHEIRO
# ============================================================
# O seu ovo botou o chapéu de chef! O LIVRO DE RECEITAS mostra
# um prato e os ingredientes NA ORDEM. Pegue cada um nos 8 potes
# da bancada (clique ou teclas 1-8) e jogue na panela. Depois
# MEXA a panela (gire o mouse em volta dela ou alterne ← →) até
# a barra encher e SIRVA. Ingrediente errado? A panela solta
# fumaça preta e a receita perde tempo. Se o tempo da receita
# acabar, ela QUEIMA. A partida dura 90 segundos.
#
# Cada receita concluída entra na COLEÇÃO DE RECEITAS do ovo
# (core/progresso.colecionar).

# ------------------------------------------------------------
# RECEITAS (ids de ingredientes = core/itens.COMIDAS)
# ------------------------------------------------------------
RECEITAS = [
    # 2 ingredientes
    dict(id="super_limonada", nome="SUPER LIMONADA", ingredientes=["limao", "suco_limao"]),
    dict(id="banana_split", nome="BANANA SPLIT", ingredientes=["banana", "sorvete"]),
    dict(id="maca_do_amor", nome="MAÇÃ DO AMOR", ingredientes=["maca", "marshmallow"]),
    dict(id="pao_queijo_picante", nome="PÃO DE QUEIJO PICANTE",
         ingredientes=["pao_queijo", "pimenta"]),
    # 3 ingredientes
    dict(id="vitamina_morango", nome="VITAMINA DE MORANGO",
         ingredientes=["leite", "morango", "banana"]),
    dict(id="pizza_limao", nome="PIZZA DE LIMÃO", ingredientes=["pizza", "limao", "pimenta"]),
    dict(id="sorvete_nuvem", nome="SORVETE NUVEM",
         ingredientes=["sorvete", "marshmallow", "morango"]),
    dict(id="torta_maca", nome="TORTA DE MAÇÃ", ingredientes=["maca", "leite", "pao_queijo"]),
    dict(id="suco_arco_iris", nome="SUCO ARCO-ÍRIS",
         ingredientes=["suco_limao", "morango", "banana"]),
    dict(id="sopa_abobora", nome="SOPA DE ABÓBORA", ingredientes=["abobora", "leite", "pimenta"]),
    # 4 ingredientes
    dict(id="sanduiche_turbo", nome="SANDUÍCHE TURBO",
         ingredientes=["pao_queijo", "sanduiche", "pimenta", "limao"]),
    dict(id="bolo_abobora", nome="BOLO DE ABÓBORA",
         ingredientes=["leite", "abobora", "bolo", "marshmallow"]),
    dict(id="milkshake_polar", nome="MILK-SHAKE POLAR",
         ingredientes=["leite", "sorvete", "banana", "morango"]),
    dict(id="salada_frutas", nome="SALADA DE FRUTAS",
         ingredientes=["maca", "banana", "morango", "limao"]),
    dict(id="pizza_doce", nome="PIZZA DOCE",
         ingredientes=["pizza", "marshmallow", "morango", "banana"]),
    # 5 ingredientes
    dict(id="bolo_festa", nome="BOLO DE FESTA",
         ingredientes=["leite", "bolo", "morango", "marshmallow", "sorvete"]),
    dict(id="lanche_do_rei", nome="LANCHE DO REI",
         ingredientes=["pizza", "sanduiche", "bolo", "suco_limao", "abobora"]),
    dict(id="pizza_vulcao", nome="PIZZA VULCÃO",
         ingredientes=["pizza", "pimenta", "abobora", "pao_queijo", "limao"]),
    dict(id="sobremesa_maluca", nome="SOBREMESA MALUCA",
         ingredientes=["sorvete", "pimenta", "bolo", "limao", "marshmallow"]),
]
_RECEITA = {r["id"]: r for r in RECEITAS}

INGREDIENTES = ["limao", "maca", "banana", "leite", "pao_queijo", "suco_limao", "sanduiche",
                "sorvete", "pizza", "bolo", "pimenta", "morango", "marshmallow", "abobora"]
NOMES_CURTOS = {"abobora": "ABÓBORA", "pao_queijo": "PÃO QUEIJO", "suco_limao": "SUCO"}


def _nome(ing):
    return t(NOMES_CURTOS.get(ing) or COMIDAS.get(ing, {}).get("nome", ing.upper()))


# ------------------------------------------------------------
# REGRAS
# ------------------------------------------------------------
TEMPO_PARTIDA = 90.0
N_POTES = 8

# Por dificuldade (FÁCIL, NORMAL, CHEF)
TAMANHOS = [(2, 3), (3, 4), (4, 5)]         # nº de ingredientes das receitas
TEMPO_RECEITA = [20.0, 15.0, 13.0]
VOLTAS = [1.5, 2.0, 2.5]                    # voltas de colher para ficar pronto
PENA_ERRO = [2.0, 3.0, 3.5]                 # segundos perdidos por ingrediente errado
DICA_APOS = [0.0, 4.0, None]                # pote certo brilha depois de X s parado
EMBARALHAR = [False, False, True]           # CHEF: os potes trocam todos a cada receita
META = [800, 1000, 1200]
MULT_PONTOS = [0.8, 1.0, 1.25]             # CHEF vale mais

BLOQUEIO_ERRO = 0.35
TEMPO_ENTREGA = 0.75
TEMPO_QUEIMOU = 1.2

# ------------------------------------------------------------
# CENÁRIO
# ------------------------------------------------------------
LIVRO = pygame.Rect(22, 74, 404, 322)
PANELA = (640, 318)                         # centro da boca da panela
BOCA_W, BOCA_H = 300, 90
LIQ_W, LIQ_H = 268, 70
FUNDO_PANELA = 444
BANCADA_Y = 470
CHEF = (906, 330)
ALT_CHEF = 96
BARRA_MEXER = pygame.Rect(510, 184, 260, 24)
POTE_W, POTE_H = 94, 112
POTES_X = [70 + i * 126 for i in range(N_POTES)]
POTE_TOPO = 540
ENTREGA = (910, 452)
ICONE_LIVRO = 58

TAMPAS = [(230, 80, 80), (250, 160, 50), (240, 210, 60), (110, 200, 90),
          (70, 180, 220), (110, 120, 230), (180, 110, 220), (240, 120, 180)]

TECLAS_POTE = {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2, pygame.K_4: 3, pygame.K_5: 4,
               pygame.K_6: 5, pygame.K_7: 6, pygame.K_8: 7,
               pygame.K_KP1: 0, pygame.K_KP2: 1, pygame.K_KP3: 2, pygame.K_KP4: 3,
               pygame.K_KP5: 4, pygame.K_KP6: 5, pygame.K_KP7: 6, pygame.K_KP8: 7}
TECLAS_ESQ = (pygame.K_LEFT, pygame.K_a)
TECLAS_DIR = (pygame.K_RIGHT, pygame.K_d)
TECLAS_SERVIR = (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER)

AGUA = (120, 180, 225)
PAPEL = (252, 244, 222)
TINTA = (90, 55, 35)


def _formatar_tempo(seg):
    seg = max(0, int(math.ceil(seg)))
    return f"{seg // 60}:{seg % 60:02d}"


# ============================================================
# SPRITES (tudo em cache)
# ============================================================

_cache = {}


def _girado(ing, tam, ang):
    """Ícone da comida girado (passos de 15°, em cache)."""
    passo = int(round(ang / 15)) % 24
    chave = ("gir", ing, tam, passo)
    s = _cache.get(chave)
    if s is None:
        s = pygame.transform.rotate(icone_comida(ing, tam), passo * 15)
        _cache[chave] = s
    return s


def _fumaca(raio, preta, alfa):
    """Bolinha de vapor (branca) ou fumaça (preta) semitransparente."""
    raio = max(4, int(raio) // 2 * 2)
    nivel = max(1, min(8, int(alfa * 8 + 0.5)))
    chave = ("fum", raio, preta, nivel)
    s = _cache.get(chave)
    if s is None:
        s = pygame.Surface((raio * 2, raio * 2), pygame.SRCALPHA)
        cor = (45, 42, 48) if preta else (250, 250, 255)
        a = int((200 if preta else 120) * nivel / 8)
        pygame.draw.circle(s, (*cor, a), (raio, raio), raio)
        pygame.draw.circle(s, (*ui.clarear(cor, 30), min(255, a + 20)),
                           (int(raio * 0.75), int(raio * 0.7)), max(2, raio // 3))
        _cache[chave] = s
    return s


def _pote(indice):
    """Pote de vidro com tampa colorida (sem o ingrediente)."""
    chave = ("pote", indice)
    s = _cache.get(chave)
    if s is not None:
        return s
    s = pygame.Surface((POTE_W + 8, POTE_H + 8), pygame.SRCALPHA)
    tampa = TAMPAS[indice % len(TAMPAS)]
    corpo = pygame.Rect(4, 22, POTE_W, POTE_H - 20)
    # Sombra no balcão
    pygame.draw.ellipse(s, (0, 0, 0, 70), (6, POTE_H - 6, POTE_W - 4, 14))
    # Vidro
    pygame.draw.rect(s, (60, 80, 90), corpo.inflate(4, 4), border_radius=22)
    pygame.draw.rect(s, (205, 232, 240), corpo, border_radius=20)
    pygame.draw.rect(s, (225, 245, 250), corpo.inflate(-14, -14), border_radius=16)
    # Tampa
    t = pygame.Rect(0, 0, POTE_W - 10, 22)
    t.midtop = (corpo.centerx, 6)
    pygame.draw.rect(s, ui.escurecer(tampa, 70), t.inflate(4, 4), border_radius=8)
    pygame.draw.rect(s, tampa, t, border_radius=7)
    pygame.draw.rect(s, ui.clarear(tampa, 50), (t.x + 6, t.y + 3, t.w - 12, 5), border_radius=3)
    for x in range(t.x + 10, t.right - 6, 10):
        pygame.draw.line(s, ui.escurecer(tampa, 30), (x, t.y + 10), (x, t.bottom - 3), 2)
    _cache[chave] = s
    return s


def _brilho_pote():
    """Reflexo do vidro (vai por cima do ingrediente)."""
    s = _cache.get("brilho")
    if s is None:
        s = pygame.Surface((POTE_W + 8, POTE_H + 8), pygame.SRCALPHA)
        pygame.draw.rect(s, (255, 255, 255, 110), (14, 34, 10, POTE_H - 50), border_radius=5)
        pygame.draw.rect(s, (255, 255, 255, 80), (28, 34, 5, 30), border_radius=3)
        _cache["brilho"] = s
    return s


def _panela():
    """Panela grande de metal (sem o caldo)."""
    s = _cache.get("panela")
    if s is not None:
        return s
    w, h = BOCA_W + 110, FUNDO_PANELA - PANELA[1] + 70
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    cx, top = w // 2, 30                      # centro da boca = (cx, top + BOCA_H/2 - ...)
    cy = top + 10                             # PANELA fica em (cx, cy) dentro do sprite
    fundo = cy + (FUNDO_PANELA - PANELA[1])
    metal, escuro, claro = (150, 160, 175), (85, 92, 108), (205, 212, 225)
    # Alças
    for lado in (-1, 1):
        ax = cx + lado * (BOCA_W // 2 + 22)
        pygame.draw.rect(s, (40, 30, 30), (ax - 26, cy + 18, 52, 22), border_radius=11)
        pygame.draw.rect(s, (70, 50, 45), (ax - 24, cy + 20, 48, 16), border_radius=8)
    # Corpo
    corpo = [(cx - BOCA_W // 2, cy), (cx + BOCA_W // 2, cy),
             (cx + BOCA_W // 2 - 14, fundo), (cx - BOCA_W // 2 + 14, fundo)]
    pygame.draw.polygon(s, metal, corpo)
    pygame.draw.ellipse(s, metal, (cx - BOCA_W // 2 + 14, fundo - 22, BOCA_W - 28, 44))
    pygame.draw.polygon(s, escuro, [(cx + BOCA_W // 2 - 60, cy), (cx + BOCA_W // 2, cy),
                                    (cx + BOCA_W // 2 - 14, fundo), (cx + BOCA_W // 2 - 70, fundo + 18)])
    pygame.draw.polygon(s, claro, [(cx - BOCA_W // 2 + 30, cy + 20), (cx - BOCA_W // 2 + 50, cy + 20),
                                   (cx - BOCA_W // 2 + 58, fundo), (cx - BOCA_W // 2 + 40, fundo)])
    pygame.draw.line(s, escuro, (cx - BOCA_W // 2 + 10, cy + 60), (cx + BOCA_W // 2 - 10, cy + 60), 3)
    pygame.draw.arc(s, (60, 64, 78), (cx - BOCA_W // 2 + 14, fundo - 22, BOCA_W - 28, 44),
                    math.pi, math.tau, 4)
    # Boca (aro + interior escuro)
    boca = pygame.Rect(0, 0, BOCA_W, BOCA_H)
    boca.center = (cx, cy)
    pygame.draw.ellipse(s, (60, 64, 78), boca.inflate(10, 8))
    pygame.draw.ellipse(s, claro, boca.inflate(4, 2))
    pygame.draw.ellipse(s, (45, 48, 58), boca.inflate(-10, -10))
    _cache["panela"] = (s, (cx, cy))
    return _cache["panela"]


def _chapeu(largura):
    """Chapéu de chef (larg x ~1.05 larg)."""
    largura = int(largura)
    chave = ("chapeu", largura)
    s = _cache.get(chave)
    if s is not None:
        return s
    w, h = largura, int(largura * 1.0)
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    k = w / 100
    contorno = (70, 70, 90)
    bolas = [(26, 42, 24), (50, 30, 28), (74, 42, 24), (38, 26, 18), (62, 26, 18)]
    for x, y, r in bolas:
        pygame.draw.circle(s, contorno, (int(x * k), int(y * k)), int((r + 3) * k))
    faixa = pygame.Rect(int(18 * k), int(52 * k), int(64 * k), int(40 * k))
    pygame.draw.rect(s, contorno, faixa.inflate(int(6 * k), int(6 * k)), border_radius=int(8 * k))
    for x, y, r in bolas:
        pygame.draw.circle(s, (250, 250, 252), (int(x * k), int(y * k)), int(r * k))
    pygame.draw.rect(s, (250, 250, 252), faixa, border_radius=int(6 * k))
    pygame.draw.rect(s, (215, 218, 230), (faixa.x, faixa.bottom - int(12 * k), faixa.w, int(12 * k)),
                     border_radius=int(6 * k))
    for x in (34, 50, 66):
        pygame.draw.line(s, (215, 218, 230), (int(x * k), int(58 * k)), (int(x * k), int(80 * k)),
                         max(1, int(2 * k)))
    pygame.draw.circle(s, BRANCO, (int(40 * k), int(22 * k)), int(6 * k))
    _cache[chave] = s
    return s


def _chapeu_girado(largura, ang):
    passo = int(round(ang / 2))
    chave = ("chapeu_g", int(largura), passo)
    s = _cache.get(chave)
    if s is None:
        s = pygame.transform.rotate(_chapeu(largura), passo * 2)
        if len(_cache) > 900:
            _cache.clear()
        _cache[chave] = s
    return s


def _prato(receita_id):
    """Tigela com o prato pronto (cores e ingredientes da receita)."""
    chave = ("prato", receita_id)
    s = _cache.get(chave)
    if s is not None:
        return s
    ings = _RECEITA[receita_id]["ingredientes"]
    w, h = 130, 100
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    cor = _cor_caldo(ings)
    pygame.draw.ellipse(s, (0, 0, 0, 70), (12, 78, 106, 18))
    # Tigela
    pygame.draw.ellipse(s, (60, 60, 80), (8, 36, 114, 58))
    pygame.draw.ellipse(s, (245, 245, 250), (11, 38, 108, 52))
    pygame.draw.rect(s, (0, 0, 0, 0), (0, 0, w, 58))
    pygame.draw.ellipse(s, (60, 60, 80), (6, 30, 118, 34))
    pygame.draw.ellipse(s, (235, 238, 245), (9, 32, 112, 29))
    pygame.draw.ellipse(s, cor, (16, 36, 98, 21))
    pygame.draw.ellipse(s, ui.clarear(cor, 40), (30, 38, 40, 8))
    # Os ingredientes por cima
    for k, ing in enumerate(ings[:3]):
        ic = icone_comida(ing, 40)
        x = 26 + k * 30
        s.blit(ic, ic.get_rect(center=(x + 10, 30 - (k % 2) * 8)))
    pygame.draw.rect(s, (230, 70, 70), (46, 72, 38, 7), border_radius=3)   # faixinha na tigela
    _cache[chave] = s
    return s


def _cor_caldo(ings):
    if not ings:
        return AGUA
    r = g = b = 0
    for ing in ings:
        c = COMIDAS.get(ing, {}).get("cor", (200, 160, 100))
        r, g, b = r + c[0], g + c[1], b + c[2]
    n = len(ings)
    return ui.escurecer((int(r / n), int(g / n), int(b / n)), 15)


def _veu_icone():
    s = _cache.get("veu_icone")
    if s is None:
        s = pygame.Surface((ICONE_LIVRO + 8, ICONE_LIVRO + 8), pygame.SRCALPHA)
        pygame.draw.rect(s, (*PAPEL, 150), s.get_rect(), border_radius=10)
        _cache["veu_icone"] = s
    return s


# ============================================================
# O JOGO
# ============================================================

class OvoCozinheiro(MiniJogo):

    ID = "ovo_cozinheiro"
    TITULO = "OVO COZINHEIRO"
    TITULO_CURTO = "COZINHEIRO"
    DESCRICAO = "Siga o livro de receitas: ingredientes na ordem certa, mexa a panela e sirva!"
    COR = (215, 110, 60)
    INSTRUCOES = [
        "Siga o LIVRO DE RECEITAS: pegue os ingredientes NA ORDEM.",
        "Clique no pote ou aperte 1 a 8.",
        "Depois MEXA: gire o mouse em volta da panela ou alterne ← →.",
        "Barra cheia? CLIQUE ou ESPAÇO para servir!",
        "Errou o ingrediente? Fumaça preta e menos tempo!",
    ]
    OPCOES = ["FÁCIL", "NORMAL", "CHEF"]
    ROTULO_PONTOS = "PONTOS"
    CONTAGEM = True

    MOEDAS_POR = 40             # NORMAL bem jogado ~1200 pontos -> ~30 moedas
    MOEDAS_MAX = 40
    MOEDAS_MIN = 1

    # --------------------------------------------------------
    # CENÁRIO: cozinha com azulejos, janela e trilho de utensílios
    # --------------------------------------------------------

    @classmethod
    def criar_fundo(cls, jogador):
        sup = pygame.Surface((LARGURA, ALTURA))
        rnd = random.Random(21)

        # Parede: papel de parede com bolinhas em cima, azulejos embaixo
        sup.blit(ui.gradiente(LARGURA, 220, (255, 226, 190), (250, 212, 170)), (0, 0))
        for y in range(18, 220, 36):
            for x in range(18 + (y // 36 % 2) * 18, LARGURA, 36):
                pygame.draw.circle(sup, (245, 196, 150), (x, y), 4)
        azulejo = 44
        for y in range(220, BANCADA_Y, azulejo):
            for x in range(0, LARGURA, azulejo):
                par = (x // azulejo + y // azulejo) % 2
                cor = (240, 248, 250) if par else (200, 230, 238)
                pygame.draw.rect(sup, cor, (x, y, azulejo, azulejo))
                pygame.draw.rect(sup, (170, 200, 210), (x, y, azulejo, azulejo), 1)
        pygame.draw.rect(sup, (200, 120, 80), (0, 214, LARGURA, 8))

        # Janela (atrás do chef)
        jan = pygame.Rect(800, 76, 190, 120)
        pygame.draw.rect(sup, (120, 80, 50), jan.inflate(16, 16), border_radius=6)
        sup.blit(ui.gradiente(jan.w, jan.h, (120, 200, 255), (190, 235, 255)), jan)
        for x, y, r in ((840, 120, 14), (858, 112, 18), (878, 120, 14), (950, 150, 10), (962, 146, 13)):
            pygame.draw.circle(sup, BRANCO, (x, y), r)
        pygame.draw.circle(sup, (255, 230, 90), (960, 100), 16)
        pygame.draw.line(sup, (120, 80, 50), (jan.centerx, jan.y), (jan.centerx, jan.bottom), 6)
        pygame.draw.line(sup, (120, 80, 50), (jan.x, jan.centery), (jan.right, jan.centery), 6)
        for x in range(jan.x - 8, jan.right + 8, 24):          # cortininha
            pygame.draw.circle(sup, (230, 90, 90), (x + 12, jan.y - 4), 12)
            pygame.draw.circle(sup, (250, 250, 250), (x + 12, jan.y - 4), 5)

        # Trilho com utensílios pendurados
        pygame.draw.line(sup, (120, 120, 135), (470, 84), (790, 84), 6)
        for x, tipo in ((500, "concha"), (560, "espatula"), (720, "batedor"), (770, "concha")):
            pygame.draw.line(sup, (90, 90, 100), (x, 84), (x, 96), 3)
            if tipo == "concha":
                pygame.draw.line(sup, (150, 155, 170), (x, 96), (x, 146), 6)
                pygame.draw.circle(sup, (150, 155, 170), (x, 154), 14)
                pygame.draw.circle(sup, (110, 115, 130), (x, 152), 9)
            elif tipo == "espatula":
                pygame.draw.line(sup, (140, 90, 50), (x, 96), (x, 136), 7)
                pygame.draw.rect(sup, (170, 175, 190), (x - 13, 134, 26, 30), border_radius=4)
                for dx in (-6, 0, 6):
                    pygame.draw.line(sup, (120, 125, 140), (x + dx, 140), (x + dx, 158), 2)
            else:
                pygame.draw.line(sup, (140, 90, 50), (x, 96), (x, 122), 7)
                for dx in (-12, -5, 5, 12):
                    pygame.draw.arc(sup, (170, 175, 190), (x - abs(dx), 116, abs(dx) * 2, 56), math.pi,
                                    math.tau, 2)
                    pygame.draw.line(sup, (170, 175, 190), (x - abs(dx), 144), (x + abs(dx), 144), 1)

        # Livro de receitas (cartão com espiral)
        l = LIVRO
        pygame.draw.rect(sup, (0, 0, 0), l.move(6, 7), border_radius=14)
        pygame.draw.rect(sup, (150, 60, 40), l.inflate(12, 12), border_radius=16)
        pygame.draw.rect(sup, PAPEL, l, border_radius=12)
        for y in range(l.y + 96, l.bottom - 20, 22):
            pygame.draw.line(sup, (225, 210, 190), (l.x + 12, y), (l.right - 12, y), 1)
        pygame.draw.line(sup, (240, 170, 170), (l.x + 30, l.y + 44), (l.x + 30, l.bottom - 8), 2)
        pygame.draw.rect(sup, (205, 80, 60), (l.x, l.y, l.w, 40), border_top_left_radius=12,
                         border_top_right_radius=12)
        pygame.draw.rect(sup, (230, 110, 80), (l.x, l.y, l.w, 10), border_top_left_radius=12,
                         border_top_right_radius=12)
        for x in range(l.x + 26, l.right - 10, 34):
            pygame.draw.circle(sup, (60, 50, 50), (x, l.y - 2), 7)
            pygame.draw.circle(sup, (200, 200, 210), (x, l.y - 2), 7, 3)
        ui.desenhar_texto(sup, t("LIVRO DE RECEITAS"), (l.centerx, l.y + 22), 12, BRANCO, "center")

        # Bancada: tampo de mármore + armário de madeira
        pygame.draw.rect(sup, (230, 230, 236), (0, BANCADA_Y, LARGURA, 34))
        for _ in range(40):
            x, y = rnd.randrange(LARGURA), rnd.randrange(BANCADA_Y + 4, BANCADA_Y + 30)
            pygame.draw.line(sup, (205, 205, 215), (x, y), (x + rnd.randint(10, 40), y + rnd.randint(-3, 3)), 1)
        pygame.draw.rect(sup, (250, 250, 255), (0, BANCADA_Y, LARGURA, 4))
        pygame.draw.rect(sup, (160, 100, 60), (0, BANCADA_Y + 34, LARGURA, ALTURA - BANCADA_Y - 34))
        for x in range(0, LARGURA, 128):
            pygame.draw.rect(sup, (140, 85, 50), (x + 6, BANCADA_Y + 44, 116, ALTURA - BANCADA_Y - 54),
                             3, border_radius=6)
        pygame.draw.rect(sup, (120, 70, 40), (0, BANCADA_Y + 34, LARGURA, 6))
        # Prateleira dos potes
        pygame.draw.rect(sup, (110, 65, 38), (0, POTE_TOPO + POTE_H - 4, LARGURA, 16))
        pygame.draw.rect(sup, (185, 125, 80), (0, POTE_TOPO + POTE_H - 4, LARGURA, 4))

        # Fogão: boca do fogão embaixo da panela
        pygame.draw.ellipse(sup, (40, 40, 48), (PANELA[0] - 130, BANCADA_Y - 10, 260, 34))
        pygame.draw.ellipse(sup, (70, 70, 80), (PANELA[0] - 110, BANCADA_Y - 6, 220, 24), 4)

        # Plaquinha de entrega (onde o prato vai)
        pygame.draw.ellipse(sup, (200, 200, 210), (ENTREGA[0] - 64, ENTREGA[1] + 6, 128, 26))
        pygame.draw.ellipse(sup, (245, 245, 250), (ENTREGA[0] - 60, ENTREGA[1] + 4, 120, 22))
        ui.desenhar_texto(sup, t("ENTREGA"), (ENTREGA[0], ENTREGA[1] + 44), 8, (120, 70, 40), "center",
                          sombra=False)
        return sup

    @classmethod
    def desenhar_icone(cls, sup, jogador):
        w, h = sup.get_size()
        k = h / ALTURA
        # Panela e ingredientes voando
        pan, _ = _panela()
        pw, ph = pan.get_size()
        img = pygame.transform.smoothscale(pan, (int(pw * k * 1.3), int(ph * k * 1.3)))
        sup.blit(img, img.get_rect(center=(w * 0.42, h * 0.62)))
        for i, ing in enumerate(("morango", "banana", "leite")):
            ic = icone_comida(ing, max(12, int(h * 0.2)))
            sup.blit(ic, ic.get_rect(center=(w * (0.28 + i * 0.14), h * (0.28 + (i % 2) * 0.08))))
        corpo = jogador.desenhar(sup, (int(w * 0.78), int(h * 0.62)), h * 0.34, espelhar=True)
        ch = _chapeu(corpo.w * 1.05)
        sup.blit(ch, ch.get_rect(midbottom=(corpo.centerx, corpo.top + corpo.h * 0.28)))

    # --------------------------------------------------------
    # PARTIDA
    # --------------------------------------------------------

    def reiniciar(self):
        self.tempo_restante = TEMPO_PARTIDA
        self.acabou = False
        self.t_fim = 0.0
        self.feitas = 0
        self.perfeitas = 0
        self.queimadas = 0
        self.erros = 0
        self.acoes = 0
        self.descobertas = []
        self.seq = 0                        # receitas seguidas sem queimar
        self.melhor_seq = 0
        self.numero = 0
        self.saco = []
        self.receita = None
        self.potes = random.sample(INGREDIENTES, N_POTES)
        self.pote_pop = [1.0] * N_POTES     # animação de reabastecer (0 -> 1)
        self.pote_aperto = [0.0] * N_POTES  # afundadinha ao clicar
        self.voando = []                    # ingredientes a caminho da panela
        self.expulsos = []                  # ingredientes errados cuspidos
        self.fumacas = []
        self.bolhas = []
        self.t_vapor = 0.0
        self.cor_caldo = list(AGUA)
        self.chef_pulo = 0.0
        self.chef_susto = 0.0
        self.aviso_nova = 0.0
        self.nome_pop = 0.0
        self.prato = None                   # [receita_id, t]
        self._nova_receita(primeira=True)

    def partida_valida(self):
        return self.acoes > 0

    def _pool(self):
        lo, hi = TAMANHOS[self.opcao]
        return [r for r in RECEITAS if lo <= len(r["ingredientes"]) <= hi]

    def _nova_receita(self, primeira=False):
        if not self.saco:
            self.saco = self._pool()
            random.shuffle(self.saco)
            if self.receita is not None and len(self.saco) > 1 and self.saco[-1] is self.receita:
                self.saco.insert(0, self.saco.pop())
        self.receita = self.saco.pop()
        self.numero += 1
        self.passo = 0
        self.fase = "montar"
        self.t_fase = 0.0
        self.t_total = TEMPO_RECEITA[self.opcao]
        self.t_receita = self.t_total
        self.erros_receita = 0
        self.parado = 0.0
        self.bloqueio = 0.0
        self.mexido = 0.0
        self.giro = 0.0
        self.t_mexeu = 9.0
        self.ultimo_ang = None
        self.sentido = 0.0
        self.ultima_seta = 0
        self.no_caldo = []
        self.cor_alvo = AGUA
        self.nome_pop = 0.0
        self._reabastecer(primeira)

    def _reabastecer(self, primeira=False):
        precisa = self.receita["ingredientes"]
        if EMBARALHAR[self.opcao] and not primeira:
            outros = [i for i in INGREDIENTES if i not in precisa]
            novos = list(precisa) + random.sample(outros, N_POTES - len(precisa))
            random.shuffle(novos)
            trocou = list(range(N_POTES))
            self.potes = novos
        else:
            faltam = [i for i in precisa if i not in self.potes]
            livres = [k for k in range(N_POTES) if self.potes[k] not in precisa]
            random.shuffle(livres)
            trocou = []
            for ing, k in zip(faltam, livres):
                self.potes[k] = ing
                trocou.append(k)
            # Um pote "enfeite" também muda, para a bancada não ficar parada
            livres = [k for k in livres if k not in trocou]
            fora = [i for i in INGREDIENTES if i not in self.potes]
            if livres and fora and not primeira and random.random() < 0.6:
                k = random.choice(livres)
                self.potes[k] = random.choice(fora)
                trocou.append(k)
        if primeira:
            return
        for k in trocou:
            self.pote_pop[k] = 0.0
            cx = POTES_X[k]
            self.particulas.explodir((cx, POTE_TOPO + 40), [BRANCO, (220, 240, 255)], 6, 120, 0.4,
                                     (3, 6), gravidade=-60)
        if trocou:
            self.som("revelar", 0.4)

    # --------------------------------------------------------
    # CONTROLES
    # --------------------------------------------------------

    def evento_jogo(self, e):
        if self.acabou:
            return
        if e.type == pygame.KEYDOWN:
            if e.key in TECLAS_POTE:
                self._escolher(TECLAS_POTE[e.key])
            elif e.key in TECLAS_ESQ:
                self._mexer_tecla(-1)
            elif e.key in TECLAS_DIR:
                self._mexer_tecla(1)
            elif e.key in TECLAS_SERVIR:
                self._servir()
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self.fase == "montar":
                k = self._pote_em(e.pos)
                if k is not None:
                    self._escolher(k)
            elif self.fase == "servir":
                self._servir()
        elif e.type == pygame.MOUSEMOTION:
            if self.fase == "mexer":
                self._mexer_mouse(e.pos)

    def _pote_em(self, pos):
        x, y = pos
        for k, px in enumerate(POTES_X):
            if abs(x - px) <= POTE_W // 2 + 12 and POTE_TOPO - 6 <= y <= POTE_TOPO + POTE_H + 14:
                return k
        return None

    def _escolher(self, k):
        if self.fase != "montar":
            if self.fase == "mexer":
                self.textos.adicionar(t("MEXA A PANELA!"), (PANELA[0], PANELA[1] - 150), BRANCO, 12)
            return
        if self.bloqueio > 0 or self.pote_pop[k] < 0.6:
            return
        self.acoes += 1
        self.pote_aperto[k] = 1.0
        ing = self.potes[k]
        certo = self.receita["ingredientes"][self.passo]
        origem = (POTES_X[k], POTE_TOPO + 50)
        if ing == certo:
            self.passo += 1
            self.parado = 0.0
            self.voando.append(dict(ing=ing, x0=origem[0], y0=origem[1], t=0.0, dur=0.32,
                                    errado=False, ang=random.uniform(-40, 40)))
            self.som("pulo", 0.5)
            if self.passo >= len(self.receita["ingredientes"]):
                self.fase = "mexer"
                self.t_fase = 0.0
                self.ultimo_ang = None
        else:
            self.erros += 1
            self.erros_receita += 1
            pena = PENA_ERRO[self.opcao]
            self.t_receita -= pena
            self.bloqueio = BLOQUEIO_ERRO
            self.chef_susto = 0.8
            self.tremer(0.25)
            self.som("erro")
            self.voando.append(dict(ing=ing, x0=origem[0], y0=origem[1], t=0.0, dur=0.3,
                                    errado=True, ang=random.uniform(-40, 40)))
            self.textos.adicionar(t("ECA! -{n}s", n=f"{pena:g}"), (PANELA[0], PANELA[1] - 110), (255, 110, 100), 16)

    def _mexer_mouse(self, pos):
        dx = pos[0] - PANELA[0]
        dy = (pos[1] - PANELA[1] - 20) * 2.2       # a boca é achatada: corrige o círculo
        dist = math.hypot(dx, dy)
        if dist < 30 or dist > 520:
            self.ultimo_ang = None
            return
        a = math.atan2(dy, dx)
        if self.ultimo_ang is not None:
            d = (a - self.ultimo_ang + math.pi) % math.tau - math.pi
            if abs(d) < 1.4:
                sinal = 1 if d > 0 else -1
                if abs(self.sentido) < 0.3 or (self.sentido > 0) == (sinal > 0):
                    self._girar(abs(d), sinal)
                self.sentido = self.sentido * 0.85 + sinal * 0.15
        self.ultimo_ang = a

    def _mexer_tecla(self, direcao):
        if self.fase != "mexer":
            return
        if direcao == self.ultima_seta:
            self.giro += 0.15 * direcao
            return
        self.ultima_seta = direcao
        self._girar(math.tau / 4, 1)

    def _girar(self, rad, sinal):
        antes = int(self.giro / (math.pi / 2))
        self.giro += rad * sinal
        self.t_mexeu = 0.0
        self.acoes += 1
        self.mexido = min(1.0, self.mexido + rad / (VOLTAS[self.opcao] * math.tau))
        if int(self.giro / (math.pi / 2)) != antes:
            self.som("tic", 0.35)
            if random.random() < 0.7:
                self._bolha()
        if self.mexido >= 1.0:
            self.fase = "servir"
            self.t_fase = 0.0
            self.som("acerto")
            self.chef_pulo = 0.6
            self.particulas.explodir((PANELA[0], PANELA[1]), [AMARELO, BRANCO, ui.clarear(tuple(self.cor_alvo), 40)],
                                     26, 300, 0.7, (3, 7))

    def _servir(self):
        if self.fase != "servir":
            return
        n = len(self.receita["ingredientes"])
        base = 10 + 12 * n
        frac = max(0.0, self.t_receita / self.t_total)
        rapidez = int(base * 0.6 * frac)
        perfeita = 8 if self.erros_receita == 0 else 0
        self.seq += 1
        self.melhor_seq = max(self.melhor_seq, self.seq)
        sequencia = 3 * min(5, self.seq - 1)      # receitas seguidas sem queimar
        total = int(round((base + rapidez + perfeita + sequencia) * MULT_PONTOS[self.opcao]))
        self.pontos += total
        self.feitas += 1
        if perfeita:
            self.perfeitas += 1

        x, y = PANELA[0], PANELA[1] - 70
        self.textos.adicionar(f"+{total}", (x, y), AMARELO, 20)
        if rapidez >= base * 0.35:
            self.textos.adicionar(t("RAPIDINHO!"), (x - 110, y + 36), (140, 230, 255), 12)
        if perfeita:
            self.textos.adicionar(t("PERFEITA!"), (x + 110, y + 36), (150, 255, 150), 12)

        rid = self.receita["id"]
        if rid not in self.descobertas:
            self.descobertas.append(rid)
            self.aviso_nova = 1.8
            self.som("conquista", 0.8)
        else:
            self.som("moeda")
        try:
            from core import progresso
            progresso.colecionar(self.app, "receitas", rid)
        except Exception:
            pass

        self.prato = [rid, 0.0]
        self.chef_pulo = 0.8
        self.fase = "entrega"
        self.t_fase = 0.0
        self.no_caldo = []
        self.cor_alvo = AGUA
        self.particulas.explodir((PANELA[0], PANELA[1] - 10), [AMARELO, (255, 250, 200), BRANCO],
                                 20, 260, 0.6)

    def _queimar(self):
        self.fase = "queimou"
        self.t_fase = 0.0
        self.queimadas += 1
        self.seq = 0
        self.chef_susto = 1.2
        self.tremer(0.4)
        self.som("explosao", 0.8)
        self.textos.adicionar(t("QUEIMOU!"), (PANELA[0], PANELA[1] - 120), (255, 110, 90), 24)
        self.cor_alvo = (60, 45, 40)
        for _ in range(16):
            self._soltar_fumaca(True, forte=True)

    # --------------------------------------------------------
    # LÓGICA
    # --------------------------------------------------------

    def atualizar_jogo(self, dt):
        self.bloqueio = max(0.0, self.bloqueio - dt)
        self.chef_pulo = max(0.0, self.chef_pulo - dt)
        self.chef_susto = max(0.0, self.chef_susto - dt)
        self.aviso_nova = max(0.0, self.aviso_nova - dt)
        self.nome_pop = min(1.0, self.nome_pop + dt / 0.35)
        self.t_fase += dt
        self.t_mexeu += dt
        for k in range(N_POTES):
            self.pote_pop[k] = min(1.0, self.pote_pop[k] + dt / 0.35)
            self.pote_aperto[k] = max(0.0, self.pote_aperto[k] - dt / 0.18)

        # Caldo muda de cor aos poucos
        alvo = self.cor_alvo
        for i in range(3):
            self.cor_caldo[i] += (alvo[i] - self.cor_caldo[i]) * min(1.0, dt * 4)

        self._atualizar_voando(dt)
        self._atualizar_fumaca(dt)

        # Relógio da partida
        if not self.acabou:
            antes = self.tempo_restante
            self.tempo_restante = max(0.0, self.tempo_restante - dt)
            if self.tempo_restante <= 5 and int(antes) != int(self.tempo_restante):
                self.som("clique", 0.8)
            if self.tempo_restante <= 0:
                self.acabou = True
                self.t_fim = 0.0
                self.textos.adicionar(t("TEMPO!"), (LARGURA // 2, 250), AMARELO, 28)
                self.som("bandeira")
                return
        else:
            self.t_fim += dt
            if self.t_fim > 1.4:
                self._fim()
            return

        # Fases da receita
        if self.fase in ("montar", "mexer", "servir"):
            self.t_receita -= dt
            if self.fase == "montar":
                self.parado += dt
            if self.fase == "mexer" and self.t_mexeu > 0.6:
                self.mexido = max(0.0, self.mexido - dt * 0.08)
            if self.t_receita <= 0:
                self.t_receita = 0.0
                self._queimar()
        elif self.fase == "entrega":
            if self.prato:
                self.prato[1] += dt
            if self.t_fase >= TEMPO_ENTREGA:
                self.particulas.explodir(ENTREGA, [AMARELO, BRANCO, (255, 180, 120)], 16, 220, 0.6)
                self.som("ponto", 0.8)
                self.prato = None
                self._nova_receita()
        elif self.fase == "queimou":
            if random.random() < dt * 12:
                self._soltar_fumaca(True)
            if self.t_fase >= TEMPO_QUEIMOU:
                self._nova_receita()

        # Vapor saindo da panela
        self.t_vapor -= dt
        if self.t_vapor <= 0:
            intenso = self.fase in ("mexer", "servir")
            self.t_vapor = random.uniform(0.06, 0.1) if intenso else random.uniform(0.12, 0.2)
            self._soltar_fumaca(False)
        if random.random() < dt * (6 if self.fase in ("mexer", "servir") else 2.5):
            self._bolha()

    def _atualizar_voando(self, dt):
        vivos = []
        for v in self.voando:
            v["t"] += dt
            if v["t"] < v["dur"]:
                vivos.append(v)
                continue
            if v["errado"]:
                # Cai na panela, faz fumaça preta e é cuspido para fora
                for _ in range(7):
                    self._soltar_fumaca(True, forte=True)
                self.expulsos.append(dict(ing=v["ing"], x=PANELA[0], y=PANELA[1],
                                          vx=random.choice((-1, 1)) * random.uniform(160, 260),
                                          vy=-random.uniform(420, 520), ang=0.0,
                                          giro=random.uniform(-600, 600)))
                self.som("boing", 0.6)
            else:
                cor = COMIDAS.get(v["ing"], {}).get("cor", BRANCO)
                self.particulas.explodir((PANELA[0], PANELA[1] + 4), [cor, ui.clarear(cor, 60), (180, 220, 255)],
                                         14, 240, 0.5, (3, 6), 700)
                self.som("ponto", 0.5)
                if self.fase in ("montar", "mexer", "servir"):
                    self.no_caldo.append(v["ing"])
                    self.cor_alvo = _cor_caldo(self.no_caldo)
                self.tremer(0.05)
        self.voando = vivos

        for x in self.expulsos:
            x["vy"] += 1100 * dt
            x["x"] += x["vx"] * dt
            x["y"] += x["vy"] * dt
            x["ang"] += x["giro"] * dt
        self.expulsos = [x for x in self.expulsos if x["y"] < ALTURA + 60]

    def _soltar_fumaca(self, preta, forte=False):
        x = PANELA[0] + random.uniform(-LIQ_W * 0.38, LIQ_W * 0.38)
        y = PANELA[1] + random.uniform(-6, 10)
        vel = random.uniform(90, 160) if forte else random.uniform(40, 80)
        vida = random.uniform(1.0, 1.5) if preta else random.uniform(1.1, 1.7)
        self.fumacas.append([x, y, random.uniform(-25, 25) * (2 if forte else 1), -vel,
                             vida, vida, random.uniform(10, 16) if preta else random.uniform(8, 12), preta])
        if len(self.fumacas) > 120:
            del self.fumacas[:len(self.fumacas) - 120]

    def _bolha(self):
        self.bolhas.append([PANELA[0] + random.uniform(-LIQ_W * 0.36, LIQ_W * 0.36),
                            PANELA[1] + 4 + random.uniform(-LIQ_H * 0.22, LIQ_H * 0.25),
                            0.0, random.uniform(0.35, 0.6), random.randint(4, 8)])

    def _atualizar_fumaca(self, dt):
        vivas = []
        for f in self.fumacas:
            f[0] += f[2] * dt + math.sin(self.tempo * 2 + f[1] * 0.05) * 12 * dt
            f[1] += f[3] * dt
            f[3] *= (1 - 0.6 * dt)
            f[4] -= dt
            f[6] += dt * (22 if f[7] else 14)
            if f[4] > 0:
                vivas.append(f)
        self.fumacas = vivas
        for b in self.bolhas:
            b[2] += dt
        self.bolhas = [b for b in self.bolhas if b[2] < b[3]]

    def _fim(self):
        meta = META[self.opcao]
        venceu = self.pontos >= meta
        total = len(self._pool())
        linhas = [t("PONTOS: {n}  (META {meta})", n=self.pontos, meta=meta),
                  t("RECEITAS: {a}   PERFEITAS: {b}", a=self.feitas, b=self.perfeitas),
                  t("DESCOBERTAS: {a}/{b}", a=len(self.descobertas), b=total)]
        if self.queimadas:
            linhas.append(t("QUEIMADAS: {n}", n=self.queimadas))
        self.terminar(venceu=venceu, titulo=t("CHEF ESTRELADO!") if venceu else t("FIM DO EXPEDIENTE!"),
                      linhas=linhas)

    # --------------------------------------------------------
    # DESENHO
    # --------------------------------------------------------

    def desenhar_jogo(self, tela):
        tela.blit(self.fundo(self.jogador), (0, 0))
        self._desenhar_livro(tela)
        self._desenhar_fogo(tela)
        self._desenhar_panela(tela)
        self._desenhar_chef(tela)
        self._desenhar_prato(tela)
        self._desenhar_potes(tela)
        self._desenhar_voando(tela)
        self._desenhar_fumacas(tela)
        self._desenhar_mexer(tela)
        self.particulas.desenhar(tela)
        self.textos.desenhar(tela)
        self._desenhar_avisos(tela)

    # --- livro ---------------------------------------------

    def _desenhar_livro(self, tela):
        l = LIVRO
        r = self.receita
        ings = r["ingredientes"]
        ui.desenhar_texto(tela, t("RECEITA {n}", n=self.numero), (l.x + 42, l.y + 52), 8, (170, 110, 80),
                          "midleft", sombra=False)
        nova = r["id"] not in self.descobertas
        if nova:
            ui.desenhar_texto(tela, t("NOVA!"), (l.right - 16, l.y + 52), 8, (220, 80, 60), "midright",
                              sombra=False)

        # Nome com "pop" quando a receita chega
        tam = ui.tamanho_que_cabe(t(r["nome"]), l.w - 60, (18, 16, 14, 12, 10))
        k = self.nome_pop
        pulo = int(math.sin(min(1.0, k) * math.pi) * 8)
        ui.desenhar_texto(tela, t(r["nome"]), (l.centerx + 12, l.y + 80 - pulo), tam, (200, 70, 50),
                          "center", sombra=False)

        # Ingredientes na ordem
        n = len(ings)
        passo_x = 72
        x0 = l.centerx + 12 - (n - 1) * passo_x / 2
        y = l.y + 150
        for i, ing in enumerate(ings):
            x = x0 + i * passo_x
            feito = i < self.passo
            atual = i == self.passo and self.fase == "montar"
            dy = 0
            if atual:
                dy = -abs(math.sin(self.tempo * 6)) * 6
                caixa = pygame.Rect(0, 0, ICONE_LIVRO + 10, ICONE_LIVRO + 10)
                caixa.center = (int(x), int(y + dy))
                pygame.draw.rect(tela, (255, 236, 150), caixa, border_radius=12)
                pygame.draw.rect(tela, (230, 150, 40), caixa, 3, border_radius=12)
            tela.blit(icone_comida(ing, ICONE_LIVRO),
                      icone_comida(ing, ICONE_LIVRO).get_rect(center=(int(x), int(y + dy))))
            if feito:
                v = _veu_icone()
                tela.blit(v, v.get_rect(center=(int(x), int(y))))
                ui.check(tela, (int(x + 16), int(y + 16)), 18)
            # Número da ordem
            cor_num = (230, 150, 40) if atual else (170, 130, 100)
            pygame.draw.circle(tela, cor_num, (int(x), int(y + 44)), 10)
            ui.desenhar_texto(tela, str(i + 1), (int(x) + 1, int(y + 45)), 8, BRANCO, "center", sombra=False)
            if i < n - 1:
                ui.desenhar_texto(tela, "+", (int(x + passo_x / 2), int(y)), 12, (170, 110, 80), "center",
                                  sombra=False)

        # Fórmula por extenso
        formula = " + ".join(_nome(i) for i in ings)
        linhas = ui.quebrar_linhas("= " + formula, 8, l.w - 56)
        for j, linha in enumerate(linhas[:3]):
            ui.desenhar_texto(tela, linha, (l.centerx + 12, l.y + 216 + j * 16), 8, TINTA, "midtop",
                              sombra=False)

        # O que fazer agora
        if self.fase == "montar":
            dica = t("PEGUE: {nome}", nome=_nome(ings[self.passo]))
            cor = (60, 120, 60)
        elif self.fase == "mexer":
            dica = t("MEXA A PANELA!")
            cor = (200, 110, 30)
        elif self.fase == "servir":
            dica = t("SIRVA O PRATO!")
            cor = (60, 120, 60)
        elif self.fase == "queimou":
            dica = t("QUEIMOU... PRÓXIMA!")
            cor = (200, 60, 50)
        else:
            dica = t("DELÍCIA!")
            cor = (60, 120, 60)
        ui.desenhar_texto(tela, dica, (l.centerx + 12, l.bottom - 50), 10, cor, "center", sombra=False)

        # Tempo da receita
        barra = pygame.Rect(l.x + 40, l.bottom - 30, l.w - 60, 16)
        frac = max(0.0, min(1.0, self.t_receita / self.t_total))
        pygame.draw.rect(tela, (90, 60, 50), barra.inflate(4, 4), border_radius=8)
        pygame.draw.rect(tela, (225, 210, 190), barra, border_radius=7)
        if frac > 0.5:
            cor = (110, 200, 90)
        elif frac > 0.25:
            cor = (240, 190, 50)
        else:
            cor = (235, 80, 60) if int(self.tempo * 6) % 2 == 0 else (255, 150, 120)
        if frac > 0:
            pygame.draw.rect(tela, cor, (barra.x, barra.y, max(6, int(barra.w * frac)), barra.h),
                             border_radius=7)
        # Relojinho de areia
        ax, ay = l.x + 22, barra.centery
        pygame.draw.polygon(tela, (150, 90, 60), [(ax - 7, ay - 9), (ax + 7, ay - 9), (ax, ay), (ax + 7, ay + 9),
                                                  (ax - 7, ay + 9), (ax, ay)])
        pygame.draw.polygon(tela, (240, 200, 110), [(ax - 4, ay + 7), (ax + 4, ay + 7), (ax, ay + 2)])

        # Coleção logo abaixo do livro
        total = len(self._pool())
        ui.desenhar_texto(tela, t("DESCOBERTAS: {a}/{b}", a=len(self.descobertas), b=total),
                          (l.x + 6, l.bottom + 14), 10, (120, 60, 40), "topleft", sombra=False)

    # --- fogo e panela -------------------------------------

    def _desenhar_fogo(self, tela):
        cx, base = PANELA[0], BANCADA_Y + 4
        forte = 1.4 if self.fase in ("mexer", "servir") else 1.0
        if self.fase == "queimou":
            forte = 1.8
        for i in range(9):
            x = cx - 112 + i * 28
            h = (18 + 8 * math.sin(self.tempo * 13 + i * 1.7)) * forte
            pygame.draw.polygon(tela, (255, 120, 30), [(x - 11, base), (x + 11, base), (x, base - h)])
            pygame.draw.polygon(tela, (255, 220, 80), [(x - 5, base), (x + 5, base), (x, base - h * 0.55)])
            pygame.draw.circle(tela, (90, 170, 255), (x, base + 1), 4)

    def _desenhar_panela(self, tela):
        sup, (ox, oy) = _panela()
        tremida = 0
        if self.fase == "queimou" or self.bloqueio > 0:
            tremida = int(math.sin(self.tempo * 50) * 3)
        elif self.fase in ("mexer", "servir"):
            tremida = int(math.sin(self.tempo * 25) * 1.5)
        px, py = PANELA[0] + tremida, PANELA[1]
        tela.blit(sup, (px - ox, py - oy))

        # Caldo
        cor = tuple(int(c) for c in self.cor_caldo)
        liq = pygame.Rect(0, 0, LIQ_W, LIQ_H)
        liq.center = (px, py + 6)
        pygame.draw.ellipse(tela, ui.escurecer(cor, 40), liq)
        pygame.draw.ellipse(tela, cor, liq.inflate(-8, -10).move(0, -2))
        onda = math.sin(self.tempo * 4) * 8
        pygame.draw.ellipse(tela, ui.clarear(cor, 45), (liq.x + 40 + onda, liq.y + 12, 70, 12))

        # Ingredientes boiando (girando junto com a colher)
        n = len(self.no_caldo)
        for i, ing in enumerate(self.no_caldo):
            a = self.giro * 0.8 + i * math.tau / max(1, n) + self.tempo * 0.4
            x = px + math.cos(a) * LIQ_W * 0.28
            y = py + 4 + math.sin(a) * LIQ_H * 0.2 + math.sin(self.tempo * 3 + i) * 2
            ic = _girado(ing, 34, math.degrees(a) * 0.3)
            tela.blit(ic, ic.get_rect(center=(int(x), int(y))))

        # Bolhas
        for bx, by, t, vida, r in self.bolhas:
            k = t / vida
            rr = max(2, int(r * (0.5 + k)))
            pygame.draw.circle(tela, ui.clarear(cor, 60), (int(bx), int(by - k * 4)), rr, 2)

        # Colher de pau (gira com o mexido)
        g = self.giro
        ponta = (px + math.cos(g) * LIQ_W * 0.32, py + 6 + math.sin(g) * LIQ_H * 0.28)
        cabo = (ponta[0] + 40 + math.cos(g) * 30, ponta[1] - 150)
        pygame.draw.line(tela, (90, 55, 30), (ponta[0] + 2, ponta[1]), (cabo[0] + 2, cabo[1]), 11)
        pygame.draw.line(tela, (190, 130, 70), ponta, cabo, 8)
        pygame.draw.line(tela, (225, 170, 110), (ponta[0] - 2, ponta[1] - 10), (cabo[0] - 2, cabo[1] + 6), 2)
        pygame.draw.ellipse(tela, (90, 55, 30), (ponta[0] - 16, ponta[1] - 9, 32, 20))
        pygame.draw.ellipse(tela, (190, 130, 70), (ponta[0] - 14, ponta[1] - 8, 28, 16))

        # Beirada da frente (por cima do caldo)
        boca = pygame.Rect(0, 0, BOCA_W, BOCA_H)
        boca.center = (px, py)
        pygame.draw.arc(tela, (60, 64, 78), boca.inflate(10, 8), math.pi * 1.02, math.pi * 1.98, 6)
        pygame.draw.arc(tela, (205, 212, 225), boca.inflate(2, 0), math.pi * 1.05, math.pi * 1.95, 3)

    def _desenhar_mexer(self, tela):
        if self.fase not in ("mexer", "servir") or self.acabou:
            return
        b = BARRA_MEXER
        ui.painel(tela, b.inflate(16, 38).move(0, -8), (40, 30, 30), BRANCO, 12, 3, sombra=False)
        rotulo = t("MEXA!") if self.fase == "mexer" else t("PRONTO!")
        ui.desenhar_texto(tela, rotulo, (b.centerx, b.y - 12), 10, AMARELO, "center")
        pygame.draw.rect(tela, (70, 60, 60), b, border_radius=10)
        cor = (255, 170, 60) if self.fase == "mexer" else (120, 230, 100)
        if self.mexido > 0:
            pygame.draw.rect(tela, cor, (b.x, b.y, max(10, int(b.w * self.mexido)), b.h), border_radius=10)
            pygame.draw.rect(tela, ui.clarear(cor, 50), (b.x + 4, b.y + 3, max(2, int(b.w * self.mexido) - 8), 5),
                             border_radius=3)
        pygame.draw.rect(tela, BRANCO, b, 2, border_radius=10)

        if self.fase == "mexer":
            # Setinha girando em volta da panela + dica de teclas
            a0 = self.tempo * 4
            pontos = []
            for i in range(14):
                a = a0 + i * 0.3
                pontos.append((PANELA[0] + math.cos(a) * (BOCA_W // 2 + 44),
                               PANELA[1] + 10 + math.sin(a) * (BOCA_H // 2 + 36)))
            pygame.draw.lines(tela, (60, 30, 20), False, [(x + 2, y + 2) for x, y in pontos], 6)
            pygame.draw.lines(tela, AMARELO, False, pontos, 4)
            fx, fy = pontos[-1]
            ax, ay = pontos[-2]
            d = math.atan2(fy - ay, fx - ax)
            ponta = [(fx + math.cos(d) * 14, fy + math.sin(d) * 14),
                     (fx + math.cos(d + 2.3) * 12, fy + math.sin(d + 2.3) * 12),
                     (fx + math.cos(d - 2.3) * 12, fy + math.sin(d - 2.3) * 12)]
            pygame.draw.polygon(tela, AMARELO, ponta)
            seta = int(self.tempo * 6) % 2
            ui.desenhar_texto(tela, "←", (b.x - 34, b.centery), 14, AMARELO if seta == 0 else (120, 100, 80),
                              "center")
            ui.desenhar_texto(tela, "→", (b.right + 34, b.centery), 14, AMARELO if seta == 1 else (120, 100, 80),
                              "center")

    # --- chef ----------------------------------------------

    def _desenhar_chef(self, tela):
        x, y = CHEF
        ang = 0.0
        dy = math.sin(self.tempo * 3) * 3
        if self.chef_pulo > 0:
            dy -= abs(math.sin(self.chef_pulo * 10)) * 22
        if self.fase == "mexer" and self.t_mexeu < 0.3:
            ang = math.sin(self.giro * 2) * 10
        if self.chef_susto > 0:
            ang = math.sin(self.tempo * 45) * 9
            x += math.sin(self.tempo * 37) * 4
        if self.acabou:
            ang = math.sin(self.tempo * 4) * 6
        corpo = self.jogador.desenhar(tela, (int(x), int(y + dy)), ALT_CHEF, espelhar=True, angulo=ang)

        # Chapéu de chef acompanhando a inclinação
        larg = corpo.w * 1.02
        ch = _chapeu_girado(larg, ang)
        d = corpo.h * 0.36 + larg * 0.36
        rad = math.radians(ang)
        cx = corpo.centerx - math.sin(rad) * d
        cy = corpo.centery - math.cos(rad) * d
        tela.blit(ch, ch.get_rect(center=(int(cx), int(cy))))

        # Gota de suor no susto / estrelinhas no pulo
        if self.chef_susto > 0:
            gx, gy = corpo.right - 4, corpo.top + 20 + (0.8 - self.chef_susto) * 20
            pygame.draw.circle(tela, (120, 190, 255), (int(gx), int(gy)), 6)
            pygame.draw.polygon(tela, (120, 190, 255), [(gx - 5, gy - 2), (gx + 5, gy - 2), (gx, gy - 12)])
        elif self.chef_pulo > 0:
            for k in range(3):
                a = self.tempo * 6 + k * math.tau / 3
                ui.estrela(tela, (corpo.centerx + math.cos(a) * 60, corpo.top + math.sin(a) * 14), 7,
                           AMARELO, a)

    def _desenhar_prato(self, tela):
        if not self.prato:
            return
        rid, t = self.prato
        k = min(1.0, t / TEMPO_ENTREGA)
        e = 1 - (1 - k) ** 2
        x = PANELA[0] + (ENTREGA[0] - PANELA[0]) * e
        y = PANELA[1] - 40 + (ENTREGA[1] - PANELA[1] + 30) * e - math.sin(k * math.pi) * 120
        s = _prato(rid)
        tela.blit(s, s.get_rect(center=(int(x), int(y))))
        if int(self.tempo * 10) % 2 == 0:
            ui.estrela(tela, (x + 50, y - 30), 8, AMARELO, self.tempo * 4)

    # --- potes ---------------------------------------------

    def _desenhar_potes(self, tela):
        mouse = pygame.mouse.get_pos()
        hover = self._pote_em(mouse) if self.fase == "montar" and not self.acabou else None
        certo = None
        if self.fase == "montar" and not self.acabou:
            dica = DICA_APOS[self.opcao]
            if dica is not None and self.parado >= dica:
                certo = self.receita["ingredientes"][self.passo]
        for k, px in enumerate(POTES_X):
            pop = self.pote_pop[k]
            dy = (1 - pop) * 60 + self.pote_aperto[k] * 6
            if k == hover:
                dy -= 6
            topo = POTE_TOPO + dy
            if certo and self.potes[k] == certo:
                brilho = 0.5 + 0.5 * math.sin(self.tempo * 7)
                r = pygame.Rect(0, 0, POTE_W + 18 + int(brilho * 6), POTE_H + 14 + int(brilho * 6))
                r.center = (px, int(topo + POTE_H / 2 + 4))
                pygame.draw.rect(tela, ui.misturar((255, 200, 60), (255, 250, 190), brilho), r, 5,
                                 border_radius=24)
            clip = tela.get_clip()
            tela.set_clip(pygame.Rect(0, 0, LARGURA, POTE_TOPO + POTE_H + 12).clip(clip))
            sup = _pote(k)
            tela.blit(sup, (px - POTE_W // 2 - 4, topo - 4))
            ic = icone_comida(self.potes[k], 62)
            tela.blit(ic, ic.get_rect(center=(px, int(topo + 66))))
            tela.blit(_brilho_pote(), (px - POTE_W // 2 - 4, topo - 4))
            tela.set_clip(clip)
            if k == hover:
                r = pygame.Rect(0, 0, POTE_W + 8, POTE_H + 6)
                r.midtop = (px, int(topo) - 2)
                pygame.draw.rect(tela, BRANCO, r, 3, border_radius=22)
            # Número da tecla na tampa
            ui.desenhar_texto(tela, str(k + 1), (px, int(topo + 13)), 10, BRANCO, "center")
            # Nome embaixo (na prateleira)
            ui.desenhar_texto(tela, _nome(self.potes[k]), (px, POTE_TOPO + POTE_H + 30), 8,
                              (255, 240, 210), "center")
        if self.bloqueio > 0 and self.fase == "montar":
            ui.desenhar_texto(tela, t("ESPERE A FUMAÇA..."), (LARGURA // 2, POTE_TOPO - 16), 8,
                              (255, 180, 160), "center")

    def _desenhar_voando(self, tela):
        for v in self.voando:
            k = v["t"] / v["dur"]
            x = v["x0"] + (PANELA[0] - v["x0"]) * k
            y = v["y0"] + (PANELA[1] - 10 - v["y0"]) * k - math.sin(k * math.pi) * 140
            ic = _girado(v["ing"], 52, v["ang"] + k * 360)
            tela.blit(ic, ic.get_rect(center=(int(x), int(y))))
        for x in self.expulsos:
            ic = _girado(x["ing"], 52, x["ang"])
            tela.blit(ic, ic.get_rect(center=(int(x["x"]), int(x["y"]))))
            ui.desenhar_texto(tela, "×", (int(x["x"]) + 22, int(x["y"]) - 22), 12, (255, 90, 80), "center")

    def _desenhar_fumacas(self, tela):
        for x, y, _, _, vida, vida0, raio, preta in self.fumacas:
            k = vida / vida0
            s = _fumaca(raio, preta, min(1.0, k * 1.3))
            tela.blit(s, s.get_rect(center=(int(x), int(y))))

    def _desenhar_avisos(self, tela):
        if self.aviso_nova > 0 and self.estado == "jogando":
            t = 1.8 - self.aviso_nova
            escala = min(1.0, t / 0.2)
            y = 150 - int((1 - escala) * 30)
            if int(self.tempo * 8) % 2 == 0 or t < 0.8:
                caixa = pygame.Rect(0, 0, 300, 50)
                caixa.center = (PANELA[0], y)
                ui.painel(tela, caixa, (200, 70, 50), AMARELO, 14, 3, sombra=True)
                ui.desenhar_texto(tela, _t("RECEITA NOVA!"), caixa.center, 16, AMARELO, "center")
                ui.estrela(tela, (caixa.x + 18, caixa.centery), 9, AMARELO, self.tempo * 3)
                ui.estrela(tela, (caixa.right - 18, caixa.centery), 9, AMARELO, -self.tempo * 3)
        if self.fase == "servir" and not self.acabou:
            if int(self.tempo * 4) % 2 == 0:
                ui.desenhar_texto(tela, _t("CLIQUE OU ESPAÇO PARA SERVIR!"), (PANELA[0], BANCADA_Y + 50), 10,
                                  AMARELO, "center")

    # --- HUD -----------------------------------------------

    def desenhar_hud(self, tela):
        fundo = (50, 28, 20)
        caixa = pygame.Rect(12, 12, 300, 48)
        ui.painel(tela, caixa, fundo, BRANCO, 12, 3, sombra=False)
        ui.desenhar_texto(tela, t("PONTOS: {n}", n=self.pontos), (caixa.x + 16, caixa.centery), 14,
                          AMARELO, "midleft")

        relogio = pygame.Rect(0, 12, 150, 48)
        relogio.centerx = LARGURA // 2
        urgente = self.tempo_restante <= 10 and not self.acabou
        pulo = 0
        cor = BRANCO
        if urgente:
            pulo = int(abs(math.sin((self.tempo_restante % 1.0) * math.pi)) * 6)
            cor = (255, 110, 100) if int(self.tempo_restante * 4) % 2 == 0 else AMARELO
        relogio.y -= pulo
        ui.painel(tela, relogio, fundo, cor, 12, 3, sombra=False)
        rc = (relogio.x + 28, relogio.centery)
        pygame.draw.circle(tela, BRANCO, rc, 14)
        pygame.draw.circle(tela, (40, 44, 70), rc, 14, 3)
        ang = -math.pi / 2 + (1 - self.tempo_restante / TEMPO_PARTIDA) * math.tau
        pygame.draw.line(tela, (220, 50, 50), rc, (rc[0] + math.cos(ang) * 9, rc[1] + math.sin(ang) * 9), 2)
        ui.desenhar_texto(tela, _formatar_tempo(self.tempo_restante),
                          (relogio.right - 16, relogio.centery + 1), 16, cor, "midright")

        meta = META[self.opcao]
        caixa = pygame.Rect(0, 12, 208, 48)
        caixa.x = relogio.right + 20
        ui.painel(tela, caixa, fundo, BRANCO, 12, 3, sombra=False)
        ok = self.pontos >= meta
        ui.desenhar_texto(tela, t("META: {n}", n=meta), (caixa.x + 12, caixa.y + 9),
                          10, (150, 240, 120) if ok else (255, 220, 190))
        rec = self.recorde()
        ui.desenhar_texto(tela, t("RECORDE: {n}", n=rec if rec is not None else '--'),
                          (caixa.x + 12, caixa.y + 27), 10, AMARELO)
        if ok:
            ui.estrela(tela, (caixa.right - 20, caixa.centery), 10, AMARELO, self.tempo)

        if self.seq >= 2:
            texto = t("SEQUÊNCIA {n}", n=self.seq)
            sup = ui.texto(texto, 10, LARANJA)
            c2 = pygame.Rect(caixa.x, 66, sup.get_width() + 28, 26)
            ui.painel(tela, c2, fundo, LARANJA, 10, 2, sombra=False)
            tela.blit(sup, sup.get_rect(midleft=(c2.x + 14, c2.centery + 1)))
