"""Read-only, merge-aware OOXML extraction of EIB source workbooks."""
from pathlib import Path
import hashlib, json, re, zipfile, xml.etree.ElementTree as ET

NS = {'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
      'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
SOURCES = {
 2022: ('cab-impact-report-2022.xlsx','331a9dcff654d6d38712ae6acf2df3c5ceb7f79958ba4fa892d860cd21cd7f10','https://www.eib.org/attachments/fi/cab-impact-report-2022.xlsx'),
 2023: ('2023cabimpactreport.xlsx','d03755c356410388ffd468f81e9b0d500069b1b61ef747a4ca51089cfcb6189d','https://www.eib.org/attachments/fi/2023cabimpactreport.xlsx'),
 2024: ('2024CABimpactreport.xlsx','71e19eaf2efa7ce98ce50b0a975746e14a11e21e0378a5aa75edd33c4d28589a','https://www.eib.org/files/fi/2024CABimpactreport.xlsx')}
COLUMNS = {'C':'project_name','D':'country','E':'sector_raw','F':'activity','G':'taxonomy_eligible','H':'taxonomy_alignment','I':'environmental_contribution','J':'project_cost_eur_m','K':'financing_type','L':'approved_eib_share','M':'net_signed_loan_eur_m','N':'economic_life_years','O':'eligible_pct','P':'absolute_ghg_kt_year','Q':'relative_ghg_kt_year','R':'allocation_eur_m'}
NUMCOLS=set('JLMNOPQR')

def excel_col(s):
 v=0
 for a in s: v=26*v+ord(a)-64
 return v

def coordinates(ref):
 a,b=re.fullmatch(r'([A-Z]+)(\d+)',ref).groups()
 return int(b),excel_col(a)

def read_book(path):
 with zipfile.ZipFile(path) as z:
  strings=[]
  if 'xl/sharedStrings.xml' in z.namelist():
   strings=[''.join(t.text or '' for t in si.findall('.//m:t',NS)) for si in ET.fromstring(z.read('xl/sharedStrings.xml'))]
  rels={r.attrib['Id']:r.attrib['Target'] for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
  book={}
  for sheet in ET.fromstring(z.read('xl/workbook.xml')).findall('m:sheets/m:sheet',NS):
   target=rels[sheet.attrib['{'+NS['r']+'}id']]
   target=target.lstrip('/') if target.startswith('/') else 'xl/'+target
   root=ET.fromstring(z.read(target)); cells={}
   for c in root.findall('.//m:sheetData/m:row/m:c',NS):
    typ=c.attrib.get('t','n'); v=c.find('m:v',NS); literal=None if v is None else v.text
    if typ=='s': value=strings[int(literal)] if literal is not None else None
    elif typ=='inlineStr': value=''.join(t.text or '' for t in c.findall('.//m:t',NS))
    elif typ=='n': value=float(literal) if literal is not None else None
    else: value=literal
    cells[c.attrib['r']]={'value':value,'literal':literal,'type':typ,'formula':None if c.find('m:f',NS) is None else c.find('m:f',NS).text}
   merges=[m.attrib['ref'] for m in root.findall('m:mergeCells/m:mergeCell',NS)]
   mask={}
   for merge in merges:
    left,right=(merge.split(':')+[merge])[:2] if ':' not in merge else merge.split(':')
    r0,c0=coordinates(left);r1,c1=coordinates(right)
    for ref in cells:
     r,c=coordinates(ref)
     if r0<=r<=r1 and c0<=c<=c1 and ref!=left: mask[ref]=left
   book[sheet.attrib['name']]={'cells':cells,'merge_mask':mask,'merges':merges}
  return book

def status(v,year):
 if isinstance(v,(float,int)):return 'numeric'
 s=str(v or '').lower()
 if 'threshold' in s:return 'below_threshold'
 if 'intermediat' in s or 'framework' in s:return 'deferred_intermediated_framework'
 if 'not applicable' in s:return 'not_applicable'
 if 'clarification' in s:return 'withheld_external_review' if year==2024 else 'clarification_nondisclosure'
 return 'other_missing'

def extract(source_dir):
 rows=[];notes=[];hidden=[];summaries=[];manifest=[]
 for year,(filename,sha,url) in SOURCES.items():
  path=source_dir/filename;actual=hashlib.sha256(path.read_bytes()).hexdigest()
  assert actual==sha,(filename,actual,sha)
  manifest.append({'year':year,'filename':filename,'source_url':url,'sha256':actual,'bytes':path.stat().st_size})
  book=read_book(path)
  for sn,sh in book.items():
   for ref,c in sh['cells'].items():
    if isinstance(c['value'],str) and len(c['value'])>100:
     notes.append({'year':year,'sheet':sn,'cell':ref,'text':c['value']})
   if not sn.startswith('Project Information'):continue
   stream='EuGBS' if 'EuGBS' in sn else 'CAB'
   for ref,c in sh['cells'].items():
    if not re.fullmatch('B[0-9]+',ref):continue
    v=c['value'];pid=str(int(v)) if isinstance(v,(int,float)) and float(v).is_integer() else str(v)
    if not re.fullmatch(r'\d{8}',pid):continue
    r=int(ref[1:]); out={'report_year':year,'stream':stream,'project_id':pid,'source_file':filename,'source_sheet':sn,'source_row':r,'source_url':url,'cost_vintage':'initial_authorised' if year==2022 else 'current_authorised'}
    for col,name in COLUMNS.items():
     cref=f'{col}{r}';cell=sh['cells'].get(cref,{});raw=cell.get('value');value=None if cref in sh['merge_mask'] else raw
     if col in NUMCOLS:
      out[name]=value if isinstance(value,(int,float)) else None
      out[name+'_raw']=raw
     else:out[name]=value
     if cref in sh['merge_mask'] and col in 'PQ' and raw is not None:
      hidden.append({'report_year':year,'stream':stream,'project_id':pid,'sheet':sn,'cell':cref,'hidden_raw':raw,'anchor':sh['merge_mask'][cref],'displayed_status':sh['cells'][sh['merge_mask'][cref]]['value']})
    out['ghg_status']=status(out['absolute_ghg_kt_year_raw'],year)
    assert (out['absolute_ghg_kt_year'] is None)==(out['relative_ghg_kt_year'] is None),out
    out['numeric_ghg']=out['absolute_ghg_kt_year'] is not None
    rows.append(out)
   summ=book['Aggregate GHG summary ('+stream+')' if year==2024 else 'CAB - Summary']['cells']
   for metric,cell in [('absolute','C2'),('relative','C3')]:
    summaries.append({'report_year':year,'stream':stream,'metric':metric,'published':summ[cell]['value'],'formula':summ[cell]['formula'],'source_cell':cell})
 return rows,notes,hidden,summaries,manifest
