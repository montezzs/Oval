from core import idioma
from core.idioma import t
import math
import random

import pygame

from settings import *
from core import assets, ui
from core import cosmeticos
from jogos.base_multi import MiniJogoMulti, TECLAS_MOVER, CORES_JOGADOR

# ============================================================
# SUMÔ DE OVOS (2 JOGADORES)
# ============================================================
# Dois ovos lutadores num tatame redondo, com vista "de cima"
# (como no Pou). Empurre, dê uma INVESTIDA e FINQUE O PÉ: quem
# cair do ringue perde o round. Cada round perdido desenha uma
# RACHADURA no ovo; a terceira rachadura encerra a luta.
#
# Pedra-papel-tesoura:
#   andar < investida < fincar o pé < contornar e empurrar de lado

# Ringue
CENTRO = (512, 410)
RAIO_RINGUE = 260
RAIO_ARGILA = 306
RAIO_MINIMO = 150

# Lutadores (círculo de colisão nos "pés" do ovo)
RAIO_OVO = 40
ALTURA_OVO = 90
ACELERACAO = 1400
VEL_MAX = 330
VEL_MAX_FINCADO = 60
VEL_LIMITE = 1500               # nada anda mais rápido que isso

INVESTIDA_VEL = 650
INVESTIDA_TEMPO = 0.25
INVESTIDA_RECARGA = 1.2
FINCAR_MAX = 1.0
FINCAR_RECARGA = 2.0
TEMPO_TONTO = 0.15

TEMPO_QUEDA = 0.6               # animação de cair do ringue
TEMPO_CAMERA_LENTA = 0.5
CAMERA_LENTA = 0.35
JANELA_EMPATE = 0.05            # os dois caem "juntos" -> round anulado

ROUNDS_VITORIA = 3              # melhor de 5

POWERUP_INTERVALO = 8.0
POWERUP_VIDA = 6.0
PIMENTA_TEMPO = 4.0
BIGORNA_TEMPO = 5.0

SUB_PASSO = 1 / 240             # passos pequenos: ninguém atravessa ninguém

# Posições de largada (atrás das linhas brancas)
LARGADA = [(412.0, 410.0), (612.0, 410.0)]

# Teclas de ação (movimento vem de TECLAS_MOVER)
TECLAS_INVESTIDA = [
    (pygame.K_SPACE, pygame.K_f, pygame.K_q),
    (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_RCTRL, pygame.K_PERIOD, pygame.K_KP0),
]
TECLAS_FINCAR = [
    (pygame.K_g, pygame.K_e),
    (pygame.K_RSHIFT, pygame.K_SLASH),
]

# Modos (OPCOES)
MODOS = [
    # TATAME: normal; depois de 20 s o ringue encolhe
    {"atrito": 3.0, "quique": 0.9, "raio": RAIO_RINGUE, "encolhe_desde": 20.0, "encolhe": 4.0},
    # GELO: escorrega muito e quica mais (caótico!)
    {"atrito": 0.8, "quique": 1.1, "raio": RAIO_RINGUE, "encolhe_desde": 20.0, "encolhe": 4.0},
    # ENCOLHE: começa maior e já encolhe desde o início
    {"atrito": 3.0, "quique": 0.9, "raio": 300, "encolhe_desde": 0.0, "encolhe": 6.0},
]

# Cores do cenário
COR_MADEIRA = (200, 170, 120)
COR_TABUA = (175, 145, 100)
COR_ARGILA = (230, 200, 150)
COR_ARGILA_BORDA = (200, 165, 115)
COR_ARGILA_FORA = (204, 170, 122)
COR_CORDA = (240, 225, 170)
COR_NO = (205, 185, 130)
COR_POEIRA = [(225, 200, 150), (240, 222, 180), (205, 175, 125)]


def _contorno(cor):
    """Cor de contorno que aparece até no ovo branco."""
    if sum(cor) > 600:
        return (120, 120, 140)
    return ui.escurecer(cor, 80)


# ============================================================
# DESENHOS COM CACHE
# ============================================================

_cache_sprites = {}
_cache_sombras = {}


def _sombra(largura, altura, alpha=80):
    chave = (int(largura), int(altura), alpha)
    s = _cache_sombras.get(chave)
    if s is None:
        s = pygame.Surface((max(2, int(largura)), max(2, int(altura))), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (60, 40, 20, alpha), s.get_rect())
        _cache_sombras[chave] = s
    return s


def _sprite_lutador(jogador, aparencia, altura, cor_faixa):
    """
    Avatar do ovo com a faixa de sumô (mawashi) na cintura.
    A faixa fica por cima do corpo e por baixo do rosto/cabelo.
    """
    apar = tuple(aparencia)
    cos = jogador._cosmeticos_de(apar)
    chave = (apar, cos, round(altura, 1), cor_faixa)
    sup = _cache_sprites.get(chave)
    if sup is not None:
        return sup

    ovo, cabelo, olho, boca = apar
    base = pygame.Surface((100, 100), pygame.SRCALPHA)
    cosmeticos.aplicar(base, cos, "atras", ovo)
    base.blit(assets.OVOS[ovo], (0, 0))
    cosmeticos.aplicar(base, cos, "corpo", ovo)

    # Faixa: desenhada numa camada e recortada no formato do ovo
    escuro = (40, 30, 30)
    faixa = pygame.Surface((100, 100), pygame.SRCALPHA)
    faixa.fill(cor_faixa, (0, 74, 100, 9))
    faixa.fill(escuro, (0, 73, 100, 1))
    faixa.fill(escuro, (0, 83, 100, 1))
    faixa.fill(ui.escurecer(cor_faixa, 50), (45, 74, 9, 15))      # a "aba" da frente
    faixa.fill(escuro, (44, 74, 1, 15))
    faixa.fill(escuro, (54, 74, 1, 15))
    mascara = assets.OVOS[ovo].copy()
    mascara.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGBA_MAX)
    faixa.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    base.blit(faixa, (0, 0))

    base.blit(assets.CABELOS[cabelo], (0, 0))
    base.blit(assets.OLHOS[olho], (0, 0))
    base.blit(assets.BOCAS[boca], (0, 0))
    cosmeticos.aplicar(base, cos, "frente", ovo)

    lado = max(1, round(100 * altura / jogador.OVO_RECT.h))
    sup = pygame.transform.smoothscale(base, (lado, lado))

    if len(_cache_sprites) > 60:
        _cache_sprites.clear()
    _cache_sprites[chave] = sup
    return sup


