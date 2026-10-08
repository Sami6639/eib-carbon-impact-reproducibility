"""Download exact inspected source vintages; reject any changed source."""
from pathlib import Path
import hashlib,json,urllib.request
R=Path(__file__).resolve().parent
(R/'sources').mkdir(exist_ok=True)
for m in json.loads((R/'source_manifest.json').read_text()):
 p=R/'sources'/m['file']
 if p.exists():b=p.read_bytes()
 else:b=urllib.request.urlopen(m['url'],timeout=90).read()
 if hashlib.sha256(b).hexdigest()!=m['sha256']:raise ValueError('Source edition changed: '+m['file'])
 if not p.exists():p.write_bytes(b)
 print('Verified',m['file'])
