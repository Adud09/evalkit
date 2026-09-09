"""Tests for the sandboxed runner."""

from evalkit.runner import (
    TestCase,
    load_suite,
    run_one,
    run_solution,
)


class TestRunOne:
    def test_pass(self, good_solution):
        case = TestCase(name="t", stdin="2 3", stdout="5")
        result = run_one(good_solution, case, timeout_s=10)
        assert result.passed
        assert result.status == "pass"

    def test_fail_wrong_output(self, wrong_solution):
        case = TestCase(name="t", stdin="2 3", stdout="5")
        result = run_one(wrong_solution, case, timeout_s=10)
        assert not result.passed
        assert result.status == "fail"

    def test_error_captured(self, crash_solution):
        case = TestCase(name="t", stdin="2 3", stdout="5")
        result = run_one(crash_solution, case, timeout_s=10)
        assert not result.passed
        assert result.status == "error"
        assert "boom" in result.error

    def test_timeout_kills_hang(self, hang_solution):
        case = TestCase(name="t", stdin="2 3", stdout="5")
        result = run_one(hang_solution, case, timeout_s=1.0)
        assert not result.passed
        assert result.status == "timeout"

    def test_whitespace_tolerant(self, good_solution):
        """Trailing whitespace/newlines should not fail a correct answer."""
        case = TestCase(name="t", stdin="2 3", stdout="5\n\n")
        result = run_one(good_solution, case, timeout_s=10)
        assert result.passed

    def test_duration_measured(self, good_solution):
        case = TestCase(name="t", stdin="1 1", stdout="2")
        result = run_one(good_solution, case, timeout_s=10)
        assert result.duration_ms >= 0


class TestRunSolution:
    def test_full_suite_pass(self, good_solution, sum_suite):
        report = run_solution(good_solution, sum_suite, timeout_s=10)
        assert report.all_passed
        assert report.score == 1.0
        assert report.passed_count == 5

    def test_peak_memory_recorded(self, good_solution, sum_suite):
        # RUSAGE_CHILDREN high-water mark. a python process is never
        # tiny, so anything above a few MB means the plumbing works
        report = run_solution(good_solution, sum_suite, timeout_s=10)
        assert report.peak_memory_kb > 4000

    def test_full_suite_fail(self, wrong_solution, sum_suite):
        # note: a - b accidentally passes the 0+0 case, so the score is
        # low but not zero, the point is it fails overall
        report = run_solution(wrong_solution, sum_suite, timeout_s=10)
        assert not report.all_passed
        assert 0.0 < report.score < 1.0

    def test_shuffled_order_same_results(self, good_solution, sum_suite):
        """Shuffled execution must not change the outcome for clean code."""
        straight = run_solution(good_solution, sum_suite, timeout_s=10)
        shuffled = run_solution(good_solution, sum_suite, timeout_s=10, shuffle_seed=7)
        assert straight.score == shuffled.score

    def test_to_dict_shape(self, good_solution, sum_suite):
        d = run_solution(good_solution, sum_suite, timeout_s=10).to_dict()
        assert set(d) == {
            "solution", "score", "passed", "total", "avg_runtime_ms",
            "peak_memory_kb", "results",
        }
        assert d["score"] == 1.0
        assert len(d["results"]) == 5
        assert d["peak_memory_kb"] > 0


class TestLoadSuite:
    def test_load_json_suite(self, tmp_path):
        import json

        suite = tmp_path / "suite.json"
        suite.write_text(json.dumps({
            "test_cases": [
                {"name": "a", "stdin": "1 2", "stdout": "3"},
                {"name": "b", "stdin": "2 2", "stdout": "4"},
            ]
        }))
        cases = load_suite(suite)
        assert len(cases) == 2
        assert cases[0].name == "a"
        assert cases[1].stdout == "4"
