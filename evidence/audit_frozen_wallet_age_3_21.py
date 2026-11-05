from pathlib import Path
import sys,types,json,hashlib,random
from unittest.mock import patch
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
import companion_tools as tools
from session_rewards import session_token
from session_reader import RewardRead
class Root:
 def __init__(self):self.scheduled=[]
 def winfo_children(self):return []
 def winfo_viewable(self):return True
 def after(self,*args):self.scheduled.append(args)
for seed in range(200):
 r=random.Random(seed);clock=[100.];pending=[];saved=[]
 s=dict(id='wallet-audit',running_since=1.,auto_rewards=True,wallet_auto=True,money_mode='wallet',wallet_start=1000,wallet_current=1000,wallet_net=0,wallet_offset=0,exp=0,mesos=0,kills=0,party_exp=0)
 a=types.SimpleNamespace(state={'utility_session':s},root=Root(),save_state=lambda:saved.append(True),training_gain_context=lambda:['mob','map',2,27],training_buffer_yield=lambda *args:False,training_accept_character=lambda *args:None,render_levelup=lambda:None)
 a._wallet_scope=session_token(s);a.run_bg=lambda job,loaded,on_error:pending.append((loaded,on_error));a.utility_poll_rewards=lambda:tools.utility_poll_rewards(a)
 def dispatch():
  clock[0]+=.2;a._wallet_last_poll=0;a.utility_poll_rewards();return pending.pop()
 with patch.object(tools,'window_rect',return_value=(0,0,1,1)),patch.object(tools.time,'monotonic',side_effect=lambda:clock[0]):
  loaded,failed=dispatch();before=dict(s);clock[0]+=r.uniform(16,120)
  loaded(dict(events=RewardRead([('bonus',99),('mesos',9999)],False),wallet=9999))
  assert a.state['utility_session']==before and not saved
  assert not a._reward_busy and a.root.scheduled
  assert not hasattr(a,'_training_party_seen_at')
  loaded,failed=dispatch();loaded(dict(events=RewardRead([],False),wallet=1020))
  assert a.state['utility_session']['mesos']==20 and not a._reward_busy
  loaded,failed=dispatch();clock[0]+=r.uniform(.1,30);failed(RuntimeError('simulated read failure'))
  assert not a._reward_busy
  loaded,failed=dispatch();loaded(dict(events=RewardRead([],False),wallet=1030))
  assert a.state['utility_session']['mesos']==30 and not a._reward_busy
report=dict(ok=True,cases=200,scope='Delayed optional wallet result ignored without save; timely checkpoint recovers, random reader failure clears busy and later polling succeeds. Synthetic callbacks only, no wallet/game reads',source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest())
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
