"""Static anti-cheat scan of candidate solutions.

Catches the obvious ways people game graders: hardcoded expected
outputs, reading the test file at runtime, env probing, importing
grader internals. Static analysis is a signal, not a verdict. The
severity ranking is what decides fatal vs merely weird.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class Severity(Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class Finding:
    rule: str
    severity: Severity
    line: int
    detail: str


# (rule, severity, pattern, detail) applied per line
_LINE_RULES = [
    (
        "test-file-access",
        Severity.HIGH,
        re.compile(
            r'''["'](?:tests?|suite|grader|answer|expected)[^"'\n]*\.(?:json|txt|py|yaml|yml)["']''',
            re.I,
        ),
        "solution references a test/grader file",
    ),
    (
        "grader-import",
        Severity.HIGH,
        re.compile(r"\b(?:import|from)\s+(?:evalkit|grader|runner|pytest)\b", re.I),
        "solution imports grader internals",
    ),
    (
        "env-probing",
        Severity.MEDIUM,
        re.compile(r"os\.environ|getenv\s*\(", re.I),
        "solution reads environment variables",
    ),
    (
        "process-spawn",
        Severity.MEDIUM,
        re.compile(r"subprocess|os\.system|os\.exec|popen", re.I),
        "solution spawns processes",
    ),
    (
        "introspection",
        Severity.MEDIUM,
        re.compile(r"inspect\.|sys\._getframe|globals\s*\(\)|locals\s*\(\)", re.I),
        "solution inspects runtime frames",
    ),
    (
        "network-access",
        Severity.LOW,
        re.compile(
            r"\b(?:import|from)\s+(?:requests|urllib|httpx|socket|http\.client)\b",
            re.I,
        ),
        "solution performs network access",
    ),
]


def scan_source(source: str) -> list[Finding]:
    """Run the per-line rules. Comments are exempt."""
    findings: list[Finding] = []
    for lineno, line in enumerate(source.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        for rule, severity, pattern, detail in _LINE_RULES:
            if pattern.search(line):
                findings.append(Finding(rule, severity, lineno, detail))
    return findings


def scan_for_hardcoded_outputs(
    source: str,
    expected_outputs: list[str],
    min_len: int = 3,
) -> list[Finding]:
    """Find expected outputs embedded as string literals.

    Short common values ("1", "yes", "true") are ignored, they match
    innocent code constantly and tell you nothing.
    """
    findings: list[Finding] = []
    trivial = {"1", "0", "true", "false", "yes", "no", "-1", "none", "[]", "{}"}

    for lineno, line in enumerate(source.splitlines(), start=1):
        if line.strip().startswith("#"):
            continue
        for match in re.finditer(r'''["']([^\n"']{1,80})["']''', line):
            literal = match.group(1).strip()
            if len(literal) < min_len or literal.lower() in trivial:
                continue
            for expected in expected_outputs:
                expected = expected.strip()
                if len(expected) < min_len or expected.lower() in trivial:
                    continue
                if literal == expected:
                    findings.append(
                        Finding(
                            rule="hardcoded-output",
                            severity=Severity.HIGH,
                            line=lineno,
                            detail=f'expected output "{expected[:40]}" hardcoded as literal',
                        )
                    )
                    break  # one finding per line is plenty
    return findings


def scan_solution(
    solution_path: Path | str,
    expected_outputs: list[str] | None = None,
) -> list[Finding]:
    source = Path(solution_path).read_text()
    findings = scan_source(source)
    if expected_outputs:
        findings.extend(scan_for_hardcoded_outputs(source, expected_outputs))
    order = {Severity.HIGH: 0, Severity.MEDIUM: 1, Severity.LOW: 2, Severity.INFO: 3}
    findings.sort(key=lambda f: (order[f.severity], f.line))
    return findings


def verdict(findings: list[Finding]) -> str:
    """clean / review / reject. Any HIGH finding rejects."""
    if any(f.severity == Severity.HIGH for f in findings):
        return "reject"
    if findings:
        return "review"
    return "clean"
