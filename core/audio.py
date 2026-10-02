import os
import random

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
    "tic", "levelup", "conquista", "obturador",
)

# Efeitos que tocam MUITO têm versões com o tom um pouco diferente
# (<nome>_baixo.mp3 e <nome>_alto.mp3), sorteadas a cada vez para
# não cansar o ouvido.
VARIAR_TOM = ("clique", "moeda", "pulo", "ponto", "bater", "boing", "comer", "revelar", "tic")
SUFIXOS_TOM = ("_baixo", "", "_alto")


# ============================================================
# GERENCIADOR
# ============================================================

class Audio:

    TEMPO_FADE = 0.35

    def __init__(self, save):
        self.save = save
        self.ativo = pygame.mixer.get_init() is not None
        self.sons = {}             # nome -> [variações]
        self.atual = None          # faixa tocando
        self._proxima = None       # faixa esperando o fade
        self._fade = 0.0           # 1 = volume cheio
        self._saindo = False

        if self.ativo:
            pygame.mixer.set_num_channels(16)
            for nome in SFX:
                sufixos = SUFIXOS_TOM if nome in VARIAR_TOM else ("",)
                variacoes = []
                for suf in sufixos:
                    try:
                        variacoes.append(pygame.mixer.Sound(
                            os.path.join(PASTA_SFX, nome + suf + ".mp3")))
                    except (pygame.error, FileNotFoundError):
                        pass
                if variacoes:
                    self.sons[nome] = variacoes

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
        if not self.ativo or nome == (self._proxima or self.atual):
            return
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
        return trilhas.arquivo(nome)

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
        vol = self.volume_sfx if self.ativo else 0.0
        if vol <= 0:
            return
        variacoes = self.sons.get(nome)
        if variacoes:
            snd = random.choice(variacoes)
            snd.set_volume(min(1.0, 0.55 * volume * vol))
            snd.play()
