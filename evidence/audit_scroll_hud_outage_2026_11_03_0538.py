from pathlib import Path
import sys,json,random,hashlib,statistics,types
from unittest.mock import patch
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
from session_rewards import RewardTracker,session_token
from training_accounting import TrainingAccountant
import training_ui
from session_reader import RewardRead
b=Path(__file__).resolve().parent;old=json.loads((b/'audit_frozen_static_ocr_3_24.json').read_text());bright=json.loads((b/'audit_frozen_money_brightness_3_24.json').read_text());sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest();assert old['source_sha']==bright['source_sha']==sha
cases=0;polls=0;under=[];over=[]
for name in old['captures']:
 pool=old['captures'][name]+bright['captures'][name]
 for seed in range(250):
  r=random.Random(seed);accountant=TrainingAccountant();session=dict(id='audit',running_since=1,auto_rewards=True,exp=0,mesos=0,kills=0,party_exp=0);token=session_token(session)
  app=types.SimpleNamespace(state={'character_exp':{'level':27,'exp':1000}},training_gain_context=lambda:['mob','map',2,27])
  app.training_buffer_yield=types.MethodType(training_ui.training_buffer_yield,app);app.training_observe_yield=types.MethodType(training_ui.training_observe_yield,app)
  totals=dict(exp=0,kills=0,party_exp=0,mesos=0)
  for frame in range(60):
   c=r.choice(pool);events=list(c['events']);positions=list(c['positions']);trusted=list(c['trusted_money'])
   if frame>=10:
    last=positions[-1][0];positions += [(last+60,45),(last+120,45),(last+180,45)]
    amount=None if frame<56 and r.random()<.35 else 17
    events += [('exp',13),('bonus',3),('mesos',amount)]
   if frame>=10:
    gaps=[b[0]-a[0] for a,b in zip(c['positions'],c['positions'][1:])];gap=statistics.median(gaps)
    # Synthetic append scrolls three rows; preserve actual old OCR coordinates.
    last=c['positions'][-1][0];positions=list(c['positions'])+[(last+gap*(j+1),45) for j in range(3)]
    entries=[(event,(p[0]-3*gap,p[1])) for event,p in zip(events,positions) if p[0]-3*gap>=0]
    events=[e for e,p in entries];positions=[p for e,p in entries];trusted=[]
   reading=RewardRead(events,False,trusted,positions);previous=accountant.character
   hud=None if 10<=frame<55 else dict(level=27,exp=1000 if frame<10 else 1016)
   accountant.feed(session,token,reading,hud,frame*.5);delta=accountant.last_delta;polls+=1
   with patch('time.monotonic',return_value=frame*.5):
    if hud is not None and accountant.character is hud:
     app.state['character_exp']=dict(hud);app.training_buffer_yield(delta,previous,hud)
    else:app.training_buffer_yield(delta)
   if frame<10:assert session['exp']==0
   elif frame>=55:assert session['exp']==16,(name,seed,frame,session)
   elif frame*.5-accountant.ledger.last_at>15:
    assert session['exp_source']=='Reward log · partial'
    assert 0<=session['exp']<=16
   assert app._yield_learner.samples in ([],[16]),(name,seed,frame,app._yield_learner.samples)
   for key in totals:totals[key]+=delta[key]
   if frame<10:assert not any(totals.values()),(name,seed,frame,totals)
   if any(totals[k]>v for k,v in dict(exp=16,kills=1,party_exp=3,mesos=17).items()):over.append(dict(fixture=name,seed=seed,frame=frame,totals=dict(totals)));break
  if totals!=dict(exp=16,kills=1,party_exp=3,mesos=17):under.append(dict(fixture=name,seed=seed,totals=totals))
  cases+=1
report=dict(ok=not over,cases=cases,hud_recovery_exact_cases=cases,partial_yield_samples=0,polls=polls,overcounts=over,under_or_inexact=under,source_sha=sha,scope='Actual cachedoldOCR + syntheticnewscroll; HUDoutage22.5seconds, partialfallbacklabel/bounds, laterHUD16exact and no partialyieldlearning; no livegame')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(dict(ok=report['ok'],cases=cases,polls=polls,overcounts=len(over),under_or_inexact=len(under),examples=over[:2]+under[:2])))
