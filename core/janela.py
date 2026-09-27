import os

import pygame

try:
    from pygame._sdl2 import video as _video
except ImportError:
    _video = None

from settings import *

# ============================================================
# JANELA REDIMENSIONÁVEL
# ============================================================
# O jogo inteiro desenha numa tela "lógica" fixa de 1024x720.
# A cada frame essa tela é esticada (mantendo a proporção, com
# faixas pretas nas sobras) para o tamanho real da janela.
#
# Modo principal: pygame.SCALED -> quem estica é a PLACA DE VÍDEO
# (~1 ms por frame em 1080p, contra ~10 ms esticando no processador).
# O SDL já converte o mouse para as coordenadas lógicas.
#
# Se o SCALED não funcionar (driver sem renderizador), cai no modo
# antigo: smoothscale no processador + conversão manual do mouse.
#
# Em qualquer modo, NENHUMA cena precisa saber o tamanho real da
# janela: eventos de mouse e pygame.mouse.get_pos() são lógicos.

TAMANHO_MIN = (LARGURA, ALTURA)
TAMANHO_MAX = (1920, 1080)

# Tamanhos oferecidos no menu de pausa
TAMANHOS = [(1024, 720), (1280, 900), (1536, 1080), (1920, 1080)]

_get_pos_original = pygame.mouse.get_pos

# Esticar com suavização (a fonte pixelada fica sem "degraus" tortos)
os.environ.setdefault("SDL_RENDER_SCALE_QUALITY", "linear")


def _janela_sdl():
    if _video is None:
        return None
    try:
        return _video.Window.from_display_module()
    except (AttributeError, pygame.error):
        return None


class Janela:

    def __init__(self, tamanho=None):
        self.tela = pygame.Surface((LARGURA, ALTURA))
        self.tamanho = self._limitar(tamanho or TAMANHO_MIN)
        self.destino = pygame.Rect(0, 0, LARGURA, ALTURA)
        self.escala = 1.0
        self.gpu = False

        # Sem janela de verdade (testes com o driver "dummy"), o SCALED não
        # tem renderizador e pode derrubar o processo: usa o modo antigo
        sem_video = os.environ.get("SDL_VIDEODRIVER", "").lower() in ("dummy", "offscreen")
        if not os.environ.get("OVAL_SEM_GPU") and not sem_video:
            try:
                self.superficie = pygame.display.set_mode((LARGURA, ALTURA),
                                                          pygame.SCALED | pygame.RESIZABLE)
                self.gpu = self.superficie.get_size() == (LARGURA, ALTURA) and _janela_sdl() is not None
            except pygame.error:
                self.gpu = False

        if self.gpu:
            win = _janela_sdl()
            try:
                win.minimum_size = TAMANHO_MIN
            except (AttributeError, pygame.error):
                pass
            self._aplicar_tamanho(self.tamanho, centralizar=True)
        else:
            self.superficie = pygame.display.set_mode(self.tamanho, pygame.RESIZABLE)
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

    def _aplicar_tamanho(self, tamanho, centralizar=False):
        """Modo GPU: muda o tamanho da janela do sistema."""
        win = _janela_sdl()
        if win is None:
            return
        try:
            win.restore()
        except pygame.error:
            pass
        win.size = tamanho
        if centralizar:
            try:
                win.position = _video.WINDOWPOS_CENTERED
            except (AttributeError, pygame.error):
                pass
        self.tamanho = tuple(win.size)

    def _calcular(self):
        """Modo antigo: onde a tela lógica fica dentro da janela (letterbox)."""
        w, h = self.superficie.get_size()
        escala = min(w / LARGURA, h / ALTURA)
        dw, dh = round(LARGURA * escala), round(ALTURA * escala)
        self.destino = pygame.Rect((w - dw) // 2, (h - dh) // 2, dw, dh)
        self.escala = escala
        self.superficie.fill((0, 0, 0))

    def redimensionar(self, tamanho):
        """Muda o tamanho da janela respeitando os limites."""
        novo = self._limitar(tamanho)

        if self.gpu:
            self._aplicar_tamanho(novo)
            return

        self.tamanho = novo
        if novo != self.superficie.get_size():
            win = _janela_sdl()
            if win is not None:
                try:
                    win.restore()
                except pygame.error:
                    pass
            self.superficie = pygame.display.set_mode(novo, pygame.RESIZABLE)
        self._calcular()

    # --------------------------------------------------------
    # MOUSE
    # --------------------------------------------------------

    def para_logico(self, pos):
        if self.gpu:
            x, y = pos
        else:
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
            if e.type == pygame.MOUSEMOTION and not self.gpu:
                e.rel = (int(e.rel[0] / self.escala), int(e.rel[1] / self.escala))
            return e

        if e.type == pygame.VIDEORESIZE:
            if self.gpu:
                win = _janela_sdl()
                if win is not None:
                    tamanho = tuple(win.size)
                    if self._limitar(tamanho) != tamanho:
                        self._aplicar_tamanho(self._limitar(tamanho))
                    else:
                        self.tamanho = tamanho
                return None

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
        if self.gpu:
            self.superficie.blit(self.tela, (0, 0))
        elif self.destino.size == (LARGURA, ALTURA):
            self.superficie.blit(self.tela, self.destino)
        else:
            alvo = self.superficie.subsurface(self.destino)
            pygame.transform.smoothscale(self.tela, self.destino.size, alvo)
        pygame.display.flip()
