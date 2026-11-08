# Umbrale Companion 2.4.0-companion

This project combines the supplied Umbrale 2.0.0 source with the Maple Companion interface and utilities. Original source notices and documentation are retained.

## Run and build

On Windows 10/11 with Python 3.12, install `requirements.txt` and run `python app.py` from this directory. Windows OCR language support must be installed. Data indexes and map images are cached on first use.

To build the executable, install PyInstaller and run `python build_release.py`. The builder stages a new application without deleting existing user state or cache.

## Integrated interface

Light lavender surfaces, readable dark navigation icons, white-on-dark tooltips, a character profile, global search, and Tools accompany the original Quests, Mobs, Items, Training and PQ screens. Tools include session tracking, itinerary planning, timers, bookmarks, map comparison and shortcuts.

The default panel is 360 pixels wide. Profile controls occupy one row; global search opens on request and Escape hides it. Suggestions begin folded. EXP appears as a single percentage, while the original EXP and party controls open in a separate Details window. The gear offers saved text sizes of 100%, 115% and 130%, applied to lists, Companion controls, dialogs, tooltips and GPS. The title-row controls keep their size to avoid overflow. Technical status details are available on hover; unavailable game indexes show a compact Retry state.

## GPS beside the game minimap

Start a route using the original quest/map GPS actions. The native GPS strip docks immediately to the right of the detected game minimap and matches its height. It shows the next destination, portal guidance, step number and intermediate maps. Expand the route to inspect all steps. The dock action restores the minimap anchor after manual undocking. Automatic advancement depends on successfully reading the new map from the screen; manually select the current location if OCR cannot read it.

The original Umbrale route engine, portal rendering and minimap detection are retained. No gameplay movement or game input is automated.

## Market sources

Automatic prices come from maplestory.watch's public endpoints, with timestamps and offline/cache status. MesoWatch is a separate website: its button opens https://beta.meso.watch/ and supports copying an item name and saving an explicitly manual price note. This release does not claim an automatic MesoWatch API integration.

## Quest acquisition sources

Version 2.3 adds shops and breakables to unfinished item objectives. A compact source row shows the action, merchant or object, map, optional price/access condition, and GPS. Other sources lists alternatives. The GPS routes to the merchant or gathering map; breakable coordinates and guaranteed drops are not claimed. The itinerary can include these maps without inventing monster drops. Cached guide schema 4 refreshes older monster-only guides.

Validated examples: Salad from 24 Hr Mobile Store in Ant Tunnel Park (220 mesos each), and Plant Sample from Ellinia Flower on five maps. Source pages: https://meowdb.com/msclassic/npcs/614 and https://meowdb.com/msclassic/breakables/0000003 . Breakable drop associations are community reports.

The HTTPS resource missing from the 2.2 Windows package is included. Packaged first-run data loading was checked with certificate and hostname verification enabled. Desktop deployment updates only program files and checks that the saved-state file is unchanged during copying.

## Monster maps and rewards

Version 2.4 places three map suggestions below monster objectives, including item-drop monsters. Each row shows known spawn points and portal distance. Spawn and Nearest selectors persist the chosen ordering; every map name opens native GPS with the correct monster. The full map window follows changes in the current map. Completed objectives keep their map lists folded. The model uses the entire cached map dataset, rather than just the older eight-map guide shortlist. Unknown spawn counts and routes remain explicitly unknown.

Quest cards have a concise reward summary and a Rewards dialog with all listed EXP, mesos, items, fame and town contribution. Fixed, selectable and random pools are separate; a reported chance is displayed only when present in the source data. Eight model tests and thirteen interface checks passed for map ordering, full coverage, live distance updates, correct GPS targets and reward classifications, alongside the existing regression checks. No new two-hour run is claimed for this version.

## Validation

- 140 original logic checks passed.
- 66 OCR checks passed against the supplied static screenshots using Windows OCR.
- 34 Companion and market model checks passed.
- 26 interface integration checks passed.
- 43 compact presentation and font-size checks passed, including distinct navigation icons, the native Umbrale menu, monitor bounds, empty journals, selected-size feedback, concise status messages and failed-load recovery.
- 19 Tools-window checks passed: all six screens at all three text sizes, with action buttons fully visible at the 440-pixel minimum width.
- 40 native GPS docking checks passed: minimap detection, right-edge placement, height matching across three screenshots at all three text sizes, route steps, undocking and re-docking, and callback errors.
- Packaged Windows OCR read the supplied static fixture successfully without desktop capture.
- A two-hour source UI lifecycle check completed 432 cycles in 7,200.1 seconds with no callback errors. Measured font objects stayed at 45; temporary windows returned to zero after each cycle. Final startup, status and icon refinements were covered by the focused final checks and packaged OCR validation.

For 2.3, seven acquisition-model tests and eleven acquisition-interface checks passed, including generic boxes, source scoping, nearest maps, citizenship requirements, correct merchant GPS targets, plant maps, completed-objective hiding, and drop-lookup failures. The original 140 logic checks, 26 integration checks and 34 pre-existing model tests also passed. The two-hour lifecycle run above belongs to the 2.2 interface work; no new two-hour run is claimed for 2.3.

These checks do not establish live traversal through the game. The executable was built successfully; it has not been independently exercised through a complete live game route. Original test_flicker.py was retained but not run.

## Source and GitHub

This is a full Python source project, not an extension depending on the old compiled Companion. Local caches, personal state and build dependencies are excluded from the source archive. The requested liavbateman/umbrale repository returned 404 through the connected GitHub account; no code was pushed or published elsewhere.
