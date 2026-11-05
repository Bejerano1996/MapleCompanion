from pathlib import Path
import sys,json,hashlib
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
from PIL import Image
from game_sync import find_minimap,minimap_title
from training_context import map_from_title
maps={str(i):dict(id=str(i),displayName='Ant Tunnel '+'I'*i,displayStreet='Dungeon') for i in (1,2,3)}
cases=[]
for name,expected in [('live_frame_ant_tunnel2.png','2'),('live_frame_1920.png','2'),('live_exp_2560.png','3')]:
 original=Image.open(root/'tests'/name).convert('RGB')
 for scale in (1,.85,.7,.5):
  image=original.resize((round(original.width*scale),round(original.height*scale)),Image.Resampling.LANCZOS)
  frame=find_minimap(image);title=minimap_title(image,frame) if frame else None
  found=map_from_title(title,maps) if title is not None else None
  cases.append(dict(fixture=name,scale=scale,expected=expected,found=found,status='correct' if found==expected else 'unavailable' if found is None else 'wrong'))
report=dict(ok=not any(c['status']=='wrong' for c in cases),cases=cases,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='Local supplied fullgame screenshots with synthetic downscaling; unknown is distinguished from wrong; no livegameplay')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
