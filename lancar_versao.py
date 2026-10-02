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
          "--distpath", "dist", "--workpath", "build", "--specpath", "build",
          "main.py")

    rodar("git", "push", "origin", "main")
    rodar("gh", "release", "create", tag, EXE,
          "--title", f"Oval {versao}",
          "--notes", COMO_JOGAR + novidades,
          "--target", "main", "--latest")
    print(f"\nPronto! https://github.com/montezzs/Oval/releases/tag/{tag}")


if __name__ == "__main__":
    main()
