"""Thin, PIT-safe adapters around three GitHub Elliott-wave repos. Each adapter receives ONLY bars <= the cutoff (x, a daily OHLCV
frame) and the trade direction, and returns a uniform state at the cutoff:
  state in {'w3' (waves 1-2 done, in wave 3), 'w5' (1-4 done, in wave 5), 'done' (5-wave impulse completed in the last 20 bars),
            'abc_done' (impulse + ABC completed in the last 20 bars), 'none'}
  plus levels for the level tests: tgt (wave target), inval (rule-based invalidation = wave-1 origin for w3, wave-1 end for w5),
  last (end of the last completed wave: wave-2 end for w3, wave-4 end for w5).
Shorts: prices are mirrored (p' = K - p, which keeps every Fibonacci/length ratio) and the library's upward logic is used; levels are
mapped back. Pivot lags (repaint control, see leak_ew.py): taew pivots need 1 later bar (never on the last bar of truncated data);
ElliottWaves (argrelextrema order=7, mode 'clip') can mark provisional pivots in the last 7 bars -> dropped; ElliottWaveAnalyzer
monowaves whose end is the LAST bar (hi()/lo() ran out of data, still extending) are unconfirmed -> treated as 'in progress'."""
import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import sys, io, contextlib, numpy as np, pandas as pd
sys.path.insert(0,(_SCANNER_ROOT + '/ta-repos-eval/repos/ElliottWaveAnalyzer')); sys.path.insert(0,(_SCANNER_ROOT + '/ta-repos-eval/repos/python-taew'))
from taew import ew as TAEW
from models.MonoWave import MonoWaveUp, MonoWaveDown
from models.WaveRules import Impulse
from models.WaveOptions import WaveOptionsGenerator5
from models.WavePattern import WavePattern
from scipy import signal
import math
_src=open((_SCANNER_ROOT + '/ta-repos-eval/repos/ElliottWaves/elliottwaves.py')).read()
_AR={'np':np,'pd':pd,'signal':signal,'math':math}
# only the function definitions (the module itself downloads data and runs a broken demo at import time)
for name in ('minmaxTwoMeasures','isMin','isMax','distance','isElliottWave','filterWaveSet','line','elliottWaveLinearRegressionError','findBestFitWave'):
    i=_src.index('def '+name+'('); j=_src.index('\ndef ',i+5) if '\ndef ' in _src[i+5:] else len(_src)
    k=_src.find('\n# %%',i); j=min(j,k) if k>0 else j
    exec(_src[i:j],_AR)
RECENT=20
def mirror(x):
    K=2*float(x.High.max())
    y=pd.DataFrame({'Open':K-x.Open,'High':K-x.Low,'Low':K-x.High,'Close':K-x.Close,'Volume':x.Volume},index=x.index)
    return y,K
def _back(v,K,sgn): return None if v is None else (v if sgn==1 else K-v)
def _quiet(f,*a):
    with contextlib.redirect_stdout(io.StringIO()): return f(*a)
# ---------------------------------------------------------------- python-taew (DrEdwardPCB, MIT)
def taew_state(x,sgn,W=120):
    y,K=(x,None) if sgn==1 else mirror(x); y=y.iloc[-W:]; v=list(y.Close.values.astype(float)); n=len(v); C=v[-1]
    best=None
    for c in _quiet(TAEW.Practical_ElliottWave5_label_upward,v):
        X,Z=c['x'],c['z']
        if not (Z[0]<Z[1]<Z[2]<Z[3]<Z[4]): continue          # the repo does not enforce time order
        if n-1-Z[4]>RECENT or min(v[Z[4]:])<X[4]: continue
        tgt=X[4]+(X[1]-X[0])
        if C>=tgt: continue
        k=(Z[4],X[3]-X[2])
        if best is None or k>best[0]: best=(k,'w5',tgt,X[1],X[4])
    if best is None:
        for c in _quiet(TAEW.Practical_ElliottWave3_label_upward,v):
            X,Z=c['x'],c['z']
            if not (Z[0]<Z[1]<Z[2]): continue
            if n-1-Z[2]>RECENT or min(v[Z[2]:])<X[2]: continue
            tgt=X[2]+1.618*(X[1]-X[0])
            if C>=tgt: continue
            k=(Z[2],X[1]-X[0])
            if best is None or k>best[0]: best=(k,'w3',tgt,X[0],X[2])
    if best is None:
        done=[c for c in _quiet(TAEW.Traditional_ElliottWave_label_upward,v) if len(c['z'])>=6 and all(np.diff(c['z'])>0) and n-1-c['z'][5]<=RECENT]
        if done: return dict(state='done',tgt=None,inval=None,last=None)
        return dict(state='none',tgt=None,inval=None,last=None)
    _,st,t,i_,l_=best
    return dict(state=st,tgt=_back(t,K,sgn),inval=_back(i_,K,sgn),last=_back(l_,K,sgn))
# ---------------------------------------------------------------- ElliottWaveAnalyzer (drstevendev, NO licence)
_OPTS=WaveOptionsGenerator5(6).options_sorted
_IMP=Impulse('impulse')
def _rules_ok(waves):
    """evaluate the repo's Impulse conditions that only involve the completed waves"""
    names={f'wave{i+1}' for i in range(len(waves))}; d={f'wave{i+1}':w for i,w in enumerate(waves)}
    for _,cnd in _IMP.conditions.items():
        if set(cnd['waves'])<=names and not cnd['function'](*[d[w] for w in cnd['waves']]): return False
    return True
