"""Tests for the reconciliation clip rule."""

from __future__ import annotations

from app.domain.models import TargetRequirementProgress
from app.domain.reconciliation import reconcile


class TestReconcileClipRule:
    def test_no_clips_when_valid(self):
        rows = [
            TargetRequirementProgress(1, 10, 4, 2),
            TargetRequirementProgress(1, 11, 3, 3),
        ]
        assert reconcile(rows) == []

    def test_clip_when_satisfied_exceeds_required(self):
        rows = [
            TargetRequirementProgress(1, 10, 3, 5),  # over-satisfied
        ]
        clips = reconcile(rows)
        assert len(clips) == 1
        assert clips[0] == (1, 10, 3)

    def test_multiple_clips(self):
        rows = [
            TargetRequirementProgress(1, 10, 3, 5),
            TargetRequirementProgress(2, 11, 2, 4),
            TargetRequirementProgress(3, 12, 6, 6),  # exact — not clipped
        ]
        clips = reconcile(rows)
        assert len(clips) == 2
        ids = {(c[0], c[1]) for c in clips}
        assert (1, 10) in ids
        assert (2, 11) in ids

    def test_empty_rows_returns_no_clips(self):
        assert reconcile([]) == []
