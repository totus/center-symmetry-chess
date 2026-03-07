from chess_variant_research.host import HostResources, recommend_parallel_games


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
