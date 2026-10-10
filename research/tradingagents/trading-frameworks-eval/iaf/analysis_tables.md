### A. IAF event engine vs independent pandas replay (longs, all setups incl. excluded rows)
| asset_run | policy | N | identical | mean_iaf | mean_sim | max_abs_diff |
|---|---|---|---|---|---|---|
| crypto | f8 | 301 | +100.0 | +28.3 | +28.3 | +0.0 |
| crypto | fsetup | 301 | +99.3 | +26.4 | +26.4 | +0.9 |
| crypto | hold | 301 | +100.0 | +38.4 | +38.4 | +0.0 |
| crypto | t12 | 301 | +100.0 | +24.2 | +24.2 | +0.0 |
| crypto | t5 | 301 | +100.0 | +10.5 | +10.5 | +0.0 |
| crypto | t8 | 301 | +100.0 | +17.4 | +17.4 | +0.0 |
| stock | f8 | 280 | +99.6 | +0.9 | +0.9 | +11.0 |
| stock | fsetup | 280 | +98.9 | +1.3 | +1.3 | +22.8 |
| stock | hold | 280 | +100.0 | +1.0 | +1.0 | +0.0 |
| stock | t12 | 280 | +100.0 | +1.0 | +1.0 | +0.0 |
| stock | t5 | 280 | +100.0 | +0.4 | +0.4 | +0.0 |
| stock | t8 | 280 | +100.0 | +0.5 | +0.5 | +0.0 |

### B. STOCK LONGS — ALL longs — IAF event engine, net of costs
| group | policy | N | mean | median | hit | x_spy | xmed_spy | mean_wo_top1 | mean_wo_top3 | x_spy_wo_top3 | flag |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Bot stock | hold, no stop | 30 | +2.3 | +0.3 | 53 | +1.0 | -1.0 | +1.3 | -0.3 | -1.6 | LUCK (edge gone w/o top tickers) |
| Bot stock | setup's own stop (fixed) | 30 | +1.9 | -0.2 | 50 | +1.1 | -1.0 | +0.9 | -0.7 | -1.5 | LUCK (edge gone w/o top tickers) |
| Bot stock | fixed 8% | 30 | +2.3 | +0.3 | 53 | +1.0 | -1.0 | +1.3 | -0.3 | -1.6 | LUCK (edge gone w/o top tickers) |
| Bot stock | trailing 5% | 30 | +1.7 | -0.8 | 47 | +0.7 | -1.9 | +0.6 | -1.0 | -2.0 | LUCK (edge gone w/o top tickers) |
| Bot stock | trailing 8% | 30 | +2.3 | +0.3 | 53 | +1.0 | -1.0 | +1.3 | -0.3 | -1.6 | LUCK (edge gone w/o top tickers) |
| Bot stock | trailing 12% | 30 | +2.3 | +0.3 | 53 | +1.0 | -1.0 | +1.3 | -0.3 | -1.6 | LUCK (edge gone w/o top tickers) |
| Grok stock | hold, no stop | 143 | +1.7 | +0.1 | 52 | -0.1 | -1.2 | +1.0 | +0.2 | -1.6 | no edge vs bench |
| Grok stock | setup's own stop (fixed) | 143 | +1.6 | +0.0 | 51 | +0.3 | -1.4 | +1.0 | +0.3 | -1.0 | LUCK (edge gone w/o top tickers) |
| Grok stock | fixed 8% | 143 | +1.1 | -0.2 | 49 | -0.1 | -2.0 | +0.4 | -0.3 | -1.5 | no edge vs bench |
| Grok stock | trailing 5% | 143 | +0.7 | -0.2 | 48 | -0.2 | -1.6 | +0.4 | -0.2 | -1.1 | no edge vs bench |
| Grok stock | trailing 8% | 143 | +1.2 | +0.3 | 52 | +0.0 | -1.2 | +0.8 | +0.2 | -0.9 | LUCK (edge gone w/o top tickers) |
| Grok stock | trailing 12% | 143 | +1.6 | +0.1 | 52 | +0.3 | -1.4 | +1.0 | +0.3 | -1.1 | LUCK (edge gone w/o top tickers) |
| Ilan charts stock | hold, no stop | 11 | +11.3 | +2.7 | 55 | +8.4 | -2.3 | +7.7 | -0.4 | -2.5 | LUCK (edge gone w/o top tickers) |
| Ilan charts stock | setup's own stop (fixed) | 11 | +11.3 | +2.7 | 55 | +8.4 | -2.3 | +7.7 | -0.4 | -2.5 | LUCK (edge gone w/o top tickers) |
| Ilan charts stock | fixed 8% | 11 | +4.0 | -8.7 | 45 | +2.4 | -7.2 | -0.2 | -7.5 | -8.4 | LUCK (edge gone w/o top tickers) |
| Ilan charts stock | trailing 5% | 11 | +3.1 | +1.5 | 73 | +1.7 | +1.9 | +1.4 | -0.9 | -2.2 | LUCK (edge gone w/o top tickers) |
| Ilan charts stock | trailing 8% | 11 | +2.3 | +0.8 | 64 | +1.2 | +1.9 | +1.0 | -1.2 | -2.1 | LUCK (edge gone w/o top tickers) |
| Ilan charts stock | trailing 12% | 11 | +3.5 | +0.8 | 55 | +2.0 | +1.9 | +0.4 | -3.5 | -4.5 | LUCK (edge gone w/o top tickers) |
| Perplexity stock | hold, no stop | 60 | +5.9 | +1.7 | 60 | +5.0 | +0.7 | +3.2 | +0.7 | -0.3 | LUCK (edge gone w/o top tickers) |
| Perplexity stock | setup's own stop (fixed) | 60 | +5.4 | +0.6 | 53 | +4.9 | -0.5 | +2.6 | +0.1 | -0.4 | LUCK (edge gone w/o top tickers) |
| Perplexity stock | fixed 8% | 60 | +4.4 | -0.2 | 48 | +4.2 | -2.0 | +1.6 | -1.1 | -1.3 | LUCK (edge gone w/o top tickers) |
| Perplexity stock | trailing 5% | 60 | +2.4 | -0.2 | 48 | +2.7 | -1.0 | -0.4 | -1.1 | -0.9 | LUCK (edge gone w/o top tickers) |
| Perplexity stock | trailing 8% | 60 | +2.1 | -1.2 | 43 | +2.2 | -0.6 | -0.8 | -1.9 | -1.8 | LUCK (edge gone w/o top tickers) |
| Perplexity stock | trailing 12% | 60 | +3.2 | -0.2 | 48 | +2.9 | -2.0 | +0.3 | -1.1 | -1.3 | LUCK (edge gone w/o top tickers) |

### B. STOCK LONGS — rule-filtered longs (no Grok prebreakout, sector ETF uptrend) — IAF event engine, net of costs
| group | policy | N | mean | median | hit | x_spy | xmed_spy | mean_wo_top1 | mean_wo_top3 | x_spy_wo_top3 | flag |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Bot stock | hold, no stop | 17 | +1.7 | +0.4 | 59 | +0.4 | -0.8 | +0.7 | -0.4 | -1.8 | LUCK (edge gone w/o top tickers) |
| Bot stock | setup's own stop (fixed) | 17 | +1.7 | +0.4 | 59 | +0.8 | -0.5 | +0.8 | -0.3 | -1.3 | LUCK (edge gone w/o top tickers) |
| Bot stock | fixed 8% | 17 | +1.7 | +0.4 | 59 | +0.4 | -0.8 | +0.7 | -0.4 | -1.8 | LUCK (edge gone w/o top tickers) |
| Bot stock | trailing 5% | 17 | +1.3 | +0.4 | 59 | +0.3 | -0.8 | +0.4 | -0.8 | -1.9 | LUCK (edge gone w/o top tickers) |
| Bot stock | trailing 8% | 17 | +1.7 | +0.4 | 59 | +0.4 | -0.8 | +0.7 | -0.4 | -1.8 | LUCK (edge gone w/o top tickers) |
| Bot stock | trailing 12% | 17 | +1.7 | +0.4 | 59 | +0.4 | -0.8 | +0.7 | -0.4 | -1.8 | LUCK (edge gone w/o top tickers) |
| Grok stock | hold, no stop | 58 | +3.6 | +1.1 | 66 | +1.7 | -0.3 | +2.0 | +0.6 | -1.4 | LUCK (edge gone w/o top tickers) |
| Grok stock | setup's own stop (fixed) | 58 | +3.9 | +1.1 | 66 | +2.4 | -0.3 | +2.3 | +0.9 | -0.6 | LUCK (edge gone w/o top tickers) |
| Grok stock | fixed 8% | 58 | +4.2 | +1.1 | 66 | +2.7 | -0.3 | +2.6 | +1.2 | -0.2 | LUCK (edge gone w/o top tickers) |
| Grok stock | trailing 5% | 58 | +3.0 | +1.0 | 60 | +1.9 | -0.4 | +2.3 | +1.3 | +0.2 | robust to top-3 removal |
| Grok stock | trailing 8% | 58 | +3.7 | +1.1 | 66 | +2.4 | -0.3 | +2.9 | +1.6 | +0.4 | robust to top-3 removal |
| Grok stock | trailing 12% | 58 | +4.6 | +1.1 | 66 | +3.1 | -0.3 | +2.9 | +1.3 | -0.1 | LUCK (edge gone w/o top tickers) |
| Ilan charts stock | hold, no stop | 4 | +12.3 | +4.6 | 75 | +7.3 | -0.1 | +1.1 | -5.8 | -11.4 | LUCK (edge gone w/o top tickers) |
| Ilan charts stock | setup's own stop (fixed) | 4 | +12.3 | +4.6 | 75 | +7.3 | -0.1 | +1.1 | -5.8 | -11.4 | LUCK (edge gone w/o top tickers) |
| Ilan charts stock | fixed 8% | 4 | +11.3 | +4.6 | 75 | +6.9 | -0.1 | -0.2 | -9.8 | -12.7 | LUCK (edge gone w/o top tickers) |
| Ilan charts stock | trailing 5% | 4 | +3.6 | +5.5 | 75 | +0.0 | +1.1 | +0.4 | -9.8 | -12.7 | LUCK (edge gone w/o top tickers) |
| Ilan charts stock | trailing 8% | 4 | +2.7 | +4.9 | 75 | -0.6 | +0.8 | +0.0 | -9.8 | -12.7 | no edge vs bench |
| Ilan charts stock | trailing 12% | 4 | +1.7 | +2.3 | 50 | -2.2 | -1.5 | -0.4 | -5.8 | -11.4 | no edge vs bench |
| Perplexity stock | hold, no stop | 36 | +8.1 | +1.8 | 58 | +7.4 | +1.6 | +3.5 | -0.8 | -1.5 | LUCK (edge gone w/o top tickers) |
| Perplexity stock | setup's own stop (fixed) | 36 | +8.9 | +1.8 | 58 | +8.5 | +1.6 | +4.4 | +0.2 | -0.2 | LUCK (edge gone w/o top tickers) |
| Perplexity stock | fixed 8% | 36 | +8.1 | +0.6 | 53 | +8.0 | -0.6 | +3.5 | -0.8 | -0.8 | LUCK (edge gone w/o top tickers) |
| Perplexity stock | trailing 5% | 36 | +5.6 | +0.6 | 56 | +6.0 | +0.6 | +0.9 | -0.1 | +0.2 | robust to top-3 removal |
| Perplexity stock | trailing 8% | 36 | +3.9 | -1.6 | 42 | +4.4 | -0.6 | -0.8 | -2.1 | -1.7 | LUCK (edge gone w/o top tickers) |
| Perplexity stock | trailing 12% | 36 | +4.9 | -3.4 | 42 | +4.8 | -2.7 | +0.2 | -1.5 | -1.5 | LUCK (edge gone w/o top tickers) |

### B. CRYPTO LONGS — ALL longs — IAF event engine, net of costs
| group | policy | N | mean | median | hit | x_btc | xmed_btc | mean_wo_top1 | mean_wo_top3 | x_btc_wo_top3 | flag |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Grok crypto | hold, no stop | 255 | +36.9 | +32.1 | 93 | +14.7 | +4.7 | +36.3 | +30.8 | +8.6 | robust to top-3 removal |
| Grok crypto | setup's own stop (fixed) | 255 | +25.6 | +25.1 | 70 | +9.7 | +0.8 | +23.7 | +19.6 | +5.0 | robust to top-3 removal |
| Grok crypto | fixed 8% | 255 | +28.2 | +28.7 | 78 | +10.1 | +2.8 | +26.1 | +21.9 | +4.9 | robust to top-3 removal |
| Grok crypto | trailing 5% | 255 | +11.0 | +6.1 | 58 | +2.4 | -0.4 | +9.3 | +8.3 | +0.0 | robust to top-3 removal |
| Grok crypto | trailing 8% | 255 | +18.2 | +22.9 | 76 | +3.6 | -0.4 | +17.1 | +15.9 | +0.8 | robust to top-3 removal |
| Grok crypto | trailing 12% | 255 | +25.3 | +26.8 | 82 | +8.3 | +2.4 | +22.2 | +18.8 | +2.7 | robust to top-3 removal |
| Perplexity crypto | hold, no stop | 9 | +46.1 | +49.7 | 100 | +14.4 | +18.1 | +44.1 | +33.7 | +2.0 | robust to top-3 removal |
| Perplexity crypto | setup's own stop (fixed) | 9 | +46.1 | +49.7 | 100 | +14.4 | +18.1 | +44.1 | +33.7 | +2.0 | robust to top-3 removal |
| Perplexity crypto | fixed 8% | 9 | +46.1 | +49.7 | 100 | +14.4 | +18.1 | +44.1 | +33.7 | +2.0 | robust to top-3 removal |
| Perplexity crypto | trailing 5% | 9 | +25.7 | +26.8 | 100 | +3.9 | +5.7 | +23.4 | +17.9 | -3.9 | LUCK (edge gone w/o top tickers) |
| Perplexity crypto | trailing 8% | 9 | +30.6 | +31.9 | 100 | +3.9 | +4.8 | +29.6 | +24.0 | -4.6 | LUCK (edge gone w/o top tickers) |
| Perplexity crypto | trailing 12% | 9 | +41.4 | +36.1 | 100 | +12.1 | +7.9 | +38.0 | +33.7 | +2.0 | robust to top-3 removal |

### B. CRYPTO LONGS — rule-filtered longs (no Grok prebreakout) — IAF event engine, net of costs
| group | policy | N | mean | median | hit | x_btc | xmed_btc | mean_wo_top1 | mean_wo_top3 | x_btc_wo_top3 | flag |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Grok crypto | hold, no stop | 255 | +36.9 | +32.1 | 93 | +14.7 | +4.7 | +36.3 | +30.8 | +8.6 | robust to top-3 removal |
| Grok crypto | setup's own stop (fixed) | 255 | +25.6 | +25.1 | 70 | +9.7 | +0.8 | +23.7 | +19.6 | +5.0 | robust to top-3 removal |
| Grok crypto | fixed 8% | 255 | +28.2 | +28.7 | 78 | +10.1 | +2.8 | +26.1 | +21.9 | +4.9 | robust to top-3 removal |
| Grok crypto | trailing 5% | 255 | +11.0 | +6.1 | 58 | +2.4 | -0.4 | +9.3 | +8.3 | +0.0 | robust to top-3 removal |
| Grok crypto | trailing 8% | 255 | +18.2 | +22.9 | 76 | +3.6 | -0.4 | +17.1 | +15.9 | +0.8 | robust to top-3 removal |
| Grok crypto | trailing 12% | 255 | +25.3 | +26.8 | 82 | +8.3 | +2.4 | +22.2 | +18.8 | +2.7 | robust to top-3 removal |
| Perplexity crypto | hold, no stop | 9 | +46.1 | +49.7 | 100 | +14.4 | +18.1 | +44.1 | +33.7 | +2.0 | robust to top-3 removal |
| Perplexity crypto | setup's own stop (fixed) | 9 | +46.1 | +49.7 | 100 | +14.4 | +18.1 | +44.1 | +33.7 | +2.0 | robust to top-3 removal |
| Perplexity crypto | fixed 8% | 9 | +46.1 | +49.7 | 100 | +14.4 | +18.1 | +44.1 | +33.7 | +2.0 | robust to top-3 removal |
| Perplexity crypto | trailing 5% | 9 | +25.7 | +26.8 | 100 | +3.9 | +5.7 | +23.4 | +17.9 | -3.9 | LUCK (edge gone w/o top tickers) |
| Perplexity crypto | trailing 8% | 9 | +30.6 | +31.9 | 100 | +3.9 | +4.8 | +29.6 | +24.0 | -4.6 | LUCK (edge gone w/o top tickers) |
| Perplexity crypto | trailing 12% | 9 | +41.4 | +36.1 | 100 | +12.1 | +7.9 | +38.0 | +33.7 | +2.0 | robust to top-3 removal |

### C1. STOCKS vs SPY / sector ETF — policy: hold, no stop (same entry->exit window; shorts: excess = ret + bench ret)
| group | dir | N | tickers | mean | median | hit | x_spy | xmed_spy | x_sector | mean_wo_top1 | mean_wo_top3 | x_spy_wo_top1 | x_spy_wo_top3 | top1 | flag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Bot | LONG | 30 | 24 | +2.3 | +0.3 | 53 | +1.0 | -1.0 | +1.4 | +1.3 | -0.3 | -0.0 | -1.6 | AMD(1) | LUCK (edge gone w/o top tickers) |
| Bot | SHORT | 19 | 15 | +0.0 | +0.8 | 58 | +1.3 | +1.9 | +1.7 | -0.6 | -1.4 | +0.6 | -0.1 | CRM(1) | LUCK (edge gone w/o top tickers) |
| Grok momentum | LONG | 40 | 30 | +4.6 | +4.5 | 70 | +3.1 | +2.9 | +0.3 | +3.4 | +1.5 | +1.9 | +0.0 | ALAB(4) | robust to top-3 removal |
| Grok momentum | SHORT | 25 | 18 | -4.4 | -3.3 | 40 | -2.8 | -2.1 | -1.1 | -5.2 | -6.8 | -3.6 | -5.2 | IREN(1) | no edge vs bench |
| Grok near-low | LONG | 14 | 12 | +0.4 | -1.8 | 43 | -1.2 | -3.8 | +0.8 | -4.2 | -8.9 | -5.8 | -10.5 | RXRX(3) | no edge vs bench |
| Grok near-low | SHORT | 12 | 12 | +5.0 | +6.7 | 75 | +6.4 | +8.5 | +5.7 | +4.1 | +2.1 | +5.5 | +3.4 | RH(1) | robust to top-3 removal |
| Grok portfolio-news | LONG | 12 | 9 | +0.3 | +0.3 | 50 | -0.9 | -1.0 | -0.2 | -0.2 | -1.1 | -1.4 | -2.3 | TSLA(1) | no edge vs bench |
| Grok portfolio-news | SHORT | 21 | 11 | -2.5 | -2.8 | 29 | -1.3 | -1.6 | -0.4 | -3.1 | -4.5 | -1.9 | -3.4 | COIN(1) | no edge vs bench |
| Grok prebreakout | LONG | 42 | 31 | -3.3 | -3.2 | 33 | -4.9 | -4.6 | -1.9 | -3.8 | -4.7 | -5.4 | -6.3 | PBR(1) | no edge vs bench |
| Grok prebreakout | SHORT | 27 | 23 | +5.7 | +6.5 | 70 | +7.1 | +8.5 | +5.1 | +4.9 | +4.0 | +6.4 | +5.5 | WHR(1) | robust to top-3 removal |
| Grok x-trends | LONG | 19 | 8 | +3.1 | +0.4 | 74 | +1.4 | -1.2 | -0.7 | +0.7 | -0.4 | -1.1 | -2.2 | AMD(4) | LUCK (edge gone w/o top tickers) |
| Grok x-trends | SHORT | 34 | 6 | -5.2 | -5.2 | 12 | -3.3 | -2.8 | -3.6 | -5.8 | -6.9 | -4.0 | -5.1 | SPY(6) | no edge vs bench |
| Ilan charts | LONG | 11 | 11 | +11.3 | +2.7 | 55 | +8.4 | -2.3 | +5.6 | +7.7 | -0.4 | +5.0 | -2.5 | SMCI(1) | LUCK (edge gone w/o top tickers) |
| Original sheet (Grok/Pplx) | LONG | 17 | 17 | +8.0 | -4.1 | 47 | +4.3 | -4.5 | +4.4 | +2.5 | -3.1 | -1.4 | -7.0 | IOVA(1) | LUCK (edge gone w/o top tickers) |
| Original sheet (Grok/Pplx) | SHORT | 10 | 10 | -4.0 | +0.7 | 50 | -1.0 | +3.4 | -3.8 | -10.1 | -17.7 | -7.3 | -14.9 | LCID(1) | no edge vs bench |
| Perplexity | LONG | 59 | 42 | +5.8 | +1.7 | 59 | +5.0 | +0.6 | +6.2 | +3.1 | +0.5 | +2.2 | -0.4 | XP(2) | LUCK (edge gone w/o top tickers) |
| Perplexity | SHORT | 41 | 31 | -0.7 | -0.7 | 49 | +0.3 | +1.6 | +0.3 | -1.3 | -2.3 | -0.3 | -1.3 | HE(1) | LUCK (edge gone w/o top tickers) |

