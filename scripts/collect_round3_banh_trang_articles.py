#!/usr/bin/env python3
from pathlib import Path
from io import BytesIO
import hashlib,html,json,re,time
from urllib.parse import quote_plus
import httpx
from PIL import Image,ImageOps
P=Path(__file__).resolve().parents[1];F=P/'data'/'raw'/'images'/'banh_trang_nuong'
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131 Safari/537.36'
def norm(b):
 if len(b)<5120:raise ValueError()
 with Image.open(BytesIO(b)) as s:s.load();im=ImageOps.exif_transpose(s).convert('RGB')
 if min(im.size)<180:raise ValueError()
 if max(im.size)>768:im.thumbnail((768,768),Image.Resampling.LANCZOS)
 o=BytesIO();im.save(o,'JPEG',quality=91,optimize=True);return o.getvalue(),im.width,im.height
def main():
 existing={hashlib.sha256(p.read_bytes()).hexdigest() for p in F.glob('*.jpg')};added=0
 with httpx.Client(headers={'User-Agent':UA},follow_redirects=True) as c:
  for first in (1,11,21,31,41,51):
   q='"bánh tráng nướng" công thức món ăn'
   r=c.get('https://www.bing.com/search',params={'q':q,'first':first,'count':10},timeout=60);time.sleep(1)
   links=re.findall(r'<h2[^>]*>\s*<a[^>]+href="(https?://[^"]+)"',r.text,re.I)
   for landing in links:
    if added>=25:break
    try:
     page=c.get(html.unescape(landing),timeout=40);time.sleep(1)
     m=re.search(r'<meta[^>]+(?:property|name)=["\']og:image["\'][^>]+content=["\']([^"\']+)',page.text,re.I)
     if not m:
      m=re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']og:image["\']',page.text,re.I)
     if not m:continue
     url=html.unescape(m.group(1));raw=c.get(url,headers={'Referer':landing},timeout=40).content;time.sleep(1)
     data,w,h=norm(raw);sha=hashlib.sha256(data).hexdigest()
     if sha in existing:continue
     existing.add(sha);key=hashlib.sha256(url.encode()).hexdigest()[:8];stem='web_'+key
     if (F/(stem+'.jpg')).exists():continue
     (F/(stem+'.jpg')).write_bytes(data)
     rec={'id':key,'title':'Bánh tráng nướng','url':url,'foreign_landing_url':landing,'creator':None,'license':None,'license_url':None,'provider':'Bing Web Search','source':'web','width':w,'height':h,'sha256':sha,'our_class':'banh_trang_nuong','query':q,'review_status':'pending'}
     (F/(stem+'.json')).write_text(json.dumps(rec,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');added+=1;print(added,stem,flush=True)
    except Exception:pass
 print('added',added)
if __name__=='__main__':main()
