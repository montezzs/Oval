# ============================================================
# FACHADA DAS CASAS (RUA DOS OVOS)
# ============================================================
# Dados da casa de cada ovo: cores, estilos das partes e itens da
# frente. O desenho fica em core/fachada_desenho.py.
#
#   casa = {
#       "cor_parede": 0, "parede": "liso",
#       "cor_telhado": 0, "telhado": "triangulo",
#       "cor_porta": 0, "porta": "reta",
#       "janela": "quadrada", "cerca": "nenhuma",
#       "correio": "padrao", "caminho": "terra",
#       "chamine": True,
#       "itens": {"esq": "vaso_flor", "dir": "", "telhado": ""},
#   }

PALETA_PAREDE = [
    ("CREME", (255, 240, 200)), ("AMARELO", (255, 220, 110)), ("PÊSSEGO", (255, 190, 150)),
    ("ROSA", (255, 175, 195)), ("LILÁS", (205, 175, 240)), ("AZUL", (150, 200, 255)),
    ("MENTA", (170, 230, 190)), ("VERDE", (150, 205, 120)), ("CINZA", (200, 200, 210)),
    ("BRANCO", (250, 250, 250)),
]

# A 1ª cor do telhado é "COR DO OVO" (resolvida na hora de desenhar)
PALETA_TELHADO = [
    ("COR DO OVO", None), ("VERMELHO", (200, 60, 55)), ("TELHA", (205, 110, 60)),
    ("MARROM", (120, 75, 45)), ("VERDE", (60, 140, 70)), ("AZUL", (60, 100, 190)),
    ("ROXO", (110, 70, 170)), ("ROSA", (230, 100, 150)), ("PRETO", (50, 50, 60)),
    ("AMARELO", (235, 180, 40)),
]

PALETA_PORTA = [
    ("MADEIRA", (150, 95, 55)), ("VERMELHA", (200, 50, 50)), ("AZUL", (50, 90, 180)),
    ("VERDE", (50, 130, 70)), ("AMARELA", (240, 190, 40)), ("BRANCA", (245, 245, 245)),
    ("ROXA", (120, 70, 170)), ("PRETA", (45, 45, 55)),
]

# Parede padrão de cada casa: 1 AMARELO, 2 AZUL, 3 ROSA, 4 MENTA, 5 LILÁS
PAREDE_DO_SLOT = [1, 5, 3, 6, 4]

# ------------------------------------------------------------
# CATÁLOGO (peças grátis têm preco 0 e ficam sempre disponíveis)
# ------------------------------------------------------------

def _p(nome, parte, preco, raridade, desc):
    return dict(nome=nome, parte=parte, preco=preco, raridade=raridade, desc=desc)


