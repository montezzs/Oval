import random

# ============================================================
# CAIXA SURPRESA
# ============================================================
# Sorteia um cosmético pela raridade. Se sair um que o ovo já tem,
# vira OVOEDAS (40% do preço dele). Usada pela LOJA (ovo-cápsula
# comprável) e pelo prêmio das 3 missões do dia.

PRECO_CAIXA = 150
PESOS = {"COMUM": 50, "INCOMUM": 30, "RARO": 13, "EPICO": 5, "ÉPICO": 5, "LENDARIO": 2, "LENDÁRIO": 2}


def _catalogo():
    itens = {}
    for nome in ("cosmeticos", "cosmeticos_novos"):
        try:
            mod = __import__(f"core.{nome}", fromlist=[nome])
        except ImportError:
            continue
        itens.update(getattr(mod, "CATALOGO", {}))
    return itens


def sortear(save, rnd=None):
    """
    Devolve (item_id | None, nome, raridade, moedas_de_consolo).
    Já grava no save (inventário ou moedas).
    """
    rnd = rnd or random
    catalogo = _catalogo()
    # Exclusivos (loja=False) também podem sair, mas raramente
    raridade = rnd.choices(list(PESOS), weights=list(PESOS.values()))[0]
    raridade = raridade.replace("É", "E").replace("Á", "A")
    candidatos = [(cid, d) for cid, d in catalogo.items()
                  if str(d.get("raridade", "COMUM")).replace("É", "E").replace("Á", "A") == raridade]
    if not candidatos:
        candidatos = list(catalogo.items())
    if not candidatos:
        save.ganhar(60)
        return None, "60 OVOEDAS", "COMUM", 60
    cid, d = rnd.choice(candidatos)
    nome = d.get("nome", cid.upper())
    if cid in save["inventario"]:
        consolo = max(20, int(d.get("preco", 100) * 0.4))
        save.ganhar(consolo)
        return cid, nome, raridade, consolo
    save["inventario"].append(cid)
    save.salvar()
    return cid, nome, raridade, 0
