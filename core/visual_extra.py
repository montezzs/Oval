import math
import random

import pygame

from core import assets
from core import cosmeticos as c
from core.ui import estrela

# ============================================================
# APARÊNCIA EXTRA (vendida na loja, fora do criador)
# ============================================================
# Cabelos, olhos, bocas e cores de ovo NOVOS que SUBSTITUEM a parte
# base do ovo (Jogador.compor cuida disso), e roupas (slot "roupa",
# desenhadas como os outros cosméticos). Tudo procedural no quadro
# 100x100: corpo do ovo = elipse (15,14,67,74), olhos ~ y 27-45,
# boca ~ y 56-80.
#
# Slots que substituem a parte base:
#   "cabelo_x"  -> no lugar de assets.CABELOS[cabelo]
#   "olhos_x"   -> no lugar de assets.OLHOS[olho] (OLHO_FECHADO continua)
#   "boca_x"    -> no lugar de assets.BOCAS[boca] (triste/aberta continuam)
#   "cor_x"     -> no lugar de assets.OVOS[ovo] (e muda Jogador.cor)
# Slot novo de cosmético comum:
#   "roupa"     -> camisetas, vestidos... (camadas "atras"/"corpo")

SLOT_CABELO = "cabelo_x"
SLOT_OLHOS = "olhos_x"
SLOT_BOCA = "boca_x"
SLOT_COR = "cor_x"
SLOT_ROUPA = "roupa"
SLOTS_TROCA = (SLOT_CABELO, SLOT_OLHOS, SLOT_BOCA, SLOT_COR)

# Grupos da aba VISUAL da loja (rótulo, slot)
GRUPOS_LOJA = [("CABELO", SLOT_CABELO), ("OLHOS", SLOT_OLHOS), ("BOCA", SLOT_BOCA),
               ("COR", SLOT_COR), ("ROUPA", SLOT_ROUPA)]

DESCRICOES = {
    SLOT_CABELO: "Troca o cabelo do seu ovo em todos os jogos!",
    SLOT_OLHOS: "Troca os olhos do seu ovo em todos os jogos!",
    SLOT_BOCA: "Troca a boca do seu ovo em todos os jogos!",
    SLOT_COR: "Pinta o seu ovo de uma cor nova em todos os jogos!",
    SLOT_ROUPA: "Uma roupa nova para o seu ovo usar em todos os jogos!",
}

_item = c._item
_forma = c._forma
_temp = c._temp

EL, ER = (36, 36), (61, 36)          # centro dos olhos
OVO = (15, 14, 67, 74)
OVO_GORDO = (12, 11, 73, 80)         # ovo + volume do cabelo
CLARO_LINHA = (235, 235, 242)        # linhas do rosto em ovos escuros

ARCO = [(240, 60, 70), (255, 150, 40), (255, 220, 50), (90, 200, 90), (70, 150, 255),
        (160, 90, 230)]


def _i(nome, slot, preco, raridade, loja=True, camadas=(), esconde=None, esconde_cabelo=False):
    d = _item(nome, slot, preco, raridade, camadas, esconde_cabelo, loja, esconde)
    d["descricao"] = DESCRICOES.get(slot, "")
    return d


# ============================================================
# CATÁLOGO
# ============================================================

ITENS = {
    # ---------------- CABELOS ----------------
    "cab_topete": _i("TOPETE", SLOT_CABELO, 80, "COMUM"),
    "cab_franja": _i("FRANJINHA", SLOT_CABELO, 90, "COMUM"),
    "cab_coque": _i("COQUE", SLOT_CABELO, 110, "COMUM"),
    "cab_rabo": _i("RABO DE CAVALO", SLOT_CABELO, 160, "INCOMUM"),
    "cab_marias": _i("MARIA-CHIQUINHA", SLOT_CABELO, 190, "INCOMUM"),
    "cab_black": _i("BLACK POWER", SLOT_CABELO, 260, "INCOMUM"),
    "cab_moicano": _i("MOICANO PUNK", SLOT_CABELO, 380, "RARO"),
    "cab_cachos": _i("CACHINHOS DOURADOS", SLOT_CABELO, 450, "RARO"),
    "cab_fogo": _i("CABELO DE FOGO", SLOT_CABELO, 1100, "EPICO"),
    "cab_arco_iris": _i("CABELO ARCO-ÍRIS", SLOT_CABELO, 2200, "LENDARIO"),

    # ---------------- OLHOS ----------------
    "olh_bolinha": _i("OLHINHOS DE BOLINHA", SLOT_OLHOS, 60, "COMUM"),
    "olh_sono": _i("OLHOS SONOLENTOS", SLOT_OLHOS, 80, "COMUM"),
    "olh_cilios": _i("CÍLIOS LONGOS", SLOT_OLHOS, 100, "COMUM"),
    "olh_brilho": _i("OLHOS BRILHANTES", SLOT_OLHOS, 200, "INCOMUM"),
    "olh_gato": _i("OLHOS DE GATO", SLOT_OLHOS, 260, "INCOMUM"),
    "olh_coracao": _i("OLHOS APAIXONADOS", SLOT_OLHOS, 400, "RARO"),
    "olh_espiral": _i("OLHOS HIPNÓTICOS", SLOT_OLHOS, 480, "RARO"),
    "olh_robo": _i("OLHOS DE ROBÔ", SLOT_OLHOS, 900, "EPICO"),
    "olh_galaxia": _i("OLHOS DE GALÁXIA", SLOT_OLHOS, 2400, "LENDARIO"),
    "olh_estrela": _i("OLHOS DE ESTRELA", SLOT_OLHOS, 0, "EPICO", loja=False),

    # ---------------- BOCAS ----------------
    "boc_sorriso": _i("SORRISÃO", SLOT_BOCA, 60, "COMUM"),
    "boc_gato": _i("BOQUINHA DE GATO", SLOT_BOCA, 70, "COMUM"),
    "boc_assobio": _i("ASSOBIANDO", SLOT_BOCA, 90, "COMUM"),
    "boc_batom": _i("BATOM VERMELHO", SLOT_BOCA, 180, "INCOMUM"),
    "boc_vampiro": _i("PRESINHAS DE VAMPIRO", SLOT_BOCA, 250, "INCOMUM"),
    "boc_aparelho": _i("APARELHO NOS DENTES", SLOT_BOCA, 360, "RARO"),
    "boc_pirulito": _i("PIRULITO", SLOT_BOCA, 520, "RARO"),
    "boc_ouro": _i("DENTE DE OURO", SLOT_BOCA, 850, "EPICO"),
    "boc_chiclete": _i("BOLA DE CHICLETE", SLOT_BOCA, 1200, "EPICO"),
    "boc_diamante": _i("SORRISO DE DIAMANTE", SLOT_BOCA, 2000, "LENDARIO"),

    # ---------------- CORES DO OVO ----------------
    "cor_rosa": _i("ROSA CHICLETE", SLOT_COR, 90, "COMUM"),
    "cor_laranja": _i("LARANJA", SLOT_COR, 90, "COMUM"),
    "cor_gema": _i("AMARELO GEMA", SLOT_COR, 110, "COMUM"),
    "cor_menta": _i("VERDE MENTA", SLOT_COR, 160, "INCOMUM"),
    "cor_lilas": _i("LILÁS", SLOT_COR, 190, "INCOMUM"),
    "cor_codorna": _i("OVO DE CODORNA", SLOT_COR, 240, "INCOMUM"),
    "cor_chocolate": _i("CHOCOLATE", SLOT_COR, 380, "RARO"),
    "cor_preto": _i("PRETO NOITE", SLOT_COR, 420, "RARO"),
    "cor_dourado": _i("DOURADO", SLOT_COR, 950, "EPICO"),
    "cor_galaxia": _i("GALÁXIA", SLOT_COR, 1400, "EPICO"),
    "cor_arco_iris": _i("ARCO-ÍRIS", SLOT_COR, 2500, "LENDARIO"),
    "cor_abobora": _i("ABÓBORA DE HALLOWEEN", SLOT_COR, 0, "EPICO", loja=False),

    # ---------------- ROUPAS ----------------
    "rou_listrada": _i("CAMISETA LISTRADA", SLOT_ROUPA, 80, "COMUM", camadas=("corpo",)),
    "rou_macacao": _i("MACACÃO JEANS", SLOT_ROUPA, 120, "COMUM", camadas=("corpo",)),
    "rou_futebol": _i("CAMISA DE FUTEBOL", SLOT_ROUPA, 160, "INCOMUM", camadas=("corpo",)),
    "rou_vestido": _i("VESTIDO DE BOLINHAS", SLOT_ROUPA, 180, "INCOMUM", camadas=("corpo",)),
    "rou_moletom": _i("MOLETOM COM CAPUZ", SLOT_ROUPA, 230, "INCOMUM",
                      camadas=("atras", "corpo")),
    "rou_quimono": _i("QUIMONO DE KARATÊ", SLOT_ROUPA, 380, "RARO", camadas=("corpo",)),
    "rou_terno": _i("TERNO ELEGANTE", SLOT_ROUPA, 450, "RARO", camadas=("corpo",)),
    "rou_astronauta": _i("TRAJE DE ASTRONAUTA", SLOT_ROUPA, 1000, "EPICO", camadas=("corpo",)),
    "rou_armadura": _i("ARMADURA DE CAVALEIRO", SLOT_ROUPA, 1400, "EPICO", camadas=("corpo",)),
    "rou_manto": _i("MANTO REAL", SLOT_ROUPA, 2300, "LENDARIO", camadas=("atras", "corpo")),
    "rou_sueter_natal": _i("SUÉTER DE NATAL", SLOT_ROUPA, 0, "RARO", loja=False,
                           camadas=("corpo",)),

    # ---------------- CHAPÉUS EXCLUSIVOS (eventos) ----------------
    "gorro_natal": _item("GORRO DE NATAL", "cabeca", 0, "RARO", ("frente",), True, loja=False),
    "chapeu_bruxa": _item("CHAPÉU DE BRUXA", "cabeca", 0, "EPICO", ("frente",), True, loja=False),
    "orelhas_coelho": _item("ORELHAS DE COELHO DE PÁSCOA", "cabeca", 0, "RARO", ("frente",),
                            loja=False, esconde={0, 6, 7}),
}

