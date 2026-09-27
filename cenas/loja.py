import math

import pygame

from settings import *
from core import ui
from core.cena import Cena, tecla_voltar
from core.fundo_menu import FundoAnimado
from core.jogador import Jogador

# ============================================================
# LOJA
# ============================================================
# À esquerda o PROVADOR (o ovo já "vestindo" o item em foco),
# à direita a grade de produtos (4x3 por página) com 8 abas.
#   ← → ↑ ↓  escolhe      Q / E  troca de aba
#   ENTER    compra / equipa / usa      ESC  volta
# Cosméticos, pets e móveis ficam em save["inventario"];
# comidas e sementes em save["comida"] (quantidade).

ABAS = ["CHAPÉUS", "ROSTO", "CORPO", "VISUAL", "EFEITOS", "PETS", "CASA", "QUINTAL", "MERCADO"]
SLOT_DA_ABA = {"CHAPÉUS": "cabeca", "ROSTO": "rosto", "CORPO": "corpo", "EFEITOS": "efeito"}

# Aba VISUAL: aparência extra (core/visual_extra.py), uma página por
# grupo (CABELO, OLHOS, BOCA, COR, ROUPA). Teclas 1-5 pulam de grupo.
ABA_VISUAL = "VISUAL"
GRUPOS_VISUAL = [("CABELO", "cabelo_x"), ("OLHOS", "olhos_x"), ("BOCA", "boca_x"),
                 ("COR", "cor_x"), ("ROUPA", "roupa")]

COLS, LINS = 4, 3
CARD = (150, 150)
GRADE = pygame.Rect(352, 150, 4 * 150 + 3 * 14, 3 * 150 + 2 * 14)
PROVADOR = pygame.Rect(16, 138, 320, 566)
ALTURA_PROVADOR = 170            # altura do corpo do ovo no provador

CORES_RARIDADE = {
    "COMUM": (230, 230, 240), "INCOMUM": (110, 220, 120), "RARO": (90, 170, 255),
    "EPICO": (190, 120, 255), "ÉPICO": (190, 120, 255), "LENDARIO": (255, 214, 64),
    "LENDÁRIO": (255, 214, 64),
}


def _modulo(nome):
    """Importa um módulo de catálogo (pode ainda não existir)."""
    try:
        return __import__(f"core.{nome}", fromlist=[nome])
    except ImportError:
        return None


DESCRICOES = {
    "cosmetico": "Aparece no seu ovo em TODOS os mini jogos!",
    "pet": "Segue o seu ovo pela casa e comemora com você no fim dos jogos.",
    "movel": "Enfeita a casa. Clique nele para ver o que faz!",
}


class Produto:

    def __init__(self, tipo, pid, dados):
        self.tipo = tipo            # cosmetico | pet | movel | comida | semente
        self.id = pid
        self.dados = dados
        self.nome = dados.get("nome", pid.upper())
        if tipo == "pet" and dados.get("especie"):
            self.nome = f"{dados['nome']} ({dados['especie']})"
        self.preco = int(dados.get("preco", 0))
        self.raridade = dados.get("raridade", "COMUM")
        self.descricao = dados.get("talento") or dados.get("descricao") or DESCRICOES.get(tipo, "")
        if tipo == "comida" and dados.get("efeitos"):
            nomes = {"fome": "FOME", "energia": "ENERGIA", "diversao": "DIVERSÃO",
                     "higiene": "HIGIENE"}
            self.descricao = "  ".join(f"{nomes.get(k, k)} +{v}" for k, v in dados["efeitos"].items())
        elif tipo == "semente" and dados.get("tempo"):
            minutos = int(dados["tempo"]) // 60
            tempo = f"{minutos // 60}h" if minutos >= 60 else f"{minutos} min"
            self.descricao = f"Plante no jardim do SOL. Fica pronta em {tempo}."


