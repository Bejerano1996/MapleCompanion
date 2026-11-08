"""CPU-only local OCR of the game's visible lower-right reward log. No network or inputs."""
from session_rewards import reward_event,reward_kind
_engine=None
_money_retry_turn=0

class RewardRead(list):
    """Visible notices from a partially masked region."""
    def __init__(self,events=(),partial=True,trusted_money=(),positions=()):
        super().__init__(events);self.partial=partial;self.trusted_money=set(trusted_money);self.positions=list(positions)

def ocr_rows(image,max_size=(1280,720)):
    global _engine
    import numpy as np
    if _engine is None:
        import onnxruntime
        onnxruntime.disable_telemetry_events()
        from rapidocr_onnxruntime import RapidOCR
        _engine=RapidOCR(intra_op_num_threads=1,inter_op_num_threads=1)
    image=image.convert('RGB');image.thumbnail(max_size)
    if image.width<640:
        image=image.resize((image.width*3,image.height*3))
    rows,_=_engine(np.asarray(image)[:,:,::-1],use_cls=False)
    return rows or []

def retry_money_row(image,position):
    """Bounded recognition-only fallback; two views must agree, never trusted money."""
    if _engine is None:return None
    import numpy as np
    from PIL import ImageOps
    y,h=position
    size=image.copy();size.thumbnail((1280,720))
    scale=size.height/image.height
    if size.width<640:scale*=3
    top=max(0,int((y-h*.8)/scale));bottom=min(image.height,int((y+h*.8)/scale)+1)
    if bottom<=top:return None
    crop=image.crop((0,top,image.width,bottom)).convert('RGB')
    values=[]
    try:
        for view in (crop,ImageOps.autocontrast(crop)):
            rows,_=_engine(np.asarray(view)[:,:,::-1],use_det=False,use_cls=False)
            if not rows or len(rows)!=1:return None
            text,score=rows[0];event=reward_event(text)
            if score<.9 or not event or event[0]!='mesos':return None
            values.append(event[1])
    except Exception:
        # Optional recovery must not discard the normal detector's valid rows.
        return None
    return values[0] if values[0]==values[1] else None


