from settings import *
from jogos.base_multi import MiniJogoMulti

# ============================================================
# MINI JOGO HÍBRIDO: SOLO (CONTRA BOT) OU 2 JOGADORES
# ============================================================
# Na tela de início o jogador escolhe:
#   VS BOT FÁCIL / VS BOT MÉDIO / VS BOT DIFÍCIL / 2 JOGADORES
# O jogo lê:
#   self.solo         -> True contra o bot (o bot é o jogador 1 = J2)
#   self.dificuldade  -> 0 fácil, 1 médio, 2 difícil (só no solo)
# e termina com self.terminar_multi(vencedor, linhas) como os
# jogos de 2 jogadores (vencedor 0 = J1, 1 = J2/bot, None = empate).
#
# Medalhas: vencer o bot FÁCIL = bronze, MÉDIO = prata, DIFÍCIL = ouro.
# Aparece nas duas abas do menu (SOLO e 2 JOGADORES).

NOMES_BOT = ["BOT FÁCIL", "BOT MÉDIO", "BOT DIFÍCIL"]


class MiniJogoHibrido(MiniJogoMulti):

    HIBRIDO = True
    OPCOES = ["VS BOT FÁCIL", "VS BOT MÉDIO", "VS BOT DIFÍCIL", "2 JOGADORES"]
    CONTROLES_J2 = "SETAS + ENTER"
    MOEDAS_BOT = [8, 14, 22]         # vitória contra o bot (por dificuldade)
    MOEDAS_BOT_DERROTA = 2
    TEMPO_MINIMO = 20.0

    @property
    def solo(self):
        return self.opcao < 3

    @property
    def dificuldade(self):
        return min(2, self.opcao)

    def nome(self, i):
        if i == 1 and self.solo:
            return NOMES_BOT[self.dificuldade]
        return super().nome(i)

    def partida_valida(self):
        # Contra o bot basta o J1 ter jogado
        return self._mexeu[0] if self.solo else all(self._mexeu)

    def calcular_moedas(self, valor, venceu):
        if self.solo:
            return self.MOEDAS_BOT[self.dificuldade] if venceu else self.MOEDAS_BOT_DERROTA
        return super().calcular_moedas(valor, venceu)

    def terminar_multi(self, vencedor, linhas=None):
        # Venceu o bot: vale medalha (recorde "venceu nesta dificuldade")
        if self.solo and vencedor == 0 and self.estado != "fim":
            self.app.save.registrar(f"{self.ID}_{self.opcao}", 1)
        super().terminar_multi(vencedor, linhas)

    def evento(self, e):
        # Clique do mouse também conta como "jogou" (jogos de tabuleiro)
        import pygame
        if self.estado == "jogando" and e.type == pygame.MOUSEBUTTONDOWN:
            self._mexeu[0] = True
            if not self.solo:
                self._mexeu[1] = True
        super().evento(e)