# Não vendem na loja: dados por conquistas / eventos / caixa surpresa.
# (Aparecem na loja para equipar assim que estiverem no inventário.)
EXCLUSIVOS = ["olh_estrela", "cor_abobora", "rou_sueter_natal", "gorro_natal", "chapeu_bruxa",
              "orelhas_coelho"]


# ============================================================
# FERRAMENTAS
# ============================================================

def _y_topo(x):
    """y do topo do corpo do ovo na coluna x."""
    k = (x - 48.5) / 33.5
    if abs(k) >= 1:
        return 51
    return 51 - 37 * math.sqrt(1 - k * k)


def _calota(y_max, rect=OVO_GORDO):
    """Silhueta: ovo (com volume) do topo até y_max."""
    def f(s, cor):
        pygame.draw.ellipse(s, cor, rect)
        c._apagar_abaixo(s, y_max)
    return f


def _juntar(*fs):
    def f(s, cor):
        for g in fs:
            g(s, cor)
    return f


def _faixas_y(cores, y0, y1, onda=0.0):
    """detalhes(): pinta faixas horizontais (opcionalmente onduladas)."""
    def f(s):
        n = len(cores)
        passo = (y1 - y0) / n
        for x in range(100):
            d = onda * math.sin(x / 7.0)
            for k, cor in enumerate(cores):
                a = y0 + k * passo + d
                b = y0 + (k + 1) * passo + d
                if k == 0:
                    a = 0
                if k == n - 1:
                    b = 100
                s.fill(cor, (x, round(a), 1, max(1, round(b) - round(a))))
    return f


def _clarear_linhas(sup):
    """Troca as linhas quase pretas por claras (rosto em ovo escuro)."""
    r = sup.get_bounding_rect()
    if not r.w:
        return
    sup.lock()
    for y in range(r.top, r.bottom):
        for x in range(r.left, r.right):
            p = sup.get_at((x, y))
            if p.a and p.r < 80 and p.g < 80 and p.b < 80:
                sup.set_at((x, y), (*CLARO_LINHA, p.a))
    sup.unlock()


_cache = {}


def _parte(chave, criar):
    sup = _cache.get(chave)
    if sup is None:
        if len(_cache) > 300:
            _cache.clear()
        sup = criar()
        _cache[chave] = sup
    return sup


# ============================================================
# CORES DO OVO
# ============================================================

def _galaxia(s):
    for (x, y, r, cor) in ((30, 40, 18, (150, 70, 220)), (64, 70, 20, (60, 120, 240)),
                           (60, 28, 11, (240, 100, 210)), (28, 76, 11, (110, 70, 220))):
        t = _temp()
        for k in range(r, 0, -3):
            pygame.draw.circle(t, (*cor, 22), (x, y), k)
        s.blit(t, (0, 0))
    rnd = random.Random(7)
    for _ in range(26):
        x, y = rnd.randint(16, 81), rnd.randint(15, 87)
        cor = rnd.choice(((255, 255, 255), (200, 220, 255), (255, 230, 170)))
        s.fill(cor, (x, y, 1, 1))
    for x, y, r in ((68, 24, 4), (25, 58, 3), (58, 80, 3)):
        c._estrela4(s, (255, 255, 255), (x, y), r, 0.3)


def _dourado(s):
    t = _temp()
    pygame.draw.ellipse(t, (190, 130, 20, 130), OVO)
    pygame.draw.ellipse(t, (0, 0, 0, 0), (10, 8, 67, 74))
    s.blit(t, (0, 0))
    t = _temp()
    pygame.draw.ellipse(t, (255, 240, 160, 170), (24, 22, 16, 30))
    s.blit(t, (0, 0))
    pygame.draw.ellipse(s, (255, 250, 215), (27, 26, 6, 12))
    c._estrela4(s, (255, 255, 240), (66, 26), 5, 0.28)
    c._estrela4(s, (255, 255, 240), (30, 70), 3, 0.3)


def _preto(s):
    pygame.draw.arc(s, (95, 95, 115), (22, 20, 30, 40), math.radians(110), math.radians(170), 3)
    s.fill((120, 120, 140), (27, 24, 3, 3))


def _chocolate(s):
    pygame.draw.arc(s, (165, 110, 70), (22, 20, 30, 40), math.radians(110), math.radians(170), 3)
    # cobertura escorrendo
    pontos = [(0, 0), (100, 0), (100, 24)]
    for x in range(96, 0, -8):
        pontos += [(x, 24 + (6 if x % 16 else 11)), (x - 4, 24)]
    pontos += [(0, 24)]
    t = _temp()
    pygame.draw.polygon(t, (90, 50, 28), pontos)
    for x in range(8, 96, 16):
        pygame.draw.circle(t, (90, 50, 28), (x - 4, 35), 2)
    s.blit(t, (0, 0))
    for x, y, cor in ((40, 18, (255, 90, 110)), (52, 22, (120, 200, 255)), (60, 17, (255, 230, 90)),
                      (33, 25, (140, 230, 140)), (65, 25, (255, 255, 255))):
        s.fill(cor, (x, y, 3, 2))


def _codorna(s):
    rnd = random.Random(3)
    for _ in range(34):
        x, y = rnd.randint(16, 81), rnd.randint(15, 87)
        r = rnd.choice((1, 1, 1, 2, 2))
        pygame.draw.circle(s, rnd.choice(((160, 120, 85), (135, 100, 70), (185, 150, 110))), (x, y), r)


def _arco_iris(s):
    _faixas_y(ARCO, 14, 88, onda=2.5)(s)
    t = _temp()
    pygame.draw.ellipse(t, (255, 255, 255, 90), (24, 22, 14, 26))
    s.blit(t, (0, 0))


def _abobora(s):
    esc = (205, 90, 15)
    for rect in ((30, 13, 37, 76), (41, 13, 15, 76), (20, 13, 57, 76)):
        pygame.draw.ellipse(s, esc, rect, 2)
    t = _temp()
    pygame.draw.ellipse(t, (255, 190, 90, 110), (24, 24, 10, 22))
    s.blit(t, (0, 0))


