import math
import random

import pygame

from settings import *
from core import ui

# ============================================================
# CUIDADOS: COMER E TOMAR BANHO
# ============================================================
# Bandeja: abre pela geladeira ou pelo botão COMIDA. ARRASTE a
#          comida até a boca do ovo. Cheio (fome >= 95) = "NÃO!".
# Banho:   botão SABÃO -> o cursor vira sabonete; esfregue no ovo
#          para fazer espuma e depois clique no CHUVEIRINHO.

POR_PAGINA = 6
ALTURA_BANDEJA = 118


def _itens():
    try:
        from core import itens
        return itens
    except ImportError:
        return None


class Bandeja:

    def __init__(self, ctx):
        self.ctx = ctx
        self.aberta = False
        self.anim = 0.0              # 0 fechada .. 1 aberta
        self.pagina = 0
        self.arrastando = None       # id da comida sendo arrastada
        self.pos_arraste = (0, 0)
        self.rects = []
        self.seta_esq = pygame.Rect(0, 0, 40, 60)
        self.seta_dir = pygame.Rect(0, 0, 40, 60)
        self.fechar = pygame.Rect(0, 0, 40, 40)

    def comidas(self):
        itens = _itens()
        catalogo = getattr(itens, "COMIDAS", {}) if itens else {}
        return [(cid, q) for cid, q in self.ctx.app.save["comida"].items()
                if cid in catalogo and q > 0]

    def abrir(self):
        self.aberta = True
        self.pagina = 0
        self.ctx.som("clique")

    def alternar(self):
        if self.aberta:
            self.aberta = False
            self.ctx.som("voltar", 0.6)
        else:
            self.abrir()

    # --------------------------------------------------------

    def evento(self, e):
        """Devolve True se o evento foi usado pela bandeja."""
        if not self.aberta:
            return False

        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                self.aberta = False
                return True
            if e.key in (pygame.K_LEFT, pygame.K_a):
                self.pagina = max(0, self.pagina - 1)
                return True
            if e.key in (pygame.K_RIGHT, pygame.K_d):
                self.pagina = min(self._paginas() - 1, self.pagina + 1)
                return True

        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self.fechar.collidepoint(e.pos):
                self.aberta = False
                self.ctx.som("voltar", 0.6)
                return True
            if self.seta_esq.collidepoint(e.pos):
                self.pagina = max(0, self.pagina - 1)
                return True
            if self.seta_dir.collidepoint(e.pos):
                self.pagina = min(self._paginas() - 1, self.pagina + 1)
                return True
            for cid, r in self.rects:
                if r.collidepoint(e.pos):
                    self.arrastando = cid
                    self.pos_arraste = e.pos
                    self.ctx.som("clique", 0.5)
                    return True
            return self._area().collidepoint(e.pos)

        if e.type == pygame.MOUSEMOTION and self.arrastando:
            self.pos_arraste = e.pos
            return True

        if e.type == pygame.MOUSEBUTTONUP and e.button == 1 and self.arrastando:
            cid = self.arrastando
            self.arrastando = None
            if self.ctx.rect_boca().inflate(40, 40).collidepoint(e.pos):
                self.comer(cid)
            return True

        return False

    def comer(self, cid):
        ctx = self.ctx
        save = ctx.app.save
        itens = _itens()
        pocao = bool(itens and itens.COMIDAS.get(cid, {}).get("pocao"))
        # Poções são bebidas: o ovo aceita mesmo de barriga cheia
        if ctx.necessidade("fome") >= 95 and not pocao:
            ctx.recusar()
            return
        if save["comida"].get(cid, 0) <= 0:
            return
        save["comida"][cid] -= 1
        if save["comida"][cid] <= 0:
            del save["comida"][cid]
        save.salvar()

        itens = _itens()
        dados = itens.COMIDAS.get(cid, {}) if itens else {}
        ctx.comer(cid, dados.get("efeitos", {"fome": 10}))

    # --------------------------------------------------------

    def _paginas(self):
        return max(1, math.ceil(len(self.comidas()) / POR_PAGINA))

    def _area(self):
        y = ALTURA - int(ALTURA_BANDEJA * self.anim)
        return pygame.Rect(150, y, 724, ALTURA_BANDEJA)

    def atualizar(self, dt):
        alvo = 1.0 if self.aberta else 0.0
        self.anim += (alvo - self.anim) * min(1.0, dt * 12)
        self.pagina = min(self.pagina, self._paginas() - 1)

    def desenhar(self, tela):
        self.rects = []
        if self.anim < 0.02:
            return
        itens = _itens()
        area = self._area()
        ui.painel(tela, area.inflate(0, 20).move(0, 10), (230, 235, 245), (150, 160, 180), 18, 4)
        pygame.draw.rect(tela, (200, 210, 225), (area.x + 10, area.y + 10, area.w - 20, 6),
                         border_radius=3)

        lista = self.comidas()
        if not lista:
            ui.desenhar_texto(tela, "GELADEIRA VAZIA! COMPRE COMIDA NA LOJA", area.center, 12,
                              (80, 80, 110), "center", sombra=False)
        inicio = self.pagina * POR_PAGINA
        for k, (cid, q) in enumerate(lista[inicio:inicio + POR_PAGINA]):
            r = pygame.Rect(area.x + 56 + k * 104, area.y + 20, 92, 88)
            self.rects.append((cid, r))
            pygame.draw.rect(tela, (255, 255, 255), r, border_radius=12)
            pygame.draw.rect(tela, (170, 180, 200), r, 2, border_radius=12)
            if cid != self.arrastando and itens:
                itens.desenhar_comida(tela, cid, (r.centerx, r.y + 38), 52)
            ui.desenhar_texto(tela, f"x{q}", (r.right - 8, r.bottom - 8), 10, (60, 60, 90),
                              "bottomright", sombra=False)

        self.seta_esq = pygame.Rect(area.x + 8, area.y + 34, 40, 60)
        self.seta_dir = pygame.Rect(area.right - 48, area.y + 34, 40, 60)
        self.fechar = pygame.Rect(area.right - 34, area.y - 30, 40, 40)
        if self._paginas() > 1:
            for rect, s, ok in ((self.seta_esq, "<", self.pagina > 0),
                                (self.seta_dir, ">", self.pagina < self._paginas() - 1)):
                pygame.draw.rect(tela, (120, 130, 170) if ok else (190, 195, 210), rect,
                                 border_radius=10)
                ui.desenhar_texto(tela, s, rect.center, 16, BRANCO, "center")
        pygame.draw.circle(tela, (220, 80, 80), self.fechar.center, 18)
        pygame.draw.circle(tela, BRANCO, self.fechar.center, 18, 3)
        ui.desenhar_texto(tela, "×", self.fechar.center, 16, BRANCO, "center")

        if lista:
            ui.desenhar_texto(tela, "ARRASTE ATÉ A BOCA DO OVO", (area.centerx, area.y - 16), 10,
                              BRANCO, "center")

    def desenhar_arraste(self, tela):
        if self.arrastando:
            itens = _itens()
            if itens:
                itens.desenhar_comida(tela, self.arrastando, self.pos_arraste, 60)


