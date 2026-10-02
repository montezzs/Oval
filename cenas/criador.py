import math
import random

import pygame

from settings import *
from core.idioma import t
from core import assets, ui
from core.cena import Cena, tecla_voltar
from core.fundo_menu import FundoAnimado

# ============================================================
# CRIADOR DE PERSONAGEM
# ============================================================
# Escolher ovo, cabelo, olhos e boca numa tela só.
#   ↑ ↓   escolhe a linha
#   ← →   troca a opção
#   ENTER avança / confirma
# Modo "inicial": depois de confirmar vai para a casa.
# Modo "editar": tem CANCELAR e volta para quem chamou.
# Modo "novo": ovo novo da vizinhança (ESC volta para o nome).

LINHAS = [
    ("ovo", "OVO"),
    ("cabelo", "CABELO"),
    ("olho", "OLHOS"),
    ("boca", "BOCA"),
]


class CenaCriador(Cena):

    musica = "nasce_um_ovo"

    def __init__(self, app, modo="inicial", ao_terminar=None, ao_cancelar=None):
        super().__init__(app)
        self.modo = modo
        self.ao_terminar = ao_terminar
        self.ao_cancelar = ao_cancelar
        # No criador só as partes básicas (os extras da loja ficam de fora)
        self.jogador.usar_extras = False
        self.original = self.jogador.aparencia()
        self.valores = list(self.original)
        self.linha = 0
        self.tempo = 0.0
        self.pulo = 0.0
        self.fundo = FundoAnimado((40, 90, 170), (110, 180, 240), semente=5)
        self.particulas = ui.Particulas()

        # Painel da direita
        self.painel = pygame.Rect(520, 150, 450, 470)
        self.setas = []

        for i in range(len(LINHAS)):
            y = self.painel.y + 40 + i * 82
            esq = pygame.Rect(self.painel.x + 160, y, 44, 44)
            dir_ = pygame.Rect(self.painel.right - 64, y, 44, 44)
            linha = pygame.Rect(self.painel.x + 12, y - 8, self.painel.w - 24, 60)
            self.setas.append((esq, dir_, linha))

        base_y = self.painel.y + 380
        if modo in ("inicial", "novo"):
            self.botoes = [ui.Botao((0, 0, 200, 56), "SORTEAR", 16,
                                    cor=(90, 70, 150), cor_hover=(130, 100, 200)),
                           ui.Botao((0, 0, 200, 56), "PRONTO!", 16,
                                    cor=(50, 130, 70), cor_hover=(70, 180, 100))]
        else:
            self.botoes = [ui.Botao((0, 0, 200, 56), "CANCELAR", 16,
                                    cor=(120, 60, 60), cor_hover=(170, 80, 80)),
                           ui.Botao((0, 0, 200, 56), "SALVAR", 16,
                                    cor=(50, 130, 70), cor_hover=(70, 180, 100))]

        self.botoes[0].rect.topleft = (self.painel.x + 16, base_y)
        self.botoes[1].rect.topright = (self.painel.right - 16, base_y)

        self._aplicar()

    # --------------------------------------------------------

    def _tamanho(self, i):
        return len(self.jogador.listas()[LINHAS[i][0]])

    def _aplicar(self):
        self.jogador.definir_aparencia(*self.valores)

    def _mudar(self, i, direcao):
        self.linha = i
        self.valores[i] = (self.valores[i] + direcao) % self._tamanho(i)
        self._aplicar()
        self.pulo = 1.0
        self.som("clique")

    def _sortear(self):
        self.valores = [random.randrange(self._tamanho(i)) for i in range(len(LINHAS))]
        self._aplicar()
        self.pulo = 1.0
        self.som("boing")
        self.particulas.explodir((260, 330), [AMARELO, BRANCO, self.jogador.cor], 30, 320)

    def _confirmar(self):
        self.jogador.usar_extras = True
        self.som("vencer")
        self.jogador.salvar()
        if self.ao_terminar:
            self.ao_terminar()

    def _cancelar(self):
        self.jogador.usar_extras = True
        self.som("voltar")
        self.jogador.definir_aparencia(*self.original)
        if self.ao_terminar:
            self.ao_terminar()

    # --------------------------------------------------------

    def evento(self, e):
        if e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_UP, pygame.K_w):
                self.linha = (self.linha - 1) % len(LINHAS)
                self.som("clique", 0.5)
            elif e.key in (pygame.K_DOWN, pygame.K_s):
                self.linha = (self.linha + 1) % len(LINHAS)
                self.som("clique", 0.5)
            elif e.key in (pygame.K_LEFT, pygame.K_a):
                self._mudar(self.linha, -1)
            elif e.key in (pygame.K_RIGHT, pygame.K_d):
                self._mudar(self.linha, 1)
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if self.linha < len(LINHAS) - 1:
                    self.linha += 1
                    self.som("selecionar")
                else:
                    self._confirmar()
            elif tecla_voltar(e) and self.modo == "editar":
                self._cancelar()
            elif tecla_voltar(e) and self.modo == "novo" and self.ao_cancelar:
                self.som("voltar")
                self.ao_cancelar()

        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for i, (esq, dir_, linha) in enumerate(self.setas):
                if esq.collidepoint(e.pos):
                    self._mudar(i, -1)
                elif dir_.collidepoint(e.pos):
                    self._mudar(i, 1)
                elif linha.collidepoint(e.pos):
                    self.linha = i

            if self.botoes[1].evento(e):
                self._confirmar()
            elif self.botoes[0].evento(e):
                if self.modo in ("inicial", "novo"):
                    self._sortear()
                else:
                    self._cancelar()

        elif e.type == pygame.MOUSEWHEEL:
            self._mudar(self.linha, -1 if e.y > 0 else 1)

    def atualizar(self, dt):
        self.tempo += dt
        self.pulo = max(0.0, self.pulo - dt * 3)
        self.fundo.atualizar(dt)
        self.particulas.atualizar(dt)
        for b in self.botoes:
            b.atualizar(dt)

    # --------------------------------------------------------

    def _nome_opcao(self, i):
        v = self.valores[i]
        if LINHAS[i][0] == "ovo":
            return t(assets.NOMES_OVOS[v])
        return t("{n} de {total}", n=v + 1, total=self._tamanho(i))

    def desenhar(self, tela):
        self.fundo.desenhar(tela)

        titulo = t("CRIE SEU OVO!") if self.modo in ("inicial", "novo") else t("TROCAR APARÊNCIA")
        ui.centralizado(tela, titulo, 50, 36, AMARELO)
        if self.jogador.nome:
            ui.centralizado(tela, self.jogador.nome, 104, 16)

        # ---------------- Personagem grande ----------------
        centro = (260, 390)
        pygame.draw.ellipse(tela, (20, 40, 80), (centro[0] - 120, 540, 240, 40))
        pygame.draw.ellipse(tela, (60, 100, 170), (centro[0] - 110, 534, 220, 36))

        salto = abs(math.sin(self.pulo * math.pi)) * 40
        balanco = math.sin(self.tempo * 2.5) * 5
        self.jogador.desenhar(tela, (centro[0], 552 - 130 - salto + balanco), 260)
        self.particulas.desenhar(tela)

        # ---------------- Painel de opções ----------------
        ui.painel(tela, self.painel, (30, 40, 80), BRANCO, 18, 4)

        for i, (chave, rotulo) in enumerate(LINHAS):
            esq, dir_, linha = self.setas[i]
            ativa = (i == self.linha)

            if ativa:
                pygame.draw.rect(tela, (70, 90, 160), linha, border_radius=12)
                pygame.draw.rect(tela, UI_DESTAQUE, linha, 3, border_radius=12)

            cor = AMARELO if ativa else BRANCO
            ui.desenhar_texto(tela, t(rotulo), (linha.x + 16, linha.centery), 16, cor, "midleft")

            for seta, simbolo in ((esq, "<"), (dir_, ">")):
                hover = seta.collidepoint(pygame.mouse.get_pos())
                pygame.draw.rect(tela, (110, 130, 210) if hover else (70, 80, 140),
                                 seta, border_radius=10)
                pygame.draw.rect(tela, BRANCO, seta, 2, border_radius=10)
                ui.desenhar_texto(tela, simbolo, seta.center, 18, BRANCO, "center")

            meio = (esq.right + dir_.left) // 2
            if chave == "ovo":
                pygame.draw.circle(tela, self.jogador.cor, (meio - 70, linha.centery), 9)
                pygame.draw.circle(tela, BRANCO, (meio - 70, linha.centery), 9, 2)
            ui.desenhar_texto(tela, self._nome_opcao(i), (meio + (10 if chave == "ovo" else 0),
                              linha.centery), 14, cor, "center")

        for b in self.botoes:
            b.desenhar(tela)

        dica = t("↑ ↓ escolhe   ← → troca   ENTER avança")
        if self.modo == "novo":
            dica += t("   ESC volta")
        ui.centralizado(tela, dica, 660, 12)
