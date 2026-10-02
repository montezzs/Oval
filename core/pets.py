import datetime
import math
import random

import pygame

from settings import *
from core import ui
from core.idioma import t

# ============================================================
# PETS
# ============================================================
# 10 bichinhos que seguem o ovo na casa (CASA / SOL / BRINCAR),
# pulam nas telas de fim dos mini jogos e aparecem no provador.
#
# Como são desenhados:
#   Cada espécie desenha uma POSE (tupla de parâmetros já
#   arredondados) com um _Pincel, em coordenadas de DESIGN:
#   px de tela na escala 1, origem (0, 0) = ponto dos pés,
#   y negativo para cima e o bicho olhando para a DIREITA.
#   A pose é desenhada 3x maior e reduzida com smoothscale
#   (bordas suaves) e vai para um cache. Por frame o custo é
#   praticamente um blit.

# ============================================================
# CATÁLOGO
# ============================================================

CATALOGO = {
    "pintinho": dict(nome="PIU", especie="PINTINHO", preco=150, raridade="COMUM",
                     voa=False, talento="Acha 1 semente de limão por dia"),
    "gatinho": dict(nome="MIMI", especie="GATINHO", preco=300, raridade="INCOMUM",
                    voa=False, talento="Ronrona no carinho: diversão em dobro"),
    "cachorrinho": dict(nome="PIPOCA", especie="CACHORRINHO", preco=300,
                        raridade="INCOMUM", voa=False,
                        talento="Busca a bola no SOL: diversão +5"),
    "pinguim": dict(nome="GELINHO", especie="PINGUIM", preco=300, raridade="INCOMUM",
                    voa=False, talento="Piscina e chuva limpam 50% mais"),
    "abelha": dict(nome="ZUZU", especie="ABELHA", preco=500, raridade="RARO",
                   voa=True, talento="Plantas crescem 20% mais rápido"),
    "slime": dict(nome="GELECA", especie="SLIME", preco=600, raridade="RARO",
                  voa=False, talento="Higiene cai 30% mais devagar"),
    "fantasma": dict(nome="BUH", especie="FANTASMINHA", preco=650, raridade="RARO",
                     voa=True, talento="Brilha à noite; dormir rende 20% mais"),
    "robo": dict(nome="BIP", especie="ROBOZINHO", preco=1000, raridade="EPICO",
                 voa=False, talento="Avisa e colhe as plantas prontas"),
    "dragao": dict(nome="FAÍSCA", especie="DRAGÃOZINHO", preco=1500, raridade="EPICO",
                   voa=True, talento="1 marshmallow assado por dia"),
    "unicornio": dict(nome="ARCO-ÍRIS", especie="UNICÓRNIO", preco=2500,
                      raridade="LENDARIO", voa=False,
                      talento="+5% OVOEDAS em todos os jogos"),
}

# Tamanho dos pets na casa (1.0 = medidas do design; o ovo tem 150 px)
ESCALA_MUNDO = 1.4

ALTURA_OVO = 150
CASINHA = (80, 560)              # porta da casinha do pet (SOL)

ARCO_IRIS = [(255, 90, 90), (255, 180, 60), (255, 230, 70), (100, 210, 110),
             (90, 160, 255)]
OLHO = (40, 28, 45)
BRANCO_OLHO = (255, 255, 255)
ROSA = (255, 135, 165)


def bonus_moedas(pet_id):
    """Multiplicador de OVOEDAS: só o unicórnio (lendário) dá +5%."""
    return 1.05 if pet_id == "unicornio" else 1.0


# ============================================================
# PINCEL (desenho vetorial simples com transformações)
# ============================================================

def _bezier(p0, p1, p2, n=12):
    pts = []
    for i in range(n + 1):
        t = i / n
        a = (1 - t) * (1 - t)
        b = 2 * (1 - t) * t
        c = t * t
        pts.append((a * p0[0] + b * p1[0] + c * p2[0], a * p0[1] + b * p1[1] + c * p2[1]))
    return pts


def _misturar(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


class _Pincel:
    """
    Desenha formas em coordenadas de design numa Surface grande.
    Formas (tuplas):
      ("c", cx, cy, r)                    círculo
      ("e", cx, cy, rx, ry[, ang])        elipse (ang em graus, anti-horário)
      ("rr", x, y, w, h, raio)            retângulo arredondado
      ("p", [pontos])                     polígono
      ("l", [pontos], largura)            linha grossa com pontas redondas
      ("b", p0, p1, p2, largura)          curva (bezier) grossa
      ("a", cx, cy, rx, ry, a0, a1, larg) arco grosso (graus, 0 = direita, 90 = cima)
    `forma(cor, borda, *formas)` pinta a BORDA de todas (a união fica
    com um contorno só) e depois o recheio.
    """

    def __init__(self, sup, ox, oy, s, espessura):
        self.sup = sup
        self.ox = ox
        self.oy = oy
        self.s = s
        self.w = espessura
        self.m = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0)
        self.pilha = []

    # ---------------- transformações ----------------

    def salvar(self):
        self.pilha.append(self.m)

    def restaurar(self):
        self.m = self.pilha.pop()

    def _mult(self, n):
        a, b, c, d, e, f = self.m
        A, B, C, D, E, F = n
        self.m = (a * A + b * D, a * B + b * E, a * C + b * F + c,
                  d * A + e * D, d * B + e * E, d * C + e * F + f)

    def mover(self, dx, dy):
        if dx or dy:
            self._mult((1, 0, dx, 0, 1, dy))

    def girar(self, graus, cx=0.0, cy=0.0):
        """Gira (anti-horário na tela) em volta de (cx, cy)."""
        if not graus:
            return
        r = math.radians(graus)
        co, si = math.cos(r), math.sin(r)
        self.mover(cx, cy)
        self._mult((co, si, 0, -si, co, 0))
        self.mover(-cx, -cy)

    def escalar(self, sx, sy, cx=0.0, cy=0.0):
        if sx == 1 and sy == 1:
            return
        self.mover(cx, cy)
        self._mult((sx, 0, 0, 0, sy, 0))
        self.mover(-cx, -cy)

    def pt(self, x, y):
        a, b, c, d, e, f = self.m
        return ((a * x + b * y + c) * self.s + self.ox, (d * x + e * y + f) * self.s + self.oy)

    def fator(self):
        a, b, _, d, e, _ = self.m
        return math.sqrt(abs(a * e - b * d)) * self.s

    # ---------------- pontos das formas ----------------

    def _pts_elipse(self, cx, cy, rx, ry, ang=0.0, a0=0.0, a1=360.0, fechada=True):
        n = int(max(12, min(110, (rx + ry) * self.fator() * 0.4)))
        if not fechada:
            n = max(4, int(n * abs(a1 - a0) / 360) + 3)
        ra = math.radians(ang)
        ca, sa = math.cos(ra), math.sin(ra)
        pts = []
        total = n if fechada else n + 1
        for i in range(total):
            a = math.radians(a0 + (a1 - a0) * i / n)
            lx = rx * math.cos(a)
            ly = -ry * math.sin(a)
            pts.append(self.pt(cx + lx * ca + ly * sa, cy - lx * sa + ly * ca))
        return pts

    def _pts_rr(self, x, y, w, h, r):
        r = max(0.0, min(r, w / 2, h / 2))
        pts = []
        cantos = ((x + w - r, y + r, 0), (x + r, y + r, 90),
                  (x + r, y + h - r, 180), (x + w - r, y + h - r, 270))
        for cx, cy, a0 in cantos:
            if r <= 0:
                pts.append(self.pt(cx, cy))
                continue
            for i in range(7):
                a = math.radians(a0 + 90 * i / 6)
                pts.append(self.pt(cx + r * math.cos(a), cy - r * math.sin(a)))
        return pts

    # ---------------- pintura ----------------

    def _traco(self, pts, cor, larg, fechada=False):
        if len(pts) < 2:
            if pts:
                pygame.draw.circle(self.sup, cor, pts[0], max(1.0, larg / 2))
            return
        if larg < 1.6:
            pygame.draw.lines(self.sup, cor, fechada, pts, 1)
            return
        r = larg / 2
        seq = pts + [pts[0]] if fechada else pts
        for (x1, y1), (x2, y2) in zip(seq, seq[1:]):
            dx, dy = x2 - x1, y2 - y1
            d = math.hypot(dx, dy)
            if d < 1e-6:
                continue
            nx, ny = -dy / d * r, dx / d * r
            pygame.draw.polygon(self.sup, cor, [(x1 + nx, y1 + ny), (x2 + nx, y2 + ny),
                                                (x2 - nx, y2 - ny), (x1 - nx, y1 - ny)])
        for p in pts:
            pygame.draw.circle(self.sup, cor, p, r)

    def _pintar(self, f, cor, exp):
        t = f[0]
        fat = self.fator()
        if t == "c":
            pygame.draw.polygon(self.sup, cor, self._pts_elipse(f[1], f[2], f[3] + exp,
                                                                f[3] + exp))
        elif t == "e":
            ang = f[5] if len(f) > 5 else 0.0
            pygame.draw.polygon(self.sup, cor, self._pts_elipse(f[1], f[2], f[3] + exp,
                                                                f[4] + exp, ang))
        elif t == "rr":
            x, y, w, h, r = f[1:6]
            pygame.draw.polygon(self.sup, cor, self._pts_rr(x - exp, y - exp, w + 2 * exp,
                                                            h + 2 * exp, r + exp))
        elif t == "p":
            pts = [self.pt(*q) for q in f[1]]
            if exp:
                self._traco(pts, cor, 2 * exp * fat, True)
            pygame.draw.polygon(self.sup, cor, pts)
        elif t == "l":
            self._traco([self.pt(*q) for q in f[1]], cor, (f[2] + 2 * exp) * fat)
        elif t == "b":
            pts = [self.pt(*q) for q in _bezier(f[1], f[2], f[3], 14)]
            self._traco(pts, cor, (f[4] + 2 * exp) * fat)
        elif t == "a":
            cx, cy, rx, ry, a0, a1, larg = f[1:8]
            pts = self._pts_elipse(cx, cy, rx, ry, 0, a0, a1, fechada=False)
            self._traco(pts, cor, (larg + 2 * exp) * fat)

    def forma(self, cor, borda, *formas, w=None):
        w = self.w if w is None else w
        if borda is not None and w > 0:
            for f in formas:
                self._pintar(f, borda, w)
        for f in formas:
            self._pintar(f, cor, 0)

    def faixas(self, borda, pares, w=None):
        """Várias formas de cores diferentes com UM contorno em volta de todas
        (crina e cauda do arco-íris). `pares` = [(cor, forma), ...]."""
        w = self.w if w is None else w
        for _, f in pares:
            self._pintar(f, borda, w)
        for cor, f in pares:
            self._pintar(f, cor, 0)


# ------------------------------------------------------------
# Peças de rosto reaproveitadas por todos
# ------------------------------------------------------------

def _olho(p, x, y, r, modo, cor=OLHO):
    """Olho fofo: oval preto com 2 brilhos. Modos: aberto, piscar,
    feliz (^), dormindo (u), bravo."""
    if modo in ("aberto", "bravo"):
        p.forma(cor, None, ("e", x, y, r * 0.82, r))
        p.forma(BRANCO_OLHO, None, ("c", x - r * 0.28, y - r * 0.38, r * 0.36))
        p.forma(BRANCO_OLHO, None, ("c", x + r * 0.3, y + r * 0.38, r * 0.16))
    elif modo == "piscar":
        p.forma(cor, None, ("l", [(x - r * 0.8, y + r * 0.1), (x + r * 0.8, y + r * 0.1)],
                            r * 0.42))
    elif modo == "feliz":
        p.forma(cor, None, ("a", x, y + r * 0.45, r * 0.85, r * 0.8, 20, 160, r * 0.42))
    else:   # dormindo
        p.forma(cor, None, ("a", x, y - r * 0.2, r * 0.85, r * 0.6, 200, 340, r * 0.4))


def _bochecha(p, x, y, rx, ry, base, alpha=None):
    cor = _misturar(base, ROSA, 0.6)
    if alpha is not None:
        cor = (*cor, alpha)
    p.forma(cor, None, ("e", x, y, rx, ry))


def _q(v, passo):
    """Arredonda para múltiplos de `passo` (poucas poses diferentes no cache)."""
    return round(round(v / passo) * passo, 3)


def _envelope(ta, dur, sub=0.3):
    """0 -> 1 -> 0 com rampas de `sub` segundos (entra, segura, sai)."""
    if ta <= 0 or ta >= dur:
        return 0.0
    return max(0.0, min(1.0, ta / sub, (dur - ta) / sub))


# ============================================================
# ESPÉCIES
# ============================================================

class _Anim:
    """Estado de animação passado para a espécie montar a pose."""

    def __init__(self):
        self.acao = "parado"     # parado | andar | idle | dormir | reacao | feliz
        self.variante = None     # nome da animação ociosa
        self.t = 0.0             # tempo global (s)
        self.ta = 0.0            # tempo na ação atual (s)
        self.u = 0.0             # progresso da reação (0..1)
        self.passo = 0.0         # ciclos de passada (distância percorrida)
        self.rapido = False
        self.perto = False       # ovo pertinho (cachorro abana o rabo)
        self.olhos = "aberto"
        self.trazendo = False
        self.noite = False


