---
name: MSM next roadmap
overview: Turn the current bootstrap-quality desktop app into a coherent MVP roadmap that preserves the existing architecture, prioritizes shipping a polished offline experience, and sequences updater/release work behind the core product gaps that block confidence today.
todos:
  - id: phase1-core
    content: Align the current UI with spec-critical MVP behavior and add GUI smoke confidence around the core loop.
    status: completed
  - id: phase2-content
    content: Complete bundled content and assets so the app delivers a real offline experience by default.
    status: completed
  - id: phase3-updater
    content: Implement a safe manual updater after the content contract and reconciliation behavior are stable.
    status: completed
  - id: phase4-polish
    content: Apply UX fidelity, accessibility, and desktop polish without expanding product scope.
    status: completed
  - id: phase5-release
    content: Add packaging, installer, and release validation once runtime paths and bundled resources are stable.
    status: completed
isProject: false
---

# MSM Companion App Next Steps

## Executive Summary

The current build is a strong base rather than a release candidate. The architecture is already worth preserving: startup/bootstrap is clean in [c:\MSM_App\app\bootstrap.py](c:\MSM_App\app\bootstrap.py), command/state orchestration is centralized in [c:\MSM_App\app\services\app_service.py](c:\MSM_App\app\services\app_service.py), and the main user loop is already reflected in tests like [c:\MSM_App\tests\unit\test_acceptance.py](c:\MSM_App\tests\unit\test_acceptance.py).

Top priorities should be:

- Complete the shipped offline product baseline: the app expects bundled content and assets, but the current runtime falls back to placeholders through [c:\MSM_App\app\assets\resolver.py](c:\MSM_App\app\assets\resolver.py) and seeds only partial Amber content in [c:\MSM_App\scripts\seed_content_db.py](c:\MSM_App\scripts\seed_content_db.py).
- Bring the UI into spec on the highest-visibility interactions: the catalog is already tabbed in [c:\MSM_App\app\ui\catalog_panel.py](c:\MSM_App\app\ui\catalog_panel.py), but the implementation still renders a vertical list, and egg increment currently fires from the whole row in [c:\MSM_App\app\ui\widgets\egg_row_widget.py](c:\MSM_App\app\ui\widgets\egg_row_widget.py) instead of just the icon.
- Add confidence and packaging only after the above are stable: updater UI is still a stub in [c:\MSM_App\app\ui\settings_panel.py](c:\MSM_App\app\ui\settings_panel.py) and packaging artifacts are not present, but neither should be built on top of incomplete bundled content or mismatched UX.

## Gap Analysis

### Functional Gaps

- End-to-end manual update flow is not implemented. The Settings screen exists, but `Check for Updates` is explicitly disabled in [c:\MSM_App\app\ui\settings_panel.py](c:\MSM_App\app\ui\settings_panel.py).
- Undo/redo exists in service logic and keyboard shortcuts in [c:\MSM_App\app\ui\main_window.py](c:\MSM_App\app\ui\main_window.py), but there is no visible affordance or state feedback for it.
- Close-out currently operates at grouped monster level from [c:\MSM_App\app\ui\inwork_panel.py](c:\MSM_App\app\ui\inwork_panel.py), which limits visibility into duplicate target instances.

### Content And Data Gaps

- Bundled `content.db` expectations are in place in [c:\MSM_App\app\bootstrap.py](c:\MSM_App\app\bootstrap.py), but the release content seed only includes 19 Wublins, 12 Celestials, and 1 Amber monster in [c:\MSM_App\scripts\seed_content_db.py](c:\MSM_App\scripts\seed_content_db.py).
- Asset references are populated in the DB seed, but the bundle expected under `resources/images` and `resources/audio` is not complete, so the current UX is placeholder-heavy.
- Test fixtures in [c:\MSM_App\tests\conftest.py](c:\MSM_App\tests\conftest.py) still use a reduced synthetic data set rather than validating against the real packaged content shape.

### UI And UX Gaps