CATALOGO = {
    # ---- parede (acabamento) ----
    "liso": _p("LISO", "parede", 0, "COMUM", "Parede lisinha, do jeito que veio."),
    "parede_madeira": _p("MADEIRA", "parede", 80, "COMUM", "Tábuas de madeira com preguinhos."),
    "parede_listras": _p("LISTRAS", "parede", 90, "COMUM", "Listras verticais animadas."),
    "parede_bolinhas": _p("BOLINHAS", "parede", 90, "COMUM", "Bolinhas por toda a parede."),
    "parede_tijolo": _p("TIJOLINHO", "parede", 150, "INCOMUM", "Tijolinho à vista, charmoso."),
    "parede_pedra": _p("PEDRA DE CASTELO", "parede", 450, "RARO", "Pedras grandes de castelo."),
    # ---- telhado ----
    "triangulo": _p("TRIÂNGULO", "telhado", 0, "COMUM", "O telhado clássico."),
    "telhado_telhas": _p("TELHAS DE ESCAMA", "telhado", 150, "INCOMUM", "Telhas redondinhas como escamas."),
    "telhado_palha": _p("TELHADO DE PALHA", "telhado", 180, "INCOMUM", "Palha fofinha de casa de campo."),
    "telhado_cogumelo": _p("TELHADO COGUMELO", "telhado", 950, "EPICO", "Um cogumelo gigante de bolinhas."),
    # ---- porta ----
    "reta": _p("RETA", "porta", 0, "COMUM", "Porta simples de madeira."),
    "porta_arco": _p("PORTA EM ARCO", "porta", 60, "COMUM", "Porta com o topo arredondado."),
    "porta_redonda": _p("PORTA REDONDA", "porta", 200, "INCOMUM", "Porta redonda de toca."),
    "porta_ovo": _p("PORTA DE OVO", "porta", 450, "RARO", "Porta em forma de ovo, com moldura dourada."),
    # ---- janelas ----
    "quadrada": _p("QUADRADA", "janela", 0, "COMUM", "Janelas quadradas com cruz."),
    "janela_redonda": _p("JANELAS REDONDAS", "janela", 60, "COMUM", "Janelas redondas de navio."),
    "janela_arco": _p("JANELAS EM ARCO", "janela", 90, "COMUM", "Janelas com o topo em arco."),
    "janela_floreira": _p("JANELAS COM FLOREIRA", "janela", 200, "INCOMUM", "Uma floreira embaixo de cada janela."),
    "janela_coracao": _p("JANELAS DE CORAÇÃO", "janela", 480, "RARO", "Janelas de coração que brilham à noite."),
    # ---- cerca ----
    "nenhuma": _p("SEM CERCA", "cerca", 0, "COMUM", "Nada de cerca."),
    "cerca_estacas": _p("CERCA RÚSTICA", "cerca", 60, "COMUM", "Estacas de madeira com arame."),
    "cerca_branca": _p("CERCA BRANCA", "cerca", 90, "COMUM", "A cerquinha branca dos sonhos."),
    "cerca_viva": _p("CERCA-VIVA", "cerca", 180, "INCOMUM", "Arbustos com florzinhas."),
    "cerca_ferro": _p("GRADE DE FERRO", "cerca", 250, "INCOMUM", "Grade elegante com pontas de lança."),
    # ---- correio ----
    "padrao": _p("CAIXA PADRÃO", "correio", 0, "COMUM", "Caixa de correio azul."),
    "correio_ovo": _p("CAIXA DE CORREIO OVO", "correio", 280, "INCOMUM", "Uma caixa de correio em forma de ovo."),
    # ---- caminho ----
    "terra": _p("TERRA", "caminho", 0, "COMUM", "Caminho de terra batida."),
    "caminho_pedras": _p("PEDRINHAS", "caminho", 60, "COMUM", "Pedrinhas no meio da grama."),
    "caminho_tijolos": _p("TIJOLOS", "caminho", 90, "COMUM", "Caminho de tijolos."),
    "caminho_tapete": _p("TAPETE VERMELHO", "caminho", 400, "RARO", "Para entrar como uma estrela."),
    "caminho_arco_iris": _p("CAMINHO ARCO-ÍRIS", "caminho", 1000, "EPICO", "Um caminho com todas as cores."),
    # ---- itens de chão (ESQUERDA / DIREITA) ----
    "vaso_flor": _p("VASO DE FLOR", "chao", 0, "COMUM", "Presente de mudança. Flores que dançam no vento."),
    "cacto": _p("CACTO", "chao", 45, "COMUM", "Espinhento, mas fofo."),
    "flamingo": _p("FLAMINGO DE JARDIM", "chao", 50, "COMUM", "Um flamingo cor-de-rosa numa perna só."),
    "anao_jardim": _p("ANÃO DE JARDIM", "chao", 80, "COMUM", "Ele pisca quando ninguém está olhando."),
    "canteiro_flores": _p("JARDIM DE FLORES", "chao", 90, "COMUM", "Uma caixa cheia de flores."),
    "casinha_passaro": _p("CASINHA DE PASSARINHO", "chao", 150, "INCOMUM", "Um passarinho azul mora aqui."),
    "abobora_lanterna": _p("ABÓBORA-LANTERNA", "chao", 150, "INCOMUM", "O rosto brilha à noite."),
    "poste_luz": _p("POSTE DE LUZ", "chao", 160, "INCOMUM", "Ilumina a calçada à noite."),
    "banco": _p("BANCO DE JARDIM", "chao", 180, "INCOMUM", "O ovo senta nele para ver a rua."),
    "arvore": _p("ÁRVORE FRONDOSA", "chao", 220, "INCOMUM", "Uma árvore com frutinhas vermelhas."),
    "bicicleta": _p("BICICLETA", "chao", 250, "INCOMUM", "Na cor do seu ovo. TRIM!"),
    "arbusto_ovo": _p("ARBUSTO EM FORMA DE OVO", "chao", 280, "INCOMUM", "Podado com muito carinho."),
    "espantalho": _p("ESPANTALHO", "chao", 300, "INCOMUM", "Espanta os corvos (quase sempre)."),
    "fonte": _p("FONTE DE JARDIM", "chao", 600, "RARO", "Uma fontezinha que não para de jorrar."),
    # ---- itens do telhado ----
    "antena": _p("ANTENA DE TV", "enfeite", 50, "COMUM", "Pega todos os canais de desenho."),
    "bandeira": _p("BANDEIRA", "enfeite", 60, "COMUM", "Uma bandeira na cor do seu ovo."),
    "baloes": _p("BALÕES", "enfeite", 90, "COMUM", "Três balões presos na chaminé."),
    "cata_vento_galo": _p("GALO CATA-VENTO", "enfeite", 150, "INCOMUM", "Gira mais rápido quando venta."),
    "pisca_pisca": _p("PISCA-PISCA", "enfeite", 200, "INCOMUM", "Luzinhas que piscam à noite."),
    "painel_solar": _p("PAINEL SOLAR", "enfeite", 300, "INCOMUM", "Energia limpa do sol."),
    "gato_telhado": _p("GATO NO TELHADO", "enfeite", 480, "RARO", "Um gato laranja dorminhoco. MIAU!"),
}

