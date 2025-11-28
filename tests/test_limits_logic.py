import psycopg
import pytest

from tests.conftest import DummyConn, reload_module


@pytest.fixture
def limits(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(psycopg, "connect", lambda *a, **k: DummyConn())
    return reload_module("limits.main")


def test_compute_state_transitions(limits):
    assert limits._compute_state(0.5, 0.8, 1.0) == limits.STATE_OK
    assert limits._compute_state(0.85, 0.8, 1.0) == limits.STATE_NEAR_LIMIT
    assert limits._compute_state(1.0, 0.8, 1.0) == limits.STATE_AT_LIMIT
    assert limits._compute_state(1.2, 0.8, 1.0) == limits.STATE_EXCEEDED


def test_summaries_from_documents_accumulates_and_forecasts(limits):
    docs = [
        {"totals": {"gross_amount": 100}, "date": "2024-01-10"},
        {"totals": {"gross_amount": 200}, "date": "2024-02-10"},
    ]

    summary = limits._summaries_from_documents(docs)

    assert summary["accumulated"] == 300
    assert summary["monthly_totals"][1] == 100
    assert summary["monthly_totals"][2] == 200
    assert summary["forecast"] == pytest.approx(1800)