CORES = {
    "cor_rosa": dict(rgb=(255, 125, 185)),
    "cor_laranja": dict(rgb=(255, 145, 40)),
    "cor_gema": dict(rgb=(255, 205, 40)),
    "cor_menta": dict(rgb=(135, 225, 185)),
    "cor_lilas": dict(rgb=(185, 145, 240)),
    "cor_codorna": dict(rgb=(238, 224, 198), desenho=_codorna),
    "cor_chocolate": dict(rgb=(130, 80, 48), desenho=_chocolate, escuro=True),
    "cor_preto": dict(rgb=(42, 42, 54), desenho=_preto, escuro=True),
    "cor_dourado": dict(rgb=(240, 190, 50), desenho=_dourado),
    "cor_galaxia": dict(rgb=(38, 28, 88), desenho=_galaxia, escuro=True, rep=(90, 60, 190)),
    "cor_arco_iris": dict(rgb=(255, 255, 255), desenho=_arco_iris, rep=(240, 110, 170)),
    "cor_abobora": dict(rgb=(245, 135, 30), desenho=_abobora),
}


def rgb(cor_id):
    """Cor "de referência" (Jogador.cor) de uma cor extra, ou None."""
    d = CORES.get(cor_id)
    if d is None:
        return None
    return d.get("rep", d["rgb"])


def escuro(cor_id):
    d = CORES.get(cor_id)
    return bool(d and d.get("escuro"))


def ovo_para_cosmeticos(ovo, cor_id):
    """Índice de ovo usado pelos cosméticos (contornos "no branco")."""
    cor = rgb(cor_id)
    if cor is None:
        return ovo
    if sum(cor) > 600:
        return c.OVO_BRANCO
    return 1 if ovo == c.OVO_BRANCO else ovo


def _criar_corpo(cor_id):
    d = CORES[cor_id]
    base = assets.OVOS[c.OVO_BRANCO]
    sup = base.copy()
    sup.fill(d["rgb"], special_flags=pygame.BLEND_RGB_MULT)
    if d.get("desenho"):
        t = _temp()
        d["desenho"](t)
        c._recortar(t, base)
        sup.blit(t, (0, 0))
    return sup


def corpo(cor_id):
    """Corpo do ovo (100x100) pintado com a cor extra."""
    return _parte(("corpo", cor_id), lambda: _criar_corpo(cor_id))


# ============================================================
# CABELOS
# ============================================================
# Cada cabelo tem até 3 partes: "atras" (antes do corpo), "topo"
# (em cima da cabeça, some embaixo dos chapéus) e "lados" (fica
# visível mesmo com chapéu: marias, rabo, cachos laterais).

def _topete_topo(sup):
    preto, borda, brilho = (40, 35, 50), (15, 12, 20), (100, 95, 125)

    def forma(s, cor):
        _cabelo_liso(recuo=5, y_lados=30)(s, cor)
        pygame.draw.ellipse(s, cor, (28, 3, 42, 18))
        pygame.draw.circle(s, cor, (65, 9), 7)
        pygame.draw.polygon(s, cor, [(26, 17), (40, 6), (44, 16)])

    def detalhes(s):
        pygame.draw.arc(s, brilho, (34, 5, 30, 14), math.radians(40), math.radians(150), 2)
        pygame.draw.arc(s, brilho, (58, 4, 12, 12), math.radians(-40), math.radians(90), 1)

    sup.blit(_forma(forma, preto, borda, detalhes=detalhes), (0, 0))


def _franja_topo(sup):
    cor, borda, fio = (135, 85, 45), (80, 45, 20), (170, 115, 65)

    def forma(s, cr):
        pygame.draw.ellipse(s, cr, OVO_GORDO)
        c._apagar_abaixo(s, 25)
        # mechas da franja
        for x in range(27, 72, 7):
            pygame.draw.polygon(s, cr, [(x - 4, 24), (x + 4, 24), (x + 1, 31)])
        # mechas dos lados até a altura dos olhos
        lado = _temp()
        pygame.draw.ellipse(lado, cr, OVO_GORDO)
        pygame.draw.ellipse(lado, (0, 0, 0, 0), (19, 14, 59, 74))
        c._apagar_abaixo(lado, 46)
        s.blit(lado, (0, 0))

    def detalhes(s):
        for x in (34, 44, 54, 63):
            pygame.draw.line(s, fio, (x - 2, 13), (x, 22), 1)
        pygame.draw.arc(s, (200, 145, 90), (26, 13, 30, 14), math.radians(90), math.radians(160), 2)

    sup.blit(_forma(forma, cor, borda, detalhes=detalhes), (0, 0))


def _cabelo_liso(cor=None, borda=None, recuo=7, y_lados=34):
    """Cabelo "colado" na cabeça: meia-lua do topo descendo pelos lados."""
    def forma(s, cr):
        pygame.draw.ellipse(s, cr, OVO_GORDO)
        pygame.draw.ellipse(s, (0, 0, 0, 0), (17, 11 + recuo, 63, 74))
        c._apagar_abaixo(s, y_lados)
    return forma


def _coque_topo(sup):
    cor, borda, fio = (95, 55, 35), (55, 28, 15), (135, 85, 55)

    def detalhes(s):
        for x in (30, 40, 58, 68):
            pygame.draw.line(s, fio, (48, 12), (x, 22), 1)

    sup.blit(_forma(_cabelo_liso(recuo=10), cor, borda, detalhes=detalhes), (0, 0))

    def bola(s, cr):
        pygame.draw.circle(s, cr, (48, 8), 8)

    sup.blit(_forma(bola, cor, borda, detalhes=lambda s: pygame.draw.arc(
        s, fio, (42, 2, 12, 12), math.radians(20), math.radians(200), 1)), (0, 0))
    pygame.draw.rect(sup, (255, 100, 150), (41, 13, 15, 4), border_radius=2)
    pygame.draw.rect(sup, (190, 50, 100), (41, 13, 15, 4), 1, border_radius=2)


def _rabo_topo(sup):
    cor, borda, fio = (245, 200, 90), (185, 135, 40), (255, 230, 150)

    def detalhes(s):
        for x in (28, 38, 48, 58):
            pygame.draw.line(s, fio, (x, 14), (x + 12, 22), 1)

    sup.blit(_forma(_cabelo_liso(recuo=10), cor, borda, detalhes=detalhes), (0, 0))


def _rabo_atras(sup):
    cor, borda = (245, 200, 90), (185, 135, 40)

    def forma(s, cr):
        for (x, y, r) in ((70, 16, 8), (79, 24, 8), (85, 34, 7), (88, 44, 6), (87, 53, 5),
                          (84, 60, 3)):
            pygame.draw.circle(s, cr, (x, y), r)

    def detalhes(s):
        pygame.draw.arc(s, (255, 235, 160), (74, 20, 16, 30), math.radians(-60), math.radians(60), 2)

    sup.blit(_forma(forma, cor, borda, detalhes=detalhes), (0, 0))


def _rabo_lados(sup):
    # lacinho que prende o rabo
    pygame.draw.circle(sup, (140, 30, 50), (72, 17), 4)
    pygame.draw.circle(sup, (230, 60, 90), (72, 17), 3)


def _marias_topo(sup):
    cor, borda = (215, 95, 45), (140, 50, 20)

    def detalhes(s):
        pygame.draw.line(s, borda, (48, 11), (48, 21), 1)
        pygame.draw.arc(s, (250, 150, 90), (26, 13, 22, 14), math.radians(100), math.radians(170), 2)

    sup.blit(_forma(_cabelo_liso(recuo=10), cor, borda, detalhes=detalhes), (0, 0))


def _marias_lados(sup):
    cor, borda = (215, 95, 45), (140, 50, 20)

    def forma(s, cr):
        pygame.draw.ellipse(s, cr, (3, 24, 15, 30))
        pygame.draw.ellipse(s, cr, (79, 24, 15, 30))
        pygame.draw.polygon(s, cr, [(3, 50), (11, 48), (8, 60)])
        pygame.draw.polygon(s, cr, [(94, 50), (86, 48), (89, 60)])

    def detalhes(s):
        for x in (7, 84):
            pygame.draw.arc(s, (250, 150, 90), (x, 30, 8, 18), math.radians(100), math.radians(250), 1)
            pygame.draw.line(s, borda, (x + 3, 34), (x + 5, 50), 1)

    sup.blit(_forma(forma, cor, borda, detalhes=detalhes), (0, 0))
    for x in (11, 86):
        lacos = [(x, 24), (x - 7, 19), (x - 7, 29)], [(x, 24), (x + 7, 19), (x + 7, 29)]
        for p in lacos:
            pygame.draw.polygon(sup, (60, 120, 230), p)
            pygame.draw.polygon(sup, (30, 70, 160), p, 1)
        pygame.draw.circle(sup, (30, 70, 160), (x, 24), 3)
        pygame.draw.circle(sup, (110, 170, 255), (x, 24), 2)


