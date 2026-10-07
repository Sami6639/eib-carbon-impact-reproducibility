"""Verify distributed artifacts and optionally acquired sources/regenerated outputs."""
from pathlib import Path
import argparse, hashlib, json
from extract import SOURCES
ROOT=Path(__file__).resolve().parents[1]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main(source_check=False,output_check=False):
 problems=[];checked=0
 manifest=ROOT/'CHECKSUMS.sha256'
 if not manifest.exists():raise SystemExit('CHECKSUMS.sha256 is absent. Use the original portable bundle or its verified checksum manifest.')
 for line in manifest.read_text().splitlines():
  expected,relative=line.split('  ',1);path=ROOT/relative
  if not path.is_file():problems.append(f'Missing distributed artifact: {relative}')
  elif digest(path)!=expected:problems.append(f'Distributed-artifact checksum mismatch: {relative}')
  checked+=1
 if source_check:
  for file,expected,_ in SOURCES.values():
   path=ROOT/'sources'/file
   if not path.is_file():problems.append(f'Missing audited original: sources/{file}')
   elif digest(path)!=expected:problems.append(f'Source-vintage checksum mismatch: sources/{file}')
   checked+=1
 if output_check:
  for relative,expected in json.loads((ROOT/'expected_output_checksums.json').read_text()).items():
   path=ROOT/relative
   if not path.is_file():problems.append(f'Missing regenerated output: {relative}')
   elif digest(path)!=expected:problems.append(f'Regenerated-output mismatch: {relative}')
   checked+=1
 if problems:raise SystemExit('\n'.join(problems)+'\nInvestigate discrepancies; do not silently replace source or output hash baselines.')
 print(f'PASS: {checked} checksums matched. Source originals and local project-level outputs remain outside redistribution scope.')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--sources',action='store_true');p.add_argument('--outputs',action='store_true');a=p.parse_args();main(a.sources,a.outputs)
