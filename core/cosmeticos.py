import math

import pygame

from core import assets
from core.ui import escurecer, estrela, coracao

# ============================================================
# COSMÉTICOS
# ============================================================
# Chapéus, acessórios de rosto, roupas e efeitos do ovo.
#
# Tudo é desenhado de forma procedural no QUADRO 100x100 do
# avatar (o mesmo das imagens do ovo/cabelo/olho/boca):
#   corpo do ovo = elipse (15,14,67,74) -> centro (48, 51)
#   topo da cabeça y=14, olhos y 27-45, boca y 56-80, base y=88
#
# Camadas (quem chama é Jogador.compor):
#   "atras"  -> antes do ovo (capa, asas, metade de trás da boia)
#   "corpo"  -> depois do ovo, antes de cabelo/olho/boca
#   "frente" -> por cima de tudo (chapéus, óculos, gravata...)
#
# As partes estáticas ficam em cache (uma Surface 100x100 por
# item/camada/cor do ovo). Os EFEITOS são animados e desenhados
# direto na tela por desenhar_efeito(), com sprites em cache.

SLOTS = ["cabeca", "rosto", "corpo", "efeito"]

RARIDADES = {
    "COMUM": (230, 230, 240),
    "INCOMUM": (110, 220, 120),
    "RARO": (90, 170, 255),
    "EPICO": (190, 120, 255),
    "LENDARIO": (255, 214, 64),
}

# Cabelos "de topo": somem embaixo dos chapéus que escondem cabelo
# (0 chapéu de cowboy, 1 fios, 4 roxo, 5 tiara, 6 e 7 cocô).
# Os cabelos 2 (tufos laterais) e 3 (longo) continuam aparecendo.
CABELOS_DE_TOPO = {0, 1, 4, 5, 6, 7}

OVO_BRANCO = 2

# ============================================================
# CATÁLOGO
# ============================================================


def _item(nome, slot, preco, raridade, camadas, esconde_cabelo=False,
          loja=True, esconde=None):
    """
    `esconde`: cabelos que somem com este item. Padrão: todos os de
    topo se `esconde_cabelo`, senão nenhum. Alguns itens que não
    escondem cabelo ainda assim tiram os cabelos que brigariam com
    eles (ex: orelhas de gato não ficam em cima do chapéu de cowboy).
    """
    if esconde is None:
        esconde = CABELOS_DE_TOPO if esconde_cabelo else ()
    return dict(nome=nome, slot=slot, preco=preco, raridade=raridade,
                esconde_cabelo=esconde_cabelo, loja=loja, camadas=camadas,
                esconde=frozenset(esconde))


CATALOGO = {
    # ---------------- CABEÇA (camada frente) ----------------
    "bone": _item("BONÉ VERMELHO", "cabeca", 60, "COMUM", ("frente",), True),
    "gorro": _item("GORRO DE LÃ", "cabeca", 70, "COMUM", ("frente",), True),
    "laco": _item("LAÇO DE FITA", "cabeca", 45, "COMUM", ("frente",)),
    "flor": _item("FLOR NO CABELO", "cabeca", 45, "COMUM", ("frente",)),
    "orelhas_gato": _item("ORELHAS DE GATO", "cabeca", 150, "INCOMUM",
                          ("frente",), esconde={0}),
    "chapeu_chef": _item("CHAPÉU DE CHEF", "cabeca", 180, "INCOMUM",
                         ("frente",), True),
    "cartola": _item("CARTOLA", "cabeca", 250, "INCOMUM", ("frente",), True),
    "chapeu_pirata": _item("CHAPÉU PIRATA", "cabeca", 280, "INCOMUM",
                           ("frente",), True),
    "chapeu_mago": _item("CHAPÉU DE MAGO", "cabeca", 450, "RARO",
                         ("frente",), True),
    "chifre_unicornio": _item("CHIFRE DE UNICÓRNIO", "cabeca", 420, "RARO",
                              ("frente",), esconde={0, 6, 7}),
    "aureola": _item("AURÉOLA", "cabeca", 500, "RARO", ("frente",),
                     esconde={0, 6, 7}),
    "coroa": _item("COROA REAL", "cabeca", 1200, "EPICO", ("frente",), True),
    # os cabelos de topo "furariam" o vidro; tufos e cabelo longo ficam
    "capacete_espacial": _item("CAPACETE ESPACIAL", "cabeca", 1300, "EPICO",
                               ("frente",), esconde=CABELOS_DE_TOPO),

    # ---------------- ROSTO (camada frente) ----------------
    "bochechas": _item("BOCHECHAS ROSADAS", "rosto", 40, "COMUM", ("frente",)),
    "tapa_olho": _item("TAPA-OLHO", "rosto", 50, "COMUM", ("frente",)),
    "oculos_redondos": _item("ÓCULOS DE NERD", "rosto", 55, "COMUM",
                             ("frente",)),
    "bigode": _item("BIGODÃO", "rosto", 60, "COMUM", ("frente",)),
    "oculos_sol": _item("ÓCULOS DO SOL", "rosto", 70, "COMUM", ("frente",)),
    "oculos_coracao": _item("ÓCULOS DE CORAÇÃO", "rosto", 200, "INCOMUM",
                            ("frente",)),
    "mascara_heroi": _item("MÁSCARA DE HERÓI", "rosto", 220, "INCOMUM",
                           ("frente",)),

    # ---------------- CORPO ----------------
    "gravata": _item("GRAVATA-BORBOLETA", "corpo", 55, "COMUM", ("frente",)),
    "cachecol": _item("CACHECOL LISTRADO", "corpo", 80, "COMUM", ("corpo",)),
    "colar_havaiano": _item("COLAR HAVAIANO", "corpo", 150, "INCOMUM",
                            ("corpo",)),
    "medalha": _item("MEDALHA DE OURO", "corpo", 250, "INCOMUM", ("frente",)),
    # a metade da frente vai na camada "frente" para o cabelo longo
    # não cobrir a boia nem o patinho
    "boia_patinho": _item("BOIA DE PATINHO", "corpo", 280, "INCOMUM",
                          ("atras", "frente")),
    "capa_heroi": _item("CAPA DE HERÓI", "corpo", 450, "RARO", ("atras",)),
    "asas_anjo": _item("ASAS DE ANJO", "corpo", 950, "EPICO", ("atras",)),

    # ---------------- EFEITOS (animados) ----------------
    "nuvenzinha": _item("NUVENZINHA DE CHUVA", "efeito", 280, "INCOMUM", ()),
    "aura_notas": _item("NOTAS MUSICAIS", "efeito", 300, "INCOMUM", ()),
    "aura_brilhos": _item("ESTRELINHAS", "efeito", 480, "RARO", ()),
    "aura_coracoes": _item("CORAÇÕES", "efeito", 480, "RARO", ()),
    "aura_dourada": _item("AURA DOURADA", "efeito", 2200, "LENDARIO", ()),

    # ---------------- RECOMPENSA (não vende) ----------------
    # Ganha ao completar o ÁLBUM DE BORBOLETAS.
    "asas_borboleta": _item("ASAS DE BORBOLETA", "corpo", 0, "LENDARIO",
                            ("atras",), loja=False),
}

EFEITOS = ("nuvenzinha", "aura_notas", "aura_brilhos", "aura_coracoes",
           "aura_dourada")

# Efeitos registrados por outros módulos (core/cosmeticos_novos.py):
# id -> desenhar(tela, cx, cy, h, t, fase)
EFEITOS_EXTRA = {}

