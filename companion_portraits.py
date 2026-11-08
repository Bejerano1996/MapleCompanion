"""Small cached portraits, fetched off the UI thread from the existing database."""
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from pathlib import Path
from io import BytesIO
import queue
import re
import tkinter as tk
from PIL import Image, ImageTk
from widgets import Tooltip

class NpcImageParser(HTMLParser):
    def __init__(self,name):super().__init__();self.name=name.casefold();self.path=None
    def handle_starttag(self,tag,attrs):
        a=dict(attrs);src=a.get('src','')
        if tag=='img' and a.get('alt','').casefold()==self.name and re.fullmatch(r'/msclassic/npcs/[a-z0-9-]+\.webp',src):self.path=src

def fetch_portrait(db,kind,identity,name):
    if kind not in ('mob','npc') or not str(identity).isdigit():raise ValueError('Invalid portrait')
    cache=Path(db.cache_dir)/'portraits';cache.mkdir(exist_ok=True)
    file=cache/(kind+'-'+str(identity)+'.png')
    if file.is_file():
        with Image.open(file) as im:return im.convert('RGBA')
    if kind=='mob':path=f'/msclassic/monsters/sprites/mob_{identity}.png'
    else:
        parser=NpcImageParser(name);parser.feed(db._get('/npcs/'+str(identity),30*86400));path=parser.path
        if not path:return None
    raw=db._fetch(path.removeprefix("/msclassic"))
    if len(raw)>2000000:raise ValueError('Portrait too large')
    with Image.open(BytesIO(raw)) as im:
        if im.width>2048 or im.height>2048:raise ValueError('Portrait dimensions too large')
        image=im.convert('RGBA')
    image.save(file);return image

class Portraits:
    def __init__(self,app):
        self.app=app;self.root=app.root;self.images={};self.pending={};self.failed=set();self.results=queue.Queue();self.pool=ThreadPoolExecutor(max_workers=2,thread_name_prefix='portraits')
        self.job=self.root.after(100,self.drain);self.root.bind('<Destroy>',self.close,add='+')
    def close(self,event):
        if event.widget==self.root:
            self.root.after_cancel(self.job);self.pool.shutdown(wait=False,cancel_futures=True)
    def attach(self,parent,kind,identity,name,bg,size=30):
        if identity is None:return None
        key=(kind,str(identity),size)
        view=tk.Label(parent,bg=bg,bd=0,padx=0,pady=0)
        view.pack(side='left',padx=(4,5))
        Tooltip(view,name)
        if key in self.images:view.config(image=self.images[key]);view.image=self.images[key]
        elif key not in self.failed:
            self.pending.setdefault(key,[]).append(view)
            if len(self.pending[key])==1:
                future=self.pool.submit(fetch_portrait,self.app.db,kind,identity,name)
                def done(f):
                    try:result=f.result()
                    except Exception:result=None
                    self.results.put((key,result))
                future.add_done_callback(done)
        return view
    def drain(self):
        for _ in range(20):
            try:key,image=self.results.get_nowait()
            except queue.Empty:break
            views=self.pending.pop(key,[])
            if image is None:
                self.failed.add(key)
                for v in views:
                    if v.winfo_exists():v.destroy()
                continue
            image.thumbnail((key[2]-4,key[2]-4),Image.Resampling.NEAREST)
            canvas=Image.new('RGBA',(key[2],key[2]));canvas.alpha_composite(image,((key[2]-image.width)//2,(key[2]-image.height)//2))
            photo=ImageTk.PhotoImage(canvas,master=self.root);self.images[key]=photo
            if len(self.images)>160:self.images.pop(next(iter(self.images)))
            for v in views:
                if v.winfo_exists():v.config(image=photo);v.image=photo
        self.job=self.root.after(100,self.drain)

def portrait(app,parent,kind,identity,name,bg,size=30):
    if not hasattr(app,'_portraits'):app._portraits=Portraits(app)
    return app._portraits.attach(parent,kind,identity,name,bg,size)
