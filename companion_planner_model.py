"""Quest itinerary using cached directed portal links and known monster locations."""
from collections import deque


def planner_graph(map_data):
    graph = {}
    for mid, record in map_data.items():
        links = []
        for link in record.get('connectedMaps', []):
            destination = str(link.get('mapId', ''))
            if destination in map_data and destination not in links:
                links.append(destination)
        graph[str(mid)] = sorted(links)
    return graph


def planner_paths(graph, start):
    start = str(start)
    if start not in graph:
        return {}
    paths = {start: [start]}
    queue = deque([start])
    while queue:
        here = queue.popleft()
        for destination in graph.get(here, []):
            if destination not in paths:
                paths[destination] = paths[here] + [destination]
                queue.append(destination)
    return paths


def planner_objectives(state, quests, guides):
    objectives = []
    for qid in dict.fromkeys(str(q) for q in state.get('active', [])):
        quest = quests.get(qid)
        if not quest:
            continue
        done = {str(i) for i in state.get('done', {}).get(qid, [])}
        progress = state.get('progress', {}).get(qid, {})
        steps = guides.get(qid, [])
        for index, need in enumerate(quest.get('need') or []):
            target = max(0, int(need.get('count') or 0))
            current = max(0, int(progress.get(str(index), progress.get(index, 0)) or 0))
            if str(index) in done or (target and current >= target):
                continue
            mobs = set()
            if need.get('mobId') is not None:
                mobs.add(str(need['mobId']))
            if index < len(steps):
                mobs.update(str(line['mob']) for line in steps[index].get('lines', []) if line.get('mob') is not None)
            objectives.append({'id': f'{qid}:{index}', 'qid': qid, 'index': index,
                               'quest': quest.get('name', qid), 'name': need.get('name', 'Objective'),
                               'remaining': max(0, target-current), 'mobs': sorted(mobs),
                               'kind': 'hunt' if need.get('mobId') is not None else 'collect'})
    return objectives


def planner_itinerary(start, map_data, objectives, max_stops=20):
    """Greedy coverage per portal. Explicitly a suggestion, not an optimal tour."""
    graph = planner_graph(map_data)
    pending = {o['id']: o for o in objectives}
    coverage = {}
    for mid, record in map_data.items():
        mobs = {str(m['id']) for m in record.get('monsters', []) if m.get('id') is not None}
        matches = {key for key, objective in pending.items() if mobs.intersection(objective['mobs'])}
        if matches:
            coverage[str(mid)] = matches
    stops = []
    here = str(start)
    total_portals = 0
    while pending and len(stops) < max_stops:
        paths = planner_paths(graph, here)
        choices = []
        for mid, ids in coverage.items():
            hits = ids.intersection(pending)
            if hits and mid in paths:
                distance = len(paths[mid])-1
                choices.append((-len(hits)/(distance+1), distance, -len(hits), mid, sorted(hits)))
        if not choices:
            break
        _, distance, _, mid, ids = min(choices)
        stops.append({'map': mid, 'from': here, 'path': paths[mid], 'portals': distance,
                      'objectives': [pending.pop(key) for key in ids]})
        total_portals += distance
        here = mid
    unplanned = []
    for objective in pending.values():
        entry = dict(objective)
        entry['reason'] = ('Source not loaded' if not objective['mobs'] else
                           'No cached location' if not any(objective['id'] in ids for ids in coverage.values()) else
                           'Stop limit reached' if len(stops) >= max_stops else 'No known portal route')
        unplanned.append(entry)
    return {'start': str(start), 'stops': stops, 'portals': total_portals, 'unplanned': unplanned}
