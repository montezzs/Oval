import math
import random
import threading
import time
from functools import lru_cache

import pygame

from settings import *
from core import ui
from jogos.base_hibrido import MiniJogoHibrido
from jogos.base_multi import CORES_JOGADOR

# ============================================================
# JOGOS DE TABULEIRO (BASE) + JOGO DA VELHA
# ============================================================
# JogoTabuleiro: base comum dos jogos de tabuleiro por turnos
# (jogo da velha, 4 em linha, pontinhos, xadegg):
#   - self.vez (0 = J1, 1 = J2/bot), "hot seat" no 2 JOGADORES
#   - o bot pensa numa THREAD (a tela nunca trava); o jogo só
#     implementa foto_bot() (cópia do estado), pensar_bot(foto)
#     (roda na thread) e aplicar_bot(jogada)
#   - finalizar(vencedor, linhas): mostra o tabuleiro final um
#     pouquinho e depois chama terminar_multi
#   - tela de início compacta (4 modos + J2 + VOLTAR)

TECLAS_DIR = {
    pygame.K_UP: (0, -1), pygame.K_w: (0, -1), pygame.K_DOWN: (0, 1), pygame.K_s: (0, 1),
    pygame.K_LEFT: (-1, 0), pygame.K_a: (-1, 0), pygame.K_RIGHT: (1, 0), pygame.K_d: (1, 0),
}
TECLAS_OK = (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)


def fundo_mesa(cor_topo, cor_base, cor_ponto, semente):
    """Fundo simples: gradiente + bolinhas discretas."""
    sup = ui.gradiente(LARGURA, ALTURA, cor_topo, cor_base)
    rnd = random.Random(semente)
    for _ in range(90):
        pygame.draw.circle(sup, cor_ponto, (rnd.randrange(LARGURA), rnd.randrange(ALTURA)),
                           rnd.choice((2, 3, 3, 4)))
    return sup


