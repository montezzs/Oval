import copy
import json
import os

from settings import *

# ============================================================
# SAVE
# ============================================================
# Guarda nome, aparência, opções de som e recordes num JSON
# para não perder nada quando o jogo for fechado.

PADRAO = {
    "nome": "",
    "ovo": 0,
    "cabelo": 0,
    "olho": 0,
    "boca": 0,
    "volume": VOLUME_PADRAO,
    "sons": True,
    "recordes": {},
    "janela": [1024, 720],

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
    "sempre_dia": False,
    "album": [],                # borboletas já pegas
    "diario": {},               # baú diário, desafio do ROBERT, limites do dia
    "jogados": [],              # ids de jogos já jogados (jukebox)
}


class Save:

    def __init__(self, dados=None):
        self.dados = copy.deepcopy(PADRAO)

        if dados:
            for chave, valor in dados.items():
                if chave not in PADRAO:
                    continue
                padrao = PADRAO[chave]
                # bool é subclasse de int: não deixa True virar número
                if isinstance(padrao, bool) != isinstance(valor, bool):
                    continue
                if isinstance(valor, type(padrao)):
                    self.dados[chave] = valor
                # int aceito onde o padrão é float
                elif isinstance(padrao, float) and isinstance(valor, int):
                    self.dados[chave] = float(valor)

    # --------------------------------------------------------

    @classmethod
    def carregar(cls):
        try:
            with open(ARQUIVO_SAVE, "r", encoding="utf-8") as f:
                return cls(json.load(f))
        except (OSError, ValueError):
            return cls()

    def salvar(self):
        try:
            temp = ARQUIVO_SAVE + ".tmp"
            with open(temp, "w", encoding="utf-8") as f:
                json.dump(self.dados, f, ensure_ascii=False, indent=2)
            os.replace(temp, ARQUIVO_SAVE)
        except OSError:
            pass

    # --------------------------------------------------------

    def __getitem__(self, chave):
        return self.dados[chave]

    def __setitem__(self, chave, valor):
        self.dados[chave] = valor

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
