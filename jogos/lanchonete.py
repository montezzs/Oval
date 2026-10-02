import math
import random

import pygame

from settings import *
from core import ui
from core.idioma import t
from jogos.base import MiniJogo

# ============================================================
# LANCHONETE DO OVO
# ============================================================
# O seu ovo abriu uma lanchonete anos 50! Os clientes (a família
# do ovo, o ROBERT e o TOTÓ) pedem lanches e você monta a pilha
# na ordem certa: pão de baixo, recheios e o pão de cima. Errou
# um ingrediente? Joga a pilha no lixo e começa de novo.
# Cliente que perde a paciência vai embora bravo e leva uma das
# 3 estrelas da lanchonete. O expediente dura 150 segundos.

# ------------------------------------------------------------
# REGRAS
# ------------------------------------------------------------
EXPEDIENTE = 150.0
ESTRELAS = 3
PACIENCIA_INICIO = 20.0             # segundos no começo do expediente...
PACIENCIA_FIM = 10.0                # ... e no fim
DRENO_FILA = 0.3                    # quem está na fila perde paciência mais devagar
REFRESCO_BALCAO = 0.6               # ao chegar no balcão recupera até 60% da paciência
PENA_LIXO = 2.0
MAX_CLIENTES = 4                    # 1 no balcão + 3 na fila
INICIO_SUCO = 60.0
CHANCE_SUCO = 0.35

# Por dificuldade: (máx. de ingredientes do lanche, multiplicador da paciência, intervalo dos clientes)
DIFICULDADES = [(4, 1.4, 1.25), (6, 1.0, 1.0), (7, 0.8, 0.85)]

INGREDIENTES = ["pao", "carne", "queijo", "alface", "tomate", "cebola"]
NOMES = {"pao": "PÃO", "pao_base": "PÃO", "pao_topo": "PÃO", "carne": "CARNE", "queijo": "QUEIJO",
         "alface": "ALFACE", "tomate": "TOMATE", "cebola": "CEBOLA", "suco": "SUCO"}
TECLA_DE = {"pao_base": 1, "pao_topo": 1, "carne": 2, "queijo": 3, "alface": 4, "tomate": 5, "cebola": 6,
            "suco": 7}
RECHEIOS = ["carne", "queijo", "alface", "tomate", "cebola"]
PESO_RECHEIOS = [30, 25, 20, 15, 10]

# ------------------------------------------------------------
# CENÁRIO
# ------------------------------------------------------------
BALCAO_Y = 420
BALCAO_FIM = 500
PRATO = (512, 545)
BASE_PILHA = 540
X_BALCAO = 420                      # cliente sendo atendido
X_FILA = [420, 620, 745, 870]
POTE_W, POTE_H = 92, 108
POTES_X = [252 + i * 104 for i in range(6)]
POTE_Y = 592
SUCO_RECT = pygame.Rect(858, 520, 110, 180)
LIXO_RECT = pygame.Rect(120, 626, 62, 80)
CHEF = (66, 600)
COPO_POS = (648, 526)
BALAO_X, BALAO_W, BALAO_BAIXO = 16, 300, 402

LARG_PRATO = 118                    # largura dos ingredientes no prato
LARG_ICONE = 70                     # no balão do pedido
LARG_POTE = 58                      # dentro do pote

TECLAS_ESQ = (pygame.K_LEFT, pygame.K_a)
TECLAS_DIR = (pygame.K_RIGHT, pygame.K_d)
TECLAS_POR = (pygame.K_SPACE, pygame.K_DOWN, pygame.K_s, pygame.K_RETURN, pygame.K_KP_ENTER)
TECLAS_LIXO = (pygame.K_UP, pygame.K_w, pygame.K_BACKSPACE)
NUMEROS = {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2, pygame.K_4: 3, pygame.K_5: 4, pygame.K_6: 5,
           pygame.K_KP1: 0, pygame.K_KP2: 1, pygame.K_KP3: 2, pygame.K_KP4: 3, pygame.K_KP5: 4,
           pygame.K_KP6: 5}
TECLAS_SUCO = (pygame.K_7, pygame.K_KP7)


# ============================================================
# DESENHO DOS INGREDIENTES (com cache)
# ============================================================
# Cada camada é desenhada 3x maior e diminuída (fica suave).
# `espessura` = quanto a camada sobe a pilha; `pendura` = quanto
# ela passa para baixo da linha (o queijo pinga).

Z = 3
ALTURAS = {  # (altura da imagem, espessura na pilha, pendura) em fração da largura
    "pao_base": (0.24, 0.2, 0.0),
    "carne": (0.2, 0.16, 0.0),
    "queijo": (0.2, 0.07, 0.12),
    "alface": (0.14, 0.09, 0.02),
    "tomate": (0.12, 0.09, 0.0),
    "cebola": (0.1, 0.07, 0.0),
    "pao_topo": (0.44, 0.4, 0.0),
}

_camadas = {}


