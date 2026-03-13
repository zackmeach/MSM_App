---
name: msm do now plan
overview: "Concrete implementation plan for the current Do Now scope: restore bundle integrity, make content updates finalize safely in-process, narrow updater v1 to a reliable DB-focused scope, and define a release gate that matches the authoritative SRS/TDD stack."
todos:
  - id: lock-updater-v1-scope
    content: Decide and document v1 updater as DB-only content replacement handled by the desktop client, with discovery/media sourcing moved to the maintainer content pipeline.
    status: completed
  - id: restore-bundle-integrity
    content: Populate the real referenced egg/monster bundle assets and harden verify_bundle so missing DB-referenced assets fail the build.
    status: completed
  - id: refactor-update-finalization
    content: Split updater staging from finalization, then implement close/replace/reopen/rebind/reconcile flow with rollback protection.
    status: completed
  - id: add-do-now-tests
    content: Add automated coverage for bundle-integrity failures, updater live rebind, and rollback/finalization scenarios.
    status: completed
  - id: publish-release-gate
    content: Create a release checklist that blocks readiness on bundle integrity, updater correctness, packaging evidence, and clean-machine validation.
    status: completed
isProject: false
---

# Do Now Implementation Plan

## 1. Executive summary

The recommended path is to keep v1 as a **manual, DB-focused content updater** while making the shipped install bundle genuinely complete and enforceable. Concretely: ship the real bundled egg/monster images in `resources/`, harden bundle verification so DB-referenced asset paths must exist, refactor update finalization so a successful content update is immediately active in the running app, and add a release gate checklist that blocks release on bundle, updater, packaging, and clean-machine validation. The highest-risk blocker is **bundled asset integrity**, because the current checkout has no `resources/` files at all while the app, build pipeline, README, and SRS all assume a complete offline bundle.

## 2. Recommended decisions

### A. Bundled asset situation

- Recommended decision: **Ship the real egg/monster image files in `resources/images/eggs/` and `resources/images/monsters/`, then make `scripts/verify_bundle.py` fail on any DB-referenced missing path.**
- Why this is best now: The authoritative SRS already requires a complete bundled DB and bundled assets at install time in `[MSM_Awakening_Tracker_SRS_v1.1.md](MSM_Awakening_Tracker_SRS_v1.1.md)`. The runtime code also assumes bundle-first offline operation in `[app/bootstrap.py](app/bootstrap.py)`, `[app/assets/resolver.py](app/assets/resolver.py)`, `[msm_tracker.spec](msm_tracker.spec)`, and `[scripts/build.py](scripts/build.py)`. Shipping the real files is the smallest way to make the release truthful without expanding runtime updater scope.
- Alternative considered: **Narrow the release claim to placeholder-only / incomplete media coverage.** Not preferred because it forces authoritative doc changes across SRS/TDD/Vision/README and weakens the offline-first product promise right before release. Use this only if the BBB-compliant source asset set cannot be assembled immediately.

### B. Updater finalization

- Recommended decision: **Refactor the update flow so the worker only downloads and validates the staged DB; the main-thread finalization path then closes the live content connection, atomically replaces `content.db`, reopens it, rebinds dependent services, runs reconciliation/finalization, clears undo/redo, and refreshes UI state.**
- Why this is best now: It directly addresses the current correctness gap in `[app/updater/update_service.py](app/updater/update_service.py)`, `[app/services/app_service.py](app/services/app_service.py)`, and `[app/ui/main_window.py](app/ui/main_window.py)` without introducing broader updater scope. It also avoids Windows file-replacement issues caused by replacing an in-use SQLite DB and its WAL sidecars.
- Alternative considered: **Keep current file-replace behavior and require restart to pick up new content.** Not preferred because the current code already reports success immediately, but the running app can stay bound to stale content and caches, which is misleading and unsafe.

### C. Updater v1 scope

- Recommended decision: **Define the shipped desktop updater as DB-only replacement of a prebuilt `content.db` artifact.** New monster discovery and any image/media sourcing happen in the content-production pipeline, not inside the shipped app.
- Why this is best now: It preserves the user-facing capability that new content can appear after updates, while avoiding a large scope jump into in-app scraping, asset downloading, cache population, provenance enforcement, and rollback for mixed DB/media payloads. This is the smallest path that matches correctness and release reliability.
- Alternative considered: **Implement DB + image/media/content discovery in the app now.** Not preferred because the codebase currently has only resolver scaffolding for cached assets, not a safe end-to-end asset fetch/apply system. That would materially expand both architecture and test surface.

