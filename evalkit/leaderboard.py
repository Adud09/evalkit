"""Fair ranking of submissions.

Score first, then runtime, then memory, then name (last tiebreak is
there for stable output, not for glory). Rejected submissions always
rank below accepted ones, no matter how fast they were.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Submission:
    name: str
    score: float  # 0.0 - 1.0
    avg_runtime_ms: float = 0.0
    peak_memory_kb: float = 0.0
    status: str = "ok"  # ok | rejected (anticheat) | error

    def sort_key(self) -> tuple:
        # score desc, runtime asc, memory asc, name asc for stability
        return (-self.score, self.avg_runtime_ms, self.peak_memory_kb, self.name)


@dataclass
class Leaderboard:
    submissions: list[Submission] = field(default_factory=list)

    def add(self, sub: Submission) -> None:
        self.submissions.append(sub)

    def ranked(self) -> list[Submission]:
        ok = [s for s in self.submissions if s.status == "ok"]
        flagged = [s for s in self.submissions if s.status != "ok"]
        return sorted(ok, key=Submission.sort_key) + sorted(
            flagged, key=Submission.sort_key
        )

    def render(self, top: int | None = None) -> str:
        rows = self.ranked() if top is None else self.ranked()[:top]
        if not rows:
            return "(no submissions)"

        header = (
            f"{'#':<4}{'name':<26}{'score':>8}{'runtime':>12}{'peak_mem':>12}  status"
        )
        lines = [header, "-" * len(header)]
        for i, s in enumerate(rows, start=1):
            lines.append(
                f"{i:<4}{s.name[:25]:<26}{s.score:>8.2%}"
                f"{s.avg_runtime_ms:>10.1f}ms{s.peak_memory_kb:>9.0f}KB  {s.status}"
            )
        return "\n".join(lines)


def load_submission(path: Path | str) -> Submission:
    data = json.loads(Path(path).read_text())
    return Submission(
        name=data.get("solution", Path(path).stem),
        score=float(data.get("score", 0.0)),
        avg_runtime_ms=float(data.get("avg_runtime_ms", 0.0)),
        peak_memory_kb=float(data.get("peak_memory_kb", 0.0)),
        status=data.get("status", "ok"),
    )


def load_leaderboard(paths: list[Path | str]) -> Leaderboard:
    board = Leaderboard()
    for p in paths:
        board.add(load_submission(p))
    return board
