"""Reproduce the EIB reporting census analysis. No original source is edited.
Usage: python code/run_analysis.py --source-dir PATH
"""
import argparse, itertools, json, math, sys, platform, os
os.environ.setdefault('MPLCONFIGDIR','/tmp/eib_matplotlib_config')
os.environ.setdefault('XDG_CACHE_HOME','/tmp/eib_cache')
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from extract import extract
ROOT=Path(__file__).resolve().parents[1]
DEFAULT_SOURCE=ROOT/'sources'
UNIT='tCO₂e/year per EUR million of project cost'


def save(df,name,folder='results'):
 df.to_csv(ROOT/folder/(name+'.csv'),index=False,float_format='%.12g')

def js(obj,name):
 (ROOT/'results'/f'{name}.json').write_text(json.dumps(obj,indent=2,default=lambda v: v.item() if isinstance(v,np.generic) else str(v),allow_nan=False))

def intensity(d,metric='relative',cost='eligible',denom='observed',weights=None):
 z=d[d.numeric_ghg].copy()
 c=z.project_cost_eur_m*(z.eligible_pct/100 if cost=='eligible' else 1)
 s=1000*z[metric+'_ghg_kt_year']/c
 a=z.allocation_eur_m if weights is None else z.project_id.map(weights)
 den=a.sum() if denom=='observed' else d.allocation_eur_m.sum()
 return float((a*s).sum()/den) if den else np.nan

def add_fields(d):
 d=d.copy();d['eligible_share']=d.eligible_pct/100
 d['eligible_cost_eur_m']=d.project_cost_eur_m*d.eligible_share
 d['sector']=d.sector_raw.str.extract(r'SECTION\s+([A-Z])',expand=False)
 names={'D':'Electricity and energy','H':'Transport and storage','F':'Construction','C':'Manufacturing','M':'Professional/RDI','E':'Water and waste','J':'Information and communication'}
 d['sector_name']=d.sector.map(names)
 d['renewable_generation']=d.activity.str.contains('Production of Electricity',na=False)
 for m in ['relative','absolute']:
  d[m+'_eligible_intensity']=1000*d[m+'_ghg_kt_year']/d.eligible_cost_eur_m
  d[m+'_whole_intensity']=1000*d[m+'_ghg_kt_year']/d.project_cost_eur_m
 return d

def permutation_shapley(v0,v1):
 """Exact symmetric product decomposition; factors are accounting inputs, not causes."""
 out=np.zeros(len(v0));perms=list(itertools.permutations(range(len(v0))))
 for order in perms:
  cur=np.array(v0,dtype=float)
  for k in order:
   before=np.prod(cur);cur[k]=v1[k];out[k]+=np.prod(cur)-before
 return out/len(perms)

def decomposition(d0,d1,metric='relative',matched=False,cost_basis='eligible'):
 a=d0[d0.numeric_ghg].set_index('project_id');b=d1[d1.numeric_ghg].set_index('project_id')
 common=sorted(set(a.index)&set(b.index))
 if matched:a=a.loc[common];b=b.loc[common]
 D0=a.allocation_eur_m.sum();D1=b.allocation_eur_m.sum();rows=[]
 for pid in sorted(set(a.index)|set(b.index)):
  row={'project_id':pid,'metric':metric,'matched_only':matched,'cost_basis':cost_basis,'period':f'{d0.report_year.iloc[0]}_{d1.report_year.iloc[0]}'}
  if pid in common:
   x,y=a.loc[pid],b.loc[pid];w0=x.allocation_eur_m/D0;w1=y.allocation_eur_m/D1
   s0=x[metric+'_'+cost_basis+'_intensity'];s1=y[metric+'_'+cost_basis+'_intensity']
   # Applicability was tested globally; sign and zero of G are unrestricted.
   part=permutation_shapley([1000*x[metric+'_ghg_kt_year'],1/x.project_cost_eur_m,1/x.eligible_share if cost_basis=='eligible' else 1],[1000*y[metric+'_ghg_kt_year'],1/y.project_cost_eur_m,1/y.eligible_share if cost_basis=='eligible' else 1])
   assert abs(part.sum()-(s1-s0))<1e-7
   row.update(name=y.project_name,status='numeric_continuer',ghg_revision=(w0+w1)/2*part[0],cost_update=(w0+w1)/2*part[1],eligibility_update=(w0+w1)/2*part[2],allocation_reweighting=(s0+s1)/2*(w1-w0),numeric_addition=0.,numeric_removal=0.)
  elif pid in b.index:
   y=b.loc[pid];st='report_entry' if pid not in set(d0.project_id) else 'new_numeric_disclosure'
   row.update(name=y.project_name,status=st,ghg_revision=0.,cost_update=0.,eligibility_update=0.,allocation_reweighting=0.,numeric_addition=y.allocation_eur_m/D1*y[metric+'_'+cost_basis+'_intensity'],numeric_removal=0.)
  else:
   x=a.loc[pid];st='report_exit' if pid not in set(d1.project_id) else 'numeric_disclosure_removed'
   row.update(name=x.project_name,status=st,ghg_revision=0.,cost_update=0.,eligibility_update=0.,allocation_reweighting=0.,numeric_addition=0.,numeric_removal=-x.allocation_eur_m/D0*x[metric+'_'+cost_basis+'_intensity'])
  row['total']=sum(row[k] for k in ['ghg_revision','cost_update','eligibility_update','allocation_reweighting','numeric_addition','numeric_removal']);rows.append(row)
 out=pd.DataFrame(rows)
 expected=intensity(b.reset_index(),metric,cost=cost_basis)-intensity(a.reset_index(),metric,cost=cost_basis)
 assert math.isclose(out.total.sum(),expected,abs_tol=1e-8)
 return out

