from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(slots=True)
class HostResources:
    logical_cpus: int
    total_memory_mb: int | None


def detect_host_resources() -> HostResources:
    logical = os.cpu_count() or 1
    total_memory_mb: int | None = None

    try:
        page_size = int(os.sysconf("SC_PAGE_SIZE"))
        phys_pages = int(os.sysconf("SC_PHYS_PAGES"))
        total_memory_mb = (page_size * phys_pages) // (1024 * 1024)
    except (AttributeError, OSError, ValueError):
        total_memory_mb = None

    return HostResources(logical_cpus=logical, total_memory_mb=total_memory_mb)


def recommend_parallel_games(
    games: int,
    engine_threads: int,
    hash_mb: int,
    requested_parallel_games: int | None,
    host: HostResources | None = None,
) -> int:
    if games <= 0:
        return 1

    env_override = os.getenv("CHESS_RESEARCH_PARALLEL_GAMES")
    if env_override:
        try:
            env_workers = int(env_override)
            if env_workers > 0:
                return max(1, min(games, env_workers))
        except ValueError:
            pass

    if requested_parallel_games is not None and requested_parallel_games > 0:
        return max(1, min(games, requested_parallel_games))

    host_info = host or detect_host_resources()

    cpu_bound = max(1, host_info.logical_cpus // max(1, engine_threads))

    if host_info.total_memory_mb is None:
        mem_bound = cpu_bound
    else:
        reserve_mb = max(2048, int(host_info.total_memory_mb * 0.25))
        usable_mb = max(1024, host_info.total_memory_mb - reserve_mb)
        per_worker_mb = max(384, hash_mb + 256)
        mem_bound = max(1, usable_mb // per_worker_mb)

    return max(1, min(games, cpu_bound, mem_bound))
