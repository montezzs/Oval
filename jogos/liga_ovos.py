from core.idioma import t
import heapq
import math
import random

import pygame

from settings import *
from core import ui
from core import assets
from core.jogador import Jogador
from jogos.base import MiniJogo

# ============================================================
# LIGA-OVOS
# ============================================================
# O tabuleiro está cheio de retratos da FAMÍLIA do seu ovo.
# Ache dois parentes iguais e ligue os dois com uma linha de até
# 2 curvas (ela pode passar pela borda, por fora das peças).
# Limpe o tabuleiro antes do tempo acabar! O SEU ovo vale dobrado.

COLS = 12
LINHAS = 8
TIPOS = 24                      # 24 parentes x 4 peças = 96
PECA_W, PECA_H = 62, 70
VAO = 6
PASSO_X = PECA_W + VAO
PASSO_Y = PECA_H + VAO
LARG_TAB = COLS * PECA_W + (COLS - 1) * VAO
ALT_TAB = LINHAS * PECA_H + (LINHAS - 1) * VAO
X0 = (LARGURA - LARG_TAB) // 2
Y0 = 90
BORDA = 10                      # distância das "pistas" da borda até as peças
PAINEL = pygame.Rect(X0 - 20, Y0 - 20, LARG_TAB + 40, ALT_TAB + 40)

TEMPO_INICIAL = 180.0
TEMPO_POR_PAR = 2.0
TEMPO_MENOS_POR_CICLO = 15.0
TEMPO_MINIMO = 90.0
DICAS = 3
DUR_DICA = 2.5
JANELA_COMBO = 2.0
COMBO_MAX = 10                  # o bônus do combo para de crescer no x10
DUR_RAIO = 0.3
DUR_SUMIR = 0.25
DUR_NIVEL = 2.8
DUR_FIM = 1.6
TENTATIVAS_EMBARALHAR = 50

MODOS = ["fixo", "baixo", "esquerda", "centro"]
NOMES_MODOS = {
    "fixo": "AS PEÇAS FICAM PARADAS",
    "baixo": "AS PEÇAS CAEM!",
    "esquerda": "AS PEÇAS VÃO PARA A ESQUERDA!",
    "centro": "AS PEÇAS VÃO PARA O CENTRO!",
}

# Direções em pares opostos: (0,1) (2,3)
DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1)]

TECLAS = {
    pygame.K_UP: (0, -1), pygame.K_w: (0, -1),
    pygame.K_DOWN: (0, 1), pygame.K_s: (0, 1),
    pygame.K_LEFT: (-1, 0), pygame.K_a: (-1, 0),
    pygame.K_RIGHT: (1, 0), pygame.K_d: (1, 0),
}

COR_FUNDO = (255, 245, 225)
COR_BOLINHA = (250, 225, 200)
COR_PECA = (250, 240, 220)
COR_PECA_BORDA = (200, 180, 150)
COR_SELECAO = (255, 214, 64)


def tempo_do_nivel(nivel):
    ciclo = (nivel - 1) // len(MODOS)
    return max(TEMPO_MINIMO, TEMPO_INICIAL - TEMPO_MENOS_POR_CICLO * ciclo)


def modo_do_nivel(nivel):
    return MODOS[(nivel - 1) % len(MODOS)]


def _formatar_tempo(seg):
    seg = max(0, int(math.ceil(seg)))
    return f"{seg // 60}:{seg % 60:02d}"


# ============================================================
# CAMINHOS (lógica pura: grade[l][c] = tipo ou None)
# ============================================================
# A grade lógica tem uma borda invisível de 1 célula em volta
# (colunas -1 e COLS, linhas -1 e LINHAS) por onde a linha passa.

def _dentro(c, l):
    return 0 <= c < COLS and 0 <= l < LINHAS


def _livre(grade, c, l):
    if c < -1 or c > COLS or l < -1 or l > LINHAS:
        return False
    if _dentro(c, l):
        return grade[l][c] is None
    return True


def buscar_caminho(grade, a, b):
    """
    Caminho de `a` até `b` com no máximo 2 curvas (3 segmentos) por
    casas vazias ou pela borda. Devolve a lista de casas (de a até b)
    com o menor número de curvas (e depois o mais curto), ou None.
    """
    if a == b:
        return None
    fila = []
    melhor = {}
    pai = {}
    n = 0
    for d, (dx, dy) in enumerate(DIRS):
        c, l = a[0] + dx, a[1] + dy
        if (c, l) == b or _livre(grade, c, l):
            st = (c, l, d)
            melhor[st] = (0, 1)
            pai[st] = None
            heapq.heappush(fila, (0, 1, n, st))
            n += 1

    while fila:
        curvas, passos, _, st = heapq.heappop(fila)
        if melhor.get(st) != (curvas, passos):
            continue
        c, l, d = st
        if (c, l) == b:
            caminho = []
            while st is not None:
                caminho.append((st[0], st[1]))
                st = pai[st]
            caminho.append(a)
            caminho.reverse()
            return caminho
        for nd, (dx, dy) in enumerate(DIRS):
            if nd == d ^ 1:
                continue
            nc = curvas + (nd != d)
            if nc > 2:
                continue
            x, y = c + dx, l + dy
            if (x, y) != b and not _livre(grade, x, y):
                continue
            ns = (x, y, nd)
            val = (nc, passos + 1)
            if ns in melhor and melhor[ns] <= val:
                continue
            melhor[ns] = val
            pai[ns] = st
            heapq.heappush(fila, (nc, passos + 1, n, ns))
            n += 1
    return None


