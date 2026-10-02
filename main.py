import os
import sys
import time

import pygame

from settings import *
from core import assets, idioma, perfis, progresso, ui
from core.idioma import t
from core.audio import Audio
from core.janela import Janela
from core.jogador import Jogador
from core.necessidades import Necessidades
from cenas.casa import CenaCasa
from cenas.criador import CenaCriador
from cenas.nome import CenaNome

# ============================================================
# OVAL
# ============================================================
# Arquivo principal: cria a janela, carrega tudo e roda o loop.
# Cada tela do jogo é uma "cena" (pasta cenas/ e jogos/).
#
#   cenas/titulo.py      -> tela inicial (JOGAR / OPÇÕES / SAIR)
#   cenas/vizinhanca.py  -> RUA DOS OVOS (5 casas = 5 ovos)
#   cenas/reforma.py     -> customizar a fachada da casa
#   cenas/nome.py        -> digitar o nome
#   cenas/criador.py     -> escolher ovo, cabelo, olhos e boca
#   cenas/casa.py        -> vida do ovo (cômodos SOL/CASA/BRINCAR)
#   cenas/pausa.py       -> menu de pausa
#   cenas/menu_jogos.py  -> escolher um mini jogo
#   jogos/*.py           -> os mini jogos
#
# Saves: saves/global.json (preferências) + saves/ovo_N.json
# (um por ovo). O ovo "ativo" fica em self.save / self.jogador /
# self.necessidades; na tela inicial e na rua não há ovo ativo.

TEMPO_TRANSICAO = 0.24


