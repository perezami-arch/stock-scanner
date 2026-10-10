# Architecture / ארכיטקטורה

```mermaid
flowchart TD
    subgraph SCHED[Schedules - Israel time]
        W[Weekly: Mon 09:00<br/>full models, up to 50 names]
        D[Daily: every day 08:24<br/>paper scan + news + trade follow-up]
    end
    W --> R
    D --> R
    R[1. Regime check<br/>tracker/market_regime.py, tracker/rules/regime*.py] --> C
    C[2. Candidates<br/>scanner/swing_scan.py + modules/scanner_crypto.py<br/>US stocks >= $1.5B, crypto longs] --> E
    E[3. Enrichment<br/>fundamentals, news, short, levels, waves,<br/>geometry, elliott v2, momentum 12-1, research_columns] --> J
    subgraph PLAT[4. Cross-challenges - scanner/scanner_platforms.py]
        J[Jev: news pre-filter] --> G[Grok: X sentiment + crypto]
        J --> P[Perplexity Sonar: catalysts]
        G --> CL[Claude: analyst]
        P --> CL
        CL --> GPT[GPT: devil's advocate]
    end
    GPT --> S
    S[5. Ranking<br/>70% baseline + 30% experimental research,<br/>earnings block and sector cap] --> L
    L[(Levels JSON<br/>single source of truth<br/>modules/scanner_levelsfile.py)] --> REP
    REP[6. Hebrew report MD + PDF<br/>scanner/unified_report.py, run_daily_report.py] --> T
    L --> CH[scanner_charts.py]
    CH --> REP
    T[7. Tracker<br/>tracker/build7.py, engine.py, alerts.py] --> LL
    LL[Learning loop<br/>scanner_lessons.py, run_checkpoints.py] --> TS
    TS[tool_stats.py<br/>forward measurement of weight-0 tools<br/>graduation: >=30 OOS, 8-10 entry days, FDR q<0.10, incremental, walk-forward] -.-> S
    TV[TradingView alerts] --> RELAY[Vercel relay /api/tv] --> T
    L --> FR[Frozen research snapshots<br/>baseline vs weighted ranking]
    D --> DAILY[Daily technical review and news<br/>all open positions]
    DAILY --> POST[Closed trade audit<br/>5 / 10 / 20 sessions AFTER exit]
    FR --> RL[Persistent research ledger<br/>no automatic weight changes]
    DAILY --> RL
    RL --> GH[Daily summaries in GitHub<br/>after Linux deployment]
```

The active stop rules live in `modules/scanner_stops.py` and the causal ATR stop engine in `modules/stop_rules.py`.
The 30% Gann/Tekunah overlay is the user's explicit experimental allocation, not a validated graduation.
Other research/model columns retain their existing policies. The ranking is computed before model
enrichment; the final earnings/reconciliation gate can still remove recommendations.
See `research/jewish-lunar/FORWARD_RESEARCH.he.md` and `ops/LINUX_DEPLOYMENT.he.md`.
