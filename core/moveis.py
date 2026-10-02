import math
import random
import time

import pygame

from settings import *
from core import assets, ui
from core.idioma import t

# ============================================================
# MÓVEIS DA CASA E DO QUINTAL (SOL)
# ============================================================
# Cada móvel é um objeto com posição fixa na tela (1024x720) que
# a cena da casa desenha na ordem de `base_y` (quem toca o chão
# mais "atrás" é desenhado primeiro). As partes paradas de cada
# móvel são pintadas UMA vez numa Surface em cache; por frame só
# desenhamos as partes animadas (poucas primitivas).
#
# Métodos chamados pela cena (ver a classe Movel):
#   atualizar(dt, ctx)             lógica / timers
#   desenhar(tela, ctx)            antes do ovo
#   desenhar_ovo_ocupado(tela, ctx) só quando o ovo "ocupa" o móvel
#   desenhar_frente(tela, ctx)     depois do ovo (água, cobertor...)
#   desenhar_brilho(tela, ctx)     DEPOIS do véu de noite/luz apagada
#                                  (o que brilha no escuro)
#   desenhar_sobreposicao(tela, ctx) por cima de tudo (telescópio)
#   clicar(pos, ctx) -> bool       True = consumiu o clique
#   dica(ctx) -> str | None        texto ao passar o mouse

# ============================================================
# CATÁLOGO
# ============================================================

CATALOGO = {
    # Grátis (sempre presentes)
    "geladeira": dict(nome="GELADEIRA", preco=0, raridade="COMUM", comodo="CASA",
                      loja=False, desc="Guarda as comidas do ovo."),
    "interruptor": dict(nome="INTERRUPTOR", preco=0, raridade="COMUM", comodo="CASA",
                        loja=False, desc="Apaga a luz para o ovo dormir."),

    # CASA
    "tapete": dict(nome="TAPETE REDONDO", preco=80, raridade="COMUM", comodo="CASA",
                   loja=True, desc="Um tapete fofinho para a sala."),
    "planta": dict(nome="PLANTA NO VASO", preco=70, raridade="COMUM", comodo="CASA",
                   loja=True, desc="Balança as folhas quando você mexe nela."),
    "lampada_lava": dict(nome="LÂMPADA DE LAVA", preco=90, raridade="COMUM", comodo="CASA",
                         loja=True, desc="Bolhas coloridas que brilham no escuro."),
    "retrato": dict(nome="RETRATO DO OVO", preco=90, raridade="COMUM", comodo="CASA",
                    loja=True, desc="Uma foto sua! Clique para trocar o fundo."),
    "relogio_cuco": dict(nome="RELÓGIO CUCO", preco=180, raridade="INCOMUM", comodo="CASA",
                         loja=True, desc="Mostra a hora de verdade. CUCO!"),
    "vitrola": dict(nome="VITROLA", preco=250, raridade="INCOMUM", comodo="CASA",
                    loja=True, desc="Toca as músicas dos jogos que você já jogou."),
    "estante_trofeus": dict(nome="ESTANTE DE TROFÉUS", preco=300, raridade="INCOMUM",
                            comodo="CASA", loja=True,
                            desc="Mostra os troféus que você ganhou nos jogos."),
    "tv": dict(nome="TELEVISÃO", preco=400, raridade="RARO", comodo="CASA",
               loja=True, desc="4 canais! Assistir deixa o ovo feliz."),
    "aquario": dict(nome="AQUÁRIO", preco=450, raridade="RARO", comodo="CASA",
                    loja=True, desc="Três peixinhos. Dê ração para eles!"),
    "cama": dict(nome="CAMA", preco=550, raridade="RARO", comodo="CASA",
                 loja=True, desc="Dormir na cama recupera energia 2x mais rápido."),

    # SOL (quintal)
    "canteiro_2": dict(nome="CANTEIRO EXTRA", preco=150, raridade="COMUM", comodo="SOL",
                       loja=True, desc="Mais um canteiro para plantar."),
    "canteiro_3": dict(nome="CANTEIRO EXTRA", preco=300, raridade="INCOMUM", comodo="SOL",
                       loja=True, desc="Mais um canteiro para plantar."),
    "canteiro_4": dict(nome="CANTEIRO EXTRA", preco=500, raridade="RARO", comodo="SOL",
                       loja=True, desc="Mais um canteiro para plantar."),
    "cata_vento": dict(nome="CATA-VENTO", preco=60, raridade="COMUM", comodo="SOL",
                       loja=True, desc="Gira com o vento. Clique para soprar!"),
    "casinha_pet": dict(nome="CASINHA DO PET", preco=250, raridade="INCOMUM", comodo="SOL",
                        loja=True, desc="O seu pet dorme nela à noite."),
    "piscina": dict(nome="PISCINA INFLÁVEL", preco=350, raridade="INCOMUM", comodo="SOL",
                    loja=True, desc="Banho divertido: limpa e diverte."),
    "varal_luzes": dict(nome="VARAL DE LUZES", preco=120, raridade="COMUM", comodo="SOL",
                        loja=True, desc="Luzinhas coloridas que acendem à noite."),
    "telescopio": dict(nome="TELESCÓPIO", preco=450, raridade="RARO", comodo="SOL",
                       loja=True, desc="À noite, pegue uma estrela cadente!"),
    "balanco": dict(nome="ÁRVORE COM BALANÇO", preco=500, raridade="RARO", comodo="SOL",
                    loja=True, desc="O ovo senta e balança. Uhuuu!"),
}

# Contorno de madeira escura usado em quase tudo (combina com o fundo)
MADEIRA_ESCURA = (70, 42, 22)


# ============================================================
# AJUDANTES DE DESENHO (CACHE)
# ============================================================

_rascunho = None
_sprites = {}


def _tela_rascunho():
    """Surface transparente do tamanho da tela, reaproveitada para
    pintar as partes estáticas com coordenadas absolutas."""
    global _rascunho
    if _rascunho is None:
        _rascunho = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
    _rascunho.fill((0, 0, 0, 0))
    return _rascunho


def _preparar(sup, rle=False):
    """Converte para o formato da tela. `rle=True` (sprites que nunca
    mudam) deixa o blit ~5x mais rápido: as áreas transparentes e
    opacas viram "trechos" copiados de uma vez."""
    if pygame.display.get_surface() is not None:
        sup = sup.convert_alpha()
    if rle:
        sup.set_alpha(255, pygame.RLEACCEL)
    return sup


def _sprite(chave, caixa, pintor):
    """Pinta (uma vez) com `pintor(sup)` em coordenadas de tela e
    guarda só o pedaço `caixa`. Devolve (Surface, pos)."""
    s = _sprites.get(chave)
    caixa = pygame.Rect(caixa)
    if s is None:
        r = _tela_rascunho()
        pintor(r)
        s = _preparar(r.subsurface(caixa).copy(), rle=True)
        _sprites[chave] = s
    return s, caixa.topleft


def _blit_sprite(tela, chave, caixa, pintor, desloc=(0, 0)):
    s, pos = _sprite(chave, caixa, pintor)
    tela.blit(s, (pos[0] + desloc[0], pos[1] + desloc[1]))


_brilhos = {}


def _brilho(raio, cor, alpha):
    """Bolinha de luz radial (centro mais forte) em cache."""
    chave = (raio, cor, alpha)
    s = _brilhos.get(chave)
    if s is None:
        s = pygame.Surface((raio * 2, raio * 2), pygame.SRCALPHA)
        passos = 7
        for i in range(passos):
            r = max(1, int(raio * (1 - i / passos)))
            a = int(alpha * (i + 1) / passos)
            pygame.draw.circle(s, (*cor, a), (raio, raio), r)
        s = _preparar(s, rle=True)
        _brilhos[chave] = s
    return s


def _blit_brilho(tela, centro, raio, cor, alpha):
    s = _brilho(raio, cor, alpha)
    tela.blit(s, (int(centro[0]) - raio, int(centro[1]) - raio))


def _sombra_chao(sup, rect, alpha=70):
    """Sombra suave (elipse) no chão, pintada no sprite estático."""
    rect = pygame.Rect(rect)
    s = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.ellipse(s, (0, 0, 0, alpha), s.get_rect())
    sup.blit(s, rect)


def _girar(ponto, centro, ang):
    """Gira `ponto` em volta de `centro` (ang em radianos, sentido
    horário na tela)."""
    c, s = math.cos(ang), math.sin(ang)
    dx, dy = ponto[0] - centro[0], ponto[1] - centro[1]
    return (centro[0] + dx * c - dy * s, centro[1] + dx * s + dy * c)


def _cor_ovo(ctx):
    try:
        return ctx.app.jogador.cor
    except AttributeError:
        return (120, 200, 255)


def _ovinho(tela, centro, larg, cor, contorno=None):
    """Mini-ovo desenhado com primitivas (cuco, cobertor...)."""
    r = pygame.Rect(0, 0, larg, int(larg * 1.25))
    r.center = (int(centro[0]), int(centro[1]))
    pygame.draw.ellipse(tela, cor, r)
    if contorno:
        pygame.draw.ellipse(tela, contorno, r, 1)
    return r


def _nota(tela, pos, cor, tam=1.0):
    """Notinha musical (bolinha + haste + bandeirinha)."""
    x, y = int(pos[0]), int(pos[1])
    r = max(2, int(3 * tam))
    pygame.draw.circle(tela, cor, (x, y), r)
    topo = y - int(12 * tam)
    pygame.draw.line(tela, cor, (x + r - 1, y), (x + r - 1, topo), 2)
    pygame.draw.line(tela, cor, (x + r - 1, topo), (x + r + int(5 * tam), topo + int(4 * tam)), 2)


def _borboleta(tela, pos, cor, bater):
    """Borboletinha: 2 pares de asas triangulares batendo."""
    x, y = pos
    a = 0.35 + 0.65 * abs(bater)
    esc = ui.escurecer(cor, 60)
    for lado in (-1, 1):
        cima = [(x, y), (x + lado * 11 * a, y - 9), (x + lado * 9 * a, y + 1)]
        baixo = [(x, y + 1), (x + lado * 8 * a, y + 8), (x + lado * 3 * a, y + 6)]
        pygame.draw.polygon(tela, cor, cima)
        pygame.draw.polygon(tela, esc, cima, 1)
        pygame.draw.polygon(tela, ui.clarear(cor, 30), baixo)
    pygame.draw.line(tela, (40, 30, 30), (x, y - 5), (x, y + 6), 2)


# ============================================================
# CLASSE BASE
# ============================================================

class Movel:
    """Móvel genérico (também serve para os canteiros, que a cena
    do jardim desenha)."""

    # Caixa que contém TODO o desenho (usada no ícone da loja)
    caixa = (0, 0, 10, 10)
    # Móveis que o ovo "ocupa" (cama, balanço, piscina)
    ocupavel = False

    def __init__(self, movel_id):
        self.id = movel_id
        info = CATALOGO.get(movel_id, {})
        self.nome = info.get("nome", movel_id.upper())
        self.comodo = info.get("comodo", "CASA")
        self.base_y = 0
        self.rect = pygame.Rect(0, 0, 0, 0)

    # True enquanto o móvel mostra uma tela por cima de tudo
    # (o telescópio). A cena deve mandar TODOS os cliques para ele.
    @property
    def modal(self):
        return False

    def atualizar(self, dt, ctx):
        pass

    def desenhar(self, tela, ctx):
        pass

    def desenhar_frente(self, tela, ctx):
        pass

    def desenhar_brilho(self, tela, ctx):
        pass

    def desenhar_sobreposicao(self, tela, ctx):
        pass

    def clicar(self, pos, ctx):
        return False

    def dica(self, ctx):
        return None

    def ovo_chegou(self, ctx):
        pass

    def desenhar_ovo_ocupado(self, tela, ctx):
        pass

    # --------------------------------------------------------

    def _ocupado(self, ctx):
        return getattr(ctx, "ovo_ocupado", None) is self

    def _mouse_em_cima(self):
        try:
            return self.rect.collidepoint(pygame.mouse.get_pos())
        except pygame.error:
            return False


# ============================================================
# GELADEIRA
# ============================================================

