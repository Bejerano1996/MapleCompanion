"""Local supplied HUD screenshots only; no live screen capture."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image
from session_reader import read_character_image
here=Path(__file__).parent;results=[]
for name,lv,n in [('live_exp_2560.png',26,29285),('live_frame_ant_tunnel2.png',25,5299),('live_frame_1920.png',25,5340)]:
 image=Image.open(here/name).convert('RGB');w,h=image.size
 r=read_character_image(image.crop((int(w*.1),int(h*.91),int(w*.92),h)))
 assert r and (r['level'],r['exp'])==(lv,n),(name,r)
 results.append({'image':name,'level':r['level'],'exp':r['exp']})
print(json.dumps({'ok':True,'results':results}))
