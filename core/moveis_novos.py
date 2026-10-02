import math

import pygame

from core import moveis as M
from core import ui
from core.idioma import t
from core.moveis import Movel, _blit_brilho, _blit_sprite, MADEIRA_ESCURA

# ============================================================
# MÓVEIS NOVOS (coleção "Vizinhança")
# ============================================================
# Mesma API de core/moveis.py. Registrados no CATALOGO/_CLASSES
# quando este módulo é importado (o moveis.py importa no final).

NOVOS = {
    "cortinas": dict(nome="CORTINAS", preco=110, raridade="COMUM", comodo="CASA", loja=True,
                     desc="Fecham sozinhas quando o ovo dorme."),
    "quadro_vizinhanca": dict(nome="QUADRO DA VIZINHANÇA", preco=150, raridade="INCOMUM",
                              comodo="CASA", loja=True,
                              desc="A sua rua em miniatura, com as casas dos vizinhos."),
    "pipa": dict(nome="PIPA", preco=90, raridade="COMUM", comodo="SOL", loja=True,
                 desc="Voa no céu do quintal. Clique para dar um looping!"),
    "fogueira": dict(nome="FOGUEIRA", preco=300, raridade="INCOMUM", comodo="SOL", loja=True,
                     desc="Acende no fim do dia. Ficar pertinho diverte o ovo."),
}


# ============================================================
# CORTINAS
# ============================================================

class Cortinas(Movel):

    caixa = (568, 56, 454, 300)
    X0, X1, Y0, Y1 = 575, 1015, 66, 350
    MEIO = 795
    COR = (220, 80, 90)

    def __init__(self, movel_id):
        super().__init__(movel_id)
        self.rect = pygame.Rect(575, 60, 440, 290)
        self.base_y = 60
        self.fechada = 0.0            # 0 aberta, 1 fechada
        self.manual = None            # None = automático (fecha quando dorme)

    def atualizar(self, dt, ctx):
        dormindo = bool(getattr(ctx, "dormindo", False))
        if self.manual is None:
            alvo = 1.0 if dormindo else 0.0
        else:
            alvo = 1.0 if self.manual else 0.0
            if not dormindo and self.manual and getattr(self, "_dormia", False):
                self.manual = None          # acordou: volta ao automático
        self._dormia = dormindo
        passo = dt / 0.8
        self.fechada = min(alvo, self.fechada + passo) if alvo > self.fechada \
            else max(alvo, self.fechada - passo)

    def _painel(self, tela, x0, x1, esquerda):
        largura = x1 - x0
        cor = self.COR
        pygame.draw.rect(tela, cor, (x0, self.Y0 + 4, largura, self.Y1 - self.Y0))
        dobras = max(2, int(largura / 18))
        for k in range(1, dobras):
            x = x0 + k * largura / dobras
            pygame.draw.line(tela, ui.escurecer(cor, 45), (x, self.Y0 + 6), (x, self.Y1), 3)
            pygame.draw.line(tela, ui.clarear(cor, 30), (x + 3, self.Y0 + 6), (x + 3, self.Y1), 1)
        pygame.draw.rect(tela, ui.escurecer(cor, 70), (x0, self.Y0 + 4, largura, self.Y1 - self.Y0), 2)
        # Barra de baixo franzida
        for x in range(int(x0), int(x1), 8):
            pygame.draw.circle(tela, ui.escurecer(cor, 30), (x + 4, self.Y1), 4)
        # Faixa que prende a cortina aberta
        if self.fechada < 0.2:
            pygame.draw.rect(tela, (255, 214, 64), (x0 + 2, 246, largura - 4, 8), border_radius=3)

    def desenhar(self, tela, ctx):
        f = self.fechada
        abre = 65
        # esquerda: de X0 até X0 + abre (aberta) ou até o MEIO (fechada)
        esq_fim = self.X0 + abre + (self.MEIO - self.X0 - abre) * f
        dir_ini = self.X1 - abre - (self.X1 - abre - self.MEIO) * f
        self._painel(tela, self.X0, esq_fim, True)
        self._painel(tela, dir_ini, self.X1, False)
        pygame.draw.line(tela, (120, 80, 40), (self.X0 - 4, self.Y0), (self.X1 + 4, self.Y0), 6)
        for x in (self.X0 - 4, self.X1 + 4):
            pygame.draw.circle(tela, (120, 80, 40), (x, self.Y0), 6)
            pygame.draw.circle(tela, (160, 110, 60), (x, self.Y0), 3)

    def clicar(self, pos, ctx):
        f = self.fechada
        esq_fim = self.X0 + 65 + (self.MEIO - self.X0 - 65) * f
        dir_ini = self.X1 - 65 - (self.X1 - 65 - self.MEIO) * f
        if not (self.X0 <= pos[0] <= esq_fim or dir_ini <= pos[0] <= self.X1) \
                or not self.Y0 <= pos[1] <= self.Y1:
            return False
        self.manual = not (self.fechada > 0.5)
        ctx.som("virar")
        return True

    def dica(self, ctx):
        return t("CORTINAS: clique para abrir/fechar")


