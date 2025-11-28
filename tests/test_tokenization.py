import psycopg
import pytest

from tests.conftest import DummyConn, reload_module


@pytest.fixture
def orchestrator(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(psycopg, "connect", lambda *a, **k: DummyConn())
    return reload_module("orchestrator.main")


def test_tokenize_splits_and_normalizes(orchestrator):
    tokens = orchestrator._tokenize("Hello, World! 123")
    assert tokens == ["hello", "world", "123"]


def test_lexical_score_rewards_overlap(orchestrator):
    score = orchestrator._lexical_score("abc def", ["def", "xyz"])
    assert score == pytest.approx(0.5)

