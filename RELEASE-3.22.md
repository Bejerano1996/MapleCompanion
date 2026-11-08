# 3.22 candidate
Map comparison now validates each saved session money-time anchor before adding its totals. A malformed row is counted as excluded rather than crashing the entire comparison or poisoning valid rates. Saved history is not rewritten. Missing/None and numeric string legacy anchors remain supported.
Validation uses synthetic and recorded inputs, not live gameplay. Existing OCR/partial-visibility and reconciliation policy limitations remain.
