"""The GPS window's content drawn as one picture.

Tk paints each piece of a window separately, so changing a multi-part panel (text that
re-wraps, panels that move) showed half-updated frames for a moment: a flicker on every map
change. One picture swapped for another is a single change on screen, so it can't flicker.
"""
from PIL import Image, ImageDraw, ImageFont

from widgets import C

_fonts = {}


SYMBOLS = set("★◉●☆✓✔")  # not in Segoe UI; drawn with Segoe UI Symbol instead


def font(size, bold=False, symbols=False):
    key = (size, bold, symbols)
    if key not in _fonts:
        names = (("seguisym.ttf",) if symbols else ()) +                 (("segoeuib.ttf", "arialbd.ttf") if bold else ("segoeui.ttf", "arial.ttf"))
        for name in names:
            try:
                _fonts[key] = ImageFont.truetype(name, size)
                break
            except OSError:
                continue
        else:
            _fonts[key] = ImageFont.load_default()
    return _fonts[key]


def wrap(text, fnt, width):
    """Lines of `text` that each fit in `width` pixels."""
    lines, line = [], ""
    for word in text.split(" "):
        trial = f"{line} {word}".strip()
        if line and fnt.getlength(trial) > width:
            lines.append(line)
            line = word
        else:
            line = trial
    return lines + ([line] if line else [])


def _arrow(draw, kind, box, colour):
    """A big direction arrow, drawn as a shape (fonts differ in which arrow symbols they have)."""
    x0, y0, x1, y1 = box
    cx, cy, r = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2
    points = {"right": [(x0, y0), (x1, cy), (x0, y1)], "left": [(x1, y0), (x0, cy), (x1, y1)],
              "up": [(x0, y1), (cx, y0), (x1, y1)], "down": [(x0, y0), (cx, y1), (x1, y0)]}.get(kind)
    if points:
        draw.polygon(points, fill=colour)
    else:  # "talk": a speech bubble
        draw.rounded_rectangle((x0, y0 + 2, x1, y1 - 8), radius=6, fill=colour)
        draw.polygon([(cx - 6, y1 - 9), (cx - 10, y1), (cx + 2, y1 - 9)], fill=colour)
        for dx in (-r / 2, 0, r / 2):
            draw.ellipse((cx + dx - 2, cy - 5, cx + dx + 2, cy - 1), fill=C["card_hi"])


def fit(text, fnt, width):
    """`text` shortened with … so it fits in `width` pixels."""
    if fnt.getlength(text) <= width:
        return text
    while text and fnt.getlength(text + "…") > width:
        text = text[:-1]
    return text.rstrip() + "…"


