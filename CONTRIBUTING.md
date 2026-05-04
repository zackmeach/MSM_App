# Contributing

Thanks for considering a contribution. This is a small hobby fan project, so
the bar is "tests green and the architecture stays clean," not heavyweight
process. The notes below cover the conventions that have emerged.

## Setup

See [README.md](README.md) → "Quick Start (Development)" for the canonical
one-time setup. In short: `python -m venv .venv`, install
`requirements.txt`, run `scripts/seed_content_db.py`, then `python main.py`.

## Branching and PRs

- Work on a topic branch off `main`. Naming convention seen in history:
  `kind/short-description` (for example, `polish/icon-size-and-home-spacing`).
- Open a pull request against `main`. Squash-merge is the default.
- Push only after `python -m pytest tests/` exits clean.

## Commit messages

The git log uses a short `<scope>: <imperative>` format. Examples from the
existing history:

- `ui: prevent sectionBadge clipping at right edge`
- `db: make migrations atomic — wrap each .sql in BEGIN/COMMIT with rollback on failure`
- `updater: enforce HTTPS + allowlisted host for content_db_url in manifest`
- `docs: add MIT LICENSE and Legal & Attribution section to README`

Keep the title under ~70 characters. Use the body for the *why* when it's
not obvious from the diff.

## Tests

- `python -m pytest tests/` runs everything. The suite is fast (~12s) so
  there's no excuse to skip it before pushing.
- Place unit tests under `tests/unit/`, integration tests under
  `tests/integration/`. Conventions live in [CLAUDE.md](CLAUDE.md) under
  "Test Conventions."
- Acceptance tests (`tests/unit/test_acceptance.py`) map to SRS criteria
  AC-R01 through AC-R06; if you change reconcile or close-out behavior,
  re-read the SRS and update those tests.

## Architecture rules

These are hard constraints, enforced by code review:

- `app/domain/` has zero Qt or SQLite imports. It's pure Python.
- `app/ui/` never imports `app.repositories` or `sqlite3`. UI reads
  ViewModels and calls `AppService` methods.
- `app/` never imports from `pipeline/`. The pipeline is maintainer
  tooling; the desktop app only consumes its published artifacts.
- Every state mutation goes through a `Command` subclass with `execute()`
  and `undo()`. `AppService` owns the undo/redo stacks.
- Repositories are functions, not classes; the connection is injected.
- Repositories never call `conn.commit()`. The caller (Command or service
  using `with transaction(...)`) owns the transaction.

Read [CLAUDE.md](CLAUDE.md) before touching the architecture for the full
rationale.

## Content pipeline safety

`pipeline/` and `scripts/{import,review,publish}_content.py` are
maintainer-only tooling. Running `publish_content.py` mutates `content/`
which is the live update channel for installed apps. Do **not** run it
casually — coordinate with the maintainer first.

The same goes for `scripts/import_content.py` (which fetches from the
fan wiki) — re-running on a different day will produce review-queue items
that need human resolution before publishing. See
[`pipeline/SOURCE_POLICY.md`](pipeline/SOURCE_POLICY.md).

## Style and tooling

- 4-space Python, UTF-8, LF line endings (see `.editorconfig`).
- `pyproject.toml` carries pytest + ruff config. If you adopt `ruff` for
  formatting/linting locally, keep its settings in sync via that file.
- Type hints on public APIs; we use `from __future__ import annotations`
  throughout.

## Release gates

[RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md) is the gate before tagging.
Don't add a release tag until every section is signed off.

## Reporting issues

Open a GitHub issue. Include the platform (Windows version), Python
version (only relevant for source runs), and reproduction steps.

## Legal

This project uses BBB Fan Kit imagery and *My Singing Monsters* trademarks
under Big Blue Bubble's Fan Content Policy. See
[README.md](README.md#legal--attribution). By contributing you agree your
contributions are licensed under the project's MIT [LICENSE](LICENSE).
