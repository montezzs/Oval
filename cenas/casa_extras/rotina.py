import datetime
import math
import random

import pygame

from settings import *
from core import ui

# ============================================================
# ROTINA DIÁRIA
# ============================================================
# - BAÚ DIÁRIO no chão da CASA: 20, 25, 30, 40, 50, 60, 100
#   OVOEDAS (dias seguidos) + 1 comida. Faltou um dia: volta ao 1.
# - DESAFIO DO DIA do ROBERT (BRINCAR): cumpra e ganhe +50.
# - TOTÓ dança e dá dicas.

PREMIOS_BAU = [20, 25, 30, 40, 50, 60, 100]
COMIDAS_BAU = ["maca", "banana", "leite", "pao_queijo", "suco_limao", "sanduiche", "sorvete"]
PREMIO_DESAFIO = 50

BAU = pygame.Rect(676, 566, 64, 50)
ROBERT = pygame.Rect(815, 165, 170, 395)
TOTO = pygame.Rect(925, 405, 95, 160)

DICAS = [
    "Dica: com as 4 barrinhas acima de 70 você ganha +10% de OVOEDAS!",
    "Dica: a chuva rega o jardim sozinha.",
    "Dica: pegue todas as borboletas e ganhe asas!",
    "Dica: a 1ª partida do dia em cada jogo vale +5 OVOEDAS.",
    "Dica: apague a luz para o ovo dormir e recuperar a energia.",
    "Dica: jogos para 2 ficam na aba 2 JOGADORES.",
    "Dica: depois da chuva procure o pote de ouro do arco-íris!",
    "Dica: aperte L para abrir a loja.",
]


def _hoje():
    return datetime.date.today().isoformat()


def _ontem():
    return (datetime.date.today() - datetime.timedelta(days=1)).isoformat()


# ------------------------------------------------------------
# DESAFIO (chamado também pelo App no fim dos mini jogos)
# ------------------------------------------------------------

def desafio_do_dia(save):
    d = save["diario"].get("desafio")
    if isinstance(d, dict) and d.get("dia") == _hoje():
        return d
    from jogos import JOGOS
    from jogos import trofeus
    rnd = random.Random(_hoje())
    jogo = rnd.choice(JOGOS)
    tipo, meta, texto = trofeus.meta_desafio(jogo)
    d = dict(dia=_hoje(), jogo=jogo.ID, tipo=tipo, meta=meta, texto=texto,
             feito=False, pago=False)
    save["diario"]["desafio"] = d
    return d


def verificar_desafio(save, jogo, valor, venceu):
    d = desafio_do_dia(save)
    if d["feito"] or d["jogo"] != jogo.ID:
        return
    if d["tipo"] == "vitoria":
        ok = venceu
    elif d["tipo"] == "menor":
        ok = venceu and valor <= d["meta"]
    else:
        ok = valor >= d["meta"]
    if ok:
        d["feito"] = True


