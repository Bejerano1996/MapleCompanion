from pathlib import Path
import sys,json,random,hashlib
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
from session_rewards import RewardTracker
from session_reader import RewardRead
cases=0
for seed in range(200):
 rng=random.Random(seed);spacing=rng.randint(18,26);height=rng.randint(12,16)
 positions=lambda:[(spacing*i+rng.uniform(-1,1),height) for i in range(4)]
 new_amount=rng.choice([30,40,50])
 old=[('mesos',10),('mesos',None),('mesos',20),('mesos',30)]
 new=[('mesos',None),('mesos',20),('mesos',30),('mesos',new_amount)]
 t=RewardTracker(confirm_money=2);t.feed(RewardRead(old,False,(),positions()))
 total=0
 for _ in range(5):total+=t.feed(RewardRead(new,False,(),positions()))['mesos']
 assert total==new_amount,(seed,total,new_amount)
 cases+=1
report=dict(ok=True,cases=cases,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='Synthetic actual one-row scroll with missing amount,two distinct surviving amounts,small geometry jitter,new pickup may equal surviving amount; no live gameplay')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
