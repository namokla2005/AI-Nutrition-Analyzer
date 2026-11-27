#!/usr/bin/env python3
"""Collect/review four new food classes via Openverse."""
from __future__ import annotations
import argparse, hashlib, io, json, shutil, time
from collections import Counter
from pathlib import Path
from typing import Any
import httpx
from PIL import Image, ImageDraw, ImageOps, UnidentifiedImageError

PROJECT=Path(__file__).resolve().parents[1]; ROOT=PROJECT/'data/raw/images'; REPORTS=PROJECT/'data/reports'
SHEETS=REPORTS/'round3_contact_sheets_bao_chao_canh_mam'; PROV=REPORTS/'round3_provenance_bao_chao_canh_mam.json'
SPECS={
 'banh_bao':['bánh bao','banh bao','Vietnamese steamed bun','Vietnamese pork steamed bun','bánh bao nhân thịt'],
 'chao':['cháo Việt Nam','Vietnamese congee','Vietnamese rice porridge','cháo gà','cháo lòng'],
 'banh_canh':['bánh canh','banh canh','Vietnamese thick noodle soup','bánh canh cua','bánh canh giò heo'],
 'bun_mam':['bún mắm','bun mam','Vietnamese fermented fish noodle soup','Mekong delta bun mam','bún mắm miền Tây']}
UA='AI-Nutrition-Analyzer round3 academic dataset (github.com/namokla2005/AI-Nutrition-Analyzer)'; MIN=5120; last=0.0

def paced_get(c,url,**kw):
 global last
 for attempt in range(5):
  d=1.02-(time.monotonic()-last)
  if d>0: time.sleep(d)
  try:
   r=c.get(url,follow_redirects=True,timeout=60,**kw); last=time.monotonic(); r.raise_for_status(); return r
  except httpx.HTTPStatusError as exc:
   last=time.monotonic()
   if 400 <= exc.response.status_code < 500 and exc.response.status_code != 429: raise
   if attempt==4: raise
   time.sleep(2**(attempt+1))
  except httpx.HTTPError:
   last=time.monotonic()
   if attempt==4: raise
   time.sleep(2**(attempt+1))

def state(cls):
 ids=set(); hashes=set()
 for b in (ROOT/cls,ROOT/'_rejected'/cls):
  if not b.exists(): continue
  for p in b.glob('*.json'):
   try: ids.add(str(json.loads(p.read_text(encoding='utf-8')).get('id','')))
   except Exception: pass
  for p in b.glob('*.jpg'): hashes.add(hashlib.sha256(p.read_bytes()).hexdigest())
 return ids,hashes