def shapley_function(v0,v1,fn):
 out=np.zeros(len(v0));perms=list(itertools.permutations(range(len(v0))))
 for order in perms:
  cur=np.array(v0,dtype=float)
  for k in order:
   before=fn(cur);cur[k]=v1[k];out[k]+=fn(cur)-before
 return out/len(perms)


def comparison(label,a,b,cost='eligible',**extra):
 i0=intensity(a,cost=cost);i1=intensity(b,cost=cost)
 return dict(specification=label,intensity_2023=i0,intensity_2024=i1,signed_change=i1-i0,magnitude_change_pct=(abs(i1)/abs(i0)-1)*100,n_2023=int(a.numeric_ghg.sum()),n_2024=int(b.numeric_ghg.sum()),cost_denominator=cost,**extra)

def main(source_dir):
 for sub in ['data','results','figures']:(ROOT/sub).mkdir(exist_ok=True)
 raw,notes,hidden,summ,manifest=extract(source_dir)
 d=add_fields(pd.DataFrame(raw));summary=pd.DataFrame(summ)
 # Hard validity checks define the applicable domain of the decomposition.
 assert not d.duplicated(['report_year','stream','project_id']).any()
 assert np.isfinite(d[['project_cost_eur_m','eligible_pct','allocation_eur_m']]).all().all()
 assert (d.project_cost_eur_m>0).all() and d.eligible_pct.between(0.0000001,100).all() and (d.allocation_eur_m>0).all()
 assert d.numeric_ghg.equals(d.relative_ghg_kt_year.notna())
 assert d.numeric_ghg.equals(d.absolute_ghg_kt_year.notna())
 save(d,'project_report_stream_rows','data');save(pd.DataFrame(notes),'source_notes','data');save(pd.DataFrame(hidden),'hidden_merged_payloads','data')
 (ROOT/'data/source_manifest.json').write_text(json.dumps(manifest,indent=2))
 cab={y:d[(d.report_year==y)&(d.stream=='CAB')].copy() for y in [2022,2023,2024]}
 agg=[];cov=[];contributions=[]
 for (year,stream),z in d.groupby(['report_year','stream'],sort=True):
  A=z.allocation_eur_m.sum();An=z.loc[z.numeric_ghg,'allocation_eur_m'].sum()
  row=dict(report_year=year,stream=stream,projects=len(z),numeric_ghg_projects=int(z.numeric_ghg.sum()),allocation_eur_m=A,numeric_ghg_allocation_eur_m=An,allocation_coverage=An/A,record_coverage=z.numeric_ghg.mean(),eligible_lt100_projects=int((z.eligible_pct<100).sum()))
  for metric in ['relative','absolute']:
   pub=float(summary[(summary.report_year==year)&(summary.stream==stream)&(summary.metric==metric)].published.iloc[0])
   row[metric+'_published']=pub
   for den in ['all','observed']:row[metric+'_'+den]=intensity(z,metric,denom=den)
   row[metric+'_whole_cost']=intensity(z,metric,cost='whole')
   row[metric+'_published_minus_all']=pub-row[metric+'_all'];row[metric+'_published_minus_observed']=pub-row[metric+'_observed']
  agg.append(row)
  for (status,sector,financing),zz in z.groupby(['ghg_status','sector_name','financing_type']):
   cov.append(dict(report_year=year,stream=stream,ghg_status=status,sector_name=sector,financing_type=financing,projects=len(zz),allocation_eur_m=zz.allocation_eur_m.sum(),share_all_allocation=zz.allocation_eur_m.sum()/A))
  nz=z[z.numeric_ghg].copy();nz['observed_allocation_weight']=nz.allocation_eur_m/An;nz['all_allocation_weight']=nz.allocation_eur_m/A
  nz['relative_observed_contribution']=nz.observed_allocation_weight*nz.relative_eligible_intensity
  nz['relative_all_contribution']=nz.all_allocation_weight*nz.relative_eligible_intensity
  nz['absolute_contribution_share']=nz.relative_observed_contribution.abs()/nz.relative_observed_contribution.abs().sum()
  contributions.append(nz)
 agg=pd.DataFrame(agg);save(agg,'table1_coverage_and_intensities');save(pd.DataFrame(cov),'coverage_by_status_sector_financing')
 contribution=pd.concat(contributions,ignore_index=True);save(contribution,'project_contributions')
 # Exact observed-set and selected matched-set decompositions.
 all_decs=[];bridges=[];rulebridges=[];panels=[];matched_results=[];revision_counts=[]
 for y0,y1 in [(2022,2023),(2023,2024)]:
  a,b=cab[y0],cab[y1];common=set(a.project_id)&set(b.project_id);numeric=set(a.loc[a.numeric_ghg,'project_id'])&set(b.loc[b.numeric_ghg,'project_id'])
  for metric in ['relative','absolute']:
   for matched in [False,True]:
    for cost_basis in ['eligible','whole']:all_decs.append(decomposition(a,b,metric,matched,cost_basis))
  g0=agg[(agg.report_year==y0)&(agg.stream=='CAB')].iloc[0];g1=agg[(agg.report_year==y1)&(agg.stream=='CAB')].iloc[0]
  c0,c1=g0.allocation_coverage,g1.allocation_coverage;i0,i1=g0.relative_observed,g1.relative_observed
  br=dict(period=f'{y0}_{y1}',conditional_intensity_term=(c0+c1)/2*(i1-i0),coverage_term=(i0+i1)/2*(c1-c0),all_allocation_change=g1.relative_all-g0.relative_all,observed_change=i1-i0,published_change=g1.relative_published-g0.relative_published,published_minus_observed_trend_wedge=(g1.relative_published-g0.relative_published)-(i1-i0),published_minus_all_trend_wedge=(g1.relative_published-g0.relative_published)-(g1.relative_all-g0.relative_all),published_minus_observed_before=g0.relative_published-i0,published_minus_observed_after=g1.relative_published-i1,published_minus_all_before=g0.relative_published-g0.relative_all,published_minus_all_after=g1.relative_published-g1.relative_all)
  assert math.isclose(br['conditional_intensity_term']+br['coverage_term'],br['all_allocation_change'],abs_tol=1e-9);bridges.append(br)
  z0=0.;z1=1. if y1==2024 else 0.
  ruleparts=shapley_function([i0,c0,z0],[i1,c1,z1],lambda v:v[0]*(v[1]+(1-v[1])*v[2]))
  assert math.isclose(ruleparts.sum(),br['published_change'],abs_tol=1e-9)
  rulebridges.append(dict(period=f'{y0}_{y1}',conditional_intensity=ruleparts[0],allocation_coverage=ruleparts[1],inferred_denominator_rule=ruleparts[2],published_change=br['published_change'],inferred_observed_rule_before=z0,inferred_observed_rule_after=z1))
  amap=a.set_index('project_id');bmap=b.set_index('project_id')
  for pid in sorted(set(a.project_id)|set(b.project_id)):
   x=amap.loc[pid] if pid in amap.index else None;y=bmap.loc[pid] if pid in bmap.index else None
   panels.append(dict(period=f'{y0}_{y1}',project_id=pid,membership='continuing' if x is not None and y is not None else ('entry' if y is not None else 'exit'),status_before=x.ghg_status if x is not None else 'not_reported',status_after=y.ghg_status if y is not None else 'not_reported',allocation_before=x.allocation_eur_m if x is not None else 0,allocation_after=y.allocation_eur_m if y is not None else 0))
  x=a[a.project_id.isin(numeric)];y=b[b.project_id.isin(numeric)]
  w0=x.set_index('project_id').allocation_eur_m;w1=y.set_index('project_id').allocation_eur_m
  merged=x.merge(y,on='project_id',suffixes=('_before','_after'))
  rc=dict(period=f'{y0}_{y1}',numeric_pairs=len(numeric),shared_ids=len(common),report_entries=len(set(b.project_id)-set(a.project_id)),report_exits=len(set(a.project_id)-set(b.project_id)))
  for field in ['relative_ghg_kt_year','absolute_ghg_kt_year','project_cost_eur_m','eligible_pct','allocation_eur_m']:
   rc[field+'_changes_abs_gt_1e_minus8']=int(((merged[field+'_after']-merged[field+'_before']).abs()>1e-8).sum())
  rc['numeric_report_additions']=len(set(b.loc[b.numeric_ghg,'project_id'])-set(a.project_id));rc['numeric_report_exits']=len(set(a.loc[a.numeric_ghg,'project_id'])-set(b.project_id))
  rc['numeric_to_missing_continuers']=int(sum(amap.loc[pid].numeric_ghg and not bmap.loc[pid].numeric_ghg for pid in common));rc['missing_to_numeric_continuers']=int(sum(not amap.loc[pid].numeric_ghg and bmap.loc[pid].numeric_ghg for pid in common));revision_counts.append(rc)
  matched_results.append(dict(period=f'{y0}_{y1}',shared_ids=len(common),numeric_pairs=len(numeric),matched_allocation_before=x.allocation_eur_m.sum(),matched_allocation_after=y.allocation_eur_m.sum(),fraction_allocation_before=x.allocation_eur_m.sum()/a.allocation_eur_m.sum(),fraction_allocation_after=y.allocation_eur_m.sum()/b.allocation_eur_m.sum(),intensity_before=intensity(x),intensity_after=intensity(y),fixed_old_weights_after=intensity(y,weights=w0),fixed_new_weights_before=intensity(x,weights=w1)))
 dec=pd.concat(all_decs,ignore_index=True);save(dec,'project_exact_decompositions');save(pd.DataFrame(bridges),'coverage_convention_bridges');save(pd.DataFrame(rulebridges),'published_rule_shapley_bridge');save(pd.DataFrame(panels),'project_membership_transitions');save(pd.DataFrame(matched_results),'matched_panel_results');save(pd.DataFrame(revision_counts),'input_revision_and_membership_counts')
 columns=['ghg_revision','cost_update','eligibility_update','allocation_reweighting','numeric_addition','numeric_removal','total']
 dectable=dec.groupby(['period','metric','matched_only','cost_basis'])[columns].sum().reset_index();save(dectable,'table2_exact_decomposition')
 # Three-year selected balanced panel, fixed weighting and cost vintage.
 ids=set.intersection(*(set(z.loc[z.numeric_ghg,'project_id']) for z in cab.values()));base=cab[2022].set_index('project_id').loc[sorted(ids)]
 bal=[]
 for year,z in cab.items():
  x=z[z.project_id.isin(ids)].copy();frozen=x.copy();frozen.project_cost_eur_m=frozen.project_id.map(base.project_cost_eur_m);frozen.eligible_pct=frozen.project_id.map(base.eligible_pct)
  bal.append(dict(report_year=year,projects=len(x),allocation_eur_m=x.allocation_eur_m.sum(),annual_weights=intensity(x),fixed_2022_weights=intensity(x,weights=base.allocation_eur_m),fixed_2022_weights_cost_eligibility=intensity(frozen,weights=base.allocation_eur_m)))
 save(pd.DataFrame(bal),'balanced_three_year_panel')
 # Sector conditional profiles and symmetric mix/within-sector decomposition.
 sectors=[];sector_decomp=[]
 for year,z in cab.items():
  n=z[z.numeric_ghg];total=n.allocation_eur_m.sum()
  for sec,x in z.groupby('sector_name'):
   nn=x[x.numeric_ghg];sectors.append(dict(report_year=year,sector_name=sec,projects=len(x),numeric_projects=len(nn),allocation_eur_m=x.allocation_eur_m.sum(),numeric_allocation_eur_m=nn.allocation_eur_m.sum(),allocation_coverage=nn.allocation_eur_m.sum()/x.allocation_eur_m.sum(),observed_allocation_share=nn.allocation_eur_m.sum()/total,relative_intensity=intensity(x),whole_cost_intensity=intensity(x,cost='whole'),relative_contribution=(nn.allocation_eur_m*nn.relative_eligible_intensity).sum()/total))
 sectors=pd.DataFrame(sectors);save(sectors,'table3_sector_profiles')
 for sec in sorted(sectors.sector_name.unique()):
  x=sectors[(sectors.report_year==2023)&(sectors.sector_name==sec)].iloc[0];y=sectors[(sectors.report_year==2024)&(sectors.sector_name==sec)].iloc[0]
  if x.numeric_projects and y.numeric_projects:
   within=(x.observed_allocation_share+y.observed_allocation_share)/2*(y.relative_intensity-x.relative_intensity);mix=(x.relative_intensity+y.relative_intensity)/2*(y.observed_allocation_share-x.observed_allocation_share)
  else:within=np.nan;mix=np.nan
  sector_decomp.append(dict(sector_name=sec,within_sector=within,sector_allocation_mix=mix,contribution_change=y.relative_contribution-x.relative_contribution))
 sd=pd.DataFrame(sector_decomp);save(sd,'sector_exact_decomposition')
 # Prespecified cross-section/membership sensitivities.
 a,b=cab[2023],cab[2024];sens=[comparison('All observed CAB: eligible cost',a,b),comparison('All observed CAB: whole-project cost',a,b,cost='whole')]
 for label,fn in [('100% eligible in each year',lambda z:z.eligible_pct==100),('Renewable-generation activities',lambda z:z.renewable_generation),('Excluding manufacturing',lambda z:z.sector!='C'),('Investment loans',lambda z:z.financing_type=='Investment loan')]:
  sens.append(comparison(label,a[fn(a)],b[fn(b)]))
 paired=set(a.loc[a.numeric_ghg,'project_id'])&set(b.loc[b.numeric_ghg,'project_id'])
 sens.append(comparison('Numeric continuing CAB projects',a[a.project_id.isin(paired)],b[b.project_id.isin(paired)]))
 same100=set(a.loc[a.numeric_ghg&(a.eligible_pct==100),'project_id'])&set(b.loc[b.numeric_ghg&(b.eligible_pct==100),'project_id'])
 sens.append(comparison('Continuing and 100% eligible in both',a[a.project_id.isin(same100)],b[b.project_id.isin(same100)]))
 # Leave one ID out of BOTH periods, avoiding one-sided deletion bias.
 loo=[]
 for pid in sorted(set(a.project_id)|set(b.project_id)):
  r=comparison(pid,a[a.project_id!=pid],b[b.project_id!=pid]);r['project_id']=pid;r['change_from_full_delta']=r['signed_change']-sens[0]['signed_change'];loo.append(r)
 loo=pd.DataFrame(loo);save(loo,'leave_one_project_out')
 top=set()
 for z in [a,b]:
  zz=z[z.numeric_ghg];top |= set(zz.loc[(zz.allocation_eur_m*zz.relative_eligible_intensity).abs().nlargest(5).index,'project_id'])
 sens.append(comparison('Excluding union of annual top-five contributions',a[~a.project_id.isin(top)],b[~b.project_id.isin(top)]))
 # Winsorization of intensity changes target; retained only as a sensitivity.
 wins=[]
 for y,z in [(2023,a),(2024,b)]:
  zz=z[z.numeric_ghg].copy();lo,hi=zz.relative_eligible_intensity.quantile([.01,.99]);wins.append(float((zz.allocation_eur_m*zz.relative_eligible_intensity.clip(lo,hi)).sum()/zz.allocation_eur_m.sum()))
 sens.append(dict(specification='Annual 1st/99th percentile intensity winsorization',intensity_2023=wins[0],intensity_2024=wins[1],signed_change=wins[1]-wins[0],magnitude_change_pct=(abs(wins[1])/abs(wins[0])-1)*100,n_2023=int(a.numeric_ghg.sum()),n_2024=int(b.numeric_ghg.sum()),cost_denominator='eligible'))
 # Stream boundary: allocate finance once per project; do not sum GHG or C.
 e=d[(d.report_year==2024)&(d.stream=='EuGBS')];migrants=(set(a.project_id)&set(e.project_id))-set(b.project_id)
 sens.append(comparison('CAB excluding IDs migrating to EuGBS',a[~a.project_id.isin(migrants)],b[~b.project_id.isin(migrants)]))
 combined=[];duplicates=[]
 for pid,g in d[d.report_year==2024].groupby('project_id'):
  row=g[g.stream=='CAB'].iloc[0].copy() if (g.stream=='CAB').any() else g.iloc[0].copy();row.allocation_eur_m=g.allocation_eur_m.sum();row.stream='CAB+EuGBS';combined.append(row)
  if len(g)>1:duplicates.append(dict(project_id=pid,streams=';'.join(g.stream),allocation_eur_m=g.allocation_eur_m.sum(),eligible_pct_sum=g.eligible_pct.sum(),absolute_ghg_values=';'.join(map(str,g.absolute_ghg_kt_year)),relative_ghg_values=';'.join(map(str,g.relative_ghg_kt_year)),cost_values=';'.join(map(str,g.project_cost_eur_m))))
 combined=pd.DataFrame(combined)
 alternate=combined.copy()
 for pid in set(b.project_id)&set(e.project_id):
  for col in ['relative_ghg_kt_year','absolute_ghg_kt_year']:
   alternate.loc[alternate.project_id==pid,col]=e.loc[e.project_id==pid,col].iloc[0]
 duplicate_sensitivity=[]
 for metric in ['relative','absolute']:
  for rule,zz in [('CAB priority',combined),('EuGBS priority',alternate)]:
   duplicate_sensitivity.append(dict(metric=metric,duplicate_ghg_rule=rule,whole_cost_observed_intensity=intensity(zz,metric,cost='whole'),whole_cost_all_allocation_intensity=intensity(zz,metric,cost='whole',denom='all')))
 save(pd.DataFrame(duplicate_sensitivity),'duplicate_stream_ghg_precision_sensitivity')
 save(combined,'combined_2024_project_boundary_sensitivity','data');save(pd.DataFrame(duplicates),'duplicate_stream_reconciliation')
 sens.append(comparison('2024 CAB+EuGBS project boundary; whole cost',a,combined,cost='whole'))
 fixed=[]
 for boundary,bdata in [('CAB',b),('CAB+EuGBS project-deduplicated',combined)]:
  pair=set(a.loc[a.numeric_ghg,'project_id'])&set(bdata.loc[bdata.numeric_ghg,'project_id'])
  for cost_basis in ['eligible','whole'] if boundary=='CAB' else ['whole']:
   for exclude in [False,True] if boundary=='CAB' else [False]:
    subset=pair-{'20160845'} if exclude else pair
    x=a[a.project_id.isin(subset)].copy();y=bdata[bdata.project_id.isin(subset)].copy();xb=x.set_index('project_id');w=xb.allocation_eur_m
    before=intensity(x,cost=cost_basis);after=intensity(y,cost=cost_basis);fixedafter=intensity(y,cost=cost_basis,weights=w)
    w1=y.set_index('project_id').allocation_eur_m;fixedbefore=intensity(x,cost=cost_basis,weights=w1);wsym=(w/w.sum()+w1/w1.sum())/2
    symbefore=intensity(x,cost=cost_basis,weights=wsym);symafter=intensity(y,cost=cost_basis,weights=wsym)
    frozen=y.copy();frozen.project_cost_eur_m=frozen.project_id.map(xb.project_cost_eur_m);frozen.eligible_pct=frozen.project_id.map(xb.eligible_pct)
    frozenafter=intensity(frozen,cost=cost_basis,weights=w)
    fixed.append(dict(boundary_2024=boundary,cost_basis=cost_basis,exclude_normandie=exclude,numeric_pairs=len(subset),allocation_2023_eur_m=x.allocation_eur_m.sum(),allocation_2024_eur_m=y.allocation_eur_m.sum(),intensity_2023=before,annual_weight_intensity_2024=after,fixed_2023_weight_intensity_2024=fixedafter,fixed_2024_weight_intensity_2023=fixedbefore,symmetric_fixed_weight_intensity_2023=symbefore,symmetric_fixed_weight_intensity_2024=symafter,fixed_2024_weight_magnitude_change_pct=(abs(after/fixedbefore)-1)*100,symmetric_fixed_weight_magnitude_change_pct=(abs(symafter/symbefore)-1)*100,fixed_2023_weight_cost_eligibility_intensity_2024=frozenafter,annual_weight_magnitude_change_pct=(abs(after/before)-1)*100,fixed_weight_magnitude_change_pct=(abs(fixedafter/before)-1)*100,ghg_only_magnitude_change_pct=(abs(frozenafter/before)-1)*100))
    if boundary=='CAB' and not exclude:
     sens.append(dict(specification='Numeric continuing CAB: fixed 2023 weights; '+cost_basis+' cost',intensity_2023=before,intensity_2024=fixedafter,signed_change=fixedafter-before,magnitude_change_pct=(abs(fixedafter/before)-1)*100,n_2023=len(subset),n_2024=len(subset),cost_denominator=cost_basis))
    if boundary=='CAB' and cost_basis=='whole' and not exclude:
     for label,oldvalue,newvalue in [('annual weights',before,after),('fixed 2024 weights',fixedbefore,after)]:
      sens.append(dict(specification='Numeric continuing CAB: '+label+'; whole cost',intensity_2023=oldvalue,intensity_2024=newvalue,signed_change=newvalue-oldvalue,magnitude_change_pct=(abs(newvalue/oldvalue)-1)*100,n_2023=len(subset),n_2024=len(subset),cost_denominator='whole'))
  if boundary!='CAB':
   for label,oldvalue,value in [('annual weights',before,after),('fixed 2023 weights',before,fixedafter),('fixed 2024 weights',fixedbefore,after)]:
    sens.append(dict(specification='Numeric continuing combined boundary: '+label+'; whole cost',intensity_2023=oldvalue,intensity_2024=value,signed_change=value-oldvalue,magnitude_change_pct=(abs(value/oldvalue)-1)*100,n_2023=len(subset),n_2024=len(subset),cost_denominator='whole'))
 boundarydec=decomposition(a,combined,matched=True,cost_basis='whole');save(boundarydec,'combined_boundary_matched_decomposition')
 save(pd.DataFrame(fixed),'fixed_cohort_scope_controls')
 save(pd.DataFrame(sens),'deterministic_sensitivities_all')
 main_specs=['All observed CAB: eligible cost','All observed CAB: whole-project cost','100% eligible in each year','Renewable-generation activities','Numeric continuing CAB: annual weights; whole cost','Numeric continuing CAB: fixed 2023 weights; whole cost','Numeric continuing CAB: fixed 2024 weights; whole cost','Numeric continuing combined boundary: annual weights; whole cost','Numeric continuing combined boundary: fixed 2023 weights; whole cost','Numeric continuing combined boundary: fixed 2024 weights; whole cost']
 save(pd.DataFrame(sens).set_index('specification').loc[main_specs].reset_index(),'table4_deterministic_sensitivities')
 # Concentration uses absolute signed contributions; no negative-share paradox.
 conc=[]
 for (year,stream),z in contribution.groupby(['report_year','stream']):
  p=z.absolute_contribution_share.sort_values(ascending=False);aw=z.observed_allocation_weight
  conc.append(dict(report_year=year,stream=stream,top1_abs_contribution_share=p.iloc[0],top5_abs_contribution_share=p.head(5).sum(),top10_abs_contribution_share=p.head(10).sum(),abs_contribution_hhi=(p*p).sum(),allocation_hhi=(aw*aw).sum(),allocation_effective_project_count=1/(aw*aw).sum(),positive_relative_projects=int((z.relative_ghg_kt_year>0).sum()),zero_relative_projects=int((z.relative_ghg_kt_year==0).sum())))
 save(pd.DataFrame(conc),'concentration')
 # Missing-intensity scenarios; all values are stipulated inputs, not estimates/bounds.
 g0=agg[(agg.report_year==2023)&(agg.stream=='CAB')].iloc[0];g1=agg[(agg.report_year==2024)&(agg.stream=='CAB')].iloc[0]
 scenarios=[]
 for m0,m1 in itertools.product([-1000,-500,-250,0,250],repeat=2):
  full0=g0.relative_all+(1-g0.allocation_coverage)*m0;full1=g1.relative_all+(1-g1.allocation_coverage)*m1
  scenarios.append(dict(missing_intensity_2023=m0,missing_intensity_2024=m1,scenario_total_2023=full0,scenario_total_2024=full1,signed_change=full1-full0))
 save(pd.DataFrame(scenarios),'missing_intensity_scenarios')
 equal_missing=(g0.relative_all-g1.relative_all)/(g0.allocation_coverage-g1.allocation_coverage)
 tipping=[]
 for m0 in [-1000,-500,-250,0,250]:
  m1=(g0.relative_all+(1-g0.allocation_coverage)*m0-g1.relative_all)/(1-g1.allocation_coverage)
  tipping.append(dict(assumed_missing_intensity_2023=m0,tie_required_missing_intensity_2024=m1))
 save(pd.DataFrame(tipping),'missing_intensity_tipping_points')
 result=dict(primary=dict(published_magnitude_fall_pct=(1-abs(g1.relative_published/g0.relative_published))*100,observed_magnitude_fall_pct=(1-abs(g1.relative_observed/g0.relative_observed))*100,all_allocation_magnitude_fall_pct=(1-abs(g1.relative_all/g0.relative_all))*100,observed_delta=g1.relative_observed-g0.relative_observed,all_delta=g1.relative_all-g0.relative_all,coverage_change_pp=100*(g1.allocation_coverage-g0.allocation_coverage),coverage_2023=g0.allocation_coverage,coverage_2024=g1.allocation_coverage),missing_scenario=dict(equal_missing_intensity_tie=equal_missing,interpretation='Stipulated allocation-weighted missing-record expected intensity; not an estimate or physical bound.'),stream_boundary=dict(migrating_ids=sorted(migrants),migrating_projects=len(migrants),migrating_2023_allocation_eur_m=a[a.project_id.isin(migrants)].allocation_eur_m.sum(),migrating_2024_eugbs_allocation_eur_m=e[e.project_id.isin(migrants)].allocation_eur_m.sum(),combined_unique_projects=len(combined),combined_allocation_eur_m=combined.allocation_eur_m.sum()),leave_one_out=dict(min_signed_change=loo.signed_change.min(),max_signed_change=loo.signed_change.max(),min_magnitude_change_pct=loo.magnitude_change_pct.min(),max_magnitude_change_pct=loo.magnitude_change_pct.max(),most_influential_id=loo.loc[loo.change_from_full_delta.abs().idxmax(),'project_id']),cab_rows=int((d.stream=='CAB').sum()),numeric_cab_rows=int(((d.stream=='CAB')&d.numeric_ghg).sum()),hidden_subordinate_payloads=len(hidden),balanced_panel_projects=len(ids),runtime=dict(python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__,matplotlib=matplotlib.__version__))
 js(result,'key_results')
 # Machine-readable assertion log, rechecked in independent unittest script.
 tests=dict(unique_keys=True,source_hashes_match=True,positive_financial_denominators=True,merged_missingness_preserved=True,expected_counts=[len(cab[y]) for y in [2022,2023,2024]],numeric_counts=[int(cab[y].numeric_ghg.sum()) for y in [2022,2023,2024]],all_exact_decompositions=True,unresolved_2022_absolute_residual=float(agg.loc[(agg.report_year==2022)&(agg.stream=='CAB'),'absolute_published_minus_all'].iloc[0]))
 js(tests,'validation_assertions')
 make_figures(agg,dec,pd.DataFrame(cov),sectors,pd.DataFrame(sens))
 print(json.dumps(result,indent=2,default=lambda v:v.item() if isinstance(v,np.generic) else str(v)))