class Geladeira(Movel):

    caixa = (86, 296, 140, 304)

    def __init__(self, movel_id):
        super().__init__(movel_id)
        self.rect = pygame.Rect(96, 300, 120, 290)
        self.base_y = 590
        self.tremer = 0.0

    def _pintar(self, cor_ovo):
        def pintor(s):
            _sombra_chao(s, (90, 580, 132, 16), 80)
            corpo = pygame.Rect(96, 300, 120, 290)
            pygame.draw.rect(s, (235, 240, 245), corpo, border_radius=8)
            # Faixa de sombra na lateral direita (volume)
            pygame.draw.rect(s, (215, 222, 232), (184, 304, 28, 282), border_radius=6)
            # Brilho na esquerda
            pygame.draw.rect(s, (252, 253, 255), (102, 308, 8, 86), border_radius=4)
            pygame.draw.rect(s, (252, 253, 255), (102, 408, 8, 150), border_radius=4)
            pygame.draw.rect(s, (150, 160, 175), corpo, 3, border_radius=8)
            # Divisão congelador / geladeira
            pygame.draw.line(s, (150, 160, 175), (97, 400), (214, 400), 3)
            # Puxadores
            pygame.draw.rect(s, (170, 175, 190), (196, 330, 6, 40), border_radius=3)
            pygame.draw.rect(s, (170, 175, 190), (196, 420, 6, 60), border_radius=3)
            pygame.draw.rect(s, (120, 125, 140), (196, 330, 6, 40), 1, border_radius=3)
            pygame.draw.rect(s, (120, 125, 140), (196, 420, 6, 60), 1, border_radius=3)
            # Pezinhos
            pygame.draw.rect(s, (90, 95, 110), (104, 588, 12, 5))
            pygame.draw.rect(s, (90, 95, 110), (196, 588, 12, 5))
            # Ímã de limão
            ui.limao(s, (130, 340), 7)
            # Ímã-estrela
            ui.estrela(s, (168, 352), 7, (255, 120, 150))
            # "Desenho de criança" do ovo preso na porta
            papel = pygame.Rect(106, 432, 38, 46)
            pygame.draw.rect(s, (255, 253, 235), papel)
            pygame.draw.rect(s, (200, 195, 170), papel, 1)
            pygame.draw.circle(s, (230, 70, 70), (125, 434), 3)
            ovo = pygame.Rect(0, 0, 18, 22)
            ovo.center = (125, 457)
            pygame.draw.ellipse(s, cor_ovo, ovo)
            pygame.draw.ellipse(s, ui.escurecer(cor_ovo, 70), ovo, 1)
            pygame.draw.circle(s, (20, 20, 20), (121, 454), 1)
            pygame.draw.circle(s, (20, 20, 20), (129, 454), 1)
            pygame.draw.arc(s, (20, 20, 20), (120, 455, 10, 6), math.pi, 2 * math.pi, 1)
            # Sol rabiscado no cantinho do desenho
            pygame.draw.circle(s, (255, 210, 60), (139, 439), 3)
            # Grama rabiscada
            pygame.draw.line(s, (90, 190, 80), (108, 472), (142, 472), 2)
        return pintor

    def atualizar(self, dt, ctx):
        self.tremer = max(0.0, self.tremer - dt)

    def desenhar(self, tela, ctx):
        cor = _cor_ovo(ctx)
        dx = int(math.sin(self.tremer * 60) * 2) if self.tremer > 0 else 0
        _blit_sprite(tela, ("geladeira", cor), self.caixa, self._pintar(cor), (dx, 0))

    def clicar(self, pos, ctx):
        if not self.rect.collidepoint(pos):
            return False
        self.tremer = 0.25
        ctx.som("clique")
        ctx.abrir_bandeja()
        return True

    def dica(self, ctx):
        return t("GELADEIRA: COMIDA")


# ============================================================
# INTERRUPTOR
# ============================================================

class Interruptor(Movel):

    caixa = (228, 356, 30, 42)

    def __init__(self, movel_id):
        super().__init__(movel_id)
        self.rect = pygame.Rect(224, 352, 38, 50)      # um pouco maior: fácil de clicar
        self.base_y = 394

    def desenhar(self, tela, ctx):
        placa = pygame.Rect(232, 360, 22, 34)
        pygame.draw.rect(tela, (240, 235, 220), placa, border_radius=4)
        pygame.draw.rect(tela, (120, 100, 80), placa, 2, border_radius=4)
        pygame.draw.rect(tela, (200, 190, 170), (238, 367, 10, 20), border_radius=2)
        y = 378 if ctx.luz_apagada else 368
        pygame.draw.rect(tela, (255, 255, 250), (238, y, 10, 8), border_radius=2)
        pygame.draw.rect(tela, (150, 135, 110), (238, y, 10, 8), 1, border_radius=2)

    def clicar(self, pos, ctx):
        if not self.rect.collidepoint(pos):
            return False
        ctx.som("clique")
        ctx.alternar_luz()
        return True

    def dica(self, ctx):
        return t("ACENDER A LUZ") if ctx.luz_apagada else t("APAGAR A LUZ")


# ============================================================
# TAPETE
# ============================================================

class Tapete(Movel):

    caixa = (280, 618, 464, 76)

    def __init__(self, movel_id):
        super().__init__(movel_id)
        self.rect = pygame.Rect(282, 620, 460, 70)
        self.base_y = 540       # fica embaixo de tudo

    @staticmethod
    def _pintar(s):
        for larg, alt, cor in ((460, 70, (190, 60, 80)), (400, 56, (240, 200, 90)),
                               (330, 42, (190, 60, 80)), (240, 28, (250, 240, 220))):
            r = pygame.Rect(0, 0, larg, alt)
            r.center = (512, 655)
            pygame.draw.ellipse(s, cor, r)
        # Bolinhas decorativas na faixa amarela
        for i in range(14):
            a = i / 14 * math.tau
            x = 512 + math.cos(a) * 183
            y = 655 + math.sin(a) * 24.5
            pygame.draw.circle(s, (190, 60, 80), (int(x), int(y)), 3)
        r = pygame.Rect(0, 0, 460, 70)
        r.center = (512, 655)
        pygame.draw.ellipse(s, (130, 35, 55), r, 2)

    def desenhar(self, tela, ctx):
        _blit_sprite(tela, "tapete", self.caixa, self._pintar)


# ============================================================
# PLANTA NO VASO
# ============================================================

class Planta(Movel):

    caixa = (536, 426, 88, 170)
    PIVO = (578, 535)
    # (ângulo em graus a partir da vertical, comprimento, largura)
    FOLHAS = [(-42, 72, 13), (40, 70, 13), (-20, 92, 14), (18, 90, 14), (0, 98, 12)]
    CORES = [(60, 160, 70), (90, 190, 80)]
    BORBOLETAS = [(255, 150, 60), (90, 170, 255), (255, 220, 70), (255, 130, 190),
                  (120, 220, 110), (170, 110, 230), (245, 245, 255)]

    def __init__(self, movel_id):
        super().__init__(movel_id)
        self.rect = pygame.Rect(546, 436, 64, 156)
        self.base_y = 590
        self.mexer = 0.0          # tempo desde o último clique (balanço forte)
        self.borboletas = []      # [x, y, vx, vida, cor, fase]

    @staticmethod
    def _pintar_vaso(s):
        _sombra_chao(s, (548, 582, 60, 12), 80)
        vaso = [(556, 540), (600, 540), (594, 590), (562, 590)]
        pygame.draw.polygon(s, (200, 110, 60), vaso)
        pygame.draw.polygon(s, (230, 140, 85), [(560, 544), (568, 544), (568, 586), (565, 586)])
        pygame.draw.line(s, (165, 85, 45), (560, 562), (597, 562), 2)
        pygame.draw.polygon(s, (120, 60, 30), vaso, 2)
        borda = pygame.Rect(552, 534, 52, 8)
        pygame.draw.rect(s, (170, 90, 50), borda, border_radius=2)
        pygame.draw.rect(s, (120, 60, 30), borda, 2, border_radius=2)

    def atualizar(self, dt, ctx):
        self.mexer += dt
        vivas = []
        for b in self.borboletas:
            b[3] -= dt
            b[0] += b[2] * dt
            b[1] -= 38 * dt
            if b[3] > 0:
                vivas.append(b)
        self.borboletas = vivas

    def _folha(self, ang_base, ang, comp, larg):
        px, py = self.PIVO
        a = math.radians(ang + ang_base)
        dx, dy = math.sin(a), -math.cos(a)
        nx, ny = -dy, dx
        # Ponta um pouco caída (curva) para as folhas laterais
        cai = abs(ang) / 45 * 10
        tx, ty = px + dx * comp, py + dy * comp + cai

        def p(f, w):
            return (px + dx * comp * f + nx * w, py + dy * comp * f + ny * w + cai * f * f)

        return [(px, py), p(0.25, larg * 0.6), p(0.55, larg), p(0.8, larg * 0.7),
                (tx, ty), p(0.8, -larg * 0.7), p(0.55, -larg), p(0.25, -larg * 0.6)], (tx, ty)

    def desenhar(self, tela, ctx):
        t = ctx.tempo
        ang = 3 * math.sin(t)
        if self.mexer < 1.5:
            ang += 12 * math.exp(-3 * self.mexer) * math.sin(14 * self.mexer)
        for i, (a0, comp, larg) in enumerate(self.FOLHAS):
            pontos, ponta = self._folha(a0, ang * (0.6 + 0.2 * (i % 3)), comp, larg)
            cor = self.CORES[i % 2]
            pygame.draw.polygon(tela, cor, pontos)
            pygame.draw.polygon(tela, (30, 95, 40), pontos, 1)
            pygame.draw.line(tela, (40, 120, 50), self.PIVO, ponta, 1)
        _blit_sprite(tela, "planta_vaso", self.caixa, self._pintar_vaso)

    def desenhar_frente(self, tela, ctx):
        for x, y, _, vida, cor, fase in self.borboletas:
            bx = x + math.sin(vida * 5 + fase) * 12
            _borboleta(tela, (int(bx), int(y)), cor, math.sin(vida * 22))

    def clicar(self, pos, ctx):
        if not self.rect.collidepoint(pos):
            return False
        self.mexer = 0.0
        ctx.som("asa", 0.7)
        dia = ctx.fase_dia != "noite" and not ctx.luz_apagada
        if dia and len(self.borboletas) < 3:
            self.borboletas.append([578.0, 470.0, random.choice((-40, 40, 55)), 4.5,
                                    random.choice(self.BORBOLETAS), random.uniform(0, 6)])
        ctx.particulas.explodir((578, 480), [(60, 160, 70), (90, 190, 80)], qtd=5,
                                vel=120, vida=0.6, tamanho=(2, 4))
        return True


# ============================================================
# LÂMPADA DE LAVA
# ============================================================

class LampadaLava(Movel):

    caixa = (424, 438, 40, 84)
    VIDRO = [(437, 500), (451, 500), (455, 470), (449, 448), (439, 448), (433, 470)]

    def __init__(self, movel_id):
        super().__init__(movel_id)
        self.rect = pygame.Rect(426, 436, 36, 84)
        self.base_y = 515

    @classmethod
    def _pintar_fundo(cls, s):
        # Prateleirinha própria (fica escondida pelo rack quando há TV)
        pygame.draw.rect(s, (130, 85, 50), (426, 514, 36, 6))
        pygame.draw.rect(s, MADEIRA_ESCURA, (426, 514, 36, 6), 1)
        base = [(432, 515), (456, 515), (452, 500), (436, 500)]
        pygame.draw.polygon(s, (80, 80, 90), base)
        pygame.draw.polygon(s, (40, 40, 50), base, 1)
        pygame.draw.line(s, (120, 120, 135), (436, 506), (452, 506), 1)
        pygame.draw.polygon(s, (255, 140, 80, 120), cls.VIDRO)

    @classmethod
    def _pintar_frente(cls, s):
        pygame.draw.polygon(s, (200, 90, 50), cls.VIDRO, 1)
        pygame.draw.line(s, (255, 230, 200), (437, 468), (440, 452), 2)
        tampa = [(436, 448), (452, 448), (450, 442), (438, 442)]
        pygame.draw.polygon(s, (80, 80, 90), tampa)
        pygame.draw.polygon(s, (40, 40, 50), tampa, 1)

    def _bolhas(self, tela, t, forte=False):
        cor = (255, 110, 50) if forte else (255, 90, 40)
        for i, (vel, fase, r) in enumerate(((0.7, 0.0, 6), (0.5, 2.1, 5), (0.9, 4.0, 4))):
            s = math.sin(t * vel + fase)
            y = 474 - 18 * s
            x = 444 + 3 * math.sin(t * 1.3 + i * 2)
            # A bolha estica um pouco quando está subindo/descendo rápido
            estica = 1 + 0.25 * abs(math.cos(t * vel + fase))
            rr = pygame.Rect(0, 0, int(r * 2 / estica), int(r * 2 * estica))
            rr.center = (int(x), int(y))
            pygame.draw.ellipse(tela, cor, rr)
        pygame.draw.ellipse(tela, cor, (437, 492, 14, 8))      # lava acumulada no fundo

    def _escuro(self, ctx):
        return ctx.luz_apagada

    def desenhar(self, tela, ctx):
        if self._escuro(ctx):
            _blit_brilho(tela, (444, 476), 70, (255, 140, 80), 40)
        _blit_sprite(tela, "lava_fundo", self.caixa, self._pintar_fundo)
        self._bolhas(tela, ctx.tempo)
        _blit_sprite(tela, "lava_frente", self.caixa, self._pintar_frente)

    def desenhar_brilho(self, tela, ctx):
        if not self._escuro(ctx):
            return
        _blit_brilho(tela, (444, 476), 70, (255, 140, 80), 45)
        _blit_brilho(tela, (444, 476), 34, (255, 170, 110), 70)
        pygame.draw.polygon(tela, (170, 70, 45), self.VIDRO)
        self._bolhas(tela, ctx.tempo, forte=True)
        _blit_sprite(tela, "lava_frente", self.caixa, self._pintar_frente)

    def clicar(self, pos, ctx):
        return False


# ============================================================
# RETRATO DO OVO
# ============================================================

