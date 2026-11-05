"""Minimap pictures with markers, drawn from meowdb's map data."""
from PIL import Image, ImageDraw, ImageFont

MINIMAP_WIDTH = 318
MINIMAP_MAX_HEIGHT = 200
PAD, PAD_TOP = 6, 26          # room around the map so a callout near an edge isn't cut off
CALLOUT = "#ffe14d"           # the one thing to go to: bright yellow, ringed and labelled


def _place(detail, portal):
    """(fx, fy): where a portal sits on its map, 0..1 from the left / top; None if unknown."""
    if not detail.get("minimapWidth") or not detail.get("minimapHeight"):
        return None
    return ((portal["x"] + detail["miniMapCenterX"]) / detail["minimapWidth"],
            (portal["y"] + detail["miniMapCenterY"]) / detail["minimapHeight"])


def portal_side(detail, portal):
    """Where a portal sits on its map, in words ("right side, bottom")."""
    place = _place(detail, portal)
    if place is None:  # no map size known
        return f'"{portal.get("name", "?")}" portal'
    fx, fy = place
    side = ("far left" if fx < 0.15 else "left side" if fx < 0.42 else "middle" if fx < 0.58
            else "right side" if fx < 0.85 else "far right")
    height = "top" if fy < 0.35 else "bottom" if fy > 0.7 else ""
    return side + (", " + height if height else "")


def portal_direction(detail, portal):
    """(arrow, plain words) for the GPS card: "▶", "Right edge, at the bottom"."""
    place = _place(detail, portal)
    if place is None:
        return "➜", f'Find the "{portal.get("name", "?")}" portal'
    fx, fy = place
    if fx < 0.2:
        arrow, where = "◀", "Left edge"
    elif fx > 0.8:
        arrow, where = "▶", "Right edge"
    elif fx < 0.42:
        arrow, where = "◀", "Left part of the map"
    elif fx > 0.58:
        arrow, where = "▶", "Right part of the map"
    else:
        arrow, where = ("▲" if fy < 0.5 else "▼"), "Middle of the map"
    height = ", at the top" if fy < 0.35 else ", at the bottom" if fy > 0.7 else ", halfway up"
    return arrow, where + height


def _font(size):
    for name in ("segoeuib.ttf", "arialbd.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _callout(draw, x, y, text):
    """A ring around (x, y), a downward pointer above it and a label: impossible to miss."""
    draw.ellipse((x - 12, y - 12, x + 12, y + 12), outline="black", width=6)
    draw.ellipse((x - 12, y - 12, x + 12, y + 12), outline=CALLOUT, width=4)
    draw.polygon([(x - 7, y - 23), (x + 7, y - 23), (x, y - 14)], fill=CALLOUT, outline="black")
    font = _font(12)
    tw = draw.textlength(text, font=font)
    draw.text((x - tw / 2, y - 39), text, font=font, fill=CALLOUT, stroke_width=2, stroke_fill="black")


def render_minimap(db, map_id, mob_id=None, npc_name=None, exit_portal=None):
    """Minimap image with markers: gold star = NPC, red dots = monster spawns, small blue dots
    = portals. The portal to take next (or the NPC to talk to) gets a big yellow callout,
    "ENTER" / "TALK". Coordinates come from meowdb's map data (background)."""
    detail = db.map_detail(map_id)
    if not (detail and detail.get("hasMinimapImage") and detail.get("minimapWidth")
            and detail.get("minimapHeight")):
        return None
    art = Image.open(db.minimap_png(map_id)).convert("RGBA")
    scale = min(MINIMAP_WIDTH / art.width, MINIMAP_MAX_HEIGHT / art.height)
    art = art.resize((max(1, int(art.width * scale)), max(1, int(art.height * scale))), Image.NEAREST)
    w, h = art.size
    img = Image.new("RGBA", (w + 2 * PAD, h + PAD_TOP + PAD), (0, 0, 0, 0))
    img.alpha_composite(art, (PAD, PAD_TOP))
    draw = ImageDraw.Draw(img)

    def pos(x, y):
        return (PAD + (x + detail["miniMapCenterX"]) / detail["minimapWidth"] * w,
                PAD_TOP + (y + detail["miniMapCenterY"]) / detail["minimapHeight"] * h)

    target = None
    for p in detail.get("portals") or []:
        if p.get("toMapId"):
            x, y = pos(p["x"], p["y"])
            if p.get("name") == exit_portal:
                target = (x, y, "ENTER")
            else:  # the other portals stay small and quiet when one is the goal
                r = 2.5 if exit_portal else 3
                draw.ellipse((x - r, y - r, x + r, y + r),
                             fill="#2f6aa8" if exit_portal else "#4aa8ff", outline="white")
    if mob_id is not None:  # one monster id, or a tuple of them
        wanted = {str(m) for m in (mob_id if isinstance(mob_id, (list, tuple)) else [mob_id])}
        for s in detail.get("spawns") or []:
            if str(s.get("mobId")) in wanted:
                x, y = pos(s["x"], s["y"])
                draw.ellipse((x - 2.5, y - 2.5, x + 2.5, y + 2.5), fill="#ff4d4d", outline="#400")
    if npc_name:
        for n in detail.get("npcs") or []:
            if n.get("name", "").lower() == npc_name.lower():
                x, y = pos(n["x"], n["y"])
                star = [(x, y - 8), (x + 2.5, y - 2.5), (x + 8, y - 2), (x + 4, y + 2), (x + 5, y + 8),
                        (x, y + 5), (x - 5, y + 8), (x - 4, y + 2), (x - 8, y - 2), (x - 2.5, y - 2.5)]
                draw.polygon(star, fill="#ffd45e", outline="black")
                target = target or (x, y, "TALK")
    if target:
        _callout(draw, *target)
    return img
