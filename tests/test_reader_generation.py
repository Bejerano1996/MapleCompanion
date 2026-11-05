from pathlib import Path
import sys,types,json
from unittest.mock import patch
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
import companion_tools as tools,training_ui
from session_reader import RewardRead
class Root:
 def winfo_children(self):return []
 def winfo_viewable(self):return True
 def after(self,*args):pass
import unittest
class ReaderGenerationTests(unittest.TestCase):
 def test_superseded_callback_after_mode_roundtrip(self):
  cases=0
  for mode in ("auto_roundtrip","notice_reset"):
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
     callback=dispatch()
     if mode=="auto_roundtrip":
      s["auto_rewards"]=False;a.utility_poll_rewards();s["auto_rewards"]=True
     a._reward_token=None;a.utility_poll_rewards()
     callback({'events':RewardRead([('exp',7),('bonus',2)],False),'character':{'level':27,'exp':1009}})
     assert (s['exp'],s['party_exp'],s['kills'])==(0,0,0),(mode,s)
     assert not hasattr(a,'_training_party_seen_at')
     dispatch()({'events':RewardRead([('exp',7),('bonus',2)],False),'character':{'level':27,'exp':1009}})
     assert s['exp']==0
    cases+=1

if __name__=='__main__':unittest.main()