class Retrato(Movel):

    caixa = (838, 368, 96, 110)
    CORES = [(255, 235, 180), (200, 230, 255), (220, 255, 210), (255, 210, 230), (230, 220, 255)]

    def __init__(self, movel_id):
        super().__init__(movel_id)
        self.rect = pygame.Rect(842, 378, 88, 96)
        self.base_y = 474
        self.cor = 1

    @staticmethod
    def _pintar_moldura(s):
        pygame.draw.circle(s, (90, 90, 100), (886, 373), 3)        # preguinho
        moldura = pygame.Rect(842, 378, 88, 96)
        pygame.draw.rect(s, (150, 100, 55), moldura, 6)
        pygame.draw.rect(s, (185, 130, 75), moldura.inflate(-4, -4), 1)
        pygame.draw.rect(s, MADEIRA_ESCURA, moldura, 2)
        pygame.draw.rect(s, MADEIRA_ESCURA, moldura.inflate(-12, -12), 1)

    def desenhar(self, tela, ctx):
        interno = pygame.Rect(848, 384, 76, 84)
        cor = self.CORES[self.cor]
        tela.fill(cor, interno)
        # Chão do "estúdio" da foto
        tela.fill(ui.escurecer(cor, 22), (848, 452, 76, 16))

        antigo = tela.get_clip()
        tela.set_clip(interno.clip(antigo) if antigo else interno)
        tem_pet = bool(ctx.pet_id)
        cx = 878 if tem_pet else 886
        ctx.desenhar_ovo(tela, (cx, 430), 50)
        if tem_pet:
            try:
                from core import pets
                pets.desenhar_parado(tela, ctx.pet_id, (910, 464), 0.0, False, escala=0.45)
            except (TypeError, AttributeError, KeyError):
                pass
        tela.set_clip(antigo)
        _blit_sprite(tela, "retrato_moldura", self.caixa, self._pintar_moldura)

    def clicar(self, pos, ctx):
        if not self.rect.collidepoint(pos):
            return False
        self.cor = (self.cor + 1) % len(self.CORES)
        ctx.som("virar", 0.7)
        return True


# ============================================================
# RELÓGIO CUCO
# ============================================================
# (Um pouco abaixo do desenho original para não ficar atrás
# do painel com o nome do cômodo no HUD.)

class RelogioCuco(Movel):

    caixa = (506, 86, 78, 158)
    DY = 56
    CENTRO = (545, 141)

    def __init__(self, movel_id):
        super().__init__(movel_id)
        self.rect = pygame.Rect(512, 90, 66, 150)
        self.base_y = 240
        self.ultima_hora = None
        self.fila = 0             # quantos "CUCO!" faltam
        self.anim = -1.0          # tempo da animação atual (-1 = parado)
        self.cantou = False       # já disse "CUCO!" nesta animação

    @classmethod
    def _pintar(cls, s):
        dy = cls.DY
        # Correntes com os pesos em forma de pinha
        for x in (529, 561):
            pygame.draw.line(s, (180, 150, 60), (x, 110 + dy), (x, 124 + dy + 54), 1)
            pinha = pygame.Rect(x - 4, 176 + dy - 2, 8, 16)
            pygame.draw.ellipse(s, (120, 75, 35), pinha)
            pygame.draw.ellipse(s, MADEIRA_ESCURA, pinha, 1)
        # Corpo
        corpo = pygame.Rect(522, 60 + dy, 46, 50)
        pygame.draw.rect(s, (140, 90, 50), corpo)
        pygame.draw.rect(s, MADEIRA_ESCURA, corpo, 2)
        # Telhado
        telhado = [(516, 62 + dy), (545, 38 + dy), (574, 62 + dy)]
        pygame.draw.polygon(s, (100, 60, 30), telhado)
        pygame.draw.polygon(s, MADEIRA_ESCURA, telhado, 2)
        # Folhinhas entalhadas
        for lado in (-1, 1):
            f = pygame.Rect(0, 0, 12, 6)
            f.center = (545 + lado * 16, 58 + dy)
            pygame.draw.ellipse(s, (70, 150, 60), f)
        # Buraco da porta
        pygame.draw.rect(s, (40, 25, 15), (537, 44 + dy, 16, 12))
        # Mostrador
        pygame.draw.circle(s, (250, 248, 240), cls.CENTRO, 14)
        pygame.draw.circle(s, MADEIRA_ESCURA, cls.CENTRO, 14, 2)
        for i in range(12):
            a = i / 12 * math.tau
            p1 = (cls.CENTRO[0] + math.sin(a) * 11, cls.CENTRO[1] - math.cos(a) * 11)
            p2 = (cls.CENTRO[0] + math.sin(a) * 9, cls.CENTRO[1] - math.cos(a) * 9)
            pygame.draw.line(s, (90, 80, 70), p1, p2, 1)

    def atualizar(self, dt, ctx):
        h, _ = ctx.hora_real()
        if self.ultima_hora is None:
            self.ultima_hora = h
        elif h != self.ultima_hora:
            self.ultima_hora = h
            self.fila = min(3, (h % 12) or 12)

        if self.anim >= 0:
            self.anim += dt
            if self.anim > 1.0:
                self.anim = -1.0
        if self.anim < 0 and self.fila > 0:
            self.fila -= 1
            self.anim = 0.0
            self.cantou = False

        # O "CUCO!" sai no meio da animação
        if self.anim >= 0.3 and not self.cantou:
            self.cantou = True
            if ctx.comodo == self.comodo:
                ctx.som("boing", 0.6)

    def desenhar(self, tela, ctx):
        dy = self.DY
        # Pêndulo (atrás do corpo)
        ang = math.radians(15) * math.sin(math.tau * ctx.tempo)
        topo = (545, 110 + dy)
        fim = (545 + math.sin(ang) * 70, 110 + dy + math.cos(ang) * 70)
        pygame.draw.line(tela, (180, 150, 60), topo, fim, 2)
        pygame.draw.circle(tela, (255, 200, 40), (int(fim[0]), int(fim[1])), 6)
        pygame.draw.circle(tela, (170, 120, 20), (int(fim[0]), int(fim[1])), 6, 1)

        _blit_sprite(tela, "cuco", self.caixa, self._pintar)

        # Ponteiros com a hora de verdade
        h, m = ctx.hora_real()
        cx, cy = self.CENTRO
        ah = ((h % 12) + m / 60) / 12 * math.tau
        am = m / 60 * math.tau
        pygame.draw.line(tela, (30, 30, 30), (cx, cy),
                         (cx + math.sin(ah) * 7, cy - math.cos(ah) * 7), 2)
        pygame.draw.line(tela, (30, 30, 30), (cx, cy),
                         (cx + math.sin(am) * 11, cy - math.cos(am) * 11), 1)
        pygame.draw.circle(tela, (200, 60, 60), (cx, cy), 2)

        # Porta + mini-ovo saindo
        porta = pygame.Rect(537, 44 + dy, 16, 12)
        if self.anim >= 0:
            fora = math.sin(min(1.0, self.anim) * math.pi)       # 0 -> 1 -> 0
            _ovinho(tela, (545, porta.centery - 2 - 10 * fora), 8 + int(6 * fora),
                    _cor_ovo(ctx), (40, 40, 50))
            pygame.draw.rect(tela, (160, 105, 60), (porta.x - 5, porta.y, 5, 12))
            if self.anim >= 0.3:
                # Balãozinho "CUCO!" (fica abaixo do painel do HUD)
                balao = pygame.Rect(562, 86, 54, 18)
                pygame.draw.polygon(tela, BRANCO, [(556, 100), (566, 92), (568, 100)])
                pygame.draw.rect(tela, BRANCO, balao, border_radius=6)
                pygame.draw.rect(tela, (60, 60, 70), balao, 1, border_radius=6)
                ui.desenhar_texto(tela, t("CUCO!"), balao.center, 8, (40, 30, 30), "center",
                                  sombra=False)
        else:
            pygame.draw.rect(tela, (160, 105, 60), porta)
            pygame.draw.rect(tela, MADEIRA_ESCURA, porta, 1)
            pygame.draw.circle(tela, (230, 190, 90), (550, porta.centery), 1)

    def clicar(self, pos, ctx):
        if not self.rect.collidepoint(pos):
            return False
        if self.fila == 0 and self.anim < 0:
            self.fila = 1
        return True

    def dica(self, ctx):
        h, m = ctx.hora_real()
        return f"{h:02d}:{m:02d}"


# ============================================================
# VITROLA (JUKEBOX)
# ============================================================

class Vitrola(Movel):

    caixa = (460, 462, 96, 132)
    CORES_NOTAS = [(255, 230, 120), (255, 150, 190), (150, 220, 255), (170, 255, 170)]

    def __init__(self, movel_id):
        super().__init__(movel_id)
        self.rect = pygame.Rect(462, 466, 92, 126)
        self.base_y = 590
        self.tocando = False      # a cena pode ligar (ou usar ctx.jukebox_tocando)
        self.notas = []           # [x, y, vida, cor, fase]
        self.prox_nota = 0.0
        self.diversao = 0.0

    @staticmethod
    def _pintar(s):
        _sombra_chao(s, (462, 582, 92, 12), 80)
        # Mesinha: tampo, pés e prateleira de baixo com discos
        for x in (472, 536):
            pygame.draw.rect(s, (130, 85, 50), (x, 518, 6, 72))
            pygame.draw.rect(s, MADEIRA_ESCURA, (x, 518, 6, 72), 1)
        pygame.draw.rect(s, (130, 85, 50), (470, 560, 74, 6))
        pygame.draw.rect(s, MADEIRA_ESCURA, (470, 560, 74, 6), 1)
        for i, cor in enumerate(((60, 60, 70), (200, 70, 70), (70, 110, 200))):
            pygame.draw.rect(s, cor, (484 + i * 12, 540, 10, 20))
            pygame.draw.rect(s, (25, 25, 30), (484 + i * 12, 540, 10, 20), 1)
        tampo = pygame.Rect(466, 510, 82, 10)
        pygame.draw.rect(s, (150, 100, 60), tampo, border_radius=2)
        pygame.draw.rect(s, MADEIRA_ESCURA, tampo, 2, border_radius=2)
        # Caixa da vitrola
        caixa = pygame.Rect(472, 485, 70, 26)
        pygame.draw.rect(s, (170, 60, 50), caixa, border_radius=3)
        pygame.draw.rect(s, (200, 90, 75), (475, 488, 64, 4), border_radius=2)
        pygame.draw.rect(s, (100, 30, 25), caixa, 2, border_radius=3)
        pygame.draw.circle(s, (230, 200, 120), (482, 502), 3)
        pygame.draw.circle(s, (230, 200, 120), (532, 502), 3)
        for x in range(492, 524, 5):
            pygame.draw.line(s, (120, 40, 35), (x, 496), (x, 506), 1)
        # Disco
        disco = pygame.Rect(480, 478, 46, 12)
        pygame.draw.ellipse(s, (25, 25, 30), disco)
        pygame.draw.ellipse(s, (60, 60, 70), disco.inflate(-12, -4), 1)
        pygame.draw.ellipse(s, (220, 50, 50), (497, 482, 12, 4))

    def _tocando(self, ctx):
        return bool(getattr(ctx, "jukebox_tocando", False)) or self.tocando

    def atualizar(self, dt, ctx):
        tocando = self._tocando(ctx)
        if tocando:
            self.prox_nota -= dt
            if self.prox_nota <= 0 and len(self.notas) < 6:
                self.prox_nota = 0.6
                self.notas.append([503.0, 472.0, 2.2, random.choice(self.CORES_NOTAS),
                                   random.uniform(0, 6)])
            self.diversao += dt
            if self.diversao >= 15 and ctx.comodo == self.comodo:
                self.diversao = 0.0
                ctx.mudar_necessidade("diversao", 1, (505, 450))
        vivas = []
        for n in self.notas:
            n[2] -= dt
            n[1] -= 34 * dt
            if n[2] > 0:
                vivas.append(n)
        self.notas = vivas

    def desenhar(self, tela, ctx):
        _blit_sprite(tela, "vitrola", self.caixa, self._pintar)
        tocando = self._tocando(ctx)
        # Brilho girando no disco (dá a ideia de rotação)
        if tocando:
            a = ctx.tempo * 6
            p1 = (503 + math.cos(a) * 9, 484 + math.sin(a) * 2.5)
            p2 = (503 + math.cos(a) * 20, 484 + math.sin(a) * 5)
            pygame.draw.line(tela, (150, 150, 165), p1, p2, 1)
        # Braço da agulha
        ponta = (514, 483) if tocando else (530, 491)
        pygame.draw.line(tela, (190, 190, 200), (536, 480), ponta, 2)
        pygame.draw.circle(tela, (150, 150, 160), (536, 480), 3)

    def desenhar_frente(self, tela, ctx):
        for x, y, vida, cor, fase in self.notas:
            _nota(tela, (x + math.sin(vida * 4 + fase) * 10, y), cor)

    def clicar(self, pos, ctx):
        if not self.rect.collidepoint(pos):
            return False
        ctx.som("selecionar")
        ctx.abrir_jukebox()
        return True

    def dica(self, ctx):
        return "JUKEBOX"


# ============================================================
# ESTANTE DE TROFÉUS
# ============================================================

MEDALHAS = {"ouro": (255, 200, 40), "prata": (200, 205, 215), "bronze": (205, 125, 60)}
_ORDEM_MEDALHA = {"ouro": 0, "prata": 1, "bronze": 2}
_trofeus_sup = {}


