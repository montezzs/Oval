import functools
import os

from settings import *

# ============================================================
# TRILHAS SONORAS
# ============================================================
# Cada tela / mini jogo tem a sua música em musicas/trilhas/<id>.mp3.
# Elas são compostas em código e gravadas por:
#   python ferramentas/compor_musicas.py
# (as partituras ficam em ferramentas/partituras.py e os .mid,
# para editar no FL Studio, em musicas/midi/)


# Temas das telas do jogo (tela inicial, rua, loja...). Também
# aparecem na JUKEBOX (seção TEMAS) depois de ouvidos uma vez.
TEMAS = (
    "abertura",         # TELA INICIAL
    "rua_dos_ovos",     # VIZINHANÇA (dia)
    "rua_noite",        # VIZINHANÇA (noite)
    "dia_de_chuva",     # CASA com chuva
    "maos_a_obra",      # REFORMA / MUDANÇA
    "vitrine",          # LOJA
    "nasce_um_ovo",     # NOME + CRIADOR
    "cancao_de_ninar",  # CASA com a luz apagada
    "quintal_feliz",    # SOL (quintal, de dia)
)

NOMES_TEMAS = {
    "casa": "TEMA DA CASA",
    "ovein": "OVEIN (CLÁSSICO)",
    "abertura": "ABERTURA",
    "rua_dos_ovos": "RUA DOS OVOS",
    "rua_noite": "RUA DOS OVOS (NOITE)",
    "dia_de_chuva": "DIA DE CHUVA",
    "maos_a_obra": "MÃOS À OBRA",
    "vitrine": "VITRINE",
    "nasce_um_ovo": "NASCE UM OVO",
    "cancao_de_ninar": "CANÇÃO DE NINAR",
    "quintal_feliz": "QUINTAL FELIZ",
}

DICAS_TEMAS = {
    "cancao_de_ninar": "DICA: APAGUE A LUZ PARA DORMIR",
    "dia_de_chuva": "DICA: ESPERE UM DIA DE CHUVA",
    "rua_noite": "DICA: VISITE A RUA DE NOITE",
    "quintal_feliz": "DICA: VÁ AO QUINTAL DE DIA",
    "vitrine": "DICA: VISITE A LOJA",
    "maos_a_obra": "DICA: REFORME SUA CASA",
}


def arquivo(nome):
    return os.path.join(PASTA_TRILHAS, nome + ".mp3")


@functools.lru_cache(maxsize=None)
def existe(nome):
    return os.path.exists(arquivo(nome))
