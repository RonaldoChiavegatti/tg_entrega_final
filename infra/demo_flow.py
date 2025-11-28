"""Demonstra o fluxo presign → upload → PATCH → painel de limites sem depender de infra externa.

Uso:
    DEFAULT_TENANT_ID=demo STORAGE_BACKEND=filesystem python infra/demo_flow.py

O script:
- Gera um documento sintético com texto base.
- Faz presign e upload para o backend filesystem.
- Recarrega `documents` e `limits` com conexões dummy.
- Aplica PATCH com validação/audit e recalcula limites, medindo o SLA (<5s).
"""

from __future__ import annotations

import importlib
import json
import os
import sys
import time
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

# Evita dependência de S3/Redis reais
os.environ.setdefault("STORAGE_BACKEND", "filesystem")
os.environ.setdefault("FILESYSTEM_STORAGE_ROOT", str(Path("./.demo_storage").resolve()))
os.environ.setdefault("DEFAULT_TENANT_ID", "demo")

BASE_DIR = Path(__file__).resolve().parents[1]
SERVICES_PATH = BASE_DIR / "services"
if str(SERVICES_PATH) not in sys.path:
    sys.path.append(str(SERVICES_PATH))
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

import psycopg  # noqa: E402
from documents import storage_s3  # noqa: E402
from infra.synthetic_data import SyntheticDoc, generate_synthetic_documents  # noqa: E402


def _ensure_demo_dependencies() -> None:
    """Injeta stubs mínimos para módulos ausentes (opentelemetry, etc.)."""

    if "opentelemetry" in sys.modules:
        return

    class _TracerProvider:
        def __init__(self, *args, **kwargs):
            pass

        def add_span_processor(self, *args, **kwargs):
            return None

    class _BatchSpanProcessor:
        def __init__(self, *args, **kwargs):
            pass

    class _Resource:
        @staticmethod
        def create(*args, **kwargs):
            return None

    class _RequestsInstrumentor:
        def instrument(self, *args, **kwargs):
            return None

    class _FastAPIInstrumentor:
        @staticmethod
        def instrument_app(*args, **kwargs):
            return None

    baggage = types.SimpleNamespace(set_baggage=lambda *a, **k: None)
    context_mod = types.SimpleNamespace(
        get_current=lambda: None,
        attach=lambda ctx: None,
        detach=lambda token: None,
    )
    trace_mod = types.SimpleNamespace(set_tracer_provider=lambda *a, **k: None)
    exporter = types.SimpleNamespace(OTLPSpanExporter=lambda *a, **k: None)
    fastapi_inst = types.SimpleNamespace(FastAPIInstrumentor=_FastAPIInstrumentor)
    requests_inst = types.SimpleNamespace(RequestsInstrumentor=_RequestsInstrumentor)
    resource_mod = types.SimpleNamespace(Resource=_Resource)
    tracer_provider = types.SimpleNamespace(TracerProvider=_TracerProvider)
    span_processor = types.SimpleNamespace(BatchSpanProcessor=_BatchSpanProcessor)

    stubs = {
        "opentelemetry": types.SimpleNamespace(baggage=baggage, context=context_mod, trace=trace_mod),
        "opentelemetry.baggage": baggage,
        "opentelemetry.context": context_mod,
        "opentelemetry.trace": trace_mod,
        "opentelemetry.exporter.otlp.proto.http.trace_exporter": exporter,
        "opentelemetry.instrumentation.fastapi": fastapi_inst,
        "opentelemetry.instrumentation.requests": requests_inst,
        "opentelemetry.sdk.resources": resource_mod,
        "opentelemetry.sdk.trace": tracer_provider,
        "opentelemetry.sdk.trace.export": span_processor,
    }

    for name, module in stubs.items():
        sys.modules[name] = module