- The egg increment affordance does not match spec: `mousePressEvent()` on the whole row emits increment in [c:\MSM_App\app\ui\widgets\egg_row_widget.py](c:\MSM_App\app\ui\widgets\egg_row_widget.py).
- The catalog implementation is a scrollable vertical card list despite the intended grid presentation in [c:\MSM_App\app\ui\catalog_panel.py](c:\MSM_App\app\ui\catalog_panel.py).
- Placeholder and asset state are available in view models in [c:\MSM_App\app\ui\viewmodels.py](c:\MSM_App\app\ui\viewmodels.py) but not used to improve fallback presentation or communicate missing official assets.

### Technical And Developer Experience Gaps

- There is no dedicated updater module, no network dependency, and no tests for update/reconciliation integration.
- There are no UI tests despite `pytest-qt` already being present in [c:\MSM_App\requirements.txt](c:\MSM_App\requirements.txt).
- Asset pipeline expectations exist, but there is no repeatable fetch/prepare/verify workflow for bundled images/audio.

### Release Readiness Gaps

- No packaging pipeline or installer artifacts exist yet.
- No icon pipeline or packaged-build verification flow is present.
- No GUI smoke-test checklist or automated smoke suite exists for pre-release confidence.

## Phased Roadmap

### Phase 1: Stabilize MVP Core

Objective:

- Align the existing working app with the required MVP interaction model and improve confidence around the core loop.

Why this phase comes first:

- The app already has the right command/service structure. The fastest path to a coherent MVP is to finish the current experience before building secondary systems around it.

Concrete deliverables:

- Egg increment restricted to clicking the egg icon only.
- Catalog converted from vertical list to a true card grid.
- Undo/redo state surfaced in the main shell and verified against current `AppService` state.
- Close-out behavior clarified for duplicate targets, either through per-instance handling or explicit product-approved grouped behavior.
- `pytest-qt` smoke coverage for add target, increment egg, close out, undo, redo, and restart persistence.

Dependencies:

- Existing seams in [c:\MSM_App\app\ui\main_window.py](c:\MSM_App\app\ui\home_view.py), [c:\MSM_App\app\ui\catalog_panel.py](c:\MSM_App\app\ui\inwork_panel.py), and [c:\MSM_App\app\services\app_service.py](c:\MSM_App\app\services\app_service.py).

Risks and blockers:

- Duplicate-target close-out may require a small UX/product call if grouped cards are retained.
- Grid layout work can expose missing assets more aggressively, increasing pressure on Phase 2.

Exit criteria / Definition of done:

- Core add/increment/close-out/undo/redo loop matches the SRS interaction model.
- A basic GUI smoke suite passes locally and covers the main user journey.
- No known mismatch remains between documented MVP behavior and the visible UI for the home and catalog flows.

### Phase 2: Complete Content And Asset Bundling

Objective:

- Make the app feel like a real offline product by shipping the intended content database and bundled media.

Why this phase belongs here:

- Packaging and updater work are lower-value until the baseline offline install actually contains the intended content and visuals.

Concrete deliverables:

- `resources/db/content.db` regenerated from a release-grade seed.
- Amber content expanded from Kayna-only to the agreed full supported vessel set.
- Bundled monster art, egg art, UI placeholder image, ding audio, and asset manifest/verification rules.
- Test fixtures updated to reflect real content categories and representative Amber coverage.

Dependencies:

- [c:\MSM_App\scripts\seed_content_db.py](c:\MSM_App\scripts\seed_content_db.py), [c:\MSM_App\app\assets\resolver.py](c:\MSM_App\app\assets\resolver.py), and the release resource layout expected by [c:\MSM_App\app\bootstrap.py](c:\MSM_App\app\bootstrap.py).

Risks and blockers:

- Official BBB Fan Kit asset availability may be incomplete.
- Amber scope may need a product call if seasonality/availability metadata becomes necessary.

Exit criteria / Definition of done:

