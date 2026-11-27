#!/usr/bin/env python3
"""Verify requested round-3 collection and write its provenance report."""
from __future__ import annotations
import hashlib,json,re
from collections import Counter,defaultdict
from pathlib import Path
from PIL import Image
P=Path(__file__).resolve().parents[1];R=P/'data/raw/images';REPORT=P/'data/reports/round3_provenance_nhom_4_mon_moi.json';CLASSES=['banh_uot','banh_tom','bo_kho','thit_kho_trung']
REQ=['id','title','url','foreign_landing_url','creator','license','license_url','provider','source','width','height','sha256','our_class','query']
rows=[];summary=[];errors=[];license_counts=Counter();global_names=defaultdict(list)
for cls in CLASSES:
 accepted=list((R/cls).glob('*.jpg'));rejected=list((R/'_rejected'/cls).glob('*.jpg'));active_hashes=defaultdict(list)
 for status,paths in [('accepted',accepted),('rejected',rejected)]:
  for image in paths:
   global_names[image.name].append(f'{cls}:{status}')
   side=image.with_suffix('.json')
   if not side.exists():errors.append(f'missing sidecar: {image}');continue
   try:data=json.loads(side.read_text(encoding='utf-8'))
   except Exception as exc:errors.append(f'bad sidecar {side}: {exc}');continue
   for key in REQ:
    if key not in data:errors.append(f'{side}: missing key {key}')
   if not data.get('url') or not data.get('foreign_landing_url'):errors.append(f'{side}: missing source URL')
   if data.get('our_class')!=cls:errors.append(f'{side}: class mismatch')
   if not re.fullmatch(r'(ov_[0-9a-f]{8}|commons_\d+|web_[0-9a-f]{8})\.jpg',image.name):errors.append(f'bad filename: {image.name}')
   if image.stat().st_size<5120:errors.append(f'too small: {image}')
   digest=hashlib.sha256(image.read_bytes()).hexdigest()
   if digest!=data.get('sha256'):errors.append(f'hash mismatch: {image}')
   try:
    with Image.open(image) as im:im.verify();w,h=im.size
   except Exception as exc:errors.append(f'bad image {image}: {exc}');continue
   if min(w,h)<200:errors.append(f'bad dimensions: {image} {w}x{h}')
   if status=='accepted':active_hashes[digest].append(image.name)
   data['local_file']=image.relative_to(P).as_posix();data['review_status']=status;data['width']=w;data['height']=h
   side.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
   rows.append(data);license_counts[data.get('license') or 'unknown']+=1
 for digest,names in active_hashes.items():
  if len(names)>1:errors.append(f'duplicate active hash {cls}: {names}')
 summary.append({'class':cls,'downloaded_new':len(accepted)+len(rejected),'rejected':len(rejected),'accepted':len(accepted),'clean_total':len(accepted),'shortfall_to_34':max(0,34-len(accepted))})
for name,locations in global_names.items():
 if len(locations)>1:errors.append(f'duplicate filename {name}: {locations}')
REPORT.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
result={'classes':summary,'provenance_path':str(REPORT),'provenance_records':len(rows),'license_counts':dict(sorted(license_counts.items())),'duplicate_names_across_classes':{k:v for k,v in global_names.items() if len(v)>1},'errors':errors}
(P/'data/reports/round3_requested_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
assert not errors,errors
assert len(rows)==sum(x['downloaded_new'] for x in summary)
assert all(x['downloaded_new']>=40 and x['accepted']>=34 for x in summary)
print(json.dumps(result,ensure_ascii=False,indent=2))
