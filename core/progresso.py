import time

# ============================================================
# PROGRESSO DO OVO: NÍVEL (XP) + CONQUISTAS
# ============================================================
# Tudo o que o ovo faz dá XP: jogar, comer, tomar banho, abrir o
# baú, cumprir o desafio do ROBERT... Subir de nível paga OVOEDAS
# (mais nos marcos 5, 10, 15...). As CONQUISTAS são metas de médio
# prazo contadas em save["stats"]; cada uma paga uma vez só.
#
# Quem chama (cenas, App) usa só:
#   ganhar_xp(app, qtd)          -> soma XP (e avisa se subiu)
#   contar(app, chave, n=1)      -> incrementa uma estatística
#   definir(app, chave, valor)   -> estatística "máxima" (streak, nível...)
# Os avisos aparecem como TOASTS em qualquer tela (App.toasts).

NIVEL_MAX = 30

XP_PARTIDA = 10
XP_VITORIA = 20
XP_COMER = 2
XP_BANHO = 6
XP_BAU = 15
XP_DESAFIO = 30
XP_CARINHO = 1


def xp_para(nivel):
    """XP que falta do nível `nivel` para o próximo."""
    return 60 + 40 * nivel


def premio_nivel(nivel):
    """OVOEDAS ao chegar no nível (marcos de 5 em 5 valem mais)."""
    return 100 if nivel % 5 == 0 else 20 + nivel * 2


def progresso(save):
    """(nível, xp dentro do nível, xp necessário) para barras."""
    nivel = max(1, save["nivel"])
    if nivel >= NIVEL_MAX:
        return nivel, 1, 1
    return nivel, save["xp"], xp_para(nivel)


