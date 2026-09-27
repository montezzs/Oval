import math

from core import pets as P
from core.pets import _Especie, _olho, _bochecha, _q, _envelope, _misturar

# ============================================================
# PETS NOVOS (coleção "Vizinhança")
# ============================================================
# Mesmo sistema de core/pets.py: cada espécie monta uma POSE
# (tupla arredondada, para o cache) e desenha com o _Pincel em
# coordenadas de design (pés em (0, 0), olhando para a direita).
# Registrados no CATALOGO/_ESPECIES quando este módulo é importado.

NOVOS = {
    "tartaruga": dict(nome="TUCA", especie="TARTARUGA", preco=280, raridade="INCOMUM",
                      voa=False, talento="Fome cai 15% mais devagar"),
    "coelho": dict(nome="FLOCO", especie="COELHINHO", preco=450, raridade="RARO",
                   voa=False, talento="Acha 1 cenoura por dia no SOL"),
    "capivara": dict(nome="CAPI", especie="CAPIVARA", preco=1400, raridade="EPICO",
                     voa=False, talento="Diversão cai 25% mais devagar"),
}


# ------------------------------------------------------------
# TARTARUGA (TUCA)
# ------------------------------------------------------------

class _Tartaruga(_Especie):
    id = "tartaruga"
    frente = 30
    caixa = (-34, -40, 38, 4)
    borda = (70, 110, 40)
    sombra = 50
    topo = (0, -36)
    boca = (30, -12)
    passo_px = 22
    vel_mult = 0.6
    idles = (("esconder", 2.6), ("olhar", 2.0))
    reacao_dur = 1.0
    piscar_fase = 0.7
    CASCO = (110, 160, 70)
    PELE = (160, 200, 110)
    HEX = (80, 130, 50)

    def pose(self, e):
        o = e.olhos
        a = e.acao
        if a == "andar":
            return ("andar", int(e.passo * 4) % 2, o, 0, 0)
        if a == "dormir":
            return ("parado", 0, "dormindo", 1, 0)
        if a == "reacao":
            return ("parado", 0, "feliz", 0, int(_q(math.sin(e.ta * 18) * 8 * (1 - e.u), 4)))
        if a == "feliz":
            return ("andar", int(e.t * 6) % 2, "feliz", 0, 0)
        if a == "idle" and e.variante == "esconder":
            k = _envelope(e.ta, 2.6, 0.3)
            return ("parado", 0, "dormindo" if k > 0.5 else o, 1 if k > 0.5 else 0, 0)
        if a == "idle" and e.variante == "olhar":
            return ("parado", 1, o, 0, 0)
        return ("parado", 0, o, 0, 0)

    def desloc(self, e):
        if e.acao == "feliz":
            return 0.0, -abs(math.sin(e.t * 5)) * 6
        return 0.0, 0.0

    def desenhar(self, p, pose):
        tipo, f, olhos, dentro, tilt = pose
        B = self.borda
        p.girar(tilt, 0, -10)
        # Patinhas
        dy = [(0, -2), (-2, 0)][f] if tipo == "andar" else (0, 0)
        for i, x in enumerate((-15, -5, 7, 17)):
            p.forma(self.PELE, B, ("e", x, -3 + dy[i % 2], 4.5, 3.2))
        # Rabinho
        p.forma(self.PELE, B, ("p", [(-22, -9), (-30, -6), (-22, -5)]))
        # Cabeça (escondida = só a pontinha)
        if dentro:
            p.forma(self.PELE, B, ("c", 21, -11, 5))
            _olho(p, 23, -12, 1.6, "dormindo")
        else:
            hx = 26 if f == 0 else 27
            hy = -15 if f == 0 else -18
            p.forma(self.PELE, B, ("e", 19, -11, 6, 4), ("c", hx, hy, 8))
            _olho(p, hx + 2.5, hy - 2, 2.2, olhos)
            p.forma((60, 90, 40), None, ("a", hx + 3, hy + 2.5, 2.4, 1.4, 200, 340, 0.6))
            _bochecha(p, hx - 1, hy + 2.5, 2, 1.3, self.PELE)
        # Casco
        p.forma(self.CASCO, B, ("e", 0, -17, 22, 13))
        p.forma(_misturar(self.CASCO, (255, 255, 255), 0.25), None, ("e", -6, -23, 8, 3.5, 12))
        for hx, hy in ((-9, -16), (3, -20), (9, -11), (-2, -9)):
            pts = [(hx + 4.5 * math.cos(math.radians(60 * k)), hy + 4.5 * math.sin(math.radians(60 * k)))
                   for k in range(6)]
            p.forma(self.HEX, _misturar(self.HEX, B, 0.5), ("p", pts), w=0.5)
        p.forma(B, None, ("e", 0, -5.5, 22, 3))


# ------------------------------------------------------------
# COELHO (FLOCO)
# ------------------------------------------------------------