class DummyCursor:
    def __init__(self, sink: list[Dict[str, Any]]):
        self.sink = sink

    def execute(self, query: str, params: Optional[Iterable[Any]] = None):
        self.sink.append({"query": query.strip(), "params": list(params or [])})

    def fetchone(self):
        return None

    def fetchall(self):
        return []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class DummyConn:
    def __init__(self):
        self.statements: list[Dict[str, Any]] = []

    def cursor(self):
        return DummyCursor(self.statements)

    def close(self):
        return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class MemoryCollection:
    def __init__(self):
        self.docs: Dict[str, Dict[str, Any]] = {}

    def replace_one(self, _filter: Dict[str, Any], doc: Dict[str, Any], upsert: bool = False):
        self.docs[str(doc.get("_id"))] = doc

    def find_one(self, query: Dict[str, Any]):
        key = query.get("_id") if isinstance(query, dict) else query
        return self.docs.get(str(key))

    def find(self, query: Dict[str, Any]):
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


@dataclass
class DemoResult:
    doc_id: str
    presign_key: str
    storage_path: Path
    audit_entries: int
    updated_fields: List[str]
    dashboard_state: str
    elapsed_ms: float


class DemoRunner:
    def __init__(self, tenant: str):
        self.tenant = tenant
        self.events: list[Tuple[str, Dict[str, Any]]] = []
        self.audit_conn = DummyConn()
        self.limit_conn = DummyConn()

    def _reload_modules(self):
        _ensure_demo_dependencies()
        psycopg.connect = lambda *a, **k: DummyConn()  # type: ignore[assignment]
        documents = importlib.reload(importlib.import_module("documents.main"))
        limits = importlib.reload(importlib.import_module("limits.main"))
        return documents, limits

    def _wire_dependencies(self, documents, limits, memory: MemoryCollection):
        documents.documents_collection = memory
        documents.mongo_client = None
        documents.pg_conn = self.audit_conn
        documents._publish_event = lambda name, payload: self.events.append((name, payload))

        limits.documents_collection = memory
        limits.mongo_client = None
        limits.get_conn = lambda: self.limit_conn
        limits._publish_event = lambda name, payload: self.events.append((name, payload))

    def _seed_document(self, memory: MemoryCollection, doc: SyntheticDoc) -> None:
        memory.replace_one(
            {"_id": doc.doc_id},
            {
                "_id": doc.doc_id,
                "tenant_id": doc.tenant_id,
                "storage": {"mock_text": doc.text},
            },
            upsert=True,
        )

    def run(self) -> DemoResult:
        documents, limits = self._reload_modules()
        memory = MemoryCollection()
        self._wire_dependencies(documents, limits, memory)

        synthetic = generate_synthetic_documents(count=1, error_ratio=0.0, seed=42, tenant_id=self.tenant)[0]
        presigned = storage_s3.presign_put(f"demo/{synthetic.doc_id}.txt", "text/plain", self.tenant)
        uploaded = storage_s3.upload_via_presign(presigned, synthetic.text.encode("utf-8"), content_type="text/plain")
        self._seed_document(memory, synthetic)

        start = time.perf_counter()
        patch_changes = [
            documents.PatchChange(path="totals.gross_amount", value=250.0, source="demo"),
            documents.PatchChange(path="storage.mock_text", value="demo patch", source="demo"),
        ]
        documents._run_ocr_pipeline(synthetic.doc_id, tenant_id=self.tenant)
        documents.patch_doc(
            synthetic.doc_id,
            patch_changes,
            x_user_id="demo-user",
        )
        dashboard = limits.recalc_limits(self.tenant, year=time.gmtime().tm_year, doc_ids=[synthetic.doc_id])
        elapsed_ms = (time.perf_counter() - start) * 1000

        return DemoResult(
            doc_id=synthetic.doc_id,
            presign_key=str(presigned["key"]),
            storage_path=Path(uploaded.get("path", "")),
            audit_entries=len(self.audit_conn.statements),
            updated_fields=[change.path for change in patch_changes],
            dashboard_state=dashboard.state,
            elapsed_ms=elapsed_ms,
        )


def main() -> None:
    tenant = os.getenv("DEFAULT_TENANT_ID", "demo")
    runner = DemoRunner(tenant)
    result = runner.run()

    print(
        json.dumps(
            {
                "doc_id": result.doc_id,
                "tenant": tenant,
                "presigned_key": result.presign_key,
                "storage_path": str(result.storage_path),
                "audit_entries": result.audit_entries,
                "dashboard_state": result.dashboard_state,
                "elapsed_ms": round(result.elapsed_ms, 2),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
