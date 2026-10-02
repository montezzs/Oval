import math
import random

import pygame

from settings import *
from core import ui
from jogos.base_multi import MiniJogoMulti, TECLAS_MOVER, TECLAS_ACAO, CORES_JOGADOR

# ============================================================
# GUERRA DE TINTA
# ============================================================
# Cada ovo é um rolo de pintura vivo: rola pelo chão deixando
# um rastro da cor da própria casca. Jogue BALÕES DE TINTA,
# pegue os itens e, quando o tempo acabar, quem tiver pintado
# mais chão vence!

COLS = 32
LINHAS = 20
CEL = 28
X0 = 64
Y0 = 130
AREA = pygame.Rect(X0, Y0, COLS * CEL, LINHAS * CEL)

ALTURA_OVO = 40
RAIO_OVO = 17                   # raio de colisão
VEL = 260
VEL_TENIS = 1.4
RAIO_PINTURA = 1.15             # em células (rolo normal)
RAIO_ROLO = 2.2                 # com o item ROLO
IMPULSO = 400
TEMPO_TONTO = 0.4

DIST_BALAO = 180
TEMPO_VOO = 0.45
CARGAS = 2
RECARGA = 3.0

INTERVALO_ITEM = 7.0
DURACAO_ITEM = 6.0
ITENS = ["rolo", "tenis", "bomba"]
NOMES_ITENS = {"rolo": "ROLO!", "tenis": "TÊNIS!", "bomba": "BOMBA DE TINTA!"}

SPAWNS = [(3, 10), (COLS - 4, 10)]

# Vasos (blocos 2x2): canto de cima à esquerda de cada um. Sempre espelhados.
LAYOUTS = [
    [(7, 4), (23, 4), (15, 9), (7, 14), (23, 14)],
    [(10, 6), (20, 6), (10, 12), (20, 12)],
    [(8, 9), (22, 9), (12, 3), (18, 3), (12, 15), (18, 15)],
]

# Modos: (duração do round, rounds para vencer)
MODOS = [(60.0, 1), (45.0, 2), (120.0, 1)]
MAX_ROUNDS = 5

TEMPO_ANUNCIO = 1.5
TEMPO_CONTANDO = 2.6
TEMPO_RESULTADO = 2.4

PISO = (245, 245, 240)
REJUNTE = (225, 225, 220)
MURO = (60, 60, 80)

OITO = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]


def _tinta(cor):
    """Cor da tinta: o ovo branco pinta de lilás (branco no piso claro não aparece)."""
    if sum(cor) > 600:
        return (170, 180, 225)
    return cor


