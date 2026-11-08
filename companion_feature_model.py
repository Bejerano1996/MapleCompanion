"""Local companion utilities. Pure state operations; no game input or network."""
import math
import time
import uuid
from copy import deepcopy


def utility_number(value, minimum=0, maximum=10**15):
    """Accept finite user-entered numbers without accepting bool/NaN/infinity."""
    if isinstance(value, bool):
        raise ValueError('Enter a number')
    try:
        result = float(str(value).replace(',', '').strip())
    except (TypeError, ValueError):
        raise ValueError('Enter a number') from None
    if not math.isfinite(result) or not minimum <= result <= maximum:
        raise ValueError(f'Enter a number from {minimum:g} to {maximum:g}')
    return result


def utility_session_new(now=None):
    return {'id': uuid.uuid4().hex, 'started_at': time.time() if now is None else now,
            'elapsed': 0.0, 'running_since': None, 'kills': 0, 'exp': 0,
            'mesos': 0, 'cost': 0, 'note': ''}


def utility_session_elapsed(session, now=None):
    now = time.time() if now is None else now
    elapsed = max(0.0, float(session.get('elapsed', 0)))
    running = session.get('running_since')
    if running is not None:
        elapsed += max(0.0, now - float(running))
    return elapsed


def utility_session_toggle(session, now=None):
    now = time.time() if now is None else now
    result = deepcopy(session)
    if result.get('running_since') is None:
        result['running_since'] = now
    else:
        result['elapsed'] = utility_session_elapsed(result, now)
        result['running_since'] = None
    return result


def utility_session_rates(session, now=None):
    seconds = utility_session_elapsed(session, now)
    factor = 3600 / seconds if seconds >= 1 else 0
    return {'seconds': seconds, 'kills_hour': session.get('kills', 0) * factor,
            'exp_hour': session.get('exp', 0) * factor,
            'net_mesos': session.get('mesos', 0) - session.get('cost', 0),
            'net_hour': (session.get('mesos', 0) - session.get('cost', 0)) * factor}


def utility_session_snapshot(session, now=None):
    result = deepcopy(session)
    result['elapsed'] = utility_session_elapsed(result, now)
    result['running_since'] = None
    return result


def utility_bookmark(state, map_id, title, note=''):
    """Upsert by map ID, preserving ordering and other bookmarks."""
    map_id = str(map_id).strip()
    if not map_id or len(map_id) > 40:
        raise ValueError('Choose a map first')
    bookmarks = deepcopy(state.get('map_bookmarks', []))
    entry = {'map_id': map_id, 'title': str(title).strip()[:120], 'note': str(note)[:2000]}
    for i, existing in enumerate(bookmarks):
        if existing.get('map_id') == map_id:
            bookmarks[i] = entry
            break
    else:
        if len(bookmarks) >= 100:
            raise ValueError('You can save up to 100 maps')
        bookmarks.append(entry)
    return bookmarks


def utility_search_history(history, query):
    query = str(query).strip()[:240]
    if not query:
        return list(history or [])[:20]
    return [query] + [str(x) for x in (history or []) if str(x).casefold() != query.casefold()][:19]


def utility_timer_new(label, minutes, now=None):
    seconds = utility_number(minutes, minimum=1/60, maximum=1440) * 60
    now = time.time() if now is None else now
    return {'id': uuid.uuid4().hex, 'label': str(label).strip()[:80] or 'Reminder',
            'duration': seconds, 'due': now + seconds, 'fired': False}


def utility_timer_status(timer, now=None):
    now = time.time() if now is None else now
    remaining = max(0, math.ceil(float(timer['due']) - now))
    return remaining, remaining == 0


def utility_format_time(seconds):
    seconds = max(0, int(seconds))
    hours, rest = divmod(seconds, 3600)
    minutes, seconds = divmod(rest, 60)
    return f'{hours:02}:{minutes:02}:{seconds:02}'


def utility_session_track_map(session, map_id, title='', now=None):
    """Attribute observed running time conservatively; never relabel legacy time."""
    result=deepcopy(session)
    known=str(map_id).strip() if isinstance(map_id,(str,int)) and not isinstance(map_id,bool) else ''
    if not known or len(known)>40:
        result['map_unattributed']=True
        return result
    recorded=result.get('map_ids',[])
    if not isinstance(recorded,list):
        result['map_unattributed']=True
        recorded=[]
    seen=list(dict.fromkeys(str(value) for value in recorded if value))
    anchor=result.get('map_id')
    if anchor and str(anchor) not in seen:seen.insert(0,str(anchor))
    if not anchor:
        if utility_session_elapsed(result,now)>0:result['map_unattributed']=True
        result['map_id']=known
        result['map_name']=str(title or known).strip()[:120]
    if known not in seen:seen.append(known)
    result['map_ids']=seen[:100]
    result['map_mixed']=bool(result.get('map_mixed')) or len(seen)>1
    return result


def utility_compare_maps(history, metric='exp_hour', minimum_seconds=60):
    """Pool completed single-map manual sessions; rates use total time, not means."""
    buckets={}
    excluded={key:0 for key in ('unfinished','unknown_map','mixed_maps','invalid','no_time')}
    for session in history or []:
        if not isinstance(session,dict):
            excluded['invalid']+=1;continue
        if session.get('finished_at') is None or session.get('running_since') is not None:
            excluded['unfinished']+=1;continue
        map_id=str(session.get('map_id') or '').strip()
        if not map_id or session.get('map_unattributed'):
            excluded['unknown_map']+=1;continue
        recorded=session.get('map_ids',[map_id])
        if not isinstance(recorded,list):
            excluded['invalid']+=1;continue
        maps=set(str(value) for value in recorded if value)
        maps.add(map_id)
        if session.get('map_mixed') or len(maps)>1:
            excluded['mixed_maps']+=1;continue
        try:
            seconds=utility_number(session.get('elapsed',0))
            totals={key:utility_number(session.get(key,0),minimum=-10**15 if key=='exp' and session.get('exp_is_net') else 0) for key in ('kills','exp','mesos','cost')}
        except ValueError:
            excluded['invalid']+=1;continue
        if seconds<=0:
            excluded['no_time']+=1;continue
        row=buckets.setdefault(map_id,dict(map_id=map_id,map_name=str(session.get('map_name') or map_id),
                   sessions=0,seconds=0,kills=0,exp=0,mesos=0,cost=0,log_gap_sessions=0))
        row['sessions']+=1;row['seconds']+=seconds
        if session.get('reading_gaps'):row['log_gap_sessions']+=1
        for key,value in totals.items():row[key]+=value
    rows=[];short_maps=0
    for row in buckets.values():
        if row['seconds']<minimum_seconds:
            short_maps+=1;continue
        row['net_mesos']=row['mesos']-row['cost']
        factor=3600/row['seconds']
        row.update(exp_hour=row['exp']*factor,kills_hour=row['kills']*factor,net_hour=row['net_mesos']*factor)
        rows.append(row)
    if metric not in ('exp_hour','kills_hour','net_hour'):metric='exp_hour'
    rows.sort(key=lambda row:(-row[metric],row['map_name'].casefold(),row['map_id']))
    return {'maps':rows,'excluded':excluded,'below_minimum_maps':short_maps,'metric':metric,
            'minimum_seconds':minimum_seconds,'scope':'Recorded totals from completed sessions observed on one map; auto kills are estimates.'}
