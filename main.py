import os
import sys

import pygame

from settings import *
from core import assets, ui
from core.audio import Audio
from core.janela import Janela
from core.jogador import Jogador
from core.necessidades import Necessidades
from core.save import Save
from cenas.casa import CenaCasa
from cenas.criador import CenaCriador
from cenas.nome import CenaNome

# ============================================================
# OVEIO / OVAL
# ============================================================
# Arquivo principal: cria a janela, carrega tudo e roda o loop.
# Cada tela do jogo é uma "cena" (pasta cenas/ e jogos/).
#
#   cenas/nome.py        -> digitar o nome
#   cenas/criador.py     -> escolher ovo, cabelo, olhos e boca
#   cenas/casa.py        -> jogo principal (cômodos SOL/CASA/BRINCAR)
#   cenas/pausa.py       -> menu de pausa
#   cenas/menu_jogos.py  -> escolher um mini jogo
#   jogos/*.py           -> os mini jogos

TEMPO_TRANSICAO = 0.24


class App:

    def __init__(self):
        pygame.mixer.pre_init(FREQUENCIA_AUDIO, -16, 2, 512)
        pygame.init()

        # Se não houver placa de som, o jogo roda sem áudio
        if pygame.mixer.get_init() is None:
            try:
                pygame.mixer.init()
            except pygame.error:
                pass

        icone = pygame.image.load(caminho("Img", "personagem", "P_verde.png"))
        pygame.display.set_icon(icone)
        pygame.display.set_caption(TITULO)
        self.save = Save.carregar()
        self.necessidades = Necessidades(self.save)

        # Janela redimensionável: tudo é desenhado em self.tela (1024x720)
        self.janela = Janela(self.save["janela"])
        self.tela = self.janela.tela
        self.clock = pygame.time.Clock()

        # As imagens só podem ser convertidas depois da janela existir
        assets.carregar()
        pygame.key.stop_text_input()

        self.jogador = Jogador(self.save)
        self.audio = Audio(self.save)

        self.cena = None
        self._proxima = None
        self._fase = None        # None, "saindo" ou "entrando"
        self._fade = 0.0
        self.rodando = True
        self.tempo_total = 0.0

        # Já tem ovo salvo? Vai direto para a casa.
        if self.jogador.nome:
            self.trocar(CenaCasa(self), fade=False)
        else:
            self.trocar(CenaNome(self, "inicial", self._depois_do_nome), fade=False)

    # --------------------------------------------------------
    # FLUXO INICIAL
    # --------------------------------------------------------

    def _depois_do_nome(self):
        self.trocar(CenaCriador(self, "inicial", self._depois_do_criador))

    def _depois_do_criador(self):
        self.trocar(CenaCasa(self))

    # --------------------------------------------------------
    # CENAS
    # --------------------------------------------------------

    def trocar(self, cena, fade=True):
        """Troca a cena ativa (com escurecimento, se fade=True)."""
        if self._fase == "saindo":
            # Já estava trocando: só atualiza o destino
            self._proxima = cena
            return

        if not fade or self.cena is None:
            self._ativar(cena)
        else:
            self._proxima = cena
            self._fase = "saindo"

    def _ativar(self, cena):
        if self.cena is not None:
            self.cena.sair()
        self.cena = cena
        # Evita que um clique "vaze" para a próxima cena
        pygame.event.clear((pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP))
        cena.entrar()

    def sair(self):
        self.rodando = False

    # --------------------------------------------------------
    # PET / ECONOMIA (usados pelas cenas e mini jogos)
    # --------------------------------------------------------

    def bonus_moedas(self):
        """Multiplicador de moedas: pet (unicórnio) x OVO FELIZ."""
        from core import pets
        bonus = pets.bonus_moedas(self.save["pet"])
        if self.necessidades.feliz():
            bonus *= 1.10
        return bonus

    def ao_terminar_minijogo(self, jogo, valor, venceu):
        """
        Chamado pela base dos mini jogos ao fim de cada partida.
        Devolve moedas extras (bônus VARIEDADE: 1ª partida do dia
        em cada jogo vale +5).
        """
        import datetime
        self.necessidades.pos_minijogo()
        self.necessidades.salvar()

        if jogo.ID not in self.save["jogados"]:
            self.save["jogados"].append(jogo.ID)

        diario = self.save["diario"]
        hoje = datetime.date.today().isoformat()
        if diario.get("variedade_dia") != hoje:
            diario["variedade_dia"] = hoje
            diario["variedade"] = []
        extra = 0
        if jogo.ID not in diario["variedade"]:
            diario["variedade"].append(jogo.ID)
            extra = 5

        # Desafio do dia do ROBERT
        from cenas.casa_extras import rotina
        rotina.verificar_desafio(self.save, jogo, valor, venceu)
        self.save.salvar()
        return extra

    def estado_sono(self):
        """A cena da casa informa se o ovo está dormindo (e bônus de sono)."""
        casa = getattr(self.cena, "casa", None) or self.cena
        info = getattr(casa, "info_sono", None)
        return info() if info else {}

    def desenhar_pet(self, tela, pos, feliz=False):
        """Desenha o pet ativo (se houver) com os pés em `pos`."""
        from core import pets
        pets.desenhar_parado(tela, self.save["pet"], pos, self.tempo_total, feliz)

    # --------------------------------------------------------
    # LOOP
    # --------------------------------------------------------

    def rodar(self):
        while self.rodando:
            # dt limitado: se a janela travar (arrastar), a física não explode
            dt = min(self.clock.tick(FPS) / 1000.0, 1 / 20)
            self.passo(dt)

        self.save["janela"] = list(self.janela.tamanho)
        self.necessidades.salvar()
        pygame.quit()

    def passo(self, dt):
        """Um frame: eventos -> lógica -> desenho."""
        self.tempo_total += dt
        trocou = False

        for e in pygame.event.get():
            e = self.janela.converter_evento(e)
            if e is None:
                continue
            if e.type == pygame.QUIT:
                self.sair()
            elif self._fase is None and not trocou:
                cena = self.cena
                cena.evento(e)
                # Se a cena mudou, o resto dos eventos deste frame
                # não pode "vazar" para a cena nova
                trocou = self.cena is not cena

        self._atualizar_transicao(dt)
        self.audio.atualizar(dt)
        self.necessidades.atualizar(dt, **self.estado_sono())
        self.cena.atualizar(dt)
        self.cena.desenhar(self.tela)

        if self._fade > 0:
            # Smoothstep: o escurecimento começa e termina macio
            ui.veu(self.tela, int(255 * ui.suavizar(self._fade)), (14, 10, 26))

        self.janela.apresentar()

    def _atualizar_transicao(self, dt):
        passo = dt / TEMPO_TRANSICAO

        if self._fase == "saindo":
            self._fade = min(1.0, self._fade + passo)
            if self._fade >= 1.0:
                self._ativar(self._proxima)
                self._proxima = None
                self._fase = "entrando"

        elif self._fase == "entrando":
            self._fade = max(0.0, self._fade - passo)
            if self._fade <= 0.0:
                self._fase = None


if __name__ == "__main__":
    # Garante que os imports funcionem mesmo rodando de outra pasta
    sys.path.insert(0, BASE_DIR)
    os.chdir(BASE_DIR)
    App().rodar()
    sys.exit()
