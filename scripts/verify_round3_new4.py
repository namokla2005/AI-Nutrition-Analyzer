#!/usr/bin/env python3
from pathlib import Path
from PIL import Image
import hashlib,json
P=Path(__file__).resolve().parents[1];R=P/'data'/'raw'/'images';C=['banh_da_cua','goi_ga','banh_trang_nuong','mi_xao'];req={'id','title','url','foreign_landing_url','creator','license','license_url','provider','source','width','height','sha256','our_class','query','review_status'}
pro=json.loads((P/'data'/'reports'/'round3_provenance_new4.json').read_text(encoding='utf-8'));issues=[];counts={}
for cls in C:
 a=list((R/cls).glob('*.jpg'));x=list((R/'_rejected'/cls).glob('*.jpg'));counts[cls]={'accepted':len(a),'rejected':len(x),'downloaded':len(a)+len(x)}
 for status,paths in [('accepted',a),('rejected',x)]:
  for im in paths:
   if im.stat().st_size<5120:issues.append([str(im),'under_5kb'])
   try:
    with Image.open(im) as z:z.verify()
   except Exception as e:issues.append([str(im),'bad_image',str(e)])
   s=im.with_suffix('.json')
   if not s.exists():issues.append([str(im),'missing_sidecar']);continue
   d=json.loads(s.read_text(encoding='utf-8'))
   if not req.issubset(d):issues.append([str(s),'missing_keys',sorted(req-set(d))])
   if d.get('review_status')!=status or d.get('our_class')!=cls:issues.append([str(s),'status_or_class'])
   if d.get('sha256')!=hashlib.sha256(im.read_bytes()).hexdigest():issues.append([str(s),'hash'])
missing=sum(not (P/r['local_file']).exists() for r in pro);print(json.dumps({'disk_counts':counts,'provenance_records':len(pro),'missing_provenance_files':missing,'issues':issues,'ok':not issues and not missing},ensure_ascii=False,indent=2))
if issues or missing:raise SystemExit(1)