### D. Release gate checklist

- Recommended decision: **Add a concrete release gate document and treat it as a hard blocker for any build called “ready”.** The gate must require bundle integrity, updater finalization behavior, automated test pass, PyInstaller packaging pass, and clean-machine validation evidence.
- Why this is best now: The repo already has partial executable gates in `[scripts/build.py](scripts/build.py)` and `[scripts/verify_bundle.py](scripts/verify_bundle.py)`, but no single release decision artifact. A written gate makes the remaining readiness gaps explicit, especially installer-grade packaging versus current dev-build packaging.
- Alternative considered: **Rely on build script success alone.** Not preferred because the current build script does not enforce asset-path integrity, updater finalization, installer readiness, or clean-machine validation.

## 3. Implementation plan by workstream

## Asset bundle integrity

- Objective: Make the shipped bundle truthful and enforceable so every asset path referenced by `content.db` exists in the packaged resources tree, and the build fails if that is not true.
- Exact files/modules likely impacted:
  - `[resources/](resources/)`
  - `[scripts/seed_content_db.py](scripts/seed_content_db.py)`
  - `[scripts/verify_bundle.py](scripts/verify_bundle.py)`
  - `[scripts/build.py](scripts/build.py)`
  - `[msm_tracker.spec](msm_tracker.spec)`
  - `[README.md](README.md)`
  - Test coverage: likely new `tests/unit/test_verify_bundle.py` or `tests/integration/test_verify_bundle.py`
- Step-by-step implementation sequence:
  1. Inventory the asset paths referenced by `egg_types.egg_image_path` and `monsters.image_path` from the seeded DB in `[scripts/seed_content_db.py](scripts/seed_content_db.py)`.
  2. Assemble the required BBB-compliant image files under `resources/images/eggs/` and `resources/images/monsters/` using the exact relative filenames referenced in the DB.
  3. If any referenced file cannot be provided immediately, stop and choose the fallback path: narrow the release/document claims before implementation continues.
  4. Tighten `scripts/verify_bundle.py` so it checks:
    - existence of `resources/db/content.db`
    - existence of `resources/images/ui/placeholder.png`
    - existence of `resources/images/ui/app_icon.ico`
    - existence of `resources/audio/ding.wav`
    - every distinct DB-referenced asset path resolves under `resources/` and exists on disk
    - count assertions match seeded expectations, not loose minimums
  5. Make `verify_bundle.py` print a concise missing-assets report and return non-zero if anything is missing.
  6. Add automated tests that create temporary resource trees/DB fixtures and prove the verifier fails on missing DB-referenced assets and passes on complete bundles.
  7. Keep `scripts/build.py` using `verify_bundle.py` as a hard gate before PyInstaller packaging.
  8. Verify `[msm_tracker.spec](msm_tracker.spec)` still includes the whole `resources/` tree and references a real icon path.
- Dependencies:
  - Availability of the actual release-approved image set.
  - Decision C, because if v1 updater is DB-only, shipping a complete bundle is mandatory rather than optional.
- Risks/pitfalls:
  - Current checkout has zero `resources/` files, so build/package may fail immediately once verification is tightened.
  - DB-relative asset paths must match exact file names/casing used in the bundle.
  - `generate_assets.py` does not generate the real egg/monster art, only placeholder/audio/icon, so verification must not assume generated assets cover catalog media.
- Definition of done:
  - `resources/` contains the real referenced egg/monster image files or the release claim has been formally narrowed.
  - `scripts/verify_bundle.py` fails on any missing DB-referenced asset.
  - Automated tests cover both pass and fail bundle-integrity cases.
  - `scripts/build.py` blocks packaging when bundle integrity is broken.
- Must do now:
  - Bundle the referenced files or formally narrow the release claim.
  - Harden verifier and tests.
- Can defer until after Do Now:
  - Asset compression, deduplication, or build-size optimization.

## Updater finalization

