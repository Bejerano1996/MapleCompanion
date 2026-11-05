from pathlib import Path
import sys,json,hashlib,random
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
from training_accounting import TrainingAccountant
from training_model import absolute_exp
from session_rewards import session_token
import leveling
rng=random.Random(1523);cases=0
for level in range(1,98):
 for jump in (2,3,5):
  if level+jump>99:continue
  for interval in (6.,15.,15.001):
   prior=(-100,0,500)[cases%3]
   before={'level':level,'exp':rng.randrange(leveling.exp_to_next(level))}
   after={'level':level+jump,'exp':rng.randrange(leveling.exp_to_next(level+jump))}
   expected=prior+absolute_exp(after)-absolute_exp(before)
   s=dict(id='multi-party',running_since=1,auto_rewards=True,exp=prior,kills=7,party_exp=11,mesos=80)
   a=TrainingAccountant();t=session_token(s);a.feed(s,t,[],before,0);a.feed(s,t,[],before,.1)
   a.feed(s,t,[('exp',7),('bonus',None)],after,1.)
   assert s['exp']==prior and a.character==before
   a.feed(s,t,[('exp',7),('bonus',2)],None,1.+interval/2)
   assert s['exp']==prior
   a.feed(s,t,[('exp',7),('bonus',2)],after,1.+interval)
   if interval>15:
    assert s['exp']==prior+9 and a.character==before
    assert s['exp_source']=='Reward log \u00b7 partial'
    a.feed(s,t,[('exp',7),('bonus',2)],after,2.+interval)
   assert s['exp']==expected and a.character==after,(level,jump,interval,s,expected)
   a.feed(s,t,[('exp',7),('bonus',2)],None,40.)
   assert s['exp']==expected and s['party_exp']==13 and s['kills']==8 and s['mesos']==80
   cases+=1
report=dict(ok=True,cases=cases,jumps=[2,3,5],confirmation_intervals=[6,15,15.001],prior_exp=[-100,0,500],source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='Synthetic multi-level positive HUD jumps; party refinement between confirmation reads, production accountant; no OCR/livegame')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
