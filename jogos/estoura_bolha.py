import math
import random

import pygame

from settings import *
from core import ui
from jogos.base import MiniJogo

# ============================================================
# ESTOURA-BOLHAS
# ============================================================
# Hora do banho! O seu ovo sopra bolhas de chiclete pela boca.
# Junte 3 ou mais da mesma cor para estourar; as bolhas que
# ficarem soltas do teto caem (e valem o dobro). Algumas bolhas
# têm PINTINHOS presos: solte todos para passar de fase.
# Errou 6 vezes seguidas? O teto desce uma linha!

# Grade hexagonal (linhas ímpares deslocadas meia bolha)
COLS = 12
DIAM = 56
R = DIAM // 2
X0 = 162                            # parede esquerda
X1 = X0 + COLS * DIAM + R           # parede direita (862)
TOPO = 70                           # altura inicial do teto
ALT_LINHA = DIAM * math.sqrt(3) / 2  # distância entre as linhas (~48.5)
RAIO_COLISAO = DIAM - 8             # encosta um pouquinho antes de tocar
LINHA_PERDE = 580                   # bolha passou daqui -> fim de jogo
LINHAS_MAX_INICIO = 8

# Lançador (a boca do ovo)
LANCADOR = (512, 650)
ALT_OVO = 76
BOCA = 0.2 * ALT_OVO                # distância do centro do ovo até a boca
VEL_TIRO = 1100
ANG_MIN, ANG_MAX = 12.0, 168.0
VEL_MIRA = 90.0
TEMPO_SOPRO = 0.12                  # bochechas infladas antes de soprar
TEMPO_CRESCER = 0.22                # bolha nova crescendo na boca
ESCALA_BOCA = 0.55                  # tamanho da bolha esperando na boca

DISPAROS_TETO = 6                   # erros seguidos até o teto descer
CHAO_BOLHAS = 700                   # onde as bolhas que caem quicam

PONTOS_ESTOURO = 10
PONTOS_QUEDA = 20
PONTOS_PINTINHO = 100
PONTOS_FASE = 500

CORES = [(240, 80, 90), (255, 200, 60), (90, 200, 110), (80, 150, 240), (170, 110, 230),
         (255, 140, 60)]
NUM_CORES = (4, 5, 6)

PROXIMA_POS = (404, 668)

# Cores dos textos (escuras, para ler bem no fundo claro do banheiro)
TXT_ROXO = (130, 50, 160)
TXT_LARANJA = (235, 95, 30)
TXT_ROSA = (225, 50, 110)
PROXIMA_ESCALA = 0.72

TECLAS_ESQ = (pygame.K_LEFT, pygame.K_a)
TECLAS_DIR = (pygame.K_RIGHT, pygame.K_d)
TECLAS_TIRO = (pygame.K_SPACE, pygame.K_w, pygame.K_UP, pygame.K_RETURN, pygame.K_KP_ENTER)
TECLAS_TROCA = (pygame.K_DOWN, pygame.K_s)


# ============================================================
# GRADE HEXAGONAL
# ============================================================

def _vizinhos(l, c):
    """As 6 células vizinhas (depende da paridade da linha)."""
    if l % 2 == 0:
        deltas = ((0, -1), (0, 1), (-1, -1), (-1, 0), (1, -1), (1, 0))
    else:
        deltas = ((0, -1), (0, 1), (-1, 0), (-1, 1), (1, 0), (1, 1))
    for dl, dc in deltas:
        nl, nc = l + dl, c + dc
        if nl >= 0 and 0 <= nc < COLS:
            yield (nl, nc)


def _centro(l, c, teto):
    x = X0 + R + c * DIAM + (R if l % 2 else 0)
    y = teto + R + l * ALT_LINHA
    return x, y


# ============================================================
# DESENHOS (feitos uma vez só, com cache)
# ============================================================

_sprites = {}
Z = 2


