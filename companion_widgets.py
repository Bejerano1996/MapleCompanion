from widgets import font_size
"""Maple Companion visual components, adapted for the Umbrale source project."""
import tkinter as tk
from PIL import Image,ImageDraw,ImageTk
from widgets import C,FONT,Tooltip

def ui_button(parent, text, command, primary=False, compact=False, tip=None):
    color = '#ed973f' if primary else C['card']
    ink = '#41240d' if primary else C['text']
    b = tk.Button(parent, text=text, command=command, bg=color, fg=ink, activebackground='#e88b2f' if primary else C['button'], activeforeground=ink, relief='flat', bd=0, cursor='hand2', font=(FONT, font_size(9), 'bold' if primary else 'normal'), padx=10 if compact else 14, pady=5 if compact else 8, highlightthickness=1, highlightbackground=color, highlightcolor=C['text'] if primary else C['gold'], takefocus=True)
    if tip:
        Tooltip(b, tip)
    return b

def ui_card(parent, padx=12, pady=8, radius=18):
    f = tk.Frame(parent, bg=C['card'], highlightbackground=C['border'], highlightcolor=C['border'], highlightthickness=1)
    f.pack(fill='x', padx=padx, pady=pady)
    ui_round_card(f, radius)
    return f

def ui_round_card(frame, radius=14, fill=None, border=None):
    if getattr(frame, '_rounded_corners', None):
        return
    try:
        background = frame.master.cget('bg')
    except tk.TclError:
        background = C['bg']
    scale = 4
    r = radius
    sheet = Image.new('RGB', (2 * r * scale, 2 * r * scale), background)
    draw = ImageDraw.Draw(sheet)
    draw.ellipse((0, 0, 2 * r * scale - 1, 2 * r * scale - 1), fill=fill or C['card'], outline=border or C['border'], width=scale)
    corners = [(0, 0, 'nw', (0, 0, r * scale, r * scale)), (1, 0, 'ne', (r * scale, 0, 2 * r * scale, r * scale)), (0, 1, 'sw', (0, r * scale, r * scale, 2 * r * scale)), (1, 1, 'se', (r * scale, r * scale, 2 * r * scale, 2 * r * scale))]
    frame._rounded_corners = []
    for rx, ry, anchor, box in corners:
        photo = ImageTk.PhotoImage(sheet.crop(box).resize((r, r), Image.Resampling.LANCZOS), master=frame)
        corner = tk.Label(frame, image=photo, bg=background, bd=0, padx=0, pady=0)
        corner.image = photo
        corner.place(relx=rx, rely=ry, x=1 if rx else -1, y=1 if ry else -1, anchor=anchor)
        frame._rounded_corners.append(corner)
    def release_corners(event):
        if event.widget != frame:return
        for corner in frame._rounded_corners:
            corner.image=None
        frame._rounded_corners=[]
    frame.bind('<Destroy>',release_corners,add='+')

def ui_nav_icon(master, key, selected=False):
    scale, size = 4, 20
    icon = Image.new('RGBA', (size*scale, size*scale), (0, 0, 0, 0))
    pen = ImageDraw.Draw(icon)
    ink = C['icon_active'] if selected else C['icon']
    def line(points, width=1.25):
        pen.line([(int(x*scale),int(y*scale)) for x,y in points], fill=ink, width=max(1,int(width*scale)), joint='curve')
    def oval(box, fill=None):
        pen.ellipse(tuple(int(x*scale) for x in box), outline=ink, fill=fill, width=scale)
    def rect(box, radius=1.5):
        pen.rounded_rectangle(tuple(int(x*scale) for x in box), radius=int(radius*scale), outline=ink, width=scale)
    if selected:
        pen.rounded_rectangle((0,0,size*scale-1,size*scale-1),radius=6*scale,fill=C['button'])
    if key == 'home':
        line([(3,9),(10,3),(17,9)]);line([(5,8),(5,17),(15,17),(15,8)]);line([(8,17),(8,12),(12,12),(12,17)])
    elif key == 'quests':
        rect((4,4,16,17));rect((7,2,13,6));line([(7,11),(9,13),(13,9)])
    elif key == 'map':
        oval((5,2,15,12));line([(5.5,10),(10,18),(14.5,10)]);oval((8.5,5.5,11.5,8.5))
    elif key == 'mobs':
        pen.arc((3*scale,4*scale,17*scale,20*scale),180,360,fill=ink,width=scale);line([(3,12),(3,16),(17,16),(17,12)]);oval((7,10,8,11),ink);oval((12,10,13,11),ink)
    elif key == 'train':
        line([(3,16),(8,11),(11,13),(17,5)]);line([(12,5),(17,5),(17,10)])
    elif key == 'items':
        rect((4,6,16,17));pen.arc((7*scale,2*scale,13*scale,10*scale),180,360,fill=ink,width=scale);line([(7,7),(7,9)]);line([(13,7),(13,9)])
    elif key == 'pq':
        oval((7,2,13,8));oval((1,5,5,9));oval((15,5,19,9))
        line([(5,18),(5,14),(7,11),(13,11),(15,14),(15,18)])
        line([(1,16),(1,13),(3,11),(5,12)])
        line([(19,16),(19,13),(17,11),(15,12)])
    elif key == 'money':
        oval((2,7,12,17));oval((8,2,18,12));line([(13,4),(13,10)]);line([(11,6),(15,6)]);line([(7,9),(7,15)])
    elif key == 'tools':
        for x,y in ((3,3),(11,3),(3,11),(11,11)):rect((x,y,x+6,y+6))
    elif key == 'settings':
        oval((3,3,17,17));oval((7,7,13,13))
        for a,b in [((10,0),(10,4)),((10,16),(10,20)),((0,10),(4,10)),((16,10),(20,10))]:line([a,b])
    elif key == 'watch':
        line([(10,2),(12.3,7),(18,8),(14,12),(15,18),(10,15),(5,18),(6,12),(2,8),(7.7,7),(10,2)])
    else:
        oval((3,3,13,13));line([(12,12),(18,18)],1.5)
    return ImageTk.PhotoImage(icon.resize((size,size),Image.Resampling.LANCZOS),master=master)

def ui_walk_widgets(parent):
    for child in parent.winfo_children():
        yield child
        yield from ui_walk_widgets(child)

def ui_tools_icon(master, due=False):
    scale=4
    icon=Image.new('RGBA',(16*scale,16*scale),(0,0,0,0))
    pen=ImageDraw.Draw(icon)
    ink=C['icon_active'] if due else C['icon']
    for x,y in ((2,2),(9,2),(2,9),(9,9)):
        pen.rounded_rectangle((x*scale,y*scale,(x+5)*scale,(y+5)*scale),radius=scale,outline=ink,width=scale)
    if due:
        pen.ellipse((10*scale,10*scale,16*scale-1,16*scale-1),fill='#ed973f',outline=C['header'],width=scale)
    return ImageTk.PhotoImage(icon.resize((16,16),Image.Resampling.LANCZOS),master=master)