class App:

    def __init__(self):
        pygame.mixer.pre_init(FREQUENCIA_AUDIO, -16, 2, 512)
        pygame.init()

        # Se não houver placa de som, o jogo roda sem áudio
        if pygame.mixer.get_init() is None:
            try:
                pygame.mixer.init()
            except pygame.error:
                pass

        icone = pygame.image.load(caminho("Img", "personagem", "P_verde.png"))
        pygame.display.set_icon(icone)
        pygame.display.set_caption(TITULO)

        # Saves: o save antigo (1 ovo) vira o morador da casa 1
        perfis.migrar_save_antigo()
        self.config = perfis.carregar_config()
        idioma.definir(self.config["idioma"] or "pt")
        # Tutorial: quem já jogava antes dele existir não precisa ver
        if self.config["tutorial"] < 0:
            from cenas.casa_extras.tutorial import TUTORIAL_FIM
            self.config["tutorial"] = TUTORIAL_FIM if self.config["tem_ovo"] else 0
            self.config.salvar()
        self.resumo_volta = None
        self._sorte_partida = False
        self._iris = {}
        self._fps_rel = 0.0

        # Ovo ativo (nenhum até entrar numa casa)
        self.save = None
        self.jogador = None
        self.necessidades = None
        self.slot = -1
        self.jogou_partida = False

        # Janela redimensionável: tudo é desenhado em self.tela (1024x720)
        self.janela = Janela(self.config["janela"])
        self.tela = self.janela.tela
        self.clock = pygame.time.Clock()

        # As imagens só podem ser convertidas depois da janela existir
        assets.carregar()
        pygame.key.stop_text_input()

        self.audio = Audio(self.config)
        # Avisos de conquista / nível que aparecem por cima de qualquer tela
        self.toasts = ui.Toasts(lambda nome: self.audio.som(nome))
        self._flash = 0.0

        self.cena = None
        self._proxima = None
        self._fase = None        # None, "saindo" ou "entrando"
        self._fade = 0.0
        self.rodando = True
        self.tempo_total = 0.0

        if self.config["idioma"] is None:
            # Idioma ainda não escolhido: pergunta antes de tudo
            from cenas.escolher_idioma import CenaEscolherIdioma
            self.trocar(CenaEscolherIdioma(self, self._comecar), fade=False)
        else:
            self._comecar(fade=False)

    def _comecar(self, fade=True):
        """Primeira cena de verdade (depois do idioma)."""
        if perfis.primeira_execucao(self.config):
            # 1ª vez: cria o ovo da casa 1 e vai direto para ela
            self.iniciar_rascunho(0)
            self.trocar(CenaNome(self, "inicial", self._depois_do_nome), fade=fade)
        else:
            from cenas.titulo import CenaTitulo
            self.trocar(CenaTitulo(self), fade=fade)

    # --------------------------------------------------------
    # FLUXO INICIAL (1ª execução)
    # --------------------------------------------------------

    def _depois_do_nome(self):
        self.trocar(CenaCriador(self, "inicial", self._depois_do_criador))

    def _depois_do_criador(self):
        self.confirmar_rascunho(presente=True)
        if 0 <= self.config["tutorial"] < 90:
            # Tutorial: o ovo começa com fome e sujinho (para os 1ºs passos)
            self.necessidades.valores["fome"] = 45.0
            self.necessidades.valores["higiene"] = 40.0
            self.necessidades.salvar()
        self.trocar(CenaCasa(self))

    # --------------------------------------------------------
    # OVOS (trocar o ovo ativo)
    # --------------------------------------------------------

    def carregar_ovo(self, slot):
        """Torna o ovo da casa `slot` o ovo ativo. False se não der."""
        if self.save is not None and self.slot == slot and self.save.arquivo:
            return True
        self.descarregar_ovo()
        save = perfis.carregar_ovo(slot, self.config)
        if save is None:
            return False
        self.save = save
        self.slot = slot
        fora = time.time() - save["ultimo_tempo"] if save["ultimo_tempo"] > 0 else 0
        self.necessidades = Necessidades(save)      # aplica o tempo offline
        self.jogador = Jogador(save)
        self.config["ultimo_ovo"] = slot
        self.config.salvar()
        from jogos.base import MiniJogo
        MiniJogo._fundos.clear()
        progresso.sincronizar(self)
        self.resumo_volta = self._montar_resumo(fora) if fora >= 4 * 3600 else None
        return True

    def _montar_resumo(self, segundos):
        """'Enquanto você estava fora...' (mostrado pela casa ao entrar)."""
        import datetime
        from types import SimpleNamespace
        save = self.save
        horas = int(segundos // 3600)
        linhas = [t("Você ficou fora {n} DIA(S)!", n=horas // 24) if horas >= 48
                  else t("Você ficou fora {n}h!", n=horas)]
        try:
            from cenas.casa_extras.jardim import Jardim
            jardim = Jardim(SimpleNamespace(app=SimpleNamespace(save=save)))
            prontas = sum(1 for c in save["jardim"] if jardim.pronta(c))
            if prontas:
                linhas.append(t("{n} PLANTA(S) PRONTA(S) NO JARDIM", n=prontas))
        except Exception:
            pass
        if save["diario"].get("bau_ultimo") != datetime.date.today().isoformat():
            linhas.append(t("O BAÚ DO DIA ESTÁ ESPERANDO"))
        cartas = sum(1 for c in save["cartas"] if isinstance(c, dict) and not c.get("lida"))
        if cartas:
            linhas.append(t("{n} CARTA(S) NOVA(S) NA CAIXA DO CORREIO", n=cartas))
        m = save["diario"].get("missoes")
        if not isinstance(m, dict) or m.get("dia") != datetime.date.today().isoformat():
            linhas.append(t("MISSÕES NOVAS COM O ROBERT"))
        baixas = [nome for nome in ("fome", "energia", "diversao", "higiene")
                  if self.necessidades.valor(nome) < 40]
        if baixas:
            rotulos = {"fome": "FOME", "energia": "SONO", "diversao": "TÉDIO", "higiene": "SUJEIRA"}
            linhas.append(t("O OVO ESTÁ COM {lista}!", lista=", ".join(t(rotulos[b]) for b in baixas)))
        return linhas

    def descarregar_ovo(self):
        """Salva e solta o ovo ativo (tela inicial / rua)."""
        if self.save is None:
            return
        if self.save.arquivo:
            self.necessidades.salvar()
        self.save = self.jogador = self.necessidades = None
        self.slot = -1

    def iniciar_rascunho(self, slot):
        """Ovo novo em criação (ainda sem arquivo)."""
        self.descarregar_ovo()
        self.save = perfis.novo_rascunho(self.config)
        self.slot = slot
        self.jogador = Jogador(self.save)
        self.necessidades = Necessidades(self.save)

    def confirmar_rascunho(self, presente=True):
        """Grava o ovo em criação na casa escolhida (continua ativo)."""
        self.jogador.salvar()
        self.necessidades.salvar()
        perfis.criar_ovo(self.slot, self.save, presente)
        progresso.iniciar_liberacao(self.save, novo=True)
        self.save.salvar()
        self.config["ultimo_ovo"] = self.slot
        self.config["tem_ovo"] = True
        self.config.salvar()

    def descartar_rascunho(self):
        self.save = self.jogador = self.necessidades = None
        self.slot = -1

    def iniciar_novo_ovo(self, slot):
        """+NOVO na vizinhança: nome -> aparência -> casa nova."""
        from cenas.vizinhanca import CenaVizinhanca
        self.iniciar_rascunho(slot)

        def cancelar():
            self.descartar_rascunho()
            self.trocar(CenaVizinhanca(self))

        def depois_do_criador():
            self.confirmar_rascunho(presente=True)
            self.trocar(CenaVizinhanca(self, mudanca=slot))

        def depois_do_nome():
            self.trocar(CenaCriador(self, "novo", depois_do_criador,
                                    ao_cancelar=lambda: self.trocar(nome_cena)))

        nome_cena = CenaNome(self, "novo", depois_do_nome, ao_cancelar=cancelar, slot=slot)
        self.trocar(nome_cena)

    # --------------------------------------------------------
    # CENAS
    # --------------------------------------------------------

    def trocar(self, cena, fade=True):
        """Troca a cena ativa (com escurecimento, se fade=True)."""
        if self._fase == "saindo":
            # Já estava trocando: só atualiza o destino
            self._proxima = cena
            return

        if not fade or self.cena is None:
            self._ativar(cena)
        else:
            self._proxima = cena
            self._fase = "saindo"

    def _ativar(self, cena):
        if self.cena is not None:
            self.cena.sair()
        self.cena = cena
        # Evita que um clique "vaze" para a próxima cena
        pygame.event.clear((pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP))
        cena.entrar()

    def sair(self):
        self.rodando = False

    # --------------------------------------------------------
    # PET / ECONOMIA (usados pelas cenas e mini jogos)
    # --------------------------------------------------------

    def bonus_moedas(self):
        """Multiplicador de moedas: pet (unicórnio) x OVO FELIZ."""
        from core import pets
        from core import eventos
        bonus = pets.bonus_moedas(self.save["pet"])
        if self.necessidades.feliz():
            bonus *= progresso.mult_feliz(self.save)
        bonus *= eventos.mult_moedas()
        if self._sorte_partida:
            bonus *= progresso.MULT_SORTE
        return bonus

    def ao_terminar_minijogo(self, jogo, valor, venceu, variedade=True):
        """
        Chamado pela base dos mini jogos ao fim de cada partida.
        Devolve moedas extras (bônus VARIEDADE: 1ª partida do dia
        em cada jogo vale +5).
        """
        import datetime
        self.jogou_partida = True
        self._sorte_partida = progresso.consumir_sorte(self)
        self.necessidades.pos_minijogo()
        self.necessidades.salvar()

        if jogo.ID not in self.save["jogados"]:
            self.save["jogados"].append(jogo.ID)

        diario = self.save["diario"]
        hoje = datetime.date.today().isoformat()
        if diario.get("variedade_dia") != hoje:
            diario["variedade_dia"] = hoje
            diario["variedade"] = []
        extra = 0
        if variedade and jogo.ID not in diario["variedade"]:
            diario["variedade"].append(jogo.ID)
            extra = 5

        # Desafio do dia do ROBERT
        from cenas.casa_extras import rotina
        rotina.verificar_desafio(self.save, jogo, valor, venceu)
        self.save.salvar()

        # Progresso: XP e estatísticas das conquistas
        from jogos import JOGOS
        solo = {j.ID for j in JOGOS if not getattr(j, "MULTI", False)}
        jogados = set(self.save["jogados"])
        progresso.contar(self, "partidas")
        progresso.definir(self, "jogos_diferentes", len(jogados))
        progresso.definir(self, "jogos_solo", len(jogados & solo))
        if getattr(jogo, "novo_recorde", False):
            progresso.contar(self, "recordes")
        if getattr(jogo, "MULTI", False) and venceu:
            progresso.contar(self, "vitorias_multi")
        if venceu:
            progresso.contar(self, "vitorias")
            if self.save["pet"]:
                progresso.afeicao(self, self.save["pet"], 1)
        xp = progresso.XP_VITORIA if venceu else progresso.XP_PARTIDA
        jogo.xp_ganho = xp * (2 if progresso.xp_dobrado(self.save) else 1)
        progresso.ganhar_xp(self, xp)
        return extra

    def estado_sono(self):
        """A cena da casa informa se o ovo está dormindo (e bônus de sono)."""
        casa = getattr(self.cena, "casa", None) or self.cena
        info = getattr(casa, "info_sono", None)
        return info() if info else {}

    def desenhar_pet(self, tela, pos, feliz=False):
        """Desenha o pet ativo (se houver) com os pés em `pos`."""
        from core import pets
        if self.save is not None:
            pets.desenhar_parado(tela, self.save["pet"], pos, self.tempo_total, feliz)

    def desenhar_pet_de(self, tela, pet_id, pos, escala=0.8, feliz=False):
        """Pet de qualquer ovo (vizinhança / tela inicial)."""
        from core import pets
        if pet_id:
            pets.desenhar_parado(tela, pet_id, pos, self.tempo_total, feliz, escala)

    # --------------------------------------------------------
    # LOOP
    # --------------------------------------------------------

    def rodar(self):
        while self.rodando:
            # dt limitado: se a janela travar (arrastar), a física não explode
            dt = min(self.clock.tick(FPS) / 1000.0, 1 / 20)
            self.passo(dt)
        self.fechar()
        pygame.quit()

    def fechar(self):
        """Grava tudo antes de fechar o jogo."""
        self.config["janela"] = list(self.janela.tamanho)
        self.config.salvar()
        if self.save is not None and self.save.arquivo:
            self.necessidades.salvar()

    def passo(self, dt):
        """Um frame: eventos -> lógica -> desenho."""
        self.tempo_total += dt
        trocou = False

        for e in pygame.event.get():
            e = self.janela.converter_evento(e)
            if e is None:
                continue
            if e.type == pygame.QUIT:
                self.sair()
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_F12:
                self._foto_pendente = True
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_F11:
                self.alternar_tela_cheia()
            elif self._fase is None and not trocou:
                cena = self.cena
                cena.evento(e)
                # Se a cena mudou, o resto dos eventos deste frame
                # não pode "vazar" para a cena nova
                trocou = self.cena is not cena

        self._atualizar_transicao(dt)
        self.audio.atualizar(dt)
        if self.necessidades is not None and self.save.arquivo:
            self.necessidades.atualizar(dt, **self.estado_sono())
        self.cena.atualizar(dt)
        self.toasts.atualizar(dt)
        self.cena.desenhar(self.tela)

        # A foto é tirada antes dos avisos e do flash por cima
        if getattr(self, "_foto_pendente", False):
            self._foto_pendente = False
            self.tirar_foto()

        self.toasts.desenhar(self.tela)

        if self._fade > 0:
            # Smoothstep: a íris começa e termina macia
            self._desenhar_iris(ui.suavizar(self._fade))
        if self.config["mostrar_fps"]:
            self._fps_rel += dt
            if self._fps_rel > 0.5 or not hasattr(self, "_fps_txt"):
                self._fps_rel = 0.0
                self._fps_txt = f"{self.clock.get_fps():.0f} FPS"
            ui.desenhar_texto(self.tela, self._fps_txt, (6, ALTURA - 6), 8, (120, 255, 150), "bottomleft")
        if self._flash > 0:
            ui.veu(self.tela, int(255 * min(1.0, self._flash / 0.25)), (255, 255, 255))
            self._flash = max(0.0, self._flash - dt)

        self.janela.apresentar()

    def _desenhar_iris(self, k):
        """Transição: um buraco em forma de OVO que fecha e abre."""
        passo = min(24, int(k * 24 + 0.5))
        if passo >= 24:
            self.tela.fill((8, 8, 16))
            return
        sup = self._iris.get(passo)
        if sup is None:
            sup = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
            sup.fill((8, 8, 16, 255))
            f = 1 - passo / 24
            w, h = int(1400 * f), int(1700 * f)
            buraco = pygame.Rect(0, 0, w, h)
            buraco.center = (LARGURA // 2, ALTURA // 2 + int(40 * f))
            pygame.draw.ellipse(sup, (0, 0, 0, 0), buraco)
            if w > 20:
                pygame.draw.ellipse(sup, (255, 214, 64, 255), buraco, 4)
            self._iris[passo] = sup
        self.tela.blit(sup, (0, 0))

    def alternar_tela_cheia(self):
        try:
            pygame.display.toggle_fullscreen()
        except pygame.error:
            pass

    def tirar_foto(self):
        """F12: salva a tela (com uma plaquinha do OVAL) em fotos/."""
        import datetime
        foto = self.tela.copy()
        marca = ui.texto(f"OVAL  •  {datetime.date.today().strftime('%d/%m/%Y')}", 10, AMARELO)
        r = marca.get_rect(bottomright=(LARGURA - 10, ALTURA - 10)).inflate(16, 10)
        ui.painel(foto, r, (20, 24, 40), AMARELO, 8, 2, sombra=False)
        foto.blit(marca, marca.get_rect(center=r.center))
        pasta = caminho_dados("fotos")
        nome = datetime.datetime.now().strftime("oval_%Y%m%d_%H%M%S.png")
        try:
            os.makedirs(pasta, exist_ok=True)
            pygame.image.save(foto, os.path.join(pasta, nome))
        except (OSError, pygame.error):
            self.toasts.adicionar(t("OPS!"), t("NÃO DEU PARA SALVAR A FOTO"), "", "erro")
            return
        self._flash = 0.25
        self.audio.som("obturador")
        self.toasts.adicionar(t("FOTO SALVA!"), f"fotos/{nome}", "", None)
        progresso.contar(self, "fotos")

    def _atualizar_transicao(self, dt):
        passo = dt / TEMPO_TRANSICAO

        if self._fase == "saindo":
            self._fade = min(1.0, self._fade + passo)
            if self._fade >= 1.0:
                self._ativar(self._proxima)
                self._proxima = None
                self._fase = "entrando"

        elif self._fase == "entrando":
            self._fade = max(0.0, self._fade - passo)
            if self._fade <= 0.0:
                self._fase = None


if __name__ == "__main__":
    # Garante que os imports funcionem mesmo rodando de outra pasta
    sys.path.insert(0, BASE_DIR)
    os.chdir(BASE_DIR)
    try:
        App().rodar()
    except Exception:
        # No .exe não há console: o erro vai para erro.log (ao lado dos saves)
        import traceback
        try:
            with open(caminho_dados("erro.log"), "w", encoding="utf-8") as f:
                traceback.print_exc(file=f)
        except OSError:
            pass
        raise
    sys.exit()
