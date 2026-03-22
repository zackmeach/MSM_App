---
name: home ui foundation
overview: Implement a desktop-first Home screen foundation in the existing PySide6 app by rebuilding the Home page layout/components, refining the top navigation shell, and establishing reusable dark-theme styling while preserving current AppService-driven behavior.
todos:
  - id: refresh-app-shell
    content: Refine `main_window.py` nav shell and shared dark-theme stylesheet to establish the reusable desktop foundation.
    status: completed
  - id: rebuild-home-layout
    content: Rework `home_view.py`, `breed_list_panel.py`, and `inwork_panel.py` into the new two-column Home composition with polished empty/populated states.
    status: completed
  - id: refine-home-widgets
    content: Redesign `egg_row_widget.py` and right-rail entry widgets so the UI matches the mockup direction while preserving current interaction contracts.
    status: completed
  - id: preserve-routing-state
    content: Keep Home/Catalog/Settings stack behavior and add the empty-state CTA route to Catalog without breaking `AppService` refresh flows.
    status: completed
  - id: update-smoke-tests
    content: Adjust GUI smoke tests for the new widget structure and verify the core Home interactions still pass.
    status: completed
isProject: false
---

# Home UI Foundation Plan

## Integration Points

- Keep the existing app shell in [C:/MSM_App/app/ui/main_window.py](C:/MSM_App/app/ui/main_window.py), which already owns the top nav, `QStackedWidget`, and service wiring for Home / Catalog / Settings.
- Rework the Home page internals in [C:/MSM_App/app/ui/home_view.py](C:/MSM_App/app/ui/home_view.py) so the page feels like the mockup without changing the overall app architecture.
- Preserve the current state flow from [C:/MSM_App/app/services/app_service.py](C:/MSM_App/app/services/app_service.py) and [C:/MSM_App/app/ui/viewmodels.py](C:/MSM_App/app/ui/viewmodels.py) so real data can replace placeholders cleanly.

## Planned Changes

- Update [C:/MSM_App/app/ui/main_window.py](C:/MSM_App/app/ui/main_window.py) to make the desktop shell visually closer to the mockup:
  - move the app title/logo area to the left of the nav row
  - keep `Home`, `Catalog`, `Settings` as the primary nav items
  - add a real active-state treatment for the current page
  - tighten page margins/max width so the main content reads as a centered desktop workspace
  - expand the shared stylesheet into reusable surface, spacing, button, focus, and typography primitives
- Rebuild [C:/MSM_App/app/ui/home_view.py](C:/MSM_App/app/ui/home_view.py) as a page container rather than a bare splitter wrapper:
  - outer desktop page padding/max width
  - two-column layout with a dominant left `Breed List` panel and narrower right `In-Work Monsters` panel
  - responsive behavior that stays desktop-first and only compresses when the window is narrow
- Refactor [C:/MSM_App/app/ui/breed_list_panel.py](C:/MSM_App/app/ui/breed_list_panel.py) into a richer panel shell:
  - header/title treatment matching the mockup tone
  - polished empty state with icon/illustration zone, explanatory copy, and CTA routed to Catalog
  - populated list state that keeps the current sort behavior and service signal contract
- Replace or significantly redesign [C:/MSM_App/app/ui/widgets/egg_row_widget.py](C:/MSM_App/app/ui/widgets/egg_row_widget.py) so each row reads like the future increment control:
  - egg icon area clearly looks interactive
  - name, breeding time, `bred / total`, and progress indicator are laid out as a reusable row component
  - keep the important existing behavior where the egg icon itself is the increment interaction, not a separate plus button
- Refactor [C:/MSM_App/app/ui/inwork_panel.py](C:/MSM_App/app/ui/inwork_panel.py) into grouped secondary sections:
  - `Wublins`, `Celestials`, and `Amber Vessels` always render as clear sections
  - each section supports both empty placeholder text and populated placeholder/real entries
  - visual weight stays secondary relative to the Breed List panel
- Replace or adapt [C:/MSM_App/app/ui/widgets/monster_card.py](C:/MSM_App/app/ui/widgets/monster_card.py) for the right rail so in-work entries feel like compact list cards rather than catalog tiles.
- Add small reusable UI pieces under [C:/MSM_App/app/ui/widgets/](C:/MSM_App/app/ui/widgets/) only where it meaningfully reduces duplication, such as:
  - a shared panel container/header widget
  - a reusable primary button style/widget if QSS alone becomes awkward
  - section widgets for in-work groups

## Data / State Strategy

- Continue using real `AppService` state for normal Home rendering.
- Extend view models in [C:/MSM_App/app/ui/viewmodels.py](C:/MSM_App/app/ui/viewmodels.py) only if the new UI needs explicit display metadata such as subtitle text, section empty-copy, or richer placeholder entry data.
- Use local/mock placeholder content only for visual fallback states where the UI needs a believable populated example, while keeping the empty-state path intact and not interfering with real DB-backed state.
- Add a direct signal from the Breed List empty-state CTA back into the main window so clicking `Open Monster Catalog` switches the stack to the Catalog page.

## Tests / Verification

- Update [C:/MSM_App/tests/unit/test_gui_smoke.py](C:/MSM_App/tests/unit/test_gui_smoke.py) for any renamed widgets or changed click targets while preserving the core behavior checks:
  - Catalog still emits add-target
  - Breed List populates after add
  - egg icon increment behavior still works
  - in-work panel close-out behavior still works
- Run targeted smoke coverage for the rebuilt Home shell and confirm keyboard focus, nav switching, and empty-state CTA routing remain functional.

## Notes

- Catalog and Settings already exist as real pages in [C:/MSM_App/app/ui/catalog_panel.py](C:/MSM_App/app/ui/catalog_panel.py) and [C:/MSM_App/app/ui/settings_panel.py](C:/MSM_App/app/ui/settings_panel.py), so this pass only needs routing polish, not new placeholder pages.
- The implementation should avoid adding timers, metrics, dashboard widgets, or new product systems beyond the Home workflow defined in the request.

