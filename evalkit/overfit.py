"""Overfitting detection via train/validation split scoring.

A submission that passes every visible test but collapses on held-out
tests was tuned to the tests, not the problem. Split the suite: the
train set is what the candidate could see while developing, the val
set is held out and scored only at evaluation time.

Overfit gap = train_score - val_score. Big gap means the solution
memorized rather than generalized.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from .runner import DEFAULT_TIMEOUT_S, TestCase, run_one


@dataclass
class Split:
    """A train/validation split of a test suite."""

    train: list[TestCase] = field(default_factory=list)
    val: list[TestCase] = field(default_factory=list)


@dataclass
class OverfitReport:
    """Result of split scoring."""

    train_score: float = 0.0
    val_score: float = 0.0

    @property
    def gap(self) -> float:
        """How much worse the solution does on unseen tests."""
        return self.train_score - self.val_score

    @property
    def is_overfit(self) -> bool:
        """Heuristic: passed most of train but dropped on val."""
        return self.train_score >= 0.9 and self.val_score < self.train_score - 0.1

    def to_dict(self) -> dict:
        return {
            "train_score": round(self.train_score, 4),
            "val_score": round(self.val_score, 4),
            "gap": round(self.gap, 4),
            "overfit": self.is_overfit,
        }


def make_split(
    cases: list[TestCase],
    val_ratio: float = 0.3,
    seed: int = 42,
) -> Split:
    """Random train/val split.

    Small suites (<= 3 tests) keep everything in train. Splitting three
tests makes both halves statistically meaningless.
    """
    if len(cases) <= 3 or val_ratio <= 0:
        return Split(train=list(cases), val=[])
    if val_ratio >= 1:
        return Split(train=[], val=list(cases))

    shuffled = list(cases)
    random.Random(seed).shuffle(shuffled)
    n_val = max(1, round(len(shuffled) * val_ratio))
    return Split(
        val=shuffled[:n_val],
        train=shuffled[n_val:],
    )


def score_split(
    solution_path: str,
    split: Split,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> OverfitReport:
    """Score a solution separately on train and val sets."""
    report = OverfitReport()

    if split.train:
        passed = sum(
            1
            for case in split.train
            if run_one(solution_path, case, timeout_s).passed
        )
        report.train_score = passed / len(split.train)

    if split.val:
        passed = sum(
            1
            for case in split.val
            if run_one(solution_path, case, timeout_s).passed
        )
        report.val_score = passed / len(split.val)

    return report


def check_overfit(
    solution_path: str,
    cases: list[TestCase],
    val_ratio: float = 0.3,
    seed: int = 42,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> OverfitReport:
    """One-call convenience: split, then score both halves."""
    split = make_split(cases, val_ratio=val_ratio, seed=seed)
    return score_split(solution_path, split, timeout_s=timeout_s)
