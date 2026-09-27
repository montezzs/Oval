import os
import sys

# ============================================================
# CAMINHOS
# ============================================================

# Rodando como .exe (PyInstaller)? Os arquivos do jogo (imagens,
# fonte, músicas) ficam dentro do pacote; os saves ficam ao lado
# do .exe, para não se perderem quando o jogo for fechado.
CONGELADO = getattr(sys, "frozen", False)

if CONGELADO:
    BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    DADOS_DIR = os.path.dirname(os.path.abspath(sys.executable))
    # Pasta do .exe sem permissão de escrita? Usa %APPDATA%\Oval
    if not os.access(DADOS_DIR, os.W_OK):
        DADOS_DIR = os.path.join(os.environ.get("APPDATA", DADOS_DIR), "Oval")
else:
    # Pasta do projeto (funciona mesmo rodando o jogo de outra pasta)
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DADOS_DIR = BASE_DIR

# Para testes: OVAL_DADOS=<pasta> grava saves/músicas geradas em outro lugar
if os.environ.get("OVAL_DADOS"):
    DADOS_DIR = os.environ["OVAL_DADOS"]


def caminho(*partes):
    """Monta um caminho absoluto a partir da pasta do projeto."""
    return os.path.join(BASE_DIR, *partes)


def caminho_dados(*partes):
    """Caminho de um arquivo gravável (saves, músicas geradas)."""
    return os.path.join(DADOS_DIR, *partes)


FONTE = caminho("Fonts", "PressStart2P-Regular.ttf")
PASTA_MUSICAS = caminho("musicas")
# Trilhas que já vêm prontas com o jogo
PASTA_TRILHAS = caminho("musicas", "trilhas")
# Trilhas geradas na hora (quando não vieram prontas)
PASTA_TRILHAS_GERADAS = caminho_dados("musicas", "trilhas") if CONGELADO else PASTA_TRILHAS
ARQUIVO_SAVE = caminho_dados("save.json")          # save antigo (1 ovo só)
PASTA_SAVES = caminho_dados("saves")

# ============================================================
# JANELA
# ============================================================

LARGURA = 1024
ALTURA = 720
TITULO = "Oval"
VERSAO = "2.0"
FPS = 60

# ============================================================
# ÁUDIO
# ============================================================

FREQUENCIA_AUDIO = 44100
VOLUME_PADRAO = 0.25           # volume inicial da música (0.0 a 1.0)
VOLUMES = [0.0, 0.25, 0.5, 0.75, 1.0]

# Ganho de cada faixa: a Ovein.mp3 é mais alta que as trilhas
# geradas, então é atenuada para todas soarem parecidas
GANHO_FAIXA = {
    "ovein": 0.3,
}
GANHO_FAIXA_PADRAO = 0.45

# ============================================================
# CORES
# ============================================================

BRANCO = (255, 255, 255)
PRETO = (0, 0, 0)
CINZA = (120, 120, 130)
ESCURO = (22, 24, 38)
AMARELO = (255, 214, 64)
VERMELHO = (230, 70, 70)
VERDE = (90, 200, 90)
AZUL = (60, 150, 230)
ROXO = (140, 90, 210)
LARANJA = (255, 150, 50)

# Cores da interface
UI_FUNDO = (32, 36, 58)
UI_BORDA = (255, 255, 255)
UI_DESTAQUE = (255, 196, 60)
UI_BOTAO = (58, 66, 104)
UI_BOTAO_HOVER = (84, 96, 150)
UI_SOMBRA = (0, 0, 0, 110)