### C2. CRYPTO vs BTC / ETH / 50-50 basket — policy: hold, no stop
| group | dir | N | tickers | mean | median | hit | x_btc | xmed_btc | x_eth | x_basket | xmed_basket | mean_wo_top1 | mean_wo_top3 | x_btc_wo_top1 | x_btc_wo_top3 | top3 | flag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Grok crypto | LONG | 255 | 19 | +36.9 | +32.1 | 93 | +14.7 | +4.7 | +11.8 | +13.3 | +2.7 | +36.3 | +30.8 | +14.0 | +8.6 | SOL-USD(46),ZEC-USD(5),NEAR-USD(5) | robust to top-3 removal |
| Grok crypto | SHORT | 120 | 30 | -22.6 | -10.9 | 28 | -9.1 | -0.4 | -9.0 | -9.1 | -2.3 | -24.6 | -27.8 | -11.3 | -14.6 | DEXE-USD(2),BEAT38837-USD(1),DOGE-USD(13) | no edge vs bench |
| Perplexity | LONG | 9 | 5 | +46.1 | +49.7 | 100 | +14.4 | +18.1 | +9.3 | +11.9 | +15.6 | +44.1 | +33.7 | +12.4 | +2.0 | SOL-USD(2),LINK-USD(2),AVAX-USD(1) | robust to top-3 removal |
| Perplexity | SHORT | 2 | 2 | -111.0 | -111.0 | 0 | -79.3 | -79.3 | -74.4 | -76.9 | -76.9 | -166.6 | +nan | -135.0 | +nan | HYPE32196-USD(1),ZEC-USD(1) | no edge vs bench |

### C1. STOCKS vs SPY / sector ETF — policy: trailing 8% (same entry->exit window; shorts: excess = ret + bench ret)
| group | dir | N | tickers | mean | median | hit | x_spy | xmed_spy | x_sector | mean_wo_top1 | mean_wo_top3 | x_spy_wo_top1 | x_spy_wo_top3 | top1 | flag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Bot | LONG | 30 | 24 | +2.3 | +0.3 | 53 | +1.0 | -1.0 | +1.4 | +1.3 | -0.3 | -0.0 | -1.6 | AMD(1) | LUCK (edge gone w/o top tickers) |
| Bot | SHORT | 19 | 15 | -0.2 | +0.2 | 53 | +0.9 | +1.8 | +1.2 | -0.9 | -1.7 | +0.3 | -0.6 | CRM(1) | LUCK (edge gone w/o top tickers) |
| Grok momentum | LONG | 40 | 30 | +3.3 | +4.1 | 68 | +2.3 | +2.6 | +0.3 | +2.3 | +1.1 | +1.4 | +0.2 | HPE(2) | robust to top-3 removal |
| Grok momentum | SHORT | 25 | 18 | -3.6 | -4.6 | 28 | -3.2 | -3.3 | -2.2 | -4.2 | -4.7 | -3.8 | -4.3 | MGM(1) | no edge vs bench |
| Grok near-low | LONG | 14 | 12 | +1.6 | -1.0 | 43 | +0.5 | -3.4 | +1.4 | -1.1 | -5.1 | -2.1 | -5.9 | RXRX(3) | LUCK (edge gone w/o top tickers) |
| Grok near-low | SHORT | 12 | 12 | +0.2 | +0.3 | 50 | +0.9 | +1.4 | +0.1 | -1.2 | -4.2 | -0.6 | -3.5 | RH(1) | LUCK (edge gone w/o top tickers) |
| Grok portfolio-news | LONG | 12 | 9 | +0.3 | +0.3 | 50 | -0.9 | -1.0 | -0.2 | -0.2 | -1.1 | -1.4 | -2.3 | TSLA(1) | no edge vs bench |
| Grok portfolio-news | SHORT | 21 | 11 | -1.3 | -2.8 | 33 | -0.3 | -1.6 | +0.5 | -1.9 | -3.1 | -0.8 | -2.1 | COIN(1) | no edge vs bench |
| Grok prebreakout | LONG | 42 | 31 | -2.7 | -3.2 | 31 | -3.9 | -4.5 | -1.2 | -3.2 | -4.0 | -4.4 | -5.2 | PBR(1) | no edge vs bench |
| Grok prebreakout | SHORT | 27 | 23 | +4.6 | +6.4 | 67 | +5.9 | +8.4 | +4.0 | +3.8 | +2.7 | +5.1 | +4.0 | WHR(1) | robust to top-3 removal |
| Grok x-trends | LONG | 19 | 8 | +3.1 | +0.4 | 74 | +1.4 | -1.2 | -0.7 | +0.7 | -0.4 | -1.1 | -2.2 | AMD(4) | LUCK (edge gone w/o top tickers) |
| Grok x-trends | SHORT | 34 | 6 | -4.5 | -5.2 | 12 | -2.9 | -2.8 | -3.0 | -5.1 | -5.9 | -3.5 | -4.6 | SPY(6) | no edge vs bench |
| Ilan charts | LONG | 11 | 11 | +2.3 | +0.8 | 64 | +1.2 | +1.9 | +1.5 | +1.0 | -1.2 | +0.1 | -2.1 | AI(1) | LUCK (edge gone w/o top tickers) |
| Original sheet (Grok/Pplx) | LONG | 17 | 17 | +3.4 | +0.8 | 53 | +2.8 | +1.2 | +2.3 | +0.5 | -2.2 | +0.1 | -2.5 | WGS(1) | LUCK (edge gone w/o top tickers) |
| Original sheet (Grok/Pplx) | SHORT | 10 | 10 | +2.9 | +1.5 | 50 | +4.2 | +3.1 | +3.3 | -2.4 | -4.3 | -1.5 | -3.6 | LCID(1) | LUCK (edge gone w/o top tickers) |
| Perplexity | LONG | 59 | 42 | +2.2 | -1.2 | 44 | +2.3 | -0.5 | +3.7 | -0.7 | -1.8 | -0.6 | -1.7 | XP(2) | LUCK (edge gone w/o top tickers) |
| Perplexity | SHORT | 41 | 31 | -0.2 | -2.5 | 41 | +0.4 | -1.0 | -0.7 | -0.8 | -1.7 | -0.2 | -1.1 | HE(1) | LUCK (edge gone w/o top tickers) |

### C2. CRYPTO vs BTC / ETH / 50-50 basket — policy: trailing 8%
| group | dir | N | tickers | mean | median | hit | x_btc | xmed_btc | x_eth | x_basket | xmed_basket | mean_wo_top1 | mean_wo_top3 | x_btc_wo_top1 | x_btc_wo_top3 | top3 | flag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Grok crypto | LONG | 255 | 19 | +18.2 | +22.9 | 76 | +3.6 | -0.4 | +0.7 | +2.2 | +1.1 | +17.1 | +15.9 | +2.5 | +0.8 | SOL-USD(46),HYPE32196-USD(15),LINK-USD(23) | robust to top-3 removal |
| Grok crypto | SHORT | 120 | 30 | -2.1 | -3.9 | 35 | +1.3 | -0.4 | +2.2 | +1.7 | -0.2 | -3.6 | -4.4 | -0.2 | -1.0 | DEXE-USD(2),BEAT38837-USD(1),XRP-USD(5) | LUCK (edge gone w/o top tickers) |
| Perplexity | LONG | 9 | 5 | +30.6 | +31.9 | 100 | +3.9 | +4.8 | -2.2 | +0.9 | +2.1 | +29.6 | +24.0 | +2.0 | -4.6 | LINK-USD(2),SOL-USD(2),ETH-USD(2) | LUCK (edge gone w/o top tickers) |
| Perplexity | SHORT | 2 | 2 | -18.7 | -18.7 | 0 | -9.4 | -9.4 | +0.8 | -4.3 | -4.3 | -21.8 | +nan | -12.6 | +nan | ZEC-USD(1),HYPE32196-USD(1) | no edge vs bench |

### D. Named leave-one-ticker-out checks (excess = vs SPY for stocks, vs BTC for crypto)
| check | policy | sample | N | mean | median | hit | excess_vs_mkt | excess_median |
|---|---|---|---|---|---|---|---|---|
| Grok crypto longs w/o NEAR | hold, no stop | with NEAR-USD | 255 | +36.9 | +32.1 | 93 | +14.7 | +4.7 |
| Grok crypto longs w/o NEAR | hold, no stop | without NEAR-USD | 250 | +34.9 | +32.0 | 92 | +12.7 | +4.6 |
| Grok crypto longs w/o NEAR | trailing 8% | with NEAR-USD | 255 | +18.2 | +22.9 | 76 | +3.6 | -0.4 |
| Grok crypto longs w/o NEAR | trailing 8% | without NEAR-USD | 250 | +18.1 | +24.6 | 77 | +3.4 | -0.4 |
| Perplexity (all, longs) w/o XP | hold, no stop | with XP | 68 | +11.2 | +1.8 | 65 | +6.3 | +0.9 |
| Perplexity (all, longs) w/o XP | hold, no stop | without XP | 66 | +8.9 | +1.8 | 64 | +3.9 | +0.7 |
| Perplexity (all, longs) w/o XP | trailing 8% | with XP | 68 | +6.0 | +0.3 | 51 | +2.5 | -0.5 |
| Perplexity (all, longs) w/o XP | trailing 8% | without XP | 66 | +3.6 | -0.1 | 50 | +0.0 | -0.5 |
| Original sheet longs w/o IOVA | hold, no stop | with IOVA | 17 | +8.0 | -4.1 | 47 | +4.3 | -4.5 |
| Original sheet longs w/o IOVA | hold, no stop | without IOVA | 16 | +2.5 | -4.2 | 44 | -1.4 | -4.7 |
| Original sheet longs w/o IOVA | trailing 8% | with IOVA | 17 | +3.4 | +0.8 | 53 | +2.8 | +1.2 |
| Original sheet longs w/o IOVA | trailing 8% | without IOVA | 16 | +2.2 | -1.6 | 50 | +1.5 | -1.0 |

### E. SHORTS (independent replay; IAF v8 cannot short) — excess vs SPY/BTC means short beat shorting the market
| src | asset | subset | policy | N | mean | median | hit | x_spy | x_btc | mean_wo_top1 | x_spy_wo_top1 | x_spy_wo_top3 | flag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Bot | stock | all shorts | hold, no stop | 19 | +0.0 | +0.8 | 58 | +1.3 | +nan | -0.6 | +0.6 | -0.1 | LUCK (edge gone w/o top tickers) |
| Bot | stock | score>=3 & <SMA200 | hold, no stop | 7 | +0.5 | +0.8 | 71 | +1.7 | +nan | +0.2 | +1.4 | +0.2 | robust to top-3 removal |
| Grok | crypto | all shorts | hold, no stop | 120 | -22.6 | -10.9 | 28 | +nan | -9.1 | -24.6 | +nan | +nan | no edge vs bench |
| Grok | stock | all shorts | hold, no stop | 129 | -1.3 | -1.8 | 41 | +0.4 | +nan | -1.7 | -0.0 | -0.5 | LUCK (edge gone w/o top tickers) |
| Grok | stock | score>=3 & <SMA200 | hold, no stop | 33 | +5.3 | +7.3 | 76 | +6.9 | +nan | +4.7 | +6.3 | +5.6 | robust to top-3 removal |
| Perplexity | crypto | all shorts | hold, no stop | 2 | -111.0 | -111.0 | 0 | +nan | -79.3 | -166.6 | +nan | +nan | no edge vs bench |
| Perplexity | stock | all shorts | hold, no stop | 41 | -0.7 | -0.7 | 49 | +0.3 | +nan | -1.3 | -0.3 | -1.3 | LUCK (edge gone w/o top tickers) |
| Perplexity | stock | score>=3 & <SMA200 | hold, no stop | 20 | +1.8 | +6.6 | 70 | +2.4 | +nan | +0.6 | +1.2 | -0.7 | LUCK (edge gone w/o top tickers) |
| Bot | stock | all shorts | setup's own stop (fixed) | 19 | -0.9 | -0.9 | 47 | +0.2 | +nan | -1.6 | -0.5 | -1.6 | LUCK (edge gone w/o top tickers) |
| Bot | stock | score>=3 & <SMA200 | setup's own stop (fixed) | 7 | +0.5 | +0.8 | 71 | +1.7 | +nan | +0.2 | +1.4 | +0.2 | robust to top-3 removal |
| Grok | crypto | all shorts | setup's own stop (fixed) | 120 | -10.7 | -10.0 | 20 | +nan | -2.8 | -12.5 | +nan | +nan | no edge vs bench |
| Grok | stock | all shorts | setup's own stop (fixed) | 129 | -0.9 | -2.5 | 36 | +0.3 | +nan | -1.4 | -0.1 | -0.6 | LUCK (edge gone w/o top tickers) |
| Grok | stock | score>=3 & <SMA200 | setup's own stop (fixed) | 33 | +5.1 | +7.3 | 73 | +6.5 | +nan | +4.5 | +5.9 | +5.1 | robust to top-3 removal |
| Perplexity | crypto | all shorts | setup's own stop (fixed) | 2 | -85.2 | -85.2 | 0 | +nan | -68.5 | -166.6 | +nan | +nan | no edge vs bench |
| Perplexity | stock | all shorts | setup's own stop (fixed) | 41 | -0.5 | -0.7 | 49 | +0.3 | +nan | -1.1 | -0.3 | -1.3 | LUCK (edge gone w/o top tickers) |
| Perplexity | stock | score>=3 & <SMA200 | setup's own stop (fixed) | 20 | +2.0 | +6.6 | 70 | +2.6 | +nan | +0.8 | +1.4 | -0.5 | LUCK (edge gone w/o top tickers) |
| Bot | stock | all shorts | trailing 8% | 19 | -0.2 | +0.2 | 53 | +0.9 | +nan | -0.9 | +0.3 | -0.6 | LUCK (edge gone w/o top tickers) |
| Bot | stock | score>=3 & <SMA200 | trailing 8% | 7 | +0.5 | +0.8 | 71 | +1.7 | +nan | +0.2 | +1.4 | +0.2 | robust to top-3 removal |
| Grok | crypto | all shorts | trailing 8% | 120 | -2.1 | -3.9 | 35 | +nan | +1.3 | -3.6 | +nan | +nan | LUCK (edge gone w/o top tickers) |
| Grok | stock | all shorts | trailing 8% | 129 | -0.9 | -2.5 | 36 | +0.2 | +nan | -1.3 | -0.2 | -0.6 | LUCK (edge gone w/o top tickers) |
| Grok | stock | score>=3 & <SMA200 | trailing 8% | 33 | +4.1 | +6.3 | 64 | +5.3 | +nan | +3.5 | +4.6 | +3.7 | robust to top-3 removal |
| Perplexity | crypto | all shorts | trailing 8% | 2 | -18.7 | -18.7 | 0 | +nan | -9.4 | -21.8 | +nan | +nan | no edge vs bench |
| Perplexity | stock | all shorts | trailing 8% | 41 | -0.2 | -2.5 | 41 | +0.4 | +nan | -0.8 | -0.2 | -1.1 | LUCK (edge gone w/o top tickers) |
| Perplexity | stock | score>=3 & <SMA200 | trailing 8% | 20 | +3.2 | +4.5 | 55 | +3.3 | +nan | +2.1 | +2.2 | +0.5 | robust to top-3 removal |

### F. Same setups as the team's hold-no-stop CSV (longs flagged in_hold_no_stop_csv), our PIT entry
| src | asset | N | mean | median | hit | x_spy | x_btc | mean_wo_top1 | mean_wo_top3 | x_spy_wo_top3 | x_btc_wo_top3 | top3 | flag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Bot | stock | 25 | +1.6 | +0.1 | 52 | +0.4 | +nan | +0.6 | -0.6 | -1.9 | +nan | PANW(3),META(2),VLO(1) | LUCK (edge gone w/o top tickers) |
| Grok | crypto | 240 | +38.0 | +32.6 | 93 | +nan | +15.4 | +37.6 | +31.6 | +nan | +9.1 | SOL-USD(46),ZEC-USD(5),NEAR-USD(4) | robust to top-3 removal |
| Grok | stock | 139 | +1.2 | +0.1 | 52 | -0.6 | +nan | +0.5 | -0.3 | -2.1 | +nan | IOVA(1),RXRX(3),AMD(4) | no edge vs bench |
| Perplexity | crypto | 8 | +47.4 | +51.2 | 100 | +nan | +15.7 | +45.4 | +32.9 | +nan | +1.3 | SOL-USD(2),LINK-USD(2),AVAX-USD(1) | robust to top-3 removal |
| Perplexity | stock | 53 | +6.7 | +1.7 | 58 | +5.9 | +nan | +3.6 | +0.8 | -0.1 | +nan | XP(2),INTR(3),STNE(2) | LUCK (edge gone w/o top tickers) |

### G. Grok crypto LONGS vs BTC / ETH / basket — full period vs team fair window, all exit policies
| window | policy | sample | N | tickers | mean | median | hit | x_btc | xmed_btc | x_eth | xmed_eth | x_basket | xmed_basket | x_btc_wo_top1 | x_btc_wo_top3 | top3 | flag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| full period | hold, no stop | all | 255 | 19 | +36.9 | +32.1 | 93 | +14.7 | +4.7 | +11.8 | +3.3 | +13.3 | +2.7 | +14.0 | +8.6 | SOL-USD(46),ZEC-USD(5),NEAR-USD(5) | robust to top-3 removal |
| full period | hold, no stop | w/o NEAR | 250 | 18 | +34.9 | +32.0 | 92 | +12.7 | +4.6 | +9.7 | +2.7 | +11.2 | +2.4 | +11.5 | +6.4 | SOL-USD(46),ZEC-USD(5),UNI7083-USD(8) | robust to top-3 removal |
| full period | setup's own stop (fixed) | all | 255 | 19 | +25.6 | +25.1 | 70 | +9.6 | +0.8 | +7.7 | -0.4 | +8.7 | +1.6 | +8.3 | +5.0 | SOL-USD(46),NEAR-USD(5),LINK-USD(23) | robust to top-3 removal |
| full period | setup's own stop (fixed) | w/o NEAR | 250 | 18 | +24.0 | +24.7 | 70 | +8.0 | +0.4 | +6.1 | -0.4 | +7.1 | +1.5 | +6.3 | +3.7 | SOL-USD(46),LINK-USD(23),ZEC-USD(5) | robust to top-3 removal |
| full period | fixed 8% | all | 255 | 19 | +28.2 | +28.7 | 78 | +10.1 | +2.8 | +7.8 | -0.4 | +8.9 | +1.9 | +8.4 | +4.9 | SOL-USD(46),ZEC-USD(5),LINK-USD(23) | robust to top-3 removal |
| full period | fixed 8% | w/o NEAR | 250 | 18 | +27.5 | +28.8 | 78 | +9.1 | +2.8 | +6.8 | -0.4 | +8.0 | +1.9 | +7.3 | +3.4 | SOL-USD(46),ZEC-USD(5),LINK-USD(23) | robust to top-3 removal |
| full period | trailing 5% | all | 255 | 19 | +11.0 | +6.1 | 58 | +2.4 | -0.4 | -0.3 | -0.5 | +1.1 | -1.0 | +1.3 | +0.0 | SOL-USD(46),ETH-USD(44),UNI7083-USD(8) | robust to top-3 removal |
| full period | trailing 5% | w/o NEAR | 250 | 18 | +11.1 | +6.1 | 59 | +2.5 | -0.4 | -0.2 | -0.5 | +1.2 | -1.0 | +1.4 | +0.1 | SOL-USD(46),ETH-USD(44),UNI7083-USD(8) | robust to top-3 removal |
| full period | trailing 8% | all | 255 | 19 | +18.2 | +22.9 | 76 | +3.6 | -0.4 | +0.7 | -0.5 | +2.2 | +1.1 | +2.5 | +0.8 | SOL-USD(46),HYPE32196-USD(15),LINK-USD(23) | robust to top-3 removal |
| full period | trailing 8% | w/o NEAR | 250 | 18 | +18.1 | +24.6 | 77 | +3.4 | -0.4 | +0.5 | -0.5 | +1.9 | +1.1 | +2.2 | +0.4 | SOL-USD(46),HYPE32196-USD(15),LINK-USD(23) | robust to top-3 removal |
| full period | trailing 12% | all | 255 | 19 | +25.3 | +26.8 | 82 | +8.3 | +2.4 | +4.9 | -0.4 | +6.6 | +1.6 | +6.1 | +2.7 | SOL-USD(46),NEAR-USD(5),ZEC-USD(5) | robust to top-3 removal |
| full period | trailing 12% | w/o NEAR | 250 | 18 | +24.1 | +26.7 | 82 | +7.0 | +2.2 | +3.6 | -0.4 | +5.3 | +1.6 | +4.4 | +1.8 | SOL-USD(46),ZEC-USD(5),AVAX-USD(6) | robust to top-3 removal |
| fair window 08-12..10-04 | hold, no stop | all | 117 | 15 | +21.9 | +14.2 | 84 | +8.8 | +1.1 | +9.9 | +3.8 | +9.3 | +2.1 | +6.4 | +4.1 | NEAR-USD(3),SOL-USD(22),UNI7083-USD(3) | robust to top-3 removal |
| fair window 08-12..10-04 | hold, no stop | w/o NEAR | 114 | 14 | +19.4 | +14.1 | 83 | +6.4 | +0.4 | +7.5 | +3.5 | +6.9 | +2.0 | +5.5 | +3.0 | SOL-USD(22),UNI7083-USD(3),AAVE-USD(4) | robust to top-3 removal |
| fair window 08-12..10-04 | setup's own stop (fixed) | all | 117 | 15 | +20.2 | +13.9 | 77 | +7.8 | -0.4 | +8.7 | +2.8 | +8.3 | +1.9 | +5.4 | +3.0 | NEAR-USD(3),SOL-USD(22),UNI7083-USD(3) | robust to top-3 removal |
| fair window 08-12..10-04 | setup's own stop (fixed) | w/o NEAR | 114 | 14 | +17.8 | +10.9 | 76 | +5.4 | -0.4 | +6.3 | +2.7 | +5.8 | +1.7 | +4.5 | +2.3 | SOL-USD(22),UNI7083-USD(3),LINK-USD(13) | robust to top-3 removal |
| fair window 08-12..10-04 | fixed 8% | all | 117 | 15 | +20.2 | +13.9 | 78 | +7.7 | -0.4 | +8.6 | +3.3 | +8.1 | +1.9 | +5.2 | +2.7 | NEAR-USD(3),SOL-USD(22),UNI7083-USD(3) | robust to top-3 removal |
| fair window 08-12..10-04 | fixed 8% | w/o NEAR | 114 | 14 | +17.8 | +11.3 | 77 | +5.2 | -0.4 | +6.2 | +2.7 | +5.7 | +1.7 | +4.2 | +2.0 | SOL-USD(22),UNI7083-USD(3),LINK-USD(13) | robust to top-3 removal |
| fair window 08-12..10-04 | trailing 5% | all | 117 | 15 | +9.3 | +5.4 | 63 | +1.9 | -0.4 | +1.2 | -0.4 | +1.5 | +0.0 | +0.8 | -0.4 | UNI7083-USD(3),SOL-USD(22),HYPE32196-USD(5) | LUCK (edge gone w/o top tickers) |
| fair window 08-12..10-04 | trailing 5% | w/o NEAR | 114 | 14 | +9.3 | +5.3 | 63 | +1.9 | -0.4 | +1.2 | -0.4 | +1.6 | +0.0 | +0.8 | -0.4 | UNI7083-USD(3),SOL-USD(22),HYPE32196-USD(5) | LUCK (edge gone w/o top tickers) |
| fair window 08-12..10-04 | trailing 8% | all | 117 | 15 | +12.3 | +7.7 | 74 | +2.2 | -0.4 | +2.3 | -0.4 | +2.3 | +0.5 | +1.4 | -0.3 | UNI7083-USD(3),SOL-USD(22),NEAR-USD(3) | LUCK (edge gone w/o top tickers) |
| fair window 08-12..10-04 | trailing 8% | w/o NEAR | 114 | 14 | +11.5 | +6.9 | 74 | +1.5 | -0.4 | +1.6 | -0.4 | +1.5 | +0.4 | +0.6 | -0.9 | UNI7083-USD(3),SOL-USD(22),LINK-USD(13) | LUCK (edge gone w/o top tickers) |
| fair window 08-12..10-04 | trailing 12% | all | 117 | 15 | +16.5 | +8.7 | 77 | +5.3 | -0.4 | +5.6 | +0.6 | +5.5 | +1.1 | +3.2 | +0.6 | NEAR-USD(3),SOL-USD(22),UNI7083-USD(3) | robust to top-3 removal |
| fair window 08-12..10-04 | trailing 12% | w/o NEAR | 114 | 14 | +14.3 | +8.4 | 76 | +3.2 | -0.4 | +3.6 | +0.1 | +3.4 | +1.1 | +1.6 | -0.3 | SOL-USD(22),UNI7083-USD(3),AVAX-USD(3) | LUCK (edge gone w/o top tickers) |

