import unittest
from types import SimpleNamespace
from unittest.mock import patch

import game_sync
import screen_visibility as visibility
from test_game_window_identity import FakeUser32


class FakeZOrder(FakeUser32):
    def GetTopWindow(self,parent):return next(iter(self.windows),0)
    def GetWindow(self,hwnd,kind):
        keys=list(self.windows)
        index=keys.index(hwnd)+1
        return keys[index] if index<len(keys) else 0


class VisibilityTests(unittest.TestCase):
    def test_union_coverage_is_exact_and_clipped(self):
        rect=(10,10,110,110)
        self.assertTrue(visibility.fully_covered(rect,[(0,0,60,200),(60,0,200,200)]))
        self.assertFalse(visibility.fully_covered(rect,[(0,0,59,200),(60,0,200,200)]))
        self.assertFalse(visibility.fully_covered(rect,[(110,10,200,110)]))

    def test_plain_fixture_rect_does_not_query_os(self):
        with patch.object(visibility.ctypes,'windll',None):
            self.assertEqual(visibility.covering_windows((0,0,100,100)),[])

    def test_union_matches_pixel_oracle_for_variable_overlaps(self):
        import random
        randomizer=random.Random(340)
        for _ in range(1000):
            rectangle=(0,0,8,7)
            covers=[]
            for _ in range(randomizer.randrange(12)):
                x1,x2=sorted(randomizer.sample(range(-3,12),2))
                y1,y2=sorted(randomizer.sample(range(-3,11),2))
                covers.append((x1,y1,x2,y2))
            oracle=all(any(left<=x<right and top<=y<bottom for left,top,right,bottom in covers)
                       for x in range(8) for y in range(7))
            self.assertEqual(visibility.fully_covered(rectangle,covers),oracle,covers)

    def test_only_higher_visible_windows_cover_game(self):
        rect=game_sync.GameWindowRect((100,100,1100,900),2)
        user=FakeZOrder({1:dict(title='Browser',rect=(0,0,400,500)),
                         2:dict(title='MapleStory',rect=tuple(rect)),
                         3:dict(title='Below game',rect=(100,100,1100,900))})
        with patch.object(visibility.ctypes,'windll',SimpleNamespace(user32=user)):
            self.assertEqual(visibility.covering_windows(rect),[(100,100,400,500)])

    def test_moved_or_missing_game_blocks_old_capture(self):
        rect=game_sync.GameWindowRect((100,100,1100,900),2)
        user=FakeZOrder({2:dict(title='MapleStory',rect=(101,100,1101,900))})
        with patch.object(visibility.ctypes,'windll',SimpleNamespace(user32=user)):
            self.assertEqual(visibility.covering_windows(rect),[tuple(rect)])

    def test_unreadable_higher_window_does_not_allow_unmasked_ocr(self):
        rect=game_sync.GameWindowRect((100,100,1100,900),2)
        user=FakeZOrder({1:dict(title='Unknown overlay',rect=tuple(rect)),
                         2:dict(title='MapleStory',rect=tuple(rect))})
        original=user.GetWindowRect
        user.GetWindowRect=lambda hwnd,pointer: False if hwnd==1 else original(hwnd,pointer)
        with patch.object(visibility.ctypes,'windll',SimpleNamespace(user32=user)):
            self.assertEqual(visibility.covering_windows(rect),[tuple(rect)])

    def test_invisible_minimized_cloaked_and_zero_alpha_windows_are_ignored(self):
        rect=game_sync.GameWindowRect((100,100,1100,900),5)
        windows={1:dict(title='Hidden',rect=tuple(rect),visible=False),
                 2:dict(title='Minimized',rect=tuple(rect),minimized=True),
                 3:dict(title='Other desktop',rect=tuple(rect)),
                 4:dict(title='Transparent',rect=tuple(rect)),
                 5:dict(title='MapleStory',rect=tuple(rect))}
        user=FakeZOrder(windows)
        with patch.object(visibility.ctypes,'windll',SimpleNamespace(user32=user)), \
             patch.object(visibility,'_cloaked',side_effect=lambda hwnd:hwnd==3), \
             patch.object(visibility,'_transparent',side_effect=lambda hwnd,u:hwnd==4):
            self.assertEqual(visibility.covering_windows(rect),[])

    def test_z_order_cycle_blocks_capture(self):
        rect=game_sync.GameWindowRect((100,100,1100,900),2)
        user=FakeZOrder({1:dict(title='Overlay',rect=(0,0,200,200)),
                         2:dict(title='MapleStory',rect=tuple(rect))})
        user.GetWindow=lambda hwnd,kind:1
        with patch.object(visibility.ctypes,'windll',SimpleNamespace(user32=user)):
            self.assertEqual(visibility.covering_windows(rect),[tuple(rect)])


if __name__=='__main__':unittest.main()
