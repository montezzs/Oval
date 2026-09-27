import pygame

# ============================================================
# CENA
# ============================================================
# Cada tela do jogo (nome, criador, casa, menu de jogos, cada
# mini jogo...) é uma Cena. O App chama os métodos abaixo a
# cada frame, só da cena ativa.


class Cena:

    # Nome da música desta cena (None = mantém a atual)
    musica = None

    def __init__(self, app):
        self.app = app

    # Atalhos úteis
    @property
    def jogador(self):
        return self.app.jogador

    @property
    def audio(self):
        return self.app.audio

    def som(self, nome, volume=1.0):
        self.app.audio.som(nome, volume)

    # --------------------------------------------------------

    def entrar(self):
        """Chamado quando a cena vira a cena ativa."""
        if self.musica:
            self.app.audio.tocar(self.musica)

    def sair(self):
        """Chamado quando a cena deixa de ser a ativa."""
        pass

    def evento(self, e):
        pass

    def atualizar(self, dt):
        pass

    def desenhar(self, tela):
        pass


def tecla_confirmar(e):
    return e.type == pygame.KEYDOWN and e.key in (
        pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)


def tecla_voltar(e):
    return e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE
