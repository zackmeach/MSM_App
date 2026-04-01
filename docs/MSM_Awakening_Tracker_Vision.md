# MSM Awakening Tracker: Vision & Q&A Document

## Overview

A lightweight Windows desktop companion app for *My Singing Monsters* that helps players efficiently track and manage the egg-filling process for **Amber Vessels**, **sleeping Wublins**, and **sleeping Celestials**. The app solves a specific pain point: players currently have to mentally track which eggs they need across multiple in-progress monsters, bouncing between islands and trying to memorize requirements. This app eliminates that friction.

---

## Background: How Awakening Works in MSM

Understanding the three awakening systems this app supports:

- **Wublins:** Place a Wublin statue, then "zap" the required eggs into it from your breeding structures. Each Wublin has a specific set of egg types and quantities needed. A timer starts on first zap, but this app does not track timers.
- **Celestials:** Purchase a Dormant Celestial using Keys, then revive it by zapping the required eggs. Same zapping mechanic as Wublins. This app tracks regular Celestials only (not Ascension/adult upgrades).
- **Amber Vessels:** Purchase a Vessel using Relics, then zap required eggs into it. Most Vessels are limited-time. This app tracks standard Amber monsters only.

The common thread across all three: the player needs to breed specific egg types in specific quantities and zap them into the target monster. This app helps players track exactly what they still need to breed.

---

## Project Intentions & Goals

The app should help the player:

- **(B) Minimize wasted breeds/eggs** — never breed something you don't need
- **(C) Optimize completion speed** — know at a glance what to breed next
- **(D) Serve as a clean checklist tracker** — simple, clear, no clutter

The app should **not**:

- Track timers or send notifications (the in-game UI already handles timers)
- Offer breeding optimization suggestions or strategy advice
- Support rare/epic Wublins, Celestial Ascension, or any special-case variants (v1 scope only)
- Support multiple user profiles (single user, single machine)

---

## Questions & Answers

### SCOPE

**Q: Should the app track only active projects, or also a full backlog/planner?**

> The user selects a monster they want to start working on, which adds that monster and its egg requirements to the active tracker. No backlog or future planning features.

**Q: Should Celestial Ascension (monthly adult upgrades) be included?**

> No. This first version is for regular Celestials, regular Wublins, and Amber Vessels only. Special cases may be added in a future version.

---

### USER WORKFLOW

**Q: What should the home screen communicate immediately on launch?**

> A list of monsters that need to be bred, organized by descending breeding time. Also visible: the list of in-work target monsters (the Wublins/Celestials/Ambers currently being filled).

**Q: Does the player work on multiple targets simultaneously?**

> Yes — typically 2 to 5 at once. The app must handle this gracefully, including working on multiple copies of the same target monster.

**Q: Should the app support multiple user profiles?**

> No. Single user, single computer.

---

### DATA ENTRY & PROGRESS TRACKING

**Q: Should progress updates be manual or automated?**

> Manual only. No screenshots, no OCR, no import.

**Q: How does the user log progress?**

> Each egg type in the Breed List has a clickable **egg icon** as its increment button. The user clicks the egg icon for a monster when they breed one. The counter increments by 1 (e.g., `2/7`). There is no separate `+` button — the egg image itself is the button.

**Q: Should accidental increments be reversible?**

> Yes. **Ctrl+Z** undoes the last action. **Ctrl+Y** and **Ctrl+Shift+Z** both redo it. Undo/redo applies to all actions: adding a target monster, removing a target monster, and incrementing egg progress. For actions that modify the active target set (adds and close-outs), Reconciliation is embedded atomically inside the undo and redo operations — undoing a close-out restores the target and all affected Breed List rows in a single step.

---

### WHAT IS TRACKED PER EGG IN THE BREED LIST

Each egg entry in the Breed List shows:

- Egg icon (clickable — acts as the increment button)
- Monster/egg name
- Breeding time (used for sorting)
- Progress counter: `bred / total needed` (e.g., `2/7`)

What is **not** shown or tracked:

- Timers or expiry countdowns
- Remaining quantity as a separate field (visible via the counter)
- Notes or strategy fields
- Breeding structure capacity or throughput

---

### BREED LIST BEHAVIOR

**Q: How does aggregation work across multiple active targets?**

> The Breed List is a **global sum** across all active projects. If two in-work monsters both require Mammott eggs, the totals are added together into a single Mammott row.

**Q: What happens when an egg's bred count reaches the total needed?**

> The row plays a **"ding" audio cue** and **immediately disappears** from the list. There is no "show completed" toggle. Completed entries are gone.

**Q: What happens to completed entries if a new target monster is added that requires the same egg?**

> A brand new entry is created with `bred = 0` and the new total. Completion is final — there is no phantom progress carried forward.

**Q: What happens to the Breed List when an in-work monster is dismissed (marked as awakened)?**

> Dismissing an in-work monster triggers a **Reconciliation Check**. The system recomputes valid egg totals from the remaining active targets and removes any rows for egg types no longer required by any of them — silently, with no ding and no animation. If the dismissed monster was already fully bred, Reconciliation confirms validity and nothing visible changes. The Breed List is always valid for the current active target set.

> **Resolved edge case:** If a player accidentally adds a monster and removes it before breeding any eggs, Reconciliation handles this automatically — any egg rows that were added for that monster and are not required by any other active target are silently purged. No orphaned rows are ever left behind. The player can also press Ctrl+Z to undo the add entirely and restore the prior state.

---

### IN-WORK MONSTERS

**Q: What does the in-work list look like?**

> A panel showing the target monsters currently being filled. If the same monster has been added multiple times, it shows as `Monster Name × N` rather than as duplicate rows.

