import math
import random
from collections import deque

import pygame

from settings import *
from core import ui
from core.idioma import t
from jogos.base import MiniJogo

# ============================================================
# CAMPO MINADO DO OVO
# ============================================================
# Um campo de grama esconde vários OVOS-BOMBA (o seu ovo com um
# pavio aceso na cabeça!). Os números contam quantos ovos-bomba
# estão encostados naquela casinha. Abra todas as casas seguras
# no menor tempo possível.

NIVEIS = [
    (9, 9, 10),         # FÁCIL:   linhas, colunas, minas
    (16, 16, 40),       # MÉDIO
    (16, 30, 99),       # DIFÍCIL
]

AREA_TOPO = 78          # área livre abaixo do HUD
AREA_BASE = 708
MOLDURA = 14            # espessura da cerca em volta do tabuleiro
CEL_MAX = 56

DUR_ABRIR = 0.16        # animação da casinha abrindo
ATRASO_ONDA = 0.022     # atraso por "passo" da onda do flood fill
ATRASO_MAX = 0.6

ESPERA_EXPLOSAO = 0.5   # tempo antes das outras minas aparecerem
ESPERA_FIM = 1.3
DUR_VITORIA = 2.4

VIZINHOS = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]

# Cores clássicas dos números
CORES_NUMEROS = {
    1: (30, 70, 225),
    2: (20, 125, 40),
    3: (215, 35, 35),
    4: (70, 20, 140),
    5: (140, 60, 20),
    6: (0, 140, 150),
    7: (15, 15, 15),
    8: (105, 105, 112),
}

GRAMAS = [(118, 198, 72), (106, 186, 62)]
TERRAS = [(234, 212, 168), (224, 200, 154)]

TECLAS = {
    pygame.K_UP: (0, -1), pygame.K_w: (0, -1),
    pygame.K_DOWN: (0, 1), pygame.K_s: (0, 1),
    pygame.K_LEFT: (-1, 0), pygame.K_a: (-1, 0),
    pygame.K_RIGHT: (1, 0), pygame.K_d: (1, 0),
}