class _Especie:
    id = ""
    caixa = (-40, -70, 40, 4)          # área de desenho (design)
    borda = (60, 40, 40)
    espessura = 1.25
    sombra = 34                        # largura da sombra (design)
    topo = (0, -50)                    # de onde saem Zzz e corações
    boca = (20, -25)                   # onde a bolinha fica ao trazer
    frente = 26                        # quanto o bicho avança à frente dos pés
    passo_px = 36                      # px por ciclo de passada
    voa = False
    altura_voo = 0
    altura_dormindo = 0
    idles = (("parado", 3.0),)
    reacao_dur = 1.0
    piscar_fase = 0.0

    def pose(self, e):
        return ("parado",)

    def desenhar(self, p, pose):
        pass

    def desloc(self, e):
        """Deslocamento extra (design) calculado por frame: pulinhos etc."""
        if e.acao == "feliz":
            return 0.0, -abs(math.sin(e.t * 5)) * 12
        return 0.0, 0.0


# ------------------------------------------------------------
# PINTINHO (PIU)
# ------------------------------------------------------------

class _Pintinho(_Especie):
    frente = 24
    id = "pintinho"
    caixa = (-28, -54, 30, 4)
    borda = (175, 110, 20)
    sombra = 30
    topo = (10, -46)
    boca = (22, -29)
    passo_px = 30
    idles = (("bicar", 3.2), ("asas", 1.4))
    reacao_dur = 0.9
    COR = (255, 220, 60)
    ASA = (242, 188, 38)
    LAR = (255, 150, 40)

    def pose(self, e):
        o = e.olhos
        a = e.acao
        if a == "andar":
            fr = e.passo % 1.0
            ar = 0.12 < fr < 0.88
            return (-6 if ar else 0, 0, 0, -20 if ar and fr < 0.5 else 0,
                    "ar" if ar else "chao", 1.0, 1.0, o, 0)
        if a == "dormir":
            r = _q(math.sin(e.t * 2) * 0.025, 0.0125)
            return (0, -4, 7, 0, "sentado", 1.06 + r, 0.92 - r, "dormindo", 0)
        if a == "reacao":
            return (0, 0, -2, -55, "ar" if e.u < 0.85 else "chao", 1.0, 1.0, "feliz",
                    1 if e.u < 0.45 else 0)
        if a == "feliz":
            ar = abs(math.sin(e.t * 5)) > 0.15
            return (0, 0, 0, -55 if int(e.t * 10) % 2 else -25, "ar" if ar else "chao",
                    1.0, 1.0, "feliz", int(e.t * 4) % 2)
        if a == "idle" and e.variante == "bicar":
            ta = e.ta
            k = max(0.0, 1 - abs(ta - 1.9) / 0.18, 1 - abs(ta - 2.35) / 0.18)
            k = _q(k, 0.5)
            return (int(-12 * k), int(4 * k), int(8 * k), 0, "chao", 1.0, 1.0, o, 0)
        if a == "idle" and e.variante == "asas":
            return (0, 0, 0, -45 if int(e.ta * 9) % 2 else -5, "chao", 1.0, 1.0, "feliz", 1)
        r = _q(math.sin(e.t * 2.5) * 0.02, 0.01)
        return (0, 0, 0, 0, "chao", 1 - r * 0.5, 1 + r, o, 0)

    def desloc(self, e):
        if e.acao == "andar":
            return 0.0, -8 * math.sin(math.pi * (e.passo % 1.0))
        if e.acao == "reacao":
            return 0.0, -34 * math.sin(math.pi * min(1.0, e.u / 0.85))
        if e.acao == "idle" and e.variante == "asas":
            return 0.0, -3 * abs(math.sin(e.ta * 9))
        return super().desloc(e)

    def desenhar(self, p, pose):
        tilt, cdx, cdy, asa, pes, sx, sy, olhos, bico = pose
        B = self.borda
        p.girar(tilt, 0, 0)

        # Perninhas
        if pes == "chao":
            for x in (-5, 4):
                p.forma(self.LAR, B, ("l", [(x, -6), (x, -0.8)], 2.0),
                        ("l", [(x - 2.6, -0.8), (x + 3.6, -0.8)], 2.0), w=0.8)
        elif pes == "ar":
            for x in (-4, 4):
                p.forma(self.LAR, B, ("l", [(x, -6), (x - 1.2, -2.5), (x + 1.8, -2.2)], 2.0),
                        w=0.8)

        if pes != "sentado":
            p.mover(0, -3)
        p.escalar(sx, sy, 0, 3 if pes != "sentado" else 0)

        hx, hy = 10 + cdx, -30 + cdy
        # Topete (atrás da cabeça)
        p.forma(self.ASA, B, ("l", [(hx - 1, hy - 8), (hx - 4, hy - 14)], 2.4),
                ("l", [(hx + 1, hy - 8), (hx + 2.5, hy - 15)], 2.4), w=0.9)
        # Rabinho
        p.forma(self.ASA, B, ("p", [(-12, -22), (-21, -28), (-18.5, -21),
                                    (-22, -16.5), (-12, -14)]))
        # Corpo + cabeça (uma bolinha só)
        p.forma(self.COR, B, ("c", 0, -16, 16), ("c", hx, hy, 10))
        # Barriguinha mais clarinha
        p.forma((255, 236, 140), None, ("e", 3, -10, 9, 5.5))
        # Asa
        p.salvar()
        p.girar(asa, 3, -19)
        p.forma(self.ASA, B, ("e", -3, -17.5, 7.5, 4.8, -8), w=0.9)
        p.forma(_misturar(self.ASA, B, 0.35), None,
                ("a", -4, -16.5, 4.5, 2.2, 200, 330, 0.7))
        p.restaurar()
        # Bico
        if bico:
            p.forma(self.LAR, B, ("p", [(hx + 7, hy - 3.2), (hx + 14, hy - 3.5), (hx + 7.5, hy - 0.4)]),
                    ("p", [(hx + 7, hy + 0.8), (hx + 12, hy + 2.8), (hx + 7, hy + 3)]), w=0.9)
        else:
            p.forma(self.LAR, B, ("p", [(hx + 7.5, hy - 2.6), (hx + 14.5, hy - 0.2),
                                        (hx + 7.5, hy + 2.4)]), w=0.9)
        # Rosto
        _olho(p, hx + 3.5, hy - 3.2, 2.7, olhos)
        _bochecha(p, hx + 1.5, hy + 3.2, 2.6, 1.6, self.COR)


# ------------------------------------------------------------
# GATINHO (MIMI)
# ------------------------------------------------------------

class _Gatinho(_Especie):
    frente = 30
    id = "gatinho"
    caixa = (-42, -62, 40, 4)
    borda = (125, 68, 28)
    sombra = 42
    topo = (15, -56)
    boca = (24, -27)
    passo_px = 40
    idles = (("lamber", 3.0), ("espreguicar", 2.4))
    reacao_dur = 1.4
    piscar_fase = 1.3
    COR = (240, 160, 70)
    ESC = (214, 134, 52)
    LIS = (196, 110, 36)
    CRE = (255, 236, 212)
    ORELHA = (255, 160, 170)

    def pose(self, e):
        o = e.olhos
        cauda = _q(math.sin(e.t * 2.0), 0.34)
        a = e.acao
        if a == "andar":
            return ("pe", int(e.passo * 8) % 8, o, cauda, 0)
        if a == "dormir":
            return ("dormir", int(e.t * 1.2) % 2, "dormindo", 0, 0)
        if a == "reacao":
            return ("pe", -1, "feliz", _q(math.sin(e.t * 7), 0.5), _q(math.sin(e.ta * 9) * 6, 2))
        if a == "feliz":
            return ("pe", -1, "feliz", _q(math.sin(e.t * 7), 0.5), 0)
        if a == "idle" and e.variante == "lamber":
            return ("lamber", int(e.ta * 5) % 2, "feliz", cauda, 0)
        if a == "idle" and e.variante == "espreguicar":
            return ("espreguicar", 0, "dormindo", cauda, _q(_envelope(e.ta, 2.4, 0.35), 0.5))
        return ("pe", -1, o, cauda, 0)

    def _cabeca(self, p, olhos, boca_aberta=False, lingua=False):
        B = self.borda
        hx, hy = 15, -34
        # Orelhas
        p.forma(self.COR, B, ("p", [(4.5, -40), (5.5, -53), (13.5, -45)]),
                ("p", [(17, -46), (25, -53), (26.5, -40)]))
        p.forma(self.ORELHA, None, ("p", [(6.8, -42.5), (7.3, -49.5), (11.5, -45)]),
                ("p", [(19.5, -45.5), (24, -49.5), (24.7, -42.5)]))
        # Cabeça
        p.forma(self.COR, B, ("c", hx, hy, 13))
        # Listrinhas da testa
        p.forma(self.LIS, None, ("l", [(15, -46.5), (15, -43)], 1.5),
                ("l", [(11.5, -46), (12.3, -43.2)], 1.3), ("l", [(18.5, -46), (17.7, -43.2)], 1.3))
        # Focinho clarinho
        p.forma(self.CRE, None, ("e", hx + 1.5, hy + 5.2, 7, 4.4))
        _olho(p, hx - 4, hy - 1.8, 2.8, olhos)
        _olho(p, hx + 5.5, hy - 1.8, 2.8, olhos)
        # Nariz e boca "w"
        p.forma((240, 110, 130), None, ("p", [(hx - 0.1, hy + 2.8), (hx + 3.1, hy + 2.8),
                                              (hx + 1.5, hy + 4.4)]))
        if boca_aberta:
            p.forma((120, 40, 50), None, ("e", hx + 1.5, hy + 7.2, 2.2, 2.4))
        else:
            p.forma(OLHO, None, ("a", hx + 0.2, hy + 5, 1.4, 1.2, 200, 340, 0.6),
                    ("a", hx + 2.8, hy + 5, 1.4, 1.2, 200, 340, 0.6))
        if lingua:
            p.forma((255, 120, 140), None, ("e", hx + 1.5, hy + 7, 1.6, 2))
        # Bigodes
        cor_b = (120, 70, 40)
        p.forma(cor_b, None, ("l", [(hx - 5, hy + 4), (hx - 12, hy + 3)], 0.6),
                ("l", [(hx - 5, hy + 5.5), (hx - 12, hy + 6.5)], 0.6),
                ("l", [(hx + 8, hy + 4), (hx + 15, hy + 3)], 0.6),
                ("l", [(hx + 8, hy + 5.5), (hx + 15, hy + 6.5)], 0.6))
        _bochecha(p, hx - 7.5, hy + 3, 2.4, 1.5, self.COR)
        _bochecha(p, hx + 9.5, hy + 3, 2.4, 1.5, self.COR)

    def _cauda(self, p, cauda, alta=0):
        B = self.borda
        sw = cauda * 5
        p0, p1, p2 = (-14, -20), (-29 + sw * 0.3, -22 - alta), (-25 + sw, -40 - alta)
        p.forma(self.COR, B, ("b", p0, p1, p2, 4.6))
        pts = _bezier(p0, p1, p2, 10)
        p.forma(self.LIS, None, ("l", pts[8:], 4.6), ("l", pts[5:6], 4.6))

    def desenhar(self, p, pose):
        tipo, f, olhos, cauda, x = pose
        B = self.borda

        if tipo == "dormir":
            p.escalar(1.0, 1.0 + f * 0.04, 0, 0)
            p.forma(self.COR, B, ("e", -2, -10, 19, 10))
            for sx in (-10, -4, 2):
                p.forma(self.LIS, None, ("l", [(sx - 1, -19), (sx, -15.5)], 2.0))
            p.forma(self.COR, B, ("b", (-19, -8), (-8, 3), (18, -2), 4.6))
            p.forma(self.LIS, None, ("l", _bezier((-19, -8), (-8, 3), (18, -2), 10)[8:], 4.6))
            p.salvar()
            p.mover(-2, 20)
            p.girar(-8, 15, -34)
            self._cabeca(p, "dormindo")
            p.restaurar()
            return

        tilt = x if tipo == "pe" else 0
        k = x if tipo == "espreguicar" else 0
        p.girar(tilt, 0, 0)

        self._cauda(p, cauda, 8 * k)

        # Perninhas: (x, fase, perto)
        pernas = ((-5, math.pi, False), (12, 0.0, False), (-11, 0.0, True), (6, math.pi, True))
        for px, fase, perto in pernas:
            dx = lift = 0.0
            if f >= 0:
                th = f / 8 * math.tau + fase
                dx = math.sin(th) * 3.2
                lift = max(0.0, math.cos(th)) * 2.2
            topo_y = -13
            if tipo == "espreguicar" and px > 0:
                dx += 8 * k
                topo_y += 5 * k
            if tipo == "lamber" and px == 6:
                continue
            cor = self.COR if perto else self.ESC
            p.forma(cor, B, ("l", [(px, topo_y), (px + dx, -2.7 - lift)], 5.2))

        p.salvar()
        p.girar(-14 * k, -6, -12)
        p.forma(self.COR, B, ("e", 0, -17, 18, 11))
        for sx in (-9, -3, 3):
            p.forma(self.LIS, None, ("l", [(sx - 1.3, -26.5), (sx, -22.5), (sx - 0.8, -19.5)], 2.1))
        p.forma(self.CRE, None, ("e", 6, -11, 9, 3.5))
        p.restaurar()

        p.salvar()
        if tipo == "espreguicar":
            p.mover(3 * k, 7 * k)
        if tipo == "lamber":
            p.girar(-12, 12, -24)
        self._cabeca(p, olhos, boca_aberta=(tipo == "espreguicar" and k > 0.6),
                     lingua=(tipo == "lamber" and f == 0))
        p.restaurar()

        if tipo == "lamber":
            py = -1.5 if f else 0.0
            p.forma(self.COR, B, ("l", [(6, -13), (15, -23 + py)], 5.2))
            p.forma(self.CRE, None, ("c", 15, -23 + py, 1.8))


