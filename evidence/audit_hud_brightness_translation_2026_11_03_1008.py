from pathlib import Path
import sys,json,hashlib
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
from PIL import Image,ImageOps,ImageEnhance
from session_reader import read_character_image
cases=[];wrong=[]
for name,level,exp in [('live_exp_2560.png',26,29285),('live_frame_ant_tunnel2.png',25,5299),('live_frame_1920.png',25,5340)]:
 im=Image.open(root/'tests'/name).convert('RGB');w,h=im.size;footer=im.crop((int(w*.1),int(h*.91),int(w*.92),h))
 for brightness in (.8,1.,1.2):
  for left,top in ((0,0),(3,2)):
   image=ImageOps.expand(ImageEnhance.Brightness(footer).enhance(brightness),border=(left,top,6-left,4-top),fill=(0,0,0));reading=read_character_image(image)
   case=dict(fixture=name,brightness=brightness,padding=[left,top],reading=reading,expected=dict(level=level,exp=exp));cases.append(case)
   if reading and (reading['level'],reading['exp'])!=(level,exp):wrong.append(case)
report=dict(ok=not wrong,cases=cases,wrong=wrong,unknown_cases=sum(c['reading'] is None for c in cases),source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='ActualOCR of3localHUDfooters withbrightness.8/1/1.2 andsmallcontent-preservingtranslation, knownEXP/leveltargets; no livegamecapture')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(dict(ok=report['ok'],cases=len(cases),wrong=len(wrong),unknown=report['unknown_cases'],examples=wrong[:2])))
