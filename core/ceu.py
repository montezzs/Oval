import math
import random

import pygame

from core import ui

# ============================================================
# CÉU (tela inicial, vizinhança, reforma)
# ============================================================
# Gradiente pela fase do dia (mesma regra do Clima: relógio real
# ou SEMPRE DIA), sol girando, lua, estrelas piscando e nuvens.

CORES_CEU = {
    "dia": ((120, 200, 255), (200, 235, 255)),
    "amanhecer": ((255, 190, 150), (255, 230, 200)),
    "por_do_sol": ((255, 140, 90), (255, 200, 150)),
    "noite": ((15, 20, 55), (40, 50, 100)),
}

_gradientes = {}


def gradiente(fase, largura, altura, nublado=False):
    chave = (fase, largura, altura, nublado)
    sup = _gradientes.get(chave)
    if sup is None:
        topo, base = CORES_CEU.get(fase, CORES_CEU["dia"])
        if nublado:
            topo = ui.misturar(topo, (150, 160, 175), 0.45)
            base = ui.misturar(base, (190, 195, 205), 0.45)
        sup = ui.gradiente(largura, altura, topo, base)
        _gradientes[chave] = sup
    return sup


class Nuvens:

    def __init__(self, n, y_min, y_max, largura=1024, semente=7, escala=1.0):
        rnd = random.Random(semente)
        self.largura = largura
        self.itens = []
        for _ in range(n):
            larg = int(rnd.randint(110, 200) * escala)
            sup = pygame.Surface((larg, larg // 2), pygame.SRCALPHA)
            for _ in range(6):
                r = rnd.randint(larg // 7, larg // 4)
                cx = rnd.randint(r, larg - r)
                cy = rnd.randint(larg // 4, max(larg // 4 + 1, larg // 2 - r // 2))
                pygame.draw.circle(sup, (245, 248, 255, 235), (cx, cy), r)
            self.itens.append([sup, rnd.uniform(-larg, largura), rnd.uniform(y_min, y_max),
                               rnd.uniform(8, 20)])
        self._cinzas = None

    def atualizar(self, dt, vento=0.3):
        for n in self.itens:
            n[1] += n[3] * dt * (0.6 + vento)
            if n[1] > self.largura + 20:
                n[1] = -n[0].get_width() - 20

    def desenhar(self, tela, cinza=False):
        if cinza and self._cinzas is None:
            self._cinzas = []
            for sup, *_ in self.itens:
                c = sup.copy()
                c.fill((200, 205, 215, 255), special_flags=pygame.BLEND_RGBA_MULT)
                self._cinzas.append(c)
        for i, (sup, x, y, _) in enumerate(self.itens):
            tela.blit(self._cinzas[i] if cinza else sup, (x, y))


class Ceu:
    """Estrelas, sol e lua (o gradiente vem de `gradiente`)."""

    def __init__(self, largura=1024, altura_estrelas=300, semente=11):
        rnd = random.Random(semente)
        self.estrelas = [(rnd.randrange(largura), rnd.randrange(altura_estrelas),
                          rnd.uniform(0, 6.28), rnd.choice([1, 1, 2])) for _ in range(60)]

    def desenhar(self, tela, fase, t, sol=(140, 110), lua=(880, 90), nublado=False):
        if fase == "noite":
            for x, y, f, r in self.estrelas:
                brilho = 150 + int(100 * math.sin(t * 2 + f))
                pygame.draw.circle(tela, (brilho, brilho, min(255, brilho + 30)), (x, y), r)
            topo = CORES_CEU["noite"][0]
            pygame.draw.circle(tela, (240, 240, 210), lua, 26)
            pygame.draw.circle(tela, ui.misturar(topo, CORES_CEU["noite"][1], 0.3),
                               (lua[0] + 10, lua[1] - 6), 23)
        elif not nublado:
            cx, cy = sol
            cor = (255, 220, 80) if fase == "dia" else (255, 190, 90)
            for i in range(8):
                a = math.radians(t * 10 + i * 45)
                pygame.draw.line(tela, cor, (cx + math.cos(a) * 50, cy + math.sin(a) * 50),
                                 (cx + math.cos(a) * 66, cy + math.sin(a) * 66), 5)
            pygame.draw.circle(tela, cor, sol, 40)
            pygame.draw.circle(tela, ui.clarear(cor, 30), (cx - 10, cy - 10), 14)
