import random

import pygame

from settings import *
from core import ui
from jogos.base_multi import CORES_JOGADOR
from jogos.jogo_velha import JogoTabuleiro, TECLAS_DIR, TECLAS_OK, fundo_mesa

# ============================================================
# PONTINHOS (DOTS AND BOXES 5 × 5)
# ============================================================
# Cada jogada liga dois pontinhos. Quem fecha uma caixa ganha a
# caixa (aparece o ovinho do dono) e JOGA DE NOVO.
# Linhas: horizontais 0..29 (r*5+c, r = 0..5), verticais
# 30..59 (30 + r*6 + c, r = 0..4, c = 0..5).

N = 5
ESP = 92
X0 = LARGURA // 2 - N * ESP // 2
Y0 = 176
N_LINHAS = 2 * N * (N + 1)


def _geometria():
    lados, caixas_da_linha, pontas = [], [[] for _ in range(N_LINHAS)], []
    for r in range(N + 1):
        for c in range(N):
            pontas.append(((X0 + c * ESP, Y0 + r * ESP), (X0 + (c + 1) * ESP, Y0 + r * ESP)))
    for r in range(N):
        for c in range(N + 1):
            pontas.append(((X0 + c * ESP, Y0 + r * ESP), (X0 + c * ESP, Y0 + (r + 1) * ESP)))
    for r in range(N):
        for c in range(N):
            ls = (r * N + c, (r + 1) * N + c, 30 + r * (N + 1) + c, 30 + r * (N + 1) + c + 1)
            lados.append(ls)
            for l in ls:
                caixas_da_linha[l].append(r * N + c)
    meios = [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) for a, b in pontas]
    return lados, caixas_da_linha, pontas, meios


LADOS, CAIXAS_DA_LINHA, PONTAS, MEIOS = _geometria()


def n_lados(feitas, cx):
    return sum(feitas[l] for l in LADOS[cx])


def fecha(feitas, l):
    """Quantas caixas a linha l fecharia."""
    return sum(1 for cx in CAIXAS_DA_LINHA[l] if n_lados(feitas, cx) == 3)


def capturas(feitas):
    return [l for l in range(N_LINHAS) if not feitas[l] and fecha(feitas, l)]


def seguras(feitas):
    return [l for l in range(N_LINHAS) if not feitas[l]
            and all(n_lados(feitas, cx) < 2 for cx in CAIXAS_DA_LINHA[l])]


def entrega(feitas, l):
    """Quantas caixas o rival pega (guloso) se eu jogar l (sem fechar nada)."""
    f = list(feitas)
    f[l] = True
    total = 0
    while True:
        cs = capturas(f)
        if not cs:
            return total
        total += fecha(f, cs[0])
        f[cs[0]] = True


def ponta_dupla(feitas, l):
    """
    l fecha a caixa A e a próxima caixa B da corrente seria a ÚLTIMA
    (corrente de 2). Devolve a linha M (a outra ponta de B) para o
    "sacrifício duplo" (double-dealing), ou None.
    """
    cxs = CAIXAS_DA_LINHA[l]
    if len(cxs) != 2:
        return None
    a, b = cxs
    if n_lados(feitas, a) != 3:
        a, b = b, a
    if n_lados(feitas, a) != 3 or n_lados(feitas, b) != 2:
        return None
    abertas = [m for m in LADOS[b] if not feitas[m] and m != l]
    if len(abertas) != 1:
        return None
    m = abertas[0]
    for c in CAIXAS_DA_LINHA[m]:
        if c != b and n_lados(feitas, c) >= 2:
            return None             # a corrente continua depois de B
    return m


def bot_pontinhos(feitas, dono, dif):
    livres = [l for l in range(N_LINHAS) if not feitas[l]]
    caps = capturas(feitas)
    if dif == 0:
        if caps and random.random() < 0.6:
            return random.choice(caps)
        return random.choice(livres)
    seg = seguras(feitas)
    if dif == 1:
        if caps:
            return random.choice(caps)
        if seg:
            return random.choice(seg)
        return random.choice(livres)

    # DIFÍCIL
    if caps:
        normais = [l for l in caps if ponta_dupla(feitas, l) is None]
        if normais or seg:
            return (normais or caps)[0]
        # Última corrente de 2: se ainda sobra muita caixa depois,
        # entrega as 2 (sacrifício duplo) e fica com o controle
        l = caps[0]
        m = ponta_dupla(feitas, l)
        resto = sum(1 for cx in range(N * N) if dono[cx] is None) - 2
        if m is not None and resto >= 3 and not capturas_exceto(feitas, l):
            return m
        return l
    if seg:
        return random.choice(seg)
    # Sem jogada segura: entrega a menor corrente possível
    return min(livres, key=lambda l: (entrega(feitas, l), random.random()))


