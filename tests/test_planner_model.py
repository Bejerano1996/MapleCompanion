import unittest
from copy import deepcopy
from companion_planner_model import *


class PlannerTests(unittest.TestCase):
    def setUp(self):
        self.maps = {
            'a': {'connectedMaps': [{'mapId': 'b'}, {'mapId': 'missing'}], 'monsters': [{'id': 1}]},
            'b': {'connectedMaps': [{'mapId': 'c'}], 'monsters': [{'id': 2}, {'id': 3}]},
            'c': {'connectedMaps': [], 'monsters': [{'id': 4}]},
            'island': {'connectedMaps': [], 'monsters': [{'id': 9}]}}

    def test_directed_routes_and_unknown_links(self):
        graph = planner_graph(self.maps)
        self.assertEqual(planner_paths(graph, 'a')['c'], ['a', 'b', 'c'])
        self.assertNotIn('a', planner_paths(graph, 'c'))
        self.assertEqual(planner_paths(graph, 'missing'), {})

    def test_shared_map_covers_multiple_objectives(self):
        objectives = [{'id': str(i), 'mobs': [str(i)]} for i in (2, 3, 4)]
        plan = planner_itinerary('a', self.maps, objectives)
        self.assertEqual([s['map'] for s in plan['stops']], ['b', 'c'])
        self.assertEqual(len(plan['stops'][0]['objectives']), 2)
        self.assertEqual(plan['portals'], 2)
        self.assertEqual(plan['unplanned'], [])

    def test_current_map_is_zero_portals(self):
        plan = planner_itinerary('a', self.maps, [{'id': 'o', 'mobs': ['1']}])
        self.assertEqual(plan['stops'][0]['path'], ['a'])
        self.assertEqual(plan['portals'], 0)

    def test_explicit_unplanned_reasons(self):
        objectives = [{'id': 'source', 'mobs': []}, {'id': 'location', 'mobs': ['99']}, {'id': 'route', 'mobs': ['9']}]
        plan = planner_itinerary('a', self.maps, objectives)
        self.assertEqual([o['reason'] for o in plan['unplanned']], ['Source not loaded', 'No cached location', 'No known portal route'])

    def test_objectives_respect_progress_done_and_removed_quests(self):
        quests = {'q': {'name': 'Quest', 'need': [{'count': 10, 'mobId': 1}, {'count': 5, 'itemId': 2}, {'count': 3, 'mobId': 3}]}}
        state = {'active': ['q', 'q', 'missing'], 'progress': {'q': {'0': 10, '1': 2}}, 'done': {'q': [2]}}
        guides = {'q': [{}, {'lines': [{'mob': 2}]}]}
        before = deepcopy(state)
        result = planner_objectives(state, quests, guides)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['remaining'], 3)
        self.assertEqual(result[0]['mobs'], ['2'])
        self.assertEqual(state, before)

    def test_route_limit(self):
        objectives = [{'id': '2', 'mobs': ['2']}, {'id': '4', 'mobs': ['4']}]
        plan = planner_itinerary('a', self.maps, objectives, max_stops=1)
        self.assertEqual(len(plan['stops']), 1)
        self.assertEqual(plan['unplanned'][0]['reason'], 'Stop limit reached')


if __name__ == '__main__':
    unittest.main()
