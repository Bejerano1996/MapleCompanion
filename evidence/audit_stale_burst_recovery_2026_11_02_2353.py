from pathlib import Path
import sys,types,json,hashlib,random
from unittest.mock import patch
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
import companion_tools as tools
from session_reader import RewardRead
class Root:
 def winfo_children(self):return []
 def winfo_viewable(self):return True
 def after(self,*args):pass
rejected=0
for seed in range(500):
 r=random.Random(seed);clock=[100.];pending=[]
 s=dict(id='audit',running_since=1,auto_rewards=True,exp=0,mesos=0,kills=0,party_exp=0)
 a=types.SimpleNamespace(state={'utility_session':s},root=Root(),save_state=lambda:None,training_gain_context=lambda:['mob','map',2,27],training_buffer_yield=lambda *args:False,training_accept_character=lambda *args:None,render_levelup=lambda:None)
 a.run_bg=lambda job,loaded,on_error:pending.append(loaded);a.utility_poll_rewards=lambda:tools.utility_poll_rewards(a)
 def dispatch():
  clock[0]+=.2;a.utility_poll_rewards();return pending.pop()
 with patch.object(tools,'window_rect',return_value=(0,0,1,1)),patch.object(tools.time,'monotonic',side_effect=lambda:clock[0]):
  for _ in range(2):dispatch()(dict(events=RewardRead([],False),character=dict(level=27,exp=1000)))
  old=[('exp',7),('bonus',2),('mesos',17)];new=old+[('exp',11),('bonus',3),('mesos',23)]
  dispatch()(dict(events=RewardRead(old,False,[2]),character=dict(level=27,exp=1009)))
  assert (s['exp'],s['mesos'],s['kills'],s['party_exp'])==(9,17,1,2)
  for _ in range(r.randint(1,6)):
   cb=dispatch();clock[0]+=r.uniform(15.01,120)
   cb(dict(events=RewardRead(new,False,[2,5]),character=dict(level=27,exp=1023)))
   assert (s['exp'],s['mesos'],s['kills'],s['party_exp'])==(9,17,1,2)
   assert not a._reward_busy;rejected+=1
  for _ in range(3):dispatch()(dict(events=RewardRead(new,False,[2,5]),character=dict(level=27,exp=1023)))
  assert (s['exp'],s['mesos'],s['kills'],s['party_exp'])==(23,40,2,5),(seed,s)
report=dict(ok=True,cases=500,rejected_callbacks=rejected,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='Synthetic actual callbacks:1–6consecutive stale results preserve accounted rewards, timely same visible stack recovers new rewards once, repeated reads stay stable; no OCR/livegame')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
