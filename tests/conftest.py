"""Shared fixtures: tiny solutions and suites used across tests."""

from pathlib import Path

import pytest

SOLUTIONS = Path(__file__).parent / "solutions"


@pytest.fixture
def good_solution(tmp_path: Path) -> Path:
    """A correct, clean solution: reads two ints, prints their sum."""
    p = tmp_path / "good.py"
    p.write_text("a, b = map(int, input().split())\nprint(a + b)\n")
    return p


@pytest.fixture
def wrong_solution(tmp_path: Path) -> Path:
    """A solution that computes the wrong thing."""
    p = tmp_path / "wrong.py"
    p.write_text("a, b = map(int, input().split())\nprint(a - b)\n")
    return p


@pytest.fixture
def crash_solution(tmp_path: Path) -> Path:
    """A solution that raises on every input."""
    p = tmp_path / "crash.py"
    p.write_text("raise RuntimeError('boom')\n")
    return p


@pytest.fixture
def hang_solution(tmp_path: Path) -> Path:
    """A solution that loops forever."""
    p = tmp_path / "hang.py"
    p.write_text("while True:\n    pass\n")
    return p


@pytest.fixture
def sum_suite() -> list:
    from evalkit.runner import TestCase

    return [
        TestCase(name="basic", stdin="2 3", stdout="5"),
        TestCase(name="zeros", stdin="0 0", stdout="0"),
        TestCase(name="negatives", stdin="-5 3", stdout="-2"),
        TestCase(name="large", stdin="1000000 2000000", stdout="3000000"),
        TestCase(name="another", stdin="7 8", stdout="15"),
    ]
