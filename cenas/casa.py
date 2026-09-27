import math
import random
import time

import pygame

from settings import *
from core import assets, progresso, ui
from core.cena import Cena, tecla_voltar
from cenas.casa_extras.clima import Clima, POTE
from cenas.casa_extras.cuidados import Bandeja, Banho
from cenas.casa_extras.jardim import Jardim
from cenas.casa_extras.jukebox import Jukebox
from cenas.casa_extras.quintal import Bola, Borboletas
from cenas.casa_extras.rotina import Rotina
from cenas.casa_extras.tutorial import Tutorial
from cenas.casa_extras.eventos_casa import CacaOvos, desenhar_faixa

# ============================================================
# CASA (JOGO PRINCIPAL)
# ============================================================
# Três cômodos: SOL, CASA e BRINCAR.
#   ← →  ou 1 2 3   troca de cômodo (com animação de deslizar)
#   clique no chão  o ovo anda até lá
#   clique no ovo   ele pula feliz (ou acorda)
#   L               loja          ESC  menu de pausa
#
# CASA:    geladeira (comer), sabão (banho), luz (dormir), baú diário
# SOL:     jardim, borboletas + álbum, bola para o pet, clima e noite
# BRINCAR: mini jogos, desafio do ROBERT, TOTÓ
#
# Esta cena também é o "ctx" usado pelos móveis (core/moveis.py)
# e pelo pet (core/pets.py): veja a seção "API PARA MÓVEIS E PET".

COMODOS = [
    # nome,     fundo,     x inicial, chão (base do ovo), limites x
    ("SOL",     "sol",     560, 610, (80, 944)),
    ("CASA",    "casa",    360, 640, (80, 944)),
    ("BRINCAR", "brincar", 420, 650, (80, 640)),
]

ALTURA_OVO = 150
from core.jogador import OLHO_FECHADO
from core.jogador import BOCA_ABERTA   # boca "aberta" (funciona com boca extra)
VEL_ANDAR = 260

FERRAMENTAS = {
    "CASA": ["comida", "sabao", "luz"],
    "SOL": ["bola", "album"],
    "BRINCAR": [],
}
ROTULOS_FERRAMENTA = {"comida": "COMIDA", "sabao": "SABÃO", "luz": "LUZ", "bola": "BOLA",
                      "album": "ÁLBUM"}


def _modulo(nome):
    try:
        return __import__(f"core.{nome}", fromlist=[nome])
    except ImportError:
        return None


