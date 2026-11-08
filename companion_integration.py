from widgets import font_size
"""Maple Companion presentation and tools on top of Umbrale's source engine.

No packaged bytecode, private APIs, game input or game process access are used.
"""
import os
import tkinter as tk
import tkinter.font as tkfont
import webbrowser
import time
from PIL import Image,ImageTk
import widgets
from widgets import C,FONT,label,ScrollArea
from companion_widgets import ui_button,ui_card,ui_nav_icon,ui_walk_widgets,ui_round_card
from companion_feature_model import utility_session_new,utility_session_snapshot,utility_search_history
from companion_tools import install_tools,ui_tools_indicator
from companion_market import market_open
from monster_maps_ui import install_monster_maps
from quest_rewards_ui import install_quest_rewards
from training_ui import install_training_ui

MESOWATCH_URL='https://meso.watch/'

def apply_palette():
    C.update(base='#ffffff',bg='#f4f3f8',card='#ffffff',card_hi='#fff7ef',
             border='#e2dfe9',border_hi='#777387',header='#f4f3f8',header_dark='#eeedf5',
             accent='#ac5d18',accent_hi='#854409',press='#f3d2a8',text='#252735',muted='#626477',
             disabled='#878695',gold='#854409',link='#854409',green='#248453',red='#b43446',
             button='#fff0dd',button_hi='#f9dfbf',bar_muted='#41485e',bar_green='#248453',
             icon='#41485e',icon_active='#854409',tip_bg='#1f2937',tip_text='#ffffff')

