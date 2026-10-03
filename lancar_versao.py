"""Gera o Oval.exe e publica uma nova release no GitHub.

Uso:
    python lancar_versao.py 1.7 "O que mudou nesta versão"

Precisa de: PyInstaller (pip install pyinstaller) e GitHub CLI logado (gh auth login).
"""
import os
import subprocess
import sys

PASTA = os.path.dirname(os.path.abspath(__file__))
EXE = os.path.join(PASTA, "dist", "Oval.exe")

COMO_JOGAR = """## Como jogar

1. Baixe o **Oval.exe** logo abaixo, em *Assets*
2. Dê dois cliques para abrir. Não precisa instalar nada, nem o Python.

> O Windows pode mostrar o aviso "O Windows protegeu o computador", porque o jogo não tem assinatura digital. Clique em **Mais informações → Executar assim mesmo**.

O progresso é salvo em `%APPDATA%\\Oval\\save.json`.

## Novidades

"""


def rodar(*cmd):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(">", " ".join(cmd))
    subprocess.run(cmd, cwd=PASTA, check=True)


def conferir_exe():
    """Para tudo se algum .py de cenas/core/jogos não entrou no .exe."""
    from PyInstaller.archive.readers import CArchiveReader
    arq = CArchiveReader(EXE)
    mods = set()
    for nome in arq.toc:
        if nome.startswith("PYZ"):
            mods |= set(arq.open_embedded_archive(nome).toc)
    faltando = []
    for pasta in ("cenas", "core", "jogos"):
        for raiz, _, arquivos in os.walk(os.path.join(PASTA, pasta)):
            for a in arquivos:
                if a.endswith(".py"):
                    rel = os.path.relpath(os.path.join(raiz, a), PASTA)[:-3]
                    mod = rel.replace(os.sep, ".").removesuffix(".__init__")
                    if mod not in mods:
                        faltando.append(mod)
    if faltando:
        print("Módulos que ficaram fora do .exe:", ", ".join(sorted(faltando)))
        sys.exit(1)
    print("Todos os módulos do jogo estão no .exe")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    versao, novidades = sys.argv[1], sys.argv[2]
    tag = "v" + versao

    # Não lança versão com mudanças que não foram commitadas
    pendente = subprocess.run(["git", "status", "--porcelain"], cwd=PASTA,
                              capture_output=True, text=True).stdout.strip()
    if pendente:
        print("Há mudanças não commitadas. Faça o commit antes de lançar:\n" + pendente)
        sys.exit(1)

    dados = []
    # Os .mid de musicas/midi só servem para editar, não vão no .exe
    for origem, destino in (("Fonts", "Fonts"), ("Img", "Img"),
                            ("musicas/trilhas", "musicas/trilhas"),
                            ("musicas/sfx", "musicas/sfx"),
                            ("musicas/Ovein.mp3", "musicas")):
        dados += ["--add-data", f"{os.path.join(PASTA, origem)};{destino}"]
    rodar(sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
          "--onefile", "--windowed", "--name", "Oval",
          "--icon", os.path.join(PASTA, "Img", "oval.ico"),
          *dados,
          # casa/loja/caixa importam módulos pelo nome (__import__), então o
          # PyInstaller não os acha sozinho: inclui todos os submódulos
          "--collect-submodules", "core", "--collect-submodules", "cenas",
          "--collect-submodules", "jogos",
          "--distpath", "dist", "--workpath", "build", "--specpath", "build",
          "main.py")

    conferir_exe()
    rodar("git", "push", "origin", "main")
    rodar("gh", "release", "create", tag, EXE,
          "--title", f"Oval {versao}",
          "--notes", COMO_JOGAR + novidades,
          "--target", "main", "--latest")
    print(f"\nPronto! https://github.com/montezzs/Oval/releases/tag/{tag}")


if __name__ == "__main__":
    main()
