"""Reconcile screen rewards with validated EXP-bar differences."""
from session_rewards import RewardTracker,apply_rewards,session_token
from training_model import ExpLedger

class TrainingAccountant:
    def __init__(self):
        self.tracker=RewardTracker(confirm_money=2);self.ledger=ExpLedger();self.bar_total=None;self.logs_since_bar=0;self.character=None;self.unavailable=False
    def feed(self,session,token,events,reading=None,now=0):
        if session_token(session)!=token or session.get('running_since') is None or not session.get('auto_rewards',True):return False
        delta=self.tracker.feed(events);self.last_delta=delta
        if self.bar_total is not None:
            self.logs_since_bar+=delta['exp'];log_delta=dict(delta,exp=0)
        else:log_delta=delta
        changed=apply_rewards(session,token,log_delta)
        if not session.get('auto_rewards',True) or session.get('running_since') is None:return False
        if events is None:
            if not self.unavailable:session['reading_gaps']=session.get('reading_gaps',0)+1
            self.unavailable=True
        else:self.unavailable=False
        if reading:
            value=self.ledger.observe(reading,session.get('exp',0),now)
            if value is not None:
                changed=changed or value!=session.get('exp',0)
                session['exp']=value;session['exp_source']='EXP bar · net';session['exp_is_net']=True;self.bar_total=value;self.logs_since_bar=0;self.character=reading
        if self.bar_total is not None:
            if now-(self.ledger.last_at if self.ledger.last_at is not None else now)>15:
                value=self.bar_total+self.logs_since_bar
                changed=changed or session.get('exp')!=value;session['exp']=value;session['exp_source']='Reward log · partial'
        else:session['exp_source']='Reward log · observed'
        return changed
