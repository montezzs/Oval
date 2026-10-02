from core.idioma import t
import math
import random

import pygame

from settings import *
from core import assets, ui
from core.jogador import Jogador, BOCA_TRISTE, OLHO_FECHADO
from jogos.base_hibrido import MiniJogoHibrido
from jogos.base_multi import TECLAS_MOVER, CORES_JOGADOR

# ============================================================
# OVO KOMBAT (VS BOT OU 2 JOGADORES)
# ============================================================
# Luta 2D estilo fliperama. Os LUTADORES são os ovos da rua do
# jogador (só leitura: nada é gravado nos saves deles); se houver
# menos de 5, o elenco é completado com ovos sorteados.
#
#   ANDAR / PULAR (CIMA) / AGACHAR (BAIXO)
#   SOCO, CHUTE, BLOQUEAR (segurar)
#   ESPECIAL: BAIXO, FRENTE + SOCO
#   FATALOVO (no FINALIZE-O!): FRENTE, FRENTE, BAIXO + CHUTE
#
# Melhor de 3 rounds, 60 segundos cada.

CHAO = 620
GRAVIDADE = 2400
VEL_ANDAR = 250
VEL_PULO = 860
X_MIN, X_MAX = 50, LARGURA - 50
DIST_MIN = 58
TEMPO_ROUND = 60
ALT_OVO = 96
L_MEMBRO = 38                 # cada segmento de braço/perna

TECLAS_SOCO = [(pygame.K_SPACE, pygame.K_q), (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_KP0)]
TECLAS_CHUTE = [(pygame.K_f, pygame.K_e), (pygame.K_RSHIFT, pygame.K_SLASH)]
TECLAS_BLOQ = [(pygame.K_g,), (pygame.K_RCTRL, pygame.K_PERIOD)]

ESTILOS = [
    dict(nome="LIMÃO DE FOGO", esp="fogo", vel=1.0, forca=1.0, pulo=1.0, cor=(255, 160, 40)),
    dict(nome="INVESTIDA CASCUDA", esp="investida", vel=0.93, forca=1.12, pulo=0.92,
         cor=(230, 70, 60)),
    dict(nome="GANCHO DE GEMA", esp="gancho", vel=1.0, forca=1.08, pulo=1.05, cor=(250, 215, 60)),
    dict(nome="TELEPORTE DE CLARA", esp="teleporte", vel=1.08, forca=0.93, pulo=1.08,
         cor=(160, 110, 255)),
    dict(nome="RASTEIRA ESCORREGADIA", esp="deslize", vel=1.15, forca=0.95, pulo=1.0,
         cor=(70, 200, 255)),
]

NOMES_EXTRAS = ["SUB-OVO", "SCORPOVO", "RAIDOVO", "OVO KANG", "SONYA GEMA", "KUNG LAOVO",
                "JAX CASCA", "KITANOVO", "BARAKOVO", "JOHNNY GEMA"]

# alc = alcance à frente (min, max); alt = faixa vertical (relativa aos pés)
ATAQUES = {
    "soco": dict(ini=0.06, ativo=0.08, rec=0.14, dano=6, alc=(15, 100), alt=(-140, -95),
                 emp=180, stun=0.28, pose="soco"),
    "chute": dict(ini=0.10, ativo=0.10, rec=0.22, dano=9, alc=(15, 112), alt=(-95, -45),
                  emp=280, stun=0.34, pose="chute"),
    "soco_baixo": dict(ini=0.05, ativo=0.07, rec=0.12, dano=4, alc=(15, 92), alt=(-80, -35),
                       emp=120, stun=0.22, pose="agsoco"),
    "rasteira": dict(ini=0.10, ativo=0.10, rec=0.30, dano=7, alc=(10, 118), alt=(-30, 5),
                     emp=160, stun=0.3, pose="rasteira", derruba=True),
    "voadora": dict(ini=0.04, ativo=0.40, rec=0.0, dano=8, alc=(10, 95), alt=(-90, -10),
                    emp=240, stun=0.32, pose="chute"),
    "investida": dict(ini=0.10, ativo=0.32, rec=0.25, dano=11, alc=(0, 80), alt=(-150, -20),
                      emp=420, stun=0.45, pose="investida", vx=720),
    "gancho": dict(ini=0.07, ativo=0.18, rec=0.30, dano=13, alc=(0, 84), alt=(-200, -60),
                   emp=200, stun=0.5, pose="gancho", vy=-560, vx=120, derruba=True),
    "deslize": dict(ini=0.08, ativo=0.36, rec=0.25, dano=10, alc=(0, 108), alt=(-35, 5),
                    emp=200, stun=0.4, pose="rasteira", vx=560, derruba=True),
    "fogo": dict(ini=0.18, ativo=0.0, rec=0.30, dano=0, alc=(0, 0), alt=(0, 0),
                 emp=0, stun=0, pose="especial"),
    "teleporte": dict(ini=0.30, ativo=0.0, rec=0.0, dano=0, alc=(0, 0), alt=(0, 0),
                      emp=0, stun=0, pose="especial"),
    "chute_tele": dict(ini=0.05, ativo=0.12, rec=0.25, dano=10, alc=(10, 112), alt=(-120, -40),
                       emp=300, stun=0.4, pose="chute"),
}
BAIXOS = ("soco_baixo", "rasteira", "deslize")

# Poses (olhando para a direita, origem nos pés, y para cima negativo)
#   c = centro do ovo, a = inclinação (graus), sy = achatamento,
#   p = pés (trás, frente), m = mãos (trás, frente)
POSES = {
    "idle0": dict(c=(0, -100), a=0, p=((-22, 0), (20, 0)), m=((34, -112), (50, -122))),
    "idle1": dict(c=(0, -97), a=0, p=((-22, 0), (20, 0)), m=((34, -109), (50, -119))),
    "andar0": dict(c=(0, -100), a=-3, p=((-30, 0), (26, -4)), m=((34, -112), (50, -122))),
    "andar1": dict(c=(0, -98), a=-3, p=((-8, -4), (10, 0)), m=((34, -110), (50, -120))),
    "agachar": dict(c=(0, -72), a=0, sy=0.9, p=((-28, 0), (28, 0)), m=((34, -88), (48, -96))),
    "pulo": dict(c=(0, -100), a=8, p=((-14, -24), (20, -28)), m=((-30, -120), (40, -128))),
    "soco": dict(c=(8, -100), a=-8, p=((-30, 0), (26, 0)), m=((30, -106), (104, -114))),
    "chute": dict(c=(-10, -104), a=12, p=((-24, 0), (100, -72)), m=((-38, -96), (24, -124))),
    "agsoco": dict(c=(6, -72), a=-6, sy=0.9, p=((-30, 0), (28, 0)), m=((30, -86), (92, -70))),
    "rasteira": dict(c=(-18, -58), a=20, sy=0.9, p=((-40, 0), (108, -6)),
                     m=((-56, -6), (-20, -20))),
    "bloqueio": dict(c=(-4, -100), a=6, p=((-26, 0), (18, 0)), m=((34, -128), (40, -104))),
    "agbloq": dict(c=(-4, -72), a=6, sy=0.9, p=((-28, 0), (28, 0)), m=((34, -98), (40, -78))),
    "dano": dict(c=(-12, -98), a=16, p=((-26, 0), (16, 0)), m=((-50, -120), (10, -150))),
    "investida": dict(c=(14, -92), a=-22, p=((-50, 0), (20, -10)), m=((-20, -80), (40, -78))),
    "gancho": dict(c=(6, -110), a=-6, p=((-18, -4), (22, -30)), m=((-30, -96), (50, -200))),
    "especial": dict(c=(0, -100), a=-4, p=((-32, 0), (28, 0)), m=((84, -112), (90, -100))),
    "caido": dict(c=(0, -80), a=45, p=((-50, -40), (-30, -60)), m=((-60, -110), (40, -130))),
    "ko": dict(c=(-6, -42), a=88, p=((66, -10), (78, -28)), m=((-40, -8), (-10, -60))),
    "tonto0": dict(c=(0, -98), a=10, p=((-22, 0), (20, 0)), m=((-20, -58), (26, -60))),
    "tonto1": dict(c=(0, -98), a=-10, p=((-22, 0), (20, 0)), m=((-24, -60), (22, -58))),
    "vitoria0": dict(c=(0, -104), a=0, p=((-22, 0), (22, 0)), m=((-40, -190), (40, -194))),
    "vitoria1": dict(c=(0, -112), a=0, p=((-18, -8), (18, -8)), m=((-30, -200), (30, -204))),
}
CANVAS = (300, 300)
ANCORA = (150, 270)

