from pathlib import Path
import sys,json,random,hashlib
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
from training_accounting import TrainingAccountant
from session_rewards import session_token
from session_reader import RewardRead
checks=[]
for seed in range(500):
 r=random.Random(seed);s=dict(id='audit',running_since=1,auto_rewards=True,exp=0,mesos=0,kills=0,party_exp=0);a=TrainingAccountant();token=session_token(s)
 def feed(rows,now,exp=None):a.feed(s,token,RewardRead(rows,False),None if exp is None else {'level':27,'exp':exp},now)
 feed([],0,10000);feed([],.1,10000)
 rows=[];gain=money=party=0;now=16+r.random()*20
 for i in range(r.randint(1,8)):
  base=r.randint(5,40);bonus=r.randint(1,5);coin=r.randint(1,100);rows += [('exp',base),('bonus',bonus),('mesos',coin)]
  gain+=base+bonus;party+=bonus;money+=coin
  feed(rows,now);feed(rows,now+.15);now+=.4
 assert s['exp']==gain and s['mesos']==money,(seed,'fallback',s,gain,money)
 loss=r.randint(0,300) if seed%2 else 0
 feed(rows,now,10000+gain-loss)
 assert s['exp']==gain-loss,(seed,'recovery',s,gain,loss)
 for offset in (.2,16,31):feed(rows,now+offset)
 assert s['exp']==gain-loss and s['party_exp']==party and s['mesos']==money,(seed,'duplicate',s)
 rows += [('exp',7),('bonus',2),('mesos',17)]
 feed(rows,now+32,10000+gain-loss+9);feed(rows,now+32.2);feed(rows,now+49)
 assert s['exp']==gain-loss+9 and s['mesos']==money+17 and s['party_exp']==party+2,(seed,'next',s)
 checks.append(seed)
report=dict(ok=True,cases=len(checks),source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='Randomized15secondHUDfallback then authoritative HUD recovery, optionalnetloss, moneyconfirmation, repeatednotices and freshpartyreward; synthetic only, no OCR/livegame')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
