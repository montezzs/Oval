import math
import random

import pygame

from settings import *
from core import ceu, fachada, ui
from core import fachada_desenho as fd
from core.cena import Cena
from core.idioma import t
from core.jogador import Jogador
from cenas.casa_extras.clima import Clima, VEUS
from cenas.rua_comum import carregar_perfis

# ============================================================
# TELA INICIAL
# ============================================================
# Aparece sempre que o jogo abre (menos na 1ª vez). Céu pela hora
# real, as casas da RUA DOS OVOS no horizonte e os ovos do jogador
# desfilando pela grama.
#   JOGAR  -> vizinhança
#   OPÇÕES -> volume, sons, tamanho da tela, sempre dia
#   SAIR   -> fecha o jogo (ESC não faz nada aqui, de propósito)

HORIZONTE = 590
X_CASAS = [180, 346, 512, 678, 844]
Y_DESFILE = 690


class CenaTitulo(Cena):

    musica = "abertura"

    def __init__(self, app):
        super().__init__(app)
        self.tempo = 0.0
        self.clima = Clima(app.config)
        self.ceu = ceu.Ceu(altura_estrelas=HORIZONTE - 60)
        self.nuvens = ceu.Nuvens(5, 60, 200, semente=3)
        self._chao = None
        self._chave_chao = None

        self.menu = ui.Menu(["JOGAR", "OPÇÕES", "SAIR"], LARGURA // 2, 290)
        jogar, opcoes, sair = self.menu.botoes
        jogar.rect = pygame.Rect(362, 290, 300, 76)
        jogar.tamanho = 28
        jogar.cor, jogar.cor_hover = (70, 170, 90), (90, 200, 110)
        opcoes.rect = pygame.Rect(392, 386, 240, 52)
        opcoes.tamanho = 16
        sair.rect = pygame.Rect(392, 450, 240, 52)
        sair.tamanho = 16
        sair.cor_hover = (170, 70, 70)

        self._montar_desfile()

    # --------------------------------------------------------

    def _montar_desfile(self):
        self.perfis = carregar_perfis()
        self.desfile = []
        ocupados = [p for p in self.perfis if p.ocupado]
        if ocupados:
            for i, p in enumerate(ocupados):
                self.desfile.append(dict(jogador=p.jogador, nome=p.nome, pet=p.save["pet"],
                                     aparencia=None, x=-100.0 - i * 150, pulo=0.0, balao=0.0))
        else:
            # Ninguém na rua: desfila a família de ovos (sem cabelo)
            from core import assets
            from core.save import Save
            base = Jogador(Save())
            for i in range(min(4, len(assets.OVOS))):
                self.desfile.append(dict(jogador=base, nome="", pet="", aparencia=(i, 0, 0, 0),
                                         x=-100.0 - i * 150, pulo=0.0, balao=0.0))
        # Ovos dos AMIGOS (códigos colados em AMIGOS) desfilam junto
        from core import codigo
        for _, d in codigo.amigos(self.app.config)[:4]:
            try:
                self.desfile.append(dict(jogador=codigo.jogador_do_amigo(d), nome=d.get("n", "AMIGO"),
                                         pet=d.get("p", "") if isinstance(d.get("p"), str) else "",
                                         aparencia=None, x=0.0, pulo=0.0, balao=0.0))
            except Exception:
                pass
        # Espalha pela tela já no começo
        n = len(self.desfile)
        for i, d in enumerate(self.desfile):
            d["x"] = 120 + i * (LARGURA - 160) / max(1, n)

    def entrar(self):
        self.app.descarregar_ovo()
        super().entrar()

    # --------------------------------------------------------

    def _escolher(self, i):
        rotulo = self.menu.botoes[i].rotulo
        if rotulo == "JOGAR":
            from cenas.vizinhanca import CenaVizinhanca
            self.som("selecionar")
            self.app.trocar(CenaVizinhanca(self.app))
        elif rotulo == "OPÇÕES":
            from cenas.pausa import CenaOpcoes
            self.som("selecionar")
            self.app.trocar(CenaOpcoes(self.app, self, self), fade=False)
        elif rotulo == "SAIR":
            self.app.config.salvar()
            self.app.sair()

    def evento(self, e):
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            return
        escolha = self.menu.evento(e)
        if escolha is not None:
            self._escolher(escolha)
            return
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for d in self.desfile:
                if self._rect_ovo(d).collidepoint(e.pos):
                    d["pulo"] = 1.0
                    d["balao"] = 1.2
                    self.som("boing")
                    return

    def _rect_ovo(self, d):
        return pygame.Rect(d["x"] - 26, Y_DESFILE - 70, 52, 70)

    def atualizar(self, dt):
        self.tempo += dt
        self.clima.atualizar(dt)
        self.nuvens.atualizar(dt, self.clima.vento)
        self.menu.atualizar(dt)
        pulsa = 1 + 0.03 * math.sin(self.tempo * 4)
        jogar = self.menu.botoes[0]
        jogar.rect = pygame.Rect(0, 0, round(300 * pulsa), round(76 * pulsa))
        jogar.rect.center = (512, 328)
        for d in self.desfile:
            d["x"] += 50 * dt
            if d["x"] > LARGURA + 90:
                d["x"] -= LARGURA + 180
            d["pulo"] = max(0.0, d["pulo"] - dt * 1.6)
            d["balao"] = max(0.0, d["balao"] - dt)

    # --------------------------------------------------------

    def _desenhar_chao(self):
        fase = self.clima.fase
        chave = (fase, self.clima.tipo)
        if self._chave_chao == chave:
            return self._chao
        sup = pygame.Surface((LARGURA, ALTURA - 520), pygame.SRCALPHA)
        oy = 520
        # Colinas
        for cor, base, amp, fase_s in (((130, 195, 115), 548, 18, 0.0), ((150, 210, 125), 575, 12, 1.7)):
            pts = [(0, ALTURA - oy)]
            for x in range(0, LARGURA + 17, 16):
                pts.append((x, base - oy + amp * math.sin(x / LARGURA * 4 * math.pi + fase_s)))
            pts.append((LARGURA, ALTURA - oy))
            pygame.draw.polygon(sup, cor, pts)
        pygame.draw.rect(sup, (110, 200, 90), (0, HORIZONTE - oy, LARGURA, ALTURA - HORIZONTE))
        rnd = random.Random(8)
        for _ in range(60):
            x, y = rnd.randrange(LARGURA), rnd.randrange(HORIZONTE + 6, ALTURA - 4) - oy
            pygame.draw.line(sup, (90, 175, 75), (x, y), (x - 3, y - 6), 2)
            pygame.draw.line(sup, (90, 175, 75), (x, y), (x + 3, y - 6), 2)
        self._chao, self._chave_chao = sup, chave
        return sup

    def desenhar(self, tela):
        fase = self.clima.fase
        nublado = self.clima.tipo != "sol"
        noite = fase == "noite"
        tela.blit(ceu.gradiente(fase, LARGURA, HORIZONTE, nublado), (0, 0))
        self.ceu.desenhar(tela, fase, self.tempo, sol=(140, 110), lua=(880, 90), nublado=nublado)
        self.nuvens.desenhar(tela, cinza=nublado or noite)
        tela.blit(self._desenhar_chao(), (0, 520))

        # Casas da rua no horizonte
        for p, x in zip(self.perfis, X_CASAS):
            if p.ocupado:
                fd.desenhar_casa(tela, (x, HORIZONTE), 0.42, p.casa, p.cor, noite, self.tempo,
                                 dormindo=p.dormindo, vento=self.clima.vento)
            else:
                fd.desenhar_lote_vazio(tela, (x, HORIZONTE), 0.42, self.tempo,
                                       em_obras=p.estado == "corrompido")

        # Desfile
        for d in self.desfile:
            pulo = math.sin(d["pulo"] * math.pi) * 40 if d["pulo"] > 0 else 0
            salto = 18 * abs(math.sin(4 * self.tempo + d["x"] * 0.01)) + pulo
            if d["pet"]:
                self.app.desenhar_pet_de(tela, d["pet"], (d["x"] - 48, Y_DESFILE), 0.5)
            d["jogador"].desenhar(tela, (d["x"], Y_DESFILE - 28 - salto), 56, aparencia=d["aparencia"])

        # Véu da hora do dia sobre o chão e as luzes por cima
        veu = VEUS.get(fase)
        if veu:
            self._veu_chao(tela, veu)
            if noite:
                for p, x in zip(self.perfis, X_CASAS):
                    if p.ocupado:
                        fd.desenhar_luzes(tela, (x, HORIZONTE), 0.42, p.casa, p.cor, self.tempo,
                                          dormindo=p.dormindo)

        for d in self.desfile:
            if d["balao"] > 0 and d["nome"]:
                sup = ui.texto(d["nome"].upper() + "!", 10, (40, 30, 20), sombra=False)
                caixa = sup.get_rect(midbottom=(d["x"], Y_DESFILE - 100)).inflate(16, 10)
                caixa.clamp_ip(pygame.Rect(4, 0, LARGURA - 8, ALTURA))
                pygame.draw.rect(tela, (255, 255, 255), caixa, border_radius=8)
                tela.blit(sup, sup.get_rect(center=caixa.center))

        self._desenhar_logo(tela)
        self.menu.desenhar(tela)
        from cenas.casa_extras.eventos_casa import desenhar_faixa
        desenhar_faixa(tela, 0)
        ui.desenhar_texto(tela, t("ENTER = JOGAR"), (16, 700), 8, (230, 230, 240), "bottomleft")
        ui.desenhar_texto(tela, "V" + VERSAO, (LARGURA - 16, 700), 8, (230, 230, 240), "bottomright")

    def _veu_chao(self, tela, veu):
        cor, alpha = veu
        chave = (cor, alpha)
        if getattr(self, "_veu_chave", None) != chave:
            s = pygame.Surface((LARGURA, ALTURA - 520))
            s.fill(cor)
            s.set_alpha(alpha)
            self._veu_sup, self._veu_chave = s, chave
        tela.blit(self._veu_sup, (0, 520))

    # --------------------------------------------------------

    def _desenhar_logo(self, tela):
        letras = ["O", "V", "A", "L"]
        tam = 72
        larguras = [64 if l == "O" else ui.texto(l, tam).get_width() for l in letras]
        esp = 14
        total = sum(larguras) + esp * (len(letras) - 1)
        x = LARGURA // 2 - total // 2
        piscar = (self.tempo % 4) < 0.12
        for i, (l, w) in enumerate(zip(letras, larguras)):
            dy = 6 * math.sin(2 * self.tempo + i * 0.6)
            cx, cy = x + w // 2, 150 + dy
            if l == "O":
                self._ovo_logo(tela, (cx, cy), piscar)
            else:
                ui.desenhar_texto(tela, l, (cx + 6, cy + 6), tam, (0, 0, 0), "center", False)
                for ox, oy in ((-4, 0), (4, 0), (0, -4), (0, 4), (-3, -3), (3, 3), (-3, 3), (3, -3)):
                    ui.desenhar_texto(tela, l, (cx + ox, cy + oy), tam, (120, 60, 20), "center", False)
                ui.desenhar_texto(tela, l, (cx, cy), tam, AMARELO, "center", False)
            x += w + esp
        sub = ui.texto(t("A VIZINHANÇA DOS OVOS"), 14, BRANCO)
        caixa = sub.get_rect(midtop=(LARGURA // 2, 236)).inflate(24, 14)
        fundo = pygame.Surface(caixa.size, pygame.SRCALPHA)
        pygame.draw.rect(fundo, (20, 24, 40, 170), fundo.get_rect(), border_radius=10)
        tela.blit(fundo, caixa)
        tela.blit(sub, sub.get_rect(center=caixa.center))

    @staticmethod
    def _ovo_logo(tela, centro, piscar):
        cx, cy = centro
        cor = (168, 230, 29)
        r = pygame.Rect(0, 0, 60, 74)
        r.center = (cx, cy)
        pygame.draw.ellipse(tela, (0, 0, 0), r.move(6, 6))
        pygame.draw.ellipse(tela, cor, r)
        pygame.draw.ellipse(tela, ui.clarear(cor, 50), (r.x + 12, r.y + 10, 14, 20))
        pygame.draw.ellipse(tela, (120, 60, 20), r, 4)
        for dx in (-10, 10):
            if piscar:
                pygame.draw.line(tela, (20, 20, 20), (cx + dx - 4, cy - 2), (cx + dx + 4, cy - 2), 3)
            else:
                pygame.draw.circle(tela, (20, 20, 20), (cx + dx, cy - 2), 4)
        pygame.draw.arc(tela, (20, 20, 20), (cx - 10, cy + 2, 20, 14), math.pi * 1.1, math.pi * 1.9, 3)
