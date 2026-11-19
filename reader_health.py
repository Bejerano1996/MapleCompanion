"""Ephemeral screen-reader health. AUTO enabled is not proof of a fresh reading."""
class ReaderHealth:
    def __init__(self):
        self.game = None
        self.captured_at = None
        self.known = 0
        self.references = 0
        self.error = None

    def record(self, result, now, captured_at=None):
        self.error = None
        self.game = result is not None and bool(result.get('window', True))
        if result is not None and result.get('capture_blocked'):
            self.error = 'game area covered by overlapping windows'
            return
        if result is None or result.get('map_only'):
            return
        self.captured_at = now if captured_at is None else captured_at
        self.known = len(set(result.get('tracked') or []))
        self.references = len(result.get('references') or [])

    def failed(self, reason):
        self.error = reason

    def status(self, auto, data_ready, now):
        suffix = '\nClick to switch AUTO on/off.'
        if not auto:
            return 'disabled', 'AUTO off: quest titles update only on manual sync.' + suffix
        if not data_ready:
            return 'gold', 'AUTO waiting for game data. Additional quest sources can enable reference mode.' + suffix
        if self.error:
            return 'gold', 'AUTO waiting for a fresh screen read: ' + self.error + suffix
        if self.game is False:
            return 'gold', 'AUTO waiting: MapleStory window was not found. Saved quests are unchanged.' + suffix
        if self.captured_at is None:
            return 'gold', 'AUTO on: waiting for the first quest screen reading.' + suffix
        age = max(0, now-self.captured_at)
        if age > 15:
            return 'gold', f'AUTO on: last quest screen read {int(age)}s ago; waiting for fresh evidence.' + suffix
        counts = f'{self.known} tracked quest titles, {self.references} additional references'
        if not self.known and not self.references:
            return 'gold', f'Game found · quest screen read {int(age)}s ago. No quest titles visible; open the in-game Quest Helper.' + suffix
        return ('green' if age <= 6 else 'gold'), f'Quest screen read {int(age)}s ago · {counts}.' + suffix
