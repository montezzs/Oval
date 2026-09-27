import os
import random

import pygame

from settings import *
from core import sintetizador as s
from core import trilhas

# ============================================================
# ÁUDIO
# ============================================================
# - Música: troca de faixa com fade (sem travar o jogo)
# - Efeitos sonoros: gerados na hora pelo sintetizador

FAIXAS_FIXAS = {
    "ovein": os.path.join(PASTA_MUSICAS, "Ovein.mp3"),
}


# ------------------------------------------------------------
# EFEITOS SONOROS
# ------------------------------------------------------------

def _sfx_clique():
    b = s.buffer_vazio(0.06)
    s.nota(b, 0, len(b), 900, "quadrada", 0.2, 0.25)
    return b


def _sfx_selecionar():
    b = s.buffer_vazio(0.1)
    m = len(b) // 2
    s.nota(b, 0, m, 660, "quadrada", 0.2, 0.25)
    s.nota(b, m, m, 990, "quadrada", 0.2, 0.25)
    return b


def _sfx_voltar():
    b = s.buffer_vazio(0.1)
    m = len(b) // 2
    s.nota(b, 0, m, 700, "quadrada", 0.2, 0.25)
    s.nota(b, m, m, 470, "quadrada", 0.2, 0.25)
    return b


def _sfx_comer():
    b = s.buffer_vazio(0.16)
    n = len(b) // 4
    for i, f in enumerate([523, 659, 784, 1046]):
        s.nota(b, i * n, n, f, "quadrada", 0.35, 0.5)
    return b


def _sfx_moeda():
    b = s.buffer_vazio(0.3)
    s.nota(b, 0, int(0.07 * s.TAXA), 988, "quadrada", 0.35, 0.5)
    s.nota(b, int(0.07 * s.TAXA), int(0.23 * s.TAXA), 1319, "quadrada", 0.35, 0.5,
           envelope="pluck")
    return b


def _sfx_pulo():
    b = s.buffer_vazio(0.16)
    s.nota(b, 0, len(b), 300, "quadrada", 0.35, 0.5, deslize=1.2)
    return b


def _sfx_mola():
    b = s.buffer_vazio(0.4)
    s.nota(b, 0, len(b), 220, "triangulo", 0.7, deslize=2.0, envelope="pluck")
    s.nota(b, 0, len(b), 440, "quadrada", 0.15, 0.25, deslize=2.0, envelope="pluck")
    return b


def _sfx_boing():
    b = s.buffer_vazio(0.3)
    m = len(b) // 2
    s.nota(b, 0, m, 260, "triangulo", 0.7, deslize=1.0)
    s.nota(b, m, m, 520, "triangulo", 0.6, deslize=-0.8, envelope="pluck")
    return b


def _sfx_explosao():
    rnd = random.Random(5)
    n = int(0.7 * s.TAXA)
    b = []
    ant = 0.0
    for i in range(n):
        t = i / n
        ant = ant * 0.85 + rnd.uniform(-1, 1) * 0.15
        b.append(ant * 4 * (1 - t) ** 2)
    s.nota(b, 0, int(0.3 * s.TAXA), 110, "seno", 0.8, deslize=-1.5, envelope="pluck")
    return b


def _sfx_perder():
    b = s.buffer_vazio(0.75)
    n = len(b) // 4
    for i, f in enumerate([392, 330, 262, 196]):
        s.nota(b, i * n, n, f, "quadrada", 0.35, 0.5,
               deslize=-0.1 if i == 3 else 0)
    return b


def _sfx_vencer():
    b = s.buffer_vazio(0.9)
    n = int(0.1 * s.TAXA)
    for i, f in enumerate([523, 659, 784, 1046]):
        s.nota(b, i * n, n, f, "quadrada", 0.3, 0.25)
    s.nota(b, 4 * n, len(b) - 4 * n, 1318, "quadrada", 0.3, 0.25, envelope="pluck")
    s.nota(b, 4 * n, len(b) - 4 * n, 784, "triangulo", 0.4, envelope="pluck")
    return b


