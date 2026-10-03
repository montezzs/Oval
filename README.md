# Oval

Oval is a cozy game developed by me (Samuel Montez) where the main goal is to take care of an egg and play fun little games to earn coins and buy accessories for your egg and your house.

Inspired by Pou (mobile game).

**Current version / Versão atual: 2.1**

## ⬇️ [Download Oval.exe](https://github.com/montezzs/Oval/releases/latest/download/Oval.exe)

**EN:** Click the link above, open `Oval.exe` and play, no install needed.
**PT:** Clique no link acima, abra o `Oval.exe` e jogue, não precisa instalar nada.
**ES:** Haz clic en el enlace, abre `Oval.exe` y juega, no necesitas instalar nada.

> Windows SmartScreen: *More info / Mais informações / Más información → Run anyway / Executar assim mesmo / Ejecutar de todas formas*.

**Languages / Idiomas:** English, Português, Español. chosen the first time you open the game and changeable in OPTIONS.

---

## What's new / Novidades

### 2.1
- **EN:** Fixed the `.exe`: house furniture (fridge, trophy shelf and the rest) was missing from 2.0.
- **PT:** Corrigido o `.exe`: os móveis da casa (geladeira, estante de troféus etc.) não vinham na 2.0.

### 2.0
- **EN:** English and Spanish translations, title screen, Egg Street, friends, achievements, renovation, XP and medals, 14 new mini games, a new soundtrack (57 original tracks) and a refreshed look.
- **PT:** Tradução para inglês e espanhol, tela de título, Rua dos Ovos, amigos, conquistas, reforma, XP e medalhas, 14 minijogos novos, trilha sonora nova (57 músicas originais) e visual renovado.

---

## English

A pet egg on EGG STREET: up to 5 eggs, each in its own house, with needs, a garden, pets,
a shop, facade renovation and dozens of mini games (solo and 2 players on the same keyboard).

### Play

- **No install:** download [`Oval.exe`](https://github.com/montezzs/Oval/releases/latest/download/Oval.exe) and double-click it.
- **With Python:** `pip install pygame`, then `python main.py`.

Saves live in the `saves/` folder (next to `main.py`; in the `.exe`, in `%APPDATA%\Oval\saves`):
`global.json` holds the preferences and `ovo_1.json` to `ovo_5.json` one per house. Deleted eggs
go to `saves/lixeira/` (restore one by copying the file back).

To start over: title screen -> OPTIONS -> START OVER (deletes all saves; the eggs leave
in a moving truck). F12 takes a screenshot (`fotos/` folder).

### Music and sound effects

The music (`musicas/trilhas/*.mp3`) and effects (`musicas/sfx/*.mp3`) are composed in code in
`ferramentas/partituras.py` and rendered with FluidSynth + a General MIDI SoundFont:

```
python ferramentas/compor_musicas.py            # everything
python ferramentas/compor_musicas.py casa jogos # only some tracks
```

The `.mid` files are in `musicas/midi/` so you can open them in FL Studio.

### Translations

Texts go through `t()` from `core/idioma.py`; the English and Spanish translations are in
`core/traducoes/` (key = the original Portuguese text).

### Build Oval.exe and publish

```
python lancar_versao.py 2.0 "What changed in this version"
```

(builds the `.exe` with PyInstaller and creates the GitHub Release; the icon comes from
`tools/gerar_icone.py`).

---

## Português

Um ovinho de estimação na RUA DOS OVOS: até 5 ovos, cada um na sua casa, com
necessidades, jardim, pets, loja, reforma da fachada e dezenas de mini jogos
(solo e para 2 jogadores no mesmo teclado).

### Jogar

- **Sem instalar nada:** baixe o [`Oval.exe`](https://github.com/montezzs/Oval/releases/latest/download/Oval.exe) e dê dois cliques.
- **Pelo Python:** `pip install pygame` e depois `python main.py`.

Os saves ficam na pasta `saves/` (ao lado do `main.py`; no `.exe`, em `%APPDATA%\Oval\saves`):
`global.json` com as preferências e `ovo_1.json` a `ovo_5.json`, um por casa. Ovos apagados
vão para `saves/lixeira/` (dá para restaurar copiando o arquivo de volta).

Para começar tudo de novo: tela inicial -> OPÇÕES -> RECOMEÇAR DO ZERO (apaga todos os saves;
os ovos vão embora de caminhão de mudança). F12 tira uma foto da tela (pasta `fotos/`).

### Músicas e efeitos sonoros

As músicas (`musicas/trilhas/*.mp3`) e os efeitos (`musicas/sfx/*.mp3`) são compostos em
código em `ferramentas/partituras.py` e gravados com FluidSynth + SoundFont General MIDI:

```
python ferramentas/compor_musicas.py            # tudo
python ferramentas/compor_musicas.py casa jogos # só algumas
```

Os `.mid` ficam em `musicas/midi/` para abrir no FL Studio.

### Traduções

Os textos passam por `t()` de `core/idioma.py`; as traduções em inglês e espanhol ficam em
`core/traducoes/` (a chave é o texto original em português).

### Gerar o Oval.exe e publicar

```
python lancar_versao.py 2.0 "O que mudou nesta versão"
```

(gera o `.exe` com PyInstaller e cria a Release no GitHub; o ícone sai de
`tools/gerar_icone.py`).
