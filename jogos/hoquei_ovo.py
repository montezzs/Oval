import math
import random

import pygame

from settings import *
from core import ui
from core.idioma import t
from jogos.base_multi import MiniJogoMulti, TECLAS_MOVER, TECLAS_ACAO, CORES_JOGADOR

# ============================================================
# HÓQUEI DE OVOS (2 JOGADORES)
# ============================================================
# Mesa de air hockey no gelo, vista de cima. Cada jogador É o
# rebatedor (o próprio ovo em cima de um disco) e o "disco" é um
# LIMÃO. Cada um fica na sua metade da mesa. A TACADA FORTE deixa
# o limão pegando fogo ("LIMÃO QUENTE"). Se ninguém fizer gol por
# 30 segundos, entra um SEGUNDO LIMÃO!

# Mesa (retângulo com cantos arredondados)
MESA = pygame.Rect(60, 96, 904, 590)
RAIO_CANTO = 60
BORDA = 14
MEIO_X = LARGURA // 2
GOL_Y = MESA.centery                   # 391
GOL_ABERTURA = 200
GOL_TOPO = GOL_Y - GOL_ABERTURA // 2   # 291
GOL_BASE = GOL_Y + GOL_ABERTURA // 2   # 491
GOL_FUNDO = 44                         # profundidade do bolsão do gol
RAIO_POSTE = 4

# Rebatedores (os ovos)
R_REB = 42
ALTURA_OVO = 76
ACELERACAO = 4800
VEL_MAX_REB = 560
ATRITO_REB = 8.5
CASA = [(MESA.left + 110, GOL_Y), (MESA.right - 110, GOL_Y)]

# Limão (disco)
R_LIMAO = 22
ATRITO_LIMAO = 0.3
VEL_MAX_LIMAO = 1100
QUIQUE_PAREDE = 0.95
QUIQUE_REB = 0.9
SOMA_REB = 1.1                         # quanto da velocidade do rebatedor vai pro limão
SAIDA_MIN = 90                         # o limão sempre se afasta do ovo depois do toque

# Tacada forte
TACADA_JANELA = 0.2
TACADA_RECARGA = 1.0
TACADA_BONUS = 1.4
VEL_QUENTE = 380                       # abaixo disso o limão "esfria"

TEMPO_DOIS_LIMOES = 30.0
TEMPO_PARADO = 3.0                     # limão parado muito tempo leva um empurrão
TEMPO_GOL = 1.5
TEMPO_SAQUE = 0.9

SUB_PASSO = 1 / 240                    # 4 passos por frame: nada atravessa nada

METAS = [5, 7, 10]

# Cantos arredondados: (centro do arco, sinal x, sinal y)
CANTOS = [
    ((MESA.left + RAIO_CANTO, MESA.top + RAIO_CANTO), -1, -1),
    ((MESA.right - RAIO_CANTO, MESA.top + RAIO_CANTO), 1, -1),
    ((MESA.left + RAIO_CANTO, MESA.bottom - RAIO_CANTO), -1, 1),
    ((MESA.right - RAIO_CANTO, MESA.bottom - RAIO_CANTO), 1, 1),
]
POSTES = [(MESA.left, GOL_TOPO), (MESA.left, GOL_BASE),
          (MESA.right, GOL_TOPO), (MESA.right, GOL_BASE)]

COR_GELO = (225, 240, 255)
COR_RISCO = (205, 225, 245)
COR_BORDA = (40, 60, 120)
COR_BRILHO = (90, 120, 200)

_cache = {}

# Giros do limão pré-desenhados (rotate a cada frame pesa)
PASSOS_GIRO = 48
# Squash do ovo em degraus (smoothscale a cada frame pesa)
PASSOS_ESTICAR = 12


def _circulo_alpha(raio, cor, alpha):
    chave = ("c", raio, cor, alpha)
    s = _cache.get(chave)
    if s is None:
        s = pygame.Surface((raio * 2 + 2, raio * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*cor, alpha), (raio + 1, raio + 1), raio)
        _cache[chave] = s
    return s


def _limao_girado(raio, quente, angulo):
    passo = int((angulo % 360) / 360 * PASSOS_GIRO) % PASSOS_GIRO
    chave = ("giro", raio, quente, passo)
    s = _cache.get(chave)
    if s is None:
        base = _limao_quente(raio) if quente else ui.limao_sup(raio)
        s = pygame.transform.rotate(base, passo * 360 / PASSOS_GIRO)
        _cache[chave] = s
    return s


def _limao_quente(raio):
    chave = ("quente", raio)
    s = _cache.get(chave)
    if s is None:
        s = ui.limao_sup(raio).copy()
        s.fill((255, 150, 70), special_flags=pygame.BLEND_RGB_MULT)
        s.fill((40, 0, 0), special_flags=pygame.BLEND_RGB_ADD)
        _cache[chave] = s
    return s


# ============================================================
# PEÇAS
# ============================================================