- Objective: Ensure a successful content update is immediately active in the running app, with safe rollback semantics and post-update reconciliation against the new content.
- Exact files/modules likely impacted:
  - `[app/updater/update_service.py](app/updater/update_service.py)`
  - `[app/bootstrap.py](app/bootstrap.py)`
  - `[app/services/app_service.py](app/services/app_service.py)`
  - `[app/ui/main_window.py](app/ui/main_window.py)`
  - `[app/domain/reconciliation.py](app/domain/reconciliation.py)`
  - `[app/repositories/monster_repo.py](app/repositories/monster_repo.py)`
  - `[app/repositories/settings_repo.py](app/repositories/settings_repo.py)`
  - `[app/commands/add_target.py](app/commands/add_target.py)`
  - Tests: `[tests/unit/test_updater.py](tests/unit/test_updater.py)`, likely new integration tests around live rebind/finalization
- Step-by-step implementation sequence:
  1. Split the updater into two phases in `[app/updater/update_service.py](app/updater/update_service.py)`:
    - worker thread: fetch manifest, download staged DB, validate staged DB
    - finalization phase: close/reopen/rebind/reconcile on the main thread (or a clearly serialized finalization path)
  2. Move content-DB opening logic behind a reusable helper in `[app/bootstrap.py](app/bootstrap.py)` so the same connection setup is used on initial launch and post-update reopen.
  3. Add a small rebinding API to `[app/services/app_service.py](app/services/app_service.py)` that swaps in a new content connection and refreshes `_requirements_cache`, `_egg_types_map`, settings metadata reads, catalog reads, and any other content-backed state.
  4. Remove stale-connection assumptions in the updater itself by either rebinding `UpdateService` to the new connection or making current-version reads go through a refreshed provider instead of a constructor-captured connection.
  5. In the finalization sequence:
    - block update UI actions
    - checkpoint/close the old content connection
    - handle/remove stale `content.db-wal` and `content.db-shm` sidecars as needed
    - back up current `content.db`
    - atomically replace with staged DB using `os.replace` semantics rather than `shutil.move`
    - reopen the new content connection
    - rebind `AppService`, `UpdateService`, and the stored app context connection reference
  6. Implement the post-update reconciliation/finalization pass using the new content:
    - remove or close out any active targets that now point at deprecated monsters
    - clip/purge progress rows per the reconciliation rules
    - update a `last_reconciled_content_version` app setting to support idempotence and crash recovery
    - clear undo/redo only after the finalization transaction succeeds
  7. Refresh the catalog, breed list, in-work panel, and settings metadata from the rebound service so the new content version is visible immediately.
  8. Change success messaging in the Settings flow so it no longer implies a restart is required when live finalization succeeds.
  9. Add rollback logic: if replacement/reopen/reconciliation fails after backup creation, restore the prior DB, reopen the previous connection, and surface a failure state instead of reporting success.
- Dependencies:
  - Stable connection-open helper in `[app/bootstrap.py](app/bootstrap.py)`.
  - Clear definition of reconciliation/finalization behavior for deprecated or changed content rows.
- Risks/pitfalls:
  - Replacing a SQLite file on Windows while a connection or WAL sidecar is active is error-prone.
  - `AppService` caches content-derived data at construction time today; forgetting to refresh any cache will leave mixed old/new state.
  - Undo/redo commands created before update may reference no-longer-valid content assumptions, so stack clearing must happen after successful finalization, not before.
  - The current `[app/domain/reconciliation.py](app/domain/reconciliation.py)` implementation is narrower than the TDD’s broader finalization expectations, so finalization logic may need to live partly in service/repository code rather than only the pure domain helper.
- Definition of done:
  - After a successful update, the running app reads the new `content_version` immediately with no restart.
  - Catalog and settings reflect new content in the same session.
  - Post-update reconciliation runs against the new content and leaves userstate valid.
  - Undo/redo is cleared only after successful finalization.
  - Failed finalization restores the prior DB and app remains usable.
  - Automated tests cover success, validation failure, replacement failure, rollback, and live rebind behavior.
- Must do now:
  - Separate staging from finalization.
  - Reopen/rebind the content DB and run post-update reconciliation.
  - Add rollback coverage.
- Can defer until after Do Now:
  - Background resume/retry UX for interrupted updates beyond a single recovery marker.

## Updater v1 scope decision

