import math
import time

import pygame

from settings import *
from core.idioma import t as tr
from core import ui

# ============================================================
# JARDIM (cômodo SOL)
# ============================================================
# Até 4 canteiros (o 1º é grátis, os outros são comprados na
# loja: canteiro_2/3/4). Cada planta passa por 4 estágios
# (broto, muda, planta, pronta) em tempo REAL — continua
# crescendo com o jogo fechado — mas cada estágio precisa ser
# REGADO (clique na gotinha). Sem água a planta só pausa.
#
# save["jardim"] = [ {"semente": id, "progresso": s, "regado": estagio,
#                     "t": timestamp, "colheitas": n}, ... ]  (1 por canteiro)

CANTEIROS_X = [160, 270, 380, 490]
LARG = 95
TOPO = 520
BASE = 560
ESTAGIOS = 4


def _itens():
    try:
        from core import itens
        return itens
    except ImportError:
        return None


def _formatar_tempo(s):
    s = max(0, int(s))
    if s >= 3600:
        return f"{s // 3600}h{(s % 3600) // 60:02d}"
    return f"{s // 60}:{s % 60:02d}"


class Jardim:

    def __init__(self, ctx):
        self.ctx = ctx
        self.save = ctx.app.save
        self.escolhendo = None          # índice do canteiro esperando semente
        self.rects_sementes = []
        self._normalizar()
        self._crescer_offline()

    # --------------------------------------------------------
    # DADOS
    # --------------------------------------------------------

    def _normalizar(self):
        lista = self.save["jardim"]
        while len(lista) < len(CANTEIROS_X):
            lista.append({})
        for i, c in enumerate(lista):
            if not isinstance(c, dict):
                lista[i] = {}

    def disponiveis(self):
        inv = self.save["inventario"]
        return 1 + sum(1 for i in (2, 3, 4) if f"canteiro_{i}" in inv)

    def rect(self, i):
        return pygame.Rect(CANTEIROS_X[i], TOPO, LARG, BASE - TOPO)

    @staticmethod
    def _nome_comida(cid):
        itens = _itens()
        d = getattr(itens, "COMIDAS", {}).get(cid) if itens else None
        return tr(d["nome"]) if d and d.get("nome") else cid.upper()

    def _dados_semente(self, sid):
        itens = _itens()
        return getattr(itens, "SEMENTES", {}).get(sid) if itens else None

    def _duracao(self, c):
        d = self._dados_semente(c.get("semente", ""))
        return float(d.get("tempo", 600)) if d else 600.0

    def estagio(self, c):
        if not c.get("semente"):
            return -1
        dur = self._duracao(c)
        passo = dur / (ESTAGIOS - 1)
        return min(ESTAGIOS - 1, int(c.get("progresso", 0) / passo))

    def precisa_agua(self, c):
        e = self.estagio(c)
        return 0 <= e < ESTAGIOS - 1 and c.get("regado", -1) < e

    def pronta(self, c):
        return self.estagio(c) == ESTAGIOS - 1

    def restante(self, c):
        return self._duracao(c) - c.get("progresso", 0)

    def _velocidade(self):
        return 1.2 if self.save["pet"] == "abelha" else 1.0

    def _crescer(self, c, segundos):
        """Avança o crescimento só até o fim do estágio regado."""
        if not c.get("semente") or self.pronta(c):
            return
        dur = self._duracao(c)
        passo = dur / (ESTAGIOS - 1)
        limite = (c.get("regado", -1) + 1) * passo
        c["progresso"] = min(limite, dur, c.get("progresso", 0) + segundos * self._velocidade())

    def _crescer_offline(self):
        agora = time.time()
        for c in self.save["jardim"]:
            if c.get("semente"):
                t = c.get("t", agora)
                if agora > t:
                    self._crescer(c, agora - t)
                c["t"] = agora

    # --------------------------------------------------------
    # AÇÕES
    # --------------------------------------------------------

    def plantar(self, i, sid):
        comida = self.save["comida"]
        if comida.get(sid, 0) <= 0:
            return
        comida[sid] -= 1
        if comida[sid] <= 0:
            del comida[sid]
        d = self._dados_semente(sid) or {}
        self.save["jardim"][i] = {"semente": sid, "progresso": 0.0, "regado": -1,
                                  "t": time.time(),
                                  "colheitas": d.get("colheitas", 1)}
        self.save.salvar()
        r = self.rect(i)
        self.ctx.particulas.explodir(r.center, [(120, 80, 45), (160, 110, 60)], 14, 140)
        self.ctx.som("pulo")
        self.ctx.andar_ate(r.centerx)

    def regar(self, i):
        c = self.save["jardim"][i]
        c["regado"] = self.estagio(c)
        self.save.salvar()
        r = self.rect(i)
        self.ctx.particulas.explodir((r.centerx, r.y), [(90, 170, 255), (170, 210, 255)], 20, 160)
        self.ctx.som("revelar")
        self.ctx.andar_ate(r.centerx)

    def colher(self, i, automatico=False):
        c = self.save["jardim"][i]
        d = self._dados_semente(c.get("semente", "")) or {}
        colheita = d.get("colheita", {})
        r = self.rect(i)
        for cid, qtd in colheita.get("comida", {}).items():
            self.save["comida"][cid] = self.save["comida"].get(cid, 0) + qtd
            self.ctx.textos.adicionar(f"+{qtd} {self._nome_comida(cid)}", (r.centerx, r.y - 30), BRANCO, 10)
        moedas = colheita.get("moedas", 0)
        if moedas:
            self.ctx.ganhar_moedas(moedas, (r.centerx, r.y - 50))

        restantes = c.get("colheitas", 1) - 1
        if restantes > 0:
            # Árvores produzem de novo: volta para o estágio "planta"
            dur = self._duracao(c)
            c["progresso"] = dur / (ESTAGIOS - 1) * 2
            c["regado"] = 2
            c["colheitas"] = restantes
        else:
            self.save["jardim"][i] = {}
        self.save.salvar()
        self.ctx.particulas.explodir(r.center, [AMARELO, (120, 220, 90), BRANCO], 30, 260)
        self.ctx.som("acerto")
        if not automatico:
            self.ctx.andar_ate(r.centerx)

    def clicar(self, pos):
        """Clique no cômodo SOL. Devolve True se foi no jardim."""
        if self.escolhendo is not None:
            for sid, r in self.rects_sementes:
                if r.collidepoint(pos):
                    self.plantar(self.escolhendo, sid)
                    self.escolhendo = None
                    return True
            self.escolhendo = None
            return True

        for i in range(self.disponiveis()):
            if not self.rect(i).inflate(10, 90).move(0, -40).collidepoint(pos):
                continue
            c = self.save["jardim"][i]
            if not c.get("semente"):
                sementes = self._sementes_no_inventario()
                if sementes:
                    self.escolhendo = i
                    self.ctx.som("clique")
                else:
                    self.ctx.avisar("COMPRE SEMENTES NO MERCADO DA LOJA!")
                    self.ctx.som("erro", 0.4)
            elif self.pronta(c):
                self.colher(i)
            elif self.precisa_agua(c):
                self.regar(i)
            else:
                self.ctx.avisar(tr("PRONTO EM {tempo}", tempo=_formatar_tempo(self.restante(c) / self._velocidade())))
            return True
        return False

    def _sementes_no_inventario(self):
        itens = _itens()
        sementes = getattr(itens, "SEMENTES", {}) if itens else {}
        return [(sid, q) for sid, q in self.save["comida"].items() if sid in sementes and q > 0]

    def molhar_tudo(self):
        """A chuva rega todas as plantas."""
        for c in self.save["jardim"]:
            if c.get("semente") and self.precisa_agua(c):
                c["regado"] = self.estagio(c)

    # --------------------------------------------------------

    def atualizar(self, dt):
        agora = time.time()
        for i, c in enumerate(self.save["jardim"]):
            if c.get("semente"):
                self._crescer(c, dt)
                c["t"] = agora
                # Robozinho BIP colhe sozinho
                if self.save["pet"] == "robo" and self.pronta(c) and self.ctx.comodo == "SOL":
                    self.colher(i, automatico=True)
        if self.ctx.chovendo:
            self.molhar_tudo()

    def desenhar(self, tela):
        itens = _itens()
        t = self.ctx.tempo
        mouse = pygame.mouse.get_pos()

        for i in range(self.disponiveis()):
            r = self.rect(i)
            pygame.draw.rect(tela, (170, 120, 70), r.inflate(8, 8), border_radius=6)
            pygame.draw.rect(tela, (120, 80, 45), r, border_radius=4)
            for k in range(4):
                y = r.y + 7 + k * 9
                pygame.draw.line(tela, (95, 60, 30), (r.x + 6, y), (r.right - 6, y), 2)

            c = self.save["jardim"][i]
            if not c.get("semente"):
                if r.inflate(10, 90).move(0, -40).collidepoint(mouse):
                    ui.desenhar_texto(tela, tr("PLANTAR"), (r.centerx, r.y - 16), 8, BRANCO, "center")
                continue

            e = self.estagio(c)
            if itens and hasattr(itens, "desenhar_planta"):
                itens.desenhar_planta(tela, c["semente"], e, (r.centerx, r.y + 12), t,
                                      c.get("colheitas"))
            if self.precisa_agua(c):
                y = r.y - 70 + math.sin(t * 4) * 4
                pygame.draw.circle(tela, (70, 150, 255), (r.centerx, int(y) + 5), 9)
                pygame.draw.polygon(tela, (70, 150, 255), [(r.centerx - 8, int(y) + 2),
                                                           (r.centerx + 8, int(y) + 2),
                                                           (r.centerx, int(y) - 12)])
                pygame.draw.circle(tela, (200, 230, 255), (r.centerx - 3, int(y) + 3), 3)
            if r.inflate(10, 90).move(0, -40).collidepoint(mouse) and not self.pronta(c):
                txt = tr("REGAR!") if self.precisa_agua(c) else _formatar_tempo(
                    self.restante(c) / self._velocidade())
                ui.desenhar_texto(tela, txt, (r.centerx, r.bottom + 12), 8, BRANCO, "center")

    def desenhar_escolha(self, tela):
        """Janelinha para escolher a semente."""
        self.rects_sementes = []
        if self.escolhendo is None:
            return
        itens = _itens()
        sementes = self._sementes_no_inventario()
        if not sementes:
            self.escolhendo = None
            return
        r0 = self.rect(self.escolhendo)
        largura = len(sementes) * 84 + 16
        caixa = pygame.Rect(0, 0, largura, 126)
        caixa.midbottom = (max(largura // 2 + 10, min(LARGURA - largura // 2 - 10, r0.centerx)),
                           r0.y - 90)
        ui.painel(tela, caixa, (40, 30, 20), AMARELO, 12, 3)
        ui.desenhar_texto(tela, tr("ESCOLHA A SEMENTE"), (caixa.centerx, caixa.y + 8), 8, AMARELO,
                          "midtop")
        mouse = pygame.mouse.get_pos()
        for k, (sid, q) in enumerate(sementes):
            r = pygame.Rect(caixa.x + 8 + k * 84, caixa.y + 24, 76, 94)
            pygame.draw.rect(tela, (90, 70, 40) if r.collidepoint(mouse) else (60, 45, 28), r,
                             border_radius=8)
            if itens and hasattr(itens, "icone_semente"):
                ic = itens.icone_semente(sid, 56)
                tela.blit(ic, ic.get_rect(center=(r.centerx, r.y + 36)))
            ui.desenhar_texto(tela, f"x{q}", (r.centerx, r.bottom - 14), 10, BRANCO, "center")
            self.rects_sementes.append((sid, r))
