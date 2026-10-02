import math
import random

import pygame

from settings import *
from core import assets, ui
from core.jogador import BOCA_TRISTE, BOCA_ABERTA, OLHO_FECHADO
from jogos.base_hibrido import MiniJogoHibrido
from jogos.base_multi import TECLAS_MOVER, TECLAS_ACAO, CORES_JOGADOR

# ============================================================
# EGG FIGHTER (LUTA DE DEDÃO COM OVOS)
# ============================================================
# Duas mãos entrelaçadas no centro; no lugar dos polegares, dois
# OVOS. Incline, estique, abaixe para esquivar e ATAQUE para
# prender o ovo do outro por baixo do seu. Segure por 3 segundos
# e o round é seu! Quem está preso aperta tudo para escapar.
# Melhor de 3.

PIVOS = [(470, 560), (554, 560)]
COMPR = 160                 # do pivô até o centro do ovo (ext = 1)
ALT_OVO = 66
ANG_MAX = 75
EXT_MIN, EXT_MAX = 0.55, 1.35
ACEL_ANG = 900
TEMPO_ATAQUE = 0.34
TEMPO_PRENDER = 3.0
FUGA_MAX = 12.0
FUGA_DECAI = 2.5
ESQUIVA_MAX = 0.55
ESQUIVA_RECARGA = 0.9
TEMPO_ROUND = 25.0
RAIO_CONTATO = 64

PELE = (240, 200, 160)
PELE_2 = (225, 182, 142)
PELE_BORDA = (170, 120, 90)

BOTS = [
    dict(reacao=0.6, ataque=0.3, esquiva=0.1, fuga=3.0, alto=0.2, mira=False),
    dict(reacao=0.3, ataque=0.55, esquiva=0.4, fuga=5.5, alto=0.6, mira=True),
    dict(reacao=0.12, ataque=0.85, esquiva=0.75, fuga=8.0, alto=0.9, mira=True),
]


class Dedao:

    def __init__(self, i):
        self.i = i
        self.lado = 1 if i == 0 else -1      # para onde fica o adversário
        self.ang = 0.0
        self.vang = 0.0
        self.ext = 1.0
        self.estado = "livre"               # livre / ataque / tonto / preso / prendendo
        self.t = 0.0
        self.recarga = 0.0
        self.esquiva = 0.0                  # tempo abaixado
        self.esquiva_rec = 0.0
        self.fuga = 0.0
        self.preso_t = 0.0
        self.total_preso = 0.0              # tempo prendendo neste round
        self.ang0 = 0.0
        self.invul = 0.0

    def ponta(self):
        a = math.radians(self.ang)
        px, py = PIVOS[self.i]
        return px + math.sin(a) * COMPR * self.ext, py - math.cos(a) * COMPR * self.ext

    def mudar(self, estado):
        self.estado = estado
        self.t = 0.0