### H. Whole scanner: unfiltered vs rule-filtered (rules: longs no Grok prebreakout + stock sector uptrend; shorts only stocks with score>=3 & <SMA200; no crypto shorts)
| asset | policy | subset | N | tickers | mean | median | hit | x_spy | x_btc | mean_wo_top1 | mean_wo_top3 | flag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| stock | hold, no stop | unfiltered L+S | 433 | 210 | +1.4 | +0.0 | 50 | +1.1 | +nan | +1.0 | +0.5 | robust to top-3 removal |
| stock | hold, no stop | rule-filtered L+S | 175 | 117 | +4.5 | +2.2 | 66 | +3.9 | +nan | +3.6 | +2.5 | robust to top-3 removal |
| stock | hold, no stop | unfiltered longs | 244 | 153 | +3.2 | +0.4 | 55 | +1.7 | +nan | +2.5 | +1.6 | robust to top-3 removal |
| stock | hold, no stop | rule-filtered longs | 115 | 70 | +5.0 | +1.1 | 63 | +3.5 | +nan | +3.6 | +1.9 | robust to top-3 removal |
| stock | setup's own stop (fixed) | unfiltered L+S | 433 | 210 | +1.3 | -1.0 | 46 | +1.2 | +nan | +0.9 | +0.4 | robust to top-3 removal |
| stock | setup's own stop (fixed) | rule-filtered L+S | 175 | 117 | +4.8 | +2.1 | 66 | +4.4 | +nan | +3.9 | +2.7 | robust to top-3 removal |
| stock | setup's own stop (fixed) | unfiltered longs | 244 | 153 | +2.9 | +0.1 | 51 | +1.8 | +nan | +2.3 | +1.3 | robust to top-3 removal |
| stock | setup's own stop (fixed) | rule-filtered longs | 115 | 70 | +5.4 | +1.1 | 63 | +4.2 | +nan | +4.0 | +2.3 | robust to top-3 removal |
| stock | fixed 8% | unfiltered L+S | 433 | 210 | +0.9 | -1.1 | 46 | +0.9 | +nan | +0.5 | +0.1 | robust to top-3 removal |
| stock | fixed 8% | rule-filtered L+S | 175 | 117 | +4.7 | +1.8 | 64 | +4.3 | +nan | +3.8 | +2.6 | robust to top-3 removal |
| stock | fixed 8% | unfiltered longs | 244 | 153 | +2.2 | -0.2 | 49 | +1.2 | +nan | +1.5 | +0.6 | LUCK (edge gone w/o top tickers) |
| stock | fixed 8% | rule-filtered longs | 115 | 70 | +5.3 | +1.0 | 61 | +4.2 | +nan | +3.9 | +2.1 | robust to top-3 removal |
| stock | trailing 5% | unfiltered L+S | 433 | 210 | +0.4 | -0.9 | 45 | +0.4 | +nan | +0.0 | -0.2 | LUCK (edge gone w/o top tickers) |
| stock | trailing 5% | rule-filtered L+S | 175 | 117 | +3.5 | +1.1 | 60 | +3.2 | +nan | +2.5 | +2.2 | robust to top-3 removal |
| stock | trailing 5% | unfiltered longs | 244 | 153 | +1.3 | -0.2 | 49 | +0.7 | +nan | +0.7 | +0.1 | LUCK (edge gone w/o top tickers) |
| stock | trailing 5% | rule-filtered longs | 115 | 70 | +3.6 | +0.6 | 59 | +2.9 | +nan | +2.1 | +1.5 | robust to top-3 removal |
| stock | trailing 8% | unfiltered L+S | 433 | 210 | +0.6 | -0.7 | 46 | +0.6 | +nan | +0.2 | -0.1 | LUCK (edge gone w/o top tickers) |
| stock | trailing 8% | rule-filtered L+S | 175 | 117 | +3.4 | +0.8 | 59 | +3.2 | +nan | +2.5 | +2.0 | robust to top-3 removal |
| stock | trailing 8% | unfiltered longs | 244 | 153 | +1.6 | +0.0 | 51 | +0.7 | +nan | +0.9 | +0.3 | LUCK (edge gone w/o top tickers) |
| stock | trailing 8% | rule-filtered longs | 115 | 70 | +3.4 | +0.4 | 57 | +2.6 | +nan | +2.0 | +1.2 | robust to top-3 removal |
| stock | trailing 12% | unfiltered L+S | 433 | 210 | +0.9 | -0.8 | 47 | +0.8 | +nan | +0.5 | +0.2 | robust to top-3 removal |
| stock | trailing 12% | rule-filtered L+S | 175 | 117 | +4.1 | +1.4 | 61 | +3.7 | +nan | +3.1 | +2.2 | robust to top-3 removal |
| stock | trailing 12% | unfiltered longs | 244 | 153 | +2.2 | +0.1 | 51 | +1.1 | +nan | +1.5 | +0.6 | LUCK (edge gone w/o top tickers) |
| stock | trailing 12% | rule-filtered longs | 115 | 70 | +4.1 | +0.4 | 57 | +3.0 | +nan | +2.7 | +1.2 | robust to top-3 removal |
| crypto | hold, no stop | unfiltered L+S | 386 | 32 | +17.8 | +20.5 | 72 | +nan | +6.8 | +15.3 | +12.5 | robust to top-3 removal |
| crypto | hold, no stop | rule-filtered L+S | 264 | 19 | +37.2 | +32.4 | 93 | +nan | +14.7 | +36.5 | +31.2 | robust to top-3 removal |
| crypto | hold, no stop | unfiltered longs | 264 | 19 | +37.2 | +32.4 | 93 | +nan | +14.7 | +36.5 | +31.2 | robust to top-3 removal |
| crypto | hold, no stop | rule-filtered longs | 264 | 19 | +37.2 | +32.4 | 93 | +nan | +14.7 | +36.5 | +31.2 | robust to top-3 removal |
| crypto | setup's own stop (fixed) | unfiltered L+S | 386 | 32 | +14.2 | +3.5 | 55 | +nan | +5.5 | +11.7 | +8.9 | robust to top-3 removal |
| crypto | setup's own stop (fixed) | rule-filtered L+S | 264 | 19 | +26.3 | +27.4 | 71 | +nan | +9.8 | +24.4 | +20.2 | robust to top-3 removal |
| crypto | setup's own stop (fixed) | unfiltered longs | 264 | 19 | +26.3 | +27.4 | 71 | +nan | +9.8 | +24.4 | +20.2 | robust to top-3 removal |
| crypto | setup's own stop (fixed) | rule-filtered longs | 264 | 19 | +26.3 | +27.4 | 71 | +nan | +9.8 | +24.4 | +20.2 | robust to top-3 removal |
| crypto | fixed 8% | unfiltered L+S | 386 | 32 | +17.4 | +7.8 | 60 | +nan | +6.9 | +14.9 | +12.6 | robust to top-3 removal |
| crypto | fixed 8% | rule-filtered L+S | 264 | 19 | +28.9 | +29.5 | 78 | +nan | +10.2 | +26.7 | +22.4 | robust to top-3 removal |
| crypto | fixed 8% | unfiltered longs | 264 | 19 | +28.9 | +29.5 | 78 | +nan | +10.2 | +26.7 | +22.4 | robust to top-3 removal |
| crypto | fixed 8% | rule-filtered longs | 264 | 19 | +28.9 | +29.5 | 78 | +nan | +10.2 | +26.7 | +22.4 | robust to top-3 removal |
| crypto | trailing 5% | unfiltered L+S | 386 | 32 | +7.5 | +1.3 | 52 | +nan | +2.1 | +6.2 | +4.9 | robust to top-3 removal |
| crypto | trailing 5% | rule-filtered L+S | 264 | 19 | +11.5 | +8.0 | 60 | +nan | +2.4 | +9.8 | +8.8 | robust to top-3 removal |
| crypto | trailing 5% | unfiltered longs | 264 | 19 | +11.5 | +8.0 | 60 | +nan | +2.4 | +9.8 | +8.8 | robust to top-3 removal |
| crypto | trailing 5% | rule-filtered longs | 264 | 19 | +11.5 | +8.0 | 60 | +nan | +2.4 | +9.8 | +8.8 | robust to top-3 removal |
| crypto | trailing 8% | unfiltered L+S | 386 | 32 | +12.0 | +6.5 | 64 | +nan | +2.8 | +10.8 | +9.5 | robust to top-3 removal |
| crypto | trailing 8% | rule-filtered L+S | 264 | 19 | +18.6 | +25.2 | 77 | +nan | +3.6 | +17.5 | +16.2 | robust to top-3 removal |
| crypto | trailing 8% | unfiltered longs | 264 | 19 | +18.6 | +25.2 | 77 | +nan | +3.6 | +17.5 | +16.2 | robust to top-3 removal |
| crypto | trailing 8% | rule-filtered longs | 264 | 19 | +18.6 | +25.2 | 77 | +nan | +3.6 | +17.5 | +16.2 | robust to top-3 removal |
| crypto | trailing 12% | unfiltered L+S | 386 | 32 | +15.9 | +8.3 | 65 | +nan | +5.6 | +13.0 | +11.8 | robust to top-3 removal |
| crypto | trailing 12% | rule-filtered L+S | 264 | 19 | +25.9 | +28.1 | 82 | +nan | +8.4 | +22.7 | +19.5 | robust to top-3 removal |
| crypto | trailing 12% | unfiltered longs | 264 | 19 | +25.9 | +28.1 | 82 | +nan | +8.4 | +22.7 | +19.5 | robust to top-3 removal |
| crypto | trailing 12% | rule-filtered longs | 264 | 19 | +25.9 | +28.1 | 82 | +nan | +8.4 | +22.7 | +19.5 | robust to top-3 removal |

