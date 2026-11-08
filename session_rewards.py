"""Reward-log accounting. Reads visible messages; kill counts are EXP-event estimates."""
import re
import unicodedata

_AMOUNT=re.compile(r'[\(f]\s*\+\s*([0-9][0-9, ]*)\s*(?:\)|$)')

def reward_event(text):
    text=unicodedata.normalize('NFKC',str(text)).strip();amount=_AMOUNT.search(text)
    if not amount:return None
    value=int(amount[1].replace(',','').replace(' ',''))
    if not 0<value<=100000000:return None
    lower=text.casefold().replace('qained','gained').replace('receited','received')
    if 'mesos' in lower and ('gained' in lower or 'received' in lower):return ('mesos',value)
    if re.search(r'exp(?=$|[\W\d]|for)',lower):
        if 'bonus' in lower or 'party' in lower:return ('bonus',value)
        if 'received' in lower:return ('exp',value)
    return None

def reward_kind(text):
    lower=unicodedata.normalize('NFKC',str(text)).casefold().replace('qained','gained').replace('receited','received')
    if 'mesos' in lower and ('gained' in lower or 'received' in lower):return 'mesos'
    if re.search(r'exp(?=$|[\W\d]|for)',lower):
        if 'party' in lower or 'bonus' in lower:return 'bonus'
        if 'received' in lower:return 'exp'
    return None

class RewardTracker:
    def __init__(self,confirm_money=1):self.previous=None;self.credited=[];self.seen=[];self.blanks=0;self.confirm_money=max(1,int(confirm_money));self.replacement=None;self.replacement_reads=0
    @staticmethod
    def _align(old,current):
        # Preserve row identity when OCR temporarily misses an amount or inserts a row.
        n,m=len(old),len(current);dp=[[0]*(m+1) for _ in range(n+1)]
        def weight(a,b):
            if a[0]!=b[0]:return 0
            if a[1]==b[1]:return 3
            return 1  # same-kind OCR refinement must not turn an old row into new money
        for i in range(n-1,-1,-1):
            for j in range(m-1,-1,-1):
                w=weight(old[i],current[j])
                dp[i][j]=max(dp[i+1][j],dp[i][j+1],w+dp[i+1][j+1] if w else 0)
        pairs=[];i=j=0
        while i<n and j<m:
            w=weight(old[i],current[j])
            if w and dp[i][j]==w+dp[i+1][j+1]:pairs.append((i,j));i+=1;j+=1
            elif dp[i][j]==dp[i+1][j]:i+=1
            else:j+=1
        return pairs
    def feed(self,events):
        totals={'exp':0,'mesos':0,'kills':0,'party_exp':0}
        if events is None:self.previous=None;self.credited=[];self.seen=[];self.blanks=0;self.replacement=None;self.replacement_reads=0;return totals
        current=[tuple(row) for row in events]
        if not current:
            # A masked empty image cannot prove the old notices disappeared.
            if getattr(events,'partial',False):return totals
            self.replacement=None;self.replacement_reads=0
            if self.previous is None:self.previous=[];self.credited=[];self.seen=[]
            self.blanks+=1
            if self.blanks>=4:self.previous=[];self.credited=[];self.seen=[]
            return totals
        self.blanks=0;old=self.previous
        if old is None:self.previous=current;self.credited=[True]*len(current);self.seen=[1]*len(current);return totals
        # A fully replaced notice stack of the same kinds used to align forever
        # as OCR corrections, suppressing genuine later pickups. Require stable
        # replacement readings; a one-frame fading digit must still add nothing.
        replacement_reads=1
        if old and len(old)==len(current) and all(self.credited) and all(a[0]==b[0] and a[1] is not None and b[1] is not None and a[1]!=b[1] for a,b in zip(old,current)):
            candidate=tuple(current)
            self.replacement_reads=self.replacement_reads+1 if self.replacement==candidate else 1
            self.replacement=candidate
            if self.replacement_reads<max(2,self.confirm_money):return totals
            replacement_reads=self.replacement_reads;old=[]
        self.replacement=None;self.replacement_reads=0
        pairs=self._align(old,current)
        if old and not pairs:self.previous=current;self.credited=[True]*len(current);self.seen=[1]*len(current);return totals
        previous_credit=self.credited;previous_seen=self.seen
        last=pairs[-1][1] if pairs else -1
        credited=[j<=last for j in range(len(current))]
        seen=[replacement_reads if amount is not None else 0 for kind,amount in current]
        for i,j in pairs:
            credited[j]=previous_credit[i]
            seen[j]=previous_seen[i]+1 if old[i]==current[j] and current[j][1] is not None else seen[j]
        for j,(kind,amount) in enumerate(current):
            # Fresh, high-confidence money notices can disappear before another
            # OCR pass. Low-confidence amounts still require repeated agreement.
            if kind=='mesos' and j in getattr(events,'trusted_money',()):seen[j]=max(seen[j],self.confirm_money)
            if credited[j] or amount is None or (kind=='mesos' and seen[j]<self.confirm_money):continue
            credited[j]=True
            if kind=='mesos':totals['mesos']+=amount
            elif kind in ('exp','bonus'):
                totals['exp']+=amount
                if kind=='exp':totals['kills']+=1
                else:totals['party_exp']+=amount
        self.previous=current;self.credited=credited;self.seen=seen
        return totals


def session_token(session):
    return (session.get('id'),session.get('running_since'),session.get('auto_rewards',True))

def apply_rewards(session,token,delta):
    if session_token(session)!=token or session.get('running_since') is None or not session.get('auto_rewards',True):return False
    for key in ('exp','mesos','kills','party_exp'):
        if key=='mesos' and session.get('money_mode')=='wallet':continue
        session[key]=session.get(key,0)+delta.get(key,0)
    if delta.get('kills'):session['kills_estimated']=True
    return any(delta.values())
