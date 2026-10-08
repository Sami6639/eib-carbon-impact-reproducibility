from pathlib import Path
import json,re,hashlib
import pdfplumber
R=Path(__file__).resolve().parent
cells=json.loads((R/'data/cell_provenance.json').read_text());checks=[];fail=[]
for year in [2024,2025]:
 with pdfplumber.open(R/'sources'/f'IBRD_FY{year}.pdf') as d:
  for c in cells:
   if c['year']!=year or c['field'] in ['name','country']:continue
   bb=c['bbox'];pg=d.pages[c['page']-1]
   ss=pg.crop(bb).extract_text(x_tolerance=.4,y_tolerance=.6) or ''
   norm=lambda s:re.sub(r'\s','',s).replace('−','-')
   ok=(re.findall(r'\bP\d{6}\b',ss)==[c['text']]) if c['field']=='source_id' else norm(ss)==norm(c['text'])
   checks.append(dict(year=year,page=c['page'],row=c['row_number'],field=c['field'],passed=ok))
   if not ok:fail.append(dict(**c,second_reader=ss))
result=dict(checks=len(checks),passed=sum(x['passed'] for x in checks),failures=fail)
(R/'results/extraction_validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));assert not fail
