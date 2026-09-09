"""Determinism checking via randomized-order reruns.

A solution that only passes when tests run in one specific order is a
red flag: usually global state, cached inputs, or accidental coupling
between tests. Rerun the suite in shuffled orders and demand identical
results every time.

Two distinct failure modes:
  order-dependence: pass/fail flips depending on test order
  nondeterminism:   same input, different output across runs
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from .runner import TestCase, TestResult, run_one


@dataclass
class DeterminismReport:
    """Results of repeated shuffled runs."""

    runs: int = 0
    order_dependent: list[str] = field(default_factory=list)
    nondeterministic: list[str] = field(default_factory=list)

    @property
    def is_deterministic(self) -> bool:
        return not self.order_dependent and not self.nondeterministic

    def to_dict(self) -> dict:
        return {
            "runs": self.runs,
            "deterministic": self.is_deterministic,
            "order_dependent_tests": self.order_dependent,
            "nondeterministic_tests": self.nondeterministic,
        }


def check_determinism(
    solution_path: str,
    cases: list[TestCase],
    runs: int = 3,
    seed: int = 1337,
    timeout_s: float = 5.0,
) -> DeterminismReport:
    """Rerun the suite `runs` times in different shuffled orders.

    Args:
        solution_path: Candidate solution file.
        cases: Full test suite.
        runs: Number of reruns, each with a different order.
        seed: Base seed so shuffles are reproducible.
        timeout_s: Per-test timeout.
    """
    report = DeterminismReport(runs=runs)
    rng = random.Random(seed)

    # test name -> list of (passed, output) across all runs
    observations: dict[str, list[tuple[bool, str]]] = {c.name: [] for c in cases}

    for _ in range(runs):
        order = list(cases)
        rng.shuffle(order)
        for case in order:
            result: TestResult = run_one(solution_path, case, timeout_s)
            observations[case.name].append((result.passed, result.output))

    for name, obs in observations.items():
        outcomes = {passed for passed, _ in obs}
        outputs = {output for _, output in obs}

        # same test passed in some runs, failed in others
        if len(outcomes) > 1:
            report.order_dependent.append(name)
            continue  # already flagged; nondeterminism is implied

        # same outcome but output drifted across runs
        if len(outputs) > 1:
            report.nondeterministic.append(name)

    return report
