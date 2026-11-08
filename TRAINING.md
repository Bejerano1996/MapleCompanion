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