- Fresh install can run offline with bundled DB and bundled core assets.
- Supported monsters ship with correct catalog entries and requirement rows.
- Missing official art is the exception, not the default UX path.

### Phase 3: Implement Manual Updater

Objective:

- Add a safe manual content refresh flow that can discover and apply new supported content without harming local user state.

Why this phase belongs here:

- Once bundled content is stable, the updater can target a well-defined content contract and reconciliation behavior instead of chasing moving seed rules.

Concrete deliverables:

- Dedicated updater module with fetch, stage, validate, apply, rollback-safe failure handling, and post-update reconciliation.
- Settings screen wiring for `Check for Updates`, progress/status feedback, and success/failure messaging.
- Content-version comparison and metadata refresh in the UI.
- Tests for update success, no-update case, network failure, invalid payload, and reconciliation clip behavior using [c:\MSM_App\app\domain\reconciliation.py](c:\MSM_App\app\domain\reconciliation.py).

Dependencies:

- Stable content schema from [c:\MSM_App\app\db\migrations\content\0001_initial_schema.sql](c:\MSM_App\app\db\migrations\content\0001_initial_schema.sql).
- Product/source decision for where update payloads are hosted and how official assets are distributed.

Risks and blockers:

- External source format and reliability may introduce delivery risk.
- Update safety rules must be explicit so failed updates never corrupt `content.db` or user progress.

Exit criteria / Definition of done:

- User can manually check for updates from Settings.
- A successful update replaces content metadata and preserves user state.
- A failed update leaves the prior app content intact and clearly informs the user.

### Phase 4: UX Fidelity And Product Polish

Objective:

- Raise the app from functional to polished while staying within v1 scope.

Why this phase belongs here:

- Visual polish is most efficient once core interactions, content shape, and updater behavior are stable.

Concrete deliverables:

- Better placeholder treatment and image-state awareness.
- Focus states, keyboard polish, spacing, and 1080p readability verification.
- Home, catalog, and settings views tuned to the dark polished visual target.
- Visible app icon/disclaimer/version presentation finalized.

Dependencies:

- Stable assets and packaged visuals from Phase 2.
- Main shell and state plumbing from Phase 1.

Risks and blockers:

- Easy to overrun into scope creep; this phase should stay focused on fidelity, not new feature invention.

Exit criteria / Definition of done:

- No major spec-visible UI mismatch remains.
- The app is visually coherent in the packaged desktop context.
- Accessibility and keyboard basics have been manually verified.

### Phase 5: Packaging, QA, And Release Readiness

Objective:

- Produce a repeatable Windows release flow with enough confidence to ship.

Why this phase belongs last:

- Packaging is only meaningful once the runtime experience, assets, and update assumptions are stable.

Concrete deliverables:

- PyInstaller packaging configuration and bundled-resource inclusion.
- Windows installer pipeline and release checklist.
- GUI smoke-test runbook and packaged-build validation on a clean machine/profile.
- Versioning, icon inclusion, and installer acceptance criteria.

Dependencies:

- Stable resource bundle and updater decisions.
- Finalized runtime paths already started in [c:\MSM_App\app\bootstrap.py](c:\MSM_App\app\bootstrap.py).

Risks and blockers:

- Packaging will surface hidden path or asset resolution assumptions.
- Installer decisions may affect update locations and future patch strategy.

Exit criteria / Definition of done:

- App installs on Windows without requiring Python.
- Packaged build launches, loads bundled content/assets, and passes smoke tests.
- Release checklist can be executed repeatedly with predictable output.

## Prioritized Task List

