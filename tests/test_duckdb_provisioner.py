"""Versao: v2
Criado em: 2026-08-31 21:50 -03:00
Alterado em: 2026-08-31 22:32 -03:00
Criado por: Codex (ChatGPT)
Projeto/pasta: ha.ext.tarifas
Finalidade: Validar selecao e instalacao atomica do DuckDB CLI.
"""

from __future__ import annotations

import asyncio
import gzip
import hashlib
import importlib.util
import sys
import threading
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

_MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "tarifas_energia_brasil"
    / "duckdb_provisioner.py"
)
_SPEC = importlib.util.spec_from_file_location("tarifas_duckdb_provisioner_test", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
provisioner = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = provisioner
_SPEC.loader.exec_module(provisioner)


@pytest.mark.parametrize(
    ("machine", "libc", "expected"),
    [
        ("x86_64", "musl", "linux-amd64-musl"),
        ("aarch64", "musl", "linux-arm64-musl"),
        ("amd64", "glibc", "linux-amd64"),
        ("arm64", "GNU libc", "linux-arm64"),
    ],
)
def test_detect_duckdb_asset(machine, libc, expected):
    assert provisioner.detect_duckdb_asset(
        system="Linux", machine=machine, libc=libc
    ).platform_id == expected


def test_detect_duckdb_asset_rejects_unsupported_platform():
    with pytest.raises(provisioner.DuckDBProvisionError):
        provisioner.detect_duckdb_asset(system="Windows", machine="amd64", libc="")


class _Content:
    def __init__(self, payload):
        self.payload = payload

    async def iter_chunked(self, _size):
        yield self.payload[:3]
        yield self.payload[3:]


class _Response:
    def __init__(self, payload):
        self.content = _Content(payload)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    def raise_for_status(self):
        return None


class _Session:
    def __init__(self, payload):
        self.payload = payload
        self.calls = 0

    def get(self, *_args, **_kwargs):
        self.calls += 1
        return _Response(self.payload)


def test_provisions_validated_binary_once(monkeypatch, tmp_path):
    binary = b"synthetic-duckdb-cli"
    archive = gzip.compress(binary)
    asset = provisioner.DuckDBAsset(
        "linux-amd64-musl", "duckdb.gz", hashlib.sha256(archive).hexdigest()
    )
    main_thread = threading.get_ident()
    detection_threads = []

    def detect():
        detection_threads.append(threading.get_ident())
        return asset

    monkeypatch.setattr(provisioner, "detect_duckdb_asset", detect)
    session = _Session(archive)
    validator = AsyncMock()

    async def run():
        installed = await provisioner.async_provision_duckdb_cli(session, tmp_path, validator)
        reused = await provisioner.async_provision_duckdb_cli(session, tmp_path, validator)
        return installed, reused

    installed, reused = asyncio.run(run())

    assert installed == reused
    assert open(installed, "rb").read() == binary
    assert session.calls == 1
    assert validator.await_count == 2
    assert detection_threads and all(item != main_thread for item in detection_threads)
    assert not list(tmp_path.rglob("*.part"))


def test_rejects_wrong_checksum_without_partial_install(monkeypatch, tmp_path):
    asset = provisioner.DuckDBAsset("linux-amd64", "duckdb.gz", "0" * 64)
    monkeypatch.setattr(provisioner, "detect_duckdb_asset", lambda: asset)

    async def run():
        await provisioner.async_provision_duckdb_cli(
            _Session(gzip.compress(b"invalid")), tmp_path, AsyncMock()
        )

    with pytest.raises(provisioner.DuckDBProvisionError, match="checksum"):
        asyncio.run(run())

    assert not list(tmp_path.rglob("duckdb"))
    assert not list(tmp_path.rglob("*.part"))
