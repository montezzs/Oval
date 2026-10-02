# ============================================================
# IDIOMA (pt / en / es)
# ============================================================
# GUIA RÁPIDO PARA TRADUTORES
#
# 1) Importe:   from core.idioma import t
#
# 2) Envolva SÓ o que o jogador lê na tela:
#        ui.desenhar_texto(tela, t("PAUSADO"), ...)
#    NÃO envolva chaves internas, ids, nomes de arquivo/sprite/som,
#    chaves de save, nem strings usadas em comparações
#    (if rotulo == "JOGAR": ... continua em português).
#
# 3) A CHAVE é a frase ORIGINAL em português, exatamente igual
#    (acentos, maiúsculas, pontuação). Sem tradução -> aparece o pt.
#    Adicione a entrada em EN e ES no módulo de core/traducoes/:
#        comum.py       main.py, titulo, opções, tela de idioma, coisas gerais
#        cenas.py       cenas/*.py e cenas/casa_extras/*
#        core_textos.py core/*.py (itens, conquistas, cosméticos, pets...)
#        jogos_a.py / jogos_b.py / jogos_c.py / jogos_d.py
#                       jogos/*.py, divididos por quem coordena a tarefa
#    A mesma chave em dois módulos: vale a do último na lista de
#    core/traducoes/__init__.py (evite duplicar; se a frase já existe
#    em outro módulo, não precisa repetir).
#
# 4) Variáveis: converta f-strings em placeholders do .format:
#        f"VOCÊ GANHOU {n} MOEDAS"  ->  t("VOCÊ GANHOU {n} MOEDAS", n=n)
#    e no dicionário:  "VOCÊ GANHOU {n} MOEDAS": "YOU EARNED {n} COINS"
#    Use nomes (não {} vazios). Formatos como {x:.1f} funcionam.
#
# 5) CONSTANTES DE MÓDULO / CLASSE (TITULO, DESCRICAO, DICAS, NOMES...)
#    são avaliadas no import, ANTES de o idioma ser escolhido.
#    Por isso NÃO faça  TITULO = t("PULA OVO").  Deixe a constante em
#    português e traduza no momento de DESENHAR:
#        ui.texto(t(self.TITULO), 20)
#        for dica in DICAS: ... t(dica) ...
#    Assim a troca de idioma no menu vale na hora.
#
# 6) Botões: ui.Botao / ui.Menu já traduzem o rótulo sozinhos ao
#    desenhar (b.rotulo continua em pt para as comparações). Basta
#    pôr a tradução no dicionário. Rótulo com variável: monte-o já
#    traduzido com t(...) (a tradução de algo já traduzido devolve
#    ele mesmo).
#
# 7) Mantenha MAIÚSCULAS se o original é maiúsculo, e tamanho
#    parecido: a fonte PressStart2P é LARGA (cada letra = tamanho em
#    px). Texto em inglês/espanhol não pode estourar botões/painéis;
#    se ficar maior, abrevie.
#
# 8) Superfícies pré-renderizadas com texto (guardadas em __init__)
#    não mudam sozinhas: refaça-as ao desenhar, ou registre
#    idioma.ao_mudar(funcao) para invalidar o cache.
#
# 9) Fonte: PressStart2P tem ñ ¿ ¡ á é í ó ú ü (e ç ã õ). As
#    MAIÚSCULAS acentuadas perdem o acento (ui.preparar), menos Ñ.
# ============================================================

from core.traducoes import juntar

IDIOMAS = ("pt", "en", "es")
NOMES = {"pt": "PORTUGUÊS", "en": "ENGLISH", "es": "ESPAÑOL"}

_atual = "pt"
_tabelas = juntar()
_ouvintes = []

# Troca de caracteres que a fonte não tivesse (hoje nenhum falta).
_FALLBACK = str.maketrans({})


def definir(idioma):
    """Muda o idioma ("pt", "en" ou "es") e avisa quem se registrou."""
    global _atual
    if idioma not in IDIOMAS:
        idioma = "pt"
    if idioma == _atual:
        return
    _atual = idioma
    for f in list(_ouvintes):
        try:
            f(idioma)
        except Exception:
            pass


def atual():
    return _atual


def ao_mudar(callback):
    """Registra callback(idioma) chamado a cada troca de idioma."""
    if callback not in _ouvintes:
        _ouvintes.append(callback)
    return callback


def t(texto_pt, **fmt):
    """Tradução de `texto_pt` no idioma atual (ou ele mesmo)."""
    if not isinstance(texto_pt, str):
        return texto_pt
    msg = texto_pt
    if _atual != "pt":
        msg = _tabelas[_atual].get(texto_pt, texto_pt).translate(_FALLBACK)
    if fmt:
        try:
            msg = msg.format(**fmt)
        except (KeyError, IndexError, ValueError):
            msg = texto_pt.format(**fmt)
    return msg


def nome(idioma=None):
    return NOMES.get(idioma or _atual, "PORTUGUÊS")
