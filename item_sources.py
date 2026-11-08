"""Item acquisition from public shop and breakable data; no gameplay input."""
import re
import guides

def page_links(rsc):
    found=[]
    for kind,a,b in guides.page_events(rsc):
        if kind=='link':found.append((a,b))
        elif kind=='block':found.extend(guides.links(b))
    return list(dict.fromkeys(found))

def section_links(rsc,predicate):
    found=[]
    for section in guides.sections(rsc):
        if not predicate(section['title'].casefold()):continue
        found.extend(section['links'])
        for tag,block in section['blocks']:found.extend(guides.links(block))
    return list(dict.fromkeys(found))

def breakable_links(rsc):
    result=[]
    for href,caption in section_links(rsc,lambda title:'breakable' in title):
        match=re.fullmatch(r'/msclassic/breakables/(\d+)',href)
        if not match:continue
        name=re.split(r'\d{7}|[▲▼]',caption,1)[0].strip()
        result.append({'id':match[1],'name':name or 'Breakable','href':href})
    return list({row['id']:row for row in result}.values())

def breakable_maps(rsc,maps):
    result=[]
    for href,caption in section_links(rsc,lambda title:'spawn' in title and 'map' in title):
        match=re.fullmatch(r'/msclassic/maps/(\d+)',href)
        if not match:continue
        mid=match[1]
        # Only route to real indexed maps, not an unrelated or removed page.
        if mid not in maps:continue
        result.append([mid,maps[mid].get('displayName') or maps[mid].get('name') or mid])
    return list({row[0]:row for row in result}.values())

def shop_sources(sellers,maps):
    result=[]
    for seller in sellers:
        mid=str(seller.get('mapId') or '')
        if mid not in maps or not seller.get('npc'):continue
        price=seller.get('price')
        result.append({'kind':'shop','name':seller['npc'],'npc':seller['npc'],
                       'maps':[[mid,maps[mid].get('displayName') or mid]],
                       'price':price if isinstance(price,(int,float)) and not isinstance(price,bool) and price>=0 else None,
                       'citizen':seller.get('citizen'),'source':'https://meowdb.com/msclassic/npc-shops'})
    return result

def ranked_sources(sources,distances):
    def key(source):
        distance=min((distances.get(row[0],10**9) for row in source.get('maps',[])),default=10**9)
        return (bool(source.get('citizen')),distance,source.get('price') if source.get('price') is not None else 10**9,source.get('name',''))
    return sorted(sources,key=key)

def nearest_target(source,distances):
    return min(source.get('maps') or [],key=lambda row:distances.get(row[0],10**9),default=None)