class _Coelho(_Especie):
    id = "coelho"
    frente = 24
    caixa = (-30, -70, 32, 4)
    borda = (200, 200, 215)
    sombra = 36
    topo = (12, -64)
    boca = (22, -26)
    passo_px = 60
    idles = (("farejar", 2.4), ("coçar", 1.6))
    reacao_dur = 1.2
    piscar_fase = 2.1
    PELO = (245, 245, 250)
    ROSA_O = (255, 180, 200)

    def pose(self, e):
        o = e.olhos
        a = e.acao
        if a == "andar":
            fr = e.passo % 1.0
            sq = 1 if fr < 0.2 else 0
            return (sq, 0, o, 0)
        if a == "dormir":
            return (1, -30, "dormindo", 0)
        if a == "reacao":
            return (0, int(_q(math.sin(e.ta * 20) * 40, 20)), "feliz", 1)
        if a == "feliz":
            return (0, int(_q(math.sin(e.t * 8) * 10, 10)), "feliz", 1)
        if a == "idle" and e.variante == "farejar":
            return (0, 0, o, int(e.ta * 8) % 2 + 1)
        if a == "idle" and e.variante == "coçar":
            return (0, 10, "feliz", 0)
        return (0, 0, o, 0)

    def desloc(self, e):
        if e.acao == "andar":
            fr = e.passo % 1.0
            if fr >= 0.2:
                u = (fr - 0.2) / 0.8
                return 0.0, -26 * 4 * u * (1 - u)
            return 0.0, 0.0
        if e.acao == "reacao":
            return 0.0, -30 * math.sin(math.pi * min(1.0, e.u))
        return super().desloc(e)

    def desenhar(self, p, pose):
        sq, orelha, olhos, nariz = pose
        B = self.borda
        if sq:
            p.escalar(1.15, 0.85, 0, 0)
        # Orelhas
        for ox, base_ang in ((7, 100), (15, 80)):
            p.salvar()
            p.girar(orelha * (1 if ox == 7 else -1) + (base_ang - 90), ox, -38)
            p.forma(self.PELO, B, ("e", ox, -50, 4.2, 13))
            p.forma(self.ROSA_O, None, ("e", ox, -49, 2, 9.5))
            p.restaurar()
        # Rabinho e patas
        p.forma(self.PELO, B, ("c", -19, -15, 5.5))
        p.forma(self.PELO, B, ("e", 8, -3, 7, 3.2), ("e", -8, -3, 6, 3))
        # Corpo e cabeça
        p.forma(self.PELO, B, ("e", -3, -15, 17, 13), ("c", 13, -30, 12))
        p.forma((255, 255, 255), None, ("e", 2, -11, 8, 5))
        _olho(p, 17, -32, 2.8, olhos)
        p.forma((255, 130, 160), None, ("e", 24 + (nariz == 2) * 0.6, -28.5, 2.2, 1.6))
        p.forma((150, 110, 120), None, ("a", 22.5, -25.5, 1.6, 1.2, 200, 340, 0.6))
        _bochecha(p, 14, -25, 2.8, 1.6, self.PELO)


# ------------------------------------------------------------
# CAPIVARA (CAPI)
# ------------------------------------------------------------

class _Capivara(_Especie):
    id = "capivara"
    frente = 34
    caixa = (-36, -62, 50, 4)
    borda = (110, 70, 40)
    sombra = 58
    topo = (26, -54)
    boca = (40, -26)
    passo_px = 34
    idles = (("relaxar", 4.0), ("mastigar", 2.0))
    reacao_dur = 1.6
    piscar_fase = 1.7
    COR = (160, 110, 70)
    FOCINHO = (120, 80, 50)

    def pose(self, e):
        o = e.olhos
        a = e.acao
        if a == "andar":
            return (int(e.passo * 4) % 2, o, 0, 0)
        if a == "dormir":
            return (0, "dormindo", 1, 0)
        if a in ("reacao", "feliz"):
            return (0, "dormindo" if a == "reacao" else "feliz", 1, int(e.t * 3) % 2)
        if a == "idle" and e.variante == "relaxar":
            return (0, "dormindo", 1, 0)
        if a == "idle" and e.variante == "mastigar":
            return (0, o, 0, int(e.ta * 6) % 2)
        return (0, o, 0, 0)

    def desenhar(self, p, pose):
        passo, olhos, tangerina, boca = pose
        B = self.borda
        # Patinhas curtas
        for i, x in enumerate((-22, -10, 8, 18)):
            dy = -1.5 if (passo and i % 2) or (not passo and i % 2 == 0 and False) else 0
            p.forma(self.FOCINHO, B, ("rr", x - 3, -9 + dy, 6, 9 - dy, 2))
        # Corpo
        p.forma(self.COR, B, ("rr", -30, -36, 58, 30, 13))
        p.forma(_misturar(self.COR, (255, 255, 255), 0.18), None, ("e", -8, -29, 14, 4))
        # Cabeça
        p.forma(self.COR, B, ("rr", 16, -46, 28, 23, 9), ("c", 22, -46, 3.4), ("c", 29, -47, 3.4))
        p.forma(self.FOCINHO, B, ("rr", 35, -38, 12, 14, 5), w=0.7)
        p.forma((60, 40, 30), None, ("c", 43, -34, 1.2), ("c", 43, -30, 1.2))
        if boca:
            p.forma((60, 40, 30), None, ("l", [(38, -25), (42, -26)], 0.8))
        _olho(p, 31, -40, 2.2, olhos)
        # A famosa tangerina na cabeça
        if tangerina:
            p.forma((255, 150, 40), (200, 100, 20), ("c", 26, -53, 6), w=0.8)
            p.forma((80, 160, 60), None, ("e", 29, -59, 3, 1.5, 30))
            p.forma((255, 200, 120), None, ("c", 24, -55, 1.6))


# ------------------------------------------------------------
# REGISTRO
# ------------------------------------------------------------

P.CATALOGO.update(NOVOS)
for _c in (_Tartaruga, _Coelho, _Capivara):
    P._ESPECIES[_c.id] = _c()
