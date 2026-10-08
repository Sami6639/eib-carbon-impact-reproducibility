from pathlib import Path
import json,pandas as pd,numpy as np
R=Path(__file__).resolve().parent;D=pd.read_csv(R.parent/'ibrd/data/project_records.csv');A=D[D.year==2024].set_index('project_id');B=D[D.year==2025].set_index('project_id');L=pd.read_csv(R/'results/audit_ledger.csv').set_index('project_id');S=json.loads((R/'results/cost_summary.json').read_text())
def extreme(j,lo,hi,maximize):
 a=min(j);b=max(j)
 for _ in range(100):
  z=(a+b)/2;w=np.where((j-z>=0)==maximize,hi,lo);f=np.sum(w*(j-z))
  if f>0:a=z
  else:b=z
 return (a+b)/2
rows=[]
for label,ids in [('strict',S['strict_ids']),('expanded',S['expanded_ids'])]:
 j=(A.loc[ids].ghg/L.loc[ids].cost_usd_m).to_numpy();a=A.loc[ids].allocation_usd_m.to_numpy();b=B.loc[ids].allocation_usd_m.to_numpy();i0lo=extreme(j,a-.05,a+.05,False);i0hi=extreme(j,a-.05,a+.05,True);i1lo=extreme(j,b-.0000005,b+.0000005,False);i1hi=extreme(j,b-.0000005,b+.0000005,True)
 rows.append(dict(cohort=label,lower_change_pct=100*(i1lo/i0hi-1),upper_change_pct=100*(i1hi/i0lo-1),common_precision_change_pct=100*((np.round(b,1)@j/np.round(b,1).sum())/(np.round(a,1)@j/np.round(a,1).sum())-1)))
pd.DataFrame(rows).to_csv(R/'results/allocation_rounding_bounds.csv',index=False,float_format='%.12g');print(rows)
