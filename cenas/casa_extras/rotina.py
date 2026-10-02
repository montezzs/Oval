import datetime
import math
import random

import pygame

from settings import *
from core.idioma import t as tr
from core import ui

# ============================================================
# ROTINA DIÁRIA
# ============================================================
# - BAÚ DIÁRIO no chão da CASA: 20, 25, 30, 40, 50, 60, 100
#   OVOEDAS (dias seguidos) + 1 comida. Depois do 7º dia a sequência
#   continua (SEMANA 2, 3...) e todo dia vale 100. Faltou um dia:
#   volta ao 1 (e o ovo avisa que a sequência foi perdida).
# - MISSÕES DO DIA do ROBERT (BRINCAR): 2 missões + o desafio de
#   pontuação; as 3 juntas dão bônus + CAIXA SURPRESA.
# - TOTÓ dança e dá dicas.

PREMIOS_BAU = [20, 25, 30, 40, 50, 60, 100]
COMIDAS_BAU = ["maca", "banana", "leite", "pao_queijo", "suco_limao", "sanduiche", "sorvete"]
PREMIO_DESAFIO = 40

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

_MULTI = None


def _jogos_multi():
    global _MULTI
    if _MULTI is None:
        from jogos import JOGOS
        _MULTI = {j.ID for j in JOGOS if getattr(j, "MULTI", False)}
    return _MULTI


def desafio_do_dia(save):
    # Caminho rápido (chamado todo frame no BRINCAR): o desafio de hoje já existe
    d = save["diario"].get("desafio")
    if isinstance(d, dict) and d.get("dia") == _hoje() and \
            (d.get("feito") or d.get("jogo") not in _jogos_multi()):
        return d
    from jogos import JOGOS
    from jogos import trofeus
    multi = _jogos_multi()
    # (desafios antigos que caíram num jogo de 2 jogadores são refeitos)
    if isinstance(d, dict) and d.get("dia") == _hoje() and (d.get("feito") or d.get("jogo") not in multi):
        return d
    # Só jogos SOLO: nem todo mundo tem um amigo por perto
    rnd = random.Random(_hoje())
    from core import progresso
    solo = [j for j in JOGOS if not getattr(j, "MULTI", False)]
    # Só jogos que o ovo já pode jogar
    jogo = rnd.choice([j for j in solo if progresso.liberado(save, j)] or solo)
    tipo, meta, texto = trofeus.meta_desafio(jogo)
    d = dict(dia=_hoje(), jogo=jogo.ID, tipo=tipo, meta=meta, texto=texto,
             feito=False, pago=False)
    save["diario"]["desafio"] = d
    return d


# ------------------------------------------------------------
# MISSÕES DO DIA (2 missões sorteadas + o desafio de pontuação)
# ------------------------------------------------------------
# Cada missão guarda o valor da estatística quando foi criada;
# o progresso é quanto ela subiu desde então. Completar as 3 (e
# receber com o ROBERT) paga um bônus + uma CAIXA SURPRESA.

POOL_MISSOES = [
    ("partidas", "JOGUE {n} PARTIDAS", (2, 3, 4), 15),
    ("vitorias", "VENÇA {n} PARTIDA(S)", (1, 2), 15),
    ("banhos", "DÊ {n} BANHO(S) NO OVO", (1,), 12),
    ("comidas", "COMA {n} VEZES", (2, 3), 10),
    ("carinhos", "FAÇA {n} CARINHOS", (5, 10), 10),
    ("moedas_jogos", "GANHE {n} OVOEDAS EM JOGOS", (30, 50), 15),
]
BONUS_MISSOES = 40


def _texto_missao(x):
    """Texto da missão no idioma atual (o save guarda o texto em pt)."""
    for stat, modelo, _, _ in POOL_MISSOES:
        if stat == x.get("stat"):
            return tr(modelo, n=x.get("meta", 0))
    return tr(x.get("texto", ""))


def missoes_do_dia(save):
    diario = save["diario"]
    m = diario.get("missoes")
    if isinstance(m, dict) and m.get("dia") == _hoje():
        return m
    rnd = random.Random("missoes" + _hoje() + str(save["nome"]))
    escolhidas = rnd.sample(POOL_MISSOES, 2)
    st = save["stats"]
    lista = []
    for stat, texto, metas, premio in escolhidas:
        n = rnd.choice(metas)
        lista.append(dict(stat=stat, texto=texto.format(n=n), meta=n, base=st.get(stat, 0),
                          premio=premio, pago=False))
    m = dict(dia=_hoje(), lista=lista, bonus=False)
    diario["missoes"] = m
    return m


