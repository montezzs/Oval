from core.idioma import t
import math
import random

import pygame

from settings import *
from core import ui
from jogos.base_hibrido import MiniJogoHibrido
from jogos.base_multi import TECLAS_MOVER, TECLAS_ACAO, CORES_JOGADOR
from jogos.boliche import desenhar_inicio_hibrido, ajustar_botoes_hibrido

# ============================================================
# REI DO QUINTAL (VS BOT OU 2 JOGADORES)
# ============================================================
# Quintal visto de cima com uma ZONA-COROA. Ficar SOZINHO nela
# soma pontos. A zona muda de lugar a cada 20 s. INVESTIDA (ação)
# empurra e atordoa o outro. Itens: CASCA DE BANANA (quem pisa
# escorrega rodando) e MOLA (quem pisa é arremessado). Primeiro a
# 30 pontos, ou quem tiver mais em 90 s.

ARENA = pygame.Rect(40, 96, 944, 606)
R_OVO = 26
ALT_OVO = 56
ACEL = 2300
VMAX = 280
ATRITO = 7.0
DASH_VEL = 780
DASH_T = 0.22
DASH_RECARGA = 1.3
EMPURRAO = 640
ATORDOA = 0.75

ZONA_R = 84
ZONA_TROCA = 20.0
ZONA_AVISO = 3.0
META = 30
DURACAO = 90.0
PONTOS_SEG = 1.0

OBSTACULOS = [(170, 610, 34, "toco"), (860, 196, 34, "balde"), (860, 612, 30, "moita"),
              (170, 196, 30, "moita")]
LUGARES_ZONA = [(512, 398), (330, 300), (694, 300), (330, 500), (694, 500), (512, 240), (512, 566)]

ITEM_R = 16
ITEM_INTERVALO = (4.5, 7.5)
ARMADILHA_VIDA = 18.0
SUB = 1 / 240

# Bot por dificuldade: fácil, médio, difícil
BOT_VEL = [0.74, 0.9, 1.0]
BOT_REACAO = [0.5, 0.24, 0.08]
BOT_ERRO = [30, 12, 3]               # graus de erro na investida
BOT_ALCANCE = [110, 160, 200]
BOT_EVITA = [False, True, True]
BOT_ITEM = [90, 180, 280]            # distância em que vai buscar item

_cache = {}


def _sup_zona():
    sup = _cache.get("zona")
    if sup is None:
        sup = pygame.Surface((ZONA_R * 2, ZONA_R * 2), pygame.SRCALPHA)
        pygame.draw.circle(sup, (255, 214, 64, 70), (ZONA_R, ZONA_R), ZONA_R)
        pygame.draw.circle(sup, (255, 240, 150, 60), (ZONA_R, ZONA_R), ZONA_R - 18)
        _cache["zona"] = sup
    return sup


