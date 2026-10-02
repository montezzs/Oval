import math
import random

import pygame

from settings import *
from core import ui
from core.assets import comida_sup
from jogos.base import MiniJogo

# ============================================================
# COBRINHA DO OVO
# ============================================================
# A cabeça da cobra é o seu ovo e a cauda cresce com a cor dele.
# Coma os limões! A cada 5 limões aparece um LIMÃO DOURADO que
# vale 5 pontos, mas some rapidinho.

COLS = 30
LINHAS = 18
CEL = 32
X0 = (LARGURA - COLS * CEL) // 2
Y0 = 84

CIMA, BAIXO, ESQ, DIR = (0, -1), (0, 1), (-1, 0), (1, 0)

TECLAS = {
    pygame.K_UP: CIMA, pygame.K_w: CIMA,
    pygame.K_DOWN: BAIXO, pygame.K_s: BAIXO,
    pygame.K_LEFT: ESQ, pygame.K_a: ESQ,
    pygame.K_RIGHT: DIR, pygame.K_d: DIR,
}

INTERVALO_INICIAL = 0.14
INTERVALO_MINIMO = 0.065
TEMPO_DOURADO = 6.0


def _tela(cel):
    """Centro de uma célula em pixels."""
    return (X0 + cel[0] * CEL + CEL / 2, Y0 + cel[1] * CEL + CEL / 2)


