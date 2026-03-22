---
name: A. What was ambiguous in the prior plan
overview: Implementation-ready addendum to the existing content update pipeline plan, freezing artifact schemas, stable identity rules, normalized content records, migration/backfill behavior, manual review workflow, asset policy, validation ownership, and exact phase deliverables.
todos: []
isProject: false
---

# A. What was ambiguous in the prior plan

- The prior plan correctly established the maintainer-pipeline vs desktop-client boundary, but four contract layers were still directional rather than frozen:
  - artifact payload schemas
  - stable identity rules (`content_key` permanence and classification logic)
  - exact maintainer-side normalized record schemas
  - migration/backfill behavior needed to make rebuilt `content.db` safe for existing `userstate.db`
- The prior plan also named operational concepts without freezing them:
  - manual review queue structure
  - curator override file structure
  - source acquisition failure handling
  - exact publish/install blocking rules for placeholder/media issues
- This addendum resolves those ambiguities without changing the already-approved high-level architecture:
  - **maintainer pipeline** acquires, normalizes, diffs, builds, validates, and publishes
  - **desktop client** consumes published artifacts only, using the existing staging/finalization flow in [C:\MSM_App\app\updater\update_service.py](C:\MSM_App\app\updater\update_service.py)
- Concrete contradiction resolved from the repo:
  - [C:\MSM_App\app\assets\resolver.py](C:\MSM_App\app\assets\resolver.py) already supports a cache layer (`data_dir/assets`) before bundled resources, so the repo is structurally compatible with future optional asset packs. This means the artifact strategy should not stay DB-only forever.

# B. Frozen decisions

## B1. Release artifact scope

- **Frozen recommendation for initial rollout**:
  - `manifest.json`
  - `content.db`
  - `content.db.sha256`
  - `diff-report.json`
  - `validation-report.json`
  - `assets-manifest.json`
  - `assets-pack.zip` is **published and versioned in the maintainer pipeline from the first release**, but **desktop client consumption is feature-gated and deferred to the client-hardening phase**.
- Rationale:
  - The product/vision requires updates to data and improved imagery over time.
  - The current client in [C:\MSM_App\app\updater\update_service.py](C:\MSM_App\app\updater\update_service.py) only stages `content.db`, so runtime asset download should not be assumed on day one.
  - Publishing `assets-manifest.json` immediately avoids redesigning the release contract later and supports installer/release bundle validation from the beginning.

## B2. Stable identity policy

- Every monster and every egg gets a **maintainer-owned permanent `content_key`**.
- Numeric SQLite IDs are treated as **storage/runtime identifiers only**.
- Numeric IDs should be **preserved when possible** by the DB builder for operational simplicity, but they are **not** the durable identity contract.
- Durable identity across releases is `content_key`, not row ID.

## B3. Rename/deprecation policy

- Entities are **never hard-deleted** from canonical content once published.
- If an entity is no longer in scope, it becomes deprecated.
- A rename keeps the same `content_key`.
- A replacement gets a new `content_key` and the old entity is deprecated.
- Slug drift alone does not create a new entity.

## B4. Source acquisition policy

- Desktop client never scrapes external sources.
- Maintainer pipeline fetches only:
  - factual source content from approved wiki/API targets
  - official media from BBB-approved source package or allowlisted BBB media endpoints
- No runtime desktop-side Fandom scraping or BBB asset fetching is allowed.

## B5. Placeholder policy

- Placeholder assets are allowed to ship if official BBB assets are unavailable.
- Placeholder usage is a **release-blocking issue only for entities marked “must-have official art” by curator policy**.
- For all other new in-scope monsters, placeholders are allowed with explicit review approval and must be tracked in release reports.

## B6. Mixed-schema policy

- During migration rollout, the desktop app must support:
  - old `content.db` + old `userstate.db`
  - new `content.db` + old `userstate.db` during first startup migration
  - new `content.db` + new `userstate.db`
- Mixed-schema behavior is handled by startup migration before normal UI state loads.

# C. Exact artifact schemas

## C1. `manifest.json`

### Purpose

- Single source of truth for the desktop client’s update check.
- Hosted remotely and fetched by [C:\MSM_App\app\updater\update_service.py](C:\MSM_App\app\updater\update_service.py).

### Compatibility rule

- Must remain backward-compatible with the current client by preserving:
  - `content_version`
  - `content_db_url`
- All added fields are ignored by older clients.
- `artifact_contract_version` governs compatibility for new clients.

### Exact schema


| Field                          | Type                  | Required | Description                                                                     |
| ------------------------------ | --------------------- | -------- | ------------------------------------------------------------------------------- |
| `artifact_contract_version`    | string                | yes      | Contract version for manifest/artifact interpretation. Initial value: `1.1`.    |
| `channel`                      | string                | yes      | Release channel. Allowed: `stable`, `beta`. Initial rollout uses `stable` only. |
| `content_version`              | string                | yes      | Human-visible content release version.                                          |
| `published_at_utc`             | string (ISO-8601 UTC) | yes      | Publish timestamp.                                                              |
| `schema_version`               | integer               | yes      | Highest content DB migration version expected by this artifact.                 |
| `min_supported_client_version` | string                | yes      | Oldest desktop app version allowed to consume this release.                     |
| `content_db_url`               | string (HTTPS URL)    | yes      | Download location for `content.db`.                                             |
| `content_db_sha256`            | string (64 hex chars) | yes      | SHA-256 for downloaded `content.db`.                                            |
| `content_db_size_bytes`        | integer               | yes      | Exact artifact size.                                                            |
| `content_db_required`          | boolean               | yes      | Always `true`.                                                                  |
| `assets_manifest_url`          | string (HTTPS URL)    | yes      | URL for `assets-manifest.json`. Required even before client consumes assets.    |
| `assets_pack_url`              | string (HTTPS URL)    | no       | URL for `assets-pack.zip` when published.                                       |
| `assets_pack_sha256`           | string (64 hex chars) | no       | SHA-256 for `assets-pack.zip`. Required iff `assets_pack_url` present.          |
| `assets_pack_size_bytes`       | integer               | no       | Asset pack size. Required iff `assets_pack_url` present.                        |
| `assets_pack_optional`         | boolean               | yes      | `true` in initial rollout.                                                      |
| `diff_report_url`              | string (HTTPS URL)    | yes      | URL for `diff-report.json`.                                                     |
| `validation_report_url`        | string (HTTPS URL)    | yes      | URL for `validation-report.json`.                                               |
| `release_notes_url`            | string (HTTPS URL)    | no       | Optional human-readable release notes.                                          |
| `rollback_to_version`          | string                | no       | Previous recommended safe rollback target.                                      |
| `generated_by_build_id`        | string                | yes      | Immutable build ID from maintainer pipeline.                                    |
| `generated_by_git_sha`         | string                | yes      | Source revision used to generate artifacts.                                     |


