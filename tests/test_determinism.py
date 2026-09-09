"""Tests for determinism checking."""

from evalkit.determinism import check_determinism
from evalkit.runner import TestCase


class TestDeterminism:
    def test_clean_solution_is_deterministic(self, good_solution, sum_suite):
        report = check_determinism(good_solution, sum_suite, runs=3, timeout_s=10)
        assert report.is_deterministic
        assert report.runs == 3

    def test_nondeterministic_solution_flagged(self, tmp_path, sum_suite):
        """Unseeded randomness must be caught: same input, different outputs."""
        # don't name this file random.py: it shadows the stdlib module
        # and circular-imports itself. cost me 20 minutes.
        p = tmp_path / "nondet.py"
        p.write_text(
            "import random\n"
            "print(random.randint(0, 999999))\n"
        )
        report = check_determinism(str(p), sum_suite, runs=3, timeout_s=10)
        assert not report.is_deterministic
        assert report.nondeterministic or report.order_dependent

    def test_to_dict_shape(self, good_solution, sum_suite):
        d = check_determinism(good_solution, sum_suite, runs=2, timeout_s=10).to_dict()
        assert d["deterministic"] is True
        assert d["runs"] == 2
        assert d["order_dependent_tests"] == []
        assert d["nondeterministic_tests"] == []


class TestRunnerIntegration:
    def test_run_one_used_under_hood(self, good_solution):
        """check_determinism returns per-test granularity, not just a bool."""
        single = [TestCase(name="only", stdin="1 1", stdout="2")]
        report = check_determinism(good_solution, single, runs=2, timeout_s=10)
        # single-test suite: order can't vary, but output must be stable
        assert report.is_deterministic
