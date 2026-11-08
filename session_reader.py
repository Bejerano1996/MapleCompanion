"""CPU-only local OCR of the game's visible lower-right reward log. No network or inputs."""
from session_rewards import reward_event
_engine=None

def read_reward_image(image):
    global _engine
    import numpy as np
    if _engine is None:
        import onnxruntime
        onnxruntime.disable_telemetry_events()
        from rapidocr_onnxruntime import RapidOCR
        _engine=RapidOCR(intra_op_num_threads=1,inter_op_num_threads=1)
    image=image.convert('RGB');image.thumbnail((1280,720))
    rows,_=_engine(np.asarray(image)[:,:,::-1],use_cls=False)
    result=[]
    for box,text,score in rows or []:
        event=reward_event(text)
        if event and score>=.82:
            result.append((min(p[1] for p in box),event))
    return [event for _,event in sorted(result,key=lambda x:x[0])]

def capture_rewards(hide=()):
    from game_sync import find_game_window
    from PIL import ImageGrab,ImageDraw
    box=find_game_window()
    if box is None:return None
    x,y,right,bottom=box;w=right-x;h=bottom-y
    crop=(x+int(w*.60),y+int(h*.50),right,y+int(h*.95))
    image=ImageGrab.grab(bbox=crop,all_screens=True).convert('RGB')
    draw=ImageDraw.Draw(image)
    for left,top,r,b in hide:
        if r>crop[0] and left<crop[2] and b>crop[1] and top<crop[3]:
            draw.rectangle((max(0,left-crop[0]),max(0,top-crop[1]),min(image.width,r-crop[0]),min(image.height,b-crop[1])),fill='black')
    return read_reward_image(image)
