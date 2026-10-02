import copy
import json
import os

from settings import *

# ============================================================
# SAVE
# ============================================================
# Cada ovo tem o seu próprio arquivo (saves/ovo_N.json) com nome,
# aparência, moedas, recordes, casa, jardim... As preferências de
# quem está jogando (volume, sons, tamanho da janela...) ficam num
# arquivo só (saves/global.json), carregado como Config.

PADRAO = {
    "nome": "",
    "ovo": 0,
    "cabelo": 0,
    "olho": 0,
    "boca": 0,
    "recordes": {},

    # Economia / loja
    "moedas": 0,
    "moedas_total": 0,          # tudo que já ganhou (estatística)
    "inventario": [],           # ids de tudo que já comprou
    "equipado": {},             # slot -> id do cosmético
    "pet": "",                  # id do pet ativo ("" = nenhum)
    "moveis": [],               # móveis que estão aparecendo na casa/sol
    "comida": {},               # id da comida -> quantidade

    # Vida do ovo (casa / sol)
    "necessidades": {},
    "jardim": [],
    "ultimo_tempo": 0.0,
    "album": [],                # borboletas já pegas
    "diario": {},               # baú diário, desafio do ROBERT, limites do dia
    "jogados": [],              # ids de jogos já jogados (jukebox)

    # Vizinhança
    "casa": {},                 # fachada (ver core/fachada.py)
    "criado_em": 0.0,
    "cartas": [],               # cartas dos vizinhos

    # Progresso (core/progresso.py)
    "xp": 0,
    "nivel": 1,
    "conquistas": [],           # ids das conquistas liberadas
    "stats": {},                # contadores (partidas, banhos, ouros...)
}

CONFIG_PADRAO = {
    "versao": 2,
    "volume": VOLUME_PADRAO,
    "sons": True,
    "volume_sfx": 1.0,          # volume dos efeitos (0.0 a 1.0)
    "tutorial": -1,             # passo do tutorial (-1 = decidir; 99 = acabou)
    "mostrar_fps": False,
    "reduzir_tremor": False,
    "daltonico": False,
    "amigos": [],               # códigos de amigos (core/codigo.py)
    "janela": [1024, 720],
    "sempre_dia": False,
    "j2": [],                   # aparência sorteada do J2 [ovo, cabelo, olho, boca]
    "j2_slot": -1,              # ou a casa do vizinho que joga como J2
    "ultimo_ovo": -1,
    "temas_ouvidos": [],
    "viu_rua": False,
    "tem_ovo": False,           # já criou o 1º ovo (senão: 1ª execução)
    "migrado": False,
    "banner_migracao": False,
    "idioma": None,             # "pt" / "en" / "es" (None = perguntar na abertura)
}

# Chaves que moram no Config mesmo se alguém pedir ao save do ovo
CHAVES_GLOBAIS = {"volume", "sons", "volume_sfx", "janela", "sempre_dia", "j2", "j2_slot"}


def _validar(dados, padrao):
    """Copia do `dados` só as chaves conhecidas e com o tipo certo."""
    saida = copy.deepcopy(padrao)
    if not isinstance(dados, dict):
        return saida
    for chave, valor in dados.items():
        if chave not in padrao:
            continue
        p = padrao[chave]
        # Padrão None = "ainda não escolhido": aceita texto ou None
        if p is None:
            if valor is None or isinstance(valor, str):
                saida[chave] = valor
            continue
        # bool é subclasse de int: não deixa True virar número
        if isinstance(p, bool) != isinstance(valor, bool):
            continue
        if isinstance(valor, type(p)):
            saida[chave] = valor
        # int aceito onde o padrão é float
        elif isinstance(p, float) and isinstance(valor, int):
            saida[chave] = float(valor)
    return saida


def gravar_json(arquivo, dados):
    """Gravação atômica: nunca deixa um arquivo pela metade."""
    pasta = os.path.dirname(arquivo)
    if pasta:
        os.makedirs(pasta, exist_ok=True)
    temp = arquivo + ".tmp"
    with open(temp, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    os.replace(temp, arquivo)


class Save:

    PADRAO = PADRAO

    def __init__(self, dados=None, arquivo=None, config=None):
        self.dados = _validar(dados, self.PADRAO)
        # arquivo = None -> rascunho / cópia só de leitura (nunca grava)
        self.arquivo = arquivo
        self.config = config

    # --------------------------------------------------------

    @staticmethod
    def ler(arquivo):
        """(dict | None, "ok" | "ausente" | "corrompido")."""
        if not os.path.exists(arquivo):
            return None, "ausente"
        try:
            with open(arquivo, "r", encoding="utf-8") as f:
                dados = json.load(f)
        except (OSError, ValueError, UnicodeDecodeError):
            return None, "corrompido"
        if not isinstance(dados, dict):
            return None, "corrompido"
        return dados, "ok"

    def salvar(self):
        if self.arquivo is None:
            return
        try:
            gravar_json(self.arquivo, self.dados)
        except OSError:
            pass

    # --------------------------------------------------------

    def __getitem__(self, chave):
        if chave in CHAVES_GLOBAIS and self.config is not None:
            return self.config[chave]
        return self.dados[chave]

    def __setitem__(self, chave, valor):
        if chave in CHAVES_GLOBAIS and self.config is not None:
            self.config[chave] = valor
            self.config.salvar()
            return
        self.dados[chave] = valor

    def get(self, chave, padrao=None):
        try:
            return self[chave]
        except KeyError:
            return padrao

    # --------------------------------------------------------
    # MOEDAS
    # --------------------------------------------------------

    def ganhar(self, qtd):
        qtd = max(0, int(qtd))
        self.dados["moedas"] += qtd
        self.dados["moedas_total"] += qtd
        self.salvar()
        return qtd

    def gastar(self, qtd):
        """Tenta gastar. Devolve True se tinha moedas suficientes."""
        if qtd > self.dados["moedas"]:
            return False
        self.dados["moedas"] -= qtd
        self.salvar()
        return True

    # --------------------------------------------------------
    # RECORDES
    # --------------------------------------------------------

    def recorde(self, chave):
        return self.dados["recordes"].get(chave)

    def registrar(self, chave, valor, menor_melhor=False):
        """
        Registra um resultado. Devolve True se for novo recorde.
        """
        atual = self.recorde(chave)

        if atual is None or (valor < atual if menor_melhor else valor > atual):
            self.dados["recordes"][chave] = valor
            self.salvar()
            return True

        return False


class Config(Save):
    """Preferências globais (saves/global.json)."""

    PADRAO = CONFIG_PADRAO

    def __init__(self, dados=None, arquivo=None):
        super().__init__(dados, arquivo, config=None)
