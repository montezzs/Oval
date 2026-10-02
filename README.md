# Oval

Oval its a cozy game developed by me (Samuel Montez) where the main goal is to take cary of an egg and play funny little games to gain coins and buy more accesories to your egg and your house

Inspired in Pou (mobile game)

## ⬇️ [Download Oval.exe](https://github.com/montezzs/Oval/releases/latest/download/Oval.exe)

**PT:** Clique no link acima, abra o `Oval.exe` e jogue — não precisa instalar nada.
**EN:** Click the link above, open `Oval.exe` and play — no install needed.
**ES:** Haz clic en el enlace, abre `Oval.exe` y juega — no necesitas instalar nada.

> Windows SmartScreen: *Mais informações / More info / Más información → Executar assim mesmo / Run anyway / Ejecutar de todas formas*.

Um ovinho de estimação na RUA DOS OVOS: até 5 ovos, cada um na sua casa, com
necessidades, jardim, pets, loja, reforma da fachada e dezenas de mini jogos
(solo e para 2 jogadores no mesmo teclado).

## Jogar

- **Sem instalar nada:** baixe o [`Oval.exe`](https://github.com/montezzs/Oval/releases/latest/download/Oval.exe) e dê dois cliques.
- **Pelo Python:** `pip install pygame` e depois `python main.py`.

Os saves ficam na pasta `saves/` (ao lado do `main.py`; no `.exe`, em `%APPDATA%\Oval\saves`):
`global.json` com as preferências e `ovo_1.json` a `ovo_5.json`, um por casa. Ovos apagados
vão para `saves/lixeira/` (dá para restaurar copiando o arquivo de volta).

Para começar tudo de novo: tela inicial -> OPÇÕES -> RECOMEÇAR DO ZERO (apaga todos os saves;
os ovos vão embora de caminhão de mudança). F12 tira uma foto da tela (pasta `fotos/`).

## Músicas e efeitos sonoros

As músicas (`musicas/trilhas/*.mp3`) e os efeitos (`musicas/sfx/*.mp3`) são compostos em
código em `ferramentas/partituras.py` e gravados com FluidSynth + SoundFont General MIDI:

```
python ferramentas/compor_musicas.py            # tudo
python ferramentas/compor_musicas.py casa jogos # só algumas
```

Os `.mid` ficam em `musicas/midi/` para abrir no FL Studio.

## Gerar o Oval.exe e publicar

```
python lancar_versao.py 2.0 "O que mudou nesta versão"
```

(gera o `.exe` com PyInstaller e cria a Release no GitHub; o ícone sai de
`tools/gerar_icone.py`).
