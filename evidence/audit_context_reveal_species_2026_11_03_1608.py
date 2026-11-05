from pathlib import Path
import sys,types,json,hashlib,random
from unittest.mock import patch
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
import training_context,training_ui
rng=random.Random(1608);cases=0
for seed in range(500):
 clock=[100.];tracker=training_context.ContextTracker()
 a=types.SimpleNamespace(state=dict(training_auto_context=True,training_target='23',map='a',party=6,character_exp={'level':27,'exp':1000},character_exp_at=100.),db=types.SimpleNamespace(monsters={23:dict(id=23,name='A',exp=13),24:dict(id=24,name='B',exp=50)},map_data={'a':{'monsters':[{'id':23}]},'b':{'monsters':[{'id':24}]}}))
 for name in ('training_target','training_plausible_targets','training_gain_context','training_party_total','training_forecast_now'):setattr(a,name,types.MethodType(getattr(training_ui,name),a))
 def feed(map_id,mobs):
  a._training_context=tracker.feed(dict(game=True,map=map_id,mobs=mobs,party_visible=2),clock[0]);clock[0]+=.1
 with patch('time.time',side_effect=lambda:clock[0]):
  feed('a',[23]);feed('a',[23]);assert a.training_target()['id']==23
  clock[0]+=rng.uniform(.1,30);feed(None,[23]);assert a.training_target() is None
  feed('b',[23]);assert a.training_target() is None
  feed('b',[23]);assert a.training_target() is None and not a.training_forecast_now()['available']
  feed('b',[24]);assert a.training_target()['id']==24 and a.training_forecast_now()['available']
  # A current map timestamp must not rescue species older than20seconds.
  clock[0]+=20.001;a._training_context['map_at']=clock[0];a._training_context['party_at']=clock[0]
  assert a.training_target() is None
  assert not a.training_forecast_now()['available']
 cases+=1
report=dict(ok=True,cases=cases,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='Production ContextTracker + target/forecast, synthetic hide/reveal/map-change/species-freshness sequences; not real monster kills or OCR/livegame')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