def _trofeu(medalha):
    """Taça (trapézio + 2 alças + base) em cache: 22x32 px."""
    s = _trofeus_sup.get(medalha)
    if s is None:
        cor = MEDALHAS.get(medalha, MEDALHAS["bronze"])
        esc = ui.escurecer(cor, 80)
        s = pygame.Surface((22, 32), pygame.SRCALPHA)
        for lado in (-1, 1):
            r = pygame.Rect(0, 0, 10, 10)
            r.center = (11 + lado * 8, 8)
            pygame.draw.ellipse(s, esc, r, 2)
        taca = [(3, 2), (19, 2), (15, 14), (7, 14)]
        pygame.draw.polygon(s, cor, taca)
        pygame.draw.polygon(s, esc, taca, 1)
        pygame.draw.line(s, ui.clarear(cor, 70), (6, 4), (8, 11), 2)
        pygame.draw.rect(s, cor, (9, 14, 4, 8))
        pygame.draw.rect(s, esc, (9, 14, 4, 8), 1)
        pygame.draw.rect(s, cor, (4, 22, 14, 4))
        pygame.draw.rect(s, (90, 60, 40), (3, 26, 16, 6))
        pygame.draw.rect(s, esc, (4, 22, 14, 4), 1)
        s = _preparar(s, rle=True)
        _trofeus_sup[medalha] = s
    return s


class EstanteTrofeus(Movel):

    caixa = (286, 108, 218, 196)
    PRATELEIRAS = (190, 280)

    def __init__(self, movel_id):
        super().__init__(movel_id)
        self.rect = pygame.Rect(290, 110, 210, 182)
        self.base_y = 290
        self.lista = []           # [(titulo, medalha, texto)] já ordenada (máx 16)
        self.recarga = 0.0

    @classmethod
    def _pintar(cls, s):
        for y in cls.PRATELEIRAS:
            for x in (300, 482):
                mao = [(x, y + 10), (x + 16, y + 10), (x, y + 26)]
                pygame.draw.polygon(s, (110, 70, 40), mao)
                pygame.draw.polygon(s, MADEIRA_ESCURA, mao, 1)
            pygame.draw.rect(s, (130, 85, 50), (290, y, 210, 10))
            pygame.draw.line(s, (165, 115, 70), (291, y + 1), (498, y + 1), 1)
            pygame.draw.rect(s, MADEIRA_ESCURA, (290, y, 210, 10), 2)
        # Plaquinha
        placa = pygame.Rect(352, 116, 86, 20)
        pygame.draw.rect(s, (150, 100, 55), placa, border_radius=4)
        pygame.draw.rect(s, MADEIRA_ESCURA, placa, 2, border_radius=4)
        rot = ui.texto(t("TROFÉUS"), 8, (255, 225, 140), sombra=False)
        s.blit(rot, rot.get_rect(center=placa.center))

    def _atualizar_lista(self, ctx):
        try:
            todos = list(ctx.trofeus())
        except (AttributeError, TypeError):
            todos = []
        todos.sort(key=lambda tr: _ORDEM_MEDALHA.get(tr[1], 3))
        self.lista = todos[:16]

    def atualizar(self, dt, ctx):
        self.recarga -= dt
        if self.recarga <= 0:
            self.recarga = 1.0
            self._atualizar_lista(ctx)

    def _slot(self, i):
        prat = i // 8
        x = 304 + (i % 8) * 26
        y = self.PRATELEIRAS[prat]
        return pygame.Rect(x - 11, y - 32, 22, 32)

    def desenhar(self, tela, ctx):
        if not self.lista and self.recarga <= 0:
            self._atualizar_lista(ctx)
        _blit_sprite(tela, "estante", self.caixa, self._pintar)
        brilho = int(ctx.tempo / 1.5)
        for i, (_, medalha, _) in enumerate(self.lista):
            r = self._slot(i)
            tela.blit(_trofeu(medalha), r)
            # Uma faísca passeia pelos troféus de ouro
            if medalha == "ouro" and i == brilho % max(1, len(self.lista)):
                fase = (ctx.tempo / 1.5) % 1
                tam = int(5 * math.sin(fase * math.pi)) + 1
                ui.estrela(tela, (r.x + 6, r.y + 5), tam, (255, 255, 230), fase * 3)

    def _indice_em(self, pos):
        for i in range(len(self.lista)):
            if self._slot(i).inflate(4, 4).collidepoint(pos):
                return i
        return None

    def _texto(self, i):
        titulo, medalha, rec = self.lista[i]
        txt = f"{titulo} - {str(medalha).upper()}"
        return f"{txt} ({rec})" if rec else txt

    def dica(self, ctx):
        try:
            pos = pygame.mouse.get_pos()
        except pygame.error:
            return None
        i = self._indice_em(pos)
        if i is not None:
            return self._texto(i)
        if self.rect.collidepoint(pos) and not self.lista:
            return t("GANHE TROFÉUS NOS MINI JOGOS!")
        return None

    def clicar(self, pos, ctx):
        i = self._indice_em(pos)
        if i is None:
            return False
        r = self._slot(i)
        ctx.som("ponto", 0.7)
        ctx.textos.adicionar(self._texto(i), (r.centerx if r.centerx > 380 else 380, r.y - 8),
                             AMARELO, 10)
        return True


# ============================================================
# TELEVISÃO
# ============================================================
# (TV 8 px mais estreita que no desenho original, para caber a
# lâmpada de lava no canto do rack sem encostar.)

class Televisao(Movel):

    caixa = (244, 360, 222, 234)
    TELA = pygame.Rect(274, 415, 136, 86)
    CANAIS = ["DESLIGADA", "ROBERT SHOW", "DESENHO", "CHUVISCO", "RECORDES"]
    X_CENTRO = 342

    def __init__(self, movel_id):
        super().__init__(movel_id)
        self.rect = pygame.Rect(250, 364, 210, 226)
        self.base_y = 590
        self.canal = 0
        self.troca = 0.0          # mostra "CH n" por um tempinho
        self.diversao = 0.0
        self.letreiro = ""

    # ------------------ partes estáticas --------------------

    @staticmethod
    def _pintar(s):
        _sombra_chao(s, (244, 580, 222, 14), 80)
        # Rack
        pygame.draw.rect(s, (120, 80, 50), (250, 518, 210, 66))
        pygame.draw.rect(s, MADEIRA_ESCURA, (250, 518, 210, 66), 2)
        for x in (258, 358):
            porta = pygame.Rect(x, 525, 94, 53)
            pygame.draw.rect(s, (135, 92, 58), porta)
            pygame.draw.rect(s, (95, 60, 35), porta, 2)
        pygame.draw.circle(s, (230, 190, 90), (344, 551), 3)
        pygame.draw.circle(s, (230, 190, 90), (366, 551), 3)
        pygame.draw.rect(s, (150, 100, 60), (246, 512, 218, 8), border_radius=2)
        pygame.draw.rect(s, MADEIRA_ESCURA, (246, 512, 218, 8), 2, border_radius=2)
        for x in (256, 444):
            pygame.draw.rect(s, MADEIRA_ESCURA, (x, 584, 10, 6))
        # Antena
        for ponta in ((312, 368), (374, 366)):
            pygame.draw.line(s, (60, 60, 70), (342, 404), ponta, 2)
            pygame.draw.circle(s, (60, 60, 70), ponta, 3)
        pygame.draw.ellipse(s, (60, 60, 70), (332, 398, 20, 10))
        # Corpo
        corpo = pygame.Rect(262, 405, 160, 110)
        pygame.draw.rect(s, (45, 45, 55), corpo, border_radius=10)
        pygame.draw.rect(s, (70, 70, 85), corpo.inflate(-6, -6), 2, border_radius=8)
        pygame.draw.rect(s, (20, 20, 25), corpo, 2, border_radius=10)
        pygame.draw.rect(s, (15, 15, 20), Televisao.TELA.inflate(4, 4), border_radius=4)

    @staticmethod
    def _pintar_vidro(s):
        # Reflexo + linhas de varredura por cima da tela
        t = Televisao.TELA
        for y in range(t.y, t.bottom, 3):
            pygame.draw.line(s, (0, 0, 0, 28), (t.x, y), (t.right - 1, y))
        pygame.draw.polygon(s, (255, 255, 255, 26),
                            [(t.x, t.y), (t.x + 60, t.y), (t.x, t.y + 50)])

    _chuvisco = []

    @classmethod
    def _quadros_chuvisco(cls):
        if not cls._chuvisco:
            rnd = random.Random(7)
            for _ in range(4):
                s = pygame.Surface(cls.TELA.size)
                for y in range(0, cls.TELA.h, 4):
                    for x in range(0, cls.TELA.w, 4):
                        v = rnd.randint(40, 230)
                        s.fill((v, v, v), (x, y, 4, 4))
                cls._chuvisco.append(s.convert() if pygame.display.get_surface() else s)
        return cls._chuvisco

    # ------------------ lógica ------------------------------

    def atualizar(self, dt, ctx):
        self.troca = max(0.0, self.troca - dt)
        if self.canal and ctx.comodo == self.comodo and abs(ctx.ovo_x - self.X_CENTRO) < 220:
            self.diversao += dt
            if self.diversao >= 10:
                self.diversao = 0.0
                ctx.mudar_necessidade("diversao", 1, (self.X_CENTRO, 390))

    def _montar_letreiro(self, ctx):
        partes = []
        try:
            for titulo, _, rec in ctx.trofeus():
                partes.append((f"{titulo}: {rec}" if rec else str(titulo)).upper())
        except (AttributeError, TypeError):
            pass
        self.letreiro = "   *   ".join(partes) if partes else t("JOGUE OS MINI JOGOS!")

    def clicar(self, pos, ctx):
        if not self.rect.collidepoint(pos):
            return False
        self.canal = (self.canal + 1) % len(self.CANAIS)
        self.troca = 1.5
        if self.canal == 4:
            self._montar_letreiro(ctx)
        ctx.som("clique")
        return True

    def dica(self, ctx):
        if self.canal == 0:
            return t("TV DESLIGADA")
        return t("CANAL {n}: {nome}", n=self.canal, nome=t(self.CANAIS[self.canal]))

    # ------------------ desenho -----------------------------

    def _desenhar_tela(self, tela, ctx):
        t = ctx.tempo
        s = self.TELA
        antigo = tela.get_clip()
        tela.set_clip(s.clip(antigo) if antigo else s)

        if self.canal == 0:
            tela.fill((28, 34, 40), s)
        elif self.canal == 1:
            self._canal_robert(tela, t)
        elif self.canal == 2:
            self._canal_desenho(tela, ctx, t)
        elif self.canal == 3:
            quadros = self._quadros_chuvisco()
            tela.blit(quadros[int(t * 20) % len(quadros)], s)
        else:
            self._canal_recordes(tela, ctx, t)

        if self.canal and self.troca > 0:
            tela.fill((10, 20, 10), (s.right - 42, s.y + 2, 40, 13))
            ui.desenhar_texto(tela, t("CH {n}", n=self.canal), (s.right - 5, s.y + 5), 8,
                              (120, 255, 140), "topright", sombra=False)
        _blit_sprite(tela, "tv_vidro", self.TELA, self._pintar_vidro)
        tela.set_clip(antigo)

    def _canal_robert(self, tela, t):
        s = self.TELA
        tela.fill((80, 140, 210), s)
        tela.fill((200, 60, 70), (s.x, s.y, 12, s.h))            # cortinas
        tela.fill((200, 60, 70), (s.right - 12, s.y, 12, s.h))
        tela.fill((60, 100, 160), (s.x, s.y + 64, s.w, 22))       # palco
        ui.desenhar_texto(tela, "ROBERT SHOW", (s.centerx, s.y + 5), 8, AMARELO, "midtop")
        # ROBERT: palito com boné arco-íris acenando
        cx, cy = s.x + 60, s.y + 36
        branco = (250, 250, 250)
        pygame.draw.circle(tela, branco, (cx, cy), 7, 2)
        for i, cor in enumerate(((255, 80, 80), (255, 220, 60), (90, 200, 255))):
            pygame.draw.arc(tela, cor, (cx - 9 + i * 2, cy - 11 + i * 2, 18 - i * 4, 14 - i * 4),
                            0, math.pi, 2)
        pygame.draw.line(tela, (255, 80, 80), (cx + 6, cy - 4), (cx + 13, cy - 4), 2)
        pygame.draw.line(tela, branco, (cx, cy + 7), (cx, cy + 24), 2)
        mao = (cx + 13, cy + 2 + 6 * math.sin(t * 10))
        pygame.draw.line(tela, branco, (cx, cy + 12), mao, 2)
        pygame.draw.line(tela, branco, (cx, cy + 12), (cx - 9, cy + 20), 2)
        pygame.draw.line(tela, branco, (cx, cy + 24), (cx - 6, cy + 34), 2)
        pygame.draw.line(tela, branco, (cx, cy + 24), (cx + 6, cy + 34), 2)
        # Letreiro rolando
        sup = ui.texto(t("OI OVO!   OI OVO!"), 8, BRANCO, sombra=False)
        tela.fill((20, 30, 60), (s.x, s.bottom - 13, s.w, 13))
        x = s.right - (t * 40) % (sup.get_width() + s.w)
        tela.blit(sup, (x, s.bottom - 11))

    def _canal_desenho(self, tela, ctx, t):
        s = self.TELA
        tela.fill((150, 210, 255), s)
        pygame.draw.circle(tela, (255, 220, 70), (s.right - 22, s.y + 16), 9)
        pygame.draw.ellipse(tela, (255, 255, 255), (s.x + 20 + (t * 8) % 60, s.y + 10, 30, 10))
        desloc = (t * 30) % 70
        for i in range(4):
            x = s.x - 30 + i * 70 - desloc
            pygame.draw.circle(tela, (90, 190, 90), (int(x), s.bottom + 18), 42)
            pygame.draw.circle(tela, (70, 160, 75), (int(x), s.bottom + 18), 42, 2)
        tela.fill((70, 150, 70), (s.x, s.bottom - 10, s.w, 10))
        pulo = abs(math.sin(t * 4)) * 16
        ctx.desenhar_ovo(tela, (s.x + 50, s.bottom - 24 - pulo), 24)

    def _canal_recordes(self, tela, ctx, t):
        s = self.TELA
        tela.fill((22, 20, 50), s)
        if not self.letreiro:
            self._montar_letreiro(ctx)
        for i in range(6):
            fase = (t * 1.5 + i * 0.37) % 1
            x = s.x + 10 + (i * 23) % (s.w - 20)
            y = s.y + 24 + (i * 37) % 50
            ui.estrela(tela, (x, y), int(1 + 3 * math.sin(fase * math.pi)), (255, 230, 120))
        ui.desenhar_texto(tela, "RECORDES", (s.centerx, s.y + 6), 8, AMARELO, "midtop")
        sup = ui.texto(self.letreiro, 10, BRANCO)
        x = s.right - (t * 45) % (sup.get_width() + s.w)
        tela.blit(sup, (x, s.centery + 4))

    def _desenhar_luz(self, tela):
        # Luz azulada que a TV joga no quarto escuro
        _blit_brilho(tela, self.TELA.center, 120, (140, 180, 255), 40)

    def desenhar(self, tela, ctx):
        _blit_sprite(tela, "tv", self.caixa, self._pintar)
        self._desenhar_tela(tela, ctx)
        led = (90, 230, 110) if self.canal else (200, 50, 50)
        pygame.draw.circle(tela, led, (412, 509), 2)

    def desenhar_brilho(self, tela, ctx):
        if not (self.canal and ctx.luz_apagada):
            return
        self._desenhar_luz(tela)
        self._desenhar_tela(tela, ctx)


