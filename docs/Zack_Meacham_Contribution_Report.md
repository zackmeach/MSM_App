# MSM Awakening Tracker — Resume Extract

**Zack Meacham** · Solo author, end-to-end · Windows desktop application (Python + PySide6)

The MSM Awakening Tracker is a Windows desktop companion app for *My Singing Monsters* that helps players track egg requirements for awakening Wublins, Celestials, and Amber Vessels. Built solo from greenfield to six tagged releases, it spans a strictly-layered PySide6/Qt runtime, a two-database SQLite design with a stable-identity scheme that survives content rebuilds, a secure in-app auto-updater, an offline ETL content pipeline, a self-publishing GitHub Actions CI/CD chain, and a 472-test suite. The work demonstrates not just feature delivery but production-grade reliability engineering: atomic database swaps, threat-model-driven security hardening, reproducible builds, and a deliberate over-engineering audit — every release shipped through a feature-branch + pull-request workflow.

> Sourced from the git history of `C:\MSM_App` through v1.0.2 (June 2026): 103 commits, 15 merged PRs, 6 tagged releases. Test/module/dependency counts verified against the working tree.

---

## Technologies & Skills

**Languages**
- Python 3.10+ (dataclasses, `Enum`, ABCs/`abstractmethod`, `contextlib` context managers, `from __future__` annotations)
- SQL (SQLite dialect: WAL journaling, PRAGMA tuning, partial unique indexes, URI read-only connections)
- JSON Schema (draft-07), YAML

**Frameworks & Libraries**
- PySide6 / Qt 6 (QObject, Signals/Slots, QThread, QPropertyAnimation, QMediaPlayer / QAudioOutput)
- `sqlite3` (stdlib), `hashlib` (SHA-256), `urllib.request` (streaming HTTP)
- `jsonschema`, `PyYAML`, `packaging.version` (with a dependency-free fallback)
- `pytest`, `pytest-qt`, `unittest.mock`, `http.server`
- Pillow (optional asset accelerator), `zlib`/`struct` (hand-rolled PNG/ICO encoders)

**Tooling & Infrastructure**
- PyInstaller 6 (one-folder bundle, `_MEIPASS` detection, hidden-import wiring)
- Inno Setup 6 (per-user Windows installer, fixed AppId, lzma2 compression)
- GitHub Actions (Windows runners, three trigger-segregated workflows)
- Git (feature-branch + PR workflow, Conventional Commits), `ruff`, `requirements.lock` pinning

**Concepts & Practices**
- Layered architecture with a strictly unidirectional dependency graph
- Command pattern with undo/redo; signal-driven state flow; passive ViewModel-driven UI
- Stable-identity slug system decoupling user state from numeric primary keys
- Atomic transactions, atomic file swap with rollback, defense-in-depth integrity checks
- Threat-model-driven security (URL allowlisting, mandatory checksums, bounded downloads)
- ETL pipeline design (normalize → semantic diff → deterministic build → validate → publish)
- Reproducible builds, release gating, acceptance-test traceability to an SRS

---

## Systems & Components Built

### Desktop Application Layer (`app/`)
- Architected a strictly-layered PySide6/Qt runtime — a Qt- and SQLite-free pure-Python **domain** core, function-style **repositories** with dependency-injected connections, an `AppService(QObject)` orchestrator, and a **passive UI** that reads only frozen **ViewModel** dataclasses — yielding a fully unit-testable business layer with a clean dependency arrow (theme state is passed *into* the service rather than the service importing the UI).
- Implemented a **Command pattern** with disciplined undo/redo: each command (`AddTarget`, `CloseOut`, `IncrementEgg`) snapshots its own reversal state (row snapshots, prior counts, original ids), and `AppService` re-pushes a command on a failed undo/redo so the in-memory history can never desync from the database.
- Drove all UI updates through Qt **signal/slot state flow** (commands mutate → service derives state → emits a single `AppStateViewModel` → panels re-render), with dedicated `completion_event`/`error_occurred` signals decoupling side effects from rendering, and **keyed diff rendering** in the breed-list panel that reuses/reorders `EggRowWidget`s by id with animation-aware teardown guards.

