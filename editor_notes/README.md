# Editor's Notes

Weekly (or whenever) personal column from the editor. One note per file.

## How to write a note

1. Create `editor_notes/YYYY-MM-DD.md` (the date is the publish date — usually Sunday).
2. Front matter on top:

   ```
   ---
   title: A short, declarative title
   ---
   ```

3. Body below in plain Markdown. Keep it 150-300 words. Use:
   - Blank lines between paragraphs
   - `## Subheading` for any internal structure
   - `**bold**`, `*italic*`, `[link](https://...)`

4. Commit the file. The next daily build (or a manual `python generate_editor_note.py` run) will:
   - Render it to `/editor-notes/YYYY-MM-DD.html`
   - Update `/editor-notes/index.html` with the new entry at the top
   - Show the latest note's title as a banner on the homepage (until a newer note replaces it)

## Falls back gracefully

If this directory has zero `.md` files, the homepage shows no editor banner and no `/editor-notes/` URLs are generated. Nothing breaks.
