# Content Source Policy

This document defines the architecture, data sources, acquisition policies, and
review workflows for the MSM Awakening Tracker content system.

---

## Three-Layer Architecture

```
Layer 1 — Ingestion / Import (maintainer-side)
  External source (MSM Wiki) -> wiki_fetcher -> SourceCache -> normalizer
    -> review_items (if ambiguous) -> review_queue.json
    -> normalized records -> pipeline/normalized/*.json

Layer 2 — Build / Publish (maintainer-side)
  pipeline/normalized/*.json -> db_builder -> content.db
    -> diff engine -> DiffResult
    -> validation checks -> [ValidationCheck]
    -> artifact generator -> manifest.json + reports
    -> publish to content repo

Layer 3 — App Consumption (desktop client)
  manifest.json (hosted) -> update_service -> download content.db
    -> validate SHA-256 + schema -> atomic replace -> reconcile -> done
```

**Key principle:** The desktop app never scrapes the web. It only consumes
prebuilt `content.db` from a hosted manifest. All data acquisition and
normalization happen in the maintainer-side pipeline.

---

## Allowed Sources

### Primary factual source: MSM Fandom Wiki

- **URL pattern:** `https://mysingingmonsters.fandom.com/wiki/<PageName>`
- **Authority level:** Primary — considered authoritative for factual game data
- **Extracted data:**
  - Monster names and display names
  - Monster types (wublin, celestial, amber)
  - Egg/breeding requirements (egg type + quantity per monster)
  - Breeding times for each egg type
- **Not extracted (v1):**
  - Lore text, trivia, flavor descriptions
  - Sound/audio references
  - Breeding combination details beyond egg type + time

### Advisory sources (future)

- **BBB official announcements** — authoritative for game updates, new monsters
- **Community data repositories** — advisory, requires cross-referencing

### Explicitly excluded sources

- Direct game client data extraction
- Unofficial APIs or data leaks
- Copyrighted asset downloads (images, audio) from any source

---

## Field Classification

| Field | Source Authority | Auto-accept? | Notes |
|-------|----------------|--------------|-------|
| `display_name` | Wiki (authoritative) | If unchanged | Review if changed |
| `monster_type` | Wiki (authoritative) | If unchanged | Review if changed |
| `content_key` | Derived (computed) | Auto for existing | Review for new |
| Egg requirements | Wiki (authoritative) | Never | Always review changes |
| `breeding_time_seconds` | Wiki (authoritative) | If unchanged | Review if changed |
| `image_path` | Generated (placeholder) | Auto | Never sourced from wiki |
| `is_placeholder` | Internal | Auto | Always `true` for v1 |
| `asset_source` | Internal | Auto | Always `generated_placeholder` for v1 |

---

## Image Acquisition Policy (v1)

**All images remain generated placeholders for v1.**

- The importer captures image *metadata* (source URLs, availability) in raw
  cached payloads but does NOT download images
- The `asset_source` field remains `"generated_placeholder"` for all content
- The `is_placeholder` field remains `true` for all content
- When official assets become available in the future, they are integrated via
  `asset_overrides` in `pipeline/curation/overrides.yaml`, NOT by direct download

**Rationale:** Image licensing under the BBB Fan Content Policy requires careful
compliance. Factual game data (names, types, requirements) is freely usable;
artwork is not. Separating image sourcing from data acquisition avoids legal risk.

---

## BBB Fan Content Policy Compliance

The application includes a BBB Fan Content Policy disclaimer in Settings (already
implemented). Compliance is maintained by:

1. Only scraping **factual game data** (names, types, requirements, times)
2. Never downloading copyrighted artwork, audio, or creative assets
3. Using **generated placeholder images** for all monster/egg visuals
4. Including the disclaimer text in every distributed build
5. Crediting Big Blue Bubble as the creator of My Singing Monsters

---

## Review Workflow

### When the importer runs

1. Maintainer runs `python scripts/import_content.py`
2. The importer fetches current data from the MSM Wiki
3. Each fetched record is normalized via `pipeline/raw/normalizer.py`
4. Records are compared against existing `pipeline/normalized/*.json`
5. Changes are classified and review items are generated

### Change classification rules