- Objective: Remove ambiguity about what the shipped desktop updater does in v1 so code, docs, and QA all test the same behavior.
- Exact files/modules likely impacted:
  - `[MSM_Awakening_Tracker_SRS_v1.1.md](MSM_Awakening_Tracker_SRS_v1.1.md)`
  - `[MSM_Awakening_Tracker_TDD_v1_3.md](MSM_Awakening_Tracker_TDD_v1_3.md)`
  - `[MSM_Awakening_Tracker_Vision.md](MSM_Awakening_Tracker_Vision.md)`
  - `[README.md](README.md)`
  - `[app/ui/settings_panel.py](app/ui/settings_panel.py)`
  - Possibly `[app/ui/viewmodels.py](app/ui/viewmodels.py)` if update copy is centralized there
- Step-by-step implementation sequence:
  1. Record the product decision explicitly: the **desktop app updater installs a prebuilt `content.db` package only**.
  2. Rewrite the SRS update requirements so they describe manual download/apply of validated content data, not in-app wiki scraping or asset downloading.
  3. Preserve the product outcome that new monsters can appear after updates, but describe that discovery/content assembly as part of the maintainer’s content pipeline, not the installed client.
  4. Align the TDD sections that currently describe `downloaded asset cache`, `asset_fetcher.py`, BBB Fan Kit runtime fetching, and mixed DB/media commit behavior so they match the reduced v1 scope.
  5. Update README and Settings UI copy to say “content updates” rather than implying image/media refresh if that behavior is not shipped.
  6. Add one explicit statement in docs and release checklist that **installer-bundled assets are the v1 media source of truth**.
- Dependencies:
  - Decision A, because DB-only updater increases the importance of the shipped bundle.
- Risks/pitfalls:
  - If docs are not aligned, the release remains misleading even if code is correct.
  - The current TDD contains future-facing updater architecture that an implementation agent could otherwise mistake for required v1 scope.
- Definition of done:
  - SRS, TDD, Vision, README, and basic Settings copy all describe the same v1 updater behavior.
  - The release gate checklist tests only the chosen scope.
- Must do now:
  - Make the scope decision explicit and update docs/UI language accordingly.
- Can defer until after Do Now:
  - Designing a future DB+media updater v2.

## Release gate checklist

- Objective: Define a hard, auditable minimum bar for calling the app “ready”.
- Exact files/modules likely impacted:
  - New `[RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md)` or similar root-level checklist doc
  - `[README.md](README.md)`
  - `[scripts/build.py](scripts/build.py)`
  - `[scripts/verify_bundle.py](scripts/verify_bundle.py)`
- Step-by-step implementation sequence:
  1. Add a checklist doc that divides gates into bundle integrity, updater behavior, automated testing, packaging, and clean-machine validation.
  2. For each gate, define the evidence source: script output, pytest target, packaged artifact inspection, or manual validation note.
  3. Require bundle-integrity evidence from `scripts/verify_bundle.py` after the DB is seeded.
  4. Require updater evidence from automated tests covering validation failure, rollback, live rebind, and reconciliation after update.
  5. Require packaging evidence from PyInstaller output and bundled resource inspection; explicitly note that installer-grade readiness is not met until an installer artifact and install test exist.
  6. Require a clean-machine/profile validation pass on Windows 10/11 that verifies first launch, offline operation, bundled assets, user data placement under `%APPDATA%`, and manual update behavior.
  7. Link the checklist language to the chosen updater scope so QA does not test for non-v1 asset downloading.
- Dependencies:
  - Final decisions from A/B/C.
- Risks/pitfalls:
  - A checklist without explicit evidence sources becomes ceremonial.
  - Current repo docs are stale about some readiness gaps, so the checklist must supersede them rather than copy them.
- Definition of done:
  - A reviewer can answer “ready / not ready” using a single checklist document.
  - Every checklist item maps to an executable check or specific manual validation step.
  - The checklist makes current installer-grade gaps explicit instead of hiding them.
- Must do now:
  - Create the release gate doc and align it to actual executable checks.
- Can defer until after Do Now:
  - Automating every manual clean-machine check.

## 4. Suggested task breakdown for an implementation agent

1. **Task: Asset reference inventory**
  - Purpose: Produce the authoritative list of required bundled egg/monster files from the seeded DB.
  - Likely files touched: `[scripts/seed_content_db.py](scripts/seed_content_db.py)`, working notes, possibly `resources/`
  - Estimated complexity: Small
  - Blockers/dependencies: None