def alcancaveis(grade, a):
    """Todas as peças que `a` consegue ligar (com até 2 curvas), sem olhar o tipo."""
    achadas = set()
    visitado = set()
    frente = [(a, None)]
    for _ in range(3):
        nova = []
        for (c0, l0), d_ant in frente:
            for d, (dx, dy) in enumerate(DIRS):
                if d_ant is not None and (d >> 1) == (d_ant >> 1):
                    continue            # seguir reto já foi feito pelo raio anterior
                c, l = c0, l0
                while True:
                    c += dx
                    l += dy
                    if c < -1 or c > COLS or l < -1 or l > LINHAS:
                        break
                    if _dentro(c, l) and grade[l][c] is not None:
                        if (c, l) != a:
                            achadas.add((c, l))
                        break
                    chave = (c, l, d >> 1)
                    if chave not in visitado:
                        visitado.add(chave)
                        nova.append(((c, l), d))
        frente = nova
    return achadas


def cantos(caminho):
    """Só os pontos onde a linha muda de direção (mais as pontas)."""
    if len(caminho) <= 2:
        return list(caminho)
    pts = [caminho[0]]
    for i in range(1, len(caminho) - 1):
        a, b, c = caminho[i - 1], caminho[i], caminho[i + 1]
        if (b[0] - a[0], b[1] - a[1]) != (c[0] - b[0], c[1] - b[1]):
            pts.append(b)
    pts.append(caminho[-1])
    return pts


def _centro(c, l):
    """Centro de uma casa lógica em pixels (a borda fica bem rente)."""
    if c < 0:
        x = X0 - BORDA
    elif c >= COLS:
        x = X0 + LARG_TAB + BORDA
    else:
        x = X0 + c * PASSO_X + PECA_W / 2
    if l < 0:
        y = Y0 - BORDA
    elif l >= LINHAS:
        y = Y0 + ALT_TAB + BORDA
    else:
        y = Y0 + l * PASSO_Y + PECA_H / 2
    return x, y


def _grupo_cabelo(cab):
    # Cabelos parecidos contam como um só: os ralinhos (1 e 2) e os de
    # "chapéu" (6 e 7). Ficam 6 grupos x 4 cores = 24 parentes bem diferentes.
    return {2: 1, 7: 6}.get(cab, cab)


# ============================================================
# PEÇA
# ============================================================

class Peca:

    def __init__(self, tipo, c, l):
        self.tipo = tipo
        self.x, self.y = _centro(c, l)          # posição visual (desliza)


