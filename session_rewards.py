"""Reward-log accounting. Reads visible messages; kill counts are EXP-event estimates."""
import re
import unicodedata

_AMOUNT=re.compile(r'[\(f]\s*\+\s*([0-9][0-9, ]*)\s*(?:\)|$)')

def reward_event(text):
    text=unicodedata.normalize('NFKC',str(text)).strip();amounts=list(_AMOUNT.finditer(text))
    if len(amounts)!=1 or len(re.findall(r'[\(f]\s*\+',text))!=1:return None
    amount=amounts[0]
    digits=amount[1].replace(' ','')
    if ',' in digits and not re.fullmatch(r'[0-9]{1,3}(?:,[0-9]{3})+',digits):return None
    value=int(digits.replace(',',''))
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
    def __init__(self,confirm_money=1):self.previous=None;self.credited=[];self.seen=[];self.blanks=0;self.confirm_money=max(1,int(confirm_money));self.replacement=None;self.replacement_reads=0;self.positions=[];self.was_partial=False
    @staticmethod
    def _align(old,current,old_positions=(),positions=(),prefer_stationary=False):
        # Preserve row identity when OCR temporarily misses an amount or inserts a row.
        n,m=len(old),len(current);dp=[[0]*(m+1) for _ in range(n+1)]
        spatial=len(old_positions)==n and len(positions)==m and bool(n and m)
        shift=0
        if spatial:
            # Exact surviving notices tell us how far the stack scrolled.
            shifts=[positions[j][0]-old_positions[i][0] for i,a in enumerate(old) for j,b in enumerate(current) if a==b and a[1] is not None]
            if shifts:
                tolerance=max(5,min(p[1] for p in positions)*.4)
                shift=max(shifts,key=lambda s:(sum(abs(v-s)<=tolerance for v in shifts),-abs(s)))
                if prefer_stationary:
                    overlaps=[(a,b) for i,a in enumerate(old) for j,b in enumerate(current)
                        if abs(old_positions[i][0]-positions[j][0])<=tolerance]
                    if overlaps and all(a[0]==b[0] and (a[1] is None or b[1] is None or a[1]==b[1]) for a,b in overlaps):shift=0
                stable_partial=(n==m and any(a[1] is None for a in old+current)
                    and all(a[0]==b[0] for a,b in zip(old,current))
                    and all(abs(a[0]-b[0])<=tolerance for a,b in zip(old_positions,positions)))
                if stable_partial and abs(shift)>tolerance:
                    anchors={a for i,a in enumerate(old) for j,b in enumerate(current)
                        if a==b and a[1] is not None and abs(positions[j][0]-old_positions[i][0]-shift)<=tolerance}
                    stationary_possible=all(a[1] is None or b[1] is None or a[1]==b[1] for a,b in zip(old,current))
                    # Even several repeating amounts cannot prove movement when
                    # every observed value still fits its original row position.
                    if stationary_possible or len(anchors)<2:shift=0
        def weight(i,j):
            a,b=old[i],current[j]
            if a[0]!=b[0]:return 0
            if spatial and abs(positions[j][0]-old_positions[i][0]-shift)>max(5,min(old_positions[i][1],positions[j][1])*.4):return 0
            if a[1]==b[1]:return 3
            return 1  # same-kind OCR refinement must not turn an old row into new money
        for i in range(n-1,-1,-1):
            for j in range(m-1,-1,-1):
                w=weight(i,j)
                dp[i][j]=max(dp[i+1][j],dp[i][j+1],w+dp[i+1][j+1] if w else 0)
        pairs=[];i=j=0
        while i<n and j<m:
            w=weight(i,j)
            if w and dp[i][j]==w+dp[i+1][j+1]:pairs.append((i,j));i+=1;j+=1
            elif dp[i][j]==dp[i+1][j]:i+=1
            else:j+=1
        return pairs
    def _retain_hidden(self,old,current,credited,seen,positions,pairs,partial):
        """Carry missing row credits only while coverage is partial; cap memory."""
        if not partial or not old or len(self.positions)!=len(old) or len(positions)!=len(current) or not pairs:
            return current,credited,seen,positions
        offsets=sorted(positions[j][0]-self.positions[i][0] for i,j in pairs)
        shift=offsets[len(offsets)//2]
        tolerance=max(5,min(p[1] for p in positions)*.4)
        anchors={old[i] for i,j in pairs if old[i]==current[j] and old[i][1] is not None}
        if abs(shift)>tolerance and len(anchors)<2:return current,credited,seen,positions
        entries=[(positions[j],row,credited[j],seen[j]) for j,row in enumerate(current)]
        hidden=[]
        matched={i for i,j in pairs}
        for i,row in enumerate(old):
            y=self.positions[i][0]+shift;h=self.positions[i][1]
            if i in matched or y<0 or any(abs(y-p[0])<=max(5,min(h,p[1])*.4) for p in positions):continue
            hidden.append(((y,h),row,self.credited[i],self.seen[i]))
        hidden.sort(key=lambda item:item[0][0])
        budget=max(0,128-len(entries))
        if budget:entries.extend(hidden[-budget:])
        entries.sort(key=lambda item:item[0][0])
        return [e[1] for e in entries],[e[2] for e in entries],[e[3] for e in entries],[e[0] for e in entries]
    def feed(self,events):
        self.refined_party_exp=0;self.trailing_party_exp=0
        totals={'exp':0,'mesos':0,'kills':0,'party_exp':0}
        if events is None:self.previous=None;self.credited=[];self.seen=[];self.blanks=0;self.replacement=None;self.replacement_reads=0;self.positions=[];self.was_partial=False;return totals
        partial=bool(getattr(events,'partial',False))
        current=[tuple(row) for row in events]
        positions=getattr(events,'positions',())
        if not current:
            # A masked empty image cannot prove the old notices disappeared.
            if partial:self.was_partial=True;return totals
            self.replacement=None;self.replacement_reads=0
            if self.previous is None:self.previous=[];self.credited=[];self.seen=[]
            self.blanks+=1
            if self.blanks>=4:self.previous=[];self.credited=[];self.seen=[];self.positions=[];self.was_partial=False
            return totals
        self.blanks=0;old=self.previous
        if old is None:self.previous=current;self.credited=[True]*len(current);self.seen=[1]*len(current);self.positions=positions;self.was_partial=partial;return totals
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
        pairs=self._align(old,current,self.positions,positions,partial or self.was_partial)
        if old and not pairs:self.previous=current;self.credited=[True]*len(current);self.seen=[1]*len(current);self.positions=positions;self.was_partial=partial;return totals
        previous_credit=self.credited;previous_seen=self.seen
        last=pairs[-1][1] if pairs else -1
        credited=[j<=last for j in range(len(current))]
        seen=[replacement_reads if amount is not None else 0 for kind,amount in current]
        for i,j in pairs:
            credited[j]=previous_credit[i]
            seen[j]=previous_seen[i]+1 if old[i]==current[j] and current[j][1] is not None else seen[j]
        old_by_new={j:i for i,j in pairs}
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
                else:
                    totals['party_exp']+=amount
                    if j in old_by_new and old[old_by_new[j]][1] is None:self.refined_party_exp+=amount
                    if j>last and j>0 and j-1 in old_by_new and current[j-1][0]=='exp' and current[j-1][1] is not None:self.trailing_party_exp+=amount
        current,credited,seen,positions=self._retain_hidden(old,current,credited,seen,positions,pairs,partial)
        self.previous=current;self.credited=credited;self.seen=seen;self.positions=positions;self.was_partial=partial
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
