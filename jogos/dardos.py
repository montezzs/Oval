import math
import random

import pygame

from settings import *
from core import ui
from jogos.base_hibrido import MiniJogoHibrido
from jogos.base_multi import TECLAS_MOVER, TECLAS_ACAO, CORES_JOGADOR
from jogos.boliche import desenhar_inicio_hibrido, ajustar_botoes_hibrido

# ============================================================
# DARDOS 301 (VS BOT OU 2 JOGADORES POR TURNOS)
# ============================================================
# Alvo oficial (setores, duplo, triplo, bull). A mão treme: o
# círculo mostra a tremedeira. SEGURAR ESPAÇO/mouse estabiliza e
# carrega a força; SOLTAR lança. Força ideal ~70% (fraco cai,
# forte sobe) e segurar demais cansa o braço. 3 dardos por vez,
# 301 pontos, tem que zerar EXATO (passou = ESTOUROU, volta).

C = (604, 396)
ESC = 250 / 170                    # mm -> px
R_BULL_IN = 6.35 * ESC
R_BULL = 15.9 * ESC
R_TRI_IN = 99 * ESC
R_TRI_OUT = 107 * ESC
R_DUP_IN = 162 * ESC
R_DUP_OUT = 170 * ESC
R_NUM = 276
R_FUNDO = 304
ORDEM = [20, 1, 18, 4, 13, 6, 10, 15, 2, 17, 3, 19, 7, 16, 8, 11, 14, 9, 12, 5]

INICIO = 301
RODADAS = 12
FORCA_IDEAL = 0.7
TEMPO_CARGA = 1.6                  # segundos para a força encher
TREMOR_SOLTO = 42
TREMOR_MIN = 7
CANSA = 2.2                        # segurando mais que isso o braço cansa
QUEDA = 170                        # px de desvio por força errada
VEL_MIRA = 320
T_VOO = 0.28
MAO = (930, 700)

_cache = {}


