import math
import random

import pygame

from settings import *
from core import ui
from jogos.base import MiniJogo

# ============================================================
# SALTO NO LAGO
# ============================================================
# Uma manhã no lago. O seu ovo pula de vitória-régia em
# vitória-régia: SEGURE para carregar (o ovo vai achatando como
# uma mola) e SOLTE para saltar. Cair bem no meio da folha é
# PERFEITO e vale mais! Cair na água acaba a partida (a não ser
# que você tenha uma BOIA).
#
#   folha normal   -> 110 px
#   folha pequena  -> 70 px (depois de 20 saltos)
#   folha móvel    -> vai e volta
#   folha seca     -> afunda 1.2 s depois que você pisa
#   tartaruga      -> mergulha a cada 3 s
#   flor-mola      -> joga você sozinha para a próxima folha (+3)

# Cenário (coordenadas da tela)
Y_MARGEM = 330                  # margem do fundo (começo da água)
Y_FOLHA = 540                   # superfície das folhas (onde o ovo pisa)
X_OVO = 260                     # posição do ovo na tela

# Ovo
ALTURA_OVO = 70
from core.jogador import BOCA_ABERTA as BOCA_SUSTO  # boca "O" (susto na água)

# Salto
TEMPO_CARGA = 0.9               # segundos para a força ir de 0 a 1
TEMPO_ARCO = 0.55
ALCANCE_MIN = 60
ALCANCE_VAR = 380
ALCANCE_MAX = ALCANCE_MIN + ALCANCE_VAR
DIST_MAX = 0.9 * ALCANCE_MAX    # nunca gerar folha mais longe que isso
RAIO_PERFEITO = 12

# Folhas
LARG_NORMAL = 110
LARG_PEQUENA = 70
AMPLITUDE_MOVEL = 60
FREQ_MOVEL = 0.6
TEMPO_AFUNDA = 1.2
CICLO_TARTARUGA = 3.0
MERGULHO = 1.0

TECLAS_PULO = (pygame.K_SPACE, pygame.K_UP, pygame.K_w, pygame.K_RETURN, pygame.K_KP_ENTER)

# Cores
AGUA = (60, 170, 200)
AGUA_CLARA = (110, 210, 230)
FOLHA = (70, 180, 80)
FOLHA_BORDA = (50, 140, 60)
LOTUS = (255, 150, 190)


def _altura_arco(p):
    return 90 + 60 * p


def _alcance(p):
    return ALCANCE_MIN + ALCANCE_VAR * p


def _forca_para(dist):
    """Força (0..1) que faz o ovo andar `dist` pixels."""
    return max(0.0, min(1.0, (dist - ALCANCE_MIN) / ALCANCE_VAR))


# ============================================================
# DESENHOS (com cache)
# ============================================================

_cache = {}