### Example payload

```json
{
  "artifact_contract_version": "1.1",
  "channel": "stable",
  "content_version": "2026.03.22.1",
  "published_at_utc": "2026-03-22T18:30:00Z",
  "schema_version": 3,
  "min_supported_client_version": "1.1.0",
  "content_db_url": "https://updates.example.com/msm/stable/2026.03.22.1/content.db",
  "content_db_sha256": "5d4c0d17d83dbd4f6f0b4fb91a0b2ca58fe7e785be2f98b0e6c2fe6123456789",
  "content_db_size_bytes": 851968,
  "content_db_required": true,
  "assets_manifest_url": "https://updates.example.com/msm/stable/2026.03.22.1/assets-manifest.json",
  "assets_pack_url": "https://updates.example.com/msm/stable/2026.03.22.1/assets-pack.zip",
  "assets_pack_sha256": "1f2b3c4d5e6f77889900aabbccddeeff00112233445566778899aabbccddeeff",
  "assets_pack_size_bytes": 14827520,
  "assets_pack_optional": true,
  "diff_report_url": "https://updates.example.com/msm/stable/2026.03.22.1/diff-report.json",
  "validation_report_url": "https://updates.example.com/msm/stable/2026.03.22.1/validation-report.json",
  "release_notes_url": "https://updates.example.com/msm/stable/2026.03.22.1/release-notes.md",
  "rollback_to_version": "2026.03.01.1",
  "generated_by_build_id": "build-20260322-183000-7b4f3a1",
  "generated_by_git_sha": "7b4f3a17877bfa29c4ac5bd1c0c7b8fb7b1a9999"
}
```

### Client compatibility rules

- Current client only requires `content_version` and `content_db_url`.
- New client must reject manifest if:
  - `artifact_contract_version` unsupported
  - `min_supported_client_version` greater than current client version
  - `content_db_sha256` missing or malformed
- Unknown fields must be ignored.

## C2. `assets-manifest.json`

### Purpose

- Canonical machine-readable index of every asset relevant to a content release.
- Used by maintainer validation immediately and by desktop-client asset verification when asset-pack support is enabled.

### Exact schema


| Field                       | Type    | Required | Description                               |
| --------------------------- | ------- | -------- | ----------------------------------------- |
| `artifact_contract_version` | string  | yes      | Must match manifest contract.             |
| `content_version`           | string  | yes      | Associated content release.               |
| `generated_by_build_id`     | string  | yes      | Immutable build ID.                       |
| `asset_pack_sha256`         | string  | no       | Required iff `asset_pack_present = true`. |
| `asset_pack_present`        | boolean | yes      | Whether a pack exists for this release.   |
| `assets`                    | array   | yes      | Flat list of asset records.               |


### Asset record schema


| Field            | Type    | Required | Description                                                                     |
| ---------------- | ------- | -------- | ------------------------------------------------------------------------------- |
| `entity_type`    | string  | yes      | `monster`, `egg`, or `ui`.                                                      |
| `content_key`    | string  | no       | Required for `monster` and `egg`; omitted for generic UI assets.                |
| `relative_path`  | string  | yes      | Path under resources root, e.g. `images/monsters/zynth.png`.                    |
| `sha256`         | string  | yes      | Asset binary hash.                                                              |
| `byte_size`      | integer | yes      | Asset size in bytes.                                                            |
| `asset_source`   | string  | yes      | `bbb_fan_kit`, `generated_placeholder`, or `bundled_ui`.                        |
| `is_placeholder` | boolean | yes      | True only for generated placeholders.                                           |
| `status`         | string  | yes      | `official`, `placeholder`, `ui_core`.                                           |
| `license_basis`  | string  | yes      | `bbb_fan_kit_policy`, `internal_generated_placeholder`, or `internal_ui_asset`. |


### Example payload

```json
{
  "artifact_contract_version": "1.1",
  "content_version": "2026.03.22.1",
  "generated_by_build_id": "build-20260322-183000-7b4f3a1",
  "asset_pack_present": true,
  "asset_pack_sha256": "1f2b3c4d5e6f77889900aabbccddeeff00112233445566778899aabbccddeeff",
  "assets": [
    {
      "entity_type": "monster",
      "content_key": "monster:wublin:zynth",
      "relative_path": "images/monsters/zynth.png",
      "sha256": "b6d5f9898d42e10f12f6fd1eabf1112233445566778899001122334455667788",
      "byte_size": 38421,
      "asset_source": "bbb_fan_kit",
      "is_placeholder": false,
      "status": "official",
      "license_basis": "bbb_fan_kit_policy"
    },
    {
      "entity_type": "monster",
      "content_key": "monster:wublin:blipsqueak",
      "relative_path": "images/monsters/blipsqueak.png",
      "sha256": "aa55f9898d42e10f12f6fd1eabf1112233445566778899001122334455667700",
      "byte_size": 12610,
      "asset_source": "generated_placeholder",
      "is_placeholder": true,
      "status": "placeholder",
      "license_basis": "internal_generated_placeholder"
    }
  ]
}
```

### Compatibility rules

- Required for all published releases from day one.
- Older desktop clients ignore it.
- New asset-capable clients must reject asset pack activation if any unpacked file hash differs from this manifest.

## C3. `diff-report.json`

### Purpose

