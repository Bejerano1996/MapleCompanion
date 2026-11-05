# Umbrale Companion 3.15

A separate party-bonus-only HUD increase now invalidates learned base-only EXP samples. This prevents a base7andlaterbonus2sequence from becoming an incorrect learned7EXP/event estimate.

Late bonus OCR with an unchanged HUD does not invalidate a valid complete-yield estimate. Three fresh complete windows can recalibrate after an invalidation. Split-only streams remain uncalibrated rather than guessed; the session EXP accounting still includes observed party bonuses.

Tested with local images, synthetic accounting and native UI callbacks, not live gameplay. Notice ambiguity can still leave totals incomplete.

Close the companion before installing software files. Preserve state.json and caches.
