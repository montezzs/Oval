# ============================================================
# LISTA DE MINI JOGOS
# ============================================================
# A ordem aqui é a ordem dos cards no menu de jogos. Os jogos
# multiplayer (MULTI = True) aparecem sozinhos na aba
# "2 JOGADORES"; os outros na aba "SOLO".

# ---------------- Originais ----------------
from jogos.cobrinha import Cobrinha
from jogos.campo_minado import CampoMinado
from jogos.memoria import Memoria
from jogos.volei import Volei
from jogos.chuva import ChuvaComida
from jogos.pulo import PuloNuvens
from jogos.voador import OvoVoador

# ---------------- Novos (solo) ----------------
from jogos.ovo_corredor import OvoCorredor
from jogos.ovonoide import Ovonoide
from jogos.ovo_2048 import Ovo2048
from jogos.mini_golfe import MiniGolfe
from jogos.atravessa import Atravessa
from jogos.coral_ovos import CoralOvos
from jogos.ovo_colher import OvoColher
from jogos.ovotris import Ovotris
from jogos.toupeiras import Toupeiras
from jogos.salto_lago import SaltoLago
from jogos.pescaria import Pescaria
from jogos.descida_neve import DescidaNeve
from jogos.invasores import Invasores
from jogos.liga_ovos import LigaOvos
from jogos.lanchonete import Lanchonete
from jogos.ovo_ritmo import OvoRitmo
from jogos.ovo_man import OvoMan
from jogos.ninho_arrumado import NinhoArrumado
from jogos.estoura_bolha import EstouraBolha
from jogos.ovo_estrada import OvoEstrada
from jogos.ovo_sobrevivente import OvoSobrevivente
from jogos.micro_ovo import MicroOvo
from jogos.pinball_ovo import PinballOvo
from jogos.ovo_cozinheiro import OvoCozinheiro

# ---------------- Novos (2 jogadores) ----------------
from jogos.sumo_ovo import SumoOvo
from jogos.hoquei_ovo import HoqueiOvo
from jogos.guerra_tinta import GuerraTinta
from jogos.futebol_ovo import FutebolOvo
from jogos.ovo_bomba import OvoBomba
from jogos.corrida_rua import CorridaRua

# ---------------- Contra BOT ou 2 jogadores ----------------
from jogos.xadegg import Xadegg
from jogos.quatro_linha import QuatroEmLinha
from jogos.pontinhos import Pontinhos
from jogos.jogo_velha import JogoVelha
from jogos.ovo_kombat import OvoKombat
from jogos.thumb_fighter import ThumbFighter
from jogos.boliche import Boliche
from jogos.dardos import Dardos
from jogos.rei_quintal import ReiQuintal

JOGOS = [
    Cobrinha, CampoMinado, Memoria, Volei, ChuvaComida, PuloNuvens, OvoVoador,
    OvoCorredor, Ovonoide, Ovo2048, MiniGolfe, Atravessa, CoralOvos, OvoColher,
    Ovotris, Toupeiras, SaltoLago, Pescaria, DescidaNeve, Invasores, LigaOvos,
    Lanchonete, OvoRitmo, OvoMan, NinhoArrumado, EstouraBolha, OvoEstrada,
    OvoSobrevivente, MicroOvo, PinballOvo, OvoCozinheiro,
    SumoOvo, HoqueiOvo, GuerraTinta, FutebolOvo, OvoBomba, CorridaRua,
    Xadegg, QuatroEmLinha, Pontinhos, JogoVelha, OvoKombat, ThumbFighter, Boliche, Dardos, ReiQuintal,
]
