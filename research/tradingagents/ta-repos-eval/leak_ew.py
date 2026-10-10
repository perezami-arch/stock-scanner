"""Leak / repaint checks for the Elliott adapters and the smc wrapper (30 random setups, seed 20261008, same sample as leak_ta.py).
 1. Pivot repaint: pivots each repo would see on the history truncated at the rule bar (T) vs on the FULL series, restricted to bars
    <= the rule bar (F). Differences = pivots that need later bars (look-ahead in a vectorised full-series run / repaint live).
 2. Adapter determinism under junk: every state/level from ew_libs and every smc wrapper feature recomputed with all bars after the
    rule bar replaced by garbage must be identical (adapters truncate before calling the repo).
 3. Equivalence: our depth-first enumeration for alessioricco/ElliottWaves vs the repo's own 9-nested-loop ElliottWaveDiscovery on short
    windows (where the brute force is feasible)."""
import sys, io, contextlib, numpy as np, pandas as pd, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0,'/workspace/ta-repos-eval')
from common import *
import ew_libs as E, features_smc as FS
samp=leak_sample(30)
def taew_pivots(v):
    # verbatim replica of the repo's peak/valley loop (identical in every *_label_* function)
    x=[]; z=[]
    for i in range(1,len(v)-1):
        if (v[i]<=v[i+1] and v[i-1]>=v[i]) or (v[i]>=v[i+1] and v[i-1]<=v[i]):
            x.append(v[i]); z.append(i); d=E.TAEW.diff(x); d.insert(0,1)
            x=E.TAEW.trimming(x,E.TAEW.otherThan(d,otherthan=0)); z=E.TAEW.trimming(z,E.TAEW.otherThan(d,otherthan=0))
    return z
rows=[]
for _,r in (samp.iterrows() if 'eqonly' not in sys.argv else []):
    df=hist(r); last=pd.Timestamp(r.rule_bar_actual); t=trunc(df,r); n=len(t); sg=1 if r.direction=='LONG' else -1
    # 1a taew pivots
    pT=set(taew_pivots(list(t.Close.values))); pF=set(i for i in taew_pivots(list(df.Close.values)) if i<=n-1)
    # 1b ElliottWaves argrelextrema(order=7) pivots, raw (repo) and after our confirmation shift
    def arp(x,drop):
        z=E._AR['minmaxTwoMeasures'](x[['Close']].reset_index(drop=True).copy(),'Close','Close','FlowMinMax',E.ORDER); fm=z.FlowMinMax.values.copy()
        if drop: fm[len(fm)-E.ORDER:]=0
        return {(i,int(fm[i])) for i in np.where(fm!=0)[0]}
    aT_raw=arp(t,False); aT=arp(t,True); aF={p for p in arp(df,False) if p[0]<=n-1}; aF_conf={p for p in aF if p[0]<=n-1-E.ORDER}
    # 1c ElliottWaveAnalyzer: monowave chain (skip 0) from the window low on T vs F: is the wave that ends on the last bar extended later?
    def chain(x):
        lows=x.Low.values.astype(float)[-200:] if len(x)>=200 else x.Low.values.astype(float); highs=x.High.values.astype(float)[-len(lows):]
        return lows,highs
    off=max(0,n-200); lw=t.Low.values[off:].astype(float); hg=t.High.values[off:].astype(float); i0=int(np.argmin(lw))
    lwF=df.Low.values[off:].astype(float); hgF=df.High.values[off:].astype(float)
    ends=[]; endsF=[]; s=i0; sF=i0
    for wi in range(5):
        Cls=E.MonoWaveUp if wi%2==0 else E.MonoWaveDown
        w=Cls(lows=lw,highs=hg,dates=np.arange(len(lw)),idx_start=s,skip=0); wf=Cls(lows=lwF,highs=hgF,dates=np.arange(len(lwF)),idx_start=sF,skip=0)
        if w.idx_end is None: break
        ends.append(w.idx_end); endsF.append(wf.idx_end); s=w.idx_end; sF=wf.idx_end if wf.idx_end is not None else sF
        if w.idx_end>=len(lw)-1: break
    ewa_last_unconf=bool(ends and ends[-1]>=len(lw)-1); ewa_changed=ends!=endsF[:len(ends)]
    # 2 junk determinism
    Fj=dict(F); Fj[(r.ticker,r.asset=='crypto')]=garbage(df,last).astype(float)
    xj=trunc(Fj[(r.ticker,r.asset=='crypto')].dropna(subset=['Close']),r)
    dif=0; tot=0
    for f in (E.taew_state,E.ewa_state,E.ar_state):
        a=f(t,sg); b=f(xj,sg)
        for k in set(a)|set(b): tot+=1; dif+=not same(a.get(k),b.get(k))
    sa=FS.feat(dict(setup_id=r.setup_id,ticker=r.ticker,asset=r.asset,rule_bar_actual=r.rule_bar_actual))
    import common; F0=common.F; common.F=Fj
    try: sb=FS.feat(dict(setup_id=r.setup_id,ticker=r.ticker,asset=r.asset,rule_bar_actual=r.rule_bar_actual))
    finally: common.F=F0
    for k in set(sa)|set(sb):
        tot+=1; va,vb=sa.get(k),sb.get(k)
        dif+= (not (va==vb)) if isinstance(va,(list,str,bool)) or va is None else (not same(va,vb))
    rows.append(dict(setup_id=r.setup_id,ticker=r.ticker,direction=r.direction,n_bars=n,
        taew_piv_T=len(pT),taew_piv_F=len(pF),taew_extra_in_F=len(pF-pT),taew_F_pivot_on_cut_bar=(n-1) in pF,taew_missing_in_F=len(pT-pF),
        ar_raw_provisional=len(aT_raw-aF),ar_raw_missing=len(aF-aT_raw),ar_conf_equal=(aT==aF_conf),
        ewa_last_wave_unconfirmed=ewa_last_unconf,ewa_chain_changes_with_future=ewa_changed,junk_values=tot,junk_mismatch=dif))
