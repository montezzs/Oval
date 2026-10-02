import pygame

from settings import *

# ============================================================
# CARREGAMENTO DE IMAGENS
# ============================================================
# As imagens são carregadas UMA vez (depois da janela existir)
# e convertidas com convert_alpha(), o que deixa o blit
# muito mais rápido.

OVOS = []
CABELOS = []
OLHOS = []
BOCAS = []
FUNDOS = {}

NOMES_OVOS = ["VERDE", "AZUL", "BRANCO", "VERMELHO"]

_carregado = False


def _imagem(*partes):
    return pygame.image.load(caminho("Img", *partes)).convert_alpha()


def carregar():
    """Carrega todas as imagens do jogo (chamar depois do set_mode)."""
    global _carregado

    if _carregado:
        return

    OVOS.extend([
        _imagem("personagem", "P_verde.png"),
        _imagem("personagem", "P_azul.png"),
        _imagem("personagem", "P_branco.png"),
        _imagem("personagem", "P_vermelho.png"),
    ])

    for nome in ["cabelo1", "cabelo2", "cabelo3", "cabelo4",
                 "cabelo5", "cabelo6", "cabelo7", "cabelo7C"]:
        CABELOS.append(_imagem("cabelo", nome + ".png"))

    for i in range(1, 4):
        OLHOS.append(_imagem("olho", f"olho{i}.png"))

    for i in range(1, 7):
        BOCAS.append(_imagem("boca", f"boca{i}.png"))

    for nome in ["sol", "casa", "brincar"]:
        fundo = pygame.image.load(caminho("Img", "fundo", nome + ".png")).convert()
        FUNDOS[nome] = pygame.transform.scale(fundo, (LARGURA, ALTURA))

    _carregado = True


# ============================================================
# FONTES
# ============================================================

_fontes = {}


def fonte(tamanho):
    """Devolve a fonte do jogo no tamanho pedido (com cache)."""
    f = _fontes.get(tamanho)

    if f is None:
        f = pygame.font.Font(FONTE, tamanho)
        _fontes[tamanho] = f

    return f


_comidas = {}


def comida_sup(tam):
    """Img/jogos/comida.png escalada (suave) para caber em tam x tam, com cache."""
    tam = max(1, int(tam))
    s = _comidas.get(tam)
    if s is None:
        base = _comidas.get("base")
        if base is None:
            base = pygame.image.load(caminho("Img", "jogos", "comida.png"))
            try:
                base = base.convert_alpha()
            except pygame.error:
                pass
            _comidas["base"] = base
        w, h = base.get_size()
        k = tam / max(w, h)
        img = pygame.transform.smoothscale(base, (max(1, round(w * k)), max(1, round(h * k))))
        s = pygame.Surface((tam, tam), pygame.SRCALPHA)
        s.blit(img, img.get_rect(center=(tam // 2, tam // 2)))
        _comidas[tam] = s
    return s
