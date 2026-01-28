# QWebChannel Bridge (Backend ↔ Web)

## Required Methods
### readTextFile(relativePath) -> string
- Reads UTF-8 text for preview rendering (Markdown/text).
- Must enforce: relative path only, stay under project root.
- Safety: cap max bytes (e.g., 2MB).

## Optional Methods
### requestGraph(view, focus) -> string (JSON)
- Returns graph payload for the requested view/focus.

### openPath(relativePath)
- Opens a rendered preview window (Markdown rendered if possible).