def collect(cls,target):
 folder=ROOT/cls; folder.mkdir(parents=True,exist_ok=True); ids,hashes=state(cls); saved=failed=0
 with httpx.Client(headers={'User-Agent':UA}) as c:
  for q in SPECS[cls]:
   for page in range(1,8):
    if saved>=target:return {'class':cls,'saved':saved,'failed':failed}
    try: rows=paced_get(c,'https://api.openverse.org/v1/images/',params={'q':q,'page_size':20,'page':page,'license':'cc0,by,by-sa','license_type':'commercial,modification'}).json().get('results',[])
    except Exception: failed+=1; break
    if not rows: break
    for x in rows:
     if saved>=target: break
     iid=str(x.get('id') or '').lower(); lic=str(x.get('license') or '').lower()
     if not iid or iid in ids or lic not in {'cc0','by','by-sa'} or not x.get('url') or not x.get('foreign_landing_url'): continue
     ids.add(iid); raw=None; used=''
     for u in (x.get('thumbnail'),x.get('url')):
      if not u: continue
      try:
       z=paced_get(c,str(u),headers={'Accept':'image/*','Referer':str(x.get('foreign_landing_url') or '')})
       if len(z.content)>=MIN: raw=z.content; used=str(z.url); break
      except Exception: pass
     if raw is None: failed+=1; continue
     try:
      with Image.open(io.BytesIO(raw)) as im:
       im.load(); im=ImageOps.exif_transpose(im).convert('RGB')
       if min(im.size)<250 or max(im.size)<350: raise ValueError('small')
       if max(im.size)>768: im.thumbnail((768,768),Image.Resampling.LANCZOS)
       out=io.BytesIO(); im.save(out,'JPEG',quality=92,optimize=True); payload=out.getvalue(); sw,sh=im.size
      if len(payload)<MIN: raise ValueError('small file')
      digest=hashlib.sha256(payload).hexdigest()
      if digest in hashes: continue
      stem=f'ov_{iid[:8]}'
      if (folder/f'{stem}.jpg').exists(): continue
      meta={'id':iid,'title':x.get('title'),'url':x.get('url'),'foreign_landing_url':x.get('foreign_landing_url'),'creator':x.get('creator'),'license':x.get('license'),'license_url':x.get('license_url'),'provider':x.get('provider'),'source':x.get('source'),'width':x.get('width') or sw,'height':x.get('height') or sh,'sha256':digest,'our_class':cls,'query':q,'local_file':(folder/f'{stem}.jpg').relative_to(PROJECT).as_posix(),'downloaded_from':used,'review_status':'pending'}
      (folder/f'{stem}.jpg').write_bytes(payload); (folder/f'{stem}.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); hashes.add(digest); saved+=1
      print(json.dumps({'class':cls,'saved':saved,'file':stem+'.jpg','query':q},ensure_ascii=False),flush=True)
     except (OSError,ValueError,UnidentifiedImageError): failed+=1
 return {'class':cls,'saved':saved,'failed':failed}

def sheets():
 SHEETS.mkdir(parents=True,exist_ok=True); manifest=[]
 for cls in SPECS:
  for old in SHEETS.glob(f'{cls}_*.jpg'): old.unlink()
  paths=sorted((ROOT/cls).glob('*.jpg'))
  for pg,start in enumerate(range(0,len(paths),25),1):
   batch=paths[start:start+25]; cw,ch,cols=240,190,5; canvas=Image.new('RGB',(cw*cols,ch*((len(batch)+4)//5)),'white'); draw=ImageDraw.Draw(canvas)
   for i,p in enumerate(batch,1):
    with Image.open(p) as im: thumb=ImageOps.contain(im.convert('RGB'),(cw-10,ch-42))
    x,y=((i-1)%5)*cw,((i-1)//5)*ch; canvas.paste(thumb,(x+(cw-thumb.width)//2,y+3)); draw.rectangle((x+1,y+1,x+cw-2,y+ch-2),outline='#555',width=2); draw.text((x+5,y+ch-35),f'{i:02d} {p.name}',fill='black'); manifest.append({'class':cls,'sheet':f'{cls}_{pg:02d}.jpg','number':i,'file':p.name})
   canvas.save(SHEETS/f'{cls}_{pg:02d}.jpg','JPEG',quality=92)
 (SHEETS/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 return manifest

def apply(path):
 moved=0
 for r in json.loads(path.read_text(encoding='utf-8')):
  if r.get('review_status')!='rejected': continue
  src=ROOT/r['class']/r['file']; dst=ROOT/'_rejected'/r['class']; dst.mkdir(parents=True,exist_ok=True)
  if src.exists():
   shutil.move(str(src),dst/src.name); side=src.with_suffix('.json')
   if side.exists(): shutil.move(str(side),dst/side.name)
   moved+=1
 return moved

def provenance():
 rows=[]
 for cls in SPECS:
  for status,b in [('accepted',ROOT/cls),('rejected',ROOT/'_rejected'/cls)]:
   if not b.exists(): continue
   for s in sorted(b.glob('*.json')):
    p=s.with_suffix('.jpg')
    if not p.exists(): continue
    r=json.loads(s.read_text(encoding='utf-8')); r['review_status']=status; r['local_file']=p.relative_to(PROJECT).as_posix(); rows.append(r)
 REPORTS.mkdir(parents=True,exist_ok=True); PROV.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); return rows

def verify():
 rows=provenance(); req={'id','title','url','foreign_landing_url','creator','license','license_url','provider','source','width','height','sha256','our_class','query','review_status'}; errors=[]; seen={}; classes={}
 for cls in SPECS:
  a=list((ROOT/cls).glob('*.jpg')); r=list((ROOT/'_rejected'/cls).glob('*.jpg')); classes[cls]={'downloaded_new':len(a)+len(r),'rejected':len(r),'accepted':len(a),'clean_total':len(a)}
 for r in rows:
  p=PROJECT/r['local_file']
  if req-r.keys(): errors.append(f"{p}: missing {sorted(req-r.keys())}"); continue
  if not p.exists() or p.stat().st_size<MIN: errors.append(f'{p}: missing/small'); continue
  d=hashlib.sha256(p.read_bytes()).hexdigest()
  if d!=r['sha256']: errors.append(f'{p}: hash mismatch')
  if r['review_status']=='accepted':
   if d in seen: errors.append(f'{p}: duplicate accepted image of {seen[d]}')
   seen[d]=str(p)
  try:
   with Image.open(p) as im: im.verify()
  except Exception as e: errors.append(f'{p}: invalid {e}')
 summary={'classes':classes,'provenance':PROV.relative_to(PROJECT).as_posix(),'provenance_records':len(rows),'licenses':dict(Counter(str(r.get('license') or 'unknown') for r in rows)),'errors':errors}; (REPORTS/'round3_verification_bao_chao_canh_mam.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(json.dumps(summary,ensure_ascii=False,indent=2)); return not errors

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--target',type=int,default=55); ap.add_argument('--classes',nargs='*',choices=sorted(SPECS),default=list(SPECS)); ap.add_argument('--sheets-only',action='store_true'); ap.add_argument('--apply-review',type=Path); ap.add_argument('--verify',action='store_true'); a=ap.parse_args()
 if a.apply_review: print(json.dumps({'moved':apply(a.apply_review)})); sheets(); provenance(); return 0
 if a.verify:return 0 if verify() else 1
 stats=[]
 if not a.sheets_only:
  for cls in a.classes:
   existing=len(list((ROOT/cls).glob('*.jpg'))); stats.append(collect(cls,max(0,a.target-existing)))
  (REPORTS/'round3_collection_stats_bao_chao_canh_mam.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'sheet_entries':len(sheets()),'provenance_records':len(provenance())})); return 0
if __name__=='__main__': raise SystemExit(main())