- Exact semantic delta between prior published release and candidate release.
- Used by maintainers for approval and by CI for regression assertions.

### Exact schema


| Field                       | Type   | Required | Description                                              |
| --------------------------- | ------ | -------- | -------------------------------------------------------- |
| `artifact_contract_version` | string | yes      | Contract version.                                        |
| `previous_content_version`  | string | yes      | Baseline version.                                        |
| `next_content_version`      | string | yes      | Candidate version.                                       |
| `generated_by_build_id`     | string | yes      | Build ID.                                                |
| `summary`                   | object | yes      | Aggregate counters.                                      |
| `entity_changes`            | array  | yes      | Detailed entity-level changes.                           |
| `asset_changes`             | array  | yes      | Detailed asset changes.                                  |
| `manual_review_items`       | array  | yes      | Unresolved or reviewed issues associated with this diff. |


### `summary` fields


| Field                                | Type    | Required |
| ------------------------------------ | ------- | -------- |
| `new_monsters`                       | integer | yes      |
| `changed_monsters`                   | integer | yes      |
| `deprecated_monsters`                | integer | yes      |
| `revived_monsters`                   | integer | yes      |
| `new_eggs`                           | integer | yes      |
| `changed_eggs`                       | integer | yes      |
| `deprecated_eggs`                    | integer | yes      |
| `requirement_changes`                | integer | yes      |
| `official_to_placeholder_downgrades` | integer | yes      |
| `placeholder_to_official_upgrades`   | integer | yes      |


### `entity_changes` record


| Field          | Type          | Required | Description                                                                                            |
| -------------- | ------------- | -------- | ------------------------------------------------------------------------------------------------------ |
| `entity_type`  | string        | yes      | `monster` or `egg`.                                                                                    |
| `content_key`  | string        | yes      | Stable entity key.                                                                                     |
| `change_class` | string        | yes      | One of `new`, `rename`, `field_change`, `requirements_change`, `deprecated`, `revived`, `replacement`. |
| `before`       | object/null   | yes      | Prior normalized entity snapshot.                                                                      |
| `after`        | object/null   | yes      | New normalized entity snapshot.                                                                        |
| `notes`        | array[string] | yes      | Human-readable reasons.                                                                                |


### `asset_changes` record


| Field                  | Type        | Required |
| ---------------------- | ----------- | -------- |
| `content_key`          | string      | yes      |
| `relative_path_before` | string/null | yes      |
| `relative_path_after`  | string/null | yes      |
| `change_class`         | string      | yes      |
| `sha256_before`        | string/null | yes      |
| `sha256_after`         | string/null | yes      |
| `status_before`        | string/null | yes      |
| `status_after`         | string/null | yes      |


### Example payload

```json
{
  "artifact_contract_version": "1.1",
  "previous_content_version": "2026.03.01.1",
  "next_content_version": "2026.03.22.1",
  "generated_by_build_id": "build-20260322-183000-7b4f3a1",
  "summary": {
    "new_monsters": 1,
    "changed_monsters": 2,
    "deprecated_monsters": 0,
    "revived_monsters": 0,
    "new_eggs": 0,
    "changed_eggs": 1,
    "deprecated_eggs": 0,
    "requirement_changes": 2,
    "official_to_placeholder_downgrades": 0,
    "placeholder_to_official_upgrades": 3
  },
  "entity_changes": [
    {
      "entity_type": "monster",
      "content_key": "monster:wublin:zynth",
      "change_class": "requirements_change",
      "before": {"name": "Zynth"},
      "after": {"name": "Zynth"},
      "notes": ["Quantity changed for egg:monster:egg:mammott from 3 to 2"]
    }
  ],
  "asset_changes": [],
  "manual_review_items": []
}
```

### Compatibility rules

- Not consumed by current client.
- Publish-blocking if malformed.
- Missing file blocks release publication.

## C4. `validation-report.json`

### Purpose

- Machine-readable record of all validation gates run for a release candidate.

### Exact schema


| Field                       | Type   | Required | Description                       |
| --------------------------- | ------ | -------- | --------------------------------- |
| `artifact_contract_version` | string | yes      | Contract version.                 |
| `content_version`           | string | yes      | Candidate release version.        |
| `generated_by_build_id`     | string | yes      | Build ID.                         |
| `overall_status`            | string | yes      | `pass`, `warn`, or `fail`.        |
| `checks`                    | array  | yes      | Ordered validation check results. |


### Check record schema


| Field            | Type   | Required |
| ---------------- | ------ | -------- |
| `check_id`       | string | yes      |
| `owner_module`   | string | yes      |
| `scope`          | string | yes      |
| `status`         | string | yes      |
| `severity`       | string | yes      |
| `blocking_level` | string | yes      |
| `message`        | string | yes      |
| `details`        | object | no       |


### Blocking levels

- `publish_blocker`
- `client_install_blocker`
- `warning_only`

### Example payload

```json
{
  "artifact_contract_version": "1.1",
  "content_version": "2026.03.22.1",
  "generated_by_build_id": "build-20260322-183000-7b4f3a1",
  "overall_status": "pass",
  "checks": [
    {
      "check_id": "db.integrity",
      "owner_module": "pipeline.validation.content_db",
      "scope": "content.db",
      "status": "pass",
      "severity": "error",
      "blocking_level": "publish_blocker",
      "message": "SQLite integrity check returned ok"
    },
    {
      "check_id": "assets.placeholder_count",
      "owner_module": "pipeline.validation.assets",
      "scope": "assets-manifest.json",
      "status": "warn",
      "severity": "warning",
      "blocking_level": "warning_only",
      "message": "3 monster assets remain placeholders",
      "details": {"content_keys": ["monster:wublin:blipsqueak"]}
    }
  ]
}
```

### Compatibility rules

- Publish required from day one.
- Desktop client may optionally fetch/display a condensed interpretation in the future, but does not need it for initial rollout.

# D. Exact normalized-content schemas

## D1. `monsters.json`

### Record schema


