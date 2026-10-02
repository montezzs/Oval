# ============================================================
# TRADUÇÕES
# ============================================================
# Cada módulo desta pasta define EN = {...} e ES = {...} com
# chave = texto ORIGINAL em português. Os imports são explícitos
# (e não por listdir) para o PyInstaller incluir tudo no .exe.
# Módulo novo? Adicione-o na lista abaixo.

from core.traducoes import comum, cenas, core_textos, jogos_a, jogos_b, jogos_c, jogos_d

MODULOS = (comum, cenas, core_textos, jogos_a, jogos_b, jogos_c, jogos_d)


def juntar():
    """{"en": {...}, "es": {...}} com todos os módulos juntos."""
    tabelas = {"en": {}, "es": {}}
    for m in MODULOS:
        tabelas["en"].update(getattr(m, "EN", {}))
        tabelas["es"].update(getattr(m, "ES", {}))
    return tabelas
