from pathlib import Path
import json,re,pandas as pd,fitz
R=Path(__file__).resolve().parent
items=[dict(project_id='P131256',document='P131256_IEG.pdf',page=8,source_value=900774,source_unit='tonnes CO2e/year',finding='FY25 annex value agrees with reported completion result; FY24 value equals IEG target 1270000. Closure 28 June 2024; this is a report-vintage update, not 2024-to-2025 physical change.'),dict(project_id='P160408',document='P160408_IEG.pdf',page=7,source_value=1382000,source_unit='tonnes/year, estimated reduction',finding='FY25 annex value agrees with estimated completion result. IEG end target 4789515 differs from FY24 annex 5661643.6; direct forecast-error interpretation is not identified.'),dict(project_id='P154283',document='P154283_IEG.pdf',page=6,source_value=7465,source_unit='thousand tonnes/year',finding='IEG target 8892 and completion 7465 are in thousand tonnes/year; annex values 8892 and 7465 appear under tonnes/year. Factor-1000 unit conflict. Do not silently restate; excluded from primary as status transition.'),dict(project_id='P132741',document='Not independently traced in this audit',page=None,source_value=None,source_unit=None,finding='Annex status transition retained descriptively; underlying 32000 completion estimate not independently traced.')]
for r in items:
 if r['page']:
  d=fitz.open(R/'sources'/r['document']);s=d[r['page']-1].get_text();assert f"{r['source_value']:,}" in s
pd.DataFrame(items).to_csv(R/'results/outcome_trace.csv',index=False)
# Additional exploratory sensitivity prompted by newly found unit conflict.
import analyze_ibrd as a
ids=a.valid[a.valid!='P154283'];r=a.result(a.A.loc[ids],a.B.loc[ids],'All valid matched excluding solar-park unit conflict')
pd.DataFrame([r]).to_csv(R/'results/unit_conflict_sensitivity.csv',index=False,float_format='%.12g')
print('Trace checks passed; unit-conflict exclusion',r)
