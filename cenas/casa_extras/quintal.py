import datetime
import math
import random

import pygame

from settings import *
from core.idioma import t as tr
from core import ui

# ============================================================
# QUINTAL: BORBOLETAS, ÁLBUM E BOLA DO PET
# ============================================================

ESPECIES = [
    ("laranja", "MONARCA", (255, 150, 50)),
    ("azul", "AZULÃO", (70, 150, 255)),
    ("amarela", "LIMÃOZINHA", (255, 225, 60)),
    ("rosa", "ROSINHA", (255, 120, 190)),
    ("verde", "FOLHINHA", (110, 210, 100)),
    ("roxa", "VIOLETA", (170, 100, 230)),
    ("branca", "NUVEM", (245, 245, 255)),
    ("dourada", "DOURADA RARA", (255, 205, 40)),
]
MAX_BORBOLETAS = 3
MOEDAS_BORBOLETA = 2
LIMITE_DIA = 10            # moedas por dia com borboletas


def _hoje():
    return datetime.date.today().isoformat()


class Borboleta:

    def __init__(self):
        dourada = random.random() < 0.05
        self.especie = 7 if dourada else random.randrange(7)
        self.x = random.choice([-30, LARGURA + 30])
        self.y = random.uniform(200, 460)
        self.alvo = (random.uniform(80, LARGURA - 80), random.uniform(180, 480))
        self.fase = random.uniform(0, 6.28)
        self.vel = random.uniform(70, 110)
        self.fugindo = False

    def atualizar(self, dt, t):
        dx, dy = self.alvo[0] - self.x, self.alvo[1] - self.y
        d = math.hypot(dx, dy)
        if d < 20:
            if self.fugindo:
                return False
            self.alvo = (random.uniform(80, LARGURA - 80), random.uniform(180, 480))
        else:
            self.x += dx / d * self.vel * dt
            self.y += dy / d * self.vel * dt + math.sin(t * 5 + self.fase) * 40 * dt
        return True

    @property
    def rect(self):
        return pygame.Rect(self.x - 22, self.y - 18, 44, 36)

    def desenhar(self, tela, t):
        cor = ESPECIES[self.especie][2]
        bater = abs(math.sin(t * 14 + self.fase))
        x, y = int(self.x), int(self.y)
        abre = 6 + 12 * bater
        contorno = (60, 40, 30)
        for lado in (-1, 1):
            cima = [(x, y), (x + lado * abre * 1.4, y - 14), (x + lado * abre * 1.2, y + 2)]
            baixo = [(x, y), (x + lado * abre, y + 12), (x + lado * abre * 0.5, y + 4)]
            pygame.draw.polygon(tela, cor, cima)
            pygame.draw.polygon(tela, contorno, cima, 1)
            pygame.draw.polygon(tela, ui.escurecer(cor, 30), baixo)
            pygame.draw.polygon(tela, contorno, baixo, 1)
        pygame.draw.line(tela, (50, 35, 25), (x, y - 6), (x, y + 8), 3)
        pygame.draw.line(tela, (50, 35, 25), (x, y - 6), (x - 4, y - 12), 1)
        pygame.draw.line(tela, (50, 35, 25), (x, y - 6), (x + 4, y - 12), 1)
        if self.especie == 7 and int(t * 6) % 2 == 0:
            ui.estrela(tela, (x + 10, y - 14), 4, (255, 250, 200), t)