def compose_strip(view, width, height, px_per_point=4 / 3):
    """The GPS strip: a violet disc with the direction arrow (or a state mark), then two lines,
    `headline` (where to go on this map) and `sub` (which map that leads to, step n of m)."""
    px = lambda pt: max(8, round(pt * px_per_point))
    f_head, f_sub = font(px(10.5), True), font(px(8.5))
    img = Image.new("RGB", (width, height), C["header"])
    d = ImageDraw.Draw(img)
    pad = round(height * 0.16)
    disc = height - 2 * pad
    # the disc and its mark are drawn 4x bigger and shrunk, so their edges are smooth
    big = Image.new("RGBA", (disc * 4, disc * 4), (0, 0, 0, 0))
    b = ImageDraw.Draw(big)
    s = disc * 4
    b.ellipse((0, 0, s - 1, s - 1), fill=C["press"], outline=C["accent"], width=max(4, s // 22))
    inset = s * 0.3
    box = (inset, inset, s - inset, s - inset)
    state = view.get("state")
    if view.get("arrow"):
        _arrow(b, view["arrow"], box, C["gold"])
    elif state == "there":  # a check mark
        b.line([(s * 0.3, s * 0.52), (s * 0.45, s * 0.67), (s * 0.71, s * 0.36)], fill=C["green"],
               width=max(6, s // 10), joint="curve")
    else:  # waiting / no way: three dots
        for k in (-1, 0, 1):
            cx, r = s / 2 + k * s * 0.17, s * 0.05
            b.ellipse((cx - r, s / 2 - r, cx + r, s / 2 + r), fill=C["muted"])
    img.paste(big.resize((disc, disc), Image.LANCZOS), (pad, pad), big.resize((disc, disc), Image.LANCZOS))
    tx = pad + disc + round(pad * 0.9)
    room = width - tx - pad // 2
    head, sub = fit(view.get("headline", ""), f_head, room), fit(view.get("sub", ""), f_sub, room)
    gap = max(1, height // 25)
    total = f_head.size + gap + f_sub.size
    y = (height - total) // 2 - max(1, f_head.size // 8)
    d.text((tx, y), head, font=f_head, fill=C["text"])
    d.text((tx, y + f_head.size + gap), sub, font=font(f_sub.size, symbols=True) if SYMBOLS & set(sub) else f_sub,
           fill=C["link"] if view.get("arrow") else C["muted"])
    return img


def compose_map(view, width, height, px_per_point=4 / 3):
    """The docked GPS's map: exactly width x height, the minimap (portal, NPC or spawns marked)
    made as big as fits, with one small legend line above it, top-aligned."""
    img = Image.new("RGB", (width, height), C["bg"])
    d = ImageDraw.Draw(img)
    f_small = font(max(8, round(7.5 * px_per_point)))
    pad = max(3, height // 40)
    y = pad
    legend = view.get("legend")
    if legend:
        f = font(f_small.size, symbols=True) if SYMBOLS & set(legend) else f_small
        d.text((pad + 2, y), fit(legend, f, width - 2 * pad), font=f, fill=view.get("legend_colour", C["gold"]))
        y += f_small.size + pad
    mm = view.get("minimap")
    if mm is None:
        msg = view.get("message") or "Loading the map..."
        lines = wrap(msg, f_small, width - 2 * pad)
        for line in lines:
            d.text((pad + 2, y), line, font=f_small, fill=C["muted"])
            y += f_small.size + 2
        return img
    if mm.mode == "RGBA":  # meowdb's pictures have see-through margins: the map starts at the top
        box = mm.getchannel("A").getbbox()
        if box:
            mm = mm.crop(box)
    room_w, room_h = width - 2 * pad, height - y - pad
    scale = min(room_w / mm.width, room_h / mm.height)
    if scale <= 0:
        return img
    size = (max(1, round(mm.width * scale)), max(1, round(mm.height * scale)))
    mm = mm.resize(size, Image.LANCZOS if scale < 1 else Image.NEAREST)
    # right under the legend, like the game's own minimap: a wide map leaves its spare room at
    # the bottom instead of a gap above it
    img.paste(mm, ((width - mm.width) // 2, y), mm if mm.mode == "RGBA" else None)
    return img


def compose(view, width, px_per_point=4 / 3, header=True):
    """Draw the GPS content. `view`: title, message (or the NEXT card fields step, arrow, where,
    then_do, dest), chain, steps (list), map_name, legend, legend_colour, minimap (PIL image).
    `px_per_point` matches the text size to the rest of the window (screen scaling, text size).
    Without `header` (the strip already says it): no title, message or NEXT card."""
    px = lambda pt: max(8, round(pt * px_per_point))
    f_title, f_text, f_small = font(px(9.5), True), font(px(8.5)), font(px(7.5))
    f_where, f_dest = font(px(11), True), font(px(9.5), True)
    pad, inner = 8, width - 16
    img = Image.new("RGB", (width, 2000), C["bg"])
    d = ImageDraw.Draw(img)
    y = 4

    def text(lines, fnt, colour, x, y, gap=2):
        for line in lines:
            f = fnt
            if SYMBOLS & set(line):  # a line with ★ / ◉: use the font that has those symbols
                f = font(fnt.size, symbols=True)
            d.text((x, y), line, font=f, fill=colour)
            y += fnt.size + gap
        return y

    def route_lines(y):
        if view.get("chain"):
            y = text(wrap(view["chain"], f_text, inner), f_text, C["muted"], pad, y) + 4
        for line in view.get("steps") or []:
            y = text(wrap(line, f_small, inner), f_small, C["muted"], pad, y, gap=1) + 2
        return y

    def the_map(y):
        mm = view.get("minimap")
        top = y + 2
        y = text([view.get("map_name", "")], f_text, C["text"], pad + 6, top + 4)
        if view.get("legend"):
            y = text([view["legend"]], f_small, view.get("legend_colour", C["gold"]), pad + 6, y)
        if mm is not None:
            y += 4
            img.paste(mm, ((width - mm.width) // 2, y), mm if mm.mode == "RGBA" else None)
            y += mm.height + 4
        d.rounded_rectangle((pad, top, width - pad, y), radius=3, outline=C["border"])
        return y

    if not header:  # under the strip: the map first, then the maps after this one
        return img.crop((0, 0, width, route_lines(the_map(y) + 6) + 4))
    y = text([view["title"]], f_title, C["green"], pad, y) + 4
    if view.get("message"):
        y = text(wrap(view["message"], f_text, inner), f_text, C["muted"], pad, y) + 6
    else:
        # NEXT card
        top = y
        y += 6
        y = text([view["step"]], f_small, C["muted"], pad + 8, y) + 2
        arrow_w = px(24)
        tx = pad + 12 + arrow_w + 10
        tw = width - tx - pad - 8
        body_top = y
        y = text(wrap(view["where"], f_where, tw), f_where, C["gold"], tx, y) + 2
        y = text(wrap(view["then_do"], f_text, tw), f_text, C["text"], tx, y) + 2
        y = text(wrap(view["dest"], f_dest, tw), f_dest, C["green"], tx, y) + 8
        d.rounded_rectangle((pad, top, width - pad, y), radius=4, fill=C["card_hi"])
        # redraw the card's text on top of its background
        y2 = top + 6
        y2 = text([view["step"]], f_small, C["muted"], pad + 8, y2) + 2
        y2 = text(wrap(view["where"], f_where, tw), f_where, C["gold"], tx, y2) + 2
        y2 = text(wrap(view["then_do"], f_text, tw), f_text, C["text"], tx, y2) + 2
        text(wrap(view["dest"], f_dest, tw), f_dest, C["green"], tx, y2)
        _arrow(d, view["arrow"], (pad + 12, body_top + 4, pad + 12 + arrow_w, body_top + 4 + arrow_w), C["gold"])
        y = route_lines(y + 6)
    y = the_map(y)
    return img.crop((0, 0, width, y + 4))
