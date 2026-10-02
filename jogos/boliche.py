import math
import random

import pygame

from settings import *
from core import ui
from jogos.base_hibrido import MiniJogoHibrido
from jogos.base_multi import TECLAS_MOVER, TECLAS_ACAO, CORES_JOGADOR

# ============================================================
# BOLICHE (VS BOT OU 2 JOGADORES POR TURNOS)
# ============================================================
# Pista em perspectiva vista de trás. A bola é o próprio ovo!
# Cada jogada tem 3 toques: MIRA (seta oscilando) -> FORÇA
# (barra) -> EFEITO (curva). 10 pinos com colisão em cadeia e
# placar oficial de 10 frames (strike, spare e bônus do 10º).
# J1 e J2/bot alternam os frames.

# Mundo em "metros": x = lateral (0 no meio), z = distância
LANE = 0.53                 # meia largura da pista
CANAL = 0.61                # x da bola dentro da canaleta
PAREDE = 0.70               # paredes laterais do fundo (os pinos quicam)
Z_PIT = 8.1                 # fim da pista (depois é o poço)
L_VIS = 8.45
Z_BOLA = 0.35
R_BOLA = 0.11
R_PINO = 0.062
M_BOLA = 6.0
M_PINO = 1.5
ALT_PINO = 0.32
AMP_MIRA = 6.0              # graus
HOOK = 1.6                  # curva (m/s²) com efeito máximo
SUB = 1 / 480

# Projeção (pseudo-perspectiva: a pista afina lá no fundo)
Y_B = 712
Y_T = 168
CX = LARGURA // 2
PX = 470
ENCOLHE = 0.62

PINOS_POS = [(0.0, 7.0),
             (-0.152, 7.26), (0.152, 7.26),
             (-0.305, 7.52), (0.0, 7.52), (0.305, 7.52),
             (-0.457, 7.78), (-0.152, 7.78), (0.152, 7.78), (0.457, 7.78)]

COR_PINO = (250, 248, 240)
COR_LISTRA = (220, 40, 50)

_cache = {}


def proj(x, z):
    t = z / L_VIS
    s = 1 - ENCOLHE * t
    return CX + x * PX * s, Y_B - (Y_B - Y_T) * t, s


def _tri(p):
    p %= 2.0
    return p if p < 1 else 2 - p


# ------------------------------------------------------------
# SPRITES EM CACHE
# ------------------------------------------------------------

def _pino_base():
    sup = _cache.get("pino")
    if sup is None:
        sup = pygame.Surface((48, 120), pygame.SRCALPHA)
        partes = [("e", (4, 52, 40, 66)), ("r", (15, 30, 18, 36)), ("e", (12, 4, 24, 34))]
        for cor, inf in (((40, 40, 50), 4), (COR_PINO, 0)):
            for tipo, r in partes:
                r = pygame.Rect(r).inflate(inf, inf)
                if tipo == "e":
                    pygame.draw.ellipse(sup, cor, r)
                else:
                    pygame.draw.rect(sup, cor, r)
        pygame.draw.rect(sup, COR_LISTRA, (14, 34, 20, 4))
        pygame.draw.rect(sup, COR_LISTRA, (14, 42, 20, 4))
        pygame.draw.ellipse(sup, (215, 212, 205), (26, 62, 14, 50))
        pygame.draw.ellipse(sup, BRANCO, (10, 64, 8, 26))
        pygame.draw.ellipse(sup, BRANCO, (16, 10, 6, 10))
        _cache["pino"] = sup
    return sup


def pino_sprite(altura, angulo):
    hb = max(4, int(altura / 3))
    ab = int(round(angulo / 15.0))
    chave = ("p", hb, ab)
    sup = _cache.get(chave)
    if sup is None:
        sup = pygame.transform.rotozoom(_pino_base(), ab * 15, hb * 3 / 120)
        _cache[chave] = sup
    return sup


