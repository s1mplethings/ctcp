# CSV Cleaner Studio

A polished local web tool for uploading CSV data, previewing the first rows, applying lightweight cleanup operations, and exporting a cleaned CSV.

## What It Does

- Upload a `.csv` file from the browser
- Preview the raw table
- Remove empty rows
- Remove duplicate rows
- Keep only selected columns
- Preview the cleaned result
- Export the cleaned CSV

## Quick Start

1. Open a terminal in this project directory.
2. Start the local server:

```bash
python app.py
```

3. Visit `http://127.0.0.1:8008` in your browser.

## Replay / Export Entry

The cold-replay entrypoint used by CTCP packaging is:

```bash
python scripts/run_project_web.py --serve
python scripts/run_project_web.py --goal "replay smoke export" --project-name "CSV Cleaner Studio" --out generated_output
```

## Project Layout

- `app.py`: local HTTP server for the browser tool
- `src/csv_cleaner_web/service.py`: CSV parsing, cleaning, and export helpers
- `static/`: HTML/CSS/JS frontend
- `tests/`: unit tests for the cleaning logic
- `artifacts/`: screenshots and test/demo evidence

## Local Verify

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```
