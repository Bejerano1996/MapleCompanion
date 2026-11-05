from pathlib import Path
import sys,json,random,hashlib
from fractions import Fraction
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
from training_model import training_forecast
import leveling
rng=random.Random(1723);cases=0
for _ in range(5000):
 lv=rng.randint(1,99);need=leveling.exp_to_next(lv);exp=rng.randrange(need);gain=rng.randint(10,5000)/10
 def forecast(n,at):return training_forecast({'level':lv,'exp':n},{'id':1,'name':'probe','exp':50},personal_gain=gain,now=100,read_at=at)
 original=forecast(exp,100);earned=min(need-1,exp+rng.randint(1,100));lost=max(0,exp-rng.randint(1,100))
 later=forecast(earned,100);death=forecast(lost,100);stale=forecast(exp,80)
 assert later['kills']<=original['kills']<=death['kills']
 rational=Fraction(str(gain));remaining=need-exp
 expected=(remaining*rational.denominator+rational.numerator-1)//rational.numerator
 assert original['kills']==expected
 assert stale['stale'] and stale['kills']==original['kills'] and not original['stale']
 cases+=1
report=dict(ok=True,cases=cases,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='Synthetic same-level gain/loss monotonicity,exact decimal reference and stale-flag scoping; not livegameplay')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