def desenhar_inicio_hibrido(jogo, tela):
    """Tela de início compacta (4 modos + VISUAL DO J2 + VOLTAR)."""
    ui.veu(tela, 150)
    topo = 24
    caixa = pygame.Rect(0, topo, 760, ALTURA - topo - 24)
    caixa.centerx = LARGURA // 2
    ui.painel(tela, caixa, (28, 32, 56), jogo.COR, 22, 5)

    ui.desenhar_texto(tela, jogo.TITULO, (LARGURA // 2, topo + 20), 28, AMARELO, "midtop")
    sub = f"VS {jogo.nome(1)}" if jogo.solo else "2 JOGADORES"
    ui.desenhar_texto(tela, sub, (LARGURA // 2, topo + 58), 12, (180, 200, 255), "midtop")

    y_ovos = topo + 124
    for i, x in ((0, caixa.x + 150), (1, caixa.right - 150)):
        balanco = math.sin(jogo.tempo * 3 + i * 1.5) * 4
        jogo.desenhar_ovo(tela, i, (x, y_ovos + balanco), 60, espelhar=(i == 1))
        ui.desenhar_texto(tela, jogo.nome(i)[:14], (x, y_ovos + 42), 14, CORES_JOGADOR[i], "midtop")
        if i == 1 and jogo.solo:
            ctrl = "COMPUTADOR"
        else:
            ctrl = jogo.CONTROLES_J1 if i == 0 else jogo.CONTROLES_J2
        ui.desenhar_texto(tela, ctrl, (x, y_ovos + 64), 10, BRANCO, "midtop")
    ui.desenhar_texto(tela, "VS", (LARGURA // 2, y_ovos), 32, AMARELO, "center")

    y = y_ovos + 88
    for linha in jogo.INSTRUCOES:
        for s in ui.quebrar_linhas(linha, 10, caixa.w - 50):
            ui.desenhar_texto(tela, s, (LARGURA // 2, y), 10, BRANCO, "midtop")
            y += 16
        y += 3

    v = jogo.vitorias()
    y_rec = jogo.menu_inicio.botoes[0].rect.y - 32
    ui.desenhar_texto(tela, f"VITÓRIAS  J1 {v[0]} × {v[1]} J2", (LARGURA // 2, y_rec),
                      14, AMARELO, "midtop")
    ui.desenhar_texto(tela, "ESCOLHA O MODO", (LARGURA // 2, y_rec - 24), 12,
                      (180, 200, 255), "midtop")
    jogo.menu_inicio.desenhar(tela)


def ajustar_botoes_hibrido(jogo):
    """Os 4 modos lado a lado: encolhe o texto para caber."""
    for b in jogo.menu_inicio.botoes[:len(jogo.OPCOES)]:
        b.tamanho = ui.tamanho_que_cabe(b.rotulo, b.rect.w - 14, (14, 12, 10, 8))


def pontuacao(frames):
    """Totais acumulados por frame (None = ainda esperando bônus)."""
    bolas = [b for f in frames for b in f]
    idx = 0
    total = 0
    res = []
    for i in range(10):
        f = frames[i]
        if not f:
            break
        if i < 9:
            if f[0] == 10:
                bonus = bolas[idx + 1:idx + 3]
                if len(bonus) < 2:
                    break
                total += 10 + sum(bonus)
                idx += 1
            elif len(f) == 2:
                if sum(f) == 10:
                    bonus = bolas[idx + 2:idx + 3]
                    if not bonus:
                        break
                    total += 10 + bonus[0]
                else:
                    total += sum(f)
                idx += 2
            else:
                break
        else:
            if len(f) == 3 or (len(f) == 2 and sum(f) < 10):
                total += sum(f)
            else:
                break
        res.append(total)
    return res


def marcas(frames, i):
    f = frames[i]

    def n(v):
        return "-" if v == 0 else str(v)

    if i < 9:
        if not f:
            return ["", ""]
        if f[0] == 10:
            return ["", "X"]
        if len(f) == 1:
            return [n(f[0]), ""]
        return [n(f[0]), "/" if sum(f) == 10 else n(f[1])]
    m = ["", "", ""]
    if len(f) >= 1:
        m[0] = "X" if f[0] == 10 else n(f[0])
    if len(f) >= 2:
        if f[0] == 10:
            m[1] = "X" if f[1] == 10 else n(f[1])
        else:
            m[1] = "/" if f[0] + f[1] == 10 else n(f[1])
    if len(f) >= 3:
        if f[0] == 10 and f[1] < 10:
            m[2] = "/" if f[1] + f[2] == 10 else n(f[2])
        else:
            m[2] = "X" if f[2] == 10 else n(f[2])
    return m


class Pino:
    __slots__ = ("x", "z", "vx", "vz", "caido", "queda", "lado", "fora", "ativo")

    def __init__(self, x, z):
        self.x, self.z = x, z
        self.vx = self.vz = 0.0
        self.caido = False
        self.queda = 0.0
        self.lado = 1
        self.fora = False
        self.ativo = True

    @property
    def mexendo(self):
        return abs(self.vx) + abs(self.vz) > 0.04


class Boliche(MiniJogoHibrido):

    ID = "boliche"
    TITULO = "BOLICHE"
    DESCRICAO = "Seu ovo vira a bola! Mire, dose a força e capriche no efeito para fazer STRIKE."
    COR = (150, 70, 200)
    INSTRUCOES = [
        "3 TOQUES: MIRA (seta) -> FORÇA (barra) -> EFEITO (curva).",
        "A/D ou SETAS movem o ovo antes de mirar. 10 frames, placar oficial.",
        "STRIKE = 10 + 2 bolas • SPARE = 10 + 1 bola. Revezam a cada frame.",
    ]
    CONTROLES_J1 = "ESPAÇO / CLIQUE"
    CONTROLES_J2 = "ENTER / CLIQUE"
    TEMPO_MINIMO = 30.0

    # --------------------------------------------------------
    # CENÁRIO
    # --------------------------------------------------------

    @classmethod
    def criar_fundo(cls, jogador):
        sup = ui.gradiente(LARGURA, ALTURA, (40, 20, 70), (14, 10, 30))
        # Pistas vizinhas (apagadas) e piso lateral
        for lado in (-1, 1):
            for k in (1, 2):
                off = lado * 1.55 * k
                pts = [proj(off - LANE, 0)[:2], proj(off + LANE, 0)[:2],
                       proj(off + LANE, Z_PIT)[:2], proj(off - LANE, Z_PIT)[:2]]
                pygame.draw.polygon(sup, (70 - 12 * k, 50 - 8 * k, 60 - 8 * k), pts)
        # Canaletas
        for lado in (-1, 1):
            a, b = sorted((lado * LANE, lado * (LANE + 0.13)))
            pts = [proj(a, 0)[:2], proj(b, 0)[:2], proj(b, Z_PIT)[:2], proj(a, Z_PIT)[:2]]
            pygame.draw.polygon(sup, (60, 60, 75), pts)
            pygame.draw.line(sup, (30, 30, 40), proj(lado * (LANE + 0.065), 0)[:2],
                             proj(lado * (LANE + 0.065), Z_PIT)[:2], 3)
        # Tábuas da pista
        n = 13
        for k in range(n):
            a = -LANE + 2 * LANE * k / n
            b = -LANE + 2 * LANE * (k + 1) / n
            cor = (214, 170, 110) if k % 2 == 0 else (200, 154, 96)
            pts = [proj(a, 0)[:2], proj(b, 0)[:2], proj(b, Z_PIT)[:2], proj(a, Z_PIT)[:2]]
            pygame.draw.polygon(sup, cor, pts)
        # Área dos pinos mais clara (com brilho)
        pts = [proj(-LANE, 6.6)[:2], proj(LANE, 6.6)[:2], proj(LANE, Z_PIT)[:2], proj(-LANE, Z_PIT)[:2]]
        pygame.draw.polygon(sup, (232, 196, 140), pts)
        # Brilho de verniz no meio
        for k, z0 in enumerate((1.0, 3.2)):
            pts = [proj(-0.2, z0)[:2], proj(0.2, z0)[:2], proj(0.08, z0 + 1.6)[:2], proj(-0.08, z0 + 1.6)[:2]]
            pygame.draw.polygon(sup, (226, 186, 130), pts)
        # Linha de falta, pontos e setas
        pygame.draw.line(sup, (40, 30, 30), proj(-LANE, 0.06)[:2], proj(LANE, 0.06)[:2], 4)
        for k in range(-3, 4):
            x = k * 0.14
            px, py, s = proj(x, 1.9)
            pygame.draw.circle(sup, (80, 50, 40), (int(px), int(py)), max(2, int(4 * s)))
            zc = 4.3 + abs(k) * 0.25
            p1 = proj(x, zc + 0.3)[:2]
            p2 = proj(x - 0.035, zc)[:2]
            p3 = proj(x + 0.035, zc)[:2]
            pygame.draw.polygon(sup, (90, 50, 40), (p1, p2, p3))
        # Pontos onde ficam os pinos
        for x, z in PINOS_POS:
            px, py, s = proj(x, z)
            pygame.draw.ellipse(sup, (205, 170, 120), (px - 12 * s, py - 4 * s, 24 * s, 8 * s))
        # Poço e cortina
        yp = proj(0, Z_PIT)[1]
        largura = proj(LANE + 0.3, Z_PIT)[0] - proj(-LANE - 0.3, Z_PIT)[0]
        poco = pygame.Rect(0, yp - 64, int(largura), 64)
        poco.centerx = CX
        pygame.draw.rect(sup, (10, 8, 16), poco)
        pygame.draw.rect(sup, (30, 20, 50), (poco.x, poco.y - 6, poco.w, 12))
        # Paredes laterais do fundo
        for lado in (-1, 1):
            pts = [proj(lado * PAREDE, 6.3)[:2], proj(lado * PAREDE, Z_PIT)[:2],
                   (proj(lado * PAREDE, Z_PIT)[0], yp - 64), (proj(lado * PAREDE, 6.3)[0], proj(0, 6.3)[1] - 50)]
            pygame.draw.polygon(sup, (50, 34, 80), pts)
            pygame.draw.polygon(sup, (120, 80, 200), pts, 2)
        # Letreiro
        placa = pygame.Rect(0, poco.y - 58, poco.w + 60, 44)
        placa.centerx = CX
        ui.painel(sup, placa, (60, 20, 90), (255, 90, 200), 10, 3, sombra=False)
        ui.desenhar_texto(sup, "OVAL LANES", placa.center, 16, (255, 220, 250), "center")
        # Neon nas laterais
        for lado in (-1, 1):
            x = CX + lado * 400
            pygame.draw.line(sup, (255, 90, 200), (x, 130), (x + lado * 60, ALTURA), 4)
            pygame.draw.line(sup, (120, 220, 255), (x + lado * 30, 130), (x + lado * 100, ALTURA), 3)
        return sup

    @classmethod
    def desenhar_icone(cls, sup, jogador):
        w, h = sup.get_size()
        pino = pino_sprite(h * 0.3, 0)
        for k, (dx, dy) in enumerate(((0, 0), (-0.09, -0.06), (0.09, -0.06))):
            r = pino.get_rect(midbottom=(int(w * (0.68 + dx)), int(h * (0.62 + dy))))
            sup.blit(pino, r)
        jogador.desenhar(sup, (w * 0.3, h * 0.62), h * 0.4, angulo=-25)

    # --------------------------------------------------------
    # PARTIDA
    # --------------------------------------------------------

    def __init__(self, app, menu):
        self.seguradas = set()
        self._bola_base = [None, None]
        self._bola_cache = {}
        self._placar_cache = None
        super().__init__(app, menu)

    def _montar_menu_inicio(self):
        super()._montar_menu_inicio()
        ajustar_botoes_hibrido(self)

    def _desenhar_inicio(self, tela):
        desenhar_inicio_hibrido(self, tela)

    def reiniciar(self):
        self.jogadas = [[[] for _ in range(10)] for _ in (0, 1)]
        self.frame = 0
        self.vez = 0
        self.banner = None
        self._som_t = 0.0
        self._bola_base = [self.jogador.avatar(100, self.aparencia(i)).copy() for i in (0, 1)]
        self._bola_cache = {}
        self._placar_cache = None
        self._armar_pinos()
        self._nova_bola()

    def _armar_pinos(self):
        self.pinos = [Pino(x, z) for x, z in PINOS_POS]

    def _eh_bot(self):
        return self.solo and self.vez == 1

    def _nova_bola(self):
        self.fase = "mira"
        self.tempo_fase = 0.0
        self.t_osc = 0.0
        self.x0 = 0.0
        self.ang = 0.0
        self.forca = 0.0
        self.efeito = 0.0
        self.bola = None
        self.em_pe = sum(1 for p in self.pinos if p.ativo)
        self.plano = self._plano_bot() if self._eh_bot() else None
        self._ant = None

    # --------------------------------------------------------
    # BOT
    # --------------------------------------------------------

    def _plano_bot(self):
        d = self.dificuldade
        ativos = [p for p in self.pinos if p.ativo]
        if len(ativos) == 10:
            tx = random.choice((0.06, -0.06))
            zt = 7.0
        else:
            frente = min(ativos, key=lambda p: p.z)
            media = sum(p.x for p in ativos) / len(ativos)
            tx = frente.x * 0.55 + media * 0.45
            zt = frente.z
        x0 = max(-0.3, min(0.3, tx * 0.4))
        ang = math.degrees(math.atan2(tx - x0, zt - Z_BOLA))
        ang += random.gauss(0, [1.3, 0.55, 0.17][d])
        forca = random.gauss([0.5, 0.68, 0.8][d], [0.18, 0.1, 0.04][d])
        efeito = random.gauss(0, [0.45, 0.2, 0.06][d])
        return {"x0": x0,
                "ang": max(-AMP_MIRA * 0.97, min(AMP_MIRA * 0.97, ang)),
                "forca": max(0.04, min(0.97, forca)),
                "efeito": max(-0.95, min(0.95, efeito)),
                "espera": random.uniform(0.35, 0.7) + (0.3 if d == 0 else 0.0)}

    def _atualizar_bot(self, dt):
        p = self.plano
        if self.tempo_fase < p["espera"]:
            return
        if self.fase == "mira":
            dx = p["x0"] - self.x0
            if abs(dx) > 0.01:
                self.x0 += max(-0.6 * dt, min(0.6 * dt, dx))
                return
            atual, alvo = self.ang, p["ang"]
        elif self.fase == "forca":
            atual, alvo = self.forca, p["forca"]
        else:
            atual, alvo = self.efeito, p["efeito"]
        ant = self._ant
        self._ant = atual - alvo
        if ant is not None and (ant == 0 or (ant < 0) != (self._ant < 0)):
            self._travar()

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
        super().evento(e)

    def evento_jogo(self, e):
        apertou = ((e.type == pygame.KEYDOWN and (e.key in TECLAS_ACAO[0] or e.key in TECLAS_ACAO[1]))
                   or (e.type == pygame.MOUSEBUTTONDOWN and e.button == 1))
        if apertou and not self._eh_bot() and self.fase in ("mira", "forca", "efeito"):
            self._mexeu[self.vez if not self.solo else 0] = True
            self._travar()

    def _travar(self):
        self._ant = None
        self.tempo_fase = 0.0
        self.t_osc = 0.0
        if self.fase == "mira":
            self.fase = "forca"
            self.som("clique")
        elif self.fase == "forca":
            self.fase = "efeito"
            self.som("clique")
        elif self.fase == "efeito":
            self._lancar()

    def _lancar(self):
        v = 4.5 + 4.5 * self.forca
        a = math.radians(self.ang)
        self.bola = {"x": self.x0, "z": Z_BOLA, "vx": v * math.sin(a), "vz": v * math.cos(a),
                     "spin": self.efeito, "canaleta": False, "poco": False, "giro": 0.0,
                     "t_poco": 0.0}
        self.fase = "rolando"
        self.tempo_fase = 0.0
        self.som("pulo")

    # --------------------------------------------------------
    # LOOP
    # --------------------------------------------------------

    def atualizar_jogo(self, dt):
        self.tempo_fase += dt
        self.t_osc += dt
        self._som_t = max(0.0, self._som_t - dt)
        if self.banner:
            self.banner[2] -= dt
            if self.banner[2] <= 0:
                self.banner = None

        if self.fase == "mira":
            self.ang = AMP_MIRA * math.sin(self.t_osc * 2.3)
            if not self._eh_bot():
                k = self.seguradas
                esq = any(TECLAS_MOVER[i]["esq"] in k for i in (0, 1))
                dir_ = any(TECLAS_MOVER[i]["dir"] in k for i in (0, 1))
                self.x0 = max(-0.38, min(0.38, self.x0 + (dir_ - esq) * 0.6 * dt))
        elif self.fase == "forca":
            self.forca = _tri(self.t_osc * 1.1)
        elif self.fase == "efeito":
            self.efeito = 2 * _tri(self.t_osc * 0.8 + 0.5) - 1
        elif self.fase == "rolando":
            passos = max(1, int(round(dt / SUB)))
            h = dt / passos
            for _ in range(passos):
                self._fisica(h)
            b = self.bola
            if b["poco"]:
                b["t_poco"] += dt
                parado = not any(p.mexendo for p in self.pinos if p.ativo and not p.fora)
                if b["t_poco"] > 2.5 or (b["t_poco"] > 0.7 and parado):
                    self._contar()
            elif self.tempo_fase > 8:
                self._contar()
        elif self.fase == "resultado":
            if self.tempo_fase > 1.7:
                self._proxima()

        if self.fase in ("mira", "forca", "efeito") and self._eh_bot() and self.plano:
            self._atualizar_bot(dt)

        for p in self.pinos:
            if p.caido and p.queda < 1:
                p.queda = min(1.0, p.queda + dt * 5)

    def _fisica(self, h):
        b = self.bola
        if not b["poco"]:
            if b["z"] > 2.5 and not b["canaleta"]:
                b["vx"] += b["spin"] * HOOK * h
            b["x"] += b["vx"] * h
            b["z"] += b["vz"] * h
            b["giro"] += math.hypot(b["vx"], b["vz"]) * h / R_BOLA
            if not b["canaleta"] and abs(b["x"]) > LANE - 0.02:
                b["canaleta"] = True
                b["x"] = math.copysign(CANAL, b["x"])
                b["vx"] = 0.0
                self.som("erro", 0.5)
            if b["z"] > Z_PIT:
                b["poco"] = True
                self.som("bater", 0.4)
            elif not b["canaleta"]:
                for p in self.pinos:
                    if p.ativo and not p.fora:
                        self._colidir(b, p)

        pinos = [p for p in self.pinos if p.ativo and not p.fora]
        for p in pinos:
            if not p.mexendo:
                p.vx = p.vz = 0.0
                continue
            p.x += p.vx * h
            p.z += p.vz * h
            f = math.exp(-1.6 * h)
            p.vx *= f
            p.vz *= f
            if p.z > 6.3 and abs(p.x) > PAREDE:
                p.x = math.copysign(PAREDE, p.x)
                p.vx = -p.vx * 0.6
            if p.z > Z_PIT + 0.08 or p.z < 5.0 or (p.z <= 6.3 and abs(p.x) > LANE + 0.03):
                p.fora = True
                self._derrubar(p, 0.5)
        for i in range(len(pinos)):
            a = pinos[i]
            for j in range(i + 1, len(pinos)):
                c = pinos[j]
                if a.mexendo or c.mexendo:
                    self._colidir_pinos(a, c)

    def _derrubar(self, p, forca):
        if not p.caido:
            p.caido = True
            p.lado = 1 if p.vx > 0.05 else (-1 if p.vx < -0.05 else random.choice((-1, 1)))
            if self._som_t <= 0:
                self.som("bater", min(0.8, 0.3 + forca * 0.08))
                self._som_t = 0.05

    def _colidir(self, b, p):
        dx = p.x - b["x"]
        dz = p.z - b["z"]
        d2 = dx * dx + dz * dz
        r = R_BOLA + R_PINO
        if d2 >= r * r or d2 == 0:
            return
        d = math.sqrt(d2)
        nx, nz = dx / d, dz / d
        vrel = (b["vx"] - p.vx) * nx + (b["vz"] - p.vz) * nz
        if vrel > 0:
            j = 1.6 * vrel / (1 / M_BOLA + 1 / M_PINO)
            b["vx"] -= j / M_BOLA * nx
            b["vz"] -= j / M_BOLA * nz
            # Um pouco de caos no pino (bolas iguais não dão sempre o mesmo resultado)
            giro = random.uniform(-0.12, 0.12)
            cx, sx = math.cos(giro), math.sin(giro)
            ix, iz = nx * cx - nz * sx, nx * sx + nz * cx
            p.vx += j / M_PINO * ix
            p.vz += j / M_PINO * iz
            self._derrubar(p, vrel)
        sep = r - d
        b["x"] -= nx * sep * 0.2
        p.x += nx * sep * 0.8
        p.z += nz * sep * 0.8

    def _colidir_pinos(self, a, c):
        dx = c.x - a.x
        dz = c.z - a.z
        d2 = dx * dx + dz * dz
        r = 2 * R_PINO
        if d2 >= r * r or d2 == 0:
            return
        d = math.sqrt(d2)
        nx, nz = dx / d, dz / d
        vrel = (a.vx - c.vx) * nx + (a.vz - c.vz) * nz
        if vrel > 0:
            j = 1.7 * vrel / 2
            a.vx -= j * nx
            a.vz -= j * nz
            c.vx += j * nx
            c.vz += j * nz
            if vrel > 0.15:
                self._derrubar(a, vrel)
                self._derrubar(c, vrel)
        sep = (r - d) / 2
        a.x -= nx * sep
        a.z -= nz * sep
        c.x += nx * sep
        c.z += nz * sep

    # --------------------------------------------------------
    # PLACAR
    # --------------------------------------------------------

    def _contar(self):
        n = sum(1 for p in self.pinos if p.ativo and p.caido)
        f = self.jogadas[self.vez][self.frame]
        fresco = self.em_pe == 10
        f.append(n)
        self._placar_cache = None
        cor = CORES_JOGADOR[self.vez]
        if fresco and n == 10:
            self.banner = ["STRIKE!", AMARELO, 1.7]
            self.som("acerto")
            self.tremer(0.25)
            px, py, _ = proj(0, 7.4)
            self.particulas.explodir((px, py - 40), [AMARELO, BRANCO, (255, 90, 200), (120, 220, 255)],
                                     40, 420, 1.1, (3, 7), 300)
        elif n == self.em_pe and n > 0:
            self.banner = ["SPARE!", (120, 220, 255), 1.7]
            self.som("ponto")
            px, py, _ = proj(0, 7.4)
            self.particulas.explodir((px, py - 40), [(120, 220, 255), BRANCO], 24, 300, 0.9)
        elif self.bola and self.bola["canaleta"] and n == 0:
            self.banner = ["CANALETA!", (255, 140, 120), 1.5]
        elif n == 0:
            self.banner = ["ZERO!", (255, 140, 120), 1.5]
        else:
            self.banner = [f"{n} PINO{'S' if n > 1 else ''}", cor, 1.4]
        self.fase = "resultado"
        self.tempo_fase = 0.0

    def _proxima(self):
        f = self.jogadas[self.vez][self.frame]
        if self.frame < 9:
            acabou = (len(f) == 1 and f[0] == 10) or len(f) == 2
            rearma = acabou
        else:
            if len(f) == 1:
                acabou, rearma = False, f[0] == 10
            elif len(f) == 2:
                if f[0] == 10:
                    acabou, rearma = False, f[1] == 10
                elif f[0] + f[1] == 10:
                    acabou, rearma = False, True
                else:
                    acabou, rearma = True, True
            else:
                acabou, rearma = True, True

        if acabou:
            if self.vez == 0:
                self.vez = 1
            else:
                self.vez = 0
                self.frame += 1
            self._placar_cache = None
            if self.frame >= 10:
                self._fim()
                return
            self._armar_pinos()
        elif rearma:
            self._armar_pinos()
        else:
            for p in self.pinos:
                if p.caido:
                    p.ativo = False
                else:
                    p.x, p.z = PINOS_POS[self.pinos.index(p)]
        self._nova_bola()

    def totais(self):
        res = []
        for i in (0, 1):
            t = pontuacao(self.jogadas[i])
            res.append(t[-1] if t else 0)
        return res

    def _fim(self):
        t = self.totais()
        self.pontos = t[0]
        vencedor = None if t[0] == t[1] else (0 if t[0] > t[1] else 1)
        strikes = [sum(1 for f in self.jogadas[i] for k, b in enumerate(f)
                       if b == 10 and (k == 0 or f[k - 1] == 10 or (k == 2 and sum(f[:2]) == 10)))
                   for i in (0, 1)]
        linhas = [f"{self.nome(0)[:10]} {t[0]}  ×  {t[1]} {self.nome(1)[:10]}",
                  f"STRIKES: {strikes[0]} × {strikes[1]}"]
        self.fase = "fim"
        self.terminar_multi(vencedor, linhas)

    # --------------------------------------------------------
    # DESENHO
    # --------------------------------------------------------

    def _ovo(self, i, h, ang):
        hb = max(4, int(h / 4))
        ab = int(round(ang / 20.0)) % 18
        chave = (i, hb, ab)
        sup = self._bola_cache.get(chave)
        if sup is None:
            if len(self._bola_cache) > 400:
                self._bola_cache.clear()
            sup = pygame.transform.rotozoom(self._bola_base[i], ab * 20, hb * 4 / 100)
            self._bola_cache[chave] = sup
        return sup

    def desenhar_jogo(self, tela):
        tela.blit(self.fundo(self.jogador), (0, 0))
        objs = []
        for p in self.pinos:
            if p.ativo and not p.fora:
                objs.append((p.z, 0, p))
        b = self.bola
        if b is None:
            objs.append((Z_BOLA, 1, None))
        elif not b["poco"]:
            objs.append((b["z"], 1, b))
        objs.sort(key=lambda o: -o[0])

        if self.fase in ("mira", "forca", "efeito"):
            self._desenhar_trajeto(tela)

        for z, tipo, o in objs:
            if tipo == 0:
                px, py, s = proj(o.x, o.z)
                h = ALT_PINO * PX * s
                ang = -o.lado * 90 * o.queda
                spr = pino_sprite(h, ang)
                if o.queda > 0:
                    r = spr.get_rect(center=(px, py - h * 0.5 * (1 - o.queda) - 4 * s))
                else:
                    pygame.draw.ellipse(tela, (150, 110, 70), (px - 14 * s, py - 4 * s, 28 * s, 8 * s))
                    r = spr.get_rect(midbottom=(px, py + 2))
                tela.blit(spr, r)
            else:
                if o is None:
                    x, zz, giro = self.x0, Z_BOLA, math.sin(self.tempo * 4) * 6
                else:
                    x, zz, giro = o["x"], o["z"], -math.degrees(o["giro"]) * 0.35
                px, py, s = proj(x, zz)
                h = 2.2 * R_BOLA * PX * s
                pygame.draw.ellipse(tela, (120, 85, 50), (px - h * 0.4, py - h * 0.1, h * 0.8, h * 0.2))
                spr = self._ovo(self.vez, h, giro)
                tela.blit(spr, spr.get_rect(center=(px, py - h * 0.5)))

        self.particulas.desenhar(tela)
        self.textos.desenhar(tela)
        if self.banner:
            texto, cor, t = self.banner
            tam = 44 if t > 1.5 else 40
            ui.desenhar_texto(tela, texto, (CX, 330), tam, cor, "center")

    def _desenhar_trajeto(self, tela):
        """Seta da mira + prévia curta do caminho (com a curva do efeito)."""
        a = math.radians(self.ang)
        v = 4.5 + 4.5 * (self.forca if self.fase != "mira" else 0.5)
        vx, vz = v * math.sin(a), v * math.cos(a)
        x, z = self.x0, Z_BOLA
        spin = self.efeito if self.fase == "efeito" else 0.0
        pontos = []
        dt = 0.04
        while z < 4.2:
            if z > 2.5:
                vx += spin * HOOK * dt
            x += vx * dt
            z += vz * dt
            if abs(x) > LANE:
                break
            pontos.append(proj(x, z))
        cor = CORES_JOGADOR[self.vez]
        for k, (px, py, s) in enumerate(pontos):
            if k % 2 == 0:
                pygame.draw.circle(tela, cor, (int(px), int(py)), max(2, int(6 * s)))
        if len(pontos) >= 2:
            (x1, y1, _), (x2, y2, _) = pontos[-2], pontos[-1]
            ang = math.atan2(y2 - y1, x2 - x1)
            for sinal in (-1, 1):
                pygame.draw.line(tela, AMARELO, (x2, y2),
                                 (x2 - 16 * math.cos(ang + sinal * 0.5), y2 - 16 * math.sin(ang + sinal * 0.5)), 4)

    def desenhar_hud(self, tela):
        self._desenhar_placar(tela)
        if self.fase == "fim":
            return
        # Painel da vez (esquerda)
        caixa = pygame.Rect(12, 540, 236, 168)
        ui.painel(tela, caixa, (20, 24, 40), CORES_JOGADOR[self.vez], 12, 3, sombra=False)
        ui.desenhar_texto(tela, "VEZ DE", (caixa.centerx, caixa.y + 12), 10, (180, 200, 255), "midtop")
        ui.desenhar_texto(tela, self.nome(self.vez)[:12], (caixa.centerx, caixa.y + 30), 14,
                          CORES_JOGADOR[self.vez], "midtop")
        bola = len(self.jogadas[self.vez][min(self.frame, 9)]) + 1
        ui.desenhar_texto(tela, f"FRAME {self.frame + 1}  BOLA {bola}", (caixa.centerx, caixa.y + 56),
                          10, BRANCO, "midtop")
        if self._eh_bot():
            dica = ["PENSANDO..."]
        else:
            dica = {"mira": ["A/D: POSIÇÃO", "ESPAÇO: MIRA"],
                    "forca": ["ESPAÇO: FORÇA"],
                    "efeito": ["ESPAÇO: EFEITO"]}.get(self.fase, [])
        for k, linha in enumerate(dica):
            ui.desenhar_texto(tela, linha, (caixa.centerx, caixa.y + 92 + k * 22), 10, AMARELO, "midtop")
        ui.desenhar_texto(tela, f"PINOS EM PÉ: {sum(1 for p in self.pinos if p.ativo and not p.caido)}",
                          (caixa.centerx, caixa.bottom - 22), 8, (200, 200, 220), "midtop")

        # Medidores (direita)
        caixa = pygame.Rect(LARGURA - 248, 540, 236, 168)
        ui.painel(tela, caixa, (20, 24, 40), BRANCO, 12, 3, sombra=False)
        barra = pygame.Rect(caixa.x + 24, caixa.y + 34, 36, 118)
        ui.desenhar_texto(tela, "FORÇA", (barra.centerx, caixa.y + 12), 8, BRANCO, "midtop")
        pygame.draw.rect(tela, (50, 50, 70), barra, border_radius=6)
        f = self.forca if self.fase != "mira" else 0.0
        cheio = pygame.Rect(barra.x, barra.bottom - int(barra.h * f), barra.w, int(barra.h * f))
        cor = ui.misturar((90, 200, 90), (230, 70, 70), f)
        pygame.draw.rect(tela, cor, cheio, border_radius=6)
        pygame.draw.rect(tela, BRANCO, barra, 2, border_radius=6)

        trilho = pygame.Rect(caixa.x + 84, caixa.y + 80, 132, 14)
        ui.desenhar_texto(tela, "EFEITO", (trilho.centerx, caixa.y + 12), 8, BRANCO, "midtop")
        ui.desenhar_texto(tela, "<- CURVA ->", (trilho.centerx, caixa.y + 44), 8, (180, 200, 255), "midtop")
        pygame.draw.rect(tela, (50, 50, 70), trilho, border_radius=6)
        pygame.draw.line(tela, BRANCO, (trilho.centerx, trilho.y - 4), (trilho.centerx, trilho.bottom + 4), 2)
        e = self.efeito if self.fase in ("efeito", "rolando", "resultado") else 0.0
        pygame.draw.circle(tela, AMARELO, (int(trilho.centerx + e * trilho.w / 2), trilho.centery), 10)
        ui.desenhar_texto(tela, f"MIRA {self.ang:+.1f}", (trilho.centerx, caixa.y + 118),
                          8, (200, 200, 220), "midtop")

    def _desenhar_placar(self, tela):
        chave = (str(self.jogadas), self.vez, self.frame)
        if self._placar_cache is None or self._placar_cache[0] != chave:
            self._placar_cache = (chave, self._montar_placar())
        tela.blit(self._placar_cache[1], (12, 6))

    def _montar_placar(self):
        W_NOME, W_F, W_10, W_TOT, H = 118, 60, 84, 74, 34
        largura = W_NOME + 9 * W_F + W_10 + W_TOT
        sup = pygame.Surface((largura + 4, 14 + 2 * H + 4), pygame.SRCALPHA)
        for k in range(10):
            x = W_NOME + k * W_F + (W_10 if k == 10 else 0)
            w = W_F if k < 9 else W_10
            ui.desenhar_texto(sup, str(k + 1), (x + w // 2, 0), 8, (200, 200, 230), "midtop")
        ui.desenhar_texto(sup, "TOTAL", (W_NOME + 9 * W_F + W_10 + W_TOT // 2, 0), 8, (200, 200, 230), "midtop")
        for i in (0, 1):
            y = 14 + i * H
            totais = pontuacao(self.jogadas[i])
            linha = pygame.Rect(0, y, largura, H)
            pygame.draw.rect(sup, (20, 24, 40), linha)
            nome = pygame.Rect(0, y, W_NOME, H)
            pygame.draw.rect(sup, (35, 30, 60), nome)
            ui.desenhar_texto(sup, self.nome(i)[:8], (6, y + H // 2), 10, CORES_JOGADOR[i], "midleft")
            for k in range(10):
                x = W_NOME + k * W_F
                w = W_F if k < 9 else W_10
                caixa = pygame.Rect(x, y, w, H)
                atual = (i == self.vez and k == self.frame)
                pygame.draw.rect(sup, (60, 60, 90) if atual else (32, 36, 58), caixa)
                pygame.draw.rect(sup, (90, 90, 130), caixa, 1)
                ms = marcas(self.jogadas[i], k)
                n = len(ms)
                cw = 20
                for m_i, m in enumerate(ms):
                    cx = caixa.right - (n - m_i) * cw
                    pygame.draw.rect(sup, (90, 90, 130), (cx, y, cw, 15), 1)
                    if m:
                        cor = AMARELO if m in ("X", "/") else BRANCO
                        ui.desenhar_texto(sup, m, (cx + cw // 2 + 1, y + 4), 8, cor, "midtop", sombra=False)
                if k < len(totais):
                    ui.desenhar_texto(sup, str(totais[k]), (caixa.centerx, y + 20), 10, BRANCO, "midtop",
                                      sombra=False)
            tot = pygame.Rect(W_NOME + 9 * W_F + W_10, y, W_TOT, H)
            pygame.draw.rect(sup, (50, 40, 80), tot)
            pygame.draw.rect(sup, (90, 90, 130), tot, 1)
            ui.desenhar_texto(sup, str(totais[-1] if totais else 0), tot.center, 14, AMARELO, "center")
        pygame.draw.rect(sup, BRANCO, (0, 14, largura, 2 * H), 2)
        return sup
