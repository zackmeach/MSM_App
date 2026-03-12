---
name: MSM Tracker Bootstrap
overview: Build a brand-new PySide6 Windows desktop app from an empty repo with a runnable shell, dual-SQLite bootstrap, an explicit satisfaction-aware user-state schema, test-first domain logic, and an MVP core loop before any updater work.
todos:
  - id: skeleton-bootstrap
    content: Create the runnable PySide6 skeleton, bootstrap module, runtime paths, logging, and app wiring.
    status: completed
  - id: db-migrations-seed
    content: Add dual-database migrations, the explicit satisfaction-aware user-state schema, and a minimal representative dev seed dataset for content.db plus userstate defaults.
    status: completed
  - id: catalog-home-shell
    content: Build the main window, home view, catalog shell, settings shell, and the first view models.
    status: completed
  - id: core-domain-state
    content: Implement the satisfaction-aware domain state, add-target flow, and aggregated Breed List derivation with tests.
    status: completed
  - id: core-actions-persistence
    content: Implement increment, completion, close-out, reconciliation, undo/redo, and restart persistence milestone by milestone with tests.
    status: completed
  - id: release-content-bundle
    content: Replace the dev seed dataset with a release-complete bundled content.db and assets before packaging or calling the app content-complete.
    status: completed
isProject: false
---

# MSM Awakening Tracker Implementation Plan

## Confirmed Architecture

- Use Python + PySide6 with a thin widget layer and a central presenter/service in [app/services/app_service.py](app/services/app_service.py).
- Use two SQLite files exactly as required: bundled/read-only content in [resources/db/content.db](resources/db/content.db) and local user state in `%APPDATA%\\MSMAwakeningTracker\\userstate.db`, initialized from [app/bootstrap.py](app/bootstrap.py).
- Keep business rules out of widgets. Core logic lives in [app/domain/](app/domain/) and repository code lives in [app/repositories/](app/repositories/).
- Keep reconciliation centralized in [app/domain/reconciliation.py](app/domain/reconciliation.py) and make all add/close-out flows call it atomically.
- Use [resources/db/content.db](resources/db/content.db) `update_metadata` as the **single source of truth** for content version and last-updated metadata. `userstate.db/app_settings` will not duplicate those values.
- Start with `sqlite3`, plain SQL migrations, and pytest/pytest-qt.

## Chosen Repo Structure

- [main.py](main.py): app entrypoint.
- [app/bootstrap.py](app/bootstrap.py): runtime paths, DB copy/init, migrations, logging, service wiring.
- [app/ui/](app/ui/): [main_window.py](app/ui/main_window.py), [home_view.py](app/ui/home_view.py), [catalog_panel.py](app/ui/catalog_panel.py), [settings_panel.py](app/ui/settings_panel.py), reusable row/card widgets, and [viewmodels.py](app/ui/viewmodels.py).
- [app/domain/](app/domain/): enums, dataclasses, breed-list derivation, reconciliation, completion policy.
- [app/commands/](app/commands/): add-target, close-out-target, increment-egg, base command.
- [app/repositories/](app/repositories/): content reads, active target writes, progress/state queries, settings.
- [app/db/migrations/content/](app/db/migrations/content/) and [app/db/migrations/userstate/](app/db/migrations/userstate/): schema bootstrap and future migrations.
- [resources/](resources/): bundled `content.db`, placeholder assets, UI assets, ding audio.
- [tests/unit/](tests/unit/) and [tests/integration/](tests/integration/): reconciliation first, then commands, repos, startup, persistence.
- [requirements.txt](requirements.txt) and [README.md](README.md): dependencies and local run instructions.

## Critical Design Decisions

- I will **not** follow the TDD's delete-only `breed_progress` completion model as written. It conflicts with the SRS derivation rule and your requirement that reintroduced egg types start fresh at `bred=0`.
- I will implement the user-approved **satisfaction-aware** model instead: user state will track outstanding requirement progress per active target requirement so completed demand stays hidden, newly added demand starts fresh, and close-out only removes the clicked target's contribution.
- I will reject the TDD's `QTimer.singleShot(0, ...)` catalog-filter suggestion because your implementation constraints explicitly say **no timers**. Catalog filtering will run synchronously on text change.
- The docs do not define how a global egg click should allocate progress across multiple active targets that need the same egg. I will make this explicit: allocate one click to the **oldest still-unsatisfied target requirement first**, ordered by `active_targets.added_at ASC`, with `active_targets.id ASC` as the deterministic tie-breaker.
- The TDD's duplicate consolidated close-out rule is still useful: when a grouped duplicate monster entry is clicked, close out the most recently added matching active target instance.

## Explicit State and Data Rules