_BLACK = ((58, 40, 32), (30, 20, 15), (95, 70, 55))


def _black_atras(sup):
    cor, borda, claro = _BLACK

    def forma(s, cr):
        pygame.draw.ellipse(s, cr, (6, 1, 86, 56))
        for a in range(0, 360, 30):
            x = 49 + math.cos(math.radians(a)) * 42
            y = 29 + math.sin(math.radians(a)) * 27
            pygame.draw.circle(s, cr, (round(x), round(y)), 6)
        c._apagar_abaixo(s, 58)

    def detalhes(s):
        rnd = random.Random(5)
        for _ in range(26):
            x, y = rnd.randint(8, 90), rnd.randint(2, 50)
            pygame.draw.arc(s, claro, (x, y, 6, 5), math.radians(20), math.radians(160), 1)

    sup.blit(_forma(forma, cor, borda, detalhes=detalhes), (0, 0))


def _black_topo(sup):
    cor, borda, claro = _BLACK

    def forma(s, cr):
        _cabelo_liso(recuo=6, y_lados=32)(s, cr)
        for x in range(30, 70, 7):
            pygame.draw.circle(s, cr, (x, min(24, round(_y_topo(x)) + 6)), 4)

    def detalhes(s):
        for x in range(26, 72, 9):
            pygame.draw.arc(s, claro, (x, 13, 6, 5), math.radians(20), math.radians(160), 1)

    sup.blit(_forma(forma, cor, borda, esp=1, detalhes=detalhes), (0, 0))


def _moicano_topo(sup):
    rosa, borda, claro = (230, 60, 160), (130, 20, 85), (255, 150, 215)
    def forma(s, cr):
        pontas = [(31, 9), (37, 2), (45, 0), (53, 0), (60, 2), (66, 9)]
        vales = [(40, 14), (44, 11), (49, 10), (54, 11), (58, 14)]
        pts = [(40, round(_y_topo(40)) + 3)]
        for i, p in enumerate(pontas):
            pts.append(p)
            if i < len(vales):
                pts.append(vales[i])
        for x in range(58, 39, -2):
            pts.append((x, round(_y_topo(x)) + 3))
        pygame.draw.polygon(s, cr, pts)

    def detalhes(s):
        for a, b in (((45, 3), (47, 14)), ((53, 3), (51, 14)), ((38, 6), (43, 14)),
                     ((60, 6), (55, 14))):
            pygame.draw.line(s, claro, a, b, 1)

    sup.blit(_forma(forma, rosa, borda, detalhes=detalhes), (0, 0))
    # laterais raspadas
    for x in range(24, 36, 3):
        sup.fill((90, 90, 100), (x, round(_y_topo(x)) + 3, 1, 1))
    for x in range(63, 74, 3):
        sup.fill((90, 90, 100), (x, round(_y_topo(x)) + 3, 1, 1))


_CACHO = ((250, 200, 70), (190, 130, 30), (255, 235, 150))


def _cachos(sup, angulos):
    cor, borda, claro = _CACHO
    pontos = []
    for a in angulos:
        ar = math.radians(a)
        pontos.append((round(48.5 + math.cos(ar) * 34), round(51 - math.sin(ar) * 38)))
    for p in pontos:
        pygame.draw.circle(sup, borda, p, 8)
    for p in pontos:
        pygame.draw.circle(sup, cor, p, 6)
    for x, y in pontos:
        pygame.draw.arc(sup, claro, (x - 4, y - 4, 8, 8), math.radians(90), math.radians(250), 1)
        sup.fill(borda, (x + 1, y, 1, 1))


def _cachos_topo(sup):
    cor, borda, _ = _CACHO
    sup.blit(_forma(_calota(22), cor, borda), (0, 0))
    _cachos(sup, (40, 62, 82, 102, 122, 142))


def _cachos_lados(sup):
    _cachos(sup, (-8, 14, 166, 188))


