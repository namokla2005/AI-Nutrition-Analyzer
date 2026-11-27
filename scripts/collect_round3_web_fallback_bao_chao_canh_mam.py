#!/usr/bin/env python3
"""Bing Images fallback collector for the round-3 four-class batch."""
from __future__ import annotations
import argparse, hashlib, html, io, json, re, time
from pathlib import Path
from urllib.parse import quote_plus
import httpx
from PIL import Image, ImageOps, UnidentifiedImageError
PROJECT=Path(__file__).resolve().parents[1]; ROOT=PROJECT/'data/raw/images'; REPORTS=PROJECT/'data/reports'; MIN=5120
SPECS={'banh_bao':['"bánh bao nhân thịt"','"bánh bao Việt Nam"','"Vietnamese steamed bun"'],'chao':['"cháo gà"','"cháo lòng"','"cháo Việt Nam"','"Vietnamese congee"'],'banh_canh':['"bánh canh cua"','"bánh canh giò heo"','"bánh canh Việt Nam"'],'bun_mam':['"bún mắm Sóc Trăng"','"bún mắm Cần Thơ"','"bún mắm Châu Đốc"','"tô bún mắm"','"bún mắm miền Tây"']}
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36'; last=0.0

def pace():
 global last
 d=1.03-(time.monotonic()-last)
 if d>0: time.sleep(d)
 last=time.monotonic()

def candidates(client,q):
 url=f'https://www.bing.com/images/search?q={quote_plus(q)}&form=HDRSC2&first=1&count=100'
 r=client.get(url,timeout=45); r.raise_for_status(); text=r.text
 out=[]
 for tag in re.findall(r'<a[^>]+class="[^"]*iusc[^"]*"[^>]*>',text,re.I):
  m=re.search(r'\bm="([^"]+)"',tag)
  if not m: continue
  try:
   data=json.loads(html.unescape(m.group(1))); image=data.get('murl'); page=data.get('purl')
   if image and page: out.append((str(image),str(page),str(data.get('t') or data.get('turl') or '')))
  except Exception: pass
 if not out:
  decoded=html.unescape(text)
  for image,page in re.findall(r'"murl":"(https?://.*?)".*?"purl":"(https?://.*?)"',decoded): out.append((image,page,''))
 return out

def collect(cls,target_total):
 folder=ROOT/cls; folder.mkdir(parents=True,exist_ok=True); existing=len(list(folder.glob('*.jpg'))); need=max(0,target_total-existing); seen=set(); hashes=set()
 for b in (folder,ROOT/'_rejected'/cls):
  if not b.exists():continue
  for p in b.glob('*.json'):
   try: seen.add(str(json.loads(p.read_text(encoding='utf-8')).get('url','')))
   except Exception:pass
  for p in b.glob('*.jpg'): hashes.add(hashlib.sha256(p.read_bytes()).hexdigest())
 saved=failed=0
 with httpx.Client(headers={'User-Agent':UA,'Accept':'text/html,application/xhtml+xml,image/avif,image/webp,image/*,*/*'}) as client:
  for query in SPECS[cls]:
   try: rows=candidates(client,query)
   except Exception as e: print(f'query failed {query}: {e}'); continue
   for image_url,page_url,title in rows:
    if saved>=need:break
    if image_url in seen:continue
    seen.add(image_url); pace()
    try:
     r=client.get(image_url,headers={'Referer':page_url,'Accept':'image/*'},timeout=30,follow_redirects=True); r.raise_for_status(); raw=r.content
     if len(raw)<MIN:raise ValueError('small')
     with Image.open(io.BytesIO(raw)) as im:
      im.load(); im=ImageOps.exif_transpose(im).convert('RGB')
      if min(im.size)<250 or max(im.size)<350:raise ValueError('dimensions')
      if max(im.size)>768: im.thumbnail((768,768),Image.Resampling.LANCZOS)
      buf=io.BytesIO(); im.save(buf,'JPEG',quality=92,optimize=True); payload=buf.getvalue(); w,h=im.size
     if len(payload)<MIN:raise ValueError('stored small')
     digest=hashlib.sha256(payload).hexdigest()
     if digest in hashes:continue
     token=hashlib.sha256(image_url.encode()).hexdigest()[:8]; stem=f'web_{token}'
     if (folder/f'{stem}.jpg').exists():continue
     meta={'id':token,'title':title,'url':image_url,'foreign_landing_url':page_url,'creator':'','license':'unknown','license_url':'','provider':'bing','source':'bing_image_search','width':w,'height':h,'sha256':digest,'our_class':cls,'query':query,'local_file':(folder/f'{stem}.jpg').relative_to(PROJECT).as_posix(),'downloaded_from':str(r.url),'review_status':'pending'}
     (folder/f'{stem}.jpg').write_bytes(payload);(folder/f'{stem}.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');hashes.add(digest);saved+=1
     print(json.dumps({'class':cls,'saved':saved,'file':stem+'.jpg','query':query},ensure_ascii=False),flush=True)
    except (httpx.HTTPError,OSError,ValueError,UnidentifiedImageError):failed+=1
   if saved>=need:break
 return {'class':cls,'before':existing,'saved':saved,'final':len(list(folder.glob('*.jpg'))),'failed':failed}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--classes',nargs='*',choices=sorted(SPECS),default=list(SPECS));ap.add_argument('--target',type=int,default=60);a=ap.parse_args(); rows=[collect(c,a.target) for c in a.classes]; REPORTS.mkdir(parents=True,exist_ok=True);(REPORTS/'round3_web_collection_stats_bao_chao_canh_mam.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(rows,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
