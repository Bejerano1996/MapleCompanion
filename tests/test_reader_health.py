import unittest
from reader_health import ReaderHealth


class ReaderHealthTests(unittest.TestCase):
    def test_auto_enabled_does_not_claim_live_before_read(self):
        health=ReaderHealth()
        self.assertEqual(health.status(True,True,0)[0],'gold')
        self.assertIn('first quest',health.status(True,True,0)[1])

    def test_fresh_color_uses_capture_time_not_callback_time(self):
        health=ReaderHealth()
        health.record({'window':True,'tracked':['a','a'],'references':[]},10,captured_at=1)
        color,text=health.status(True,True,10)
        self.assertEqual(color,'gold')
        self.assertIn('9s ago',text)
        self.assertIn('1 tracked',text)

    def test_fresh_stale_boundaries(self):
        health=ReaderHealth()
        health.record({'tracked':['a']},0)
        self.assertEqual(health.status(True,True,6)[0],'green')
        self.assertEqual(health.status(True,True,6.001)[0],'gold')
        self.assertIn('waiting for fresh evidence',health.status(True,True,15.001)[1])

    def test_game_absence_and_errors_never_stay_green(self):
        health=ReaderHealth()
        health.record({'tracked':['a']},0)
        health.record(None,1)
        self.assertEqual(health.status(True,True,1)[0],'gold')
        health.failed('capture expired')
        self.assertIn('capture expired',health.status(True,True,1)[1])

    def test_occlusion_does_not_claim_a_fresh_quest_read(self):
        health=ReaderHealth()
        health.record({'tracked':['a']},0)
        health.record({'window':True,'capture_blocked':True},1)
        self.assertEqual(health.captured_at,0)
        self.assertEqual(health.status(True,True,1)[0],'gold')
        self.assertIn('overlapping windows',health.status(True,True,1)[1])

    def test_map_only_does_not_refresh_quest_timestamp(self):
        health=ReaderHealth()
        health.record({'tracked':['a']},0)
        health.record({'map_only':True,'window':True},12)
        self.assertEqual(health.captured_at,0)
        self.assertEqual(health.status(True,True,12)[0],'gold')

    def test_game_found_without_quest_is_explained(self):
        health=ReaderHealth()
        health.record({'window':True,'tracked':[],'references':[]},0)
        self.assertEqual(health.status(True,True,1)[0],'gold')
        self.assertIn('Quest Helper',health.status(True,True,1)[1])

    def test_auto_off_and_missing_data_are_distinct(self):
        health=ReaderHealth()
        self.assertEqual(health.status(False,False,0)[0],'disabled')
        self.assertIn('waiting for game data',health.status(True,False,0)[1])


if __name__=='__main__': unittest.main()
