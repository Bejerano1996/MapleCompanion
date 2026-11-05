# UMBRΛLE development log

Every change, why it was made and how it was tested, newest at the bottom.

Each round picks the most valuable open item, changes the source in this folder, tests it
headlessly, and records the result below. Rounds never build or install the app and never
send input to the game. To ship the changes: close the app and run `build.bat`.

## Backlog (most valuable first)

1. ~~Sync accuracy: regression test set~~ (round 1). Grow it with every new screenshot.
2. ~~Quest Helper on busy backgrounds~~ (round 5: titles). Still open: JM's progress lines
   ("0 / 5 Leather") don't read on the first screenshot; needs more screenshots to tune.
3. ~~Start-up speed~~ (measured in round 3: 0.05 s, not needed).
4. ~~"What next?" suggestions~~ (round 4). Next: learn completed quests from the Q window's
   Completed tab during Reset, so suggestions skip what you already did.
5. ~~Route quality: ships and taxis~~ (round 3). Next: El Nath / Ludibrium links when they appear in the data.
6. ~~Error resilience~~ (round 2).
7. **Keyboard use:** shortcuts inside the window (1-4 for tabs, / to search, Esc to collapse).
10. **From the Classic patch notes / wiki (Oct 2026):** ~~Excavation Site routable~~ (loop round 2); Kerning City Party Quest (Lv 21+, wiki "First Time Together") as a
    Training/Quests hint; Citizenship quests (88, Henesys + Kerning) — shops already mark
    citizen-only stock; Forgotten Hollow opens Nov 18 (routes/maps once in the data).
11. ~~Shops in the map search~~ (loop round 2).
8. ~~Larger text~~ (round 7), ~~colour contrast~~ (round 8).
9. ~~Code health~~ (rounds 9-11: logic tests; widgets.py, game_sync.py, minimap.py split out).

## Rounds

### Round 1: regression tests for screen reading
- **Added** `tests/run_regression.py`: 3 real screenshots (Quest window + see-through helper; Perion
  with the game's Quest Helper; the minimap corner) and 6 minimap misreads, each with the expected
  quests, live quests, `have / need` counts (checked by eye against the image), map and Q-window state.
- **Bug found and fixed** (`sync.title_score`): numbered quests were confused, e.g. "I Need to Find
  My Daughter 2" also matched "... 1", because the comparison dropped the trailing number. When both
  names end in a number or roman numeral and they differ, it is no longer a match.
- **Result:** 27 passed, 0 failed. Run with `python tests/run_regression.py`.

### Round 2: never lose your list, survive network trouble
- **Safe saving:** `state.json`, the guides cache and every downloaded page are now written to a
  temporary file and swapped in (`meowdb.write_atomic`), so a crash mid-write can't corrupt them.
- **Autosave:** the list is saved every 30 s when it changed (it used to be saved only on ✕, so a
  crash or shutdown lost everything since launch).
- **Retries:** downloads retry twice (after 1 s and 3 s) on network errors and busy-server
  answers (429/5xx); a missing page (404) still fails at once.
- **Offline mode:** if a cached page has expired but meowdb.com is unreachable, the old copy is
  used and the status line says "Offline".
- **Tested:** crash-during-write keeps the old file; 2 failures then success = 3 attempts; 404 =
  1 attempt; expired cache served when offline; autosave wrote a change without closing.
  Regression: 27 passed, 0 failed.

### Round 3: routes with ships and taxis
- **Measured first:** start-up loads all data in 0.05 s, so backlog #3 (start-up speed) was dropped.
- **Routes now use transport** (`meowdb._transport_links`): Shanks' ship Southperry → Lith Harbor
  (one way), the Ellinia ⇄ Orbis ship (incl. the station walks missing from the map data), and the
  Regular Cabs between Victoria Island towns. The search is now cheapest-path (a portal costs 1,
  a cab 3, Shanks 4, the Orbis ship 6), so walking still wins when it's close.
- **Display:** a transport step reads "talk to Shanks and sail to Victoria Island → Lith Harbor",
  and the minimap stars the NPC to talk to instead of ringing a portal.
- **Tested:** Snail Hunting Ground I → A Split Road unchanged (3 portals); Maple Island → Henesys
  via Shanks; Henesys → Perion by cab; Henesys ⇄ Orbis both ways; screenshot of the route card.
  Regression: 27 passed, 0 failed.

### Round 4: "Quests you could take now"
- **New section** under the quest list (collapsible): up to 5 quests whose level and prerequisites
  you meet, that aren't on your list. Class-specific, event and daily quests and ones 20+ levels
  below you are left out; nearest quest giver first, then most EXP. Each name appears once (tiered
  quests like "Donating to Henesys" x5 share one) and at most two per NPC. ＋ adds, ✕ hides for good.
- **Also:** a collapsed card's "Go to" line shows only the distance, so it no longer gets cut off.
- **Tested:** at Henesys, Lv 15: Donating to Henesys, Mrs. Ming Ming's First Worry, The Reason
  Behind the Mushroom Studies, two Casey crafting quests (1 portal away); hide and add work;
  screenshot checked. Regression: 27 passed, 0 failed.
- **Limit:** "completed" only knows quests finished with ✓ Complete in this app, so a quest you did
  in the game before using the helper can be suggested; ✕ hides it.

### Fix (between rounds 4 and 5): other tabs didn't follow your location
- **Reported:** on the Training tab the map didn't update. The sync did read the new map, but only
  the Quests tab was redrawn, so Training/Monsters/Items kept distances, "Nearest" order and routes
  from the old map. Now any tab is redrawn when you change maps.
- **Tested:** Training sorted by Nearest at Henesys, then a sync reporting Perion: the list re-sorted
  from Perion. Regression: 27 passed, 0 failed. This build was installed at the user's request.

### Round 5: reading the see-through Quest Helper
- **Installed first** (user request): the build with rounds 1-4 + the Training fix.
- **Darker OCR pass** (`screen_ocr.passes`): besides the 110 threshold, a pass at 80 pulls dark text
  off bright scenery. On the first screenshot it reads all 3 Quest Helper titles; "JM From tha
  Streetz" was never read before and is now LIVE. App and tests now share one list of passes.
- **Ambiguous lines are skipped** (`sync.match_quests`): when a line matches two quests equally
  ("Daughter ?" with the number misread), it no longer guesses; the darker pass had exposed this.
- **Short words kept** (`sync.SHORT_WORDS`): "an" etc. are no longer dropped, so "Mr. Thunder in
  Need of an..." isn't confused with "... in Need of Help" (it only worked before by luck).
- **Tested:** regression 27/27, now expecting JM as LIVE. Speed: quick scan 0.23-0.25 s, full scan
  1.15 s on the 2560x1440 game window.

### Round 6: a new real screenshot, and Training ranked by monster count
- **Regression grew:** `tests/live_2.png`, captured from the running game (Damp Tree-Forest, the
  Quest Helper over a dark forest). All 5 counts and the map read correctly (checked by eye).
  Regression: 36 passed, 0 failed.
- **Training, at the user's request:** a new **Most mobs** sort (now the default) ranks maps by how
  many monsters spawn there; the EXP and Nearest sorts break ties by monster count too. Each map
  shows "N mobs" next to its EXP/hour. The list is now picked from every map in your level range,
  not only the top 15 by EXP, so mob-heavy maps can't be cut before sorting.
- **Layout:** the numbers column is packed first, so long area names no longer cut it ("79 mob").
- **Tested:** Perion, Lv 20: Most mobs → Ant Tunnel III (99), The Swamp of Despair II (79), Deep
  Ant Tunnel I (68); Nearest → Deep Valley II (2 portals); screenshots checked.

### Round 7: text size
- **"Aa" button** in the title bar cycles the list text through 100%, 115% and 130%; the choice is
  saved. The title bar keeps its size so its buttons always fit.
- **Layout fixes found while testing at 130%:** the title is now packed after the buttons, so a
  narrow window shortens the title instead of hiding buttons (Aa was disappearing at 340 px); in an
  open card the "covers all · 1 portal" details move to their own line; the small "kill · Lv 3"
  note is hidden at bigger sizes instead of being cut to "ill · Lv".
- **Tested:** screenshots at 100%, 115% and 130% in a 340 px window; the size survives a restart.
  Regression: 36 passed, 0 failed.

### Round 8: colour contrast
- **Measured** every text/background pair (WCAG ratio; small text needs 4.5:1). The lists all pass
  (white 12.7:1, muted 5.5:1 on cards). The failures were all on the blue bars: inactive tabs and
  "Lv" 3.3:1, AUTO off 2.4:1, AUTO on 3.8:1.
- **Fixed** with two bar-specific colours: `bar_muted` #cfdbea (4.6:1 on the title bar, 6.3:1 on
  the tab bar) and `bar_green` #a8ffbf for AUTO on (5.5:1).
