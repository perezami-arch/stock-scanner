import pandas as pd
exec(open('analysis.py').read().split("if __name__=='__main__':")[0])  # builds F with compliance
b=pd.read_csv('breadth_daily.csv',index_col=0,parse_dates=True)
aa=pd.read_csv('aaii_weekly.csv',parse_dates=['reported_date']).sort_values('reported_date')
for i,f in F.iterrows():
    if not isinstance(f.alert_date,str): continue
    A=pd.Timestamp(f.alert_date); x=b[b.index<A].iloc[-1]
    F.loc[i,['s5fi','s5th','s5tw']]=[x.S5FI,x.S5TH,x.S5TW]
    y=aa[aa.reported_date<A]
    if len(y): y=y.iloc[-1]; F.loc[i,['aaii_bull','aaii_bear','aaii_spread']]=[y.bullish,y.bearish,y.bullish-y.bearish]; F.loc[i,'aaii_date']=str(y.reported_date.date())
F.to_pickle('features4.pkl'); print(F.groupby('alert_date')[['s5fi','s5th','aaii_bear','aaii_spread']].first().round(1))
