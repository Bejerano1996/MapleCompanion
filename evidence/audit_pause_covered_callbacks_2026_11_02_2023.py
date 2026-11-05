from pathlib import Path
import sys,json,types,random,hashlib
from unittest.mock import patch
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
import companion_tools as tools
from session_reader import RewardRead
from session_rewards import session_token
class Root:
 def winfo_children(self):return []
 def winfo_viewable(self):return True
 def after(self,*args):pass
results=[]
for seed in range(200):
 rng=random.Random(seed);clock=[100.];pending=[]
 s=dict(id='audit',running_since=1.,auto_rewards=True,exp=0,mesos=0,kills=0,party_exp=0)
 app=types.SimpleNamespace(state={'utility_session':s},root=Root(),save_state=lambda:None,render_levelup=lambda:None,training_buffer_yield=lambda *a:False,training_accept_character=lambda *a:None)
 app.run_bg=lambda job,loaded,on_error:pending.append(loaded)
 app.utility_poll_rewards=lambda:tools.utility_poll_rewards(app)
 with patch.object(tools,'window_rect',return_value=(0,0,1,1)),patch.object(tools.time,'monotonic',side_effect=lambda:clock[0]):
  app.utility_poll_rewards();stale=pending.pop()
  s['running_since']=None;app.utility_poll_rewards()
  # Resume while the old worker is still pending. Its callback must be ignored.
  s['running_since']=2.;clock[0]+=.2;app.utility_poll_rewards()
  stale({'events':RewardRead([('exp',777),('bonus',222),('mesos',999)],False,[2])})
  assert all(s[k]==0 for k in ('exp','mesos','kills','party_exp'))
  assert not hasattr(app,'_training_party_seen_at')
  clock[0]+=.2;app.utility_poll_rewards();fresh=pending.pop()
  old=[('exp',7),('bonus',2),('mesos',30)]
  pos=[(20*i,12) for i in range(3)]
  fresh({'events':RewardRead(old,False,(),pos)})
  assert s['mesos']==0 and s['exp']==0
  for _ in range(rng.randint(1,8)):
   clock[0]+=.2;app.utility_poll_rewards();pending.pop()({'events':RewardRead(old[:2],True,(),pos[:2])})
  for _ in range(2):
   clock[0]+=.2;app.utility_poll_rewards();pending.pop()({'events':RewardRead(old,False,(),pos)})
  assert s['mesos']==0 and s['exp']==0
  amount=rng.randint(31,1000);new=old+[('exp',11),('bonus',3),('mesos',amount)]
  for _ in range(3):
   clock[0]+=.2;app.utility_poll_rewards();pending.pop()({'events':RewardRead(new,False,(),[(20*i,12) for i in range(6)])})
  assert (s['exp'],s['party_exp'],s['kills'],s['mesos'])==(14,3,1,amount),s
  results.append(seed)
report=dict(ok=True,cases=len(results),scope='Production utility_poll_rewards callbacks with simulated delayed workers, pause/resume, partial cover and new pickup; no game capture',source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest())
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
