from pathlib import Path
import sys,json,hashlib,random
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
from training_accounting import TrainingAccountant
from session_rewards import session_token
import leveling
rng=random.Random(1508);cases=0
for level in range(1,99):
 for delay in (.05,1.,4.99,5.):
  for hud_first in (False,True):
   base=rng.randint(2,min(20,max(2,leveling.exp_to_next(level+1)//3)))
   bonus=rng.randint(1,max(1,base//2));gain=base+bonus
   remain=rng.randint(1,min(gain,leveling.exp_to_next(level)))
   before={'level':level,'exp':leveling.exp_to_next(level)-remain};after={'level':level+1,'exp':gain-remain}
   s=dict(id='party-cross',running_since=1,auto_rewards=True,exp=0,kills=0,mesos=0);a=TrainingAccountant();token=session_token(s)
   a.feed(s,token,[],before,0);a.feed(s,token,[],before,.1)
   unknown=[('exp',base),('bonus',None)];full=[('exp',base),('bonus',bonus)]
   if hud_first:
    a.feed(s,token,unknown,after,1.)
    a.feed(s,token,full,None,1.+delay)
   else:
    a.feed(s,token,full,None,1.)
    a.feed(s,token,full,after,1.+delay)
   for now in (21.,22.,25.):a.feed(s,token,full,None,now)
   assert s['exp']==gain,(level,delay,hud_first,s,a.logs_since_bar)
   assert s['party_exp']==bonus and s['kills']==1,(level,s)
   a.feed(s,token,full,after,26.)
   assert s['exp']==gain
   assert a.character==after
   cases+=1
report=dict(ok=True,cases=cases,levels=[1,98],bonus_delays=[.05,1,4.99,5],both_hud_notice_orders=True,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='Production accountant, synthetic one-level crossings and late party refinements within supported5second grace; no OCR/live game')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
