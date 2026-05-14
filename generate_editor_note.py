"""
CatchTheBrief — Editor's Note generator.

Reads markdown files in editor_notes/*.md (filename = YYYY-MM-DD.md),
renders each one to editor-notes/YYYY-MM-DD.html using templates/editor_note.html,
generates editor-notes/index.html (chronological list, newest first),
and exposes latest_note() / banner_html() helpers for the homepage.

Falls back gracefully: zero markdown files => zero output, no errors.

Markdown supported (small, intentional subset — no external library):
  - YAML-ish front matter: --- title: ... ---
  - Blank-line-separated paragraphs
  - ## subheadings
  - **bold**, *italic*, [text](url)
"""

from __future__ import annotations

import html
import re
import urllib.parse
from datetime import datetime
from pathlib import Path

SITE_URL       = "https://catchthebrief.com"
NOTES_SRC_DIR  = Path("editor_notes")
NOTES_OUT_DIR  = Path("editor-notes")
TEMPLATE_PATH  = Path("templates/editor_note.html")
DATE_RE        = re.compile(r"^(\d{4}-\d{2}-\d{2})\.md$", re.IGNORECASE)
FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _nice_date(iso: str) -> str:
    try:
        dt = datetime.strptime(iso, "%Y-%m-%d")
        return f"{dt.day} {dt.strftime('%B')} {dt.year}"
    except ValueError:
        return iso


def _parse_front_matter(text: str) -> tuple[dict, str]:
    m = FRONT_MATTER_RE.match(text)
    if not m:
        return {}, text
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            meta[k.strip().lower()] = v.strip().strip('"').strip("'")
    return meta, text[m.end():]


def _inline_md(text: str) -> str:
    """Inline markdown: bold, italic, links. Escapes HTML first."""
    out = html.escape(text)
    # links [text](url) — do these before italics so the URL underscores survive
    out = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda m: f'<a href="{html.escape(m.group(2), quote=True)}">{m.group(1)}</a>',
        out,
    )
    # **bold**
    out = re.sub(r"\*\*([^*\n]+)\*\*", r"<strong>\1</strong>", out)
    # *italic*  (single asterisks; avoid eating the bold we just made)
    out = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", out)
    return out


def _render_body(md: str) -> str:
    """Tiny markdown -> HTML for the body of a note."""
    blocks = re.split(r"\n\s*\n", md.strip())
    rendered = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        if block.startswith("## "):
            rendered.append(f"<h2>{_inline_md(block[3:].strip())}</h2>")
        elif block.startswith("# "):
            # Treat a leading h1 inside body as h2 — the page already has the h1 title.
            rendered.append(f"<h2>{_inline_md(block[2:].strip())}</h2>")
        else:
            # Collapse single internal newlines into spaces inside a paragraph.
            paragraph = re.sub(r"\s*\n\s*", " ", block)
            rendered.append(f"<p>{_inline_md(paragraph)}</p>")
    return "\n      ".join(rendered)


def _read_note(path: Path) -> dict | None:
    m = DATE_RE.match(path.name)
    if not m:
        return None
    date_iso = m.group(1)
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as e:
        print(f"  editor-notes: cannot read {path}: {e}")
        return None
    meta, body = _parse_front_matter(raw)
    title = meta.get("title") or "Editor's Note"
    body_html = _render_body(body)
    # Plain-text excerpt for meta description — derived from raw markdown
    # (not from rendered HTML, to avoid double-escaping HTML entities).
    plain = body
    plain = re.sub(r"^---.*?---\s*", "", plain, flags=re.DOTALL)  # safety re-strip
    plain = re.sub(r"^#{1,6}\s+", "", plain, flags=re.MULTILINE)  # heading markers
    plain = re.sub(r"\*\*([^*\n]+)\*\*", r"\1", plain)             # bold
    plain = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"\1", plain)    # italic
    plain = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", plain)         # links
    plain = re.sub(r"\s+", " ", plain).strip()
    excerpt = plain[:160]
    return {
        "date":      date_iso,
        "nice_date": _nice_date(date_iso),
        "title":     title,
        "body_html": body_html,
        "excerpt":   excerpt,
        "slug":      date_iso,
    }


