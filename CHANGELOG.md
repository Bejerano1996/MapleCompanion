## 2.6.1

- Monster cards use an inset thumbnail and two text lines so names and stats fit narrow windows.
- Shorter search hint; thumbnail padding prevents rounded corners from masking sprites.
- Layout checked at widths 340, 360 and 480 with all three font scales.

## 2.6.0

- Monster and quest NPC thumbnails load asynchronously with a disk cache.
- MesoWatch opens in a WebView2 window with the requested search already filled; exact matches open automatically.
- Job Test monster variants are excluded; regular Evil Eye keeps its eight known maps.
- PQ guides remain accessible while game indexes are unavailable.
- Consistent tools icon and coin price icon.

# Changelog

## 2.4.0-companion — per-monster maps and quest rewards

- Inline monster locations below objectives: known spawn counts and portal distance from the current map, sorted by Spawn or Nearest. Click a map to open native GPS with that monster highlighted.
- Three maps by default; all-map lists update when the current map changes. Completed objectives keep their maps folded.
- All cached spawn locations are considered, rather than only the previous eight-map guide shortlist.
- Every tracked quest has a concise reward summary and a full Rewards dialog. Fixed items, selectable items and random pools are separated, with reported chances where available.

## 2.3.0-companion — quest item sources

- Unfinished quest items show a compact shop or breakable source with a GPS action.
- Show merchant price and citizenship requirements; prefer unrestricted nearby sources.
- Read breakable links and spawn maps from the item's public database page, including plants and boxes. Mark community drop reports as such and avoid claiming guaranteed drops.
- Other sources opens the remaining shops and maps; completed objectives hide acquisition hints.
- Include shop and gathering maps in the quest itinerary. Upgrade cached quest guides to schema 4.
- Includes the 2.2.1 first-run HTTPS packaging fix; no saved-state level changes are performed by deployment.

## 2.2.1-companion — first-run HTTPS fix

- Include the SSL runtime's required certificate-policy resource in Windows builds. Fresh installations can load game data without relying on a pre-existing cache.
- Preserve certificate and hostname verification.
- Add `--check-data report.json` for validating HTTPS initialization, game indexes and window detection in the packaged application.
- Verified loading 401 quests, 453 maps and 206 monsters from a fresh packaged installation; the desktop copy resumed reading live maps and quests after the missing resource was restored.

## 2.2.0-companion — compact presentation

- 360-pixel default panel, a single profile row, and search on demand.
- Folded suggestions; EXP details and party settings open separately.
- Saved 100%, 115% and 130% text sizes apply to Companion controls, native lists, dialogs, tooltips and GPS; header controls keep their footprint.
- Short messages with detailed status on hover; a compact Retry state when game indexes cannot load.
- Manual quest addition is on the main screen; clearing the list is under settings and retains confirmation.
- The native Umbrale quest engine, Trainer, PQ guides, minimap docking and route steps are retained.

## 2.1.0-companion — source integration

- Full Umbrale source combined with the Companion light interface, tools and public market client.
- MesoWatch website lookup and explicitly manual price notes.
- Full source and a standalone Windows executable, built without depending on an older compiled Companion engine.

## 2.0.0 — UMBRΛLE

The first release under the new name: a redesigned in-game overlay.

- New identity: the UMBRΛLE sigil and icon, an obsidian / arcane-violet palette, thin rims.
- Collapsible overlay: a compact title row (next objective + progress bar) that expands into a
  floating panel; settings menu, pin, opacity, text size, auto-collapse when you go back to the game.
- Counts without the in-game Quest Helper, from the game's own gold progress lines.
- Focus on one quest: all its objectives under the collapsed title row.
- GPS strip docked to the game's minimap, matching its height and following it on every map change.
- Location read from inside the minimap window, at any resolution or UI scale; misreads can be
  corrected and are remembered.
- Slim quest cards with progress bars; the panel reopens after "Reset from Quest window".
- Opening UMBRΛLE again brings the running one forward instead of starting a second copy.
