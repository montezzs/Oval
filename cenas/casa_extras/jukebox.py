import pygame

from settings import *
from core import ui

# ============================================================
# JUKEBOX (vitrola da casa)
# ============================================================
# Toca o tema da casa ou a trilha de qualquer mini jogo que o
# jogador já jogou pelo menos uma vez.

POR_PAGINA = 8


class Jukebox:

    def __init__(self, ctx):
        self.ctx = ctx
        self.aberta = False
        self.indice = 0
        self.rects = []
        self.inicio = 0

    def faixas(self):
        from jogos import JOGOS
        jogados = set(self.ctx.app.save["jogados"])
        lista = [("ovein", "TEMA DO OVEIO", None)]
        for jogo in JOGOS:
            if jogo.ID in jogados:
                lista.append((jogo.ID, jogo.TITULO, getattr(jogo, "TRILHA", None)))
        return lista

    def abrir(self):
        self.aberta = True
        self.ctx.som("selecionar")

    def _tocar(self, faixa):
        fid, _, estilo = faixa
        if estilo:
            from core import trilhas
            trilhas.registrar(fid, estilo)
        self.ctx.definir_faixa(fid)
        self.ctx.som("clique")

    def evento(self, e):
        if not self.aberta:
            return False
        lista = self.faixas()
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                self.aberta = False
            elif e.key in (pygame.K_UP, pygame.K_w):
                self.indice = (self.indice - 1) % len(lista)
            elif e.key in (pygame.K_DOWN, pygame.K_s):
                self.indice = (self.indice + 1) % len(lista)
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self._tocar(lista[self.indice])
            return True
        if e.type == pygame.MOUSEWHEEL:
            self.indice = max(0, min(len(lista) - 1, self.indice - e.y))
            return True
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for i, r in self.rects:
                if r.collidepoint(e.pos):
                    self.indice = i
                    self._tocar(lista[i])
                    return True
            self.aberta = False
            return True
        return e.type in (pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION)

    def desenhar(self, tela):
        self.rects = []
        if not self.aberta:
            return
        lista = self.faixas()
        self.indice = min(self.indice, len(lista) - 1)
        if self.indice < self.inicio:
            self.inicio = self.indice
        elif self.indice >= self.inicio + POR_PAGINA:
            self.inicio = self.indice - POR_PAGINA + 1

        ui.veu(tela, 150)
        caixa = pygame.Rect(0, 0, 560, 520)
        caixa.center = (LARGURA // 2, ALTURA // 2)
        ui.painel(tela, caixa, (40, 24, 20), (230, 170, 90), 18, 4)
        ui.desenhar_texto(tela, "♪ JUKEBOX ♪", (caixa.centerx, caixa.y + 18), 22, AMARELO, "midtop")
        atual = self.ctx.faixa
        for k, (fid, nome, _) in enumerate(lista[self.inicio:self.inicio + POR_PAGINA]):
            i = self.inicio + k
            r = pygame.Rect(caixa.x + 24, caixa.y + 70 + k * 50, caixa.w - 48, 42)
            self.rects.append((i, r))
            sel = i == self.indice
            pygame.draw.rect(tela, (100, 60, 40) if sel else (70, 40, 30), r, border_radius=10)
            if sel:
                pygame.draw.rect(tela, AMARELO, r, 2, border_radius=10)
            tocando = fid == atual
            ui.desenhar_texto(tela, ("▶ " if tocando else "   ") + nome, (r.x + 14, r.centery), 12,
                              AMARELO if tocando else BRANCO, "midleft")
        ui.desenhar_texto(tela, f"{len(lista) - 1} trilhas desbloqueadas • jogue mais para liberar!",
                          (caixa.centerx, caixa.bottom - 28), 8, (230, 200, 160), "midtop")