def _coroa(tam):
    chave = ("coroa", tam)
    sup = _cache.get(chave)
    if sup is None:
        w, h = tam, int(tam * 0.7)
        sup = pygame.Surface((w + 4, h + 4), pygame.SRCALPHA)
        pts = [(2, h), (2, h * 0.3), (w * 0.27, h * 0.6), (w * 0.5 + 2, 2), (w * 0.73 + 4, h * 0.6),
               (w + 2, h * 0.3), (w + 2, h)]
        pygame.draw.polygon(sup, (255, 214, 64), pts)
        pygame.draw.polygon(sup, (150, 100, 20), pts, 2)
        for fx in (0.27, 0.5, 0.73):
            pygame.draw.circle(sup, (230, 60, 80), (int(w * fx) + 2, int(h * 0.78)), max(2, tam // 12))
        _cache[chave] = sup
    return sup


def _sombra(w, h):
    chave = ("sombra", w, h)
    sup = _cache.get(chave)
    if sup is None:
        sup = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.ellipse(sup, (0, 0, 0, 80), sup.get_rect())
        _cache[chave] = sup
    return sup


def _item_sup(tipo, chao=False):
    chave = ("item", tipo, chao)
    sup = _cache.get(chave)
    if sup is None:
        sup = pygame.Surface((40, 40), pygame.SRCALPHA)
        if not chao:
            pygame.draw.circle(sup, (255, 255, 255, 60), (20, 20), 19)
        if tipo == "banana":
            pygame.draw.arc(sup, (250, 220, 60), (6, 4, 30, 30), math.radians(200), math.radians(340), 8)
            pygame.draw.arc(sup, (140, 110, 30), (6, 4, 30, 30), math.radians(200), math.radians(340), 2)
            pygame.draw.circle(sup, (90, 70, 20), (8, 20), 3)
            if chao:
                pygame.draw.polygon(sup, (250, 220, 60), [(20, 30), (10, 38), (16, 30)])
                pygame.draw.polygon(sup, (250, 220, 60), [(22, 30), (32, 38), (26, 30)])
        else:
            for k in range(4):
                pygame.draw.ellipse(sup, (170, 180, 200), (8, 24 - k * 6, 24, 10), 3)
            pygame.draw.rect(sup, (230, 70, 70), (6, 4, 28, 7), border_radius=3)
            pygame.draw.rect(sup, (90, 90, 110), (6, 30, 28, 6), border_radius=3)
        _cache[chave] = sup
    return sup


class Ovo:
    def __init__(self, i):
        self.i = i
        self.x, self.y = (ARENA.left + 130, ARENA.centery) if i == 0 else (ARENA.right - 130, ARENA.centery)
        self.vx = self.vy = 0.0
        self.fx, self.fy = (1.0, 0.0) if i == 0 else (-1.0, 0.0)
        self.dash = 0.0
        self.recarga = 0.0
        self.atordoado = 0.0
        self.escorrega = 0.0
        self.voo = 0.0
        self.giro = 0.0
        self.item = None
        self.pontos = 0.0
        self.empurroes = 0
        self.ix = self.iy = 0.0        # entrada de movimento (-1..1)

    @property
    def livre(self):
        return self.atordoado <= 0 and self.escorrega <= 0 and self.voo <= 0


class ReiQuintal(MiniJogoHibrido):

    ID = "rei_quintal"
    TITULO = "REI DO QUINTAL"
    TITULO_CURTO = "REI QUINTAL"
    DESCRICAO = "Fique sozinho na zona da coroa para somar pontos! Empurre, escorregue e arremesse o rival."
    COR = (230, 170, 40)
    INSTRUCOES = [
        "Fique SOZINHO na zona da COROA para somar pontos. Ela muda a cada 20 s!",
        "INVESTIDA empurra e atordoa. Pegue itens: BANANA (escorrega) e MOLA (arremessa).",
        "J1: WASD, ESPAÇO investida, F item • J2: SETAS, ENTER investida, SHIFT DIR. item",
        "Primeiro a 30 pontos ou mais pontos em 90 s.",
    ]
    CONTROLES_J1 = "WASD + ESPAÇO/F"
    CONTROLES_J2 = "SETAS + ENTER/SHIFT"
    TEMPO_MINIMO = 25.0

    # --------------------------------------------------------
    # CENÁRIO
    # --------------------------------------------------------

    @classmethod
    def criar_fundo(cls, jogador):
        sup = pygame.Surface((LARGURA, ALTURA))
        sup.fill((70, 120, 50))
        rnd = random.Random(7)
        # Grama com faixas de cortador
        for k in range(0, ARENA.w, 60):
            cor = (112, 186, 82) if (k // 60) % 2 == 0 else (100, 172, 72)
            pygame.draw.rect(sup, cor, (ARENA.x + k, ARENA.y, min(60, ARENA.w - k), ARENA.h))
        for _ in range(260):
            x = rnd.randint(ARENA.left + 4, ARENA.right - 4)
            y = rnd.randint(ARENA.top + 4, ARENA.bottom - 4)
            pygame.draw.line(sup, (80, 150, 60), (x, y), (x + rnd.randint(-2, 2), y - 5), 2)
        for _ in range(26):
            x = rnd.randint(ARENA.left + 10, ARENA.right - 10)
            y = rnd.randint(ARENA.top + 10, ARENA.bottom - 10)
            cor = rnd.choice([(255, 255, 255), (255, 220, 80), (255, 130, 170), (180, 160, 255)])
            for a in range(5):
                ang = a * math.tau / 5
                pygame.draw.circle(sup, cor, (int(x + math.cos(ang) * 4), int(y + math.sin(ang) * 4)), 3)
            pygame.draw.circle(sup, (255, 200, 40), (x, y), 2)
        # Obstáculos
        for x, y, r, tipo in OBSTACULOS:
            pygame.draw.ellipse(sup, (50, 90, 40), (x - r, y - r * 0.4 + 10, r * 2, r * 1.1))
            if tipo == "toco":
                pygame.draw.circle(sup, (110, 70, 40), (x, y), r)
                for rr in (r - 8, r - 16, r - 24):
                    if rr > 2:
                        pygame.draw.circle(sup, (170, 120, 70), (x, y), rr, 2)
            elif tipo == "balde":
                pygame.draw.circle(sup, (150, 160, 175), (x, y), r)
                pygame.draw.circle(sup, (80, 150, 230), (x, y), r - 6)
                pygame.draw.circle(sup, (170, 210, 255), (x - 6, y - 6), 6)
                pygame.draw.circle(sup, (90, 95, 110), (x, y), r, 3)
            else:
                for dx, dy in ((-10, 6), (10, 6), (0, -8), (0, 4)):
                    pygame.draw.circle(sup, (40, 120, 50), (x + dx, y + dy), r - 10)
                for dx, dy in ((-8, -4), (8, -6)):
                    pygame.draw.circle(sup, (60, 150, 60), (x + dx, y + dy), r - 18)
        # Cerca
        pygame.draw.rect(sup, (150, 100, 55), ARENA.inflate(18, 18), 9, border_radius=8)
        pygame.draw.rect(sup, (110, 70, 35), ARENA.inflate(18, 18), 2, border_radius=8)
        for x in range(ARENA.left - 9, ARENA.right + 10, 48):
            for y in (ARENA.top - 9, ARENA.bottom + 9):
                pygame.draw.rect(sup, (190, 140, 80), (x - 5, y - 7, 10, 14), border_radius=2)
        for y in range(ARENA.top - 9, ARENA.bottom + 10, 48):
            for x in (ARENA.left - 9, ARENA.right + 9):
                pygame.draw.rect(sup, (190, 140, 80), (x - 7, y - 5, 14, 10), border_radius=2)
        return sup

    @classmethod
    def desenhar_icone(cls, sup, jogador):
        w, h = sup.get_size()
        pygame.draw.circle(sup, (255, 214, 64), (w // 2, int(h * 0.62)), int(h * 0.3), 4)
        jogador.desenhar(sup, (w * 0.5, h * 0.58), h * 0.42)
        c = _coroa(max(12, int(h * 0.28)))
        sup.blit(c, c.get_rect(midbottom=(w // 2, int(h * 0.32))))

    # --------------------------------------------------------
    # PARTIDA
    # --------------------------------------------------------

    def __init__(self, app, menu):
        self.seguradas = set()
        self._avatares = {}
        super().__init__(app, menu)

    def _montar_menu_inicio(self):
        super()._montar_menu_inicio()
        ajustar_botoes_hibrido(self)

    def _desenhar_inicio(self, tela):
        desenhar_inicio_hibrido(self, tela)

    def reiniciar(self):
        self.ovos = [Ovo(0), Ovo(1)]
        self.zona = LUGARES_ZONA[0]
        self.prox_zona = None
        self.t_zona = 0.0
        self.relogio = DURACAO
        self.itens = []               # [x, y, tipo, t]
        self.armadilhas = []          # [x, y, tipo, dono, graca, vida]
        self.t_item = random.uniform(*ITEM_INTERVALO)
        self.banner = None
        self.dono_zona = None
        self.disputa = False
        self._pontos_int = [0, 0]
        self.bot_t = 0.0
        self.bot_alvo = None
        self._avatares = {}
        for i in (0, 1):
            base = self.jogador.avatar(ALT_OVO, self.aparencia(i)).copy()
            self._avatares[(i, False)] = base
            self._avatares[(i, True)] = pygame.transform.flip(base, True, False)

    def _eh_bot(self, i):
        return self.solo and i == 1

    def _girado(self, i, ang):
        ab = int(round(ang / 30.0)) % 12
        chave = (i, "g", ab)
        sup = self._avatares.get(chave)
        if sup is None:
            sup = pygame.transform.rotate(self._avatares[(i, False)], ab * 30)
            self._avatares[chave] = sup
        return sup

    # --------------------------------------------------------
    # CONTROLES
    # --------------------------------------------------------

    def evento(self, e):
        if e.type == pygame.KEYDOWN:
            self.seguradas.add(e.key)
        elif e.type == pygame.KEYUP:
            self.seguradas.discard(e.key)
        elif e.type == pygame.WINDOWFOCUSLOST:
            self.seguradas.clear()
        super().evento(e)

    def _donos_tecla(self, tecla):
        """Jogadores humanos que usam esta tecla (no solo o J1 usa as duas)."""
        donos = []
        for i in (0, 1):
            if tecla in TECLAS_ACAO[i]:
                donos.append(i)
        if self.solo:
            return [0] if donos else []
        return donos

    def evento_jogo(self, e):
        if e.type != pygame.KEYDOWN:
            return
        for i in self._donos_tecla(e.key):
            o = self.ovos[i]
            conjunto = TECLAS_ACAO[i] if not self.solo else (TECLAS_ACAO[0] + TECLAS_ACAO[1])
            principal = e.key in (TECLAS_ACAO[0][0], TECLAS_ACAO[1][0], TECLAS_ACAO[1][1])
            if e.key in conjunto:
                if principal:
                    self._investida(o)
                else:
                    self._usar_item(o)

    def _investida(self, o, dx=None, dy=None):
        if not o.livre or o.recarga > 0:
            return
        if dx is not None:
            d = math.hypot(dx, dy) or 1
            o.fx, o.fy = dx / d, dy / d
        o.vx, o.vy = o.fx * DASH_VEL, o.fy * DASH_VEL
        o.dash = DASH_T
        o.recarga = DASH_RECARGA
        self.som("pulo", 0.6)

    def _usar_item(self, o):
        if o.item is None or not o.livre:
            return
        x = o.x - o.fx * (R_OVO + 20)
        y = o.y - o.fy * (R_OVO + 20)
        x = max(ARENA.left + 14, min(ARENA.right - 14, x))
        y = max(ARENA.top + 14, min(ARENA.bottom - 14, y))
        self.armadilhas.append([x, y, o.item, o.i, 0.8, ARMADILHA_VIDA])
        if len(self.armadilhas) > 5:
            self.armadilhas.pop(0)
        o.item = None
        self.som("clique")

    def _entrada_humana(self, i):
        k = self.seguradas
        conjuntos = (0, 1) if self.solo else (i,)
        ix = iy = 0
        for c in conjuntos:
            t = TECLAS_MOVER[c]
            ix += (t["dir"] in k) - (t["esq"] in k)
            iy += (t["baixo"] in k) - (t["cima"] in k)
        return max(-1, min(1, ix)), max(-1, min(1, iy))

    # --------------------------------------------------------
    # BOT
    # --------------------------------------------------------

    def _bot(self, dt):
        o, r = self.ovos[1], self.ovos[0]
        d = self.dificuldade
        self.bot_t -= dt
        if self.bot_t > 0:
            return
        self.bot_t = BOT_REACAO[d] * random.uniform(0.7, 1.3)

        zx, zy = self.zona
        if self.prox_zona and d >= 1 and self.t_zona > ZONA_TROCA - (1.2 if d == 1 else 2.5):
            zx, zy = self.prox_zona
        dist_r = math.hypot(r.x - o.x, r.y - o.y)
        r_na_zona = math.hypot(r.x - self.zona[0], r.y - self.zona[1]) < ZONA_R
        eu_na_zona = math.hypot(o.x - self.zona[0], o.y - self.zona[1]) < ZONA_R

        # Alvo: item perto (se não disputa agora) ou a zona
        alvo = (zx + math.sin(self.tempo * 0.7) * 20, zy + math.cos(self.tempo * 0.9) * 20)
        if o.item is None and self.itens and not (r_na_zona and eu_na_zona):
            it = min(self.itens, key=lambda t: math.hypot(t[0] - o.x, t[1] - o.y))
            if math.hypot(it[0] - o.x, it[1] - o.y) < BOT_ITEM[d] and not (r_na_zona and not eu_na_zona and d == 2):
                alvo = (it[0], it[1])
        if r_na_zona and dist_r < 260 and r.livre:
            alvo = (r.x, r.y)
        self.bot_alvo = alvo

        # Investida no rival
        if o.recarga <= 0 and o.livre and r.voo <= 0 and dist_r < BOT_ALCANCE[d] and \
                (r_na_zona or eu_na_zona) and r.atordoado <= 0:
            px, py = r.x + r.vx * 0.12, r.y + r.vy * 0.12
            ang = math.atan2(py - o.y, px - o.x) + math.radians(random.gauss(0, BOT_ERRO[d]))
            if d > 0 or random.random() < 0.6:
                self._investida(o, math.cos(ang), math.sin(ang))

        # Itens: deixa a armadilha na zona ou quando o rival vem atrás
        if o.item is not None:
            atras = (r.x - o.x) * o.fx + (r.y - o.y) * o.fy < 0 and dist_r < 220
            if (d == 0 and random.random() < 0.15) or (d > 0 and (atras or (eu_na_zona and not r_na_zona and random.random() < 0.3))):
                self._usar_item(o)

    def _entrada_bot(self):
        o = self.ovos[1]
        if self.bot_alvo is None:
            return 0.0, 0.0
        dx, dy = self.bot_alvo[0] - o.x, self.bot_alvo[1] - o.y
        dist = math.hypot(dx, dy)
        if dist < 14:
            return 0.0, 0.0
        ix, iy = dx / dist, dy / dist
        if BOT_EVITA[self.dificuldade]:
            for a in self.armadilhas:
                if a[3] == 1 and a[4] > 0:
                    continue
                ax, ay = o.x - a[0], o.y - a[1]
                da = math.hypot(ax, ay)
                if 0 < da < 80:
                    ix += ax / da * (80 - da) / 40
                    iy += ay / da * (80 - da) / 40
            n = math.hypot(ix, iy) or 1
            ix, iy = ix / n, iy / n
        f = BOT_VEL[self.dificuldade] * min(1.0, dist / 60)
        return ix * f, iy * f

    # --------------------------------------------------------
    # LOOP
    # --------------------------------------------------------

    def atualizar_jogo(self, dt):
        if self.banner:
            self.banner[2] -= dt
            if self.banner[2] <= 0:
                self.banner = None

        self.relogio -= dt
        # Zona
        self.t_zona += dt
        if self.prox_zona is None and self.t_zona > ZONA_TROCA - ZONA_AVISO:
            self.prox_zona = random.choice([p for p in LUGARES_ZONA if p != self.zona])
            self.som("tic", 0.6)
        if self.t_zona >= ZONA_TROCA:
            self.zona = self.prox_zona
            self.prox_zona = None
            self.t_zona = 0.0
            self.banner = ["A COROA MUDOU!", AMARELO, 1.2]
            self.som("revelar", 0.7)

        # Itens aparecendo
        self.t_item -= dt
        if self.t_item <= 0:
            self.t_item = random.uniform(*ITEM_INTERVALO)
            if len(self.itens) < 2:
                self._gerar_item()

        # Entradas
        for o in self.ovos:
            if self._eh_bot(o.i):
                o.ix, o.iy = self._entrada_bot()
            else:
                o.ix, o.iy = self._entrada_humana(o.i)
                if o.ix or o.iy:
                    self._mexeu[o.i if not self.solo else 0] = True
        if self.solo:
            self._bot(dt)

        for o in self.ovos:
            for nome in ("dash", "recarga", "atordoado"):
                setattr(o, nome, max(0.0, getattr(o, nome) - dt))
            if o.escorrega > 0:
                o.escorrega = max(0.0, o.escorrega - dt)
                o.giro += 900 * dt
            if o.voo > 0:
                o.voo = max(0.0, o.voo - dt)
                if o.voo == 0:
                    o.atordoado = 0.3
                    self.som("bater", 0.6)
                    self.particulas.explodir((o.x, o.y + 16), [(160, 120, 70), (120, 180, 80)], 10, 160, 0.5)
            if o.livre and (o.ix or o.iy):
                n = math.hypot(o.ix, o.iy)
                o.fx, o.fy = o.ix / max(1.0, n) if n else o.fx, o.iy / max(1.0, n) if n else o.fy
                nf = math.hypot(o.fx, o.fy) or 1
                o.fx, o.fy = o.fx / nf, o.fy / nf

        passos = max(1, int(round(dt / SUB)))
        h = dt / passos
        for _ in range(passos):
            self._fisica(h)

        for a in self.armadilhas:
            a[4] -= dt
            a[5] -= dt
        self.armadilhas = [a for a in self.armadilhas if a[5] > 0]
        self._pegar_e_pisar()

        # Pontos na zona
        dentro = [o for o in self.ovos
                  if o.voo <= 0 and math.hypot(o.x - self.zona[0], o.y - self.zona[1]) < ZONA_R]
        self.dono_zona = dentro[0].i if len(dentro) == 1 else None
        self.disputa = len(dentro) == 2
        if self.dono_zona is not None:
            o = self.ovos[self.dono_zona]
            o.pontos += PONTOS_SEG * dt
            if int(o.pontos) > self._pontos_int[o.i]:
                self._pontos_int[o.i] = int(o.pontos)
                self.textos.adicionar("+1", (o.x, o.y - 50), CORES_JOGADOR[o.i], 12)
                self.som("tic", 0.35)
        self.pontos = int(self.ovos[0].pontos)

        # Fim
        p = [o.pontos for o in self.ovos]
        if max(p) >= META:
            self._fim(0 if p[0] >= META else 1)
        elif self.relogio <= 0:
            a, b = int(p[0]), int(p[1])
            self._fim(None if a == b else (0 if a > b else 1))

    def _gerar_item(self):
        for _ in range(20):
            x = random.randint(ARENA.left + 40, ARENA.right - 40)
            y = random.randint(ARENA.top + 40, ARENA.bottom - 40)
            if all(math.hypot(x - ox, y - oy) > r + 40 for ox, oy, r, _ in OBSTACULOS) and \
                    all(math.hypot(x - o.x, y - o.y) > 90 for o in self.ovos):
                self.itens.append([x, y, random.choice(("banana", "mola")), 0.0])
                self.som("revelar", 0.4)
                return

    def _fisica(self, h):
        for o in self.ovos:
            if o.voo > 0:
                pass
            elif o.livre and o.dash <= 0:
                o.vx += o.ix * ACEL * h
                o.vy += o.iy * ACEL * h
                atr = ATRITO if not (o.ix or o.iy) else ATRITO * 0.5
                o.vx -= o.vx * atr * h
                o.vy -= o.vy * atr * h
                v = math.hypot(o.vx, o.vy)
                if v > VMAX:
                    o.vx, o.vy = o.vx / v * VMAX, o.vy / v * VMAX
            elif o.escorrega > 0:
                o.vx -= o.vx * 0.6 * h
                o.vy -= o.vy * 0.6 * h
            else:
                atr = 1.5 if o.dash > 0 else 4.0
                o.vx -= o.vx * atr * h
                o.vy -= o.vy * atr * h
            o.x += o.vx * h
            o.y += o.vy * h
            # Cerca
            if o.x < ARENA.left + R_OVO:
                o.x = ARENA.left + R_OVO
                o.vx = abs(o.vx) * 0.5
            elif o.x > ARENA.right - R_OVO:
                o.x = ARENA.right - R_OVO
                o.vx = -abs(o.vx) * 0.5
            if o.y < ARENA.top + R_OVO:
                o.y = ARENA.top + R_OVO
                o.vy = abs(o.vy) * 0.5
            elif o.y > ARENA.bottom - R_OVO:
                o.y = ARENA.bottom - R_OVO
                o.vy = -abs(o.vy) * 0.5
            # Obstáculos (quem está voando passa por cima)
            if o.voo <= 0:
                for ox, oy, r, _ in OBSTACULOS:
                    dx, dy = o.x - ox, o.y - oy
                    d = math.hypot(dx, dy)
                    if 0 < d < r + R_OVO:
                        nx, ny = dx / d, dy / d
                        o.x, o.y = ox + nx * (r + R_OVO), oy + ny * (r + R_OVO)
                        vn = o.vx * nx + o.vy * ny
                        if vn < 0:
                            o.vx -= 1.5 * vn * nx
                            o.vy -= 1.5 * vn * ny

        a, b = self.ovos
        if a.voo > 0 or b.voo > 0:
            return
        dx, dy = b.x - a.x, b.y - a.y
        d = math.hypot(dx, dy)
        if d == 0 or d >= 2 * R_OVO:
            return
        nx, ny = dx / d, dy / d
        sep = (2 * R_OVO - d) / 2
        a.x -= nx * sep
        a.y -= ny * sep
        b.x += nx * sep
        b.y += ny * sep
        vrel = (a.vx - b.vx) * nx + (a.vy - b.vy) * ny
        if vrel <= 0:
            return
        if a.dash > 0 and b.dash > 0:
            for o, s in ((a, -1), (b, 1)):
                o.vx, o.vy = nx * s * 420, ny * s * 420
                o.dash = 0.0
                o.atordoado = 0.4
            self._pancada((a.x + b.x) / 2, (a.y + b.y) / 2, 0.25)
        elif a.dash > 0 or b.dash > 0:
            atac, alvo, s = (a, b, 1) if a.dash > 0 else (b, a, -1)
            alvo.vx, alvo.vy = nx * s * EMPURRAO, ny * s * EMPURRAO
            alvo.atordoado = ATORDOA
            alvo.escorrega = 0.0
            atac.vx *= 0.25
            atac.vy *= 0.25
            atac.dash = 0.0
            atac.empurroes += 1
            self._pancada(alvo.x, alvo.y, 0.3)
            self.textos.adicionar(t("POW!"), (alvo.x, alvo.y - 60), AMARELO, 16)
        else:
            j = vrel * 0.9 + 60
            a.vx -= j * nx
            a.vy -= j * ny
            b.vx += j * nx
            b.vy += j * ny

    def _pancada(self, x, y, forca):
        self.som("bater")
        self.tremer(forca)
        self.particulas.explodir((x, y), [BRANCO, AMARELO, (255, 180, 120)], 16, 260, 0.5)

    def _pegar_e_pisar(self):
        for o in self.ovos:
            if o.voo > 0:
                continue
            if o.item is None:
                for it in self.itens:
                    if math.hypot(it[0] - o.x, it[1] - o.y) < R_OVO + ITEM_R:
                        o.item = it[2]
                        self.itens.remove(it)
                        self.som("moeda", 0.6)
                        self.textos.adicionar("BANANA!" if o.item == "banana" else "MOLA!",
                                              (o.x, o.y - 50), BRANCO, 12)
                        break
            for a in list(self.armadilhas):
                if a[3] == o.i and a[4] > 0:
                    continue
                if math.hypot(a[0] - o.x, a[1] - o.y) < R_OVO * 0.8 + 10:
                    self.armadilhas.remove(a)
                    v = math.hypot(o.vx, o.vy)
                    if v < 1:
                        o.vx, o.vy, v = o.fx, o.fy, 1.0
                    if a[2] == "banana":
                        o.escorrega = 1.1
                        o.dash = 0.0
                        o.vx, o.vy = o.vx / v * max(v, 320), o.vy / v * max(v, 320)
                        self.som("erro", 0.7)
                        self.textos.adicionar(t("ESCORREGOU!"), (o.x, o.y - 60), (255, 230, 100), 12)
                    else:
                        o.voo = 0.8
                        o.dash = 0.0
                        o.escorrega = 0.0
                        ang = math.atan2(o.vy, o.vx) + random.uniform(-0.6, 0.6)
                        o.vx, o.vy = math.cos(ang) * 520, math.sin(ang) * 520
                        self.som("mola")
                        self.textos.adicionar(t("BOING!"), (o.x, o.y - 60), (180, 220, 255), 14)

    def _fim(self, vencedor):
        p = [int(o.pontos) for o in self.ovos]
        linhas = [t("PONTOS  {a} × {b}", a=p[0], b=p[1]),
                  t("EMPURRÕES  {a} × {b}", a=self.ovos[0].empurroes, b=self.ovos[1].empurroes)]
        if max(p) >= META:
            linhas.insert(0, t("COROA COM {n} PONTOS!", n=META))
        self.terminar_multi(vencedor, linhas)

    # --------------------------------------------------------
    # DESENHO
    # --------------------------------------------------------

    def desenhar_jogo(self, tela):
        tela.blit(self.fundo(self.jogador), (0, 0))
        zx, zy = self.zona
        tela.blit(_sup_zona(), (zx - ZONA_R, zy - ZONA_R))
        cor_anel = AMARELO if self.dono_zona is None and not getattr(self, "disputa", False) else \
            ((255, 120, 100) if getattr(self, "disputa", False) else CORES_JOGADOR[self.dono_zona])
        pul = int(3 * math.sin(self.tempo * 6))
        pygame.draw.circle(tela, cor_anel, (zx, zy), ZONA_R + pul, 4)
        if self.prox_zona and int(self.tempo * 5) % 2 == 0:
            px, py = self.prox_zona
            for k in range(12):
                a = k * math.tau / 12 + self.tempo
                pygame.draw.arc(tela, BRANCO, (px - ZONA_R, py - ZONA_R, ZONA_R * 2, ZONA_R * 2), a, a + 0.25, 3)
        if self.dono_zona is None:
            c = _coroa(40)
            tela.blit(c, c.get_rect(center=(zx, zy - 6 + math.sin(self.tempo * 3) * 5)))

        for x, y, tipo, dono, graca, vida in self.armadilhas:
            if vida > 3 or int(self.tempo * 6) % 2 == 0:
                s = _item_sup(tipo, True)
                tela.blit(s, s.get_rect(center=(x, y)))
        for x, y, tipo, _ in self.itens:
            s = _item_sup(tipo)
            tela.blit(s, s.get_rect(center=(x, y + math.sin(self.tempo * 4 + x) * 4)))

        for o in sorted(self.ovos, key=lambda o: o.y):
            alt = math.sin((1 - o.voo / 0.8) * math.pi) * 70 if o.voo > 0 else 0
            sw = int(R_OVO * 2 * (1 - alt / 160))
            sh = _sombra(sw, max(6, sw // 3))
            tela.blit(sh, sh.get_rect(center=(o.x, o.y + R_OVO * 0.7)))
            if o.escorrega > 0:
                spr = self._girado(o.i, o.giro)
            else:
                spr = self._avatares[(o.i, o.fx < -0.1)]
            y = o.y - 6 - alt
            if o.livre and (abs(o.vx) + abs(o.vy)) > 40:
                y -= abs(math.sin(self.tempo * 14 + o.i)) * 4
            tela.blit(spr, spr.get_rect(center=(o.x, y)))
            if o.dash > 0:
                pygame.draw.circle(tela, BRANCO, (int(o.x - o.fx * 30), int(o.y - o.fy * 30)), 8, 2)
            if o.atordoado > 0 and o.voo <= 0:
                for k in range(3):
                    a = self.tempo * 6 + k * math.tau / 3
                    ui.estrela(tela, (o.x + math.cos(a) * 22, y - 38 + math.sin(a) * 6), 6, AMARELO)
            if self.dono_zona == o.i:
                c = _coroa(28)
                tela.blit(c, c.get_rect(midbottom=(o.x, y - 30)))
            if o.item:
                s = _item_sup(o.item)
                tela.blit(s, s.get_rect(center=(o.x + 30, y - 30)))

        self.particulas.desenhar(tela)
        self.textos.desenhar(tela)
        if self.banner:
            ui.desenhar_texto(tela, t(self.banner[0]), (LARGURA // 2, ALTURA // 2 - 120), 28, self.banner[1],
                              "center")
        elif getattr(self, "disputa", False):
            ui.desenhar_texto(tela, t("DISPUTA!"), (zx, zy - ZONA_R - 16), 12, (255, 140, 120), "center")

    def desenhar_hud(self, tela):
        caixa = pygame.Rect(12, 8, LARGURA - 96, 74)
        ui.painel(tela, caixa, (20, 24, 40), BRANCO, 12, 3, sombra=False)
        seg = max(0, int(math.ceil(self.relogio)))
        cor_t = (255, 120, 100) if seg <= 10 else BRANCO
        ui.desenhar_texto(tela, f"{seg // 60}:{seg % 60:02d}", (caixa.centerx, caixa.y + 14), 20, cor_t, "midtop")
        ui.desenhar_texto(tela, t("META {n}", n=META), (caixa.centerx, caixa.y + 46), 8, (180, 200, 255), "midtop")
        for i in (0, 1):
            o = self.ovos[i]
            w = 300
            x = caixa.x + 20 if i == 0 else caixa.right - 20 - w
            ui.desenhar_texto(tela, self.nome(i)[:12], (x if i == 0 else x + w, caixa.y + 12), 12,
                              CORES_JOGADOR[i], "topleft" if i == 0 else "topright")
            ui.desenhar_texto(tela, str(int(o.pontos)), (x + w if i == 0 else x, caixa.y + 10), 16, AMARELO,
                              "topright" if i == 0 else "topleft")
            barra = pygame.Rect(x, caixa.y + 38, w, 18)
            pygame.draw.rect(tela, (50, 50, 70), barra, border_radius=6)
            f = min(1.0, o.pontos / META)
            cheio = pygame.Rect(0, barra.y, int(w * f), barra.h)
            if i == 0:
                cheio.x = barra.x
            else:
                cheio.right = barra.right
            if cheio.w > 0:
                pygame.draw.rect(tela, CORES_JOGADOR[i], cheio, border_radius=6)
            pygame.draw.rect(tela, BRANCO, barra, 2, border_radius=6)
            # Recarga da investida
            rx = barra.x if i == 0 else barra.right - 60
            pronta = o.recarga <= 0
            pygame.draw.rect(tela, (90, 200, 90) if pronta else (80, 80, 100),
                             (rx, barra.bottom + 4, int(60 * (1 - o.recarga / DASH_RECARGA)), 5))
