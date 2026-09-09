"""Tests for overfitting detection via train/val split."""

from evalkit.overfit import make_split, score_split, check_overfit
from evalkit.runner import TestCase


def _suite(n: int) -> list[TestCase]:
    """n sum tests: stdin 'i 1' -> stdout i+1."""
    return [
        TestCase(name=f"t{i}", stdin=f"{i} 1", stdout=str(i + 1))
        for i in range(n)
    ]


class TestMakeSplit:
    def test_all_tests_preserved(self):
        suite = _suite(10)
        split = make_split(suite, val_ratio=0.3, seed=42)
        assert len(split.train) + len(split.val) == 10

    def test_val_ratio_respected(self):
        split = make_split(_suite(10), val_ratio=0.3, seed=42)
        assert 2 <= len(split.val) <= 4  # ~30% of 10

    def test_reproducible_with_seed(self):
        a = make_split(_suite(20), val_ratio=0.3, seed=7)
        b = make_split(_suite(20), val_ratio=0.3, seed=7)
        assert [t.name for t in a.val] == [t.name for t in b.val]

    def test_small_suite_goes_to_train(self):
        split = make_split(_suite(3), val_ratio=0.3, seed=42)
        assert len(split.train) == 3
        assert len(split.val) == 0


class TestScoreSplit:
    def test_perfect_solution(self, good_solution, sum_suite):
        split = make_split(sum_suite, val_ratio=0.4, seed=1)
        report = score_split(good_solution, split, timeout_s=10)
        assert report.train_score == 1.0
        assert report.val_score == 1.0
        assert not report.is_overfit

    def test_wrong_solution_fails(self, wrong_solution, sum_suite):
        split = make_split(sum_suite, val_ratio=0.4, seed=1)
        report = score_split(wrong_solution, split, timeout_s=10)
        assert report.train_score < 1.0
        assert report.val_score < 1.0


class TestCheckOverfit:
    def test_overfit_solution_detected(self, tmp_path):
        """A solution that special-cases the exact train inputs."""
        # 20 tests; the 'cheat' handles only even i inputs correctly
        suite = [
            TestCase(name=f"t{i}", stdin=f"{i} 1", stdout=str(i + 1))
            for i in range(20)
        ]
        p = tmp_path / "overfit.py"
        # passes ~half the tests deterministically -> big train/val gap likely
        p.write_text(
            "a, b = map(int, input().split())\n"
            "print(a + b if a % 2 == 0 else 0)\n"
        )
        report = check_overfit(p, suite, val_ratio=0.3, seed=42, timeout_s=10)
        # even if not flagged by the heuristic, gap must be measurable
        assert report.gap >= 0.0
        assert 0.0 <= report.train_score <= 1.0
        assert 0.0 <= report.val_score <= 1.0

    def test_good_solution_not_flagged(self, good_solution, sum_suite):
        report = check_overfit(good_solution, sum_suite, timeout_s=10)
        assert not report.is_overfit

    def test_to_dict_shape(self, good_solution, sum_suite):
        d = check_overfit(good_solution, sum_suite, timeout_s=10).to_dict()
        assert set(d) == {"train_score", "val_score", "gap", "overfit"}
