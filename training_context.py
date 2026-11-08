"""Read-only training context; visible roster/mobs are evidence, not kill telemetry."""
import re,time

def key(text):return re.sub(r'[^a-z0-9]','',str(text).casefold())

def plausible_monsters(identities,map_id,map_data):
    """Reject labels outside indexed normal spawns; unknown metadata stays unknown."""
    record=map_data.get(map_id)
    spawns=record.get('monsters') if isinstance(record,dict) else None
    if not isinstance(spawns,list) or any(not isinstance(row,dict) or row.get('id') is None for row in spawns):
        return list(identities)
    allowed={str(row['id']) for row in spawns}
    return [identity for identity in identities if str(identity) in allowed]

def visible_monsters(lines,monsters):
    found=[]
    for line in lines:
        match=re.match(r'\s*Lv[\s.,:]*(\d{1,3})\s*(.+)',line['text'],re.I)
        if not match or line.get('score',1)<.85:continue
        hits=[m for m in monsters.values() if m.get('level')==int(match[1]) and key(m.get('display') or m['name'])==key(match[2])]
        if len(hits)==1 and hits[0]['id'] not in found:found.append(hits[0]['id'])
    return found

class ContextTracker:
    def __init__(self):self.pending_map=None;self.pending_party=None;self.data={}
    def feed(self,reading,now):
        if not reading or not reading.get('game'):
            self.pending_map=None;self.pending_party=None;self.data={'game':False,'map':None,'party_visible':None,'mobs':[],'at':now};return self.data
        result=dict(self.data,game=True,at=now,mobs=reading.get('mobs',[]),mobs_at=now,map_readable=bool(reading.get('map')),party_readable=reading.get('party_visible') is not None,map_blocked=reading.get('map_blocked',False))
        map_id=reading.get('map')
        if map_id:
            if map_id==self.pending_map:result.update(map=map_id,map_at=now)
            elif map_id!=result.get('map'):result.update(map=None,map_at=None)
        self.pending_map=map_id
        party=reading.get('party_visible')
        if party is not None and 2<=party<=6:
            if party==self.pending_party:result.update(party_visible=party,party_at=now)
            else:result.update(party_visible=None)
        self.pending_party=party
        for field,stamp in (('map','map_at'),('party_visible','party_at')):
            if result.get(stamp) is None or now-result[stamp]>20:result[field]=None
        self.data=result;return result

def party_rows(image,lines):
    """Count aligned visible HP rows with a readable roster-name anchor."""
    import cv2,numpy as np
    rgb=np.asarray(image.convert('RGB'));r,g,b=[rgb[:,:,i].astype('int16') for i in range(3)]
    mask=((r>140)&(r>g*1.5)&(r>b*1.5)).astype('uint8')*255
    contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    h,w=mask.shape;bars=[]
    for contour in contours:
        x,y,bw,bh=cv2.boundingRect(contour)
        if not (10<=bw<=w*.65 and 2<=bh<=max(20,h*.06) and bw/bh>=1.2):continue
        cy=y+bh/2
        names=[l for l in lines if l.get('score',0)>=.85 and re.fullmatch(r'[A-Za-z][A-Za-z0-9]{2,19}',l['text'].strip()) and abs(l['y']+l['h']/2-cy)<=max(bh*1.5,12) and 0<x-(l['x']+l['w'])<w*.65]
        bars.append((x,cy,bool(names)))
    best=[]
    for left,_,_ in bars:
        group=[(y,named) for start,y,named in bars if abs(start-left)<=5]
        if not any(named for _,named in group):continue
        ys=sorted({round(y) for y,_ in group})
        unique=[]
        for y in ys:
            if not unique or y-unique[-1]>6:unique.append(y)
        if 2<=len(unique)<=6:
            gaps=[b-a for a,b in zip(unique,unique[1:])]
            if min(gaps)>=8 and max(gaps)<=max(45,h*.13) and max(gaps)<=min(gaps)*1.6 and len(unique)>len(best):best=unique
    return len(best) if best else None

