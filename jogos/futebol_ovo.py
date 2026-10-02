import math
import random

import pygame

from settings import *
from core import assets, ui
from core.idioma import t
from jogos.base_multi import MiniJogoMulti, TECLAS_MOVER, CORES_JOGADOR

# ============================================================
# FUTEBOL DE OVOS (2 JOGADORES)
# ============================================================
# Um contra um no estádio lotado, com vista de lado (estilo "Head
# Soccer"). Os jogadores são os ovos, com chuteirinhas. Cabeceie,
# chute e solte o SUPER-CHUTE DE FOGO (o medidor enche a cada toque
# na bola). Power-ups caem do céu de paraquedas. O ROBERT apita.

# Campo
CHAO = 620                      # onde os ovos pisam e a bola quica
TETO = 96                       # teto invisível (abaixo do placar)
GOL_L = 90                      # largura (profundidade) do gol
GOL_TOPO = 400                  # altura do travessão
TELHADO_Y = 360                 # o telhadinho inclinado começa aqui (na parede)
ESP_TRAVE = 5                   # "grossura" do travessão e do telhado

# Ovos
ALTURA_OVO = 110
R_OVO = 50
BOTA = 10                       # altura da chuteirinha embaixo do ovo
VEL_ANDAR = 360
PULO = 900
GRAVIDADE_OVO = 2200

# Bola
R_BOLA = 26
R_PRAIA = 40
GRAVIDADE_BOLA = 1500
QUIQUE_CHAO = 0.75
QUIQUE_PAREDE = 0.8
QUIQUE_OVO = 0.7
ARRASTO = 0.2
ROLAMENTO = 0.7                 # atrito extra rolando no chão
SOMA_OVO = 0.6
SAIDA_MIN = 80
VEL_MAX_BOLA = 1400

# Chute e super-chute
CHUTE_TEMPO = 0.18
CHUTE_RECARGA = 0.4
CHUTE_ALCANCE = 70
CHUTE_VEL = (700, -450)
SUPER_VEL = 1100
SUPER_TOQUE = 0.2               # cada toque enche 20%
SUPER_ARMADO = 1.2              # tempo para encostar na bola depois de apertar
EMPURRAO_FOGO = 1000            # ~200 px de empurrão
TONTO_FOGO = 1.0

# Power-ups
PODER_INTERVALO = 12.0
PODER_INTERVALO_MALUCO = 4.0
GIGANTE_TEMPO = 6.0
GELO_TEMPO = 2.0
PRAIA_TEMPO = 8.0

TEMPO_GOL = 2.2
TEMPO_SAIDA = 1.0

SUB_PASSO = 1 / 240

CASAS = [300, LARGURA - 300]

# Modos: (tempo em segundos ou None, gols para vencer ou None, maluco?)
MODOS = [
    {"tempo": 120, "gols": None, "maluco": False},
    {"tempo": None, "gols": 5, "maluco": False},
    {"tempo": 60, "gols": None, "maluco": True},
]

# Teclas de ação (movimento: A/D e ←/→; pulo: W e ↑)
TECLAS_CHUTE = [
    (pygame.K_SPACE, pygame.K_f, pygame.K_q),
    (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_RCTRL, pygame.K_PERIOD, pygame.K_KP0),
]
TECLAS_SUPER = [
    (pygame.K_g, pygame.K_e),
    (pygame.K_RSHIFT, pygame.K_SLASH),
]

# Travessões: segmentos (a, b) com "grossura" (cápsulas)
TRAVES = [
    ((0, TELHADO_Y), (GOL_L, GOL_TOPO)),                        # telhado esquerdo
    ((0, GOL_TOPO), (GOL_L, GOL_TOPO)),                         # travessão esquerdo
    ((LARGURA, TELHADO_Y), (LARGURA - GOL_L, GOL_TOPO)),        # telhado direito
    ((LARGURA, GOL_TOPO), (LARGURA - GOL_L, GOL_TOPO)),         # travessão direito
]
PONTAS = [(GOL_L, GOL_TOPO), (LARGURA - GOL_L, GOL_TOPO)]

COR_CEU = (100, 190, 255)
COR_GRAMA = (70, 180, 70)
COR_FAIXA = (80, 195, 80)
COR_TRAVE = (240, 240, 240)

_cache = {}


