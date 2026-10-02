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


def arquivo(nome):
    return os.path.join(PASTA_TRILHAS, nome + ".mp3")


@functools.lru_cache(maxsize=None)
def existe(nome):
    return os.path.exists(arquivo(nome))
