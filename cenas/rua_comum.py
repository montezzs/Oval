import datetime

from core import perfis
from core.jogador import Jogador
from core.necessidades import Necessidades, NOMES

# ============================================================
# PERFIS DOS OVOS (para a tela inicial e a vizinhança)
# ============================================================
# Cópias SÓ DE LEITURA de cada ovo da rua: aparência, fachada,
# necessidades (com o tempo offline simulado, sem gravar) e o
# "status" que aparece no balão da casa.


class Perfil:

    def __init__(self, slot):
        self.slot = slot
        self.estado = perfis.estado_slot(slot)      # vazio / ok / corrompido
        self.save = None
        self.jogador = None
        self.necessidades = {}
        self.status = ("", (230, 230, 240), False)
        if self.estado == "ok":
            self.save = perfis.ler_ovo(slot)
            if self.save is None:
                self.estado = "corrompido"
                return
            self.jogador = Jogador(self.save)
            nec = Necessidades(self.save)           # simula o offline (não grava)
            self.necessidades = {n: nec.valor(n) for n in NOMES}
            self.status = self._calcular_status()

    @property
    def ocupado(self):
        return self.estado == "ok"

    @property
    def nome(self):
        return self.jogador.nome if self.jogador else ""

    @property
    def casa(self):
        return self.save["casa"] if self.save else None

    @property
    def cor(self):
        return self.jogador.cor if self.jogador else (200, 200, 200)

    @property
    def dormindo(self):
        return bool(self.save and self.save["diario"].get("dormindo"))

    @property
    def carta_nova(self):
        return bool(self.save and any(not c.get("lida") for c in self.save["cartas"]
                                      if isinstance(c, dict)))

    def _plantas_prontas(self):
        # O Jardim simula o crescimento offline (numa cópia: não grava)
        from types import SimpleNamespace
        from cenas.casa_extras.jardim import Jardim
        ctx = SimpleNamespace(app=SimpleNamespace(save=self.save))
        jardim = Jardim(ctx)
        return any(jardim.pronta(c) for c in self.save["jardim"])

    def _calcular_status(self):
        n = self.necessidades
        vermelho, amarelo = (230, 70, 70), (255, 214, 64)
        if n["higiene"] < 20:
            return "PRECISA DE BANHO!", vermelho, True
        if n["fome"] < 25:
            return "ESTÁ COM FOME!", vermelho, True
        if n["energia"] < 25:
            return "ESTÁ COM SONO!", vermelho, True
        if n["diversao"] < 25:
            return "QUER BRINCAR!", vermelho, True
        try:
            if self._plantas_prontas():
                return "PLANTAS PRONTAS!", amarelo, True
        except Exception:
            pass
        if self.save["diario"].get("bau_ultimo") != datetime.date.today().isoformat():
            return "BAÚ DO DIA ESPERANDO!", amarelo, True
        if self.carta_nova:
            return "CHEGOU CARTA!", amarelo, True
        if all(v >= 70 for v in n.values()):
            return "OVO FELIZ! ★", (90, 200, 90), False
        return "TUDO BEM POR AQUI.", (230, 230, 240), False


def carregar_perfis():
    return [Perfil(s) for s in range(perfis.MAX_SLOTS)]