### In-App Content Updater (`app/updater/`)
- Built a client-side update subsystem that fetches a remote JSON manifest, **streams** a new SQLite DB in 64 KB chunks under a **64 MB hard ceiling**, and trusts it only after a mandatory **SHA-256** check plus a `PRAGMA integrity_check` and referential-integrity (orphan-row) schema audit.
- Designed an **atomic database swap with automatic rollback**: the live DB is backed up, replaced via `os.replace()` (atomic rename, cross-volume `shutil.move` fallback), and reopened read-only — any failure during the swap *or* the subsequent userstate reconciliation restores the backup, so content and userstate are never left mismatched.
- Hardened the channel against a **poisoned-manifest threat model**: HTTPS-only scheme and host allowlist (`raw.githubusercontent.com`) blocking HTTP-downgrade, `file://` local-read, and attacker-host redirects, gated behind an artifact-contract-version check and a **numeric (non-lexical)** min-client-version comparison (`1.9.0 < 1.10.0`).
- Ran all network I/O on a **fresh per-phase Qt worker thread** (documented rationale: avoids a fragile `QThread`-reuse use-after-free) and guaranteed SQLite connection closure on every path plus WAL/SHM sidecar deletion to avoid Windows file-lock (WinError 32) failures.

### Two-Database & Stable-Identity Layer
- Designed a **two-database SQLite architecture** (read-only `content.db` + read-write `userstate.db`) that enforces content immutability *at runtime* by reopening the DB in SQLite URI `mode=ro`, so accidental writes raise `OperationalError` rather than silently corrupting shipped data.
- Built a **slug-based stable-identity system** (`content_key` like `monster:wublin:zynth`) decoupling user progress from numeric AUTOINCREMENT ids, guarded by **partial unique indexes** (`WHERE content_key != ''`) that enforce uniqueness of populated keys while tolerating pre-backfill placeholders, with an **idempotent backfill** that degrades gracefully (logs and skips) on slug collisions instead of crashing startup.
- Wrote **post-content-update reconciliation** that re-resolves changed numeric ids through stable keys, drops deprecated targets, and rebuilds progress via **delete-then-insert** (avoiding a `(active_target_id, egg_type_id)` primary-key collision that in-place id remaps would cause) inside a single atomic transaction, carrying counts over by stable key and clipping to new requirements via a pure-domain clip rule.
- Implemented an **idempotent, numbered-SQL migration runner** that wraps each migration in an explicit `BEGIN/COMMIT` with rollback — eliminating a class of partial-apply failures (SQLite legacy-autocommit committing statements individually) that would otherwise brick startup with a duplicate-column error.

### Maintainer Content Pipeline (`pipeline/`)
- Designed an offline **ETL pipeline** (ingest → normalize → semantic diff → deterministic build → validate → publish) with a strict one-way boundary keeping pipeline tooling out of the app runtime, driven by a canonical normalized-JSON source of truth and a one-line `version.txt` bump.
- Built a **semantic diff engine** that classifies content changes into a fixed taxonomy (new, rename, deprecated, revived, field_change, requirements_change, plus licensing-sensitive `placeholder_to_official` ↔ `official_to_placeholder` asset transitions) and emits a typed, reviewable release delta.
- Engineered a **deterministic DB builder** that preserves numeric primary keys across full rebuilds via `IntegrityError`-guarded explicit-id inserts keyed on durable `content_key` slugs, plus a **9-gate publish-validation system** (integrity, orphan-FK scans, unique-key, JSON-Schema conformance/completeness, blocking-review gate) with per-check blocking levels producing a machine-readable report.
- Defined a **versioned artifact contract** (manifest + assets/diff/validation reports) stamped with contract version, SHA-256 + byte size, build id, and git SHA — the exact manifest the in-app updater checksum-validates — and a content-addressed (SHA-256-keyed) source cache for reproducible, fully-provenanced rebuilds.

