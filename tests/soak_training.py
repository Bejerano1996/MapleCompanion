"""Three-hour repeat validation of training models, own UI fixtures and local OCR.
No game capture, hotkeys or gameplay inputs. Rechecks source revisions while work proceeds.
"""
import argparse,json,subprocess,sys,time,hashlib,tempfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--minutes',type=float,default=180);p.add_argument('--interval',type=float,default=60);p.add_argument('--resume',action='store_true');a=p.parse_args()
project=Path(__file__).resolve().parents[1];base=project.parent.parent;report=base/'work/training-three-hour-soak.json';start=time.monotonic();cycles=[]
if a.resume and report.exists():
 previous=json.loads(report.read_text(encoding='utf-8'));cycles=previous.get('cycles',[])
 start-=float(previous.get('elapsed_seconds',0))
def fingerprint():return hashlib.sha256(b''.join(x.read_bytes() for x in sorted(project.glob('*.py')))).hexdigest()
def write(running):
 report.write_text(json.dumps({'running':running,'elapsed_seconds':round(time.monotonic()-start,2),'target_seconds':a.minutes*60,'cycles':cycles,'scope':'Source regression, own fixture UI and local supplied OCR fixtures only; no live game capture or gameplay input.'},indent=2),encoding='utf-8')
while time.monotonic()-start<a.minutes*60:
 cycle={'index':len(cycles)+1,'seconds':round(time.monotonic()-start,1),'source_sha':fingerprint(),'results':[]}
 for name in ('test_session_rewards.py','test_session_rewards_capture.py','test_training_model.py','test_training_ui.py'):
  file=project/'tests'/name
  if not file.is_file():continue
  try:
   r=subprocess.run([sys.executable,'-X','utf8',str(file)],cwd=project,capture_output=True,text=True,encoding='utf-8',timeout=45)
   cycle['results'].append({'test':name,'ok':r.returncode==0,'output':(r.stdout+r.stderr)[-1600:]})
  except Exception as e:cycle['results'].append({'test':name,'ok':False,'error':str(e)})
 if len(cycles)%5==0:
  with tempfile.TemporaryDirectory(prefix='training-ocr-',dir=base/'work') as tmp:
   out=Path(tmp)/'result.json'
   for image in ('session-rewards-fixture.png','party-rewards-fixture.png'):
    try:
     r=subprocess.run([sys.executable,'-X','utf8',str(project/'app.py'),'--check-rewards-image',str(project/'tests'/image),str(out)],cwd=project,capture_output=True,text=True,encoding='utf-8',timeout=45)
     data=json.loads(out.read_text()) if out.exists() else {}
     cycle['results'].append({'test':'OCR '+image,'ok':r.returncode==0 and data.get('ok',False) and data.get('totals',{}).get('exp',0)>0,'totals':data.get('totals'),'error':data.get('error')})
    except Exception as e:cycle['results'].append({'test':'OCR '+image,'ok':False,'error':str(e)})
 cycle['ok']=all(r['ok'] for r in cycle['results']);cycles.append(cycle);write(True)
 print(json.dumps({'cycle':cycle['index'],'seconds':round(time.monotonic()-start,1),'ok':cycle['ok'],'tests':len(cycle['results'])}),flush=True)
 deadline=min(start+a.minutes*60,time.monotonic()+max(1,a.interval))
 while time.monotonic()<deadline:time.sleep(min(.5,max(.01,deadline-time.monotonic())))
write(False);print('SOAK COMPLETE',flush=True)