# Ícones de slots com desenho próprio (core/visual_extra.py):
# slot -> icone(item_id, tamanho, ovo)
ICONE_SLOT = {}


def esconde_cabelo(ids, cabelo):
    """True se algum chapéu equipado esconde o cabelo `cabelo`."""
    for item_id in ids or ():
        dados = CATALOGO.get(item_id)
        if dados and cabelo in dados["esconde"]:
            return True

    return False


# ============================================================
# FERRAMENTAS DE DESENHO
# ============================================================

_TRANSP = (0, 0, 0, 0)
_mascara_ovo = None


def _temp():
    return pygame.Surface((100, 100), pygame.SRCALPHA)


def _mascara():
    """Elipse do ovo opaca (branca) num fundo transparente."""
    global _mascara_ovo

    if _mascara_ovo is None:
        _mascara_ovo = _temp()
        pygame.draw.ellipse(_mascara_ovo, (255, 255, 255, 255), (15, 14, 67, 74))

    return _mascara_ovo


def _recortar_ovo(sup):
    """Apaga tudo o que ficou fora do corpo do ovo."""
    sup.blit(_mascara(), (0, 0), special_flags=pygame.BLEND_RGBA_MIN)


def _recortar(sup, forma):
    """Apaga de `sup` tudo o que ficou fora da silhueta de `forma`."""
    m = pygame.mask.from_surface(forma, 1)
    sup.blit(m.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=_TRANSP),
             (0, 0), special_flags=pygame.BLEND_RGBA_MIN)


_VIZINHOS = ((1, 0), (-1, 0), (0, 1), (0, -1))
_VIZINHOS_8 = _VIZINHOS + ((1, 1), (1, -1), (-1, 1), (-1, -1))


def _contorno_interno(forma, cor, esp=2):
    """
    Pinta um contorno de `esp` px na borda de dentro da silhueta de
    `forma` (não aumenta o tamanho da forma). Usa máscaras: a borda
    é a silhueta menos a silhueta "encolhida" (erosão).
    """
    m = pygame.mask.from_surface(forma, 1)
    miolo = m

    for passo in range(esp):
        viz = _VIZINHOS_8 if passo == 0 and esp >= 2 else _VIZINHOS
        for dx, dy in viz:
            miolo = miolo.overlap_mask(m, (dx * (passo + 1), dy * (passo + 1)))

    borda = m.copy()
    borda.erase(miolo, (0, 0))
    forma.blit(borda.to_surface(setcolor=cor, unsetcolor=_TRANSP), (0, 0))


def _forma(desenhar, cor, contorno=None, esp=2, detalhes=None):
    """
    Desenha uma forma grande no estilo dos cosméticos:
    preenchimento `cor`, `detalhes(sup)` recortados pela forma e
    contorno de dentro de `esp` px (padrão: cor -60).
    `desenhar(sup, cor)` pinta a silhueta.
    """
    sup = _temp()
    desenhar(sup, cor)

    if detalhes:
        silhueta = sup.copy()
        detalhes(sup)
        _recortar(sup, silhueta)

    if esp:
        _contorno_interno(sup, contorno or escurecer(cor, 60), esp)

    return sup


def _poligono(pontos):
    return lambda s, c: pygame.draw.polygon(s, c, pontos)


def _elipse(rect):
    return lambda s, c: pygame.draw.ellipse(s, c, rect)


def _circulo(centro, raio):
    return lambda s, c: pygame.draw.circle(s, c, centro, raio)


def _linha(sup, cor, a, b, esp=2):
    pygame.draw.line(sup, cor, a, b, esp)


def _apagar_abaixo(sup, y):
    """Apaga tudo de y para baixo (recorte "em y <= y-1")."""
    sup.fill(_TRANSP, (0, y, 100, 100 - y))


def _apagar_acima(sup, y):
    sup.fill(_TRANSP, (0, 0, 100, y))


def _coracao_q(sup, cor, cx, cy, cresce=0):
    """Coração do óculos (largura 22) centrado em (cx, cy)."""
    r = 6 + cresce
    pygame.draw.circle(sup, cor, (cx - 5, cy - 3), r)
    pygame.draw.circle(sup, cor, (cx + 5, cy - 3), r)
    pygame.draw.polygon(sup, cor, [
        (cx - 11 - cresce, cy - 1), (cx + 11 + cresce, cy - 1),
        (cx, cy + 10 + cresce)])


def _estrela4(sup, cor, centro, raio, fino=0.32):
    """Estrela de 4 pontas (brilho)."""
    x, y = centro
    r2 = raio * fino
    pygame.draw.polygon(sup, cor, [
        (x, y - raio), (x + r2, y - r2), (x + raio, y), (x + r2, y + r2),
        (x, y + raio), (x - r2, y + r2), (x - raio, y), (x - r2, y - r2)])


def _branco(ovo, normal, no_branco=(150, 150, 170)):
    """Contorno de peças brancas: mais forte quando o ovo é branco."""
    return no_branco if ovo == OVO_BRANCO else normal


# ============================================================
# CABEÇA
# ============================================================


def _bone(sup, ovo):
    cor, escuro, claro = (225, 55, 55), (150, 25, 25), (255, 120, 110)

    def copa(s, c):
        pygame.draw.ellipse(s, c, (27, 4, 44, 34))
        _apagar_abaixo(s, 22)

    def detalhes(s):
        _linha(s, escuro, (41, 6), (37, 21))
        _linha(s, escuro, (57, 6), (61, 21))
        # brilho da copa
        pygame.draw.arc(s, claro, (31, 7, 36, 26), math.radians(100),
                        math.radians(150), 2)

    sup.blit(_forma(copa, cor, (110, 20, 20), detalhes=detalhes), (0, 0))
    pygame.draw.circle(sup, escuro, (49, 5), 3)

    # aba para a frente/direita
    sup.blit(_forma(_elipse((50, 16, 38, 9)), escuro, (95, 15, 15)), (0, 0))
    _linha(sup, claro, (54, 18), (83, 20))

    # logo: um ovinho
    pygame.draw.circle(sup, (255, 255, 255), (42, 14), 4)
    pygame.draw.ellipse(sup, cor, (40, 12, 4, 5))


def _gorro(sup, ovo):
    cor, barra, nervura = (70, 130, 230), (40, 90, 190), (30, 70, 160)

    def cupula(s, c):
        pygame.draw.ellipse(s, c, (25, 4, 48, 38))
        _apagar_abaixo(s, 21)

    def listra(s):
        pygame.draw.rect(s, (255, 255, 255), (25, 11, 48, 4))

    sup.blit(_forma(cupula, cor, detalhes=listra), (0, 0))

    def detalhes_barra(s):
        for x in range(27, 72, 5):
            pygame.draw.line(s, nervura, (x, 17), (x, 24), 1)

    sup.blit(_forma(lambda s, c: pygame.draw.rect(s, c, (23, 16, 52, 9),
                                                  border_radius=4),
                    barra, (20, 50, 130), detalhes=detalhes_barra), (0, 0))

    # pompom
    pompom = _forma(_circulo((49, 5), 5), (255, 255, 255),
                    _branco(ovo, (175, 185, 215)), esp=1)
    sup.blit(pompom, (0, 0))
    for p in ((47, 3), (51, 5), (48, 7)):
        sup.fill((210, 218, 238), (p, (1, 1)))


