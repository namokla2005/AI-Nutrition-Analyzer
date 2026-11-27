#!/usr/bin/env python3
"""Bing Images fallback for banh_uot, banh_tom, thit_kho_trung."""
from __future__ import annotations
import argparse,hashlib,html,io,json,re,time
from pathlib import Path
import httpx
from PIL import Image,ImageOps,UnidentifiedImageError
PROJECT=Path(__file__).resolve().parents[1];ROOT=PROJECT/'data/raw/images';MIN_BYTES=5120
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131 Safari/537.36'
QUERIES={'banh_uot':['bánh ướt món ăn','bánh ướt thịt nướng','bánh ướt chả lụa','đĩa bánh ướt','Vietnamese banh uot dish'],'banh_tom':['bánh tôm Hồ Tây món ăn','bánh tôm Hà Nội','đĩa bánh tôm','Vietnamese shrimp fritters banh tom','Hanoi West Lake shrimp cakes'],'bo_kho':['bò kho món ăn Việt Nam','bò kho bánh mì','tô bò kho','Vietnamese beef stew bo kho','bo kho noodle soup'],'thit_kho_trung':['thịt kho trứng món ăn','thịt kho tàu trứng vịt','thịt kho hột vịt','Vietnamese braised pork eggs','Vietnamese caramelized pork with eggs']}
def search(client,q,first):
 r=client.get('https://www.bing.com/images/search',params={'q':q,'form':'HDRSC2','first':first,'count':35,'qft':'+filterui:photo-photo'},headers={'User-Agent':UA});r.raise_for_status();rows=[]
 # Only image-result anchors carry the m JSON; generic m= attributes are noise.
 for raw in re.findall(r'<a[^>]+class="iusc"[^>]+m="([^"]+)"',r.text):
  try:
   o=json.loads(html.unescape(raw))
   if o.get('murl') and o.get('purl'):rows.append(o)
  except (json.JSONDecodeError,TypeError):pass
 return rows
def download(client,url,referer):
 r=client.get(url,headers={'User-Agent':UA,'Accept':'image/*','Referer':referer},follow_redirects=True);r.raise_for_status();data=r.content
 if len(data)<MIN_BYTES:raise ValueError('small')
 try:
  with Image.open(io.BytesIO(data)) as src:src.load();im=ImageOps.exif_transpose(src).convert('RGB')
 except (UnidentifiedImageError,OSError,ValueError) as e:raise ValueError('not image') from e
 if min(im.size)<200:raise ValueError('dimensions')
 if max(im.size)>768:im.thumbnail((768,768),Image.Resampling.LANCZOS)
 out=io.BytesIO();im.save(out,'JPEG',quality=91,optimize=True);b=out.getvalue()
 if len(b)<MIN_BYTES:raise ValueError('jpeg small')
 return b,im.width,im.height
def existing(cls):
 hashes={hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/cls).glob('*.jpg')};urls=set()
 for base in (ROOT/cls,ROOT/'_rejected'/cls):
  if not base.exists():continue
  for p in base.glob('*.json'):
   try:urls.add(str(json.loads(p.read_text(encoding='utf-8')).get('url','')))
   except (OSError,json.JSONDecodeError):pass
 return hashes,urls
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--classes',nargs='*',choices=sorted(QUERIES),default=list(QUERIES));ap.add_argument('--target',type=int,default=60);a=ap.parse_args();summary=[]
 with httpx.Client(timeout=httpx.Timeout(45,connect=15)) as client:
  for cls in a.classes:
   d=ROOT/cls;d.mkdir(parents=True,exist_ok=True);hashes,urls=existing(cls);before=len(list(d.glob('*.jpg')));stats={'candidates':0,'saved':0,'failed':0,'duplicate':0}
   for q in QUERIES[cls]:
    for first in (1,36,71):
     if len(list(d.glob('*.jpg')))>=a.target:break
     try:rows=search(client,q,first)
     except httpx.HTTPError:stats['failed']+=1;continue
     for item in rows:
      if len(list(d.glob('*.jpg')))>=a.target:break
      stats['candidates']+=1;url=str(item['murl']);landing=str(item['purl'])
      if url in urls:stats['duplicate']+=1;continue
      urls.add(url);time.sleep(1.03)
      try:payload,w,h=download(client,url,landing)
      except (httpx.HTTPError,ValueError,OSError):stats['failed']+=1;continue
      digest=hashlib.sha256(payload).hexdigest()
      if digest in hashes:stats['duplicate']+=1;continue
      token=hashlib.sha256(url.encode()).hexdigest()[:8];image=d/f'web_{token}.jpg';side=d/f'web_{token}.json'
      if image.exists() or side.exists():stats['duplicate']+=1;continue
      md={'id':'bing:'+token,'title':item.get('t') or item.get('desc') or '','url':url,'foreign_landing_url':landing,'creator':'','license':'','license_url':'','provider':'bing','source':'bing_image_search','width':w,'height':h,'sha256':digest,'our_class':cls,'query':q,'local_file':image.relative_to(PROJECT).as_posix(),'downloaded_from':url,'review_status':'pending'}
      image.write_bytes(payload);side.write_text(json.dumps(md,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');hashes.add(digest);stats['saved']+=1;print(json.dumps({'class':cls,'count':len(list(d.glob('*.jpg'))),'file':image.name,'query':q},ensure_ascii=False),flush=True)
     time.sleep(1.0)
    if len(list(d.glob('*.jpg')))>=a.target:break
   row={'class':cls,'before':before,'stats':stats,'on_disk':len(list(d.glob('*.jpg')))};summary.append(row);print(json.dumps(row,ensure_ascii=False),flush=True)
 (PROJECT/'data/reports/round3_requested_web_stats.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
