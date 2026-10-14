"""PIT wrapper around smartmoneyconcepts (joshyattridge, MIT) + agreement with scanner_geometry.
leak_ta.py shows that EVERY smc output changes when later bars exist (centred swing window shift(-L/2), FVG uses the next candle,
Mitigated/Broken/Swept indices are searched in later bars, liquidity range = 1% of the WHOLE series' range, and the swing
function stamps an artificial swing on the very last bar). The wrapper therefore:
  * runs smc only on the history truncated at the rule bar (a live scan),
  * removes the artificial swings that swing_highs_lows() stamps on bar 0 and the LAST bar (never confirmed),
  * uses swing_length=10 (a swing at bar i is confirmed at i+5 <= cutoff), close-break BOS/CHoCH, OB with wick mitigation,
  * treats an FVG / OB / liquidity level as 'open' only if its mitigation/sweep index is 0 (= not hit up to the cutoff)."""
import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import sys, numpy as np, pandas as pd, warnings, io, contextlib
warnings.filterwarnings('ignore')
sys.path.insert(0,(_SCANNER_ROOT + '/ta-repos-eval'))
from common import *
with contextlib.redirect_stdout(io.StringIO()): from smartmoneyconcepts import smc
from multiprocessing import Pool
SL=10
def smc_pit(x):
    o=x.copy(); o.columns=[q.lower() for q in o.columns]; o=o.reset_index(drop=True); n=len(o)
    sw=smc.swing_highs_lows(o,swing_length=SL).copy()
    art_last=bool(pd.notna(sw.HighLow.iloc[-1]))
    sw.iloc[0]=np.nan; sw.iloc[-1]=np.nan
    return o,n,sw,smc.fvg(o),smc.bos_choch(o,sw,close_break=True),smc.ob(o,sw),smc.liquidity(o,sw,range_percent=0.01),smc.retracements(o,sw),art_last
def feat(r):
    out=dict(setup_id=r['setup_id'])
    try:
        x=trunc(hist(r),r)
        if len(x)<60: out['smc_error']='short'; return out
        o,n,sw,fv,bc,ob,lq,rt,art=smc_pit(x)
        c=o.close.values; h=o.high.values; l=o.low.values; A=atr14(h,l,c)[-1]; C=c[-1]
        out.update(smc_last_bar=str(x.index[-1].date()),smc_artificial_last_swing=art,_A=A,_C=C)
        # swings (confirmed)
        sh=[(i,o.high[i]) for i in np.where(sw.HighLow==1)[0]]; sl_=[(i,o.low[i]) for i in np.where(sw.HighLow==-1)[0]]
        out['_swing_highs']=[p for i,p in sh]; out['_swing_lows']=[p for i,p in sl_]
        # BOS / CHoCH: order events by the bar that broke the level (all <= cutoff by construction)
        ev=bc.dropna(subset=['BrokenIndex']); ev=ev.assign(dir=ev.BOS.fillna(ev.CHOCH),kind=np.where(ev.CHOCH.notna(),'choch','bos')).sort_values('BrokenIndex')
        if len(ev):
            e=ev.iloc[-1]; out['smc_last_break_dir']=float(e.dir); out['smc_last_break_kind']=e.kind; out['smc_bars_since_break']=float(n-1-e.BrokenIndex)
            out['smc_breaks_last20_net']=float(ev[ev.BrokenIndex>=n-20].dir.sum())
        # FVG open (unmitigated up to the cutoff)
        f=fv.dropna(subset=['FVG']); f=f[f.MitigatedIndex==0]
        out['smc_fvg_open_n']=len(f)
        ab=f[f.Bottom>C]; be=f[f.Top<C]; inside=f[(f.Bottom<=C)&(f.Top>=C)]
        out['smc_in_fvg']=len(inside)>0
        out['_fvg_above_lo']=float(ab.Bottom.min()) if len(ab) else np.nan; out['_fvg_above_type']=float(ab.loc[ab.Bottom.idxmin(),'FVG']) if len(ab) else np.nan
        out['_fvg_below_hi']=float(be.Top.max()) if len(be) else np.nan; out['_fvg_below_type']=float(be.loc[be.Top.idxmax(),'FVG']) if len(be) else np.nan
        # OB active (not mitigated)
        b=ob.dropna(subset=['OB']); b=b[b.MitigatedIndex==0]
        out['smc_ob_open_n']=len(b)
        bull=b[(b.OB==1)&(b.Top<=C)]; bear=b[(b.OB==-1)&(b.Bottom>=C)]
        out['_ob_below_lo']=float(bull.loc[bull.Top.idxmax(),'Bottom']) if len(bull) else np.nan; out['_ob_below_hi']=float(bull.Top.max()) if len(bull) else np.nan
        out['_ob_above_hi']=float(bear.loc[bear.Bottom.idxmin(),'Top']) if len(bear) else np.nan; out['_ob_above_lo']=float(bear.Bottom.min()) if len(bear) else np.nan
        out['smc_ob_strength_below']=float(bull.loc[bull.Top.idxmax(),'Percentage']) if len(bull) else np.nan
        out['smc_ob_strength_above']=float(bear.loc[bear.Bottom.idxmin(),'Percentage']) if len(bear) else np.nan
        # liquidity (>=2 swings within 1% of the range); open = not swept up to the cutoff
        q=lq.dropna(subset=['Liquidity'])
        op=q[q.Swept==0]; out['smc_liq_open_n']=len(op)
        out['_liq_above']=sorted(op[(op.Liquidity==1)&(op.Level>C)].Level.tolist()); out['_liq_below']=sorted(op[(op.Liquidity==-1)&(op.Level<C)].Level.tolist())
        rs=q[(q.Swept>0)&(q.Swept>=n-3)]
        out['smc_swept_last3_bsl']=bool((rs.Liquidity==1).any()); out['smc_swept_last3_ssl']=bool((rs.Liquidity==-1).any())
        out['smc_ret_dir']=float(rt.Direction.iloc[-1]) if pd.notna(rt.Direction.iloc[-1]) else np.nan
        out['smc_ret_current']=float(rt['CurrentRetracement%'].iloc[-1]); out['smc_ret_deepest']=float(rt['DeepestRetracement%'].iloc[-1])
    except Exception as e: out['smc_error']=f'{e.__class__.__name__}: {e}'
    return out
if __name__=='__main__':
    recs=S[['setup_id','ticker','asset','rule_bar_actual']].to_dict('records')
    with Pool(2) as p: res=p.map(feat,recs,chunksize=10)
    X=pd.DataFrame(res); X.to_pickle(OUT+'smc_features.pkl')
    print(X.shape,'errors:',X.get('smc_error',pd.Series(dtype=object)).notna().sum(), ' artificial last-bar swing stamped:',X.smc_artificial_last_swing.mean())
    print(X.describe(include='all').T.to_string())