### Build & Release Engineering
- Built a **fail-fast release pipeline** (`build.py`) chaining version injection → pytest → content-DB seed → asset/icon generation → bundle verification → PyInstaller → Inno Setup as checked subprocesses, aborting on the first non-zero exit so no broken artifact can ship.
- Engineered a **build-time bundle-verification gate** (`verify_bundle.py`) that cross-validates the seeded content DB against on-disk assets — every DB-referenced image path must resolve to a real file, zero orphaned join rows, per-type row floors — required to exit 0 before any release tag.
- Authored **zero-dependency stdlib PNG and multi-resolution ICO encoders** (`zlib`/`struct`, correct CRC32 chunking and ICO directory packing) so placeholder/icon generation needs no imaging library, plus a **provenance-aware Fan Kit importer** recording SHA-256, byte size, and license basis per image with idempotent skip/`--force`/`--dry-run` semantics.
- Established **reproducible builds** via two-tier dependency management (dev floors in `requirements.txt`, a fully-pinned 25-package closure in `requirements.lock` with a documented regenerate workflow) and a single-source-of-truth versioning scheme (regex-injected app version + one-file content-version bump).

### CI/CD (GitHub Actions)
- Designed a **three-workflow** pipeline (PR/push test gating, tag-driven release build, on-demand content publishing), each scoped to least-privilege permissions — only release/publish request `contents: write`.
- Automated the full **Windows release pipeline** on `v*` tags: version injection from the git tag, pytest gating (pipeline-only tests pragmatically ignored), PyInstaller freeze, Inno Setup compilation, and GitHub Release publication with auto-generated notes and **automatic prerelease detection** for hyphenated semver.
- Built a **self-publishing content workflow** that validates a review queue, generates SQLite/manifest artifacts, verifies them inline, and commits them back to the repo as a bot identity — wiring CI directly into the app's in-app update channel — and practiced **shift-left validation** by running the content publisher in `--dry-run` on every PR.

### Testing
- Authored a **472-test, 34-module pytest suite** (31 unit, 3 integration) running against **real in-memory SQLite** with production migrations applied — hermetic, never touching `%APPDATA%` — spanning domain logic, repositories, command undo/redo, the pipeline, the updater, and `pytest-qt` GUI smoke coverage.
- Wrote **acceptance tests traceably mapped to formal SRS criteria** (AC-R01..AC-R06) and functional requirements (FR-410, FR-506, FR-507), converting a requirements spec into executable regression guards.
- Hardened the updater with **adversarial tests** (SHA-256 mismatch, scheme/host allowlist rejection of `file://`/`ftp://`/`http://` and subdomain spoofing) and a **live-HTTP end-to-end harness** serving pipeline artifacts over an ephemeral-port `http.server` to exercise the full fetch → download → validate → finalize → rollback loop.
- Proved **transactional atomicity under failure** by forcing partial-migration and mid-reconciliation faults (broken SQL, monkeypatched repo calls in autocommit mode) and asserting byte-identical rollback, and added a **builder-parity guard** keeping the bundled seeder and pipeline builder byte-equivalent.

---

## Engineering Practices Demonstrated