def _simbolo(s, indice, c, t, cor):
    """Simbolozinho em cada cor (ajuda a diferenciar amarelo e laranja)."""
    x, y = c
    if indice == 0:
        ui.coracao(s, (x, y + 2), t, cor)
    elif indice == 1:
        ui.estrela(s, (x, y), t * 0.62, cor)
    elif indice == 2:
        pygame.draw.circle(s, cor, (x, y), t * 0.4, max(3, t // 7))
    elif indice == 3:
        pygame.draw.polygon(s, cor, [(x, y - t * 0.5), (x + t * 0.42, y), (x, y + t * 0.5),
                                     (x - t * 0.42, y)])
    elif indice == 4:
        pygame.draw.polygon(s, cor, [(x, y - t * 0.46), (x + t * 0.46, y + t * 0.38),
                                     (x - t * 0.46, y + t * 0.38)])
    else:
        r = pygame.Rect(0, 0, int(t * 0.66), int(t * 0.66))
        r.center = (x, y)
        pygame.draw.rect(s, cor, r, border_radius=t // 8)


def _pintinho_grande(quadro=0):
    s = pygame.Surface((60, 60), pygame.SRCALPHA)
    amarelo, contorno = (255, 222, 70), (200, 140, 20)
    # Topete
    pygame.draw.ellipse(s, contorno, (26, 4, 8, 14))
    pygame.draw.ellipse(s, contorno, (31, 6, 8, 12))
    pygame.draw.circle(s, contorno, (30, 33), 21)
    pygame.draw.circle(s, amarelo, (30, 33), 18)
    # Asinha
    if quadro == 0:
        pygame.draw.ellipse(s, contorno, (6, 30, 18, 12))
        pygame.draw.ellipse(s, (255, 236, 130), (8, 32, 14, 8))
    else:
        pygame.draw.ellipse(s, contorno, (4, 20, 18, 12))
        pygame.draw.ellipse(s, (255, 236, 130), (6, 22, 14, 8))
    # Olhos e bico
    pygame.draw.circle(s, (30, 20, 20), (24, 29), 3)
    pygame.draw.circle(s, (30, 20, 20), (38, 29), 3)
    pygame.draw.circle(s, BRANCO, (23, 28), 1)
    pygame.draw.circle(s, BRANCO, (37, 28), 1)
    pygame.draw.polygon(s, (255, 140, 40), [(27, 34), (35, 34), (31, 41)])
    pygame.draw.circle(s, (255, 160, 160), (19, 36), 3)
    pygame.draw.circle(s, (255, 160, 160), (43, 36), 3)
    return s


def _brilho(s, lado):
    """Arco de brilho branco no canto de cima à esquerda."""
    camada = pygame.Surface((lado, lado), pygame.SRCALPHA)
    r = pygame.Rect(lado * 0.16, lado * 0.16, lado * 0.68, lado * 0.68)
    pygame.draw.arc(camada, (255, 255, 255, 180), r, math.radians(100), math.radians(170),
                    max(3, lado // 14))
    pygame.draw.circle(camada, (255, 255, 255, 180), (lado * 0.33, lado * 0.26), lado // 22)
    s.blit(camada, (0, 0))


def _bolha(tipo, pintinho=False):
    lado = DIAM * Z
    s = pygame.Surface((lado, lado), pygame.SRCALPHA)
    c = (lado // 2, lado // 2)
    raio = lado // 2 - 1

    if tipo == "arco":
        # Fatias com todas as cores
        pygame.draw.circle(s, (120, 90, 140), c, raio)
        n = len(CORES)
        for i, cor in enumerate(CORES):
            pontos = [c]
            for k in range(9):
                a = (i + k / 8) * math.tau / n
                pontos.append((c[0] + math.cos(a) * (raio - 4), c[1] + math.sin(a) * (raio - 4)))
            pygame.draw.polygon(s, cor, pontos)
        pygame.draw.circle(s, BRANCO, c, raio * 0.36)
        ui.estrela(s, c, raio * 0.3, (255, 200, 60))
    elif tipo == "bomba":
        # Bolha clarinha com uma bomba em forma de ovo dentro
        pygame.draw.circle(s, (120, 120, 140), c, raio)
        pygame.draw.circle(s, (205, 210, 225), c, raio - 4)
        ovo = pygame.Rect(0, 0, raio * 1.05, raio * 1.3)
        ovo.center = (c[0], c[1] + 6)
        pygame.draw.ellipse(s, (20, 20, 30), ovo.inflate(6, 6))
        pygame.draw.ellipse(s, (60, 60, 75), ovo)
        pygame.draw.ellipse(s, (120, 120, 140), (ovo.x + 8, ovo.y + 8, 10, 16))
        topo = (c[0] + 4, ovo.y - 2)
        pygame.draw.lines(s, (190, 150, 90), False, [topo, (topo[0] + 8, topo[1] - 12),
                                                     (topo[0] + 18, topo[1] - 14)], 5)
        ui.estrela(s, (topo[0] + 20, topo[1] - 16), 10, (255, 150, 40))
        ui.estrela(s, (topo[0] + 20, topo[1] - 16), 5, (255, 240, 140))
    else:
        cor = CORES[tipo]
        pygame.draw.circle(s, ui.escurecer(cor, 70), c, raio)          # borda mais escura
        pygame.draw.circle(s, cor, c, raio - 4)
        pygame.draw.circle(s, ui.clarear(cor, 25), (c[0] - 6, c[1] - 6), raio - 14)
        pygame.draw.circle(s, cor, (c[0] + 2, c[1] + 2), raio - 14)
        if pintinho:
            pygame.draw.circle(s, ui.clarear(cor, 70), c, raio - 12)
            pinto = pygame.transform.smoothscale(_pintinho_grande(), (int(raio * 1.5), int(raio * 1.5)))
            s.blit(pinto, pinto.get_rect(center=(c[0], c[1] + 2)))
        else:
            _simbolo(s, tipo, c, int(raio * 0.8), ui.clarear(cor, 55))
    _brilho(s, lado)
    return pygame.transform.smoothscale(s, (DIAM, DIAM))


def _sprite(tipo, pintinho=False):
    chave = (tipo, pintinho)
    s = _sprites.get(chave)
    if s is None:
        s = _bolha(tipo, pintinho)
        _sprites[chave] = s
    return s


def _sprite_pintinho(quadro):
    chave = ("pinto", quadro)
    s = _sprites.get(chave)
    if s is None:
        s = pygame.transform.smoothscale(_pintinho_grande(quadro), (34, 34))
        _sprites[chave] = s
    return s


_escalas = {}


def _bolha_escalada(tipo, lado):
    """Bolha em outro tamanho (boca do ovo e 'próxima'), com cache."""
    lado = max(2, int(lado) // 2 * 2)
    chave = (tipo, lado)
    s = _escalas.get(chave)
    if s is None:
        if len(_escalas) > 300:
            _escalas.clear()
        s = pygame.transform.smoothscale(_sprite(tipo), (lado, lado))
        _escalas[chave] = s
    return s


# ============================================================
# PEÇAS
# ============================================================

class Bolha:

    def __init__(self, cor, pintinho=False):
        self.cor = cor
        self.pintinho = pintinho


# ============================================================
# JOGO
# ============================================================

class EstouraBolha(MiniJogo):

    ID = "estoura_bolha"
    TITULO = "ESTOURA-BOLHAS"
    TITULO_CURTO = "BOLHAS"
    DESCRICAO = "Seu ovo sopra bolhas de chiclete! Junte 3 da mesma cor para estourar e solte os pintinhos."
    COR = (240, 110, 170)
    INSTRUCOES = [
        "Sopre bolhas: junte 3 da mesma cor para estourar!",
        "Bolhas soltas do teto caem e valem o dobro.",
        "Solte todos os PINTINHOS para passar de fase.",
        "Errou 6 vezes seguidas? O teto desce!",
        "←→/A D ou MOUSE mira • ESPAÇO sopra • ↓/S troca",
    ]
    OPCOES = ["FÁCIL (4 CORES)", "MÉDIO (5)", "DIFÍCIL (6)"]
    MENOR_MELHOR = False
    ROTULO_PONTOS = "PONTOS"
    CONTAGEM = True

    TRILHA = dict(bpm=120, tom="F#", escala="pentatonica", lead="quadrada", duty=0.125,
                  envelope="staccato", baixo="rock", onda_baixo="triangulo",
                  acomp="arpejo8", onda_acomp="sino", bateria="pop",
                  energia=0.65, eco=(0.18, 0.22))

    # O design pedia 1 moeda a cada 60, mas pintinhos (+100) e fases (+500)
    # rendem muito: com 150 uma partida típica (2-3 fases) dá ~20-27 moedas.
    MOEDAS_POR = 150
    MOEDAS_MAX = 45

    # --------------------------------------------------------
    # CENÁRIO: hora do banho
    # --------------------------------------------------------

    @classmethod
    def criar_fundo(cls, jogador):
        sup = ui.gradiente(LARGURA, ALTURA, (255, 200, 230), (170, 210, 255))
        rnd = random.Random(24)

        # Azulejos claros
        linhas = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        for x in range(0, LARGURA, 48):
            pygame.draw.line(linhas, (255, 255, 255, 40), (x, 0), (x, ALTURA), 2)
        for y in range(0, ALTURA, 48):
            pygame.draw.line(linhas, (255, 255, 255, 40), (0, y), (LARGURA, y), 2)

        # Área do jogo um pouco mais clara
        pygame.draw.rect(linhas, (255, 255, 255, 60), (X0, 0, X1 - X0, ALTURA))
        # Linha de perigo (tracejada)
        for x in range(X0 + 6, X1 - 6, 24):
            pygame.draw.line(linhas, (230, 70, 110, 150), (x, LINHA_PERDE), (x + 12, LINHA_PERDE), 3)
        sup.blit(linhas, (0, 0))

        # Paredes laterais (borda da banheira)
        for x in (X0 - 12, X1):
            parede = pygame.Rect(x, 0, 12, 690)
            pygame.draw.rect(sup, (255, 250, 252), parede)
            pygame.draw.rect(sup, (220, 150, 190), parede, 2)
            pygame.draw.line(sup, (240, 200, 225), (parede.centerx, 0), (parede.centerx, 690), 2)

        # Bolhinhas decorativas nas laterais
        for _ in range(26):
            lado = rnd.choice((0, 1))
            x = rnd.randint(14, X0 - 30) if lado == 0 else rnd.randint(X1 + 26, LARGURA - 14)
            y = rnd.randint(90, 560)
            r = rnd.randint(4, 13)
            pygame.draw.circle(sup, (255, 255, 255), (x, y), r, 2)
            pygame.draw.circle(sup, (255, 255, 255), (x - r // 3, y - r // 3), max(1, r // 4))

        # Prateleira com xampu e sabonete (direita)
        prat = pygame.Rect(X1 + 24, 470, 120, 10)
        pygame.draw.rect(sup, (255, 255, 255), prat, border_radius=4)
        pygame.draw.rect(sup, (200, 150, 190), prat, 2, border_radius=4)
        frasco = pygame.Rect(prat.x + 12, prat.y - 62, 36, 62)
        pygame.draw.rect(sup, (120, 200, 220), frasco, border_radius=10)
        pygame.draw.rect(sup, (60, 130, 160), frasco, 2, border_radius=10)
        pygame.draw.rect(sup, (250, 250, 255), (frasco.x + 8, frasco.y + 18, 20, 24), border_radius=4)
        pygame.draw.rect(sup, (60, 130, 160), (frasco.x + 11, frasco.y - 12, 14, 14), border_radius=3)
        sabao = pygame.Rect(prat.x + 62, prat.y - 22, 48, 22)
        pygame.draw.rect(sup, (255, 170, 200), sabao, border_radius=9)
        pygame.draw.rect(sup, (210, 110, 150), sabao, 2, border_radius=9)
        pygame.draw.ellipse(sup, (255, 220, 235), (sabao.x + 8, sabao.y + 4, 20, 7))

        # Espuma na base (círculos brancos sobrepostos)
        for i in range(70):
            x = i * 15 + rnd.randint(-6, 6)
            y = 700 + rnd.randint(-10, 10)
            r = rnd.randint(14, 26)
            pygame.draw.circle(sup, (225, 235, 250), (x, y + 3), r)
        for i in range(70):
            x = i * 15 + rnd.randint(-6, 6)
            y = 702 + rnd.randint(-10, 10)
            r = rnd.randint(12, 22)
            pygame.draw.circle(sup, (255, 255, 255), (x, y), r)

        # Patinho de borracha (esquerda, boiando na espuma)
        cls._patinho(sup, 78, 668)
        return sup

    @staticmethod
    def _patinho(sup, x, y):
        amarelo, contorno = (255, 215, 50), (200, 150, 20)
        pygame.draw.ellipse(sup, contorno, (x - 44, y - 22, 88, 50))
        pygame.draw.ellipse(sup, amarelo, (x - 41, y - 19, 82, 44))
        pygame.draw.polygon(sup, contorno, [(x + 30, y - 16), (x + 50, y - 34), (x + 42, y - 8)])
        pygame.draw.polygon(sup, amarelo, [(x + 32, y - 15), (x + 46, y - 30), (x + 40, y - 10)])
        pygame.draw.circle(sup, contorno, (x - 18, y - 32), 26)
        pygame.draw.circle(sup, amarelo, (x - 18, y - 32), 23)
        pygame.draw.polygon(sup, (230, 110, 30), [(x - 42, y - 34), (x - 58, y - 28), (x - 42, y - 22)])
        pygame.draw.polygon(sup, (255, 140, 40), [(x - 40, y - 32), (x - 54, y - 28), (x - 40, y - 24)])
        pygame.draw.circle(sup, (30, 20, 20), (x - 26, y - 40), 4)
        pygame.draw.circle(sup, BRANCO, (x - 27, y - 41), 1)
        pygame.draw.ellipse(sup, (255, 240, 150), (x - 8, y - 8, 30, 12))
        pygame.draw.ellipse(sup, (255, 245, 170), (x - 30, y - 50, 12, 8))

    @classmethod
    def desenhar_icone(cls, sup, jogador):
        w, h = sup.get_size()
        d = 22
        for i, (fx, fy, cor, pinto) in enumerate(((0.28, 0.12, 0, False), (0.39, 0.12, 0, False),
                                                   (0.5, 0.12, 3, True), (0.61, 0.12, 2, False),
                                                   (0.72, 0.12, 1, False), (0.335, 0.28, 3, False),
                                                   (0.445, 0.28, 2, False), (0.555, 0.28, 1, True),
                                                   (0.665, 0.28, 4, False))):
            s = pygame.transform.smoothscale(_sprite(cor, pinto), (d, d))
            sup.blit(s, s.get_rect(center=(int(w * fx), int(h * fy) + 4)))
        centro = (w // 2, int(h * 0.74))
        jogador.desenhar(sup, centro, h * 0.34)
        s = pygame.transform.smoothscale(_sprite(0), (12, 12))
        sup.blit(s, s.get_rect(center=(centro[0], int(centro[1] + h * 0.34 * 0.2))))
        s = pygame.transform.smoothscale(_sprite(0), (d - 2, d - 2))
        sup.blit(s, s.get_rect(center=(centro[0] + 40, int(h * 0.5))))

    # --------------------------------------------------------
    # PARTIDA
    # --------------------------------------------------------

    def reiniciar(self):
        self.ncores = NUM_CORES[self.opcao] if self.opcao < len(NUM_CORES) else 4
        self.fase = 1
        self.angulo = 90.0
        self.teclas = set()
        self.tiro = None
        self.sopro = 0.0
        self.crescer = 1.0
        self.erros = 0
        self.ate_especial = random.randint(13, 17)
        self.salvos = 0
        self.morto = False
        self.tempo_morto = 0.0
        self.transicao = 0.0
        self.estouros = []          # bolhas esperando para estourar (efeito em cascata)
        self.aneis = []             # anéis dos estouros
        self.caindo = []            # bolhas soltas caindo
        self.pintinhos = []         # pintinhos livres voando
        self._caminho = None
        self._chave_caminho = None
        self._novo_tabuleiro(animar=False)
        self.atual = self._sortear()
        self.proxima = self._sortear()

    def _novo_tabuleiro(self, animar=True):
        self.teto = float(TOPO)
        self.teto_vis = self.teto - 520 if animar else self.teto
        self.erros = 0
        self.grade = {}
        self.versao = 0
        linhas = min(LINHAS_MAX_INICIO, 4 + self.fase)
        for l in range(linhas):
            for c in range(COLS):
                # Copia a cor de um vizinho às vezes (forma grupinhos)
                vizinhas = [self.grade[v].cor for v in _vizinhos(l, c) if v in self.grade]
                if vizinhas and random.random() < 0.45:
                    cor = random.choice(vizinhas)
                else:
                    cor = random.randrange(self.ncores)
                self.grade[(l, c)] = Bolha(cor)

        # Pintinhos presos (espalhados, fora da última linha)
        qtd = min(2 + self.fase, 6)
        candidatas = [(l, c) for (l, c) in self.grade if l < linhas - 1]
        random.shuffle(candidatas)
        escolhidas = []
        for cel in candidatas:
            if all(abs(cel[0] - o[0]) + abs(cel[1] - o[1]) >= 3 for o in escolhidas):
                escolhidas.append(cel)
            if len(escolhidas) >= qtd:
                break
        for cel in escolhidas:
            self.grade[cel].pintinho = True
        self.total_pintinhos = len(escolhidas)

    def _cores_presentes(self):
        return sorted({b.cor for b in self.grade.values()})

    def _sortear(self):
        """Próxima bolha: sempre uma cor presente (ou um especial de vez em quando)."""
        self.ate_especial -= 1
        if self.ate_especial <= 0:
            self.ate_especial = random.randint(13, 17)
            return random.choice(("bomba", "arco"))
        cores = self._cores_presentes() or list(range(self.ncores))
        return random.choice(cores)

    def _conferir_cores(self):
        """Se a cor da bolha sumiu do tabuleiro, sorteia outra."""
        cores = self._cores_presentes()
        if not cores:
            return
        if isinstance(self.atual, int) and self.atual not in cores:
            self.atual = random.choice(cores)
        if isinstance(self.proxima, int) and self.proxima not in cores:
            self.proxima = random.choice(cores)

    # --------------------------------------------------------
    # CONTROLES
    # --------------------------------------------------------

    def evento(self, e):
        if e.type == pygame.KEYDOWN:
            self.teclas.add(e.key)
        elif e.type == pygame.KEYUP:
            self.teclas.discard(e.key)
        elif e.type == pygame.WINDOWFOCUSLOST:
            self.teclas.clear()
        super().evento(e)

    def _rect_proxima(self):
        r = pygame.Rect(0, 0, 64, 64)
        r.center = PROXIMA_POS
        return r

    def evento_jogo(self, e):
        if e.type == pygame.MOUSEMOTION:
            self._mirar_mouse(e.pos)
        elif e.type == pygame.MOUSEBUTTONDOWN:
            if e.button == 3:
                self._trocar()
            elif e.button == 1:
                if self._rect_proxima().collidepoint(e.pos):
                    self._trocar()
                elif not self.botao_pausa.collidepoint(e.pos):
                    self._mirar_mouse(e.pos)
                    self._soprar()
        elif e.type == pygame.KEYDOWN:
            if e.key in TECLAS_TIRO:
                self._soprar()
            elif e.key in TECLAS_TROCA:
                self._trocar()

    def _mirar_mouse(self, pos):
        if self.botao_pausa.collidepoint(pos):
            return
        ox, oy = self._boca()
        dy = oy - pos[1]
        if dy < 8:
            dy = 8
        ang = math.degrees(math.atan2(dy, pos[0] - ox))
        self.angulo = max(ANG_MIN, min(ANG_MAX, ang))

    def _pode_soprar(self):
        return (self.tiro is None and self.sopro <= 0 and self.crescer >= 1.0 and not self.morto
                and self.transicao <= 0 and abs(self.teto_vis - self.teto) < 3)

    def _soprar(self):
        if self._pode_soprar():
            self.sopro = TEMPO_SOPRO
            self.som("asa", 0.5)

    def _trocar(self):
        if self.morto or self.transicao > 0 or self.sopro > 0:
            return
        self.atual, self.proxima = self.proxima, self.atual
        self.crescer = min(self.crescer, 0.5)
        self.som("virar", 0.6)

    # --------------------------------------------------------
    # LÓGICA
    # --------------------------------------------------------

    def _inclinacao(self):
        return (self.angulo - 90) * 0.22

    def _boca(self):
        """Posição da boca do ovo (de onde sai a bolha)."""
        cx, cy = LANCADOR[0], LANCADOR[1] - BOCA
        a = math.radians(self._inclinacao())
        return (cx + BOCA * math.sin(a), cy + BOCA * math.cos(a))

    def atualizar_jogo(self, dt):
        self._animar(dt)

        if self.morto:
            self.tempo_morto += dt
            if self.tempo_morto > 1.8:
                self.terminar(linhas=[f"PONTOS: {self.pontos}", f"FASE: {self.fase}",
                                      f"PINTINHOS SALVOS: {self.salvos}"])
            return

        if self.transicao > 0:
            self.transicao -= dt
            if self.transicao <= 0:
                self.fase += 1
                self._novo_tabuleiro()
                self._conferir_cores()
                self._texto(f"FASE {self.fase}!", (LARGURA // 2, 380), AMARELO, 28)
            return

        # Mira pelo teclado
        giro = 0
        if any(t in self.teclas for t in TECLAS_ESQ):
            giro += 1
        if any(t in self.teclas for t in TECLAS_DIR):
            giro -= 1
        if giro:
            self.angulo = max(ANG_MIN, min(ANG_MAX, self.angulo + giro * VEL_MIRA * dt))

        # Sopro: bochechas infladas e depois a bolha sai voando
        if self.sopro > 0:
            self.sopro -= dt
            if self.sopro <= 0:
                self.sopro = 0.0
                self._lancar()

        if self.tiro is None and self.crescer < 1.0:
            self.crescer = min(1.0, self.crescer + dt / TEMPO_CRESCER)

        if self.tiro is not None:
            self._mover_tiro(dt)

    def _lancar(self):
        x, y = self._boca()
        a = math.radians(self.angulo)
        self.tiro = {"x": x, "y": y, "vx": math.cos(a) * VEL_TIRO, "vy": -math.sin(a) * VEL_TIRO,
                     "tipo": self.atual}
        self.atual = self.proxima
        self.proxima = self._sortear()
        self.crescer = 0.0
        self.som("pulo", 0.4)

    def _colide(self, x, y):
        """Célula ocupada que a bolha em (x, y) está tocando (ou None)."""
        l0 = round((y - self.teto - R) / ALT_LINHA)
        lim = RAIO_COLISAO * RAIO_COLISAO
        for l in (l0 - 1, l0, l0 + 1):
            if l < 0:
                continue
            desloc = R if l % 2 else 0
            c0 = round((x - X0 - R - desloc) / DIAM)
            for c in (c0 - 1, c0, c0 + 1):
                if (l, c) in self.grade:
                    cx, cy = _centro(l, c, self.teto)
                    if (cx - x) ** 2 + (cy - y) ** 2 < lim:
                        return (l, c)
        return None

    def _mover_tiro(self, dt):
        t = self.tiro
        dist = VEL_TIRO * dt
        passos = max(1, int(dist / 6) + 1)
        for _ in range(passos):
            t["x"] += t["vx"] * dt / passos
            t["y"] += t["vy"] * dt / passos

            # Rebate nas paredes
            if t["x"] < X0 + R:
                t["x"] = 2 * (X0 + R) - t["x"]
                t["vx"] = abs(t["vx"])
                self.som("clique", 0.4)
            elif t["x"] > X1 - R:
                t["x"] = 2 * (X1 - R) - t["x"]
                t["vx"] = -abs(t["vx"])
                self.som("clique", 0.4)

            no_teto = t["y"] - R <= self.teto
            bateu = self._colide(t["x"], t["y"])
            if no_teto or bateu is not None:
                self.tiro = None
                self._grudar(t["x"], t["y"], bateu, no_teto, t["tipo"])
                return

    def _grudar(self, x, y, bateu, no_teto, tipo):
        """Prende a bolha na célula vazia mais próxima (vizinha da colisão)."""
        candidatas = set()
        if bateu is not None:
            candidatas.update(v for v in _vizinhos(*bateu) if v not in self.grade)
        if no_teto:
            candidatas.update((0, c) for c in range(COLS) if (0, c) not in self.grade)
        # A própria célula onde a bolha está (se estiver presa em algo)
        l = max(0, round((y - self.teto - R) / ALT_LINHA))
        c = round((x - X0 - R - (R if l % 2 else 0)) / DIAM)
        if 0 <= c < COLS and (l, c) not in self.grade and self._apoiada((l, c)):
            candidatas.add((l, c))
        if not candidatas:
            # Não deveria acontecer; procura qualquer célula livre apoiada perto
            for (bl, bc) in list(self.grade):
                candidatas.update(v for v in _vizinhos(bl, bc) if v not in self.grade)
            candidatas.update((0, k) for k in range(COLS) if (0, k) not in self.grade)

        def dist(cel):
            cx, cy = _centro(cel[0], cel[1], self.teto)
            return (cx - x) ** 2 + (cy - y) ** 2

        cel = min(candidatas, key=dist)
        cor = tipo if isinstance(tipo, int) else 0
        self.grade[cel] = Bolha(cor)
        self._resolver(cel, tipo)

    def _apoiada(self, cel):
        return cel[0] == 0 or any(v in self.grade for v in _vizinhos(*cel))

    def _grupo(self, cel, cor=None):
        """Flood fill: todas as bolhas ligadas da mesma cor."""
        cor = self.grade[cel].cor if cor is None else cor
        vistos = {cel}
        pilha = [cel]
        while pilha:
            atual = pilha.pop()
            for v in _vizinhos(*atual):
                if v not in vistos and v in self.grade and self.grade[v].cor == cor:
                    vistos.add(v)
                    pilha.append(v)
        return vistos

    def _melhor_cor(self, cel):
        """Arco-íris: vira a cor que forma o maior grupo com os vizinhos."""
        melhor, tamanho = None, 0
        for v in _vizinhos(*cel):
            if v in self.grade:
                cor = self.grade[v].cor
                self.grade[cel].cor = cor
                n = len(self._grupo(cel, cor))
                if n > tamanho:
                    melhor, tamanho = cor, n
        if melhor is None:
            cores = self._cores_presentes()
            melhor = random.choice(cores)
        return melhor

    def _resolver(self, cel, tipo):
        x, y = _centro(cel[0], cel[1], self.teto)
        estourou = False

        if tipo == "bomba":
            alvo = [cel] + [v for v in _vizinhos(*cel) if v in self.grade]
            self.som("explosao", 0.6)
            self.tremer(0.2)
            self.aneis.append([x, y, (255, 170, 60), 0.0, 2.2])
            self.particulas.explodir((x, y), [(255, 170, 40), (255, 90, 30), (255, 240, 120),
                                              (80, 80, 90)], 36, 320, 0.7)
            self._estourar(alvo, cel)
            estourou = True
        else:
            if tipo == "arco":
                self.grade[cel].cor = self._melhor_cor(cel)
                self.particulas.explodir((x, y), CORES, 16, 200, 0.5)
            grupo = self._grupo(cel)
            if len(grupo) >= 3:
                self._estourar(grupo, cel)
                estourou = True

        if estourou:
            self.erros = 0
            self._derrubar_soltas()
        else:
            self.som("bater", 0.35)
            self.erros += 1
            if self.erros >= DISPAROS_TETO:
                self._descer_teto()

        self.versao += 1

        # Todos os pintinhos livres: FASE LIMPA!
        if not any(b.pintinho for b in self.grade.values()):
            self._fase_limpa()
            return

        if self._passou_da_linha():
            self._perder()
            return

        self._conferir_cores()

    def _estourar(self, celulas, origem):
        ox, oy = _centro(origem[0], origem[1], self.teto)
        ordem = sorted(celulas, key=lambda c: (_centro(c[0], c[1], self.teto)[0] - ox) ** 2 +
                       (_centro(c[0], c[1], self.teto)[1] - oy) ** 2)
        for i, cel in enumerate(ordem):
            b = self.grade.pop(cel, None)
            if b is None:
                continue
            x, y = _centro(cel[0], cel[1], self.teto)
            self.estouros.append([x, y, b.cor, i * 0.045, False])
            if b.pintinho:
                self._soltar_pintinho(x, y)
        ganho = PONTOS_ESTOURO * len(ordem)
        self.pontos += ganho
        self._texto(f"+{ganho}", (ox, oy + 36), TXT_ROXO, 16 if ganho < 50 else 20)
        self.som("acerto", 0.6)

    def _derrubar_soltas(self):
        """Bolhas sem ligação com o teto caem (valem o dobro)."""
        presas = set()
        pilha = [(0, c) for c in range(COLS) if (0, c) in self.grade]
        presas.update(pilha)
        while pilha:
            atual = pilha.pop()
            for v in _vizinhos(*atual):
                if v in self.grade and v not in presas:
                    presas.add(v)
                    pilha.append(v)
        soltas = [cel for cel in self.grade if cel not in presas]
        if not soltas:
            return
        soma_x = 0
        maior_y = 0
        for cel in soltas:
            b = self.grade.pop(cel)
            x, y = _centro(cel[0], cel[1], self.teto)
            soma_x += x
            maior_y = max(maior_y, y)
            self.caindo.append({"x": x, "y": y, "vx": random.uniform(-60, 60),
                                "vy": random.uniform(-160, -40), "cor": b.cor, "quicou": False})
            if b.pintinho:
                self._soltar_pintinho(x, y)
        ganho = PONTOS_QUEDA * len(soltas)
        self.pontos += ganho
        pos = (soma_x / len(soltas), maior_y + 10)
        self._texto(f"+{ganho} ×2!", pos, TXT_LARANJA, 20)
        self.som("moeda", 0.7)

    def _texto(self, msg, pos, cor, tamanho):
        """Texto flutuante sempre dentro da área do jogo (longe do HUD)."""
        x = max(X0 + 70, min(X1 - 70, pos[0]))
        y = max(130, min(LINHA_PERDE - 20, pos[1]))
        self.textos.adicionar(msg, (x, y), cor, tamanho)

    def _soltar_pintinho(self, x, y):
        self.salvos += 1
        self.pontos += PONTOS_PINTINHO
        self.pintinhos.append({"x0": x, "x": x, "y": y, "t": random.uniform(0, 3)})
        self._texto("piu!", (x, y - 16), TXT_LARANJA, 14)
        self._texto(f"+{PONTOS_PINTINHO}", (x, y + 14), TXT_ROXO, 14)
        self.som("revelar", 0.7)

    def _descer_teto(self):
        self.teto += ALT_LINHA
        self.erros = 0
        self.tremer(0.15)
        self.som("bater", 0.9)
        self._texto("O TETO DESCEU!", (LARGURA // 2, 440), TXT_ROSA, 20)

    def _passou_da_linha(self):
        for (l, c) in self.grade:
            if self.teto + R + l * ALT_LINHA + R > LINHA_PERDE:
                return True
        return False

    def _fase_limpa(self):
        self.pontos += PONTOS_FASE
        self._texto("FASE LIMPA!", (LARGURA // 2, 300), AMARELO, 32)
        self._texto(f"+{PONTOS_FASE}", (LARGURA // 2, 350), TXT_LARANJA, 20)
        self.som("vencer", 0.8)
        self.particulas.explodir((LARGURA // 2, 320), [self.jogador.cor, self.jogador.cor_clara,
                                                        AMARELO, BRANCO], 50, 380, 1.0)
        # As bolhas que sobraram estouram em cascata
        for i, (cel, b) in enumerate(sorted(self.grade.items(), key=lambda kv: kv[0][0])):
            x, y = _centro(cel[0], cel[1], self.teto)
            self.estouros.append([x, y, b.cor, 0.3 + i * 0.012, False])
        self.grade.clear()
        self.versao += 1
        self.transicao = 2.0

    def _perder(self):
        self.morto = True
        self.tempo_morto = 0.0
        self.tremer(0.35)
        self.som("erro", 0.9)
        self._texto("AS BOLHAS CHEGARAM!", (LARGURA // 2, 400), TXT_ROSA, 20)
        # Tudo despenca
        for cel, b in self.grade.items():
            x, y = _centro(cel[0], cel[1], self.teto)
            self.caindo.append({"x": x, "y": y, "vx": random.uniform(-80, 80),
                                "vy": random.uniform(-200, 0), "cor": b.cor, "quicou": False})
        self.grade.clear()
        self.versao += 1

    def _animar(self, dt):
        # Teto desliza suave até a posição de verdade
        self.teto_vis += (self.teto - self.teto_vis) * min(1.0, dt * 10)
        if abs(self.teto_vis - self.teto) < 0.5:
            self.teto_vis = self.teto

        # Estouros em cascata
        vivos = []
        for e in self.estouros:
            e[3] -= dt
            if e[3] <= 0:
                cor = CORES[e[2]] if isinstance(e[2], int) else BRANCO
                self.aneis.append([e[0], e[1], cor, 0.0, 1.0])
                self.particulas.explodir((e[0], e[1]), [cor, ui.clarear(cor, 60), BRANCO], 9, 200, 0.5,
                                         (2, 5))
            else:
                vivos.append(e)
        self.estouros = vivos

        self.aneis = [[x, y, cor, t + dt, esc] for x, y, cor, t, esc in self.aneis if t + dt < 0.35]

        # Bolhas caindo: quicam uma vez no chão e somem
        caindo = []
        for b in self.caindo:
            b["vy"] += 1500 * dt
            b["x"] += b["vx"] * dt
            b["y"] += b["vy"] * dt
            if b["y"] >= CHAO_BOLHAS - R and b["vy"] > 0:
                if b["quicou"]:
                    cor = CORES[b["cor"]]
                    self.particulas.explodir((b["x"], CHAO_BOLHAS - 10), [cor, BRANCO], 6, 140, 0.4, (2, 4))
                    continue
                b["quicou"] = True
                b["y"] = CHAO_BOLHAS - R
                b["vy"] = -b["vy"] * 0.45
            caindo.append(b)
        self.caindo = caindo

        # Pintinhos voam em zigue-zague
        voando = []
        for p in self.pintinhos:
            p["t"] += dt
            p["y"] -= 150 * dt
            p["x"] = p["x0"] + math.sin(p["t"] * 5) * 40
            if p["y"] > -40:
                voando.append(p)
        self.pintinhos = voando

    # --------------------------------------------------------
    # MIRA (linha pontilhada com 1 rebote)
    # --------------------------------------------------------

    def _trajetoria(self):
        origem = self._boca()
        chave = (round(self.angulo, 1), self.versao, self.teto, round(origem[0]), round(origem[1]))
        if chave == self._chave_caminho:
            return self._caminho
        x, y = origem
        a = math.radians(self.angulo)
        vx, vy = math.cos(a), -math.sin(a)
        pontos = []
        rebotes = 0
        passo = 6
        for _ in range(300):
            x += vx * passo
            y += vy * passo
            if x < X0 + R or x > X1 - R:
                if rebotes >= 1:
                    break
                rebotes += 1
                x = 2 * (X0 + R) - x if x < X0 + R else 2 * (X1 - R) - x
                vx = -vx
            if y - R <= self.teto or self._colide(x, y) is not None:
                break
            pontos.append((x, y))
        self._caminho = pontos
        self._chave_caminho = chave
        return pontos

    # --------------------------------------------------------
    # DESENHO
    # --------------------------------------------------------

    def desenhar_jogo(self, tela):
        tela.blit(self.fundo(self.jogador), (0, 0))
        teto = self.teto_vis

        self._desenhar_teto(tela, teto)

        # Bolhas da grade
        for (l, c), b in self.grade.items():
            x, y = _centro(l, c, teto)
            if y < -R:
                continue
            s = _sprite(b.cor, b.pintinho)
            tela.blit(s, (round(x - R), round(y - R)))

        # Estouros esperando a vez (ainda aparecem, tremendo)
        for x, y, cor, espera, pinto in self.estouros:
            s = _sprite(cor, pinto)
            dx = math.sin(self.tempo * 60 + x) * 2
            tela.blit(s, (round(x - R + dx), round(y - R)))

        # Anéis dos estouros
        for x, y, cor, t, esc in self.aneis:
            raio = int((R + t * 120) * (1 if esc < 2 else 1.6))
            larg = max(1, int(6 * (1 - t / 0.35)))
            pygame.draw.circle(tela, cor, (round(x), round(y)), raio, larg)

        # Linha de mira
        if self.estado == "jogando" and self._pode_mirar():
            pontos = self._trajetoria()
            anda = int(self.tempo * 24) % 4
            for i in range(anda, len(pontos), 4):
                x, y = pontos[i]
                pygame.draw.circle(tela, (90, 60, 120), (round(x), round(y)), 4)
                pygame.draw.circle(tela, BRANCO, (round(x), round(y)), 3)

        # Bolha voando
        if self.tiro:
            s = _sprite(self.tiro["tipo"])
            tela.blit(s, (round(self.tiro["x"] - R), round(self.tiro["y"] - R)))

        # Bolhas caindo
        for b in self.caindo:
            s = _sprite(b["cor"])
            tela.blit(s, (round(b["x"] - R), round(b["y"] - R)))

        self._desenhar_lancador(tela)

        # Pintinhos livres
        for p in self.pintinhos:
            s = _sprite_pintinho(int(p["t"] * 10) % 2)
            if math.cos(p["t"] * 5) < 0:
                s = pygame.transform.flip(s, True, False)
            tela.blit(s, s.get_rect(center=(round(p["x"]), round(p["y"]))))

        self.particulas.desenhar(tela)
        self.textos.desenhar(tela)

    def _pode_mirar(self):
        return not self.morto and self.transicao <= 0 and self.tiro is None

    def _desenhar_teto(self, tela, teto):
        # Tampo que empurra as bolhas para baixo quando o teto desce
        aviso = (self.erros == DISPAROS_TETO - 1 and not self.morto and self.transicao <= 0
                 and int(self.tempo * 6) % 2 == 0)
        topo = max(0, int(teto))
        if topo > 0:
            bloco = pygame.Rect(X0, 0, X1 - X0, topo)
            pygame.draw.rect(tela, (235, 160, 200), bloco)
            for x in range(X0 + 20, X1, 40):
                pygame.draw.line(tela, (220, 140, 185), (x, 0), (x, topo), 6)
        barra = pygame.Rect(X0 - 12, int(teto) - 12, X1 - X0 + 24, 14)
        cor = (255, 90, 120) if aviso else (255, 255, 255)
        pygame.draw.rect(tela, (0, 0, 0), barra.move(0, 3), border_radius=6)
        pygame.draw.rect(tela, cor, barra, border_radius=6)
        pygame.draw.rect(tela, (200, 110, 160), barra, 2, border_radius=6)

    def _desenhar_lancador(self, tela):
        # Bochechas infladas (squash horizontal) durante o sopro
        k = 0.0
        if self.sopro > 0:
            k = math.sin(math.pi * (1 - self.sopro / TEMPO_SOPRO))
        sx, sy = 1 + 0.18 * k, 1 - 0.08 * k
        incl = self._inclinacao()
        if self.morto:
            incl = math.sin(self.tempo_morto * 12) * 16 * max(0.0, 1 - self.tempo_morto / 1.8)

        cx, cy = LANCADOR[0], LANCADOR[1] - BOCA
        pygame.draw.ellipse(tela, (190, 200, 235), (cx - 34, cy + ALT_OVO / 2 - 6, 68, 14))

        sup = self.jogador.avatar(ALT_OVO)
        if k > 0.01:
            w, h = sup.get_size()
            sup = pygame.transform.smoothscale(sup, (round(w * sx), round(h * sy)))
        if abs(incl) > 0.5:
            sup = pygame.transform.rotate(sup, incl)
        # O pé do ovo fica parado; o centro sobe/desce com o squash
        cy_ovo = cy + ALT_OVO * (1 - sy) / 2
        tela.blit(sup, sup.get_rect(center=(round(cx), round(cy_ovo))))

        # Bolha crescendo na boca
        if not self.morto and self.transicao <= 0 and self.tiro is None:
            bx, by = self._boca()
            if self.sopro > 0:
                escala = ESCALA_BOCA + (1 - ESCALA_BOCA) * (1 - self.sopro / TEMPO_SOPRO)
            else:
                escala = ESCALA_BOCA * self.crescer
            if escala > 0.05:
                s = _bolha_escalada(self.atual, DIAM * escala)
                tela.blit(s, s.get_rect(center=(round(bx), round(by))))

        # Próxima bolha na saboneteira
        px, py = PROXIMA_POS
        pygame.draw.ellipse(tela, (150, 150, 190), (px - 32, py + 12, 64, 16))
        pygame.draw.ellipse(tela, (230, 235, 255), (px - 30, py + 10, 60, 14))
        s = _bolha_escalada(self.proxima, DIAM * PROXIMA_ESCALA)
        tela.blit(s, s.get_rect(center=(px, py)))
        ui.desenhar_texto(tela, "PRÓXIMA", (px, py - 36), 10, (90, 60, 120), "center", sombra=False)

        # Erros até o teto descer (bolinhas que vão se apagando)
        ex, ey = 620, 668
        restam = DISPAROS_TETO - self.erros
        perigo = restam == 1 and not self.morto
        cor_rot = (230, 60, 100) if perigo else (90, 60, 120)
        ui.desenhar_texto(tela, "TETO", (ex + 35, ey - 36), 10, cor_rot, "center", sombra=False)
        for i in range(DISPAROS_TETO):
            c = (ex + i * 14, ey)
            if i < restam:
                cor = (255, 90, 120) if perigo and int(self.tempo * 6) % 2 == 0 else (255, 255, 255)
                pygame.draw.circle(tela, (120, 80, 150), c, 6)
                pygame.draw.circle(tela, cor, c, 5)
            else:
                pygame.draw.circle(tela, (160, 140, 190), c, 5, 2)

    def desenhar_hud(self, tela):
        caixa = pygame.Rect(12, 12, 420, 48)
        ui.painel(tela, caixa, (20, 24, 40), BRANCO, 12, 3, sombra=False)
        ui.desenhar_texto(tela, f"PONTOS: {self.pontos}", (caixa.x + 16, caixa.centery), 14,
                          AMARELO, "midleft")
        rec = self.recorde()
        if rec is not None:
            ui.desenhar_texto(tela, f"RECORDE: {rec}", (caixa.x + 236, caixa.centery), 12,
                              (180, 200, 255), "midleft")

        # Fase e pintinhos presos (antes do botão de pausa)
        presos = sum(1 for b in self.grade.values() if b.pintinho)
        caixa = pygame.Rect(0, 12, 250, 48)
        caixa.right = LARGURA - 76
        ui.painel(tela, caixa, (20, 24, 40), BRANCO, 12, 3, sombra=False)
        ui.desenhar_texto(tela, f"FASE {self.fase}", (caixa.x + 16, caixa.centery), 12,
                          BRANCO, "midleft")
        s = _sprite_pintinho(int(self.tempo * 4) % 2)
        tela.blit(s, s.get_rect(center=(caixa.right - 92, caixa.centery - 1)))
        ui.desenhar_texto(tela, f"×{presos}", (caixa.right - 70, caixa.centery), 14,
                          AMARELO, "midleft")
