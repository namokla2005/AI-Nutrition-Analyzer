#!/usr/bin/env python3
"""Make every round-3 image basename globally unique while preserving prefixes."""
import hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parents[1];R=P/'data/raw/images';CLASSES=['banh_uot','banh_tom','bo_kho','thit_kho_trung']
items=[]
for status in ('accepted','rejected'):
 for cls in CLASSES:
  base=R/cls if status=='accepted' else R/'_rejected'/cls
  items.extend((status,cls,x) for x in sorted(base.glob('*.jpg')))
used=set();renamed=[]
for status,cls,image in items:
 old=image.name
 if old not in used:used.add(old);continue
 side=image.with_suffix('.json');data=json.loads(side.read_text(encoding='utf-8'));prefix=image.stem.split('_',1)[0]
 if prefix=='commons':
  token=str(int(hashlib.sha256(f'{cls}:{status}:{old}:{data.get("id")}'.encode()).hexdigest()[:8],16))
 else:
  token=hashlib.sha256(f'{cls}:{status}:{old}:{data.get("id")}'.encode()).hexdigest()[:8]
 new=f'{prefix}_{token}.jpg';n=0
 while new in used:
  n+=1;token=hashlib.sha256(f'{cls}:{status}:{old}:{n}'.encode()).hexdigest()[:8];new=f'{prefix}_{token}.jpg'
 new_image=image.with_name(new);new_side=new_image.with_suffix('.json');image.rename(new_image);side.rename(new_side);data['local_file']=new_image.relative_to(P).as_posix();new_side.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');used.add(new);renamed.append({'class':cls,'status':status,'old':old,'new':new})
print(json.dumps({'renamed':len(renamed),'rows':renamed},ensure_ascii=False))