class CenaLoja(Cena):

    musica = "vitrine"

    def __init__(self, app, voltar_para):
        super().__init__(app)
        self.voltar_para = voltar_para
        self.fundo = FundoAnimado((90, 50, 20), (170, 110, 40), semente=12)
        self.aba = 0
        self.pagina = 0
        self.indice = 0
        self.tempo = 0.0
        self.confirmar = None           # Produto aguardando SIM/NÃO
        self.aviso = ""
        self.tempo_aviso = 0.0
        self.particulas = ui.Particulas()
        self._icones = {}
        self._provador = {}
        self._ultimo_mouse = None

        self.botao_voltar = ui.Botao((16, 16, 150, 52), "< VOLTAR", 14)
        self.botao_acao = ui.Botao((0, 0, 280, 56), "COMPRAR", 16,
                                   cor=(40, 130, 60), cor_hover=(60, 180, 90))
        self.botao_acao.rect.midbottom = (PROVADOR.centerx, PROVADOR.bottom - 16)
        self.botao_sim = ui.Botao((0, 0, 160, 54), "SIM", 16, cor=(40, 130, 60),
                                  cor_hover=(60, 180, 90))
        self.botao_nao = ui.Botao((0, 0, 160, 54), "NÃO", 16, cor=(130, 50, 50),
                                  cor_hover=(180, 70, 70))
        self.botao_sim.rect.center = (LARGURA // 2 - 95, ALTURA // 2 + 60)
        self.botao_nao.rect.center = (LARGURA // 2 + 95, ALTURA // 2 + 60)
        self.seta_esq = pygame.Rect(GRADE.x, GRADE.bottom + 14, 44, 36)
        self.seta_dir = pygame.Rect(GRADE.right - 44, GRADE.bottom + 14, 44, 36)

        self.rects_abas = []
        largura = (LARGURA - 32) // len(ABAS)
        for i in range(len(ABAS)):
            self.rects_abas.append(pygame.Rect(16 + i * largura, 84, largura - 6, 42))

        self.produtos = self._montar_produtos()
        self._pags = {nome: self._dividir(nome) for nome in ABAS}

        # Botões dos grupos da aba VISUAL (no lugar das bolinhas de página)
        primeiras = []                  # (rótulo, 1ª página do grupo)
        for i, (rot, _) in enumerate(self._pags[ABA_VISUAL]):
            if rot and rot not in (r for r, _ in primeiras):
                primeiras.append((rot, i))
        n = max(1, len(primeiras))
        livre = self.seta_dir.x - self.seta_esq.right - 20
        larg = min(104, (livre - (n - 1) * 8) // n)
        x0 = GRADE.centerx - (n * larg + (n - 1) * 8) // 2
        self.rects_grupos = [(rot, i, pygame.Rect(x0 + k * (larg + 8), self.seta_esq.y, larg,
                                                  self.seta_esq.h))
                             for k, (rot, i) in enumerate(primeiras)]

    # --------------------------------------------------------
    # CATÁLOGO
    # --------------------------------------------------------

    def _montar_produtos(self):
        inv = set(self.app.save["inventario"])
        abas = {nome: [] for nome in ABAS}
        slots_visual = {s for _, s in GRUPOS_VISUAL}

        cos = _modulo("cosmeticos")
        for pid, d in getattr(cos, "CATALOGO", {}).items():
            aba = next((a for a, s in SLOT_DA_ABA.items() if s == d.get("slot")), None)
            if aba is None and d.get("slot") in slots_visual:
                aba = ABA_VISUAL
            if aba and (d.get("loja", True) or pid in inv):
                abas[aba].append(Produto("cosmetico", pid, d))

        pets = _modulo("pets")
        for pid, d in getattr(pets, "CATALOGO", {}).items():
            abas["PETS"].append(Produto("pet", pid, d))

        moveis = _modulo("moveis")
        for pid, d in getattr(moveis, "CATALOGO", {}).items():
            if not d.get("loja", True):
                continue
            aba = "QUINTAL" if d.get("comodo") == "SOL" else "CASA"
            abas[aba].append(Produto("movel", pid, d))

        itens = _modulo("itens")
        for pid, d in getattr(itens, "COMIDAS", {}).items():
            if d.get("loja", True):
                abas["MERCADO"].append(Produto("comida", pid, d))
        for pid, d in getattr(itens, "SEMENTES", {}).items():
            abas["MERCADO"].append(Produto("semente", pid, d))

        # CAIXA SURPRESA: um cosmético sorteado pela raridade
        from core import caixa
        abas["MERCADO"].append(Produto("caixa", "caixa_surpresa", dict(
            nome="CAIXA SURPRESA", preco=caixa.PRECO_CAIXA, raridade="RARO",
            descricao="Um cosmético sorteado! Repetido vira OVOEDAS. Pode vir até exclusivo!")))

        for lista in abas.values():
            lista.sort(key=lambda p: (p.preco, p.nome))
        return abas

    def _dividir(self, aba):
        """Páginas da aba: lista de (rótulo do grupo ou None, produtos)."""
        n = COLS * LINS
        lista = self.produtos[aba]
        if aba == ABA_VISUAL:
            grupos = [(rot, [p for p in lista if p.dados.get("slot") == slot])
                      for rot, slot in GRUPOS_VISUAL]
        else:
            grupos = [(None, lista)]
        pags = [(rot, itens[i:i + n]) for rot, itens in grupos if itens
                for i in range(0, len(itens), n)]
        return pags or [(None, [])]

    @property
    def lista(self):
        return self.produtos[ABAS[self.aba]]

    @property
    def paginas(self):
        return len(self._pags[ABAS[self.aba]])

    @property
    def na_pagina(self):
        pags = self._pags[ABAS[self.aba]]
        return pags[min(self.pagina, len(pags) - 1)][1]

    @property
    def grupo(self):
        """Rótulo do grupo da página atual (aba VISUAL) ou None."""
        pags = self._pags[ABAS[self.aba]]
        return pags[min(self.pagina, len(pags) - 1)][0]

    def _ir_pagina(self, pagina):
        if pagina != self.pagina:
            self.pagina = pagina
            self.indice = 0
            self.som("clique", 0.6)

    @property
    def atual(self):
        itens = self.na_pagina
        if not itens:
            return None
        return itens[min(self.indice, len(itens) - 1)]

    # --------------------------------------------------------
    # ESTADO DE CADA PRODUTO
    # --------------------------------------------------------

    def _tem(self, p):
        if p.tipo == "caixa":
            return False
        if p.tipo in ("comida", "semente"):
            return self.app.save["comida"].get(p.id, 0)
        return p.id in self.app.save["inventario"]

    def _ativo(self, p):
        save = self.app.save
        if p.tipo == "cosmetico":
            return save["equipado"].get(p.dados.get("slot")) == p.id
        if p.tipo == "pet":
            return save["pet"] == p.id
        if p.tipo == "movel":
            return p.id in save["moveis"]
        return False

    def _rotulo_acao(self, p):
        if p is None:
            return ""
        if p.tipo in ("comida", "semente"):
            return f"COMPRAR  {p.preco}"
        if not self._tem(p):
            return f"COMPRAR  {p.preco}"
        if p.id.startswith("canteiro"):
            return "COMPRADO"
        if p.tipo == "cosmetico":
            return "TIRAR" if self._ativo(p) else "EQUIPAR"
        if p.tipo == "pet":
            return "GUARDAR" if self._ativo(p) else "USAR ESTE PET"
        return "ESCONDER" if self._ativo(p) else "MOSTRAR"

    # --------------------------------------------------------
    # AÇÕES
    # --------------------------------------------------------

    def _avisar(self, msg):
        self.aviso = msg
        self.tempo_aviso = 2.2

    def _acao(self):
        p = self.atual
        if p is None:
            return
        compravel = p.tipo in ("comida", "semente") or not self._tem(p)
        if compravel:
            if p.preco > self.app.save["moedas"]:
                self.som("erro", 0.6)
                self._avisar("OVOEDAS INSUFICIENTES!")
                return
            self.som("clique")
            self.confirmar = p
            return
        if p.id.startswith("canteiro"):
            return
        self._alternar(p)

    def _comprar(self, p):
        save = self.app.save
        if not save.gastar(p.preco):
            self.som("erro")
            return
        from core import progresso
        progresso.contar(self.app, "compras")
        progresso.contar(self.app, "moedas_gastas", p.preco)
        if p.tipo == "caixa":
            self._abrir_caixa()
            return
        if p.tipo in ("comida", "semente"):
            save["comida"][p.id] = save["comida"].get(p.id, 0) + 1
        else:
            if p.id not in save["inventario"]:
                save["inventario"].append(p.id)
            # Equipa / ativa automaticamente
            if not self._ativo(p):
                self._alternar(p, silencioso=True)
        save.salvar()
        self.som("moeda")
        self.som("vencer", 0.5)
        cores = [CORES_RARIDADE.get(p.raridade, BRANCO), AMARELO, BRANCO]
        self.particulas.explodir(PROVADOR.center, cores, 40, 380)
        self._avisar(f"{p.nome} COMPRADO!")

    def _abrir_caixa(self):
        from core import caixa, progresso
        save = self.app.save
        item, nome, raridade, consolo = caixa.sortear(save)
        progresso.contar(self.app, "caixas")
        cor = CORES_RARIDADE.get(raridade, BRANCO)
        self.particulas.explodir(PROVADOR.center, [cor, AMARELO, BRANCO], 90, 460)
        self.som("levelup" if raridade in ("EPICO", "LENDARIO") else "vencer")
        if consolo:
            self._avisar(f"{nome} (REPETIDO): +{consolo} OVOEDAS")
        else:
            self._avisar(f"CAIXA: {nome} ({raridade})!")
            self.produtos = self._montar_produtos()
        self.app.toasts.adicionar("CAIXA SURPRESA! (" + raridade + ")", nome,
                                  f"+{consolo}" if consolo else "", None)
        save.salvar()

    def _alternar(self, p, silencioso=False):
        save = self.app.save
        if p.tipo == "cosmetico":
            slot = p.dados.get("slot")
            if save["equipado"].get(slot) == p.id:
                save["equipado"].pop(slot, None)
            else:
                save["equipado"][slot] = p.id
        elif p.tipo == "pet":
            save["pet"] = "" if save["pet"] == p.id else p.id
        elif p.tipo == "movel":
            if p.id in save["moveis"]:
                save["moveis"].remove(p.id)
            else:
                save["moveis"].append(p.id)
        save.salvar()
        self._provador.clear()
        if not silencioso:
            self.som("boing" if p.tipo == "pet" else "selecionar")

    def _trocar_aba(self, aba):
        self.aba = aba % len(ABAS)
        self.pagina = 0
        self.indice = 0
        self.som("clique", 0.6)

    def _mover(self, dx, dy):
        n = len(self.na_pagina)
        if n == 0:
            return
        col, lin = self.indice % COLS, self.indice // COLS
        if dx:
            novo = self.indice + dx
            if novo < 0 and self.pagina > 0:
                self.pagina -= 1
                self.indice = len(self.na_pagina) - 1
            elif novo >= n and self.pagina < self.paginas - 1:
                self.pagina += 1
                self.indice = 0
            else:
                self.indice = max(0, min(n - 1, novo))
        else:
            lin = max(0, min((n - 1) // COLS, lin + dy))
            self.indice = min(n - 1, lin * COLS + col)
        self.som("clique", 0.4)

    def _voltar(self):
        self.som("voltar")
        self.app.trocar(self.voltar_para)

    # --------------------------------------------------------
    # EVENTOS
    # --------------------------------------------------------

    def evento(self, e):
        if self.confirmar is not None:
            self._evento_confirmar(e)
            return

        if tecla_voltar(e) or self.botao_voltar.evento(e):
            self._voltar()
            return

        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_q:
                self._trocar_aba(self.aba - 1)
            elif e.key in (pygame.K_e, pygame.K_TAB):
                self._trocar_aba(self.aba + 1)
            elif e.key in (pygame.K_LEFT, pygame.K_a):
                self._mover(-1, 0)
            elif e.key in (pygame.K_RIGHT, pygame.K_d):
                self._mover(1, 0)
            elif e.key in (pygame.K_UP, pygame.K_w):
                self._mover(0, -1)
            elif e.key in (pygame.K_DOWN, pygame.K_s):
                self._mover(0, 1)
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self._acao()
            elif ABAS[self.aba] == ABA_VISUAL and pygame.K_1 <= e.key <= pygame.K_9:
                k = e.key - pygame.K_1
                if k < len(self.rects_grupos):
                    self._ir_pagina(self.rects_grupos[k][1])

        elif e.type == pygame.MOUSEWHEEL:
            if e.y < 0 and self.pagina < self.paginas - 1:
                self.pagina += 1
                self.indice = 0
            elif e.y > 0 and self.pagina > 0:
                self.pagina -= 1
                self.indice = 0

        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for i, r in enumerate(self.rects_abas):
                if r.collidepoint(e.pos):
                    self._trocar_aba(i)
                    return
            for i in range(len(self.na_pagina)):
                if self._rect_card(i).collidepoint(e.pos):
                    if i == self.indice:
                        self._acao()
                    else:
                        self.indice = i
                        self.som("clique", 0.5)
                    return
            if ABAS[self.aba] == ABA_VISUAL:
                for _, pagina, r in self.rects_grupos:
                    if r.collidepoint(e.pos):
                        self._ir_pagina(pagina)
                        return
            if self.botao_acao.evento(e):
                self._acao()
            elif self.seta_esq.collidepoint(e.pos) and self.pagina > 0:
                self.pagina -= 1
                self.indice = 0
                self.som("clique")
            elif self.seta_dir.collidepoint(e.pos) and self.pagina < self.paginas - 1:
                self.pagina += 1
                self.indice = 0
                self.som("clique")

    def _evento_confirmar(self, e):
        sim = self.botao_sim.evento(e) or (
            e.type == pygame.KEYDOWN and e.key in (pygame.K_RETURN, pygame.K_KP_ENTER,
                                                   pygame.K_s, pygame.K_SPACE))
        nao = self.botao_nao.evento(e) or (
            e.type == pygame.KEYDOWN and e.key in (pygame.K_ESCAPE, pygame.K_n))
        if sim:
            p = self.confirmar
            self.confirmar = None
            self._comprar(p)
        elif nao:
            self.confirmar = None
            self.som("voltar")

    # --------------------------------------------------------

    def atualizar(self, dt):
        self.tempo += dt
        self.tempo_aviso = max(0.0, self.tempo_aviso - dt)
        self.fundo.atualizar(dt)
        self.particulas.atualizar(dt)
        self.botao_voltar.atualizar(dt)
        self.botao_acao.atualizar(dt)
        self.botao_sim.atualizar(dt)
        self.botao_nao.atualizar(dt)

        pos = pygame.mouse.get_pos()
        if pos != self._ultimo_mouse and self.confirmar is None:
            self._ultimo_mouse = pos
            for i in range(len(self.na_pagina)):
                if self._rect_card(i).collidepoint(pos):
                    self.indice = i

    # --------------------------------------------------------
    # DESENHO
    # --------------------------------------------------------

    def _rect_card(self, i):
        c, l = i % COLS, i // COLS
        return pygame.Rect(GRADE.x + c * (CARD[0] + 14), GRADE.y + l * (CARD[1] + 14), *CARD)

    def _icone(self, p, tamanho):
        chave = (p.tipo, p.id, tamanho, self.jogador.ovo)
        sup = self._icones.get(chave)
        if sup is not None:
            return sup
        sup = None
        try:
            if p.tipo == "cosmetico":
                sup = _modulo("cosmeticos").icone(p.id, tamanho, self.jogador.ovo)
            elif p.tipo == "pet":
                sup = _modulo("pets").icone(p.id, tamanho)
            elif p.tipo == "movel":
                sup = _modulo("moveis").icone(p.id, tamanho)
            elif p.tipo == "semente":
                sup = _modulo("itens").icone_semente(p.id, tamanho)
            elif p.tipo == "caixa":
                sup = pygame.Surface((tamanho, tamanho), pygame.SRCALPHA)
                t = tamanho
                corpo = pygame.Rect(int(t * 0.18), int(t * 0.38), int(t * 0.64), int(t * 0.5))
                tampa = pygame.Rect(int(t * 0.12), int(t * 0.26), int(t * 0.76), int(t * 0.16))
                pygame.draw.rect(sup, (170, 90, 230), corpo, border_radius=4)
                pygame.draw.rect(sup, (200, 130, 255), tampa, border_radius=4)
                pygame.draw.rect(sup, AMARELO, (t // 2 - t // 14, tampa.y, t // 7, corpo.bottom - tampa.y))
                pygame.draw.circle(sup, AMARELO, (t // 2 - t // 8, tampa.y - t // 14), t // 10, 3)
                pygame.draw.circle(sup, AMARELO, (t // 2 + t // 8, tampa.y - t // 14), t // 10, 3)
                ui.desenhar_texto(sup, "?", (t // 2, corpo.centery + t // 12), max(12, t // 4), BRANCO, "center")
            elif p.tipo == "comida":
                sup = pygame.Surface((tamanho, tamanho), pygame.SRCALPHA)
                _modulo("itens").desenhar_comida(sup, p.id, (tamanho // 2, tamanho // 2),
                                                 int(tamanho * 0.8))
        except (AttributeError, KeyError, TypeError, ValueError, pygame.error):
            sup = None
        if sup is None:
            sup = pygame.Surface((tamanho, tamanho), pygame.SRCALPHA)
            ui.desenhar_texto(sup, "?", (tamanho // 2, tamanho // 2), 24, BRANCO, "center")
        self._icones[chave] = sup
        return sup

    def _avatar_provador(self, p):
        """Avatar do jogador vestindo o item em foco (sem comprar)."""
        equip = dict(self.app.save["equipado"])
        if p is not None and p.tipo == "cosmetico":
            equip[p.dados.get("slot")] = p.id
        ids = tuple(v for _, v in sorted(equip.items()) if v)
        chave = (self.jogador.aparencia(), ids)
        sup = self._provador.get(chave)
        if sup is None:
            base = Jogador.compor(*self.jogador.aparencia(), cosmeticos=ids)
            lado = round(100 * ALTURA_PROVADOR / Jogador.OVO_RECT.h)
            sup = pygame.transform.scale(base, (lado, lado))
            if len(self._provador) > 30:
                self._provador.clear()
            self._provador[chave] = sup
        return sup, ids

    def desenhar(self, tela):
        self.fundo.desenhar(tela)
        ui.desenhar_texto(tela, "LOJA", (LARGURA // 2, 18), 40, AMARELO, "midtop")
        self.botao_voltar.desenhar(tela)
        ui.desenhar_moedas(tela, self.app.save["moedas"], (LARGURA - 16, 20), "topright", 18)

        # Abas
        for i, nome in enumerate(ABAS):
            r = self.rects_abas[i]
            ativa = i == self.aba
            pygame.draw.rect(tela, (120, 70, 20) if ativa else (60, 36, 14), r, border_radius=10)
            pygame.draw.rect(tela, AMARELO if ativa else (190, 150, 100), r, 3, border_radius=10)
            ui.desenhar_texto(tela, nome, r.center, 10, AMARELO if ativa else BRANCO, "center")

        self._desenhar_provador(tela)
        self._desenhar_grade(tela)

        if self.tempo_aviso > 0:
            sup = ui.texto(self.aviso, 14, AMARELO)
            r = sup.get_rect(midbottom=(GRADE.centerx, ALTURA - 8)).inflate(24, 14)
            ui.painel(tela, r, (40, 24, 10), AMARELO, 10, 2, sombra=False)
            tela.blit(sup, sup.get_rect(center=r.center))
        elif ABAS[self.aba] in ("CASA", "QUINTAL"):
            ui.desenhar_texto(tela, "QUER MUDAR A FACHADA? USE REFORMAR NA RUA DOS OVOS!",
                              (GRADE.centerx, ALTURA - 16), 8, (255, 220, 150), "center")

        self.particulas.desenhar(tela)

        if self.confirmar is not None:
            self._desenhar_confirmar(tela)

    def _desenhar_provador(self, tela):
        ui.painel(tela, PROVADOR, (40, 26, 12), (220, 170, 90), 18, 4)
        p = self.atual

        # Palco
        palco_y = PROVADOR.y + 290
        pygame.draw.ellipse(tela, (70, 45, 20), (PROVADOR.centerx - 110, palco_y - 16, 220, 40))
        pygame.draw.ellipse(tela, (110, 75, 35), (PROVADOR.centerx - 100, palco_y - 20, 200, 34))

        balanco = math.sin(self.tempo * 2) * 4
        if p is not None and p.tipo == "movel":
            icone = self._icone(p, 220)
            tela.blit(icone, icone.get_rect(midbottom=(PROVADOR.centerx, palco_y)))
        elif p is not None and p.tipo in ("comida", "semente"):
            icone = self._icone(p, 160)
            tela.blit(icone, icone.get_rect(center=(PROVADOR.centerx, palco_y - 110 + balanco)))
        else:
            sup, ids = self._avatar_provador(p)
            centro = (PROVADOR.centerx - (30 if self._pet_provador(p) else 0),
                      palco_y - ALTURA_PROVADOR // 2 - 22 + balanco)
            desenhar_efeito = getattr(_modulo("cosmeticos"), "desenhar_efeito", None)
            if desenhar_efeito and ids:
                desenhar_efeito(tela, ids, centro, ALTURA_PROVADOR, self.tempo, "atras")
            dx = (Jogador.OVO_RECT.centerx - 50) * sup.get_width() / 100
            dy = (Jogador.OVO_RECT.centery - 50) * sup.get_width() / 100
            tela.blit(sup, sup.get_rect(center=(centro[0] - dx, centro[1] - dy)))
            if desenhar_efeito and ids:
                desenhar_efeito(tela, ids, centro, ALTURA_PROVADOR, self.tempo, "frente")
            pet = self._pet_provador(p)
            if pet:
                pets = _modulo("pets")
                pets.desenhar_parado(tela, pet, (PROVADOR.right - 62, palco_y - 6), self.tempo,
                                     feliz=True, escala=1.0)

        if p is None:
            ui.desenhar_texto(tela, "EM BREVE!", (PROVADOR.centerx, palco_y + 60), 14,
                              BRANCO, "center")
            return

        # Informações
        y = palco_y + 36
        cor_r = CORES_RARIDADE.get(p.raridade, BRANCO)
        for linha in ui.quebrar_linhas(p.nome, 14, PROVADOR.w - 30)[:2]:
            ui.desenhar_texto(tela, linha, (PROVADOR.centerx, y), 14, AMARELO, "midtop")
            y += 22
        ui.desenhar_texto(tela, p.raridade.replace("EPICO", "ÉPICO").replace("LENDARIO", "LENDÁRIO"),
                          (PROVADOR.centerx, y + 2), 10, cor_r, "midtop")
        y += 22
        for linha in ui.quebrar_linhas(p.descricao, 10, PROVADOR.w - 36)[:4]:
            ui.desenhar_texto(tela, linha, (PROVADOR.centerx, y), 10, (230, 220, 200), "midtop")
            y += 16

        tem = self._tem(p)
        if p.tipo in ("comida", "semente"):
            ui.desenhar_texto(tela, f"VOCÊ TEM: {tem}", (PROVADOR.centerx, self.botao_acao.rect.y - 26),
                              12, BRANCO, "midtop")

        # Botão de ação
        rotulo = self._rotulo_acao(p)
        self.botao_acao.rotulo = rotulo
        pode = p.preco <= self.app.save["moedas"]
        compravel = rotulo.startswith("COMPRAR")
        if compravel:
            self.botao_acao.cor = (40, 130, 60) if pode else (90, 60, 60)
            self.botao_acao.cor_hover = (60, 180, 90) if pode else (120, 70, 70)
        else:
            self.botao_acao.cor, self.botao_acao.cor_hover = (60, 70, 130), (90, 100, 180)
        self.botao_acao.desenhar(tela)
        if compravel:
            ui.moeda(tela, (self.botao_acao.rect.right - 26, self.botao_acao.rect.centery - 2), 12)

    def _pet_provador(self, p):
        if p is not None and p.tipo == "pet":
            return p.id
        return self.app.save["pet"] or None

    def _desenhar_grade(self, tela):
        itens = self.na_pagina
        if not itens:
            ui.desenhar_texto(tela, "NADA AQUI AINDA", GRADE.center, 16, BRANCO, "center")
        for i, p in enumerate(itens):
            r = self._rect_card(i)
            sel = i == self.indice
            if sel:
                r = r.move(0, -4)
            cor_r = CORES_RARIDADE.get(p.raridade, BRANCO)
            pygame.draw.rect(tela, (0, 0, 0), r.move(0, 5), border_radius=14)
            pygame.draw.rect(tela, (70, 44, 20) if not sel else (100, 64, 28), r, border_radius=14)
            pygame.draw.rect(tela, cor_r, (r.x, r.y, r.w, 8), border_top_left_radius=14,
                             border_top_right_radius=14)

            icone = self._icone(p, 88)
            tela.blit(icone, icone.get_rect(center=(r.centerx, r.y + 56)))

            linhas = ui.quebrar_linhas(p.nome, 8, r.w - 12)[:2]
            y_nome = r.y + (106 if len(linhas) > 1 else 112)
            for k, linha in enumerate(linhas):
                ui.desenhar_texto(tela, linha, (r.centerx, y_nome + k * 11), 8, BRANCO, "midtop")

            # Preço ou estado
            tem = self._tem(p)
            if p.tipo in ("comida", "semente") or not tem:
                cor = AMARELO if p.preco <= self.app.save["moedas"] else (255, 110, 110)
                ui.moeda(tela, (r.centerx - 24, r.bottom - 17), 8)
                ui.desenhar_texto(tela, str(p.preco), (r.centerx - 12, r.bottom - 16), 10, cor,
                                  "midleft")
                if p.tipo in ("comida", "semente") and tem:
                    ui.desenhar_texto(tela, f"x{tem}", (r.right - 8, r.y + 14), 10, BRANCO,
                                      "topright")
            else:
                ativo = self._ativo(p)
                txt = "EM USO" if ativo else "É SEU"
                if p.id.startswith("canteiro"):
                    txt = "COMPRADO"
                ui.desenhar_texto(tela, txt, (r.centerx, r.bottom - 16), 10,
                                  (120, 255, 150) if ativo or p.id.startswith("canteiro") else BRANCO,
                                  "center")

            borda = AMARELO if sel else (150, 110, 70)
            pygame.draw.rect(tela, borda, r, 3 if sel else 2, border_radius=14)

        # Páginas
        visual = ABAS[self.aba] == ABA_VISUAL and self.rects_grupos
        if self.paginas > 1:
            for rect, simbolo, ativo in ((self.seta_esq, "<", self.pagina > 0),
                                         (self.seta_dir, ">", self.pagina < self.paginas - 1)):
                pygame.draw.rect(tela, (100, 64, 28) if ativo else (50, 34, 16), rect,
                                 border_radius=10)
                ui.desenhar_texto(tela, simbolo, rect.center, 16,
                                  BRANCO if ativo else (120, 100, 80), "center")
        if visual:
            # Grupos (CABELO, OLHOS...) no lugar das bolinhas
            atual = self.grupo
            for k, (rot, _, r) in enumerate(self.rects_grupos):
                ativo = rot == atual
                pygame.draw.rect(tela, (120, 70, 20) if ativo else (60, 36, 14), r, border_radius=10)
                pygame.draw.rect(tela, AMARELO if ativo else (150, 110, 70), r, 2, border_radius=10)
                ui.desenhar_texto(tela, rot, (r.centerx, r.centery - 3), 8,
                                  AMARELO if ativo else BRANCO, "center")
                ui.desenhar_texto(tela, str(k + 1), (r.centerx, r.bottom - 6), 6,
                                  (200, 170, 120), "center")
        elif self.paginas > 1:
            for i in range(self.paginas):
                cor = AMARELO if i == self.pagina else (120, 90, 60)
                pygame.draw.circle(tela, cor, (GRADE.centerx - (self.paginas - 1) * 10 + i * 20,
                                               self.seta_esq.centery), 5)

    def _desenhar_confirmar(self, tela):
        ui.veu(tela, 150)
        caixa = pygame.Rect(0, 0, 560, 240)
        caixa.center = (LARGURA // 2, ALTURA // 2)
        ui.painel(tela, caixa, (40, 26, 12), AMARELO, 18, 4)
        p = self.confirmar
        ui.desenhar_texto(tela, "COMPRAR", (caixa.centerx, caixa.y + 24), 16, BRANCO, "midtop")
        for j, linha in enumerate(ui.quebrar_linhas(p.nome, 16, caixa.w - 40)[:2]):
            ui.desenhar_texto(tela, linha, (caixa.centerx, caixa.y + 54 + j * 24), 16, AMARELO,
                              "midtop")
        ui.moeda(tela, (caixa.centerx - 40, caixa.y + 124), 12)
        ui.desenhar_texto(tela, f"{p.preco} ?", (caixa.centerx - 22, caixa.y + 124), 16, AMARELO,
                          "midleft")
        self.botao_sim.desenhar(tela)
        self.botao_nao.desenhar(tela)