def _load_all() -> list[dict]:
    if not NOTES_SRC_DIR.exists():
        return []
    notes = []
    for path in sorted(NOTES_SRC_DIR.glob("*.md")):
        n = _read_note(path)
        if n:
            notes.append(n)
    notes.sort(key=lambda n: n["date"], reverse=True)
    return notes


# ── Page rendering ───────────────────────────────────────────────────────────

def _render_note_page(note: dict, others: list[dict]) -> str:
    if not TEMPLATE_PATH.exists():
        return ""
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    canonical = f"{SITE_URL}/editor-notes/{note['slug']}.html"
    other_items = []
    for o in others:
        if o["date"] == note["date"]:
            continue
        other_items.append(
            f'<li><span class="on-date">{o["nice_date"]}</span>'
            f'<a href="/editor-notes/{o["slug"]}.html">{html.escape(o["title"])}</a></li>'
        )
    other_html = ""
    if other_items:
        other_html = (
            '<div class="other-notes"><h3>Past notes</h3><ul>'
            + "".join(other_items)
            + "</ul></div>"
        )
    replacements = {
        "{{TITLE}}":             html.escape(note["title"]),
        "{{TITLE_URL_ENCODED}}": urllib.parse.quote(note["title"]),
        "{{META_DESCRIPTION}}":  html.escape(note["excerpt"], quote=True),
        "{{CANONICAL_URL}}":     canonical,
        "{{ISO_DATE}}":          note["date"],
        "{{NICE_DATE}}":         note["nice_date"],
        "{{BODY_HTML}}":         note["body_html"],
        "{{OTHER_NOTES_HTML}}":  other_html,
    }
    out = template
    for k, v in replacements.items():
        out = out.replace(k, v)
    return out


def _render_index(notes: list[dict]) -> str:
    """Render editor-notes/index.html — a simple chronological list."""
    if not notes:
        return ""
    items = []
    for n in notes:
        items.append(
            '<li class="note-item">'
            f'<a href="/editor-notes/{n["slug"]}.html">'
            f'<span class="note-date">{n["nice_date"]}</span>'
            f'<span class="note-title">{html.escape(n["title"])}</span>'
            f'<span class="note-excerpt">{html.escape(n["excerpt"])}…</span>'
            "</a></li>"
        )
    page = f"""<!DOCTYPE html>
<html lang="en-IN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="icon" type="image/svg+xml" href="/favicon.svg">
  <title>Editor's Notes — CatchTheBrief</title>
  <meta name="description" content="Personal column from the editor of CatchTheBrief. Weekly notes on India tech, the briefing, and what we're missing.">
  <meta property="og:title" content="Editor's Notes — CatchTheBrief">
  <meta property="og:description" content="Personal column from the editor of CatchTheBrief.">
  <link rel="canonical" href="{SITE_URL}/editor-notes/">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: 'Inter', sans-serif; background: #FAFAFA; color: #1A1A2E; line-height: 1.6; -webkit-font-smoothing: antialiased; }}
    a {{ color: inherit; text-decoration: none; }}
    header {{ border-bottom: 1px solid #E2E8F0; padding: 0 20px; background: #fff; }}
    .header-inner {{ max-width: 1100px; margin: 0 auto; height: 60px; display: flex; align-items: center; justify-content: space-between; }}
    .logo {{ font-family: 'Space Grotesk', sans-serif; font-size: 20px; font-weight: 700; }}
    .logo span {{ color: #2563EB; }}
    .back-link {{ font-size: 13px; font-weight: 600; color: #4A5568; padding: 8px 16px; border: 1.5px solid #CBD5E0; border-radius: 999px; background: #fff; }}
    .back-link:hover {{ color: #2563EB; border-color: #2563EB; }}
    main {{ max-width: 720px; margin: 0 auto; padding: 56px 20px 80px; }}
    .kicker {{ display: inline-block; font-family: 'Space Grotesk', sans-serif; font-size: 11px; font-weight: 700; letter-spacing: 1.2px; text-transform: uppercase; color: #B45309; background: #FFFBEB; border: 1px solid #FDE68A; padding: 5px 11px; border-radius: 999px; margin-bottom: 14px; }}
    h1 {{ font-family: 'Space Grotesk', sans-serif; font-size: clamp(32px, 5vw, 44px); font-weight: 700; letter-spacing: -0.6px; line-height: 1.15; margin-bottom: 12px; }}
    .page-sub {{ color: #4A5568; font-size: 17px; margin-bottom: 36px; }}
    ul.notes-list {{ list-style: none; }}
    .note-item {{ border-top: 1px solid #E2E8F0; }}
    .note-item:last-child {{ border-bottom: 1px solid #E2E8F0; }}
    .note-item a {{ display: block; padding: 22px 4px; transition: background 0.15s; }}
    .note-item a:hover {{ background: #F7FAFF; }}
    .note-date {{ display: block; font-size: 12px; font-weight: 600; color: #718096; letter-spacing: 0.3px; text-transform: uppercase; margin-bottom: 6px; }}
    .note-title {{ display: block; font-family: 'Space Grotesk', sans-serif; font-size: 20px; font-weight: 700; color: #1A1A2E; margin-bottom: 6px; line-height: 1.3; }}
    .note-excerpt {{ display: block; color: #4A5568; font-size: 15px; line-height: 1.55; }}
    footer {{ border-top: 1px solid #E2E8F0; padding: 28px 20px; text-align: center; font-size: 13px; color: #718096; background: #fff; }}
    .footer-editor {{ font-size: 13px; color: #4A5568; margin-bottom: 6px; }}
    .footer-editor strong {{ color: #1A1A2E; font-weight: 600; }}
    .footer-editor a {{ color: #2563EB; font-weight: 500; }}
  </style>
</head>
<body>
  <header>
    <div class="header-inner">
      <a href="/" class="logo">Catch<span>The</span>Brief</a>
      <a href="/" class="back-link">← All Briefs</a>
    </div>
  </header>
  <main>
    <span class="kicker">📝 Editor's Notes</span>
    <h1>Notes from the editor</h1>
    <p class="page-sub">Weekly-ish personal column from Rajneesh. Why some stories made the cut, what's being missed, and what's coming next.</p>
    <ul class="notes-list">
      {''.join(items)}
    </ul>
  </main>
  <footer>
    <p class="footer-editor">Edited by <strong>Rajneesh</strong> · <a href="mailto:catchthebrief@gmail.com">catchthebrief@gmail.com</a></p>
    © 2026 CatchTheBrief · Made with ☕ in India
  </footer>
</body>
</html>
"""
    return page


