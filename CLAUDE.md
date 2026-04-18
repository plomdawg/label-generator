# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A FastAPI web app for generating and printing 4×6" thermal label sheets. Labels are rendered as PIL images at 203 DPI and exported as PDFs. Live preview, URL sharing, and named templates are core features.

Deployed at `labels.plom.one` (homelab port 8777).

## Commands

```bash
# Run locally (from src/)
pip install fastapi uvicorn pillow pytz jinja2 python-multipart
python app.py        # serves on http://localhost:8777

# Docker (from services/label-generator/)
make up              # start
make restart         # restart (use this after code changes, not make up)
make logs            # last 100 lines
make logs-follow     # follow logs
make build           # rebuild image
make shell           # open shell in container
```

No tests or linter are configured (pytest + httpx are installed but unused).

## Architecture

**Backend (`app.py`)** — FastAPI with four endpoints:
- `GET /` — serves the main HTML, injecting URL params into Jinja2 template
- `GET /api/templates` / `GET /api/templates/{id}` — reads `templates.json`
- `POST /preview` — returns base64-encoded PNG images (one per sheet)
- `POST /generate` — returns a multi-page PDF blob

**Frontend (`templates/index.html`)** — Alpine.js + Tailwind (both from CDN, no build step). Three Alpine components:
- `variablesManager()` — template variable state, persisted to localStorage
- `templateSelector()` — loads templates from `/api/templates`, handles switching
- `labelForm()` — main form state, triggers preview/generate, builds share URLs

**Image pipeline:** `parse_input()` substitutes `{{ var }}` placeholders → `create_label_sheets()` renders PIL images at 812×1218px → preview returns base64 PNGs, generate saves to PDF.

## Template System

Templates live entirely in **`templates.json`**. Structure:

```json
{
  "template_id": {
    "name": "Display Name",
    "description": "Short description",
    "variables": { "var_name": "default_value" },
    "items": [
      { "text": "Label text with {{ var_name }} and \\n newlines", "quantity": 10 }
    ],
    "defaults": {
      "font_size": 24,
      "bold": true,
      "rows": 10,
      "columns": 3,
      "font_family": "DejaVuSans"
    }
  }
}
```

Valid values:
- `font_family`: `DejaVuSans`, `DejaVuSerif`, `DejaVuSansMono`, `ComicSansMS`
- `font_size`: 8–72
- `rows`: 1–20, `columns`: 1–10
- `{{ date }}` is always available (auto-injected, Pacific time, formatted `M/D/YYYY`)

**To add a template:** add a new key to `templates.json` and restart the container (`make restart` from `services/label-generator/`). No code changes needed.

## URL Parameter System

All settings are URL-addressable:
```
/?template=cables&font_size=64&bold=true&rows=5&columns=1&font_family=DejaVuSans&data=<base64>
```
`data` is a base64-encoded JSON array of label items. URL params override template defaults, enabling shareable pre-configured links.

## Non-Obvious Details

- **`make restart` not `make up`** — the container uses bind mounts; `make up` skips already-running containers and won't pick up changes.
- **Bold is a string on the wire** — HTML form sends `"true"`/`"false"` strings; server converts with `.lower() == "true"`.
- **Preview images are Blob URLs** — server returns base64, frontend converts to `URL.createObjectURL()` and revokes old ones to avoid memory leaks.
- **Template load priority** — URL params preserve existing form data (`skipDataLoad=true`); clicking a template button overwrites form data entirely.
- **Fonts from system** — DejaVu fonts installed via `fonts-dejavu-core` in the Dockerfile. Comic Sans is `ComicSansMS.ttf`; others follow `DejaVuSans-Bold.ttf` pattern.
- **No input sanitization needed** — text goes straight to PIL (no HTML rendering), so XSS is not a concern.
