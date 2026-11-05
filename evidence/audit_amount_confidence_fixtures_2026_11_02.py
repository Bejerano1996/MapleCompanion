from pathlib import Path
import sys,json,hashlib
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
from PIL import Image,ImageEnhance
from session_reader import read_reward_image
from session_rewards import RewardTracker
cases=[]
for name,factor,expected_exp,expected_money in [('session-rewards-fixture.png',1,9,27),('session-rewards-fixture.png',1.2,2,17),('party-rewards-fixture.png',1,4,0)]:
 image=ImageEnhance.Brightness(Image.open(root/'tests'/name).convert('RGB')).enhance(factor)
 events=read_reward_image(image,True);tracker=RewardTracker(confirm_money=2);tracker.feed([]);total=dict(exp=0,mesos=0)
 for _ in range(3):
  delta=tracker.feed(events)
  for key in total:total[key]+=delta[key]
 assert total==dict(exp=expected_exp,mesos=expected_money),(name,factor,total,list(events))
 cases.append(dict(fixture=name,brightness=factor,totals=total))
report=dict(ok=True,cases=cases,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='Preservation of existing known observed fixture totals,not full actual reward recovery; offline supplied images')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