# ── Public API ───────────────────────────────────────────────────────────────

def build_all() -> list[dict]:
    """
    Build every note page + the index. Returns the list of notes
    (newest first) so callers can pick the latest for the homepage banner.
    Returns [] if no notes exist.
    """
    notes = _load_all()
    if not notes:
        # Clean up any old output dir? No — leave it alone in case someone wrote pages by hand.
        return []
    NOTES_OUT_DIR.mkdir(exist_ok=True)
    written = 0
    for note in notes:
        html_text = _render_note_page(note, notes)
        if not html_text:
            continue
        out = NOTES_OUT_DIR / f"{note['slug']}.html"
        out.write_text(html_text, encoding="utf-8")
        written += 1
    index_html = _render_index(notes)
    if index_html:
        (NOTES_OUT_DIR / "index.html").write_text(index_html, encoding="utf-8")
    print(f"  editor-notes: built {written} note pages + index")
    return notes


def latest_note() -> dict | None:
    notes = _load_all()
    return notes[0] if notes else None


def banner_html(note: dict | None) -> str:
    """HTML for the homepage editor-note banner. Empty string if no note."""
    if not note:
        return ""
    title_escaped = html.escape(note["title"])
    return (
        f'<a class="editor-note-banner" href="/editor-notes/{note["slug"]}.html">'
        f'<span class="enb-label">📝 Editor\'s Note</span>'
        f'<span class="enb-title">{title_escaped}</span>'
        f'<span class="enb-arrow">→</span>'
        f"</a>"
    )


def all_slugs() -> list[str]:
    """Return slugs for sitemap inclusion."""
    return [n["slug"] for n in _load_all()]


if __name__ == "__main__":
    notes = build_all()
    if notes:
        print(f"  latest: {notes[0]['date']} — {notes[0]['title']}")
    else:
        print("  no notes found in editor_notes/ — nothing built")
