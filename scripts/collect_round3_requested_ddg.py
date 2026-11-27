#!/usr/bin/env python3
"""DuckDuckGo Images fallback collector for requested classes."""
from __future__ import annotations
import argparse,hashlib,io,json,re,time
from pathlib import Path
import httpx
from PIL import Image,ImageOps,UnidentifiedImageError
P=Path(__file__).resolve().parents[1];ROOT=P/'data/raw/images';UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131 Safari/537.36';MIN=5120
Q={'banh_uot':['"bánh ướt" món ăn Việt Nam','"bánh ướt" chả lụa','"banh uot" Vietnamese food'],'banh_tom':['"bánh tôm" Hồ Tây','"bánh tôm" Hà Nội','"banh tom" shrimp fritter'],'bo_kho':['"bò kho" món Việt','"bò kho" bánh mì','"bo kho" Vietnamese beef stew'],'thit_kho_trung':['"thịt kho trứng" món ăn','"thịt kho tàu" trứng','"Vietnamese braised pork eggs"']}
def ddg(client,q):
 h=client.get('https://duckduckgo.com/',params={'q':q},headers={'User-Agent':UA});h.raise_for_status();m=re.search(r'vqd=["\']?([\d-]+)',h.text)
 if not m:raise ValueError('no vqd')
 r=client.get('https://duckduckgo.com/i.js',params={'l':'vn-vi','o':'json','q':q,'vqd':m.group(1),'f':',,,','p':'1'},headers={'User-Agent':UA,'Referer':str(h.url)});r.raise_for_status();return r.json().get('results') or []
def image(client,url,referer):
 r=client.get(url,headers={'User-Agent':UA,'Accept':'image/*','Referer':referer},follow_redirects=True);r.raise_for_status();b=r.content
 if len(b)<MIN:raise ValueError()
 try:
  with Image.open(io.BytesIO(b)) as s:s.load();im=ImageOps.exif_transpose(s).convert('RGB')
 except (UnidentifiedImageError,OSError,ValueError):raise ValueError()
 if min(im.size)<200:raise ValueError()
 if max(im.size)>768:im.thumbnail((768,768),Image.Resampling.LANCZOS)
 o=io.BytesIO();im.save(o,'JPEG',quality=91,optimize=True);payload=o.getvalue()
 if len(payload)<MIN:raise ValueError()
 return payload,im.width,im.height
def current(cls):
 hashes={hashlib.sha256(x.read_bytes()).hexdigest() for x in (ROOT/cls).glob('*.jpg')};urls=set()
 for base in (ROOT/cls,ROOT/'_rejected'/cls):
  if base.exists():
   for s in base.glob('*.json'):
    try:urls.add(str(json.loads(s.read_text(encoding='utf-8')).get('url','')))
    except Exception:pass
 return hashes,urls
def main():
 a=argparse.ArgumentParser();a.add_argument('--target',type=int,default=60);a.add_argument('--classes',nargs='*',choices=sorted(Q),default=list(Q));z=a.parse_args();summary=[]
 with httpx.Client(timeout=httpx.Timeout(45,connect=15)) as c:
  for cls in z.classes:
   d=ROOT/cls;hs,urls=current(cls);before=len(list(d.glob('*.jpg')));st={'candidate':0,'saved':0,'failed':0,'duplicate':0}
   for q in Q[cls]:
    if len(list(d.glob('*.jpg')))>=z.target:break
    try:rows=ddg(c,q)
    except Exception as e:print(json.dumps({'class':cls,'query':q,'error':str(e)},ensure_ascii=False));st['failed']+=1;continue
    for it in rows:
     if len(list(d.glob('*.jpg')))>=z.target:break
     st['candidate']+=1;url=str(it.get('image') or '');landing=str(it.get('url') or '')
     if not url or url in urls:st['duplicate']+=1;continue
     urls.add(url);time.sleep(1.03)
     try:payload,w,h=image(c,url,landing)
     except Exception:st['failed']+=1;continue
     dig=hashlib.sha256(payload).hexdigest()
     if dig in hs:st['duplicate']+=1;continue
     token=hashlib.sha256(url.encode()).hexdigest()[:8];im=d/f'web_{token}.jpg';side=d/f'web_{token}.json'
     if im.exists() or side.exists():st['duplicate']+=1;continue
     md={'id':'ddg:'+token,'title':it.get('title') or '','url':url,'foreign_landing_url':landing,'creator':'','license':'','license_url':'','provider':'duckduckgo','source':'duckduckgo_image_search','width':w,'height':h,'sha256':dig,'our_class':cls,'query':q,'local_file':im.relative_to(P).as_posix(),'downloaded_from':url,'review_status':'pending'}
     im.write_bytes(payload);side.write_text(json.dumps(md,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');hs.add(dig);st['saved']+=1;print(json.dumps({'class':cls,'count':len(list(d.glob('*.jpg'))),'file':im.name},ensure_ascii=False),flush=True)
   summary.append({'class':cls,'before':before,'stats':st,'on_disk':len(list(d.glob('*.jpg')))})
 (P/'data/reports/round3_requested_ddg_stats.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