| Field                | Type          | Required | Description                                            |
| -------------------- | ------------- | -------- | ------------------------------------------------------ |
| `content_key`        | string        | yes      | Permanent maintainer identity.                         |
| `display_name`       | string        | yes      | User-facing name.                                      |
| `monster_type`       | string        | yes      | `wublin`, `celestial`, `amber`.                        |
| `source_slug`        | string        | yes      | Current factual source slug.                           |
| `source_url`         | string        | yes      | Canonical page URL.                                    |
| `source_fingerprint` | string        | yes      | Hash of normalized raw-source payload for this entity. |
| `wiki_slug`          | string        | yes      | Current wiki slug persisted into DB for compatibility. |
| `image_path`         | string        | yes      | Relative runtime asset path.                           |
| `is_placeholder`     | boolean       | yes      | Whether current image path is placeholder-backed.      |
| `asset_source`       | string        | yes      | `bbb_fan_kit` or `generated_placeholder`.              |
| `asset_sha256`       | string        | yes      | Current asset hash.                                    |
| `is_deprecated`      | boolean       | yes      | Deprecated state.                                      |
| `deprecated_at_utc`  | string/null   | yes      | Timestamp if deprecated.                               |
| `deprecation_reason` | string/null   | yes      | Human reason code.                                     |
| `provenance`         | object        | yes      | Structured provenance.                                 |
| `overrides_applied`  | array[string] | yes      | Override keys used during normalization.               |


### Invariants

- `content_key` unique across monsters.
- `display_name` unique among active monsters of same type unless explicit alias policy says otherwise.
- `image_path` must correspond to an entry in `assets.json`.
- `is_placeholder = true` iff referenced asset has `status = placeholder`.

### Example

```json
{
  "content_key": "monster:wublin:zynth",
  "display_name": "Zynth",
  "monster_type": "wublin",
  "source_slug": "Zynth",
  "source_url": "https://example.invalid/wiki/Zynth",
  "source_fingerprint": "sha256:9ab1...",
  "wiki_slug": "Zynth",
  "image_path": "images/monsters/zynth.png",
  "is_placeholder": false,
  "asset_source": "bbb_fan_kit",
  "asset_sha256": "b6d5f9898d42e10f12f6fd1eabf1112233445566778899001122334455667788",
  "is_deprecated": false,
  "deprecated_at_utc": null,
  "deprecation_reason": null,
  "provenance": {
    "factual_source": "fandom",
    "retrieved_at_utc": "2026-03-22T16:00:00Z",
    "raw_snapshot_id": "raw-20260322-fandom-01"
  },
  "overrides_applied": []
}
```

## D2. `eggs.json`

### Record schema


| Field                   | Type          | Required |
| ----------------------- | ------------- | -------- |
| `content_key`           | string        | yes      |
| `display_name`          | string        | yes      |
| `breeding_time_seconds` | integer       | yes      |
| `breeding_time_display` | string        | yes      |
| `source_slug`           | string        | yes      |
| `source_url`            | string        | yes      |
| `source_fingerprint`    | string        | yes      |
| `egg_image_path`        | string        | yes      |
| `is_placeholder`        | boolean       | yes      |
| `asset_source`          | string        | yes      |
| `asset_sha256`          | string        | yes      |
| `is_deprecated`         | boolean       | yes      |
| `deprecated_at_utc`     | string/null   | yes      |
| `deprecation_reason`    | string/null   | yes      |
| `provenance`            | object        | yes      |
| `overrides_applied`     | array[string] | yes      |


### Invariants

- `content_key` unique across eggs.
- `breeding_time_seconds > 0` for active eggs.
- `egg_image_path` must exist in `assets.json`.

## D3. `requirements.json`

### Record schema


| Field                | Type          | Required |
| -------------------- | ------------- | -------- |
| `monster_key`        | string        | yes      |
| `egg_key`            | string        | yes      |
| `quantity`           | integer       | yes      |
| `source_fingerprint` | string        | yes      |
| `provenance`         | object        | yes      |
| `overrides_applied`  | array[string] | yes      |


### Invariants

- Composite uniqueness on (`monster_key`, `egg_key`).
- `quantity >= 1`.
- `monster_key` and `egg_key` must reference active or deprecated entities in their respective files.

### Example

```json
{
  "monster_key": "monster:wublin:zynth",
  "egg_key": "egg:mammott",
  "quantity": 3,
  "source_fingerprint": "sha256:4cd2...",
  "provenance": {
    "factual_source": "fandom",
    "retrieved_at_utc": "2026-03-22T16:00:00Z"
  },
  "overrides_applied": []
}
```

## D4. `assets.json`

### Record schema


| Field              | Type    | Required |
| ------------------ | ------- | -------- |
| `entity_type`      | string  | yes      |
| `content_key`      | string  | no       |
| `relative_path`    | string  | yes      |
| `sha256`           | string  | yes      |
| `byte_size`        | integer | yes      |
| `asset_source`     | string  | yes      |
| `status`           | string  | yes      |
| `is_placeholder`   | boolean | yes      |
| `license_basis`    | string  | yes      |
| `source_reference` | string  | yes      |
| `generated_at_utc` | string  | yes      |


### Invariants

- `relative_path` unique.
- `content_key` required for `monster` and `egg` assets.
- `sha256` immutable for a given binary.

## D5. `aliases.json`

### Record schema


| Field         | Type    | Required |
| ------------- | ------- | -------- |
| `entity_type` | string  | yes      |
| `content_key` | string  | yes      |
| `alias_kind`  | string  | yes      |
| `alias_value` | string  | yes      |
| `is_active`   | boolean | yes      |
| `notes`       | string  | no       |


### Allowed `alias_kind`

- `display_name`
- `source_slug`
- `legacy_name`
- `legacy_slug`

### Invariants

- Alias values are case-insensitive unique within (`entity_type`, `alias_kind`) unless explicitly deprecated.

## D6. `deprecations.json`

### Record schema


| Field                     | Type   | Required |
| ------------------------- | ------ | -------- |
| `entity_type`             | string | yes      |
| `content_key`             | string | yes      |
| `deprecated_at_utc`       | string | yes      |
| `reason_code`             | string | yes      |
| `replacement_content_key` | string | no       |
| `approved_by`             | string | yes      |
| `notes`                   | string | no       |


