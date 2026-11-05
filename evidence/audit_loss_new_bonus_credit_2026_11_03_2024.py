from pathlib import Path
import sys,json,hashlib
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
from training_accounting import TrainingAccountant
from session_rewards import session_token
import leveling
cases=0
for level in range(1,99):
 for loss in (1,4,8):
  for order in ('old_first','new_first','together'):
   prior=(-100,0,500)[cases%3]
   s=dict(id='cross-loss',running_since=1,auto_rewards=True,exp=prior,party_exp=11,kills=7,mesos=80)
   a=TrainingAccountant();t=session_token(s);before={'level':level,'exp':leveling.exp_to_next(level)-1}
   a.feed(s,t,[],before,0);a.feed(s,t,[],before,.1)
   unclear=[('exp',7),('bonus',None)];full=[('exp',7),('bonus',2)]
   a.feed(s,t,unclear,{'level':level+1,'exp':8},1.)
   assert s['exp']==prior+9
   a.feed(s,t,unclear,{'level':level+1,'exp':8-loss},2.)
   assert s['exp']==prior+9-loss
   pending=unclear+[('exp',7)]
   a.feed(s,t,pending,None,3.)
   if order=='old_first':
    a.feed(s,t,full+[('exp',7)],None,3.5)
   elif order=='new_first':
    a.feed(s,t,pending+[('bonus',2)],None,3.5)
   final=full+[('exp',7),('bonus',2)]
   a.feed(s,t,final,None,4.)
   for now in (21.,22.,30.):a.feed(s,t,final,None,now)
   assert s['exp']==prior+18-loss,(level,loss,order,s,a.logs_since_bar)
   assert s['party_exp']==15 and s['kills']==9 and s['mesos']==80
   a.feed(s,t,final,{'level':level+1,'exp':17-loss},31.)
   assert s['exp']==prior+18-loss
   cases+=1
report=dict(ok=True,cases=cases,level_crossings=[1,98],losses=[1,4,8],bonus_refinement_orders=["old_first","new_first","together"],prior_exp=[-100,0,500],source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='Production accountant, synthetic level crossing then acceptedHUDloss then newbase/bonus andoldbonusrefinement within5secondcredit; no OCR/game')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