**Q: How does the player mark a monster as awakened/complete?**

> They click the in-work monster. This decrements N by 1 (or removes the entry entirely if N was 1). This action triggers an automatic **Reconciliation Check**, which recomputes the Breed List against the updated active target set. Any egg rows no longer required by any remaining active target are removed silently (no ding, no animation). If the closed-out monster was already fully bred before close-out, Reconciliation simply confirms validity and nothing visible changes.

---

### SORTING & FILTERING

**Q: How should the Breed List be sorted?**

> Default: **descending breeding time** (longest breed first). Additional sort options: ascending breeding time, remaining quantity descending, name A–Z.

**Q: Should there be filtering options?**

> Basic sorting and filtering only. Default sort is descending breeding time. Additional sort options (e.g., ascending breeding time, remaining count, name A–Z) are reasonable additions. No optimization filters, no island-availability filters, and no "show completed" toggle — completed rows vanish automatically, so this toggle has no purpose.

---

### DATABASE & UPDATES

**Q: Should the app ship with a built-in database or rely on external sources?**

> The app ships with a **complete built-in database** (all monster requirements, breeding times, and images included at install). No internet connection is needed to use the app.

**Q: Can users manually edit the database?**

> No. The database is not user-editable.

**Q: How does the database stay current?**

> Settings includes a **"Check for Updates"** option. When triggered, the app:
> 
> 1. Checks a remote manifest for a newer content database version
> 2. Downloads and validates the prebuilt `content.db` package
> 3. Replaces the local content database and finalizes in-process (reconnects, reconciles user state, refreshes UI)

> New monster discovery, requirement changes, and image updates are handled by the project maintainer in a content-production pipeline. The desktop client receives these changes as a prebuilt database package. This supports new monster discovery without requiring the installed app to scrape external sources.

---

### IMAGES & ASSETS

**Q: What is the image/icon strategy?**

> All icons and images ship **inside the app at install time**. Egg icons appear in the Breed List as the increment button. Monster images appear in the in-work panel and the monster catalog.

**Q: Where do assets come from?**

> Official BBB Fan Kit assets where available. Where not available (e.g., newly released monsters not yet in the Fan Kit), a placeholder (egg silhouette + initials) is used until the next update adds the real asset.

**Q: What about copyright/licensing?**

> The app must comply with Big Blue Bubble's Fan Content Policy, which permits non-commercial fan apps using assets only from their official Fan Kit. A required BBB disclaimer must appear in the app's Settings/About section.

---

### UI & UX DESIGN

**Q: What is the overall UI style?**

> Modern and minimalistic with a **dark-ish theme** (not a flat black minimal look — more polished and designed). Monster and egg images are used throughout for at-a-glance clarity. Not dense/data-heavy — spacious and modern.

**Q: What is the general layout?**

> - **Left/primary:** Breed List (egg rows with progress counters, sorted by breeding time)
> - **Right/secondary:** In-Work Monsters panel (grouped by type — Wublin / Celestial / Amber)
> - **Separate panel or screen:** Monster Catalog (tabs by type, search box, grid of monsters to click-to-add)
> - **Settings screen:** Check for Updates, DB version info, disclaimer

**Q: What micro-interactions matter?**

> - Clicking an egg icon increments its counter
> - When a row completes (player-driven): ding sound + fast fade-out animation
> - When a row is removed by Reconciliation (close-out-driven): immediate silent removal, no ding, no animation
> - Ctrl+Z / Ctrl+Y / Ctrl+Shift+Z for undo/redo across all actions
> - Clicking an in-work monster decrements or removes it, and triggers Reconciliation

**Q: Any specific usability requirements?**

> - Adding a monster from the catalog should be a single click
> - Undo/redo must work reliably for every user action
> - The Breed List should be immediately readable without any navigation

---

### PLATFORM & PACKAGING

**Q: What OS is targeted?**

> Windows only (v1).

**Q: What does "lightweight" mean here?**

> The app is simple in concept — it does a few things and does them well. Fast startup, low resource use, clean UX. Not about installer file size specifically.

**Q: Standard install or portable?**

> Standard install.

---

## MVP Scope Summary

| Feature                                          | In v1 |
| ------------------------------------------------ | ----- |
| Wublin tracking (regular only)                   | ✅     |
| Celestial tracking (regular only)                | ✅     |
| Amber Vessel tracking                            | ✅     |
| Rare/Epic Wublins                                | ❌     |
| Celestial Ascension                              | ❌     |
| Aggregate Breed List with progress counters      | ✅     |
| Egg icon as increment button                     | ✅     |
| Ding + disappear on completion                   | ✅     |
| Ctrl+Z / Ctrl+Y undo/redo                        | ✅     |
| Multiple simultaneous targets                    | ✅     |
| Duplicate target tracking (× N)                  | ✅     |
| In-work monster panel                            | ✅     |
| Monster catalog (by type, searchable)            | ✅     |
| Built-in asset pack                              | ✅     |
| Check for Updates (content DB replacement)        | ✅     |
| Timers / notifications                           | ❌     |
| Breeding optimization suggestions                | ❌     |
| Multi-user profiles                              | ❌     |
| User-editable database                           | ❌     |
| Show completed toggle                            | ❌     |

---

## Suggested Tech Stack

- **UI Framework:** Python + PySide6 (modern, clean, Windows-compatible)
- **Local Storage:** SQLite (single file, supports versioning and queries)
- **Undo/Redo:** Command pattern (stack of reversible state transitions)
- **Packaging:** PyInstaller + Windows installer (Inno Setup or MSI)
- **Content Updater:** Manifest-driven content DB download and replacement; media bundled at install time
