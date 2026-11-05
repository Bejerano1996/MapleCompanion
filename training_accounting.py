"""Reconcile screen rewards with validated EXP-bar differences."""
from session_rewards import RewardTracker,apply_rewards,session_token
from training_model import ExpLedger,absolute_exp
import math

class NoticeReconciliation:
    """Match notice gains to HUD gains across short display/OCR timing offsets."""
    def __init__(self):self.pending=0;self.base_pending=0;self.bonus_credit=0;self.credit_at=None;self.stable_pending=0;self.stable_at=None
    def feed(self,delta,hud_change,now,baseline=False,refined_party_exp=0,trailing_party_exp=0):
        if baseline:
            self.__init__();return 0
        if self.credit_at is not None and now-self.credit_at>5:
            self.bonus_credit=0;self.credit_at=None
        possible_late=delta.get('party_exp',0) if not delta.get('kills') else refined_party_exp
        if self.base_pending and not delta.get('kills'):
            # A freshly appended bonus after an existing uncovered base belongs
            # to the new notice sequence; old refinements remain eligible credit.
            possible_late=max(refined_party_exp,possible_late-trailing_party_exp)
        late=min(self.bonus_credit,possible_late,delta.get('exp',0))
        self.bonus_credit-=late
        old_pending=self.pending
        self.pending+=delta.get('exp',0)-late
        self.base_pending+=max(0,delta.get('exp',0)-delta.get('party_exp',0))
        if hud_change is not None:
            if hud_change<0:
                # A fresh net-loss reading already includes gains/losses in this
                # interval. Never extrapolate them back over the recorded loss.
                # Keep short-lived credit for bonuses already covered before
                # this loss, so their delayed OCR refinement cannot add them twice.
                self.pending=0;self.base_pending=0;self.stable_pending=0;self.stable_at=None;return 0
            covered=min(self.pending,hud_change);self.pending-=covered
            missing=hud_change-covered
            # A small gap beside a known base reward can be an unread party
            # bonus. Do not absorb unrelated quest gains or later base rewards.
            if 0<missing<=max(1,math.ceil(self.base_pending*.6)) and self.base_pending:
                self.bonus_credit+=missing;self.credit_at=now
            self.base_pending=min(self.base_pending,self.pending)
            # Repeated accepted, unchanged HUD totals are stronger evidence than
            # an old unmatched log remainder. Allow the existing five-second
            # reconciliation grace, and retire only the witnessed old amount.
            # Notices arriving in this callback must remain pending separately.
            if hud_change==0 and self.stable_at is not None and now-self.stable_at>5:
                self.pending-=min(self.stable_pending,old_pending,self.pending)
                self.base_pending=min(self.base_pending,self.pending)
                self.stable_at=None;self.stable_pending=0
            if not self.pending:self.stable_at=None;self.stable_pending=0
            elif hud_change>0 or self.stable_at is None:
                self.stable_pending=self.pending;self.stable_at=now
        return self.pending

class TrainingAccountant:
    def __init__(self):
        self.tracker=RewardTracker(confirm_money=2);self.ledger=ExpLedger();self.bar_total=None;self.logs_since_bar=0;self.character=None;self.unavailable=False;self.reconciliation=NoticeReconciliation()
    def feed(self,session,token,events,reading=None,now=0):
        if session_token(session)!=token or session.get('running_since') is None or not session.get('auto_rewards',True):return False
        delta=self.tracker.feed(events);self.last_delta=delta
        if self.bar_total is not None:
            log_delta=dict(delta,exp=0)
        else:log_delta=delta
        changed=apply_rewards(session,token,log_delta)
        if not session.get('auto_rewards',True) or session.get('running_since') is None:return False
        if events is None:
            if not self.unavailable:session['reading_gaps']=session.get('reading_gaps',0)+1
            self.unavailable=True
        else:self.unavailable=False
        hud_change=None;baseline=False
        if reading:
            old_anchor=self.ledger.anchor;old_reading=self.ledger.last
            value=self.ledger.observe(reading,session.get('exp',0),now)
            baseline=old_anchor is None or old_anchor!=self.ledger.anchor
            if value is not None:
                if old_reading and not baseline:hud_change=absolute_exp(reading)-absolute_exp(old_reading)
                changed=changed or value!=session.get('exp',0)
                session['exp']=value;session['exp_source']='EXP bar · net';session['exp_is_net']=True;self.bar_total=value;self.character=reading
        self.logs_since_bar=self.reconciliation.feed(delta,hud_change,now,baseline,self.tracker.refined_party_exp,self.tracker.trailing_party_exp)
        if self.bar_total is not None:
            if now-(self.ledger.last_at if self.ledger.last_at is not None else now)>15:
                value=self.bar_total+self.logs_since_bar
                changed=changed or session.get('exp')!=value;session['exp']=value;session['exp_source']='Reward log · partial'
        else:session['exp_source']='Reward log · observed'
        return changed