class LigaOvos(MiniJogo):

    ID = "liga_ovos"
    TITULO = "LIGA-OVOS"
    TITULO_CURTO = "LIGA-OVOS"
    DESCRICAO = "Ache dois parentes iguais do seu ovo e ligue-os com até 2 curvas antes do tempo acabar!"
    COR = (240, 150, 120)
    INSTRUCOES = [
        "Clique em dois ovos IGUAIS da família.",
        "Se uma linha com até 2 curvas ligar os dois, eles somem!",
        "O SEU ovo vale o dobro. Pares rápidos fazem COMBO!",
        "Limpe tudo antes do tempo acabar. H = DICA.",
        "MOUSE ou SETAS/WASD + ESPAÇO • H dica",
    ]

    MOEDAS_POR = 100
    MOEDAS_MAX = 30

    _sprites = {}

    # --------------------------------------------------------
    # CENÁRIO: toalha de piquenique
    # --------------------------------------------------------

    @classmethod
    def criar_fundo(cls, jogador):
        sup = pygame.Surface((LARGURA, ALTURA))
        sup.fill(COR_FUNDO)
        # Bolinhas da toalha
        for j, y in enumerate(range(10, ALTURA + 30, 40)):
            for x in range(10 + (20 if j % 2 else 0), LARGURA + 30, 40):
                pygame.draw.circle(sup, COR_BOLINHA, (x, y), 8)
        # Barrado xadrez em cima e embaixo
        for x in range(0, LARGURA, 24):
            for i, y in enumerate((0, ALTURA - 12)):
                cor = (245, 170, 160) if (x // 24 + i) % 2 else (255, 214, 200)
                pygame.draw.rect(sup, cor, (x, y, 24, 12))

        # Painel branco do tabuleiro, com sombra
        sombra = pygame.Surface(PAINEL.size, pygame.SRCALPHA)
        pygame.draw.rect(sombra, (150, 110, 80, 70), sombra.get_rect(), border_radius=20)
        sup.blit(sombra, (PAINEL.x + 6, PAINEL.y + 8))
        pygame.draw.rect(sup, (255, 255, 255), PAINEL, border_radius=20)
        pygame.draw.rect(sup, (240, 220, 200), PAINEL, 3, border_radius=20)
        # Marquinhas das casas (aparecem quando as peças somem)
        for l in range(LINHAS):
            for c in range(COLS):
                r = pygame.Rect(X0 + c * PASSO_X, Y0 + l * PASSO_Y, PECA_W, PECA_H)
                pygame.draw.rect(sup, (248, 243, 236), r, border_radius=10)
        return sup

    @classmethod
    def sprite(cls, jogador, apar, eh_voce):
        chave = (apar, eh_voce, jogador.chave_visual() if eh_voce else ())
        s = cls._sprites.get(chave)
        if s is not None:
            return s
        s = pygame.Surface((PECA_W, PECA_H), pygame.SRCALPHA)
        fundo = (255, 236, 176) if eh_voce else COR_PECA
        borda = (225, 170, 50) if eh_voce else COR_PECA_BORDA
        pygame.draw.rect(s, ui.escurecer(fundo, 30), (0, 0, PECA_W, PECA_H), border_radius=10)
        pygame.draw.rect(s, fundo, (0, 0, PECA_W, PECA_H - 4), border_radius=10)
        pygame.draw.rect(s, borda, (0, 0, PECA_W, PECA_H), 2, border_radius=10)
        cx, cy = PECA_W / 2, PECA_H / 2 + 4
        pygame.draw.ellipse(s, ui.escurecer(fundo, 22), (cx - 16, cy + 17, 32, 8))
        jogador.desenhar(s, (cx, cy), 40, aparencia=apar)
        if eh_voce:
            ui.estrela(s, (PECA_W - 11, 11), 8, (255, 190, 30))
            ui.estrela(s, (PECA_W - 11, 11), 5, (255, 240, 150))
        if len(cls._sprites) > 80:
            cls._sprites.clear()
        cls._sprites[chave] = s
        return s

    @classmethod
    def desenhar_icone(cls, sup, jogador):
        w, h = sup.get_size()
        minha = jogador.aparencia()
        outra = ((minha[0] + 1) % len(assets.OVOS), (minha[1] + 3) % len(assets.CABELOS), minha[2], minha[3])
        terceira = ((minha[0] + 2) % len(assets.OVOS), (minha[1] + 5) % len(assets.CABELOS),
                    (minha[2] + 1) % len(assets.OLHOS), minha[3])
        esc = 0.62
        pw, ph = int(PECA_W * esc), int(PECA_H * esc)
        pecas = [outra, minha, terceira, outra, terceira, minha]
        x0 = w // 2 - (3 * pw + 2 * 6) // 2
        y0 = h // 2 - (2 * ph + 6) // 2 + 4
        pos = []
        for i, apar in enumerate(pecas):
            x = x0 + (i % 3) * (pw + 6)
            y = y0 + (i // 3) * (ph + 6)
            img = pygame.transform.smoothscale(cls.sprite(jogador, apar, apar == minha), (pw, ph))
            sup.blit(img, (x, y))
            pos.append((x + pw // 2, y + ph // 2))
        # Raio ligando os dois "você" (por cima, com uma curva)
        a, b = pos[1], pos[5]
        pts = [a, (a[0], y0 - 6), (b[0] + pw // 2 + 4, y0 - 6), (b[0] + pw // 2 + 4, b[1]), b]
        cor = jogador.cor if sum(jogador.cor) < 600 else (150, 170, 220)
        pygame.draw.lines(sup, ui.escurecer(cor, 90), False, pts, 7)
        pygame.draw.lines(sup, cor, False, pts, 4)
        pygame.draw.lines(sup, BRANCO, False, pts, 1)

    # --------------------------------------------------------
    # PARTIDA
    # --------------------------------------------------------

    def reiniciar(self):
        self.nivel = 1
        self.pares = 0
        self.dicas = DICAS
        self.combo = 0
        self.maior_combo = 0
        self.t_ultimo_par = -10.0
        self.relogio = 0.0

        self.fase = "jogando"           # jogando / nivel / acabou
        self.t_fase = 0.0
        self.bonus_tempo = 0

        self.selecionada = None
        self.cursor = [0, 0]
        self.teclado = False
        self.mouse = (-100, -100)
        self.dica = None                # (a, b) piscando
        self.t_dica = 0.0

        self.raios = []                 # [pontos_px, cor, t0]
        self.sumindo = []               # [peça, t0, dourada]
        self.coracoes = []              # [x, y, vx, vy, vida, cor]
        self.ultimo_segundo = None
        self.r_dica = pygame.Rect(718, 12, 176, 48)

        self._novo_tabuleiro()

    def _novo_tabuleiro(self):
        self.modo = modo_do_nivel(self.nivel)
        self.tempo_nivel = tempo_do_nivel(self.nivel)
        self.tempo_restante = self.tempo_nivel
        self.familia = self._sortear_familia()
        self.minha = self.jogador.aparencia()
        self.imagens = [self.sprite(self.jogador, apar, apar == self.minha) for apar in self.familia]

        tipos = [t for t in range(TIPOS) for _ in range(4)]
        random.shuffle(tipos)
        self.grade = [[None] * COLS for _ in range(LINHAS)]
        self.pecas = [[None] * COLS for _ in range(LINHAS)]
        for i, t in enumerate(tipos):
            c, l = i % COLS, i // COLS
            self.grade[l][c] = t
            p = Peca(t, c, l)
            self.pecas[l][c] = p
        self.selecionada = None
        self.dica = None
        if self._achar_jogada() is None:
            self._embaralhar(silencioso=True)

    def _sortear_familia(self):
        """
        24 parentes: o próprio jogador + 23 combinações que diferem
        dele e entre si pelo par (cor, cabelo). Olhos e boca variam.
        """
        minha = self.jogador.aparencia()
        usados = {(minha[0], _grupo_cabelo(minha[1]))}
        lista = [tuple(minha)]
        cands = [(o, c) for o in range(len(assets.OVOS)) for c in range(len(assets.CABELOS))]
        random.shuffle(cands)
        # Espalha as cores: vai pegando uma de cada cor por vez
        vezes = {}
        ordem = []
        for oc in cands:
            vezes[oc[0]] = vezes.get(oc[0], 0) + 1
            ordem.append((vezes[oc[0]], oc))
        ordem.sort(key=lambda item: item[0])
        cands = [oc for _, oc in ordem]
        for ovo, cab in cands:
            if len(lista) >= TIPOS:
                break
            g = (ovo, _grupo_cabelo(cab))
            if g in usados:
                continue
            usados.add(g)
            lista.append((ovo, cab, random.randrange(len(assets.OLHOS)), random.randrange(len(assets.BOCAS))))
        # Garantia (nunca deve acontecer): completa com qualquer combinação diferente
        while len(lista) < TIPOS:
            cand = (random.randrange(len(assets.OVOS)), random.randrange(len(assets.CABELOS)),
                    random.randrange(len(assets.OLHOS)), random.randrange(len(assets.BOCAS)))
            if cand not in lista:
                lista.append(cand)
        random.shuffle(lista)
        return lista

    # --------------------------------------------------------
    # BUSCA DE JOGADAS
    # --------------------------------------------------------

    def _ocupadas(self):
        return [(c, l) for l in range(LINHAS) for c in range(COLS) if self.grade[l][c] is not None]

    def _achar_jogada(self):
        """Algum par que dá para ligar agora (ou None)."""
        for a in self._ocupadas():
            t = self.grade[a[1]][a[0]]
            for b in alcancaveis(self.grade, a):
                if self.grade[b[1]][b[0]] == t:
                    return (a, b)
        return None

    def _embaralhar(self, silencioso=False):
        """
        Troca as peças de lugar até existir pelo menos 1 par ligável.
        As posições não mudam, então as ligações possíveis entre as
        casas são calculadas uma vez só.
        """
        casas = self._ocupadas()
        if len(casas) < 2:
            return
        ligacoes = [(a, b) for a in casas for b in alcancaveis(self.grade, a) if a < b]
        if not ligacoes:
            # Peças todas isoladas (quase impossível): junta tudo embaixo,
            # aí sempre existem casas ligáveis (vizinhas ou pela borda)
            self._compactar("baixo")
            casas = self._ocupadas()
            ligacoes = [(a, b) for a in casas for b in alcancaveis(self.grade, a) if a < b]
        pecas = [self.pecas[l][c] for c, l in casas]
        ok = False
        for _ in range(TENTATIVAS_EMBARALHAR):
            random.shuffle(pecas)
            tipo = {casa: p.tipo for casa, p in zip(casas, pecas)}
            if any(tipo[a] == tipo[b] for a, b in ligacoes):
                ok = True
                break
        if not ok and ligacoes:
            # Força: coloca duas peças iguais numa ligação possível
            a, b = random.choice(ligacoes)
            ia, ib = casas.index(a), casas.index(b)
            par = next(i for i, p in enumerate(pecas) if i != ia and p.tipo == pecas[ia].tipo)
            pecas[ib], pecas[par] = pecas[par], pecas[ib]
        for (c, l), p in zip(casas, pecas):
            self.pecas[l][c] = p
            self.grade[l][c] = p.tipo
        self.selecionada = None
        self.dica = None
        if not silencioso:
            self.som("virar", 0.8)
            self.textos.adicionar(t("EMBARALHANDO!"), (LARGURA // 2, Y0 + ALT_TAB // 2), (120, 90, 220), 20)

    # --------------------------------------------------------
    # AÇÕES
    # --------------------------------------------------------

    def _casa_em(self, pos):
        c = int((pos[0] - X0 + VAO / 2) // PASSO_X)
        l = int((pos[1] - Y0 + VAO / 2) // PASSO_Y)
        if _dentro(c, l) and X0 - VAO <= pos[0] < X0 + LARG_TAB + VAO and \
                Y0 - VAO <= pos[1] < Y0 + ALT_TAB + VAO:
            return (c, l)
        return None

    def evento_jogo(self, e):
        if e.type == pygame.MOUSEMOTION:
            self.mouse = e.pos
            self.teclado = False
            return
        if self.fase != "jogando":
            return

        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.mouse = e.pos
            self.teclado = False
            if self.r_dica.collidepoint(e.pos):
                self._usar_dica()
                return
            casa = self._casa_em(e.pos)
            if casa is not None:
                self.cursor = list(casa)
                self._escolher(casa)

        elif e.type == pygame.KEYDOWN:
            if e.key in TECLAS:
                dc, dl = TECLAS[e.key]
                if self.teclado:
                    self.cursor[0] = max(0, min(COLS - 1, self.cursor[0] + dc))
                    self.cursor[1] = max(0, min(LINHAS - 1, self.cursor[1] + dl))
                elif self.selecionada:
                    self.cursor = list(self.selecionada)
                self.teclado = True
            elif e.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER):
                self.teclado = True
                self._escolher(tuple(self.cursor))
            elif e.key == pygame.K_h:
                self._usar_dica()

    def _escolher(self, casa):
        c, l = casa
        if self.grade[l][c] is None:
            self.selecionada = None
            return
        if self.selecionada is None:
            self.selecionada = casa
            self.som("clique", 0.6)
            return
        if self.selecionada == casa:
            self.selecionada = None
            self.som("voltar", 0.4)
            return

        a = self.selecionada
        if self.grade[a[1]][a[0]] == self.grade[l][c]:
            caminho = buscar_caminho(self.grade, a, casa)
            if caminho:
                self._ligar(a, casa, caminho)
                return
            self.som("erro", 0.5)
            x, y = _centro(c, l)
            self.textos.adicionar(t("SEM CAMINHO!"), (x, y - 30), (230, 80, 80), 12)
            self.selecionada = None
            return
        # Tipo diferente: passa a seleção para a nova peça
        self.selecionada = casa
        self.som("clique", 0.6)

    def _usar_dica(self):
        if self.dicas <= 0:
            self.som("erro", 0.4)
            return
        par = self._achar_jogada()
        if par is None:
            return
        self.dicas -= 1
        self.dica = par
        self.t_dica = DUR_DICA
        self.som("selecionar", 0.7)

    def _ligar(self, a, b, caminho):
        tipo = self.grade[a[1]][a[0]]
        eh_voce = self.familia[tipo] == self.minha

        # Raio
        cor = Jogador.cor_do_ovo(self.familia[tipo][0])
        if sum(cor) > 600:
            cor = (150, 170, 225)
        self.raios.append([[_centro(*p) for p in cantos(caminho)], cor, self.relogio])

        # Peças fazem "pop" e soltam corações
        for c, l in (a, b):
            p = self.pecas[l][c]
            self.sumindo.append([p, self.relogio, eh_voce])
            self.grade[l][c] = None
            self.pecas[l][c] = None
            for _ in range(3):
                self.coracoes.append([p.x, p.y, random.uniform(-60, 60), random.uniform(-160, -90),
                                      1.0, random.choice([(235, 60, 90), (255, 120, 160), (255, 90, 120)])])
            if eh_voce:
                self.particulas.explodir((p.x, p.y), [AMARELO, (255, 240, 170), BRANCO], 16, 200, 0.7)
        self.selecionada = None
        if self.dica and (a in self.dica or b in self.dica):
            self.dica = None

        # Pontos, combo e tempo
        if self.relogio - self.t_ultimo_par < JANELA_COMBO:
            self.combo += 1
        else:
            self.combo = 1
        self.t_ultimo_par = self.relogio
        self.maior_combo = max(self.maior_combo, self.combo)
        ganho = 20 if eh_voce else 10
        if self.combo >= 2:
            ganho += 5 * (min(self.combo, COMBO_MAX) - 1)
        self.pontos += ganho
        self.pares += 1
        self.tempo_restante += TEMPO_POR_PAR

        meio = ((_centro(*a)[0] + _centro(*b)[0]) / 2, (_centro(*a)[1] + _centro(*b)[1]) / 2)
        if eh_voce:
            self.textos.adicionar(t("VOCÊ! +{n}", n=ganho), (meio[0], meio[1] - 10), (230, 150, 0), 16)
            self.som("moeda", 0.8)
        else:
            self.textos.adicionar(f"+{ganho}", (meio[0], meio[1] - 10), (240, 100, 120), 14)
            self.som("acerto", 0.6)
        if self.combo >= 2:
            self.textos.adicionar(f"COMBO ×{self.combo}", (meio[0], meio[1] + 16), (120, 90, 220), 14)

        self._compactar()

        if not self._ocupadas():
            self._completar_nivel()
        elif self._achar_jogada() is None:
            self._embaralhar()

    def _compactar(self, modo=None):
        """Faz as peças escorregarem conforme o modo do nível."""
        modo = modo or self.modo
        if modo == "fixo":
            return
        nova = [[None] * COLS for _ in range(LINHAS)]
        if modo == "baixo":
            for c in range(COLS):
                coluna = [self.pecas[l][c] for l in range(LINHAS - 1, -1, -1) if self.pecas[l][c]]
                for i, p in enumerate(coluna):
                    nova[LINHAS - 1 - i][c] = p
        elif modo == "esquerda":
            for l in range(LINHAS):
                linha = [p for p in self.pecas[l] if p]
                for i, p in enumerate(linha):
                    nova[l][i] = p
        else:   # centro: metade esquerda vai para a direita e vice-versa
            meio = COLS // 2
            for l in range(LINHAS):
                esq = [p for p in self.pecas[l][:meio] if p]
                dir_ = [p for p in self.pecas[l][meio:] if p]
                for i, p in enumerate(reversed(esq)):
                    nova[l][meio - 1 - i] = p
                for i, p in enumerate(dir_):
                    nova[l][meio + i] = p
        self.pecas = nova
        self.grade = [[p.tipo if p else None for p in linha] for linha in nova]
        self.dica = None

    def _completar_nivel(self):
        self.bonus_tempo = int(self.tempo_restante) * 2
        self.pontos += self.bonus_tempo
        self.fase = "nivel"
        self.t_fase = 0.0
        self.som("vencer", 0.8)
        self.tremer(0.2)
        for _ in range(8):
            self.particulas.explodir((random.uniform(PAINEL.left, PAINEL.right),
                                      random.uniform(PAINEL.top, PAINEL.bottom)),
                                     [AMARELO, (255, 120, 150), (120, 200, 255), (140, 230, 120),
                                      self.jogador.cor], 16, 260, 1.0)

    # --------------------------------------------------------
    # LÓGICA
    # --------------------------------------------------------

    def atualizar_jogo(self, dt):
        self.relogio += dt

        # Peças deslizando para a posição certa
        k = min(1.0, dt * 14)
        for l in range(LINHAS):
            for c in range(COLS):
                p = self.pecas[l][c]
                if p:
                    tx, ty = _centro(c, l)
                    p.x += (tx - p.x) * k
                    p.y += (ty - p.y) * k
                    if abs(tx - p.x) < 0.3 and abs(ty - p.y) < 0.3:
                        p.x, p.y = tx, ty

        self.raios = [r for r in self.raios if self.relogio - r[2] < DUR_RAIO]
        self.sumindo = [s for s in self.sumindo if self.relogio - s[1] < DUR_SUMIR]
        vivos = []
        for h in self.coracoes:
            h[0] += h[2] * dt
            h[1] += h[3] * dt
            h[3] += 120 * dt
            h[4] -= dt
            if h[4] > 0:
                vivos.append(h)
        self.coracoes = vivos

        if self.dica:
            self.t_dica -= dt
            if self.t_dica <= 0:
                self.dica = None

        if self.fase == "jogando":
            self.tempo_restante -= dt
            seg = int(math.ceil(self.tempo_restante))
            if seg != self.ultimo_segundo:
                self.ultimo_segundo = seg
                if 0 < seg <= 10:
                    self.som("clique", 0.35)
            if self.tempo_restante <= 0:
                self.tempo_restante = 0
                self.fase = "acabou"
                self.t_fase = 0.0
                self.selecionada = None
                self.som("erro", 0.7)
                self.tremer(0.25)

        elif self.fase == "nivel":
            self.t_fase += dt
            if self.t_fase >= DUR_NIVEL:
                self.nivel += 1
                self.fase = "jogando"
                self._novo_tabuleiro()

        elif self.fase == "acabou":
            self.t_fase += dt
            if self.t_fase >= DUR_FIM:
                self.terminar(titulo=t("O TEMPO ACABOU!"),
                              linhas=[t("PONTOS: {n}", n=self.pontos),
                                      t("NÍVEL: {n}  •  PARES: {p}", n=self.nivel, p=self.pares),
                                      t("MAIOR COMBO: ×{n}", n=self.maior_combo)])

    # --------------------------------------------------------
    # DESENHO
    # --------------------------------------------------------

    def desenhar_jogo(self, tela):
        tela.blit(self.fundo(self.jogador), (0, 0))

        hover = None
        if self.fase == "jogando" and self.estado == "jogando" and not self.teclado:
            hover = self._casa_em(self.mouse)
        pulso = 0.5 + 0.5 * math.sin(self.tempo * 8)

        for l in range(LINHAS):
            for c in range(COLS):
                p = self.pecas[l][c]
                if p is None:
                    continue
                img = self.imagens[p.tipo]
                x = p.x - PECA_W / 2
                y = p.y - PECA_H / 2
                sel = (c, l) == self.selecionada
                if sel or (c, l) == hover:
                    y -= 3
                tela.blit(img, (int(x), int(y)))
                r = pygame.Rect(int(x), int(y), PECA_W, PECA_H)
                if sel:
                    cor = ui.misturar(COR_SELECAO, (255, 250, 200), pulso)
                    pygame.draw.rect(tela, (150, 100, 0), r.inflate(10, 10), 2, border_radius=13)
                    pygame.draw.rect(tela, cor, r.inflate(6, 6), 4, border_radius=12)
                elif (c, l) == hover:
                    pygame.draw.rect(tela, (255, 200, 120), r.inflate(4, 4), 2, border_radius=11)
                if self.dica and (c, l) in self.dica and int(self.tempo * 6) % 2 == 0:
                    pygame.draw.rect(tela, (60, 200, 120), r.inflate(8, 8), 4, border_radius=12)

        # Cursor do teclado
        if self.teclado and self.fase == "jogando":
            x, y = _centro(*self.cursor)
            r = pygame.Rect(0, 0, PECA_W + 10, PECA_H + 10)
            r.center = (int(x), int(y))
            k = int(2 * math.sin(self.tempo * 8))
            pygame.draw.rect(tela, (40, 60, 140), r.inflate(4 + k, 4 + k), 5, border_radius=14)
            pygame.draw.rect(tela, (90, 160, 255), r.inflate(2 + k, 2 + k), 3, border_radius=14)

        self._desenhar_raios(tela)

        # Peças sumindo ("pop" 1.2 -> 0)
        for p, t0, dourada in self.sumindo:
            q = (self.relogio - t0) / DUR_SUMIR
            esc = 1.0 + q if q < 0.2 else 1.2 * (1 - (q - 0.2) / 0.8)
            if esc <= 0.05:
                continue
            img = self.imagens[p.tipo]
            img = pygame.transform.smoothscale(img, (max(1, int(PECA_W * esc)), max(1, int(PECA_H * esc))))
            tela.blit(img, img.get_rect(center=(int(p.x), int(p.y))))
            if dourada and int(self.tempo * 20) % 2 == 0:
                r = img.get_rect(center=(int(p.x), int(p.y)))
                pygame.draw.rect(tela, (255, 200, 40), r.inflate(6, 6), 4, border_radius=12)

        for x, y, _, _, vida, cor in self.coracoes:
            ui.coracao(tela, (int(x), int(y)), int(10 + 6 * vida), cor)

        self.particulas.desenhar(tela)
        self.textos.desenhar(tela)

        if self.fase == "nivel":
            self._desenhar_nivel(tela)
        elif self.fase == "acabou":
            ui.veu(tela, 90)
            ui.desenhar_texto(tela, t("O TEMPO ACABOU!"), (LARGURA // 2, ALTURA // 2), 28, (255, 120, 120), "center")

    def _desenhar_raios(self, tela):
        for pontos, cor, t0 in self.raios:
            q = (self.relogio - t0) / DUR_RAIO
            # A linha "se desenha" do começo até o fim e depois pisca
            total = sum(math.dist(pontos[i], pontos[i + 1]) for i in range(len(pontos) - 1))
            alcance = total * min(1.0, q / 0.45)
            rnd = random.Random(int(self.relogio * 30))
            pts = [pontos[0]]
            andou = 0.0
            for i in range(len(pontos) - 1):
                a, b = pontos[i], pontos[i + 1]
                seg = math.dist(a, b)
                if seg == 0:
                    continue
                passos = max(1, int(seg / 16))
                for k in range(1, passos + 1):
                    f = k / passos
                    if andou + seg * f > alcance:
                        break
                    x = a[0] + (b[0] - a[0]) * f
                    y = a[1] + (b[1] - a[1]) * f
                    if k < passos:      # tremidinha de raio (menos nas quinas)
                        nx, ny = -(b[1] - a[1]) / seg, (b[0] - a[0]) / seg
                        j = rnd.uniform(-4, 4)
                        x, y = x + nx * j, y + ny * j
                    pts.append((x, y))
                andou += seg
                if andou > alcance:
                    break
            if len(pts) < 2:
                continue
            grossura = 1.0 if q < 0.7 else max(0.3, (1 - q) / 0.3)
            pygame.draw.lines(tela, ui.escurecer(cor, 100), False, pts, max(2, int(12 * grossura)))
            pygame.draw.lines(tela, ui.clarear(cor, 50), False, pts, max(2, int(8 * grossura)))
            pygame.draw.lines(tela, BRANCO, False, pts, max(1, int(3 * grossura)))
            for p in (pts[0], pts[-1]):
                pygame.draw.circle(tela, BRANCO, (int(p[0]), int(p[1])), max(2, int(6 * grossura)))

    def _desenhar_nivel(self, tela):
        ui.veu(tela, 120)
        caixa = pygame.Rect(0, 0, 640, 280)
        caixa.center = (LARGURA // 2, ALTURA // 2)
        ui.painel(tela, caixa, (28, 32, 56), AMARELO, 20, 4)
        ui.desenhar_texto(tela, t("NÍVEL {n} COMPLETO!", n=self.nivel), (caixa.centerx, caixa.y + 28), 24,
                          AMARELO, "midtop")
        ui.desenhar_texto(tela, t("BÔNUS DE TEMPO: +{n}", n=self.bonus_tempo), (caixa.centerx, caixa.y + 78), 14,
                          BRANCO, "midtop")
        dy = -abs(math.sin(self.t_fase * 6)) * 14
        self.jogador.desenhar(tela, (caixa.centerx, caixa.y + 150 + dy), 60)
        prox = self.nivel + 1
        ui.desenhar_texto(tela, t("NÍVEL {n}: {modo}", n=prox, modo=t(NOMES_MODOS[modo_do_nivel(prox)])),
                          (caixa.centerx, caixa.y + 206), 12, (180, 220, 255), "midtop")
        ui.desenhar_texto(tela, t("TEMPO: {v}", v=_formatar_tempo(tempo_do_nivel(prox))),
                          (caixa.centerx, caixa.y + 232), 12, (180, 220, 255), "midtop")

    def desenhar_hud(self, tela):
        fundo = (20, 24, 40)

        # Pontos e recorde
        caixa = pygame.Rect(12, 12, 220, 48)
        ui.painel(tela, caixa, fundo, BRANCO, 12, 3, sombra=False)
        ui.desenhar_texto(tela, t("PONTOS: {n}", n=self.pontos), (caixa.x + 12, caixa.y + 9), 12, AMARELO)
        rec = self.recorde()
        ui.desenhar_texto(tela, t("RECORDE: {v}", v=rec if rec is not None else '--'), (caixa.x + 12, caixa.y + 28),
                          10, (180, 220, 255))

        # Tempo (relógio + barra)
        caixa2 = pygame.Rect(caixa.right + 12, 12, 300, 48)
        ui.painel(tela, caixa2, fundo, BRANCO, 12, 3, sombra=False)
        frac = max(0.0, min(1.0, self.tempo_restante / self.tempo_nivel))
        pouco = self.tempo_restante <= 15 and self.fase == "jogando"
        rc = (caixa2.x + 24, caixa2.centery)
        pygame.draw.circle(tela, BRANCO, rc, 13)
        pygame.draw.circle(tela, (40, 44, 70), rc, 13, 3)
        ang = -math.pi / 2 + math.tau * (1 - frac)
        pygame.draw.line(tela, (220, 50, 50), rc, (rc[0] + math.cos(ang) * 9, rc[1] + math.sin(ang) * 9), 2)
        barra = pygame.Rect(caixa2.x + 46, caixa2.centery - 8, 160, 16)
        pygame.draw.rect(tela, (50, 54, 80), barra, border_radius=8)
        if frac > 0:
            cor = (240, 70, 70) if pouco and int(self.tempo * 4) % 2 == 0 else \
                ui.misturar((240, 90, 70), (110, 210, 110), min(1.0, frac * 2))
            pygame.draw.rect(tela, cor, (barra.x, barra.y, max(8, int(barra.w * frac)), barra.h), border_radius=8)
        pygame.draw.rect(tela, BRANCO, barra, 2, border_radius=8)
        ui.desenhar_texto(tela, _formatar_tempo(self.tempo_restante), (caixa2.right - 12, caixa2.centery + 1),
                          14, (255, 130, 130) if pouco else BRANCO, "midright")

        # Nível (com setinha do modo)
        caixa3 = pygame.Rect(caixa2.right + 12, 12, 150, 48)
        ui.painel(tela, caixa3, fundo, BRANCO, 12, 3, sombra=False)
        ui.desenhar_texto(tela, t("NÍVEL"), (caixa3.x + 12, caixa3.y + 9), 10, (180, 220, 255))
        ui.desenhar_texto(tela, str(self.nivel), (caixa3.x + 12, caixa3.y + 26), 14, BRANCO)
        seta = {"fixo": "•", "baixo": "↓", "esquerda": "←", "centro": "→←"}[self.modo]
        ui.desenhar_texto(tela, seta, (caixa3.right - 14, caixa3.centery + 1), 14, AMARELO, "midright")

        # Botão de dica
        r = self.r_dica
        hover = r.collidepoint(self.mouse) and self.dicas > 0 and self.fase == "jogando"
        ui.painel(tela, r, (60, 70, 120) if hover else fundo, AMARELO if hover else BRANCO, 12, 3, sombra=False)
        ui.desenhar_texto(tela, t("DICA (H)"), (r.x + 12, r.centery + 1), 12,
                          BRANCO if self.dicas else (120, 120, 140), "midleft")
        for i in range(DICAS):
            cx = r.right - 44 + i * 14
            cheia = i < self.dicas
            pygame.draw.circle(tela, (255, 220, 90) if cheia else (70, 74, 100), (cx, r.centery - 2), 5)
            pygame.draw.rect(tela, (180, 180, 190) if cheia else (70, 74, 100), (cx - 3, r.centery + 3, 6, 4))