class JogoTabuleiro(MiniJogoHibrido):

    CONTAGEM = False
    CONTROLES_J1 = "MOUSE OU SETAS + ENTER"
    CONTROLES_J2 = "MOUSE OU SETAS + ENTER"
    ATRASO_BOT = 0.45          # tempo mínimo "pensando" (segundos de jogo)
    ESPERA_FIM = 1.4

    # --------------------------------------------------------
    # TURNOS / BOT
    # --------------------------------------------------------

    def _reset_turnos(self, vez=0):
        self.vez = vez
        self._geracao = getattr(self, "_geracao", 0) + 1
        self._bot_thread = None
        self._bot_espera = 0.0
        self._fim = None
        if not hasattr(self, "tempo_bot_max"):
            self.tempo_bot_max = 0.0

    def vez_do_bot(self):
        return self.solo and self.vez == 1 and self._fim is None

    def ocupado(self):
        """True durante animações (ninguém joga)."""
        return False

    def humano_pode(self):
        return (self.estado == "jogando" and self._fim is None and not self.vez_do_bot()
                and not self.ocupado())

    def foto_bot(self):
        raise NotImplementedError

    def pensar_bot(self, foto):
        raise NotImplementedError

    def aplicar_bot(self, jogada):
        raise NotImplementedError

    def _atualizar_bot(self, dt):
        if not self.vez_do_bot() or self.ocupado():
            return
        if self._bot_thread is None:
            foto = self.foto_bot()
            caixa = {}

            def rodar():
                t0 = time.perf_counter()
                try:
                    caixa["r"] = self.pensar_bot(foto)
                except Exception as ex:          # repassa para o loop principal
                    caixa["erro"] = ex
                caixa["t"] = time.perf_counter() - t0

            t = threading.Thread(target=rodar, daemon=True)
            self._bot_thread = (t, caixa, self._geracao)
            self._bot_espera = 0.0
            t.start()
            return
        self._bot_espera += dt
        t, caixa, ger = self._bot_thread
        if t.is_alive() or self._bot_espera < self.ATRASO_BOT:
            return
        self._bot_thread = None
        if ger != self._geracao:
            return
        if "erro" in caixa:
            raise caixa["erro"]
        self.tempo_bot_max = max(self.tempo_bot_max, caixa.get("t", 0.0))
        self.aplicar_bot(caixa["r"])

    def pensando(self):
        return self._bot_thread is not None

    def finalizar(self, vencedor, linhas=None, espera=None):
        if self._fim is None:
            self._fim = [vencedor, linhas or [], self.ESPERA_FIM if espera is None else espera]

    def atualizar_turnos(self, dt):
        """Chamar no atualizar_jogo de cada jogo."""
        if self._fim is not None:
            self._fim[2] -= dt
            if self._fim[2] <= 0:
                self.terminar_multi(self._fim[0], self._fim[1])
            return
        self._atualizar_bot(dt)

    def evento(self, e):
        if self.estado == "jogando" and e.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
            if not self.vez_do_bot():
                self._mexeu[0 if self.solo else self.vez] = True
        super().evento(e)

    # --------------------------------------------------------
    # HUD: DE QUEM É A VEZ
    # --------------------------------------------------------

    def texto_vez(self):
        if self.vez_do_bot():
            return "PENSANDO" + "." * (1 + int(self.tempo * 3) % 3)
        return "SUA VEZ!"

    def desenhar_vez(self, tela, rect):
        i = self.vez
        ui.painel(tela, rect, (20, 24, 40), CORES_JOGADOR[i], 12, 3, sombra=False)
        self.desenhar_ovo(tela, i, (rect.x + 30, rect.centery + 1), 34)
        ui.desenhar_texto(tela, self.nome(i)[:14], (rect.x + 58, rect.y + 10), 12,
                          CORES_JOGADOR[i], "topleft")
        ui.desenhar_texto(tela, self.texto_vez(), (rect.x + 58, rect.bottom - 10), 10,
                          AMARELO, "bottomleft")

    def desenhar_hud(self, tela):
        if self._fim is None:
            self.desenhar_vez(tela, pygame.Rect(12, 12, 290, 56))

    # --------------------------------------------------------
    # TELA DE INÍCIO COMPACTA (4 modos + J2 + VOLTAR)
    # --------------------------------------------------------

    def _desenhar_inicio(self, tela):
        ui.veu(tela, 150)
        topo = 24
        caixa = pygame.Rect(0, topo, 760, ALTURA - topo - 24)
        caixa.centerx = LARGURA // 2
        ui.painel(tela, caixa, (28, 32, 56), self.COR, 22, 5)

        tam = ui.tamanho_que_cabe(self.TITULO, caixa.w - 60, (28, 24, 20))
        ui.desenhar_texto(tela, self.TITULO, (LARGURA // 2, topo + 20), tam, AMARELO, "midtop")
        ui.desenhar_texto(tela, "VS BOT OU 2 JOGADORES NO MESMO PC", (LARGURA // 2, topo + 58),
                          10, (180, 200, 255), "midtop")

        y_ovos = topo + 124
        for i, x in ((0, caixa.x + 150), (1, caixa.right - 150)):
            balanco = math.sin(self.tempo * 3 + i * 1.5) * 4
            self.desenhar_ovo(tela, i, (x, y_ovos + balanco), 60, espelhar=(i == 1))
            ui.desenhar_texto(tela, self.nome(i), (x, y_ovos + 42), 14, CORES_JOGADOR[i], "midtop")
            ctrl = "BOT" if (i == 1 and self.solo) else "MOUSE OU SETAS"
            ui.desenhar_texto(tela, ctrl, (x, y_ovos + 64), 10, BRANCO, "midtop")
        ui.desenhar_texto(tela, "VS", (LARGURA // 2, y_ovos), 32, AMARELO, "center")

        y = y_ovos + 88
        for linha in self.INSTRUCOES:
            for sub in ui.quebrar_linhas(linha, 10, caixa.w - 50):
                ui.desenhar_texto(tela, sub, (LARGURA // 2, y), 10, BRANCO, "midtop")
                y += 16
            y += 3

        v = self.vitorias()
        y_rec = self.menu_inicio.botoes[0].rect.y - 32
        ui.desenhar_texto(tela, f"VITÓRIAS  J1 {v[0]} × {v[1]} J2", (LARGURA // 2, y_rec),
                          14, AMARELO, "midtop")
        ui.desenhar_texto(tela, "ESCOLHA O MODO", (LARGURA // 2, y_rec - 24), 12,
                          (180, 200, 255), "midtop")
        self.menu_inicio.desenhar(tela)


# ============================================================
# JOGO DA VELHA
# ============================================================

CEL = 150
TAB = pygame.Rect(0, 0, CEL * 3, CEL * 3)
TAB.center = (LARGURA // 2, 420)
LINHAS3 = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]
META = 3                    # melhor de 5: quem fizer 3 vitórias
MAX_RODADAS = 9


def _vencedor3(t):
    for a, b, c in LINHAS3:
        if t[a] is not None and t[a] == t[b] == t[c]:
            return t[a], (a, b, c)
    return None, None


@lru_cache(maxsize=None)
def _minimax3(t, p):
    """Valor da posição para quem joga (p): 1 ganha, 0 empate, -1 perde."""
    v, _ = _vencedor3(t)
    if v is not None:
        return 1 if v == p else -1
    if None not in t:
        return 0
    melhor = -2
    for k in range(9):
        if t[k] is None:
            n = t[:k] + (p,) + t[k + 1:]
            melhor = max(melhor, -_minimax3(n, 1 - p))
            if melhor == 1:
                break
    return melhor


class JogoVelha(JogoTabuleiro):

    ID = "jogo_velha"
    TITULO = "JOGO DA VELHA"
    TITULO_CURTO = "VELHA"
    DESCRICAO = "O clássico! Seu ovinho é o X, o rival é o O. Melhor de 5: quem fizer 3 vitórias leva!"
    COR = (200, 120, 60)
    INSTRUCOES = [
        "Faça 3 ovinhos em linha: reta ou diagonal!",
        "MELHOR DE 5: quem vencer 3 rodadas leva. Quem começa alterna.",
        "MOUSE: clique na casa  •  TECLADO: SETAS + ENTER",
    ]
    @classmethod
    def criar_fundo(cls, jogador):
        sup = fundo_mesa((250, 214, 160), (214, 160, 100), (236, 196, 140), 33)
        pygame.draw.rect(sup, (150, 96, 50), TAB.inflate(56, 56).move(0, 8), border_radius=28)
        pygame.draw.rect(sup, (255, 240, 210), TAB.inflate(56, 56), border_radius=28)
        pygame.draw.rect(sup, (170, 110, 60), TAB.inflate(56, 56), 6, border_radius=28)
        for k in (1, 2):
            x = TAB.x + k * CEL
            y = TAB.y + k * CEL
            pygame.draw.line(sup, (120, 80, 50), (x, TAB.y + 8), (x, TAB.bottom - 8), 10)
            pygame.draw.line(sup, (120, 80, 50), (TAB.x + 8, y), (TAB.right - 8, y), 10)
        return sup

    @classmethod
    def desenhar_icone(cls, sup, jogador):
        w, h = sup.get_size()
        c = min(w, h) // 5
        x0, y0 = w // 2 - c * 3 // 2, h // 2 - c * 3 // 2
        for k in (1, 2):
            pygame.draw.line(sup, (90, 60, 40), (x0 + k * c, y0), (x0 + k * c, y0 + 3 * c), 3)
            pygame.draw.line(sup, (90, 60, 40), (x0, y0 + k * c), (x0 + 3 * c, y0 + k * c), 3)
        m = c // 4
        pygame.draw.line(sup, (230, 70, 70), (x0 + m, y0 + m), (x0 + c - m, y0 + c - m), 4)
        pygame.draw.line(sup, (230, 70, 70), (x0 + c - m, y0 + m), (x0 + m, y0 + c - m), 4)
        pygame.draw.circle(sup, (70, 120, 230), (x0 + c * 5 // 2, y0 + c * 3 // 2), c // 2 - 3, 4)
        jogador.desenhar(sup, (x0 + c // 2 + c * 2, y0 + c // 2), c * 0.8)

    # --------------------------------------------------------

    def reiniciar(self):
        self.placar = [0, 0]
        self.rodada = 0
        self.cursor = 4
        self._nova_rodada()

    def _nova_rodada(self):
        self.tab = [None] * 9
        self.surgiu = [0.0] * 9
        self.linha_vit = None
        self.pausa_rodada = 0.0
        self._reset_turnos(self.rodada % 2)

    # --------------------------------------------------------

    def jogadas_validas(self):
        return [k for k in range(9) if self.tab[k] is None]

    def jogar(self, k):
        if self.tab[k] is not None or self.pausa_rodada > 0:
            return
        self.tab[k] = self.vez
        self.surgiu[k] = self.tempo
        self.som("bater" if self.vez == 0 else "clique")
        v, linha = _vencedor3(tuple(self.tab))
        if v is not None or None not in self.tab:
            self.rodada += 1
            self.linha_vit = linha
            if v is not None:
                self.placar[v] += 1
                c = self._centro(linha[1])
                self.particulas.explodir(c, [CORES_JOGADOR[v], AMARELO, BRANCO], 30, 300, 0.9)
                self.textos.adicionar(f"PONTO DE {self.nome(v)[:10]}!", c, AMARELO) \
                    if hasattr(self.textos, "adicionar") else None
            if max(self.placar) >= META or self.rodada >= MAX_RODADAS:
                if self.placar[0] == self.placar[1]:
                    ganhador = None
                else:
                    ganhador = 0 if self.placar[0] > self.placar[1] else 1
                self.finalizar(ganhador, [f"PLACAR  {self.placar[0]} × {self.placar[1]}",
                                          f"RODADAS JOGADAS: {self.rodada}"], 1.6)
            else:
                self.pausa_rodada = 1.3
            return
        self.vez = 1 - self.vez

    def ocupado(self):
        return self.pausa_rodada > 0

    # BOT -----------------------------------------------------

    def foto_bot(self):
        return tuple(self.tab), self.vez, self.dificuldade

    def pensar_bot(self, foto):
        t, p, dif = foto
        livres = [k for k in range(9) if t[k] is None]
        if dif == 0:
            return random.choice(livres)
        if dif == 1:
            for quem in (p, 1 - p):         # ganha, senão bloqueia
                for k in livres:
                    n = t[:k] + (quem,) + t[k + 1:]
                    if _vencedor3(n)[0] == quem:
                        return k
            if 4 in livres and random.random() < 0.6:
                return 4
            return random.choice(livres)
        random.shuffle(livres)
        return max(livres, key=lambda k: -_minimax3(t[:k] + (p,) + t[k + 1:], 1 - p))

    def aplicar_bot(self, k):
        self.jogar(k)

    # LOOP ----------------------------------------------------

    def _celula_em(self, pos):
        if not TAB.collidepoint(pos):
            return None
        return (pos[1] - TAB.y) // CEL * 3 + (pos[0] - TAB.x) // CEL

    def _centro(self, k):
        return (TAB.x + (k % 3) * CEL + CEL // 2, TAB.y + (k // 3) * CEL + CEL // 2)

    def evento_jogo(self, e):
        if not self.humano_pode():
            return
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            k = self._celula_em(e.pos)
            if k is not None:
                self.cursor = k
                self.jogar(k)
        elif e.type == pygame.MOUSEMOTION:
            k = self._celula_em(e.pos)
            if k is not None:
                self.cursor = k
        elif e.type == pygame.KEYDOWN:
            if e.key in TECLAS_DIR:
                dx, dy = TECLAS_DIR[e.key]
                x, y = (self.cursor % 3 + dx) % 3, (self.cursor // 3 + dy) % 3
                self.cursor = y * 3 + x
            elif e.key in TECLAS_OK:
                self.jogar(self.cursor)

    def atualizar_jogo(self, dt):
        if self.pausa_rodada > 0 and self._fim is None:
            self.pausa_rodada -= dt
            if self.pausa_rodada <= 0:
                self.pausa_rodada = 0
                self._nova_rodada()
            return
        self.atualizar_turnos(dt)

    # DESENHO -------------------------------------------------

    def desenhar_jogo(self, tela):
        tela.blit(self.fundo(self.jogador), (0, 0))
        if self.estado == "inicio":
            return
        if self.humano_pode() and self.tab[self.cursor] is None:
            cx, cy = self._centro(self.cursor)
            r = pygame.Rect(0, 0, CEL - 22, CEL - 22)
            r.center = (cx, cy)
            pygame.draw.rect(tela, CORES_JOGADOR[self.vez], r, 4, border_radius=16)
        for k, dono in enumerate(self.tab):
            if dono is None:
                continue
            cx, cy = self._centro(k)
            cor = self.cor(dono)
            escuro = ui.escurecer(cor, 70)
            if dono == 0:
                for s in (-1, 1):
                    pygame.draw.line(tela, escuro, (cx - 52, cy - 52 * s), (cx + 52, cy + 52 * s), 16)
                    pygame.draw.line(tela, cor, (cx - 50, cy - 50 * s), (cx + 50, cy + 50 * s), 10)
            else:
                pygame.draw.circle(tela, escuro, (cx, cy), 58, 14)
                pygame.draw.circle(tela, cor, (cx, cy), 55, 8)
            t = min(1.0, (self.tempo - self.surgiu[k]) * 5)
            dy = -int((1 - t) * 40)
            self.desenhar_ovo(tela, dono, (cx, cy + dy + 2), 70)
        if self.linha_vit:
            a, b = self._centro(self.linha_vit[0]), self._centro(self.linha_vit[2])
            if int(self.tempo * 6) % 2 == 0:
                pygame.draw.line(tela, AMARELO, a, b, 12)

        # Placar da série
        caixa = pygame.Rect(0, 84, 420, 44)
        caixa.centerx = LARGURA // 2
        ui.painel(tela, caixa, (20, 24, 40), BRANCO, 12, 3, sombra=False)
        ui.desenhar_texto(tela, f"{self.placar[0]}  ×  {self.placar[1]}", caixa.center, 18,
                          AMARELO, "center")
        for i in (0, 1):
            x = caixa.x + 30 if i == 0 else caixa.right - 30
            self.desenhar_ovo(tela, i, (x, caixa.centery + 1), 30)
        ui.desenhar_texto(tela, f"RODADA {min(self.rodada + 1, MAX_RODADAS)}  •  MELHOR DE 5",
                          (LARGURA // 2, caixa.bottom + 6), 8, (90, 50, 30), "midtop", False)
        self.particulas.desenhar(tela)
        self.textos.desenhar(tela)
