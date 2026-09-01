"""Versao: 0.2.4
Criado em: 2026-08-31 21:40 -03:00
Alterado em: 2026-08-31 22:32 -03:00
Criado por: Codex (ChatGPT)
Projeto/pasta: ha.ext.tarifas
Finalidade: Provisionar de modo seguro e persistente o DuckDB CLI oficial.
"""

from __future__ import annotations

import asyncio
import gzip
import hashlib
import os
import platform
import shutil
import tempfile
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path

import aiohttp

DUCKDB_CLI_VERSION = "1.5.5"
DUCKDB_RELEASE_URL = f"https://github.com/duckdb/duckdb/releases/download/v{DUCKDB_CLI_VERSION}"
DUCKDB_DOWNLOAD_MAX_BYTES = 32 * 1024 * 1024
DUCKDB_BINARY_MAX_BYTES = 100 * 1024 * 1024
DUCKDB_DOWNLOAD_TIMEOUT = aiohttp.ClientTimeout(total=300, connect=30, sock_read=120)


@dataclass(frozen=True)
class DuckDBAsset:
    """Artefato oficial permitido para uma plataforma."""

    platform_id: str
    filename: str
    sha256: str


DUCKDB_ASSETS = {
    "linux-amd64-musl": DuckDBAsset(
        "linux-amd64-musl",
        "duckdb_cli-linux-amd64-musl.gz",
        "59bc84a96f58777bb21b67129222628d0ac196bbf722d3107ceb94a8602429d2",
    ),
    "linux-arm64-musl": DuckDBAsset(
        "linux-arm64-musl",
        "duckdb_cli-linux-arm64-musl.gz",
        "b4967d323429af32f4374f92fa67b265f2b680d9b23086244327e158584df764",
    ),
    "linux-amd64": DuckDBAsset(
        "linux-amd64",
        "duckdb_cli-linux-amd64.gz",
        "c61f21485e6e41d3a0c28ce9904ea18346309cf427b4cf9479bc3564348dc885",
    ),
    "linux-arm64": DuckDBAsset(
        "linux-arm64",
        "duckdb_cli-linux-arm64.gz",
        "50c719e603a4e599d435e5321542458edc1fc5f7eed65979fe9bc5ae4e3ba23",
    ),
}

_INSTALL_LOCKS: dict[tuple[int, str], asyncio.Lock] = {}


class DuckDBProvisionError(RuntimeError):
    """Falha controlada ao localizar ou provisionar o CLI."""


def detect_duckdb_asset(
    *, system: str | None = None, machine: str | None = None, libc: str | None = None
) -> DuckDBAsset:
    """Seleciona somente artefatos Linux de arquitetura e libc conhecidas."""

    system_name = (system or platform.system()).lower()
    machine_name = (machine or platform.machine()).lower()
    if system_name != "linux":
        raise DuckDBProvisionError(f"sistema nao suportado pelo provisionador: {system_name}")

    architectures = {
        "x86_64": "amd64",
        "amd64": "amd64",
        "aarch64": "arm64",
        "arm64": "arm64",
    }
    architecture = architectures.get(machine_name)
    if architecture is None:
        raise DuckDBProvisionError(f"arquitetura nao suportada: {machine_name}")

    libc_name = libc.lower() if libc is not None else platform.libc_ver()[0].lower()
    if not libc_name and list(Path("/lib").glob("ld-musl-*.so.1")):
        libc_name = "musl"
    if "musl" in libc_name:
        platform_id = f"linux-{architecture}-musl"
    elif libc_name in {"glibc", "gnu libc", "libc"}:
        platform_id = f"linux-{architecture}"
    else:
        raise DuckDBProvisionError(f"libc nao reconhecida: {libc_name or 'desconhecida'}")
    return DUCKDB_ASSETS[platform_id]


def _extract_checked(source: Path, destination: Path, expected_sha256: str) -> None:
    """Valida o pacote comprimido e extrai com limite de tamanho."""

    digest = hashlib.sha256()
    with source.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    if digest.hexdigest() != expected_sha256:
        raise DuckDBProvisionError("checksum SHA-256 do DuckDB CLI nao confere")

    extracted = 0
    with gzip.open(source, "rb") as compressed, destination.open("wb") as output:
        while chunk := compressed.read(1024 * 1024):
            extracted += len(chunk)
            if extracted > DUCKDB_BINARY_MAX_BYTES:
                raise DuckDBProvisionError("DuckDB CLI descomprimido excedeu 100 MiB")
            output.write(chunk)
        output.flush()
        os.fsync(output.fileno())
    os.chmod(destination, 0o700)


def _append_download(path: Path, chunk: bytes) -> None:
    with path.open("ab") as output:
        output.write(chunk)


def _sync_file(path: Path) -> None:
    with path.open("ab") as handle:
        handle.flush()
        os.fsync(handle.fileno())


async def async_provision_duckdb_cli(
    session: aiohttp.ClientSession,
    root: str | Path,
    validator: Callable[[str], Awaitable[None]],
) -> str:
    """Reutiliza ou instala atomicamente o CLI oficial correspondente ao host."""

    # platform.libc_ver() pode abrir o executavel Python. A deteccao inteira
    # precisa ficar fora do event loop do Home Assistant.
    asset = await asyncio.to_thread(detect_duckdb_asset)
    target_dir = Path(root) / DUCKDB_CLI_VERSION / asset.platform_id
    target = target_dir / "duckdb"
    lock_key = (id(asyncio.get_running_loop()), str(target.resolve()))
    lock = _INSTALL_LOCKS.setdefault(lock_key, asyncio.Lock())

    async with lock:
        if target.is_file() and os.access(target, os.X_OK):
            try:
                await validator(str(target))
                return str(target)
            except (OSError, RuntimeError, ValueError):
                await asyncio.to_thread(target.unlink, missing_ok=True)

        await asyncio.to_thread(target_dir.mkdir, parents=True, exist_ok=True)
        archive_fd, archive_name = tempfile.mkstemp(suffix=".gz.part", dir=target_dir)
        binary_fd, binary_name = tempfile.mkstemp(suffix=".bin.part", dir=target_dir)
        os.close(archive_fd)
        os.close(binary_fd)
        archive = Path(archive_name)
        binary = Path(binary_name)
        try:
            downloaded = 0
            url = f"{DUCKDB_RELEASE_URL}/{asset.filename}"
            try:
                async with session.get(url, timeout=DUCKDB_DOWNLOAD_TIMEOUT) as response:
                    response.raise_for_status()
                    async for chunk in response.content.iter_chunked(64 * 1024):
                        downloaded += len(chunk)
                        if downloaded > DUCKDB_DOWNLOAD_MAX_BYTES:
                            raise DuckDBProvisionError("download do DuckDB CLI excedeu 32 MiB")
                        await asyncio.to_thread(_append_download, archive, chunk)
                await asyncio.to_thread(_sync_file, archive)
            except (aiohttp.ClientError, TimeoutError) as err:
                raise DuckDBProvisionError(f"download do DuckDB CLI falhou: {err}") from err
            await asyncio.to_thread(_extract_checked, archive, binary, asset.sha256)
            await validator(str(binary))
            await asyncio.to_thread(os.replace, binary, target)
            return str(target)
        finally:
            await asyncio.to_thread(archive.unlink, missing_ok=True)
            await asyncio.to_thread(binary.unlink, missing_ok=True)


def find_duckdb_cli_on_path() -> str | None:
    """Preserva a preferencia por um CLI administrado pelo usuario."""

    return shutil.which("duckdb")