2. **Task: Populate release asset bundle**
  - Purpose: Add the real release-approved egg/monster image files to match DB references exactly.
  - Likely files touched: `[resources/images/eggs/](resources/images/eggs/)`, `[resources/images/monsters/](resources/images/monsters/)`
  - Estimated complexity: Medium to Large
  - Blockers/dependencies: Availability of BBB-compliant source assets
3. **Task: Harden bundle verification**
  - Purpose: Make bundle verification fail on any missing DB-referenced asset or missing core resource.
  - Likely files touched: `[scripts/verify_bundle.py](scripts/verify_bundle.py)`, `[scripts/build.py](scripts/build.py)`
  - Estimated complexity: Medium
  - Blockers/dependencies: Task 1 complete; Task 2 or release-claim fallback decision made
4. **Task: Add bundle-integrity tests**
  - Purpose: Prove the verifier catches missing asset paths and passes complete bundles.
  - Likely files touched: new `tests/unit/test_verify_bundle.py` or `tests/integration/test_verify_bundle.py`
  - Estimated complexity: Medium
  - Blockers/dependencies: Task 3
5. **Task: Refactor updater into stage vs finalize**
  - Purpose: Separate download/validation from live DB replacement and service rebinding.
  - Likely files touched: `[app/updater/update_service.py](app/updater/update_service.py)`, `[app/bootstrap.py](app/bootstrap.py)`
  - Estimated complexity: Large
  - Blockers/dependencies: None
6. **Task: Add content rebinding in runtime services**
  - Purpose: Allow the app to swap to a reopened `content.db` and refresh caches/UI-backed reads.
  - Likely files touched: `[app/services/app_service.py](app/services/app_service.py)`, `[app/ui/main_window.py](app/ui/main_window.py)`, `[app/commands/add_target.py](app/commands/add_target.py)`
  - Estimated complexity: Medium
  - Blockers/dependencies: Task 5
7. **Task: Implement post-update reconciliation/finalization**
  - Purpose: Reconcile userstate against new content, clear undo/redo safely, and record finalization version.
  - Likely files touched: `[app/services/app_service.py](app/services/app_service.py)`, `[app/domain/reconciliation.py](app/domain/reconciliation.py)`, repositories/settings helpers, updater tests
  - Estimated complexity: Large
  - Blockers/dependencies: Tasks 5 and 6
8. **Task: Add updater finalization tests**
  - Purpose: Cover success, rollback, stale-cache refresh, and no-restart-needed behavior.
  - Likely files touched: `[tests/unit/test_updater.py](tests/unit/test_updater.py)`, possibly new integration tests
  - Estimated complexity: Medium to Large
  - Blockers/dependencies: Tasks 5 through 7
9. **Task: Align updater scope docs and UI copy**
  - Purpose: Make v1 updater scope explicit and remove conflicting runtime-media language.
  - Likely files touched: `[MSM_Awakening_Tracker_SRS_v1.1.md](MSM_Awakening_Tracker_SRS_v1.1.md)`, `[MSM_Awakening_Tracker_TDD_v1_3.md](MSM_Awakening_Tracker_TDD_v1_3.md)`, `[MSM_Awakening_Tracker_Vision.md](MSM_Awakening_Tracker_Vision.md)`, `[README.md](README.md)`, `[app/ui/settings_panel.py](app/ui/settings_panel.py)`
  - Estimated complexity: Medium
  - Blockers/dependencies: Decision C
10. **Task: Create release gate checklist**
  - Purpose: Define the minimum evidence required to declare release readiness.
  - Likely files touched: new `[RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md)`, `[README.md](README.md)`
  - Estimated complexity: Small
  - Blockers/dependencies: Decisions A/B/C fixed

## 5. Test plan

### Automated tests to add/update

- Update `[tests/unit/test_updater.py](tests/unit/test_updater.py)` to cover:
  - valid staged DB + successful finalize uses the new `content_version` immediately
  - failed staged DB validation leaves existing DB untouched
  - replacement/finalization failure restores backup and reopens prior DB
  - undo/redo is cleared only after successful finalization
  - post-update reconciliation runs against new content and leaves userstate valid
- Add bundle verifier tests for:
  - missing monster image path fails
  - missing egg image path fails
  - missing placeholder/audio/icon fails
  - complete temporary bundle passes