### I. Fibonacci exits vs ATR stops vs trailing 8% vs hold (same setups with a confirmed zigzag leg; Z=2xATR14 zigzag, 0.5xATR buffer; x_mkt = vs BTC for crypto, vs SPY for stocks)
| segment | policy | N | tickers | mean | median | hit | x_mkt | mean_wo_top1 | x_mkt_wo_top1 | top1 | stopped | target | days | flag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Grok crypto LONG | hold, no stop | 255 | 19 | +36.9 | +32.1 | 93 | +14.7 | +36.3 | +14.0 | SOL-USD(46) | +0.0 | +0.0 | +53.3 | robust to top-3 removal |
| Grok crypto LONG | trailing 8% (close) | 255 | 19 | +18.2 | +22.9 | 76 | +3.6 | +17.1 | +2.5 | SOL-USD(46) | +54.9 | +0.0 | +32.0 | robust to top-3 removal |
| Grok crypto LONG | 2xATR stop (close) | 255 | 19 | +29.0 | +28.7 | 77 | +11.0 | +27.3 | +9.8 | SOL-USD(46) | +15.3 | +0.0 | +44.7 | robust to top-3 removal |
| Grok crypto LONG | 3xATR stop (close) | 255 | 19 | +33.1 | +31.1 | 87 | +12.6 | +31.7 | +11.3 | SOL-USD(46) | +5.9 | +0.0 | +50.2 | robust to top-3 removal |
| Grok crypto LONG | fib stop + 1.272 tgt (close) | 255 | 19 | +7.6 | +7.9 | 68 | +2.6 | +7.0 | +1.8 | LINK-USD(23) | +29.8 | +62.4 | +10.2 | robust to top-3 removal |
| Grok crypto LONG | fib stop + 1.618 tgt (close) | 255 | 19 | +9.4 | +10.6 | 65 | +2.8 | +8.5 | +2.0 | LINK-USD(23) | +30.2 | +54.9 | +13.1 | robust to top-3 removal |
| Grok crypto LONG | fib stop + 2.618 tgt (close) | 255 | 19 | +15.2 | +12.2 | 64 | +3.7 | +13.1 | +3.2 | ETH-USD(44) | +30.6 | +47.1 | +19.2 | robust to top-3 removal |
| Grok crypto LONG | fib stop + 1/3 at each tgt (close) | 255 | 19 | +10.7 | +11.3 | 67 | -0.9 | +10.4 | -1.2 | AAVE-USD(4) | +30.6 | +61.6 | +19.2 | no edge vs bench |
| Grok crypto LONG | 2xATR stop (intraday) | 255 | 19 | +27.4 | +28.1 | 75 | +10.2 | +25.6 | +8.8 | SOL-USD(46) | +18.0 | +0.0 | +42.8 | robust to top-3 removal |
| Grok crypto LONG | 3xATR stop (intraday) | 255 | 19 | +32.6 | +31.0 | 85 | +12.4 | +31.0 | +11.1 | SOL-USD(46) | +7.5 | +0.0 | +49.4 | robust to top-3 removal |
| Grok crypto LONG | fib stop + 1.272 tgt (intraday) | 255 | 19 | +3.6 | +2.3 | 62 | +0.3 | +3.1 | -0.3 | LINK-USD(23) | +39.2 | +56.5 | +7.6 | LUCK (edge gone w/o top tickers) |
| Grok crypto LONG | fib stop + 1.618 tgt (intraday) | 255 | 19 | +5.7 | +3.8 | 56 | +1.2 | +4.7 | +0.4 | LINK-USD(23) | +41.6 | +47.5 | +10.6 | LUCK (edge gone w/o top tickers) |
| Grok crypto LONG | fib stop + 2.618 tgt (intraday) | 255 | 19 | +10.2 | +2.4 | 55 | +1.7 | +9.0 | +1.1 | LINK-USD(23) | +42.4 | +41.6 | +14.6 | robust to top-3 removal |
| Grok crypto LONG | fib stop + 1/3 at each tgt (intraday) | 255 | 19 | +6.4 | +4.0 | 58 | -2.1 | +6.2 | -2.4 | UNI7083-USD(8) | +42.4 | +53.3 | +14.6 | no edge vs bench |
| All stock LONG | hold, no stop | 242 | 151 | +3.2 | +0.4 | 54 | +1.6 | +2.5 | +0.9 | XP(2) | +0.0 | +0.0 | +19.1 | LUCK (edge gone w/o top tickers) |
| All stock LONG | trailing 8% (close) | 242 | 151 | +1.6 | +0.0 | 51 | +0.7 | +0.9 | +0.0 | XP(2) | +42.6 | +0.0 | +11.5 | LUCK (edge gone w/o top tickers) |
| All stock LONG | 2xATR stop (close) | 242 | 151 | +2.5 | +0.0 | 51 | +1.4 | +1.8 | +0.7 | XP(2) | +26.9 | +0.0 | +15.0 | LUCK (edge gone w/o top tickers) |
| All stock LONG | 3xATR stop (close) | 242 | 151 | +3.5 | +0.3 | 53 | +2.2 | +2.8 | +1.5 | XP(2) | +14.0 | +0.0 | +17.2 | robust to top-3 removal |
| All stock LONG | fib stop + 1.272 tgt (close) | 242 | 151 | +1.2 | -1.0 | 45 | +0.9 | +0.7 | +0.4 | RXRX(4) | +48.3 | +25.2 | +7.7 | LUCK (edge gone w/o top tickers) |
| All stock LONG | fib stop + 1.618 tgt (close) | 242 | 151 | +1.2 | -1.2 | 43 | +0.8 | +0.8 | +0.4 | RXRX(4) | +48.8 | +11.2 | +9.0 | LUCK (edge gone w/o top tickers) |
| All stock LONG | fib stop + 2.618 tgt (close) | 242 | 151 | +1.4 | -1.2 | 42 | +0.9 | +0.9 | +0.4 | RXRX(4) | +49.2 | +5.0 | +10.1 | LUCK (edge gone w/o top tickers) |
| All stock LONG | fib stop + 1/3 at each tgt (close) | 242 | 151 | +1.3 | -1.1 | 44 | +0.8 | +0.8 | +0.4 | RXRX(4) | +49.2 | +24.4 | +10.1 | LUCK (edge gone w/o top tickers) |
| All stock LONG | 2xATR stop (intraday) | 242 | 151 | +2.6 | +0.0 | 50 | +1.7 | +1.9 | +1.0 | XP(2) | +31.4 | +0.0 | +14.0 | robust to top-3 removal |
| All stock LONG | 3xATR stop (intraday) | 242 | 151 | +3.5 | +0.3 | 53 | +2.3 | +2.9 | +1.6 | XP(2) | +15.3 | +0.0 | +16.9 | robust to top-3 removal |
| All stock LONG | fib stop + 1.272 tgt (intraday) | 242 | 151 | +1.4 | -0.5 | 47 | +1.1 | +1.1 | +0.8 | RXRX(4) | +51.7 | +30.2 | +5.9 | robust to top-3 removal |
| All stock LONG | fib stop + 1.618 tgt (intraday) | 242 | 151 | +2.0 | -0.8 | 44 | +1.6 | +1.6 | +1.1 | RXRX(4) | +52.9 | +15.3 | +7.1 | robust to top-3 removal |
| All stock LONG | fib stop + 2.618 tgt (intraday) | 242 | 151 | +1.7 | -1.0 | 42 | +1.2 | +1.3 | +0.8 | RXRX(4) | +53.7 | +7.4 | +8.4 | robust to top-3 removal |
| All stock LONG | fib stop + 1/3 at each tgt (intraday) | 242 | 151 | +1.8 | -0.8 | 43 | +1.2 | +1.3 | +0.8 | RXRX(4) | +53.7 | +28.1 | +8.4 | robust to top-3 removal |
| Rule-filtered stock LONG | hold, no stop | 115 | 70 | +5.0 | +1.1 | 63 | +3.5 | +3.6 | +2.1 | XP(2) | +0.0 | +0.0 | +19.8 | robust to top-3 removal |
| Rule-filtered stock LONG | trailing 8% (close) | 115 | 70 | +3.4 | +0.4 | 57 | +2.6 | +2.0 | +1.1 | XP(2) | +44.3 | +0.0 | +11.9 | robust to top-3 removal |
| Rule-filtered stock LONG | 2xATR stop (close) | 115 | 70 | +5.1 | +1.0 | 62 | +3.9 | +3.7 | +2.5 | XP(2) | +20.0 | +0.0 | +15.8 | robust to top-3 removal |
| Rule-filtered stock LONG | 3xATR stop (close) | 115 | 70 | +5.5 | +1.1 | 63 | +4.1 | +4.1 | +2.7 | XP(2) | +10.4 | +0.0 | +17.9 | robust to top-3 removal |
| Rule-filtered stock LONG | fib stop + 1.272 tgt (close) | 115 | 70 | +2.5 | +1.0 | 57 | +2.0 | +1.8 | +1.3 | RXRX(3) | +30.4 | +36.5 | +9.6 | robust to top-3 removal |
| Rule-filtered stock LONG | fib stop + 1.618 tgt (close) | 115 | 70 | +3.0 | +0.3 | 54 | +2.4 | +2.4 | +1.8 | WGS(1) | +30.4 | +15.7 | +11.1 | robust to top-3 removal |
| Rule-filtered stock LONG | fib stop + 2.618 tgt (close) | 115 | 70 | +2.6 | +0.3 | 53 | +1.9 | +2.0 | +1.3 | RXRX(3) | +31.3 | +7.0 | +12.1 | robust to top-3 removal |
| Rule-filtered stock LONG | fib stop + 1/3 at each tgt (close) | 115 | 70 | +2.7 | +0.5 | 55 | +1.9 | +2.1 | +1.4 | RXRX(3) | +31.3 | +35.7 | +12.1 | robust to top-3 removal |
| Rule-filtered stock LONG | 2xATR stop (intraday) | 115 | 70 | +5.2 | +1.0 | 62 | +4.1 | +3.8 | +2.7 | XP(2) | +25.2 | +0.0 | +15.1 | robust to top-3 removal |
| Rule-filtered stock LONG | 3xATR stop (intraday) | 115 | 70 | +5.5 | +1.1 | 63 | +4.2 | +4.1 | +2.8 | XP(2) | +12.2 | +0.0 | +17.4 | robust to top-3 removal |
| Rule-filtered stock LONG | fib stop + 1.272 tgt (intraday) | 115 | 70 | +2.2 | +0.5 | 55 | +1.8 | +1.8 | +1.3 | VICR(3) | +38.3 | +43.5 | +7.2 | robust to top-3 removal |
| Rule-filtered stock LONG | fib stop + 1.618 tgt (intraday) | 115 | 70 | +3.2 | +0.0 | 50 | +2.6 | +2.3 | +1.8 | RXRX(3) | +38.3 | +19.1 | +9.2 | robust to top-3 removal |
| Rule-filtered stock LONG | fib stop + 2.618 tgt (intraday) | 115 | 70 | +2.4 | -0.2 | 49 | +1.6 | +1.8 | +1.1 | RXRX(3) | +39.1 | +7.0 | +10.2 | robust to top-3 removal |
| Rule-filtered stock LONG | fib stop + 1/3 at each tgt (intraday) | 115 | 70 | +2.6 | +0.0 | 50 | +1.9 | +2.0 | +1.3 | RXRX(3) | +39.1 | +42.6 | +10.2 | robust to top-3 removal |
| Perplexity stock LONG | hold, no stop | 59 | 42 | +5.8 | +1.7 | 59 | +5.0 | +3.1 | +2.2 | XP(2) | +0.0 | +0.0 | +23.7 | LUCK (edge gone w/o top tickers) |
| Perplexity stock LONG | trailing 8% (close) | 59 | 42 | +2.2 | -1.2 | 44 | +2.3 | -0.7 | -0.6 | XP(2) | +54.2 | +0.0 | +13.9 | LUCK (edge gone w/o top tickers) |
| Perplexity stock LONG | 2xATR stop (close) | 59 | 42 | +6.0 | +0.6 | 53 | +5.6 | +3.2 | +2.8 | XP(2) | +27.1 | +0.0 | +18.8 | robust to top-3 removal |
| Perplexity stock LONG | 3xATR stop (close) | 59 | 42 | +6.3 | +1.1 | 56 | +5.9 | +3.6 | +3.2 | XP(2) | +20.3 | +0.0 | +20.2 | robust to top-3 removal |
| Perplexity stock LONG | fib stop + 1.272 tgt (close) | 59 | 42 | +0.2 | -2.1 | 34 | +0.4 | -0.5 | -0.3 | MRVL(2) | +57.6 | +13.6 | +10.4 | LUCK (edge gone w/o top tickers) |
| Perplexity stock LONG | fib stop + 1.618 tgt (close) | 59 | 42 | +0.3 | -2.1 | 34 | +0.5 | -0.4 | -0.1 | MRVL(2) | +57.6 | +6.8 | +10.8 | LUCK (edge gone w/o top tickers) |
| Perplexity stock LONG | fib stop + 2.618 tgt (close) | 59 | 42 | +0.5 | -2.3 | 32 | +0.7 | -0.4 | -0.3 | XP(2) | +59.3 | +5.1 | +11.3 | LUCK (edge gone w/o top tickers) |
| Perplexity stock LONG | fib stop + 1/3 at each tgt (close) | 59 | 42 | +0.3 | -2.1 | 34 | +0.5 | -0.3 | -0.1 | XP(2) | +59.3 | +11.9 | +11.3 | LUCK (edge gone w/o top tickers) |
| Perplexity stock LONG | 2xATR stop (intraday) | 59 | 42 | +6.2 | +0.6 | 53 | +5.9 | +3.4 | +3.1 | XP(2) | +32.2 | +0.0 | +18.0 | robust to top-3 removal |
| Perplexity stock LONG | 3xATR stop (intraday) | 59 | 42 | +6.3 | +1.1 | 56 | +5.9 | +3.6 | +3.1 | XP(2) | +22.0 | +0.0 | +19.9 | robust to top-3 removal |
| Perplexity stock LONG | fib stop + 1.272 tgt (intraday) | 59 | 42 | +0.2 | -1.6 | 29 | +0.4 | -0.4 | -0.2 | MRVL(2) | +64.4 | +13.6 | +7.9 | LUCK (edge gone w/o top tickers) |
| Perplexity stock LONG | fib stop + 1.618 tgt (intraday) | 59 | 42 | +0.5 | -1.6 | 29 | +0.6 | -0.2 | +0.0 | MRVL(2) | +64.4 | +5.1 | +8.3 | LUCK (edge gone w/o top tickers) |
| Perplexity stock LONG | fib stop + 2.618 tgt (intraday) | 59 | 42 | -0.1 | -1.6 | 25 | +0.1 | -0.8 | -0.6 | MRVL(2) | +66.1 | +1.7 | +8.6 | LUCK (edge gone w/o top tickers) |
| Perplexity stock LONG | fib stop + 1/3 at each tgt (intraday) | 59 | 42 | +0.2 | -1.6 | 27 | +0.3 | -0.5 | -0.2 | MRVL(2) | +66.1 | +11.9 | +8.6 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | hold, no stop | 142 | 96 | +1.6 | +0.1 | 52 | -0.2 | +0.9 | -0.9 | IOVA(1) | +0.0 | +0.0 | +17.1 | no edge vs bench |
| Grok stock LONG | trailing 8% (close) | 142 | 96 | +1.1 | +0.2 | 52 | -0.0 | +0.8 | -0.4 | WGS(1) | +42.3 | +0.0 | +10.8 | no edge vs bench |
| Grok stock LONG | 2xATR stop (close) | 142 | 96 | +1.0 | -0.1 | 50 | -0.2 | +0.4 | -0.9 | IOVA(1) | +29.6 | +0.0 | +13.0 | no edge vs bench |
| Grok stock LONG | 3xATR stop (close) | 142 | 96 | +1.9 | +0.1 | 52 | +0.4 | +1.3 | -0.3 | IOVA(1) | +14.1 | +0.0 | +15.5 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | fib stop + 1.272 tgt (close) | 142 | 96 | +1.0 | -0.4 | 48 | +0.6 | +0.7 | +0.2 | VICR(3) | +45.1 | +29.6 | +6.8 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | fib stop + 1.618 tgt (close) | 142 | 96 | +1.2 | -0.9 | 44 | +0.6 | +0.7 | +0.1 | WGS(1) | +45.8 | +13.4 | +8.5 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | fib stop + 2.618 tgt (close) | 142 | 96 | +1.1 | -0.9 | 44 | +0.4 | +0.6 | -0.1 | RXRX(3) | +45.8 | +4.9 | +9.8 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | fib stop + 1/3 at each tgt (close) | 142 | 96 | +1.1 | -0.8 | 46 | +0.4 | +0.7 | -0.0 | RXRX(3) | +45.8 | +28.9 | +9.8 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | 2xATR stop (intraday) | 142 | 96 | +1.2 | -0.1 | 50 | +0.0 | +0.6 | -0.6 | IOVA(1) | +32.4 | +0.0 | +12.0 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | 3xATR stop (intraday) | 142 | 96 | +2.0 | +0.1 | 52 | +0.5 | +1.4 | -0.2 | IOVA(1) | +15.5 | +0.0 | +15.2 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | fib stop + 1.272 tgt (intraday) | 142 | 96 | +1.6 | +0.3 | 55 | +1.1 | +1.2 | +0.7 | VICR(3) | +46.5 | +35.9 | +5.3 | robust to top-3 removal |
| Grok stock LONG | fib stop + 1.618 tgt (intraday) | 142 | 96 | +2.4 | +0.0 | 50 | +1.7 | +1.9 | +1.3 | WGS(1) | +47.9 | +17.6 | +7.1 | robust to top-3 removal |
| Grok stock LONG | fib stop + 2.618 tgt (intraday) | 142 | 96 | +2.0 | -0.1 | 49 | +1.2 | +1.6 | +0.8 | RXRX(3) | +48.6 | +9.2 | +8.6 | robust to top-3 removal |
| Grok stock LONG | fib stop + 1/3 at each tgt (intraday) | 142 | 96 | +2.0 | -0.0 | 50 | +1.2 | +1.7 | +0.9 | RXRX(3) | +48.6 | +33.8 | +8.6 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | hold, no stop | 60 | 49 | +3.6 | +6.3 | 73 | +4.8 | +3.4 | +4.6 | LULU(3) | +0.0 | +0.0 | +19.0 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | trailing 8% (close) | 60 | 49 | +3.4 | +3.1 | 62 | +4.2 | +3.1 | +3.9 | WHR(1) | +35.0 | +0.0 | +13.8 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | 2xATR stop (close) | 60 | 49 | +4.2 | +6.3 | 72 | +5.2 | +4.0 | +5.0 | LULU(3) | +11.7 | +0.0 | +17.6 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | 3xATR stop (close) | 60 | 49 | +4.3 | +6.3 | 73 | +5.4 | +4.1 | +5.2 | LULU(3) | +6.7 | +0.0 | +18.0 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | fib stop + 1.272 tgt (close) | 60 | 49 | +3.3 | +2.9 | 78 | +3.6 | +3.0 | +3.3 | LULU(3) | +10.0 | +43.3 | +10.2 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | fib stop + 1.618 tgt (close) | 60 | 49 | +3.9 | +3.9 | 77 | +4.4 | +3.7 | +4.2 | LULU(3) | +10.0 | +31.7 | +12.4 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | fib stop + 2.618 tgt (close) | 60 | 49 | +4.5 | +5.4 | 77 | +5.3 | +4.3 | +5.1 | LULU(3) | +10.0 | +18.3 | +15.0 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | fib stop + 1/3 at each tgt (close) | 60 | 49 | +3.9 | +3.8 | 77 | +4.6 | +3.7 | +4.4 | LULU(3) | +10.0 | +43.3 | +15.0 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | 2xATR stop (intraday) | 60 | 49 | +4.0 | +6.3 | 72 | +5.0 | +3.8 | +4.8 | LULU(3) | +16.7 | +0.0 | +16.2 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | 3xATR stop (intraday) | 60 | 49 | +4.5 | +6.3 | 73 | +5.6 | +4.4 | +5.5 | LULU(3) | +6.7 | +0.0 | +17.6 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | fib stop + 1.272 tgt (intraday) | 60 | 49 | +3.0 | +2.5 | 77 | +3.2 | +2.8 | +2.9 | LULU(3) | +15.0 | +46.7 | +8.3 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | fib stop + 1.618 tgt (intraday) | 60 | 49 | +3.1 | +3.2 | 73 | +3.6 | +2.9 | +3.3 | LULU(3) | +16.7 | +31.7 | +10.9 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | fib stop + 2.618 tgt (intraday) | 60 | 49 | +3.9 | +4.0 | 73 | +4.6 | +3.7 | +4.3 | LULU(3) | +16.7 | +23.3 | +12.9 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | fib stop + 1/3 at each tgt (intraday) | 60 | 49 | +3.4 | +3.5 | 73 | +4.1 | +3.2 | +3.8 | LULU(3) | +16.7 | +45.0 | +12.9 | robust to top-3 removal |
| All stock SHORT | hold, no stop | 189 | 101 | -1.0 | -1.2 | 44 | +0.5 | -1.3 | +0.2 | LCID(1) | +0.0 | +0.0 | +16.2 | LUCK (edge gone w/o top tickers) |
| All stock SHORT | trailing 8% (close) | 189 | 101 | -0.7 | -2.0 | 39 | +0.3 | -0.9 | +0.0 | LCID(1) | +37.0 | +0.0 | +10.9 | LUCK (edge gone w/o top tickers) |
| All stock SHORT | 2xATR stop (close) | 189 | 101 | -0.5 | -1.8 | 43 | +0.8 | -0.7 | +0.5 | LCID(1) | +28.6 | +0.0 | +13.2 | robust to top-3 removal |
| All stock SHORT | 3xATR stop (close) | 189 | 101 | -0.7 | -1.2 | 44 | +0.6 | -1.0 | +0.3 | LCID(1) | +17.5 | +0.0 | +14.7 | robust to top-3 removal |
| All stock SHORT | fib stop + 1.272 tgt (close) | 189 | 101 | +0.0 | +0.0 | 50 | +0.4 | -0.1 | +0.2 | LCID(1) | +55.6 | +19.6 | +6.9 | LUCK (edge gone w/o top tickers) |
| All stock SHORT | fib stop + 1.618 tgt (close) | 189 | 101 | -0.0 | -0.6 | 48 | +0.5 | -0.2 | +0.3 | LCID(1) | +57.1 | +13.2 | +8.1 | robust to top-3 removal |
| All stock SHORT | fib stop + 2.618 tgt (close) | 189 | 101 | +0.3 | -0.6 | 48 | +0.9 | -0.0 | +0.6 | LCID(1) | +57.1 | +7.4 | +9.4 | robust to top-3 removal |
| All stock SHORT | fib stop + 1/3 at each tgt (close) | 189 | 101 | +0.1 | -0.3 | 48 | +0.8 | -0.1 | +0.6 | LCID(1) | +57.1 | +18.0 | +9.4 | robust to top-3 removal |
| All stock SHORT | 2xATR stop (intraday) | 189 | 101 | -0.3 | -1.8 | 42 | +0.9 | -0.6 | +0.6 | LCID(1) | +37.0 | +0.0 | +12.4 | robust to top-3 removal |
| All stock SHORT | 3xATR stop (intraday) | 189 | 101 | -0.4 | -1.2 | 44 | +0.9 | -0.7 | +0.6 | LCID(1) | +20.1 | +0.0 | +14.4 | robust to top-3 removal |
| All stock SHORT | fib stop + 1.272 tgt (intraday) | 189 | 101 | -0.1 | -0.4 | 47 | +0.2 | -0.2 | +0.1 | LULU(3) | +59.3 | +21.7 | +5.0 | LUCK (edge gone w/o top tickers) |
| All stock SHORT | fib stop + 1.618 tgt (intraday) | 189 | 101 | -0.3 | -0.5 | 45 | +0.1 | -0.4 | -0.0 | LULU(3) | +60.8 | +15.3 | +6.4 | LUCK (edge gone w/o top tickers) |
| All stock SHORT | fib stop + 2.618 tgt (intraday) | 189 | 101 | -0.1 | -0.7 | 42 | +0.4 | -0.2 | +0.3 | PATH(2) | +63.5 | +10.1 | +7.2 | LUCK (edge gone w/o top tickers) |
| All stock SHORT | fib stop + 1/3 at each tgt (intraday) | 189 | 101 | -0.1 | -0.5 | 46 | +0.4 | -0.2 | +0.3 | LULU(3) | +63.5 | +17.5 | +7.2 | robust to top-3 removal |

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

