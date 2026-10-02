import math
import random

import pygame

from settings import *
from core.idioma import t
from core import ceu, perfis, ui
from core import fachada_desenho as fd
from core.cena import Cena, tecla_confirmar, tecla_voltar
from cenas.rua_comum import carregar_perfis

# ============================================================
# MUDANÇA (RECOMEÇAR DO ZERO)
# ============================================================
# Os saves são APAGADOS logo que a cena abre (se o jogo fechar no
# meio da animação, o recomeço já está garantido). A animação usa
# só a cópia dos perfis que ficou na memória:
#   1. o caminhão de mudança chega e abre a porta
#   2. cada ovo sai da sua casa com uma caixa e sobe na rampa
#      (a casa vira um lote vazio e o pet vai atrás)
#   3. buzina, o caminhão vai embora soltando fumaça
#   4. "ATÉ LOGO!" -> o jogo começa do zero (nome do 1º ovo)
# ENTER / ESC pulam direto para o final.

X_CASAS = [180, 346, 512, 678, 844]
HORIZONTE = 470          # base das casas
ESCALA_CASA = 0.46
Y_CALCADA = 492          # os ovos andam por aqui (atrás do caminhão)
Y_RUA = 640              # chão do caminhão
X_PARADO = 400           # onde o caminhão para (traseira)
X_RAMPA = X_PARADO - 72

VEL_OVO = 240
T_CHEGADA = 2.2
T_PORTA = 0.5
INTERVALO_OVOS = 1.1

LARG_BAU = 320           # baú do caminhão
ALT_BAU = 150
LARG_CABINE = 104


def _ease_out(t):
    return 1 - (1 - t) ** 3


class OvoMudando:
    """Um ovo indo da porta de casa até dentro do caminhão."""

    def __init__(self, perfil, x_casa, atraso):
        self.perfil = perfil
        self.x_casa = x_casa
        self.atraso = atraso
        # Caminho: porta -> calçada -> ponta da rampa -> dentro do baú
        self.pontos = [(x_casa, HORIZONTE - 6), (x_casa, Y_CALCADA), (X_RAMPA - 14, Y_CALCADA),
                       (X_RAMPA - 14, Y_RUA), (X_PARADO + 26, Y_RUA - 40)]
        self.trecho = 0
        self.x, self.y = self.pontos[0]
        self.saiu = False            # já saiu de casa (a casa vira lote)
        self.dentro = False          # já entrou no caminhão
        self.passo = 0.0
        self.balao = 0.0

    def atualizar(self, dt, tempo):
        if self.dentro or tempo < self.atraso:
            return None
        evento = None
        if not self.saiu:
            self.saiu = True
            self.balao = 1.6
            evento = "saiu"
        self.balao = max(0.0, self.balao - dt)
        self.passo += dt * 11
        anda = VEL_OVO * dt
        while anda > 0 and self.trecho < len(self.pontos) - 1:
            alvo = self.pontos[self.trecho + 1]
            dx, dy = alvo[0] - self.x, alvo[1] - self.y
            d = math.hypot(dx, dy)
            if d <= anda:
                self.x, self.y = alvo
                anda -= d
                self.trecho += 1
            else:
                self.x += dx / d * anda
                self.y += dy / d * anda
                anda = 0
        if self.trecho >= len(self.pontos) - 1:
            self.dentro = True
            evento = "entrou"
        return evento

    @property
    def olhando_esq(self):
        if self.trecho + 1 >= len(self.pontos):
            return False
        return self.pontos[self.trecho + 1][0] < self.x - 1


