import math

import pygame

from settings import *
from core.idioma import t
from core import perfis, ui
from core.cena import Cena, tecla_voltar
from core.fundo_menu import FundoAnimado

# ============================================================
# NOME
# ============================================================
# Usada no começo do jogo (modo "inicial"), no menu de pausa
# para trocar o nome (modo "trocar") e no +NOVO da vizinhança
# (modo "novo"). Dois ovos da rua não podem ter o mesmo nome.

LIMITE_NOME = 15


class CenaNome(Cena):

    musica = "nasce_um_ovo"

    def __init__(self, app, modo="inicial", ao_terminar=None, ao_cancelar=None, slot=None):
        super().__init__(app)
        self.modo = modo
        self.ao_terminar = ao_terminar
        self.ao_cancelar = ao_cancelar or ao_terminar
        self.slot = app.slot if slot is None else slot
        self.pode_cancelar = modo in ("trocar", "novo")
        self.erro = ""
        self.texto = self.jogador.nome if modo == "trocar" else ""
        self.fundo = FundoAnimado((30, 110, 50), (90, 190, 90), semente=3)
        self.tempo = 0.0
        self.tremer = 0.0

        self.caixa = pygame.Rect(0, 0, 520, 72)
        self.caixa.center = (LARGURA // 2, 330)

        self.botao_ok = ui.Botao((0, 0, 260, 60), "CONFIRMAR", 18)
        self.botao_ok.rect.center = (LARGURA // 2 + (145 if self.pode_cancelar else 0), 460)

        self.botao_cancelar = ui.Botao((0, 0, 260, 60), "CANCELAR", 18,
                                       cor=(110, 60, 60), cor_hover=(160, 80, 80))
        self.botao_cancelar.rect.center = (LARGURA // 2 - 145, 460)

    # --------------------------------------------------------

    def entrar(self):
        super().entrar()
        pygame.key.start_text_input()

    def sair(self):
        pygame.key.stop_text_input()

    def _valido(self, c):
        """Aceita só caracteres visíveis que existem na fonte."""
        return c.isprintable() and c not in "\t\r\n"

    def _confirmar(self):
        nome = self.texto.strip()

        if not nome:
            self.tremer = 0.4
            self.som("erro")
            return

        if perfis.normalizar_nome(nome) in perfis.nomes_em_uso(excluir=self.slot):
            self.tremer = 0.4
            self.erro = t("JÁ TEM UM {nome} NA RUA!", nome=nome.upper())
            self.som("erro")
            return

        self.som("selecionar")
        self.jogador.nome = nome
        self.jogador.salvar()

        if self.ao_terminar:
            self.ao_terminar()

    def _cancelar(self):
        self.som("voltar")
        if self.ao_cancelar:
            self.ao_cancelar()

    # --------------------------------------------------------

    def evento(self, e):
        if e.type == pygame.TEXTINPUT:
            for c in e.text:
                if self._valido(c) and len(self.texto) < LIMITE_NOME:
                    self.texto += c
                    self.erro = ""
                    self.som("revelar", 0.6)

        elif e.type == pygame.KEYDOWN:
            if e.key == pygame.K_BACKSPACE:
                self.texto = self.texto[:-1]
                self.erro = ""
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._confirmar()
            elif tecla_voltar(e) and self.pode_cancelar:
                self._cancelar()

        if self.botao_ok.evento(e):
            self._confirmar()
        elif self.pode_cancelar and self.botao_cancelar.evento(e):
            self._cancelar()

    def atualizar(self, dt):
        self.tempo += dt
        self.tremer = max(0.0, self.tremer - dt)
        self.fundo.atualizar(dt)
        self.botao_ok.atualizar(dt)
        self.botao_cancelar.atualizar(dt)

    def desenhar(self, tela):
        self.fundo.desenhar(tela)

        if self.modo == "inicial":
            y = 90 + math.sin(self.tempo * 2) * 6
            ui.desenhar_texto(tela, t("BEM-VINDO AO"), (LARGURA // 2, y), 28,
                              BRANCO, "midtop")
            ui.desenhar_texto(tela, "OVAL!", (LARGURA // 2, y + 48), 56,
                              AMARELO, "midtop")
            ui.centralizado(tela, t("Como vai se chamar o seu ovo?"), 240, 16)
        elif self.modo == "novo":
            y = 100 + math.sin(self.tempo * 2) * 6
            ui.desenhar_texto(tela, t("NOME DO NOVO OVO"), (LARGURA // 2, y), 36, AMARELO, "midtop")
            ui.centralizado(tela, t("ELE VAI MORAR NA CASA {n}", n=self.slot + 1), 190, 12)
            ui.centralizado(tela, t("Como vai se chamar o novo ovo?"), 240, 16)
        else:
            ui.centralizado(tela, t("TROCAR NOME"), 110, 40, AMARELO)
            ui.centralizado(tela, t("Digite o novo nome:"), 240, 16)

        # Caixa de texto (treme quando tenta confirmar vazio)
        caixa = self.caixa.move(int(math.sin(self.tempo * 60) * 8 * self.tremer / 0.4), 0)
        ui.painel(tela, caixa, BRANCO, (40, 40, 60), 14, 4)

        superficie = ui.texto(self.texto, 24, (30, 30, 40), sombra=False)
        rect = superficie.get_rect(midleft=(caixa.x + 22, caixa.centery))
        tela.blit(superficie, rect)

        # Cursor piscando
        if int(self.tempo * 2) % 2 == 0:
            x = rect.right + 4 if self.texto else caixa.x + 22
            pygame.draw.rect(tela, (30, 30, 40), (x, caixa.centery - 14, 4, 28))

        ui.desenhar_texto(tela, f"{len(self.texto)}/{LIMITE_NOME}",
                          (caixa.right, caixa.bottom + 12), 12, BRANCO, "topright")

        if self.erro:
            ui.centralizado(tela, self.erro, 396, 12, (230, 70, 70))

        self.botao_ok.desenhar(tela)

        if self.pode_cancelar:
            self.botao_cancelar.desenhar(tela)
            ui.centralizado(tela, t("ENTER confirma  •  ESC cancela"), 640, 12)
        else:
            ui.centralizado(tela, t("Aperte ENTER para continuar"), 640, 12)