# ============================================================
# AQUÁRIO
# ============================================================

class Aquario(Movel):

    caixa = (604, 432, 162, 164)
    TANQUE = pygame.Rect(615, 440, 140, 100)
    CORES = [(255, 140, 40), (255, 220, 60), (120, 200, 255)]
    _peixes_sup = {}

    def __init__(self, movel_id):
        super().__init__(movel_id)
        self.rect = pygame.Rect(610, 436, 150, 154)
        self.base_y = 590
        rnd = random.Random()
        self.peixes = []
        for i in range(len(self.CORES)):
            self.peixes.append(dict(x=640.0 + i * 38, y=470.0 + i * 15, y0=470.0 + i * 15,
                                    dir=1 if i % 2 == 0 else -1, vel=rnd.uniform(22, 34),
                                    cor=i, fase=rnd.uniform(0, 6), giro=-1.0))
        self.flocos = []          # [x, y, vida]
        self.bolhas = []          # [x, y, r]
        self.prox_bolha = 0.0
        self.recarga = 0.0

    @classmethod
    def _peixe(cls, cor_i, direita):
        chave = (cor_i, direita)
        s = cls._peixes_sup.get(chave)
        if s is None:
            cor = cls.CORES[cor_i]
            s = pygame.Surface((26, 14), pygame.SRCALPHA)
            cauda = [(1, 2), (10, 7), (1, 12)]
            pygame.draw.polygon(s, ui.escurecer(cor, 30), cauda)
            pygame.draw.polygon(s, ui.escurecer(cor, 90), cauda, 1)
            pygame.draw.ellipse(s, cor, (7, 2, 16, 10))
            pygame.draw.ellipse(s, ui.escurecer(cor, 90), (7, 2, 16, 10), 1)
            pygame.draw.polygon(s, ui.escurecer(cor, 40), [(13, 3), (17, 0), (18, 4)])
            pygame.draw.circle(s, BRANCO, (19, 6), 2)
            pygame.draw.circle(s, (20, 20, 20), (19, 6), 1)
            if not direita:
                s = pygame.transform.flip(s, True, False)
            s = _preparar(s)
            cls._peixes_sup[chave] = s
        return s

    @classmethod
    def _pintar_fundo(cls, s):
        _sombra_chao(s, (604, 580, 162, 14), 80)
        movel = pygame.Rect(610, 540, 150, 50)
        pygame.draw.rect(s, (90, 70, 60), movel)
        for x in (615, 687):
            pygame.draw.rect(s, (105, 83, 72), (x, 546, 68, 40))
            pygame.draw.rect(s, (55, 40, 32), (x, 546, 68, 40), 2)
        pygame.draw.circle(s, (230, 190, 90), (677, 566), 2)
        pygame.draw.circle(s, (230, 190, 90), (693, 566), 2)
        pygame.draw.rect(s, (55, 40, 32), movel, 2)
        t = cls.TANQUE
        pygame.draw.rect(s, (160, 220, 255, 60), (t.x, t.y, t.w, 12))
        pygame.draw.rect(s, (120, 200, 255, 110), (t.x, 452, t.w, t.bottom - 452))
        # Cascalho
        pygame.draw.rect(s, (230, 200, 140), (617, 522, 136, 16))
        rnd = random.Random(3)
        for _ in range(40):
            cor = rnd.choice(((200, 165, 110), (250, 230, 190), (180, 140, 100)))
            pygame.draw.circle(s, cor, (rnd.randint(619, 751), rnd.randint(524, 536)), 1)
        # Pedrinha e conchinha
        pygame.draw.ellipse(s, (150, 150, 160), (720, 514, 22, 12))
        pygame.draw.ellipse(s, (110, 110, 120), (720, 514, 22, 12), 1)
        pygame.draw.circle(s, (255, 200, 210), (636, 522), 5)

    @classmethod
    def _pintar_frente(cls, s):
        t = cls.TANQUE
        pygame.draw.line(s, (220, 245, 255), (t.x + 2, 452), (t.right - 3, 452), 2)
        pygame.draw.line(s, (255, 255, 255, 120), (t.x + 8, t.y + 16), (t.x + 8, t.y + 60), 3)
        pygame.draw.line(s, (255, 255, 255, 90), (t.x + 16, t.y + 16), (t.x + 16, t.y + 34), 2)
        pygame.draw.rect(s, (220, 240, 255), t, 3)
        pygame.draw.rect(s, (70, 70, 85), (t.x - 3, t.y - 4, t.w + 6, 6))

    def atualizar(self, dt, ctx):
        t = ctx.tempo
        self.recarga = max(0.0, self.recarga - dt)
        # Flocos de ração caindo
        for f in self.flocos:
            if f[1] < 519:
                f[1] += 16 * dt
            f[2] -= dt
        self.flocos = [f for f in self.flocos if f[2] > 0]

        for p in self.peixes:
            if p["giro"] >= 0:
                p["giro"] += dt
                if p["giro"] > 0.6:
                    p["giro"] = -1.0
            alvo = None
            if self.flocos:
                alvo = min(self.flocos, key=lambda f: abs(f[0] - p["x"]) + abs(f[1] - p["y"]))
            if alvo:
                dx, dy = alvo[0] - p["x"], alvo[1] - p["y"]
                dist = math.hypot(dx, dy)
                if dist < 6:
                    self.flocos.remove(alvo)
                else:
                    p["x"] += dx / dist * 55 * dt
                    p["y"] += dy / dist * 55 * dt
                    p["dir"] = 1 if dx > 0 else -1
            else:
                p["x"] += p["dir"] * p["vel"] * dt
                if p["x"] > 740:
                    p["dir"] = -1
                elif p["x"] < 630:
                    p["dir"] = 1
                ty = p["y0"] + 6 * math.sin(t * 1.1 + p["fase"])
                p["y"] += (ty - p["y"]) * min(1.0, dt * 3)
            p["x"] = max(630.0, min(740.0, p["x"]))
            p["y"] = max(462.0, min(512.0, p["y"]))

        # Bolhinhas
        self.prox_bolha -= dt
        if self.prox_bolha <= 0:
            self.prox_bolha = random.uniform(0.4, 0.9)
            self.bolhas.append([640.0, 518.0, random.choice((2, 2, 3))])
        for b in self.bolhas:
            b[1] -= 30 * dt
        self.bolhas = [b for b in self.bolhas if b[1] > 456]

    def desenhar(self, tela, ctx):
        t = ctx.tempo
        _blit_sprite(tela, "aquario_fundo", self.caixa, self._pintar_fundo)
        # Algas onduladas
        for bx, alt in ((660, 52), (705, 40)):
            ant = (bx, 524)
            for i in range(1, 7):
                y = 524 - alt * i / 6
                x = bx + math.sin(t * 2 + i * 0.8 + bx) * (1.5 + i * 0.9)
                pygame.draw.line(tela, (60, 170, 80), ant, (x, y), 4)
                ant = (x, y)
        for x, y, _ in self.flocos:
            pygame.draw.rect(tela, (220, 140, 70), (int(x), int(y), 3, 2))
        for p in self.peixes:
            s = self._peixe(p["cor"], p["dir"] > 0)
            if p["giro"] >= 0:
                s = pygame.transform.rotate(s, -p["dir"] * 360 * p["giro"] / 0.6)
            tela.blit(s, s.get_rect(center=(int(p["x"]), int(p["y"]))))
        for x, y, r in self.bolhas:
            pygame.draw.circle(tela, (235, 250, 255), (int(x + math.sin(y * 0.2) * 2), int(y)), r, 1)
        _blit_sprite(tela, "aquario_frente", self.caixa, self._pintar_frente)

    def clicar(self, pos, ctx):
        if not self.rect.collidepoint(pos):
            return False
        # Clique num peixe: cambalhota
        for p in self.peixes:
            if abs(pos[0] - p["x"]) < 15 and abs(pos[1] - p["y"]) < 11:
                if p["giro"] < 0:
                    p["giro"] = 0.0
                    ctx.som("pulo", 0.6)
                return True
        if self.TANQUE.collidepoint(pos):
            x0 = max(625, min(745, pos[0]))
            for _ in range(6):
                self.flocos.append([x0 + random.uniform(-14, 14), 452 + random.uniform(0, 5), 8.0])
            ctx.som("clique")
            if self.recarga <= 0:
                self.recarga = 30.0
                ctx.mudar_necessidade("diversao", 2, (685, 430))
        return True

    def dica(self, ctx):
        return t("DAR RAÇÃO AOS PEIXES")


# ============================================================
# CAMA
# ============================================================

class Cama(Movel):

    caixa = (774, 466, 244, 162)
    ocupavel = True
    X_DESTINO = 890
    ALTURA_OVO = 118

    def __init__(self, movel_id):
        super().__init__(movel_id)
        self.rect = pygame.Rect(780, 470, 234, 152)
        self.base_y = 622
        self.deitado = False
        self.tempo_deitado = 0.0

    @staticmethod
    def _pintar_ovinhos(s, rect):
        for i, x in enumerate(range(rect.x + 10, rect.right - 6, 20)):
            y = rect.y + (9 if i % 2 == 0 else 22)
            if rect.y < y < rect.bottom - 4:
                _ovinho(s, (x, y), 7, (250, 250, 255))

    @classmethod
    def _pintar(cls, s, com_cobertor):
        _sombra_chao(s, (774, 612, 244, 14), 80)
        # Cabeceira
        cab = pygame.Rect(1000, 470, 14, 140)
        pygame.draw.rect(s, (150, 100, 58), cab, border_top_left_radius=7,
                         border_top_right_radius=7)
        pygame.draw.rect(s, MADEIRA_ESCURA, cab, 2, border_top_left_radius=7,
                         border_top_right_radius=7)
        # Pés e estrado
        for x in (786, 998):
            pygame.draw.rect(s, (110, 70, 38), (x, 610, 10, 12))
            pygame.draw.rect(s, MADEIRA_ESCURA, (x, 610, 10, 12), 1)
        estrado = pygame.Rect(780, 570, 230, 40)
        pygame.draw.rect(s, (140, 90, 50), estrado, border_radius=4)
        pygame.draw.line(s, (165, 112, 68), (784, 575), (1005, 575), 2)
        pygame.draw.rect(s, MADEIRA_ESCURA, estrado, 2, border_radius=4)
        # Colchão
        colchao = pygame.Rect(784, 548, 222, 26)
        pygame.draw.rect(s, (245, 245, 250), colchao, border_radius=6)
        pygame.draw.rect(s, (200, 205, 215), colchao, 2, border_radius=6)
        # Travesseiro
        trav = pygame.Rect(930, 530, 66, 28)
        pygame.draw.ellipse(s, (255, 255, 255), trav)
        pygame.draw.ellipse(s, (200, 205, 215), trav, 2)
        pygame.draw.arc(s, (215, 220, 230), (944, 538, 38, 12), 0.3, 2.8, 1)
        if com_cobertor:
            cob = pygame.Rect(784, 552, 150, 34)
            pygame.draw.rect(s, (80, 140, 220), cob, border_radius=6)
            cls._pintar_ovinhos(s, cob.inflate(-16, 0))
            # Dobra (parte de cima do lençol virada)
            pygame.draw.rect(s, (130, 180, 240), (920, 552, 16, 34), border_radius=4)
            pygame.draw.rect(s, (50, 100, 180), cob, 2, border_radius=6)

    def _centro_ovo(self):
        # Deitado com a cabeça no travesseiro e o corpo afundado no colchão
        return (932, 522)

    @classmethod
    def _pintar_cobertor_alto(cls, s, cx, cy):
        # Lençol na frente do colchão (o ovo fica "dentro" da cama)
        lencol = pygame.Rect(784, 552, 222, 22)
        pygame.draw.rect(s, (250, 250, 255), lencol, border_radius=6)
        pygame.draw.line(s, (215, 220, 232), (790, 556), (1000, 556), 2)
        pygame.draw.rect(s, (200, 205, 215), lencol, 2, border_radius=6)
        # Cobertor puxado por cima da parte de baixo do ovo (lado dos pés)
        pontos = [(784, 588), (784, 552), (812, 546), (832, 540), (846, cy - 12),
                  (858, cy - 32), (872, cy - 40), (884, cy - 34), (889, cy - 12),
                  (891, 552), (893, 588)]
        pygame.draw.polygon(s, (80, 140, 220), pontos)
        for x, y in ((800, 568), (822, 556), (842, 574), (856, 548), (868, cy - 16),
                     (872, 568), (826, 578)):
            _ovinho(s, (x, y), 7, (250, 250, 255))
        # Dobra do lençol virada por cima do cobertor
        dobra = [(880, cy - 36), (890, cy - 32), (896, 588), (886, 588), (884, cy - 10)]
        pygame.draw.polygon(s, (130, 180, 240), dobra)
        pygame.draw.polygon(s, (50, 100, 180), dobra, 2)
        pygame.draw.polygon(s, (50, 100, 180), pontos, 2)

    def atualizar(self, dt, ctx):
        if not self._ocupado(ctx):
            self.deitado = False
        elif self.deitado:
            self.tempo_deitado += dt

    def desenhar(self, tela, ctx):
        cheio = not (self._ocupado(ctx) and self.deitado)
        _blit_sprite(tela, ("cama", cheio), self.caixa,
                     lambda s: self._pintar(s, cheio))

    def desenhar_ovo_ocupado(self, tela, ctx):
        if not self.deitado:
            return
        cx, cy = self._centro_ovo()
        resp = math.sin(ctx.tempo * 1.6) * 1.5
        ctx.desenhar_ovo(tela, (cx, cy - resp), self.ALTURA_OVO, angulo=-90, dormindo=True)

    def desenhar_frente(self, tela, ctx):
        if not (self._ocupado(ctx) and self.deitado):
            return
        cx, cy = self._centro_ovo()
        _blit_sprite(tela, "cama_cobertor", self.caixa,
                     lambda s: self._pintar_cobertor_alto(s, cx, cy))
        # Z z z saindo da cabeça
        for i in range(3):
            fase = (ctx.tempo * 0.5 + i / 3) % 1
            x = cx + 34 + fase * 22 + math.sin(fase * 6 + i) * 4
            y = cy - 50 - fase * 60
            sup = ui.texto("Z", 10 + i * 3, (220, 230, 255))
            if fase > 0.6:
                sup = sup.copy()
                sup.set_alpha(int(255 * (1 - fase) / 0.4))
            tela.blit(sup, sup.get_rect(center=(int(x), int(y))))

    def clicar(self, pos, ctx):
        if not self.rect.collidepoint(pos):
            return False
        ctx.som("clique")
        if self._ocupado(ctx):
            ctx.liberar_ovo()
        else:
            ctx.ocupar_ovo(self, self.X_DESTINO)
        return True

    def ovo_chegou(self, ctx):
        self.deitado = True
        self.tempo_deitado = 0.0
        ctx.som("pulo", 0.6)
        ctx.dormir()

    def dica(self, ctx):
        return t("DORMIR NA CAMA")


