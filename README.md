# סורק מניות וקריפטו של אילן (stock-scanner)

שכבת מחקר משולבת: [שילוב המחקר בניקוד הטכני](research/jewish-lunar/INTEGRATION.he.md).
בכניסה `run_unified_scan.py` נוספה שכבה ניסיונית שמשקלה המוגדר 30%, לצד 70% לציון הבסיס, לפי בקשת אילן.
היא כוללת לוח אסטרונומי ציבורי ומנגנון הרחבה חודשי. התיעוד להלן מתאר את תמונת המקור; אזכורי משקל 0 קודמים אינם מתארים את שכבת השקלול החדשה.


הרחבת המעקב: [מחקר מצטבר ומעקב יומי](research/jewish-lunar/FORWARD_RESEARCH.he.md), כולל חדשות לכל עסקה פתוחה ובדיקות 5/10/20 ימי מסחר **אחרי סגירת עסקה**. קובצי הפעלה למחשב הלינוקס: [התקנה ותזמון](ops/LINUX_DEPLOYMENT.he.md). עדכון הריפו לבדו אינו מפעיל את הבוט. סיכומי המעקב יתפרסמו כאן מדי יום לאחר הפעלת המתזמן.

ריפו פרטי שמכיל **קוד, תיעוד ומחקר**: כולל לוח אסטרונומי ציבורי וסיכומי מעקב עתידיים; בלי מפתחות או מטמוני מחירים גולמיים. מטרתו לאפשר ל-GPT (דרך מחבר GitHub של ChatGPT) ולבוטים אחרים לקרוא את הסורק ואת המבנה שלו.
התמונה צולמה מהמחשב של הבוט ב-10.10.2026. הקוד רץ בפועל מ-`/workspace` על המחשב הזה, ולא מהריפו.

> **חשוב:** הקוד מייבא קבצים לפי נתיבים מוחלטים תחת `/workspace/...` (ולפעמים `sys.path.insert('/workspace')`). הקוד **לא שוכתב**. טבלת הנתיבים המקוריים נמצאת בהמשך.

## ארכיטקטורה ותפקידי הפלטפורמות
| רכיב | תפקיד |
|---|---|
| **הבוט (שוק ההון)** | כל הטכני: מחירים, ATR, סטופים, פיבו/אליוט, רמות, גלי ווליום, מומנטום 12-1, ניקוד |
| **Grok (xAI)** | סנטימנט מ-X, וקריפטו |
| **Perplexity Sonar** | קטליסטים (דוחות, חדשות, אירועים) |
| **Claude** | האנליסט: מסכם וממליץ על כל מועמד |
| **GPT** | פרקליט השטן: מאתגר את התזה של Claude |
| **Jev** | פילטר מקדים לכותרות חדשות לפני שהן מגיעות למודלים |

ראו `ARCHITECTURE.md` לתרשים זרימה.