def _sfx_bandeira():
    b = s.buffer_vazio(0.09)
    s.nota(b, 0, len(b), 440, "quadrada", 0.35, 0.25, deslize=0.5)
    return b


def _sfx_revelar():
    b = s.buffer_vazio(0.05)
    s.nota(b, 0, len(b), 1200, "triangulo", 0.5, envelope="pluck")
    return b


def _sfx_virar():
    rnd = random.Random(9)
    n = int(0.09 * s.TAXA)
    b = []
    for i in range(n):
        t = i / n
        b.append(rnd.uniform(-1, 1) * 0.35 * (t * (1 - t) * 4))
    return b


def _sfx_bater():
    b = s.buffer_vazio(0.12)
    s.nota(b, 0, len(b), 180, "seno", 0.9, deslize=-0.6, envelope="pluck")
    s.nota(b, 0, int(len(b) * 0.3), 700, "quadrada", 0.12, 0.5, envelope="pluck")
    return b


def _sfx_erro():
    b = s.buffer_vazio(0.22)
    s.nota(b, 0, len(b), 140, "quadrada", 0.35, 0.5)
    s.nota(b, 0, len(b), 147, "quadrada", 0.35, 0.5)
    return b


def _sfx_asa():
    rnd = random.Random(2)
    n = int(0.12 * s.TAXA)
    b = []
    ant = 0.0
    for i in range(n):
        t = i / n
        ant = ant * 0.7 + rnd.uniform(-1, 1) * 0.3
        b.append(ant * 1.4 * (1 - t) * min(1, t * 10))
    s.nota(b, 0, n, 500, "triangulo", 0.2, deslize=0.6, envelope="pluck")
    return b


def _sfx_ponto():
    b = s.buffer_vazio(0.25)
    m = int(0.08 * s.TAXA)
    s.nota(b, 0, m, 784, "quadrada", 0.3, 0.5)
    s.nota(b, m, len(b) - m, 1046, "quadrada", 0.3, 0.5, envelope="pluck")
    return b


def _sfx_acerto():
    b = s.buffer_vazio(0.35)
    n = int(0.08 * s.TAXA)
    for i, f in enumerate([659, 784, 1046]):
        s.nota(b, i * n, len(b) - i * n, f, "sino", 0.3, envelope="pluck")
    return b


def _sfx_tic():
    b = s.buffer_vazio(0.035)
    s.nota(b, 0, len(b), 1500, "quadrada", 0.25, 0.25, envelope="pluck")
    return b


def _sfx_levelup():
    b = s.buffer_vazio(1.0)
    n = int(0.07 * s.TAXA)
    for i, f in enumerate([523, 659, 784, 1046, 1318, 1568]):
        s.nota(b, i * n, n + 200, f, "quadrada", 0.25, 0.25)
    s.nota(b, 6 * n, len(b) - 6 * n, 2093, "sino", 0.35, envelope="pluck")
    s.nota(b, 6 * n, len(b) - 6 * n, 1046, "triangulo", 0.4, envelope="pluck")
    return b


def _sfx_conquista():
    b = s.buffer_vazio(0.7)
    n = int(0.09 * s.TAXA)
    for i, f in enumerate([784, 988, 1175]):
        s.nota(b, i * n, len(b) - i * n, f, "sino", 0.3, envelope="pluck")
    s.nota(b, 3 * n, len(b) - 3 * n, 1568, "triangulo", 0.3, envelope="pluck")
    return b


def _sfx_obturador():
    rnd = random.Random(12)
    n = int(0.16 * s.TAXA)
    b = []
    for i in range(n):
        t = i / n
        # dois "cliques" de ruído: abre e fecha
        env = max(0.0, 1 - t * 12) + max(0.0, 1 - abs(t - 0.55) * 14)
        b.append(rnd.uniform(-1, 1) * 0.5 * env)
    return b