class CenaCasa(Cena):

    def __init__(self, app):
        super().__init__(app)
        self.i_comodo = 1                # começa na CASA
        self.tempo = 0.0

        # Ovo
        self.x = COMODOS[self.i_comodo][2]
        self.alvo_x = self.x
        self.olhando_esq = False
        self.pulo = 0.0
        self.passo = 0.0
        self.boca_aberta = 0.0
        self.recusa = 0.0
        self.frio = 0.0
        self.ardido = 0.0
        self.bocejo = 0.0
        self.ovo_ocupado = None
        self._ocupando = None
        self.dormindo = False
        self.luz_apagada = False

        # Deslizar entre cômodos
        self.slide = 0.0
        self.slide_dir = 1
        self.comodo_antigo = self.i_comodo

        # Efeitos
        self.coracoes = []
        self.moedas_voando = []
        self.particulas = ui.Particulas()
        self.textos = ui.TextoFlutuante()
        self.nuvens = self._criar_nuvens()
        self.dica = 7.0
        self.aviso = ""
        self.tempo_aviso = 0.0
        self.moedas_hud = float(app.save["moedas"])
        self.pop_moedas = 0.0
        self.piscar_em = random.uniform(2.0, 5.0)
        self.piscando = 0.0
        self.aterrissou = 0.0
        self._cache_sup = {}

        # Sistemas
        self.clima = Clima(app.save)
        self.jardim = Jardim(self)
        self.bandeja = Bandeja(self)
        self.banho = Banho(self)
        self.borboletas = Borboletas(self)
        self.bola_pet = Bola(self)
        self.rotina = Rotina(self)
        self.tutorial = Tutorial(self)
        self.caca = CacaOvos(self)
        self.resumo = None               # "enquanto você estava fora..."
        self.jukebox = Jukebox(self)
        self.faixa = "ovein"
        self.moveis = {}
        self.pet = None
        self._pet_id = None

        # Botões
        self.seta_esq = pygame.Rect(16, ALTURA // 2 - 40, 64, 80)
        self.seta_dir = pygame.Rect(LARGURA - 80, ALTURA // 2 - 40, 64, 80)
        self.botao_pausa = pygame.Rect(LARGURA - 76, 16, 60, 60)
        self.botao_loja = pygame.Rect(LARGURA - 204, 16, 116, 60)
        self.botao_rua = pygame.Rect(744, 16, 62, 60)
        self._restaurar_sono = True
        self.bola_jogos = pygame.Rect(690, 350, 190, 145)
        self.botao_jogar = ui.Botao((0, 0, 220, 64), "▶ JOGAR", 20,
                                    cor=(200, 50, 50), cor_hover=(240, 80, 80))
        self.botao_jogar.rect.center = (790, 640)
        self._veu_luz = None

    # ========================================================
    # PROPRIEDADES / API PARA MÓVEIS E PET (ctx)
    # ========================================================

    @property
    def musica(self):
        # A escolha da JUKEBOX manda; senão a música segue o momento
        if self.faixa != "ovein":
            return self.faixa
        if self.dormindo and self.comodo == "CASA":
            return "cancao_de_ninar"
        if self.clima.chovendo:
            return "dia_de_chuva"
        if self.comodo == "SOL" and self.clima.fase == "dia":
            return "quintal_feliz"
        return "ovein"

    @property
    def comodo(self):
        return COMODOS[self.i_comodo][0]

    @property
    def noite(self):
        return self.clima.noite

    @property
    def fase_dia(self):
        return self.clima.fase

    @property
    def chovendo(self):
        return self.clima.chovendo

    @property
    def vento(self):
        return self.clima.vento

    @property
    def ovo_x(self):
        return self.x

    @property
    def ovo_chao(self):
        return COMODOS[self.i_comodo][3]

    @property
    def jukebox_tocando(self):
        return self.faixa != "ovein"

    @property
    def olhando(self):
        return self.olhando_esq

    @property
    def pet_id(self):
        return self.app.save["pet"]

    def necessidade(self, nome):
        return self.app.necessidades.valor(nome)

    def mudar_necessidade(self, nome, delta, pos=None):
        self.app.necessidades.mudar(nome, delta)
        if pos is not None and abs(delta) >= 1:
            cor = (120, 255, 150) if delta > 0 else (255, 120, 120)
            self.textos.adicionar(f"{'+' if delta > 0 else ''}{int(delta)}", pos, cor, 12)

    def ganhar_moedas(self, qtd, pos):
        qtd = self.app.save.ganhar(qtd)
        if qtd <= 0:
            return
        self.textos.adicionar(f"+{qtd}", (pos[0], pos[1] - 10), AMARELO, 16)
        for i in range(min(8, qtd)):
            self.moedas_voando.append([float(pos[0]) + random.uniform(-20, 20),
                                       float(pos[1]) + random.uniform(-20, 20), -i * 0.05])
        self.som("moeda")

    def ocupar_ovo(self, movel, x):
        self.liberar_ovo()
        self._ocupando = movel
        self.alvo_x = self._limitar_x(x)

    def liberar_ovo(self):
        if self.ovo_ocupado is not None and getattr(self.ovo_ocupado, "id", "") == "cama":
            self._acordar()
        self.ovo_ocupado = None
        self._ocupando = None

    def dormir(self):
        self.dormindo = True
        self.luz_apagada = self.comodo == "CASA"

    def desenhar_ovo(self, tela, centro, altura, angulo=0, dormindo=False, espelhar=False):
        ovo, cabelo, olho, boca = self.jogador.aparencia()
        if dormindo or self.dormindo:
            olho = OLHO_FECHADO
        return self.jogador.desenhar(tela, centro, altura, aparencia=(ovo, cabelo, olho, boca),
                                     espelhar=espelhar, angulo=angulo)

    def abrir_bandeja(self):
        self.bandeja.abrir()

    def alternar_luz(self):
        if self.luz_apagada:
            self._acordar()
            self.som("clique")
        else:
            self.luz_apagada = True
            self.som("clique")
            cama = self.moveis.get("cama")
            if cama is not None and "cama" in self.app.save["moveis"]:
                # Anda acordado até a cama; ela chama dormir() ao deitar
                self.ocupar_ovo(cama, getattr(cama, "X_DESTINO", cama.rect.centerx))
            else:
                self.dormindo = True

    def abrir_jukebox(self):
        self.jukebox.abrir()

    def definir_faixa(self, faixa):
        self.faixa = faixa
        self.audio.tocar(faixa)

    def trofeus(self):
        from jogos import trofeus
        return trofeus.lista(self.app.save)

    @staticmethod
    def hora_real():
        t = time.localtime()
        return t.tm_hour, t.tm_min

    def avisar(self, msg):
        self.aviso = msg
        self.tempo_aviso = 3.0

    def andar_ate(self, x):
        if self.ovo_ocupado is not None:
            self.liberar_ovo()
        if self.dormindo:
            self._acordar()
        self.alvo_x = self._limitar_x(x)

    def pular(self):
        if self.pulo <= 0:
            self.pulo = 1.0

    def rect_corpo(self):
        chao = self.ovo_chao
        return pygame.Rect(int(self.x - ALTURA_OVO * 0.45), int(chao - ALTURA_OVO),
                           int(ALTURA_OVO * 0.9), ALTURA_OVO)

    def rect_boca(self):
        c = self.rect_corpo()
        return pygame.Rect(c.x + c.w * 0.25, c.y + c.h * 0.55, c.w * 0.5, c.h * 0.3)

    def comer(self, comida_id, efeitos):
        self.boca_aberta = 0.9
        self.som("comer")
        from core import itens
        dados = itens.COMIDAS.get(comida_id, {})
        if dados.get("pocao"):
            progresso.contar(self.app, "pocoes")
            buff = dados.get("buff")
            if buff:
                progresso.ativar_buff(self.app, *buff)
                self.avisar(f"{dados['nome']}: {dados.get('descricao', '')}")
            self.particulas.explodir(self.rect_corpo().center, [dados.get("cor", BRANCO), BRANCO],
                                     30, 260)
        else:
            progresso.contar(self.app, "comidas")
        progresso.ganhar_xp(self.app, progresso.XP_COMER)
        boca = self.rect_boca()
        for nome, delta in efeitos.items():
            self.mudar_necessidade(nome, delta)
        texto = " ".join(f"+{v}" for v in efeitos.values())
        self.textos.adicionar(texto, (boca.centerx, boca.y - 60), (120, 255, 150), 14)
        self.particulas.explodir(boca.center, [(240, 200, 120), BRANCO], 12, 140)
        if comida_id == "sorvete":
            self.frio = 2.0
        elif comida_id == "pimenta":
            self.ardido = 2.0
        elif comida_id == "bolo":
            self.particulas.explodir(boca.center, [AMARELO, (255, 90, 140), (120, 200, 255)], 40, 300)

    def comemorar_nivel(self, nivel):
        """Chamado por core/progresso quando o ovo sobe de nível."""
        corpo = self.rect_corpo()
        self.particulas.explodir(corpo.center, [AMARELO, (120, 220, 255), (255, 90, 140), BRANCO],
                                 70, 420, 1.2, (3, 7), 380)
        self.textos.adicionar(f"NÍVEL {nivel}!", (corpo.centerx, corpo.y - 40), (120, 220, 255), 20)
        if self.pulo <= 0 and not self.dormindo:
            self.pulo = 1.0

    def recusar(self):
        self.recusa = 1.0
        self.textos.adicionar("NÃO! TÔ CHEIO!", (self.x, self.ovo_chao - ALTURA_OVO - 30),
                              (255, 150, 150), 12)
        self.som("erro", 0.5)

    def info_sono(self):
        mult = 2.0 if (self.ovo_ocupado is not None
                       and getattr(self.ovo_ocupado, "id", "") == "cama") else 1.0
        if self.app.save["pet"] == "fantasma":
            mult *= 1.2
        pet = self.app.save["pet"]
        higiene = 0.7 if pet == "slime" else 1.0
        return {"dormindo": self.dormindo, "mult_sono": mult, "mult_higiene": higiene,
                "mult_fome": 0.85 if pet == "tartaruga" else 1.0,
                "mult_diversao": 0.75 if pet == "capivara" else 1.0}

    # ========================================================
    # INTERNOS
    # ========================================================

    def _limitar_x(self, x):
        xmin, xmax = COMODOS[self.i_comodo][4]
        return max(xmin, min(xmax, x))

    def _acordar(self):
        if self.dormindo:
            self.textos.adicionar("BOM DIA!", (self.x, self.ovo_chao - ALTURA_OVO - 20), AMARELO, 12)
        self.dormindo = False
        self.luz_apagada = False
        if self.ovo_ocupado is not None and getattr(self.ovo_ocupado, "id", "") == "cama":
            self.ovo_ocupado = None

    def _criar_nuvens(self):
        nuvens = []
        rnd = random.Random(4)
        for _ in range(5):
            larg = rnd.randint(140, 240)
            sup = pygame.Surface((larg, larg // 2), pygame.SRCALPHA)
            for _ in range(7):
                r = rnd.randint(larg // 7, larg // 4)
                cx = rnd.randint(r, larg - r)
                cy = rnd.randint(larg // 4, larg // 2 - r // 2)
                pygame.draw.circle(sup, (255, 255, 255, 230), (cx, cy), r)
            nuvens.append([sup, rnd.uniform(0, LARGURA), rnd.uniform(40, 300),
                           rnd.uniform(10, 25)])
        return nuvens

    def _sincronizar(self):
        """Cria os móveis comprados e o pet ativo (se mudaram na loja)."""
        mod = _modulo("moveis")
        if mod is not None and hasattr(mod, "criar"):
            catalogo = getattr(mod, "CATALOGO", {})
            ids = ["geladeira", "interruptor"] + list(self.app.save["moveis"])
            for mid in ids:
                if mid in catalogo and mid not in self.moveis:
                    try:
                        self.moveis[mid] = mod.criar(mid)
                    except Exception:     # móvel com problema não pode derrubar a casa
                        pass

        pid = self.app.save["pet"]
        if pid != self._pet_id:
            self._pet_id = pid
            self.pet = None
            pets = _modulo("pets")
            if pid and pets is not None and hasattr(pets, "PetNoMundo"):
                self.pet = pets.PetNoMundo(pid)
                self.pet.teleportar(self.x - 90, self.ovo_chao)

    def _moveis_do_comodo(self):
        if self.comodo not in ("CASA", "SOL"):
            return []
        ativos = {"geladeira", "interruptor"} | set(self.app.save["moveis"])
        lista = [m for mid, m in self.moveis.items()
                 if mid in ativos and getattr(m, "comodo", "") == self.comodo]
        lista.sort(key=lambda m: getattr(m, "base_y", 0))
        return lista

    def _presentes_do_pet(self):
        """Talentos diários: PIU acha semente, FAÍSCA assa marshmallow."""
        import datetime
        pet = self.app.save["pet"]
        presentes = {"pintinho": ("SOL", "semente_limao", "PIU achou uma SEMENTE DE LIMÃO!"),
                     "coelho": ("SOL", "cenoura", "FLOCO achou uma CENOURA!"),
                     "dragao": ("CASA", "marshmallow", "FAÍSCA assou um MARSHMALLOW!")}
        if pet not in presentes or self.slide > 0:
            return
        comodo, item, msg = presentes[pet]
        diario = self.app.save["diario"]
        hoje = datetime.date.today().isoformat()
        if self.comodo != comodo or diario.get(f"presente_{pet}") == hoje:
            return
        diario[f"presente_{pet}"] = hoje
        self.app.save["comida"][item] = self.app.save["comida"].get(item, 0) + 1
        self.app.save.salvar()
        self.avisar(msg)
        self.som("acerto")

    def entrar(self):
        super().entrar()
        self._sincronizar()
        if self.app.resumo_volta:
            self.resumo = self.app.resumo_volta
            self.app.resumo_volta = None
        from core import eventos
        eventos.entregar_presente(self.app)
        real = float(self.app.save["moedas"])
        ganhou = real - self.moedas_hud
        self.moedas_hud = min(self.moedas_hud, real)
        if ganhou >= 1:
            # Voltou de um mini jogo / loja com moedas: elas voam até o HUD
            for i in range(min(14, max(3, int(ganhou) // 3))):
                self.moedas_voando.append([LARGURA / 2 + random.uniform(-60, 60),
                                           ALTURA / 2 + random.uniform(-40, 40), -0.25 - i * 0.06])
        # Saiu para a rua dormindo? Volta dormindo, com a luz apagada.
        if self._restaurar_sono:
            self._restaurar_sono = False
            if self.app.save["diario"].pop("dormindo", False):
                self.dormindo = True
                self.luz_apagada = True

    def ir_para_rua(self):
        """Volta para a RUA DOS OVOS (o ovo é salvo pela vizinhança)."""
        from cenas.vizinhanca import CenaVizinhanca
        self.app.save["diario"]["dormindo"] = bool(self.dormindo and self.comodo == "CASA")
        if not self.app.config["viu_rua"]:
            self.app.config["viu_rua"] = True
            self.app.config.salvar()
        self.app.necessidades.salvar()
        self.som("selecionar")
        self.app.trocar(CenaVizinhanca(self.app, saindo=self.app.slot))

    def sair(self):
        self.rotina.calendario = 0.0
        self.banho.sair()
        self._acordar()
        self.liberar_ovo()

    def _trocar_comodo(self, novo):
        self.dica = min(self.dica, 1.0)
        novo %= len(COMODOS)
        if novo == self.i_comodo or self.slide > 0.3:
            return
        diff = (novo - self.i_comodo) % len(COMODOS)
        self.slide_dir = 1 if diff == 1 else -1
        self.comodo_antigo = self.i_comodo
        self._acordar()
        self.liberar_ovo()
        self.banho.sair()
        self.bandeja.aberta = False
        self.bola_pet.ativa = False
        self.jardim.escolhendo = None
        self.i_comodo = novo
        self.slide = 1.0
        self.x = self.alvo_x = COMODOS[novo][2]
        if self.pet is not None:
            self.pet.teleportar(self.x - 90, self.ovo_chao)
        self.som("clique")

    def _abrir_jogos(self):
        from cenas.menu_jogos import CenaMenuJogos
        self.som("selecionar")
        self.app.trocar(CenaMenuJogos(self.app, self))

    def _abrir_loja(self):
        from cenas.loja import CenaLoja
        self.som("selecionar")
        self.app.trocar(CenaLoja(self.app, self))

    def _abrir_pausa(self):
        from cenas.pausa import CenaPausa
        self.som("clique")
        self.app.trocar(CenaPausa(self.app, self), fade=False)

    def _carinho(self):
        progresso.contar(self.app, "carinhos")
        if self.dormindo:
            self._acordar()
            self.liberar_ovo()
            self.som("boing")
            return
        if self.pulo <= 0:
            self.pulo = 1.0
            self.som("boing")
        for _ in range(4):
            self.coracoes.append([self.x + random.uniform(-40, 40),
                                  self.ovo_chao - ALTURA_OVO - random.uniform(0, 30),
                                  random.uniform(-20, 20), 1.2])

    def _usar_ferramenta(self, nome):
        if nome == "comida":
            self.bandeja.alternar()
        elif nome == "sabao":
            self.bandeja.aberta = False
            self.banho.alternar()
        elif nome == "luz":
            self.alternar_luz()
        elif nome == "bola":
            self.bola_pet.alternar()
        elif nome == "album":
            self.borboletas.album_aberto = True
            self.som("selecionar")

    def _rects_ferramentas(self):
        return [(nome, pygame.Rect(16 + i * 76, ALTURA - 82, 66, 66))
                for i, nome in enumerate(FERRAMENTAS[self.comodo])]

    # ========================================================
    # EVENTOS
    # ========================================================

    def _movel_modal(self):
        for m in self._moveis_do_comodo():
            if getattr(m, "modal", False):
                return m
        return None

    def evento(self, e):
        # Móvel com tela cheia (telescópio) recebe tudo
        modal = self._movel_modal()
        if modal is not None:
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                try:
                    modal.clicar(e.pos, self)
                except Exception:
                    pass
            elif tecla_voltar(e) and hasattr(modal, "aberto"):
                modal.aberto = False
                self.som("voltar")
            return

        if self.resumo is not None:
            if e.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                self.resumo = None
                self.som("clique")
            return

        # Janelas por cima de tudo
        if self.jukebox.evento(e) or self.borboletas.evento_album(e):
            return
        if self.banho.evento(e):
            return
        if self.bandeja.evento(e):
            return

        if e.type == pygame.KEYDOWN:
            if tecla_voltar(e):
                if self.jardim.escolhendo is not None:
                    self.jardim.escolhendo = None
                else:
                    self._abrir_pausa()
            elif e.key in (pygame.K_LEFT, pygame.K_a):
                self._trocar_comodo(self.i_comodo - 1)
            elif e.key in (pygame.K_RIGHT, pygame.K_d):
                self._trocar_comodo(self.i_comodo + 1)
            elif e.key in (pygame.K_1, pygame.K_KP1):
                self._trocar_comodo(0)
            elif e.key in (pygame.K_2, pygame.K_KP2):
                self._trocar_comodo(1)
            elif e.key in (pygame.K_3, pygame.K_KP3):
                self._trocar_comodo(2)
            elif e.key == pygame.K_l:
                self._abrir_loja()
            elif e.key == pygame.K_v:
                self.ir_para_rua()
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and self.comodo == "BRINCAR":
                self._abrir_jogos()
            elif e.key == pygame.K_SPACE:
                self._carinho()
            return

        if self.comodo == "SOL" and self.bola_pet.evento(e):
            return

        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self._clique(e.pos)

    def _clique(self, pos):
        if self.tutorial.clicar(pos):
            return
        # HUD
        if self.botao_pausa.collidepoint(pos):
            self._abrir_pausa()
            return
        if self.botao_loja.collidepoint(pos):
            self._abrir_loja()
            return
        if self.botao_rua.collidepoint(pos):
            self.ir_para_rua()
            return
        if self.seta_esq.collidepoint(pos):
            self._trocar_comodo(self.i_comodo - 1)
            return
        if self.seta_dir.collidepoint(pos):
            self._trocar_comodo(self.i_comodo + 1)
            return
        for nome, r in self._rects_ferramentas():
            if r.collidepoint(pos):
                self._usar_ferramenta(nome)
                return

        # Coisas do cômodo
        if self.rotina.clicar(pos):
            return
        if self.comodo == "BRINCAR" and (self.bola_jogos.collidepoint(pos)
                                         or self.botao_jogar.rect.collidepoint(pos)):
            self._abrir_jogos()
            return
        if self.comodo == "SOL":
            if self.clima.pote_disponivel() and not self.noite \
                    and POTE.inflate(20, 20).collidepoint(pos):
                self.clima.pegar_pote()
                self.ganhar_moedas(15, pos)
                self.particulas.explodir(pos, [AMARELO, BRANCO], 30, 300)
                self.avisar("POTE DE OURO! +15 OVOEDAS")
                return
            if self.caca.clicar(pos):
                return
            if self.borboletas.clicar(pos):
                return
            if self.jardim.clicar(pos):
                return

        if self.pet is not None and self.pet.clicar(pos, self):
            progresso.afeicao(self.app, self.app.save["pet"], 2)
            return

        # Com o ovo "ocupando" um móvel, o clique no móvel é dele
        for m in reversed(self._moveis_do_comodo()):
            if m.rect.collidepoint(pos):
                try:
                    if m.clicar(pos, self):
                        return
                except Exception:
                    return

        if self.ovo_ocupado is None and self.rect_corpo().inflate(10, 20).collidepoint(pos):
            self._carinho()
            return

        if pos[1] > self.ovo_chao - 120:
            self.andar_ate(pos[0])

    # ========================================================
    # ATUALIZAÇÃO
    # ========================================================

    def atualizar(self, dt):
        self.tempo += dt
        self.dica = max(0.0, self.dica - dt)
        if self.app.cena is self and self.slide <= 0:
            self.audio.tocar(self.musica)
        self.slide = max(0.0, self.slide - dt * 3.2)
        pulo_antes = self.pulo
        self.pulo = max(0.0, self.pulo - dt * 2.2)
        if pulo_antes > 0 and self.pulo <= 0:
            self.aterrissou = 0.16
        self.aterrissou = max(0.0, self.aterrissou - dt)
        self.pop_moedas = max(0.0, self.pop_moedas - dt)
        self.piscando = max(0.0, self.piscando - dt)
        self.piscar_em -= dt
        if self.piscar_em <= 0:
            self.piscando = 0.13
            # Às vezes pisca duas vezes seguidas
            self.piscar_em = 0.25 if random.random() < 0.2 else random.uniform(2.5, 6.0)
        self.tempo_aviso = max(0.0, self.tempo_aviso - dt)
        for nome in ("boca_aberta", "recusa", "frio", "ardido"):
            setattr(self, nome, max(0.0, getattr(self, nome) - dt))
        self.botao_jogar.atualizar(dt)
        self._sincronizar()
        self._presentes_do_pet()

        self.clima.atualizar(dt)
        self.jardim.atualizar(dt)
        self.bandeja.atualizar(dt)
        self.banho.atualizar(dt)
        self.borboletas.atualizar(dt)
        self.rotina.atualizar(dt)
        self.tutorial.atualizar(dt)
        if self.app.necessidades.feliz():
            progresso.registrar_feliz(self.app, dt)
        if self.comodo == "SOL":
            self.bola_pet.atualizar(dt)
            # Chuva limpa (o pinguim adora)
            if self.chovendo:
                mult = 1.5 if self.app.save["pet"] == "pinguim" else 1.0
                self.app.necessidades.mudar("higiene", 0.3 * mult * dt)

        # Foguinho saindo da boca depois da pimenta
        if self.ardido > 0 and random.random() < dt * 20:
            boca = self.rect_boca()
            self.particulas.explodir(boca.center, [(255, 120, 30), (255, 220, 60)], 2, 120,
                                     vida=0.4)

        # Bocejo com pouca energia
        if self.necessidade("energia") < 25 and not self.dormindo:
            self.bocejo += dt
            if self.bocejo > 6:
                self.bocejo = 0
                self.boca_aberta = 0.8

        # Andar até o alvo
        if not self.dormindo or self._ocupando is not None:
            vel = VEL_ANDAR * (0.6 if self.necessidade("energia") < 25 else 1.0)
            dist = self.alvo_x - self.x
            if abs(dist) > 2 and self.ovo_ocupado is None:
                self.olhando_esq = dist < 0
                self.x += max(-vel * dt, min(vel * dt, dist))
                self.passo += dt * 12
            else:
                self.x = self.alvo_x if self.ovo_ocupado is None else self.x
                self.passo = 0.0
                if self._ocupando is not None:
                    movel = self._ocupando
                    self._ocupando = None
                    self.ovo_ocupado = movel
                    chegou = getattr(movel, "ovo_chegou", None)
                    if chegou:
                        chegou(self)

        for m in self._moveis_do_comodo():
            try:
                m.atualizar(dt, self)
            except Exception:
                pass
        if self.pet is not None:
            self.pet.atualizar(dt, self)

        for n in self.nuvens:
            n[1] += n[3] * dt * (1 + self.vento)
            if n[1] > LARGURA + 20:
                n[1] = -n[0].get_width() - 20

        for c in self.coracoes:
            c[0] += c[2] * dt
            c[1] -= 70 * dt
            c[3] -= dt
        self.coracoes = [c for c in self.coracoes if c[3] > 0]

        # Moedas voando para o HUD
        alvo = (LARGURA - 60, 104)
        for m in self.moedas_voando:
            m[2] += dt * 1.6
            if m[2] > 0:
                k = min(1.0, m[2])
                m[0] += (alvo[0] - m[0]) * k * 0.25
                m[1] += (alvo[1] - m[1]) * k * 0.25
        antes = len(self.moedas_voando)
        self.moedas_voando = [m for m in self.moedas_voando
                              if math.hypot(m[0] - alvo[0], m[1] - alvo[1]) > 12]
        if len(self.moedas_voando) < antes:
            self.pop_moedas = 0.15
            self.som("tic", 0.25)

        real = self.app.save["moedas"]
        if self.moedas_hud < real:
            self.moedas_hud = min(real, self.moedas_hud + max(1.0, (real - self.moedas_hud) * dt * 4))
        else:
            self.moedas_hud = float(real)

        self.particulas.atualizar(dt)
        self.textos.atualizar(dt)

    # ========================================================
    # DESENHO
    # ========================================================

    def _desenhar_fundo(self, tela, indice, dx):
        nome = COMODOS[indice][0]
        fundo = assets.FUNDOS[COMODOS[indice][1]]
        if nome == "SOL":
            fundo = self.clima.fundo_sol(fundo)
        tela.blit(fundo, (dx, 0))
        if nome == "CASA" and dx == 0:
            self.clima.desenhar_janela(tela)
        if nome == "SOL":
            tela.set_clip(pygame.Rect(dx, 0, LARGURA, ALTURA))
            if dx == 0:
                self.clima.desenhar_ceu(tela)
            for sup, x, y, _ in self.nuvens:
                if self.noite and dx == 0:
                    continue
                tela.blit(sup, (x + dx, y))
            tela.set_clip(None)

    def desenhar(self, tela):
        if self.slide > 0:
            t = 1 - (1 - self.slide) ** 3
            desloc = int(t * LARGURA) * self.slide_dir
            self._desenhar_fundo(tela, self.comodo_antigo, -self.slide_dir * LARGURA + desloc)
            self._desenhar_fundo(tela, self.i_comodo, desloc)
            self._desenhar_ovo(tela, desloc)
            self._desenhar_hud(tela)
            return

        self._desenhar_fundo(tela, self.i_comodo, 0)

        if self.comodo == "SOL":
            if not self.noite:
                self.clima.desenhar_pote(tela)
            self.jardim.desenhar(tela)
            self.caca.desenhar(tela)
        self.rotina.desenhar(tela)

        moveis = self._moveis_do_comodo()
        for m in moveis:
            self._seguro(m.desenhar, tela)

        if self.comodo == "BRINCAR":
            self._desenhar_bola_jogos(tela)

        if self.ovo_ocupado is not None:
            self._seguro(self.ovo_ocupado.desenhar_ovo_ocupado, tela)
        else:
            self._desenhar_ovo(tela)

        # Pet depois do ovo (a abelha pousa na cabeça dele)
        if self.pet is not None:
            self.pet.desenhar(tela, self)

        for m in moveis:
            self._seguro(m.desenhar_frente, tela)

        if self.comodo == "SOL":
            self.bola_pet.desenhar(tela)
            self.borboletas.desenhar(tela)
            self.clima.desenhar_chuva(tela)

        if self.luz_apagada and self.comodo == "CASA":
            tela.blit(self._veu_apagado(), (0, 0))
            cama = self.ovo_ocupado is not None and getattr(self.ovo_ocupado, "id", "") == "cama"
            if not cama:           # a cama desenha o próprio "Z z z"
                self._desenhar_zzz(tela)

        # Coisas que brilham no escuro (lâmpada de lava, TV, varal)
        for m in moveis:
            self._seguro(getattr(m, "desenhar_brilho", lambda t, c: None), tela)

        for x, y, _, vida in self.coracoes:
            ui.coracao(tela, (int(x), int(y)), int(18 * min(1, vida + 0.3)))
        self.particulas.desenhar(tela)
        self.textos.desenhar(tela)
        self.banho.desenhar(tela)

        self._desenhar_hud(tela)
        self._desenhar_dica_movel(tela, moveis)
        self.rotina.desenhar_calendario(tela)
        self.rotina.desenhar_missoes(tela)
        desenhar_faixa(tela, 78)

        if self.comodo == "SOL":
            self.jardim.desenhar_escolha(tela)
        self.bandeja.desenhar(tela)
        self.bandeja.desenhar_arraste(tela)
        self.borboletas.desenhar_album(tela)
        self.jukebox.desenhar(tela)

        # Telas cheias dos móveis (céu do telescópio)
        for m in moveis:
            self._seguro(getattr(m, "desenhar_sobreposicao", lambda t, c: None), tela)

        self.tutorial.desenhar(tela)
        if self.resumo:
            self._desenhar_resumo(tela)

    def _desenhar_resumo(self, tela):
        ui.veu(tela, 140)
        caixa = pygame.Rect(0, 0, 560, 90 + len(self.resumo) * 30)
        caixa.center = (LARGURA // 2, ALTURA // 2)
        ui.painel(tela, caixa, (30, 34, 60), AMARELO, 18, 4)
        ui.desenhar_texto(tela, "ENQUANTO VOCÊ ESTAVA FORA...", (caixa.centerx, caixa.y + 18), 14,
                          AMARELO, "midtop")
        for i, linha in enumerate(self.resumo):
            cor = BRANCO if i else (180, 220, 255)
            ui.desenhar_texto(tela, linha, (caixa.centerx, caixa.y + 52 + i * 30), 10, cor, "midtop")
        if int(self.tempo * 2) % 2 == 0:
            ui.desenhar_texto(tela, "clique para continuar", (caixa.centerx, caixa.bottom - 14), 8,
                              (170, 170, 200), "midbottom")

    def _seguro(self, funcao, tela):
        """Um móvel com erro de desenho não pode derrubar a casa."""
        try:
            funcao(tela, self)
        except Exception:
            pass

    def _veu_apagado(self):
        if self._veu_luz is None:
            from cenas.casa_extras.clima import VIDROS_CASA
            s = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
            s.fill((10, 10, 30, 170))
            for vidro in VIDROS_CASA:
                pygame.draw.rect(s, (10, 10, 30, 60), vidro)
            self._veu_luz = s
        return self._veu_luz

    def _desenhar_zzz(self, tela):
        if not self.dormindo:
            return
        base = self.rect_corpo()
        if self.ovo_ocupado is not None:
            base = self.ovo_ocupado.rect
        for i in range(3):
            fase = (self.tempo * 0.5 + i / 3) % 1
            ui.desenhar_texto(tela, "Z", (base.centerx + 30 + fase * 50, base.y - fase * 70),
                              12 + i * 5, (220, 220, 255), "center")

    def _desenhar_bola_jogos(self, tela):
        pulso = (math.sin(self.tempo * 4) + 1) / 2
        raio = int(52 + pulso * 10)
        alpha = int(120 + 100 * pulso) // 10 * 10
        chave = ("anel", raio, alpha)
        anel = self._cache_sup.get(chave)
        if anel is None:
            anel = pygame.Surface((raio * 2 + 8, raio * 2 + 8), pygame.SRCALPHA)
            pygame.draw.circle(anel, (255, 230, 90, alpha), (raio + 4, raio + 4), raio, 5)
            self._cache_sup[chave] = anel
        tela.blit(anel, anel.get_rect(center=(752, 446)))
        self.botao_jogar.desenhar(tela)
        ui.desenhar_texto(tela, "Clique na bola para jogar!", (790, 588), 12, BRANCO, "center")

    def _desenhar_ovo(self, tela, dx=0):
        chao = self.ovo_chao
        salto = math.sin(self.pulo * math.pi) * 70 if self.pulo > 0 else 0
        andando = abs(math.sin(self.passo)) * 10 if self.passo else 0
        respira = math.sin(self.tempo * (1.2 if self.dormindo else 2.4)) * 3
        tremor = math.sin(self.tempo * 60) * 3 if self.frio > 0 else 0
        nao = math.sin(self.recusa * 20) * 10 * self.recusa

        altura_no_ar = salto + andando
        larg = int(110 - altura_no_ar * 0.6) // 4 * 4
        sombra = self._cache_sup.get(("sombra", larg))
        if sombra is None:
            sombra = pygame.Surface((max(4, larg), 22), pygame.SRCALPHA)
            pygame.draw.ellipse(sombra, (0, 0, 0, 90), sombra.get_rect())
            self._cache_sup[("sombra", larg)] = sombra
        tela.blit(sombra, sombra.get_rect(center=(self.x + dx, chao)))

        # Squash & stretch: estica subindo, amassa ao cair no chão
        escala = (1.0, 1.0)
        if self.aterrissou > 0:
            k = math.sin(self.aterrissou / 0.16 * math.pi)
            escala = (1 + 0.14 * k, 1 - 0.12 * k)
        elif self.pulo > 0.7:
            k = (self.pulo - 0.7) / 0.3
            escala = (1 - 0.08 * k, 1 + 0.1 * k)
        centro = (self.x + dx + tremor,
                  chao - ALTURA_OVO * escala[1] / 2 - altura_no_ar + respira)
        ovo, cabelo, olho, boca = self.jogador.aparencia()
        if self.dormindo or self.piscando > 0:
            olho = OLHO_FECHADO
        if self.boca_aberta > 0 and int(self.boca_aberta * 8) % 3 != 2:
            boca = BOCA_ABERTA
        elif not self.dormindo and min(self.app.necessidades.valores.values()) < 30:
            # Alguma necessidade lá embaixo: carinha triste
            from core.jogador import BOCA_TRISTE
            boca = BOCA_TRISTE
        corpo = self.jogador.desenhar(tela, centro, ALTURA_OVO, aparencia=(ovo, cabelo, olho, boca),
                                      espelhar=self.olhando_esq, angulo=nao, esticar=escala)
        if dx:
            return

        higiene = self.necessidade("higiene")
        if higiene < 40:
            mancha = self._cache_sup.get("mancha")
            if mancha is None:
                mancha = pygame.Surface((22, 14), pygame.SRCALPHA)
                pygame.draw.ellipse(mancha, (110, 70, 30, 110), mancha.get_rect())
                self._cache_sup["mancha"] = mancha
            for i, (ox, oy) in enumerate(((-0.25, 0.15), (0.2, 0.3), (0.05, -0.2))):
                tela.blit(mancha, (corpo.centerx + ox * corpo.w - 11, corpo.centery + oy * corpo.h - 7))
        if higiene < 20:
            for i in range(3):
                a = self.tempo * 4 + i * 2.1
                pygame.draw.circle(tela, (20, 20, 20), (int(corpo.centerx + math.cos(a) * 70),
                                                        int(corpo.y + 10 + math.sin(a * 1.3) * 20)), 3)
            for i in range(2):
                y = corpo.y - 10 - (self.tempo * 20 + i * 15) % 30
                pygame.draw.arc(tela, (120, 200, 90), (corpo.centerx - 30 + i * 40, y, 16, 16),
                                0, 3.14, 2)

        if self.frio > 0:
            ui.desenhar_texto(tela, "BRRR!", (corpo.centerx, corpo.y - 24), 12, (180, 220, 255),
                              "center")

        self.banho.desenhar_no_ovo(tela)

        # Guarda-chuva na chuva do SOL
        if self.comodo == "SOL" and self.chovendo:
            cor = self.jogador.cor
            topo = corpo.y - 80
            cabo_x = corpo.right + 6
            pygame.draw.line(tela, (80, 60, 40), (corpo.centerx, topo), (cabo_x, corpo.centery), 4)
            pygame.draw.arc(tela, (80, 60, 40), (cabo_x - 8, corpo.centery - 6, 16, 20), 3.14, 6.28, 3)
            pygame.draw.polygon(tela, cor, [(corpo.centerx - 90, topo + 30), (corpo.centerx, topo - 20),
                                            (corpo.centerx + 90, topo + 30)])
            pygame.draw.polygon(tela, self.jogador.cor_contorno,
                                [(corpo.centerx - 90, topo + 30), (corpo.centerx, topo - 20),
                                 (corpo.centerx + 90, topo + 30)], 3)

        # Balõezinhos de necessidade
        balao = None
        if self.dormindo:
            balao = None
        elif self.necessidade("fome") < 25:
            balao = "RONC!"
        elif self.necessidade("diversao") < 25:
            balao = "..."
        if balao and int(self.tempo / 3) % 2 == 0:
            b = pygame.Rect(0, 0, 80, 36)
            b.midbottom = (corpo.right + 30, corpo.y + 10)
            pygame.draw.ellipse(tela, BRANCO, b)
            pygame.draw.ellipse(tela, (40, 40, 60), b, 2)
            ui.desenhar_texto(tela, balao, b.center, 10, (40, 40, 60), "center", sombra=False)

    def _desenhar_dica_movel(self, tela, moveis):
        mouse = pygame.mouse.get_pos()
        for m in reversed(moveis):
            if m.rect.collidepoint(mouse):
                try:
                    dica = m.dica(self)
                except Exception:
                    dica = None
                if dica:
                    sup = ui.texto(dica, 10)
                    r = sup.get_rect(midbottom=(mouse[0], mouse[1] - 14)).inflate(16, 12)
                    r.clamp_ip(tela.get_rect())
                    ui.painel(tela, r, (20, 24, 40), BRANCO, 8, 2, sombra=False)
                    tela.blit(sup, sup.get_rect(center=r.center))
                return

    def _desenhar_hud(self, tela):
        # Nome
        nome = ui.texto(self.jogador.nome, 16)
        painel = pygame.Rect(16, 16, max(nome.get_width(), 150) + 92, 60)
        ui.painel(tela, painel, (30, 36, 60), BRANCO, 14, 3)
        self.jogador.desenhar(tela, (48, 48), 38)
        tela.blit(nome, nome.get_rect(midleft=(78, 36)))
        nivel, xp, meta = progresso.progresso(self.app.save)
        ui.desenhar_texto(tela, f"NV {nivel}", (78, 59), 8, (120, 220, 255), "midleft")
        barra = pygame.Rect(118, 55, painel.right - 132, 8)
        pygame.draw.rect(tela, (60, 60, 90), barra, border_radius=4)
        pygame.draw.rect(tela, (120, 220, 255), (barra.x, barra.y, max(3, int(barra.w * xp / meta)),
                                                 barra.h), border_radius=4)

        self._desenhar_necessidades(tela)

        # Cômodo
        titulo = self.comodo
        caixa = pygame.Rect(0, 0, 230, 60)
        caixa.midtop = (LARGURA // 2, 16)
        ui.painel(tela, caixa, (30, 36, 60), BRANCO, 14, 3)
        ui.desenhar_texto(tela, titulo, (caixa.centerx, caixa.y + 12), 18, AMARELO, "midtop")
        for i in range(len(COMODOS)):
            cor = AMARELO if i == self.i_comodo else (110, 110, 140)
            pygame.draw.circle(tela, cor, (caixa.centerx - 20 + i * 20, caixa.bottom - 12), 5)

        mouse = pygame.mouse.get_pos()

        # Loja + moedas
        hover = self.botao_loja.collidepoint(mouse)
        pygame.draw.rect(tela, (200, 130, 40) if hover else (160, 100, 30), self.botao_loja,
                         border_radius=14)
        pygame.draw.rect(tela, BRANCO, self.botao_loja, 3, border_radius=14)
        sacola = pygame.Rect(self.botao_loja.x + 12, self.botao_loja.y + 20, 26, 26)
        pygame.draw.rect(tela, (255, 150, 60), sacola, border_radius=6)
        pygame.draw.arc(tela, BRANCO, (sacola.x + 5, sacola.y - 10, 16, 20), 0, 3.14, 3)
        pygame.draw.ellipse(tela, BRANCO, (sacola.x + 9, sacola.y + 8, 8, 11))
        ui.desenhar_texto(tela, "LOJA", (self.botao_loja.x + 76, self.botao_loja.centery), 14,
                          BRANCO, "center")
        ui.desenhar_moedas(tela, int(self.moedas_hud), (LARGURA - 16, 86), "topright",
                           16 + (4 if self.pop_moedas > 0 else 0))
        self._desenhar_botao_rua(tela, mouse)
        for x, y, atraso in self.moedas_voando:
            if atraso >= 0:
                ui.moeda(tela, (x, y), 10, giro=abs(math.cos(self.tempo * 8 + x)))

        # Setas
        for rect, simbolo in ((self.seta_esq, "<"), (self.seta_dir, ">")):
            hover = rect.collidepoint(mouse)
            s = self._cache_sup.get(("seta", hover))
            if s is None:
                s = pygame.Surface(rect.size, pygame.SRCALPHA)
                pygame.draw.rect(s, (20, 24, 40, 200 if hover else 130), s.get_rect(), border_radius=16)
                self._cache_sup[("seta", hover)] = s
            tela.blit(s, rect)
            ui.desenhar_texto(tela, simbolo, rect.center, 28, AMARELO if hover else BRANCO, "center")

        # Pausa
        hover = self.botao_pausa.collidepoint(mouse)
        pygame.draw.rect(tela, (70, 80, 130) if hover else (30, 36, 60), self.botao_pausa,
                         border_radius=14)
        pygame.draw.rect(tela, BRANCO, self.botao_pausa, 3, border_radius=14)
        cx, cy = self.botao_pausa.center
        pygame.draw.rect(tela, BRANCO, (cx - 11, cy - 13, 8, 26), border_radius=2)
        pygame.draw.rect(tela, BRANCO, (cx + 3, cy - 13, 8, 26), border_radius=2)

        if self.slide > 0:
            return

        # Ferramentas
        for nome, r in self._rects_ferramentas():
            ativo = (nome == "sabao" and self.banho.ativo) or (nome == "comida" and self.bandeja.aberta) \
                or (nome == "luz" and self.luz_apagada) or (nome == "bola" and self.bola_pet.ativa)
            hover = r.collidepoint(mouse)
            pygame.draw.rect(tela, (0, 0, 0), r.move(0, 4), border_radius=14)
            pygame.draw.rect(tela, (90, 100, 160) if hover or ativo else (30, 36, 60), r,
                             border_radius=14)
            pygame.draw.rect(tela, AMARELO if ativo else BRANCO, r, 3, border_radius=14)
            self._icone_ferramenta(tela, nome, (r.centerx, r.centery - 6))
            ui.desenhar_texto(tela, ROTULOS_FERRAMENTA[nome], (r.centerx, r.bottom - 10), 8,
                              BRANCO, "center")

        # Aviso
        if self.tempo_aviso > 0:
            sup = ui.texto(self.aviso, 12, AMARELO)
            r = sup.get_rect(center=(LARGURA // 2, 140)).inflate(28, 18)
            ui.painel(tela, r, (20, 24, 40), AMARELO, 12, 2, sombra=False)
            tela.blit(sup, sup.get_rect(center=r.center))

        if self.dica > 0 and self.comodo != "BRINCAR":
            alpha = min(1.0, self.dica)
            sup = ui.texto("← → troca de cômodo  •  vá ao BRINCAR para jogar!", 12)
            caixa = sup.get_rect(center=(LARGURA // 2 + 60, ALTURA - 40)).inflate(32, 24)
            degrau = int(alpha * 10)
            fundo = self._cache_sup.get(("dica", degrau))
            if fundo is None:
                fundo = pygame.Surface(caixa.size, pygame.SRCALPHA)
                pygame.draw.rect(fundo, (20, 24, 40, 20 * degrau), fundo.get_rect(), border_radius=12)
                self._cache_sup[("dica", degrau)] = fundo
            tela.blit(fundo, caixa)
            sup = sup.copy()
            sup.set_alpha(int(255 * alpha))
            tela.blit(sup, sup.get_rect(center=caixa.center))

    def _desenhar_botao_rua(self, tela, mouse):
        r = self.botao_rua
        hover = r.collidepoint(mouse)
        pygame.draw.rect(tela, (70, 80, 130) if hover else (30, 36, 60), r, border_radius=14)
        pygame.draw.rect(tela, BRANCO, r, 3, border_radius=14)
        cx, cy = r.centerx, r.y + 24 - (3 if hover else 0)
        pygame.draw.rect(tela, (255, 230, 160), (cx - 12, cy - 4, 24, 16))
        pygame.draw.polygon(tela, (230, 90, 70), [(cx - 16, cy - 3), (cx, cy - 15), (cx + 16, cy - 3)])
        pygame.draw.rect(tela, (120, 70, 40), (cx - 4, cy + 3, 8, 9))
        ui.desenhar_texto(tela, "RUA", (r.centerx, r.bottom - 11), 8, BRANCO, "center")

        # Dica para quem ainda não conhece a rua
        if not self.app.config["viu_rua"] and (self.tempo > 120 or self.app.jogou_partida):
            s = 1 + 0.06 * math.sin(self.tempo * 6)
            sup = ui.texto("NOVO! VEJA SUA RUA", 10, (40, 30, 10), sombra=False)
            caixa = sup.get_rect(midtop=(r.centerx, r.bottom + 14)).inflate(20, 14)
            caixa = caixa.inflate(int(caixa.w * (s - 1)), int(caixa.h * (s - 1)))
            caixa.clamp_ip(pygame.Rect(8, 0, LARGURA - 16, ALTURA))
            pygame.draw.polygon(tela, AMARELO, [(r.centerx - 8, caixa.y + 1), (r.centerx + 8, caixa.y + 1),
                                                (r.centerx, caixa.y - 9)])
            pygame.draw.rect(tela, AMARELO, caixa, border_radius=10)
            tela.blit(sup, sup.get_rect(center=caixa.center))

    def _icone_ferramenta(self, tela, nome, c):
        x, y = c
        if nome == "comida":
            pygame.draw.circle(tela, (230, 50, 60), (x, y + 2), 13)
            pygame.draw.circle(tela, (255, 140, 140), (x - 5, y - 3), 4)
            pygame.draw.line(tela, (110, 70, 30), (x, y - 10), (x + 2, y - 16), 3)
            pygame.draw.ellipse(tela, (90, 190, 80), (x + 2, y - 18, 12, 7))
        elif nome == "sabao":
            pygame.draw.rect(tela, (255, 200, 230), (x - 16, y - 8, 32, 18), border_radius=7)
            for k in range(3):
                pygame.draw.circle(tela, BRANCO, (x - 10 + k * 10, y - 12 - k * 3), 4 + k, 1)
        elif nome == "luz":
            cor = (255, 230, 90) if not self.luz_apagada else (90, 90, 110)
            pygame.draw.circle(tela, cor, (x, y - 3), 12)
            pygame.draw.rect(tela, (170, 170, 180), (x - 6, y + 8, 12, 8), border_radius=2)
        elif nome == "bola":
            pygame.draw.circle(tela, (230, 50, 50), (x, y), 13)
            pygame.draw.line(tela, BRANCO, (x - 13, y), (x + 13, y), 2)
            pygame.draw.circle(tela, BRANCO, (x, y), 13, 2)
        elif nome == "album":
            pygame.draw.rect(tela, (200, 150, 90), (x - 15, y - 12, 30, 24), border_radius=3)
            pygame.draw.line(tela, (120, 80, 40), (x, y - 12), (x, y + 12), 2)
            pygame.draw.polygon(tela, (255, 150, 50), [(x - 10, y - 6), (x - 2, y), (x - 10, y + 6)])
            pygame.draw.polygon(tela, (255, 150, 50), [(x + 10, y - 6), (x + 2, y), (x + 10, y + 6)])

    def _desenhar_necessidades(self, tela):
        from core.necessidades import NOMES
        n = self.app.necessidades
        x0, y0 = 16, 84
        for i, nome in enumerate(NOMES):
            v = n.valor(nome)
            x = x0 + i * 100
            fundo = pygame.Rect(x, y0, 94, 30)
            s = self._cache_sup.get("barra")
            if s is None:
                s = pygame.Surface(fundo.size, pygame.SRCALPHA)
                pygame.draw.rect(s, (20, 24, 40, 190), s.get_rect(), border_radius=10)
                self._cache_sup["barra"] = s
            tela.blit(s, fundo)
            self._icone_necessidade(tela, nome, (x + 14, y0 + 15))
            barra = pygame.Rect(x + 28, y0 + 11, 58, 9)
            pygame.draw.rect(tela, (60, 60, 80), barra, border_radius=4)
            if self.app.config["daltonico"]:
                cor = (255, 120, 0) if v < 30 else (AMARELO if v < 70 else (60, 150, 230))
            else:
                cor = VERMELHO if v < 30 else (AMARELO if v < 70 else VERDE)
            if v < 30 and int(self.tempo * 3) % 2 == 0:
                cor = (255, 150, 150) if not self.app.config["daltonico"] else (255, 200, 120)
            pygame.draw.rect(tela, cor, (barra.x, barra.y, max(2, int(barra.w * v / 100)), barra.h),
                             border_radius=4)
        if n.feliz():
            r = pygame.Rect(x0 + 404, y0, 116, 30)
            ui.painel(tela, r, (60, 50, 10), AMARELO, 10, 2, sombra=False)
            pygame.draw.circle(tela, AMARELO, (r.x + 15, r.centery), 9)
            pygame.draw.arc(tela, (120, 80, 0), (r.x + 9, r.centery - 4, 12, 9), 3.4, 6.0, 2)
            mult = progresso.mult_feliz(self.app.save)
            ui.desenhar_texto(tela, f"FELIZ x{mult:.2f}".replace(".", ","), (r.x + 30, r.centery), 8,
                              AMARELO, "midleft")
        # Reforços das poções
        for i, texto in enumerate(progresso.buffs_ativos(self.app.save)):
            sup = ui.texto(texto, 8, (230, 210, 255))
            r = sup.get_rect(topleft=(x0 + 8 + i * 150, y0 + 40)).inflate(16, 10)
            pygame.draw.rect(tela, (60, 40, 100), r, border_radius=8)
            pygame.draw.rect(tela, (170, 120, 255), r, 2, border_radius=8)
            tela.blit(sup, sup.get_rect(center=r.center))

    @staticmethod
    def _icone_necessidade(tela, nome, c):
        x, y = c
        if nome == "fome":
            pygame.draw.circle(tela, (240, 240, 240), (x, y), 9)
            pygame.draw.circle(tela, (200, 200, 210), (x, y), 5, 1)
            pygame.draw.line(tela, (200, 200, 210), (x - 11, y - 8), (x - 11, y + 8), 2)
        elif nome == "energia":
            pygame.draw.polygon(tela, AMARELO, [(x + 2, y - 10), (x - 6, y + 1), (x, y + 1),
                                                (x - 2, y + 10), (x + 7, y - 2), (x + 1, y - 2)])
        elif nome == "diversao":
            pygame.draw.circle(tela, (90, 170, 255), (x, y), 9)
            pygame.draw.arc(tela, BRANCO, (x - 9, y - 4, 18, 8), 3.14, 6.28, 2)
        else:
            pygame.draw.circle(tela, (90, 180, 255), (x, y + 3), 7)
            pygame.draw.polygon(tela, (90, 180, 255), [(x - 6, y + 1), (x + 6, y + 1), (x, y - 10)])
