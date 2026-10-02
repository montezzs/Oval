# ============================================================
# TROFÉUS DOS MINI JOGOS
# ============================================================
# Uma tabela central com os limites de BRONZE / PRATA / OURO de
# cada jogo (seção E do design). Usada pela ESTANTE DE TROFÉUS
# da casa e pelo DESAFIO DO DIA do ROBERT.
#
# Tipos de regra:
#   "maior"    -> recorde (maior é melhor) >= limite
#   "menor"    -> recorde (menor é melhor) <= limite
#   "opcao"    -> venceu na dificuldade: bronze=0, prata=1, ouro=2
#   "partidas" -> total de partidas decididas no multiplayer

NIVEIS = ["bronze", "prata", "ouro"]


def _r(ouro, prata=None, bronze=None, tipo="maior"):
    if tipo == "maior":
        prata = prata if prata is not None else max(1, round(ouro * 0.6))
        bronze = bronze if bronze is not None else max(1, round(ouro * 0.3))
    return dict(tipo=tipo, bronze=bronze, prata=prata, ouro=ouro)


REGRAS = {
    # Jogos originais
    "cobrinha": _r(40),
    "minado": dict(tipo="opcao"),
    "memoria": dict(tipo="opcao"),
    "volei": dict(tipo="opcao", vitoria=17),
    "chuva": _r(300),
    "pulo": _r(1000),
    "voador": _r(50),
    # Novos
    "ovo_corredor": _r(2500),
    "ovonoide": _r(8000),
    "ovo_2048": _r(20000),
    "mini_golfe": _r(27, 32, 38, tipo="menor"),
    "atravessa": _r(5000),
    "coral_ovos": _r(20),
    "ovo_colher": _r(600),          # pontos = metros + 25 por checkpoint
    "ovotris": _r(30000),
    "toupeiras": _r(1500),
    "salto_lago": _r(100),
    "pescaria": _r(1200),
    "descida_neve": _r(3000),
    "invasores": _r(6000),
    "liga_ovos": _r(3000),
    "lanchonete": _r(900),
    "ovo_ritmo": _r(100000),
    "ovo_man": _r(12000),
    "ninho_arrumado": _r(60, 40, 20),
    "estoura_bolha": _r(6000),
    "ovo_estrada": _r(2000),
    # Mais novos
    "ovo_sobrevivente": _r(8000, 5000, 2500),
    "micro_ovo": _r(30, 18, 8),
    "pinball_ovo": _r(90000, 45000, 20000),
    "ovo_cozinheiro": _r(1600),
}

PARTIDAS = dict(tipo="partidas", bronze=1, prata=10, ouro=30)


def regra(jogo):
    if getattr(jogo, "HIBRIDO", False):
        return REGRAS.get(jogo.ID, dict(tipo="opcao"))
    if getattr(jogo, "MULTI", False):
        return REGRAS.get(jogo.ID, PARTIDAS)
    return REGRAS.get(jogo.ID)


def _melhor(save, jogo, menor):
    if jogo.OPCOES:
        valores = [save.recorde(f"{jogo.ID}_{i}") for i in range(len(jogo.OPCOES))]
    else:
        valores = [save.recorde(jogo.ID)]
    valores = [v for v in valores if isinstance(v, (int, float))]
    if not valores:
        return None
    return min(valores) if menor else max(valores)


def nivel(save, jogo):
    """Devolve ("ouro"|"prata"|"bronze"|None, texto do recorde)."""
    r = regra(jogo)
    if r is None:
        return None, ""
    tipo = r["tipo"]

    if tipo == "partidas":
        total = 0
        chaves = [f"{jogo.ID}_{i}_vitorias" for i in range(len(jogo.OPCOES))] \
            if jogo.OPCOES else [f"{jogo.ID}_vitorias"]
        for c in chaves:
            v = save["recordes"].get(c)
            if isinstance(v, list) and len(v) == 2:
                total += v[0] + v[1]
        obtido = None
        for n in NIVEIS:
            if total >= r[n]:
                obtido = n
        return obtido, f"{total} partidas"

    if tipo == "opcao":
        obtido = None
        for i, n in enumerate(NIVEIS):
            v = save.recorde(f"{jogo.ID}_{i}")
            venceu = v is not None and (v >= r["vitoria"] if "vitoria" in r else True)
            if venceu:
                obtido = n
        return obtido, "venceu " + (jogo.OPCOES[NIVEIS.index(obtido)] if obtido else "-")

    menor = tipo == "menor"
    melhor = _melhor(save, jogo, menor)
    if melhor is None:
        return None, ""
    obtido = None
    for n in NIVEIS:
        if (melhor <= r[n]) if menor else (melhor >= r[n]):
            obtido = n
    return obtido, f"recorde {jogo.formatar(melhor)}"


def lista(save):
    """[(titulo, nivel, texto)] de todos os troféus conquistados."""
    from jogos import JOGOS
    resultado = []
    for jogo in JOGOS:
        n, txt = nivel(save, jogo)
        if n:
            resultado.append((jogo.TITULO_CURTO or jogo.TITULO, n, txt))
    ordem = {"ouro": 0, "prata": 1, "bronze": 2}
    resultado.sort(key=lambda x: ordem[x[1]])
    return resultado


def meta_desafio(jogo):
    """(tipo, meta, texto) para o desafio do dia do ROBERT."""
    r = regra(jogo)
    nome = jogo.TITULO_CURTO or jogo.TITULO
    if getattr(jogo, "MULTI", False):
        return "vitoria", 1, f"Jogue {nome} com um amigo e VENÇA!"
    if r is None or r["tipo"] == "opcao":
        return "vitoria", 1, f"Vença uma partida de {nome}!"
    if r["tipo"] == "menor":
        return "menor", r["bronze"], f"Faça {jogo.formatar(r['bronze'])} ou menos em {nome}!"
    return "maior", r["bronze"], f"Faça {jogo.formatar(r['bronze'])} em {nome}!"