def valor_em(x, y):
    """(pontos, rótulo) do ponto na tela."""
    dx, dy = x - C[0], y - C[1]
    r = math.hypot(dx, dy)
    if r <= R_BULL_IN:
        return 50, "BULL!"
    if r <= R_BULL:
        return 25, "25"
    if r > R_DUP_OUT:
        return 0, "FORA"
    ang = math.degrees(math.atan2(dx, -dy)) % 360
    n = ORDEM[int(((ang + 9) % 360) // 18)]
    if R_TRI_IN <= r <= R_TRI_OUT:
        return 3 * n, f"T{n}"
    if R_DUP_IN <= r:
        return 2 * n, f"D{n}"
    return n, str(n)


def ponto_alvo(n, mult):
    """Centro da região (n, mult) na tela. n=25/50 são o bull."""
    if n == 50:
        return C
    if n == 25:
        r = (R_BULL_IN + R_BULL) / 2
        return C[0], C[1] - r
    ang = math.radians(ORDEM.index(n) * 18)
    r = {1: (R_TRI_OUT + R_DUP_IN) / 2, 2: (R_DUP_IN + R_DUP_OUT) / 2,
         3: (R_TRI_IN + R_TRI_OUT) / 2}[mult]
    return C[0] + math.sin(ang) * r, C[1] - math.cos(ang) * r


def fecha(x):
    """Jeito mais fácil de fazer exatamente x com 1 dardo (ou None)."""
    if 1 <= x <= 20:
        return (x, 1)
    if x == 25:
        return (25, 1)
    if x % 2 == 0 and x <= 40:
        return (x // 2, 2)
    if x % 3 == 0 and x <= 60:
        return (x // 3, 3)
    if x == 50:
        return (50, 1)
    return None


def rotulo_alvo(a):
    n, m = a
    if n == 50:
        return "BULL"
    if n == 25:
        return "25"
    return {1: "", 2: "D", 3: "T"}[m] + str(n)


def estrategia(resta):
    f = fecha(resta)
    if f:
        return f
    cands = [(3 * n, (n, 3)) for n in (20, 19, 18, 17, 16)] + [(n, (n, 1)) for n in range(20, 0, -1)]
    for v, a in cands:
        sobra = resta - v
        if sobra >= 2 and (sobra > 60 or fecha(sobra)):
            return a
    return (1, 1)


def _arco(r, a1, a2, passos=5):
    return [(C[0] + math.sin(math.radians(a1 + (a2 - a1) * k / passos)) * r,
             C[1] - math.cos(math.radians(a1 + (a2 - a1) * k / passos)) * r) for k in range(passos + 1)]


def _dardo_base(cor):
    chave = ("dardo", cor)
    sup = _cache.get(chave)
    if sup is None:
        sup = pygame.Surface((64, 64), pygame.SRCALPHA)
        # Ponta (8,56) -> corpo -> pena de galinha
        pygame.draw.line(sup, (200, 200, 210), (8, 56), (20, 44), 2)
        pygame.draw.line(sup, (90, 90, 100), (19, 45), (34, 30), 6)
        pygame.draw.line(sup, cor, (25, 39), (29, 35), 7)
        pygame.draw.line(sup, (230, 230, 240), (33, 31), (42, 22), 2)
        pena = [(40, 24), (46, 6), (58, 2), (62, 10), (56, 20), (46, 26)]
        pygame.draw.polygon(sup, (250, 246, 232), pena)
        pygame.draw.polygon(sup, (120, 90, 60), pena, 2)
        for k in range(3):
            pygame.draw.line(sup, (200, 150, 90), (44 + k * 4, 22 - k * 2), (50 + k * 4, 8 + k), 1)
        pygame.draw.circle(sup, (220, 40, 40), (58, 5), 3)
        _cache[chave] = sup
    return sup


def dardo_sprite(cor, escala):
    e = round(escala * 10) / 10
    chave = ("dardo", cor, e)
    sup = _cache.get(chave)
    if sup is None:
        base = _dardo_base(cor)
        sup = base if e == 1.0 else pygame.transform.rotozoom(base, 0, e)
        _cache[chave] = sup
    return sup


class Dardos(MiniJogoHibrido):

    ID = "dardos"
    TITULO = "DARDOS"
    DESCRICAO = "301 no alvo do galinheiro! Segure para firmar a mão e solte com a força certa."
    COR = (200, 60, 60)
    INSTRUCOES = [
        "MIRE com WASD/SETAS ou o MOUSE. A mão treme (o círculo)!",
        "SEGURE ESPAÇO/CLIQUE para firmar e carregar; SOLTE para lançar.",
        "Força ideal: faixa verde (fraco cai, forte sobe). Segurar demais cansa.",
        "301: 3 dardos por vez, ZERE EXATO. Passou? ESTOUROU e volta!",
    ]
    CONTROLES_J1 = "ESPAÇO / MOUSE"
    CONTROLES_J2 = "ENTER / MOUSE"
    TEMPO_MINIMO = 25.0

    TRILHA = dict(bpm=100, tom="G", escala="blues", lead="triangulo", envelope="pluck",
                  baixo="walking", onda_baixo="seno", acomp="contratempo", onda_acomp="sino",
                  bateria="shuffle", energia=0.45, eco=(0.2, 0.25))

    # --------------------------------------------------------
    # CENÁRIO
    # --------------------------------------------------------

    @classmethod
    def criar_fundo(cls, jogador):
        sup = pygame.Surface((LARGURA, ALTURA))
        # Parede de tábuas do galinheiro
        for k in range(0, LARGURA, 64):
            cor = (120, 78, 48) if (k // 64) % 2 == 0 else (110, 70, 42)
            pygame.draw.rect(sup, cor, (k, 0, 64, ALTURA))
            pygame.draw.line(sup, (70, 42, 26), (k, 0), (k, ALTURA), 3)
            for y in (80 + (k * 7) % 200, 420 + (k * 13) % 200):
                pygame.draw.circle(sup, (60, 38, 24), (k + 20, y), 3)
        # Luz em cima do alvo
        luz = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        for r in range(360, 0, -40):
            pygame.draw.circle(luz, (255, 230, 170, 10), C, r)
        sup.blit(luz, (0, 0))
        # Fundo preto com números
        pygame.draw.circle(sup, (30, 20, 16), (C[0] + 6, C[1] + 8), R_FUNDO)
        pygame.draw.circle(sup, (24, 24, 28), C, R_FUNDO)
        pygame.draw.circle(sup, (70, 70, 80), C, R_FUNDO, 3)
        for i, n in enumerate(ORDEM):
            a = math.radians(i * 18)
            ui.desenhar_texto(sup, str(n), (C[0] + math.sin(a) * R_NUM, C[1] - math.cos(a) * R_NUM),
                              16, BRANCO, "center")
        # Setores
        for i in range(20):
            a1, a2 = i * 18 - 9, i * 18 + 9
            simples = (28, 28, 30) if i % 2 == 0 else (238, 222, 186)
            anel = (205, 40, 40) if i % 2 == 0 else (40, 150, 70)
            for r1, r2, cor in ((R_BULL, R_TRI_IN, simples), (R_TRI_IN, R_TRI_OUT, anel),
                                (R_TRI_OUT, R_DUP_IN, simples), (R_DUP_IN, R_DUP_OUT, anel)):
                pts = _arco(r2, a1, a2) + _arco(r1, a2, a1)
                pygame.draw.polygon(sup, cor, pts)
        pygame.draw.circle(sup, (40, 150, 70), C, int(R_BULL))
        pygame.draw.circle(sup, (205, 40, 40), C, int(R_BULL_IN))
        # Arames
        for r in (R_BULL_IN, R_BULL, R_TRI_IN, R_TRI_OUT, R_DUP_IN, R_DUP_OUT):
            pygame.draw.circle(sup, (190, 190, 200), C, int(r), 1)
        for i in range(20):
            a = math.radians(i * 18 - 9)
            p1 = (C[0] + math.sin(a) * R_BULL, C[1] - math.cos(a) * R_BULL)
            p2 = (C[0] + math.sin(a) * R_DUP_OUT, C[1] - math.cos(a) * R_DUP_OUT)
            pygame.draw.line(sup, (190, 190, 200), p1, p2, 1)
        # Enfeites: fardo de feno e penas
        pygame.draw.rect(sup, (220, 180, 80), (LARGURA - 150, ALTURA - 90, 140, 80), border_radius=8)
        for k in range(5):
            pygame.draw.line(sup, (180, 140, 50), (LARGURA - 146, ALTURA - 80 + k * 15),
                             (LARGURA - 14, ALTURA - 84 + k * 15), 2)
        return sup

    @classmethod
    def desenhar_icone(cls, sup, jogador):
        w, h = sup.get_size()
        cx, cy = int(w * 0.42), int(h * 0.5)
        r = int(h * 0.36)
        for k, cor in enumerate(((24, 24, 28), (205, 40, 40), (238, 222, 186), (40, 150, 70), (205, 40, 40))):
            pygame.draw.circle(sup, cor, (cx, cy), max(2, r - k * r // 5))
        d = _dardo_base((110, 230, 120))
        sup.blit(d, (cx - 8, cy - 56))
        jogador.desenhar(sup, (w * 0.82, h * 0.62), h * 0.34)

    # --------------------------------------------------------
    # PARTIDA
    # --------------------------------------------------------

    def __init__(self, app, menu):
        self.seguradas = set()
        super().__init__(app, menu)

    def _montar_menu_inicio(self):
        super()._montar_menu_inicio()
        ajustar_botoes_hibrido(self)

    def _desenhar_inicio(self, tela):
        desenhar_inicio_hibrido(self, tela)

    def reiniciar(self):
        self.resta = [INICIO, INICIO]
        self.vez = 0
        self.rodada = 1
        self.cravados = []            # (x, y, dono)
        self.voo = None
        self.banner = None
        self.fase = "mirar"
        self.tempo_fase = 0.0
        self.historico = [[], []]     # pontos por turno
        self._novo_turno()

    def _eh_bot(self):
        return self.solo and self.vez == 1

    def _novo_turno(self):
        self.turno = []               # rótulos dos dardos deste turno
        self.inicio_turno = self.resta[self.vez]
        self.cravados = []
        self._novo_dardo()

    def _novo_dardo(self):
        self.fase = "mirar"
        self.tempo_fase = 0.0
        self.segurando = False
        self.t_segura = 0.0
        self.mira = [C[0], C[1] - (R_TRI_IN + R_TRI_OUT) / 2 + 60]
        self.fase_tremor = random.uniform(0, 100)
        self.plano = None
        if self._eh_bot():
            d = self.dificuldade
            alvo = estrategia(self.resta[1])
            px, py = ponto_alvo(*alvo)
            self.plano = {"alvo": (px, py), "rot": rotulo_alvo(alvo),
                          "t": max(0.5, random.gauss(TEMPO_CARGA * FORCA_IDEAL, [0.3, 0.15, 0.07][d])),
                          "erro": [17, 10, 4.5][d], "espera": random.uniform(0.3, 0.6)}

    # --------------------------------------------------------
    # MÃO TREMENDO + FORÇA
    # --------------------------------------------------------

    def forca(self):
        return min(1.0, self.t_segura / TEMPO_CARGA) if self.segurando else 0.0

    def amplitude(self):
        if not self.segurando:
            return TREMOR_SOLTO
        t = self.t_segura
        if t < 1.1:
            return TREMOR_SOLTO + (TREMOR_MIN - TREMOR_SOLTO) * (t / 1.1)
        if t < CANSA:
            return TREMOR_MIN
        return TREMOR_MIN + (t - CANSA) * 45

    def oscilacao(self):
        a = self.amplitude()
        t = self.tempo * 1.0 + self.fase_tremor
        return (a * (math.sin(t * 2.7) * 0.6 + math.sin(t * 4.9 + 1.3) * 0.4),
                a * (math.cos(t * 2.2) * 0.6 + math.sin(t * 5.3 + 0.4) * 0.4))

    # --------------------------------------------------------
    # CONTROLES
    # --------------------------------------------------------

    def evento(self, e):
        if e.type == pygame.KEYDOWN:
            self.seguradas.add(e.key)
        elif e.type == pygame.KEYUP:
            self.seguradas.discard(e.key)
        elif e.type == pygame.WINDOWFOCUSLOST:
            self.seguradas.clear()
            if self.estado == "jogando" and getattr(self, "segurando", False):
                self.segurando = False
        super().evento(e)

    def evento_jogo(self, e):
        if self._eh_bot() or self.fase != "mirar":
            return
        acao = TECLAS_ACAO[0] + TECLAS_ACAO[1]
        if e.type == pygame.MOUSEMOTION:
            self.mira = [float(e.pos[0]), float(e.pos[1])]
        if (e.type == pygame.KEYDOWN and e.key in acao) or (e.type == pygame.MOUSEBUTTONDOWN and e.button == 1):
            if not self.segurando:
                self.segurando = True
                self.t_segura = 0.0
                self._mexeu[self.vez if not self.solo else 0] = True
        elif (e.type == pygame.KEYUP and e.key in acao) or (e.type == pygame.MOUSEBUTTONUP and e.button == 1):
            if self.segurando:
                self._lancar()

    def _lancar(self):
        dx, dy = self.oscilacao()
        f = self.forca()
        alvo = (self.mira[0] + dx, self.mira[1] + dy + (FORCA_IDEAL - f) * QUEDA)
        if self.plano:
            e = self.plano["erro"]
            alvo = (alvo[0] + random.gauss(0, e), alvo[1] + random.gauss(0, e))
        self.segurando = False
        self.voo = {"de": MAO, "para": alvo, "t": 0.0}
        self.fase = "voando"
        self.tempo_fase = 0.0
        self.som("asa", 0.6)

    # --------------------------------------------------------
    # LOOP
    # --------------------------------------------------------

    def atualizar_jogo(self, dt):
        self.tempo_fase += dt
        if self.banner:
            self.banner[2] -= dt
            if self.banner[2] <= 0:
                self.banner = None

        if self.fase == "mirar":
            if self.segurando:
                self.t_segura += dt
                if self.t_segura > 4.0 and not self._eh_bot():
                    self._lancar()
                    return
            if self._eh_bot():
                self._atualizar_bot(dt)
            else:
                k = self.seguradas
                vx = vy = 0
                for i in (0, 1):
                    t = TECLAS_MOVER[i]
                    vx += (t["dir"] in k) - (t["esq"] in k)
                    vy += (t["baixo"] in k) - (t["cima"] in k)
                vx, vy = max(-1, min(1, vx)), max(-1, min(1, vy))
                vel = VEL_MIRA * (0.45 if self.segurando else 1.0)
                self.mira[0] = max(C[0] - R_FUNDO, min(C[0] + R_FUNDO, self.mira[0] + vx * vel * dt))
                self.mira[1] = max(C[1] - R_FUNDO, min(C[1] + R_FUNDO, self.mira[1] + vy * vel * dt))

        elif self.fase == "voando":
            self.voo["t"] += dt
            if self.voo["t"] >= T_VOO:
                self._cravar(self.voo["para"])

        elif self.fase == "troca":
            if self.tempo_fase > 1.5:
                self._trocar_vez()

        elif self.fase == "espera":
            if self.tempo_fase > 0.5:
                self._novo_dardo()

    def _atualizar_bot(self, dt):
        p = self.plano
        if self.tempo_fase < p["espera"]:
            return
        dx, dy = p["alvo"][0] - self.mira[0], p["alvo"][1] - self.mira[1]
        dist = math.hypot(dx, dy)
        if dist > 2 and not self.segurando:
            passo = min(dist, VEL_MIRA * dt)
            self.mira[0] += dx / dist * passo
            self.mira[1] += dy / dist * passo
            return
        self.mira = list(p["alvo"])
        if not self.segurando:
            self.segurando = True
            self.t_segura = 0.0
        elif self.t_segura >= p["t"]:
            self._lancar()

    def _cravar(self, pos):
        self.voo = None
        x, y = pos
        pts, rot = valor_em(x, y)
        if pts > 0 or math.hypot(x - C[0], y - C[1]) < R_FUNDO:
            self.cravados.append((x, y, self.vez))
        cor = CORES_JOGADOR[self.vez]
        if pts == 0:
            self.som("erro", 0.6)
        elif rot.startswith("T") or pts >= 25:
            self.som("acerto")
            self.particulas.explodir((x, y), [AMARELO, BRANCO, (255, 200, 120)], 18, 240, 0.6)
        else:
            self.som("bater", 0.7)
        self.textos.adicionar(rot if pts else "FORA!", (x, y - 30), AMARELO if pts >= 25 or rot[0] == "T" else cor, 14)
        self.turno.append(rot if pts else "0")

        novo = self.resta[self.vez] - pts
        if novo < 0:
            self.resta[self.vez] = self.inicio_turno
            self.banner = ["ESTOUROU!", (255, 120, 100), 1.5]
            self.som("perder", 0.7)
            self.tremer(0.2)
            self._fim_turno()
            return
        self.resta[self.vez] = novo
        if novo == 0:
            self.banner = ["ZEROU!", AMARELO, 2.0]
            self.particulas.explodir((x, y), [AMARELO, BRANCO, (120, 255, 150), (255, 90, 140)], 50, 420, 1.2)
            self._fim(self.vez)
            return
        if len(self.turno) >= 3:
            self._fim_turno()
        else:
            self.fase = "espera"
            self.tempo_fase = 0.0

    def _fim_turno(self):
        self.historico[self.vez].append(self.inicio_turno - self.resta[self.vez])
        self.fase = "troca"
        self.tempo_fase = 0.0

    def _trocar_vez(self):
        if self.vez == 1:
            self.rodada += 1
            if self.rodada > RODADAS:
                r = self.resta
                self._fim(None if r[0] == r[1] else (0 if r[0] < r[1] else 1))
                return
        self.vez = 1 - self.vez
        self._novo_turno()

    def _fim(self, vencedor):
        self.fase = "fim"
        self.pontos = INICIO - self.resta[0]
        medias = []
        for i in (0, 1):
            h = self.historico[i]
            medias.append(round(sum(h) / len(h)) if h else 0)
        linhas = [f"RESTAM  {self.resta[0]} × {self.resta[1]}",
                  f"MÉDIA POR TURNO  {medias[0]} × {medias[1]}"]
        if vencedor is not None and self.resta[vencedor] == 0:
            linhas.insert(0, f"{self.nome(vencedor)[:12]} ZEROU NA RODADA {self.rodada}!")
        self.terminar_multi(vencedor, linhas)

    # --------------------------------------------------------
    # DESENHO
    # --------------------------------------------------------

    def desenhar_jogo(self, tela):
        tela.blit(self.fundo(self.jogador), (0, 0))
        for x, y, dono in self.cravados:
            spr = dardo_sprite(CORES_JOGADOR[dono], 1.0)
            tela.blit(spr, (x - 8, y - 56))

        if self.fase == "mirar":
            mx, my = self.mira
            tx, ty = self.oscilacao()
            a = int(self.amplitude())
            cor = CORES_JOGADOR[self.vez]
            pygame.draw.circle(tela, cor, (int(mx), int(my)), max(4, a), 2)
            px, py = int(mx + tx), int(my + ty)
            pygame.draw.circle(tela, BRANCO, (px, py), 6, 2)
            pygame.draw.line(tela, BRANCO, (px - 12, py), (px - 4, py), 2)
            pygame.draw.line(tela, BRANCO, (px + 4, py), (px + 12, py), 2)
            pygame.draw.line(tela, BRANCO, (px, py - 12), (px, py - 4), 2)
            pygame.draw.line(tela, BRANCO, (px, py + 4), (px, py + 12), 2)

        # O ovo lançador no canto (com o dardo na mão)
        ovo_y = MAO[1] - 50 + (0 if self.fase != "mirar" else math.sin(self.tempo * 3) * 3)
        self.desenhar_ovo(tela, self.vez, (MAO[0] + 20, ovo_y), 96, espelhar=True)
        if self.fase in ("mirar", "espera"):
            tela.blit(dardo_sprite(CORES_JOGADOR[self.vez], 1.4), (MAO[0] - 70, MAO[1] - 150))

        if self.voo:
            v = self.voo
            t = min(1.0, v["t"] / T_VOO)
            (x1, y1), (x2, y2) = v["de"], v["para"]
            x = x1 + (x2 - x1) * t
            y = y1 + (y2 - y1) * t - math.sin(t * math.pi) * 90
            esc = 2.2 - 1.2 * t
            spr = dardo_sprite(CORES_JOGADOR[self.vez], esc)
            tela.blit(spr, (x - 8 * esc, y - 56 * esc))

        self.particulas.desenhar(tela)
        self.textos.desenhar(tela)
        if self.banner:
            texto, cor, _ = self.banner
            ui.desenhar_texto(tela, texto, (C[0], C[1]), 44, cor, "center")
        elif self.fase == "troca":
            pts = self.inicio_turno - self.resta[self.vez]
            ui.desenhar_texto(tela, f"TURNO: {pts}", (C[0], C[1]), 32, AMARELO, "center")

    def desenhar_hud(self, tela):
        caixa = pygame.Rect(14, 14, 272, 692)
        ui.painel(tela, caixa, (20, 24, 40), BRANCO, 14, 3, sombra=False)
        ui.desenhar_texto(tela, "301", (caixa.centerx, caixa.y + 12), 20, AMARELO, "midtop")
        ui.desenhar_texto(tela, f"RODADA {min(self.rodada, RODADAS)}/{RODADAS}", (caixa.centerx, caixa.y + 42),
                          10, (180, 200, 255), "midtop")
        for i in (0, 1):
            r = pygame.Rect(caixa.x + 12, caixa.y + 70 + i * 132, caixa.w - 24, 120)
            ativo = (i == self.vez)
            pygame.draw.rect(tela, (44, 50, 80) if ativo else (30, 34, 54), r, border_radius=10)
            if ativo:
                pygame.draw.rect(tela, CORES_JOGADOR[i], r, 3, border_radius=10)
            ui.desenhar_texto(tela, self.nome(i)[:12], (r.x + 12, r.y + 12), 12, CORES_JOGADOR[i], "topleft")
            ui.desenhar_texto(tela, str(self.resta[i]), (r.centerx, r.y + 40), 36, BRANCO, "midtop")
            h = self.historico[i]
            if h:
                ui.desenhar_texto(tela, f"ÚLTIMO: {h[-1]}", (r.centerx, r.bottom - 18), 8,
                                  (200, 200, 220), "midtop")

        # Dardos do turno
        y = caixa.y + 348
        ui.desenhar_texto(tela, "DARDOS DO TURNO", (caixa.centerx, y), 10, BRANCO, "midtop")
        for k in range(3):
            r = pygame.Rect(caixa.x + 20 + k * 80, y + 22, 70, 40)
            pygame.draw.rect(tela, (30, 34, 54), r, border_radius=8)
            pygame.draw.rect(tela, (90, 90, 130), r, 2, border_radius=8)
            if k < len(self.turno):
                ui.desenhar_texto(tela, self.turno[k], r.center, 12, AMARELO, "center")

        # Saída sugerida
        f = fecha(self.resta[self.vez])
        if f and self.fase in ("mirar", "espera"):
            ui.desenhar_texto(tela, f"SAÍDA: {rotulo_alvo(f)}", (caixa.centerx, y + 76), 12,
                              (120, 255, 150), "midtop")

        # Força e firmeza
        y = caixa.y + 460
        barra = pygame.Rect(caixa.x + 24, y + 22, caixa.w - 48, 22)
        ui.desenhar_texto(tela, "FORÇA", (caixa.centerx, y), 10, BRANCO, "midtop")
        pygame.draw.rect(tela, (50, 50, 70), barra, border_radius=6)
        zona = pygame.Rect(barra.x + int(barra.w * (FORCA_IDEAL - 0.08)), barra.y, int(barra.w * 0.16), barra.h)
        pygame.draw.rect(tela, (60, 140, 70), zona)
        f = self.forca()
        pygame.draw.rect(tela, AMARELO, (barra.x, barra.y + 6, int(barra.w * f), barra.h - 12))
        pygame.draw.rect(tela, BRANCO, barra, 2, border_radius=6)

        y += 64
        ui.desenhar_texto(tela, "FIRMEZA DA MÃO", (caixa.centerx, y), 10, BRANCO, "midtop")
        barra = pygame.Rect(caixa.x + 24, y + 22, caixa.w - 48, 22)
        pygame.draw.rect(tela, (50, 50, 70), barra, border_radius=6)
        firme = 1 - (min(TREMOR_SOLTO, self.amplitude()) - TREMOR_MIN) / (TREMOR_SOLTO - TREMOR_MIN)
        cor = ui.misturar((230, 70, 70), (90, 200, 90), firme)
        pygame.draw.rect(tela, cor, (barra.x, barra.y, int(barra.w * max(0.02, firme)), barra.h), border_radius=6)
        pygame.draw.rect(tela, BRANCO, barra, 2, border_radius=6)
        if self.segurando and self.t_segura > CANSA:
            ui.desenhar_texto(tela, "BRAÇO CANSANDO!", (caixa.centerx, y + 52), 10, (255, 140, 120), "midtop")
        elif self._eh_bot():
            ui.desenhar_texto(tela, "BOT MIRANDO...", (caixa.centerx, y + 52), 10, (180, 200, 255), "midtop")
        else:
            ui.desenhar_texto(tela, "SEGURE E SOLTE", (caixa.centerx, y + 52), 10, (180, 200, 255), "midtop")