# ------------------------------------------------------------
# CACHORRINHO (PIPOCA)
# ------------------------------------------------------------

class _Cachorrinho(_Especie):
    frente = 33
    id = "cachorrinho"
    caixa = (-40, -62, 44, 4)
    borda = (110, 68, 38)
    sombra = 44
    topo = (17, -56)
    boca = (29, -24)
    passo_px = 44
    idles = (("deitar", 4.5), ("cocar", 2.2))
    reacao_dur = 1.1
    piscar_fase = 2.1
    COR = (230, 200, 160)
    ESC = (206, 172, 132)
    MAN = (140, 90, 50)
    FOC = (248, 232, 205)

    def _abano(self, e, rapido):
        if rapido:
            return int(_q(math.sin(e.t * 8 * math.tau) * 30, 15))
        return int(_q(math.sin(e.t * 3) * 12, 6))

    def pose(self, e):
        o = e.olhos
        a = e.acao
        animado = e.perto or a in ("reacao", "feliz") or e.rapido
        cauda = self._abano(e, animado)
        if a == "andar":
            return ("pe", int(e.passo * 8) % 8, o, cauda, 1 if (e.rapido and not e.trazendo) else 0)
        if a == "dormir":
            return ("deitar", int(e.t * 1.2) % 2, "dormindo", 0, 0)
        if a == "reacao":
            return ("pe", int(e.t * 14) % 8, "feliz", cauda, 1)
        if a == "feliz":
            return ("pe", -1, "feliz", cauda, 1)
        if a == "idle" and e.variante == "deitar":
            return ("deitar", 0, o, self._abano(e, False), 0)
        if a == "idle" and e.variante == "cocar":
            return ("sentar", int(e.ta * 14) % 2, "feliz", cauda, 1)
        return ("pe", -1, o, cauda, 0)

    def desloc(self, e):
        if e.acao == "reacao":
            # dá uma voltinha em círculo
            a = e.u * math.tau
            return math.sin(a) * 22, -abs(math.sin(a * 2)) * 5
        if e.acao == "andar" and e.rapido:
            return 0.0, -abs(math.sin(e.passo * math.tau)) * 3
        return super().desloc(e)

    def _cabeca(self, p, olhos, lingua):
        B = self.borda
        hx, hy = 17, -36
        # Orelha de trás
        p.forma(self.MAN, B, ("e", hx + 9.5, hy - 1, 4.5, 8.5, 28))
        p.forma(self.COR, B, ("c", hx, hy, 14))
        # Focinho
        p.forma(self.FOC, B, ("e", hx + 8.5, hy + 6, 8, 6))
        if lingua:
            p.forma((255, 120, 140), (190, 70, 90), ("e", hx + 10, hy + 11.5, 2.4, 3.8), w=0.7)
        p.forma(OLHO, None, ("a", hx + 10.5, hy + 8.2, 2.4, 1.8, 200, 340, 0.8),
                ("l", [(hx + 13.4, hy + 5), (hx + 13.4, hy + 7.4)], 0.8))
        p.forma(OLHO, None, ("e", hx + 14.2, hy + 3.2, 3, 2.3))
        p.forma((255, 255, 255), None, ("c", hx + 13.2, hy + 2.4, 0.8))
        # Olhos
        _olho(p, hx - 2, hy - 2.5, 2.9, olhos)
        _olho(p, hx + 6.5, hy - 2.5, 2.9, olhos)
        _bochecha(p, hx - 5, hy + 4.5, 2.6, 1.6, self.COR)
        # Orelha da frente (caída)
        p.forma(self.MAN, B, ("e", hx - 10, hy + 1, 5, 9.5, -22))

    def _cauda(self, p, ang):
        B = self.borda
        p.salvar()
        p.girar(ang, -18, -22)
        p.forma(self.COR, B, ("b", (-17, -22), (-25, -25), (-25, -35), 4.4))
        p.forma(self.FOC, None, ("c", -25, -35, 2.2))
        p.restaurar()

    def desenhar(self, p, pose):
        tipo, f, olhos, cauda, lingua = pose
        B = self.borda

        if tipo == "deitar":
            p.escalar(1.0, 1.0 + f * 0.03, 0, 0)
            p.salvar()
            p.girar(-40, -18, -8)
            self._cauda(p, cauda)
            p.restaurar()
            p.forma(self.ESC, B, ("l", [(12, -4), (26, -3.2)], 6))
            p.forma(self.COR, B, ("e", -1, -10, 21, 9.5))
            p.forma(self.MAN, None, ("e", -7, -14, 7, 4))
            p.forma(self.COR, B, ("e", -12, -8, 8, 6.5))
            p.salvar()
            p.mover(4, 21)
            self._cabeca(p, olhos, False)
            p.restaurar()
            p.forma(self.COR, B, ("l", [(10, -3.2), (24, -3)], 6))
            return

        if tipo == "sentar":
            self._cauda(p, cauda + 40)
            for px, cor in ((10, self.ESC), (5, self.COR)):
                p.forma(cor, B, ("l", [(px, -18), (px + 1, -2.7)], 6))
            p.forma(self.COR, B, ("e", -3, -19, 13, 14, 25))
            p.forma(self.MAN, None, ("e", -7, -24, 5.5, 4.5, 25))
            j = 1.5 if f else -1.5
            p.forma(self.ESC, B, ("l", [(-9, -10), (2, -31 + j)], 5.6))
            p.forma(self.COR, B, ("e", -8, -8, 9.5, 7.5))
            p.salvar()
            p.mover(-6, -4)
            p.girar(8, 17, -30)
            self._cabeca(p, "feliz", True)
            p.restaurar()
            return

        self._cauda(p, cauda)
        pernas = ((-6, math.pi, False), (13, 0.0, False), (-13, 0.0, True), (7, math.pi, True))
        for px, fase, perto in pernas:
            dx = lift = 0.0
            if f >= 0:
                th = f / 8 * math.tau + fase
                dx = math.sin(th) * 3.6
                lift = max(0.0, math.cos(th)) * 2.4
            cor = self.COR if perto else self.ESC
            p.forma(cor, B, ("l", [(px, -13), (px + dx, -3 - lift)], 6))
        p.forma(self.COR, B, ("e", 0, -17, 20, 12))
        p.forma(self.MAN, None, ("e", -6, -22.5, 7.5, 4.8))
        p.forma(self.FOC, None, ("e", 7, -10.5, 9, 3.5))
        self._cabeca(p, olhos, lingua)


# ------------------------------------------------------------
# PINGUIM (GELINHO)
# ------------------------------------------------------------

class _Pinguim(_Especie):
    frente = 20
    id = "pinguim"
    caixa = (-36, -60, 36, 4)
    borda = (14, 14, 24)
    sombra = 36
    topo = (2, -56)
    boca = (9, -28)
    passo_px = 24
    idles = (("barriga", 3.4), ("olhar", 2.4))
    reacao_dur = 1.0
    piscar_fase = 0.6
    PRETO = (40, 42, 58)
    BARRIGA = (250, 250, 255)
    LAR = (255, 150, 40)

    def pose(self, e):
        o = e.olhos
        a = e.acao
        if a == "andar":
            s = math.sin(e.passo * math.tau)
            return ("pe", int(_q(s * 8, 4)), 1 if s > 0.3 else (-1 if s < -0.3 else 0),
                    10, o, 0)
        if a == "dormir":
            return ("pe", 4, 0, 0, "dormindo", 1 + int(e.t * 1.3) % 4)
        if a == "reacao":
            return ("pe", 0, 0, 60 if int(e.ta * 14) % 2 else 5, "feliz", 0)
        if a == "feliz":
            return ("pe", 0, 0, 55 if int(e.t * 10) % 2 else 10, "feliz", 0)
        if a == "idle" and e.variante == "barriga":
            ta = e.ta
            if ta < 0.25 or 1.55 <= ta < 1.8:
                return ("deitar", 1, 0, -20, o, 0)
            if ta < 1.55:
                return ("deitar", 2, 0, -35, "feliz", 0)
            s = math.sin((ta - 1.8) * 4 * math.tau / 1.6 * 0.5)
            return ("pe", int(_q(s * 8, 4)), 1 if s > 0.3 else (-1 if s < -0.3 else 0),
                    10, o, 0)
        if a == "idle" and e.variante == "olhar":
            return ("pe", 5 if e.ta % 1.2 < 0.6 else -5, 0, 15, o, 0)
        return ("pe", 0, 0, 5, o, 0)

    def desloc(self, e):
        if e.acao == "idle" and e.variante == "barriga":
            ta = e.ta
            if ta < 0.25:
                return 0.0, 0.0
            if ta < 1.55:
                u = (ta - 0.25) / 1.3
                return 46 * (1 - (1 - u) ** 2), 0.0
            if ta < 1.8:
                return 46.0, 0.0
            return 46 * max(0.0, 1 - (ta - 1.8) / 1.6), -abs(math.sin((ta - 1.8) * 6)) * 1.5
        if e.acao == "reacao":
            return 0.0, -abs(math.sin(e.ta * 9)) * 7
        if e.acao == "andar":
            return 0.0, -abs(math.sin(e.passo * math.tau)) * 1.5
        return super().desloc(e)

    def desenhar(self, p, pose):
        tipo, tilt, pe, asa, olhos, bolha = pose
        B = self.borda
        if tipo == "deitar":
            self._deitado(p, olhos, tilt == 2)
            return
        p.girar(tilt, 0, 0)
        self._corpo(p, pe, asa, olhos, bolha)

    def _deitado(self, p, olhos, deslizando):
        """Deitado de barriga, escorregando (cabeça para a frente)."""
        B = self.borda
        if not deslizando:
            p.girar(-8, 0, 0)
        p.forma(self.LAR, B, ("e", -25, -13, 5.5, 2.6, -35), ("e", -24.5, -7.5, 5.5, 2.6, -8))
        p.forma(self.PRETO, B, ("b", (13, -24), (14, -30), (10, -31), 2.2))
        p.forma(self.PRETO, B, ("e", 0, -13, 24, 13))
        p.forma(self.BARRIGA, None, ("e", 1, -6.5, 20, 5.5), ("e", 16, -14, 8, 7.5))
        p.forma(self.PRETO, B, ("e", -8, -21.5, 11, 3.4, 8))
        _olho(p, 13.5, -16, 2.6, olhos)
        _olho(p, 20, -16, 2.6, olhos)
        p.forma(self.LAR, (200, 100, 20), ("p", [(21.5, -13.5), (28.5, -12), (21.5, -10)]), w=0.8)
        _bochecha(p, 11, -10.5, 2.4, 1.5, self.BARRIGA)
        if deslizando:
            for k in range(3):
                p.forma((200, 225, 255), None, ("l", [(-30 - k * 3, -3 - k * 4), (-38 - k * 3, -3 - k * 4)], 1.4))

    def _corpo(self, p, pe, asa, olhos, bolha, deitado=False):
        B = self.borda
        # Pés
        lift_e = 2.5 if pe == -1 else 0
        lift_d = 2.5 if pe == 1 else 0
        p.forma(self.LAR, B, ("e", -6.5, -1.8 - lift_e, 6, 2.8), ("e", 6.5, -1.8 - lift_d, 6, 2.8))
        # Topete
        p.forma(self.PRETO, B, ("b", (0, -49), (-1, -55), (-4, -56), 2.2),
                ("b", (1, -49), (3, -55), (6, -55), 2.0))
        # Corpo
        p.forma(self.PRETO, B, ("e", 0, -26, 16.5, 24))
        # Barriga / rosto branco
        p.forma(self.BARRIGA, None, ("e", 1.5, -22, 12, 17), ("c", -2.5, -36, 6.2),
                ("c", 5.5, -36, 6.2))
        # Nadadeiras
        for lado in (-1, 1):
            p.salvar()
            ang = -asa if lado < 0 else asa
            if deitado:
                ang = -asa if lado > 0 else asa
            p.girar(ang, 13.5 * lado, -33)
            p.forma(self.PRETO, B, ("e", 15.5 * lado, -23, 4.2, 11, 10 * lado))
            p.restaurar()
        # Rosto
        _olho(p, -2.5, -37, 2.8, olhos)
        _olho(p, 5.5, -37, 2.8, olhos)
        p.forma(self.LAR, (200, 100, 20), ("p", [(-0.5, -33.2), (5.8, -33.2), (2.6, -29.6)]), w=0.8)
        _bochecha(p, -6.5, -31.5, 2.6, 1.6, self.BARRIGA)
        _bochecha(p, 9.5, -31.5, 2.6, 1.6, self.BARRIGA)
        if bolha:
            r = (0, 1.6, 3.2, 4.6, 3.2)[bolha]
            p.forma((200, 230, 255), (120, 170, 220), ("c", 6 + r * 0.7, -30.5 + r * 0.2, r), w=0.6)
            p.forma((255, 255, 255), None, ("c", 5.2 + r * 0.5, -31.5, r * 0.3))


# ------------------------------------------------------------
# ABELHA (ZUZU)
# ------------------------------------------------------------