_engine=None
def roman_suffix(image):
    """Count separated narrow I glyphs in the minimap's second text row."""
    import cv2,numpy as np
    a=np.asarray(image.convert('RGB'));height=image.height
    contours,_=cv2.findContours((a.min(axis=2)>=180).astype('uint8')*255,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    rects=sorted([cv2.boundingRect(c) for c in contours])
    rects=[r for r in rects if height*.45<=r[1]<=height*.8 and max(5,height*.1)<=r[3]<=height*.4]
    if not rects:return None
    last=rects[-1];count=0
    for rect in reversed(rects):
        x,y,w,h=rect
        if w>h*.4 or abs(y-last[1])>2 or abs(h-last[3])>2:break
        if count and last[0]-(x+w)>h*.23:break
        count+=1;last=rect
    return 'I'*count if 1<=count<=6 else None

def map_from_title(title,maps):
    import sync
    from difflib import SequenceMatcher
    lines=context_lines(title)
    found=sync.match_map(lines,maps) if lines and maps else None
    if not found:return None
    record=maps.get(found,{})
    digits=re.findall(r'\d+',record.get('displayName',''))
    if digits and not all(any(number in re.findall(r'\d+',l['text']) for l in lines) for number in digits):return None
    variant=re.fullmatch(r'(.+?) (I{1,6})',record.get('displayName',''))
    if not variant:return found
    suffix=roman_suffix(title)
    if not suffix:return None
    base=key(variant[1])
    if not any(SequenceMatcher(None,key(l['text'])[:len(base)],base).ratio()>=.85 for l in lines):return None
    choices=[m['id'] for m in maps.values() if m.get('displayName')==variant[1]+' '+suffix and m.get('displayStreet')==record.get('displayStreet')]
    return choices[0] if len(choices)==1 else None

def context_lines(image):
    global _engine
    import numpy as np
    if _engine is None:
        from rapidocr_onnxruntime import RapidOCR
        _engine=RapidOCR(intra_op_num_threads=1,inter_op_num_threads=1)
    image=image.convert('RGB');original=image.size;image.thumbnail((1600,900))
    if image.width<640:image=image.resize((image.width*3,image.height*3))
    rows,_=_engine(np.asarray(image)[:,:,::-1],use_cls=False)
    sx,sy=original[0]/image.width,original[1]/image.height
    return [dict(text=t,score=float(c),x=min(p[0] for p in box)*sx,y=min(p[1] for p in box)*sy,w=(max(p[0] for p in box)-min(p[0] for p in box))*sx,h=(max(p[1] for p in box)-min(p[1] for p in box))*sy) for box,t,c in rows or []]

def capture_context(maps,monsters,hide=()):
    from PIL import ImageGrab,ImageDraw
    from game_sync import find_game_window,find_minimap,minimap_title
    box=find_game_window()
    if not box:return {'game':False}
    captured_at=time.time()
    x,y,right,bottom=box;image=ImageGrab.grab(bbox=box,all_screens=True).convert('RGB');w,h=image.size
    covers=[(l-x,t-y,r-x,b-y) for l,t,r,b in hide]
    report={};frame=find_minimap(image,covers,report);draw=ImageDraw.Draw(image)
    if frame and any(r>frame[0] and l<frame[2] and b>frame[1] and t<frame[3] for l,t,r,b in covers):frame=None;report['blocked']=True
    for rect in covers:draw.rectangle(rect,fill='black')
    title=minimap_title(image,frame) if frame else None
    map_id=map_from_title(title,maps) if title else None
    roster=image.crop((int(w*.65),int(h*.04),w,int(h*.45)))
    count=party_rows(roster,context_lines(roster))
    mobs=[]
    for left in (0,.31,.62):
        scene=image.crop((int(w*left),int(h*.18),min(w,int(w*(left+.38))),int(h*.88)))
        for mob in visible_monsters(context_lines(scene),monsters):
            if mob not in mobs:mobs.append(mob)
    return dict(game=True,map=map_id,party_visible=count,mobs=mobs,captured_at=captured_at,map_blocked=bool(report.get('blocked')))

def context_poll(self):
    session=self.state['utility_session']
    if session.get('running_since') is None or not self.state.get('training_auto_context',True) or not self.db.maps:return
    if getattr(self,'_context_busy',False) or time.monotonic()-getattr(self,'_context_last_poll',-100)<8:return
    import tkinter as tk
    from game_sync import window_rect
    from session_rewards import session_token
    windows=[self.root]+[v for v in self.root.winfo_children() if isinstance(v,tk.Toplevel)]
    hide=[window_rect(v) for v in windows if v.winfo_viewable()]
    token=session_token(session);self._context_busy=True;self._context_last_poll=time.monotonic()
    if getattr(self,'_context_scope',None)!=token:
        self._context_tracker=ContextTracker();self._context_scope=token
        self._training_party_seen_at=0
        self._training_context=dict(game=True,at=time.time(),map=None,mobs=[],party_visible=None)
    def loaded(reading):
        self._context_busy=False
        if token!=session_token(self.state['utility_session']) or not self.state.get('training_auto_context',True):return
        data=self._context_tracker.feed(reading,reading.get('captured_at',time.time()));self._training_context=data
        seen=self.state['utility_session'].setdefault('observed_monsters',{})
        for mob in data.get('mobs',[]):
            if len(seen)<40 or str(mob) in seen:seen[str(mob)]={'last_seen':data['at'],'map':data.get('map')}
        if data.get('map'):
            if self.state.get('map')!=str(data['map']):self.set_location(str(data['map']))
            self._live_last_result={'_minimap_readable':True}
        elif not reading.get('map'):self._live_last_result={'_minimap_readable':False}
        if getattr(self,'_utility_refresh',None):self._utility_refresh()
        self.render_levelup()
    def failed(error):
        self._context_busy=False;self._context_error=str(error)[:100]
    self.run_bg(lambda:capture_context(self.db.maps,self.db.monsters,hide),loaded,on_error=failed)

def context_summary(self):
    data=getattr(self,'_training_context',{});now=time.time()
    if not data:return 'Map / party / mobs · waiting for screen reading'
    if not data.get('game') or now-data.get('at',0)>20:return 'Game context unavailable · last session totals retained'
    map_id=data.get('map') if now-(data.get('map_at') or 0)<=20 else None
    record=self.db.maps.get(str(map_id),{})
    map_name=(record.get('displayName') or record.get('name') or map_id) if map_id else 'Map unreadable'
    if data.get('map_blocked'):map_name='Minimap covered · move overlay away'
    party=data.get('party_visible') if data.get('party_readable') and now-(data.get('party_at') or 0)<=20 else None
    party_text=f'Party · {party} visible members' if party else ('Party detected · member count unreadable' if now-getattr(self,'_training_party_seen_at',0)<20 else 'Party size unknown · roster must be visible')
    names=[self.db.monsters[i].get('display') or self.db.monsters[i]['name'] for i in data.get('mobs',[]) if i in self.db.monsters]
    return ('' if data.get('map_readable') else 'Last map · ')+str(map_name)+'\n'+party_text+'\n'+('Visible mobs · '+', '.join(names[:3]) if names else 'No readable monster labels')
