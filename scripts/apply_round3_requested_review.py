#!/usr/bin/env python3
"""Apply first visual-review decisions to the four requested classes."""
import json,shutil
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[1];ROOT=PROJECT/'data/raw/images';SHEETS=PROJECT/'data/reports/round3_requested_contact_sheets'
KEEP_OV={'banh_uot':{3,7,8},'banh_tom':{18},'thit_kho_trung':{4,7,8,9}}
BO_REJECT={3,4,5,6,7,8,9,10,15,16,18,19,20,22,23,24,26,27,30,34,35,37,39,40,41,44}
rows=[]
for cls in ('banh_uot','banh_tom','thit_kho_trung'):
 index=json.loads((SHEETS/f'{cls}_index.json').read_text(encoding='utf-8'))
 for item in index:
  n=item['number'];name=item['file'];reject=name.startswith('web_') or (name.startswith('ov_') and n not in KEEP_OV[cls])
  if reject:rows.append({'class':cls,'file':name,'reason':'visual review: unrelated to target dish'})
index=json.loads((SHEETS/'bo_kho_index.json').read_text(encoding='utf-8'))
for item in index:
 if item['number'] in BO_REJECT:rows.append({'class':'bo_kho','file':item['file'],'reason':'visual review: not a clear bowl/plate of bo kho'})
for row in rows:
 src=ROOT/row['class']/row['file'];dst=ROOT/'_rejected'/row['class'];dst.mkdir(parents=True,exist_ok=True)
 if src.exists():shutil.move(str(src),dst/src.name)
 side=src.with_suffix('.json')
 if side.exists():
  data=json.loads(side.read_text(encoding='utf-8'));data['review_status']='rejected';data['review_reason']=row['reason'];side.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');shutil.move(str(side),dst/side.name)
print(json.dumps({'rejected':len(rows)},ensure_ascii=False))
