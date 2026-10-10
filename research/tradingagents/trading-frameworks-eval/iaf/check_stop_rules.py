"""Regression check: stop_rules.ChandelierStop must reproduce the earlier independent replays exactly."""
import pandas as pd
R=pd.read_csv('sim_ratchet_trades.csv'); C=pd.read_csv('sim_chand_trades.csv'); T=pd.read_csv('sim_targets_trades.csv'); Fb=pd.read_csv('sim_fib_trades.csv')
ok=True
for a,b,src in [('rt_plain_c','chand4_c',C),('rt_plain_i','chand4_i',C),('rt_plain_h618_c','tg_ch_HY2_c',T),('rt_plain_h618_i','tg_ch_HY2_i',T),('rt_fixed3_c','atr3_c',Fb),('rt_fixed3_i','atr3_i',Fb)]:
    m=R[R.policy==a].merge(src[src.policy==b],on='setup_id',suffixes=('','_o')); d=(m.ret_net-m.ret_net_o).abs()
    print(f'{a:18s} vs {b:12s} N={len(m):4d} max|diff|={d.max():.2e} mismatches={int((d>1e-9).sum())}'); ok&=bool((d<=1e-9).all())
print('OK' if ok else 'MISMATCH')
