"""Keep guaranteed, selectable and random quest rewards separate."""
import math

def item_text(item):
    return f"{item.get('count',1)} × {item.get('name','Item')}"

def reward_sections(quest):
    guaranteed=[]
    for key,unit in [('exp','EXP'),('mesos','mesos')]:
        if quest.get(key):guaranteed.append(f'{quest[key]:,} {unit}')
    if quest.get('fame'):guaranteed.append(f"{quest['fame']:+} fame")
    contribution=quest.get('contribution') or {}
    if contribution.get('amount'):guaranteed.append(f"{contribution['amount']:+} {contribution.get('town','town')} contribution")
    guaranteed.extend(item_text(item) for item in quest.get('get') or [] if item.get('count',1)>0)
    result=[{'title':'Guaranteed','rows':guaranteed}] if guaranteed else []
    for field,title in [('rewardChoices','Choose a reward'),('rewardRandom','Random reward · not guaranteed')]:
        for group in quest.get(field) or []:
            rows=[]
            for item in group.get('items') or []:
                if item.get('count',1)<=0:continue
                text=item_text(item)
                chance=item.get('chance')
                if field=='rewardRandom' and isinstance(chance,(int,float)) and not isinstance(chance,bool) and math.isfinite(chance) and 0<=chance<=100:text+=f' · {chance:g}%'
                rows.append(text)
            if rows:result.append({'title':title+(' · '+group['jobName'] if group.get('jobName') else ''),'rows':rows})
    return result

def reward_summary(quest):
    parts=[f"{quest[k]:,} {unit}" for k,unit in [('exp','EXP'),('mesos','mesos')] if quest.get(k)]
    items=[item for item in quest.get('get') or [] if item.get('count',1)>0]
    if len(items)==1:parts.append(item_text(items[0]))
    elif items:parts.append(f'{len(items)} items')
    if quest.get('rewardChoices'):parts.append('Choice')
    if quest.get('rewardRandom'):parts.append('Random item')
    if quest.get('fame'):parts.append(f"{quest['fame']:+} fame")
    if (quest.get('contribution') or {}).get('amount'):parts.append('Town contribution')
    return ' · '.join(parts) or 'No reward listed'
