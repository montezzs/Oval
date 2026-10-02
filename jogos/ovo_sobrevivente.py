import heapq
import math
import random

import pygame

from settings import *
from core import ui
from core.idioma import t as tr
from jogos.base import MiniJogo

# ============================================================
# OVO SOBREVIVENTE
# ============================================================
# Os utensílios da cozinha se rebelaram! Colheres, frigideiras e
# batedores vêm em ondas cada vez maiores e o seu ovo só precisa
# SOBREVIVER por 3 minutos. Ele joga LIMÕES sozinho no inimigo mais
# perto; você só anda. Cada inimigo derrotado solta um CRISTAL de
# XP e, ao subir de nível, o jogo pausa para você escolher 1 de 3
# melhorias. Aos 2:00 chega o chefe: o LIQUIDIFICADOR!
#
# Pontos = inimigos derrotados x 10 + nível x 50 (+500 se sobreviver).

DURACAO = 180.0                 # 3 minutos
TEMPO_CHEFE = 120.0             # o liquidificador chega aos 2:00

# Arena (maior que a tela; a câmera segue o ovo)
ARENA_W, ARENA_H = 2048, 1536
PAREDE = 40                     # espessura da bancada em volta

# Ovo
ALTURA_OVO = 52
RAIO_OVO = 19
VEL_OVO = 215
TEMPO_INVENCIVEL = 1.0
VIDAS = (6, 5, 4)               # corações por dificuldade

# Limões
VEL_LIMAO = 520
ALCANCE = 560                   # só mira em quem está perto
DANO_BASE = 14
RECARGA_BASE = 0.7
RAIO_LIMAO = 10
RAIO_ORBITA = 88
DANO_ORBITA = 8

# Cristais de XP
RAIO_IMA = 90
MAX_CRISTAIS = 260
CORES_CRISTAL = {1: (90, 190, 255), 3: (110, 230, 120), 10: (200, 110, 255)}

# Inimigos
MAX_INIMIGOS = 150
CELULA = 44                     # grade para os inimigos não se empilharem
TIPOS = {
    #              vida  vel  raio xp
    "colher":     (9,    95,  16,  1),
    "frigideira": (34,   58,  24,  3),
    "batedor":    (20,   80,  18,  1),
}
VIDA_CHEFE = 2000

# Dificuldade: (inimigos, vida dos inimigos, dano do chefe)
DIFICULDADE = [(0.72, 0.85, 1), (1.0, 1.0, 1), (1.2, 1.15, 2)]

# Cores
PRATA = (200, 200, 215)
PRATA_CLARA = (238, 238, 248)
CONTORNO = (70, 70, 92)
FERRO = (52, 52, 64)
SUCO = (240, 90, 70)

TECLAS_ESQ = (pygame.K_LEFT, pygame.K_a)
TECLAS_DIR = (pygame.K_RIGHT, pygame.K_d)
TECLAS_CIMA = (pygame.K_UP, pygame.K_w)
TECLAS_BAIXO = (pygame.K_DOWN, pygame.K_s)
TECLAS_OK = (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)

# ------------------------------------------------------------
# MELHORIAS (cartas ao subir de nível)
# ------------------------------------------------------------
#   id: (nome, descrição, nível máximo, cor)
MELHORIAS = {
    "dano":     ("LIMÃO AZEDO", "+30% DE DANO NOS LIMÕES E NA ÓRBITA", 5, (250, 210, 50)),
    "cadencia": ("TIRO RÁPIDO", "JOGA LIMÕES 15% MAIS RÁPIDO", 5, (255, 150, 60)),
    "perfura":  ("LIMÃO PERFURANTE", "CADA LIMÃO ATRAVESSA +1 INIMIGO", 3, (120, 220, 120)),
    "multi":    ("MAIS LIMÕES", "+1 LIMÃO EM CADA ARREMESSO", 3, (255, 240, 120)),
    "orbita":   ("LIMÕES EM ÓRBITA", "+1 LIMÃO GIRANDO EM VOLTA DO OVO", 4, (140, 230, 90)),
    "sal":      ("AURA DE SAL", "SAL EM VOLTA DO OVO: MACHUCA E DEIXA LENTO", 4, (230, 235, 255)),
    "vida":     ("CASCA GROSSA", "+1 CORAÇÃO NO MÁXIMO (E CURA 1)", 3, (240, 80, 110)),
    "ima":      ("ÍMÃ DE XP", "PEGA CRISTAIS DE BEM MAIS LONGE", 3, (230, 70, 70)),
    "pes":      ("PÉS LIGEIROS", "O OVO ANDA 12% MAIS RÁPIDO", 3, (120, 200, 255)),
    "lanche":   ("LANCHINHO", "CURA 2 CORAÇÕES", 99, (240, 170, 110)),
}


def _xp_para(nivel):
    """XP necessário para sair do `nivel` atual."""
    return 4 + (nivel - 1) * 3


def _formatar_tempo(seg):
    seg = max(0, int(math.ceil(seg)))
    return f"{seg // 60}:{seg % 60:02d}"


# ============================================================
# DESENHOS (feitos uma vez só, com cache)
# ============================================================

_sprites = {}
Z = 2                           # desenha 2x maior e diminui (fica suave)


def _rosto(s, cx, cy, e=1.0, sobrancelha=(30, 30, 45), bravo=True):
    """Olhinhos bravos-fofos (mesmo estilo dos Invasores)."""
    for lado in (-1, 1):
        ex = cx + lado * 9 * e
        pygame.draw.circle(s, (30, 30, 40), (ex, cy), 7.5 * e)
        pygame.draw.circle(s, BRANCO, (ex, cy), 6 * e)
        pygame.draw.circle(s, (20, 20, 30), (ex - lado * 1.2 * e, cy + 1.8 * e), 3.4 * e)
        pygame.draw.circle(s, BRANCO, (ex - lado * 2 * e, cy), 1.2 * e)
        if bravo:
            pygame.draw.line(s, sobrancelha, (cx + lado * 17 * e, cy - 11 * e),
                             (cx + lado * 4 * e, cy - 6 * e), max(2, int(3.4 * e)))
    for lado in (-1, 1):
        pygame.draw.ellipse(s, (240, 140, 160), (cx + lado * 16 * e - 4 * e, cy + 6 * e, 8 * e, 5 * e))
    pygame.draw.ellipse(s, (90, 20, 40), (cx - 5 * e, cy + 9 * e, 10 * e, 7 * e))


def _pezinhos(s, cx, y, abertura=14, cor=(60, 60, 80)):
    for lado in (-1, 1):
        pygame.draw.ellipse(s, cor, (cx + lado * abertura - 9, y - 5, 18, 10))


def _colher():
    s = pygame.Surface((44 * Z, 60 * Z), pygame.SRCALPHA)
    cx = 44
    # Cabo (para baixo), pezinhos no fim
    cabo = pygame.Rect(cx - 7, 62, 14, 42)
    pygame.draw.rect(s, CONTORNO, cabo.inflate(6, 6), border_radius=7)
    pygame.draw.rect(s, PRATA, cabo, border_radius=6)
    pygame.draw.rect(s, PRATA_CLARA, (cabo.x + 3, cabo.y + 4, 3, 30), border_radius=2)
    _pezinhos(s, cx, 110, 12, CONTORNO)
    # Concha (cabeça)
    concha = pygame.Rect(cx - 34, 6, 68, 64)
    pygame.draw.ellipse(s, CONTORNO, concha.inflate(8, 8))
    pygame.draw.ellipse(s, PRATA, concha)
    pygame.draw.ellipse(s, (180, 180, 198), concha.inflate(-16, -14))
    pygame.draw.ellipse(s, PRATA_CLARA, (concha.x + 10, concha.y + 8, 16, 22))
    _rosto(s, cx, 40, 1.05)
    return s


def _frigideira():
    s = pygame.Surface((78 * Z, 56 * Z), pygame.SRCALPHA)
    # Cabo de madeira (para a direita)
    cabo = pygame.Rect(104, 44, 50, 16)
    pygame.draw.rect(s, (60, 35, 20), cabo.inflate(6, 6), border_radius=8)
    pygame.draw.rect(s, (150, 95, 55), cabo, border_radius=7)
    pygame.draw.circle(s, (60, 35, 20), (146, 52), 4)
    _pezinhos(s, 60, 104, 22, (40, 40, 50))
    # Panela redonda vista de cima (meio de lado)
    corpo = pygame.Rect(6, 8, 108, 92)
    pygame.draw.ellipse(s, (20, 20, 28), corpo.inflate(8, 8))
    pygame.draw.ellipse(s, (70, 70, 86), corpo)
    pygame.draw.ellipse(s, FERRO, corpo.inflate(-18, -18))
    pygame.draw.arc(s, (120, 120, 140), corpo.inflate(-8, -8), 1.8, 2.9, 4)
    _rosto(s, 60, 50, 1.2, sobrancelha=(220, 220, 235))
    return s


