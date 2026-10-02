import os

import pygame

from settings import *
from core import trilhas

# ============================================================
# ÁUDIO
# ============================================================
# - Música: troca de faixa com fade (sem travar o jogo)
# - Efeitos sonoros: MP3 em musicas/sfx (ferramentas/compor_musicas.py)

FAIXAS_FIXAS = {
    "ovein": os.path.join(PASTA_MUSICAS, "Ovein.mp3"),
}

SFX = (
    "clique", "selecionar", "voltar", "comer", "moeda", "pulo", "mola", "boing",
    "explosao", "perder", "vencer", "recorde", "compra", "bandeira", "revelar",
    "virar", "bater", "erro", "asa", "ponto", "acerto",
)


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

        if self.ativo:
            pygame.mixer.set_num_channels(16)
            for nome in SFX:
                try:
                    self.sons[nome] = pygame.mixer.Sound(os.path.join(PASTA_SFX, nome + ".mp3"))
                except (pygame.error, FileNotFoundError):
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

    # --------------------------------------------------------
    # MÚSICA
    # --------------------------------------------------------

    def tocar(self, nome):
        """Troca a música com fade. Não faz nada se já estiver tocando."""
        if not self.ativo or nome == (self._proxima or self.atual):
            return

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
        return trilhas.arquivo(nome)

    def _iniciar(self, nome):
        self.atual = nome
        self._proxima = None
        self._saindo = False
        self._fade = 0.0

        try:
            pygame.mixer.music.load(self._arquivo(nome))
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
        if not self.ativo or not self.sons_ligados:
            return
        snd = self.sons.get(nome)
        if snd is not None:
            snd.set_volume(0.55 * volume)
            snd.play()
