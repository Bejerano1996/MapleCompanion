# 3.25 candidate
Applying an explicit manual EXP correction invalidates older in-flight reward/HUD reads so they cannot immediately overwrite the correction. The next fresh reader establishes a new baseline; differences between the correction and that baseline are not invented as session gains or losses. Blank EXP preserves normal automatic continuity.
Validation uses isolated native UI callbacks, recorded-image OCR and synthetic streams, not live gameplay. Existing partial-visibility and reconciliation limits remain.