# ============================================================
# CATA-VENTO
# ============================================================

class CataVento(Movel):

    caixa = (580, 438, 64, 134)
    CENTRO = (612, 470)
    CORES = [(255, 80, 80), (255, 220, 60), (80, 180, 255), (120, 220, 90)]

    def __init__(self, movel_id):
        super().__init__(movel_id)
        self.rect = pygame.Rect(582, 440, 60, 130)
        self.base_y = 565
        self.angulo = 0.0
        self.sopro = 0.0

    @staticmethod
    def _pintar(s):
        pygame.draw.line(s, (200, 200, 200), (612, 470), (612, 565), 3)
        pygame.draw.line(s, (150, 150, 155), (613, 470), (613, 565), 1)
        for dx in (-6, -2, 3, 7):
            pygame.draw.line(s, (40, 170, 40), (612, 566), (612 + dx, 556), 2)

    def atualizar(self, dt, ctx):
        self.sopro = max(0.0, self.sopro - dt)
        vel = 90 + 270 * max(0.0, min(1.0, ctx.vento))
        if ctx.chovendo:
            vel = max(vel, 360)
        if self.sopro > 0:
            vel = max(vel, 900 * min(1.0, self.sopro))
        self.angulo = (self.angulo + vel * dt) % 360

    def desenhar(self, tela, ctx):
        _blit_sprite(tela, "cata_vento", self.caixa, self._pintar)
        cx, cy = self.CENTRO
        base = math.radians(self.angulo)
        for i, cor in enumerate(self.CORES):
            a = base + i * math.pi / 2
            ponta = (cx + math.cos(a) * 26, cy + math.sin(a) * 26)
            lado = (cx + math.cos(a + 1.2) * 15, cy + math.sin(a + 1.2) * 15)
            pygame.draw.polygon(tela, cor, [(cx, cy), ponta, lado])
            pygame.draw.polygon(tela, ui.escurecer(cor, 70), [(cx, cy), ponta, lado], 1)
            pygame.draw.line(tela, ui.clarear(cor, 60), (cx, cy), ponta, 1)
        pygame.draw.circle(tela, (240, 240, 240), (cx, cy), 4)
        pygame.draw.circle(tela, (120, 120, 130), (cx, cy), 4, 1)

    def clicar(self, pos, ctx):
        if not self.rect.collidepoint(pos):
            return False
        self.sopro = 2.0
        ctx.som("asa")
        return True


# ============================================================
# CASINHA DO PET
# ============================================================

class CasinhaPet(Movel):

    caixa = (14, 434, 132, 136)

    def __init__(self, movel_id):
        super().__init__(movel_id)
        self.rect = pygame.Rect(20, 440, 120, 120)
        self.base_y = 560
        self.balanco = 0.0

    @staticmethod
    def _pintar(s):
        _sombra_chao(s, (18, 552, 124, 14), 70)
        base = pygame.Rect(30, 480, 100, 80)
        pygame.draw.rect(s, (200, 70, 60), base)
        for y in range(492, 560, 12):
            pygame.draw.line(s, (170, 55, 48), (31, y), (128, y), 1)
        pygame.draw.rect(s, (110, 35, 30), base, 2)
        # Porta em arco (elipse cortada na base)
        porta = pygame.Surface((40, 60), pygame.SRCALPHA)
        pygame.draw.ellipse(porta, (50, 30, 25), porta.get_rect())
        s.blit(porta, (60, 505), pygame.Rect(0, 0, 40, 55))
        pygame.draw.arc(s, (110, 35, 30), (60, 505, 40, 60), 0, math.pi, 2)
        # Telhado
        telhado = [(20, 485), (80, 440), (140, 485)]
        pygame.draw.polygon(s, (120, 60, 40), telhado)
        for i in range(1, 4):
            y = 440 + i * 11
            meia = (y - 440) * 60 / 45
            pygame.draw.line(s, (95, 45, 30), (80 - meia + 3, y), (80 + meia - 3, y), 1)
        pygame.draw.polygon(s, (70, 32, 22), telhado, 2)
        # Tigelinha com osso
        pygame.draw.ellipse(s, (90, 140, 220), (112, 550, 24, 10))
        pygame.draw.ellipse(s, (50, 90, 170), (112, 550, 24, 10), 1)

    def _nome(self, ctx):
        pid = ctx.pet_id
        if not pid:
            return "PET"
        try:
            from core import pets
            return pets.CATALOGO[pid]["nome"]
        except (AttributeError, KeyError, ImportError):
            return str(pid).upper()

    def atualizar(self, dt, ctx):
        self.balanco = max(0.0, self.balanco - dt)

    def desenhar(self, tela, ctx):
        dy = int(-abs(math.sin(self.balanco * 20)) * 4) if self.balanco > 0 else 0
        _blit_sprite(tela, "casinha", self.caixa, self._pintar, (0, dy))
        # Plaquinha com o nome do pet
        placa = pygame.Rect(42, 487 + dy, 76, 14)
        pygame.draw.rect(tela, (240, 220, 170), placa, border_radius=3)
        pygame.draw.rect(tela, (110, 70, 40), placa, 1, border_radius=3)
        sup = ui.texto(self._nome(ctx), 8, (90, 50, 30), sombra=False)
        if sup.get_width() > placa.w - 6:
            sup = _encolher(sup, placa.w - 6)
        tela.blit(sup, sup.get_rect(center=placa.center))

    def clicar(self, pos, ctx):
        if not self.rect.collidepoint(pos):
            return False
        self.balanco = 0.3
        ctx.som("bater", 0.6)
        return True

    def dica(self, ctx):
        return t("CASINHA DO {nome}", nome=self._nome(ctx)) if ctx.pet_id else t("CASINHA DO PET")


_encolhidos = {}


def _encolher(sup, largura):
    chave = (id(sup), largura)
    s = _encolhidos.get(chave)
    if s is None:
        if len(_encolhidos) > 40:
            _encolhidos.clear()
        alt = max(1, int(sup.get_height() * largura / sup.get_width()))
        s = pygame.transform.smoothscale(sup.convert_alpha(), (largura, alt))
        _encolhidos[chave] = s
    return s


# ============================================================
# PISCINA INFLÁVEL
# ============================================================

class Piscina(Movel):

    caixa = (624, 552, 162, 66)
    ocupavel = True
    X_DESTINO = 705
    AGUA = pygame.Rect(638, 566, 134, 34)
    LINHA = 583                   # linha da água (meio da elipse)
    ALTURA_OVO = 112
    DURACAO = 10.0

    def __init__(self, movel_id):
        super().__init__(movel_id)
        self.rect = pygame.Rect(630, 556, 150, 54)
        self.base_y = 606
        self.dentro = False
        self.tempo_dentro = 0.0
        self.acumulado = 0.0

    @staticmethod
    def _pintar_borda(s):
        _sombra_chao(s, (626, 590, 158, 22), 60)
        pygame.draw.ellipse(s, (215, 80, 130), (630, 566, 150, 46))    # lateral (volume)
        pygame.draw.ellipse(s, (255, 120, 170), (630, 560, 150, 46), 8)
        pygame.draw.arc(s, (255, 190, 215), (634, 562, 142, 40), 0.4, 2.7, 2)
        pygame.draw.ellipse(s, (170, 50, 100), (630, 560, 150, 46), 1)

    def _desenhar_agua(self, tela, t):
        pygame.draw.ellipse(tela, (90, 190, 255), self.AGUA)
        for i in range(3):
            x = 652 + i * 36 + math.sin(t * 2 + i) * 6
            y = 575 + (i % 2) * 12
            pygame.draw.arc(tela, (170, 225, 255), (x, y, 22, 6), 0.2, 2.9, 2)

    def _desenhar_chuva(self, tela, t, ctx):
        if not ctx.chovendo:
            return
        for i in range(3):
            fase = (t * 1.3 + i * 0.33) % 1
            x = 650 + (i * 47 + int(t * 1.3 + i * 0.33) * 29) % 110
            y = 572 + (i * 11) % 22
            r = pygame.Rect(0, 0, int(4 + 18 * fase), int(2 + 6 * fase))
            r.center = (x, y)
            pygame.draw.ellipse(tela, (210, 240, 255), r, 1)

    def _patinho(self, tela, t, pos=None):
        x, y = pos or (700, 574)
        y += math.sin(t * 2.5) * 2
        pygame.draw.ellipse(tela, (255, 215, 40), (x - 10, y - 5, 20, 12))
        pygame.draw.circle(tela, (255, 215, 40), (int(x + 7), int(y - 7)), 6)
        pygame.draw.polygon(tela, (255, 130, 30), [(x + 12, y - 8), (x + 18, y - 6), (x + 12, y - 4)])
        pygame.draw.circle(tela, (20, 20, 20), (int(x + 8), int(y - 9)), 1)
        pygame.draw.ellipse(tela, (230, 180, 20), (x - 7, y - 3, 10, 6), 1)

    def atualizar(self, dt, ctx):
        if not self._ocupado(ctx):
            self.dentro = False
            return
        if not self.dentro:
            return
        self.tempo_dentro += dt
        self.acumulado += dt
        if self.acumulado >= 1.0:
            self.acumulado -= 1.0
            ctx.mudar_necessidade("higiene", 4, (self.X_DESTINO, 470))
            ctx.mudar_necessidade("diversao", 1)
            if random.random() < 0.5:
                ctx.particulas.explodir((self.X_DESTINO + random.uniform(-40, 40), self.LINHA),
                                        [(170, 225, 255), (255, 255, 255)], qtd=5, vel=140,
                                        vida=0.5, tamanho=(2, 4))
        if self.tempo_dentro >= self.DURACAO:
            ctx.liberar_ovo()

    def desenhar(self, tela, ctx):
        t = ctx.tempo
        _blit_sprite(tela, "piscina", self.caixa, self._pintar_borda)
        self._desenhar_agua(tela, t)
        self._desenhar_chuva(tela, t, ctx)
        if not (self._ocupado(ctx) and self.dentro):
            self._patinho(tela, t)

    def _centro_ovo(self, t):
        # Pulo para dentro (0.5 s) e depois boiando
        if self.tempo_dentro < 0.5:
            f = self.tempo_dentro / 0.5
            y0 = 610 - self.ALTURA_OVO / 2
            y1 = self.LINHA - self.ALTURA_OVO * 0.3
            return (self.X_DESTINO, y0 + (y1 - y0) * f - math.sin(f * math.pi) * 70)
        return (self.X_DESTINO, self.LINHA - self.ALTURA_OVO * 0.3 + math.sin(t * 2.2) * 2)

    def desenhar_ovo_ocupado(self, tela, ctx):
        if not self.dentro:
            return
        t = ctx.tempo
        cx, cy = self._centro_ovo(t)
        antigo = tela.get_clip()
        corte = pygame.Rect(0, 0, LARGURA, self.LINHA + 2)
        tela.set_clip(corte.clip(antigo) if antigo else corte)
        ang = math.sin(t * 1.7) * 4 if self.tempo_dentro >= 0.5 else 0
        ctx.desenhar_ovo(tela, (cx, cy), self.ALTURA_OVO, angulo=ang)
        tela.set_clip(antigo)

    def desenhar_frente(self, tela, ctx):
        if not (self._ocupado(ctx) and self.dentro):
            return
        t = ctx.tempo
        # Metade da frente da piscina (água + borda) por cima do ovo
        antigo = tela.get_clip()
        frente = pygame.Rect(600, self.LINHA, 200, 40)
        tela.set_clip(frente.clip(antigo) if antigo else frente)
        _blit_sprite(tela, "piscina", self.caixa, self._pintar_borda)
        self._desenhar_agua(tela, t)
        tela.set_clip(antigo)
        # Ondinhas em volta do ovo
        for i in range(2):
            fase = (t * 0.8 + i * 0.5) % 1
            r = pygame.Rect(0, 0, int(90 + 60 * fase), int(12 + 8 * fase))
            r.center = (self.X_DESTINO, self.LINHA + 2)
            pygame.draw.ellipse(tela, (200, 235, 255), r, 1)
        self._patinho(tela, t, (745, 588))

    def clicar(self, pos, ctx):
        if not self.rect.collidepoint(pos):
            return False
        ctx.som("clique")
        if self._ocupado(ctx):
            ctx.liberar_ovo()
        else:
            ctx.ocupar_ovo(self, self.X_DESTINO)
        return True

    def ovo_chegou(self, ctx):
        self.dentro = True
        self.tempo_dentro = 0.0
        self.acumulado = 0.0
        ctx.som("pulo")
        ctx.particulas.explodir((self.X_DESTINO, self.LINHA), [(170, 225, 255), (255, 255, 255),
                                (90, 190, 255)], qtd=22, vel=260, vida=0.7)

    def dica(self, ctx):
        return "TOMAR BANHO DE PISCINA"


