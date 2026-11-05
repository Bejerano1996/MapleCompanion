from pathlib import Path
import sys,json,random,hashlib
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
from training_accounting import TrainingAccountant
from session_rewards import session_token
base=Path(__file__).resolve().parent;full=json.loads((base/'audit_hud_brightness_translation_2026_11_03_1008.json').read_text());partial=json.loads((base/'audit_hud_missing_component_2026_11_03_1038.json').read_text())
sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest();assert full['source_sha']==partial['source_sha']==sha
first=next(c['reading'] for c in full['cases'] if c['fixture']=='live_frame_ant_tunnel2.png');later=next(c['reading'] for c in full['cases'] if c['fixture']=='live_frame_1920.png');missing=[c['reading'] for c in partial['cases'] if c['concordant_channel_missing']];assert len(missing)==11 and all(x is None for x in missing)
for seed in range(500):
 rng=random.Random(seed);session=dict(id='audit',running_since=1,auto_rewards=True,exp=0,kills=0,party_exp=0,mesos=0);a=TrainingAccountant();token=session_token(session)
 a.feed(session,token,[],dict(first),0);a.feed(session,token,[],dict(first),.1)
 anchor=a.ledger.anchor;last_at=a.ledger.last_at;character=a.character;now=16.
 for _ in range(40):
  now+=rng.uniform(.1,2);a.feed(session,token,[],rng.choice(missing),now)
  assert a.ledger.anchor==anchor and a.ledger.last_at==last_at and a.character is character
  assert session['exp']==0 and session['exp_source'].endswith('partial')
 a.feed(session,token,[],dict(later),now+1)
 assert session['exp']==41 and a.ledger.last_at==now+1
 for i in range(10):a.feed(session,token,[],dict(later) if i%2 else None,now+2+i)
 assert session['exp']==41
report=dict(ok=True,cases=500,missing_hud_polls=20000,actual_rejected_variants=len(missing),net_exp_recovery=41,source_sha=sha,scope='Cached actualHUDOCR5299->5340 and11actualsinglecomponentrejections sequenced through productionaccountant; syntheticorder/timing,no livegame')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