def _laco(sup, ovo):
    cor, escuro = (255, 110, 170), (200, 50, 120)

    def alcas(s, c):
        pygame.draw.polygon(s, c, [(64, 17), (53, 10), (53, 24)])
        pygame.draw.polygon(s, c, [(64, 17), (75, 10), (75, 24)])

    def pontas(s, c):
        pygame.draw.polygon(s, c, [(63, 18), (59, 25), (62, 24)])
        pygame.draw.polygon(s, c, [(65, 18), (69, 25), (66, 24)])

    sup.blit(_forma(pontas, cor, escuro, esp=1), (0, 0))
    sup.blit(_forma(alcas, cor, escuro), (0, 0))
    pygame.draw.circle(sup, escuro, (64, 17), 3)
    sup.fill((255, 255, 255), (56, 13, 2, 2))


def _flor(sup, ovo):
    cx, cy = 30, 20
    borda = _branco(ovo, (230, 200, 220), (205, 140, 180))

    # folha (atrás das pétalas)
    sup.blit(_forma(_elipse((34, 24, 10, 5)), (90, 190, 80), (50, 130, 50),
                    esp=1), (0, 0))

    for i in range(5):
        a = math.radians(i * 72 - 90)
        p = (round(cx + math.cos(a) * 6), round(cy + math.sin(a) * 6))
        pygame.draw.circle(sup, (255, 255, 255), p, 5)
        pygame.draw.circle(sup, borda, p, 5, 1)

    pygame.draw.circle(sup, (255, 205, 40), (cx, cy), 4)
    pygame.draw.circle(sup, (230, 160, 20), (cx, cy), 4, 1)
    sup.fill((230, 160, 20), (cx, cy, 2, 2))


def _orelhas_gato(sup, ovo):
    externo, interno, contorno = (70, 70, 80), (255, 170, 200), (40, 40, 50)

    esquerda = [(24, 24), (28, 2), (42, 17)]
    direita = [(56, 17), (70, 2), (74, 24)]

    def orelhas(s, c):
        pygame.draw.polygon(s, c, esquerda)
        pygame.draw.polygon(s, c, direita)

    sup.blit(_forma(orelhas, externo, contorno), (0, 0))
    # a base da orelha "nasce" da cabeça: sem contorno embaixo
    pygame.draw.line(sup, externo, (27, 22), (39, 17), 2)
    pygame.draw.line(sup, externo, (59, 17), (71, 22), 2)
    pygame.draw.polygon(sup, interno, [(28, 20), (30, 8), (38, 17)])
    pygame.draw.polygon(sup, interno, [(60, 17), (68, 8), (70, 20)])


def _chapeu_chef(sup, ovo):
    sombra = (225, 228, 240)
    contorno = _branco(ovo, (170, 175, 195))

    # tufo: contornos (raio + 2) primeiro, depois o branco
    tufos = (((37, 11), 8), ((49, 10), 10), ((61, 11), 8))
    for c, r in tufos:
        pygame.draw.circle(sup, contorno, c, r + 2)
    for c, r in tufos:
        pygame.draw.circle(sup, (255, 255, 255), c, r)
    # sombrinhas entre os gomos
    pygame.draw.arc(sup, sombra, (29, 3, 16, 16), math.radians(250),
                    math.radians(340), 2)
    pygame.draw.arc(sup, sombra, (53, 3, 16, 16), math.radians(200),
                    math.radians(290), 2)

    def pregas(s):
        for x in (35, 42, 49, 56, 63):
            pygame.draw.line(s, sombra, (x, 14), (x, 23), 2)

    faixa = _forma(lambda s, c: pygame.draw.rect(s, c, (29, 13, 40, 11)),
                   (255, 255, 255), contorno, detalhes=pregas)
    sup.blit(faixa, (0, 0))


def _cartola(sup, ovo):
    preto, faixa, brilho = (35, 35, 45), (210, 40, 70), (80, 80, 100)
    borda = (12, 12, 18)

    def copa(s, c):
        pygame.draw.rect(s, c, (35, 0, 28, 18))

    def detalhes(s):
        pygame.draw.rect(s, faixa, (35, 12, 28, 5))
        _linha(s, brilho, (38, 2), (38, 11))

    sup.blit(_forma(copa, preto, borda, detalhes=detalhes), (0, 0))
    sup.blit(_forma(lambda s, c: pygame.draw.rect(s, c, (25, 17, 48, 6),
                                                  border_radius=3),
                    preto, borda), (0, 0))
    _linha(sup, brilho, (29, 18), (69, 18), 1)


def _chapeu_pirata(sup, ovo):
    preto, dourado = (40, 35, 45), (235, 195, 70)

    pontos = [(19, 23), (27, 6), (40, 2), (49, 5), (58, 2), (71, 6),
              (79, 23), (49, 18)]
    sup.blit(_forma(_poligono(pontos), preto, (15, 12, 18)), (0, 0))
    pygame.draw.lines(sup, dourado, False, [(19, 23), (49, 18), (79, 23)], 2)
    pygame.draw.lines(sup, (170, 135, 40), False,
                      [(21, 21), (27, 7), (40, 3), (49, 6), (58, 3), (71, 7),
                       (77, 21)], 1)

    # caveira
    osso = (255, 255, 255)
    pygame.draw.line(sup, osso, (43, 12), (55, 18), 2)
    pygame.draw.line(sup, osso, (43, 18), (55, 12), 2)
    for p in ((42, 11), (54, 17), (42, 17), (54, 11)):
        sup.fill(osso, (p, (3, 2)))
    pygame.draw.circle(sup, osso, (49, 10), 4)
    sup.fill(osso, (47, 13, 5, 2))
    sup.fill(preto, (47, 9, 2, 2))
    sup.fill(preto, (51, 9, 2, 2))


def _chapeu_mago(sup, ovo):
    roxo, escuro, ouro = (95, 60, 185), (60, 35, 130), (255, 225, 90)

    sup.blit(_forma(_elipse((17, 15, 64, 10)), escuro, (35, 18, 85)), (0, 0))

    def cone(s, c):
        pygame.draw.polygon(s, c, [(30, 19), (68, 19), (52, 1)])
        pygame.draw.polygon(s, c, [(50, 4), (54, 0), (64, 3), (55, 6)])

    def detalhes(s):
        pygame.draw.polygon(s, ouro, [(31, 16), (67, 16), (68, 19), (30, 19)])

    sup.blit(_forma(cone, roxo, (40, 20, 105), detalhes=detalhes), (0, 0))
    estrela(sup, (42, 12), 3, ouro)
    estrela(sup, (56, 8), 2, ouro)
    pygame.draw.circle(sup, ouro, (47, 6), 2)
    sup.fill(roxo, (48, 5, 1, 1))


def _chifre_unicornio(sup, ovo):
    chifre, espiral, contorno = (255, 240, 200), (255, 170, 210), (210, 170, 120)

    sup.blit(_forma(_elipse((42, 14, 14, 5)), (255, 200, 230), (220, 140, 180),
                    esp=1), (0, 0))

    def detalhes(s):
        _linha(s, espiral, (45, 13), (53, 10))
        _linha(s, espiral, (46, 8), (52, 6))
        _linha(s, espiral, (47, 4), (51, 2))

    sup.blit(_forma(_poligono([(43, 17), (55, 17), (50, 0)]), chifre, contorno,
                    esp=1, detalhes=detalhes), (0, 0))


def _aureola(sup, ovo):
    brilho = _temp()
    pygame.draw.ellipse(brilho, (255, 245, 170, 140), (30, 0, 38, 11), 1)
    sup.blit(brilho, (0, 0))
    pygame.draw.ellipse(sup, (255, 225, 80), (32, 1, 34, 9), 3)
    # sombra de baixo do anel e reflexo de cima (legível em fundo claro)
    pygame.draw.arc(sup, (215, 165, 30), (32, 1, 34, 9), math.radians(200),
                    math.radians(340), 1)
    pygame.draw.arc(sup, (255, 250, 210), (33, 1, 32, 8), math.radians(60),
                    math.radians(120), 1)


