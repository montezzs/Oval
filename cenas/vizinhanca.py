import datetime
import math
import random

import pygame

from settings import *
from core.idioma import t
from core import idioma
from core import ceu, perfis, ui
from core import fachada_desenho as fd
from core.cena import Cena, tecla_voltar
from cenas.casa_extras.clima import Clima, VEUS
from cenas.rua_comum import carregar_perfis

# ============================================================
# RUA DOS OVOS (VIZINHANÇA)
# ============================================================
# 5 casas ao longo de uma rua em ferradura (como no protótipo do
# dono): cada casa é um ovo com o seu próprio save. Casa vazia =
# lote com a placa +NOVO.
#
#   ← → / A D / TAB   escolhe a casa
#   ENTER / ESPAÇO    entra (ou +NOVO no lote vazio)
#   R                 reformar a fachada
#   DELETE            apagar o ovo (2 confirmações, segurar 3 s)
#   ESC               volta para a tela inicial

# Âncora (centro da base da fachada) e escala (perspectiva)
CASAS = [((118, 540), 1.00), ((232, 318), 0.84), ((512, 250), 0.72),
         ((792, 318), 0.84), ((906, 540), 1.00)]

# Rua: arco de elipse (centro, raios); largura muda com a altura
RUA_C = (512, 720)
RUA_RX, RUA_RY = 270, 390
Y_CEU = 125

ARVORES = [((40, 250), 34), ((392, 205), 26), ((632, 205), 26), ((984, 250), 34)]
FONTE = (512, 575)

TEMPO_SEGURAR = 3.0
AJUDA = "← → ESCOLHER • ENTER ENTRAR • R REFORMAR • ESC INÍCIO"


def ponto_rua(theta):
    return (RUA_C[0] + RUA_RX * math.cos(theta), RUA_C[1] - RUA_RY * math.sin(theta))


def largura_rua(y):
    return 50 + 40 * max(0.0, (y - 330)) / 390


def normal_rua(theta):
    nx, ny = RUA_RY * math.cos(theta), -RUA_RX * math.sin(theta)
    n = math.hypot(nx, ny) or 1
    return nx / n, ny / n


def tangente_rua(theta):
    tx, ty = -RUA_RX * math.sin(theta), -RUA_RY * math.cos(theta)
    n = math.hypot(tx, ty) or 1
    return tx / n, ty / n


def borda_rua(theta, lado):
    """lado=+1 borda de fora, -1 de dentro, 0 centro; frações também valem."""
    x, y = ponto_rua(theta)
    nx, ny = normal_rua(theta)
    w = largura_rua(y) / 2 * lado
    return (x + nx * w, y + ny * w)


# ============================================================
# VEÍCULOS
# ============================================================

CORES_CARRO = [(230, 70, 70), (70, 130, 230), (255, 200, 50), (120, 200, 90), (250, 250, 250)]


