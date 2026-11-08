"""Learn personal EXP per reward event only when validated HUD changes agree."""
class YieldLearner:
    def __init__(self):self.signature=None;self.samples=[];self.last_at=None;self.window={};self.window_at=None
    def _sync(self,signature,now):
        if self.signature!=signature or self.last_at is not None and now-self.last_at>45:
            self.signature=signature;self.samples=[];self.last_at=None
            self.window={};self.window_at=None
    def add_window(self,signature,delta,now):
        self._sync(signature,now)
        if not signature or not signature[0]:return
        if self.window_at is not None and now-self.window_at>5:self.window={};self.window_at=None
        if self.window_at is None and any(delta.get(k,0) for k in ('exp','kills','party_exp')):self.window_at=now
        for key in ('exp','kills','party_exp'):self.window[key]=self.window.get(key,0)+delta.get(key,0)
    def take_window(self,signature,now):
        self._sync(signature,now)
        result=self.window if self.window_at is not None and now-self.window_at<=5 else {}
        self.window={};self.window_at=None
        return result
    def observe(self,signature,delta,hud_delta,now):
        self._sync(signature,now)
        if not signature or not signature[0]:return False
        bonus=delta.get('party_exp',0)
        if delta.get('kills',0)==0 and isinstance(bonus,int) and not isinstance(bonus,bool) and bonus>0 and delta.get('exp')==bonus and hud_delta==bonus:
            # A separately confirmed bonus proves that base-only samples can
            # omit part of personal yield. Wait for new complete samples.
            self.samples=[];self.last_at=None
            return False
        if delta.get('kills')!=1:return False
        gain=delta.get('exp',0)
        if not isinstance(gain,int) or isinstance(gain,bool) or not 0<gain<=100000000 or hud_delta!=gain:return False
        if self.samples and gain!=self.samples[-1]:self.samples=[]
        self.samples=(self.samples+[gain])[-3:];self.last_at=now
        return True
    def estimate(self,signature,now):
        self._sync(signature,now)
        if signature!=self.signature or self.last_at is None or now-self.last_at>45 or len(self.samples)<3:return None
        return self.samples[-1]
    def progress(self,signature,now):
        self._sync(signature,now)
        return len(self.samples) if signature==self.signature and self.last_at is not None and now-self.last_at<=45 else 0