R=pd.DataFrame(rows)
if len(R): R.to_csv(OUT+'leak_ew.csv',index=False)
if len(R):
  print(R.to_string())
  print('taew: setups where the full series has a pivot ON the cutoff bar (1-bar look-ahead if run on full data):',int(R.taew_F_pivot_on_cut_bar.sum()),'/30; other pivot diffs:',int((R.taew_missing_in_F>0).sum()))
  print('ElliottWaves raw: setups with provisional (later-vanishing) pivots in the last 7 bars:',int((R.ar_raw_provisional>0).sum()),'; with pivots only visible later:',int((R.ar_raw_missing>0).sum()),'; after our 7-bar shift identical to full-series pivots<=cut-7:',int(R.ar_conf_equal.sum()),'/30')
  print('EWA: last wave of the chain still open at the cutoff:',int(R.ewa_last_wave_unconfirmed.sum()),' chain changes once later bars exist:',int(R.ewa_chain_changes_with_future.sum()))
  print('junk determinism: values',int(R.junk_values.sum()),' mismatches',int(R.junk_mismatch.sum()))
# 3 equivalence vs the repo's brute force (short windows)
eq=[]; 
for _,r in samp.head(int(sys.argv[2]) if len(sys.argv)>2 else 8).iterrows():
    t=trunc(hist(r),r).iloc[-(int(sys.argv[3]) if len(sys.argv)>3 else 150):].copy(); t.index=range(len(t)); z=E.ar_pivots(t); smp=z[z.FlowMinMax!=0][['Close','FlowMinMax']].reset_index(drop=True)
    with contextlib.redirect_stdout(io.StringIO()):
        i_=E._src.index('\ndef ElliottWaveDiscovery('); exec(E._src[i_:E._src.index('# %%',i_)],E._AR)
        brute=E._AR['ElliottWaveDiscovery'](smp,'Close')
    mine=E.ar_waves(smp)
    b9={tuple(w) for w in brute if len(w)==9}; m9={tuple(w) for w in mine if len(w)==9}; b6={tuple(w[:6]) for w in brute}; m6={tuple(w[:6]) for w in mine}
    eq.append(dict(setup_id=r.setup_id,pivots=len(smp),brute_n=len(brute),dfs_n=len(mine),same9=b9==m9,same_impulses=b6==m6))
Q=pd.DataFrame(eq); print(Q.to_string()); Q.to_csv(OUT+'leak_ew_equivalence.csv',index=False)
