import pygame

from settings import *
from core import ui

# ============================================================
# JUKEBOX (vitrola da casa)
# ============================================================
# Toca o tema da casa, os TEMAS do jogo (tela inicial, rua, loja...
# liberados quando ouvidos pela 1ª vez) ou a trilha de qualquer
# mini jogo que o jogador já jogou pelo menos uma vez.

POR_PAGINA = 8


class Jukebox:

    def __init__(self, ctx):
        self.ctx = ctx
        self.aberta = False
        self.indice = 0
        self.rects = []
        self.inicio = 0

    def faixas(self):
        """[(id, nome, estilo, bloqueada, dica)]"""
        from core import trilhas
        from jogos import JOGOS
        jogados = set(self.ctx.app.save["jogados"])
        ouvidos = set(self.ctx.app.config["temas_ouvidos"])
        lista = [("ovein", trilhas.NOMES_TEMAS["ovein"], None, False, "")]
        for tid in trilhas.TEMAS:
            bloqueada = tid not in ouvidos
            lista.append((tid, trilhas.NOMES_TEMAS.get(tid, tid.upper()), None, bloqueada,
                          trilhas.DICAS_TEMAS.get(tid, "DICA: EXPLORE O JOGO")))
        for jogo in JOGOS:
            if jogo.ID in jogados:
                lista.append((jogo.ID, jogo.TITULO, getattr(jogo, "TRILHA", None), False, ""))
        return lista

    def abrir(self):
        self.aberta = True
        self.ctx.som("selecionar")

    def _tocar(self, faixa):
        fid, _, estilo, bloqueada, _ = faixa
        if bloqueada:
            self.ctx.som("erro")
            return
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
        for k, (fid, nome, _, bloqueada, dica) in enumerate(lista[self.inicio:self.inicio + POR_PAGINA]):
            i = self.inicio + k
            r = pygame.Rect(caixa.x + 24, caixa.y + 70 + k * 50, caixa.w - 48, 42)
            self.rects.append((i, r))
            sel = i == self.indice
            pygame.draw.rect(tela, (100, 60, 40) if sel else (70, 40, 30), r, border_radius=10)
            if sel:
                pygame.draw.rect(tela, AMARELO, r, 2, border_radius=10)
            tocando = fid == atual
            if bloqueada:
                ui.desenhar_texto(tela, "   ???", (r.x + 14, r.centery), 12, (150, 120, 100), "midleft")
                ui.desenhar_texto(tela, dica, (r.right - 12, r.centery), 8, (200, 170, 130), "midright")
                continue
            tam = ui.tamanho_que_cabe(nome, r.w - 60, (12, 10, 8))
            ui.desenhar_texto(tela, ("▶ " if tocando else "   ") + nome, (r.x + 14, r.centery), tam,
                              AMARELO if tocando else BRANCO, "midleft")
        liberadas = sum(1 for f in lista if not f[3]) - 1
        ui.desenhar_texto(tela, f"{liberadas} trilhas liberadas • jogue e explore para liberar mais!",
                          (caixa.centerx, caixa.bottom - 28), 8, (230, 200, 160), "midtop")
