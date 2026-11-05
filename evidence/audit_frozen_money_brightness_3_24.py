from pathlib import Path
import sys,json,random,hashlib
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
from PIL import Image,ImageOps,ImageEnhance
import session_reader as reader
from session_rewards import RewardTracker
captures={};failures=[];polls=0
for name in ('session-rewards-fixture.png','party-rewards-fixture.png'):
 im=Image.open(root/'tests'/name).convert('RGB');reads=[];specs=[]
 for brightness in (.8,1.,1.2):
  for left,top in ((0,0),(8,4)):
   reader._money_retry_turn=0;image=ImageOps.expand(ImageEnhance.Brightness(im).enhance(brightness),border=(left,top,12-left,12-top),fill=(0,0,0))
   events=reader.read_reward_image(image,True);reads.append(events);specs.append(dict(brightness=brightness,padding=[left,top]))
 captures[name]=[dict(spec=spec,events=list(e),positions=e.positions,trusted_money=sorted(e.trusted_money)) for spec,e in zip(specs,reads)]
 for seed in range(100):
  r=random.Random(seed);order=[r.randrange(len(reads)) for _ in range(50)];t=RewardTracker(confirm_money=2);t.feed(reads[order[0]])
  for frame,index in enumerate(order[1:],1):
   delta=t.feed(reads[index]);polls+=1
   if any(delta.values()):failures.append(dict(fixture=name,seed=seed,frame=frame,order=order[:frame+1],delta=delta));break
report=dict(ok=not failures,streams=200,polls=polls,failures=failures,captures=captures,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='Actual12combinedbrightness/translationOCRvariants replayed as unchanged oldnotices; no livegame')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(dict(ok=report['ok'],streams=200,polls=polls,failures=len(failures),examples=failures[:2])))
