import math

import pygame

from settings import *
from core import ui
from core.cena import Cena, tecla_voltar

# ============================================================
# MINI JOGO (CLASSE BASE)
# ============================================================
# Cuida de tudo que é igual em todos os mini jogos:
#   - tela de início (instruções, dificuldade, recorde)
#   - contagem 3, 2, 1, VAI!
#   - pausa (ESC / P / janela perde o foco)
#   - tela de fim de jogo com recorde
#   - tremida de tela, partículas e textos flutuantes
#
# Cada jogo só precisa implementar:
#   reiniciar()            -> monta uma partida nova (usa self.opcao)
#   evento_jogo(e)         -> teclado/mouse durante a partida
#   atualizar_jogo(dt)     -> lógica
#   desenhar_jogo(tela)    -> desenha TUDO (inclusive o fundo)
# e chamar self.terminar(...) quando a partida acabar.

TEMPO_CONTAGEM = 1.8


class MiniJogo(Cena):

    ID = "base"
    TITULO = "MINI JOGO"
    TITULO_CURTO = None         # nome no card do menu (padrão: TITULO)
    DESCRICAO = ""
    INSTRUCOES = []
    COR = (80, 90, 160)
    OPCOES = None               # ex: ["FÁCIL", "MÉDIO", "DIFÍCIL"]
    MENOR_MELHOR = False        # recorde é o menor valor? (tempo, jogadas)
    ROTULO_PONTOS = "PONTOS"
    CONTAGEM = True             # mostra 3, 2, 1 antes de começar
    MULTI = False               # jogo para 2 jogadores (ver MiniJogoMulti)
    TRILHA = None               # estilo da música procedural (core/compositor.py)

    # Moedas ganhas ao terminar (ver calcular_moedas)
    MOEDAS_POR = 5              # 1 moeda a cada N pontos
    MOEDAS_MAX = 40             # teto por partida
    MOEDAS_VITORIA = 0          # bônus quando vence
    MOEDAS_MIN = 1              # consolo por ter jogado (se fez algo)
    MOEDAS_RECORDE = 10         # bônus por novo recorde
    TEMPO_MINIMO = 12.0         # partidas mais curtas só dão MOEDAS_MIN (anti-farm)

    # Cache dos fundos (são desenhados uma vez só)
    _fundos = {}

    # --------------------------------------------------------

    @property
    def musica(self):
        return self.ID

    def entrar(self):
        # Trilha procedural: registra o estilo antes de tocar
        if self.TRILHA:
            from core import trilhas
            trilhas.registrar(self.ID, self.TRILHA)
        super().entrar()

    @classmethod
    def criar_fundo(cls, jogador):
        """Desenha o cenário do jogo (LARGURA x ALTURA). Sobrescrever."""
        return ui.gradiente(LARGURA, ALTURA, cls.COR, ui.escurecer(cls.COR, 60))

    @classmethod
    def fundo(cls, jogador):
        chave = (cls.ID, jogador.aparencia(), jogador.chave_visual())
        sup = MiniJogo._fundos.get(chave)
        if sup is None:
            sup = cls.criar_fundo(jogador).convert()
            MiniJogo._fundos[chave] = sup
        return sup

    @classmethod
    def miniatura(cls, jogador, tamanho):
        """Imagem do card no menu de jogos."""
        sup = pygame.transform.smoothscale(cls.fundo(jogador), tamanho)
        cls.desenhar_icone(sup, jogador)
        return sup

    @classmethod
    def desenhar_icone(cls, sup, jogador):
        """Desenha algo por cima da miniatura. Padrão: o avatar."""
        w, h = sup.get_size()
        jogador.desenhar(sup, (w // 2, h // 2 + 4), h * 0.5)

    # --------------------------------------------------------

    def __init__(self, app, menu):
        super().__init__(app)
        self.menu_jogos = menu
        self.opcao = 0
        self.pontos = 0
        self.estado = "inicio"
        self.tempo_estado = 0.0
        self.tempo = 0.0
        self.tremor = 0.0
        self.novo_recorde = False
        self.titulo_fim = ""
        self.linhas_fim = []
        self.venceu = False
        self.moedas_ganhas = 0
        self.tempo_partida = 0.0    # segundos jogando (sem contar pausa)
        self.particulas = ui.Particulas()
        self.textos = ui.TextoFlutuante()
        self.camada = pygame.Surface((LARGURA, ALTURA))
        self.botao_pausa = pygame.Rect(LARGURA - 64, 12, 48, 48)
        self._montar_menu_inicio()
        self.menu_pausa = ui.Menu(["CONTINUAR", "REINICIAR", "SAIR"],
                                  LARGURA // 2, 300, 340, 56, 14, 16)
        self.menu_fim = None
        self._preparar()

    # --------------------------------------------------------
    # CONTROLE DE ESTADO
    # --------------------------------------------------------

    def _montar_menu_inicio(self):
        rotulos = list(self.OPCOES) if self.OPCOES else ["JOGAR!"]
        rotulos.append("VOLTAR")
        altura = 50 if len(rotulos) > 2 else 56
        y = ALTURA - 70 - len(rotulos) * (altura + 10)
        self.menu_inicio = ui.Menu(rotulos, LARGURA // 2, y, 320, altura, 10, 16)
        self.menu_inicio.indice = min(self.opcao, len(rotulos) - 2)

    def _preparar(self):
        """Limpa efeitos e monta uma partida nova."""
        self.pontos = 0
        self.tremor = 0.0
        self.particulas.limpar()
        self.textos.lista.clear()
        self.reiniciar()

    def _mudar_estado(self, estado):
        self.estado = estado
        self.tempo_estado = 0.0

    def comecar(self):
        self.tempo_partida = 0.0
        self._preparar()
        self._mudar_estado("contagem" if self.CONTAGEM else "jogando")

    def pausar(self):
        if self.estado in ("jogando", "contagem"):
            self.som("clique")
            self.menu_pausa.indice = 0
            self._estado_antes_pausa = self.estado
            self._mudar_estado("pausado")

    def chave_recorde(self, opcao=None):
        opcao = self.opcao if opcao is None else opcao
        return f"{self.ID}_{opcao}" if self.OPCOES else self.ID

    def recorde(self, opcao=None):
        return self.app.save.recorde(self.chave_recorde(opcao))

    @classmethod
    def formatar(cls, valor):
        """Como pontos/recorde aparecem na tela. Sobrescrever se precisar."""
        return str(valor)

    def calcular_moedas(self, valor, venceu):
        """
        Quantas moedas a partida vale. O padrão usa as constantes
        MOEDAS_*; jogos podem sobrescrever com uma regra própria.
        """
        if self.MENOR_MELHOR:
            base = self.MOEDAS_VITORIA if venceu else self.MOEDAS_MIN
        else:
            base = valor // max(1, self.MOEDAS_POR)
            if venceu:
                base += self.MOEDAS_VITORIA
            if valor > 0 or venceu:
                base = max(base, self.MOEDAS_MIN)
        return max(0, min(self.MOEDAS_MAX, int(base)))

    def terminar(self, venceu=False, valor=None, titulo=None, linhas=None,
                 registrar=True):
        """
        Encerra a partida.
          venceu   -> muda o título e o som
          valor    -> valor do recorde (padrão: self.pontos)
          registrar-> False para não contar recorde (ex: perdeu no minado)
        """
        if self.estado == "fim":
            return

        valor = self.pontos if valor is None else valor
        self.venceu = venceu
        self.novo_recorde = False

        # Zero pontos não conta como recorde
        if registrar and (self.MENOR_MELHOR or valor > 0):
            self.novo_recorde = self.app.save.registrar(
                self.chave_recorde(), valor, self.MENOR_MELHOR)

        # Moedas (com bônus de recorde, variedade, pet e "ovo feliz")
        extra = self.app.ao_terminar_minijogo(self, valor, venceu)
        if self.tempo_partida < self.TEMPO_MINIMO and not venceu:
            moedas = min(self.MOEDAS_MIN, self.calcular_moedas(valor, venceu))
        else:
            moedas = self.calcular_moedas(valor, venceu) + extra
            if self.novo_recorde:
                moedas += self.MOEDAS_RECORDE
        moedas = round(moedas * self.app.bonus_moedas()) if moedas > 0 else 0
        self.moedas_ganhas = self.app.save.ganhar(moedas)

        self.titulo_fim = titulo or ("VOCÊ VENCEU!" if venceu else "FIM DE JOGO")
        self.linhas_fim = linhas if linhas is not None else [
            f"{self.ROTULO_PONTOS}: {self.formatar(valor)}"
        ]

        rotulos = ["JOGAR DE NOVO"]
        if self.OPCOES:
            rotulos.append("DIFICULDADE")
        rotulos.append("MENU DE JOGOS")
        self.menu_fim = ui.Menu(rotulos, LARGURA // 2, 420, 340, 54, 12, 16)

        # No multiplayer alguém sempre ganha: som de festa
        self.som("vencer" if venceu or self.novo_recorde or self.MULTI else "perder")
        self._mudar_estado("fim")

    def sair_para_menu(self):
        self.som("voltar")
        self.app.trocar(self.menu_jogos)

    def tremer(self, forca=0.3):
        self.tremor = max(self.tremor, forca)

    # --------------------------------------------------------
    # GANCHOS (sobrescrever nos jogos)
    # --------------------------------------------------------

    def reiniciar(self):
        pass

    def evento_jogo(self, e):
        pass

    def atualizar_jogo(self, dt):
        pass

    def desenhar_jogo(self, tela):
        tela.blit(self.fundo(self.jogador), (0, 0))

    def desenhar_hud(self, tela):
        """HUD padrão: pontos à esquerda e recorde ao lado."""
        caixa = pygame.Rect(12, 12, 300, 48)
        ui.painel(tela, caixa, (20, 24, 40), BRANCO, 12, 3, sombra=False)
        ui.desenhar_texto(tela, f"{self.ROTULO_PONTOS}: {self.formatar(self.pontos)}",
                          (caixa.x + 16, caixa.centery), 14, AMARELO, "midleft")

        rec = self.recorde()
        if rec is not None:
            ui.desenhar_texto(tela, f"RECORDE: {self.formatar(rec)}",
                              (caixa.right + 16, caixa.centery), 12, BRANCO, "midleft")

    # --------------------------------------------------------
    # LOOP
    # --------------------------------------------------------

    def evento(self, e):
        # Janela perdeu o foco -> pausa automaticamente
        if e.type == pygame.WINDOWFOCUSLOST:
            self.pausar()
            return

        if self.estado == "inicio":
            self._evento_inicio(e)

        elif self.estado in ("jogando", "contagem"):
            if tecla_voltar(e) or (e.type == pygame.KEYDOWN and e.key == pygame.K_p):
                self.pausar()
            elif (e.type == pygame.MOUSEBUTTONDOWN and e.button == 1
                  and self.botao_pausa.collidepoint(e.pos)):
                self.pausar()
            elif self.estado == "jogando":
                self.evento_jogo(e)

        elif self.estado == "pausado":
            if tecla_voltar(e) or (e.type == pygame.KEYDOWN and e.key == pygame.K_p):
                self._mudar_estado(self._estado_antes_pausa)
                return
            escolha = self.menu_pausa.evento(e)
            if escolha == 0:
                self._mudar_estado(self._estado_antes_pausa)
            elif escolha == 1:
                self.som("selecionar")
                self.comecar()
            elif escolha == 2:
                self.sair_para_menu()

        elif self.estado == "fim":
            # Pequena espera para não pular a tela sem querer
            if self.tempo_estado < 0.6:
                return
            if tecla_voltar(e):
                self.sair_para_menu()
                return
            escolha = self.menu_fim.evento(e)
            if escolha is None:
                return
            rotulo = self.menu_fim.botoes[escolha].rotulo
            if rotulo == "JOGAR DE NOVO":
                self.som("selecionar")
                self.comecar()
            elif rotulo == "DIFICULDADE":
                self.som("selecionar")
                self._montar_menu_inicio()
                self._preparar()
                self._mudar_estado("inicio")
            else:
                self.sair_para_menu()

    def _evento_inicio(self, e):
        if tecla_voltar(e):
            self.sair_para_menu()
            return

        antes = self.menu_inicio.indice
        escolha = self.menu_inicio.evento(e)

        # Mostrar a prévia da dificuldade selecionada
        if self.OPCOES and self.menu_inicio.indice != antes \
                and self.menu_inicio.indice < len(self.OPCOES):
            self.opcao = self.menu_inicio.indice
            self._preparar()

        if escolha is None:
            return

        if escolha == len(self.menu_inicio.botoes) - 1:
            self.sair_para_menu()
        else:
            if self.OPCOES:
                self.opcao = escolha
            self.som("selecionar")
            self.comecar()

    def atualizar(self, dt):
        self.tempo += dt
        self.tempo_estado += dt
        self.tremor = max(0.0, self.tremor - dt)

        if self.estado == "jogando":
            self.tempo_partida += dt
            self.atualizar_jogo(dt)
        elif self.estado == "contagem":
            if self.tempo_estado >= TEMPO_CONTAGEM:
                self._mudar_estado("jogando")
        elif self.estado == "inicio":
            antes = self.menu_inicio.indice
            self.menu_inicio.atualizar(dt)
            if self.OPCOES and self.menu_inicio.indice != antes \
                    and self.menu_inicio.indice < len(self.OPCOES):
                self.opcao = self.menu_inicio.indice
                self._preparar()
        elif self.estado == "pausado":
            self.menu_pausa.atualizar(dt)
        elif self.estado == "fim":
            self.menu_fim.atualizar(dt)

        # Efeitos continuam no fim de jogo (explosões, confete...)
        if self.estado in ("jogando", "fim"):
            self.particulas.atualizar(dt)
            self.textos.atualizar(dt)

    # --------------------------------------------------------
    # DESENHO
    # --------------------------------------------------------

    def desenhar(self, tela):
        if self.tremor > 0:
            self.desenhar_jogo(self.camada)
            f = int(self.tremor * 30)
            dx = int(math.sin(self.tempo * 90) * f)
            dy = int(math.cos(self.tempo * 70) * f)
            tela.fill((0, 0, 0))
            tela.blit(self.camada, (dx, dy))
        else:
            self.desenhar_jogo(tela)

        if self.estado != "inicio":
            self.desenhar_hud(tela)
            self._desenhar_botao_pausa(tela)

        if self.estado == "inicio":
            self._desenhar_inicio(tela)
        elif self.estado == "contagem":
            self._desenhar_contagem(tela)
        elif self.estado == "pausado":
            self._desenhar_pausa(tela)
        elif self.estado == "fim":
            self._desenhar_fim(tela)

    def _desenhar_botao_pausa(self, tela):
        if self.estado not in ("jogando", "contagem"):
            return
        r = self.botao_pausa
        hover = r.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(tela, (70, 80, 130) if hover else (20, 24, 40), r, border_radius=12)
        pygame.draw.rect(tela, BRANCO, r, 3, border_radius=12)
        pygame.draw.rect(tela, BRANCO, (r.centerx - 9, r.centery - 10, 6, 20))
        pygame.draw.rect(tela, BRANCO, (r.centerx + 3, r.centery - 10, 6, 20))

    def _desenhar_inicio(self, tela):
        ui.veu(tela, 150)

        topo = 40
        caixa = pygame.Rect(0, topo, 700, ALTURA - topo - 40)
        caixa.centerx = LARGURA // 2
        ui.painel(tela, caixa, (28, 32, 56), self.COR, 22, 5)

        # Título com o avatar do lado
        tam = ui.tamanho_que_cabe(self.TITULO, caixa.w - 190, (30, 26, 22, 18))
        ui.desenhar_texto(tela, self.TITULO, (LARGURA // 2, topo + 28 + (30 - tam) // 2), tam,
                          AMARELO, "midtop")
        self.jogador.desenhar(tela, (caixa.x + 60, topo + 46 + math.sin(self.tempo * 3) * 4), 44)
        self.jogador.desenhar(tela, (caixa.right - 60, topo + 46 + math.cos(self.tempo * 3) * 4),
                              44, espelhar=True)

        # Instruções
        y = topo + 92
        for linha in self.INSTRUCOES:
            for sub in ui.quebrar_linhas(linha, 12, caixa.w - 80):
                ui.desenhar_texto(tela, sub, (LARGURA // 2, y), 12, BRANCO, "midtop")
                y += 22
            y += 6

        # Recorde da opção selecionada
        indice = self.menu_inicio.indice
        opcao = indice if (self.OPCOES and indice < len(self.OPCOES)) else self.opcao
        rec = self.recorde(opcao)
        texto_rec = f"★ RECORDE: {self.formatar(rec)} ★" if rec is not None else "★ SEM RECORDE AINDA ★"
        y_rec = self.menu_inicio.botoes[0].rect.y - 36
        ui.desenhar_texto(tela, texto_rec, (LARGURA // 2, y_rec), 14, AMARELO, "midtop")

        limite = y_rec - 12
        if self.OPCOES:
            ui.desenhar_texto(tela, "ESCOLHA A DIFICULDADE", (LARGURA // 2, y_rec - 30),
                              12, (180, 200, 255), "midtop")
            limite = y_rec - 42

        # Prévia do jogo no espaço que sobrar
        espaco = limite - y - 8
        if espaco >= 90:
            altura = min(170, espaco)
            tamanho = (int(altura * 1.6), altura)
            if getattr(self, "_previa_tam", None) != tamanho:
                self._previa = self.miniatura(self.jogador, tamanho)
                self._previa_tam = tamanho
            r = self._previa.get_rect(midtop=(LARGURA // 2, y + 4))
            pygame.draw.rect(tela, (0, 0, 0), r.inflate(12, 12).move(0, 4), border_radius=10)
            tela.blit(self._previa, r)
            pygame.draw.rect(tela, self.COR, r.inflate(8, 8), 4, border_radius=8)

        self.menu_inicio.desenhar(tela)

    def _desenhar_contagem(self, tela):
        restante = TEMPO_CONTAGEM - self.tempo_estado
        passo = TEMPO_CONTAGEM / 3
        numero = int(restante / passo) + 1
        frac = (restante % passo) / passo
        tamanho = int(56 + 40 * frac)
        rotulo = str(max(1, min(3, numero)))
        ui.desenhar_texto(tela, rotulo, (LARGURA // 2, ALTURA // 2), tamanho,
                          AMARELO, "center")
        ui.desenhar_texto(tela, "PREPARE-SE!", (LARGURA // 2, ALTURA // 2 + 80), 16,
                          BRANCO, "center")

    def _desenhar_pausa(self, tela):
        ui.veu(tela, 170)
        caixa = pygame.Rect(0, 0, 440, 360)
        caixa.center = (LARGURA // 2, ALTURA // 2 + 20)
        ui.painel(tela, caixa, (28, 32, 56), self.COR, 20, 5)
        ui.desenhar_texto(tela, "PAUSADO", (LARGURA // 2, caixa.y + 34), 28,
                          AMARELO, "midtop")
        self.menu_pausa.desenhar(tela)

    def _desenhar_fim(self, tela):
        ui.veu(tela, 160)
        caixa = pygame.Rect(0, 0, 600, 560)
        caixa.center = (LARGURA // 2, ALTURA // 2 + 10)
        ui.painel(tela, caixa, (28, 32, 56), AMARELO if self.venceu else self.COR, 22, 5)

        cor_titulo = AMARELO if self.venceu else (255, 120, 120)
        tam = ui.tamanho_que_cabe(self.titulo_fim, caixa.w - 40, (30, 24, 20, 16))
        ui.desenhar_texto(tela, self.titulo_fim, (LARGURA // 2, caixa.y + 30 + (30 - tam) // 2),
                          tam, cor_titulo, "midtop")

        # Avatar feliz pulando (venceu) ou tonto balançando (perdeu)
        if self.venceu or self.novo_recorde:
            dy = -abs(math.sin(self.tempo * 5)) * 16
            ang = 0
        else:
            dy = 0
            ang = math.sin(self.tempo * 4) * 12
        self.jogador.desenhar(tela, (LARGURA // 2, caixa.y + 150 + dy), 80, angulo=ang)
        self.app.desenhar_pet(tela, (LARGURA // 2 - 110, caixa.y + 190), feliz=self.venceu)

        # Moedas ganhas (contando para cima)
        if self.moedas_ganhas > 0:
            mostrar = min(self.moedas_ganhas, int(self.tempo_estado * 40) + 1)
            pilula = pygame.Rect(0, 0, 130, 46)
            pilula.center = (caixa.right - 110, caixa.y + 150)
            ui.painel(tela, pilula, (60, 48, 20), AMARELO, 23, 3, sombra=False)
            ui.moeda(tela, (pilula.x + 26, pilula.centery), 14)
            ui.desenhar_texto(tela, f"+{mostrar}", (pilula.x + 48, pilula.centery), 16,
                              AMARELO, "midleft")

        y = caixa.y + 230
        for linha in self.linhas_fim:
            ui.desenhar_texto(tela, linha, (LARGURA // 2, y), 16, BRANCO, "midtop")
            y += 30

        if self.novo_recorde:
            if int(self.tempo * 4) % 2 == 0:
                ui.desenhar_texto(tela, "★ NOVO RECORDE! ★", (LARGURA // 2, y + 4), 18,
                                  AMARELO, "midtop")
        else:
            rec = self.recorde()
            if rec is not None:
                ui.desenhar_texto(tela, f"RECORDE: {self.formatar(rec)}", (LARGURA // 2, y + 4),
                                  14, (180, 200, 255), "midtop")

        # Posiciona o menu logo abaixo do texto
        base = max(y + 50, caixa.bottom - len(self.menu_fim.botoes) * 66 - 10)
        for i, b in enumerate(self.menu_fim.botoes):
            b.rect.midtop = (LARGURA // 2, base + i * 66)
        self.menu_fim.desenhar(tela)