### K. Deeper STRUCTURE stops, no targets (strict PIT 2xATR14 zigzag; leg = last confirmed swing high + its origin low; mirrored for shorts) vs hold / fixed 3xATR / chandelier 4xATR (same setups; stop_med/p25 = initial stop distance % of entry; fallback% = structure level already breached at entry, next deeper confirmed pivot used)
| segment | policy | N | exited | still_open | stopped | stop_med | stop_p25 | mean | median | hit | x_mkt | mean_wo_top1 | mean_wo_top3 | x_mkt_wo_top1 | x_mkt_wo_top3 | days | fallback | flag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Grok crypto LONG | hold, no stop | 254 | 0 | 254 | +0.0 | +nan | +nan | +36.8 | +32.0 | 93 | +14.8 | +36.2 | +30.7 | +14.0 | +8.6 | +53.3 | +nan | robust to top-3 removal |
| Grok crypto LONG | fixed 3xATR (close) | 254 | 15 | 239 | +5.9 | +10.5 | +8.5 | +33.1 | +31.1 | 87 | +12.6 | +31.6 | +26.8 | +11.3 | +6.5 | +50.2 | +nan | robust to top-3 removal |
| Grok crypto LONG | chandelier 4xATR (close) | 254 | 19 | 235 | +7.5 | +13.9 | +11.3 | +32.7 | +30.3 | 85 | +12.8 | +31.1 | +26.2 | +11.6 | +6.8 | +49.1 | +nan | robust to top-3 removal |
| Grok crypto LONG | (a) below 0.786 - 0.5ATR (close) | 254 | 35 | 219 | +13.8 | +10.4 | +5.4 | +29.2 | +28.0 | 79 | +11.0 | +28.6 | +23.9 | +10.2 | +6.2 | +45.1 | +7.9 | robust to top-3 removal |
| Grok crypto LONG | (b) below swing origin - 0.5ATR (close) | 254 | 25 | 229 | +9.8 | +14.4 | +6.9 | +30.3 | +28.5 | 83 | +11.3 | +29.4 | +24.8 | +10.3 | +6.3 | +47.1 | +3.9 | robust to top-3 removal |
| Grok crypto LONG | (c) below swing origin - 1.0ATR (close) | 254 | 15 | 239 | +5.9 | +16.3 | +8.9 | +32.7 | +29.8 | 87 | +12.3 | +31.1 | +26.4 | +11.1 | +6.5 | +49.6 | +2.8 | robust to top-3 removal |
| Grok crypto LONG | (d) structure trail, confirmed higher-lows (close) | 254 | 42 | 212 | +16.5 | +14.4 | +6.9 | +27.6 | +27.3 | 77 | +10.2 | +25.0 | +22.5 | +7.9 | +5.4 | +43.8 | +3.9 | robust to top-3 removal |
| Grok crypto LONG | fixed 3xATR (intraday) | 254 | 19 | 235 | +7.5 | +10.5 | +8.5 | +32.5 | +30.9 | 85 | +12.4 | +31.0 | +26.0 | +11.1 | +6.3 | +49.4 | +nan | robust to top-3 removal |
| Grok crypto LONG | chandelier 4xATR (intraday) | 254 | 45 | 209 | +17.7 | +13.9 | +11.3 | +29.2 | +28.5 | 82 | +10.9 | +26.9 | +21.8 | +9.2 | +4.4 | +46.3 | +nan | robust to top-3 removal |
| Grok crypto LONG | (a) below 0.786 - 0.5ATR (intraday) | 254 | 41 | 213 | +16.1 | +10.4 | +5.4 | +27.5 | +27.3 | 76 | +9.8 | +25.0 | +22.6 | +7.5 | +5.1 | +43.8 | +7.9 | robust to top-3 removal |
| Grok crypto LONG | (b) below swing origin - 0.5ATR (intraday) | 254 | 34 | 220 | +13.4 | +14.4 | +6.9 | +29.2 | +28.1 | 79 | +11.0 | +28.7 | +24.1 | +10.2 | +6.3 | +45.6 | +3.9 | robust to top-3 removal |
| Grok crypto LONG | (c) below swing origin - 1.0ATR (intraday) | 254 | 21 | 233 | +8.3 | +16.3 | +8.9 | +31.3 | +28.8 | 84 | +11.7 | +30.9 | +26.2 | +11.0 | +6.4 | +48.1 | +2.8 | robust to top-3 removal |
| Grok crypto LONG | (d) structure trail, confirmed higher-lows (intraday) | 254 | 107 | 147 | +42.1 | +14.4 | +6.9 | +21.8 | +15.6 | 69 | +7.6 | +19.2 | +16.5 | +5.3 | +2.5 | +37.6 | +3.9 | robust to top-3 removal |
| All stock LONG | hold, no stop | 228 | 0 | 228 | +0.0 | +nan | +nan | +3.7 | +0.5 | 56 | +2.2 | +3.0 | +2.0 | +1.4 | +0.5 | +19.2 | +nan | robust to top-3 removal |
| All stock LONG | fixed 3xATR (close) | 228 | 28 | 200 | +12.3 | +12.6 | +7.7 | +4.0 | +0.4 | 55 | +2.6 | +3.2 | +2.3 | +1.9 | +0.9 | +17.5 | +nan | robust to top-3 removal |
| All stock LONG | chandelier 4xATR (close) | 228 | 36 | 192 | +15.8 | +16.8 | +10.3 | +3.7 | +0.4 | 55 | +2.4 | +3.0 | +2.0 | +1.7 | +0.7 | +17.2 | +nan | robust to top-3 removal |
| All stock LONG | (a) below 0.786 - 0.5ATR (close) | 228 | 75 | 153 | +32.9 | +8.4 | +2.1 | +2.5 | -0.7 | 46 | +1.6 | +1.7 | +0.9 | +0.8 | +0.0 | +13.3 | +24.1 | robust to top-3 removal |
| All stock LONG | (b) below swing origin - 0.5ATR (close) | 228 | 64 | 164 | +28.1 | +11.7 | +3.9 | +2.3 | -0.5 | 48 | +1.3 | +1.6 | +0.7 | +0.6 | -0.3 | +14.3 | +14.9 | LUCK (edge gone w/o top tickers) |
| All stock LONG | (c) below swing origin - 1.0ATR (close) | 228 | 49 | 179 | +21.5 | +13.1 | +5.2 | +3.7 | +0.1 | 51 | +2.6 | +3.0 | +2.0 | +1.8 | +0.9 | +15.4 | +10.1 | robust to top-3 removal |
| All stock LONG | (d) structure trail, confirmed higher-lows (close) | 228 | 69 | 159 | +30.3 | +11.7 | +3.9 | +2.6 | -0.5 | 48 | +1.6 | +1.8 | +0.9 | +0.8 | -0.0 | +14.1 | +14.9 | LUCK (edge gone w/o top tickers) |
| All stock LONG | fixed 3xATR (intraday) | 228 | 31 | 197 | +13.6 | +12.6 | +7.7 | +4.0 | +0.4 | 55 | +2.7 | +3.3 | +2.3 | +2.0 | +1.0 | +17.1 | +nan | robust to top-3 removal |
| All stock LONG | chandelier 4xATR (intraday) | 228 | 40 | 188 | +17.5 | +16.8 | +10.3 | +3.8 | +0.4 | 55 | +2.6 | +3.1 | +2.1 | +1.8 | +0.9 | +16.9 | +nan | robust to top-3 removal |
| All stock LONG | (a) below 0.786 - 0.5ATR (intraday) | 228 | 91 | 137 | +39.9 | +8.4 | +2.1 | +1.4 | -0.8 | 41 | +0.7 | +1.0 | +0.4 | +0.2 | -0.3 | +11.0 | +24.1 | LUCK (edge gone w/o top tickers) |
| All stock LONG | (b) below swing origin - 0.5ATR (intraday) | 228 | 79 | 149 | +34.6 | +11.7 | +3.9 | +1.6 | -0.8 | 45 | +0.7 | +1.2 | +0.5 | +0.3 | -0.4 | +12.5 | +14.9 | LUCK (edge gone w/o top tickers) |
| All stock LONG | (c) below swing origin - 1.0ATR (intraday) | 228 | 68 | 160 | +29.8 | +13.1 | +5.2 | +2.1 | -0.6 | 46 | +1.1 | +1.6 | +0.7 | +0.6 | -0.3 | +14.0 | +10.1 | LUCK (edge gone w/o top tickers) |
| All stock LONG | (d) structure trail, confirmed higher-lows (intraday) | 228 | 85 | 143 | +37.3 | +11.7 | +3.9 | +1.8 | -0.6 | 45 | +0.9 | +1.4 | +0.8 | +0.5 | -0.1 | +12.3 | +14.9 | LUCK (edge gone w/o top tickers) |
| Rule-filtered stock LONG | hold, no stop | 115 | 0 | 115 | +0.0 | +nan | +nan | +5.0 | +1.1 | 63 | +3.5 | +3.6 | +1.9 | +2.1 | +0.3 | +19.8 | +nan | robust to top-3 removal |
| Rule-filtered stock LONG | fixed 3xATR (close) | 115 | 12 | 103 | +10.4 | +13.0 | +8.3 | +5.5 | +1.1 | 63 | +4.1 | +4.1 | +2.3 | +2.7 | +0.9 | +17.9 | +nan | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 4xATR (close) | 115 | 19 | 96 | +16.5 | +17.3 | +11.1 | +5.3 | +0.6 | 60 | +4.0 | +3.9 | +2.2 | +2.6 | +0.8 | +17.7 | +nan | robust to top-3 removal |
| Rule-filtered stock LONG | (a) below 0.786 - 0.5ATR (close) | 115 | 28 | 87 | +24.3 | +11.3 | +3.2 | +4.2 | +0.4 | 55 | +3.2 | +2.8 | +1.4 | +1.7 | +0.4 | +14.7 | +14.8 | robust to top-3 removal |
| Rule-filtered stock LONG | (b) below swing origin - 0.5ATR (close) | 115 | 23 | 92 | +20.0 | +16.2 | +5.2 | +4.3 | +0.4 | 57 | +3.1 | +2.9 | +1.4 | +1.7 | +0.1 | +15.7 | +6.1 | robust to top-3 removal |
| Rule-filtered stock LONG | (c) below swing origin - 1.0ATR (close) | 115 | 20 | 95 | +17.4 | +18.2 | +6.6 | +5.2 | +0.6 | 59 | +4.1 | +3.8 | +2.1 | +2.7 | +0.9 | +15.4 | +3.5 | robust to top-3 removal |
| Rule-filtered stock LONG | (d) structure trail, confirmed higher-lows (close) | 115 | 27 | 88 | +23.5 | +16.2 | +5.2 | +4.6 | +0.4 | 57 | +3.4 | +3.2 | +1.7 | +2.0 | +0.5 | +15.6 | +6.1 | robust to top-3 removal |
| Rule-filtered stock LONG | fixed 3xATR (intraday) | 115 | 14 | 101 | +12.2 | +13.0 | +8.3 | +5.5 | +1.1 | 63 | +4.2 | +4.1 | +2.4 | +2.8 | +1.0 | +17.4 | +nan | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 4xATR (intraday) | 115 | 21 | 94 | +18.3 | +17.3 | +11.1 | +5.5 | +0.6 | 60 | +4.3 | +4.1 | +2.3 | +2.8 | +1.1 | +17.4 | +nan | robust to top-3 removal |
| Rule-filtered stock LONG | (a) below 0.786 - 0.5ATR (intraday) | 115 | 37 | 78 | +32.2 | +11.3 | +3.2 | +2.0 | -0.1 | 49 | +1.1 | +1.2 | +0.5 | +0.3 | -0.4 | +11.1 | +14.8 | LUCK (edge gone w/o top tickers) |
| Rule-filtered stock LONG | (b) below swing origin - 0.5ATR (intraday) | 115 | 30 | 85 | +26.1 | +16.2 | +5.2 | +2.6 | +0.1 | 52 | +1.5 | +1.7 | +0.9 | +0.7 | -0.2 | +13.2 | +6.1 | LUCK (edge gone w/o top tickers) |
| Rule-filtered stock LONG | (c) below swing origin - 1.0ATR (intraday) | 115 | 28 | 87 | +24.3 | +18.2 | +6.6 | +2.5 | +0.1 | 52 | +1.4 | +1.6 | +0.4 | +0.6 | -0.6 | +13.8 | +3.5 | LUCK (edge gone w/o top tickers) |
| Rule-filtered stock LONG | (d) structure trail, confirmed higher-lows (intraday) | 115 | 35 | 80 | +30.4 | +16.2 | +5.2 | +2.7 | +0.1 | 52 | +1.7 | +1.9 | +1.3 | +0.9 | +0.3 | +12.8 | +6.1 | robust to top-3 removal |
| Perplexity stock LONG | hold, no stop | 57 | 0 | 57 | +0.0 | +nan | +nan | +6.7 | +1.7 | 61 | +5.8 | +3.8 | +1.2 | +2.9 | +0.3 | +23.2 | +nan | robust to top-3 removal |
| Perplexity stock LONG | fixed 3xATR (close) | 57 | 10 | 47 | +17.5 | +12.3 | +8.6 | +7.1 | +1.2 | 58 | +6.6 | +4.2 | +1.7 | +3.7 | +1.2 | +20.6 | +nan | robust to top-3 removal |
| Perplexity stock LONG | chandelier 4xATR (close) | 57 | 15 | 42 | +26.3 | +16.4 | +11.5 | +6.4 | +0.6 | 54 | +5.9 | +3.5 | +0.9 | +3.1 | +0.4 | +20.2 | +nan | robust to top-3 removal |
| Perplexity stock LONG | (a) below 0.786 - 0.5ATR (close) | 57 | 25 | 32 | +43.9 | +4.1 | +0.6 | +3.5 | -1.3 | 40 | +3.3 | +0.6 | -0.7 | +0.4 | -0.9 | +14.2 | +26.3 | LUCK (edge gone w/o top tickers) |
| Perplexity stock LONG | (b) below swing origin - 0.5ATR (close) | 57 | 23 | 34 | +40.4 | +8.4 | +2.3 | +3.7 | -1.3 | 42 | +3.5 | +0.8 | -0.6 | +0.5 | -0.8 | +15.4 | +8.8 | LUCK (edge gone w/o top tickers) |
| Perplexity stock LONG | (c) below swing origin - 1.0ATR (close) | 57 | 12 | 45 | +21.1 | +12.0 | +4.5 | +7.5 | +1.7 | 60 | +6.9 | +4.6 | +2.1 | +4.1 | +1.5 | +18.8 | +8.8 | robust to top-3 removal |
| Perplexity stock LONG | (d) structure trail, confirmed higher-lows (close) | 57 | 24 | 33 | +42.1 | +8.4 | +2.3 | +3.9 | -1.3 | 42 | +3.7 | +1.0 | -0.3 | +0.8 | -0.5 | +15.2 | +8.8 | LUCK (edge gone w/o top tickers) |
| Perplexity stock LONG | fixed 3xATR (intraday) | 57 | 11 | 46 | +19.3 | +12.3 | +8.6 | +7.1 | +1.2 | 58 | +6.6 | +4.2 | +1.7 | +3.7 | +1.2 | +20.2 | +nan | robust to top-3 removal |
| Perplexity stock LONG | chandelier 4xATR (intraday) | 57 | 17 | 40 | +29.8 | +16.4 | +11.5 | +6.5 | +0.6 | 54 | +6.1 | +3.6 | +1.0 | +3.3 | +0.6 | +19.7 | +nan | robust to top-3 removal |
| Perplexity stock LONG | (a) below 0.786 - 0.5ATR (intraday) | 57 | 28 | 29 | +49.1 | +4.1 | +0.6 | +1.0 | -0.7 | 37 | +0.8 | +0.4 | -0.7 | +0.2 | -0.8 | +10.6 | +26.3 | LUCK (edge gone w/o top tickers) |
| Perplexity stock LONG | (b) below swing origin - 0.5ATR (intraday) | 57 | 27 | 30 | +47.4 | +8.4 | +2.3 | +0.4 | -1.3 | 37 | +0.1 | -0.3 | -1.4 | -0.5 | -1.6 | +11.8 | +8.8 | LUCK (edge gone w/o top tickers) |
| Perplexity stock LONG | (c) below swing origin - 1.0ATR (intraday) | 57 | 23 | 34 | +40.4 | +12.0 | +4.5 | +1.1 | -1.7 | 40 | +0.7 | +0.4 | -0.8 | +0.1 | -1.1 | +16.1 | +8.8 | LUCK (edge gone w/o top tickers) |
| Perplexity stock LONG | (d) structure trail, confirmed higher-lows (intraday) | 57 | 28 | 29 | +49.1 | +8.4 | +2.3 | +0.6 | -0.9 | 37 | +0.4 | -0.0 | -1.1 | -0.2 | -1.2 | +11.7 | +8.8 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | hold, no stop | 131 | 0 | 131 | +0.0 | +nan | +nan | +2.0 | +0.3 | 54 | +0.2 | +1.2 | +0.4 | -0.6 | -1.5 | +17.4 | +nan | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | fixed 3xATR (close) | 131 | 16 | 115 | +12.2 | +12.9 | +8.2 | +2.2 | +0.3 | 54 | +0.6 | +1.5 | +0.7 | -0.1 | -1.0 | +16.0 | +nan | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | chandelier 4xATR (close) | 131 | 18 | 113 | +13.7 | +17.3 | +10.9 | +2.3 | +0.4 | 55 | +0.7 | +1.5 | +0.7 | -0.1 | -0.9 | +15.7 | +nan | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | (a) below 0.786 - 0.5ATR (close) | 131 | 39 | 92 | +29.8 | +10.2 | +2.9 | +1.6 | -0.2 | 48 | +0.5 | +0.9 | +0.1 | -0.2 | -0.9 | +12.4 | +21.4 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | (b) below swing origin - 0.5ATR (close) | 131 | 30 | 101 | +22.9 | +13.3 | +5.0 | +1.5 | +0.0 | 50 | +0.2 | +0.7 | -0.2 | -0.6 | -1.4 | +13.6 | +16.0 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | (c) below swing origin - 1.0ATR (close) | 131 | 26 | 105 | +19.8 | +16.1 | +6.3 | +1.8 | -0.2 | 50 | +0.4 | +1.1 | +0.2 | -0.3 | -1.2 | +14.3 | +11.5 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | (d) structure trail, confirmed higher-lows (close) | 131 | 34 | 97 | +26.0 | +13.3 | +5.0 | +1.8 | +0.0 | 50 | +0.5 | +1.0 | +0.2 | -0.2 | -1.1 | +13.3 | +16.0 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | fixed 3xATR (intraday) | 131 | 18 | 113 | +13.7 | +12.9 | +8.2 | +2.3 | +0.3 | 54 | +0.8 | +1.6 | +0.8 | +0.0 | -0.8 | +15.6 | +nan | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | chandelier 4xATR (intraday) | 131 | 20 | 111 | +15.3 | +17.3 | +10.9 | +2.4 | +0.4 | 55 | +0.8 | +1.7 | +0.9 | +0.1 | -0.7 | +15.4 | +nan | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | (a) below 0.786 - 0.5ATR (intraday) | 131 | 48 | 83 | +36.6 | +10.2 | +2.9 | +1.3 | -0.7 | 43 | +0.4 | +0.6 | -0.2 | -0.4 | -1.1 | +10.9 | +21.4 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | (b) below swing origin - 0.5ATR (intraday) | 131 | 38 | 93 | +29.0 | +13.3 | +5.0 | +1.7 | -0.2 | 48 | +0.6 | +1.0 | +0.1 | -0.2 | -1.0 | +12.6 | +16.0 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | (c) below swing origin - 1.0ATR (intraday) | 131 | 32 | 99 | +24.4 | +16.1 | +6.3 | +1.9 | -0.2 | 49 | +0.6 | +1.2 | +0.3 | -0.1 | -1.0 | +13.3 | +11.5 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | (d) structure trail, confirmed higher-lows (intraday) | 131 | 42 | 89 | +32.1 | +13.3 | +5.0 | +2.2 | -0.2 | 48 | +1.1 | +1.4 | +0.6 | +0.3 | -0.5 | +12.3 | +16.0 | LUCK (edge gone w/o top tickers) |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | hold, no stop | 60 | 0 | 60 | +0.0 | +nan | +nan | +3.6 | +6.3 | 73 | +4.8 | +3.4 | +2.7 | +4.6 | +3.9 | +19.0 | +nan | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | fixed 3xATR (close) | 60 | 4 | 56 | +6.7 | +10.7 | +8.1 | +4.3 | +6.3 | 73 | +5.4 | +4.1 | +3.4 | +5.2 | +4.5 | +18.0 | +nan | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | chandelier 4xATR (close) | 60 | 4 | 56 | +6.7 | +14.3 | +10.7 | +4.5 | +6.3 | 73 | +5.6 | +4.3 | +3.6 | +5.4 | +4.7 | +17.9 | +nan | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | (a) below 0.786 - 0.5ATR (close) | 60 | 6 | 54 | +10.0 | +21.5 | +12.2 | +3.3 | +5.5 | 70 | +4.4 | +3.1 | +2.3 | +4.1 | +3.4 | +17.4 | +5.0 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | (b) below swing origin - 0.5ATR (close) | 60 | 5 | 55 | +8.3 | +24.3 | +15.3 | +3.5 | +6.3 | 72 | +4.6 | +3.3 | +2.6 | +4.4 | +3.7 | +17.7 | +1.7 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | (c) below swing origin - 1.0ATR (close) | 60 | 4 | 56 | +6.7 | +26.4 | +16.6 | +3.9 | +6.3 | 73 | +5.1 | +3.7 | +3.0 | +4.9 | +4.2 | +17.9 | +0.0 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | (d) structure trail, confirmed higher-lows (close) | 60 | 8 | 52 | +13.3 | +24.3 | +15.3 | +3.3 | +6.3 | 72 | +4.3 | +3.0 | +2.3 | +4.1 | +3.4 | +17.1 | +1.7 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | fixed 3xATR (intraday) | 60 | 4 | 56 | +6.7 | +10.7 | +8.1 | +4.5 | +6.3 | 73 | +5.6 | +4.4 | +3.7 | +5.5 | +4.8 | +17.6 | +nan | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | chandelier 4xATR (intraday) | 60 | 5 | 55 | +8.3 | +14.3 | +10.7 | +4.4 | +6.3 | 73 | +5.5 | +4.2 | +3.6 | +5.3 | +4.6 | +17.4 | +nan | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | (a) below 0.786 - 0.5ATR (intraday) | 60 | 8 | 52 | +13.3 | +21.5 | +12.2 | +3.4 | +4.6 | 68 | +4.4 | +3.2 | +2.4 | +4.2 | +3.4 | +17.1 | +5.0 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | (b) below swing origin - 0.5ATR (intraday) | 60 | 8 | 52 | +13.3 | +24.3 | +15.3 | +3.2 | +4.6 | 68 | +4.2 | +2.9 | +2.2 | +3.9 | +3.2 | +17.2 | +1.7 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | (c) below swing origin - 1.0ATR (intraday) | 60 | 6 | 54 | +10.0 | +26.4 | +16.6 | +3.6 | +5.5 | 70 | +4.7 | +3.4 | +2.6 | +4.4 | +3.7 | +17.5 | +0.0 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | (d) structure trail, confirmed higher-lows (intraday) | 60 | 11 | 49 | +18.3 | +24.3 | +15.3 | +2.9 | +4.0 | 67 | +3.9 | +2.6 | +1.9 | +3.6 | +2.9 | +16.5 | +1.7 | robust to top-3 removal |
| All stock SHORT | hold, no stop | 173 | 0 | 173 | +0.0 | +nan | +nan | -0.9 | -1.2 | 46 | +0.5 | -1.2 | -1.5 | +0.2 | -0.1 | +16.8 | +nan | LUCK (edge gone w/o top tickers) |
| All stock SHORT | fixed 3xATR (close) | 173 | 32 | 141 | +18.5 | +10.7 | +8.0 | -0.5 | -1.2 | 46 | +0.8 | -0.8 | -1.1 | +0.5 | +0.2 | +15.2 | +nan | robust to top-3 removal |
| All stock SHORT | chandelier 4xATR (close) | 173 | 27 | 146 | +15.6 | +14.3 | +10.7 | -0.5 | -1.2 | 46 | +0.8 | -0.8 | -1.1 | +0.5 | +0.2 | +15.5 | +nan | robust to top-3 removal |
| All stock SHORT | (a) below 0.786 - 0.5ATR (close) | 173 | 68 | 105 | +39.3 | +7.7 | +2.1 | -1.0 | -1.4 | 41 | +0.1 | -1.3 | -1.6 | -0.2 | -0.5 | +13.2 | +26.0 | LUCK (edge gone w/o top tickers) |
| All stock SHORT | (b) below swing origin - 0.5ATR (close) | 173 | 62 | 111 | +35.8 | +10.2 | +2.9 | -1.1 | -1.5 | 43 | +0.1 | -1.4 | -1.7 | -0.2 | -0.5 | +13.9 | +18.5 | LUCK (edge gone w/o top tickers) |
| All stock SHORT | (c) below swing origin - 1.0ATR (close) | 173 | 44 | 129 | +25.4 | +12.1 | +3.3 | -0.5 | -1.2 | 45 | +0.7 | -0.8 | -1.1 | +0.4 | +0.1 | +14.4 | +15.6 | robust to top-3 removal |
| All stock SHORT | (d) structure trail, confirmed higher-lows (close) | 173 | 73 | 100 | +42.2 | +10.2 | +2.9 | -1.1 | -1.8 | 42 | +0.0 | -1.4 | -1.7 | -0.3 | -0.6 | +13.1 | +18.5 | LUCK (edge gone w/o top tickers) |
| All stock SHORT | fixed 3xATR (intraday) | 173 | 36 | 137 | +20.8 | +10.7 | +8.0 | -0.1 | -1.2 | 46 | +1.2 | -0.4 | -0.7 | +0.9 | +0.6 | +14.8 | +nan | robust to top-3 removal |
| All stock SHORT | chandelier 4xATR (intraday) | 173 | 35 | 138 | +20.2 | +14.3 | +10.7 | -0.3 | -1.2 | 46 | +1.1 | -0.6 | -0.9 | +0.8 | +0.5 | +14.9 | +nan | robust to top-3 removal |
| All stock SHORT | (a) below 0.786 - 0.5ATR (intraday) | 173 | 79 | 94 | +45.7 | +7.7 | +2.1 | -0.8 | -1.2 | 37 | +0.1 | -1.0 | -1.3 | -0.1 | -0.4 | +11.6 | +26.0 | LUCK (edge gone w/o top tickers) |
| All stock SHORT | (b) below swing origin - 0.5ATR (intraday) | 173 | 74 | 99 | +42.8 | +10.2 | +2.9 | -1.2 | -1.8 | 38 | -0.2 | -1.3 | -1.6 | -0.3 | -0.6 | +12.7 | +18.5 | no edge vs bench |
| All stock SHORT | (c) below swing origin - 1.0ATR (intraday) | 173 | 68 | 105 | +39.3 | +12.1 | +3.3 | -0.6 | -1.6 | 42 | +0.5 | -0.9 | -1.2 | +0.2 | -0.1 | +13.5 | +15.6 | LUCK (edge gone w/o top tickers) |
| All stock SHORT | (d) structure trail, confirmed higher-lows (intraday) | 173 | 83 | 90 | +48.0 | +10.2 | +2.9 | -1.1 | -1.8 | 38 | -0.2 | -1.3 | -1.6 | -0.3 | -0.6 | +12.0 | +18.5 | no edge vs bench |

