# Changelog

All notable changes to the MSM Awakening Tracker are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

For changes prior to the introduction of this changelog, see the git log.

---

## [Unreleased]

### Added

- `LICENSE` (MIT) and a "Legal & Attribution" section in `README.md` clarifying
  that the project is unofficial fan content and that BBB Fan Kit imagery is
  not covered by the source license.
- README "BBB Fan Kit Images (optional)" section explaining where to obtain
  the Fan Kit and how `import_fankit_images.py` consumes it.
- `app/bootstrap.open_content_db_readonly()` for runtime use, opening
  `content.db` via `?mode=ro` URI so any stray write raises immediately.
- `tests/unit/test_acceptance.py`: `TestAC_R03_*` and `TestAC_R06_*` classes
  that pin SRS acceptance criteria R03 (no clip when not needed) and R06
  (silent orphan removal on close-out).
- `pyproject.toml` with pytest and ruff configuration.
- `.editorconfig` with project-wide whitespace conventions.
- `docs/improvement-plan-2026-05-04.md`: prioritized plan from a multi-agent
  software audit.

### Changed

- Migrations now run inside an explicit `BEGIN; ... COMMIT;` so a partial
  failure rolls back atomically. A buggy migration no longer bricks startup
  with `duplicate column` on the next launch.
- `content.db` is opened read-only after migrations and backfill complete,
  enforcing the documented runtime invariant. The updater opens its own
  writable handle when swapping the file.
- `settings_repo.set_value()` no longer commits internally; callers
  (`AppService.set_ui_pref`, `AppService.handle_sort_change`) wrap the call
  in `with transaction(...)` so multi-write transactions can compose.
- Manifest `content_db_url` is now validated against an HTTPS-only,
  GitHub-raw-only allowlist (override via kwargs for local test fixtures).
- `RELEASE_CHECKLIST.md` content gates updated to reflect actual content:
  64 monsters (20 Wublins, 12 Celestials, 32 Amber Vessels) and 76 egg types.
- `README.md` and `RELEASE_CHECKLIST.md` no longer claim "no installer
  exists"; `installer/msm_tracker.iss` is the per-user Windows installer.

### Security

- Reject `content_db_url` whose scheme is not `https` or whose host is not
  on the allowlist (`raw.githubusercontent.com`). Prevents a poisoned
  manifest from triggering plain-HTTP downgrade, `file://` reads, or
  attacker-host downloads even though SHA-256 still gates the content.

### Fixed

- `import_fankit_images.py` now exits non-zero with a clear error and a
  pointer to the README when `Monsters/` is missing.
- Stale documentation: dropped the `(359 tests)` parenthetical from
  `CLAUDE.md`, `AGENTS.md`, and `README.md` (count drifts as tests are
  added).