def _desenhar_camada(tipo, w):
    fa, _, _ = ALTURAS[tipo]
    W, H = int(w * Z), max(3, int(w * fa * Z))
    s = pygame.Surface((W, H), pygame.SRCALPHA)
    borda = 2 * Z

    if tipo == "pao_base":
        r = pygame.Rect(W * 0.03, H * 0.1, W * 0.94, H * 0.86)
        pygame.draw.rect(s, (150, 95, 40), r, border_radius=int(H * 0.35))
        pygame.draw.rect(s, (230, 170, 80), r.inflate(-borda * 2, -borda * 2), border_radius=int(H * 0.3))
        pygame.draw.rect(s, (250, 215, 150), (r.x + borda * 2, r.y + borda, r.w - borda * 4, H * 0.22),
                         border_radius=int(H * 0.1))
    elif tipo == "carne":
        r = pygame.Rect(W * 0.02, H * 0.05, W * 0.96, H * 0.9)
        pygame.draw.rect(s, (70, 40, 20), r, border_radius=int(H * 0.45))
        pygame.draw.rect(s, (120, 70, 40), r.inflate(-borda * 2, -borda * 2), border_radius=int(H * 0.4))
        for k in range(6):
            x = r.x + W * 0.1 + k * W * 0.15
            pygame.draw.line(s, (90, 50, 25), (x, r.y + H * 0.3), (x + W * 0.06, r.y + H * 0.3), Z * 2)
        pygame.draw.rect(s, (150, 95, 60), (r.x + W * 0.08, r.y + borda, W * 0.6, H * 0.15),
                         border_radius=int(H * 0.08))
    elif tipo == "queijo":
        topo = H * 0.35
        pygame.draw.rect(s, (220, 160, 20), (0, 0, W, topo + borda))
        pygame.draw.rect(s, (255, 210, 60), (borda, borda, W - borda * 2, topo - borda))
        for k, fx in enumerate((0.12, 0.36, 0.62, 0.86)):
            x = W * fx
            comp = H * (0.95 if k % 2 == 0 else 0.7)
            tri = [(x - W * 0.07, topo), (x + W * 0.07, topo), (x, comp)]
            pygame.draw.polygon(s, (220, 160, 20), [(tri[0][0] - Z, tri[0][1]), (tri[1][0] + Z, tri[1][1]),
                                                     (tri[2][0], tri[2][1] + Z)])
            pygame.draw.polygon(s, (255, 210, 60), tri)
    elif tipo == "alface":
        pts = [(0, H * 0.5)]
        for k in range(17):
            x = W * k / 16
            pts.append((x, H * (0.18 if k % 2 == 0 else 0.02)))
        pts.append((W, H * 0.5))
        for k in range(16, -1, -1):
            x = W * k / 16
            pts.append((x, H * (0.98 if k % 2 == 0 else 0.7)))
        pygame.draw.polygon(s, (60, 140, 50), pts)
        interno = [(x, y + (borda if y < H * 0.5 else -borda)) for x, y in pts]
        pygame.draw.polygon(s, (110, 200, 80), interno)
        for k in range(5):
            x = W * (0.1 + k * 0.2)
            pygame.draw.line(s, (170, 230, 130), (x, H * 0.3), (x + W * 0.06, H * 0.6), Z)
    elif tipo == "tomate":
        for k in range(3):
            r = pygame.Rect(W * 0.01 + k * W * 0.33, 0, W * 0.33, H)
            pygame.draw.ellipse(s, (150, 30, 25), r)
            pygame.draw.ellipse(s, (230, 60, 50), r.inflate(-borda * 2, -borda * 2))
            pygame.draw.ellipse(s, (255, 130, 110), r.inflate(-r.w * 0.45, -r.h * 0.45))
    elif tipo == "cebola":
        for k in range(3):
            r = pygame.Rect(W * 0.02 + k * W * 0.32, 0, W * 0.32, H)
            pygame.draw.ellipse(s, (170, 130, 170), r, borda + Z)
            pygame.draw.ellipse(s, (240, 220, 240), r.inflate(-Z * 2, -Z * 2), borda)
    elif tipo == "pao_topo":
        r = pygame.Rect(W * 0.02, H * 0.04, W * 0.96, H * 1.7)
        pygame.draw.ellipse(s, (150, 95, 40), r)
        pygame.draw.ellipse(s, (230, 170, 80), r.inflate(-borda * 2, -borda * 2))
        pygame.draw.ellipse(s, (250, 205, 130), (r.x + W * 0.14, r.y + H * 0.12, W * 0.34, H * 0.22))
        pygame.draw.rect(s, (150, 95, 40), (0, H * 0.86, W, H * 0.14))
        pygame.draw.rect(s, (215, 150, 65), (borda, H * 0.86, W - borda * 2, H * 0.14 - borda))
        rnd = random.Random(4)
        for _ in range(11):
            x = rnd.uniform(0.18, 0.82) * W
            y = rnd.uniform(0.25, 0.7) * H
            if ((x - W / 2) / (W * 0.45)) ** 2 + ((y - H * 0.9) / (H * 0.8)) ** 2 > 1:
                continue
            pygame.draw.ellipse(s, (255, 250, 230), (x, y, W * 0.035, H * 0.06))
    return pygame.transform.smoothscale(s, (max(1, W // Z), max(1, H // Z)))


def _camada(tipo, w, errado=False):
    chave = (tipo, w, errado)
    s = _camadas.get(chave)
    if s is None:
        if errado:
            s = _camada(tipo, w).copy()
            s.fill((255, 170, 170), special_flags=pygame.BLEND_RGB_MULT)
        else:
            s = _desenhar_camada(tipo, w)
        _camadas[chave] = s
    return s


def _copo(w):
    """Copo de suco de limão com canudinho."""
    chave = ("copo", w)
    s = _camadas.get(chave)
    if s is not None:
        return s
    W, H = int(w * Z), int(w * 1.5 * Z)
    s = pygame.Surface((W, H), pygame.SRCALPHA)
    corpo = [(W * 0.12, H * 0.2), (W * 0.88, H * 0.2), (W * 0.78, H * 0.98), (W * 0.22, H * 0.98)]
    suco = [(W * 0.15, H * 0.34), (W * 0.85, H * 0.34), (W * 0.78, H * 0.94), (W * 0.22, H * 0.94)]
    pygame.draw.line(s, (240, 80, 90), (W * 0.58, H * 0.5), (W * 0.78, H * 0.02), Z * 4)
    pygame.draw.polygon(s, (220, 240, 250), corpo)
    pygame.draw.polygon(s, (220, 235, 80), suco)
    pygame.draw.polygon(s, (120, 150, 170), corpo, Z * 2)
    pygame.draw.line(s, (255, 255, 255), (W * 0.26, H * 0.4), (W * 0.3, H * 0.85), Z * 3)
    pygame.draw.circle(s, (120, 170, 40), (int(W * 0.84), int(H * 0.22)), int(W * 0.2))
    pygame.draw.circle(s, (230, 240, 120), (int(W * 0.84), int(H * 0.22)), int(W * 0.16))
    s = pygame.transform.smoothscale(s, (W // Z, H // Z))
    _camadas[chave] = s
    return s


# ============================================================
# CLIENTES
# ============================================================

class Cliente:

    def __init__(self, tipo, aparencia, paciencia):
        self.tipo = tipo                # "ovo", "robert", "toto"
        self.aparencia = aparencia
        self.x = LARGURA + 90.0
        self.pac_max = paciencia
        self.paciencia = paciencia
        self.estado = "fila"            # fila, balcao, feliz, bravo
        self.t = 0.0
        self.pedido = []
        self.suco = False
        self.pulo = 0.0
        self.fase = random.uniform(0, math.tau)

    @property
    def frac(self):
        return max(0.0, min(1.0, self.paciencia / self.pac_max))


class Lanchonete(MiniJogo):

    ID = "lanchonete"
    TITULO = "LANCHONETE DO OVO"
    TITULO_CURTO = "LANCHONETE"
    DESCRICAO = "Seu ovo abriu uma lanchonete! Monte os lanches na ordem certa antes que a paciência acabe."
    COR = (230, 70, 90)
    INSTRUCOES = [
        "Monte de baixo p/ cima: PÃO, recheios, PÃO!",
        "Errou? Jogue no lixo (↑) e comece de novo.",
        "Cliente bravo leva uma das 3 estrelas!",
        "Depois de 60 s: SUCO DE LIMÃO (tecla 7).",
        "←→ escolhe • ESPAÇO põe • 1-7 • ↑ lixo",
    ]
    OPCOES = ["CAFÉ DA MANHÃ", "ALMOÇO", "HORA DO RUSH"]
    MOEDAS_POR = 50
    MOEDAS_MAX = 24
    MOEDAS_VITORIA = 4

    # --------------------------------------------------------
    # CENÁRIO: lanchonete anos 50
    # --------------------------------------------------------

    @classmethod
    def criar_fundo(cls, jogador):
        sup = pygame.Surface((LARGURA, ALTURA))
        sup.fill((255, 230, 200))
        rnd = random.Random(9)

        # Listras verticais suaves na parede
        for x in range(0, LARGURA, 48):
            pygame.draw.rect(sup, (250, 222, 190), (x, 0, 24, 300))

        # Quadro com milk-shake
        q = pygame.Rect(560, 150, 110, 130)
        pygame.draw.rect(sup, (60, 160, 170), q, border_radius=8)
        pygame.draw.rect(sup, (40, 110, 120), q, 4, border_radius=8)
        copo = [(q.centerx - 26, q.y + 50), (q.centerx + 26, q.y + 50), (q.centerx + 16, q.bottom - 14),
                (q.centerx - 16, q.bottom - 14)]
        pygame.draw.polygon(sup, (255, 170, 200), copo)
        pygame.draw.polygon(sup, (200, 100, 140), copo, 3)
        for dx, r in ((-14, 14), (6, 16), (20, 11)):
            pygame.draw.circle(sup, (255, 250, 245), (q.centerx + dx, q.y + 46), r)
        pygame.draw.circle(sup, (220, 30, 50), (q.centerx + 4, q.y + 26), 8)
        pygame.draw.line(sup, (240, 240, 250), (q.centerx + 10, q.y + 36), (q.centerx + 26, q.y + 12), 5)

        # Cardápio
        c = pygame.Rect(700, 146, 290, 140)
        pygame.draw.rect(sup, (40, 40, 50), c, border_radius=8)
        pygame.draw.rect(sup, (170, 120, 70), c, 6, border_radius=8)
        titulo = ui.texto(t("CARDÁPIO"), 14, (255, 220, 120), sombra=False)
        sup.blit(titulo, titulo.get_rect(midtop=(c.centerx, c.y + 14)))
        for k, (nome, preco) in enumerate((("X-OVO", "5"), ("X-SALADA", "7"), ("SUCO LIMÃO", "3"))):
            y = c.y + 46 + k * 28
            n = ui.texto(t(nome), 10, (240, 240, 240), sombra=False)
            p = ui.texto(preco, 10, (255, 220, 120), sombra=False)
            sup.blit(n, (c.x + 20, y))
            ui.moeda(sup, (c.right - 44, y + 5), 7)
            sup.blit(p, (c.right - 30, y))

        # Relógio
        rel = (400, 210)
        pygame.draw.circle(sup, (230, 60, 60), rel, 38)
        pygame.draw.circle(sup, (255, 255, 250), rel, 31)
        for i in range(12):
            a = i * math.tau / 12
            pygame.draw.circle(sup, (60, 60, 80), (int(rel[0] + math.cos(a) * 25), int(rel[1] + math.sin(a) * 25)), 2)
        pygame.draw.line(sup, (40, 40, 60), rel, (rel[0], rel[1] - 20), 3)
        pygame.draw.line(sup, (40, 40, 60), rel, (rel[0] + 14, rel[1] + 5), 3)

        # Faixa xadrez vermelho/branco
        lado = 15
        for i in range(LARGURA // lado + 1):
            for j in range(2):
                cor = (230, 60, 60) if (i + j) % 2 == 0 else (255, 255, 255)
                pygame.draw.rect(sup, cor, (i * lado, 300 + j * lado, lado, lado))
        pygame.draw.line(sup, (180, 40, 40), (0, 300), (LARGURA, 300), 2)
        pygame.draw.line(sup, (180, 40, 40), (0, 330), (LARGURA, 330), 2)

        # Parede de baixo (atrás dos clientes)
        pygame.draw.rect(sup, (240, 205, 170), (0, 332, LARGURA, BALCAO_Y - 332))

        # Cozinha (bancada de inox)
        cozinha = ui.gradiente(LARGURA, ALTURA - BALCAO_FIM, (170, 176, 190), (120, 126, 140))
        sup.blit(cozinha, (0, BALCAO_FIM))
        for _ in range(40):
            x, y = rnd.randrange(LARGURA), rnd.randrange(BALCAO_FIM + 10, ALTURA)
            pygame.draw.line(sup, (185, 190, 205), (x, y), (x + rnd.randint(30, 90), y), 1)
        # Prateleira dos potes
        pygame.draw.rect(sup, (90, 94, 110), (180, POTE_Y + POTE_H - 6, 650, 14), border_radius=4)
        pygame.draw.rect(sup, (200, 205, 215), (180, POTE_Y + POTE_H - 6, 650, 4), border_radius=2)

        # Prato
        prato = pygame.Rect(0, 0, 190, 40)
        prato.center = PRATO
        pygame.draw.ellipse(sup, (90, 94, 110), prato.move(0, 6))
        pygame.draw.ellipse(sup, (230, 230, 235), prato)
        pygame.draw.ellipse(sup, (255, 255, 255), prato.inflate(-40, -12))
        pygame.draw.ellipse(sup, (200, 200, 210), prato.inflate(-40, -12), 2)
        return sup

    @classmethod
    def desenhar_icone(cls, sup, jogador):
        w, h = sup.get_size()
        # Lanche grande no centro
        pilha = ["pao_base", "carne", "queijo", "alface", "tomate", "pao_topo"]
        larg = int(w * 0.3)
        y = h - 18
        cx = int(w * 0.62)
        pygame.draw.ellipse(sup, (255, 255, 255), (cx - larg * 0.7, y - 8, larg * 1.4, 18))
        for c in pilha:
            s = _camada(c, larg)
            _, esp, pend = ALTURAS[c]
            sup.blit(s, s.get_rect(midbottom=(cx, int(y + pend * larg))))
            y -= esp * larg
        # Chef
        centro = (int(w * 0.24), int(h * 0.62))
        altura = h * 0.42
        jogador.desenhar(sup, centro, altura)
        if not jogador.save["equipado"].get("cabeca"):
            _chapeu_chef(sup, centro, altura)

    # --------------------------------------------------------
    # PARTIDA
    # --------------------------------------------------------

    def reiniciar(self):
        self.max_ingr, self.mult_pac, self.mult_intervalo = DIFICULDADES[self.opcao]
        self.relogio = 0.0
        self.estrelas = ESTRELAS
        self.atendidos = 0
        self.cursor = 0                 # pote selecionado (6 = máquina de suco)
        self.pilha = []                 # [tipo, queda, velocidade, squash]
        self.errado = False
        self.tremer_pilha = 0.0
        self.suco_pronto = False
        self.clientes = []
        self.saindo = []                # clientes indo embora
        self.entregando = None          # lanche voando para o cliente
        self.proximo_cliente = 3.0
        self.acabando = 0.0             # espera curta antes da tela de fim
        self.fim_motivo = None
        self.chef_pulo = 0.0
        self.chef_nao = 0.0
        self.aviso = ("", 0.0)
        self.estrela_quebrando = 0.0
        self._placa_nome = None

        # Dois clientes já esperando (aparecem na prévia)
        self._novo_cliente(x=X_FILA[0])
        self._novo_cliente(x=X_FILA[1])
        self._promover()

    # --------------------------------------------------------
    # CLIENTES E PEDIDOS
    # --------------------------------------------------------

    def _paciencia(self):
        k = min(1.0, self.relogio / EXPEDIENTE)
        return (PACIENCIA_INICIO + (PACIENCIA_FIM - PACIENCIA_INICIO) * k) * self.mult_pac

    def _novo_cliente(self, x=None):
        r = random.random()
        if r < 0.14:
            tipo, apar = "robert", None
        elif r < 0.28:
            tipo, apar = "toto", None
        else:
            tipo = "ovo"
            meu = self.jogador.aparencia()
            while True:
                apar = (random.randrange(4), random.randrange(8), random.randrange(3), random.randrange(6))
                if apar[:3] != meu[:3]:
                    break
        c = Cliente(tipo, apar, self._paciencia())
        if x is not None:
            c.x = float(x)
        self.clientes.append(c)

    def _novo_pedido(self):
        # Os lanches crescem ao longo do expediente
        k = min(1.0, self.relogio / (EXPEDIENTE * 0.75))
        maximo = 1 + int(round(k * (self.max_ingr - 3)))
        maximo = max(1, min(self.max_ingr - 2, maximo))
        n = random.randint(max(1, maximo - 2), maximo)
        recheios = []
        for _ in range(n):
            for _ in range(10):
                r = random.choices(RECHEIOS, PESO_RECHEIOS)[0]
                if recheios.count(r) < 2 and (not recheios or recheios[-1] != r):
                    break
            recheios.append(r)
        suco = self.relogio >= INICIO_SUCO and random.random() < CHANCE_SUCO
        return ["pao_base"] + recheios + ["pao_topo"], suco

    def _promover(self):
        """O primeiro da fila vai para o balcão."""
        if self.clientes and self.clientes[0].estado == "fila":
            c = self.clientes[0]
            c.estado = "balcao"
            c.pedido, c.suco = self._novo_pedido()
            c.paciencia = max(c.paciencia, c.pac_max * REFRESCO_BALCAO)

    @property
    def atual(self):
        """Cliente no balcão (ou None)."""
        if self.clientes and self.clientes[0].estado == "balcao":
            return self.clientes[0]
        return None

    # --------------------------------------------------------
    # CONTROLES
    # --------------------------------------------------------

    def evento_jogo(self, e):
        if self.fim_motivo:
            return
        if e.type == pygame.KEYDOWN:
            if e.key in TECLAS_ESQ:
                self.cursor = (self.cursor - 1) % 7
                self.som("clique", 0.5)
            elif e.key in TECLAS_DIR:
                self.cursor = (self.cursor + 1) % 7
                self.som("clique", 0.5)
            elif e.key in TECLAS_POR:
                self._usar(self.cursor)
            elif e.key in TECLAS_LIXO:
                self._lixeira()
            elif e.key in NUMEROS:
                self.cursor = NUMEROS[e.key]
                self._usar(self.cursor)
            elif e.key in TECLAS_SUCO:
                self.cursor = 6
                self._usar(6)
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self.botao_pausa.collidepoint(e.pos):
                return
            for i, x in enumerate(POTES_X):
                r = pygame.Rect(0, 0, POTE_W, POTE_H + 20)
                r.midtop = (x, POTE_Y - 20)
                if r.collidepoint(e.pos):
                    self.cursor = i
                    self._usar(i)
                    return
            if SUCO_RECT.collidepoint(e.pos):
                self.cursor = 6
                self._usar(6)
            elif LIXO_RECT.inflate(20, 20).collidepoint(e.pos):
                self._lixeira()

    def _avisar(self, msg):
        self.aviso = (msg, 1.4)

    def _usar(self, indice):
        if indice == 6:
            self._dar_suco()
        else:
            self._colocar(INGREDIENTES[indice])

    def _colocar(self, ingr):
        c = self.atual
        if c is None or self.entregando:
            self._avisar(t("ESPERE O CLIENTE!"))
            return
        if self.errado:
            self.tremer_pilha = 0.4
            self.som("erro", 0.5)
            self._avisar(t("JOGUE FORA! (↑)"))
            return
        if len(self.pilha) >= 9:
            return

        if ingr == "pao":
            tipo = "pao_base" if not self.pilha else "pao_topo"
        else:
            tipo = ingr
        self.pilha.append([tipo, -120.0, 0.0, 0.0])
        self.chef_pulo = 0.25
        self.som("pulo", 0.4)

        n = len(self.pilha)
        if n > len(c.pedido) or c.pedido[n - 1] != tipo:
            self.errado = True
            self.tremer_pilha = 0.5
            self.chef_nao = 0.6
            self.som("erro", 0.8)
            self._avisar(t("ERROU! JOGUE FORA (↑)"))
            return

        self._talvez_entregar()

    def _dar_suco(self):
        c = self.atual
        if c is None or self.entregando:
            self._avisar(t("ESPERE O CLIENTE!"))
            return
        if not c.suco:
            self.som("erro", 0.5)
            self._avisar(t("NÃO PEDIU SUCO!"))
            return
        if self.suco_pronto:
            return
        self.suco_pronto = True
        self.som("comer", 0.6)
        self.particulas.explodir(COPO_POS, [(230, 240, 90), (255, 255, 200)], 10, 140, 0.5, (2, 4))
        self._talvez_entregar()

    def _talvez_entregar(self):
        c = self.atual
        if c is None or self.errado:
            return
        if len(self.pilha) != len(c.pedido):
            return
        if c.suco and not self.suco_pronto:
            self._avisar(t("FALTA O SUCO! (7)"))
            return
        self._entregar(c)

    def _lixeira(self):
        if not self.pilha:
            return
        self.pilha = []
        self.errado = False
        self.tremer_pilha = 0.0
        c = self.atual
        self.som("virar", 0.7)
        self.particulas.explodir(LIXO_RECT.midtop, [(230, 170, 80), (120, 70, 40), (110, 200, 80)], 12, 160,
                                 0.5, (3, 6))
        if c is not None:
            c.paciencia = max(0.1, c.paciencia - PENA_LIXO)
            self.textos.adicionar(f"-{PENA_LIXO:.0f} s", (X_BALCAO + 70, 300), (255, 140, 140), 14)

    def _entregar(self, c):
        n = len(c.pedido) + (1 if c.suco else 0)
        bonus = int(round(20 * c.frac))
        ganho = 10 + 5 * n + bonus
        self.pontos += ganho
        self.atendidos += 1
        msg = t("+{n} RÁPIDO!", n=ganho) if bonus >= 14 else f"+{ganho}"
        self.textos.adicionar(msg, (c.x, 250), AMARELO if bonus >= 14 else BRANCO, 20 if bonus >= 14 else 16)
        self.som("acerto")
        self.entregando = [[p[0] for p in self.pilha], self.suco_pronto, 0.0]
        self.pilha = []
        self.suco_pronto = False
        c.estado, c.t = "feliz", 0.0
        c.pulo = 1.0

    def _embora_bravo(self, c):
        era_balcao = c is self.atual
        c.estado, c.t = "bravo", 0.0
        self.estrelas -= 1
        self.estrela_quebrando = 1.0
        self.tremer(0.25)
        self.som("perder", 0.7)
        self.textos.adicionar(t("HMPF!"), (c.x, 280), (255, 110, 110), 20)
        if era_balcao:
            # A pilha desse cliente vai para o lixo
            if self.pilha:
                self.particulas.explodir((PRATO[0], BASE_PILHA - 20), [(230, 170, 80), (120, 70, 40)], 10, 160,
                                         0.5, (3, 6))
            self.pilha = []
            self.errado = False
            self.suco_pronto = False
        if self.estrelas <= 0:
            self.estrelas = 0
            self.fim_motivo = "estrelas"
            self.acabando = 1.6

    # --------------------------------------------------------
    # LÓGICA
    # --------------------------------------------------------

    def atualizar_jogo(self, dt):
        if self.fim_motivo:
            self.acabando -= dt
            self._animar(dt)
            if self.acabando <= 0:
                self._fim()
            return

        self.relogio += dt
        if self.relogio >= EXPEDIENTE:
            self.relogio = EXPEDIENTE
            self.fim_motivo = "tempo"
            self.acabando = 1.0
            self.som("bandeira")
            self.textos.adicionar(t("FIM DO EXPEDIENTE!"), (LARGURA // 2, 250), AMARELO, 24)
            return

        # Chegada de clientes
        self.proximo_cliente -= dt
        esperando = len(self.clientes)
        if esperando == 0 and self.proximo_cliente > 1.2:
            self.proximo_cliente = 1.2
        if self.proximo_cliente <= 0 and esperando < MAX_CLIENTES:
            self._novo_cliente()
            k = min(1.0, self.relogio / EXPEDIENTE)
            self.proximo_cliente = (7.0 - 3.5 * k) * self.mult_intervalo * random.uniform(0.8, 1.2)

        # Paciência
        for i, c in enumerate(self.clientes):
            chegou = abs(c.x - X_FILA[min(i, 3)]) < 4
            if c.estado == "balcao" and chegou:
                c.paciencia -= dt
            elif c.estado == "fila":
                c.paciencia -= dt * DRENO_FILA
            if c.paciencia <= 0:
                self._embora_bravo(c)

        # Quem foi embora sai da fila
        for c in list(self.clientes):
            if c.estado in ("feliz", "bravo"):
                self.clientes.remove(c)
                self.saindo.append(c)
        self._promover()
        self._animar(dt)

    def _animar(self, dt):
        # Clientes andando até o seu lugar
        for i, c in enumerate(self.clientes):
            c.t += dt
            alvo = X_FILA[min(i, 3)]
            passo = 320 * dt
            c.x += max(-passo, min(passo, alvo - c.x))
        for c in self.saindo:
            c.t += dt
            c.pulo = max(0.0, c.pulo - dt * 1.5)
            if c.t > 0.4:
                c.x -= 560 * dt
            if c.estado == "bravo" and random.random() < dt * 14:
                self.particulas.explodir((c.x + random.uniform(-16, 16), 300), [(200, 200, 205), (150, 150, 160)],
                                         1, 60, 0.8, (5, 9), gravidade=-160)
            if c.estado == "feliz" and random.random() < dt * 6:
                self.textos.adicionar("♥", (c.x + random.uniform(-30, 30), 300), (255, 110, 150), 16)
        self.saindo = [c for c in self.saindo if c.x > -120]

        # Ingredientes caindo no prato (com quique e squash)
        for p in self.pilha:
            if p[1] < 0 or p[2] != 0:
                p[2] += 5200 * dt
                p[1] += p[2] * dt
                if p[1] >= 0:
                    p[1] = 0.0
                    if p[2] > 300:
                        p[2] = -p[2] * 0.22
                        p[3] = 1.0
                    else:
                        p[2] = 0.0
            p[3] = max(0.0, p[3] - dt * 6)

        if self.entregando:
            self.entregando[2] += dt / 0.35
            if self.entregando[2] >= 1:
                self.entregando = None

        self.tremer_pilha = max(0.0, self.tremer_pilha - dt)
        self.chef_pulo = max(0.0, self.chef_pulo - dt)
        self.chef_nao = max(0.0, self.chef_nao - dt)
        self.estrela_quebrando = max(0.0, self.estrela_quebrando - dt)
        msg, t = self.aviso
        self.aviso = (msg, max(0.0, t - dt))

    def _fim(self):
        linhas = [t("PONTOS: {n}", n=self.pontos),
                  t("CLIENTES: {n}  •  ESTRELAS: {e}/{total}", n=self.atendidos, e=self.estrelas, total=ESTRELAS)]
        if self.fim_motivo == "estrelas":
            self.terminar(titulo=t("LANCHONETE FECHADA!"), linhas=linhas)
        elif self.estrelas == ESTRELAS:
            self.terminar(venceu=True, titulo=t("EXPEDIENTE PERFEITO!"), linhas=linhas)
        else:
            self.terminar(titulo=t("FIM DO EXPEDIENTE!"), linhas=linhas)

    # --------------------------------------------------------
    # DESENHO
    # --------------------------------------------------------

    def desenhar_jogo(self, tela):
        tela.blit(self.fundo(self.jogador), (0, 0))
        self._desenhar_letreiro(tela)

        # Clientes (atrás do balcão): a fila de trás para a frente
        for c in self.saindo:
            self._desenhar_cliente(tela, c, 0)
        for i in range(len(self.clientes) - 1, -1, -1):
            self._desenhar_cliente(tela, self.clientes[i], i)

        self._desenhar_balcao(tela)
        self._desenhar_potes(tela)
        self._desenhar_suco_e_lixo(tela)
        self._desenhar_chef(tela)
        self._desenhar_pilha(tela)
        self._desenhar_pedido(tela)

        self.particulas.desenhar(tela)
        self.textos.desenhar(tela)

        msg, t = self.aviso
        if t > 0 and msg and self.estado == "jogando":
            sup = ui.texto(msg, 14, (255, 120, 120) if "!" in msg else BRANCO)
            caixa = sup.get_rect(center=(PRATO[0], 410)).inflate(24, 16)
            ui.painel(tela, caixa, (20, 24, 40), (255, 120, 120), 10, 2, sombra=False)
            tela.blit(sup, sup.get_rect(center=caixa.center))

    def _desenhar_letreiro(self, tela):
        nome = (self.jogador.nome or "OVO").upper()
        texto = t("LANCHONETE DO {nome}", nome=nome)
        if self._placa_nome is None or self._placa_nome[0] != texto:
            tam = 20
            while tam > 12 and ui.texto(texto, tam).get_width() > 600:
                tam -= 2
            frente = ui.texto(texto, tam, (255, 90, 110), sombra=False)
            w, h = frente.get_width() + 60, frente.get_height() + 30
            placa = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.rect(placa, (50, 25, 45), (0, 0, w, h), border_radius=14)
            pygame.draw.rect(placa, (255, 80, 100), (4, 4, w - 8, h - 8), 3, border_radius=12)
            brilho = pygame.Surface((w, h), pygame.SRCALPHA)
            glow = ui.texto(texto, tam, (255, 80, 100, 90), sombra=False)
            for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
                brilho.blit(glow, glow.get_rect(center=(w // 2 + dx, h // 2 + dy)))
            brilho.set_alpha(110)
            placa.blit(brilho, (0, 0))
            placa.blit(frente, frente.get_rect(center=(w // 2, h // 2)))
            apagada = placa.copy()
            apagada.fill((140, 140, 140), special_flags=pygame.BLEND_RGB_MULT)
            self._placa_nome = (texto, placa, apagada)
        _, placa, apagada = self._placa_nome
        # Neon piscando de vez em quando
        pisca = (self.tempo % 7.0) > 6.75 and int(self.tempo * 20) % 2 == 0
        sup = apagada if pisca else placa
        tela.blit(sup, sup.get_rect(midtop=(LARGURA // 2, 72)))

    def _desenhar_cliente(self, tela, c, indice):
        balcao = indice == 0
        altura = 120 if balcao else 96
        pe = BALCAO_Y + 18
        dy = 0.0
        if c.estado == "feliz":
            dy = -abs(math.sin(c.t * 10)) * 26 * max(0.3, c.pulo)
        elif abs(c.x - X_FILA[min(indice, 3)]) > 3 or c.estado in ("bravo",) and c.t > 0.4:
            dy = -abs(math.sin(c.t * 12)) * 6        # andando
        cx = c.x
        impaciente = c.estado in ("balcao", "fila") and c.frac < 0.25
        if impaciente:
            cx += math.sin(self.tempo * 40 + c.fase) * 2
        cy = pe - altura / 2 + dy
        bravo = c.estado == "bravo"

        if c.tipo == "ovo":
            ang = math.sin(c.t * 30) * 5 if c.estado == "bravo" else 0
            if bravo:
                self._ovo_vermelho(tela, (cx, cy), altura, c.aparencia, ang)
            else:
                self.jogador.desenhar(tela, (cx, cy), altura, aparencia=c.aparencia)
            topo = cy - altura / 2
        elif c.tipo == "robert":
            topo = self._desenhar_robert(tela, cx, pe + dy, altura, bravo)
        else:
            topo = self._desenhar_toto(tela, cx, pe + dy, altura, bravo)

        # Mãozinhas no balcão
        if c.tipo != "toto":
            for lado in (-1, 1):
                pygame.draw.circle(tela, (70, 60, 70), (int(cx + lado * altura * 0.36), BALCAO_Y + 2), 9)
                pygame.draw.circle(tela, (255, 220, 190) if c.tipo == "robert" else _cor_mao(self, c),
                                   (int(cx + lado * altura * 0.36), BALCAO_Y + 2), 7)

        # Barra de paciência de quem está na fila
        if c.estado == "fila" and abs(c.x - X_FILA[min(indice, 3)]) < 30:
            r = pygame.Rect(0, 0, 60, 10)
            r.midbottom = (int(cx), int(topo - 12))
            pygame.draw.rect(tela, (40, 40, 50), r.inflate(4, 4), border_radius=4)
            cor = ui.misturar((230, 60, 60), (90, 210, 90), c.frac)
            pygame.draw.rect(tela, cor, (r.x, r.y, int(r.w * c.frac), r.h), border_radius=3)

        # Veia de raiva de quem está sem paciência
        if impaciente and int(self.tempo * 4) % 2 == 0:
            vx, vy = int(cx + altura * 0.3), int(topo + 8)
            for ang in (0.8, 2.4, 3.9, 5.5):
                x1, y1 = vx + math.cos(ang) * 4, vy + math.sin(ang) * 4
                x2, y2 = vx + math.cos(ang) * 11, vy + math.sin(ang) * 11
                pygame.draw.line(tela, (40, 20, 20), (x1, y1), (x2, y2), 6)
                pygame.draw.line(tela, (230, 50, 50), (x1, y1), (x2, y2), 3)

        # Fumacinha de raiva
        if c.estado == "bravo" and int(c.t * 6) % 2 == 0:
            for lado in (-1, 1):
                pygame.draw.circle(tela, (210, 210, 215), (int(cx + lado * 20), int(topo - 10)), 7)

    def _ovo_vermelho(self, tela, centro, altura, aparencia, angulo):
        """Ovo cliente vermelho de raiva (mesma posição de jogador.desenhar)."""
        sup = self.jogador.avatar(altura, aparencia).copy()
        sup.fill((255, 140, 140), special_flags=pygame.BLEND_RGB_MULT)
        sup.fill((90, 0, 0), special_flags=pygame.BLEND_RGB_ADD)
        escala = sup.get_width() / 100
        dx = (self.jogador.OVO_RECT.centerx - 50) * escala
        dy = (self.jogador.OVO_RECT.centery - 50) * escala
        if angulo:
            sup = pygame.transform.rotate(sup, angulo)
        tela.blit(sup, sup.get_rect(center=(round(centro[0] - dx), round(centro[1] - dy))))

    def _desenhar_robert(self, tela, cx, pe, altura, bravo):
        """ROBERT: palito com boné arco-íris."""
        esc = altura / 104
        r = int(altura * 0.3)
        cabeca_y = pe - altura * 0.66
        pele = (255, 190, 170) if bravo else (255, 220, 190)
        # Corpo (palito) e braços
        pygame.draw.line(tela, (40, 40, 50), (cx, cabeca_y + r), (cx, pe), max(2, int(5 * esc)))
        for lado in (-1, 1):
            pygame.draw.line(tela, (40, 40, 50), (cx, cabeca_y + r + 14 * esc),
                             (cx + lado * altura * 0.36, BALCAO_Y + 2), max(2, int(4 * esc)))
        pygame.draw.circle(tela, (60, 50, 50), (int(cx), int(cabeca_y)), r + 2)
        pygame.draw.circle(tela, pele, (int(cx), int(cabeca_y)), r)
        # Olhos e boca
        for lado in (-1, 1):
            pygame.draw.circle(tela, (30, 30, 40), (int(cx + lado * 9 * esc), int(cabeca_y)), max(2, int(3 * esc)))
        if bravo:
            pygame.draw.arc(tela, (120, 40, 40), (cx - 9 * esc, cabeca_y + 8 * esc, 18 * esc, 12 * esc), 0.3, 2.8, 2)
            for lado in (-1, 1):
                pygame.draw.line(tela, (30, 30, 40), (cx + lado * 4 * esc, cabeca_y - 7 * esc),
                                 (cx + lado * 13 * esc, cabeca_y - 10 * esc), 2)
        else:
            pygame.draw.arc(tela, (120, 40, 40), (cx - 10 * esc, cabeca_y + 1 * esc, 20 * esc, 14 * esc), 3.4, 6.0, 2)
        # Boné arco-íris
        cores = [(230, 60, 60), (255, 150, 40), (255, 220, 60), (90, 200, 90), (60, 150, 230), (140, 90, 210)]
        y_bone = cabeca_y - r * 0.3
        pygame.draw.circle(tela, (60, 50, 50), (int(cx), int(y_bone)), r + 4, draw_top_left=True,
                           draw_top_right=True)
        for k, cor in enumerate(cores):
            rr = r + 2 - k * (r / 7)
            pygame.draw.circle(tela, cor, (int(cx), int(y_bone)), max(2, int(rr)),
                               draw_top_left=True, draw_top_right=True)
        aba = pygame.Rect(cx - 2, y_bone - 3, r * 1.45, max(4, int(7 * esc)))
        pygame.draw.rect(tela, (60, 50, 50), aba.inflate(4, 4), border_radius=4)
        pygame.draw.rect(tela, (230, 60, 60), aba, border_radius=3)
        return y_bone - r

    def _desenhar_toto(self, tela, cx, pe, altura, bravo):
        """TOTÓ: cachorrinho com as patas no balcão."""
        esc = altura / 90
        cy = pe - 60 * esc
        cor = (190, 130, 80)
        escura = (120, 75, 40)
        # Patas
        for lado in (-1, 1):
            pygame.draw.ellipse(tela, escura, (cx + lado * 26 * esc - 12 * esc, BALCAO_Y - 8, 24 * esc, 16))
            pygame.draw.ellipse(tela, cor, (cx + lado * 26 * esc - 10 * esc, BALCAO_Y - 6, 20 * esc, 12))
        # Orelhas
        for lado in (-1, 1):
            orelha = pygame.Rect(0, 0, 20 * esc, 40 * esc)
            orelha.midtop = (cx + lado * 30 * esc, cy - 26 * esc)
            pygame.draw.ellipse(tela, escura, orelha)
        cabeca = pygame.Rect(0, 0, 64 * esc, 56 * esc)
        cabeca.center = (cx, cy)
        pygame.draw.ellipse(tela, escura, cabeca.inflate(4, 4))
        pygame.draw.ellipse(tela, cor, cabeca)
        focinho = pygame.Rect(0, 0, 34 * esc, 24 * esc)
        focinho.center = (cx, cy + 12 * esc)
        pygame.draw.ellipse(tela, (240, 210, 170), focinho)
        pygame.draw.ellipse(tela, (30, 30, 30), (cx - 6 * esc, cy + 4 * esc, 12 * esc, 9 * esc))
        for lado in (-1, 1):
            pygame.draw.circle(tela, (30, 30, 30), (int(cx + lado * 13 * esc), int(cy - 6 * esc)), max(2, int(4 * esc)))
            if bravo:
                pygame.draw.line(tela, (30, 30, 30), (cx + lado * 6 * esc, cy - 14 * esc),
                                 (cx + lado * 18 * esc, cy - 17 * esc), 2)
        if not bravo:
            pygame.draw.ellipse(tela, (240, 100, 120), (cx - 5 * esc, cy + 18 * esc, 10 * esc, 12 * esc))
        # Coleira
        pygame.draw.rect(tela, (60, 150, 230), (cx - 22 * esc, cy + 25 * esc, 44 * esc, 7 * esc), border_radius=3)
        pygame.draw.circle(tela, AMARELO, (int(cx), int(cy + 33 * esc)), max(2, int(4 * esc)))
        return cy - 30 * esc

    def _desenhar_balcao(self, tela):
        pygame.draw.rect(tela, (180, 50, 50), (0, BALCAO_Y, LARGURA, BALCAO_FIM - BALCAO_Y))
        for x in range(0, LARGURA, 64):
            pygame.draw.rect(tela, (200, 64, 64), (x + 8, BALCAO_Y + 22, 48, BALCAO_FIM - BALCAO_Y - 34),
                             border_radius=6)
        pygame.draw.rect(tela, (220, 220, 230), (0, BALCAO_Y - 4, LARGURA, 14))
        pygame.draw.line(tela, (255, 255, 255), (0, BALCAO_Y - 2), (LARGURA, BALCAO_Y - 2), 2)
        pygame.draw.line(tela, (150, 150, 165), (0, BALCAO_Y + 10), (LARGURA, BALCAO_Y + 10), 2)
        pygame.draw.rect(tela, (220, 220, 230), (0, BALCAO_FIM - 6, LARGURA, 6))

    def _desenhar_potes(self, tela):
        for i, x in enumerate(POTES_X):
            sel = i == self.cursor and self.estado == "jogando"
            y = POTE_Y - (8 if sel else 0)
            corpo = pygame.Rect(0, 0, POTE_W, POTE_H - 18)
            corpo.midtop = (x, y + 18)
            if sel:
                pygame.draw.rect(tela, AMARELO, corpo.inflate(12, 34).move(0, -8), border_radius=16)
            # Vidro
            pygame.draw.rect(tela, (80, 90, 110), corpo.inflate(4, 4), border_radius=12)
            pygame.draw.rect(tela, (215, 235, 245), corpo, border_radius=12)
            # Ingrediente dentro
            tipo = "pao_topo" if INGREDIENTES[i] == "pao" else INGREDIENTES[i]
            s = _camada(tipo, LARG_POTE)
            tela.blit(s, s.get_rect(center=(x, corpo.y + 30)))
            if tipo in ("tomate", "cebola", "alface", "queijo"):
                tela.blit(s, s.get_rect(center=(x, corpo.y + 42)))
            pygame.draw.line(tela, (255, 255, 255), (corpo.x + 10, corpo.y + 8), (corpo.x + 10, corpo.bottom - 10), 3)
            # Etiqueta com o nome
            nome = t(NOMES[INGREDIENTES[i]])
            etq = pygame.Rect(0, 0, POTE_W - 12, 18)
            etq.midbottom = (x, corpo.bottom - 6)
            pygame.draw.rect(tela, (255, 250, 235), etq, border_radius=4)
            pygame.draw.rect(tela, (150, 120, 90), etq, 1, border_radius=4)
            ui.desenhar_texto(tela, nome, (x, etq.centery + 1), 10, (120, 60, 40), "center", sombra=False)
            # Tampa com o número
            tampa = pygame.Rect(0, 0, POTE_W + 6, 20)
            tampa.midbottom = (x, corpo.y + 4)
            cor_tampa = [(230, 170, 80), (150, 90, 50), (240, 190, 40), (90, 180, 70), (220, 70, 60),
                         (190, 150, 200)][i]
            pygame.draw.rect(tela, ui.escurecer(cor_tampa, 70), tampa.inflate(4, 4), border_radius=6)
            pygame.draw.rect(tela, cor_tampa, tampa, border_radius=6)
            pygame.draw.circle(tela, (30, 30, 40), (x, tampa.centery), 11)
            ui.desenhar_texto(tela, str(i + 1), (x + 1, tampa.centery + 1), 12, BRANCO, "center", sombra=False)

        # Setinha em cima do pote escolhido
        if self.estado == "jogando" and self.cursor < 6:
            x = POTES_X[self.cursor]
            y = POTE_Y - 30 + math.sin(self.tempo * 8) * 3
            pygame.draw.polygon(tela, (30, 30, 40), [(x - 12, y - 12), (x + 12, y - 12), (x, y + 2)])
            pygame.draw.polygon(tela, AMARELO, [(x - 9, y - 10), (x + 9, y - 10), (x, y - 1)])

    def _desenhar_suco_e_lixo(self, tela):
        # Máquina de suco de limão
        r = SUCO_RECT
        sel = self.cursor == 6 and self.estado == "jogando"
        if sel:
            pygame.draw.rect(tela, AMARELO, r.inflate(12, 12), border_radius=18)
        pygame.draw.rect(tela, (70, 80, 100), r.inflate(4, 4), border_radius=14)
        pygame.draw.rect(tela, (240, 240, 245), r, border_radius=14)
        tanque = pygame.Rect(r.x + 14, r.y + 36, r.w - 28, 70)
        pygame.draw.rect(tela, (200, 230, 240), tanque, border_radius=10)
        nivel = tanque.inflate(-8, -20).move(0, 8)
        pygame.draw.rect(tela, (225, 240, 90), nivel, border_radius=8)
        for k in range(3):
            lx = nivel.x + 16 + k * 24
            ly = nivel.y + 12 + math.sin(self.tempo * 2 + k) * 4
            pygame.draw.circle(tela, (120, 170, 40), (int(lx), int(ly)), 8)
            pygame.draw.circle(tela, (240, 250, 150), (int(lx), int(ly)), 6)
        pygame.draw.rect(tela, (80, 90, 110), tanque, 3, border_radius=10)
        ui.desenhar_texto(tela, t("SUCO"), (r.centerx, r.y + 18), 12, (60, 120, 40), "center", sombra=False)
        pygame.draw.rect(tela, (90, 90, 100), (r.centerx - 8, tanque.bottom, 16, 18))
        pygame.draw.rect(tela, (70, 80, 100), (r.x + 16, r.bottom - 24, r.w - 32, 8), border_radius=3)
        pygame.draw.circle(tela, (30, 30, 40), (r.centerx, r.bottom - 48), 12)
        ui.desenhar_texto(tela, "7", (r.centerx + 1, r.bottom - 47), 12, BRANCO, "center", sombra=False)

        # Lixeira
        l = LIXO_RECT
        pygame.draw.rect(tela, (60, 64, 76), l.inflate(4, 4), border_radius=8)
        pygame.draw.rect(tela, (140, 146, 160), l, border_radius=8)
        for k in range(3):
            x = l.x + 14 + k * 17
            pygame.draw.line(tela, (110, 116, 130), (x, l.y + 14), (x, l.bottom - 10), 3)
        tampa = pygame.Rect(l.x - 6, l.y - 12, l.w + 12, 14)
        pygame.draw.rect(tela, (60, 64, 76), tampa.inflate(4, 4), border_radius=6)
        pygame.draw.rect(tela, (170, 176, 190), tampa, border_radius=6)
        pygame.draw.rect(tela, (60, 64, 76), (l.centerx - 10, tampa.y - 8, 20, 8), border_radius=3)
        pygame.draw.circle(tela, (30, 30, 40), (l.centerx, l.centery + 6), 12)
        ui.desenhar_texto(tela, "↑", (l.centerx + 1, l.centery + 7), 12, BRANCO, "center", sombra=False)

    def _desenhar_chef(self, tela):
        altura = 92
        x, y = CHEF
        dy = -math.sin(self.chef_pulo / 0.25 * math.pi) * 12 if self.chef_pulo > 0 else 0
        ang = -8 if self.chef_pulo > 0 else 0
        if self.chef_nao > 0:
            ang = math.sin(self.chef_nao * 30) * 10
        sombra = pygame.Rect(0, 0, 80, 14)
        sombra.center = (x, y + altura / 2 + 4)
        pygame.draw.ellipse(tela, (100, 104, 118), sombra)
        centro = (x, y + dy)
        self.jogador.desenhar(tela, centro, altura, angulo=ang)
        if not self.app.save["equipado"].get("cabeca"):
            _chapeu_chef(tela, centro, altura, ang)
        # Aventalzinho
        av = pygame.Rect(0, 0, altura * 0.46, altura * 0.26)
        av.midbottom = (x, y + dy + altura * 0.47)
        pygame.draw.rect(tela, (255, 255, 255), av, border_bottom_left_radius=12, border_bottom_right_radius=12)
        pygame.draw.rect(tela, (200, 60, 60), av, 2, border_bottom_left_radius=12, border_bottom_right_radius=12)

    def _desenhar_pilha(self, tela):
        cx = PRATO[0]
        if self.tremer_pilha > 0:
            cx += math.sin(self.tempo * 50) * 7 * min(1.0, self.tremer_pilha * 3)
        y = BASE_PILHA
        n = len(self.pilha)
        for i, (tipo, queda, _, squash) in enumerate(self.pilha):
            s = _camada(tipo, LARG_PRATO, self.errado)
            _, esp, pend = ALTURAS[tipo]
            balanco = math.sin(self.tempo * 2.5) * i * 0.8
            if squash > 0 and i == n - 1:
                w, h = s.get_size()
                s = pygame.transform.smoothscale(s, (int(w * (1 + 0.12 * squash)), max(1, int(h * (1 - 0.25 * squash)))))
            tela.blit(s, s.get_rect(midbottom=(int(cx + balanco), int(y + pend * LARG_PRATO + queda))))
            y -= esp * LARG_PRATO

        if self.errado and int(self.tempo * 4) % 2 == 0:
            yy = (BASE_PILHA + y) / 2
            for k in (-1, 1):
                pygame.draw.line(tela, (40, 20, 20), (cx - 30, yy - 30 * k), (cx + 30, yy + 30 * k), 14)
            for k in (-1, 1):
                pygame.draw.line(tela, (230, 50, 50), (cx - 28, yy - 28 * k), (cx + 28, yy + 28 * k), 9)

        if self.suco_pronto:
            s = _copo(34)
            tela.blit(s, s.get_rect(midbottom=(COPO_POS[0], COPO_POS[1] + 22)))

        # Lanche voando até o cliente
        if self.entregando:
            camadas, suco, k = self.entregando
            x0, y0 = PRATO[0], BASE_PILHA
            x1, y1 = X_BALCAO, BALCAO_Y + 4
            px = x0 + (x1 - x0) * k
            py = y0 + (y1 - y0) * k - math.sin(k * math.pi) * 80
            esc = 1 - 0.35 * k
            larg = int(LARG_PRATO * esc)
            yy = py
            for tipo in camadas:
                s = _camada(tipo, LARG_PRATO)
                s = pygame.transform.smoothscale(s, (larg, max(1, int(s.get_height() * esc))))
                _, esp, pend = ALTURAS[tipo]
                tela.blit(s, s.get_rect(midbottom=(int(px), int(yy + pend * larg))))
                yy -= esp * larg

    def _desenhar_pedido(self, tela):
        c = self.atual
        if c is None:
            return
        itens = list(c.pedido) + (["suco"] if c.suco else [])
        feitos = len(self.pilha) if not self.errado else 0
        linha_h = 22 if len(itens) <= 7 else 20
        altura = sum(28 if i == "pao_topo" else linha_h for i in itens) + 84
        b = pygame.Rect(BALAO_X, BALAO_BAIXO - altura, BALAO_W, altura)

        # Balão com rabinho apontando para o cliente
        ponta = (X_BALCAO - 58, b.bottom - 44)
        pygame.draw.polygon(tela, (60, 60, 70), [(b.right - 4, b.bottom - 96), (b.right - 4, b.bottom - 40),
                                                 (ponta[0] + 4, ponta[1] + 2)])
        ui.painel(tela, b, (255, 255, 255), (60, 60, 70), 18, 4)
        pygame.draw.polygon(tela, (255, 255, 255), [(b.right - 6, b.bottom - 90), (b.right - 6, b.bottom - 46),
                                                    ponta])
        ui.desenhar_texto(tela, t("PEDIDO"), (b.x + 18, b.y + 16), 12, (180, 60, 60), "topleft", sombra=False)
        y = b.bottom - 44
        for k, tipo in enumerate(itens):
            if tipo == "suco":
                feito = self.suco_pronto
                proximo = not feito and feitos >= len(c.pedido)
            else:
                feito = k < feitos
                proximo = k == feitos and not self.errado
            h = 28 if tipo == "pao_topo" else linha_h
            meio = y - h / 2
            # Ícone
            if tipo == "suco":
                s = _copo(16)
            else:
                s = _camada(tipo, LARG_ICONE)
            tela.blit(s, s.get_rect(center=(b.x + 76, int(meio))))
            # Texto: tecla + nome
            if feito:
                cor = (90, 170, 90)
            elif proximo:
                cor = (30, 30, 40)
            else:
                cor = (140, 140, 150)
            msg = f"{TECLA_DE[tipo]} {t(NOMES[tipo])}"
            ui.desenhar_texto(tela, msg, (b.x + 130, int(meio) + 1), 12, cor, "midleft", sombra=False)
            if proximo:
                ui.desenhar_texto(tela, "▶", (b.x + 26, int(meio) + 1), 12, (230, 60, 60), "midleft", sombra=False)
            if feito:
                pygame.draw.line(tela, (90, 170, 90), (b.x + 22, meio), (b.x + 28, meio + 6), 3)
                pygame.draw.line(tela, (90, 170, 90), (b.x + 28, meio + 6), (b.x + 38, meio - 6), 3)
            y -= h

        # Barra de paciência
        barra = pygame.Rect(b.x + 18, b.bottom - 26, b.w - 36, 12)
        pygame.draw.rect(tela, (60, 60, 70), barra.inflate(4, 4), border_radius=6)
        pygame.draw.rect(tela, (220, 220, 225), barra, border_radius=5)
        cor = ui.misturar((230, 60, 60), (90, 210, 90), c.frac)
        if c.frac < 0.3 and int(self.tempo * 6) % 2 == 0:
            cor = (255, 120, 120)
        pygame.draw.rect(tela, cor, (barra.x, barra.y, int(barra.w * c.frac), barra.h), border_radius=5)

    def desenhar_hud(self, tela):
        caixa = pygame.Rect(12, 12, 420, 48)
        ui.painel(tela, caixa, (20, 24, 40), BRANCO, 12, 3, sombra=False)
        ui.desenhar_texto(tela, t("PONTOS: {n}", n=self.pontos), (caixa.x + 16, caixa.centery), 14,
                          AMARELO, "midleft")
        rec = self.recorde()
        if rec is not None:
            ui.desenhar_texto(tela, t("RECORDE: {n}", n=rec), (caixa.x + 236, caixa.centery), 12,
                              (180, 200, 255), "midleft")

        # Relógio do expediente
        caixa = pygame.Rect(0, 12, 150, 48)
        caixa.right = LARGURA - 76
        resta = int(math.ceil(EXPEDIENTE - self.relogio))
        pouco = resta <= 15
        cor = (255, 110, 110) if pouco and int(self.tempo * 4) % 2 == 0 else BRANCO
        ui.painel(tela, caixa, (20, 24, 40), cor, 12, 3, sombra=False)
        pygame.draw.circle(tela, cor, (caixa.x + 24, caixa.centery + 1), 11, 3)
        pygame.draw.line(tela, cor, (caixa.x + 24, caixa.centery + 1), (caixa.x + 24, caixa.centery - 5), 3)
        pygame.draw.line(tela, cor, (caixa.x + 24, caixa.centery + 1), (caixa.x + 29, caixa.centery + 1), 3)
        ui.desenhar_texto(tela, f"{resta // 60}:{resta % 60:02d}", (caixa.right - 14, caixa.centery + 1), 16,
                          cor, "midright")

        # Estrelas da lanchonete
        caixa2 = pygame.Rect(0, 12, 146, 48)
        caixa2.right = caixa.x - 10
        ui.painel(tela, caixa2, (20, 24, 40), BRANCO, 12, 3, sombra=False)
        for i in range(ESTRELAS):
            c = (caixa2.x + 28 + i * 45, caixa2.centery + 1)
            if i < self.estrelas:
                ui.estrela(tela, c, 17, AMARELO)
            else:
                ui.estrela(tela, c, 17, (70, 70, 90))
                if i == self.estrelas and self.estrela_quebrando > 0:
                    k = 1 - self.estrela_quebrando
                    ui.estrela(tela, (c[0], c[1] + k * 40), 17 * (1 - k * 0.5), (255, 160, 60), k * 3)


def _cor_mao(jogo, c):
    """Cor da mãozinha do cliente (a cor do ovo dele)."""
    return jogo.jogador.cor_do_ovo(c.aparencia[0]) if c.aparencia else (255, 220, 190)


def _chapeu_chef(tela, centro, altura, angulo=0.0):
    """Chapéu de cozinheiro por cima da cabeça do ovo."""
    cx, cy = centro
    a = math.radians(-angulo)
    topo = altura * 0.5

    def pt(dx, dy):
        # gira em torno do centro do ovo
        x, y = dx, dy - topo
        return (cx + x * math.cos(a) - y * math.sin(a), cy + x * math.sin(a) + y * math.cos(a))

    w = altura * 0.62
    faixa_h = altura * 0.2
    faixa = [pt(-w / 2, 4), pt(w / 2, 4), pt(w / 2, 4 - faixa_h), pt(-w / 2, 4 - faixa_h)]
    for dx, dy, r in ((-w * 0.32, -faixa_h - altura * 0.1, altura * 0.17), (w * 0.32, -faixa_h - altura * 0.1,
                                                                           altura * 0.17),
                      (0, -faixa_h - altura * 0.2, altura * 0.21)):
        p = pt(dx, dy)
        pygame.draw.circle(tela, (150, 150, 165), (int(p[0]), int(p[1])), int(r) + 2)
    for dx, dy, r in ((-w * 0.32, -faixa_h - altura * 0.1, altura * 0.17), (w * 0.32, -faixa_h - altura * 0.1,
                                                                           altura * 0.17),
                      (0, -faixa_h - altura * 0.2, altura * 0.21)):
        p = pt(dx, dy)
        pygame.draw.circle(tela, (255, 255, 255), (int(p[0]), int(p[1])), int(r))
    pygame.draw.polygon(tela, (255, 255, 255), faixa)
    pygame.draw.polygon(tela, (150, 150, 165), faixa, 2)
    pygame.draw.line(tela, (225, 225, 235), pt(-w / 2 + 4, 4 - faixa_h * 0.5), pt(w / 2 - 4, 4 - faixa_h * 0.5), 2)