- **Satisfaction-aware user-state schema for MVP:** `userstate.db` will store `active_targets(id, monster_id, added_at)`, `target_requirement_progress(active_target_id, egg_type_id, required_count, satisfied_count, PRIMARY KEY(active_target_id, egg_type_id))`, and `app_settings(key, value)`.
- **What is derived vs persisted:** the visible Breed List is derived by grouping `target_requirement_progress` rows by `egg_type_id` and summing `required_count` and `satisfied_count` across active targets. I will not use a single global `breed_progress` aggregate table for the MVP because it cannot preserve the approved satisfaction-aware behavior cleanly.
- **Add target behavior:** inserting an `active_targets` row will also materialize one `target_requirement_progress` row per content requirement for that target with `satisfied_count = 0`.
- **Increment behavior:** clicking an egg will update exactly one eligible `target_requirement_progress` row for that `egg_type_id`, chosen by the allocation rule above, and increment `satisfied_count` by 1 without touching unrelated targets.
- **Completion behavior:** a Breed List row disappears when the aggregate remaining count for that egg type reaches 0 across all active targets. If a later target reintroduces that egg type, its newly materialized `target_requirement_progress` rows start at `satisfied_count = 0`, so the visible row restarts fresh exactly as approved.
- **Close-out behavior:** closing out a target deletes its `active_targets` row and its associated `target_requirement_progress` rows only. Remaining targets keep their own satisfied progress unchanged, which prevents old completed work from being resurrected incorrectly.
- **Version metadata authority:** `content.db/update_metadata` stores `content_version`, `last_updated_utc`, and `source`. `userstate.db/app_settings` stores only user preferences and app-local bookkeeping such as `breed_list_sort_order` and `last_reconciled_content_version`.
- **Dev seed vs release content:** Milestone 0/1 will intentionally use a small representative dev seed dataset so the app becomes runnable early. Before any release or “content complete” claim, [resources/db/content.db](resources/db/content.db) must be replaced with a release-complete bundled dataset covering all in-scope regular Wublins, regular Celestials, and Amber Vessels required by the SRS.

## Milestone Order

### Milestone 0: Project Skeleton and Bootstrap

- Create the empty-repo package layout, entrypoint, PySide6 shell, home/catalog/settings placeholders, and base styling.
- Add runtime bootstrap for dev paths and `%APPDATA%` storage.
- Create migration runner and initial schemas for content/userstate, including `target_requirement_progress` and `update_metadata`.
- Seed a **small representative dev dataset** first so the app is runnable early, while explicitly keeping release-complete bundled content as a later packaging/content milestone.
- Add test harness, fixtures, and the first repository/startup tests.
- Why first: this locks paths, schema, and app wiring before domain/UI logic piles up.

### Milestone 1: Content Load and Catalog

- Implement content repositories and catalog view models.
- Load the dev seed monsters/requirements from `content.db`, while keeping the repository and asset layout identical to the eventual release-complete bundle.
- Render catalog tabs, search, and click-to-add plumbing.
- Add tests for content reads and case-insensitive substring filtering.

### Milestone 2: Add Target and Aggregated Breed List

- Implement active target creation plus materialized `target_requirement_progress` rows for the satisfaction-aware state model.
- Implement pure aggregate derivation for the visible Breed List from outstanding per-target requirement rows.
- Render Home view with Breed List on the left and In-Work panel on the right.
- Add tests for aggregation, grouping, no-orphan invariants, and fresh-row creation.

### Milestone 3: Increment and Completion Handling

- Implement egg click flow, deterministic oldest-unsatisfied allocation, row completion, ding playback, and immediate removal.
- Keep the UI thin: command executes, state refreshes, completion event drives ding/fade only.
- Add tests for increment behavior, completion deletion, reintroduced egg reset, and no over-increment.

### Milestone 4: Close-Out and Reconciliation

- Implement close-out of one target instance, grouped duplicate handling, and centralized reconciliation.
- Ensure silent removal on reconciliation and clip/orphan behavior where applicable to the satisfaction-aware state model.
- Add the highest-risk reconciliation tests first, including acceptance-style scenarios.

### Milestone 5: Undo/Redo

- Add command stack management for add, close-out, and increment only.
- Ensure undo restores exact prior state snapshots and redo invalidation follows standard rules.
- Add keyboard shortcuts on the main window.
- Add focused tests for atomic undo/redo and restart stack reset.

### Milestone 6: Persistence and Settings Shell

- Persist every user action immediately.
- Restore state and sort preference on restart.
- Add the basic Settings page with version metadata read from `content.db/update_metadata` and BBB disclaimer text.
- Add restart persistence tests and settings persistence tests.

### Milestone 7: Updater Deferred Until Core Loop Is Stable

- Leave scraper/updater implementation for after the core loop works end-to-end.
- Before coding updater behavior, validate real wiki payloads and BBB asset URL shapes because the TDD still leaves those unresolved.

## First Implementation Pass After Approval

- Create [main.py](main.py), [app/bootstrap.py](app/bootstrap.py), [app/ui/main_window.py](app/ui/main_window.py), [app/services/app_service.py](app/services/app_service.py), and the initial migration files.
- Create the minimum domain/repository modules needed to launch the app, load a dev-seeded `content.db`, and materialize `target_requirement_progress`.
- Add [tests/conftest.py](tests/conftest.py), [tests/integration/test_migrations.py](tests/integration/test_migrations.py), and [tests/unit/test_breed_list.py](tests/unit/test_breed_list.py) so the skeleton is validated from the start.

## Known Ambiguities and How I Will Handle Them

- SRS/TDD conflict on completion persistence: resolved with the user-approved satisfaction-aware model.
- TDD timer suggestion conflicts with your no-timers constraint: rejected.
- Updater asset URLs and wiki parser details are still doc-level unknowns, but they do not block the MVP vertical slice and will stay deferred.
- Initial content completeness is intentionally staged: Milestone 0/1 uses representative dev seed content, and release completeness is a separate required packaging/content step before shipping.

