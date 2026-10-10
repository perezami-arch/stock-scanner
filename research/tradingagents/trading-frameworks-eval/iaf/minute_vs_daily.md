Timed setups (exact/schedule/ui_log) in main non-dup population with a minute entry: 464; of which entry moved vs daily version: stocks 20, crypto 99 (all crypto timed entries move from next 00:00 UTC to the alert minute).

| policy | source | asset | dir | subset | N | DAILY-cutoff mean / median / hit / x_mkt (w/o top1) | EXACT-MINUTE mean / median / hit / x_mkt (w/o top1) | Δmean pp | Δmedian pp |
|---|---|---|---|---|---|---|---|---|---|
| hold | Bot | stock | LONG | all timed | 30 | +2.3 / +0.3 / 53% / +1.0 (w/o top1 -0.0) | +2.3 / +0.3 / 53% / +1.0 (w/o top1 -0.0) | +0.00 | +0.00 |
| hold | Bot | stock | SHORT | all timed | 19 | +0.0 / +0.8 / 58% / +1.3 (w/o top1 +0.6) | -0.0 / +0.8 / 58% / +1.3 (w/o top1 +0.7) | -0.01 | -0.00 |
| hold | Grok | crypto | LONG | all timed | 54 | +4.5 / +3.5 / 67% / +0.6 (w/o top1 -0.2) | +4.9 / +3.9 / 69% / +0.9 (w/o top1 +0.0) | +0.38 | -0.02 |
| hold | Grok | crypto | LONG | entry changed | 54 | +4.5 / +3.5 / 67% / +0.6 (w/o top1 -0.2) | +4.9 / +3.9 / 69% / +0.9 (w/o top1 +0.0) | +0.38 | -0.02 |
| hold | Grok | crypto | SHORT | all timed | 36 | -2.6 / -2.0 / 42% / +1.0 (w/o top1 +0.2) | -2.5 / -2.1 / 42% / +0.9 (w/o top1 -0.0) | +0.07 | +0.06 |
| hold | Grok | crypto | SHORT | entry changed | 36 | -2.6 / -2.0 / 42% / +1.0 (w/o top1 +0.2) | -2.5 / -2.1 / 42% / +0.9 (w/o top1 -0.0) | +0.07 | +0.06 |
| hold | Grok | stock | LONG | all timed | 127 | +0.9 / +0.3 / 54% / -0.7 (w/o top1 -1.1) | +0.8 / +0.3 / 53% / -0.8 (w/o top1 -1.3) | -0.13 | +0.00 |
| hold | Grok | stock | SHORT | all timed | 119 | -1.0 / -1.8 / 40% / +0.5 (w/o top1 +0.3) | -1.0 / -1.8 / 40% / +0.5 (w/o top1 +0.3) | -0.00 | -0.00 |
| hold | Perplexity | crypto | LONG | all timed | 9 | +46.1 / +49.7 / 100% / +14.4 (w/o top1 +12.4) | +45.5 / +50.3 / 100% / +14.5 (w/o top1 +12.4) | -0.58 | -0.69 |
| hold | Perplexity | crypto | LONG | entry changed | 9 | +46.1 / +49.7 / 100% / +14.4 (w/o top1 +12.4) | +45.5 / +50.3 / 100% / +14.5 (w/o top1 +12.4) | -0.58 | -0.69 |
| hold | Perplexity | stock | LONG | all timed | 42 | +1.9 / +0.6 / 55% / +0.9 (w/o top1 +0.1) | +1.6 / +0.4 / 55% / +0.6 (w/o top1 -0.3) | -0.28 | -0.00 |
| hold | Perplexity | stock | LONG | entry changed | 14 | +3.2 / -0.0 / 50% / +3.0 (w/o top1 +0.5) | +2.4 / -1.2 / 50% / +2.1 (w/o top1 -0.5) | -0.81 | -1.32 |
| hold | Perplexity | stock | SHORT | all timed | 28 | -3.0 / -2.3 / 39% / -1.9 (w/o top1 -2.6) | -2.9 / -2.3 / 39% / -1.7 (w/o top1 -2.5) | +0.15 | -0.00 |
| hold | Perplexity | stock | SHORT | entry changed | 6 | -11.1 / -10.2 / 33% / -10.8 (w/o top1 -14.5) | -10.3 / -10.3 / 33% / -9.9 (w/o top1 -13.7) | +0.78 | -0.12 |
| t8 | Bot | stock | LONG | all timed | 30 | +2.3 / +0.3 / 53% / +1.0 (w/o top1 -0.0) | +2.3 / +0.3 / 53% / +1.0 (w/o top1 -0.0) | +0.00 | +0.00 |
| t8 | Bot | stock | SHORT | all timed | 19 | -0.2 / +0.2 / 53% / +0.9 (w/o top1 +0.3) | -0.2 / +0.2 / 53% / +0.9 (w/o top1 +0.3) | -0.01 | -0.00 |
| t8 | Grok | crypto | LONG | all timed | 54 | +2.4 / +2.6 / 56% / -0.4 (w/o top1 -1.0) | +1.9 / +1.8 / 54% / -0.5 (w/o top1 -0.8) | -0.54 | -0.24 |
| t8 | Grok | crypto | LONG | entry changed | 54 | +2.4 / +2.6 / 56% / -0.4 (w/o top1 -1.0) | +1.9 / +1.8 / 54% / -0.5 (w/o top1 -0.8) | -0.54 | -0.24 |
| t8 | Grok | crypto | SHORT | all timed | 36 | -2.7 / -2.7 / 42% / +0.4 (w/o top1 +0.0) | -3.1 / -3.3 / 42% / -0.0 (w/o top1 -0.5) | -0.42 | +0.09 |
| t8 | Grok | crypto | SHORT | entry changed | 36 | -2.7 / -2.7 / 42% / +0.4 (w/o top1 +0.0) | -3.1 / -3.3 / 42% / -0.0 (w/o top1 -0.5) | -0.42 | +0.09 |
| t8 | Grok | stock | LONG | all timed | 127 | +0.8 / +0.1 / 52% / -0.4 (w/o top1 -0.7) | +0.7 / +0.0 / 51% / -0.5 (w/o top1 -0.9) | -0.13 | +0.00 |
| t8 | Grok | stock | SHORT | all timed | 119 | -1.2 / -2.5 / 35% / -0.1 (w/o top1 -0.3) | -1.2 / -2.5 / 35% / -0.1 (w/o top1 -0.3) | -0.00 | -0.00 |
| t8 | Perplexity | crypto | LONG | all timed | 9 | +30.6 / +31.9 / 100% / +3.9 (w/o top1 +2.0) | +30.1 / +31.8 / 100% / +4.0 (w/o top1 +2.1) | -0.52 | -0.64 |
| t8 | Perplexity | crypto | LONG | entry changed | 9 | +30.6 / +31.9 / 100% / +3.9 (w/o top1 +2.0) | +30.1 / +31.8 / 100% / +4.0 (w/o top1 +2.1) | -0.52 | -0.64 |
| t8 | Perplexity | stock | LONG | all timed | 42 | -0.8 / -2.0 / 43% / -0.8 (w/o top1 -1.4) | -0.8 / -2.3 / 40% / -0.9 (w/o top1 -1.5) | -0.04 | -0.00 |
| t8 | Perplexity | stock | LONG | entry changed | 14 | -2.2 / -3.6 / 29% / -0.7 (w/o top1 -2.5) | -2.3 / -3.7 / 21% / -0.9 (w/o top1 -2.8) | -0.09 | -0.88 |
| t8 | Perplexity | stock | SHORT | all timed | 28 | -3.1 / -3.5 / 29% / -2.5 (w/o top1 -3.0) | -2.8 / -3.5 / 29% / -2.1 (w/o top1 -2.6) | +0.26 | -0.00 |
| t8 | Perplexity | stock | SHORT | entry changed | 6 | -6.5 / -5.4 / 33% / -7.6 (w/o top1 -11.2) | -5.2 / -7.6 / 33% / -5.8 (w/o top1 -9.0) | +1.31 | -0.16 |
| fsetup | Bot | stock | LONG | all timed | 30 | +1.9 / -0.2 / 50% / +1.1 (w/o top1 +0.0) | +1.9 / -0.2 / 50% / +1.1 (w/o top1 +0.0) | +0.00 | +0.00 |
| fsetup | Bot | stock | SHORT | all timed | 19 | -0.9 / -0.9 / 47% / +0.2 (w/o top1 -0.5) | -0.9 / -0.9 / 47% / +0.2 (w/o top1 -0.5) | -0.01 | -0.00 |
| fsetup | Grok | crypto | LONG | all timed | 54 | +2.5 / +2.2 / 56% / -0.3 (w/o top1 -0.9) | +2.9 / +2.7 / 57% / -0.0 (w/o top1 -0.7) | +0.38 | -0.02 |
| fsetup | Grok | crypto | LONG | entry changed | 54 | +2.5 / +2.2 / 56% / -0.3 (w/o top1 -0.9) | +2.9 / +2.7 / 57% / -0.0 (w/o top1 -0.7) | +0.38 | -0.02 |
| fsetup | Grok | crypto | SHORT | all timed | 36 | -3.9 / -4.7 / 36% / -0.0 (w/o top1 -0.5) | -4.2 / -5.2 / 36% / -0.2 (w/o top1 -0.7) | -0.32 | +0.03 |
| fsetup | Grok | crypto | SHORT | entry changed | 36 | -3.9 / -4.7 / 36% / -0.0 (w/o top1 -0.5) | -4.2 / -5.2 / 36% / -0.2 (w/o top1 -0.7) | -0.32 | +0.03 |
| fsetup | Grok | stock | LONG | all timed | 127 | +0.5 / +0.0 / 51% / -0.6 (w/o top1 -1.0) | +0.4 / +0.0 / 50% / -0.7 (w/o top1 -1.1) | -0.13 | +0.00 |
| fsetup | Grok | stock | SHORT | all timed | 119 | -0.9 / -2.3 / 36% / +0.3 (w/o top1 +0.0) | -0.9 / -2.3 / 36% / +0.3 (w/o top1 +0.0) | -0.00 | -0.00 |
| fsetup | Perplexity | crypto | LONG | all timed | 9 | +46.1 / +49.7 / 100% / +14.4 (w/o top1 +12.4) | +45.5 / +50.3 / 100% / +14.5 (w/o top1 +12.4) | -0.58 | -0.69 |
| fsetup | Perplexity | crypto | LONG | entry changed | 9 | +46.1 / +49.7 / 100% / +14.4 (w/o top1 +12.4) | +45.5 / +50.3 / 100% / +14.5 (w/o top1 +12.4) | -0.58 | -0.69 |
| fsetup | Perplexity | stock | LONG | all timed | 42 | +1.7 / -0.8 / 48% / +1.3 (w/o top1 +0.4) | +1.5 / -0.5 / 48% / +1.0 (w/o top1 +0.1) | -0.28 | -0.00 |
| fsetup | Perplexity | stock | LONG | entry changed | 14 | +4.0 / -0.0 / 50% / +4.2 (w/o top1 +1.7) | +3.2 / -1.2 / 50% / +3.3 (w/o top1 +0.8) | -0.81 | -1.32 |
| fsetup | Perplexity | stock | SHORT | all timed | 28 | -2.7 / -2.3 / 39% / -1.7 (w/o top1 -2.5) | -2.5 / -2.3 / 39% / -1.5 (w/o top1 -2.3) | +0.15 | -0.00 |
| fsetup | Perplexity | stock | SHORT | entry changed | 6 | -11.1 / -10.2 / 33% / -10.8 (w/o top1 -14.5) | -10.3 / -10.3 / 33% / -9.9 (w/o top1 -13.7) | +0.78 | -0.12 |