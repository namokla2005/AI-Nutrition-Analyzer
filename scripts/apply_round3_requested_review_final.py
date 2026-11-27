#!/usr/bin/env python3
"""Apply final contact-sheet review and mark all active sidecars accepted."""
import json,shutil
from pathlib import Path
P=Path(__file__).resolve().parents[1];R=P/'data/raw/images';S=P/'data/reports/round3_requested_contact_sheets'
REJECT={'banh_uot':{17,22,30,34,35,37,40},'banh_tom':{9,14,15,19,27,30,32,38,39,41,56,60,63},'bo_kho':{28,32,33,40,46,47},'thit_kho_trung':{26,43,47}}
moved=[]
for cls,nums in REJECT.items():
 idx=json.loads((S/f'{cls}_index.json').read_text(encoding='utf-8'))
 for x in idx:
  if x['number'] not in nums:continue
  src=R/cls/x['file'];dst=R/'_rejected'/cls;dst.mkdir(parents=True,exist_ok=True)
  if src.exists():shutil.move(str(src),dst/src.name)
  side=src.with_suffix('.json')
  if side.exists():
   d=json.loads(side.read_text(encoding='utf-8'));d['review_status']='rejected';d['review_reason']='final visual review: not a clear target dish';side.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');shutil.move(str(side),dst/side.name)
  moved.append({'class':cls,'file':x['file'],'number':x['number']})
for cls in REJECT:
 for side in (R/cls).glob('*.json'):
  d=json.loads(side.read_text(encoding='utf-8'));d['review_status']='accepted';d.pop('review_reason',None);side.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'moved':len(moved),'decisions':moved},ensure_ascii=False))
