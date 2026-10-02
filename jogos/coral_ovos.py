import math
import random

import pygame

from settings import *
from core import ui
from core import sintetizador as sint
from core.jogador import Jogador
from jogos.base import MiniJogo

# ============================================================
# CORAL DOS OVOS
# ============================================================
# Você é o MAESTRO! Quatro ovos cantores (a família: VERDE, AZUL,
# BRANCO e VERMELHO) cantam uma melodia que cresce uma nota por
# rodada. Repita a sequência apertando a POSIÇÃO de quem cantou.
# No modo MALUCO, a cada 5 rodadas os cantores trocam de lugar!

CENTRO = (512, 400)                 # o maestro fica no meio do palco
POSICOES = [(512, 210), (290, 400), (734, 400), (512, 590)]   # cima, esq, dir, baixo
NOMES_POSICAO = ["DE CIMA", "DA ESQUERDA", "DA DIREITA", "DE BAIXO"]
SETAS = ["↑", "←", "→", "↓"]
LETRAS = ["W", "A", "D", "S"]

ALTURA_CANTOR = 100
ALTURA_MAESTRO = 90
RAIO_CLIQUE = 72

# Cantores na posição inicial: (cor do ovo, nota que canta, cor da luz)
CANTORES = [
    (0, "Eb5", (150, 235, 60)),     # VERDE    - cima
    (1, "G4", (70, 200, 255)),      # AZUL     - esquerda
    (3, "Bb4", (255, 90, 120)),     # VERMELHO - direita
    (2, "Eb4", (255, 255, 255)),    # BRANCO   - baixo
]
# Cabelo, olho e boca de cada cantor (a "família" do ovo)
PARTES_CANTORES = [(1, 0, 1), (5, 1, 4), (0, 2, 5), (3, 1, 3)]

TECLAS = {
    pygame.K_UP: 0, pygame.K_w: 0, pygame.K_KP8: 0,
    pygame.K_LEFT: 1, pygame.K_a: 1, pygame.K_KP4: 1,
    pygame.K_RIGHT: 2, pygame.K_d: 2, pygame.K_KP6: 2,
    pygame.K_DOWN: 3, pygame.K_s: 3, pygame.K_KP2: 3,
}

VIDAS = [3, 1, 1]                   # FÁCIL, NORMAL, MALUCO
META = [15, 20, 20]                 # rodadas para completar o concerto
TEMPO_RESPOSTA = 5.0                # segundos por nota na vez do jogador
DUR_TROCA = 0.8
TEMPO_PREPARAR = 0.8
TEMPO_RODADA_OK = 1.1
TEMPO_ERRO = 1.4
DUR_VITORIA = 2.4

PALCO_TOPO = 236                    # onde começa o piso de madeira
PALCO_BASE = 668                    # beirada do palco (depois vem a plateia)


def _intervalo(rodada, opcao):
    """Tempo de cada nota na demonstração (fica mais rápido)."""
    t = max(0.25, 0.55 - 0.02 * (rodada - 1))
    if opcao == 0:
        t = max(0.45, t + 0.2)          # FÁCIL: sempre mais devagar
    return t


def _angulo_de(pos):
    return math.atan2(pos[1] - CENTRO[1], pos[0] - CENTRO[0])


def _raio_de(pos):
    return math.hypot(pos[0] - CENTRO[0], pos[1] - CENTRO[1])


# ============================================================
# NOTAS DOS CANTORES (geradas uma vez, com cache)
# ============================================================

_sons_notas = {}


def _som_nota(nome):
    """Sino + triângulo, 0.45 s (arpejo de Mi bemol)."""
    if nome in _sons_notas:
        return _sons_notas[nome]
    snd = None
    try:
        f = sint.frequencia(nome)
        buf = sint.buffer_vazio(0.5)
        n = int(0.45 * sint.TAXA)
        sint.nota(buf, 0, n, f, "sino", 0.55, envelope="pluck")
        sint.nota(buf, 0, n, f, "triangulo", 0.3)
        sint.nota(buf, 0, int(0.2 * sint.TAXA), f * 2, "sino", 0.12, envelope="pluck")
        snd = pygame.mixer.Sound(file=sint.wav_em_memoria(sint.para_pcm(buf, 0.7)))
    except (pygame.error, ValueError):
        snd = None
    _sons_notas[nome] = snd
    return snd


# ============================================================
# DESENHOS PEQUENOS
# ============================================================

