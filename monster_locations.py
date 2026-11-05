"""Known monster spawn points and directed portal distances, using cached map data."""
import math
def monster_locations(map_data,maps,mob,distances,fallback=(),sort='mobs'):
    rows={}
    for key,record in map_data.items():
        matches=[entry for entry in record.get('monsters') or [] if str(entry.get('id'))==str(mob)]
        if not matches:continue
        counts=[entry.get('count') for entry in matches]
        known=all(isinstance(n,(int,float)) and not isinstance(n,bool) and math.isfinite(n) and n>=0 for n in counts)
        mid=str(key)
        rows[mid]={'map':mid,'name':maps.get(mid,{}).get('displayName') or record.get('name') or mid,
                   'spawn':sum(counts) if known else None,'distance':distances.get(mid),'mob':mob}
    for mid,name in fallback:
        mid=str(mid)
        if mid not in rows:rows[mid]={'map':mid,'name':name,'spawn':None,'distance':distances.get(mid),'mob':mob}
    choices=list(rows.values())
    reachable=[row for row in choices if row['distance'] is not None]
    if distances and reachable:choices=reachable
    def distance(row):return row['distance'] if row['distance'] is not None else float('inf')
    def spawn(row):return -row['spawn'] if row['spawn'] is not None else float('inf')
    return sorted(choices,key=lambda row:(distance(row),spawn(row),row['name']) if sort=='near' else (spawn(row),distance(row),row['name']))
