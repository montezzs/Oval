import math

import pygame

from settings import *
from core import codigo, progresso, ui
from core.cena import Cena, tecla_voltar

# ============================================================
# AMIGOS (pela pausa da casa)
# ============================================================
# Em cima: o CÓDIGO DO SEU OVO (C copia). Embaixo: cole (CTRL+V)
# ou digite o código de um amigo e aperte ENTER. Cada amigo mostra
# o ovo dele e os recordes que ele desafia você a bater.


def _copiar(texto):
    try:
        if not pygame.scrap.get_init():
            pygame.scrap.init()
        pygame.scrap.put_text(texto)
        return True
    except (pygame.error, AttributeError):
        return False


def _colar():
    try:
        if not pygame.scrap.get_init():
            pygame.scrap.init()
        return pygame.scrap.get_text() or ""
    except (pygame.error, AttributeError):
        return ""


class CenaAmigos(Cena):

    def __init__(self, app, casa, pausa):
        super().__init__(app)
        self.casa = casa
        self.pausa = pausa
        self.tempo = 0.0
        self.meu = codigo.gerar(app.save)
        self.digitado = ""
        self.aviso = ""
        self.tempo_aviso = 0.0
        self._amigos = None
        self.botao_copiar = ui.Botao((0, 0, 220, 44), "COPIAR (C)", 12)
        self.botao_copiar.rect.topright = (LARGURA - 56, 64)
        self.botao_voltar = ui.Botao((0, 0, 200, 46), "VOLTAR", 14)
        self.botao_voltar.rect.midbottom = (LARGURA // 2, ALTURA - 12)
        # O código também fica num arquivo (para quem não consegue copiar)
        try:
            with open(caminho_dados("meu_codigo_oval.txt"), "w", encoding="utf-8") as f:
                f.write(self.meu + "\n")
        except OSError:
            pass

    def entrar(self):
        super().entrar()
        pygame.key.start_text_input()

    def sair(self):
        pygame.key.stop_text_input()

    def _avisar(self, texto):
        self.aviso = texto
        self.tempo_aviso = 3.0

    def _lista(self):
        if self._amigos is None:
            self._amigos = [(d, codigo.jogador_do_amigo(d)) for _, d in codigo.amigos(self.app.config)]
        return self._amigos

    def _adicionar(self):
        res = codigo.adicionar(self.app.config, self.digitado, self.meu)
        msgs = {"ok": "AMIGO ADICIONADO!", "invalido": "CÓDIGO INVÁLIDO :(", "repetido": "ESSE AMIGO JÁ ESTÁ NA LISTA",
                "eu": "ESSE É O SEU PRÓPRIO CÓDIGO!", "cheio": f"MÁXIMO DE {codigo.MAX_AMIGOS} AMIGOS"}
        self._avisar(msgs[res])
        if res == "ok":
            self.som("vencer")
            self.digitado = ""
            self._amigos = None
            progresso.definir(self.app, "amigos", len(self.app.config["amigos"]))
        else:
            self.som("erro")

    def evento(self, e):
        if tecla_voltar(e) or self.botao_voltar.evento(e):
            self.som("voltar")
            self.app.trocar(self.pausa, fade=False)
            return
        if self.botao_copiar.evento(e):
            self._copiar_meu()
            return
        if e.type == pygame.KEYDOWN:
            ctrl = e.mod & pygame.KMOD_CTRL
            if ctrl and e.key == pygame.K_v:
                self.digitado = _colar().strip()[:200]
                self.som("clique")
            elif ctrl and e.key == pygame.K_c or (e.key == pygame.K_c and not self.digitado):
                self._copiar_meu()
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and self.digitado:
                self._adicionar()
            elif e.key == pygame.K_BACKSPACE:
                self.digitado = self.digitado[:-1]
        elif e.type == pygame.TEXTINPUT:
            if not (pygame.key.get_mods() & pygame.KMOD_CTRL):
                texto = "".join(ch for ch in e.text.upper() if ch.isalnum() or ch == "-")
                if texto and not (texto == "C" and not self.digitado):
                    self.digitado = (self.digitado + texto)[:200]

    def _copiar_meu(self):
        if _copiar(self.meu):
            self._avisar("CÓDIGO COPIADO! MANDE PARA UM AMIGO.")
        else:
            self._avisar("NÃO DEU PARA COPIAR: VEJA meu_codigo_oval.txt")
        self.som("selecionar")

    def atualizar(self, dt):
        self.tempo += dt
        self.tempo_aviso = max(0.0, self.tempo_aviso - dt)
        self.casa.atualizar(dt)
        self.botao_copiar.atualizar(dt)
        self.botao_voltar.selecionado = True
        self.botao_voltar.atualizar(dt)

    # --------------------------------------------------------

    def desenhar(self, tela):
        self.casa.desenhar(tela)
        ui.veu(tela, 200)
        caixa = pygame.Rect(30, 14, LARGURA - 60, ALTURA - 84)
        ui.painel(tela, caixa, (30, 34, 60), (120, 220, 255), 20, 4)
        ui.desenhar_texto(tela, "AMIGOS", (LARGURA // 2, caixa.y + 16), 24, AMARELO, "midtop")

        # Meu código
        ui.desenhar_texto(tela, "CÓDIGO DO SEU OVO:", (caixa.x + 30, 70), 10, (180, 220, 255), "topleft")
        linhas = ui.quebrar_linhas(self.meu.replace("-", " "), 10, 640)
        for i, l in enumerate(linhas[:4]):
            ui.desenhar_texto(tela, l, (caixa.x + 30, 92 + i * 18), 10, BRANCO, "topleft")
        self.botao_copiar.desenhar(tela)

        # Campo do amigo
        campo = pygame.Rect(caixa.x + 30, 176, caixa.w - 60, 40)
        pygame.draw.rect(tela, (20, 24, 40), campo, border_radius=10)
        pygame.draw.rect(tela, AMARELO, campo, 2, border_radius=10)
        texto = self.digitado[-52:] or "COLE O CÓDIGO DE UM AMIGO (CTRL+V) E APERTE ENTER"
        cursor = "_" if self.digitado and int(self.tempo * 2) % 2 == 0 else ""
        ui.desenhar_texto(tela, texto + cursor, (campo.x + 12, campo.centery), 10,
                          BRANCO if self.digitado else (130, 130, 160), "midleft")
        if self.tempo_aviso > 0:
            ui.desenhar_texto(tela, self.aviso, (LARGURA // 2, campo.bottom + 8), 10, AMARELO, "midtop")

        # Lista de amigos
        lista = self._lista()
        if not lista:
            ui.desenhar_texto(tela, "NENHUM AMIGO AINDA. TROQUE CÓDIGOS E DESAFIE RECORDES!",
                              (LARGURA // 2, 340), 10, (180, 180, 210), "midtop")
        from jogos import JOGOS
        titulos = {j.ID: (j.TITULO_CURTO or j.TITULO) for j in JOGOS}
        formatos = {j.ID: j.formatar for j in JOGOS}
        for i, (d, jog) in enumerate(lista[:8]):
            col, lin = i % 2, i // 2
            r = pygame.Rect(caixa.x + 20 + col * ((caixa.w - 50) // 2 + 10), 244 + lin * 92,
                            (caixa.w - 50) // 2, 84)
            pygame.draw.rect(tela, (44, 48, 80), r, border_radius=12)
            pygame.draw.rect(tela, (90, 100, 150), r, 2, border_radius=12)
            balanco = math.sin(self.tempo * 3 + i) * 3
            jog.desenhar(tela, (r.x + 40, r.centery + balanco), 50)
            ui.desenhar_texto(tela, f"{d.get('n', 'AMIGO')}  •  NV {d.get('l', 1)}", (r.x + 80, r.y + 8), 10,
                              AMARELO, "topleft")
            for k, (jid, (valor, _)) in enumerate(list(d.get("r", {}).items())[:3]):
                fmt = formatos.get(jid, str)
                ui.desenhar_texto(tela, f"DUVIDO: {fmt(valor)} NO {titulos.get(jid, jid).upper()}",
                                  (r.x + 80, r.y + 28 + k * 16), 8, BRANCO, "topleft")

        self.botao_voltar.desenhar(tela)