def _sprite_veiculo(tipo, cor):
    """Visto de cima, apontando para a direita (+x)."""
    if tipo == "onibus":
        w, h = 72, 24
        sup = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(sup, (230, 30, 30), (0, 0, w, h), border_radius=5)
        for i in range(5):
            pygame.draw.rect(sup, (120, 190, 255), (8 + i * 12, 3, 8, 4))
            pygame.draw.rect(sup, (120, 190, 255), (8 + i * 12, h - 7, 8, 4))
        pygame.draw.rect(sup, (255, 255, 255), (6, h // 2 - 2, w - 14, 4))
        pygame.draw.rect(sup, (180, 220, 255), (w - 8, 3, 5, h - 6), border_radius=2)
    elif tipo == "sorvete":
        w, h = 50, 24
        sup = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(sup, (255, 170, 200), (0, 0, w, h), border_radius=6)
        pygame.draw.rect(sup, (180, 220, 255), (w - 12, 3, 7, h - 6), border_radius=2)
        pygame.draw.polygon(sup, (230, 180, 110), [(14, 6), (14, h - 6), (26, h // 2)])
        pygame.draw.circle(sup, (255, 240, 240), (13, h // 2), 6)
    else:
        w, h = 40, 22
        sup = pygame.Surface((w, h), pygame.SRCALPHA)
        for rx in (6, w - 12):
            pygame.draw.rect(sup, (30, 30, 35), (rx, 0, 6, 4))
            pygame.draw.rect(sup, (30, 30, 35), (rx, h - 4, 6, 4))
        pygame.draw.rect(sup, cor, (0, 2, w, h - 4), border_radius=6)
        pygame.draw.rect(sup, ui.clarear(cor, 35), (10, 5, 18, h - 10), border_radius=3)
        pygame.draw.rect(sup, (180, 220, 255), (28, 5, 6, h - 10), border_radius=2)
        pygame.draw.rect(sup, ui.escurecer(cor, 60), (0, 2, w, h - 4), 1, border_radius=6)
    return sup


class Veiculo:

    def __init__(self, rnd):
        r = rnd.random()
        self.tipo = "carro" if r < 0.65 else ("onibus" if r < 0.85 else "sorvete")
        self.cor = rnd.choice(CORES_CARRO)
        self.sentido = rnd.choice((-1, 1))              # +1: esquerda -> direita
        self.theta = math.pi + 0.08 if self.sentido > 0 else -0.08
        self.faixa = 0.5 * self.sentido                 # mão inglesa? não: cada sentido na sua faixa
        self.vel = 0.5 * rnd.uniform(0.85, 1.15)
        self.buzinou = False
        self.base = _sprite_veiculo(self.tipo, self.cor)
        self._cache = {}

    @property
    def fora(self):
        return self.theta < -0.1 or self.theta > math.pi + 0.1

    def atualizar(self, dt):
        self.theta -= self.vel * dt * self.sentido

    def pos(self):
        return borda_rua(self.theta, self.faixa)

    def rect(self):
        x, y = self.pos()
        return pygame.Rect(x - 26, y - 20, 52, 40)

    def desenhar(self, tela):
        x, y = self.pos()
        if y > ALTURA + 30:
            return
        tx, ty = tangente_rua(self.theta)
        if self.sentido > 0:
            tx, ty = -tx, -ty
        ang = round(math.degrees(math.atan2(-ty, tx)) / 10) * 10
        esc = round((0.6 + 0.4 * max(0.0, y - 330) / 390) * 10) / 10
        chave = (ang, esc)
        sup = self._cache.get(chave)
        if sup is None:
            base = pygame.transform.smoothscale(
                self.base, (round(self.base.get_width() * esc), round(self.base.get_height() * esc)))
            sup = pygame.transform.rotate(base, ang)
            self._cache[chave] = sup
        tela.blit(sup, sup.get_rect(center=(x, y)))


# ============================================================
# A CENA
# ============================================================

class CenaVizinhanca(Cena):

    def __init__(self, app, saindo=None, mudanca=None, reformada=None):
        super().__init__(app)
        self.tempo = 0.0
        self.clima = Clima(app.config)
        self.ceu = ceu.Ceu(altura_estrelas=Y_CEU - 10, semente=21)
        self.nuvens = ceu.Nuvens(4, 16, 80, semente=9, escala=0.7)
        self.rnd = random.Random()
        self.particulas = ui.Particulas()
        self.textos = ui.TextoFlutuante()
        self.veiculos = []
        self.prox_veiculo = 2.0
        self.passaros = None
        self.prox_passaros = 8.0
        self._fundo = None
        self._chave_fundo = None
        self._veu = None

        self.perfis = []
        self.sel = 0
        self.balao = True
        self.hover = None
        self._ultimo_clique = (-1, -10.0)
        self.anim = None               # entrar / sair pela porta
        self.brotar = {}               # slot -> tempo (casa nova brotando)
        self.brilho = {}               # slot -> tempo (casa reformada)
        self.murchar = None            # (slot, t) casa sendo apagada
        self.pulo = [0.0] * 5
        self.espiar = [0.0] * 5
        self.modal = None              # None / "apagar1" / "apagar2" / "pausa"
        self.segurar = 0.0
        self._ultimo_segundo = 0
        self.aviso = ""
        self.tempo_aviso = 0.0
        self.banner = 0.0
        self.boas_vindas = None        # (texto, tempo)

        self._saindo = saindo
        self._mudanca = mudanca
        self._reformada = reformada

        self._calcular_caminhos()
        self._botoes()

    # --------------------------------------------------------
    # PREPARO
    # --------------------------------------------------------

    def _botoes(self):
        self.bt_inicio = pygame.Rect(16, 16, 150, 48)
        self.bt_pausa = pygame.Rect(958, 16, 48, 48)
        # Modal de apagar
        self.ap_nao = pygame.Rect(0, 0, 240, 56)
        self.ap_sim = pygame.Rect(0, 0, 180, 44)
        self.ap_segurar = pygame.Rect(0, 0, 320, 60)
        self.ap_cancelar = pygame.Rect(0, 0, 200, 48)
        self.ap_foco = 0
        # Mini menu de pausa
        self.menu_pausa = ui.Menu(["CONTINUAR", "OPÇÕES", "SAIR DO JOGO"], LARGURA // 2, 250,
                                  360, 56, 14, 16)

    def _calcular_caminhos(self):
        """Ponto da borda de fora da rua mais perto de cada porta."""
        self.caminhos = []
        amostras = [math.pi * i / 240 for i in range(241)]
        for (ax, ay), s in CASAS:
            porta = (ax, ay + 6 * s)
            melhor = min(amostras, key=lambda th: math.dist(borda_rua(th, 1.0), porta))
            self.caminhos.append((porta, borda_rua(melhor, 0.95)))

    def entrar(self):
        self.app.descarregar_ovo()
        self.perfis = carregar_perfis()
        self._gerar_cartas()
        self.perfis = carregar_perfis()

        cfg = self.app.config
        ult = cfg["ultimo_ovo"]
        if self._mudanca is not None:
            self.sel = self._mudanca
        elif self._saindo is not None and 0 <= self._saindo < 5:
            self.sel = self._saindo
        elif 0 <= ult < 5 and self.perfis[ult].ocupado:
            self.sel = ult
        else:
            ocupados = [p.slot for p in self.perfis if p.ocupado]
            self.sel = ocupados[0] if ocupados else 0
        self.balao = True

        if self._saindo is not None and 0 <= self._saindo < 5 and self.perfis[self._saindo].ocupado:
            self.anim = {"tipo": "sair", "slot": self._saindo, "t": 0.0}
        if self._mudanca is not None and self.perfis[self._mudanca].ocupado:
            p = self.perfis[self._mudanca]
            self.brotar[self._mudanca] = 0.0
            self.boas_vindas = (t("BEM-VINDO, {nome}!", nome=p.nome.upper()), 2.5)
            (ax, ay), s = CASAS[self._mudanca]
            self.particulas.explodir((ax, ay - 90 * s), [p.cor, AMARELO, BRANCO], 50, 380)
            self.som("acerto")
        if self._reformada is not None:
            self.brilho[self._reformada] = 1.5
        if cfg["banner_migracao"]:
            self.banner = 8.0
            cfg["banner_migracao"] = False
            cfg.salvar()
        self._saindo = self._mudanca = self._reformada = None
        self.clima._atualizar_estado()
        self.app.audio.tocar(self.musica)

    @property
    def musica(self):
        if self.clima.chovendo:
            return "dia_de_chuva"
        if self.clima.fase == "noite":
            return "rua_noite"
        return "rua_dos_ovos"

    # --------------------------------------------------------
    # CARTAS DOS VIZINHOS
    # --------------------------------------------------------

    def _gerar_cartas(self):
        """1 carta por dia para cada ovo (com 2 ou mais ovos na rua)."""
        ocupados = [p for p in self.perfis if p.ocupado]
        if len(ocupados) < 2:
            return
        hoje = datetime.date.today().isoformat()
        from jogos import JOGOS
        from core import pets
        from core.fachada import PALETA_PAREDE
        for p in ocupados:
            if p.save["diario"].get("carta_dia") == hoje:
                continue
            outros = [o for o in ocupados if o.slot != p.slot]
            rnd = random.Random(f"{hoje}-{p.slot}")
            de = rnd.choice(outros)
            modelos = []
            jogos_feitos = [(j, de.save.recorde(j.ID)) for j in JOGOS
                            if not getattr(j, "MULTI", False) and not j.OPCOES
                            and isinstance(de.save.recorde(j.ID), (int, float)) and de.save.recorde(j.ID) > 0]
            if jogos_feitos:
                j, v = rnd.choice(jogos_feitos)
                modelos.append(t("OI! AQUI É {nome} DA CASA {casa}. FIZ {valor} NA {jogo}! DUVIDO VOCÊ PASSAR!",
                                 nome=de.nome.upper(), casa=de.slot + 1, valor=j.formatar(v),
                                 jogo=t(j.TITULO_CURTO or j.TITULO).upper()))
            if de.save["pet"] in getattr(pets, "CATALOGO", {}):
                nome_pet = pets.CATALOGO[de.save["pet"]]["nome"]
                modelos.append(t("OI! AQUI É {nome}. ADOTEI UM PET: {pet}! VEM VER!", nome=de.nome.upper(), pet=t(nome_pet)))
            cor = PALETA_PAREDE[de.casa["cor_parede"]][0]
            modelos.append(t("OI! {nome} PINTOU A CASA DE {cor}. FICOU LINDA!", nome=de.nome.upper(), cor=t(cor)))
            modelos.append(t("OI, VIZINHO! AQUI É {nome} DA CASA {casa}. VAMOS JOGAR JUNTOS NO MODO 2 JOGADORES?",
                             nome=de.nome.upper(), casa=de.slot + 1))
            texto = rnd.choice(modelos)
            carta = {"de": de.slot, "nome": de.nome, "texto": texto, "dia": hoje, "lida": False,
                     "apar": list(de.jogador.aparencia())}

            def gravar(save, carta=carta):
                save["diario"]["carta_dia"] = hoje
                cartas = [c for c in save["cartas"] if isinstance(c, dict)]
                cartas.append(carta)
                save["cartas"] = cartas[-10:]
            perfis.modificar_ovo(p.slot, gravar)

    def _abrir_carta(self, slot):
        p = self.perfis[slot]
        novas = [c for c in p.save["cartas"] if isinstance(c, dict) and not c.get("lida")]
        if not novas:
            return False
        self.carta = dict(novas[-1])
        self.modal = "carta"
        self.som("revelar")
        hoje = datetime.date.today().isoformat()

        def ler(save):
            for c in save["cartas"]:
                if isinstance(c, dict):
                    c["lida"] = True
            if save["diario"].get("carta_lida") != hoje:
                save["diario"]["carta_lida"] = hoje
                nec = save["necessidades"] if isinstance(save["necessidades"], dict) else {}
                nec["diversao"] = min(100.0, float(nec.get("diversao", 80)) + 3)
                save["necessidades"] = nec
        perfis.modificar_ovo(slot, ler)
        self.perfis[slot] = type(p)(slot)
        return True

    # --------------------------------------------------------
    # AÇÕES
    # --------------------------------------------------------

    def _entrar_casa(self, slot):
        p = self.perfis[slot]
        if not p.ocupado:
            return
        if self.anim is not None and self.anim["tipo"] == "entrar":
            return
        self.som("selecionar")
        self.anim = {"tipo": "entrar", "slot": slot, "t": 0.0}

    def _concluir_entrada(self, slot):
        from cenas.casa import CenaCasa
        if self.app.carregar_ovo(slot):
            self.app.trocar(CenaCasa(self.app))
        else:
            self._avisar("ESTA CASA ESTÁ EM OBRAS")
            self.perfis = carregar_perfis()

    def _novo(self, slot):
        self.som("selecionar")
        self.app.iniciar_novo_ovo(slot)

    def _reformar(self, slot):
        if not self.perfis[slot].ocupado:
            return
        from cenas.reforma import CenaReforma
        if self.app.carregar_ovo(slot):
            self.som("selecionar")
            self.app.trocar(CenaReforma(self.app, slot))

    def _pedir_apagar(self, slot):
        if self.perfis[slot].estado == "vazio":
            return
        self.modal = "apagar1"
        self.ap_foco = 0
        self.som("erro", 0.6)

    def _apagar(self):
        slot = self.sel
        if perfis.apagar_ovo(slot, self.app.config):
            self.murchar = (slot, 0.0)
            (ax, ay), s = CASAS[slot]
            self.textos.adicionar(t("TCHAU!"), (ax, ay - 200 * s), BRANCO, 16)
            self.som("perder", 0.6)
        else:
            self._avisar("NÃO DEU PARA APAGAR")
            self.perfis = carregar_perfis()
        self.modal = None
        self.segurar = 0.0

    def _avisar(self, msg):
        self.aviso = t(msg)
        self.tempo_aviso = 2.5

    def _acao_principal(self):
        p = self.perfis[self.sel]
        if p.ocupado:
            self._entrar_casa(self.sel)
        elif p.estado == "vazio":
            self._novo(self.sel)
        else:
            self._avisar("ESTA CASA ESTÁ EM OBRAS")

    def _selecionar(self, slot):
        if slot != self.sel:
            self.som("clique", 0.6)
            self.pulo[slot] = 1.0
            if self.clima.fase == "noite":
                self.espiar[slot] = 1.5
        self.sel = slot
        self.balao = True

    # --------------------------------------------------------
    # GEOMETRIA
    # --------------------------------------------------------

    def _hitbox(self, i):
        (ax, ay), s = CASAS[i]
        return pygame.Rect(ax - 125 * s, ay - 200 * s, 250 * s, 225 * s)

    def _casa_em(self, pos):
        for i in sorted(range(5), key=lambda i: -CASAS[i][0][1]):
            if self._hitbox(i).collidepoint(pos):
                return i
        return None

    def _balao_em_cima(self, i):
        return False

    def _rect_balao(self):
        (ax, ay), s = CASAS[self.sel]
        p = self.perfis[self.sel]
        w = 300 if p.estado != "vazio" else 180
        r = pygame.Rect(0, 0, w, 72)
        # Casas 2 e 4: o balão vai um pouco para dentro da ferradura,
        # para não cobrir o telhado e a placa das casas 1 e 5
        desvio = {1: 110, 3: -110}.get(self.sel, 0)
        r.midtop = (ax + desvio, ay + 22 * s)
        r.clamp_ip(pygame.Rect(16, 0, LARGURA - 32, ALTURA))
        return r

    def _botoes_balao(self):
        r = self._rect_balao()
        p = self.perfis[self.sel]
        if p.estado == "vazio":
            return [("novo", pygame.Rect(r.x + 10, r.y + 8, r.w - 20, 40))]
        if p.estado == "corrompido":
            return [("apagar", pygame.Rect(r.x + 254, r.y + 8, 38, 40))]
        return [("entrar", pygame.Rect(r.x + 10, r.y + 8, 130, 40)),
                ("reformar", pygame.Rect(r.x + 148, r.y + 8, 100, 40)),
                ("apagar", pygame.Rect(r.x + 254, r.y + 8, 38, 40))]

    def _pos_placa(self, i):
        (ax, ay), s = CASAS[i]
        p = self.perfis[i]
        topo = fd.topo(p.casa) if p.ocupado else fd.TOPO_TELHADO
        return (ax, max(80, ay + (topo - 22) * s))

    # --------------------------------------------------------
    # EVENTOS
    # --------------------------------------------------------

    def evento(self, e):
        if self.anim is not None and self.anim["tipo"] == "entrar":
            # Clique/tecla pula a animação
            if e.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                self.anim["t"] = 1.0
            return
        if self.modal:
            self._evento_modal(e)
            return

        if e.type == pygame.KEYDOWN:
            k = e.key
            if tecla_voltar(e):
                self.som("voltar")
                from cenas.titulo import CenaTitulo
                self.app.trocar(CenaTitulo(self.app))
            elif k in (pygame.K_LEFT, pygame.K_a):
                self._selecionar((self.sel - 1) % 5)
            elif k in (pygame.K_RIGHT, pygame.K_d, pygame.K_TAB):
                self._selecionar((self.sel + 1) % 5)
            elif k in (pygame.K_UP, pygame.K_w):
                if self.sel < 2:
                    self._selecionar(self.sel + 1)
                elif self.sel > 2:
                    self._selecionar(self.sel - 1)
            elif k in (pygame.K_DOWN, pygame.K_s):
                if self.sel in (1, 2) and self.sel != 2:
                    self._selecionar(self.sel - 1)
                elif self.sel == 3:
                    self._selecionar(4)
            elif k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self._acao_principal()
            elif k == pygame.K_r:
                self._reformar(self.sel)
            elif k in (pygame.K_DELETE, pygame.K_BACKSPACE):
                self._pedir_apagar(self.sel)
            elif k == pygame.K_c:
                if self.perfis[self.sel].ocupado:
                    self._abrir_carta(self.sel)
            return

        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self._clique(e.pos)

    def _clique(self, pos):
        if self.banner > 0:
            self.banner = 0.0
        if self.bt_inicio.collidepoint(pos):
            from cenas.titulo import CenaTitulo
            self.som("voltar")
            self.app.trocar(CenaTitulo(self.app))
            return
        if self.bt_pausa.collidepoint(pos):
            self.modal = "pausa"
            self.som("clique")
            return

        if self.balao:
            for acao, r in self._botoes_balao():
                if r.collidepoint(pos):
                    {"entrar": lambda: self._entrar_casa(self.sel),
                     "reformar": lambda: self._reformar(self.sel),
                     "apagar": lambda: self._pedir_apagar(self.sel),
                     "novo": lambda: self._novo(self.sel)}[acao]()
                    return
            if self._rect_balao().collidepoint(pos):
                return

        # Caixa de correio: abre a carta
        for i, p in enumerate(self.perfis):
            if p.ocupado and p.carta_nova:
                (ax, ay), s = CASAS[i]
                caixa = pygame.Rect(ax + 40 * s, ay - 44 * s, 32 * s, 50 * s)
                if caixa.inflate(10, 10).collidepoint(pos):
                    self._selecionar(i)
                    self._abrir_carta(i)
                    return

        # Veículos (buzina)
        for v in self.veiculos:
            if not v.buzinou and v.rect().collidepoint(pos):
                v.buzinou = True
                self.textos.adicionar(t("BI-BI!"), v.pos(), AMARELO, 12)
                self.som("bater")
                return

        # Fonte da praça
        if math.dist(pos, FONTE) < 70:
            self.particulas.explodir((FONTE[0], FONTE[1] - 60), [(170, 220, 255), BRANCO], 16, 220)
            self.som("ponto")
            return

        i = self._casa_em(pos)
        if i is None:
            self.balao = False
            return
        p = self.perfis[i]
        agora = self.tempo
        if p.estado == "vazio":
            self._selecionar(i)
            self._novo(i)
            return
        duplo = self._ultimo_clique[0] == i and agora - self._ultimo_clique[1] < 0.35
        self._ultimo_clique = (i, agora)
        if duplo and p.ocupado:
            self._entrar_casa(i)
            return
        self._selecionar(i)

    def _evento_modal(self, e):
        if self.modal == "pausa":
            if tecla_voltar(e):
                self.modal = None
                return
            escolha = self.menu_pausa.evento(e)
            if escolha == 0:
                self.modal = None
            elif escolha == 1:
                from cenas.pausa import CenaOpcoes
                self.modal = None
                self.app.trocar(CenaOpcoes(self.app, self, self), fade=False)
            elif escolha == 2:
                self.app.sair()
            return

        if self.modal == "carta":
            if e.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                self.modal = None
                self.som("voltar")
            return

        if self.modal == "apagar1":
            if tecla_voltar(e) or (e.type == pygame.KEYDOWN and e.key == pygame.K_n):
                self.modal = None
                self.som("voltar")
            elif e.type == pygame.KEYDOWN and e.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_a,
                                                         pygame.K_d, pygame.K_TAB):
                self.ap_foco = 1 - self.ap_foco
            elif e.type == pygame.KEYDOWN and e.key in (pygame.K_RETURN, pygame.K_KP_ENTER,
                                                         pygame.K_SPACE):
                if self.ap_foco == 0:
                    self.modal = None
                    self.som("voltar")
                else:
                    self._ir_para_apagar2()
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if self.ap_nao.collidepoint(e.pos):
                    self.modal = None
                    self.som("voltar")
                elif self.ap_sim.collidepoint(e.pos):
                    self._ir_para_apagar2()
            return

        if self.modal == "apagar2":
            if tecla_voltar(e):
                self.modal = None
                self.segurar = 0.0
                self.som("voltar")
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 \
                    and self.ap_cancelar.collidepoint(e.pos):
                self.modal = None
                self.segurar = 0.0
                self.som("voltar")

    def _ir_para_apagar2(self):
        self.modal = "apagar2"
        self.segurar = 0.0
        self._ultimo_segundo = 0
        # Tecla ainda apertada do passo 1 não conta: precisa soltar antes
        self._precisa_soltar = True
        self.som("erro", 0.6)

    # --------------------------------------------------------
    # ATUALIZAÇÃO
    # --------------------------------------------------------

    def atualizar(self, dt):
        self.tempo += dt
        self.clima.atualizar(dt)
        self.nuvens.atualizar(dt, self.clima.vento)
        self.particulas.atualizar(dt)
        self.textos.atualizar(dt)
        self.tempo_aviso = max(0.0, self.tempo_aviso - dt)
        self.banner = max(0.0, self.banner - dt)
        self.pulo = [max(0.0, v - dt * 2) for v in self.pulo]
        self.espiar = [max(0.0, v - dt) for v in self.espiar]
        for k in list(self.brotar):
            self.brotar[k] += dt
            if self.brotar[k] > 0.8:
                del self.brotar[k]
        for k in list(self.brilho):
            self.brilho[k] -= dt
            if self.brilho[k] <= 0:
                del self.brilho[k]
        if self.boas_vindas:
            txt, tt = self.boas_vindas
            self.boas_vindas = (txt, tt - dt) if tt - dt > 0 else None
        if self.murchar:
            slot, t = self.murchar
            t += dt
            if t >= 0.6:
                self.murchar = None
                self.perfis = carregar_perfis()
                (ax, ay), s = CASAS[slot]
                self.particulas.explodir((ax, ay - 20), [(230, 230, 230), (200, 190, 170)], 24, 200)
            else:
                self.murchar = (slot, t)

        self.app.audio.tocar(self.musica)

        # Animação da porta
        if self.anim is not None:
            self.anim["t"] += dt / (0.6 if self.anim["tipo"] == "entrar" else 0.5)
            if self.anim["t"] >= 1.0:
                a, self.anim = self.anim, None
                if a["tipo"] == "entrar":
                    self._concluir_entrada(a["slot"])

        # Hover
        pos = pygame.mouse.get_pos()
        self.hover = None if self.modal else self._casa_em(pos)

        # Segurar para apagar
        if self.modal == "apagar2":
            mouse = pygame.mouse.get_pressed()[0] and self.ap_segurar.collidepoint(pos)
            teclas = pygame.key.get_pressed()
            tecla = teclas[pygame.K_DELETE] or teclas[pygame.K_RETURN] or teclas[pygame.K_KP_ENTER]
            if getattr(self, "_precisa_soltar", False):
                if not tecla and not pygame.mouse.get_pressed()[0]:
                    self._precisa_soltar = False
                mouse = tecla = False
            if mouse or tecla:
                self.segurar += dt
                seg = int(self.segurar)
                if seg > self._ultimo_segundo:
                    self._ultimo_segundo = seg
                    self.som("ponto")
                if self.segurar >= TEMPO_SEGURAR:
                    self._apagar()
            else:
                self.segurar = max(0.0, self.segurar - dt * TEMPO_SEGURAR / 0.4)
                self._ultimo_segundo = int(self.segurar)
        elif self.modal == "pausa":
            self.menu_pausa.atualizar(dt)

        # Veículos
        self.prox_veiculo -= dt
        if self.prox_veiculo <= 0:
            self.prox_veiculo = self.rnd.uniform(7, 14)
            self.veiculos.append(Veiculo(self.rnd))
        for v in self.veiculos:
            v.atualizar(dt)
        self.veiculos = [v for v in self.veiculos if not v.fora]

        # Pássaros (de dia, sem chuva)
        if self.passaros:
            self.passaros["x"] += 90 * dt * self.passaros["dir"]
            if not -80 < self.passaros["x"] < LARGURA + 80:
                self.passaros = None
        else:
            self.prox_passaros -= dt
            if self.prox_passaros <= 0:
                self.prox_passaros = self.rnd.uniform(15, 25)
                if self.clima.fase != "noite" and not self.clima.chovendo:
                    d = self.rnd.choice((-1, 1))
                    self.passaros = {"x": -60 if d > 0 else LARGURA + 60, "y": self.rnd.uniform(30, 105),
                                     "dir": d}

    # --------------------------------------------------------
    # DESENHO
    # --------------------------------------------------------

    def _desenhar_fundo(self):
        fase = self.clima.fase
        nublado = self.clima.tipo != "sol"
        chave = (fase, nublado)
        if self._chave_fundo == chave:
            return self._fundo
        sup = pygame.Surface((LARGURA, ALTURA))
        sup.blit(ceu.gradiente(fase, LARGURA, Y_CEU + 20, nublado), (0, 0))
        # Colinas
        for cor, base, amp, f in (((150, 205, 130), 118, 10, 0.3), ((165, 215, 145), 132, 8, 2.1)):
            pts = [(0, ALTURA)]
            for x in range(0, LARGURA + 17, 16):
                pts.append((x, base + amp * math.sin(x / LARGURA * 4 * math.pi + f)))
            pts.append((LARGURA, ALTURA))
            pygame.draw.polygon(sup, cor, pts)
        # Gramado com listras de corte
        grama = pygame.Surface((LARGURA, ALTURA - Y_CEU - 12))
        grama.fill((190, 228, 170))
        for x in range(-ALTURA, LARGURA, 48):
            pygame.draw.polygon(grama, (196, 233, 176), [(x, 0), (x + 24, 0), (x + 24 + ALTURA, ALTURA),
                                                           (x + ALTURA, ALTURA)])
        sup.blit(grama, (0, Y_CEU + 12))
        rnd = random.Random(14)
        for _ in range(120):
            x, y = rnd.randrange(LARGURA), rnd.randrange(Y_CEU + 20, ALTURA)
            pygame.draw.line(sup, (160, 205, 140), (x, y), (x - 3, y - 6), 2)
            pygame.draw.line(sup, (160, 205, 140), (x, y), (x + 3, y - 6), 2)
        for _ in range(30):
            x, y = rnd.randrange(LARGURA), rnd.randrange(Y_CEU + 20, ALTURA)
            pygame.draw.rect(sup, rnd.choice([(255, 255, 255), (255, 230, 90)]), (x, y, 2, 2))

        self._desenhar_rua(sup)
        self._desenhar_praca(sup)
        for (x, y), r in ARVORES:
            self._arvore(sup, x, y, r)
        self._fundo, self._chave_fundo = sup, chave
        return sup

    def _desenhar_rua(self, sup):
        n = 90
        thetas = [math.pi * (1 - i / n) for i in range(n + 1)]
        # Estende as pontas para fora da tela
        ext = [-0.25] + [0.0] + [math.pi]
        thetas = [math.pi + 0.25] + thetas + [-0.25]
        fora = [borda_rua(t, 1) for t in thetas]
        dentro = [borda_rua(t, -1) for t in thetas]
        pygame.draw.polygon(sup, (44, 44, 52), fora + dentro[::-1])
        pygame.draw.lines(sup, (200, 200, 205), False, fora, 4)
        pygame.draw.lines(sup, (200, 200, 205), False, dentro, 4)
        del ext
        # Faixa tracejada medida ao longo do arco
        centro = [ponto_rua(t) for t in thetas]
        dist = 0.0
        for a, b in zip(centro, centro[1:]):
            seg = math.dist(a, b)
            passos = max(1, int(seg / 2))
            for k in range(passos):
                d = dist + seg * k / passos
                if (d % 34) < 18:
                    f0, f1 = k / passos, (k + 1) / passos
                    p0 = (a[0] + (b[0] - a[0]) * f0, a[1] + (b[1] - a[1]) * f0)
                    p1 = (a[0] + (b[0] - a[0]) * f1, a[1] + (b[1] - a[1]) * f1)
                    esp = round(3 + max(0, p0[1] - 330) / 390)
                    pygame.draw.line(sup, (255, 214, 64), p0, p1, esp)
            dist += seg

    def _desenhar_praca(self, sup):
        # Canteiros redondos
        rnd = random.Random(3)
        for cx, cy in ((380, 640), (644, 640)):
            pygame.draw.ellipse(sup, (120, 80, 45), (cx - 35, cy - 11, 70, 22))
            for i in range(6):
                fx = cx - 24 + i * 10
                fy = cy - 2 + (i % 2) * 4
                cor = rnd.choice([(255, 90, 120), (255, 220, 60), (170, 110, 240), (255, 255, 255)])
                pygame.draw.line(sup, (70, 150, 60), (fx, fy + 4), (fx, fy - 6), 2)
                pygame.draw.circle(sup, cor, (fx, fy - 7), 4)
        # Bacia da fonte (a água e os jatos são animados)
        pygame.draw.ellipse(sup, (205, 205, 215), (412, 548, 200, 56))
        pygame.draw.ellipse(sup, (160, 160, 175), (412, 548, 200, 56), 4)

    @staticmethod
    def _arvore(sup, x, y, r):
        pygame.draw.rect(sup, (120, 80, 45), (x - 5, y, 10, 30))
        for dx, dy, rr in ((0, -r * 0.4, r), (-r * 0.6, 0, r * 0.75), (r * 0.6, 0, r * 0.75)):
            pygame.draw.circle(sup, (70, 160, 75), (x + dx, y + dy), rr)
        pygame.draw.circle(sup, (95, 185, 90), (x - r * 0.3, y - r * 0.6), r * 0.35)

    # --------------------------------------------------------
    # NÍVEL DA VILA: a soma dos níveis dos ovos enfeita a praça
    # --------------------------------------------------------
    MARCOS_VILA = [(3, "BANDEIRINHAS"), (8, "LAMPIÕES"), (15, "ESTÁTUA DO OVO DOURADO"),
                   (25, "ARCO DE FLORES"), (40, "FOGOS TODA NOITE")]

    def nivel_vila(self):
        return sum(max(1, p.save["nivel"]) for p in self.perfis if p.ocupado and p.save is not None)

    def _desenhar_vila(self, tela, noite):
        nv = self.nivel_vila()
        t = self.tempo
        if nv >= 25:
            # Arco de flores atrás da fonte
            for i in range(19):
                a = math.pi + i * math.pi / 18
                x, y = 512 + math.cos(a) * 120, 560 + math.sin(a) * 90
                cor = [(255, 120, 170), (255, 220, 80), (170, 120, 255), (255, 255, 255)][i % 4]
                pygame.draw.circle(tela, (70, 150, 60), (int(x), int(y)), 9)
                pygame.draw.circle(tela, cor, (int(x), int(y)), 6)
        if nv >= 3:
            # Bandeirinhas entre os postes da praça
            for lado in (-1, 1):
                x0, x1 = 512 + lado * 40, 512 + lado * 150
                for i in range(8):
                    f = i / 7
                    x = x0 + (x1 - x0) * f
                    y = 470 + math.sin(f * math.pi) * 22 + math.sin(t * 2 + i) * 1.5
                    cor = [(230, 60, 60), (255, 214, 64), (60, 150, 230), (90, 200, 90)][i % 4]
                    pygame.draw.polygon(tela, cor, [(x - 6, y), (x + 6, y), (x, y + 12)])
                pygame.draw.line(tela, (90, 70, 50), (x0, 470), (x1, 470), 1)
        if nv >= 8:
            for x in (398, 626):
                pygame.draw.rect(tela, (60, 60, 70), (x - 3, 520, 6, 60))
                pygame.draw.rect(tela, (40, 40, 50), (x - 9, 510, 18, 14), border_radius=4)
                cor = (255, 230, 140) if noite else (230, 230, 200)
                pygame.draw.circle(tela, cor, (x, 517), 6)
                if noite:
                    ui.estrela(tela, (x, 517), 12 + math.sin(t * 3) * 2, (255, 240, 170), t)
        if nv >= 15:
            # Estatuazinha dourada no topo da fonte
            ovo = pygame.Rect(0, 0, 26, 32)
            ovo.midbottom = (512, 512)
            pygame.draw.ellipse(tela, (200, 150, 30), ovo.move(2, 2))
            pygame.draw.ellipse(tela, (255, 214, 64), ovo)
            pygame.draw.ellipse(tela, (255, 245, 180), (ovo.x + 5, ovo.y + 5, 7, 10))
        if nv >= 40 and noite and int(t * 1.5) % 4 == 0 and random.random() < 0.08:
            self.particulas.explodir((random.randint(200, 820), random.randint(60, 200)),
                                     [(255, 120, 170), AMARELO, (120, 200, 255), BRANCO], 30, 220, 1.2,
                                     (2, 4), 60)
        # Placa da vila
        placa = pygame.Rect(0, 0, 150, 26)
        placa.center = (512, 626)
        pygame.draw.rect(tela, (120, 80, 45), placa, border_radius=6)
        pygame.draw.rect(tela, (80, 50, 25), placa, 2, border_radius=6)
        ui.desenhar_texto(tela, idioma.t("VILA NÍVEL {n}", n=nv), placa.center, 8, (255, 240, 200), "center")
        proximo = next((m for m in self.MARCOS_VILA if m[0] > nv), None)
        if proximo and pygame.Rect(placa).inflate(20, 20).collidepoint(pygame.mouse.get_pos()):
            ui.desenhar_texto(tela, idioma.t("NÍVEL {n}: {marco}", n=proximo[0], marco=idioma.t(proximo[1])), (512, 604), 8, AMARELO, "midbottom")

    def _desenhar_fonte(self, tela):
        pygame.draw.ellipse(tela, (110, 190, 250), (424, 556, 176, 40))
        for i in range(3):
            a = self.tempo * 0.8 + i * 2.1
            cx = 512 + math.cos(a) * 50
            cy = 576 + math.sin(a) * 9
            pygame.draw.arc(tela, (170, 225, 255), (cx - 14, cy - 4, 28, 8), 0, math.pi, 2)
        pygame.draw.rect(tela, (215, 215, 225), (504, 520, 16, 40))
        pygame.draw.ellipse(tela, (205, 205, 215), (488, 512, 48, 14))
        for i in range(12):
            f = (self.tempo / 1.2 + i / 12) % 1.0
            ang = i * math.tau / 12
            dx = math.cos(ang) * 60 * f
            dy = -30 * math.sin(f * math.pi) + 50 * f * f + math.sin(ang) * 8 * f
            pygame.draw.circle(tela, (190, 230, 255), (512 + dx, 508 + dy), 3)

    def desenhar(self, tela):
        fase = self.clima.fase
        noite = fase == "noite"
        nublado = self.clima.tipo != "sol"
        tela.blit(self._desenhar_fundo(), (0, 0))
        self.ceu.desenhar(tela, fase, self.tempo, sol=(120, 62), lua=(880, 60), nublado=nublado)
        # O sol/lua não pode passar da faixa do céu
        self.nuvens.desenhar(tela, cinza=nublado)
        self._desenhar_passaros(tela)

        if self.clima.chovendo:
            self._pocas(tela)

        # Calçadinhas até a rua
        for i, p in enumerate(self.perfis):
            if p.ocupado:
                (ax, ay), s = CASAS[i]
                a, b = self.caminhos[i]
                fd.desenhar_caminho(tela, a, b, 26 * s, p.casa["caminho"], self.tempo)

        self._desenhar_fonte(tela)
        self._desenhar_vila(tela, noite)

        # Destaque da casa selecionada
        if not self.modal:
            (ax, ay), s = CASAS[self.sel]
            alpha = int(95 + 25 * math.sin(self.tempo * 4 * math.pi / 2)) // 10 * 10
            cache = getattr(self, "_sel_cache", None)
            if cache is None:
                cache = self._sel_cache = {}
            sel = cache.get((self.sel, alpha))
            if sel is None:
                sel = pygame.Surface((round(270 * s), round(40 * s)), pygame.SRCALPHA)
                pygame.draw.ellipse(sel, (255, 240, 150, alpha), sel.get_rect())
                cache[(self.sel, alpha)] = sel
            tela.blit(sel, sel.get_rect(center=(ax, ay + 2 * s)))

        # Casas, ovos e carros por ordem de profundidade (y)
        desenhos = []
        for i in range(5):
            desenhos.append((CASAS[i][0][1], 0, i))
        for v in self.veiculos:
            desenhos.append((v.pos()[1] - 10, 1, v))
        desenhos.sort(key=lambda d: (d[0], d[1]))
        for _, tipo, obj in desenhos:
            if tipo == 0:
                self._desenhar_casa(tela, obj, noite)
            else:
                obj.desenhar(tela)

        self.particulas.desenhar(tela)

        # Chuva
        if self.clima.chovendo:
            for x, y, v in self.clima.gotas:
                pygame.draw.line(tela, (170, 200, 255), (x, y), (x - 5, y + 16), 2)

        # Véu da hora do dia (o céu já tem a cor certa) e luzes por cima
        veu = VEUS.get(fase)
        if veu:
            if self._veu is None or self._veu[0] != veu:
                s = pygame.Surface((LARGURA, ALTURA - Y_CEU))
                s.fill(veu[0])
                s.set_alpha(veu[1])
                self._veu = (veu, s)
            tela.blit(self._veu[1], (0, Y_CEU))
            if fase in ("noite", "por_do_sol"):
                for i, p in enumerate(self.perfis):
                    if p.ocupado:
                        (ax, ay), s = CASAS[i]
                        if i not in self.brotar and not (self.murchar and self.murchar[0] == i):
                            fd.desenhar_luzes(tela, (ax, ay), s, p.casa, p.cor, self.tempo,
                                              dormindo=p.dormindo)
                        if self.espiar[i] > 0:
                            self._espiar(tela, i)

        self._desenhar_placas(tela)
        self.textos.desenhar(tela)
        self._desenhar_hud(tela)
        if self.balao and not self.modal and self.anim is None and not self.murchar:
            self._desenhar_balao(tela)
        if self.hover is not None and not self.modal and self.anim is None:
            self._desenhar_tooltip(tela, self.hover)
        if self.boas_vindas:
            txt, tt = self.boas_vindas
            (ax, ay), s = CASAS[self.sel]
            sup = ui.texto(txt, 20, AMARELO)
            r = sup.get_rect(center=(ax, ay - 250 * s))
            r.clamp_ip(pygame.Rect(20, 80, LARGURA - 40, ALTURA))
            ui.painel(tela, r.inflate(28, 18), (32, 36, 58), AMARELO, 12, 3)
            tela.blit(sup, r)
        if self.banner > 0:
            self._desenhar_banner(tela)
        if self.tempo_aviso > 0:
            sup = ui.texto(self.aviso, 12, AMARELO)
            r = sup.get_rect(center=(LARGURA // 2, 660)).inflate(28, 18)
            ui.painel(tela, r, (20, 24, 40), AMARELO, 12, 2, sombra=False)
            tela.blit(sup, sup.get_rect(center=r.center))
        if self.modal:
            self._desenhar_modal(tela)

    def _pocas(self, tela):
        for i, th in enumerate((2.9, 2.5, 2.0, 1.2, 0.7, 0.3)):
            x, y = borda_rua(th, 0.35 if i % 2 else -0.35)
            w = 30 + (i * 13) % 30
            poca = pygame.Surface((w, 10), pygame.SRCALPHA)
            pygame.draw.ellipse(poca, (80, 90, 115, 120), poca.get_rect())
            tela.blit(poca, (x - w / 2, y - 5))
            f = (self.tempo / 0.9 + i * 0.37) % 1.0
            r = 2 + 8 * f
            pygame.draw.ellipse(tela, (220, 230, 255), (x - r, y - r / 3, r * 2, r * 2 / 3), 1)

    def _desenhar_passaros(self, tela):
        if not self.passaros:
            return
        b = self.passaros
        abre = 4 + 3 * math.sin(self.tempo * 12)
        for k, (dx, dy) in enumerate(((0, 0), (-18, 8), (-30, -6))):
            x = b["x"] + dx * b["dir"]
            y = b["y"] + dy
            pygame.draw.line(tela, (60, 60, 70), (x - 5, y - abre), (x, y), 2)
            pygame.draw.line(tela, (60, 60, 70), (x, y), (x + 5, y - abre), 2)

    # ---------------- casa + ovo ----------------

    def _desenhar_casa(self, tela, i, noite):
        p = self.perfis[i]
        (ax, ay), s = CASAS[i]
        if self.murchar and self.murchar[0] == i:
            f = 1 - self.murchar[1] / 0.6
            fd.desenhar_casa(tela, (ax, ay), s, p.casa, p.cor, noite, self.tempo, escala_y=f)
            return
        if not p.ocupado:
            fd.desenhar_lote_vazio(tela, (ax, ay), s, self.tempo, hover=(self.hover == i),
                                   em_obras=(p.estado == "corrompido"))
            return
        esc_y = 1.0
        if i in self.brotar:
            t = self.brotar[i] / 0.8
            esc_y = min(1.15, t * 1.15 / 0.6) if t < 0.6 else 1.15 - 0.15 * (t - 0.6) / 0.4
        fd.desenhar_casa(tela, (ax, ay), s, p.casa, p.cor, noite, self.tempo,
                         dormindo=p.dormindo, vento=self.clima.vento, carta=p.carta_nova,
                         escala_y=esc_y)
        if i in self.brilho:
            for k in range(4):
                f = ((1.5 - self.brilho[i]) / 1.5 + k / 4) % 1.0
                ui.estrela(tela, (ax - 60 * s + k * 40 * s, ay - 60 * s - f * 120 * s), 6, AMARELO,
                           self.tempo * 3)

        # O ovo fica dentro de casa à noite
        anim = self.anim if (self.anim and self.anim["slot"] == i) else None
        if noite and anim is None:
            return
        self._desenhar_ovo(tela, i, p, anim)

    def _pos_ovo(self, i, p):
        (ax, ay), s = CASAS[i]
        itens = p.casa["itens"]
        if itens.get("esq") == "banco":
            return ax - 100 * s, ay - 14 * s, True
        if itens.get("dir") == "banco":
            return ax + 100 * s, ay - 14 * s, True
        return ax - 50 * s, ay + 14 * s, False

    def _desenhar_ovo(self, tela, i, p, anim):
        (ax, ay), s = CASAS[i]
        x, chao, sentado = self._pos_ovo(i, p)
        altura = round(60 * s * (0.9 if sentado else 1.0))
        esc = 1.0
        if anim is not None:
            t = max(0.0, min(1.0, anim["t"]))
            f = t if anim["tipo"] == "entrar" else 1 - t
            x = x + (ax - x) * f
            chao = chao + (ay - chao) * f
            esc = 1 - 0.5 * f
            if f > 0.95:
                return
        pulo = math.sin(self.pulo[i] * math.pi) * 20 * s if self.pulo[i] > 0 else 0
        resp = 1 + 0.02 * math.sin(self.tempo * 3 * math.pi + i)
        h = max(8, round(altura * esc * resp))
        if self.clima.chovendo and anim is None and "capa_chuva" not in p.save["equipado"].values():
            self._guarda_chuva(tela, (x, chao - h - pulo), h, p.cor)
        espelhar = (math.sin(self.tempo * 0.4 + i * 2) > 0.85)
        p.jogador.desenhar(tela, (x, chao - h / 2 - pulo), h, espelhar=espelhar)
        if p.save["pet"] and anim is None:
            self.app.desenhar_pet_de(tela, p.save["pet"], (ax - 14 * s, ay + 24 * s), 0.45 * s,
                                     feliz=(i == self.sel))

    @staticmethod
    def _guarda_chuva(tela, topo, h, cor):
        x, y = topo
        r = h * 0.75
        pygame.draw.line(tela, (80, 60, 40), (x, y - r * 0.55), (x, y + h * 0.4), 2)
        pts = [(x - r, y - r * 0.2)]
        for k in range(9):
            a = math.pi * k / 8
            pts.append((x - r * math.cos(a), y - r * 0.2 - r * 0.6 * math.sin(a)))
        pts.append((x + r, y - r * 0.2))
        pygame.draw.polygon(tela, cor, pts)
        pygame.draw.polygon(tela, ui.escurecer(cor, 60), pts, 2)

    def _espiar(self, tela, i):
        p = self.perfis[i]
        (ax, ay), s = CASAS[i]
        luz = pygame.Surface((round(80 * s), round(30 * s)), pygame.SRCALPHA)
        pygame.draw.polygon(luz, (255, 220, 130, 80), [(luz.get_width() * 0.35, 0),
                                                         (luz.get_width() * 0.65, 0),
                                                         (luz.get_width(), luz.get_height()),
                                                         (0, luz.get_height())])
        tela.blit(luz, luz.get_rect(midtop=(ax, ay)))
        h = round(52 * s)
        area = pygame.Rect(ax - 16 * s, ay - 54 * s, 32 * s, 54 * s)
        tela.set_clip(area)
        p.jogador.desenhar(tela, (ax - 8 * s, ay - h / 2), h)
        tela.set_clip(None)

    # ---------------- placas / balões ----------------

    def _desenhar_placas(self, tela):
        for i, p in enumerate(self.perfis):
            if self.murchar and self.murchar[0] == i:
                continue
            x, y = self._pos_placa(i)
            sel = (i == self.sel and not self.modal)
            if p.estado == "vazio":
                ui.desenhar_texto(tela, t("CASA {n} • LIVRE", n=i + 1), (x, y), 8, (70, 100, 70), "center", False)
                continue
            if p.estado == "corrompido":
                ui.desenhar_texto(tela, t("EM OBRAS"), (x, y), 10, (200, 120, 30), "center", False)
                continue
            tam = 12 if sel else 10
            nome = ui.texto(p.nome, tam, (60, 40, 30), sombra=False)
            dy = math.sin(self.tempo * 4) * 3 if sel else 0
            r = pygame.Rect(0, 0, nome.get_width() + 34, 24)
            r.center = (x, y + dy)
            pygame.draw.rect(tela, (0, 0, 0), r.move(2, 3), border_radius=6)
            pygame.draw.rect(tela, (255, 214, 64) if sel else (255, 248, 230), r, border_radius=6)
            pygame.draw.rect(tela, (120, 80, 40), r, 2, border_radius=6)
            ovo = pygame.Rect(r.x + 8, r.centery - 6, 10, 12)
            pygame.draw.ellipse(tela, p.cor, ovo)
            pygame.draw.ellipse(tela, ui.escurecer(p.cor, 80), ovo, 1)
            tela.blit(nome, nome.get_rect(midleft=(r.x + 24, r.centery)))
            if sel and not (self.balao and self._balao_em_cima(i)):
                ui.desenhar_texto(tela, "↓", (x, r.y - 14 + dy), 16, AMARELO, "center")
            if p.status[2]:
                bx, by = r.right + 12, r.centery + math.sin(self.tempo * 6) * 2
                pygame.draw.circle(tela, (255, 214, 64), (bx, by), 9)
                pygame.draw.circle(tela, (150, 100, 0), (bx, by), 9, 2)
                ui.desenhar_texto(tela, "!", (bx + 1, by + 1), 10, (60, 40, 10), "center", False)

    def _desenhar_balao(self, tela):
        r = self._rect_balao()
        (ax, ay), s = CASAS[self.sel]
        ui.painel(tela, r, (32, 36, 58), BRANCO, 12, 2)
        bx = max(r.x + 16, min(r.right - 16, ax))
        if self._balao_em_cima(self.sel):
            pygame.draw.polygon(tela, (32, 36, 58), [(bx - 9, r.bottom - 2), (bx + 9, r.bottom - 2),
                                                     (bx, r.bottom + 10)])
            pygame.draw.lines(tela, BRANCO, False, [(bx - 9, r.bottom), (bx, r.bottom + 10),
                                                    (bx + 9, r.bottom)], 2)
        else:
            pygame.draw.polygon(tela, (32, 36, 58), [(bx - 9, r.y + 2), (bx + 9, r.y + 2), (bx, r.y - 10)])
            pygame.draw.lines(tela, BRANCO, False, [(bx - 9, r.y), (bx, r.y - 10), (bx + 9, r.y)], 2)
        mouse = pygame.mouse.get_pos()
        estilos = {"entrar": ((70, 170, 90), "ENTRAR", 12, "ENTER"),
                   "reformar": ((230, 140, 50), "REFORMAR", 10, "R"),
                   "apagar": ((170, 60, 60), "", 10, "DEL"),
                   "novo": ((70, 170, 90), "+NOVO", 14, "ENTER")}
        for acao, b in self._botoes_balao():
            cor, txt, tam, dica = estilos[acao]
            hover = b.collidepoint(mouse)
            pygame.draw.rect(tela, ui.clarear(cor, 30) if hover else cor, b, border_radius=10)
            pygame.draw.rect(tela, BRANCO, b, 2, border_radius=10)
            if acao == "apagar":
                cx, cy = b.center
                pygame.draw.rect(tela, BRANCO, (cx - 7, cy - 6, 14, 16), border_radius=2)
                pygame.draw.rect(tela, BRANCO, (cx - 9, cy - 10, 18, 3))
                pygame.draw.rect(tela, BRANCO, (cx - 3, cy - 13, 6, 3))
                for k in (-3, 0, 3):
                    pygame.draw.line(tela, cor, (cx + k, cy - 3), (cx + k, cy + 7), 1)
            else:
                ui.desenhar_texto(tela, t(txt), b.center, tam, BRANCO, "center")
            ui.desenhar_texto(tela, dica, (b.centerx, b.bottom + 11), 8, (230, 230, 240), "center")

    def _desenhar_tooltip(self, tela, i):
        p = self.perfis[i]
        (ax, ay), s = CASAS[i]
        px, py = self._pos_placa(i)
        if p.estado == "vazio":
            linhas = ui.quebrar_linhas(t("CASA LIVRE! CLIQUE EM +NOVO PARA TER UM OVO AQUI."), 8, 200)
            r = pygame.Rect(0, 0, 220, 20 + 14 * len(linhas))
        elif p.estado == "corrompido":
            linhas = ui.quebrar_linhas(t("ESTA CASA ESTÁ EM OBRAS (O ARQUIVO DO OVO ESTÁ ESTRAGADO)."), 8, 200)
            r = pygame.Rect(0, 0, 220, 20 + 14 * len(linhas))
        else:
            linhas = None
            r = pygame.Rect(0, 0, 260, 140)
        # Ao lado da casa (em cima ficam a placa e o balão)
        r.centery = ay - 100 * s
        if ax <= LARGURA // 2:
            r.left = ax + 130 * s
        else:
            r.right = ax - 130 * s
        r.clamp_ip(pygame.Rect(8, 64, LARGURA - 16, ALTURA - 100))
        ui.painel(tela, r, (32, 36, 58), BRANCO, 12, 2)
        if linhas is not None:
            for k, l in enumerate(linhas):
                ui.desenhar_texto(tela, l, (r.centerx, r.y + 12 + k * 14), 8, BRANCO, "midtop")
            return
        p.jogador.desenhar(tela, (r.x + 28, r.y + 28), 34)
        ui.desenhar_texto(tela, p.nome, (r.x + 52, r.y + 12), 12, AMARELO)
        ui.desenhar_moedas(tela, p.save["moedas"], (r.x + 52, r.y + 32), "topleft", 10)
        if p.save["pet"]:
            from core import pets
            nome_pet = pets.CATALOGO.get(p.save["pet"], {}).get("nome", "")
            if nome_pet:
                ui.desenhar_texto(tela, t("PET: ") + t(nome_pet), (r.right - 10, r.y + 36), 8,
                                  (230, 230, 240), "topright")
        from core.necessidades import ROTULOS
        for k, (nome, v) in enumerate(p.necessidades.items()):
            x = r.x + 12 + (k % 2) * 124
            y = r.y + 70 + (k // 2) * 18
            ui.desenhar_texto(tela, t(ROTULOS[nome])[:4], (x, y), 8, (230, 230, 240))
            cor = (230, 70, 70) if v < 30 else ((255, 200, 60) if v < 70 else (90, 200, 90))
            pygame.draw.rect(tela, (20, 24, 40), (x + 44, y, 60, 8), border_radius=3)
            pygame.draw.rect(tela, cor, (x + 44, y, round(60 * v / 100), 8), border_radius=3)
        txt, cor, _ = p.status
        ui.desenhar_texto(tela, t(txt), (r.centerx, r.bottom - 14), 8, cor, "center")

    def _desenhar_hud(self, tela):
        mouse = pygame.mouse.get_pos()
        hover = self.bt_inicio.collidepoint(mouse)
        ui.painel(tela, self.bt_inicio, (70, 80, 130) if hover else (30, 36, 60), BRANCO, 12, 3)
        ui.desenhar_texto(tela, t("← INÍCIO"), self.bt_inicio.center, 12, BRANCO, "center")
        titulo = pygame.Rect(362, 12, 300, 46)
        ui.painel(tela, titulo, (30, 36, 60), BRANCO, 14, 3)
        ui.desenhar_texto(tela, t("RUA DOS OVOS"), titulo.center, 16, AMARELO, "center")
        hover = self.bt_pausa.collidepoint(mouse)
        ui.painel(tela, self.bt_pausa, (70, 80, 130) if hover else (30, 36, 60), BRANCO, 12, 3)
        cx, cy = self.bt_pausa.center
        pygame.draw.rect(tela, BRANCO, (cx - 9, cy - 11, 6, 22), border_radius=2)
        pygame.draw.rect(tela, BRANCO, (cx + 3, cy - 11, 6, 22), border_radius=2)
        ajuda = pygame.Rect(212, 684, 600, 30)
        fundo = pygame.Surface(ajuda.size, pygame.SRCALPHA)
        pygame.draw.rect(fundo, (20, 24, 40, 200), fundo.get_rect(), border_radius=12)
        tela.blit(fundo, ajuda)
        ui.desenhar_texto(tela, t(AJUDA), ajuda.center, 8, BRANCO, "center")

    def _desenhar_banner(self, tela):
        msg = t("BEM-VINDO À RUA DOS OVOS! SUA CASA É A 1. CLIQUE EM +NOVO PARA TER MAIS OVOS.")
        linhas = ui.quebrar_linhas(msg, 10, 700)
        r = pygame.Rect(0, 0, 740, 20 + 18 * len(linhas))
        r.midtop = (LARGURA // 2, 72)
        ui.painel(tela, r, (32, 36, 58), AMARELO, 12, 3)
        for k, l in enumerate(linhas):
            ui.desenhar_texto(tela, l, (r.centerx, r.y + 12 + k * 18), 10, BRANCO, "midtop")

    # ---------------- modais ----------------

    def _desenhar_modal(self, tela):
        ui.veu(tela, 170)
        if self.modal == "pausa":
            caixa = pygame.Rect(0, 0, 440, 330)
            caixa.midtop = (LARGURA // 2, 160)
            ui.painel(tela, caixa, (30, 34, 60), BRANCO, 20, 4)
            ui.desenhar_texto(tela, t("PAUSADO"), (LARGURA // 2, 190), 24, AMARELO, "midtop")
            self.menu_pausa.desenhar(tela)
            return
        if self.modal == "carta":
            self._desenhar_carta(tela)
            return

        p = self.perfis[self.sel]
        caixa = pygame.Rect(0, 0, 640, 320)
        caixa.center = (LARGURA // 2, ALTURA // 2)
        ui.painel(tela, caixa, (40, 30, 50), (255, 120, 120), 20, 4)
        if p.jogador:
            balanco = math.sin(self.tempo * 2) * 4
            from core.jogador import BOCA_TRISTE
            apar = list(p.jogador.aparencia())
            apar[3] = BOCA_TRISTE
            p.jogador.desenhar(tela, (caixa.x + 100, caixa.centery + balanco), 90, aparencia=tuple(apar))
        nome = (p.nome or t("ESTE OVO")).upper()
        if self.modal == "apagar1":
            ui.desenhar_texto(tela, t("APAGAR ESTE OVO?"), (caixa.centerx + 60, caixa.y + 30), 20,
                              (255, 120, 120), "midtop")
            msg = t("{nome} VAI SE MUDAR PARA SEMPRE. AS OVOEDAS, ROUPAS, PETS, "
                    "PLANTAS E RECORDES DELE VÃO JUNTO.", nome=nome)
            for k, l in enumerate(ui.quebrar_linhas(msg, 10, 380)):
                ui.desenhar_texto(tela, l, (caixa.x + 200, caixa.y + 84 + k * 20), 10, BRANCO)
            self.ap_nao.topleft = (caixa.x + 200, caixa.bottom - 88)
            self.ap_sim.midleft = (self.ap_nao.right + 20, self.ap_nao.centery)
            for r, txt, cor, tam, foco in ((self.ap_nao, "NÃO, FICA!", (70, 170, 90), 14, self.ap_foco == 0),
                                           (self.ap_sim, "SIM, APAGAR", (170, 60, 60), 10, self.ap_foco == 1)):
                pygame.draw.rect(tela, ui.clarear(cor, 30) if foco else cor, r, border_radius=12)
                pygame.draw.rect(tela, AMARELO if foco else BRANCO, r, 3, border_radius=12)
                ui.desenhar_texto(tela, t(txt), r.center, tam, BRANCO, "center")
            ui.desenhar_texto(tela, t("ESC = NÃO"), (caixa.centerx + 60, caixa.bottom - 22), 8,
                              (230, 230, 240), "center")
        else:
            ui.desenhar_texto(tela, t("TEM CERTEZA MESMO?"), (caixa.centerx + 60, caixa.y + 30), 20,
                              (255, 120, 120), "midtop")
            msg = t("SE VOCÊ NÃO É O DONO DESTE OVO, PEÇA PARA UM ADULTO. "
                    "SEGURE O BOTÃO VERMELHO POR 3 SEGUNDOS.")
            for k, l in enumerate(ui.quebrar_linhas(msg, 10, 380)):
                ui.desenhar_texto(tela, l, (caixa.x + 200, caixa.y + 84 + k * 20), 10, BRANCO)
            self.ap_segurar.topleft = (caixa.x + 200, caixa.bottom - 150)
            self.ap_cancelar.topleft = (caixa.x + 200, caixa.bottom - 76)
            r = self.ap_segurar
            pygame.draw.rect(tela, (170, 60, 60), r, border_radius=12)
            f = min(1.0, self.segurar / TEMPO_SEGURAR)
            if f > 0:
                pygame.draw.rect(tela, (255, 120, 120), (r.x, r.y, round(r.w * f), r.h), border_radius=12)
            pygame.draw.rect(tela, BRANCO, r, 3, border_radius=12)
            ui.desenhar_texto(tela, t("SEGURE PARA APAGAR"), r.center, 12, BRANCO, "center")
            r = self.ap_cancelar
            pygame.draw.rect(tela, (70, 170, 90), r, border_radius=12)
            pygame.draw.rect(tela, BRANCO, r, 3, border_radius=12)
            ui.desenhar_texto(tela, t("CANCELAR"), r.center, 12, BRANCO, "center")

    def _desenhar_carta(self, tela):
        c = self.carta
        papel = pygame.Rect(0, 0, 520, 300)
        papel.center = (LARGURA // 2, ALTURA // 2)
        pygame.draw.rect(tela, (0, 0, 0), papel.move(6, 6), border_radius=6)
        pygame.draw.rect(tela, (255, 250, 235), papel, border_radius=6)
        for y in range(papel.y + 70, papel.bottom - 30, 22):
            pygame.draw.line(tela, (225, 215, 195), (papel.x + 20, y), (papel.right - 20, y), 1)
        ui.desenhar_texto(tela, t("CARTA DE ") + c.get("nome", "").upper(), (papel.x + 24, papel.y + 22), 12,
                          (120, 60, 30), sombra=False)
        # Selo com o mini avatar do remetente
        selo = pygame.Rect(papel.right - 84, papel.y + 14, 64, 72)
        pygame.draw.rect(tela, (230, 90, 90), selo, border_radius=4)
        pygame.draw.rect(tela, (255, 255, 255), selo.inflate(-8, -8), border_radius=3)
        apar = c.get("apar")
        if isinstance(apar, list) and len(apar) == 4 and self.perfis[self.sel].jogador:
            self.perfis[self.sel].jogador.desenhar(tela, selo.center, 34, aparencia=tuple(apar))
        for k, l in enumerate(ui.quebrar_linhas(t(c.get("texto", "")), 10, 400)):
            ui.desenhar_texto(tela, l, (papel.x + 24, papel.y + 96 + k * 22), 10, (60, 40, 30), sombra=False)
        ui.desenhar_texto(tela, t("CLIQUE PARA FECHAR"), (papel.centerx, papel.bottom - 16), 8,
                          (150, 120, 90), "center", False)
