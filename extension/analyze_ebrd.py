from pathlib import Path
import sys,json,math
from pyxlsb import open_workbook
from openpyxl.utils import get_column_letter
import numpy as np,pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'code'))
from extract import read_book,coordinates
from run_analysis import permutation_shapley
R=Path(__file__).resolve().parent; rows=[];countries=[];checks=[]
for y in [2023,2024,2025]:
 if y==2023:
  c={}
  with open_workbook(str(R/'sources'/'ebrd2023.xlsb')) as book:
   with book.get_sheet('7. GPP Impact ') as sheet:
    for row in sheet.rows():
     for cell in row:
      if cell.v is not None:c[f'{get_column_letter(cell.c+1)}{cell.r+1}']={'value':cell.v}
 else:
  s=read_book(R/'sources'/f'ebrd{y}.xlsx')['7. GPP Impact'];c=s['cells']
 v=lambda ref:c.get(ref,{}).get('value')
 starts={str(x['value']):coordinates(ref)[0] for ref,x in c.items() if isinstance(x['value'],str) and x['value'].startswith('7.') and ref.startswith('A')}
 for r in range(starts['7.1 By GPP category']+1,starts['7.2 By country']):
  if v(f'A{r}') in ['Renewable Energy','Energy Efficiency','Grand Total']:
   rows.append(dict(year=y,category=v(f'A{r}'),projects=v(f'B{r}'),portfolio_eur=v(f'C{r}'),full_ghg_t=v(f'D{r}'),attributed_ghg_t=v(f'{"G" if y<=2024 else "F"}{r}'),source_sheet='7. GPP Impact',source_row=r))
 # country section 7.2 is explicitly renewable-energy only, excluding GEFFs
 start=starts['7.2 By country'];end=min(r for k,r in starts.items() if r>start)
 for r in range(start+1,end):
  if isinstance(v(f'B{r}'),(int,float)):
   countries.append(dict(year=y,country=v(f'A{r}'),projects=v(f'B{r}'),portfolio_eur=v(f'C{r}'),full_ghg_t=v(f'D{r}'),attributed_ghg_t=v(f'F{r}'),source_row=r))
a=pd.DataFrame(rows);ct=pd.DataFrame(countries)
for df in [a,ct]:
 df['full_intensity']=df.full_ghg_t/(df.portfolio_eur/1e6)
 df['attributed_intensity']=df.attributed_ghg_t/(df.portfolio_eur/1e6)
 df['effective_attribution_ratio']=df.attributed_ghg_t/df.full_ghg_t
for y in [2023,2024,2025]:
 cat=a[a.year==y].set_index('category');co=ct[(ct.year==y)&(ct.country!='Grand Total')];gt=ct[(ct.year==y)&(ct.country=='Grand Total')].iloc[0]
 for field in ['projects','portfolio_eur','full_ghg_t','attributed_ghg_t']:
  for x,z,label in [(co[field].sum(),gt[field],'country sum'),(gt[field],cat.loc['Renewable Energy',field],'country/category RE'),(cat.loc[['Renewable Energy','Energy Efficiency'],field].sum(),cat.loc['Grand Total',field],'category sum')]:
   if field!='projects': assert math.isclose(x,z,rel_tol=1e-12,abs_tol=1e-5),(y,field,label,x,z)
   checks.append(dict(year=y,field=field,check=label,residual=x-z,status='pass' if math.isclose(x,z,rel_tol=1e-12,abs_tol=1e-5) else 'source_count_discrepancy'))
# separate exact two-factor bridges: I_attributed = I_full * effective attribution ratio
bridges=[];all_co=[];loo=[]
for y0,y1 in [(2023,2024),(2024,2025)]:
 for category in a.category.unique():
  x,z=[a[(a.year==y)&(a.category==category)].iloc[0] for y in [y0,y1]]
  terms=permutation_shapley([x.full_intensity,x.effective_attribution_ratio],[z.full_intensity,z.effective_attribution_ratio])
  delta=z.attributed_intensity-x.attributed_intensity
  assert abs(terms.sum()-delta)<1e-8
  bridges.append(dict(period=f'{y0}_{y1}',category=category,full_intensity_change_pct=100*(z.full_intensity/x.full_intensity-1),attributed_intensity_change_pct=100*(z.attributed_intensity/x.attributed_intensity-1),full_intensity_term=terms[0],effective_attribution_term=terms[1],attributed_intensity_delta=delta))
 x,z=[ct[(ct.year==y)&(ct.country!='Grand Total')].set_index('country') for y in [y0,y1]]
 co=[]
 for country in sorted(set(x.index)|set(z.index)):
  if country in x.index and country in z.index:
   p,q=x.loc[country],z.loc[country];w0=p.portfolio_eur/x.portfolio_eur.sum();w1=q.portfolio_eur/z.portfolio_eur.sum();s0=p.attributed_intensity;s1=q.attributed_intensity
   co.append(dict(country=country,within_country=(w0+w1)/2*(s1-s0),country_mix=(s0+s1)/2*(w1-w0),entry=0.,exit=0.))
  elif country in z.index:
   q=z.loc[country];co.append(dict(country=country,within_country=0.,country_mix=0.,entry=q.attributed_ghg_t/(z.portfolio_eur.sum()/1e6),exit=0.))
  else:
   p=x.loc[country];co.append(dict(country=country,within_country=0.,country_mix=0.,entry=0.,exit=-p.attributed_ghg_t/(x.portfolio_eur.sum()/1e6)))
  p=x.drop(country,errors='ignore');q=z.drop(country,errors='ignore')
  full=100*((q.full_ghg_t.sum()/q.portfolio_eur.sum())/(p.full_ghg_t.sum()/p.portfolio_eur.sum())-1)
  attr=100*((q.attributed_ghg_t.sum()/q.portfolio_eur.sum())/(p.attributed_ghg_t.sum()/p.portfolio_eur.sum())-1)
  loo.append(dict(period=f'{y0}_{y1}',excluded_country=country,full_intensity_change_pct=full,attributed_intensity_change_pct=attr,opposite_sign=full*attr<0))
 co=pd.DataFrame(co);delta=z.attributed_ghg_t.sum()/(z.portfolio_eur.sum()/1e6)-x.attributed_ghg_t.sum()/(x.portfolio_eur.sum()/1e6)
 assert abs(co.iloc[:,1:].sum().sum()-delta)<1e-8
 co['period']=f'{y0}_{y1}';all_co.append(co)
co=pd.concat(all_co);pd.DataFrame(loo).to_csv(R/'results'/'ebrd_leave_one_country_out.csv',index=False)
for name,df in [('ebrd_category',a),('ebrd_country',ct),('ebrd_attribution_bridge',pd.DataFrame(bridges)),('ebrd_country_decomposition',co),('ebrd_reconciliation_checks',pd.DataFrame(checks))]:df.to_csv(R/'results'/f'{name}.csv',index=False)
print(a.to_string(index=False));print(pd.DataFrame(bridges).to_string(index=False));print('Country bridge:',co.groupby('period')[['within_country','country_mix','entry','exit']].sum().to_dict());print('Reconciliation checks',pd.DataFrame(checks).status.value_counts().to_dict());print('Opposite signs LOO',pd.DataFrame(loo).groupby('period').opposite_sign.agg(['sum','count']).to_dict())
