from pathlib import Path
import itertools,json,math,sys
import numpy as np,pandas as pd
R=Path(__file__).resolve().parent
D=pd.read_csv(R/'data/project_records.csv')
OUT=R/'results';OUT.mkdir(exist_ok=True)
def save(x,n):x.to_csv(OUT/(n+'.csv'),index=False,float_format='%.12g')
def shapley(v0,v1):
 out=np.zeros(len(v0));pp=list(itertools.permutations(range(len(v0))))
 for order in pp:
  x=np.array(v0,float)
  for k in order:
   old=np.prod(x);x[k]=v1[k];out[k]+=np.prod(x)-old
 return out/len(pp)
def intensity(d,weights=None,adjust=False):
 w=d.allocation_usd_m if weights is None else weights.reindex(d.index)
 j=d.ghg/d.commitment_usd_m
 if adjust:j=j*d['share']/100
 return float((w*j).sum()/w.sum())
def result(a,b,label,adjust=False):
 i0=intensity(a,adjust=adjust);i1=intensity(b,adjust=adjust);fixed=intensity(b,a.allocation_usd_m,adjust);old_new=intensity(a,b.allocation_usd_m,adjust)
 w=(a.allocation_usd_m/a.allocation_usd_m.sum()+b.allocation_usd_m/b.allocation_usd_m.sum())/2
 freeze=b.copy();freeze['commitment_usd_m']=a.commitment_usd_m;freeze['share']=a['share']
 return dict(specification=label,n=len(a),before=i0,after=i1,annual_change_pct=100*(i1/i0-1),fixed_old_after=fixed,fixed_old_change_pct=100*(fixed/i0-1),fixed_new_change_pct=100*(i1/old_new-1),symmetric_change_pct=100*(intensity(b,w,adjust)/intensity(a,w,adjust)-1),frozen_finance_change_pct=100*(intensity(freeze,a.allocation_usd_m,adjust)/i0-1),allocation_before=a.allocation_usd_m.sum(),allocation_after=b.allocation_usd_m.sum())
def decompose(a,b,label,adjust=False):
 rows=[];wa=a.allocation_usd_m/a.allocation_usd_m.sum();wb=b.allocation_usd_m/b.allocation_usd_m.sum()
 for pid in a.index:
  x=a.loc[pid];y=b.loc[pid];v0=[x.ghg,1/x.commitment_usd_m];v1=[y.ghg,1/y.commitment_usd_m]
  if adjust:v0+=[x['share']/100];v1+=[y['share']/100]
  within=shapley(v0,v1)*(wa[pid]+wb[pid])/2
  rw=(np.prod(v0)+np.prod(v1))/2*(wb[pid]-wa[pid])
  rows.append(dict(specification=label,project_id=pid,country=x.country,status_before=x.status,status_after=y.status,ghg_update=within[0],commitment_update=within[1],share_update=within[2] if adjust else 0,allocation_reweighting=rw,total=within.sum()+rw))
 out=pd.DataFrame(rows);assert math.isclose(out.total.sum(),intensity(b,adjust=adjust)-intensity(a,adjust=adjust),abs_tol=1e-8);return out
A=D[D.year==2024].set_index('project_id');B=D[D.year==2025].set_index('project_id');ids=sorted(set(A.index)&set(B.index));a=A.loc[ids];b=B.loc[ids]
flow=pd.DataFrame({'project_id':ids,'id_conflict':a.id_conflict.values|b.id_conflict.values,'numeric_both':(a.ghg.notna()&b.ghg.notna()).values,'positive_finance_both':((a.commitment_usd_m>0)&(b.commitment_usd_m>0)&(a.allocation_usd_m>0)&(b.allocation_usd_m>0)).values,'same_status':(a.status==b.status).values})
flow['included_primary']=~flow.id_conflict&flow.numeric_both&flow.positive_finance_both&flow.same_status
save(flow,'sample_flow_project_level');valid=flow.loc[~flow.id_conflict&flow.numeric_both&flow.positive_finance_both,'project_id'];primary=flow.loc[flow.included_primary,'project_id'];a=A.loc[primary];b=B.loc[primary]
res=[];dec=[]
for label,sel in [('Primary stable status',primary),('All valid matched incl status transitions',valid),('Active in both reports',a[a.status=='active'].index),('Closed in both reports',a[a.status=='closed'].index),('Renewable energy and efficiency',a[a.category.str.contains('Renewable Energy')].index)]:
 x=A.loc[sel];y=B.loc[sel];res.append(result(x,y,label));dec.append(decompose(x,y,label))
res.append(result(a,b,'Primary with reported IBRD share adjustment',True));dec.append(decompose(a,b,'Primary with reported IBRD share adjustment',True))
# Common precision sensitivity: FY24 finance values to 0.1m, FY25 GHG to whole tonnes.
ar=a.copy();br=b.copy()
for z in [ar,br]:
 z['ghg']=z.ghg.round(0)
 for c in ['commitment_usd_m','allocation_usd_m']:z[c]=z[c].round(1)
