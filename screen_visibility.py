"""OS-window occlusion for screen-only readers; no game input or memory access."""
import ctypes
import ctypes.wintypes as win


def intersection(a, b):
    left, top = max(a[0], b[0]), max(a[1], b[1])
    right, bottom = min(a[2], b[2]), min(a[3], b[3])
    return (left, top, right, bottom) if left < right and top < bottom else None


def fully_covered(rectangle, covers):
    """Exact half-open rectangle union test, without allocating a screenshot-size mask."""
    clips = [clip for cover in covers if (clip := intersection(rectangle, cover))]
    if not clips:
        return False
    if rectangle in clips:
        return True
    xs = sorted({rectangle[0], rectangle[2], *(value for clip in clips for value in (clip[0], clip[2]))})
    for left, right in zip(xs, xs[1:]):
        intervals = sorted((clip[1], clip[3]) for clip in clips if clip[0] <= left and clip[2] >= right)
        cursor = rectangle[1]
        for top, bottom in intervals:
            if top > cursor:
                break
            cursor = max(cursor, bottom)
        if cursor < rectangle[3]:
            return False
    return True


def _cloaked(hwnd):
    try:
        value = win.DWORD()
        result = ctypes.windll.dwmapi.DwmGetWindowAttribute(win.HWND(hwnd), 14, ctypes.byref(value), ctypes.sizeof(value))
        return result == 0 and bool(value.value)
    except (AttributeError, OSError):
        return False


def _transparent(hwnd, user32):
    try:
        getter=user32.GetWindowLongW
        try:
            getter.argtypes=[win.HWND,ctypes.c_int]
        except AttributeError:pass
        if getter(hwnd, -20) & 0x80000:  # WS_EX_LAYERED
            color, alpha, flags = win.DWORD(), win.BYTE(), win.DWORD()
            layered=user32.GetLayeredWindowAttributes
            try:
                layered.argtypes=[win.HWND,ctypes.POINTER(win.DWORD),ctypes.POINTER(win.BYTE),ctypes.POINTER(win.DWORD)]
            except AttributeError:pass
            if layered(hwnd, ctypes.byref(color), ctypes.byref(alpha), ctypes.byref(flags)):
                return bool(flags.value & 2) and alpha.value == 0  # LWA_ALPHA
    except (AttributeError, OSError):
        pass
    return False


def covering_windows(game_rectangle):
    """Visible higher-Z windows clipped to a live game's screen rectangle.

    Plain rectangles used by image/unit-test callers have no OS identity and do
    not query the desktop. A moved/disappeared game conservatively blocks the
    old rectangle until the next capture locates it again.
    """
    game = getattr(game_rectangle, 'hwnd', None)
    if not game:
        return []
    blocked = [tuple(game_rectangle)]
    try:
        user32 = ctypes.windll.user32
        # These calls read window-manager metadata only.
        for name, args, result in (
                ('GetTopWindow', [win.HWND], win.HWND),
                ('GetWindow', [win.HWND, win.UINT], win.HWND),
                ('GetWindowRect', [win.HWND, ctypes.POINTER(win.RECT)], win.BOOL),
                ('IsWindowVisible', [win.HWND], win.BOOL),
                ('IsIconic', [win.HWND], win.BOOL)):
            function = getattr(user32, name)
            try:
                function.argtypes, function.restype = args, result
            except AttributeError:  # deterministic Python fakes
                pass
        current = win.RECT()
        if not user32.IsWindowVisible(game) or user32.IsIconic(game) or _cloaked(game):
            return blocked
        if not user32.GetWindowRect(game, ctypes.byref(current)):
            return blocked
        if (current.left, current.top, current.right, current.bottom) != tuple(game_rectangle):
            return blocked
        covers, visited = [], set()
        hwnd = user32.GetTopWindow(None)
        while hwnd and hwnd != game and len(visited) < 1024:
            if hwnd in visited:
                return blocked
            visited.add(hwnd)
            if user32.IsWindowVisible(hwnd) and not user32.IsIconic(hwnd) and not _cloaked(hwnd) and not _transparent(hwnd, user32):
                rect = win.RECT()
                if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                    # Its visible pixels cannot be located safely during this race.
                    return blocked
                clip = intersection(game_rectangle, (rect.left, rect.top, rect.right, rect.bottom))
                if clip:
                    covers.append(clip)
            hwnd = user32.GetWindow(hwnd, 2)  # GW_HWNDNEXT, explicit Z order
        return covers if hwnd == game else blocked
    except (AttributeError, OSError, ValueError):
        return blocked
