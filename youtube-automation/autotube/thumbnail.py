"""Thumbnail generation with Pillow: video frame + dark overlay + bold text."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

W, H = 1280, 720
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def _font(size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(FONT_BOLD, size)
    except OSError:
        return ImageFont.load_default(size)


def _hex(color: str) -> tuple[int, int, int]:
    c = color.lstrip("#")
    return tuple(int(c[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_w: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if draw.textlength(trial, font=font) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines[:3]


def make_card(
    headline: str,
    out: Path,
    theme: dict,
    subtext: str = "",
    resolution: tuple[int, int] = (1920, 1080),
) -> Path:
    """Full-frame infographic card: tech background + big stat/label text."""
    w, h = resolution
    bg = _hex(theme.get("bg_color", "#0a0e2a"))
    accent = _hex(theme.get("accent_color", "#4cc9f0"))
    fg = _hex(theme.get("text_color", "#ffffff"))

    img = Image.new("RGB", (w, h), bg)
    draw = ImageDraw.Draw(img)

    # subtle grid + accent bar for a "tech infographic" feel
    step = max(40, h // 18)
    grid = tuple(min(255, c + 12) for c in bg)
    for x in range(0, w, step):
        draw.line([(x, 0), (x, h)], fill=grid, width=1)
    for y in range(0, h, step):
        draw.line([(0, y), (w, y)], fill=grid, width=1)
    draw.rectangle([0, 0, int(w * 0.02), h], fill=accent)

    text = headline.upper().strip() or "AI NEWS"
    size = int(h * 0.13)
    font = _font(size)
    max_w = int(w * 0.82)
    lines = _wrap(draw, text, font, max_w)
    while size > 40 and (len(lines) > 3 or any(draw.textlength(l, font=font) > max_w for l in lines)):
        size -= 6
        font = _font(size)
        lines = _wrap(draw, text, font, max_w)

    line_h = int(size * 1.15)
    total = line_h * len(lines)
    y = (h - total) // 2 - (int(h * 0.04) if subtext else 0)
    x = int(w * 0.09)
    for i, line in enumerate(lines):
        draw.text((x, y + i * line_h), line, font=font, fill=fg,
                  stroke_width=max(2, size // 20), stroke_fill=(0, 0, 0))

    if subtext:
        sfont = _font(int(h * 0.045))
        draw.text((x, y + total + int(h * 0.03)), subtext.upper()[:60],
                  font=sfont, fill=accent, stroke_width=2, stroke_fill=(0, 0, 0))

    img.save(out, "JPEG", quality=92)
    return out


def make_thumbnail(
    text: str,
    out: Path,
    theme: dict,
    frame: Path | None = None,
) -> Path:
    bg = _hex(theme.get("bg_color", "#0d1321"))
    accent = _hex(theme.get("accent_color", "#ffd166"))
    fg = _hex(theme.get("text_color", "#ffffff"))

    if frame and frame.exists():
        img = Image.open(frame).convert("RGB").resize((W, H))
        img = ImageEnhance.Brightness(img).enhance(0.55)
        img = ImageEnhance.Contrast(img).enhance(1.15)
        img = img.filter(ImageFilter.GaussianBlur(1))
    else:
        img = Image.new("RGB", (W, H), bg)

    # left-to-right dark gradient so text pops
    overlay = Image.new("L", (W, 1))
    for x in range(W):
        overlay.putpixel((x, 0), int(200 * max(0.0, 1 - x / (W * 0.75))))
    overlay = overlay.resize((W, H))
    img = Image.composite(Image.new("RGB", (W, H), (5, 5, 8)), img, overlay)

    draw = ImageDraw.Draw(img)
    text = text.upper().strip() or "WATCH THIS"
    size = 128
    font = _font(size)
    max_w = int(W * 0.62)
    lines = _wrap(draw, text, font, max_w)
    while size > 56 and (
        len(lines) > 2 or any(draw.textlength(l, font=font) > max_w for l in lines)
    ):
        size -= 8
        font = _font(size)
        lines = _wrap(draw, text, font, max_w)

    line_h = int(size * 1.18)
    total_h = line_h * len(lines)
    y = (H - total_h) // 2
    x = int(W * 0.06)

    # accent bar
    draw.rectangle([x - 28, y + 6, x - 14, y + total_h - 6], fill=accent)

    for i, line in enumerate(lines):
        ly = y + i * line_h
        # last line in accent color, rest in fg; heavy black stroke for contrast
        color = accent if i == len(lines) - 1 and len(lines) > 1 else fg
        draw.text((x, ly), line, font=font, fill=color,
                  stroke_width=max(4, size // 16), stroke_fill=(0, 0, 0))

    img.save(out, "JPEG", quality=92)
    return out
