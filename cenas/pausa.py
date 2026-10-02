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
        self.rotulos = ["CONTINUAR", "CONQUISTAS", "AMIGOS", "VIZINHANÇA", "LOJA", "OPÇÕES",
                        "TROCAR APARÊNCIA", "TROCAR NOME", "SAIR DO JOGO"]
        self.menu = ui.Menu(self.rotulos, LARGURA // 2, 150, 420, 44, 8, 14)

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
        if escolha is None:
            return
        rotulo = self.rotulos[escolha]
        if rotulo == "CONTINUAR":
            self._voltar()
        elif rotulo == "CONQUISTAS":
            from cenas.conquistas import CenaConquistas
            self.som("selecionar")
            self.app.trocar(CenaConquistas(self.app, self.casa, self), fade=False)
        elif rotulo == "AMIGOS":
            from cenas.amigos import CenaAmigos
            self.som("selecionar")
            self.app.trocar(CenaAmigos(self.app, self.casa, self), fade=False)
        elif rotulo == "VIZINHANÇA":
            self.som("selecionar")
            self.casa.ir_para_rua()
        elif rotulo == "LOJA":
            from cenas.loja import CenaLoja
            self.som("selecionar")
            self.app.trocar(CenaLoja(self.app, self.casa))
        elif rotulo == "OPÇÕES":
            self.som("selecionar")
            self.app.trocar(CenaOpcoes(self.app, self.casa, self), fade=False)
        elif rotulo == "TROCAR APARÊNCIA":
            from cenas.criador import CenaCriador
            self.som("selecionar")
            self.app.trocar(CenaCriador(self.app, "editar", self._voltar_para_pausa))
        elif rotulo == "TROCAR NOME":
            from cenas.nome import CenaNome
            self.som("selecionar")
            self.app.trocar(CenaNome(self.app, "trocar", self._voltar_para_pausa))
        elif rotulo == "SAIR DO JOGO":
            self.app.sair()

    def atualizar(self, dt):
        self.casa.atualizar(dt)
        self.menu.atualizar(dt)

    def desenhar(self, tela):
        self.casa.desenhar(tela)
        ui.veu(tela, 170)
        caixa = pygame.Rect(0, 0, 500, 610)
        caixa.midtop = (LARGURA // 2, 36)
        ui.painel(tela, caixa, (30, 34, 60), BRANCO, 20, 4)
        ui.desenhar_texto(tela, "PAUSADO", (LARGURA // 2, 62), 32, AMARELO, "midtop", True, True)
        self.menu.desenhar(tela)
        ui.centralizado(tela, "ESC para voltar", 666, 12)


class CenaOpcoes(Cena):
    """
    Opções (da pausa da casa ou da tela inicial). Na tela inicial
    aparece também RECOMEÇAR DO ZERO: apaga TODOS os saves e os
    ovos vão embora de caminhão de mudança (cenas/mudanca.py).
    """

    def __init__(self, app, casa, pausa):
        super().__init__(app)
        self.casa = casa
        self.pausa = pausa
        from cenas.titulo import CenaTitulo
        self.pode_resetar = isinstance(pausa, CenaTitulo)
        self.menu = ui.Menu(self._rotulos(), LARGURA // 2, 96, 500, 44, 8, 14)
        if self.pode_resetar:
            b = self.menu.botoes[-2]
            b.cor, b.cor_hover = (130, 50, 50), (190, 70, 70)
        self.confirmando = False
        self.menu_confirmar = ui.Menu(["NÃO, VOLTAR", "SIM, APAGAR TUDO"], LARGURA // 2, 420,
                                      380, 54, 12, 14)
        b = self.menu_confirmar.botoes[1]
        b.cor, b.cor_hover = (150, 50, 50), (210, 70, 70)

    def _rotulos(self):
        vol = int(self.audio.volume * 100)
        sfx = int(self.audio.volume_sfx * 100)
        w, h = self.app.janela.tamanho
        rotulos = [
            f"MÚSICA: {vol}%" if vol else "MÚSICA: DESLIGADA",
            f"EFEITOS: {sfx}%" if sfx else "EFEITOS: DESLIGADOS",
            f"TELA: {w}x{h}",
            "SEMPRE DIA: SIM" if self.app.config["sempre_dia"] else "SEMPRE DIA: NÃO (RELÓGIO)",
            "TELA CHEIA (F11)",
            "TREMOR DA TELA: " + ("REDUZIDO" if self.app.config["reduzir_tremor"] else "NORMAL"),
            "MOSTRAR FPS: " + ("SIM" if self.app.config["mostrar_fps"] else "NÃO"),
            "CORES DAS BARRAS: " + ("DALTÔNICO" if self.app.config["daltonico"] else "PADRÃO"),
        ]
        if self.pode_resetar:
            rotulos.append("RECOMEÇAR DO ZERO")
        rotulos.append("VOLTAR")
        return rotulos

    def _atualizar_rotulos(self):
        for b, r in zip(self.menu.botoes, self._rotulos()):
            b.rotulo = r

    def _proximo_tamanho(self):
        atual = tuple(self.app.janela.tamanho)
        indice = TAMANHOS.index(atual) + 1 if atual in TAMANHOS else 0
        novo = TAMANHOS[indice % len(TAMANHOS)]
        self.app.janela.redimensionar(novo)
        self.app.config["janela"] = list(self.app.janela.tamanho)
        self.app.config.salvar()

    def _evento_confirmar(self, e):
        if tecla_voltar(e):
            self.som("voltar")
            self.confirmando = False
            return
        escolha = self.menu_confirmar.evento(e)
        if escolha == 0:
            self.som("voltar")
            self.confirmando = False
        elif escolha == 1:
            from cenas.mudanca import CenaMudanca
            self.som("selecionar")
            self.app.trocar(CenaMudanca(self.app))

    def evento(self, e):
        if self.confirmando:
            self._evento_confirmar(e)
            return
        if tecla_voltar(e):
            self.som("voltar")
            self.app.trocar(self.pausa, fade=False)
            return
        escolha = self.menu.evento(e)
        if escolha is None:
            return
        rotulo = self.menu.botoes[escolha].rotulo
        if escolha == 0:
            self.audio.proximo_volume()
        elif escolha == 1:
            self.audio.proximo_volume_sfx()
        elif escolha == 2:
            self._proximo_tamanho()
        elif escolha == 3:
            self.app.config["sempre_dia"] = not self.app.config["sempre_dia"]
            self.app.config.salvar()
        elif rotulo.startswith("TELA CHEIA"):
            self.app.alternar_tela_cheia()
        elif rotulo.startswith("TREMOR") or rotulo.startswith("MOSTRAR FPS") or rotulo.startswith("CORES"):
            chave = "reduzir_tremor" if rotulo.startswith("TREMOR") else \
                ("mostrar_fps" if rotulo.startswith("MOSTRAR") else "daltonico")
            self.app.config[chave] = not self.app.config[chave]
            self.app.config.salvar()
        elif rotulo == "RECOMEÇAR DO ZERO":
            self.som("erro", 0.6)
            self.confirmando = True
            self.menu_confirmar.indice = 0
            return
        else:
            self.som("voltar")
            self.app.trocar(self.pausa, fade=False)
            return
        self.som("clique")
        self._atualizar_rotulos()

    def atualizar(self, dt):
        self.casa.atualizar(dt)
        if self.confirmando:
            self.menu_confirmar.atualizar(dt)
        else:
            self.menu.atualizar(dt)

    def desenhar(self, tela):
        self.casa.desenhar(tela)
        ui.veu(tela, 170)
        caixa = pygame.Rect(0, 0, 580, 650)
        caixa.midtop = (LARGURA // 2, 16)
        ui.painel(tela, caixa, (30, 34, 60), BRANCO, 20, 4)
        ui.desenhar_texto(tela, "OPÇÕES", (LARGURA // 2, 36), 28, AMARELO, "midtop", True, True)
        self.menu.desenhar(tela)
        ui.centralizado(tela, "Dica: arraste a borda da janela para redimensionar", 680, 10)
        ui.centralizado(tela, "ESC para voltar", 700, 10)
        if self.confirmando:
            self._desenhar_confirmar(tela)

    def _desenhar_confirmar(self, tela):
        ui.veu(tela, 150)
        caixa = pygame.Rect(0, 0, 620, 360)
        caixa.center = (LARGURA // 2, ALTURA // 2)
        ui.painel(tela, caixa, (50, 26, 34), (230, 90, 90), 20, 5)
        ui.desenhar_texto(tela, "RECOMEÇAR DO ZERO?", (LARGURA // 2, caixa.y + 30), 22,
                          (255, 140, 140), "midtop")
        linhas = ["TODOS os ovos, casas, moedas, recordes,",
                  "conquistas e preferências serão APAGADOS.",
                  "Os ovos vão se mudar da rua. Não dá para desfazer!"]
        for k, linha in enumerate(linhas):
            ui.desenhar_texto(tela, linha, (LARGURA // 2, caixa.y + 84 + k * 24), 11, BRANCO,
                              "midtop")
        self.menu_confirmar.desenhar(tela)
