from pathlib import Path
import sys,json,hashlib
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
from PIL import Image
from session_reader import read_character_image
cases=[];wrong=[]
for name,lv,n in [('live_exp_2560.png',26,29285),('live_frame_ant_tunnel2.png',25,5299),('live_frame_1920.png',25,5340)]:
 im=Image.open(root/'tests'/name).convert('RGB');w,h=im.size;footer=im.crop((int(w*.1),int(h*.91),int(w*.92),h))
 for removed in (.25,.35,.45):
  cropped=footer.crop((int(footer.width*removed),0,footer.width,footer.height));reading=read_character_image(cropped)
  c=dict(fixture=name,left_fraction_removed=removed,reading=reading,expected=dict(level=lv,exp=n));cases.append(c)
  if reading and (reading['level'],reading['exp'])!=(lv,n):wrong.append(c)
report=dict(ok=not wrong,cases=cases,wrong=wrong,unknown=sum(c['reading'] is None for c in cases),fallback_reads=sum(c['reading'] is not None and c['reading']['source']=='EXP+percent' for c in cases),source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='Actual3localHUDfooterOCR after removing25/35/45percentleftregion, tests loss ofLVlabel and uniqueEXP/percentfallback; no gamecapture')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(dict(ok=report['ok'],cases=len(cases),unknown=report['unknown'],fallback_reads=report['fallback_reads'],wrong=wrong)))
