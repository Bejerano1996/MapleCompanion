from pathlib import Path
import sys,json,random,math,hashlib
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
from companion_feature_model import utility_session_new,utility_session_toggle,utility_session_elapsed,utility_session_rates
from wallet_model import checkpoint
r=random.Random(123);checks=0
for seed in range(500):
 now=0.;s=utility_session_toggle(utility_session_new(now),now)
 now+=r.uniform(1,500);prefix=now
 # Automatic wallet's first verified reading starts its active measurement epoch.
 s.update(wallet_auto=True,money_mode='wallet',wallet_start=10000,wallet_offset=0,wallet_elapsed_anchor=utility_session_elapsed(s,now))
 wallet_seconds=0.;net=0
 for segment in range(3):
  active=r.uniform(1,300);now+=active;wallet_seconds+=active;gain=r.randint(-100,500);net+=gain
  s=checkpoint(s,10000+net,10000)
  rates=utility_session_rates(s,now)
  assert math.isclose(rates['net_hour'],net*3600/wallet_seconds,rel_tol=1e-9)
  s=utility_session_toggle(s,now);now+=r.uniform(1,10000)
  assert math.isclose(utility_session_rates(s,now)['net_hour'],rates['net_hour'],rel_tol=1e-9)
  s=utility_session_toggle(s,now);checks+=1
 # UI pickup-mode switch resets money and its active elapsed anchor, leaving EXP epoch alone.
 s.update(mesos=0,cost=0,money_mode='notices',wallet_auto=False,money_elapsed_anchor=utility_session_elapsed(s,now))
 notice_seconds=0.;loot=cost=0
 for segment in range(3):
  active=r.uniform(1,300);now+=active;notice_seconds+=active;loot+=r.randint(0,500);cost+=r.randint(0,100);s.update(mesos=loot,cost=cost)
  rates=utility_session_rates(s,now)
  assert math.isclose(rates['net_hour'],(loot-cost)*3600/notice_seconds,rel_tol=1e-9)
  assert math.isclose(rates['seconds'],prefix+wallet_seconds+notice_seconds,rel_tol=1e-9)
  s=utility_session_toggle(s,now);now+=r.uniform(1,10000)
  assert math.isclose(utility_session_rates(s,now)['net_hour'],rates['net_hour'],rel_tol=1e-9)
  s=utility_session_toggle(s,now);checks+=1
report=dict(ok=True,cases=500,rate_checkpoints=checks,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='Synthetic automatic-wallet then pickup mode elapsed anchors across pauses/resumes, gains/spending, rate denominator epochs; no wallet/OCR/livegame')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
