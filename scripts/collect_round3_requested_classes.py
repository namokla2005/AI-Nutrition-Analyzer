#!/usr/bin/env python3
"""Collect the four requested round-3 Vietnamese food classes."""
from __future__ import annotations
import argparse, hashlib, io, json, re, time
from pathlib import Path
from typing import Any
import httpx
from PIL import Image, ImageDraw, ImageOps, UnidentifiedImageError

PROJECT=Path(__file__).resolve().parents[1]; ROOT=PROJECT/'data/raw/images'; REPORTS=PROJECT/'data/reports'
UA='AI-Nutrition-Analyzer/round3 academic collection (github.com/namokla2005/AI-Nutrition-Analyzer)'
SPECS={
'banh_uot':['bánh ướt','banh uot','Vietnamese steamed rice rolls','Vietnamese wet rice cakes','bánh ướt Vietnam'],
'banh_tom':['bánh tôm','banh tom','Vietnamese shrimp fritter','Hanoi shrimp cakes','West Lake shrimp cake'],
'bo_kho':['bò kho','bo kho','Vietnamese beef stew','bò kho bánh mì','Vietnamese beef carrot stew'],
'thit_kho_trung':['thịt kho trứng','thit kho trung','Vietnamese braised pork eggs','Vietnamese caramelized pork eggs','thịt kho tàu'],}
MIN_BYTES=5120; last_download=0.0

def paced_download(client,urls,referer=''):
 global last_download
 for url in urls:
  if not url: continue
  delay=1.02-(time.monotonic()-last_download)
  if delay>0: time.sleep(delay)
  try:
   r=client.get(url,headers={'Accept':'image/*','Referer':referer},follow_redirects=True); last_download=time.monotonic(); r.raise_for_status()
   if len(r.content)>=MIN_BYTES and ('image' in r.headers.get('content-type','').lower() or r.content.startswith((b'\xff\xd8',b'\x89PNG',b'GIF8',b'RIFF'))): return r.content,str(r.url)
  except (httpx.HTTPError,OSError): last_download=time.monotonic()
 raise ValueError('download failed')

def jpeg(data):
 try:
  with Image.open(io.BytesIO(data)) as src: src.load(); im=ImageOps.exif_transpose(src).convert('RGB')
 except (UnidentifiedImageError,OSError,ValueError) as e: raise ValueError('not image') from e
 if min(im.size)<200: raise ValueError('too small')
 if max(im.size)>768: im.thumbnail((768,768),Image.Resampling.LANCZOS)
 out=io.BytesIO(); im.save(out,'JPEG',quality=91,optimize=True); b=out.getvalue()
 if len(b)<MIN_BYTES: raise ValueError('stored too small')
 return b,im.width,im.height

def state(cls):
 ids=set(); hashes=set()
 for base in (ROOT/cls,ROOT/'_rejected'/cls):
  if not base.exists(): continue
  for p in base.glob('*.json'):
   try: ids.add(str(json.loads(p.read_text(encoding='utf-8')).get('id','')))
   except (OSError,json.JSONDecodeError): pass
  for p in base.glob('*.jpg'): hashes.add(hashlib.sha256(p.read_bytes()).hexdigest())
 return ids,hashes

def ov_token(value):
 h=re.sub('[^0-9a-f]','',str(value).lower())
 return (h+hashlib.sha256(str(value).encode()).hexdigest())[:8]

