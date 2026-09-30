import math

import pygame

from settings import *
from core import ui
from core.cena import Cena, tecla_voltar, tecla_confirmar
from core.fundo_menu import FundoAnimado

# ============================================================
# MENU DE MINI JOGOS
# ============================================================
# Duas abas: SOLO e 2 JOGADORES. Os cards rolam na vertical
# (roda do mouse / setas) e a seleção sempre fica visível.
#   ← → ↑ ↓ / WASD  escolhe      ENTER / clique  joga
#   TAB / Q / E     troca de aba ESC             volta para a casa

COLUNAS = 4
CARD_L = 220
CARD_A = 204
ESPACO_X = 22
ESPACO_Y = 20
AREA = pygame.Rect(0, 146, LARGURA, 452)      # região onde os cards rolam

ABAS = [("SOLO", False), ("2 JOGADORES", True)]


class CenaMenuJogos(Cena):

    musica = "jogos"

    def __init__(self, app, casa):
        super().__init__(app)
        from jogos import JOGOS

        self.casa = casa
        self.todos = JOGOS
        self.aba = 0
        self.indices = [0, 0]           # seleção lembrada em cada aba
        self.tempo = 0.0
        self.rolagem = 0.0              # rolagem atual (suave)
        self.rolagem_alvo = 0.0
        self.fundo = FundoAnimado((40, 20, 80), (110, 50, 150), semente=9)
        self._ultimo_mouse = None
        self.miniaturas = {}

        self.botao_voltar = ui.Botao((16, 16, 150, 52), "< CASA", 14)
        self.botao_loja = ui.Botao((LARGURA - 166, 16, 150, 52), "LOJA", 14,
                                   cor=(150, 100, 20), cor_hover=(200, 140, 40))
        self.rects_abas = []
        for i in range(len(ABAS)):
            r = pygame.Rect(0, 0, 250, 44)
            r.midtop = (LARGURA // 2 - 135 + i * 270, 94)
            self.rects_abas.append(r)
        self.animacao = {}
        self._brilhos = {}
        self._status = None
        self.ingresso = None            # jogo bloqueado esperando confirmação
        self._veu_card = None

    # --------------------------------------------------------

    @property
    def jogos(self):
        multi = ABAS[self.aba][1]
        # Jogos híbridos (bot ou 2 jogadores) aparecem nas duas abas
        return [j for j in self.todos
                if bool(getattr(j, "MULTI", False)) == multi or getattr(j, "HIBRIDO", False)]

    @property
    def indice(self):
        return self.indices[self.aba]

    @indice.setter
    def indice(self, valor):
        self.indices[self.aba] = valor

    def entrar(self):
        super().entrar()
        # A chave das miniaturas já inclui aparência e cosméticos: só
        # esvazia se crescer demais (antes refazia as 32 a cada volta)
        if len(self.miniaturas) > 80:
            self.miniaturas.clear()
        self._status = None

    def _rect_card(self, i):
        """Retângulo do card i SEM a rolagem."""
        jogos = self.jogos
        linha, col = divmod(i, COLUNAS)
        na_linha = min(COLUNAS, len(jogos) - linha * COLUNAS)
        largura_linha = na_linha * CARD_L + (na_linha - 1) * ESPACO_X
        x0 = (LARGURA - largura_linha) // 2
        return pygame.Rect(x0 + col * (CARD_L + ESPACO_X),
                           AREA.y + 14 + linha * (CARD_A + ESPACO_Y), CARD_L, CARD_A)

    def _rolagem_maxima(self):
        linhas = math.ceil(len(self.jogos) / COLUNAS)
        # margem de cima (14) + cards + sombra/brilho embaixo (10)
        altura = linhas * (CARD_A + ESPACO_Y) - ESPACO_Y + 24
        return max(0, altura - AREA.h)

    def _mostrar_selecionado(self):
        """Ajusta a rolagem para o card selecionado ficar visível."""
        if not self.jogos:
            return
        r = self._rect_card(self.indice)
        topo = r.y - AREA.y - 14
        base = r.bottom - AREA.y + 14
        if topo < self.rolagem_alvo:
            self.rolagem_alvo = topo
        elif base > self.rolagem_alvo + AREA.h:
            self.rolagem_alvo = base - AREA.h
        self.rolagem_alvo = max(0, min(self._rolagem_maxima(), self.rolagem_alvo))

    def _miniatura(self, jogo):
        chave = (jogo.ID, self.jogador.aparencia(), self.jogador.chave_visual())
        sup = self.miniaturas.get(chave)
        if sup is None:
            sup = jogo.miniatura(self.jogador, (CARD_L - 16, 118))
            self.miniaturas[chave] = sup
        return sup

    def _jogar(self, i):
        from core import progresso
        self.indice = i
        jogo = self.jogos[i]
        if not progresso.liberado(self.app.save, jogo):
            self.ingresso = jogo
            self.som("erro", 0.5)
            return
        self.som("selecionar")
        self.app.trocar(jogo(self.app, self))

    def _evento_ingresso(self, e):
        from core import progresso
        jogo = self.ingresso
        preco = progresso.preco_ingresso(jogo.ID)
        comprar = (e.type == pygame.KEYDOWN and e.key in (pygame.K_RETURN, pygame.K_KP_ENTER)) or \
            (e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self._rect_comprar().collidepoint(e.pos))
        if comprar:
            if self.app.save.gastar(preco):
                progresso.liberar(self.app, jogo.ID)
                progresso.contar(self.app, "moedas_gastas", preco)
                self.som("vencer")
                self.app.toasts.adicionar("JOGO LIBERADO!", jogo.TITULO, "", None)
                self.ingresso = None
            else:
                self.som("erro")
            return
        if tecla_voltar(e) or (e.type == pygame.MOUSEBUTTONDOWN):
            self.som("voltar")
            self.ingresso = None

    def _rect_comprar(self):
        r = pygame.Rect(0, 0, 260, 50)
        r.center = (LARGURA // 2, ALTURA // 2 + 70)
        return r

    def _trocar_aba(self, aba):
        if aba == self.aba:
            return
        self.aba = aba % len(ABAS)
        self.rolagem = self.rolagem_alvo = 0.0
        self._mostrar_selecionado()
        self.rolagem = self.rolagem_alvo
        self.som("clique")

    def _mover(self, dx, dy):
        n = len(self.jogos)
        if n == 0:
            return
        if dx:
            self.indice = (self.indice + dx) % n
        elif dy:
            novo = self.indice + dy * COLUNAS
            if novo < 0:
                # Vai para a última linha, mesma coluna (ou o último)
                col = self.indice % COLUNAS
                ultima = (n - 1) // COLUNAS
                novo = min(n - 1, ultima * COLUNAS + col)
            elif novo >= n:
                novo = self.indice % COLUNAS if self.indice // COLUNAS == (n - 1) // COLUNAS \
                    else n - 1
            self.indice = novo
        self._mostrar_selecionado()
        self.som("clique", 0.5)

    # --------------------------------------------------------

    def evento(self, e):
        if self.ingresso is not None:
            self._evento_ingresso(e)
            return
        if tecla_voltar(e) or self.botao_voltar.evento(e):
            self.som("voltar")
            self.app.trocar(self.casa)
            return

        if self.botao_loja.evento(e):
            from cenas.loja import CenaLoja
            self.som("selecionar")
            self.app.trocar(CenaLoja(self.app, self))
            return

        if e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_LEFT, pygame.K_a):
                self._mover(-1, 0)
            elif e.key in (pygame.K_RIGHT, pygame.K_d):
                self._mover(1, 0)
            elif e.key in (pygame.K_UP, pygame.K_w):
                self._mover(0, -1)
            elif e.key in (pygame.K_DOWN, pygame.K_s):
                self._mover(0, 1)
            elif e.key in (pygame.K_TAB, pygame.K_q, pygame.K_e):
                self._trocar_aba(self.aba + (-1 if e.key == pygame.K_q else 1))
            elif tecla_confirmar(e) and self.jogos:
                self._jogar(self.indice)

        elif e.type == pygame.MOUSEWHEEL:
            self.rolagem_alvo = max(0, min(self._rolagem_maxima(),
                                           self.rolagem_alvo - e.y * 80))

        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for i, r in enumerate(self.rects_abas):
                if r.collidepoint(e.pos):
                    self._trocar_aba(i)
                    return
            if AREA.collidepoint(e.pos):
                for i in range(len(self.jogos)):
                    if self._rect_card(i).move(0, -int(self.rolagem)).collidepoint(e.pos):
                        self._jogar(i)
                        break

    def atualizar(self, dt):
        self.tempo += dt
        self.fundo.atualizar(dt)
        self.botao_voltar.atualizar(dt)
        self.botao_loja.atualizar(dt)
        # A rolagem nunca passa do fim da aba atual
        maximo = self._rolagem_maxima()
        self.rolagem_alvo = max(0.0, min(maximo, self.rolagem_alvo))
        self.indice = max(0, min(len(self.jogos) - 1, self.indice))
        self.rolagem += (self.rolagem_alvo - self.rolagem) * min(1.0, dt * 12)
        self.rolagem = max(0.0, min(maximo, self.rolagem))

        pos = pygame.mouse.get_pos()
        if pos != self._ultimo_mouse:
            self._ultimo_mouse = pos
            if AREA.collidepoint(pos):
                for i in range(len(self.jogos)):
                    r = self._rect_card(i).move(0, -int(self.rolagem))
                    if r.collidepoint(pos) and i != self.indice:
                        self.indice = i
                        self.som("clique", 0.3)

        for i, jogo in enumerate(self.jogos):
            alvo = 1.0 if i == self.indice else 0.0
            atual = self.animacao.get(jogo.ID, 0.0)
            self.animacao[jogo.ID] = atual + (alvo - atual) * min(1.0, dt * 12)

    # --------------------------------------------------------

    def desenhar(self, tela):
        self.fundo.desenhar(tela)

        y = 22 + math.sin(self.tempo * 2) * 3
        ui.desenhar_texto(tela, "MINI JOGOS", (LARGURA // 2, y), 36, AMARELO, "midtop")
        self.botao_voltar.desenhar(tela)
        self.botao_loja.desenhar(tela)
        ui.desenhar_moedas(tela, self.app.save["moedas"], (LARGURA - 16, 76), "topright")

        # Abas
        for i, (nome, multi) in enumerate(ABAS):
            r = self.rects_abas[i]
            ativa = i == self.aba
            qtd = sum(1 for j in self.todos
                      if bool(getattr(j, "MULTI", False)) == multi or getattr(j, "HIBRIDO", False))
            pygame.draw.rect(tela, (90, 60, 150) if ativa else (40, 30, 70), r, border_radius=12)
            pygame.draw.rect(tela, AMARELO if ativa else (140, 120, 180), r, 3, border_radius=12)
            ui.desenhar_texto(tela, f"{nome} ({qtd})", r.center, 14,
                              AMARELO if ativa else BRANCO, "center")

        # Cards (recortados na área de rolagem)
        tela.set_clip(AREA)
        desloc = int(self.rolagem)
        for i, jogo in enumerate(self.jogos):
            r = self._rect_card(i).move(0, -desloc)
            if r.bottom < AREA.top - 20 or r.top > AREA.bottom + 20:
                continue
            self._desenhar_card(tela, r, jogo)
        tela.set_clip(None)

        # Barra de rolagem
        maximo = self._rolagem_maxima()
        if maximo > 0:
            trilho = pygame.Rect(LARGURA - 18, AREA.y + 8, 8, AREA.h - 16)
            pygame.draw.rect(tela, (40, 30, 70), trilho, border_radius=4)
            prop = AREA.h / (AREA.h + maximo)
            alt = max(30, int(trilho.h * prop))
            y = trilho.y + int((trilho.h - alt) * (self.rolagem / maximo))
            pygame.draw.rect(tela, (200, 180, 255), (trilho.x, y, 8, alt), border_radius=4)

        # Descrição do jogo selecionado
        jogos = self.jogos
        if jogos:
            jogo = jogos[min(self.indice, len(jogos) - 1)]
            caixa = pygame.Rect(40, ALTURA - 118, LARGURA - 80, 104)
            ui.painel(tela, caixa, (24, 20, 44), jogo.COR, 16, 4)
            ui.desenhar_texto(tela, jogo.TITULO, (caixa.x + 20, caixa.y + 14), 16,
                              AMARELO, "topleft")
            linhas = ui.quebrar_linhas(jogo.DESCRICAO, 12, caixa.w - 40)[:2]
            for j, linha in enumerate(linhas):
                ui.desenhar_texto(tela, linha, (caixa.x + 20, caixa.y + 42 + j * 20), 12,
                                  BRANCO, "topleft")
            dica = "TAB troca de aba  •  ENTER joga  •  ESC volta"
            ui.desenhar_texto(tela, dica, (caixa.centerx, caixa.bottom - 12), 10,
                              (170, 160, 210), "midbottom")

        if self.ingresso is not None:
            self._desenhar_ingresso(tela)

    def _desenhar_ingresso(self, tela):
        from core import progresso
        jogo = self.ingresso
        ui.veu(tela, 170)
        caixa = pygame.Rect(0, 0, 560, 300)
        caixa.center = (LARGURA // 2, ALTURA // 2)
        ui.painel(tela, caixa, (40, 30, 70), jogo.COR, 20, 5)
        ui.desenhar_texto(tela, jogo.TITULO, (caixa.centerx, caixa.y + 24), 18, AMARELO, "midtop")
        nivel = progresso.nivel_para(jogo.ID)
        ui.desenhar_texto(tela, f"LIBERA NO NÍVEL {nivel} (VOCÊ ESTÁ NO {self.app.save['nivel']})",
                          (caixa.centerx, caixa.y + 70), 10, BRANCO, "midtop")
        ui.desenhar_texto(tela, "OU COMPRE O INGRESSO AGORA:", (caixa.centerx, caixa.y + 100), 10,
                          (200, 190, 240), "midtop")
        r = self._rect_comprar()
        preco = progresso.preco_ingresso(jogo.ID)
        pode = self.app.save["moedas"] >= preco
        pygame.draw.rect(tela, (60, 150, 80) if pode else (90, 80, 90), r, border_radius=14)
        pygame.draw.rect(tela, BRANCO, r, 3, border_radius=14)
        ui.moeda(tela, (r.x + 40, r.centery), 12)
        ui.desenhar_texto(tela, f"{preco}  LIBERAR", (r.x + 62, r.centery), 14, BRANCO, "midleft")
        ui.desenhar_texto(tela, "ENTER compra  •  ESC cancela", (caixa.centerx, caixa.bottom - 20), 10,
                          (170, 160, 210), "midbottom")

    def _desenhar_card(self, tela, rect, jogo):
        anim = self.animacao.get(jogo.ID, 0.0)
        rect = rect.move(0, -int(6 * anim))

        if anim > 0.05:
            degrau = max(1, int(anim * 10))
            brilho = self._brilhos.get(degrau)
            if brilho is None:
                brilho = pygame.Surface((rect.w + 20, rect.h + 20), pygame.SRCALPHA)
                pygame.draw.rect(brilho, (*AMARELO, 9 * degrau), brilho.get_rect(),
                                 border_radius=22)
                self._brilhos[degrau] = brilho
            tela.blit(brilho, (rect.x - 10, rect.y - 10))

        pygame.draw.rect(tela, (0, 0, 0), rect.move(0, 6), border_radius=16)
        pygame.draw.rect(tela, jogo.COR, rect, border_radius=16)

        mini = self._miniatura(jogo)
        tela.blit(mini, (rect.x + 8, rect.y + 8))
        pygame.draw.rect(tela, (20, 20, 30), (rect.x + 8, rect.y + 8, *mini.get_size()), 2,
                         border_radius=4)

        ui.desenhar_texto(tela, jogo.TITULO_CURTO or jogo.TITULO, (rect.centerx, rect.y + 138),
                          14, BRANCO, "midtop")

        rec = self._texto_recorde(jogo)
        ui.desenhar_texto(tela, rec, (rect.centerx, rect.y + 168), 10,
                          AMARELO if "★" in rec else (220, 220, 240), "midtop")

        borda = ui.misturar(BRANCO, AMARELO, anim)
        pygame.draw.rect(tela, borda, rect, 4, border_radius=16)
        from core import progresso
        if not progresso.liberado(self.app.save, jogo):
            self._desenhar_cadeado(tela, rect, jogo)
            return
        self._desenhar_selos(tela, rect, jogo)

    def _desenhar_cadeado(self, tela, rect, jogo):
        from core import progresso
        if self._veu_card is None:
            self._veu_card = pygame.Surface((CARD_L, CARD_A), pygame.SRCALPHA)
            pygame.draw.rect(self._veu_card, (10, 8, 20, 185), self._veu_card.get_rect(), border_radius=16)
        tela.blit(self._veu_card, rect)
        c = (rect.centerx, rect.y + 64)
        pygame.draw.rect(tela, (200, 200, 215), (c[0] - 16, c[1] - 30, 32, 34), 6, border_radius=14)
        corpo = pygame.Rect(0, 0, 50, 38)
        corpo.midtop = (c[0], c[1] - 6)
        pygame.draw.rect(tela, (255, 200, 60), corpo, border_radius=6)
        pygame.draw.rect(tela, (150, 100, 20), corpo, 3, border_radius=6)
        pygame.draw.circle(tela, (120, 80, 10), (c[0], corpo.y + 16), 5)
        ui.desenhar_texto(tela, f"NÍVEL {progresso.nivel_para(jogo.ID)}", (rect.centerx, rect.y + 138), 14,
                          AMARELO, "midtop")
        ui.desenhar_texto(tela, f"OU {progresso.preco_ingresso(jogo.ID)} OVOEDAS", (rect.centerx, rect.y + 168),
                          10, (220, 220, 240), "midtop")

    def _status_jogos(self):
        """(medalhas, jogos já jogados hoje, jogo do desafio) — calculado 1x por visita."""
        if self._status is None:
            import datetime
            from jogos import trofeus
            from cenas.casa_extras import rotina
            save = self.app.save
            medalhas = {j.ID: trofeus.nivel(save, j)[0] for j in self.todos}
            diario = save["diario"]
            hoje = datetime.date.today().isoformat()
            jogados_hoje = set(diario.get("variedade", [])) if diario.get("variedade_dia") == hoje \
                else set()
            d = rotina.desafio_do_dia(save)
            desafio = d["jogo"] if not d.get("feito") else None
            self._status = (medalhas, jogados_hoje, desafio)
        return self._status

    def _desenhar_selos(self, tela, rect, jogo):
        medalhas, jogados_hoje, desafio = self._status_jogos()
        # Medalha conquistada (canto de cima, à direita)
        medalha = medalhas.get(jogo.ID)
        if medalha:
            cor = {"bronze": (205, 127, 50), "prata": (200, 205, 215), "ouro": (255, 214, 64)}[medalha]
            c = (rect.right - 20, rect.y + 20)
            pygame.draw.circle(tela, ui.escurecer(cor, 80), (c[0], c[1] + 2), 14)
            pygame.draw.circle(tela, cor, c, 14)
            ui.estrela(tela, c, 9, ui.clarear(cor, 70))
        # +5 da 1ª partida do dia (canto de cima, à esquerda)
        if jogo.ID not in jogados_hoje:
            r = pygame.Rect(rect.x + 2, rect.y + 2, 44, 24)
            pygame.draw.rect(tela, (40, 140, 60), r, border_radius=8)
            pygame.draw.rect(tela, (170, 255, 170), r, 2, border_radius=8)
            ui.desenhar_texto(tela, "+5", r.center, 10, BRANCO, "center")
        # Jogo do desafio do ROBERT
        if jogo.ID == desafio:
            y = rect.y + 104 + math.sin(self.tempo * 4) * 3
            r = pygame.Rect(0, 0, 118, 22)
            r.center = (rect.centerx, int(y))
            pygame.draw.rect(tela, (230, 120, 30), r, border_radius=8)
            pygame.draw.rect(tela, AMARELO, r, 2, border_radius=8)
            ui.desenhar_texto(tela, "! DESAFIO", r.center, 8, BRANCO, "center")

    def _texto_recorde(self, jogo):
        save = self.app.save
        if getattr(jogo, "MULTI", False):
            chaves = [f"{jogo.ID}_{i}_vitorias" for i in range(len(jogo.OPCOES))] \
                if jogo.OPCOES else [f"{jogo.ID}_vitorias"]
            v1 = v2 = 0
            for c in chaves:
                v = save["recordes"].get(c)
                if isinstance(v, list) and len(v) == 2:
                    v1 += v[0]
                    v2 += v[1]
            return f"★ J1 {v1} × {v2} J2" if v1 or v2 else "NOVO!"

        if jogo.OPCOES:
            # Mostra o recorde da dificuldade mais alta já jogada
            for i in reversed(range(len(jogo.OPCOES))):
                valor = save.recorde(f"{jogo.ID}_{i}")
                if valor is not None:
                    return f"★ {jogo.OPCOES[i]}: {jogo.formatar(valor)}"
            return "NOVO!"

        valor = save.recorde(jogo.ID)
        if valor is None:
            return "NOVO!"
        return f"★ RECORDE: {jogo.formatar(valor)}"