def progresso_missao(save, mis):
    return max(0, min(mis["meta"], save["stats"].get(mis["stat"], 0) - mis["base"]))


def missoes_resumo(save):
    """(feitas, total) contando o desafio do ROBERT como a 3ª missão."""
    m = missoes_do_dia(save)
    feitas = sum(1 for x in m["lista"] if progresso_missao(save, x) >= x["meta"])
    feitas += 1 if desafio_do_dia(save)["feito"] else 0
    return feitas, len(m["lista"]) + 1


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
        self.calendario = 0.0        # tempo restante do calendário do baú
        self.painel = 0.0            # painel das missões do dia
        self.cal_seq = 0

    # --------------------------------------------------------
    # BAÚ
    # --------------------------------------------------------

    def bau_disponivel(self):
        return self.ctx.app.save["diario"].get("bau_ultimo") != _hoje()

    def abrir_bau(self):
        save = self.ctx.app.save
        diario = save["diario"]
        anterior = diario.get("bau_seq", 0)
        if not isinstance(anterior, int):
            anterior = 0
        seguido = diario.get("bau_ultimo") == _ontem()
        seq = anterior + 1 if seguido else 1
        perdeu = not seguido and anterior > 1
        diario["bau_seq"] = seq
        diario["bau_ultimo"] = _hoje()
        premio = PREMIOS_BAU[min(seq, len(PREMIOS_BAU)) - 1]
        comida = random.choice(COMIDAS_BAU)
        save["comida"][comida] = save["comida"].get(comida, 0) + 1
        save.salvar()
        self.ctx.ganhar_moedas(premio, BAU.center)
        self.ctx.particulas.explodir(BAU.center, [AMARELO, (255, 90, 90), BRANCO, (120, 200, 255)],
                                     50, 380)
        self.ctx.som("vencer")
        from core import itens
        nome = tr(itens.COMIDAS.get(comida, {}).get("nome", comida.upper()))
        if perdeu:
            self.ctx.avisar(tr("SEQUÊNCIA DE {n} DIAS PERDIDA :(  +{premio} e 1 {nome}", n=anterior, premio=premio, nome=nome))
        elif seq > len(PREMIOS_BAU):
            semana = (seq - 1) // 7 + 1
            self.ctx.avisar(tr("{n} DIAS SEGUIDOS! (SEMANA {semana}) +{premio} e 1 {nome}!", n=seq, semana=semana, premio=premio, nome=nome))
        else:
            self.ctx.avisar(tr("BAÚ DO DIA {n}/7: +{premio} OVOEDAS e 1 {nome}!", n=seq, premio=premio, nome=nome))
        self.calendario = 4.0
        self.cal_seq = seq
        from core import progresso
        progresso.definir(self.ctx.app, "streak", seq)
        progresso.ganhar_xp(self.ctx.app, progresso.XP_BAU)

    # --------------------------------------------------------
    # CLIQUES
    # --------------------------------------------------------

    def clicar(self, pos):
        comodo = self.ctx.comodo
        if self.painel > 0 and not ROBERT.collidepoint(pos):
            self.painel = 0.0           # clique fora fecha o painel das missões
            return True
        if comodo == "CASA" and self.bau_disponivel() and BAU.inflate(12, 12).collidepoint(pos):
            self.abrir_bau()
            return True
        if comodo == "BRINCAR":
            if ROBERT.collidepoint(pos) and not TOTO.collidepoint(pos):
                self._falar_robert()
                return True
            if TOTO.collidepoint(pos):
                self.danca_toto = 2.0
                self._mostrar(tr(random.choice(DICAS)), (TOTO.centerx - 120, TOTO.y - 10))
                self.ctx.som("boing")
                return True
        return False

    def _falar_robert(self):
        """Paga o que estiver pronto e mostra o painel das missões."""
        from core import progresso
        app = self.ctx.app
        save = app.save
        m = missoes_do_dia(save)
        pagou = 0
        for mis in m["lista"]:
            if not mis["pago"] and progresso_missao(save, mis) >= mis["meta"]:
                mis["pago"] = True
                pagou += mis["premio"]
                progresso.contar(app, "missoes")
                progresso.ganhar_xp(app, 10)
        if pagou:
            self.ctx.ganhar_moedas(pagou, (ROBERT.centerx, ROBERT.y + 140))
        d = desafio_do_dia(save)
        if d["feito"] and not d["pago"]:
            progresso.contar(app, "missoes")
        todas = all(x["pago"] for x in m["lista"]) and (d["pago"] or d["feito"])
        if todas and not m["bonus"]:
            m["bonus"] = True
            from core import caixa
            item, nome, raridade, consolo = caixa.sortear(save)
            self.ctx.ganhar_moedas(BONUS_MISSOES, (ROBERT.centerx, ROBERT.y + 100))
            progresso.contar(app, "caixas")
            texto = tr("+{n} OVOEDAS", n=consolo) if consolo or item is None else tr(nome)
            app.toasts.adicionar(tr("3 MISSÕES COMPLETAS!"), tr("CAIXA SURPRESA: ") + texto,
                                 f"+{BONUS_MISSOES}", "levelup")
            self.ctx.particulas.explodir(ROBERT.center, [AMARELO, BRANCO, (255, 120, 190)], 60, 400)
        save.salvar()
        self.painel = 7.0
        self._desafio_robert(save)

    def _desafio_robert(self, save):
        d = desafio_do_dia(save)
        if d["feito"] and not d["pago"]:
            d["pago"] = True
            save.salvar()
            self.ctx.ganhar_moedas(PREMIO_DESAFIO, (ROBERT.centerx, ROBERT.y + 120))
            self.ctx.som("vencer")
            from core import progresso
            progresso.contar(self.ctx.app, "desafios")
            progresso.ganhar_xp(self.ctx.app, progresso.XP_DESAFIO)
            self.ctx.avisar(tr("PARABÉNS! Desafio cumprido: +{n} OVOEDAS!", n=PREMIO_DESAFIO))
        self.ctx.som("selecionar")

    def _mostrar(self, texto, pos):
        self.balao = texto
        self.tempo_balao = 5.0
        self.pos_balao = pos

    # --------------------------------------------------------

    def atualizar(self, dt):
        self.tempo_balao = max(0.0, self.tempo_balao - dt)
        self.danca_toto = max(0.0, self.danca_toto - dt)
        self.calendario = max(0.0, self.calendario - dt)
        self.painel = max(0.0, self.painel - dt)
        if self.ctx.comodo != "BRINCAR":
            self.painel = 0.0
        if self.ctx.comodo != "CASA":
            self.calendario = 0.0

    def desenhar_missoes(self, tela):
        """Painel com as 3 missões do dia (abre ao falar com o ROBERT)."""
        if self.painel <= 0:
            return
        save = self.ctx.app.save
        m = missoes_do_dia(save)
        d = desafio_do_dia(save)
        k = min(1.0, self.painel / 0.3, (7.0 - self.painel) / 0.2)
        caixa = pygame.Rect(0, 0, 470, 210)
        caixa.topright = (ROBERT.x - 10, 170 - int(20 * (1 - k)))
        ui.painel(tela, caixa, (30, 34, 60), AMARELO, 16, 3)
        ui.desenhar_texto(tela, tr("MISSÕES DO DIA"), (caixa.centerx, caixa.y + 12), 14, AMARELO, "midtop")
        linhas = [(_texto_missao(x), progresso_missao(save, x), x["meta"], x["premio"], x["pago"]) for x in m["lista"]]
        linhas.append((tr("DESAFIO: ") + tr(d["texto"]), 1 if d["feito"] else 0, 1, PREMIO_DESAFIO, d["pago"]))
        for i, (texto, feito, meta, premio, pago) in enumerate(linhas):
            y = caixa.y + 44 + i * 40
            r = pygame.Rect(caixa.x + 14, y, caixa.w - 28, 34)
            ok = feito >= meta
            pygame.draw.rect(tela, (50, 70, 50) if ok else (44, 48, 80), r, border_radius=8)
            tam = ui.tamanho_que_cabe(texto, r.w - 120, (10, 8))
            ui.desenhar_texto(tela, texto, (r.x + 10, r.y + 6), tam, BRANCO, "topleft")
            barra = pygame.Rect(r.x + 10, r.bottom - 10, r.w - 130, 5)
            pygame.draw.rect(tela, (70, 70, 100), barra, border_radius=3)
            pygame.draw.rect(tela, (120, 255, 150) if ok else AMARELO,
                             (barra.x, barra.y, max(2, int(barra.w * feito / meta)), barra.h), border_radius=3)
            if pago:
                ui.check(tela, (r.right - 20, r.centery), 14)
            else:
                ui.desenhar_texto(tela, f"{feito}/{meta}", (r.right - 70, r.centery), 10, BRANCO, "midright")
                ui.moeda(tela, (r.right - 54, r.centery), 6)
                ui.desenhar_texto(tela, str(premio), (r.right - 44, r.centery), 10, AMARELO, "midleft")
        rodape = tr("BÔNUS JÁ RECEBIDO!") if m["bonus"] else tr("COMPLETE AS 3: +{n} E UMA CAIXA SURPRESA!", n=BONUS_MISSOES)
        ui.desenhar_texto(tela, rodape, (caixa.centerx, caixa.bottom - 12), 8, (230, 220, 170), "midbottom")

    def desenhar_calendario(self, tela):
        """7 caixinhas da semana do baú (as abertas com ✓, a de hoje pulsando)."""
        if self.calendario <= 0:
            return
        t = self.ctx.tempo
        k = min(1.0, self.calendario / 0.3, (4.0 - self.calendario) / 0.25)
        seq = self.cal_seq
        semana = (seq - 1) // 7
        hoje = (seq - 1) % 7
        caixa = pygame.Rect(0, 0, 560, 118)
        caixa.midtop = (LARGURA // 2, 170 - int(30 * (1 - k)))
        ui.painel(tela, caixa, (40, 30, 24), AMARELO, 16, 3)
        titulo = tr("BAÚ DIÁRIO") if semana == 0 else tr("BAÚ DIÁRIO  •  SEMANA {n}", n=semana + 1)
        ui.desenhar_texto(tela, titulo, (caixa.centerx, caixa.y + 12), 12, AMARELO, "midtop")
        for i in range(7):
            r = pygame.Rect(caixa.x + 20 + i * 76, caixa.y + 36, 66, 68)
            aberto = i <= hoje
            if i == hoje:
                r = r.inflate(int(6 * abs(math.sin(t * 5))), int(6 * abs(math.sin(t * 5))))
            cor = (90, 70, 30) if aberto else (60, 50, 44)
            pygame.draw.rect(tela, cor, r, border_radius=10)
            pygame.draw.rect(tela, AMARELO if i == hoje else (150, 120, 80), r, 3 if i == hoje else 2,
                             border_radius=10)
            valor = PREMIOS_BAU[i] if semana == 0 else PREMIOS_BAU[-1]
            ui.desenhar_texto(tela, tr("DIA {n}", n=i + 1 + semana * 7), (r.centerx, r.y + 8), 8,
                              BRANCO if aberto else (170, 160, 150), "midtop")
            ui.moeda(tela, (r.centerx - 12, r.y + 40), 8)
            ui.desenhar_texto(tela, str(valor), (r.centerx - 2, r.y + 40), 10,
                              AMARELO if aberto else (170, 160, 150), "midleft")
            if aberto and i < hoje:
                ui.check(tela, (r.right - 12, r.bottom - 12), 12)

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
            save = self.ctx.app.save
            d = desafio_do_dia(save)
            m = missoes_do_dia(save)
            feitas, total = missoes_resumo(save)
            pendente = not d["pago"] or not m["bonus"] or \
                any(not x["pago"] and progresso_missao(save, x) >= x["meta"] for x in m["lista"])
            # Exclamação sobre o ROBERT quando há missão / prêmio
            if pendente:
                pronto = (d["feito"] and not d["pago"]) or \
                    any(not x["pago"] and progresso_missao(save, x) >= x["meta"] for x in m["lista"])
                cor = (120, 255, 150) if pronto else AMARELO
                y = ROBERT.y + 10 + math.sin(t * 4) * 4
                ui.desenhar_texto(tela, "!", (ROBERT.centerx + 40, y), 28, cor, "center")
                ui.desenhar_texto(tela, f"{feitas}/{total}", (ROBERT.centerx + 40, y + 26), 10, cor, "center")
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