def _lugares_plateia():
    """Onde cada mini-ovo da plateia senta (pés), sobre uma almofada."""
    lugares = []
    # Duas fileiras em cima (a de trás fica atrás do placar)
    for fila, y in enumerate((74, 100)):
        desloc = 20 if fila % 2 else 0
        for x in range(26 + desloc, LARGURA - 16, 40):
            lugares.append((x, y))
    # Três colunas em cada lateral
    for coluna, x in enumerate((38, 98, 158)):
        for y in range(160 + (coluna % 2) * 28, ALTURA - 16, 56):
            lugares.append((x, y))
            lugares.append((LARGURA - x, y))
    lugares.sort(key=lambda p: p[1])
    return lugares


def _desenhar_pimenta(tela, centro, tam=1.0):
    x, y = centro
    corpo = [(x - 14 * tam, y - 4 * tam), (x - 4 * tam, y - 10 * tam), (x + 10 * tam, y - 6 * tam),
             (x + 16 * tam, y + 6 * tam), (x + 8 * tam, y + 2 * tam), (x - 4 * tam, y + 2 * tam)]
    pygame.draw.polygon(tela, (220, 40, 40), corpo)
    pygame.draw.polygon(tela, (130, 20, 20), corpo, 2)
    pygame.draw.line(tela, (255, 140, 140), (x - 6 * tam, y - 6 * tam), (x + 6 * tam, y - 5 * tam), 2)
    pygame.draw.line(tela, (60, 150, 50), (x - 13 * tam, y - 5 * tam), (x - 20 * tam, y - 12 * tam),
                     max(2, int(3 * tam)))
    pygame.draw.circle(tela, (60, 150, 50), (int(x - 13 * tam), int(y - 4 * tam)), max(2, int(4 * tam)))


def _desenhar_bigorna(tela, centro, tam=1.0):
    x, y = centro
    topo = [(x - 18 * tam, y - 8 * tam), (x + 12 * tam, y - 8 * tam), (x + 20 * tam, y - 3 * tam),
            (x + 8 * tam, y), (x + 6 * tam, y + 4 * tam), (x - 6 * tam, y + 4 * tam),
            (x - 8 * tam, y), (x - 14 * tam, y - 2 * tam)]
    pygame.draw.polygon(tela, (90, 95, 110), topo)
    pygame.draw.rect(tela, (90, 95, 110), (x - 10 * tam, y + 4 * tam, 20 * tam, 8 * tam))
    pygame.draw.polygon(tela, (40, 42, 55), topo, 2)
    pygame.draw.rect(tela, (40, 42, 55), (x - 10 * tam, y + 4 * tam, 20 * tam, 8 * tam), 2)
    pygame.draw.line(tela, (170, 175, 190), (x - 14 * tam, y - 6 * tam), (x + 10 * tam, y - 6 * tam), 2)


def _desenhar_estrelinhas(tela, centro, tempo, raio=26):
    for k in range(3):
        a = tempo * 7 + k * math.tau / 3
        px = centro[0] + math.cos(a) * raio
        py = centro[1] + math.sin(a) * raio * 0.35
        ui.estrela(tela, (px, py), 7, AMARELO, a)


# ============================================================
# LUTADOR
# ============================================================

class Lutador:

    def __init__(self, i, pos):
        self.i = i
        self.x, self.y = pos
        self.vx = self.vy = 0.0
        self.dir = (1.0, 0.0) if i == 0 else (-1.0, 0.0)
        self.espelhar = (i == 1)
        self.investida = 0.0        # tempo restante da investida
        self.recarga_inv = 0.0
        self.pedido_inv = 0.0       # guarda o aperto um pouquinho
        self.fincado = False
        self.tempo_fincado = 0.0
        self.recarga_fin = 0.0
        self.tonto = 0.0
        self.queda = None           # segundos desde que caiu (None = no ringue)
        self.sumiu = False
        self.pimenta = 0.0
        self.bigorna = 0.0
        self.esticar = 0.0          # squash & stretch (mola)
        self.vel_esticar = 0.0
        self.pulinhos = 0.0         # pose de vitória
        self.fumaca = 0.0

    @property
    def raio(self):
        return RAIO_OVO * (1.15 if self.bigorna > 0 else 1.0)

    @property
    def massa(self):
        m = 1.0
        if self.investida > 0:
            m *= 2.0
        if self.fincado:
            m *= 3.0
        if self.bigorna > 0:
            m *= 2.0
        return m

    @property
    def no_ringue(self):
        return self.queda is None

    def velocidade(self):
        return math.hypot(self.vx, self.vy)


# ============================================================
# JOGO
# ============================================================

