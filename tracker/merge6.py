"""Keep previously fetched bars (frozen, as in the 07.10 report); append only new dates from the 08.10 fetch."""
import pandas as pd
for nf,of in [('prices_all.pkl','prices_all_pre1008.pkl'),('auto/crypto_1h.pkl','auto/crypto_1h_pre1008.pkl'),('auto/crypto_daily.pkl','auto/crypto_daily_pre1008.pkl')]:
    n=pd.read_pickle(nf); o=pd.read_pickle(of)
    n.to_pickle(nf.replace('.pkl','_raw1008.pkl'))
    ts=sorted(set(o.columns.get_level_values(0))|set(n.columns.get_level_values(0)))
    parts={}
    for t in ts:
        a=o[t] if t in o.columns.get_level_values(0) else None
        b=n[t] if t in n.columns.get_level_values(0) else None
        if a is None: parts[t]=b; continue
        a=a.dropna(subset=['Close'])
        if b is None: parts[t]=a; continue
        b=b.dropna(subset=['Close']); b=b[b.index>o.index[-1]]
        if t=='WBD': b=b.iloc[0:0]   # Yahoo now returns a single bogus 05.10 bar for WBD
        parts[t]=pd.concat([a,b])
    m=pd.concat(parts,axis=1).sort_index(); m.columns.names=n.columns.names
    m.to_pickle(nf); print(nf,m.index[-1],m.shape)
