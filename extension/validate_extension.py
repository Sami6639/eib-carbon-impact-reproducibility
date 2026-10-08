from pathlib import Path
import math,json,sys,hashlib
import pandas as pd,openpyxl
R=Path(__file__).resolve().parent
# Independent source reads and calculations, without production analysis imports.
a=pd.read_csv(R/'results/ebrd_category.csv');checks=[]
for y in [2024,2025]:
 w=openpyxl.load_workbook(R/'sources'/f'ebrd{y}.xlsx',data_only=True);s=w['7. GPP Impact'];r0=41 if y==2024 else 40
 for j,cat in enumerate(['Renewable Energy','Energy Efficiency','Grand Total']):
  r=r0+j;z=a[(a.year==y)&(a.category==cat)].iloc[0]
  for field,col in [('projects','B'),('portfolio_eur','C'),('full_ghg_t','D'),('attributed_ghg_t','G' if y==2024 else 'F')]:
   assert math.isclose(z[field],s[f'{col}{r}'].value,rel_tol=1e-12,abs_tol=1e-6);checks.append(f'openpyxl_{y}_{cat}_{field}')
 b0=s[f'C{r0}'].value;g=s[f'D{r0}'].value;q=s[f'{"G" if y==2024 else "F"}{r0}'].value
 assert math.isclose(q/(b0/1e6),a[(a.year==y)&(a.category=='Renewable Energy')].attributed_intensity.iloc[0],rel_tol=1e-12)
b=pd.read_csv(R/'results/ebrd_attribution_bridge.csv')
for _,z in b.iterrows():
 y0,y1=map(int,z.period.split('_'));x,t=[a[(a.year==y)&(a.category==z.category)].iloc[0] for y in [y0,y1]]
 full=.5*(x.effective_attribution_ratio+t.effective_attribution_ratio)*(t.full_intensity-x.full_intensity)
 ratio=.5*(x.full_intensity+t.full_intensity)*(t.effective_attribution_ratio-x.effective_attribution_ratio)
 assert abs(full-z.full_intensity_term)<1e-8 and abs(ratio-z.effective_attribution_term)<1e-8
 assert abs(full+ratio-(t.attributed_intensity-x.attributed_intensity))<1e-8;checks.append(f'independent_bridge_{z.period}_{z.category}')
# Explicit source-anomaly checks preserve the original values.
v=pd.read_csv(R/'results/ebrd_reconciliation_checks.csv');flags=v[v.status!='pass'];assert len(flags)==1 and flags.iloc[0].year==2024 and flags.iloc[0].residual==1
w=openpyxl.load_workbook(R/'sources/nib2011_2025.xlsx',data_only=False);s=w.worksheets[0]
assert s['H20'].value=='=SUM(H8:H19)'
c=openpyxl.load_workbook(R/'sources/nib2011_2025.xlsx',data_only=True).worksheets[0]
assert c['H11'].value==sum(c[f'H{r}'].value for r in range(12,17))==1054420
assert sum(c[f'H{r}'].value for r in [8,9,10,11,17,18,19])==1267600
assert c['H20'].value==2322020
checks+=['NIB_shared_formula_expanded','NIB_parent_equals_children','NIB_disjoint_sum','NIB_cached_published_value']
for obj in json.loads((R/'source_manifest.json').read_text()):
 p=R/'sources'/obj['name'];assert hashlib.sha256(p.read_bytes()).hexdigest()==obj['sha256'];checks.append('sha256_'+obj['name'])
report=dict(status='passed',checks=len(checks),check_names=checks,source_exceptions=['EBRD 2024 category count 195 versus general count 194; no forced reconciliation','NIB hierarchy totals preserved; non-overlapping sums reported as analyst diagnostics'],interpretation_limits=['EBRD country groups are not a project panel','NIB historical cohort title is not a longitudinal panel','EIB 2025 workbook unavailable; no 2025 EIB estimate'])
(R/'results/extension_validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