class Rebatedor:

    def __init__(self, i):
        self.i = i
        self.x, self.y = CASA[i]
        self.vx = self.vy = 0.0
        self.janela = 0.0          # tacada forte ativa
        self.recarga = 0.0
        self.esticar = 0.0
        self.vel_esticar = 0.0
        self.choro = 0.0
        self.espera_som = 0.0
        self.entrada = (0, 0)

    @property
    def x_min(self):
        return MESA.left + R_REB if self.i == 0 else MEIO_X + R_REB

    @property
    def x_max(self):
        return MEIO_X - R_REB if self.i == 0 else MESA.right - R_REB


class Limao:

    def __init__(self, x, y, vx=0.0, vy=0.0):
        self.x, self.y = float(x), float(y)
        self.vx, self.vy = float(vx), float(vy)
        self.quente = False
        self.angulo = 0.0
        self.rastro = []
        self.parado = 0.0
        self.no_gol = None         # lado do gol em que entrou (0 = esquerdo)


# ============================================================
# JOGO
# ============================================================

class HoqueiOvo(MiniJogoMulti):

    ID = "hoquei_ovo"
    TITULO = "HÓQUEI DE OVOS"
    TITULO_CURTO = "HÓQUEI"
    DESCRICAO = "Air hockey no gelo! Seu ovo é o rebatedor e o disco é um limão. Faça gol no amigo!"
    COR = (60, 120, 230)
    INSTRUCOES = [
        "Rebata o LIMÃO e faça gol do outro lado! Cada um na sua metade.",
        "TACADA FORTE: aperte na hora da batida e o limão pega fogo!",
        "30 segundos sem gol? Entra um SEGUNDO LIMÃO!",
        "J1: WASD + ESPAÇO/F tacada • J2: SETAS + ENTER/. tacada",
    ]
    OPCOES = ["ATÉ 5", "ATÉ 7", "ATÉ 10"]
    CONTROLES_J1 = "WASD + ESPAÇO"
    CONTROLES_J2 = "SETAS + ENTER"
    CONTAGEM = True

    MOEDAS_PARTIDA = 8
    MOEDAS_VITORIA_J1 = 5
    MOEDAS_MAX = 18

    # --------------------------------------------------------
    # CENÁRIO: arena com a mesa de gelo
    # --------------------------------------------------------

    @classmethod
    def criar_fundo(cls, jogador):
        sup = ui.gradiente(LARGURA, ALTURA, (34, 44, 80), (14, 18, 36))
        rnd = random.Random(61)

        # Luzes da arena lá no fundo
        for _ in range(70):
            x, y = rnd.randrange(LARGURA), rnd.randrange(ALTURA)
            pygame.draw.circle(sup, rnd.choice([(60, 70, 120), (80, 90, 140), (50, 60, 100)]),
                               (x, y), rnd.choice((1, 2, 2, 3)))

        # Bolsões dos gols (atrás da mesa)
        for lado in (0, 1):
            bolsao = pygame.Rect(0, GOL_TOPO - 10, GOL_FUNDO + 12, GOL_ABERTURA + 20)
            if lado == 0:
                bolsao.right = MESA.left + 2
            else:
                bolsao.left = MESA.right - 2
            pygame.draw.rect(sup, (230, 60, 60), bolsao, border_radius=10)
            dentro = bolsao.inflate(-12, -20)
            if lado == 0:
                dentro.right = bolsao.right
            else:
                dentro.left = bolsao.left
            pygame.draw.rect(sup, (30, 34, 50), dentro)
            for x in range(dentro.left, dentro.right, 8):
                pygame.draw.line(sup, (90, 96, 120), (x, dentro.top), (x, dentro.bottom - 1), 1)
            for y in range(dentro.top, dentro.bottom, 8):
                pygame.draw.line(sup, (90, 96, 120), (dentro.left, y), (dentro.right - 1, y), 1)

        # Borda da mesa
        fora = MESA.inflate(BORDA * 2, BORDA * 2)
        pygame.draw.rect(sup, (10, 12, 24), fora.move(6, 8), border_radius=RAIO_CANTO + BORDA)
        pygame.draw.rect(sup, COR_BORDA, fora, border_radius=RAIO_CANTO + BORDA)

        # Gelo
        pygame.draw.rect(sup, COR_GELO, MESA, border_radius=RAIO_CANTO)
        gelo = pygame.Surface(MESA.size, pygame.SRCALPHA)
        for _ in range(140):
            x, y = rnd.randrange(MESA.w), rnd.randrange(MESA.h)
            comp = rnd.randint(10, 50)
            a = rnd.uniform(0, math.pi)
            pygame.draw.line(gelo, (*COR_RISCO, 255), (x, y),
                             (x + math.cos(a) * comp, y + math.sin(a) * comp), 1)
        # Furinhos de ar da mesa
        for y in range(24, MESA.h, 36):
            for x in range(24 + (y // 36 % 2) * 18, MESA.w, 36):
                pygame.draw.circle(gelo, (200, 215, 238, 255), (x, y), 2)
        mascara = pygame.Surface(MESA.size, pygame.SRCALPHA)
        pygame.draw.rect(mascara, (255, 255, 255, 255), mascara.get_rect(), border_radius=RAIO_CANTO)
        gelo.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        sup.blit(gelo, MESA.topleft)

        # Áreas dos gols (semicírculos azul claro)
        area = pygame.Surface(MESA.size, pygame.SRCALPHA)
        for cx in (0, MESA.w):
            pygame.draw.circle(area, (170, 210, 255, 255), (cx, GOL_Y - MESA.top), 110)
            pygame.draw.circle(area, (60, 120, 230, 255), (cx, GOL_Y - MESA.top), 110, 4)
        sup.blit(area, MESA.topleft)

        # Linha central vermelha e círculo central azul
        pygame.draw.line(sup, (230, 60, 60), (MEIO_X, MESA.top), (MEIO_X, MESA.bottom - 1), 6)
        pygame.draw.circle(sup, (60, 120, 230), (MEIO_X, GOL_Y), 90, 4)
        pygame.draw.circle(sup, (60, 120, 230), (MEIO_X, GOL_Y), 10)
        for x in (MESA.left + 250, MESA.right - 250):
            for y in (GOL_Y - 160, GOL_Y + 160):
                pygame.draw.circle(sup, (230, 60, 60), (x, y), 8)
                pygame.draw.circle(sup, (230, 60, 60), (x, y), 26, 2)

        # Brilho interno da borda
        pygame.draw.rect(sup, COR_BRILHO, MESA.inflate(6, 6), 3, border_radius=RAIO_CANTO + 3)

        # Abertura dos gols na borda (a borda some ali)
        for x in (MESA.left - BORDA - 2, MESA.right - 2):
            pygame.draw.rect(sup, (30, 34, 50), (x, GOL_TOPO, BORDA + 4, GOL_ABERTURA))
        pygame.draw.line(sup, (230, 60, 60), (MESA.left, GOL_TOPO), (MESA.left, GOL_BASE), 3)
        pygame.draw.line(sup, (230, 60, 60), (MESA.right, GOL_TOPO), (MESA.right, GOL_BASE), 3)
        for px, py in POSTES:
            pygame.draw.circle(sup, (240, 240, 250), (px, py), 7)
            pygame.draw.circle(sup, (120, 30, 30), (px, py), 7, 2)

        # Plaquinhas de patrocínio na borda
        for texto, cx, cy in (("OVAL", 250, MESA.top - BORDA // 2),
                              ("LIMÕES & CIA", LARGURA - 250, MESA.top - BORDA // 2),
                              ("LIMÕES & CIA", 250, MESA.bottom + BORDA // 2),
                              ("OVAL", LARGURA - 250, MESA.bottom + BORDA // 2)):
            tt = ui.texto(t(texto), 10, (40, 40, 60), sombra=False)
            r = tt.get_rect(center=(cx, cy)).inflate(16, 8)
            pygame.draw.rect(sup, (255, 230, 90), r, border_radius=4)
            pygame.draw.rect(sup, (30, 30, 50), r, 2, border_radius=4)
            sup.blit(tt, tt.get_rect(center=r.center))
        return sup

    @classmethod
    def desenhar_icone(cls, sup, jogador):
        w, h = sup.get_size()
        apar2 = ((jogador.ovo + 1) % 4, (jogador.cabelo + 4) % 8, (jogador.olho + 1) % 3,
                 (jogador.boca + 2) % 6)
        for (x, ap, esp) in ((w * 0.25, None, False), (w * 0.75, apar2, True)):
            pygame.draw.circle(sup, (30, 40, 80), (int(x), int(h * 0.62)), int(h * 0.2))
            jogador.desenhar(sup, (x, h * 0.55), h * 0.36, aparencia=ap, espelhar=esp)
        ui.limao(sup, (w // 2, int(h * 0.55)), 11, 20)
        for k in range(3):
            pygame.draw.circle(sup, (255, 200, 60), (w // 2 - 18 - k * 9, int(h * 0.55) + k), 4 - k)

    # --------------------------------------------------------
    # PARTIDA
    # --------------------------------------------------------

    def __init__(self, app, menu):
        self.seguradas = set()
        super().__init__(app, menu)

    def reiniciar(self):
        self.meta = METAS[self.opcao]
        self.placar = [0, 0]
        self.rebs = [Rebatedor(0), Rebatedor(1)]
        self.limoes = [Limao(MEIO_X, GOL_Y)]
        self.fase = "saque"
        self.tempo_fase = 0.0
        self.tempo_sem_gol = 0.0
        self.quem_marcou = None
        self.banner = None
        # Avatares guardados (o cache do jogador pode ser limpo)
        self._avatares = [self.jogador.avatar(ALTURA_OVO, self.aparencia(i)).copy() for i in (0, 1)]
        self._avatares[1] = pygame.transform.flip(self._avatares[1], True, False)
        self._mini = [self.jogador.avatar(34, self.aparencia(i)).copy() for i in (0, 1)]
        self._mini[1] = pygame.transform.flip(self._mini[1], True, False)
        self._esticados = {}
        self._hud_cache = None

    def _banner(self, texto, cor, tempo, tamanho=28):
        self.banner = [texto, cor, tempo, tamanho, tempo]

    def _saque(self, lado):
        """Limão parado no lado de quem sofreu o gol (lado None = meio)."""
        if lado is None:
            x = MEIO_X
        else:
            x = MEIO_X - 170 if lado == 0 else MEIO_X + 170
        self.limoes = [Limao(x, GOL_Y)]
        for r in self.rebs:
            r.x, r.y = CASA[r.i]
            r.vx = r.vy = 0.0
            r.janela = 0.0
        self.fase = "saque"
        self.tempo_fase = 0.0
        self.tempo_sem_gol = 0.0

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
            if e.key in TECLAS_ACAO[i]:
                self._tacada(self.rebs[i])

    def _tacada(self, r):
        if r.recarga > 0 or self.fase == "gol":
            return
        r.janela = TACADA_JANELA
        r.recarga = TACADA_RECARGA
        r.vel_esticar += 5.0
        self.som("asa", 0.6)

    def _controles(self):
        apertadas = pygame.key.get_pressed()
        seg = self.seguradas
        res = []
        for i in (0, 1):
            m = TECLAS_MOVER[i]

            def s(nome):
                k = m[nome]
                return apertadas[k] or k in seg

            dx = (1 if s("dir") else 0) - (1 if s("esq") else 0)
            dy = (1 if s("baixo") else 0) - (1 if s("cima") else 0)
            res.append((dx, dy))
        return res

    # --------------------------------------------------------
    # LÓGICA
    # --------------------------------------------------------

    def atualizar_jogo(self, dt):
        self.tempo_fase += dt
        if self.banner:
            self.banner[2] -= dt
            if self.banner[2] <= 0:
                self.banner = None

        pode_mover = self.fase in ("jogo", "saque")
        controles = self._controles() if pode_mover else [(0, 0), (0, 0)]
        for r, (dx, dy) in zip(self.rebs, controles):
            r.entrada = (dx, dy)
            r.recarga = max(0.0, r.recarga - dt)
            r.janela = max(0.0, r.janela - dt)
            r.espera_som = max(0.0, r.espera_som - dt)
            r.vel_esticar += (-260 * r.esticar - 12 * r.vel_esticar) * dt
            r.esticar = max(-1.0, min(1.0, r.esticar + r.vel_esticar * dt))
            if r.choro > 0:
                r.choro -= dt
                if random.random() < 0.35:
                    esp = -1 if r.i == 1 else 1
                    for olho in (-1, 1):
                        self.particulas.explodir((r.x + olho * 12 * esp, r.y - 14),
                                                 [(90, 170, 255), (150, 210, 255)], 1, 90, 0.6,
                                                 (2, 4), 500)

        if self.fase == "saque":
            if self.tempo_fase >= TEMPO_SAQUE:
                self.fase = "jogo"
                self.tempo_fase = 0.0
        elif self.fase == "jogo":
            self.tempo_sem_gol += dt
            if self.tempo_sem_gol >= TEMPO_DOIS_LIMOES and len(self.limoes) == 1:
                self._segundo_limao()
        elif self.fase == "gol":
            if self.tempo_fase >= TEMPO_GOL:
                if max(self.placar) >= self.meta:
                    g = self.placar
                    self.terminar_multi(0 if g[0] > g[1] else 1, [t("PLACAR  {a} × {b}", a=g[0], b=g[1])])
                    return
                self._saque(1 - self.quem_marcou)

        # Física em passos pequenos
        passos = max(1, math.ceil(dt / SUB_PASSO))
        h = dt / passos
        for _ in range(passos):
            self._fisica(h)
            if self.fase == "gol":
                break

        # Rastro, giro e limão parado
        for L in self.limoes:
            L.rastro.insert(0, (L.x, L.y))
            del L.rastro[6:]
            v = math.hypot(L.vx, L.vy)
            L.angulo -= L.vx * dt * 0.8
            if L.quente and v < VEL_QUENTE:
                L.quente = False
            if L.quente and random.random() < 0.6:
                self.particulas.explodir((L.x, L.y), [(255, 140, 30), (255, 220, 60), (230, 60, 30)],
                                         1, 60, 0.35, (2, 5), 0)
            if self.fase == "jogo" and v < 20:
                L.parado += dt
                if L.parado >= TEMPO_PARADO:
                    L.parado = 0.0
                    dx, dy = MEIO_X - L.x, GOL_Y - L.y
                    d = math.hypot(dx, dy)
                    if d < 60:
                        # Já está no meio: escorrega para um dos lados
                        L.vx, L.vy = random.choice((-160, 160)), random.uniform(-60, 60)
                    else:
                        L.vx, L.vy = dx / d * 180, dy / d * 180
            else:
                L.parado = 0.0

    def _segundo_limao(self):
        x, y = MEIO_X, GOL_Y
        # Não nasce em cima de ninguém
        for cy in (GOL_Y, MESA.top + 90, MESA.bottom - 90):
            livre = all(math.hypot(L.x - x, L.y - cy) > R_LIMAO * 3 for L in self.limoes) and \
                all(math.hypot(r.x - x, r.y - cy) > R_REB + R_LIMAO + 10 for r in self.rebs)
            if livre:
                y = cy
                break
        novo = Limao(x, y, 0.0, random.choice((-120, 120)))
        self.limoes.append(novo)
        self._banner(t("DOIS LIMÕES!"), AMARELO, 1.6)
        self.som("revelar")
        self.particulas.explodir((x, y), [(250, 222, 40), BRANCO, (70, 170, 60)], 18, 220, 0.6,
                                 (2, 5), 0)

    # --------------------------------------------------------
    # FÍSICA
    # --------------------------------------------------------

    def _fisica(self, h):
        # Rebatedores
        for r in self.rebs:
            dx, dy = r.entrada
            if dx or dy:
                n = math.hypot(dx, dy)
                r.vx += dx / n * ACELERACAO * h
                r.vy += dy / n * ACELERACAO * h
            f = math.exp(-ATRITO_REB * h)
            r.vx *= f
            r.vy *= f
            v = math.hypot(r.vx, r.vy)
            if v > VEL_MAX_REB:
                r.vx *= VEL_MAX_REB / v
                r.vy *= VEL_MAX_REB / v
            r.x += r.vx * h
            r.y += r.vy * h
            self._prender_rebatedor(r)

        if self.fase == "gol":
            return

        # Limões
        f = math.exp(-ATRITO_LIMAO * h)
        for L in self.limoes:
            L.vx *= f
            L.vy *= f
            L.x += L.vx * h
            L.y += L.vy * h
            self._paredes(L)

        for L in self.limoes:
            for r in self.rebs:
                self._colidir_reb(L, r)
        if len(self.limoes) == 2:
            self._colidir_limoes(*self.limoes)

        for L in self.limoes:
            self._paredes(L)
            # Limão espremido contra a parede: quem sai é o rebatedor
            for r in self.rebs:
                dx, dy = r.x - L.x, r.y - L.y
                d = math.hypot(dx, dy)
                minimo = R_REB + R_LIMAO
                if d < minimo:
                    if d < 1e-6:
                        dx, dy, d = (-1.0 if r.i == 0 else 1.0), 0.0, 1.0
                    nx, ny = dx / d, dy / d
                    r.x = L.x + nx * minimo
                    r.y = L.y + ny * minimo
                    vn = r.vx * nx + r.vy * ny
                    if vn < 0:
                        r.vx -= vn * nx
                        r.vy -= vn * ny
                    self._prender_rebatedor(r)

            v = math.hypot(L.vx, L.vy)
            if v > VEL_MAX_LIMAO:
                L.vx *= VEL_MAX_LIMAO / v
                L.vy *= VEL_MAX_LIMAO / v

        # Gol?
        for L in self.limoes:
            if L.x < MESA.left - R_LIMAO:
                self._gol(1, L)
                return
            if L.x > MESA.right + R_LIMAO:
                self._gol(0, L)
                return

    @staticmethod
    def _prender_rebatedor(r):
        """Mantém o rebatedor na sua metade (e longe dos cantos redondos)."""
        if r.x < r.x_min:
            r.x, r.vx = r.x_min, max(0.0, r.vx)
        elif r.x > r.x_max:
            r.x, r.vx = r.x_max, min(0.0, r.vx)
        if r.y < MESA.top + R_REB:
            r.y, r.vy = MESA.top + R_REB, max(0.0, r.vy)
        elif r.y > MESA.bottom - R_REB:
            r.y, r.vy = MESA.bottom - R_REB, min(0.0, r.vy)
        limite = RAIO_CANTO - R_REB
        for (cx, cy), sx, sy in CANTOS:
            if (r.x - cx) * sx > 0 and (r.y - cy) * sy > 0:
                d = math.hypot(r.x - cx, r.y - cy)
                if d > limite:
                    nx, ny = (r.x - cx) / d, (r.y - cy) / d
                    r.x, r.y = cx + nx * limite, cy + ny * limite
                    vn = r.vx * nx + r.vy * ny
                    if vn > 0:
                        r.vx -= vn * nx
                        r.vy -= vn * ny

    def _paredes(self, L):
        r = R_LIMAO
        bateu = 0.0
        na_boca = GOL_TOPO < L.y < GOL_BASE

        # Dentro do bolsão do gol: paredes de cima/baixo do bolsão
        if L.x < MESA.left or L.x > MESA.right:
            if L.y < GOL_TOPO + r:
                L.y, bateu = GOL_TOPO + r, max(bateu, abs(L.vy))
                L.vy = abs(L.vy) * QUIQUE_PAREDE
            elif L.y > GOL_BASE - r:
                L.y, bateu = GOL_BASE - r, max(bateu, abs(L.vy))
                L.vy = -abs(L.vy) * QUIQUE_PAREDE
        else:
            if L.y < MESA.top + r:
                L.y, bateu = MESA.top + r, max(bateu, abs(L.vy))
                L.vy = abs(L.vy) * QUIQUE_PAREDE
            elif L.y > MESA.bottom - r:
                L.y, bateu = MESA.bottom - r, max(bateu, abs(L.vy))
                L.vy = -abs(L.vy) * QUIQUE_PAREDE

        # Laterais (menos na boca do gol)
        if not na_boca:
            if L.x < MESA.left + r:
                L.x, bateu = MESA.left + r, max(bateu, abs(L.vx))
                L.vx = abs(L.vx) * QUIQUE_PAREDE
            elif L.x > MESA.right - r:
                L.x, bateu = MESA.right - r, max(bateu, abs(L.vx))
                L.vx = -abs(L.vx) * QUIQUE_PAREDE

        # Cantos arredondados
        limite = RAIO_CANTO - r
        for (cx, cy), sx, sy in CANTOS:
            if (L.x - cx) * sx > 0 and (L.y - cy) * sy > 0:
                d = math.hypot(L.x - cx, L.y - cy)
                if d > limite:
                    nx, ny = (L.x - cx) / d, (L.y - cy) / d
                    L.x, L.y = cx + nx * limite, cy + ny * limite
                    vn = L.vx * nx + L.vy * ny
                    if vn > 0:
                        L.vx -= (1 + QUIQUE_PAREDE) * vn * nx
                        L.vy -= (1 + QUIQUE_PAREDE) * vn * ny
                        bateu = max(bateu, vn)

        # Traves (as pontas da abertura do gol)
        for px, py in POSTES:
            dx, dy = L.x - px, L.y - py
            d = math.hypot(dx, dy)
            minimo = r + RAIO_POSTE
            if d < minimo:
                if d < 1e-6:
                    dx, dy, d = (1.0 if px < MEIO_X else -1.0), 0.0, 1.0
                nx, ny = dx / d, dy / d
                L.x, L.y = px + nx * minimo, py + ny * minimo
                vn = L.vx * nx + L.vy * ny
                if vn < 0:
                    L.vx -= (1 + QUIQUE_PAREDE) * vn * nx
                    L.vy -= (1 + QUIQUE_PAREDE) * vn * ny
                    bateu = max(bateu, -vn)

        if bateu > 200 and self.estado == "jogando":
            self.som("bater", min(0.6, bateu / 1500))

    def _colidir_reb(self, L, r):
        dx, dy = L.x - r.x, L.y - r.y
        d = math.hypot(dx, dy)
        minimo = R_REB + R_LIMAO
        if d >= minimo:
            return
        if d < 1e-6:
            dx, dy, d = (1.0 if r.i == 0 else -1.0), 0.0, 1.0
        nx, ny = dx / d, dy / d

        # Primeiro separa, depois calcula a velocidade
        L.x = r.x + nx * minimo
        L.y = r.y + ny * minimo

        rvx, rvy = L.vx - r.vx, L.vy - r.vy
        vn = rvx * nx + rvy * ny
        if vn >= 0:
            return

        # Reflete pela normal e soma a velocidade do rebatedor
        vx, vy = L.vx, L.vy
        vpn = vx * nx + vy * ny
        if vpn < 0:
            vx -= (1 + QUIQUE_REB) * vpn * nx
            vy -= (1 + QUIQUE_REB) * vpn * ny
        vx += SOMA_REB * r.vx
        vy += SOMA_REB * r.vy

        # Sempre sai do ovo (nada de limão grudado)
        saida = (vx - r.vx) * nx + (vy - r.vy) * ny
        if saida < SAIDA_MIN:
            vx += (SAIDA_MIN - saida) * nx
            vy += (SAIDA_MIN - saida) * ny

        forte = r.janela > 0
        if forte:
            vx *= TACADA_BONUS
            vy *= TACADA_BONUS
            v = math.hypot(vx, vy)
            if v < 700:
                vx, vy = vx / v * 700, vy / v * 700
            L.quente = True
            r.janela = 0.0
        else:
            L.quente = False

        L.vx, L.vy = vx, vy
        velocidade = math.hypot(vx, vy)

        r.vel_esticar -= min(7.0, 2.0 + velocidade / 250)
        ponto = (L.x - nx * R_LIMAO, L.y - ny * R_LIMAO)
        if forte:
            self.som("acerto", 0.9)
            self.tremer(0.15)
            self.textos.adicionar(t("LIMÃO QUENTE!"), (r.x, r.y - 70), (255, 150, 60), 14)
            self.particulas.explodir(ponto, [(255, 220, 80), (255, 140, 30), BRANCO], 16, 320, 0.4,
                                     (2, 4), 0)
        elif r.espera_som <= 0:
            self.som("bater", min(1.0, 0.3 + velocidade / 1200))
            self.particulas.explodir(ponto, [BRANCO, (200, 230, 255)], 5, 140, 0.3, (2, 3), 0)
        r.espera_som = 0.1

    def _colidir_limoes(self, a, b):
        dx, dy = b.x - a.x, b.y - a.y
        d = math.hypot(dx, dy)
        minimo = R_LIMAO * 2
        if d >= minimo:
            return
        if d < 1e-6:
            dx, dy, d = 1.0, 0.0, 1.0
        nx, ny = dx / d, dy / d
        sobra = (minimo - d) / 2
        a.x -= nx * sobra
        a.y -= ny * sobra
        b.x += nx * sobra
        b.y += ny * sobra
        vn = (b.vx - a.vx) * nx + (b.vy - a.vy) * ny
        if vn < 0:
            j = -(1 + QUIQUE_PAREDE) * vn / 2
            a.vx -= j * nx
            a.vy -= j * ny
            b.vx += j * nx
            b.vy += j * ny
            if j > 100:
                self.som("bater", 0.4)

    def _gol(self, quem, L):
        """quem: jogador que marcou (0 ou 1)."""
        self.placar[quem] += 1
        self.quem_marcou = quem
        self.fase = "gol"
        self.tempo_fase = 0.0
        L.vx = L.vy = 0.0
        L.x = MESA.left - R_LIMAO - 6 if quem == 1 else MESA.right + R_LIMAO + 6
        # O outro limão (se tiver) sai de cena
        self.limoes = [L]

        self.som("ponto")
        self.som("explosao", 0.5)
        self.tremer(0.4)
        gol_x = MESA.left if quem == 1 else MESA.right
        cor = self.cor(quem)
        for k in range(3):
            self.particulas.explodir((gol_x, GOL_Y + (k - 1) * 60), [cor, CORES_JOGADOR[quem], BRANCO,
                                                                     AMARELO], 16, 420, 1.1, (3, 6), 350)
        self.rebs[1 - quem].choro = 1.2
        self.rebs[quem].vel_esticar += 8.0

        final = self.placar[quem] >= self.meta
        if not final and self.placar[quem] == self.meta - 1:
            self._banner(t("MATCH POINT!"), (255, 150, 150), 1.4, 20)

    def calcular_moedas(self, valor, venceu):
        base = self.MOEDAS_PARTIDA + sum(self.placar) // 3
        if venceu:
            base += self.MOEDAS_VITORIA_J1
        return min(self.MOEDAS_MAX, base)

    # --------------------------------------------------------
    # DESENHO
    # --------------------------------------------------------

    def desenhar_jogo(self, tela):
        tela.blit(self.fundo(self.jogador), (0, 0))
        tt = self.tempo

        # Sirene no gol de quem sofreu
        if self.fase == "gol" and int(tt * 8) % 2 == 0:
            x = MESA.left - GOL_FUNDO // 2 if self.quem_marcou == 1 else MESA.right + GOL_FUNDO // 2
            tela.blit(_circulo_alpha(120, (255, 40, 40), 70), (x - 121, GOL_Y - 121))
            tela.blit(_circulo_alpha(60, (255, 90, 60), 90), (x - 61, GOL_Y - 61))

        # Limões: sombra, rastro e o limão
        for L in self.limoes:
            tela.blit(_circulo_alpha(R_LIMAO, (40, 60, 110), 60), (L.x - R_LIMAO + 3, L.y - R_LIMAO + 5))
            cor = (255, 120, 30) if L.quente else (250, 222, 40)
            if math.hypot(L.vx, L.vy) > 150:
                for k, (px, py) in enumerate(L.rastro[1:6]):
                    raio = max(4, int(R_LIMAO * (1 - k * 0.14)))
                    alpha = (130 if L.quente else 90) - k * 18
                    tela.blit(_circulo_alpha(raio, cor, alpha), (px - raio - 1, py - raio - 1))
            sup = _limao_girado(R_LIMAO, L.quente, L.angulo)
            tela.blit(sup, sup.get_rect(center=(round(L.x), round(L.y))))
            if self.fase == "saque" and self.estado == "jogando":
                raio = R_LIMAO + 8 + int(abs(math.sin(tt * 6)) * 5)
                pygame.draw.circle(tela, (60, 120, 230), (round(L.x), round(L.y)), raio, 3)

        # Rebatedores (quem está mais embaixo na frente)
        for r in sorted(self.rebs, key=lambda o: o.y):
            self._desenhar_rebatedor(tela, r, tt)

        self.particulas.desenhar(tela)

        # GOL!
        if self.fase == "gol" and self.estado == "jogando":
            k = self.tempo_fase
            esc = min(1.0, k * 5)
            balanco = 1 + 0.12 * math.sin(k * 14) * max(0.0, 1 - k)
            tam = max(16, int(72 * esc * balanco) // 4 * 4)
            cor = CORES_JOGADOR[self.quem_marcou]
            painel = pygame.Rect(0, 0, 360, 150)
            painel.center = (LARGURA // 2, 262)
            if esc >= 1:
                ui.painel(tela, painel, (20, 24, 40), cor, 18, 4, sombra=False)
            ui.desenhar_texto(tela, t("GOL!"), (LARGURA // 2, 246), tam, AMARELO, "center")
            if k > 0.2:
                ui.desenhar_texto(tela, self.nome(self.quem_marcou), (LARGURA // 2, 308), 16, cor,
                                  "center")

        self._desenhar_banner(tela)
        self.textos.desenhar(tela)

    def _desenhar_rebatedor(self, tela, r, t):
        cx, cy = round(r.x), round(r.y)
        # Sombra e base (o "disco" do rebatedor)
        tela.blit(_circulo_alpha(R_REB, (30, 50, 100), 70), (cx - R_REB + 5, cy - R_REB + 8))
        cor_ovo = self.cor(r.i)
        base = ui.escurecer(cor_ovo, 70) if sum(cor_ovo) < 600 else (170, 175, 195)
        pygame.draw.circle(tela, base, (cx, cy), R_REB)
        pygame.draw.circle(tela, CORES_JOGADOR[r.i], (cx, cy), R_REB, 4)
        pygame.draw.circle(tela, (20, 24, 40), (cx, cy), R_REB, 1)

        # Tacada forte pronta / ativa
        if r.janela > 0:
            pygame.draw.circle(tela, (255, 160, 40), (cx, cy), R_REB + 6, 4)
        elif r.recarga > 0 and self.fase != "gol":
            frac = 1 - r.recarga / TACADA_RECARGA
            rect = pygame.Rect(0, 0, R_REB * 2 + 12, R_REB * 2 + 12)
            rect.center = (cx, cy)
            pygame.draw.arc(tela, (200, 210, 230), rect, math.pi / 2, math.pi / 2 + math.tau * frac, 3)

        # O ovo em cima (squash quando rebate)
        e = round(r.esticar * PASSOS_ESTICAR) / PASSOS_ESTICAR
        sup = self._ovo_esticado(r.i, e)
        w, h = sup.get_size()
        altura_vista = ALTURA_OVO * (1 + 0.16 * e) if abs(e) > 0.02 else ALTURA_OVO
        # Os pés ficam no centro de baixo do disco
        centro_ovo_y = cy + R_REB * 0.45 - altura_vista / 2
        tela.blit(sup, sup.get_rect(center=(cx, round(centro_ovo_y - h * 0.01))))

    def _ovo_esticado(self, i, e):
        """Avatar com squash/stretch (em degraus, guardado em cache)."""
        if abs(e) <= 0.02:
            return self._avatares[i]
        chave = (i, e)
        sup = self._esticados.get(chave)
        if sup is None:
            base = self._avatares[i]
            w, h = base.get_size()
            sup = pygame.transform.smoothscale(base, (max(2, round(w * (1 - 0.18 * e))),
                                                      max(2, round(h * (1 + 0.16 * e)))))
            self._esticados[chave] = sup
        return sup

    def _desenhar_banner(self, tela):
        if not self.banner or self.estado != "jogando":
            return
        texto, cor, resta, tam, total = self.banner
        entrada = min(1.0, (total - resta) * 6)
        tam_atual = tam if entrada >= 1 else max(12, int(tam * (0.6 + 0.4 * entrada)))
        sup = ui.texto(texto, tam_atual, cor)
        r = sup.get_rect(center=(LARGURA // 2, 170))
        ui.painel(tela, r.inflate(36, 24), (20, 24, 40), cor, 14, 3, sombra=False)
        tela.blit(sup, r)

    def desenhar_hud(self, tela):
        """Placar central com os dois ovinhos."""
        caixa = pygame.Rect(0, 6, 540, 66)
        caixa.centerx = LARGURA // 2
        chave = (self.meta, tuple(self.placar))
        if self._hud_cache is None or self._hud_cache[0] != chave:
            self._hud_cache = (chave, self._montar_hud(caixa))
        tela.blit(self._hud_cache[1], caixa.topleft)
        if len(self.limoes) == 2 and self.fase != "gol":
            ui.desenhar_texto(tela, t("2 LIMÕES!"), (caixa.centerx + 150, caixa.bottom - 12), 10,
                              AMARELO, "center")
        else:
            falta = max(0, int(TEMPO_DOIS_LIMOES - self.tempo_sem_gol) + 1)
            if self.fase == "jogo" and falta <= 10:
                ui.desenhar_texto(tela, t("LIMÃO EXTRA EM {n}", n=falta), (caixa.centerx + 150,
                                                                   caixa.bottom - 12), 10,
                                  (255, 200, 120), "center")

    def _montar_hud(self, caixa):
        """Placar pré-desenhado (só muda quando sai gol)."""
        sup = pygame.Surface(caixa.size, pygame.SRCALPHA)
        c = sup.get_rect()
        ui.painel(sup, c, (20, 24, 40), BRANCO, 14, 3, sombra=False)
        for i in (0, 1):
            lado = -1 if i == 0 else 1
            mini = self._mini[i]
            sup.blit(mini, mini.get_rect(center=(c.centerx + lado * 238, c.centery + 2)))
            ui.desenhar_texto(sup, self.nome(i)[:10], (c.centerx + lado * 205, c.y + 20), 12,
                              CORES_JOGADOR[i], "midright" if i == 1 else "midleft")
            ui.desenhar_texto(sup, str(self.placar[i]), (c.centerx + lado * 50, c.centery + 2),
                              32, AMARELO, "center")
        ui.desenhar_texto(sup, "×", (c.centerx, c.centery + 2), 20, BRANCO, "center")
        ui.desenhar_texto(sup, t("ATÉ {n}", n=self.meta), (c.centerx - 150, c.bottom - 12), 10,
                          (180, 200, 255), "center")
        return sup

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
            for sub in ui.quebrar_linhas(linha, 10, caixa.w - 50):
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
