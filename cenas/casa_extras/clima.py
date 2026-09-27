import math
import random
import time

import pygame

from settings import *
from core import ui

# ============================================================
# DIA / NOITE E CLIMA
# ============================================================
# - Hora do dia segue o relógio de verdade (ou "SEMPRE DIA").
# - O clima é sorteado a cada 20 minutos reais, de forma
#   determinística (o mesmo bloco de tempo dá sempre o mesmo
#   clima, então fechar e abrir o jogo não "troca" a chuva).
# - Depois de uma chuva aparece um ARCO-ÍRIS por 3 minutos com
#   um pote de ouro (+15 OVOEDAS, uma vez por arco-íris).

BLOCO_CLIMA = 20 * 60
DURACAO_ARCO = 3 * 60

# Vidros da janela grande do cômodo CASA (na imagem de fundo)
VIDROS_CASA = [
    pygame.Rect(598, 82, 158, 92),
    pygame.Rect(818, 82, 172, 94),
    pygame.Rect(604, 220, 158, 116),
    pygame.Rect(816, 222, 188, 114),
]
AREA_JANELA = pygame.Rect(580, 60, 440, 300)
COR_VIDRO = (0, 187, 255)

_mascara = None


def mascara_vidro():
    """Máscara com só os pixels azuis do vidro (a janela é desenhada à mão)."""
    global _mascara
    if _mascara is None:
        from core import assets
        fundo = assets.FUNDOS["casa"].subsurface(AREA_JANELA)
        _mascara = pygame.mask.from_threshold(fundo, COR_VIDRO, (30, 30, 30, 255))
    return _mascara

POTE = pygame.Rect(944, 548, 60, 50)

VEUS = {
    "amanhecer": ((255, 170, 120), 50),
    "por_do_sol": ((255, 120, 80), 70),
    "noite": ((20, 30, 80), 150),
}

CEU_JANELA = {
    "amanhecer": (255, 190, 150),
    "dia": None,
    "por_do_sol": (255, 140, 90),
    "noite": (20, 30, 70),
}


def _clima_do_bloco(bloco):
    r = random.Random(bloco * 7919 + 13).random()
    if r < 0.65:
        return "sol"
    if r < 0.85:
        return "nublado"
    return "chuva"


