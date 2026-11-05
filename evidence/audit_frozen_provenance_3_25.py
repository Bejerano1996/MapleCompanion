from pathlib import Path
import sys,json,random,hashlib
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
from training_accounting import TrainingAccountant
from session_rewards import session_token
cases=0
for seed in range(200):
 rng=random.Random(seed);base_a=rng.randint(4,80);bonus_a=rng.randint(1,base_a//2);base_b=rng.randint(4,80);bonus_b=rng.randint(1,base_b//2)
 for scenario in ('old_unread','old_refined_after_new','old_refined_before_new','old_inserted_before_new'):
  s=dict(id='probe',running_since=1,auto_rewards=True,exp=0,kills=0,mesos=0);a=TrainingAccountant();token=session_token(s)
  a.feed(s,token,[],{'level':27,'exp':1000},0)
  events=[('exp',base_a)]
  if scenario!='old_inserted_before_new':events.append(('bonus',None))
  a.feed(s,token,list(events),{'level':27,'exp':1000+base_a+bonus_a},1)
  events.append(('exp',base_b));a.feed(s,token,list(events),None,2)
  if scenario in ('old_refined_before_new','old_inserted_before_new'):
   if scenario=='old_inserted_before_new':events.insert(1,('bonus',bonus_a))
   else:events[1]=('bonus',bonus_a)
   a.feed(s,token,list(events),None,2.5)
  events.append(('bonus',bonus_b));a.feed(s,token,list(events),None,3)
  if scenario=='old_refined_after_new':events[1]=('bonus',bonus_a);a.feed(s,token,list(events),None,4)
  a.feed(s,token,list(events),None,20)
  expected=base_a+bonus_a+base_b+bonus_b
  assert s['exp']==expected,(seed,scenario,s['exp'],expected)
  a.feed(s,token,list(events),{'level':27,'exp':1000+expected},21)
  assert s['exp']==expected
  cases+=1
report=dict(ok=True,cases=cases,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='Synthetic ordered old/new bonus refinement/insertion and trailing sequence,HDUoutage/recovery; not livegameplay')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
