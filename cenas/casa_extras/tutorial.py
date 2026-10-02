import math

import pygame

from settings import *
from core import ui

# ============================================================
# TUTORIAL GUIADO (primeiros minutos do 1º ovo)
# ============================================================
# O próprio ovo pede as coisas num balão e uma seta pulsante
# aponta o que clicar. Cada passo cumprido paga +10 OVOEDAS.
# O passo fica em config["tutorial"] (0..N; TUTORIAL_FIM = acabou),
# então só acontece uma vez por jogador (não por ovo).
#
# Os passos são detectados pelas estatísticas do save (comidas,
# banhos, partidas, compras) e pelo cômodo atual: nada precisa
# avisar o tutorial.

TUTORIAL_FIM = 99
PREMIO_PASSO = 10

PASSOS = [
    # (texto do ovo, alvo, como saber que terminou)
    ("Estou com FOME! Clique em COMIDA e arraste algo até a minha boca.", "comida", "comidas"),
    ("Tô sujinho... Clique no SABÃO, esfregue e depois clique no CHUVEIRO.", "sabao", "banhos"),
    ("Vamos brincar? Vá para o cômodo BRINCAR (seta > ou tecla 3).", "seta_dir", "brincar"),
    ("Clique na bola (ou em JOGAR) e jogue uma partida!", "jogar", "partidas"),
    ("Ganhou OVOEDAS! Que tal comprar algo na LOJA?", "loja", "compras"),
]


