import datetime
import os
import time
import unicodedata

import settings
from core.save import CHAVES_GLOBAIS, CONFIG_PADRAO, Config, PADRAO, Save, gravar_json

# ============================================================
# PERFIS (os ovos da vizinhança)
# ============================================================
# Cada casa da RUA DOS OVOS é um "slot" (0 a 4) com o seu próprio
# arquivo saves/ovo_N.json (N = slot + 1). Aqui ficam: caminhos,
# leitura, criação, lixeira e a migração do save antigo (1 ovo).
#
# Os caminhos são lidos na hora de cada chamada (e não guardados
# como argumento padrão) para os testes poderem trocar a pasta.

PASTA_SAVES = settings.PASTA_SAVES
ARQUIVO_ANTIGO = settings.ARQUIVO_SAVE
MAX_SLOTS = 5
MAX_LIXEIRA = 10


def arquivo_global():
    return os.path.join(PASTA_SAVES, "global.json")


def arquivo_ovo(slot):
    return os.path.join(PASTA_SAVES, f"ovo_{slot + 1}.json")


def pasta_lixeira():
    return os.path.join(PASTA_SAVES, "lixeira")


# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------

def carregar_config():
    arq = arquivo_global()
    dados, status = Save.ler(arq)
    if status == "corrompido":
        try:
            os.replace(arq, arq + ".corrompido")
        except OSError:
            pass
    return Config(dados, arquivo=arq)


# ------------------------------------------------------------
# OVOS
# ------------------------------------------------------------

def estado_slot(slot):
    """"vazio", "ok" ou "corrompido"."""
    if not 0 <= slot < MAX_SLOTS:
        return "vazio"
    _, status = Save.ler(arquivo_ovo(slot))
    if status == "ausente":
        return "vazio"
    return status


def slots_ocupados():
    return [s for s in range(MAX_SLOTS) if estado_slot(s) == "ok"]


def carregar_ovo(slot, config):
    """Save do ovo (que grava no próprio arquivo) ou None se não der."""
    dados, status = Save.ler(arquivo_ovo(slot))
    if status != "ok":
        return None
    save = Save(dados, arquivo=arquivo_ovo(slot), config=config)
    _completar_casa(save, slot)
    return save


def ler_ovo(slot):
    """Cópia só de leitura (nunca grava). None se vazio/corrompido."""
    dados, status = Save.ler(arquivo_ovo(slot))
    if status != "ok":
        return None
    save = Save(dados, arquivo=None)
    _completar_casa(save, slot)
    return save


def _completar_casa(save, slot):
    from core import fachada
    save["casa"] = fachada.normalizar(save["casa"], slot, save["ovo"])


def normalizar_nome(nome):
    n = unicodedata.normalize("NFKD", nome)
    n = "".join(c for c in n if not unicodedata.combining(c))
    return " ".join(n.casefold().split())


def nomes_em_uso(excluir=None):
    nomes = set()
    for s in range(MAX_SLOTS):
        if s == excluir:
            continue
        save = ler_ovo(s)
        if save is not None and save["nome"].strip():
            nomes.add(normalizar_nome(save["nome"]))
    return nomes


def novo_rascunho(config):
    """Ovo em criação: ainda não tem arquivo (nada é gravado)."""
    return Save(arquivo=None, config=config)


def criar_ovo(slot, save, presente=True):
    """Grava o rascunho como o ovo da casa `slot`."""
    from core import fachada
    save.arquivo = arquivo_ovo(slot)
    save["criado_em"] = time.time()
    save["casa"] = fachada.casa_padrao(slot, save["ovo"])
    if "vaso_flor" not in save["inventario"]:
        save["inventario"].append("vaso_flor")
    if presente:
        # Presente de mudança: 100 OVOEDAS + 3 maçãs + vaso de flor
        save.dados["moedas"] += 100
        save.dados["moedas_total"] += 100
        save["comida"]["maca"] = save["comida"].get("maca", 0) + 3
    save["ultimo_tempo"] = time.time()
    save.salvar()