def _bola_sup(raio, praia=False):
    """Bola de futebol (ou de praia) desenhada grande e reduzida."""
    chave = ("bola", raio, praia)
    s = _cache.get(chave)
    if s is not None:
        return s
    z = 4
    r = raio * z
    lado = r * 2 + 4 * z
    c = lado // 2
    d = pygame.Surface((lado, lado), pygame.SRCALPHA)
    if praia:
        cores = [(240, 60, 60), (255, 255, 255), (255, 210, 50), (255, 255, 255),
                 (60, 130, 230), (255, 255, 255)]
        for k in range(6):
            a1 = k * math.tau / 6
            a2 = (k + 1) * math.tau / 6
            pontos = [(c, c)] + [(c + math.cos(a1 + (a2 - a1) * t / 8) * r * 1.1,
                                  c + math.sin(a1 + (a2 - a1) * t / 8) * r * 1.1) for t in range(9)]
            pygame.draw.polygon(d, cores[k], pontos)
        pygame.draw.circle(d, (255, 255, 255), (c, c), r // 5)
    else:
        pygame.draw.circle(d, (255, 255, 255), (c, c), r)
        # Pentágono no meio e 5 em volta
        def pent(cx, cy, rr, giro):
            return [(cx + math.cos(giro + k * math.tau / 5) * rr,
                     cy + math.sin(giro + k * math.tau / 5) * rr) for k in range(5)]
        pygame.draw.polygon(d, (30, 30, 40), pent(c, c, r * 0.36, -math.pi / 2))
        for k in range(5):
            a = -math.pi / 2 + k * math.tau / 5 + math.pi / 5
            px, py = c + math.cos(a) * r * 0.95, c + math.sin(a) * r * 0.95
            pygame.draw.polygon(d, (30, 30, 40), pent(px, py, r * 0.3, a))
            ix, iy = c + math.cos(a) * r * 0.36, c + math.sin(a) * r * 0.36
            pygame.draw.line(d, (30, 30, 40), (ix, iy), (px, py), z)
    mascara = pygame.Surface((lado, lado), pygame.SRCALPHA)
    pygame.draw.circle(mascara, (255, 255, 255, 255), (c, c), r)
    d.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    pygame.draw.circle(d, (40, 40, 60), (c, c), r, 2 * z)
    pygame.draw.circle(d, (255, 255, 255, 150), (c - r // 3, c - r // 3), r // 6)
    s = pygame.transform.smoothscale(d, (lado // z, lado // z))
    _cache[chave] = s
    return s


def _bola_fogo(raio, praia):
    chave = ("fogo", raio, praia)
    s = _cache.get(chave)
    if s is None:
        s = _bola_sup(raio, praia).copy()
        s.fill((255, 150, 60), special_flags=pygame.BLEND_RGB_MULT)
        s.fill((60, 10, 0), special_flags=pygame.BLEND_RGB_ADD)
        _cache[chave] = s
    return s


def _alpha(tam, cor, alpha, elipse=True):
    chave = ("a", tam, cor, alpha, elipse)
    s = _cache.get(chave)
    if s is None:
        s = pygame.Surface(tam, pygame.SRCALPHA)
        if elipse:
            pygame.draw.ellipse(s, (*cor, alpha), s.get_rect())
        else:
            s.fill((*cor, alpha))
        _cache[chave] = s
    return s


def _ponto_segmento(px, py, a, b):
    """Ponto mais perto de (px, py) no segmento a-b."""
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    return ax + dx * t, ay + dy * t


# ============================================================
# PEÇAS
# ============================================================

class Jogador:

    def __init__(self, i):
        self.i = i
        self.lado = 1 if i == 0 else -1          # para onde ataca/chuta
        self.x = float(CASAS[i])
        self.pes = float(CHAO)
        self.vx = 0.0
        self.vy = 0.0
        self.kb = 0.0                            # empurrão (bola de fogo)
        self.no_chao = True
        self.chute = 0.0
        self.chute_feito = False
        self.recarga = 0.0
        self.medidor = 0.0
        self.armado = 0.0
        self.tonto = 0.0
        self.congelado = 0.0
        self.gigante = 0.0
        self.esticar = 0.0
        self.vel_esticar = 0.0
        self.espera_toque = 0.0
        self.pedido_pulo = 0.0
        self.pedido_chute = 0.0
        self.imune_fogo = 0.0

    @property
    def escala(self):
        return 1.5 if self.gigante > 0 else 1.0

    @property
    def raio(self):
        return R_OVO * self.escala

    @property
    def cy(self):
        """Centro do ovo (e do círculo de colisão)."""
        return self.pes - BOTA * self.escala - ALTURA_OVO * self.escala / 2

    @property
    def x_min(self):
        return GOL_L + self.raio

    @property
    def x_max(self):
        return LARGURA - GOL_L - self.raio

    @property
    def preso(self):
        return self.tonto > 0 or self.congelado > 0


class Bola:

    def __init__(self, x, y):
        self.x, self.y = float(x), float(y)
        self.vx = self.vy = 0.0
        self.fogo = False
        self.praia = 0.0
        self.angulo = 0.0
        self.squash = 0.0
        self.parada = 0.0
        self.na_cabeca = 0.0
        self.toque_cabeca = 9.0

    @property
    def raio(self):
        return R_PRAIA if self.praia > 0 else R_BOLA


# ============================================================
# JOGO
# ============================================================

class FutebolOvo(MiniJogoMulti):

    ID = "futebol_ovo"
    TITULO = "FUTEBOL DE OVOS"
    TITULO_CURTO = "FUTEBOL"
    DESCRICAO = "Um contra um no estádio lotado! Cabeceie, chute e solte o SUPER-CHUTE DE FOGO."
    COR = (60, 170, 70)
    INSTRUCOES = [
        "Faça gol no outro lado! Cabeceie e chute a bola.",
        "Cada toque enche o SUPER. Cheio? Solte o SUPER-CHUTE DE FOGO!",
        "Pegue os presentes que caem do céu (GIGANTE, GELO, PRAIA).",
        "J1: A D W, ESPAÇO chuta, G super • J2: ← → ↑, ENTER chuta, SHIFT super",
    ]
    OPCOES = ["2 MINUTOS", "ATÉ 5 GOLS", "1 MIN MALUCO"]
    CONTROLES_J1 = "A D W + ESPAÇO + G"
    CONTROLES_J2 = "← → ↑ + ENTER + SHIFT"
    CONTAGEM = True

    MOEDAS_PARTIDA = 8
    MOEDAS_VITORIA_J1 = 5
    MOEDAS_MAX = 18

    @classmethod
    def formatar(cls, valor):
        return f"{int(valor) // 60}:{int(valor) % 60:02d}"

    # --------------------------------------------------------
    # CENÁRIO: estádio com arquibancada e gramado
    # --------------------------------------------------------

    @classmethod
    def criar_fundo(cls, jogador):
        sup = pygame.Surface((LARGURA, ALTURA))
        rnd = random.Random(13)

        # Céu com nuvens
        sup.blit(ui.gradiente(LARGURA, 170, (70, 160, 240), COR_CEU), (0, 0))
        for nx, ny, esc in ((150, 110, 0.8), (480, 70, 0.6), (800, 120, 0.9)):
            for dx, dy, r in ((-30, 6, 22), (0, -6, 30), (32, 4, 24), (58, 10, 16), (-52, 12, 14)):
                pygame.draw.circle(sup, (255, 255, 255), (int(nx + dx * esc), int(ny + dy * esc)),
                                   int(r * esc))

        # Refletores
        for x in (70, LARGURA - 70):
            pygame.draw.line(sup, (90, 90, 110), (x, 150), (x, 40), 6)
            painel = pygame.Rect(0, 0, 70, 34)
            painel.midbottom = (x, 44)
            pygame.draw.rect(sup, (70, 70, 90), painel, border_radius=4)
            for k in range(3):
                for m in range(2):
                    pygame.draw.circle(sup, (255, 250, 200), (painel.x + 14 + k * 21, painel.y + 10 + m * 14), 6)

        # Arquibancada em 2 degraus
        pygame.draw.rect(sup, (160, 160, 175), (0, 160, LARGURA, 120))
        pygame.draw.rect(sup, (130, 130, 150), (0, 280, LARGURA, 120))
        for y in range(160, 400, 30):
            pygame.draw.line(sup, (115, 115, 135), (0, y), (LARGURA, y), 2)
        pygame.draw.rect(sup, (100, 100, 120), (0, 156, LARGURA, 6))
        pygame.draw.rect(sup, (100, 100, 120), (0, 278, LARGURA, 5))

        # Placas de propaganda na beira do campo
        pygame.draw.rect(sup, (40, 50, 90), (0, 396, LARGURA, 34))
        for k, texto in enumerate(("OVAL", "LIMÕES & CIA", "OVOEDAS", "OVEIO", "GOL!")):
            cx = 110 + k * 200
            t = ui.texto(texto, 12, (255, 230, 90), sombra=False)
            pygame.draw.rect(sup, (60, 70, 130), t.get_rect(center=(cx, 413)).inflate(24, 12),
                             border_radius=3)
            sup.blit(t, t.get_rect(center=(cx, 413)))

        # Gramado com faixas
        pygame.draw.rect(sup, COR_GRAMA, (0, 430, LARGURA, ALTURA - 430))
        for x in range(0, LARGURA, 128):
            pygame.draw.rect(sup, COR_FAIXA, (x, 430, 64, ALTURA - 430))
        for _ in range(500):
            x, y = rnd.randrange(LARGURA), rnd.randrange(432, ALTURA)
            pygame.draw.line(sup, (60, 160, 60), (x, y), (x + rnd.randint(-1, 1), y - 4), 1)

        # Linhas brancas (vistas de lado)
        branco = (235, 245, 235)
        pygame.draw.line(sup, branco, (0, 452), (LARGURA, 452), 2)
        pygame.draw.line(sup, branco, (0, 700), (LARGURA, 700), 3)
        pygame.draw.line(sup, branco, (LARGURA // 2 - 8, 452), (LARGURA // 2 + 8, 700), 3)
        pygame.draw.ellipse(sup, branco, (LARGURA // 2 - 120, 540, 240, 80), 3)
        pygame.draw.lines(sup, branco, False, [(0, 470), (170, 470), (230, 680), (0, 680)], 3)
        pygame.draw.lines(sup, branco, False, [(LARGURA, 470), (LARGURA - 170, 470),
                                               (LARGURA - 230, 680), (LARGURA, 680)], 3)
        # Sombra do chão onde os ovos pisam
        pygame.draw.line(sup, (60, 150, 60), (0, CHAO + 2), (LARGURA, CHAO + 2), 2)
        return sup

    @classmethod
    def desenhar_icone(cls, sup, jogador):
        w, h = sup.get_size()
        apar2 = ((jogador.ovo + 1) % 4, (jogador.cabelo + 4) % 8, (jogador.olho + 1) % 3,
                 (jogador.boca + 2) % 6)
        # Golzinhos nas pontas
        for x0, x1 in ((0, int(w * 0.09)), (w - 1, int(w * 0.91))):
            topo = int(h * 0.5)
            for k in range(0, 5):
                y = topo + k * (h - 8 - topo) // 4
                pygame.draw.line(sup, BRANCO, (x0, y), (x1, y), 1)
            pygame.draw.line(sup, COR_TRAVE, (x1, topo), (x1, h - 8), 3)
            pygame.draw.line(sup, COR_TRAVE, (x0, topo), (x1, topo), 3)
        jogador.desenhar(sup, (w * 0.3, h * 0.68), h * 0.42)
        jogador.desenhar(sup, (w * 0.72, h * 0.68), h * 0.42, aparencia=apar2, espelhar=True)
        bola = pygame.transform.smoothscale(_bola_sup(R_BOLA), (int(h * 0.2), int(h * 0.2)))
        sup.blit(bola, bola.get_rect(center=(w // 2, int(h * 0.3))))

    # --------------------------------------------------------
    # PARTIDA
    # --------------------------------------------------------

    def __init__(self, app, menu):
        self.seguradas = set()
        super().__init__(app, menu)

    def reiniciar(self):
        self.modo = MODOS[self.opcao]
        self.gravidade = 0.7 if self.modo["maluco"] else 1.0
        self.placar = [0, 0]
        self.relogio = float(self.modo["tempo"] or 0)
        self.decorrido = 0.0
        self.gol_de_ouro = False
        self.jogs = [Jogador(0), Jogador(1)]
        self.bola = Bola(LARGURA // 2, 250)
        self.poder = None                     # [tipo, x, y, vy, vida_no_chao]
        self.prox_poder = PODER_INTERVALO_MALUCO if self.modo["maluco"] else PODER_INTERVALO
        self.banner = None
        self.lento = 0.0
        self.espera_lento = 0.0
        self.quem_marcou = None
        self.rede = [0.0, 0.0]                # ondulação das redes
        self.juiz_x = LARGURA / 2
        self.toto_x = 60.0
        self.toto_dir = 1
        self._montar_sprites()
        self._saida()

    def _montar_sprites(self):
        """Avatares e torcida guardados (o cache do avatar pode ser limpo)."""
        self._avatar = {}
        rnd = random.Random(4)
        self._torcida = [[], []]
        for i in (0, 1):
            ovo = self.aparencia(i)[0]
            for _ in range(6):
                apar = (ovo, rnd.randrange(len(assets.CABELOS)), rnd.randrange(len(assets.OLHOS)),
                        rnd.randrange(len(assets.BOCAS)))
                self._torcida[i].append(self.jogador.avatar(18, apar).copy())
        self._mini = [self.jogador.avatar(30, self.aparencia(i)).copy() for i in (0, 1)]
        self.lugares = []
        for fila, y in enumerate((212, 248, 334, 370)):
            desloc = 11 if fila % 2 else 0
            for x in range(14 + desloc, LARGURA - 8, 24):
                lado = 0 if x < LARGURA // 2 else 1
                self.lugares.append((x, y, lado, rnd.randrange(6), rnd.uniform(0, math.tau)))

    def _avatar_de(self, i, altura):
        chave = (i, altura)
        s = self._avatar.get(chave)
        if s is None:
            s = self.jogador.avatar(altura, self.aparencia(i)).copy()
            self._avatar[chave] = s
        return s

    def _saida(self):
        """Recoloca todo mundo e a bola fica parada no alto do meio."""
        for jg in self.jogs:
            jg.x = float(CASAS[jg.i])
            jg.pes = float(CHAO)
            jg.vx = jg.vy = jg.kb = 0.0
            jg.no_chao = True
            jg.chute = 0.0
            jg.armado = 0.0
            jg.tonto = 0.0
        praia = self.bola.praia if hasattr(self, "bola") else 0.0
        self.bola = Bola(LARGURA // 2, 250)
        self.bola.praia = praia
        self.fase = "saida"
        self.tempo_fase = 0.0

    def _banner(self, texto, cor, tempo, tamanho=28):
        self.banner = [texto, cor, tempo, tamanho, tempo]

    # --------------------------------------------------------
    # TECLADO
    # --------------------------------------------------------

    def evento(self, e):
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
            jg = self.jogs[i]
            if e.key == TECLAS_MOVER[i]["cima"]:
                jg.pedido_pulo = 0.12
            elif e.key in TECLAS_CHUTE[i]:
                jg.pedido_chute = 0.12
            elif e.key in TECLAS_SUPER[i]:
                self._armar_super(jg)

    def _armar_super(self, jg):
        if jg.medidor >= 1.0 and jg.armado <= 0 and not jg.preso:
            jg.armado = SUPER_ARMADO
            self.som("revelar", 0.8)
            self.textos.adicionar(t("SUPER!"), (jg.x, jg.cy - 90), (255, 150, 60), 16)

    def _controles(self):
        apertadas = pygame.key.get_pressed()
        seg = self.seguradas
        res = []
        for i in (0, 1):
            m = TECLAS_MOVER[i]

            def s(nome):
                k = m[nome]
                return apertadas[k] or k in seg

            res.append(((1 if s("dir") else 0) - (1 if s("esq") else 0), s("cima")))
        return res

    # --------------------------------------------------------
    # LÓGICA
    # --------------------------------------------------------

    def atualizar_jogo(self, dt):
        self.tempo_fase += dt
        self.espera_lento = max(0.0, self.espera_lento - dt)
        for k in (0, 1):
            self.rede[k] = max(0.0, self.rede[k] - dt)
        if self.banner:
            self.banner[2] -= dt
            if self.banner[2] <= 0:
                self.banner = None
        self._animar_fundo(dt)

        dt_fis = dt
        if self.lento > 0:
            self.lento -= dt
            dt_fis = dt * 0.35

        jogando = self.fase in ("jogo", "saida")
        controles = self._controles() if jogando else [(0, False), (0, False)]
        for jg, (dx, pulo) in zip(self.jogs, controles):
            self._atualizar_jogador(jg, dx, pulo, dt_fis, dt, jogando)

        bola = self.bola
        bola.praia = max(0.0, bola.praia - dt_fis)
        bola.squash = max(0.0, bola.squash - dt)

        if self.fase == "saida":
            if self.tempo_fase >= TEMPO_SAIDA:
                self.fase = "jogo"
                self.tempo_fase = 0.0
                self.som("bandeira", 0.6)
        elif self.fase == "jogo":
            self.decorrido += dt_fis
            self._atualizar_relogio(dt_fis)
            self._atualizar_poder(dt_fis)
        elif self.fase == "gol":
            if self.tempo_fase >= TEMPO_GOL:
                if self._acabou():
                    self._acabar()
                    return
                self._saida()
        elif self.fase == "apito":
            if self.tempo_fase >= 1.6:
                self._acabar()
                return

        passos = max(1, math.ceil(dt_fis / SUB_PASSO))
        h = dt_fis / passos
        for _ in range(passos):
            self._fisica(h)

        # Giro da bola
        if self.fase != "saida":
            bola.angulo -= math.degrees(bola.vx * dt_fis / bola.raio)

        # Bola parada em cima da cabeça por 2 s -> empurrãozinho
        bola.toque_cabeca += dt
        if bola.toque_cabeca < 0.25:
            bola.na_cabeca += dt
            if bola.na_cabeca >= 2.0:
                bola.na_cabeca = 0.0
                bola.vx = random.choice((-1, 1)) * 350
                bola.vy = -350
                self.som("boing", 0.6)
        else:
            bola.na_cabeca = 0.0

        # Bola parada muito tempo (num canto) -> pula para o meio
        if self.fase == "jogo" and math.hypot(bola.vx, bola.vy) < 30:
            bola.parada += dt
            if bola.parada > 3.0:
                bola.parada = 0.0
                bola.vy = -600
                bola.vx = 260 if bola.x < LARGURA / 2 else -260
        else:
            bola.parada = 0.0

        # Fogo solta faísca
        if bola.fogo and random.random() < 0.8:
            self.particulas.explodir((bola.x, bola.y), [(255, 140, 30), (255, 220, 60), (220, 50, 20)],
                                     2, 80, 0.4, (3, 6), -60)

    def _atualizar_relogio(self, dt):
        if self.modo["tempo"] is None or self.gol_de_ouro:
            return
        antes = self.relogio
        self.relogio = max(0.0, self.relogio - dt)
        if antes > 10 >= self.relogio:
            self._banner(t("10 SEGUNDOS!"), (255, 180, 120), 1.2, 20)
        if self.relogio <= 0:
            if self.placar[0] == self.placar[1]:
                self.gol_de_ouro = True
                self._banner(t("GOL DE OURO!"), AMARELO, 2.0, 32)
                self.som("bandeira")
                self.tremer(0.2)
            else:
                self.fase = "apito"
                self.tempo_fase = 0.0
                self._banner(t("FIM DE JOGO!"), BRANCO, 1.6, 32)
                self.som("bandeira")

    def _acabou(self):
        g = self.placar
        if self.gol_de_ouro:
            return True
        if self.modo["gols"] is not None and max(g) >= self.modo["gols"]:
            return True
        return False

    def _acabar(self):
        g = self.placar
        vencedor = None if g[0] == g[1] else (0 if g[0] > g[1] else 1)
        linhas = [t("PLACAR  {a} × {b}", a=g[0], b=g[1])]
        if self.gol_de_ouro:
            linhas.append(t("DECIDIDO NO GOL DE OURO!"))
        self.terminar_multi(vencedor, linhas)

    def calcular_moedas(self, valor, venceu):
        base = self.MOEDAS_PARTIDA + sum(self.placar) // 2
        if venceu:
            base += self.MOEDAS_VITORIA_J1
        return min(self.MOEDAS_MAX, base)

    def _atualizar_jogador(self, jg, dx, pulo, dt_fis, dt, jogando):
        jg.recarga = max(0.0, jg.recarga - dt_fis)
        jg.tonto = max(0.0, jg.tonto - dt_fis)
        jg.congelado = max(0.0, jg.congelado - dt_fis)
        jg.armado = max(0.0, jg.armado - dt_fis)
        jg.espera_toque = max(0.0, jg.espera_toque - dt_fis)
        jg.imune_fogo = max(0.0, jg.imune_fogo - dt_fis)
        jg.pedido_pulo = max(0.0, jg.pedido_pulo - dt)
        jg.pedido_chute = max(0.0, jg.pedido_chute - dt)
        jg.chute = max(0.0, jg.chute - dt_fis)
        if jg.gigante > 0:
            jg.gigante = max(0.0, jg.gigante - dt_fis)
            if jg.gigante <= 0:
                self.textos.adicionar(t("NORMAL"), (jg.x, jg.cy - 70), BRANCO, 12)
        jg.vel_esticar += (-240 * jg.esticar - 11 * jg.vel_esticar) * dt
        jg.esticar = max(-1.0, min(1.0, jg.esticar + jg.vel_esticar * dt))

        if jg.armado > 0 and random.random() < 0.5:
            self.particulas.explodir((jg.x + random.uniform(-jg.raio, jg.raio), jg.cy + jg.raio * 0.6),
                                     [(255, 140, 30), (255, 220, 60)], 1, 40, 0.4, (3, 5), -200)

        livre = jogando and not jg.preso
        jg.vx = dx * VEL_ANDAR if livre else 0.0
        if livre and (jg.pedido_pulo > 0 or pulo) and jg.no_chao:
            jg.vy = -PULO * (0.85 if self.gravidade < 1 else 1.0)
            jg.no_chao = False
            jg.pedido_pulo = 0.0
            jg.vel_esticar += 6.0
            self.som("pulo", 0.5)
        if livre and jg.pedido_chute > 0 and jg.recarga <= 0:
            jg.pedido_chute = 0.0
            jg.chute = CHUTE_TEMPO
            jg.chute_feito = False
            jg.recarga = CHUTE_RECARGA
            self.som("asa", 0.5)

    def _animar_fundo(self, dt):
        # Juiz acompanha a bola devagar
        alvo = min(max(self.bola.x, 380), LARGURA - 380)
        self.juiz_x += max(-60 * dt, min(60 * dt, alvo - self.juiz_x))
        # Totó corre pela arquibancada
        self.toto_x += self.toto_dir * 130 * dt
        if self.toto_x > LARGURA - 30:
            self.toto_dir = -1
        elif self.toto_x < 30:
            self.toto_dir = 1

    # --------------------------------------------------------
    # POWER-UPS (caem de paraquedas)
    # --------------------------------------------------------

    def _atualizar_poder(self, dt):
        if self.poder:
            p = self.poder
            if p[2] < CHAO - 24:
                p[2] = min(CHAO - 24, p[2] + 90 * dt)
            else:
                p[4] -= dt
                if p[4] <= 0:
                    self.poder = None
                    return
            for jg in self.jogs:
                if math.hypot(jg.x - p[1], jg.cy - p[2]) < jg.raio + 24:
                    self._pegar_poder(jg, p[0])
                    self.poder = None
                    return
            return
        self.prox_poder -= dt
        if self.prox_poder <= 0:
            self.prox_poder = PODER_INTERVALO_MALUCO if self.modo["maluco"] else PODER_INTERVALO
            tipo = random.choice(("gigante", "gelo", "praia"))
            self.poder = [tipo, random.uniform(220, LARGURA - 220), 110.0, 0.0, 4.0]

    def _pegar_poder(self, jg, tipo):
        outro = self.jogs[1 - jg.i]
        self.som("moeda")
        self.particulas.explodir((jg.x, jg.cy - 40), [CORES_JOGADOR[jg.i], BRANCO, AMARELO], 14,
                                 220, 0.6, (2, 5), 300)
        if tipo == "gigante":
            jg.gigante = GIGANTE_TEMPO
            jg.vel_esticar += 8.0
            self.textos.adicionar(t("OVO GIGANTE!"), (jg.x, jg.cy - 110), AMARELO, 16)
            jg.x = min(max(jg.x, jg.x_min), jg.x_max)
        elif tipo == "gelo":
            outro.congelado = GELO_TEMPO
            outro.chute = 0.0
            self.som("erro", 0.6)
            self.textos.adicionar(t("CONGELOU!"), (outro.x, outro.cy - 90), (160, 230, 255), 16)
        else:
            self.bola.praia = PRAIA_TEMPO
            self.textos.adicionar(t("BOLA DE PRAIA!"), (self.bola.x, self.bola.y - 60), (255, 200, 90), 14)

    # --------------------------------------------------------
    # FÍSICA
    # --------------------------------------------------------

    def _fisica(self, h):
        g = self.gravidade
        for jg in self.jogs:
            jg.kb *= math.exp(-5.0 * h)
            if abs(jg.kb) < 5:
                jg.kb = 0.0
            jg.x += (jg.vx + jg.kb) * h
            if jg.x < jg.x_min:
                jg.x, jg.kb = jg.x_min, 0.0
            elif jg.x > jg.x_max:
                jg.x, jg.kb = jg.x_max, 0.0
            if not jg.no_chao:
                jg.vy += GRAVIDADE_OVO * g * h
                jg.pes += jg.vy * h
                if jg.pes >= CHAO:
                    impacto = min(1.0, jg.vy / PULO)
                    jg.pes = CHAO
                    jg.vy = 0.0
                    jg.no_chao = True
                    jg.vel_esticar -= 6.0 * impacto

        self._colidir_ovos(*self.jogs)

        if self.fase == "saida":
            # Bola parada no ar; se alguém encostar, a saída acaba
            for jg in self.jogs:
                if self._colidir_bola(jg):
                    self.fase = "jogo"
                    self.tempo_fase = 0.0
            return
        if self.fase == "gol":
            self._mover_bola(h)
            self._mundo_bola()
            return

        self._mover_bola(h)
        self._mundo_bola()
        for jg in self.jogs:
            self._colidir_bola(jg)
            self._tentar_chute(jg)
        self._mundo_bola()
        self._desgrudar()
        self._checar_gol()

    def _colidir_ovos(self, a, b):
        dx, dy = b.x - a.x, b.cy - a.cy
        d = math.hypot(dx, dy)
        minimo = a.raio + b.raio
        if d >= minimo:
            return
        if d < 1e-6:
            dx, dy, d = 1.0, 0.0, 1.0
        nx, ny = dx / d, dy / d
        sobra = minimo - d

        if abs(ny) > 0.6:
            # Um em cima do outro: quem está em cima quica
            de_cima, de_baixo = (a, b) if ny > 0 else (b, a)
            de_cima.pes -= sobra * abs(ny)
            if de_cima.vy > -300:
                de_cima.vy = -520
            de_cima.no_chao = False
            empurra = 1 if de_cima.x >= de_baixo.x else -1
            de_cima.kb += 160 * empurra
            if de_cima.espera_toque <= 0:
                self.som("boing", 0.5)
                de_cima.espera_toque = 0.2
        # Separação para os lados (cada um metade)
        lado = (sobra * abs(nx) + 0.5) / 2
        sx = 1 if dx >= 0 else -1
        a.x -= lado * sx
        b.x += lado * sx
        for jg in (a, b):
            jg.x = min(max(jg.x, jg.x_min), jg.x_max)

    def _mover_bola(self, h):
        b = self.bola
        if b.fogo:
            b.x += b.vx * h
            b.y += b.vy * h
            return
        praia = b.praia > 0
        b.vy += GRAVIDADE_BOLA * self.gravidade * (0.5 if praia else 1.0) * h
        f = math.exp(-(0.8 if praia else ARRASTO) * h)
        b.vx *= f
        b.vy *= f
        if b.y >= CHAO - b.raio - 0.5:
            b.vx *= math.exp(-ROLAMENTO * h)
        v = math.hypot(b.vx, b.vy)
        if v > VEL_MAX_BOLA:
            b.vx *= VEL_MAX_BOLA / v
            b.vy *= VEL_MAX_BOLA / v
        b.x += b.vx * h
        b.y += b.vy * h

    def _mundo_bola(self):
        """Chão, paredes, teto e travessões."""
        b = self.bola
        r = b.raio
        bateu = False
        if b.y > CHAO - r:
            b.y = CHAO - r
            if b.vy > 0:
                forte = b.vy
                q = 0.85 if b.praia > 0 else QUIQUE_CHAO
                b.vy = -b.vy * q
                if abs(b.vy) < 70:
                    b.vy = 0.0
                if forte > 250:
                    b.squash = 0.12
                    if self.fase in ("jogo", "gol"):
                        self.som("bater", min(0.5, forte / 2000))
            bateu = True
        if b.y < TETO + r:
            b.y = TETO + r
            b.vy = abs(b.vy) * 0.6
            bateu = True
        if b.x < r:
            b.x = r
            b.vx = abs(b.vx) * QUIQUE_PAREDE
            bateu = True
        elif b.x > LARGURA - r:
            b.x = LARGURA - r
            b.vx = -abs(b.vx) * QUIQUE_PAREDE
            bateu = True

        for a, c in TRAVES:
            px, py = _ponto_segmento(b.x, b.y, a, c)
            dx, dy = b.x - px, b.y - py
            d = math.hypot(dx, dy)
            minimo = r + ESP_TRAVE
            if d < minimo:
                if d < 1e-6:
                    dx, dy, d = 0.0, -1.0, 1.0
                nx, ny = dx / d, dy / d
                b.x, b.y = px + nx * minimo, py + ny * minimo
                vn = b.vx * nx + b.vy * ny
                if vn < 0:
                    b.vx -= (1 + 0.7) * vn * nx
                    b.vy -= (1 + 0.7) * vn * ny
                    if -vn > 200:
                        self.som("bater", min(0.7, -vn / 1200))
                # Em cima do telhado inclinado a bola sempre escorrega para o campo
                if ny < -0.3:
                    para_campo = 1 if a[0] < LARGURA / 2 else -1
                    if b.vx * para_campo < 60:
                        b.vx = 60 * para_campo
                bateu = True

        if bateu and b.fogo:
            self._apagar_fogo()

    def _apagar_fogo(self):
        b = self.bola
        b.fogo = False
        self.particulas.explodir((b.x, b.y), [(255, 140, 30), (255, 220, 60), (120, 120, 120)],
                                 12, 200, 0.5, (3, 6), 100)

    def _colidir_bola(self, jg):
        """Bola x ovo (círculo x círculo). Devolve True se encostou."""
        b = self.bola
        dx, dy = b.x - jg.x, b.y - jg.cy
        d = math.hypot(dx, dy)
        minimo = jg.raio + b.raio
        if d >= minimo:
            return False
        if d < 1e-6:
            dx, dy, d = 0.0, -1.0, 1.0
        nx, ny = dx / d, dy / d

        # Bola de fogo atropela o adversário
        if b.fogo and jg.imune_fogo <= 0:
            jg.kb = EMPURRAO_FOGO * (1 if b.vx > 0 else -1)
            jg.tonto = TONTO_FOGO
            jg.vel_esticar -= 8.0
            self.tremer(0.3)
            self.som("explosao", 0.7)
            self.textos.adicionar(t("TOMA!"), (jg.x, jg.cy - 90), (255, 150, 60), 18)
            self._apagar_fogo()
            b.vx = -b.vx * 0.3
            b.vy = -300

        # Primeiro separa, depois muda a velocidade
        b.x = jg.x + nx * minimo
        b.y = jg.cy + ny * minimo

        vjx, vjy = jg.vx + jg.kb, jg.vy
        rvx, rvy = b.vx - vjx, b.vy - vjy
        vn = rvx * nx + rvy * ny
        if vn < 0:
            vbn = b.vx * nx + b.vy * ny
            if vbn < 0:
                b.vx -= (1 + QUIQUE_OVO) * vbn * nx
                b.vy -= (1 + QUIQUE_OVO) * vbn * ny
            b.vx += SOMA_OVO * vjx
            b.vy += SOMA_OVO * vjy
            saida = (b.vx - vjx) * nx + (b.vy - vjy) * ny
            if saida < SAIDA_MIN:
                b.vx += (SAIDA_MIN - saida) * nx
                b.vy += (SAIDA_MIN - saida) * ny
            self._toque(jg, -vn, (b.x - nx * b.raio, b.y - ny * b.raio))

        # Bola em cima da cabeça
        if ny < -0.6:
            b.toque_cabeca = 0.0

        # SUPER armado: o próximo toque vira bola de fogo
        if jg.armado > 0:
            self._super_chute(jg)
        return True

    def _toque(self, jg, forca, ponto):
        if jg.espera_toque > 0:
            return
        jg.espera_toque = 0.3
        jg.medidor = min(1.0, jg.medidor + SUPER_TOQUE)
        jg.vel_esticar -= min(5.0, 1.5 + forca / 300)
        if self.fase in ("jogo", "saida"):
            self.som("bater", min(1.0, 0.35 + forca / 1200))
            self.particulas.explodir(ponto, [BRANCO, (230, 255, 230)], 5, 120, 0.3, (2, 4), 200)
            if jg.medidor >= 1.0 and jg.armado <= 0:
                self.textos.adicionar(t("SUPER PRONTO!"), (jg.x, jg.cy - 100), AMARELO, 12)

    def _tentar_chute(self, jg):
        if jg.chute <= 0 or jg.chute_feito or jg.preso:
            return
        b = self.bola
        pe_x = jg.x + jg.lado * jg.raio * 0.6
        pe_y = jg.pes - 12 * jg.escala
        frente = (b.x - jg.x) * jg.lado
        if frente < -10 or b.y < jg.cy - 20 * jg.escala:
            return
        if math.hypot(b.x - pe_x, b.y - pe_y) > CHUTE_ALCANCE * jg.escala + b.raio * 0.5:
            return
        jg.chute_feito = True
        if jg.armado > 0:
            self._super_chute(jg)
            return
        leve = 1.15 if b.praia > 0 else 1.0
        b.vx = (CHUTE_VEL[0] * jg.lado + 0.5 * jg.vx) * leve
        b.vy = CHUTE_VEL[1] * leve
        b.fogo = False
        self.som("mola", 0.7)
        self._toque(jg, 700, (b.x, b.y))
        self.particulas.explodir((b.x - jg.lado * b.raio, b.y + 6), [BRANCO, (200, 240, 200)], 6,
                                 160, 0.3, (2, 4), 200)

    def _super_chute(self, jg):
        b = self.bola
        jg.armado = 0.0
        jg.medidor = 0.0
        jg.imune_fogo = 0.3
        b.fogo = True
        b.vx = SUPER_VEL * jg.lado
        b.vy = 0.0
        # Não sai de dentro do chão/teto
        b.y = min(max(b.y, TETO + b.raio + 2), CHAO - b.raio - 2)
        self.som("explosao", 0.8)
        self.tremer(0.2)
        self.textos.adicionar(t("SUPER-CHUTE!"), (jg.x, jg.cy - 100), (255, 140, 40), 18)
        self.particulas.explodir((b.x, b.y), [(255, 140, 30), (255, 220, 60), (230, 60, 30)], 18,
                                 300, 0.5, (3, 6), 0)

    def _desgrudar(self):
        """Bola espremida (contra o chão ou entre os ovos) é empurrada para fora."""
        b = self.bola
        dentro = []
        for jg in self.jogs:
            if math.hypot(b.x - jg.x, b.y - jg.cy) < jg.raio + b.raio - 0.5:
                dentro.append(jg)
        if not dentro:
            return
        if len(dentro) == 2:
            # Entre os dois: a bola "espirra" para cima
            topo = min(jg.cy - math.sqrt(max(0.0, (jg.raio + b.raio) ** 2 - (b.x - jg.x) ** 2))
                       for jg in dentro)
            b.y = max(TETO + b.raio, topo - 1)
            b.vy = min(b.vy, -450)
            return
        jg = dentro[0]
        dx, dy = jg.x - b.x, jg.cy - b.y
        d = math.hypot(dx, dy)
        if d < 1e-6:
            dx, dy, d = 0.0, -1.0, 1.0
        nx, ny = dx / d, dy / d
        sobra = jg.raio + b.raio - d + 0.5
        # O ovo é que sai (pisou na bola: dá um pulinho)
        jg.x = min(max(jg.x + nx * sobra, jg.x_min), jg.x_max)
        if ny < -0.3:
            jg.pes += ny * sobra
            if jg.pes < CHAO:
                jg.no_chao = False
                jg.vy = min(jg.vy, -250)
        # Se o ovo não conseguiu sair (parede), a bola pula por cima
        if math.hypot(b.x - jg.x, b.y - jg.cy) < jg.raio + b.raio - 1:
            topo = jg.cy - math.sqrt(max(0.0, (jg.raio + b.raio) ** 2 - (b.x - jg.x) ** 2))
            b.y = max(TETO + b.raio, topo - 1)
            b.vy = min(b.vy, -400)

    def _checar_gol(self):
        b = self.bola
        if self.fase != "jogo":
            return
        # Câmera lenta: a bola passa raspando a trave
        if self.espera_lento <= 0 and math.hypot(b.vx, b.vy) > 350:
            for px, py in PONTAS:
                if math.hypot(b.x - px, b.y - py) < b.raio + ESP_TRAVE + 30:
                    self.lento = 0.3
                    self.espera_lento = 1.5
                    self.textos.adicionar("UH!", (px, py - 60), BRANCO, 16)
                    break
        if b.y > GOL_TOPO:
            if b.x < GOL_L - 6:
                self._gol(1)
            elif b.x > LARGURA - GOL_L + 6:
                self._gol(0)

    def _gol(self, quem):
        self.placar[quem] += 1
        self.quem_marcou = quem
        self.fase = "gol"
        self.tempo_fase = 0.0
        self.bola.fogo = False
        lado_gol = 0 if quem == 1 else 1
        self.rede[lado_gol] = 1.2
        self.som("ponto")
        self.som("vencer", 0.5)
        self.tremer(0.4)
        x = GOL_L // 2 if quem == 1 else LARGURA - GOL_L // 2
        for k in range(4):
            self.particulas.explodir((x + random.uniform(-40, 40), 420 + k * 50),
                                     [self.cor(quem), CORES_JOGADOR[quem], BRANCO, AMARELO],
                                     14, 420, 1.2, (3, 6), 400)
        self.jogs[quem].vel_esticar += 8.0
        if self.gol_de_ouro:
            self._banner(t("GOL DE OURO!"), AMARELO, TEMPO_GOL, 24)

    # --------------------------------------------------------
    # DESENHO
    # --------------------------------------------------------

    def desenhar_jogo(self, tela):
        tela.blit(self.fundo(self.jogador), (0, 0))
        t = self.tempo

        self._desenhar_torcida(tela, t)
        self._desenhar_toto(tela, t)
        self._desenhar_juiz(tela, t)

        # Power-up de paraquedas
        if self.poder:
            self._desenhar_poder(tela, t)

        # Sombras
        b = self.bola
        for jg in self.jogs:
            larg = jg.raio * 2 * max(0.4, 1 - (CHAO - jg.pes) / 400)
            s = _alpha((int(larg), max(6, int(larg / 5))), (30, 80, 30), 90)
            tela.blit(s, s.get_rect(center=(int(jg.x), CHAO + 2)))
        larg = b.raio * 2 * max(0.3, 1 - (CHAO - b.raio - b.y) / 500)
        s = _alpha((int(larg), max(4, int(larg / 4))), (30, 80, 30), 90)
        tela.blit(s, s.get_rect(center=(int(b.x), CHAO + 2)))

        for jg in self.jogs:
            self._desenhar_jogador(tela, jg, t)
        self._desenhar_bola(tela, t)
        self._desenhar_gols(tela, t)

        self.particulas.desenhar(tela)
        self._desenhar_banner(tela)
        self._desenhar_gooool(tela)
        self.textos.desenhar(tela)

    def _desenhar_torcida(self, tela, t):
        ola = None
        if self.fase == "gol":
            ola = -100 + self.tempo_fase * 700
        for x, y, lado, k, fase in self.lugares:
            dy = math.sin(t * 4 + fase) * 2
            dx = math.sin(t * 2 + fase) * 2
            if ola is not None:
                dy -= 22 * math.exp(-((x - ola) / 70) ** 2)
                if lado == self.quem_marcou:
                    dy -= abs(math.sin(t * 10 + fase)) * 6
            s = self._torcida[lado][k]
            tela.blit(s, (x - 12 + dx, y - 22 + dy))

    def _desenhar_toto(self, tela, t):
        """O cachorrinho Totó correndo pela arquibancada."""
        x = self.toto_x
        pulo = abs(math.sin(t * 12)) * 4
        if self.fase == "gol":
            pulo = abs(math.sin(t * 8)) * 14
        y = 156 - pulo
        d = self.toto_dir
        marrom = (170, 115, 60)
        escuro = (110, 70, 35)
        for k, fase in enumerate((0, math.pi)):
            px = x + (-8 + k * 14) * d + math.sin(t * 16 + fase) * 3
            pygame.draw.line(tela, escuro, (x + (-8 + k * 14) * d, y - 6), (px, y), 3)
        pygame.draw.ellipse(tela, marrom, (x - 13, y - 16, 26, 13))
        cabeca = (x + 13 * d, y - 18)
        pygame.draw.circle(tela, marrom, (int(cabeca[0]), int(cabeca[1])), 7)
        pygame.draw.ellipse(tela, escuro, (cabeca[0] - 3 - 4 * d, cabeca[1] - 6, 6, 11))
        pygame.draw.circle(tela, (20, 20, 20), (int(cabeca[0] + 3 * d), int(cabeca[1] - 1)), 2)
        pygame.draw.circle(tela, (20, 20, 20), (int(cabeca[0] + 7 * d), int(cabeca[1] + 2)), 2)
        rabo = math.sin(t * 20) * 5
        pygame.draw.line(tela, escuro, (x - 12 * d, y - 12), (x - 20 * d, y - 18 + rabo), 3)

    def _desenhar_juiz(self, tela, t):
        """O ROBERT de juiz: bonequinho de palito com boné arco-íris e apito."""
        x = int(self.juiz_x)
        pes = 468
        comemora = self.fase in ("gol", "apito")
        passo = math.sin(t * 6) * 5 if not comemora else 0
        cor = (40, 40, 50)
        quadril = (x, pes - 24)
        ombro = (x, pes - 48)
        cabeca = (x, pes - 60)
        pygame.draw.line(tela, cor, quadril, (x - 7 + passo, pes), 3)
        pygame.draw.line(tela, cor, quadril, (x + 7 - passo, pes), 3)
        pygame.draw.line(tela, cor, quadril, ombro, 3)
        # Camisa listrada de juiz
        camisa = pygame.Rect(x - 7, pes - 48, 14, 22)
        pygame.draw.rect(tela, (250, 250, 250), camisa, border_radius=3)
        for k in range(3):
            pygame.draw.line(tela, cor, (camisa.x + 3 + k * 4, camisa.y + 1), (camisa.x + 3 + k * 4, camisa.bottom - 2), 2)
        if comemora:
            balanco = math.sin(t * 10) * 4
            pygame.draw.line(tela, cor, ombro, (x - 16, pes - 72 + balanco), 3)
            pygame.draw.line(tela, cor, ombro, (x + 16, pes - 72 - balanco), 3)
        else:
            pygame.draw.line(tela, cor, ombro, (x - 12, pes - 30 - passo * 0.5), 3)
            pygame.draw.line(tela, cor, ombro, (x + 12, pes - 30 + passo * 0.5), 3)
        pygame.draw.circle(tela, (255, 220, 180), cabeca, 10)
        pygame.draw.circle(tela, cor, cabeca, 10, 2)
        pygame.draw.circle(tela, cor, (x + 3, pes - 61), 1)
        # Boné arco-íris
        for k, c in enumerate([(230, 60, 60), (255, 160, 40), (255, 230, 60), (80, 190, 80),
                               (60, 130, 230), (150, 80, 200)]):
            pygame.draw.arc(tela, c, (x - 11 + k, pes - 73 + k, 22 - 2 * k, 20 - 2 * k), 0, math.pi, 2)
        pygame.draw.line(tela, (60, 130, 230), (x, pes - 64), (x + 15, pes - 64), 3)
        # Apito
        pygame.draw.rect(tela, (200, 200, 210), (x + 8, pes - 58, 6, 4))

    def _desenhar_poder(self, tela, t):
        tipo, x, y, _, vida = self.poder
        if y >= CHAO - 24 and vida < 1.2 and int(t * 8) % 2 == 0:
            return
        balanco = math.sin(t * 3) * 6 if y < CHAO - 24 else 0
        x = x + balanco
        # Paraquedas enquanto cai
        if y < CHAO - 24:
            topo = (x, y - 62)
            pygame.draw.line(tela, (80, 80, 90), (x - 26, y - 56), (x - 10, y - 18), 1)
            pygame.draw.line(tela, (80, 80, 90), (x + 26, y - 56), (x + 10, y - 18), 1)
            pygame.draw.line(tela, (80, 80, 90), (x, y - 56), (x, y - 22), 1)
            cupula = pygame.Rect(0, 0, 60, 36)
            cupula.midtop = (topo[0], topo[1] - 10)
            pygame.draw.ellipse(tela, (255, 110, 110), cupula)
            pygame.draw.line(tela, (255, 255, 255), (cupula.centerx, cupula.top + 2),
                             (cupula.centerx, cupula.centery), 3)
            pygame.draw.ellipse(tela, (150, 40, 40), cupula, 2)
        centro = (int(x), int(y))
        pygame.draw.circle(tela, (255, 250, 230), centro, 22)
        pygame.draw.circle(tela, AMARELO, centro, 22, 3)
        if tipo == "gigante":
            self.desenhar_ovo(tela, 0, (x - 4, y + 3), 24)
            pygame.draw.polygon(tela, (230, 60, 60), [(x + 12, y - 12), (x + 6, y - 2), (x + 18, y - 2)])
            pygame.draw.rect(tela, (230, 60, 60), (x + 10, y - 3, 4, 10))
        elif tipo == "gelo":
            for k in range(3):
                a = k * math.pi / 3
                dx, dy = math.cos(a) * 14, math.sin(a) * 14
                pygame.draw.line(tela, (80, 170, 230), (x - dx, y - dy), (x + dx, y + dy), 3)
            pygame.draw.circle(tela, (160, 220, 255), centro, 4)
        else:
            s = _bola_sup(13, True)
            tela.blit(s, s.get_rect(center=centro))

    def _desenhar_jogador(self, tela, jg, t):
        esc = jg.escala
        altura = int(ALTURA_OVO * esc)
        sup = self._avatar_de(jg.i, altura)
        esp = jg.lado < 0
        if esp:
            sup = pygame.transform.flip(sup, True, False)
        e = jg.esticar
        sx, sy = 1 - 0.12 * e, 1 + 0.14 * e
        if abs(e) > 0.02:
            w, h = sup.get_size()
            sup = pygame.transform.smoothscale(sup, (max(2, round(w * sx)), max(2, round(h * sy))))
        else:
            sx = sy = 1.0
        if jg.tonto > 0:
            sup = pygame.transform.rotate(sup, math.sin(t * 14) * 10)

        # Chuteirinhas
        self._desenhar_botas(tela, jg)

        altura_vista = altura * sy
        base_ovo = jg.pes - BOTA * esc
        centro = (jg.x, base_ovo - altura_vista / 2)
        tela.blit(sup, sup.get_rect(center=(round(centro[0]), round(centro[1] - sup.get_height() * 0.01))))

        # Super armado: anel de fogo
        if jg.armado > 0:
            for k in range(8):
                a = t * 6 + k * math.tau / 8
                px = jg.x + math.cos(a) * jg.raio * 1.05
                py = jg.cy + math.sin(a) * jg.raio * 1.15
                cor = (255, 140, 30) if k % 2 else (255, 220, 60)
                pygame.draw.circle(tela, cor, (int(px), int(py)), 6 + int(2 * math.sin(t * 20 + k)))
        # Congelado: bloco de gelo
        if jg.congelado > 0:
            r = pygame.Rect(0, 0, int(jg.raio * 2.3), int(altura * 1.05 + BOTA * esc))
            r.midbottom = (int(jg.x), int(jg.pes) + 2)
            tela.blit(_alpha(r.size, (170, 230, 255), 130, elipse=False), r)
            pygame.draw.rect(tela, (230, 250, 255), r, 3, border_radius=6)
            pygame.draw.line(tela, BRANCO, (r.x + 10, r.y + 12), (r.x + 26, r.y + 30), 3)
            pygame.draw.line(tela, BRANCO, (r.x + 10, r.y + 26), (r.x + 18, r.y + 36), 2)
        # Tonto: estrelinhas
        if jg.tonto > 0:
            for k in range(3):
                a = t * 7 + k * math.tau / 3
                ui.estrela(tela, (jg.x + math.cos(a) * 30 * esc, base_ovo - altura - 8 + math.sin(a) * 8),
                           7, AMARELO, a)
        # Gigante acabando: pisca um aviso
        if 0 < jg.gigante < 1.5 and int(t * 8) % 2 == 0:
            ui.desenhar_texto(tela, "!", (jg.x, base_ovo - altura - 14), 16, AMARELO, "midbottom")

    def _desenhar_botas(self, tela, jg):
        esc = jg.escala
        f = jg.lado
        cor = self.cor(jg.i)
        cor = cor if sum(cor) < 700 else (235, 235, 240)
        contorno = ui.escurecer(cor, 90) if sum(cor) < 600 else (110, 110, 130)
        # Ângulo do chute: o pé da frente gira para frente e para cima
        giro = 0.0
        if jg.chute > 0:
            giro = math.sin(math.pi * (1 - jg.chute / CHUTE_TEMPO)) * 1.1
        for k, (ox, frente) in enumerate(((-12, False), (10, True))):
            pivo = (jg.x + ox * f * esc, jg.pes - BOTA * esc - 8 * esc)
            pontos = [(-8, 6), (10, 6), (19, 11), (20, 18), (-8, 18)]
            a = -giro * f if frente else 0.0
            ca, sa = math.cos(a), math.sin(a)
            tela_pts = []
            for px, py in pontos:
                px *= f * esc
                py *= esc
                tela_pts.append((pivo[0] + px * ca - py * sa, pivo[1] + px * sa + py * ca))
            c = cor if frente else ui.escurecer(cor, 30)
            pygame.draw.polygon(tela, c, tela_pts)
            pygame.draw.polygon(tela, contorno, tela_pts, 2)
            # Sola branca
            pygame.draw.line(tela, BRANCO, tela_pts[3], tela_pts[4], 2)

    def _desenhar_bola(self, tela, t):
        b = self.bola
        praia = b.praia > 0
        sup = _bola_fogo(b.raio, praia) if b.fogo else _bola_sup(b.raio, praia)
        if b.angulo:
            sup = pygame.transform.rotate(sup, b.angulo % 360)
        if b.squash > 0:
            k = b.squash / 0.12
            w, h = sup.get_size()
            sup = pygame.transform.smoothscale(sup, (int(w * (1 + 0.25 * k)), int(h * (1 - 0.22 * k))))
            tela.blit(sup, sup.get_rect(midbottom=(round(b.x), round(b.y + b.raio + 2))))
        else:
            tela.blit(sup, sup.get_rect(center=(round(b.x), round(b.y))))
        if self.fase == "saida" and self.estado == "jogando":
            raio = b.raio + 6 + int(abs(math.sin(t * 6)) * 5)
            pygame.draw.circle(tela, BRANCO, (round(b.x), round(b.y)), raio, 2)

    def _desenhar_gols(self, tela, t):
        for lado in (0, 1):
            onda = self.rede[lado]
            def X(x):
                return x if lado == 0 else LARGURA - x
            # Rede (grade de linhas brancas), ondulando depois de um gol
            for k in range(0, GOL_L + 1, 12):
                desl = math.sin(t * 20 + k * 0.3) * 6 * onda
                topo = TELHADO_Y + (GOL_TOPO - TELHADO_Y) * k / GOL_L
                pygame.draw.line(tela, (255, 255, 255), (X(k + desl), topo), (X(k - desl), CHAO), 2)
            for y in range(GOL_TOPO + 12, CHAO, 14):
                desl = math.sin(t * 20 + y * 0.1) * 6 * onda
                pygame.draw.line(tela, (255, 255, 255), (X(0), y + desl), (X(GOL_L), y - desl), 2)
            for k in range(1, 3):
                y = TELHADO_Y + (GOL_TOPO - TELHADO_Y) * k / 3
                pygame.draw.line(tela, (255, 255, 255), (X(0), y), (X(GOL_L * k / 3), y), 1)
            # Traves
            pygame.draw.line(tela, COR_TRAVE, (X(0), TELHADO_Y), (X(GOL_L), GOL_TOPO), 8)
            pygame.draw.line(tela, COR_TRAVE, (X(0), GOL_TOPO), (X(GOL_L), GOL_TOPO), 8)
            pygame.draw.line(tela, COR_TRAVE, (X(GOL_L), GOL_TOPO), (X(GOL_L), CHAO), 8)
            pygame.draw.line(tela, (170, 170, 180), (X(GOL_L) + (3 if lado == 0 else -3), GOL_TOPO),
                             (X(GOL_L) + (3 if lado == 0 else -3), CHAO), 2)
            pygame.draw.circle(tela, COR_TRAVE, (X(GOL_L), GOL_TOPO), 6)

    def _desenhar_banner(self, tela):
        if not self.banner or self.estado != "jogando":
            return
        texto, cor, resta, tam, total = self.banner
        entrada = min(1.0, (total - resta) * 6)
        tam_atual = tam if entrada >= 1 else max(12, int(tam * (0.6 + 0.4 * entrada)))
        sup = ui.texto(texto, tam_atual, cor)
        r = sup.get_rect(center=(LARGURA // 2, 140))
        ui.painel(tela, r.inflate(36, 24), (20, 24, 40), cor, 14, 3, sombra=False)
        tela.blit(sup, r)

    def _desenhar_gooool(self, tela):
        if self.fase != "gol" or self.estado != "jogando":
            return
        letras = t("GOOOOL!")
        n = min(len(letras), int(self.tempo_fase / 0.09) + 1)
        texto = letras[:n]
        cor = CORES_JOGADOR[self.quem_marcou]
        balanco = 1 + 0.08 * math.sin(self.tempo_fase * 16)
        tam = int(56 * balanco) // 4 * 4
        sup = ui.texto(texto, tam, AMARELO)
        # Alinhado pela esquerda para as letras "nascerem" no lugar
        largura_total = ui.texto(letras, 56, AMARELO).get_width()
        x0 = LARGURA // 2 - largura_total // 2
        painel = pygame.Rect(0, 0, largura_total + 60, 130)
        painel.center = (LARGURA // 2, 258)
        ui.painel(tela, painel, (20, 24, 40), cor, 18, 4, sombra=False)
        tela.blit(sup, sup.get_rect(midleft=(x0, 240)))
        if self.tempo_fase > 0.5:
            ui.desenhar_texto(tela, self.nome(self.quem_marcou), (LARGURA // 2, 296), 16, cor, "center")

    def desenhar_hud(self, tela):
        caixa = pygame.Rect(0, 6, 600, 72)
        caixa.centerx = LARGURA // 2
        ui.painel(tela, caixa, (20, 24, 40), BRANCO, 14, 3, sombra=False)
        for i in (0, 1):
            lado = -1 if i == 0 else 1
            jg = self.jogs[i]
            sup = self._mini[i]
            if i == 1:
                sup = pygame.transform.flip(sup, True, False)
            tela.blit(sup, sup.get_rect(center=(caixa.centerx + lado * 272, caixa.centery)))
            ancora = "midleft" if i == 0 else "midright"
            x = caixa.centerx + lado * 246
            ui.desenhar_texto(tela, self.nome(i)[:10], (x, caixa.y + 20), 12, CORES_JOGADOR[i], ancora)
            # Medidor do SUPER
            barra = pygame.Rect(0, 0, 130, 12)
            if i == 0:
                barra.midleft = (x, caixa.y + 46)
            else:
                barra.midright = (x, caixa.y + 46)
            pygame.draw.rect(tela, (50, 56, 80), barra, border_radius=5)
            cheio = jg.medidor >= 1.0
            cor = (255, 140, 40) if cheio else (255, 214, 64)
            if cheio and int(self.tempo * 6) % 2 == 0:
                cor = (255, 230, 120)
            larg = int(barra.w * jg.medidor)
            if larg > 0:
                parte = pygame.Rect(barra.x, barra.y, larg, barra.h)
                if i == 1:
                    parte.right = barra.right
                pygame.draw.rect(tela, cor, parte, border_radius=5)
            pygame.draw.rect(tela, BRANCO, barra, 2, border_radius=5)
            rotulo = t("SUPER!") if cheio else t("SUPER")
            ui.desenhar_texto(tela, rotulo, barra.center, 10, (40, 30, 20) if cheio else BRANCO,
                              "center", sombra=not cheio)
            ui.desenhar_texto(tela, str(self.placar[i]), (caixa.centerx + lado * 44, caixa.y + 30), 32,
                              AMARELO, "center")
        ui.desenhar_texto(tela, "×", (caixa.centerx, caixa.y + 30), 20, BRANCO, "center")
        if self.gol_de_ouro:
            info, cor = t("GOL DE OURO"), AMARELO
        elif self.modo["tempo"] is None:
            info, cor = t("ATÉ {n}", n=self.modo['gols']), (180, 200, 255)
        else:
            info = self.formatar(math.ceil(self.relogio))
            cor = (255, 150, 150) if self.relogio <= 10 else BRANCO
        ui.desenhar_texto(tela, info, (caixa.centerx, caixa.bottom - 14), 12, cor, "center")

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
            ui.desenhar_texto(tela, ctrl, (x, y_ovos + 64), 10, BRANCO, "midtop")
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