class ThumbFighter(MiniJogoHibrido):

    ID = "thumb_fighter"
    TITULO = "EGG FIGHTER"
    TITULO_CURTO = "EGG FIGHTER"
    DESCRICAO = "Luta de dedão com ovos! Prenda o ovo do outro por 3 segundos para vencer."
    COR = (220, 120, 60)
    INSTRUCOES = [
        "INCLINE (ESQ/DIR), ESTIQUE (CIMA) E ESQUIVE (BAIXO).",
        "ATAQUE (J1 ESPAÇO / J2 ENTER) E CAIA POR CIMA DO OUTRO OVO!",
        "SEGURE A TECLA 3 S PARA VENCER O ROUND. PRESO? APERTE TUDO PARA FUGIR!",
        "MELHOR DE 3.",
    ]
    CONTROLES_J1 = "WASD + ESPAÇO"
    CONTROLES_J2 = "SETAS + ENTER"
    CONTAGEM = False
    MOEDAS_PARTIDA = 8
    MOEDAS_VITORIA_J1 = 5

    # --------------------------------------------------------
    # CENÁRIO: mesa com holofote
    # --------------------------------------------------------

    @classmethod
    def criar_fundo(cls, jogador):
        sup = ui.gradiente(LARGURA, ALTURA, (70, 40, 60), (150, 80, 60))
        # papel de parede listrado
        for x in range(0, LARGURA, 64):
            pygame.draw.rect(sup, (86, 50, 70), (x, 0, 28, 440))
        # quadro de ringue na parede
        q = pygame.Rect(0, 0, 300, 150)
        q.midtop = (LARGURA // 2, 60)
        pygame.draw.rect(sup, (90, 60, 30), q.inflate(20, 20), border_radius=6)
        pygame.draw.rect(sup, (60, 120, 200), q)
        for k in range(3):
            y = q.y + 40 + k * 30
            pygame.draw.line(sup, (240, 240, 240), (q.x + 10, y), (q.right - 10, y), 3)
        for x in (q.x + 10, q.right - 10):
            pygame.draw.rect(sup, (230, 60, 60), (x - 5, q.y + 30, 10, 100))
        # mesa
        pygame.draw.rect(sup, (120, 70, 40), (0, 440, LARGURA, ALTURA - 440))
        pygame.draw.rect(sup, (150, 92, 52), (0, 440, LARGURA, 16))
        for y in (500, 580, 670):
            pygame.draw.line(sup, (100, 58, 34), (0, y), (LARGURA, y), 3)
        for x, y in ((140, 470), (400, 520), (760, 470), (880, 600), (240, 620), (620, 690)):
            pygame.draw.line(sup, (100, 58, 34), (x, y), (x, y + 30), 3)
        # holofote
        luz = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        pygame.draw.polygon(luz, (255, 240, 200, 26), [(440, 0), (584, 0), (800, 700), (224, 700)])
        pygame.draw.ellipse(luz, (255, 240, 200, 40), (262, 560, 500, 130))
        sup.blit(luz, (0, 0))
        return sup

    @classmethod
    def desenhar_icone(cls, sup, jogador):
        w, h = sup.get_size()
        mao = pygame.Rect(0, 0, int(w * 0.5), int(h * 0.28))
        mao.midbottom = (w // 2, h - 2)
        pygame.draw.rect(sup, PELE_BORDA, mao.inflate(4, 4), border_radius=h // 8)
        pygame.draw.rect(sup, PELE, mao, border_radius=h // 8)
        for k in range(4):
            x = mao.x + mao.w * (k + 0.5) / 4
            pygame.draw.line(sup, PELE_BORDA, (x, mao.y + 4), (x, mao.bottom - 4), 2)
        for i, ang in ((0, -18), (1, 22)):
            x = w // 2 + (-1 if i == 0 else 1) * int(w * 0.12)
            pygame.draw.line(sup, PELE, (x, mao.y + 4), (x + (4 if i == 0 else -4), mao.y - h * 0.12),
                             max(3, int(w * 0.08)))
        a = jogador.aparencia()
        jogador.desenhar(sup, (int(w * 0.38), int(h * 0.4)), h * 0.3, angulo=-15)
        jogador.desenhar(sup, (int(w * 0.62), int(h * 0.34)), h * 0.3,
                         aparencia=((a[0] + 1) % len(assets.OVOS), a[1], a[2], a[3]), espelhar=True, angulo=15)

    # --------------------------------------------------------

    def __init__(self, app, menu):
        self.seguradas = set()
        self._sprites = {}
        self.dedos = [Dedao(0), Dedao(1)]
        super().__init__(app, menu)

    def _montar_menu_inicio(self):
        super()._montar_menu_inicio()
        for b in self.menu_inicio.botoes[:len(self.OPCOES)]:
            b.tamanho = ui.tamanho_que_cabe(b.rotulo, b.rect.w - 14, (14, 12, 10, 8))

    def reiniciar(self):
        self._sprites.clear()
        self.rounds = [0, 0]
        self.n_round = 0
        self.banner = None
        self.bot = dict(t=0.0, dx=0, cima=False, baixo=False, hold=0.0, mash=0.0)
        self.seguradas.clear()
        self._novo_round()

    def _novo_round(self):
        self.n_round += 1
        self.dedos = [Dedao(0), Dedao(1)]
        self.fase = "intro"
        self.t_fase = 0.0
        self.timer = TEMPO_ROUND
        self.pressas = [0, 0]
        self.banner = None

    def _banner_(self, texto, cor, tempo, sub=None):
        self.banner = [texto, cor, tempo, sub]

    # --------------------------------------------------------
    # ENTRADA
    # --------------------------------------------------------

    def evento(self, e):
        if e.type == pygame.KEYDOWN:
            self.seguradas.add(e.key)
        elif e.type == pygame.KEYUP:
            self.seguradas.discard(e.key)
        elif e.type == pygame.WINDOWFOCUSLOST:
            self.seguradas.clear()
        super().evento(e)

    def _segura(self, k):
        return k in self.seguradas or pygame.key.get_pressed()[k]

    def evento_jogo(self, e):
        if e.type != pygame.KEYDOWN or self.fase != "luta":
            return
        for i in (0, 1):
            if i == 1 and self.solo:
                continue
            d = self.dedos[i]
            if d.estado == "preso":
                if e.key in TECLAS_ACAO[i] or e.key in TECLAS_MOVER[i].values():
                    self.pressas[i] += 1
            elif e.key in TECLAS_ACAO[i]:
                self._atacar(i)

    def _entrada(self, i, dt):
        if i == 1 and self.solo:
            return self._bot(dt)
        m = TECLAS_MOVER[i]
        dx = (1 if self._segura(m["dir"]) else 0) - (1 if self._segura(m["esq"]) else 0)
        segura = any(self._segura(k) for k in TECLAS_ACAO[i])
        return dx, self._segura(m["cima"]), self._segura(m["baixo"]), segura

    def _atacar(self, i):
        d = self.dedos[i]
        if d.estado != "livre" or d.recarga > 0:
            return
        d.mudar("ataque")
        d.ang0 = d.ang
        d.esquiva = 0.0
        self.som("asa", 0.6)

    # --------------------------------------------------------
    # LÓGICA
    # --------------------------------------------------------

    def atualizar_jogo(self, dt):
        self.t_fase += dt
        if self.banner:
            self.banner[2] -= dt
            if self.banner[2] <= 0:
                self.banner = None

        if self.fase == "intro":
            canto = ["UM,", "DOIS,", "TRÊS,", "QUATRO..."]
            k = int(self.t_fase / 0.4)
            if k < 4 and (self.banner is None or self.banner[0] != canto[k]):
                self._banner_(canto[k], BRANCO, 0.4, f"ROUND {self.n_round}")
                self.som("tic", 0.6)
            elif k == 4 and (self.banner is None or self.banner[0] != "GUERRA DE DEDÃO!"):
                self._banner_("GUERRA DE DEDÃO!", AMARELO, 0.8)
                self.som("bandeira", 0.7)
            for d in self.dedos:
                d.ang = math.sin(self.t_fase * math.pi * 2.5) * 25 * (1 if d.i == 0 else -1)
            if self.t_fase > 2.2:
                self.fase = "luta"
                self.t_fase = 0.0
            return

        if self.fase == "ponto":
            for d in self.dedos:
                d.t += dt
            if self.t_fase > 1.8:
                v = 0 if self.rounds[0] >= 2 else (1 if self.rounds[1] >= 2 else None)
                if v is not None:
                    self.terminar_multi(v, [f"ROUNDS  {self.rounds[0]} × {self.rounds[1]}"])
                elif self.n_round >= 5:
                    self.terminar_multi(None, [f"ROUNDS  {self.rounds[0]} × {self.rounds[1]}"])
                else:
                    self._novo_round()
            return

        self.timer -= dt
        entradas = [self._entrada(0, dt), self._entrada(1, dt)]
        for i, d in enumerate(self.dedos):
            self._atualizar_dedo(d, self.dedos[1 - i], entradas[i], dt)
        if self.fase == "luta":
            self._contatos()
        if self.fase == "luta" and self.timer <= 0:
            self.timer = 0
            a, b = self.dedos[0].total_preso, self.dedos[1].total_preso
            v = None if abs(a - b) < 0.05 else (0 if a > b else 1)
            self._ponto(v, "TEMPO!")

    def _atualizar_dedo(self, d, o, entrada, dt):
        dx, cima, baixo, segura = entrada
        d.t += dt
        d.recarga = max(0.0, d.recarga - dt)
        d.esquiva_rec = max(0.0, d.esquiva_rec - dt)
        d.invul = max(0.0, d.invul - dt)
        ext_alvo = 1.0

        if d.estado == "livre":
            d.vang += dx * ACEL_ANG * dt
            if baixo and d.esquiva_rec <= 0:
                d.esquiva += dt
                if d.esquiva > ESQUIVA_MAX:
                    d.esquiva_rec = ESQUIVA_RECARGA
                    d.esquiva = 0.0
                ext_alvo = EXT_MIN
            else:
                if d.esquiva > 0:
                    d.esquiva_rec = ESQUIVA_RECARGA * 0.5
                d.esquiva = 0.0
                ext_alvo = 1.18 if cima else 1.0
        elif d.estado == "ataque":
            ox, oy = o.ponta()
            px, py = PIVOS[d.i]
            tx, ty = ox, oy - 44
            desejo = math.degrees(math.atan2(tx - px, py - ty))
            # Mira automática curta: é preciso se inclinar para acertar
            desejo = max(d.ang0 - 18, min(d.ang0 + 18, desejo))
            if d.t < 0.1:
                ext_alvo = EXT_MAX
                d.vang += (desejo - d.ang) * 20 * dt
            else:
                ext_alvo = max(0.7, min(EXT_MAX, math.hypot(tx - px, ty - py) / COMPR))
                d.ang += (desejo - d.ang) * min(1.0, 14 * dt)
            if d.t >= TEMPO_ATAQUE:
                d.mudar("livre")
                d.recarga = 0.35
        elif d.estado == "tonto":
            d.vang += math.sin(d.t * 20) * 600 * dt
            ext_alvo = 0.85
            if d.t > 0.6:
                d.mudar("livre")
        elif d.estado == "prendendo":
            d.vang *= 0.5
            ext_alvo = d.ext
            if not segura:
                self._soltar(d, o, "SOLTOU!")
                return
            d.preso_t += dt
            d.total_preso += dt
            if d.preso_t >= TEMPO_PRENDER:
                self._ponto(d.i, "PRESO!")
                return
        elif d.estado == "preso":
            px, py = PIVOS[d.i]
            ax, ay = o.ponta()
            tx, ty = ax, ay + 46
            d.ang = max(-ANG_MAX, min(ANG_MAX, math.degrees(math.atan2(tx - px, py - ty))))
            d.ext = max(0.4, min(EXT_MAX, math.hypot(tx - px, ty - py) / COMPR))
            d.vang = 0.0
            d.fuga = max(0.0, d.fuga + self.pressas[d.i] - FUGA_DECAI * dt)
            if self.pressas[d.i]:
                self.particulas.explodir(d.ponta(), [BRANCO, (200, 230, 255)], 3, 160, 0.3)
            self.pressas[d.i] = 0
            if d.fuga >= FUGA_MAX:
                self._soltar(o, d, "ESCAPOU!", fugiu=True)
            return

        d.vang *= max(0.0, 1 - 5 * dt)
        d.ang += d.vang * dt
        if abs(d.ang) > ANG_MAX:
            d.ang = math.copysign(ANG_MAX, d.ang)
            d.vang *= -0.3
        d.ext += (ext_alvo - d.ext) * min(1.0, 10 * dt)

    def _contatos(self):
        a, b = self.dedos
        pa, pb = a.ponta(), b.ponta()
        dist = math.hypot(pa[0] - pb[0], pa[1] - pb[1])
        if dist < 54 and a.estado != "preso" and b.estado != "preso":
            # os ovos se empurram
            s = 1 if pb[0] >= pa[0] else -1
            a.vang -= s * 120
            b.vang += s * 120
        if dist >= RAIO_CONTATO:
            return
        atacando = [d for d in (a, b) if d.estado == "ataque" and d.t >= 0.08]
        if not atacando:
            return
        if len(atacando) == 2:
            alto, baixo = (a, b) if pa[1] < pb[1] else (b, a)
            self._prender(alto, baixo)
            return
        d = atacando[0]
        o = b if d is a else a
        pd, po = d.ponta(), o.ponta()
        if o.invul > 0:
            return
        if o.esquiva > 0 and o.ext < 0.8:
            d.mudar("tonto")
            self.textos.adicionar("ESQUIVOU!", (po[0], po[1] - 60), (140, 220, 255), 12)
            self.som("boing", 0.6)
        elif pd[1] < po[1] - 10:
            self._prender(d, o)
        else:
            d.mudar("tonto")
            o.vang += (1 if o.i == 0 else -1) * -80
            self.textos.adicionar("BATEU!", (pd[0], pd[1] - 50), (255, 200, 120), 12)
            self.som("bater", 0.5)
            self.tremer(0.1)

    def _prender(self, d, o):
        d.mudar("prendendo")
        d.preso_t = 0.0
        o.mudar("preso")
        o.fuga = 0.0
        o.esquiva = 0.0
        self.pressas[o.i] = 0
        self.particulas.explodir(o.ponta(), [AMARELO, BRANCO, self.cor(d.i)], 26, 360, 0.6)
        self.textos.adicionar("PEGOU!", (o.ponta()[0], o.ponta()[1] - 70), AMARELO, 16)
        self.som("bater")
        self.tremer(0.3)

    def _soltar(self, d, o, texto, fugiu=False):
        """d estava prendendo, o estava preso."""
        d.mudar("tonto" if fugiu else "livre")
        d.recarga = 0.5
        o.mudar("livre")
        o.invul = 0.6
        o.fuga = 0.0
        o.ext = 0.9
        o.vang = (1 if o.i == 0 else -1) * -200
        p = o.ponta()
        self.textos.adicionar(texto, (p[0], p[1] - 70), (140, 255, 160) if fugiu else BRANCO, 14)
        if fugiu:
            self.particulas.explodir(p, [(140, 255, 160), BRANCO], 20, 300, 0.5)
            self.som("boing")

    def _ponto(self, v, texto):
        self.fase = "ponto"
        self.t_fase = 0.0
        if v is None:
            self._banner_(texto, AMARELO, 1.8, "NINGUÉM PONTUA")
            self.som("erro", 0.6)
            return
        self.rounds[v] += 1
        self._banner_(texto, AMARELO, 1.8, f"PONTO DE {self.nome(v).upper()}")
        self.som("vencer" if v == 0 or not self.solo else "perder", 0.8)
        for k in range(3):
            self.particulas.explodir((LARGURA // 2 + random.randint(-200, 200),
                                      random.randint(160, 320)),
                                     [CORES_JOGADOR[v], AMARELO, BRANCO], 26, 360, 1.0)
        self.tremer(0.3)

    # --------------------------------------------------------
    # BOT (é o dedão 1)
    # --------------------------------------------------------

    def _bot(self, dt):
        cfg = BOTS[self.dificuldade]
        b = self.bot
        me, op = self.dedos[1], self.dedos[0]
        b["t"] -= dt
        b["hold"] -= dt
        if me.estado == "preso":
            b["mash"] += cfg["fuga"] * dt * random.uniform(0.7, 1.3)
            while b["mash"] >= 1:
                b["mash"] -= 1
                self.pressas[1] += 1
            return 0, False, False, False
        if me.estado == "prendendo":
            return 0, False, False, True
        if b["hold"] <= 0:
            b["baixo"] = False
        # esquiva quando o outro ataca
        if op.estado == "ataque" and op.t < 0.1 and b["t"] <= 0.05 and not b["baixo"]:
            b["t"] = 0.15
            if random.random() < cfg["esquiva"]:
                b["baixo"], b["hold"] = True, 0.35
        if b["t"] <= 0:
            b["t"] = cfg["reacao"] * random.uniform(0.7, 1.3)
            pm, po = me.ponta(), op.ponta()
            dist = math.hypot(pm[0] - po[0], pm[1] - po[1])
            mais_alto = pm[1] < po[1] - 12
            b["cima"] = random.random() < cfg["alto"]
            if cfg["mira"]:
                alvo = -20 if dist > 110 else (10 if mais_alto else -5)
                alvo += op.ang * 0.4
                b["dx"] = -1 if me.ang > alvo + 6 else (1 if me.ang < alvo - 6 else 0)
            else:
                b["dx"] = random.choice((-1, 0, 0, 1))
            if dist < 150 and me.estado == "livre":
                chance = cfg["ataque"] * (1.0 if mais_alto or not cfg["mira"] else 0.3)
                if random.random() < chance:
                    self._atacar(1)
        return b["dx"], b["cima"] and not b["baixo"], b["baixo"], False

    # --------------------------------------------------------
    # DESENHO
    # --------------------------------------------------------

    def _ovo(self, i, expr, ang):
        q = int(round(ang / 3.0)) * 3
        chave = (i, expr, q)
        s = self._sprites.get(chave)
        if s is None:
            a = self.aparencia(i)
            if expr == "preso":
                a = (a[0], a[1], OLHO_FECHADO, BOCA_TRISTE)
            elif expr == "tonto":
                a = (a[0], a[1], a[2], BOCA_TRISTE)
            elif expr == "ataque":
                a = (a[0], a[1], a[2], BOCA_ABERTA)
            dono = self._vizinho if (i == 1 and self._vizinho is not None) else self.jogador
            s = dono.avatar(ALT_OVO, a)
            if i == 1:
                s = pygame.transform.flip(s, True, False)
            if expr == "preso":
                w, h = s.get_size()
                s = pygame.transform.smoothscale(s, (int(w * 1.12), int(h * 0.82)))
            s = pygame.transform.rotate(s, -q)
            if len(self._sprites) > 600:
                self._sprites.clear()
            self._sprites[chave] = s
        return s

    def _maos(self):
        s = getattr(self, "_sup_maos", None)
        if s is None:
            s = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
            # mangas
            for i, (x0, x1) in enumerate(((0, 330), (LARGURA, LARGURA - 330))):
                cor = ui.escurecer(CORES_JOGADOR[i], 40)
                pts = [(x0, 650), (x1, 600), (x1, 720), (x0, 720)]
                pygame.draw.polygon(s, cor, pts)
                pygame.draw.polygon(s, ui.escurecer(cor, 40), pts, 4)
            # punhos
            punho = pygame.Rect(0, 0, 300, 130)
            punho.midtop = (LARGURA // 2, 548)
            pygame.draw.rect(s, PELE_BORDA, punho.inflate(8, 8), border_radius=48)
            pygame.draw.rect(s, PELE, punho, border_radius=48)
            pygame.draw.rect(s, PELE_BORDA, (punho.x - 60, 580, 70, 90), border_radius=30)
            pygame.draw.rect(s, PELE, (punho.x - 56, 584, 66, 82), border_radius=28)
            pygame.draw.rect(s, PELE_BORDA, (punho.right - 10, 580, 70, 90), border_radius=30)
            pygame.draw.rect(s, PELE, (punho.right - 10, 584, 66, 82), border_radius=28)
            # dedos entrelaçados
            for k in range(4):
                y = 596 + k * 22
                esq = k % 2 == 0
                r = pygame.Rect(0, 0, 150, 26)
                if esq:
                    r.midleft = (LARGURA // 2 - 70, y)
                else:
                    r.midright = (LARGURA // 2 + 70, y)
                pygame.draw.rect(s, PELE_BORDA, r.inflate(4, 4), border_radius=13)
                pygame.draw.rect(s, PELE if esq else PELE_2, r, border_radius=13)
                unha = pygame.Rect(0, 0, 16, 14)
                unha.center = (r.right - 12, y) if esq else (r.x + 12, y)
                pygame.draw.ellipse(s, (250, 220, 205), unha)
            self._sup_maos = s
        return s

    def desenhar_jogo(self, tela):
        tela.blit(self.fundo(self.jogador), (0, 0))
        # dedões (base do polegar) por trás das mãos
        for d in self.dedos:
            px, py = PIVOS[d.i]
            a = math.radians(d.ang)
            dist = max(10.0, COMPR * d.ext - 26)
            fx, fy = px + math.sin(a) * dist, py - math.cos(a) * dist
            pygame.draw.line(tela, PELE_BORDA, (px, py), (fx, fy), 40)
            pygame.draw.line(tela, PELE, (px, py), (fx, fy), 32)
            pygame.draw.circle(tela, PELE, (int(fx), int(fy)), 16)
        tela.blit(self._maos(), (0, 0))
        # ovos (quem prende por cima)
        ordem = sorted(self.dedos, key=lambda d: d.estado == "prendendo")
        for d in ordem:
            expr = {"preso": "preso", "tonto": "tonto", "ataque": "ataque",
                    "prendendo": "ataque"}.get(d.estado, "normal")
            if d.invul > 0 and int(self.tempo * 20) % 2:
                continue
            s = self._ovo(d.i, expr, d.ang)
            p = d.ponta()
            tela.blit(s, s.get_rect(center=(int(p[0]), int(p[1]))))
            if d.estado == "tonto":
                for k in range(3):
                    a = self.tempo * 5 + k * math.tau / 3
                    ui.estrela(tela, (int(p[0] + math.cos(a) * 30), int(p[1] - 48 + math.sin(a) * 6)),
                               6, AMARELO, a)
        # progresso da prisão
        for d in self.dedos:
            if d.estado == "prendendo":
                o = self.dedos[1 - d.i]
                p = o.ponta()
                r = pygame.Rect(0, 0, 124, 124)
                r.center = (int(p[0]), int(p[1]) - 20)
                frac = min(1.0, d.preso_t / TEMPO_PRENDER)
                pygame.draw.arc(tela, (40, 30, 30), r, 0, math.tau, 8)
                pygame.draw.arc(tela, CORES_JOGADOR[d.i], r, math.pi / 2,
                                math.pi / 2 + math.tau * frac, 8)
                n = min(3, int(d.preso_t) + 1)
                ui.desenhar_texto(tela, str(n), (r.centerx, r.y - 16), 20, AMARELO, "center")
                # barra de fuga
                bw = 140
                bx = int(p[0]) - bw // 2
                pygame.draw.rect(tela, (30, 20, 30), (bx - 3, 520 - 3, bw + 6, 16))
                pygame.draw.rect(tela, (140, 255, 160), (bx, 520, int(bw * min(1.0, o.fuga / FUGA_MAX)),
                                                         10))
                if not (o.i == 1 and self.solo):
                    ui.desenhar_texto(tela, "APERTE TUDO!", (int(p[0]), 546), 10, BRANCO, "center")
        self.particulas.desenhar(tela)
        self.textos.desenhar(tela)
        if self.banner and self.estado != "inicio":
            texto, cor, _, sub = self.banner
            ui.desenhar_texto(tela, texto, (LARGURA // 2, 260), 40 if len(texto) < 12 else 30,
                              cor, "center")
            if sub:
                ui.desenhar_texto(tela, sub, (LARGURA // 2, 310), 14, BRANCO, "center")

    def desenhar_hud(self, tela):
        for i in (0, 1):
            nome = self.nome(i).upper()
            sup = ui.texto(nome, 14, CORES_JOGADOR[i])
            anc = "topleft" if i == 0 else "topright"
            pos = (20, 18) if i == 0 else (LARGURA - 84, 18)
            r = sup.get_rect(**{anc: pos}).inflate(20, 14)
            ui.painel(tela, r, (30, 20, 30), BRANCO, 10, 2, sombra=False)
            tela.blit(sup, sup.get_rect(center=r.center))
            for k in range(2):
                cx = (r.x + 12 + k * 24) if i == 0 else (r.right - 12 - k * 24)
                pygame.draw.circle(tela, (40, 30, 40), (cx, r.bottom + 16), 9)
                pygame.draw.circle(tela, AMARELO if self.rounds[i] > k else (90, 80, 90),
                                   (cx, r.bottom + 16), 7)
        caixa = pygame.Rect(0, 0, 84, 50)
        caixa.midtop = (LARGURA // 2, 12)
        ui.painel(tela, caixa, (30, 20, 30), (230, 170, 80), 10, 3, sombra=False)
        cor = (255, 90, 80) if self.timer < 5 else AMARELO
        ui.desenhar_texto(tela, str(int(math.ceil(self.timer))), caixa.center, 20, cor, "center")

    def _desenhar_inicio(self, tela):
        ui.veu(tela, 150)
        topo = 24
        caixa = pygame.Rect(0, topo, 780, ALTURA - topo - 24)
        caixa.centerx = LARGURA // 2
        ui.painel(tela, caixa, (40, 26, 36), self.COR, 22, 5)
        ui.desenhar_texto(tela, self.TITULO, (LARGURA // 2, topo + 20), 28, AMARELO, "midtop")
        ui.desenhar_texto(tela, "VS BOT OU 2 JOGADORES", (LARGURA // 2, topo + 58), 12,
                          (255, 200, 160), "midtop")
        y_ovos = topo + 124
        for i, x in ((0, caixa.x + 150), (1, caixa.right - 150)):
            balanco = math.sin(self.tempo * 3 + i * 1.5) * 4
            self.desenhar_ovo(tela, i, (x, y_ovos + balanco), 60, espelhar=(i == 1))
            ui.desenhar_texto(tela, self.nome(i), (x, y_ovos + 42), 14, CORES_JOGADOR[i], "midtop")
            ctrl = self.CONTROLES_J1 if i == 0 else self.CONTROLES_J2
            ui.desenhar_texto(tela, ctrl, (x, y_ovos + 64), 10, BRANCO, "midtop")
        ui.desenhar_texto(tela, "VS", (LARGURA // 2, y_ovos), 32, AMARELO, "center")
        y = y_ovos + 92
        for linha in self.INSTRUCOES:
            for sub in ui.quebrar_linhas(linha, 10, caixa.w - 50):
                ui.desenhar_texto(tela, sub, (LARGURA // 2, y), 10, BRANCO, "midtop")
                y += 16
            y += 3
        v = self.vitorias()
        y_rec = self.menu_inicio.botoes[0].rect.y - 30
        ui.desenhar_texto(tela, f"VITÓRIAS  J1 {v[0]} × {v[1]} J2", (LARGURA // 2, y_rec),
                          12, AMARELO, "midtop")
        self.menu_inicio.desenhar(tela)
