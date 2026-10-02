import math
import random

import pygame

from settings import *
from core.idioma import t as tr
from core import eventos, progresso, ui

# ============================================================
# EVENTOS NA CASA
# ============================================================
# - CAÇA AOS OVINHOS (Páscoa): 6 ovinhos pintados escondidos no
#   SOL (lugares sorteados pelo dia). Cada um vale OVOEDAS; achar
#   todos no mesmo dia libera a conquista CAÇADOR DE OVOS.
# - FAIXA do evento / fim de semana no topo da casa.

QTD_OVINHOS = 6
MOEDAS_OVINHO = 6
LUGARES = [(120, 470), (260, 520), (380, 455), (560, 520), (640, 460), (820, 505), (930, 470),
           (190, 600), (470, 610), (720, 600), (880, 615), (330, 585)]
CORES = [(255, 120, 170), (120, 200, 255), (255, 220, 80), (150, 230, 120), (200, 140, 255),
         (255, 160, 90)]

_sprites = {}


def _ovinho(cor):
    s = _sprites.get(cor)
    if s is None:
        s = pygame.Surface((26, 32), pygame.SRCALPHA)
        pygame.draw.ellipse(s, cor, (1, 1, 24, 30))
        clara = tuple(min(255, c + 70) for c in cor)
        escura = tuple(max(0, c - 70) for c in cor)
        pygame.draw.line(s, clara, (3, 13), (23, 13), 3)
        for x in (7, 13, 19):
            pygame.draw.circle(s, BRANCO, (x, 21), 2)
        pygame.draw.ellipse(s, escura, (1, 1, 24, 30), 2)
        pygame.draw.ellipse(s, (255, 255, 255, 170), (6, 5, 6, 8))
        _sprites[cor] = s
    return s


class CacaOvos:

    def __init__(self, ctx):
        self.ctx = ctx

    def _estado(self):
        save = self.ctx.app.save
        d = save["diario"]
        dia = eventos.hoje().isoformat()
        if d.get("pascoa_dia") != dia:
            d["pascoa_dia"] = dia
            d["pascoa_achados"] = []
        return d

    def ovinhos(self):
        """[(indice, pos, cor)] ainda escondidos hoje."""
        if eventos.sazonal() != "pascoa":
            return []
        d = self._estado()
        rnd = random.Random("pascoa" + d["pascoa_dia"])
        lugares = rnd.sample(LUGARES, QTD_OVINHOS)
        return [(i, pos, CORES[i % len(CORES)]) for i, pos in enumerate(lugares)
                if i not in d["pascoa_achados"]]

    def clicar(self, pos):
        if self.ctx.comodo != "SOL":
            return False
        for i, (x, y), cor in self.ovinhos():
            if math.hypot(pos[0] - x, pos[1] - y) < 24:
                d = self._estado()
                d["pascoa_achados"].append(i)
                self.ctx.ganhar_moedas(MOEDAS_OVINHO, (x, y))
                self.ctx.particulas.explodir((x, y), [cor, BRANCO, AMARELO], 24, 260)
                self.ctx.som("acerto")
                faltam = QTD_OVINHOS - len(d["pascoa_achados"])
                if faltam:
                    self.ctx.avisar(tr("OVINHO DE PÁSCOA! Faltam {n} hoje.", n=faltam))
                else:
                    self.ctx.avisar("ACHOU TODOS OS OVINHOS DE HOJE!")
                    progresso.definir(self.ctx.app, "pascoa", 1)
                self.ctx.app.save.salvar()
                return True
        return False

    def desenhar(self, tela):
        if self.ctx.comodo != "SOL":
            return
        t = self.ctx.tempo
        for i, (x, y), cor in self.ovinhos():
            s = _ovinho(cor)
            balanca = math.sin(t * 3 + i) * 6
            rot = pygame.transform.rotate(s, balanca) if abs(balanca) > 1 else s
            tela.blit(rot, rot.get_rect(midbottom=(x, y + 16)))
            if int(t * 2 + i) % 5 == 0:
                ui.estrela(tela, (x + 12, y - 14), 5, (255, 250, 200), t)


def desenhar_faixa(tela, y=0):
    """Faixinha do evento ativo (se houver) no topo da tela."""
    texto = eventos.faixa()
    if not texto:
        return
    sup = ui.texto(texto, 8, (30, 20, 20), sombra=False)
    r = sup.get_rect(midtop=(LARGURA // 2, y)).inflate(24, 8)
    pygame.draw.rect(tela, eventos.cor_faixa(), r, border_bottom_left_radius=8,
                     border_bottom_right_radius=8)
    tela.blit(sup, sup.get_rect(center=r.center))
