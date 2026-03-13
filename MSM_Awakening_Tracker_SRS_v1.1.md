# Software Requirements Specification
## My Singing Monsters — Awakening Tracker
### Version 1.1 | Desktop Companion App

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Overall Description](#2-overall-description)
3. [Stakeholders & User Personas](#3-stakeholders--user-personas)
4. [Functional Requirements](#4-functional-requirements)
   - 4.1 Application Launch & Home Screen
   - 4.2 Monster Catalog
   - 4.3 In-Work Monsters Panel
   - 4.4 Breed List
   - 4.5 Undo / Redo System
   - 4.6 Audio Feedback
   - 4.7 Settings & Update System
   - 4.8 Database & Asset Management
5. [Non-Functional Requirements](#5-non-functional-requirements)
6. [UI & UX Requirements](#6-ui--ux-requirements)
7. [Data Model](#7-data-model)
8. [State & Logic Rules](#8-state--logic-rules)
   - 8.1 Breed List Derivation
   - 8.2 Reconciliation Check *(new in v1.1)*
   - 8.3 Clip Rule
   - 8.4 Completion vs. Silent Removal
   - 8.5 Undo/Redo — Command Objects
   - 8.6 Sort Persistence
9. [Acceptance Criteria — Reconciliation](#9-acceptance-criteria--reconciliation) *(new in v1.1)*
10. [Platform & Packaging Requirements](#10-platform--packaging-requirements)
11. [Out of Scope (v1)](#11-out-of-scope-v1)
12. [Glossary](#12-glossary)

---

## 1. Introduction

### 1.1 Purpose

This document specifies the complete functional and non-functional requirements for the **MSM Awakening Tracker** — a Windows desktop companion application for the mobile game *My Singing Monsters* (MSM). It is intended as the authoritative reference for development and testing of version 1.0.

### 1.2 Problem Statement

When working to awaken Wublins, Celestials, or Amber Vessel monsters, players must track which egg types and quantities still need to be bred across multiple simultaneous targets. The game provides no cross-island aggregate view of these requirements, forcing players to mentally track needs across 2–5 or more in-progress targets simultaneously. This results in wasted breeds (breeding eggs that are not needed) and inefficient completion.

### 1.3 Solution Summary

A lightweight, offline-first Windows desktop app that:
- Maintains a list of active awakening targets (Wublins, Celestials, Amber Vessels)
- Computes and displays a single aggregated Breed List showing exactly what the player needs to breed and in what quantity
- Allows the player to log each breed with a single click
- Automatically removes completed egg requirements from view
- Supports undo/redo for all actions

### 1.4 Scope

This document covers **version 1.0 only**. Features explicitly deferred to future versions are listed in Section 11.

### 1.5 Definitions and Acronyms

See [Section 12 — Glossary](#12-glossary).

---

## 2. Overall Description

### 2.1 Product Perspective

The app is a standalone Windows desktop application. It requires no internet connection for core functionality. An optional update mechanism connects to external sources to refresh the bundled monster database.

### 2.2 Product Functions (Summary)

| Function | Description |
|---|---|
| Monster Catalog | Browse and add awakening targets by type |
| In-Work Panel | View and manage active awakening targets |
| Breed List | Aggregated, sorted view of all eggs still needed |
| Progress Tracking | Increment bred counts per egg type via click |
| Undo / Redo | Reverse or replay any user action |
| Database Updates | Download and apply prebuilt content database updates |

### 2.3 User Characteristics

- Single user, single machine (no multi-profile support)
- Familiar with *My Singing Monsters* gameplay and awakening mechanics
- Uses the app alongside the game (not instead of it)
- Values speed and low friction — does not want to navigate deep menus

### 2.4 Constraints

- **Platform:** Windows only (v1)
- **Connectivity:** Core features fully offline; internet only required for "Check for Updates"
- **Licensing:** Must comply with Big Blue Bubble (BBB) Fan Content Policy; assets sourced only from the official BBB Fan Kit
- **Single user:** No accounts, no sync, no cloud

### 2.5 Assumptions

- The player understands MSM awakening mechanics and will accurately log their breeds manually
- A project maintainer produces and publishes prebuilt content database updates when game content changes
- BBB Fan Kit assets are available for all monsters included at launch; placeholders are acceptable for newly released monsters not yet in the Fan Kit

---

## 3. Stakeholders & User Personas

### 3.1 Primary User — Active MSM Collector

**Goal:** Efficiently awaken multiple Wublins, Celestials, and Amber Vessels simultaneously without wasting breeds.

**Behavior:** Opens the app alongside MSM, clicks an egg icon each time they breed an egg, glances at the Breed List to decide what to breed next, and occasionally adds or removes targets.

**Pain Points Addressed:**
- No longer needs to mentally track totals across multiple targets
- No longer breeds eggs they don't need
- No longer has to navigate between islands to check requirements

### 3.2 Developer / Maintainer

Maintains the bundled database, handles update scraper logic, and manages packaging. Needs a clean, documented data layer (SQLite) and a structured asset pipeline.

---

## 4. Functional Requirements

---

### 4.1 Application Launch & Home Screen

#### FR-101 — Home Screen Layout on Launch
On launch, the app shall display:
- The **Breed List** as the primary/left panel
- The **In-Work Monsters** panel as the secondary/right panel
- Navigation access to the **Monster Catalog** and **Settings**

#### FR-102 — Immediate Readability
The home screen shall present all actionable information (what to breed next, how many, current progress) without requiring any navigation, scroll-to-find, or additional interaction.

#### FR-103 — Breed List Ordering on Launch
The Breed List shall default to **descending breeding time** (longest breed at the top) on every launch and whenever the sort order is reset.

---

### 4.2 Monster Catalog

#### FR-201 — Catalog Access
The Monster Catalog shall be accessible as a distinct panel or screen from the main layout.

#### FR-202 — Catalog Organization by Type
Monsters in the catalog shall be organized into three tabs:
1. **Wublins**
2. **Celestials**
3. **Amber Vessels**

#### FR-203 — Search
The catalog shall include a text search box that filters the visible monsters in real time by name (case-insensitive, partial match).

#### FR-204 — Monster Grid Display
Each monster in the catalog shall be displayed as a grid item containing:
- Monster image (or placeholder if image unavailable)
- Monster name

#### FR-205 — Single-Click Add
Clicking a monster in the catalog shall immediately add it to the In-Work Monsters panel and trigger a Reconciliation Check to update the Breed List. No confirmation dialog is required or shown.

#### FR-206 — Add Duplicate Targets
A monster may be added to the In-Work panel multiple times (e.g., two Wublins of the same type). Each addition is a separate instance contributing its full egg requirements to the Breed List aggregate.

#### FR-207 — Catalog Completeness
The catalog shall include all regular Wublins, regular Celestials, and Amber Vessel monsters included in the bundled database at time of install, and all subsequently discovered monsters added via the update mechanism.

---

### 4.3 In-Work Monsters Panel

#### FR-301 — In-Work Panel Display
The In-Work panel shall show all currently active awakening targets.

#### FR-302 — Grouping by Type
Active monsters shall be visually grouped by type:
1. Wublins
2. Celestials
3. Amber Vessels

#### FR-303 — Duplicate Consolidation
If the same monster has been added multiple times, it shall appear as a single entry labeled `[Monster Name] × N` (e.g., `Wubbox × 2`) rather than as multiple rows.

#### FR-304 — Monster Entry Display
Each entry in the In-Work panel shall show:
- Monster image (or placeholder)
- Monster name (with `× N` if N > 1)

#### FR-305 — Mark as Awakened (Decrement)
Clicking an in-work monster entry shall:
- Decrement N by 1
- If N becomes 0, remove the entry from the In-Work panel entirely
- Trigger an automatic **Reconciliation Check** (see Section 8.2) to ensure the Breed List remains valid for the updated set of active targets

> **Design note:** Closing out a target does not *manually* edit the Breed List. Instead, the system automatically reconciles the list so it stays valid. Any egg rows that are no longer required by any remaining active target are removed silently during reconciliation. If the closed-out monster happened to be fully bred before close-out, reconciliation will confirm validity and change nothing visible.

#### FR-306 — In-Work Entry Undo/Redo
Adding and removing in-work monsters shall be fully reversible via the undo/redo system (see Section 4.5). Undo of a close-out restores the target and triggers Reconciliation to restore any Breed List rows that were removed.

---

### 4.4 Breed List

#### FR-401 — Invariant: Always Valid for Active Targets
**The Breed List shall at all times reflect only egg types required by at least one currently active target.** No orphaned rows — egg rows whose `total_needed` has fallen to zero across all active targets — may persist in the list. This invariant is enforced via the Reconciliation Check (Section 8.2), which runs automatically on every change to the active target set.

#### FR-402 — Aggregate Calculation
The Breed List shall display one row per unique egg type, where the **total needed** is the sum of that egg type's requirements across all currently active targets.

> **Example:** If Target A needs 3 Mammott eggs and Target B needs 4 Mammott eggs, the Breed List shows one Mammott row with total = 7.

#### FR-403 — Breed List Row Contents
Each row in the Breed List shall display:
- **Egg icon** (clickable — serves as the increment button)
- **Monster/egg name**
- **Breeding time** (displayed as a human-readable string, e.g., `8h 30m`)
- **Progress counter** in the format `bred / total needed` (e.g., `2 / 7`)

#### FR-404 — Egg Icon as Increment Button
The egg icon in each row is the sole increment control. There is no separate `+` button. Clicking the egg icon increments the `bred` count for that egg type by 1.

#### FR-405 — Progress Counter Behavior
- The `bred` count starts at 0 when an egg type first appears in the list
- Each click of the egg icon increments `bred` by 1
- The counter displays as `bred / total` at all times while the row is visible

#### FR-406 — Row Completion Behavior
When `bred` reaches `total needed` for a given egg type row via a player click:
1. A **"ding" audio cue** plays immediately
2. The row plays a **fast fade-out animation** and is removed from the Breed List
3. The row does **not** reappear unless a new target requiring that egg type is subsequently added (see FR-410)

#### FR-407 — No "Show Completed" Toggle
Completed rows are permanently removed from the visible Breed List. There is no toggle or option to re-display them. (Undo is the only mechanism to restore a completed row — see FR-501.)

#### FR-408 — Breed List Update on Any Target Change
Whenever the active target set changes (a monster is added or closed out), the system shall run a Reconciliation Check (Section 8.2) rather than applying manual per-row edits. Reconciliation is the **single source of truth** for all Breed List updates triggered by target changes.

> This supersedes any prior language suggesting the Breed List is "not affected" by close-out actions. The list is always reconciled; reconciliation simply confirms validity and makes no visible changes if everything was already complete.

#### FR-409 — Silent Removal vs. Ding Removal

| Trigger | Audio | Animation |
|---|---|---|
| Player clicks egg icon and `bred` reaches `total` | ✅ Ding | ✅ Fade-out |
| Reconciliation removes a row (target closed out) | ❌ No ding | Immediate/silent removal |

#### FR-410 — New Target Added After Completion
If a new awakening target is added to the In-Work panel that requires an egg type that was previously completed and removed:
- A **brand new row** is created with `bred = 0` and `total = new target's requirement`
- Prior completion state is not carried forward; there is no phantom progress

#### FR-411 — Sort Options
The Breed List shall support the following sort orders, selectable by the user:
1. **Descending breeding time** (default — longest breed first)
2. **Ascending breeding time** (shortest breed first)
3. **Remaining quantity descending** (most eggs still needed first)
4. **Name A–Z** (alphabetical by egg/monster name)

The selected sort order shall persist across sessions.

#### FR-412 — Increment Undo/Redo
All egg icon increment actions shall be fully reversible via the undo/redo system (see Section 4.5).

---

### 4.5 Undo / Redo System

#### FR-501 — Undo Keyboard Shortcut
**Ctrl+Z** shall undo the most recent user action.

#### FR-502 — Redo Keyboard Shortcuts
**Ctrl+Y** and **Ctrl+Shift+Z** shall both redo the most recently undone action.

#### FR-503 — Actions Covered by Undo/Redo
The undo/redo system shall cover **all** of the following action types:
- Adding a target monster (from the catalog)
- Closing out / removing a target monster (from the In-Work panel)
- Incrementing an egg's bred count (via egg icon click)

#### FR-504 — Undo Stack Implementation
The undo/redo system shall be implemented using the **Command pattern** — a stack of reversible state transitions. Each action is encapsulated as a command object with `execute()` and `undo()` methods.

#### FR-505 — Reconciliation as Part of Every Command
Every command that modifies the active target set (`AddTargetCommand`, `CloseOutTargetCommand`) shall execute the Reconciliation Check as an atomic part of its `execute()` and `undo()` methods. Reconciliation is not a separate step; it is embedded within the command so that undo always restores the prior valid state in a single operation.

#### FR-506 — Undo a Completion
If a row was completed (ding + removed), undoing the final egg icon increment shall:
- Restore the row to the Breed List with `bred = total - 1`
- Not replay the ding sound

#### FR-507 — Undo Stack Invalidation
Performing a new action after undoing one or more steps shall **clear the redo stack** (standard undo/redo behavior).

#### FR-508 — Undo/Redo Across Sessions
The undo/redo stack **does not** need to persist across application restarts. The stack resets on every launch.

---

### 4.6 Audio Feedback

#### FR-601 — Completion Ding
A short, pleasant audio cue ("ding") shall play when an egg row completes (bred count reaches total via player click).

#### FR-602 — No Audio on Silent Removal
No audio shall play when a row is removed due to Reconciliation (triggered by a target being closed out or removed from the In-Work panel).

#### FR-603 — Audio File
The ding sound shall be a short audio file bundled with the app. No external audio dependencies.

#### FR-604 — Audio Non-Blocking
Audio playback shall be non-blocking and shall not delay any UI state change or animation.

---

### 4.7 Settings & Update System

#### FR-701 — Settings Screen
The app shall include a Settings screen accessible from the main navigation. It shall contain:
- **Check for Updates** button
- Current database version / last updated timestamp
- **BBB Fan Content Policy disclaimer** (see FR-706)

#### FR-702 — Check for Updates Trigger
The update process shall only run when explicitly triggered by the user via the "Check for Updates" button. It does not run automatically on launch.

#### FR-703 — Update Process: Content Database Replacement
The update process shall:
1. Fetch a manifest from a known remote URL describing the available content database version
2. If a newer version is available, download the prebuilt `content.db` artifact
3. Validate the downloaded database (schema, row counts, metadata)
4. Replace the local `content.db` with the validated download

> **Scope note (v1):** New monster discovery, requirement changes, and image updates are performed by the project maintainer in a content-production pipeline. The desktop client receives these changes as a prebuilt `content.db` package. The client does not scrape external sources or download individual assets at runtime.

#### FR-704 — Update Process: Post-Update Finalization
After a successful content database replacement, the app shall:
1. Reopen the content database connection and rebind all dependent services
2. Run a reconciliation pass against the updated content to clip or remove invalid user progress
3. Clear the undo/redo history (stale commands may reference outdated content)
4. Refresh all UI panels to reflect the new content immediately, without requiring a restart

#### FR-705 — Bundled Assets as v1 Media Source
- All monster images, egg icons, and UI assets are bundled at install time and sourced exclusively from the official BBB Fan Kit
- The v1 update process replaces content data only; it does not download or replace image assets at runtime
- Placeholder images are used where Fan Kit assets are not yet available at build time
- Updated media is delivered in subsequent application releases (new installer builds), not via the in-app update mechanism

#### FR-706 — BBB Disclaimer (Required)
The Settings/About section shall display the following (or substantially equivalent) disclaimer:

> *This app is an unofficial fan creation and is not affiliated with, endorsed by, or sponsored by Big Blue Bubble Inc. All My Singing Monsters assets used in this app are sourced from the official Big Blue Bubble Fan Kit and are used in accordance with the BBB Fan Content Policy. My Singing Monsters is a trademark of Big Blue Bubble Inc.*

#### FR-707 — Update Failure Handling
If the update process fails (network unavailable, download error, validation failure, replacement error), the app shall:
- Display a user-friendly error message indicating the update could not be completed
- Leave the existing local database untouched (restore from backup if replacement was attempted)
- Allow the user to retry

#### FR-708 — No Auto-Update
There shall be no automatic or background update process. Updates are always manually triggered.

---

### 4.8 Database & Asset Management

#### FR-801 — Bundled Database
The app shall ship with a complete SQLite database containing all monster records, egg requirement data, breeding times, and image asset references at the time of packaging.

#### FR-802 — Offline Operation
All core app functionality (Breed List, In-Work panel, Monster Catalog, progress tracking) shall work fully offline without any network access.

#### FR-803 — No User Editing of Database
The database is read-only from the user's perspective. No UI shall be provided for editing monster data, requirements, or breeding times.

#### FR-804 — Bundled Assets
All monster images, egg icons, and UI assets shall be bundled inside the app at install time. The app shall not fetch assets at runtime during normal operation.

#### FR-805 — Database Versioning
The database shall include a version/schema version field and a last-updated timestamp, visible in the Settings screen.

#### FR-806 — Single-Machine, Single-User Storage
All user state (current in-work monsters, bred counts, sort preference) shall be stored locally in a SQLite file on the user's machine. No cloud storage, no sync.

---

## 5. Non-Functional Requirements

### 5.1 Performance

| Requirement | Target |
|---|---|
| Application startup time | < 3 seconds on modern hardware |
| Egg icon click → counter update | < 100ms (imperceptible) |
| Reconciliation + Breed List re-render on target add/remove | < 200ms |
| Update scraper completion time | < 60 seconds for a full refresh under normal network conditions |

### 5.2 Reliability

- **NFR-201:** App shall not lose user state (in-work monsters, bred counts) on crash or unexpected close. State shall be persisted to SQLite after every user action.
- **NFR-202:** Undo/redo stack shall be consistent at all times; no action shall result in an invalid state (e.g., `bred > total`, negative counts, orphaned Breed List rows).

### 5.3 Usability

- **NFR-301:** All primary actions (incrementing an egg, adding a target, viewing the breed list) shall be reachable within 1–2 interactions from the home screen.
- **NFR-302:** The Breed List shall be legible at a glance without requiring horizontal scrolling at 1080p resolution.
- **NFR-303:** Keyboard shortcuts (Ctrl+Z, Ctrl+Y, Ctrl+Shift+Z) shall work whenever the main window is in focus, regardless of which UI element is focused.

### 5.4 Maintainability

- **NFR-401:** The database schema shall be versioned to support non-destructive migrations on update.
- **NFR-402:** Monster data (requirements, images, names) shall be cleanly separated from application logic to simplify updates.
- **NFR-403:** The update scraper shall be modular and independently testable.
- **NFR-404:** The Reconciliation Check shall be implemented as a single, reusable function callable from any command's `execute()` or `undo()` method.

### 5.5 Compatibility

- **NFR-501:** The app shall run on Windows 10 (64-bit) and Windows 11 without additional dependencies beyond those bundled by the installer.
- **NFR-502:** The app shall not require administrator privileges for normal operation (post-install).

### 5.6 Accessibility (Baseline)

- **NFR-601:** All interactive controls shall have visible focus states.
- **NFR-602:** Text shall meet a minimum contrast ratio of 4.5:1 against backgrounds (WCAG AA).

---

## 6. UI & UX Requirements

### 6.1 Overall Visual Style

- **Theme:** Dark, polished, modern — not flat black minimal. Think soft dark backgrounds with layered card surfaces, subtle shadows, and accent colors drawn from the MSM aesthetic.
- **Density:** Spacious and readable. Not data-dense. Each row in the Breed List should feel like a card, not a spreadsheet cell.
- **Imagery:** Monster and egg images are first-class UI elements, not decorative afterthoughts. They provide at-a-glance identification without reading names.

### 6.2 Layout

```
┌─────────────────────────────────────────────────────────────┐
│  [Nav: Home]  [Catalog]  [Settings]              [App Logo] │
├──────────────────────────────┬──────────────────────────────┤
│                              │                              │
│         BREED LIST           │     IN-WORK MONSTERS         │
│   (primary / left panel)     │   (secondary / right panel)  │
│                              │                              │
│  [egg icon] Mammott   8h 30m │  — Wublins ————————————     │
│             ████░░░  3 / 7   │   [img] Wubbox × 2          │
│                              │   [img] Ziggurab            │
│  [egg icon] Tweedle   1h 00m │                              │
│             █░░░░░░  1 / 6   │  — Celestials ——————————    │
│                              │   [img] Galvana             │
│  ...                         │                              │
│                              │  — Amber Vessels ———————    │
│                              │   [img] Ambered Wubbox      │
└──────────────────────────────┴──────────────────────────────┘
```

### 6.3 Breed List Row Design

Each row shall contain (left to right):
1. **Egg icon** — prominent, visually distinct, clickable (entire icon area is the hit target)
2. **Monster/egg name** — medium weight text
3. **Breeding time** — secondary/muted text
4. **Progress counter** — `bred / total`, right-aligned, with a subtle progress bar or fill indicator to convey completion at a glance

### 6.4 In-Work Panel Design

- Monsters displayed as cards or rows with image + name
- Grouped sections (Wublins / Celestials / Amber Vessels) with clear visual separators
- `× N` badge displayed inline when N > 1
- Clicking an entry should have a visible "press" or active state before removal

### 6.5 Monster Catalog Design

- Tab bar for Wublins / Celestials / Amber Vessels
- Search box at top, filters in real time
- Grid layout of monster cards (image + name)
- Single click adds to In-Work — a brief visual confirmation (highlight flash or checkmark overlay) is desirable but not required in v1

### 6.6 Animations & Micro-Interactions

| Interaction | Behavior |
|---|---|
| Egg icon click | Brief press/scale-down animation on the icon; counter increments |
| Row completion (player-triggered) | Ding audio + fast fade-out (recommended: ~300ms opacity fade) |
| Target monster close-out (In-Work) | Brief visual confirmation on click (active state) |
| Row removed by Reconciliation | Immediate or very fast removal, no audio |

### 6.7 Window Sizing

- The app shall have a sensible minimum window size (recommend 900×600px) below which layout does not break
- The app shall be resizable; panels may scale proportionally

---

## 7. Data Model

### 7.1 Monster Table

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Internal ID |
| `name` | TEXT | Display name |
| `type` | TEXT | `wublin`, `celestial`, `amber` |
| `image_path` | TEXT | Path to bundled image asset |
| `is_placeholder` | BOOLEAN | True if using initials placeholder |
| `wiki_slug` | TEXT | Fandom wiki page slug for update lookups |

### 7.2 Egg Type Table

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Internal ID |
| `name` | TEXT | Display name (e.g., "Mammott") |
| `breeding_time_seconds` | INTEGER | Used for sorting |
| `breeding_time_display` | TEXT | Human-readable (e.g., "8h 30m") |
| `egg_image_path` | TEXT | Path to bundled egg icon |

### 7.3 Monster Requirements Table

| Column | Type | Description |
|---|---|---|
| `monster_id` | INTEGER FK → Monster | The awakening target |
| `egg_type_id` | INTEGER FK → Egg Type | Required egg type |
| `quantity` | INTEGER | How many of this egg are needed |

### 7.4 Active Targets Table (User State)

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Row ID |
| `monster_id` | INTEGER FK → Monster | Which monster |
| `added_at` | DATETIME | When added (for ordering) |

### 7.5 Breed Progress Table (User State)

| Column | Type | Description |
|---|---|---|
| `egg_type_id` | INTEGER FK → Egg Type | Which egg type |
| `bred_count` | INTEGER | How many have been bred so far |

> **Note:** `bred_count` tracks the raw accumulated bred eggs across all sources. The Reconciliation Check (Section 8.2) enforces that `bred_count` never exceeds `total_needed`, and removes progress rows for egg types no longer required by any active target.

### 7.6 App Settings Table

| Column | Type | Description |
|---|---|---|
| `key` | TEXT PK | Setting name |
| `value` | TEXT | Setting value |

Tracked settings: `breed_list_sort_order`, `db_version`, `db_last_updated`.

---

## 8. State & Logic Rules

### 8.1 Breed List Derivation

The rendered Breed List is always derived live from the current database state as follows:
1. Retrieve all active targets from the Active Targets table
2. For each active target, retrieve egg requirements from the Monster Requirements table
3. Group by `egg_type_id`; sum quantities → `required_totals[egg_type_id]`
4. For each egg type in `required_totals`, retrieve `bred_count` from the Breed Progress table (default 0 if absent)
5. Compute `remaining = required_totals[egg_type_id] - bred_count`
6. Render only rows where `remaining > 0`
7. Apply the user's selected sort order

---

### 8.2 Reconciliation Check *(new in v1.1)*

**Purpose:** Enforce the invariant that the Breed List is always valid for the current set of active targets. No orphaned rows — egg requirements belonging to no remaining active target — may exist.

**Invariant:** For every `egg_type_id` with a row in the Breed List (or a `bred_count` entry in the Breed Progress table), there must be at least one active target that requires that egg type.

#### Trigger Events

Reconciliation shall run automatically — as an atomic part of the triggering operation — whenever:

| Event | Notes |
|---|---|
| Target monster added to In-Work | New egg rows may need to appear |
| Target monster closed out / decremented to zero | Egg rows may become orphaned |
| Undo or Redo of any target add/close-out | Embedded in the command's `undo()` / `execute()` |
| *(Optional)* Data update changes monster requirements | Run once after the update completes |

#### Reconciliation Algorithm

```
function reconcile():
    required_totals = {}
    for each active_target in ActiveTargets:
        for each (egg_type_id, qty) in Requirements[active_target.monster_id]:
            required_totals[egg_type_id] += qty

    for each (egg_type_id, bred_count) in BreedProgress:
        if egg_type_id NOT IN required_totals OR required_totals[egg_type_id] == 0:
            # Egg type no longer required by any active target — purge it
            DELETE BreedProgress WHERE egg_type_id = egg_type_id
        else:
            # Clip bred_count if it exceeds new total
            new_total = required_totals[egg_type_id]
            if bred_count > new_total:
                UPDATE BreedProgress SET bred_count = new_total WHERE egg_type_id = egg_type_id

    # UI re-renders Breed List from derivation (Section 8.1)
```

#### UX Behavior During Reconciliation

- All removals and clips caused by Reconciliation are **silent**: no ding audio, no fade animation
- The Breed List simply re-renders with the updated valid state
- Reconciliation completes within the same UI frame as the triggering action (no visible delay)

---

### 8.3 Clip Rule

During Reconciliation, if `bred_count` for any egg type would exceed the new `required_totals[egg_type_id]` (possible when a target is closed out), the `bred_count` is clipped:

```
bred_count = min(bred_count, required_totals[egg_type_id])
```

After clipping, if `remaining = required_totals - bred_count = 0`, the row is not displayed (but the progress entry is retained in case the total is later restored via undo). If `required_totals` drops to 0 entirely (no active target requires the egg type), the progress entry is deleted entirely.

---

### 8.4 Completion vs. Silent Removal

| Condition | Trigger | Audio | Animation |
|---|---|---|---|
| Player clicks egg icon; `bred` reaches `total` | Player action | ✅ Ding | ✅ Fade-out (~300ms) |
| Reconciliation removes/clips a row (target closed out or undone) | System action | ❌ None | ❌ Immediate/silent |

This distinction is absolute. The ding and fade-out are reserved exclusively for player-driven completion. Reconciliation-driven removals are always silent.

---

### 8.5 Undo/Redo — Command Objects

Each command object shall implement:
- `execute()` — performs the action, persists state to DB, runs Reconciliation if applicable
- `undo()` — reverses the action, restores prior DB state, runs Reconciliation if applicable

**Commands:**

| Command | execute() | undo() |
|---|---|---|
| `AddTargetCommand(monster_id)` | Insert into ActiveTargets; run Reconciliation | Delete from ActiveTargets; run Reconciliation |
| `CloseOutTargetCommand(active_target_id)` | Delete from ActiveTargets; run Reconciliation | Re-insert into ActiveTargets; run Reconciliation |
| `IncrementEggCommand(egg_type_id)` | Increment `bred_count` by 1; check for player-completion | Decrement `bred_count` by 1; restore row if it was completed |

> **Note:** `IncrementEggCommand` does **not** run Reconciliation — it only modifies a `bred_count` and does not change the active target set.

---

### 8.6 Sort Persistence

The selected sort order is saved to the App Settings table immediately on change and reloaded on every launch.

---

## 9. Acceptance Criteria — Reconciliation

The following scenarios shall pass in testing to confirm correct Reconciliation behavior.

### AC-R01 — Close-out removes orphaned rows

**Setup:** Two active targets (A, B) both require Mammott eggs. Only target A requires Tweedle eggs.

**Action:** Close out target A.

**Expected:**
- Target A is removed from the In-Work panel
- The Mammott row remains (target B still requires it) with `total` reduced by A's Mammott requirement
- The Tweedle row is removed silently (no ding, no fade)
- No Tweedle progress entry remains in the database

---

### AC-R02 — No orphaned rows after close-out

**Setup:** Any number of active targets.

**Action:** Close out any target.

**Expected:**
- Every egg row remaining in the Breed List is required by at least one remaining active target
- There are no rows for egg types with `total_needed = 0`

---

### AC-R03 — bred_count clipped correctly

**Setup:** Target A requires 5 Mammott eggs. Player has bred 5 (row completed and removed). Target B also requires 3 Mammott (adding B created a fresh row; player bred 2/3).

**Action:** Close out target B while target A is still active.

**Expected:**
- Mammott row remains (target A still needs 5)
- `total_needed` is now 5 (from A only); `bred_count` is 2 (from the last B-era progress); `remaining` = 3
- Row is visible and correct; no clipping was needed since `bred_count` (2) < `total_needed` (5)

---

### AC-R04 — Ctrl+Z restores complete prior state atomically

**Setup:** Active targets exist with a valid Breed List. Close out one target, which causes Reconciliation to remove one or more egg rows.

**Action:** Press Ctrl+Z.

**Expected:**
- The closed-out target is restored to the In-Work panel
- All Breed List rows removed by Reconciliation are restored with their prior `bred_count` values
- The Breed List is identical to its pre-close-out state
- The undo is atomic — no intermediate invalid state is visible to the user

---

### AC-R05 — bred_count ≤ total_needed invariant holds at all times

**Invariant check (applies after every operation):**
- For every egg type in the Breed List: `bred_count ≤ total_needed`
- This shall hold after adds, close-outs, increments, and undo/redo of any action

---

### AC-R06 — No ding on Reconciliation removal

**Setup:** Target A requires Tweedle eggs. Player has bred 1/6 Tweedle (partial progress).

**Action:** Close out target A (Tweedle row becomes orphaned).

**Expected:**
- Tweedle row is removed immediately and silently
- No ding audio plays
- No fade-out animation plays

---

## 10. Platform & Packaging Requirements

### 10.1 Target Platform

- **OS:** Windows 10 (64-bit) and Windows 11
- **Architecture:** x86-64

### 10.2 Tech Stack

| Component | Technology |
|---|---|
| UI Framework | Python + PySide6 |
| Local Storage | SQLite (via Python `sqlite3` or SQLAlchemy) |
| Undo/Redo | Command pattern (custom implementation) |
| Audio Playback | PySide6 `QSoundEffect` or `QMediaPlayer` |
| Packaging | PyInstaller (single-dir or onefile) |
| Installer | Inno Setup or NSIS |
| Content Updater | Manifest-driven content DB download and replacement |

### 10.3 Installation

- Standard Windows installer (`.exe`)
- Installs to `%ProgramFiles%\MSM Awakening Tracker\` by default
- User data (SQLite state DB) stored in `%APPDATA%\MSMAwakeningTracker\`
- App does not require administrator privileges post-install

### 10.4 Portable Version

Not required in v1. Standard installer only.

### 10.5 Dependencies

All Python dependencies and PySide6 runtime shall be bundled by PyInstaller. The end user shall not need to install Python or any runtime separately.

### 10.6 App Icon

A custom app icon (`.ico`) shall be provided for the Windows taskbar, window title bar, and Start Menu shortcut.

---

## 11. Out of Scope (v1)

The following features are explicitly excluded from version 1.0:

| Feature | Notes |
|---|---|
| Rare / Epic Wublins | May be added in a future version |
| Celestial Ascension (monthly adult upgrades) | Future version |
| Awakening timers or expiry notifications | In-game UI handles this |
| Breeding optimization suggestions or strategy | Out of scope by design |
| Multi-user profiles | Single user only |
| User-editable monster database | Read-only |
| Show Completed toggle | Completed rows are permanently removed |
| Backlog / future planning features | Active tracker only |
| Portable app (.zip) | Standard installer only |
| macOS / Linux support | Windows only |
| Cloud sync or backup | Local storage only |
| In-app purchases or monetization | Fan app, non-commercial |

---

## 12. Glossary

| Term | Definition |
|---|---|
| **Awakening** | The process of zapping the required eggs into a sleeping Wublin, Celestial, or Amber Vessel to bring it to life |
| **Zapping** | The in-game action of sending a bred egg from a breeding structure to a target monster |
| **Wublin** | A class of monsters in MSM that require specific eggs zapped into a statue to awaken |
| **Celestial** | A class of powerful MSM monsters awakened via the same egg-zapping mechanic as Wublins |
| **Amber Vessel** | A limited-availability class of monsters awakened by zapping eggs into a purchased Vessel |
| **Breed List** | The aggregated, real-time list of egg types and quantities the player still needs to breed across all active targets; always valid for the current active target set |
| **In-Work Monsters** | The set of awakening targets the player is currently filling with eggs |
| **Close out / Mark as Awakened** | The action of clicking an In-Work monster to decrement its count, signaling the player has fully awakened one instance; triggers Reconciliation |
| **Egg type** | A specific monster variant whose egg is used in awakening (e.g., Mammott, Tweedle) |
| **Bred count** | The number of a given egg type the player has bred and logged in the app so far |
| **Total needed** | The sum of a given egg type's requirements across all active targets |
| **Remaining** | `total_needed - bred_count`; the number of eggs of a given type still to breed |
| **Orphaned row** | A Breed List row (or progress entry) for an egg type no longer required by any active target; always eliminated by the Reconciliation Check |
| **Reconciliation Check** | The system process that recomputes valid egg totals from active targets and removes or clips any invalid Breed List entries; runs automatically on every change to the active target set |
| **Silent removal** | Removal of a Breed List row without ding audio or fade animation; occurs during Reconciliation, never during player-triggered completion |
| **Command pattern** | A software design pattern encapsulating actions as objects with `execute()` and `undo()` methods, enabling undo/redo |
| **BBB** | Big Blue Bubble Inc., the developer of *My Singing Monsters* |
| **Fan Kit** | The official asset pack released by BBB for fan content use |
| **Placeholder** | A substitute image (egg silhouette + initials) used when a real monster image is not yet available |

---

*Document Version: 1.1*
*v1.1 Changes: Added Reconciliation Check invariant and algorithm (Section 8.2); added Acceptance Criteria section (Section 9); rewrote FR-305 to trigger Reconciliation on close-out; added FR-401 (Breed List invariant) and FR-408 (Reconciliation as single source of truth); updated FR-505 (Reconciliation embedded in commands); updated NFR-202 and NFR-404; added "Orphaned row", "Reconciliation Check", and "Close out" to Glossary; renumbered Sections 9–12.*
*Based on: MSM Companion App Vision & Q&A Document + Reconciliation Change Request*
*Status: Draft — Ready for Development Review*
