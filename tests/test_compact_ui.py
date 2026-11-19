"""Compact presentation, accessible font sizes and native EXP details. Own windows only."""
from pathlib import Path
import sys,os,json,tempfile,time,types
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from unittest.mock import patch
import tkinter as tk
import tkinter.font as tkfont
import app,widgets
from PIL import ImageTk
from companion_widgets import ui_walk_widgets,ui_nav_icon
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
with tempfile.TemporaryDirectory(prefix='compact-ui-',dir=Path(__file__).parent) as folder:
    app.STATE_FILE=os.path.join(folder,'state.json')
    Path(app.STATE_FILE).write_text(json.dumps({'auto_sync':False,'auto_on_v2':True,'level':26,'map':'010005061','active':['10306'],'tracked':['10306'],'text_scale':1.0,'panel_size':[470,640]}),encoding='utf-8')
    root=tk.Tk();errors=[];root.report_callback_exception=lambda x,y,z:errors.append(str(y))
    a=app.App(root);a.db.load_indexes();pump()
    check('Default expanded width is compact',a.state['panel_size'][0]==360)
    icons={key:ImageTk.getimage(a._companion_nav[key,False]).tobytes() for key,title in app.TABS}
    search_icon=ui_nav_icon(root,'search',False)
    check('Navigation icons are distinct and Party Quests is not a search icon',len(set(icons.values()))==5 and icons['pq']!=ImageTk.getimage(search_icon).tobytes())
    check('Suggestions start folded',a.state['suggest_open'] is False)
    check('Global search hidden initially',not a._companion_search.winfo_ismapped())
    a.ui_focus_search();pump()
    check('Search opens on request',bool(a._companion_search.winfo_ismapped()))
    a.ui_close_search();pump()
    check('Escape action closes search',not a._companion_search.winfo_ismapped())
    baseline=tkfont.Font(root=root,font=a.profile_name.cget('font')).actual('size')
    header=tkfont.Font(root=root,font=a.title.cget('font')).actual('size')
    for cycle in range(3):
        for scale in (1.3,1.15,1.0):
            a.set_text_size(scale);pump()
            size=tkfont.Font(root=root,font=a.profile_name.cget('font')).actual('size')
            check(f'Font size cycle {cycle} / {scale}',size==round(baseline*scale))
            check(f'Header controls keep their footprint {cycle} / {scale}',tkfont.Font(root=root,font=a.title.cget('font')).actual('size')==header)
    saved_geometry=root.geometry()
    left,top,right,bottom=widgets.work_area(root.winfo_x(),root.winfo_y())
    root.geometry(f'360x520{right-360:+d}{top+10:+d}')
    a.set_text_size(1.0);a.open_menu();pump()
    menu=a.menu
    native_size=next(w for w in ui_walk_widgets(menu.body) if isinstance(w,tk.Label) and w.cget('text')=='130%')
    native_size.event_generate('<Button-1>');pump()
    check('Native Umbrale menu changes the text size',a.state['text_scale']==1.3)
    check('Native settings menu remains within the monitor',menu.winfo_x()+menu.winfo_width()<=right+1 and menu.winfo_y()+menu.winfo_height()<=bottom+1)
    menu.close();root.geometry(saved_geometry);pump()
    a.set_text_size(1.3);a.ui_settings();pump()
    settings=next(w for w in root.winfo_children() if isinstance(w,tk.Toplevel) and 'Character profile' in w.title())
    entry=next(w for w in ui_walk_widgets(settings) if isinstance(w,tk.Entry))
    check('New profile fields use chosen font size',tkfont.Font(root=root,font=entry.cget('font')).actual('size')==round(11*1.3))
    selected=next(w for w in ui_walk_widgets(settings) if isinstance(w,tk.Button) and w.cget('text')=='115%')
    selected.invoke();pump()
    check('Text-size button applies and marks the chosen size',a.state['text_scale']==1.15 and selected.cget('text')=='✓ 115%')
    settings.destroy()
    a.set_text_size(1.3)
    a.companion_exp_details();pump()
    check('Native EXP details open separately',a._companion_exp_window.winfo_exists())
    a.set_party(3);pump()
    check('Party controls update native state',a.state['party']==3)
    a.training_accept_character({'level':26,'exp':29285});a.render_levelup();pump()
    check('Compact EXP reports actual percentage',any(isinstance(w,tk.Label) and '53.34%' in w.cget('text') for w in ui_walk_widgets(a.lvl_strip)))
    a._companion_exp_window.destroy();a.render_levelup();pump()
    with patch('app.messagebox.showinfo') as info:
        a.db.access_paused=True;a.open_data_status()
        check('Data status explains permission pause and retained indexes','renewed permission' in info.call_args.args[1] and str(len(a.db.quests)) in info.call_args.args[1])
    check('Closing details keeps compact summary usable',a.lvl_strip.winfo_exists())
    a.set_status('Error: <urlopen error [Errno 11001] getaddrinfo failed>','red')
    check('Technical errors have short user-facing copy','urlopen' not in a.status.cget('text') and len(a.status.cget('text'))<60)
    check('Original error is available on hover','getaddrinfo' in a._companion_status_tip.text)
    a.set_status('Error: HTTP Error 403: Forbidden','red');pump()
    check('Denied requests retain their HTTP reason','403' in a.status.cget('text'))
    a.companion_error_details();pump()
    details=next(w for w in root.winfo_children() if isinstance(w,tk.Toplevel) and 'Background error details' in w.title())
    check('Error details are selectable in a separate window',any(isinstance(w,tk.Text) and '403' in w.get('1.0','end') for w in ui_walk_widgets(details)))
    details.destroy()
    a.set_status('AUTO is off: quests and counts update only when you press sync; the GPS still follows you')
    check('Routine auto-sync status is concise',a.status.cget('text')=='Auto sync off')
    a.set_status('Offline: meowdb.com unreachable, using saved data (401 quests)')
    check('Offline mode is concise and retains full details',a.status.cget('text')=='Offline · saved data' and '401 quests' in a._companion_status_tip.text)
    a.save_state()
    check('Font choice persists',json.loads(Path(app.STATE_FILE).read_text())['text_scale']==1.3)
    original_quests=a.db.quests.copy();original_loader=a.db.load_indexes
    def load_indexes(self):raise ConnectionError('fixture connection unavailable')
    a.db.load_indexes=types.MethodType(load_indexes,a.db)
    a.companion_retry_data();pump()
    texts=[w.cget('text') for w in ui_walk_widgets(a.scroll.inner) if isinstance(w,(tk.Label,tk.Button))]
    check('Failed data load shows a short recovery state','Game data unavailable' in texts and 'Retry' in texts)
    check('Recovery message is actually mapped on screen',bool(a.scroll.inner.winfo_ismapped()))
    check('Failed data load preserves tracked quests',a.state['active']==['10306'])
    def load_indexes(self):self.quests=original_quests
    a.db.load_indexes=types.MethodType(load_indexes,a.db)
    a.companion_retry_data();pump()
    check('Retry returns to the native quest view',not a._companion_data_error and not a._companion_loading and bool(a.scroll.inner.winfo_children()))
    a.db.load_indexes=original_loader
    original_active=list(a.state['active'])
    a.state['active']=[];a.set_tab('quests');pump()
    check('Empty journal still offers manual quest addition',any(isinstance(w,(tk.Label,tk.Button)) and w.cget('text')=='+ Quest' for w in ui_walk_widgets(a.scroll.inner)))
    a.state['active']=original_active
    check('No callback errors',not errors)
    for job in root.tk.call('after','info'):root.tk.call('after','cancel',job)
    root.destroy()
report={'ok':True,'count':len(checks),'checks':checks}
Path(__file__).with_name('compact-ui-results.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report),flush=True)
