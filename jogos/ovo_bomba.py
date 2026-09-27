import math
import random

import pygame

from settings import *
from core import ui
from jogos.base_multi import (MiniJogoMulti, TECLAS_MOVER, TECLAS_ACAO, CORES_JOGADOR,
                              jogador_da_tecla)

# ============================================================
# OVO-BOMBA
# ============================================================
# Dois ovos num labirinto de pilares de pedra e caixas de ovos.
# As "bombas" são OVOS DE PÁSCOA de chocolate com pavio: a
# explosão é de confete e chocolate! Quem for pego vira um OVO
# DE CHOCOLATE e perde o round. Estoure as caixas para achar
# itens: +BOMBA, +FOGO, TÊNIS e CHUTE.

COLS = 15
LINHAS = 11
CEL = 56
X0 = 92
Y0 = 92
AREA = pygame.Rect(X0, Y0, COLS * CEL, LINHAS * CEL)

VAZIO, PILAR, CAIXA = 0, 1, 2

SPAWNS = [(0, 0), (COLS - 1, LINHAS - 1)]
# Células sempre livres em "L" em volta de cada spawn
LIVRES = {(0, 0), (1, 0), (0, 1), (COLS - 1, LINHAS - 1), (COLS - 2, LINHAS - 1), (COLS - 1, LINHAS - 2)}

DIRECOES = {"cima": (0, -1), "baixo": (0, 1), "esq": (-1, 0), "dir": (1, 0)}

VEL_INICIAL = 200
VEL_MAXIMA = 320
ASSISTENCIA = 18                # px: desliza para alinhar com o corredor
PAVIO = 2.5
DURACAO_FOGO = 0.5
MAX_BOMBAS = 8
MAX_ALCANCE = 8
VEL_CHUTE = 380
TEMPO_MORTE_SUBITA = 90.0
INTERVALO_MORTE_SUBITA = 0.25
TEMPO_FIM_ROUND = 1.8
TEMPO_ANUNCIO = 1.5
ALTURA_OVO = 46

ITENS = ["bomba", "fogo", "tenis", "chute"]
NOMES_ITENS = {"bomba": "+BOMBA", "fogo": "+FOGO", "tenis": "TÊNIS!", "chute": "CHUTE!"}

# Modos: (vitórias para ganhar, chance de item, bombas iniciais, alcance inicial)
MODOS = [
    (2, 0.30, 1, 2),        # MELHOR DE 3
    (3, 0.30, 1, 2),        # MELHOR DE 5
    (2, 0.60, 2, 3),        # CAOS
]

CHOCOLATE = (110, 62, 30)
CHOCOLATE_CLARO = (160, 100, 55)
CONFETE = [(255, 90, 120), (255, 214, 64), (90, 200, 255), (140, 230, 120), (200, 140, 255),
           (255, 255, 255)]


def _centro(cel):
    return (X0 + cel[0] * CEL + CEL / 2, Y0 + cel[1] * CEL + CEL / 2)