def _distancia_cor(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


# ============================================================
# SPRITES
# ============================================================

_sprites = {}


def _vaso_sup():
    s = _sprites.get("vaso")
    if s is None:
        lado = CEL * 2
        s = pygame.Surface((lado, lado + 22), pygame.SRCALPHA)
        # Planta
        for dx, dy, r in ((-14, 10, 12), (14, 10, 12), (0, 2, 14), (-6, 14, 10), (8, 16, 10)):
            pygame.draw.circle(s, (40, 120, 50), (lado // 2 + dx, dy + 6), r + 2)
        for dx, dy, r in ((-14, 10, 12), (14, 10, 12), (0, 2, 14), (-6, 14, 10), (8, 16, 10)):
            pygame.draw.circle(s, (80, 170, 80), (lado // 2 + dx, dy + 5), r)
        pygame.draw.circle(s, (255, 120, 160), (lado // 2 - 8, 8), 5)
        pygame.draw.circle(s, (255, 230, 90), (lado // 2 + 10, 12), 4)
        # Vaso de barro
        corpo = [(6, 26), (lado - 6, 26), (lado - 12, lado + 18), (12, lado + 18)]
        pygame.draw.polygon(s, (150, 70, 40), [(x + 2, y + 3) for x, y in corpo])
        pygame.draw.polygon(s, (205, 105, 60), corpo)
        pygame.draw.rect(s, (225, 125, 75), (2, 20, lado - 4, 12), border_radius=4)
        pygame.draw.rect(s, (150, 70, 40), (2, 20, lado - 4, 12), 2, border_radius=4)
        pygame.draw.line(s, (235, 150, 100), (14, 38), (18, lado + 10), 3)
        # Respingo de tinta decorativo
        pygame.draw.circle(s, (90, 160, 255), (lado - 20, 50), 5)
        pygame.draw.circle(s, (90, 160, 255), (lado - 14, 58), 3)
        _sprites["vaso"] = s
    return s


def _balao_sup(cor):
    chave = ("balao", cor)
    s = _sprites.get(chave)
    if s is None:
        s = pygame.Surface((26, 32), pygame.SRCALPHA)
        escura = (90, 90, 110) if sum(cor) > 600 else ui.escurecer(cor, 80)
        pygame.draw.ellipse(s, escura, (1, 1, 24, 26))
        pygame.draw.ellipse(s, cor, (3, 3, 20, 22))
        pygame.draw.ellipse(s, ui.misturar(cor, BRANCO, 0.7), (7, 6, 6, 8))
        pygame.draw.polygon(s, escura, [(13, 26), (9, 31), (17, 31)])
        _sprites[chave] = s
    return s


def _item_sup(tipo):
    chave = ("item", tipo)
    s = _sprites.get(chave)
    if s is not None:
        return s
    s = pygame.Surface((40, 40), pygame.SRCALPHA)
    cor = {"rolo": (255, 120, 170), "tenis": (90, 200, 255), "bomba": (255, 190, 60)}[tipo]
    pygame.draw.circle(s, ui.escurecer(cor, 90), (20, 20), 19)
    pygame.draw.circle(s, cor, (20, 20), 17)
    pygame.draw.circle(s, ui.misturar(cor, BRANCO, 0.6), (20, 20), 13)
    if tipo == "rolo":
        pygame.draw.rect(s, (230, 60, 110), (8, 10, 24, 10), border_radius=4)
        pygame.draw.line(s, (80, 80, 90), (20, 20), (20, 25), 2)
        pygame.draw.line(s, (80, 80, 90), (20, 25), (26, 25), 2)
        pygame.draw.rect(s, (120, 80, 50), (24, 25, 4, 9), border_radius=2)
    elif tipo == "tenis":
        pygame.draw.rect(s, (230, 50, 60), (9, 18, 18, 9), border_radius=4)
        pygame.draw.rect(s, (230, 50, 60), (9, 11, 9, 10), border_radius=3)
        pygame.draw.rect(s, (255, 255, 255), (8, 26, 24, 4), border_radius=2)
        pygame.draw.line(s, (255, 255, 255), (12, 17), (18, 17), 2)
        for y in (14, 20):
            pygame.draw.line(s, (60, 120, 200), (30, y), (36, y), 2)
    else:
        pygame.draw.circle(s, (70, 60, 100), (20, 23), 9)
        pygame.draw.circle(s, (130, 120, 170), (17, 20), 3)
        pygame.draw.line(s, (120, 90, 60), (20, 14), (24, 8), 2)
        pygame.draw.circle(s, (255, 150, 40), (25, 7), 3)
        for ang in range(0, 360, 60):
            a = math.radians(ang)
            pygame.draw.circle(s, (80, 170, 255), (int(20 + math.cos(a) * 14), int(23 + math.sin(a) * 12)), 2)
    _sprites[chave] = s
    return s


# ============================================================
# OBJETOS
# ============================================================

class Pintor:

    def __init__(self, i, cel):
        self.i = i
        self.x = X0 + cel[0] * CEL + CEL / 2
        self.y = Y0 + cel[1] * CEL + CEL / 2
        self.kx = self.ky = 0.0         # empurrão (colisão)
        self.olhando = (1.0, 0.0) if i == 0 else (-1.0, 0.0)
        self.vel_atual = 0.0
        self.cargas = CARGAS
        self.recarga = 0.0
        self.tonto = 0.0
        self.rolo = 0.0
        self.tenis = 0.0
        self.angulo = 0.0
        self.respingo = 0.0


class Balao:

    def __init__(self, dono, origem, alvo):
        self.dono = dono
        self.origem = origem
        self.alvo = alvo
        self.t = 0.0


# ============================================================
# JOGO
# ============================================================

class GuerraTinta(MiniJogoMulti):

    ID = "guerra_tinta"
    TITULO = "GUERRA DE TINTA"
    TITULO_CURTO = "TINTA"
    DESCRICAO = "Os ovos rolam pintando o chão com a própria cor. Quem pintar mais até o fim do tempo ganha!"
    COR = (90, 160, 255)
    INSTRUCOES = [
        "Role pelo chão pintando com a cor do seu ovo!",
        "Jogue BALÕES DE TINTA e pegue ROLO, TÊNIS e BOMBA.",
        "Quando o tempo acabar, quem pintou mais vence!",
        "J1: WASD + ESPAÇO/F    J2: SETAS + ENTER/CTRL",
    ]
    OPCOES = ["60 SEGUNDOS", "MELHOR DE 3", "SUPER 120s"]
    CONTROLES_J1 = "WASD + ESPAÇO"
    CONTROLES_J2 = "SETAS + ENTER"
    CONTAGEM = True

    MOEDAS_PARTIDA = 12
    MOEDAS_VITORIA_J1 = 8
    MOEDAS_MODO_LONGO = 6       # MELHOR DE 3 e SUPER 120s

    # --------------------------------------------------------
    # CENÁRIO: piso de ladrilho, muro com baldes de tinta
    # --------------------------------------------------------

    @classmethod
    def criar_fundo(cls, jogador):
        sup = pygame.Surface((LARGURA, ALTURA))
        sup.fill(MURO)
        rnd = random.Random(9)

        # Tijolinhos do muro
        for y in range(0, ALTURA, 18):
            desloc = 0 if (y // 18) % 2 == 0 else 20
            for x in range(-40, LARGURA, 40):
                pygame.draw.rect(sup, (70, 70, 92), (x + desloc + 2, y + 2, 36, 14), border_radius=2)

        # Respingos coloridos no muro
        cores = [(255, 90, 120), (90, 200, 255), (255, 214, 64), (140, 230, 120), (200, 140, 255)]
        for _ in range(40):
            x, y = rnd.randrange(LARGURA), rnd.randrange(ALTURA)
            cor = rnd.choice(cores)
            pygame.draw.circle(sup, cor, (x, y), rnd.randint(3, 7))
            for _ in range(3):
                pygame.draw.circle(sup, cor, (x + rnd.randint(-12, 12), y + rnd.randint(-12, 12)), 2)

        # Baldes de tinta nas laterais
        for i, y in enumerate(range(170, 660, 120)):
            cls._balde(sup, 30, y, cores[i % len(cores)])
            cls._balde(sup, LARGURA - 30, y + 50, cores[(i + 2) % len(cores)])

        # Borda e piso
        pygame.draw.rect(sup, (40, 40, 56), AREA.inflate(20, 20), border_radius=8)
        pygame.draw.rect(sup, (120, 120, 140), AREA.inflate(20, 20), 3, border_radius=8)
        sup.blit(_piso_limpo(), AREA.topleft)
        return sup

    @staticmethod
    def _balde(sup, x, y, cor):
        pygame.draw.ellipse(sup, (30, 30, 40), (x - 20, y + 20, 40, 10))
        pygame.draw.rect(sup, (170, 175, 190), (x - 16, y - 14, 32, 38), border_radius=4)
        pygame.draw.rect(sup, (120, 125, 140), (x - 16, y - 14, 32, 38), 2, border_radius=4)
        pygame.draw.ellipse(sup, cor, (x - 16, y - 20, 32, 12))
        pygame.draw.ellipse(sup, ui.escurecer(cor, 50), (x - 16, y - 20, 32, 12), 2)
        pygame.draw.rect(sup, cor, (x - 16, y - 14, 10, 20), border_radius=3)     # escorrido
        pygame.draw.circle(sup, cor, (x - 11, y + 6), 5)
        pygame.draw.arc(sup, (90, 90, 100), (x - 18, y - 34, 36, 36), 0.2, math.pi - 0.2, 2)

    @classmethod
    def desenhar_icone(cls, sup, jogador):
        w, h = sup.get_size()
        y = h // 2 + 14
        cor = _tinta(jogador.cor)
        pygame.draw.rect(sup, cor, (w // 2 - 90, y + 4, 90, 18), border_radius=9)
        for dx in (-80, -50, -20):
            pygame.draw.circle(sup, cor, (w // 2 + dx, y + 20), 7)
        jogador.desenhar(sup, (w // 2 - 4, y - 4), 42, angulo=-20)
        b = _balao_sup(cor)
        sup.blit(b, b.get_rect(center=(w // 2 + 60, y - 30)))
        pygame.draw.circle(sup, (255, 90, 120), (w // 2 + 70, y + 12), 12)
        pygame.draw.circle(sup, (255, 90, 120), (w // 2 + 86, y + 6), 5)

    # --------------------------------------------------------
    # PARTIDA
    # --------------------------------------------------------

    def reiniciar(self):
        self.duracao, self.precisa = MODOS[self.opcao]
        self.vitorias_round = [0, 0]
        self.round = 1
        self.rounds_jogados = 0
        self.seguradas = set()
        cores = [_tinta(self.cor(0)), _tinta(self.cor(1))]
        self.tintas = cores
        # Cores parecidas (ou verde x azul): o J2 pinta com bolinhas
        verde_azul = {tuple(self.cor(0)), tuple(self.cor(1))} == {(168, 230, 29), (0, 183, 239)}
        self.bolinhas = verde_azul or _distancia_cor(cores[0], cores[1]) < 260
        self._montar_round()

    def _montar_round(self):
        self.layout = random.choice(LAYOUTS)
        self.vasos = set()
        for c, l in self.layout:
            for dc in (0, 1):
                for dl in (0, 1):
                    self.vasos.add((c + dc, l + dl))
        self.retangulos_vasos = [pygame.Rect(X0 + c * CEL, Y0 + l * CEL, CEL * 2, CEL * 2)
                                 for c, l in self.layout]

        self.dono = [[-1] * COLS for _ in range(LINHAS)]
        self.contagem = [0, 0]
        self.total = COLS * LINHAS - len(self.vasos)
        # Cenário inteiro + tinta (só as células que mudam são redesenhadas)
        self.chao = self.fundo(self.jogador).copy()
        for r in self.retangulos_vasos:
            # Base de pedra embaixo de cada vaso (lá não dá para pintar)
            pygame.draw.rect(self.chao, (170, 165, 155), r.inflate(-2, -2), border_radius=8)
            pygame.draw.rect(self.chao, (205, 200, 190), r.inflate(-6, -6), border_radius=6)

        self.ovos = [Pintor(i, SPAWNS[i]) for i in (0, 1)]
        self.baloes = []
        self.itens = []             # [tipo, x, y, tempo]
        self.relogio_item = 3.0
        self.restante = self.duracao
        self.ultimo_tique = None
        self.fase = "anuncio"       # anuncio, jogo, contando, resultado
        self.tempo_fase = 0.0 if self.round > 1 else TEMPO_ANUNCIO
        self.vencedor_round = None
        self.final = [0.0, 0.0]
        for ovo in self.ovos:
            self._pintar_em_volta(ovo.x, ovo.y, 1.6, ovo.i)

    def calcular_moedas(self, valor, venceu):
        base = self.MOEDAS_PARTIDA + (self.MOEDAS_VITORIA_J1 if venceu else 0)
        if self.opcao in (1, 2):
            base += self.MOEDAS_MODO_LONGO
        return base

    # --------------------------------------------------------
    # ENTRADA
    # --------------------------------------------------------

    def entrar(self):
        self.seguradas = set()
        super().entrar()

    def evento(self, e):
        if e.type == pygame.KEYDOWN:
            self.seguradas.add(e.key)
        elif e.type == pygame.KEYUP:
            self.seguradas.discard(e.key)
        elif e.type == pygame.WINDOWFOCUSLOST:
            self.seguradas.clear()
        super().evento(e)

    def evento_jogo(self, e):
        if e.type == pygame.KEYDOWN:
            for i in (0, 1):
                if e.key in TECLAS_ACAO[i]:
                    self._jogar_balao(self.ovos[i])

    def _segura(self, tecla):
        if tecla in self.seguradas:
            return True
        try:
            return bool(pygame.key.get_pressed()[tecla])
        except (IndexError, pygame.error):
            return False

    def _direcao(self, i):
        t = TECLAS_MOVER[i]
        dx = (1 if self._segura(t["dir"]) else 0) - (1 if self._segura(t["esq"]) else 0)
        dy = (1 if self._segura(t["baixo"]) else 0) - (1 if self._segura(t["cima"]) else 0)
        if dx and dy:
            return dx * 0.7071, dy * 0.7071
        return float(dx), float(dy)

    # --------------------------------------------------------
    # PINTURA
    # --------------------------------------------------------

    def _pintar(self, c, l, i):
        if not (0 <= c < COLS and 0 <= l < LINHAS) or (c, l) in self.vasos:
            return False
        antes = self.dono[l][c]
        if antes == i:
            return False
        if antes >= 0:
            self.contagem[antes] -= 1
        self.contagem[i] += 1
        self.dono[l][c] = i
        self._desenhar_celula(c, l)
        return True

    def _pintar_em_volta(self, x, y, raio, i):
        cc = (x - X0) / CEL - 0.5
        cl = (y - Y0) / CEL - 0.5
        r = int(math.ceil(raio))
        r2 = raio * raio
        for l in range(int(round(cl)) - r, int(round(cl)) + r + 1):
            for c in range(int(round(cc)) - r, int(round(cc)) + r + 1):
                if (c - cc) ** 2 + (l - cl) ** 2 <= r2:
                    self._pintar(c, l, i)

    def _pintar_losango(self, cel, raio, i):
        for dl in range(-raio, raio + 1):
            for dc in range(-raio, raio + 1):
                if abs(dc) + abs(dl) <= raio:
                    self._pintar(cel[0] + dc, cel[1] + dl, i)

    def _desenhar_celula(self, c, l):
        """Redesenha só a célula que mudou na Surface do chão."""
        r = pygame.Rect(X0 + c * CEL, Y0 + l * CEL, CEL, CEL)
        self.chao.blit(_piso_limpo(), r, r.move(-X0, -Y0))
        i = self.dono[l][c]
        if i < 0:
            return
        cor = self.tintas[i]
        self.chao.set_clip(AREA)
        pygame.draw.rect(self.chao, cor, r)
        # Duas manchas redondas espirrando um pouco para fora
        rnd = random.Random(c * 131 + l * 17 + i * 7 + self.contagem[i])
        for _ in range(2):
            cx = r.x + rnd.randint(4, CEL - 4)
            cy = r.y + rnd.randint(4, CEL - 4)
            pygame.draw.circle(self.chao, cor, (cx, cy), rnd.randint(6, 9))
        brilho = ui.misturar(cor, BRANCO, 0.35)
        pygame.draw.circle(self.chao, brilho, (r.x + rnd.randint(6, CEL - 6), r.y + rnd.randint(6, CEL - 6)), 2)
        if i == 1 and self.bolinhas:
            clara = ui.misturar(cor, BRANCO, 0.75)
            for dx, dy in ((7, 7), (21, 7), (14, 14), (7, 21), (21, 21)):
                pygame.draw.circle(self.chao, clara, (r.x + dx, r.y + dy), 3)
        self.chao.set_clip(None)

    # --------------------------------------------------------
    # LÓGICA
    # --------------------------------------------------------

    def atualizar_jogo(self, dt):
        self.tempo_fase += dt

        if self.fase == "anuncio":
            if self.tempo_fase >= TEMPO_ANUNCIO:
                self.fase = "jogo"
                self.tempo_fase = 0.0
            return
        if self.fase == "contando":
            if self.tempo_fase >= TEMPO_CONTANDO:
                self._resultado_round()
            return
        if self.fase == "resultado":
            if self.tempo_fase >= TEMPO_RESULTADO:
                self._proximo()
            return

        # Relógio e tique-taque nos últimos segundos
        self.restante -= dt
        seg = math.ceil(self.restante)
        if seg <= 10 and seg != self.ultimo_tique and seg > 0:
            self.ultimo_tique = seg
            self.som("ponto", 0.6)
        if self.restante <= 0:
            self.restante = 0.0
            self._acabar_round()
            return

        for ovo in self.ovos:
            self._mover(ovo, dt)
        self._colidir_ovos()
        for ovo in self.ovos:
            raio = RAIO_ROLO if ovo.rolo > 0 else RAIO_PINTURA
            self._pintar_em_volta(ovo.x, ovo.y, raio, ovo.i)
            self._pegar_itens(ovo)

        # Balões voando
        for b in list(self.baloes):
            b.t += dt
            if b.t >= TEMPO_VOO:
                self.baloes.remove(b)
                self._splash(b)

        # Itens
        self.relogio_item -= dt
        if self.relogio_item <= 0:
            self.relogio_item = INTERVALO_ITEM
            if len(self.itens) < 2:
                self._criar_item()
        for it in self.itens:
            it[3] += dt

    def _mover(self, ovo, dt):
        ovo.tonto = max(0.0, ovo.tonto - dt)
        ovo.rolo = max(0.0, ovo.rolo - dt)
        ovo.tenis = max(0.0, ovo.tenis - dt)
        if ovo.cargas < CARGAS:
            ovo.recarga += dt
            if ovo.recarga >= RECARGA:
                ovo.recarga = 0.0
                ovo.cargas += 1
        else:
            ovo.recarga = 0.0

        dx, dy = (0.0, 0.0) if ovo.tonto > 0 else self._direcao(ovo.i)
        vel = VEL * (VEL_TENIS if ovo.tenis > 0 else 1.0)
        if dx or dy:
            ovo.olhando = (dx, dy)
        vx, vy = dx * vel, dy * vel
        ovo.vel_atual = math.hypot(vx, vy)

        # Empurrão da colisão vai diminuindo
        amortece = math.exp(-7 * dt)
        ovo.kx *= amortece
        ovo.ky *= amortece
        antes = ovo.x
        ovo.x += (vx + ovo.kx) * dt
        ovo.y += (vy + ovo.ky) * dt
        self._limitar(ovo)

        # Rola: gira conforme anda para os lados
        andou = ovo.x - antes
        ovo.angulo -= math.degrees(andou / (ALTURA_OVO * 0.45))
        if abs(vy) > 1 and abs(andou) < 0.5:
            ovo.angulo += math.sin(self.tempo * 14) * 0.8

        # Respingos enquanto rola
        if ovo.vel_atual > 0:
            ovo.respingo -= dt
            if ovo.respingo <= 0:
                ovo.respingo = 0.06
                self.particulas.explodir((ovo.x - dx * 14, ovo.y + 14 - dy * 10), [self.tintas[ovo.i]],
                                         1, 90, 0.35, (2, 4), 200)

    def _limitar(self, ovo):
        r = RAIO_OVO
        ovo.x = min(max(ovo.x, AREA.left + r), AREA.right - r)
        ovo.y = min(max(ovo.y, AREA.top + r), AREA.bottom - r)
        # Vasos: empurra o círculo para fora do retângulo
        for rect in self.retangulos_vasos:
            px = min(max(ovo.x, rect.left), rect.right)
            py = min(max(ovo.y, rect.top), rect.bottom)
            dx, dy = ovo.x - px, ovo.y - py
            d2 = dx * dx + dy * dy
            if d2 >= r * r:
                continue
            if d2 < 1e-6:
                # Centro dentro do vaso: sai pelo lado mais perto
                saidas = [(ovo.x - rect.left, -1, 0), (rect.right - ovo.x, 1, 0),
                          (ovo.y - rect.top, 0, -1), (rect.bottom - ovo.y, 0, 1)]
                dist, sx, sy = min(saidas)
                ovo.x += sx * (dist + r)
                ovo.y += sy * (dist + r)
            else:
                d = math.sqrt(d2)
                ovo.x = px + dx / d * r
                ovo.y = py + dy / d * r
            if (ovo.kx * dx + ovo.ky * dy) < 0:
                ovo.kx = ovo.ky = 0.0

    def _colidir_ovos(self):
        a, b = self.ovos
        dx, dy = b.x - a.x, b.y - a.y
        d = math.hypot(dx, dy)
        if d >= RAIO_OVO * 2:
            return
        if d < 0.01:
            dx, dy, d = 1.0, 0.0, 1.0
        nx, ny = dx / d, dy / d
        # Separa e empurra os dois
        sobra = (RAIO_OVO * 2 - d) / 2
        a.x -= nx * sobra
        a.y -= ny * sobra
        b.x += nx * sobra
        b.y += ny * sobra
        a.kx, a.ky = -nx * IMPULSO, -ny * IMPULSO
        b.kx, b.ky = nx * IMPULSO, ny * IMPULSO
        self._limitar(a)
        self._limitar(b)
        # O mais lento fica tonto
        if abs(a.vel_atual - b.vel_atual) > 1:
            lento = a if a.vel_atual < b.vel_atual else b
            lento.tonto = TEMPO_TONTO
        self.som("boing", 0.7)
        self.tremer(0.08)
        meio = ((a.x + b.x) / 2, (a.y + b.y) / 2)
        self.particulas.explodir(meio, [self.tintas[0], self.tintas[1], BRANCO], 10, 180, 0.5, (2, 5))

    def _jogar_balao(self, ovo):
        if self.fase != "jogo" or ovo.cargas <= 0 or ovo.tonto > 0:
            return
        ovo.cargas -= 1
        ox, oy = ovo.olhando
        n = math.hypot(ox, oy) or 1.0
        alvo = (ovo.x + ox / n * DIST_BALAO, ovo.y + oy / n * DIST_BALAO)
        alvo = (min(max(alvo[0], AREA.left + CEL / 2), AREA.right - CEL / 2),
                min(max(alvo[1], AREA.top + CEL / 2), AREA.bottom - CEL / 2))
        self.baloes.append(Balao(ovo.i, (ovo.x, ovo.y - 10), alvo))
        self.som("pulo", 0.6)

    def _splash(self, b):
        c = int((b.alvo[0] - X0) // CEL)
        l = int((b.alvo[1] - Y0) // CEL)
        self._pintar_losango((c, l), 2, b.dono)
        cor = self.tintas[b.dono]
        self.particulas.explodir(b.alvo, [cor, ui.misturar(cor, BRANCO, 0.5)], 18, 240, 0.6, (3, 6), 300)
        self.textos.adicionar("SPLASH!", (b.alvo[0], b.alvo[1] - 24), BRANCO, 12)
        self.som("bater", 0.6)

    def _criar_item(self):
        livres = []
        for _ in range(60):
            c, l = random.randrange(1, COLS - 1), random.randrange(1, LINHAS - 1)
            if (c, l) in self.vasos:
                continue
            x, y = X0 + c * CEL + CEL / 2, Y0 + l * CEL + CEL / 2
            if all(math.hypot(o.x - x, o.y - y) > 110 for o in self.ovos):
                livres.append((x, y))
                break
        if livres:
            x, y = livres[0]
            self.itens.append([random.choice(ITENS), x, y, 0.0])
            self.som("revelar", 0.5)

    def _pegar_itens(self, ovo):
        for it in list(self.itens):
            if math.hypot(it[1] - ovo.x, it[2] - ovo.y) > 26:
                continue
            self.itens.remove(it)
            tipo = it[0]
            if tipo == "rolo":
                ovo.rolo = DURACAO_ITEM
            elif tipo == "tenis":
                ovo.tenis = DURACAO_ITEM
            else:
                c = int((ovo.x - X0) // CEL)
                l = int((ovo.y - Y0) // CEL)
                for dl in range(-4, 5):
                    for dc in range(-4, 5):
                        self._pintar(c + dc, l + dl, ovo.i)
                self.tremer(0.15)
                self.som("explosao", 0.5)
                cor = self.tintas[ovo.i]
                self.particulas.explodir((ovo.x, ovo.y), [cor, BRANCO], 30, 320, 0.8, (3, 7))
            self.som("moeda", 0.7)
            self.textos.adicionar(NOMES_ITENS[tipo], (ovo.x, ovo.y - 40), BRANCO, 12)

    # --- fim do round ---

    def porcentagem(self, i):
        return 100.0 * self.contagem[i] / max(1, self.total)

    def _acabar_round(self):
        self.fase = "contando"
        self.tempo_fase = 0.0
        self.final = [self.porcentagem(0), self.porcentagem(1)]
        self.baloes.clear()
        self.som("bandeira")

    def _resultado_round(self):
        self.fase = "resultado"
        self.tempo_fase = 0.0
        self.rounds_jogados += 1
        p0, p1 = self.final
        if abs(p0 - p1) < 0.5:
            self.vencedor_round = None
            self.som("erro")
        else:
            v = 0 if p0 > p1 else 1
            self.vencedor_round = v
            self.vitorias_round[v] += 1
            self.som("acerto")
            cor = self.tintas[v]
            for k in range(3):
                self.particulas.explodir((LARGURA // 2 + (k - 1) * 200, 300),
                                         [cor, BRANCO, AMARELO], 20, 320)

    def _proximo(self):
        placar = self.vitorias_round
        fim = max(placar) >= self.precisa or self.rounds_jogados >= MAX_ROUNDS
        if self.precisa == 1:
            fim = True
        if fim:
            if placar[0] == placar[1]:
                vencedor = None
            else:
                vencedor = 0 if placar[0] > placar[1] else 1
            linhas = [f"PINTADO: {self.final[0]:.0f}% × {self.final[1]:.0f}%"]
            if self.precisa > 1:
                linhas.insert(0, f"ROUNDS: {placar[0]} × {placar[1]}")
            self.terminar_multi(vencedor, linhas)
        else:
            self.round += 1
            self.particulas.limpar()
            self.textos.lista.clear()
            self._montar_round()

    # --------------------------------------------------------
    # DESENHO
    # --------------------------------------------------------

    def desenhar_jogo(self, tela):
        tela.blit(self.chao, (0, 0))
        t = self.tempo

        # Itens pulsando
        for tipo, x, y, idade in self.itens:
            s = _item_sup(tipo)
            esc = 1.0 + 0.08 * math.sin(t * 6)
            if idade < 0.3:
                esc *= idade / 0.3
            if esc > 0.05:
                s = pygame.transform.smoothscale(s, (max(1, int(40 * esc)), max(1, int(40 * esc))))
                tela.blit(s, s.get_rect(center=(x, y)))

        # Vasos e ovos, de cima para baixo
        objetos = [(r.bottom, 0, r) for r in self.retangulos_vasos]
        objetos += [(o.y + RAIO_OVO, 1, o) for o in self.ovos]
        objetos.sort(key=lambda x: (x[0], x[1]))
        vaso = _vaso_sup()
        for _, tipo, obj in objetos:
            if tipo == 0:
                tela.blit(vaso, (obj.x, obj.y - 22))
            else:
                self._desenhar_pintor(tela, obj)

        # Balões voando em arco (com sombra no chão)
        for b in self.baloes:
            k = b.t / TEMPO_VOO
            x = b.origem[0] + (b.alvo[0] - b.origem[0]) * k
            y = b.origem[1] + (b.alvo[1] - b.origem[1]) * k
            altura = math.sin(math.pi * k) * 60
            pygame.draw.ellipse(tela, (160, 160, 150), (x - 9, y - 3, 18, 7))
            s = _balao_sup(self.tintas[b.dono])
            s = pygame.transform.rotate(s, k * 360)
            tela.blit(s, s.get_rect(center=(x, y - altura)))

        self.particulas.desenhar(tela)
        self.textos.desenhar(tela)

        if self.estado == "jogando":
            self._desenhar_avisos(tela)

    def _desenhar_pintor(self, tela, ovo):
        x, y = ovo.x, ovo.y
        pygame.draw.ellipse(tela, (190, 190, 185), (x - 16, y + 12, 32, 10))
        if ovo.rolo > 0:
            # Rolo de pintura gigante na frente
            cor = self.tintas[ovo.i]
            pygame.draw.ellipse(tela, cor, (x - 30, y + 6, 60, 18))
            pygame.draw.ellipse(tela, ui.escurecer(cor, 60), (x - 30, y + 6, 60, 18), 2)
        if ovo.tenis > 0:
            for k in range(3):
                ox = -ovo.olhando[0] * (26 + k * 8)
                oy = -ovo.olhando[1] * (26 + k * 8)
                pygame.draw.line(tela, (120, 180, 255), (x + ox - 6, y + oy - 8 + k * 8),
                                 (x + ox + 6, y + oy - 8 + k * 8), 2)
        # Avatar com contorno escuro (aparece até em cima da própria tinta)
        s = self._avatar_contornado(ovo.i)
        ang = ovo.angulo % 360
        if ang:
            s = pygame.transform.rotate(s, ang)
        tela.blit(s, s.get_rect(center=(round(x), round(y - 3))))
        if ovo.tonto > 0:
            for k in range(3):
                a = self.tempo * 8 + k * math.tau / 3
                ui.estrela(tela, (x + math.cos(a) * 18, y - 30 + math.sin(a) * 6), 5, AMARELO, a)
        # Setinha mostrando para onde vai o balão
        if self.fase == "jogo" and self.estado == "jogando":
            ox, oy = ovo.olhando
            n = math.hypot(ox, oy) or 1.0
            px, py = x + ox / n * 30, y + oy / n * 30
            cor = CORES_JOGADOR[ovo.i]
            pygame.draw.polygon(tela, cor, [(px + ox / n * 7, py + oy / n * 7),
                                            (px - oy / n * 5, py + ox / n * 5),
                                            (px + oy / n * 5, py - ox / n * 5)])

    def _avatar_contornado(self, i):
        cache = getattr(self, "_cache_contorno", None)
        if cache is None:
            cache = self._cache_contorno = {}
        chave = (i, self.aparencia(i), self.jogador.chave_visual())
        s = cache.get(chave)
        if s is None:
            base = self.jogador.avatar(ALTURA_OVO, self.aparencia(i))
            w, h = base.get_size()
            silhueta = base.copy()
            silhueta.fill((0, 0, 0), special_flags=pygame.BLEND_RGB_MULT)
            # Ovo escuro ganha contorno claro; ovo claro, contorno escuro
            r, g, b = self.cor(i)
            escuro = 0.3 * r + 0.59 * g + 0.11 * b < 110
            silhueta.fill((235, 235, 245) if escuro else (30, 30, 45), special_flags=pygame.BLEND_RGB_ADD)
            s = pygame.Surface((w + 6, h + 6), pygame.SRCALPHA)
            for dx, dy in OITO:
                s.blit(silhueta, (3 + dx * 2, 3 + dy * 2))
            s.blit(base, (3, 3))
            cache[chave] = s
        return s

    def _desenhar_avisos(self, tela):
        cx = AREA.centerx
        if self.fase == "anuncio":
            painel = pygame.Rect(0, 0, 420, 90)
            painel.center = (cx, AREA.centery)
            ui.painel(tela, painel, (20, 24, 40), AMARELO, 16, 3)
            ui.desenhar_texto(tela, f"ROUND {self.round}!", (cx, painel.centery - 10), 32, AMARELO, "center")
            ui.desenhar_texto(tela, f"QUEM FIZER {self.precisa} VENCE", (cx, painel.centery + 26), 10,
                              BRANCO, "center")
        elif self.fase == "jogo" and self.restante <= 10:
            if (self.tempo * 2) % 1 < 0.7:
                painel = pygame.Rect(0, 0, 440, 50)
                painel.midbottom = (cx, AREA.bottom - 10)
                ui.painel(tela, painel, (20, 24, 40), (255, 120, 120), 14, 3)
                ui.desenhar_texto(tela, "ÚLTIMOS SEGUNDOS!", painel.center, 18, (255, 150, 150), "center")
        elif self.fase in ("contando", "resultado"):
            self._desenhar_placar_final(tela)

    def _desenhar_placar_final(self, tela):
        ui.veu(tela, 120)
        painel = pygame.Rect(0, 0, 640, 400)
        painel.center = (LARGURA // 2, AREA.centery)
        ui.painel(tela, painel, (28, 32, 56), self.COR, 20, 4)
        ui.desenhar_texto(tela, "QUEM PINTOU MAIS?", (painel.centerx, painel.y + 22), 20, AMARELO, "midtop")

        # Barras crescendo
        k = min(1.0, self.tempo_fase / 1.8) if self.fase == "contando" else 1.0
        k = 1 - (1 - k) ** 3
        base = painel.bottom - 70
        for i in (0, 1):
            x = painel.centerx + (-130 if i == 0 else 130)
            pct = self.final[i] * k
            h = int(200 * pct / max(1.0, max(self.final)))      # quem pintou mais enche a barra
            barra = pygame.Rect(0, 0, 90, max(4, h))
            barra.midbottom = (x, base)
            pygame.draw.rect(tela, self.tintas[i], barra, border_radius=8)
            pygame.draw.rect(tela, BRANCO, barra, 3, border_radius=8)
            ui.desenhar_texto(tela, f"{pct:.1f}%", (x, barra.top - 8), 16, BRANCO, "midbottom")
            ui.desenhar_texto(tela, self.nome(i)[:12], (x, base + 12), 12, CORES_JOGADOR[i], "midtop")

            # Ovos: o vencedor pula, o perdedor leva um SPLAT de tinta
            ox = x + (-110 if i == 0 else 110)
            oy = base - 60
            if self.fase == "resultado" and self.vencedor_round == i:
                oy -= abs(math.sin(self.tempo * 6)) * 16
            self.desenhar_ovo(tela, i, (ox, oy), 64, espelhar=(i == 1))
            if self.fase == "resultado" and self.vencedor_round == 1 - i:
                self._splat(tela, (ox, oy - 4), self.tintas[1 - i])

        if self.fase == "resultado":
            if self.vencedor_round is None:
                texto, cor = "EMPATE!", AMARELO
            else:
                texto, cor = f"{self.nome(self.vencedor_round)[:12]} VENCEU!", CORES_JOGADOR[self.vencedor_round]
            ui.desenhar_texto(tela, texto, (painel.centerx, painel.y + 62), 16, cor, "midtop")

    def _splat(self, tela, centro, cor):
        """Mancha de tinta na cara do perdedor."""
        x, y = centro
        rnd = random.Random(3)
        escura = ui.escurecer(cor, 50)
        pygame.draw.circle(tela, escura, (int(x), int(y)), 23)
        pygame.draw.circle(tela, cor, (int(x), int(y)), 21)
        for _ in range(8):
            a = rnd.uniform(0, math.tau)
            d = rnd.uniform(18, 30)
            pygame.draw.circle(tela, cor, (int(x + math.cos(a) * d), int(y + math.sin(a) * d)), rnd.randint(4, 8))
        for dx in (-10, 4, 14):
            comp = rnd.randint(14, 26)
            pygame.draw.line(tela, cor, (x + dx, y + 10), (x + dx, y + 10 + comp), 6)
            pygame.draw.circle(tela, cor, (int(x + dx), int(y + 10 + comp)), 4)
        pygame.draw.circle(tela, ui.misturar(cor, BRANCO, 0.6), (int(x - 8), int(y - 8)), 5)
        ui.desenhar_texto(tela, "SPLAT!", (x, y - 44), 14, BRANCO, "center")

    def desenhar_hud(self, tela):
        # Painéis dos jogadores
        for i in (0, 1):
            ovo = self.ovos[i]
            caixa = pygame.Rect(0, 12, 330, 50)
            if i == 0:
                caixa.x = 12
            else:
                caixa.right = LARGURA - 76
            ui.painel(tela, caixa, (20, 24, 40), CORES_JOGADOR[i], 12, 3, sombra=False)
            esq = i == 0
            icone = (caixa.x + 26, caixa.centery) if esq else (caixa.right - 26, caixa.centery)
            self.desenhar_ovo(tela, i, icone, 30, espelhar=not esq)
            nx = caixa.x + 50 if esq else caixa.right - 50
            ui.desenhar_texto(tela, self.nome(i)[:12], (nx, caixa.y + 8), 12, CORES_JOGADOR[i],
                              "topleft" if esq else "topright")

            # Balões (cargas) e recarga
            for k in range(CARGAS):
                bx = nx + 10 + k * 26 if esq else nx - 10 - k * 26
                s = _balao_mini(self.tintas[i]) if k < ovo.cargas else _balao_vazio()
                tela.blit(s, s.get_rect(center=(bx, caixa.y + 36)))
            if ovo.cargas < CARGAS:
                bx = nx + 10 + ovo.cargas * 26 if esq else nx - 10 - ovo.cargas * 26
                larg = int(18 * ovo.recarga / RECARGA)
                pygame.draw.rect(tela, BRANCO, (bx - 9, caixa.y + 44, larg, 3))

            # Itens ativos
            x = nx + 70 if esq else nx - 70
            for tipo, tempo in (("rolo", ovo.rolo), ("tenis", ovo.tenis)):
                if tempo > 0:
                    s = _icone_hud(tipo)
                    tela.blit(s, s.get_rect(center=(x, caixa.y + 36)))
                    ui.desenhar_texto(tela, f"{math.ceil(tempo)}", (x + (14 if esq else -14), caixa.y + 37),
                                      10, BRANCO, "midleft" if esq else "midright")
                    x += 50 if esq else -50

            # Rounds (bolinhas)
            if self.precisa > 1:
                for k in range(self.precisa):
                    bx = caixa.right - 18 - k * 20 if esq else caixa.x + 18 + k * 20
                    cor = AMARELO if k < self.vitorias_round[i] else (60, 64, 90)
                    pygame.draw.circle(tela, cor, (bx, caixa.y + 16), 7)
                    pygame.draw.circle(tela, BRANCO, (bx, caixa.y + 16), 7, 2)

        # Relógio
        caixa = pygame.Rect(0, 12, 150, 50)
        caixa.centerx = (12 + 330 + LARGURA - 76 - 330) // 2
        ui.painel(tela, caixa, (20, 24, 40), BRANCO, 12, 3, sombra=False)
        seg = max(0, math.ceil(self.restante))
        cor = (255, 150, 150) if seg <= 10 else BRANCO
        ui.desenhar_texto(tela, f"{seg // 60}:{seg % 60:02d}", (caixa.centerx, caixa.centery - 7), 16, cor, "center")
        ui.desenhar_texto(tela, f"ROUND {self.round}", (caixa.centerx, caixa.centery + 14), 10,
                          (180, 200, 255), "center")

        # Barra de porcentagem: uma cor "empurra" a outra
        barra = pygame.Rect(AREA.x, 74, AREA.w, 28)
        pygame.draw.rect(tela, (20, 24, 40), barra.inflate(8, 8), border_radius=12)
        pygame.draw.rect(tela, (200, 200, 195), barra, border_radius=10)
        p0, p1 = self.porcentagem(0), self.porcentagem(1)
        w0 = int(barra.w * p0 / 100)
        w1 = int(barra.w * p1 / 100)
        if w0 > 0:
            pygame.draw.rect(tela, self.tintas[0], (barra.x, barra.y, w0, barra.h),
                             border_top_left_radius=10, border_bottom_left_radius=10)
        if w1 > 0:
            pygame.draw.rect(tela, self.tintas[1], (barra.right - w1, barra.y, w1, barra.h),
                             border_top_right_radius=10, border_bottom_right_radius=10)
        pygame.draw.rect(tela, BRANCO, barra, 2, border_radius=10)
        ui.desenhar_texto(tela, f"{p0:.0f}%", (barra.x + 10, barra.centery + 1), 14, BRANCO, "midleft")
        ui.desenhar_texto(tela, f"{p1:.0f}%", (barra.right - 10, barra.centery + 1), 14, BRANCO, "midright")


# ============================================================
# CACHES
# ============================================================

_piso = None


def _piso_limpo():
    """Piso claro com rejunte (tamanho da arena)."""
    global _piso
    if _piso is None:
        _piso = pygame.Surface(AREA.size)
        _piso.fill(PISO)
        for c in range(COLS + 1):
            pygame.draw.line(_piso, REJUNTE, (c * CEL, 0), (c * CEL, AREA.h), 1)
        for l in range(LINHAS + 1):
            pygame.draw.line(_piso, REJUNTE, (0, l * CEL), (AREA.w, l * CEL), 1)
        rnd = random.Random(4)
        for _ in range(300):
            x, y = rnd.randrange(AREA.w), rnd.randrange(AREA.h)
            pygame.draw.circle(_piso, (235, 235, 228), (x, y), 1)
    return _piso


def _balao_mini(cor):
    chave = ("balao_mini", cor)
    s = _sprites.get(chave)
    if s is None:
        s = _sprites[chave] = pygame.transform.smoothscale(_balao_sup(cor), (16, 20))
    return s


def _balao_vazio():
    s = _sprites.get("balao_vazio")
    if s is None:
        s = pygame.Surface((16, 20), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (90, 94, 120), (1, 1, 14, 15), 2)
        pygame.draw.line(s, (90, 94, 120), (8, 16), (8, 19), 2)
        _sprites["balao_vazio"] = s
    return s


def _icone_hud(tipo):
    chave = ("hud", tipo)
    s = _sprites.get(chave)
    if s is None:
        s = _sprites[chave] = pygame.transform.smoothscale(_item_sup(tipo), (22, 22))
    return s
