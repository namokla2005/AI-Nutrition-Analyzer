#!/usr/bin/env python3
"""Collect focused round-3 supplements from DuckDuckGo Images."""
from __future__ import annotations
import hashlib, html, json, re, time
from io import BytesIO
from pathlib import Path
from urllib.parse import quote_plus
import httpx
from PIL import Image, ImageOps

PROJECT=Path(__file__).resolve().parents[1]
ROOT=PROJECT/'data'/'raw'/'images'
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131 Safari/537.36'
NEED={'goi_ga':55,'mi_xao':55,'banh_trang_nuong':25}
QUERIES={
 'goi_ga':['Vietnamese chicken salad recipe','goi ga chicken salad','Vietnamese cabbage chicken salad'],
 'mi_xao':['Vietnamese stir fried noodles recipe','mi xao noodles','Vietnamese seafood stir fried noodles'],
 'banh_trang_nuong':['banh trang nuong recipe','Vietnamese rice paper pizza grilled'],
}

def norm(raw):
 if len(raw)<5120: raise ValueError('small')
 with Image.open(BytesIO(raw)) as src:
  src.load(); im=ImageOps.exif_transpose(src).convert('RGB')
 if min(im.size)<180: raise ValueError('dimensions')
 if max(im.size)>768: im.thumbnail((768,768),Image.Resampling.LANCZOS)
 out=BytesIO(); im.save(out,'JPEG',quality=91,optimize=True); data=out.getvalue()
 if len(data)<5120: raise ValueError('small jpeg')
 return data,im.width,im.height

def results(client,q):
 page=client.get('https://duckduckgo.com/',params={'q':q},timeout=60).text
 matches=re.findall(r'vqd=["\']?([\d-]+)',page)
 if not matches: matches=re.findall(r'vqd["\']?\s*[:=]\s*["\']([\d-]+)',page)
 if not matches: raise ValueError('no vqd token')
 vqd=matches[0]; out=[]
 for _ in range(3):
  r=client.get('https://duckduckgo.com/i.js',params={'l':'us-en','o':'json','q':q,'vqd':vqd,'f':',,,','p':'1'},headers={'Referer':'https://duckduckgo.com/'},timeout=60)
  r.raise_for_status(); payload=r.json(); out.extend(payload.get('results') or [])
  nxt=payload.get('next')
  if not nxt: break
  time.sleep(1)
  r=client.get('https://duckduckgo.com'+nxt,headers={'Referer':'https://duckduckgo.com/'},timeout=60)
  r.raise_for_status(); payload=r.json(); out.extend(payload.get('results') or [])
  if not payload.get('next'): break
 return out

def main():
 summary=[]
 with httpx.Client(headers={'User-Agent':UA},follow_redirects=True) as client:
  for cls,target in NEED.items():
   folder=ROOT/cls; existing={hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.glob('*.jpg')}
   known={json.loads(p.read_text(encoding='utf-8')).get('url') for p in folder.glob('ddg_*.json')}
   added=0
   for q in QUERIES[cls]:
    if added>=target: break
    try: candidates=results(client,q)
    except Exception as e:
     print(json.dumps({'warning':str(e),'query':q}),flush=True); continue
    for item in candidates:
     if added>=target: break
     url=str(item.get('image') or ''); landing=str(item.get('url') or '')
     if not url or not landing or url in known: continue
     known.add(url)
     try:
      r=client.get(url,headers={'Referer':landing},timeout=45); r.raise_for_status()
      data,w,h=norm(r.content); time.sleep(1)
      sha=hashlib.sha256(data).hexdigest()
      if sha in existing: continue
      existing.add(sha); key=hashlib.sha256(url.encode()).hexdigest()[:8]; stem='web_'+key
      if (folder/(stem+'.jpg')).exists(): continue
      (folder/(stem+'.jpg')).write_bytes(data)
      rec={'id':key,'title':html.unescape(str(item.get('title') or '')),'url':url,'foreign_landing_url':landing,'creator':None,'license':None,'license_url':None,'provider':'DuckDuckGo Images','source':'web','width':w,'height':h,'sha256':sha,'our_class':cls,'query':q,'review_status':'pending'}
      (folder/(stem+'.json')).write_text(json.dumps(rec,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
      added+=1; print(json.dumps({'class':cls,'added':added,'file':stem+'.jpg'}),flush=True)
     except Exception: continue
   summary.append({'class':cls,'added':added})
 print(json.dumps(summary,ensure_ascii=False,indent=2))
 return 0
if __name__=='__main__': raise SystemExit(main())
