import os
import sys

# ============================================================
# CAMINHOS
# ============================================================

# Pasta do projeto (funciona mesmo rodando o jogo de outra pasta)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# No .exe (PyInstaller) os arquivos ficam numa pasta temporária que some
# ao fechar o jogo, então o save vai para %APPDATA%\Oval
if getattr(sys, "frozen", False):
    PASTA_DADOS = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "Oval")
    os.makedirs(PASTA_DADOS, exist_ok=True)
else:
    PASTA_DADOS = BASE_DIR


def caminho(*partes):
    """Monta um caminho absoluto a partir da pasta do projeto."""
    return os.path.join(BASE_DIR, *partes)


FONTE = caminho("Fonts", "PressStart2P-Regular.ttf")
PASTA_MUSICAS = caminho("musicas")
PASTA_TRILHAS = caminho("musicas", "trilhas")
PASTA_SFX = caminho("musicas", "sfx")
ARQUIVO_SAVE = os.path.join(PASTA_DADOS, "save.json")

# ============================================================
# JANELA
# ============================================================

LARGURA = 1024
ALTURA = 720
TITULO = "Oval"
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