# Bots: reação (s), chances de bloquear/atacar/especial/punir/pular e de fazer o FATALOVO
BOTS = [
    dict(reacao=0.5, bloq=0.12, ataque=0.35, especial=0.05, pune=0.0, pular=0.04, fatal=0.35,
         vel=0.7),
    dict(reacao=0.28, bloq=0.45, ataque=0.55, especial=0.18, pune=0.4, pular=0.08, fatal=0.7,
         vel=0.9),
    dict(reacao=0.12, bloq=0.8, ataque=0.75, especial=0.35, pune=0.85, pular=0.1, fatal=1.0,
         vel=1.0),
]


def _contorno(cor):
    if sum(cor) > 600:
        return (120, 120, 140)
    return ui.escurecer(cor, 80)


def _girar(ox, oy, ang):
    """Gira um deslocamento (tela, y para baixo) no sentido anti-horário visual."""
    r = math.radians(ang)
    c, s = math.cos(r), math.sin(r)
    return ox * c + oy * s, -ox * s + oy * c


def _articulacao(a, b, dobra):
    """Cotovelo/joelho de dois segmentos L_MEMBRO entre a e b."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    d = math.hypot(dx, dy) or 1.0
    if d >= 2 * L_MEMBRO:
        k = 2 * L_MEMBRO / d
        b = (a[0] + dx * k, a[1] + dy * k)
        return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2), b
    h = math.sqrt(L_MEMBRO ** 2 - (d / 2) ** 2)
    px, py = -dy / d * dobra, dx / d * dobra
    return ((a[0] + b[0]) / 2 + px * h, (a[1] + b[1]) / 2 + py * h), b


class Perfil:
    """Um lutador do elenco (visual + estilo) com os sprites em cache."""

    def __init__(self, nome, jogador, estilo):
        self.nome = nome.strip().upper()[:12] or t("OVO")
        self.jog = jogador
        self.apar = jogador.aparencia()
        self.estilo = estilo
        cor = Jogador.cor_do_ovo(self.apar[0])
        self.cor = cor
        self.cor_membro = _contorno(cor)
        self._sprites = {}

    def retrato(self, altura):
        return self.jog.avatar(altura, self.apar)

    def sprite(self, pose, face, branco=False):
        chave = (pose, face, branco)
        s = self._sprites.get(chave)
        if s is None:
            if branco:
                s = self.sprite(pose, face).copy()
                s.fill((110, 110, 110), special_flags=pygame.BLEND_RGB_ADD)
            elif face < 0:
                s = pygame.transform.flip(self.sprite(pose, 1), True, False)
            else:
                s = self._montar(pose)
            self._sprites[chave] = s
        return s

    def _montar(self, nome):
        pose = POSES[nome]
        sup = pygame.Surface(CANVAS, pygame.SRCALPHA)
        ax, ay = ANCORA
        cx, cy = pose["c"]
        ang = pose["a"]
        sy = pose.get("sy", 1.0)

        apar = self.apar
        if nome == "ko":
            apar = (apar[0], apar[1], OLHO_FECHADO, BOCA_TRISTE)
        elif nome in ("dano", "caido", "tonto0", "tonto1"):
            apar = (apar[0], apar[1], apar[2], BOCA_TRISTE)
        corpo = self.jog.avatar(ALT_OVO, apar)
        if sy != 1.0:
            w, h = corpo.get_size()
            corpo = pygame.transform.smoothscale(corpo, (w, max(1, round(h * sy))))
        if ang:
            corpo = pygame.transform.rotate(corpo, ang)

        def ponto(ox, oy):
            rx, ry = _girar(ox, oy * sy, ang)
            return ax + cx + rx, ay + cy + ry

        quadris = (ponto(-13, 36), ponto(13, 36))
        ombros = (ponto(-26, 6), ponto(26, 8))
        pes = [(ax + p[0], ay + p[1]) for p in pose["p"]]
        maos = [(ax + m[0], ay + m[1]) for m in pose["m"]]
        luva = self.estilo["cor"]
        membro = self.cor_membro

        def perna(i):
            joelho, pe = _articulacao(quadris[i], pes[i], -1)
            pygame.draw.line(sup, membro, quadris[i], joelho, 10)
            pygame.draw.line(sup, membro, joelho, pe, 10)
            pygame.draw.circle(sup, membro, joelho, 5)
            r = pygame.Rect(0, 0, 28, 13)
            r.center = (pe[0] + 5, pe[1] - 3)
            pygame.draw.ellipse(sup, (40, 38, 52), r)
            pygame.draw.ellipse(sup, (90, 88, 110), r.inflate(-12, -8).move(4, -2))

        def braco(i):
            cot, mao = _articulacao(ombros[i], maos[i], 1)
            pygame.draw.line(sup, membro, ombros[i], cot, 8)
            pygame.draw.line(sup, membro, cot, mao, 8)
            pygame.draw.circle(sup, membro, cot, 4)
            pygame.draw.circle(sup, ui.escurecer(luva, 70), mao, 13)
            pygame.draw.circle(sup, luva, mao, 11)
            pygame.draw.circle(sup, ui.clarear(luva, 70), (mao[0] - 3, mao[1] - 4), 4)

        perna(0)
        braco(0)
        sup.blit(corpo, corpo.get_rect(center=(ax + cx, ay + cy)))
        perna(1)
        braco(1)
        return sup


class Lutador:

    def __init__(self, i, perfil, x, face):
        self.i = i
        self.p = perfil
        e = perfil.estilo
        self.vel = e["vel"]
        self.forca = e["forca"]
        self.pulo = e["pulo"]
        self.x, self.y = float(x), float(CHAO)
        self.vx = self.vy = 0.0
        self.face = face
        self.vida = 100.0
        self.vida_lenta = 100.0
        self.estado = "normal"
        self.t = 0.0
        self.atk = None
        self.acertou = False
        self.stun = 0.0
        self.no_chao = True
        self.agachado = False
        self.bloqueando = False
        self.andando = 0
        self.invul = 0.0
        self.combo = 0
        self.flash = 0.0
        self._vy_feito = False

    def mudar(self, estado):
        self.estado = estado
        self.t = 0.0

    def hurtbox(self):
        if self.estado in ("caido", "deitado", "ko"):
            topo = -60
        elif self.agachado and self.no_chao and self.estado in ("normal",) or \
                (self.estado == "ataque" and self.atk in BAIXOS):
            topo = -100
        else:
            topo = -150
        return pygame.Rect(int(self.x) - 28, int(self.y) + topo, 56, -topo)

    def hitbox(self):
        d = ATAQUES[self.atk]
        a0, a1 = d["alc"]
        y0, y1 = d["alt"]
        if self.face > 0:
            x0, x1 = self.x + a0, self.x + a1
        else:
            x0, x1 = self.x - a1, self.x - a0
        return pygame.Rect(int(x0), int(self.y + y0), int(x1 - x0), int(y1 - y0))

    def pose(self, tempo):
        e = self.estado
        if e == "ataque":
            if self.atk == "teleporte":
                return None
            return ATAQUES[self.atk]["pose"]
        if e == "dano":
            return "dano"
        if e == "caido":
            return "caido"
        if e in ("deitado", "ko"):
            return "ko"
        if e == "tonto":
            return "tonto0" if int(tempo * 4) % 2 == 0 else "tonto1"
        if e == "vitoria":
            return "vitoria0" if int(tempo * 3) % 2 == 0 else "vitoria1"
        if not self.no_chao:
            return "pulo"
        if self.bloqueando:
            return "agbloq" if self.agachado else "bloqueio"
        if self.agachado:
            return "agachar"
        if self.andando:
            return "andar0" if int(tempo * 7) % 2 == 0 else "andar1"
        return "idle0" if int(tempo * 2.5) % 2 == 0 else "idle1"


class OvoKombat(MiniJogoHibrido):

    ID = "ovo_kombat"
    TITULO = "OVO KOMBAT"
    DESCRICAO = "Luta de fliperama com os ovos da sua rua! Socos, chutes, especiais e um FATALOVO fofo."
    COR = (170, 40, 40)
    INSTRUCOES = [
        "ESCOLHA SEU LUTADOR! MELHOR DE 3 ROUNDS, 60 S CADA.",
        "J1: WASD, ESPAÇO SOCO, F CHUTE, G BLOQUEIA",
        "J2: SETAS, ENTER SOCO, SHIFT DIR. CHUTE, CTRL DIR. BLOQUEIA",
        "ESPECIAL: BAIXO, FRENTE + SOCO",
        "FINALIZE-O: FRENTE, FRENTE, BAIXO + CHUTE = FATALOVO!",
    ]
    CONTROLES_J1 = "WASD + ESPAÇO/F/G"
    CONTROLES_J2 = "SETAS + ENTER/SHIFT/CTRL"
    CONTAGEM = False
    MOEDAS_PARTIDA = 10
    MOEDAS_VITORIA_J1 = 6

    # --------------------------------------------------------
    # CENÁRIO: templo ao entardecer
    # --------------------------------------------------------

    @classmethod
    def criar_fundo(cls, jogador):
        sup = ui.gradiente(LARGURA, ALTURA, (40, 16, 64), (240, 120, 70))
        # sol
        for r, c in ((130, (250, 150, 90)), (104, (255, 190, 110)), (86, (255, 220, 150))):
            pygame.draw.circle(sup, c, (720, 250), r)
        # montanhas
        pygame.draw.polygon(sup, (110, 50, 90), [(0, 470), (160, 330), (300, 430), (470, 300),
                                                 (650, 440), (820, 320), (1024, 450), (1024, 560),
                                                 (0, 560)])
        pygame.draw.polygon(sup, (78, 34, 70), [(0, 520), (220, 420), (420, 500), (600, 410),
                                                (800, 500), (1024, 430), (1024, 560), (0, 560)])
        # pagode
        sil = (46, 20, 48)
        base_x = 190
        for k, (w, y) in enumerate(((150, 470), (120, 400), (90, 336), (60, 280))):
            pygame.draw.rect(sup, sil, (base_x - w // 2 + 16, y, w - 32, 70 if k == 0 else 64))
            pygame.draw.polygon(sup, sil, [(base_x - w // 2 - 20, y + 6), (base_x, y - 26),
                                           (base_x + w // 2 + 20, y + 6)])
        pygame.draw.line(sup, sil, (base_x, 254), (base_x, 220), 4)
        # torii (moldura)
        verm, verm_e = (200, 40, 40), (130, 20, 30)
        for x in (70, LARGURA - 70):
            pygame.draw.rect(sup, verm_e, (x - 16, 110, 32, CHAO - 110))
            pygame.draw.rect(sup, verm, (x - 12, 110, 24, CHAO - 110))
        pygame.draw.rect(sup, verm_e, (20, 150, LARGURA - 40, 22))
        pygame.draw.polygon(sup, (40, 20, 30), [(0, 100), (LARGURA, 100), (LARGURA - 20, 124),
                                                (20, 124)])
        pygame.draw.rect(sup, verm, (30, 124, LARGURA - 60, 10))
        # lanternas
        for x in (250, 420, 604, 774):
            pygame.draw.line(sup, (40, 20, 30), (x, 172), (x, 196), 2)
            pygame.draw.ellipse(sup, (255, 170, 60), (x - 14, 196, 28, 34))
            pygame.draw.ellipse(sup, (255, 220, 140), (x - 7, 204, 14, 18))
            pygame.draw.rect(sup, (40, 20, 30), (x - 8, 228, 16, 5))
        # chão de pedra em perspectiva
        pygame.draw.rect(sup, (120, 90, 80), (0, 560, LARGURA, ALTURA - 560))
        pygame.draw.rect(sup, (150, 115, 95), (0, 560, LARGURA, 8))
        fuga = (LARGURA // 2, 380)
        for k in range(-12, 13):
            xb = LARGURA // 2 + k * 110
            t = (560 - fuga[1]) / (ALTURA - fuga[1])
            xt = fuga[0] + (xb - fuga[0]) * t
            pygame.draw.line(sup, (100, 72, 66), (xt, 568), (xb, ALTURA), 2)
        y, passo = 575.0, 8.0
        while y < ALTURA:
            pygame.draw.line(sup, (100, 72, 66), (0, int(y)), (LARGURA, int(y)), 2)
            passo *= 1.35
            y += passo
        # emblema no chão
        pygame.draw.ellipse(sup, (200, 150, 60), (LARGURA // 2 - 150, 600, 300, 64), 5)
        pygame.draw.ellipse(sup, (170, 120, 50), (LARGURA // 2 - 90, 612, 180, 40), 3)
        return sup

    @classmethod
    def desenhar_icone(cls, sup, jogador):
        w, h = sup.get_size()
        a = jogador.aparencia()
        outra = ((a[0] + 1) % len(assets.OVOS), (a[1] + 3) % len(assets.CABELOS), a[2], a[3])
        ui.estrela(sup, (w // 2, int(h * 0.5)), int(h * 0.2), (255, 220, 80))
        jogador.desenhar(sup, (int(w * 0.3), int(h * 0.56)), h * 0.36)
        jogador.desenhar(sup, (int(w * 0.7), int(h * 0.56)), h * 0.36, aparencia=outra,
                         espelhar=True)
        pygame.draw.circle(sup, (230, 60, 60), (int(w * 0.43), int(h * 0.5)), max(3, h // 14))
        pygame.draw.circle(sup, (60, 120, 230), (int(w * 0.57), int(h * 0.55)), max(3, h // 14))

    # --------------------------------------------------------
    # ELENCO
    # --------------------------------------------------------

    def __init__(self, app, menu):
        self.seguradas = set()
        self.elenco = None
        self.fase = "selecao"
        self.lut = []
        super().__init__(app, menu)

    def _carregar_elenco(self):
        from core import perfis
        from core.save import Save
        jogs = [(self.jogador.nome or t("VOCÊ"), self.jogador)]
        try:
            slots = perfis.slots_ocupados()
        except Exception:
            slots = []
        for s in slots:
            if s == self.app.slot or len(jogs) >= 5:
                continue
            save = perfis.ler_ovo(s)
            if save is not None:
                j = Jogador(save)
                jogs.append((j.nome or t("OVO {n}", n=s + 1), j))
        nomes = [n for n in NOMES_EXTRAS]
        random.shuffle(nomes)
        while len(jogs) < 5:
            j = Jogador(Save())
            j.definir_aparencia(random.randrange(len(assets.OVOS)),
                                random.randrange(len(assets.CABELOS)),
                                random.randrange(len(assets.OLHOS)),
                                random.randrange(len(assets.BOCAS)))
            jogs.append((nomes.pop(), j))
        self.elenco = [Perfil(n, j, ESTILOS[k]) for k, (n, j) in enumerate(jogs)]

    def _montar_menu_inicio(self):
        super()._montar_menu_inicio()
        for b in self.menu_inicio.botoes[:len(self.OPCOES)]:
            b.tamanho = ui.tamanho_que_cabe(b.rotulo, b.rect.w - 14, (14, 12, 10, 8))

    def reiniciar(self):
        if self.elenco is None:
            self._carregar_elenco()
        self.fase = "selecao"
        self.t_fase = 0.0
        self.cursor = [0, 1]
        self.escolha = [None, None]
        self.bot_roleta = 0.0
        self.lut = []
        self.proj = []
        self.rounds = [0, 0]
        self.n_round = 0
        self.banner = None
        self.hitstop = 0.0
        self.lento = 0.0
        self.timer = TEMPO_ROUND
        self.acoes = [[], []]
        self.buf = [[], []]
        self.relogio = 0.0
        self.fatal = False
        self.venc = None
        self.bot = dict(t=0.0, dx=0, cima=False, baixo=False, bloq=False, hold=0.0)
        self.seguradas.clear()

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
        if e.type != pygame.KEYDOWN:
            return
        for i in (0, 1):
            if i == 1 and self.solo:
                continue
            mov = TECLAS_MOVER[i]
            if self.fase == "selecao":
                self._evento_selecao(i, e.key, mov)
                continue
            for nome, k in mov.items():
                if e.key == k:
                    self.buf[i].append((self.relogio, nome))
                    del self.buf[i][:-4]
            if e.key in TECLAS_SOCO[i]:
                self.acoes[i].append("soco")
            elif e.key in TECLAS_CHUTE[i]:
                self.acoes[i].append("chute")

    def _sequencia(self, i, seq, janela):
        L = self.lut[i]
        frente = "dir" if L.face > 0 else "esq"
        tras = "esq" if L.face > 0 else "dir"
        buf = [n if n in ("cima", "baixo") else ("frente" if n == frente else "tras")
               for t, n in self.buf[i] if self.relogio - t <= janela]
        return buf[-len(seq):] == list(seq)

    # --------------------------------------------------------
    # SELEÇÃO
    # --------------------------------------------------------

    def _evento_selecao(self, i, k, mov):
        if self.escolha[i] is not None:
            return
        n = len(self.elenco)
        if k == mov["esq"]:
            self.cursor[i] = (self.cursor[i] - 1) % n
            self.som("tic", 0.5)
        elif k == mov["dir"]:
            self.cursor[i] = (self.cursor[i] + 1) % n
            self.som("tic", 0.5)
        elif k in TECLAS_SOCO[i] or k in TECLAS_CHUTE[i]:
            if self.cursor[i] == self.escolha[1 - i]:
                self.som("erro", 0.6)
                return
            self.escolha[i] = self.cursor[i]
            self.som("selecionar")
            cx = LARGURA // 2 + (self.cursor[i] - (len(self.elenco) - 1) / 2) * 190
            self.particulas.explodir((cx, 300), [CORES_JOGADOR[i], BRANCO, AMARELO], 24, 300, 0.6)

    def _atualizar_selecao(self, dt):
        if self.solo and self.escolha[0] is not None and self.escolha[1] is None:
            self.bot_roleta += dt
            if int(self.bot_roleta * 12) != int((self.bot_roleta - dt) * 12):
                self.cursor[1] = (self.cursor[1] + 1) % len(self.elenco)
                if self.cursor[1] == self.escolha[0]:
                    self.cursor[1] = (self.cursor[1] + 1) % len(self.elenco)
                self.som("tic", 0.3)
            if self.bot_roleta > 1.0:
                opcoes = [k for k in range(len(self.elenco)) if k != self.escolha[0]]
                self.cursor[1] = self.escolha[1] = random.choice(opcoes)
                self.som("selecionar")
        if self.escolha[0] is not None and self.escolha[1] is not None:
            self.t_fase += dt
            if self.t_fase > 0.9:
                self.lut = [Lutador(0, self.elenco[self.escolha[0]], 330, 1),
                            Lutador(1, self.elenco[self.escolha[1]], LARGURA - 330, -1)]
                self._novo_round()

    # --------------------------------------------------------
    # ROUNDS
    # --------------------------------------------------------

    def _banner_(self, texto, cor, tempo, sub=None):
        self.banner = [texto, cor, tempo, sub]

    def _novo_round(self):
        self.n_round += 1
        for L, x, f in ((self.lut[0], 330, 1), (self.lut[1], LARGURA - 330, -1)):
            L.x, L.y, L.vx, L.vy, L.face = float(x), float(CHAO), 0.0, 0.0, f
            L.vida = L.vida_lenta = 100.0
            L.mudar("normal")
            L.no_chao, L.agachado, L.bloqueando, L.andando = True, False, False, 0
            L.invul = 0.0
        self.proj.clear()
        self.timer = TEMPO_ROUND
        self.fase = "intro"
        self.t_fase = 0.0
        self.acoes = [[], []]
        self._banner_(t("ROUND {n}", n=self.n_round), AMARELO, 1.1)
        self.som("bandeira", 0.7)

    def _ko(self, vencedor, tempo_esgotado=False):
        self.fase = "ko"
        self.t_fase = 0.0
        self.lento = 1.0
        if vencedor is not None:
            self.rounds[vencedor] += 1
            self._banner_("TEMPO!" if tempo_esgotado else "K.O.!", (255, 80, 60), 1.6,
                          t("ROUND DE {nome}", nome=self.lut[vencedor].p.nome))
        else:
            self._banner_("EMPATE!", AMARELO, 1.6)
        self.som("explosao" if not tempo_esgotado else "tic", 0.7)
        self.tremer(0.5)

    def _pos_ko(self):
        v = 0 if self.rounds[0] >= 2 else (1 if self.rounds[1] >= 2 else None)
        if v is None:
            if self.n_round >= 5:
                self._acabar(None)
            else:
                self._novo_round()
            return
        self.venc = v
        per = self.lut[1 - v]
        per.mudar("tonto")
        per.x = max(X_MIN + 40, min(X_MAX - 40, per.x))
        per.y, per.vy, per.vx, per.no_chao = float(CHAO), 0.0, 0.0, True
        w = self.lut[v]
        w.mudar("normal")
        self.fase = "finalize"
        self.t_fase = 0.0
        self.buf = [[], []]
        self.acoes = [[], []]
        self._banner_("FINALIZE-O!", (255, 60, 60), 1.4)
        self.som("bandeira")

    def _fazer_fatal(self):
        self.fase = "fatal"
        self.t_fase = 0.0
        self.fatal = True
        w = self.lut[self.venc]
        w.mudar("ataque")
        w.atk = "fogo"
        self._banner_("FATALOVO!", (255, 60, 60), 3.0, "OMELETE FOFINHO!")
        self.som("levelup")
        self.tremer(0.4)

    def _acabar(self, v):
        linhas = []
        if self.lut:
            linhas.append(f"{self.lut[0].p.nome} × {self.lut[1].p.nome}")
            linhas.append(t("ROUNDS  {a} × {b}", a=self.rounds[0], b=self.rounds[1]))
        if self.fatal:
            linhas.append(t("FATALOVO! OMELETE FOFINHO!"))
        self.terminar_multi(v, linhas)

    # --------------------------------------------------------
    # LÓGICA
    # --------------------------------------------------------

    def atualizar_jogo(self, dt):
        if self.fase == "selecao":
            self._atualizar_selecao(dt)
            return
        if self.banner:
            self.banner[2] -= dt
            if self.banner[2] <= 0:
                self.banner = None
        if self.hitstop > 0:
            self.hitstop -= dt
            return
        if self.lento > 0:
            self.lento -= dt
            dt *= 0.3
        self.t_fase += dt
        self.relogio += dt
        for L in self.lut:
            L.vida_lenta = max(L.vida, L.vida_lenta - 30 * dt)
            L.flash = max(0.0, L.flash - dt)

        entradas = [(0, False, False, False), (0, False, False, False)]
        if self.fase == "intro":
            self.acoes = [[], []]
            if self.t_fase > 1.1 and self.banner is None:
                self._banner_("LUTE!", (255, 70, 50), 0.7)
                self.som("explosao", 0.5)
            if self.t_fase > 1.8:
                self.fase = "luta"
                self.t_fase = 0.0
        elif self.fase == "luta":
            self.timer -= dt
            entradas = [self._entrada(0, dt), self._entrada(1, dt)]
            for i in (0, 1):
                acoes, self.acoes[i] = self.acoes[i], []
                for a in acoes:
                    self._acao(i, a)
            if self.timer <= 0:
                self.timer = 0
                a, b = self.lut[0].vida, self.lut[1].vida
                self._ko(None if abs(a - b) < 0.5 else (0 if a > b else 1), True)
        elif self.fase == "ko":
            if self.t_fase > 1.6:
                self._pos_ko()
        elif self.fase == "finalize":
            v = self.venc
            if not (v == 1 and self.solo):
                entradas[v] = self._entrada(v, dt)
                entradas[v] = (entradas[v][0], False, False, False)
            acoes, self.acoes[v] = self.acoes[v], []
            if "chute" in acoes and self._sequencia(v, ("frente", "frente", "baixo"), 1.5):
                self._fazer_fatal()
            elif v == 1 and self.solo and self.t_fase > 1.3:
                if random.random() < BOTS[self.dificuldade]["fatal"]:
                    self._fazer_fatal()
                else:
                    self.t_fase = 99
            if self.fase == "finalize" and self.t_fase > 5.0:
                per = self.lut[1 - v]
                per.mudar("caido")
                per.vy, per.no_chao = -300, False
                self.som("bater")
                self._vitoria()
        elif self.fase == "fatal":
            self._atualizar_fatal(dt)
        elif self.fase == "vitoria":
            if self.t_fase > 2.4:
                self._acabar(self.venc)

        for i, L in enumerate(self.lut):
            self._atualizar_lutador(L, self.lut[1 - i], entradas[i], dt)
        self._separar()
        self._atualizar_proj(dt)

    def _vitoria(self):
        self.fase = "vitoria"
        self.t_fase = 0.0
        w = self.lut[self.venc]
        w.mudar("vitoria")
        self._banner_(t("{nome} VENCE!", nome=w.p.nome), AMARELO, 2.4, "FATALOVO!" if self.fatal else None)
        self.som("vencer")

    def _atualizar_fatal(self, dt):
        per = self.lut[1 - self.venc]
        if per.estado != "omelete" and self.t_fase > 0.6:
            per.mudar("omelete")
            self.particulas.explodir((per.x, per.y - 80), [BRANCO, AMARELO, (255, 200, 60)],
                                     50, 520, 1.0, (4, 9), 600)
            self.som("explosao")
            self.tremer(0.5)
        if self.t_fase > 0.6:
            n = int((self.t_fase - 0.6) / 0.35)
            if n != getattr(self, "_fogos", -1):
                self._fogos = n
                cor = random.choice([(255, 90, 140), (120, 200, 255), (255, 230, 90),
                                     (140, 255, 150), (220, 140, 255)])
                self.particulas.explodir((random.randint(150, LARGURA - 150),
                                          random.randint(110, 300)),
                                         [cor, BRANCO], 36, 380, 1.1, (3, 6), 200)
                self.som("tic", 0.4)
        if self.t_fase > 3.2:
            self._fogos = -1
            self._vitoria()

    def _entrada(self, i, dt):
        """(dx, cima, baixo, bloq) do humano ou do bot."""
        if i == 1 and self.solo:
            return self._bot(dt)
        m = TECLAS_MOVER[i]
        dx = (1 if self._segura(m["dir"]) else 0) - (1 if self._segura(m["esq"]) else 0)
        bloq = any(self._segura(k) for k in TECLAS_BLOQ[i])
        return dx, self._segura(m["cima"]), self._segura(m["baixo"]), bloq

    def _acao(self, i, acao):
        L = self.lut[i]
        if L.estado != "normal":
            return
        if acao == "soco" and self._sequencia(i, ("baixo", "frente"), 0.5):
            acao = "especial"
        if not L.no_chao:
            if acao in ("soco", "chute"):
                self._atacar(L, "voadora")
            return
        if acao == "especial":
            esp = L.p.estilo["esp"]
            if esp == "fogo" and any(p["dono"] == i for p in self.proj):
                return
            self._atacar(L, esp)
            self.som("asa", 0.8)
            self.particulas.explodir((L.x, L.y - 100), [L.p.estilo["cor"], BRANCO], 14, 260, 0.4)
            self.buf[i].clear()
        elif acao == "soco":
            self._atacar(L, "soco_baixo" if L.agachado else "soco")
        elif acao == "chute":
            self._atacar(L, "rasteira" if L.agachado else "chute")

    def _atacar(self, L, atk):
        L.mudar("ataque")
        L.atk = atk
        L.acertou = False
        L.bloqueando = False
        L._vy_feito = False
        if atk not in BAIXOS:
            L.agachado = False
        if atk == "teleporte":
            L.invul = 0.35
            self.particulas.explodir((L.x, L.y - 90), [(200, 170, 255), BRANCO], 22, 260, 0.5)
        if atk in ("soco", "chute", "soco_baixo", "rasteira"):
            self.som("asa", 0.35)

    def _atualizar_lutador(self, L, O, entrada, dt):
        L.t += dt
        L.invul = max(0.0, L.invul - dt)
        dx, cima, baixo, bloq = entrada
        L.andando = 0

        if L.estado == "normal":
            if L.no_chao:
                L.face = 1 if O.x >= L.x else -1
                L.agachado = baixo
                L.bloqueando = bloq
                if bloq or baixo:
                    L.vx = 0.0
                else:
                    v = VEL_ANDAR * L.vel * (0.8 if dx == -L.face else 1.0)
                    if L.i == 1 and self.solo:
                        v *= BOTS[self.dificuldade]["vel"]
                    L.vx = dx * v
                    L.andando = dx
                if cima and not baixo and not bloq and self.fase == "luta":
                    L.vy = -VEL_PULO * L.pulo
                    L.vx = dx * 270
                    L.no_chao = False
                    L.agachado = False
                    self.som("pulo", 0.4)
        elif L.estado == "ataque":
            d = ATAQUES[L.atk]
            if L.atk == "teleporte":
                if L.t >= d["ini"]:
                    L.x = max(X_MIN, min(X_MAX, O.x - O.face * 80))
                    if abs(L.x - O.x) < 40:
                        L.x = max(X_MIN, min(X_MAX, O.x + O.face * 80))
                    L.face = 1 if O.x >= L.x else -1
                    self.particulas.explodir((L.x, L.y - 90), [(200, 170, 255), BRANCO],
                                             22, 260, 0.5)
                    self._atacar(L, "chute_tele")
                    self.som("boing", 0.6)
            else:
                ativo = d["ini"] <= L.t < d["ini"] + d["ativo"]
                if "vx" in d and L.t < d["ini"] + d["ativo"] and not L.acertou:
                    L.vx = L.face * d["vx"]
                elif L.no_chao:
                    L.vx *= max(0.0, 1 - 12 * dt)
                if "vy" in d and L.t >= d["ini"] and not L._vy_feito:
                    L._vy_feito = True
                    L.vy = d["vy"]
                    L.no_chao = False
                if L.atk == "fogo" and not L.acertou and L.t >= d["ini"] and self.fase == "luta":
                    L.acertou = True
                    self.proj.append(dict(x=L.x + L.face * 70, y=L.y - 110,
                                          vx=L.face * 540, dono=L.i, t=0.0))
                if ativo and not L.acertou and d["dano"] > 0 and self.fase == "luta":
                    if L.hitbox().colliderect(O.hurtbox()):
                        L.acertou = True
                        self._acertar(L, O, d)
                fim = d["ini"] + d["ativo"] + d["rec"]
                if L.atk == "voadora":
                    if L.no_chao:
                        L.mudar("normal")
                elif L.t >= fim and (L.no_chao or L.atk == "gancho"):
                    L.mudar("normal")
        elif L.estado == "dano":
            L.vx *= max(0.0, 1 - 8 * dt)
            if L.t >= L.stun:
                L.mudar("normal")
                L.combo = 0
                O.combo = 0
        elif L.estado == "deitado":
            L.vx = 0.0
            if L.t > 0.55:
                L.mudar("normal")
                L.invul = 0.3
                O.combo = 0
        elif L.estado in ("ko", "tonto", "omelete", "vitoria"):
            L.vx *= max(0.0, 1 - 10 * dt)

        L.x += L.vx * dt
        if not L.no_chao:
            L.vy += GRAVIDADE * dt
            L.y += L.vy * dt
            if L.y >= CHAO:
                L.y = float(CHAO)
                L.vy = 0.0
                L.no_chao = True
                if L.estado == "caido":
                    L.mudar("ko" if L.vida <= 0 or self.fase in ("ko", "vitoria") else "deitado")
                    self.tremer(0.15)
                    self.particulas.explodir((L.x, CHAO), [(170, 140, 120), (200, 170, 150)],
                                             12, 200, 0.5, (3, 6), 400)
                    self.som("bater", 0.5)
                elif L.estado == "normal":
                    L.vx = 0.0
        L.x = max(X_MIN, min(X_MAX, L.x))

    def _separar(self):
        if len(self.lut) < 2:
            return
        a, b = self.lut
        if a.estado == "omelete" or b.estado == "omelete":
            return
        if a.no_chao and b.no_chao or abs(a.y - b.y) < 90:
            d = b.x - a.x
            if abs(d) < DIST_MIN:
                s = 1 if d > 0 else -1
                if d == 0:
                    s = a.face
                meio = (DIST_MIN - abs(d)) / 2
                a.x -= s * meio
                b.x += s * meio
                for L in (a, b):
                    L.x = max(X_MIN, min(X_MAX, L.x))

    def _acertar(self, A, B, d, pos=None):
        if B.invul > 0 or B.estado in ("caido", "deitado", "ko"):
            return
        dirn = 1 if B.x >= A.x else -1
        if pos is None:
            pos = (B.x - dirn * 24, A.hitbox().centery if A.atk in ATAQUES else B.y - 100)
        dano = d["dano"] * A.forca
        de_frente = B.face == -dirn
        baixo = A.atk in BAIXOS if A.estado == "ataque" else False
        bloqueou = (B.bloqueando and B.estado == "normal" and B.no_chao and de_frente
                    and (B.agachado or not baixo))
        if bloqueou:
            B.vida -= dano * 0.15
            B.vx = dirn * d["emp"] * 0.7
            self.hitstop = 0.04
            self.particulas.explodir(pos, [(140, 200, 255), BRANCO], 10, 240, 0.3, (2, 5), 0)
            self.som("tic", 0.7)
        else:
            A.combo = A.combo + 1 if B.estado == "dano" else 1
            dano *= max(0.5, 1 - 0.15 * (A.combo - 1))
            B.vida -= dano
            B.flash = 0.08
            B.agachado = B.bloqueando = False
            if d.get("derruba") or B.vida <= 0:
                B.mudar("caido")
                B.vy = -420 if B.vida > 0 else -560
                B.vx = dirn * 280
                B.no_chao = False
            else:
                B.mudar("dano")
                B.stun = d["stun"]
                B.vx = dirn * d["emp"]
            self.hitstop = 0.05 + dano * 0.005
            self.tremer(0.08 + dano * 0.012)
            self.particulas.explodir(pos, [AMARELO, BRANCO, B.p.cor], 10 + int(dano), 340, 0.45,
                                     (3, 7), 300)
            self.textos.adicionar(str(int(round(dano))), (pos[0], pos[1] - 20), (255, 230, 120), 14)
            if A.combo >= 2:
                self.textos.adicionar(t("{n} GOLPES!", n=A.combo), (A.x, A.y - 200), (255, 140, 60), 12)
            self.som("bater", 0.8)
        if B.vida <= 0:
            B.vida = 0
            if self.fase == "luta":
                self._ko(A.i)

    def _atualizar_proj(self, dt):
        vivos = []
        for p in self.proj:
            p["x"] += p["vx"] * dt
            p["t"] += dt
            alvo = self.lut[1 - p["dono"]]
            r = pygame.Rect(int(p["x"]) - 18, int(p["y"]) - 18, 36, 36)
            if self.fase == "luta" and r.colliderect(alvo.hurtbox()) and alvo.invul <= 0 \
                    and alvo.estado not in ("caido", "deitado", "ko"):
                dono = self.lut[p["dono"]]
                d = dict(dano=10, emp=260, stun=0.35)
                self._acertar(dono, alvo, d, (p["x"], p["y"]))
                self.particulas.explodir((p["x"], p["y"]), [(255, 200, 60), (255, 120, 40)],
                                         20, 300, 0.5)
                continue
            if X_MIN - 60 < p["x"] < X_MAX + 60:
                if int(p["t"] * 30) % 2 == 0:
                    self.particulas.explodir((p["x"] - p["vx"] * 0.03, p["y"]),
                                             [(255, 170, 40), (255, 230, 90)], 2, 60, 0.3,
                                             (2, 5), -100)
                vivos.append(p)
        # dois limões se anulam
        if len(vivos) == 2 and vivos[0]["dono"] != vivos[1]["dono"] \
                and abs(vivos[0]["x"] - vivos[1]["x"]) < 36:
            self.particulas.explodir((vivos[0]["x"], vivos[0]["y"]), [(255, 200, 60), BRANCO],
                                     30, 360, 0.6)
            self.som("explosao", 0.5)
            vivos = []
        self.proj = vivos

    # --------------------------------------------------------
    # BOT
    # --------------------------------------------------------

    def _bot(self, dt):
        cfg = BOTS[self.dificuldade]
        b = self.bot
        me, op = self.lut[1], self.lut[0]
        b["hold"] -= dt
        b["t"] -= dt
        if b["hold"] <= 0:
            b["bloq"] = b["baixo"] = b["cima"] = False
        if b["t"] > 0 or me.estado != "normal":
            return b["dx"], b["cima"], b["baixo"], b["bloq"]
        b["t"] = cfg["reacao"] * random.uniform(0.7, 1.3)
        dist = abs(op.x - me.x)
        fwd = 1 if op.x > me.x else -1
        b["dx"] = 0
        r = random.random

        ameaca_proj = any(p["dono"] == 0 and (p["x"] - me.x) * p["vx"] < 0
                          and abs(p["x"] - me.x) < 260 for p in self.proj)
        d = ATAQUES.get(op.atk) if op.estado == "ataque" else None
        ameaca = d is not None and op.t < d["ini"] + d["ativo"] and dist < 190
        recuperando = d is not None and op.t >= d["ini"] + d["ativo"]

        if not me.no_chao:
            if dist < 120:
                self.acoes[1].append("chute")
            return 0, False, False, False
        if ameaca or ameaca_proj:
            if r() < cfg["bloq"]:
                b["bloq"] = True
                b["baixo"] = op.atk in BAIXOS if d else False
                b["hold"] = 0.35
                return 0, False, b["baixo"], True
            if ameaca_proj and r() < cfg["pular"] * 4:
                b["cima"], b["hold"] = True, 0.1
                b["dx"] = fwd
                return fwd, True, False, False
        esp = me.p.estilo["esp"]
        if recuperando and dist < 140 and r() < cfg["pune"]:
            if esp in ("gancho", "investida", "deslize") and r() < 0.6:
                self._bot_especial(me)
            else:
                self.acoes[1].append("chute")
            return 0, False, False, False
        if dist > 140:
            if r() < cfg["especial"] and (esp in ("fogo", "teleporte") and dist > 240
                                          or esp in ("investida", "deslize") and dist < 330):
                self._bot_especial(me)
                return 0, False, False, False
            if r() < cfg["pular"]:
                b["cima"], b["hold"] = True, 0.1
            b["dx"] = fwd
        else:
            if r() < cfg["ataque"]:
                escolha = random.random()
                if escolha < 0.1 + cfg["especial"] * 0.5 and esp == "gancho":
                    self._bot_especial(me)
                elif escolha < 0.4:
                    self.acoes[1].append("soco")
                elif escolha < 0.7:
                    self.acoes[1].append("chute")
                else:
                    b["baixo"], b["hold"] = True, 0.25
                    me.agachado = True
                    self.acoes[1].append("chute" if r() < 0.5 else "soco")
            elif r() < 0.4:
                b["dx"] = -fwd
        return b["dx"], b["cima"], b["baixo"], b["bloq"]

    def _bot_especial(self, me):
        if me.estado == "normal" and me.no_chao:
            esp = me.p.estilo["esp"]
            if esp == "fogo" and any(p["dono"] == 1 for p in self.proj):
                return
            self._atacar(me, esp)
            self.som("asa", 0.8)

    # --------------------------------------------------------
    # DESENHO
    # --------------------------------------------------------

    def _omelete(self):
        s = getattr(self, "_sup_omelete", None)
        if s is None:
            s = pygame.Surface((170, 80), pygame.SRCALPHA)
            for cx, cy, r in ((40, 50, 28), (85, 44, 36), (130, 50, 28), (62, 58, 24),
                              (110, 58, 24)):
                pygame.draw.circle(s, (235, 235, 230), (cx, cy), r + 2)
            for cx, cy, r in ((40, 50, 28), (85, 44, 36), (130, 50, 28), (62, 58, 24),
                              (110, 58, 24)):
                pygame.draw.circle(s, (255, 255, 250), (cx, cy), r)
            pygame.draw.circle(s, (240, 170, 30), (85, 42), 25)
            pygame.draw.circle(s, (255, 205, 50), (85, 42), 22)
            pygame.draw.circle(s, (255, 240, 170), (77, 34), 6)
            for ox in (-8, 8):
                pygame.draw.ellipse(s, (40, 30, 30), (85 + ox - 3, 36, 6, 9))
            pygame.draw.arc(s, (40, 30, 30), (77, 42, 16, 12), math.pi, 2 * math.pi, 2)
            for ox in (-15, 15):
                pygame.draw.circle(s, (255, 140, 150), (85 + ox, 50), 4)
            self._sup_omelete = s
        return s

    def _sombra(self):
        s = getattr(self, "_sup_sombra", None)
        if s is None:
            s = pygame.Surface((96, 20), pygame.SRCALPHA)
            pygame.draw.ellipse(s, (30, 10, 20, 90), s.get_rect())
            self._sup_sombra = s
        return s

    def _limao(self, t):
        frames = getattr(self, "_frames_limao", None)
        if frames is None:
            base = ui.limao_sup(18)
            frames = [pygame.transform.rotate(base, a * 30) for a in range(12)]
            self._frames_limao = frames
        return frames[int(t * 24) % 12]

    def desenhar_jogo(self, tela):
        tela.blit(self.fundo(self.jogador), (0, 0))
        if self.estado == "inicio":
            return
        if self.fase == "selecao":
            self._desenhar_selecao(tela)
            self.particulas.desenhar(tela)
            return

        sombra = self._sombra()
        for L in self.lut:
            if not (L.estado == "ataque" and L.atk == "teleporte"):
                tela.blit(sombra, sombra.get_rect(center=(int(L.x), CHAO + 2)))
        ordem = sorted(self.lut, key=lambda L: L.estado == "ataque")
        for L in ordem:
            self._desenhar_lutador(tela, L)
        for p in self.proj:
            img = self._limao(p["t"])
            tela.blit(img, img.get_rect(center=(int(p["x"]), int(p["y"]))))
        self.particulas.desenhar(tela)
        self.textos.desenhar(tela)
        self._desenhar_banner(tela)
        if self.fase == "finalize" and not (self.venc == 1 and self.solo):
            ui.desenhar_texto(tela, t("FRENTE, FRENTE, BAIXO + CHUTE"), (LARGURA // 2, 250), 12,
                              (255, 220, 120), "center")

    def _desenhar_lutador(self, tela, L):
        if L.estado == "omelete":
            s = self._omelete()
            pulo = abs(math.sin(L.t * 5)) * 10 * max(0.0, 1 - L.t / 2)
            tela.blit(s, s.get_rect(midbottom=(int(L.x), CHAO + 6 - int(pulo))))
            for k in range(3):
                fase = (L.t * 0.7 + k / 3) % 1.0
                ui.coracao(tela, (int(L.x - 40 + k * 40), int(CHAO - 60 - fase * 90)),
                           int(8 + 4 * (1 - fase)))
            return
        pose = L.pose(self.tempo)
        if pose is None:
            return
        if L.invul > 0 and L.estado == "normal" and int(self.tempo * 20) % 2:
            return
        s = L.p.sprite(pose, L.face, L.flash > 0)
        ax = ANCORA[0]
        tela.blit(s, (int(L.x) - ax, int(L.y) - ANCORA[1]))
        if L.estado == "tonto":
            for k in range(3):
                a = self.tempo * 4 + k * math.tau / 3
                ui.estrela(tela, (int(L.x + math.cos(a) * 34), int(L.y - 190 + math.sin(a) * 8)),
                           7, AMARELO, a)

    def _desenhar_banner(self, tela):
        if not self.banner:
            return
        texto, cor, _, sub = self.banner
        texto, sub = t(texto), t(sub)
        tam = 48 if len(texto) <= 10 else 32
        ui.desenhar_texto(tela, texto, (LARGURA // 2, 300), tam, cor, "center")
        if sub:
            ui.desenhar_texto(tela, sub, (LARGURA // 2, 350), 16, BRANCO, "center")

    def _desenhar_selecao(self, tela):
        ui.veu(tela, 110)
        ui.desenhar_texto(tela, t("ESCOLHA SEU LUTADOR"), (LARGURA // 2, 70), 26, AMARELO, "center")
        n = len(self.elenco)
        for k, per in enumerate(self.elenco):
            r = pygame.Rect(0, 0, 176, 200)
            r.center = (LARGURA // 2 + (k - (n - 1) / 2) * 190, 250)
            ui.painel(tela, r, (34, 26, 48), per.estilo["cor"], 14, 3, sombra=False)
            img = per.retrato(80)
            tela.blit(img, img.get_rect(center=(r.centerx, r.y + 80)))
            tam = ui.tamanho_que_cabe(per.nome, r.w - 16, (12, 10, 8))
            ui.desenhar_texto(tela, per.nome, (r.centerx, r.y + 150), tam, BRANCO, "center")
            est = t(per.estilo["nome"])
            ui.desenhar_texto(tela, est, (r.centerx, r.y + 176),
                              ui.tamanho_que_cabe(est, r.w - 14, (8, 6)), per.estilo["cor"],
                              "center")
            for i in (0, 1):
                if self.cursor[i] == k:
                    cor = CORES_JOGADOR[i]
                    grossura = 6 if self.escolha[i] == k else 3
                    pygame.draw.rect(tela, cor, r.inflate(10 + i * 10, 10 + i * 10), grossura, 16)
                    rot = t("J1") if i == 0 else ("BOT" if self.solo else t("J2"))
                    ui.desenhar_texto(tela, rot, (r.x + 8 if i == 0 else r.right - 8, r.y - 14),
                                      12, cor, "midleft" if i == 0 else "midright")
        # prévias grandes
        for i, x in ((0, 200), (1, LARGURA - 200)):
            per = self.elenco[self.cursor[i]]
            pose = "vitoria0" if self.escolha[i] is not None else \
                ("idle0" if int(self.tempo * 2.5) % 2 == 0 else "idle1")
            s = per.sprite(pose, 1 if i == 0 else -1)
            tela.blit(s, (x - ANCORA[0], 660 - ANCORA[1]))
            e = per.estilo
            bx = x + (150 if i == 0 else -150)
            anc = "midleft" if i == 0 else "midright"
            ui.desenhar_texto(tela, per.nome, (bx, 440), 16, CORES_JOGADOR[i], anc)
            ui.desenhar_texto(tela, t("ESPECIAL:"), (bx, 472), 10, BRANCO, anc)
            ui.desenhar_texto(tela, t(e["nome"]), (bx, 490), 10, e["cor"], anc)
            for k, (rot, v) in enumerate(((t("VEL"), e["vel"]), (t("FOR"), e["forca"]),
                                          (t("PULO"), e["pulo"]))):
                y = 520 + k * 26
                w = max(4, min(90, int(90 * (v - 0.7) / 0.5)))
                if i == 0:
                    ui.desenhar_texto(tela, rot, (bx, y), 10, BRANCO, "midleft")
                    pygame.draw.rect(tela, (60, 50, 70), (bx + 50, y - 6, 90, 12))
                    pygame.draw.rect(tela, e["cor"], (bx + 50, y - 6, w, 12))
                else:
                    ui.desenhar_texto(tela, rot, (bx, y), 10, BRANCO, "midright")
                    pygame.draw.rect(tela, (60, 50, 70), (bx - 140, y - 6, 90, 12))
                    pygame.draw.rect(tela, e["cor"], (bx - 50 - w, y - 6, w, 12))
        dica = t("A/D + ESPAÇO") + ("" if self.solo else "   |   " + t("SETAS + ENTER"))
        ui.desenhar_texto(tela, dica, (LARGURA // 2, 690), 10, (220, 210, 240), "center")

    def desenhar_hud(self, tela):
        if self.fase == "selecao" or len(self.lut) < 2:
            return
        w = 380
        for i, L in enumerate(self.lut):
            x0 = 512 - 58 - w if i == 0 else 512 + 58
            r = pygame.Rect(x0, 18, w, 26)
            pygame.draw.rect(tela, (20, 14, 26), r.inflate(8, 8), border_radius=6)
            pygame.draw.rect(tela, (120, 20, 30), r)
            lenta = int(w * L.vida_lenta / 100)
            viva = int(w * L.vida / 100)
            cor = (90, 220, 90) if L.vida > 30 else (240, 200, 60)
            if i == 0:
                pygame.draw.rect(tela, (250, 240, 200), (r.right - lenta, r.y, lenta, r.h))
                pygame.draw.rect(tela, cor, (r.right - viva, r.y, viva, r.h))
            else:
                pygame.draw.rect(tela, (250, 240, 200), (r.x, r.y, lenta, r.h))
                pygame.draw.rect(tela, cor, (r.x, r.y, viva, r.h))
            pygame.draw.rect(tela, BRANCO, r, 2)
            anc = "topleft" if i == 0 else "topright"
            px = r.x if i == 0 else r.right
            ui.desenhar_texto(tela, L.p.nome, (px, 54), 12, CORES_JOGADOR[i], anc)
            tag = t("J1") if i == 0 else ("BOT" if self.solo else t("J2"))
            ui.desenhar_texto(tela, tag, (px, 72), 8, BRANCO, anc)
            for k in range(2):
                cx = (r.right - 12 - k * 24) if i == 0 else (r.x + 12 + k * 24)
                ganho = self.rounds[i] > k
                pygame.draw.circle(tela, (40, 30, 40), (cx, 94), 9)
                pygame.draw.circle(tela, AMARELO if ganho else (90, 80, 90), (cx, 94), 7)
        caixa = pygame.Rect(0, 0, 84, 54)
        caixa.midtop = (512, 10)
        ui.painel(tela, caixa, (20, 14, 26), (200, 150, 60), 10, 3, sombra=False)
        cor = (255, 90, 80) if self.timer < 10 else AMARELO
        ui.desenhar_texto(tela, str(int(math.ceil(self.timer))), caixa.center, 22, cor, "center")

    def _desenhar_inicio(self, tela):
        ui.veu(tela, 150)
        topo = 22
        caixa = pygame.Rect(0, topo, 800, ALTURA - topo - 22)
        caixa.centerx = LARGURA // 2
        ui.painel(tela, caixa, (28, 20, 36), self.COR, 22, 5)
        ui.desenhar_texto(tela, t(self.TITULO), (LARGURA // 2, topo + 18), 28, AMARELO, "midtop")
        ui.desenhar_texto(tela, t("VS BOT OU 2 JOGADORES"), (LARGURA // 2, topo + 56), 12,
                          (255, 190, 170), "midtop")
        if self.elenco:
            n = len(self.elenco)
            for k, per in enumerate(self.elenco):
                x = int(LARGURA // 2 + (k - (n - 1) / 2) * 120)
                img = per.retrato(56)
                dy = int(math.sin(self.tempo * 3 + k) * 4)
                tela.blit(img, img.get_rect(center=(x, topo + 128 + dy)))
                ui.desenhar_texto(tela, per.nome, (x, topo + 170),
                                  ui.tamanho_que_cabe(per.nome, 112, (10, 8)), BRANCO, "midtop")
        y = topo + 200
        for linha in self.INSTRUCOES:
            for sub in ui.quebrar_linhas(t(linha), 10, caixa.w - 60):
                ui.desenhar_texto(tela, sub, (LARGURA // 2, y), 10, BRANCO, "midtop")
                y += 16
            y += 4
        v = self.vitorias()
        y_rec = self.menu_inicio.botoes[0].rect.y - 30
        ui.desenhar_texto(tela, t("VITÓRIAS  J1 {a} × {b} J2", a=v[0], b=v[1]), (LARGURA // 2, y_rec),
                          12, AMARELO, "midtop")
        self.menu_inicio.desenhar(tela)