def _nota_musical(tela, pos, tam, cor):
    """Uma notinha musical (colcheia) desenhada à mão."""
    x, y = int(pos[0]), int(pos[1])
    r = max(3, tam // 4)
    esp = max(2, tam // 8)
    for dx, dy, c in ((2, 2, (20, 10, 20)), (0, 0, cor)):
        pygame.draw.ellipse(tela, c, (x - r - 2 + dx, y - r + dy, r * 2 + 3, r * 2))
        haste = x + r + dx
        pygame.draw.line(tela, c, (haste, y + dy), (haste, y - tam + dy), esp)
        pygame.draw.line(tela, c, (haste, y - tam + dy), (haste + r + 3, y - tam + r + 3 + dy), esp)


def _flor(tela, pos, raio, ang, cor):
    x, y = pos
    for k in range(5):
        a = ang + k * math.tau / 5
        pygame.draw.circle(tela, cor, (int(x + math.cos(a) * raio), int(y + math.sin(a) * raio)),
                           max(2, int(raio * 0.75)))
    pygame.draw.circle(tela, (255, 220, 60), (int(x), int(y)), max(2, int(raio * 0.6)))


_cones = {}


def _cone(indice):
    """Luz do holofote apontando para uma posição (pré-desenhada)."""
    if indice in _cones:
        return _cones[indice]
    alvo = POSICOES[indice]
    lx = int(alvo[0] * 0.75 + CENTRO[0] * 0.25)
    ly = 64
    pe = alvo[1] + 56
    larg_base = 190
    x0 = min(lx - 20, alvo[0] - larg_base // 2) - 4
    x1 = max(lx + 20, alvo[0] + larg_base // 2) + 4
    sup = pygame.Surface((x1 - x0, pe + 26 - ly), pygame.SRCALPHA)
    pontos = [(lx - 14 - x0, 0), (lx + 14 - x0, 0),
              (alvo[0] + larg_base // 2 - x0, pe - ly), (alvo[0] - larg_base // 2 - x0, pe - ly)]
    pygame.draw.polygon(sup, (255, 240, 180, 60), pontos)
    pygame.draw.ellipse(sup, (255, 240, 180, 70),
                        (alvo[0] - larg_base // 2 - x0, pe - ly - 22, larg_base, 44))
    _cones[indice] = (sup, (x0, ly))
    return _cones[indice]


class CoralOvos(MiniJogo):

    ID = "coral_ovos"
    TITULO = "CORAL DOS OVOS"
    TITULO_CURTO = "CORAL"
    DESCRICAO = "Você é o maestro! Repita a melodia dos quatro ovos cantores sem desafinar."
    COR = (200, 50, 80)
    INSTRUCOES = [
        "Você é o MAESTRO do coral da família!",
        "Ouça os cantores e repita a sequência.",
        "A cada rodada a melodia ganha uma nota.",
        "MALUCO: os cantores trocam de lugar!",
        "SETAS/WASD (a posição) ou MOUSE",
    ]
    OPCOES = ["FÁCIL", "NORMAL", "MALUCO"]
    ROTULO_PONTOS = "SEQUÊNCIA"
    CONTAGEM = True

    MOEDAS_MAX = 40

    # --------------------------------------------------------
    # CENÁRIO: palco de teatro
    # --------------------------------------------------------

    @classmethod
    def criar_fundo(cls, jogador):
        sup = pygame.Surface((LARGURA, ALTURA))
        rnd = random.Random(8)
        parede = (40, 20, 40)
        sup.fill(parede)

        # Parede do fundo com listras suaves
        for x in range(0, LARGURA, 48):
            pygame.draw.rect(sup, (46, 24, 47), (x, 0, 24, PALCO_TOPO))

        # Arco decorativo atrás do cantor de cima, com lâmpadas
        arco = pygame.Rect(360, 86, 304, 190)
        pygame.draw.rect(sup, (58, 28, 62), arco, border_top_left_radius=150,
                         border_top_right_radius=150)
        pygame.draw.rect(sup, (200, 160, 60), arco, 5, border_top_left_radius=150,
                         border_top_right_radius=150)
        for i in range(19):
            a = math.pi + i * math.pi / 18
            px = arco.centerx + math.cos(a) * (arco.w / 2 - 12)
            py = arco.y + 150 + math.sin(a) * 138
            pygame.draw.circle(sup, (255, 230, 150), (int(px), int(py)), 4)
        for _ in range(14):
            x = rnd.randrange(arco.left + 30, arco.right - 30)
            y = rnd.randrange(arco.top + 50, PALCO_TOPO - 10)
            ui.estrela(sup, (x, y), rnd.choice((3, 4, 5)), (120, 90, 140))

        # Piso de madeira (tábuas)
        tabua = 24
        for i, y in enumerate(range(PALCO_TOPO, PALCO_BASE, tabua)):
            cor = (170, 110, 60) if i % 2 == 0 else (160, 102, 55)
            pygame.draw.rect(sup, cor, (0, y, LARGURA, tabua))
            pygame.draw.line(sup, (130, 80, 40), (0, y), (LARGURA, y), 2)
            for x in range((i * 97) % 180, LARGURA, 180):
                pygame.draw.line(sup, (130, 80, 40), (x, y), (x, y + tabua), 2)
            for _ in range(4):
                vx = rnd.randrange(0, LARGURA - 60)
                pygame.draw.arc(sup, (150, 95, 50), (vx, y + 6, rnd.randint(30, 60), 10), 0, math.pi, 1)
        # Sombra do fundo do palco
        sombra = pygame.Surface((LARGURA, 40), pygame.SRCALPHA)
        for k in range(40):
            pygame.draw.line(sombra, (0, 0, 0, int(110 * (1 - k / 40))), (0, k), (LARGURA, k))
        sup.blit(sombra, (0, PALCO_TOPO))

        # Tablados dos cantores + dicas das teclas
        for i, (x, y) in enumerate(POSICOES):
            base = pygame.Rect(0, 0, 150, 40)
            base.center = (x, y + 56)
            pygame.draw.ellipse(sup, (70, 40, 20), base.move(0, 8))
            pygame.draw.ellipse(sup, (110, 66, 34), base.move(0, 4))
            pygame.draw.ellipse(sup, (196, 150, 80), base)
            pygame.draw.ellipse(sup, (230, 190, 110), base.inflate(-24, -12), 2)
            # Plaquinha com a seta e a letra
            placa = pygame.Rect(0, 0, 60, 26)
            if i == 0:
                placa.midleft = (x + 84, y + 50)
            elif i == 1:
                placa.midright = (x - 70, y + 56)
            elif i == 2:
                placa.midleft = (x + 70, y + 56)
            else:
                placa.midleft = (x + 84, y + 54)
            pygame.draw.rect(sup, (30, 16, 30), placa.move(2, 3), border_radius=8)
            pygame.draw.rect(sup, (60, 34, 58), placa, border_radius=8)
            pygame.draw.rect(sup, (200, 160, 60), placa, 2, border_radius=8)
            ui.desenhar_texto(sup, f"{SETAS[i]} {LETRAS[i]}", (placa.centerx + 1, placa.centery + 1),
                              10, (255, 235, 180), "center")

        # Caixote do maestro
        caixa = pygame.Rect(0, 0, 110, 30)
        caixa.midtop = (CENTRO[0], CENTRO[1] + 40)
        pygame.draw.rect(sup, (60, 34, 18), caixa.move(0, 6), border_radius=6)
        pygame.draw.rect(sup, (150, 40, 60), caixa, border_radius=6)
        pygame.draw.rect(sup, (230, 190, 60), caixa, 3, border_radius=6)
        ui.estrela(sup, caixa.center, 9, (230, 190, 60))

        # Beirada do palco com luzes de ribalta
        pygame.draw.rect(sup, (12, 6, 12), (0, PALCO_BASE, LARGURA, ALTURA - PALCO_BASE))
        pygame.draw.rect(sup, (110, 60, 30), (0, PALCO_BASE - 4, LARGURA, 12))
        pygame.draw.line(sup, (200, 140, 80), (0, PALCO_BASE - 4), (LARGURA, PALCO_BASE - 4), 2)
        for x in range(40, LARGURA, 80):
            pygame.draw.circle(sup, (255, 230, 150), (x, PALCO_BASE - 4), 6, draw_top_left=True,
                               draw_top_right=True)

        # Cortinas laterais (dobras verticais, borda de dentro franzida)
        larg = 176
        pano = pygame.Surface((larg, PALCO_BASE), pygame.SRCALPHA)
        for x in range(larg):
            onda = 0.5 + 0.5 * math.cos(x / 15 * math.pi)
            pygame.draw.line(pano, ui.misturar((130, 20, 40), (180, 30, 50), onda),
                             (x, 0), (x, PALCO_BASE))
        borda = []
        for y in range(0, PALCO_BASE + 1, 8):
            franzido = 140 - 36 * math.sin(min(1.0, y / 430) * math.pi) + 8 * math.sin(y * 0.05)
            borda.append((franzido, y))
        mascara = pygame.Surface((larg, PALCO_BASE), pygame.SRCALPHA)
        pygame.draw.polygon(mascara, (255, 255, 255, 255), [(0, 0)] + borda + [(0, PALCO_BASE)])
        pano.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        pygame.draw.lines(pano, (100, 14, 32), False, borda, 3)

        for lado in (0, 1):
            if lado == 0:
                sup.blit(pano, (0, 0))
            else:
                sup.blit(pygame.transform.flip(pano, True, False), (LARGURA - larg, 0))
            # Amarração dourada
            amarra_x = 108 if lado == 0 else LARGURA - 108
            pygame.draw.ellipse(sup, (230, 190, 60), (amarra_x - 34, 440, 68, 14))
            pygame.draw.circle(sup, (230, 190, 60), (amarra_x, 447), 9)
            pygame.draw.line(sup, (230, 190, 60), (amarra_x, 455), (amarra_x - 6, 490), 3)
            pygame.draw.line(sup, (230, 190, 60), (amarra_x, 455), (amarra_x + 6, 490), 3)

        # Bambinela (cortina de cima) com franja dourada
        pygame.draw.rect(sup, (180, 30, 50), (0, 0, LARGURA, 60))
        for x in range(-64, LARGURA + 64, 128):
            pygame.draw.ellipse(sup, (150, 24, 44), (x, 20, 128, 70))
            pygame.draw.ellipse(sup, (180, 30, 50), (x + 6, 14, 116, 60))
        pygame.draw.rect(sup, (180, 30, 50), (0, 0, LARGURA, 44))
        for x in range(0, LARGURA, 128):
            for k in range(1, 4):
                pygame.draw.line(sup, (140, 22, 42), (x + k * 32, 0), (x + k * 32, 40), 3)
        pygame.draw.line(sup, (230, 190, 60), (0, 62), (LARGURA, 62), 4)
        for x in range(0, LARGURA, 16):
            pygame.draw.polygon(sup, (230, 190, 60), [(x, 62), (x + 16, 62), (x + 8, 76)])
            pygame.draw.polygon(sup, (180, 140, 40), [(x + 8, 62), (x + 16, 62), (x + 8, 76)])

        # Latas dos holofotes presas na bambinela
        for i in range(4):
            alvo = POSICOES[i]
            lx = int(alvo[0] * 0.75 + CENTRO[0] * 0.25)
            pygame.draw.rect(sup, (30, 30, 36), (lx - 14, 58, 28, 16), border_radius=4)
            pygame.draw.ellipse(sup, (255, 240, 180), (lx - 10, 68, 20, 8))
        return sup

    @classmethod
    def desenhar_icone(cls, sup, jogador):
        w, h = sup.get_size()
        cx, cy = w // 2, h // 2 + 6
        cantores = [(cx, cy - 34, 0), (cx - 52, cy + 4, 1), (cx + 52, cy + 4, 2), (cx, cy + 36, 3)]
        for x, y, i in cantores:
            ovo = CANTORES[i][0]
            partes = PARTES_CANTORES[i]
            jogador.desenhar(sup, (x, y), 26, aparencia=(ovo,) + partes)
        # Luz no cantor de cima
        luz = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.polygon(luz, (255, 240, 180, 70), [(cx - 6, 0), (cx + 6, 0), (cx + 26, cy - 14),
                                                       (cx - 26, cy - 14)])
        sup.blit(luz, (0, 0))
        jogador.desenhar(sup, (cx, cy + 2), 30)
        _nota_musical(sup, (cx + 30, cy - 34), 14, AMARELO)
        _nota_musical(sup, (cx - 34, cy - 30), 12, (255, 150, 200))

    # --------------------------------------------------------
    # PARTIDA
    # --------------------------------------------------------

    def reiniciar(self):
        minha = self.jogador.aparencia()
        self.aparencias = []
        for i, (ovo, _, _) in enumerate(CANTORES):
            cab, olho, boca = PARTES_CANTORES[i]
            # O cantor da mesma cor do jogador fica bem diferente dele
            if ovo == minha[0]:
                if cab == minha[1] or cab in (6, 7):
                    cab = (minha[1] + 3) % 8 if (minha[1] + 3) % 8 < 6 else 1
                if olho == minha[2]:
                    olho = (olho + 1) % 3
                if boca == minha[3]:
                    boca = (boca + 2) % 6
            self.aparencias.append((ovo, cab, olho, boca))

        self.lugares = [0, 1, 2, 3]             # lugar de cada cantor
        self.saida = [POSICOES[i] for i in range(4)]
        self.sequencia = []
        self.vidas = VIDAS[self.opcao]
        self.fase = "preparar"
        self.t_fase = 0.0
        self.indice = 0                         # nota atual (demonstração / resposta)
        self.t_espera = 0.0
        self.cantando = [0.0] * 4               # tempo restante de "boca aberta"
        self.crescer = [1.0] * 4                # escala animada de cada cantor
        self.balanco = [0.0] * 4                # balanço de quem desafinou
        self.ultimo_ativo = None                # para onde a batuta aponta
        self.notinhas = []                      # ♪ flutuando: [x, y, vx, vy, vida, cor]
        self.flores = []                        # flores jogadas no palco
        self.aplauso = 0.0
        self.volume_musica = 1.0
        self.ultima_troca = 0
        self.canal = 0
        self._nova_nota()

    # --------------------------------------------------------
    # AJUDANTES
    # --------------------------------------------------------

    def _cantor_no_lugar(self, lugar):
        return self.lugares.index(lugar)

    def _pos_cantor(self, c):
        """Posição atual do cantor c (animada durante a troca)."""
        if self.fase != "trocar":
            return POSICOES[self.lugares[c]]
        t = min(1.0, self.t_fase / DUR_TROCA)
        t = t * t * (3 - 2 * t)
        a0, a1 = _angulo_de(self.saida[c]), _angulo_de(POSICOES[self.lugares[c]])
        r0, r1 = _raio_de(self.saida[c]), _raio_de(POSICOES[self.lugares[c]])
        delta = (a1 - a0) % math.tau
        if delta > math.pi + 0.01:
            delta -= math.tau
        a = a0 + delta * t
        r = r0 + (r1 - r0) * t
        pulo = abs(math.sin(t * math.pi * 4)) * 18 * (1 - t * 0.3)
        return (CENTRO[0] + math.cos(a) * r, CENTRO[1] + math.sin(a) * r - pulo)

    def _nova_nota(self):
        """Acrescenta uma nota (no máximo 2 iguais seguidas)."""
        opcoes = list(range(4))
        if len(self.sequencia) >= 2 and self.sequencia[-1] == self.sequencia[-2]:
            opcoes.remove(self.sequencia[-1])
        self.sequencia.append(random.choice(opcoes))

    def _tocar(self, cantor, volume=1.0):
        """Canta a nota do cantor num canal separado (não é cortada por SFX)."""
        if not self.audio.ativo or not self.audio.sons_ligados:
            return
        snd = _som_nota(CANTORES[cantor][1])
        if snd is None:
            return
        try:
            total = pygame.mixer.get_num_channels()
            self.canal = 1 - self.canal
            canal = pygame.mixer.Channel(max(0, total - 1 - self.canal))
            snd.set_volume(0.6 * volume)
            canal.play(snd)
        except pygame.error:
            pass

    def _cantar(self, cantor, duracao):
        self.cantando[cantor] = duracao
        self.ultimo_ativo = cantor
        self._tocar(cantor)
        x, y = self._pos_cantor(cantor)
        cor = CANTORES[cantor][2]
        for _ in range(2):
            self.notinhas.append([x + random.uniform(-30, 30), y - 50, random.uniform(-40, 40),
                                  random.uniform(-110, -70), 1.0, cor])

    def _mudar_fase(self, fase):
        self.fase = fase
        self.t_fase = 0.0

    # --------------------------------------------------------
    # CONTROLES
    # --------------------------------------------------------

    def evento_jogo(self, e):
        if self.fase != "vez":
            return      # durante a demonstração o coral não escuta ninguém
        if e.type == pygame.KEYDOWN and e.key in TECLAS:
            self._responder(TECLAS[e.key])
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for lugar, (x, y) in enumerate(POSICOES):
                if math.hypot(e.pos[0] - x, e.pos[1] - (y + 10)) < RAIO_CLIQUE:
                    self._responder(lugar)
                    break

    def _responder(self, lugar):
        cantor = self._cantor_no_lugar(lugar)
        certo = self.sequencia[self.indice]
        self.t_espera = 0.0
        if cantor != certo:
            self._errar(cantor)
            return
        self._cantar(cantor, 0.32)
        self.indice += 1
        if self.indice >= len(self.sequencia):
            self._acertar_rodada()

    def _acertar_rodada(self):
        self.pontos = len(self.sequencia)
        self.aplauso = 1.2
        self.som("acerto")
        for x in range(120, LARGURA - 100, 130):
            self.particulas.explodir((x, PALCO_BASE + 10), [AMARELO, (255, 240, 160), BRANCO],
                                     6, 240, 0.8, (3, 6))
        self.textos.adicionar(f"+{self.pontos}", (CENTRO[0], CENTRO[1] - 80), AMARELO, 20)
        if self.pontos >= META[self.opcao]:
            self._mudar_fase("vitoria")
            self.som("vencer")
        else:
            self._mudar_fase("rodada_ok")

    def _errar(self, cantor):
        self.vidas -= 1
        self.balanco[cantor] = 1.0
        self.cantando = [0.0] * 4
        self.ultimo_ativo = cantor
        self.som("erro")
        self.tremer(0.15)
        x, y = POSICOES[self.lugares[cantor]]
        # Alguém da plateia joga uma flor (para animar o cantor)
        cor = random.choice([(255, 120, 170), (255, 90, 90), (190, 130, 255), (255, 170, 80)])
        self.flores.append([x + random.uniform(-60, 60), -20.0, y + random.uniform(40, 70), 0.0,
                            random.uniform(0, math.tau), cor])
        if len(self.flores) > 12:
            self.flores.pop(0)
        self._mudar_fase("errou")

    # --------------------------------------------------------
    # LÓGICA
    # --------------------------------------------------------

    def atualizar_jogo(self, dt):
        self.t_fase += dt
        self._animar(dt)

        if self.fase == "preparar":
            if self.t_fase >= TEMPO_PREPARAR:
                self.indice = 0
                self._mudar_fase("mostrar")
                self._cantar(self.sequencia[0], _intervalo(len(self.sequencia), self.opcao) * 0.8)

        elif self.fase == "mostrar":
            passo = _intervalo(len(self.sequencia), self.opcao)
            if self.t_fase >= passo:
                self.t_fase -= passo
                self.indice += 1
                if self.indice < len(self.sequencia):
                    self._cantar(self.sequencia[self.indice], passo * 0.8)
                else:
                    self.indice = 0
                    self.t_espera = 0.0
                    self._mudar_fase("vez")

        elif self.fase == "vez":
            self.t_espera += dt
            if self.t_espera >= TEMPO_RESPOSTA:
                certo = self.sequencia[self.indice]
                self.textos.adicionar("DEMOROU!", (CENTRO[0], CENTRO[1] - 110), (255, 170, 120), 16)
                self._errar(certo)

        elif self.fase == "rodada_ok":
            if self.t_fase >= TEMPO_RODADA_OK:
                self._nova_nota()
                rodadas = len(self.sequencia) - 1
                if self.opcao == 2 and rodadas % 5 == 0 and rodadas != self.ultima_troca:
                    self.ultima_troca = rodadas
                    self._comecar_troca()
                else:
                    self._mudar_fase("preparar")

        elif self.fase == "trocar":
            if self.t_fase >= DUR_TROCA + 0.5:
                self._mudar_fase("preparar")

        elif self.fase == "errou":
            if self.t_fase >= TEMPO_ERRO:
                if self.vidas > 0:
                    self.textos.adicionar("DE NOVO!", (CENTRO[0], CENTRO[1] - 110), AMARELO, 18)
                    self._mudar_fase("preparar")
                else:
                    self._fim(False)

        elif self.fase == "vitoria":
            if int((self.t_fase - dt) * 5) != int(self.t_fase * 5):
                x = random.uniform(200, LARGURA - 200)
                y = random.uniform(150, 550)
                self.particulas.explodir((x, y), [AMARELO, (255, 120, 150), (120, 200, 255),
                                                  (140, 230, 120), self.jogador.cor], 22, 280, 1.0)
            if self.t_fase >= DUR_VITORIA:
                self._fim(True)

        self._abaixar_musica(dt)

    def _comecar_troca(self):
        self.saida = [POSICOES[self.lugares[c]] for c in range(4)]
        novo = list(self.lugares)
        while any(a == b for a, b in zip(novo, self.lugares)):
            random.shuffle(novo)
        self.lugares = novo
        self.som("pulo")
        self._mudar_fase("trocar")

    def _animar(self, dt):
        for c in range(4):
            self.cantando[c] = max(0.0, self.cantando[c] - dt)
            alvo = 1.15 if self.cantando[c] > 0 else 1.0
            self.crescer[c] += (alvo - self.crescer[c]) * min(1.0, dt * 18)
            self.balanco[c] = max(0.0, self.balanco[c] - dt * 0.8)
        self.aplauso = max(0.0, self.aplauso - dt)

        vivas = []
        for n in self.notinhas:
            n[0] += n[2] * dt + math.sin(n[4] * 9) * 20 * dt
            n[1] += n[3] * dt
            n[4] -= dt * 0.9
            if n[4] > 0:
                vivas.append(n)
        self.notinhas = vivas

        for f in self.flores:
            if f[1] < f[2]:
                f[3] += 600 * dt
                f[1] = min(f[2], f[1] + f[3] * dt)
                f[4] += dt * 6

    def _abaixar_musica(self, dt):
        """Música a 30% enquanto o coral canta (volta sozinha depois)."""
        alvo = 0.3 if self.fase in ("preparar", "mostrar") else 0.6
        self.volume_musica += (alvo - self.volume_musica) * min(1.0, dt * 6)
        if not self.audio.ativo or self.audio.atual != self.ID:
            return
        try:
            pygame.mixer.music.set_volume(pygame.mixer.music.get_volume() * self.volume_musica)
        except pygame.error:
            pass

    def _fim(self, venceu):
        rodadas = self.pontos
        linhas = [f"SEQUÊNCIA: {rodadas} NOTAS"]
        if venceu:
            linhas.append("BIS! BIS! A PLATEIA AMOU!")
        else:
            certo = self.sequencia[self.indice] if self.indice < len(self.sequencia) else 0
            linhas.append(f"ERA O OVO {NOMES_POSICAO[self.lugares[certo]]}")
        self.terminar(venceu=venceu, valor=rodadas,
                      titulo="CONCERTO COMPLETO!" if venceu else "FIM DO SHOW",
                      linhas=linhas)

    def calcular_moedas(self, valor, venceu):
        moedas = 2 * valor
        if self.opcao == 2:
            moedas = int(moedas * 1.5)
        if valor > 0:
            moedas = max(moedas, self.MOEDAS_MIN)
        return max(0, min(self.MOEDAS_MAX, moedas))

    # --------------------------------------------------------
    # DESENHO
    # --------------------------------------------------------

    def desenhar_jogo(self, tela):
        tela.blit(self.fundo(self.jogador), (0, 0))

        # Holofote no cantor ativo
        if self.fase != "trocar":
            for c in range(4):
                if self.cantando[c] > 0:
                    sup, pos = _cone(self.lugares[c])
                    tela.blit(sup, pos)

        # Tablado aceso embaixo de quem canta
        for c in range(4):
            if self.cantando[c] > 0 and self.fase != "trocar":
                x, y = POSICOES[self.lugares[c]]
                cor = CANTORES[c][2]
                pygame.draw.ellipse(tela, cor, (x - 75, y + 36, 150, 40), 4)

        # Flores já no chão ficam atrás dos ovos
        for x, y, alvo, _, ang, cor in self.flores:
            if y >= alvo:
                _flor(tela, (x, y), 7, ang, cor)

        # Ordem de desenho: quem está mais no fundo primeiro
        ordem = sorted(range(4), key=lambda c: self._pos_cantor(c)[1])
        maestro_desenhado = False
        for c in ordem:
            pos = self._pos_cantor(c)
            if not maestro_desenhado and pos[1] > CENTRO[1] + 20:
                self._desenhar_maestro(tela)
                maestro_desenhado = True
            self._desenhar_cantor(tela, c, pos)
        if not maestro_desenhado:
            self._desenhar_maestro(tela)

        # Flores caindo e notinhas
        for x, y, alvo, _, ang, cor in self.flores:
            if y < alvo:
                _flor(tela, (x, y), 8, ang, cor)
        for x, y, _, _, vida, cor in self.notinhas:
            _nota_musical(tela, (x, y), 18 if vida > 0.5 else 14, cor)

        self._desenhar_plateia(tela)
        self.particulas.desenhar(tela)
        self.textos.desenhar(tela)
        if self.estado in ("jogando", "pausado"):
            self._desenhar_faixa(tela)

    def _desenhar_cantor(self, tela, c, pos):
        altura = round(ALTURA_CANTOR * self.crescer[c] / 2) * 2
        x, y = pos
        # Sombra
        pygame.draw.ellipse(tela, (60, 34, 18), (x - 34, y + 42, 68, 16))

        espelhar = False
        angulo = 0.0
        if self.fase == "trocar":
            espelhar = math.cos(_angulo_de(self.saida[c])) < 0
        if self.balanco[c] > 0:
            angulo = math.sin(self.balanco[c] * 30) * 14 * self.balanco[c]
        elif self.cantando[c] > 0:
            angulo = math.sin(self.tempo * 14) * 4

        # O pé fica no chão quando cresce
        cy = y + (ALTURA_CANTOR - altura) / 2
        self.jogador.desenhar(tela, (x, cy), altura, aparencia=self.aparencias[c],
                              espelhar=espelhar, angulo=angulo)

        # Boca aberta cantando: elipse preta com língua vermelha
        if self.cantando[c] > 0 and abs(angulo) < 6:
            escala = round(100 * altura / Jogador.OVO_RECT.h) / 100
            abre = 0.6 + 0.4 * abs(math.sin(self.tempo * 16))
            mx = x
            my = cy + (66 - Jogador.OVO_RECT.centery) * escala
            bw, bh = 24 * escala, (10 + 10 * abre) * escala
            boca = pygame.Rect(0, 0, int(bw), int(bh))
            boca.center = (int(mx), int(my))
            pygame.draw.ellipse(tela, (30, 10, 20), boca.inflate(4, 4))
            pygame.draw.ellipse(tela, (20, 0, 10), boca)
            lingua = pygame.Rect(0, 0, int(bw * 0.6), int(bh * 0.45))
            lingua.midbottom = (boca.centerx, boca.bottom - 1)
            pygame.draw.ellipse(tela, (230, 70, 90), lingua)

    def _desenhar_maestro(self, tela):
        x, y = CENTRO
        h = ALTURA_MAESTRO
        balanco = math.sin(self.tempo * math.pi * 100 / 60) * 3
        corpo = self.jogador.desenhar(tela, (x, y), h, angulo=balanco)

        # Gravata-borboleta (se não estiver usando roupa)
        equipado = self.app.save["equipado"]
        if not any(equipado.get(k) for k in ("corpo", "roupa", "pescoco", "gravata")):
            gy = corpo.centery + int(h * 0.36)
            gx = corpo.centerx
            t = int(h * 0.1)
            for lado in (-1, 1):
                pygame.draw.polygon(tela, (20, 20, 30), [(gx, gy), (gx + lado * t * 1.6, gy - t),
                                                         (gx + lado * t * 1.6, gy + t)])
                pygame.draw.polygon(tela, (70, 70, 90), [(gx, gy), (gx + lado * t * 1.6, gy - t),
                                                         (gx + lado * t * 1.6, gy + t)], 1)
            pygame.draw.circle(tela, (200, 40, 60), (gx, gy), max(3, t // 2 + 1))

        # Mão de luva branca com a batuta
        mao = (corpo.right + 6, corpo.centery + 8)
        if self.ultimo_ativo is not None and (any(self.cantando) or self.fase == "errou"):
            alvo = self._pos_cantor(self.ultimo_ativo)
            ang = math.atan2(alvo[1] - 20 - mao[1], alvo[0] - mao[0])
        else:
            ang = -math.pi / 3 + math.sin(self.tempo * math.pi * 100 / 60) * 0.45
        ponta = (mao[0] + math.cos(ang) * 62, mao[1] + math.sin(ang) * 62)
        pygame.draw.line(tela, (40, 30, 30), mao, ponta, 6)
        pygame.draw.line(tela, (250, 250, 240), mao, ponta, 3)
        pygame.draw.circle(tela, (255, 230, 120), (int(ponta[0]), int(ponta[1])), 3)
        pygame.draw.circle(tela, (120, 120, 140), mao, 11)
        pygame.draw.circle(tela, (250, 250, 250), mao, 9)

    def _desenhar_plateia(self, tela):
        base = ALTURA + 6
        for i, x in enumerate(range(24, LARGURA, 58)):
            pula = 0.0
            if self.aplauso > 0:
                pula = abs(math.sin(self.tempo * 14 + i * 1.3)) * 10 * min(1.0, self.aplauso)
            alt = 50 + (i * 7) % 12
            cabeca = pygame.Rect(0, 0, 42, alt)
            cabeca.midbottom = (x + (i % 3) * 4, base - pula)
            pygame.draw.ellipse(tela, (30, 20, 30), cabeca)
            pygame.draw.ellipse(tela, (52, 36, 52), cabeca, 2)
            if self.aplauso > 0 and i % 2 == 0:
                mx = cabeca.centerx + (10 if (int(self.tempo * 10) + i) % 2 else 4)
                pygame.draw.circle(tela, (44, 30, 44), (mx, cabeca.top + 4), 7)
                pygame.draw.circle(tela, (44, 30, 44), (mx - 14, cabeca.top + 4), 7)

    def _desenhar_faixa(self, tela):
        """Faixa de status no topo (quem canta / sua vez)."""
        caixa = pygame.Rect(0, 0, 380, 40)
        caixa.midtop = (LARGURA // 2, 80)
        cor = BRANCO
        if self.fase in ("preparar", "mostrar"):
            texto, cor = "OUÇA O CORAL...", (190, 210, 255)
        elif self.fase == "vez":
            texto, cor = f"SUA VEZ!  {self.indice}/{len(self.sequencia)}", AMARELO
        elif self.fase == "rodada_ok":
            texto, cor = "MUITO BEM!", (150, 240, 120)
        elif self.fase == "trocar":
            texto, cor = "TROCA-TROCA!", (255, 160, 220)
        elif self.fase == "errou":
            texto, cor = "DESAFINOU!", (255, 130, 130)
        else:
            texto, cor = "BRAVO!", AMARELO
        ui.painel(tela, caixa, (24, 14, 28), cor, 12, 3, sombra=False)
        ui.desenhar_texto(tela, texto, (caixa.centerx, caixa.centery + 1), 14, cor, "center")

        # Tempo para responder (só aparece se o jogador demorar)
        if self.fase == "vez" and self.t_espera > 1.5:
            resta = max(0.0, 1 - self.t_espera / TEMPO_RESPOSTA)
            barra = pygame.Rect(caixa.x + 14, caixa.bottom - 7, int((caixa.w - 28) * resta), 4)
            pygame.draw.rect(tela, (255, 120, 90) if resta < 0.35 else AMARELO, barra)

    def desenhar_hud(self, tela):
        caixa = pygame.Rect(12, 12, 450, 48)
        ui.painel(tela, caixa, (20, 16, 30), BRANCO, 12, 3, sombra=False)
        ui.desenhar_texto(tela, f"SEQUÊNCIA: {self.pontos}", (caixa.x + 16, caixa.centery), 14,
                          AMARELO, "midleft")
        rec = self.recorde()
        texto = f"RECORDE: {rec}" if rec is not None else "RECORDE: --"
        ui.desenhar_texto(tela, texto, (caixa.x + 246, caixa.centery), 12, (180, 200, 255), "midleft")

        # Vidas (FÁCIL) ou o nível
        caixa = pygame.Rect(0, 12, 150, 48)
        caixa.right = LARGURA - 76
        ui.painel(tela, caixa, (20, 16, 30), BRANCO, 12, 3, sombra=False)
        total = VIDAS[self.opcao]
        if total > 1:
            for i in range(total):
                c = (caixa.x + 32 + i * 43, caixa.centery + 1)
                ui.coracao(tela, c, 28, (235, 60, 90) if i < self.vidas else (70, 60, 80))
        else:
            ui.desenhar_texto(tela, self.OPCOES[self.opcao], caixa.center, 12,
                              (255, 160, 220) if self.opcao == 2 else BRANCO, "center")
