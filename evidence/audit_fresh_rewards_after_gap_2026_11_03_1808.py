from pathlib import Path
import sys,types,json,hashlib
from unittest.mock import patch
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
import companion_tools as tools
from session_reader import RewardRead
class Root:
 def winfo_children(self):return []
 def winfo_viewable(self):return False
 def after(self,*args):pass
cases=0
for seed in range(250):
 for gapmode in ('error','unavailable'):
  clock=[100.];pending=[]
  s=dict(id=str(seed),running_since=1,auto_rewards=True,exp=0,mesos=0,kills=0,party_exp=0)
  a=types.SimpleNamespace(root=Root(),state={'utility_session':s,'character_exp':{'level':27,'exp':1000}},save_state=lambda:None,render_levelup=lambda:None,run_bg=lambda job,loaded,on_error:pending.append((loaded,on_error)))
  a.training_accept_character=lambda r:a.state.update(character_exp=dict(r))
  a.training_gain_context=lambda:['','a',None,27]
  a.training_buffer_yield=lambda *args:False
  a.utility_poll_rewards=lambda:tools.utility_poll_rewards(a)
  events=RewardRead([('exp',7),('bonus',2),('mesos',17)],False)
  with patch('time.monotonic',side_effect=lambda:clock[0]):
   def dispatch():
    clock[0]+=.2;tools.utility_poll_rewards(a);assert len(pending)==1 and a._reward_busy
    return pending.pop()
   for _ in range(2):dispatch()[0]({'events':RewardRead([],False),'character':{'level':27,'exp':1000}})
   dispatch()[0]({'events':events,'character':{'level':27,'exp':1009}})
   assert (s['exp'],s['party_exp'],s['kills'],s['mesos'])==(9,2,1,0)
   clock[0]+=(.1,1.,4.)[seed%3]
   loaded,failed=dispatch()
   if gapmode=='error':failed(RuntimeError('Synthetic capture failure'))
   else:loaded({'events':None,'character':None})
   assert not a._reward_busy
   for _ in range(4):dispatch()[0]({'events':events,'character':{'level':27,'exp':1009}})
   assert (s['exp'],s['party_exp'],s['kills'])==(9,2,1)
   assert s['mesos']==(17 if gapmode=='error' else 0),(seed,gapmode,s)
   fresh_base,fresh_bonus,fresh_money=(7,2,17) if seed%2 else (13,3,31)
   stack=list(events)
   count=seed%4+1
   for i in range(count):
    stack += [('exp',fresh_base),('bonus',fresh_bonus),('mesos',fresh_money)]
    visible=RewardRead(stack,False)
    for _ in range(2):dispatch()[0]({'events':visible,'character':{'level':27,'exp':1009+(i+1)*(fresh_base+fresh_bonus)}})
   for _ in range(4):dispatch()[0]({'events':visible,'character':{'level':27,'exp':1009+count*(fresh_base+fresh_bonus)}})
   assert s['exp']==9+count*(fresh_base+fresh_bonus)
   assert s['party_exp']==2+count*fresh_bonus and s['kills']==1+count
   assert s['mesos']==(17 if gapmode=='error' else 0)+count*fresh_money,(seed,gapmode,s)
   assert not a._reward_busy and not pending
  cases+=1
report=dict(ok=True,cases=cases,capture_error_cases=250,unavailable_gap_cases=250,fresh_pickups_per_case=[1,4],fresh_amount_modes=["identical","different"],no_new_reward_omitted=True,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='Actual reward polling/callback/accountant, syntheticold notices around shorterror/unavailablegap then1..4freshappendedpickups, repeatedreadconfirmation. Missing-gap oldmoney conservatively uncounted baseline; no actual capture/OCR/game.')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
