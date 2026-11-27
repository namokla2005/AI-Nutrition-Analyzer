#!/usr/bin/env python3
"""Apply second review: remove noisy Bing results, keeping clear bo kho."""
import json,shutil
from pathlib import Path
P=Path(__file__).resolve().parents[1];R=P/'data/raw/images';S=P/'data/reports/round3_requested_contact_sheets'
KEEP_BO={19,20,25,28,30,39,41,46};rows=[]
for cls in ('banh_uot','banh_tom','thit_kho_trung'):
 for x in json.loads((S/f'{cls}_index.json').read_text(encoding='utf-8')):
  if x['file'].startswith('web_'):rows.append((cls,x['file']))
for x in json.loads((S/'bo_kho_index.json').read_text(encoding='utf-8')):
 if x['file'].startswith('web_') and x['number'] not in KEEP_BO:rows.append(('bo_kho',x['file']))
for cls,name in rows:
 src=R/cls/name;dst=R/'_rejected'/cls;dst.mkdir(parents=True,exist_ok=True)
 if src.exists():shutil.move(str(src),dst/src.name)
 side=src.with_suffix('.json')
 if side.exists():
  d=json.loads(side.read_text(encoding='utf-8'));d['review_status']='rejected';d['review_reason']='visual review: unrelated/noisy web-search result';side.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');shutil.move(str(side),dst/side.name)
print(json.dumps({'rejected':len(rows)}))
