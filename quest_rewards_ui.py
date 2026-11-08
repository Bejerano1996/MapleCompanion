import tkinter as tk
from widgets import C,label,button,ScrollArea,Tooltip
from quest_rewards import reward_summary,reward_sections

def render_quest_rewards(self,parent,bg,qid):
    row=tk.Frame(parent,bg=C[bg]);row.pack(fill='x',padx=12,pady=(0,4))
    button(row,'Rewards…',lambda:self.open_quest_rewards(qid),bg=bg,fg='gold',size=8,padx=3,
           tip='All rewards, including random and selectable items').pack(side='right')
    info=label(row,reward_summary(self.db.quests[qid]),bg=bg,fg='muted',size=7,anchor='w',justify='left',wraplength=max(140,self.wrap(130)))
    info.pack(side='left',fill='x',expand=True)
    Tooltip(info,'Click Rewards for the complete list. Random items and selectable rewards are not all guaranteed.')

def open_quest_rewards(self,qid):
    quest=self.db.quests[qid]
    window=self.ui_dialog('Rewards · '+quest['name'])
    area=ScrollArea(window);area.pack(fill='both',expand=True)
    sections=reward_sections(quest)
    if not sections:label(area.inner,'No reward listed',fg='muted').pack(anchor='w',padx=14,pady=8)
    for section in sections:
        label(area.inner,section['title'],bold=True,fg='gold',size=10,wraplength=410,justify='left').pack(anchor='w',padx=14,pady=(10,4))
        for text in section['rows']:label(area.inner,text,size=10,wraplength=410,justify='left').pack(anchor='w',padx=18,pady=3)
    area.commit()

def install_quest_rewards(cls):
    cls.render_quest_rewards=render_quest_rewards
    cls.open_quest_rewards=open_quest_rewards
