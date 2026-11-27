#!/usr/bin/env python3
"""DuckDuckGo Images fallback for bánh bao and bánh canh."""
from __future__ import annotations
import argparse, hashlib, io, json, re, time
from pathlib import Path
from urllib.parse import quote_plus
import httpx
from PIL import Image, ImageOps
P=Path(__file__).resolve().parents[1];ROOT=P/'data/raw/images';REPORTS=P/'data/reports';MIN=5120
Q={'banh_bao':['bánh bao nhân thịt','bánh bao Việt Nam','Vietnamese steamed pork bun'],'banh_canh':['bánh canh cua','bánh canh giò heo','tô bánh canh Việt Nam']};UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36';last=0.0
def pace():
 global last
 d=1.03-(time.monotonic()-last)
 if d>0:time.sleep(d)
 last=time.monotonic()
def search(c,q):
 r=c.get('https://duckduckgo.com/',params={'q':q},timeout=40);r.raise_for_status();
 m=re.search(r'vqd=["\']([^"\']+)',r.text) or re.search(r'vqd=([\d-]+)',r.text)
 if not m:return []
 token=m.group(1); headers={'Referer':str(r.url),'Accept':'application/json','X-Requested-With':'XMLHttpRequest'}
 x=c.get('https://duckduckgo.com/i.js',params={'l':'wt-wt','o':'json','q':q,'vqd':token,'f':',,,','p':'1'},headers=headers,timeout=40);x.raise_for_status();return x.json().get('results',[])
def collect(cls,target):
 folder=ROOT/cls;folder.mkdir(parents=True,exist_ok=True);before=len(list(folder.glob('*.jpg')));need=max(0,target-before);seen=set();hashes=set()
 for b in (folder,ROOT/'_rejected'/cls):
  if not b.exists():continue
  for s in b.glob('*.json'):
   try:seen.add(str(json.loads(s.read_text(encoding='utf-8')).get('url','')))
   except:pass
  for p in b.glob('*.jpg'):hashes.add(hashlib.sha256(p.read_bytes()).hexdigest())
 saved=failed=0
 with httpx.Client(headers={'User-Agent':UA}) as c:
  for q in Q[cls]:
   try:rows=search(c,q)
   except Exception as e:print('search fail',q,e);continue
   for x in rows:
    if saved>=need:break
    u=str(x.get('image') or '');page=str(x.get('url') or '')
    if not u or not page or u in seen:continue
    seen.add(u);pace()
    try:
     r=c.get(u,headers={'Referer':page,'Accept':'image/*'},follow_redirects=True,timeout=30);r.raise_for_status();raw=r.content
     if len(raw)<MIN:raise ValueError()
     with Image.open(io.BytesIO(raw)) as im:
      im.load();im=ImageOps.exif_transpose(im).convert('RGB')
      if min(im.size)<250 or max(im.size)<350:raise ValueError()
      if max(im.size)>768:im.thumbnail((768,768),Image.Resampling.LANCZOS)
      z=io.BytesIO();im.save(z,'JPEG',quality=92,optimize=True);data=z.getvalue();w,h=im.size
     if len(data)<MIN:raise ValueError()
     dig=hashlib.sha256(data).hexdigest()
     if dig in hashes:continue
     tok=hashlib.sha256(u.encode()).hexdigest()[:8];stem='web_'+tok
     if (folder/(stem+'.jpg')).exists():continue
     meta={'id':tok,'title':x.get('title') or '','url':u,'foreign_landing_url':page,'creator':'','license':'unknown','license_url':'','provider':'duckduckgo','source':'duckduckgo_image_search','width':w,'height':h,'sha256':dig,'our_class':cls,'query':q,'local_file':(folder/(stem+'.jpg')).relative_to(P).as_posix(),'downloaded_from':str(r.url),'review_status':'pending'}
     (folder/(stem+'.jpg')).write_bytes(data);(folder/(stem+'.json')).write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');hashes.add(dig);saved+=1;print(json.dumps({'class':cls,'saved':saved,'file':stem+'.jpg'},ensure_ascii=False),flush=True)
    except Exception:failed+=1
 return {'class':cls,'before':before,'saved':saved,'final':len(list(folder.glob('*.jpg'))),'failed':failed}
def main():
 a=argparse.ArgumentParser();a.add_argument('--classes',nargs='*',choices=sorted(Q),default=list(Q));a.add_argument('--target',type=int,default=60);x=a.parse_args();rows=[collect(c,x.target) for c in x.classes];(REPORTS/'round3_ddg_stats_bao_canh.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(rows,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
