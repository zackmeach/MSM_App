# MSM Awakening Tracker

A lightweight Windows desktop companion app for *My Singing Monsters* that helps
players track egg requirements for Amber Vessels, sleeping Wublins, and sleeping
Celestials.

## Quick Start (Development)

```bash
# Create a virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Seed the dev content database (first time only)
python scripts/seed_content_db.py

# Run the app
python main.py

# Run tests
pytest
```

## Project Layout

| Path | Purpose |
|---|---|
| `main.py` | Application entry point |
| `app/bootstrap.py` | Runtime path detection, DB init, logging, service wiring |
| `app/ui/` | PySide6 widget layer (thin — no business logic) |
| `app/domain/` | Pure domain logic: models, breed-list derivation, reconciliation |
| `app/commands/` | Command-pattern objects for undo/redo |
| `app/services/` | Application service / presenter layer |
| `app/repositories/` | SQLite data access |
| `app/db/` | Connection factory, migration runner, SQL migration scripts |
| `app/assets/` | Runtime asset path resolver |
| `resources/` | Bundled static assets (DB, images, audio) |
| `scripts/` | Build-time utilities (seed DB, fetch assets) |
| `tests/` | pytest unit and integration tests |

## Databases

| File | Location (runtime) | Ownership |
|---|---|---|
| `content.db` | `%APPDATA%\MSMAwakeningTracker\` | Read-only at runtime; written by seed/update only |
| `userstate.db` | `%APPDATA%\MSMAwakeningTracker\` | Read-write; user progress and preferences |

## Tech Stack

- Python 3.11+
- PySide6 (Qt for Python)
- SQLite via `sqlite3`
- pytest / pytest-qt