class Clima:

    def __init__(self, save):
        self.save = save
        self.tempo = 0.0
        rnd = random.Random(5)
        self.estrelas = [(rnd.randrange(LARGURA), rnd.randrange(430), rnd.uniform(0, 6.28),
                          rnd.choice([1, 1, 2])) for _ in range(60)]
        self.gotas = [[rnd.uniform(0, LARGURA), rnd.uniform(0, ALTURA), rnd.uniform(560, 760)]
                      for _ in range(150)]
        self.pocas = [(rnd.randint(40, 980), rnd.randint(600, 700), rnd.randint(50, 110))
                      for _ in range(6)]
        self._arco = None
        self._atualizar_estado()

    # --------------------------------------------------------
    # ESTADO
    # --------------------------------------------------------

    def _atualizar_estado(self):
        agora = time.time()
        bloco = int(agora // BLOCO_CLIMA)
        self.bloco = bloco
        self.tipo = _clima_do_bloco(bloco)
        dentro = agora - bloco * BLOCO_CLIMA
        self.arco_iris = (self.tipo != "chuva" and _clima_do_bloco(bloco - 1) == "chuva"
                          and dentro < DURACAO_ARCO)

        if self.save["sempre_dia"]:
            self.fase = "dia"
        else:
            h = time.localtime(agora).tm_hour
            if 6 <= h < 7:
                self.fase = "amanhecer"
            elif 7 <= h < 18:
                self.fase = "dia"
            elif 18 <= h < 19:
                self.fase = "por_do_sol"
            else:
                self.fase = "noite"

    @property
    def noite(self):
        return self.fase == "noite"

    @property
    def chovendo(self):
        return self.tipo == "chuva"

    @property
    def vento(self):
        return {"sol": 0.2, "nublado": 0.5, "chuva": 1.0}[self.tipo]

    def pote_disponivel(self):
        return self.arco_iris and self.save["diario"].get("pote") != self.bloco

    def pegar_pote(self):
        self.save["diario"]["pote"] = self.bloco
        self.save.salvar()

    def atualizar(self, dt):
        self.tempo += dt
        # O estado muda devagar: basta recalcular de vez em quando
        if int(self.tempo * 2) != int((self.tempo - dt) * 2):
            self._atualizar_estado()
        if self.chovendo:
            for g in self.gotas:
                g[1] += g[2] * dt
                g[0] -= g[2] * 0.25 * dt
                if g[1] > ALTURA:
                    g[1] = random.uniform(-40, 0)
                    g[0] = random.uniform(0, LARGURA + 200)

    # --------------------------------------------------------
    # DESENHO (cômodo SOL)
    # --------------------------------------------------------

    def fundo_sol(self, fundo):
        """
        Fundo do SOL já com clima, arco-íris e cor da hora do dia.
        Fica em cache por estado: assim é 1 blit só por frame (os
        véus transparentes de tela cheia são caros).
        """
        chave = (self.fase, self.tipo, self.arco_iris and not self.noite)
        if getattr(self, "_chave_fundo", None) != chave:
            sup = fundo.copy()
            if self.tipo in ("nublado", "chuva"):
                ui.veu(sup, 60 if self.tipo == "nublado" else 90, (90, 100, 120))
            if chave[2]:
                sup.blit(self._superficie_arco(), (0, 0))
            cor_alpha = VEUS.get(self.fase)
            if cor_alpha:
                ui.veu(sup, cor_alpha[1], cor_alpha[0])
            self._fundo_sol = sup
            self._chave_fundo = chave
        return self._fundo_sol

    def desenhar_ceu(self, tela):
        """Por cima do fundo (já colorido por fundo_sol), antes dos objetos."""
        if self.noite:
            for x, y, fase, r in self.estrelas:
                brilho = 150 + int(100 * math.sin(self.tempo * 2 + fase))
                pygame.draw.circle(tela, (brilho, brilho, min(255, brilho + 30)), (x, y), r)
            # Lua crescente
            pygame.draw.circle(tela, (240, 240, 210), (720, 170), 34)
            pygame.draw.circle(tela, (28, 40, 96), (736, 160), 30)
            # O SOL dorme de máscara
            pygame.draw.polygon(tela, (80, 90, 160), [(0, 0), (205, 0), (200, 44), (0, 50)])
            pygame.draw.line(tela, (60, 70, 130), (0, 26), (202, 22), 3)
            for i in range(3):
                fase_z = (self.tempo * 0.6 + i / 3) % 1
                ui.desenhar_texto(tela, "z", (220 + fase_z * 60 + i * 6, 70 - fase_z * 50),
                                  10 + i * 4, (230, 230, 255), "center")

    def desenhar_pote(self, tela):
        if not self.pote_disponivel() or self.noite:
            return
        r = POTE
        pygame.draw.ellipse(tela, (30, 30, 30), (r.x, r.y + 14, r.w, r.h - 14))
        pygame.draw.rect(tela, (40, 40, 40), (r.x + 4, r.y + 12, r.w - 8, 10), border_radius=4)
        for i in range(6):
            ui.moeda(tela, (r.x + 10 + i * 8, r.y + 10 - (i % 2) * 5), 7,
                     giro=abs(math.cos(self.tempo * 3 + i)))
        if int(self.tempo * 2) % 2 == 0:
            ui.estrela(tela, (r.right, r.y), 5, (255, 250, 200), self.tempo)

    def desenhar_chuva(self, tela):
        """Depois dos objetos: gotas caindo e poças."""
        if not self.chovendo:
            return
        for x, y, w in self.pocas:
            pygame.draw.ellipse(tela, (120, 150, 190), (x, y, w, 14))
            pygame.draw.ellipse(tela, (170, 200, 235), (x + 6, y + 3, w - 30, 5))
        for x, y, v in self.gotas:
            pygame.draw.line(tela, (170, 200, 255), (x, y), (x - 5, y + 16), 2)

    def _superficie_arco(self):
        if self._arco is None:
            s = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
            cores = [(255, 70, 70), (255, 160, 50), (255, 230, 60), (90, 210, 90),
                     (70, 150, 255), (90, 80, 200), (170, 90, 220)]
            for i, cor in enumerate(cores):
                raio = 390 - i * 9
                pygame.draw.circle(s, (*cor, 110), (620, 560), raio, 9)
            # Apaga a parte de baixo (arco só no céu)
            pygame.draw.rect(s, (0, 0, 0, 0), (0, 470, LARGURA, ALTURA - 470))
            self._arco = s
        return self._arco

    # --------------------------------------------------------
    # JANELA DO CÔMODO CASA
    # --------------------------------------------------------

    def _ceu_janela(self, cor):
        """Céu da janela (só nos pixels do vidro), com cache por cor."""
        if not hasattr(self, "_janelas"):
            self._janelas = {}
        sup = self._janelas.get(cor)
        if sup is None:
            mascara = mascara_vidro()
            sup = mascara.to_surface(setcolor=(*cor, 255), unsetcolor=(0, 0, 0, 0))
            if cor == CEU_JANELA["noite"]:
                rnd = random.Random(3)
                w, h = sup.get_size()
                for _ in range(40):
                    x, y = rnd.randrange(w), rnd.randrange(h)
                    if mascara.get_at((x, y)):
                        sup.set_at((x, y), (220, 220, 255, 255))
                # Lua crescente num dos vidros
                lua = pygame.Surface(sup.get_size(), pygame.SRCALPHA)
                pygame.draw.circle(lua, (240, 240, 210, 255), (110, 50), 16)
                pygame.draw.circle(lua, (*cor, 255), (118, 44), 14)
                lua.blit(mascara.to_surface(setcolor=(255, 255, 255, 255),
                                            unsetcolor=(0, 0, 0, 0)),
                         (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
                sup.blit(lua, (0, 0))
            self._janelas[cor] = sup
        return sup

    def desenhar_janela(self, tela):
        cor = CEU_JANELA.get(self.fase)
        if self.tipo == "chuva" and cor is None:
            cor = (120, 140, 170)
        if cor is not None:
            tela.blit(self._ceu_janela(cor), AREA_JANELA)
        if self.chovendo:
            for vidro in VIDROS_CASA:
                for i in range(8):
                    x = vidro.x + 6 + (i * 23 + int(self.tempo * 90)) % (vidro.w - 12)
                    y = vidro.y + 6 + (i * 37 + int(self.tempo * 300)) % max(1, vidro.h - 24)
                    pygame.draw.line(tela, (200, 220, 255), (x, y), (x - 2, y + 10), 1)
