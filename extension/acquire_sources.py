"""Acquire fixed public source vintages. Do not modify expected hashes on mismatch."""
from pathlib import Path
import urllib.request,json,hashlib
R=Path(__file__).resolve().parent
(R/'sources').mkdir(exist_ok=True)
for s in json.loads((R/'source_manifest.json').read_text()):
 p=R/'sources'/s['name']
 if p.exists() and hashlib.sha256(p.read_bytes()).hexdigest()==s['sha256']:
  print('Verified',s['name']);continue
 r=urllib.request.urlopen(urllib.request.Request(s['url'],headers={'User-Agent':'Academic replication source acquisition'}),timeout=60)
 b=r.read();h=hashlib.sha256(b).hexdigest()
 if h!=s['sha256']:raise RuntimeError(f'Source version mismatch for {s["name"]}: {h}. Investigate; do not overwrite expected hash.')
 p.write_bytes(b);print('Downloaded and verified',s['name'])