def read_reward_image(image,include_pending=False):
    global _money_retry_turn
    rows=ocr_rows(image)
    # Merge boxes on the same line: the detector can split "You" from the amount.
    groups=[]
    for box,text,score in sorted(rows or [],key=lambda row:min(p[1] for p in row[0])):
        y=sum(p[1] for p in box)/4;h=max(p[1] for p in box)-min(p[1] for p in box)
        group=next((g for g in groups if abs(g['y']-y)<max(5,min(g['h'],h)*.45)),None)
        if group is None:group={'y':y,'h':h,'parts':[]};groups.append(group)
        group['parts'].append((min(p[0] for p in box),text,score))
    result=[];trusted_money=[];positions=[]
    for group in sorted(groups,key=lambda g:g['y']):
        parts=sorted(group['parts']);text=' '.join(p[1] for p in parts)
        score=sum(len(p[1])*p[2] for p in parts)/max(1,sum(len(p[1]) for p in parts))
        # A long clear prefix must not hide an uncertain numeric OCR box.
        amount_score=min((p[2] for p in parts if any(c.isdigit() for c in p[1])),default=score)
        event=reward_event(text)
        if event and score>=.75 and amount_score>=.75:
            if event[0]=='mesos' and score>=.95 and amount_score>=.95:trusted_money.append(len(result))
            result.append(event)
            positions.append((group['y'],group['h']))
        elif include_pending and score>=.7:
            kind=reward_kind(text)
            if kind:
                result.append((kind,None));positions.append((group['y'],group['h']))
    if include_pending:
        pending=[index for index,event in enumerate(result) if event==('mesos',None)]
        if pending:
            # Two consecutive attempts allow the normal across-poll confirmation.
            index=pending[(_money_retry_turn//2)%len(pending)]
            _money_retry_turn=(_money_retry_turn+1)%(2*len(pending))
            amount=retry_money_row(image,positions[index])
            if amount is not None:result[index]=('mesos',amount)
        else:_money_retry_turn=0
    return RewardRead(result,partial=False,trusted_money=trusted_money,positions=positions)

def capture_rewards(hide=()):
    from game_sync import find_game_window
    from PIL import ImageGrab,ImageDraw
    box=find_game_window()
    if box is None:return None
    x,y,right,bottom=box;w=right-x;h=bottom-y
    # Keep the floating reward notices large enough for OCR at 1080p/1440p.
    # The previous wide scene crop left their small glyphs at native resolution.
    crop=(x+int(w*.70),y+int(h*.60),right,y+int(h*.91))
    # A covered log is unavailable, not an empty log: do not recount old pickups on uncover.
    # Floating notices sit above the quick-slot/HUD area. A tools window
    # touching only the scene above them must not disable the entire reader.
    log=(x+int(w*.70),y+int(h*.70),right,y+int(h*.83))
    partial=any(r>log[0] and left<log[2] and b>log[1] and top<log[3] for left,top,r,b in hide)
    if partial:
        from PIL import Image
        visible=Image.new('L',(log[2]-log[0],log[3]-log[1]),255)
        mask=ImageDraw.Draw(visible)
        for left,top,r,b in hide:
            if r>log[0] and left<log[2] and b>log[1] and top<log[3]:
                mask.rectangle((max(0,left-log[0]),max(0,top-log[1]),min(visible.width,r-log[0]),min(visible.height,b-log[1])),fill=0)
        if visible.getbbox() is None:return None
    image=ImageGrab.grab(bbox=crop,all_screens=True).convert('RGB')
    draw=ImageDraw.Draw(image)
    for left,top,r,b in hide:
        if r>crop[0] and left<crop[2] and b>crop[1] and top<crop[3]:
            draw.rectangle((max(0,left-crop[0]),max(0,top-crop[1]),min(image.width,r-crop[0]),min(image.height,b-crop[1])),fill='black')
    events=read_reward_image(image,include_pending=True)
    if partial:
        if isinstance(events,RewardRead):events.partial=True
        else:events=RewardRead(events)
    return events


def read_character_image(image):
    from training_model import character_reading
    rows=ocr_rows(image,max_size=(1800,300))
    return character_reading([text for box,text,score in rows if score>=.75])

def wallet_from_rows(rows):
    import re
    from wallet_model import balance
    if not any('iteminventory' in re.sub(r'\W','',t.lower()) for _,t,c in rows if c>=.85):return None
    candidates=[]
    for box,text,score in rows:
        if score<.85 or text.strip().upper()!='MESOS':continue
        y=sum(p[1] for p in box)/4;left=min(p[0] for p in box);height=max(p[1] for p in box)-min(p[1] for p in box)
        for b,t,c in rows:
            if c<.97 or not re.fullmatch(r'(?:0|[1-9]\d{0,2}(?:,\d{3})*|[1-9]\d*)',t.strip()):continue
            if abs(sum(p[1] for p in b)/4-y)>max(8,height*.7):continue
            gap=left-max(p[0] for p in b)
            if not 0<=gap<=height*4:continue
            try:candidates.append(balance(t))
            except ValueError:pass
    return candidates[0] if len(set(candidates))==1 else None

def capture_wallet(hide=()):
    from game_sync import find_game_window
    from PIL import ImageGrab,ImageDraw
    box=find_game_window()
    if not box:return None
    x,y,r,b=box;crop=(x+int((r-x)*.70),y,r,y+int((b-y)*.65))
    image=ImageGrab.grab(bbox=crop,all_screens=True).convert('RGB')
    draw=ImageDraw.Draw(image)
    for left,top,right,bottom in hide:
        if right>crop[0] and left<crop[2] and bottom>crop[1] and top<crop[3]:
            draw.rectangle((max(0,left-crop[0]),max(0,top-crop[1]),min(image.width,right-crop[0]),min(image.height,bottom-crop[1])),fill='black')
    return wallet_from_rows(ocr_rows(image))

def capture_training(hide=(),read_status=True,read_wallet=False):
    # Reward log and HUD are independent sources; a covered log must not hide a clear HUD.
    events=capture_rewards(hide)
    reading=None
    if read_status:
        from game_sync import find_game_window
        from PIL import ImageGrab
        box=find_game_window()
        if box:
            x,y,right,bottom=box;w=right-x;h=bottom-y
            crop=(x+int(w*.1),y+int(h*.91),x+int(w*.92),bottom)
            covered=any(r>crop[0] and left<crop[2] and b>crop[1] and top<crop[3] for left,top,r,b in hide)
            if not covered:reading=read_character_image(ImageGrab.grab(bbox=crop,all_screens=True).convert('RGB'))
    result={'events':events,'character':reading}
    if read_wallet:result['wallet']=capture_wallet(hide)
    return result
