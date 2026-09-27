import math

import pygame

from settings import *
from core import progresso, ui
from core.cena import Cena, tecla_voltar

# ============================================================
# CONQUISTAS / COLEÇÕES / ESTATÍSTICAS (pela pausa da casa)
# ============================================================
# Cabeçalho com nível, XP e idade do ovo; três abas:
#   CONQUISTAS   -> grade (rola com a roda do mouse / setas)
#   COLEÇÕES     -> borboletas, peixes da pescaria, receitas
#   ESTATÍSTICAS -> números do ovo + coração dos pets
# Q / E ou TAB trocam de aba.

ABAS = ["CONQUISTAS", "COLEÇÕES", "ESTATÍSTICAS"]
AREA = pygame.Rect(40, 156, LARGURA - 80, 480)
LINHA = 38

ESTATISTICAS = [
    ("partidas", "PARTIDAS JOGADAS"), ("vitorias", "VITÓRIAS"), ("recordes", "RECORDES BATIDOS"),
    ("ouros", "MEDALHAS DE OURO"), ("moedas_jogos", "OVOEDAS GANHAS EM JOGOS"),
    ("moedas_gastas", "OVOEDAS GASTAS"), ("compras", "COMPRAS"), ("comidas", "REFEIÇÕES"),
    ("banhos", "BANHOS"), ("carinhos", "CARINHOS"), ("pocoes", "POÇÕES BEBIDAS"),
    ("missoes", "MISSÕES CUMPRIDAS"), ("desafios", "DESAFIOS DO ROBERT"), ("caixas", "CAIXAS SURPRESA"),
    ("streak", "MAIOR SEQUÊNCIA DO BAÚ"), ("dias_feliz", "DIAS FELIZES SEGUIDOS"), ("fotos", "FOTOS"),
]


