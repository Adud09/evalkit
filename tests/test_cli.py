"""End-to-end CLI tests."""

import json

from evalkit.cli import main


def _write_suite(tmp_path, cases):
    p = tmp_path / "suite.json"
    p.write_text(json.dumps({"test_cases": cases}))
    return p


class TestRunCommand:
    def test_good_solution_exits_zero(self, tmp_path, good_solution, sum_suite):
        suite = _write_suite(
            tmp_path,
            [{"name": c.name, "stdin": c.stdin, "stdout": c.stdout} for c in sum_suite],
        )
        rc = main(["run", str(good_solution), str(suite)])
        assert rc == 0

    def test_wrong_solution_exits_one(self, tmp_path, wrong_solution, sum_suite):
        suite = _write_suite(
            tmp_path,
            [{"name": c.name, "stdin": c.stdin, "stdout": c.stdout} for c in sum_suite],
        )
        rc = main(["run", str(wrong_solution), str(suite)])
        assert rc == 1

    def test_output_json_written(self, tmp_path, good_solution, sum_suite):
        suite = _write_suite(
            tmp_path,
            [{"name": c.name, "stdin": c.stdin, "stdout": c.stdout} for c in sum_suite],
        )
        out = tmp_path / "result.json"
        rc = main(["run", str(good_solution), str(suite), "-o", str(out)])
        assert rc == 0
        data = json.loads(out.read_text())
        assert data["score"] == 1.0
        assert len(data["results"]) == 5
        assert data["peak_memory_kb"] > 0


class TestCheckCommand:
    def test_full_check_accepts_good(self, tmp_path, good_solution, sum_suite, capsys):
        suite = _write_suite(
            tmp_path,
            [{"name": c.name, "stdin": c.stdin, "stdout": c.stdout} for c in sum_suite],
        )
        rc = main(["check", str(good_solution), str(suite), "--determinism-runs", "2"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "ACCEPT" in out

    def test_full_check_rejects_cheater(self, tmp_path, sum_suite, capsys):
        """Hardcoded outputs are HIGH severity -> verdict reject."""
        cheat = tmp_path / "cheat.py"
        # prints a hardcoded literal for one case, garbage elsewhere:
        # can't compute, only memorized, exactly what the scanner hunts
        cheat.write_text(
            "a, b = map(int, input().split())\n"
            "if a == 1000000:\n"
            "    print(\"3000000\")\n"
            "else:\n"
            "    print(0)\n"
        )
        suite = _write_suite(
            tmp_path,
            [{"name": c.name, "stdin": c.stdin, "stdout": c.stdout} for c in sum_suite],
        )
        rc = main(["check", str(cheat), str(suite), "--determinism-runs", "2"])
        out = capsys.readouterr().out
        assert rc == 1
        assert "REJECT" in out
        assert "hardcoded-output" in out

    def test_env_probing_downgraded_to_review(self, tmp_path, sum_suite, capsys):
        """env-probing is MEDIUM: it flags review but alone doesn't reject."""
        probe = tmp_path / "probe.py"
        probe.write_text(
            'import os\nif os.environ.get("GRADING"):\n    print("5")\n'
            "else:\n"
            "    a, b = map(int, input().split())\n    print(a + b)\n"
        )
        suite = _write_suite(
            tmp_path,
            [{"name": c.name, "stdin": c.stdin, "stdout": c.stdout} for c in sum_suite],
        )
        rc = main(["check", str(probe), str(suite), "--determinism-runs", "2"])
        out = capsys.readouterr().out
        assert rc == 0  # still accepts, but flags for human review
        assert "env-probing" in out
        assert "review" in out


class TestRankCommand:
    def test_rank_multiple(self, tmp_path, capsys):
        a = tmp_path / "a.json"
        a.write_text(json.dumps({"solution": "a", "score": 0.5, "avg_runtime_ms": 10}))
        b = tmp_path / "b.json"
        b.write_text(json.dumps({"solution": "b", "score": 1.0, "avg_runtime_ms": 10}))
        rc = main(["rank", str(a), str(b)])
        out = capsys.readouterr().out
        assert rc == 0
        # match full table rows, not substrings of the header
        assert out.index("1   b") < out.index("2   a")