assert (ar.commitment_usd_m>0).all() and (br.commitment_usd_m>0).all()
res.append(result(ar,br,'Common displayed precision'));dec.append(decompose(ar,br,'Common displayed precision'))
# Original IBRD share/full eligibility reporting fields held stable as stricter sensitivity.
sel=a.index[(a['share']==b['share'])&(a.eligible==b.eligible)];res.append(result(a.loc[sel],b.loc[sel],'Stable reported financing and eligibility shares'))
save(pd.DataFrame(res),'matched_results');save(pd.concat(dec),'matched_decomposition')
loo=[]
for pid in primary:
 r=result(a.drop(pid),b.drop(pid),pid);r['omitted_project']=pid;loo.append(r)
save(pd.DataFrame(loo),'leave_one_project_out')
lco=[]
for c in sorted(a.country.unique()):
 sel=a.index[a.country!=c];r=result(a.loc[sel],b.loc[sel],c);r['omitted_country']=c;lco.append(r)
save(pd.DataFrame(lco),'leave_one_country_out')
coverage=[]
for yr,x in [(2024,A),(2025,B)]:
 z=x.loc[primary];coverage.append(dict(year=yr,listed_records=len(x),numeric_ghg_records=x.ghg.notna().sum(),primary_n=len(z),primary_allocation=z.allocation_usd_m.sum(),listed_allocation=x.allocation_usd_m.sum(),allocation_coverage_pct=100*z.allocation_usd_m.sum()/x.allocation_usd_m.sum(),primary_ghg=z.ghg.sum(),listed_numeric_ghg=x.ghg.sum(),ghg_coverage_pct=100*z.ghg.sum()/x.ghg.sum()))
save(pd.DataFrame(coverage),'sample_coverage')
trans=sorted(set(valid)-set(primary));t=A.loc[trans][['name','status','ghg','allocation_usd_m']].join(B.loc[trans][['status','ghg','allocation_usd_m']],lsuffix='_2024',rsuffix='_2025');t['ghg_change_pct']=100*(t.ghg_2025/t.ghg_2024-1);save(t.reset_index(),'status_transitions')
save(D[D.id_conflict][['year','row_number','source_id','description_ids','name','ghg']],'identity_conflicts')
# Source totals differences retained; rounding tolerance based on contributing records.
checks=[]
T=pd.read_csv(R/'data/source_totals.csv')
for _,t in T.iterrows():
 z=D[(D.year==t.year)&(D.status==t.status)]
 for c in ['commitment','allocation','ghg']:
  v=float(str(t[c]).replace(',',''));s=z[c].sum();tol=(len(z)+1)*.05 if c!='ghg' else .5
  checks.append(dict(year=t.year,status=t.status,field=c,source=v,reconstructed=s,difference=s-v,tolerance=tol,within_rounding=abs(s-v)<=tol))
# FY25 main report page 43 gives net commitments 25,577 USDm; allocated is not outstanding balance.
s=D[D.year==2025].commitment_usd_m.sum();checks.append(dict(year=2025,status='all',field='commitment_usd_m_main_report_p43',source=25577,reconstructed=s,difference=s-25577,tolerance=.5,within_rounding=abs(s-25577)<=.5))
save(pd.DataFrame(checks),'source_reconciliation')
summary=dict(listed_records=D.groupby('year').size().to_dict(),common_ids=len(ids),numeric_both=int(flow.numeric_both.sum()),eligible_matched=len(valid),primary_n=len(primary),active_primary=int((a.status=='active').sum()),closed_primary=int((a.status=='closed').sum()),identity_conflict_records=int(D.id_conflict.sum()),matched_ghg_changed=int((a.ghg!=b.ghg).sum()),matched_ghg_changed_beyond_whole_tonne_rounding=int((a.ghg.round()!=b.ghg.round()).sum()),commitment_changed=int((a.commitment_usd_m!=b.commitment_usd_m).sum()),allocation_changed=int((a.allocation_usd_m!=b.allocation_usd_m).sum()),report_2025_removed_records=int(B.removed.sum()),transition_projects=trans,primary_result=res[0],project_loo=dict(n=len(loo),annual_min=min(x['annual_change_pct'] for x in loo),annual_max=max(x['annual_change_pct'] for x in loo),fixed_min=min(x['fixed_old_change_pct'] for x in loo),fixed_max=max(x['fixed_old_change_pct'] for x in loo)),country_loo=dict(n=len(lco),annual_min=min(x['annual_change_pct'] for x in lco),annual_max=max(x['annual_change_pct'] for x in lco),fixed_min=min(x['fixed_old_change_pct'] for x in lco),fixed_max=max(x['fixed_old_change_pct'] for x in lco)))
(OUT/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2));print(pd.DataFrame(res)[['specification','n','annual_change_pct','fixed_old_change_pct','frozen_finance_change_pct']].to_string(index=False));print(pd.concat(dec).groupby('specification')[['ghg_update','commitment_update','share_update','allocation_reweighting','total']].sum().to_string())
