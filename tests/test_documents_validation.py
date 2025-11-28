import psycopg
import pytest
from fastapi import HTTPException

from tests.conftest import DummyConn, reload_module


@pytest.fixture
def documents(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(psycopg, "connect", lambda *a, **k: DummyConn())
    return reload_module("documents.main")


def test_validate_cnpj_accepts_fourteen_digits(documents):
    assert documents._validate_cnpj("12345678901234") is True
    assert documents._validate_cnpj("1234567890123") is False


def test_validate_date_iso_format(documents):
    assert documents._validate_date("2024-02-29") is True
    assert documents._validate_date("29/02/2024") is False


def test_validate_document_blocks_negative_amount(documents):
    doc = {"totals": {"gross_amount": -1}, "fields": []}
    with pytest.raises(HTTPException) as exc:
        documents._validate_document(doc)
    assert exc.value.status_code == 400

