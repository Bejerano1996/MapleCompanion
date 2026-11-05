from pathlib import Path
import sys,json,random,hashlib
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
from training_model import character_reading,absolute_exp
from training_accounting import TrainingAccountant
from session_rewards import session_token
import leveling
steps=0;injected=0
for seed in range(200):
 rng=random.Random(seed);level=27;exp=63000;now=0.;s=dict(id='mixed',running_since=1,auto_rewards=True,exp=0,mesos=0,kills=0);a=TrainingAccountant();token=session_token(s)
 def parsed(lv,n,explicit=None):return character_reading([f'LV. {lv if explicit is None else explicit}',f'EXP. {n:,} [{100*n/leveling.exp_to_next(lv):.2f}%]'])
 start=absolute_exp({'level':level,'exp':exp})
 a.feed(s,token,[],parsed(level,exp),now);a.feed(s,token,[],parsed(level,exp),.1)
 for index in range(50):
  now+=rng.uniform(.2,2)
  if index%7==0:
   invalid=parsed(level,exp,100);assert invalid is None
   a.feed(s,token,[],invalid,now);injected+=1;now+=.1
  if index%9==0:
   a.feed(s,token,[],parsed(level+3,100),now);injected+=1;now+=.1
  gain=-rng.randint(1,800) if rng.random()<.15 else rng.randint(1,200)
  exp=max(0,exp+gain)
  while exp>=leveling.exp_to_next(level):exp-=leveling.exp_to_next(level);level+=1
  r=parsed(level,exp);assert r is not None
  a.feed(s,token,[],r,now)
  expected=absolute_exp({'level':level,'exp':exp})-start
  assert s['exp']==expected,(seed,index,s['exp'],expected)
  steps+=1
report=dict(ok=True,seeds=200,valid_steps=steps,rejected_or_unconfirmed_injections=injected,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='Synthetic formatted HUD text->parser->accountant with gains,losses,levelup and unsupported/outlier levels; no OCR image recognition or livegameplay')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
