"""
CatchTheBrief — Title Card Generator (Session 13)

Replaces Pollinations.AI illustrations with branded 1200x630 title cards that
are generated server-side at publish time. PNG (universally accepted by Twitter,
Facebook, LinkedIn for og:image).

Public API (all return an absolute URL to the rendered card, or "" on failure):
  build_for_article(title, category, slug)
  build_for_day(date_iso, brief_count=5)
  build_for_editor_note(title, date_iso)
  build_default()

Standalone usage: `python generate_title_card.py` regenerates the default OG
card so you can preview it.

Dependency: Pillow. Fonts are discovered from common system locations on
Ubuntu / Windows / macOS — no font files are bundled.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("Pillow not installed — title cards will be skipped (callers fall back to og-default).")

SITE_URL    = "https://catchthebrief.com"
CARDS_DIR   = Path("images/cards")
DEFAULT_DIR = Path("images")
DEFAULT_PATH = DEFAULT_DIR / "og-default.png"
W, H = 1200, 630

# Strong, saturated gradients. White text reads on all of these.
CATEGORY_GRADIENTS = {
    "AI & ML":         ((124, 58, 237),  (76, 29, 149)),    # purple → deep purple
    "Startup Funding": ((5, 150, 105),   (6, 95, 70)),      # emerald → deep green
    "Digital India":   ((220, 38, 38),   (127, 29, 29)),    # red → dark red
    "Product Launch":  ((217, 119, 6),   (120, 53, 15)),    # amber → burnt orange
    "India Tech":      ((37, 99, 235),   (30, 64, 175)),    # blue → deep blue
}
DEFAULT_GRADIENT = ((37, 99, 235), (124, 58, 237))   # blue → purple (brand mix)
EDITOR_GRADIENT  = ((180, 83, 9),  (120, 53, 15))    # amber → burnt orange (editor's note kicker palette)

# Font search order. The first existing path wins.
BOLD_CANDIDATES = [
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/segoeuib.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]
REGULAR_CANDIDATES = [
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/Library/Fonts/Arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]


# ── Internals ────────────────────────────────────────────────────────────────

def _find_font(candidates, size):
    if not PIL_AVAILABLE:
        return None
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _make_gradient(color1, color2):
    """135deg linear gradient — color1 at top-left, color2 at bottom-right."""
    base = Image.new("RGB", (W, H), color1)
    top  = Image.new("RGB", (W, H), color2)
    diag = W + H - 2
    # Build the mask as a raw byte buffer — significantly faster than putdata.
    buf = bytearray(W * H)
    for y in range(H):
        row_off = y * W
        for x in range(W):
            buf[row_off + x] = int(255 * (x + y) / diag)
    mask = Image.frombytes("L", (W, H), bytes(buf))
    base.paste(top, (0, 0), mask)
    return base


def _wrap(text, font, draw, max_width):
    """Greedy word-wrap to fit max_width pixels."""
    words = text.split()
    lines, cur = [], ""
    for w in words:
        candidate = (cur + " " + w).strip()
        bbox = draw.textbbox((0, 0), candidate, font=font)
        if (bbox[2] - bbox[0]) <= max_width or not cur:
            cur = candidate
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _fit_title(title, draw, max_width, max_lines, start_size, min_size):
    size = start_size
    while size >= min_size:
        font = _find_font(BOLD_CANDIDATES, size)
        lines = _wrap(title, font, draw, max_width)
        if len(lines) <= max_lines:
            return font, lines, size
        size -= 4
    font = _find_font(BOLD_CANDIDATES, min_size)
    lines = _wrap(title, font, draw, max_width)
    return font, lines[:max_lines], min_size


def _line_height(font, draw):
    bbox = draw.textbbox((0, 0), "Mg", font=font)
    return bbox[3] - bbox[1]


def _render_card(out_path, *, title, kicker, gradient):
    """Core renderer. Writes a PNG and returns its absolute URL, or '' on failure."""
    if not PIL_AVAILABLE:
        return ""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    img = _make_gradient(*gradient)
    draw = ImageDraw.Draw(img)

    px, py = 80, 80
    white = (255, 255, 255)
    muted = (235, 235, 245)

    # ── Kicker (top-left)
    kicker_font = _find_font(REGULAR_CANDIDATES, 26)
    draw.text((px, py), kicker.upper(), font=kicker_font, fill=muted)
    kicker_h = _line_height(kicker_font, draw)

    # ── Title — fit-to-box
    title_box_w = W - 2 * px
    title_top   = py + kicker_h + 32
    title_bot   = H - py - 90      # reserve room for wordmark + accent
    avail_h     = title_bot - title_top

    title_font, lines, _size = _fit_title(
        title, draw,
        max_width  = title_box_w,
        max_lines  = 4,
        start_size = 84,
        min_size   = 44,
    )
    lh = _line_height(title_font, draw)
    line_gap = int(lh * 0.30)
    total_h = lh * len(lines) + line_gap * max(0, len(lines) - 1)
    # Vertically center the title block within the available band.
    block_top = title_top + max(0, (avail_h - total_h) // 2) - 8
    for i, ln in enumerate(lines):
        y = block_top + i * (lh + line_gap)
        draw.text((px, y), ln, font=title_font, fill=white)

    # ── Accent bar (bottom-left)
    bar_y = H - py - 6
    draw.rectangle([px, bar_y, px + 64, bar_y + 4], fill=white)

    # ── Wordmark (bottom-right)
    wm_font = _find_font(BOLD_CANDIDATES, 28)
    wordmark = "CatchTheBrief"
    wm_bbox = draw.textbbox((0, 0), wordmark, font=wm_font)
    ww = wm_bbox[2] - wm_bbox[0]
    wh = wm_bbox[3] - wm_bbox[1]
    wm_x = W - px - ww
    wm_y = H - py - wh - 4
    draw.text((wm_x, wm_y), wordmark, font=wm_font, fill=white)

    img.save(out_path, "PNG", optimize=True)
    rel = out_path.as_posix()
    if rel.startswith("/"):
        rel = rel[1:]
    return f"{SITE_URL}/{rel}"


def _nice_date(iso):
    try:
        dt = datetime.strptime(iso, "%Y-%m-%d")
        return f"{dt.day} {dt.strftime('%B')} {dt.year}"
    except Exception:
        return iso


# ── Public API ───────────────────────────────────────────────────────────────

def build_for_article(title, category, slug):
    gradient = CATEGORY_GRADIENTS.get(category, DEFAULT_GRADIENT)
    out = CARDS_DIR / f"{slug}.png"
    return _render_card(out, title=title, kicker=category, gradient=gradient)


def build_for_day(date_iso, brief_count=5):
    nice = _nice_date(date_iso)
    brief_word = "brief" if brief_count == 1 else "briefs"
    title = f"{brief_count} {brief_word} from {nice}"
    out = CARDS_DIR / f"day-{date_iso}.png"
    return _render_card(out, title=title, kicker="DAILY ARCHIVE", gradient=DEFAULT_GRADIENT)


def build_for_editor_note(title, date_iso):
    out = CARDS_DIR / f"note-{date_iso}.png"
    return _render_card(out, title=title, kicker="EDITOR'S NOTE", gradient=EDITOR_GRADIENT)


def build_default():
    """Generate the site-wide fallback og:image at /images/og-default.png."""
    DEFAULT_DIR.mkdir(parents=True, exist_ok=True)
    return _render_card(
        DEFAULT_PATH,
        title="India's daily tech & startup briefing",
        kicker="CATCHTHEBRIEF",
        gradient=DEFAULT_GRADIENT,
    )


if __name__ == "__main__":
    if not PIL_AVAILABLE:
        print("Pillow not installed. Run `pip install Pillow` and retry.")
        raise SystemExit(1)
    print("Generating default OG card ->", build_default() or "FAILED")
    print("Generating sample article card ->",
          build_for_article("Sample headline: India's startup funding hits a new high in Q4",
                            "Startup Funding", "sample-card"))
    print("Generating sample day card ->", build_for_day("2026-05-14"))
    print("Generating sample editor note card ->",
          build_for_editor_note("Why I started CatchTheBrief", "2026-05-14"))
