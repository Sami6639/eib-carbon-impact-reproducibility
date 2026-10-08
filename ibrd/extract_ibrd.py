from pathlib import Path
import re,json,hashlib
import fitz,pandas as pd
R=Path(__file__).resolve().parent
URLS={2024:'https://thedocs.worldbank.org/en/doc/93cedba65079dfee19fed7da7703b6e0-0340022025/original/FY24-Green-Bond-Annex-Table-External-View.pdf',2025:'https://thedocs.worldbank.org/en/doc/ee7c9a7a4fba5bd686a52257a086c75e-0340022026/original/FY25-IBRD-Green-Bond-Annex-Complete.pdf'}
def clean(x):return ' '.join((x or '').split())
def number(x):
 s=clean(x).replace(',','').replace('%','')
 return float(s) if re.fullmatch(r'-?\d+(\.\d+)?',s) else None

def main():
 records=[];cells=[];totals=[];manifest=[];removed_ids={}
 for year,url in URLS.items():
  f=R/'sources'/f'IBRD_FY{year}.pdf';doc=fitz.open(f);manifest.append(dict(year=year,file=f.name,url=url,sha256=hashlib.sha256(f.read_bytes()).hexdigest(),bytes=f.stat().st_size,retrieved='2026-10-07'))
  full_text='\n'.join(x.get_text() for x in doc)
  m=re.search(r'The projects -(.+?)were fully',full_text,re.S)
  removed_ids[year]=set(re.findall(r'P\d{6}',m.group(1))) if m else set()
  for pi,page in enumerate(doc):
   if 'Green Bond Portfolio -' not in page.get_text():continue
   status='active' if 'Portfolio - Active' in page.get_text() else 'closed'
   ts=page.find_tables()
   for t in ts.tables:
    rows=t.extract();headers=next((rr for rr in rows if rr[0]=='#'),None)
    if headers is None:continue
    h=[clean(c) for c in headers]
    rules={'source_id':lambda s:s in ['Project Link','Project ID'],'name':lambda s:s.startswith('Project Name'),'country':lambda s:s=='Country','category':lambda s:s.startswith('Project Category'),'life':lambda s:s.startswith('Project Life'),'share':lambda s:s.startswith('IBRD Share'),'eligible':lambda s:s.startswith('GB Eligible'),'commitment':lambda s:s.startswith('Committed'),'allocation':lambda s:s.startswith('Allocated'),'ghg':lambda s:s.startswith('Annual GHG'),'other':lambda s:s=='Other Results'}
    ix={k:next(j for j,s in enumerate(h) if fn(s)) for k,fn in rules.items()}
    for ri,row in enumerate(rows):
     if clean(row[0])=='TOTAL':totals.append(dict(year=year,status=status,page=pi+1,**{k:clean(row[ix[k]]) for k in ['commitment','allocation','ghg']}));continue
     if not re.fullmatch(r'\d+',clean(row[0])):continue
     rec=dict(year=year,status=status,page=pi+1,row_number=int(row[0]),**{k:clean(row[j]) for k,j in ix.items()})
     ids=re.findall(r'\bP\d{6}\b',rec['name']);rec['description_ids']=';'.join(sorted(set(ids)));rec['id_conflict']=bool(ids and rec['source_id'] not in ids)
     rec['project_id']=rec['source_id'];rec['removed']=bool(rec['source_id'] in removed_ids[year] or re.search('fully repaid|removed from the current',rec['name'],re.I))
     for k in ['life','share','eligible','commitment','allocation','ghg']:
      rec[k+'_raw']=rec[k];rec[k]=number(rec[k])
     for k in ['commitment','allocation']:
      rec[k+'_usd_m']=rec[k] if year==2024 or rec[k] is None else rec[k]/1e6
     records.append(rec)
     for k in ['source_id','name','country','share','eligible','commitment','allocation','ghg']:
      bb=t.rows[ri].cells[ix[k]]
      cells.append(dict(year=year,page=pi+1,row_number=rec['row_number'],field=k,bbox=bb,text=clean(row[ix[k]])))
 (R/'data').mkdir(exist_ok=True);pd.DataFrame(records).to_csv(R/'data/project_records.csv',index=False);pd.DataFrame(totals).to_csv(R/'data/source_totals.csv',index=False)
 (R/'data/cell_provenance.json').write_text(json.dumps(cells,indent=2))
 prior=json.loads((R/'source_manifest.json').read_text()) if (R/'source_manifest.json').exists() else []
 manifest += [m for m in prior if m['file'] not in [x['file'] for x in manifest]]
 (R/'source_manifest.json').write_text(json.dumps(manifest,indent=2))
 d=pd.DataFrame(records);print(d.groupby(['year','status']).size());print('CONFLICTS',d[d.id_conflict][['year','row_number','source_id','description_ids']].to_string(index=False));print('DUPLICATES',d[d.duplicated(['year','project_id'],False)][['year','row_number','source_id']].to_string(index=False));print('TOTALS',totals)
if __name__=='__main__':main()
