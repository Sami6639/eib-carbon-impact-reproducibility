"""Independent import and exact identity regression tests; standard-library unittest."""
import hashlib, itertools, json, math, os, sys, unittest
from pathlib import Path
from decimal import Decimal
import numpy as np
import pandas as pd
import openpyxl
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'code'))
from extract import SOURCES,extract
from run_analysis import permutation_shapley,shapley_function,intensity
SOURCE=Path(os.getenv('EIB_SOURCE_DIR',str(ROOT/'sources')))

class EIBTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.d=pd.read_csv(ROOT/'data/project_report_stream_rows.csv',dtype={'project_id':str})
  cls.a=pd.read_csv(ROOT/'results/table1_coverage_and_intensities.csv')
 def test_01_source_integrity(self):
  for file,sha,url in SOURCES.values():self.assertEqual(hashlib.sha256((SOURCE/file).read_bytes()).hexdigest(),sha)
 def test_02_population(self):
  self.assertEqual(len(self.d),475);self.assertEqual(len(self.d[self.d.stream=='CAB']),461)
  self.assertFalse(self.d.duplicated(['report_year','stream','project_id']).any())
  self.assertEqual(self.d[self.d.stream=='CAB'].groupby('report_year').numeric_ghg.sum().tolist(),[93,116,109])
 def test_03_independent_openpyxl_cell_import(self):
  checked=0
  for year,(file,_,_) in SOURCES.items():
   w=openpyxl.load_workbook(SOURCE/file,data_only=True,read_only=False)
   for r in self.d[self.d.report_year==year].itertuples():
    sh=w[r.source_sheet];source_row=r.source_row
    for col,field in [('J','project_cost_eur_m'),('O','eligible_pct'),('P','absolute_ghg_kt_year'),('Q','relative_ghg_kt_year'),('R','allocation_eur_m')]:
     raw=sh[f'{col}{source_row}'].value;v=getattr(r,field)
     if isinstance(raw,(int,float)):self.assertTrue(math.isclose(raw,v,rel_tol=1e-10,abs_tol=1e-8),(r.project_id,col,raw,v))
     else:self.assertTrue(pd.isna(v),(r.project_id,col,raw,v))
     checked+=1
  self.assertEqual(checked,475*5)
 def test_04_hidden_merged_zeros(self):
  h=pd.read_csv(ROOT/'data/hidden_merged_payloads.csv',dtype={'project_id':str})
  self.assertEqual(len(h),12);self.assertTrue((h.hidden_raw==0).all())
  z=self.d[(self.d.report_year==2024)&(self.d.stream=='CAB')].set_index('project_id').loc[h.project_id]
  self.assertTrue(z.relative_ghg_kt_year.isna().all());self.assertTrue((z.ghg_status=='below_threshold').all())
 def test_05_financial_domain(self):
  self.assertTrue((self.d.project_cost_eur_m>0).all());self.assertTrue((self.d.allocation_eur_m>0).all());self.assertTrue(self.d.eligible_pct.between(0.000001,100).all())
  np.testing.assert_allclose(self.d.eligible_cost_eur_m,self.d.project_cost_eur_m*self.d.eligible_pct/100,rtol=1e-10)
 def test_06_published_decimal_reconstruction(self):
  # This arithmetic path uses independently imported visible Excel cells, not extracted CSV GHG.
  for year,(file,_,_) in SOURCES.items():
   if year==2022:continue
   w=openpyxl.load_workbook(SOURCE/file,data_only=True,read_only=False)
   for stream in ['CAB','EuGBS'] if year==2024 else ['CAB']:
    sn='Project Information' if year==2023 else f'Project Information ({stream})';sh=w[sn]
    rr=self.d[(self.d.report_year==year)&(self.d.stream==stream)]
    for metric,col in [('relative','Q'),('absolute','P')]:
     n=Decimal(0);den=Decimal(0)
     for r in rr.itertuples():
      k=r.source_row;A=Decimal(str(sh[f'R{k}'].value));P=sh[f'P{k}'].value;Q=sh[f'Q{k}'].value;valid=isinstance(P,(int,float)) and isinstance(Q,(int,float))
      if valid:
       G=Decimal(str(sh[f'{col}{k}'].value));C=Decimal(str(sh[f'J{k}'].value));e=Decimal(str(sh[f'O{k}'].value))/100;n+=A*1000*G/(C*e)
      if year==2023 or valid:den+=A
     actual=self.a[(self.a.report_year==year)&(self.a.stream==stream)][metric+'_published'].iloc[0]
     self.assertTrue(math.isclose(float(n/den),actual,rel_tol=1e-10,abs_tol=1e-8))
 def test_07_coverage_identity(self):
  for m in ['relative','absolute']:np.testing.assert_allclose(self.a[m+'_all'],self.a[m+'_observed']*self.a.allocation_coverage,rtol=1e-10,atol=1e-8)
 def test_08_project_decompositions_sum(self):
  d=pd.read_csv(ROOT/'results/project_exact_decompositions.csv')
  fields=['ghg_revision','cost_update','eligibility_update','allocation_reweighting','numeric_addition','numeric_removal']
  np.testing.assert_allclose(d[fields].sum(axis=1),d.total,rtol=1e-9,atol=1e-8)
  totals=pd.read_csv(ROOT/'results/table2_exact_decomposition.csv')
  for r in totals.itertuples():
   a,b=map(int,r.period.split('_'));x=self.d.query('report_year==@a and stream=="CAB"');y=self.d.query('report_year==@b and stream=="CAB"')
   if r.matched_only:
    ids=set(x[x.numeric_ghg].project_id)&set(y[y.numeric_ghg].project_id);x=x[x.project_id.isin(ids)];y=y[y.project_id.isin(ids)]
   self.assertAlmostEqual(r.total,intensity(y,r.metric,cost=r.cost_basis)-intensity(x,r.metric,cost=r.cost_basis),places=7)
 def test_09_shapley_order_symmetry_and_zero(self):
  v0=np.array([-2000.,.02,1.]);v1=np.array([-2300.,.018,2.]);forward=permutation_shapley(v0,v1);back=permutation_shapley(v1,v0)
  np.testing.assert_allclose(forward,-back,atol=1e-10);self.assertAlmostEqual(sum(forward),np.prod(v1)-np.prod(v0),places=10)
  np.testing.assert_allclose(permutation_shapley(v0,v0),[0,0,0])
 def test_10_disclosure_transitions(self):
  p=pd.read_csv(ROOT/'results/project_membership_transitions.csv');x=p[p.period=='2023_2024']
  self.assertEqual((x.membership=='continuing').sum(),64);self.assertEqual((x.membership=='exit').sum(),94);self.assertEqual((x.membership=='entry').sum(),101)
  self.assertEqual(((x.status_before=='numeric')&(x.status_after!='numeric')&(x.membership=='continuing')).sum(),3)
 def test_11_rule_bridge(self):
  b=pd.read_csv(ROOT/'results/published_rule_shapley_bridge.csv');np.testing.assert_allclose(b[['conditional_intensity','allocation_coverage','inferred_denominator_rule']].sum(axis=1),b.published_change,atol=1e-8)
  self.assertEqual(b.loc[b.period=='2022_2023','inferred_denominator_rule'].iloc[0],0)
 def test_12_combined_boundary(self):
  b=pd.read_csv(ROOT/'data/combined_2024_project_boundary_sensitivity.csv',dtype={'project_id':str});self.assertEqual(len(b),178);self.assertFalse(b.project_id.duplicated().any())
  self.assertAlmostEqual(b.allocation_eur_m.sum(),self.d[self.d.report_year==2024].allocation_eur_m.sum(),places=6)
  n=b[b.project_id=='20160845'].iloc[0];self.assertAlmostEqual(n.allocation_eur_m,130);self.assertAlmostEqual(n.relative_ghg_kt_year,-14.2);self.assertAlmostEqual(n.project_cost_eur_m,1260)
 def test_13_zero_and_positive(self):
  z=self.d[(self.d.report_year==2024)&(self.d.stream=='CAB')];self.assertEqual((z.relative_ghg_kt_year==0).sum(),8);self.assertEqual((z.relative_ghg_kt_year>0).sum(),4)
 def test_14_no_single_deletion_reversal(self):
  z=pd.read_csv(ROOT/'results/leave_one_project_out.csv');self.assertTrue((z.signed_change>0).all())
 def test_15_exact_missing_scenario_tie(self):
  a=self.a[(self.a.report_year==2023)&(self.a.stream=='CAB')].iloc[0];b=self.a[(self.a.report_year==2024)&(self.a.stream=='CAB')].iloc[0]
  for r in pd.read_csv(ROOT/'results/missing_intensity_tipping_points.csv').itertuples():
   self.assertAlmostEqual(a.relative_all+(1-a.allocation_coverage)*r.assumed_missing_intensity_2023,b.relative_all+(1-b.allocation_coverage)*r.tie_required_missing_intensity_2024,places=6)
 def test_16_unresolved_2022_residual_retained(self):
  a=self.a[(self.a.report_year==2022)&(self.a.stream=='CAB')].iloc[0];self.assertAlmostEqual(a.absolute_published_minus_all,-0.0157438292302,places=8)

if __name__=='__main__':unittest.main(verbosity=2)
