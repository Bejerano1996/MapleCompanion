from pathlib import Path
import sys,json,random,hashlib
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
from training_accounting import TrainingAccountant
from session_rewards import session_token
from session_reader import RewardRead
cases=[]
def run(gain,missing,late_total):
 s=dict(id='audit',running_since=1,auto_rewards=True,exp=0,mesos=0,kills=0,party_exp=0);a=TrainingAccountant();t=session_token(s)
 def poll(rows,now,exp=None):a.feed(s,t,RewardRead(rows,False),None if exp is None else dict(level=27,exp=10000+exp),now)
 poll([],0,0);poll([],.1,0);rows=[('exp',gain-2),('bonus',2)]
 poll(rows,16);poll(rows,17,gain-missing);recovered=s['exp'];poll(rows,34);fallback=s['exp']
 poll(rows,35,late_total);confirmed=s['exp'];poll(rows,36,late_total);poll(rows,53)
 return recovered,fallback,confirmed,s['exp']
r=random.Random(2153)
for _ in range(200):
 gain=r.randint(10,100);missing=r.randint(1,gain-1)
 loss=run(gain,missing,gain-missing);lag=run(gain,missing,gain)
 assert loss[:2]==lag[:2]==(gain-missing,gain)
 assert loss[2]==gain-missing and lag[2]==gain
 cases.append(dict(gain=gain,ambiguous=missing,loss_confirmed=loss[2],loss_recredited=loss[3],lag_confirmed=lag[2],lag_final=lag[3]))
report=dict(ok=True,cases=len(cases),identical_observed_prefixes=len(cases),fresh_hud_correct=True,persistent_loss_recredit_cases=sum(c['loss_recredited']!=c['loss_confirmed'] for c in cases),source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),conclusion='Same observed notices/HUD prefix can mean loss or HUDlag. Clearing all unmatched pending immediately would lose valid lagging gains; current fallback overstates hiddenloss until next authoritative HUD. Fresh HUD reads correct both totals, but unchanged subsequent HUD reads do NOT retire old unmatched pending; after another outage loss is recredited again. Repeated stable HUD evidence offers a bounded finalization policy to test next. Do not claim ambiguity solved.',scope='Offline alternate-ground-truth simulations; no livegame/OCR',examples=cases[:3])
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='examples'}))