class CenaMudanca(Cena):

    musica = "maos_a_obra"

    def __init__(self, app):
        super().__init__(app)
        self.tempo = 0.0
        self.particulas = ui.Particulas()
        self.nuvens = ceu.Nuvens(4, 40, 180, semente=21)
        self.ceu = ceu.Ceu(altura_estrelas=HORIZONTE - 60)

        # Guarda a rua na memória e APAGA TUDO do disco. Daqui até o
        # recomeço as preferências ficam só na memória (arquivo=None):
        # nada pode recriar a pasta saves/ (ex.: a jukebox anotando a
        # música que acabou de tocar).
        from core.save import Config
        self.perfis = carregar_perfis()
        app.descarregar_ovo()
        app.config = Config(dict(app.config.dados), arquivo=None)
        app.audio.save = app.config
        self.apagou = perfis.apagar_tudo()

        self.ovos = []
        k = 0
        for p, x in zip(self.perfis, X_CASAS):
            if p.ocupado:
                self.ovos.append(OvoMudando(p, x, T_CHEGADA + T_PORTA + 0.3 + k * INTERVALO_OVOS))
                k += 1
        self.lotes_vazios = {p.slot for p in self.perfis if not p.ocupado}

        self.fase = "chegando"
        self.tempo_fase = 0.0
        self.caminhao_x = -LARG_BAU - LARG_CABINE - 60
        self.vel_saida = 0.0
        self.porta = 0.0             # 0 = fechada, 1 = aberta
        self.carregados = 0
        self.giro_rodas = 0.0
        self.buzina = 0.0
        self._chao = None

    # --------------------------------------------------------

    def _mudar(self, fase):
        self.fase = fase
        self.tempo_fase = 0.0

    def _pular_para_o_fim(self):
        for o in self.ovos:
            o.saiu = o.dentro = True
            self.lotes_vazios.add(o.perfil.slot)
        self.carregados = len(self.ovos)
        self.caminhao_x = LARGURA + 200
        self._mudar("fim")

    def _recomecar(self):
        """Tudo do zero: preferências novas e o 1º ovo (como na 1ª vez)."""
        from cenas.nome import CenaNome
        from jogos.base import MiniJogo
        app = self.app
        app.save = app.jogador = app.necessidades = None
        app.slot = -1
        app.jogou_partida = False
        app.config = perfis.carregar_config()
        app.config["janela"] = list(app.janela.tamanho)     # a janela fica como está
        app.config["tutorial"] = 0                          # começa com o tutorial
        app.audio.save = app.config
        app.audio._aplicar_volume()
        MiniJogo._fundos.clear()
        app.iniciar_rascunho(0)
        app.trocar(CenaNome(app, "inicial", app._depois_do_nome))

    def evento(self, e):
        if self.fase == "fim":
            if self.tempo_fase > 1.2 and (tecla_confirmar(e) or tecla_voltar(e) or
                                          (e.type == pygame.MOUSEBUTTONDOWN and e.button == 1)):
                self.som("selecionar")
                self._recomecar()
            return
        if tecla_voltar(e) or tecla_confirmar(e):
            self.som("clique")
            self._pular_para_o_fim()

    # --------------------------------------------------------

    def atualizar(self, dt):
        self.tempo += dt
        self.tempo_fase += dt
        self.nuvens.atualizar(dt, 0.3)
        self.particulas.atualizar(dt)
        self.buzina = max(0.0, self.buzina - dt)
        x_antes = self.caminhao_x

        if self.fase == "chegando":
            k = min(1.0, self.tempo_fase / T_CHEGADA)
            inicio = -LARG_BAU - LARG_CABINE - 60
            self.caminhao_x = inicio + (X_PARADO - inicio) * _ease_out(k)
            if k >= 1:
                self.som("virar")
                self._buzinar()
                self._mudar("abrindo")

        elif self.fase == "abrindo":
            self.porta = min(1.0, self.tempo_fase / T_PORTA)
            if self.porta >= 1:
                self._mudar("carregando")

        elif self.fase == "carregando":
            for o in self.ovos:
                ev = o.atualizar(dt, self.tempo)
                if ev == "saiu":
                    self.lotes_vazios.add(o.perfil.slot)
                    self.particulas.explodir((o.x_casa, HORIZONTE - 40),
                                             [(230, 220, 200), BRANCO, (200, 180, 150)], 18, 160, 0.7,
                                             (3, 7), 0)
                    self.som("boing", 0.6)
                elif ev == "entrou":
                    self.carregados += 1
                    self.som("pulo", 0.7)
                    self.particulas.explodir((X_PARADO + 30, Y_RUA - 60), [AMARELO, BRANCO], 10, 160,
                                             0.5, (2, 4), 300)
            if all(o.dentro for o in self.ovos) and self.tempo_fase > 0.8:
                self._mudar("fechando")

        elif self.fase == "fechando":
            self.porta = max(0.0, 1 - self.tempo_fase / T_PORTA)
            if self.porta <= 0 and self.tempo_fase > T_PORTA + 0.4:
                self._buzinar()
                self._mudar("saindo")

        elif self.fase == "saindo":
            self.vel_saida = min(900.0, self.vel_saida + 420 * dt)
            self.caminhao_x += self.vel_saida * dt
            # Fumacinha do escapamento
            if random.random() < dt * 30:
                self.particulas.explodir((self.caminhao_x - 6, Y_RUA - 22),
                                         [(170, 170, 180), (200, 200, 210), (140, 140, 150)], 2, 60, 0.9,
                                         (5, 10), -40)
            if self.caminhao_x > LARGURA + 60:
                self._mudar("fim")
                self.som("vencer", 0.6)

        self.giro_rodas += (self.caminhao_x - x_antes) / 24

    def _buzinar(self):
        self.buzina = 0.5
        self.som("ponto")

    # --------------------------------------------------------

    def _desenhar_cenario(self):
        if self._chao is not None:
            return self._chao
        sup = ceu.gradiente("dia", LARGURA, ALTURA, False).copy()
        # Grama
        pygame.draw.rect(sup, (120, 200, 100), (0, HORIZONTE - 20, LARGURA, ALTURA))
        rnd = random.Random(3)
        for _ in range(70):
            x, y = rnd.randrange(LARGURA), rnd.randrange(HORIZONTE, ALTURA - 4)
            pygame.draw.line(sup, (95, 175, 80), (x, y), (x - 3, y - 6), 2)
            pygame.draw.line(sup, (95, 175, 80), (x, y), (x + 3, y - 6), 2)
        # Calçada e rua
        pygame.draw.rect(sup, (205, 200, 190), (0, Y_CALCADA - 12, LARGURA, 36))
        for x in range(0, LARGURA, 48):
            pygame.draw.line(sup, (180, 175, 165), (x, Y_CALCADA - 12), (x, Y_CALCADA + 23), 2)
        pygame.draw.rect(sup, (70, 72, 84), (0, Y_CALCADA + 24, LARGURA, Y_RUA - Y_CALCADA + 10))
        pygame.draw.rect(sup, (90, 92, 104), (0, Y_CALCADA + 24, LARGURA, 6))
        for x in range(10, LARGURA, 90):
            pygame.draw.rect(sup, (240, 230, 150), (x, (Y_CALCADA + Y_RUA) // 2 + 20, 48, 6), border_radius=3)
        self._chao = sup.convert()
        return self._chao

    def desenhar(self, tela):
        tela.blit(self._desenhar_cenario(), (0, 0))
        self.ceu.desenhar(tela, "dia", self.tempo, sol=(140, 90), lua=(880, 90))
        self.nuvens.desenhar(tela)

        # Casas (quem já saiu deixa um lote vazio)
        for p, x in zip(self.perfis, X_CASAS):
            if p.slot in self.lotes_vazios or not p.ocupado:
                fd.desenhar_lote_vazio(tela, (x, HORIZONTE), ESCALA_CASA, self.tempo)
            else:
                fd.desenhar_casa(tela, (x, HORIZONTE), ESCALA_CASA, p.casa, p.cor, False, self.tempo)

        # Ovos na calçada (atrás do caminhão)
        for o in self.ovos:
            if o.saiu and not o.dentro and o.y < Y_CALCADA + 30:
                self._desenhar_ovo(tela, o)

        self._desenhar_caminhao(tela)

        # Ovos na rampa (na frente)
        for o in self.ovos:
            if o.saiu and not o.dentro and o.y >= Y_CALCADA + 30:
                self._desenhar_ovo(tela, o)

        self.particulas.desenhar(tela)

        for o in self.ovos:
            if o.balao > 0 and o.perfil.nome:
                sup = ui.texto(t("TCHAU, CASA!"), 10, (40, 30, 20), sombra=False)
                caixa = sup.get_rect(midbottom=(o.x, o.y - 70)).inflate(16, 10)
                caixa.clamp_ip(pygame.Rect(4, 0, LARGURA - 8, ALTURA))
                pygame.draw.rect(tela, BRANCO, caixa, border_radius=8)
                tela.blit(sup, sup.get_rect(center=caixa.center))

        if self.buzina > 0 and self.caminhao_x > -LARG_BAU:
            x = self.caminhao_x + LARG_BAU + LARG_CABINE + 20
            ui.desenhar_texto(tela, t("BI-BI!"), (x, Y_RUA - 150), 14, AMARELO, "center")

        if self.fase == "fim":
            self._desenhar_fim(tela)
        else:
            ui.desenhar_texto(tela, t("ENTER para pular"), (LARGURA - 14, ALTURA - 12), 8,
                              (240, 240, 250), "bottomright")

    def _desenhar_ovo(self, tela, o):
        p = o.perfil
        pulo = abs(math.sin(o.passo)) * 8
        base_y = o.y - pulo
        if p.save["pet"]:
            lado = 1 if o.olhando_esq else -1
            self.app.desenhar_pet_de(tela, p.save["pet"], (o.x + lado * 46, o.y), 0.45)
        pygame.draw.ellipse(tela, (150, 145, 135) if o.y < Y_CALCADA + 30 else (55, 57, 66),
                            (o.x - 22, o.y - 6, 44, 10))
        p.jogador.desenhar(tela, (o.x, base_y - 26), 50, espelhar=o.olhando_esq)
        # Caixa de papelão nos braços
        caixa = pygame.Rect(0, 0, 34, 24)
        caixa.midtop = (o.x + (-10 if o.olhando_esq else 10), base_y - 26)
        pygame.draw.rect(tela, (200, 150, 90), caixa, border_radius=3)
        pygame.draw.rect(tela, (140, 95, 50), caixa, 2, border_radius=3)
        pygame.draw.line(tela, (230, 200, 140), (caixa.x + 4, caixa.y + 8), (caixa.right - 4, caixa.y + 8), 3)

    def _desenhar_caminhao(self, tela):
        x = int(self.caminhao_x)
        chao = Y_RUA
        bau = pygame.Rect(x, chao - 34 - ALT_BAU, LARG_BAU, ALT_BAU)
        cabine = pygame.Rect(bau.right - 4, chao - 34 - 104, LARG_CABINE, 104)
        balanco = int(math.sin(self.tempo * 18) * 1.5) if self.fase in ("chegando", "saindo") else 0
        bau.y += balanco
        cabine.y += balanco

        # Sombra
        pygame.draw.ellipse(tela, (40, 42, 50), (x - 10, chao - 12, LARG_BAU + LARG_CABINE + 30, 22))

        # Cabine
        pygame.draw.rect(tela, (220, 70, 60), cabine, border_top_right_radius=26, border_radius=8)
        pygame.draw.rect(tela, (140, 40, 36), cabine, 3, border_top_right_radius=26, border_radius=8)
        vidro = pygame.Rect(cabine.x + 40, cabine.y + 12, 52, 40)
        pygame.draw.rect(tela, (170, 220, 250), vidro, border_top_right_radius=18, border_radius=4)
        pygame.draw.line(tela, BRANCO, (vidro.x + 10, vidro.y + 30), (vidro.x + 26, vidro.y + 8), 3)
        pygame.draw.rect(tela, (255, 240, 150), (cabine.right - 12, cabine.bottom - 34, 10, 14),
                         border_radius=3)
        pygame.draw.rect(tela, (90, 90, 100), (cabine.right - 8, cabine.bottom - 12, 14, 8), border_radius=3)

        # Baú
        pygame.draw.rect(tela, (245, 245, 250), bau, border_radius=10)
        pygame.draw.rect(tela, (120, 124, 140), bau, 3, border_radius=10)
        faixa = pygame.Rect(bau.x + 3, bau.y + 92, bau.w - 6, 16)
        pygame.draw.rect(tela, (255, 190, 60), faixa)
        ui.desenhar_texto(tela, t("MUDANÇAS"), (bau.centerx + 30, bau.y + 26), 16, (220, 70, 60), "center",
                          False)
        ui.desenhar_texto(tela, "OVAL", (bau.centerx + 30, bau.y + 60), 24, (60, 90, 180), "center", False)
        ovo = pygame.Rect(0, 0, 26, 32)
        ovo.center = (bau.centerx - 60, bau.y + 58)
        pygame.draw.ellipse(tela, (168, 230, 29), ovo)
        pygame.draw.ellipse(tela, (90, 130, 20), ovo, 2)

        # Traseira: interior escuro com as caixas, porta abrindo e rampa
        if self.porta > 0:
            fundo = pygame.Rect(bau.x + 6, bau.y + 6, 118, bau.h - 12)
            pygame.draw.rect(tela, (50, 44, 40), fundo, border_radius=6)
            for i in range(self.carregados * 2):
                cx = fundo.x + 8 + (i % 3) * 36
                cy = fundo.bottom - 26 - (i // 3) * 22
                if cy > fundo.y:
                    pygame.draw.rect(tela, (200, 150, 90), (cx, cy, 32, 22), border_radius=3)
                    pygame.draw.rect(tela, (140, 95, 50), (cx, cy, 32, 22), 2, border_radius=3)
            # Porta girando para a esquerda
            larg_porta = int(118 * (1 - self.porta))
            if larg_porta > 2:
                pygame.draw.rect(tela, (225, 225, 235), (bau.x, bau.y, larg_porta, bau.h), border_radius=6)
            aberta = int(40 * self.porta)
            pygame.draw.polygon(tela, (215, 215, 225), [(bau.x, bau.y), (bau.x - aberta, bau.y + 10),
                                                        (bau.x - aberta, bau.bottom - 10),
                                                        (bau.x, bau.bottom)])
            pygame.draw.polygon(tela, (120, 124, 140), [(bau.x, bau.y), (bau.x - aberta, bau.y + 10),
                                                        (bau.x - aberta, bau.bottom - 10),
                                                        (bau.x, bau.bottom)], 2)
            # Rampa
            if self.porta >= 1:
                pygame.draw.polygon(tela, (150, 150, 165), [(bau.x + 4, bau.bottom - 4),
                                                            (bau.x + 60, bau.bottom - 4),
                                                            (X_RAMPA + 20, chao), (X_RAMPA - 30, chao)])
                pygame.draw.polygon(tela, (100, 100, 115), [(bau.x + 4, bau.bottom - 4),
                                                            (bau.x + 60, bau.bottom - 4),
                                                            (X_RAMPA + 20, chao), (X_RAMPA - 30, chao)], 2)
        else:
            pygame.draw.line(tela, (150, 154, 170), (bau.x + 118, bau.y + 6), (bau.x + 118, bau.bottom - 6), 2)

        # Chassi e rodas
        pygame.draw.rect(tela, (60, 62, 72), (x, chao - 38, LARG_BAU + LARG_CABINE - 4, 10))
        for rx in (x + 60, x + 250, x + LARG_BAU + 58):
            c = (rx, chao - 20)
            pygame.draw.circle(tela, (30, 30, 36), c, 24)
            pygame.draw.circle(tela, (170, 170, 185), c, 11)
            for k in range(3):
                a = self.giro_rodas + k * math.tau / 3
                pygame.draw.line(tela, (90, 90, 100), c,
                                 (c[0] + math.cos(a) * 10, c[1] + math.sin(a) * 10), 3)

    def _desenhar_fim(self, tela):
        k = min(1.0, self.tempo_fase / 0.5)
        ui.veu(tela, int(150 * k))
        caixa = pygame.Rect(0, 0, 640, 250)
        caixa.center = (LARGURA // 2, ALTURA // 2 - 40)
        ui.painel(tela, caixa, (30, 34, 60), AMARELO, 20, 4)
        ui.desenhar_texto(tela, t("ATÉ LOGO, RUA DOS OVOS!"), (LARGURA // 2, caixa.y + 34), 20, AMARELO,
                          "midtop")
        if self.apagou:
            linhas = ["Todos os saves foram apagados.", "Hora de chocar um ovo novinho!"]
        else:
            linhas = ["Alguns arquivos não puderam ser apagados.", "Feche o jogo e confira a pasta saves/."]
        for i, linha in enumerate(linhas):
            ui.desenhar_texto(tela, t(linha), (LARGURA // 2, caixa.y + 94 + i * 28), 12, BRANCO, "midtop")
        if self.tempo_fase > 1.2 and int(self.tempo * 2) % 2 == 0:
            ui.desenhar_texto(tela, t("APERTE ENTER PARA RECOMEÇAR"), (LARGURA // 2, caixa.bottom - 40), 12,
                              (170, 235, 255), "midtop")
