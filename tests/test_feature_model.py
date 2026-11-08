import unittest
from companion_feature_model import *


class UtilityModelTests(unittest.TestCase):
    def test_manual_session_pause_resume(self):
        s = utility_session_new(100)
        s = utility_session_toggle(s, 100)
        self.assertEqual(utility_session_elapsed(s, 160), 60)
        s = utility_session_toggle(s, 160)
        self.assertEqual(utility_session_elapsed(s, 500), 60)
        s = utility_session_toggle(s, 600)
        s.update(kills=10, exp=1000, mesos=100, cost=150)
        rates = utility_session_rates(s, 660)
        self.assertEqual(rates['seconds'], 120)
        self.assertEqual(rates['kills_hour'], 300)
        self.assertEqual(rates['net_hour'], -1500)

    def test_session_snapshot_does_not_mutate(self):
        s = utility_session_toggle(utility_session_new(0), 0)
        saved = utility_session_snapshot(s, 42)
        self.assertEqual(saved['elapsed'], 42)
        self.assertIsNone(saved['running_since'])
        self.assertEqual(s['running_since'], 0)
        self.assertEqual(s['elapsed'], 0)

    def test_clock_rollback(self):
        s = utility_session_toggle(utility_session_new(100), 100)
        self.assertEqual(utility_session_elapsed(s, 50), 0)

    def test_zero_duration_has_no_infinite_rates(self):
        self.assertEqual(utility_session_rates(utility_session_new(0), 0)['exp_hour'], 0)

    def test_numeric_validation(self):
        self.assertEqual(utility_number('1,234'), 1234)
        for value in (True, None, 'nan', 'inf', '-1', '', '1e20'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                utility_number(value)

    def test_map_upsert_preserves_original(self):
        state = {'map_bookmarks': [{'map_id': '001', 'title': 'A', 'note': ''}]}
        result = utility_bookmark(state, '001', 'Updated', 'Note')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['note'], 'Note')
        self.assertEqual(state['map_bookmarks'][0]['title'], 'A')
        self.assertEqual(utility_bookmark(state, '002', 'B')[1]['map_id'], '002')

    def test_map_limit_allows_edit(self):
        state = {'map_bookmarks': [{'map_id': str(i)} for i in range(100)]}
        self.assertEqual(len(utility_bookmark(state, '0', 'new')), 100)
        with self.assertRaises(ValueError):
            utility_bookmark(state, '101', 'extra')

    def test_search_deduplicates_and_limits(self):
        self.assertEqual(utility_search_history(['Luke', 'Mano'], 'luke'), ['luke', 'Mano'])
        self.assertEqual(len(utility_search_history(list(map(str, range(40))), 'new')), 20)

    def test_timer_due_boundary(self):
        timer = utility_timer_new('Buff', 2, 100)
        self.assertEqual(utility_timer_status(timer, 219.5), (1, False))
        self.assertEqual(utility_timer_status(timer, 220), (0, True))
        self.assertEqual(utility_timer_status(timer, 500), (0, True))
        self.assertFalse(timer['fired'])

    def test_timer_validation_and_display(self):
        with self.assertRaises(ValueError):
            utility_timer_new('Invalid', 0)
        self.assertEqual(utility_format_time(3661), '01:01:01')


if __name__ == '__main__':
    unittest.main()