### Invariants

- Replacement key cannot equal deprecated key.
- Deprecation of an active entity must appear here before publication.

## D7. `overrides.yaml`

### Exact structure

- Top-level sections:
  - `identity_overrides`
  - `field_overrides`
  - `asset_overrides`
  - `classification_overrides`
- Every override record must have:
  - `override_id`
  - `entity_type`
  - `target_selector`
  - `approved_by`
  - `reason`
  - `effective_from_content_version`

### Example

```yaml
identity_overrides:
  - override_id: ident-001
    entity_type: monster
    target_selector:
      source_slug: Zynth
    forced_content_key: monster:wublin:zynth
    approved_by: maintainer
    reason: Canonical identity freeze
    effective_from_content_version: 2026.03.22.1
```

## D8. `manual-review-queue.json`

### Record schema


| Field                   | Type    | Required |
| ----------------------- | ------- | -------- |
| `review_id`             | string  | yes      |
| `issue_type`            | string  | yes      |
| `severity`              | string  | yes      |
| `entity_type`           | string  | no       |
| `candidate_content_key` | string  | no       |
| `source_reference`      | string  | yes      |
| `proposed_resolution`   | string  | no       |
| `blocking`              | boolean | yes      |
| `created_at_utc`        | string  | yes      |
| `status`                | string  | yes      |
| `approved_by`           | string  | no       |
| `resolution_notes`      | string  | no       |


### Allowed `issue_type`

- `identity_ambiguous`
- `rename_vs_new_unclear`
- `replacement_unclear`
- `official_asset_missing`
- `source_payload_incomplete`
- `override_required`

### Invariants

- Any unresolved `blocking = true` item blocks publication.
- Closed items must include `approved_by` and `resolution_notes`.

# E. Stable identity and rename/deprecation rules

## E1. `content_key` format

- Monster format: `monster:<monster_type>:<canonical_slug>`
- Egg format: `egg:<canonical_slug>`
- `canonical_slug` rules:
  - lowercase ASCII only
  - allowed characters: `a-z`, `0-9`, `-`
  - spaces collapse to `-`
  - punctuation removed except hyphen
  - no consecutive hyphens
- Examples:
  - `monster:wublin:zynth`
  - `monster:celestial:galvana`
  - `monster:amber:kayna`
  - `egg:toe-jammer`

## E2. Permanence rules

- Once published, `content_key` never changes.
- Display name may change.
- Source slug may change.
- Asset path may change.
- Type may only change with explicit replacement/deprecation review; do not silently mutate type on a live `content_key`.

## E3. Numeric ID policy

- DB builder should preserve numeric IDs for unchanged `content_key` rows when building next release from previous release baseline.
- If preservation fails, correctness still holds because `content_key` is the durable identity.
- Desktop userstate survival must never depend on numeric ID stability.

## E4. Classification rules

### Decision table


| Scenario                                                   | Same `content_key`?                 | Same semantic entity? | Outcome                     |
| ---------------------------------------------------------- | ----------------------------------- | --------------------- | --------------------------- |
| Name changed, same source entity, same type                | yes                                 | yes                   | `rename`                    |
| Source slug changed, same entity                           | yes                                 | yes                   | `slug_drift` / field update |
| Requirements changed, same entity                          | yes                                 | yes                   | `requirements_change`       |
| Official art added for placeholder entity                  | yes                                 | yes                   | `placeholder_to_official`   |
| Entity disappears from source with no replacement evidence | yes                                 | no longer active      | `deprecated`                |
| New entity appears with no strong link to existing one     | new key                             | yes new entity        | `new monster`               |
| Old entity retired and new different entity introduced     | old key deprecated, new key created | no                    | `deprecated + replacement`  |
| Name collides but type and provenance disagree             | unresolved                          | unclear               | manual review blocker       |


### Rename vs new vs replacement rules

- `rename` when all are true:
  - current entity can be mapped via override, alias, or stable provenance
  - type unchanged
  - no conflicting active entity already owns the target name
- `new monster` when all are true:
  - no existing content key matches by override, slug, alias, or approved provenance
  - not explicitly marked as replacement of a deprecated entity
- `deprecated + replacement` when all are true:
  - maintainer review explicitly links old entity to new one as non-identical successor
  - replacement receives a fresh `content_key`
  - old entity remains deprecated with `replacement_content_key`

## E5. Alias handling

- Aliases are lookup aids only.
- Adding an alias never changes `content_key`.
- Alias resolution precedence:
  1. explicit identity override
  2. exact `content_key`
  3. exact current `source_slug`
  4. active alias match
  5. exact normalized display-name match within entity type
  6. otherwise manual review

## E6. Slug drift handling

- If source slug changes but alias/override/history links it to the same entity:
  - keep same `content_key`
  - update `source_slug` and `wiki_slug`
  - record prior slug in aliases
  - classify as field change, not new entity

# F. DB migration and reconciliation spec

## F1. `content.db` migration order

1. Add new content migration `0002_stable_identity_and_asset_metadata.sql`
  - add `content_key`, provenance, asset metadata, deprecation metadata to `monsters`
  - add `content_key`, provenance, asset metadata, deprecation metadata, `is_deprecated` to `egg_types`
  - add auxiliary tables `content_aliases` and `content_audit`
  - extend required `update_metadata` keys
2. Backfill current rows:
  - derive `content_key` from current seeded names/types using frozen slug rules
  - set `source_slug = wiki_slug` for monsters
  - initialize fingerprint fields to empty or seeded placeholders for historical baseline
  - initialize asset metadata from existing paths and bundle hashes when available
3. Add uniqueness indexes on `content_key` columns after successful backfill.

## F2. `userstate.db` migration order

1. Add `0002_stable_keys.sql`
  - `ALTER TABLE active_targets ADD COLUMN monster_key TEXT NOT NULL DEFAULT ''`
  - `ALTER TABLE target_requirement_progress ADD COLUMN egg_key TEXT NOT NULL DEFAULT ''`
  - `INSERT OR IGNORE INTO app_settings(key, value) VALUES('last_reconciled_content_version', '')`
