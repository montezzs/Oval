import os
import sys

# ============================================================
# CAMINHOS
# ============================================================

# Rodando como .exe (PyInstaller)? Os arquivos do jogo (imagens,
# fonte, músicas) ficam dentro do pacote, numa pasta temporária que
# some ao fechar o jogo; por isso os saves vão para %APPDATA%\Oval.
CONGELADO = getattr(sys, "frozen", False)

if CONGELADO:
    BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    DADOS_DIR = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "Oval")
else:
    # Pasta do projeto (funciona mesmo rodando o jogo de outra pasta)
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DADOS_DIR = BASE_DIR

# Para testes: OVAL_DADOS=<pasta> grava saves, fotos e logs em outro lugar
if os.environ.get("OVAL_DADOS"):
    DADOS_DIR = os.environ["OVAL_DADOS"]

if CONGELADO:
    os.makedirs(DADOS_DIR, exist_ok=True)

PASTA_DADOS = DADOS_DIR


def caminho(*partes):
    """Monta um caminho absoluto a partir da pasta do projeto."""
    return os.path.join(BASE_DIR, *partes)


def caminho_dados(*partes):
    """Caminho de um arquivo gravável (saves, fotos, logs)."""
    return os.path.join(DADOS_DIR, *partes)


FONTE = caminho("Fonts", "PressStart2P-Regular.ttf")
PASTA_MUSICAS = caminho("musicas")
# Trilhas que já vêm prontas com o jogo
PASTA_TRILHAS = caminho("musicas", "trilhas")
PASTA_SFX = caminho("musicas", "sfx")
ARQUIVO_SAVE = caminho_dados("save.json")          # save antigo (1 ovo só)
PASTA_SAVES = caminho_dados("saves")

# ============================================================
# JANELA
# ============================================================

LARGURA = 1024
ALTURA = 720
TITULO = "Oval"
VERSAO = "2.1"
FPS = 60

# ============================================================
# ÁUDIO
# ============================================================

FREQUENCIA_AUDIO = 44100
VOLUME_PADRAO = 0.25           # volume inicial da música (0.0 a 1.0)
VOLUMES = [0.0, 0.25, 0.5, 0.75, 1.0]

# Ganho de cada faixa: a Ovein.mp3 é mais alta que as trilhas
# (normalizadas em -16 LUFS), então é atenuada para todas soarem parecidas
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

# Cores da interface (paleta "cozy": azul-ameixa noturno + creme + mel)
UI_FUNDO = (36, 38, 66)
UI_BORDA = (255, 246, 228)        # creme: menos duro que o branco puro
UI_DESTAQUE = (255, 200, 72)
UI_BOTAO = (62, 68, 112)
UI_BOTAO_HOVER = (92, 104, 168)
UI_SOMBRA = (0, 0, 0, 110)

UI_PAINEL = (32, 34, 60)          # fundo dos painéis por cima dos jogos
UI_PAINEL_HUD = (26, 28, 50)      # caixinhas pequenas de HUD
UI_TEXTO = (255, 250, 240)        # texto principal (branco quentinho)
UI_TEXTO_SUAVE = (190, 204, 250)  # texto secundário (dicas, recorde)
UI_CONTORNO = (26, 18, 40)        # contorno de títulos (legibilidade)
UI_SUCESSO = (70, 175, 100)
UI_SUCESSO_HOVER = (96, 205, 126)
UI_PERIGO = (196, 70, 82)
UI_PERIGO_HOVER = (230, 98, 108)
UI_MOEDA_FUNDO = (64, 44, 16)