def save(cls,stem,item,query,data,downloaded,hashes):
 payload,w,h=jpeg(data); digest=hashlib.sha256(payload).hexdigest()
 if digest in hashes: return False
 d=ROOT/cls; image=d/f'{stem}.jpg'; side=d/f'{stem}.json'
 if image.exists() or side.exists(): return False
 md={'id':str(item.get('id','')),'title':item.get('title') or '','url':item.get('url') or '',
 'foreign_landing_url':item.get('foreign_landing_url') or '','creator':item.get('creator') or '',
 'license':item.get('license') or '','license_url':item.get('license_url') or '',
 'provider':item.get('provider') or '','source':item.get('source') or '',
 'width':w,'height':h,'sha256':digest,'our_class':cls,'query':query,
 'local_file':image.relative_to(PROJECT).as_posix(),'downloaded_from':downloaded,'review_status':'pending'}
 image.write_bytes(payload); side.write_text(json.dumps(md,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); hashes.add(digest); return True

def collect_ov(client,cls,queries,target,ids,hashes):
 stats={'candidates':0,'saved':0,'failed':0,'duplicate':0}
 for q in queries:
  for page in range(1,8):
   if len(list((ROOT/cls).glob('*.jpg')))>=target:return stats
   try:
    time.sleep(1.02); r=client.get('https://api.openverse.org/v1/images/',params={'q':q,'page_size':20,'page':page,'license':'cc0,by,by-sa','license_type':'commercial,modification'}); r.raise_for_status(); result=r.json()
   except (httpx.HTTPError,ValueError): stats['failed']+=1; break
   rows=result.get('results') or []
   if not rows:break
   for item in rows:
    if len(list((ROOT/cls).glob('*.jpg')))>=target:return stats
    stats['candidates']+=1; iid=str(item.get('id') or '').lower()
    if not iid or iid in ids:stats['duplicate']+=1;continue
    ids.add(iid)
    if str(item.get('license') or '').lower() not in {'cc0','by','by-sa'}:continue
    try:
     data,url=paced_download(client,[str(item.get('url') or ''),str(item.get('thumbnail') or '')],str(item.get('foreign_landing_url') or ''))
     stem='ov_'+ov_token(iid)
     if save(cls,stem,item,q,data,url,hashes):stats['saved']+=1;print(json.dumps({'class':cls,'count':len(list((ROOT/cls).glob('*.jpg'))),'file':stem+'.jpg','query':q},ensure_ascii=False),flush=True)
     else:stats['duplicate']+=1
    except (ValueError,OSError):stats['failed']+=1
   if not result.get('next'):break
 return stats

def commons_license(meta):
 short=str((meta.get('LicenseShortName') or {}).get('value') or '').lower(); url=str((meta.get('LicenseUrl') or {}).get('value') or '')
 if 'public domain' in short or 'cc0' in short:return 'cc0',url
 if 'cc by-sa' in short:return 'by-sa',url
 if 'cc by' in short:return 'by',url
 return '',url

def collect_commons(client,cls,queries,target,ids,hashes):
 stats={'candidates':0,'saved':0,'failed':0,'duplicate':0}
 for q in queries:
  if len(list((ROOT/cls).glob('*.jpg')))>=target:break
  params={'action':'query','format':'json','formatversion':2,'generator':'search','gsrsearch':f'"{q}" filetype:bitmap','gsrnamespace':6,'gsrlimit':100,'prop':'imageinfo','iiprop':'url|size|mime|extmetadata'}
  try:
   time.sleep(1.02);r=client.get('https://commons.wikimedia.org/w/api.php',params=params);r.raise_for_status();pages=(r.json().get('query') or {}).get('pages') or []
  except (httpx.HTTPError,ValueError):stats['failed']+=1;continue
  if isinstance(pages,dict):pages=list(pages.values())
  for page in pages:
   if len(list((ROOT/cls).glob('*.jpg')))>=target:break
   stats['candidates']+=1; pid=str(page.get('pageid') or ''); iid='commons:'+pid
   if not pid or iid in ids:stats['duplicate']+=1;continue
   ids.add(iid);info=(page.get('imageinfo') or [{}])[0];meta=info.get('extmetadata') or {};lic,licurl=commons_license(meta)
   if not lic:continue
   url=str(info.get('url') or '');item={'id':pid,'title':page.get('title') or '','url':url,'foreign_landing_url':str(info.get('descriptionurl') or f'https://commons.wikimedia.org/?curid={pid}'),'creator':str((meta.get('Artist') or {}).get('value') or ''),'license':lic,'license_url':licurl,'provider':'wikimedia','source':'wikimedia_commons'}
   try:
    data,used=paced_download(client,[url],item['foreign_landing_url']);stem='commons_'+pid
    if save(cls,stem,item,q,data,used,hashes):stats['saved']+=1;print(json.dumps({'class':cls,'count':len(list((ROOT/cls).glob('*.jpg'))),'file':stem+'.jpg','query':q},ensure_ascii=False),flush=True)
    else:stats['duplicate']+=1
   except (ValueError,OSError):stats['failed']+=1
 return stats

def sheets(classes):
 out=REPORTS/'round3_requested_contact_sheets';out.mkdir(parents=True,exist_ok=True);made=[]
 for cls in classes:
  for old in out.glob(f'{cls}_*.jpg'):old.unlink()
  paths=sorted((ROOT/cls).glob('*.jpg'));index=[]
  for page,start in enumerate(range(0,len(paths),25),1):
   batch=paths[start:start+25];cw,ch,cols=220,180,5;canvas=Image.new('RGB',(cw*cols,ch*((len(batch)+4)//5)),'white');draw=ImageDraw.Draw(canvas)
   for i,p in enumerate(batch):
    with Image.open(p) as src:thumb=ImageOps.contain(src.convert('RGB'),(cw-10,ch-42))
    x,y=(i%cols)*cw,(i//cols)*ch;canvas.paste(thumb,(x+(cw-thumb.width)//2,y+3));n=start+i+1;draw.text((x+5,y+ch-36),f'#{n:03d} {p.name}',fill='black');index.append({'number':n,'file':p.name})
   dest=out/f'{cls}_{page:02d}.jpg';canvas.save(dest,'JPEG',quality=92);made.append(dest.relative_to(PROJECT).as_posix())
  (out/f'{cls}_index.json').write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 return made

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--classes',nargs='*',choices=sorted(SPECS),default=list(SPECS));ap.add_argument('--target',type=int,default=55);ap.add_argument('--sheets-only',action='store_true');a=ap.parse_args();REPORTS.mkdir(parents=True,exist_ok=True);summ=[]
 if not a.sheets_only:
  with httpx.Client(headers={'User-Agent':UA},timeout=httpx.Timeout(40,connect=15)) as client:
   for cls in a.classes:
    (ROOT/cls).mkdir(parents=True,exist_ok=True);ids,hashes=state(cls);before=len(list((ROOT/cls).glob('*.jpg')));ov=collect_ov(client,cls,SPECS[cls],a.target,ids,hashes);co=collect_commons(client,cls,SPECS[cls],a.target,ids,hashes);summ.append({'class':cls,'before':before,'openverse':ov,'commons':co,'on_disk':len(list((ROOT/cls).glob('*.jpg')))});print(json.dumps(summ[-1],ensure_ascii=False),flush=True)
  (REPORTS/'round3_requested_collection_stats.json').write_text(json.dumps(summ,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'contact_sheets':sheets(a.classes)},ensure_ascii=False,indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
