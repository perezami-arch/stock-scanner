# Hook snippets (not applied - swing_scan.py / build7.py / run_unified_scan.py belong to other executors)

## swing_scan.py - after the GEOMETRY block, before the first scan_raw.csv write
```python
import scanner_levels as SRL, scanner_waves as WV, scanner_elliott_v2 as EV2   # 2026-10-08: EXPERIMENTAL S/R + waves + Elliott v2, weight 0
# ---- EXPERIMENTAL S/R levels (scanner_levels, SWING = 400D + 200W) + volume waves / RSI-CCI divergences (scanner_waves). LOGGED ONLY.
try:
    _sw, _wt0 = [], time.time()
    for t, _ok in zip(out['t'], out['mcap_ok']):
        if t.startswith('^') or not bool(_ok): continue
        b = ST.daily_bars(t, 'stock', SCAN_ASOF, _px_dir)
        if b is None or len(b) < 60: _sw.append({'t': t, 'wv_flag': 'no data / <60 bars'}); continue
        rec = {'t': t, **SRL.sr_columns(t, SCAN_ASOF, 'SWING', 'LONG')}          # own 12y Yahoo download, cached per day
        rec.update(WV.waves_columns(b, SCAN_ASOF, 'stock', 'LONG'))              # LONG view (like the Fib/Elliott columns)
        rec.update({f'short_{k}': v for k, v in WV.waves_columns(b, SCAN_ASOF, 'stock', 'SHORT').items()
                    if k.startswith('wave_')})                                    # SHORT-view wave_end/start for short candidates
        rec.update(EV2.elliott_v2_columns(b, SCAN_ASOF, 'stock', 'LONG'))         # ev2_long_* + ev2_short_* (both views) + ev2_* (LONG view)
        _sw.append(rec)
    out = out.merge(pd.DataFrame(_sw), on='t', how='left')
    print(f"\n=== EXPERIMENTAL S/R + volume waves (logged only, weight 0) - {time.time()-_wt0:.0f}s ===")
    print(out[~out['t'].str.startswith('^')][[c for c in ['t','px','sr_support','sr_support_dist_atr','sr_support_tf','sr_resistance',
          'sr_resistance_dist_atr','sr_resistance_tf','wave_end_signal','wave_end_n','wave_end_families','wave_start_signal','wave_start_n','ev2_long_label','ev2_short_label','rsi14','cci20','crsi'] if c in out.columns]].to_string(index=False))
except Exception as _e:   # never break the scan on a logged-only block
    print(f'SR/WAVES logged-only block failed: {_e.__class__.__name__}: {_e}')
```

## build7.py - tracker columns from the lookups (keyed by setup_id), after the other lookup merges
```python
import scanner_levels as SRL, scanner_waves as WV
import scanner_elliott_v2 as EV2
for _f, _keys in (('/workspace/tracker/sr_levels_lookup.csv', SRL.TRACKER_KEYS), ('/workspace/tracker/volume_waves_lookup.csv', WV.TRACKER_KEYS),
                  ('/workspace/tracker/elliott_v2_lookup.csv', EV2.TRACKER_KEYS)):   # ev2_* = trade-direction view, v1 columns untouched
    _lk = pd.read_csv(_f).drop_duplicates('setup_id').set_index('setup_id')
    for _k in _keys:
        df['exp_' + _k] = df['setup_id'].map(_lk[_k]) if _k in _lk.columns else None   # weight 0, experimental
```
Regenerate the lookups (PIT, all tracker stock setups): S/R `python3 /workspace/sr-waves-eval/bt.py` (NOTE: bt.py also rewrites
volume_waves_lookup.csv); waves with the >=2-families signal `python3 /workspace/elliott-v2-eval/regen_waves_lookup.py`;
Elliott v2 `python3 /workspace/elliott-v2-eval/ev2_bt.py` (writes elliott_v2_lookup.csv + pit_leak_check.csv).
Waves signal change (08.10): wave_end_signal / wave_start_signal = wave_end_n >= 2 independent families (wave_end_families lists them);
the old any-reason flag is now wave_end_any.

## Charts (optional) - in run_unified_scan.py after the report
```python
import scanner_charts as SC; SC.render_run(run_dir)
# Renders PURELY from <run_dir>/levels/<T>.json when present (schema /workspace/levels_schema.json, levels-1.0), else builds a reference
# levels file in charts/levels_built/. Writes charts/<T>_<dir>.png, charts/chart_index.json (exact numbers drawn) and charts_he.pdf.
# Single chart: SC.render_from_levels(levels_dict_or_path, bars_df, out_png, index_path=None)
```
