#!/usr/bin/env python3
"""Download browser-isolated Bing candidate URLs with sidecars."""
import argparse,hashlib,io,json,time
from pathlib import Path
import httpx
from PIL import Image,ImageOps,UnidentifiedImageError
P=Path(__file__).resolve().parents[1];R=P/'data/raw/images';C=P/'data/reports/round3_browser_candidates.json';UA='Mozilla/5.0 Chrome/131 Safari/537.36'
def state(cls):
 hs={hashlib.sha256(x.read_bytes()).hexdigest() for x in (R/cls).glob('*.jpg')};urls=set()
 for b in (R/cls,R/'_rejected'/cls):
  if b.exists():
   for s in b.glob('*.json'):
    try:urls.add(json.loads(s.read_text(encoding='utf-8')).get('url',''))
    except Exception:pass
 return hs,urls
def main():
 a=argparse.ArgumentParser();a.add_argument('--target',type=int,default=65);z=a.parse_args();data=json.loads(C.read_text(encoding='utf-8'));summary=[]
 with httpx.Client(timeout=httpx.Timeout(45,connect=15)) as c:
  for cls,spec in data.items():
   d=R/cls;hs,urls=state(cls);before=len(list(d.glob('*.jpg')));saved=failed=dup=0
   for it in spec['rows']:
    if len(list(d.glob('*.jpg')))>=z.target:break
    url=it['url'];landing=it['foreign_landing_url']
    if url in urls:dup+=1;continue
    urls.add(url);time.sleep(1.03)
    try:
     q=c.get(url,headers={'User-Agent':UA,'Accept':'image/*','Referer':landing},follow_redirects=True);q.raise_for_status();raw=q.content
     if len(raw)<5120:raise ValueError()
     with Image.open(io.BytesIO(raw)) as src:src.load();im=ImageOps.exif_transpose(src).convert('RGB')
     if min(im.size)<200:raise ValueError()
     if max(im.size)>768:im.thumbnail((768,768),Image.Resampling.LANCZOS)
     o=io.BytesIO();im.save(o,'JPEG',quality=91,optimize=True);payload=o.getvalue()
     if len(payload)<5120:raise ValueError()
    except Exception:failed+=1;continue
    sha=hashlib.sha256(payload).hexdigest()
    if sha in hs:dup+=1;continue
    token=hashlib.sha256(url.encode()).hexdigest()[:8];img=d/f'web_{token}.jpg';side=d/f'web_{token}.json'
    if img.exists() or side.exists():dup+=1;continue
    md={'id':'bing:'+token,'title':it.get('title',''),'url':url,'foreign_landing_url':landing,'creator':'','license':'','license_url':'','provider':'bing','source':'bing_image_search_browser','width':im.width,'height':im.height,'sha256':sha,'our_class':cls,'query':spec['query'],'local_file':img.relative_to(P).as_posix(),'downloaded_from':url,'review_status':'pending'}
    img.write_bytes(payload);side.write_text(json.dumps(md,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');hs.add(sha);saved+=1;print(json.dumps({'class':cls,'count':len(list(d.glob('*.jpg'))),'file':img.name},ensure_ascii=False),flush=True)
   summary.append({'class':cls,'before':before,'saved':saved,'failed':failed,'duplicate':dup,'on_disk':len(list(d.glob('*.jpg')))})
 (P/'data/reports/round3_browser_download_stats.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