class _Abelha(_Especie):
    frente = 18
    id = "abelha"
    caixa = (-26, -42, 24, 4)
    borda = (125, 80, 10)
    sombra = 24
    topo = (6, -32)
    boca = (3, 2)
    passo_px = 40
    voa = True
    altura_voo = 100
    altura_dormindo = 0
    idles = (("pousar", 999.0),)
    reacao_dur = 1.2
    piscar_fase = 1.7
    AMA = (255, 210, 50)
    PRETO = (48, 36, 40)
    ASA = (235, 245, 255, 165)
    ASA_B = (140, 170, 215)

    def pose(self, e):
        o = e.olhos
        a = e.acao
        bate = (1.0, 0.3, 0.65)[int(e.t * 60) % 3]
        if a == "andar":
            return (bate, o, -10, 0)
        if a == "dormir":
            return (0.55, "dormindo", 0, 1)
        if a == "reacao":
            return (bate, "feliz", -12, 0)
        if a == "feliz":
            return (bate, "feliz", 0, 0)
        if a == "idle" and e.variante == "pousar":
            k = bate if e.ta % 2.5 < 0.3 else 0.55
            return (k, o, 0, 1)
        return (bate, o, 0, 0)

    def desloc(self, e):
        if e.acao == "feliz":
            return math.sin(e.t * 3) * 6, -abs(math.sin(e.t * 5)) * 8 - 6
        return 0.0, 0.0

    def desenhar(self, p, pose):
        k, olhos, tilt, pousada = pose
        B = self.borda
        p.girar(tilt, 0, -12)
        # Asas (atrás do corpo)
        for rx0, ry0, ang, esc in ((-6, -20, 22, 0.9), (0, -21, -8, 1.0)):
            ry = max(1.2, 8.5 * k * esc)
            p.forma(self.ASA, self.ASA_B, ("e", rx0 - 1.5, ry0 - ry * 0.9, 5.8 * esc, ry, ang), w=0.8)
        # Antenas
        p.forma(self.PRETO, None, ("b", (7, -19), (5.5, -26), (3, -29), 1.4),
                ("b", (11, -19), (13.5, -25), (16, -27.5), 1.4))
        p.forma(self.PRETO, None, ("c", 3, -29.5, 2.1), ("c", 16.2, -28, 2.1))
        # Perninhas
        if pousada:
            p.forma(self.PRETO, None, ("l", [(-4, -3), (-4.5, 0.5)], 1.6),
                    ("l", [(3, -3), (3.5, 0.5)], 1.6))
        else:
            p.forma(self.PRETO, None, ("l", [(-4, -3), (-6, 0)], 1.6),
                    ("l", [(3, -3), (1.5, 0.5)], 1.6))
        # Ferrão
        p.forma(self.PRETO, B, ("p", [(-13, -14), (-20.5, -11.5), (-13, -9.5)]), w=0.8)
        # Corpo
        p.forma(self.AMA, B, ("e", 0, -12, 15, 10.5))
        for x1, x2 in ((-10.5, -6.8), (-3.5, 0.2)):
            topo = []
            base = []
            n = 6
            for i in range(n + 1):
                x = x1 + (x2 - x1) * i / n
                h = 10.5 * math.sqrt(max(0.0, 1 - (x / 15) ** 2)) - 0.2
                topo.append((x, -12 - h))
                base.append((x, -12 + h))
            p.forma(self.PRETO, None, ("p", topo + base[::-1]))
        # Rosto
        _olho(p, 6.2, -14, 2.6, olhos)
        _olho(p, 11.8, -14, 2.6, olhos)
        p.forma(OLHO, None, ("a", 9, -10.8, 2, 1.5, 200, 340, 0.8))
        _bochecha(p, 3.6, -10, 2.2, 1.4, self.AMA)
        _bochecha(p, 13.6, -10, 1.8, 1.4, self.AMA)
        # Brilho no corpo
        p.forma((255, 240, 170), None, ("e", -1, -19, 5, 1.6, 5))


# ------------------------------------------------------------
# SLIME (GELECA)
# ------------------------------------------------------------

def _gota_pts():
    pts = []
    for i in range(64):
        a = i / 64 * math.tau
        s, c = math.sin(a), math.cos(a)
        if s >= 0:
            ponta = s ** 6
            pts.append((23 * c * (1 - 0.5 * ponta), -17 - 17 * s - 12 * ponta))
        else:
            pts.append((23 * c, -17 - 17 * s))
    return pts


_GOTA = _gota_pts()


class _Slime(_Especie):
    frente = 23
    id = "slime"
    caixa = (-40, -62, 40, 4)
    borda = (45, 150, 80)
    sombra = 44
    topo = (0, -54)
    boca = (4, -8)
    passo_px = 70
    idles = (("respirar", 4.0), ("balancar", 2.0))
    reacao_dur = 1.3
    piscar_fase = 0.3
    VERDE = (120, 230, 140, 215)

    def pose(self, e):
        o = e.olhos
        a = e.acao
        if a == "andar":
            fr = e.passo % 1.0
            if fr < 0.25:
                sq = math.sin(fr / 0.25 * math.pi)
                sx, sy = 1 + 0.3 * sq, 1 - 0.3 * sq
            else:
                u = (fr - 0.25) / 0.75
                st = 0.2 * abs(2 * u - 1)
                sx, sy = 1 - st * 0.6, 1 + st
            return (_q(sx, 0.05), _q(sy, 0.05), o, 1, 0, 0)
        if a == "dormir":
            r = _q(math.sin(e.t * 2) * 0.03, 0.015)
            return (1.12 + r, 0.86 - r, "dormindo", 0, 0, 0)
        if a == "reacao":
            k = _envelope(e.ta, self.reacao_dur, 0.25)
            return (1.0, 1.0, "feliz", 1, int(_q(k * 14, 3.5)), 0)
        if a == "feliz":
            s = abs(math.sin(e.t * 5))
            sq = max(0.0, 0.25 - s) * 0.7
            return (_q(1 + sq, 0.05), _q(1 - sq + s * 0.08, 0.05), "feliz", 1, 0, 0)
        if a == "idle" and e.variante == "balancar":
            return (1.0, 1.0, "feliz", 1, 0, int(_q(math.sin(e.ta * 6) * 10, 5)))
        d = _q(math.sin(e.t * 2.2) * 0.05, 0.025)
        return (1 - d * 0.6, 1 + d, o, 0, 0, 0)

    def desloc(self, e):
        if e.acao == "andar":
            fr = e.passo % 1.0
            if fr >= 0.25:
                u = (fr - 0.25) / 0.75
                return 0.0, -22 * 4 * u * (1 - u)
            return 0.0, 0.0
        return super().desloc(e)

    def _gota(self, p, olhos, boca):
        B = self.borda
        p.forma(self.VERDE, B, ("p", _GOTA),
                ("b", (0, -44), (1.5, -50.5), (6.5, -51), 3.2))
        # Brilhos
        p.forma((255, 255, 255, 220), None, ("e", -12.5, -25, 3, 6.5, -30), ("c", -7, -36, 1.8))
        # Rosto
        _olho(p, -5, -21, 4, olhos)
        _olho(p, 7.5, -21, 4, olhos)
        if boca:
            p.forma((60, 110, 70), None, ("e", 1.2, -12.8, 3, 2.4))
            p.forma((255, 130, 150), None, ("e", 1.2, -11.8, 1.7, 1.1))
        else:
            p.forma((60, 110, 70), None, ("a", 1.2, -14, 2.6, 1.8, 200, 340, 0.9))
        p.forma((255, 150, 170, 215), None, ("e", -12, -14.5, 3.2, 1.9),
                ("e", 14.5, -14.5, 3.2, 1.9))

    def desenhar(self, p, pose):
        sx, sy, olhos, boca, sep, tilt = pose
        if sep:
            for lado in (-1, 1):
                p.salvar()
                p.mover(lado * (3 + sep * 1.4), 0)
                p.escalar(0.62, 0.62, 0, 0)
                self._gota(p, olhos, boca)
                p.restaurar()
            return
        p.girar(tilt, 0, 0)
        p.escalar(sx, sy, 0, 0)
        self._gota(p, olhos, boca)


# ------------------------------------------------------------
# FANTASMA (BUH)
# ------------------------------------------------------------

class _Fantasma(_Especie):
    frente = 24
    id = "fantasma"
    caixa = (-34, -64, 34, 4)
    borda = (135, 145, 195)
    sombra = 36
    topo = (0, -58)
    boca = (18, -16)
    passo_px = 60
    voa = True
    altura_voo = 70
    altura_dormindo = 26
    idles = (("bleh", 2.2), ("girar", 2.0))
    reacao_dur = 1.2
    piscar_fase = 2.6
    BRANCO = (250, 250, 255, 215)

    def pose(self, e):
        o = e.olhos
        a = e.acao
        onda = int(e.t * 5) % 4
        if a == "andar":
            return (onda, 0, 0, o, -8)
        if a == "dormir":
            return (int(e.t * 2) % 4, 0, 0, "dormindo", 0)
        if a == "reacao":
            return (onda, 1, 1, "bravo", 0)
        if a == "feliz":
            return (onda, 2 if int(e.t * 6) % 2 else 1, 3, "feliz", 0)
        if a == "idle" and e.variante == "bleh":
            return (onda, 2 if int(e.ta * 6) % 2 else 0, 2, "feliz", 0)
        if a == "idle" and e.variante == "girar":
            return (onda, 1, 3, "feliz", int(_q(math.sin(e.ta * math.pi) * 14, 7)))
        return (onda, 0, 0, o, 0)

    def desloc(self, e):
        if e.acao == "feliz":
            return 0.0, -abs(math.sin(e.t * 5)) * 8 - 8
        return 0.0, 0.0

    def desenhar(self, p, pose):
        onda, bracos, boca, olhos, tilt = pose
        B = self.borda
        p.girar(tilt, 0, -30)
        formas = [("c", 0, -34, 22), ("rr", -22, -34, 44, 26, 0)]
        for i, bx in enumerate((-14.67, 0.0, 14.67)):
            dy = 1.8 * math.sin(onda / 4 * math.tau + i * 2.1)
            formas.append(("c", bx, -8 + dy, 7.4))
        if bracos == 0:
            formas += [("e", -22, -20, 4.8, 3.4, -30), ("e", 22, -20, 4.8, 3.4, 30)]
        elif bracos == 1:
            formas += [("e", -24, -34, 3.4, 5.2, -25), ("e", 24, -34, 3.4, 5.2, 25)]
        else:
            formas += [("e", -24, -34, 3.4, 5.2, -25), ("e", 22, -20, 4.8, 3.4, 30)]
        p.forma(self.BRANCO, B, *formas)
        # Brilho
        p.forma((255, 255, 255, 235), None, ("e", -11, -46, 4, 2.5, 35))
        # Rosto
        if olhos == "bravo":
            _olho(p, -6.5, -34, 4.6, "aberto")
            _olho(p, 7.5, -34, 4.6, "aberto")
            p.forma(OLHO, None, ("l", [(-10.5, -42), (-3.5, -39.5)], 1.2),
                    ("l", [(11.5, -42), (4.5, -39.5)], 1.2))
        else:
            _olho(p, -6.5, -34, 4.6, olhos)
            _olho(p, 7.5, -34, 4.6, olhos)
        cor_boca = (70, 45, 80)
        if boca == 1:
            p.forma(cor_boca, None, ("e", 0.5, -23.5, 4.2, 5))
            p.forma((255, 120, 150), None, ("e", 0.5, -21.2, 2.4, 1.8))
        elif boca == 2:
            p.forma(cor_boca, None, ("a", 0.5, -26, 3.4, 2.6, 200, 340, 1.0))
            p.forma((255, 120, 150), (200, 80, 110), ("e", 2, -22.6, 2, 2.4), w=0.6)
        elif boca == 3:
            p.forma(cor_boca, None, ("a", 0.5, -26.5, 3.6, 3.4, 190, 350, 1.0))
        else:
            p.forma(cor_boca, None, ("e", 0.5, -25, 2.1, 2.6))
        _bochecha(p, -13.5, -27.5, 3.2, 1.9, (250, 250, 255), 215)
        _bochecha(p, 14.5, -27.5, 3.2, 1.9, (250, 250, 255), 215)


# ------------------------------------------------------------
# ROBÔ (BIP)
# ------------------------------------------------------------

