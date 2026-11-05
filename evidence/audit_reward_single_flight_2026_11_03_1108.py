from pathlib import Path
import sys,json,types,random,hashlib
from unittest.mock import patch
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
import companion_tools as tools
from session_reader import RewardRead
class Root:
 def winfo_children(self):return []
 def winfo_viewable(self):return True
 def after(self,*args):pass
rng=random.Random(1108);pending=[];clock=[100.];launches=[0];blocked=0;resets=0
session=dict(id='audit',running_since=1,auto_rewards=True,exp=0,kills=0,mesos=0,party_exp=0)
app=types.SimpleNamespace(root=Root(),state={'utility_session':session},save_state=lambda:None,render_levelup=lambda:None,training_gain_context=lambda:['mob','map',2,27],training_buffer_yield=lambda *args:False,training_accept_character=lambda *args:None)
def run(job,loaded,on_error):launches[0]+=1;pending.append(loaded)
app.run_bg=run;app.utility_poll_rewards=lambda:tools.utility_poll_rewards(app)
with patch.object(tools,'window_rect',return_value=(0,0,1,1)),patch('time.monotonic',side_effect=lambda:clock[0]):
 for cycle in range(500):
  clock[0]+=.2;app.utility_poll_rewards();assert len(pending)==1
  launched=launches[0]
  for i in range(rng.randint(20,50)):
   clock[0]+=rng.uniform(.001,.01)
   if i==10 and cycle%7==0:app._reward_token=None;resets+=1
   app.utility_poll_rewards();blocked+=1
   assert len(pending)==1 and launches[0]==launched
  callback=pending.pop();callback(dict(events=RewardRead([],False),character=dict(level=27,exp=1000+cycle)))
  assert not app._reward_busy and not pending
report=dict(ok=True,completed_captures=launches[0],blocked_poll_requests=blocked,generation_resets_while_busy=resets,max_pending_captures=1,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='Productionpollscheduler with heldcallback and20–50rapidpolls perread, optionalreaderreset; single-flight prevents overlapping rewardcaptures. Mockedasyncdelivery,not actualthreads/OCR/livegame')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
