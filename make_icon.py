"""Draws the UMBRΛLE sigil and app icon from the brand logo (assets/umbrale_logo.png, white
strokes and a violet dot on black):

- assets/sigil.png: the sigil alone on a transparent background, used in the overlay's title row
- icon.ico / icon.png: the sigil on an obsidian tile, for the .exe, taskbar and dialogs
"""
import os

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
LOGO = os.path.join(HERE, "assets", "umbrale_logo.png")
SIGIL = os.path.join(HERE, "assets", "sigil.png")
CROP = (112, 132, 520, 491)    # the triangle in the logo, with a little room around it
STROKE = (238, 234, 246)       # silver-white strokes
DOT = (139, 92, 246)           # the arcane violet accent (#8B5CF6)


def sigil(size=512):
    """The logo's strokes and dot as clean colours, with the black background turned into
    transparency (the logo's soft edges become soft alpha, so it stays smooth when shrunk)."""
    src = Image.open(LOGO).convert("RGB").crop(CROP)
    side = max(src.size)
    square = Image.new("RGB", (side, side), (0, 0, 0))
    square.paste(src, ((side - src.width) // 2, (side - src.height) // 2))
    out = Image.new("RGBA", square.size)
    pixels, dst = square.load(), out.load()
    for y in range(side):
        for x in range(side):
            r, g, b = pixels[x, y]
            violet = b > r + 50 and b > g + 80
            # brightness above the dark background's noise becomes opacity
            level = (max(r, g, b) - 45) / (215 - 45) if not violet else (b - 40) / (215 - 40)
            alpha = round(255 * min(1.0, max(0.0, level)))
            dst[x, y] = (*(DOT if violet else STROKE), alpha)
    return out.resize((size, size), Image.LANCZOS)


def icon(mark, size=512):
    """The sigil on a rounded obsidian tile with a thin violet rim."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((8, 8, size - 8, size - 8), radius=size // 6, fill="#09090F", outline="#3B3260",
                        width=size // 64)
    inner = round(size * 0.74)
    m = mark.resize((inner, inner), Image.LANCZOS)
    img.alpha_composite(m, ((size - inner) // 2, (size - inner) // 2 + size // 40))
    return img


if __name__ == "__main__":
    mark = sigil()
    mark.save(SIGIL)
    tile = icon(mark)
    tile.save(os.path.join(HERE, "icon.ico"), sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64),
                                                    (128, 128), (256, 256)])
    tile.resize((256, 256), Image.LANCZOS).save(os.path.join(HERE, "icon.png"))
    print("assets/sigil.png, icon.ico and icon.png written")