class _Robo(_Especie):
    frente = 24
    id = "robo"
    caixa = (-40, -66, 40, 6)
    borda = (88, 98, 124)
    sombra = 30
    topo = (0, -62)
    boca = (25, -18)
    passo_px = 56
    idles = (("olhar", 2.4), ("coracao", 2.0), ("acenar", 1.8))
    reacao_dur = 1.0
    piscar_fase = 0.9
    CORPO = (170, 180, 200)
    TELA = (30, 40, 60)
    VERDE = (120, 255, 160)
    RODA = (60, 60, 70)

    def pose(self, e):
        o = e.olhos
        a = e.acao
        ant = int(e.t * 2) % 2
        roda = int(e.passo * 8) % 8
        if a == "andar":
            return (0, roda, o, ant, 0, -6)
        if a == "dormir":
            return (0, 0, "dormindo", 0, 0, 3)
        if a == "reacao":
            rot = int(_q(min(1.0, e.u * 1.25) * 360, 22.5)) % 360
            return (rot, roda, "feliz", 1, 1 + int(e.ta * 8) % 2, 0)
        if a == "feliz":
            return (0, 0, "feliz", ant, 1 + int(e.t * 6) % 2, int(_q(math.sin(e.t * 6) * 5, 5)))
        if a == "idle" and e.variante == "olhar":
            return (0, 0, "olhar_e" if e.ta % 1.2 < 0.6 else "olhar_d", ant, 0, 0)
        if a == "idle" and e.variante == "coracao":
            return (0, 0, "coracao", 1, 3, 0)
        if a == "idle" and e.variante == "acenar":
            return (0, 0, "feliz", ant, 2 if int(e.ta * 5) % 2 else 4, 0)
        return (0, 0, o, ant, 0, 0)

    def desloc(self, e):
        if e.acao == "reacao":
            return 0.0, -abs(math.sin(e.u * math.pi)) * 8
        return super().desloc(e)

    def desenhar(self, p, pose):
        rot, roda, olhos, antena, bracos, tilt = pose
        B = self.borda
        p.girar(rot, 0, -28)
        p.girar(tilt, 0, 0)
        # Garfo + roda
        p.forma((140, 150, 172), B, ("p", [(-7, -14), (7, -14), (4, -8), (-4, -8)]))
        p.forma(self.RODA, (28, 28, 34), ("c", 0, -8, 8.5))
        p.forma((110, 112, 128), None, ("c", 0, -8, 5.8))
        p.forma((170, 175, 190), None, ("c", 0, -8, 2.8))
        for i in range(4):
            a = math.radians(roda * 11.25 + i * 90)
            p.forma(self.RODA, None, ("c", math.cos(a) * 4.4, -8 - math.sin(a) * 4.4, 1.1))
        # Braços (atrás do corpo)
        maos = {0: ((-24, -20), (24, -20)), 1: ((-25, -44), (24, -20)),
                2: ((-24, -20), (25, -44)), 3: ((-22, -34), (22, -34)),
                4: ((-24, -20), (28, -38))}[bracos]
        for (mx, my), ox in zip(maos, (-15, 15)):
            p.forma((150, 160, 182), B, ("l", [(ox, -28), (mx, my)], 3.4))
            p.forma(self.CORPO, B, ("c", mx, my, 3.3))
        # Antena
        p.forma((100, 105, 125), None, ("l", [(0, -44), (0, -51)], 1.8))
        if antena:
            p.forma((255, 110, 110, 90), None, ("c", 0, -54, 6))
            p.forma((255, 70, 70), (150, 30, 30), ("c", 0, -54, 3), w=0.7)
            p.forma((255, 200, 200), None, ("c", -0.9, -54.9, 1))
        else:
            p.forma((130, 40, 40), (90, 20, 20), ("c", 0, -54, 3), w=0.7)
        # Corpo
        p.forma(self.CORPO, B, ("rr", -18, -44, 36, 32, 8))
        p.forma((214, 222, 236), None, ("rr", -15, -42.5, 9, 2.6, 1.3))
        p.forma(self.TELA, (70, 80, 104), ("rr", -13.5, -40.5, 27, 19, 4.5), w=0.9)
        # Luzinhas do peito
        p.forma((255, 200, 60), None, ("c", -10, -16.5, 1.6))
        p.forma((90, 200, 255), None, ("c", -5.5, -16.5, 1.6))
        p.forma(B, None, ("l", [(3, -17.5), (12, -17.5)], 0.9), ("l", [(3, -15.3), (12, -15.3)], 0.9))
        # Rosto na tela
        V = self.VERDE
        if olhos == "coracao":
            cx, cy = 0, -33
            p.forma((255, 110, 150), None, ("c", cx - 3, cy - 1.5, 3.3), ("c", cx + 3, cy - 1.5, 3.3),
                    ("p", [(cx - 6.2, cy - 0.5), (cx + 6.2, cy - 0.5), (cx, cy + 6)]))
            return
        dx = {"olhar_e": -2.5, "olhar_d": 2.5}.get(olhos, 0)
        if olhos in ("aberto", "olhar_e", "olhar_d"):
            p.forma(V, None, ("rr", -8.3 + dx, -37, 4.6, 6.4, 1.3), ("rr", 3.7 + dx, -37, 4.6, 6.4, 1.3))
            p.forma((230, 255, 240), None, ("rr", -7.8 + dx, -36.4, 1.5, 1.5, 0.4),
                    ("rr", 4.2 + dx, -36.4, 1.5, 1.5, 0.4))
        elif olhos == "feliz":
            p.forma(V, None, ("l", [(-8.5, -32.5), (-6, -35.5), (-3.5, -32.5)], 1.5),
                    ("l", [(3.5, -32.5), (6, -35.5), (8.5, -32.5)], 1.5))
        else:
            cor = V if olhos == "piscar" else (70, 140, 100)
            p.forma(cor, None, ("rr", -8.3, -33.5, 4.6, 1.6, 0.6), ("rr", 3.7, -33.5, 4.6, 1.6, 0.6))
        p.forma(V, None, ("l", [(-2.2, -28.4), (-0.8, -27.2), (0.8, -27.2), (2.2, -28.4)], 1.0))
        p.forma((255, 120, 170), None, ("rr", -12, -29.5, 3.2, 1.6, 0.6), ("rr", 8.8, -29.5, 3.2, 1.6, 0.6))


# ------------------------------------------------------------
# DRAGÃO (FAÍSCA)
# ------------------------------------------------------------

class _Dragao(_Especie):
    frente = 32
    id = "dragao"
    caixa = (-48, -64, 40, 4)
    borda = (25, 95, 60)
    sombra = 40
    topo = (14, -58)
    boca = (29, -27)
    passo_px = 60
    voa = True
    altura_voo = 70
    altura_dormindo = 0
    idles = (("pousar", 999.0),)
    reacao_dur = 0.9
    piscar_fase = 3.1
    VERDE = (60, 180, 110)
    ESCURO = (40, 140, 90)
    BARRIGA = (230, 240, 160)
    CHIFRE = (255, 240, 200)
    ASA = (150, 90, 210)
    ASA_E = (115, 65, 175)
    ASAS = (-30, -15, 5, 20, 5, -15)

    def pose(self, e):
        o = e.olhos
        a = e.acao
        asa = self.ASAS[int(e.t * 24) % 6]
        if a == "andar":
            return (1, asa, 0, o, -6, 0)
        if a == "dormir":
            return (0, 55, 0, "dormindo", 0, 0)
        if a == "reacao":
            return (1, asa, 1, "feliz", 8, 0)
        if a == "feliz":
            return (1, asa, 1 if int(e.t * 4) % 2 else 0, "feliz", 0, 0)
        if a == "idle" and e.variante == "pousar":
            fumaca = int(e.ta * 3) % 6
            return (0, 55, 0, o, 0, fumaca if fumaca < 3 else 0)
        return (1, asa, 0, o, 0, 0)

    def desloc(self, e):
        if e.acao == "feliz":
            return 0.0, -abs(math.sin(e.t * 5)) * 8 - 6
        return 0.0, 0.0

    def _asa(self, p, ang, cor, dx=0.0, esc=1.0):
        B = self.borda
        p.salvar()
        p.mover(dx, 0)
        p.girar(ang, -2, -28)
        p.escalar(esc, esc, -2, -28)
        pts = [(-2, -28), (-8, -44), (-22, -52), (-21, -44), (-28, -40), (-21, -35),
               (-24, -28), (-12, -27)]
        p.forma(cor, B, ("p", pts))
        membrana = _misturar(cor, (60, 20, 90), 0.3)
        p.forma(membrana, None, ("l", [(-3, -29), (-21, -44)], 0.9),
                ("l", [(-3, -29), (-21, -35)], 0.9))
        p.restaurar()

    def desenhar(self, p, pose):
        voando, asa, boca, olhos, tilt, fumaca = pose
        B = self.borda
        p.girar(tilt, 0, -18)
        if not voando:
            p.mover(0, 3)
        # Asa de trás
        esc_asa = 1.0 if voando else 0.8
        self._asa(p, asa + 10, self.ASA_E, 4, 0.85 * esc_asa)
        # Cauda
        fim = (-35, -19) if voando else (-34, -6)
        meio = (-27, -5) if voando else (-24, 2)
        p.forma(self.VERDE, B, ("b", (-11, -14), meio, fim, 5))
        d = (fim[0] - meio[0], fim[1] - meio[1])
        n = math.hypot(*d) or 1
        d = (d[0] / n, d[1] / n)
        q = (-d[1], d[0])
        ponta = (fim[0] + d[0] * 7, fim[1] + d[1] * 7)
        p.forma(self.ESCURO, B, ("p", [ponta, (fim[0] + q[0] * 4.5, fim[1] + q[1] * 4.5),
                                       (fim[0] - q[0] * 4.5, fim[1] - q[1] * 4.5)]), w=1.0)
        # Espinhos das costas
        p.forma(self.ESCURO, B, ("p", [(-11, -27), (-11, -34), (-6, -30)]),
                ("p", [(-15.5, -21), (-17.5, -27.5), (-12, -25)]),
                ("p", [(-5, -31), (-2, -37.5), (0, -32)]), w=1.0)
        # Pernas
        if voando:
            for px, cor in ((6, self.ESCURO), (-6, self.ESCURO), (-2, self.VERDE), (10, self.VERDE)):
                p.forma(cor, B, ("l", [(px, -9), (px - 1, -3.5)], 5))
        else:
            p.forma(self.ESCURO, B, ("e", 12, -3, 4.8, 3))
            p.forma(self.VERDE, B, ("e", -8, -6, 7.5, 6))
            p.forma(self.VERDE, B, ("e", 6, -2.8, 4.8, 3))
        # Corpo
        p.forma(self.VERDE, B, ("e", 0, -18, 16, 14))
        p.forma(self.BARRIGA, None, ("e", 4.5, -15, 9.5, 10.5))
        for yy in (-19, -14, -9):
            p.forma((205, 215, 130), None, ("a", 4.5, yy, 7, 1.6, 200, 340, 0.7))
        # Chifres
        p.forma(self.CHIFRE, (170, 150, 100), ("p", [(6.5, -43), (3.5, -53.5), (11, -45.5)]),
                ("p", [(15, -46), (18, -56), (20.5, -44.5)]), w=0.9)
        # Cabeça + focinho
        p.forma(self.VERDE, B, ("c", 14, -35, 12.5), ("e", 23.5, -30.5, 8.5, 6.5))
        p.forma(OLHO, None, ("c", 28, -33, 0.9), ("c", 30.3, -31.6, 0.9))
        # Olhos grandes
        _olho(p, 10.5, -37.5, 3.4, olhos)
        _olho(p, 19, -37.5, 3.4, olhos)
        if boca:
            p.forma((120, 30, 40), None, ("e", 27, -27, 3.4, 2.6))
            p.forma((255, 120, 110), None, ("e", 26.5, -26, 1.8, 1.1))
        else:
            p.forma(B, None, ("a", 24.5, -28.5, 4, 2, 200, 330, 0.9))
        _bochecha(p, 8.5, -30.5, 2.6, 1.6, self.VERDE)
        # Fumacinha
        if fumaca:
            r = 1.2 + fumaca * 0.8
            p.forma((225, 225, 230), (170, 170, 180), ("c", 31 + fumaca * 3, -36 - fumaca * 3, r), w=0.6)
        # Asa da frente
        self._asa(p, asa, self.ASA, 0.0, esc_asa)


# ------------------------------------------------------------
# UNICÓRNIO (ARCO-ÍRIS)
# ------------------------------------------------------------

