#!/usr/bin/env python3
from pathlib import Path
from io import BytesIO
import hashlib,html,json,re,time
import httpx
from PIL import Image,ImageOps
P=Path(__file__).resolve().parents[1];F=P/'data'/'raw'/'images'/'banh_trang_nuong'; UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131 Safari/537.36'
def norm(b):
 if len(b)<5120:raise ValueError()
 with Image.open(BytesIO(b)) as s:s.load();im=ImageOps.exif_transpose(s).convert('RGB')
 if min(im.size)<180:raise ValueError()
 if max(im.size)>768:im.thumbnail((768,768),Image.Resampling.LANCZOS)
 o=BytesIO();im.save(o,'JPEG',quality=91,optimize=True);return o.getvalue(),im.width,im.height
def main():
 q='banh trang nuong Vietnamese rice paper pizza'; search='https://images.search.yahoo.com/search/images?p='+q.replace(' ','+')
 with httpx.Client(headers={'User-Agent':UA},follow_redirects=True) as c:
  text=c.get(search,timeout=60).text
  pairs=re.findall(r'"iurl":"(https?:\\?/\\?/[^" ]+)".*?"rurl":"(https?:\\?/\\?/[^" ]+)"',text)
  if not pairs:pairs=[(u,search) for u in re.findall(r'"iurl":"(https?:\\?/\\?/[^" ]+)"',text)]
  existing={hashlib.sha256(p.read_bytes()).hexdigest() for p in F.glob('*.jpg')};added=0
  for url,landing in pairs:
   if added>=30:break
   url=url.replace('\\/','/');landing=landing.replace('\\/','/')
   try:
    raw=c.get(url,headers={'Referer':landing},timeout=40).content;time.sleep(1);data,w,h=norm(raw);sha=hashlib.sha256(data).hexdigest()
    if sha in existing:continue
    existing.add(sha);key=hashlib.sha256(url.encode()).hexdigest()[:8];stem='web_'+key
    if (F/(stem+'.jpg')).exists():continue
    (F/(stem+'.jpg')).write_bytes(data);rec={'id':key,'title':q,'url':url,'foreign_landing_url':landing,'creator':None,'license':None,'license_url':None,'provider':'Yahoo Images','source':'web','width':w,'height':h,'sha256':sha,'our_class':'banh_trang_nuong','query':q,'review_status':'pending'};(F/(stem+'.json')).write_text(json.dumps(rec,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');added+=1
   except Exception:pass
  print('pairs',len(pairs),'added',added)
if __name__=='__main__':main()