2. Backfill on first startup after both schemas available:
  - for each `active_targets.monster_id`, resolve current `content.db.monsters.content_key`
  - write to `active_targets.monster_key`
  - for each `target_requirement_progress.egg_type_id`, resolve current `content.db.egg_types.content_key`
  - write to `target_requirement_progress.egg_key`
3. After backfill, all future reconcile/update logic must use keys as the authoritative bridge.

## F3. Mixed-schema startup behavior

- On startup in [C:\MSM_App\app\bootstrap.py](C:\MSM_App\app\bootstrap.py):
  - run content migrations
  - run userstate migrations
  - run a new post-migration backfill step before loading app state
- If `content.db` is pre-`0002` and `userstate.db` is pre-`0002`:
  - migrate both and backfill keys from current numeric IDs
- If `content.db` is `0002+` and `userstate.db` is pre-`0002`:
  - migrate userstate and backfill from stable `content_key`
- If backfill cannot resolve any current target or progress row:
  - treat as startup-fatal integrity issue in development
  - in production, log error, surface recovery dialog, and offer restore-from-backup / bundled-baseline fallback

## F4. Post-update reconciliation behavior

- After a successful `content.db` finalize in [C:\MSM_App\app\ui\main_window.py](C:\MSM_App\app\ui\main_window.py):
  1. resolve every active target by `monster_key`
  2. if no active monster exists for key or monster is deprecated, delete target and associated progress
  3. rebuild target requirement expectations from new `monster_requirements` using `egg_key`
  4. for existing requirement rows:
    - if egg still required, keep and clip `satisfied_count` to `required_count`
    - if egg no longer required, delete that target requirement progress row
  5. for new required eggs not previously tracked, insert zero-satisfied rows
  6. update `last_reconciled_content_version`
- This replaces the current narrower logic that only checks `monster_id` active/deprecated and clips satisfied counts.

## F5. Rollback/recovery behavior

- If DB finalization fails before activation:
  - restore `content_backup.db`
  - keep prior `userstate.db`
  - do not update `last_reconciled_content_version`
- If crash occurs after DB swap but before reconciliation completes:
  - startup detects `content_version != last_reconciled_content_version`
  - run reconciliation before normal UI load
- If reconciliation itself fails:
  - log structured error
  - leave app in recovery-required mode rather than loading inconsistent state

# G. Source acquisition and manual review workflow

## G1. Exact fetch targets/source categories

- `factual_sources`:
  - monster roster pages / infobox content
  - requirement data pages
  - breeding-time pages or fields
- `official_asset_sources`:
  - BBB Fan Kit archive or allowlisted BBB-hosted asset endpoints
- `curation_sources`:
  - override files committed in repo
  - deprecation records
  - alias mappings

## G2. Fetch caching rules

- Raw source cache lives under maintainer pipeline workspace, not under desktop app runtime paths.
- Cache key = source category + canonical source reference + retrieval timestamp + content hash.
- Do not re-fetch the same source within a single pipeline run.
- Preserve raw source snapshots for at least the last published release and current candidate release.

## G3. Retry / rate-limit policy

- Factual source fetch:
  - max 3 attempts
  - exponential backoff starting at 1s
  - serialize page-level requests if source policy is uncertain
  - never exceed a maintainer-configured request concurrency cap
- Official asset fetch:
  - max 3 attempts per asset package or file
  - fail closed on non-BBB domains
- Hard network timeout and explicit classification of timeout vs malformed payload vs policy violation.

## G4. Provenance requirements

- Every normalized record must record:
  - retrieval timestamp
  - canonical source reference
  - raw payload hash
  - whether any curator override altered the final field values
- Every release must be traceable back to raw snapshot IDs in `content_audit` and `validation-report.json`.

## G5. Failure classification


| Failure                                                                                                       | Severity                                         | Publish effect                                  |
| ------------------------------------------------------------------------------------------------------------- | ------------------------------------------------ | ----------------------------------------------- |
| Factual source unavailable for non-critical refresh but previous snapshot exists and no new entities expected | warning                                          | can continue with explicit stale-source warning |
| Factual source unavailable and candidate introduces unresolved changes                                        | error                                            | publish blocker                                 |
| Source payload malformed for one entity with no safe fallback                                                 | error                                            | publish blocker                                 |
| BBB asset unavailable for a new entity                                                                        | warning if placeholder approved; error otherwise | depends on placeholder approval                 |
| BBB asset fetched from non-allowlisted domain                                                                 | error                                            | publish blocker                                 |
| Identity ambiguous                                                                                            | error                                            | publish blocker                                 |
| Missing provenance metadata                                                                                   | error                                            | publish blocker                                 |


## G6. Manual review queue location and lifecycle

- Canonical file location:
  - `pipeline/review/manual-review-queue.json`
- Closed review archive location:
  - `pipeline/review/archive/<content_version>.json`
- Each run updates the active review queue.
- Unresolved blocking items fail the pipeline before artifact publication.

## G7. Release-blocking vs shippable-with-placeholder

### Release blockers

- unresolved identity match
- rename vs replacement ambiguity
- missing required metadata/provenance
- official-to-placeholder downgrade without explicit approval
- source parsing failure for an active changed entity
- unresolved requirement-set ambiguity

### Can ship with placeholder

- newly discovered monster with approved placeholder and otherwise complete factual data
- newly discovered egg with approved placeholder and otherwise complete factual data
- improved official asset not yet available, provided previous placeholder remains valid

## G8. Placeholder approval

- Placeholder use must be approved by maintainer policy encoded in overrides, not ad hoc.
- Exact approval fields in override record:
  - `override_id`
  - `content_key`
  - `approved_by`
  - `reason`
  - `valid_until_content_version` or `until_official_asset_available: true`

## G9. Product-vision reconciliation statement