TELHADOS_SEM_CHAMINE = {"telhado_cogumelo"}

# Peça padrão de cada parte (a que o ovo já tem de graça)
PADRAO_PARTE = {
    "parede": "liso", "telhado": "triangulo", "porta": "reta", "janela": "quadrada",
    "cerca": "nenhuma", "correio": "padrao", "caminho": "terra",
}


def ids_da_parte(parte):
    return [i for i, d in CATALOGO.items() if d["parte"] == parte]


def casa_padrao(slot, ovo=0):
    return {
        "cor_parede": PAREDE_DO_SLOT[slot % len(PAREDE_DO_SLOT)],
        "parede": "liso",
        "cor_telhado": 0,
        "telhado": "triangulo",
        "cor_porta": 0,
        "porta": "reta",
        "janela": "quadrada",
        "cerca": "nenhuma",
        "correio": "padrao",
        "caminho": "terra",
        "chamine": True,
        "itens": {"esq": "vaso_flor", "dir": "", "telhado": ""},
    }


def normalizar(casa, slot, ovo=0):
    """Completa chaves que faltam e troca ids desconhecidos pelo padrão."""
    base = casa_padrao(slot, ovo)
    if not isinstance(casa, dict) or not casa:
        return base
    saida = dict(base)
    for k, padrao in (("cor_parede", PALETA_PAREDE), ("cor_telhado", PALETA_TELHADO),
                      ("cor_porta", PALETA_PORTA)):
        v = casa.get(k)
        if isinstance(v, int) and not isinstance(v, bool) and 0 <= v < len(padrao):
            saida[k] = v
    for parte in PADRAO_PARTE:
        v = casa.get(parte)
        if isinstance(v, str) and v in CATALOGO and CATALOGO[v]["parte"] == parte:
            saida[parte] = v
    if isinstance(casa.get("chamine"), bool):
        saida["chamine"] = casa["chamine"]
    itens = casa.get("itens") if isinstance(casa.get("itens"), dict) else {}
    saida["itens"] = dict(base["itens"])
    for slot_item, parte in (("esq", "chao"), ("dir", "chao"), ("telhado", "enfeite")):
        v = itens.get(slot_item)
        if v == "" or (isinstance(v, str) and v in CATALOGO and CATALOGO[v]["parte"] == parte):
            saida["itens"][slot_item] = v
    return saida


def cor_parede(casa):
    return PALETA_PAREDE[casa["cor_parede"]][1]


def cor_porta(casa):
    return PALETA_PORTA[casa["cor_porta"]][1]


def cor_telhado(casa, cor_ovo):
    cor = PALETA_TELHADO[casa["cor_telhado"]][1]
    if cor is None:
        r, g, b = cor_ovo
        if min(cor_ovo) > 200:                # ovo branco
            return (215, 215, 225)
        return (max(0, r - 20), max(0, g - 20), max(0, b - 20))
    return cor


def tem_chamine(casa):
    return casa["chamine"] and casa["telhado"] not in TELHADOS_SEM_CHAMINE
