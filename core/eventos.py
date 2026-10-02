import datetime
import os

from core.idioma import t

# ============================================================
# EVENTOS DO CALENDÁRIO
# ============================================================
# Datas reais mudam o jogo por alguns dias:
#   PÁSCOA      (semana até a segunda depois da Páscoa): caça aos
#               ovinhos no SOL + presente exclusivo
#   HALLOWEEN   (24/10 a 02/11): presente exclusivo
#   NATAL       (18/12 a 06/01): presente exclusivo
#   FIM DE SEMANA (sábado e domingo): OVOEDAS x1,2 nos mini jogos
# Para testar: OVAL_HOJE=2026-04-05 python main.py

MULT_FIM_DE_SEMANA = 1.2


def hoje():
    forcado = os.environ.get("OVAL_HOJE")
    if forcado:
        try:
            return datetime.date.fromisoformat(forcado)
        except ValueError:
            pass
    return datetime.date.today()


def domingo_de_pascoa(ano):
    """Algoritmo de Meeus/Jones/Butcher."""
    a = ano % 19
    b, c = divmod(ano, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = (h + l - 7 * m + 114) % 31 + 1
    return datetime.date(ano, mes, dia)


EVENTOS = {
    "pascoa": dict(nome="SEMANA DA PÁSCOA", cor=(255, 170, 220),
                   presente="orelhas_coelho", texto="ACHE OS OVINHOS ESCONDIDOS NO SOL!"),
    "halloween": dict(nome="HALLOWEEN", cor=(255, 140, 40),
                      presente=["chapeu_bruxa", "cor_abobora"], texto="GOSTOSURAS OU TRAVESSURAS!"),
    "natal": dict(nome="NATAL NA RUA DOS OVOS", cor=(230, 60, 60),
                  presente=["gorro_natal", "rou_sueter_natal"], texto="FELIZ NATAL!"),
}


def sazonal(data=None):
    """Id do evento sazonal ativo (ou None)."""
    d = data or hoje()
    p = domingo_de_pascoa(d.year)
    if p - datetime.timedelta(days=6) <= d <= p + datetime.timedelta(days=1):
        return "pascoa"
    if (d.month == 10 and d.day >= 24) or (d.month == 11 and d.day <= 2):
        return "halloween"
    if (d.month == 12 and d.day >= 18) or (d.month == 1 and d.day <= 6):
        return "natal"
    return None


def fim_de_semana(data=None):
    return (data or hoje()).weekday() >= 5


def mult_moedas():
    return MULT_FIM_DE_SEMANA if fim_de_semana() else 1.0


def faixa():
    """Texto curto para faixas/banners (ou "")."""
    ev = sazonal()
    partes = []
    if ev:
        partes.append(t(EVENTOS[ev]["nome"]))
    if fim_de_semana():
        partes.append(t("FIM DE SEMANA: OVOEDAS x1,2"))
    return "  •  ".join(partes)


def cor_faixa():
    ev = sazonal()
    return EVENTOS[ev]["cor"] if ev else (120, 220, 140)


def entregar_presente(app):
    """1 presente exclusivo por evento por ano (chamado ao entrar na casa)."""
    ev = sazonal()
    save = app.save
    if not ev or save is None or save.arquivo is None:
        return None
    chave = f"presente_{ev}_{hoje().year}"
    if save["stats"].get(chave):
        return None
    save["stats"][chave] = True
    itens = EVENTOS[ev]["presente"]
    itens = itens if isinstance(itens, list) else [itens]
    try:
        from core import cosmeticos
        novos = [i for i in itens if i in cosmeticos.CATALOGO and i not in save["inventario"]]
    except Exception:
        novos = []
    item = novos[0] if novos else None
    if novos:
        save["inventario"].extend(novos)
        nome = " + ".join(t(cosmeticos.CATALOGO[i].get("nome", i.upper())) for i in novos)
        premio = ""
    else:
        save.ganhar(100)
        nome = t("100 OVOEDAS")
        premio = "+100"
    save.salvar()
    toasts = getattr(app, "toasts", None)
    if toasts is not None:
        toasts.adicionar(t("PRESENTE: {nome}", nome=t(EVENTOS[ev]["nome"])), nome, premio, "levelup")
    return item
