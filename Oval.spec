# -*- mode: python ; coding: utf-8 -*-
# Gera o Oval.exe (um arquivo só, sem janela de console):
#
#   python tools/gerar_icone.py
#   pyinstaller Oval.spec --noconfirm --distpath . --workpath build
#
# Os saves ficam na pasta "saves" ao lado do Oval.exe.

from PyInstaller.utils.hooks import collect_submodules

hidden = collect_submodules("core") + collect_submodules("cenas") + collect_submodules("jogos")

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[],
    datas=[("Img", "Img"), ("Fonts", "Fonts"), ("musicas", "musicas")],
    hiddenimports=hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=["numpy", "tkinter", "PIL", "matplotlib"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Oval",
    debug=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,
    icon="oval.ico",
)
