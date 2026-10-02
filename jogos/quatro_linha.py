import random
import time

import pygame

from settings import *
from core import ui
from jogos.base_multi import CORES_JOGADOR
from jogos.jogo_velha import JogoTabuleiro, TECLAS_OK, fundo_mesa

# ============================================================
# 4 EM LINHA (CONNECT FOUR 7 × 6)
# ============================================================
# As fichas são os ovinhos dos jogadores: caem pela coluna com
# gravidade e quicadinha. Bot: FÁCIL aleatório (às vezes ganha/
# bloqueia o óbvio), MÉDIO minimax 4, DIFÍCIL alfa-beta até 7
# (aprofundamento iterativo com limite de tempo) com ordenação
# pelo centro.

COLS, LINS = 7, 6
CEL = 80
TAB = pygame.Rect(0, 0, COLS * CEL, LINS * CEL)
TAB.midtop = (LARGURA // 2, 170)
RAIO_FURO = 33
ORDEM = [3, 2, 4, 1, 5, 0, 6]
COR_TAB = (40, 90, 200)
GRAV = 2600
LIMITE_BOT = 1.5
GANHA = 1_000_000


def _janelas():
    js = []
    for r in range(LINS):
        for c in range(COLS):
            for dr, dc in ((0, 1), (1, 0), (1, 1), (-1, 1)):
                cel = [(r + dr * k, c + dc * k) for k in range(4)]
                if all(0 <= rr < LINS and 0 <= cc < COLS for rr, cc in cel):
                    js.append(tuple(rr * COLS + cc for rr, cc in cel))
    return js


JANELAS = _janelas()
JANELAS_DA_CASA = [[j for j in JANELAS if k in j] for k in range(COLS * LINS)]


def ganhou(g, k, p):
    """A peça p em k fechou 4?"""
    for j in JANELAS_DA_CASA[k]:
        if g[j[0]] == p and g[j[1]] == p and g[j[2]] == p and g[j[3]] == p:
            return j
    return None


def avaliar(g, p):
    o = 1 - p
    s = 0
    for r in range(LINS):
        v = g[r * COLS + 3]
        if v == p:
            s += 4
        elif v == o:
            s -= 4
    for j in JANELAS:
        a = b = 0
        for k in j:
            v = g[k]
            if v == p:
                a += 1
            elif v == o:
                b += 1
        if b == 0:
            if a == 3:
                s += 12
            elif a == 2:
                s += 3
        elif a == 0:
            if b == 3:
                s -= 14
            elif b == 2:
                s -= 3
    return s


class _Tempo(Exception):
    pass


class _Busca:
    def __init__(self, limite):
        self.fim = time.perf_counter() + limite if limite else None
        self.nos = 0

    def negamax(self, g, alt, p, prof, a, b):
        self.nos += 1
        if self.fim and self.nos & 511 == 0 and time.perf_counter() > self.fim:
            raise _Tempo
        livres = [c for c in ORDEM if alt[c] < LINS]
        if not livres:
            return 0
        # Ganha já?
        for c in livres:
            k = alt[c] * COLS + c
            g[k] = p
            w = ganhou(g, k, p)
            g[k] = None
            if w:
                return GANHA + prof
        if prof == 0:
            return avaliar(g, p)
        melhor = -GANHA * 2
        for c in livres:
            k = alt[c] * COLS + c
            g[k] = p
            alt[c] += 1
            v = -self.negamax(g, alt, 1 - p, prof - 1, -b, -a)
            alt[c] -= 1
            g[k] = None
            if v > melhor:
                melhor = v
            if v > a:
                a = v
            if a >= b:
                break
        return melhor

    def raiz(self, g, alt, p, prof, ordem):
        a, melhor_c = -GANHA * 3, ordem[0]
        for c in ordem:
            k = alt[c] * COLS + c
            g[k] = p
            alt[c] += 1
            v = GANHA + prof + 1 if ganhou(g, k, p) else \
                -self.negamax(g, alt, 1 - p, prof - 1, -GANHA * 3, -a)
            alt[c] -= 1
            g[k] = None
            if v > a:
                a, melhor_c = v, c
        return melhor_c


class QuatroEmLinha(JogoTabuleiro):

    ID = "quatro_linha"
    TITULO = "4 EM LINHA"
    DESCRICAO = "Solte seus ovinhos na coluna e faça 4 em linha antes do rival!"
    COR = (40, 90, 200)
    INSTRUCOES = [
        "Solte um ovinho por vez: ele cai até o fundo da coluna.",
        "Faça 4 EM LINHA: deitado, em pé ou na diagonal!",
        "MOUSE: clique na coluna  •  TECLADO: ← → + ENTER",
    ]
    _tampa = None

    @classmethod
    def tampa(cls):
        """Tabuleiro azul com furos (colorkey), desenhado uma vez."""
        if cls._tampa is None:
            sup = pygame.Surface((TAB.w + 24, TAB.h + 24))
            chave = (255, 0, 255)
            sup.fill(chave)
            pygame.draw.rect(sup, COR_TAB, sup.get_rect(), border_radius=18)
            pygame.draw.rect(sup, ui.escurecer(COR_TAB, 30), sup.get_rect(), 5, border_radius=18)
            for r in range(LINS):
                for c in range(COLS):
                    cx, cy = 12 + c * CEL + CEL // 2, 12 + r * CEL + CEL // 2
                    pygame.draw.circle(sup, ui.escurecer(COR_TAB, 40), (cx, cy + 2), RAIO_FURO + 3)
                    pygame.draw.circle(sup, chave, (cx, cy), RAIO_FURO)
            sup.set_colorkey(chave)
            cls._tampa = sup.convert() if pygame.display.get_surface() else sup
            cls._tampa.set_colorkey(chave)
        return cls._tampa

    @classmethod
    def criar_fundo(cls, jogador):
        sup = fundo_mesa((120, 180, 240), (60, 110, 190), (140, 195, 245), 44)
        pygame.draw.rect(sup, (20, 30, 60), TAB.inflate(24, 24), border_radius=18)
        pygame.draw.rect(sup, (30, 50, 100), (TAB.x - 40, TAB.bottom + 4, TAB.w + 80, 24),
                         border_radius=10)
        return sup

    @classmethod
    def desenhar_icone(cls, sup, jogador):
        w, h = sup.get_size()
        c = min(w // 8, h // 6)
        x0, y0 = w // 2 - c * 7 // 2, h - c * 5 - 4
        pygame.draw.rect(sup, COR_TAB, (x0, y0, c * 7, c * 5), border_radius=6)
        rnd = random.Random(4)
        for r in range(5):
            for k in range(7):
                cor = (20, 30, 60)
                if r >= 2 and rnd.random() < 0.6:
                    cor = rnd.choice([(240, 90, 90), (250, 220, 80)])
                pygame.draw.circle(sup, cor, (x0 + k * c + c // 2, y0 + r * c + c // 2), c // 2 - 2)
        jogador.desenhar(sup, (w // 2, y0 - c * 0.6), c * 1.2)

    # --------------------------------------------------------

    def reiniciar(self):
        self.g = [None] * (COLS * LINS)      # linha 0 = fundo
        self.alt = [0] * COLS
        self.coluna = 3
        self.queda = None
        self.vitoria = None
        self._reset_turnos(0)

    def ocupado(self):
        return self.queda is not None

    def jogadas_validas(self):
        return [c for c in range(COLS) if self.alt[c] < LINS]

    def _y_linha(self, r):
        return TAB.y + (LINS - 1 - r) * CEL + CEL // 2

    def jogar(self, c):
        if self.alt[c] >= LINS or self.queda is not None:
            return
        self.coluna = c
        r = self.alt[c]
        self.alt[c] += 1           # reserva a casa; a peça entra quando pousar
        self.queda = {"c": c, "r": r, "y": float(TAB.y - 50), "vy": 0.0, "p": self.vez,
                      "quicou": False}
        self.som("pulo", 0.5)

    def _pousar(self):
        q = self.queda
        self.queda = None
        k = q["r"] * COLS + q["c"]
        self.g[k] = q["p"]
        self.som("bater")
        linha = ganhou(self.g, k, q["p"])
        if linha:
            self.vitoria = linha
            x, y = TAB.x + q["c"] * CEL + CEL // 2, self._y_linha(q["r"])
            self.particulas.explodir((x, y), [self.cor(q["p"]), AMARELO, BRANCO], 36, 320, 1.0)
            self.tremer(0.2)
            self.finalizar(q["p"], [f"4 EM LINHA EM {sum(v is not None for v in self.g)} JOGADAS"])
        elif None not in self.g:
            self.finalizar(None, ["TABULEIRO CHEIO!"])
        else:
            self.vez = 1 - self.vez

    # BOT -----------------------------------------------------

    def foto_bot(self):
        return list(self.g), list(self.alt), self.vez, self.dificuldade

    def pensar_bot(self, foto):
        g, alt, p, dif = foto
        livres = [c for c in ORDEM if alt[c] < LINS]

        def ganha_em(quem):
            for c in livres:
                k = alt[c] * COLS + c
                g[k] = quem
                w = ganhou(g, k, quem)
                g[k] = None
                if w:
                    return c
            return None

        if dif == 0:
            if random.random() < 0.5:
                c = ganha_em(p)
                if c is None:
                    c = ganha_em(1 - p)
                if c is not None:
                    return c
            return random.choice(livres)
        if dif == 1:
            ordem = livres[:]
            random.shuffle(ordem)
            return _Busca(None).raiz(g, alt, p, 4, ordem)
        # Difícil: aprofundamento iterativo até 7 com limite de tempo
        busca = _Busca(LIMITE_BOT)
        melhor = _Busca(None).raiz(g, alt, p, 2, livres)
        for prof in range(3, 8):
            ordem = [melhor] + [c for c in livres if c != melhor]
            try:
                melhor = busca.raiz(g, alt, p, prof, ordem)
            except _Tempo:
                break
        return melhor

    def aplicar_bot(self, c):
        self.jogar(c)

    # LOOP ----------------------------------------------------

    def evento_jogo(self, e):
        if e.type == pygame.MOUSEMOTION and TAB.inflate(0, 200).collidepoint(e.pos):
            if not self.vez_do_bot():
                self.coluna = max(0, min(COLS - 1, (e.pos[0] - TAB.x) // CEL))
        if not self.humano_pode():
            return
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if TAB.inflate(0, 200).collidepoint(e.pos):
                self.jogar(max(0, min(COLS - 1, (e.pos[0] - TAB.x) // CEL)))
        elif e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_LEFT, pygame.K_a):
                self.coluna = (self.coluna - 1) % COLS
            elif e.key in (pygame.K_RIGHT, pygame.K_d):
                self.coluna = (self.coluna + 1) % COLS
            elif e.key in TECLAS_OK or e.key in (pygame.K_DOWN, pygame.K_s):
                self.jogar(self.coluna)

    def atualizar_jogo(self, dt):
        q = self.queda
        if q is not None:
            alvo = self._y_linha(q["r"])
            q["vy"] += GRAV * dt
            q["y"] += q["vy"] * dt
            if q["y"] >= alvo:
                q["y"] = alvo
                if not q["quicou"] and q["vy"] > 300:
                    q["vy"] = -q["vy"] * 0.25
                    q["quicou"] = True
                else:
                    self._pousar()
            return
        self.atualizar_turnos(dt)

    # DESENHO -------------------------------------------------

    def desenhar_jogo(self, tela):
        tela.blit(self.fundo(self.jogador), (0, 0))
        if self.estado == "inicio":
            return
        # Ovinho esperando em cima da coluna
        if self._fim is None and self.queda is None:
            x = TAB.x + self.coluna * CEL + CEL // 2
            self.desenhar_ovo(tela, self.vez, (x, TAB.y - 44), 50)
            pygame.draw.polygon(tela, CORES_JOGADOR[self.vez],
                                [(x - 10, TAB.y - 12), (x + 10, TAB.y - 12), (x, TAB.y - 2)])
        for k, p in enumerate(self.g):
            if p is not None:
                r, c = divmod(k, COLS)
                self._ficha(tela, p, TAB.x + c * CEL + CEL // 2, self._y_linha(r))
        if self.queda is not None:
            q = self.queda
            self._ficha(tela, q["p"], TAB.x + q["c"] * CEL + CEL // 2, q["y"])
        tela.blit(self.tampa(), (TAB.x - 12, TAB.y - 12))
        if self.vitoria and int(self.tempo * 6) % 2 == 0:
            for k in self.vitoria:
                r, c = divmod(k, COLS)
                pygame.draw.circle(tela, AMARELO, (TAB.x + c * CEL + CEL // 2, self._y_linha(r)),
                                   RAIO_FURO + 2, 5)
        self.particulas.desenhar(tela)

    def _ficha(self, tela, p, x, y):
        pygame.draw.circle(tela, self.cor(p), (int(x), int(y)), RAIO_FURO)
        self.desenhar_ovo(tela, p, (x, y + 4), 52)

    def desenhar_hud(self, tela):
        super().desenhar_hud(tela)
        caixa = pygame.Rect(LARGURA - 300, 12, 220, 56)
        ui.painel(tela, caixa, (20, 24, 40), BRANCO, 12, 3, sombra=False)
        n = sum(v is not None for v in self.g)
        ui.desenhar_texto(tela, f"JOGADAS: {n}", caixa.center, 12, AMARELO, "center")
