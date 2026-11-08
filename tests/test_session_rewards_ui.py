from pathlib import Path
import sys,os,json,tempfile,time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import tkinter as tk
import app
import companion_portraits
real_fetch=companion_portraits.fetch_portrait
companion_portraits.fetch_portrait=lambda db,kind,identity,name:real_fetch(db,kind,identity,name) if (kind,str(identity)) in (("mob","23"),("npc","226")) else None
from companion_widgets import ui_walk_widgets
app.App.run_bg=lambda *a,**k:None
app.App.sync_from_game=lambda *a,**k:None
app.App.prefetch=lambda *a,**k:None
class NoHotkey:
    def __init__(self,*a,**k):pass
    def start(self):pass
app.HotkeyThread=NoHotkey
checks=[]
def check(name,value):
    if not value:raise AssertionError(name)
    checks.append(name)
def pump():
    for _ in range(4):root.update();time.sleep(.015)
def texts(w):return [c.cget('text') for c in ui_walk_widgets(w) if isinstance(c,(tk.Label,tk.Button))]
with tempfile.TemporaryDirectory(prefix='map-reward-',dir=Path(__file__).parent) as folder:
    app.STATE_FILE=os.path.join(folder,'state.json')
    Path(app.STATE_FILE).write_text(json.dumps({'auto_sync':False,'auto_on_v2':True,'active':['10113'],'expanded':'10113','level':27,'map':'010005000','done':{'10113':[0]}}),encoding='utf-8')
    root=tk.Tk();errors=[];root.report_callback_exception=lambda x,y,z:errors.append(str(y))
    a=app.App(root);a.db.load_indexes()


    import companion_tools
    from session_rewards import session_token
    pending=[]
    a.run_bg=lambda fn,callback,on_error=None:pending.append(callback)
    a.state['utility_session'].update(running_since=100,exp=0,mesos=0,kills=0,cost=12)
    a._reward_last_poll=0;a.utility_poll_rewards();pending.pop(0)([('exp',5)])
    a._reward_last_poll=0;a.utility_poll_rewards();pending.pop(0)([('exp',5),('exp',7),('bonus',2),('mesos',10)])
    a._reward_last_poll=0;a.utility_poll_rewards();pending.pop(0)([('exp',5),('exp',7),('bonus',2),('mesos',10)])
    check('Automatic totals applied',(a.state['utility_session']['exp'],a.state['utility_session']['mesos'],a.state['utility_session']['kills'])==(9,10,1))
    a.ui_tools();pump()
    shown=texts(root)
    check('Automatic mode visible','Auto read game' in [v.cget('text') for v in ui_walk_widgets(root) if isinstance(v,tk.Checkbutton)])
    check('Live totals visible',any('9 EXP' in t and '10 mesos' in t for t in shown))
    check('Party breakdown visible',any('party +2' in t for t in shown))
    check('Kill estimation disclosed',any('≈' in t and 'kills' in t for t in shown) and any('including party' in getattr(getattr(v,'_training_tip',None),'text','') for v in ui_walk_widgets(root)))
    next(v for v in ui_walk_widgets(root) if isinstance(v,tk.Button) and v.cget('text')=='Save totals').invoke();pump()
    check('Save retains live totals',a.state['utility_session']['exp']==9 and a.state['utility_session']['cost']==12)
    a._reward_last_poll=0;a.utility_poll_rewards();late=pending.pop(0);a.state['utility_session']['running_since']=None;late([('exp',7),('bonus',2),('mesos',10),('exp',100)])
    check('Paused session rejects pending read',a.state['utility_session']['exp']==9)
    next(v for v in ui_walk_widgets(root) if isinstance(v,tk.Button) and v.cget('text')=='Mesos · wallet checkpoints').invoke();pump()
    dialog=next(w for w in root.winfo_children() if isinstance(w,tk.Toplevel) and 'wallet checkpoints' in w.title())
    entries=[v for v in ui_walk_widgets(dialog) if isinstance(v,tk.Entry)]
    entries[0].insert(0,'10,000');entries[1].insert(0,'12,345')
    next(v for v in ui_walk_widgets(dialog) if isinstance(v,tk.Button) and v.cget('text')=='Apply wallet checkpoint').invoke();pump()
    check('Wallet replaces incomplete notices',a.state['utility_session']['mesos']==2345 and a.state['utility_session']['exp']==9)
    from companion_feature_model import utility_session_rates
    check('Wallet spending not subtracted twice',utility_session_rates(a.state['utility_session'])['net_mesos']==2345)
    a.state['utility_session']['running_since']=100
    from session_rewards import apply_rewards
    apply_rewards(a.state['utility_session'],session_token(a.state['utility_session']),dict(mesos=999))
    check('Wallet ignores log money',a.state['utility_session']['mesos']==2345)
    next(v for v in ui_walk_widgets(root) if isinstance(v,tk.Button) and v.cget('text')=='Mesos · wallet checkpoints').invoke();pump()
    next(v for v in ui_walk_widgets(root) if isinstance(v,tk.Button) and v.cget('text')=='Start automatic wallet reading').invoke();pump()
    def wallet_read(value):
        pending.clear();a._reward_busy=False;a._reward_last_poll=0;a.utility_poll_rewards()
        pending.pop()({'events':[],'character':None,'wallet':value})
    wallet_read(179029);wallet_read(179069)
    check('Automatic wallet differences replace loot log',a.state['utility_session']['mesos']==40)
    a.state['utility_session']['running_since']=101;wallet_read(190000);wallet_read(190010)
    check('Resume excludes offline wallet changes',a.state['utility_session']['mesos']==50)
    next(v for v in ui_walk_widgets(root) if isinstance(v,tk.Button) and v.cget('text')=='Mesos · read pickup notices').invoke();pump()
    check('Pickup mode works without inventory',not a.state['utility_session']['wallet_auto'] and a.state['utility_session']['money_mode']=='notices')
    check('Pickup mode resets only money baseline',a.state['utility_session']['mesos']==0 and a.state['utility_session']['exp']==9)
    check('No callback errors',not errors)
    print(json.dumps({'ok':True,'checks':checks}));root.destroy()
