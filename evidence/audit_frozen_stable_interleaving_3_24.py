from pathlib import Path
import sys,json,random,hashlib
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
from training_accounting import NoticeReconciliation
r=random.Random(2223)
for i in range(1000):
 old=r.randint(20,500);covered=r.randint(1,old-1);first=r.randint(1,100);second=r.randint(1,100)
 a=NoticeReconciliation();a.feed(dict(exp=old+50,kills=1),50,0)
 assert a.feed({},covered,2)==old-covered
 assert a.feed(dict(exp=first,kills=1),None,4)==old-covered+first
 assert a.feed({},0,7)==old-covered+first
 assert a.feed(dict(exp=second,kills=1),0,7.001)==first+second
 assert a.base_pending<=a.pending and a.pending>=0
 assert a.feed({},first+second,8)==0
 assert a.feed({},0,14)==0
 assert a.feed({},None,30)==0
report=dict(ok=True,cases=1000,scope='PartialpositiveHUD resets witness; fresh notices before/at retirement survive; strict5secondboundary and final HUD consume exactlyonce; offline only',source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest())
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
