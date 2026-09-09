"""Tests for the static anti-cheat scanner."""

from evalkit.anticheat import (
    Finding,
    Severity,
    scan_for_hardcoded_outputs,
    scan_source,
    scan_solution,
    verdict,
)


class TestScanSource:
    def test_clean_solution(self):
        src = "a, b = map(int, input().split())\nprint(a + b)\n"
        assert scan_source(src) == []

    def test_env_probing_flagged(self):
        src = "import os\nprint(os.environ.get('GRADING'))\n"
        findings = scan_source(src)
        assert any(f.rule == "env-probing" for f in findings)

    def test_comments_ignored(self):
        src = "# reads os.environ in the grader\nx = 1\n"
        assert scan_source(src) == []

    def test_test_file_access_flagged_high(self):
        src = 'open("tests.json").read()\n'
        findings = scan_source(src)
        assert any(
            f.rule == "test-file-access" and f.severity == Severity.HIGH
            for f in findings
        )

    def test_grader_import_flagged(self):
        src = "from evalkit.runner import run_one\n"
        findings = scan_source(src)
        assert any(f.rule == "grader-import" for f in findings)

    def test_line_numbers_reported(self):
        src = "x = 1\ny = 2\nimport requests\n"
        findings = scan_source(src)
        assert findings[0].line == 3


class TestHardcodedOutputs:
    def test_expected_output_detected(self):
        src = 'results = ["1 5 7 9", "x"]\n'
        findings = scan_for_hardcoded_outputs(src, ["1 5 7 9"])
        assert any(f.rule == "hardcoded-output" for f in findings)
        assert findings[0].severity == Severity.HIGH

    def test_trivial_outputs_ignored(self):
        """'1' alone must not count as a hardcoded answer."""
        src = 'flags = ["1", "yes"]\n'
        findings = scan_for_hardcoded_outputs(src, ["1"])
        assert findings == []

    def test_innocent_strings_not_flagged(self):
        src = 'print("hello world")\n'
        findings = scan_for_hardcoded_outputs(src, ["1 5 7 9"])
        assert findings == []


class TestVerdict:
    def test_clean(self):
        assert verdict([]) == "clean"

    def test_review_for_medium(self):
        f = Finding("env-probing", Severity.MEDIUM, 3, "x")
        assert verdict([f]) == "review"

    def test_reject_for_high(self):
        f = Finding("hardcoded-output", Severity.HIGH, 3, "x")
        assert verdict([f]) == "reject"


class TestScanSolution:
    def test_end_to_end(self, tmp_path):
        p = tmp_path / "cheat.py"
        p.write_text(
            'import os\nprint(os.environ.get("X"))\n'
            'answers = {"case1": "42 42 42"}\nprint(answers["case1"])\n'
        )
        findings = scan_solution(p, expected_outputs=["42 42 42"])
        rules = {f.rule for f in findings}
        assert "env-probing" in rules
        assert "hardcoded-output" in rules
        # severity ordering: HIGH findings listed first
        assert findings[0].severity == Severity.HIGH