class Borboletas:

    def __init__(self, ctx):
        self.ctx = ctx
        self.lista = []
        self.espera = 2.0
        self.album_aberto = False

    def _diario(self):
        d = self.ctx.app.save["diario"]
        if d.get("borboletas_dia") != _hoje():
            d["borboletas_dia"] = _hoje()
            d["borboletas_moedas"] = 0
        return d

    def pode_aparecer(self):
        return self.ctx.comodo == "SOL" and not self.ctx.noite and not self.ctx.chovendo

    def atualizar(self, dt):
        t = self.ctx.tempo
        if not self.pode_aparecer():
            for b in self.lista:
                if not b.fugindo:
                    b.fugindo = True
                    b.alvo = (-60 if b.x < LARGURA / 2 else LARGURA + 60, b.y - 100)
        else:
            self.espera -= dt
            if self.espera <= 0 and len(self.lista) < MAX_BORBOLETAS:
                self.lista.append(Borboleta())
                self.espera = random.uniform(6, 14)
        self.lista = [b for b in self.lista if b.atualizar(dt, t)]

    def clicar(self, pos):
        for b in self.lista:
            if not b.fugindo and b.rect.inflate(16, 16).collidepoint(pos):
                self._pegar(b)
                return True
        return False

    def _pegar(self, b):
        self.lista.remove(b)
        save = self.ctx.app.save
        diario = self._diario()
        chave, nome, cor = ESPECIES[b.especie]
        self.ctx.andar_ate(b.x)
        self.ctx.pular()
        self.ctx.particulas.explodir((b.x, b.y), [cor, BRANCO], 16, 180)
        self.ctx.mudar_necessidade("diversao", 3, (b.x, b.y))

        if diario["borboletas_moedas"] < LIMITE_DIA:
            ganho = MOEDAS_BORBOLETA * (5 if b.especie == 7 else 1)
            ganho = min(ganho, LIMITE_DIA - diario["borboletas_moedas"])
            diario["borboletas_moedas"] += ganho
            self.ctx.ganhar_moedas(ganho, (b.x, b.y - 20))
        else:
            self.ctx.som("pulo")

        if chave not in save["album"]:
            save["album"].append(chave)
            self.ctx.avisar(tr("NOVA NO ÁLBUM: {nome}!", nome=tr(nome)))
            self.ctx.som("vencer", 0.6)
            if len(save["album"]) >= len(ESPECIES) and "asas_borboleta" not in save["inventario"]:
                save["inventario"].append("asas_borboleta")
                self.ctx.avisar("ÁLBUM COMPLETO! GANHOU ASAS DE BORBOLETA!")
        save.salvar()

    def desenhar(self, tela):
        for b in self.lista:
            b.desenhar(tela, self.ctx.tempo)

    # --------------------------------------------------------
    # ÁLBUM
    # --------------------------------------------------------

    def evento_album(self, e):
        if not self.album_aberto:
            return False
        if (e.type == pygame.KEYDOWN) or (e.type == pygame.MOUSEBUTTONDOWN):
            self.album_aberto = False
            self.ctx.som("voltar", 0.6)
            return True
        return e.type in (pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION)

    def desenhar_album(self, tela):
        if not self.album_aberto:
            return
        ui.veu(tela, 160)
        caixa = pygame.Rect(0, 0, 700, 440)
        caixa.center = (LARGURA // 2, ALTURA // 2)
        ui.painel(tela, caixa, (250, 245, 225), (160, 120, 70), 18, 5)
        ui.desenhar_texto(tela, tr("ÁLBUM DE BORBOLETAS"), (caixa.centerx, caixa.y + 20), 20,
                          (120, 80, 40), "midtop", sombra=False)
        album = self.ctx.app.save["album"]
        for i, (chave, nome, cor) in enumerate(ESPECIES):
            c, l = i % 4, i // 4
            r = pygame.Rect(caixa.x + 30 + c * 162, caixa.y + 70 + l * 160, 146, 146)
            pygame.draw.rect(tela, (235, 225, 195), r, border_radius=12)
            pygame.draw.rect(tela, (180, 150, 100), r, 2, border_radius=12)
            tem = chave in album
            b = Borboleta()
            b.x, b.y, b.especie, b.fase = r.centerx, r.y + 58, i, 0.0
            if tem:
                b.desenhar(tela, self.ctx.tempo)
                ui.desenhar_texto(tela, tr(nome), (r.centerx, r.bottom - 26), 8, (90, 60, 30),
                                  "midtop", sombra=False)
            else:
                pygame.draw.circle(tela, (205, 195, 170), (r.centerx, r.y + 58), 26)
                ui.desenhar_texto(tela, "?", (r.centerx, r.y + 58), 20, (170, 160, 140), "center",
                                  sombra=False)
        ui.desenhar_texto(tela, tr("{n}/{total} — complete e ganhe ASAS!", n=len(album), total=len(ESPECIES)),
                          (caixa.centerx, caixa.bottom - 30), 10, (120, 80, 40), "midtop",
                          sombra=False)


# ============================================================
# BOLA PARA O PET
# ============================================================

class Bola:

    RAIO = 36

    def __init__(self, ctx):
        self.ctx = ctx
        self.ativa = False
        self.segurando = False
        self.x = self.y = 0.0
        self.vx = self.vy = 0.0
        self.historico = []
        self.estado = "parada"        # parada | voando | buscando | trazendo | escondida

    def alternar(self):
        if self.ativa:
            self.ativa = False
            self.estado = "parada"
        else:
            self.ativa = True
            self.x = self.ctx.ovo_x + 50
            self.y = self.ctx.ovo_chao - self.RAIO
            self.vx = self.vy = 0
            self.estado = "parada"
            self.ctx.avisar("ARRASTE E SOLTE A BOLA PARA JOGAR!")
        self.ctx.som("clique")

    def evento(self, e):
        if not self.ativa or self.estado in ("buscando", "trazendo", "escondida"):
            return False
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if math.hypot(e.pos[0] - self.x, e.pos[1] - self.y) < self.RAIO + 18:
                self.segurando = True
                self.historico = [(e.pos, self.ctx.tempo)]
                return True
        elif e.type == pygame.MOUSEMOTION and self.segurando:
            self.x, self.y = e.pos
            self.historico.append((e.pos, self.ctx.tempo))
            self.historico = self.historico[-6:]
            return True
        elif e.type == pygame.MOUSEBUTTONUP and e.button == 1 and self.segurando:
            self.segurando = False
            (x0, y0), t0 = self.historico[0]
            dt = max(0.016, self.ctx.tempo - t0)
            self.vx = max(-900, min(900, (e.pos[0] - x0) / dt))
            self.vy = max(-900, min(600, (e.pos[1] - y0) / dt))
            self.estado = "voando"
            self.ctx.som("pulo", 0.6)
            return True
        return False

    def atualizar(self, dt):
        if not self.ativa:
            return
        chao = self.ctx.ovo_chao - self.RAIO
        if self.estado == "voando":
            self.vy += 1200 * dt
            self.x += self.vx * dt
            self.y += self.vy * dt
            if self.x < 20 or self.x > LARGURA - 20:
                self.x = max(20, min(LARGURA - 20, self.x))
                self.vx *= -0.6
            if self.y >= chao:
                self.y = chao
                if abs(self.vy) > 120:
                    self.vy *= -0.5
                    self.ctx.som("bater", 0.3)
                else:
                    self.vy = 0
                self.vx *= 0.9
                if abs(self.vx) < 20 and self.vy == 0:
                    self.vx = 0
                    self._parou()
        elif self.estado == "trazendo":
            pet = self.ctx.pet
            if pet is None or not getattr(pet, "trazendo", False):
                # O pet devolveu a bola no pé do ovo (ele mesmo dá a diversão)
                self.estado = "parada"
                self.x = self.ctx.ovo_x + 50
                self.y = chao
                self.ctx.som("ponto")

    def _parou(self):
        pet = self.ctx.pet
        if pet is None:
            self.estado = "parada"
            self.ctx.mudar_necessidade("diversao", 1, (self.x, self.y - 30))
            return
        self.estado = "buscando"

        def pegou():
            self.estado = "trazendo"
        pet.buscar(self.x, pegou)

    def desenhar(self, tela):
        if not self.ativa or self.estado == "trazendo":
            return
        x, y = int(self.x), int(self.y)
        chao = self.ctx.ovo_chao
        pygame.draw.ellipse(tela, (60, 120, 40), (x - 12, chao - 4, 24, 8))
        pygame.draw.circle(tela, (230, 50, 50), (x, y), self.RAIO)
        pygame.draw.circle(tela, (255, 255, 255), (x, y), self.RAIO, 2)
        pygame.draw.line(tela, (255, 255, 255), (x - self.RAIO, y), (x + self.RAIO, y), 2)
        pygame.draw.circle(tela, (255, 190, 190), (x - 4, y - 4), 3)
