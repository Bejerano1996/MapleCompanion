"""Compact per-objective map suggestions. Clicking a map uses the native GPS."""
import tkinter as tk
from widgets import C,label,button,link,Tooltip,ScrollArea
from monster_locations import monster_locations

def objective_monsters(self,need,step):
    rows={}
    if need.get('mobId') is not None:rows[str(need['mobId'])]={'mob':need['mobId'],'maps':[]}
    for line in step.get('lines',[]):
        if line.get('mob') is not None:
            key=str(line['mob'])
            rows.setdefault(key,{'mob':line['mob'],'maps':[]})['maps'].extend(line.get('maps') or [])
    return list(rows.values())

def render_objective_map_sort(self,parent,bg):
    row=tk.Frame(parent,bg=C[bg]);row.pack(fill='x',pady=(2,5))
    label(row,'Maps',bg=bg,fg='muted',size=8).pack(side='left')
    selected=self.state.get('objective_map_sort','mobs')
    for key,title in [('mobs','Spawn'),('near','Nearest')]:
        button(row,title,lambda key=key:self.set_objective_map_sort(key),bg='button' if key==selected else bg,
               fg='gold' if key==selected else 'muted',size=8,padx=5,
               tip='Most known spawn points first' if key=='mobs' else 'Fewest portal steps from your current map').pack(side='left',padx=3)

def set_objective_map_sort(self,sort):
    if sort not in ('mobs','near'):return
    self.state['objective_map_sort']=sort;self.save_state();self.render()

def monster_map_rows(self,group):
    return monster_locations(self.db.map_data,self.db.maps,group['mob'],self.distances(),group.get('maps',()),self.state.get('objective_map_sort','mobs'))

def render_monster_map_row(self,parent,bg,qid,row):
    box=tk.Frame(parent,bg=C[bg]);box.pack(fill='x',padx=(18,4),pady=(0,3))
    destination=link(box,row['name'],lambda:self.start_route(qid,row['map'],row['mob']),bg=bg,
                     fg='green' if row['distance']==0 else 'link',size=8,anchor='w',justify='left',wraplength=max(140,self.wrap(95)))
    destination.pack(fill='x')
    spawn='—' if row['spawn'] is None else f"{row['spawn']:g}"
    distance='Here' if row['distance']==0 else f"{row['distance']} portals" if row['distance'] is not None else 'Route unknown'
    label(box,f'Spawn {spawn} · {distance}',bg=bg,fg='muted',size=7,anchor='w').pack(fill='x')
    Tooltip(destination,'Open GPS to this map. Spawn is the known number of spawn points, not a live on-screen monster count. Distance uses known portal routes from your current map.')

def toggle_objective_maps(self,key):
    opened=getattr(self,'_objective_maps_open',set())
    opened.symmetric_difference_update({key});self._objective_maps_open=opened;self.render()

def render_objective_monster_maps(self,parent,bg,qid,index,need,step,done):
    groups=objective_monsters(self,need,step)
    if not groups:return
    key=(qid,index)
    if done and key not in getattr(self,'_objective_maps_open',set()):
        link(parent,'▸ Maps',lambda:toggle_objective_maps(self,key),bg=bg,fg='muted',size=7).pack(anchor='w',padx=18,pady=(0,3))
        return
    for group in groups:
        rows=monster_map_rows(self,group)
        if need.get('mobId') is None:
            info=self.db.monsters.get(int(group['mob'])) or {}
            label(parent,'Drops from '+str(info.get('display') or group['mob']),bg=bg,fg='muted',size=8).pack(anchor='w',padx=18)
        if not rows:
            label(parent,'No map data yet',bg=bg,fg='muted',size=7).pack(anchor='w',padx=18)
        for row in rows[:3]:render_monster_map_row(self,parent,bg,qid,row)
        if len(rows)>3:
            link(parent,f'All maps ({len(rows)})…',lambda group=group:self.open_monster_maps(qid,group),bg=bg,size=7).pack(anchor='w',padx=18,pady=(0,4))
    if done:link(parent,'▴ Hide maps',lambda:toggle_objective_maps(self,key),bg=bg,fg='muted',size=7).pack(anchor='w',padx=18)

def open_monster_maps(self,qid,group):
    info=self.db.monsters.get(int(group['mob'])) or {}
    window=self.ui_dialog('Maps · '+str(info.get('display') or group['mob']))
    controls=tk.Frame(window,bg=C['bg']);controls.pack(fill='x',padx=14,pady=4)
    area=ScrollArea(window);area.pack(fill='both',expand=True)
    buttons={};signature=[None]
    def draw(sort=None):
        if sort:self.state['objective_map_sort']=sort;self.save_state();self.render()
        current=self.state.get('objective_map_sort','mobs')
        for key,control in buttons.items():control.config(text=('✓ ' if key==current else '')+('Spawn' if key=='mobs' else 'Nearest'))
        area.clear(False)
        for row in monster_map_rows(self,group):render_monster_map_row(self,area.inner,'bg',qid,row)
        area.commit()
        signature[0]=(self.state.get('map'),current,self.cabs())
    for key,title in [('mobs','Spawn'),('near','Nearest')]:
        buttons[key]=button(controls,title,lambda key=key:draw(key),size=9)
        buttons[key].pack(side='left',padx=3)
    job=[None]
    def refresh():
        if not window.winfo_exists():return
        if signature[0]!=(self.state.get('map'),self.state.get('objective_map_sort','mobs'),self.cabs()):draw()
        job[0]=window.after(1000,refresh)
    def cleanup(event):
        if event.widget is window and job[0]:
            try:window.after_cancel(job[0])
            except tk.TclError:pass
            job[0]=None
    window.bind('<Destroy>',cleanup,add='+')
    draw()
    job[0]=window.after(1000,refresh)

def install_monster_maps(cls):
    for name,fn in [('render_objective_map_sort',render_objective_map_sort),('set_objective_map_sort',set_objective_map_sort),
                    ('render_objective_monster_maps',render_objective_monster_maps),('open_monster_maps',open_monster_maps)]:setattr(cls,name,fn)
