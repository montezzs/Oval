import math
import random

import pygame

from settings import *
from core import assets, ui
from core.cena import tecla_voltar
from core.jogador import Jogador
from core.idioma import t
from jogos.base import MiniJogo

# ============================================================
# MINI JOGO MULTIPLAYER (2 JOGADORES NO MESMO TECLADO)
# ============================================================
#   JOGADOR 1: WASD (+ ESPAÇO / F / G ...)
#   JOGADOR 2: SETAS (+ ENTER / SHIFT DIREITO / CTRL DIREITO ...)
#
# O J1 é o ovo do save. O J2 tem uma aparência sorteada (salva
# nas preferências) ou usa o visual de um VIZINHO da rua (outro
# ovo do jogador, só leitura: nada é gravado no save dele). O
# botão "J2: ..." da tela de início alterna entre as opções.
#
# Os jogos multiplayer chamam self.terminar_multi(vencedor, linhas)
# com vencedor = 0 (J1), 1 (J2) ou None (empate).
#
# Ajudantes úteis:
#   self.nome(i)              -> nome do jogador i (0 ou 1)
#   self.aparencia(i)         -> tupla da aparência
#   self.cor(i)               -> cor do ovo
#   self.desenhar_ovo(tela, i, centro, altura, espelhar, angulo)
#   self.teclas(i)            -> dict com "cima", "baixo", "esq", "dir"
#                                (bool, lidas do teclado agora)
#   TECLAS_ACAO[i]            -> teclas de ação de cada jogador

# Teclas de movimento de cada jogador
TECLAS_MOVER = [
    {"cima": pygame.K_w, "baixo": pygame.K_s, "esq": pygame.K_a, "dir": pygame.K_d},
    {"cima": pygame.K_UP, "baixo": pygame.K_DOWN, "esq": pygame.K_LEFT, "dir": pygame.K_RIGHT},
]

# Teclas de ação (a primeira de cada lista é a "principal")
TECLAS_ACAO = [
    [pygame.K_SPACE, pygame.K_f, pygame.K_g, pygame.K_q, pygame.K_e],
    [pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_RSHIFT, pygame.K_RCTRL,
     pygame.K_PERIOD, pygame.K_SLASH, pygame.K_KP0],
]

CORES_JOGADOR = [(110, 230, 120), (255, 150, 150)]


def jogador_da_tecla(tecla):
    """Qual jogador (0/1) é dono desta tecla, ou None."""
    for i in (0, 1):
        if tecla in TECLAS_MOVER[i].values() or tecla in TECLAS_ACAO[i]:
            return i
    return None


