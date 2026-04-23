"""Versao: 0.1.0
Criado em: 2026-04-23 09:00:00 -03:00
Criado por: Codex
Projeto/pasta: ha.ext.tarifas
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class CreditoEntry:
    """Credito de energia registrado por competencia mensal."""

    competencia: str
    kwh: float


def competencia_from_cycle_key(cycle_key: str | None) -> str | None:
    """Extrai competencia (YYYY-MM) a partir da chave mensal interna."""

    if not cycle_key:
        return None
    parts = cycle_key.split("-")
    if len(parts) < 2:
        return None
    year, month = parts[0], parts[1]
    if len(year) == 4 and len(month) == 2 and year.isdigit() and month.isdigit():
        return f"{year}-{month}"
    return None


def parse_competencia(competencia: str) -> datetime:
    """Converte competencia no formato YYYY-MM para datetime."""

    return datetime.strptime(competencia, "%Y-%m")


def purge_expired_credits(
    entries: list[CreditoEntry],
    reference_competencia: str,
    validade_meses: int = 60,
) -> list[CreditoEntry]:
    """Remove creditos vencidos pela janela de validade em meses."""

    reference = parse_competencia(reference_competencia)
    kept: list[CreditoEntry] = []
    for entry in entries:
        try:
            dt = parse_competencia(entry.competencia)
        except ValueError:
            continue
        months_diff = (reference.year - dt.year) * 12 + (reference.month - dt.month)
        if 0 <= months_diff <= validade_meses and entry.kwh > 0:
            kept.append(entry)
    return sort_oldest_first(kept)


def sort_oldest_first(entries: list[CreditoEntry]) -> list[CreditoEntry]:
    """Ordena creditos da competencia mais antiga para a mais recente."""

    return sorted(entries, key=lambda item: parse_competencia(item.competencia))


def add_credit_entry(
    entries: list[CreditoEntry],
    competencia: str,
    kwh: float,
) -> list[CreditoEntry]:
    """Adiciona credito a competencia existente ou cria nova entrada."""

    if kwh <= 0:
        return sort_oldest_first(entries)

    updated = [CreditoEntry(item.competencia, item.kwh) for item in entries]
    for item in updated:
        if item.competencia == competencia:
            item.kwh += kwh
            return sort_oldest_first(updated)

    updated.append(CreditoEntry(competencia=competencia, kwh=kwh))
    return sort_oldest_first(updated)


def consume_credits_oldest_first(
    entries: list[CreditoEntry],
    consumo_kwh: float,
) -> tuple[list[CreditoEntry], float]:
    """Consome creditos mais antigos primeiro e retorna saldo atualizado."""

    required = max(consumo_kwh, 0.0)
    updated = [CreditoEntry(item.competencia, item.kwh) for item in sort_oldest_first(entries)]
    consumed = 0.0

    for item in updated:
        if required <= 0:
            break
        if item.kwh <= 0:
            continue
        use = min(item.kwh, required)
        item.kwh -= use
        required -= use
        consumed += use

    remaining = [item for item in updated if item.kwh > 1e-9]
    return remaining, consumed


def total_credits_kwh(entries: list[CreditoEntry]) -> float:
    """Soma total de creditos disponiveis no ledger."""

    return sum(max(item.kwh, 0.0) for item in entries)


def serialize_entries(entries: list[CreditoEntry]) -> list[dict[str, float | str]]:
    """Serializa entries para persistencia em storage."""

    return [{"competencia": item.competencia, "kwh": item.kwh} for item in entries]


def deserialize_entries(payload: list[dict[str, object]] | None) -> list[CreditoEntry]:
    """Converte payload persistido para lista tipada de creditos."""

    entries: list[CreditoEntry] = []
    for row in payload or []:
        comp = str(row.get("competencia", "")).strip()
        raw_kwh = row.get("kwh", 0.0)
        try:
            kwh = float(raw_kwh)
        except (TypeError, ValueError):
            continue
        if not comp or kwh <= 0:
            continue
        try:
            parse_competencia(comp)
        except ValueError:
            continue
        entries.append(CreditoEntry(competencia=comp, kwh=kwh))
    return sort_oldest_first(entries)
