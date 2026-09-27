import math
import random

import pygame

from settings import *
from core import ui
from core import assets
from jogos.base import MiniJogo

# ============================================================
# MEMÓRIA DA FAMÍLIA OVO
# ============================================================
# As cartas mostram a "família" do seu ovo: primos, tias e avós,
# cada um com uma combinação diferente de cor, cabelo, olhos e
# boca. Um dos pares é VOCÊ! Encontre todos os pares com o menor
# número de jogadas.

NIVEIS = [
    (4, 3),     # FÁCIL:   colunas, linhas  (6 pares)
    (4, 4),     # MÉDIO:   8 pares
    (6, 4),     # DIFÍCIL: 12 pares
]

AREA_TOPO = 76          # área livre abaixo do HUD
AREA_BASE = 704
MESA_PAD = 22           # borda da mesa em volta das cartas
MESA_LARG_MAX = 720     # deixa a janela e a luminária aparecendo
ESPACO = 12             # espaço entre as cartas
ALTURA_MAX = 196
PROPORCAO = 0.76        # largura / altura da carta

DUR_VIRAR = 0.25
ESPERA_ERRO = 0.8
DUR_VITORIA = 2.3

# Cor do "halo" atrás do avatar, contrastando com cada cor de ovo
# (verde, azul, branco, vermelho)
HALOS = [(255, 208, 222), (255, 236, 170), (172, 190, 228), (196, 238, 212)]

TECLAS = {
    pygame.K_UP: (0, -1), pygame.K_w: (0, -1),
    pygame.K_DOWN: (0, 1), pygame.K_s: (0, 1),
    pygame.K_LEFT: (-1, 0), pygame.K_a: (-1, 0),
    pygame.K_RIGHT: (1, 0), pygame.K_d: (1, 0),
}