def apagar_ovo(slot, config):
    """
    Move o arquivo do ovo para a lixeira (nunca apaga de verdade).
    Devolve True se deu certo.
    """
    arq = arquivo_ovo(slot)
    if not os.path.exists(arq):
        return False
    lixeira = pasta_lixeira()
    carimbo = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = os.path.join(lixeira, f"ovo_{slot + 1}_{carimbo}.json")
    n = 1
    while os.path.exists(destino):
        destino = os.path.join(lixeira, f"ovo_{slot + 1}_{carimbo}_{n}.json")
        n += 1
    try:
        os.makedirs(lixeira, exist_ok=True)
        os.replace(arq, destino)
    except OSError:
        return False

    # Guarda só os mais recentes
    try:
        antigos = sorted((os.path.join(lixeira, a) for a in os.listdir(lixeira)
                          if a.endswith(".json")), key=os.path.getmtime)
        for a in antigos[:-MAX_LIXEIRA]:
            os.remove(a)
    except OSError:
        pass

    if config["ultimo_ovo"] == slot:
        config["ultimo_ovo"] = -1
    if config["j2_slot"] == slot:
        config["j2_slot"] = -1
    config.salvar()
    return True


def modificar_ovo(slot, funcao):
    """Lê o ovo `slot`, aplica funcao(save) e grava (ovo NÃO carregado)."""
    dados, status = Save.ler(arquivo_ovo(slot))
    if status != "ok":
        return False
    save = Save(dados, arquivo=arquivo_ovo(slot))
    funcao(save)
    save.salvar()
    return True


def primeira_execucao(config=None):
    """Nenhum ovo e nunca criou um (quem apagou todos vê a tela inicial)."""
    if slots_ocupados():
        return False
    return not (config is not None and config["tem_ovo"])


def apagar_tudo():
    """
    RECOMEÇAR DO ZERO: apaga a pasta saves/ inteira (ovos, lixeira,
    preferências) e o save antigo de 1 ovo (e os backups dele), para
    a migração não trazer nada de volta. Devolve True se deu certo.
    """
    import glob
    import shutil
    ok = True
    if os.path.isdir(PASTA_SAVES):
        shutil.rmtree(PASTA_SAVES, ignore_errors=True)
        ok = not os.path.exists(PASTA_SAVES)
    pasta = os.path.dirname(ARQUIVO_ANTIGO)
    for arq in [ARQUIVO_ANTIGO] + glob.glob(os.path.join(pasta, "save_antigo*.json")):
        try:
            if os.path.exists(arq):
                os.remove(arq)
        except OSError:
            ok = False
    return ok


# ------------------------------------------------------------
# MIGRAÇÃO DO SAVE ANTIGO (1 ovo -> casa 1)
# ------------------------------------------------------------

def migrar_save_antigo():
    """
    Se existe o save.json antigo e ainda não existe saves/global.json,
    ele vira o ovo da casa 1. O original é renomeado (backup), nunca
    apagado. Devolve True se migrou.
    """
    if not os.path.exists(ARQUIVO_ANTIGO) or os.path.exists(arquivo_global()):
        return False
    cru, status = Save.ler(ARQUIVO_ANTIGO)
    if status != "ok":
        return False

    from core import fachada
    try:
        config = Config({k: v for k, v in cru.items() if k in CONFIG_PADRAO},
                        arquivo=arquivo_global())
        if isinstance(cru.get("j2"), list) and len(cru["j2"]) == 4:
            config["j2"] = cru["j2"]

        nome = cru.get("nome", "")
        if isinstance(nome, str) and nome.strip():
            ovo = Save({k: v for k, v in cru.items() if k in PADRAO and k not in CHAVES_GLOBAIS},
                       arquivo=arquivo_ovo(0))
            casa = fachada.casa_padrao(0, ovo["ovo"])
            ovo["casa"] = casa
            ovo["criado_em"] = time.time()
            if "vaso_flor" not in ovo["inventario"]:
                ovo["inventario"].append("vaso_flor")
            gravar_json(ovo.arquivo, ovo.dados)
            config["ultimo_ovo"] = 0
            config["tem_ovo"] = True
            config["migrado"] = True
            config["banner_migracao"] = True

        gravar_json(config.arquivo, config.dados)
    except OSError:
        return False

    # Backup do save antigo
    destino = os.path.join(os.path.dirname(ARQUIVO_ANTIGO), "save_antigo.json")
    if os.path.exists(destino):
        carimbo = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        destino = os.path.join(os.path.dirname(ARQUIVO_ANTIGO), f"save_antigo_{carimbo}.json")
    try:
        os.replace(ARQUIVO_ANTIGO, destino)
    except OSError:
        pass
    return True
