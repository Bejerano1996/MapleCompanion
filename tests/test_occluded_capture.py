from types import SimpleNamespace
import unittest
from unittest.mock import patch
from PIL import Image

import game_sync
import session_reader
import training_context


class OccludedCaptureTests(unittest.TestCase):
    def test_manual_sync_without_game_never_reads_desktop(self):
        with patch.object(game_sync,'find_game_window',return_value=None),patch('PIL.ImageGrab.grab') as grab:
            self.assertIsNone(game_sync.capture_and_read(SimpleNamespace(),auto=False))
        grab.assert_not_called()
    def test_covered_game_does_not_read_browser_quest_text(self):
        box=(100,100,1100,900)
        db=SimpleNamespace(quests={},maps={})
        with patch.object(game_sync,'find_game_window',return_value=box), \
             patch('screen_visibility.covering_windows',return_value=[box]), \
             patch('PIL.ImageGrab.grab',return_value=Image.new('RGB',(1000,800))) as grab, \
             patch.object(game_sync,'find_minimap',return_value=None), \
             patch.object(game_sync,'read_location',return_value=(None,'',False)), \
             patch('screen_ocr.read_lines',return_value=[]) as read, \
             patch.object(game_sync,'read_notices',return_value=[]):
            result=game_sync.capture_and_read(db,auto=True,exp_bar=False)
        self.assertTrue(result.get('capture_blocked'))
        grab.assert_not_called();read.assert_not_called()

    def test_external_window_covering_log_is_unavailable(self):
        box=(100,100,1100,900);cover=(800,660,1100,764)
        with patch.object(game_sync,'find_game_window',return_value=box), \
             patch('screen_visibility.covering_windows',return_value=[cover]), \
             patch('PIL.ImageGrab.grab',return_value=Image.new('RGB',(300,248))) as grab, \
             patch.object(session_reader,'read_reward_image',return_value=[('exp',56)]) as read:
            self.assertIsNone(session_reader.capture_rewards())
        grab.assert_not_called();read.assert_not_called()

    def test_window_appearing_during_capture_does_not_credit_browser_reward(self):
        box=(100,100,1100,900);cover=(800,660,1100,764)
        with patch.object(game_sync,'find_game_window',return_value=box), \
             patch('screen_visibility.covering_windows',side_effect=[[],[cover]]), \
             patch('PIL.ImageGrab.grab',return_value=Image.new('RGB',(300,248))), \
             patch.object(session_reader,'read_reward_image',return_value=[('exp',56)]) as read:
            self.assertIsNone(session_reader.capture_rewards())
        read.assert_not_called()

    def test_covered_hud_is_not_a_character_reading(self):
        box=(100,100,1100,900)
        with patch.object(session_reader,'capture_rewards',return_value=[]), \
             patch.object(game_sync,'find_game_window',return_value=box), \
             patch('screen_visibility.covering_windows',return_value=[(100,828,1100,900)]), \
             patch('PIL.ImageGrab.grab',return_value=Image.new('RGB',(1000,72))), \
             patch.object(session_reader,'read_character_image',return_value={'level':40,'exp':1000}) as read:
            result=session_reader.capture_training()
        self.assertIsNone(result['character']);read.assert_not_called()

    def test_partial_hud_mask_preserves_only_uncovered_pixels(self):
        box=(100,100,1100,900)
        with patch.object(session_reader,'capture_rewards',return_value=[]), \
             patch.object(game_sync,'find_game_window',return_value=box), \
             patch('screen_visibility.covering_windows',return_value=[(900,828,1100,900)]), \
             patch('PIL.ImageGrab.grab',return_value=Image.new('RGB',(1000,72),'white')), \
             patch.object(session_reader,'read_character_image',return_value=None) as read:
            session_reader.capture_training()
        image=read.call_args.args[0]
        self.assertEqual(image.getpixel((0,20)),(255,255,255))
        self.assertEqual(image.getpixel((900,20)),(0,0,0))

    def test_covered_context_does_not_identify_browser_monsters(self):
        box=(100,100,1100,900)
        with patch.object(game_sync,'find_game_window',return_value=box), \
             patch('screen_visibility.covering_windows',return_value=[box]), \
             patch('PIL.ImageGrab.grab',return_value=Image.new('RGB',(1000,800))) as grab, \
             patch.object(game_sync,'find_minimap',return_value=None), \
             patch.object(training_context,'context_lines',return_value=[]) as read:
            result=training_context.capture_context({}, {})
        self.assertEqual(result.get('mobs'),[])
        self.assertTrue(result.get('map_blocked'))
        grab.assert_not_called();read.assert_not_called()


if __name__=='__main__':unittest.main()