- **Tested:** screenshot of both bars with AUTO off and on; regression 36 passed, 0 failed.

### Round 9: logic tests
- **Added** `tests/test_logic.py` (24 checks, no screen reading): walking route, Shanks' one-way ship,
  cab ride, Henesys ⇄ Orbis, distances; portal side incl. maps without size data; best map covers all
  objectives and is the nearest such map, and nothing is offered once all are done; suggestions
  (count, no duplicates, level, not already listed, hide works); all three Training sorts list 15
  maps and "Most mobs" puts the busiest map first; number tails and the "an" rule.
- **Result:** 24 passed, 0 failed (two failures on the first run were mistakes in the test itself:
  unreachable maps have no distance, and the Training row layout changed in round 6).
  Regression: 36 passed, 0 failed. Run both before each build:
  `python tests/test_logic.py` and `python tests/run_regression.py`.
- **Next for code health:** split app.py (~2,000 lines) into ui / routes / sync modules, now that
  tests guard the behaviour.

### Round 10: code health, part 1
- **Split** the colours and small styled widgets (label, button, link, Tooltip, ScrollArea, text size)
  out of app.py into `widgets.py` (137 lines); app.py went from 1,805 to 1,670 lines.
- **Caught during the split:** an automatic rename also changed the saved setting's name
  ("text_scale"), which would have reset everyone's text size; restored before testing.
- **Tested:** pyflakes clean on all modules; logic 24/24, regression 36/36; screenshots of every tab
  look the same as before.
- **Next:** move routing/minimap drawing (`render_minimap`, `portal_side`) and the screen-sync
  helpers (`capture_and_read`, `find_game_window`, `HotkeyThread`) into their own modules.

### Installed (18:03): everything through round 10
- At the user's request: rounds 5-10 (darker OCR pass and ambiguity fixes, Training by monster
  count, text size, contrast, logic tests, widgets.py split). Self-test passed in the build and
  after install; state.json (18:02) was kept.

### Round 11: code health, part 2
- **Split** screen reading into `game_sync.py` (finding the game window, screenshots with our own
  window hidden, OCR + matching, the Ctrl+Shift+S hotkey; 105 lines) and minimap drawing into
  `minimap.py` (59 lines). app.py is now 1,522 lines (from 1,805 two rounds ago) and imports them
  under the same names, so nothing else changed.
- **Tested:** pyflakes clean on all 7 modules (unused imports left by the move removed); logic 24/24,
  regression 36/36; a full and a quick sync through the new module on `live_2.png` give the same
  3 quests and map; screenshots of every tab unchanged.

### Round 12: what lives on a training map; one distance everywhere
- **Training:** opening a map now lists its monsters, busiest first: "Zombie Mushroom ×61 Lv 24 ·
  45 EXP". Clicking one marks where it spawns on the minimap; by default all of them are marked.
- **Bug found in the screenshot:** a card said "6 portals away" while its route said "4": the card
  showed the route's cost (a cab counts 3) instead of its length. `distances()` now returns the
  number of steps in the best route, so every label agrees with the route shown.
- **Tested:** Perion → Ant Tunnel III = 4 and 4; a new check that the distance equals the route's
  length for a sample of maps; logic 25/25, regression 36/36; screenshot checked.

### Round 13: turned-in quests leave the list by themselves
- **New** (`App._check_gone`): when a LIVE quest stops showing in the game's Quest Helper for 5
  syncs in a row (~10 s) while the helper is on screen, the app acts on it. If all its objectives
  were done it was turned in: it moves to completed (its follow-ups then appear under
  suggestions) and the status says "✓ Turned in: …". Otherwise (removed from the helper,
  forfeited) it only stops being LIVE and stays on the list. No pop-up, so play isn't interrupted.
- **Safety:** nothing is judged while the helper isn't visible (closed, covered, other screen),
  and a quest that reappears within 5 syncs is left alone.
- **Tested:** the four scenarios above by hand, then added to `tests/test_logic.py`;
  logic 28/28, regression 36/36.

### Fix + install (18:12): the app "didn't open"
- **Cause:** it opened as an invisible strip. Closing while shrunk to the title bar saved a 38 px
  height (`root.geometry()` was read right after un-shrinking, before Windows applied it), and with
  45% see-through on the edge of the left monitor the window was practically invisible.
