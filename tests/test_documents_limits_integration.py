import psycopg
import pytest

from tests.conftest import DummyConn, reload_module


class MemoryCollection:
    def __init__(self):
        self.docs = {}

    def replace_one(self, _filter, doc, upsert=False):
        self.docs[str(doc.get("_id"))] = doc

    def find_one(self, query):
        key = query.get("_id") if isinstance(query, dict) else query
        return self.docs.get(str(key))

    def find(self, query):
        tenant = query.get("tenant_id")
        date_filter = query.get("date", {})
        regex = str(date_filter.get("$regex", ""))
        ids_filter = query.get("_id")
        ids = set(str(item) for item in ids_filter.get("$in", [])) if isinstance(ids_filter, dict) else None

        results = []
        for doc_id, doc in self.docs.items():
            if ids is not None and doc_id not in ids:
                continue
            if tenant and doc.get("tenant_id") != tenant:
                continue
            if regex and not str(doc.get("date", "")).startswith(regex.strip("^")):
                continue
            results.append(doc)
        return results


@pytest.fixture
def modules(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(psycopg, "connect", lambda *a, **k: DummyConn())
    documents = reload_module("documents.main")
    limits = reload_module("limits.main")
    return documents, limits


def test_upload_to_dashboard_flow(modules, monkeypatch: pytest.MonkeyPatch):
    documents, limits = modules
    memory = MemoryCollection()
    events: list[tuple[str, dict]] = []
    snapshots: list[dict] = []

    documents.documents_collection = memory
    limits.documents_collection = memory
    monkeypatch.setattr(documents, "_record_audit", lambda *a, **k: None)
    monkeypatch.setattr(documents, "_publish_event", lambda name, payload: events.append((name, payload)))
    monkeypatch.setattr(limits, "_publish_event", lambda name, payload: events.append((name, payload)))
    monkeypatch.setattr(limits, "_get_limit_config", lambda year: {"annual_limit": 1000.0, "warn": 0.8, "critical": 1.0})

    def fake_persist(tenant_id, year, monthly_totals, forecast, config):
        cumulative = 0.0
        for month in range(1, 13):
            cumulative += monthly_totals.get(month, 0.0)
            ratio = max(cumulative, forecast) / config["annual_limit"] if config["annual_limit"] else 0.0
            state = limits._compute_state(ratio, config["warn"], config["critical"])
            snapshots.append({"month": month, "state": state, "accumulated": cumulative, "forecast": forecast})

    monkeypatch.setattr(limits, "_persist_snapshots", fake_persist)

    memory.replace_one(
        {"_id": "doc1"},
        {
            "_id": "doc1",
            "tenant_id": "t1",
            "storage": {"mock_text": "total 123.50\n2024-03-10\n12345678901234"},
        },
        upsert=True,
    )

    documents._run_ocr_pipeline("doc1", tenant_id="t1")
    documents.patch_doc(
        "doc1",
        [documents.PatchChange(path="totals.gross_amount", value=200.0, source="user")],
        x_user_id="user-1",
    )

    limits.fields_updated({"doc_id": "doc1"})
    dashboard = limits.dashboard(2024, tenant_id="t1")

    assert any(event == documents.EVENT_FIELDS_UPDATED for event, _ in events)
    assert any(event == documents.EVENT_LIMITS_RECALCULATED or event == limits.EVENT_LIMITS_RECALCULATED for event, _ in events)
    assert len(snapshots) == 12
    assert dashboard.state in {limits.STATE_NEAR_LIMIT, limits.STATE_EXCEEDED}