### L. 4xATR stops + Fibonacci / Elliott profit targets (strict PIT, same legs/setups as K) vs hold / fixed 3xATR / chandelier 4xATR. stop_x/target_x/open_ = trades whose final exit was stop / target / still open (marked 2026-10-07); has_tgt = % with a valid target beyond entry; reached = % that touched (first) target; kept_going = % of target-reached trades where holding the whole position to 2026-10-07 would have been worth more; left_pp = avg pp given up vs holding, over target-reached trades
| segment | policy | N | stop_x | target_x | open_ | has_tgt | reached_pct | kept_going | left_pp | mean | median | hit | x_mkt | mean_wo_top1 | mean_wo_top3 | x_mkt_wo_top1 | x_mkt_wo_top3 | days | flag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Grok crypto LONG | hold, no stop | 254 | 0 | 0 | 254 | +nan | +nan | +nan | +nan | +36.8 | +32.0 | 93 | +14.8 | +36.2 | +30.7 | +14.0 | +8.6 | +53.3 | robust to top-3 removal |
| Grok crypto LONG | fixed 3xATR, no target (close) | 254 | 15 | 0 | 239 | +nan | +nan | +nan | +nan | +33.1 | +31.1 | 87 | +12.6 | +31.6 | +26.8 | +11.3 | +6.5 | +50.2 | robust to top-3 removal |
| Grok crypto LONG | chandelier 4xATR, no target (close) | 254 | 19 | 0 | 235 | +nan | +nan | +nan | +nan | +32.7 | +30.3 | 85 | +12.8 | +31.1 | +26.2 | +11.6 | +6.8 | +49.1 | robust to top-3 removal |
| Grok crypto LONG | fixed 4xATR + 1.272 ext full (close) | 254 | 4 | 226 | 24 | +96.9 | +89.0 | +83.2 | +24.1 | +14.6 | +13.5 | 94 | +4.8 | +13.4 | +14.0 | +4.0 | +2.9 | +15.8 | robust to top-3 removal |
| Grok crypto LONG | fixed 4xATR + 1.618 ext full (close) | 254 | 4 | 215 | 35 | +96.9 | +84.6 | +83.3 | +22.3 | +17.1 | +14.9 | 93 | +5.7 | +15.9 | +15.8 | +4.8 | +3.7 | +18.6 | robust to top-3 removal |
| Grok crypto LONG | fixed 4xATR + 2.618 ext full (close) | 254 | 4 | 182 | 68 | +96.9 | +71.7 | +60.4 | +10.8 | +28.3 | +26.1 | 91 | +9.5 | +26.4 | +26.0 | +8.2 | +7.1 | +29.2 | robust to top-3 removal |
| Grok crypto LONG | fixed 4xATR + 1/3 at each ext (close) | 254 | 4 | 160 | 90 | +96.9 | +89.0 | +77.9 | +17.2 | +20.7 | +19.4 | 92 | +1.6 | +19.4 | +17.9 | +0.8 | -0.5 | +32.2 | LUCK (edge gone w/o top tickers) |
| Grok crypto LONG | fixed 4xATR + Elliott w3/w5 target (close) | 254 | 4 | 63 | 187 | +30.7 | +24.8 | +68.3 | +13.6 | +32.7 | +28.9 | 91 | +13.5 | +31.3 | +26.9 | +12.6 | +8.4 | +43.3 | robust to top-3 removal |
| Grok crypto LONG | chandelier 4xATR + 1.272 ext full (close) | 254 | 14 | 216 | 24 | +96.9 | +85.0 | +81.9 | +24.1 | +13.5 | +13.2 | 90 | +4.5 | +12.2 | +12.2 | +3.8 | +2.5 | +14.7 | robust to top-3 removal |
| Grok crypto LONG | chandelier 4xATR + 1.618 ext full (close) | 254 | 16 | 202 | 36 | +96.9 | +79.5 | +83.7 | +22.1 | +15.4 | +14.1 | 88 | +5.2 | +14.1 | +13.1 | +4.4 | +3.1 | +17.2 | robust to top-3 removal |
| Grok crypto LONG | chandelier 4xATR + 2.618 ext full (close) | 254 | 19 | 167 | 68 | +96.9 | +65.7 | +62.3 | +11.4 | +25.2 | +21.4 | 85 | +8.1 | +23.1 | +21.9 | +6.7 | +5.2 | +27.3 | robust to top-3 removal |
| Grok crypto LONG | chandelier 4xATR + 1/3 at each ext (close) | 254 | 19 | 146 | 89 | +96.9 | +85.0 | +78.7 | +17.9 | +18.7 | +17.8 | 87 | +1.2 | +17.2 | +16.1 | +0.4 | -0.9 | +30.2 | LUCK (edge gone w/o top tickers) |
| Grok crypto LONG | chandelier 4xATR + Elliott w3/w5 target (close) | 254 | 17 | 55 | 182 | +30.7 | +21.7 | +74.5 | +14.0 | +29.9 | +27.3 | 86 | +12.3 | +27.9 | +24.3 | +11.0 | +7.5 | +41.1 | robust to top-3 removal |
| Grok crypto LONG | chandelier 4xATR + 1/3 at 1.618, rest chandelier (close) | 254 | 19 | 0 | 235 | +96.9 | +79.5 | +84.2 | +7.6 | +26.9 | +25.2 | 87 | +7.0 | +25.8 | +22.4 | +6.3 | +3.0 | +49.1 | robust to top-3 removal |
| Grok crypto LONG | chandelier 4xATR + 1/2 at 1.618, rest chandelier (close) | 254 | 19 | 0 | 235 | +96.9 | +79.5 | +84.2 | +11.3 | +24.0 | +22.7 | 88 | +4.2 | +22.5 | +19.8 | +2.9 | +0.9 | +49.1 | robust to top-3 removal |
| Grok crypto LONG | fixed 3xATR, no target (intraday) | 254 | 19 | 0 | 235 | +nan | +nan | +nan | +nan | +32.5 | +30.9 | 85 | +12.4 | +31.0 | +26.0 | +11.1 | +6.3 | +49.4 | robust to top-3 removal |
| Grok crypto LONG | chandelier 4xATR, no target (intraday) | 254 | 45 | 0 | 209 | +nan | +nan | +nan | +nan | +29.2 | +28.5 | 82 | +10.9 | +26.9 | +21.8 | +9.2 | +4.4 | +46.3 | robust to top-3 removal |
| Grok crypto LONG | fixed 4xATR + 1.272 ext full (intraday) | 254 | 5 | 235 | 14 | +96.9 | +92.5 | +81.7 | +28.2 | +9.9 | +7.9 | 96 | +1.4 | +9.9 | +8.4 | +0.7 | -0.2 | +13.6 | LUCK (edge gone w/o top tickers) |
| Grok crypto LONG | fixed 4xATR + 1.618 ext full (intraday) | 254 | 5 | 223 | 26 | +96.9 | +87.8 | +82.1 | +24.9 | +14.0 | +11.4 | 94 | +3.5 | +12.7 | +12.3 | +2.6 | +1.4 | +17.1 | robust to top-3 removal |
| Grok crypto LONG | fixed 4xATR + 2.618 ext full (intraday) | 254 | 5 | 190 | 59 | +96.9 | +74.8 | +74.7 | +14.8 | +24.8 | +23.6 | 92 | +7.3 | +22.9 | +21.9 | +6.1 | +4.7 | +26.7 | robust to top-3 removal |
| Grok crypto LONG | fixed 4xATR + 1/3 at each ext (intraday) | 254 | 5 | 162 | 87 | +96.9 | +92.5 | +77.0 | +20.4 | +17.1 | +14.7 | 92 | -0.8 | +15.7 | +14.4 | -1.6 | -2.7 | +30.0 | no edge vs bench |
| Grok crypto LONG | fixed 4xATR + Elliott w3/w5 target (intraday) | 254 | 5 | 63 | 186 | +30.7 | +24.8 | +71.4 | +19.7 | +31.0 | +28.0 | 91 | +12.3 | +29.3 | +24.9 | +11.2 | +6.9 | +42.6 | robust to top-3 removal |
| Grok crypto LONG | chandelier 4xATR + 1.272 ext full (intraday) | 254 | 15 | 224 | 15 | +96.9 | +88.2 | +80.8 | +28.0 | +9.0 | +7.4 | 93 | +1.1 | +9.0 | +7.4 | +0.5 | -0.5 | +13.2 | LUCK (edge gone w/o top tickers) |
| Grok crypto LONG | chandelier 4xATR + 1.618 ext full (intraday) | 254 | 21 | 206 | 27 | +96.9 | +81.1 | +80.6 | +25.0 | +12.3 | +10.7 | 89 | +3.2 | +10.9 | +9.8 | +2.2 | +0.9 | +15.9 | robust to top-3 removal |
| Grok crypto LONG | chandelier 4xATR + 2.618 ext full (intraday) | 254 | 25 | 170 | 59 | +96.9 | +66.9 | +76.5 | +15.5 | +21.5 | +19.0 | 85 | +5.7 | +19.4 | +17.3 | +4.5 | +2.6 | +24.8 | robust to top-3 removal |
| Grok crypto LONG | chandelier 4xATR + 1/3 at each ext (intraday) | 254 | 30 | 143 | 81 | +96.9 | +88.2 | +78.1 | +21.4 | +14.8 | +13.0 | 85 | -1.0 | +13.3 | +12.2 | -1.8 | -2.8 | +27.5 | no edge vs bench |
| Grok crypto LONG | chandelier 4xATR + Elliott w3/w5 target (intraday) | 254 | 37 | 55 | 162 | +30.7 | +21.7 | +74.5 | +19.7 | +25.8 | +22.0 | 83 | +9.7 | +23.0 | +19.1 | +8.0 | +4.3 | +38.3 | robust to top-3 removal |
| Grok crypto LONG | chandelier 4xATR + 1/3 at 1.618, rest chandelier (intraday) | 254 | 45 | 0 | 209 | +96.9 | +81.1 | +81.1 | +11.1 | +23.6 | +23.0 | 84 | +5.2 | +21.7 | +18.4 | +3.6 | +1.0 | +46.3 | robust to top-3 removal |
| Grok crypto LONG | chandelier 4xATR + 1/2 at 1.618, rest chandelier (intraday) | 254 | 45 | 0 | 209 | +96.9 | +81.1 | +81.1 | +14.6 | +20.7 | +19.7 | 86 | +2.4 | +19.2 | +15.8 | +1.1 | -1.0 | +46.3 | LUCK (edge gone w/o top tickers) |
| All stock LONG | hold, no stop | 228 | 0 | 0 | 228 | +nan | +nan | +nan | +nan | +3.7 | +0.5 | 56 | +2.2 | +3.0 | +2.0 | +1.4 | +0.5 | +19.2 | robust to top-3 removal |
| All stock LONG | fixed 3xATR, no target (close) | 228 | 28 | 0 | 200 | +nan | +nan | +nan | +nan | +4.0 | +0.4 | 55 | +2.6 | +3.2 | +2.3 | +1.9 | +0.9 | +17.5 | robust to top-3 removal |
| All stock LONG | chandelier 4xATR, no target (close) | 228 | 36 | 0 | 192 | +nan | +nan | +nan | +nan | +3.7 | +0.4 | 55 | +2.4 | +3.0 | +2.0 | +1.7 | +0.7 | +17.2 | robust to top-3 removal |
| All stock LONG | fixed 4xATR + 1.272 ext full (close) | 228 | 17 | 74 | 137 | +98.7 | +32.5 | +41.9 | +1.9 | +3.3 | +1.3 | 60 | +2.1 | +2.8 | +2.1 | +1.7 | +1.0 | +14.1 | robust to top-3 removal |
| All stock LONG | fixed 4xATR + 1.618 ext full (close) | 228 | 18 | 47 | 163 | +98.7 | +20.6 | +57.4 | +2.3 | +3.4 | +1.0 | 59 | +2.2 | +3.0 | +2.3 | +1.8 | +1.1 | +15.3 | robust to top-3 removal |
| All stock LONG | fixed 4xATR + 2.618 ext full (close) | 228 | 18 | 16 | 194 | +98.7 | +7.0 | +43.8 | +4.7 | +3.6 | +0.5 | 57 | +2.2 | +3.1 | +2.1 | +1.7 | +0.7 | +17.5 | robust to top-3 removal |
| All stock LONG | fixed 4xATR + 1/3 at each ext (close) | 228 | 18 | 10 | 200 | +98.7 | +32.5 | +39.2 | +1.3 | +3.5 | +0.7 | 58 | +2.0 | +3.0 | +2.2 | +1.6 | +0.8 | +17.9 | robust to top-3 removal |
| All stock LONG | fixed 4xATR + Elliott w3/w5 target (close) | 228 | 18 | 17 | 193 | +31.1 | +7.5 | +47.1 | +0.6 | +3.9 | +0.6 | 57 | +2.5 | +3.1 | +2.2 | +1.8 | +0.9 | +17.7 | robust to top-3 removal |
| All stock LONG | chandelier 4xATR + 1.272 ext full (close) | 228 | 28 | 73 | 127 | +98.7 | +32.0 | +42.5 | +2.0 | +2.9 | +1.1 | 59 | +1.8 | +2.5 | +1.8 | +1.4 | +0.7 | +13.5 | robust to top-3 removal |
| All stock LONG | chandelier 4xATR + 1.618 ext full (close) | 228 | 29 | 46 | 153 | +98.7 | +20.2 | +58.7 | +2.5 | +3.2 | +0.6 | 58 | +2.0 | +2.7 | +2.0 | +1.6 | +0.9 | +14.6 | robust to top-3 removal |
| All stock LONG | chandelier 4xATR + 2.618 ext full (close) | 228 | 35 | 16 | 177 | +98.7 | +7.0 | +43.8 | +4.7 | +3.3 | +0.4 | 55 | +2.0 | +2.8 | +1.8 | +1.6 | +0.6 | +16.4 | robust to top-3 removal |
| All stock LONG | chandelier 4xATR + 1/3 at each ext (close) | 228 | 35 | 10 | 183 | +98.7 | +32.0 | +41.1 | +1.3 | +3.2 | +0.6 | 56 | +1.9 | +2.7 | +1.9 | +1.4 | +0.6 | +16.8 | robust to top-3 removal |
| All stock LONG | chandelier 4xATR + Elliott w3/w5 target (close) | 228 | 35 | 17 | 176 | +31.1 | +7.5 | +47.1 | +0.6 | +3.8 | +0.5 | 57 | +2.5 | +3.0 | +2.1 | +1.8 | +0.9 | +16.5 | robust to top-3 removal |
| All stock LONG | chandelier 4xATR + 1/3 at 1.618, rest chandelier (close) | 228 | 36 | 0 | 192 | +98.7 | +20.2 | +60.9 | +0.6 | +3.5 | +0.5 | 55 | +2.2 | +3.0 | +2.1 | +1.7 | +0.8 | +17.2 | robust to top-3 removal |
| All stock LONG | chandelier 4xATR + 1/2 at 1.618, rest chandelier (close) | 228 | 36 | 0 | 192 | +98.7 | +20.2 | +60.9 | +1.1 | +3.4 | +0.6 | 57 | +2.1 | +3.0 | +2.1 | +1.7 | +0.8 | +17.2 | robust to top-3 removal |
| All stock LONG | fixed 3xATR, no target (intraday) | 228 | 31 | 0 | 197 | +nan | +nan | +nan | +nan | +4.0 | +0.4 | 55 | +2.7 | +3.3 | +2.3 | +2.0 | +1.0 | +17.1 | robust to top-3 removal |
| All stock LONG | chandelier 4xATR, no target (intraday) | 228 | 40 | 0 | 188 | +nan | +nan | +nan | +nan | +3.8 | +0.4 | 55 | +2.6 | +3.1 | +2.1 | +1.8 | +0.9 | +16.9 | robust to top-3 removal |
| All stock LONG | fixed 4xATR + 1.272 ext full (intraday) | 228 | 21 | 94 | 113 | +98.7 | +41.2 | +52.1 | +1.6 | +3.2 | +1.3 | 64 | +2.2 | +2.8 | +2.2 | +1.8 | +1.3 | +12.5 | robust to top-3 removal |
| All stock LONG | fixed 4xATR + 1.618 ext full (intraday) | 228 | 21 | 61 | 146 | +98.7 | +26.8 | +45.9 | -1.2 | +4.2 | +1.2 | 62 | +3.0 | +3.7 | +3.0 | +2.6 | +1.9 | +14.2 | robust to top-3 removal |
| All stock LONG | fixed 4xATR + 2.618 ext full (intraday) | 228 | 23 | 24 | 181 | +98.7 | +10.5 | +29.2 | +1.7 | +3.7 | +0.6 | 58 | +2.4 | +3.2 | +2.3 | +1.9 | +1.0 | +16.6 | robust to top-3 removal |
| All stock LONG | fixed 4xATR + 1/3 at each ext (intraday) | 228 | 23 | 14 | 191 | +98.7 | +41.2 | +45.7 | +0.6 | +3.6 | +1.1 | 60 | +2.3 | +3.2 | +2.4 | +1.9 | +1.1 | +17.4 | robust to top-3 removal |
| All stock LONG | fixed 4xATR + Elliott w3/w5 target (intraday) | 228 | 23 | 17 | 188 | +31.1 | +7.5 | +52.9 | +1.5 | +3.8 | +0.6 | 57 | +2.5 | +3.1 | +2.1 | +1.7 | +0.8 | +17.0 | robust to top-3 removal |
| All stock LONG | chandelier 4xATR + 1.272 ext full (intraday) | 228 | 29 | 94 | 105 | +98.7 | +41.2 | +52.1 | +1.6 | +3.0 | +1.2 | 62 | +2.0 | +2.6 | +2.0 | +1.7 | +1.1 | +12.2 | robust to top-3 removal |
| All stock LONG | chandelier 4xATR + 1.618 ext full (intraday) | 228 | 31 | 60 | 137 | +98.7 | +26.3 | +46.7 | -1.2 | +3.9 | +1.0 | 60 | +2.8 | +3.4 | +2.6 | +2.4 | +1.6 | +13.8 | robust to top-3 removal |
| All stock LONG | chandelier 4xATR + 2.618 ext full (intraday) | 228 | 37 | 24 | 167 | +98.7 | +10.5 | +29.2 | +1.7 | +3.6 | +0.5 | 57 | +2.4 | +3.1 | +2.2 | +1.9 | +1.0 | +15.8 | robust to top-3 removal |
| All stock LONG | chandelier 4xATR + 1/3 at each ext (intraday) | 228 | 39 | 14 | 175 | +98.7 | +41.2 | +47.9 | +0.6 | +3.4 | +0.8 | 58 | +2.2 | +3.0 | +2.2 | +1.8 | +1.0 | +16.4 | robust to top-3 removal |
| All stock LONG | chandelier 4xATR + Elliott w3/w5 target (intraday) | 228 | 38 | 19 | 171 | +31.1 | +8.3 | +47.4 | +0.7 | +3.9 | +0.6 | 57 | +2.7 | +3.1 | +2.2 | +2.0 | +1.1 | +16.0 | robust to top-3 removal |
| All stock LONG | chandelier 4xATR + 1/3 at 1.618, rest chandelier (intraday) | 228 | 40 | 0 | 188 | +98.7 | +26.3 | +48.3 | -1.0 | +3.8 | +0.5 | 55 | +2.6 | +3.3 | +2.4 | +2.1 | +1.2 | +16.9 | robust to top-3 removal |
| All stock LONG | chandelier 4xATR + 1/2 at 1.618, rest chandelier (intraday) | 228 | 40 | 0 | 188 | +98.7 | +26.3 | +48.3 | -1.0 | +3.8 | +0.6 | 57 | +2.6 | +3.4 | +2.5 | +2.2 | +1.3 | +16.9 | robust to top-3 removal |
| Rule-filtered stock LONG | hold, no stop | 115 | 0 | 0 | 115 | +nan | +nan | +nan | +nan | +5.0 | +1.1 | 63 | +3.5 | +3.6 | +1.9 | +2.1 | +0.3 | +19.8 | robust to top-3 removal |
| Rule-filtered stock LONG | fixed 3xATR, no target (close) | 115 | 12 | 0 | 103 | +nan | +nan | +nan | +nan | +5.5 | +1.1 | 63 | +4.1 | +4.1 | +2.3 | +2.7 | +0.9 | +17.9 | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 4xATR, no target (close) | 115 | 19 | 0 | 96 | +nan | +nan | +nan | +nan | +5.3 | +0.6 | 60 | +4.0 | +3.9 | +2.2 | +2.6 | +0.8 | +17.7 | robust to top-3 removal |
| Rule-filtered stock LONG | fixed 4xATR + 1.272 ext full (close) | 115 | 10 | 48 | 57 | +98.3 | +41.7 | +41.7 | +3.2 | +4.0 | +2.0 | 67 | +3.0 | +3.3 | +2.3 | +2.3 | +1.3 | +14.5 | robust to top-3 removal |
| Rule-filtered stock LONG | fixed 4xATR + 1.618 ext full (close) | 115 | 10 | 32 | 73 | +98.3 | +27.8 | +53.1 | +3.8 | +4.3 | +1.8 | 66 | +3.2 | +3.7 | +2.6 | +2.6 | +1.5 | +15.6 | robust to top-3 removal |
| Rule-filtered stock LONG | fixed 4xATR + 2.618 ext full (close) | 115 | 10 | 12 | 93 | +98.3 | +10.4 | +50.0 | +8.2 | +4.5 | +1.4 | 64 | +3.1 | +3.7 | +2.4 | +2.3 | +1.1 | +17.5 | robust to top-3 removal |
| Rule-filtered stock LONG | fixed 4xATR + 1/3 at each ext (close) | 115 | 10 | 8 | 97 | +98.3 | +41.7 | +37.5 | +2.3 | +4.4 | +1.8 | 63 | +3.0 | +3.7 | +2.6 | +2.4 | +1.3 | +17.9 | robust to top-3 removal |
| Rule-filtered stock LONG | fixed 4xATR + Elliott w3/w5 target (close) | 115 | 10 | 14 | 91 | +40.9 | +12.2 | +50.0 | +1.1 | +5.2 | +1.4 | 64 | +3.9 | +3.8 | +2.0 | +2.5 | +0.7 | +17.6 | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 4xATR + 1.272 ext full (close) | 115 | 15 | 48 | 52 | +98.3 | +41.7 | +41.7 | +3.2 | +3.8 | +2.0 | 64 | +2.9 | +3.1 | +2.1 | +2.2 | +1.2 | +13.9 | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 4xATR + 1.618 ext full (close) | 115 | 15 | 32 | 68 | +98.3 | +27.8 | +53.1 | +3.8 | +4.1 | +1.5 | 63 | +3.1 | +3.6 | +2.4 | +2.5 | +1.4 | +15.0 | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 4xATR + 2.618 ext full (close) | 115 | 18 | 12 | 85 | +98.3 | +10.4 | +50.0 | +8.2 | +4.3 | +1.0 | 61 | +3.1 | +3.5 | +2.3 | +2.3 | +1.1 | +16.5 | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 4xATR + 1/3 at each ext (close) | 115 | 18 | 8 | 89 | +98.3 | +41.7 | +39.6 | +2.3 | +4.2 | +1.4 | 61 | +3.0 | +3.6 | +2.5 | +2.3 | +1.2 | +17.0 | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 4xATR + Elliott w3/w5 target (close) | 115 | 18 | 14 | 83 | +40.9 | +12.2 | +50.0 | +1.1 | +5.3 | +1.3 | 63 | +4.2 | +3.9 | +2.2 | +2.8 | +1.0 | +16.7 | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 4xATR + 1/3 at 1.618, rest chandelier (close) | 115 | 19 | 0 | 96 | +98.3 | +27.8 | +56.2 | +0.9 | +4.9 | +1.0 | 60 | +3.6 | +3.9 | +2.5 | +2.6 | +1.2 | +17.7 | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 4xATR + 1/2 at 1.618, rest chandelier (close) | 115 | 19 | 0 | 96 | +98.3 | +27.8 | +56.2 | +1.6 | +4.7 | +1.0 | 61 | +3.4 | +3.9 | +2.6 | +2.6 | +1.3 | +17.7 | robust to top-3 removal |
| Rule-filtered stock LONG | fixed 3xATR, no target (intraday) | 115 | 14 | 0 | 101 | +nan | +nan | +nan | +nan | +5.5 | +1.1 | 63 | +4.2 | +4.1 | +2.4 | +2.8 | +1.0 | +17.4 | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 4xATR, no target (intraday) | 115 | 21 | 0 | 94 | +nan | +nan | +nan | +nan | +5.5 | +0.6 | 60 | +4.3 | +4.1 | +2.3 | +2.8 | +1.1 | +17.4 | robust to top-3 removal |
| Rule-filtered stock LONG | fixed 4xATR + 1.272 ext full (intraday) | 115 | 12 | 59 | 44 | +98.3 | +51.3 | +52.5 | +3.6 | +3.4 | +1.9 | 70 | +2.5 | +3.0 | +2.1 | +2.0 | +1.1 | +12.4 | robust to top-3 removal |
| Rule-filtered stock LONG | fixed 4xATR + 1.618 ext full (intraday) | 115 | 12 | 40 | 63 | +98.3 | +34.8 | +45.0 | +1.1 | +4.9 | +2.0 | 68 | +3.9 | +4.3 | +3.0 | +3.2 | +1.9 | +14.4 | robust to top-3 removal |
| Rule-filtered stock LONG | fixed 4xATR + 2.618 ext full (intraday) | 115 | 12 | 14 | 89 | +98.3 | +12.2 | +42.9 | +8.4 | +4.2 | +1.8 | 64 | +3.0 | +3.6 | +2.4 | +2.3 | +1.1 | +16.6 | robust to top-3 removal |
| Rule-filtered stock LONG | fixed 4xATR + 1/3 at each ext (intraday) | 115 | 12 | 9 | 94 | +98.3 | +51.3 | +45.8 | +2.2 | +4.2 | +1.8 | 65 | +2.8 | +3.6 | +2.6 | +2.3 | +1.2 | +17.1 | robust to top-3 removal |
| Rule-filtered stock LONG | fixed 4xATR + Elliott w3/w5 target (intraday) | 115 | 12 | 14 | 89 | +40.9 | +12.2 | +57.1 | +1.9 | +5.0 | +1.8 | 63 | +3.8 | +3.6 | +1.9 | +2.4 | +0.6 | +16.6 | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 4xATR + 1.272 ext full (intraday) | 115 | 17 | 59 | 39 | +98.3 | +51.3 | +52.5 | +3.6 | +3.4 | +1.9 | 67 | +2.6 | +2.9 | +2.1 | +2.1 | +1.2 | +12.2 | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 4xATR + 1.618 ext full (intraday) | 115 | 17 | 40 | 58 | +98.3 | +34.8 | +45.0 | +1.1 | +4.9 | +2.0 | 65 | +3.9 | +4.2 | +3.0 | +3.3 | +2.0 | +14.2 | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 4xATR + 2.618 ext full (intraday) | 115 | 20 | 14 | 81 | +98.3 | +12.2 | +42.9 | +8.4 | +4.3 | +1.0 | 61 | +3.2 | +3.7 | +2.5 | +2.5 | +1.4 | +16.1 | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 4xATR + 1/3 at each ext (intraday) | 115 | 20 | 9 | 86 | +98.3 | +51.3 | +47.5 | +2.1 | +4.2 | +1.5 | 62 | +3.0 | +3.6 | +2.6 | +2.4 | +1.4 | +16.5 | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 4xATR + Elliott w3/w5 target (intraday) | 115 | 20 | 16 | 79 | +40.9 | +13.9 | +50.0 | +0.8 | +5.5 | +1.1 | 63 | +4.5 | +4.1 | +2.4 | +3.1 | +1.3 | +16.0 | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 4xATR + 1/3 at 1.618, rest chandelier (intraday) | 115 | 21 | 0 | 94 | +98.3 | +34.8 | +47.5 | -0.1 | +5.3 | +1.5 | 60 | +4.1 | +4.3 | +3.0 | +3.1 | +1.7 | +17.4 | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 4xATR + 1/2 at 1.618, rest chandelier (intraday) | 115 | 21 | 0 | 94 | +98.3 | +34.8 | +47.5 | +0.2 | +5.2 | +1.6 | 60 | +4.0 | +4.4 | +3.1 | +3.2 | +1.9 | +17.4 | robust to top-3 removal |
| Perplexity stock LONG | hold, no stop | 57 | 0 | 0 | 57 | +nan | +nan | +nan | +nan | +6.7 | +1.7 | 61 | +5.8 | +3.8 | +1.2 | +2.9 | +0.3 | +23.2 | robust to top-3 removal |
| Perplexity stock LONG | fixed 3xATR, no target (close) | 57 | 10 | 0 | 47 | +nan | +nan | +nan | +nan | +7.1 | +1.2 | 58 | +6.6 | +4.2 | +1.7 | +3.7 | +1.2 | +20.6 | robust to top-3 removal |
| Perplexity stock LONG | chandelier 4xATR, no target (close) | 57 | 15 | 0 | 42 | +nan | +nan | +nan | +nan | +6.4 | +0.6 | 54 | +5.9 | +3.5 | +0.9 | +3.1 | +0.4 | +20.2 | robust to top-3 removal |
| Perplexity stock LONG | fixed 4xATR + 1.272 ext full (close) | 57 | 7 | 16 | 34 | +98.2 | +28.1 | +43.8 | +10.0 | +4.2 | +1.8 | 61 | +3.7 | +3.1 | +1.8 | +2.6 | +1.2 | +18.7 | robust to top-3 removal |
| Perplexity stock LONG | fixed 4xATR + 1.618 ext full (close) | 57 | 7 | 10 | 40 | +98.2 | +17.5 | +70.0 | +15.2 | +4.4 | +1.7 | 61 | +3.9 | +3.2 | +2.0 | +2.7 | +1.4 | +19.3 | robust to top-3 removal |
| Perplexity stock LONG | fixed 4xATR + 2.618 ext full (close) | 57 | 7 | 6 | 44 | +98.2 | +10.5 | +83.3 | +19.8 | +4.9 | +1.7 | 61 | +4.3 | +3.4 | +1.8 | +2.7 | +1.1 | +20.7 | robust to top-3 removal |
| Perplexity stock LONG | fixed 4xATR + 1/3 at each ext (close) | 57 | 7 | 6 | 44 | +98.2 | +28.1 | +43.8 | +9.0 | +4.5 | +1.8 | 61 | +3.9 | +3.2 | +2.0 | +2.6 | +1.3 | +20.7 | robust to top-3 removal |
| Perplexity stock LONG | fixed 4xATR + Elliott w3/w5 target (close) | 57 | 7 | 4 | 46 | +29.8 | +7.0 | +75.0 | +2.8 | +6.8 | +1.7 | 61 | +6.2 | +4.0 | +1.4 | +3.4 | +0.8 | +20.6 | robust to top-3 removal |
| Perplexity stock LONG | chandelier 4xATR + 1.272 ext full (close) | 57 | 13 | 15 | 29 | +98.2 | +26.3 | +46.7 | +11.0 | +3.7 | +0.8 | 56 | +3.3 | +2.5 | +1.2 | +2.2 | +0.8 | +17.8 | robust to top-3 removal |
| Perplexity stock LONG | chandelier 4xATR + 1.618 ext full (close) | 57 | 13 | 9 | 35 | +98.2 | +15.8 | +77.8 | +17.4 | +3.8 | +0.8 | 56 | +3.5 | +2.7 | +1.4 | +2.3 | +1.0 | +18.3 | robust to top-3 removal |
| Perplexity stock LONG | chandelier 4xATR + 2.618 ext full (close) | 57 | 15 | 6 | 36 | +98.2 | +10.5 | +83.3 | +19.8 | +4.3 | +0.6 | 54 | +3.9 | +2.7 | +1.1 | +2.3 | +0.6 | +19.2 | robust to top-3 removal |
| Perplexity stock LONG | chandelier 4xATR + 1/3 at each ext (close) | 57 | 15 | 6 | 36 | +98.2 | +26.3 | +53.3 | +10.1 | +3.9 | +0.8 | 56 | +3.6 | +2.6 | +1.4 | +2.2 | +0.9 | +19.2 | robust to top-3 removal |
| Perplexity stock LONG | chandelier 4xATR + Elliott w3/w5 target (close) | 57 | 14 | 4 | 39 | +29.8 | +7.0 | +75.0 | +2.8 | +6.5 | +0.8 | 56 | +6.1 | +3.7 | +1.1 | +3.2 | +0.6 | +19.5 | robust to top-3 removal |
| Perplexity stock LONG | chandelier 4xATR + 1/3 at 1.618, rest chandelier (close) | 57 | 15 | 0 | 42 | +98.2 | +15.8 | +88.9 | +6.7 | +5.5 | +0.6 | 54 | +5.1 | +3.5 | +1.1 | +3.0 | +0.6 | +20.2 | robust to top-3 removal |
| Perplexity stock LONG | chandelier 4xATR + 1/2 at 1.618, rest chandelier (close) | 57 | 15 | 0 | 42 | +98.2 | +15.8 | +88.9 | +9.4 | +5.1 | +0.6 | 54 | +4.7 | +3.5 | +1.2 | +3.0 | +0.7 | +20.2 | robust to top-3 removal |
| Perplexity stock LONG | fixed 3xATR, no target (intraday) | 57 | 11 | 0 | 46 | +nan | +nan | +nan | +nan | +7.1 | +1.2 | 58 | +6.6 | +4.2 | +1.7 | +3.7 | +1.2 | +20.2 | robust to top-3 removal |
| Perplexity stock LONG | chandelier 4xATR, no target (intraday) | 57 | 17 | 0 | 40 | +nan | +nan | +nan | +nan | +6.5 | +0.6 | 54 | +6.1 | +3.6 | +1.0 | +3.3 | +0.6 | +19.7 | robust to top-3 removal |
| Perplexity stock LONG | fixed 4xATR + 1.272 ext full (intraday) | 57 | 8 | 20 | 29 | +98.2 | +35.1 | +75.0 | +10.0 | +3.6 | +1.8 | 63 | +3.3 | +2.9 | +1.7 | +2.5 | +1.2 | +16.9 | robust to top-3 removal |
| Perplexity stock LONG | fixed 4xATR + 1.618 ext full (intraday) | 57 | 8 | 11 | 38 | +98.2 | +19.3 | +63.6 | +12.7 | +4.7 | +1.8 | 63 | +4.2 | +3.7 | +2.4 | +3.1 | +1.9 | +19.0 | robust to top-3 removal |
| Perplexity stock LONG | fixed 4xATR + 2.618 ext full (intraday) | 57 | 8 | 6 | 43 | +98.2 | +10.5 | +83.3 | +24.2 | +4.6 | +1.7 | 61 | +4.1 | +3.3 | +1.9 | +2.7 | +1.2 | +20.5 | robust to top-3 removal |
| Perplexity stock LONG | fixed 4xATR + 1/3 at each ext (intraday) | 57 | 8 | 6 | 43 | +98.2 | +35.1 | +70.0 | +8.1 | +4.3 | +1.8 | 63 | +3.8 | +3.3 | +2.1 | +2.7 | +1.4 | +20.5 | robust to top-3 removal |
| Perplexity stock LONG | fixed 4xATR + Elliott w3/w5 target (intraday) | 57 | 8 | 4 | 45 | +29.8 | +7.0 | +75.0 | +4.1 | +6.9 | +1.7 | 61 | +6.3 | +4.0 | +1.5 | +3.5 | +0.9 | +20.0 | robust to top-3 removal |
| Perplexity stock LONG | chandelier 4xATR + 1.272 ext full (intraday) | 57 | 14 | 20 | 23 | +98.2 | +35.1 | +75.0 | +10.0 | +3.5 | +1.2 | 58 | +3.3 | +2.8 | +1.5 | +2.6 | +1.3 | +15.7 | robust to top-3 removal |
| Perplexity stock LONG | chandelier 4xATR + 1.618 ext full (intraday) | 57 | 15 | 10 | 32 | +98.2 | +17.5 | +70.0 | +14.1 | +4.2 | +1.1 | 58 | +3.9 | +3.1 | +1.8 | +2.8 | +1.6 | +17.7 | robust to top-3 removal |
| Perplexity stock LONG | chandelier 4xATR + 2.618 ext full (intraday) | 57 | 17 | 6 | 34 | +98.2 | +10.5 | +83.3 | +24.2 | +3.9 | +0.6 | 54 | +3.7 | +2.6 | +1.1 | +2.3 | +0.8 | +18.6 | robust to top-3 removal |
| Perplexity stock LONG | chandelier 4xATR + 1/3 at each ext (intraday) | 57 | 17 | 6 | 34 | +98.2 | +35.1 | +75.0 | +8.9 | +3.8 | +1.1 | 56 | +3.6 | +2.8 | +1.6 | +2.6 | +1.2 | +18.6 | robust to top-3 removal |
| Perplexity stock LONG | chandelier 4xATR + Elliott w3/w5 target (intraday) | 57 | 16 | 4 | 37 | +29.8 | +7.0 | +75.0 | +4.1 | +6.5 | +0.9 | 56 | +6.2 | +3.6 | +1.0 | +3.3 | +0.7 | +18.5 | robust to top-3 removal |
| Perplexity stock LONG | chandelier 4xATR + 1/3 at 1.618, rest chandelier (intraday) | 57 | 17 | 0 | 40 | +98.2 | +17.5 | +80.0 | +5.4 | +5.7 | +0.6 | 54 | +5.4 | +3.7 | +1.3 | +3.3 | +1.0 | +19.7 | robust to top-3 removal |
| Perplexity stock LONG | chandelier 4xATR + 1/2 at 1.618, rest chandelier (intraday) | 57 | 17 | 0 | 40 | +98.2 | +17.5 | +80.0 | +7.6 | +5.3 | +0.9 | 56 | +5.0 | +3.7 | +1.5 | +3.4 | +1.1 | +19.7 | robust to top-3 removal |
| Grok stock LONG | hold, no stop | 131 | 0 | 0 | 131 | +nan | +nan | +nan | +nan | +2.0 | +0.3 | 54 | +0.2 | +1.2 | +0.4 | -0.6 | -1.5 | +17.4 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | fixed 3xATR, no target (close) | 131 | 16 | 0 | 115 | +nan | +nan | +nan | +nan | +2.2 | +0.3 | 54 | +0.6 | +1.5 | +0.7 | -0.1 | -1.0 | +16.0 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | chandelier 4xATR, no target (close) | 131 | 18 | 0 | 113 | +nan | +nan | +nan | +nan | +2.3 | +0.4 | 55 | +0.7 | +1.5 | +0.7 | -0.1 | -0.9 | +15.7 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | fixed 4xATR + 1.272 ext full (close) | 131 | 9 | 46 | 76 | +98.5 | +35.1 | +41.3 | -1.1 | +2.5 | +1.3 | 60 | +1.1 | +2.2 | +1.5 | +0.8 | +0.1 | +12.1 | robust to top-3 removal |
| Grok stock LONG | fixed 4xATR + 1.618 ext full (close) | 131 | 10 | 30 | 91 | +98.5 | +22.9 | +50.0 | -2.1 | +2.6 | +0.6 | 59 | +1.1 | +2.1 | +1.3 | +0.6 | -0.2 | +13.6 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | fixed 4xATR + 2.618 ext full (close) | 131 | 10 | 8 | 113 | +98.5 | +6.1 | +12.5 | -5.8 | +2.5 | +0.4 | 56 | +0.8 | +1.9 | +1.1 | +0.2 | -0.6 | +16.1 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | fixed 4xATR + 1/3 at each ext (close) | 131 | 10 | 3 | 118 | +98.5 | +35.1 | +37.0 | -1.4 | +2.6 | +0.6 | 56 | +0.9 | +2.2 | +1.5 | +0.5 | -0.3 | +16.5 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | fixed 4xATR + Elliott w3/w5 target (close) | 131 | 10 | 10 | 111 | +33.6 | +7.6 | +40.0 | -0.1 | +2.1 | +0.4 | 56 | +0.5 | +1.4 | +0.6 | -0.2 | -1.1 | +16.1 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | chandelier 4xATR + 1.272 ext full (close) | 131 | 13 | 46 | 72 | +98.5 | +35.1 | +41.3 | -1.1 | +2.2 | +1.3 | 60 | +1.0 | +1.9 | +1.2 | +0.6 | -0.1 | +11.6 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | chandelier 4xATR + 1.618 ext full (close) | 131 | 14 | 30 | 87 | +98.5 | +22.9 | +50.0 | -2.1 | +2.5 | +0.6 | 59 | +1.1 | +2.0 | +1.2 | +0.6 | -0.2 | +13.0 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | chandelier 4xATR + 2.618 ext full (close) | 131 | 17 | 8 | 106 | +98.5 | +6.1 | +12.5 | -5.8 | +2.5 | +0.4 | 56 | +0.9 | +1.9 | +1.1 | +0.4 | -0.5 | +15.1 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | chandelier 4xATR + 1/3 at each ext (close) | 131 | 17 | 3 | 111 | +98.5 | +35.1 | +37.0 | -1.8 | +2.5 | +0.6 | 56 | +0.9 | +2.1 | +1.3 | +0.5 | -0.3 | +15.5 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | chandelier 4xATR + Elliott w3/w5 target (close) | 131 | 18 | 10 | 103 | +33.6 | +7.6 | +40.0 | -0.1 | +2.3 | +0.4 | 56 | +0.8 | +1.5 | +0.7 | +0.1 | -0.8 | +14.9 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | chandelier 4xATR + 1/3 at 1.618, rest chandelier (close) | 131 | 18 | 0 | 113 | +98.5 | +22.9 | +50.0 | -1.4 | +2.3 | +0.4 | 56 | +0.7 | +1.8 | +1.1 | +0.2 | -0.5 | +15.7 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | chandelier 4xATR + 1/2 at 1.618, rest chandelier (close) | 131 | 18 | 0 | 113 | +98.5 | +22.9 | +50.0 | -1.6 | +2.4 | +0.5 | 57 | +0.8 | +2.0 | +1.3 | +0.4 | -0.3 | +15.7 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | fixed 3xATR, no target (intraday) | 131 | 18 | 0 | 113 | +nan | +nan | +nan | +nan | +2.3 | +0.3 | 54 | +0.8 | +1.6 | +0.8 | +0.0 | -0.8 | +15.6 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | chandelier 4xATR, no target (intraday) | 131 | 20 | 0 | 111 | +nan | +nan | +nan | +nan | +2.4 | +0.4 | 55 | +0.8 | +1.7 | +0.9 | +0.1 | -0.7 | +15.4 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | fixed 4xATR + 1.272 ext full (intraday) | 131 | 11 | 58 | 62 | +98.5 | +44.3 | +43.1 | -1.5 | +2.7 | +1.2 | 66 | +1.5 | +2.3 | +1.7 | +1.1 | +0.5 | +10.6 | robust to top-3 removal |
| Grok stock LONG | fixed 4xATR + 1.618 ext full (intraday) | 131 | 11 | 38 | 82 | +98.5 | +29.0 | +42.1 | -5.7 | +3.7 | +1.0 | 63 | +2.4 | +3.1 | +2.3 | +1.8 | +1.0 | +12.3 | robust to top-3 removal |
| Grok stock LONG | fixed 4xATR + 2.618 ext full (intraday) | 131 | 13 | 14 | 104 | +98.5 | +10.7 | +7.1 | -6.6 | +2.8 | +0.4 | 57 | +1.2 | +2.4 | +1.6 | +0.8 | -0.0 | +15.1 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | fixed 4xATR + 1/3 at each ext (intraday) | 131 | 13 | 6 | 112 | +98.5 | +44.3 | +37.9 | -1.9 | +2.9 | +0.7 | 60 | +1.3 | +2.6 | +1.9 | +0.9 | +0.2 | +15.9 | robust to top-3 removal |
| Grok stock LONG | fixed 4xATR + Elliott w3/w5 target (intraday) | 131 | 13 | 10 | 108 | +33.6 | +7.6 | +50.0 | +0.7 | +2.0 | +0.4 | 55 | +0.5 | +1.3 | +0.5 | -0.2 | -1.1 | +15.5 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | chandelier 4xATR + 1.272 ext full (intraday) | 131 | 13 | 58 | 60 | +98.5 | +44.3 | +43.1 | -1.5 | +2.6 | +1.2 | 65 | +1.4 | +2.1 | +1.5 | +0.9 | +0.3 | +10.4 | robust to top-3 removal |
| Grok stock LONG | chandelier 4xATR + 1.618 ext full (intraday) | 131 | 14 | 38 | 79 | +98.5 | +29.0 | +42.1 | -5.7 | +3.5 | +1.0 | 62 | +2.2 | +2.9 | +2.1 | +1.6 | +0.8 | +12.1 | robust to top-3 removal |
| Grok stock LONG | chandelier 4xATR + 2.618 ext full (intraday) | 131 | 18 | 14 | 99 | +98.5 | +10.7 | +7.1 | -6.6 | +3.0 | +0.4 | 57 | +1.5 | +2.6 | +1.8 | +1.1 | +0.3 | +14.6 | robust to top-3 removal |
| Grok stock LONG | chandelier 4xATR + 1/3 at each ext (intraday) | 131 | 19 | 6 | 106 | +98.5 | +44.3 | +39.7 | -2.2 | +2.8 | +0.7 | 59 | +1.3 | +2.5 | +1.8 | +0.9 | +0.2 | +15.2 | robust to top-3 removal |
| Grok stock LONG | chandelier 4xATR + Elliott w3/w5 target (intraday) | 131 | 19 | 11 | 101 | +33.6 | +8.4 | +45.5 | +0.0 | +2.4 | +0.4 | 57 | +1.0 | +1.7 | +0.9 | +0.3 | -0.6 | +14.6 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | chandelier 4xATR + 1/3 at 1.618, rest chandelier (intraday) | 131 | 20 | 0 | 111 | +98.5 | +29.0 | +42.1 | -3.2 | +2.8 | +0.4 | 56 | +1.2 | +2.3 | +1.5 | +0.7 | -0.0 | +15.4 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | chandelier 4xATR + 1/2 at 1.618, rest chandelier (intraday) | 131 | 20 | 0 | 111 | +98.5 | +29.0 | +42.1 | -3.8 | +2.9 | +0.5 | 56 | +1.4 | +2.6 | +1.8 | +1.0 | +0.3 | +15.4 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | hold, no stop | 60 | 0 | 0 | 60 | +nan | +nan | +nan | +nan | +3.6 | +6.3 | 73 | +4.8 | +3.4 | +2.7 | +4.6 | +3.9 | +19.0 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | fixed 3xATR, no target (close) | 60 | 4 | 0 | 56 | +nan | +nan | +nan | +nan | +4.3 | +6.3 | 73 | +5.4 | +4.1 | +3.4 | +5.2 | +4.5 | +18.0 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | chandelier 4xATR, no target (close) | 60 | 4 | 0 | 56 | +nan | +nan | +nan | +nan | +4.5 | +6.3 | 73 | +5.6 | +4.3 | +3.6 | +5.4 | +4.7 | +17.9 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | fixed 4xATR + 1.272 ext full (close) | 60 | 2 | 27 | 31 | +80.0 | +45.0 | +70.4 | +0.3 | +3.5 | +3.2 | 80 | +3.9 | +3.3 | +2.9 | +3.6 | +3.2 | +11.3 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | fixed 4xATR + 1.618 ext full (close) | 60 | 2 | 22 | 36 | +80.0 | +36.7 | +72.7 | -0.6 | +3.9 | +3.9 | 78 | +4.4 | +3.7 | +3.2 | +4.2 | +3.7 | +12.8 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | fixed 4xATR + 2.618 ext full (close) | 60 | 2 | 11 | 47 | +80.0 | +18.3 | +45.5 | -5.1 | +4.6 | +6.3 | 78 | +5.5 | +4.4 | +3.7 | +5.3 | +4.6 | +16.2 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | fixed 4xATR + 1/3 at each ext (close) | 60 | 4 | 3 | 53 | +80.0 | +45.0 | +70.4 | +0.1 | +3.6 | +4.7 | 73 | +4.6 | +3.4 | +2.8 | +4.4 | +3.8 | +17.3 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | fixed 4xATR + Elliott w3/w5 target (close) | 60 | 2 | 11 | 47 | +41.7 | +18.3 | +81.8 | -1.8 | +4.3 | +4.5 | 77 | +5.2 | +4.1 | +3.4 | +5.0 | +4.3 | +14.7 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | chandelier 4xATR + 1.272 ext full (close) | 60 | 2 | 27 | 31 | +80.0 | +45.0 | +70.4 | +0.3 | +3.6 | +3.2 | 80 | +4.0 | +3.4 | +2.9 | +3.7 | +3.2 | +11.2 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | chandelier 4xATR + 1.618 ext full (close) | 60 | 2 | 22 | 36 | +80.0 | +36.7 | +72.7 | -0.6 | +3.9 | +3.9 | 78 | +4.5 | +3.7 | +3.2 | +4.3 | +3.8 | +12.8 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | chandelier 4xATR + 2.618 ext full (close) | 60 | 2 | 11 | 47 | +80.0 | +18.3 | +45.5 | -5.1 | +4.7 | +6.3 | 78 | +5.6 | +4.5 | +3.7 | +5.4 | +4.7 | +16.1 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | chandelier 4xATR + 1/3 at each ext (close) | 60 | 4 | 3 | 53 | +80.0 | +45.0 | +70.4 | -0.3 | +3.8 | +4.7 | 73 | +4.9 | +3.6 | +3.1 | +4.7 | +4.1 | +17.1 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | chandelier 4xATR + Elliott w3/w5 target (close) | 60 | 2 | 11 | 47 | +41.7 | +18.3 | +81.8 | -1.8 | +4.4 | +4.5 | 77 | +5.3 | +4.3 | +3.6 | +5.1 | +4.5 | +14.6 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | chandelier 4xATR + 1/3 at 1.618, rest chandelier (close) | 60 | 4 | 0 | 56 | +80.0 | +36.7 | +72.7 | -1.5 | +4.3 | +5.9 | 73 | +5.4 | +4.1 | +3.4 | +5.2 | +4.5 | +17.9 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | chandelier 4xATR + 1/2 at 1.618, rest chandelier (close) | 60 | 4 | 0 | 56 | +80.0 | +36.7 | +72.7 | -1.3 | +4.2 | +5.5 | 75 | +5.3 | +4.0 | +3.3 | +5.1 | +4.4 | +17.9 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | fixed 3xATR, no target (intraday) | 60 | 4 | 0 | 56 | +nan | +nan | +nan | +nan | +4.5 | +6.3 | 73 | +5.6 | +4.4 | +3.7 | +5.5 | +4.8 | +17.6 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | chandelier 4xATR, no target (intraday) | 60 | 5 | 0 | 55 | +nan | +nan | +nan | +nan | +4.4 | +6.3 | 73 | +5.5 | +4.2 | +3.6 | +5.3 | +4.6 | +17.4 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | fixed 4xATR + 1.272 ext full (intraday) | 60 | 2 | 30 | 28 | +80.0 | +50.0 | +66.7 | +0.5 | +3.5 | +3.0 | 82 | +3.8 | +3.3 | +2.8 | +3.6 | +3.1 | +9.8 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | fixed 4xATR + 1.618 ext full (intraday) | 60 | 2 | 24 | 34 | +80.0 | +40.0 | +75.0 | -0.2 | +3.8 | +3.5 | 80 | +4.3 | +3.6 | +3.2 | +4.1 | +3.6 | +11.3 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | fixed 4xATR + 2.618 ext full (intraday) | 60 | 2 | 14 | 44 | +80.0 | +23.3 | +42.9 | -3.5 | +4.6 | +6.2 | 78 | +5.4 | +4.4 | +3.7 | +5.2 | +4.5 | +15.0 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | fixed 4xATR + 1/3 at each ext (intraday) | 60 | 4 | 5 | 51 | +80.0 | +50.0 | +66.7 | +0.3 | +3.6 | +4.7 | 75 | +4.6 | +3.4 | +2.9 | +4.4 | +3.8 | +16.6 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | fixed 4xATR + Elliott w3/w5 target (intraday) | 60 | 2 | 14 | 44 | +41.7 | +23.3 | +64.3 | -1.6 | +4.4 | +4.3 | 77 | +5.3 | +4.2 | +3.5 | +5.1 | +4.4 | +14.2 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | chandelier 4xATR + 1.272 ext full (intraday) | 60 | 2 | 30 | 28 | +80.0 | +50.0 | +66.7 | +0.5 | +3.6 | +3.0 | 82 | +3.9 | +3.4 | +3.0 | +3.7 | +3.2 | +9.8 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | chandelier 4xATR + 1.618 ext full (intraday) | 60 | 2 | 24 | 34 | +80.0 | +40.0 | +75.0 | -0.2 | +4.0 | +3.5 | 80 | +4.4 | +3.8 | +3.4 | +4.2 | +3.7 | +11.3 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | chandelier 4xATR + 2.618 ext full (intraday) | 60 | 3 | 14 | 43 | +80.0 | +23.3 | +42.9 | -3.5 | +4.4 | +6.2 | 78 | +5.2 | +4.2 | +3.5 | +5.0 | +4.2 | +14.5 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | chandelier 4xATR + 1/3 at each ext (intraday) | 60 | 5 | 5 | 50 | +80.0 | +50.0 | +70.0 | +0.3 | +3.7 | +4.7 | 73 | +4.7 | +3.5 | +3.0 | +4.5 | +3.9 | +15.9 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | chandelier 4xATR + Elliott w3/w5 target (intraday) | 60 | 3 | 14 | 43 | +41.7 | +23.3 | +64.3 | -1.6 | +4.3 | +4.3 | 77 | +5.1 | +4.1 | +3.4 | +4.9 | +4.2 | +13.6 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | chandelier 4xATR + 1/3 at 1.618, rest chandelier (intraday) | 60 | 5 | 0 | 55 | +80.0 | +40.0 | +79.2 | -1.0 | +4.3 | +5.9 | 73 | +5.3 | +4.1 | +3.4 | +5.2 | +4.5 | +17.4 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | chandelier 4xATR + 1/2 at 1.618, rest chandelier (intraday) | 60 | 5 | 0 | 55 | +80.0 | +40.0 | +79.2 | -0.8 | +4.2 | +5.4 | 75 | +5.3 | +4.0 | +3.3 | +5.1 | +4.4 | +17.4 | robust to top-3 removal |
| All stock SHORT | hold, no stop | 173 | 0 | 0 | 173 | +nan | +nan | +nan | +nan | -0.9 | -1.2 | 46 | +0.5 | -1.2 | -1.5 | +0.2 | -0.1 | +16.8 | LUCK (edge gone w/o top tickers) |
| All stock SHORT | fixed 3xATR, no target (close) | 173 | 32 | 0 | 141 | +nan | +nan | +nan | +nan | -0.5 | -1.2 | 46 | +0.8 | -0.8 | -1.1 | +0.5 | +0.2 | +15.2 | robust to top-3 removal |
| All stock SHORT | chandelier 4xATR, no target (close) | 173 | 27 | 0 | 146 | +nan | +nan | +nan | +nan | -0.5 | -1.2 | 46 | +0.8 | -0.8 | -1.1 | +0.5 | +0.2 | +15.5 | robust to top-3 removal |
| All stock SHORT | fixed 4xATR + 1.272 ext full (close) | 173 | 19 | 38 | 116 | +93.1 | +22.0 | +63.2 | -0.5 | -0.8 | +0.2 | 50 | +0.1 | -1.0 | -1.3 | -0.1 | -0.4 | +11.7 | LUCK (edge gone w/o top tickers) |
| All stock SHORT | fixed 4xATR + 1.618 ext full (close) | 173 | 19 | 29 | 125 | +93.1 | +16.8 | +69.0 | -1.7 | -0.6 | -0.7 | 48 | +0.4 | -0.9 | -1.2 | +0.2 | -0.1 | +12.7 | LUCK (edge gone w/o top tickers) |
| All stock SHORT | fixed 4xATR + 2.618 ext full (close) | 173 | 19 | 14 | 140 | +93.1 | +8.1 | +50.0 | -3.7 | -0.6 | -0.7 | 47 | +0.6 | -0.9 | -1.2 | +0.3 | +0.0 | +14.7 | robust to top-3 removal |
| All stock SHORT | fixed 4xATR + 1/3 at each ext (close) | 173 | 21 | 3 | 149 | +93.1 | +22.0 | +63.2 | -0.0 | -0.9 | -0.9 | 46 | +0.4 | -1.2 | -1.5 | +0.2 | -0.1 | +15.4 | LUCK (edge gone w/o top tickers) |
| All stock SHORT | fixed 4xATR + Elliott w3/w5 target (close) | 173 | 19 | 11 | 143 | +25.4 | +6.4 | +81.8 | -1.8 | -0.7 | -0.9 | 47 | +0.6 | -1.0 | -1.3 | +0.3 | -0.0 | +14.5 | LUCK (edge gone w/o top tickers) |
| All stock SHORT | chandelier 4xATR + 1.272 ext full (close) | 173 | 24 | 38 | 111 | +93.1 | +22.0 | +63.2 | -0.5 | -0.8 | +0.2 | 50 | +0.2 | -0.9 | -1.2 | -0.0 | -0.3 | +11.6 | LUCK (edge gone w/o top tickers) |
| All stock SHORT | chandelier 4xATR + 1.618 ext full (close) | 173 | 24 | 29 | 120 | +93.1 | +16.8 | +69.0 | -1.7 | -0.6 | -0.5 | 48 | +0.5 | -0.8 | -1.1 | +0.2 | -0.1 | +12.6 | LUCK (edge gone w/o top tickers) |
| All stock SHORT | chandelier 4xATR + 2.618 ext full (close) | 173 | 25 | 14 | 134 | +93.1 | +8.1 | +50.0 | -3.7 | -0.5 | -0.7 | 47 | +0.8 | -0.8 | -1.1 | +0.5 | +0.1 | +14.5 | robust to top-3 removal |
| All stock SHORT | chandelier 4xATR + 1/3 at each ext (close) | 173 | 27 | 3 | 143 | +93.1 | +22.0 | +63.2 | -0.6 | -0.7 | -0.9 | 46 | +0.6 | -1.0 | -1.3 | +0.3 | +0.0 | +15.2 | robust to top-3 removal |
| All stock SHORT | chandelier 4xATR + Elliott w3/w5 target (close) | 173 | 25 | 11 | 137 | +25.4 | +6.4 | +81.8 | -1.8 | -0.5 | -0.9 | 47 | +0.7 | -0.8 | -1.1 | +0.4 | +0.1 | +14.3 | robust to top-3 removal |
| All stock SHORT | chandelier 4xATR + 1/3 at 1.618, rest chandelier (close) | 173 | 27 | 0 | 146 | +93.1 | +16.8 | +69.0 | -2.0 | -0.5 | -1.2 | 46 | +0.8 | -0.8 | -1.1 | +0.5 | +0.2 | +15.5 | robust to top-3 removal |
| All stock SHORT | chandelier 4xATR + 1/2 at 1.618, rest chandelier (close) | 173 | 27 | 0 | 146 | +93.1 | +16.8 | +69.0 | -1.9 | -0.5 | -0.9 | 47 | +0.8 | -0.8 | -1.1 | +0.5 | +0.2 | +15.5 | robust to top-3 removal |
| All stock SHORT | fixed 3xATR, no target (intraday) | 173 | 36 | 0 | 137 | +nan | +nan | +nan | +nan | -0.1 | -1.2 | 46 | +1.2 | -0.4 | -0.7 | +0.9 | +0.6 | +14.8 | robust to top-3 removal |
| All stock SHORT | chandelier 4xATR, no target (intraday) | 173 | 35 | 0 | 138 | +nan | +nan | +nan | +nan | -0.3 | -1.2 | 46 | +1.1 | -0.6 | -0.9 | +0.8 | +0.5 | +14.9 | robust to top-3 removal |
| All stock SHORT | fixed 4xATR + 1.272 ext full (intraday) | 173 | 21 | 44 | 108 | +93.1 | +25.4 | +59.1 | -0.3 | -0.6 | +0.5 | 52 | +0.3 | -0.8 | -1.1 | +0.1 | -0.2 | +10.8 | LUCK (edge gone w/o top tickers) |
| All stock SHORT | fixed 4xATR + 1.618 ext full (intraday) | 173 | 21 | 36 | 116 | +93.1 | +20.8 | +61.1 | -1.4 | -0.4 | +0.6 | 51 | +0.5 | -0.6 | -0.9 | +0.3 | +0.0 | +11.7 | robust to top-3 removal |
| All stock SHORT | fixed 4xATR + 2.618 ext full (intraday) | 173 | 21 | 19 | 133 | +93.1 | +11.0 | +42.1 | -3.0 | -0.4 | -0.7 | 47 | +0.9 | -0.7 | -1.0 | +0.5 | +0.2 | +14.2 | robust to top-3 removal |
| All stock SHORT | fixed 4xATR + 1/3 at each ext (intraday) | 173 | 23 | 6 | 144 | +93.1 | +25.4 | +56.8 | -0.1 | -0.7 | -0.4 | 47 | +0.6 | -0.9 | -1.2 | +0.4 | +0.1 | +15.1 | robust to top-3 removal |
| All stock SHORT | fixed 4xATR + Elliott w3/w5 target (intraday) | 173 | 21 | 14 | 138 | +25.4 | +8.1 | +64.3 | -1.6 | -0.5 | -0.9 | 47 | +0.8 | -0.8 | -1.1 | +0.5 | +0.2 | +14.3 | robust to top-3 removal |
| All stock SHORT | chandelier 4xATR + 1.272 ext full (intraday) | 173 | 25 | 44 | 104 | +93.1 | +25.4 | +59.1 | -0.3 | -0.4 | +0.5 | 53 | +0.4 | -0.6 | -0.9 | +0.2 | -0.1 | +10.6 | LUCK (edge gone w/o top tickers) |
| All stock SHORT | chandelier 4xATR + 1.618 ext full (intraday) | 173 | 26 | 36 | 111 | +93.1 | +20.8 | +61.1 | -1.4 | -0.2 | +0.6 | 51 | +0.7 | -0.4 | -0.7 | +0.5 | +0.2 | +11.4 | robust to top-3 removal |
| All stock SHORT | chandelier 4xATR + 2.618 ext full (intraday) | 173 | 33 | 19 | 121 | +93.1 | +11.0 | +42.1 | -3.0 | -0.2 | -0.7 | 48 | +1.0 | -0.5 | -0.9 | +0.7 | +0.3 | +13.6 | robust to top-3 removal |
| All stock SHORT | chandelier 4xATR + 1/3 at each ext (intraday) | 173 | 35 | 6 | 132 | +93.1 | +25.4 | +61.4 | -0.4 | -0.4 | -0.5 | 47 | +0.8 | -0.7 | -1.0 | +0.6 | +0.3 | +14.4 | robust to top-3 removal |
| All stock SHORT | chandelier 4xATR + Elliott w3/w5 target (intraday) | 173 | 33 | 14 | 126 | +25.4 | +8.1 | +64.3 | -1.6 | -0.3 | -0.9 | 47 | +0.9 | -0.6 | -0.9 | +0.6 | +0.3 | +13.6 | robust to top-3 removal |
| All stock SHORT | chandelier 4xATR + 1/3 at 1.618, rest chandelier (intraday) | 173 | 35 | 0 | 138 | +93.1 | +20.8 | +66.7 | -1.3 | -0.2 | -0.9 | 46 | +1.1 | -0.5 | -0.8 | +0.8 | +0.5 | +14.9 | robust to top-3 removal |
| All stock SHORT | chandelier 4xATR + 1/2 at 1.618, rest chandelier (intraday) | 173 | 35 | 0 | 138 | +93.1 | +20.8 | +66.7 | -1.4 | -0.2 | -0.7 | 48 | +1.1 | -0.5 | -0.8 | +0.8 | +0.5 | +14.9 | robust to top-3 removal |