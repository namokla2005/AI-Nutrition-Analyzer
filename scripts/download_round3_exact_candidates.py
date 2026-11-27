#!/usr/bin/env python3
"""Download browser-extracted exact Bing image candidates."""
import hashlib,io,json,time
from pathlib import Path
import httpx
from PIL import Image,ImageOps
P=Path(__file__).resolve().parents[1];R=P/'data/raw/images';src=P/'data/reports/round3_exact_candidates_bao_canh.json';MIN=5120;last=0.0
rows=json.loads(src.read_text(encoding='utf-8'))
with httpx.Client(headers={'User-Agent':'Mozilla/5.0 Chrome/130 Safari/537.36','Accept':'image/*'}) as c:
 for cls,items in rows.items():
  folder=R/cls;folder.mkdir(parents=True,exist_ok=True);seen=set();hashes=set()
  for b in (folder,R/'_rejected'/cls):
   if not b.exists():continue
   for s in b.glob('*.json'):
    try:seen.add(str(json.loads(s.read_text(encoding='utf-8')).get('url','')))
    except:pass
   for f in b.glob('*.jpg'):hashes.add(hashlib.sha256(f.read_bytes()).hexdigest())
  saved=0
  for x in items:
   u=x['url'];page=x['foreign_landing_url']
   if u in seen:continue
   seen.add(u);d=1.03-(time.monotonic()-last)
   if d>0:time.sleep(d)
   last=time.monotonic()
   try:
    z=c.get(u,headers={'Referer':page},follow_redirects=True,timeout=30);z.raise_for_status();raw=z.content
    if len(raw)<MIN:raise ValueError()
    with Image.open(io.BytesIO(raw)) as im:
     im.load();im=ImageOps.exif_transpose(im).convert('RGB')
     if min(im.size)<250 or max(im.size)<350:raise ValueError()
     if max(im.size)>768:im.thumbnail((768,768),Image.Resampling.LANCZOS)
     out=io.BytesIO();im.save(out,'JPEG',quality=92,optimize=True);data=out.getvalue();w,h=im.size
    if len(data)<MIN:raise ValueError()
    dig=hashlib.sha256(data).hexdigest()
    if dig in hashes:continue
    tok=hashlib.sha256(u.encode()).hexdigest()[:8];stem='web_'+tok
    if (folder/(stem+'.jpg')).exists():continue
    meta={'id':tok,'title':x.get('title',''),'url':u,'foreign_landing_url':page,'creator':'','license':'unknown','license_url':'','provider':'bing','source':'bing_image_search_browser','width':w,'height':h,'sha256':dig,'our_class':cls,'query':'exact phrase browser search','local_file':(folder/(stem+'.jpg')).relative_to(P).as_posix(),'downloaded_from':str(z.url),'review_status':'pending'}
    (folder/(stem+'.jpg')).write_bytes(data);(folder/(stem+'.json')).write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');hashes.add(dig);saved+=1;print(json.dumps({'class':cls,'saved':saved,'file':stem+'.jpg'}),flush=True)
   except Exception:pass
 print(json.dumps({'class':cls,'new':saved,'active':len(list(folder.glob('*.jpg')))}))
