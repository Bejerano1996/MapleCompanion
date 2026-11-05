from pathlib import Path
import sys,types,copy,json,hashlib
from unittest.mock import patch
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
import training_context
class Root:
 def winfo_children(self):return []
 def winfo_viewable(self):return False
cases=0
for seed in range(100):
 for mode in ('pause','resume','replace','rewards_off','context_off'):
  clock=[100.];pending=[];moves=[];renders=[]
  session=dict(id='old',running_since=1,auto_rewards=True,exp=42)
  a=types.SimpleNamespace(root=Root(),state=dict(utility_session=session,training_auto_context=True,map='current'),db=types.SimpleNamespace(maps={'a':{},'b':{}},monsters={}),run_bg=lambda work,loaded,on_error:pending.append(loaded),set_location=lambda m:moves.append(m),render_levelup=lambda:renders.append(1))
  with patch('time.time',side_effect=lambda:clock[0]),patch('time.monotonic',side_effect=lambda:clock[0]):
   training_context.context_poll(a);assert a._context_busy and len(pending)==1
   before=copy.deepcopy(a._training_context)
   if mode=='pause':session['running_since']=None
   elif mode=='resume':session['running_since']=2
   elif mode=='replace':a.state['utility_session']=dict(id='new',running_since=1,auto_rewards=True,exp=0)
   elif mode=='rewards_off':session['auto_rewards']=False
   else:a.state['training_auto_context']=False
   state=copy.deepcopy(a.state)
   pending.pop()(dict(game=True,map='a',mobs=[23],party_visible=2,captured_at=100.))
   assert not a._context_busy and a._training_context==before
   assert a.state==state and not moves and not renders
   a.state['utility_session']=dict(id='fresh',running_since=3,auto_rewards=True,exp=0);a.state['training_auto_context']=True
   for _ in range(2):
    clock[0]+=9;training_context.context_poll(a);assert len(pending)==1
    pending.pop()(dict(game=True,map='b',mobs=[24],party_visible=3,captured_at=clock[0]))
   assert a._training_context['map']=='b' and a._training_context['party_visible']==3
   assert a.state['utility_session']['observed_monsters'].keys()=={'24'}
   assert moves==['b'] and len(renders)==2 and not a._context_busy
  cases+=1
report=dict(ok=True,cases=cases,late_modes=['pause','resume','replace','rewards_off','context_off'],fresh_reader_recovered=True,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='Actual context_poll held callbacks; synthetic sessions/context, no actual worker/capture/OCR/game')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
