# Simulated account without crypto (01.11.2026)
`recompute_nocrypto.py` replays the account from the official 16.10.2026 balance ($27,460) to the 30.10.2026 close with the
stock positions only (same rules and dedup lists as the box ledger). Output: `account_nocrypto.csv`.
Check: at the old (crypto-inclusive) slot sizes the stock legs reproduce the ledger's stock components (e.g. trial 22.10
-630.12 x 5217.39/4615.38 = -712.3 here; 23.10 +392.35 -> +443.5).
Limits: crypto P&L before 16.10 is inside the $27,460 baseline (not separable); stops on 30.10 checked with the 29.10
levels, exit at the stop price; trial COP is kept on the ledger's entry 132.76 without a half (the tracker has a different COP row).