def _geometria(opcao):
    """Tamanho da célula e canto do tabuleiro para cada dificuldade."""
    linhas, cols, _ = NIVEIS[opcao]
    altura_util = AREA_BASE - AREA_TOPO - 2 * MOLDURA
    cel = min(CEL_MAX, (LARGURA - 40 - 2 * MOLDURA) // cols, altura_util // linhas)
    x0 = (LARGURA - cols * cel) // 2
    y0 = AREA_TOPO + MOLDURA + (altura_util - linhas * cel) // 2
    return cel, x0, y0


def _formatar_tempo(seg):
    seg = max(0, int(seg))
    return f"{seg // 60}:{seg % 60:02d}"


# ============================================================
# SPRITES (desenhados uma vez para cada tamanho de célula)
# ============================================================

def _bloco_grama(cel, cor, semente):
    """Casinha fechada: um bloquinho de grama elevado."""
    sup = pygame.Surface((cel, cel))
    borda = max(2, cel // 12)
    sup.fill(ui.escurecer(cor, 70))
    pygame.draw.rect(sup, cor, (1, 1, cel - 2, cel - 2))

    # Brilho em cima/esquerda e sombra embaixo/direita (efeito 3D)
    claro = ui.clarear(cor, 55)
    escuro = ui.escurecer(cor, 45)
    pygame.draw.rect(sup, claro, (1, 1, cel - 2, borda))
    pygame.draw.rect(sup, claro, (1, 1, borda, cel - 2))
    pygame.draw.rect(sup, escuro, (1, cel - 1 - borda, cel - 2, borda))
    pygame.draw.rect(sup, escuro, (cel - 1 - borda, 1, borda, cel - 2))

    # Tufinhos de grama
    rnd = random.Random(semente)
    tufo = ui.escurecer(cor, 28)
    for _ in range(3):
        x = rnd.randint(borda + 3, cel - borda - 4)
        y = rnd.randint(borda + 5, cel - borda - 3)
        alt = max(2, cel // 9)
        pygame.draw.line(sup, tufo, (x, y), (x - 2, y - alt), 1)
        pygame.draw.line(sup, tufo, (x, y), (x + 1, y - alt - 1), 1)
    return sup


def _terra(cel, cor):
    """Casinha aberta: terra clarinha, um pouco afundada."""
    sup = pygame.Surface((cel, cel))
    sup.fill(cor)
    sombra = ui.escurecer(cor, 34)
    pygame.draw.line(sup, sombra, (0, 0), (cel - 1, 0), 2)
    pygame.draw.line(sup, sombra, (0, 0), (0, cel - 1), 2)
    pygame.draw.rect(sup, ui.escurecer(cor, 18), (0, 0, cel, cel), 1)
    return sup


def _bandeira(cel, jogador):
    """Bandeirinha na cor do ovo do jogador, com mastro."""
    sup = pygame.Surface((cel, cel), pygame.SRCALPHA)
    mx = int(cel * 0.36)
    topo = int(cel * 0.18)
    base = int(cel * 0.8)
    grossura = max(2, cel // 14)

    # Montinho de terra na base
    pygame.draw.ellipse(sup, (110, 80, 50), (mx - cel * 0.2, base - cel * 0.06,
                                             cel * 0.44, cel * 0.14))
    # Mastro
    pygame.draw.line(sup, (70, 50, 35), (mx, topo), (mx, base), grossura)

    # Tecido
    pontos = [(mx + 1, topo), (mx + cel * 0.44, topo + cel * 0.15), (mx + 1, topo + cel * 0.32)]
    pygame.draw.polygon(sup, jogador.cor, pontos)
    pygame.draw.polygon(sup, jogador.cor_contorno, pontos, max(1, cel // 20))
    pygame.draw.circle(sup, (240, 210, 80), (mx, topo), max(2, cel // 14))
    return sup


def _mina(cel, jogador):
    """
    O OVO-BOMBA: o avatar do jogador com um pavio saindo da cabeça.
    Devolve (surface, ponta_do_pavio).
    """
    sup = pygame.Surface((cel, cel), pygame.SRCALPHA)
    jogador.desenhar(sup, (cel * 0.48, cel * 0.6), cel * 0.58)

    # Pavio em curva
    pontos = [(cel * 0.52, cel * 0.33), (cel * 0.58, cel * 0.22),
              (cel * 0.67, cel * 0.16), (cel * 0.75, cel * 0.09)]
    grossura = max(2, cel // 14)
    pygame.draw.lines(sup, (60, 45, 30), False, pontos, grossura + 2)
    pygame.draw.lines(sup, (170, 140, 100), False, pontos, grossura)
    ponta = (cel * 0.77, cel * 0.08)
    return sup, ponta


def _faisca(tela, pos, raio, tempo, fase=0.0):
    """Faisquinha animada na ponta do pavio."""
    pisca = 0.75 + 0.35 * math.sin(tempo * 25 + fase)
    r = max(3, raio * pisca)
    pygame.draw.circle(tela, (255, 140, 30), (int(pos[0]), int(pos[1])), int(r * 0.8))
    ui.estrela(tela, pos, r, (255, 230, 90), tempo * 6 + fase)
    pygame.draw.circle(tela, BRANCO, (int(pos[0]), int(pos[1])), max(1, int(r * 0.3)))


class CampoMinado(MiniJogo):

    ID = "minado"
    TITULO = "CAMPO MINADO"
    TITULO_CURTO = "MINADO"
    DESCRICAO = "Ovos-bomba escondidos na grama! Use os números para abrir o campo sem explodir."
    COR = (200, 110, 50)
    INSTRUCOES = [
        "Abra a grama sem achar um OVO-BOMBA!",
        "O número conta os ovos-bomba encostados nele.",
        "Marque os ovos-bomba com a sua bandeirinha.",
        "Número com as bandeiras certas? Clique: abre tudo!",
        "MOUSE esq./dir. ou SETAS + ESPAÇO + F",
    ]
    OPCOES = ["FÁCIL", "MÉDIO", "DIFÍCIL"]
    MENOR_MELHOR = True
    MOEDAS_MIN = 2

    def calcular_moedas(self, valor, venceu):
        """Vencer vale 8 / 18 / 30 conforme a dificuldade."""
        return (8, 18, 30)[self.opcao] if venceu else self.MOEDAS_MIN
    ROTULO_PONTOS = "TEMPO"
    CONTAGEM = False

    _sprites = {}
    _fundos_tab = {}

    @classmethod
    def formatar(cls, valor):
        return _formatar_tempo(valor)

    # --------------------------------------------------------
    # CENÁRIO: fazenda com colinas
    # --------------------------------------------------------

    @classmethod
    def criar_fundo(cls, jogador):
        sup = ui.gradiente(LARGURA, ALTURA, (110, 180, 245), (200, 232, 255))
        rnd = random.Random(7)

        # Sol
        pygame.draw.circle(sup, (255, 240, 170), (170, 120), 62)
        pygame.draw.circle(sup, (255, 222, 90), (170, 120), 48)

        # Nuvens
        for cx, cy, esc in ((420, 90, 1.0), (700, 150, 0.8), (900, 70, 0.7), (80, 260, 0.6)):
            for dx, dy, r in ((-40, 6, 26), (-12, -8, 34), (22, -2, 30), (48, 8, 22), (0, 14, 26)):
                pygame.draw.circle(sup, (250, 252, 255),
                                   (int(cx + dx * esc), int(cy + dy * esc)), int(r * esc))

        # Colinas distantes e próximas
        for cx, cy, rx, ry in ((120, 420, 360, 170), (560, 440, 420, 180), (980, 410, 330, 170)):
            pygame.draw.ellipse(sup, (128, 190, 120), (cx - rx, cy - ry, rx * 2, ry * 2))
        for cx, cy, rx, ry in ((300, 500, 420, 170), (840, 510, 400, 170)):
            pygame.draw.ellipse(sup, (104, 176, 86), (cx - rx, cy - ry, rx * 2, ry * 2))

        # Celeiro na colina
        cx, cy = 880, 330
        pygame.draw.rect(sup, (190, 50, 45), (cx - 46, cy - 40, 92, 70))
        pygame.draw.polygon(sup, (140, 40, 38), [(cx - 56, cy - 38), (cx, cy - 86), (cx + 56, cy - 38)])
        pygame.draw.rect(sup, (250, 240, 230), (cx - 18, cy - 4, 36, 34))
        pygame.draw.line(sup, (190, 50, 45), (cx - 18, cy - 4), (cx + 18, cy + 30), 3)
        pygame.draw.line(sup, (190, 50, 45), (cx + 18, cy - 4), (cx - 18, cy + 30), 3)

        # Chão de grama
        chao = ui.gradiente(LARGURA, ALTURA - 440, (92, 170, 68), (62, 132, 50))
        sup.blit(chao, (0, 440))
        pygame.draw.ellipse(sup, (92, 170, 68), (-200, 400, LARGURA + 400, 90))

        # Cerquinha no horizonte
        for x in range(-10, LARGURA + 20, 34):
            pygame.draw.rect(sup, (235, 225, 205), (x, 404, 8, 34))
            pygame.draw.polygon(sup, (235, 225, 205), [(x, 404), (x + 4, 398), (x + 8, 404)])
        pygame.draw.rect(sup, (220, 208, 186), (0, 412, LARGURA, 6))
        pygame.draw.rect(sup, (220, 208, 186), (0, 426, LARGURA, 6))

        # Tufos e flores
        for _ in range(420):
            x, y = rnd.randrange(LARGURA), rnd.randrange(450, ALTURA)
            pygame.draw.line(sup, (50, 118, 44), (x, y), (x + rnd.randint(-2, 2), y - 7), 2)
        for _ in range(55):
            x, y = rnd.randrange(LARGURA), rnd.randrange(460, ALTURA)
            cor = rnd.choice([(255, 120, 150), (255, 230, 90), (255, 255, 255), (170, 130, 255)])
            for dx, dy in ((-3, 0), (3, 0), (0, -3), (0, 3)):
                pygame.draw.circle(sup, cor, (x + dx, y + dy), 3)
            pygame.draw.circle(sup, (255, 200, 40), (x, y), 2)
        return sup

    @classmethod
    def _fundo_tabuleiro(cls, jogador, opcao):
        """Cenário + cerca de madeira em volta do tabuleiro (cacheado)."""
        chave = (opcao, jogador.aparencia())
        sup = cls._fundos_tab.get(chave)
        if sup is not None:
            return sup

        sup = cls.fundo(jogador).copy()
        linhas, cols, _ = NIVEIS[opcao]
        cel, x0, y0 = _geometria(opcao)
        tab = pygame.Rect(x0, y0, cols * cel, linhas * cel)
        cerca = tab.inflate(MOLDURA * 2, MOLDURA * 2)

        # Sombra no chão
        sombra = pygame.Surface(cerca.inflate(16, 16).size, pygame.SRCALPHA)
        pygame.draw.rect(sombra, (0, 0, 0, 90), sombra.get_rect(), border_radius=16)
        sup.blit(sombra, (cerca.x - 2, cerca.y + 4))

        # Moldura de madeira
        pygame.draw.rect(sup, (126, 80, 42), cerca, border_radius=10)
        pygame.draw.rect(sup, (168, 112, 64), cerca.inflate(-4, -4), 3, border_radius=9)
        pygame.draw.rect(sup, (84, 52, 28), cerca, 3, border_radius=10)
        for x in range(cerca.left + 20, cerca.right - 10, 70):
            pygame.draw.rect(sup, (96, 58, 30), (x - 6, cerca.top - 6, 12, 16), border_radius=3)
            pygame.draw.rect(sup, (96, 58, 30), (x - 6, cerca.bottom - 10, 12, 16), border_radius=3)
            pygame.draw.rect(sup, (186, 126, 76), (x - 4, cerca.top - 4, 8, 4), border_radius=2)
        pygame.draw.rect(sup, (60, 40, 22), tab.inflate(4, 4))

        sup = sup.convert()
        cls._fundos_tab[chave] = sup
        return sup

    @classmethod
    def _criar_sprites(cls, cel, jogador):
        chave = (cel, jogador.aparencia())
        s = cls._sprites.get(chave)
        if s is not None:
            return s

        s = {}
        for i in range(2):
            s["fechada", i] = _bloco_grama(cel, GRAMAS[i], 11 + i)
            s["fechada_hover", i] = _bloco_grama(cel, ui.clarear(GRAMAS[i], 30), 11 + i)
            s["aberta", i] = _terra(cel, TERRAS[i])
        s["explodida"] = _terra(cel, (235, 84, 64))
        s["bandeira"] = _bandeira(cel, jogador)
        s["mina"], s["ponta"] = _mina(cel, jogador)
        s["mina_hud"], s["ponta_hud"] = _mina(40, jogador)
        s["numero"] = 24 if cel >= 48 else (20 if cel >= 34 else 16)

        if len(cls._sprites) > 12:
            cls._sprites.clear()
        cls._sprites[chave] = s
        return s

    @classmethod
    def desenhar_icone(cls, sup, jogador):
        w, h = sup.get_size()
        cel = max(16, h // 5)
        cols, linhas = 5, 3
        x0 = w // 2 - cols * cel // 2
        y0 = h // 2 - linhas * cel // 2 + cel // 3
        s = cls._criar_sprites(cel, jogador)
        pygame.draw.rect(sup, (84, 52, 28), (x0 - 4, y0 - 4, cols * cel + 8, linhas * cel + 8),
                         border_radius=4)
        abertas = {(0, 2): 1, (1, 2): 1, (2, 2): 2, (0, 1): 1, (1, 1): 0}
        for c in range(cols):
            for l in range(linhas):
                pos = (x0 + c * cel, y0 + l * cel)
                if (c, l) in abertas:
                    sup.blit(s["aberta", (c + l) % 2], pos)
                    n = abertas[(c, l)]
                    if n:
                        ui.desenhar_texto(sup, str(n), (pos[0] + cel // 2 + 1, pos[1] + cel // 2 + 1),
                                          max(8, cel // 2), CORES_NUMEROS[n], "center", False)
                else:
                    sup.blit(s["fechada", (c + l) % 2], pos)
        sup.blit(s["bandeira"], (x0 + 4 * cel, y0 + 1 * cel))

        # Ovo-bomba grande na frente
        tam = int(h * 0.5)
        mina, ponta = _mina(tam, jogador)
        mx, my = x0 + 3 * cel - tam // 2, y0 + cel - tam // 2 - 4
        sup.blit(mina, (mx, my))
        _faisca(sup, (mx + ponta[0], my + ponta[1]), max(4, tam // 9), 0.3)

    # --------------------------------------------------------
    # PARTIDA
    # --------------------------------------------------------

    def reiniciar(self):
        self.linhas, self.cols, self.qtd_minas = NIVEIS[self.opcao]
        self.cel, self.x0, self.y0 = _geometria(self.opcao)
        self.sprites = self._criar_sprites(self.cel, self.jogador)
        self._fundo_tab = self._fundo_tabuleiro(self.jogador, self.opcao)

        self.minas = set()
        self.numeros = [[0] * self.cols for _ in range(self.linhas)]
        self.aberta = [[False] * self.cols for _ in range(self.linhas)]
        self.bandeira = [[False] * self.cols for _ in range(self.linhas)]
        self.t_abre = [[None] * self.cols for _ in range(self.linhas)]
        self.qtd_abertas = 0
        self.qtd_bandeiras = 0

        self.gerado = False             # minas só nascem depois do 1º clique
        self.cronometro = 0.0
        self.fase = "jogando"           # jogando / explodiu / venceu
        self.t_fase = 0.0
        self.mina_explodida = None
        self.fila_minas = []            # minas que vão aparecendo ao perder
        self.intervalo_minas = 0.05
        self.minas_mostradas = {}       # célula -> instante em que apareceu
        self.mostrar_erros = False
        self.proximo_confete = 0.0
        self.sons_pendentes = []        # "tique" da onda de abertura

        self.cursor = [self.cols // 2, self.linhas // 2]
        self.teclado = False
        self.mouse = (-100, -100)

    def _gerar_minas(self, seguro):
        """Sorteia as minas longe do primeiro clique (célula + 8 vizinhas)."""
        proibidas = {seguro} | set(self._vizinhos(seguro))
        livres = [(c, l) for l in range(self.linhas) for c in range(self.cols)
                  if (c, l) not in proibidas]
        self.minas = set(random.sample(livres, min(self.qtd_minas, len(livres))))
        for l in range(self.linhas):
            for c in range(self.cols):
                self.numeros[l][c] = sum(1 for v in self._vizinhos((c, l)) if v in self.minas)
        self.gerado = True

    def _vizinhos(self, cel):
        c, l = cel
        for dc, dl in VIZINHOS:
            nc, nl = c + dc, l + dl
            if 0 <= nc < self.cols and 0 <= nl < self.linhas:
                yield (nc, nl)

    def _celula_em(self, pos):
        c = (pos[0] - self.x0) // self.cel
        l = (pos[1] - self.y0) // self.cel
        if 0 <= c < self.cols and 0 <= l < self.linhas:
            return (int(c), int(l))
        return None

    def _centro(self, cel):
        return (self.x0 + cel[0] * self.cel + self.cel / 2,
                self.y0 + cel[1] * self.cel + self.cel / 2)

    # --------------------------------------------------------
    # AÇÕES
    # --------------------------------------------------------

    def evento_jogo(self, e):
        if self.fase != "jogando":
            return

        if e.type == pygame.MOUSEMOTION:
            self.mouse = e.pos
            self.teclado = False

        elif e.type == pygame.MOUSEBUTTONDOWN and e.button in (1, 2, 3):
            self.mouse = e.pos
            self.teclado = False
            cel = self._celula_em(e.pos)
            if cel is None:
                return
            self.cursor = list(cel)
            if e.button == 1:
                self._acao_revelar(cel)
            elif e.button == 2:
                self._acao_abrir_volta(cel)
            else:
                self._acao_bandeira(cel)

        elif e.type == pygame.KEYDOWN:
            if e.key in TECLAS:
                dc, dl = TECLAS[e.key]
                if self.teclado:
                    self.cursor[0] = max(0, min(self.cols - 1, self.cursor[0] + dc))
                    self.cursor[1] = max(0, min(self.linhas - 1, self.cursor[1] + dl))
                self.teclado = True
            elif e.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER):
                self.teclado = True
                self._acao_revelar(tuple(self.cursor))
            elif e.key == pygame.K_f:
                self.teclado = True
                self._acao_bandeira(tuple(self.cursor))

    def _acao_revelar(self, cel):
        c, l = cel
        if self.aberta[l][c]:
            self._acao_abrir_volta(cel)
            return
        if self.bandeira[l][c]:
            return
        if not self.gerado:
            self._gerar_minas(cel)
        self._abrir([cel])

    def _acao_abrir_volta(self, cel):
        """"Chord": número com as bandeiras certas abre os vizinhos."""
        c, l = cel
        n = self.numeros[l][c]
        if not self.aberta[l][c] or n == 0:
            return
        viz = list(self._vizinhos(cel))
        bandeiras = sum(1 for (vc, vl) in viz if self.bandeira[vl][vc])
        if bandeiras != n:
            return
        fechadas = [(vc, vl) for (vc, vl) in viz
                    if not self.aberta[vl][vc] and not self.bandeira[vl][vc]]
        if fechadas:
            self._abrir(fechadas)

    def _acao_bandeira(self, cel):
        c, l = cel
        if self.aberta[l][c]:
            return
        self.bandeira[l][c] = not self.bandeira[l][c]
        self.qtd_bandeiras += 1 if self.bandeira[l][c] else -1
        self.som("bandeira", 0.7)
        if self.bandeira[l][c]:
            x, y = self._centro(cel)
            self.particulas.explodir((x, y - self.cel * 0.2),
                                     [self.jogador.cor, (120, 200, 80)], 6, 90, 0.4, (2, 3))

    def _abrir(self, celulas):
        """Abre células com flood fill ITERATIVO (fila, sem recursão)."""
        atingida = None
        fila = deque()
        vistos = set()
        for cel in celulas:
            c, l = cel
            if self.aberta[l][c] or self.bandeira[l][c] or cel in vistos:
                continue
            if cel in self.minas:
                atingida = atingida or cel
                continue
            vistos.add(cel)
            fila.append((cel, 0))

        novas = 0
        while fila:
            (c, l), passo = fila.popleft()
            self.aberta[l][c] = True
            self.t_abre[l][c] = self.tempo + min(ATRASO_MAX, passo * ATRASO_ONDA)
            novas += 1
            if self.numeros[l][c] == 0:
                for viz in self._vizinhos((c, l)):
                    vc, vl = viz
                    if viz in vistos or self.aberta[vl][vc] or self.bandeira[vl][vc] \
                            or viz in self.minas:
                        continue
                    vistos.add(viz)
                    fila.append((viz, passo + 1))

        self.qtd_abertas += novas

        if atingida:
            self._explodir(atingida)
            return

        if novas:
            # Um som só por ação; aberturas grandes ganham uns "tiques" baixinhos
            self.som("revelar", 0.6)
            extras = min(4, novas // 10)
            self.sons_pendentes = [self.tempo + 0.08 * (i + 1) for i in range(extras)]
            if novas == 1:
                x, y = self._centro(celulas[0])
                self.particulas.explodir((x, y), [(150, 110, 70), (120, 190, 70)],
                                         5, 80, 0.35, (2, 3))

        if self.qtd_abertas >= self.linhas * self.cols - self.qtd_minas:
            self._vencer()

    # --------------------------------------------------------
    # FIM DA PARTIDA
    # --------------------------------------------------------

    def _explodir(self, cel):
        self.fase = "explodiu"
        self.t_fase = 0.0
        self.mina_explodida = cel
        self.sons_pendentes = []
        self.tremer(0.45)
        self.som("explosao", 0.8)

        x, y = self._centro(cel)
        self.particulas.explodir((x, y), [(255, 200, 60), (255, 120, 30), (230, 60, 40), BRANCO],
                                 40, 340, 0.9)
        self.particulas.explodir((x, y), [(90, 90, 100), (140, 140, 150), (60, 60, 70)],
                                 16, 120, 1.2, (5, 9), -60)
        self.particulas.explodir((x, y), [self.jogador.cor, self.jogador.cor_escura],
                                 14, 260, 0.8)

        # As outras minas aparecem da mais perto para a mais longe
        outras = [m for m in self.minas if m != cel and not self.bandeira[m[1]][m[0]]]
        outras.sort(key=lambda m: (m[0] - cel[0]) ** 2 + (m[1] - cel[1]) ** 2)
        self.fila_minas = outras
        self.intervalo_minas = min(0.08, 1.4 / max(1, len(outras)))
        self.minas_mostradas = {cel: 0.0}

    def _vencer(self):
        self.fase = "venceu"
        self.t_fase = 0.0
        self.proximo_confete = 0.0
        self.som("acerto")
        for (c, l) in self.minas:
            x, y = self._centro((c, l))
            self.particulas.explodir((x, y), [AMARELO, BRANCO, self.jogador.cor], 6, 160, 0.7)

    def _linhas_fim(self):
        seguras = self.linhas * self.cols - self.qtd_minas
        return [t("TEMPO: {n}", n=_formatar_tempo(self.cronometro)),
                t("CASAS ABERTAS: {a}/{b}", a=self.qtd_abertas, b=seguras),
                t("NÍVEL: {n}", n=t(self.OPCOES[self.opcao]))]

    # --------------------------------------------------------
    # LÓGICA
    # --------------------------------------------------------

    def atualizar_jogo(self, dt):
        # Tiques da onda de abertura
        while self.sons_pendentes and self.tempo >= self.sons_pendentes[0]:
            self.sons_pendentes.pop(0)
            self.som("revelar", 0.25)

        if self.fase == "jogando":
            if self.gerado:
                self.cronometro = min(5999.0, self.cronometro + dt)

        elif self.fase == "explodiu":
            self.t_fase += dt
            if self.t_fase >= ESPERA_EXPLOSAO:
                self.mostrar_erros = True
            # Revela as minas uma a uma
            while self.fila_minas:
                i = len(self.minas_mostradas) - 1
                if self.t_fase < ESPERA_EXPLOSAO + i * self.intervalo_minas:
                    break
                m = self.fila_minas.pop(0)
                self.minas_mostradas[m] = self.t_fase
                self.particulas.explodir(self._centro(m), [(150, 110, 70), (200, 170, 120)],
                                         4, 90, 0.35, (2, 3))
                if i % 3 == 0:
                    self.som("revelar", 0.3)
            fim = ESPERA_EXPLOSAO + len(self.minas_mostradas) * self.intervalo_minas + ESPERA_FIM
            if not self.fila_minas and self.t_fase >= fim:
                self.terminar(venceu=False, registrar=False, titulo=t("KABUM!"),
                              linhas=[t("ERA UM OVO-BOMBA!")] + self._linhas_fim()[:2])

        elif self.fase == "venceu":
            self.t_fase += dt
            self.proximo_confete -= dt
            if self.proximo_confete <= 0:
                self.proximo_confete = 0.22
                x = random.uniform(self.x0, self.x0 + self.cols * self.cel)
                y = random.uniform(self.y0, self.y0 + self.linhas * self.cel)
                self.particulas.explodir((x, y), [AMARELO, (255, 120, 150), (120, 200, 255),
                                                  (140, 230, 120), self.jogador.cor],
                                         22, 280, 1.0, (3, 6))
            if self.t_fase >= DUR_VITORIA:
                valor = max(1, int(self.cronometro))
                self.terminar(venceu=True, valor=valor, linhas=self._linhas_fim())

    # --------------------------------------------------------
    # DESENHO
    # --------------------------------------------------------

    def desenhar_jogo(self, tela):
        tela.blit(self._fundo_tab, (0, 0))

        s = self.sprites
        cel = self.cel
        agora = self.tempo
        hover = None
        if self.fase == "jogando" and self.estado == "jogando" and not self.teclado:
            hover = self._celula_em(self.mouse)

        numero_tam = s["numero"]
        minas_anim = []     # desenhadas por cima de tudo (pavio pode passar da célula)

        for l in range(self.linhas):
            y = self.y0 + l * cel
            for c in range(self.cols):
                x = self.x0 + c * cel
                xadrez = (c + l) % 2
                t = self.t_abre[l][c]
                cel_atual = (c, l)

                # ----- célula fechada -----
                if t is None or agora < t:
                    mostrada = cel_atual in self.minas_mostradas
                    if self.fase == "venceu" and cel_atual in self.minas:
                        tela.blit(s["aberta", xadrez], (x, y))
                        minas_anim.append(("feliz", cel_atual))
                        continue
                    if mostrada:
                        fundo = "explodida" if cel_atual == self.mina_explodida else ("aberta", xadrez)
                        tela.blit(s[fundo], (x, y))
                        minas_anim.append(("mina", cel_atual))
                        continue

                    nome = "fechada_hover" if cel_atual == hover else "fechada"
                    tela.blit(s[nome, xadrez], (x, y))
                    if self.bandeira[l][c]:
                        tela.blit(s["bandeira"], (x, y))
                        if self.mostrar_erros and cel_atual not in self.minas:
                            self._desenhar_x(tela, x, y)
                    continue

                # ----- célula aberta -----
                p = (agora - t) / DUR_ABRIR
                tela.blit(s["aberta", xadrez], (x, y))
                n = self.numeros[l][c]
                if n and p >= 0.45:
                    ui.desenhar_texto(tela, str(n), (x + cel // 2 + 1, y + cel // 2 + 1),
                                      numero_tam, CORES_NUMEROS[n], "center", False)
                if p < 1:
                    # Bloco de grama encolhendo e subindo
                    tam = int(cel * (1 - p))
                    if tam > 2:
                        r = pygame.Rect(0, 0, tam, tam)
                        r.center = (x + cel // 2, y + cel // 2 - int(cel * 0.25 * p))
                        pygame.draw.rect(tela, GRAMAS[xadrez], r, border_radius=3)
                        pygame.draw.rect(tela, ui.escurecer(GRAMAS[xadrez], 60), r, 1,
                                         border_radius=3)

        # Ovos-bomba e ovos felizes
        for tipo, m in minas_anim:
            if tipo == "feliz":
                self._desenhar_ovo_feliz(tela, m)
            else:
                self._desenhar_mina(tela, m)

        # Cursor do teclado
        if self.teclado and self.fase == "jogando":
            r = pygame.Rect(self.x0 + self.cursor[0] * cel, self.y0 + self.cursor[1] * cel, cel, cel)
            pulso = int(2 * math.sin(self.tempo * 8))
            pygame.draw.rect(tela, (40, 30, 10), r.inflate(6 + pulso, 6 + pulso), 5, border_radius=6)
            pygame.draw.rect(tela, AMARELO, r.inflate(4 + pulso, 4 + pulso), 3, border_radius=6)

        self.particulas.desenhar(tela)
        self.textos.desenhar(tela)

    def _desenhar_x(self, tela, x, y):
        """Bandeira errada: X vermelho por cima."""
        cel = self.cel
        m = cel // 5
        g = max(3, cel // 9)
        for a, b in (((x + m, y + m), (x + cel - m, y + cel - m)),
                     ((x + cel - m, y + m), (x + m, y + cel - m))):
            pygame.draw.line(tela, (60, 0, 0), a, b, g + 2)
            pygame.draw.line(tela, (240, 40, 40), a, b, g)

    def _desenhar_mina(self, tela, m):
        s = self.sprites
        cel = self.cel
        x = self.x0 + m[0] * cel
        y = self.y0 + m[1] * cel

        if m == self.mina_explodida:
            # O ovo que explodiu fica tonto, com estrelinhas girando
            ang = math.sin(self.tempo * 10) * 14
            cx, cy = x + cel * 0.5, y + cel * 0.58
            self.jogador.desenhar(tela, (cx, cy), cel * 0.58, angulo=ang)
            for i in range(3):
                a = self.tempo * 4 + i * math.tau / 3
                ui.estrela(tela, (cx + math.cos(a) * cel * 0.34, y + cel * 0.16 + math.sin(a) * cel * 0.08),
                           max(3, cel // 9), AMARELO, a)
            return

        # "Pulinho" ao aparecer
        t0 = self.minas_mostradas.get(m, 0.0)
        p = (self.t_fase - t0) / 0.2
        sprite = s["mina"]
        if p < 1:
            esc = max(0.1, p) * (1 + 0.35 * math.sin(math.pi * max(0.0, p)))
            lado = max(2, int(cel * esc))
            sprite = pygame.transform.smoothscale(sprite, (lado, lado))
            tela.blit(sprite, sprite.get_rect(center=(x + cel // 2, y + cel // 2)))
            return

        tela.blit(sprite, (x, y))
        ponta = s["ponta"]
        _faisca(tela, (x + ponta[0], y + ponta[1]), max(3, cel // 8), self.tempo, m[0] + m[1] * 3)

    def _desenhar_ovo_feliz(self, tela, m):
        cel = self.cel
        x, y = self._centro(m)
        fase = (m[0] + m[1]) * 0.45
        dy = -abs(math.sin(self.tempo * 7 + fase)) * cel * 0.3
        self.jogador.desenhar(tela, (x, y + cel * 0.06 + dy), cel * 0.62)

    def desenhar_hud(self, tela):
        s = self.sprites

        # Minas restantes (pode ficar negativo)
        caixa = pygame.Rect(12, 12, 150, 48)
        ui.painel(tela, caixa, (20, 24, 40), BRANCO, 12, 3, sombra=False)
        tela.blit(s["mina_hud"], (caixa.x + 6, caixa.y + 4))
        ponta = s["ponta_hud"]
        _faisca(tela, (caixa.x + 6 + ponta[0], caixa.y + 4 + ponta[1]), 5, self.tempo)
        restam = 0 if self.fase == "venceu" else self.qtd_minas - self.qtd_bandeiras
        rotulo = f"{restam:03d}" if restam >= 0 else str(restam)
        ui.desenhar_texto(tela, rotulo, (caixa.right - 14, caixa.centery + 1), 20,
                          (255, 110, 90) if restam < 0 else AMARELO, "midright")

        # Cronômetro
        caixa2 = pygame.Rect(caixa.right + 12, 12, 150, 48)
        ui.painel(tela, caixa2, (20, 24, 40), BRANCO, 12, 3, sombra=False)
        rc = (caixa2.x + 26, caixa2.centery)
        pygame.draw.circle(tela, BRANCO, rc, 14)
        pygame.draw.circle(tela, (40, 44, 70), rc, 14, 3)
        ang = self.cronometro * math.tau / 60 - math.pi / 2
        pygame.draw.line(tela, (220, 50, 50), rc,
                         (rc[0] + math.cos(ang) * 10, rc[1] + math.sin(ang) * 10), 2)
        pygame.draw.line(tela, (40, 44, 70), rc, (rc[0], rc[1] - 7), 2)
        ui.desenhar_texto(tela, _formatar_tempo(self.cronometro), (caixa2.right - 14, caixa2.centery + 1),
                          20, BRANCO, "midright")

        # Nível e recorde
        caixa3 = pygame.Rect(caixa2.right + 12, 12, 210, 48)
        ui.painel(tela, caixa3, (20, 24, 40), BRANCO, 12, 3, sombra=False)
        x = caixa3.x + 14
        ui.desenhar_texto(tela, t(self.OPCOES[self.opcao]), (x, caixa3.y + 9), 10, (180, 220, 255))
        rec = self.recorde()
        texto_rec = t("RECORDE: {n}", n=self.formatar(rec) if rec is not None else "--")
        ui.desenhar_texto(tela, texto_rec, (x, caixa3.y + 26), 12, AMARELO)
