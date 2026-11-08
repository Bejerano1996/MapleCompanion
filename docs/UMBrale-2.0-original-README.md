# UMBRΛLE

<img src="icon.png" width="96" align="right" alt="UMBRΛLE sigil">

A compact, dark-fantasy overlay that floats above **MapleStory Classic** and guides your quests:
where to go, what to kill or collect, how far you are, and the way there, portal by portal.

It only **reads the screen** (screen capture + Windows OCR, like a screenshot tool). It never
reads the game's memory and never sends the game any input.

**Version 2.0.0** · Windows 10 / 11

## What it does

- **Floating overlay.** Collapsed, it's a single title row (sigil, your next objective with a
  progress bar, sync, expand, pin, menu). Expanded, a compact panel with Quests, Mobs, Items,
  Training and PQ tabs. Drag it anywhere, pin it in place; it stays on top of the game.
- **Counts without the game's Quest Helper.** On every quest kill or pickup the game shows a gold
  line near the top of the screen ("Jr. Necki 12 / 20"); UMBRΛLE reads those and keeps every
  quest's counts up to date. The in-game Quest Helper and Quest window are read too when visible.
- **Focus on one quest.** ◉ on a quest card: the panel shows only that quest, and collapsed, all
  its objectives (each with a bar) sit under the title row.
- **GPS.** A slim strip docked to the game's minimap: a big arrow, where to go on this map, which
  map that leads to, step n of m, and the map with the portal (or NPC, or spawns) marked. It
  follows the minimap's position and size on every map change, at any resolution.
- **Knows where you are** by reading the map name inside the game's minimap window. Wrong? Click
  the location line and pick the right map; that reading is remembered.
- **Suggestions, monsters, items, training maps, party quests**: what to pick up next (best EXP
  per minute), where a monster lives, who drops or sells an item, the best maps for your level,
  and party quest stages with answers. Data from [meowdb.com](https://meowdb.com).

## Run it

```bat
pip install -r requirements.txt
start.bat
```

Run MapleStory in a window or borderless window. `Ctrl+Shift+S` syncs from the game; AUTO keeps
following it every 2 seconds. Settings (opacity, text size, auto sync, auto-collapse, lock
position, reset position) are in the ⋯ menu.

## Build

```bat
build.bat
```

Builds `..\UMBRALE\UMBRALE.exe` with PyInstaller (needs `pip install pyinstaller`). Your list
(`state.json`) and the download cache next to the .exe are kept between builds.

## Tests

```bat
python tests\test_logic.py        :: routes, suggestions, counts from the gold lines, ...
python tests\run_regression.py    :: screen reading on real screenshots (minimap, map names, quests)
python tests\test_flicker.py      :: no flicker on syncs (opens windows; leave the mouse still)
```

## Layout

| File | What's in it |
| --- | --- |
| `app.py` | The overlay: windows, tabs, GPS, syncing with the game |
| `widgets.py` | Palette and building blocks (buttons, switches, slider, popovers, scroll area) |
| `game_sync.py` | Finding the game, screenshots, the minimap window, map names, the gold lines |
| `screen_ocr.py`, `sync.py` | Windows OCR and matching what's read to quests, counts and maps |
| `meowdb.py` | Game data from meowdb.com (cached in `cache/`) |
| `gps_image.py`, `minimap.py` | Drawing the GPS strip and the annotated minimaps |
| `quest_rank.py`, `party_quests.py` | Quest suggestions; party quest guides |
| `make_icon.py`, `assets/` | The sigil and app icon, made from the UMBRΛLE logo |
| `docs/DEVLOG.md` | Development log: what changed, why, and how it was tested |
