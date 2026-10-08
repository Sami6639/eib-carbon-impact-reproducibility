"""Acquire the frozen 60-document inventory; never accept a changed source silently."""
from pathlib import Path
from urllib.request import Request, urlopen
import hashlib,json
R=Path(__file__).resolve().parent
(R/'sources').mkdir(exist_ok=True)
for r in json.loads((R/'all_sources.json').read_text()):
 path=R/'sources'/r['file']
 if path.exists():data=path.read_bytes()
 else:
  with urlopen(Request(r['url'],headers={'User-Agent':'Mozilla/5.0'}),timeout=120) as response:data=response.read()
 if hashlib.sha256(data).hexdigest()!=r['sha256']:
  raise RuntimeError('Source identity changed: '+r['file']+'; investigate edition, do not replace the expected hash.')
 if not path.exists():path.write_bytes(data)
 print(r['file'],'verified')
print('All 60 source-file identities verified.')