def ewa_state(x,sgn,W=200):
    y,K=(x,None) if sgn==1 else mirror(x); y=y.iloc[-W:]
    lows=y.Low.values.astype(float); highs=y.High.values.astype(float); dates=np.arange(len(y)); n=len(y); C=float(y.Close.values[-1])
    i0=int(np.argmin(lows))
    if n-1-i0<5: return dict(state='none',tgt=None,inval=None,last=None)
    for opt in _OPTS:
        cfg=opt.values; waves=[]; s=i0; cur=None
        for wi in range(5):
            Cls=MonoWaveUp if wi%2==0 else MonoWaveDown
            w=Cls(lows=lows,highs=highs,dates=dates,idx_start=s,skip=cfg[wi])
            if w.idx_end is None or w.idx_end>=n-1: cur=wi+1; break     # no confirmed end -> this wave is in progress
            waves.append(w); s=w.idx_end
        if cur is None: cur=6
        if len(waves)<2 or not _rules_ok(waves): continue
        if cur==3:
            w1,w2=waves[0],waves[1]
            if lows[w2.idx_end:].min()<w2.low: continue
            tgt=w2.low+1.618*(w1.high-w1.low)
            if C>=tgt: continue
            return dict(state='w3',tgt=_back(tgt,K,sgn),inval=_back(w1.low,K,sgn),last=_back(w2.low,K,sgn),cfg=str(cfg))
        if cur==5:
            w1,w4=waves[0],waves[3]
            if lows[w4.idx_end:].min()<w4.low: continue
            tgt=w4.low+(w1.high-w1.low)
            if C>=tgt: continue
            return dict(state='w5',tgt=_back(tgt,K,sgn),inval=_back(w1.high,K,sgn),last=_back(w4.low,K,sgn),cfg=str(cfg))
        if cur==6 and WavePattern(waves).check_rule(_IMP) and n-1-waves[4].idx_end<=RECENT:
            return dict(state='done',tgt=None,inval=None,last=None,cfg=str(cfg))
    return dict(state='none',tgt=None,inval=None,last=None)
# ---------------------------------------------------------------- ElliottWaves (alessioricco, MIT)
ORDER=7
AR_RECENT=60
def ar_pivots(y):
    z=_AR['minmaxTwoMeasures'](y[['Close']].copy(),'Close','Close','FlowMinMax',ORDER)
    fm=z.FlowMinMax.values.copy(); fm[len(fm)-ORDER:]=0      # provisional pivots in the last ORDER bars (clip mode) dropped
    z['FlowMinMax']=fm
    return z
def ar_waves(samp):
    """same set as the repo's ElliottWaveDiscovery (9 nested loops) but enumerated depth-first with the repo's own monotone
    pre-conditions applied early; every candidate is accepted only if the repo's isElliottWave() returns it."""
    v=samp.Close.values; f=samp.FlowMinMax.values; n=len(v); mins=[i for i in range(n) if f[i]==-1]; maxs=[i for i in range(n) if f[i]==1]
    out=set()
    for i0 in mins:
        for i1 in (i for i in maxs if i>i0 and v[i]>v[i0]):
            for i2 in (i for i in mins if i>i1 and v[i0]<v[i]<v[i1]):
                for i3 in (i for i in maxs if i>i2 and v[i]>v[i2]):
                    for i4 in (i for i in mins if i>i3 and v[i1]<v[i]<v[i3]):
                        for i5 in (i for i in maxs if i>i4 and v[i]>v[i3]):
                            if not (v[i5]>max(v[i1],v[i2],v[i3],v[i4])): continue
                            # the repo only reports an impulse when some min/max/min triple follows it (any values): take the first
                            # type-valid triple for the 6-point result, then the value-pruned triples for 9-point (impulse+ABC) results
                            tri=None
                            for ia in (i for i in mins if i>i5):
                                ib=next((i for i in maxs if i>ia),None); ic=next((i for i in mins if ib is not None and i>ib),None)
                                if ic is not None: tri=(ia,ib,ic); break
                            if tri is None: continue
                            w=_AR['isElliottWave'](samp,'Close',i0,i1,i2,i3,i4,i5,*tri)
                            if w is None: continue
                            out.add(tuple(w[:6]))
                            for ia in (i for i in mins if i>i5 and v[i]<v[i5]):
                                for ib in (i for i in maxs if i>ia and v[ia]<v[i]<v[i5]):
                                    for ic in (i for i in mins if i>ib and v[i]<v[ia]):
                                        w=_AR['isElliottWave'](samp,'Close',i0,i1,i2,i3,i4,i5,ia,ib,ic)
                                        if w is not None: out.add(tuple(w))
    return [list(w) for w in out]
def ar_state(x,sgn,W=250):
    y,K=(x,None) if sgn==1 else mirror(x); y=y.iloc[-W:].copy(); y.index=range(len(y)); n=len(y)
    z=ar_pivots(y); samp=z[z.FlowMinMax!=0][['Close','FlowMinMax']]
    pos=samp.index.values
    waves=ar_waves(samp)
    # an impulse is only reported once 3 more pivots (>= 7 bars each) follow it, so 'recent' is wider here (AR_RECENT bars)
    nine=[w for w in waves if len(w)==9 and n-1-pos[w[-1]]<=AR_RECENT]
    six=[w for w in waves if len(w)>=6 and n-1-pos[w[5]]<=AR_RECENT]
    st='none'
    if nine: st='abc_done'
    elif six: st='impulse_seen'
    return dict(state=st,tgt=None,inval=None,last=None,n_patterns=len(waves))
