# Release Gate Checklist

This checklist defines the minimum criteria for declaring a build "release-ready."
Every item must pass before the build may be shipped. Items marked with a script
name are verified by running that script; manual items require a human sign-off.

---

## 1. Bundle Integrity

| # | Gate | Evidence source | Pass? |
|---|------|-----------------|-------|
| 1.1 | `resources/db/content.db` exists and is seeded | `scripts/verify_bundle.py` | |
| 1.2 | `resources/images/ui/placeholder.png` exists | `scripts/verify_bundle.py` | |
| 1.3 | `resources/images/ui/app_icon.ico` exists | `scripts/verify_bundle.py` | |
| 1.4 | `resources/audio/ding.wav` exists | `scripts/verify_bundle.py` | |
| 1.5 | Every `monsters.image_path` in content.db resolves to a file under `resources/` | `scripts/verify_bundle.py` | |
| 1.6 | Every `egg_types.egg_image_path` in content.db resolves to a file under `resources/` | `scripts/verify_bundle.py` | |
| 1.7 | Monster count >= 64 (20 Wublins, 12 Celestials, 32 Amber Vessels) | `scripts/verify_bundle.py` | |
| 1.8 | Egg type count >= 76 | `scripts/verify_bundle.py` | |
| 1.9 | No orphaned requirement rows | `scripts/verify_bundle.py` | |

**How to verify:** `python scripts/verify_bundle.py` — must exit 0.

---

## 2. Automated Tests

| # | Gate | Evidence source | Pass? |
|---|------|-----------------|-------|
| 2.1 | Full test suite passes (`pytest tests/ -v`) | pytest output | |
| 2.2 | Acceptance criteria AC-R01 through AC-R06 pass | `tests/unit/test_acceptance.py` | |
| 2.3 | GUI smoke tests pass | `tests/unit/test_gui_smoke.py` | |
| 2.4 | Updater validation tests pass | `tests/unit/test_updater.py` | |
| 2.5 | Updater finalization tests pass (rebind, rollback, WAL cleanup) | `tests/unit/test_update_finalization.py` | |
| 2.6 | Bundle verifier tests pass | `tests/unit/test_verify_bundle.py` | |

**How to verify:** `python -m pytest tests/ -v --tb=short` — must exit 0 with 0 failures.

---

## 3. Updater Behavior

| # | Gate | Evidence source | Pass? |
|---|------|-----------------|-------|
| 3.1 | Updater is DB-only (no runtime image download or wiki scraping) | Code review / `app/updater/update_service.py` | |
| 3.2 | Successful update replaces content.db and reopens connection | `tests/unit/test_update_finalization.py` | |
| 3.3 | AppService rebinds caches after update (requirements, egg types) | `tests/unit/test_update_finalization.py` | |
| 3.4 | Settings panel shows new content version immediately after update | Manual test | |
| 3.5 | Undo/redo stack is cleared after successful finalization | `tests/unit/test_updater.py` | |
| 3.6 | Failed validation leaves prior content.db untouched | `tests/unit/test_updater.py` | |
| 3.7 | Failed finalization restores backup and reopens prior connection | `tests/unit/test_update_finalization.py` | |
| 3.8 | WAL/SHM sidecars are removed before DB replacement on Windows | `tests/unit/test_update_finalization.py` | |

---

## 4. Packaging

| # | Gate | Evidence source | Pass? |
|---|------|-----------------|-------|
| 4.1 | `python scripts/build.py` completes successfully | Build script output | |
| 4.2 | PyInstaller output at `dist/MSMAwakeningTracker/` contains the executable | File inspection | |
| 4.3 | `dist/MSMAwakeningTracker/resources/` contains `db/content.db` | File inspection | |
| 4.4 | `dist/MSMAwakeningTracker/resources/images/` contains egg and monster images | File inspection | |
| 4.5 | `dist/MSMAwakeningTracker/resources/audio/ding.wav` exists | File inspection | |
| 4.6 | Application icon is embedded in the `.exe` | File inspection | |

| 4.7 | `installer/msm_tracker.iss` (Inno Setup) compiles the per-user installer | `iscc installer/msm_tracker.iss` → `installer/Output/` | |

---

## 5. Clean-Machine Validation

| # | Gate | Evidence source | Pass? |
|---|------|-----------------|-------|
| 5.1 | App launches from packaged build on Windows 10 or 11 without Python installed | Manual test on clean machine/VM | |
| 5.2 | First launch copies bundled content.db to `%APPDATA%\MSMAwakeningTracker\` | Manual verification | |
| 5.3 | Catalog displays monster images from bundled assets (not blank/broken) | Visual check | |
| 5.4 | Breed List egg icons display from bundled assets | Visual check | |
| 5.5 | Core workflow functions offline (add target, increment, close out, undo/redo) | Manual walkthrough | |
| 5.6 | No admin privileges required for normal operation post-install | Manual test | |
| 5.7 | User data persists across app restart from `%APPDATA%` | Manual test | |

---

## 6. Documentation Alignment

| # | Gate | Evidence source | Pass? |
|---|------|-----------------|-------|
| 6.1 | SRS FR-703 through FR-705 describe DB-only content updates | Document review | |
| 6.2 | TDD Section 18 describes manifest + staged DB flow, not wiki scraping | Document review | |
| 6.3 | README content coverage claims match actual `resources/` contents | Document review | |
| 6.4 | Settings panel UI text says "Content Updates" (not generic "Updates") | Visual check | |
| 6.5 | BBB Fan Content Policy disclaimer is present in Settings | Visual check | |

---

## Sign-off

| Role | Name | Date | Notes |
|------|------|------|-------|
| Developer | | | |
| Reviewer | | | |
