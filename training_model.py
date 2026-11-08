"""Validated character EXP readings and honest training forecasts (Classic levels 1-99)."""
import math,re,time
from decimal import Decimal
from collections import Counter
import leveling

def valid_level(level):return isinstance(level,int) and not isinstance(level,bool) and 1<=level<=99

def character_reading(texts,level_hint=None):
    """Require an EXP integer and matching displayed percentage; never infer from % alone."""
    clean=[str(t) for t in texts]
    hud=[]
    for t in clean:
        hud += [int(m) for m in re.findall(r'\bL[Vv][\s.:]*(\d{1,2})(?!\d)',t)]
    numbers,pcts,_=leveling.bar_numbers([t for t in clean if 'exp' in t.casefold() or '%' in t])
    if not numbers or not pcts:return None
    levels=[v for v in hud if valid_level(v)] or list(range(1,100))
    candidates=[]
    for lv in set(levels):
        need=leveling.exp_to_next(lv)
        for n in set(numbers):
            if not 0<=n<need:continue
            for pct in set(pcts):
                if abs(100*n/need-pct)<=.011:candidates.append((lv,n,pct))
    # Ambiguous matches cannot calibrate a character or count session EXP.
    pairs={(lv,n) for lv,n,_ in candidates}
    if len(pairs)!=1:return None
    lv,n=next(iter(pairs));pct=next(p for l,e,p in candidates if l==lv and e==n)
    return {'level':lv,'exp':n,'percent':pct,'need':leveling.exp_to_next(lv),'source':'HUD' if hud else 'EXP+percent'}

def absolute_exp(reading):
    lv=reading['level'];n=reading['exp']
    if not valid_level(lv) or not isinstance(n,int) or isinstance(n,bool) or not 0<=n<leveling.exp_to_next(lv):raise ValueError('Invalid character EXP')
    return sum(leveling.exp_to_next(i) for i in range(1,lv))+n

class ExpLedger:
    """Two validated samples establish a baseline; bar deltas replace log totals, never add twice."""
    def __init__(self):self.anchor=None;self.session_anchor=0;self.last=None;self.confirmed=False;self.last_at=None;self.pending_jump=None
    def observe(self,reading,session_exp,now=None):
        if reading is None:return None
        now=time.monotonic() if now is None else now;total=absolute_exp(reading)
        if self.anchor is None:
            self.anchor=total;self.session_anchor=session_exp;self.last=reading;self.last_at=now;return None
        difference=reading['level']-self.last['level']
        if difference<0 or difference>1:
            if self.pending_jump is None or self.pending_jump['level']!=reading['level']:
                self.pending_jump=reading;return None
            if difference<0:
                self.anchor=total;self.session_anchor=session_exp
            self.pending_jump=None
        self.pending_jump=None
        self.confirmed=True;self.last=reading;self.last_at=now
        return self.session_anchor+total-self.anchor

def adjusted_party_total(total,reference_level,current_level):
    """A supplied total includes the character's level; carry only its known change."""
    if total is None or reference_level is None or current_level is None:return total
    if not isinstance(total,int) or isinstance(total,bool) or not valid_level(reference_level) or not valid_level(current_level):return total
    return total+current_level-reference_level

def training_forecast(reading,mob,party=1,hits='all',party_levels=None,now=None,read_at=None,personal_gain=None):
    if not reading:return {'available':False,'reason':'Read the EXP bar or set level and current EXP'}
    if not valid_level(reading.get('level')):return {'available':False,'reason':'EXP table unavailable for this level'}
    try:total=absolute_exp(reading)
    except (ValueError,KeyError,TypeError):return {'available':False,'reason':'Current EXP is unknown'}
    lv=reading['level'];left=leveling.exp_to_next(lv)-reading['exp']
    if not mob or not isinstance(mob.get('exp'),(int,float)) or isinstance(mob.get('exp'),bool) or not math.isfinite(mob['exp']) or mob['exp']<=0:return {'available':False,'reason':'Select a monster with known EXP','remaining':left}
    if hits not in leveling.HITS or not isinstance(party,int) or isinstance(party,bool) or not 1<=party<=6:return {'available':False,'reason':'Check party settings'}
    if party_levels is not None and (not isinstance(party_levels,int) or isinstance(party_levels,bool) or party_levels<lv+party-1):return {'available':False,'reason':'Check the party level total'}
    if personal_gain is not None and (not isinstance(personal_gain,(int,float)) or isinstance(personal_gain,bool) or not math.isfinite(personal_gain) or personal_gain<1):return {'available':False,'reason':'Check personal EXP per kill'}
    gain=personal_gain if personal_gain is not None else leveling.party_exp(mob['exp'],lv,party,hits,party_levels)
    numerator,denominator=Decimal(str(gain)).as_integer_ratio()
    kills=(left*denominator+numerator-1)//numerator
    return {'available':True,'remaining':left,'gain':gain,'kills':kills,'mob':mob.get('display') or mob.get('name') or str(mob.get('id')),'level':lv,'next_level':lv+1,'party':party,'stale':read_at is not None and now is not None and now-read_at>15,'source':'your EXP/kill' if personal_gain is not None else 'formula · party share' if party>1 else 'monster base EXP'}