# ============================================================
# VARAL DE LUZES
# ============================================================

class VaralLuzes(Movel):

    caixa = (140, 100, 880, 400)
    A = (150, 120)
    B = (1000, 160)
    FLECHA = 60
    CORES = [(255, 90, 90), (255, 220, 60), (90, 200, 255), (120, 230, 120)]

    def __init__(self, movel_id):
        super().__init__(movel_id)
        self.rect = pygame.Rect(150, 110, 850, 100)
        self.base_y = 440
        self.lampadas = []
        x = 175
        while x < 1000:
            self.lampadas.append((x, self._y(x) + 7))
            x += 50

    @classmethod
    def _y(cls, x):
        u = (x - cls.A[0]) / (cls.B[0] - cls.A[0])
        return cls.A[1] + (cls.B[1] - cls.A[1]) * u + cls.FLECHA * 4 * u * (1 - u)

    @classmethod
    def _pintar(cls, s, apagado=True):
        # Postes
        for x, topo, chao in ((150, 112, 462), (1000, 152, 496)):
            pygame.draw.line(s, (120, 85, 50), (x, topo), (x, chao), 5)
            pygame.draw.line(s, (80, 55, 30), (x + 2, topo), (x + 2, chao), 1)
            pygame.draw.circle(s, (90, 60, 35), (x, topo), 4)
        pontos = [(x, cls._y(x)) for x in range(150, 1001, 10)]
        pygame.draw.lines(s, (50, 60, 60), False, pontos, 2)
        x = 175
        i = 0
        while x < 1000:
            y = cls._y(x)
            pygame.draw.rect(s, (60, 70, 70), (x - 2, y, 5, 5))
            cor = cls.CORES[i % 4]
            if apagado:
                cor = ui.misturar(cor, (200, 200, 200), 0.35)
            pygame.draw.ellipse(s, cor, (x - 4, y + 4, 9, 12))
            pygame.draw.ellipse(s, ui.escurecer(cor, 80), (x - 4, y + 4, 9, 12), 1)
            x += 50
            i += 1

    def _desenhar_acesas(self, tela, ctx, halo=True):
        t = ctx.tempo
        for i, (x, y) in enumerate(self.lampadas):
            cor = self.CORES[i % 4]
            forca = 0.6 + 0.4 * math.sin(3 * t - i * 0.6)
            if halo:
                _blit_brilho(tela, (x, y + 3), 14, cor, int(60 * forca + 20))
            pygame.draw.ellipse(tela, ui.misturar(cor, (255, 255, 255), 0.5 * forca),
                                (x - 4, y - 3, 9, 12))

    # O desenho é cortado em 3 pedaços (fio + 2 postes) para não
    # copiar uma Surface enorme quase toda transparente a cada frame.
    PEDACOS = [("varal_fio", (144, 106, 862, 110)), ("varal_poste1", (144, 216, 14, 250)),
               ("varal_poste2", (994, 216, 14, 284))]

    def desenhar(self, tela, ctx):
        for chave, caixa in self.PEDACOS:
            _blit_sprite(tela, chave, caixa, self._pintar)
        if ctx.noite:
            self._desenhar_acesas(tela, ctx)

    def desenhar_brilho(self, tela, ctx):
        if ctx.noite:
            self._desenhar_acesas(tela, ctx)


# ============================================================
# TELESCÓPIO
# ============================================================
# (Mudado de lugar: no desenho original ele ficava bem em cima
# dos canteiros 3/4 e as plantas altas o cobriam.)

