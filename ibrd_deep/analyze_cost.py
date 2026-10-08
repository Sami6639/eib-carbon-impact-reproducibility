from pathlib import Path
import json,itertools,math
import numpy as np,pandas as pd
R=Path(__file__).resolve().parent;O=R/'results';D=pd.read_csv(R.parent/'ibrd/data/project_records.csv');L=pd.read_csv(O/'audit_ledger.csv').set_index('project_id');A=D[D.year==2024].set_index('project_id');B=D[D.year==2025].set_index('project_id')
strict=L.index[L.cost_accepted&L.same_status&(L.ghg_class=='annual_direct')];expanded=L.index[L.cost_accepted&L.same_status&L.ghg_class.isin(['annual_direct','annualized_lifetime','annual_components'])];allcost=L.index[L.cost_accepted&L.same_status]
def run(ids,label,basis='completion',fixed=True):
 a=A.loc[ids];b=B.loc[ids];c=L.loc[ids,'cost_usd_m' if basis=='completion' else 'appraisal_cost_usd_m'];g0=a.ghg.to_numpy();g1=b.ghg.to_numpy();w0=(a.allocation_usd_m/a.allocation_usd_m.sum()).to_numpy();w1=(b.allocation_usd_m/b.allocation_usd_m.sum()).to_numpy();c0=c.to_numpy() if fixed else a.commitment_usd_m.to_numpy();c1=c0 if fixed else b.commitment_usd_m.to_numpy();j0=g0/c0;j1=g1/c1;i0=float(w0@j0);i1=float(w1@j1);fx=float(w0@j1);fn=float(w1@j0);sym=(w0+w1)/2
 rows=[]
 for k,pid in enumerate(ids):
  vals0=[g0[k],1/c0[k]];vals1=[g1[k],1/c1[k]];sh=np.zeros(2)
  for order in itertools.permutations(range(2)):
   x=np.array(vals0)
   for z in order:
    before=np.prod(x);x[z]=vals1[z];sh[z]+=(np.prod(x)-before)/2
  sh*=sym[k];rw=(j0[k]+j1[k])/2*(w1[k]-w0[k]);rows.append(dict(specification=label,project_id=pid,ghg=sh[0],denominator=sh[1],reweighting=rw,total=sum(sh)+rw))
 assert math.isclose(sum(r['total'] for r in rows),i1-i0,abs_tol=1e-8)
 r=dict(specification=label,n=len(ids),before=i0,after=i1,annual_change_pct=100*(i1/i0-1),fixed_old_change_pct=100*(fx/i0-1),fixed_new_change_pct=100*(i1/fn-1),symmetric_change_pct=100*((sym@j1)/(sym@j0)-1),allocation_2024=a.allocation_usd_m.sum(),allocation_2025=b.allocation_usd_m.sum(),listed_coverage_2024_pct=100*a.allocation_usd_m.sum()/A.allocation_usd_m.sum(),listed_coverage_2025_pct=100*b.allocation_usd_m.sum()/B.allocation_usd_m.sum(),primary65_coverage_2024_pct=100*a.allocation_usd_m.sum()/6975.8,primary65_coverage_2025_pct=100*b.allocation_usd_m.sum()/7618.591354,countries=a.country.nunique())
 return r,rows
res=[];dec=[]
for ids,l,basis,fixed in [(strict,'Strict annual and whole cost','completion',True),(strict,'Same strict cohort eligible commitment','completion',False),(expanded,'Including reconstructed annual quantities','completion',True),(expanded,'Same expanded cohort eligible commitment','completion',False),(allcost,'All accepted costs reported numerator diagnostic','completion',True),(allcost,'Same all-cost cohort eligible commitment','completion',False)]:
 r,d=run(ids,l,basis,fixed);res.append(r);dec+=d
# Document-date guard and source-cost rounding.
early=[p for p in strict if L.loc[p,'cost_source_date']<='2024-06-30' and L.loc[p,'ghg_source_date']<='2024-06-30'];r,d=run(early,'Strict source documents dated by FY2024 end');res.append(r);dec+=d
app=[p for p in strict if pd.notna(L.loc[p,'appraisal_cost_usd_m'])];r,d=run(app,'Fixed appraisal cost on available strict cohort','appraisal');res.append(r);dec+=d;r,d=run(app,'Fixed completion cost same appraisal cohort');res.append(r);dec+=d
loo=[]
for label,ids in [('strict',strict),('expanded',expanded)]:
 for p in ids:r,_=run([i for i in ids if i!=p],label+'_omit_'+p);r['cohort']=label;r['omitted']=p;loo.append(r)
 for c in A.loc[ids].country.unique():
  sel=[i for i in ids if A.loc[i,'country']!=c]
  if sel:r,_=run(sel,label+'_omit_country_'+c);r['cohort']=label+'_country';r['omitted']=c;loo.append(r)
for name,rows in [('cost_results',res),('cost_decomposition',dec),('cost_leave_one_out',loo)]:pd.DataFrame(rows).to_csv(O/(name+'.csv'),index=False,float_format='%.12g')
# Remove flagged horizon/basis/unit conflicts from pre-existing 65 without pretending untraced active projects are validated.
primary=pd.read_csv(R.parent/'ibrd/results/sample_flow_project_level.csv');ids=primary.loc[primary.included_primary,'project_id'];flagged=L.index[L.same_status&L.ghg_class.isin(['horizon_conflict','basis_ambiguity','unit_ambiguity'])];clean=[p for p in ids if p not in flagged]
# run supports eligible commitment for IDs without cost by reindexing ledger.
oldL=L;L=L.reindex(ids);r,d=run(clean,'Original primary excluding identified basis flags','completion',False);L=oldL
pd.DataFrame([r]).to_csv(O/'flag_exclusion_sensitivity.csv',index=False,float_format='%.12g')
summary=dict(audit_projects=len(L),completion_documents_projects=30,interim_only_projects=1,accepted_costs=len(allcost),strict_n=len(strict),expanded_n=len(expanded),strict_ids=list(strict),expanded_ids=list(expanded),ghg_classes=L.ghg_class.value_counts().to_dict(),flagged_primary_ids=list(flagged),source_date_guard_n=len(early),unresolved_cost_projects=list(L.index[~L.cost_accepted]),source_files=len(json.loads((R/'all_sources.json').read_text())),unique_source_hashes=len(set(x['sha256'] for x in json.loads((R/'all_sources.json').read_text()))))
(O/'cost_summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2));print(pd.DataFrame(res)[['specification','n','before','after','annual_change_pct','fixed_old_change_pct']].to_string(index=False));print('FLAGS',r);print(pd.DataFrame(loo).groupby('cohort').annual_change_pct.agg(['min','max']).to_string())