def _geometria(opcao):
    """Tamanho das cartas e retângulo da mesa para cada dificuldade."""
    cols, linhas = NIVEIS[opcao]
    area_h = AREA_BASE - AREA_TOPO - 2 * MESA_PAD
    area_w = MESA_LARG_MAX - 2 * MESA_PAD
    h = min(ALTURA_MAX, (area_h - (linhas - 1) * ESPACO) // linhas)
    w = min(int(h * PROPORCAO), (area_w - (cols - 1) * ESPACO) // cols)
    h = min(h, int(w / PROPORCAO))
    grade_w = cols * w + (cols - 1) * ESPACO
    grade_h = linhas * h + (linhas - 1) * ESPACO
    x0 = (LARGURA - grade_w) // 2
    y0 = AREA_TOPO + MESA_PAD + (area_h - grade_h) // 2
    mesa = pygame.Rect(x0 - MESA_PAD, y0 - MESA_PAD, grade_w + 2 * MESA_PAD, grade_h + 2 * MESA_PAD)
    return w, h, x0, y0, mesa


def _formatar_tempo(seg):
    seg = max(0, int(seg))
    return f"{seg // 60}:{seg % 60:02d}"


def _diferencas(a, b):
    return sum(1 for x, y in zip(a, b) if x != y)


# ============================================================
# CARTAS (desenhadas uma vez para cada tamanho)
# ============================================================

def _verso(w, h, jogador):
    """Verso da carta: ovinhos na cor do jogador e um "?" no meio."""
    sup = pygame.Surface((w, h), pygame.SRCALPHA)
    cor = jogador.cor
    claro_demais = sum(cor) > 600
    if claro_demais:
        # Ovo branco: um tom levemente azulado para não confundir com a frente
        cor = ui.misturar(cor, (190, 200, 235), 0.35)
    borda = ui.escurecer(cor, 80)
    raio = max(6, w // 10)

    pygame.draw.rect(sup, borda, (0, 0, w, h), border_radius=raio)
    miolo = pygame.Rect(0, 0, w, h).inflate(-8, -8)
    pygame.draw.rect(sup, cor, miolo, border_radius=raio - 3)

    # Estampa de ovinhos (recortada no miolo)
    estampa = pygame.Surface(miolo.size, pygame.SRCALPHA)
    pygame.draw.rect(estampa, (255, 255, 255), estampa.get_rect(), border_radius=raio - 3)
    desenho = pygame.Surface(miolo.size, pygame.SRCALPHA)
    passo = max(14, w // 5)
    ow, oh = max(5, passo // 2 - 1), max(7, int(passo * 0.62))
    for j, y in enumerate(range(-passo // 2, miolo.h + passo, passo)):
        for x in range(-passo // 2 + (passo // 2 if j % 2 else 0), miolo.w + passo, passo):
            if claro_demais:
                tom = BRANCO if (x // passo + j) % 2 else ui.escurecer(cor, 40)
            else:
                tom = ui.clarear(cor, 40) if (x // passo + j) % 2 else ui.escurecer(cor, 30)
            pygame.draw.ellipse(desenho, tom, (x - ow // 2, y - oh // 2, ow, oh))
    desenho.blit(estampa, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    sup.blit(desenho, miolo.topleft)

    # Medalhão com "?"
    r = int(w * 0.24)
    centro = (w // 2, h // 2)
    pygame.draw.circle(sup, (0, 0, 0, 90), (centro[0] + 2, centro[1] + 3), r + 3)
    pygame.draw.circle(sup, BRANCO, centro, r + 3)
    pygame.draw.circle(sup, ui.escurecer(cor, 120), centro, r)
    tam = 32 if w >= 130 else (24 if w >= 90 else 16)
    ui.desenhar_texto(sup, "?", (centro[0] + 2, centro[1] + 2), tam, BRANCO, "center")

    # Brilhinho no canto
    pygame.draw.rect(sup, ui.clarear(borda, 60), (0, 0, w, h), 2, border_radius=raio)
    return sup


def _frente(w, h, jogador, apar, eh_voce):
    """Frente da carta: fundo clarinho com o ovo da combinação."""
    sup = pygame.Surface((w, h), pygame.SRCALPHA)
    raio = max(6, w // 10)
    pygame.draw.rect(sup, (196, 160, 104), (0, 0, w, h), border_radius=raio)
    miolo = pygame.Rect(0, 0, w, h).inflate(-8, -8)
    pygame.draw.rect(sup, (252, 246, 230), miolo, border_radius=raio - 3)
    pygame.draw.rect(sup, (232, 216, 184), miolo.inflate(-8, -8), 1, border_radius=raio - 5)

    # Halo colorido atrás do ovo
    altura = min(w * 0.6, h * 0.44)
    centro = (w / 2, h * 0.52)
    halo = HALOS[apar[0] % len(HALOS)]
    pygame.draw.circle(sup, halo, (int(centro[0]), int(centro[1] - altura * 0.08)), int(altura * 0.78))

    # Sombrinha no "chão"
    pygame.draw.ellipse(sup, (215, 200, 170), (centro[0] - altura * 0.4, centro[1] + altura * 0.44,
                                               altura * 0.8, altura * 0.16))
    jogador.desenhar(sup, centro, altura, aparencia=apar)

    if eh_voce:
        tam = 12 if w >= 120 else 10
        ui.desenhar_texto(sup, "VOCÊ", (w // 2, h - 8 - tam // 2 - 4), tam, (220, 90, 40),
                          "center", False)
        ui.estrela(sup, (14, 14), max(5, w // 16), AMARELO)
        ui.estrela(sup, (w - 14, 14), max(5, w // 16), AMARELO)
    return sup


def _sombra(w, h):
    sup = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(sup, (0, 0, 0, 90), (0, 0, w, h), border_radius=max(6, w // 10))
    return sup


class Carta:
    """Uma carta na mesa."""

    def __init__(self, par, rect, col, lin):
        self.par = par              # índice da combinação
        self.rect = rect
        self.col, self.lin = col, lin
        self.aberta = False         # face para cima (depois da animação)
        self.achada = False
        self.giro = 1.0             # 0..1 da animação de virar (1 = parada)
        self.brilho = 0.0           # estrelinhas depois de achar o par

    def virar(self):
        self.aberta = not self.aberta
        self.giro = 0.0

    @property
    def mostrando_frente(self):
        """Durante a animação, troca a face no meio do giro."""
        if self.giro < 0.5:
            return not self.aberta
        return self.aberta


class Memoria(MiniJogo):

    ID = "memoria"
    TITULO = "MEMÓRIA DO OVO"
    TITULO_CURTO = "MEMÓRIA"
    DESCRICAO = "A família do seu ovo virou cartas! Ache os pares de primos, tias e... você mesmo!"
    COR = (150, 100, 200)
    INSTRUCOES = [
        "Vire duas cartas: se forem iguais, é um par!",
        "Cada carta é um parente do seu ovo.",
        "Um dos pares é VOCÊ! Ache todos os pares",
        "com o menor número de jogadas.",
        "MOUSE ou SETAS + ESPAÇO para virar",
    ]
    OPCOES = ["FÁCIL", "MÉDIO", "DIFÍCIL"]
    MENOR_MELHOR = True

    def calcular_moedas(self, valor, venceu):
        """6 / 12 / 20 ao vencer, +4 se foi bem esperto (poucas jogadas)."""
        if not venceu:
            return self.MOEDAS_MIN
        base = (6, 12, 20)[self.opcao]
        if self.jogadas <= len(self.pares) * 1.5:
            base += 4
        return base
    ROTULO_PONTOS = "JOGADAS"
    CONTAGEM = False

    _cartas_cache = {}
    _mesas = {}

    # --------------------------------------------------------
    # CENÁRIO: quarto aconchegante à noite
    # --------------------------------------------------------

    @classmethod
    def criar_fundo(cls, jogador):
        sup = pygame.Surface((LARGURA, ALTURA))
        rnd = random.Random(4)

        # Papel de parede listrado com estampa de ovinhos e estrelas
        sup.fill((66, 54, 104))
        for x in range(0, LARGURA, 64):
            pygame.draw.rect(sup, (74, 61, 116), (x, 0, 32, ALTURA))
            pygame.draw.line(sup, (86, 72, 132), (x + 32, 0), (x + 32, ALTURA), 2)
        for j, y in enumerate(range(24, 620, 48)):
            for x in range(16 + (32 if j % 2 else 0), LARGURA, 64):
                if j % 2:
                    ui.estrela(sup, (x, y), 5, (100, 88, 150))
                else:
                    pygame.draw.ellipse(sup, (98, 84, 146), (x - 5, y - 7, 10, 14))

        # Rodapé de madeira e chão
        pygame.draw.rect(sup, (96, 62, 44), (0, 610, LARGURA, 40))
        pygame.draw.rect(sup, (122, 82, 56), (0, 610, LARGURA, 6))
        for y in range(650, ALTURA, 18):
            pygame.draw.rect(sup, (112, 74, 48) if (y // 18) % 2 else (104, 68, 44),
                             (0, y, LARGURA, 18))
            for x in range(rnd.randrange(0, 120), LARGURA, 180):
                pygame.draw.line(sup, (80, 52, 34), (x, y), (x, y + 17), 2)

        # Tapete redondo
        pygame.draw.ellipse(sup, (150, 60, 80), (262, 640, 500, 110))
        pygame.draw.ellipse(sup, (200, 110, 120), (282, 650, 460, 90), 6)

        # ----- Janela com lua e estrelas -----
        jan = pygame.Rect(22, 110, 112, 190)
        pygame.draw.rect(sup, (40, 30, 30), jan.inflate(22, 22).move(4, 6), border_radius=8)
        pygame.draw.rect(sup, (150, 104, 64), jan.inflate(22, 22), border_radius=8)
        ceu = ui.gradiente(jan.w, jan.h, (14, 18, 52), (48, 50, 118))
        sup.blit(ceu, jan)
        for _ in range(16):
            x = rnd.randrange(jan.left + 4, jan.right - 4)
            y = rnd.randrange(jan.top + 4, jan.bottom - 30)
            if rnd.random() < 0.3:
                ui.estrela(sup, (x, y), 4, (255, 240, 170))
            else:
                pygame.draw.circle(sup, (230, 230, 255), (x, y), 1)
        lua = (jan.x + 78, jan.y + 46)
        pygame.draw.circle(sup, (255, 246, 190), lua, 22)
        pygame.draw.circle(sup, (26, 30, 70), (lua[0] + 10, lua[1] - 6), 19)
        # Telhados da cidade lá fora
        for i, x in enumerate(range(jan.left, jan.right, 26)):
            alt = 18 + (i * 13) % 20
            pygame.draw.rect(sup, (20, 20, 40), (x, jan.bottom - alt, 24, alt))
            pygame.draw.rect(sup, (255, 220, 120), (x + 8, jan.bottom - alt + 6, 5, 5))
        pygame.draw.rect(sup, (150, 104, 64), (jan.centerx - 4, jan.top, 8, jan.h))
        pygame.draw.rect(sup, (150, 104, 64), (jan.left, jan.centery - 4, jan.w, 8))
        pygame.draw.rect(sup, (110, 72, 42), jan.inflate(22, 22), 3, border_radius=8)
        pygame.draw.rect(sup, (170, 120, 76), (jan.left - 20, jan.bottom + 10, jan.w + 40, 12),
                         border_radius=4)

        # Cortinas
        for lado in (-1, 1):
            base_x = jan.left - 18 if lado < 0 else jan.right - 6
            pontos = [(base_x, jan.top - 20), (base_x + 24, jan.top - 20),
                      (base_x + 24 - 10 * lado, jan.bottom + 30), (base_x, jan.bottom + 30)]
            pygame.draw.polygon(sup, (190, 70, 90), pontos)
            for k in range(1, 3):
                x = base_x + k * 8
                pygame.draw.line(sup, (150, 50, 70), (x, jan.top - 18), (x - 3 * lado, jan.bottom + 28), 2)
        pygame.draw.rect(sup, (120, 80, 50), (jan.left - 30, jan.top - 26, jan.w + 60, 8),
                         border_radius=4)

        # ----- Quadro com o retrato do jogador -----
        quadro = pygame.Rect(896, 104, 104, 120)
        pygame.draw.rect(sup, (30, 20, 20), quadro.move(4, 6), border_radius=6)
        pygame.draw.rect(sup, (200, 160, 70), quadro, border_radius=6)
        pygame.draw.rect(sup, (150, 110, 40), quadro, 3, border_radius=6)
        tela_q = quadro.inflate(-18, -18)
        pygame.draw.rect(sup, (240, 226, 196), tela_q)
        jogador.desenhar(sup, tela_q.center, 58)
        pygame.draw.line(sup, (60, 50, 40), (quadro.centerx, quadro.top - 18),
                         (quadro.left + 16, quadro.top), 2)
        pygame.draw.line(sup, (60, 50, 40), (quadro.centerx, quadro.top - 18),
                         (quadro.right - 16, quadro.top), 2)
        pygame.draw.circle(sup, (180, 180, 190), (quadro.centerx, quadro.top - 18), 4)

        # ----- Prateleira com luminária -----
        prat = pygame.Rect(890, 420, 120, 12)
        pygame.draw.rect(sup, (30, 20, 20), prat.move(3, 5), border_radius=3)
        pygame.draw.rect(sup, (150, 100, 62), prat, border_radius=3)
        for i, (cor, alt) in enumerate((((200, 70, 70), 34), ((70, 140, 200), 28), ((240, 200, 80), 38), ((100, 180, 110), 30))):
            pygame.draw.rect(sup, cor, (prat.x + 6 + i * 13, prat.y - alt, 11, alt))
            pygame.draw.rect(sup, ui.escurecer(cor, 50), (prat.x + 6 + i * 13, prat.y - alt, 11, alt), 1)
        lx = prat.right - 34
        # Brilho quente da luminária
        brilho = pygame.Surface((300, 300), pygame.SRCALPHA)
        for r in range(150, 0, -10):
            a = int(34 * (1 - r / 150))
            pygame.draw.circle(brilho, (255, 200, 110, a), (150, 150), r)
        sup.blit(brilho, (lx - 150, prat.y - 60 - 150))
        pygame.draw.rect(sup, (70, 60, 60), (lx - 3, prat.y - 44, 6, 44))
        pygame.draw.ellipse(sup, (70, 60, 60), (lx - 14, prat.y - 6, 28, 8))
        cupula = [(lx - 26, prat.y - 44), (lx + 26, prat.y - 44), (lx + 16, prat.y - 78), (lx - 16, prat.y - 78)]
        pygame.draw.polygon(sup, (255, 214, 130), cupula)
        pygame.draw.polygon(sup, (210, 150, 70), cupula, 2)

        # Leve escurecida geral (é noite)
        noite = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        noite.fill((10, 10, 40, 40))
        sup.blit(noite, (0, 0))
        return sup

    @classmethod
    def _fundo_mesa(cls, jogador, opcao):
        """Cenário + mesa de madeira do tamanho certo (cacheado)."""
        chave = (opcao, jogador.aparencia())
        sup = cls._mesas.get(chave)
        if sup is not None:
            return sup

        sup = cls.fundo(jogador).copy()
        mesa = _geometria(opcao)[4]

        # Sombra, espessura da frente e tampo
        sombra = pygame.Surface(mesa.inflate(24, 40).size, pygame.SRCALPHA)
        pygame.draw.rect(sombra, (0, 0, 0, 110), sombra.get_rect(), border_radius=24)
        sup.blit(sombra, (mesa.x - 6, mesa.y + 6))
        pygame.draw.rect(sup, (92, 56, 32), mesa.move(0, 12), border_radius=18)
        pygame.draw.rect(sup, (150, 98, 58), mesa, border_radius=18)

        # Tábuas do tampo
        tampo = mesa.inflate(-16, -16)
        pygame.draw.rect(sup, (170, 114, 70), tampo, border_radius=12)
        rnd = random.Random(8)
        tabua = 34
        for i, y in enumerate(range(tampo.top, tampo.bottom, tabua)):
            alt = min(tabua, tampo.bottom - y)
            cor = (176, 118, 72) if i % 2 else (166, 110, 66)
            r = pygame.Rect(tampo.x, y, tampo.w, alt)
            pygame.draw.rect(sup, cor, r, border_radius=10 if (i == 0 or y + tabua >= tampo.bottom) else 0)
            pygame.draw.line(sup, (130, 84, 50), (tampo.x + 6, y), (tampo.right - 7, y), 2)
            # veios da madeira
            for _ in range(3):
                vx = rnd.randrange(tampo.x + 20, max(tampo.x + 21, tampo.right - 80))
                vy = y + rnd.randrange(8, max(9, alt - 6))
                pygame.draw.arc(sup, (150, 98, 58), (vx, vy - 4, rnd.randint(30, 70), 8), 0, math.pi, 1)
        pygame.draw.rect(sup, (110, 70, 40), tampo, 2, border_radius=12)
        pygame.draw.rect(sup, (196, 140, 90), mesa, 2, border_radius=18)

        sup = sup.convert()
        cls._mesas[chave] = sup
        return sup

    @classmethod
    def _sprites(cls, w, h, jogador, pares):
        """Verso, frentes e sombra das cartas (cacheado)."""
        minha = jogador.aparencia()
        c = cls._cartas_cache
        if len(c) > 120:
            c.clear()

        chave = ("verso", w, h, minha)
        if chave not in c:
            c[chave] = _verso(w, h, jogador)
        verso = c[chave]

        frentes = []
        for apar in pares:
            chave = ("frente", w, h, apar, apar == minha)
            if chave not in c:
                c[chave] = _frente(w, h, jogador, apar, apar == minha)
            frentes.append(c[chave])

        chave = ("sombra", w, h)
        if chave not in c:
            c[chave] = _sombra(w, h)
        return verso, frentes, c[chave]

    @classmethod
    def desenhar_icone(cls, sup, jogador):
        w, h = sup.get_size()
        cw = int(h * 0.48)
        ch = int(cw / PROPORCAO)
        minha = jogador.aparencia()
        outra = ((minha[0] + 1) % len(assets.OVOS), (minha[1] + 3) % len(assets.CABELOS),
                 minha[2], (minha[3] + 2) % len(assets.BOCAS))
        verso = _verso(cw, ch, jogador)
        cartas = [(verso, 12), (_frente(cw, ch, jogador, outra, False), 0),
                  (_frente(cw, ch, jogador, minha, True), -12)]
        for i, (carta, ang) in enumerate(cartas):
            img = pygame.transform.rotate(carta, ang)
            cx = w // 2 + (i - 1) * int(cw * 0.95)
            cy = h // 2 + 4 + (0 if i == 1 else 6)
            sup.blit(img, img.get_rect(center=(cx, cy)))

    # --------------------------------------------------------
    # PARTIDA
    # --------------------------------------------------------

    def reiniciar(self):
        self.cols, self.linhas = NIVEIS[self.opcao]
        self.w, self.h, self.x0, self.y0, self.mesa = _geometria(self.opcao)
        self._fundo = self._fundo_mesa(self.jogador, self.opcao)

        qtd_pares = self.cols * self.linhas // 2
        self.pares = self._sortear_familia(qtd_pares)
        self.verso, self.frentes, self.sombra = self._sprites(self.w, self.h, self.jogador, self.pares)

        indices = list(range(qtd_pares)) * 2
        random.shuffle(indices)
        self.cartas = []
        for i, par in enumerate(indices):
            col, lin = i % self.cols, i // self.cols
            rect = pygame.Rect(self.x0 + col * (self.w + ESPACO),
                               self.y0 + lin * (self.h + ESPACO), self.w, self.h)
            self.cartas.append(Carta(par, rect, col, lin))

        self.viradas = []           # cartas abertas esperando conferir (no máx. 2)
        self.fase_jogada = None     # None / "conferir" / "errou" / "desvirar"
        self.t_jogada = 0.0
        self.jogadas = 0
        self.achados = 0
        self.cronometro = 0.0
        self.iniciado = False
        self.fase = "jogando"       # jogando / venceu
        self.t_fase = 0.0
        self.proximo_confete = 0.0

        self.cursor = 0
        self.teclado = False
        self.mouse = (-100, -100)

    def _sortear_familia(self, qtd):
        """
        Sorteia as combinações (ovo, cabelo, olho, boca) sem repetir.
        Sempre inclui o próprio jogador. Cada par difere de todos os
        outros em pelo menos 2 partes, e parentes da mesma cor de ovo
        sempre têm cabelos diferentes (fica fácil de distinguir).
        """
        minha = self.jogador.aparencia()
        lista = [minha]
        tamanhos = (len(assets.OVOS), len(assets.CABELOS), len(assets.OLHOS), len(assets.BOCAS))
        tentativas = 0
        while len(lista) < qtd:
            tentativas += 1
            # Espalha as cores: escolhe entre as cores menos usadas
            usos = [sum(1 for a in lista if a[0] == o) for o in range(tamanhos[0])]
            menor = min(usos)
            ovo = random.choice([o for o in range(tamanhos[0]) if usos[o] == menor])
            cand = (ovo, random.randrange(tamanhos[1]), random.randrange(tamanhos[2]),
                    random.randrange(tamanhos[3]))
            exigente = tentativas < 4000
            ok = True
            for a in lista:
                dif = _diferencas(cand, a)
                if dif < 2 or (exigente and a[0] == cand[0] and a[1] == cand[1]):
                    ok = False
                    break
            if ok:
                lista.append(cand)
        random.shuffle(lista)
        return lista

    # --------------------------------------------------------
    # AÇÕES
    # --------------------------------------------------------

    def _carta_em(self, pos):
        for i, c in enumerate(self.cartas):
            if c.rect.collidepoint(pos):
                return i
        return None

    def evento_jogo(self, e):
        if self.fase != "jogando":
            return

        if e.type == pygame.MOUSEMOTION:
            self.mouse = e.pos
            self.teclado = False

        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.mouse = e.pos
            self.teclado = False
            i = self._carta_em(e.pos)
            if i is not None:
                self.cursor = i
                self._escolher(i)

        elif e.type == pygame.KEYDOWN:
            if e.key in TECLAS:
                dc, dl = TECLAS[e.key]
                if self.teclado:
                    col = max(0, min(self.cols - 1, self.cursor % self.cols + dc))
                    lin = max(0, min(self.linhas - 1, self.cursor // self.cols + dl))
                    self.cursor = lin * self.cols + col
                self.teclado = True
            elif e.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER):
                self.teclado = True
                self._escolher(self.cursor)

    def _escolher(self, i):
        """Vira a carta i (se puder)."""
        # Enquanto confere/desvira um par, cliques são ignorados:
        # nunca ficam 3 cartas abertas ao mesmo tempo.
        if self.fase_jogada is not None or len(self.viradas) >= 2:
            return
        carta = self.cartas[i]
        if carta.aberta or carta.achada:
            return

        carta.virar()
        self.viradas.append(carta)
        self.iniciado = True
        self.som("virar", 0.9)

        if len(self.viradas) == 2:
            self.jogadas += 1
            self.pontos = self.jogadas
            self.fase_jogada = "conferir"
            self.t_jogada = 0.0

    def _acertou(self, a, b):
        a.achada = b.achada = True
        a.brilho = b.brilho = 1.0
        self.achados += 1
        self.som("acerto")
        for c in (a, b):
            self.particulas.explodir(c.rect.center, [AMARELO, BRANCO, self.jogador.cor,
                                                     (255, 150, 200)], 22, 230, 0.8)
        meio = ((a.rect.centerx + b.rect.centerx) / 2, (a.rect.centery + b.rect.centery) / 2)
        eh_voce = self.pares[a.par] == self.jogador.aparencia()
        self.textos.adicionar("É VOCÊ!" if eh_voce else "PAR!", meio, AMARELO, 20)

        if self.achados == len(self.pares):
            self.fase = "venceu"
            self.t_fase = 0.0

    # --------------------------------------------------------
    # LÓGICA
    # --------------------------------------------------------

    def atualizar_jogo(self, dt):
        for c in self.cartas:
            if c.giro < 1:
                c.giro = min(1.0, c.giro + dt / DUR_VIRAR)
            if c.brilho > 0:
                c.brilho = max(0.0, c.brilho - dt)

        if self.fase == "jogando" and self.iniciado:
            self.cronometro = min(5999.0, self.cronometro + dt)

        # Conferência do par
        if self.fase_jogada is not None:
            self.t_jogada += dt
            a, b = self.viradas
            if self.fase_jogada == "conferir":
                if a.giro >= 1 and b.giro >= 1:
                    if a.par == b.par:
                        self.viradas = []
                        self.fase_jogada = None
                        self._acertou(a, b)
                    else:
                        self.fase_jogada = "errou"
                        self.t_jogada = 0.0
                        self.som("erro", 0.3)
            elif self.fase_jogada == "errou":
                if self.t_jogada >= ESPERA_ERRO:
                    a.virar()
                    b.virar()
                    self.som("virar", 0.6)
                    self.fase_jogada = "desvirar"
                    self.t_jogada = 0.0
            elif self.fase_jogada == "desvirar":
                if a.giro >= 1 and b.giro >= 1:
                    self.viradas = []
                    self.fase_jogada = None

        if self.fase == "venceu":
            self.t_fase += dt
            self.proximo_confete -= dt
            if self.proximo_confete <= 0:
                self.proximo_confete = 0.2
                x = random.uniform(self.mesa.left, self.mesa.right)
                y = random.uniform(self.mesa.top, self.mesa.bottom)
                self.particulas.explodir((x, y), [AMARELO, (255, 120, 150), (120, 200, 255),
                                                  (140, 230, 120), self.jogador.cor],
                                         22, 280, 1.0, (3, 6))
            if self.t_fase >= DUR_VITORIA:
                self.terminar(venceu=True, valor=self.jogadas,
                              linhas=[f"JOGADAS: {self.jogadas}",
                                      f"TEMPO: {_formatar_tempo(self.cronometro)}"])

    # --------------------------------------------------------
    # DESENHO
    # --------------------------------------------------------

    def desenhar_jogo(self, tela):
        tela.blit(self._fundo, (0, 0))

        hover = None
        livre = self.fase == "jogando" and self.fase_jogada is None and self.estado == "jogando"
        if livre and not self.teclado:
            hover = self._carta_em(self.mouse)

        for i, c in enumerate(self.cartas):
            r = c.rect
            dy = 0
            if c.giro < 1:
                dy = -math.sin(math.pi * c.giro) * 10
            elif self.fase == "venceu":
                dy = -abs(math.sin(self.t_fase * 7 - (c.col + c.lin) * 0.6)) * 16
            elif i == hover and not c.aberta:
                dy = -4

            img = self.frentes[c.par] if c.mostrando_frente else self.verso
            sombra = self.sombra
            escala = abs(math.cos(math.pi * c.giro))
            if escala < 0.999:
                larg = max(1, int(self.w * escala))
                img = pygame.transform.smoothscale(img, (larg, self.h))
                sombra = pygame.transform.scale(sombra, (larg, self.h))
            tela.blit(sombra, sombra.get_rect(center=(r.centerx + 4, r.centery + 6)))
            destino = img.get_rect(center=(r.centerx, r.centery + dy))
            tela.blit(img, destino)

            if c.achada:
                pulso = 0.5 + 0.5 * math.sin(self.tempo * 4 + i)
                cor = ui.misturar((255, 200, 60), (255, 250, 190), pulso)
                pygame.draw.rect(tela, cor, destino.inflate(4, 4), 3, border_radius=max(6, self.w // 10) + 2)
            elif i == hover and not c.aberta:
                pygame.draw.rect(tela, BRANCO, destino.inflate(4, 4), 3, border_radius=max(6, self.w // 10) + 2)

            # Estrelinhas girando em volta do par encontrado
            if c.brilho > 0:
                for k in range(4):
                    a = self.tempo * 5 + k * math.pi / 2
                    pos = (destino.centerx + math.cos(a) * self.w * 0.62,
                           destino.centery + math.sin(a) * self.h * 0.5)
                    ui.estrela(tela, pos, 4 + 6 * c.brilho, AMARELO, a)

        # Cursor do teclado
        if self.teclado and self.fase == "jogando":
            r = self.cartas[self.cursor].rect
            pulso = int(3 * math.sin(self.tempo * 8))
            pygame.draw.rect(tela, (40, 30, 10), r.inflate(12 + pulso, 12 + pulso), 6, border_radius=14)
            pygame.draw.rect(tela, AMARELO, r.inflate(10 + pulso, 10 + pulso), 4, border_radius=14)

        self.particulas.desenhar(tela)
        self.textos.desenhar(tela)

    def desenhar_hud(self, tela):
        fundo = (20, 24, 40)

        # Jogadas
        caixa = pygame.Rect(12, 12, 196, 48)
        ui.painel(tela, caixa, fundo, BRANCO, 12, 3, sombra=False)
        ui.desenhar_texto(tela, f"JOGADAS: {self.jogadas}", (caixa.x + 16, caixa.centery + 1), 14,
                          AMARELO, "midleft")

        # Pares encontrados (com uma cartinha de ícone)
        caixa2 = pygame.Rect(caixa.right + 12, 12, 232, 48)
        ui.painel(tela, caixa2, fundo, BRANCO, 12, 3, sombra=False)
        icone = pygame.Rect(caixa2.x + 12, caixa2.y + 10, 20, 28)
        pygame.draw.rect(tela, self.jogador.cor, icone.move(5, -3), border_radius=4)
        pygame.draw.rect(tela, ui.escurecer(self.jogador.cor, 80), icone.move(5, -3), 2, border_radius=4)
        pygame.draw.rect(tela, (252, 246, 230), icone, border_radius=4)
        pygame.draw.rect(tela, (196, 160, 104), icone, 2, border_radius=4)
        ui.coracao(tela, icone.center, 12)
        ui.desenhar_texto(tela, f"PARES: {self.achados}/{len(self.pares)}",
                          (caixa2.right - 12, caixa2.centery + 1), 14, BRANCO, "midright")

        # Tempo
        caixa3 = pygame.Rect(caixa2.right + 12, 12, 132, 48)
        ui.painel(tela, caixa3, fundo, BRANCO, 12, 3, sombra=False)
        rc = (caixa3.x + 24, caixa3.centery)
        pygame.draw.circle(tela, BRANCO, rc, 13)
        pygame.draw.circle(tela, (40, 44, 70), rc, 13, 3)
        ang = self.cronometro * math.tau / 60 - math.pi / 2
        pygame.draw.line(tela, (220, 50, 50), rc, (rc[0] + math.cos(ang) * 9, rc[1] + math.sin(ang) * 9), 2)
        ui.desenhar_texto(tela, _formatar_tempo(self.cronometro), (caixa3.right - 12, caixa3.centery + 1),
                          16, BRANCO, "midright")

        # Nível e recorde
        caixa4 = pygame.Rect(caixa3.right + 12, 12, 176, 48)
        ui.painel(tela, caixa4, fundo, BRANCO, 12, 3, sombra=False)
        ui.desenhar_texto(tela, self.OPCOES[self.opcao], (caixa4.x + 12, caixa4.y + 9), 10, (180, 220, 255))
        rec = self.recorde()
        texto_rec = f"RECORDE: {rec}" if rec is not None else "RECORDE: --"
        ui.desenhar_texto(tela, texto_rec, (caixa4.x + 12, caixa4.y + 26), 12, AMARELO)
