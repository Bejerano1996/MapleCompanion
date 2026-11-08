# Training sessions

- Start/resume records the current session; Pause excludes paused time and rewards.
- After two validated EXP-bar readings, session EXP is the bar difference, including party and quests, with deaths reflected as net losses. It replaces the log sum, so party bonuses are not added twice.
- When the bar is unavailable, visible reward messages are a partial fallback. Party shown as “seen” is the subset identified in notices, already included in bar EXP.
- Mesos require two matching reads and are visible pickups observed in notices, not an automatic wallet balance. Hidden, faded or indistinguishable repeated messages can be missed. Expenses remain manual. Manual mode lets you correct totals.
- Setup selects a monster and eligible party members on the map. The forecast rounds remaining EXP / your EXP per kill upward. Blank party levels assumes equal levels; all/me/leech describe who damages the monster. The formula assumes the party receives the monster EXP pool.
- An optional personal EXP-per-kill override includes the bonus already. It is tied to the selected monster, level and party settings, and expires when those change.
- Level and current EXP can be calibrated explicitly. Automatic calibration requires an integer EXP and matching percentage; percentage-only guesses do not change the level. Supported forecast table: Classic levels 1–99.
- A stale forecast is marked Last read. It is an estimate of future kills under the chosen conditions, not an exact personal kill counter. Session kill counts are EXP-event estimates including shared party rewards.
- All game integration is read-only screen capture. The training OCR runs locally, uses CPU models bundled with the app, and sends no game screenshots to a server.

Formula reference, verified 2026-10-29: https://meowdb.com/msclassic/formulas/leveling

Validation reports distinguish supplied screenshot fixtures, synthetic streams, and any actual live checks. The timed soak records source revisions; it does not claim three hours of live gameplay.

## Wallet balance mode (3.1)
Session → Mesos · wallet checkpoints → Start automatic wallet reading.
Keep ITEM INVENTORY open in the upper-right 30% of the game, within its top65%, with the balance and MESOS label unobscured. The first verified reading starts a new money baseline. Readings are attempted about every3seconds when the reader is free. Closing or covering the inventory preserves the last checkpoint; the reading age shows freshness. This measures net wallet change including spending, trades and storage transfers, not gross loot. Loot notices are ignored for money in wallet mode. Costs are not subtracted twice. Resume rebaselines and excludes offline balance changes. Manual starting/current balances are an alternative. Wallet reading never opens the inventory or sends game input.

## Pickup notice mode (3.2)
Session → Mesos · read pickup notices selects the floating gained-mesos notifications in the lower-right, with inventory closed. It disables wallet auto-reading. Switching from wallet starts a new money baseline and preserves EXP/kill totals. Only the new money period enters mesos/hour.
The tracker now carries row positions and estimates scroll movement from matching notices before matching OCR corrections. The post-read wait is120ms instead of450ms. These do not guarantee capture of every transient notice: hidden amounts, OCR errors, or an indistinguishable fully replaced identical stack can remain unresolved. Session totals remain observed estimates; do not describe them as verified exact money telemetry.
Version3.2 was checked with local OCR fixtures and deterministic scrolling-message tests. No live3.2 comparison was completed because the game closed before validation.

## Automatic game context (3.3)
Setup → Detect map, visible monsters and party automatically is enabled by default. During a running session a separate, single background job reads minimap title, upper-right roster and tiled monster labels about every8seconds. Context OCR has its own CPU engine, so it does not serialize reward reads.
Map and roster changes require repeated observations. Roman I/II/III map suffixes use the actual title glyphs to prevent OCR collapsing them. Occluded or stale evidence is unknown. Party bonus notices prove recent party activity, not size. The displayed count is visible roster members, not proof of all eligible members on the map. No panel does not imply solo; manual Setup remains available.
Visible monster labels are observations, not definitive victim identity. One visible species can provide an estimated target. Multiple species do not choose an arbitrary target. Observed species are retained in the session separately from estimated EXP-event kills. Formula party shares are estimates; actual training EXP still uses validated HUD changes. No inputs or game-memory access.
Validation: recorded Ant TunnelII/III variants, recorded4and5member rosters including low HP, and Horny Mushroom labels; live independent minimap read of Land of Wild Boar. Installed end-to-end automatic polling still requires live validation.

## Personal EXP/event calibration (3.4)
Three matching observations can calibrate personal yield: exactly one newly credited base EXP event, and its total EXP including credited bonus must equal the difference between consecutive validated HUD readings. Multiple base events, incomplete bonus totals, quest gains and negative HUD changes do not calibrate. This is a correlated estimate of personal EXP per reward event, not proof of which player killed the monster.
A single current target is required. Calibration is cleared on target, map, own level or observed party-context changes, including returning to an earlier map, and expires after45seconds without a valid sample. A changed yield must earn three new matching samples. It can supply a forecast even when roster size is unknown; no solo membership is invented. Explicit manual gain retains priority.
If multiple species are visible and the roster is readable, separate formula estimates for up to two species are shown. These remain estimates by visible species. EXP widgets are reused between readings to avoid repeated rebuilds.

## Notice/HUD timing reconciliation (3.5)
Notice rewards and the HUD can update in either order. Uncovered notice EXP is retained across unchanged HUD reads, then consumed by later matching HUD gains. A short, bounded credit for a plausible unread party bonus prevents a later refinement from being added again after the HUD has already included it. New complete base+bonus rewards are not consumed as old missing bonuses. Fresh net losses clear extrapolation so fallback cannot undo a recorded loss. HUD changes remain authoritative while readable; fallback is still a partial observed estimate.
Offline regression reproduces the previous9-to11EXP double count and covers delayed refinement, new rewards during the delay, HUD-leading/log-leading timing, net loss and level boundaries.100seeded12reward schedules with varied HUD/bonus delay also pass. These are simulations, not live-game validation.