# ============================================================
# BANHO
# ============================================================

class Banho:

    MAX_BOLHAS = 20

    def __init__(self, ctx):
        self.ctx = ctx
        self.ativo = False           # modo sabonete
        self.esfregando = False
        self.distancia = 0.0
        self.ultimo = None
        self.bolhas = []             # (dx, dy, raio) relativos ao centro do ovo
        self.chuveiro = 0.0          # tempo restante de água caindo
        self.brilho = 0.0
        self.rect_chuveiro = pygame.Rect(0, 0, 64, 64)

    def alternar(self):
        self.ativo = not self.ativo
        self.esfregando = False
        self.ctx.som("clique")
        pygame.mouse.set_visible(not self.ativo)

    def sair(self):
        if self.ativo:
            self.ativo = False
            pygame.mouse.set_visible(True)

    def _mostrar_chuveiro(self):
        return bool(self.bolhas) and self.chuveiro <= 0

    def evento(self, e):
        if self._mostrar_chuveiro() and e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 \
                and self.rect_chuveiro.collidepoint(e.pos):
            self.chuveiro = 2.0
            self.ctx.som("virar")
            self.sair()
            return True

        if not self.ativo:
            return False

        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            self.sair()
            return True
        if e.type == pygame.MOUSEBUTTONDOWN:
            if e.button == 3:
                self.sair()
                return True
            if e.button == 1:
                self.esfregando = True
                self.ultimo = e.pos
                return True
        if e.type == pygame.MOUSEBUTTONUP and e.button == 1:
            self.esfregando = False
            return True
        if e.type == pygame.MOUSEMOTION and self.esfregando:
            corpo = self.ctx.rect_corpo()
            if self.ultimo and corpo.collidepoint(e.pos):
                self.distancia += math.dist(self.ultimo, e.pos)
                while self.distancia >= 40 and len(self.bolhas) < self.MAX_BOLHAS:
                    self.distancia -= 40
                    cx, cy = corpo.center
                    dx = max(-corpo.w * 0.42, min(corpo.w * 0.42, e.pos[0] - cx
                                                  + random.uniform(-10, 10)))
                    dy = max(-corpo.h * 0.42, min(corpo.h * 0.42, e.pos[1] - cy
                                                  + random.uniform(-10, 10)))
                    self.bolhas.append((dx, dy, random.randint(6, 12)))
                    self.ctx.mudar_necessidade("higiene", 2)
                    self.ctx.som("revelar", 0.3)
            self.ultimo = e.pos
            return True
        return e.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP)

    def atualizar(self, dt):
        self.brilho = max(0.0, self.brilho - dt)
        if self.chuveiro > 0:
            self.chuveiro -= dt
            # As bolhas estouram uma a uma enquanto a água cai
            if self.bolhas and random.random() < dt * 14:
                dx, dy, r = self.bolhas.pop()
                cx, cy = self.ctx.rect_corpo().center
                self.ctx.particulas.explodir((cx + dx, cy + dy), [BRANCO, (200, 230, 255)], 5, 90)
                self.ctx.mudar_necessidade("higiene", 1)
            if self.chuveiro <= 0:
                self.bolhas.clear()
                self.brilho = 1.5
                self.ctx.som("acerto")
                # Banho completo: conta para as conquistas e dá XP
                from core import progresso
                progresso.contar(self.ctx.app, "banhos")
                progresso.ganhar_xp(self.ctx.app, progresso.XP_BANHO)

    def desenhar_no_ovo(self, tela):
        corpo = self.ctx.rect_corpo()
        cx, cy = corpo.center
        for dx, dy, r in self.bolhas:
            pygame.draw.circle(tela, (255, 255, 255), (int(cx + dx), int(cy + dy)), r)
            pygame.draw.circle(tela, (200, 220, 245), (int(cx + dx), int(cy + dy)), r, 2)
            pygame.draw.circle(tela, (255, 255, 255), (int(cx + dx - r / 3), int(cy + dy - r / 3)),
                               max(1, r // 4))
        if self.brilho > 0:
            for i in range(3):
                a = self.ctx.tempo * 2 + i * 2.1
                ui.estrela(tela, (cx + math.cos(a) * corpo.w * 0.6, cy + math.sin(a) * corpo.h * 0.5),
                           7, (255, 250, 200), a)

    def desenhar(self, tela):
        corpo = self.ctx.rect_corpo()
        # Água do chuveiro
        if self.chuveiro > 0:
            topo = corpo.y - 110
            pygame.draw.rect(tela, (170, 175, 190), (corpo.centerx - 30, topo - 16, 60, 14),
                             border_radius=6)
            for i in range(16):
                x = corpo.centerx - 26 + (i * 7) % 54
                y = topo + ((i * 29 + int(self.ctx.tempo * 600)) % (corpo.bottom - topo))
                pygame.draw.line(tela, (120, 180, 255), (x, y), (x, y + 12), 2)

        # Botão do chuveirinho
        if self._mostrar_chuveiro():
            self.rect_chuveiro.midbottom = (corpo.centerx, corpo.y - 70)
            r = self.rect_chuveiro
            pygame.draw.circle(tela, (40, 110, 200), r.center, 30)
            pygame.draw.circle(tela, BRANCO, r.center, 30, 3)
            pygame.draw.rect(tela, BRANCO, (r.centerx - 14, r.centery - 12, 28, 10), border_radius=4)
            for k in range(4):
                pygame.draw.line(tela, (170, 220, 255), (r.centerx - 10 + k * 7, r.centery + 2),
                                 (r.centerx - 12 + k * 7, r.centery + 16), 2)
            ui.desenhar_texto(tela, "CHUVEIRO!", (r.centerx, r.y - 12), 8, BRANCO, "center")

        # Cursor de sabonete
        if self.ativo:
            mx, my = pygame.mouse.get_pos()
            sab = pygame.Rect(0, 0, 44, 28)
            sab.center = (mx, my)
            pygame.draw.rect(tela, (255, 200, 230), sab, border_radius=10)
            pygame.draw.rect(tela, (220, 140, 190), sab, 2, border_radius=10)
            pygame.draw.line(tela, (255, 240, 250), (sab.x + 8, sab.y + 7), (sab.x + 22, sab.y + 7), 3)
            ui.desenhar_texto(tela, "ESFREGUE NO OVO! (botão direito sai)", (LARGURA // 2, 130),
                              10, BRANCO, "center")