class Cobrinha(MiniJogo):

    ID = "cobrinha"
    TITULO = "COBRINHA DO OVO"
    TITULO_CURTO = "COBRINHA"
    MOEDAS_POR = 2              # 2 limões = 1 OVOEDA
    MOEDAS_MAX = 22
    DESCRICAO = "Seu ovo virou cobra! Coma limões para a cauda crescer com a sua cor."
    COR = (60, 150, 70)
    INSTRUCOES = [
        "Guie o seu ovo e coma os LIMÕES!",
        "Cada limão faz a cauda crescer com a sua cor.",
        "O LIMÃO DOURADO vale 5, mas some rápido!",
        "Não bata na cerca nem na própria cauda.",
        "SETAS ou WASD para mover",
    ]

    # --------------------------------------------------------
    # CENÁRIO: jardim com cerca de madeira
    # --------------------------------------------------------

    @classmethod
    def criar_fundo(cls, jogador):
        sup = pygame.Surface((LARGURA, ALTURA))
        sup.fill((58, 128, 58))
        rnd = random.Random(21)

        # Grama e flores ao redor
        for _ in range(500):
            x, y = rnd.randrange(LARGURA), rnd.randrange(ALTURA)
            pygame.draw.line(sup, (48, 110, 48), (x, y), (x + rnd.randint(-2, 2), y - 6), 2)
        for _ in range(60):
            x, y = rnd.randrange(LARGURA), rnd.randrange(ALTURA)
            cor = rnd.choice([(255, 120, 150), (255, 230, 90), (255, 255, 255), (170, 130, 255)])
            for dx, dy in ((-4, 0), (4, 0), (0, -4), (0, 4)):
                pygame.draw.circle(sup, cor, (x + dx, y + dy), 3)
            pygame.draw.circle(sup, (255, 200, 40), (x, y), 2)

        # Tabuleiro quadriculado
        for c in range(COLS):
            for l in range(LINHAS):
                cor = (104, 170, 70) if (c + l) % 2 == 0 else (94, 158, 62)
                pygame.draw.rect(sup, cor, (X0 + c * CEL, Y0 + l * CEL, CEL, CEL))

        # Cerca de madeira
        borda = pygame.Rect(X0 - 12, Y0 - 12, COLS * CEL + 24, LINHAS * CEL + 24)
        pygame.draw.rect(sup, (120, 76, 40), borda, 12, border_radius=6)
        pygame.draw.rect(sup, (160, 106, 60), borda.inflate(-6, -6), 3, border_radius=6)
        for x in range(borda.left, borda.right + 1, 64):
            for y in (borda.top, borda.bottom - 1):
                pygame.draw.rect(sup, (100, 60, 30), (x - 7, y - 10, 14, 20), border_radius=3)
                pygame.draw.rect(sup, (180, 120, 70), (x - 5, y - 8, 10, 4), border_radius=2)
        return sup

    @classmethod
    def desenhar_icone(cls, sup, jogador):
        w, h = sup.get_size()
        cor = jogador.cor
        for i in range(5):
            x = w // 2 - 60 + i * 18
            pygame.draw.circle(sup, jogador.cor_contorno, (x, h // 2 + 12), 11)
            pygame.draw.circle(sup, cor, (x, h // 2 + 12), 9)
        jogador.desenhar(sup, (w // 2 + 40, h // 2 + 6), 40)
        c = comida_sup(28)
        sup.blit(c, c.get_rect(center=(w // 2 + 80, h // 2 - 26)))

    # --------------------------------------------------------
    # PARTIDA
    # --------------------------------------------------------

    def reiniciar(self):
        meio = LINHAS // 2
        self.corpo = [(8, meio), (7, meio), (6, meio), (5, meio)]
        self.anterior = list(self.corpo)
        self.direcao = DIR
        self.fila = []                  # próximas direções digitadas
        self.intervalo = INTERVALO_INICIAL
        self.relogio = 0.0
        self.crescer = 0
        self.morto = False
        self.tempo_morto = 0.0
        self.limoes = 0
        self.limao = None
        self.dourado = None
        self.tempo_dourado = 0.0
        self.limao = self._lugar_livre()

    def _lugar_livre(self):
        ocupado = set(self.corpo)
        if self.limao:
            ocupado.add(self.limao)
        if self.dourado:
            ocupado.add(self.dourado)
        livres = [(c, l) for c in range(COLS) for l in range(LINHAS) if (c, l) not in ocupado]
        return random.choice(livres) if livres else None

    # --------------------------------------------------------

    def evento_jogo(self, e):
        if e.type == pygame.KEYDOWN and e.key in TECLAS:
            nova = TECLAS[e.key]
            ultima = self.fila[-1] if self.fila else self.direcao
            # Não deixa virar 180 graus (morreria na hora)
            if nova != ultima and (nova[0] != -ultima[0] or nova[1] != -ultima[1]):
                if len(self.fila) < 3:
                    self.fila.append(nova)

    def atualizar_jogo(self, dt):
        if self.morto:
            self.tempo_morto += dt
            if self.tempo_morto > 0.9:
                self.terminar(linhas=[f"LIMÕES: {self.pontos}",
                                      f"TAMANHO: {len(self.corpo)}"])
            return

        # Limão dourado some depois de um tempo
        if self.dourado:
            self.tempo_dourado -= dt
            if self.tempo_dourado <= 0:
                self.particulas.explodir(_tela(self.dourado), [AMARELO, BRANCO], 10, 120)
                self.dourado = None

        self.relogio += dt
        while self.relogio >= self.intervalo and not self.morto:
            self.relogio -= self.intervalo
            self._passo()

    def _passo(self):
        if self.fila:
            self.direcao = self.fila.pop(0)

        cabeca = self.corpo[0]
        nova = (cabeca[0] + self.direcao[0], cabeca[1] + self.direcao[1])

        # A ponta da cauda sai do lugar neste passo (a não ser que cresça)
        perigo = self.corpo if self.crescer else self.corpo[:-1]

        if not (0 <= nova[0] < COLS and 0 <= nova[1] < LINHAS) or nova in perigo:
            self._morrer()
            return

        self.anterior = list(self.corpo)
        self.corpo.insert(0, nova)

        if self.crescer:
            self.crescer -= 1
            self.anterior.append(self.anterior[-1])   # segmento novo nasce parado
        else:
            self.corpo.pop()

        if nova == self.limao:
            self._comer(nova, 1)
            self.limao = self._lugar_livre()
            self.limoes += 1
            if self.limoes % 5 == 0 and self.dourado is None:
                self.dourado = self._lugar_livre()
                self.tempo_dourado = TEMPO_DOURADO
        elif nova == self.dourado:
            self._comer(nova, 5)
            self.dourado = None

        if self.limao is None:
            # Encheu o tabuleiro inteiro!
            self.terminar(venceu=True, linhas=[f"LIMÕES: {self.pontos}", "TABULEIRO CHEIO!"])

    def _comer(self, cel, valor):
        self.pontos += valor
        self.crescer += valor
        self.intervalo = max(INTERVALO_MINIMO, self.intervalo - 0.003 * valor)
        pos = _tela(cel)
        self.particulas.explodir(pos, [(250, 222, 40), (255, 248, 180), (120, 200, 60)],
                                 18 if valor == 1 else 36, 200)
        self.textos.adicionar(f"+{valor}", (pos[0], pos[1] - 20),
                              AMARELO if valor > 1 else BRANCO, 16 if valor > 1 else 14)
        self.som("moeda" if valor > 1 else "comer")

    def _morrer(self):
        self.morto = True
        self.tempo_morto = 0.0
        self.relogio = 0.0
        self.anterior = list(self.corpo)
        self.tremer(0.35)
        self.som("explosao", 0.6)
        pos = _tela(self.corpo[0])
        self.particulas.explodir(pos, [self.jogador.cor, BRANCO, self.jogador.cor_escura], 30, 260)

    # --------------------------------------------------------
    # DESENHO
    # --------------------------------------------------------

    def _posicoes(self):
        """Posição suave (interpolada) de cada segmento."""
        t = 0.0 if self.morto else min(1.0, self.relogio / self.intervalo)
        pos = []
        for i, cel in enumerate(self.corpo):
            ant = self.anterior[i] if i < len(self.anterior) else cel
            a, b = _tela(ant), _tela(cel)
            pos.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
        return pos

    def desenhar_jogo(self, tela):
        tela.blit(self.fundo(self.jogador), (0, 0))

        # Limões (balançando)
        balanco = (self.tempo * 3) % 2
        dy = -abs(balanco - 1) * 4
        if self.limao:
            cx, cy = _tela(self.limao)
            pygame.draw.ellipse(tela, (70, 120, 50), (cx - 12, cy + 8, 24, 8))
            c = comida_sup(28)
            tela.blit(c, c.get_rect(center=(cx, cy + dy)))

        if self.dourado:
            cx, cy = _tela(self.dourado)
            piscando = self.tempo_dourado > 2 or int(self.tempo * 8) % 2 == 0
            if piscando:
                brilho = int(18 + 4 * abs(balanco - 1))
                pygame.draw.circle(tela, (255, 240, 120), (int(cx), int(cy)), brilho, 3)
                c = comida_sup(32)
                tela.blit(c, c.get_rect(center=(cx, cy + dy)))
                ui.estrela(tela, (cx + 14, cy - 14), 6, AMARELO, self.tempo * 3)

        # Corpo: do rabo para a cabeça
        pos = self._posicoes()
        cor = self.jogador.cor
        clara = self.jogador.cor_clara
        # Contorno bem escuro para a cauda aparecer em cima da grama
        contorno = (90, 90, 110) if sum(cor) > 600 else ui.escurecer(cor, 120)
        n = len(pos)

        for i in range(n - 1, 0, -1):
            x, y = pos[i]
            raio = 13 - int(5 * i / max(1, n - 1))
            # Liga um segmento no outro para parecer contínuo
            px, py = pos[i - 1]
            mx, my = (x + px) / 2, (y + py) / 2
            pygame.draw.circle(tela, contorno, (int(mx), int(my)), raio + 3)
            pygame.draw.circle(tela, contorno, (int(x), int(y)), raio + 3)

        for i in range(n - 1, 0, -1):
            x, y = pos[i]
            raio = 13 - int(5 * i / max(1, n - 1))
            px, py = pos[i - 1]
            mx, my = (x + px) / 2, (y + py) / 2
            c = cor if i % 2 else clara
            pygame.draw.circle(tela, c, (int(mx), int(my)), raio)
            pygame.draw.circle(tela, c, (int(x), int(y)), raio)
            pygame.draw.circle(tela, ui.clarear(c, 50), (int(x - raio / 3), int(y - raio / 3)),
                               max(2, raio // 4))

        # Cabeça: o próprio ovo do jogador!
        hx, hy = pos[0]
        if self.morto:
            ang = math.sin(self.tempo_morto * 20) * 15
            self.jogador.desenhar(tela, (hx, hy), 42, espelhar=self.direcao == ESQ, angulo=ang)
        else:
            self.jogador.desenhar(tela, (hx, hy), 42, espelhar=self.direcao == ESQ)

        self.particulas.desenhar(tela)
        self.textos.desenhar(tela)

        if self.estado == "jogando" and not self.morto and self.dourado:
            ui.desenhar_texto(tela, f"LIMÃO DOURADO: {self.tempo_dourado:.1f}s",
                              (LARGURA // 2, ALTURA - 38), 12, AMARELO, "center")