class Rotina:

    def __init__(self, ctx):
        self.ctx = ctx
        self.balao = None            # texto do balão do ROBERT/TOTÓ
        self.tempo_balao = 0.0
        self.pos_balao = (0, 0)
        self.danca_toto = 0.0

    # --------------------------------------------------------
    # BAÚ
    # --------------------------------------------------------

    def bau_disponivel(self):
        return self.ctx.app.save["diario"].get("bau_ultimo") != _hoje()

    def abrir_bau(self):
        save = self.ctx.app.save
        diario = save["diario"]
        seq = diario.get("bau_seq", 0) + 1 if diario.get("bau_ultimo") == _ontem() else 1
        if seq > len(PREMIOS_BAU):
            seq = 1
        diario["bau_seq"] = seq
        diario["bau_ultimo"] = _hoje()
        premio = PREMIOS_BAU[seq - 1]
        comida = random.choice(COMIDAS_BAU)
        save["comida"][comida] = save["comida"].get(comida, 0) + 1
        save.salvar()
        self.ctx.ganhar_moedas(premio, BAU.center)
        self.ctx.particulas.explodir(BAU.center, [AMARELO, (255, 90, 90), BRANCO, (120, 200, 255)],
                                     50, 380)
        self.ctx.som("vencer")
        self.ctx.avisar(f"BAÚ DO DIA {seq}/7: +{premio} OVOEDAS e 1 {comida.upper()}!")

    # --------------------------------------------------------
    # CLIQUES
    # --------------------------------------------------------

    def clicar(self, pos):
        comodo = self.ctx.comodo
        if comodo == "CASA" and self.bau_disponivel() and BAU.inflate(12, 12).collidepoint(pos):
            self.abrir_bau()
            return True
        if comodo == "BRINCAR":
            if ROBERT.collidepoint(pos) and not TOTO.collidepoint(pos):
                self._falar_robert()
                return True
            if TOTO.collidepoint(pos):
                self.danca_toto = 2.0
                self._mostrar(random.choice(DICAS), (TOTO.centerx - 120, TOTO.y - 10))
                self.ctx.som("boing")
                return True
        return False

    def _falar_robert(self):
        save = self.ctx.app.save
        d = desafio_do_dia(save)
        if d["feito"] and not d["pago"]:
            d["pago"] = True
            save.salvar()
            self.ctx.ganhar_moedas(PREMIO_DESAFIO, (ROBERT.centerx, ROBERT.y + 120))
            self.ctx.som("vencer")
            self._mostrar("PARABÉNS! Desafio cumprido: +50 OVOEDAS!", (ROBERT.x - 110, ROBERT.y + 120))
        elif d["pago"]:
            self._mostrar("Você já cumpriu o desafio de hoje. Volte amanhã!",
                          (ROBERT.x - 110, ROBERT.y + 120))
        else:
            self._mostrar("DESAFIO DO DIA: " + d["texto"] + " (+50)", (ROBERT.x - 110, ROBERT.y + 120))
        self.ctx.som("selecionar")

    def _mostrar(self, texto, pos):
        self.balao = texto
        self.tempo_balao = 5.0
        self.pos_balao = pos

    # --------------------------------------------------------

    def atualizar(self, dt):
        self.tempo_balao = max(0.0, self.tempo_balao - dt)
        self.danca_toto = max(0.0, self.danca_toto - dt)

    def desenhar(self, tela):
        t = self.ctx.tempo
        if self.ctx.comodo == "CASA" and self.bau_disponivel():
            pula = abs(math.sin(t * 3)) * 6
            r = BAU.move(0, -int(pula))
            pygame.draw.ellipse(tela, (60, 40, 25), (BAU.x - 4, BAU.bottom - 8, BAU.w + 8, 14))
            pygame.draw.rect(tela, (230, 80, 80), r, border_radius=8)
            pygame.draw.rect(tela, (150, 40, 40), r, 3, border_radius=8)
            pygame.draw.rect(tela, AMARELO, (r.centerx - 5, r.y, 10, r.h))
            pygame.draw.rect(tela, AMARELO, (r.x, r.y + 16, r.w, 8))
            pygame.draw.circle(tela, AMARELO, (r.centerx - 10, r.y - 4), 8, 3)
            pygame.draw.circle(tela, AMARELO, (r.centerx + 10, r.y - 4), 8, 3)
            if int(t * 2) % 2 == 0:
                ui.estrela(tela, (r.right + 4, r.y - 6), 6, (255, 250, 200), t)

        if self.ctx.comodo == "BRINCAR":
            d = desafio_do_dia(self.ctx.app.save)
            # Exclamação sobre o ROBERT quando há desafio / prêmio
            if not d["pago"]:
                cor = (120, 255, 150) if d["feito"] else AMARELO
                y = ROBERT.y + 10 + math.sin(t * 4) * 4
                ui.desenhar_texto(tela, "!", (ROBERT.centerx + 40, y), 28, cor, "center")
            if self.danca_toto > 0:
                for i in range(3):
                    a = t * 5 + i * 2.1
                    ui.desenhar_texto(tela, "♪", (TOTO.centerx + math.cos(a) * 50,
                                                  TOTO.y + 30 + math.sin(a) * 20), 14,
                                      (255, 230, 120), "center")

        if self.tempo_balao > 0 and self.balao:
            linhas = ui.quebrar_linhas(self.balao, 10, 300)
            h = len(linhas) * 18 + 20
            caixa = pygame.Rect(0, 0, 320, h)
            caixa.midbottom = self.pos_balao
            caixa.clamp_ip(pygame.Rect(10, 90, LARGURA - 20, ALTURA - 100))
            pygame.draw.rect(tela, BRANCO, caixa, border_radius=14)
            pygame.draw.rect(tela, (40, 40, 60), caixa, 3, border_radius=14)
            for i, linha in enumerate(linhas):
                ui.desenhar_texto(tela, linha, (caixa.centerx, caixa.y + 10 + i * 18), 10,
                                  (30, 30, 50), "midtop", sombra=False)
