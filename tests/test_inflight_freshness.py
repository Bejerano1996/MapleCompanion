from pathlib import Path
import sys,types,json,hashlib
from unittest.mock import patch
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
import companion_tools as tools,training_ui,leveling
from session_reader import RewardRead
class Root:
 def winfo_children(self):return []
 def winfo_viewable(self):return True
 def after(self,*args):pass
import unittest
class InflightFreshnessTests(unittest.TestCase):
 def test_expiring_context_and_level_crossing(self):
  cases=0
  for change in ('map_at','mobs_at','party_at','map','level'):
   for seed in range(40):
    clock=[100.+seed];pending=[];base=leveling.exp_to_next(27)-5 if change=='level' else 1000
    s=dict(id='audit',running_since=1.,auto_rewards=True,exp=0,mesos=0,kills=0,party_exp=0)
    a=types.SimpleNamespace(state={'utility_session':s,'character_exp':{'level':27,'exp':base},'training_auto_context':True},root=Root(),save_state=lambda:None,render_levelup=lambda:None,db=types.SimpleNamespace(monsters={23:dict(id=23,name='probe',exp=50)},map_data={'a':{'monsters':[{'id':'23'}]},'b':{'monsters':[{'id':'23'}]}}))
    a._training_context=dict(map='a',map_readable=True,map_at=clock[0],mobs=[23],mobs_at=clock[0],party_readable=True,party_visible=2,party_at=clock[0])
    for name in ('training_target','training_plausible_targets','training_gain_context','training_party_total','training_buffer_yield','training_observe_yield'):
     setattr(a,name,types.MethodType(getattr(training_ui,name),a))
    a.training_accept_character=lambda reading:a.state.update(character_exp=dict(reading))
    a.run_bg=lambda job,loaded,on_error:pending.append(loaded)
    a.utility_poll_rewards=lambda:tools.utility_poll_rewards(a)
    def dispatch():
     clock[0]+=.2;tools.utility_poll_rewards(a);return pending.pop()
    with patch.object(tools,'window_rect',return_value=(0,0,1,1)),patch('time.monotonic',side_effect=lambda:clock[0]),patch('time.time',side_effect=lambda:clock[0]):
     for _ in range(2):dispatch()({'events':RewardRead([],False),'character':{'level':27,'exp':base}})
     callback=dispatch()
     if change.endswith('_at'):a._training_context[change]=clock[0]-20.001
     elif change=='map':a._training_context['map']='b'
     reading={'level':28,'exp':4} if change=='level' else {'level':27,'exp':base+9}
     events=[('exp',7),('bonus',2)]
     callback({'events':RewardRead(events,False),'character':reading})
     assert a._yield_learner.samples==[],(change,seed,a._yield_learner.samples)
     assert (s['exp'],s['party_exp'])==(9,2),(change,s)
     for field in ('map_at','mobs_at','party_at'):a._training_context[field]=clock[0]
     for index in range(1,4):
      events += [('exp',7),('bonus',2)]
      dispatch()({'events':RewardRead(events,False),'character':dict(level=reading['level'],exp=reading['exp']+9*index)})
     assert a._yield_learner.estimate(a.training_gain_context(),clock[0])==9,(change,seed)
     assert (s['exp'],s['party_exp'],s['kills'])==(36,8,4),(change,s)
    cases+=1

if __name__=='__main__':unittest.main()
