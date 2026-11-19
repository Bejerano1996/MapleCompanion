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
    check('Quest sources have a direct local keyboard shortcut',bool(root.bind('<Control-Shift-F>')))
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
    check('Failed refresh keeps cached game data visible','Game data unavailable' not in texts and bool(a.scroll.inner.winfo_children()))
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
    from alternate_sources import AlternateCatalogs, parse_catalog
    a.alternate_catalogs=AlternateCatalogs(folder)
    a.alternate_catalogs.rows['ccplz']=parse_catalog('ccplz','<li><a href="/quests/fixture">Fixture New Quest</a><span>Level 39, from NPC, 120 EXP</span></li>')
    journal_before=json.dumps(a.state,sort_keys=True)
    source_saved_geometry=root.geometry()
    left,top,right,bottom=widgets.work_area(root.winfo_x(),root.winfo_y())
    root.geometry(f'360x520{right-360:+d}{top+10:+d}');pump()
    source_window=a.open_alternate_sources();pump()
    check('Source dialog fits the monitor at right edge',source_window.winfo_x()+source_window.winfo_width()<=right+1 and source_window.winfo_y()+source_window.winfo_height()<=bottom+1)
    source_text=[w.cget('text') for w in ui_walk_widgets(source_window) if isinstance(w,(tk.Label,tk.Button))]
    check('Alternate catalog shows attributed quest and EXP',any('Fixture New Quest' in t for t in source_text) and any('CCPLZ · 120 EXP' in t for t in source_text))
    check('Alternate catalog does not mutate journal',json.dumps(a.state,sort_keys=True)==journal_before)
    source_search=next(w for w in ui_walk_widgets(source_window) if isinstance(w,tk.Entry))
    source_area=next(w for w in ui_walk_widgets(source_window) if isinstance(w,widgets.ScrollArea))
    source_rows_before=tuple(child.winfo_id() for child in source_area.inner.winfo_children())
    source_search.insert(0,'Fixture');pump()
    check('Source search reuses rows when matches stay the same',tuple(child.winfo_id() for child in source_area.inner.winfo_children())==source_rows_before)
    source_search.delete(0,'end')
    source_search.insert(0,'unmatched');pump()
    check('Alternate catalog search filters results',not any(isinstance(w,tk.Label) and w.winfo_ismapped() and 'Fixture New Quest' in w.cget('text') for w in ui_walk_widgets(source_window)))
    check('Source window is reused instead of duplicated',a.open_alternate_sources() is source_window)
    source_window.destroy();root.geometry(source_saved_geometry);pump()
    a.open_menu();pump()
    source_menu=next(w for w in ui_walk_widgets(a.menu.body) if isinstance(w,tk.Label) and w.cget('text')=='Additional quest sources')
    source_menu.event_generate('<Button-1>');pump()
    check('Settings menu opens the real source dialog',a._alternate_sources_window is not None and bool(a._alternate_sources_window.winfo_exists()))
    a._alternate_sources_window.destroy();pump()
    a.set_tab('quests');pump()
    reference_journal=a._snapshot()
    refs=[dict(name='Fixture New Quest',sources=a.alternate_catalogs.rows['ccplz'])]
    reference_time=app.time.monotonic()
    with patch.object(app.time,'monotonic',return_value=reference_time):
        check('Manual reference read accepted',a.update_quest_references({'references':refs,'auto':False}))
    a.render();pump()
    reference_text=[w.cget('text') for w in ui_walk_widgets(a.scroll.inner) if isinstance(w,(tk.Label,tk.Button))]
    check('Live reference card shows source EXP and exact title', 'Visible quest · additional sources' in reference_text and 'Fixture New Quest' in reference_text and 'CCPLZ: 120 EXP' in reference_text)
    check('Live reference does not create game quest IDs or progress',a._snapshot()==reference_journal)
    with patch.object(app.time,'monotonic',return_value=reference_time+16):
        check('Old reference expires',a.update_quest_references({'references':[],'auto':True}))
    a.render();pump()
    check('Expired reference card disappears',not any(isinstance(w,tk.Label) and w.cget('text')=='Visible quest · additional sources' for w in ui_walk_widgets(a.scroll.inner)))
    old_auto=a.state['auto_sync'];a.state['auto_sync']=True
    auto_dot_id=a.auto_dot.winfo_id()
    a.reader_health.record({'tracked':['fixture']},100)
    with patch.object(app.time,'monotonic',return_value=101):a.refresh_reader_health()
    check('AUTO dot confirms a fresh quest read',a.auto_dot.cget('fg')==widgets.C['green'])
    with patch.object(app.time,'monotonic',return_value=116):a.refresh_reader_health()
    check('AUTO dot marks an old read and explains it',a.auto_dot.cget('fg')==widgets.C['gold'] and 'waiting for fresh evidence' in a._auto_status_tip.text)
    check('Reader health updates reuse the indicator widget',a.auto_dot.winfo_id()==auto_dot_id)
    a.state['auto_sync']=old_auto;a.refresh_reader_health()
    check('No callback errors',not errors)
    for job in root.tk.call('after','info'):root.tk.call('after','cancel',job)
    root.destroy()
report={'ok':True,'count':len(checks),'checks':checks}
Path(__file__).with_name('compact-ui-results.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report),flush=True)