class _Unicornio(_Especie):
    frente = 42
    id = "unicornio"
    caixa = (-54, -98, 56, 4)
    borda = (178, 156, 210)
    sombra = 56
    topo = (26, -80)
    boca = (40, -40)
    passo_px = 50
    idles = (("patinha", 1.8), ("cheirar", 2.8))
    reacao_dur = 1.3
    piscar_fase = 1.9
    BRANCO = (255, 250, 255)
    ESC = (232, 224, 244)
    CASCO = (205, 185, 232)
    CHIFRE = (255, 210, 80)
    CH_B = (205, 150, 40)
    FOC = (255, 226, 238)

    def pose(self, e):
        o = e.olhos
        a = e.acao
        crina = int(e.t * 5) % 4
        if a == "andar":
            return ("pe", int(e.passo * 8) % 8, o, 0, crina, 0, 0)
        if a == "dormir":
            return ("deitado", -1, "dormindo", 0, 0, 0, 0)
        if a == "reacao":
            k = _envelope(e.ta, self.reacao_dur, 0.3)
            return ("pe", -1, "feliz", int(_q(k * 28, 7)), crina, 0, 1 if k > 0.5 else 0)
        if a == "feliz":
            return ("pe", -1, "feliz", 0, crina, 2, 0)
        if a == "idle" and e.variante == "patinha":
            return ("pe", -1, o, 0, crina, 0, (0, 1, 2, 1)[int(e.ta * 6) % 4])
        if a == "idle" and e.variante == "cheirar":
            k = _envelope(e.ta, 2.8, 0.4)
            return ("pe", -1, "feliz" if k > 0.9 else o, 0, crina, (2 + int(_q(k, 0.5) * 2)) if k > 0.2 else 0, 0)
        return ("pe", -1, o, 0, crina, 0, 0)

    def desloc(self, e):
        if e.acao == "andar":
            return 0.0, -abs(math.sin(e.passo * math.tau)) * 2.5
        return super().desloc(e)

    def _crina(self, p, onda):
        pares = []
        for i, cor in enumerate(ARCO_IRIS):
            w = math.sin(onda / 4 * math.tau + i) * 1.2
            pares.append((cor, ("b", (21 - i * 1.6, -61 + i * 1.4), (9 - i * 1.8 + w, -56 + i * 1.8),
                                (5 - i * 1.2 + w, -38 + i * 1.5), 3.4)))
        p.faixas(self.borda, pares)

    def _cauda(self, p, onda):
        pares = []
        for i, cor in enumerate(ARCO_IRIS):
            w = math.sin(onda / 4 * math.tau + i * 0.8) * 2
            pares.append((cor, ("b", (-22, -33 + i * 1.6), (-38 + w, -36 + i * 2.2),
                                (-40 + i * 1.4 + w, -14 + i * 0.8), 3.4)))
        p.faixas(self.borda, pares)

    def _cabeca(self, p, olhos, onda):
        B = self.borda
        self._crina(p, onda)
        # Orelha
        p.forma(self.BRANCO, B, ("p", [(18.5, -58), (19.5, -67.5), (25, -60)]))
        p.forma((255, 180, 200), None, ("p", [(20, -59.5), (20.6, -64.5), (23.4, -60.3)]))
        # Cabeça
        p.forma(self.BRANCO, B, ("c", 25, -50, 12))
        p.forma(self.FOC, B, ("e", 34, -44.5, 7.5, 6.2, -15))
        p.forma((200, 140, 175), None, ("c", 37.5, -46, 0.9))
        p.forma((160, 110, 150), None, ("a", 35.5, -42, 2.4, 1.3, 200, 330, 0.8))
        # Chifre em espiral
        p.forma(self.CHIFRE, self.CH_B, ("p", [(23.6, -60.5), (30.5, -82), (30.2, -59)]), w=1.0)
        for fy in (-64, -69, -74):
            ex = 23.8 + (fy + 60.5) / -21.5 * 6.9
            p.forma(self.CH_B, None, ("l", [(ex + 0.2, fy + 0.6), (ex + 5.2 - (fy + 64) * -0.12, fy - 1.6)], 0.8))
        # Topete
        p.forma(ARCO_IRIS[4], self.borda, ("b", (23, -61), (28, -61), (29.5, -56), 2.6),
                ("b", (22, -60), (25.5, -58.5), (25, -54.5), 2.4), w=0.8)
        p.forma(ARCO_IRIS[0], None, ("b", (22, -60), (25.5, -58.5), (25, -54.5), 2.4))
        # Olho com cílios
        _olho(p, 27.5, -50.5, 3.2, olhos)
        if olhos in ("aberto", "piscar"):
            p.forma(OLHO, None, ("l", [(29.8, -53.2), (31.8, -55)], 0.8),
                    ("l", [(28.3, -54), (29.3, -56.2)], 0.8))
        _bochecha(p, 25, -44.5, 2.6, 1.6, self.BRANCO)

    def desenhar(self, p, pose):
        tipo, f, olhos, empina, crina, cabeca, pata = pose
        B = self.borda

        if tipo == "deitado":
            self._cauda(p, crina)
            p.mover(0, 11)
            p.forma(self.ESC, B, ("e", 13, -12.5, 7, 3))
            p.forma(self.BRANCO, B, ("e", 0, -26, 24, 13.5),
                    ("p", [(12, -34), (18, -44), (28, -40), (22, -27)]))
            p.forma(self.ESC, B, ("e", -12, -12.5, 8, 3.2))
            p.salvar()
            p.mover(-2, 10)
            p.girar(-12, 18, -40)
            self._cabeca(p, olhos, crina)
            p.restaurar()
            return

        p.girar(empina, -14, 0)
        self._cauda(p, crina)

        # Pernas: (x, fase, perto)
        pernas = ((-10, math.pi, False), (17, 0.0, False), (-17, 0.0, True), (10, math.pi, True))
        for px, fase, perto in pernas:
            dx = lift = 0.0
            if f >= 0:
                th = f / 8 * math.tau + fase
                dx = math.sin(th) * 3.5
                lift = max(0.0, math.cos(th)) * 3.5
            if empina and px > 0:
                dx, lift = 4 + (px - 10) * 0.2, 7
            if pata and px == 10:
                dx, lift = pata * 2.0, pata * 3.0
            cor = self.BRANCO if perto else self.ESC
            base = -4.4 - lift
            p.forma(cor, B, ("l", [(px, -18), (px + dx, base)], 6))
            p.forma(self.CASCO, B, ("rr", px + dx - 3.2, base, 6.4, 4.4, 1.6), w=1.0)

        # Corpo + pescoço (um contorno só)
        p.forma(self.BRANCO, B, ("e", 0, -26, 24, 13.5),
                ("p", [(12, -34), (18, -50), (29, -46), (22, -27)]))
        # Cabeça (pastar abaixa / feliz balança)
        p.salvar()
        if cabeca == 2:
            p.girar(-8 + 16 * (int(crina) % 2), 18, -34)
        elif cabeca > 2:
            p.girar(-11 * (cabeca - 2), 16, -32)
        self._cabeca(p, olhos, crina)
        p.restaurar()


_ESPECIES = {c.id: c() for c in (_Pintinho, _Gatinho, _Cachorrinho, _Pinguim, _Abelha,
                                  _Slime, _Fantasma, _Robo, _Dragao, _Unicornio)}


# ============================================================
# CACHE DE SPRITES
# ============================================================

_cache = {}
_LIMITE_CACHE = 900


def _renderizar(esp, pose, escala):
    x0, y0, x1, y1 = esp.caixa
    fw = max(2, math.ceil((x1 - x0) * escala))
    fh = max(2, math.ceil((y1 - y0) * escala))
    ss = 3 if max(fw, fh) <= 200 else 2
    sup = pygame.Surface((fw * ss, fh * ss), pygame.SRCALPHA)
    sup.fill((*esp.borda, 0))
    p = _Pincel(sup, -x0 * escala * ss, -y0 * escala * ss, escala * ss, esp.espessura)
    esp.desenhar(p, pose)
    fin = pygame.transform.smoothscale(sup, (fw, fh))
    if pygame.display.get_surface() is not None:
        fin = fin.convert_alpha()
    return fin, -x0 * escala, -y0 * escala, fin.get_bounding_rect()


def _sprite(esp, pose, escala, espelhar=False):
    """(surface, âncora_x, âncora_y, retângulo_visível) de uma pose."""
    escala = max(0.1, round(escala * 20) / 20)
    chave = (esp.id, pose, escala, espelhar)
    r = _cache.get(chave)
    if r is not None:
        return r
    if espelhar:
        sup, ax, ay, br = _sprite(esp, pose, escala, False)
        virada = pygame.transform.flip(sup, True, False)
        w = sup.get_width()
        r = (virada, w - ax, ay, pygame.Rect(w - br.right, br.y, br.w, br.h))
    else:
        r = _renderizar(esp, pose, escala)
    if len(_cache) > _LIMITE_CACHE:
        _cache.clear()
    _cache[chave] = r
    return r


def _blit_pose(tela, esp, pose, pos, escala, espelhar=False, alpha=255):
    sup, ax, ay, br = _sprite(esp, pose, escala, espelhar)
    x = round(pos[0] - ax)
    y = round(pos[1] - ay)
    if alpha < 255:
        sup.set_alpha(max(0, int(alpha)))
        tela.blit(sup, (x, y))
        sup.set_alpha(255)
    else:
        tela.blit(sup, (x, y))
    return br.move(x, y)


# ------------------------------------------------------------
# Enfeites (sombra, Zzz, bolinha, brilho, arco-íris)
# ------------------------------------------------------------

_sombras = {}


