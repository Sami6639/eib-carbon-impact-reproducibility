from pathlib import Path
import json,re,hashlib,itertools,math
from decimal import Decimal,getcontext
import pandas as pd,numpy as np,pdfplumber
R=Path(__file__).resolve().parent;L=json.loads((R/'audit_ledger.json').read_text());M=json.loads((R/'all_sources.json').read_text());checks=[]
def chk(label,ok,detail=''):
 checks.append({'check':label,'passed':bool(ok),'detail':str(detail)})
 if not ok:print('FAIL',label,detail)
for r in M:chk('sha256 '+r['file'],hashlib.sha256((R/'sources'/r['file']).read_bytes()).hexdigest()==r['sha256'])
norm=lambda s:re.sub(r'\s+','',s).replace(',','').replace('\u00ad','')
for r in L:
 for k in ['cost','ghg']:
  if k+'_file' not in r:continue
  with pdfplumber.open(R/'sources'/r[k+'_file']) as p:s=p.pages[r[k+'_pdf_page']-1].extract_text() or ''
  chk('second reader '+r['project_id']+' '+k,norm(r[k+'_token']) in norm(s))
  if k=='cost' and r.get('appraisal_token'):chk('appraisal token '+r['project_id'],norm(r['appraisal_token']) in norm(s))
 if r['ghg_class'] in ['annual_direct','annualized_lifetime','annual_components','interim_annual']:
  chk('quantity reconciliation '+r['project_id'],abs(r['source_ghg_quantity']/r['divisor']-r['annex_ghg'])<=.5)
# Additional semantics anchors independently parsed, distinct from a numeric-match claim.
anchors=[('P146194_ICR.pdf',21,['20 years']),('P149872_ICR.pdf',22,['Lifetime of 8 years']),('P107992_IEG.pdf',11,['15-year']),('P112578_ICR.pdf',34,['1,468','1,746']),('P148527_ICR.pdf',50,['1,831','15,850','2020']),('P110371_ICR.pdf',35,['Forecast CO2 emissions over 10','years in the cities','312,000']),('P164047_ICR.pdf',53,['five years','30 years','3.12 million']),('P150930_ICR.pdf',24,['20 years','599,858']),('P107159_ICR.pdf',51,['357.34','Total']),('P132741_ISR.pdf',4,['Tons/year','32,000','115,840'])]
for fn,pg,tokens in anchors:
 with pdfplumber.open(R/'sources'/fn) as p:s=p.pages[pg-1].extract_text() or ''
 chk('semantic locator '+fn+' '+str(pg),all(norm(t).lower() in norm(s).lower() for t in tokens))
# Independent exact arithmetic from the delivered ledger and original extracted records.
getcontext().prec=40;D=pd.read_csv(R.parent/'ibrd/data/project_records.csv').set_index(['year','project_id']);ll={r['project_id']:r for r in L};S=json.loads((R/'results/cost_summary.json').read_text());RR=pd.read_csv(R/'results/cost_results.csv').set_index('specification')
for cohort,label in [('strict','Strict annual and whole cost'),('expanded','Including reconstructed annual quantities')]:
 ids=S[cohort+'_ids'];vals={}
 for year in [2024,2025]:
  total=sum(Decimal(str(D.loc[(year,p),'allocation_usd_m'])) for p in ids);v=sum(Decimal(str(D.loc[(year,p),'allocation_usd_m']))/total*Decimal(str(D.loc[(year,p),'ghg']))/Decimal(str(ll[p]['cost_usd_m'])) for p in ids);vals[year]=v;chk(cohort+' intensity '+str(year),math.isclose(float(v),RR.loc[label,'before' if year==2024 else 'after'],abs_tol=1e-7))
 pct=(vals[2025]/vals[2024]-1)*100;chk(cohort+' change',math.isclose(float(pct),RR.loc[label,'annual_change_pct'],abs_tol=1e-10))
 chk(cohort+' unchanged GHG',all(D.loc[(2024,p),'ghg']==D.loc[(2025,p),'ghg'] for p in ids))
 # Exhaustive allocation corners independently verify the fractional-program bounds, 2^10 and 2^15.
 j=np.array([float(D.loc[(2024,p),'ghg'])/ll[p]['cost_usd_m'] for p in ids]);a=np.array([D.loc[(2024,p),'allocation_usd_m'] for p in ids]);b=np.array([D.loc[(2025,p),'allocation_usd_m'] for p in ids]);bits=np.array(list(itertools.product([-1,1],repeat=len(ids))));w=a+bits*.05;v0=w@j/w.sum(axis=1);w=b+bits*.0000005;v1=w@j/w.sum(axis=1);lo=100*(v1.min()/v0.max()-1);hi=100*(v1.max()/v0.min()-1);bounds=pd.read_csv(R/'results/allocation_rounding_bounds.csv').set_index('cohort').loc[cohort]
 chk(cohort+' rounding lower',math.isclose(lo,bounds.lower_change_pct,abs_tol=1e-10));chk(cohort+' rounding upper',math.isclose(hi,bounds.upper_change_pct,abs_tol=1e-10))
# Verify exact bridge from independently derived algebra, not production Shapley code.
bridge=pd.read_csv(R/'results/cost_decomposition.csv')
for label,g in bridge.groupby('specification'):
 chk('bridge '+label,math.isclose(g.total.sum(),RR.loc[label,'after']-RR.loc[label,'before'],abs_tol=1e-7))
 for _,q in g.iterrows():chk('component sum '+label+' '+q.project_id,math.isclose(q.total,q.ghg+q.denominator+q.reweighting,abs_tol=1e-9))
chk('audit census unique',len(L)==len(set(r['project_id'] for r in L))==31)
chk('cost source dates',all(r['cost_source_date']<='2024-06-30' for r in L if r['cost_accepted']))
out={'checks':len(checks),'passed':sum(c['passed'] for c in checks),'failed':sum(not c['passed'] for c in checks),'source_core_fields':sum(1 for r in L for k in ['cost','ghg'] if k+'_file' in r),'note':'Checks validate retrieved-file identity, extraction, selected semantic locators and arithmetic; manual scope judgements and physical counterfactuals are not proven by passing tests.','details':checks};(R/'results/deep_validation.json').write_text(json.dumps(out,indent=2));print({k:v for k,v in out.items() if k!='details'});assert not out['failed']
