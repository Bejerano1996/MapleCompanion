from pathlib import Path
import sys,json,hashlib
from fractions import Fraction
sys.path.insert(0,str(Path(__file__).resolve().parent/'umbrale-companion'))
from training_model import training_forecast
project=Path(__file__).resolve().parent/'umbrale-companion'
cases=0;failures=[]
for numerator in range(10,101):
    gain=numerator/10
    for left in range(1,136):
        ratio=Fraction(left)/Fraction(str(gain))
        expected=-(-ratio.numerator//ratio.denominator)
        actual=training_forecast({'level':5,'exp':135-left},{'name':'probe','exp':1},personal_gain=gain)['kills']
        cases+=1
        if actual!=expected:failures.append(dict(left=left,gain=gain,actual=actual,expected=expected))
sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(project.glob('*.py')))).hexdigest()
report=dict(ok=not failures,cases=cases,failures=failures,source_sha=sha,scope='Offline exact Fraction reference versus decimal gain forecast; no game capture')
Path(__file__).with_suffix('.json').write_text(json.dumps(report))
print(json.dumps(report))
assert not failures