| Change Type | Auto-Accepted? | Review Item Type | Blocking? |
|-------------|---------------|-----------------|-----------|
| Unchanged record (same key, same fields) | Yes | None | N/A |
| New monster (new content_key) | No | `new_entity` | No |
| Changed requirement (quantity differs) | No | `requirement_change` | Yes |
| Changed field (name, type) | No | `field_change` | Yes |
| Missing required fields | No | `source_payload_incomplete` | Yes |
| Duplicate content_key | No | `identity_ambiguous` | Yes |
| Deprecated monster | No | `entity_deprecated` | No |

### Maintainer review process

1. After import, inspect `pipeline/curation/review_queue.json`
2. Use `python scripts/review_content.py --show` to view pending items
3. For each review item:
   - **`new_entity`**: Verify the monster exists in-game, approve the content_key
   - **`requirement_change`**: Cross-reference against game data, approve or override
   - **`identity_ambiguous`**: Create an identity override in `overrides.yaml`
   - **`source_payload_incomplete`**: Investigate the source page, add a field
     override or skip the record
4. Approve/reject items via `python scripts/review_content.py --approve <id>`
5. Once all blocking items are resolved, verify:
   `python scripts/review_content.py --check` exits 0
6. Then publish:
   `python scripts/publish_content.py --content-version <next_version>`

### Override system

Overrides are YAML entries in `pipeline/curation/overrides.yaml`. Four types:

- **Identity overrides** — force a specific `content_key` for a record
- **Field overrides** — force a specific field value (e.g., corrected name)
- **Asset overrides** — force a specific asset source/path
- **Classification overrides** — force deprecated/active status

Overrides are applied *after* normalization, preserving the original raw data
for audit trails. See `pipeline/curation/overrides.py` for the full schema.

---

## Data Contracts

### Raw payload format (fetcher output)

The wiki fetcher produces payloads matching this shape:

```json
{
  "name": "Zynth",
  "monster_type": "wublin",
  "wiki_slug": "Zynth",
  "source_url": "https://mysingingmonsters.fandom.com/wiki/Zynth",
  "image_path": "images/monsters/zynth.png",
  "is_placeholder": true,
  "asset_source": "generated_placeholder",
  "requirements": [
    {"egg_name": "Noggin", "quantity": 2},
    {"egg_name": "Mammott", "quantity": 1}
  ]
}
```

### Normalized record format (normalizer output)

The normalizer produces records matching the frozen schemas in
`pipeline/schemas/normalized.py`:

```json
{
  "content_key": "monster:wublin:zynth",
  "display_name": "Zynth",
  "monster_type": "wublin",
  "source_slug": "Zynth",
  "source_url": "https://mysingingmonsters.fandom.com/wiki/Zynth",
  "source_fingerprint": "sha256:abc123...",
  "wiki_slug": "Zynth",
  "image_path": "images/monsters/zynth.png",
  "is_placeholder": true,
  "asset_source": "generated_placeholder",
  "asset_sha256": "",
  "is_deprecated": false,
  "deprecated_at_utc": null,
  "deprecation_reason": null,
  "provenance": {
    "factual_source": "fandom",
    "retrieved_at_utc": "2026-03-22T12:00:00+00:00",
    "raw_snapshot_id": "raw-abc123def456"
  },
  "overrides_applied": []
}
```

### Review item format

```json
{
  "review_id": "auto-abc123def456",
  "issue_type": "new_entity | requirement_change | identity_ambiguous | source_payload_incomplete",
  "severity": "error | warning",
  "source_reference": "wiki/Zynth",
  "blocking": true,
  "created_at_utc": "2026-03-22T12:00:00+00:00",
  "status": "open | approved | rejected",
  "candidate_content_key": "monster:wublin:zynth",
  "proposed_resolution": "description of the issue"
}
```

---

## Source Freshness

- The importer runs **on-demand** by the maintainer, not on a schedule
- The `SourceCache` (`pipeline/raw/source_cache.py`) deduplicates by SHA-256 hash,
  so re-running the importer against unchanged wiki pages is a no-op
- Content publishes are triggered manually via `workflow_dispatch` (CI) or
  `python scripts/publish_content.py` (local)
- There is no auto-publishing — a human always reviews and triggers the publish
