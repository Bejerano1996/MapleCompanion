# Umbrale Companion 3.13

Automatic training context now stays unknown until fresh map/monster evidence arrives. A saved manual target does not become a current observation at startup. Explicit manual mode remains available.

Monster label recognition requires the level label at the start of the OCR line. Instruction/chat prefixes such as Hunt Lv.19 no longer count as visible monster labels.

Includes prior party EXP, notice identity, money confidence and compact UI fixes. Validation uses supplied images, synthetic scenarios and isolated native UI tests, not live gameplay. Visible monsters remain inferred context, not proof of personally killed species.

Close the companion before replacing program files. Preserve state.json and caches.
