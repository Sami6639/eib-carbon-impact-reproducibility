from pathlib import Path
import pandas as pd,numpy as np,json,math,hashlib,itertools
R=Path(__file__).resolve().parent;D=pd.read_csv(R/'data/project_records.csv');A=D[D.year==2024].set_index('project_id');B=D[D.year==2025].set_index('project_id');F=pd.read_csv(R/'results/sample_flow_project_level.csv');checks=[]
def ck(name,condition):
 checks.append(dict(name=name,passed=bool(condition)))
 if not condition:raise AssertionError(name)
ck('unique_project_year',not D.duplicated(['year','project_id']).any());ck('FY24_row_sequence',set(A.row_number)==set(range(1,147)));ck('FY25_row_sequence',set(B.row_number)==set(range(1,162)))
# Independent two-factor closed-form and exact subset-weighted Shapley (not permutation implementation).
M=pd.read_csv(R/'results/matched_decomposition.csv')
for label,g in M.groupby('specification'):
 ids=g.project_id.tolist();a=A.loc[ids].copy();b=B.loc[ids].copy();adjust='share adjustment' in label
 if label=='Common displayed precision':
  for z in [a,b]:
   z['ghg']=z.ghg.round();z['commitment_usd_m']=z.commitment_usd_m.round(1);z['allocation_usd_m']=z.allocation_usd_m.round(1)
 wa=a.allocation_usd_m/a.allocation_usd_m.sum();wb=b.allocation_usd_m/b.allocation_usd_m.sum()
 for _,r in g.iterrows():
  x,y=a.loc[r.project_id],b.loc[r.project_id];u=[x.ghg,1/x.commitment_usd_m];v=[y.ghg,1/y.commitment_usd_m]
  if adjust:u.append(x['share']/100);v.append(y['share']/100)
  n=len(u);parts=[]
  for k in range(n):
   others=[j for j in range(n) if j!=k];val=0.
   for ss in range(n):
    for subset in itertools.combinations(others,ss):
     coef=math.factorial(ss)*math.factorial(n-ss-1)/math.factorial(n)
     prod=math.prod(v[j] if j in subset else u[j] for j in others)
     val+=coef*(v[k]-u[k])*prod
   parts.append(val*(wa[r.project_id]+wb[r.project_id])/2)
  terms=[r.ghg_update,r.commitment_update]+([r.share_update] if adjust else [])
  ck('independent_components_'+label+'_'+r.project_id,np.allclose(parts,terms,atol=1e-7,rtol=1e-9))
  rw=(math.prod(u)+math.prod(v))/2*(wb[r.project_id]-wa[r.project_id]);ck('independent_weight_'+label+'_'+r.project_id,math.isclose(rw,r.allocation_reweighting,abs_tol=1e-7,rel_tol=1e-9))
 total=((b.ghg/b.commitment_usd_m)*(b['share']/100 if adjust else 1)*wb).sum()-((a.ghg/a.commitment_usd_m)*(a['share']/100 if adjust else 1)*wa).sum();ck('exact_sum_'+label,math.isclose(total,g.total.sum(),abs_tol=1e-7))
ids=F[F.included_primary].project_id;a=A.loc[ids];b=B.loc[ids];ck('all_primary_GHG_equal_at_whole_tonne_precision',np.array_equal(a.ghg.round(),b.ghg.round()));ck('same_status_primary',(a.status==b.status).all());ck('primary_no_conflicting_id',not a.id_conflict.any() and not b.id_conflict.any());ck('primary_positive_denominators',(a.commitment_usd_m>0).all() and (b.commitment_usd_m>0).all())
for m in json.loads((R/'source_manifest.json').read_text()):ck('source_sha256_'+m['file'],hashlib.sha256((R/'sources'/m['file']).read_bytes()).hexdigest()==m['sha256'])
for _,r in pd.read_csv(R/'results/source_reconciliation.csv').iterrows():ck('source_rounding_'+str(r.year)+'_'+r.status+'_'+r.field,r.within_rounding)
res=dict(check_count=len(checks),passed=sum(x['passed'] for x in checks),checks=checks,limits=['Reporting-vintage accounting, not causal identification','Eligible commitment denominator differs from EIB project cost','Primary numerical GHG stability only at common displayed precision','Four status transitions and identity conflicts excluded from primary','FY25 finance footnote unit conflict retained; USD scaling supported by header and main-report commitment total'])
(R/'results/analysis_validation.json').write_text(json.dumps(res,indent=2));print('Independent analysis checks',len(checks),'passed')