def _fogo_topo(sup):
    camadas = (((230, 50, 30), (140, 20, 10), 0), ((255, 150, 30), None, 6),
               ((255, 235, 90), None, 12))
    xs = (22, 30, 38, 46, 54, 62, 70, 76)
    topo = (18, 8, 3, 0, 2, 6, 12, 22)
    for cor, borda, recuo in camadas:
        def forma(s, cr, recuo=recuo):
            pygame.draw.ellipse(s, cr, (15 + recuo, 13 + recuo // 2, 67 - 2 * recuo, 30))
            c._apagar_abaixo(s, 25)
            for i, x in enumerate(xs):
                if recuo and (i == 0 or i == len(xs) - 1):
                    continue
                if recuo >= 12 and i in (1, 6):
                    continue
                vale = round(_y_topo(x)) + 6
                ponta = topo[i] + recuo
                dx = 4 - recuo // 6
                pygame.draw.polygon(s, cr, [(x - dx - 1, vale), (x + dx + 1, vale),
                                            (x + 2, ponta)])
        sup.blit(_forma(forma, cor, borda, esp=2 if borda else 0), (0, 0))


def _arco_atras(sup):
    def forma(s, cr):
        pygame.draw.ellipse(s, cr, (8, 3, 82, 70))
        pygame.draw.polygon(s, cr, [(8, 38), (90, 38), (93, 92), (5, 92)])
        for x in range(9, 90, 8):
            pygame.draw.polygon(s, (0, 0, 0, 0), [(x, 93), (x + 6, 93), (x + 3, 88)])

    def detalhes(s):
        _faixas_y(ARCO, 4, 96, onda=2)(s)
        for x in (12, 86):
            pygame.draw.line(s, (255, 255, 255), (x, 30), (x, 50), 1)

    sup.blit(_forma(forma, (255, 255, 255), (90, 60, 140), detalhes=detalhes), (0, 0))


def _arco_topo(sup):
    def forma(s, cr):
        pygame.draw.ellipse(s, cr, OVO_GORDO)
        c._apagar_abaixo(s, 23)
        for x in range(26, 72, 8):
            pygame.draw.polygon(s, cr, [(x - 4, 22), (x + 5, 22), (x + 2, 29)])

    def detalhes(s):
        _faixas_y(ARCO, 8, 30, onda=1.5)(s)
        pygame.draw.arc(s, (255, 255, 255), (26, 13, 30, 14), math.radians(95), math.radians(150), 2)

    sup.blit(_forma(forma, (255, 255, 255), (90, 60, 140), detalhes=detalhes), (0, 0))


CABELOS = {
    "cab_topete": dict(topo=_topete_topo),
    "cab_franja": dict(topo=_franja_topo),
    "cab_coque": dict(topo=_coque_topo, alto=True),
    "cab_rabo": dict(topo=_rabo_topo, atras=_rabo_atras, lados=_rabo_lados),
    "cab_marias": dict(topo=_marias_topo, lados=_marias_lados),
    "cab_black": dict(topo=_black_topo, atras=_black_atras),
    "cab_moicano": dict(topo=_moicano_topo, alto=True),
    "cab_cachos": dict(topo=_cachos_topo, lados=_cachos_lados),
    "cab_fogo": dict(topo=_fogo_topo, alto=True),
    "cab_arco_iris": dict(topo=_arco_topo, atras=_arco_atras),
}


def cabelo_escondido(cab_id, ids):
    """True se um chapéu equipado cobre o TOPO do cabelo extra."""
    alto = CABELOS.get(cab_id, {}).get("alto")
    for item_id in ids or ():
        d = c.CATALOGO.get(item_id)
        if not d:
            continue
        esconde = d["esconde"]
        if c.CABELOS_DE_TOPO <= esconde or (alto and 7 in esconde):
            return True
    return False


def cabelo(cab_id, parte, escondido=False):
    """
    Parte do cabelo extra: "atras" (antes do corpo) ou "frente".
    `escondido`: um chapéu cobre o topo (só sobram os lados).
    """
    d = CABELOS.get(cab_id)
    if d is None:
        return None

    def criar():
        sup = _temp()
        if parte == "atras":
            if d.get("atras"):
                d["atras"](sup)
        else:
            if not escondido:
                d["topo"](sup)
            if d.get("lados"):
                d["lados"](sup)
        return sup

    return _parte(("cab", cab_id, parte, escondido), criar)


# ============================================================
# OLHOS
# ============================================================

ESCURO = (25, 22, 32)


def _dois(f):
    """Chama f(sup, centro, lado) para os dois olhos (lado -1 = esquerdo)."""
    def g(sup):
        f(sup, EL, -1)
        f(sup, ER, 1)
    return g


@_dois
def _olh_bolinha(sup, ctr, lado):
    x, y = ctr
    pygame.draw.circle(sup, ESCURO, (x, y + 1), 5)
    sup.fill((255, 255, 255), (x - 2, y - 2, 2, 2))


@_dois
def _olh_sono(sup, ctr, lado):
    x, y = ctr
    t = _temp()
    pygame.draw.ellipse(t, (255, 255, 255), (x - 8, y - 5, 16, 13))
    c._apagar_acima(t, y + 1)
    pygame.draw.circle(t, ESCURO, (x + lado, y + 4), 4)
    silh = _temp()
    pygame.draw.ellipse(silh, (255, 255, 255), (x - 8, y - 5, 16, 13))
    c._apagar_acima(silh, y + 1)
    c._recortar(t, silh)
    sup.blit(t, (0, 0))
    pygame.draw.arc(sup, ESCURO, (x - 8, y - 5, 16, 13), math.radians(180), math.radians(360), 1)
    # pálpebra pesada
    pygame.draw.line(sup, ESCURO, (x - 9, y + 1), (x + 8, y + 1), 2)
    pygame.draw.arc(sup, ESCURO, (x - 8, y - 4, 16, 8), math.radians(20), math.radians(160), 1)


@_dois
def _olh_cilios(sup, ctr, lado):
    x, y = ctr
    sup.blit(_forma(c._elipse((x - 6, y - 6, 12, 13)), (255, 255, 255), ESCURO, esp=1), (0, 0))
    pygame.draw.circle(sup, ESCURO, (x, y + 1), 4)
    sup.fill((255, 255, 255), (x - 2, y - 2, 2, 2))
    # cílios para fora
    for dx, dy, fx, fy in ((0, -5, 1, -9), (2, -3, 5, -6), (3, 0, 7, -2)):
        pygame.draw.line(sup, ESCURO, (x + lado * dx, y + dy), (x + lado * fx, y + fy), 2)


@_dois
def _olh_brilho(sup, ctr, lado):
    x, y = ctr

    def detalhes(s):
        pygame.draw.ellipse(s, (70, 140, 255), (x - 6, y - 1, 12, 9))
        pygame.draw.ellipse(s, (15, 25, 80), (x - 3, y - 4, 6, 8))
        pygame.draw.ellipse(s, (255, 255, 255), (x - 6, y - 7, 6, 6))
        s.fill((255, 255, 255), (x + 2, y + 3, 2, 2))

    sup.blit(_forma(c._elipse((x - 7, y - 9, 15, 19)), (35, 65, 170), ESCURO, esp=2,
                    detalhes=detalhes), (0, 0))


@_dois
def _olh_gato(sup, ctr, lado):
    x, y = ctr
    pts = [(x - 9, y + lado * 0), (x - 3, y - 5), (x + 4, y - 5), (x + 9, y),
           (x + 3, y + 5), (x - 4, y + 5)]
    # canto de fora puxadinho para cima
    if lado < 0:
        pts[0] = (x - 10, y - 3)
    else:
        pts[3] = (x + 10, y - 3)

    def detalhes(s):
        pygame.draw.ellipse(s, (120, 190, 30), (x - 7, y + 1, 14, 6))
        pygame.draw.ellipse(s, ESCURO, (x - 1, y - 5, 3, 11))
        s.fill((255, 255, 255), (x - 4, y - 3, 2, 2))

    sup.blit(_forma(c._poligono(pts), (200, 235, 70), ESCURO, esp=1, detalhes=detalhes), (0, 0))


def _coracao(s, cor, x, y, k=0):
    pygame.draw.circle(s, cor, (x - 3, y - 2), 4 + k)
    pygame.draw.circle(s, cor, (x + 3, y - 2), 4 + k)
    pygame.draw.polygon(s, cor, [(x - 7 - k, y - 1), (x + 7 + k, y - 1), (x, y + 7 + k)])


@_dois
def _olh_coracao(sup, ctr, lado):
    x, y = ctr
    sup.blit(_forma(lambda s, cr: _coracao(s, cr, x, y + 1, 1), (255, 70, 130), (160, 20, 70),
                    esp=2), (0, 0))
    sup.fill((255, 210, 225), (x - 5, y - 3, 2, 2))


@_dois
def _olh_espiral(sup, ctr, lado):
    x, y = ctr
    sup.blit(_forma(c._circulo((x, y), 8), (255, 255, 255), ESCURO, esp=1), (0, 0))
    pts = []
    for i in range(40):
        th = i / 39 * 4 * math.pi
        r = 0.4 + th * 0.52
        pts.append((x + math.cos(th * lado) * r, y + math.sin(th * lado) * r))
    pygame.draw.lines(sup, ESCURO, False, pts, 1)


@_dois
def _olh_robo(sup, ctr, lado):
    x, y = ctr
    sup.blit(_forma(lambda s, cr: pygame.draw.rect(s, cr, (x - 9, y - 7, 18, 14), border_radius=3),
                    (150, 155, 170), (60, 62, 75), esp=1), (0, 0))
    pygame.draw.rect(sup, (15, 35, 55), (x - 7, y - 5, 14, 10), border_radius=2)
    brilho = _temp()
    pygame.draw.rect(brilho, (60, 230, 255, 90), (x - 6, y - 4, 12, 8), border_radius=2)
    sup.blit(brilho, (0, 0))
    pygame.draw.rect(sup, (90, 240, 255), (x - 3, y - 3, 6, 6), border_radius=1)
    sup.fill((220, 255, 255), (x - 2, y - 2, 2, 2))
    for bx in (x - 8, x + 7):
        sup.fill((90, 92, 105), (bx, y - 6, 1, 1))
        sup.fill((90, 92, 105), (bx, y + 5, 1, 1))


@_dois
def _olh_galaxia(sup, ctr, lado):
    x, y = ctr

    def detalhes(s):
        pygame.draw.ellipse(s, (60, 90, 220), (x - 6, y - 1, 12, 10))
        pygame.draw.ellipse(s, (230, 90, 200), (x - 3, y + 2, 7, 5))
        rnd = random.Random(x)
        for _ in range(6):
            s.fill((255, 255, 255), (x + rnd.randint(-5, 4), y + rnd.randint(-6, 7), 1, 1))
        pygame.draw.ellipse(s, (255, 255, 255), (x - 6, y - 7, 6, 6))
        c._estrela4(s, (255, 255, 230), (x + 3, y + 4), 3, 0.3)

    sup.blit(_forma(c._elipse((x - 7, y - 9, 15, 19)), (95, 40, 170), (20, 12, 50), esp=2,
                    detalhes=detalhes), (0, 0))


@_dois
def _olh_estrela(sup, ctr, lado):
    x, y = ctr
    estrela(sup, (x, y + 1), 10, (200, 110, 10))
    estrela(sup, (x, y + 1), 8, (255, 215, 40))
    sup.fill((255, 250, 200), (x - 2, y - 2, 2, 2))


OLHOS = {
    "olh_bolinha": dict(f=_olh_bolinha, linhas=True),
    "olh_sono": dict(f=_olh_sono),
    "olh_cilios": dict(f=_olh_cilios),
    "olh_brilho": dict(f=_olh_brilho),
    "olh_gato": dict(f=_olh_gato),
    "olh_coracao": dict(f=_olh_coracao),
    "olh_espiral": dict(f=_olh_espiral),
    "olh_robo": dict(f=_olh_robo),
    "olh_galaxia": dict(f=_olh_galaxia),
    "olh_estrela": dict(f=_olh_estrela),
}


# ============================================================
# BOCAS
# ============================================================

LINHA = (35, 25, 30)


def _boc_sorriso(sup):
    def forma(s, cr):
        pygame.draw.ellipse(s, cr, (35, 52, 28, 22))
        c._apagar_acima(s, 61)

    def detalhes(s):
        s.fill((255, 255, 255), (36, 61, 26, 3))
        pygame.draw.ellipse(s, (240, 110, 130), (41, 67, 16, 9))

    sup.blit(_forma(forma, (120, 25, 40), LINHA, esp=2, detalhes=detalhes), (0, 0))


def _boc_gato(sup):
    pygame.draw.lines(sup, LINHA, False, [(37, 62), (39, 66), (42, 68), (45, 67), (48, 64),
                                          (51, 67), (54, 68), (57, 66), (59, 62)], 2)
    pygame.draw.polygon(sup, (255, 130, 160), [(44, 58), (52, 58), (48, 62)])
    pygame.draw.polygon(sup, (190, 70, 100), [(44, 58), (52, 58), (48, 62)], 1)


def _boc_assobio(sup):
    pygame.draw.circle(sup, (160, 40, 70), (53, 65), 5)
    pygame.draw.circle(sup, (235, 110, 140), (53, 65), 4)
    pygame.draw.circle(sup, (90, 20, 35), (53, 65), 2)
    # notinha musical
    pygame.draw.ellipse(sup, LINHA, (63, 60, 5, 4))
    pygame.draw.line(sup, LINHA, (67, 61), (67, 53), 1)
    pygame.draw.line(sup, LINHA, (67, 53), (71, 55), 2)


def _boc_batom(sup):
    def forma(s, cr):
        pygame.draw.polygon(s, cr, [(35, 65), (41, 60), (48, 62), (55, 60), (61, 65)])
        pygame.draw.ellipse(s, cr, (36, 59, 24, 13))
        c._apagar_acima(s, 60)

    def detalhes(s):
        pygame.draw.line(s, (140, 15, 40), (37, 65), (59, 65), 1)
        s.fill((255, 170, 190), (44, 67, 5, 2))

    sup.blit(_forma(forma, (225, 35, 70), (140, 15, 40), esp=1, detalhes=detalhes), (0, 0))


def _boc_vampiro(sup):
    pygame.draw.arc(sup, LINHA, (34, 54, 30, 16), math.radians(200), math.radians(340), 2)
    for x in (42, 55):
        pts = [(x - 3, 67), (x + 3, 67), (x, 74)]
        pygame.draw.polygon(sup, (255, 255, 255), pts)
        pygame.draw.polygon(sup, LINHA, pts, 1)


def _dentes(sup, x0, y0, w, h, n, cor=(255, 255, 255)):
    def forma(s, cr):
        pygame.draw.rect(s, cr, (x0, y0, w, h), border_radius=4)

    def detalhes(s):
        for i in range(1, n):
            x = x0 + round(i * w / n)
            pygame.draw.line(s, (190, 190, 205), (x, y0), (x, y0 + h), 1)

    sup.blit(_forma(forma, cor, LINHA, esp=2, detalhes=detalhes), (0, 0))


def _boc_aparelho(sup):
    _dentes(sup, 35, 59, 28, 11, 4)
    pygame.draw.line(sup, (140, 145, 160), (37, 64), (60, 64), 1)
    for x in (39, 46, 53, 59):
        sup.fill((120, 125, 140), (x - 1, 63, 3, 3))
        sup.fill((230, 235, 245), (x - 1, 63, 1, 1))


def _boc_pirulito(sup):
    pygame.draw.arc(sup, LINHA, (37, 56, 20, 12), math.radians(200), math.radians(340), 2)
    pygame.draw.line(sup, (160, 160, 175), (54, 65), (70, 56), 4)
    pygame.draw.line(sup, (255, 255, 255), (54, 65), (70, 56), 2)
    sup.blit(_forma(c._circulo((73, 53), 7), (255, 120, 180), (180, 40, 100), esp=1,
                    detalhes=lambda s: [pygame.draw.arc(s, (255, 255, 255), (73 - r, 53 - r, 2 * r, 2 * r),
                                                        math.radians(a), math.radians(a + 200), 2)
                                        for r, a in ((6, 0), (3, 180))]), (0, 0))


def _boc_ouro(sup):
    def forma(s, cr):
        pygame.draw.ellipse(s, cr, (34, 52, 30, 22))
        c._apagar_acima(s, 59)

    def detalhes(s):
        s.fill((255, 255, 255), (35, 59, 28, 5))
        for x in (41, 47, 53, 59):
            pygame.draw.line(s, (190, 190, 205), (x, 59), (x, 63), 1)
        s.fill((255, 200, 40), (47, 59, 6, 5))
        s.fill((255, 245, 170), (48, 60, 2, 2))

    sup.blit(_forma(forma, (110, 25, 40), LINHA, esp=2, detalhes=detalhes), (0, 0))
    c._estrela4(sup, (255, 250, 200), (55, 57), 4, 0.3)


def _boc_chiclete(sup):
    def detalhes(s):
        pygame.draw.arc(s, (255, 220, 240), (43, 58, 16, 16), math.radians(100), math.radians(170), 2)
        s.fill((255, 255, 255), (45, 62, 3, 3))

    sup.blit(_forma(c._circulo((50, 68), 11), (255, 140, 200), (205, 60, 140), esp=2,
                    detalhes=detalhes), (0, 0))


def _boc_diamante(sup):
    def forma(s, cr):
        pygame.draw.ellipse(s, cr, (34, 52, 30, 22))
        c._apagar_acima(s, 59)

    def detalhes(s):
        for x in range(36, 62, 5):
            pts = [(x, 59), (x + 5, 59), (x + 4, 64), (x + 2, 66), (x, 64)]
            pygame.draw.polygon(s, (190, 240, 255), pts)
            pygame.draw.line(s, (255, 255, 255), (x + 1, 60), (x + 2, 63), 1)
            pygame.draw.polygon(s, (90, 170, 220), pts, 1)

    sup.blit(_forma(forma, (70, 25, 60), LINHA, esp=2, detalhes=detalhes), (0, 0))
    c._estrela4(sup, (255, 255, 255), (37, 57), 4, 0.3)
    c._estrela4(sup, (210, 250, 255), (62, 63), 3, 0.3)


BOCAS = {
    "boc_sorriso": dict(f=_boc_sorriso, linhas=True),
    "boc_gato": dict(f=_boc_gato, linhas=True),
    "boc_assobio": dict(f=_boc_assobio, linhas=True),
    "boc_batom": dict(f=_boc_batom),
    "boc_vampiro": dict(f=_boc_vampiro, linhas=True),
    "boc_aparelho": dict(f=_boc_aparelho, linhas=True),
    "boc_pirulito": dict(f=_boc_pirulito, linhas=True),
    "boc_ouro": dict(f=_boc_ouro, linhas=True),
    "boc_chiclete": dict(f=_boc_chiclete),
    "boc_diamante": dict(f=_boc_diamante, linhas=True),
}


def _rosto(tabela, pid, claro):
    d = tabela.get(pid)
    if d is None:
        return None

    def criar():
        sup = _temp()
        d["f"](sup)
        if claro and d.get("linhas"):
            _clarear_linhas(sup)
        return sup

    return _parte(("rosto", pid, bool(claro)), criar)


def olhos(olho_id, claro=False):
    """Olhos extra (100x100). `claro`: ovo escuro (linhas claras)."""
    return _rosto(OLHOS, olho_id, claro)


def boca(boca_id, claro=False):
    return _rosto(BOCAS, boca_id, claro)


def linhas_claras(sup):
    """Cópia de `sup` com as linhas pretas clareadas (em cache)."""
    return _parte(("claro", id(sup)), lambda: _copia_clara(sup))


def _copia_clara(sup):
    s = sup.copy()
    _clarear_linhas(s)
    return s


# ============================================================
# ROUPAS (desenhos no formato dos cosméticos: f(sup, ovo))
# ============================================================

def _tronco(y, gola=None):
    """Silhueta: corpo do ovo de y para baixo (gola = elipse recortada)."""
    def f(s, cr):
        pygame.draw.ellipse(s, cr, OVO)
        c._apagar_acima(s, y)
        if gola:
            pygame.draw.ellipse(s, (0, 0, 0, 0), gola)
    return f


def _vestir(sup, forma, cor, borda, detalhes=None, esp=2):
    t = _forma(forma, cor, borda, esp=esp, detalhes=detalhes)
    sup.blit(t, (0, 0))


def _rou_listrada(sup, ovo):
    def detalhes(s):
        for y in range(77, 100, 6):
            s.fill((255, 255, 255), (0, y, 100, 3))

    _vestir(sup, _tronco(72, (34, 66, 30, 12)), (40, 70, 160), (20, 35, 95), detalhes)


def _rou_macacao(sup, ovo):
    jeans, borda, costura = (70, 115, 190), (35, 60, 120), (150, 190, 240)

    def forma(s, cr):
        _tronco(80)(s, cr)
        pygame.draw.rect(s, cr, (34, 70, 30, 14), border_radius=2)
        c._recortar_ovo(s)

    def detalhes(s):
        for x in range(37, 62, 3):
            s.fill(costura, (x, 72, 1, 1))
        pygame.draw.rect(s, costura, (41, 74, 16, 7), 1)

    # alças
    for a, b in (((36, 71), (25, 59)), ((61, 71), (72, 59))):
        pygame.draw.line(sup, borda, a, b, 5)
        pygame.draw.line(sup, jeans, a, b, 3)
    _vestir(sup, forma, jeans, borda, detalhes)
    for x in (37, 60):
        pygame.draw.circle(sup, (255, 210, 60), (x, 73), 2)
    c._recortar_ovo(sup)


def _rou_futebol(sup, ovo):
    amarelo, borda, verde = (255, 215, 40), (190, 150, 20), (40, 150, 70)

    def detalhes(s):
        pygame.draw.polygon(s, verde, [(38, 70), (60, 70), (49, 80)])
        pygame.draw.polygon(s, amarelo, [(41, 70), (57, 70), (49, 77)])
        # número 10
        azul = (40, 80, 180)
        s.fill(azul, (38, 82, 2, 8))
        pygame.draw.rect(s, azul, (43, 82, 6, 8), 2)
        s.fill(verde, (15, 72, 6, 30))
        s.fill(verde, (76, 72, 8, 30))

    _vestir(sup, _tronco(72, (34, 64, 30, 12)), amarelo, borda, detalhes)


def _rou_vestido(sup, ovo):
    verm, borda = (225, 50, 75), (140, 20, 45)

    def forma(s, cr):
        _tronco(72, (34, 64, 30, 12))(s, cr)
        pygame.draw.polygon(s, cr, [(22, 78), (75, 78), (88, 94), (9, 94)])
        pygame.draw.ellipse(s, cr, (9, 86, 79, 12))

    def detalhes(s):
        for i, (x, y) in enumerate(((28, 80), (40, 86), (54, 84), (66, 79), (20, 90),
                                    (74, 91), (47, 93), (33, 94), (62, 93))):
            pygame.draw.circle(s, (255, 255, 255), (x, y), 2)

    _vestir(sup, forma, verm, borda, detalhes)
    # golinha branca
    branco = c._branco(ovo, (190, 190, 205))
    for x in (36, 50):
        pygame.draw.ellipse(sup, (255, 255, 255), (x, 71, 13, 6))
        pygame.draw.ellipse(sup, branco, (x, 71, 13, 6), 1)


def _rou_moletom_atras(sup, ovo):
    sup.blit(_forma(c._elipse((9, 6, 79, 62)), (70, 155, 90), (35, 95, 50)), (0, 0))
    c._apagar_abaixo(sup, 66)


def _rou_moletom(sup, ovo):
    verde, borda = (90, 180, 110), (40, 110, 60)

    def detalhes(s):
        pygame.draw.rect(s, (70, 155, 90), (34, 82, 30, 12), border_radius=4)
        pygame.draw.rect(s, borda, (34, 82, 30, 12), 1, border_radius=4)

    _vestir(sup, _tronco(71, (32, 64, 34, 13)), verde, borda, detalhes)
    for x in (43, 55):
        pygame.draw.line(sup, (255, 255, 255), (x, 75), (x - 1, 83), 1)
        sup.fill((255, 255, 255), (x - 2, 83, 2, 2))


def _rou_quimono(sup, ovo):
    borda = c._branco(ovo, (175, 180, 200), (130, 135, 160))

    def detalhes(s):
        pygame.draw.line(s, borda, (35, 68), (56, 80), 2)
        pygame.draw.line(s, borda, (63, 68), (48, 77), 2)
        s.fill((30, 30, 35), (0, 78, 100, 5))
        s.fill((80, 80, 90), (0, 79, 100, 1))

    _vestir(sup, _tronco(68, (38, 60, 22, 14)), (250, 250, 252), borda, detalhes)
    # nó e pontas da faixa preta
    sup.fill((30, 30, 35), (55, 77, 6, 7))
    pygame.draw.polygon(sup, (30, 30, 35), [(55, 82), (51, 90), (54, 91), (58, 83)])
    pygame.draw.polygon(sup, (30, 30, 35), [(59, 82), (64, 89), (61, 91), (57, 83)])
    c._recortar_ovo(sup)


def _rou_terno(sup, ovo):
    preto, borda = (45, 45, 60), (15, 15, 25)

    def detalhes(s):
        pygame.draw.polygon(s, (255, 255, 255), [(38, 70), (60, 70), (49, 90)])
        pygame.draw.polygon(s, (210, 40, 60), [(47, 72), (51, 72), (52, 84), (49, 88), (46, 84)])
        pygame.draw.line(s, (90, 90, 110), (38, 70), (47, 86), 2)
        pygame.draw.line(s, (90, 90, 110), (60, 70), (51, 86), 2)
        s.fill((255, 255, 255), (63, 77, 6, 2))
        s.fill((255, 255, 255), (64, 76, 2, 1))

    _vestir(sup, _tronco(70), preto, borda, detalhes)


def _rou_astronauta(sup, ovo):
    borda = c._branco(ovo, (160, 165, 185), (120, 125, 150))

    def detalhes(s):
        s.fill((255, 140, 40), (0, 72, 100, 3))
        pygame.draw.rect(s, (70, 75, 95), (38, 78, 22, 11), border_radius=2)
        for i, cor in enumerate(((255, 70, 70), (90, 220, 110), (80, 170, 255))):
            s.fill(cor, (41 + i * 6, 81, 4, 4))
        pygame.draw.circle(s, (40, 80, 180), (27, 82), 4)
        c._estrela4(s, (255, 255, 255), (27, 82), 3, 0.3)

    _vestir(sup, _tronco(67, (36, 60, 26, 12)), (238, 240, 248), borda, detalhes)


def _rou_armadura(sup, ovo):
    prata, borda, luz = (185, 192, 210), (95, 100, 120), (235, 240, 250)

    def detalhes(s):
        for y in (74, 82, 90):
            pygame.draw.line(s, borda, (0, y), (100, y), 1)
            pygame.draw.line(s, luz, (0, y + 1), (100, y + 1), 1)
        for x in range(22, 80, 9):
            s.fill(borda, (x, 70, 2, 2))
        pygame.draw.rect(s, (255, 205, 60), (46, 74, 6, 14))
        pygame.draw.rect(s, (255, 205, 60), (42, 78, 14, 4))

    _vestir(sup, _tronco(66, (36, 58, 26, 12)), prata, borda, detalhes)
    for x in (20, 77):
        sup.blit(_forma(c._elipse((x - 7, 63, 14, 11)), prata, borda,
                        detalhes=lambda s, x=x: pygame.draw.line(s, luz, (x - 3, 66), (x + 2, 66), 1)),
                 (0, 0))


def _rou_manto_atras(sup, ovo):
    def detalhes(s):
        pygame.draw.line(s, (150, 20, 40), (18, 60), (10, 96), 3)
        pygame.draw.line(s, (150, 20, 40), (80, 60), (88, 96), 3)
        pygame.draw.lines(s, (255, 200, 50), False, [(6, 95), (49, 90), (92, 95)], 3)

    sup.blit(_forma(c._poligono([(26, 44), (72, 44), (92, 97), (49, 92), (6, 97)]),
                    (210, 35, 60), (120, 10, 30), detalhes=detalhes), (0, 0))


def _rou_manto(sup, ovo):
    borda = c._branco(ovo, (175, 175, 195))

    def forma(s, cr):
        pygame.draw.ellipse(s, cr, (12, 68, 74, 16))

    def detalhes(s):
        for x, y in ((20, 76), (30, 72), (42, 79), (56, 73), (67, 79), (77, 74), (49, 72)):
            s.fill((30, 30, 30), (x, y, 2, 3))

    _vestir(sup, forma, (252, 252, 255), borda, detalhes)
    pygame.draw.circle(sup, (190, 130, 20), (49, 83), 4)
    pygame.draw.circle(sup, (255, 210, 60), (49, 83), 3)
    sup.fill((230, 40, 70), (48, 82, 2, 2))


def _rou_sueter_natal(sup, ovo):
    verm, borda = (205, 40, 50), (130, 15, 25)

    def detalhes(s):
        for x in range(0, 100, 6):
            pygame.draw.lines(s, (255, 255, 255), False, [(x, 79), (x + 3, 76), (x + 6, 79)], 2)
        for x in (28, 49, 70):
            pygame.draw.polygon(s, (40, 150, 70), [(x - 5, 92), (x + 5, 92), (x, 83)])
            s.fill((255, 220, 60), (x - 1, 82, 2, 2))
        for x in range(20, 80, 8):
            s.fill((255, 255, 255), (x, 72, 2, 2))

    _vestir(sup, _tronco(70, (34, 62, 30, 13)), verm, borda, detalhes)


# ============================================================
# CHAPÉUS EXCLUSIVOS
# ============================================================

def _gorro_natal(sup, ovo):
    verm, borda = (220, 40, 50), (130, 15, 25)

    def forma(s, cr):
        pygame.draw.polygon(s, cr, [(25, 20), (72, 20), (70, 10), (80, 12), (86, 22), (78, 8),
                                    (60, 1), (40, 3)])

    def detalhes(s):
        pygame.draw.arc(s, (250, 110, 110), (32, 4, 30, 20), math.radians(100), math.radians(160), 2)

    sup.blit(_forma(forma, verm, borda, detalhes=detalhes), (0, 0))
    contorno = c._branco(ovo, (200, 205, 220))
    sup.blit(_forma(lambda s, cr: pygame.draw.rect(s, cr, (21, 16, 56, 9), border_radius=4),
                    (255, 255, 255), contorno), (0, 0))
    sup.blit(_forma(c._circulo((86, 22), 6), (255, 255, 255), contorno), (0, 0))
    for p in ((30, 19), (44, 21), (58, 19), (70, 21), (85, 20)):
        sup.fill((220, 225, 238), (p, (2, 2)))


def _chapeu_bruxa(sup, ovo):
    preto, borda, roxo = (45, 35, 60), (15, 10, 25), (130, 70, 200)
    sup.blit(_forma(c._elipse((8, 16, 82, 10)), preto, borda), (0, 0))

    def cone(s, cr):
        pygame.draw.polygon(s, cr, [(30, 20), (68, 20), (58, 8), (70, 2), (60, 0), (50, 2)])

    def detalhes(s):
        s.fill(roxo, (30, 14, 40, 5))

    sup.blit(_forma(cone, preto, borda, detalhes=detalhes), (0, 0))
    pygame.draw.rect(sup, (255, 205, 60), (45, 13, 8, 7), 2)
    pygame.draw.circle(sup, (255, 230, 120), (64, 5), 1)


def _orelhas_coelho(sup, ovo):
    branco = (255, 255, 255)
    contorno = c._branco(ovo, (200, 195, 215), (150, 145, 175))

    def orelhas(s, cr):
        for x, a in ((31, 12), (55, -12)):
            o = pygame.Surface((14, 30), pygame.SRCALPHA)
            pygame.draw.ellipse(o, cr, (0, 0, 14, 30))
            o = pygame.transform.rotate(o, a)
            s.blit(o, o.get_rect(center=(x + 7, 12)))

    def dentro(s):
        for x, a in ((31, 12), (55, -12)):
            o = pygame.Surface((14, 30), pygame.SRCALPHA)
            pygame.draw.ellipse(o, (255, 170, 200), (4, 5, 6, 20))
            o = pygame.transform.rotate(o, a)
            s.blit(o, o.get_rect(center=(x + 7, 12)))

    sup.blit(_forma(orelhas, branco, contorno, detalhes=dentro), (0, 0))
    # tiara pastel com um ovinho de páscoa
    pygame.draw.arc(sup, (140, 200, 255), (22, 13, 54, 20), math.radians(20), math.radians(160), 3)
    sup.blit(_forma(c._elipse((44, 12, 9, 11)), (255, 220, 90), (200, 150, 40), esp=1,
                    detalhes=lambda s: s.fill((255, 120, 170), (44, 16, 9, 2))), (0, 0))


DESENHOS = {
    ("rou_listrada", "corpo"): _rou_listrada,
    ("rou_macacao", "corpo"): _rou_macacao,
    ("rou_futebol", "corpo"): _rou_futebol,
    ("rou_vestido", "corpo"): _rou_vestido,
    ("rou_moletom", "atras"): _rou_moletom_atras,
    ("rou_moletom", "corpo"): _rou_moletom,
    ("rou_quimono", "corpo"): _rou_quimono,
    ("rou_terno", "corpo"): _rou_terno,
    ("rou_astronauta", "corpo"): _rou_astronauta,
    ("rou_armadura", "corpo"): _rou_armadura,
    ("rou_manto", "atras"): _rou_manto_atras,
    ("rou_manto", "corpo"): _rou_manto,
    ("rou_sueter_natal", "corpo"): _rou_sueter_natal,
    ("gorro_natal", "frente"): _gorro_natal,
    ("chapeu_bruxa", "frente"): _chapeu_bruxa,
    ("orelhas_coelho", "frente"): _orelhas_coelho,
}


# ============================================================
# CONSULTAS
# ============================================================

def extras_de(ids):
    """{slot: id} dos itens que SUBSTITUEM partes base."""
    ext = {}
    for item_id in ids or ():
        d = c.CATALOGO.get(item_id)
        if d and d["slot"] in SLOTS_TROCA:
            ext[d["slot"]] = item_id
    return ext


# ============================================================
# ÍCONES DA LOJA
# ============================================================

def _enquadrar(sup, caixa, tamanho):
    lado = max(caixa.w, caixa.h, 30)
    lado = round(lado * 1.15) + 4
    quad = pygame.Rect(0, 0, lado, lado)
    quad.center = caixa.center
    M = 40
    grande = pygame.Surface((100 + 2 * M, 100 + 2 * M), pygame.SRCALPHA)
    grande.blit(sup, (M, M))
    quad.move_ip(M, M)
    quad.clamp_ip(grande.get_rect())
    return c._escalar(grande.subsurface(quad).copy(), tamanho)


def icone(item_id, tamanho, ovo=1):
    """Ícone de um item de cabelo/olhos/boca/cor extra."""
    slot = c.CATALOGO[item_id]["slot"]

    if slot == SLOT_CABELO:
        limpo = _temp()
        limpo.blit(cabelo(item_id, "atras"), (0, 0))
        limpo.blit(assets.OVOS[ovo], (0, 0))
        limpo.blit(cabelo(item_id, "frente"), (0, 0))
        limpo.blit(assets.OLHOS[0], (0, 0))
        caixa = cabelo(item_id, "frente").get_bounding_rect()
        atras = cabelo(item_id, "atras").get_bounding_rect()
        if atras.w:
            caixa = caixa.union(atras)
        caixa = caixa.union(pygame.Rect(20, 14, 58, 30))
        return _enquadrar(limpo, caixa, tamanho)

    if slot == SLOT_COR:
        # sem cabelo: só o ovo e o rosto
        limpo = _temp()
        limpo.blit(corpo(item_id), (0, 0))
        claro = escuro(item_id)
        limpo.blit(linhas_claras(assets.OLHOS[0]) if claro else assets.OLHOS[0], (0, 0))
        limpo.blit(linhas_claras(assets.BOCAS[0]) if claro else assets.BOCAS[0], (0, 0))
        return _enquadrar(limpo, pygame.Rect(OVO), tamanho)

    # olhos / boca: rosto de perto, sem cabelo
    limpo = _temp()
    limpo.blit(assets.OVOS[ovo], (0, 0))
    if slot == SLOT_OLHOS:
        limpo.blit(olhos(item_id), (0, 0))
        caixa = olhos(item_id).get_bounding_rect()
    else:
        limpo.blit(boca(item_id), (0, 0))
        caixa = boca(item_id).get_bounding_rect()
    return _enquadrar(limpo, caixa, tamanho)


# ============================================================
# REGISTRO
# ============================================================

c.CATALOGO.update(ITENS)
c._DESENHOS.update(DESENHOS)
for _s in (SLOT_ROUPA,) + SLOTS_TROCA:
    if _s not in c.SLOTS:
        c.SLOTS.append(_s)
# roupa por baixo de tudo (cachecol, colar... ficam por cima)
c._ORDEM_SLOT.update({SLOT_ROUPA: -1, SLOT_CABELO: 4, SLOT_OLHOS: 4, SLOT_BOCA: 4, SLOT_COR: 4})
for _s in SLOTS_TROCA:
    c.ICONE_SLOT[_s] = icone