- Add an integration-style test for the live rebind path:
  - start with one content DB version
  - apply a staged replacement with different metadata and at least one changed monster/content record
  - assert `AppService.get_settings_viewmodel()`, catalog data, and add-target validation use the new connection without restart
- Keep existing reconciliation and acceptance tests, but add one update-driven reconciliation case where requirements shrink or a monster becomes deprecated.

### Manual validation to perform

- Developer build/manual run:
  - launch with bundled resources only and no network
  - confirm catalog images and egg icons render from bundled paths
  - open Settings and verify content version/last updated metadata display
- Manual update flow:
  - use a controlled test manifest/staged DB with a changed `content_version`
  - install update from Settings
  - confirm success message reflects immediate activation, not “restart required”
  - confirm Settings version label updates immediately
  - confirm catalog and add-target behavior reflect new content in the same session
- Bundle verification/manual package inspection:
  - inspect PyInstaller output for `resources/db/content.db`, `resources/images/...`, `resources/audio/ding.wav`, and icon presence

### Failure/rollback cases

- Corrupt staged DB
- Manifest missing `content_db_url`
- DB replacement fails while backup exists
- Reopen of replaced DB fails
- Post-update reconciliation fails after replacement; previous DB must be restored and reopened
- Deprecated-monster finalization removes or invalidates active targets safely with user-visible status messaging

### Windows-specific concerns

- Verify file replacement while prior SQLite connection is closed and WAL/SHM sidecars are handled.
- Validate on Windows 10 and Windows 11 if possible, or at minimum one OS plus one clean profile.
- Confirm no admin rights are needed post-install and data remains under `%APPDATA%\MSMAwakeningTracker`.
- Confirm packaged app works when launched from a non-dev machine/profile without a local `resources/` source tree.

## 6. Documentation updates required

### If the recommended DB-only updater scope is chosen

- `[MSM_Awakening_Tracker_SRS_v1.1.md](MSM_Awakening_Tracker_SRS_v1.1.md)`
  - Rewrite FR-703 to FR-705 so the installed client performs **manual content DB updates**, not in-app wiki scraping or image downloading.
  - Keep the product outcome that new monsters may appear after updates, but attribute discovery/content assembly to the maintainer pipeline rather than the installed client.
- `[MSM_Awakening_Tracker_TDD_v1_3.md](MSM_Awakening_Tracker_TDD_v1_3.md)`
  - Narrow Section 6.5/6.6/18 references to downloaded asset cache, asset fetcher, and BBB Fan Kit runtime downloads.
  - Keep the post-update finalization/reconciliation behavior, but frame it around DB replacement only.
- `[MSM_Awakening_Tracker_Vision.md](MSM_Awakening_Tracker_Vision.md)`
  - Update the Q&A or product statements that imply the app itself fetches both data and images during update.
- `[README.md](README.md)`
  - Clarify that updates refresh content data, while bundled media ships in the installer/build bundle.
  - Align content-coverage claims with what is actually present in `resources/`.
- User-facing text
  - `[app/ui/settings_panel.py](app/ui/settings_panel.py)`: consider changing button/status text to “Check for Content Updates” / “Install Content Update” so the shipped UI does not imply broader media sync than implemented.

### If DB + image/media updater scope is chosen instead

- Keep the broader SRS/Vision intent, but add or restore implementation docs for:
  - manifest schema covering DB plus asset payloads
  - asset cache population and rollback rules
  - provenance/domain allowlist rules for downloaded media
  - user-facing messaging that explicitly says images can update after install
- This path is not recommended for the current Do Now scope.

## 7. Sequencing recommendation

1. **Fix the updater v1 scope decision first on paper** so implementation does not chase the wrong architecture. This unblocks the rest of the plan and locks the test target.
2. **Do asset bundle integrity next** because it is the clearest release blocker and the build/package pipeline cannot be trusted until the bundle is real and verified.
3. **Then implement updater finalization** once the content source-of-truth and shipped bundle assumptions are stable. This avoids designing rebinding/finalization around a moving updater scope.
4. **Create the release gate checklist last, but before sign-off** so it reflects the actual implemented bundle rules, updater behavior, and packaging status rather than stale assumptions.

Reasoning: scope clarity prevents wasted work; bundle integrity is the most immediate blocker to a truthful offline release; updater finalization is the biggest behavioral correctness fix once the content model is settled; the release checklist should codify the finished minimum bar rather than speculate ahead of implementation.