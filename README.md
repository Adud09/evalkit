# evalkit

A small harness for grading code submissions without getting gamed. Runs each submission in its own subprocess, checks determinism, detects overfitting, scans for cheating, and ranks fairly. Stdlib only.

```text
$ evalkit check examples/two-sum-solution.py examples/two-sum-suite.json

== CORRECTNESS =================================================
  [   PASS] basic
  [   PASS] swapped
  [   PASS] zeros
  [   PASS] negatives
  [   PASS] duplicates
  [   PASS] large
  score: 100.0%

== DETERMINISM =================================================
  DETERMINISTIC across 3 shuffled runs

== OVERFIT =====================================================
  train: 100.0%  val: 100.0%  gap: 0.0%  -> OK

== ANTICHEAT ===================================================
  clean
  verdict: clean

== SUMMARY =====================================================
  [PASS] correctness
  [PASS] determinism
  [PASS] overfit
  [PASS] anticheat

  OVERALL: ACCEPT
```

## Why

Code evaluation is easy to game. Solutions hardcode expected outputs, tune to the visible tests, or only pass when the tests run in one lucky order. evalkit treats grading as an adversarial problem and checks for all three:

| Check | Catches | How |
|---|---|---|
| Correctness | wrong answers | one subprocess per test, wall-clock timeout |
| Determinism | order-dependent / stateful code | reruns the suite in shuffled orders, demands identical outcomes |
| Overfitting | solutions tuned to visible tests | train/validation split, only held-out tests count |
| Anti-cheat | hardcoded outputs, test tampering, env probing | static scan, severity-ranked findings |
| Leaderboard | unfair tie-breaks | score, then runtime, then memory |

## Install

```bash
pip install -e .
```

Python 3.10+. No runtime deps, stdlib only. Memory tracking uses `resource`, so Linux/macOS (no Windows).

## Usage

Define a challenge (`examples/two-sum-suite.json`):

```json
{
  "test_cases": [
    { "name": "basic", "stdin": "4 9\n2 7 11 15", "stdout": "0 1" },
    { "name": "swapped", "stdin": "4 6\n3 2 4", "stdout": "1 2" }
  ]
}
```

Run a submission:

```bash
evalkit run solutions/alice.py suites/two-sum.json
```

Full evaluation report:

```bash
evalkit check solutions/alice.py suites/two-sum.json
```

Rank a batch of results:

```bash
evalkit run solutions/alice.py suites/two-sum.json -o results/alice.json
evalkit run solutions/bob.py   suites/two-sum.json -o results/bob.json
evalkit rank results/*.json
```

```text
== LEADERBOARD =================================================
#   name                         score     runtime    peak_mem  status
----------------------------------------------------------------------
1   examples/two-sum-solution  100.00%      17.9ms    18176KB  ok
```

## Library use

```python
from evalkit.runner import TestCase, run_solution
from evalkit.determinism import check_determinism
from evalkit.overfit import check_overfit
from evalkit.anticheat import scan_solution

suite = [TestCase(name="t1", stdin="2 3", stdout="5")]

report = run_solution("solutions/alice.py", suite)     # correctness
det = check_determinism("solutions/alice.py", suite)   # stability
over = check_overfit("solutions/alice.py", suite)      # generalization
cheat = scan_solution("solutions/alice.py", ["5"])     # static analysis
```

## Design notes

- A subprocess per test. A crashing or hanging submission can't take the grader down; timeouts are enforced by the OS, not by hope.
- Whitespace-tolerant comparison. Trailing newlines fail nobody.
- Determinism is not correctness. A solution can be perfectly deterministic and completely wrong, the checks are independent.
- The overfit heuristic is honest about its limits: suites of 3 tests or fewer are never split, both halves would be statistically meaningless.
- Peak memory comes from `rusage(RUSAGE_CHILDREN)`, a high-water mark over reaped children. Per-test attribution isn't possible that way and I didn't want a psutil dependency for it. Good enough for ranking.
- Static analysis is a signal, not a verdict. `env-probing` is MEDIUM (review), `hardcoded-output` is HIGH (reject). The `verdict()` function encodes that policy.

## Development

```bash
pip install -e . pytest
pytest -q
```

55 tests. Every module is tested against clean solutions, wrong solutions, crashing solutions, hanging solutions, and deliberate cheaters.

## License

MIT
