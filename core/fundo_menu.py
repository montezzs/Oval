import math
import random

import pygame

from settings import *
from core import assets
from core.ui import gradiente

# ============================================================
# FUNDO ANIMADO DOS MENUS
# ============================================================
# Gradiente + ovinhos flutuando devagar. O gradiente é criado
# uma única vez; por frame só movemos os ovinhos.


class FundoAnimado:

    def __init__(self, cor_topo=(60, 140, 220), cor_base=(120, 200, 255),
                 qtd=14, semente=1):
        self.base = gradiente(LARGURA, ALTURA, cor_topo, cor_base)
        rnd = random.Random(semente)
        self.ovos = []

        for _ in range(qtd):
            escala = rnd.uniform(0.35, 0.8)
            img = assets.OVOS[rnd.randrange(len(assets.OVOS))]
            img = pygame.transform.smoothscale(
                img, (int(100 * escala), int(100 * escala)))
            img.set_alpha(70)
            self.ovos.append([
                img,
                rnd.uniform(0, LARGURA),
                rnd.uniform(0, ALTURA),
                rnd.uniform(12, 30) * escala,      # velocidade de subida
                rnd.uniform(0, math.tau),          # fase do balanço
            ])

        self.tempo = 0.0

    def atualizar(self, dt):
        self.tempo += dt

        for ovo in self.ovos:
            ovo[2] -= ovo[3] * dt
            if ovo[2] < -110:
                ovo[2] = ALTURA + 10
                ovo[1] = random.uniform(0, LARGURA)

    def desenhar(self, tela):
        tela.blit(self.base, (0, 0))

        for img, x, y, _, fase in self.ovos:
            dx = math.sin(self.tempo * 0.8 + fase) * 18
            tela.blit(img, (x + dx, y))
