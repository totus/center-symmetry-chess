from __future__ import annotations

import os

import pytest

from chess_variant_research.host import (
    HostResources,
    detect_host_resources,
    recommend_parallel_games,
)


def test_recommend_parallel_games_respects_requested_limit() -> None:
    host = HostResources(logical_cpus=16, total_memory_mb=32768)
    workers = recommend_parallel_games(
        games=100,
        engine_threads=1,
        hash_mb=128,
        requested_parallel_games=4,
        host=host,
    )
    assert workers == 4


def test_recommend_parallel_games_uses_cpu_bound() -> None:
    host = HostResources(logical_cpus=8, total_memory_mb=32768)
    workers = recommend_parallel_games(
        games=100,
        engine_threads=2,
        hash_mb=128,
        requested_parallel_games=None,
        host=host,
    )
    assert workers == 4


def test_recommend_parallel_games_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    host = HostResources(logical_cpus=8, total_memory_mb=32768)
    monkeypatch.setenv("CHESS_RESEARCH_PARALLEL_GAMES", "3")
    workers = recommend_parallel_games(
        games=100,
        engine_threads=2,
        hash_mb=128,
        requested_parallel_games=None,
        host=host,
    )
    assert workers == 3


def test_detect_host_resources_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(os, "cpu_count", lambda: None)

    def bad_sysconf(_: str) -> int:
        raise OSError("x")

    monkeypatch.setattr(os, "sysconf", bad_sysconf)
    host = detect_host_resources()
    assert host.logical_cpus == 1
    assert host.total_memory_mb is None


def test_recommend_parallel_games_misc_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    host = HostResources(logical_cpus=4, total_memory_mb=None)
    monkeypatch.setenv("CHESS_RESEARCH_PARALLEL_GAMES", "bad")
    workers = recommend_parallel_games(
        games=0,
        engine_threads=1,
        hash_mb=128,
        requested_parallel_games=None,
        host=host,
    )
    assert workers == 1

    workers2 = recommend_parallel_games(
        games=8,
        engine_threads=1,
        hash_mb=128,
        requested_parallel_games=None,
        host=host,
    )
    assert workers2 == 4
