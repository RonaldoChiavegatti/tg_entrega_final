import importlib
import sys
from pathlib import Path
from types import ModuleType
from typing import Iterable

import pytest


class DummyCursor:
    def __init__(self, fetchone_result=None, fetchall_results: Iterable = ()):  # type: ignore[assignment]
        self.statements = []
        self.fetchone_result = fetchone_result
        self.fetchall_results = list(fetchall_results)

    def execute(self, *args, **kwargs):
        self.statements.append((args, kwargs))

    def fetchone(self):
        return self.fetchone_result

    def fetchall(self):
        return self.fetchall_results

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class DummyConn:
    def __init__(self, cursor: DummyCursor | None = None):
        self._cursor = cursor or DummyCursor()

    def cursor(self):
        return self._cursor

    def close(self):
        return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


@pytest.fixture(autouse=True)
def add_services_to_path(monkeypatch: pytest.MonkeyPatch) -> None:
    base = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(base / "services"))


def reload_module(module_name: str) -> ModuleType:
    to_delete = [name for name in sys.modules if name == module_name or name.startswith(f"{module_name}.")]
    for name in to_delete:
        sys.modules.pop(name, None)
    return importlib.import_module(module_name)

