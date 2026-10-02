import math

import pygame

from settings import *
from core import idioma, ui
from core.cena import Cena, tecla_voltar
from core.idioma import t

# ============================================================
# ESCOLHER IDIOMA
# ============================================================
# Aparece na 1ª abertura (config["idioma"] ainda None) e pelo botão
# IDIOMA das OPÇÕES. Ao escolher: aplica na hora, salva no config e
# chama `ao_escolher()`. Com `fundo` (uma cena), desenha ela por trás
# com um véu; sem fundo, usa o fundo animado dos menus.

OPCOES = ("pt", "en", "es")
CHAMADA = {"pt": "ESCOLHA O IDIOMA", "en": "CHOOSE YOUR LANGUAGE", "es": "ELIGE TU IDIOMA"}


def desenhar_bandeira(tela, rect, codigo):
    """Bandeirinha simples desenhada (sem imagem)."""
    r = pygame.Rect(rect)
    if codigo == "pt":
        pygame.draw.rect(tela, (0, 156, 59), r)
        cx, cy = r.center
        pygame.draw.polygon(tela, (255, 223, 0), [(cx, r.y + 4), (r.right - 5, cy),
                                                  (cx, r.bottom - 4), (r.x + 5, cy)])
        pygame.draw.circle(tela, (0, 39, 118), (cx, cy), r.h // 4)
        pygame.draw.line(tela, BRANCO, (cx - r.h // 4 + 1, cy - 1), (cx + r.h // 4 - 1, cy + 2), 2)
    elif codigo == "en":
        pygame.draw.rect(tela, (1, 33, 105), r)
        sup = pygame.Surface(r.size, pygame.SRCALPHA)
        w, h = r.size
        for cor, esp in ((BRANCO, 9), ((200, 16, 46), 3)):
            pygame.draw.line(sup, cor, (0, 0), (w, h), esp)
            pygame.draw.line(sup, cor, (0, h), (w, 0), esp)
        pygame.draw.rect(sup, BRANCO, (w // 2 - 7, 0, 14, h))
        pygame.draw.rect(sup, BRANCO, (0, h // 2 - 7, w, 14))
        pygame.draw.rect(sup, (200, 16, 46), (w // 2 - 4, 0, 8, h))
        pygame.draw.rect(sup, (200, 16, 46), (0, h // 2 - 4, w, 8))
        tela.blit(sup, r)
    else:
        pygame.draw.rect(tela, (170, 21, 27), r)
        pygame.draw.rect(tela, (241, 191, 0), (r.x, r.y + r.h // 4, r.w, r.h // 2))
    pygame.draw.rect(tela, (20, 20, 30), r, 3, border_radius=3)


class CenaEscolherIdioma(Cena):

    musica = "abertura"

    def __init__(self, app, ao_escolher, fundo=None):
        super().__init__(app)
        self.ao_escolher = ao_escolher
        self.fundo = fundo
        self.tempo = 0.0
        self.anim = None
        if fundo is None:
            from core.fundo_menu import FundoAnimado
            self.anim = FundoAnimado((52, 60, 120), (110, 150, 230), qtd=16, semente=7)
        else:
            self.musica = None
        self.menu = ui.Menu([idioma.NOMES[c] for c in OPCOES], LARGURA // 2, 270, 460, 84, 26, 22)
        for b in self.menu.botoes:
            b.rect.x += 40          # espaço para a bandeira à esquerda
        atual = app.config["idioma"]
        self.menu.indice = OPCOES.index(atual) if atual in OPCOES else 0
        self.pode_voltar = app.config["idioma"] is not None

    def evento(self, e):
        if self.pode_voltar and tecla_voltar(e):
            self.som("voltar")
            self.ao_escolher()
            return
        escolha = self.menu.evento(e)
        if escolha is not None:
            codigo = OPCOES[escolha]
            idioma.definir(codigo)
            self.app.config["idioma"] = codigo
            self.app.config.salvar()
            self.som("selecionar")
            self.ao_escolher()

    def atualizar(self, dt):
        self.tempo += dt
        if self.anim is not None:
            self.anim.atualizar(dt)
        elif hasattr(self.fundo, "atualizar"):
            self.fundo.atualizar(dt)
        self.menu.atualizar(dt)

    def desenhar(self, tela):
        if self.anim is not None:
            self.anim.desenhar(tela)
        else:
            self.fundo.desenhar(tela)
            ui.veu(tela, 170)

        caixa = pygame.Rect(0, 0, 640, 520)
        caixa.center = (LARGURA // 2, ALTURA // 2 + 10)
        ui.painel(tela, caixa, UI_FUNDO, UI_BORDA, 20, 4)

        # Globo girando + título (o título fica na língua em destaque)
        cx, cy = LARGURA // 2, caixa.y + 52
        pygame.draw.circle(tela, (70, 140, 220), (cx, cy), 22)
        larg = abs(math.cos(self.tempo * 1.5)) * 22
        pygame.draw.ellipse(tela, UI_BORDA, (cx - larg, cy - 22, 2 * larg, 44), 2)
        pygame.draw.line(tela, UI_BORDA, (cx - 22, cy), (cx + 22, cy), 2)
        pygame.draw.circle(tela, UI_BORDA, (cx, cy), 22, 3)
        foco = OPCOES[self.menu.indice]
        ui.desenhar_texto(tela, CHAMADA[foco], (LARGURA // 2, caixa.y + 96), 22, UI_DESTAQUE,
                          "midtop", True, True)
        ui.desenhar_texto(tela, "IDIOMA  •  LANGUAGE  •  IDIOMA", (LARGURA // 2, caixa.y + 138), 10,
                          UI_TEXTO_SUAVE, "midtop")

        self.menu.desenhar(tela)
        for codigo, b in zip(OPCOES, self.menu.botoes):
            r = pygame.Rect(0, 0, 72, 48)
            r.midright = (b.rect.x - 18, b.rect.centery)
            sobe = 4 if self.menu.botoes.index(b) == self.menu.indice else 0
            desenhar_bandeira(tela, r.move(0, -sobe), codigo)

        if self.pode_voltar:
            dica = t("SETAS + ENTER  •  ESC para voltar")
        else:   # 1ª vez: a dica acompanha a língua em destaque
            dica = {"pt": "SETAS + ENTER", "en": "ARROWS + ENTER", "es": "FLECHAS + ENTER"}[foco]
        ui.desenhar_texto(tela, dica, (LARGURA // 2, caixa.bottom - 22), 10, UI_TEXTO_SUAVE,
                          "midbottom")
