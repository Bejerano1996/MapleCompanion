from pathlib import Path
import sys,json,hashlib,random
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
from training_accounting import TrainingAccountant
from session_rewards import session_token
for seed in range(200):
 rng=random.Random(seed);base=rng.randint(4,80);bonus=rng.randint(1,max(1,base//2));loss=rng.randint(1,500)
 s=dict(id='probe',running_since=1,auto_rewards=True,exp=0,kills=0,mesos=0);a=TrainingAccountant();token=session_token(s)
 events=[('exp',base),('bonus',None)]
 a.feed(s,token,[],{'level':27,'exp':1000},0)
 a.feed(s,token,events,{'level':27,'exp':1000+base+bonus},1)
 a.feed(s,token,events,{'level':27,'exp':1000-loss},1.5)
 events[1]=('bonus',bonus)
 a.feed(s,token,events,None,rng.uniform(1.6,5.9))
 a.feed(s,token,events,None,20)
 assert s['exp']==-loss,(seed,s)
 events.extend([('exp',base),('bonus',bonus)])
 a.feed(s,token,events,None,21)
 assert s['exp']==-loss+base+bonus,(seed,'following reward',s)
report=dict(ok=True,seeds=200,assertions=400,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='Synthetic death/HUD-loss and late bonus within existing5second reconciliation window; no live gameplay')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