- The product vision says the app “stays current” with new monsters, changed requirements, and improved images.
- Implementation interpretation is frozen as:
  - discovery, comparison, and media ingestion happen in the maintainer pipeline
  - the desktop app reflects those discoveries by consuming published release artifacts through `Check for Updates`
  - therefore the desktop app **appears** to discover new monsters over time from the user’s perspective, but does not itself perform discovery logic

# H. Asset/update packaging policy

## H1. Asset naming/path conventions

- Monster assets: `images/monsters/<canonical_slug>.png`
- Egg assets: `images/eggs/<canonical_slug>.png`
- UI assets: `images/ui/<asset_name>.<ext>`
- `<canonical_slug>` must match `content_key` slug segment exactly.
- No spaces, uppercase, or punctuation beyond hyphen.

## H2. Placeholder generation rules

- Generator input:
  - entity type
  - `content_key`
  - display initials
  - type color profile
- Generator output must be deterministic for same inputs.
- Placeholder binary hash must therefore be stable for the same generator version.
- Placeholder file path uses the same final runtime path as the official asset would use.

## H3. Placeholder replacement rules

- When official BBB asset becomes available:
  - keep same `relative_path`
  - replace binary
  - set `is_placeholder = false`
  - update `asset_source = bbb_fan_kit`
  - new hash recorded in `assets-manifest.json`
  - classify as `placeholder_to_official`

## H4. Asset hashing/versioning policy

- Every asset file hash uses SHA-256.
- Asset version is implicit in the content release; no separate semantic asset versioning is required initially.
- Asset change is detected purely by hash delta + source/status delta.

## H5. What ships in installer vs update artifacts

### Initial rollout

- Installer ships:
  - `content.db`
  - bundled assets under `resources/`
  - `placeholder.png`
  - core UI assets
- Published update artifacts ship:
  - `content.db`
  - metadata reports
  - `assets-manifest.json`
  - `assets-pack.zip`
- Desktop client initial runtime behavior:
  - consumes `content.db`
  - ignores `assets-pack.zip` until feature gate enabled

### After client asset-pack enablement

- Desktop app may stage `assets-pack.zip` into `data_dir/assets`
- Runtime asset resolution remains `cache -> bundle -> placeholder` via [C:\MSM_App\app\assets\resolver.py](C:\MSM_App\app\assets\resolver.py)

# I. Validation and test contracts

## I1. Required validation checks


| Check ID                         | Owner module                                                                                                    | Input                                  | Pass criteria                                         | Failure effect                                                        |
| -------------------------------- | --------------------------------------------------------------------------------------------------------------- | -------------------------------------- | ----------------------------------------------------- | --------------------------------------------------------------------- |
| `db.integrity`                   | `pipeline.validation.content_db` and [C:\MSM_App\app\updater\validator.py](C:\MSM_App\app\updater\validator.py) | `content.db`                           | `PRAGMA integrity_check == ok`                        | publish blocker and client install blocker                            |
| `db.required_tables`             | same                                                                                                            | `content.db`                           | all required tables present                           | publish blocker and client install blocker                            |
| `db.required_metadata`           | same                                                                                                            | `content.db`                           | all required metadata keys present and non-empty      | publish blocker and client install blocker                            |
| `db.no_orphan_requirements`      | same                                                                                                            | `content.db`                           | no orphan `monster_id` or `egg_type_id` refs          | publish blocker and client install blocker                            |
| `db.unique_content_keys`         | `pipeline.validation.identity`                                                                                  | normalized data and built DB           | no duplicate keys                                     | publish blocker                                                       |
| `db.semantic_duplicate_entities` | `pipeline.validation.identity`                                                                                  | normalized data                        | no unresolved semantic duplicates                     | publish blocker                                                       |
| `assets.all_paths_resolve`       | `pipeline.validation.assets`                                                                                    | assets manifest + artifact tree        | every referenced path exists                          | publish blocker                                                       |
| `assets.hash_match`              | `pipeline.validation.assets`                                                                                    | asset files + `assets-manifest.json`   | all hashes match                                      | publish blocker and client install blocker when asset support enabled |
| `assets.no_unapproved_downgrade` | `pipeline.validation.assets`                                                                                    | diff + overrides                       | no official-to-placeholder downgrade without approval | publish blocker                                                       |
| `review.no_blocking_items`       | `pipeline.validation.review`                                                                                    | manual review queue                    | zero open blocking items                              | publish blocker                                                       |
| `manifest.contract_valid`        | `pipeline.validation.manifest` and client updater                                                               | `manifest.json`                        | schema-valid and compatible                           | publish blocker and client install blocker                            |
| `artifact.checksum_valid`        | client updater                                                                                                  | downloaded artifacts                   | SHA-256 matches manifest                              | client install blocker                                                |
| `reconcile.fixtures_pass`        | `tests/e2e`                                                                                                     | published artifact + fixture userstate | fixture scenarios reconcile correctly                 | publish blocker                                                       |


## I2. Golden-fixture expectations

- Add frozen fixture suites for:
  - `new_monster_with_placeholder`
  - `monster_rename_same_content_key`
  - `slug_drift_no_identity_change`
  - `requirements_quantity_change`
  - `monster_deprecated`
  - `placeholder_to_official`
  - `official_to_placeholder_unapproved`
  - `ambiguous_identity_requires_review`
- Each fixture must define:
  - baseline normalized content
  - candidate normalized content
  - expected `diff-report.json`
  - expected validation outcome
  - expected post-update userstate reconciliation result where applicable

## I3. Repo modules to extend/create

- Extend:
  - [C:\MSM_App\app\updater\validator.py](C:\MSM_App\app\updater\validator.py)
  - [C:\MSM_App\scripts\verify_bundle.py](C:\MSM_App\scripts\verify_bundle.py)
  - [C:\MSM_App\tests\unit\test_updater.py](C:\MSM_App\tests\unit\test_updater.py)
  - [C:\MSM_App\tests\unit\test_update_finalization.py](C:\MSM_App\tests\unit\test_update_finalization.py)
- Create:
  - `tests/golden/` fixture set for diff/validation outcomes
  - maintainer pipeline validation modules
  - end-to-end release pipeline tests

# J. Revised phase-by-phase implementation checklist