# ============================================================
# QUADRO DA VIZINHANÇA
# ============================================================

class QuadroVizinhanca(Movel):

    caixa = (666, 356, 132, 78)
    R = pygame.Rect(672, 362, 120, 66)

    def __init__(self, movel_id):
        super().__init__(movel_id)
        self.rect = self.R.copy()
        self.base_y = 362
        self._perfis = None
        self._relogio = 0.0

    def _carregar(self):
        from core import perfis
        self._perfis = [perfis.ler_ovo(s) for s in range(perfis.MAX_SLOTS)]

    def atualizar(self, dt, ctx):
        self._relogio -= dt
        if self._perfis is None or self._relogio <= 0:
            self._relogio = 20.0
            try:
                self._carregar()
            except Exception:
                self._perfis = [None] * 5

    def desenhar(self, tela, ctx):
        from core import fachada_desenho as fd
        from core.jogador import Jogador
        r = self.R
        pygame.draw.rect(tela, (0, 0, 0), r.move(3, 4), border_radius=3)
        pygame.draw.rect(tela, (190, 228, 170), r)
        tela.set_clip(r)
        # Rua em ferradura (miniatura)
        cx, cy = r.centerx, r.bottom + 6
        pygame.draw.ellipse(tela, (60, 60, 70), (cx - 30, cy - 44, 60, 88), 6)
        posicoes = [(r.x + 16, r.bottom - 8), (r.x + 30, r.y + 30), (cx, r.y + 22),
                    (r.right - 30, r.y + 30), (r.right - 16, r.bottom - 8)]
        slot_meu = getattr(getattr(ctx, "app", None), "slot", -1)
        for i, pos in enumerate(posicoes):
            save = self._perfis[i] if self._perfis else None
            if save is None:
                pygame.draw.rect(tela, (190, 150, 100), (pos[0] - 7, pos[1] - 3, 14, 4))
                continue
            fd.desenhar_casa(tela, pos, 0.12, save["casa"], Jogador.cor_do_ovo(save["ovo"]),
                             morador=False)
            if i == slot_meu:
                ui.estrela(tela, (pos[0], pos[1] - 28), 4, (255, 214, 64))
        tela.set_clip(None)
        pygame.draw.rect(tela, (150, 100, 55), r, 5)
        pygame.draw.rect(tela, MADEIRA_ESCURA, r.inflate(4, 4), 1)

    def clicar(self, pos, ctx):
        if not self.R.collidepoint(pos):
            return False
        nomes = [s["nome"] for i, s in enumerate(self._perfis or [])
                 if s is not None and i != getattr(ctx.app, "slot", -1)]
        ctx.avisar(t("VIZINHOS: {lista}", lista=", ".join(nomes)) if nomes else t("NENHUM VIZINHO AINDA"))
        ctx.som("clique")
        return True

    def dica(self, ctx):
        return "QUADRO DA VIZINHANÇA"


# ============================================================
# PIPA
# ============================================================

