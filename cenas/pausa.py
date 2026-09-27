import pygame

from settings import *
from core import ui
from core.cena import Cena, tecla_voltar
from core.janela import TAMANHOS

# ============================================================
# MENU DE PAUSA (+ OPÇÕES)
# ============================================================
# Desenha a casa por trás (ainda animada) com um véu escuro.


class CenaPausa(Cena):

    def __init__(self, app, casa):
        super().__init__(app)
        self.casa = casa
        self.menu = ui.Menu(["CONTINUAR", "LOJA", "OPÇÕES", "TROCAR APARÊNCIA", "TROCAR NOME",
                             "SAIR DO JOGO"], LARGURA // 2, 190, 420, 60, 14, 16)

    def _voltar(self):
        self.som("voltar")
        self.app.trocar(self.casa, fade=False)

    def _voltar_para_pausa(self):
        self.app.trocar(CenaPausa(self.app, self.casa))

    def evento(self, e):
        if tecla_voltar(e):
            self._voltar()
            return

        escolha = self.menu.evento(e)
        if escolha == 0:
            self._voltar()
        elif escolha == 1:
            from cenas.loja import CenaLoja
            self.som("selecionar")
            self.app.trocar(CenaLoja(self.app, self.casa))
        elif escolha == 2:
            self.som("selecionar")
            self.app.trocar(CenaOpcoes(self.app, self.casa, self), fade=False)
        elif escolha == 3:
            from cenas.criador import CenaCriador
            self.som("selecionar")
            self.app.trocar(CenaCriador(self.app, "editar", self._voltar_para_pausa))
        elif escolha == 4:
            from cenas.nome import CenaNome
            self.som("selecionar")
            self.app.trocar(CenaNome(self.app, "trocar", self._voltar_para_pausa))
        elif escolha == 5:
            self.app.sair()

    def atualizar(self, dt):
        self.casa.atualizar(dt)
        self.menu.atualizar(dt)

    def desenhar(self, tela):
        self.casa.desenhar(tela)
        ui.veu(tela, 170)
        caixa = pygame.Rect(0, 0, 500, 560)
        caixa.midtop = (LARGURA // 2, 70)
        ui.painel(tela, caixa, (30, 34, 60), BRANCO, 20, 4)
        ui.desenhar_texto(tela, "PAUSADO", (LARGURA // 2, 100), 32, AMARELO, "midtop")
        self.menu.desenhar(tela)
        ui.centralizado(tela, "ESC para voltar", 660, 12)


class CenaOpcoes(Cena):

    def __init__(self, app, casa, pausa):
        super().__init__(app)
        self.casa = casa
        self.pausa = pausa
        self.menu = ui.Menu(self._rotulos(), LARGURA // 2, 190, 460, 60, 14, 16)

    def _rotulos(self):
        vol = int(self.audio.volume * 100)
        w, h = self.app.janela.tamanho
        return [
            f"MÚSICA: {vol}%" if vol else "MÚSICA: DESLIGADA",
            "SONS: SIM" if self.audio.sons_ligados else "SONS: NÃO",
            f"TELA: {w}x{h}",
            "SEMPRE DIA: SIM" if self.app.save["sempre_dia"] else "SEMPRE DIA: NÃO (RELÓGIO)",
            "VOLTAR",
        ]

    def _atualizar_rotulos(self):
        for b, r in zip(self.menu.botoes, self._rotulos()):
            b.rotulo = r

    def _proximo_tamanho(self):
        atual = tuple(self.app.janela.tamanho)
        indice = TAMANHOS.index(atual) + 1 if atual in TAMANHOS else 0
        novo = TAMANHOS[indice % len(TAMANHOS)]
        self.app.janela.redimensionar(novo)
        self.app.save["janela"] = list(self.app.janela.tamanho)
        self.app.save.salvar()

    def evento(self, e):
        if tecla_voltar(e):
            self.som("voltar")
            self.app.trocar(self.pausa, fade=False)
            return
        escolha = self.menu.evento(e)
        if escolha == 0:
            self.audio.proximo_volume()
        elif escolha == 1:
            self.audio.alternar_sons()
        elif escolha == 2:
            self._proximo_tamanho()
        elif escolha == 3:
            self.app.save["sempre_dia"] = not self.app.save["sempre_dia"]
            self.app.save.salvar()
        elif escolha == 4:
            self.som("voltar")
            self.app.trocar(self.pausa, fade=False)
            return
        if escolha is not None:
            self.som("clique")
            self._atualizar_rotulos()

    def atualizar(self, dt):
        self.casa.atualizar(dt)
        self.menu.atualizar(dt)

    def desenhar(self, tela):
        self.casa.desenhar(tela)
        ui.veu(tela, 170)
        caixa = pygame.Rect(0, 0, 540, 500)
        caixa.midtop = (LARGURA // 2, 70)
        ui.painel(tela, caixa, (30, 34, 60), BRANCO, 20, 4)
        ui.desenhar_texto(tela, "OPÇÕES", (LARGURA // 2, 100), 32, AMARELO, "midtop")
        self.menu.desenhar(tela)
        ui.centralizado(tela, "Dica: arraste a borda da janela para redimensionar", 596, 10)
        ui.centralizado(tela, "ESC para voltar", 660, 12)