1. `[Must do now]` Convert the catalog from vertical list to true responsive grid. Owner: frontend. Effort: M. Rationale: current catalog behavior is a visible spec miss and affects first-run usability.
2. `[Must do now]` Restrict increment interaction to the egg icon instead of the full row. Owner: frontend. Effort: S. Rationale: this is an explicit UX/spec requirement and a high-visibility mismatch.
3. `[Must do now]` Add GUI smoke tests for add target, increment, close-out, undo, and redo. Owner: QA. Effort: M. Rationale: current automated confidence is mostly domain/data level, not user-journey level.
4. `[Must do now]` Decide and implement duplicate-target close-out UX for grouped In-Work cards. Owner: product plus frontend. Effort: M. Rationale: current grouped behavior hides instance-level intent and can create ambiguous close-out behavior.
5. `[Must do now]` Surface undo/redo availability in the main window. Owner: frontend. Effort: S. Rationale: capability already exists in `AppService`; exposing it improves discoverability and reviewability.
6. `[Must do now]` Expand `seed_content_db.py` to the full approved Amber scope. Owner: backend/data. Effort: M. Rationale: partial Amber support blocks content completeness.
7. `[Must do now]` Generate and check in a release-grade bundled `resources/db/content.db`. Owner: backend/data. Effort: S. Rationale: the app’s offline baseline should not rely on post-install updates to feel complete.
8. `[Must do now]` Add the minimum viable bundled asset set: placeholder image, egg art, monster art, ding audio. Owner: backend/data. Effort: L. Rationale: the current fallback-heavy experience undermines the polished product goal.
9. `[Should do soon]` Add asset verification tooling or a manifest check to catch missing bundle files before packaging. Owner: build/release. Effort: M. Rationale: reduces silent broken-image regressions.
10. `[Should do soon]` Update test fixtures to reflect real content categories and Amber coverage. Owner: backend/data. Effort: M. Rationale: current fixtures underrepresent shipped data complexity.
11. `[Should do soon]` Add unit tests for `AppService` state derivation and undo/redo state flags. Owner: QA. Effort: M. Rationale: this is the main orchestration seam.
12. `[Should do soon]` Implement a dedicated updater package with content-version comparison and staging. Owner: backend/data. Effort: L. Rationale: updater is still a stub but should be built on stable content assumptions.
13. `[Should do soon]` Wire the Settings panel update button to the updater flow and status messaging. Owner: frontend plus backend/data. Effort: M. Rationale: completes the user-facing manual update path.
14. `[Should do soon]` Add safe-failure and rollback tests for update application. Owner: QA. Effort: M. Rationale: update failures must be non-destructive.
15. `[Should do soon]` Implement post-update reconciliation and undo/redo reset rules where content changes affect requirements. Owner: backend/data. Effort: M. Rationale: protects invariants when the content DB changes.
16. `[Should do soon]` Improve placeholder presentation and use `is_placeholder` to distinguish official vs fallback visuals. Owner: frontend. Effort: S. Rationale: makes missing assets explicit without breaking the polished UX.
17. `[Should do soon]` Add app icon pipeline and final disclaimer/version presentation for packaged builds. Owner: build/release. Effort: M. Rationale: needed for a credible desktop release.
18. `[Can wait]` Create PyInstaller packaging configuration and resource inclusion rules. Owner: build/release. Effort: M. Rationale: should follow stable assets, paths, and update assumptions.
19. `[Can wait]` Create Windows installer automation and release checklist. Owner: build/release. Effort: M. Rationale: packaging should come after the packaged app itself is stable.
20. `[Can wait]` Add packaged-build smoke tests on a clean Windows profile/machine. Owner: QA plus build/release. Effort: M. Rationale: best done once packaging artifacts are repeatable.
21. `[Can wait]` Tune accessibility and keyboard focus details across home, catalog, and settings. Owner: frontend plus QA. Effort: M. Rationale: important for polish, but not ahead of content completeness and updater basics.
22. `[Can wait]` Add performance checks against startup, interaction, and reconciliation targets from the SRS. Owner: QA. Effort: M. Rationale: meaningful after the product surface is closer to final.

## Critical Path

The true critical path to a usable MVP is:

1. Lock the visible user journey to spec.
  - Grid catalog, icon-only egg increment, and unambiguous close-out behavior remove the most obvious gaps between “works” and “reviewable MVP.”
2. Ship complete offline content.
  - Full approved monster coverage and a real bundled `content.db` unblock confidence that the app is useful without updates.
