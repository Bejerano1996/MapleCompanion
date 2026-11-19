import unittest
from types import SimpleNamespace
from unittest.mock import patch

import game_sync


class FakeUser32:
    def __init__(self, windows):self.windows=windows
    def EnumWindows(self, callback, param):
        for hwnd in self.windows:
            if not callback(hwnd,param):break
    def IsWindowVisible(self,hwnd):return self.windows[hwnd].get('visible',True)
    def IsIconic(self,hwnd):return self.windows[hwnd].get('minimized',False)
    def GetWindowTextW(self,hwnd,buffer,size):buffer.value=self.windows[hwnd]['title'];return len(buffer.value)
    def GetClassNameW(self,hwnd,buffer,size):buffer.value=self.windows[hwnd].get('class','MapleStoryClass');return len(buffer.value)
    def GetWindowRect(self,hwnd,pointer):
        rectangle=pointer._obj
        rectangle.left,rectangle.top,rectangle.right,rectangle.bottom=self.windows[hwnd]['rect']
        return True


class GameWindowIdentityTests(unittest.TestCase):
    def test_executable_metadata_uses_only_query_rights_and_closes_handle(self):
        from unittest.mock import Mock
        def process_id(hwnd,pointer):pointer._obj.value=42;return 1
        def image_name(handle,flags,buffer,size):buffer.value=r'C:\Games\MapleStory.exe';return True
        kernel=SimpleNamespace(OpenProcess=Mock(return_value=123),
                               QueryFullProcessImageNameW=Mock(side_effect=image_name),
                               CloseHandle=Mock())
        system=SimpleNamespace(user32=SimpleNamespace(GetWindowThreadProcessId=process_id),kernel32=kernel)
        with patch.object(game_sync.ctypes,'windll',system):
            self.assertEqual(game_sync._process_image(5),'MapleStory.exe')
            kernel.OpenProcess.assert_called_once_with(0x1000,False,42)
            kernel.CloseHandle.assert_called_once_with(123)
            kernel.QueryFullProcessImageNameW.side_effect=OSError('metadata unavailable')
            self.assertIsNone(game_sync._process_image(5))
            self.assertEqual(kernel.CloseHandle.call_count,2)
            kernel.OpenProcess.return_value=0
            self.assertIsNone(game_sync._process_image(5))
            self.assertEqual(kernel.CloseHandle.call_count,2)

    def find(self,windows,images=None):
        fake=FakeUser32(windows)
        with patch.object(game_sync.ctypes,'windll',SimpleNamespace(user32=fake)), \
             patch.object(game_sync,'_process_image',side_effect=lambda hwnd:(images or {}).get(hwnd),create=True):
            return game_sync.find_game_window()

    def test_browser_database_title_is_not_the_game(self):
        windows={1:dict(title='MapleStory Classic World Database',**{'class':'Chrome_WidgetWin_1'},rect=(0,0,1200,900)),
                 2:dict(title='MapleStory',rect=(100,100,1124,868))}
        self.assertEqual(self.find(windows), (100,100,1124,868))

    def test_document_with_matching_title_and_known_other_executable_is_ignored(self):
        windows={1:dict(title='MapleStory notes',**{'class':'OpusApp'},rect=(0,0,1200,900))}
        self.assertIsNone(self.find(windows,{1:'WINWORD.EXE'}))

    def test_minimized_or_too_short_window_is_not_captured(self):
        for values in (dict(minimized=True,rect=(0,0,1200,900)),dict(rect=(0,0,1200,80))):
            self.assertIsNone(self.find({1:dict(title='MapleStory',**values)}))

    def test_game_window_remains_supported_when_metadata_query_is_denied(self):
        rectangle=(100,100,1124,868)
        self.assertEqual(self.find({1:dict(title='MapleStory',rect=rectangle)}),rectangle)

    def test_small_splash_window_does_not_hide_real_game(self):
        windows={1:dict(title='MapleStory',rect=(0,0,1200,80)),
                 2:dict(title='MapleStory',rect=(100,100,1124,868))}
        self.assertEqual(self.find(windows),(100,100,1124,868))


if __name__=='__main__':unittest.main()
