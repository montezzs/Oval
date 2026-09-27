import pygame

from settings import *

# ============================================================
# JANELA REDIMENSIONÁVEL
# ============================================================
# O jogo inteiro desenha numa tela "lógica" fixa de 1024x720.
# A cada frame essa tela é esticada (mantendo a proporção, com
# faixas pretas nas sobras) para o tamanho real da janela.
#
# O mouse é convertido de volta para as coordenadas lógicas,
# então NENHUMA cena precisa saber o tamanho real da janela:
#   - eventos de mouse têm o `pos` corrigido
#   - pygame.mouse.get_pos() devolve a posição lógica

TAMANHO_MIN = (LARGURA, ALTURA)
TAMANHO_MAX = (1920, 1080)

# Tamanhos oferecidos no menu de pausa
TAMANHOS = [(1024, 720), (1280, 900), (1536, 1080), (1920, 1080)]

_get_pos_original = pygame.mouse.get_pos


class Janela:

    def __init__(self, tamanho=None):
        self.tela = pygame.Surface((LARGURA, ALTURA))
        self.tamanho = self._limitar(tamanho or TAMANHO_MIN)
        self.superficie = pygame.display.set_mode(self.tamanho, pygame.RESIZABLE)
        self.destino = pygame.Rect(0, 0, LARGURA, ALTURA)
        self._calcular()

        # A partir daqui, qualquer módulo que chamar
        # pygame.mouse.get_pos() recebe a posição lógica.
        pygame.mouse.get_pos = self.mouse_logico

    # --------------------------------------------------------

    @staticmethod
    def _limitar(tamanho):
        w = max(TAMANHO_MIN[0], min(TAMANHO_MAX[0], int(tamanho[0])))
        h = max(TAMANHO_MIN[1], min(TAMANHO_MAX[1], int(tamanho[1])))
        return (w, h)

    def _calcular(self):
        """Onde a tela lógica fica dentro da janela (letterbox)."""
        w, h = self.superficie.get_size()
        escala = min(w / LARGURA, h / ALTURA)
        dw, dh = round(LARGURA * escala), round(ALTURA * escala)
        self.destino = pygame.Rect((w - dw) // 2, (h - dh) // 2, dw, dh)
        self.escala = escala
        self.superficie.fill((0, 0, 0))

    def redimensionar(self, tamanho):
        """Muda o tamanho da janela respeitando os limites."""
        novo = self._limitar(tamanho)
        self.tamanho = novo

        if novo != self.superficie.get_size():
            try:
                janela = pygame._sdl2.video.Window.from_display_module()
                janela.restore()
            except (AttributeError, pygame.error):
                pass
            self.superficie = pygame.display.set_mode(novo, pygame.RESIZABLE)

        self._calcular()

    # --------------------------------------------------------
    # MOUSE
    # --------------------------------------------------------

    def para_logico(self, pos):
        x = (pos[0] - self.destino.x) / self.escala
        y = (pos[1] - self.destino.y) / self.escala
        x = max(0, min(LARGURA - 1, int(x)))
        y = max(0, min(ALTURA - 1, int(y)))
        return (x, y)

    def mouse_logico(self):
        return self.para_logico(_get_pos_original())

    def converter_evento(self, e):
        """
        Ajusta eventos antes de chegarem nas cenas.
        Devolve None se o evento foi consumido aqui.
        """
        if e.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            e.pos = self.para_logico(e.pos)
            if e.type == pygame.MOUSEMOTION:
                e.rel = (int(e.rel[0] / self.escala), int(e.rel[1] / self.escala))
            return e

        if e.type == pygame.VIDEORESIZE:
            self.superficie = pygame.display.get_surface()
            tamanho = (e.w, e.h)
            if self._limitar(tamanho) != tamanho:
                self.redimensionar(tamanho)
            else:
                self.tamanho = tamanho
                self._calcular()
            return None

        return e

    # --------------------------------------------------------

    def apresentar(self):
        """Estica a tela lógica para a janela e mostra."""
        if self.destino.size == (LARGURA, ALTURA):
            self.superficie.blit(self.tela, self.destino)
        else:
            alvo = self.superficie.subsurface(self.destino)
            pygame.transform.smoothscale(self.tela, self.destino.size, alvo)
        pygame.display.flip()