class CenaConquistas(Cena):

    def __init__(self, app, casa, pausa):
        super().__init__(app)
        self.casa = casa
        self.pausa = pausa
        self.tempo = 0.0
        self.aba = 0
        self.rolagem = 0.0
        self.rolagem_alvo = 0.0
        self.botao = ui.Botao((0, 0, 200, 44), "VOLTAR", 14)
        self.botao.rect.midbottom = (LARGURA // 2, ALTURA - 10)
        self.rects_abas = []
        for i in range(len(ABAS)):
            r = pygame.Rect(0, 0, 230, 34)
            r.midtop = (LARGURA // 2 + (i - 1) * 244, 112)
            self.rects_abas.append(r)

    def _voltar(self):
        self.som("voltar")
        self.app.trocar(self.pausa, fade=False)

    def _trocar_aba(self, aba):
        self.aba = aba % len(ABAS)
        self.rolagem = self.rolagem_alvo = 0.0
        self.som("clique")

    def _altura_conteudo(self):
        if self.aba == 0:
            return math.ceil(len(progresso.CONQUISTAS) / 2) * LINHA
        if self.aba == 1:
            total = 0
            for nome, _ in progresso.COLECOES:
                n = len(progresso.catalogo_colecao(nome))
                total += 40 + math.ceil(max(1, n) / 4) * 34 + 16
            return total
        return 460

    def evento(self, e):
        if tecla_voltar(e) or self.botao.evento(e):
            self._voltar()
            return
        if e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_TAB, pygame.K_e, pygame.K_RIGHT, pygame.K_d):
                self._trocar_aba(self.aba + 1)
            elif e.key in (pygame.K_q, pygame.K_LEFT, pygame.K_a):
                self._trocar_aba(self.aba - 1)
            elif e.key in (pygame.K_DOWN, pygame.K_s):
                self.rolagem_alvo += 80
            elif e.key in (pygame.K_UP, pygame.K_w):
                self.rolagem_alvo -= 80
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._voltar()
        elif e.type == pygame.MOUSEWHEEL:
            self.rolagem_alvo -= e.y * 60
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for i, r in enumerate(self.rects_abas):
                if r.collidepoint(e.pos):
                    self._trocar_aba(i)

    def atualizar(self, dt):
        self.tempo += dt
        self.casa.atualizar(dt)
        self.botao.selecionado = True
        self.botao.atualizar(dt)
        maximo = max(0, self._altura_conteudo() - AREA.h)
        self.rolagem_alvo = max(0.0, min(float(maximo), self.rolagem_alvo))
        self.rolagem += (self.rolagem_alvo - self.rolagem) * min(1.0, dt * 12)

    # --------------------------------------------------------

    def desenhar(self, tela):
        self.casa.desenhar(tela)
        ui.veu(tela, 200)
        caixa = pygame.Rect(0, 0, 980, 650)
        caixa.midtop = (LARGURA // 2, 8)
        ui.painel(tela, caixa, (30, 34, 60), AMARELO, 20, 4)
        self._desenhar_cabecalho(tela, caixa)

        for i, (nome, r) in enumerate(zip(ABAS, self.rects_abas)):
            ativa = i == self.aba
            pygame.draw.rect(tela, (90, 60, 150) if ativa else (40, 36, 70), r, border_radius=10)
            pygame.draw.rect(tela, AMARELO if ativa else (120, 110, 170), r, 2, border_radius=10)
            ui.desenhar_texto(tela, nome, r.center, 12, AMARELO if ativa else BRANCO, "center")

        tela.set_clip(AREA)
        y0 = AREA.y - int(self.rolagem)
        [self._aba_conquistas, self._aba_colecoes, self._aba_estatisticas][self.aba](tela, y0)
        tela.set_clip(None)
        self.botao.desenhar(tela)

    def _desenhar_cabecalho(self, tela, caixa):
        save = self.app.save
        feitas = sum(1 for c in progresso.CONQUISTAS if c[0] in save["conquistas"])
        nivel, xp, meta = progresso.progresso(save)
        linha = pygame.Rect(caixa.x + 30, caixa.y + 16, caixa.w - 60, 80)
        self.jogador.desenhar(tela, (linha.x + 30, linha.y + 36), 52)
        ui.desenhar_texto(tela, f"{self.jogador.nome}  •  NÍVEL {nivel}", (linha.x + 70, linha.y + 10),
                          18, BRANCO, "topleft")
        barra = pygame.Rect(linha.x + 70, linha.y + 44, 420, 12)
        pygame.draw.rect(tela, (60, 60, 90), barra, border_radius=6)
        pygame.draw.rect(tela, (120, 220, 255), (barra.x, barra.y, max(4, int(barra.w * xp / meta)),
                                                 barra.h), border_radius=6)
        texto_xp = "NÍVEL MÁXIMO!" if nivel >= progresso.NIVEL_MAX else f"{xp}/{meta} XP"
        ui.desenhar_texto(tela, texto_xp, (barra.right + 12, barra.centery), 10, (180, 220, 255), "midleft")
        ui.desenhar_texto(tela, f"DIA {progresso.idade_dias(save)} DE VIDA", (linha.right, linha.y + 10),
                          10, (230, 220, 170), "topright")
        ui.desenhar_texto(tela, f"CONQUISTAS {feitas}/{len(progresso.CONQUISTAS)}", (linha.right, linha.y + 30),
                          10, AMARELO, "topright")

    # --------------------------------------------------------

    def _aba_conquistas(self, tela, y0):
        save = self.app.save
        feitas = set(save["conquistas"])
        st = save["stats"]
        col_w = (AREA.w - 16) // 2
        for i, (cid, nome, desc, stat, meta, premio) in enumerate(progresso.CONQUISTAS):
            col, lin = i % 2, i // 2
            r = pygame.Rect(AREA.x + col * (col_w + 16), y0 + lin * LINHA, col_w, LINHA - 4)
            if r.bottom < AREA.top or r.top > AREA.bottom:
                continue
            feita = cid in feitas
            pygame.draw.rect(tela, (70, 60, 20) if feita else (38, 42, 70), r, border_radius=8)
            pygame.draw.rect(tela, AMARELO if feita else (80, 86, 120), r, 2, border_radius=8)
            c = (r.x + 18, r.centery)
            if feita:
                pygame.draw.circle(tela, AMARELO, c, 11)
                ui.estrela(tela, c, 8, (255, 250, 220), math.sin(self.tempo * 2 + i) * 0.3)
            else:
                pygame.draw.circle(tela, (70, 76, 110), c, 11)
                pygame.draw.circle(tela, (110, 116, 150), c, 11, 2)
            ui.desenhar_texto(tela, nome, (r.x + 36, r.y + 5), 10, AMARELO if feita else BRANCO, "topleft")
            ui.desenhar_texto(tela, desc, (r.x + 36, r.y + 20), 8,
                              (230, 220, 170) if feita else (170, 175, 200), "topleft")
            if feita:
                ui.check(tela, (r.right - 16, r.centery), 14)
            else:
                valor = st.get(stat, 0)
                valor = min(meta, valor) if isinstance(valor, (int, float)) else 0
                ui.desenhar_texto(tela, f"{int(valor)}/{meta}", (r.right - 10, r.y + 6), 8, (180, 190, 220),
                                  "topright")
                ui.moeda(tela, (r.right - 40, r.y + 25), 5)
                ui.desenhar_texto(tela, str(premio), (r.right - 10, r.y + 25), 8, AMARELO, "midright")

    def _aba_colecoes(self, tela, y0):
        save = self.app.save
        y = y0
        for nome, rotulo in progresso.COLECOES:
            catalogo = progresso.catalogo_colecao(nome)
            tem = set(progresso.itens_colecao(save, nome))
            completa = catalogo and all(cid in tem for cid, _ in catalogo)
            cor = AMARELO if completa else BRANCO
            achados = sum(1 for cid, _ in catalogo if cid in tem)
            ui.desenhar_texto(tela, f"{rotulo}  {achados}/{len(catalogo)}", (AREA.x + 6, y + 8), 14, cor,
                              "topleft")
            if not completa and nome != "borboletas":
                ui.desenhar_texto(tela, f"COMPLETE E GANHE {progresso.PREMIO_COLECAO} OVOEDAS",
                                  (AREA.right - 6, y + 10), 8, (230, 220, 170), "topright")
            y += 40
            larg = (AREA.w - 30) // 4
            for i, (cid, rot) in enumerate(catalogo):
                r = pygame.Rect(AREA.x + (i % 4) * (larg + 10), y + (i // 4) * 34, larg, 28)
                ok = cid in tem
                pygame.draw.rect(tela, (60, 90, 60) if ok else (40, 42, 64), r, border_radius=8)
                pygame.draw.rect(tela, (140, 255, 150) if ok else (80, 84, 110), r, 2, border_radius=8)
                texto = str(rot).upper() if ok else "???"
                ui.desenhar_texto(tela, texto, r.center, 8, BRANCO if ok else (130, 130, 160), "center")
            y += math.ceil(max(1, len(catalogo)) / 4) * 34 + 16

    def _aba_estatisticas(self, tela, y0):
        save = self.app.save
        st = save["stats"]
        col_w = (AREA.w - 20) // 2
        for i, (chave, rotulo) in enumerate(ESTATISTICAS):
            col, lin = i % 2, i // 2
            r = pygame.Rect(AREA.x + col * (col_w + 20), y0 + lin * 30, col_w, 26)
            pygame.draw.rect(tela, (38, 42, 70), r, border_radius=6)
            ui.desenhar_texto(tela, rotulo, (r.x + 10, r.centery), 8, (200, 205, 230), "midleft")
            valor = st.get(chave, 0)
            ui.desenhar_texto(tela, str(valor if isinstance(valor, int) else 0), (r.right - 10, r.centery), 10,
                              AMARELO, "midright")
        y = y0 + math.ceil(len(ESTATISTICAS) / 2) * 30 + 16
        ui.desenhar_texto(tela, f"OVOEDAS GANHAS NA VIDA: {save['moedas_total']}", (AREA.x + 10, y), 10, AMARELO,
                          "topleft")

        # Coração dos pets
        af = st.get("afeicao", {})
        if isinstance(af, dict) and af:
            y += 30
            ui.desenhar_texto(tela, "CORAÇÃO DOS PETS (carinho e vitórias enchem)", (AREA.x + 10, y), 10,
                              (255, 170, 200), "topleft")
            y += 22
            for i, (pet, valor) in enumerate(sorted(af.items(), key=lambda x: -x[1])[:8]):
                col, lin = i % 2, i // 2
                r = pygame.Rect(AREA.x + col * (col_w + 20), y + lin * 28, col_w, 24)
                ui.desenhar_texto(tela, pet.upper(), (r.x + 10, r.centery), 8, BRANCO, "midleft")
                barra = pygame.Rect(r.x + 150, r.centery - 5, r.w - 200, 10)
                pygame.draw.rect(tela, (60, 50, 70), barra, border_radius=5)
                pygame.draw.rect(tela, (255, 110, 150), (barra.x, barra.y, max(3, int(barra.w * valor / 100)),
                                                         barra.h), border_radius=5)
                ui.coracao(tela, (barra.right + 16, r.centery), 12)
