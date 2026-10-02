import math
import random

import pygame

from settings import *
from core import ui
from core.cena import Cena, tecla_voltar
from core.idioma import t

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
TEMPO_VAI = 0.6             # quanto tempo o "VAI!" fica na tela


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

    # Moedas ganhas ao terminar (ver calcular_moedas)
    MOEDAS_POR = 5              # 1 moeda a cada N pontos
    MOEDAS_MAX = 40             # teto por partida
    MOEDAS_VITORIA = 0          # bônus quando vence
    MOEDAS_MIN = 1              # consolo por ter jogado (se fez algo)
    MOEDAS_RECORDE = 5          # bônus por novo recorde
    TEMPO_MINIMO = 12.0         # partidas mais curtas só dão MOEDAS_MIN (anti-farm)

    # Cache dos fundos (são desenhados uma vez só)
    _fundos = {}

    # --------------------------------------------------------

    @property
    def musica(self):
        return self.ID

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
        self._confete_fim = ui.Particulas()     # festa da tela de fim (por cima de tudo)
        self._vai = 0.0                    # tempo restante do "VAI!"
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
        self._confete_fim.limpar()
        self._vai = 0.0
        self.reiniciar()

    def _mudar_estado(self, estado):
        self.estado = estado
        self.tempo_estado = 0.0

        # Chuva de confete quando a partida termina bem
        if estado == "fim" and (self.venceu or self.novo_recorde or self.MULTI):
            cores = [AMARELO, (255, 140, 170), (140, 220, 255), (150, 235, 140), UI_TEXTO]
            for x in (LARGURA // 2 - 230, LARGURA // 2 + 230):
                self._confete_fim.explodir((x, ALTURA // 2 - 140), cores, 26, 420, 1.8, (3, 6), 380)

    def comecar(self):
        self.tempo_partida = 0.0
        from jogos import trofeus
        self._medalha_inicio = trofeus.nivel(self.app.save, type(self))[0]
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
        self.xp_ganho = 0
        self._moedas_mostradas = 0
        self._confete = []

        # Zero pontos não conta como recorde
        if registrar and (self.MENOR_MELHOR or valor > 0):
            self.novo_recorde = self.app.save.registrar(
                self.chave_recorde(), valor, self.MENOR_MELHOR)

        # Moedas (com bônus de recorde, variedade, pet e "ovo feliz")
        self.detalhe_moedas = []
        if not self.partida_valida():
            # Ninguém jogou de verdade: não paga nada (anti-farm)
            moedas = 0
            self.detalhe_moedas = [t("NINGUÉM JOGOU: SEM OVOEDAS")]
        else:
            curta = self.tempo_partida < self.TEMPO_MINIMO and not venceu
            # Partida curta não gasta o bônus da 1ª partida do dia
            extra = self.app.ao_terminar_minijogo(self, valor, venceu, variedade=not curta)
            base = self.calcular_moedas(valor, venceu)
            if curta:
                moedas = min(self.MOEDAS_MIN, base)
                self.detalhe_moedas = [t("PARTIDA CURTA: +{n}", n=moedas),
                                       t("JOGUE MAIS DE {n} s", n=int(self.TEMPO_MINIMO))]
            else:
                moedas = base + extra
                self.detalhe_moedas.append(t("PARTIDA +{n}", n=base))
                if extra:
                    self.detalhe_moedas.append(t("1ª DO DIA +{n}", n=extra))
                if self.novo_recorde:
                    moedas += self.MOEDAS_RECORDE
                    self.detalhe_moedas.append(t("RECORDE +{n}", n=self.MOEDAS_RECORDE))
            bonus = self.app.bonus_moedas()
            if moedas > 0 and round(moedas * bonus) > moedas:
                self.detalhe_moedas.append(t("BÔNUS ×{n}", n=f"{bonus:.2f}".replace(".", ",")))
        moedas = round(moedas * self.app.bonus_moedas()) if moedas > 0 else 0
        self.moedas_ganhas = self.app.save.ganhar(moedas)
        if self.moedas_ganhas > 0:
            from core import progresso
            progresso.contar(self.app, "moedas_jogos", self.moedas_ganhas)

        self.titulo_fim = titulo or ("VOCÊ VENCEU!" if venceu else "FIM DE JOGO")
        self.linhas_fim = linhas if linhas is not None else [
            f"{t(self.ROTULO_PONTOS)}: {self.formatar(valor)}"
        ]

        rotulos = ["JOGAR DE NOVO"]
        if self.OPCOES:
            rotulos.append("DIFICULDADE")
        rotulos.append("MENU DE JOGOS")
        self.menu_fim = ui.Menu(rotulos, LARGURA // 2, 420, 340, 54, 12, 16)

        self._avaliar_medalha(valor)
        if self.partida_valida() and not self.MULTI and registrar:
            from core import codigo
            codigo.verificar_desafios(self.app, self, valor)
        if self.novo_recorde:
            self._confete = [0.0, 0.3, 0.6]

        # No multiplayer alguém sempre ganha: som de festa
        if self.novo_recorde:
            self.som("recorde")
        else:
            self.som("vencer" if venceu or self.MULTI else "perder")
        self._mudar_estado("fim")

    def partida_valida(self):
        """False = ninguém jogou de verdade (a partida não paga moedas)."""
        return True

    def _avaliar_medalha(self, valor):
        """Medalha nova nesta partida? E quanto falta para a próxima?"""
        from jogos import trofeus
        from core import progresso
        antes = getattr(self, "_medalha_inicio", None)
        agora, _ = trofeus.nivel(self.app.save, type(self))
        ordem = [None] + trofeus.NIVEIS
        self.medalha_nova = agora if ordem.index(agora) > ordem.index(antes) else None
        if self.medalha_nova == "ouro":
            progresso.contar(self.app, "ouros")
        self._medalha_inicio = agora

        # "Faltam X para a PRATA" (só nos jogos de pontuação)
        self.falta_medalha = ""
        r = trofeus.regra(type(self))
        if r is None or r["tipo"] not in ("maior", "menor") or agora == "ouro":
            return
        proxima = trofeus.NIVEIS[ordem.index(agora)]
        melhor = trofeus._melhor(self.app.save, type(self), r["tipo"] == "menor")
        if melhor is None:
            melhor = valor
        nome = t({"bronze": "BRONZE", "prata": "PRATA", "ouro": "OURO"}[proxima])
        if r["tipo"] == "menor":
            self.falta_medalha = t("{nome}: FAÇA {n} OU MENOS", nome=nome, n=self.formatar(r[proxima]))
        else:
            falta = r[proxima] - melhor
            if falta > 0:
                self.falta_medalha = t("FALTAM {n} PARA O {nome}!", n=self.formatar(falta), nome=nome)

    def sair_para_menu(self):
        self.som("voltar")
        self.app.trocar(self.menu_jogos)

    def tremer(self, forca=0.3):
        if self.app.config["reduzir_tremor"]:
            forca *= 0.25
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
        ui.sombra_suave(tela, caixa, 12, 4, 70)
        ui.painel(tela, caixa, UI_PAINEL_HUD, UI_BORDA, 12, 3, sombra=False)
        ui.desenhar_texto(tela, f"{t(self.ROTULO_PONTOS)}: {self.formatar(self.pontos)}",
                          (caixa.x + 16, caixa.centery), 14, AMARELO, "midleft", True, True)

        # Recorde fica direto sobre o jogo: contorno para ler em qualquer fundo
        rec = self.recorde()
        if rec is not None:
            ui.desenhar_texto(tela, t("RECORDE: {n}", n=self.formatar(rec)),
                              (caixa.right + 16, caixa.centery), 12, UI_TEXTO, "midleft",
                              True, True)

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
                self._vai = TEMPO_VAI
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

        if self.estado == "fim":
            self._atualizar_fim(dt)

        # Efeitos continuam no fim de jogo (explosões, confete...)
        if self.estado in ("jogando", "fim"):
            self.particulas.atualizar(dt)
            self.textos.atualizar(dt)
        if self.estado == "fim":
            self._confete_fim.atualizar(dt)
        if self.estado == "jogando":
            self._vai = max(0.0, self._vai - dt)

    def _atualizar_fim(self, dt):
        # Contador de moedas subindo com "tic" (e "plim" no final)
        if self.moedas_ganhas > 0:
            mostrar = min(self.moedas_ganhas, int(self.tempo_estado * 40) + 1)
            antes = getattr(self, "_moedas_mostradas", 0)
            if mostrar != antes:
                self._moedas_mostradas = mostrar
                if mostrar >= self.moedas_ganhas:
                    self.som("moeda", 0.6)
                elif mostrar % 2 == 0:
                    self.som("tic", 0.3)
        # Confete do recorde em 3 rajadas
        confete = getattr(self, "_confete", [])
        while confete and self.tempo_estado >= confete[0]:
            confete.pop(0)
            cx = LARGURA // 2 + random.randint(-90, 90)
            self.particulas.explodir((cx, ALTURA // 2 - 140),
                                     [AMARELO, (255, 90, 140), (120, 200, 255), BRANCO, (120, 255, 150)],
                                     40, 420, 1.4, (3, 7), 380)

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
        elif self.estado == "jogando" and self._vai > 0:
            self._desenhar_vai(tela)

    def _desenhar_botao_pausa(self, tela):
        if self.estado not in ("jogando", "contagem"):
            return
        hover = self.botao_pausa.collidepoint(pygame.mouse.get_pos())
        r = ui.botao_base(tela, self.botao_pausa, UI_PAINEL_HUD, (70, 80, 130), hover, raio=12)
        pygame.draw.rect(tela, UI_TEXTO, (r.centerx - 9, r.centery - 10, 6, 20), border_radius=2)
        pygame.draw.rect(tela, UI_TEXTO, (r.centerx + 3, r.centery - 10, 6, 20), border_radius=2)

    def _desenhar_inicio(self, tela):
        ui.veu(tela, 150)

        topo = 40
        caixa = pygame.Rect(0, topo, 700, ALTURA - topo - 40)
        caixa.centerx = LARGURA // 2
        ui.painel(tela, caixa, UI_PAINEL, self.COR, 22, 5)

        # Título com o avatar do lado
        titulo = t(self.TITULO)
        tam = ui.tamanho_que_cabe(titulo, caixa.w - 190, (30, 26, 22, 18))
        ui.desenhar_texto(tela, titulo, (LARGURA // 2, topo + 28 + (30 - tam) // 2), tam,
                          AMARELO, "midtop", True, True)
        self.jogador.desenhar(tela, (caixa.x + 60, topo + 46 + math.sin(self.tempo * 3) * 4), 44)
        self.jogador.desenhar(tela, (caixa.right - 60, topo + 46 + math.cos(self.tempo * 3) * 4),
                              44, espelhar=True)

        # Instruções
        y = topo + 92
        for linha in self.INSTRUCOES:
            for sub in ui.quebrar_linhas(t(linha), 12, caixa.w - 80):
                ui.desenhar_texto(tela, sub, (LARGURA // 2, y), 12, UI_TEXTO, "midtop")
                y += 22
            y += 6

        # Recorde da opção selecionada
        indice = self.menu_inicio.indice
        opcao = indice if (self.OPCOES and indice < len(self.OPCOES)) else self.opcao
        rec = self.recorde(opcao)
        texto_rec = t("★ RECORDE: {n} ★", n=self.formatar(rec)) if rec is not None else t("★ SEM RECORDE AINDA ★")
        y_rec = self.menu_inicio.botoes[0].rect.y - 36
        ui.desenhar_texto(tela, texto_rec, (LARGURA // 2, y_rec), 14, AMARELO, "midtop",
                          True, True)

        # Metas das medalhas (bronze / prata / ouro)
        y_med = y_rec - 22
        if self._desenhar_medalhas(tela, y_med):
            y_rec = y_med

        limite = y_rec - 12
        if self.OPCOES:
            ui.desenhar_texto(tela, t("ESCOLHA A DIFICULDADE"), (LARGURA // 2, y_rec - 30),
                              12, UI_TEXTO_SUAVE, "midtop")
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
            ui.sombra_suave(tela, r.inflate(12, 12), 10, 5, 120)
            tela.blit(self._previa, r)
            pygame.draw.rect(tela, self.COR, r.inflate(8, 8), 4, border_radius=8)

        self.menu_inicio.desenhar(tela)

    def _textos_medalhas(self):
        from jogos import trofeus
        r = trofeus.regra(type(self))
        if r is None:
            return None
        tipo = r["tipo"]
        if tipo == "opcao":
            if not self.OPCOES:
                return None
            return [t("VENCER {op}", op=t(op)) for op in self.OPCOES[:3]]
        if tipo == "partidas":
            return [(t("{n} PARTIDAS", n=r[n]) if r[n] > 1 else t("{n} PARTIDA", n=r[n])) for n in trofeus.NIVEIS]
        if tipo == "menor":
            return [t("{n} OU MENOS", n=self.formatar(r[n])) for n in trofeus.NIVEIS]
        return [self.formatar(r[n]) for n in trofeus.NIVEIS]

    def _desenhar_medalhas(self, tela, y):
        """Uma linha com as 3 metas; a medalha conquistada fica cheia."""
        from jogos import trofeus
        textos = self._textos_medalhas()
        if not textos:
            return False
        obtido, _ = trofeus.nivel(self.app.save, type(self))
        nivel = trofeus.NIVEIS.index(obtido) if obtido else -1
        cores = [(205, 127, 50), (200, 205, 215), (255, 214, 64)]
        sups = [ui.texto(tx, 8, BRANCO if k <= nivel else (190, 190, 210)) for k, tx in enumerate(textos)]
        total = sum(s.get_width() + 22 for s in sups) + 16 * (len(sups) - 1)
        x = LARGURA // 2 - total // 2
        for k, s in enumerate(sups):
            c = (x + 7, y + 5)
            if k <= nivel:
                pygame.draw.circle(tela, cores[k], c, 7)
                pygame.draw.circle(tela, ui.escurecer(cores[k], 60), c, 7, 2)
            else:
                pygame.draw.circle(tela, cores[k], c, 7, 2)
            tela.blit(s, (x + 20, y + 1))
            x += s.get_width() + 22 + 16
        return True

    def _desenhar_contagem(self, tela):
        restante = TEMPO_CONTAGEM - self.tempo_estado
        passo = TEMPO_CONTAGEM / 3
        numero = int(restante / passo) + 1
        f = 1.0 - (restante % passo) / passo        # 0 -> 1 dentro de cada número
        rotulo = str(max(1, min(3, numero)))
        centro = (LARGURA // 2, ALTURA // 2)

        # Disco macio atrás do número (entra com "pop")
        pop = ui.quicar(min(1.0, f / 0.3))
        raio = int(78 * pop)
        if raio > 4:
            disco = pygame.Surface((raio * 2 + 8, raio * 2 + 8), pygame.SRCALPHA)
            c = (raio + 4, raio + 4)
            pygame.draw.circle(disco, (*UI_PAINEL, 190), c, raio)
            pygame.draw.circle(disco, (*AMARELO, 220), c, raio, 5)
            tela.blit(disco, disco.get_rect(center=centro))

        # Número cresce com pop e some no finalzinho
        tamanho = max(8, int(64 * pop) // 4 * 4)       # passos de 4: menos fontes em cache
        sup = ui.texto(rotulo, tamanho, AMARELO, True, True)
        if f > 0.8:
            sup = sup.copy()
            sup.set_alpha(int(255 * (1.0 - f) / 0.2))
        tela.blit(sup, sup.get_rect(center=centro))

        ui.desenhar_texto(tela, t("PREPARE-SE!"), (LARGURA // 2, ALTURA // 2 + 110), 16,
                          UI_TEXTO, "center", True, True)

    def _desenhar_vai(self, tela):
        """'VAI!' rapidinho logo depois da contagem."""
        k = 1.0 - self._vai / TEMPO_VAI
        tamanho = max(8, int(56 * ui.quicar(min(1.0, k / 0.35))) // 4 * 4)
        sup = ui.texto(t("VAI!"), tamanho, (140, 240, 140), True, True)
        if k > 0.55:
            sup = sup.copy()
            sup.set_alpha(int(255 * max(0.0, 1.0 - k) / 0.45))
        tela.blit(sup, sup.get_rect(center=(LARGURA // 2, ALTURA // 2)))

    def _desenhar_pausa(self, tela):
        ui.veu(tela, 170)
        caixa = pygame.Rect(0, 0, 440, 360)
        caixa.center = (LARGURA // 2, ALTURA // 2 + 20)
        ui.painel(tela, caixa, UI_PAINEL, self.COR, 20, 5)
        ui.desenhar_texto(tela, t("PAUSADO"), (LARGURA // 2, caixa.y + 34), 28,
                          AMARELO, "midtop", True, True)
        self.menu_pausa.desenhar(tela)

    # Raios de luz atrás do avatar quando a partida termina bem
    _raios = None

    @classmethod
    def _sup_raios(cls):
        if MiniJogo._raios is None:
            lado = 260
            s = pygame.Surface((lado, lado), pygame.SRCALPHA)
            c = lado // 2
            for i in range(12):
                a = i * math.tau / 12
                pontos = [(c, c),
                          (c + math.cos(a - 0.13) * c, c + math.sin(a - 0.13) * c),
                          (c + math.cos(a + 0.13) * c, c + math.sin(a + 0.13) * c)]
                pygame.draw.polygon(s, (255, 226, 120, 38), pontos)
            MiniJogo._raios = s
        return MiniJogo._raios

    def _desenhar_avatar_fim(self, tela, caixa):
        """Avatar feliz pulando (venceu) ou tonto balançando (perdeu)."""
        if self.venceu or self.novo_recorde:
            dy = -abs(math.sin(self.tempo * 5)) * 16
            ang = 0
        else:
            dy = 0
            ang = math.sin(self.tempo * 4) * 12
        self.jogador.desenhar(tela, (LARGURA // 2, caixa.y + 150 + dy), 80, angulo=ang)
        self.app.desenhar_pet(tela, (LARGURA // 2 - 110, caixa.y + 190), feliz=self.venceu)

    def _desenhar_xp_fim(self, tela, caixa):
        """+XP com a barra do nível e o selo de MEDALHA NOVA (lado esquerdo)."""
        from core import progresso
        xp = getattr(self, "xp_ganho", 0)
        cx = caixa.x + 110
        if xp:
            pilula = pygame.Rect(0, 0, 130, 46)
            pilula.center = (cx, caixa.y + 130)
            ui.painel(tela, pilula, (24, 44, 70), (120, 220, 255), 23, 3, sombra=False)
            ui.desenhar_texto(tela, f"+{xp} XP", pilula.center, 14, (170, 235, 255), "center")
            nivel, atual, meta = progresso.progresso(self.app.save)
            barra = pygame.Rect(0, 0, 110, 8)
            barra.midtop = (cx, pilula.bottom + 10)
            pygame.draw.rect(tela, (60, 60, 90), barra, border_radius=4)
            enche = min(1.0, self.tempo_estado / 0.8) * atual / meta
            pygame.draw.rect(tela, (120, 220, 255), (barra.x, barra.y, max(3, int(barra.w * enche)),
                                                     barra.h), border_radius=4)
            ui.desenhar_texto(tela, t("NÍVEL {n}", n=nivel), (cx, barra.bottom + 6), 8, (180, 220, 255),
                              "midtop")

        medalha = getattr(self, "medalha_nova", None)
        if medalha and self.tempo_estado > 0.4:
            cores = {"bronze": (205, 127, 50), "prata": (200, 205, 215), "ouro": (255, 214, 64)}
            cor = cores[medalha]
            k = min(1.0, (self.tempo_estado - 0.4) * 4)
            raio = int(15 * (1 + 0.3 * math.sin(k * math.pi)))
            c = (cx - 64, caixa.y + 212)
            pygame.draw.circle(tela, ui.escurecer(cor, 70), (c[0], c[1] + 2), raio)
            pygame.draw.circle(tela, cor, c, raio)
            ui.estrela(tela, c, raio * 0.6, ui.clarear(cor, 60), self.tempo * 1.5)
            ui.desenhar_texto(tela, t("MEDALHA NOVA!"), (c[0] + 22, c[1] - 7), 8, AMARELO, "midleft")
            ui.desenhar_texto(tela, t(medalha.upper()), (c[0] + 22, c[1] + 7), 10, cor, "midleft")

    def _desenhar_fim(self, tela):
        te = self.tempo_estado
        festa = self.venceu or self.novo_recorde

        # Véu entra suave (não "corta" o jogo de uma vez)
        ui.veu(tela, int(160 * ui.suavizar(te / 0.25)))
        caixa = pygame.Rect(0, 0, 600, 560)
        caixa.center = (LARGURA // 2, ALTURA // 2 + 10)
        ui.painel(tela, caixa, UI_PAINEL, AMARELO if self.venceu else self.COR, 22, 5)

        # Raios girando atrás do avatar
        if festa:
            raios = pygame.transform.rotate(self._sup_raios(), self.tempo * 25)
            antes = tela.get_clip()
            tela.set_clip(caixa.inflate(-10, -10).clip(antes))
            tela.blit(raios, raios.get_rect(center=(LARGURA // 2, caixa.y + 150)))
            tela.set_clip(antes)

        # Faixa do título (entra com "pop")
        cor_titulo = AMARELO if self.venceu else (255, 150, 150)
        titulo_fim = t(self.titulo_fim)
        tam = ui.tamanho_que_cabe(titulo_fim, caixa.w - 80, (30, 24, 20, 16))
        pop = ui.quicar(min(1.0, te / 0.4))
        sup = ui.texto(titulo_fim, tam, cor_titulo, True, True)
        faixa = pygame.Rect(0, 0, int((sup.get_width() + 70) * pop), int(58 * min(1.0, pop)))
        faixa.center = (LARGURA // 2, caixa.y + 44)
        if faixa.w > 30 and faixa.h > 10:
            ui.painel(tela, faixa, ui.misturar(UI_PAINEL, cor_titulo, 0.22), cor_titulo,
                      16, 3, sombra=True)
        if pop > 0.5:
            tela.blit(sup, sup.get_rect(center=(faixa.centerx, faixa.centery + 1)))

        self._desenhar_avatar_fim(tela, caixa)

        # Moedas ganhas (contando para cima e dando um "pop" no final)
        if self.moedas_ganhas > 0:
            total = self.moedas_ganhas
            duracao = max(0.5, min(1.4, 0.4 + total * 0.02))
            mostrar = max(1, min(total, int(round(total * ui.sair_rapido(te / duracao)))))
            brilho = max(0.0, 1.0 - (te - duracao) / 0.35) if te >= duracao else 0.0
            pilula = pygame.Rect(0, 0, 136, 48).inflate(int(14 * brilho), int(8 * brilho))
            pilula.center = (caixa.right - 110, caixa.y + 130)
            ui.desenhar_texto(tela, t("MOEDAS"), (pilula.centerx, pilula.y - 8), 10,
                              UI_TEXTO_SUAVE, "midbottom")
            ui.sombra_suave(tela, pilula, pilula.h // 2, 4, 80)
            ui.painel(tela, pilula, UI_MOEDA_FUNDO, ui.misturar(AMARELO, BRANCO, brilho * 0.6),
                      pilula.h // 2, 3, sombra=False)
            ui.moeda(tela, (pilula.x + 28, pilula.centery), 15 + int(3 * brilho),
                     giro=abs(math.cos(self.tempo * 2.5)))
            ui.desenhar_texto(tela, f"+{mostrar}", (pilula.x + 52, pilula.centery), 18,
                              ui.misturar(AMARELO, BRANCO, brilho * 0.7), "midleft", True, True)
            if brilho > 0:
                ui.estrela(tela, (pilula.right - 8, pilula.y + 4), 4 + 8 * brilho,
                           (255, 252, 220), brilho * 3)
            for k, linha in enumerate(getattr(self, "detalhe_moedas", [])[:4]):
                ui.desenhar_texto(tela, linha, (pilula.centerx, pilula.bottom + 8 + k * 13), 8,
                                  UI_TEXTO_SUAVE, "midtop")
        self._desenhar_xp_fim(tela, caixa)

        y = caixa.y + 230
        for linha in self.linhas_fim:
            ui.desenhar_texto(tela, t(linha), (LARGURA // 2, y), 16, UI_TEXTO, "midtop")
            y += 30

        if self.novo_recorde:
            # Pulsa suave em vez de piscar
            k = (math.sin(self.tempo * 6) + 1) / 2
            ui.desenhar_texto(tela, t("★ NOVO RECORDE! ★"), (LARGURA // 2, y + 4), 18,
                              ui.misturar(AMARELO, BRANCO, k * 0.5), "midtop", True, True)
        else:
            rec = self.recorde()
            if rec is not None:
                ui.desenhar_texto(tela, t("RECORDE: {n}", n=self.formatar(rec)), (LARGURA // 2, y + 4),
                                  14, UI_TEXTO_SUAVE, "midtop")
        falta = getattr(self, "falta_medalha", "")
        if falta:
            y += 26
            ui.desenhar_texto(tela, falta, (LARGURA // 2, y + 4), 10, (255, 200, 120), "midtop")

        # Posiciona o menu logo abaixo do texto
        base = max(y + 50, caixa.bottom - len(self.menu_fim.botoes) * 66 - 10)
        for i, b in enumerate(self.menu_fim.botoes):
            b.rect.midtop = (LARGURA // 2, base + i * 66)
        self.menu_fim.desenhar(tela)

        self._confete_fim.desenhar(tela)


# Fundos guardados em cache podem ter texto (ex.: placas): refaz ao trocar o idioma.
from core import idioma as _idioma  # noqa: E402
_idioma.ao_mudar(lambda _i: MiniJogo._fundos.clear())
