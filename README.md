# Umbrale Companion 2.2

A compact MapleStory Classic overlay: your current objective, quests and GPS, with extra tools one click away.

- **Next:** show your next quest objective.
- **Tabs:** quests, monsters, items, training and party quests. Hover an icon for its name.
- **Search:** click the magnifier or press Ctrl+F. Escape closes the search row.
- **Text size:** gear → 100%, 115% or 130%. Your choice is saved.
- **GPS:** start a route from a quest or map. Guidance docks beside the game's minimap; expand it to see the intermediate maps.

Suggestions start folded. EXP is a single line; **Details** opens the original EXP and party controls. **⊞** opens the optional session, route, reminders and saved-map tools. **¤** opens prices.

Automatic prices use maplestory.watch. MesoWatch opens its website and supports explicitly manual price notes.

## Run

Windows 10/11, Python 3.12, and Windows OCR language support:

```bat
pip install -r requirements.txt
python app.py
```

Keep MapleStory windowed. Ctrl+Shift+S syncs from the screen; AUTO follows the game. The app does not send gameplay input.

## Build

```bat
pip install pyinstaller
python build_release.py
```

The application is written to `dist/Umbrale Companion`. The build stages new program files without deleting existing state or cache.

## Source and checks

See [INTEGRATION.md](INTEGRATION.md) for source provenance, market limitations and validation. The original Umbrale README is preserved under `docs/`.

```bat
python tests/test_compact_ui.py
python tests/test_integration.py
python tests/test_gps_docking.py
python tests/test_tool_sizes.py
python tests/test_logic.py
python tests/run_regression.py
python -m unittest discover -s tests -p "test_*model.py"
```

Logic and GPS tests use cached game indexes. OCR regression uses the supplied screenshots. The extended lifecycle check is `python tests/soak_compact_ui.py --minutes 120`; it disables game capture and global hotkeys and uses temporary fixture state.