def _folha_sup(largura, tipo, flor):
    """Vitória-régia vista de lado (elipse achatada com a cunha)."""
    chave = ("folha", largura, tipo, flor)
    s = _cache.get(chave)
    if s is not None:
        return s

    alt = max(20, int(largura * 0.28))
    s = pygame.Surface((largura + 8, alt + 40), pygame.SRCALPHA)
    r = pygame.Rect(4, 36, largura, alt)

    if tipo == "afunda":
        cor, borda = (170, 170, 70), (120, 110, 40)        # folha seca
    else:
        cor, borda = FOLHA, FOLHA_BORDA

    pygame.draw.ellipse(s, ui.escurecer(borda, 30), r.move(0, 3))
    pygame.draw.ellipse(s, borda, r)
    pygame.draw.ellipse(s, cor, r.inflate(-6, -6))
    # Nervuras
    for i in range(-2, 3):
        pygame.draw.line(s, ui.clarear(cor, 25), r.center,
                         (r.centerx + i * largura // 6, r.y + 5 if i % 2 else r.bottom - 5), 2)
    # Cunha recortada (cor da água)
    pygame.draw.polygon(s, AGUA, [(r.centerx, r.centery), (r.centerx + largura // 5, r.bottom + 1),
                                  (r.centerx - largura // 12, r.bottom + 1)])
    if tipo == "afunda":
        # Rachaduras
        for dx in (-largura // 4, largura // 5):
            pygame.draw.lines(s, borda, False, [(r.centerx + dx, r.y + 4),
                                                (r.centerx + dx + 5, r.centery),
                                                (r.centerx + dx - 3, r.bottom - 5)], 2)
    if flor:
        cx = r.x + largura // 4
        cy = r.centery - 2
        for ang in range(0, 360, 60):
            a = math.radians(ang)
            pygame.draw.ellipse(s, LOTUS, (cx + math.cos(a) * 6 - 5, cy - 8 + math.sin(a) * 3 - 4, 10, 12))
        pygame.draw.circle(s, (255, 230, 120), (cx, cy - 8), 4)
    _cache[chave] = s
    return s


def _flor_mola_sup():
    """Flor grande em cima de uma mola (fica no meio da folha)."""
    s = _cache.get("mola")
    if s is not None:
        return s
    s = pygame.Surface((70, 60), pygame.SRCALPHA)
    cx = 35
    # Mola
    for i in range(4):
        y = 56 - i * 7
        pygame.draw.ellipse(s, (120, 120, 140), (cx - 11, y - 4, 22, 8), 3)
    # Pétalas
    for ang in range(0, 360, 45):
        a = math.radians(ang)
        pygame.draw.circle(s, (230, 90, 150), (int(cx + math.cos(a) * 14), int(22 + math.sin(a) * 9)), 9)
    for ang in range(22, 382, 45):
        a = math.radians(ang)
        pygame.draw.circle(s, LOTUS, (int(cx + math.cos(a) * 11), int(20 + math.sin(a) * 7)), 7)
    pygame.draw.circle(s, (255, 220, 80), (cx, 20), 7)
    pygame.draw.circle(s, (230, 170, 40), (cx, 20), 7, 2)
    _cache["mola"] = s
    return s


def _tartaruga_sup(largura):
    chave = ("tartaruga", largura)
    s = _cache.get(chave)
    if s is not None:
        return s
    alt = int(largura * 0.5)
    s = pygame.Surface((largura + 40, alt + 20), pygame.SRCALPHA)
    casco = pygame.Rect(20, 8, largura, alt)
    # Cabeça e patas
    pygame.draw.ellipse(s, (110, 170, 80), (casco.right - 12, casco.bottom - 30, 32, 24))
    pygame.draw.circle(s, (20, 20, 20), (casco.right + 12, casco.bottom - 22), 3)
    for dx in (14, largura - 30):
        pygame.draw.ellipse(s, (110, 170, 80), (casco.x + dx, casco.bottom - 12, 18, 12))
    # Casco (meia elipse)
    pygame.draw.ellipse(s, (70, 90, 40), casco)
    pygame.draw.ellipse(s, (120, 140, 60), casco.inflate(-8, -8))
    for i in range(3):
        hx = casco.x + largura // 4 + i * largura // 4
        pygame.draw.polygon(s, (90, 110, 45), [(hx - 12, casco.centery), (hx, casco.y + 10),
                                               (hx + 12, casco.centery), (hx, casco.bottom - 10)], 3)
    # Corta a metade de baixo (fica dentro da água)
    pygame.draw.rect(s, (0, 0, 0, 0), (0, casco.centery + 4, s.get_width(), s.get_height()))
    _cache[chave] = s
    return s


def _boia_sup(raio=18):
    chave = ("boia", raio)
    s = _cache.get(chave)
    if s is not None:
        return s
    d = raio * 2 + 4
    s = pygame.Surface((d, d), pygame.SRCALPHA)
    c = (d // 2, d // 2)
    pygame.draw.circle(s, (240, 60, 60), c, raio)
    for i in range(4):
        a1 = i * math.pi / 2
        pygame.draw.arc(s, BRANCO, (2, 2, raio * 2, raio * 2), a1, a1 + math.pi / 4, max(3, raio // 2))
    pygame.draw.circle(s, (0, 0, 0, 0), c, raio // 2)
    pygame.draw.circle(s, (150, 30, 30), c, raio, 2)
    pygame.draw.circle(s, (150, 30, 30), c, raio // 2, 2)
    _cache[chave] = s
    return s


def _morros(cor, altura_base, amp, seed, alt_total=200):
    """Faixa de morros que se repete sem emenda a cada LARGURA px."""
    s = pygame.Surface((LARGURA, alt_total), pygame.SRCALPHA)
    rnd = random.Random(seed)
    fases = [rnd.uniform(0, math.tau) for _ in range(3)]
    pontos = [(0, alt_total)]
    for x in range(0, LARGURA + 1, 8):
        a = x / LARGURA * math.tau
        y = (altura_base
             - amp * (0.55 * math.sin(a * 2 + fases[0]) + 0.3 * math.sin(a * 3 + fases[1])
                      + 0.15 * math.sin(a * 7 + fases[2])))
        pontos.append((x, y))
    pontos.append((LARGURA, alt_total))
    pygame.draw.polygon(s, cor, pontos)
    return s


def _recortar(sup, y_tela, y_fim):
    """Corta a parte transparente de cima e o que fica escondido embaixo."""
    topo = sup.get_bounding_rect().top
    fundo = max(topo + 1, min(sup.get_height(), y_fim - y_tela))
    return sup.subsurface((0, topo, sup.get_width(), fundo - topo)).copy(), y_tela + topo


def _camadas():
    """Camadas do cenário que andam com a câmera (parallax)."""
    if "camadas" in _cache:
        return _cache["camadas"]
    c = {}
    y_margem = Y_MARGEM - 36
    visivel = y_margem + 16          # a margem cobre os morros daqui para baixo
    c["longe"] = _recortar(_morros((120, 180, 120), 120, 40, 3), Y_MARGEM - 180, visivel)
    c["perto"] = _recortar(_morros((100, 160, 110), 150, 32, 9), Y_MARGEM - 170, visivel)

    # Margem do fundo com juncos e taboas
    m = pygame.Surface((LARGURA, 60), pygame.SRCALPHA)
    pygame.draw.rect(m, (90, 150, 70), (0, 16, LARGURA, 44))
    pygame.draw.rect(m, (70, 125, 60), (0, 40, LARGURA, 20))
    rnd = random.Random(5)
    for _ in range(90):
        x = rnd.randrange(LARGURA)
        h = rnd.randint(14, 34)
        pygame.draw.line(m, (60, 120, 50), (x, 36), (x + rnd.randint(-4, 4), 36 - h), 2)
        if rnd.random() < 0.25:
            pygame.draw.rect(m, (120, 80, 40), (x - 2, 36 - h, 5, 11), border_radius=2)
    c["margem"] = (m, y_margem)

    # Água: degradê parado (vai no fundo) + listras claras que deslizam
    alt = ALTURA - Y_MARGEM
    a = pygame.Surface((LARGURA, alt))
    for y in range(alt):
        a.fill(ui.misturar((90, 190, 215), (40, 140, 180), y / alt), (0, y, LARGURA, 1))
    c["agua"] = a
    rnd = random.Random(12)
    listras = []
    for _ in range(70):
        y = rnd.randrange(10, alt)
        w = int(rnd.randint(30, 110) * (0.5 + y / alt))
        listras.append((rnd.randrange(LARGURA), Y_MARGEM + y, w, 2 if y < alt / 2 else 3))
    c["listras"] = listras

    # Juncos da frente (4 moitas pequenas, para desenhar rápido)
    rnd = random.Random(33)
    juncos = []
    for grupo in range(4):
        j = pygame.Surface((100, 120), pygame.SRCALPHA)
        for _ in range(9):
            x = 50 + rnd.randint(-30, 30)
            h = rnd.randint(50, 110)
            pygame.draw.line(j, (50, 105, 45), (x, 120), (x + rnd.randint(-10, 10), 120 - h), 4)
            if rnd.random() < 0.4:
                pygame.draw.rect(j, (120, 80, 40), (x - 4, 120 - h, 9, 22), border_radius=4)
        juncos.append((j, grupo * 256 + rnd.randint(0, 60)))
    c["juncos"] = juncos

    # Formato da tela: blits bem mais rápidos
    try:
        for nome in ("longe", "perto", "margem"):
            sup, y = c[nome]
            c[nome] = (sup.convert_alpha(), y)
        c["juncos"] = [(sup.convert_alpha(), x) for sup, x in juncos]
        c["agua"] = a.convert()
    except pygame.error:
        pass
    _cache["camadas"] = c
    return c


# ============================================================
# FOLHA
# ============================================================

class Folha:

    def __init__(self, x, tipo="normal", flor=False):
        self.base = x
        self.tipo = tipo
        self.largura = LARG_PEQUENA if tipo == "pequena" else LARG_NORMAL
        self.flor = flor
        self.fase = random.uniform(0, math.tau)
        self.pisada = None          # relógio em que o ovo pisou (folha seca)
        self.afundou = False
        self.boia = False
        self.visitada = False
        self.balanco = 0.0          # afundadinha quando o ovo cai em cima

    @property
    def amplitude(self):
        return AMPLITUDE_MOVEL if self.tipo == "movel" else 0.0

    def x(self, t):
        if self.tipo == "movel":
            return self.base + AMPLITUDE_MOVEL * math.sin(math.tau * FREQ_MOVEL * t + self.fase)
        return self.base

    def ciclo(self, t):
        """Tartaruga: posição no ciclo (0..3). Mergulhada no último segundo."""
        return (t + self.fase) % CICLO_TARTARUGA

    def submersa(self, t):
        if self.tipo == "tartaruga":
            return self.ciclo(t) >= CICLO_TARTARUGA - MERGULHO
        return self.afundou

    def afundando(self, t):
        """0..1: quanto a folha já desceu (para o desenho)."""
        if self.tipo == "afunda" and self.pisada is not None:
            return min(1.0, (t - self.pisada) / TEMPO_AFUNDA)
        return 0.0


# ============================================================
# JOGO
# ============================================================

class SaltoLago(MiniJogo):

    ID = "salto_lago"
    TITULO = "SALTO NO LAGO"
    TITULO_CURTO = "LAGO"
    DESCRICAO = "Segure para carregar e solte para pular de vitória-régia em vitória-régia. Acerte o centro!"
    COR = (60, 170, 200)
    INSTRUCOES = [
        "SEGURE para carregar o pulo e SOLTE para saltar!",
        "Cair no meio da folha é PERFEITO (+2 e combo).",
        "Cuidado: folha seca afunda e a tartaruga mergulha.",
        "A BOIA salva você de uma queda na água.",
        "ESPAÇO, ↑, W ou CLIQUE: segurar e soltar",
    ]
    OPCOES = None
    MENOR_MELHOR = False
    ROTULO_PONTOS = "PONTOS"
    CONTAGEM = True

    TRILHA = dict(bpm=90, tom="Db", escala="pentatonica", lead="seno", envelope="normal",
                  baixo="longo", onda_baixo="triangulo", acomp="arpejo8", onda_acomp="sino",
                  bateria="suave", energia=0.3, eco=(0.33, 0.35))

    MOEDAS_POR = 6
    MOEDAS_MAX = 18
    MOEDAS_MIN = 1

    # --------------------------------------------------------
    # CENÁRIO: manhã no lago
    # --------------------------------------------------------

    @classmethod
    def criar_fundo(cls, jogador):
        sup = ui.gradiente(LARGURA, Y_MARGEM + 20, (255, 225, 200), (170, 220, 255))
        fundo = pygame.Surface((LARGURA, ALTURA))
        fundo.blit(sup, (0, 0))
        # Sol da manhã e nuvenzinhas
        pygame.draw.circle(fundo, (255, 240, 200), (820, 110), 56)
        pygame.draw.circle(fundo, (255, 220, 140), (820, 110), 44)
        for cx, cy in ((180, 90), (520, 60), (690, 170)):
            for dx, r in ((-26, 18), (0, 26), (28, 20)):
                pygame.draw.circle(fundo, (255, 250, 245), (cx + dx, cy), r)
        cam = _camadas()
        for nome in ("longe", "perto"):
            sup, y = cam[nome]
            fundo.blit(sup, (0, y))
        fundo.blit(cam["agua"], (0, Y_MARGEM))
        sup, y = cam["margem"]
        fundo.blit(sup, (0, y))
        return fundo

    @classmethod
    def desenhar_icone(cls, sup, jogador):
        w, h = sup.get_size()
        y = h - 30
        for x, larg in ((w * 0.22, 60), (w * 0.72, 60)):
            f = _folha_sup(larg, "normal", x > w / 2)
            sup.blit(f, f.get_rect(midtop=(int(x), y - 36)))
        # Arco pontilhado do pulo
        for i in range(1, 10):
            t = i / 10
            px = w * 0.22 + (w * 0.5) * t
            py = y - 30 - 4 * 50 * t * (1 - t)
            pygame.draw.circle(sup, BRANCO, (int(px), int(py)), 2)
        jogador.desenhar(sup, (int(w * 0.47), int(y - 76)), 34)
        ui.estrela(sup, (int(w * 0.5), int(y - 104)), 8, AMARELO, 0.2)

    # --------------------------------------------------------
    # PARTIDA
    # --------------------------------------------------------

    def reiniciar(self):
        _camadas()
        self.relogio = 0.0
        self.folhas = []
        self.estrelas = []          # [x, y] no mundo
        self.ondas = []             # [x, idade] anéis de ondinha
        self.saltos = 0
        self.perfeitos = 0
        self.combo = 0
        self.maior_combo = 0
        self.qtd_estrelas = 0
        self.boias = 0
        self.gerados = 0            # quantas folhas já foram criadas

        primeira = Folha(X_OVO, "normal", flor=True)
        primeira.largura = 140
        primeira.visitada = True
        self.folhas.append(primeira)
        self.atual = primeira       # folha em que o ovo está
        self.desvio = 0.0           # posição do ovo em relação ao centro da folha

        self.cam_x = 0.0
        self.estado_ovo = "parado"  # parado, carregando, voando, mola, agua
        self.forca = 0.0
        self.tempo_voo = 0.0
        self.voo = None             # (x0, distancia, altura, automatico)
        self.squash = 0.0
        self.tempo_agua = 0.0
        self.x_agua = 0.0
        self.pulo_sapos = 0.0
        self.espera_mola = 0.0
        self.carregando_tecla = False
        self._gerar()

    # --------------------------------------------------------
    # GERAÇÃO DAS FOLHAS
    # --------------------------------------------------------

    def _gerar(self):
        while self.folhas[-1].base < self.cam_x + LARGURA + 500:
            self._nova_folha()

    def _nova_folha(self):
        ant = self.folhas[-1]
        n = self.gerados + 1
        t = min(1.0, n / 70)

        # Tipo (depois de uma flor-mola sempre vem uma folha normal parada)
        tipo = "normal"
        if ant.tipo != "mola" and n > 2:
            r = random.random()
            opcoes = [
                ("movel", 0.10 + 0.16 * t if n > 5 else 0.0),
                ("afunda", 0.08 + 0.10 * t if n > 10 else 0.0),
                ("tartaruga", 0.08 + 0.08 * t if n > 15 else 0.0),
                ("mola", 0.06 if n > 8 else 0.0),
                ("pequena", 0.30 * t + 0.08 if n > 20 else 0.0),
            ]
            acum = 0.0
            for nome, chance in opcoes:
                acum += chance
                if r < acum:
                    tipo = nome
                    break
        folha = Folha(0, tipo, flor=random.random() < 0.25 and tipo in ("normal", "pequena"))

        # Distância: cresce com o tempo, mas sempre alcançável, contando
        # com o pior caso das duas folhas estarem se afastando
        folga = ant.amplitude + folha.amplitude
        maior = min(DIST_MAX - folga, 230 + 150 * t)
        menor = max((ant.largura + folha.largura) / 2 + 24 + folga, 110 + 50 * t)
        menor = min(menor, maior)
        if ant.tipo == "mola":
            maior = min(maior, 330)
        dist = random.uniform(menor, maior)
        folha.base = ant.base + dist

        # BOIA de vez em quando (em folha normal)
        if n % 25 == 12 and tipo == "normal":
            folha.boia = True

        # Estrela no alto do arco perfeito
        if n > 1 and random.random() < 0.3 and ant.tipo != "mola":
            p = _forca_para(dist)
            y = Y_FOLHA - ALTURA_OVO / 2 - _altura_arco(p)
            self.estrelas.append([ant.base + dist / 2, y])

        self.folhas.append(folha)
        self.gerados = n

    # --------------------------------------------------------
    # CONTROLES
    # --------------------------------------------------------

    def evento(self, e):
        # Soltou a tecla fora do jogo (pausa): cancela a carga
        if self.estado != "jogando":
            if e.type in (pygame.KEYUP, pygame.MOUSEBUTTONUP) and self.estado_ovo == "carregando":
                self.estado_ovo = "parado"
                self.forca = 0.0
        super().evento(e)

    def evento_jogo(self, e):
        if e.type == pygame.KEYDOWN and e.key in TECLAS_PULO:
            self._comecar_carga()
        elif e.type == pygame.KEYUP and e.key in TECLAS_PULO:
            self._soltar()
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self._comecar_carga()
        elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
            self._soltar()

    def _comecar_carga(self):
        if self.estado_ovo == "parado":
            self.estado_ovo = "carregando"
            self.forca = 0.0

    def _soltar(self):
        if self.estado_ovo == "carregando":
            self._pular(self.forca)

    def _pular(self, forca, automatico=False):
        x0 = self.x_ovo()
        self.voo = (x0, _alcance(forca), _altura_arco(forca), automatico)
        self.tempo_voo = 0.0
        self.estado_ovo = "voando"
        self.forca = 0.0
        self.squash = 0.0
        self.som("mola" if automatico else "pulo", 0.8)

    # --------------------------------------------------------
    # LÓGICA
    # --------------------------------------------------------

    def x_ovo(self):
        """Posição x (mundo) do ovo quando está em cima de uma folha."""
        return self.atual.x(self.relogio) + self.desvio

    def atualizar_jogo(self, dt):
        self.relogio += dt
        t = self.relogio
        self.squash = max(0.0, self.squash - dt)
        self.pulo_sapos = max(0.0, self.pulo_sapos - dt)
        self.ondas = [[x, idade + dt] for x, idade in self.ondas if idade + dt < 0.9]

        # Câmera: mantém a folha atual em X_OVO (suave)
        alvo = (self.atual.x(t) if self.estado_ovo != "voando" else self.voo[0] + self.voo[1]) - X_OVO
        self.cam_x += (alvo - self.cam_x) * min(1.0, 6 * dt)

        if self.estado_ovo == "carregando":
            self.forca = min(1.0, self.forca + dt / TEMPO_CARGA)
        elif self.estado_ovo == "voando":
            self._voar(dt)
        elif self.estado_ovo == "mola":
            self.espera_mola -= dt
            if self.espera_mola <= 0:
                prox = self._proxima(self.atual)
                dist = prox.x(t) - self.x_ovo()
                self._pular(_forca_para(dist), automatico=True)
        elif self.estado_ovo == "agua":
            self._na_agua(dt)
            return

        # Folha em que o ovo está afundou / mergulhou
        if self.estado_ovo in ("parado", "carregando", "mola"):
            f = self.atual
            if f.tipo == "afunda" and f.pisada is not None and t - f.pisada >= TEMPO_AFUNDA:
                f.afundou = True
            if f.submersa(t):
                self._cair(self.x_ovo())

        # Folhas secas continuam afundando mesmo sem o ovo em cima
        for f in self.folhas:
            if f.tipo == "afunda" and f.pisada is not None and t - f.pisada >= TEMPO_AFUNDA:
                f.afundou = True
            f.balanco = max(0.0, f.balanco - dt * 3)

        # Limpa o que ficou para trás
        limite = self.cam_x - 300
        self.folhas = [f for f in self.folhas if f.base + 200 > limite or f is self.atual]
        self.estrelas = [s for s in self.estrelas if s[0] > limite]
        self._gerar()

    def _proxima(self, folha):
        i = self.folhas.index(folha)
        return self.folhas[i + 1] if i + 1 < len(self.folhas) else folha

    def _voar(self, dt):
        self.tempo_voo += dt
        x0, dist, alt, auto = self.voo
        s = min(1.0, self.tempo_voo / TEMPO_ARCO)
        x, y = self._pos_voo(s)

        # Estrelas no caminho
        for est in list(self.estrelas):
            if math.hypot(est[0] - x, est[1] - y) < 42:
                self.estrelas.remove(est)
                self.pontos += 3
                self.qtd_estrelas += 1
                tela = (est[0] - self.cam_x, est[1])
                self.textos.adicionar("+3", (tela[0], tela[1] - 24), AMARELO, 16)
                self.particulas.explodir(tela, [AMARELO, BRANCO, (255, 240, 150)], 16, 200, 0.6)
                self.som("moeda", 0.8)

        if s >= 1.0:
            self._pousar(x0 + dist, auto)

    def _pos_voo(self, s):
        x0, dist, alt, _ = self.voo
        x = x0 + dist * s
        y = Y_FOLHA - ALTURA_OVO / 2 - 4 * alt * s * (1 - s)
        return x, y

    def _pousar(self, x, automatico):
        t = self.relogio
        alvo = None
        melhor = 1e9
        for f in self.folhas:
            if f.submersa(t):
                continue
            d = abs(x - f.x(t))
            if d <= f.largura / 2 and d < melhor:
                alvo, melhor = f, d
        if alvo is None:
            self._cair(x)
            return

        anterior = self.atual
        self.atual = alvo
        self.desvio = x - alvo.x(t)
        self.estado_ovo = "parado"
        self.squash = 0.14
        alvo.balanco = 1.0
        self.ondas.append([x, 0.0])
        tela = (x - self.cam_x, Y_FOLHA - ALTURA_OVO - 20)

        if alvo is anterior:
            # Pulinho na mesma folha: não conta
            self.som("boing", 0.5)
            return

        # Pontuação do salto
        self.saltos += 1
        if not alvo.visitada:
            alvo.visitada = True
            if melhor <= RAIO_PERFEITO and not automatico:
                self.combo += 1
                self.perfeitos += 1
                self.maior_combo = max(self.maior_combo, self.combo)
                ganho = 2 + min(4, self.combo - 1)
                txt = "PERFEITO!" if self.combo < 2 else f"PERFEITO x{self.combo}!"
                self.textos.adicionar(txt, (tela[0], tela[1] - 26), AMARELO, 20)
                self.textos.adicionar(f"+{ganho}", (tela[0], tela[1]), AMARELO, 16)
                self.particulas.explodir((tela[0], Y_FOLHA - 10),
                                         [AMARELO, BRANCO, self.jogador.cor], 20, 220, 0.7)
                self.som("acerto", 0.8)
                self.pulo_sapos = 0.7
            else:
                if not automatico:
                    self.combo = 0
                ganho = 1
                self.textos.adicionar("+1", tela, BRANCO, 14)
                self.som("ponto", 0.5)
            self.pontos += ganho

        # Folha especial
        if alvo.tipo == "afunda" and alvo.pisada is None:
            alvo.pisada = t
        elif alvo.tipo == "tartaruga":
            # Justo: dá pelo menos 1.2 s antes do mergulho
            falta = (CICLO_TARTARUGA - MERGULHO) - alvo.ciclo(t)
            if falta < 1.2:
                alvo.fase -= 1.2 - falta
        elif alvo.tipo == "mola":
            self.estado_ovo = "mola"
            self.espera_mola = 0.3
            self.pontos += 3
            self.textos.adicionar("MOLA! +3", (tela[0], tela[1] - 26), LOTUS, 16)
        if alvo.boia:
            alvo.boia = False
            self.boias = min(3, self.boias + 1)
            self.textos.adicionar("BOIA!", (tela[0], tela[1] - 50), (255, 120, 120), 16)
            self.som("moeda", 0.7)

    def _cair(self, x):
        self.estado_ovo = "agua"
        self.tempo_agua = 0.0
        self.x_agua = x
        self.combo = 0
        pos = (x - self.cam_x, Y_FOLHA)
        self.particulas.explodir(pos, [(120, 200, 255), (200, 240, 255), (60, 150, 230)],
                                 30, 300, 0.8, (3, 6))
        self.textos.adicionar("GLUB!", (pos[0], pos[1] - 80), (200, 240, 255), 20)
        self.ondas.append([x, 0.0])
        self.som("bater", 0.7)
        self.tremer(0.15)

    def _na_agua(self, dt):
        self.tempo_agua += dt
        if int(self.tempo_agua * 10) % 3 == 0:
            pos = (self.x_agua - self.cam_x + random.uniform(-20, 20), Y_FOLHA + 6)
            self.particulas.explodir(pos, [(210, 240, 255)], 1, 40, 0.6, (2, 4), gravidade=-120)
        if self.tempo_agua < 1.2:
            return

        if self.boias > 0:
            # A boia leva o ovo para a próxima folha (que fica segura)
            self.boias -= 1
            t = self.relogio
            destino = None
            for f in self.folhas:
                if f.base > self.x_agua - 20 and not f.visitada:
                    destino = f
                    break
            if destino is None:
                destino = self._proxima(self.atual)
            destino.tipo = "normal" if destino.tipo in ("afunda", "tartaruga", "mola") else destino.tipo
            destino.afundou = False
            destino.pisada = None
            destino.visitada = True
            self.atual = destino
            self.desvio = 0.0
            self.estado_ovo = "parado"
            self.squash = 0.14
            pos = (destino.x(t) - self.cam_x, Y_FOLHA - 60)
            self.textos.adicionar("SALVO PELA BOIA!", (pos[0], pos[1] - 30), (255, 150, 150), 14)
            self.som("acerto", 0.6)
        else:
            self.terminar(linhas=[f"PONTOS: {self.pontos}",
                                  f"SALTOS: {self.saltos}  PERFEITOS: {self.perfeitos}",
                                  f"MAIOR COMBO: {self.maior_combo}"])

    # --------------------------------------------------------
    # DESENHO
    # --------------------------------------------------------

    def _ovo(self, tela, pe, sx=1.0, sy=1.0, angulo=0.0, aparencia=None):
        """Desenha o ovo com o PÉ em `pe`, amassado por sx/sy."""
        img = self.jogador.avatar(ALTURA_OVO, aparencia)
        lado = img.get_width()
        escala = lado / 100
        if abs(sx - 1) > 0.01 or abs(sy - 1) > 0.01:
            img = pygame.transform.smoothscale(img, (max(1, round(lado * sx)), max(1, round(lado * sy))))
        if angulo:
            img = pygame.transform.rotate(img, angulo)
        ovo = self.jogador.OVO_RECT
        cy = pe[1] - ALTURA_OVO * sy / 2
        dx = (ovo.centerx - 50) * escala * sx
        dy = (ovo.centery - 50) * escala * sy
        tela.blit(img, img.get_rect(center=(round(pe[0] - dx), round(cy - dy))))

    def _desenhar_cenario(self, tela):
        tela.blit(self.fundo(self.jogador), (0, 0))
        cam = _camadas()
        # Parallax (morros 20% e 40%, margem 60%)
        for nome, fator in (("longe", 0.2), ("perto", 0.4), ("margem", 0.6)):
            sup, y = cam[nome]
            off = -(self.cam_x * fator) % LARGURA
            tela.blit(sup, (off - LARGURA, y))
            tela.blit(sup, (off, y))
        # Listras da água deslizando
        desloc = self.cam_x + self.tempo * 18
        for x, y, w, esp in cam["listras"]:
            xx = (x - desloc) % LARGURA
            pygame.draw.line(tela, AGUA_CLARA, (xx, y), (xx + w, y), esp)
            if xx + w > LARGURA:
                pygame.draw.line(tela, AGUA_CLARA, (xx - LARGURA, y), (xx + w - LARGURA, y), esp)

        # Sapos na margem (comemoram os PERFEITOS)
        base = self.cam_x * 0.6
        primeiro = int(base // 330)
        for i in range(primeiro, primeiro + 5):
            x = i * 330 + 150 - base
            if -30 < x < LARGURA + 30:
                pulo = 0.0
                if self.pulo_sapos > 0:
                    fase = (0.7 - self.pulo_sapos) / 0.7
                    pulo = abs(math.sin(fase * math.pi * 2 + i)) * 18
                self._sapo(tela, int(x), int(Y_MARGEM - 8 - pulo), self.pulo_sapos > 0)

    @staticmethod
    def _sapo(tela, x, y, feliz):
        pygame.draw.ellipse(tela, (40, 110, 40), (x - 15, y - 12, 30, 18))
        pygame.draw.ellipse(tela, (80, 170, 70), (x - 13, y - 11, 26, 15))
        for dx in (-7, 7):
            pygame.draw.circle(tela, (80, 170, 70), (x + dx, y - 12), 5)
            pygame.draw.circle(tela, BRANCO, (x + dx, y - 13), 3)
            pygame.draw.circle(tela, (0, 0, 0), (x + dx, y - 13), 1)
        if feliz:
            pygame.draw.arc(tela, (30, 60, 30), (x - 6, y - 8, 12, 7), math.pi, math.tau, 2)
            pygame.draw.line(tela, (80, 170, 70), (x - 13, y - 6), (x - 20, y - 16), 3)
            pygame.draw.line(tela, (80, 170, 70), (x + 13, y - 6), (x + 20, y - 16), 3)

    def _desenhar_folha(self, tela, f):
        t = self.relogio
        x = f.x(t) - self.cam_x
        if x < -120 or x > LARGURA + 120:
            return
        desce = f.balanco * 4

        if f.tipo == "tartaruga":
            c = f.ciclo(t)
            limite = CICLO_TARTARUGA - MERGULHO
            if c >= limite:
                # Mergulhada: só bolhas
                for i in range(3):
                    fase = (t * 2 + i * 0.3) % 1
                    pygame.draw.circle(tela, (200, 240, 255), (int(x - 20 + i * 20), int(Y_FOLHA + 4 - fase * 10)),
                                       3, 1)
                return
            sup = _tartaruga_sup(f.largura)
            tremer = math.sin(t * 40) * 2 if c > limite - 0.5 else 0
            tela.blit(sup, sup.get_rect(midbottom=(int(x + tremer), int(Y_FOLHA + 18 + desce))))
            return

        afunda = f.afundando(t)
        if f.afundou:
            return
        sup = _folha_sup(f.largura, "afunda" if f.tipo == "afunda" else "normal", f.flor)
        r = sup.get_rect(midtop=(int(x), int(Y_FOLHA - 40 + desce + afunda * 14)))
        if afunda > 0:
            sup = sup.copy()
            sup.set_alpha(int(255 * (1 - afunda * 0.7)))
            if int(t * 10) % 3 == 0:
                self.particulas.explodir((x + random.uniform(-30, 30), Y_FOLHA + 6), [(210, 240, 255)],
                                         1, 30, 0.4, (2, 3), gravidade=-100)
        tela.blit(sup, r)

        if f.tipo == "movel":
            ui.desenhar_texto(tela, "←→", (int(x), int(Y_FOLHA + 26 + desce)), 10, (30, 90, 50),
                              "center", sombra=False)
        elif f.tipo == "mola":
            m = _flor_mola_sup()
            aperto = 6 if (self.estado_ovo == "mola" and self.atual is f) else 0
            tela.blit(m, m.get_rect(midbottom=(int(x), int(Y_FOLHA + 6 + aperto))))
        if f.boia:
            b = _boia_sup()
            tela.blit(b, b.get_rect(center=(int(x + 22), int(Y_FOLHA - 20 + math.sin(t * 3) * 3))))

    def _desenhar_ovo(self, tela):
        t = self.relogio
        if self.estado_ovo == "agua":
            # Boiando, de boca aberta de susto
            x = self.x_agua - self.cam_x
            afunda = min(1.0, self.tempo_agua / 0.25)
            bob = math.sin(self.tempo_agua * 6) * 4
            ap = self.jogador.aparencia()
            ap = (ap[0], ap[1], ap[2], BOCA_SUSTO)
            clip = tela.get_clip()
            tela.set_clip(pygame.Rect(0, 0, LARGURA, int(Y_FOLHA + 4)))
            self._ovo(tela, (x, Y_FOLHA + ALTURA_OVO * 0.5 * afunda + bob), angulo=math.sin(self.tempo_agua * 4) * 12,
                      aparencia=ap)
            tela.set_clip(clip)
            if self.boias > 0 and self.tempo_agua > 0.4:
                b = _boia_sup(26)
                tela.blit(b, b.get_rect(center=(int(x), int(Y_FOLHA + bob))))
            return

        if self.estado_ovo == "voando":
            s = min(1.0, self.tempo_voo / TEMPO_ARCO)
            x, y = self._pos_voo(s)
            estica = 0.18 * (1 - s * 2) if s < 0.5 else 0.0
            ang = -12 * (1 - 2 * s)
            self._ovo(tela, (x - self.cam_x, y + ALTURA_OVO / 2), 1 - estica * 0.6, 1 + estica, ang)
            return

        x = self.x_ovo() - self.cam_x
        pe_y = Y_FOLHA + self.atual.balanco * 4 + self.atual.afundando(t) * 14
        if self.estado_ovo == "carregando":
            p = self.forca
            sx, sy = 1 + 0.25 * p, 1 - 0.4 * p
            tremida = math.sin(t * 50) * 1.5 * p if p > 0.85 else 0
            self._ovo(tela, (x + tremida, pe_y), sx, sy)
            self._arco_carga(tela, (x, pe_y - ALTURA_OVO * 0.45), p)
        else:
            k = self.squash / 0.14 if self.squash > 0 else 0.0
            if self.estado_ovo == "mola":
                k = 1.0 - max(0.0, self.espera_mola) / 0.3
            sx, sy = 1 + 0.2 * k, 1 - 0.22 * k
            self._ovo(tela, (x, pe_y), sx, sy)

    def _arco_carga(self, tela, centro, p):
        if p <= 0:
            return
        cor = ui.misturar((80, 220, 80), (255, 220, 50), p * 1.6) if p < 0.62 else \
            ui.misturar((255, 220, 50), (240, 60, 50), (p - 0.62) / 0.38)
        r = pygame.Rect(0, 0, 104, 104)
        r.center = (int(centro[0]), int(centro[1]))
        inicio = math.pi / 2 - p * math.pi
        fim = math.pi / 2 + p * math.pi
        pygame.draw.arc(tela, (20, 40, 50), r.inflate(6, 6), inicio, fim, 9)
        pygame.draw.arc(tela, cor, r, inicio, fim, 6)

    def desenhar_jogo(self, tela):
        self._desenhar_cenario(tela)
        t = self.relogio

        # Anéis de ondinha
        for x, idade in self.ondas:
            sx = x - self.cam_x
            for k in range(3):
                a = idade - k * 0.15
                if a <= 0:
                    continue
                w = int(40 + a * 180)
                h = max(4, int(w * 0.18))
                pygame.draw.ellipse(tela, (190, 235, 250), (int(sx - w / 2), int(Y_FOLHA + 4 - h / 2), w, h), 2)

        for f in self.folhas:
            self._desenhar_folha(tela, f)

        # Estrelas
        for est in self.estrelas:
            x = est[0] - self.cam_x
            if -30 < x < LARGURA + 30:
                bal = math.sin(self.tempo * 4 + est[0]) * 4
                ui.estrela(tela, (int(x), int(est[1] + bal)), 15, (190, 120, 10), self.tempo)
                ui.estrela(tela, (int(x), int(est[1] + bal)), 12, AMARELO, self.tempo)

        self._desenhar_ovo(tela)

        # Juncos na frente (60% mais rápidos que a água: dão profundidade)
        for sup, gx in _camadas()["juncos"]:
            x = (gx - self.cam_x * 1.3) % LARGURA
            tela.blit(sup, (x, ALTURA - 120))
            if x > LARGURA - sup.get_width():
                tela.blit(sup, (x - LARGURA, ALTURA - 120))

        self.particulas.desenhar(tela)
        self.textos.desenhar(tela)

        if self.estado == "jogando" and self.saltos == 0 and self.estado_ovo == "parado" \
                and self.tempo_partida < 6:
            ui.desenhar_texto(tela, "SEGURE E SOLTE!", (LARGURA // 2, 250), 16, BRANCO, "center")

    def desenhar_hud(self, tela):
        # Pontos e recorde no mesmo painel (o céu claro apagaria o texto)
        caixa = pygame.Rect(12, 12, 420, 48)
        ui.painel(tela, caixa, (20, 24, 40), BRANCO, 12, 3, sombra=False)
        ui.desenhar_texto(tela, f"PONTOS: {self.pontos}", (caixa.x + 16, caixa.centery), 14,
                          AMARELO, "midleft")
        rec = self.recorde()
        if rec is not None:
            ui.desenhar_texto(tela, f"RECORDE: {rec}", (caixa.x + 236, caixa.centery), 12,
                              (180, 200, 255), "midleft")

        caixa = pygame.Rect(12, 66, 300, 36)
        ui.painel(tela, caixa, (20, 24, 40), BRANCO, 10, 2, sombra=False)
        ui.desenhar_texto(tela, f"SALTOS {self.saltos}", (caixa.x + 12, caixa.centery), 12,
                          (180, 220, 255), "midleft")
        if self.combo >= 2:
            ui.desenhar_texto(tela, f"COMBO x{self.combo}", (caixa.x + 150, caixa.centery), 12,
                              AMARELO, "midleft")
        if self.boias:
            caixa = pygame.Rect(12, 108, 60 + 34 * self.boias, 40)
            ui.painel(tela, caixa, (20, 24, 40), (255, 150, 150), 10, 2, sombra=False)
            ui.desenhar_texto(tela, "BOIA", (caixa.x + 10, caixa.centery), 10, BRANCO, "midleft")
            for i in range(self.boias):
                b = _boia_sup(12)
                tela.blit(b, b.get_rect(center=(caixa.x + 72 + i * 30, caixa.centery)))
