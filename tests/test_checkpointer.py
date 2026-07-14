import database.checkpointer as checkpointer_module


# =============================================================================
# Test Doubles
# =============================================================================


class FakePool:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.enter_calls = 0
        self.exit_calls = 0

    def __enter__(self):
        self.enter_calls += 1
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        self.exit_calls += 1


class FakePostgresSaver:
    def __init__(self, pool):
        self.pool = pool
        self.setup_calls = 0

    def setup(self):
        self.setup_calls += 1


# =============================================================================
# PostgreSQL Runtime Tests
# =============================================================================


def test_postgres_runtime_uses_connection_pool_and_closes_it(
    monkeypatch,
):
    created_pools = []
    created_savers = []

    def fake_connection_pool(**kwargs):
        pool = FakePool(**kwargs)
        created_pools.append(pool)

        return pool

    def fake_postgres_saver(pool):
        saver = FakePostgresSaver(pool)
        created_savers.append(saver)

        return saver

    monkeypatch.setattr(
        checkpointer_module,
        "CHECKPOINT_BACKEND",
        "postgres",
    )

    monkeypatch.setattr(
        checkpointer_module,
        "DATABASE_URL",
        "postgresql://test-user:test-password@test-host/test-db",
    )

    monkeypatch.setattr(
        checkpointer_module,
        "ConnectionPool",
        fake_connection_pool,
    )

    monkeypatch.setattr(
        checkpointer_module,
        "PostgresSaver",
        fake_postgres_saver,
    )

    with checkpointer_module.checkpointer_runtime() as checkpointer:
        assert len(created_pools) == 1
        assert len(created_savers) == 1

        pool = created_pools[0]
        saver = created_savers[0]

        assert checkpointer is saver
        assert saver.pool is pool
        assert saver.setup_calls == 1

        assert pool.enter_calls == 1
        assert pool.exit_calls == 0

        assert pool.kwargs["conninfo"] == (
            "postgresql://test-user:test-password@test-host/test-db"
        )
        assert pool.kwargs["min_size"] == 1
        assert pool.kwargs["max_size"] == 5

        connection_kwargs = pool.kwargs["kwargs"]

        assert connection_kwargs["autocommit"] is True
        assert connection_kwargs["prepare_threshold"] == 0
        assert connection_kwargs["row_factory"] is checkpointer_module.dict_row

    assert pool.exit_calls == 1