def integrate(Base,core):
    apply_palette()
    core['VERSION']='3.0.1-companion'
    core['HOVER_ALPHA']=1.0
    core['PANEL_SIZE']=(360,.5)
    core['MIN_W']=340
    core['DEFAULT_STATE']['idle_alpha']=1.0

    class CompanionApp(Base):
        def __init__(self,root):
            super().__init__(root)
            session=self.state.get('utility_session')
            if not isinstance(session,dict):session=utility_session_new()
            session['running_since']=None
            self.state['utility_session']=session
            for key in ('utility_timers','utility_session_history','map_bookmarks','search_history','companion_watchlist'):
                self.state.setdefault(key,[])
            self._utility_tick_job=root.after(1000,self.utility_tick)
            self._companion_profile_refresh()
            if not self.db.quests:self.render()

        def run_bg(self,fn,callback,on_error=None):
            if getattr(fn,'__name__','')!='load_indexes' or getattr(fn,'__self__',None) is not getattr(self,'db',None):
                return super().run_bg(fn,callback,on_error)
            self._companion_loading=True;self._companion_data_error=None
            def loaded(value):
                self._companion_loading=False;self._companion_data_error=None
                callback(value)
            def failed(error):
                self._companion_loading=False;self._companion_data_error=str(error)
                if on_error:on_error(error)
                self.render()
                self._pill('Data unavailable','red')
            return super().run_bg(fn,loaded,failed)

        def _build(self):
            widgets.text_scale=self.state.get('text_scale',1.0)
            self.state.setdefault('compact_v3',True)
            self.state.setdefault('profile_name','')
            self.state.setdefault('character_class','Adventurer')
            if not self.state.get('companion_compact_v2'):
                self.state['panel_size']=[360,520]
                self.state['suggest_open']=False
                self.state['companion_compact_v2']=True
            super()._build()
            self.header.config(bg=C['header'])
            # Retain the Umbrale wordmark/sigil on a dark tile so its white strokes remain legible.
            try:
                self._companion_brand=ImageTk.PhotoImage(Image.open(os.path.join(core['BUNDLE_DIR'],'icon.png')).resize((28,28)))
                for widget in self.header.winfo_children():
                    if isinstance(widget,tk.Label) and widget.cget('image'):widget.config(image=self._companion_brand)
            except OSError:pass
            self.title.config(text='UMBRΛLE',font=(FONT, font_size(10),'bold'))
            bar=next(iter(self.tab_btns.values())).master.master
            for child in bar.winfo_children():child.destroy()
            self._companion_nav={}
            for index,(key,title) in enumerate(core['TABS']):
                cell=tk.Frame(bar,bg=C['bg']);cell.pack(side='left',expand=True,fill='x')
                b=widgets.button(cell,title,lambda k=key:self.set_tab(k),bg='bg',fg='text',padx=5,
                                 tip=f'{title} · {index+1} / Alt+{index+1}')
                for selected in (False,True):self._companion_nav[key,selected]=ui_nav_icon(self.root,key,selected)
                b.config(image=self._companion_nav[key,False],compound='none',pady=5)
                b.pack(fill='x');b.line=tk.Frame(cell,bg=C['bg'],height=2);b.line.pack(fill='x',padx=5)
                self.tab_btns[key]=b
            self.tools_btn=ui_button(bar,'⊞',self.ui_tools,compact=True,tip='Tools · Ctrl+K')
            self.tools_btn.pack(side='left',padx=3)
            self.price_btn=ui_button(bar,'',self.ui_market,compact=True,tip='MesoWatch · item prices')
            self.price_btn.pack(side='left',padx=3)
            self._utility_icons={}
            for key,btn in [('money',self.price_btn),('tools',self.tools_btn)]:
                self._utility_icons[key]=ui_nav_icon(self.root,key)
                btn.config(image=self._utility_icons[key],text='',width=22,height=22)
            self.profile=tk.Frame(self.body,bg=C['bg']);self.profile.pack(fill='x',before=bar,padx=5,pady=(3,0))
            row=self.profile
            ui_button(row,'Next →',self.companion_overview,primary=True,compact=True,tip='Next objective').pack(side='left')
            ui_button(row,'⚙',self.ui_settings,compact=True,tip='Appearance & profile · Ctrl+,').pack(side='right')
            ui_button(row,'⌕',self.ui_focus_search,compact=True,tip='Search · Ctrl+F').pack(side='right')
            self.profile_name=label(row,'',bold=True,size=9,anchor='e');self.profile_name.pack(fill='x',expand=True,padx=5)
            self.profile_summary=label(row,'',fg='muted',size=8)
            footer=self.status.master
            self.global_query=tk.StringVar()
            search=tk.Frame(self.body,bg=C['card'],highlightbackground=C['border'],highlightthickness=1)
            self._companion_search=search
            self._companion_search_footer=footer
            self.global_entry=tk.Entry(search,textvariable=self.global_query,font=(FONT, font_size(10)),bg=C['card'],fg=C['text'],insertbackground=C['text'],relief='flat')
            self.global_entry.pack(side='left',fill='x',expand=True,padx=9,ipady=7)
            self._companion_search_kind=tk.StringVar(value='Maps / NPCs')
            menu=tk.OptionMenu(search,self._companion_search_kind,'Maps / NPCs','Monsters','Items');menu.config(bg=C['card'],fg=C['text'],font=(FONT, font_size(8)),relief='flat',highlightthickness=0);menu.pack(side='left')
            self._companion_search_button=ui_button(search,'↑',self.ui_search,primary=True,compact=True,tip='Search selected database · Ctrl+F');self._companion_search_button.pack(side='right',padx=3)
            self.global_entry.bind('<Return>',lambda e:self.ui_search())
            self.global_entry.bind('<Escape>',lambda e:self.ui_close_search())
            widgets.Tooltip(self.global_entry,'Search maps, NPCs, monsters or items; choose the database to the right')
            self._companion_bindings=getattr(self,'_companion_bindings',{})
            bindings={'<Control-f>':lambda e:self.ui_focus_search(),'<Control-k>':lambda e:self.ui_tools(),'<Control-comma>':lambda e:self.ui_settings(),'<Control-KeyPress>':self._companion_control}
            for index,(key,_) in enumerate(core['TABS'],1):bindings[f'<Alt-Key-{index}>']=lambda e,k=key:self._companion_open_tab(k)
            for sequence,callback in bindings.items():
                previous=self._companion_bindings.get(sequence)
                if previous:self.root.unbind(sequence,previous)
                self._companion_bindings[sequence]=self.root.bind(sequence,callback)
            self._companion_profile_refresh()

        def _companion_open_tab(self,key):
            if self.collapsed:self.toggle_collapse()
            self.set_tab(key)

        def _companion_control(self,event):
            if event.state&4 and not event.state&1:
                action={70:self.ui_focus_search,75:self.ui_tools,188:self.ui_settings}.get(event.keycode)
                if action:action();return 'break'

        def _companion_profile_refresh(self):
            if hasattr(self,'profile_name') and self.profile_name.winfo_exists():
                self.profile_name.config(text=self.state.get('profile_name') or 'Your adventurer')
                self.profile_summary.config(text=f"{self.state.get('character_class','Adventurer')} · Level {self.state.get('level',1)}")

        def set_tab(self,tab):
            super().set_tab(tab)
            if hasattr(self,'_companion_nav'):
                for key,b in self.tab_btns.items():
                    b.config(image=self._companion_nav[key,key==tab])
            self._companion_profile_refresh()

        def _on_synced(self,result):
            self._live_last_result={'_minimap_readable':bool(result.get('map'))}
            super()._on_synced(result)
            self._companion_profile_refresh()

        def render(self,keep_scroll=True):
            if self.state.get('tab')!='pq' and (not self.db.quests or getattr(self,'_companion_loading',False) or getattr(self,'_companion_data_error',None)):
                self.scroll.clear(keep_scroll)
                unavailable=bool(getattr(self,'_companion_data_error',None))
                label(self.scroll.inner,'Game data unavailable' if unavailable else 'Loading game data…',
                      bold=True,size=10,padx=10,pady=12).pack(anchor='w')
                if unavailable:
                    widgets.button(self.scroll.inner,'Retry',self.companion_retry_data,bg='button',padx=10,
                                   tip='Download game indexes again').pack(anchor='w',padx=10,pady=(0,10))
                self.scroll.commit()
                self._fit_height()
                return
            super().render(keep_scroll)
            for frame in self.scroll.inner.winfo_children():
                if isinstance(frame,tk.Frame) and frame.cget('bg') in (C['card'],C['card_hi']):
                    frame.config(highlightthickness=1,highlightbackground=C['border'])
                    frame.pack_configure(padx=8,pady=5)
                    ui_round_card(frame,14,fill=frame.cget('bg'),border=C['border'])
            self._fit_height()

        def companion_retry_data(self):
            if getattr(self,'_companion_loading',False):return
            self.run_bg(self.db.load_indexes,self._on_loaded)
            self._pill('Loading data…','muted')
            self.render()

        def render_quests(self):
            super().render_quests()
            # Keep the native commands, with short labels and explanations on hover.
            quest_footer=None
            for widget in ui_walk_widgets(self.scroll.inner):
                if not isinstance(widget,(tk.Label,tk.Button)):continue
                text=widget.cget('text')
                if text.startswith('No quests yet.'):
                    widget.config(text='No quests yet. Sync from the Quest window or add one below.')
                    widgets.Tooltip(widget,'Open the Quest window in the game, then use Sync quests.')
                elif text=='⟲ Reset from Quest window':
                    widget.config(text='Sync quests');quest_footer=widget.master
                elif text=='Clear list':
                    widget.pack_forget()
                elif text.endswith('Quests you could take now'):widget.config(text=text.replace('Quests you could take now','Suggested quests'))
                elif text=='Collapse (▴) to keep just its objectives in view.':widget.pack_forget()
            if quest_footer:
                widgets.button(quest_footer,'+ Quest',self.open_add_dialog,bg='bg',size=8,
                               tip='Add a quest manually').pack(side='right')

        def set_status(self,text,color='muted'):
            full=str(text)
            if full.startswith('Error:'):
                text='Could not load data · try again'
            elif full.startswith("Couldn't load locations:"):
                text='Quest locations unavailable · retry sync'
            elif full.startswith("Couldn't save your list:"):
                text='Changes not saved · check folder access'
            elif full.startswith('AUTO is off:'):
                text='Auto sync off'
            elif full.startswith('AUTO on:') or full=='Following the game (AUTO)':
                text='Auto sync on'
            elif full.startswith('Offline:'):
                text='Offline · saved data'
            elif full.startswith('No quests on screen:'):
                text='Open the in-game Quest Helper'
            elif len(full)>90:
                text=full[:86].rsplit(' ',1)[0]+'…'
            super().set_status(text,color)
            tip=getattr(self,'_companion_status_tip',None)
            if tip:tip.text=full
            elif hasattr(self,'status'):
                self._companion_status_tip=widgets.Tooltip(self.status,full)

        def render_levelup(self):
            details=getattr(self,'_companion_exp_window',None)
            if details and details.winfo_exists():self._render_exp_details()
            bar=self.state.get('exp_bar')
            spec=('compact',self.state.get('level'),tuple(bar or ()),widgets.text_scale)
            if spec==self._lvl_spec:return
            self._lvl_spec=spec;self._companion_exp_compact=True
            for widget in self.lvl_strip.winfo_children():widget.destroy()
            text=f"EXP {bar[1]:.1f}%" if bar else 'EXP —'
            label(self.lvl_strip,text,bg='card',fg='muted',size=8).pack(side='left',padx=6,pady=3)
            widgets.button(self.lvl_strip,'Details',self.companion_exp_details,bg='card',size=8,padx=4,
                           tip='EXP, kills remaining & party settings').pack(side='right')

        def companion_exp_details(self):
            existing=getattr(self,'_companion_exp_window',None)
            if existing and existing.winfo_exists():existing.lift();return
            w=self.ui_dialog('EXP & party')
            self._companion_exp_window=w
            panel=tk.Frame(w,bg=C['card']);panel.pack(fill='x',padx=12,pady=6)
            self._companion_exp_panel=panel;self._companion_exp_spec=None
            self._render_exp_details()

        def _render_exp_details(self):
            original,spec=self.lvl_strip,self._lvl_spec
            try:
                self.lvl_strip=self._companion_exp_panel
                self._lvl_spec=self._companion_exp_spec
                super().render_levelup()
                self._companion_exp_spec=self._lvl_spec
            finally:
                self.lvl_strip,self._lvl_spec=original,spec

        def save_state(self):
            current=self.state.get('utility_session')
            if current:self.state['utility_session']=utility_session_snapshot(current)
            try:return super().save_state()
            finally:
                if current:self.state['utility_session']=current

        def ui_dialog(self,title):
            w=tk.Toplevel(self.root,bg=C['bg']);w.title('UMBRΛLE · '+title);w.transient(self.root);w.attributes('-topmost',True)
            width,height=470,600
            x,y=widgets.on_monitor_of(self.root,self.root.winfo_x()+30,self.root.winfo_y()+35,width,height)
            w.geometry(f'{width}x{height}{x:+d}{y:+d}');w.resizable(True,True)
            label(w,title,size=17,bold=True,wraplength=width-36,justify='left').pack(anchor='w',padx=18,pady=(16,10))
            w.bind('<Escape>',lambda e:w.destroy())
            return w

        def ui_settings(self):
            w=self.ui_dialog('Character profile')
            appearance=tk.Frame(w,bg=C['bg']);appearance.pack(fill='x',padx=18,pady=(0,6))
            label(appearance,'Text size',fg='muted').pack(side='left')
            size_buttons={}
            def choose_size(value):
                self.set_text_size(value)
                for scale,button in size_buttons.items():
                    button.config(text=('✓ ' if scale==value else '')+f'{round(scale*100)}%')
            for scale in widgets.TEXT_SCALES:
                selected=abs(scale-widgets.text_scale)<.01
                size_buttons[scale]=ui_button(appearance,('✓ ' if selected else '')+f'{round(scale*100)}%',
                                             lambda s=scale:choose_size(s),compact=True,tip='Resize text')
                size_buttons[scale].pack(side='left',padx=2)
            form=ui_card(w)
            variables={}
            for key,title in [('profile_name','Name'),('character_class','Class'),('level','Level')]:
                label(form,title,bg='card',fg='muted').pack(anchor='w',padx=12,pady=(8,2))
                var=tk.StringVar(value=str(self.state.get(key,'')));variables[key]=var
                tk.Entry(form,textvariable=var,bg=C['header_dark'],fg=C['text'],font=(FONT, font_size(11)),relief='flat').pack(fill='x',padx=12,ipady=6)
            feedback=label(form,'',fg='red',bg='card');feedback.pack(fill='x',padx=12)
            def save():
                try:
                    value=int(variables['level'].get())
                    if not 1<=value<=200:raise ValueError()
                except ValueError:feedback.config(text='Enter a level from 1 to 200');return
                self.state.update(profile_name=variables['profile_name'].get().strip()[:80],character_class=variables['character_class'].get().strip()[:80] or 'Adventurer')
                self.level.set(str(value));self.set_level();self.save_state();self._companion_profile_refresh();w.destroy()
            ui_button(form,'Save changes',save,primary=True).pack(fill='x',padx=12,pady=12)
            ui_button(w,'More settings',lambda:(w.destroy(),self.open_menu())).pack(fill='x',padx=18,pady=8)
            ui_button(w,'Clear quest list…',lambda:(w.destroy(),self.clear_quests()),compact=True,
                      tip='Remove tracked quests after confirmation').pack(anchor='w',padx=18,pady=4)

        def set_text_size(self,scale):
            if scale not in widgets.TEXT_SCALES:return
            old=widgets.text_scale
            # Scale existing controls too; native render recreates list/GPS content.
            # Remember logical sizes to prevent drift after repeated size changes.
            for widget in ui_walk_widgets(self.root):
                try:
                    ancestor=widget
                    while ancestor is not None and ancestor is not self.header:ancestor=getattr(ancestor,'master',None)
                    if ancestor is self.header:continue
                    if 'font' not in widget.keys():continue
                    current=tkfont.Font(root=self.root,font=widget.cget('font'))
                    logical=getattr(widget,'_companion_font_points',None)
                    if logical is None:
                        logical=round(current.actual('size')/old)
                        widget._companion_font_points=logical
                    actual=current.actual();actual['size']=round(logical*scale)
                    font=tkfont.Font(root=self.root,**actual)
                    widget.config(font=font);widget._companion_scaled_font=font
                except tk.TclError:pass
            super().set_text_size(scale)
            self.save_state()

        def ui_focus_search(self):
            if self.collapsed:self.toggle_collapse()
            self._companion_search.pack(side='bottom',fill='x',before=self._companion_search_footer,padx=5,pady=4)
            self.global_entry.focus_set();self.global_entry.selection_range(0,'end')

        def ui_close_search(self):
            self._companion_search.pack_forget()
            self.root.focus_set()
            return 'break'

        def ui_search(self):
            query=self.global_query.get().strip()
            if not query:self.ui_focus_search();return
            self.state['search_history']=utility_search_history(self.state.get('search_history'),query);self.save_state()
            kind=self._companion_search_kind.get()
            if kind in ('Monsters','Items'):
                self._companion_open_tab('mobs' if kind=='Monsters' else 'items')
                (self.mob_query if kind=='Monsters' else self.item_query).set(query)
            else:
                self.open_map_search(self._companion_search_button)
                box=next(w for w in ui_walk_widgets(self.map_search) if isinstance(w,tk.Entry))
                box.delete(0,'end');box.insert(0,query)

        def choose_map(self):self.open_map_search(self.map_label,correct=True)
        def ui_open_journal(self,qid=None):
            if qid:self.state['expanded']=qid
            self._companion_open_tab('quests')

        def companion_overview(self):
            w=self.ui_dialog('Your next step')
            try:objective=self.next_objective()
            except KeyError:objective=None
            label(w,objective[0] if objective else 'Add a quest or open the quest suggestions.',size=13,bold=True,wraplength=420).pack(fill='x',padx=18,pady=12)
            qid=self.focused() or (self.state.get('expanded') if self.state.get('expanded') in self.state['active'] else None) or next((q for q in self.state['active'] if q in self.db.quests),None)
            if qid:
                area=ScrollArea(w);area.pack(fill='both',expand=True)
                for index,step in enumerate(self.guides.get(qid) or []):
                    if index not in self.done_steps(qid) and step.get('sources'):
                        self.render_acquisition_sources(area.inner,'bg',qid,step)
                        break
                self.render_quest_guide(area.inner,'bg',qid,key='companion-overview:'+qid);area.commit()
            ui_button(w,'Open quest journal',lambda:(w.destroy(),self.ui_open_journal(qid)),primary=True).pack(fill='x',padx=18,pady=10)

        def open_add_dialog(self):
            w=self.ui_dialog('Add a quest');query=tk.StringVar()
            tk.Entry(w,textvariable=query,font=(FONT, font_size(11))).pack(fill='x',padx=18,ipady=6)
            area=ScrollArea(w);area.pack(fill='both',expand=True)
            def draw(*unused):
                area.clear(False);term=query.get().casefold().strip()
                rows=[q for q in self.db.quests.values() if term in q.get('name','').casefold() and q['id'] not in self.state['active']]
                for q in rows[:50]:ui_button(area.inner,q['name'],lambda q=q:(self.add_quest(q['id']),w.destroy())).pack(fill='x',padx=10,pady=3)
                area.commit()
            trace=query.trace_add('write',draw)
            w.bind('<Destroy>',lambda e:query.trace_remove('write',trace) if e.widget==w else None,add='+');draw()

        def ui_watchlist(self):
            w=self.ui_dialog('Farming watchlist');name=tk.StringVar()
            box=tk.Entry(w,textvariable=name,font=(FONT, font_size(11)));box.pack(fill='x',padx=18,ipady=6)
            area=ScrollArea(w);area.pack(fill='both',expand=True)
            def draw():
                area.clear(False)
                for item in self.state['companion_watchlist']:
                    card=ui_card(area.inner)
                    label(card,item,bg='card',bold=True,wraplength=390).pack(fill='x',padx=10,pady=8)
                    def prices(item=item):self.ui_market();self._market_search_query.set(item)
                    ui_button(card,'Prices',prices,compact=True).pack(side='left',padx=10,pady=6)
                    ui_button(card,'Remove',lambda item=item:remove(item),compact=True).pack(side='right',padx=10,pady=6)
                area.commit()
            def add():
                value=name.get().strip()[:120]
                if value and value not in self.state['companion_watchlist'] and len(self.state['companion_watchlist'])<100:
                    self.state['companion_watchlist'].append(value);self.save_state();name.set('');draw()
            def remove(value):self.state['companion_watchlist'].remove(value);self.save_state();draw()
            ui_button(w,'Save item',add,primary=True).pack(fill='x',padx=18,pady=8);draw()

        def ui_mesowatch(self,item_name=''):
            w=self.ui_dialog('MesoWatch · prices')
            self._market_search_query=tk.StringVar(value=item_name)
            box=tk.Entry(w,textvariable=self._market_search_query,font=(FONT,font_size(11)),bg=C['card'],fg=C['text'])
            box.pack(fill='x',padx=18,pady=10,ipady=7)
            feedback=label(w,'',fg='muted',wraplength=400,justify='left')
            feedback.pack(fill='x',padx=18,pady=6)
            def search():
                name=self._market_search_query.get().strip()
                if not name:feedback.config(text='Enter an item name.');box.focus_set();return
                from mesowatch_browser import launch_search
                try:launch_search(name)
                except OSError as error:feedback.config(text='Could not open MesoWatch: '+str(error));return
                feedback.config(text='Opening MesoWatch · '+name)
            box.bind('<Return>',lambda e:search())
            ui_button(w,'Search MesoWatch ↗',search,primary=True).pack(fill='x',padx=18,pady=8)
            ui_button(w,'MapleStory Watch · in-app prices',lambda:market_open(self),compact=True).pack(fill='x',padx=18,pady=6)
            box.focus_set()

        def render_item_drops(self,card,bg,iid,item=None):
            super().render_item_drops(card,bg,iid,item)
            if item and item.get('name'):
                row=tk.Frame(card,bg=C[bg]);row.pack(fill='x',padx=8,pady=5)
                def prices():self.ui_market();self._market_search_query.set(item['name'])
                ui_button(row,'Market prices',prices,compact=True).pack(side='left',padx=3)
                ui_button(row,'MesoWatch ↗',lambda:self.ui_mesowatch(item['name']),compact=True).pack(side='left',padx=3)

        def ui_market(self):self.ui_mesowatch()

    install_tools(CompanionApp)
    install_monster_maps(CompanionApp)
    install_quest_rewards(CompanionApp)
    install_training_ui(CompanionApp)
    return CompanionApp