def idade_dias(save):
    """Dias de vida do ovo (a partir do dia em que nasceu)."""
    criado = save["criado_em"]
    if not criado:
        return 1
    return max(1, int((time.time() - criado) // 86400) + 1)


# ------------------------------------------------------------
# CONQUISTAS
# ------------------------------------------------------------
# (id, nome, descrição, estatística, meta, prêmio)

CONQUISTAS = [
    ("partida_1", "PRIMEIRA PARTIDA", "Jogue um mini jogo", "partidas", 1, 20),
    ("partida_10", "JOGADOR", "Jogue 10 partidas", "partidas", 10, 50),
    ("partida_50", "VICIADO EM OVOS", "Jogue 50 partidas", "partidas", 50, 100),
    ("partida_200", "LENDA DO FLIPERAMA", "Jogue 200 partidas", "partidas", 200, 250),
    ("variedade_10", "EXPLORADOR", "Jogue 10 jogos diferentes", "jogos_diferentes", 10, 60),
    ("variedade_27", "JÁ JOGUEI DE TUDO", "Jogue todos os 31 jogos solo", "jogos_solo", 31, 200),
    ("ouro_1", "PRIMEIRO OURO", "Ganhe uma medalha de ouro", "ouros", 1, 50),
    ("ouro_5", "OVO DOURADO", "Ganhe 5 medalhas de ouro", "ouros", 5, 150),
    ("ouro_15", "CAMPEÃO DA RUA", "Ganhe 15 medalhas de ouro", "ouros", 15, 300),
    ("recorde_10", "QUEBRA-RECORDES", "Bata 10 recordes", "recordes", 10, 60),
    ("multi_5", "BOM DE DUPLA", "Vença o J2 cinco vezes", "vitorias_multi", 5, 50),
    ("banho_1", "CHEIRINHO BOM", "Dê o primeiro banho", "banhos", 1, 20),
    ("banho_20", "OVO BRILHANTE", "Dê 20 banhos", "banhos", 20, 80),
    ("comer_25", "COMILÃO", "Coma 25 vezes", "comidas", 25, 50),
    ("carinho_50", "MUITO AMOR", "Faça 50 carinhos", "carinhos", 50, 40),
    ("compra_1", "PRIMEIRA COMPRA", "Compre algo na loja", "compras", 1, 20),
    ("gasto_1000", "GASTADOR", "Gaste 1.000 OVOEDAS", "moedas_gastas", 1000, 100),
    ("streak_3", "VOLTEI!", "Abra o baú 3 dias seguidos", "streak", 3, 40),
    ("streak_7", "UMA SEMANA!", "Abra o baú 7 dias seguidos", "streak", 7, 100),
    ("streak_30", "OVO FIEL", "Abra o baú 30 dias seguidos", "streak", 30, 400),
    ("desafio_5", "AMIGO DO ROBERT", "Cumpra 5 desafios do dia", "desafios", 5, 80),
    ("nivel_5", "CRESCENDO", "Chegue ao nível 5", "nivel", 5, 50),
    ("nivel_10", "OVO FORMADO", "Chegue ao nível 10", "nivel", 10, 100),
    ("nivel_20", "OVO VETERANO", "Chegue ao nível 20", "nivel", 20, 200),
    ("nivel_30", "OVO LENDÁRIO", "Chegue ao nível 30", "nivel", 30, 500),
    ("foto_1", "SORRIA!", "Tire uma foto com F12", "fotos", 1, 20),
    ("feliz_3", "OVO RADIANTE", "3 dias seguidos de OVO FELIZ", "dias_feliz", 3, 80),
    ("missoes_10", "MISSÃO CUMPRIDA", "Complete 10 missões diárias", "missoes", 10, 80),
    ("caixas_5", "CAÇADOR DE SURPRESAS", "Abra 5 caixas surpresa", "caixas", 5, 60),
    ("amigo_1", "TEM AMIGO NA ÁREA", "Adicione o código de um amigo", "amigos", 1, 30),
    ("pet_amigo", "MELHORES AMIGOS", "Encha o coração de um pet", "pet_max", 100, 100),
    ("pocoes_10", "ALQUIMISTA", "Beba 10 poções", "pocoes", 10, 40),
    ("pascoa", "CAÇADOR DE OVOS", "Ache todos os ovinhos da Páscoa num dia", "pascoa", 1, 50),
]

POR_ID = {c[0]: c for c in CONQUISTAS}

# Conquistas que também dão um cosmético exclusivo (core/visual_extra.EXCLUSIVOS)
ITEM_CONQUISTA = {"feliz_3": "olh_estrela"}


def _stats(save):
    return save["stats"]


def _verificar(app, chave):
    """Libera as conquistas da estatística `chave` que bateram a meta."""
    save = app.save
    feitas = save["conquistas"]
    valor = _stats(save).get(chave, 0)
    for cid, nome, desc, stat, meta, premio in CONQUISTAS:
        if stat != chave or cid in feitas or valor < meta:
            continue
        feitas.append(cid)
        save.ganhar(premio)
        _toast(app, "CONQUISTA!", nome, f"+{premio}", "conquista")
        item = ITEM_CONQUISTA.get(cid)
        if item and item not in save["inventario"]:
            save["inventario"].append(item)
            _toast(app, "ITEM EXCLUSIVO!", "VEJA NA LOJA (JÁ É SEU)", "", "levelup")
    save.salvar()


def contar(app, chave, n=1):
    save = getattr(app, "save", None)
    if save is None or save.arquivo is None:
        return
    st = _stats(save)
    st[chave] = st.get(chave, 0) + n
    _verificar(app, chave)


def definir(app, chave, valor):
    """Estatística que guarda o MAIOR valor já visto."""
    save = getattr(app, "save", None)
    if save is None or save.arquivo is None:
        return
    st = _stats(save)
    if valor > st.get(chave, 0):
        st[chave] = valor
        _verificar(app, chave)


def ganhar_xp(app, qtd):
    """Soma XP ao ovo ativo. Devolve a lista de níveis alcançados."""
    save = getattr(app, "save", None)
    if save is None or save.arquivo is None or qtd <= 0:
        return []
    if xp_dobrado(save):
        qtd *= 2
    subiu = []
    nivel = max(1, save["nivel"])
    nivel_antes = nivel
    xp = save["xp"] + int(qtd)
    while nivel < NIVEL_MAX and xp >= xp_para(nivel):
        xp -= xp_para(nivel)
        nivel += 1
        subiu.append(nivel)
    if nivel >= NIVEL_MAX:
        xp = 0
    save["nivel"] = nivel
    save["xp"] = xp
    for n in subiu:
        premio = premio_nivel(n)
        save.ganhar(premio)
        _toast(app, f"NÍVEL {n}!", f"{save['nome'] or 'SEU OVO'} CRESCEU!", f"+{premio}", "levelup")
    save.salvar()
    if subiu:
        _avisar_jogos_novos(app, nivel_antes, nivel)
        definir(app, "nivel", nivel)
        # A cena atual pode comemorar (a casa solta confete)
        comemorar = getattr(app.cena, "comemorar_nivel", None)
        if comemorar:
            comemorar(nivel)
    return subiu


def _toast(app, titulo, texto, premio="", som="conquista"):
    toasts = getattr(app, "toasts", None)
    if toasts is not None:
        toasts.adicionar(titulo, texto, premio, som)


# ------------------------------------------------------------
# COMPATIBILIDADE: saves antigos ganham as conquistas que já têm
# ------------------------------------------------------------

def sincronizar(app):
    """Conta o que o save já tinha antes das conquistas existirem."""
    save = app.save
    if save is None or save.arquivo is None:
        return
    iniciar_liberacao(save, novo=False)
    from jogos import JOGOS, trofeus
    st = _stats(save)
    solo = {j.ID for j in JOGOS if not getattr(j, "MULTI", False)}
    jogados = set(save["jogados"])
    ouros = sum(1 for j in JOGOS if trofeus.nivel(save, j)[0] == "ouro")
    diario = save["diario"]
    for chave, valor in (("jogos_diferentes", len(jogados)),
                         ("jogos_solo", len(jogados & solo)),
                         ("ouros", ouros),
                         ("streak", diario.get("bau_seq", 0) if isinstance(diario.get("bau_seq"), int) else 0),
                         ("nivel", save["nivel"]),
                         ("compras", 1 if len(save["inventario"]) > 1 else 0)):
        if valor > st.get(chave, 0):
            st[chave] = valor
    # Libera em silêncio o que já estava cumprido (sem chuva de toasts)
    feitas = save["conquistas"]
    for cid, _, _, stat, meta, _ in CONQUISTAS:
        if cid not in feitas and st.get(stat, 0) >= meta:
            feitas.append(cid)
    save.salvar()


# ============================================================
# REFORÇOS DAS POÇÕES (core/itens.py: "buff")
# ============================================================
# save["diario"]["buffs"] = {"sorte": partidas restantes, "xp_ate": timestamp}

MULT_SORTE = 1.5


def _buffs(save):
    b = save["diario"].get("buffs")
    if not isinstance(b, dict):
        b = {}
        save["diario"]["buffs"] = b
    return b


def ativar_buff(app, tipo, valor):
    save = app.save
    b = _buffs(save)
    if tipo == "sorte":
        b["sorte"] = int(b.get("sorte", 0)) + int(valor)
    elif tipo == "xp":
        b["xp_ate"] = max(float(b.get("xp_ate", 0)), time.time()) + float(valor)
    save.salvar()


def consumir_sorte(app):
    """No fim de cada partida: gasta 1 carga da POÇÃO DA SORTE (se houver)."""
    save = getattr(app, "save", None)
    if save is None:
        return False
    b = _buffs(save)
    if int(b.get("sorte", 0)) > 0:
        b["sorte"] = int(b["sorte"]) - 1
        return True
    return False


def xp_dobrado(save):
    return float(_buffs(save).get("xp_ate", 0)) > time.time()


def buffs_ativos(save):
    """Textos curtos para o HUD: ["SORTE 3", "XP x2 12:30"]."""
    b = _buffs(save)
    saida = []
    if int(b.get("sorte", 0)) > 0:
        saida.append("SORTE " + str(b["sorte"]))
    resta = float(b.get("xp_ate", 0)) - time.time()
    if resta > 0:
        saida.append("XP x2 %d:%02d" % (int(resta) // 60, int(resta) % 60))
    return saida


# ============================================================
# COLEÇÕES (peixes da pescaria, receitas do cozinheiro, borboletas)
# ============================================================
# save["stats"]["colecoes"] = {"peixes": [ids], "receitas": [ids]}.
# As borboletas continuam em save["album"] (sistema antigo).

PREMIO_COLECAO = 150
COLECOES = [("borboletas", "BORBOLETAS"), ("peixes", "PEIXES DA PESCARIA"),
            ("receitas", "RECEITAS DO COZINHEIRO")]


def _colecoes(save):
    c = save["stats"].get("colecoes")
    if not isinstance(c, dict):
        c = {}
        save["stats"]["colecoes"] = c
    return c


def catalogo_colecao(nome):
    """[(id, nome bonito)] de todos os itens da coleção."""
    try:
        if nome == "peixes":
            from jogos import pescaria
            return [(k, d.get("nome", k.upper())) for k, d in pescaria.ESPECIES.items()]
        if nome == "receitas":
            from jogos import ovo_cozinheiro
            return [(r["id"], r["nome"]) for r in getattr(ovo_cozinheiro, "RECEITAS", [])]
        if nome == "borboletas":
            from cenas.casa_extras import quintal
            saida = []
            for esp in quintal.ESPECIES:
                if isinstance(esp, dict):
                    saida.append((esp.get("id", esp.get("nome")), esp.get("nome", "")))
                elif isinstance(esp, (tuple, list)):
                    saida.append((esp[0], esp[1] if len(esp) > 1 else str(esp[0]).upper()))
                else:
                    saida.append((esp, str(esp).upper()))
            return saida
    except Exception:
        pass
    return []


def itens_colecao(save, nome):
    if nome == "borboletas":
        return list(save["album"])
    return list(_colecoes(save).get(nome, []))


def colecionar(app, nome, item_id):
    """Registra um item de coleção. Completar a coleção paga um prêmio."""
    save = getattr(app, "save", None)
    if save is None or save.arquivo is None:
        return False
    lista = _colecoes(save).setdefault(nome, [])
    if item_id in lista:
        return False
    lista.append(item_id)
    total = len(catalogo_colecao(nome))
    rotulo = {"peixes": "PEIXE NOVO!", "receitas": "RECEITA NOVA!"}.get(nome, "ITEM NOVO!")
    _toast(app, rotulo, "COLEÇÃO %d/%s" % (len(lista), total or "?"), "", "revelar")
    marca = "colecao_" + nome
    if total and len(lista) >= total and marca not in save["conquistas"]:
        save["conquistas"].append(marca)
        save.ganhar(PREMIO_COLECAO)
        _toast(app, "COLEÇÃO COMPLETA!", nome.upper(), "+%d" % PREMIO_COLECAO, "levelup")
    save.salvar()
    return True


# ============================================================
# MINI JOGOS LIBERADOS AOS POUCOS
# ============================================================
# Um ovo novo começa com 8 jogos; os outros solo liberam um por
# nível (a partir do 2), ou antes com um INGRESSO (moedas). Os de
# 2 jogadores estão sempre liberados. Saves antigos (de antes deste
# sistema) ficam com tudo liberado: ninguém perde jogo.

INICIAIS = ["cobrinha", "chuva", "pulo", "memoria", "toupeiras", "ovo_corredor", "minado", "voador"]


def _ordem_liberacao():
    from jogos import JOGOS
    return [j.ID for j in JOGOS if not getattr(j, "MULTI", False) and j.ID not in INICIAIS]


def nivel_para(jogo_id):
    """Nível que libera o jogo (1 = desde o começo)."""
    if jogo_id in INICIAIS:
        return 1
    ordem = _ordem_liberacao()
    if jogo_id in ordem:
        return 2 + ordem.index(jogo_id)
    return 1


def preco_ingresso(jogo_id):
    return 60 + 15 * nivel_para(jogo_id)


def liberado(save, jogo):
    if getattr(jogo, "MULTI", False):
        return True
    lib = save["stats"].get("liberados")
    if not isinstance(lib, list):
        return True                     # save sem o sistema
    return jogo.ID in lib or nivel_para(jogo.ID) <= max(1, save["nivel"])


def liberar(app, jogo_id):
    lib = app.save["stats"].get("liberados")
    if isinstance(lib, list) and jogo_id not in lib:
        lib.append(jogo_id)
        app.save.salvar()


def iniciar_liberacao(save, novo):
    """Ao criar (novo=True) ou abrir um ovo pela 1ª vez nesta versão."""
    if "liberados" in save["stats"]:
        return
    if novo:
        save["stats"]["liberados"] = list(INICIAIS)
    else:
        from jogos import JOGOS
        save["stats"]["liberados"] = [j.ID for j in JOGOS]


def _avisar_jogos_novos(app, nivel_antes, nivel_depois):
    save = app.save
    if not isinstance(save["stats"].get("liberados"), list):
        return
    from jogos import JOGOS
    for j in JOGOS:
        n = nivel_para(j.ID)
        if nivel_antes < n <= nivel_depois and j.ID not in save["stats"]["liberados"]:
            _toast(app, "JOGO NOVO LIBERADO!", j.TITULO, "", "revelar")


# ============================================================
# OVO FELIZ POR VÁRIOS DIAS
# ============================================================
# 10 minutos de OVO FELIZ num dia contam o dia. Dias seguidos
# aumentam o bônus de moedas (x1,10 -> até x1,20).

MINUTOS_DIA_FELIZ = 10


def registrar_feliz(app, dt):
    import datetime
    save = app.save
    d = save["diario"]
    hoje = datetime.date.today().isoformat()
    if d.get("feliz_dia") != hoje:
        d["feliz_dia"] = hoje
        d["feliz_seg"] = 0.0
        d["feliz_contou"] = False
    d["feliz_seg"] = float(d.get("feliz_seg", 0)) + dt
    if not d.get("feliz_contou") and d["feliz_seg"] >= MINUTOS_DIA_FELIZ * 60:
        d["feliz_contou"] = True
        ontem = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
        seq = int(d.get("feliz_seq", 0)) + 1 if d.get("feliz_ultimo") == ontem else 1
        d["feliz_seq"] = seq
        d["feliz_ultimo"] = hoje
        _toast(app, "DIA FELIZ!", "%d DIA(S) SEGUIDOS DE OVO FELIZ" % seq, "", "acerto")
        definir(app, "dias_feliz", seq)
        save.salvar()


def mult_feliz(save):
    import datetime
    d = save["diario"]
    seq = int(d.get("feliz_seq", 0))
    hoje = datetime.date.today()
    validos = (hoje.isoformat(), (hoje - datetime.timedelta(days=1)).isoformat())
    if d.get("feliz_ultimo") not in validos:
        seq = 0
    return 1.10 + 0.02 * min(5, seq)


# ============================================================
# AFEIÇÃO DOS PETS (carinho e brincadeiras enchem o coração)
# ============================================================

def afeicao(app, pet_id, n=1):
    save = getattr(app, "save", None)
    if save is None or save.arquivo is None or not pet_id:
        return 0
    af = save["stats"].get("afeicao")
    if not isinstance(af, dict):
        af = {}
        save["stats"]["afeicao"] = af
    antes = af.get(pet_id, 0)
    af[pet_id] = min(100, antes + n)
    if antes < 100 <= af[pet_id]:
        _toast(app, "MELHORES AMIGOS!", "O CORAÇÃO DO PET ENCHEU!", "", "levelup")
    definir(app, "pet_max", af[pet_id])
    return af[pet_id]