## Phase 0: decisions/contract alignment

### Deliverables

- ADR for boundary split
- Frozen artifact schema docs
- Frozen `content_key` rules
- Frozen source/acquisition policy
- Frozen placeholder approval policy

### Exact files/modules to create or edit

- new ADR/design doc under `docs/` or repo root
- update [C:\MSM_App\MSM_Awakening_Tracker_TDD_v1_3.md](C:\MSM_App\MSM_Awakening_Tracker_TDD_v1_3.md) sections that currently blur client vs maintainer roles
- update [C:\MSM_App\MSM_Awakening_Tracker_SRS_v1.1.md](C:\MSM_App\MSM_Awakening_Tracker_SRS_v1.1.md) only if required to remove ambiguity

### Gating dependencies

- None

### Done means

- Artifact schemas are frozen exactly as specified here.
- Stable identity rules are approved.
- Open questions reduced to external/legal/ops items only.

## Phase 1: source acquisition + normalization foundation

### Deliverables

- `pipeline/raw/` source cache
- `pipeline/normalized/` JSON schemas and seed dataset
- `pipeline/curation/overrides.yaml`
- `pipeline/review/manual-review-queue.json`
- content/userstate migrations for stable keys

### Exact files/modules to create or edit

- create maintainer pipeline package
- create normalized schema documents and seed data exports
- edit [C:\MSM_App\scripts\seed_content_db.py](C:\MSM_App\scripts\seed_content_db.py) to consume normalized content rather than Python literals
- add new migration SQL files under [C:\MSM_App\app\db\migrations\content](C:\MSM_App\app\db\migrations\content) and [C:\MSM_App\app\db\migrations\userstate](C:\MSM_App\app\db\migrations\userstate)
- edit [C:\MSM_App\app\repositories\monster_repo.py](C:\MSM_App\app\repositories\monster_repo.py) and related models for new fields

### Gating dependencies

- Phase 0 frozen contracts

### Done means

- Current catalog fully represented in normalized files.
- Every monster/egg has stable `content_key`.
- Existing app can migrate local DBs and backfill stable keys successfully.

## Phase 2: diff/build/package pipeline

### Deliverables

- semantic diff engine
- deterministic DB builder
- assets manifest builder
- validation-report generator
- release manifest builder
- publishable artifact directory structure

### Exact files/modules to create or edit

- create pipeline diff/build/publish modules
- refactor [C:\MSM_App\scripts\generate_assets.py](C:\MSM_App\scripts\generate_assets.py) into reusable pipeline asset builder
- refactor [C:\MSM_App\scripts\verify_bundle.py](C:\MSM_App\scripts\verify_bundle.py) into reusable validator entry point
- update resource build path for [C:\MSM_App\resources\db\content.db](C:\MSM_App\resources\db\content.db)

### Gating dependencies

- Phase 1 normalized data and migrations

### Done means

- Build is reproducible from pinned normalized input.
- `manifest.json`, `assets-manifest.json`, `diff-report.json`, and `validation-report.json` are emitted exactly to schema.
- Release artifacts pass all publish-blocking validation checks.

## Phase 3: client integration hardening

### Deliverables

- richer validator contract
- manifest/apply decoupling
- checksum verification
- startup reconciliation recovery
- stable-key-aware reconciliation
- optional asset-pack staging behind feature gate

### Exact files/modules to create or edit

- edit [C:\MSM_App\app\updater\update_service.py](C:\MSM_App\app\updater\update_service.py)
- edit [C:\MSM_App\app\updater\validator.py](C:\MSM_App\app\updater\validator.py)
- edit [C:\MSM_App\app\ui\main_window.py](C:\MSM_App\app\ui\main_window.py)
- edit [C:\MSM_App\app\assets\resolver.py](C:\MSM_App\app\assets\resolver.py)
- edit repositories handling target reconciliation
- extend [C:\MSM_App\tests\unit\test_updater.py](C:\MSM_App\tests\unit\test_updater.py)
- extend [C:\MSM_App\tests\unit\test_update_finalization.py](C:\MSM_App\tests\unit\test_update_finalization.py)

### Gating dependencies

- Phase 2 artifact contract and generated test artifacts

### Done means

- Client can safely apply signed/checksummed content release artifacts.
- User state survives rebuilt content even when numeric IDs differ.
- Feature-gated asset-pack install path works end-to-end when enabled.

## Phase 4: operationalization and release readiness

### Deliverables

- CI release pipeline
- dry-run diff review job
- build reports and logs
- rollback runbook
- release promotion procedure

### Exact files/modules to create or edit

- CI workflow files
- publish scripts
- release docs/runbooks
- mock release server integration test harness

### Gating dependencies

- Phases 1–3 functionally complete

### Done means

- Maintainer can run source acquisition to publish with a documented, validated workflow.
- CI blocks malformed or unsafe releases automatically.
- Rollback and recovery are tested and documented.

# K. Remaining true open questions

## K1. BBB Fan Kit distribution mechanism

- Why still open:
  - Repo/docs do not freeze whether BBB assets are obtained as a zip archive, file set, or another approved format.
- What decision unblocks implementation:
  - confirm the approved acquisition mechanism and any redistribution constraints.

## K2. Production artifact hosting target

- Why still open:
  - The current updater default points at GitHub raw, but long-term hosting/retention/signing strategy is not frozen in repo/docs.
- What decision unblocks implementation:
  - choose the production host (`GitHub Releases`, object storage, CDN-backed bucket, etc.).

## K3. Signature verification rollout timing

- Why still open:
  - Checksums can be implemented immediately; signatures require key-management/distribution decisions outside the current repo.
- What decision unblocks implementation:
  - decide whether initial release uses checksum-only or checksum + detached signatures.

## K4. Whether official release notes / patch notes are an approved secondary factual source

- Why still open:
  - Repo/docs strongly imply wiki/Fandom for structured factual content, but “authoritative/approved sources” may include official notes as a secondary signal.
- What decision unblocks implementation:
  - approve or reject official patch/release notes as a secondary discovery signal used by the maintainer pipeline only.