class MiniJogoMulti(MiniJogo):

    MULTI = True
    CONTROLES_J1 = "WASD + ESPAÇO"
    CONTROLES_J2 = "SETAS + ENTER"
    MOEDAS_PARTIDA = 12         # moedas por partida (vão para o dono do save)
    MOEDAS_VITORIA_J1 = 8       # bônus se o J1 vencer
    TEMPO_MINIMO = 30.0

    def __init__(self, app, menu):
        self._aparencia_j2 = None
        self._vizinho = None            # Jogador (só leitura) do vizinho
        self._cor_trocada = False
        self._mexeu = [False, False]
        super().__init__(app, menu)
        self._carregar_vizinho()
        self._montar_menu_inicio()          # o botão do J2 mostra o vizinho

    # --------------------------------------------------------
    # JOGADORES
    # --------------------------------------------------------

    def _carregar_j2(self):
        salvo = self.app.config["j2"]
        j1 = self.jogador.aparencia()
        limites = (len(assets.OVOS), len(assets.CABELOS), len(assets.OLHOS), len(assets.BOCAS))

        if (isinstance(salvo, list) and len(salvo) == 4
                and all(isinstance(v, int) and 0 <= v < n for v, n in zip(salvo, limites))
                and salvo[0] != j1[0]):
            return tuple(salvo)

        # Padrão: derivado do J1, sempre com outra cor de ovo
        return ((j1[0] + 1) % limites[0], (j1[1] + 4) % limites[1],
                (j1[2] + 1) % limites[2], (j1[3] + 2) % limites[3])

    def _carregar_vizinho(self):
        """J2 com o visual de outro ovo da rua (config["j2_slot"])."""
        from core import perfis
        self._vizinho = None
        self._cor_trocada = False
        slot = self.app.config["j2_slot"]
        if not isinstance(slot, int) or slot < 0 or slot == self.app.slot:
            return
        save = perfis.ler_ovo(slot)
        if save is None:
            self.app.config["j2_slot"] = -1
            self.app.config.salvar()
            return
        viz = Jogador(save)
        if viz.ovo == self.jogador.ovo:
            # Mesma cor do J1: troca só durante a partida
            outra = next(i for i in range(len(assets.OVOS)) if i != self.jogador.ovo)
            viz.definir_aparencia(outra, viz.cabelo, viz.olho, viz.boca)
            self._cor_trocada = True
        self._vizinho = viz
        self._slot_vizinho = slot

    def _proximo_j2(self):
        """SORTEADO -> cada vizinho -> SORTEADO (sorteia de novo)."""
        from core import perfis
        vizinhos = [s for s in perfis.slots_ocupados() if s != self.app.slot]
        atual = self.app.config["j2_slot"]
        if atual in vizinhos:
            i = vizinhos.index(atual) + 1
            novo = vizinhos[i] if i < len(vizinhos) else -1
        else:
            novo = vizinhos[0] if vizinhos else -1
        self.app.config["j2_slot"] = novo
        self.app.config.salvar()
        if novo == -1:
            self.sortear_j2()
        self._carregar_vizinho()
        MiniJogo._fundos.clear()

    def rotulo_j2(self):
        if self._vizinho is not None:
            nome = self._vizinho.nome.strip()[:8].upper() or t("VIZINHO")
            return t("J2: {nome} (CASA {n})", nome=nome, n=self._slot_vizinho + 1)
        return t("J2: SORTEADO")

    def sortear_j2(self):
        j1 = self.jogador.aparencia()
        cores = [i for i in range(len(assets.OVOS)) if i != j1[0]]
        nova = (random.choice(cores), random.randrange(len(assets.CABELOS)),
                random.randrange(len(assets.OLHOS)), random.randrange(len(assets.BOCAS)))
        self._aparencia_j2 = nova
        self.app.config["j2"] = list(nova)
        self.app.config.salvar()
        MiniJogo._fundos.clear()

    def aparencia(self, i):
        if i == 0:
            return self.jogador.aparencia()
        if self._vizinho is not None:
            return self._vizinho.aparencia()
        if self._aparencia_j2 is None or self._aparencia_j2[0] == self.jogador.ovo:
            self._aparencia_j2 = self._carregar_j2()
        return self._aparencia_j2

    def nome(self, i):
        if i == 0:
            return (self.jogador.nome or t("JOGADOR 1")).strip() or t("JOGADOR 1")
        if self._vizinho is not None:
            return self._vizinho.nome.strip() or t("JOGADOR 2")
        return t("JOGADOR 2")

    def cor(self, i):
        return Jogador.cor_do_ovo(self.aparencia(i)[0])

    def desenhar_ovo(self, tela, i, centro, altura, espelhar=False, angulo=0.0, aparencia=None):
        dono = self._vizinho if (i == 1 and self._vizinho is not None) else self.jogador
        return dono.desenhar(tela, centro, altura, aparencia=aparencia or self.aparencia(i),
                             espelhar=espelhar, angulo=angulo)

    @staticmethod
    def teclas(i):
        apertadas = pygame.key.get_pressed()
        return {nome: apertadas[k] for nome, k in TECLAS_MOVER[i].items()}

    @staticmethod
    def acao_apertada(i):
        apertadas = pygame.key.get_pressed()
        return any(apertadas[k] for k in TECLAS_ACAO[i])

    # --------------------------------------------------------
    # RESULTADO
    # --------------------------------------------------------

    def chave_recorde(self, opcao=None):
        opcao = self.opcao if opcao is None else opcao
        return f"{self.ID}_{opcao}" if self.OPCOES else self.ID

    def vitorias(self):
        v = self.app.save["recordes"].get(self.chave_recorde() + "_vitorias")
        if isinstance(v, list) and len(v) == 2:
            return v
        return [0, 0]

    def calcular_moedas(self, valor, venceu):
        return self.MOEDAS_PARTIDA + (self.MOEDAS_VITORIA_J1 if venceu else 0)

    def comecar(self):
        self._mexeu = [False, False]
        super().comecar()

    def partida_valida(self):
        # Só paga se os DOIS jogadores apertaram alguma tecla (anti-farm)
        return all(self._mexeu)

    def terminar_multi(self, vencedor, linhas=None):
        """vencedor: 0 (J1), 1 (J2) ou None (empate)."""
        if self.estado == "fim":
            return

        placar = self.vitorias()
        if vencedor in (0, 1):
            placar[vencedor] += 1
            self.app.save["recordes"][self.chave_recorde() + "_vitorias"] = placar
            self.app.save.salvar()

        titulo = t("EMPATE!") if vencedor is None else t("{nome} VENCEU!", nome=self.nome(vencedor))
        self.vencedor = vencedor
        linhas = list(linhas or [])
        linhas.append(t("VITÓRIAS  J1 {a} × {b} J2", a=placar[0], b=placar[1]))
        if self._cor_trocada:
            linhas.append(t("COR DO J2 TROCADA NESTA PARTIDA"))
        # "venceu" aqui = o J1 venceu (define o bônus de moedas e o som)
        self.terminar(venceu=(vencedor == 0), valor=0, titulo=titulo, linhas=linhas,
                      registrar=False)

    # --------------------------------------------------------
    # TELA DE INÍCIO (VS)
    # --------------------------------------------------------

    def _montar_menu_inicio(self):
        """
        Duas fileiras: em cima os modos (ou JOGAR!), embaixo
        VISUAL DO J2 e VOLTAR. Setas em qualquer direção navegam.
        """
        opcoes = list(self.OPCOES) if self.OPCOES else ["JOGAR!"]
        rotulos = opcoes + [self.rotulo_j2(), "VOLTAR"]
        self.menu_inicio = ui.Menu(rotulos, LARGURA // 2, 0, 200, 48, 10, 14)

        n = len(opcoes)
        largura = 300 if n == 1 else min(230, (700 - 12 * (n - 1)) // n)
        total = n * largura + (n - 1) * 12
        y1 = ALTURA - 158
        for i in range(n):
            self.menu_inicio.botoes[i].rect = pygame.Rect(
                LARGURA // 2 - total // 2 + i * (largura + 12), y1, largura, 48)
        for k, i in enumerate((n, n + 1)):
            self.menu_inicio.botoes[i].rect = pygame.Rect(
                LARGURA // 2 - 250 + k * 260, y1 + 60, 240, 48)
        b = self.menu_inicio.botoes[n]
        b.tamanho = ui.tamanho_que_cabe(b.rotulo, b.rect.w - 16, (14, 12, 10, 8))
        self.menu_inicio.indice = min(self.opcao, n - 1)

    def _evento_inicio(self, e):
        if tecla_voltar(e):
            self.sair_para_menu()
            return

        # ← → também navegam (os modos ficam lado a lado)
        if e.type == pygame.KEYDOWN and e.key in (pygame.K_LEFT, pygame.K_RIGHT,
                                                  pygame.K_a, pygame.K_d):
            n = len(self.menu_inicio.botoes)
            passo = -1 if e.key in (pygame.K_LEFT, pygame.K_a) else 1
            self.menu_inicio.indice = (self.menu_inicio.indice + passo) % n
            if self.OPCOES and self.menu_inicio.indice < n - 2:
                self.opcao = self.menu_inicio.indice
                self._preparar()
            return

        n_opcoes = len(self.menu_inicio.botoes) - 2
        antes = self.menu_inicio.indice
        escolha = self.menu_inicio.evento(e)

        if self.OPCOES and self.menu_inicio.indice != antes and self.menu_inicio.indice < n_opcoes:
            self.opcao = self.menu_inicio.indice
            self._preparar()

        if escolha is None:
            return
        if escolha == n_opcoes + 1:
            self.sair_para_menu()
        elif escolha == n_opcoes:
            self.som("boing")
            self._proximo_j2()
            b = self.menu_inicio.botoes[n_opcoes]
            b.rotulo = self.rotulo_j2()
            b.tamanho = ui.tamanho_que_cabe(b.rotulo, b.rect.w - 16, (14, 12, 10, 8))
            self._preparar()
        else:
            if self.OPCOES:
                self.opcao = escolha
            self.som("selecionar")
            self.comecar()

    def evento(self, e):
        # No fim de jogo, espera mais para ninguém pular a tela sem querer
        if self.estado == "fim" and self.tempo_estado < 1.0 and e.type == pygame.KEYDOWN:
            return
        if self.estado == "jogando" and e.type == pygame.KEYDOWN:
            quem = jogador_da_tecla(e.key)
            if quem is not None:
                self._mexeu[quem] = True
        super().evento(e)

    def _desenhar_avatar_fim(self, tela, caixa):
        """Os dois ovos: o vencedor pulando, o outro triste (empate: os dois balançam)."""
        from core.jogador import BOCA_TRISTE
        vencedor = getattr(self, "vencedor", None)
        for i, x in ((0, LARGURA // 2 - 80), (1, LARGURA // 2 + 80)):
            apar = self.aparencia(i)
            if vencedor is None:
                dy, ang = 0, math.sin(self.tempo * 3 + i) * 8
            elif vencedor == i:
                dy, ang = -abs(math.sin(self.tempo * 5)) * 16, 0
            else:
                dy, ang = 0, -14 if i == 0 else 14
                apar = (apar[0], apar[1], apar[2], BOCA_TRISTE)
            self.desenhar_ovo(tela, i, (x, caixa.y + 150 + dy), 70, espelhar=(i == 1), angulo=ang,
                              aparencia=apar)
        ui.desenhar_texto(tela, t("PARA {nome}", nome=self.nome(0).upper()), (caixa.right - 110, caixa.y + 104),
                          8, (230, 220, 170), "center")

    def _desenhar_inicio(self, tela):
        ui.veu(tela, 150)
        topo = 30
        caixa = pygame.Rect(0, topo, 760, ALTURA - topo - 30)
        caixa.centerx = LARGURA // 2
        ui.painel(tela, caixa, UI_PAINEL, self.COR, 22, 5)

        tam = ui.tamanho_que_cabe(t(self.TITULO), caixa.w - 60, (28, 24, 20))
        ui.desenhar_texto(tela, t(self.TITULO), (LARGURA // 2, topo + 22), tam, AMARELO, "midtop",
                          True, True)
        ui.desenhar_texto(tela, t("2 JOGADORES"), (LARGURA // 2, topo + 62), 12,
                          UI_TEXTO_SUAVE, "midtop")

        if self._cor_trocada:
            ui.desenhar_texto(tela, t("COR DO J2 TROCADA NESTA PARTIDA"), (LARGURA // 2, topo + 80), 8,
                              (230, 220, 170), "midtop")

        # VS com os dois ovos e os controles
        y_ovos = topo + 150
        for i, x in ((0, caixa.x + 170), (1, caixa.right - 170)):
            balanco = math.sin(self.tempo * 3 + i * 1.5) * 5
            self.desenhar_ovo(tela, i, (x, y_ovos + balanco), 70, espelhar=(i == 1))
            ui.desenhar_texto(tela, self.nome(i), (x, y_ovos + 52), 14,
                              CORES_JOGADOR[i], "midtop", True, True)
            ctrl = self.CONTROLES_J1 if i == 0 else self.CONTROLES_J2
            ui.desenhar_texto(tela, t(ctrl), (x, y_ovos + 74), 10, BRANCO, "midtop")
        ui.desenhar_texto(tela, "VS", (LARGURA // 2, y_ovos), 36, AMARELO, "center", True, True)

        # Instruções
        y = y_ovos + 104
        for linha in self.INSTRUCOES:
            for sub in ui.quebrar_linhas(t(linha), 12, caixa.w - 80):
                ui.desenhar_texto(tela, sub, (LARGURA // 2, y), 12, UI_TEXTO, "midtop")
                y += 20
            y += 4

        v = self.vitorias()
        y_rec = self.menu_inicio.botoes[0].rect.y - 30
        ui.desenhar_texto(tela, t("VITÓRIAS  J1 {a} × {b} J2", a=v[0], b=v[1]),
                          (caixa.right - 40 if self.OPCOES else LARGURA // 2, y_rec), 12, AMARELO,
                          "topright" if self.OPCOES else "midtop")
        if self.OPCOES:
            ui.desenhar_texto(tela, t("ESCOLHA O MODO:"), (caixa.x + 40, y_rec), 12,
                              UI_TEXTO_SUAVE, "topleft")

        self.menu_inicio.desenhar(tela)

    def desenhar_hud(self, tela):
        """HUD padrão do multi: nomes nos cantos (jogos costumam ter placar próprio)."""
        for i, (pos, anc) in enumerate((((16, 16), "topleft"), ((LARGURA - 80, 16), "topright"))):
            sup = ui.texto(self.nome(i), 14, CORES_JOGADOR[i], True, True)
            r = sup.get_rect(**{anc: pos}).inflate(20, 16)
            ui.sombra_suave(tela, r, 10, 4, 70)
            ui.painel(tela, r, UI_PAINEL_HUD, UI_BORDA, 10, 2, sombra=False)
            tela.blit(sup, sup.get_rect(center=r.center))
