import math
import random

import pygame

from settings import *
from core import ui
from core.idioma import t
from core import assets
from core.jogador import Jogador
from jogos.base import MiniJogo

# ============================================================
# EVOLUÇÃO 2048
# ============================================================
# O clássico 2048 dentro de um ninho: deslize os ovos e junte
# dois iguais para eles EVOLUÍREM. Do ovinho de codorna ao
# pintinho, ao ovo de ouro... até virar o SEU OVO de coroa!
# Cada movimento funde cada peça no máximo uma vez.

# Tabuleiros: lado, tamanho do bloco, vão entre blocos
TABULEIROS = [
    (4, 130, 14),       # 4x4
    (5, 104, 12),       # 5x5 FÁCIL
    (3, 170, 14),       # 3x3 DESAFIO
]

AREA_TOPO = 76          # área livre abaixo do HUD
AREA_BASE = 712
LARG_PAINEL = 176       # painéis laterais (desfazer / evolução)

DUR_DESLIZAR = 0.10
DUR_POP = 0.12
DUR_SURGIR = 0.12
ESPERA_EVOLUIU = 0.55   # tempo antes do painel "VOCÊ EVOLUIU!"
ESPERA_TRAVADO = 1.3    # sem jogadas e sem desfazer: espera antes do fim

DESFAZER_MAX = 3
HISTORICO_MAX = 12
ARRASTO_MIN = 40        # pixels para o arrasto do mouse contar
CHANCE_QUATRO = 0.10
BONUS_2048 = 6          # moedas extras ao fazer o primeiro 2048

CIMA, BAIXO, ESQ, DIR = (0, -1), (0, 1), (-1, 0), (1, 0)

TECLAS = {
    pygame.K_UP: CIMA, pygame.K_w: CIMA,
    pygame.K_DOWN: BAIXO, pygame.K_s: BAIXO,
    pygame.K_LEFT: ESQ, pygame.K_a: ESQ,
    pygame.K_RIGHT: DIR, pygame.K_d: DIR,
}
TECLAS_DESFAZER = (pygame.K_z, pygame.K_BACKSPACE)

# Estágios da evolução: valor -> (nome, cor do bloco)
ESTAGIOS = {
    2: ("OVO DE CODORNA", (238, 228, 218)),
    4: ("OVO BRANCO", (237, 224, 200)),
    8: ("OVO CAIPIRA", (242, 177, 121)),
    16: ("OVO COM LAÇO", (245, 149, 99)),
    32: ("OVO RACHADO", (246, 124, 95)),
    64: ("PINTINHO", (246, 94, 59)),
    128: ("OVO DE PÁSCOA", (237, 207, 114)),
    256: ("OVO DE OURO", (237, 204, 97)),
    512: ("QUASE VOCÊ", (180, 140, 230)),
    1024: ("SEU OVO", (120, 120, 240)),
    2048: ("REI OVO", (255, 214, 64)),
    4096: ("OVO LENDÁRIO", (40, 40, 60)),
}
ESCADA = [2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096]

# Cenário (ninho)
COR_NINHO = (255, 236, 200)
PALHAS = [(230, 200, 140), (215, 180, 115)]
COR_TABULEIRO = (190, 150, 100)
COR_TRANCA = (160, 120, 70)
COR_VAZIA = (205, 170, 125)
COR_PAINEL = (112, 78, 50)
COR_PAINEL_BORDA = (245, 220, 170)


def _estagio(valor):
    """Nome e cor do bloco (4096 em diante usam o estágio lendário)."""
    return ESTAGIOS.get(valor, ESTAGIOS[4096])


# ============================================================
# LÓGICA PURA DO 2048 (sem pygame, fácil de testar)
# ============================================================

def mover_grade(grade, direcao):
    """
    Desliza a grade (lista de listas [linha][coluna], 0 = vazio).
    Cada peça funde NO MÁXIMO uma vez por movimento (2-2-4 -> 4-4).
    Devolve (nova, ganho, movimentos, fusoes, mudou):
      movimentos -> (l0, c0, l1, c1, valor) de TODAS as peças
      fusoes     -> (l, c, valor_novo)
    """
    n = len(grade)
    dc, dl = direcao
    nova = [[0] * n for _ in range(n)]
    movimentos = []
    fusoes = []
    ganho = 0

    for k in range(n):
        # Células da linha/coluna, começando pela parede do destino
        if dc:
            cels = [(k, c) for c in range(n)]
            if dc > 0:
                cels.reverse()
        else:
            cels = [(l, k) for l in range(n)]
            if dl > 0:
                cels.reverse()

        livre = 0               # próxima posição livre na linha
        pode_fundir = False     # a última peça colocada ainda pode fundir?
        for (l, c) in cels:
            v = grade[l][c]
            if not v:
                continue
            if pode_fundir:
                tl, tc = cels[livre - 1]
                if nova[tl][tc] == v:
                    nova[tl][tc] = v * 2
                    ganho += v * 2
                    fusoes.append((tl, tc, v * 2))
                    movimentos.append((l, c, tl, tc, v))
                    pode_fundir = False
                    continue
            tl, tc = cels[livre]
            livre += 1
            nova[tl][tc] = v
            pode_fundir = True
            movimentos.append((l, c, tl, tc, v))

    return nova, ganho, movimentos, fusoes, nova != grade


def tem_movimento(grade):
    """Existe alguma jogada? (casa vazia ou dois vizinhos iguais)"""
    n = len(grade)
    for l in range(n):
        for c in range(n):
            v = grade[l][c]
            if v == 0:
                return True
            if c + 1 < n and grade[l][c + 1] == v:
                return True
            if l + 1 < n and grade[l + 1][c] == v:
                return True
    return False


def _geometria(opcao):
    n, bloco, vao = TABULEIROS[opcao]
    tam = n * bloco + (n + 1) * vao
    x0 = (LARGURA - tam) // 2
    y0 = AREA_TOPO + (AREA_BASE - AREA_TOPO - tam) // 2
    return n, bloco, vao, tam, x0, y0


# ============================================================
# DESENHO DOS ESTÁGIOS (feito uma vez para cada tamanho)
# ============================================================

Z = 2                   # desenha 2x maior e reduz (fica suave)


def _pontos_ovo(cx, cy, rx, ry, n=56):
    """Contorno de ovo: mais estreito em cima, mais largo embaixo."""
    pts = []
    for i in range(n):
        a = math.tau * i / n
        s = math.sin(a)
        pts.append((cx + rx * math.cos(a) * (1 + 0.1 * s), cy + ry * s))
    return pts


def _ovo(sup, cx, cy, rx, ry, cor, contorno, esp):
    pygame.draw.polygon(sup, contorno, _pontos_ovo(cx, cy, rx + esp, ry + esp))
    pygame.draw.polygon(sup, cor, _pontos_ovo(cx, cy, rx, ry))


