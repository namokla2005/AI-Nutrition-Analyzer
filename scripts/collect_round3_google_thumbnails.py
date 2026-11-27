#!/usr/bin/env python3
from pathlib import Path
from io import BytesIO
import hashlib,html,json,re,time
import httpx
from PIL import Image,ImageOps
P=Path(__file__).resolve().parents[1];R=P/'data'/'raw'/'images'
Q={'goi_ga':'Vietnamese chicken salad dish food','mi_xao':'stir fried noodles plate food','banh_trang_nuong':'banh trang nuong rice paper pizza'}
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131 Safari/537.36'
def norm(b):
 if len(b)<3000: raise ValueError()
 with Image.open(BytesIO(b)) as s:s.load();im=ImageOps.exif_transpose(s).convert('RGB')
 if min(im.size)<100: raise ValueError()
 out=BytesIO();im.save(out,'JPEG',quality=92);return out.getvalue(),im.width,im.height
def main():
 with httpx.Client(headers={'User-Agent':UA},follow_redirects=True) as c:
  for cls,q in Q.items():
   search='https://www.google.com/search?udm=2&q='+httpx.QueryParams({'q':q})['q'].replace(' ','+')
   raw_text=c.get(search,timeout=60).text
   if cls=='goi_ga': (P/'data'/'reports'/'google_debug.html').write_text(raw_text,encoding='utf-8')
   text=raw_text.replace('\\u003d','=').replace('\\u0026','&')
   urls=re.findall(r'https://encrypted-tbn\d+\.gstatic\.com/images\?q=tbn:[^"& ]+(?:&[^" ]+)*',text)
   urls=[html.unescape(u) for u in urls]
   seen=set();added=0;folder=R/cls
   existing={hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.glob('*.jpg')}
   for u in urls:
    if u in seen or added>=60:continue
    seen.add(u)
    try:
     b=c.get(u,timeout=30).content;data,w,h=norm(b);time.sleep(1);sha=hashlib.sha256(data).hexdigest()
     if sha in existing:continue
     existing.add(sha);key=hashlib.sha256(u.encode()).hexdigest()[:8];stem='web_'+key
     if (folder/(stem+'.jpg')).exists():continue
     (folder/(stem+'.jpg')).write_bytes(data)
     rec={'id':key,'title':q,'url':u,'foreign_landing_url':search,'creator':None,'license':None,'license_url':None,'provider':'Google Images thumbnail','source':'web','width':w,'height':h,'sha256':sha,'our_class':cls,'query':q,'review_status':'pending'}
     (folder/(stem+'.json')).write_text(json.dumps(rec,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');added+=1
    except Exception:pass
   print(cls,'candidates',len(urls),'added',added,flush=True)
if __name__=='__main__':main()