class Pipa(Movel):

    caixa = (230, 110, 200, 500)
    ESTACA = (380, 600)
    CORES = [(255, 90, 90), (255, 220, 60), (90, 180, 255), (120, 220, 90)]

    def __init__(self, movel_id):
        super().__init__(movel_id)
        self.rect = pygame.Rect(0, 0, 60, 70)
        self.base_y = 600
        self.t = 0.0
        self.looping = 0.0
        self.recarga = 0.0

    def _pos(self, ctx):
        v = max(0.3, getattr(ctx, "vento", 0.3))
        return (330 + 40 * math.sin(0.7 * self.t) * v * 1.4, 170 + 20 * math.sin(1.1 * self.t))

    def atualizar(self, dt, ctx):
        self.t += dt
        self.looping = max(0.0, self.looping - dt)
        self.recarga = max(0.0, self.recarga - dt)
        x, y = self._pos(ctx)
        self.rect.center = (x, y)

    def desenhar(self, tela, ctx):
        if getattr(ctx, "chovendo", False):
            # guardada: só a estaca
            pygame.draw.line(tela, (120, 85, 50), self.ESTACA, (self.ESTACA[0], self.ESTACA[1] - 18), 4)
            return
        x, y = self._pos(ctx)
        ang = self.looping / 1.2 * math.tau if self.looping else math.sin(self.t * 1.3) * 0.15
        # Linha até a estaca (curvinha)
        pts = []
        for i in range(11):
            f = i / 10
            px = x + (self.ESTACA[0] - x) * f
            py = y + 22 + (self.ESTACA[1] - y - 22) * f + math.sin(f * math.pi) * 30
            pts.append((px, py))
        pygame.draw.lines(tela, (240, 240, 240), False, pts, 1)
        pygame.draw.line(tela, (120, 85, 50), self.ESTACA, (self.ESTACA[0], self.ESTACA[1] - 18), 4)
        # Rabiola
        for i in range(6):
            f = (i + 1) / 7
            rx = x - math.sin(ang) * 30 * f - 6 * math.sin(self.t * 4 + i)
            ry = y + 28 + 60 * f
            cor = self.CORES[i % 4]
            pygame.draw.polygon(tela, cor, [(rx - 5, ry - 3), (rx + 5, ry + 3), (rx + 5, ry - 3), (rx - 5, ry + 3)])
        # Losango em 4 cores
        c, s = math.cos(ang), math.sin(ang)

        def g(dx, dy):
            return (x + dx * c - dy * s, y + dx * s + dy * c)
        topo, dirp, baixo, esq, meio = g(0, -28), g(22, -4), g(0, 28), g(-22, -4), g(0, -4)
        for cor, tri in zip(self.CORES, ((topo, dirp, meio), (dirp, baixo, meio),
                                         (baixo, esq, meio), (esq, topo, meio))):
            pygame.draw.polygon(tela, cor, tri)
        pygame.draw.polygon(tela, (60, 40, 30), [topo, dirp, baixo, esq], 2)
        pygame.draw.line(tela, (60, 40, 30), topo, baixo, 1)
        pygame.draw.line(tela, (60, 40, 30), esq, dirp, 1)

    def clicar(self, pos, ctx):
        if getattr(ctx, "chovendo", False) or not self.rect.inflate(20, 20).collidepoint(pos):
            return False
        self.looping = 1.2
        ctx.som("asa")
        if self.recarga <= 0:
            self.recarga = 10.0
            ctx.mudar_necessidade("diversao", 1, self.rect.center)
        return True

    def dica(self, ctx):
        if getattr(ctx, "chovendo", False):
            return t("PIPA: guardada por causa da chuva")
        return t("PIPA: clique para dar um looping!")


# ============================================================
# FOGUEIRA
# ============================================================