- **Fix:** `safe_geometry()` on start-up (at least full height; moved to the primary screen if its
  title bar isn't on any screen), the app opens solid for 4 s before going see-through, and
  closing while shrunk saves the full size.
- **Tested** with a copy of the user's real state.json: opens 438x560 at the same spot, solid;
  shrink then close saves 438x560. Logic 28/28, regression 36/36. Installed (rounds 11-13 + fix),
  self-test passed, launched and confirmed visible. The improvement loop was stopped at the
  user's request.

### GPS from every tab + GPS opacity
- Inline routes removed: every 🧭 Go (Quests, Mobs, Items, Training) opens the GPS window; cards show a one-line "🧭 GPS to X [Show] ✕".
- Training no longer creates a route just by opening a map; Mobs rows got a 🧭 per map. Closing a card keeps the route the GPS is following.
- GPS header ◐: click cycles see-through, wheel fine-tunes (`gps_alpha`); solid while hovered, like the main window.
- GPS picture: ★/◉ now drawn with Segoe UI Symbol (were boxes); text size follows screen scaling and Aa.
- Tested: test_flicker 4/4, test_logic 35/35, run_regression 36/36; screenshots of Training/Mobs → GPS.

### GPS size
- GPS header ⤡ cycles 100% / 85% / 70% (`gps_scale`): the composed picture is shrunk as one image; short control wording below 80%.
- Tested: screenshots at all three sizes; test_flicker 4/4 at 100% and at 70%, test_logic 35/35, run_regression 36/36.

### GPS by map name
- 🔍 in the tab bar (and in the GPS header) opens a small search: type part of a map name, street or NPC; results show street and distance; click or Enter starts the GPS (route key "map").
- Result rows are fixed labels whose text changes, so typing doesn't rebuild the popup.
- Tested: find_maps("sleepy"/"shanks"/"el nath"/nonsense), Enter → GPS to Sleepywood, screenshots; test_flicker 4/4, test_logic 35/35, run_regression 36/36.

### Second monitor fix
- The map search popup and tooltips clamped x to ≥ 0, so on a monitor left of the main one (negative x) they jumped to the main screen. New `widgets.on_monitor_of` keeps them on the monitor of the button that opened them; the popup is placed while hidden, then shown.
- Tested with the user's layout (main at x=-340, GPS at x=-1643): popup and tooltip stay on the left monitor.
- test_flicker: hover effects are now switched off during the test (a real mouse passing over the test windows made a whole window more solid and was counted as a flicker); on failure with FLICKER_DUMP set it saves the changed frames. 36/37 runs passed after this; the one failure wasn't captured.

### Movable map search
- The map search window can be dragged by its top row ("⠿ drag"); the spot is saved (`search_pos`) and reused if it's still on a screen, else it opens under the 🔍 again.
- Tested: simulated drag → moved and saved; reopen uses it; an off-screen saved spot falls back. test_flicker 4/4, test_logic 35/35, run_regression 36/36.

## Rounds (loop on branch auto-improvements)

### Loop round 1: where to buy an item
- **Source:** meowdb.com's NPC shop list (`/msclassic/npc-shops`, 40 shops, 927 stock rows with
  Classic prices and citizen-only flags), our permitted data source. Cross-checked against the
  community wiki's Shops page (mapleclassic.wiki/wiki/Shops) and the patch notes summary on
  meowdb.com/msclassic/changelog.
- **New:** Items tab, opening an item shows **Sold by:** up to 4 shopkeepers, nearest first, each
  with price, distance, "citizens" when only Town Residents can buy it, and a 🧭 that opens the GPS
  straight to the NPC (★ on the minimap). Clicking the name previews the shop's map. Then the
  monster drops follow under **Dropped by:**. Shop-only items no longer say "no monster drops this".
- **Data:** `MeowDB._index_shops` builds `sold_by` (game item id → sellers, cheapest first) at
  start-up, cached for 7 days like the other lists; any failure leaves it empty, so the app still
  starts offline.
- **Fix found in the screenshot:** a drop row's 🧭 Go was squeezed to "G" by a long map name; the
  button is now packed first.
- **Tested:** screenshots (Red Potion: Arturo · Perion Dept. Store 50 m 1 away first); GPS to Lucy;
  test_logic +4 shop checks → 39/39, test_flicker 4/4, run_regression 36/36.

### Loop round 2: shops in the map search; patch-notes map check
- **Source:** meowdb.com NPC shop list (shop kind "Grocer", "Weapon Seller"... and stock with
  prices); patch notes (meowdb.com/msclassic/changelog, metaroad.gg Grand Launch notes) for the new
  Perion area, Excavation Site.
- **New:** the 🔍 search also finds shops, shown first in gold with 🛒: a kind ("potion", "weapon",
  "armor", "scroll", "pet") lists the nearest shops of that kind; an item name ("red potion") lists
  the nearest sellers with its price. Clicking opens the GPS to the shopkeeper. A town name
  ("perion") still finds maps, not "Return Scroll to Perion".
- **Checked:** Excavation Site I-III and <Camp> are in the map data and routable from Perion
  (Rocky Road III → Site I, 6 portals); added as a logic test so a data refresh that breaks it shows.
- **Tested:** screenshots of the search (empty / potion / red potion / weapon); test_logic +5 → 44/44,
  run_regression 36/36. test_flicker: 1 run failed on the still check (every GPS frame from 43 on
  differed, a lasting change, not a flash: something behind or over the test window), then 6/6 runs
  passed.


### Loop round 3 (user request): which quest next, by EXP for the effort
- **Asked:** "a system that prioritises quests I haven't done yet, by how easy they are to finish and
  how much EXP they give for the effort".
- **Source:** quest EXP, objectives, start/turn-in NPCs and levels from meowdb.com's quest list;
  EXP cross-checked against the community wiki's quest tables (mapleclassic.wiki/wiki/Quests:
  Sam's Suggestion 30, Todd's How-to-Hunt 10, Bringing a Mirror to Heena 2, all match).
- **New `quest_rank.py`:** an estimate in minutes per quest: walking (portals to the quest giver,
  to the farming map and back, to the turn-in NPC), kills (seconds per kill grow fast with the
  monster's level above yours), item drops (an assumed 40% drop rate; the dropper from the quest's
  guide, or the monster named in the item, e.g. Red Snail Shell → Red Snail), NPC quest items
  (403xxxx) as a hand-over, and jump quests ("[Forest of Patience] ...", "[Construction Site B1]
  ...") +10 min. Ranking score = EXP per minute × ease (halved at 30 min, halved again for monsters
  more than 3 levels above you). Unreachable quests (e.g. Maple Island from Victoria) are left out.
- **Quests tab:** "Quests you could take now" has **Best EXP/min** (default) and **Nearest**; each
  row shows "2,750 EXP · ≈2 min (quick) · 1,100 EXP/min", plus "jump quest" / "tough monsters" /
  "rough estimate". For top quests whose item source is unknown, the real droppers are looked up in
  the background (once per run, cached with the other guides) and the list re-ranks.