def _mascara_ovo(L, cx, cy, rx, ry):
    m = pygame.Surface((L, L), pygame.SRCALPHA)
    pygame.draw.polygon(m, (255, 255, 255, 255), _pontos_ovo(cx, cy, rx, ry))
    return m


def _recortar(camada, mascara):
    """Deixa só o que está dentro da máscara."""
    camada.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    return camada


def _brilho(sup, cx, cy, rx, ry, alpha=150):
    b = pygame.Surface((max(2, int(rx * 0.62)), max(2, int(ry * 0.46))), pygame.SRCALPHA)
    pygame.draw.ellipse(b, (255, 255, 255, alpha), b.get_rect())
    sup.blit(b, (cx - rx * 0.6, cy - ry * 0.66))


def _sombra_ovo(sup, cx, cy, rx, ry, fundo):
    pygame.draw.ellipse(sup, ui.escurecer(fundo, 34),
                        (cx - rx * 0.85, cy + ry * 0.78, rx * 1.7, ry * 0.36))


def _brilhinho(sup, pos, r, cor=(255, 255, 255)):
    """Estrelinha de 4 pontas."""
    x, y = pos
    pts = [(x, y - r), (x + r * 0.25, y - r * 0.25), (x + r, y), (x + r * 0.25, y + r * 0.25),
           (x, y + r), (x - r * 0.25, y + r * 0.25), (x - r, y), (x - r * 0.25, y - r * 0.25)]
    pygame.draw.polygon(sup, cor, pts)


def _coroa(sup, cx, base, w, h):
    """Coroa dourada com pedrinhas."""
    esq = cx - w / 2
    pts = [(esq, base), (esq, base - h), (esq + w * 0.25, base - h * 0.48), (cx, base - h * 1.05),
           (esq + w * 0.75, base - h * 0.48), (esq + w, base - h), (esq + w, base)]
    esp = max(2, int(w * 0.06))
    pygame.draw.polygon(sup, (255, 186, 24), pts)
    pygame.draw.polygon(sup, (130, 76, 0), pts, esp)
    pygame.draw.rect(sup, (130, 76, 0), (esq, base - h * 0.3, w, h * 0.3))
    pygame.draw.rect(sup, (255, 214, 70), (esq + esp, base - h * 0.3 + esp, w - 2 * esp, h * 0.3 - 2 * esp))
    for x, y in ((esq, base - h), (cx, base - h * 1.05), (esq + w, base - h)):
        pygame.draw.circle(sup, (130, 76, 0), (int(x), int(y)), max(3, int(w * 0.09)))
        pygame.draw.circle(sup, (255, 240, 150), (int(x), int(y)), max(2, int(w * 0.06)))
    for i, cor in enumerate(((230, 40, 70), (60, 160, 240), (230, 40, 70))):
        x = esq + w * (0.22 + 0.28 * i)
        pygame.draw.circle(sup, cor, (int(x), int(base - h * 0.15)), max(2, int(w * 0.07)))


def _retrato(jogador, completo, cabelo):
    """Avatar do jogador (100x100) com só algumas partes."""
    if completo:
        return jogador.avatar()
    ovo, cab, olho, _ = jogador.aparencia()
    sup = pygame.Surface((100, 100), pygame.SRCALPHA)
    sup.blit(assets.OVOS[ovo], (0, 0))
    if cabelo:
        sup.blit(assets.CABELOS[cab], (0, 0))
    sup.blit(assets.OLHOS[olho], (0, 0))
    return sup


def _colar_retrato(sup, img, cx, cy, altura):
    """Cola o retrato com o CENTRO DO OVO em (cx, cy)."""
    corpo = Jogador.OVO_RECT
    escala = altura / corpo.h
    lado = max(1, int(100 * escala))
    img = pygame.transform.smoothscale(img, (lado, lado))
    dx = (corpo.centerx - 50) * escala
    dy = (corpo.centery - 50) * escala
    sup.blit(img, img.get_rect(center=(int(cx - dx), int(cy - dy))))