def _batedor():
    s = pygame.Surface((46 * Z, 62 * Z), pygame.SRCALPHA)
    cx = 46
    # Cabo com anel
    cabo = pygame.Rect(cx - 9, 80, 18, 30)
    pygame.draw.rect(s, CONTORNO, cabo.inflate(6, 6), border_radius=6)
    pygame.draw.rect(s, (230, 110, 120), cabo, border_radius=5)
    pygame.draw.rect(s, (255, 170, 175), (cabo.x + 3, cabo.y + 4, 4, 18), border_radius=2)
    _pezinhos(s, cx, 116, 12, CONTORNO)
    # 4 arcos de arame
    for w in (16, 38, 60, 80):
        pygame.draw.ellipse(s, CONTORNO, (cx - w // 2 - 2, 2, w + 4, 86), 7)
    for w in (16, 38, 60, 80):
        pygame.draw.ellipse(s, PRATA, (cx - w // 2, 4, w, 82), 3)
    # Cabecinha no meio
    pygame.draw.circle(s, CONTORNO, (cx, 44), 21)
    pygame.draw.circle(s, PRATA, (cx, 44), 18)
    pygame.draw.circle(s, PRATA_CLARA, (cx - 8, 36), 5)
    _rosto(s, cx, 44, 0.8)
    return s


def _liquidificador():
    """O chefe: copo com suco vermelho, tampa e base com botões."""
    s = pygame.Surface((120 * Z, 150 * Z), pygame.SRCALPHA)
    cx = 120
    # Base
    base = pygame.Rect(cx - 70, 216, 140, 70)
    pygame.draw.rect(s, (30, 30, 40), base.inflate(8, 8), border_radius=18)
    pygame.draw.rect(s, (70, 80, 110), base, border_radius=16)
    pygame.draw.rect(s, (100, 112, 150), (base.x + 10, base.y + 8, base.w - 20, 14), border_radius=7)
    for i, cor in enumerate(((120, 230, 120), (255, 210, 70), (240, 80, 80))):
        pygame.draw.circle(s, (20, 20, 30), (base.x + 36 + i * 34, base.y + 44), 11)
        pygame.draw.circle(s, cor, (base.x + 36 + i * 34, base.y + 44), 8)
    # Pezinhos
    _pezinhos(s, cx, 292, 44, (30, 30, 40))
    # Copo (trapézio) com suco
    copo = [(cx - 78, 30), (cx + 78, 30), (cx + 56, 218), (cx - 56, 218)]
    suco = [(cx - 70, 110), (cx + 70, 110), (cx + 55, 212), (cx - 55, 212)]
    pygame.draw.polygon(s, (30, 30, 40), [(x + (6 if x > cx else -6), y) for x, y in copo])
    pygame.draw.polygon(s, (190, 225, 245), copo)
    pygame.draw.polygon(s, SUCO, suco)
    pygame.draw.polygon(s, (255, 130, 110), [(cx - 70, 110), (cx + 70, 110), (cx + 68, 122), (cx - 68, 122)])
    # Bolhas no suco
    for bx, by, r in ((-30, 160, 7), (20, 180, 5), (36, 140, 6), (-10, 196, 4)):
        pygame.draw.circle(s, (255, 170, 150), (cx + bx, by), r, 2)
    # Lâmina no fundo
    pygame.draw.polygon(s, (210, 210, 225), [(cx - 30, 206), (cx, 198), (cx + 30, 206), (cx, 212)])
    # Brilho do vidro
    pygame.draw.polygon(s, (240, 250, 255), [(cx - 66, 40), (cx - 50, 40), (cx - 40, 200), (cx - 52, 200)])
    # Alça
    pygame.draw.rect(s, (30, 30, 40), (cx + 74, 60, 36, 110), 12, border_radius=18)
    pygame.draw.rect(s, (70, 80, 110), (cx + 76, 62, 32, 106), 7, border_radius=16)
    # Tampa
    tampa = pygame.Rect(cx - 86, 12, 172, 28)
    pygame.draw.rect(s, (30, 30, 40), tampa.inflate(8, 8), border_radius=12)
    pygame.draw.rect(s, (70, 80, 110), tampa, border_radius=10)
    pygame.draw.rect(s, (30, 30, 40), (cx - 16, 0, 32, 16), border_radius=6)
    pygame.draw.rect(s, (100, 112, 150), (cx - 12, 2, 24, 12), border_radius=5)
    # Rosto (em cima do vidro)
    _rosto(s, cx, 76, 1.9)
    return s


def _cristal(valor):
    cor = CORES_CRISTAL[valor]
    w, h = (14, 18) if valor < 10 else (20, 26)
    s = pygame.Surface((w * Z, h * Z), pygame.SRCALPHA)
    W, H = w * Z, h * Z
    pontos = [(W // 2, 1), (W - 2, H * 0.4), (W // 2, H - 1), (2, H * 0.4)]
    pygame.draw.polygon(s, ui.escurecer(cor, 90), pontos)
    interno = [(W // 2, 5), (W - 6, H * 0.4), (W // 2, H - 5), (6, H * 0.4)]
    pygame.draw.polygon(s, cor, interno)
    pygame.draw.polygon(s, ui.clarear(cor, 90), [(W // 2, 5), (W - 6, H * 0.4), (W // 2, H * 0.4)])
    return pygame.transform.smoothscale(s, (w, h))


def _gota():
    s = pygame.Surface((18 * Z, 18 * Z), pygame.SRCALPHA)
    pygame.draw.circle(s, (150, 30, 30), (18, 18), 17)
    pygame.draw.circle(s, SUCO, (18, 18), 13)
    pygame.draw.circle(s, (255, 190, 170), (13, 12), 5)
    return pygame.transform.smoothscale(s, (18, 18))


def _item(tipo):
    """Coração (cura) e ímã (puxa todos os cristais) caídos no chão."""
    s = pygame.Surface((30 * Z, 30 * Z), pygame.SRCALPHA)
    c = (30, 30)
    pygame.draw.circle(s, BRANCO, c, 29)
    pygame.draw.circle(s, (255, 225, 235) if tipo == "coracao" else (220, 230, 255), c, 25)
    if tipo == "coracao":
        ui.coracao(s, (30, 32), 34, (235, 60, 90))
    else:
        _desenhar_ima(s, c, 1.0)
    return pygame.transform.smoothscale(s, (30, 30))


def _desenhar_ima(s, c, e):
    x, y = c
    pygame.draw.arc(s, (150, 30, 30), (x - 16 * e, y - 16 * e, 32 * e, 32 * e), 0, math.pi, int(10 * e))
    pygame.draw.arc(s, (230, 70, 70), (x - 14 * e, y - 14 * e, 28 * e, 28 * e), 0, math.pi, int(7 * e))
    for lado in (-1, 1):
        pygame.draw.rect(s, (230, 70, 70), (x + lado * 11 * e - 5 * e, y, 10 * e, 8 * e))
        pygame.draw.rect(s, (220, 220, 230), (x + lado * 11 * e - 5 * e, y + 8 * e, 10 * e, 7 * e))


def _branco(sup):
    """Silhueta branca (flash quando o inimigo leva dano)."""
    s = sup.copy()
    s.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGBA_MAX)
    return s


def _sprite(nome, quadro=0, espelhar=False, branco=False):
    """Inimigos com 2 quadros (balançando), espelhados e em flash branco."""
    chave = (nome, quadro, espelhar, branco)
    s = _sprites.get(chave)
    if s is not None:
        return s
    if branco:
        s = _branco(_sprite(nome, quadro, espelhar))
    elif espelhar:
        s = pygame.transform.flip(_sprite(nome, quadro), True, False)
    elif nome in ("colher", "frigideira", "batedor", "chefe"):
        base = _sprites.get((nome, "base"))
        if base is None:
            grande = {"colher": _colher, "frigideira": _frigideira, "batedor": _batedor,
                      "chefe": _liquidificador}[nome]()
            w, h = grande.get_size()
            base = pygame.transform.smoothscale(grande, (w // Z, h // Z))
            _sprites[(nome, "base")] = base
        s = pygame.transform.rotozoom(base, 7 if quadro == 0 else -7, 1.0)
    elif nome == "cristal":
        s = _cristal(quadro)
    elif nome == "gota":
        s = _gota()
    elif nome == "limao":
        # 16 ângulos do limão girando
        s = pygame.transform.rotate(ui.limao_sup(RAIO_LIMAO), quadro * 360 / 16)
    else:
        s = _item(nome)
    _sprites[chave] = s
    return s


def _sombra(largura):
    s = _sprites.get(largura)            # chave = número (rápido)
    if s is None:
        s = pygame.Surface((largura, max(6, largura // 3)), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (60, 40, 30, 70), s.get_rect())
        _sprites[largura] = s
    return s


def _aura(raio):
    chave = ("aura", raio)
    s = _sprites.get(chave)
    if s is None:
        s = pygame.Surface((raio * 2 + 4, raio * 2 + 4), pygame.SRCALPHA)
        c = (raio + 2, raio + 2)
        pygame.draw.circle(s, (255, 255, 255, 38), c, raio)
        pygame.draw.circle(s, (255, 255, 255, 110), c, raio, 3)
        pygame.draw.circle(s, (220, 230, 255, 60), c, raio - 8, 2)
        _sprites[chave] = s
    return s


def _icone(chave):
    """Ícone 64x64 de cada melhoria (nas cartas)."""
    s = _sprites.get(("icone", chave))
    if s is not None:
        return s
    s = pygame.Surface((64, 64), pygame.SRCALPHA)
    c = (32, 32)
    lim = ui.limao_sup(12)
    if chave == "dano":
        ui.estrela(s, c, 30, (255, 120, 60))
        s.blit(pygame.transform.rotozoom(lim, 0, 1.3), pygame.transform.rotozoom(lim, 0, 1.3).get_rect(center=c))
    elif chave == "cadencia":
        for i in range(3):
            pygame.draw.line(s, (255, 200, 120), (4, 16 + i * 16), (22, 16 + i * 16), 3)
            s.blit(lim, lim.get_rect(center=(24 + i * 14, 16 + i * 16)))
    elif chave == "perfura":
        pygame.draw.line(s, (60, 140, 60), (4, 58), (60, 6), 5)
        pygame.draw.polygon(s, (60, 140, 60), [(60, 4), (46, 8), (56, 18)])
        s.blit(lim, lim.get_rect(center=c))
    elif chave == "multi":
        for ang in (-30, 0, 30):
            r = pygame.transform.rotate(lim, ang)
            a = math.radians(ang - 90)
            s.blit(r, r.get_rect(center=(32 + math.cos(a) * 18, 40 + math.sin(a) * 18)))
    elif chave == "orbita":
        pygame.draw.circle(s, (140, 200, 120), c, 22, 3)
        pygame.draw.ellipse(s, (240, 240, 230), (24, 22, 16, 20))
        for ang in (0.6, 3.7):
            s.blit(lim, lim.get_rect(center=(32 + math.cos(ang) * 22, 32 + math.sin(ang) * 22)))
    elif chave == "sal":
        corpo = pygame.Rect(18, 22, 28, 36)
        pygame.draw.rect(s, (80, 80, 100), corpo.inflate(4, 4), border_radius=8)
        pygame.draw.rect(s, (245, 245, 255), corpo, border_radius=7)
        pygame.draw.rect(s, (160, 165, 185), (16, 10, 32, 14), border_radius=6)
        for x in (24, 32, 40):
            pygame.draw.circle(s, (60, 60, 80), (x, 16), 2)
        for x, y in ((8, 8), (54, 12), (10, 30), (56, 34)):
            pygame.draw.circle(s, BRANCO, (x, y), 2)
    elif chave == "vida":
        ui.coracao(s, (32, 34), 50, (120, 20, 40))
        ui.coracao(s, (32, 32), 44, (240, 80, 110))
        pygame.draw.circle(s, (255, 190, 200), (22, 24), 4)
    elif chave == "ima":
        _desenhar_ima(s, (32, 30), 1.4)
    elif chave == "pes":
        for i in range(3):
            pygame.draw.line(s, (150, 210, 255), (4, 22 + i * 10), (20, 22 + i * 10), 3)
        pygame.draw.ellipse(s, (60, 60, 80), (20, 34, 38, 18))
        pygame.draw.ellipse(s, (120, 200, 255), (22, 36, 34, 14))
        pygame.draw.rect(s, (120, 200, 255), (22, 22, 16, 20), border_radius=6)
        pygame.draw.polygon(s, BRANCO, [(30, 24), (54, 10), (48, 26)])
    else:  # lanche: torradinha
        pygame.draw.rect(s, (130, 80, 40), (12, 12, 40, 42), border_radius=12)
        pygame.draw.rect(s, (240, 200, 140), (17, 17, 30, 32), border_radius=9)
        pygame.draw.rect(s, (250, 230, 120), (24, 26, 16, 12), border_radius=4)
    _sprites[("icone", chave)] = s
    return s


_arena = []


def _chao():
    """Piso da cozinha inteiro (ARENA_W x ARENA_H), desenhado uma vez."""
    if _arena:
        return _arena[0]
    sup = pygame.Surface((ARENA_W, ARENA_H))
    rnd = random.Random(33)

    # Lajotas em xadrez, com uma variação de tom em cada uma
    lado = 64
    for lin in range(ARENA_H // lado + 1):
        for col in range(ARENA_W // lado + 1):
            base = (222, 200, 162) if (lin + col) % 2 == 0 else (206, 182, 142)
            v = rnd.randint(-5, 5)
            cor = tuple(max(0, min(255, c + v)) for c in base)
            r = pygame.Rect(col * lado, lin * lado, lado, lado)
            pygame.draw.rect(sup, cor, r)
            pygame.draw.line(sup, ui.clarear(cor, 14), r.topleft, (r.right - 1, r.top), 2)
            pygame.draw.rect(sup, (184, 160, 122), r, 1)

    # Tapetes redondos
    for cx, cy, cor in ((520, 460, (190, 70, 70)), (1500, 1060, (70, 110, 180)),
                        (1560, 380, (90, 150, 90)), (480, 1150, (200, 140, 60))):
        for k, raio in enumerate(range(150, 0, -22)):
            c = cor if k % 2 == 0 else ui.clarear(cor, 50)
            pygame.draw.circle(sup, c, (cx, cy), raio)
        pygame.draw.circle(sup, ui.escurecer(cor, 50), (cx, cy), 150, 4)

    # Farinha espalhada e migalhas
    for _ in range(40):
        x, y = rnd.randrange(PAREDE, ARENA_W - PAREDE), rnd.randrange(PAREDE, ARENA_H - PAREDE)
        for _ in range(6):
            pygame.draw.circle(sup, (240, 234, 222), (x + rnd.randint(-14, 14), y + rnd.randint(-9, 9)),
                               rnd.randint(4, 9))
    for _ in range(260):
        x, y = rnd.randrange(PAREDE, ARENA_W - PAREDE), rnd.randrange(PAREDE, ARENA_H - PAREDE)
        pygame.draw.circle(sup, rnd.choice(((170, 120, 70), (150, 100, 55), (190, 150, 90))), (x, y),
                           rnd.choice((2, 2, 3)))
    # Ervilhas perdidas
    for _ in range(30):
        x, y = rnd.randrange(PAREDE, ARENA_W - PAREDE), rnd.randrange(PAREDE, ARENA_H - PAREDE)
        pygame.draw.circle(sup, (60, 120, 40), (x + 1, y + 2), 6)
        pygame.draw.circle(sup, (110, 190, 70), (x, y), 6)
        pygame.draw.circle(sup, (180, 230, 140), (x - 2, y - 2), 2)

    # Bancada de madeira em volta (a borda da arena)
    madeira, escura = (150, 104, 66), (104, 70, 44)
    for r in (pygame.Rect(0, 0, ARENA_W, PAREDE), pygame.Rect(0, ARENA_H - PAREDE, ARENA_W, PAREDE),
              pygame.Rect(0, 0, PAREDE, ARENA_H), pygame.Rect(ARENA_W - PAREDE, 0, PAREDE, ARENA_H)):
        pygame.draw.rect(sup, madeira, r)
    for _ in range(160):
        x, y = rnd.randrange(ARENA_W), rnd.randrange(ARENA_H)
        if PAREDE < x < ARENA_W - PAREDE and PAREDE < y < ARENA_H - PAREDE:
            continue
        pygame.draw.line(sup, escura, (x, y), (x + rnd.randint(10, 40), y), 1)
    interno = pygame.Rect(PAREDE, PAREDE, ARENA_W - 2 * PAREDE, ARENA_H - 2 * PAREDE)
    pygame.draw.rect(sup, escura, interno.inflate(8, 8), 4)
    pygame.draw.rect(sup, (120, 90, 60), interno.inflate(2, 2), 2)

    if pygame.display.get_surface() is not None:
        sup = sup.convert()
    _arena.append(sup)
    return sup


# ============================================================
# PEÇAS DO JOGO
# ============================================================

class Inimigo:

    __slots__ = ("tipo", "x", "y", "kx", "ky", "vida", "vida_max", "vel", "raio", "xp",
                 "flash", "fase", "orb_cd", "esq", "chefe", "estado", "t_estado", "dx", "dy",
                 "ciclo", "ferido")

    def __init__(self, tipo, x, y, mult_vida):
        vida, vel, raio, xp = TIPOS.get(tipo, (VIDA_CHEFE, 70, 46, 0))
        self.tipo = tipo
        self.x, self.y = x, y
        self.kx = self.ky = 0.0         # empurrão (knockback)
        self.vida = self.vida_max = vida * mult_vida
        self.vel = vel * random.uniform(0.9, 1.1)
        self.raio = raio
        self.xp = xp
        self.flash = 0.0
        self.fase = random.uniform(0, math.tau)
        self.orb_cd = 0.0
        self.esq = False
        self.chefe = tipo == "chefe"
        self.estado = "andar"
        self.t_estado = 0.0
        self.dx = self.dy = 0.0
        self.ciclo = 0
        self.ferido = 0.0               # tempo desde o último dano (som)


class Limao:

    __slots__ = ("x", "y", "vx", "vy", "dano", "fura", "acertou", "vida", "giro")

    def __init__(self, x, y, vx, vy, dano, fura):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.dano = dano
        self.fura = fura
        self.acertou = set()
        self.vida = 1.3
        self.giro = random.uniform(0, 16)


# ============================================================
# JOGO
# ============================================================

class OvoSobrevivente(MiniJogo):

    ID = "ovo_sobrevivente"
    TITULO = "OVO SOBREVIVENTE"
    TITULO_CURTO = "SOBREVIVENTE"
    DESCRICAO = "Sobreviva 3 minutos contra a cozinha rebelde! O ovo joga limões sozinho; escolha melhorias."
    COR = (200, 120, 60)
    INSTRUCOES = [
        "Colheres, frigideiras e batedores querem o seu ovo!",
        "O ovo joga LIMÕES sozinho. Você só ANDA e pega os CRISTAIS.",
        "Subiu de nível? Escolha 1 de 3 melhorias.",
        "Sobreviva 3:00! Aos 2:00 chega o LIQUIDIFICADOR.",
        "SETAS/WASD andam • MOUSE segurado • 1 2 3 escolhem",
    ]
    OPCOES = ["FÁCIL", "NORMAL", "DIFÍCIL"]
    MENOR_MELHOR = False
    ROTULO_PONTOS = "PONTOS"
    CONTAGEM = True

    MOEDAS_POR = 60
    MOEDAS_MAX = 50
    MOEDAS_VITORIA = 10
    MOEDAS_MIN = 2

    # --------------------------------------------------------
    # CENÁRIO
    # --------------------------------------------------------

    @classmethod
    def criar_fundo(cls, jogador):
        # Um pedaço do meio da cozinha (tapete vermelho à esquerda)
        sup = pygame.Surface((LARGURA, ALTURA))
        sup.blit(_chao(), (0, 0), pygame.Rect(120, 160, LARGURA, ALTURA))
        return sup

    @classmethod
    def desenhar_icone(cls, sup, jogador):
        w, h = sup.get_size()
        for i, tipo in enumerate(("colher", "frigideira", "batedor")):
            s = _sprite(tipo, i % 2, i == 2)
            k = h * 0.3 / s.get_height()
            s = pygame.transform.smoothscale(s, (max(1, int(s.get_width() * k)), max(1, int(h * 0.3))))
            ang = (-0.5 + i * 0.5) * math.pi * 0.7 - math.pi / 2
            sup.blit(s, s.get_rect(center=(w // 2 + math.cos(ang) * w * 0.34,
                                           h * 0.56 + math.sin(ang) * h * 0.36)))
        jogador.desenhar(sup, (w // 2, int(h * 0.62)), h * 0.3)
        for dx in (-0.2, 0.2):
            ui.limao(sup, (int(w * (0.5 + dx)), int(h * 0.42)), max(4, h // 22))

    # --------------------------------------------------------
    # PARTIDA
    # --------------------------------------------------------

    def reiniciar(self):
        dif = DIFICULDADE[self.opcao] if self.opcao < len(DIFICULDADE) else DIFICULDADE[1]
        self.mult_qtd, self.mult_vida, self.dano_chefe = dif

        self.x = ARENA_W / 2
        self.y = ARENA_H / 2
        self.vx = self.vy = 0.0
        self.esq = False
        self.andando = 0.0
        self.teclas = set()
        self.mouse_apertado = False
        self.mouse_pos = (LARGURA // 2, ALTURA // 2)
        self.cam_x, self.cam_y = self._camera_alvo()

        self.vida_max = VIDAS[min(self.opcao, 2)]
        self.vidas = self.vida_max
        self.invencivel = 0.0
        self.dor = 0.0                      # vermelhinho na tela ao tomar dano
        self.morto = False
        self.tempo_morto = 0.0
        self.sobreviveu = False
        self.tempo_vitoria = 0.0

        self.relogio = 0.0
        self.nivel = 1
        self.xp = 0
        self.xp_barra = 0.0                 # barra de XP animada
        self.abates = 0
        self.pendentes = 0                  # níveis esperando escolha
        self.escolha = None                 # cartas na tela (dict) ou None
        self.up = {k: 0 for k in MELHORIAS}

        self.inimigos = []
        self.limoes = []
        self.gotas = []
        self.cristais = []                  # [x, y, valor, puxando]
        self.itens = []                     # [x, y, tipo]
        self.recarga = 0.6
        self.ang_orbita = 0.0
        self.tique_sal = 0.0
        self.acumulado = 0.0                # frações de inimigo para nascer
        self.proxima_onda = 30.0
        self.chefe = None
        self.chefe_veio = False
        self.aviso = ""                     # letreiro grande no meio
        self.t_aviso = 0.0
        self.cd_som_acerto = 0.0
        self.cd_som_cristal = 0.0
        self.cd_tremor = 0.0
        self.ima_total = 0.0                # ímã pego: todos os cristais vêm
        self.pontos = self._calcular_pontos()

    def _calcular_pontos(self):
        return self.abates * 10 + self.nivel * 50 + (500 if self.sobreviveu else 0)

    # Atributos que dependem das melhorias ---------------------

    def _dano(self):
        return DANO_BASE * (1 + 0.3 * self.up["dano"])

    def _recarga(self):
        return RECARGA_BASE * 0.85 ** self.up["cadencia"]

    def _vel(self):
        return VEL_OVO * (1 + 0.12 * self.up["pes"])

    def _raio_ima(self):
        return RAIO_IMA * (1 + 0.7 * self.up["ima"])

    def _raio_sal(self):
        return 62 + 16 * self.up["sal"]

    # --------------------------------------------------------
    # CONTROLES
    # --------------------------------------------------------

    def evento(self, e):
        # Acompanha teclas e mouse em qualquer estado
        if e.type == pygame.KEYDOWN:
            self.teclas.add(e.key)
        elif e.type == pygame.KEYUP:
            self.teclas.discard(e.key)
        elif e.type == pygame.MOUSEMOTION:
            self.mouse_pos = e.pos
        elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
            self.mouse_apertado = False
        elif e.type == pygame.WINDOWFOCUSLOST:
            self.teclas.clear()
            self.mouse_apertado = False
        super().evento(e)

    def evento_jogo(self, e):
        if self.escolha is not None:
            self._evento_cartas(e)
            return
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.mouse_pos = e.pos
            self.mouse_apertado = True

    def _evento_cartas(self, e):
        esc = self.escolha
        if esc["t"] < 0.3:                  # evita escolher sem querer
            return
        n = len(esc["opcoes"])
        if e.type == pygame.KEYDOWN:
            numeros = {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2,
                       pygame.K_KP1: 0, pygame.K_KP2: 1, pygame.K_KP3: 2}
            if e.key in numeros and numeros[e.key] < n:
                self._escolher(numeros[e.key])
            elif e.key in TECLAS_ESQ:
                esc["indice"] = (esc["indice"] - 1) % n
                self.som("clique", 0.5)
            elif e.key in TECLAS_DIR:
                esc["indice"] = (esc["indice"] + 1) % n
                self.som("clique", 0.5)
            elif e.key in TECLAS_OK:
                self._escolher(esc["indice"])
        elif e.type == pygame.MOUSEMOTION:
            for i, r in enumerate(self._rects_cartas()):
                if r.collidepoint(e.pos) and esc["indice"] != i:
                    esc["indice"] = i
                    self.som("clique", 0.4)
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for i, r in enumerate(self._rects_cartas()):
                if r.collidepoint(e.pos):
                    self._escolher(i)
                    break

    # --------------------------------------------------------
    # SUBIR DE NÍVEL
    # --------------------------------------------------------

    def _abrir_cartas(self):
        disponiveis = [k for k, m in MELHORIAS.items() if k != "lanche" and self.up[k] < m[2]]
        random.shuffle(disponiveis)
        opcoes = disponiveis[:3]
        # Machucado? Às vezes o LANCHINHO aparece no lugar de uma carta
        if self.vidas < self.vida_max and (len(opcoes) < 3 or random.random() < 0.35):
            if len(opcoes) >= 3:
                opcoes[2] = "lanche"
            else:
                opcoes.append("lanche")
        if not opcoes:
            opcoes = ["lanche"]
        self.escolha = {"opcoes": opcoes, "indice": 0, "t": 0.0}
        self.mouse_apertado = False

    def _escolher(self, i):
        chave = self.escolha["opcoes"][i]
        self.up[chave] += 1
        nome, _, _, cor = MELHORIAS[chave]
        nome = tr(nome)
        if chave == "vida":
            self.vida_max += 1
            self.vidas = min(self.vida_max, self.vidas + 1)
        elif chave == "lanche":
            self.vidas = min(self.vida_max, self.vidas + 2)
        self.som("selecionar")
        self.textos.adicionar(nome + "!", (self.x, self.y - 60), cor, 14)
        self.particulas.explodir((self.x, self.y), [cor, BRANCO, AMARELO], 26, 260, 0.7)
        self.invencivel = max(self.invencivel, 0.6)     # um respiro depois da escolha
        self.escolha = None
        self.pendentes -= 1
        if self.pendentes > 0:
            self._abrir_cartas()

    def _ganhar_xp(self, valor):
        self.xp += valor
        while self.xp >= _xp_para(self.nivel):
            self.xp -= _xp_para(self.nivel)
            self.nivel += 1
            self.pendentes += 1
            self.som("levelup", 0.8)
            self.textos.adicionar(tr("NÍVEL {n}!", n=self.nivel), (self.x, self.y - 70), (140, 230, 255), 18)
            self.particulas.explodir((self.x, self.y), [(140, 230, 255), BRANCO, AMARELO], 30, 300,
                                     0.8, gravidade=0)
        if self.pendentes > 0 and self.escolha is None and not self.morto:
            self._abrir_cartas()

    # --------------------------------------------------------
    # LÓGICA
    # --------------------------------------------------------

    def atualizar_jogo(self, dt):
        self.pontos = self._calcular_pontos()
        # Barra de XP corre atrás do valor de verdade
        alvo = self.xp / _xp_para(self.nivel)
        if alvo < self.xp_barra:
            self.xp_barra = alvo
        self.xp_barra += (alvo - self.xp_barra) * min(1.0, dt * 10)

        # Cartas na tela: o mundo congela
        if self.escolha is not None:
            self.escolha["t"] += dt
            return

        if self.morto:
            self.tempo_morto += dt
            if self.tempo_morto > 1.6:
                self._fim()
            return
        if self.sobreviveu:
            self.tempo_vitoria += dt
            self._mover_ovo(dt)
            self._atualizar_cristais(dt)
            self._atualizar_camera(dt)
            if self.tempo_vitoria > 2.2:
                self._fim()
            return

        self.relogio += dt
        self.invencivel = max(0.0, self.invencivel - dt)
        self.dor = max(0.0, self.dor - dt)
        self.t_aviso = max(0.0, self.t_aviso - dt)
        self.cd_som_acerto -= dt
        self.cd_som_cristal -= dt
        self.cd_tremor -= dt
        self.ima_total = max(0.0, self.ima_total - dt)

        self._mover_ovo(dt)
        self._atualizar_camera(dt)
        self._nascer(dt)
        self._atirar(dt)
        self._mover_limoes(dt)
        self._mover_inimigos(dt)
        self._orbita_e_sal(dt)
        self._mover_gotas(dt)
        self._atualizar_cristais(dt)
        self._pegar_itens()
        self.inimigos = [i for i in self.inimigos if i.vida > 0]

        if self.relogio >= DURACAO and not self.morto:
            self._vencer()

    def _mover_ovo(self, dt):
        dx = dy = 0.0
        if any(t in self.teclas for t in TECLAS_ESQ):
            dx -= 1
        if any(t in self.teclas for t in TECLAS_DIR):
            dx += 1
        if any(t in self.teclas for t in TECLAS_CIMA):
            dy -= 1
        if any(t in self.teclas for t in TECLAS_BAIXO):
            dy += 1
        if not (dx or dy) and self.mouse_apertado:
            # Mouse segurado: anda na direção do ponteiro
            mx = self.mouse_pos[0] + self.cam_x - self.x
            my = self.mouse_pos[1] + self.cam_y - self.y
            d = math.hypot(mx, my)
            if d > 12:
                dx, dy = mx / d, my / d
        d = math.hypot(dx, dy)
        vel = self._vel()
        if d > 0:
            dx, dy = dx / d, dy / d
            if dx:
                self.esq = dx < 0
        # Um pouquinho de aceleração (fica macio)
        k = min(1.0, dt * 14)
        self.vx += (dx * vel - self.vx) * k
        self.vy += (dy * vel - self.vy) * k
        self.x = max(PAREDE + RAIO_OVO, min(ARENA_W - PAREDE - RAIO_OVO, self.x + self.vx * dt))
        self.y = max(PAREDE + RAIO_OVO + 10, min(ARENA_H - PAREDE - RAIO_OVO, self.y + self.vy * dt))
        if d > 0:
            self.andando += dt
        else:
            self.andando = 0.0

    def _camera_alvo(self):
        cx = max(0, min(ARENA_W - LARGURA, self.x - LARGURA / 2))
        cy = max(0, min(ARENA_H - ALTURA, self.y - ALTURA / 2))
        return cx, cy

    def _atualizar_camera(self, dt):
        ax, ay = self._camera_alvo()
        k = min(1.0, dt * 8)
        self.cam_x += (ax - self.cam_x) * k
        self.cam_y += (ay - self.cam_y) * k

    # Inimigos nascendo -----------------------------------------

    def _sortear_tipo(self):
        t = self.relogio
        if t < 20:
            return "colher"
        r = random.random()
        if t < 50:
            return "colher" if r < 0.7 else "frigideira"
        if t < 100:
            return "colher" if r < 0.45 else ("frigideira" if r < 0.7 else "batedor")
        return "colher" if r < 0.35 else ("frigideira" if r < 0.68 else "batedor")

    def _ponto_fora_da_tela(self, ang=None, dist=None):
        ang = random.uniform(0, math.tau) if ang is None else ang
        dist = random.uniform(600, 680) if dist is None else dist
        x = self.x + math.cos(ang) * dist
        y = self.y + math.sin(ang) * dist
        return (max(PAREDE + 20, min(ARENA_W - PAREDE - 20, x)),
                max(PAREDE + 20, min(ARENA_H - PAREDE - 20, y)))

    def _novo_inimigo(self, tipo, x, y):
        # Os inimigos ficam mais fortes com o tempo (x2,2 no fim)
        mult = self.mult_vida * (1 + self.relogio / 150)
        ini = Inimigo(tipo, x, y, mult)
        ini.vel *= 1 + self.relogio / 600          # e mais rápidos também
        self.inimigos.append(ini)
        return ini

    def _nascer(self, dt):
        # Taxa contínua: cada vez mais inimigos por segundo
        taxa = (0.7 + self.relogio * 0.036) * self.mult_qtd
        if self.chefe is not None:
            taxa *= 0.6                     # o chefe já dá trabalho
        self.acumulado += taxa * dt
        while self.acumulado >= 1:
            self.acumulado -= 1
            if len(self.inimigos) < MAX_INIMIGOS:
                self._novo_inimigo(self._sortear_tipo(), *self._ponto_fora_da_tela())

        # Onda: um anel de inimigos fechando em volta do ovo
        if self.relogio >= self.proxima_onda:
            self.proxima_onda += 30.0
            if abs(self.proxima_onda - 30.0 - TEMPO_CHEFE) > 1:
                n = int((8 + self.relogio / 7) * self.mult_qtd)
                tipo = self._sortear_tipo()
                for k in range(n):
                    if len(self.inimigos) >= MAX_INIMIGOS:
                        break
                    ang = k * math.tau / n
                    self._novo_inimigo(tipo, *self._ponto_fora_da_tela(ang, 560))
                self._avisar("ONDA!", 1.4)
                self.som("asa", 0.7)

        # O CHEFE!
        if not self.chefe_veio and self.relogio >= TEMPO_CHEFE - 4 and self.t_aviso <= 0 \
                and self.relogio < TEMPO_CHEFE:
            self._avisar("CUIDADO: O CHEFE VEM AÍ!", 3.0)
            self.som("erro", 0.6)
        if not self.chefe_veio and self.relogio >= TEMPO_CHEFE:
            self.chefe_veio = True
            x, y = self._ponto_fora_da_tela(random.uniform(0, math.tau), 520)
            self.chefe = self._novo_inimigo("chefe", x, y)
            self.chefe.vida = self.chefe.vida_max = VIDA_CHEFE * self.mult_vida
            self.chefe.vel = 72
            self._avisar("LIQUIDIFICADOR!", 2.0)
            self.som("explosao", 0.8)
            self.tremer(0.4)

    def _avisar(self, msg, tempo):
        self.aviso = msg
        self.t_aviso = tempo

    # Limões -----------------------------------------------------

    def _mais_perto(self, n):
        limite = ALCANCE * ALCANCE
        perto = []
        for ini in self.inimigos:
            if ini.vida <= 0:
                continue
            d = (ini.x - self.x) ** 2 + (ini.y - self.y) ** 2
            if d < limite:
                perto.append((d, id(ini), ini))
        return [p[2] for p in heapq.nsmallest(n, perto)]

    def _atirar(self, dt):
        self.recarga -= dt
        if self.recarga > 0:
            return
        qtd = 1 + self.up["multi"]
        alvos = self._mais_perto(qtd)
        if not alvos:
            self.recarga = 0.1
            return
        self.recarga = self._recarga()
        dano = self._dano()
        fura = self.up["perfura"]
        for k in range(qtd):
            alvo = alvos[k % len(alvos)]
            ang = math.atan2(alvo.y - self.y, alvo.x - self.x)
            if k >= len(alvos):
                ang += (k - len(alvos) + 1) * 0.35 * (1 if k % 2 else -1)
            self.limoes.append(Limao(self.x, self.y - 8, math.cos(ang) * VEL_LIMAO,
                                     math.sin(ang) * VEL_LIMAO, dano, fura))
        self.som("pulo", 0.22)

    def _mover_limoes(self, dt):
        vivos = []
        for lm in self.limoes:
            lm.vida -= dt
            lm.x += lm.vx * dt
            lm.y += lm.vy * dt
            lm.giro += dt * 30
            morreu = lm.vida <= 0
            if not morreu:
                for ini in self.inimigos:
                    if ini.vida <= 0 or id(ini) in lm.acertou:
                        continue
                    r = ini.raio + RAIO_LIMAO
                    if abs(ini.x - lm.x) < r and abs(ini.y - lm.y) < r and \
                            (ini.x - lm.x) ** 2 + (ini.y - lm.y) ** 2 < r * r:
                        lm.acertou.add(id(ini))
                        self._ferir(ini, lm.dano, lm.vx, lm.vy)
                        if lm.fura <= 0:
                            morreu = True
                            self.particulas.explodir((lm.x, lm.y), [(250, 222, 40), (255, 248, 180)],
                                                     5, 130, 0.3, (2, 4))
                            break
                        lm.fura -= 1
            if not morreu:
                vivos.append(lm)
        self.limoes = vivos

    def _ferir(self, ini, dano, vx=0.0, vy=0.0, empurrao=160):
        """Dano com flash branco, número flutuante e empurrãozinho."""
        critico = random.random() < 0.12
        if critico:
            dano *= 2
        ini.vida -= dano
        ini.flash = 0.1
        # Empurrão (o chefe quase não sai do lugar)
        v = math.hypot(vx, vy)
        if v > 0:
            forca = empurrao * (0.15 if ini.chefe else 1.0)
            ini.kx += vx / v * forca
            ini.ky += vy / v * forca
        n = str(int(round(dano)))
        if critico:
            self.textos.adicionar(n + "!", (ini.x, ini.y - ini.raio - 10), LARANJA, 16)
            if self.cd_tremor <= 0:
                self.tremer(0.06)
                self.cd_tremor = 0.3
        else:
            self.textos.adicionar(n, (ini.x + random.randint(-8, 8), ini.y - ini.raio - 6), BRANCO, 10)
        if len(self.textos.lista) > 45:
            del self.textos.lista[:len(self.textos.lista) - 45]
        if ini.vida <= 0:
            self._abater(ini)
        elif self.cd_som_acerto <= 0:
            self.som("bater", 0.25)
            self.cd_som_acerto = 0.07

    def _abater(self, ini):
        self.abates += 1
        cores = {"colher": [PRATA, PRATA_CLARA, (160, 160, 180)],
                 "frigideira": [FERRO, (90, 90, 110), (150, 95, 55)],
                 "batedor": [PRATA, (230, 110, 120), PRATA_CLARA],
                 "chefe": [SUCO, (190, 225, 245), (70, 80, 110), AMARELO]}[ini.tipo]
        if ini.chefe:
            self.chefe = None
            self.tremer(0.6)
            self.app._flash = 0.25
            self.som("explosao")
            self.som("vencer", 0.6)
            self.particulas.explodir((ini.x, ini.y), cores + [BRANCO], 70, 520, 1.2, (4, 9))
            self._avisar("CHEFE DERROTADO!", 2.2)
            for _ in range(14):
                a = random.uniform(0, math.tau)
                d = random.uniform(10, 70)
                self.cristais.append([ini.x + math.cos(a) * d, ini.y + math.sin(a) * d, 10, False])
            self.itens.append([ini.x, ini.y, "coracao"])
            return
        self.particulas.explodir((ini.x, ini.y), cores + [(250, 222, 40)], 10, 200, 0.5, (2, 5))
        if self.cd_som_acerto <= 0:
            self.som("acerto", 0.35)
            self.cd_som_acerto = 0.06
        # Cristal de XP (ou um item raro)
        self._soltar_cristal(ini.x, ini.y, ini.xp)
        r = random.random()
        if r < 0.01:
            self.itens.append([ini.x, ini.y, "coracao"])
        elif r < 0.015:
            self.itens.append([ini.x, ini.y, "ima"])

    def _soltar_cristal(self, x, y, valor):
        if len(self.cristais) >= MAX_CRISTAIS:
            # Cristais demais: o valor vai para um cristal que já existe
            c = random.choice(self.cristais)
            c[2] = 10 if c[2] + valor >= 10 else (3 if c[2] + valor >= 3 else c[2])
            return
        self.cristais.append([x, y, valor, False])

    # Inimigos ---------------------------------------------------

    def _mover_inimigos(self, dt):
        grade = {}
        raio_sal2 = self._raio_sal() ** 2 if self.up["sal"] else -1
        for ini in self.inimigos:
            ini.flash = max(0.0, ini.flash - dt)
            ini.orb_cd = max(0.0, ini.orb_cd - dt)
            dx, dy = self.x - ini.x, self.y - ini.y
            d = math.hypot(dx, dy) or 1.0
            nx, ny = dx / d, dy / d
            vel = ini.vel
            if d * d < raio_sal2:
                vel *= 0.6                  # o sal deixa lento

            if ini.chefe:
                mvx, mvy = self._comportamento_chefe(ini, dt, nx, ny, vel)
            elif ini.tipo == "batedor":
                # Zigue-zague girando
                w = math.sin(self.tempo * 4 + ini.fase) * 0.8
                mvx, mvy = (nx - ny * w) * vel, (ny + nx * w) * vel
            else:
                mvx, mvy = nx * vel, ny * vel

            ini.x += (mvx + ini.kx) * dt
            ini.y += (mvy + ini.ky) * dt
            atrito = math.exp(-dt * 9)
            ini.kx *= atrito
            ini.ky *= atrito
            if abs(mvx) > 5:
                ini.esq = mvx < 0
            ini.x = max(PAREDE, min(ARENA_W - PAREDE, ini.x))
            ini.y = max(PAREDE, min(ARENA_H - PAREDE, ini.y))

            # Encostou no ovo
            if d < ini.raio + RAIO_OVO - 4:
                self._tomar_dano(self.dano_chefe if ini.chefe else 1, ini)

            if not ini.chefe:
                grade.setdefault((int(ini.x // CELULA), int(ini.y // CELULA)), []).append(ini)

        # Separação simples: quem divide a mesma célula se afasta
        for lista in grade.values():
            if len(lista) < 2:
                continue
            for i in range(len(lista)):
                a = lista[i]
                for j in range(i + 1, len(lista)):
                    b = lista[j]
                    dx, dy = b.x - a.x, b.y - a.y
                    d2 = dx * dx + dy * dy
                    lim = (a.raio + b.raio) * 0.8
                    if d2 < lim * lim:
                        d = math.sqrt(d2) or 0.01
                        emp = (lim - d) * 0.5
                        if d2 == 0:
                            dx, dy, d = random.uniform(-1, 1), 1.0, 1.0
                        a.x -= dx / d * emp
                        a.y -= dy / d * emp
                        b.x += dx / d * emp
                        b.y += dy / d * emp

    def _comportamento_chefe(self, ini, dt, nx, ny, vel):
        """Anda -> treme carregando -> investe (ou solta um anel de suco)."""
        ini.t_estado += dt
        if ini.estado == "andar":
            if ini.t_estado > 2.8:
                ini.estado, ini.t_estado = "carregar", 0.0
                ini.dx, ini.dy = nx, ny
                self.som("boing", 0.6)
            return nx * vel, ny * vel
        if ini.estado == "carregar":
            ini.dx, ini.dy = nx, ny          # mira até o último instante
            if ini.t_estado > 0.75:
                ini.ciclo += 1
                if ini.ciclo % 2 == 0:
                    self._anel_suco(ini)
                    ini.estado, ini.t_estado = "andar", 0.0
                else:
                    ini.estado, ini.t_estado = "investir", 0.0
                    self.som("bater", 0.8)
                    self.tremer(0.12)
            return 0.0, 0.0
        # Investida
        if ini.t_estado > 0.6:
            ini.estado, ini.t_estado = "andar", 0.0
        if random.random() < 0.5:
            self.particulas.explodir((ini.x, ini.y + 60), [(240, 234, 222), (200, 180, 150)], 2, 80,
                                     0.4, (3, 6), gravidade=0)
        return ini.dx * 520, ini.dy * 520

    def _anel_suco(self, ini):
        n = 10 if self.opcao < 2 else 14
        base = random.uniform(0, math.tau)
        for k in range(n):
            a = base + k * math.tau / n
            self.gotas.append([ini.x, ini.y, math.cos(a) * 210, math.sin(a) * 210, 3.5])
        self.particulas.explodir((ini.x, ini.y - 20), [SUCO, (255, 170, 150)], 20, 260, 0.6)
        self.som("explosao", 0.4)

    def _mover_gotas(self, dt):
        vivas = []
        for g in self.gotas:
            g[0] += g[2] * dt
            g[1] += g[3] * dt
            g[4] -= dt
            if (g[0] - self.x) ** 2 + (g[1] - self.y) ** 2 < (RAIO_OVO + 7) ** 2:
                self._tomar_dano(1, None)
                continue
            if g[4] > 0:
                vivas.append(g)
        self.gotas = vivas

    def _orbita_e_sal(self, dt):
        # Limões em órbita: cada um bate no mesmo inimigo a cada 0,4 s
        n = self.up["orbita"]
        if n:
            self.ang_orbita += dt * 3.2
            dano = DANO_ORBITA * (1 + 0.3 * self.up["dano"])
            for k in range(n):
                a = self.ang_orbita + k * math.tau / n
                ox = self.x + math.cos(a) * RAIO_ORBITA
                oy = self.y + math.sin(a) * RAIO_ORBITA
                for ini in self.inimigos:
                    if ini.vida <= 0 or ini.orb_cd > 0:
                        continue
                    r = ini.raio + RAIO_LIMAO + 2
                    if abs(ini.x - ox) < r and abs(ini.y - oy) < r:
                        ini.orb_cd = 0.4
                        self._ferir(ini, dano, ini.x - self.x, ini.y - self.y, 220)

        # Aura de sal: dano de pouquinho em pouquinho
        if self.up["sal"]:
            self.tique_sal -= dt
            if self.tique_sal <= 0:
                self.tique_sal = 0.5
                r2 = self._raio_sal() ** 2
                dano = 2 + 2 * self.up["sal"]
                for ini in self.inimigos:
                    if ini.vida > 0 and (ini.x - self.x) ** 2 + (ini.y - self.y) ** 2 < r2:
                        self._ferir(ini, dano, ini.x - self.x, ini.y - self.y, 60)

    def _tomar_dano(self, qtd, ini):
        if self.invencivel > 0 or self.morto or self.sobreviveu:
            return
        self.vidas -= qtd
        self.invencivel = TEMPO_INVENCIVEL
        self.dor = 0.35
        self.tremer(0.3)
        self.particulas.explodir((self.x, self.y), [self.jogador.cor, BRANCO, (255, 240, 170)], 18, 240, 0.6)
        # Empurra quem bateu (dá um espacinho para fugir)
        for outro in self.inimigos:
            dx, dy = outro.x - self.x, outro.y - self.y
            d2 = dx * dx + dy * dy
            if d2 < 110 * 110:
                d = math.sqrt(d2) or 1.0
                forca = 60 if outro.chefe else 420
                outro.kx += dx / d * forca
                outro.ky += dy / d * forca
        if self.vidas <= 0:
            self.vidas = 0
            self.morto = True
            self.tempo_morto = 0.0
            self.som("explosao", 0.8)
            self.tremer(0.5)
            self.particulas.explodir((self.x, self.y), [self.jogador.cor, BRANCO, AMARELO], 40, 320, 1.0)
        else:
            self.som("erro", 0.8)
            self.textos.adicionar(tr("AI!"), (self.x, self.y - 50), (255, 110, 110), 16)

    # Cristais e itens ---------------------------------------------

    def _atualizar_cristais(self, dt):
        r_ima = self._raio_ima()
        r_ima2 = r_ima * r_ima
        todos = self.ima_total > 0 or self.sobreviveu
        vivos = []
        pegou = 0
        for c in self.cristais:
            dx, dy = self.x - c[0], self.y - c[1]
            d2 = dx * dx + dy * dy
            if d2 < 22 * 22:
                pegou += c[2]
                continue
            if not c[3] and (d2 < r_ima2 or todos):
                c[3] = True
            if c[3]:
                d = math.sqrt(d2)
                v = 380 + max(0.0, 700 - d) * 0.6 if not todos else 900
                c[0] += dx / d * v * dt
                c[1] += dy / d * v * dt
            vivos.append(c)
        self.cristais = vivos
        if pegou:
            if self.cd_som_cristal <= 0:
                self.som("tic", 0.35)
                self.cd_som_cristal = 0.05
            if not self.sobreviveu:
                self._ganhar_xp(pegou)

    def _pegar_itens(self):
        vivos = []
        for it in self.itens:
            if (it[0] - self.x) ** 2 + (it[1] - self.y) ** 2 < 34 * 34:
                if it[2] == "coracao":
                    self.vidas = min(self.vida_max, self.vidas + 1)
                    self.textos.adicionar(tr("+1 CORAÇÃO"), (self.x, self.y - 60), (255, 120, 150), 14)
                    self.particulas.explodir((self.x, self.y), [(235, 60, 90), (255, 190, 200), BRANCO],
                                             20, 200, 0.6)
                else:
                    self.ima_total = 3.0
                    self.textos.adicionar(tr("ÍMÃ!"), (self.x, self.y - 60), (255, 120, 120), 16)
                    self.particulas.explodir((self.x, self.y), [(230, 70, 70), BRANCO], 20, 220, 0.6)
                self.som("moeda", 0.8)
                continue
            vivos.append(it)
        self.itens = vivos

    # Fim de partida ---------------------------------------------

    def _vencer(self):
        self.sobreviveu = True
        self.tempo_vitoria = 0.0
        self.relogio = DURACAO
        self.pontos = self._calcular_pontos()
        self._avisar("VOCÊ SOBREVIVEU!", 3.0)
        self.som("conquista")
        self.tremer(0.3)
        # Todos os utensílios "fogem" num puf de fumaça
        for ini in self.inimigos:
            if abs(ini.x - self.x) < LARGURA and abs(ini.y - self.y) < ALTURA:
                self.particulas.explodir((ini.x, ini.y), [(240, 240, 240), (200, 200, 210)], 4, 120,
                                         0.5, (3, 6), gravidade=-60)
        self.inimigos.clear()
        self.gotas.clear()
        self.limoes.clear()
        self.chefe = None
        self.particulas.explodir((self.x, self.y - 40), [AMARELO, (255, 90, 140), (120, 200, 255), BRANCO],
                                 60, 420, 1.4, (3, 7), 380)

    def _fim(self):
        self.pontos = self._calcular_pontos()
        linhas = [tr("PONTOS: {n}", n=self.pontos),
                  tr("TEMPO: {tempo} • NÍVEL {n}", tempo=_formatar_tempo(self.relogio), n=self.nivel),
                  tr("INIMIGOS DERROTADOS: {n}", n=self.abates)]
        if self.sobreviveu:
            self.terminar(True, self.pontos, titulo=tr("VOCÊ SOBREVIVEU!"), linhas=linhas)
        else:
            self.terminar(False, self.pontos, titulo=tr("O OVO FOI BATIDO!"), linhas=linhas)

    # --------------------------------------------------------
    # DESENHO
    # --------------------------------------------------------

    def desenhar_jogo(self, tela):
        cx, cy = int(self.cam_x), int(self.cam_y)
        tela.blit(_chao(), (0, 0), pygame.Rect(cx, cy, LARGURA, ALTURA))
        t = self.tempo
        vis = pygame.Rect(cx - 80, cy - 100, LARGURA + 160, ALTURA + 200)

        # Aura de sal (debaixo de tudo)
        if self.up["sal"] and not self.morto:
            r = self._raio_sal()
            a = _aura(r)
            tela.blit(a, a.get_rect(center=(round(self.x - cx), round(self.y - cy))))
            for k in range(12):
                ang = t * 1.5 + k * math.tau / 12
                rr = r * (0.45 + 0.5 * ((k * 37) % 10) / 10)
                pygame.draw.circle(tela, BRANCO, (round(self.x - cx + math.cos(ang) * rr),
                                                  round(self.y - cy + math.sin(ang) * rr)), 2)

        # Cristais e itens
        for c in self.cristais:
            if vis.collidepoint(c[0], c[1]):
                s = _sprite("cristal", c[2])
                dy = math.sin(t * 5 + c[0] * 0.05) * 2
                tela.blit(s, s.get_rect(center=(round(c[0] - cx), round(c[1] - cy + dy))))
        for it in self.itens:
            if vis.collidepoint(it[0], it[1]):
                s = _sprite(it[2])
                dy = math.sin(t * 4 + it[0]) * 4
                tela.blit(s, s.get_rect(center=(round(it[0] - cx), round(it[1] - cy + dy))))
                if int(t * 5) % 2 == 0:
                    ui.estrela(tela, (round(it[0] - cx + 14), round(it[1] - cy - 14 + dy)), 5, BRANCO)

        # Inimigos + ovo, do fundo para a frente (ordem por y)
        visiveis = [i for i in self.inimigos if vis.collidepoint(i.x, i.y)]
        visiveis.sort(key=lambda i: i.y)
        ovo_desenhado = False
        for ini in visiveis:
            if not ovo_desenhado and ini.y > self.y:
                self._desenhar_ovo(tela, cx, cy)
                ovo_desenhado = True
            self._desenhar_inimigo(tela, ini, cx, cy)
        if not ovo_desenhado:
            self._desenhar_ovo(tela, cx, cy)

        # Limões voando e em órbita
        for lm in self.limoes:
            s = _sprite("limao", int(lm.giro) % 16)
            tela.blit(s, s.get_rect(center=(round(lm.x - cx), round(lm.y - cy))))
        if self.up["orbita"] and not self.morto:
            n = self.up["orbita"]
            for k in range(n):
                a = self.ang_orbita + k * math.tau / n
                s = _sprite("limao", int(t * 20 + k * 4) % 16)
                tela.blit(s, s.get_rect(center=(round(self.x - cx + math.cos(a) * RAIO_ORBITA),
                                                round(self.y - cy + math.sin(a) * RAIO_ORBITA))))
        g = _sprite("gota")
        for gota in self.gotas:
            tela.blit(g, g.get_rect(center=(round(gota[0] - cx), round(gota[1] - cy))))

        self.particulas.desenhar(tela, (-cx, -cy))
        self.textos.desenhar(tela, (-cx, -cy))

        # Setinha apontando o chefe quando ele está fora da tela
        ch = self.chefe
        if ch is not None and not pygame.Rect(cx, cy, LARGURA, ALTURA).collidepoint(ch.x, ch.y):
            ang = math.atan2(ch.y - self.y, ch.x - self.x)
            px = LARGURA / 2 + math.cos(ang) * 300
            py = ALTURA / 2 + math.sin(ang) * 250
            pulso = 1 + 0.2 * math.sin(t * 10)
            pts = [(px + math.cos(ang) * 22 * pulso, py + math.sin(ang) * 22 * pulso),
                   (px + math.cos(ang + 2.5) * 16, py + math.sin(ang + 2.5) * 16),
                   (px + math.cos(ang - 2.5) * 16, py + math.sin(ang - 2.5) * 16)]
            pygame.draw.polygon(tela, (40, 10, 10), [(x + 2, y + 2) for x, y in pts])
            pygame.draw.polygon(tela, SUCO, pts)

        # Levou dano: bordinha vermelha
        if self.dor > 0:
            ui.veu(tela, int(120 * self.dor / 0.35), (200, 30, 40))

        # Letreiro grande
        if self.t_aviso > 0 and self.estado == "jogando" and self.escolha is None:
            tam = 30 if len(self.aviso) < 18 else 20
            cor = AMARELO if self.sobreviveu or "DERROTADO" in self.aviso else (255, 120, 100)
            if int(self.t_aviso * 6) % 2 == 0 or self.t_aviso < 1.0:
                ui.desenhar_texto(tela, tr(self.aviso), (LARGURA // 2, 200), tam, cor, "center")

    def _desenhar_inimigo(self, tela, ini, cx, cy):
        # Chamado para até 150 inimigos por quadro: sem get_rect/round
        t = self.tempo
        tremendo = ini.chefe and ini.estado == "carregar"
        quadro = int(t * 30) % 2 if tremendo else int(t * 6 + ini.fase) % 2
        s = _sprites.get((ini.tipo, quadro, ini.esq, ini.flash > 0))             or _sprite(ini.tipo, quadro, ini.esq, ini.flash > 0)
        w, h = s.get_size()
        pulo = abs(math.sin(t * 9 + ini.fase)) * (5 if ini.chefe else 3)
        x = int(ini.x - cx)
        y = int(ini.y - cy)
        if tremendo:
            x += random.randint(-3, 3)
        sombra = _sombra(int(ini.raio * 2.2))
        sw, sh = sombra.get_size()
        tela.blit(sombra, (x - sw // 2, y + int(h * 0.42) - sh // 2))
        tela.blit(s, (x - w // 2, int(y - pulo) - h // 2))
        if tremendo:
            # "!" em cima do chefe antes de investir
            ui.desenhar_texto(tela, "!", (x, y - h // 2 - 20), 24, (255, 80, 80), "center")

    def _desenhar_ovo(self, tela, cx, cy):
        x, y = self.x - cx, self.y - cy
        sombra = _sombra(44)
        tela.blit(sombra, sombra.get_rect(center=(round(x), round(y + ALTURA_OVO * 0.48))))
        if self.morto:
            ang = math.sin(self.tempo_morto * 14) * 25 * max(0.0, 1 - self.tempo_morto / 1.6)
            self.jogador.desenhar(tela, (x, y), ALTURA_OVO, espelhar=self.esq, angulo=ang)
            return
        if self.invencivel > 0 and int(self.invencivel * 14) % 2 == 0 and self.escolha is None:
            return
        # Andando: balança e dá pulinhos
        pulo = abs(math.sin(self.andando * 12)) * 5 if self.andando > 0 else 0
        ang = math.sin(self.andando * 12) * 6 if self.andando > 0 else 0
        if self.sobreviveu:
            pulo = abs(math.sin(self.tempo_vitoria * 7)) * 18
        self.jogador.desenhar(tela, (x, y - pulo), ALTURA_OVO, espelhar=self.esq, angulo=ang)

    # --------------------------------------------------------
    # HUD
    # --------------------------------------------------------

    def desenhar_hud(self, tela):
        # Corações
        n = self.vida_max
        caixa = pygame.Rect(12, 12, 24 + n * 30, 48)
        ui.painel(tela, caixa, (20, 24, 40), BRANCO, 12, 3, sombra=False)
        for i in range(n):
            c = (caixa.x + 27 + i * 30, caixa.centery + 1)
            cheio = i < self.vidas
            if cheio and self.vidas <= 1 and int(self.tempo * 6) % 2 == 0:
                c = (c[0], c[1] - 2)
            ui.coracao(tela, c, 24, (235, 60, 90) if cheio else (70, 70, 90))

        # Relógio (tempo que falta)
        falta = DURACAO - self.relogio
        caixa = pygame.Rect(0, 12, 150, 48)
        caixa.centerx = LARGURA // 2
        urgente = falta <= 10 and not self.sobreviveu
        ui.painel(tela, caixa, (20, 24, 40), (255, 110, 110) if urgente else BRANCO, 12, 3, sombra=False)
        tam = 22 if not (urgente and int(self.tempo * 4) % 2 == 0) else 24
        ui.desenhar_texto(tela, _formatar_tempo(falta), caixa.center, tam,
                          (255, 120, 120) if urgente else AMARELO, "center")

        # Vida do chefe
        ch = self.chefe
        if ch is not None and ch.vida > 0:
            barra = pygame.Rect(0, 70, 420, 16)
            barra.centerx = LARGURA // 2
            pygame.draw.rect(tela, (20, 24, 40), barra.inflate(8, 8), border_radius=8)
            pygame.draw.rect(tela, (70, 40, 50), barra, border_radius=6)
            cheio = barra.copy()
            cheio.w = max(2, int(barra.w * ch.vida / ch.vida_max))
            pygame.draw.rect(tela, SUCO, cheio, border_radius=6)
            pygame.draw.rect(tela, BRANCO, barra.inflate(8, 8), 2, border_radius=8)
            ui.desenhar_texto(tela, tr("LIQUIDIFICADOR"), (barra.centerx, barra.bottom + 8), 10,
                              (255, 170, 150), "midtop")

        # Abates e pontos (antes do botão de pausa)
        caixa = pygame.Rect(0, 12, 210, 48)
        caixa.right = LARGURA - 76
        ui.painel(tela, caixa, (20, 24, 40), BRANCO, 12, 3, sombra=False)
        ui.desenhar_texto(tela, f"× {self.abates}", (caixa.x + 14, caixa.y + 15), 12, BRANCO, "midleft")
        ui.desenhar_texto(tela, tr("{n} PTS", n=self.pontos), (caixa.x + 14, caixa.y + 34), 10, AMARELO, "midleft")
        rec = self.recorde()
        if rec is not None:
            ui.desenhar_texto(tela, tr("REC {n}", n=rec), (caixa.right - 12, caixa.y + 15), 8,
                              (180, 200, 255), "midright")

        # Barra de XP embaixo
        pilula = pygame.Rect(12, ALTURA - 40, 96, 30)
        ui.painel(tela, pilula, (20, 24, 40), (140, 230, 255), 10, 3, sombra=False)
        ui.desenhar_texto(tela, tr("NV {n}", n=self.nivel), pilula.center, 12, (170, 235, 255), "center")
        barra = pygame.Rect(pilula.right + 10, ALTURA - 32, LARGURA - pilula.right - 32, 14)
        pygame.draw.rect(tela, (20, 24, 40), barra.inflate(6, 6), border_radius=8)
        pygame.draw.rect(tela, (50, 60, 90), barra, border_radius=6)
        enche = max(0.0, min(1.0, self.xp_barra))
        if enche > 0:
            r = barra.copy()
            r.w = max(4, int(barra.w * enche))
            pygame.draw.rect(tela, (90, 190, 255), r, border_radius=6)
            pygame.draw.rect(tela, (190, 240, 255), (r.x + 3, r.y + 2, r.w - 6, 3), border_radius=2)

        if self.escolha is not None and self.estado == "jogando":
            self._desenhar_cartas(tela)

    def _rects_cartas(self):
        n = len(self.escolha["opcoes"]) if self.escolha else 3
        w, h, gap = 250, 310, 28
        total = n * w + (n - 1) * gap
        x0 = LARGURA // 2 - total // 2
        return [pygame.Rect(x0 + i * (w + gap), 230, w, h) for i in range(n)]

    def _desenhar_cartas(self, tela):
        esc = self.escolha
        ui.veu(tela, 170)
        ui.desenhar_texto(tela, tr("SUBIU DE NÍVEL!"), (LARGURA // 2, 130), 30, AMARELO, "center")
        ui.desenhar_texto(tela, tr("ESCOLHA UMA MELHORIA"), (LARGURA // 2, 180), 14, (180, 220, 255), "center")

        for i, (chave, r) in enumerate(zip(esc["opcoes"], self._rects_cartas())):
            nome, desc, maximo, cor = MELHORIAS[chave]
            nome, desc = tr(nome), tr(desc)
            # Entrada: as cartas sobem uma depois da outra
            k = max(0.0, min(1.0, (esc["t"] - i * 0.07) / 0.25))
            sel = i == esc["indice"]
            r = r.move(0, int((1 - k) ** 2 * 300) - (14 if sel else 0))
            if sel:
                r = r.move(0, int(math.sin(self.tempo * 5) * 3))
            ui.painel(tela, r, (44, 50, 84) if sel else (30, 34, 58), AMARELO if sel else cor,
                      18, 5 if sel else 3)

            # Número da tecla
            num = pygame.Rect(r.x + 12, r.y + 12, 34, 34)
            pygame.draw.rect(tela, AMARELO if sel else (70, 80, 120), num, border_radius=10)
            ui.desenhar_texto(tela, str(i + 1), num.center, 14, (30, 30, 40) if sel else BRANCO, "center")

            # Ícone num círculo
            centro = (r.centerx, r.y + 88)
            pygame.draw.circle(tela, ui.escurecer(cor, 120), centro, 48)
            pygame.draw.circle(tela, cor, centro, 48, 4)
            ic = _icone(chave)
            tela.blit(ic, ic.get_rect(center=centro))

            tam = ui.tamanho_que_cabe(nome, r.w - 24, (14, 12, 10))
            ui.desenhar_texto(tela, nome, (r.centerx, r.y + 150), tam, cor, "midtop")
            y = r.y + 184
            for linha in ui.quebrar_linhas(desc, 10, r.w - 34):
                ui.desenhar_texto(tela, linha, (r.centerx, y), 10, BRANCO, "midtop")
                y += 18

            # Nível atual da melhoria (bolinhas)
            if chave == "lanche":
                texto = "CURA!"
            elif self.up[chave] == 0:
                texto = "NOVO!"
            else:
                texto = tr("NÍVEL {n}", n=self.up[chave] + 1)
            ui.desenhar_texto(tela, tr(texto), (r.centerx, r.bottom - 50), 10,
                              AMARELO if texto == "NOVO!" else (180, 220, 255), "midtop")
            if chave != "lanche":
                larg = maximo * 18
                for p in range(maximo):
                    c = (r.centerx - larg // 2 + 9 + p * 18, r.bottom - 22)
                    if p < self.up[chave]:
                        pygame.draw.circle(tela, cor, c, 6)
                    elif p == self.up[chave]:
                        pygame.draw.circle(tela, AMARELO if int(self.tempo * 4) % 2 == 0 else cor, c, 6)
                    else:
                        pygame.draw.circle(tela, (90, 90, 120), c, 6, 2)

        ui.desenhar_texto(tela, tr("1 2 3 • ← → + ENTER • MOUSE"), (LARGURA // 2, 580), 10,
                          (200, 200, 220), "midtop")
