from pathlib import Path
import sys,json,types,hashlib
from unittest.mock import patch
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
import training_ui
from training_accounting import TrainingAccountant
from session_rewards import session_token
s=dict(id='fixture',running_since=1,auto_rewards=True,exp=0,mesos=0,kills=0);account=TrainingAccountant();token=session_token(s)
a=types.SimpleNamespace(state=dict(training_auto_context=False,training_target='23',party=2,character_exp={'level':27,'exp':1000}),db=types.SimpleNamespace(monsters={23:dict(id=23,exp=50)},map_data={}))
for name in ('training_target','training_plausible_targets','training_gain_context','training_party_total','training_observe_yield','training_buffer_yield'):
 setattr(a,name,types.MethodType(getattr(training_ui,name),a))
clock=[0.]
def poll(events,reading,now):
 clock[0]=now;previous=account.character;account.feed(s,token,list(events),reading,now)
 if reading is not None and account.character is reading:
  a.state['character_exp']=reading;a.training_buffer_yield(account.last_delta,previous,reading)
 else:a.training_buffer_yield(account.last_delta)
with patch('time.monotonic',side_effect=lambda:clock[0]):
 poll([],{'level':27,'exp':1000},0);poll([],{'level':27,'exp':1000},.1);events=[]
 for index in range(1,4):
  events.extend([('exp',7),('bonus',2)])
  poll(events,{'level':30,'exp':100},index)
  assert account.character['level']==27 and s['exp']==(index-1)*9
  poll(events,{'level':27,'exp':1000+index*9},index+.2)
  assert s['exp']==index*9
 assert a._yield_learner.estimate(a.training_gain_context(),3.3)==9
 assert s['exp']==27 and s['party_exp']==6
report=dict(ok=True,rejected_hud_reads=3,learned_gain=9,session_exp=s['exp'],party_exp=s['party_exp'],source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='Synthetic accountant-to-production-yield callback flow with rejected+3leveloutliers; no actualimageOCR/UI/gamecapture')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