def capturas_exceto(feitas, l):
    """Outras capturas além da corrente de l (se houver, pega elas antes)."""
    return [x for x in capturas(feitas) if x != l and not set(CAIXAS_DA_LINHA[x]) &
            set(CAIXAS_DA_LINHA[l])]


class Pontinhos(JogoTabuleiro):

    ID = "pontinhos"
    TITULO = "PONTINHOS"
    DESCRICAO = "Ligue os pontinhos e feche caixinhas. Quem fecha uma caixa joga de novo!"
    COR = (60, 150, 110)
    INSTRUCOES = [
        "Na sua vez, ligue dois pontinhos vizinhos.",
        "Fechou uma caixa? Ela é sua e você JOGA DE NOVO! Quem tiver mais caixas vence.",
        "MOUSE: clique entre dois pontos  •  TECLADO: SETAS + ENTER",
    ]
    @classmethod
    def criar_fundo(cls, jogador):
        sup = fundo_mesa((190, 230, 200), (120, 180, 140), (200, 238, 210), 55)
        folha = pygame.Rect(X0 - 40, Y0 - 40, N * ESP + 80, N * ESP + 80)
        pygame.draw.rect(sup, (80, 120, 90), folha.move(0, 8), border_radius=16)
        pygame.draw.rect(sup, (252, 250, 240), folha, border_radius=16)
        for y in range(folha.y + 20, folha.bottom - 10, 23):
            pygame.draw.line(sup, (215, 230, 245), (folha.x + 12, y), (folha.right - 12, y), 1)
        pygame.draw.line(sup, (245, 180, 180), (folha.x + 26, folha.y + 6),
                         (folha.x + 26, folha.bottom - 6), 2)
        return sup

    @classmethod
    def desenhar_icone(cls, sup, jogador):
        w, h = sup.get_size()
        e = min(w, h) // 5
        x0, y0 = w // 2 - e * 3 // 2, h // 2 - e * 3 // 2 + 4
        pygame.draw.rect(sup, (255, 200, 120), (x0, y0, e, e))
        pygame.draw.lines(sup, (220, 70, 70), False, [(x0, y0 + e), (x0, y0), (x0 + e, y0),
                                                       (x0 + e, y0 + e), (x0, y0 + e)], 4)
        pygame.draw.line(sup, (70, 110, 220), (x0 + e, y0 + e), (x0 + 2 * e, y0 + e), 4)
        pygame.draw.line(sup, (70, 110, 220), (x0 + 2 * e, y0), (x0 + 3 * e, y0), 4)
        for r in range(4):
            for c in range(4):
                pygame.draw.circle(sup, (40, 40, 60), (x0 + c * e, y0 + r * e), 4)
        jogador.desenhar(sup, (x0 + e // 2, y0 + e // 2 + 2), e * 0.75)

    # --------------------------------------------------------

    def reiniciar(self):
        self.feitas = [False] * N_LINHAS
        self.quem_fez = [None] * N_LINHAS
        self.dono = [None] * (N * N)
        self.placar = [0, 0]
        self.cursor = 0
        self.hover = None
        self.ultima = None
        self.t_ultima = 0.0
        self._reset_turnos(0)

    def jogadas_validas(self):
        return [l for l in range(N_LINHAS) if not self.feitas[l]]

    def jogar(self, l):
        if self.feitas[l]:
            return
        self.feitas[l] = True
        self.quem_fez[l] = self.vez
        self.ultima, self.t_ultima = l, self.tempo
        fechou = 0
        for cx in CAIXAS_DA_LINHA[l]:
            if self.dono[cx] is None and n_lados(self.feitas, cx) == 4:
                self.dono[cx] = self.vez
                self.placar[self.vez] += 1
                fechou += 1
                r, c = divmod(cx, N)
                centro = (X0 + c * ESP + ESP // 2, Y0 + r * ESP + ESP // 2)
                self.particulas.explodir(centro, [self.cor(self.vez), AMARELO], 14, 180, 0.6)
        if fechou:
            self.som("ponto")
        else:
            self.som("clique")
            self.vez = 1 - self.vez
        if all(self.feitas):
            v = 0 if self.placar[0] > self.placar[1] else 1 if self.placar[1] > self.placar[0] else None
            self.finalizar(v, [f"CAIXAS  {self.placar[0]} × {self.placar[1]}"])

    # BOT -----------------------------------------------------

    def foto_bot(self):
        return list(self.feitas), list(self.dono), self.dificuldade

    def pensar_bot(self, foto):
        return bot_pontinhos(*foto)

    def aplicar_bot(self, l):
        self.jogar(l)

    ATRASO_BOT = 0.35

    # LOOP ----------------------------------------------------

    def _linha_em(self, pos):
        melhor, dist = None, 34 ** 2
        for l, (mx, my) in enumerate(MEIOS):
            d = (mx - pos[0]) ** 2 + (my - pos[1]) ** 2
            if d < dist:
                melhor, dist = l, d
        return melhor

    def _mover_cursor(self, dx, dy):
        mx, my = MEIOS[self.cursor]
        melhor, custo = self.cursor, None
        for l, (x, y) in enumerate(MEIOS):
            px, py = (x - mx) * dx, (y - my) * dy
            frente = px if dx else py
            lado = abs(y - my) if dx else abs(x - mx)
            if frente <= 1:
                continue
            k = frente + lado * 2
            if custo is None or k < custo:
                melhor, custo = l, k
        self.cursor = melhor

    def evento_jogo(self, e):
        if e.type == pygame.MOUSEMOTION:
            self.hover = self._linha_em(e.pos)
            if self.hover is not None:
                self.cursor = self.hover
        if not self.humano_pode():
            return
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            l = self._linha_em(e.pos)
            if l is not None:
                self.cursor = l
                self.jogar(l)
        elif e.type == pygame.KEYDOWN:
            if e.key in TECLAS_DIR:
                self.hover = None
                self._mover_cursor(*TECLAS_DIR[e.key])
            elif e.key in TECLAS_OK:
                self.jogar(self.cursor)

    def atualizar_jogo(self, dt):
        self.atualizar_turnos(dt)

    # DESENHO -------------------------------------------------

    def desenhar_jogo(self, tela):
        tela.blit(self.fundo(self.jogador), (0, 0))
        if self.estado == "inicio":
            return
        for cx, d in enumerate(self.dono):
            if d is None:
                continue
            r, c = divmod(cx, N)
            rect = pygame.Rect(X0 + c * ESP + 5, Y0 + r * ESP + 5, ESP - 10, ESP - 10)
            pygame.draw.rect(tela, ui.clarear(self.cor(d), 60), rect, border_radius=8)
            self.desenhar_ovo(tela, d, rect.center, 50)

        if self.humano_pode() and not self.feitas[self.cursor]:
            a, b = PONTAS[self.cursor]
            cor = CORES_JOGADOR[self.vez] if int(self.tempo * 4) % 2 else (200, 200, 200)
            pygame.draw.line(tela, cor, a, b, 6)

        for l in range(N_LINHAS):
            if self.feitas[l]:
                a, b = PONTAS[l]
                cor = ui.escurecer(self.cor(self.quem_fez[l]), 40)
                larg = 8
                if l == self.ultima and self.tempo - self.t_ultima < 0.6:
                    cor, larg = AMARELO, 10
                pygame.draw.line(tela, cor, a, b, larg)
        for r in range(N + 1):
            for c in range(N + 1):
                p = (X0 + c * ESP, Y0 + r * ESP)
                pygame.draw.circle(tela, (40, 40, 60), p, 8)
                pygame.draw.circle(tela, (110, 110, 140), (p[0] - 2, p[1] - 2), 3)
        self.particulas.desenhar(tela)

    def desenhar_hud(self, tela):
        super().desenhar_hud(tela)
        caixa = pygame.Rect(LARGURA - 330, 12, 250, 56)
        ui.painel(tela, caixa, (20, 24, 40), BRANCO, 12, 3, sombra=False)
        for i in (0, 1):
            x = caixa.x + 30 if i == 0 else caixa.right - 30
            self.desenhar_ovo(tela, i, (x, caixa.centery + 1), 32)
        ui.desenhar_texto(tela, f"{self.placar[0]}  ×  {self.placar[1]}", caixa.center, 18,
                          AMARELO, "center")
