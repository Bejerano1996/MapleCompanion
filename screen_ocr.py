"""Read quest text off the screen with Windows' built-in OCR.

Only takes screenshots (like OBS or Discord screen share); it never reads the game's
memory or sends it any input.
"""
import asyncio

from PIL import Image
import winrt.windows.graphics.imaging as imaging
import winrt.windows.media.ocr as ocr
import winrt.windows.storage.streams as streams
from winrt.windows.globalization import Language

SCALE = 2  # upscaling helps with the game's small pixel font


async def _recognize(img, scale):
    img = img.convert("RGBA")
    writer = streams.DataWriter()
    writer.write_bytes(img.tobytes())
    bitmap = imaging.SoftwareBitmap.create_copy_from_buffer(
        writer.detach_buffer(), imaging.BitmapPixelFormat.RGBA8, img.width, img.height)
    # one engine per image: an engine can only run one recognition at a time
    engine = ocr.OcrEngine.try_create_from_language(Language("en-US"))
    result = await engine.recognize_async(bitmap)
    lines = []
    for line in result.lines:
        words = list(line.words)
        first, last = words[0].bounding_rect, words[-1].bounding_rect
        lines.append({"text": line.text, "x": first.x / scale, "y": first.y / scale,
                      "w": (last.x + last.width - first.x) / scale,
                      "h": max(w.bounding_rect.height for w in words) / scale})
    return lines


def _prepare(img):
    scale = min(SCALE, ocr.OcrEngine.max_image_dimension / max(img.size))
    return img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS), scale


async def _recognize_all(images):
    jobs = [_prepare(i) for i in images]
    results = await asyncio.gather(*(_recognize(big, scale) for big, scale in jobs))
    return [sorted(r, key=lambda l: (round(l["y"] / 6), l["x"])) for r in results]


THRESHOLDS = (110, 80)  # black-and-white passes; 80 catches dark text on bright scenery
WHITE_TEXT = 200         # the minimap's map name: pixels this bright in every channel


def passes(img):
    """The versions of one screenshot to OCR: as-is, plus high-contrast black-and-white ones
    that pull the see-through in-game Quest Helper's text off busy backgrounds."""
    gray = img.convert("L")
    return [img] + [gray.point(lambda p, t=t: 0 if p < t else 255) for t in THRESHOLDS]


def title_passes(img):
    """Versions of the minimap corner for reading the map name: as-is, twice the size, and white
    text only. The name is white on a light-blue bar; Windows OCR often skips that line as-is
    (seen: "Victoria Road" read, "Henesys Hunting Ground I" not), but reads it in the other two."""
    big = img.resize((img.width * 2, img.height * 2), Image.LANCZOS)
    r, g, b = img.convert("RGB").split()
    bright = lambda band: band.point(lambda p: 255 if p >= WHITE_TEXT else 0)
    white = Image.merge("RGB", (bright(r), bright(g), bright(b))).convert("L")  # 255 only if all >=
    white = white.point(lambda p: 0 if p == 255 else 255)  # the white letters, in black on white
    return [img, big, white]


def read_lines(*images, offsets=None):
    """OCR one or more images at once; returns all lines as {text, x, y, w, h}.
    `offsets` ((dx, dy) per image) maps cropped images back to the full screenshot's pixels."""
    results = asyncio.run(_recognize_all(images))
    lines = []
    for i, result in enumerate(results):
        dx, dy = offsets[i] if offsets else (0, 0)
        for line in result:
            line["x"] += dx
            line["y"] += dy
            lines.append(line)
    return lines
