"""Acquire the exact official EIB workbook editions needed for replication.
This script deliberately fails if the served content differs from the audited SHA256.
It does not redistribute the original workbooks or accept a new source vintage silently.
Run: python code/acquire_sources.py --source-dir sources
"""
import argparse, hashlib, shutil, tempfile, urllib.request
from pathlib import Path
from extract import SOURCES

def main(destination):
 destination.mkdir(parents=True,exist_ok=True)
 for year,(filename,expected,url) in SOURCES.items():
  target=destination/filename
  if target.exists():
   actual=hashlib.sha256(target.read_bytes()).hexdigest()
   if actual==expected:
    print(f'{year}: already present and verified: {target}');continue
   raise SystemExit(f'Existing {target} has SHA256 {actual}, expected {expected}. Nothing was overwritten. Obtain the original audited edition or explicitly design a new vintage analysis.')
  try:
   request=urllib.request.Request(url,headers={'User-Agent':'EIB-reporting-comparability-replication/1.0'})
   with urllib.request.urlopen(request,timeout=90) as response, tempfile.NamedTemporaryFile(dir=destination,delete=False,suffix='.pending') as temp:
    pending=Path(temp.name);shutil.copyfileobj(response,temp)
  except Exception as exc:
   raise SystemExit(f'Could not acquire {year} from the official URL {url}: {exc}. Download the named workbook manually from EIB, place it in {destination}, and rerun. No alternate edition will be accepted.')
  actual=hashlib.sha256(pending.read_bytes()).hexdigest()
  if actual!=expected:
   pending.unlink(missing_ok=True)
   raise SystemExit(f'Source-vintage mismatch for {filename}: served SHA256 {actual}; expected {expected}. The download was discarded. This may be a changed edition or non-workbook response; inspect the official site and obtain the audited edition. Do not update the checksum merely to pass this test.')
  pending.replace(target);print(f'{year}: downloaded and SHA256 verified: {target}')

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--source-dir',type=Path,default=Path(__file__).resolve().parents[1]/'sources');main(parser.parse_args().source_dir)
