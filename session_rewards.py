"""Reward-log accounting. Reads visible messages; kill counts are EXP-event estimates."""
import re

_AMOUNT=re.compile(r'[\(f]\s*\+\s*([0-9][0-9, ]*)\s*\)')

def reward_event(text):
    text=str(text).strip();amount=_AMOUNT.search(text)
    if not amount:return None
    value=int(amount[1].replace(',','').replace(' ',''))
    if not 0<value<=100000000:return None
    lower=text.casefold().replace('qained','gained')
    if 'mesos' in lower and ('gained' in lower or 'received' in lower):return ('mesos',value)
    if re.search(r'\bexp\b',lower):
        if 'bonus' in lower or 'party' in lower:return ('bonus',value)
        if 'received' in lower:return ('exp',value)
    return None

class RewardTracker:
    def __init__(self):self.previous=None;self.blanks=0
    def feed(self,events):
        totals={'exp':0,'mesos':0,'kills':0}
        if events is None:self.previous=None;self.blanks=0;return totals
        current=list(events)
        if not current:
            self.blanks+=1
            if self.blanks>=2:self.previous=[]
            return totals
        self.blanks=0
        old=self.previous;self.previous=current
        if old is None:return totals  # baseline: do not count messages from before Start/resume
        if old==current:return totals
        overlap=next((n for n in range(min(len(old),len(current)),0,-1) if old[-n:]==current[:n]),0)
        if old and not overlap:return totals  # lost continuity: rebaseline, never invent gains
        for kind,amount in current[overlap:]:
            if kind=='mesos':totals['mesos']+=amount
            else:
                totals['exp']+=amount
                if kind=='exp':totals['kills']+=1
        return totals

def session_token(session):
    return (session.get('id'),session.get('running_since'),session.get('auto_rewards',True))

def apply_rewards(session,token,delta):
    if session_token(session)!=token or session.get('running_since') is None or not session.get('auto_rewards',True):return False
    for key in ('exp','mesos','kills'):session[key]=session.get(key,0)+delta.get(key,0)
    if delta.get('kills'):session['kills_estimated']=True
    return any(delta.values())
