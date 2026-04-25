# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## What This Project Is

A Windows desktop companion app for *My Singing Monsters* built with Python + PySide6 (Qt). Players track egg requirements for awakening Wublins, Celestials, and Amber Vessels.

## Commands

```bash
# First-time setup
pip install -r requirements.txt
python scripts/seed_content_db.py       # builds resources/db/content.db from pipeline/normalized/*.json
python scripts/generate_assets.py       # creates placeholder PNGs (skips existing files)
python scripts/generate_icon.py         # creates placeholder .ico
python scripts/import_fankit_images.py  # copies BBB Fan Kit images (skips existing)
python scripts/import_fankit_images.py --dry-run  # preview without copying

# Run the app
python main.py
python main.py --debug                  # enables DEBUG-level logging

# Tests
python -m pytest tests/                 # full suite (359 tests)
python -m pytest tests/unit/            # unit only
python -m pytest tests/integration/     # integration only (uses real in-memory SQLite)
python -m pytest tests/unit/test_commands.py -v  # single module, verbose

# Full release build
python scripts/build.py                 # tests → seed → assets → verify → PyInstaller → dist/
python scripts/verify_bundle.py         # must exit 0 before tagging a release
```

## Architecture

There is a **hard boundary** between `pipeline/` (maintainer-only tooling) and `app/` (the desktop runtime). The pipeline writes artifacts; the app only consumes them. `pipeline/` is never imported by `app/` at runtime.

### Desktop App Layer (`app/`)

```
bootstrap.py          ← startup: path detection, DB init, migrations, backfill, service wiring
domain/               ← pure Python: models, breed-list derivation, reconciliation (no Qt, no DB)
commands/             ← Command-pattern objects (add_target, close_out, increment_egg) → undo/redo via AppService stacks
repositories/         ← thin SQLite access functions (monster_repo, target_repo, settings_repo)
services/app_service.py ← AppService(QObject): holds undo/redo stacks, derives state, emits signals
ui/                   ← PySide6 views and panels; no business logic, subscribes to AppService signals
ui/viewmodels.py      ← dataclass ViewModels that AppService builds and emits; UI reads these only
updater/              ← fetch manifest → validate → download → checksum → stage → apply → rollback
db/                   ← connection factory + migration runner for both databases
```

**State flow**: Commands mutate the DB → AppService recomputes state → emits `state_changed(AppStateViewModel)` → UI panels re-render. UI panels must not call repos directly.

### Two-Database Design

| DB | Location | Access |
|----|----------|--------|
| `content.db` | `%APPDATA%\MSMAwakeningTracker\` (copied from `resources/db/` on first run) | Read-only at runtime |
| `userstate.db` | `%APPDATA%\MSMAwakeningTracker\` | Read-write |

`bootstrap.py` runs pending migrations on both DBs and backfills empty `content_key` / `monster_key` / `egg_key` columns on every launch. This keeps schema upgrades transparent.

### Stable Identity System

Every monster and egg has a `content_key` slug (e.g. `monster:wublin:zynth`, `egg:noggin`). These survive numeric ID reassignment across DB rebuilds. User progress rows reference these stable keys so that content updates never orphan saved state. When adding new monsters or eggs, a `content_key` **must** be assigned.

### Content Pipeline (`pipeline/`)

Data flow: `normalized/*.json` → `diff/engine.py` → `build/db_builder.py` → `validation/checks.py` → `publish/artifacts.py` (manifest + content.db).

The `pipeline/normalized/` directory is the single source of truth for all game content. `scripts/seed_content_db.py` builds `resources/db/content.db` from it.

### In-App Content Updates

Settings → "Check for Updates" downloads a new `content.db` via `app/updater/update_service.py`. The manifest URL (`DEFAULT_MANIFEST_URL`) points to `content/manifest.json` in this repo via GitHub raw URLs. Until content artifacts are published there, the button returns a 404 — handled gracefully. The update flow verifies SHA-256, validates the staged DB schema, atomically replaces the live DB, and auto-rolls back on any failure.

### Content Pipeline Scripts

| Script | Purpose |
|--------|---------|
| `scripts/import_content.py` | Fetch from MSM Wiki, normalize, detect changes, write review queue |
| `scripts/review_content.py` | Inspect/approve/reject review items before publishing |
| `scripts/publish_content.py` | Build content.db, validate, generate manifest + artifacts → `content/` |

## Key Patterns

- **No business logic in UI**: panels only call `AppService` methods or read `ViewModel` dataclasses.
- **Command pattern for mutations**: every user action that changes state is a `Command` subclass with `execute()` and `undo()`. `AppService` maintains `_undo_stack` and `_redo_stack`.
- **Repositories are functions, not classes**: `monster_repo.fetch_all(conn)` style — pass the connection explicitly.
- **DB connections are injected**: `AppService` receives `conn_content` and `conn_userstate`; it does not open connections itself.
- **`domain/` has zero dependencies on Qt or SQLite** — keep it that way for testability.

## Test Conventions

- Unit tests mock or use in-memory SQLite; they never touch `%APPDATA%`.
- Integration tests in `tests/integration/` use real in-memory SQLite via `conftest.py` fixtures.
- GUI smoke tests (`test_gui_smoke.py`) use `pytest-qt`; they verify widget construction doesn't crash, not visual correctness.
- Acceptance tests (`test_acceptance.py`) map directly to SRS acceptance criteria AC-R01 through AC-R06.
