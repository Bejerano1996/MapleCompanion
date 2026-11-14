# Umbrale Companion 3.37

## Data request compatibility and actionable errors

The game indexes could load from disk while uncached quest help and minimap requests failed. The old outbound User-Agent embedded a personal email identifier. This release uses a product-only identifier; live checks downloaded the previously failing quest pages 10300 and 10113 and minimap images 010001081 and 010001102 successfully, with HTTPS verification unchanged.

The compact status line now distinguishes rejected requests (403), unavailable resources (404), rate limits, server outages, TLS, DNS and timeout failures. Clicking an error opens its full, selectable details. A background request failure no longer implies that all game data is unavailable.

## Validation

- Three request-identity and error-classification unit tests.
- 45 compact UI checks, including the new HTTP reason and details dialog.
- Nine sync generation/missing-game checks.
- 23 training-model checks, five quest rediscovery/reward checks, three realtime reader checks and six publication-tool checks.
- Four direct live downloads using the new product-only identity; no personal identifier was sent by these checks.

Publication uses the existing Windows build/test/package workflow. Source/program ZIPs, manifest and checksums accompany the release. No character state, caches or local diagnostics are included.
