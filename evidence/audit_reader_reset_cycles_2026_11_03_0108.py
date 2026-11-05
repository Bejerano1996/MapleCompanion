from pathlib import Path
import sys,types,json,hashlib,weakref,gc,random
from unittest.mock import patch
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
import companion_tools as tools
from session_reader import RewardRead
class Root:
 def winfo_children(self):return []
 def winfo_viewable(self):return True
 def after(self,*args):pass
clock=[100.];pending=[];retired=[];rng=random.Random(108)
s=dict(id='audit',running_since=1,auto_rewards=True,exp=0,mesos=0,kills=0,party_exp=0)
a=types.SimpleNamespace(state={'utility_session':s},root=Root(),save_state=lambda:None,training_gain_context=lambda:['mob','map',2,27],training_buffer_yield=lambda *args:False,training_accept_character=lambda *args:None,render_levelup=lambda:None)
a.run_bg=lambda job,loaded,on_error:pending.append(loaded);a.utility_poll_rewards=lambda:tools.utility_poll_rewards(a)
def dispatch():
 clock[0]+=.2;a.utility_poll_rewards();return pending.pop()
with patch.object(tools,'window_rect',return_value=(0,0,1,1)),patch.object(tools.time,'monotonic',side_effect=lambda:clock[0]):
 for i in range(1000):
  cb=dispatch();retired.append(weakref.ref(a._training_accountant));before=dict(s)
  for _ in range(rng.randint(1,5)):
   s['auto_rewards']=False;a.utility_poll_rewards();s['auto_rewards']=True;a._reward_token=None;a.utility_poll_rewards()
  cb(dict(events=RewardRead([('exp',777),('bonus',222),('mesos',999)],False,[2]),character=dict(level=27,exp=50000)));del cb
  assert s==before,(i,'old result',s,before)
  for _ in range(2):dispatch()(dict(events=RewardRead([],False),character=dict(level=27,exp=1000+9*i)))
  rows=[('exp',7),('bonus',2),('mesos',17)]
  for _ in range(2):dispatch()(dict(events=RewardRead(rows,False,[2]),character=dict(level=27,exp=1000+9*(i+1))))
  assert (s['exp'],s['mesos'],s['kills'],s['party_exp'])==(9*(i+1),17*(i+1),i+1,2*(i+1)),(i,s)
  assert not pending and not a._reward_busy
 gc.collect();live=sum(ref() is not None for ref in retired);assert live==0,live
report=dict(ok=True,cycles=1000,retired_accountants_alive=live,final_totals={k:s[k] for k in ('exp','mesos','kills','party_exp')},source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='One synthetic app over1000readerresets,1–5rapidmodechanges each, staleclosureignored,newbaseline/freshreward countedonce; weakreferences confirm retired accountants collectible; no nativeOCR/game')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