- **Threat-model-driven security, not checkbox security.** Commit bodies name the concrete attack and mitigation — poisoned manifest → attacker host / `file://` disclosure / DNS exfiltration; multi-statement migration → startup brick; `QThread` reuse → use-after-free — demonstrating reasoning over ritual. The v1.0.1 hardening pass made SHA-256 mandatory, enforced the HTTPS + host allowlist, capped streaming downloads, and opened the runtime DB read-only.
- **Reliability engineering as a first-class concern.** Atomic file swaps with rollback, atomic SQL migrations, all-or-nothing reconciliation, and read-only runtime enforcement — the no-orphaning guarantee for user progress is mechanically enforced, not merely documented.
- **Reproducible, gated releases.** Two-tier dependency pinning plus a `verify_bundle.py` gate that must exit 0 before tagging; six tagged releases (3 betas → v1.0.0 → two hardening/maintenance point releases) over ~3 months, each a real git tag with a matching GitHub Release.
- **Deliberate over-engineering audit (PRs #7–13).** A coordinated code-hygiene wave removing dead modules, an unreachable fallback path, no-op `TYPE_CHECKING` guards, a single-choice CLI flag, and tests that asserted nothing — net-negative-LOC cleanup shipped as first-class reviewed PRs.
- **Disciplined solo workflow.** 15 merged PRs each scoped to a single concern, strict Conventional Commits (`fix(updater):`, `refactor(pipeline):`, `chore(ui):`) across 103 commits for a machine-greppable, changelog-ready history; refactor PRs rebased main up before merge to keep integration linear.
- **Verified-results discipline.** Hardening commits report exact test counts (e.g. "66 updater tests pass") rather than a vague "green," and tests land in the same change as the fix (no security fix without a regression guard).
- **Proactive maintenance.** Upgraded pinned GitHub Actions off deprecated Node.js 20 *ahead* of a forced runtime cutover, verifying each action's runtime at its pinned tag and intentionally holding one action back a major version to preserve manual `git push` behavior.

---

## Resume Bullets

### (A) Software / Application Engineer
- Architected and solo-built a layered PySide6/Qt desktop application with a strictly unidirectional dependency graph — a Qt- and SQLite-free pure-Python domain core, function-style repositories with injected connections, and a passive UI reading only immutable ViewModel dataclasses — yielding a fully unit-testable business layer.
- Implemented a Command pattern with robust undo/redo in a signal-emitting `AppService(QObject)`, where each command snapshots its own reversal state and the service re-pushes commands on failed reversal so in-memory history can never desync from the database.
- Drove all UI updates through Qt signal/slot state flow (mutate → derive state → emit a single ViewModel → re-render) with keyed diff rendering and animation-aware teardown guards, keeping zero business logic in the UI layer.
- Designed a two-database SQLite architecture with a slug-based stable-identity system so user progress survives full content-DB rebuilds and numeric primary-key reassignment without orphaning saved state.
- Wrote defensive data-access code (explicit column-mapping contracts instead of `SELECT *`, transactional context managers with rollback, graceful fallbacks for corrupted settings and missing assets) hardening the app against schema drift and partial failure.
- Backed the application with a 472-test pytest suite (unit + integration + `pytest-qt` GUI smoke) running against real in-memory SQLite, with acceptance tests traceably mapped to formal SRS criteria.

### (B) Platform / Reliability / Tools Engineer
- Built a client-side content-update subsystem performing an atomic SQLite database swap (`os.replace()` with cross-volume fallback) backed by automatic rollback, where any failure during the swap or post-swap reconciliation restores a backup so user data is never left corrupted or mismatched.
- Hardened the update channel against a poisoned-manifest threat model with an HTTPS-only scheme + host allowlist, mandatory SHA-256 verification, a `PRAGMA integrity_check` + orphan-row schema audit, and a numeric (non-lexical) min-client-version gate.
- Eliminated a class of startup-bricking failures by making SQLite schema migrations atomic (`BEGIN/COMMIT` with rollback) and rebuilding update reconciliation to preserve stable-identity keys, each fix landing with dedicated regression tests.
- Designed an offline ETL content pipeline (normalize → semantic diff → deterministic build → 9-gate validation → publish) emitting a versioned, checksum-stamped artifact contract that the in-app updater verifies before applying.
- Established reproducible release builds via two-tier dependency pinning (dev floors + a fully pinned lockfile) and a bundle-verification gate that cross-validates the content DB against on-disk assets and must exit 0 before tagging.
- Owned a three-workflow GitHub Actions CI/CD pipeline (least-privilege-scoped test gating, tag-driven release, self-publishing content delivery) and proactively migrated pinned actions off deprecated Node.js 20 ahead of a forced cutover.

### (C) Full-Stack / Product Engineer
- Shipped a Windows desktop product solo from greenfield to six tagged releases over ~3 months, owning everything from the Qt UI and SQLite data layer to the build pipeline, installer, auto-updater, and CI/CD.
- Designed a content delivery system spanning both ends: a maintainer ETL pipeline that builds and publishes a versioned SQLite database, and an in-app updater that fetches, verifies (SHA-256), and atomically swaps it with automatic rollback.
- Built provenance-aware asset tooling that imports official artwork (Pillow LANCZOS resize), validates PNG magic bytes, and records SHA-256 + license basis per image, alongside zero-dependency stdlib PNG/ICO encoders for placeholders and the app icon.
- Packaged and distributed the app end-to-end with PyInstaller (one-folder, embedded icon, explicit hidden imports) and an Inno Setup per-user installer (no-admin install, fixed AppId for clean upgrades), versioned from a single source of truth.
- Ran a disciplined solo engineering process — 15 single-concern PRs, Conventional Commits across 103 commits, a dedicated security-hardening release, and a deliberate over-engineering audit shipping net-negative-LOC cleanup as reviewed work.
- Covered the full product surface (64 monsters / 76 egg types of game content) with a 472-test suite including a live-HTTP end-to-end test of the entire update loop.

---

## Interview Talking Points

- **Runtime read-only enforcement is mechanical, not aspirational.** After migrations and backfill, `content.db` is reopened via SQLite URI `mode=ro` so any stray write raises `OperationalError`. The whole no-orphaning guarantee for user progress rests on content immutability between updater swaps — so I made the invariant fail loudly rather than trusting it to be respected.
- **Why delete-then-insert in reconciliation instead of in-place UPDATE.** `(active_target_id, egg_type_id)` is a primary key; when a content rebuild reuses or swaps egg ids within one target, an in-place remap collides with a sibling row and aborts mid-transaction. Rebuilding progress (carrying satisfied counts over by stable `egg_key`, clipping to new requirements) sidesteps the collision entirely — and there's a deliberately constructed egg-id-swap test proving it.
- **The atomic-migration bug I diagnosed before it could happen.** In SQLite legacy-autocommit mode, `executescript()` commits each statement individually — so a multi-statement migration failing on statement N persists 1..N-1 without recording the version row, bricking the next launch with a duplicate-column error. Wrapping each migration in an explicit `BEGIN/COMMIT` with rollback closes that gap; the docstring names the exact failure mode rather than cargo-culting the transaction.
- **The updater threat model, attack by attack.** A poisoned manifest could force an HTTP downgrade, a `file://` local-file read, or an attacker-controlled host — even though SHA-256 still gates *content*, the URL itself is an attack surface. The fix is a scheme + host allowlist, with the allowlists injectable so tests use a permissive local fixture while production stays locked to `raw.githubusercontent.com`.
- **Fresh QThread per update phase, and why reuse was fragile.** Reusing one worker across phases relied on GC destroying the prior `QThread` before the next `moveToThread()` — a use-after-free waiting to happen. Spawning a fresh worker + thread per phase (with `quit`/`wait`/`deleteLater` cleanup) trades a little ceremony for a race I can reason about.
- **Stable identity is the spine of the whole data design.** `content_key` slugs decouple user progress from volatile AUTOINCREMENT ids; partial unique indexes (`WHERE content_key != ''`) thread the needle between guaranteeing uniqueness of populated keys and tolerating empty placeholders before backfill runs; and the deterministic builder actively preserves numeric ids across rebuilds via `IntegrityError`-guarded explicit-id inserts. Three layers, one invariant.
- **The over-engineering audit as first-class work.** After v1.0.0 I ran a deliberate net-negative-LOC pass: dead modules, an unreachable `KNOWN_MONSTER_TYPES` fallback, no-op `TYPE_CHECKING` guards, a single-choice CLI flag, and tests that asserted pure-Python string comparisons instead of app code. Treating deletion as reviewed, intentional engineering — not cleanup done "while I was in there" — is a maturity signal I'd defend.
