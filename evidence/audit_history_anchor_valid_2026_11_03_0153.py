from pathlib import Path
import sys,json,random,math,hashlib
root=Path(__file__).resolve().parent/'umbrale-companion';sys.path.insert(0,str(root))
from companion_feature_model import utility_compare_maps
r=random.Random(138);checks=0
for case in range(500):
 history=[];expected={}
 for i in range(30):
  name=str(i%3);seconds=r.uniform(1,600);anchor=seconds if i%7==0 else r.uniform(0,seconds);money_seconds=seconds-anchor;wallet=i%2==0
  mesos=0 if money_seconds==0 else r.randint(-100,500) if wallet else r.randint(0,500)
  cost=0 if wallet or money_seconds==0 else r.randint(0,100);exp=r.randint(-100,2000);kills=r.randint(0,40)
  s=dict(finished_at=1,running_since=None,map_id=name,map_ids=[name],elapsed=seconds,mesos=mesos,cost=999 if wallet else cost,exp=exp,exp_is_net=True,kills=kills,money_mode='wallet' if wallet else 'notices')
  s['wallet_elapsed_anchor' if wallet else 'money_elapsed_anchor']=anchor;history.append(s)
  e=expected.setdefault(name,dict(seconds=0,money_seconds=0,net=0,exp=0,kills=0,sessions=0))
  for key,value in [('seconds',seconds),('money_seconds',money_seconds),('net',mesos-cost),('exp',exp),('kills',kills),('sessions',1)]:e[key]+=value
 for metric in ('exp_hour','kills_hour','net_hour'):
  result=utility_compare_maps(history,metric,0);assert len(result['maps'])==3
  for row in result['maps']:
   e=expected[row['map_id']];assert row['sessions']==e['sessions']
   assert math.isclose(row['money_seconds'],e['money_seconds'],rel_tol=1e-10)
   for field,number,denominator in [('exp_hour',e['exp'],e['seconds']),('kills_hour',e['kills'],e['seconds']),('net_hour',e['net'],e['money_seconds'])]:
    assert math.isclose(row[field],number*3600/denominator,rel_tol=1e-10,abs_tol=1e-9),(case,field,row,e)
  assert [row[metric] for row in result['maps']]==sorted([row[metric] for row in result['maps']],reverse=True)
  checks+=1
report=dict(ok=True,datasets=500,sessions=15000,ranked_comparisons=checks,source_sha=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(root.glob('*.py')))).hexdigest(),scope='Synthetic completed history, mixedwallet/pickup elapsed epochs,zero-money-time entries,no double spending,negative netEXP,moneyweightedrates; no nativeUI/OCR/game')
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
