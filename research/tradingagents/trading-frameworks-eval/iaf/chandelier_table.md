### J. ATR chandelier TRAILING stops (highest close since entry - k*ATR14; ATR & extreme as of previous bar) vs hold / fixed ATR / trailing 8% (same setups; x_mkt = vs SPY stocks, vs BTC crypto; open trades marked at 2026-10-07 close)
| segment | policy | N | exited | still_open | stopped | mean | median | hit | x_mkt | mean_wo_top1 | mean_wo_top3 | x_mkt_wo_top1 | x_mkt_wo_top3 | days | days_exited | flag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Grok crypto LONG | hold, no stop | 255 | 0 | 255 | +0.0 | +36.9 | +32.1 | 93 | +14.7 | +36.3 | +30.8 | +14.0 | +8.6 | +53.3 | +nan | robust to top-3 removal |
| Grok crypto LONG | trailing 8% (close) | 255 | 140 | 115 | +54.9 | +18.2 | +22.9 | 76 | +3.6 | +17.1 | +15.9 | +2.5 | +0.8 | +32.0 | +19.0 | robust to top-3 removal |
| Grok crypto LONG | fixed 2xATR (close) | 255 | 39 | 216 | +15.3 | +29.0 | +28.7 | 77 | +11.0 | +27.3 | +23.0 | +9.8 | +5.5 | +44.7 | +10.4 | robust to top-3 removal |
| Grok crypto LONG | fixed 3xATR (close) | 255 | 15 | 240 | +5.9 | +33.1 | +31.1 | 87 | +12.6 | +31.7 | +26.8 | +11.3 | +6.5 | +50.2 | +12.3 | robust to top-3 removal |
| Grok crypto LONG | chandelier 2xATR (close) | 255 | 218 | 37 | +85.5 | +15.9 | +12.4 | 67 | +4.8 | +14.5 | +12.5 | +3.5 | +1.4 | +26.8 | +28.2 | robust to top-3 removal |
| Grok crypto LONG | chandelier 3xATR (close) | 255 | 74 | 181 | +29.0 | +27.2 | +27.5 | 79 | +10.0 | +24.5 | +19.2 | +8.2 | +3.3 | +43.3 | +25.7 | robust to top-3 removal |
| Grok crypto LONG | chandelier 4xATR (close) | 255 | 19 | 236 | +7.5 | +32.7 | +30.5 | 85 | +12.8 | +31.2 | +26.3 | +11.6 | +6.9 | +49.2 | +19.4 | robust to top-3 removal |
| Grok crypto LONG | fixed 2xATR (intraday) | 255 | 46 | 209 | +18.0 | +27.4 | +28.1 | 75 | +10.2 | +25.6 | +21.4 | +8.8 | +5.3 | +42.8 | +8.6 | robust to top-3 removal |
| Grok crypto LONG | fixed 3xATR (intraday) | 255 | 19 | 236 | +7.5 | +32.6 | +31.0 | 85 | +12.4 | +31.0 | +26.1 | +11.1 | +6.3 | +49.4 | +12.2 | robust to top-3 removal |
| Grok crypto LONG | chandelier 2xATR (intraday) | 255 | 222 | 33 | +87.1 | +15.6 | +10.8 | 64 | +4.9 | +14.1 | +12.3 | +3.5 | +1.6 | +23.9 | +24.9 | robust to top-3 removal |
| Grok crypto LONG | chandelier 3xATR (intraday) | 255 | 114 | 141 | +44.7 | +22.2 | +22.8 | 76 | +7.4 | +20.2 | +18.0 | +5.7 | +3.0 | +38.0 | +27.3 | robust to top-3 removal |
| Grok crypto LONG | chandelier 4xATR (intraday) | 255 | 45 | 210 | +17.6 | +29.3 | +28.5 | 82 | +10.9 | +27.0 | +21.9 | +9.3 | +4.4 | +46.3 | +26.8 | robust to top-3 removal |
| All stock LONG | hold, no stop | 242 | 0 | 242 | +0.0 | +3.2 | +0.4 | 54 | +1.6 | +2.5 | +1.5 | +0.9 | -0.0 | +19.1 | +nan | LUCK (edge gone w/o top tickers) |
| All stock LONG | trailing 8% (close) | 242 | 103 | 139 | +42.6 | +1.6 | +0.0 | 51 | +0.7 | +0.9 | +0.3 | +0.0 | -0.5 | +11.5 | +11.4 | LUCK (edge gone w/o top tickers) |
| All stock LONG | fixed 2xATR (close) | 242 | 65 | 177 | +26.9 | +2.5 | +0.0 | 51 | +1.4 | +1.8 | +0.9 | +0.7 | -0.2 | +15.0 | +10.0 | LUCK (edge gone w/o top tickers) |
| All stock LONG | fixed 3xATR (close) | 242 | 34 | 208 | +14.0 | +3.5 | +0.3 | 53 | +2.2 | +2.8 | +1.9 | +1.5 | +0.6 | +17.2 | +11.9 | robust to top-3 removal |
| All stock LONG | chandelier 2xATR (close) | 242 | 112 | 130 | +46.3 | +1.9 | -0.6 | 47 | +1.1 | +1.2 | +0.5 | +0.4 | -0.3 | +11.8 | +12.0 | LUCK (edge gone w/o top tickers) |
| All stock LONG | chandelier 3xATR (close) | 242 | 67 | 175 | +27.7 | +2.9 | +0.0 | 50 | +1.7 | +2.2 | +1.2 | +1.0 | +0.1 | +15.6 | +18.0 | robust to top-3 removal |
| All stock LONG | chandelier 4xATR (close) | 242 | 41 | 201 | +16.9 | +3.2 | +0.3 | 53 | +1.9 | +2.5 | +1.6 | +1.2 | +0.3 | +17.0 | +20.6 | robust to top-3 removal |
| All stock LONG | fixed 2xATR (intraday) | 242 | 76 | 166 | +31.4 | +2.6 | +0.0 | 50 | +1.7 | +1.9 | +1.1 | +1.0 | +0.1 | +14.0 | +7.4 | robust to top-3 removal |
| All stock LONG | fixed 3xATR (intraday) | 242 | 37 | 205 | +15.3 | +3.5 | +0.3 | 53 | +2.3 | +2.9 | +1.9 | +1.6 | +0.7 | +16.9 | +10.1 | robust to top-3 removal |
| All stock LONG | chandelier 2xATR (intraday) | 242 | 136 | 106 | +56.2 | +1.4 | -1.2 | 42 | +0.8 | +0.7 | +0.1 | +0.1 | -0.5 | +10.1 | +10.3 | LUCK (edge gone w/o top tickers) |
| All stock LONG | chandelier 3xATR (intraday) | 242 | 76 | 166 | +31.4 | +2.8 | -0.2 | 50 | +1.7 | +2.1 | +1.2 | +1.0 | +0.2 | +14.7 | +16.0 | robust to top-3 removal |
| All stock LONG | chandelier 4xATR (intraday) | 242 | 47 | 195 | +19.4 | +3.4 | +0.3 | 53 | +2.1 | +2.7 | +1.7 | +1.4 | +0.5 | +16.7 | +18.3 | robust to top-3 removal |
| Rule-filtered stock LONG | hold, no stop | 115 | 0 | 115 | +0.0 | +5.0 | +1.1 | 63 | +3.5 | +3.6 | +1.9 | +2.1 | +0.3 | +19.8 | +nan | robust to top-3 removal |
| Rule-filtered stock LONG | trailing 8% (close) | 115 | 51 | 64 | +44.3 | +3.4 | +0.4 | 57 | +2.6 | +2.0 | +1.2 | +1.1 | +0.4 | +11.9 | +13.3 | robust to top-3 removal |
| Rule-filtered stock LONG | fixed 2xATR (close) | 115 | 23 | 92 | +20.0 | +5.1 | +1.0 | 62 | +3.9 | +3.7 | +2.0 | +2.5 | +0.7 | +15.8 | +10.7 | robust to top-3 removal |
| Rule-filtered stock LONG | fixed 3xATR (close) | 115 | 12 | 103 | +10.4 | +5.5 | +1.1 | 63 | +4.1 | +4.1 | +2.3 | +2.7 | +0.9 | +17.9 | +15.8 | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 2xATR (close) | 115 | 49 | 66 | +42.6 | +4.3 | +0.6 | 59 | +3.4 | +2.9 | +1.6 | +2.0 | +0.7 | +12.4 | +14.8 | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 3xATR (close) | 115 | 31 | 84 | +27.0 | +4.5 | +0.4 | 57 | +3.4 | +3.1 | +1.6 | +2.0 | +0.5 | +16.0 | +22.3 | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 4xATR (close) | 115 | 19 | 96 | +16.5 | +5.3 | +0.6 | 60 | +4.0 | +3.9 | +2.2 | +2.6 | +0.8 | +17.7 | +25.0 | robust to top-3 removal |
| Rule-filtered stock LONG | fixed 2xATR (intraday) | 115 | 29 | 86 | +25.2 | +5.2 | +1.0 | 62 | +4.1 | +3.8 | +2.0 | +2.7 | +0.9 | +15.1 | +8.4 | robust to top-3 removal |
| Rule-filtered stock LONG | fixed 3xATR (intraday) | 115 | 14 | 101 | +12.2 | +5.5 | +1.1 | 63 | +4.2 | +4.1 | +2.4 | +2.8 | +1.0 | +17.4 | +12.3 | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 2xATR (intraday) | 115 | 60 | 55 | +52.2 | +3.6 | +0.4 | 53 | +2.9 | +2.2 | +1.4 | +1.5 | +0.7 | +10.8 | +12.3 | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 3xATR (intraday) | 115 | 36 | 79 | +31.3 | +4.3 | +0.4 | 57 | +3.2 | +2.8 | +1.5 | +1.8 | +0.5 | +14.5 | +19.2 | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 4xATR (intraday) | 115 | 21 | 94 | +18.3 | +5.5 | +0.6 | 60 | +4.3 | +4.1 | +2.3 | +2.8 | +1.1 | +17.4 | +22.4 | robust to top-3 removal |
| Perplexity stock LONG | hold, no stop | 59 | 0 | 59 | +0.0 | +5.8 | +1.7 | 59 | +5.0 | +3.1 | +0.5 | +2.2 | -0.4 | +23.7 | +nan | LUCK (edge gone w/o top tickers) |
| Perplexity stock LONG | trailing 8% (close) | 59 | 32 | 27 | +54.2 | +2.2 | -1.2 | 44 | +2.3 | -0.7 | -1.8 | -0.6 | -1.7 | +13.9 | +13.7 | LUCK (edge gone w/o top tickers) |
| Perplexity stock LONG | fixed 2xATR (close) | 59 | 16 | 43 | +27.1 | +6.0 | +0.6 | 53 | +5.6 | +3.2 | +0.7 | +2.8 | +0.2 | +18.8 | +8.8 | robust to top-3 removal |
| Perplexity stock LONG | fixed 3xATR (close) | 59 | 12 | 47 | +20.3 | +6.3 | +1.1 | 56 | +5.9 | +3.6 | +1.1 | +3.2 | +0.6 | +20.2 | +11.9 | robust to top-3 removal |
| Perplexity stock LONG | chandelier 2xATR (close) | 59 | 37 | 22 | +62.7 | +2.7 | -1.2 | 42 | +2.9 | -0.2 | -1.5 | +0.0 | -1.2 | +13.3 | +12.8 | LUCK (edge gone w/o top tickers) |
| Perplexity stock LONG | chandelier 3xATR (close) | 59 | 26 | 33 | +44.1 | +3.4 | -1.6 | 44 | +3.3 | +0.6 | -0.7 | +0.4 | -0.9 | +17.5 | +18.1 | LUCK (edge gone w/o top tickers) |
| Perplexity stock LONG | chandelier 4xATR (close) | 59 | 17 | 42 | +28.8 | +5.7 | +0.6 | 53 | +5.3 | +2.9 | +0.3 | +2.5 | -0.1 | +19.9 | +21.4 | LUCK (edge gone w/o top tickers) |
| Perplexity stock LONG | fixed 2xATR (intraday) | 59 | 19 | 40 | +32.2 | +6.2 | +0.6 | 53 | +5.9 | +3.4 | +0.9 | +3.1 | +0.6 | +18.0 | +7.2 | robust to top-3 removal |
| Perplexity stock LONG | fixed 3xATR (intraday) | 59 | 13 | 46 | +22.0 | +6.3 | +1.1 | 56 | +5.9 | +3.6 | +1.0 | +3.1 | +0.6 | +19.9 | +10.9 | robust to top-3 removal |
| Perplexity stock LONG | chandelier 2xATR (intraday) | 59 | 41 | 18 | +69.5 | +2.3 | -1.3 | 37 | +2.7 | -0.6 | -1.8 | -0.2 | -1.3 | +11.2 | +10.8 | LUCK (edge gone w/o top tickers) |
| Perplexity stock LONG | chandelier 3xATR (intraday) | 59 | 27 | 32 | +45.8 | +3.2 | -0.2 | 47 | +3.0 | +0.3 | -1.0 | +0.1 | -1.1 | +16.6 | +16.9 | LUCK (edge gone w/o top tickers) |
| Perplexity stock LONG | chandelier 4xATR (intraday) | 59 | 19 | 40 | +32.2 | +6.0 | +0.6 | 53 | +5.7 | +3.2 | +0.7 | +2.9 | +0.4 | +19.4 | +19.0 | robust to top-3 removal |
| Grok stock LONG | hold, no stop | 142 | 0 | 142 | +0.0 | +1.6 | +0.1 | 52 | -0.2 | +0.9 | +0.1 | -0.9 | -1.7 | +17.1 | +nan | no edge vs bench |
| Grok stock LONG | trailing 8% (close) | 142 | 60 | 82 | +42.3 | +1.1 | +0.2 | 52 | -0.0 | +0.8 | +0.1 | -0.4 | -1.0 | +10.8 | +9.9 | no edge vs bench |
| Grok stock LONG | fixed 2xATR (close) | 142 | 42 | 100 | +29.6 | +1.0 | -0.1 | 50 | -0.2 | +0.4 | -0.4 | -0.9 | -1.6 | +13.0 | +10.1 | no edge vs bench |
| Grok stock LONG | fixed 3xATR (close) | 142 | 20 | 122 | +14.1 | +1.9 | +0.1 | 52 | +0.4 | +1.3 | +0.5 | -0.3 | -1.1 | +15.5 | +11.8 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | chandelier 2xATR (close) | 142 | 60 | 82 | +42.3 | +1.8 | -0.2 | 49 | +0.5 | +1.1 | +0.4 | -0.1 | -0.8 | +11.4 | +11.0 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | chandelier 3xATR (close) | 142 | 34 | 108 | +23.9 | +2.3 | +0.3 | 53 | +0.8 | +1.6 | +0.9 | +0.1 | -0.6 | +14.5 | +16.4 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | chandelier 4xATR (close) | 142 | 20 | 122 | +14.1 | +1.9 | +0.2 | 53 | +0.3 | +1.2 | +0.5 | -0.3 | -1.1 | +15.4 | +19.1 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | fixed 2xATR (intraday) | 142 | 46 | 96 | +32.4 | +1.2 | -0.1 | 50 | +0.0 | +0.6 | -0.2 | -0.6 | -1.4 | +12.0 | +7.3 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | fixed 3xATR (intraday) | 142 | 22 | 120 | +15.5 | +2.0 | +0.1 | 52 | +0.5 | +1.4 | +0.6 | -0.2 | -0.9 | +15.2 | +10.0 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | chandelier 2xATR (intraday) | 142 | 77 | 65 | +54.2 | +1.1 | -1.2 | 43 | +0.1 | +0.7 | -0.0 | -0.3 | -0.9 | +9.9 | +9.7 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | chandelier 3xATR (intraday) | 142 | 40 | 102 | +28.2 | +2.3 | +0.0 | 51 | +0.9 | +1.7 | +0.9 | +0.2 | -0.5 | +13.5 | +13.6 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | chandelier 4xATR (intraday) | 142 | 24 | 118 | +16.9 | +2.0 | +0.3 | 53 | +0.5 | +1.4 | +0.6 | -0.2 | -0.9 | +15.1 | +16.9 | LUCK (edge gone w/o top tickers) |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | hold, no stop | 60 | 0 | 60 | +0.0 | +3.6 | +6.3 | 73 | +4.8 | +3.4 | +2.7 | +4.6 | +3.9 | +19.0 | +nan | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | trailing 8% (close) | 60 | 21 | 39 | +35.0 | +3.4 | +3.1 | 62 | +4.2 | +3.1 | +2.3 | +3.9 | +3.1 | +13.8 | +9.7 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | fixed 2xATR (close) | 60 | 7 | 53 | +11.7 | +4.2 | +6.3 | 72 | +5.2 | +4.0 | +3.3 | +5.0 | +4.3 | +17.6 | +17.1 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | fixed 3xATR (close) | 60 | 4 | 56 | +6.7 | +4.3 | +6.3 | 73 | +5.4 | +4.1 | +3.4 | +5.2 | +4.5 | +18.0 | +22.8 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | chandelier 2xATR (close) | 60 | 20 | 40 | +33.3 | +4.0 | +3.0 | 68 | +4.8 | +3.8 | +3.1 | +4.6 | +3.9 | +14.0 | +13.6 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | chandelier 3xATR (close) | 60 | 9 | 51 | +15.0 | +4.4 | +6.3 | 73 | +5.5 | +4.2 | +3.6 | +5.3 | +4.6 | +16.7 | +15.4 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | chandelier 4xATR (close) | 60 | 4 | 56 | +6.7 | +4.5 | +6.3 | 73 | +5.6 | +4.3 | +3.6 | +5.4 | +4.7 | +17.9 | +22.0 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | fixed 2xATR (intraday) | 60 | 10 | 50 | +16.7 | +4.0 | +6.3 | 72 | +5.0 | +3.8 | +3.1 | +4.8 | +4.1 | +16.2 | +12.1 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | fixed 3xATR (intraday) | 60 | 4 | 56 | +6.7 | +4.5 | +6.3 | 73 | +5.6 | +4.4 | +3.7 | +5.5 | +4.8 | +17.6 | +17.0 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | chandelier 2xATR (intraday) | 60 | 23 | 37 | +38.3 | +3.9 | +2.6 | 67 | +4.7 | +3.7 | +3.0 | +4.4 | +3.7 | +12.3 | +11.4 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | chandelier 3xATR (intraday) | 60 | 12 | 48 | +20.0 | +4.1 | +5.5 | 68 | +5.1 | +3.9 | +3.3 | +4.9 | +4.2 | +16.1 | +15.4 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | chandelier 4xATR (intraday) | 60 | 5 | 55 | +8.3 | +4.4 | +6.3 | 73 | +5.5 | +4.2 | +3.6 | +5.3 | +4.6 | +17.4 | +20.6 | robust to top-3 removal |
| All stock SHORT | hold, no stop | 189 | 0 | 189 | +0.0 | -1.0 | -1.2 | 44 | +0.5 | -1.3 | -1.6 | +0.2 | -0.1 | +16.2 | +nan | LUCK (edge gone w/o top tickers) |
| All stock SHORT | trailing 8% (close) | 189 | 70 | 119 | +37.0 | -0.7 | -2.0 | 39 | +0.3 | -0.9 | -1.2 | +0.0 | -0.3 | +10.9 | +8.4 | LUCK (edge gone w/o top tickers) |
| All stock SHORT | fixed 2xATR (close) | 189 | 54 | 135 | +28.6 | -0.5 | -1.8 | 43 | +0.8 | -0.7 | -1.0 | +0.5 | +0.2 | +13.2 | +8.2 | robust to top-3 removal |
| All stock SHORT | fixed 3xATR (close) | 189 | 33 | 156 | +17.5 | -0.7 | -1.2 | 44 | +0.6 | -1.0 | -1.3 | +0.3 | +0.1 | +14.7 | +12.9 | robust to top-3 removal |
| All stock SHORT | chandelier 2xATR (close) | 189 | 99 | 90 | +52.4 | -0.7 | -2.0 | 39 | +0.5 | -0.9 | -1.2 | +0.2 | -0.1 | +10.8 | +9.9 | LUCK (edge gone w/o top tickers) |
| All stock SHORT | chandelier 3xATR (close) | 189 | 46 | 143 | +24.3 | -0.6 | -1.6 | 44 | +0.7 | -0.8 | -1.1 | +0.4 | +0.1 | +13.7 | +14.3 | robust to top-3 removal |
| All stock SHORT | chandelier 4xATR (close) | 189 | 27 | 162 | +14.3 | -0.6 | -1.2 | 44 | +0.7 | -0.9 | -1.2 | +0.4 | +0.1 | +15.0 | +16.8 | robust to top-3 removal |
| All stock SHORT | fixed 2xATR (intraday) | 189 | 70 | 119 | +37.0 | -0.3 | -1.8 | 42 | +0.9 | -0.6 | -0.9 | +0.6 | +0.3 | +12.4 | +7.2 | robust to top-3 removal |
| All stock SHORT | fixed 3xATR (intraday) | 189 | 38 | 151 | +20.1 | -0.4 | -1.2 | 44 | +0.9 | -0.7 | -0.9 | +0.6 | +0.4 | +14.4 | +10.6 | robust to top-3 removal |
| All stock SHORT | chandelier 2xATR (intraday) | 189 | 115 | 74 | +60.8 | -0.7 | -1.8 | 38 | +0.3 | -0.9 | -1.2 | +0.0 | -0.3 | +9.5 | +8.1 | LUCK (edge gone w/o top tickers) |
| All stock SHORT | chandelier 3xATR (intraday) | 189 | 56 | 133 | +29.6 | -0.5 | -1.8 | 41 | +0.7 | -0.8 | -1.1 | +0.4 | +0.1 | +12.6 | +11.4 | robust to top-3 removal |
| All stock SHORT | chandelier 4xATR (intraday) | 189 | 36 | 153 | +19.0 | -0.5 | -1.3 | 45 | +0.8 | -0.8 | -1.1 | +0.5 | +0.2 | +14.5 | +16.1 | robust to top-3 removal |

