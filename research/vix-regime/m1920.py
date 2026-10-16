import pandas as pd,numpy as np
exec(open('market.py').read().split('P={}')[0])   # reuse S, v, test, ep
def state(conf):
    s=np.zeros(len(v)); cur=0; vv_=v.values
    for i in range(len(v)):
        up=all(vv_[max(0,i-conf+1):i+1]>20) if i>=conf-1 else False
        dn=all(vv_[max(0,i-conf+1):i+1]<19) if i>=conf-1 else False
        if up: cur=1
        elif dn: cur=0
        s[i]=cur
    return pd.Series(s,index=v.index)
P={}
vf=v
for conf in (1,2):
    st=state(conf); ev_up=(st.diff()==1); ev_dn=(st.diff()==-1)
    n_up=int(ev_up.sum()); # whipsaw: state reverses within 10 trading days
    flips=np.where(st.diff().fillna(0).values!=0)[0]; w=sum(1 for a,b in zip(flips,flips[1:]) if b-a<=10)
    print(f'--- confirm={conf} close(s): fear-on events={n_up}, fear-off events={int(ev_dn.sum())}, whipsaws (flip back <=10d)={w}/{len(flips)} ({w/max(1,len(flips)):.0%})')
    si=S.index
    P[f'state{conf}']=test(st.loc[si].astype(bool),f'[{conf}c] fear state (>20 until <19): OFF-ON',-1)
    P[f'up{conf}']=test(ev_up.loc[si],f'[{conf}c] event UP through 20: OFF-ON',-1)
    P[f'dn{conf}']=test(ev_dn.loc[si],f'[{conf}c] event DOWN through 19: ON-OFF')
p=pd.Series(P).sort_values(); print('BH q:',(p*len(p)/np.arange(1,len(p)+1))[::-1].cummin()[::-1].round(3).to_dict())
for conf in (1,2): state(conf).to_csv(f'vix_zone_state_{conf}c.csv')
