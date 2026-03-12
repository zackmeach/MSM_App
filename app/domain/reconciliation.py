"""Reconciliation — enforces the Breed List invariant.

In the satisfaction-aware model, reconciliation is simpler than in a global
aggregate model: each target owns its own progress rows, so closing out a
target and deleting its rows is inherently reconciling.  The remaining
reconciliation concern is the clip rule: after a target set change, no
target_requirement_progress row may have satisfied_count > required_count.
"""

from __future__ import annotations

from app.domain.models import TargetRequirementProgress


def reconcile(
    progress_rows: list[TargetRequirementProgress],
) -> list[tuple[int, int, int]]:
    """Return list of (active_target_id, egg_type_id, clipped_satisfied) for
    any rows where satisfied_count > required_count.

    In the satisfaction-aware model this should be rare (it can happen if
    content requirements change via an update), but the invariant must hold.
    """
    clips: list[tuple[int, int, int]] = []
    for row in progress_rows:
        if row.satisfied_count > row.required_count:
            clips.append((row.active_target_id, row.egg_type_id, row.required_count))
    return clips
