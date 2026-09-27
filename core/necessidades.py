import time

# ============================================================
# NECESSIDADES DO OVO (estilo Pou)
# ============================================================
# FOME, ENERGIA, DIVERSÃO e HIGIENE vão de 0 a 100.
# O ovo NUNCA adoece: valores baixos só mudam a carinha dele e
# tiram o bônus "OVO FELIZ" (x1.10 moedas quando tudo >= 70).
#
# Com o jogo fechado as barras caem pela metade da velocidade,
# mas o tempo offline nunca derruba uma barra abaixo de 20.

NOMES = ["fome", "energia", "diversao", "higiene"]
ROTULOS = {"fome": "FOME", "energia": "ENERGIA", "diversao": "DIVERSÃO", "higiene": "HIGIENE"}

# Queda por minuto com o jogo aberto
TAXAS = {"fome": 0.6, "energia": 0.4, "diversao": 0.5, "higiene": 0.3}

LIMITE_FELIZ = 70
PISO_OFFLINE = 20
DORMIR_POR_SEGUNDO = 1 / 3        # energia +1 a cada 3 s dormindo


class Necessidades:

    def __init__(self, save):
        self.save = save
        dados = save["necessidades"]
        self.valores = {}
        for n in NOMES:
            v = dados.get(n, 80) if isinstance(dados, dict) else 80
            self.valores[n] = float(v) if isinstance(v, (int, float)) else 80.0
            self.valores[n] = max(0.0, min(100.0, self.valores[n]))

        self._aplicar_offline()
        self._relogio_salvar = 0.0

    # --------------------------------------------------------

    def _aplicar_offline(self):
        ultimo = self.save["ultimo_tempo"]
        agora = time.time()
        if ultimo <= 0 or agora <= ultimo:
            return
        minutos = min((agora - ultimo) / 60.0, 60 * 24 * 7)
        for n in NOMES:
            antes = self.valores[n]
            depois = antes - TAXAS[n] * 0.5 * minutos
            # O tempo fechado não derruba abaixo de 20
            self.valores[n] = max(min(antes, PISO_OFFLINE), depois)

    def valor(self, nome):
        return self.valores.get(nome, 0.0)

    def mudar(self, nome, delta):
        if nome in self.valores:
            self.valores[nome] = max(0.0, min(100.0, self.valores[nome] + delta))

    def feliz(self):
        return all(v >= LIMITE_FELIZ for v in self.valores.values())

    def pos_minijogo(self):
        """Brincar cansa e suja, mas diverte!"""
        self.mudar("energia", -4)
        self.mudar("higiene", -4)
        self.mudar("diversao", 12)

    # --------------------------------------------------------

    def atualizar(self, dt, dormindo=False, mult_sono=1.0, mult_higiene=1.0,
                  mult_fome=1.0, mult_diversao=1.0):
        minuto = dt / 60.0
        self.mudar("fome", -TAXAS["fome"] * minuto * mult_fome)
        self.mudar("diversao", -TAXAS["diversao"] * minuto * mult_diversao)
        self.mudar("higiene", -TAXAS["higiene"] * minuto * mult_higiene)
        if dormindo:
            self.mudar("energia", DORMIR_POR_SEGUNDO * mult_sono * dt)
        else:
            self.mudar("energia", -TAXAS["energia"] * minuto)

        self._relogio_salvar += dt
        if self._relogio_salvar > 15:
            self._relogio_salvar = 0.0
            self.salvar()

    def salvar(self):
        self.save["necessidades"] = {n: round(v, 2) for n, v in self.valores.items()}
        self.save["ultimo_tempo"] = time.time()
        self.save.salvar()