class SumoOvo(MiniJogoMulti):

    ID = "sumo_ovo"
    TITULO = "SUMÔ DE OVOS"
    TITULO_CURTO = "SUMÔ"
    DESCRICAO = "Empurre o outro ovo para fora do tatame! Investida, finque o pé e não caia do ringue."
    COR = (220, 70, 70)
    INSTRUCOES = [
        "Empurre o outro ovo para fora do ringue! Quem cair perde o round.",
        "Cada round perdido racha o ovo: 3 rachaduras e acabou!",
        "INVESTIDA = empurrão forte • FINCAR O PÉ (segure) = fica pesadão",
        "J1: ESPAÇO/F investe, G finca • J2: ENTER/. investe, SHIFT finca",
    ]
    OPCOES = ["TATAME", "GELO", "ENCOLHE"]
    CONTROLES_J1 = "WASD + ESPAÇO + G"
    CONTROLES_J2 = "SETAS + ENTER + SHIFT"
    CONTAGEM = True

    MOEDAS_PARTIDA = 8
    MOEDAS_VITORIA_J1 = 5
    MOEDAS_MAX = 18

    # --------------------------------------------------------
    # CENÁRIO: dojô de madeira com o tatame de argila
    # --------------------------------------------------------

    @classmethod
    def criar_fundo(cls, jogador):
        sup = pygame.Surface((LARGURA, ALTURA))
        sup.fill(COR_MADEIRA)
        rnd = random.Random(8)

        # Tábuas de madeira
        for i, y in enumerate(range(0, ALTURA, 60)):
            pygame.draw.line(sup, COR_TABUA, (0, y), (LARGURA, y), 2)
            desloc = (i % 2) * 120
            for x in range(-desloc, LARGURA, 240):
                pygame.draw.line(sup, COR_TABUA, (x, y), (x, y + 60), 2)
            for _ in range(10):
                vx = rnd.randrange(LARGURA)
                vy = y + rnd.randrange(12, 50)
                pygame.draw.line(sup, (188, 158, 110), (vx, vy), (vx + rnd.randint(20, 70), vy), 1)

        # Sombra e plataforma de argila
        pygame.draw.circle(sup, (170, 140, 95), (CENTRO[0] + 6, CENTRO[1] + 8), RAIO_ARGILA + 4)
        pygame.draw.circle(sup, COR_ARGILA, CENTRO, RAIO_ARGILA)
        pygame.draw.circle(sup, COR_ARGILA_BORDA, CENTRO, RAIO_ARGILA, 6)
        for _ in range(500):
            a = rnd.uniform(0, math.tau)
            r = math.sqrt(rnd.random()) * (RAIO_ARGILA - 10)
            x = CENTRO[0] + math.cos(a) * r
            y = CENTRO[1] + math.sin(a) * r
            cor = rnd.choice([(220, 190, 140), (238, 210, 164), (215, 183, 132)])
            pygame.draw.circle(sup, cor, (int(x), int(y)), rnd.choice((1, 1, 2)))

        # Linhas de largada (shikiri-sen)
        pygame.draw.rect(sup, BRANCO, (452, 390, 8, 40))
        pygame.draw.rect(sup, BRANCO, (564, 390, 8, 40))

        # Almofadas (zabuton) da plateia
        for k, (x, y) in enumerate(_lugares_plateia()):
            cor = (130, 60, 130) if (x // 40 + y // 56) % 2 else (180, 60, 70)
            alm = pygame.Rect(0, 0, 36, 14)
            alm.center = (x, y)
            pygame.draw.rect(sup, ui.escurecer(cor, 50), alm.move(0, 3), border_radius=5)
            pygame.draw.rect(sup, cor, alm, border_radius=5)
            pygame.draw.rect(sup, ui.clarear(cor, 40), (alm.x + 4, alm.y + 2, alm.w - 8, 3),
                             border_radius=2)

        # Bandeirolas verticais nos cantos (nobori)
        for x, y in ((236, 130), (788, 130), (236, 600), (788, 600)):
            pygame.draw.line(sup, (90, 60, 35), (x, y - 10), (x, y + 104), 4)
            pano = pygame.Rect(x + 2, y, 22, 86)
            pygame.draw.rect(sup, (220, 50, 60), pano)
            for k in range(3):
                pygame.draw.rect(sup, BRANCO, (pano.x, pano.y + 12 + k * 26, pano.w, 8))
            pygame.draw.rect(sup, (130, 30, 40), pano, 2)
            pygame.draw.circle(sup, (240, 200, 80), (x, y - 12), 4)
        return sup

    @classmethod
    def desenhar_icone(cls, sup, jogador):
        w, h = sup.get_size()
        # Pedaço do ringue
        pygame.draw.circle(sup, COR_CORDA, (w // 2, int(h * 0.62)), int(h * 0.44), 4)
        apar2 = ((jogador.ovo + 1) % 4, (jogador.cabelo + 4) % 8, (jogador.olho + 1) % 3,
                 (jogador.boca + 2) % 6)
        jogador.desenhar(sup, (w * 0.36, h * 0.58), h * 0.4, angulo=-12)
        jogador.desenhar(sup, (w * 0.64, h * 0.58), h * 0.4, aparencia=apar2, espelhar=True,
                         angulo=12)
        ui.desenhar_texto(sup, t("BUM!"), (w // 2, int(h * 0.2)), 12, AMARELO, "center")

    # --------------------------------------------------------
    # PARTIDA
    # --------------------------------------------------------

    def __init__(self, app, menu):
        self.seguradas = set()      # teclas seguradas (lidas dos eventos)
        self.plateia = None
        super().__init__(app, menu)

    def reiniciar(self):
        self.modo = MODOS[self.opcao]
        self.rounds = [0, 0]
        self.rachaduras = [[], []]
        self.rounds_jogados = 0
        self.num_round = 1
        self.plateia_pulo = 0.0
        self.confete = 0.0
        self.cor_confete = BRANCO
        self._montar_plateia()
        self._novo_round(primeiro=True)

    def _novo_round(self, primeiro=False):
        self.lut = [Lutador(0, LARGADA[0]), Lutador(1, LARGADA[1])]
        self.raio = float(self.modo["raio"])
        self.tempo_round = 0.0
        self.morte_subita = False
        self.fase = "preparar"
        self.tempo_fase = 0.6 if primeiro else 0.0
        self.vencedor_round = None
        self.lento = 0.0
        self.espera_bate = 0.0
        self.powerup = None           # [tipo, x, y, vida]
        self.prox_powerup = POWERUP_INTERVALO
        self.banner = None            # [texto, cor, tempo restante, tamanho]
        self._banner(t("ROUND {n}", n=self.num_round), AMARELO, 1.4, 32)

    def _banner(self, texto, cor, tempo, tamanho=32):
        self.banner = [t(texto), cor, tempo, tamanho, tempo]

    def _montar_plateia(self):
        """Mini-ovos da família assistindo (desenhados uma vez só)."""
        if self.plateia is not None:
            return
        rnd = random.Random(5)
        aparencias = []
        for _ in range(14):
            aparencias.append((rnd.randrange(len(assets.OVOS)), rnd.randrange(len(assets.CABELOS)),
                               rnd.randrange(len(assets.OLHOS)), rnd.randrange(len(assets.BOCAS))))
        # Guardamos cópias: o cache do avatar pode ser limpo a qualquer hora
        self._sprites_plateia = [self.jogador.avatar(24, a).copy() for a in aparencias]
        self.plateia = [(x, y, rnd.randrange(len(self._sprites_plateia)), rnd.uniform(0, math.tau))
                        for x, y in _lugares_plateia()]

    # --------------------------------------------------------
    # TECLADO
    # --------------------------------------------------------

    def evento(self, e):
        # Acompanha as teclas seguradas em qualquer estado
        if e.type == pygame.KEYDOWN:
            self.seguradas.add(e.key)
        elif e.type == pygame.KEYUP:
            self.seguradas.discard(e.key)
        elif e.type == pygame.WINDOWFOCUSLOST:
            self.seguradas.clear()
        super().evento(e)

    def evento_jogo(self, e):
        if e.type != pygame.KEYDOWN:
            return
        for i in (0, 1):
            if e.key in TECLAS_INVESTIDA[i]:
                self.lut[i].pedido_inv = 0.15

    def _controles(self):
        """(dx, dy, fincar) de cada jogador."""
        apertadas = pygame.key.get_pressed()
        seg = self.seguradas

        def s(k):
            return apertadas[k] or k in seg

        res = []
        for i in (0, 1):
            m = TECLAS_MOVER[i]
            dx = (1 if s(m["dir"]) else 0) - (1 if s(m["esq"]) else 0)
            dy = (1 if s(m["baixo"]) else 0) - (1 if s(m["cima"]) else 0)
            fin = any(s(k) for k in TECLAS_FINCAR[i])
            res.append((dx, dy, fin))
        return res

    # --------------------------------------------------------
    # LÓGICA
    # --------------------------------------------------------

    def atualizar_jogo(self, dt):
        self.tempo_fase += dt
        self.plateia_pulo = max(0.0, self.plateia_pulo - dt)
        self.espera_bate = max(0.0, self.espera_bate - dt)
        if self.banner:
            self.banner[2] -= dt
            if self.banner[2] <= 0:
                self.banner = None

        # Confete da plateia na cor do vencedor
        if self.confete > 0:
            self.confete -= dt
            if random.random() < 0.5:
                x, y, _, _ = random.choice(self.plateia)
                self.particulas.explodir((x, y - 20), [self.cor_confete, BRANCO, AMARELO],
                                         3, 200, 1.0, (2, 4), 300)

        # Câmera lenta quando alguém cruza a borda
        dt_fis = dt
        if self.lento > 0:
            self.lento -= dt
            dt_fis = dt * CAMERA_LENTA

        controles = self._controles() if self.fase == "luta" else [(0, 0, False), (0, 0, False)]

        for L, (dx, dy, fin) in zip(self.lut, controles):
            self._atualizar_lutador(L, dx, dy, fin, dt_fis, dt)

        if self.fase == "preparar":
            if self.tempo_fase >= 1.4:
                self.fase = "luta"
                self.tempo_fase = 0.0
                self._banner("HAKKEYOI!", BRANCO, 0.8, 28)
                self.som("bandeira", 0.7)

        elif self.fase == "luta":
            self._atualizar_ringue(dt_fis)
            self._atualizar_powerup(dt_fis)

        # Física em passos pequenos
        passos = max(1, math.ceil(dt_fis / SUB_PASSO))
        h = dt_fis / passos
        for _ in range(passos):
            self._fisica(h)

        if self.fase == "queda":
            if self.tempo_fase >= 1.1:
                self._fim_do_round()
        elif self.fase == "resultado":
            if self.tempo_fase >= 2.2:
                if self.vencedor_round is not None and \
                        self.rounds[self.vencedor_round] >= ROUNDS_VITORIA:
                    self._acabar(self.vencedor_round)
                else:
                    if self.vencedor_round is not None:
                        self.num_round += 1
                    self._novo_round()

    def _atualizar_lutador(self, L, dx, dy, fin, dt_fis, dt):
        # Temporizadores (em tempo de jogo)
        L.recarga_inv = max(0.0, L.recarga_inv - dt_fis)
        L.recarga_fin = max(0.0, L.recarga_fin - dt_fis)
        L.tonto = max(0.0, L.tonto - dt_fis)
        L.investida = max(0.0, L.investida - dt_fis)
        L.pedido_inv = max(0.0, L.pedido_inv - dt)
        L.pimenta = max(0.0, L.pimenta - dt_fis)
        L.bigorna = max(0.0, L.bigorna - dt_fis)
        L.pulinhos = max(0.0, L.pulinhos - dt)

        # Mola do squash
        L.vel_esticar += (-240 * L.esticar - 11 * L.vel_esticar) * dt
        L.esticar = max(-1.0, min(1.0, L.esticar + L.vel_esticar * dt))

        if L.queda is not None:
            L.queda += dt_fis
            if L.queda >= TEMPO_QUEDA and not L.sumiu:
                L.sumiu = True
                self.particulas.explodir((L.x, L.y + 50), COR_POEIRA, 14, 160, 0.6, (3, 6), 200)
                self.textos.adicionar(t("POF!"), (L.x, L.y - 20), BRANCO, 16)
            return

        pode = self.fase == "luta" and L.tonto <= 0

        # Direção (a última direção fica guardada para a investida)
        if pode and (dx or dy):
            n = math.hypot(dx, dy)
            L.dir = (dx / n, dy / n)
            if dx:
                L.espelhar = dx < 0

        # FINCAR O PÉ (segurar)
        if pode and fin and L.recarga_fin <= 0 and L.tempo_fincado < FINCAR_MAX:
            if not L.fincado:
                L.fincado = True
                L.vel_esticar -= 5.0
                self.som("virar", 0.5)
                self.particulas.explodir((L.x, L.y), COR_POEIRA, 6, 90, 0.4, (2, 4), 60)
            L.tempo_fincado += dt_fis
        elif L.fincado:
            L.fincado = False
            L.recarga_fin = FINCAR_RECARGA
            L.tempo_fincado = 0.0
        elif not fin and L.recarga_fin <= 0:
            L.tempo_fincado = 0.0
        if L.fincado and L.tempo_fincado >= FINCAR_MAX:
            L.fincado = False
            L.recarga_fin = FINCAR_RECARGA
            L.tempo_fincado = 0.0

        # INVESTIDA
        recarga = 0.25 if L.pimenta > 0 else INVESTIDA_RECARGA
        if pode and L.pedido_inv > 0 and L.recarga_inv <= 0 and not L.fincado:
            L.pedido_inv = 0.0
            L.investida = INVESTIDA_TEMPO
            L.recarga_inv = recarga
            L.vx = L.dir[0] * INVESTIDA_VEL
            L.vy = L.dir[1] * INVESTIDA_VEL
            L.vel_esticar += 6.0
            self.som("asa", 0.8)
            self.particulas.explodir((L.x - L.dir[0] * 30, L.y - L.dir[1] * 30), COR_POEIRA,
                                     8, 140, 0.45, (3, 5), 80)
            if L.pimenta > 0:
                self.particulas.explodir((L.x, L.y - 50), [(255, 120, 40), (255, 220, 60)],
                                         6, 160, 0.4, (2, 4), -100)

        L.entrada = (dx, dy) if pode else (0, 0)

        # Fumaça da pimenta
        if L.pimenta > 0:
            L.fumaca -= dt
            if L.fumaca <= 0:
                L.fumaca = 0.08
                self.particulas.explodir((L.x + random.uniform(-14, 14), L.y - 92),
                                         [(200, 200, 200), (160, 160, 160)], 1, 40, 0.8,
                                         (4, 7), -120)

    def _atualizar_ringue(self, dt):
        self.tempo_round += dt
        modo = self.modo
        if self.tempo_round >= modo["encolhe_desde"] and self.raio > RAIO_MINIMO:
            if not self.morte_subita and modo["encolhe_desde"] > 0:
                self._banner("MORTE SÚBITA!", (255, 110, 110), 1.6, 28)
                self.som("erro", 0.6)
            self.morte_subita = True
            self.raio = max(RAIO_MINIMO, self.raio - modo["encolhe"] * dt)
        # Power-up que ficou fora do ringue some
        if self.powerup and math.hypot(self.powerup[1] - CENTRO[0],
                                       self.powerup[2] - CENTRO[1]) > self.raio - 24:
            self.powerup = None

    def _atualizar_powerup(self, dt):
        if self.powerup:
            self.powerup[3] -= dt
            if self.powerup[3] <= 0:
                self.powerup = None
            else:
                for L in self.lut:
                    if L.no_ringue and math.hypot(L.x - self.powerup[1],
                                                  L.y - self.powerup[2]) < L.raio + 22:
                        self._pegar_powerup(L, self.powerup[0])
                        self.powerup = None
                        break
            return

        self.prox_powerup -= dt
        if self.prox_powerup > 0:
            return
        self.prox_powerup = POWERUP_INTERVALO
        for _ in range(30):
            a = random.uniform(0, math.tau)
            r = math.sqrt(random.random()) * self.raio * 0.6
            x = CENTRO[0] + math.cos(a) * r
            y = CENTRO[1] + math.sin(a) * r
            if all(math.hypot(L.x - x, L.y - y) > 110 for L in self.lut):
                self.powerup = [random.choice(("pimenta", "bigorna")), x, y, POWERUP_VIDA]
                self.som("revelar", 0.5)
                break

    def _pegar_powerup(self, L, tipo):
        self.som("moeda", 0.8)
        cor = CORES_JOGADOR[L.i]
        if tipo == "pimenta":
            L.pimenta = PIMENTA_TEMPO
            L.recarga_inv = 0.0
            self.textos.adicionar(t("PIMENTA!"), (L.x, L.y - 110), (255, 120, 80), 16)
        else:
            L.bigorna = BIGORNA_TEMPO
            self.textos.adicionar(t("BIGORNA!"), (L.x, L.y - 110), (200, 210, 230), 16)
        L.vel_esticar += 6.0
        self.particulas.explodir((L.x, L.y - 45), [cor, BRANCO, AMARELO], 14, 200, 0.6, (2, 5), 200)

    # --------------------------------------------------------
    # FÍSICA
    # --------------------------------------------------------

    def _fisica(self, h):
        modo = self.modo
        for L in self.lut:
            if L.sumiu:
                continue
            # Aceleração pelo controle (não passa da velocidade máxima,
            # mas também não "freia" um ovo que foi arremessado)
            if L.no_ringue and L.investida <= 0:
                dx, dy = getattr(L, "entrada", (0, 0))
                if dx or dy:
                    n = math.hypot(dx, dy)
                    antes = L.velocidade()
                    nvx = L.vx + dx / n * ACELERACAO * h
                    nvy = L.vy + dy / n * ACELERACAO * h
                    depois = math.hypot(nvx, nvy)
                    maximo = VEL_MAX_FINCADO if L.fincado else VEL_MAX
                    limite = max(maximo, antes)
                    if depois > limite:
                        nvx *= limite / depois
                        nvy *= limite / depois
                    L.vx, L.vy = nvx, nvy

            # Atrito (fincado segura muito mais)
            atrito = modo["atrito"]
            if L.fincado:
                atrito = max(atrito * 3, 7.0)
            elif not L.no_ringue:
                atrito = 2.0
            elif self.fase in ("queda", "resultado"):
                atrito = max(atrito, 6.0)
            f = math.exp(-atrito * h)
            L.vx *= f
            L.vy *= f
            v = L.velocidade()
            if v > VEL_LIMITE:
                L.vx *= VEL_LIMITE / v
                L.vy *= VEL_LIMITE / v

            L.x += L.vx * h
            L.y += L.vy * h

        a, b = self.lut
        if a.no_ringue and b.no_ringue:
            self._colidir(a, b)

        # Saiu do ringue?
        caiu_agora = []
        for L in self.lut:
            if not L.no_ringue:
                continue
            dist = math.hypot(L.x - CENTRO[0], L.y - CENTRO[1])
            if self.fase in ("luta", "queda") and self.vencedor_round is None and \
                    not self._protegido(L):
                if dist > self.raio:
                    caiu_agora.append(L)
            elif dist > self.raio - 2 and dist > 0:
                # Quem ganhou o round não cai mais: fica na borda
                nx, ny = (L.x - CENTRO[0]) / dist, (L.y - CENTRO[1]) / dist
                L.x = CENTRO[0] + nx * (self.raio - 2)
                L.y = CENTRO[1] + ny * (self.raio - 2)
                vn = L.vx * nx + L.vy * ny
                if vn > 0:
                    L.vx -= vn * nx
                    L.vy -= vn * ny

        for L in caiu_agora:
            self._cair(L)

    def _protegido(self, L):
        """Depois da janela de empate, quem ficou no ringue não cai mais."""
        return self.fase == "queda" and self.tempo_fase > JANELA_EMPATE

    def _colidir(self, a, b):
        dx, dy = b.x - a.x, b.y - a.y
        dist = math.hypot(dx, dy)
        minimo = a.raio + b.raio
        if dist >= minimo:
            return
        if dist < 1e-6:
            nx, ny = (1.0, 0.0) if a.i == 0 else (-1.0, 0.0)
        else:
            nx, ny = dx / dist, dy / dist

        wa, wb = 1.0 / a.massa, 1.0 / b.massa
        soma = wa + wb

        # Separa (o mais pesado se mexe menos)
        sobra = minimo - dist
        a.x -= nx * sobra * wa / soma
        a.y -= ny * sobra * wa / soma
        b.x += nx * sobra * wb / soma
        b.y += ny * sobra * wb / soma

        # Impulso (quique com massas)
        vn = (b.vx - a.vx) * nx + (b.vy - a.vy) * ny
        if vn >= 0:
            return
        j = -(1 + self.modo["quique"]) * vn / soma
        a.vx -= j * wa * nx
        a.vy -= j * wa * ny
        b.vx += j * wb * nx
        b.vy += j * wb * ny

        # O mais leve fica tonto um instante
        if a.massa < b.massa:
            a.tonto = max(a.tonto, TEMPO_TONTO)
        elif b.massa < a.massa:
            b.tonto = max(b.tonto, TEMPO_TONTO)

        vel_rel = -vn
        a.vel_esticar -= min(6.0, vel_rel / 120)
        b.vel_esticar -= min(6.0, vel_rel / 120)
        if self.espera_bate <= 0 and vel_rel > 60:
            self.espera_bate = 0.12
            self.tremer(min(0.3, vel_rel / 2000))
            meio = ((a.x + b.x) / 2, (a.y + b.y) / 2 - 30)
            self.particulas.explodir(meio, COR_POEIRA, 6, 150, 0.5, (3, 5), 120)
            if vel_rel > 400:
                self.som("boing", 0.9)
                self.textos.adicionar(t("BUM!"), (meio[0], meio[1] - 50), AMARELO, 20)
                self.particulas.explodir(meio, [BRANCO, AMARELO], 8, 260, 0.35, (2, 4), 0)
            else:
                self.som("bater", min(1.0, 0.3 + vel_rel / 500))

    def _cair(self, L):
        L.queda = 0.0
        L.fincado = False
        L.investida = 0.0
        self.som("perder", 0.9)
        self.tremer(0.25)
        self.plateia_pulo = 1.4

        if self.fase == "luta":
            self.fase = "queda"
            self.tempo_fase = 0.0
            self.lento = TEMPO_CAMERA_LENTA
            self.perdedores = [L.i]
        else:
            # O outro também caiu (quase) junto: empate
            self.perdedores.append(L.i)

    def _fim_do_round(self):
        self.fase = "resultado"
        self.tempo_fase = 0.0
        self.rounds_jogados += 1
        perdedores = getattr(self, "perdedores", [])

        if len(perdedores) != 1:
            self.vencedor_round = None
            self._banner("EMPATE! DE NOVO!", AMARELO, 2.0, 28)
            self.som("erro", 0.7)
            return

        perdedor = perdedores[0]
        v = 1 - perdedor
        self.vencedor_round = v
        self.rounds[v] += 1
        self.rachaduras[perdedor].append(self._nova_rachadura())
        self.som("ponto")

        L = self.lut[v]
        L.pulinhos = 1.2
        L.vel_esticar -= 8.0
        self.textos.adicionar(t("HAI!"), (L.x, L.y - 120), AMARELO, 24)
        self.confete = 1.2
        self.cor_confete = self.cor(v)
        self.plateia_pulo = 1.6
        final = self.rounds[v] >= ROUNDS_VITORIA
        self._banner(t("{nome} VENCE A LUTA!" if final else "{nome} VENCE O ROUND!", nome=self.nome(v)),
                     CORES_JOGADOR[v], 2.2, 24 if len(self.nome(v)) <= 8 else 20)

    def _nova_rachadura(self):
        """Linha em zigue-zague dentro do ovo (coordenadas -1..1 da elipse)."""
        pontos = []
        u = random.uniform(-0.5, 0.5)
        v = random.uniform(-0.75, -0.3)
        pontos.append((u, v))
        dir_u = random.choice((-1, 1))
        for k in range(random.randint(3, 4)):
            u += dir_u * random.uniform(0.15, 0.3)
            v += random.uniform(0.15, 0.3)
            dir_u = -dir_u
            # Mantém dentro da elipse
            d = math.hypot(u, v)
            if d > 0.82:
                u, v = u * 0.82 / d, v * 0.82 / d
            pontos.append((u, v))
        return pontos

    def _acabar(self, vencedor):
        r = self.rounds
        self.terminar_multi(vencedor, [t("ROUNDS  {a} × {b}", a=r[0], b=r[1])])

    def calcular_moedas(self, valor, venceu):
        base = self.MOEDAS_PARTIDA + self.rounds_jogados
        if venceu:
            base += self.MOEDAS_VITORIA_J1
        return min(self.MOEDAS_MAX, base)

    # --------------------------------------------------------
    # DESENHO
    # --------------------------------------------------------

    def desenhar_jogo(self, tela):
        tela.blit(self.fundo(self.jogador), (0, 0))
        t = self.tempo

        self._desenhar_plateia(tela, t)
        self._desenhar_lanternas(tela, t)
        self._desenhar_corda(tela, t)

        # Power-up no chão
        if self.powerup:
            tipo, x, y, vida = self.powerup
            if vida > 1.5 or int(t * 8) % 2 == 0:
                s = _sombra(40, 12, 70)
                tela.blit(s, s.get_rect(center=(int(x), int(y) + 4)))
                flutua = math.sin(t * 4) * 4 - 16
                pygame.draw.circle(tela, (255, 250, 220), (int(x), int(y + flutua)), 22)
                pygame.draw.circle(tela, AMARELO, (int(x), int(y + flutua)), 22, 3)
                if tipo == "pimenta":
                    _desenhar_pimenta(tela, (x, y + flutua), 1.0)
                else:
                    _desenhar_bigorna(tela, (x, y + flutua + 2), 0.9)

        # Lutadores (quem está mais "embaixo" fica na frente)
        for L in sorted(self.lut, key=lambda o: o.y):
            self._desenhar_lutador(tela, L, t)

        self.particulas.desenhar(tela)
        self._desenhar_banner(tela)
        self.textos.desenhar(tela)

    def _desenhar_plateia(self, tela, t):
        pulo = self.plateia_pulo
        sprites = self._sprites_plateia
        for x, y, k, fase in self.plateia:
            dy = abs(math.sin(t * 3 + fase)) * 3
            if pulo > 0:
                dy += abs(math.sin(t * 9 + fase)) * 14 * min(1.0, pulo)
            s = sprites[k]
            tela.blit(s, (x - 16, y - 30 - dy))

    def _desenhar_lanternas(self, tela, t):
        pygame.draw.line(tela, (90, 60, 35), (0, 10), (250, 18), 2)
        pygame.draw.line(tela, (90, 60, 35), (LARGURA, 10), (LARGURA - 250, 18), 2)
        for k, x in enumerate((50, 130, 210, LARGURA - 50, LARGURA - 130, LARGURA - 210)):
            balanco = math.sin(t * 1.6 + k) * 3
            topo = 12 + (x % 7)
            r = pygame.Rect(0, 0, 30, 38)
            r.midtop = (x + balanco, topo + 6)
            pygame.draw.line(tela, (90, 60, 35), (x, topo), (r.centerx, r.top), 2)
            pygame.draw.ellipse(tela, (255, 120, 60), r)
            for fy in (r.top + 10, r.bottom - 12):
                pygame.draw.line(tela, (180, 60, 40), (r.left + 4, fy), (r.right - 4, fy), 2)
            pygame.draw.ellipse(tela, (180, 60, 40), r, 2)
            pygame.draw.rect(tela, (60, 40, 30), (r.centerx - 7, r.top - 3, 14, 5))
            pygame.draw.rect(tela, (60, 40, 30), (r.centerx - 7, r.bottom - 2, 14, 5))

    def _desenhar_corda(self, tela, t):
        raio = int(self.raio)
        # Argila fora da corda fica mais escura quando o ringue encolhe
        if raio + 8 < RAIO_ARGILA - 6:
            pygame.draw.circle(tela, COR_ARGILA_FORA, CENTRO, RAIO_ARGILA - 6,
                               RAIO_ARGILA - 6 - (raio + 7))

        perigo = self.morte_subita and (self.modo["encolhe_desde"] > 0 or self.raio < 200)
        piscar = perigo and self.fase == "luta" and int(t * 4) % 2 == 0
        cor = (235, 80, 80) if piscar else COR_CORDA
        escuro = (160, 50, 50) if piscar else (190, 170, 120)
        pygame.draw.circle(tela, cor, CENTRO, raio + 7, 14)
        pygame.draw.circle(tela, escuro, CENTRO, raio + 8, 2)
        pygame.draw.circle(tela, escuro, CENTRO, raio - 7, 2)
        for k in range(24):
            a = math.radians(k * 15)
            pygame.draw.circle(tela, COR_NO, (int(CENTRO[0] + math.cos(a) * raio),
                                              int(CENTRO[1] + math.sin(a) * raio)), 4)

    def _desenhar_lutador(self, tela, L, t):
        if L.sumiu:
            return
        caindo = L.queda is not None
        progresso = min(1.0, L.queda / TEMPO_QUEDA) if caindo else 0.0
        escala = 1.0 - 0.7 * progresso
        pe_y = L.y + 60 * progresso

        # Pulinhos de vitória
        pulo = 0.0
        if L.pulinhos > 0:
            pulo = abs(math.sin((1.2 - L.pulinhos) * math.pi * 3 / 1.2)) * 26

        # Sombra e anel de recarga da investida
        if not caindo:
            s = _sombra(80 * L.raio / RAIO_OVO, 22 * L.raio / RAIO_OVO, 90 if L.fincado else 70)
            tela.blit(s, s.get_rect(center=(int(L.x), int(L.y))))
            anel = pygame.Rect(0, 0, int(L.raio * 2.3), int(L.raio * 0.8))
            anel.center = (int(L.x), int(L.y))
            if self.fase in ("luta", "preparar"):
                if L.recarga_inv <= 0 or L.pimenta > 0:
                    pygame.draw.ellipse(tela, CORES_JOGADOR[L.i], anel, 3)
                else:
                    total = 0.25 if L.pimenta > 0 else INVESTIDA_RECARGA
                    frac = 1.0 - L.recarga_inv / total
                    pygame.draw.ellipse(tela, (90, 70, 50), anel, 2)
                    if frac > 0.02:
                        pygame.draw.arc(tela, BRANCO, anel, math.pi / 2,
                                        math.pi / 2 + math.tau * frac, 3)
            if L.fincado:
                pygame.draw.ellipse(tela, (120, 85, 50), anel.inflate(-20, -8), 3)

        # Squash & stretch
        e = L.esticar
        sx = 1 - 0.14 * e
        sy = 1 + 0.16 * e
        if L.fincado:
            sx *= 1.12
            sy *= 0.9
        if L.investida > 0:
            sx *= 0.92
            sy *= 1.06
        if L.pulinhos > 0:
            larg = 1 + 0.12 * abs(math.sin(t * 10))
            sx *= larg
            sy /= larg

        altura = ALTURA_OVO * (1.15 if L.bigorna > 0 else 1.0)
        sup = _sprite_lutador(self.jogador, self.aparencia(L.i), altura, CORES_JOGADOR[L.i])
        if L.espelhar:
            sup = pygame.transform.flip(sup, True, False)
        w, h = sup.get_size()
        nw = max(2, round(w * sx * escala))
        nh = max(2, round(h * sy * escala))
        if (nw, nh) != (w, h):
            sup = pygame.transform.smoothscale(sup, (nw, nh))
        if L.pimenta > 0:
            # Avermelhado pulsando ("ardido!")
            forca = 0.6 + 0.4 * math.sin(t * 12)
            sup = sup.copy()
            sup.fill((int(90 * forca), 0, 0), special_flags=pygame.BLEND_RGB_ADD)
            sup.fill((255, 200, 190), special_flags=pygame.BLEND_RGB_MULT)

        altura_vista = altura * sy * escala
        centro_ovo = (L.x, pe_y - altura_vista / 2 - pulo)

        # Tremidinha quando tonto
        if L.tonto > 0:
            centro_ovo = (centro_ovo[0] + math.sin(t * 60) * 2, centro_ovo[1])

        angulo = 0.0
        if caindo:
            angulo = L.queda * 540 * (1 if L.i == 0 else -1)
        elif L.investida > 0:
            angulo = -L.dir[0] * 10

        if angulo:
            sup = pygame.transform.rotate(sup, angulo)
        # O corpo do ovo fica 1% abaixo do centro da imagem
        rect = sup.get_rect(center=(round(centro_ovo[0]), round(centro_ovo[1] - nh * 0.01)))
        tela.blit(sup, rect)

        # Rachaduras (uma por round perdido)
        if self.rachaduras[L.i]:
            self._desenhar_rachaduras(tela, L, centro_ovo, altura_vista,
                                      altura * 0.9 * sx * escala, angulo)

        if caindo:
            return

        # Estrelinhas quando tonto e ícone do power-up
        topo = centro_ovo[1] - altura_vista / 2
        if L.tonto > 0:
            _desenhar_estrelinhas(tela, (centro_ovo[0], topo - 4), t)
        if L.bigorna > 0 and (L.bigorna > 1.2 or int(t * 8) % 2 == 0):
            _desenhar_bigorna(tela, (centro_ovo[0] + 34, topo + 2), 0.55)

        # Marcador do jogador
        cor = CORES_JOGADOR[L.i]
        my = topo - 18 + math.sin(t * 4 + L.i) * 2
        pygame.draw.polygon(tela, (20, 24, 40), [(centro_ovo[0] - 9, my - 2), (centro_ovo[0] + 9, my - 2),
                                                 (centro_ovo[0], my + 10)])
        pygame.draw.polygon(tela, cor, [(centro_ovo[0] - 6, my), (centro_ovo[0] + 6, my),
                                        (centro_ovo[0], my + 7)])
        if self.fase == "preparar":
            ui.desenhar_texto(tela, idioma.t("J{n}", n=L.i + 1), (centro_ovo[0], my - 6), 12, cor, "midbottom")

        # Tempo de fincar restante
        if L.fincado:
            frac = 1 - L.tempo_fincado / FINCAR_MAX
            barra = pygame.Rect(0, 0, 44, 6)
            barra.midtop = (int(L.x), int(L.y) + 18)
            pygame.draw.rect(tela, (40, 30, 20), barra.inflate(4, 4), border_radius=3)
            pygame.draw.rect(tela, (230, 170, 80), (barra.x, barra.y, int(barra.w * frac), barra.h),
                             border_radius=3)

    def _desenhar_rachaduras(self, tela, L, centro, altura, largura, angulo):
        cor = _contorno(self.cor(L.i))
        hw, hh = largura / 2, altura / 2
        rad = math.radians(-angulo)
        c, s = math.cos(rad), math.sin(rad)
        espessura = max(2, round(altura / 30))
        for linha in self.rachaduras[L.i]:
            pontos = []
            for u, v in linha:
                px, py = u * hw * (-1 if L.espelhar else 1), v * hh
                pontos.append((centro[0] + px * c - py * s, centro[1] + px * s + py * c))
            pygame.draw.lines(tela, cor, False, pontos, espessura)
            pygame.draw.lines(tela, (255, 255, 255), False,
                              [(x + 1, y + 1) for x, y in pontos], 1)

    def _desenhar_banner(self, tela):
        if not self.banner or self.estado != "jogando":
            return
        texto, cor, resta, tam, total = self.banner
        entrada = min(1.0, (total - resta) * 6)
        tam_atual = tam if entrada >= 1 else max(12, int(tam * (0.6 + 0.4 * entrada)))
        sup = ui.texto(texto, tam_atual, cor)
        r = sup.get_rect(center=(LARGURA // 2, 226))
        ui.painel(tela, r.inflate(36, 24), (20, 24, 40), cor, 14, 3, sombra=False)
        tela.blit(sup, r)

    def desenhar_hud(self, tela):
        """Placar de rounds: nome, bolinhas de vitória e o round atual."""
        caixa = pygame.Rect(0, 8, 520, 58)
        caixa.centerx = LARGURA // 2
        ui.painel(tela, caixa, (20, 24, 40), BRANCO, 14, 3, sombra=False)

        ui.desenhar_texto(tela, t("ROUND {n}", n=self.num_round), (caixa.centerx, caixa.y + 12), 12,
                          AMARELO, "midtop")
        ui.desenhar_texto(tela, t(self.OPCOES[self.opcao]), (caixa.centerx, caixa.bottom - 10), 10,
                          (180, 200, 255), "midbottom")

        for i in (0, 1):
            nome = self.nome(i)
            if len(nome) > 10:
                nome = nome[:10]
            cor = CORES_JOGADOR[i]
            lado = -1 if i == 0 else 1
            x_nome = caixa.centerx + lado * 90
            anc = "midright" if i == 0 else "midleft"
            ui.desenhar_texto(tela, nome, (x_nome, caixa.y + 20), 12, cor, anc)
            # Bolinhas de rounds ganhos
            for k in range(ROUNDS_VITORIA):
                bx = x_nome + lado * (8 + k * 22) if i == 1 else x_nome - (ROUNDS_VITORIA - 1 - k) * 22 - 8
                centro = (int(bx), caixa.y + 42)
                if k < self.rounds[i]:
                    pygame.draw.circle(tela, AMARELO, centro, 8)
                    pygame.draw.circle(tela, (150, 110, 20), centro, 8, 2)
                else:
                    pygame.draw.circle(tela, (70, 76, 100), centro, 8, 2)

        if self.morte_subita and self.estado == "jogando" and self.fase == "luta"                 and self.tempo_round - self.modo["encolhe_desde"] < 4.0:
            if int(self.tempo * 3) % 2 == 0:
                ui.desenhar_texto(tela, t("O RINGUE ESTÁ ENCOLHENDO!"), (LARGURA // 2, caixa.bottom + 8),
                                  10, (255, 150, 150), "midtop")

    # --------------------------------------------------------
    # TELA DE INÍCIO (VS) COMPACTA
    # --------------------------------------------------------
    # Com 3 modos + VISUAL DO J2 + VOLTAR a tela padrão não tem
    # espaço para as instruções; aqui tudo fica um pouco menor.

    def _desenhar_inicio(self, tela):
        ui.veu(tela, 150)
        topo = 24
        caixa = pygame.Rect(0, topo, 760, ALTURA - topo - 24)
        caixa.centerx = LARGURA // 2
        ui.painel(tela, caixa, (28, 32, 56), self.COR, 22, 5)

        ui.desenhar_texto(tela, t(self.TITULO), (LARGURA // 2, topo + 20), 28, AMARELO, "midtop")
        ui.desenhar_texto(tela, t("2 JOGADORES"), (LARGURA // 2, topo + 58), 12,
                          (180, 200, 255), "midtop")

        y_ovos = topo + 124
        for i, x in ((0, caixa.x + 150), (1, caixa.right - 150)):
            balanco = math.sin(self.tempo * 3 + i * 1.5) * 4
            self.desenhar_ovo(tela, i, (x, y_ovos + balanco), 60, espelhar=(i == 1))
            ui.desenhar_texto(tela, self.nome(i), (x, y_ovos + 42), 14, CORES_JOGADOR[i], "midtop")
            ctrl = self.CONTROLES_J1 if i == 0 else self.CONTROLES_J2
            ui.desenhar_texto(tela, t(ctrl), (x, y_ovos + 64), 10, BRANCO, "midtop")
        ui.desenhar_texto(tela, "VS", (LARGURA // 2, y_ovos), 32, AMARELO, "center")

        y = y_ovos + 88
        for linha in self.INSTRUCOES:
            for sub in ui.quebrar_linhas(t(linha), 10, caixa.w - 50):
                ui.desenhar_texto(tela, sub, (LARGURA // 2, y), 10, BRANCO, "midtop")
                y += 16
            y += 3

        v = self.vitorias()
        y_rec = self.menu_inicio.botoes[0].rect.y - 32
        ui.desenhar_texto(tela, t("VITÓRIAS  J1 {a} × {b} J2", a=v[0], b=v[1]), (LARGURA // 2, y_rec),
                          14, AMARELO, "midtop")
        ui.desenhar_texto(tela, t("ESCOLHA O MODO"), (LARGURA // 2, y_rec - 24), 12,
                          (180, 200, 255), "midtop")
        self.menu_inicio.desenhar(tela)