def _coroa(sup, ovo):
    ouro, escuro, brilho = (255, 200, 40), (190, 130, 20), (255, 240, 150)

    pontas = [(30, 14), (30, 3), (37, 9), (43, 2), (49, 8), (55, 2), (61, 9),
              (68, 3), (68, 14)]

    def forma(s, c):
        pygame.draw.rect(s, c, (30, 14, 39, 8))
        pygame.draw.polygon(s, c, pontas)

    def detalhes(s):
        pygame.draw.line(s, escuro, (31, 14), (67, 14), 1)

    sup.blit(_forma(forma, ouro, escuro, detalhes=detalhes), (0, 0))

    for p in ((30, 3), (43, 2), (55, 2), (68, 3)):
        pygame.draw.circle(sup, brilho, p, 2)
    pygame.draw.circle(sup, (230, 40, 70), (49, 18), 3)
    sup.fill((255, 170, 190), (48, 17, 1, 1))
    pygame.draw.circle(sup, (60, 130, 240), (38, 18), 2)
    pygame.draw.circle(sup, (60, 200, 110), (60, 18), 2)
    pygame.draw.line(sup, brilho, (33, 16), (35, 16), 1)


def _capacete_espacial(sup, ovo):
    vidro = _temp()
    pygame.draw.circle(vidro, (170, 215, 255, 60), (48, 50), 46)
    pygame.draw.circle(vidro, (230, 240, 255, 255), (48, 50), 46, 3)
    pygame.draw.circle(vidro, (140, 155, 190, 255), (48, 50), 47, 1)
    pygame.draw.arc(vidro, (255, 255, 255, 200), (14, 12, 40, 40),
                    math.radians(100), math.radians(170), 3)
    pygame.draw.circle(vidro, (255, 255, 255, 180), (28, 26), 3)
    sup.blit(vidro, (0, 0))

    # anel do pescoço
    sup.blit(_forma(_elipse((22, 84, 54, 12)), (200, 205, 220), (130, 135, 150)),
             (0, 0))
    pygame.draw.line(sup, (235, 238, 248), (32, 87), (64, 87), 1)

    # antena
    pygame.draw.line(sup, (160, 160, 170), (74, 12), (82, 3), 2)
    pygame.draw.circle(sup, (240, 60, 60), (82, 3), 2)


# ============================================================
# ROSTO
# ============================================================


def _bochechas(sup, ovo):
    t = _temp()
    pygame.draw.ellipse(t, (255, 110, 140, 150), (19, 46, 14, 8))
    pygame.draw.ellipse(t, (255, 110, 140, 150), (65, 46, 14, 8))
    _recortar_ovo(t)
    sup.blit(t, (0, 0))


def _tapa_olho(sup, ovo):
    t = _temp()
    cordao = (30, 30, 30)
    _linha(t, cordao, (18, 24), (54, 31))
    _linha(t, cordao, (74, 34), (81, 37))
    pygame.draw.ellipse(t, (25, 25, 25), (53, 27, 22, 17))
    _linha(t, (80, 80, 80), (57, 30), (63, 29))
    _recortar_ovo(t)
    sup.blit(t, (0, 0))


def _oculos_redondos(sup, ovo):
    aro = (50, 45, 60)
    t = _temp()
    for c in ((34, 35), (63, 35)):
        pygame.draw.circle(t, (210, 235, 255, 90), c, 10)
    sup.blit(t, (0, 0))
    for c in ((34, 35), (63, 35)):
        pygame.draw.circle(sup, aro, c, 10, 2)
        pygame.draw.arc(sup, (255, 255, 255), (c[0] - 7, c[1] - 7, 14, 14),
                        math.radians(110), math.radians(160), 1)
    _linha(sup, aro, (44, 34), (53, 34))
    # hastes até a borda do ovo
    _linha(sup, aro, (24, 33), (19, 31))
    _linha(sup, aro, (73, 33), (78, 31))


def _bigode(sup, ovo):
    marrom, contorno = (80, 50, 30), (50, 30, 15)

    def forma(s, c):
        pygame.draw.ellipse(s, c, (30, 50, 19, 8))
        pygame.draw.ellipse(s, c, (49, 50, 19, 8))
        pygame.draw.circle(s, c, (29, 52), 3)
        pygame.draw.circle(s, c, (69, 52), 3)
        pygame.draw.circle(s, c, (27, 49), 2)
        pygame.draw.circle(s, c, (71, 49), 2)

    sup.blit(_forma(forma, marrom, contorno, esp=1), (0, 0))
    pygame.draw.line(sup, contorno, (49, 50), (49, 55), 2)
    pygame.draw.line(sup, (125, 85, 55), (36, 52), (44, 52), 1)
    pygame.draw.line(sup, (125, 85, 55), (54, 52), (62, 52), 1)


def _oculos_sol(sup, ovo):
    preto = (25, 25, 35)
    # lentes 3 px mais altas que no design: cobrem o olho inteiro
    pygame.draw.rect(sup, preto, (21, 28, 26, 17), border_radius=6)
    pygame.draw.rect(sup, preto, (51, 28, 26, 17), border_radius=6)
    _linha(sup, preto, (21, 29), (77, 29))
    pygame.draw.line(sup, preto, (47, 32), (51, 32), 3)
    _linha(sup, (255, 255, 255), (25, 31), (31, 31))
    _linha(sup, (255, 255, 255), (55, 31), (61, 31))
    sup.fill((255, 255, 255), (25, 34, 2, 2))
    sup.fill((255, 255, 255), (55, 34, 2, 2))


def _oculos_coracao(sup, ovo):
    rosa, contorno, brilho = (240, 60, 130, 220), (150, 20, 70), (255, 190, 215)
    t = _temp()

    for cx, cy in ((34, 35), (63, 35)):
        _coracao_q(t, contorno, cx, cy, 2)
    for cx, cy in ((34, 35), (63, 35)):
        _coracao_q(t, rosa, cx, cy)
        pygame.draw.circle(t, brilho, (cx - 6, cy - 5), 2)

    _linha(t, contorno, (45, 33), (52, 33))
    sup.blit(t, (0, 0))


def _mascara_heroi(sup, ovo):
    azul, borda = (40, 90, 220), (20, 50, 150)

    t = _temp()
    pygame.draw.polygon(t, azul, [(16, 31), (81, 31), (81, 42), (58, 44),
                                  (49, 40), (40, 44), (16, 42)])
    pygame.draw.ellipse(t, _TRANSP, (24, 32, 18, 10))
    pygame.draw.ellipse(t, _TRANSP, (55, 32, 18, 10))
    _recortar_ovo(t)
    _contorno_interno(t, borda, 2)
    pygame.draw.line(t, (90, 140, 245), (20, 33), (22, 33), 1)
    sup.blit(t, (0, 0))

    # fitinhas do nó (fora do recorte)
    def fitas(s, c):
        pygame.draw.polygon(s, c, [(80, 34), (92, 30), (90, 38)])
        pygame.draw.polygon(s, c, [(80, 38), (94, 42), (88, 46)])

    sup.blit(_forma(fitas, azul, borda, esp=1), (0, 0))


# ============================================================
# CORPO
# ============================================================


