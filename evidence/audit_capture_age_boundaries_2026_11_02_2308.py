from pathlib import Path
import sys,types,json
from unittest.mock import patch
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
import companion_tools as tools,training_ui
from session_reader import RewardRead
class Root:
 def winfo_children(self):return []
 def winfo_viewable(self):return True
 def after(self,*args):pass
cases=0
for delay in (0,.2,14.999,15.001,30,120):
 for seed in range(50):
  clock=[100.+seed];pending=[]
  s=dict(id='audit',running_since=1.,auto_rewards=True,exp=0,mesos=0,kills=0,party_exp=0)
  a=types.SimpleNamespace(state={'utility_session':s,'character_exp':{'level':27,'exp':1000}},root=Root(),signature=['old','mapA',2,27],save_state=lambda:None,render_levelup=lambda:None)
  a.training_gain_context=lambda:list(a.signature)
  a.training_accept_character=lambda reading:a.state.update(character_exp=dict(reading))
  a.training_buffer_yield=types.MethodType(training_ui.training_buffer_yield,a)
  a.training_observe_yield=types.MethodType(training_ui.training_observe_yield,a)
  a.run_bg=lambda job,loaded,on_error:pending.append(loaded)
  a.utility_poll_rewards=lambda:tools.utility_poll_rewards(a)
  def dispatch():
   clock[0]+=.2;tools.utility_poll_rewards(a);return pending.pop()
  with patch.object(tools,'window_rect',return_value=(0,0,1,1)),patch.object(tools.time,'monotonic',side_effect=lambda:clock[0]):
   for _ in range(2):dispatch()({'events':RewardRead([],False),'character':{'level':27,'exp':1000}})
   callback=dispatch();clock[0]+=delay
   callback({'events':RewardRead([('exp',7),('bonus',2)],False),'character':{'level':27,'exp':1009}})
   if delay>15:
    assert a._yield_learner.samples==[],(seed,delay,a._yield_learner.samples)
    assert (s['exp'],s['party_exp'],s['kills'])==(0,0,0)
    assert not hasattr(a,'_training_party_seen_at')
   else:
    assert a._yield_learner.samples==[9]
    assert (s['exp'],s['party_exp'],s['kills'])==(9,2,1)
    assert hasattr(a,'_training_party_seen_at')
   events=[('exp',7),('bonus',2)]
   dispatch()({'events':RewardRead(events,False),'character':{'level':27,'exp':1009}})
   assert (s['exp'],s['party_exp'],s['kills'])==(9,2,1)
  cases+=1
import hashlib
report=dict(ok=True,cases=cases,scope='Callback age boundary0/.2/14.999seconds accepted,15.001/30/120seconds discarded before fresh evidence/totals/calibration; next timely capture recovers rewards once; offline only',source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest())
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
