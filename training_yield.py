"""Learn personal EXP per reward event only when validated HUD changes agree."""
class YieldLearner:
    def __init__(self):self.signature=None;self.samples=[];self.last_at=None
    def _sync(self,signature,now):
        if self.signature!=signature or self.last_at is not None and now-self.last_at>45:
            self.signature=signature;self.samples=[];self.last_at=None
    def observe(self,signature,delta,hud_delta,now):
        self._sync(signature,now)
        if not signature or not signature[0] or delta.get('kills')!=1:return False
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