def _gravata(sup, ovo):
    vermelho, escuro = (220, 40, 60), (150, 20, 40)

    def asas(s, c):
        pygame.draw.polygon(s, c, [(49, 85), (38, 79), (38, 91)])
        pygame.draw.polygon(s, c, [(49, 85), (60, 79), (60, 91)])

    def dobras(s):
        _linha(s, escuro, (42, 82), (42, 88))
        _linha(s, escuro, (56, 82), (56, 88))

    sup.blit(_forma(asas, vermelho, (110, 10, 30), detalhes=dobras), (0, 0))
    pygame.draw.rect(sup, escuro, (45, 81, 8, 9), border_radius=2)
    pygame.draw.rect(sup, vermelho, (46, 82, 6, 7), border_radius=2)


def _cachecol(sup, ovo):
    vermelho, escuro = (230, 60, 60), (160, 30, 30)
    faixa = [(21, 72), (34, 77), (49, 79), (64, 77), (77, 72), (75, 81),
             (64, 86), (49, 88), (34, 86), (23, 81)]

    def listras(s):
        for x in (30, 42, 56, 68):
            pygame.draw.line(s, (255, 255, 255), (x, 70), (x, 90), 3)

    sup.blit(_forma(_poligono(faixa), vermelho, escuro, detalhes=listras),
             (0, 0))

    # ponta pendurada
    def ponta_listras(s):
        s.fill((255, 255, 255), (58, 86, 10, 2))
        s.fill((255, 255, 255), (58, 91, 10, 2))

    ponta = _forma(lambda s, c: pygame.draw.rect(s, c, (58, 80, 10, 17)),
                   vermelho, escuro, detalhes=ponta_listras)
    sup.blit(ponta, (0, 0))
    for x in (59, 62, 65):
        pygame.draw.line(sup, escuro, (x, 97), (x, 99), 1)


def _colar_havaiano(sup, ovo):
    cores = [(255, 90, 140), (255, 210, 60), (120, 200, 255), (255, 255, 255),
             (180, 120, 240)]

    for i in range(11):
        x = 22 + i * 5.4
        y = 70 + 16 * (1 - ((x - 49) / 27) ** 2)
        c = cores[i % len(cores)]
        p = (round(x), round(y))
        borda = (150, 150, 170) if c == (255, 255, 255) else escurecer(c, 70)
        pygame.draw.circle(sup, borda, p, 5)
        pygame.draw.circle(sup, c, p, 4)
        pygame.draw.circle(sup, (255, 240, 120), p, 1)


def _medalha(sup, ovo):
    pygame.draw.line(sup, (60, 120, 230), (40, 78), (47, 86), 4)
    pygame.draw.line(sup, (230, 60, 60), (58, 78), (51, 86), 4)
    sup.blit(_forma(_circulo((49, 91), 7), (255, 200, 40), (180, 130, 20)),
             (0, 0))
    estrela(sup, (49, 91), 4, (255, 240, 150))


def _boia(ovo):
    """Anel inteiro da boia (com contorno e listras), antes de dividir."""
    amarelo, laranja = (255, 215, 50), (255, 150, 40)

    def anel(s, c):
        pygame.draw.ellipse(s, c, (8, 66, 84, 26))
        pygame.draw.ellipse(s, _TRANSP, (16, 72, 68, 14))

    def listras(s):
        for x in (14, 30, 64, 80):
            s.fill(laranja, (x, 60, 6, 40))
        # brilho no plástico
        pygame.draw.arc(s, (255, 245, 170), (11, 68, 78, 22),
                        math.radians(200), math.radians(250), 1)

    return _forma(anel, amarelo, (190, 140, 20), detalhes=listras)


def _boia_atras(sup, ovo):
    anel = _boia(ovo)
    _apagar_abaixo(anel, 79)
    sup.blit(anel, (0, 0))


def _boia_frente(sup, ovo):
    anel = _boia(ovo)
    _apagar_acima(anel, 79)
    sup.blit(anel, (0, 0))

    # cabeça do patinho
    sup.blit(_forma(_circulo((86, 68), 7), (255, 215, 50), (190, 140, 20)),
             (0, 0))
    pygame.draw.polygon(sup, (255, 140, 30), [(92, 67), (99, 70), (92, 73)])
    sup.fill((20, 20, 20), (88, 66, 2, 2))
    sup.fill((255, 150, 120), (83, 70, 3, 2))


def _capa_heroi(sup, ovo):
    vermelho, sombra = (220, 40, 55), (150, 20, 35)

    def dobras(s):
        pygame.draw.line(s, sombra, (20, 70), (12, 96), 3)
        pygame.draw.line(s, sombra, (78, 70), (86, 96), 3)

    sup.blit(_forma(_poligono([(24, 40), (74, 40), (90, 98), (49, 94),
                               (8, 98)]),
                    vermelho, (110, 10, 25), detalhes=dobras), (0, 0))