SFX = {
    "clique": _sfx_clique,
    "selecionar": _sfx_selecionar,
    "voltar": _sfx_voltar,
    "comer": _sfx_comer,
    "moeda": _sfx_moeda,
    "pulo": _sfx_pulo,
    "mola": _sfx_mola,
    "boing": _sfx_boing,
    "explosao": _sfx_explosao,
    "perder": _sfx_perder,
    "vencer": _sfx_vencer,
    "bandeira": _sfx_bandeira,
    "revelar": _sfx_revelar,
    "virar": _sfx_virar,
    "bater": _sfx_bater,
    "erro": _sfx_erro,
    "asa": _sfx_asa,
    "ponto": _sfx_ponto,
    "acerto": _sfx_acerto,
    "tic": _sfx_tic,
    "levelup": _sfx_levelup,
    "conquista": _sfx_conquista,
    "obturador": _sfx_obturador,
}

# Efeitos que tocam MUITO: ganham versões com o tom um pouco
# diferente (sorteadas a cada vez) para não cansar o ouvido.
VARIAR_TOM = ("clique", "moeda", "pulo", "ponto", "bater", "boing", "comer", "revelar", "tic")
TONS = (0.94, 1.0, 1.06)


def _reamostrar(buf, fator):
    """Tom (e duração) multiplicados por `fator`."""
    n = max(1, int(len(buf) / fator))
    ultimo = len(buf) - 1
    saida = []
    for i in range(n):
        x = i * fator
        k = int(x)
        if k >= ultimo:
            saida.append(buf[ultimo])
        else:
            f = x - k
            saida.append(buf[k] * (1 - f) + buf[k + 1] * f)
    return saida


# ============================================================
# GERENCIADOR
# ============================================================