def _cel_de(x, y):
    c = int((x - X0) // CEL)
    l = int((y - Y0) // CEL)
    return (min(COLS - 1, max(0, c)), min(LINHAS - 1, max(0, l)))


def _dentro(cel):
    return 0 <= cel[0] < COLS and 0 <= cel[1] < LINHAS


def _espiral():
    """Ordem das células na morte súbita: de fora para dentro."""
    ordem = []
    esq, dir_, cima, baixo = 0, COLS - 1, 0, LINHAS - 1
    while esq <= dir_ and cima <= baixo:
        for c in range(esq, dir_ + 1):
            ordem.append((c, cima))
        for l in range(cima + 1, baixo + 1):
            ordem.append((dir_, l))
        if cima < baixo:
            for c in range(dir_ - 1, esq - 1, -1):
                ordem.append((c, baixo))
        if esq < dir_:
            for l in range(baixo - 1, cima, -1):
                ordem.append((esq, l))
        esq, dir_, cima, baixo = esq + 1, dir_ - 1, cima + 1, baixo - 1
    return ordem


ESPIRAL = _espiral()


# ============================================================
# SPRITES (desenhados uma vez só)
# ============================================================

_sprites = {}


def _pilar_sup():
    s = _sprites.get("pilar")
    if s is None:
        s = pygame.Surface((CEL, CEL), pygame.SRCALPHA)
        pygame.draw.rect(s, (60, 60, 70), (2, 6, CEL - 4, CEL - 6), border_radius=8)
        pygame.draw.rect(s, (150, 150, 160), (2, 2, CEL - 4, CEL - 8), border_radius=8)
        pygame.draw.rect(s, (185, 185, 195), (6, 4, CEL - 12, CEL - 22), border_radius=6)
        pygame.draw.line(s, (130, 130, 142), (8, CEL - 16), (CEL - 9, CEL - 16), 2)
        pygame.draw.line(s, (165, 165, 178), (CEL // 2, 6), (CEL // 2 - 4, 20), 2)
        pygame.draw.circle(s, (205, 205, 215), (14, 12), 3)
        pygame.draw.rect(s, (90, 90, 102), (2, 2, CEL - 4, CEL - 4), 2, border_radius=8)
        _sprites["pilar"] = s
    return s


def _caixa_sup():
    s = _sprites.get("caixa")
    if s is None:
        s = pygame.Surface((CEL, CEL), pygame.SRCALPHA)
        corpo = pygame.Rect(4, 8, CEL - 8, CEL - 12)
        pygame.draw.rect(s, (130, 90, 50), corpo.move(0, 3), border_radius=6)
        pygame.draw.rect(s, (200, 150, 90), corpo, border_radius=6)
        # Calombos da caixa de ovos (2x2)
        for cx in (18, 38):
            for cy in (20, 38):
                pygame.draw.circle(s, (175, 128, 72), (cx + 1, cy + 2), 9)
                pygame.draw.circle(s, (215, 170, 110), (cx, cy), 9)
                pygame.draw.circle(s, (232, 195, 140), (cx - 3, cy - 3), 3)
        # Fita
        pygame.draw.rect(s, (220, 60, 70), (CEL // 2 - 3, 8, 6, CEL - 12))
        pygame.draw.rect(s, (255, 120, 130), (CEL // 2 - 3, 8, 2, CEL - 12))
        pygame.draw.rect(s, (130, 90, 50), corpo, 2, border_radius=6)
        _sprites["caixa"] = s
    return s


def _bomba_sup(cor):
    """Ovo de páscoa embrulhado em papel listrado na cor do dono."""
    chave = ("bomba", cor)
    s = _sprites.get(chave)
    if s is not None:
        return s
    w, h = 40, 50
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    corpo = pygame.Rect(2, 8, w - 4, h - 10)
    listras = pygame.Surface((w, h), pygame.SRCALPHA)
    listras.fill(cor)
    # Listras claras (no ovo branco, listras lilás para aparecer)
    clara = (160, 175, 235) if sum(cor) > 600 else ui.misturar(cor, BRANCO, 0.75)
    for i in range(-3, 8):
        y = 8 + i * 9
        pygame.draw.polygon(listras, clara, [(0, y), (w, y - 10), (w, y - 5), (0, y + 5)])
    mascara = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(mascara, (255, 255, 255, 255), corpo)
    listras.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    contorno = (90, 90, 110) if sum(cor) > 600 else ui.escurecer(cor, 90)
    pygame.draw.ellipse(s, contorno, corpo.inflate(4, 4))
    s.blit(listras, (0, 0))
    pygame.draw.ellipse(s, (255, 255, 255), (10, 14, 8, 12))
    # Laço no topo
    pygame.draw.polygon(s, (230, 60, 80), [(20, 10), (11, 4), (11, 14)])
    pygame.draw.polygon(s, (230, 60, 80), [(20, 10), (29, 4), (29, 14)])
    pygame.draw.circle(s, (255, 120, 140), (20, 10), 3)
    _sprites[chave] = s
    return s


def _item_sup(tipo):
    """Cápsula em forma de ovo com o ícone do item."""
    chave = ("item", tipo)
    s = _sprites.get(chave)
    if s is not None:
        return s
    s = pygame.Surface((40, 48), pygame.SRCALPHA)
    cores = {"bomba": (255, 120, 150), "fogo": (255, 170, 60), "tenis": (90, 200, 255),
             "chute": (150, 230, 110)}
    cor = cores[tipo]
    pygame.draw.ellipse(s, ui.escurecer(cor, 90), (1, 1, 38, 46))
    pygame.draw.ellipse(s, cor, (3, 3, 34, 42))
    pygame.draw.ellipse(s, ui.misturar(cor, BRANCO, 0.6), (7, 7, 26, 32))
    cx, cy = 20, 25
    if tipo == "bomba":
        pygame.draw.ellipse(s, (60, 40, 70), (cx - 8, cy - 8, 16, 19))
        pygame.draw.line(s, (120, 90, 60), (cx, cy - 8), (cx + 4, cy - 13), 2)
        pygame.draw.circle(s, (255, 200, 60), (cx + 5, cy - 14), 3)
        pygame.draw.circle(s, (150, 130, 170), (cx - 3, cy - 3), 2)
    elif tipo == "fogo":
        pygame.draw.polygon(s, (230, 70, 30), [(cx, cy - 13), (cx + 9, cy + 1), (cx + 6, cy + 10),
                                               (cx - 6, cy + 10), (cx - 9, cy + 1)])
        pygame.draw.polygon(s, (255, 210, 60), [(cx, cy - 4), (cx + 5, cy + 4), (cx + 3, cy + 9),
                                                (cx - 3, cy + 9), (cx - 5, cy + 4)])
    elif tipo == "tenis":
        pygame.draw.rect(s, (230, 50, 60), (cx - 11, cy - 4, 16, 10), border_radius=4)
        pygame.draw.rect(s, (230, 50, 60), (cx - 11, cy - 10, 9, 10), border_radius=3)
        pygame.draw.rect(s, (255, 255, 255), (cx - 12, cy + 5, 24, 4), border_radius=2)
        pygame.draw.line(s, (255, 255, 255), (cx - 8, cy - 5), (cx - 3, cy - 5), 2)
        pygame.draw.line(s, (255, 255, 255), (cx - 8, cy - 1), (cx - 1, cy - 1), 2)
    else:
        pygame.draw.ellipse(s, (240, 190, 150), (cx - 8, cy - 6, 15, 17))
        for i, dx in enumerate((-7, -3, 1, 5)):
            pygame.draw.circle(s, (240, 190, 150), (cx + dx, cy - 9), 3 - i // 3)
        pygame.draw.ellipse(s, (180, 120, 90), (cx - 8, cy - 6, 15, 17), 1)
    _sprites[chave] = s
    return s


def _icone_hud(tipo):
    chave = ("hud", tipo)
    s = _sprites.get(chave)
    if s is None:
        s = _sprites[chave] = pygame.transform.smoothscale(_item_sup(tipo), (20, 24))
    return s


# ============================================================
# OBJETOS
# ============================================================

class Bomber:

    def __init__(self, i, cel, bombas, alcance):
        self.i = i
        self.x, self.y = _centro(cel)
        self.vel = VEL_INICIAL
        self.bombas = bombas
        self.alcance = alcance
        self.chute = False
        self.vivo = True
        self.tempo_morto = 0.0
        self.olhando = (1, 0) if i == 0 else (-1, 0)
        self.andando = False
        self.passos = 0.0
        self.pilha = []             # direções apertadas (a última manda)

    @property
    def cel(self):
        return _cel_de(self.x, self.y)


class Bomba:

    def __init__(self, dono, cel, alcance, livres):
        self.dono = dono
        self.x, self.y = _centro(cel)
        self.alcance = alcance
        self.pavio = PAVIO
        self.livres = set(livres)   # jogadores que ainda estão em cima dela
        self.desliza = None         # direção quando chutada
        self.explodiu = False
        self.fase = random.random() * 6

    @property
    def cel(self):
        return _cel_de(self.x, self.y)


# ============================================================
# JOGO
# ============================================================

class OvoBomba(MiniJogoMulti):

    ID = "ovo_bomba"
    TITULO = "OVO-BOMBA"
    TITULO_CURTO = "OVO-BOMBA"
    DESCRICAO = "Solte ovos de páscoa com pavio no labirinto, estoure as caixas e cubra o rival de chocolate!"
    COR = (200, 120, 60)
    INSTRUCOES = [
        "Solte OVOS DE PÁSCOA com pavio e fuja da explosão!",
        "Estoure as caixas de ovos para achar itens.",
        "Quem virar OVO DE CHOCOLATE perde o round.",
        "J1: WASD + ESPAÇO/F    J2: SETAS + ENTER/CTRL",
    ]
    OPCOES = ["MELHOR DE 3", "MELHOR DE 5", "CAOS (MUITOS ITENS)"]
    CONTROLES_J1 = "WASD + ESPAÇO"
    CONTROLES_J2 = "SETAS + ENTER"
    CONTAGEM = True

    TRILHA = dict(bpm=140, tom="C#", escala="menor", lead="quadrada", duty=0.25,
                  envelope="normal", baixo="sincopado", onda_baixo="serra",
                  acomp="arpejo16", onda_acomp="quadrada", bateria="breakbeat",
                  energia=0.85, eco=(0.12, 0.2))

    MOEDAS_PARTIDA = 12
    MOEDAS_VITORIA_J1 = 8
    MOEDAS_POR_ROUND = 2
    MOEDAS_TETO = 30

    # --------------------------------------------------------
    # CENÁRIO: jardim com cerca-viva e grama em xadrez
    # --------------------------------------------------------

    @classmethod
    def criar_fundo(cls, jogador):
        sup = pygame.Surface((LARGURA, ALTURA))
        sup.fill((40, 120, 50))
        rnd = random.Random(17)

        # Cerca-viva em volta com folhinhas e flores
        for _ in range(900):
            x, y = rnd.randrange(LARGURA), rnd.randrange(ALTURA)
            cor = rnd.choice([(30, 100, 40), (55, 140, 60), (70, 160, 70)])
            pygame.draw.ellipse(sup, cor, (x, y, rnd.randint(5, 9), rnd.randint(3, 6)))
        for _ in range(70):
            x, y = rnd.randrange(LARGURA), rnd.randrange(ALTURA)
            if AREA.inflate(20, 20).collidepoint(x, y):
                continue
            cor = rnd.choice([(255, 120, 150), (255, 230, 90), (255, 255, 255), (170, 130, 255)])
            for dx, dy in ((-3, 0), (3, 0), (0, -3), (0, 3)):
                pygame.draw.circle(sup, cor, (x + dx, y + dy), 3)
            pygame.draw.circle(sup, (255, 200, 40), (x, y), 2)

        # Borda da arena
        pygame.draw.rect(sup, (25, 80, 35), AREA.inflate(16, 16), border_radius=10)

        # Grama em xadrez
        for c in range(COLS):
            for l in range(LINHAS):
                cor = (100, 190, 90) if (c + l) % 2 == 0 else (110, 200, 100)
                pygame.draw.rect(sup, cor, (X0 + c * CEL, Y0 + l * CEL, CEL, CEL))
        for _ in range(500):
            x = rnd.randrange(AREA.left, AREA.right)
            y = rnd.randrange(AREA.top + 6, AREA.bottom)
            pygame.draw.line(sup, (90, 175, 80), (x, y), (x + rnd.randint(-2, 2), y - 5), 2)

        # Pilares fixos (ímpar, ímpar)
        pilar = _pilar_sup()
        for c in range(1, COLS, 2):
            for l in range(1, LINHAS, 2):
                x, y = X0 + c * CEL, Y0 + l * CEL
                pygame.draw.ellipse(sup, (70, 140, 65), (x + 2, y + CEL - 12, CEL - 2, 14))
                sup.blit(pilar, (x, y))
        return sup

    @classmethod
    def desenhar_icone(cls, sup, jogador):
        w, h = sup.get_size()
        y = h // 2 + 12
        jogador.desenhar(sup, (w // 2 - 50, y), 44)
        b = pygame.transform.smoothscale(_bomba_sup(jogador.cor), (34, 42))
        sup.blit(b, b.get_rect(center=(w // 2 + 6, y + 2)))
        pygame.draw.circle(sup, (255, 230, 90), (w // 2 + 7, y - 22), 5)
        pygame.draw.circle(sup, (255, 255, 255), (w // 2 + 7, y - 22), 2)
        c = pygame.transform.smoothscale(_caixa_sup(), (44, 44))
        sup.blit(c, c.get_rect(center=(w // 2 + 60, y)))

    # --------------------------------------------------------
    # PARTIDA
    # --------------------------------------------------------

    def reiniciar(self):
        self.modo = MODOS[self.opcao]
        self.vitorias_round = [0, 0]
        self.round = 1
        self.rounds_jogados = 0
        self.seguradas = set()
        self._montar_round()

    def _montar_round(self):
        precisa, chance, bombas, alcance = self.modo
        self.chance_item = chance

        # Grade: pilares fixos + caixas em 65% das células livres
        self.grade = [[VAZIO] * COLS for _ in range(LINHAS)]
        for l in range(LINHAS):
            for c in range(COLS):
                if c % 2 == 1 and l % 2 == 1:
                    self.grade[l][c] = PILAR
                elif (c, l) not in LIVRES and random.random() < 0.65:
                    self.grade[l][c] = CAIXA

        self.ovos = [Bomber(i, SPAWNS[i], bombas, alcance) for i in (0, 1)]
        self.bombas = []
        self.itens = {}
        self.fogo = {}              # cel -> [tempo, conjunto de direções]
        self.queda = []             # pilares da morte súbita caindo: [cel, tempo]
        self._camada = None
        self.tempo_round = 0.0
        self.morte_subita = False
        self.relogio_subita = 0.0
        self.indice_subita = 0
        self.fase = "anuncio"       # anuncio, jogo, fim_round
        self.tempo_fase = 0.0 if self.round > 1 else TEMPO_ANUNCIO
        self.vencedor_round = None
        self.primeira_morte = None

    # --------------------------------------------------------
    # ENTRADA
    # --------------------------------------------------------

    def entrar(self):
        self.seguradas = set()
        super().entrar()

    def evento(self, e):
        if e.type == pygame.KEYDOWN:
            self.seguradas.add(e.key)
            i = jogador_da_tecla(e.key)
            if i is not None:
                for nome, k in TECLAS_MOVER[i].items():
                    if k == e.key:
                        pilha = self.ovos[i].pilha
                        if nome in pilha:
                            pilha.remove(nome)
                        pilha.append(nome)
        elif e.type == pygame.KEYUP:
            self.seguradas.discard(e.key)
        elif e.type == pygame.WINDOWFOCUSLOST:
            self.seguradas.clear()
        super().evento(e)

    def evento_jogo(self, e):
        if e.type == pygame.KEYDOWN:
            for i in (0, 1):
                if e.key in TECLAS_ACAO[i]:
                    self._soltar_bomba(self.ovos[i])

    def _segura(self, tecla):
        if tecla in self.seguradas:
            return True
        try:
            return bool(pygame.key.get_pressed()[tecla])
        except (IndexError, pygame.error):
            return False

    def _desejos(self, ovo):
        """Direções seguradas, da mais recente para a mais antiga."""
        teclas = TECLAS_MOVER[ovo.i]
        vivas = [n for n in ovo.pilha if self._segura(teclas[n])]
        # Tecla segurada que não passou pela pilha (ex: apertada antes de entrar)
        for n, k in teclas.items():
            if n not in vivas and self._segura(k):
                vivas.insert(0, n)
        ovo.pilha = [n for n in ovo.pilha if n in vivas]
        return [DIRECOES[n] for n in reversed(vivas)]

    # --------------------------------------------------------
    # LÓGICA
    # --------------------------------------------------------

    def calcular_moedas(self, valor, venceu):
        base = self.MOEDAS_PARTIDA + (self.MOEDAS_VITORIA_J1 if venceu else 0)
        return min(self.MOEDAS_TETO, base + self.MOEDAS_POR_ROUND * self.rounds_jogados)

    def atualizar_jogo(self, dt):
        self.tempo_fase += dt

        if self.fase == "anuncio":
            if self.tempo_fase >= TEMPO_ANUNCIO:
                self.fase = "jogo"
                self.tempo_fase = 0.0
            for ovo in self.ovos:
                ovo.andando = False
            return

        self.tempo_round += dt

        # Movimento
        for ovo in self.ovos:
            if ovo.vivo:
                self._mover_ovo(ovo, dt)
            else:
                ovo.tempo_morto += dt

        # Itens
        for ovo in self.ovos:
            if ovo.vivo and ovo.cel in self.itens:
                self._pegar_item(ovo, self.itens.pop(ovo.cel))

        # Bombas: quem saiu de cima perde a "passagem livre"
        for b in self.bombas:
            for ovo in self.ovos:
                if ovo.i in b.livres and (abs(ovo.x - b.x) >= CEL - 6 or abs(ovo.y - b.y) >= CEL - 6):
                    b.livres.discard(ovo.i)
            b.fase += dt * (5 + 16 * (1 - max(0.0, b.pavio) / PAVIO))
            if b.desliza:
                self._deslizar(b, dt)

        for b in list(self.bombas):
            b.pavio -= dt
            if b.pavio <= 0 and not b.explodiu:
                self._explodir(b)

        # Fogo
        for cel in list(self.fogo):
            self.fogo[cel][0] -= dt
            if self.fogo[cel][0] <= 0:
                del self.fogo[cel]

        # Morte súbita
        if self.tempo_round >= TEMPO_MORTE_SUBITA and self.fase == "jogo":
            if not self.morte_subita:
                self.morte_subita = True
                self.som("bandeira")
                self.tremer(0.2)
            self._morte_subita(dt)
        for q in self.queda:
            q[1] += dt
        self.queda = [q for q in self.queda if q[1] < 0.3]

        # Quem está no fogo vira ovo de chocolate (depois do round, ninguém mais)
        if self.fase == "jogo":
            for ovo in self.ovos:
                if ovo.vivo and ovo.cel in self.fogo:
                    self._pegar(ovo)

        self._checar_round(dt)

    # --- movimento com assistência de canto ---

    def _mover_ovo(self, ovo, dt):
        if self.fase != "jogo":
            ovo.andando = False
            return
        dist = ovo.vel * dt
        ovo.andando = False
        for d in self._desejos(ovo):
            if self._tentar_mover(ovo, d, dist):
                ovo.olhando = d
                ovo.andando = True
                ovo.passos += dist
                return
            if ovo.chute:
                self._tentar_chutar(ovo, d)

    def _livre(self, cel, ovo=None):
        if not _dentro(cel) or self.grade[cel[1]][cel[0]] != VAZIO:
            return False
        for b in self.bombas:
            if b.cel == cel and (ovo is None or ovo.i not in b.livres):
                return False
        return True

    def _tentar_mover(self, ovo, d, dist):
        eixo = 0 if d[0] else 1
        outro = 1 - eixo
        pos = [ovo.x, ovo.y]
        cel = ovo.cel
        centro = _centro(cel)
        alvo = (cel[0] + d[0], cel[1] + d[1])

        # Fora do corredor: desliza para alinhar (assistência de canto)
        desvio = pos[outro] - centro[outro]
        if abs(desvio) > 0.01:
            if abs(desvio) > ASSISTENCIA or not self._livre(alvo, ovo):
                return False
            if dist >= abs(desvio):
                pos[outro] = centro[outro]
            else:
                pos[outro] -= math.copysign(dist, desvio)
            ovo.x, ovo.y = pos
            return True

        pos[outro] = centro[outro]
        sinal = d[eixo]
        antes = (pos[eixo] - centro[eixo]) * sinal     # < 0: ainda não chegou no centro
        if self._livre(alvo, ovo):
            pos[eixo] += sinal * min(dist, CEL / 2)
        elif antes < -0.01:
            pos[eixo] += sinal * min(dist, -antes)
        else:
            pos[eixo] = centro[eixo]
            ovo.x, ovo.y = pos
            return False
        ovo.x, ovo.y = pos
        return True

    def _tentar_chutar(self, ovo, d):
        cel = ovo.cel
        alvo = (cel[0] + d[0], cel[1] + d[1])
        for b in self.bombas:
            if b.cel == alvo and not b.desliza and ovo.i not in b.livres:
                prox = (alvo[0] + d[0], alvo[1] + d[1])
                if self._pode_deslizar(prox):
                    b.desliza = d
                    self.som("bater", 0.6)
                return

    def _pode_deslizar(self, cel):
        if not self._livre(cel):
            return False
        if cel in self.itens:
            return False
        return all(not o.vivo or o.cel != cel for o in self.ovos)

    def _deslizar(self, b, dt):
        d = b.desliza
        eixo = 0 if d[0] else 1
        pos = [b.x, b.y]
        centro = _centro(b.cel)
        falta = (centro[eixo] - pos[eixo]) * d[eixo]    # > 0: ainda não chegou no centro
        passo = VEL_CHUTE * dt
        if falta > 0.01:
            pos[eixo] += d[eixo] * min(passo, falta)
        else:
            prox = (b.cel[0] + d[0], b.cel[1] + d[1])
            if self._pode_deslizar(prox) and not any(o is not b and o.cel == prox for o in self.bombas):
                pos[eixo] += d[eixo] * min(passo, CEL / 2)
            else:
                pos[eixo] = centro[eixo]
                b.desliza = None
        b.x, b.y = pos

    # --- bombas e explosões ---

    def _soltar_bomba(self, ovo):
        if not ovo.vivo or self.fase != "jogo":
            return
        cel = ovo.cel
        if sum(1 for b in self.bombas if b.dono == ovo.i) >= ovo.bombas:
            return
        if any(b.cel == cel for b in self.bombas) or self.grade[cel[1]][cel[0]] != VAZIO:
            return
        em_cima = [o.i for o in self.ovos
                   if o.vivo and abs(o.x - _centro(cel)[0]) < CEL - 6 and abs(o.y - _centro(cel)[1]) < CEL - 6]
        self.bombas.append(Bomba(ovo.i, cel, ovo.alcance, em_cima))
        self.som("pulo", 0.5)

    def _explodir(self, primeira):
        fila = [primeira]
        caixas = []
        while fila:
            b = fila.pop()
            if b.explodiu:
                continue
            b.explodiu = True
            if b in self.bombas:
                self.bombas.remove(b)
            origem = b.cel
            self._acender(origem, None)
            for d in DIRECOES.values():
                for k in range(1, b.alcance + 1):
                    cel = (origem[0] + d[0] * k, origem[1] + d[1] * k)
                    if not _dentro(cel) or self.grade[cel[1]][cel[0]] == PILAR:
                        break
                    self._acender(cel, d, ponta=True)
                    self._acender((cel[0] - d[0], cel[1] - d[1]), d, ponta=False)
                    if self.grade[cel[1]][cel[0]] == CAIXA:
                        caixas.append(cel)
                        break
                    outra = next((o for o in self.bombas if o.cel == cel and not o.explodiu), None)
                    if outra:
                        fila.append(outra)      # reação em cadeia
                        break
            x, y = _centro(origem)
            self.particulas.explodir((x, y), CONFETE, 22, 320, 0.9, (3, 6), 300)
            self.particulas.explodir((x, y), [CHOCOLATE, CHOCOLATE_CLARO], 10, 220, 0.7, (4, 7))

        # Caixas quebram (e às vezes soltam um item)
        for cel in caixas:
            if self.grade[cel[1]][cel[0]] != CAIXA:
                continue
            self.grade[cel[1]][cel[0]] = VAZIO
            x, y = _centro(cel)
            self.particulas.explodir((x, y), [(200, 150, 90), (215, 170, 110), (150, 105, 60)],
                                     12, 240, 0.7, (3, 7))
            if random.random() < self.chance_item:
                self.itens[cel] = random.choice(ITENS)
        self.tremer(0.2)
        self.som("explosao", 0.55)

    def _acender(self, cel, d, ponta=True):
        """Marca fogo na célula; d = direção do braço (None = centro)."""
        f = self.fogo.get(cel)
        if f is None:
            f = self.fogo[cel] = [DURACAO_FOGO, set(), DURACAO_FOGO]
        f[0] = DURACAO_FOGO
        f[2] = DURACAO_FOGO
        if d is None:
            return
        # A ponta liga para trás; o anterior liga para frente
        if ponta:
            f[1].add((-d[0], -d[1]))
        else:
            f[1].add(d)

    def _pegar_item(self, ovo, tipo):
        if tipo == "bomba":
            ovo.bombas = min(MAX_BOMBAS, ovo.bombas + 1)
        elif tipo == "fogo":
            ovo.alcance = min(MAX_ALCANCE, ovo.alcance + 1)
        elif tipo == "tenis":
            ovo.vel = min(VEL_MAXIMA, ovo.vel + 30)
        else:
            ovo.chute = True
        self.som("moeda", 0.7)
        self.textos.adicionar(NOMES_ITENS[tipo], (ovo.x, ovo.y - 40), CORES_JOGADOR[ovo.i], 12)
        self.particulas.explodir((ovo.x, ovo.y), [AMARELO, BRANCO, self.cor(ovo.i)], 12, 160, 0.5, (2, 4))

    def _pegar(self, ovo):
        ovo.vivo = False
        ovo.tempo_morto = 0.0
        self.som("bater")
        self.particulas.explodir((ovo.x, ovo.y), [CHOCOLATE, CHOCOLATE_CLARO, (230, 200, 160)],
                                 24, 260, 0.9, (3, 7))
        self.textos.adicionar("OVO DE CHOCOLATE!", (ovo.x, ovo.y - 44), BRANCO, 12)
        if self.primeira_morte is None:
            self.primeira_morte = self.tempo_round

    def _morte_subita(self, dt):
        self.relogio_subita -= dt
        while self.relogio_subita <= 0 and self.indice_subita < len(ESPIRAL):
            cel = ESPIRAL[self.indice_subita]
            self.indice_subita += 1
            if self.grade[cel[1]][cel[0]] == PILAR:
                continue
            self.relogio_subita += INTERVALO_MORTE_SUBITA
            self.grade[cel[1]][cel[0]] = PILAR
            self.itens.pop(cel, None)
            self.fogo.pop(cel, None)
            self.bombas = [b for b in self.bombas if b.cel != cel]
            self.queda.append([cel, 0.0])
            self.som("bater", 0.4)
            for ovo in self.ovos:
                if ovo.vivo and ovo.cel == cel:
                    self._pegar(ovo)

    def _proximas_subita(self, n):
        cels = []
        k = self.indice_subita
        while k < len(ESPIRAL) and len(cels) < n:
            c, l = ESPIRAL[k]
            if self.grade[l][c] != PILAR:
                cels.append((c, l))
            k += 1
        return cels

    def _checar_round(self, dt):
        vivos = [o for o in self.ovos if o.vivo]
        if self.fase == "jogo":
            if len(vivos) < 2 and self.tempo_round - self.primeira_morte >= 0.25:
                self.fase = "fim_round"
                self.tempo_fase = 0.0
                self.rounds_jogados += 1
                if len(vivos) == 1:
                    v = vivos[0].i
                    self.vencedor_round = v
                    self.vitorias_round[v] += 1
                    self.som("acerto")
                    self.particulas.explodir((vivos[0].x, vivos[0].y), CONFETE, 30, 300)
                else:
                    self.vencedor_round = None
                    self.som("erro")
        elif self.fase == "fim_round" and self.tempo_fase >= TEMPO_FIM_ROUND:
            precisa = self.modo[0]
            placar = self.vitorias_round
            if max(placar) >= precisa:
                v = 0 if placar[0] > placar[1] else 1
                self.terminar_multi(v, [f"ROUNDS: {placar[0]} × {placar[1]}"])
            else:
                self.round += 1
                self.particulas.limpar()
                self._montar_round()

    # --------------------------------------------------------
    # DESENHO
    # --------------------------------------------------------

    def desenhar_jogo(self, tela):
        t = self.tempo
        caindo = {q[0]: q[1] for q in self.queda}
        tela.blit(self._camada_grade(caindo), (0, 0))

        # Pilares da morte súbita caindo do céu
        pilar = _pilar_sup()
        for (c, l), k in caindo.items():
            dy = -int((1 - min(1.0, k / 0.2)) * 60)
            tela.blit(pilar, (X0 + c * CEL, Y0 + l * CEL + dy))

        # Morte súbita: sombra piscando onde o próximo pilar vai cair
        if self.morte_subita and self.fase == "jogo":
            for cel in self._proximas_subita(2):
                if int(self.tempo * 10) % 2 == 0:
                    r = pygame.Rect(X0 + cel[0] * CEL + 4, Y0 + cel[1] * CEL + 4, CEL - 8, CEL - 8)
                    pygame.draw.rect(tela, (230, 70, 70), r, 4, border_radius=8)

        # Itens flutuando
        for (c, l), tipo in self.itens.items():
            x, y = _centro((c, l))
            s = _item_sup(tipo)
            pygame.draw.ellipse(tela, (80, 150, 70), (x - 14, y + 14, 28, 8))
            tela.blit(s, s.get_rect(center=(x, y - 2 + math.sin(t * 4 + c) * 3)))

        self._desenhar_fogo(tela)

        # Bombas e ovos, de cima para baixo
        objetos = [(b.y, 0, b) for b in self.bombas] + [(o.y, 1, o) for o in self.ovos]
        objetos.sort(key=lambda x: (x[0], x[1]))
        for _, tipo, obj in objetos:
            if tipo == 0:
                self._desenhar_bomba(tela, obj)
            else:
                self._desenhar_ovo(tela, obj)

        self.particulas.desenhar(tela)
        self.textos.desenhar(tela)

        if self.estado == "jogando":
            self._desenhar_avisos(tela)

    def _camada_grade(self, caindo):
        """Fundo + caixas + pilares parados, redesenhado só quando a grade muda."""
        assinatura = (tuple(tuple(linha) for linha in self.grade), tuple(sorted(caindo)))
        if getattr(self, "_assinatura", None) != assinatura or self._camada is None:
            self._assinatura = assinatura
            camada = getattr(self, "_camada", None)
            if camada is None:
                camada = self._camada = pygame.Surface((LARGURA, ALTURA)).convert()
            camada.blit(self.fundo(self.jogador), (0, 0))
            caixa = _caixa_sup()
            pilar = _pilar_sup()
            for l in range(LINHAS):
                for c in range(COLS):
                    g = self.grade[l][c]
                    if g == CAIXA:
                        camada.blit(caixa, (X0 + c * CEL, Y0 + l * CEL))
                    elif g == PILAR and (c % 2 == 0 or l % 2 == 0) and (c, l) not in caindo:
                        camada.blit(pilar, (X0 + c * CEL, Y0 + l * CEL))
        return self._camada

    def _desenhar_bomba(self, tela, b):
        pulso = 1.0 + 0.06 * (1 + math.sin(b.fase))
        s = _bomba_sup(self.cor(b.dono))
        w, h = s.get_size()
        s = pygame.transform.smoothscale(s, (int(w * pulso), int(h * pulso)))
        pygame.draw.ellipse(tela, (70, 140, 60), (b.x - 18, b.y + 14, 36, 10))
        r = s.get_rect(midbottom=(round(b.x), round(b.y + 22)))
        tela.blit(s, r)
        # Pavio com faísca
        topo = (r.centerx, r.top + 6)
        ponta = (topo[0] + 6, topo[1] - 10)
        pygame.draw.line(tela, (90, 60, 40), topo, ponta, 3)
        brilho = 3 + int(abs(math.sin(b.fase * 2)) * 3)
        pygame.draw.circle(tela, (255, 150, 40), ponta, brilho + 2)
        pygame.draw.circle(tela, (255, 240, 150), ponta, brilho)

    def _desenhar_fogo(self, tela):
        for (c, l), (tempo, partes, total) in self.fogo.items():
            x, y = _centro((c, l))
            k = tempo / total
            grosso = int(24 * (0.55 + 0.45 * k))
            flash = k > 0.85
            for cor, fator in ((CHOCOLATE, 1.0), ((240, 200, 150), 0.68), ((255, 255, 255), 0.34)):
                g = max(2, int(grosso * fator))
                if flash:
                    cor = (255, 255, 255)
                pygame.draw.circle(tela, cor, (int(x), int(y)), g + (4 if not partes else 0))
                # Braços: do centro até a borda da célula
                meia = CEL // 2 + 1
                for dx, dy in partes:
                    if dx:
                        r = pygame.Rect(x if dx > 0 else x - meia, y - g, meia, g * 2)
                    else:
                        r = pygame.Rect(x - g, y if dy > 0 else y - meia, g * 2, meia)
                    pygame.draw.rect(tela, cor, r)
            # Confete espalhado no fogo
            rnd = (c * 7 + l * 13 + int(self.tempo * 10)) % len(CONFETE)
            pygame.draw.circle(tela, CONFETE[rnd], (int(x - 10), int(y + 8)), 3)
            pygame.draw.circle(tela, CONFETE[(rnd + 2) % len(CONFETE)], (int(x + 9), int(y - 7)), 3)

    def _desenhar_ovo(self, tela, ovo):
        x, y = ovo.x, ovo.y
        pygame.draw.ellipse(tela, (70, 140, 60), (x - 18, y + 16, 36, 10))
        espelhar = ovo.olhando[0] < 0 if ovo.olhando[0] else (ovo.i == 1)

        if not ovo.vivo:
            sup = self._ovo_chocolate(ovo.i, espelhar)
            k = min(1.0, ovo.tempo_morto * 3)
            ang = math.sin(ovo.tempo_morto * 12) * 10 * (1 - k)
            if ang:
                sup = pygame.transform.rotate(sup, ang)
            tela.blit(sup, sup.get_rect(center=(round(x), round(y - ALTURA_OVO * 0.08))))
            return

        ang = math.sin(ovo.passos * 0.12) * 9 if ovo.andando else 0.0
        pulo = abs(math.sin(ovo.passos * 0.12)) * 3 if ovo.andando else 0.0
        self.desenhar_ovo(tela, ovo.i, (x, y - 4 - pulo), ALTURA_OVO, espelhar, ang)

    def _ovo_chocolate(self, i, espelhar):
        """O avatar coberto de chocolate com gotas escorrendo."""
        cache = getattr(self, "_cache_choc", None)
        if cache is None:
            cache = self._cache_choc = {}
        chave = (self.aparencia(i), espelhar)
        s = cache.get(chave)
        if s is None:
            base = self.jogador.avatar(ALTURA_OVO, self.aparencia(i))
            if espelhar:
                base = pygame.transform.flip(base, True, False)
            # Silhueta de chocolate por cima (o rosto ainda aparece um pouco)
            choc = base.copy()
            choc.fill((0, 0, 0), special_flags=pygame.BLEND_RGB_MULT)
            choc.fill((125, 72, 36), special_flags=pygame.BLEND_RGB_ADD)
            choc.set_alpha(185)
            s = base.copy()
            s.blit(choc, (0, 0))
            w, h = s.get_size()
            # Cobertura no topo e gotas escorrendo
            topo = pygame.Rect(0, 0, int(w * 0.62), int(h * 0.3))
            topo.midtop = (w // 2, int(h * 0.12))
            pygame.draw.ellipse(s, CHOCOLATE, topo)
            rnd = random.Random(i + 5)
            for k in range(5):
                gx = topo.x + 6 + k * (topo.w - 12) // 4
                comp = rnd.randint(int(h * 0.12), int(h * 0.3))
                pygame.draw.line(s, CHOCOLATE, (gx, topo.centery), (gx, topo.centery + comp), 5)
                pygame.draw.circle(s, CHOCOLATE, (gx, topo.centery + comp), 4)
            pygame.draw.ellipse(s, CHOCOLATE_CLARO, (topo.x + 6, topo.y + 4, topo.w // 3, topo.h // 3))
            cache[chave] = s
        return s

    def _desenhar_avisos(self, tela):
        cx = AREA.centerx
        if self.fase == "anuncio":
            k = min(1.0, self.tempo_fase * 4)
            tam = 24 if k < 1 else 32
            painel = pygame.Rect(0, 0, 420, 90)
            painel.center = (cx, AREA.centery)
            ui.painel(tela, painel, (20, 24, 40), AMARELO, 16, 3)
            ui.desenhar_texto(tela, f"ROUND {self.round}!", (cx, painel.centery - 10), tam, AMARELO, "center")
            precisa = self.modo[0]
            ui.desenhar_texto(tela, f"QUEM FIZER {precisa} VENCE", (cx, painel.centery + 26), 10,
                              BRANCO, "center")
        elif self.fase == "fim_round":
            painel = pygame.Rect(0, 0, 560, 90)
            painel.center = (cx, AREA.centery)
            ui.painel(tela, painel, (20, 24, 40), AMARELO, 16, 3)
            if self.vencedor_round is None:
                ui.desenhar_texto(tela, "EMPATE! DE NOVO!", (cx, painel.centery - 10), 20, AMARELO, "center")
            else:
                v = self.vencedor_round
                ui.desenhar_texto(tela, f"{self.nome(v)[:12]} VENCEU O ROUND!", (cx, painel.centery - 10),
                                  16, CORES_JOGADOR[v], "center")
            ui.desenhar_texto(tela, f"{self.vitorias_round[0]} × {self.vitorias_round[1]}",
                              (cx, painel.centery + 24), 16, BRANCO, "center")
        elif self.morte_subita and self.tempo_round < TEMPO_MORTE_SUBITA + 3 and int(self.tempo * 3) % 2 == 0:
            painel = pygame.Rect(0, 0, 330, 56)
            painel.center = (cx, AREA.centery)
            ui.painel(tela, painel, (20, 24, 40), (255, 120, 120), 14, 3)
            ui.desenhar_texto(tela, "MORTE SÚBITA!", painel.center, 20, (255, 120, 120), "center")

    def desenhar_hud(self, tela):
        precisa = self.modo[0]
        for i in (0, 1):
            ovo = self.ovos[i]
            caixa = pygame.Rect(0, 12, 330, 60)
            if i == 0:
                caixa.x = 12
            else:
                caixa.right = LARGURA - 76
            ui.painel(tela, caixa, (20, 24, 40), CORES_JOGADOR[i], 12, 3, sombra=False)
            icone = (caixa.x + 30, caixa.centery) if i == 0 else (caixa.right - 30, caixa.centery)
            self.desenhar_ovo(tela, i, icone, 34, espelhar=(i == 1))
            nome = self.nome(i)[:12]
            nx = caixa.x + 58 if i == 0 else caixa.right - 58
            ancora = "topleft" if i == 0 else "topright"
            ui.desenhar_texto(tela, nome, (nx, caixa.y + 10), 12, CORES_JOGADOR[i], ancora)

            # Vitórias (bolinhas)
            for k in range(precisa):
                bx = nx + 8 + k * 20 if i == 0 else nx - 8 - k * 20
                cor = AMARELO if k < self.vitorias_round[i] else (60, 64, 90)
                pygame.draw.circle(tela, cor, (bx, caixa.y + 42), 7)
                pygame.draw.circle(tela, BRANCO, (bx, caixa.y + 42), 7, 2)

            # Poderes: bombas, fogo, velocidade, chute
            stats = [("bomba", ovo.bombas), ("fogo", ovo.alcance)]
            if ovo.vel > VEL_INICIAL:
                stats.append(("tenis", (ovo.vel - VEL_INICIAL) // 30))
            if ovo.chute:
                stats.append(("chute", None))
            for k, (tipo, n) in enumerate(stats):
                sx = caixa.x + 150 + k * 44 if i == 0 else caixa.right - 150 - k * 44
                s = _icone_hud(tipo)
                tela.blit(s, s.get_rect(center=(sx, caixa.y + 42)))
                if n is not None:
                    ui.desenhar_texto(tela, str(n), (sx + 12, caixa.y + 44), 10, BRANCO, "midleft")

        # Relógio no meio
        caixa = pygame.Rect(0, 12, 150, 60)
        caixa.centerx = (12 + 330 + LARGURA - 76 - 330) // 2
        ui.painel(tela, caixa, (20, 24, 40), BRANCO, 12, 3, sombra=False)
        if self.morte_subita:
            ui.desenhar_texto(tela, "MORTE", (caixa.centerx, caixa.centery - 9), 12, (255, 120, 120), "center")
            ui.desenhar_texto(tela, "SÚBITA!", (caixa.centerx, caixa.centery + 11), 12, (255, 120, 120), "center")
        else:
            resta = max(0, math.ceil(TEMPO_MORTE_SUBITA - self.tempo_round))
            cor = (255, 150, 150) if resta <= 10 else BRANCO
            ui.desenhar_texto(tela, f"{resta // 60}:{resta % 60:02d}", (caixa.centerx, caixa.centery - 8),
                              16, cor, "center")
            ui.desenhar_texto(tela, f"ROUND {self.round}", (caixa.centerx, caixa.centery + 16), 10,
                              (180, 200, 255), "center")
