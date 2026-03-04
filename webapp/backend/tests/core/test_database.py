from src.api.core import database


def test_get_session_yields_session(monkeypatch):
    state = {"entered": False, "exited": False}

    class _DummySession:
        def __enter__(self):
            state["entered"] = True
            return self

        def __exit__(self, exc_type, exc, tb):
            _ = (exc_type, exc, tb)
            state["exited"] = True

    monkeypatch.setattr(database, "Session", lambda _engine: _DummySession())

    gen = database.get_session()
    sess = next(gen)
    assert state["entered"] is True
    assert isinstance(sess, _DummySession)

    try:
        next(gen)
    except StopIteration:
        pass

    assert state["exited"] is True


def test_create_db_and_tables_calls_metadata_create_all(monkeypatch):
    called = {"engine": None}

    def _fake_create_all(engine):
        called["engine"] = engine

    monkeypatch.setattr(database.SQLModel.metadata, "create_all", _fake_create_all)

    database.create_db_and_tables()

    assert called["engine"] is database.engine
