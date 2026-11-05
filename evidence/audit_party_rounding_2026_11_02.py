from pathlib import Path
import sys,json,hashlib
from fractions import Fraction
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
import leveling
cases=0;failures=[]
def rounded(v):return (v.numerator*2+v.denominator)//(2*v.denominator)
for lv in (1,10,27,30,99):
 for members in range(2,7):
  for mode in ('all','me','leech'):
   for mob in range(1,501):
    for levels in (lv*members,lv+members-1):
     hitters=members if mode=='all' else 1
     damage=Fraction(1,members) if mode=='all' else Fraction(1 if mode=='me' else 0)
     share=max(1,rounded(mob*(Fraction(4*lv,5*levels)+damage/5)))
     bonus=min(Fraction(3,10),Fraction(members-1,10))+Fraction(hitters-1,20)
     expected=share+max(1,rounded(share*bonus))
     actual=leveling.party_exp(mob,lv,members,mode,levels)
     if actual!=expected:failures.append(dict(level=lv,members=members,mode=mode,mob_exp=mob,levels=levels,expected=expected,actual=actual))
     cases+=1
report=dict(ok=not failures,cases=cases,failures=failures,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='Exact rational reference for existing formula and half-up rounding,not independent proof of game formula; offline only')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(dict(ok=report['ok'],cases=cases,failures=len(failures),examples=failures[:5])))