## הזרימה
1. **בדיקת משטר שוק** (`tracker/market_regime.py`, `tracker/rules/regime*.py`).
2. **מועמדים**: סריקה טכנית על היקום (מניות ארה"ב ≥ $1.5B, קריפטו) ב-`scanner/swing_scan.py` + `modules/scanner_crypto.py`.
3. **העשרה**: פונדמנטלס, חדשות, שורט, רמות, גלים, גאומטריה, אליוט v2, עמודות מחקר (רובן במשקל 0).
4. **אתגרים צולבים** בין הפלטפורמות (`scanner/scanner_platforms.py`): Grok ↔ Perplexity ↔ Claude ↔ GPT.
5. **ניקוד** ובחירת עד 50 שמות.
6. **דוח** בעברית (Markdown + PDF) – `scanner/unified_report.py`, `scanner/run_daily_report.py`.
7. **טראקר ולולאת למידה**: `tracker/` (build7, engine, alerts), `modules/scanner_lessons.py`, `scanner/run_checkpoints.py`, `scanner/tool_stats.py`.

## לוחות זמנים מבוקשים (שעון ישראל; דורשים התקנה במחשב הבוט)
- **שבועי:** יום שני 09:00 – ריצה מלאה עם כל המודלים, עד 50 שמות לפי ציון, **בלי חלוקה ללונג/שורט**.
- **יומי:** כל יום 08:24 – סריקת נייר (`--paper --no-models`) ואחריה דוח ביניים.

## כללים פעילים
- מניות: **סטופ נגרר 4×ATR14** (שנדליר).
- לונג במניות: **חצי מהפוזיציה יוצא בפיבו 1.618**.
- קריפטו לונג: **סטופ קבוע 3×ATR14**. **קריפטו שורט מוקפא.**
- כלל שורט: `ck_score ≥ 3` **וגם** מחיר מתחת ל-SMA200.
- **מומנטום 12-1** שווה 10 נקודות בציון.
- **חסימת דוחות:** לא נכנסים 5 ימי מסחר לפני דוח (`EARNINGS_BLOCK_TD`).
- **שווי שוק מינימלי $1.5B.**
- **מקסימום 2 מניות לסקטור.**

## מדיניות משקל 0 וכלל ה"סיום"
שכבת גאן/תכונה מתועדת כחריגה מפורשת לפי בקשת אילן: 30% למחקר, אף שטרם אומת יתרון. אין בכך שינוי אוטומטי של משקלי כלים אחרים.

המדיניות הקודמת לכלים אחרים: כל כלי חדש נכנס כעמודה **במשקל 0**: נרשם בדוח ובטראקר, ולא משנה ציון, כניסה, סטופ או יעד.
כלי "מסיים" ומקבל משקל רק אם:
- **≥ 30 תוצאות מחוץ למדגם** מ-**8–10 ימי כניסה** שונים לפחות (מדידה קדימה מ-12.10.2026);
- **FDR (Benjamini–Hochberg) q < 0.10**;
- **ערך מוסף** מעבר לכללים הקיימים (incremental);
- **walk-forward** יציב.
המדידה: `scanner/tool_stats.py`. הכלל המלא: `docs/rules/out-of-sample-rule-2026-10-08.txt`.

## קובץ הרמות (JSON) – מקור האמת היחיד
בכל ריצה `run_unified_scan.py` מחשב פעם אחת לכל מועמד את הרמות (כניסה, סטופ, יעדים, פיבו, אליוט) ושומר קובץ JSON לפי `scanner/levels_schema.json` (`modules/scanner_levelsfile.py`). הדוח, הגרפים והטראקר קוראים **רק** מהקובץ הזה, כדי שלא יהיו מספרים סותרים.

## מקורות נתונים
Alpaca (מחירים, חדשות Benzinga, קריפטו), yfinance, OpenBB (FINRA short interest, דארק-פול, אופציות CBOE, קונצנזוס, לוח דוחות), FRED, SEC EDGAR, Nasdaq, CoinGecko, AAII, CNN Fear&Greed, X (דרך Grok וגישה חינמית), Perplexity, OpenRouter (Claude/GPT/Jev), data.binance.vision (היסטוריה לבקטסטים). TradingView: התראות דרך ריליי ב-Vercel.

## מפת מודולים
| תיקייה בריפו | נתיב מקורי | תוכן |
|---|---|---|
| `scanner/` | `/workspace/*.py`, `/workspace/levels_schema.json` | נקודות כניסה ותזמור: `run_unified_scan.py`, `swing_scan.py`, `scanner_platforms.py`, `unified_report.py`, `run_daily_report.py`, `run_checkpoints.py`, `research_columns.py`, `tool_stats.py`, `openbb_snapshot.py` |
| `modules/` | `/workspace/scanner_*.py`, `/workspace/x_cache.py` | `scanner_stops` (כללים פעילים), `scanner_crypto`, `scanner_charts`, `scanner_levels`, `scanner_levelsfile`, `scanner_waves`, `scanner_geometry`, `scanner_elliott_v2`, `scanner_fundamentals`, `scanner_short`, `scanner_momentum`, `scanner_news`, `scanner_newsmacro`, `scanner_lessons`, `x_cache` |
| `modules/stop_rules.py` | `/workspace/trading-frameworks-eval/iaf/stop_rules.py` | לוגיקת סטופ ATR נקודתית (PIT), משותפת לבקטסט ולסורק |
| `tracker/` | `/workspace/tracker/` | build7 (הטראקר), engine, alerts, market_regime, fetch, דוחות; `rules/`, `pplx/`, `short/`, `auto/` |
| `research/liq-sweep/` | `/workspace/liq-sweep/` | גלאי היפוך אחרי ציד נזילות |
| `research/fib-spiral/` | `/workspace/fib-spiral/` | כלל שורט ספירלת פיבו |
| `research/sr-waves-eval/` | `/workspace/sr-waves-eval/` | בדיקת רמות S/R וגלי ווליום |
| `research/elliott-v2-eval/` | `/workspace/elliott-v2-eval/` | בדיקת אליוט v2 |
| `research/ta-calib/` | `/workspace/ta-calib/` | TradingAgents מכויל (רץ על הלפטופ) |
| `research/research_nightly/` | `/workspace/research_nightly/` | מודלי לילה Qlib/FinRL, בדיקות research_columns, parity של vectorbt |
| `research/tradingagents/` | `/workspace/fin-llm-eval/`, `/workspace/ta-repos-eval/`, `/workspace/trading-frameworks-eval/` | שילוב TradingAgents ומודלי LLM פיננסיים (בקטסט על הטראקר, ריצה על הלפטופ עם Ollama), בדיקת ספריות TA/אליוט/SMC, ומסגרות מסחר (iaf, כולל `stop_rules.py`) |
| `research/tool_stats_tests/` | `/workspace/research-models/tests/` | טסטים ל-tool_stats |
| `research/results/` | `gh-repos-eval/`, `research-models/tool_stats/` | סיכומי תוצאות בלבד |
| `tradingview/` | `/workspace/tradingview/` | סקריפט Pine, ריליי Vercel (בלי סודות), ולידציה |
| `docs/rules/` | זיכרון הבוט `memory/stock-scanner/` | תוכנית עבודה v2.8, נספחים, מפות חשבונות X |
| `docs/rules/images/` | `.../ilan-rules-images/` | הגרפים של אילן שמהם נגזרו הכללים |

## איך נבדק כל כלי מחקר
- **liq-sweep (היפוך אחרי ציד נזילות):** כלל מקובע מראש (`RULE.frozen.md` + sha256), בקטסט על כל האירועים בהיסטוריה (קריפטו 1m/15m, מניות יומי), נטו אחרי עמלות/החלקה/מימון, השוואה לכניסות אקראיות, BH-FDR על 48 בדיקות, בדיקת דליפה (528/528 נקודות חיתוך זהות). רק לונג במניות יומי בכניסה בסגירה עבר (+0.15R, q=0.0009), ושביר. משקל 0.
- **fib-spiral (שורט ספירלת פיבו):** כלל מקובע מראש, בקטסט קריפטו 1h (4,727 עסקאות) ומניות יומי (4,063), נטו אחרי עלויות, השוואה לשורטים אקראיים ולחלופות יעד, בדיקת דליפה/צביעה מחדש (957/957). שלילי (−0.12R / −0.07R). משקל 0.
- **sr-waves-eval:** בדיקת PIT על סטאפים מהטראקר (bootstrap מקובץ לפי יום), ואחר כך FDR על כל המשפחה (`fdr_results.md`). שום דבר לא עבר. משקל 0.
- **elliott-v2-eval:** בדיקת דליפה מלאה (0 הבדלים מ-288,425 ערכים), 317 השוואות + משפחה משותפת 1,257, BH-FDR. 0 עברו q<0.10. משקל 0.
- **ta-calib:** פיצול כיול/holdout לפי תאריך כניסה, סף נקבע על חצי הכיול, holdout נבדק פעם אחת (נעול), BH-FDR. ההחלטה האמיתית רק על סטאפים מ-12.10.
- **research_nightly / research_columns:** בדיקת זמן ריצה ודליפה (`rc_test.py`), backfill בתוך המדגם בלבד, parity של vectorbt מול `stop_rules.py`.
- **TradingAgents (`research/tradingagents/`):** הערכת LLM פיננסיים עם בדיקת דליפה (`leak_test.py`), בקטסט על סטאפי הטראקר (`tracker_backtest.md`, `backtest/`), ריצה על הלפטופ (`laptop-run/`, Ollama + Modelfile), השוואת עלויות API (`cost/`). ספריות TA/אליוט/SMC נבדקו ב-`ta-repos-eval` (בדיקות דליפה `leak_ta.py`, `leak_ew.py`), ומסגרות מסחר ב-`trading-frameworks-eval` (בדיקות סמנטיקה וסימולציות סטופ). קוד צד שלישי (TradingAgents, llama.cpp, ai-hedge-fund וכו') לא הועתק – רק הקוד והתיעוד שלנו.
  > **הרצה ונתונים:** TradingAgents רץ על הלפטופ של אילן עם מודלי LLM מקומיים דרך Ollama, לא דרך OpenRouter. הנתונים מגיעים מ-yfinance, מ-Alpaca ומתמונת המצב של OpenStock (`laptop_scripts/openstock_market.py`: מחיר וחדשות לכל מניה, רק בריצות חיות; בבקטסט היסטורי הוא חוסם את עצמו כדי למנוע דליפה). הסקריפטים של הלפטופ (ריצת לילה, הגרסה המכוילת, README) נמצאים ב-`research/tradingagents/laptop_scripts/`.
- **tool_stats:** טסטים סינתטיים (`research/tool_stats_tests/`) לחישוב excess כיווני ול-ev2.
- **gh-repos-eval:** 7 ריפו מקצועיים נבדקו על אותו harness; LEAN/Nautilus/vectorbt שחזרו את `stop_rules.py` (787–788/788). אף אחד לא הוסיף יתרון.

## משתני סביבה (שמות בלבד)
מפתחות: `ALPACA_API_KEY_ID`, `ALPACA_API_SECRET_KEY`, `XAI_API_KEY`, `OPENROUTER_API_KEY`, `FRED_API_KEY`, `SEC_EDGAR_UA`.
ריליי TradingView (ב-Vercel): `TV_SHARED_SECRET`, `ROUTINE_WEBHOOK_URL`, `ROUTINE_AUTH_HEADER`, `TV_IP_CHECK`.
הגדרות: `SCAN_ASOF`, `SCAN_EXTRA_TICKERS`, `SCAN_FUND_LIVE`, `SCAN_GEOM_INTRADAY`, `SCAN_GEOM_INTRADAY_BUDGET_S`, `EARNINGS_BLOCK_TD`, `CRYPTO_UNIVERSE`, `PLATFORM_*` (מודלים, תקציב, `PLATFORM_MAX_PER_SECTOR`, `PLATFORM_TOP_LONG/SHORT/CRYPTO` וכו'), `PLATFORM_X_CACHE_DIR`, `NEWS_CACHE_DIR`, `RESEARCH_COLS_BUDGET_S`, `RESEARCH_COLS_TOOL_TIMEOUT_S`, `TRACKER_OUT`, `PIT_PX_DIR`, `TA_MODEL`, `TA_MAX_TOKENS`, `OLLAMA_BASE_URL`, `NIGHT_WINDOW`.

## מה לא נכלל
נתונים (`*.csv`, `*.xlsx`, `*.pkl`), לוגים, `scan-runs/`, `openbb-snapshots/`, נתוני `research-models/`, קבצי `.bak`, `venv`, `__pycache__`, `node_modules`, `.env*`, תיקיות `data/` ו-`out/` של הבקטסטים, וכל פרויקט אחר שיושב ב-`/workspace`.

---

## English summary
Private code/research repository based on the 10 Oct 2026 snapshot of Ilan's unified stock + crypto scanner. The live system runs from `/workspace` on the bot's box; existing imports still use those paths. GitHub updates require deployment to that Linux environment.

- **Roles:** bot = technicals; Grok = X sentiment + crypto; Perplexity Sonar = catalysts; Claude = analyst; GPT = devil's advocate; Jev = news pre-filter.
- **Flow:** regime check → candidates → enrichment → cross-challenges → scoring → Hebrew report → tracker + learning loop.
- **Schedule (Israel time):** weekly Monday 09:00, full models, up to 50 names by score, no long/short split; daily paper scan + interim report every day at 08:24.
- **Active rules:** 4×ATR14 trailing stop on stocks; half off at Fib 1.618 on longs; crypto longs fixed 3×ATR stop; crypto shorts frozen; short rule ck_score≥3 and below SMA200; 12-1 momentum = 10 pts; 5-trading-day earnings block; min $1.5B market cap; max 2 per sector.
- **Research overlay:** explicit user-selected experimental 30% budget / 70% baseline. Other tools retain the prior weight-0 graduation policy. Daily news/technical follow-up and post-exit 5/10/20-session audits are included; coefficients do not update automatically.
- **Single source of truth:** the per-run levels JSON (`scanner/levels_schema.json`, `modules/scanner_levelsfile.py`).
- TradingAgents integration lives in `research/tradingagents/` (our code only; upstream repos not vendored). It runs on Ilan's laptop with local LLMs via Ollama (not OpenRouter); data comes from yfinance, Alpaca and the OpenStock snapshot (`laptop_scripts/openstock_market.py`, live runs only, self-blocks in historical backtests).
- No secrets or raw price caches are committed. Public calendar fixtures and generated research/follow-up summaries are explicitly included. Env var names are listed above.
