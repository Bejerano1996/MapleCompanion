"""CPU-only local OCR of the game's visible lower-right reward log. No network or inputs."""
from session_rewards import reward_event,reward_kind
_engine=None

def read_reward_image(image,include_pending=False):
    global _engine
    import numpy as np
    if _engine is None:
        import onnxruntime
        onnxruntime.disable_telemetry_events()
        from rapidocr_onnxruntime import RapidOCR
        _engine=RapidOCR(intra_op_num_threads=1,inter_op_num_threads=1)
    image=image.convert('RGB');image.thumbnail((1280,720))
    if image.width<640:
        image=image.resize((image.width*3,image.height*3))
    rows,_=_engine(np.asarray(image)[:,:,::-1],use_cls=False)
    # Merge boxes on the same line: the detector can split "You" from the amount.
    groups=[]
    for box,text,score in sorted(rows or [],key=lambda row:min(p[1] for p in row[0])):
        y=sum(p[1] for p in box)/4;h=max(p[1] for p in box)-min(p[1] for p in box)
        group=next((g for g in groups if abs(g['y']-y)<max(5,min(g['h'],h)*.45)),None)
        if group is None:group={'y':y,'h':h,'parts':[]};groups.append(group)
        group['parts'].append((min(p[0] for p in box),text,score))
    result=[]
    for group in sorted(groups,key=lambda g:g['y']):
        parts=sorted(group['parts']);text=' '.join(p[1] for p in parts)
        score=sum(len(p[1])*p[2] for p in parts)/max(1,sum(len(p[1]) for p in parts))
        event=reward_event(text)
        if event and score>=.75:result.append(event)
        elif include_pending and score>=.7:
            kind=reward_kind(text)
            if kind:result.append((kind,None))
    return result

def capture_rewards(hide=()):
    from game_sync import find_game_window
    from PIL import ImageGrab,ImageDraw
    box=find_game_window()
    if box is None:return None
    x,y,right,bottom=box;w=right-x;h=bottom-y
    crop=(x+int(w*.60),y+int(h*.50),right,y+int(h*.95))
    # A covered log is unavailable, not an empty log: do not recount old pickups on uncover.
    log=(x+int(w*.70),y+int(h*.65),right,y+int(h*.95))
    if any(r>log[0] and left<log[2] and b>log[1] and top<log[3] for left,top,r,b in hide):return None
    image=ImageGrab.grab(bbox=crop,all_screens=True).convert('RGB')
    draw=ImageDraw.Draw(image)
    for left,top,r,b in hide:
        if r>crop[0] and left<crop[2] and b>crop[1] and top<crop[3]:
            draw.rectangle((max(0,left-crop[0]),max(0,top-crop[1]),min(image.width,r-crop[0]),min(image.height,b-crop[1])),fill='black')
    return read_reward_image(image,include_pending=True)