3. Ship the minimum polished asset bundle.
  - Without bundled visuals/audio, the product still reads like a scaffold.
4. Add GUI smoke coverage around the main workflow.
  - This is the minimum confidence gate before adding updater and packaging complexity.
5. Build manual updater on top of the stable content contract.
  - Updater depends on known content schema, known asset layout, and explicit reconciliation rules.
6. Package and validate the Windows release.
  - Packaging is the final integrator, not the starting point.

What unlocks what:

- UI-spec fixes unlock meaningful UX review.
- Complete bundled content unlocks asset bundling and release-value validation.
- Stable content plus tests unlock safe updater implementation.
- Stable runtime paths plus assets plus updater decisions unlock packaging.

## Recommended Immediate Next Sprint

Sprint goal:

- Deliver the first coherent MVP-quality build by closing the biggest visible spec gaps and making the app shippable as a complete offline experience internally.

Exact tasks for the next sprint:

1. Convert the catalog to a real grid layout.
2. Change breed-list interaction so only the egg icon increments progress.
3. Expose undo/redo availability in the shell.
4. Resolve duplicate-target close-out behavior and implement the chosen interaction.
5. Expand the content seed to the approved Amber scope.
6. Generate and include the release `content.db`.
7. Add the minimum bundled placeholder/image/audio asset set.
8. Add `pytest-qt` smoke tests for the main user loop and a fresh-start persistence check.

Suggested order of implementation:

1. UI spec corrections first: catalog grid, icon-only increment, undo/redo visibility.
2. In-Work duplicate close-out behavior next, because it may require a small product decision.
3. Content seed expansion and bundled DB generation.
4. Minimum asset bundle and asset verification check.
5. GUI smoke tests over the now-stable flow.

What should be deferred from this sprint:

- Full updater implementation.
- Installer/packaging automation.
- Final app icon pipeline beyond placeholder readiness.
- Performance optimization beyond obvious regressions.

## Acceptance Criteria For The Next Build

- Catalog displays supported monsters in a grid, grouped by Wublins, Celestials, and Amber Vessels.
- Egg progress increments only when the egg icon is clicked; clicking the rest of the row does not increment.
- Undo and redo can be triggered by keyboard shortcuts and have visible enabled/disabled state in the UI.
- Duplicate target close-out behavior is deterministic and documented in the build notes.
- Bundled `content.db` contains all regular Wublins, all regular Celestials, and the approved Amber scope for this release.
- Fresh offline startup on a clean profile loads bundled content without errors and shows official assets where available.
- Placeholder image and ding audio resolve successfully from the bundled resources.
- GUI smoke tests pass for: add target, increment egg, complete row fade/remove, close out monster, undo, redo, and restart persistence.
- No blocker-level mismatch remains between the build and the current SRS for the core home/catalog workflow.

## Risks And Unknowns

- Amber scope may still need a product decision if “standard Amber Vessels” implies seasonality or availability windows rather than simple catalog inclusion.
- Official asset availability from the BBB Fan Kit may be incomplete; this affects how much of the product can be fully polished in the next build.
- Update hosting/source format is still undefined and could materially change the updater plan.
- Grouped duplicate targets may require a UX/product choice: close newest instance, prompt for which instance, or expose per-instance rows.
- Packaging choice may influence how future updates are delivered and where assets/content are stored.

Assumptions used in this plan:

- The existing architecture should remain intact.
- The next build should optimize for coherent offline MVP quality, not release-candidate completeness.
- Manual updates are required for v1 release readiness, but not before the offline baseline is complete.

## Final Recommendation

The smartest next move is to spend the next sprint finishing the MVP the user can see and feel: fix the spec-visible interaction mismatches, complete the bundled content and asset baseline, and add GUI smoke confidence. That sequence converts the current app from a promising scaffold into a believable internal MVP and gives the updater and packaging work a stable target to build on, instead of layering release systems onto an incomplete product surface.