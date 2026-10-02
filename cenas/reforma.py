import copy
import math

import pygame

from settings import *
from core.idioma import t
from core import ceu, ui
from core import fachada as fc
from core import fachada_desenho as fd
from core.cena import Cena, tecla_voltar
from core.cosmeticos import RARIDADES

# ============================================================
# REFORMA (fachada da casa)
# ============================================================
# Prévia ao vivo à esquerda, peças à direita. Clicar numa peça que
# o ovo ainda não tem só PROVA (aparece na prévia); para ficar com
# ela é preciso COMPRAR com as OVOEDAS deste ovo. Cores são grátis.
#
#   Q / E      troca de aba          ← → ↑ ↓  escolhe
#   TAB        estilo <-> cor (ou esquerda <-> direita no JARDIM)
#   ENTER      usar / comprar        N  ver de dia / de noite
#   ESC        pronto (volta para a rua)

ABAS = [
    # (nome, chave da casa, parte do catálogo, chave da cor, paleta)
    ("PAREDE", "parede", "parede", "cor_parede", fc.PALETA_PAREDE),
    ("TELHADO", "telhado", "telhado", "cor_telhado", fc.PALETA_TELHADO),
    ("PORTA", "porta", "porta", "cor_porta", fc.PALETA_PORTA),
    ("JANELAS", "janela", "janela", None, None),
    ("CERCA", "cerca", "cerca", None, None),
    ("CAMINHO", "caminho", "caminho", None, None),
    ("CORREIO", "correio", "correio", None, None),
    ("JARDIM", "itens", "chao", None, None),
    ("ENFEITE", "itens", "enfeite", None, None),
]

PREVIA = pygame.Rect(16, 76, 560, 568)
PAINEL = pygame.Rect(588, 76, 420, 568)
ANCORA = (296, 560)
ESCALA = 1.8
CARD = (124, 96)
GRADE_X, GRADE_Y = 600, 170
POR_PAGINA = 6