def _desenhar_estagio(sup, valor, L, jogador):
    """Desenha a peça do estágio `valor` numa superfície L x L."""
    _, fundo = _estagio(valor)
    cx, cy = L / 2, L * 0.53
    ry = L * 0.31
    rx = ry * 0.8
    esp = max(2, L // 45)

    if valor == 2:
        # Ovo de codorna: pequeno e pintadinho
        ry, rx = L * 0.25, L * 0.25 * 0.8
        cy = L * 0.55
        _sombra_ovo(sup, cx, cy, rx, ry, fundo)
        _ovo(sup, cx, cy, rx, ry, (240, 225, 190), (160, 128, 90), esp)
        camada = pygame.Surface((L, L), pygame.SRCALPHA)
        rnd = random.Random(2)
        for _ in range(16):
            a = rnd.uniform(0, math.tau)
            d = rnd.uniform(0, 0.95)
            x = cx + math.cos(a) * rx * d
            y = cy + math.sin(a) * ry * d
            cor = rnd.choice([(110, 74, 44), (140, 96, 58), (90, 60, 40)])
            r = rnd.uniform(L * 0.018, L * 0.045)
            pygame.draw.ellipse(camada, cor, (x - r, y - r * 0.8, r * 2, r * 1.6))
        sup.blit(_recortar(camada, _mascara_ovo(L, cx, cy, rx, ry)), (0, 0))
        _brilho(sup, cx, cy, rx, ry)

    elif valor == 4:
        _sombra_ovo(sup, cx, cy, rx, ry, fundo)
        _ovo(sup, cx, cy, rx, ry, (253, 253, 248), (180, 170, 155), esp)
        pygame.draw.polygon(sup, (236, 234, 226), _pontos_ovo(cx + rx * 0.12, cy + ry * 0.12, rx * 0.8, ry * 0.8))
        pygame.draw.polygon(sup, (253, 253, 248), _pontos_ovo(cx - rx * 0.06, cy - ry * 0.06, rx * 0.84, ry * 0.84))
        _brilho(sup, cx, cy, rx, ry, 255)

    elif valor == 8:
        _sombra_ovo(sup, cx, cy, rx, ry, fundo)
        _ovo(sup, cx, cy, rx, ry, (190, 130, 80), (120, 76, 42), esp)
        rnd = random.Random(8)
        for _ in range(9):
            a = rnd.uniform(0, math.tau)
            d = rnd.uniform(0.1, 0.8)
            pygame.draw.circle(sup, (208, 152, 100), (int(cx + math.cos(a) * rx * d),
                                                      int(cy + math.sin(a) * ry * d)), max(2, L // 70))
        _brilho(sup, cx, cy, rx, ry)

    elif valor == 16:
        # Ovo com laço rosa
        _sombra_ovo(sup, cx, cy, rx, ry, fundo)
        _ovo(sup, cx, cy, rx, ry, (252, 240, 222), (190, 160, 130), esp)
        by = cy - ry * 0.05
        camada = pygame.Surface((L, L), pygame.SRCALPHA)
        pygame.draw.rect(camada, (200, 60, 120), (0, by - ry * 0.14, L, ry * 0.28))
        pygame.draw.rect(camada, (255, 120, 170), (0, by - ry * 0.11, L, ry * 0.22))
        sup.blit(_recortar(camada, _mascara_ovo(L, cx, cy, rx, ry)), (0, 0))
        _brilho(sup, cx, cy, rx, ry)
        for lado in (-1, 1):
            laco = [(cx, by), (cx + lado * rx * 0.75, by - ry * 0.34), (cx + lado * rx * 0.75, by + ry * 0.3)]
            pygame.draw.polygon(sup, (255, 120, 170), laco)
            pygame.draw.polygon(sup, (200, 60, 120), laco, esp)
            fita = [(cx, by), (cx + lado * rx * 0.34, by + ry * 0.55), (cx + lado * rx * 0.14, by + ry * 0.6)]
            pygame.draw.polygon(sup, (255, 120, 170), fita)
            pygame.draw.polygon(sup, (200, 60, 120), fita, max(1, esp - 1))
        pygame.draw.circle(sup, (200, 60, 120), (int(cx), int(by)), int(ry * 0.15))
        pygame.draw.circle(sup, (255, 160, 200), (int(cx), int(by)), int(ry * 0.1))

    elif valor == 32:
        # Ovo rachado com um olhinho espiando pelo buraco
        _sombra_ovo(sup, cx, cy, rx, ry, fundo)
        _ovo(sup, cx, cy, rx, ry, (246, 242, 232), (185, 170, 150), esp)
        _brilho(sup, cx, cy, rx, ry)
        hx, hy = cx + rx * 0.08, cy - ry * 0.22
        buraco = []
        for i in range(14):
            a = math.tau * i / 14
            r = ry * (0.36 if i % 2 else 0.24)
            buraco.append((hx + math.cos(a) * r * 1.1, hy + math.sin(a) * r * 0.9))
        pygame.draw.polygon(sup, (40, 26, 30), buraco)
        pygame.draw.polygon(sup, (120, 100, 90), buraco, max(1, esp - 1))
        # Rachaduras saindo do buraco
        for lado in (-1, 1):
            pts = [(hx + lado * ry * 0.34, hy), (hx + lado * ry * 0.5, hy + ry * 0.14),
                   (hx + lado * ry * 0.62, hy - ry * 0.02), (hx + lado * ry * 0.72, hy + ry * 0.16)]
            pygame.draw.lines(sup, (120, 100, 90), False, pts, esp)
        # Olhinho
        pygame.draw.circle(sup, (255, 255, 255), (int(hx), int(hy + ry * 0.02)), int(ry * 0.15))
        pygame.draw.circle(sup, (20, 20, 20), (int(hx + ry * 0.04), int(hy + ry * 0.05)), int(ry * 0.085))
        pygame.draw.circle(sup, (255, 255, 255), (int(hx + ry * 0.07), int(hy + ry * 0.01)), max(1, int(ry * 0.03)))

    elif valor == 64:
        # Pintinho saindo da casca
        casca_y = cy + ry * 0.1
        _sombra_ovo(sup, cx, cy, rx, ry, fundo)
        # Corpo/cabeça do pintinho
        pc = (int(cx), int(cy - ry * 0.18))
        pr = int(rx * 0.86)
        pygame.draw.circle(sup, (205, 150, 20), pc, pr + esp)
        pygame.draw.circle(sup, (255, 216, 56), pc, pr)
        pygame.draw.circle(sup, (255, 236, 140), (int(pc[0] - pr * 0.35), int(pc[1] - pr * 0.4)), int(pr * 0.25))
        for lado in (-1, 1):
            pygame.draw.ellipse(sup, (240, 190, 40), (pc[0] + lado * pr * 0.9 - pr * 0.3, pc[1] + pr * 0.1,
                                                      pr * 0.6, pr * 0.8))
        # Topetinho
        for dx in (-0.12, 0.0, 0.12):
            pygame.draw.line(sup, (205, 150, 20), (pc[0] + pr * dx, pc[1] - pr * 0.95),
                             (pc[0] + pr * dx * 2.5, pc[1] - pr * 1.25), esp)
        # Olhos, bico e bochechas
        for lado in (-1, 1):
            pygame.draw.circle(sup, (30, 20, 20), (int(pc[0] + lado * pr * 0.38), int(pc[1] - pr * 0.12)),
                               max(2, int(pr * 0.13)))
            pygame.draw.circle(sup, (255, 255, 255), (int(pc[0] + lado * pr * 0.38 + pr * 0.04),
                                                      int(pc[1] - pr * 0.17)), max(1, int(pr * 0.05)))
            pygame.draw.circle(sup, (255, 150, 140), (int(pc[0] + lado * pr * 0.6), int(pc[1] + pr * 0.18)),
                               max(2, int(pr * 0.12)))
        bico = [(pc[0] - pr * 0.18, pc[1] + pr * 0.05), (pc[0] + pr * 0.18, pc[1] + pr * 0.05),
                (pc[0], pc[1] + pr * 0.34)]
        pygame.draw.polygon(sup, (255, 140, 30), bico)
        pygame.draw.polygon(sup, (200, 90, 10), bico, max(1, esp - 1))
        # Metade de baixo da casca com borda em zigue-zague
        camada = pygame.Surface((L, L), pygame.SRCALPHA)
        _ovo(camada, cx, cy, rx, ry, (250, 248, 240), (180, 170, 150), esp)
        dentes = 7
        zig = []
        for i in range(dentes * 2 + 1):
            x = cx - rx * 1.3 + (rx * 2.6) * i / (dentes * 2)
            zig.append((x, casca_y - (ry * 0.16 if i % 2 else 0)))
        apagar = [(0, 0), (L, 0), (L, zig[-1][1])] + zig[::-1] + [(0, zig[0][1])]
        pygame.draw.polygon(camada, (0, 0, 0, 0), apagar)
        pygame.draw.lines(camada, (180, 170, 150), False,
                          [p for p in zig if abs(p[0] - cx) < rx * 1.05], esp)
        sup.blit(camada, (0, 0))
        # Pedaço de casca no topo da cabeça
        tampa_y = pc[1] - pr * 0.72
        tampa = [(pc[0] - pr * 0.55, tampa_y), (pc[0] - pr * 0.35, tampa_y - pr * 0.45),
                 (pc[0], tampa_y - pr * 0.6), (pc[0] + pr * 0.35, tampa_y - pr * 0.45),
                 (pc[0] + pr * 0.55, tampa_y), (pc[0] + pr * 0.3, tampa_y - pr * 0.15),
                 (pc[0] + pr * 0.1, tampa_y + pr * 0.05), (pc[0] - pr * 0.15, tampa_y - pr * 0.15),
                 (pc[0] - pr * 0.35, tampa_y + pr * 0.05)]
        pygame.draw.polygon(sup, (250, 248, 240), tampa)
        pygame.draw.polygon(sup, (180, 170, 150), tampa, max(1, esp - 1))

    elif valor == 128:
        # Ovo de páscoa listrado
        _sombra_ovo(sup, cx, cy, rx, ry, fundo)
        _ovo(sup, cx, cy, rx, ry, (140, 200, 250), (60, 100, 170), esp)
        camada = pygame.Surface((L, L), pygame.SRCALPHA)
        faixas = [(-0.55, (255, 130, 180)), (-0.1, (255, 225, 90)), (0.35, (130, 225, 170)),
                  (0.78, (190, 150, 240))]
        for pos, cor in faixas:
            y = cy + ry * pos
            h = ry * 0.2
            n = 8
            topo = [(cx - rx * 1.3 + rx * 2.6 * i / n, y - (h * 0.5 if i % 2 else 0)) for i in range(n + 1)]
            base = [(x, yy + h) for x, yy in topo]
            pygame.draw.polygon(camada, cor, topo + base[::-1])
        for pos in (-0.32, 0.13, 0.57):
            for i in range(-2, 3):
                pygame.draw.circle(camada, (255, 255, 255), (int(cx + i * rx * 0.42), int(cy + ry * pos)),
                                   max(2, int(L * 0.014)))
        sup.blit(_recortar(camada, _mascara_ovo(L, cx, cy, rx, ry)), (0, 0))
        _brilho(sup, cx, cy, rx, ry)

    elif valor == 256:
        # Ovo de ouro brilhante
        halo = pygame.Surface((L, L), pygame.SRCALPHA)
        for i in range(6, 0, -1):
            pygame.draw.circle(halo, (255, 250, 200, 22), (int(cx), int(cy)), int(ry * (0.9 + i * 0.1)))
        sup.blit(halo, (0, 0))
        _sombra_ovo(sup, cx, cy, rx, ry, fundo)
        _ovo(sup, cx, cy, rx, ry, (240, 170, 20), (150, 96, 0), esp)
        pygame.draw.polygon(sup, (255, 206, 50), _pontos_ovo(cx - rx * 0.08, cy - ry * 0.08, rx * 0.84, ry * 0.84))
        pygame.draw.polygon(sup, (255, 228, 120), _pontos_ovo(cx - rx * 0.2, cy - ry * 0.22, rx * 0.5, ry * 0.5))
        _brilho(sup, cx, cy, rx, ry, 200)
        for px, py, r in ((0.78, 0.2, 0.07), (0.2, 0.3, 0.05), (0.8, 0.72, 0.045)):
            _brilhinho(sup, (L * px, L * py), L * r)

    else:
        # Do 512 em diante: o próprio ovo do jogador ganhando partes
        altura = L * 0.54
        cy = L * 0.56
        if valor == 2048:
            # Raios de luz atrás
            raios = pygame.Surface((L, L), pygame.SRCALPHA)
            for i in range(12):
                a = math.tau * i / 12 + 0.13
                pts = [(cx, cy), (cx + math.cos(a - 0.14) * L, cy + math.sin(a - 0.14) * L),
                       (cx + math.cos(a + 0.14) * L, cy + math.sin(a + 0.14) * L)]
                pygame.draw.polygon(raios, (255, 244, 170, 160), pts)
            sup.blit(raios, (0, 0))
        elif valor >= 4096:
            # Aura arco-íris
            cores = [(255, 70, 70), (255, 160, 40), (255, 230, 60), (90, 220, 90),
                     (60, 170, 255), (150, 90, 240)]
            r0 = L * 0.47
            for i, cor in enumerate(cores):
                pygame.draw.circle(sup, cor, (int(cx), int(cy - L * 0.03)), int(r0 - i * L * 0.022))
            pygame.draw.circle(sup, fundo, (int(cx), int(cy - L * 0.03)), int(r0 - len(cores) * L * 0.022))
            for px, py in ((0.14, 0.18), (0.86, 0.22), (0.12, 0.8), (0.88, 0.84)):
                _brilhinho(sup, (L * px, L * py), L * 0.045, (255, 250, 200))
        else:
            halo = pygame.Surface((L, L), pygame.SRCALPHA)
            pygame.draw.circle(halo, (255, 255, 255, 60), (int(cx), int(cy)), int(altura * 0.66))
            sup.blit(halo, (0, 0))

        pygame.draw.ellipse(sup, ui.escurecer(fundo, 34) if valor < 4096 else (25, 25, 38),
                            (cx - altura * 0.36, cy + altura * 0.42, altura * 0.72, altura * 0.14))
        img = _retrato(jogador, valor >= 2048, valor >= 1024)
        _colar_retrato(sup, img, cx, cy, altura)
        if valor >= 2048:
            _coroa(sup, cx, cy - altura * 0.44, altura * 0.62, altura * 0.3)


def _criar_sprite(valor, T, jogador, numero=True):
    """Bloco completo (fundo + desenho + número) de tamanho T x T."""
    L = T * Z
    sup = pygame.Surface((L, L), pygame.SRCALPHA)
    _, fundo = _estagio(valor)
    raio = int(L * 0.12)
    base = int(L * 0.05)

    # Bloco com relevo: faixa mais escura embaixo
    pygame.draw.rect(sup, ui.escurecer(fundo, 45), (0, 0, L, L), border_radius=raio)
    pygame.draw.rect(sup, fundo, (0, 0, L, L - base), border_radius=raio)
    pygame.draw.rect(sup, ui.clarear(fundo, 22), (raio // 2, int(L * 0.03), L - raio, int(L * 0.03)),
                     border_radius=raio)
    _desenhar_estagio(sup, valor, L, jogador)

    # Recorta tudo no formato do bloco (raios e auras não saem dos cantos)
    mascara = pygame.Surface((L, L), pygame.SRCALPHA)
    pygame.draw.rect(mascara, (255, 255, 255, 255), (0, 0, L, L), border_radius=raio)
    sup.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    sup = pygame.transform.smoothscale(sup, (T, T))
    if not numero:
        return sup

    # Número pequeno no canto inferior direito (numa pílula escura)
    tam = 12 if T >= 120 else 10
    txt = ui.texto(str(valor), tam, BRANCO, False)
    pilula = txt.get_rect()
    pilula.inflate_ip(10, 8)
    pilula.bottomright = (T - max(4, T // 22), T - base // Z - max(3, T // 26))
    fundo_num = pygame.Surface(pilula.size, pygame.SRCALPHA)
    pygame.draw.rect(fundo_num, (40, 24, 16, 150), fundo_num.get_rect(), border_radius=pilula.h // 2)
    sup.blit(fundo_num, pilula)
    sup.blit(txt, txt.get_rect(center=(pilula.centerx + 1, pilula.centery + 1)))
    return sup


class Ovo2048(MiniJogo):

    ID = "ovo_2048"
    TITULO = "EVOLUÇÃO 2048"
    TITULO_CURTO = "2048"
    DESCRICAO = "Junte ovos iguais para evoluir: do ovinho de codorna até o SEU OVO de coroa!"
    COR = (220, 150, 70)
    INSTRUCOES = [
        "Deslize os ovos: dois iguais se juntam e EVOLUEM!",
        "Codorna, pintinho, ovo de ouro... até VOCÊ!",
        "Chegue ao 2048 para virar o REI OVO.",
        "Errou? Você pode DESFAZER 3 vezes.",
        "SETAS/WASD ou arraste o mouse • Z desfaz",
    ]
    OPCOES = ["4x4", "5x5 FÁCIL", "3x3 DESAFIO"]
    CONTAGEM = False

    MOEDAS_POR = 800
    MOEDAS_MAX = 24

    _sprites = {}
    _fundos_tab = {}

    # --------------------------------------------------------
    # SPRITES
    # --------------------------------------------------------

    @classmethod
    def sprite(cls, valor, T, jogador, numero=True):
        chave = (valor, T, numero, jogador.aparencia(), jogador.chave_visual())
        s = cls._sprites.get(chave)
        if s is None:
            if len(cls._sprites) > 160:
                cls._sprites.clear()
            s = _criar_sprite(valor, T, jogador, numero)
            cls._sprites[chave] = s
        return s

    # --------------------------------------------------------
    # CENÁRIO: ninho aconchegante
    # --------------------------------------------------------

    @classmethod
    def criar_fundo(cls, jogador):
        sup = pygame.Surface((LARGURA, ALTURA))
        sup.fill(COR_NINHO)
        rnd = random.Random(48)

        # Manchas suaves de luz
        luz = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        for _ in range(10):
            x, y = rnd.randrange(LARGURA), rnd.randrange(ALTURA)
            pygame.draw.circle(luz, (255, 246, 222, 70), (x, y), rnd.randint(60, 140))
        sup.blit(luz, (0, 0))

        # Palhinhas espalhadas
        for _ in range(420):
            x, y = rnd.randrange(LARGURA), rnd.randrange(ALTURA)
            ang = rnd.uniform(0, math.pi)
            comp = rnd.randint(8, 16)
            cor = rnd.choice(PALHAS)
            pygame.draw.line(sup, cor, (x, y), (x + math.cos(ang) * comp, y + math.sin(ang) * comp), 2)

        # Algumas peninhas
        for _ in range(8):
            x, y = rnd.randrange(40, LARGURA - 40), rnd.randrange(80, ALTURA - 40)
            ang = rnd.uniform(-0.8, 0.8)
            dx, dy = math.sin(ang) * 16, -math.cos(ang) * 16
            pena = [(x - dx, y - dy), (x + dy * 0.35, y - dx * 0.35), (x + dx, y + dy),
                    (x - dy * 0.35, y + dx * 0.35)]
            pygame.draw.polygon(sup, (255, 250, 240), pena)
            pygame.draw.line(sup, (225, 205, 170), (x - dx, y - dy), (x + dx * 1.3, y + dy * 1.3), 1)
        return sup

    @classmethod
    def _fundo_tabuleiro(cls, jogador, opcao):
        """Cenário + tabuleiro trançado + molduras dos painéis (cacheado)."""
        chave = (opcao, jogador.aparencia(), jogador.chave_visual())
        sup = cls._fundos_tab.get(chave)
        if sup is not None:
            return sup

        sup = cls.fundo(jogador).copy()
        n, bloco, vao, tam, x0, y0 = _geometria(opcao)
        tab = pygame.Rect(x0, y0, tam, tam)
        borda = tab.inflate(28, 28)

        # Sombra e borda de palha trançada
        sombra = pygame.Surface(borda.inflate(20, 20).size, pygame.SRCALPHA)
        pygame.draw.rect(sombra, (90, 60, 30, 80), sombra.get_rect(), border_radius=30)
        sup.blit(sombra, (borda.x - 4, borda.y + 2))
        pygame.draw.rect(sup, COR_TRANCA, borda, border_radius=26)
        _trancado(sup, borda)
        pygame.draw.rect(sup, COR_TABULEIRO, tab, border_radius=18)
        pygame.draw.rect(sup, ui.escurecer(COR_TABULEIRO, 30), tab, 3, border_radius=18)

        # Casas vazias
        for l in range(n):
            for c in range(n):
                r = pygame.Rect(x0 + vao + c * (bloco + vao), y0 + vao + l * (bloco + vao), bloco, bloco)
                pygame.draw.rect(sup, COR_VAZIA, r, border_radius=int(bloco * 0.12))
                pygame.draw.rect(sup, ui.escurecer(COR_VAZIA, 22), (r.x, r.y, r.w, 5),
                                 border_radius=int(bloco * 0.12))

        # Molduras dos painéis laterais
        for r in cls._paineis(opcao):
            ui.painel(sup, r, COR_PAINEL, COR_PAINEL_BORDA, 16, 3)

        sup = sup.convert()
        if len(cls._fundos_tab) > 12:
            cls._fundos_tab.clear()
        cls._fundos_tab[chave] = sup
        return sup

    @staticmethod
    def _paineis(opcao):
        """Retângulos: desfazer, jogadas, maior ovo, evolução."""
        n, bloco, vao, tam, x0, y0 = _geometria(opcao)
        esq = x0 // 2
        dir_ = x0 + tam + (LARGURA - x0 - tam) // 2
        w = LARG_PAINEL
        desfazer = pygame.Rect(esq - w // 2, y0, w, 120)
        jogadas = pygame.Rect(esq - w // 2, desfazer.bottom + 16, w, 64)
        maior = pygame.Rect(esq - w // 2, jogadas.bottom + 16, w, 196)
        evolucao = pygame.Rect(dir_ - w // 2, y0, w, 44 + 6 * 72 + 6)
        return desfazer, jogadas, maior, evolucao

    @classmethod
    def desenhar_icone(cls, sup, jogador):
        w, h = sup.get_size()
        T = int(h * 0.4)
        vao = max(4, T // 10)
        lado = 2 * T + 3 * vao
        tab = pygame.Rect(0, 0, lado, lado)
        tab.center = (w // 2, h // 2 + 2)
        pygame.draw.rect(sup, COR_TRANCA, tab.inflate(8, 8), border_radius=10)
        pygame.draw.rect(sup, COR_TABULEIRO, tab, border_radius=8)
        for i, valor in enumerate((2, 64, 256, 2048)):
            x = tab.x + vao + (i % 2) * (T + vao)
            y = tab.y + vao + (i // 2) * (T + vao)
            sup.blit(cls.sprite(valor, T, jogador, False), (x, y))
        # Setinhas de deslizar dos lados
        for lado_x, s in ((tab.left - 22, -1), (tab.right + 22, 1)):
            cy = tab.centery
            pts = [(lado_x + s * 10, cy), (lado_x - s * 4, cy - 12), (lado_x - s * 4, cy + 12)]
            pygame.draw.polygon(sup, (110, 70, 40), [(x + 2, y + 2) for x, y in pts])
            pygame.draw.polygon(sup, AMARELO, pts)

    # --------------------------------------------------------
    # PARTIDA
    # --------------------------------------------------------

    def reiniciar(self):
        (self.n, self.bloco, self.vao, self.tam,
         self.x0, self.y0) = _geometria(self.opcao)
        self._fundo = self._fundo_tabuleiro(self.jogador, self.opcao)
        (self.r_desfazer, self.r_jogadas,
         self.r_maior, self.r_evolucao) = self._paineis(self.opcao)

        self.grade = [[0] * self.n for _ in range(self.n)]
        self.historico = []
        self.desfazer_restantes = DESFAZER_MAX
        self.jogadas = 0
        self.maior = 2
        self.descobertos = {2, 4}
        self.chegou_2048 = False

        self.fase = "jogando"       # jogando / espera_evoluiu / evoluiu / travado
        self.t_fase = 0.0
        self.menu_extra = None
        self.relogio = 0.0

        # Animação
        self.movimentos = []
        self.t_mov = -10.0
        self.pops = {}
        self.nova_peca = None
        self.t_nova = -10.0
        self.t_desfeito = -10.0
        self.proximo_confete = 0.0

        self.arrasto = None
        self.mouse = (-100, -100)

        # Duas peças iniciais (sem animação, aparecem já na prévia)
        for _ in range(2):
            self._nova_peca(animar=False)

    def _nova_peca(self, animar=True):
        vazias = [(l, c) for l in range(self.n) for c in range(self.n) if not self.grade[l][c]]
        if not vazias:
            return
        l, c = random.choice(vazias)
        self.grade[l][c] = 4 if random.random() < CHANCE_QUATRO else 2
        if animar:
            self.nova_peca = (l, c)
            self.t_nova = self.t_mov + DUR_DESLIZAR

    def _centro(self, l, c):
        passo = self.bloco + self.vao
        return (self.x0 + self.vao + c * passo + self.bloco / 2,
                self.y0 + self.vao + l * passo + self.bloco / 2)

    # --------------------------------------------------------
    # AÇÕES
    # --------------------------------------------------------

    def evento_jogo(self, e):
        if e.type == pygame.MOUSEMOTION:
            self.mouse = e.pos

        # Painéis por cima do tabuleiro (evoluiu / sem jogadas)
        if self.fase in ("evoluiu", "travado") and self.menu_extra is not None:
            if self.fase == "travado" and e.type == pygame.KEYDOWN and e.key in TECLAS_DESFAZER:
                self._desfazer()
                return
            escolha = self.menu_extra.evento(e)
            if escolha is not None:
                self._escolha_menu(self.menu_extra.botoes[escolha].rotulo)
            return

        if self.fase != "jogando":
            return

        if e.type == pygame.KEYDOWN:
            if e.key in TECLAS:
                self._mover(TECLAS[e.key])
            elif e.key in TECLAS_DESFAZER:
                self._desfazer()

        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self.r_desfazer.collidepoint(e.pos):
                self._desfazer()
            else:
                self.arrasto = e.pos

        elif e.type == pygame.MOUSEMOTION and self.arrasto is not None:
            self._conferir_arrasto(e.pos)

        elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
            if self.arrasto is not None:
                self._conferir_arrasto(e.pos)
            self.arrasto = None

    def _conferir_arrasto(self, pos):
        dx = pos[0] - self.arrasto[0]
        dy = pos[1] - self.arrasto[1]
        if max(abs(dx), abs(dy)) < ARRASTO_MIN:
            return
        self.arrasto = None         # um movimento por arrasto
        if abs(dx) > abs(dy):
            self._mover(DIR if dx > 0 else ESQ)
        else:
            self._mover(BAIXO if dy > 0 else CIMA)

    def _mover(self, direcao):
        nova, ganho, movimentos, fusoes, mudou = mover_grade(self.grade, direcao)
        if not mudou:
            self.som("bater", 0.25)
            return

        self.historico.append(([linha[:] for linha in self.grade], self.pontos, self.jogadas, self.maior))
        if len(self.historico) > HISTORICO_MAX:
            self.historico.pop(0)

        self.grade = nova
        self.pontos += ganho
        self.jogadas += 1
        self.movimentos = movimentos
        self.t_mov = self.relogio
        self.pops = {(l, c): self.t_mov + DUR_DESLIZAR for l, c, _ in fusoes}

        if fusoes:
            self.som("ponto", 0.7)
            self.textos.adicionar(f"+{ganho}", (140, 84), BRANCO, 12)
            maior_nova = 0
            for l, c, v in fusoes:
                _, cor = _estagio(v)
                self.particulas.explodir(self._centro(l, c), [cor, ui.clarear(cor, 50), BRANCO],
                                         6, 190, 0.5, (3, 6))
                self.maior = max(self.maior, v)
                if v not in self.descobertos:
                    self.descobertos.add(v)
                    maior_nova = max(maior_nova, v)
            if maior_nova:
                nome = t(_estagio(maior_nova)[0])
                self.textos.adicionar(t("NOVO: {nome}!", nome=nome), (LARGURA // 2, self.y0 + self.tam // 2),
                                      AMARELO, 16)
                self.tremer(0.1)
                self.som("acerto", 0.7)
                if maior_nova >= 2048 and not self.chegou_2048:
                    self.chegou_2048 = True
                    self.fase = "espera_evoluiu"
                    self.t_fase = 0.0
        else:
            self.som("virar", 0.25)

        self._nova_peca()
        if self.nova_peca:
            self.descobertos.add(self.grade[self.nova_peca[0]][self.nova_peca[1]])

        if self.fase == "jogando":
            self._conferir_travado()

    def _conferir_travado(self):
        if tem_movimento(self.grade):
            return
        self.fase = "travado"
        self.t_fase = 0.0
        self.menu_extra = None
        self.som("erro", 0.5)
        if self._pode_desfazer():
            self._montar_menu(["DESFAZER (Z)", "ENCERRAR"])

    def _pode_desfazer(self):
        return self.desfazer_restantes > 0 and bool(self.historico)

    def _desfazer(self):
        if not self._pode_desfazer():
            self.som("erro", 0.4)
            return
        grade, self.pontos, self.jogadas, self.maior = self.historico.pop()
        self.grade = grade
        self.desfazer_restantes -= 1
        self.movimentos = []
        self.pops = {}
        self.nova_peca = None
        self.t_desfeito = self.relogio
        self.fase = "jogando"
        self.menu_extra = None
        self.arrasto = None
        self.som("voltar", 0.7)
        self.particulas.explodir(self.r_desfazer.center, [AMARELO, BRANCO, self.jogador.cor], 12, 160, 0.5)

    def _montar_menu(self, rotulos):
        cx = self.x0 + self.tam // 2
        y = self.y0 + self.tam // 2 + 40
        self.menu_extra = ui.Menu(rotulos, cx, y, 300, 50, 12, 14)

    def _escolha_menu(self, rotulo):
        if rotulo == "CONTINUAR":
            self.som("selecionar")
            self.fase = "jogando"
            self.menu_extra = None
            self._conferir_travado()
        elif rotulo.startswith("DESFAZER"):
            self._desfazer()
        else:
            self._encerrar()

    def _encerrar(self):
        nome = t(_estagio(self.maior)[0])
        linhas = [t("PONTOS: {n}", n=self.pontos),
                  t("MAIOR: {nome} ({n})", nome=nome, n=self.maior),
                  t("JOGADAS: {n}", n=self.jogadas)]
        titulo = t("VOCÊ EVOLUIU!") if self.chegou_2048 else t("SEM JOGADAS!")
        self.terminar(venceu=self.chegou_2048, titulo=titulo, linhas=linhas)

    def calcular_moedas(self, valor, venceu):
        moedas = min(self.MOEDAS_MAX, valor // self.MOEDAS_POR)
        if self.chegou_2048:
            moedas += BONUS_2048
        if valor > 0:
            moedas = max(moedas, self.MOEDAS_MIN)
        return moedas

    # --------------------------------------------------------
    # LÓGICA
    # --------------------------------------------------------

    def atualizar_jogo(self, dt):
        self.relogio += dt

        if self.fase == "espera_evoluiu":
            self.t_fase += dt
            if self.t_fase >= ESPERA_EVOLUIU:
                self.fase = "evoluiu"
                self.t_fase = 0.0
                self._montar_menu(["CONTINUAR", "ENCERRAR"])
                self.som("vencer", 0.8)
                self.tremer(0.25)

        elif self.fase == "evoluiu":
            self.t_fase += dt
            self.proximo_confete -= dt
            if self.proximo_confete <= 0:
                self.proximo_confete = 0.25
                x = random.uniform(self.x0, self.x0 + self.tam)
                y = random.uniform(self.y0, self.y0 + self.tam * 0.4)
                self.particulas.explodir((x, y), [AMARELO, (255, 120, 150), (120, 200, 255),
                                                  (140, 230, 120), self.jogador.cor], 18, 240, 1.0)

        elif self.fase == "travado":
            self.t_fase += dt
            if self.menu_extra is None and self.t_fase >= ESPERA_TRAVADO:
                self._encerrar()

        if self.menu_extra is not None:
            self.menu_extra.atualizar(dt)

    # --------------------------------------------------------
    # DESENHO
    # --------------------------------------------------------

    def desenhar_jogo(self, tela):
        tela.blit(self._fundo, (0, 0))
        self._desenhar_pecas(tela)
        self._desenhar_paineis(tela)

        if self.fase == "evoluiu":
            self._desenhar_evoluiu(tela)
        elif self.fase == "travado":
            self._desenhar_travado(tela)

        self.particulas.desenhar(tela)
        self.textos.desenhar(tela)

    def _blit_escalado(self, tela, valor, centro, escala):
        img = self.sprite(valor, self.bloco, self.jogador)
        if escala <= 0.02:
            return
        if abs(escala - 1) > 0.01:
            lado = max(1, int(self.bloco * escala))
            img = pygame.transform.smoothscale(img, (lado, lado))
        tela.blit(img, img.get_rect(center=(int(centro[0]), int(centro[1]))))

    def _desenhar_pecas(self, tela):
        p = (self.relogio - self.t_mov) / DUR_DESLIZAR

        # Deslizando: desenha as peças da jogada anterior se movendo
        if p < 1 and self.movimentos:
            e = 1 - (1 - max(0.0, p)) ** 2
            # As que não se movem primeiro, as que deslizam por cima
            ordem = sorted(self.movimentos, key=lambda m: (m[0], m[1]) != (m[2], m[3]))
            for l0, c0, l1, c1, v in ordem:
                a = self._centro(l0, c0)
                b = self._centro(l1, c1)
                self._blit_escalado(tela, v, (a[0] + (b[0] - a[0]) * e, a[1] + (b[1] - a[1]) * e), 1.0)
            return

        # Parado: desenha a grade (com "pop" das fusões e a peça nova surgindo)
        surgir_desfeito = (self.relogio - self.t_desfeito) / DUR_SURGIR
        for l in range(self.n):
            for c in range(self.n):
                v = self.grade[l][c]
                if not v:
                    continue
                escala = 1.0
                if (l, c) == self.nova_peca:
                    q = (self.relogio - self.t_nova) / DUR_SURGIR
                    if q < 1:
                        q = max(0.0, q)
                        escala = q * (1 + 0.3 * math.sin(math.pi * q))
                elif (l, c) in self.pops:
                    q = (self.relogio - self.pops[(l, c)]) / DUR_POP
                    if 0 <= q < 1:
                        escala = 1.2 - 0.2 * q
                if surgir_desfeito < 1:
                    escala = 0.85 + 0.15 * max(0.0, surgir_desfeito)
                self._blit_escalado(tela, v, self._centro(l, c), escala)

    def _desenhar_paineis(self, tela):
        # ----- Botão DESFAZER -----
        r = self.r_desfazer
        pode = self._pode_desfazer() and self.fase == "jogando"
        hover = pode and r.collidepoint(self.mouse)
        miolo = r.inflate(-14, -14)
        cor = (150, 104, 62) if hover else (132, 92, 56)
        if not pode:
            cor = (100, 72, 48)
        pygame.draw.rect(tela, cor, miolo, border_radius=12)
        pygame.draw.rect(tela, AMARELO if hover else (190, 150, 100), miolo, 2, border_radius=12)
        ui.desenhar_texto(tela, t("DESFAZER"), (r.centerx, r.y + 22), 12,
                          BRANCO if pode else (170, 150, 130), "midtop")
        # Setinha curva
        cx, cy = r.centerx - 44, r.y + 70
        cor_seta = AMARELO if pode else (170, 150, 130)
        pygame.draw.arc(tela, cor_seta, (cx - 16, cy - 14, 32, 30), -1.2, math.pi, 5)
        pygame.draw.polygon(tela, cor_seta, [(cx - 24, cy - 2), (cx - 8, cy - 2), (cx - 16, cy + 9)])
        # Ovinhos = desfazer restantes
        for i in range(DESFAZER_MAX):
            ox = r.centerx - 8 + i * 26
            cheio = i < self.desfazer_restantes
            ret = pygame.Rect(0, 0, 18, 24)
            ret.center = (ox, cy)
            if cheio:
                pygame.draw.ellipse(tela, self.jogador.cor_contorno, ret.inflate(4, 4))
                pygame.draw.ellipse(tela, self.jogador.cor, ret)
                pygame.draw.ellipse(tela, ui.clarear(self.jogador.cor, 70), (ret.x + 4, ret.y + 4, 5, 7))
            else:
                pygame.draw.ellipse(tela, (80, 58, 40), ret)
                pygame.draw.ellipse(tela, (150, 120, 90), ret, 2)
        ui.desenhar_texto(tela, "(Z)", (r.centerx, r.bottom - 14), 10, (220, 200, 170), "midbottom")

        # ----- Jogadas -----
        r = self.r_jogadas
        ui.desenhar_texto(tela, t("JOGADAS"), (r.centerx, r.y + 14), 10, (230, 210, 175), "midtop")
        ui.desenhar_texto(tela, str(self.jogadas), (r.centerx, r.bottom - 12), 16, BRANCO, "midbottom")

        # ----- Maior ovo -----
        r = self.r_maior
        ui.desenhar_texto(tela, t("MAIOR OVO"), (r.centerx, r.y + 14), 10, (230, 210, 175), "midtop")
        img = self.sprite(self.maior, 104, self.jogador)
        dy = math.sin(self.tempo * 2.5) * 3
        tela.blit(img, img.get_rect(center=(r.centerx, r.y + 92 + dy)))
        nome = t(_estagio(self.maior)[0])
        linhas = ui.quebrar_linhas(nome, 10, r.w - 20)
        y = r.bottom - 18 - (len(linhas) - 1) * 16
        for linha in linhas:
            ui.desenhar_texto(tela, linha, (r.centerx, y), 10, AMARELO, "center")
            y += 16

        # ----- Escada da evolução -----
        r = self.r_evolucao
        ui.desenhar_texto(tela, t("EVOLUÇÃO"), (r.centerx, r.y + 16), 12, AMARELO, "midtop")
        pulso = 0.5 + 0.5 * math.sin(self.tempo * 5)
        for i, valor in enumerate(ESCADA):
            x = r.x + 16 + (i % 2) * 80
            y = r.y + 44 + (i // 2) * 72
            quadro = pygame.Rect(x, y, 64, 64)
            if valor in self.descobertos:
                tela.blit(self.sprite(valor, 64, self.jogador), quadro)
                if valor == self.maior:
                    cor = ui.misturar((255, 200, 60), (255, 250, 200), pulso)
                    pygame.draw.rect(tela, cor, quadro.inflate(6, 6), 3, border_radius=10)
            else:
                pygame.draw.rect(tela, (78, 54, 36), quadro, border_radius=8)
                pygame.draw.ellipse(tela, (98, 70, 48), quadro.inflate(-26, -18))
                ui.desenhar_texto(tela, "?", (quadro.centerx + 1, quadro.centery + 1), 16,
                                  (160, 130, 100), "center", False)

    def _painel_central(self, tela, altura):
        area = pygame.Rect(self.x0, self.y0, self.tam, self.tam)
        veu = pygame.Surface(area.size, pygame.SRCALPHA)
        pygame.draw.rect(veu, (40, 24, 10, 150), veu.get_rect(), border_radius=18)
        tela.blit(veu, area)
        caixa = pygame.Rect(0, 0, min(self.tam - 20, 460), altura)
        caixa.center = area.center
        ui.painel(tela, caixa, (28, 32, 56), AMARELO, 20, 4)
        return caixa

    def _desenhar_evoluiu(self, tela):
        caixa = self._painel_central(tela, 330)
        ui.desenhar_texto(tela, t("VOCÊ EVOLUIU!"), (caixa.centerx, caixa.y + 22), 20, AMARELO, "midtop")
        dy = -abs(math.sin(self.t_fase * 5)) * 12
        ang = math.sin(self.t_fase * 4) * 10
        img = self.sprite(2048, 96, self.jogador)
        img = pygame.transform.rotate(img, ang)
        tela.blit(img, img.get_rect(center=(caixa.centerx, caixa.y + 110 + dy)))
        for i, b in enumerate(self.menu_extra.botoes):
            b.rect.midtop = (caixa.centerx, caixa.y + 184 + i * 62)
        self.menu_extra.desenhar(tela)

    def _desenhar_travado(self, tela):
        if self.menu_extra is None:
            # Sem desfazer: só um aviso rápido antes da tela de fim
            area = pygame.Rect(self.x0, self.y0, self.tam, self.tam)
            ui.desenhar_texto(tela, t("SEM JOGADAS!"), area.center, 24, (255, 120, 120), "center")
            return
        caixa = self._painel_central(tela, 270)
        ui.desenhar_texto(tela, t("SEM JOGADAS!"), (caixa.centerx, caixa.y + 24), 20, (255, 130, 130), "midtop")
        ui.desenhar_texto(tela, t("DESFAZER RESTANTES: {n}", n=self.desfazer_restantes),
                          (caixa.centerx, caixa.y + 70), 10, BRANCO, "midtop")
        for i, b in enumerate(self.menu_extra.botoes):
            b.rect.midtop = (caixa.centerx, caixa.y + 110 + i * 62)
        self.menu_extra.desenhar(tela)

    def desenhar_hud(self, tela):
        fundo = (20, 24, 40)
        caixa = pygame.Rect(12, 12, 250, 48)
        ui.painel(tela, caixa, fundo, BRANCO, 12, 3, sombra=False)
        ui.desenhar_texto(tela, t("PONTOS: {n}", n=self.pontos), (caixa.x + 16, caixa.centery + 1), 14,
                          AMARELO, "midleft")

        caixa2 = pygame.Rect(caixa.right + 12, 12, 230, 48)
        ui.painel(tela, caixa2, fundo, BRANCO, 12, 3, sombra=False)
        ui.desenhar_texto(tela, t(self.OPCOES[self.opcao]), (caixa2.x + 14, caixa2.y + 9), 10, (180, 220, 255))
        rec = self.recorde()
        texto_rec = t("RECORDE: {n}", n=rec if rec is not None else "--")
        ui.desenhar_texto(tela, texto_rec, (caixa2.x + 14, caixa2.y + 26), 12, AMARELO)


def _trancado(sup, borda):
    """Borda de palha trançada em volta do tabuleiro."""
    passo = 16
    cores = (ui.clarear(COR_TRANCA, 40), ui.escurecer(COR_TRANCA, 25))
    # Lados de cima e de baixo
    for i, x in enumerate(range(borda.left + 18, borda.right - 26, passo)):
        for y in (borda.top + 2, borda.bottom - 12):
            cor = cores[i % 2]
            pygame.draw.arc(sup, cor, (x, y, 20, 10), 0 if i % 2 else math.pi, math.pi if i % 2 else math.tau, 3)
            pygame.draw.line(sup, PALHAS[i % 2], (x + 3, y + 5), (x + 17, y + 5), 1)
    # Laterais
    for i, y in enumerate(range(borda.top + 18, borda.bottom - 26, passo)):
        for x in (borda.left + 2, borda.right - 12):
            cor = cores[i % 2]
            ang = (math.pi / 2, math.pi * 1.5) if i % 2 else (-math.pi / 2, math.pi / 2)
            pygame.draw.arc(sup, cor, (x, y, 10, 20), ang[0], ang[1], 3)
            pygame.draw.line(sup, PALHAS[i % 2], (x + 5, y + 3), (x + 5, y + 17), 1)
