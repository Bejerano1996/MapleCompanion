from pathlib import Path
import sys,types,copy,json,hashlib
from unittest.mock import patch
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
import training_context
class Root:
 def winfo_children(self):return []
 def winfo_viewable(self):return False
cases=0;failures=0
for seed in range(500):
 clock=[100.];pending=[];moves=[];renders=[]
 a=types.SimpleNamespace(root=Root(),state=dict(utility_session=dict(id=str(seed),running_since=1,auto_rewards=True,exp=42,kills=7,party_exp=11),training_auto_context=True,map='current'),db=types.SimpleNamespace(maps={'a':{},'b':{}},monsters={23:{'name':'A'},24:{'name':'B'}}),run_bg=lambda work,loaded,on_error:pending.append((loaded,on_error)),set_location=lambda m:moves.append(m),render_levelup=lambda:renders.append(1))
 with patch('time.time',side_effect=lambda:clock[0]),patch('time.monotonic',side_effect=lambda:clock[0]):
  def dispatch():
   clock[0]+=9.;training_context.context_poll(a);assert len(pending)==1 and a._context_busy
   return pending.pop()
  for _ in range(2):dispatch()[0](dict(game=True,map='a',mobs=[23],party_visible=2,captured_at=clock[0]))
  before=copy.deepcopy(a._training_context);state=copy.deepcopy(a.state)
  for _ in range(seed%5+1):
   loaded,failed=dispatch();failed(RuntimeError('Synthetic OCR failure '+('x'*200)))
   assert not a._context_busy and len(a._context_error)<=100
   assert a.state==state and a._training_context==before
   failures+=1
  clock[0]+=21.;assert training_context.context_summary(a)=='Game context unavailable · last session totals retained'
  for _ in range(2):dispatch()[0](dict(game=True,map='b',mobs=[24],party_visible=3,captured_at=clock[0]))
  assert a._training_context['map']=='b' and a._training_context['party_visible']==3
  assert moves==['a','b'] and len(renders)==4 and not a._context_busy
  assert a.state['utility_session']['exp']==42 and a.state['utility_session']['kills']==7 and a.state['utility_session']['party_exp']==11
 cases+=1
report=dict(ok=True,cases=cases,failed_callbacks=failures,fresh_context_confirmed=True,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='Actual context_poll error/success callback paths with synthetic failures/time/context; no actual OCR/capture/threads/game')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