def make_figures(agg,dec,cov,sectors,sens):
 plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.titlesize':12,'axes.labelsize':10,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':220,'figure.facecolor':'white','axes.facecolor':'white','pdf.fonttype':42,'svg.fonttype':'none'})
 blue='#245B78';gold='#B18127';gray='#555B61';light='#B9CCD6'
 def finish(fig,name):
  fig.savefig(ROOT/'figures'/f'{name}.png',bbox_inches='tight');fig.savefig(ROOT/'figures'/f'{name}.pdf',bbox_inches='tight',metadata={'CreationDate':None,'ModDate':None});plt.close(fig)
 # Signed scale makes the negative convention explicit.
 fig,ax=plt.subplots(figsize=(8.2,4.6));z=agg[agg.stream=='CAB'];xs=np.arange(len(z));width=.24
 for k,(field,label,col) in enumerate([('relative_published','Published summary',gray),('relative_observed','Numeric-GHG allocations',blue),('relative_all','All allocations; disclosed numerator',gold)]):
  vals=z[field].values;bars=ax.bar(xs+(k-1)*width,vals,width,label=label,color=col)
  ax.bar_label(bars,labels=[f'{v:.1f}' for v in vals],padding=3,fontsize=9)
 ax.set_ylim(-355,0);ax.axhline(0,color=gray,lw=.7);ax.set_xticks(xs,z.report_year.astype(str));ax.set_ylabel('Signed reporting intensity\n(tCO₂e/year per EURm eligible project cost)');ax.set_title('Reporting conventions',loc='left');ax.legend(loc='lower left',bbox_to_anchor=(0,-.38),ncol=1,frameon=False);fig.subplots_adjust(bottom=.29);finish(fig,'figure1_conventions')
 # Exact 2023-24 bridge.
 x=dec[(dec.period=='2023_2024')&(dec.metric=='relative')&(~dec.matched_only)&(dec.cost_basis=='eligible')]
 vals=[x.ghg_revision.sum(),x.cost_update.sum(),x.eligibility_update.sum(),x.allocation_reweighting.sum(),x.numeric_addition.sum(),x.numeric_removal.sum()]
 labels=['GHG revisions','Project-cost updates','Eligibility updates','Continuing-project reweighting','Numeric-set additions','Numeric-set removals']
 fig,ax=plt.subplots(figsize=(8.2,4.8));bars=ax.barh(labels[::-1],vals[::-1],color=[blue if v<0 else gold for v in vals[::-1]]);ax.axvline(0,color=gray,lw=.8);ax.bar_label(bars,labels=[f'{v:+.2f}' for v in vals[::-1]],padding=4);ax.set_xlim(min(vals)-45,max(vals)+35);ax.set_xlabel('Contribution to signed intensity change\n(tCO₂e/year per EURm eligible project cost)');ax.set_title('Sources of reported change',loc='left');fig.subplots_adjust(bottom=.17,left=.33);finish(fig,'figure2_decomposition')
 fig,(ax,bx)=plt.subplots(1,2,figsize=(10.2,4.7),gridspec_kw={'width_ratios':[1,1.15]})
 statuses=['numeric','below_threshold','deferred_intermediated_framework','not_applicable','clarification_nondisclosure','withheld_external_review'];cols=[blue,gold,light,'#868A8F','#BDBDBD','#4A3A48'];labs=['Numeric GHG','Below threshold','Deferred','Not applicable','Other clarification','Withheld']
 bottom=np.zeros(3)
 for st,col,lab in zip(statuses,cols,labs):
  v=np.array([cov[(cov.report_year==y)&(cov.stream=='CAB')&(cov.ghg_status==st)].allocation_eur_m.sum() for y in [2022,2023,2024]])/1000
  ax.bar([2022,2023,2024],v,bottom=bottom,color=col,label=lab,width=.6);bottom+=v
 ax.set_xticks([2022,2023,2024]);ax.set_ylabel('CAB allocations (EUR billion)');ax.set_title('Allocation by disclosure status',loc='left');ax.legend(frameon=False,fontsize=8,loc='upper left',bbox_to_anchor=(-.02,-.17),ncol=2)
 sec=sectors[sectors.report_year.isin([2023,2024])].pivot(index='sector_name',columns='report_year',values='allocation_coverage').sort_values(2024)
 ypos=np.arange(len(sec));bx.barh(ypos-.16,sec[2023]*100,.3,color=light,label='2023');bx.barh(ypos+.16,sec[2024]*100,.3,color=blue,label='2024');bx.set_yticks(ypos,sec.index);bx.set_xlim(0,105);bx.set_xlabel('Allocation attached to numeric GHG (%)');bx.set_title('Main-activity disclosure coverage',loc='left');bx.legend(frameon=False)
 fig.suptitle('Disclosure coverage',x=.055,y=1.02,ha='left',fontsize=12);fig.subplots_adjust(wspace=.88,bottom=.24);finish(fig,'figure3_coverage')
 labels=['All observed CAB: eligible cost','All observed CAB: whole-project cost','100% eligible in each year','Renewable-generation activities','Numeric continuing CAB: annual weights; whole cost','Numeric continuing CAB: fixed 2023 weights; whole cost','Numeric continuing combined boundary: annual weights; whole cost','Numeric continuing combined boundary: fixed 2023 weights; whole cost','2024 CAB+EuGBS project boundary; whole cost']
 zz=sens.set_index('specification').loc[labels].iloc[::-1]
 short={'All observed CAB: eligible cost':'CAB: eligible cost','All observed CAB: whole-project cost':'CAB: whole cost','100% eligible in each year':'100% eligible each year','Renewable-generation activities':'Renewable generation','Excluding manufacturing':'Excluding manufacturing','Numeric continuing CAB projects':'48 pairs: annual weights','Numeric continuing CAB: annual weights; whole cost':'48 pairs: annual weights','Continuing and 100% eligible in both':'Continuing, 100% eligible','Numeric continuing CAB: fixed 2023 weights; whole cost':'48 pairs: fixed 2023 weights','Excluding union of annual top-five contributions':'Excluding annual top-five union','2024 CAB+EuGBS project boundary; whole cost':'Combined streams: whole cost','Numeric continuing combined boundary: annual weights; whole cost':'55 pairs: annual weights','Numeric continuing combined boundary: fixed 2023 weights; whole cost':'55 pairs: fixed 2023 weights'}
 fig,ax=plt.subplots(figsize=(8.5,5.2));v=zz.magnitude_change_pct;bars=ax.barh([short[k] for k in zz.index],v,color=[blue if k<0 else gold for k in v]);ax.axvline(0,color=gray,lw=.8);ax.bar_label(bars,labels=[f'{k:+.2f}%' for k in v],padding=4);ax.set_xlim(min(v)-13,max(8,max(v)+13));ax.set_xlabel('Change in relative-GHG intensity magnitude, 2023–2024 (%)');ax.set_title('Sensitivity comparisons',loc='left');fig.subplots_adjust(left=.4,bottom=.17);finish(fig,'figure4_sensitivity')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source-dir',type=Path,default=DEFAULT_SOURCE);main(p.parse_args().source_dir)
