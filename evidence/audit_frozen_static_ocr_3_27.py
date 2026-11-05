from pathlib import Path
import sys,json,hashlib,random
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
from PIL import Image,ImageOps
import session_reader as reader
from session_rewards import RewardTracker
captures={};failures=[];polls=0
for name in ('session-rewards-fixture.png','party-rewards-fixture.png'):
 im=Image.open(root/'tests'/name).convert('RGB');reads=[]
 for left,top in ((0,0),(1,0),(0,1),(2,3),(3,2),(4,4),(8,4),(4,8),(12,12)):
  reader._money_retry_turn=0;events=reader.read_reward_image(ImageOps.expand(im,border=(left,top,12-left,12-top),fill=(0,0,0)),True)
  reads.append(events)
 captures[name]=[dict(events=list(e),positions=e.positions,trusted_money=sorted(e.trusted_money),partial=e.partial) for e in reads]
 for seed in range(100):
  rng=random.Random(seed);t=RewardTracker(confirm_money=2);order=[rng.randrange(len(reads)) for _ in range(50)]
  t.feed(reads[order[0]])
  for frame,index in enumerate(order[1:],1):
   d=t.feed(reads[index]);polls+=1
   if any(d.values()):failures.append(dict(fixture=name,seed=seed,frame=frame,order=order[:frame+1],delta=d));break
report=dict(ok=not failures,streams=200,polls=polls,failures=failures,captures=captures,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='ActualOCRresults/positions/confidences from18translated localimagevariants replayed as static pre-session messages; all deltas shouldzero; notlivegame')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(dict(ok=report['ok'],streams=200,polls=polls,failures=len(failures),examples=failures[:2])))
