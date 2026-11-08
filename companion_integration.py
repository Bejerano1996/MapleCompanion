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

MESOWATCH_URL='https://beta.meso.watch/'

def apply_palette():
    C.update(base='#ffffff',bg='#f4f3f8',card='#ffffff',card_hi='#fff7ef',
             border='#e2dfe9',border_hi='#777387',header='#f4f3f8',header_dark='#eeedf5',
             accent='#ac5d18',accent_hi='#854409',press='#f3d2a8',text='#252735',muted='#626477',
             disabled='#878695',gold='#854409',link='#854409',green='#248453',red='#b43446',
             button='#fff0dd',button_hi='#f9dfbf',bar_muted='#41485e',bar_green='#248453',
             icon='#41485e',icon_active='#854409',tip_bg='#1f2937',tip_text='#ffffff')

def integrate(Base,core):
    apply_palette()
    core['VERSION']='2.1.0-companion'
    core['HOVER_ALPHA']=1.0
    core['PANEL_SIZE']=(470,.65)
    core['MIN_W']=420
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

        def _build(self):
            self.state.setdefault('profile_name','')
            self.state.setdefault('character_class','Adventurer')
            if not self.state.get('companion_layout_v1'):
                size=self.state.get('panel_size') or [470,640]
                self.state['panel_size']=[max(470,size[0]),max(640,size[1])]
                self.state['companion_layout_v1']=True
            super()._build()
            self.header.config(bg=C['header'])
            # Retain the Umbrale wordmark/sigil on a dark tile so its white strokes remain legible.
            try:
                self._companion_brand=ImageTk.PhotoImage(Image.open(os.path.join(core['BUNDLE_DIR'],'icon.png')).resize((28,28)))
                for widget in self.header.winfo_children():
                    if isinstance(widget,tk.Label) and widget.cget('image'):widget.config(image=self._companion_brand)
            except OSError:pass
            self.title.config(text='UMBRΛLE',font=(FONT,10,'bold'))
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
            self.tools_btn=ui_button(bar,'⊞',self.ui_tools,compact=True,tip='Companion tools · Ctrl+K\nSessions, routes, reminders and saved maps')
            self.tools_btn.pack(side='left',padx=3)
            ui_button(bar,'Market',self.ui_market,compact=True,tip='Item prices · MapleStory Watch and MesoWatch').pack(side='left',padx=3)
            self.profile=ui_card(self.body,pady=(7,8));self.profile.pack_configure(before=bar)
            row=tk.Frame(self.profile,bg=C['card']);row.pack(fill='x',padx=12,pady=10)
            ui_button(row,'What next? →',self.companion_overview,primary=True,compact=True,tip='Show the next objective and native quest guide').pack(side='left')
            ui_button(row,'⚙',self.ui_settings,compact=True,tip='Profile and character settings · Ctrl+,').pack(side='right')
            self.profile_name=label(row,'',bg='card',bold=True,size=11,anchor='e');self.profile_name.pack(fill='x',expand=True)
            self.profile_summary=label(self.profile,'',bg='card',fg='muted',size=9,anchor='e');self.profile_summary.pack(fill='x',padx=14,pady=(0,9))
            footer=self.status.master
            self.global_query=tk.StringVar()
            search=tk.Frame(self.body,bg=C['card'],highlightbackground=C['border'],highlightthickness=1)
            search.pack(side='bottom',fill='x',before=footer,padx=5,pady=6)
            self.global_entry=tk.Entry(search,textvariable=self.global_query,font=(FONT,10),bg=C['card'],fg=C['text'],insertbackground=C['text'],relief='flat')
            self.global_entry.pack(side='left',fill='x',expand=True,padx=9,ipady=7)
            self._companion_search_kind=tk.StringVar(value='Maps / NPCs')
            menu=tk.OptionMenu(search,self._companion_search_kind,'Maps / NPCs','Monsters','Items');menu.config(bg=C['card'],fg=C['text'],font=(FONT,8),relief='flat',highlightthickness=0);menu.pack(side='left')
            self._companion_search_button=ui_button(search,'↑',self.ui_search,primary=True,compact=True,tip='Search selected database · Ctrl+F');self._companion_search_button.pack(side='right',padx=3)
            self.global_entry.bind('<Return>',lambda e:self.ui_search())
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
            super().render(keep_scroll)
            for frame in self.scroll.inner.winfo_children():
                if isinstance(frame,tk.Frame) and frame.cget('bg') in (C['card'],C['card_hi']):
                    frame.config(highlightthickness=1,highlightbackground=C['border'])
                    frame.pack_configure(padx=8,pady=5)
                    ui_round_card(frame,14,fill=frame.cget('bg'),border=C['border'])
            self._fit_height()

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
            label(w,title,size=17,bold=True).pack(anchor='w',padx=18,pady=(16,10))
            w.bind('<Escape>',lambda e:w.destroy())
            return w

        def ui_settings(self):
            w=self.ui_dialog('Character profile')
            form=ui_card(w)
            variables={}
            for key,title in [('profile_name','Name'),('character_class','Class'),('level','Level')]:
                label(form,title,bg='card',fg='muted').pack(anchor='w',padx=12,pady=(8,2))
                var=tk.StringVar(value=str(self.state.get(key,'')));variables[key]=var
                tk.Entry(form,textvariable=var,bg=C['header_dark'],fg=C['text'],font=(FONT,11),relief='flat').pack(fill='x',padx=12,ipady=6)
            feedback=label(form,'',fg='red',bg='card');feedback.pack(fill='x',padx=12)
            def save():
                try:
                    value=int(variables['level'].get())
                    if not 1<=value<=200:raise ValueError()
                except ValueError:feedback.config(text='Enter a level from 1 to 200');return
                self.state.update(profile_name=variables['profile_name'].get().strip()[:80],character_class=variables['character_class'].get().strip()[:80] or 'Adventurer')
                self.level.set(str(value));self.set_level();self.save_state();self._companion_profile_refresh();w.destroy()
            ui_button(form,'Save changes',save,primary=True).pack(fill='x',padx=12,pady=12)
            ui_button(w,'Opacity, text size, pinning and other settings',lambda:(w.destroy(),self.open_menu())).pack(fill='x',padx=18,pady=8)

        def ui_focus_search(self):
            if self.collapsed:self.toggle_collapse()
            self.global_entry.focus_set();self.global_entry.selection_range(0,'end')

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
            qid=self.focused() or next((q for q in self.state['active'] if q in self.db.quests),None)
            if qid:
                area=ScrollArea(w);area.pack(fill='both',expand=True)
                self.render_quest_guide(area.inner,'bg',qid,key='companion-overview:'+qid);area.commit()
            ui_button(w,'Open quest journal',lambda:(w.destroy(),self.ui_open_journal(qid)),primary=True).pack(fill='x',padx=18,pady=10)

        def open_add_dialog(self):
            w=self.ui_dialog('Add a quest');query=tk.StringVar()
            tk.Entry(w,textvariable=query,font=(FONT,11)).pack(fill='x',padx=18,ipady=6)
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
            box=tk.Entry(w,textvariable=name,font=(FONT,11));box.pack(fill='x',padx=18,ipady=6)
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
            w=self.ui_dialog('MesoWatch · price lookup')
            label(w,'MesoWatch is a separate price source. Open its website to look up prices; any price saved below is your manual note.',fg='muted',wraplength=420,justify='left').pack(fill='x',padx=18,pady=8)
            name=tk.StringVar(value=item_name);price=tk.StringVar()
            for title,var in [('Item name',name),('Your recorded price · mesos / unit',price)]:
                label(w,title,fg='muted').pack(anchor='w',padx=18,pady=(8,2))
                tk.Entry(w,textvariable=var,font=(FONT,11)).pack(fill='x',padx=18,ipady=6)
            feedback=label(w,'',wraplength=420,justify='left');feedback.pack(fill='x',padx=18,pady=10)
            def saved_note():
                record=self.state.get('companion_price_notes',{}).get(name.get().strip())
                feedback.config(text=f"Saved manual quote: {record['price']:,} mesos · {time.strftime('%d %b %H:%M',time.localtime(record['at']))}" if record else 'No recorded quote for this item.')
            def save():
                from companion_feature_model import utility_number
                try:value=int(utility_number(price.get()))
                except ValueError:feedback.config(text='Enter a valid mesos price.',fg=C['red']);return
                if not name.get().strip():feedback.config(text='Enter the item name.');return
                self.state.setdefault('companion_price_notes',{})[name.get().strip()[:120]]={'price':value,'at':time.time(),'source':'MesoWatch — manual user note'}
                self.save_state();saved_note()
            def copy_name():
                w.clipboard_clear();w.clipboard_append(name.get().strip());feedback.config(text='Item name copied. Paste it into MesoWatch search.')
            ui_button(w,'Open MesoWatch website ↗',lambda:webbrowser.open(MESOWATCH_URL),primary=True).pack(fill='x',padx=18,pady=6)
            ui_button(w,'Copy item name',copy_name).pack(fill='x',padx=18,pady=4)
            ui_button(w,'Save manual price note',save).pack(fill='x',padx=18,pady=6)
            ui_button(w,'Show saved note',saved_note).pack(fill='x',padx=18,pady=4)
            saved_note()

        def render_item_drops(self,card,bg,iid,item=None):
            super().render_item_drops(card,bg,iid,item)
            if item and item.get('name'):
                row=tk.Frame(card,bg=C[bg]);row.pack(fill='x',padx=8,pady=5)
                def prices():self.ui_market();self._market_search_query.set(item['name'])
                ui_button(row,'Market prices',prices,compact=True).pack(side='left',padx=3)
                ui_button(row,'MesoWatch ↗',lambda:self.ui_mesowatch(item['name']),compact=True).pack(side='left',padx=3)

        ui_market=market_open

    install_tools(CompanionApp)
    return CompanionApp