- **Limits:** "not done yet" = not completed in this app (as before); drop rates and kill speed are
  assumptions, so the minutes are for comparing quests, not a timer.
- **Tested:** printed rankings at Lv 8/15/30 in Henesys/Perion (quick safe quests first; "Donating"
  fell from #1 to mid-list once its tough droppers were known); screenshot of the tab; test_logic
  +8 → 51/51; test_flicker now waits for background lookups before measuring → 4/4;
  run_regression 36/36.

### Loop round 4: quests you've done, inferred from their follow-ups
- **Why:** the quest ranking (round 3) suggests "quests you haven't done", but the app only knew
  quests completed with ✓ in it. Quest chains say more: a quest on your list (or done) means every
  quest before it in its chain is done.
- **New:** `App.done_quests()` = completed in the app + all prerequisites (transitively) of your
  active and completed quests; `available()` uses it, so those no longer show up as suggestions
  and their follow-ups unlock. Cached per (list, completed).
- **Source:** quest prerequisites (`requires` / `requiresAll`) from meowdb.com's quest list; all
  279 quests with prerequisites point at known quests.
- **Tested:** test_logic +2 (Bringing a Mirror to Heena on the list → Borrowing Sera's Mirror
  done and not suggested) → 53/53; test_flicker 4/4; run_regression 36/36.
- **Backlog #4 still open:** reading the Q window's Completed tab would catch quests outside chains.

### Fix: the GPS stayed stuck on a quest that had left the list
- **Reported:** "the GPS got stuck on Talking to Stan; it won't let me move on and get a route".
- **Cause:** completing, removing or clearing a quest (`_forget`), or a Reset from the Quest window,
  took the quest off the list but left its route in `routes`. The GPS window kept following it,
  and since the quest card was gone, only the GPS window's own ✕ could stop it.
- **Fix:** `_drop_gone_quest_routes()` ends the route of any quest no longer on the list (closing the
  GPS if it showed that route), called from `_forget` and after a Reset. Map-search, Mobs, Items
  and Training routes are kept.
- **Seen while checking, not changed:** for Talking to Stan (25 Green + 25 Blue Mushrooms and their
  caps) the card's "Go to" ranks maps by mob count, so it suggests Green-only maps 7-14 portals
  away, while L Forest III / Henesys Dungeon Entrance (4 portals) have both mushrooms.
- **Tested:** test_logic +4 → 57/57; test_flicker 4/4; run_regression 36/36.

### Fix: the GPS said "You're there" at A Hill West of Henesys while the game showed Henesys
- **Reported** with a screenshot: game minimap "Victoria Road / Henesys", GPS "Route to A Hill West
  of Henesys · You're there!".
- **Cause 1: AUTO was off** in the saved settings, so the location only updated on ⟳ / Ctrl+Shift+S
  and the GPS kept the last map it had seen. **Fix:** while the GPS window is open, the 2-second
  timer still reads the minimap corner alone (`capture_and_read(map_only=True)`) and updates only
  where you are; quests, counts and "turned in" are untouched. AUTO off with no GPS reads nothing.
  The AUTO-off status now says "the GPS still follows you".
- **Cause 2: whole-screen reads could miss the map name:** on the screenshot, Windows OCR read
  "Victoria Road" but skipped "Henesys" (and, unmasked, the GPS window's own title "A Hill West of
  Henesys" then won). **Fix:** `game_sync.where_am_i` reads the minimap corner on its own first,
  then falls back to all lines; full scans use it (auto scans already read the corner as a region).
- **Tests:** run_regression + `henesys_gps_masked.png` (the user's screenshot, GPS blacked out as
  the sync does, in a 1366x768 frame) → Henesys, 37/37; test_logic +4 (timer reads only the map
  with AUTO off + GPS open, nothing without the GPS, quests untouched) → 61/61; test_flicker 6/6
  runs. Both test files now stub the real screen reading: with the always-on timer, a running game
  moved the test windows to the player's real map (seen as "Henesys Hunting Ground I").

### Fix 2: location still wrong with AUTO on (checked on the live game)
- **Live check** (game window captured like the app does, its windows blacked out): the player was
  in Henesys Hunting Ground I; the app had saved Kerning City, and a full read gave Perion.
- **Cause A: map names anywhere on screen counted.** With no map read from the minimap, `match_map`
  fell back to any line that exactly names a map; the open World Map's town labels ("Perion",
  "Kerning City"...) won. **Fix:** location comes only from the minimap title in the game window's
  top-left corner (`game_sync.where_am_i` / `read_title`); with no game window found, only a
  street + name pair counts (`match_map(anchored_only=True)`).
- **Cause B: the map line itself was skipped by OCR.** "Victoria Road" read, "Henesys Hunting
  Ground I" (white on a light-blue bar) not. **Fix:** `screen_ocr.title_passes`: the corner as-is,
  2x enlarged, and white-text-only (all channels ≥ 200); each tried until one names a map. Both new
  versions read the live title.
- **Tests:** run_regression + `live_hhg1_corner.png` (the live minimap corner only, no chat or
  names) → 38/38; test_logic +2 (World Map labels alone → no location; title still reads) → 63/63;
  test_flicker 11/12 runs passed (the one failure wasn't captured, then 8/8 in a row).

### Redesign cancelled; NPCs in the search
- **Concept A cancelled** at the user's request. It had been committed on auto-improvements on top
  of the installed fixes; it's now only on its own branch `concept-a` (639d5fe), and
  auto-improvements is back at ba72eef (what's installed). The build folder was rebuilt without it.
- **New: navigate to an NPC by name.** The 🔍 search lists NPCs first ("👤 Chief Stan · Henesys ·
  quest giver"), matching the start of a word in the name ("stan" → Chief Stan, not Assistant),
  names starting with the text first, then nearest; an NPC on several maps gets its two nearest.
  Clicking opens the GPS to that map with the NPC marked ★. Then shops, then maps, as before.
- **Source:** meowdb.com's NPC list (303 NPCs, 269 with maps, roles such as quest giver / shopkeeper).
- **Tested:** search results for stan / chief stan / shanks / arturo / mai; Enter on "chief stan" →
  GPS to Henesys with Chief Stan; test_logic +4 → 67/67; test_flicker 4/4 (twice); run_regression 38/38.

### PQ tab: party quests (Kerning City PQ)
- **Asked:** a PQ section with what to do in each one, the answers to the questions (like Kerning),
  and what you get in EXP and potential items.
- **New tab "PQ"** (`party_quests.py` data + `App.render_pq`): requirements (Lv 21+, exactly 4
  players, 30 min, channels 3-12), "Start: Lakelis · Kerning City · N portals" with 🧭 Go (GPS to
  Lakelis); each stage with what to do; Stage 1's quiz → coupon answers; Stages 2-4's every
  combination as chips you tap to cross off (only that chip repaints, nothing else); last stage
  and bonus; EXP of the PQ's own monsters (Ligator 68 × 22, Jr. Necki 80 × 6, Curse Eye 94 × 3,
  King Slime 2,400 → 4,658 per run, bonus extra); Proof of Companionship (once: 1,870 EXP, 687
  mesos, earring scroll); Companion's Magic Box contents and Squishy Shoes; notes; sources.
- **Sources:** meowdb.com KPQ guide (stages, quiz, combinations, the PQ monsters' stats, rewards);
  mapleclassic.wiki Kerning City Party Quest (extra quiz questions, box contents, channels 3-12).
  The sources give no fixed EXP per stage and no box chances, so neither is shown. KPQ is the only
  PQ in Classic so far; the data is a list, ready for more.
- **Tested:** screenshots of the tab; test_logic +5 (combination counts 4/10/20 with no duplicates,
  Lakelis on the start map, crossing off repaints only the chip, Go → Lakelis) → 72/72;
  test_flicker 5/5 runs; run_regression 38/38.

### Fix: a narrow window hid a lot of the content
- **Reported:** shrinking the window (e.g. Items while searching an item) hid much of the content
  unless the window was stretched wide.
- **Cause 1:** text was wrapped to the width at draw time (often fixed widths of 240-320 px) and a
  resize didn't redraw, so lines were cut at the right edge. **Fix:** `App.wrap(margin)` gives the
  current usable width; a resize redraws once, 250 ms after the width settles (≥ 8 px change).
- **Cause 2:** rows put a name and numbers side by side, and the name was clipped. **Fix:** long
  things get their own wrapping line: Items "Sold by" (who · where, then "50 mesos · 3 away"),
  "Dropped by" (map, then "4 portals · +14 more maps"), quest cards' "Go to" details, Mobs map
  names and hint, Training's grey line, the PQ start line; the suggestion sort buttons sit on
  their own line; the status line wraps; a narrow title reads "Quests (2)".
- **Tested:** screenshots of every tab at 340 px (the narrowest a drag allows) before/after;
  test_logic +2 (small changes don't redraw; a resize redraws once) → 74/74; test_flicker 3/3;
  run_regression 38/38.

### Redesign: UMBRΛLE in-game overlay (branch `wip`)
- **New name and look:** UMBRΛLE sigil (from the brand logo, made by `make_icon.py` into
  `assets/sigil.png` + a new `icon.ico`), obsidian / dark-glass / violet palette in `widgets.C`
  (old key names kept, so every screen keeps its meaning; "gold" is now the light violet highlight).
- **Two states:** collapsed = one title row (grip, sigil, wordmark, AUTO dot, a status line with
  location + quest count, ⟳, ▾, ⋯), about 51 px tall at 100% and as wide as its contents; expanded = the
  same row over the panel (tabs with a violet underline, location + Lv + 🔍 row, list, status line).
  The panel grows toward the middle of the screen near the right edge and moves up to fit near the
  bottom; collapsing returns the title row to where it was.
- **Settings menu (⋯):** opacity slider, text size, Auto sync / Click-through / Lock position
  switches, Sync now, Reset position, Hide overlay, Quit, with their shortcuts.
- **Global shortcuts** (Ctrl+Shift + S sync, E expand/collapse, G click-through, U hide/show,
  Home back to the home spot, top-right of the game window). The menu says when Windows refused one.
- **Click-through:** real (WS_EX_TRANSPARENT on the layered window): clicks reach the window
  underneath, checked with WindowFromPoint. Covers the overlay and the GPS, never menus or search.
  It can only be switched on while Ctrl+Shift+G is registered, so you can always get back.
- **Hide:** opacity 0 + click-through (no withdraw/deiconify, so showing again never takes the
  keyboard from the game); hidden windows are no longer blacked out of the sync screenshot.
- **Placement:** position, panel size and collapsed state saved as they change; dropped off every
  screen → back on the nearest; its monitor gone → home spot. Old `geometry` migrated once.
- **Keys in the panel:** 1-5 tabs, / map search, Esc collapses (or leaves a text box).
- **States:** hover, pressed, violet focus ring (Tab, Enter/Space), disabled. Hover fades take 150 ms,
  instant when Windows animations are off.
- **Limits:** Tk can only make a whole window see-through, so text fades along with the panel
  (no per-surface glass or blur). Clicking the overlay still takes keyboard focus from the game
  (needed for the text boxes). Corners are square.
- **Tested:** logic 74/74, regression 38/38; flicker: the redraw check passes, the on-screen frame
  check failed while the PC was in use (cursor hovers, windows on top) and should be re-run on an
  idle machine. A PyInstaller build into a temp folder passed `--selftest`; not installed.

### Layout pass 2: a smaller footprint while playing
- **GPS strip:** the GPS is a 300×50 strip (at 100% scaling) right of the game's minimap: a violet
  disc with the arrow, where to go on this map, which map it leads to and "step n/m". ▾ opens the
  annotated map, the maps after this one and every step; mouse wheel on it sets its opacity.
- **Title row:** shows the next objective ("0/10 Orange Mushroom Cap", or "Turn in: Bruce") with
  a thin progress bar, instead of the location (that's on the game's minimap).
- **Panel:** 320 wide, only as tall as its content, up to 55% of the screen (or the height you
  drag its bottom edge to). Auto-collapse (menu switch, on by default): going from the overlay
  back to the game folds the panel up 1.5 s later, unless the mouse is on it.
- **Quest cards:** closed = one row with a progress bar, done count and a green dot for live;
  open = the best map with a ➤ Go button, objectives, turn-in. No minimap in the card (map links
  start the GPS); "not tracked live" and monster levels moved into tooltips.
- **Snapping:** dragged near the game window's edges, its middle, or (GPS) the spot right of the
  minimap, a window lands exactly there.
- **Symbols:** one set of single-colour symbols instead of colour emoji; suggestions are two lines.
- **Tested:** logic 74/74, regression 38/38; flicker redraw check passes, the on-screen check
  again caught only a passing mouse and a 5/255 shift from the screen behind the 96% GPS.

### Fix: hidden overlay couldn't be brought back from the game
- **Cause:** MapleStory runs as administrator and UMBRΛLE doesn't; with the game focused, Windows
  often doesn't pass Ctrl+Shift+U / G on to the overlay (the overlay did own the shortcuts).
- **Fix:** opening UMBRΛLE again (start.bat or the .exe) now shows the copy that's already running
  (un-hides it, turns click-through off, moves it onto a screen) instead of starting a second one.
  The Hide menu item's tooltip says so. Tested: hidden + click-through copy, second launch exits in
  1 s, the first is visible and clickable again.

### Simplified: no click-through, no hiding, one shortcut
- At the user's request: click-through, Hide overlay and the Ctrl+Shift E / G / U / Home shortcuts
  are gone (with MapleStory running as administrator, Windows mostly kept them from working in the
  game anyway). The original Ctrl+Shift+S sync stays. Reset position is in the ⋯ menu; opening
  UMBRΛLE again brings the running one forward.

### Rounds 14-17: UX / UI audit
- **Round 14, audit:** screenshots of every screen (quests, mobs, items, training, PQ, menu, map
  search, GPS strip and opened, collapsed row) with the overlay solid.
- **Round 15, fixes:** the title row lost its ⟳ ▴ ⋯ buttons when expanded and the collapsed row was
  650 px wide: a progress bar (a canvas) asked for ~380 px. Bars now take no width of their own and
  the buttons are packed before the wordmark. Symbols: ➜ (GPS), ◎ (location), ⌕ (search) chosen
  from a rendered comparison (➤ and ⌖ came out tiny or blurred). Map search title in violet,
  search boxes 9 pt, the opened GPS has room for the "Then: ..." line under the map.
- **Round 16, comfort:** every text colour on every surface measured ≥ 5.1:1 (WCAG asks 4.5). GPS
  buttons in Mobs / Items lists are bigger targets; the drag handle lights up under the mouse;
  the panel's lowest height is 320 so it jumps less between tabs.
- **Round 17, polish:** the status line reads "Following the game (AUTO)". Re-audit: all screens OK.
- **Tested:** logic 74/74, regression 38/38; flicker: redraw check and map-change checks pass, the
  still-frame check keeps catching changes outside the app while the PC is in use.

### Free dragging
- At the user's request the magnet snapping is gone: the overlay and the GPS follow the mouse to
  the exact pixel. Still kept: a window dropped off every screen comes back to the nearest one.

### Pin on the title row, GPS docked to the game's minimap, GPS sizes
- **Pin (⚲)** on the title row: one click locks where the overlay and the GPS are (a lit violet
  chip while pinned); same setting as "Lock position" in the menu.
- **GPS docks to the minimap:** each sync finds the game's minimap window on the screenshot it
  already takes (`game_sync.find_minimap`: its 1 px steel-blue outline, #557799, rounded corners;
  ~4 ms) and puts the GPS against its right edge with the tops lined up. Minimaps differ per map,
  so the GPS moves along on every map change. Dragging the GPS undocks it; ⇱ in its ▾ (or Reset
  position) docks it again. Found before our own windows are blacked out of the screenshot.
- **GPS size:** small by default (72%), ⤢ in its ▾ cycles small / medium / large; text, arrow and
  the map scale with it.
- **Tested:** live on the game (Ant Tunnel II): minimap (189×196) found exactly, GPS docked at its
  right edge, tops equal, small and medium sizes; logic 74/74, regression 38/38.

### GPS docked = the minimap's size
- **Bug fixed:** any click on the GPS strip (no movement) counted as a drag and undocked it, so it
  stopped following the minimap. Now only a real drag (more than 3 px) undocks it.
- **Docked by default, map shown by default:** docked, the GPS is exactly as tall as the game's
  minimap (top and bottom lines level) and at least 215 px wide (as wide as the minimap if that's
  wider): the direction strip on top, the map fitted into the rest. Its buttons (Taxis, search,
  meowdb) appear over the bottom of the map only while the mouse is on it. It resizes along with
  the minimap on every map change. Undocked, the size setting (⤢) applies as before.
- **Tested live:** minimap (-1820, 83)-(-1609, 279) → GPS (-1608, 83)-(-1339, 280): tops and
  bottoms equal; a click keeps it docked, a drag undocks, ⇱ docks it back. Logic 74/74.

### Location read from inside the minimap window
- **Measured first:** the map name was read from a fixed corner of the game window (30% × 12%);
  the name line sat right at that crop's bottom edge, and the crop also took in game scenery
  (and other windows) next to the minimap.
- **Now:** `game_sync.read_location` crops just the name area of the minimap window found by
  `find_minimap` (right of the map icon, between the MINI MAP row and the outline under the name;
  `minimap_title`), enlarges it 3×, and reads it (as-is, then the white letters alone). The old
  corner read stays as the fallback when the window isn't found.
- **Faster:** a read from inside the window is sure and counts at once; the corner fallback still
  has to read the same twice in a row. A map change shows ~2 s sooner.
- **You can correct it:** click the location line (◎ …) and pick where you are ("I'm on:"). The
  reading's text then means that map from then on (`map_fixes` in state.json), and the sample is
  saved in cache/misreads/ (picture + what was read + the right map) to turn into a test.
- **Tests:** new FRAME_CASES in run_regression.py (Henesys; a live Ant Tunnel II shot, I vs II):
  42/42. Logic 74/74.

### Any resolution: the minimap found and read when the game stretches its windows
- **Reported:** after switching the game to 1920x1080 the GPS stayed put and didn't dock. Nothing
  assumed one resolution, but the outline test did assume an unstretched UI: at 1920x1080 the game
  scales its windows ~1.4x and the 1 px steel-blue outline blends with the white beside it
  ((103, 133, 164) on one side), so the exact-colour match found no window.
- **Fixes (`game_sync`):** the outline is matched by its colour family (red 62-132, green 18-44
  above it, blue 42-78 above it); sides are followed two pixel columns wide (a stretched line hops
  between columns), with corner reach and gap tolerance growing with the window's size; the
  bottom snaps to the last full-width outline line; the line under the map name is the first one
  without header blue below it (stretching blurs the MINI MAP row's edge into a fake line); the
  name area is scaled to one standard text size before OCR, and the white letters are read first
  (the letters' shadow made "II" read as "III"). A name ending in a number only counts as sure when
  that number was read.
- **Tests:** a live 1920x1080 shot plus the 1366 shot stretched 1.25-2.5x (bilinear, bicubic,
  nearest): window found to the pixel and "Ant Tunnel II" read in every case. Regression 56/56,
  logic 74/74. Live at 1920x1080: GPS docked, tops and bottoms equal.

### Focus on one quest
- **◉ on every quest card:** focus on just that quest. The panel then shows only it (open), with
  "All quests (n) ▸" to go back; ◉ again also goes back. The focus is saved (`focus_quest`) and
  ends by itself when the quest leaves the list.
- **Collapsed, focused:** the title row names the quest, and a card under it lists every
  objective ("0 / 20 Jr. Necki") with its own progress bar, then "➜ Turn in: Luke · Henesys
  Dungeon Entrance" (★ and violet once everything is done), plus a note when the counts aren't
  live. Before, the collapsed row showed only the first unfinished objective. The card is rebuilt
  only when something on it changes, and live counts update it.
- **Tested:** Luke the Security Guy (5 objectives), panel and collapsed screenshots; unfocusing
  while collapsed shrinks the row back. Logic 74/74, regression 56/56.

### Fix: the docked GPS got stuck over a wider minimap
- **Reported:** after moving to Swampy Land in a Deep Forest the GPS stayed over the minimap.
  Cause: the new map's minimap is wider than the last one, so it ran under the docked GPS; the sync
  reads the screen, where our GPS hid the minimap's right edge (and part of its name), so its new
  size could never be found.
- **Fix:** `find_minimap` gets our windows' rectangles: when the minimap's top edge runs into one
  of them and its right side can't be seen, it reports "blocked". The GPS then steps its own
  width to the right; the next sync (≤ 2 s) sees the whole minimap and docks exactly again. A map
  name read while half covered isn't used.
- **Tested:** covered vs docked-beside on the 1920 shot (regression 58/58), and live: a GPS left
  over the minimap stepped aside. Logic 74/74.

### Counting without the game's Quest Helper
- **Measured first:** 150 s of read-only screen recording while killing Jr. Neckis and looting
  their skins with the Quest Helper closed. The game itself shows the progress: on every kill or
  quest-item pickup it writes a gold line near the top of the screen for each quest that needs
  it, with the count ("Jr. Necki 5 / 40", "Jr. Necki 5 / 20": two quests want Jr. Neckis).
- **Reading them (`game_sync.read_notices`):** each sync checks the top-centre area for fresh
  bright gold (#ECC00C; a fading line drops out); only then it OCRs a "gold strength" picture
  ((r+g)/2-b, warm pixels only, doubled). ~70 ms when there's a line, almost nothing otherwise.
- **Matching (`App.notice_progress`):** a line belongs to an objective when it starts with its
  name and ends with its required count (so /40 and /20 go to the right quests); the slash, often
  read as "1" or "J" or lost ("19 120", "12 J 20", "5 40"), is sorted out with that count. When a
  glued "1" leaves two readings, the one right after the current count wins (the lower one with
  no count yet). Fewer than before needs a second agreeing reading. A line that came and went
  between two syncs (the "20 / 20" that finished an objective) is inferred: the same monster still
  counting for another quest while ours stands one short means ours is done.
- **Works for every quest on the list**, not only ones in the game's Quest Helper (that still
  works too, when it's visible).
- **Tested:** replaying the recording as syncs: every count climbs like the game's and ends right
  (Luke: Jr. Necki 20/20 and skins 10/10 done; Dr. Faymus: 32/40 and 13/20). Regression 62/62
  (4 cropped gold-line shots), logic 82/82 (the slash cases).

### Fix: the panel didn't stay open after "Reset from Quest window"
- Reset collapses the overlay so the game's Quest window is in view, and opens it again when done.
  Auto-collapse then folded it right back: the Reset click (overlay active) followed by Q in the
  game looked like "back to the game". While collapsed it now forgets that the overlay was the
  active window, so the reopened panel stays open. Tested with a simulated reset.

### Kills to level up (EXP bar + party split)
- **Asked:** how much % each kill gives, a small counter of kills left to level up on the current
  map, and how EXP splits in a party of 2-6.
- **Source:** meowdb.com Leveling & Tables (/msclassic/formulas/leveling): EXP to next level
  (Lv 1-5, 6-50, ×1.0548 from 51, ×2.1 from 90; matches its table) and the Party EXP formula
  (80% of the pool by level, 20% by damage; bonus +10% per extra member up to 30%, +5% per
  extra member who hit). Monster EXP from the monster list, as before.
- **New `leveling.py`** and `game_sync.read_exp_bar`: the game's status bar ("EXP. 5,340
  [11.31%]") is read on every sync (bright text only, enlarged; ~0.05 s, one pass when there's no
  bar). The % reads reliably, the number often not ("s 340"): it's used only when it matches the %.
- **Counter** under the location row on every tab: "▾ Lv 26 in 11.31% · 41,876 left", party chips
  1-6, and per monster on this map "Evil Eye 50 EXP +0.11% · 838 kills". With a party: all hit /
  I kill / I leech, and kills are the party's. Click the header to fold it.
- **Level box follows the bar:** to the level whose table fits both numbers ("5,340 [11.31%]" is
  only Lv 25), or +1 when the bar drops from near 100% to near 0%.
- **Tested:** bar read on live_frame_1920 (11.31%) and ant_tunnel2 (11.22%), none on frames
  without a bar; test_logic +16 → 98/98; run_regression 62/62; screenshots solo and party of 4.
  test_flicker 1/4, the same with the counter switched off (something else on screen moves).

### Fix: the EXP bar didn't update; EXP gauge next to the GPS; docked map from the top
- **Reported:** the counter never picked up the EXP bar; asked for a gauge right of the GPS's ✕,
  and for the docked GPS map to fill from the top like the game's minimap next to it.
- **Cause:** on the 2560x1440 game the bar's pixel digits read as "Sl .B7%" (51.87%) or
  "S3.34%" (53.34%), so no percent was found. **Fix:** the EXP text is located first (HP, MP and
  EXP are evenly spaced; the EXP text is one HP→MP step right of "MP"), then only that piece is
  read in 9 versions at once (contrast cut-offs and sizes). `leveling.read_bar` maps look-alike
  letters to digits (S→5, l→1, B→8...), trusts the EXP number when the percent (or just its two
  decimals) agrees at your level, else takes the percent most versions read (ties: nearest the
  last one). Read every 3rd auto sync (~0.5 s of OCR). A rising % counts at once; a drop or a
  level change must read the same twice.
- **EXP gauge** (`render_gauge`): a small window docked at the GPS's top-right, as tall as its
  strip (no GPS: right of the minimap): "Lv 26 · 53.34%", a bar, and kills left + % per kill for
  the map's busiest monster (party setting from the panel). ⋯ menu: "EXP gauge" switch.
- **Docked GPS map:** the minimap picture's see-through margins are trimmed and it's drawn right
  under the legend, so a wide map leaves its spare room at the bottom instead of above.
- **Tests:** run_regression + EXP bar on 4 real frames (the user's 2560 screen added as
  `live_exp_2560.png`) → 66/66; test_logic 103/103; screenshot of the GPS + gauge.

### EXP in the title row instead of the gauge window
- **Asked:** the separate EXP gauge wasn't liked; use the free space in the collapsed title row,
  and show it expanded (with a quest) too.
- **Removed** the gauge window (`render_gauge`, its GPS hooks and the ⋯ menu switch).
- **New** (`refresh_exp_pill`): the title row's top line, right of "UMBRΛLE ●", shows
  "53.34% · 570" (EXP bar % and kills left of this map's busiest monster); the tooltip names the
  monster and the % per kill. The space is only as wide as the status line under it (less when
  expanded at the panel's narrowest), so the longest wording that fits is picked ("… · 570 kills"
  down to "53.3%") and re-fitted whenever the row changes size. AUTO dot padding trimmed 3 px.
- **Tested:** screenshots collapsed and expanded with a quest at the app's real 96-dpi setting
  (both "53.34% · 570"); test_logic +1 → 104/104; run_regression 66/66.

### Trainer: the app picks the next step and steers the GPS
- **Asked:** a "trainer" that always knows what to do next and leads you there with the GPS:
  you play, it only reads the screen and shows the way. New quests only when close or with the
  monsters you already hunt; with nothing worth doing, a training map; a button in the title row.
- **New `trainer.py`** (logic only): candidates in order: turn in a finished quest (nearest NPC);
  take a suggested quest that's ≤ 4 portals away or shares your hunted monsters and is worth ≥ half
  your best open quest (up to 6 open quests; with none open, the best one ≤ 10 portals); hunt on
  the map covering the most open objectives across all quests (maps with < 30% of the busiest's
  monsters left out); else train on the nearest of the 5 busiest maps for your level.
  `Trainer` keeps its step until an event (quest taken / done / turned in, level-up, new guide,
  Skip); a map change only switches to a step ≥ 3 portals closer.
- **App:** ▶/❚❚ in the title row (saved as `trainer_on`); the status line shows "▶ Take: …",
  "▶ Hunt: Slime + Green Mushroom (3 quests)", "▶ Turn in: …", "▶ Train: …"; a TRAINER card on
  top of the Quests tab with why, Skip and Pause; the GPS follows route key "trainer"; ✕ on the
  GPS pauses the trainer. `suggested_quests(sort=)` lets it rank by value whatever the tab shows.
- **Tried on the user's list** (Kerning, Lv 26, 5 quests): Roxy's quest 1 portal away first, then
  L Forest III (4 objectives of 3 quests). Screenshots collapsed / expanded / GPS.
- **Tests:** test_logic +13 → 117/117.

### Quest rewards: shown everywhere, and counted when you want
- **Asked:** show each quest's full reward, and let the trainer weigh mesos / items too.
- **Source:** meowdb.com quest list (already downloaded): `exp` (369 quests), `mesos` (347), `get`
  items (240), `rewardChoices` (13), `rewardRandom` (35), `fame` (28), `contribution` (115).
- **Shown:** 🎁 line at the top of an open quest card ("188 EXP · 351 mesos"), on the trainer
  card for a quest to take or turn in, and in the suggestions (mesos + 🎁 on the short line, the
  whole reward on hover). `quest_rank.reward_text`.
- **Counted:** "Also count: Mesos · Items · Citizenship" (`reward_prefs`; on the trainer card, or
  under the suggestions with the trainer off). Mesos and contribution count as much EXP as they
  usually come with in quests within 10 levels of yours (median EXP per meso / per point, about
  3.6 and 20 at Lv 26); items +15%, scrolls +30%. `quest_rank.reward_points` feeds the score of
  `estimate`, so suggestions, "Best EXP/min" and the trainer all follow the switches.
- **Tests:** test_logic +7 → 124/124; screenshot of the Quests tab.

### Quest guides from meowdb, NPC hints, citizenship town, dock in the corner
- **Asked:** pick Henesys or Kerning City for Citizenship; put meowdb's jump quest guide (and any
  other guide that explains quests) into the app: "I'm on Sabitrama and the Diet Medicine and had
  no idea what to do"; then a button that docks the overlay in the top-right corner.
- **Sources:** meowdb.com/msclassic/guides: jump-quests, mark-of-the-beta-event-guide,
  forgotten-hollow-the-new-endgame-area, beginners-guide-first-steps-in-maple-world,
  kerning-city-party-quest-kpq-guide (the other 66 guides are about classes or other games);
  each quest's own page (/quest-tracker/<id>) for its NPC's "If you accept" words.
- **New `guides.py`:** the pages are RSC payloads split over numbered lines that refer to each
  other; read in page order, cut at headings. Guide tables link quests by id, so each quest gets
  its own row (Bring back / What you do / Where / Journal hint / Start and turn-in), its section's
  notes when the section is about ≤ 3 quests ("Get in: Talk to Shane in Ellinia…", map rules),
  sections that describe its "Where" ("Page 2: The Pig Beach"), NPC + map pairs and its own
  step maps. 45 quests have a guide. `MeowDB.quest_guides` (loaded with the indexes, optional) and
  `MeowDB.quest_hint` (fetched per active quest in the background, cached 30 days).
- **Quest card:** under the 🎁 line, a 📖 box (link to the guide section, facts, notes, 🧭 NPC
  buttons, step links) or, without a guide, 💬 the NPC's words with 🧭 buttons for maps it names.
- **Trainer:** new "go" step after hunting, for open quests with nothing to hunt: the NPC that
  lets you in (Shane), "Talk to Jay in Henesys", the "Where" place, or the map the NPC names.
- **Citizenship:** clicking it asks "Your town: Henesys / Kerning City"; only that town's
  contribution counts ("citizen:Henesys" in quest_rank.reward_points); the chip shows the town.
- **◥ in the title row:** docks the overlay flush in the game window's top-right corner and keeps
  it there through expand / collapse, resizes and the game window moving (checked on every sync);
  dragging it away undocks it.
- **Tests:** test_logic +13 → 137/137 (the corner test uses a fake game window, off screen);
  screenshots of the Sabitrama, First Mark and Chrishrama cards.

### Items tab: how to get an item, with the quest's steps
- **Asked:** when an item has a special way to get it (like the Pink Anthurium of Sabitrama's
  jump quest), the item search should show that way and its steps.
- **New:** `App.item_quests(item id)` indexes every quest's `need` and rewards (`get`,
  `rewardChoices`, `rewardRandom`). An opened item now shows, after its shops:
  - **🎯 Get it in:** for quest items (403xxxx, collected inside the quest), the quest with its
    level, "From Sabitrama · Sleepywood · 10 away" (GPS link) and the quest's 📖 guide box (or 💬
    its NPC's words), the same as on the quest card; quests with a guide first.
  - **🎁 A reward of:** quests that give the item, with who starts them (GPS link).
  Ordinary items skip "Get it in": quests that ask for a Screw use it up, they don't give it.
  The guide box takes a route key, so its GPS buttons follow the Items tab's route ("item").
- **Tests:** test_logic +3 → 140/140; screenshots for "pink anthurium" and "star rock".