def _asas_anjo(sup, ovo):
    sombra = (215, 225, 245)
    contorno = _branco(ovo, (170, 185, 215), (140, 150, 185))
    esquerda = [(1, 30, 24, 14), (2, 41, 22, 13), (5, 52, 18, 12)]

    for lado in (0, 1):
        for x, y, w, h in reversed(esquerda):
            if lado:
                x = 97 - x - w
            pygame.draw.ellipse(sup, contorno, (x, y, w, h))
            pygame.draw.ellipse(sup, (255, 255, 255), (x + 2, y + 2, w - 4, h - 4))
            # penas
            meio = y + h // 2
            if lado:
                _linha(sup, sombra, (x + w // 2, meio), (x + w - 5, meio - 1))
                _linha(sup, sombra, (x + w // 2, meio + 3), (x + w - 7, meio + 3))
            else:
                _linha(sup, sombra, (x + 5, meio - 1), (x + w // 2, meio))
                _linha(sup, sombra, (x + 7, meio + 3), (x + w // 2, meio + 3))


def _asas_borboleta(sup, ovo):
    laranja, bolinha, contorno = (255, 150, 60), (255, 230, 120), (120, 60, 20)
    asas = [(0, 30, 26, 22), (4, 52, 20, 16)]

    def forma(s, c):
        for x, y, w, h in asas:
            pygame.draw.ellipse(s, c, (x, y, w, h))
            pygame.draw.ellipse(s, c, (97 - x - w, y, w, h))

    def detalhes(s):
        for x, y in ((8, 37), (15, 44), (11, 59)):
            pygame.draw.circle(s, bolinha, (x, y), 3 if y < 50 else 2)
            pygame.draw.circle(s, bolinha, (97 - x, y), 3 if y < 50 else 2)
        # veios saindo do corpo
        for fim in ((5, 36), (8, 62)):
            pygame.draw.line(s, (215, 110, 40), (23, 48), fim, 1)
            pygame.draw.line(s, (215, 110, 40), (74, 48), (97 - fim[0], fim[1]), 1)

    sup.blit(_forma(forma, laranja, contorno, detalhes=detalhes), (0, 0))


# ============================================================
# TABELA DE DESENHOS E aplicar()
# ============================================================

_DESENHOS = {
    ("bone", "frente"): _bone,
    ("gorro", "frente"): _gorro,
    ("laco", "frente"): _laco,
    ("flor", "frente"): _flor,
    ("orelhas_gato", "frente"): _orelhas_gato,
    ("chapeu_chef", "frente"): _chapeu_chef,
    ("cartola", "frente"): _cartola,
    ("chapeu_pirata", "frente"): _chapeu_pirata,
    ("chapeu_mago", "frente"): _chapeu_mago,
    ("chifre_unicornio", "frente"): _chifre_unicornio,
    ("aureola", "frente"): _aureola,
    ("coroa", "frente"): _coroa,
    ("capacete_espacial", "frente"): _capacete_espacial,
    ("bochechas", "frente"): _bochechas,
    ("tapa_olho", "frente"): _tapa_olho,
    ("oculos_redondos", "frente"): _oculos_redondos,
    ("bigode", "frente"): _bigode,
    ("oculos_sol", "frente"): _oculos_sol,
    ("oculos_coracao", "frente"): _oculos_coracao,
    ("mascara_heroi", "frente"): _mascara_heroi,
    ("gravata", "frente"): _gravata,
    ("cachecol", "corpo"): _cachecol,
    ("colar_havaiano", "corpo"): _colar_havaiano,
    ("medalha", "frente"): _medalha,
    ("boia_patinho", "atras"): _boia_atras,
    ("boia_patinho", "frente"): _boia_frente,
    ("capa_heroi", "atras"): _capa_heroi,
    ("asas_anjo", "atras"): _asas_anjo,
    ("asas_borboleta", "atras"): _asas_borboleta,
}

# Ordem de empilhamento dentro de uma camada: roupa, depois rosto,
# depois chapéu (o vidro do capacete fica por cima dos óculos).
_ORDEM_SLOT = {"corpo": 0, "rosto": 1, "cabeca": 2, "efeito": 3}

_cache_camadas = {}


def _camada(item_id, camada, ovo):
    chave = (item_id, camada, ovo)
    sup = _cache_camadas.get(chave)

    if sup is None:
        sup = _temp()
        _DESENHOS[(item_id, camada)](sup, ovo)
        _cache_camadas[chave] = sup

    return sup


def aplicar(sup, ids, camada, ovo):
    """
    Desenha na Surface 100x100 `sup` as partes ESTÁTICAS dos
    cosméticos `ids` que pertencem à `camada` ("atras" | "corpo" |
    "frente"). `ovo` = índice da cor do ovo.
    """
    validos = [i for i in (ids or ()) if (i, camada) in _DESENHOS]
    validos.sort(key=lambda i: _ORDEM_SLOT[CATALOGO[i]["slot"]])

    for item_id in validos:
        sup.blit(_camada(item_id, camada, ovo), (0, 0))


# ============================================================
# EFEITOS ANIMADOS
# ============================================================
# (cx, cy) = centro do ovo na tela, h = altura do corpo do ovo.
# Tudo o que tem transparência usa sprites em cache (por tamanho
# inteiro) e set_alpha() na hora do blit: nada de Surface nova por
# quadro depois que o cache "esquenta".

_cache_efeitos = {}


def _sprite(chave, criar):
    sup = _cache_efeitos.get(chave)

    if sup is None:
        if len(_cache_efeitos) > 400:
            _cache_efeitos.clear()
        sup = criar()
        _cache_efeitos[chave] = sup

    return sup


def _blit_centro(tela, sup, pos, alpha=255):
    sup.set_alpha(max(0, min(255, int(alpha))))
    tela.blit(sup, (round(pos[0] - sup.get_width() / 2),
                    round(pos[1] - sup.get_height() / 2)))


# ---------------- nuvenzinha ----------------

def _nuvem_sprite(h):
    r1, r2 = max(3, round(0.09 * h)), max(4, round(0.12 * h))
    dx = round(0.12 * h)
    dy = round(0.06 * h)
    borda = 2 if h >= 80 else 1
    larg = 2 * (dx + r1 + borda) + 2
    alt = 2 * (r2 + borda) + dy + 2
    sup = pygame.Surface((larg, alt), pygame.SRCALPHA)
    cx, cy = larg // 2, r2 + borda + 1
    circulos = (((cx - dx, cy + dy), r1), ((cx, cy), r2), ((cx + dx, cy + dy), r1))

    for c, r in circulos:
        pygame.draw.circle(sup, (180, 190, 210), c, r + borda)
    for c, r in circulos:
        pygame.draw.circle(sup, (235, 240, 250), c, r)
    # barriguinha reta e sombra
    pygame.draw.circle(sup, (250, 252, 255), (cx - r2 // 3, cy - r2 // 3),
                       max(1, r2 // 3))
    return sup, (cx, cy)


def _nuvenzinha(tela, cx, cy, h, t, fase):
    # A nuvem fica um pouco mais alta que no design (-0.93h em vez de
    # -0.78h) para não bater nos chapéus altos. As gotas caem ATRÁS do
    # avatar: "pingam" no chapéu/cabeça em vez de atravessar o rosto.
    bal = math.sin(2 * t) * 0.02 * h

    if fase == "atras":
        esp = 2 if h >= 70 else 1
        comp = 0.05 * h
        for i, dx in enumerate((-0.10, 0.01, 0.11)):
            p = (t / 0.6 + i / 3) % 1
            y = cy - 0.80 * h + (0.26 * h) * p + bal
            x = cx + dx * h
            pygame.draw.line(tela, (90, 160, 255), (x, y), (x, y + comp), esp)
        return

    # raiozinho a cada ~8 s, por 0.1 s
    if (t % 8.0) < 0.1:
        x0, y0 = cx + 0.03 * h, cy - 0.82 * h + bal
        s = 0.06 * h
        pontos = [(x0, y0), (x0 - s, y0 + s * 1.2), (x0 + s * 0.5, y0 + s * 1.5),
                  (x0 - s * 0.6, y0 + s * 3.0)]
        esp = 3 if h >= 70 else 2
        pygame.draw.lines(tela, (200, 150, 20), False, pontos, esp + 2)
        pygame.draw.lines(tela, (255, 235, 70), False, pontos, esp)

    sup, (ox, oy) = _sprite(("nuvem", round(h)), lambda: _nuvem_sprite(h))
    tela.blit(sup, (round(cx - ox), round(cy - 0.96 * h + bal - oy)))


# ---------------- notas musicais ----------------

_CORES_NOTAS = [(120, 200, 255), (255, 200, 80), (180, 120, 240)]


def _nota_sprite(h, cor):
    r = max(2, round(0.04 * h))
    haste = max(5, round(0.12 * h))
    esp = max(1, round(r * 0.5))
    larg = r * 2 + haste // 2 + 4
    alt = haste + r + 4
    sup = pygame.Surface((larg, alt), pygame.SRCALPHA)
    borda = escurecer(cor, 80)
    bx, by = r + 1, alt - r - 2
    hx = bx + r - 1
    # contorno
    pygame.draw.ellipse(sup, borda, (bx - r - 1, by - r, 2 * r + 2, 2 * r + 1))
    pygame.draw.line(sup, borda, (hx + 1, by), (hx + 1, by - haste), esp + 2)
    pygame.draw.polygon(sup, borda, [(hx, by - haste - 1), (hx + haste // 2 + 1, by - haste + haste // 3),
                                     (hx + haste // 2 + 1, by - haste + haste // 3 + esp + 2),
                                     (hx, by - haste + esp + 2)])
    # nota
    pygame.draw.ellipse(sup, cor, (bx - r, by - r + 1, 2 * r, 2 * r - 1))
    pygame.draw.line(sup, cor, (hx + 1, by), (hx + 1, by - haste + 1), esp)
    pygame.draw.polygon(sup, cor, [(hx + 1, by - haste), (hx + haste // 2, by - haste + haste // 3 + 1),
                                   (hx + haste // 2, by - haste + haste // 3 + esp),
                                   (hx + 1, by - haste + esp)])
    return sup


def _aura_notas(tela, cx, cy, h, t):
    hq = round(h)
    for i in range(4):
        p = (t / 2.0 + i / 4) % 1
        lado = -1 if i % 2 == 0 else 1
        cor = _CORES_NOTAS[i % 3]
        sup = _sprite(("nota", hq, i % 3), lambda: _nota_sprite(h, cor))
        x = cx + lado * 0.5 * h + math.sin(p * 6.28 + i) * 0.05 * h
        y = cy + 0.2 * h - 0.85 * h * p
        alpha = 255 * (1 - p) if p > 0.15 else 255 * p / 0.15
        _blit_centro(tela, sup, (x, y), alpha)


# ---------------- estrelinhas ----------------

def _brilho_sprite(tam):
    lado = tam * 2 + 3
    sup = pygame.Surface((lado, lado), pygame.SRCALPHA)
    c = (lado / 2, lado / 2)
    _estrela4(sup, (200, 150, 30), c, tam + 1, 0.4)
    _estrela4(sup, (255, 240, 120), c, tam, 0.34)
    pygame.draw.circle(sup, (255, 255, 255), (round(c[0]), round(c[1])),
                       max(1, tam // 3))
    return sup


def _aura_brilhos(tela, cx, cy, h, t, fase):
    for i in range(3):
        th = 1.5 * t + i * 2.094
        s = math.sin(th)
        if (s < 0) != (fase == "atras"):
            continue
        x = cx + math.cos(th) * 0.62 * h
        y = cy + s * 0.25 * h - 0.1 * h
        tam = max(2, round(0.07 * h * (0.7 + 0.3 * math.sin(6 * t + i))))
        sup = _sprite(("brilho", tam), lambda: _brilho_sprite(tam))
        _blit_centro(tela, sup, (x, y))


# ---------------- corações ----------------

def _coracao_sprite(tam):
    lado = tam + 6
    sup = pygame.Surface((lado, lado), pygame.SRCALPHA)
    c = (lado // 2, lado // 2)
    if tam >= 10:
        coracao(sup, (c[0], c[1] + 1), tam + 3, (170, 40, 80))
    coracao(sup, c, tam, (255, 90, 140))
    r = max(1, tam // 8)
    pygame.draw.circle(sup, (255, 200, 220), (c[0] - tam // 4, c[1] - tam // 6), r)
    return sup


def _aura_coracoes(tela, cx, cy, h, t):
    for i in range(4):
        p = (0.5 * t + i / 4) % 1
        lado = -1 if i % 2 == 0 else 1
        x = cx + lado * 0.45 * h + math.sin(6.28 * p) * 0.06 * h
        y = cy + 0.3 * h - 0.9 * h * p
        tam = max(4, round(0.10 * h * (1 - 0.4 * p)))
        sup = _sprite(("coracao", tam), lambda: _coracao_sprite(tam))
        _blit_centro(tela, sup, (x, y), 255 * (1 - p))


# ---------------- aura dourada ----------------

_PASSOS_AURA = 8


def _aura_sprite(h, k, somar):
    """
    3 elipses concêntricas (255,210,60) com alpha 90/60/35.
    somar=True: versão "pré-multiplicada" (sem alfa) para somar à tela
    com BLEND_RGB_ADD -> a aura BRILHA em fundo escuro/madeira, sem
    ficar cor de barro. somar=False: versão com alfa normal, para
    fundos claros (onde somar deixaria tudo branco).
    """
    escala = 1 + 0.05 * math.sin(k / _PASSOS_AURA * 2 * math.pi)
    largura_max = 1.25 * 0.95 * h * 1.05
    lado_l = int(largura_max) + 4
    lado_a = int(largura_max * 1.1) + 4
    centro = (lado_l / 2, lado_a / 2)
    sup = pygame.Surface((lado_l, lado_a), 0 if somar else pygame.SRCALPHA)

    for mult, alpha in ((1.25, 35), (1.12, 60), (1.0, 90)):
        w = mult * 0.95 * h * escala
        a = w * 1.1
        rect = (centro[0] - w / 2, centro[1] - a / 2, w, a)
        if somar:
            camada = pygame.Surface((lado_l, lado_a))
            cor = tuple(round(c * alpha / 255) for c in (255, 210, 60))
            pygame.draw.ellipse(camada, cor, rect)
            sup.blit(camada, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        else:
            camada = pygame.Surface((lado_l, lado_a), pygame.SRCALPHA)
            pygame.draw.ellipse(camada, (255, 200, 40, alpha + 15), rect)
            sup.blit(camada, (0, 0))

    return sup


def _fundo_claro(tela, x, y):
    """Olha 1 pixel do fundo (antes do avatar) para escolher a aura."""
    w, h = tela.get_size()
    x = min(max(0, int(x)), w - 1)
    y = min(max(0, int(y)), h - 1)
    c = tela.get_at((x, y))
    if c[3] < 255:          # Surface transparente (ícone da loja)
        return True
    return c[0] * 0.3 + c[1] * 0.55 + c[2] * 0.15 > 185


def _aura_dourada(tela, cx, cy, h, t, fase):
    hq = round(h)
    if fase == "atras":
        # pulso 1 + 0.05·sen(3t) em passos (sprites em cache)
        k = round((3 * t) / (2 * math.pi) * _PASSOS_AURA) % _PASSOS_AURA
        somar = not _fundo_claro(tela, cx - 0.52 * h, cy + 0.1 * h)
        sup = _sprite(("aura", hq, k, somar), lambda: _aura_sprite(h, k, somar))
        pos = (round(cx - sup.get_width() / 2), round(cy - sup.get_height() / 2))
        if somar:
            tela.blit(sup, pos, special_flags=pygame.BLEND_RGB_ADD)
        else:
            tela.blit(sup, pos)
        return

    # 6 faíscas subindo pelos lados do ovo
    tam = 3 if h >= 90 else 2
    for i in range(6):
        p = (0.45 * t + i / 6) % 1
        lado = -1 if i % 2 == 0 else 1
        raio = (0.44 + 0.07 * (i // 2)) * h * (1 - 0.35 * p)
        x = cx + lado * raio + math.sin(t * 2 + i) * 0.03 * h
        y = cy + 0.42 * h - 1.0 * h * p
        if p > 0.9:
            continue
        cor = (255, 250, 200) if (i + int(t * 6)) % 3 else (255, 255, 255)
        tela.fill(cor, (round(x), round(y), tam, tam))
        if tam == 3 and p < 0.5:
            tela.fill((255, 210, 60), (round(x) + 1, round(y) - 2, 1, 7))
            tela.fill((255, 210, 60), (round(x) - 2, round(y) + 1, 7, 1))


# ---------------- auréola (bônus, sem efeito equipado) ----------------

def _aureola_brilho(tela, cx, cy, h, t):
    """Uma faísca que passeia pelo anel da auréola."""
    s = h / 74
    th = t * 1.6
    qx = 49 + math.cos(th) * 16
    qy = 5 + math.sin(th) * 4
    x = cx + (qx - 48) * s
    y = cy + (qy - 51) * s + math.sin(t * 4 * math.pi) * s
    tam = max(2, round(2.2 * s * (0.8 + 0.4 * abs(math.sin(t * 3)))))
    sup = _sprite(("brilho", tam), lambda: _brilho_sprite(tam))
    _blit_centro(tela, sup, (x, y), 230)


def desenhar_efeito(tela, ids, centro, altura, t, fase):
    """
    Efeitos ANIMADOS em volta do ovo com centro `centro` e altura do
    corpo `altura` (px). fase = "atras" (antes do avatar) ou "frente"
    (depois). Barato: só primitivas e sprites em cache.
    """
    if not ids:
        return

    cx, cy = centro
    h = float(altura)
    tem_efeito = False

    for item_id in ids:
        if item_id == "nuvenzinha":
            tem_efeito = True
            _nuvenzinha(tela, cx, cy, h, t, fase)
        elif item_id == "aura_notas":
            tem_efeito = True
            if fase == "frente":
                _aura_notas(tela, cx, cy, h, t)
        elif item_id == "aura_brilhos":
            tem_efeito = True
            _aura_brilhos(tela, cx, cy, h, t, fase)
        elif item_id == "aura_coracoes":
            tem_efeito = True
            if fase == "frente":
                _aura_coracoes(tela, cx, cy, h, t)
        elif item_id == "aura_dourada":
            tem_efeito = True
            _aura_dourada(tela, cx, cy, h, t, fase)
        elif item_id in EFEITOS_EXTRA:
            tem_efeito = True
            EFEITOS_EXTRA[item_id](tela, cx, cy, h, t, fase)

    if not tem_efeito and fase == "frente" and "aureola" in ids:
        _aureola_brilho(tela, cx, cy, h, t)


# ============================================================
# ÍCONES DA LOJA
# ============================================================

_cache_icones = {}

# Ícone de cada efeito: (altura do ovo, y do ovo, altura usada no
# efeito, y do centro do efeito) em frações do quadro, e os momentos
# "congelados" que são sobrepostos (mais partículas = ícone mais rico).
# O efeito é desenhado maior que o ovo para ficar legível no card.
_ICONE_EFEITO = {
    "nuvenzinha": (0.40, 0.72, 0.60, 0.80, (8.04,)),   # com o raiozinho
    "aura_notas": (0.46, 0.56, 0.85, 0.62, (0.25, 1.25)),
    "aura_brilhos": (0.46, 0.55, 0.70, 0.58, (0.9, 1.6)),
    "aura_coracoes": (0.46, 0.56, 0.95, 0.66, (0.1, 0.6)),
    "aura_dourada": (0.46, 0.54, 0.60, 0.54, (0.5,)),
}


def _manequim(ovo, slot):
    """Ovo semitransparente (com rosto apagadinho) para vestir o item."""
    sup = _temp()
    sup.blit(assets.OVOS[ovo], (0, 0))
    if slot in ("rosto", "cabeca"):
        sup.blit(assets.OLHOS[0], (0, 0))
    if slot == "rosto":
        sup.blit(assets.BOCAS[0], (0, 0))
    sup.set_alpha(110)
    fantasma = _temp()
    fantasma.blit(sup, (0, 0))
    return fantasma


def _escalar(sup, tamanho):
    """Aumenta em pixels "duros" (estilo pixel art) e ajusta suave."""
    w = sup.get_width()
    if tamanho == w:
        return sup
    if tamanho > w:
        k = -(-tamanho // w)
        sup = pygame.transform.scale(sup, (w * k, w * k))
    return pygame.transform.smoothscale(sup, (tamanho, tamanho))


def _icone_item(item_id, tamanho, ovo):
    dados = CATALOGO[item_id]
    item = _temp()
    for camada in ("atras", "corpo", "frente"):
        if camada in dados["camadas"]:
            item.blit(_camada(item_id, camada, ovo), (0, 0))

    # enquadramento: caixa do item, quadrada, com uma folga
    caixa = item.get_bounding_rect()
    if item_id == "capacete_espacial":
        caixa = pygame.Rect(0, 0, 100, 100)
    lado = max(caixa.w, caixa.h, 30)
    lado = round(lado * 1.18) + 4
    quad = pygame.Rect(0, 0, lado, lado)
    quad.center = caixa.center

    # desenha num quadro com margem para o recorte poder "sair" do 100x100
    M = 40
    grande = pygame.Surface((100 + 2 * M, 100 + 2 * M), pygame.SRCALPHA)
    atras = _temp()
    frente = _temp()
    if "atras" in dados["camadas"]:
        atras.blit(_camada(item_id, "atras", ovo), (0, 0))
    for camada in ("corpo", "frente"):
        if camada in dados["camadas"]:
            frente.blit(_camada(item_id, camada, ovo), (0, 0))
    # o que fica atrás do ovo não aparece através do manequim
    fora = pygame.Surface((100, 100), pygame.SRCALPHA)
    fora.fill((255, 255, 255, 255))
    pygame.draw.ellipse(fora, _TRANSP, (15, 14, 67, 74))
    atras.blit(fora, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    grande.blit(atras, (M, M))
    grande.blit(_manequim(ovo, dados["slot"]), (M, M))
    grande.blit(frente, (M, M))

    quad.move_ip(M, M)
    quad.clamp_ip(grande.get_rect())
    recorte = grande.subsurface(quad).copy()
    return _escalar(recorte, tamanho)


def _icone_efeito(item_id, tamanho, ovo):
    # desenha em alta resolução e reduz (fica suave e bem legível)
    S = max(tamanho * 2, 160)
    sup = pygame.Surface((S, S), pygame.SRCALPHA)
    h_ovo, y_ovo, h_ef, y_ef, tempos = _ICONE_EFEITO[item_id]
    cx = S * 0.5
    h, cy = S * h_ovo, S * y_ovo
    centro_ef, h_ef = (cx, S * y_ef), S * h_ef

    ovo_img = _temp()
    ovo_img.blit(assets.OVOS[ovo], (0, 0))
    ovo_img.blit(assets.OLHOS[0], (0, 0))
    ovo_img.blit(assets.BOCAS[0], (0, 0))
    lado = round(100 * h / 74)
    ovo_img = pygame.transform.smoothscale(ovo_img, (lado, lado))
    ovo_img.set_alpha(150)

    for t in tempos:
        desenhar_efeito(sup, (item_id,), centro_ef, h_ef, t, "atras")
    s = h / 74
    sup.blit(ovo_img, (round(cx - 48 * s), round(cy - 51 * s)))
    for t in tempos:
        desenhar_efeito(sup, (item_id,), centro_ef, h_ef, t, "frente")
    return pygame.transform.smoothscale(sup, (tamanho, tamanho))


def icone(item_id, tamanho, ovo=1):
    """
    Surface quadrada `tamanho` x `tamanho` para o card da loja: o item
    bem enquadrado sobre um ovo-manequim semitransparente.
    """
    tamanho = max(8, int(tamanho))
    if not 0 <= ovo < len(assets.OVOS):
        ovo = 1
    chave = (item_id, tamanho, ovo)
    sup = _cache_icones.get(chave)

    if sup is not None:
        return sup

    if item_id not in CATALOGO:
        sup = pygame.Surface((tamanho, tamanho), pygame.SRCALPHA)
    elif CATALOGO[item_id]["slot"] in ICONE_SLOT:
        sup = ICONE_SLOT[CATALOGO[item_id]["slot"]](item_id, tamanho, ovo)
    elif CATALOGO[item_id]["slot"] == "efeito":
        sup = _icone_efeito(item_id, tamanho, ovo)
    else:
        sup = _icone_item(item_id, tamanho, ovo)

    if len(_cache_icones) > 300:
        _cache_icones.clear()
    _cache_icones[chave] = sup
    return sup


# Coleção nova (registra-se no CATALOGO acima)
from core import cosmeticos_novos  # noqa: E402,F401
# Aparência extra: cabelos/olhos/bocas/cores/roupas (registra-se também)
from core import visual_extra  # noqa: E402,F401