def _sombra(tela, centro, largura, alpha=80):
    largura = max(6, int(largura) // 2 * 2)
    chave = (largura, alpha)
    s = _sombras.get(chave)
    if s is None:
        if len(_sombras) > 80:
            _sombras.clear()
        h = max(4, largura // 4)
        s = pygame.Surface((largura, h), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (0, 0, 0, alpha), s.get_rect())
        _sombras[chave] = s
    tela.blit(s, s.get_rect(center=(round(centro[0]), round(centro[1]))))


def _zzz(tela, pos, tempo, escala=1.0, cor=(235, 240, 255)):
    """Três "Z" subindo e sumindo."""
    for i in range(3):
        fase = (tempo * 0.55 + i / 3) % 1.0
        tam = max(8, int((8 + fase * 10) * escala))
        tam -= tam % 2
        sup = ui.texto("Z", tam, cor)
        x = pos[0] + (8 + fase * 16 + math.sin(fase * 6) * 3) * escala
        y = pos[1] - fase * 34 * escala
        alpha = int(255 * min(1.0, fase * 5, (1 - fase) * 3))
        sup.set_alpha(alpha)
        tela.blit(sup, sup.get_rect(center=(round(x), round(y))))
        sup.set_alpha(255)


_bolas = {}


def desenhar_bola(tela, centro, raio=8):
    """A bolinha do pet (vermelha com faixa branca) — use também na cena."""
    raio = max(3, int(raio))
    s = _bolas.get(raio)
    if s is None:
        ss = 4
        d = (raio * 2 + 2) * ss
        g = pygame.Surface((d, d), pygame.SRCALPHA)
        c = d // 2
        r = raio * ss
        pygame.draw.circle(g, (120, 20, 30), (c, c), r)
        pygame.draw.circle(g, (235, 70, 70), (c, c), r - ss)
        pygame.draw.arc(g, (255, 255, 255), (c - r, c - r * 0.55, 2 * r, r * 1.1),
                        math.pi * 1.05, math.pi * 1.95, max(2, int(r * 0.28)))
        pygame.draw.circle(g, (255, 200, 200), (c - r * 0.35, c - r * 0.4), r * 0.2)
        s = pygame.transform.smoothscale(g, (d // ss, d // ss))
        _bolas[raio] = s
    tela.blit(s, s.get_rect(center=(round(centro[0]), round(centro[1]))))


_halos = {}


def _halo(tela, centro, raio, alpha):
    raio = int(raio)
    s = _halos.get(raio)
    if s is None:
        s = pygame.Surface((raio * 2, raio * 2), pygame.SRCALPHA)
        for i in range(12):
            r = raio * (1 - i / 12)
            pygame.draw.circle(s, (150, 190, 255, 10 + i * 4), (raio, raio), r)
        _halos[raio] = s
    s.set_alpha(int(alpha))
    tela.blit(s, s.get_rect(center=(round(centro[0]), round(centro[1]))))
    s.set_alpha(255)


_arcos = {}


def _arco_iris(tela, centro, raio, alpha):
    raio = int(raio)
    s = _arcos.get(raio)
    if s is None:
        larg = max(2, raio // 7)
        s = pygame.Surface((raio * 2 + 4, raio + 4), pygame.SRCALPHA)
        for i, cor in enumerate(ARCO_IRIS):
            r = raio - i * larg
            ret = pygame.Rect(0, 0, r * 2, r * 2)
            ret.center = (raio + 2, raio + 2)
            pygame.draw.arc(s, (*cor, 200), ret, 0, math.pi, larg + 1)
        _arcos[raio] = s
    s.set_alpha(int(alpha))
    tela.blit(s, s.get_rect(midbottom=(round(centro[0]), round(centro[1]))))
    s.set_alpha(255)


def _brilho(tela, pos, tam, cor):
    x, y = pos
    pygame.draw.polygon(tela, cor, [(x, y - tam), (x + tam * 0.3, y), (x, y + tam),
                                    (x - tam * 0.3, y)])
    pygame.draw.polygon(tela, cor, [(x - tam, y), (x, y - tam * 0.3), (x + tam, y),
                                    (x, y + tam * 0.3)])


def _olhos_por_tempo(esp, t):
    return "piscar" if (t + esp.piscar_fase) % 3.6 < 0.13 else "aberto"


# ============================================================
# PET PARADO (tela de fim de jogo, provador da loja, retrato)
# ============================================================

_anim_parado = _Anim()


def desenhar_parado(tela, pet_id, pos_pes, tempo, feliz=False, escala=0.8):
    """
    Pet parado com os pés/base em `pos_pes`.
    feliz=True -> pulinhos de alegria; False -> balanço calmo.
    pet_id "" ou desconhecido -> não desenha nada.
    """
    esp = _ESPECIES.get(pet_id)
    if esp is None:
        return None
    e = _anim_parado
    e.acao = "feliz" if feliz else "parado"
    e.variante = None
    e.t = e.ta = tempo
    e.u = 0.0
    e.passo = 0.0
    e.olhos = "feliz" if feliz else _olhos_por_tempo(esp, tempo)
    e.trazendo = e.rapido = e.perto = False

    x, y = pos_pes
    dx, dy = esp.desloc(e)
    voo = 0.0
    if esp.voa:
        voo = 10 + math.sin(tempo * 2.2) * 3
    _sombra(tela, (x, y), esp.sombra * escala * (1 - min(0.4, (voo - dy) / 60)))
    pose = esp.pose(e)
    if not feliz:
        tilt = _q(math.sin(tempo * 1.6) * 3, 1.5)
        if tilt and esp.id in ("slime", "gatinho", "cachorrinho", "pintinho", "pinguim",
                               "robo", "fantasma"):
            pose = _com_balanco(esp, pose, tilt)
    return _blit_pose(tela, esp, pose, (x + dx * escala, y + (dy - voo) * escala), escala)


def _com_balanco(esp, pose, tilt):
    """Coloca uma inclinação suave na pose (balanço calmo)."""
    i = {"pintinho": 0, "slime": 5, "robo": 5, "fantasma": 4,
         "pinguim": 1, "gatinho": 4, "cachorrinho": None}.get(esp.id)
    if i is None or not isinstance(pose[i], (int, float)) or pose[i] != 0:
        return pose
    lst = list(pose)
    lst[i] = int(tilt) if float(tilt).is_integer() else tilt
    return tuple(lst)


_icones = {}


def icone(pet_id, tamanho):
    """Surface quadrada `tamanho` x `tamanho` com o pet (card da loja)."""
    chave = (pet_id, tamanho)
    s = _icones.get(chave)
    if s is not None:
        return s
    s = pygame.Surface((tamanho, tamanho), pygame.SRCALPHA)
    esp = _ESPECIES.get(pet_id)
    if esp is not None:
        e = _Anim()
        e.t = 0.35
        pose = esp.pose(e)
        # Mede o desenho na escala 1 para enquadrar bem
        _, ax, ay, br = _sprite(esp, pose, 1.0)
        maior = max(br.w, br.h + 3)
        escala = tamanho * 0.86 / maior
        sup, ax2, ay2, br2 = _sprite(esp, pose, escala)
        # pés na base do quadro, centralizado na horizontal
        ox = (tamanho - br2.w) / 2 - br2.x
        oy = tamanho - (tamanho - br2.h) / 2 - br2.bottom - tamanho * 0.02
        _sombra(s, (ox + ax2, min(tamanho - 3, oy + ay2 + 1)), esp.sombra * escala * 0.9, 60)
        s.blit(sup, (round(ox), round(oy)))
    if len(_icones) > 120:
        _icones.clear()
    _icones[chave] = s
    return s


# ============================================================
# PET NO MUNDO (segue o ovo na casa)
# ============================================================

_cliques_hoje = {"dia": None, "n": 0}
LIMITE_CLIQUES_DIA = 10


def _tem_casinha(ctx):
    tem = getattr(ctx, "tem_casinha", None)
    if tem is not None:
        return bool(tem() if callable(tem) else tem)
    try:
        return "casinha_pet" in ctx.app.save["moveis"]
    except (AttributeError, KeyError, TypeError):
        return False


class PetNoMundo:
    """O pet que segue o ovo na casa (CASA/SOL/BRINCAR)."""

    DIST_ATRAS = 95
    VEL_MAX = 240
    OCIOSO = 8.0
    SONO = 30.0

    def __init__(self, pet_id):
        self.id = pet_id if pet_id in _ESPECIES else ""
        self.esp = _ESPECIES.get(self.id)
        self.escala = ESCALA_MUNDO
        self.x = 400.0
        self.chao = 640.0
        self.y_chao = 640.0
        self.olhando = 1
        self.vel = 0.0
        self.passo = 0.0
        self.andando = False
        self.modo = "seguir"            # seguir | buscar | voltar | ir_casinha | casinha
        self.dormindo = False
        self.parado = 0.0
        self.acordado = 0.0             # tempo acordado à força (clique)
        self.t = random.uniform(0, 20)
        self.trazendo = False
        self.alt = float(self.esp.altura_voo) if self.esp else 0.0
        self.pouso = 0.0                # abelha pousada na cabeça do ovo (0..1)
        self.livre = 1.0                # abelha voando em "8" (0..1)
        self.alpha = 255

        self.acao = "parado"
        self.ta = 0.0
        self.idle_var = None
        self.idle_t = 0.0
        self.idle_i = 0

        self.reacao = 0.0
        self.recarga = 0.0
        self._reacao_x0 = 0.0
        self._teleportou = False
        self._sons = []                 # [tempo, nome, vol]

        self._busca_x = None
        self._ao_chegar = None
        self._ao_entregar = None

        self._ovo_x = None
        self._dir_ovo = 1
        self._ovo_centro = (0, 0)
        self._alt_ovo = ALTURA_OVO
        self._loop_a0 = 0.0
        self._rect = pygame.Rect(0, 0, 0, 0)
        self._anim = _Anim()

        self.coracoes = []
        self.brilhos = []
        self.fogo = []
        self._brilho_t = 0.0

    # --------------------------------------------------------
    # API
    # --------------------------------------------------------

    @property
    def rect(self):
        return self._rect

    def teleportar(self, x, chao):
        """Reaparece junto do ovo (ao trocar de cômodo)."""
        self.x = float(x)
        self.chao = self.y_chao = float(chao)
        self.vel = 0.0
        self.andando = False
        self.modo = "seguir"
        self.dormindo = False
        self.parado = 0.0
        self.trazendo = False
        self._busca_x = self._ao_chegar = self._ao_entregar = None
        self.reacao = 0.0
        self.alpha = 255
        self.pouso = 0.0
        self._ovo_x = None
        if self.esp:
            self.alt = float(self.esp.altura_voo)
        self._atualizar_rect()

    def buscar(self, x_alvo, ao_chegar, ao_entregar=None):
        """Corre até x_alvo; chama ao_chegar() ao chegar e volta "trazendo"
        a bola. Ao entregar perto do ovo: diversão +5 (e ao_entregar())."""
        if not self.esp:
            return
        if self.modo == "casinha":
            self.x, self.y_chao = float(CASINHA[0]), float(CASINHA[1])
        self.modo = "buscar"
        self._busca_x = max(30.0, min(LARGURA - 30.0, float(x_alvo)))
        self._ao_chegar = ao_chegar
        self._ao_entregar = ao_entregar
        self.trazendo = False
        self.dormindo = False
        self.reacao = 0.0
        self.alpha = 255

    def clicar(self, pos, ctx):
        if not self.esp or not self._rect.collidepoint(pos):
            return False
        noite = bool(getattr(ctx, "noite", False))
        if self.modo == "casinha":
            self._sair_casinha()
        if self.modo == "ir_casinha":
            self.modo = "seguir"
        self.dormindo = False
        self.parado = 0.0
        self.acordado = 25.0 if noite else 10.0

        topo = self._pos_topo()
        # Carinho: corações + diversão (recarga de 10 s, máx 10 por dia)
        for _ in range(4):
            self.coracoes.append([topo[0] + random.uniform(-18, 18), topo[1] + random.uniform(-6, 10),
                                  random.uniform(-18, 18), 1.2])
        hoje = datetime.date.today()
        if _cliques_hoje["dia"] != hoje:
            _cliques_hoje["dia"] = hoje
            _cliques_hoje["n"] = 0
        if self.recarga <= 0 and _cliques_hoje["n"] < LIMITE_CLIQUES_DIA:
            self.recarga = 10.0
            _cliques_hoje["n"] += 1
            extra = 2 if self.id == "gatinho" else 0   # ronrona: diversão em dobro
            self._mudar(ctx, "diversao", 2 + extra, topo)

        if self.modo in ("buscar", "voltar"):
            return True
        self._iniciar_reacao(ctx, topo)
        return True

    # --------------------------------------------------------
    # REAÇÕES AO CLIQUE
    # --------------------------------------------------------

    def _iniciar_reacao(self, ctx, topo):
        esp = self.esp
        self.reacao = esp.reacao_dur
        self._reacao_x0 = self.x
        self._teleportou = False
        self.acao = "reacao"
        self.ta = 0.0
        pid = self.id
        if pid == "pintinho":
            self._som(ctx, "ponto")
            self._texto(ctx, t("PIU!"), topo, (255, 230, 90))
        elif pid == "gatinho":
            self._som(ctx, "selecionar", 0.5)
            self._texto(ctx, t("RRRR..."), topo, (255, 170, 200))
        elif pid == "cachorrinho":
            self._som(ctx, "boing", 0.7)
            self._texto(ctx, t("AU AU!"), topo, (255, 230, 170))
        elif pid == "pinguim":
            self._som(ctx, "asa")
            self._sons = [[0.25, "asa", 0.8], [0.5, "asa", 0.6]]
        elif pid == "abelha":
            self._som(ctx, "asa")
            self._texto(ctx, t("ZZZUM!"), topo, (255, 220, 60))
            cx, cy = self._ovo_centro
            px, py = self._pos_desenho()[:2]
            self._loop_a0 = math.atan2((py - cy) / 0.6, px - cx)
        elif pid == "slime":
            self._som(ctx, "mola")
        elif pid == "fantasma":
            self._som(ctx, "virar")
            self._texto(ctx, t("BUH!"), topo, (210, 220, 255))
        elif pid == "robo":
            self._som(ctx, "ponto", 0.7)
            self._sons = [[0.2, "ponto", 0.7], [0.4, "ponto", 0.7]]
            self._texto(ctx, t("BIP BIP!"), topo, (120, 255, 160))
        elif pid == "dragao":
            self._som(ctx, "explosao", 0.25)
            if self._ovo_x is not None:
                self.olhando = -1 if self._ovo_x > self.x else 1
        elif pid == "unicornio":
            self._som(ctx, "acerto")
        elif pid == "tartaruga":
            self._som(ctx, "bater", 0.6)
            self._texto(ctx, t("TOC!"), topo, (200, 240, 160))
        elif pid == "coelho":
            self._som(ctx, "mola")
            self._texto(ctx, t("BOING!"), topo, (255, 200, 220))
        elif pid == "capivara":
            self._som(ctx, "selecionar", 0.4)
            self._texto(ctx, t("RELAXA..."), topo, (255, 200, 140))

    def _atualizar_reacao(self, dt, ctx):
        u = 1 - self.reacao / self.esp.reacao_dur
        pid = self.id
        if pid == "fantasma":
            if u < 0.3:
                self.alpha = 255 * (1 - u / 0.3)
            elif u < 0.45:
                self.alpha = 0
                if not self._teleportou:
                    self._teleportou = True
                    lado = 1 if self.x < self._ovo_x else -1
                    self.x = max(40.0, min(LARGURA - 40.0, self._ovo_x + lado * self._distancia()))
                    self._dir_ovo = -lado
                    self.olhando = -lado
            else:
                self.alpha = 255 * min(1.0, (u - 0.45) / 0.35)
        elif pid == "dragao" and u < 0.7:
            bx, by = self._pos_boca()
            for _ in range(2):
                ang = random.uniform(-0.8, -0.3)
                v = random.uniform(140, 220)
                self.fogo.append([bx, by, math.cos(ang) * v * self.olhando,
                                  math.sin(ang) * v, 0.45, random.uniform(3, 6)])
        elif pid == "unicornio" and u > 0.2 and random.random() < dt * 14:
            x, y = self._pos_topo()
            self.brilhos.append([x + random.uniform(-40, 40), y + random.uniform(-40, 0),
                                 0.8, random.choice(ARCO_IRIS)])

    # --------------------------------------------------------
    # ATUALIZAR
    # --------------------------------------------------------

    def atualizar(self, dt, ctx):
        if not self.esp:
            return
        esp = self.esp
        dt = min(dt, 0.1)
        self.t += dt
        self.chao = float(getattr(ctx, "ovo_chao", self.chao))
        ovo_x = float(ctx.ovo_x)
        if self._ovo_x is None:
            self._ovo_x = ovo_x
        dxo = ovo_x - self._ovo_x
        self._ovo_x = ovo_x
        ovo_mexeu = abs(dxo) > 0.2
        if ovo_mexeu:
            self._dir_ovo = 1 if dxo > 0 else -1
        esq = getattr(ctx, "olhando_esq", None)
        if isinstance(esq, bool) and (ovo_mexeu or self.modo != "seguir"):
            self._dir_ovo = -1 if esq else 1
        alt_ovo = getattr(ctx, "ovo_altura", ALTURA_OVO)
        self._alt_ovo = alt_ovo
        self._ovo_centro = (ovo_x, self.chao - alt_ovo * 0.5)
        noite = bool(getattr(ctx, "noite", False))
        self._anim.noite = noite

        self._atualizar_efeitos(dt)
        self.recarga = max(0.0, self.recarga - dt)
        self.acordado = max(0.0, self.acordado - dt)

        for s in self._sons:
            s[0] -= dt
            if s[0] <= 0:
                self._som(ctx, s[1], s[2])
        self._sons = [s for s in self._sons if s[0] > 0]

        if self.reacao > 0:
            self.reacao -= dt
            self._atualizar_reacao(dt, ctx)
            if self.reacao <= 0:
                self.reacao = 0.0
                self.alpha = 255

        comodo = getattr(ctx, "comodo", "")
        casinha = comodo == "SOL" and _tem_casinha(ctx)

        # ---------------- dentro da casinha ----------------
        if self.modo == "casinha":
            if not casinha or self.acordado > 0 or (not noite and ovo_mexeu):
                self._sair_casinha()
            else:
                self._atualizar_rect()
                return

        # ---------------- para onde ir ----------------
        alvo = self._alvo_seguir(ovo_x)
        vmax = self.VEL_MAX
        limiar_ir, limiar_parar = 12.0, 3.0
        alvo_chao = self.chao

        if self.modo == "buscar":
            alvo = self._busca_x
            vmax = self.VEL_MAX * (2.0 if self.id == "cachorrinho" else 1.2)
            limiar_ir = 2.0
            if abs(alvo - self.x) < 8:
                self.modo = "voltar"
                self.trazendo = True
                self.vel *= 0.3
                if self._ao_chegar:
                    self._ao_chegar()
                self._ao_chegar = None
                self._som(ctx, "pulo", 0.5)
        elif self.modo == "voltar":
            vmax = self.VEL_MAX * (2.0 if self.id == "cachorrinho" else 1.2)
            limiar_ir = 2.0
            if abs(self.x - ovo_x) < self._distancia() + 20 or abs(alvo - self.x) < 10:
                self._entregar(ctx)
        elif self.modo == "ir_casinha":
            alvo = float(CASINHA[0])
            limiar_ir = 2.0
            if not casinha or (ovo_mexeu and not noite):
                self.modo = "seguir"
            else:
                if abs(self.x - alvo) < 70:
                    alvo_chao = float(CASINHA[1])
                if abs(self.x - alvo) < 5:
                    self.modo = "casinha"
                    self.dormindo = False
                    self.vel = 0.0
                    self._atualizar_rect()
                    return
        elif (self.modo == "seguir" and casinha and self.acordado <= 0 and self.reacao <= 0
              and (noite or self.parado >= self.SONO)):
            self.modo = "ir_casinha"
            self.dormindo = False
            alvo = float(CASINHA[0])

        vmax *= getattr(self.esp, "vel_mult", 1.0)
        self.y_chao += (alvo_chao - self.y_chao) * min(1.0, dt * 6)

        # ---------------- andar ----------------
        dx = alvo - self.x
        if self.dormindo:
            if abs(dx) > 60:
                self.dormindo = False
            else:
                dx = 0.0
        if self.reacao > 0 and self.modo == "seguir":
            dx = 0.0
        if self.acao == "idle" and self.idle_var == "barriga" and abs(dx) < 60:
            dx = 0.0

        if abs(dx) > (limiar_parar if self.andando else limiar_ir):
            self.andando = True
            v_des = max(-vmax, min(vmax, dx * 5))
        else:
            self.andando = False
            v_des = 0.0
        self.vel += (v_des - self.vel) * min(1.0, dt * 9)
        if not self.andando and abs(self.vel) < 8:
            self.vel = 0.0
        self.x += self.vel * dt
        self.passo += abs(self.vel) * dt / (esp.passo_px * self.escala)
        movendo = abs(self.vel) > 20

        # Para onde olha
        if movendo:
            self.olhando = 1 if self.vel > 0 else -1
        elif self.reacao <= 0 and abs(ovo_x - self.x) > 20 and self.modo == "seguir":
            if not (self.acao == "idle" and self.idle_var == "barriga"):
                self.olhando = 1 if ovo_x > self.x else -1

        # Tempo parado -> ocioso -> dorme
        if movendo or ovo_mexeu or self.modo != "seguir" or self.reacao > 0:
            self.parado = 0.0
        else:
            self.parado += dt
        limite = self.SONO
        if noite:
            limite = 20.0
        if getattr(ctx, "luz_apagada", False):
            limite = 4.0
        if (not self.dormindo and self.modo == "seguir" and self.parado >= limite
                and self.acordado <= 0):
            self.dormindo = True

        # ---------------- ação / animação ----------------
        if self.reacao > 0:
            acao = "reacao"
        elif self.dormindo:
            acao = "dormir"
        elif movendo:
            acao = "andar"
        elif self.parado >= self.OCIOSO:
            acao = "idle"
        else:
            acao = "parado"
        if acao != self.acao:
            self.acao = acao
            self.ta = 0.0
            if acao == "idle":
                self.idle_var = esp.idles[self.idle_i % len(esp.idles)][0]
                self.idle_i += 1
                self.idle_t = 0.0
        else:
            self.ta += dt
        if self.acao == "idle":
            self._atualizar_idle(dt)
        else:
            self.idle_var = None

        # Voadores: altura
        if esp.voa:
            alvo_alt = esp.altura_voo
            if self.acao == "dormir":
                alvo_alt = esp.altura_dormindo
            elif self.modo == "buscar" or (self.modo == "voltar" and self.trazendo):
                alvo_alt = min(esp.altura_voo, 34)
            elif self.id == "dragao" and self.acao == "idle":
                alvo_alt = 0
            if self.modo == "ir_casinha" and abs(self.x - CASINHA[0]) < 140:
                alvo_alt = 8
            self.alt += (alvo_alt - self.alt) * min(1.0, dt * 3)
            quer_pouso = self.id == "abelha" and self.acao == "idle" and self.idle_var == "pousar"
            self.pouso += ((1.0 if quer_pouso else 0.0) - self.pouso) * min(1.0, dt * 2.5)
            livre = 0.0 if self.acao == "dormir" or self.modo in ("buscar", "voltar") else 1.0
            self.livre += (livre - self.livre) * min(1.0, dt * 2.0)

        # Brilhos do unicórnio ao andar (3 por segundo)
        if self.id == "unicornio" and movendo:
            self._brilho_t += dt
            if self._brilho_t >= 0.33:
                self._brilho_t = 0.0
                x, y = self._pos_desenho()[:2]
                self.brilhos.append([x - self.olhando * 30 * self.escala + random.uniform(-6, 6),
                                     y - random.uniform(8, 40) * self.escala, 0.9,
                                     random.choice(ARCO_IRIS)])

        self._atualizar_rect()

    def _atualizar_idle(self, dt):
        esp = self.esp
        self.idle_t += dt
        durs = dict(esp.idles)
        if self.idle_var is not None:
            if self.idle_t >= durs.get(self.idle_var, 3.0):
                self.idle_var = None
                self.idle_t = 0.0
                self.ta = 0.0
        elif self.idle_t >= 2.6:
            self.idle_var = esp.idles[self.idle_i % len(esp.idles)][0]
            self.idle_i += 1
            self.idle_t = 0.0
            self.ta = 0.0

    def _distancia(self):
        """95 px atrás do ovo (design), um pouco mais para os bichos compridos."""
        return max(self.DIST_ATRAS, 72 + self.esp.frente * self.escala)

    def _alvo_seguir(self, ovo_x):
        d = self._distancia()
        alvo = ovo_x - d * self._dir_ovo
        if alvo < 45 or alvo > LARGURA - 45:
            alvo = ovo_x + d * self._dir_ovo
        return max(45.0, min(LARGURA - 45.0, alvo))

    def _entregar(self, ctx):
        self.modo = "seguir"
        self.trazendo = False
        topo = self._pos_topo()
        self._mudar(ctx, "diversao", 5, topo)
        for _ in range(5):
            self.coracoes.append([topo[0] + random.uniform(-20, 20), topo[1] + random.uniform(-5, 10),
                                  random.uniform(-20, 20), 1.2])
        self._som(ctx, "acerto", 0.6)
        if self._ao_entregar:
            self._ao_entregar()
        self._ao_entregar = None
        self.parado = 0.0

    def _sair_casinha(self):
        self.modo = "seguir"
        self.x = float(CASINHA[0])
        self.y_chao = float(CASINHA[1])
        self.dormindo = False
        self.parado = 0.0

    # --------------------------------------------------------
    # POSIÇÕES
    # --------------------------------------------------------

    def _preparar_anim(self):
        e = self._anim
        esp = self.esp
        e.acao = self.acao
        if e.acao == "idle" and self.idle_var is None:
            e.acao = "parado"
        e.variante = self.idle_var
        e.t = self.t
        e.ta = self.ta
        e.u = 1 - self.reacao / esp.reacao_dur if self.reacao > 0 else 0.0
        e.passo = self.passo
        e.rapido = abs(self.vel) > 250 or self.modo in ("buscar", "voltar")
        e.perto = self._ovo_x is not None and abs(self._ovo_x - self.x) < 170
        e.trazendo = self.trazendo
        if e.acao == "dormir":
            e.olhos = "dormindo"
        elif e.acao == "reacao":
            e.olhos = "feliz"
        else:
            e.olhos = _olhos_por_tempo(esp, self.t)
        return e

    def _pos_desenho(self):
        """(x, y dos pés, olhando) já com pulinhos, voo e reações."""
        esp = self.esp
        e = self._preparar_anim()
        dx, dy = esp.desloc(e)
        olhando = self.olhando
        x = self.x + dx * olhando * self.escala
        y = self.y_chao + dy * self.escala
        if esp.voa:
            if self.id == "abelha":
                amp = (1 - self.pouso) * self.livre
                x += 40 * math.sin(self.t * 1.7) * amp
                y += 15 * math.sin(self.t * 3.4) * amp
                if not self.andando and self.reacao <= 0 and amp > 0.5:
                    olhando = 1 if math.cos(self.t * 1.7) > 0 else -1
            elif self.id == "fantasma":
                y += math.sin(self.t * 1.5) * 6
            elif self.id == "dragao":
                y += math.sin(self.t * 2.2) * 4 * min(1.0, self.alt / 30)
            y -= self.alt * self.escala
            if self.id == "abelha" and self.pouso > 0.01:
                cx = self._ovo_x + 10 * self._dir_ovo
                cy = self.chao - self._alt_ovo - 1
                x += (cx - x) * self.pouso
                y += (cy - y) * self.pouso
            if self.id == "abelha" and self.acao == "reacao":
                cx, cy = self._ovo_centro
                a = self._loop_a0 + e.u * math.tau
                x = cx + math.cos(a) * 110
                y = cy + math.sin(a) * 66
                olhando = -1 if math.sin(a) > 0 else 1
        if self.id == "cachorrinho" and self.acao == "reacao":
            olhando = self.olhando * (1 if math.cos(e.u * math.tau) > 0 else -1)
        return x, y, olhando

    def _pos_topo(self):
        x, y, olh = self._pos_desenho()
        tx, ty = self.esp.topo
        return x + tx * olh * self.escala, y + ty * self.escala

    def _pos_boca(self):
        x, y, olh = self._pos_desenho()
        bx, by = self.esp.boca
        return x + bx * olh * self.escala, y + by * self.escala

    def _atualizar_rect(self):
        if not self.esp:
            return
        if self.modo == "casinha":
            self._rect = pygame.Rect(CASINHA[0] - 26, CASINHA[1] - 64, 52, 64)
            return
        x, y, olh = self._pos_desenho()
        e = self._anim
        pose = self.esp.pose(e)
        sup, ax, ay, br = _sprite(self.esp, pose, self.escala, olh < 0)
        r = br.move(round(x - ax), round(y - ay)).inflate(14, 14)
        if r.w < 56:
            r.inflate_ip(56 - r.w, 0)
        if r.h < 56:
            r.inflate_ip(0, 56 - r.h)
        self._rect = r

    # --------------------------------------------------------
    # EFEITOS
    # --------------------------------------------------------

    def _atualizar_efeitos(self, dt):
        for c in self.coracoes:
            c[0] += c[2] * dt
            c[1] -= 60 * dt
            c[3] -= dt
        self.coracoes = [c for c in self.coracoes if c[3] > 0]
        for b in self.brilhos:
            b[1] -= 10 * dt
            b[2] -= dt
        self.brilhos = [b for b in self.brilhos if b[2] > 0]
        for f in self.fogo:
            f[0] += f[2] * dt
            f[1] += f[3] * dt
            f[3] -= 60 * dt
            f[4] -= dt
        self.fogo = [f for f in self.fogo if f[4] > 0]

    def _som(self, ctx, nome, vol=1.0):
        som = getattr(ctx, "som", None)
        if som:
            som(nome, vol)

    def _texto(self, ctx, msg, pos, cor):
        textos = getattr(ctx, "textos", None)
        if textos is not None:
            textos.adicionar(msg, (pos[0], pos[1] - 14), cor, 14)

    def _mudar(self, ctx, nome, delta, pos):
        mudar = getattr(ctx, "mudar_necessidade", None)
        if mudar:
            mudar(nome, delta, (int(pos[0]), int(pos[1])))

    # --------------------------------------------------------
    # DESENHAR
    # --------------------------------------------------------

    def desenhar(self, tela, ctx):
        if not self.esp:
            return
        esp = self.esp
        t = self.t
        noite = bool(getattr(ctx, "noite", False))

        if self.modo == "casinha":
            _zzz(tela, (CASINHA[0] + 6, CASINHA[1] - 68), t, 1.0)
            self._desenhar_efeitos(tela)
            return

        x, y, olh = self._pos_desenho()
        e = self._anim
        pose = esp.pose(e)

        # Sombra no chão
        altura = self.y_chao - y
        if self.pouso < 0.5:
            fator = 1 - min(0.55, max(0.0, altura) / 220)
            _sombra(tela, (x, self.y_chao), esp.sombra * self.escala * fator,
                    int(80 * fator * self.alpha / 255))

        # Brilho do fantasma à noite
        if self.id == "fantasma" and noite:
            pul = 0.85 + 0.15 * math.sin(t * 2)
            _halo(tela, (x, y - 34 * self.escala), 58 * self.escala, 255 * pul * self.alpha / 255)

        if self.alpha > 3:
            _blit_pose(tela, esp, pose, (x, y), self.escala, olh < 0, self.alpha)

        if self.trazendo:
            bx, by = esp.boca
            desenhar_bola(tela, (x + bx * olh * self.escala, y + by * self.escala),
                          6 * self.escala)

        # Arco-íris do unicórnio
        if self.id == "unicornio" and self.reacao > 0:
            u = 1 - self.reacao / esp.reacao_dur
            if u > 0.15:
                a = min(1.0, (u - 0.15) * 4, (1 - u) * 4) * 235
                _arco_iris(tela, (x + 4 * olh * self.escala, y - 78 * self.escala),
                           int(44 * self.escala), a)

        if self.acao == "dormir":
            tx, ty = esp.topo
            _zzz(tela, (x + tx * 0.5 * olh * self.escala, y + (ty + 6) * self.escala), t, 1.0)

        self._desenhar_efeitos(tela)

    def _desenhar_efeitos(self, tela):
        for f in self.fogo:
            k = f[4] / 0.45
            cor = _misturar((255, 90, 30), (255, 235, 90), k)
            pygame.draw.circle(tela, cor, (round(f[0]), round(f[1])), max(1, round(f[5] * (0.4 + k * 0.6))))
        for b in self.brilhos:
            _brilho(tela, (b[0], b[1]), 2 + b[2] * 6, b[3])
        for x, y, _, vida in self.coracoes:
            ui.coracao(tela, (int(x), int(y)), int(16 * min(1, vida + 0.3)))


# Coleção nova (registra-se no CATALOGO e em _ESPECIES)
from core import pets_novos  # noqa: E402,F401