class Telescopio(Movel):

    caixa = (690, 386, 76, 94)
    CABECA = (720, 434)

    def __init__(self, movel_id):
        super().__init__(movel_id)
        self.rect = pygame.Rect(690, 388, 76, 88)
        self.base_y = 474
        self.aberto = False
        self.t_aberto = 0.0
        self.t_estrela = None     # quando a estrela cadente passa (s após abrir)
        self.estrela_ini = (0, 0)
        self.noite_premiada = None
        self.mensagem = 0.0
        self.botao = pygame.Rect(0, 0, 200, 56)
        self.botao.midbottom = (LARGURA // 2, ALTURA - 24)

    @property
    def modal(self):
        return self.aberto

    @classmethod
    def _pintar(cls, s):
        hx, hy = cls.CABECA
        for pe in ((698, 472), (742, 472), (722, 476)):
            pygame.draw.line(s, (90, 90, 100), (hx, hy), pe, 3)
        pygame.draw.circle(s, (70, 70, 80), (hx, hy), 5)
        # Tubo apontando para o céu (lado direito, onde fica a lua)
        a = math.radians(-28)
        eixo = (math.cos(a), math.sin(a))
        nrm = (-eixo[1], eixo[0])
        centro = (hx + 2, hy - 8)

        def p(d, w):
            return (centro[0] + eixo[0] * d + nrm[0] * w, centro[1] + eixo[1] * d + nrm[1] * w)

        tubo = [p(-24, -5), p(28, -9), p(28, 9), p(-24, 5)]
        pygame.draw.polygon(s, (60, 70, 110), tubo)
        pygame.draw.line(s, (100, 115, 170), p(-22, -3), p(26, -6), 2)
        pygame.draw.polygon(s, (30, 35, 60), tubo, 2)
        anel = [p(20, -9), p(24, -9), p(24, 9), p(20, 9)]
        pygame.draw.polygon(s, (230, 190, 80), anel)
        # Lente
        lente = [p(28, -9), p(31, -8), p(31, 8), p(28, 9)]
        pygame.draw.polygon(s, (240, 230, 120), lente)
        # Ocular
        pygame.draw.line(s, (40, 40, 50), p(-24, 0), p(-31, 0), 5)
        # Lunetinha de mira
        pygame.draw.line(s, (40, 45, 70), p(-4, -10), p(12, -12), 3)

    # ------------------ vista do céu ------------------------

    _ceu = None

    @classmethod
    def _fundo_ceu(cls):
        if cls._ceu is None:
            s = ui.gradiente(LARGURA, ALTURA, (8, 10, 40), (40, 30, 90))
            rnd = random.Random(11)
            for _ in range(170):
                c = rnd.randint(150, 255)
                pygame.draw.circle(s, (c, c, min(255, c + 20)),
                                   (rnd.randint(0, LARGURA), rnd.randint(0, ALTURA)),
                                   rnd.choice((1, 1, 1, 2)))
            # Constelação do OVO
            pts = cls._constelacao()
            for i in range(len(pts)):
                pygame.draw.line(s, (120, 140, 220), pts[i], pts[(i + 1) % len(pts)], 1)
            for x, y in pts:
                pygame.draw.circle(s, (255, 250, 220), (int(x), int(y)), 3)
            # Máscara redonda da lente
            mascara = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
            mascara.fill((0, 0, 0, 255))
            pygame.draw.circle(mascara, (0, 0, 0, 0), (LARGURA // 2, ALTURA // 2 - 10), 330)
            pygame.draw.circle(mascara, (40, 40, 60, 255), (LARGURA // 2, ALTURA // 2 - 10), 334, 6)
            s.blit(mascara, (0, 0))
            cls._ceu = s.convert() if pygame.display.get_surface() else s
        return cls._ceu

    @staticmethod
    def _constelacao():
        pts = []
        for i in range(12):
            a = i / 12 * math.tau
            sy = math.sin(a)
            x = 512 + math.cos(a) * 105 * (1 + 0.15 * sy)
            y = 330 + sy * 140
            pts.append((x, y))
        return pts

    @staticmethod
    def _chave_noite():
        agora = time.localtime(time.time() - 12 * 3600)
        return (agora.tm_year, agora.tm_yday)

    def _pos_estrela(self):
        if self.t_estrela is None:
            return None
        f = (self.t_aberto - self.t_estrela) / 1.6
        if not 0 <= f <= 1:
            return None
        x0, y0 = self.estrela_ini
        return (x0 + 360 * f, y0 + 200 * f), f

    def atualizar(self, dt, ctx):
        self.mensagem = max(0.0, self.mensagem - dt)
        if not self.aberto:
            return
        if not ctx.noite:
            self.aberto = False
            return
        self.t_aberto += dt

    def clicar(self, pos, ctx):
        if self.aberto:
            ret = self._pos_estrela()
            if ret and math.hypot(pos[0] - ret[0][0], pos[1] - ret[0][1]) < 45:
                self.t_estrela = None
                self.noite_premiada = self._chave_noite()
                self.mensagem = 2.5
                ctx.som("vencer")
                ctx.ganhar_moedas(15, pos)
                ctx.particulas.explodir(pos, [(255, 240, 150), (255, 255, 255), (150, 200, 255)],
                                        qtd=24, vel=260)
            elif self.botao.collidepoint(pos) or \
                    math.hypot(pos[0] - LARGURA // 2, pos[1] - (ALTURA // 2 - 10)) > 334:
                self.aberto = False
                ctx.som("voltar")
            return True

        if not self.rect.collidepoint(pos):
            return False
        if not ctx.noite:
            ctx.som("erro", 0.6)
            ctx.textos.adicionar(t("SÓ À NOITE!"), (self.CABECA[0], 380), BRANCO, 12)
            return True
        self.aberto = True
        self.t_aberto = 0.0
        ctx.som("selecionar")
        if self.noite_premiada != self._chave_noite():
            self.t_estrela = random.uniform(2.0, 16.0)
            self.estrela_ini = (random.uniform(260, 480), random.uniform(120, 220))
        else:
            self.t_estrela = None
        return True

    def desenhar(self, tela, ctx):
        _blit_sprite(tela, "telescopio", self.caixa, self._pintar)
        if ctx.noite and not self.aberto:
            # Brilhinho na lente chamando atenção
            f = (math.sin(ctx.tempo * 3) + 1) / 2
            ui.estrela(tela, (748, 408), int(2 + 3 * f), (255, 250, 200))

    def desenhar_sobreposicao(self, tela, ctx):
        if not self.aberto:
            return
        t = ctx.tempo
        tela.blit(self._fundo_ceu(), (0, 0))
        for i, (x, y) in enumerate(self._constelacao()):
            if i % 3 == int(t * 2) % 3:
                _blit_brilho(tela, (x, y), 10, (255, 250, 200), 90)
        ui.desenhar_texto(tela, t("CONSTELAÇÃO DO OVO"), (LARGURA // 2, 44), 16, AMARELO, "midtop")

        ret = self._pos_estrela()
        if ret:
            (x, y), _ = ret
            for k in range(10, 0, -1):
                tx = x - k * 12
                ty = y - k * 12 * 200 / 360
                cor = ui.misturar((255, 250, 200), (40, 40, 100), k / 10)
                pygame.draw.line(tela, cor, (tx, ty), (tx + 12, ty + 12 * 200 / 360),
                                 max(1, 6 - k // 2))
            _blit_brilho(tela, (x, y), 30, (255, 250, 200), 110)
            ui.estrela(tela, (int(x), int(y)), 11, (255, 250, 190), t * 5)
        elif self.noite_premiada != self._chave_noite() and self.t_estrela is not None \
                and self.t_aberto < self.t_estrela:
            ui.desenhar_texto(tela, t("Espere uma estrela cadente..."), (LARGURA // 2, 612), 12,
                              (200, 210, 255), "center")

        if self.mensagem > 0:
            ui.desenhar_texto(tela, t("DESEJO REALIZADO!"), (LARGURA // 2, 150), 24, AMARELO, "center")
            ui.desenhar_texto(tela, t("+15 OVOEDAS"), (LARGURA // 2, 190), 16, BRANCO, "center")

        mouse = pygame.mouse.get_pos()
        hover = self.botao.collidepoint(mouse)
        ui.painel(tela, self.botao, (70, 80, 130) if hover else (30, 36, 60), BRANCO, 14, 3)
        ui.desenhar_texto(tela, t("VOLTAR"), self.botao.center, 16, AMARELO if hover else BRANCO,
                          "center")

    def dica(self, ctx):
        return t("OLHAR AS ESTRELAS") if ctx.noite else t("TELESCÓPIO: SÓ À NOITE")


# ============================================================
# ÁRVORE COM BALANÇO
# ============================================================

class Balanco(Movel):

    caixa = (756, 132, 268, 480)
    ocupavel = True
    PIVO = (825, 338)
    X_DESTINO = 825
    ALTURA_OVO = 120
    COPA = [((835, 260), 70), ((905, 225), 85), ((965, 270), 65), ((890, 300), 60)]

    def __init__(self, movel_id):
        super().__init__(movel_id)
        self.rect = pygame.Rect(776, 330, 140, 272)
        self.base_y = 600
        self.sentado = False
        self.tempo_sentado = 0.0
        self.diversao = 0.0

    @staticmethod
    def _pintar_tronco(s):
        _sombra_chao(s, (840, 590, 110, 18), 70)
        tronco = [(870, 600), (910, 600), (902, 330), (878, 330)]
        pygame.draw.polygon(s, (120, 80, 40), tronco)
        for x0, y0, y1 in ((882, 360, 420), (896, 440, 520), (884, 500, 570), (893, 380, 400)):
            pygame.draw.line(s, (95, 60, 30), (x0, y0), (x0 + 2, y1), 2)
        # Raízes
        pygame.draw.polygon(s, (120, 80, 40), [(862, 602), (874, 580), (878, 602)])
        pygame.draw.polygon(s, (120, 80, 40), [(902, 602), (906, 580), (920, 602)])
        pygame.draw.polygon(s, (80, 50, 25), tronco, 2)
        # Galho
        pygame.draw.polygon(s, (120, 80, 40), [(880, 333), (790, 326), (790, 339), (880, 347)])
        pygame.draw.polygon(s, (80, 50, 25), [(880, 333), (790, 326), (790, 339), (880, 347)], 2)

    @classmethod
    def _pintar_copa(cls, s):
        for (x, y), r in cls.COPA:
            pygame.draw.circle(s, (35, 115, 45), (x, y), r + 3)
        for (x, y), r in cls.COPA:
            pygame.draw.circle(s, (60, 170, 60), (x, y), r)
        for (x, y), r in cls.COPA:
            pygame.draw.circle(s, (90, 200, 80), (x - r // 4, y - r // 4), int(r * 0.55))
        rnd = random.Random(5)
        for _ in range(26):
            (x, y), r = rnd.choice(cls.COPA)
            a = rnd.uniform(0, math.tau)
            d = rnd.uniform(0, r * 0.8)
            pygame.draw.circle(s, (120, 215, 100), (int(x + math.cos(a) * d),
                                                    int(y + math.sin(a) * d)), 4)
        # Maçãzinhas
        for x, y in ((850, 300), (930, 250), (975, 290), (880, 200)):
            pygame.draw.circle(s, (220, 60, 60), (x, y), 6)
            pygame.draw.circle(s, (255, 150, 150), (x - 2, y - 2), 2)

    def _angulo(self, ctx):
        if self._ocupado(ctx) and self.sentado:
            return math.radians(22) * math.sin(2.2 * ctx.tempo)
        return math.radians(3) * math.sin(1.3 * ctx.tempo) * (0.3 + ctx.vento)

    def _assento(self, ang):
        pts = [(788, 516), (862, 516), (862, 526), (788, 526)]
        return [_girar(p, self.PIVO, ang) for p in pts]

    def atualizar(self, dt, ctx):
        if not self._ocupado(ctx):
            self.sentado = False
            return
        if self.sentado:
            self.tempo_sentado += dt
            self.diversao += dt
            if self.diversao >= 5:
                self.diversao = 0.0
                ctx.mudar_necessidade("diversao", 1, (self.X_DESTINO, 380))

    def desenhar(self, tela, ctx):
        _blit_sprite(tela, "balanco_tronco", (782, 318, 172, 296), self._pintar_tronco)
        ang = self._angulo(ctx)
        for x in (797, 853):
            topo = _girar((x, 338), self.PIVO, ang)
            fim = _girar((x, 516), self.PIVO, ang)
            pygame.draw.line(tela, (225, 205, 160), topo, fim, 3)
            pygame.draw.line(tela, (150, 125, 80), (topo[0] + 1, topo[1]), (fim[0] + 1, fim[1]), 1)
        self._desenhar_assento(tela, ang)
        _blit_sprite(tela, "balanco_copa", (756, 132, 268, 236), self._pintar_copa)

    def _desenhar_assento(self, tela, ang):
        pts = self._assento(ang)
        pygame.draw.polygon(tela, (160, 110, 60), pts)
        pygame.draw.polygon(tela, (90, 55, 25), pts, 2)

    def desenhar_ovo_ocupado(self, tela, ctx):
        if not self.sentado:
            return
        ang = self._angulo(ctx)
        # Subindo no assento (0.35 s) e depois balançando junto
        dist = 516 - self.PIVO[1] - self.ALTURA_OVO / 2 + 6
        cx, cy = _girar((self.PIVO[0], self.PIVO[1] + dist), self.PIVO, ang)
        if self.tempo_sentado < 0.35:
            f = self.tempo_sentado / 0.35
            y0 = 610 - 75
            cy = y0 + (cy - y0) * f - math.sin(f * math.pi) * 30
        ctx.desenhar_ovo(tela, (cx, cy), self.ALTURA_OVO, angulo=math.degrees(-ang))

    def desenhar_frente(self, tela, ctx):
        if self._ocupado(ctx) and self.sentado:
            self._desenhar_assento(tela, self._angulo(ctx))

    def clicar(self, pos, ctx):
        if not self.rect.collidepoint(pos):
            return False
        ctx.som("clique")
        if self._ocupado(ctx):
            ctx.liberar_ovo()
        else:
            ctx.ocupar_ovo(self, self.X_DESTINO)
        return True

    def ovo_chegou(self, ctx):
        self.sentado = True
        self.tempo_sentado = 0.0
        self.diversao = 0.0
        ctx.som("pulo", 0.7)

    def dica(self, ctx):
        return t("BALANÇAR")


# ============================================================
# FÁBRICA
# ============================================================

_CLASSES = {
    "geladeira": Geladeira,
    "interruptor": Interruptor,
    "tapete": Tapete,
    "planta": Planta,
    "lampada_lava": LampadaLava,
    "retrato": Retrato,
    "relogio_cuco": RelogioCuco,
    "vitrola": Vitrola,
    "estante_trofeus": EstanteTrofeus,
    "tv": Televisao,
    "aquario": Aquario,
    "cama": Cama,
    "cata_vento": CataVento,
    "casinha_pet": CasinhaPet,
    "piscina": Piscina,
    "varal_luzes": VaralLuzes,
    "telescopio": Telescopio,
    "balanco": Balanco,
}


def criar(movel_id):
    """Instancia o móvel certo (canteiros viram um Movel vazio)."""
    return _CLASSES.get(movel_id, Movel)(movel_id)


# ============================================================
# ÍCONES DA LOJA
# ============================================================

class _CtxIcone:
    """Contexto mínimo para desenhar um móvel parado no ícone."""
    app = None
    tempo = 0.6
    comodo = "CASA"
    noite = False
    fase_dia = "dia"
    luz_apagada = False
    chovendo = False
    vento = 0.0
    ovo_x = -999
    ovo_chao = 640
    ovo_ocupado = None
    pet_id = ""
    jukebox_tocando = False

    @staticmethod
    def hora_real():
        return (10, 10)

    @staticmethod
    def trofeus():
        return [("", "ouro", ""), ("", "ouro", ""), ("", "prata", ""), ("", "bronze", ""),
                ("", "prata", ""), ("", "bronze", ""), ("", "ouro", ""), ("", "bronze", ""),
                ("", "ouro", ""), ("", "prata", ""), ("", "bronze", "")]

    @staticmethod
    def desenhar_ovo(tela, centro, altura, angulo=0, dormindo=False, espelhar=False):
        img = assets.OVOS[1] if assets.OVOS else None
        if img is None:
            r = pygame.Rect(0, 0, int(altura * 0.9), altura)
            r.center = (int(centro[0]), int(centro[1]))
            pygame.draw.ellipse(tela, (120, 200, 255), r)
            return
        lado = max(1, round(100 * altura / 74))
        sup = pygame.transform.smoothscale(img, (lado, lado))
        if angulo:
            sup = pygame.transform.rotate(sup, angulo)
        esc = lado / 100
        tela.blit(sup, sup.get_rect(center=(round(centro[0] + 1.5 * esc),
                                            round(centro[1] + 1 * esc))))

    def __getattr__(self, nome):
        # Qualquer outra chamada (som, textos...) vira "não faz nada"
        return lambda *a, **k: None


_icones = {}
_tela_icone = None


def _rascunho_icone():
    """Surface própria para os ícones (a de rascunho é usada pelos
    sprites estáticos que são criados durante o desenho)."""
    global _tela_icone
    if _tela_icone is None:
        _tela_icone = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
    _tela_icone.fill((0, 0, 0, 0))
    return _tela_icone


def _pintar_canteiro_icone(s, numero):
    r = pygame.Rect(412, 320, 200, 80)
    pygame.draw.rect(s, (170, 120, 70), r, border_radius=6)
    pygame.draw.rect(s, (120, 80, 45), r.inflate(-12, -12), border_radius=4)
    for x in range(r.x + 20, r.right - 10, 24):
        pygame.draw.line(s, (95, 60, 30), (x, r.y + 12), (x, r.bottom - 12), 3)
    pygame.draw.rect(s, (110, 75, 40), r, 3, border_radius=6)
    for x in (462, 512, 562):
        pygame.draw.line(s, (60, 150, 60), (x, 346), (x, 326), 4)
        pygame.draw.ellipse(s, (90, 190, 80), (x - 16, 312, 16, 10))
        pygame.draw.ellipse(s, (90, 190, 80), (x, 308, 16, 10))
    sup = ui.texto(f"+{numero}", 28, AMARELO)
    s.blit(sup, sup.get_rect(center=(512, 270)))


def _pintar_varal_icone(s):
    pts = [(400 + i * 5, 300 + 36 * 4 * (i / 44) * (1 - i / 44)) for i in range(45)]
    for x, y in (pts[0], pts[-1]):
        pygame.draw.line(s, (120, 85, 50), (x, y - 6), (x, y + 70), 5)
    pygame.draw.lines(s, (50, 60, 60), False, pts, 3)
    for i in range(1, 6):
        x, y = pts[i * 7 + 1]
        cor = VaralLuzes.CORES[i % 4]
        pygame.draw.circle(s, ui.misturar(cor, BRANCO, 0.6), (x, y + 16), 14)
        pygame.draw.rect(s, (60, 70, 70), (x - 3, y, 7, 7))
        pygame.draw.ellipse(s, ui.misturar(cor, BRANCO, 0.3), (x - 7, y + 6, 15, 20))
        pygame.draw.ellipse(s, ui.escurecer(cor, 80), (x - 7, y + 6, 15, 20), 1)


def icone(movel_id, tamanho):
    """Surface `tamanho` x `tamanho` com o móvel bem enquadrado."""
    chave = (movel_id, tamanho)
    s = _icones.get(chave)
    if s is not None:
        return s

    rasc = _rascunho_icone()
    if movel_id.startswith("canteiro_"):
        _pintar_canteiro_icone(rasc, movel_id[-1])
        caixa = pygame.Rect(400, 240, 224, 170)
    elif movel_id == "varal_luzes":
        _pintar_varal_icone(rasc)
        caixa = pygame.Rect(390, 280, 240, 110)
    else:
        m = criar(movel_id)
        ctx = _CtxIcone()
        ctx.comodo = m.comodo
        if movel_id == "tv":
            m.canal = 2
        m.atualizar(0.0, ctx)
        m.desenhar(rasc, ctx)
        m.desenhar_brilho(rasc, ctx)
        m.desenhar_frente(rasc, ctx)
        caixa = pygame.Rect(m.caixa)
        caixa = caixa.clip(rasc.get_rect())

    recorte = rasc.subsurface(caixa)
    margem = max(2, tamanho // 12)
    util = tamanho - 2 * margem
    esc = min(util / caixa.w, util / caixa.h)
    w, h = max(1, int(caixa.w * esc)), max(1, int(caixa.h * esc))
    img = pygame.transform.smoothscale(recorte, (w, h))
    s = pygame.Surface((tamanho, tamanho), pygame.SRCALPHA)
    s.blit(img, img.get_rect(center=(tamanho // 2, tamanho // 2)))
    s = _preparar(s)
    if len(_icones) > 200:
        _icones.clear()
    _icones[chave] = s
    return s


# Coleção nova (registra-se no CATALOGO e em _CLASSES)
from core import moveis_novos  # noqa: E402,F401