class Audio:

    TEMPO_FADE = 0.35

    def __init__(self, save):
        self.save = save
        self.ativo = pygame.mixer.get_init() is not None
        self.sons = {}
        self.atual = None          # faixa tocando
        self._proxima = None       # faixa esperando o fade
        self._fade = 0.0           # 1 = volume cheio
        self._saindo = False
        self._esperando = None     # trilha sendo gerada em segundo plano
        self._relogio_espera = 0.0

        if self.ativo:
            pygame.mixer.set_num_channels(16)
            for nome, gerar in SFX.items():
                try:
                    buf = gerar()
                    tons = TONS if nome in VARIAR_TOM else (1.0,)
                    variacoes = []
                    for fator in tons:
                        b = buf if fator == 1.0 else _reamostrar(buf, fator)
                        pcm = s.para_pcm(b, 0.7)
                        variacoes.append(pygame.mixer.Sound(file=s.wav_em_memoria(pcm)))
                    self.sons[nome] = variacoes
                except pygame.error:
                    pass

    # --------------------------------------------------------
    # PREFERÊNCIAS
    # --------------------------------------------------------

    @property
    def volume(self):
        return self.save["volume"]

    def proximo_volume(self):
        """Avança para o próximo nível de volume (0%, 25%...)."""
        atual = self.volume
        maiores = [v for v in VOLUMES if v > atual + 0.01]
        self.save["volume"] = maiores[0] if maiores else VOLUMES[0]
        self.save.salvar()
        self._aplicar_volume()

    @property
    def sons_ligados(self):
        return self.save["sons"]

    def alternar_sons(self):
        self.save["sons"] = not self.save["sons"]
        self.save.salvar()

    @property
    def volume_sfx(self):
        """0.0 = efeitos desligados."""
        if not self.save["sons"]:
            return 0.0
        return max(0.0, min(1.0, float(self.save["volume_sfx"])))

    def proximo_volume_sfx(self):
        """100% -> 75% -> 50% -> 25% -> DESLIGADO -> 100%..."""
        atual = self.volume_sfx
        menores = [v for v in reversed(VOLUMES) if v < atual - 0.01 and v > 0]
        if atual <= 0.01:
            self.save["sons"] = True
            self.save["volume_sfx"] = 1.0
        elif menores:
            self.save["volume_sfx"] = menores[0]
        else:
            self.save["sons"] = False
        self.save.salvar()

    # --------------------------------------------------------
    # MÚSICA
    # --------------------------------------------------------

    def tocar(self, nome):
        """Troca a música com fade. Não faz nada se já estiver tocando."""
        if not self.ativo or nome == (self._proxima or self._esperando or self.atual):
            return
        self._esperando = None
        self._marcar_ouvido(nome)

        if self.atual is None:
            self._iniciar(nome)
        else:
            self._proxima = nome
            self._saindo = True

    def _arquivo(self, nome):
        if nome in FAIXAS_FIXAS:
            return FAIXAS_FIXAS[nome]

        if not trilhas.existe(nome):
            raise ValueError(f"trilha desconhecida: {nome}")
        arq = trilhas.arquivo(nome)
        if not os.path.exists(arq):
            # Gera numa thread e toca quando ficar pronta (não trava a tela)
            trilhas.gerar_em_fundo(nome)
            return None
        return arq

    def _marcar_ouvido(self, nome):
        """Temas ouvidos aparecem na jukebox (seção TEMAS)."""
        if nome in trilhas.TEMAS:
            try:
                ouvidos = self.save["temas_ouvidos"]
            except KeyError:
                return
            if nome not in ouvidos:
                ouvidos.append(nome)
                self.save.salvar()

    def _iniciar(self, nome):
        self.atual = nome
        self._proxima = None
        self._saindo = False
        self._fade = 0.0

        try:
            arq = self._arquivo(nome)
            if arq is None:
                # Ainda gerando: silêncio até ficar pronta
                pygame.mixer.music.stop()
                self.atual = None
                self._esperando = nome
                return
            pygame.mixer.music.load(arq)
            pygame.mixer.music.set_volume(0.0)
            pygame.mixer.music.play(-1)
        except (pygame.error, OSError, ValueError):
            self.atual = None

    def reiniciar_musica(self):
        """Recomeça a música atual do zero (jogos de ritmo)."""
        if not self.ativo or self.atual is None:
            return
        try:
            pygame.mixer.music.play(-1)
        except pygame.error:
            pass
        self._fade = 1.0
        self._saindo = False
        self._aplicar_volume()

    def posicao_musica(self):
        """Segundos desde o (re)início da música, ou None sem áudio."""
        if not self.ativo or self.atual is None:
            return None
        ms = pygame.mixer.music.get_pos()
        return ms / 1000.0 if ms >= 0 else None

    def _aplicar_volume(self):
        if not self.ativo or self.atual is None:
            return
        ganho = GANHO_FAIXA.get(self.atual, GANHO_FAIXA_PADRAO)
        pygame.mixer.music.set_volume(self.volume * ganho * self._fade)

    def atualizar(self, dt):
        if not self.ativo:
            return

        passo = dt / self.TEMPO_FADE

        if self._esperando is not None:
            self._relogio_espera += dt
            if self._relogio_espera > 0.5:
                self._relogio_espera = 0.0
                nome = self._esperando
                if nome in trilhas.FALHARAM:
                    self._esperando = None
                elif os.path.exists(trilhas.arquivo(nome)):
                    self._esperando = None
                    self._iniciar(nome)
            return

        if self._saindo:
            self._fade -= passo
            if self._fade <= 0:
                self._fade = 0
                self._iniciar(self._proxima)
        elif self._fade < 1:
            self._fade = min(1.0, self._fade + passo)

        self._aplicar_volume()

    # --------------------------------------------------------
    # EFEITOS
    # --------------------------------------------------------

    def som(self, nome, volume=1.0):
        vol = self.volume_sfx if self.ativo else 0.0
        if vol <= 0:
            return
        variacoes = self.sons.get(nome)
        if variacoes:
            snd = random.choice(variacoes)
            snd.set_volume(min(1.0, 0.55 * volume * vol))
            snd.play()