class Fogueira(Movel):

    caixa = (246, 586, 110, 124)
    CX, BASE = 300, 696

    def __init__(self, movel_id):
        super().__init__(movel_id)
        self.rect = pygame.Rect(258, 636, 84, 70)
        self.base_y = 698
        self.t = 0.0
        self.acesa_clique = 0.0
        self.relogio = 0.0

    def _acesa(self, ctx):
        if getattr(ctx, "chovendo", False):
            return False
        return self.acesa_clique > 0 or getattr(ctx, "fase_dia", "dia") in ("por_do_sol", "noite")

    @staticmethod
    def _pintar(s):
        cx, base = Fogueira.CX, Fogueira.BASE
        pygame.draw.ellipse(s, (0, 0, 0, 60), (cx - 48, base - 8, 96, 18))
        pygame.draw.line(s, (130, 80, 40), (cx - 30, base - 2), (cx + 26, base - 16), 8)
        pygame.draw.line(s, (100, 60, 30), (cx + 30, base - 2), (cx - 26, base - 16), 8)
        for i in range(7):
            a = math.pi + i * math.pi / 6
            x = cx + math.cos(a) * 40
            y = base + math.sin(a) * -6 + 2
            pygame.draw.ellipse(s, (150, 150, 160), (x - 8, y - 5, 16, 10))
            pygame.draw.ellipse(s, (110, 110, 120), (x - 8, y - 5, 16, 10), 1)

    def atualizar(self, dt, ctx):
        self.t += dt
        self.acesa_clique = max(0.0, self.acesa_clique - dt)
        if self._acesa(ctx) and abs(getattr(ctx, "ovo_x", -999) - self.CX) < 150:
            self.relogio += dt
            if self.relogio >= 10:
                self.relogio = 0.0
                ctx.mudar_necessidade("diversao", 1, (self.CX, self.BASE - 80))
        else:
            self.relogio = 0.0

    def desenhar(self, tela, ctx):
        _blit_sprite(tela, "fogueira", self.caixa, self._pintar)
        cx, base = self.CX, self.BASE - 12
        if not self._acesa(ctx):
            if getattr(ctx, "chovendo", False):
                for i in range(3):
                    f = (self.t * 0.4 + i / 3) % 1
                    r = 4 + f * 8
                    fum = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
                    pygame.draw.circle(fum, (200, 200, 210, int(160 * (1 - f))), (r + 1, r + 1), r)
                    tela.blit(fum, (cx - r + math.sin(f * 5) * 6, base - 10 - f * 50 - r))
            return
        for k, cor in enumerate(((255, 120, 30), (255, 200, 40), (255, 245, 160))):
            alt = 46 - k * 12
            for j in (-1, 0, 1):
                osc = math.sin(self.t * (7 + k * 2) + j * 1.7) * 4
                h = alt * (1.0 if j == 0 else 0.7) + osc
                w = 14 - k * 3
                x = cx + j * (12 - k * 3)
                pygame.draw.polygon(tela, cor, [(x - w, base), (x + w, base), (x + osc * 0.4, base - h)])
        for i in range(4):
            f = (self.t * 0.8 + i / 4) % 1
            x = cx + math.sin(self.t * 3 + i * 2) * 14
            tela.fill((255, 220, 120), (round(x), round(base - 40 - f * 60), 2, 2))

    def desenhar_brilho(self, tela, ctx):
        if self._acesa(ctx):
            pulso = int(4 * math.sin(self.t * 6))
            _blit_brilho(tela, (self.CX, self.BASE - 30), 120 + pulso, (255, 150, 60), 50)

    def clicar(self, pos, ctx):
        if not self.rect.collidepoint(pos):
            return False
        if getattr(ctx, "chovendo", False):
            ctx.avisar(t("A CHUVA APAGOU A FOGUEIRA!"))
            ctx.som("erro")
            return True
        self.acesa_clique = 20.0
        ctx.som("explosao", 0.3)
        return True

    def dica(self, ctx):
        return t("FOGUEIRA: fique pertinho para se divertir")


# ------------------------------------------------------------
# REGISTRO
# ------------------------------------------------------------

M.CATALOGO.update(NOVOS)
M._CLASSES.update({"cortinas": Cortinas, "quadro_vizinhanca": QuadroVizinhanca,
                   "pipa": Pipa, "fogueira": Fogueira})