class Tutorial:

    def __init__(self, ctx):
        self.ctx = ctx
        self.tempo = 0.0
        self.base = None           # estatísticas no começo do passo
        self.comemorar = 0.0
        self.botao_pular = pygame.Rect(0, 0, 150, 30)

    @property
    def config(self):
        return self.ctx.app.config

    @property
    def passo(self):
        p = self.config["tutorial"]
        return p if isinstance(p, int) else TUTORIAL_FIM

    @property
    def ativo(self):
        return 0 <= self.passo < len(PASSOS) and self.ctx.app.save.arquivo is not None

    def _stats(self):
        st = self.ctx.app.save["stats"]
        return {k: st.get(k, 0) for k in ("comidas", "banhos", "partidas", "compras")}

    def _avancar(self):
        self.config["tutorial"] = self.passo + 1
        if self.passo >= len(PASSOS):
            self.config["tutorial"] = TUTORIAL_FIM
        self.config.salvar()
        self.base = None
        self.comemorar = 1.2
        ctx = self.ctx
        ctx.ganhar_moedas(PREMIO_PASSO, (ctx.x, ctx.ovo_chao - 170))
        ctx.som("acerto")
        if not self.ativo:
            ctx.avisar("TUTORIAL COMPLETO! Agora a rua é sua!")

    def pular(self):
        self.config["tutorial"] = TUTORIAL_FIM
        self.config.salvar()
        self.ctx.som("voltar")

    # --------------------------------------------------------

    def clicar(self, pos):
        """True se o clique foi no botão PULAR."""
        if self.ativo and self.botao_pular.collidepoint(pos):
            self.pular()
            return True
        return False

    def atualizar(self, dt):
        self.tempo += dt
        self.comemorar = max(0.0, self.comemorar - dt)
        if not self.ativo:
            return
        if self.base is None:
            self.base = self._stats()
        _, _, meta = PASSOS[self.passo]
        if meta == "brincar":
            if self.ctx.comodo == "BRINCAR":
                self._avancar()
        elif self._stats()[meta] > self.base[meta]:
            self._avancar()

    # --------------------------------------------------------

    def _alvo(self):
        ctx = self.ctx
        alvo = PASSOS[self.passo][1]
        if alvo in ("comida", "sabao"):
            if ctx.comodo not in ("CASA", "SOL", "BRINCAR"):
                return None
            for nome, r in ctx._rects_ferramentas():
                if nome == alvo:
                    return r
            return ctx.seta_esq if ctx.comodo == "BRINCAR" else None
        if alvo == "seta_dir":
            return ctx.seta_dir if ctx.comodo != "BRINCAR" else None
        if alvo == "jogar":
            return ctx.botao_jogar.rect if ctx.comodo == "BRINCAR" else ctx.seta_dir
        if alvo == "loja":
            return ctx.botao_loja
        return None

    def desenhar(self, tela):
        if not self.ativo or self.ctx.slide > 0:
            return
        ctx = self.ctx
        texto = PASSOS[self.passo][0]

        # Balão do ovo
        linhas = ui.quebrar_linhas(texto, 10, 330)
        caixa = pygame.Rect(0, 0, 360, len(linhas) * 18 + 40)
        corpo = ctx.rect_corpo()
        caixa.midbottom = (corpo.centerx, corpo.y - 24)
        caixa.clamp_ip(pygame.Rect(90, 130, LARGURA - 180, ALTURA - 220))
        pygame.draw.rect(tela, (0, 0, 0), caixa.move(4, 5), border_radius=14)
        pygame.draw.rect(tela, BRANCO, caixa, border_radius=14)
        pygame.draw.rect(tela, (60, 60, 90), caixa, 3, border_radius=14)
        ponta = (max(caixa.x + 30, min(caixa.right - 30, corpo.centerx)), caixa.bottom)
        pygame.draw.polygon(tela, BRANCO, [(ponta[0] - 10, ponta[1] - 2), (ponta[0] + 10, ponta[1] - 2),
                                           (ponta[0], ponta[1] + 14)])
        ui.desenhar_texto(tela, f"TUTORIAL {self.passo + 1}/{len(PASSOS)}", (caixa.x + 14, caixa.y + 8),
                          8, (120, 120, 160), "topleft", sombra=False)
        for i, linha in enumerate(linhas):
            ui.desenhar_texto(tela, linha, (caixa.x + 14, caixa.y + 24 + i * 18), 10, (40, 40, 60),
                              "topleft", sombra=False)

        # Seta pulsante apontando o alvo
        alvo = self._alvo()
        if alvo is not None:
            pulo = abs(math.sin(self.tempo * 5)) * 12
            if alvo.y > ALTURA // 2:
                ponta = (alvo.centerx, alvo.y - 6 - pulo)
                corpo_seta = [(ponta[0], ponta[1]), (ponta[0] - 18, ponta[1] - 22), (ponta[0] - 7, ponta[1] - 22),
                              (ponta[0] - 7, ponta[1] - 44), (ponta[0] + 7, ponta[1] - 44),
                              (ponta[0] + 7, ponta[1] - 22), (ponta[0] + 18, ponta[1] - 22)]
            else:
                ponta = (alvo.centerx, alvo.bottom + 6 + pulo)
                corpo_seta = [(ponta[0], ponta[1]), (ponta[0] - 18, ponta[1] + 22), (ponta[0] - 7, ponta[1] + 22),
                              (ponta[0] - 7, ponta[1] + 44), (ponta[0] + 7, ponta[1] + 44),
                              (ponta[0] + 7, ponta[1] + 22), (ponta[0] + 18, ponta[1] + 22)]
            pygame.draw.polygon(tela, (40, 20, 0), [(x + 3, y + 3) for x, y in corpo_seta])
            pygame.draw.polygon(tela, AMARELO, corpo_seta)
            pygame.draw.polygon(tela, (160, 100, 0), corpo_seta, 2)
            anel = alvo.inflate(10 + pulo, 10 + pulo)
            pygame.draw.rect(tela, AMARELO, anel, 3, border_radius=16)

        # PULAR TUTORIAL
        self.botao_pular.bottomright = (LARGURA - 16, ALTURA - 96)
        hover = self.botao_pular.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(tela, (70, 80, 130) if hover else (30, 36, 60), self.botao_pular, border_radius=10)
        pygame.draw.rect(tela, BRANCO, self.botao_pular, 2, border_radius=10)
        ui.desenhar_texto(tela, "PULAR TUTORIAL", self.botao_pular.center, 8, BRANCO, "center")
