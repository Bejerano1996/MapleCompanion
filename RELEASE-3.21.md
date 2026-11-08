# 3.21 candidate
A callback from a superseded reader/accountant cannot mutate session totals after rapid automatic/manual transitions or baseline reset. Wallet restart assigns a unique in-memory scope, so old wallet captures cannot anchor the new balance; valid EXP from the same capture is preserved.
User saves are unchanged. Validation is recorded/synthetic, not live gameplay. Existing partial-visibility,15second capture-age and five-second stable-HUD policy limitations remain.
