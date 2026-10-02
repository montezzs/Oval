import base64
import json
import zlib

# ============================================================
# CÓDIGO DO OVO (amigos, sem internet)
# ============================================================
# O código leva nome, aparência, cosméticos, pet, nível e os 3
# melhores recordes do ovo. O amigo cola o código no jogo dele:
# o seu ovo aparece desfilando na tela inicial dele e cada recorde
# vira um desafio ("DUVIDO VOCÊ PASSAR 1200 NA PESCARIA"). Bater o
# recorde do amigo paga OVOEDAS uma vez por jogo.
#
# Formato: "OVAL-" + base32( zlib( json curto ) + crc ), em blocos.

PREFIXO = "OVAL"
PREMIO_DESAFIO_AMIGO = 20
MAX_AMIGOS = 8


def _melhores_recordes(save, qtd=3):
    from jogos import JOGOS, trofeus
    lista = []
    for j in JOGOS:
        if getattr(j, "MULTI", False):
            continue
        r = trofeus.regra(j)
        menor = bool(r and r.get("tipo") == "menor") or j.MENOR_MELHOR
        melhor = trofeus._melhor(save, j, menor)
        if melhor is None:
            continue
        nivel, _ = trofeus.nivel(save, j)
        peso = {"ouro": 3, "prata": 2, "bronze": 1}.get(nivel, 0)
        lista.append((peso, j.ID, melhor, menor))
    lista.sort(key=lambda x: -x[0])
    return {jid: [valor, 1 if menor else 0] for _, jid, valor, menor in lista[:qtd]}


def gerar(save):
    equipado = [v for v in save["equipado"].values() if v]
    dados = {
        "n": (save["nome"] or "OVO")[:12],
        "a": [save["ovo"], save["cabelo"], save["olho"], save["boca"]],
        "c": equipado[:6],
        "p": save["pet"],
        "l": save["nivel"],
        "r": _melhores_recordes(save),
    }
    cru = zlib.compress(json.dumps(dados, separators=(",", ":"), ensure_ascii=False).encode("utf-8"), 9)
    crc = zlib.crc32(cru) & 0xFFFF
    texto = base64.b32encode(cru + crc.to_bytes(2, "big")).decode("ascii").rstrip("=")
    blocos = [texto[i:i + 5] for i in range(0, len(texto), 5)]
    return PREFIXO + "-" + "-".join(blocos)


def ler(codigo):
    """dict do amigo, ou None se o código for inválido."""
    if not isinstance(codigo, str):
        return None
    limpo = "".join(ch for ch in codigo.upper() if ch.isalnum())
    if not limpo.startswith(PREFIXO):
        return None
    limpo = limpo[len(PREFIXO):]
    limpo += "=" * (-len(limpo) % 8)
    try:
        bruto = base64.b32decode(limpo)
        cru, crc = bruto[:-2], int.from_bytes(bruto[-2:], "big")
        if zlib.crc32(cru) & 0xFFFF != crc:
            return None
        dados = json.loads(zlib.decompress(cru).decode("utf-8"))
    except (ValueError, zlib.error, UnicodeDecodeError):
        return None
    if not isinstance(dados, dict) or not isinstance(dados.get("a"), list) or len(dados["a"]) != 4:
        return None
    return dados


def jogador_do_amigo(dados):
    """Jogador (só leitura) com a aparência e os cosméticos do amigo."""
    from core import assets
    from core.jogador import Jogador
    from core.save import Save
    limites = (len(assets.OVOS), len(assets.CABELOS), len(assets.OLHOS), len(assets.BOCAS))
    apar = [v if isinstance(v, int) and 0 <= v < n else 0 for v, n in zip(dados["a"], limites)]
    save = Save({"nome": str(dados.get("n", "AMIGO")), "ovo": apar[0], "cabelo": apar[1],
                 "olho": apar[2], "boca": apar[3]})
    try:
        from core import caixa
        catalogo = caixa._catalogo()
        for cid in dados.get("c", []):
            if cid in catalogo:
                save["equipado"][catalogo[cid].get("slot", cid)] = cid
    except Exception:
        pass
    return Jogador(save)


# ------------------------------------------------------------
# AMIGOS GUARDADOS (config["amigos"] = [código, ...])
# ------------------------------------------------------------

def amigos(config):
    saida = []
    for cod in config["amigos"]:
        d = ler(cod)
        if d is not None:
            saida.append((cod, d))
    return saida


def adicionar(config, codigo, meu_codigo=None):
    """'ok' | 'invalido' | 'repetido' | 'eu' | 'cheio'."""
    d = ler(codigo)
    if d is None:
        return "invalido"
    limpo = codigo.strip().upper()
    if meu_codigo and limpo == meu_codigo:
        return "eu"
    if any(ler(c) == d for c in config["amigos"]):
        return "repetido"
    if len(config["amigos"]) >= MAX_AMIGOS:
        return "cheio"
    config["amigos"].append(limpo)
    config.salvar()
    return "ok"


def verificar_desafios(app, jogo, valor):
    """Fim de partida: bateu o recorde de algum amigo neste jogo?"""
    save = app.save
    if save is None or save.arquivo is None:
        return []
    vencidos = save["stats"].setdefault("amigos_vencidos", [])
    ganhou = []
    for _, d in amigos(app.config):
        rec = d.get("r", {}).get(jogo.ID)
        if not isinstance(rec, list) or len(rec) != 2:
            continue
        alvo, menor = rec
        passou = valor < alvo if menor else valor > alvo
        chave = f"{d.get('n')}:{jogo.ID}:{alvo}"
        if passou and chave not in vencidos:
            vencidos.append(chave)
            save.ganhar(PREMIO_DESAFIO_AMIGO)
            ganhou.append(d.get("n", "AMIGO"))
            app.toasts.adicionar("DESAFIO DE AMIGO!", f"VOCÊ SUPEROU {d.get('n', 'AMIGO')}!",
                                 f"+{PREMIO_DESAFIO_AMIGO}", "conquista")
    if ganhou:
        save.salvar()
    return ganhou
