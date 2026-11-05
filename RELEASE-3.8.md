# Umbrale Companion 3.8

- Preserves a short-lived record of party bonuses already included in the EXP bar across a net EXP loss, preventing delayed OCR from adding the bonus again.
- Retries at most one unread mesos row per poll using recognition only. The original row and an autocontrast view must agree. Recovered money still requires normal confirmation across polls.
- Includes the 3.7 level-confirmation, map-plausibility, stale-callback and exact-counter fixes.

Validated with local screenshots, synthetic timing/accounting tests and an isolated native UI stability run. These are not live gameplay measurements. Unread or indistinguishable notices can still make pickup totals incomplete; visible monster/party data remain estimates.

Installation replaces program files only. Keep state.json and caches. Close the companion before installing. The existing folder may still be named Umbrale Companion 2.2.
