"""Tests for the leaderboard."""

import json

from evalkit.leaderboard import (
    Leaderboard,
    Submission,
    load_leaderboard,
    load_submission,
)


def _result_file(tmp_path, name, score, runtime, memory=100.0, status="ok"):
    p = tmp_path / f"{name}.json"
    p.write_text(json.dumps({
        "solution": name,
        "score": score,
        "avg_runtime_ms": runtime,
        "peak_memory_kb": memory,
        "status": status,
    }))
    return p


class TestRanking:
    def test_score_beats_speed(self):
        board = Leaderboard()
        board.add(Submission("slow_correct", 1.0, 900))
        board.add(Submission("fast_wrong", 0.5, 10))
        ranked = board.ranked()
        assert ranked[0].name == "slow_correct"

    def test_runtime_tiebreak(self):
        board = Leaderboard()
        board.add(Submission("alpha", 1.0, 500))
        board.add(Submission("beta", 1.0, 300))
        assert board.ranked()[0].name == "beta"

    def test_memory_second_tiebreak(self):
        board = Leaderboard()
        board.add(Submission("heavy", 1.0, 100, peak_memory_kb=2048))
        board.add(Submission("light", 1.0, 100, peak_memory_kb=512))
        assert board.ranked()[0].name == "light"

    def test_name_stable_tiebreak(self):
        board = Leaderboard()
        board.add(Submission("zeta", 1.0, 100, 100))
        board.add(Submission("alpha", 1.0, 100, 100))
        assert board.ranked()[0].name == "alpha"

    def test_rejected_always_below_ok(self):
        board = Leaderboard()
        board.add(Submission("cheater", 1.0, 1, status="rejected"))
        board.add(Submission("honest", 0.2, 900))
        ranked = board.ranked()
        assert ranked[0].name == "honest"
        assert ranked[-1].name == "cheater"


class TestRender:
    def test_render_includes_all(self):
        board = Leaderboard()
        board.add(Submission("a", 1.0, 10))
        board.add(Submission("b", 0.5, 20))
        text = board.render()
        assert "a" in text and "b" in text
        assert "100.00%" in text

    def test_render_top_n(self):
        board = Leaderboard()
        for i in range(10):
            board.add(Submission(f"s{i}", i / 10, 10))
        assert len(board.render(top=3).splitlines()) <= 6

    def test_render_empty(self):
        assert Leaderboard().render() == "(no submissions)"


class TestLoading:
    def test_load_submission(self, tmp_path):
        p = _result_file(tmp_path, "alice", 0.9, 123.4)
        sub = load_submission(p)
        assert sub.name == "alice"
        assert sub.score == 0.9

    def test_load_leaderboard_order(self, tmp_path):
        files = [
            _result_file(tmp_path, "a", 0.5, 10),
            _result_file(tmp_path, "b", 1.0, 10),
        ]
        board = load_leaderboard(files)
        assert board.ranked()[0].name == "b"
