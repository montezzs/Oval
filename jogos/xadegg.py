import math
import random
import time

import pygame

from settings import *
from core import ui
from core.idioma import t as tr
from jogos.base_multi import CORES_JOGADOR
from jogos.jogo_velha import JogoTabuleiro, TECLAS_DIR, TECLAS_OK, fundo_mesa

# ============================================================
# XADEGG (XADREZ DE OVINHOS)
# ============================================================
# Regras completas: xeque, mate, afogamento, roque, en passant,
# promoção (automática para rainha), empate por material
# insuficiente, 50 lances e repetição tripla.
#
# Motor: tabuleiro 10×12 ("mailbox", índices 21..98; ' ' = fora,
# '.' = vazio; MAIÚSCULAS = brancas = J1, minúsculas = pretas = J2).
# Lance = (origem, destino, flag) com flag 0 normal, 1 en passant,
# 2 roque, 3 promoção, 4 avanço duplo do peão.
# Bot: FÁCIL aleatório preferindo capturas; MÉDIO minimax 2
# (material); DIFÍCIL alfa-beta até 4 com quiescência, material +
# tabelas posicionais e limite de 1,5 s (roda numa thread).

VAZIO, FORA = ".", " "
DN = (-21, -19, -12, -8, 8, 12, 19, 21)
DB = (-11, -9, 9, 11)
DR = (-10, -1, 1, 10)
DK = DB + DR
MASCARA_ROQUE = {95: "KQ", 98: "K", 91: "Q", 25: "kq", 28: "k", 21: "q"}
VAL = {"P": 100, "N": 320, "B": 330, "R": 500, "Q": 900, "K": 0}
MATE = 100000
INF = 10 ** 9
CASAS = [21 + r * 10 + c for r in range(8) for c in range(8)]
I64 = {s: (s // 10 - 2) * 8 + (s % 10 - 1) for s in CASAS}

PST = {
    "P": [0, 0, 0, 0, 0, 0, 0, 0, 50, 50, 50, 50, 50, 50, 50, 50, 10, 10, 20, 30, 30, 20, 10, 10,
          5, 5, 10, 25, 25, 10, 5, 5, 0, 0, 0, 20, 20, 0, 0, 0, 5, -5, -10, 0, 0, -10, -5, 5,
          5, 10, 10, -20, -20, 10, 10, 5, 0, 0, 0, 0, 0, 0, 0, 0],
    "N": [-50, -40, -30, -30, -30, -30, -40, -50, -40, -20, 0, 0, 0, 0, -20, -40,
          -30, 0, 10, 15, 15, 10, 0, -30, -30, 5, 15, 20, 20, 15, 5, -30,
          -30, 0, 15, 20, 20, 15, 0, -30, -30, 5, 10, 15, 15, 10, 5, -30,
          -40, -20, 0, 5, 5, 0, -20, -40, -50, -40, -30, -30, -30, -30, -40, -50],
    "B": [-20, -10, -10, -10, -10, -10, -10, -20, -10, 0, 0, 0, 0, 0, 0, -10,
          -10, 0, 5, 10, 10, 5, 0, -10, -10, 5, 5, 10, 10, 5, 5, -10,
          -10, 0, 10, 10, 10, 10, 0, -10, -10, 10, 10, 10, 10, 10, 10, -10,
          -10, 5, 0, 0, 0, 0, 5, -10, -20, -10, -10, -10, -10, -10, -10, -20],
    "R": [0] * 8 + [5, 10, 10, 10, 10, 10, 10, 5] + ([-5] + [0] * 6 + [-5]) * 5
         + [0, 0, 0, 5, 5, 0, 0, 0],
    "Q": [(5 if 2 <= r <= 5 and 2 <= c <= 5 else -10 if r in (0, 7) or c in (0, 7) else 0)
          for r in range(8) for c in range(8)],
    "K": [-30, -40, -40, -50, -50, -40, -40, -30] * 4
         + [-20, -30, -30, -40, -40, -30, -30, -20, -10, -20, -20, -20, -20, -20, -20, -10,
            20, 20, 0, 0, 0, 0, 20, 20, 20, 30, 10, 0, 0, 10, 30, 20],
}


class Pos:
    __slots__ = ("b", "lado", "roque", "ep", "meio", "rei")

    def __init__(self, b, lado, roque, ep, meio, rei):
        self.b, self.lado, self.roque, self.ep, self.meio, self.rei = b, lado, roque, ep, meio, rei

    def chave(self):
        return "".join(self.b[21:99]) + str(self.lado) + self.roque + str(self.ep)


def pos_inicial():
    b = [FORA] * 120
    linhas = ["rnbqkbnr", "pppppppp", "........", "........",
              "........", "........", "PPPPPPPP", "RNBQKBNR"]
    for r in range(8):
        for c in range(8):
            b[21 + r * 10 + c] = linhas[r][c]
    return Pos(b, 0, "KQkq", -1, 0, [95, 25])


def atacado(b, s, por_branco):
    if por_branco:
        if b[s + 9] == "P" or b[s + 11] == "P":
            return True
        n, k, bq, rq = "N", "K", "BQ", "RQ"
    else:
        if b[s - 9] == "p" or b[s - 11] == "p":
            return True
        n, k, bq, rq = "n", "k", "bq", "rq"
    for d in DN:
        if b[s + d] == n:
            return True
    for d in DK:
        if b[s + d] == k:
            return True
    for d in DB:
        t = s + d
        while b[t] == VAZIO:
            t += d
        if b[t] in bq and b[t] != FORA:
            return True
    for d in DR:
        t = s + d
        while b[t] == VAZIO:
            t += d
        if b[t] in rq and b[t] != FORA:
            return True
    return False


def em_xeque(pos):
    return atacado(pos.b, pos.rei[pos.lado], pos.lado == 1)


def gerar(pos, so_capturas=False):
    """Lances pseudo-legais."""
    b = pos.b
    branco = pos.lado == 0
    inimigo = str.islower if branco else str.isupper
    ms = []
    for s in CASAS:
        p = b[s]
        if p == VAZIO or p.isupper() != branco:
            continue
        u = p.upper()
        if u == "P":
            d = -10 if branco else 10
            t = s + d
            promo = (21 <= t <= 28) if branco else (91 <= t <= 98)
            if b[t] == VAZIO and (promo or not so_capturas):
                ms.append((s, t, 3 if promo else 0))
                inicio = (81 <= s <= 88) if branco else (31 <= s <= 38)
                if inicio and b[t + d] == VAZIO and not so_capturas:
                    ms.append((s, t + d, 4))
            for t in (s + d - 1, s + d + 1):
                if inimigo(b[t]):
                    ms.append((s, t, 3 if promo else 0))
                elif t == pos.ep:
                    ms.append((s, t, 1))
        elif u == "N" or u == "K":
            for d in (DN if u == "N" else DK):
                q = b[s + d]
                if (q == VAZIO and not so_capturas) or inimigo(q):
                    ms.append((s, s + d, 0))
        else:
            dirs = DB if u == "B" else DR if u == "R" else DK
            for d in dirs:
                t = s + d
                while b[t] == VAZIO:
                    if not so_capturas:
                        ms.append((s, t, 0))
                    t += d
                if inimigo(b[t]):
                    ms.append((s, t, 0))
    if not so_capturas and pos.roque:
        r = pos.roque
        if branco and b[95] == "K":
            if "K" in r and b[96] == b[97] == VAZIO and b[98] == "R" and \
                    not any(atacado(b, x, False) for x in (95, 96, 97)):
                ms.append((95, 97, 2))
            if "Q" in r and b[94] == b[93] == b[92] == VAZIO and b[91] == "R" and \
                    not any(atacado(b, x, False) for x in (95, 94, 93)):
                ms.append((95, 93, 2))
        elif not branco and b[25] == "k":
            if "k" in r and b[26] == b[27] == VAZIO and b[28] == "r" and \
                    not any(atacado(b, x, True) for x in (25, 26, 27)):
                ms.append((25, 27, 2))
            if "q" in r and b[24] == b[23] == b[22] == VAZIO and b[21] == "r" and \
                    not any(atacado(b, x, True) for x in (25, 24, 23)):
                ms.append((25, 23, 2))
    return ms


def fazer(pos, m):
    s, t, f = m
    b = pos.b[:]
    p = b[s]
    cap = b[t]
    branco = pos.lado == 0
    b[t] = p
    b[s] = VAZIO
    if f == 1:
        b[t + 10 if branco else t - 10] = VAZIO
        cap = "p"
    elif f == 2:
        ori, dst = {97: (98, 96), 93: (91, 94), 27: (28, 26), 23: (21, 24)}[t]
        b[dst] = b[ori]
        b[ori] = VAZIO
    elif f == 3:
        b[t] = "Q" if branco else "q"
    roque = pos.roque
    if roque:
        for x in (s, t):
            tira = MASCARA_ROQUE.get(x)
            if tira:
                roque = "".join(ch for ch in roque if ch not in tira)
    rei = pos.rei
    if p == "K" or p == "k":
        rei = rei[:]
        rei[pos.lado] = t
    meio = 0 if (p == "P" or p == "p" or cap != VAZIO) else pos.meio + 1
    return Pos(b, 1 - pos.lado, roque, (s + t) // 2 if f == 4 else -1, meio, rei)


def legais(pos):
    res = []
    for m in gerar(pos):
        n = fazer(pos, m)
        if not atacado(n.b, n.rei[pos.lado], pos.lado == 1):
            res.append((m, n))
    return res


def material_insuficiente(b):
    outras = [p for p in b[21:99] if p not in (VAZIO, FORA, "K", "k")]
    return not outras or (len(outras) == 1 and outras[0] in "NBnb")


def avaliar(pos, posicional):
    b = pos.b
    s = 0
    for q in CASAS:
        p = b[q]
        if p == VAZIO:
            continue
        u = p.upper()
        if p == u:
            s += VAL[u] + (PST[u][I64[q]] if posicional else 0)
        else:
            s -= VAL[u] + (PST[u][I64[q] ^ 56] if posicional else 0)
    return s if pos.lado == 0 else -s


def _chave_ordem(b, m):
    alvo = b[m[1]]
    v = 0
    if alvo != VAZIO:
        v = VAL[alvo.upper()] * 10 - VAL[b[m[0]].upper()] // 10 + 1000
    if m[2] == 3:
        v += 8000
    elif m[2] == 1:
        v += 1000
    return -v


class _Tempo(Exception):
    pass


class Busca:
    def __init__(self, posicional, quiesc, limite):
        self.posicional = posicional
        self.quiesc = quiesc
        self.fim = time.perf_counter() + limite if limite else None
        self.nos = 0
        self.checar = False

    def _tique(self):
        self.nos += 1
        if self.checar and self.nos & 255 == 0 and time.perf_counter() > self.fim:
            raise _Tempo

    def quiesce(self, pos, a, b, prof):
        self._tique()
        parado = avaliar(pos, self.posicional)
        if parado >= b or prof >= 5:
            return parado
        if parado > a:
            a = parado
        ms = gerar(pos, True)
        ms.sort(key=lambda m: _chave_ordem(pos.b, m))
        for m in ms:
            n = fazer(pos, m)
            if atacado(n.b, n.rei[pos.lado], pos.lado == 1):
                continue
            v = -self.quiesce(n, -b, -a, prof + 1)
            if v >= b:
                return v
            if v > a:
                a = v
        return a

    def negamax(self, pos, prof, a, b, ply):
        self._tique()
        if pos.meio >= 100:
            return 0
        if prof <= 0:
            return self.quiesce(pos, a, b, 0) if self.quiesc else avaliar(pos, self.posicional)
        ms = gerar(pos)
        ms.sort(key=lambda m: _chave_ordem(pos.b, m))
        melhor = -INF
        for m in ms:
            n = fazer(pos, m)
            if atacado(n.b, n.rei[pos.lado], pos.lado == 1):
                continue
            v = -self.negamax(n, prof - 1, -b, -a, ply + 1)
            if v > melhor:
                melhor = v
            if v > a:
                a = v
            if a >= b:
                break
        if melhor == -INF:
            return -MATE + ply if em_xeque(pos) else 0
        return melhor

    def raiz(self, lista, prof):
        a = -INF
        melhor = lista[0][0]
        for m, n in lista:
            v = -self.negamax(n, prof - 1, -INF, -a, 1)
            if v > a:
                a, melhor = v, m
        return melhor, a


def bot_xadrez(pos, dif, limite=1.5):
    lista = legais(pos)
    if not lista:
        return None
    random.shuffle(lista)
    if dif == 0:
        caps = [x for x in lista if pos.b[x[0][1]] != VAZIO or x[0][2] in (1, 3)]
        if caps and random.random() < 0.7:
            return random.choice(caps)[0]
        return random.choice(lista)[0]
    lista.sort(key=lambda x: _chave_ordem(pos.b, x[0]))
    if dif == 1:
        return Busca(False, False, None).raiz(lista, 2)[0]
    busca = Busca(True, True, limite)
    melhor = lista[0][0]
    for prof in range(1, 5):
        busca.checar = prof > 1
        try:
            melhor, valor = busca.raiz(lista, prof)
        except _Tempo:
            break
        if valor >= MATE - 50:
            break
        lista.sort(key=lambda x: x[0] != melhor)
    return melhor


# ============================================================
# PEÇAS (OVINHOS COM CHAPÉU) — sprites em cache
# ============================================================

_sprites = {}


_NOMES_IMG = {"P": "peao", "N": "cavalo", "B": "bispo", "R": "torre", "Q": "rainha", "K": "rei"}
_imgs = {}


def _imagem_peca(tipo, branco):
    """Imagem desenhada em Img/xadregg (None se faltar). Maiúscula = brancas."""
    chave = (tipo, branco)
    if chave not in _imgs:
        import os
        from settings import caminho
        nome = _NOMES_IMG.get(tipo)
        img = None
        sufixos = ("branco", "branca") if branco else ("preto", "preta")
        for suf in sufixos if nome else ():
            arq = caminho("Img", "xadregg", f"{nome}_{suf}.png")
            if os.path.exists(arq):
                try:
                    img = pygame.image.load(arq).convert_alpha()
                except pygame.error:
                    img = pygame.image.load(arq)
                break
        _imgs[chave] = img
    return _imgs[chave]


def sprite_peca(tipo, cor, lado):
    """tipo maiúsculo = peça branca (jogador 1), minúsculo = preta (jogador 2/IA)."""
    branco = tipo.isupper()
    tipo = tipo.upper()
    chave = (tipo, branco, cor, lado)
    sup = _sprites.get(chave)
    if sup is not None:
        return sup
    img = _imagem_peca(tipo, branco)
    if img is not None:
        w, h = img.get_size()
        k = lado / max(w, h)
        esc = pygame.transform.smoothscale(img, (max(1, round(w * k)), max(1, round(h * k))))
        sup = pygame.Surface((lado, lado), pygame.SRCALPHA)
        sup.blit(esc, ((lado - esc.get_width()) // 2, lado - esc.get_height()))
        _sprites[chave] = sup
        return sup
    S = lado
    sup = pygame.Surface((S, S), pygame.SRCALPHA)
    escuro = ui.escurecer(cor, 90)
    ouro, ouro_esc = (255, 205, 60), (170, 120, 20)
    peao = tipo == "P"
    w, h = (S * 0.46, S * 0.52) if peao else (S * 0.56, S * 0.62)
    corpo = pygame.Rect(0, 0, int(w), int(h))
    corpo.midbottom = (S // 2, S - 3)
    topo = corpo.y
    cx = S // 2

    pygame.draw.ellipse(sup, (0, 0, 0, 70), (corpo.x + 2, S - 9, corpo.w - 4, 8))
    if tipo == "N":                           # crina atrás do corpo
        for k in range(5):
            pygame.draw.circle(sup, (120, 70, 40), (corpo.x + 4 + k * 2, topo + 6 + k * 7), S // 11)
    pygame.draw.ellipse(sup, escuro, corpo.inflate(4, 4))
    pygame.draw.ellipse(sup, cor, corpo)
    pygame.draw.ellipse(sup, ui.clarear(cor, 70),
                        (corpo.x + corpo.w * 0.2, corpo.y + corpo.h * 0.15, corpo.w * 0.22,
                         corpo.h * 0.28))
    # carinha
    oy = corpo.y + corpo.h * 0.48
    for dx in (-0.16, 0.16):
        pygame.draw.circle(sup, (20, 20, 30), (int(cx + corpo.w * dx), int(oy)), max(2, S // 22))
    pygame.draw.arc(sup, (20, 20, 30), (cx - S * 0.07, oy + S * 0.02, S * 0.14, S * 0.08),
                    math.pi, 2 * math.pi, 2)

    if tipo == "K":
        pts = [(cx - S * 0.2, topo + 4), (cx - S * 0.22, topo - S * 0.13), (cx - S * 0.1, topo - S * 0.04),
               (cx, topo - S * 0.17), (cx + S * 0.1, topo - S * 0.04), (cx + S * 0.22, topo - S * 0.13),
               (cx + S * 0.2, topo + 4)]
        pygame.draw.polygon(sup, ouro, pts)
        pygame.draw.polygon(sup, ouro_esc, pts, 2)
        pygame.draw.line(sup, ouro_esc, (cx, topo - S * 0.17), (cx, topo - S * 0.3), 4)
        pygame.draw.line(sup, ouro_esc, (cx - S * 0.06, topo - S * 0.25), (cx + S * 0.06, topo - S * 0.25), 4)
        pygame.draw.circle(sup, (230, 60, 80), (cx, int(topo - S * 0.02)), max(2, S // 18))
    elif tipo == "Q":
        arco = pygame.Rect(0, 0, int(S * 0.44), int(S * 0.2))
        arco.midtop = (cx, int(topo - S * 0.06))
        pygame.draw.arc(sup, ouro, arco, 0, math.pi, 5)
        for k, dx in enumerate((-0.14, 0, 0.14)):
            y = topo - S * (0.11 if k == 1 else 0.06)
            pygame.draw.circle(sup, (120, 200, 255) if k == 1 else (240, 90, 160),
                               (int(cx + S * dx), int(y)), max(3, S // 14))
            pygame.draw.circle(sup, ouro_esc, (int(cx + S * dx), int(y)), max(3, S // 14), 1)
    elif tipo == "R":
        torre = pygame.Rect(0, 0, int(S * 0.4), int(S * 0.14))
        torre.midbottom = (cx, topo + 6)
        pedra, pedra_esc = (170, 170, 185), (90, 90, 110)
        pygame.draw.rect(sup, pedra, torre)
        pygame.draw.rect(sup, pedra_esc, torre, 2)
        dente = torre.w // 5
        for k in (0, 2, 4):
            r = pygame.Rect(torre.x + k * dente, torre.y - S * 0.09, dente, S * 0.1)
            pygame.draw.rect(sup, pedra, r)
            pygame.draw.rect(sup, pedra_esc, r, 2)
    elif tipo == "B":
        pts = [(cx - S * 0.15, topo + 6), (cx, topo - S * 0.26), (cx + S * 0.15, topo + 6)]
        pygame.draw.polygon(sup, (245, 240, 255), pts)
        pygame.draw.polygon(sup, (110, 90, 160), pts, 2)
        pygame.draw.line(sup, (110, 90, 160), (cx + S * 0.03, topo - S * 0.16), (cx - S * 0.06, topo - S * 0.02), 3)
        pygame.draw.line(sup, ouro, (cx, topo - S * 0.04), (cx, topo + 4), 3)
        pygame.draw.circle(sup, ouro, (cx, int(topo - S * 0.27)), max(2, S // 20))
    elif tipo == "N":
        for dx in (-0.12, 0.12):                    # orelhinhas
            base = cx + S * dx
            pts = [(base - S * 0.06, topo + 8), (base, topo - S * 0.12), (base + S * 0.06, topo + 8)]
            pygame.draw.polygon(sup, cor, pts)
            pygame.draw.polygon(sup, escuro, pts, 2)
        focinho = pygame.Rect(0, 0, int(S * 0.22), int(S * 0.14))
        focinho.midleft = (int(cx + corpo.w * 0.18), int(oy + S * 0.08))
        pygame.draw.ellipse(sup, ui.clarear(cor, 30), focinho)
        pygame.draw.ellipse(sup, escuro, focinho, 2)
        pygame.draw.circle(sup, (20, 20, 30), (focinho.right - 6, focinho.centery), 2)
    elif tipo == "P":
        pygame.draw.line(sup, (60, 150, 60), (cx, topo + 2), (cx, topo - S * 0.08), 3)
        pygame.draw.ellipse(sup, (90, 200, 90), (cx, topo - S * 0.12, S * 0.12, S * 0.07))
    _sprites[chave] = sup
    return sup


# ============================================================
# JOGO
# ============================================================

CEL = 72
TAB = pygame.Rect(0, 0, CEL * 8, CEL * 8)
TAB.midtop = (LARGURA // 2, 118)
CLARA, ESCURA = (250, 232, 200), (196, 140, 96)
TEMPO_ANIM = 0.2
NOMES_PECA = {"P": "PEÃO", "N": "CAVALO", "B": "BISPO", "R": "TORRE", "Q": "RAINHA", "K": "REI"}


def casa_xy(s):
    return TAB.x + (s % 10 - 1) * CEL, TAB.y + (s // 10 - 2) * CEL


class Xadegg(JogoTabuleiro):

    ID = "xadegg"
    TITULO = "XADEGG"
    DESCRICAO = "Xadrez de ovinhos! Rei de coroa, rainha de tiara, torre, bispo e cavalo de crina."
    COR = (150, 100, 60)
    INSTRUCOES = [
        "Xadrez com regras completas: roque, en passant, promoção (vira rainha).",
        "Dê XEQUE-MATE no rei rival! Afogamento é empate.",
        "MOUSE: clique na peça e no destino  •  TECLADO: SETAS + ENTER",
    ]
    TEMPO_MINIMO = 30.0
    ESPERA_FIM = 1.8

    @classmethod
    def criar_fundo(cls, jogador):
        sup = fundo_mesa((110, 76, 50), (60, 40, 26), (125, 88, 60), 88)
        moldura = TAB.inflate(36, 36)
        pygame.draw.rect(sup, (30, 18, 10), moldura.move(0, 8), border_radius=14)
        pygame.draw.rect(sup, (120, 76, 40), moldura, border_radius=14)
        pygame.draw.rect(sup, (80, 50, 26), moldura, 4, border_radius=14)
        for r in range(8):
            for c in range(8):
                cor = CLARA if (r + c) % 2 == 0 else ESCURA
                pygame.draw.rect(sup, cor, (TAB.x + c * CEL, TAB.y + r * CEL, CEL, CEL))
        for k in range(8):
            ui.desenhar_texto(sup, tr("abcdefgh")[k].upper(), (TAB.x + k * CEL + CEL // 2, TAB.bottom + 3),
                              8, (240, 220, 190), "midtop", False)
            ui.desenhar_texto(sup, str(8 - k), (TAB.x - 9, TAB.y + k * CEL + CEL // 2), 8,
                              (240, 220, 190), "center", False)
        return sup

    @classmethod
    def desenhar_icone(cls, sup, jogador):
        w, h = sup.get_size()
        c = h // 6
        for r in range(6):
            for k in range(w // c + 1):
                pygame.draw.rect(sup, CLARA if (r + k) % 2 == 0 else ESCURA, (k * c, r * c, c, c))
        cor = jogador.cor_do_ovo(jogador.ovo)
        t = int(h * 0.5)
        sup.blit(sprite_peca("K", cor, t), (w // 2 - t - 4, h // 2 - t // 2))
        sup.blit(sprite_peca("n", (60, 60, 70), t), (w // 2 + 4, h // 2 - t // 2))

    # --------------------------------------------------------

    def reiniciar(self):
        self.pos = pos_inicial()
        self.lista = legais(self.pos)
        self.repeticoes = {self.pos.chave(): 1}
        self.sel = None
        self.cursor = 85            # e2
        self.ultimo = None
        self.anim = None
        self.capturadas = [[], []]  # peças que cada jogador comeu
        self.aviso = ""
        self.n_lances = 0
        self._reset_turnos(0)

    def ocupado(self):
        return self.anim is not None

    def jogadas_validas(self):
        return [m for m, _ in self.lista]

    def destinos(self, s):
        return [m for m, _ in self.lista if m[0] == s]

    def jogar(self, m):
        par = next((x for x in self.lista if x[0] == m), None)
        if par is None:
            return
        antes = self.pos
        s, t, f = m
        alvo = antes.b[t] if f != 1 else ("p" if antes.lado == 0 else "P")
        if alvo != VAZIO:
            self.capturadas[antes.lado].append(alvo.upper())
        self.anim = (antes.b[s], s, t, 0.0)
        self.pos = par[1]
        self.ultimo = (s, t)
        self.n_lances += 1
        self.sel = None
        ch = self.pos.chave()
        self.repeticoes[ch] = self.repeticoes.get(ch, 0) + 1
        self.lista = legais(self.pos)
        self.vez = self.pos.lado
        self.som("bater" if alvo != VAZIO else "clique")
        self.aviso = ""

        cheque = em_xeque(self.pos)
        if not self.lista:
            if cheque:
                self.aviso = "XEQUE-MATE!"
                self.finalizar(antes.lado, [tr("XEQUE-MATE!"), tr("LANCES: {n}", n=(self.n_lances + 1) // 2)])
            else:
                self.aviso = "AFOGADO!"
                self.finalizar(None, [tr("AFOGAMENTO: EMPATE")])
        elif self.pos.meio >= 100:
            self.finalizar(None, [tr("50 LANCES SEM CAPTURA")])
        elif material_insuficiente(self.pos.b):
            self.finalizar(None, [tr("MATERIAL INSUFICIENTE")])
        elif self.repeticoes[ch] >= 3:
            self.finalizar(None, [tr("REPETIÇÃO TRIPLA")])
        elif cheque:
            self.aviso = "XEQUE!"
            self.som("erro", 0.5)
        if f == 3:
            self.textos.adicionar(tr("PROMOÇÃO: RAINHA!"), (casa_xy(t)[0] + CEL // 2, casa_xy(t)[1]),
                                  AMARELO, 12)

    # BOT -----------------------------------------------------

    def foto_bot(self):
        return self.pos, self.dificuldade

    def pensar_bot(self, foto):
        return bot_xadrez(foto[0], foto[1])

    def aplicar_bot(self, m):
        if m is not None:
            self.jogar(m)

    # LOOP ----------------------------------------------------

    def _casa_em(self, pos):
        if not TAB.collidepoint(pos):
            return None
        return 21 + (pos[1] - TAB.y) // CEL * 10 + (pos[0] - TAB.x) // CEL

    def _clicar(self, s):
        self.cursor = s
        if self.sel is not None:
            m = next((m for m in self.destinos(self.sel) if m[1] == s), None)
            if m is not None:
                self.jogar(m)
                return
        p = self.pos.b[s]
        if p != VAZIO and p.isupper() == (self.pos.lado == 0) and self.destinos(s):
            self.sel = s
            self.som("selecionar", 0.4)
        else:
            self.sel = None

    def evento_jogo(self, e):
        if not self.humano_pode():
            return
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            s = self._casa_em(e.pos)
            if s is not None:
                self._clicar(s)
        elif e.type == pygame.KEYDOWN:
            if e.key in TECLAS_DIR:
                dx, dy = TECLAS_DIR[e.key]
                c = (self.cursor % 10 - 1 + dx) % 8
                r = (self.cursor // 10 - 2 + dy) % 8
                self.cursor = 21 + r * 10 + c
            elif e.key in TECLAS_OK:
                self._clicar(self.cursor)

    def atualizar_jogo(self, dt):
        if self.anim is not None:
            p, s, t, k = self.anim
            k += dt / TEMPO_ANIM
            self.anim = None if k >= 1 else (p, s, t, k)
            return
        self.atualizar_turnos(dt)

    # DESENHO -------------------------------------------------

    def desenhar_jogo(self, tela):
        tela.blit(self.fundo(self.jogador), (0, 0))
        if self.estado == "inicio":
            return
        cores = (self.cor(0), self.cor(1))
        if self.ultimo:
            for s in self.ultimo:
                x, y = casa_xy(s)
                pygame.draw.rect(tela, (240, 220, 90), (x, y, CEL, CEL))
        if em_xeque(self.pos):
            x, y = casa_xy(self.pos.rei[self.pos.lado])
            pygame.draw.rect(tela, (240, 90, 90), (x, y, CEL, CEL))
        if self.sel is not None:
            x, y = casa_xy(self.sel)
            pygame.draw.rect(tela, (120, 200, 120), (x, y, CEL, CEL))

        movendo = self.anim[2] if self.anim else None
        b = self.pos.b
        for s in CASAS:
            p = b[s]
            if p == VAZIO or s == movendo:
                continue
            x, y = casa_xy(s)
            tela.blit(sprite_peca(p, cores[0 if p.isupper() else 1], CEL), (x, y - 4))

        if self.sel is not None:
            for m in self.destinos(self.sel):
                x, y = casa_xy(m[1])
                c = (x + CEL // 2, y + CEL // 2)
                if b[m[1]] != VAZIO:
                    pygame.draw.circle(tela, (40, 140, 60), c, CEL // 2 - 3, 4)
                else:
                    pygame.draw.circle(tela, (40, 140, 60), c, 9)
        if self.humano_pode():
            x, y = casa_xy(self.cursor)
            pygame.draw.rect(tela, CORES_JOGADOR[self.vez], (x, y, CEL, CEL), 4, border_radius=6)

        if self.anim:
            p, s, t, k = self.anim
            k = 1 - (1 - k) ** 2
            (x1, y1), (x2, y2) = casa_xy(s), casa_xy(t)
            x, y = x1 + (x2 - x1) * k, y1 + (y2 - y1) * k - math.sin(k * math.pi) * 16
            final = b[t]
            tela.blit(sprite_peca(final, cores[0 if final.isupper() else 1], CEL), (x, y - 4))
        self.textos.desenhar(tela)

    def desenhar_hud(self, tela):
        for i in (0, 1):
            r = pygame.Rect(12 if i == 0 else TAB.right + 22, TAB.y, TAB.x - 34, 300)
            if i == 0:
                r.bottom = TAB.bottom
            ativo = self.vez == i and self._fim is None
            ui.painel(tela, r, (20, 24, 40), AMARELO if ativo else CORES_JOGADOR[i], 12,
                      4 if ativo else 2, sombra=False)
            self.desenhar_ovo(tela, i, (r.centerx, r.y + 46), 56)
            ui.desenhar_texto(tela, self.nome(i)[:12], (r.centerx, r.y + 84), 10,
                              CORES_JOGADOR[i], "midtop")
            ui.desenhar_texto(tela, tr("BRANCAS") if i == 0 else tr("PRETAS"), (r.centerx, r.y + 102), 8,
                              BRANCO, "midtop")
            if ativo:
                ui.desenhar_texto(tela, self.texto_vez(), (r.centerx, r.y + 120), 10, AMARELO,
                                  "midtop")
            comidas = sorted(self.capturadas[i], key=lambda p: -VAL[p])
            for k, p in enumerate(comidas[:15]):
                x = r.x + 10 + (k % 5) * 32
                y = r.y + 146 + (k // 5) * 40
                tela.blit(sprite_peca(p if i == 1 else p.lower(), self.cor(1 - i), 34), (x, y))
        if self.aviso and (self.aviso != "XEQUE!" or int(self.tempo * 3) % 2 == 0):
            ui.desenhar_texto(tela, tr(self.aviso), (LARGURA // 2, 70), 22, (255, 110, 110), "center")
        elif self._fim is None:
            ui.desenhar_texto(tela, tr("LANCE {n}", n=self.n_lances // 2 + 1), (LARGURA // 2, 70), 10,
                              (240, 220, 190), "center")