class CenaReforma(Cena):

    musica = "maos_a_obra"

    def __init__(self, app, slot):
        super().__init__(app)
        self.slot = slot
        self.save = app.save
        self.casa = copy.deepcopy(self.save["casa"])
        self.tempo = 0.0
        self.aba = 0
        self.secao = 0                  # 0 = ESTILO, 1 = COR
        self.lado = "esq"               # JARDIM: esq / dir
        self.pagina = 0
        self.foco = 0
        self.foco_cor = 0
        self.noite = False
        self.confirmar = None           # id a comprar (janela SIM/NÃO)
        self.aviso = ""
        self.tempo_aviso = 0.0
        self.pulo = 0.0
        self.particulas = ui.Particulas()
        self.nuvens = ceu.Nuvens(3, 90, 180, largura=PREVIA.right, semente=4, escala=0.8)
        self.ceu = ceu.Ceu(largura=PREVIA.right, altura_estrelas=300)

        self.bt_voltar = pygame.Rect(16, 16, 150, 48)
        self.bt_noite = pygame.Rect(28, 600, 170, 34)
        self.bt_pronto = pygame.Rect(412, 600, 150, 34)
        self.bt_chamine = pygame.Rect(600, 522, 190, 30)
        self.bt_sim = pygame.Rect(0, 0, 150, 50)
        self.bt_nao = pygame.Rect(0, 0, 150, 50)
        self.bt_acao = pygame.Rect(PAINEL.right - 176, 572, 160, 40)
        self.bt_pag_esq = pygame.Rect(600, 526, 40, 30)
        self.bt_pag_dir = pygame.Rect(956, 526, 40, 30)
        self._sincronizar_foco()

    # --------------------------------------------------------
    # DADOS
    # --------------------------------------------------------

    @property
    def dados_aba(self):
        return ABAS[self.aba]

    @property
    def tem_cor(self):
        return self.dados_aba[3] is not None

    def _ids(self):
        nome, chave, parte, _, _ = self.dados_aba
        ids = fc.ids_da_parte(parte)
        ids.sort(key=lambda i: (fc.CATALOGO[i]["preco"], i))
        if parte in ("chao", "enfeite"):
            ids = [""] + ids
        return ids

    def _pp(self):
        """Peças por página: 6 quando a aba tem cores embaixo, senão 9."""
        return POR_PAGINA if self.tem_cor else 9

    def _pagina_ids(self):
        ids = self._ids()
        return ids[self.pagina * self._pp():(self.pagina + 1) * self._pp()]

    def _paginas(self):
        return max(1, math.ceil(len(self._ids()) / self._pp()))

    def _chave_item(self):
        parte = self.dados_aba[2]
        if parte == "chao":
            return self.lado
        if parte == "enfeite":
            return "telhado"
        return None

    def _atual(self):
        """Id da peça aplicada agora (na prévia) nesta aba."""
        nome, chave, parte, _, _ = self.dados_aba
        if chave == "itens":
            return self.casa["itens"].get(self._chave_item(), "")
        return self.casa[chave]

    def possui(self, pid):
        if pid == "":
            return True
        d = fc.CATALOGO.get(pid)
        return d is not None and (d["preco"] == 0 or pid in self.save["inventario"])

    def _aplicar(self, pid):
        nome, chave, parte, _, _ = self.dados_aba
        if chave == "itens":
            self.casa["itens"][self._chave_item()] = pid
        else:
            self.casa[chave] = pid

    def _provando(self):
        """Peças aplicadas que o ovo ainda não comprou."""
        lista = []
        for k in fc.PADRAO_PARTE:
            if not self.possui(self.casa[k]):
                lista.append(self.casa[k])
        for k in ("esq", "dir", "telhado"):
            if not self.possui(self.casa["itens"].get(k, "")):
                lista.append(self.casa["itens"][k])
        return lista

    def _sincronizar_foco(self):
        ids = self._ids()
        atual = self._atual()
        if atual in ids:
            i = ids.index(atual)
            self.pagina = i // self._pp()
            self.foco = i % self._pp()
        else:
            self.pagina = self.foco = 0
        if self.tem_cor:
            self.foco_cor = self.casa[self.dados_aba[3]]

    def _item_foco(self):
        ids = self._pagina_ids()
        return ids[min(self.foco, len(ids) - 1)] if ids else ""

    # --------------------------------------------------------
    # AÇÕES
    # --------------------------------------------------------

    def _trocar_aba(self, d):
        self.aba = (self.aba + d) % len(ABAS)
        self.secao = 0
        self._sincronizar_foco()
        self.som("clique")

    def _escolher(self, pid):
        if pid == self._atual():
            if not self.possui(pid):
                self._pedir_compra(pid)
            return
        self._aplicar(pid)
        self.pulo = 1.0
        self.som("clique")
        self._poof()

    def _poof(self):
        ax, ay = ANCORA
        self.particulas.explodir((ax, ay - 140), [(255, 255, 255), (230, 230, 240)], 10, 160,
                                 vida=0.5, gravidade=-80)

    def _pedir_compra(self, pid):
        if not pid or self.possui(pid):
            return
        preco = fc.CATALOGO[pid]["preco"]
        if self.save["moedas"] < preco:
            self._avisar(t("FALTAM {n} OVOEDAS", n=preco - self.save['moedas']))
            self.som("erro")
            return
        self.confirmar = pid
        self.som("selecionar")

    def _comprar(self):
        pid, self.confirmar = self.confirmar, None
        preco = fc.CATALOGO[pid]["preco"]
        if not self.save.gastar(preco):
            self.som("erro")
            return
        if self.save is self.app.save:
            from core import progresso
            progresso.contar(self.app, "compras")
            progresso.contar(self.app, "moedas_gastas", preco)
        self.save["inventario"].append(pid)
        self.save["casa"] = copy.deepcopy(self.casa)
        self.save.salvar()
        self.som("moeda")
        self.pulo = 1.0
        cores = [AMARELO, (255, 255, 255), fc.cor_parede(self.casa)]
        self.particulas.explodir((ANCORA[0], ANCORA[1] - 160), cores, 40, 340)

    def _acao_foco(self):
        if self.secao == 1 and self.tem_cor:
            self._mudar_cor(self.foco_cor)
            return
        pid = self._item_foco()
        if pid == self._atual() and not self.possui(pid):
            self._pedir_compra(pid)
        else:
            self._escolher(pid)

    def _mudar_cor(self, i):
        chave = self.dados_aba[3]
        if self.casa[chave] != i:
            self.casa[chave] = i
            self.pulo = 1.0
            self._poof()
            self.som("clique")
        self.foco_cor = i

    def _sair(self):
        tirou = False
        for k in fc.PADRAO_PARTE:
            if not self.possui(self.casa[k]):
                self.casa[k] = self.save["casa"][k] if self.possui(self.save["casa"][k]) else fc.PADRAO_PARTE[k]
                tirou = True
        for k in ("esq", "dir", "telhado"):
            if not self.possui(self.casa["itens"].get(k, "")):
                self.casa["itens"][k] = self.save["casa"]["itens"].get(k, "")
                if not self.possui(self.casa["itens"][k]):
                    self.casa["itens"][k] = ""
                tirou = True
        self.save["casa"] = copy.deepcopy(self.casa)
        self.save.salvar()
        from cenas.vizinhanca import CenaVizinhanca
        self.som("voltar")
        viz = CenaVizinhanca(self.app, reformada=self.slot)
        if tirou:
            viz.aviso = t("PEÇAS NÃO COMPRADAS FORAM TIRADAS")
            viz.tempo_aviso = 2.5
        self.app.trocar(viz)

    def _avisar(self, msg):
        self.aviso = t(msg)
        self.tempo_aviso = 2.0

    # --------------------------------------------------------
    # GEOMETRIA
    # --------------------------------------------------------

    def _rect_aba(self, i):
        return pygame.Rect(596 + i * 45, 84, 42, 42)

    def _rect_card(self, k):
        col, lin = k % 3, k // 3
        y0 = GRADE_Y + (40 if self.dados_aba[2] == "chao" else 0)
        return pygame.Rect(GRADE_X + col * (CARD[0] + 8), y0 + lin * (CARD[1] + 8), *CARD)

    def _rect_cor(self, i):
        n = len(self.dados_aba[4])
        por_linha = 5
        col, lin = i % por_linha, i // por_linha
        return pygame.Rect(0, 0, 32, 32).move(620 + col * 76 - 16, 410 + lin * 50 - 16) if n else None

    def _rects_lado(self):
        return {"esq": pygame.Rect(600, 166, 190, 34), "dir": pygame.Rect(804, 166, 190, 34)}

    # --------------------------------------------------------
    # EVENTOS
    # --------------------------------------------------------

    def evento(self, e):
        if self.confirmar:
            if tecla_voltar(e) or (e.type == pygame.KEYDOWN and e.key == pygame.K_n):
                self.confirmar = None
            elif e.type == pygame.KEYDOWN and e.key in (pygame.K_RETURN, pygame.K_KP_ENTER,
                                                         pygame.K_SPACE):
                self._comprar()
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if self.bt_sim.collidepoint(e.pos):
                    self._comprar()
                elif self.bt_nao.collidepoint(e.pos):
                    self.confirmar = None
            return

        if e.type == pygame.KEYDOWN:
            k = e.key
            if tecla_voltar(e):
                self._sair()
            elif k == pygame.K_q:
                self._trocar_aba(-1)
            elif k == pygame.K_e:
                self._trocar_aba(1)
            elif k == pygame.K_n:
                self.noite = not self.noite
                self.som("clique")
            elif k == pygame.K_TAB:
                if self.dados_aba[2] == "chao":
                    self.lado = "dir" if self.lado == "esq" else "esq"
                    self._sincronizar_foco()
                elif self.tem_cor:
                    self.secao = 1 - self.secao
                self.som("clique", 0.6)
            elif k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self._acao_foco()
            elif k in (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d,
                       pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s):
                self._mover_foco(k)
            return

        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self._clique(e.pos)
        elif e.type == pygame.MOUSEWHEEL:
            self.pagina = max(0, min(self._paginas() - 1, self.pagina - e.y))
            self.foco = 0

    def _mover_foco(self, k):
        dx = {pygame.K_LEFT: -1, pygame.K_a: -1, pygame.K_RIGHT: 1, pygame.K_d: 1}.get(k, 0)
        dy = {pygame.K_UP: -1, pygame.K_w: -1, pygame.K_DOWN: 1, pygame.K_s: 1}.get(k, 0)
        if self.secao == 1 and self.tem_cor:
            n = len(self.dados_aba[4])
            self.foco_cor = (self.foco_cor + dx + dy * 5) % n
            self.som("clique", 0.4)
            return
        ids = self._ids()
        idx = self.pagina * self._pp() + self.foco + dx + dy * 3
        idx = max(0, min(len(ids) - 1, idx))
        self.pagina, self.foco = idx // self._pp(), idx % self._pp()
        self.som("clique", 0.4)

    def _clique(self, pos):
        if self.bt_voltar.collidepoint(pos) or self.bt_pronto.collidepoint(pos):
            self._sair()
            return
        if self.bt_noite.collidepoint(pos):
            self.noite = not self.noite
            self.som("clique")
            return
        for i in range(len(ABAS)):
            if self._rect_aba(i).collidepoint(pos):
                if i != self.aba:
                    self.aba = i
                    self.secao = 0
                    self._sincronizar_foco()
                    self.som("clique")
                return
        if self.dados_aba[2] == "chao":
            for lado, r in self._rects_lado().items():
                if r.collidepoint(pos) and lado != self.lado:
                    self.lado = lado
                    self._sincronizar_foco()
                    self.som("clique")
                    return
        if self.dados_aba[1] == "telhado" and self.bt_chamine.collidepoint(pos):
            if self.casa["telhado"] in fc.TELHADOS_SEM_CHAMINE:
                self._avisar("ESTE TELHADO NÃO TEM CHAMINÉ")
                self.som("erro")
            else:
                self.casa["chamine"] = not self.casa["chamine"]
                self.som("clique")
            return
        if self._paginas() > 1:
            if self.bt_pag_esq.collidepoint(pos):
                self.pagina = (self.pagina - 1) % self._paginas()
                self.foco = 0
                self.som("clique")
                return
            if self.bt_pag_dir.collidepoint(pos):
                self.pagina = (self.pagina + 1) % self._paginas()
                self.foco = 0
                self.som("clique")
                return
        for k, pid in enumerate(self._pagina_ids()):
            if self._rect_card(k).collidepoint(pos):
                self.foco = k
                self.secao = 0
                self._escolher(pid)
                return
        if self.tem_cor:
            for i in range(len(self.dados_aba[4])):
                if self._rect_cor(i).inflate(8, 8).collidepoint(pos):
                    self.secao = 1
                    self._mudar_cor(i)
                    return
        if self.bt_acao.collidepoint(pos):
            pid = self._item_foco()
            if not self.possui(pid):
                self._aplicar(pid)
                self._pedir_compra(pid)
            elif pid != self._atual():
                self._escolher(pid)

    # --------------------------------------------------------
    # ATUALIZAÇÃO / DESENHO
    # --------------------------------------------------------

    def atualizar(self, dt):
        self.tempo += dt
        self.pulo = max(0.0, self.pulo - dt * 2.5)
        self.tempo_aviso = max(0.0, self.tempo_aviso - dt)
        self.particulas.atualizar(dt)
        self.nuvens.atualizar(dt, 0.3)

    def desenhar(self, tela):
        tela.fill((26, 30, 50))
        self._desenhar_previa(tela)
        self._desenhar_painel(tela)
        self._desenhar_topo(tela)
        if self.tempo_aviso > 0:
            sup = ui.texto(self.aviso, 12, AMARELO)
            r = sup.get_rect(center=(PREVIA.centerx, 130)).inflate(28, 18)
            ui.painel(tela, r, (20, 24, 40), AMARELO, 12, 2, sombra=False)
            tela.blit(sup, sup.get_rect(center=r.center))
        if self.confirmar:
            self._desenhar_confirmar(tela)

    def _desenhar_topo(self, tela):
        mouse = pygame.mouse.get_pos()
        hover = self.bt_voltar.collidepoint(mouse)
        ui.painel(tela, self.bt_voltar, (70, 80, 130) if hover else (30, 36, 60), BRANCO, 12, 3)
        ui.desenhar_texto(tela, t("← VOLTAR"), self.bt_voltar.center, 12, BRANCO, "center")
        titulo = pygame.Rect(362, 8, 300, 46)
        ui.painel(tela, titulo, (30, 36, 60), BRANCO, 14, 3)
        ui.desenhar_texto(tela, t("REFORMA"), titulo.center, 16, AMARELO, "center")
        ui.desenhar_texto(tela, t("CASA DE ") + self.app.jogador.nome.upper(), (512, 62), 10, BRANCO,
                          "midtop")
        ui.desenhar_moedas(tela, self.save["moedas"], (1008, 24), "topright", 16)

    def _desenhar_previa(self, tela):
        tela.set_clip(PREVIA)
        fase = "noite" if self.noite else "dia"
        tela.blit(ceu.gradiente(fase, PREVIA.w, 360), PREVIA.topleft)
        self.ceu.desenhar(tela, fase, self.tempo, sol=(90, 150), lua=(500, 140))
        self.nuvens.desenhar(tela)
        pygame.draw.rect(tela, (190, 228, 170), (PREVIA.x, 420, PREVIA.w, PREVIA.bottom - 420))
        for x in range(PREVIA.x - 300, PREVIA.right, 48):
            pygame.draw.polygon(tela, (196, 233, 176), [(x, 420), (x + 24, 420), (x + 250, PREVIA.bottom),
                                                         (x + 226, PREVIA.bottom)])
        pygame.draw.rect(tela, (44, 44, 52), (PREVIA.x, 596, PREVIA.w, 48))
        pygame.draw.line(tela, (200, 200, 205), (PREVIA.x, 596), (PREVIA.right, 596), 4)
        for x in range(PREVIA.x, PREVIA.right, 34):
            pygame.draw.line(tela, (255, 214, 64), (x, 620), (x + 18, 620), 4)

        ax, ay = ANCORA
        s = ESCALA
        fd.desenhar_caminho(tela, (ax, ay + 10), (ax, 598), 26 * s, self.casa["caminho"], self.tempo)
        cor_ovo = self.app.jogador.cor
        fd.desenhar_casa(tela, ANCORA, s, self.casa, cor_ovo, self.noite, self.tempo)
        # O ovo (e o pet) na frente de casa
        itens = self.casa["itens"]
        if itens.get("esq") == "banco":
            x, chao = ax - 100 * s, ay - 14 * s
        elif itens.get("dir") == "banco":
            x, chao = ax + 100 * s, ay - 14 * s
        else:
            x, chao = ax - 50 * s, ay + 14 * s
        h = 100
        pulo = math.sin(self.pulo * math.pi) * 30 if self.pulo > 0 else 0
        self.app.jogador.desenhar(tela, (x, chao - h / 2 - pulo), h)
        self.app.desenhar_pet(tela, (ax - 14 * s, ay + 24 * s), feliz=self.pulo > 0)
        if self.noite:
            ui.veu(tela, 150, (20, 30, 80))
            fd.desenhar_luzes(tela, ANCORA, s, self.casa, cor_ovo, self.tempo)
        self.particulas.desenhar(tela)

        # Slot do jardim piscando
        if self.dados_aba[2] == "chao" and int(self.tempo * 3) % 2 == 0:
            cx = ax + fd.X_ITENS[self.lado] * s
            r = pygame.Rect(0, 0, 70 * s, 120 * s)
            r.midbottom = (cx, ay + 4)
            pygame.draw.rect(tela, AMARELO, r, 3, border_radius=10)

        if self._provando():
            sup = ui.texto(t("PROVANDO"), 12, AMARELO)
            tela.blit(sup, sup.get_rect(midtop=(PREVIA.centerx, PREVIA.y + 14)))
        tela.set_clip(None)
        pygame.draw.rect(tela, BRANCO, PREVIA, 3, border_radius=14)

        mouse = pygame.mouse.get_pos()
        for r, txt, cor in ((self.bt_noite, "VER DE DIA" if self.noite else "VER DE NOITE", (60, 70, 120)),
                            (self.bt_pronto, "PRONTO!", (70, 170, 90))):
            pygame.draw.rect(tela, ui.clarear(cor, 30) if r.collidepoint(mouse) else cor, r, border_radius=10)
            pygame.draw.rect(tela, BRANCO, r, 2, border_radius=10)
            ui.desenhar_texto(tela, t(txt), r.center, 8 if r is self.bt_noite else 12, BRANCO, "center")

    def _desenhar_painel(self, tela):
        ui.painel(tela, PAINEL, (32, 36, 58), BRANCO, 14, 3)
        mouse = pygame.mouse.get_pos()
        for i, aba in enumerate(ABAS):
            r = self._rect_aba(i)
            ativa = i == self.aba
            pygame.draw.rect(tela, (90, 100, 160) if ativa else ((60, 66, 100) if r.collidepoint(mouse)
                                                                  else (44, 48, 78)), r, border_radius=8)
            pygame.draw.rect(tela, AMARELO if ativa else BRANCO, r, 2, border_radius=8)
            self._icone_aba(tela, aba[0], r.center)
        nome = self.dados_aba[0]
        ui.desenhar_texto(tela, t(nome), (PAINEL.x + 14, 138), 14, AMARELO)
        ui.desenhar_texto(tela, "Q / E", (PAINEL.right - 14, 142), 8, (200, 200, 220), "topright")

        if self.dados_aba[2] == "chao":
            for lado, r in self._rects_lado().items():
                ativo = lado == self.lado
                pygame.draw.rect(tela, AMARELO if ativo else (60, 66, 100), r, border_radius=8)
                ui.desenhar_texto(tela, t("ESQUERDA") if lado == "esq" else t("DIREITA"), r.center, 10,
                                  (40, 30, 10) if ativo else BRANCO, "center", not ativo)

        cor_ovo = self.app.jogador.cor
        atual = self._atual()
        for k, pid in enumerate(self._pagina_ids()):
            r = self._rect_card(k)
            foco = (k == self.foco and self.secao == 0)
            hover = r.collidepoint(mouse)
            usando = pid == atual
            pygame.draw.rect(tela, (70, 80, 125) if (hover or foco) else (48, 54, 86), r, border_radius=10)
            borda = AMARELO if usando else (BRANCO if foco else (110, 120, 160))
            pygame.draw.rect(tela, borda, r, 3 if (usando or foco) else 2, border_radius=10)
            self._miniatura(tela, pid, r, cor_ovo)
            d = fc.CATALOGO.get(pid)
            nome_card = t(d["nome"]) if d else t("NADA")
            linhas = ui.quebrar_linhas(nome_card, 7, r.w - 10)[:2] \
                if ui.tamanho_que_cabe(nome_card, r.w - 8, (8, 7)) < 8 or \
                ui.texto(nome_card, 8).get_width() > r.w - 8 else [nome_card]
            tam = 8 if len(linhas) == 1 else 7
            for k, l in enumerate(linhas):
                y = r.bottom - 26 - (len(linhas) - 1 - k) * 9
                ui.desenhar_texto(tela, l, (r.centerx, y), tam, BRANCO, "center")
            # Etiqueta
            if usando and self.possui(pid):
                etq, cor = "USANDO", (120, 230, 120)
            elif usando:
                etq, cor = "PROVANDO", AMARELO
            elif self.possui(pid):
                etq, cor = ("GRÁTIS" if d and d["preco"] == 0 else ("TENHO" if d else "")), (200, 200, 220)
            else:
                etq, cor = None, None
            if etq is not None:
                ui.desenhar_texto(tela, t(etq), (r.centerx, r.bottom - 12), 8, cor, "center")
            else:
                preco = d["preco"]
                caro = preco > self.save["moedas"]
                sup = ui.texto(str(preco), 8, (255, 120, 120) if caro else AMARELO)
                larg = sup.get_width() + 14
                x0 = r.centerx - larg // 2
                ui.moeda(tela, (x0 + 5, r.bottom - 12), 5)
                tela.blit(sup, sup.get_rect(midleft=(x0 + 13, r.bottom - 12)))
            if d:
                pygame.draw.rect(tela, RARIDADES.get(d["raridade"], BRANCO),
                                 (r.x + 8, r.bottom - 5, r.w - 16, 3), border_radius=2)

        if self._paginas() > 1:
            for r, txt in ((self.bt_pag_esq, "←"), (self.bt_pag_dir, "→")):
                pygame.draw.rect(tela, (60, 66, 100), r, border_radius=8)
                ui.desenhar_texto(tela, txt, r.center, 12, BRANCO, "center")
            ui.desenhar_texto(tela, f"{self.pagina + 1}/{self._paginas()}", (798, 541), 10, BRANCO, "center")

        if self.tem_cor:
            ui.desenhar_texto(tela, t("COR"), (PAINEL.x + 14, 372), 12,
                              AMARELO if self.secao == 1 else BRANCO)
            ui.desenhar_texto(tela, "TAB", (PAINEL.x + max(70, 26 + ui.texto(t("COR"), 12).get_width()), 374), 8, (200, 200, 220))
            chave = self.dados_aba[3]
            for i, (nome_cor, cor) in enumerate(self.dados_aba[4]):
                r = self._rect_cor(i)
                c = fc.cor_telhado({"cor_telhado": i}, cor_ovo) if cor is None else cor
                pygame.draw.circle(tela, c, r.center, 16)
                pygame.draw.circle(tela, ui.escurecer(c, 70), r.center, 16, 2)
                if cor is None:
                    ui.desenhar_texto(tela, t("OVO"), r.center, 7, BRANCO, "center")
                if self.casa[chave] == i:
                    pygame.draw.circle(tela, BRANCO, r.center, 20, 3)
                    ui.estrela(tela, (r.right, r.y), 5, AMARELO)
                if self.secao == 1 and self.foco_cor == i:
                    pygame.draw.circle(tela, AMARELO, r.center, 23, 2)

        if self.dados_aba[1] == "telhado":
            sem = self.casa["telhado"] in fc.TELHADOS_SEM_CHAMINE
            r = self.bt_chamine
            txt = t("CHAMINÉ: ") + ("---" if sem else (t("SIM") if self.casa["chamine"] else t("NÃO")))
            pygame.draw.rect(tela, (50, 54, 80) if sem else (70, 80, 125), r, border_radius=8)
            ui.desenhar_texto(tela, txt, r.center, 8, (150, 150, 160) if sem else BRANCO, "center")

        self._desenhar_detalhe(tela)

    def _desenhar_detalhe(self, tela):
        barra = pygame.Rect(596, 564, 404, 72)
        pygame.draw.rect(tela, (24, 28, 46), barra, border_radius=10)
        if self.secao == 1 and self.tem_cor:
            nome_cor = self.dados_aba[4][self.foco_cor][0]
            ui.desenhar_texto(tela, t("COR: ") + t(nome_cor), (barra.x + 12, barra.y + 12), 12, AMARELO)
            ui.desenhar_texto(tela, t("As cores são grátis!"), (barra.x + 12, barra.y + 38), 8, BRANCO)
            return
        pid = self._item_foco()
        d = fc.CATALOGO.get(pid)
        nome = t(d["nome"]) if d else t("NADA")
        desc = t(d["desc"]) if d else t("Deixar este lugar vazio.")
        tam = ui.tamanho_que_cabe(nome, 220, (12, 10, 8))
        ui.desenhar_texto(tela, nome, (barra.x + 12, barra.y + 12), tam, AMARELO)
        for k, l in enumerate(ui.quebrar_linhas(desc, 8, 210)[:3]):
            ui.desenhar_texto(tela, l, (barra.x + 12, barra.y + 32 + k * 12), 8, BRANCO)
        r = self.bt_acao
        if not self.possui(pid):
            preco = d["preco"]
            if preco <= self.save["moedas"]:
                txt, cor = t("COMPRAR POR {n}", n=preco), (70, 170, 90)
            else:
                txt, cor = t("FALTAM {n}", n=preco - self.save['moedas']), (90, 90, 100)
        elif pid == self._atual():
            txt, cor = t("USANDO"), (60, 66, 100)
        else:
            txt, cor = t("USAR"), (70, 130, 200)
        hover = r.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(tela, ui.clarear(cor, 25) if hover else cor, r, border_radius=10)
        pygame.draw.rect(tela, BRANCO, r, 2, border_radius=10)
        tam = ui.tamanho_que_cabe(txt, r.w - 12, (10, 8))
        ui.desenhar_texto(tela, txt, r.center, tam, BRANCO, "center")

    def _miniatura(self, tela, pid, r, cor_ovo):
        area = pygame.Rect(r.x + 6, r.y + 6, r.w - 12, r.h - 40)
        parte = self.dados_aba[2]
        if pid == "":
            pygame.draw.line(tela, (150, 150, 170), (area.centerx - 12, area.centery - 12),
                             (area.centerx + 12, area.centery + 12), 3)
            pygame.draw.line(tela, (150, 150, 170), (area.centerx + 12, area.centery - 12),
                             (area.centerx - 12, area.centery + 12), 3)
            return
        if parte in ("chao", "enfeite"):
            sup = fd.miniatura_item(pid, parte, cor_ovo, area.size)
            tela.blit(sup, area)
            return
        casa = copy.deepcopy(self.casa)
        casa[self.dados_aba[1]] = pid
        casa["itens"] = {"esq": "", "dir": "", "telhado": ""}
        s = 0.27 if parte in ("cerca", "caminho") else 0.3
        sup = fd._estatica(casa, cor_ovo, False, s, sem_itens=True)
        dest = sup.get_rect(midbottom=(area.centerx, area.bottom + round(fd.Y_MAX * s) - 2))
        tela.set_clip(area)
        tela.blit(sup, dest)
        if parte == "caminho":
            fd.desenhar_caminho(tela, (area.centerx, area.bottom - 4), (area.centerx, area.bottom + 20),
                                14, pid)
        tela.set_clip(None)

    @staticmethod
    def _icone_aba(tela, nome, c):
        x, y = c
        if nome == "PAREDE":
            for j in range(3):
                for i in range(2):
                    pygame.draw.rect(tela, (205, 110, 80), (x - 12 + i * 12 + (5 if j % 2 else 0) - 3, y - 10 + j * 7, 10, 5))
        elif nome == "TELHADO":
            pygame.draw.polygon(tela, (230, 90, 70), [(x - 14, y + 6), (x, y - 10), (x + 14, y + 6)])
        elif nome == "PORTA":
            pygame.draw.rect(tela, (150, 95, 55), (x - 8, y - 12, 16, 24))
            pygame.draw.circle(tela, AMARELO, (x + 4, y), 2)
        elif nome == "JANELAS":
            pygame.draw.rect(tela, (170, 215, 255), (x - 10, y - 10, 20, 20))
            pygame.draw.rect(tela, BRANCO, (x - 10, y - 10, 20, 20), 2)
            pygame.draw.line(tela, BRANCO, (x, y - 10), (x, y + 9), 2)
            pygame.draw.line(tela, BRANCO, (x - 10, y), (x + 9, y), 2)
        elif nome == "CERCA":
            for i in range(3):
                pygame.draw.rect(tela, BRANCO, (x - 11 + i * 9, y - 8, 5, 18))
            pygame.draw.line(tela, BRANCO, (x - 13, y - 2), (x + 13, y - 2), 2)
        elif nome == "CAMINHO":
            for i in range(3):
                pygame.draw.ellipse(tela, (200, 200, 210), (x - 8 + (i % 2) * 6, y - 11 + i * 8, 10, 6))
        elif nome == "CORREIO":
            pygame.draw.rect(tela, (120, 80, 40), (x - 1, y, 3, 12))
            pygame.draw.rect(tela, (60, 110, 220), (x - 10, y - 9, 20, 11), border_radius=3)
            pygame.draw.rect(tela, (230, 60, 60), (x + 7, y - 13, 3, 7))
        elif nome == "JARDIM":
            pygame.draw.line(tela, (80, 170, 70), (x, y + 10), (x, y - 4), 2)
            for i in range(5):
                a = i * math.tau / 5
                pygame.draw.circle(tela, (255, 110, 150), (x + math.cos(a) * 5, y - 6 + math.sin(a) * 5), 3)
            pygame.draw.circle(tela, AMARELO, (x, y - 6), 3)
        elif nome == "ENFEITE":
            pygame.draw.line(tela, (200, 200, 210), (x - 8, y + 12), (x - 8, y - 12), 2)
            pygame.draw.polygon(tela, (230, 90, 70), [(x - 7, y - 12), (x + 10, y - 7), (x - 7, y - 2)])

    def _desenhar_confirmar(self, tela):
        ui.veu(tela, 160)
        d = fc.CATALOGO[self.confirmar]
        caixa = pygame.Rect(0, 0, 520, 220)
        caixa.center = (LARGURA // 2, ALTURA // 2)
        ui.painel(tela, caixa, (32, 36, 58), AMARELO, 18, 4)
        msg = t("COMPRAR {nome} POR {n}?", nome=t(d['nome']), n=d['preco'])
        for k, l in enumerate(ui.quebrar_linhas(msg, 14, 460)):
            ui.desenhar_texto(tela, l, (caixa.centerx, caixa.y + 34 + k * 24), 14, BRANCO, "midtop")
        self.bt_sim.midbottom = (caixa.centerx - 90, caixa.bottom - 24)
        self.bt_nao.midbottom = (caixa.centerx + 90, caixa.bottom - 24)
        mouse = pygame.mouse.get_pos()
        for r, txt, cor in ((self.bt_sim, "SIM", (70, 170, 90)), (self.bt_nao, "NÃO", (170, 60, 60))):
            pygame.draw.rect(tela, ui.clarear(cor, 30) if r.collidepoint(mouse) else cor, r, border_radius=12)
            pygame.draw.rect(tela, BRANCO, r, 3, border_radius=12)
            ui.desenhar_texto(tela, t(txt), r.center, 16, BRANCO, "center")
