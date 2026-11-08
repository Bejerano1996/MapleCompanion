# Umbrale Companion 2.1.0-companion

This project combines the supplied Umbrale 2.0.0 source with the Maple Companion interface and utilities. Original source notices and documentation are retained.

## Run and build

On Windows 10/11 with Python 3.12, install `requirements.txt` and run `python app.py` from this directory. Windows OCR language support must be installed. Data indexes and map images are cached on first use.

To build the executable, install PyInstaller and run `python build_release.py`. The builder stages a new application without deleting existing user state or cache.

## Integrated interface

Light lavender surfaces, readable dark navigation icons, white-on-dark tooltips, a character profile, global search, and Tools accompany the original Quests, Mobs, Items, Training and PQ screens. Tools include session tracking, itinerary planning, timers, bookmarks, map comparison and shortcuts.

## GPS beside the game minimap

Start a route using the original quest/map GPS actions. The native GPS strip docks immediately to the right of the detected game minimap and matches its height. It shows the next destination, portal guidance, step number and intermediate maps. Expand the route to inspect all steps. The dock action restores the minimap anchor after manual undocking. Automatic advancement depends on successfully reading the new map from the screen; manually select the current location if OCR cannot read it.

The original Umbrale route engine, portal rendering and minimap detection are retained. No gameplay movement or game input is automated.

## Market sources

Automatic prices come from maplestory.watch's public endpoints, with timestamps and offline/cache status. MesoWatch is a separate website: its button opens https://beta.meso.watch/ and supports copying an item name and saving an explicitly manual price note. This release does not claim an automatic MesoWatch API integration.

## Validation

- 140 original logic checks passed.
- 66 OCR checks passed against the supplied static screenshots using Windows OCR.
- 26 Companion model checks passed.
- 26 interface integration checks passed.
- 16 native GPS docking checks passed: minimap detection, right-edge placement, height matching across three screenshots, route steps, undocking and re-docking, and callback errors.

These checks do not establish live traversal through the game. The executable was built successfully; it has not been independently exercised through a complete live game route. Original test_flicker.py was retained but not run.

## Source and GitHub

This is a full Python source project, not an extension depending on the old compiled Companion. Local caches, personal state and build dependencies are excluded from the source archive. The requested liavbateman/umbrale repository returned 404 through the connected GitHub account; no code was pushed or published elsewhere.
