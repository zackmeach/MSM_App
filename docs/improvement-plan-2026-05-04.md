# MSM App — Software Improvement Plan
**Date:** 2026-05-04
**Author:** Multi-agent audit (7 independent Opus 4.7 agents) + synthesis
**Branch:** main @ b266a15

---

## How to read this plan

This document was produced by 7 independent audit agents, each scoped to a single domain of the codebase, with no shared context. Their findings were then synthesized into the prioritized, phased plan below.

- **Phases are sequenced by dependency, not just severity.** Phase 0 fixes correctness and legal risks. Later phases tackle reproducibility, hardening, performance, and polish.
- **Each work item (W-#) cites the audit that found it, the file paths involved, and a concrete "Do" list.** They're sized so that any one item can be picked up as a single focused PR.
- **Severity:** Critical = correctness/security/legal risk to ship; High = real bug or strong code-smell with user impact; Medium = quality/maintainability; Low = polish.
- **Effort:** XS = under 1 hour; S = half-day; M = 1–2 days; L = 3+ days.
- The full per-domain audit summaries are in the Appendix.

---

## At a glance

| Domain | Critical | High | Medium | Low |
|---|---:|---:|---:|---:|
| Architecture & Code Quality | 2 | 3 | 5 | 4 |
| Data Layer & Migrations | 2 | 4 | 4 | 5 |
| UI Layer & Performance | 0 | 4 | 6 | 4 |
| Test Suite Quality | 2 | 3 | 6 | 3 |
| Build / Release / Updater Security | 2 | 5 | 8 | 5 |
| Content Pipeline | 0 | 5 | 7 | 6 |
| Documentation & DX | 3 | 5 | 7 | 4 |
| **Total** | **11** | **29** | **43** | **31** |

**Total findings: ~114.** Most are small, atomic, and low-risk to fix.

**The single most important takeaway:** the architectural boundaries CLAUDE.md describes — pure domain, function-style repos, command-pattern mutations, no UI access to repos, no `pipeline/` imports in `app/` — *are genuinely intact*. Multiple agents independently verified this with grep. The codebase has good bones. The issues below are about hardening, polishing, and eliminating drift, not about fundamental redesign.

---

## Cross-cutting themes

The 7 audits agreed on five patterns. These are the highest-leverage things to fix because each shows up in multiple domains:

**1. The trust chain has a single point of failure.**
The content `manifest.json` is fetched over HTTPS but is *unsigned*. Anyone who compromises the GitHub repo, a maintainer machine with push rights, or the `publish-content.yml` workflow (`workflow_dispatch`, `contents: write`, no required reviewer) can poison every installed app's `content.db` on the next update check. The EXE is also unsigned. This is the single highest-impact issue in the whole audit.

**2. Mid-operation failure recovery is consistently weak.**
Three independent agents flagged variations of the same shape:
- `app/db/migrations.py` uses `executescript` which auto-commits — a partial migration leaves a half-upgraded DB recorded as not applied.
- `AppService.reconcile_after_content_update` is not wrapped in a transaction; mid-loop failures leave userstate.db half-reconciled with no recovery.
- The updater's `finalize_update` has a small but real window between `copy2` of the backup and `os.replace` of the live DB where a crash leaves no recoverable state.

**3. Reproducibility is broken in three places.**
- `requirements.txt` uses `>=` ranges with no lockfile; `pip install` produces different bundles on different days.
- The published `manifest.json` embeds `datetime.now()` and a timestamp-derived `build_id`, so identical inputs produce different manifests.
- The published `content.db` may itself be non-deterministic (no `VACUUM`/`application_id`/`page_size` pinning before hashing).

**4. Code-doc drift is widespread.**
- CLAUDE.md and AGENTS.md claim 359 tests; actual is 414.
- README.md and `RELEASE_CHECKLIST.md` claim "no installer wrapper exists yet" but `installer/msm_tracker.iss` is checked in.
- `RELEASE_CHECKLIST.md` claims ≥39 monsters / ≥38 eggs; actual is 64 monsters / 76 eggs.
- `--debug` flag documented in CLAUDE.md is not actually parsed in `main.py`.
- `ReconciliationResult` in `domain/models.py` is dead — the spec contract was never implemented.
- `seed_content_db.py` carries a 200-line literal-data fallback that drifts from `pipeline/normalized/*.json`.
- `app/ui/main_window.py` line 7 has a dead `import sqlite3`.
- `requirements.txt` includes `jsonschema` which is never imported.

**5. Layering boundaries hold *almost* perfectly — but a couple of leaks exist.**
- `app/services/app_service.py:313` imports from `app.ui.themes` (service depending on UI).
- `app/ui/viewmodels.py` lives under `ui/` despite being plain dataclasses with no Qt deps — they should live in `domain/` or `services/` so the dependency arrow points correctly.
- Otherwise: zero `from app.repositories` or `import sqlite3` in `app/ui/`, zero `from app.ui` or `import PySide6` in `app/domain/`, zero `from pipeline` in `app/`.

---

## Phase 0 — Stop the Bleeding
**Goal:** Eliminate every Critical-severity finding. These are correctness, security, or legal risks that block confident shipping.

### W0.1 — Add LICENSE and fan-content disclaimer
**Severity:** Critical (legal)
**Source:** Doc audit
**Effort:** XS
**Why:** The repo is public on GitHub with no LICENSE file — by default it's "all rights reserved," blocking any contributor. Worse, the project ships and references "BBB Fan Kit" copyrighted artwork from Big Blue Bubble's *My Singing Monsters* without any trademark attribution or fan-content disclaimer at the repo root. The only fair-use rationale lives in `pipeline/SOURCE_POLICY.md`.
**Where:** repo root; `README.md`.
**Do:**
1. Pick a license — MIT or Apache-2.0 are most permissive for a hobby app; or a more restrictive one if you want to retain control. Add `LICENSE` at root.
2. Add a "Legal & Attribution" section to README.md citing the BBB Fan Content Policy, "Not affiliated with Big Blue Bubble," and that *My Singing Monsters*, *Wublins*, *Celestials*, *Amber Vessels*, and the Fan Kit are BBB IP.
3. Add a `NOTICE` file at root with the same attribution if your license requires it (Apache-2.0 does).

### W0.2 — Document where to obtain the Fan Kit
**Severity:** Critical (onboarding-blocking)
**Source:** Doc audit
**Effort:** XS
**Why:** `Monsters/` is `.gitignore`d (line 46). README:21 and `scripts/import_fankit_images.py` reference it but never explain where it comes from. A clean clone followed by `python scripts/import_fankit_images.py` silently produces no images.
**Do:**
1. Add a "Setup → Fan Kit images" subsection to README.md with the link to the BBB Fan Content / Fan Kit download and where to drop the unzipped folder.
2. Have `scripts/import_fankit_images.py` print a clear "expected `Monsters/` not found — see README §X" message and exit non-zero when the directory is missing.

### W0.3 — Sign the content manifest and pin the trust root
**Severity:** Critical (security)
**Source:** Updater & Security audit
**Effort:** M
**Why:** `validate_manifest_contract()` (`app/updater/validator.py:88-101`) only checks shape/length, not authenticity. A poisoned manifest pushed by anyone with repo access (or a successful workflow-injection PR) flips every installed app to attacker-controlled content. There's no signature, no pinned public key.
**Where:** `app/updater/validator.py`, `app/updater/update_service.py`, `pipeline/publish/artifacts.py`, GitHub Actions workflows.
**Do:**
1. Pick a signing scheme — recommended: **minisign** (small, no PKI, single keypair, drops in cleanly) or **cosign** if you want Sigstore.
2. Generate a keypair offline. Commit the *public* key into `app/updater/trust/pubkey.minisign`. Store the private key as a GitHub Actions secret.
3. Update `pipeline/publish/artifacts.py` to write `content/manifest.json.minisig` next to the manifest.
4. In `app/updater/validator.py`, add `verify_manifest_signature(manifest_bytes, sig_bytes, pubkey)` that runs *before* `validate_manifest_contract()`. Fail loudly on mismatch.
5. Update `app/updater/update_service.py:do_check` to fetch both `manifest.json` and `manifest.json.minisig`, then run signature check before any field is trusted.
6. Add CI step that signs on tagged release.

### W0.4 — Restrict manifest URL fields to HTTPS + allowlisted host
**Severity:** Critical (security)
**Source:** Updater & Security audit
**Effort:** S
**Why:** `_UpdateWorker.do_stage` passes `content_db_url` from the manifest straight to `urllib.request.urlopen` (`app/updater/update_service.py:127-139`). A poisoned manifest can point at `http://attacker.example/x.db`, `file:///C:/...`, or `ftp://...`. Even though SHA-256 still has to match, the request *happens first*. SHA-256 mismatch will reject the *content*, but the request itself can still leak data via DNS or read local files.
**Where:** `app/updater/validator.py:88-101`.
**Do:**
1. In `validate_manifest_contract`, parse `content_db_url` with `urllib.parse.urlparse`.
2. Require `scheme == "https"` and `host in {"raw.githubusercontent.com"}` (extend allowlist if you ever add CDN). Reject otherwise.
3. Add unit tests covering: `http://`, `file://`, `ftp://`, malformed URLs, and a host-spoofing attempt like `raw.githubusercontent.com.attacker.example`.

### W0.5 — Make migrations atomic
**Severity:** Critical (data integrity)
**Source:** Data Layer audit
**Effort:** S
**Why:** `app/db/migrations.py:57` runs `conn.executescript(sql)` which auto-commits any prior implicit transaction and runs each statement individually. If a multi-statement migration partially succeeds and then fails (disk full, sqlite error mid-file), partial DDL persists but `INSERT INTO schema_migrations` is never reached. Next launch re-runs the file and `ALTER TABLE ... ADD COLUMN` aborts with "duplicate column." Migration `0002_stable_identity_and_asset_metadata.sql` is exactly this shape (16 ALTERs + 2 CREATEs + 4 INSERTs).
**Where:** `app/db/migrations.py:40-70`.
**Do:**
1. Rewrite the runner to: read SQL file → `conn.execute("BEGIN")` → split statements (or run each statement individually on a cursor) → `INSERT INTO schema_migrations` → `COMMIT`. On exception, `ROLLBACK`.
2. Add a docstring asserting that migration `.sql` files MUST NOT contain their own `BEGIN`/`COMMIT`.
3. Add a test that simulates mid-migration failure and asserts the DB is unchanged + version not bumped.

### W0.6 — Open content.db read-only at runtime
**Severity:** Critical (data integrity)
**Source:** Data Layer audit
**Effort:** XS
**Why:** `open_content_db` does `sqlite3.connect(str(db_path))` with no `mode=ro` (`app/bootstrap.py:60-65`). The runtime app could mutate `content.db` by accident — a stray UPDATE in a future repo function, a buggy migration. The integrity guarantee that user progress isn't orphaned partly relies on `content.db` being immutable between updater swaps. CLAUDE.md claims "Read-only at runtime" but this is not enforced.
**Where:** `app/bootstrap.py`.
**Do:**
1. After migrations + backfill complete, close the writable connection.
2. Reopen with `sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)` for runtime use.
3. The updater already gets its own writable connection during finalize — runtime never needs write.
4. Add an integration test that asserts a write attempt on the runtime content connection raises `sqlite3.OperationalError`.

### W0.7 — Make `reconcile_after_content_update` transactional
**Severity:** Critical (data integrity)
**Source:** Architecture audit
**Effort:** S
**Why:** `AppService.reconcile_after_content_update` (`app/services/app_service.py:159-258`) is ~100 lines that bypasses the documented pure `domain.reconciliation.reconcile()` function entirely, runs raw SQL inline in a loop, and has no rollback semantics. The `with self._conn_userstate:` block at line 177 is Python's auto-commit/rollback context manager — but the inner repo functions call `conn.execute` without using the `app/db/connection.py:transaction` helper. Any failure mid-loop leaves userstate.db half-reconciled, and `clear_undo_redo()` is then called in `main_window.py:271` so the user has no recovery path.
**Where:** `app/services/app_service.py:159-258`, `app/db/connection.py`.
**Do:**
1. Wrap the entire body in `with transaction(self._conn_userstate):` from `app/db/connection.py`.
2. Better still, refactor to call the pure `domain/reconciliation.reconcile()` and apply the delta in a single atomic block — this is what the spec describes and what `ReconciliationResult` was meant for.
3. Add an integration test that simulates a failure halfway through reconciliation and asserts no partial mutation persists.

### W0.8 — Fix `settings_repo.set_value` committing inside
**Severity:** Critical (transaction composability — flagged independently by Architecture *and* Data Layer audits)
**Source:** Architecture + Data Layer
**Effort:** XS
**Why:** `app/repositories/settings_repo.py:13-19` calls `conn.commit()` itself. Every other repo (target_repo, monster_repo) correctly leaves commit to the caller. If a future Command wraps multiple settings changes in `with transaction(conn)`, the inner commit completes the outer transaction prematurely. A latent landmine.
**Where:** `app/repositories/settings_repo.py`.
**Do:**
1. Delete the `conn.commit()` line.
2. Audit current callers of `set_value` and ensure each is wrapped in either `with transaction(conn)` or a Command's transaction.
3. Add a unit test that calls `set_value` without a wrapping transaction and asserts the value is *not* persisted (proves the commit was actually removed).

### W0.9 — Add AC-R03 and AC-R06 acceptance tests (or correct CLAUDE.md)
**Severity:** Critical (spec-coverage gap)
**Source:** Test Suite audit
**Effort:** S
**Why:** CLAUDE.md says acceptance tests "map directly to SRS acceptance criteria AC-R01 through AC-R06," but `tests/unit/test_acceptance.py` only covers R01, R02, R04, R05. R03 and R06 have no test classes.
**Where:** `tests/unit/test_acceptance.py`, `docs/MSM_Awakening_Tracker_SRS_v1_1.md`.
**Do:**
1. Read the SRS for AC-R03 and AC-R06.
2. If the criteria are still in scope, add `TestAC_R03_*` and `TestAC_R06_*` classes that exercise them at the domain level (matching the existing pattern with `_derive` helpers, not via UI).
3. If they're out of scope, edit CLAUDE.md to reflect the actual covered range.

---

## Phase 1 — Reproducibility & Trust Chain
**Goal:** Make builds, manifests, and content artifacts byte-reproducible. Tighten the trust chain beyond the manifest signature.

### W1.1 — Pin requirements + add lockfile + pip-audit
**Severity:** High
**Source:** Updater audit
**Effort:** S
**Why:** `requirements.txt` uses `>=` ranges with no upper bound or hash pinning. CI cache hits against unpinned files don't guarantee identical deps. A typosquatted/compromised release of any direct or transitive dep ships into the EXE.
**Where:** `requirements.txt`, `.github/workflows/`, possibly `pyproject.toml`.
**Do:**
1. Run `pip-compile --generate-hashes` from a clean environment to produce `requirements.lock`.
2. Pin the top-level `requirements.txt` to exact versions (`==`).
3. Add `pip-audit` step to `.github/workflows/ci.yml`.
4. Enable Dependabot in `.github/dependabot.yml`.
5. Update build instructions to install from the lock.

### W1.2 — Split runtime / dev / pipeline dependencies
**Severity:** Medium
**Source:** Doc audit
**Effort:** XS
**Why:** End users running `pip install -r requirements.txt` install `PyYAML` (used only by `pipeline/curation/overrides.py`) and unused `jsonschema`. Maintainer-only deps inflate user install size and attack surface.
**Where:** `requirements.txt`, new `requirements-dev.txt`, `requirements-pipeline.txt`.
**Do:**
1. Inventory imports in `app/`, `pipeline/`, `scripts/`, `tests/`.
2. Move `PyYAML` to `requirements-pipeline.txt`.
3. Remove `jsonschema` (audit confirms it's unused; if you want it, wire it into `pipeline/schemas/normalized.py`).
4. Move `pytest`, `pytest-qt` to `requirements-dev.txt`.
5. Update README to reflect.

### W1.3 — Add environment protection to release workflows
**Severity:** High
**Source:** Updater audit
**Effort:** XS
**Why:** Both `.github/workflows/publish-content.yml` and `release.yml` run on `workflow_dispatch` with `contents: write` and no required reviewer. A successful PR-injected workflow change can publish hostile content.
**Where:** `.github/workflows/publish-content.yml`, `.github/workflows/release.yml`.
**Do:**
1. Create a GitHub `production` environment with required reviewer = self.
2. Add `environment: production` to the publish job.
3. Same for the release job.
4. Lock down `permissions:` to least-privilege (only `contents: write` for the steps that need it).

### W1.4 — Make manifest reproducible (drop timestamps from output)
**Severity:** High
**Source:** Content Pipeline audit
**Effort:** XS
**Why:** `pipeline/publish/artifacts.py:50` writes `"published_at_utc": datetime.now(...).isoformat()` and `_build_id()` (`scripts/publish_content.py:84`) embeds a timestamp into `generated_by_build_id`. Identical inputs → different manifests.
**Where:** `pipeline/publish/artifacts.py`, `scripts/publish_content.py`.
**Do:**
1. Accept `--published-at` and `--build-id` CLI overrides on `publish_content.py`.
2. Default `published_at_utc` to the git commit time of HEAD when not provided.
3. Default `build_id` to the short git SHA when not provided.
4. Add a CI test: run publish twice, diff the manifests, expect zero diff.

### W1.5 — Verify content.db is byte-deterministic
**Severity:** High
**Source:** Content Pipeline audit
**Effort:** S
**Why:** `pipeline/build/db_builder.py` does not pin `application_id`, `page_size`, or `VACUUM` before the publisher hashes the DB. Two clean builds from the same JSON could differ in physical layout.
**Where:** `pipeline/build/db_builder.py`.
**Do:**
1. Set `PRAGMA application_id = <fixed magic>` and `PRAGMA page_size = 4096` at DB open.
2. After all inserts, run `VACUUM` and `PRAGMA wal_checkpoint(TRUNCATE)` to drop free pages.
3. Add a test that builds twice, computes SHA-256 on both, asserts equal.
4. If still not deterministic, document why (e.g., random page ordering during INSERT — fix by sorting input rows).

### W1.6 — Make `verify_bundle.py` actually verify the bundle
**Severity:** High
**Source:** Updater audit
**Effort:** S
**Why:** Despite the docstring's claim "must exit 0 before tagging a release," the script only inspects `resources/db/content.db` and asset paths in the source tree (`scripts/verify_bundle.py:24-117`). It never opens `dist/MSMAwakeningTracker/`, never runs the EXE, never checks for hidden-import failures.
**Where:** `scripts/verify_bundle.py`.
**Do:**
1. Add a step that asserts `dist/MSMAwakeningTracker/MSMAwakeningTracker.exe` exists.
2. Assert minimum file size (e.g., 30 MB lower bound).
3. Assert key DLLs are present (`Qt6Core.dll`, `Qt6Widgets.dll`, etc.).
4. Add a `--self-test` flag to `main.py` that constructs `AppContext`, exits 0, and have `verify_bundle.py` invoke the EXE with that flag with a 30s timeout.

### W1.7 — Restore reliable rollback (atomic backup + state marker)
**Severity:** High
**Source:** Updater audit
**Effort:** S
**Why:** `update_service.py:233-263` does `shutil.copy2(current, backup)` *then* `os.replace(staging, current)`. If the process is killed between `copy2` finishing and `os.replace` starting, state is fine. But if `copy2` partially writes the backup and crashes, the next launch finds a corrupt backup with no integrity check. Also no `fsync` — sudden power loss can leave both files partially flushed.
**Where:** `app/updater/update_service.py`.
**Do:**
1. Write the backup to `content_backup.db.tmp`, fsync, then `os.replace` to `content_backup.db`.
2. Verify the backup with `validate_content_db` before proceeding.
3. Write a `.update_state` marker file with the current step before each phase.
4. On bootstrap, read the marker and recover (if present, finish or roll back).
5. Fsync the directory after each rename.

### W1.8 — Reject downgrade attacks in updater
**Severity:** Medium
**Source:** Updater audit
**Effort:** XS
**Why:** `do_check` only checks `remote_version != self._current_version` (`update_service.py:110`). A poisoned manifest with an older version still triggers an "update" — combined with the manifest-trust hole, lets an attacker roll users back to a known-buggy DB.
**Where:** `app/updater/update_service.py`, `app/updater/validator.py`.
**Do:**
1. Use `packaging.version.Version` to parse both sides.
2. Require `Version(remote) > Version(current)` to trigger an update offer.
3. Add `packaging` to `requirements.txt` (currently bypass-imported with a fragile fallback).
4. Tests for `1.0.0`→`1.0.0`, `1.1.0`→`1.0.0`, `1.0.0-rc1`→`1.0.0-rc2`.

### W1.9 — Enforce `content_db_size_bytes` as streaming download cap
**Severity:** High
**Source:** Updater audit
**Effort:** XS
**Why:** `resp.read()` slurps the entire body into memory (`update_service.py:138-139`) with no max size or `Content-Length` check. A 10 GB manifest target fills memory and crashes.
**Where:** `app/updater/update_service.py`.
**Do:**
1. Stream the response in 64 KB chunks to a temp file.
2. Abort if cumulative bytes exceed `content_db_size_bytes × 1.05`.
3. Reject if `Content-Length` header is absent or wildly off from manifest size.

---

## Phase 2 — Documentation & Onboarding Drift
**Goal:** Bring `CLAUDE.md`, `AGENTS.md`, README, and `RELEASE_CHECKLIST.md` back in sync with reality. Add the missing onboarding files.

### W2.1 — Fix CLAUDE.md and AGENTS.md test count + `--debug` claim
**Severity:** High
**Source:** Doc + Test Suite audits
**Effort:** XS
**Why:** Both files claim 359 tests; actual is 414. CLAUDE.md mentions `python main.py --debug` but `main.py` has no argparse. AI assistants quote these claims.
**Where:** `CLAUDE.md:23,26`, `AGENTS.md:22,25`, possibly `main.py`.
**Do:**
1. Update test count to "400+" (avoid exact number that drifts) or remove the parenthetical entirely.
2. Either implement `--debug` parsing in `main.py` (one `argparse` call, set log level), or remove the line.
3. Same edits to `AGENTS.md`.

### W2.2 — Fix stale "no installer wrapper" claim
**Severity:** High
**Source:** Doc audit
**Effort:** XS
**Why:** README:258 and `RELEASE_CHECKLIST.md:68` both say no installer exists, but `installer/msm_tracker.iss` is committed.
**Where:** `README.md`, `RELEASE_CHECKLIST.md`.
**Do:** Replace both passages with the actual status (Inno Setup script exists; reference it; describe the per-user install).

### W2.3 — Update `RELEASE_CHECKLIST.md` content counts
**Severity:** High
**Source:** Doc audit
**Effort:** XS
**Why:** Claim is ≥39 monsters / ≥38 eggs; actual is 64 / 76. Either drop the count or auto-derive it from `pipeline/normalized/version.txt` + a count query.
**Do:** Add a script `scripts/release_status.py` that prints current counts, or update the numbers and add a comment "regenerated from current content.db on YYYY-MM-DD."

### W2.4 — Add `CONTRIBUTING.md`
**Severity:** High
**Source:** Doc audit
**Effort:** S
**Why:** Onboarding-friendly was a stated goal. Coding style, branch flow, how to run pipeline scripts safely, and review-queue protocol live across multiple files.
**Do:** Single file at root covering: setup, running tests, commit conventions, branch flow, review-queue workflow, pipeline safety, where to ask.

### W2.5 — Add `CHANGELOG.md`
**Severity:** High
**Source:** Doc audit
**Effort:** XS
**Why:** Desktop app with in-app updater; users deserve a change history. Currently only git tags exist.
**Do:** Adopt Keep-A-Changelog format; backfill from recent tags; tie release workflow to bump it.

### W2.6 — Consolidate AGENTS.md and CLAUDE.md
**Severity:** Medium
**Source:** Doc audit
**Effort:** XS
**Why:** ~95% identical. Drift inevitable.
**Do:** Pick one as canonical (CLAUDE.md). Replace the other with a stub: `# Codex / OpenAI agents — see CLAUDE.md` plus any tool-mapping notes specific to that platform.

### W2.7 — Add `pyproject.toml` with `python_requires` and tool config
**Severity:** Medium
**Source:** Doc audit
**Effort:** S
**Why:** Python version requirement ("3.10+" per README:271) is prose-only and not enforced. CI uses 3.11; README says 3.10+. No formatter/linter config.
**Do:**
1. Add `pyproject.toml` with `[project] requires-python = ">=3.11"` (match CI).
2. Add `[tool.ruff]` config with sensible defaults.
3. Add `[tool.pytest.ini_options]` with `qt_api = "pyside6"` and `testpaths = ["tests"]`.
4. Optionally add `pre-commit` config.

### W2.8 — Add `.editorconfig`
**Severity:** Low
**Source:** Doc audit
**Effort:** XS
**Do:** Standard 4-space indent for Python, LF line endings, UTF-8.

### W2.9 — Public method docstrings on `AppService`, commands, repos
**Severity:** Low
**Source:** Doc audit
**Effort:** S
**Why:** Modules have top-level docstrings (44/53 in `app/`) but methods don't. Type hints are excellent throughout, so this is polish.
**Do:** One- or two-line docstrings on each public method describing intent, not mechanics.

---

## Phase 3 — Schema, Identity, and Data Layer Hardening

### W3.1 — Enforce `content_key` uniqueness and non-emptiness
**Severity:** High
**Source:** Data Layer audit
**Effort:** S
**Why:** `content_key` is `NOT NULL DEFAULT ''` — "missing" is indistinguishable from "valid empty." No UNIQUE constraint. Two monsters with the same name and `monster_type` would collide silently and `fetch_monster_by_key` would resolve user state to the wrong monster after a content rebuild.
**Where:** New migration `app/db/migrations/content/0004_content_key_uniqueness.sql`.
**Do:**
1. Author migration that adds `CREATE UNIQUE INDEX uq_monsters_content_key ON monsters(content_key) WHERE content_key != ''` and same for `egg_types`.
2. Add a CHECK constraint or trigger requiring non-empty.
3. Add tests that insert duplicates and assert they fail.

### W3.2 — Short-circuit launch-time backfill
**Severity:** High
**Source:** Data Layer audit
**Effort:** XS
**Why:** `bootstrap.py:178-266` runs full-table `SELECT … WHERE content_key = ''` queries on every launch even when no rows are empty (4 unnecessary scans on every cold start). After migration 0002 ran once, the work is pure waste.
**Where:** `app/bootstrap.py`.
**Do:**
1. Gate backfill on `migrations_applied > 0` returned from `run_migrations`.
2. Or: short-circuit by counting empty rows first (`SELECT 1 FROM monsters WHERE content_key='' LIMIT 1`).
3. Remove the no-op `UPDATE monsters SET source_fingerprint = '' WHERE source_fingerprint = ''` (line 202-204).
4. Remove dead `_seed_userstate_defaults` (the same INSERT OR IGNORE happens in migration 0001).

### W3.3 — Validate migration filenames + version uniqueness
**Severity:** Medium
**Source:** Data Layer audit
**Effort:** XS
**Where:** `app/db/migrations.py:49-51`.
**Do:**
1. Glob with `[0-9][0-9][0-9][0-9]_*.sql`.
2. Assert version uniqueness before applying (raise on duplicate prefix).
3. Tests for both error paths.

### W3.4 — Use `packaging.version` for bundle/installed comparison
**Severity:** High
**Source:** Data Layer audit
**Effort:** XS
**Why:** `_init_content_db` parses dotted versions with `int()` per segment; fails open on `1.1.1-rc2` or `1.1.1+build`. Could let an older bundled version win because the newer one fails to parse.
**Where:** `app/bootstrap.py:81-121`.
**Do:** Use `packaging.version.Version`. Log when neither side parses. Add `packaging` to runtime deps.

### W3.5 — Connection lifecycle on shutdown
**Severity:** Medium
**Source:** Data Layer audit
**Effort:** XS
**Why:** Connections opened in `bootstrap()` are never explicitly closed. WAL mode means orphaned `-wal`/`-shm` sidecars can linger if the OS kills the process. Updater's finalize closes/reopens, but normal exit doesn't.
**Where:** `app/bootstrap.py`, `main.py`.
**Do:**
1. Add a `close_all` method to `AppContext`.
2. Call it from `app.aboutToQuit` in `main.py`.
3. Add `BEGIN IMMEDIATE` to `transaction()` for write paths to surface lock conflicts earlier.

### W3.6 — Switch repository row access to `sqlite3.Row` (named columns)
**Severity:** Medium
**Source:** Architecture + Data Layer audits
**Effort:** S
**Why:** `_monster_from_row` and `_egg_type_from_row` (`monster_repo.py:11-12, 112-148`) use hand-counted v2 column constants and `row[7] if has_v2 else ""` ladders. A column reorder silently breaks. Also: `repositories/base.py` mutates `conn.row_factory` then resets to `None` — racy and currently unused.
**Where:** `app/repositories/monster_repo.py`, `app/repositories/base.py`.
**Do:**
1. Use a per-call cursor with `cursor.row_factory = sqlite3.Row` instead of mutating connection-level factory.
2. Read `row["content_key"]`, etc. — schema-tolerant via `if "content_key" in row.keys()`.
3. Delete unused `fetchone_dict`/`fetchall_dicts` helpers in `base.py`.
4. Drop the `_MONSTER_V2_COLS = 13` magic constant.

### W3.7 — Replace f-string `PRAGMA table_info({table})` in bootstrap
**Severity:** Medium
**Source:** Architecture audit
**Effort:** XS
**Where:** `app/bootstrap.py:173-175`.
**Do:** `conn.execute("SELECT name FROM pragma_table_info(?)", (table,))`. Drop the `# noqa: S608`.

### W3.8 — Document cross-DB FK omissions
**Severity:** Low
**Source:** Data Layer audit
**Effort:** XS
**Where:** `app/db/migrations/userstate/0001_initial_schema.sql`.
**Do:** Add `-- intentionally no FK: refs content.db cross-DB` comments next to `monster_id` and `egg_type_id`.

---

## Phase 4 — Test Suite Plumbing

### W4.1 — Add `pyproject.toml` `[tool.pytest.ini_options]`
**Severity:** Medium
**Source:** Test Suite audit
**Effort:** XS
**Where:** `pyproject.toml` (see W2.7).
**Do:** Set `qt_api = "pyside6"`, `testpaths = ["tests"]`, warning filters, and any markers used.

### W4.2 — Smoke tests for under-covered UI panels
**Severity:** High
**Source:** Test Suite audit
**Effort:** S
**Where:** `tests/unit/test_gui_smoke.py` or new files.
**Do:** Construction + empty/non-empty refresh smoke tests for `home_view.py`, `catalog_active_panel.py`, `_active_sections.py`. Plus a navigation test on `main_window.py` that switches between Home/Catalog/Settings and asserts the active page.

### W4.3 — Replace fragile `urlopen` monkey-patch with `monkeypatch`
**Severity:** High
**Source:** Test Suite audit
**Effort:** XS
**Where:** `tests/unit/test_updater.py:259-278`.
**Do:** `monkeypatch.setattr("urllib.request.urlopen", _FakeResponse)` — pytest restores automatically.

### W4.4 — Test cleanups
**Severity:** Medium
**Source:** Test Suite audit
**Effort:** XS
**Do:**
1. `test_frozen` in `test_settings_viewmodel.py:117` → use `pytest.raises(AttributeError)` instead of try/`assert False`.
2. Remove unused imports in `test_gui_smoke.py:12-14`.
3. Remove unused `breed_panel` fixture from `test_undo_reverts_add` and `test_redo_restores_add`.
4. `test_verify_bundle.py:16,40` — use `monkeypatch.syspath_prepend` instead of mutating `sys.path` globally.

### W4.5 — Test for migration mid-failure (validates W0.5)
**Severity:** Medium
**Source:** Data Layer audit (cross-domain)
**Effort:** XS
**Do:** Integration test that runs a migration with an injected failure on statement N and asserts: (a) the DB is unchanged from pre-migration state, (b) `schema_migrations` does not record the version, (c) re-running the migration succeeds cleanly.

### W4.6 — Test for backfill no-op (validates W3.2)
**Severity:** Low
**Effort:** XS
**Do:** Test that backfill on an already-populated DB performs zero UPDATEs.

---

## Phase 5 — UI Performance and Rendering Quality

### W5.1 — Diff-style refresh for `InWorkPanel` and `CatalogActivePanel`
**Severity:** High
**Source:** UI audit
**Effort:** M
**Why:** Every `state_changed` rebuilds the entire active rail by calling `SectionCard.refresh` which `deleteLater()`s every `MonsterEntryRow` and rebuilds them. With many active monsters, every egg-click rebuilds the home + catalog rails twice.
**Where:** `app/ui/widgets/section_card.py:94-128`, `app/ui/inwork_panel.py:93-107`, `app/ui/catalog_active_panel.py:90-104`.
**Do:** Adopt the diff pattern that `BreedListPanel.refresh` already uses — reuse rows by id, only insert/remove deltas. Also: only re-render the catalog tab when the catalog page is currently shown.

### W5.2 — Debounce catalog grid resize
**Severity:** High
**Source:** UI audit
**Effort:** S
**Where:** `app/ui/catalog_browser_panel.py:209-214`.
**Do:** Re-flow existing card widgets across the grid (`removeWidget`/`addWidget`) instead of destroy/recreate, OR debounce with `QTimer.singleShot(50, …)` to coalesce rapid resize ticks.

### W5.3 — Add QPixmap cache
**Severity:** High
**Source:** UI audit
**Effort:** S
**Where:** `app/assets/resolver.py` (new wrapper) and 8 widget call sites.
**Do:** Wrap `QPixmap(path)` lookups via `QPixmapCache.find/insert` keyed on resolved absolute path + size variant. Update all 8 call sites listed in the UI audit.

### W5.4 — Hi-DPI configuration
**Severity:** High
**Source:** UI audit
**Effort:** S
**Where:** `main.py:10-22`, widgets using `setScaledContents(True)`.
**Do:** Set rounding policy to `PassThrough`. Load pixmaps at `devicePixelRatio()` resolution (`pix.setDevicePixelRatio(...)`). Prefer `pix.scaled(..., SmoothTransformation)` over `setScaledContents(True)`.

### W5.5 — Move placeholder tones from inline stylesheets to central QSS
**Severity:** Medium
**Source:** UI audit
**Effort:** S
**Where:** Five widgets listed in UI audit.
**Do:** Use `setProperty("monster_type", ...)` + `unpolish/polish` for theme switching; centralize tone tokens in `themes.py`.

### W5.6 — Toast-based error display
**Severity:** Medium
**Source:** UI audit
**Effort:** S
**Where:** `app/ui/main_window.py:213-214`, `ToastWidget`.
**Do:** Reuse `ToastWidget` with a `tone` property for non-fatal command errors. Reserve modal `QMessageBox` for unrecoverable cases (e.g., update failure).

### W5.7 — Delete dead UI code
**Severity:** Medium
**Source:** UI audit
**Effort:** XS
**Where:** `app/ui/catalog_panel.py` (dead module), `app/ui/main_window.py:7` (dead `import sqlite3`).
**Do:** Delete the file and the import. Run tests to confirm nothing referenced them.

### W5.8 — Retain QShortcut references and other small fixes
**Severity:** Low
**Source:** UI audit
**Effort:** XS
**Where:** `app/ui/main_window.py:136-138`, settings table refresh hot loop, `ToastWidget._fade_out`.
**Do:** Bind shortcuts to `self._sc_undo` etc. Hoist `QColor` / theme imports out of the settings-table loop. Stop prior animation in `ToastWidget._fade_out` before starting a new one.

### W5.9 — Make ViewModels genuinely immutable
**Severity:** Low
**Source:** UI audit
**Effort:** XS
**Where:** `app/ui/viewmodels.py:68-73`.
**Do:** Use `tuple` and `Mapping[str, ...]` (or `MappingProxyType`) for collection fields on frozen dataclasses.

---

## Phase 6 — Architecture Polish

### W6.1 — Move ViewModels out of `app/ui/`
**Severity:** Medium
**Source:** Architecture audit
**Effort:** S
**Why:** `app/services/app_service.py` imports from `app.ui.viewmodels` (defensible — they're plain dataclasses) AND from `app.ui.themes` at line 313 (a real layering violation: a service reaching into UI runtime concerns).
**Where:** `app/ui/viewmodels.py` → `app/services/viewmodels.py` (or `app/domain/viewmodels.py`).
**Do:**
1. Move the file. Update all imports.
2. Delete the `from app.ui.themes import get_active_font_offset` at `app_service.py:313` — pass current theme/font as method args from `main_window` instead.

### W6.2 — Typed exception hierarchy
**Severity:** High
**Source:** Architecture audit
**Effort:** S
**Why:** `AppService.execute_command` (`app_service.py:55-72`) catches `Exception`, logs, and emits `str(exc)`. A `RuntimeError("Monster N not found or deprecated")` looks the same to the UI as a `sqlite3.OperationalError`. No taxonomy.
**Where:** `app/domain/errors.py` (new), `app/commands/`, `app/services/app_service.py`.
**Do:**
1. Define `DomainError`, `IntegrityError`, `ContentMismatchError`, `NotFoundError` in `app/domain/errors.py`.
2. Have commands raise typed errors (e.g., `add_target.py:34` raises `NotFoundError`).
3. UI displays the `__class__.__name__` and message distinctly.
4. Reserve bare `except Exception` for unexpected failures.

### W6.3 — Replace `getattr`-based completion-event signaling
**Severity:** High
**Source:** Architecture audit
**Effort:** XS
**Where:** `app/services/app_service.py:66-69, 101-104`, `app/commands/base.py:8-13`.
**Do:** Add `def completion_egg(self) -> int | None: return None` (or `Optional[CompletionEvent]`) on the `Command` base. Override in `IncrementEggCommand`. Drop the `getattr` calls.

### W6.4 — Implement or remove `ReconciliationResult`
**Severity:** High
**Source:** Architecture audit
**Effort:** XS (delete) or S (implement)
**Where:** `app/domain/models.py:134-140`, `app/domain/reconciliation.py:15-28`.
**Do:** Decide: delete the dataclass (TDD spec drift — fine if reconcile is what it is), or have `reconcile()` return `ReconciliationResult` and have callers (including the new transactional `reconcile_after_content_update` from W0.7) consume it.

### W6.5 — Hoist lazy command imports
**Severity:** Medium
**Source:** Architecture audit
**Effort:** XS
**Where:** `app/services/app_service.py:111, 127, 141`.
**Do:** Move all three imports to module-level. There is no circular dependency to dodge — verified by the audit.

### W6.6 — Misc architecture polish
**Severity:** Low
**Source:** Architecture audit
**Effort:** XS each
**Do:**
- `target_repo.insert_target` — drop `# type: ignore` and either assert non-None or change return to `int | None`.
- `breed_list._sort_key` (lines 57-66) — replace lambda chain with dispatch dict.
- `audio_player.py:42-49` — narrow the `try/except Exception` around `QMediaPlayer()`.
- `view_model_builder.build_consumer_cards` — cache monsters map alongside requirements at `AppService.__init__` to avoid N round-trips.
- `AppService.handle_close_out` — log at debug level when no target is found.

---

## Phase 7 — Pipeline Robustness

### W7.1 — Wire collection-level validators into publish
**Severity:** High
**Source:** Content Pipeline audit
**Effort:** XS
**Where:** `scripts/publish_content.py`, `pipeline/schemas/normalized.py:209-221`.
**Why:** The `validate_monsters_file/eggs_file/requirements_file` validators (which check duplicate keys + cross-table refs on the JSON side) only run inside `pipeline/export_baseline.py`. A handcrafted `requirements.json` with a typo egg_key is not caught at publish until the SQL FK builder logs a warning and skips the row.
**Do:** Call those validators as step 2 of `publish_content.py`, before `db_builder.build`.

### W7.2 — Drop or repurpose dead 200-line literal data in `seed_content_db.py`
**Severity:** High
**Source:** Content Pipeline audit
**Effort:** XS
**Where:** `scripts/seed_content_db.py:28-260`.
**Do:** Hard-fail with a clear message if `pipeline/normalized/*.json` is missing. Delete the literal fallback (it drifts).

### W7.3 — Implement real baseline diff in `publish_content.py`
**Severity:** High
**Source:** Content Pipeline audit
**Effort:** S
**Where:** `scripts/publish_content.py:182-196`.
**Why:** Even when `--baseline-db` is passed, `baseline_monsters/eggs/requirements/assets` are hard-coded `[]`. Every publish reports everything as "new." The diff engine code is correct; the script never feeds it.
**Do:** Read records from the baseline DB into the same shape the diff engine expects.

### W7.4 — Wiki ingestion: assert non-empty requirements
**Severity:** High
**Source:** Content Pipeline audit
**Effort:** XS
**Where:** `pipeline/raw/wiki_fetcher.py:248-289, 540`.
**Why:** Regex-on-HTML can silently fail if the wiki template changes; current `source_payload_incomplete` review item is non-blocking, so `--approve-all` ships content with missing requirements.
**Do:** Make zero-requirements blocking. Add a baseline-min check (e.g., require ≥ N requirements unless explicitly overridden).

### W7.5 — `SourceCache` atomic writes
**Severity:** Medium
**Source:** Content Pipeline audit
**Effort:** XS
**Where:** `pipeline/raw/source_cache.py:46-77`.
**Do:** Write payload + index via `tempfile + os.replace` to survive Ctrl-C.

### W7.6 — Path traversal containment in `generate_assets.py`
**Severity:** Medium
**Source:** Content Pipeline audit
**Effort:** XS
**Where:** `scripts/generate_assets.py:99-100`.
**Do:** `Path(RESOURCES / rel_path).resolve().relative_to(RESOURCES.resolve())` — raise on escape.

### W7.7 — Version monotonicity check at publish
**Severity:** Medium
**Source:** Content Pipeline audit
**Effort:** XS
**Where:** `scripts/publish_content.py`, `pipeline/version.py`.
**Do:** Refuse publish if `--content-version ≤` current `content/manifest.json:content_version`.

### W7.8 — Tighten Fan Kit license metadata
**Severity:** Medium
**Source:** Content Pipeline audit
**Effort:** S
**Where:** `scripts/import_fankit_images.py:212-214`.
**Why:** Currently any file ≥ 501 bytes gets `license_basis = "bbb_fan_kit_policy"`. Maintainer error or accidental drop-in gets relabelled official.
**Do:** Require image-format check (Pillow) and either a hash-match against an expected manifest or a known-good source path.

### W7.9 — Audit-trail fields on review-queue approvals
**Severity:** Low
**Source:** Content Pipeline audit
**Effort:** XS
**Where:** `scripts/review_content.py:79-87`, `pipeline/schemas/normalized.py:218-220`.
**Do:** Schema currently requires `approved_by`/`timestamp` only on `resolved` items. Extend to `approved` items. Populate from environment / argv.

---

## Phase 8 — Low-Priority Polish (when convenient)

These are listed in the per-domain summaries (Appendix). None block anything; pick up opportunistically.

---

## Suggested execution order (dependency map)

```
W0.1, W0.2 (legal)         ── independent, do first
W0.5, W0.6, W0.7, W0.8 (data/transactions)  ── do as a group, share migration testing
W0.3, W0.4, W0.9 (security/spec) ── independent

W1.1 → W2.7 (lockfile then pyproject)
W1.4 → W1.5 → W2.3 (manifest determinism then bundle verify then RELEASE_CHECKLIST)
W1.6 → W1.7 → W1.8 → W1.9 (updater hardening, build on each other)

W3.* are mostly independent; W3.1 should follow W0.5 (atomic migrations) so the new migration is safe.

W4.1 enables W4.2..W4.6.

W5.1..W5.4 can run in parallel; W5.5..W5.9 are polish.

W6.1 enables cleaner W6.2..W6.6.

W7.1..W7.4 should land before next content publish.
```

A focused engineer doing this part-time can clear Phase 0 in ~1 week, Phases 1–2 in ~1–2 weeks, Phases 3–4 in ~1 week, Phase 5 in ~1 week, Phases 6–7 in ~1 week. ~5–7 weeks total. Phases 0–2 capture nearly all of the "scary" risk.

---

## Appendix: Per-domain audit summaries

The 7 raw audit reports — including the "Strengths" sections that prove what's already working well — were preserved verbatim from the agents. Key files of interest are referenced inline above. Recommend keeping this document under version control so future audits can diff against the current baseline.
