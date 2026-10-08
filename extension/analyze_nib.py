from pathlib import Path
import json,sys,math
import openpyxl,pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'code'))
from extract import read_book
R=Path(__file__).resolve().parent;p=R/'sources/nib2011_2025.xlsx';o=read_book(p);sn='2011-2024 (updated 2025)';c=o[sn]['cells'];wf=openpyxl.load_workbook(p,data_only=False);wv=openpyxl.load_workbook(p,data_only=True)
s=wv[sn];f=wf[sn];rows=[]
for col,label,unit in [('E','Added renewable energy capacity','MW'),('F','Increased renewable energy generation','MWh/year'),('H','GHG reduced or avoided','tCO2e/year')]:
 top=[8,9,10,11,17,18,19];sub=list(range(12,17));num=lambda r:s[f'{col}{r}'].value if isinstance(s[f'{col}{r}'].value,(int,float)) else 0.
 for r in range(8,21):
  cv=c.get(f'{col}{r}',{}).get('value');ov=s[f'{col}{r}'].value
  assert cv==ov,(col,r,cv,ov)
 parent=num(11);subs=sum(num(r) for r in sub);disjoint=sum(num(r) for r in top);display=num(20);allrows=sum(num(r) for r in range(8,20))
 assert abs(parent-subs)<1e-8
 rows.append(dict(metric=label,unit=unit,parent=parent,children_sum=subs,nonoverlapping_category_sum=disjoint,published_total=display,all_displayed_rows_sum=allrows,excess_vs_nonoverlapping=display-disjoint,excess_pct=100*(display/disjoint-1),source_formula=f[f'{col}20'].value,source_cell=f'{col}20'))
a=pd.DataFrame(rows);a.to_csv(R/'results/nib_hierarchy_audit.csv',index=False);print(a.to_string(index=False))
# No chronological inference: table is a 2025 snapshot of outstanding loans under the old framework.
# Independent cross-sheet project-level check is limited to metadata and denominator coverage, not a reconstruction with disputed units.
notes={'snapshot_date':'2025-12-31','allocation_cutoff':'2024-08-31','new_allocations_2025':False,'evidence':'B2 and A5; matured/repaid loans removed; all new disbursements since September 2024 go to new pool','ghg_shared_formula':'=SUM(H8:H19)','interpretation':'Published total includes parent Renewable energy generation and five exhaustive subcategories. Alternative subtotal sums seven top-level categories once. This is a source arithmetic diagnostic, not a validated estimate of realised emissions or an issuer-confirmed correction.','rounding_note_conflict':'B2 says standard rounding since 2023; B29 says rounded down. Both are retained, not resolved by assumption.'}
(R/'results/nib_scope_notes.json').write_text(json.dumps(notes,indent=2))
