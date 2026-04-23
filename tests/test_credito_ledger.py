"""Versao: 0.1.0
Criado em: 2026-04-23 09:00:00 -03:00
Criado por: Codex
Projeto/pasta: ha.ext.tarifas
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


def _load_credito_module():
    module_path = (
        Path(__file__).resolve().parents[1]
        / "custom_components"
        / "tarifas_energia_brasil"
        / "credito_ledger.py"
    )
    spec = importlib.util.spec_from_file_location("credito_module", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


credito = _load_credito_module()


def test_add_and_total_credits():
    ledger = []
    ledger = credito.add_credit_entry(ledger, "2026-01", 10.0)
    ledger = credito.add_credit_entry(ledger, "2026-02", 5.0)
    ledger = credito.add_credit_entry(ledger, "2026-01", 2.5)
    assert credito.total_credits_kwh(ledger) == pytest.approx(17.5)


def test_consume_oldest_first():
    ledger = [
        credito.CreditoEntry("2025-11", 3.0),
        credito.CreditoEntry("2025-12", 7.0),
        credito.CreditoEntry("2026-01", 8.0),
    ]
    updated, consumed = credito.consume_credits_oldest_first(ledger, 9.0)
    assert consumed == pytest.approx(9.0)
    assert len(updated) == 2
    assert updated[0].competencia == "2025-12"
    assert updated[0].kwh == pytest.approx(1.0)


def test_purge_expired_credits_60_months():
    ledger = [
        credito.CreditoEntry("2020-01", 4.0),
        credito.CreditoEntry("2021-03", 2.0),
        credito.CreditoEntry("2026-02", 1.0),
    ]
    updated = credito.purge_expired_credits(ledger, "2026-03", validade_meses=60)
    assert len(updated) == 2
    assert [item.competencia for item in updated] == ["2021-03", "2026-02"]


def test_cycle_key_to_competencia():
    assert credito.competencia_from_cycle_key("2026-04-D01") == "2026-04"
    assert credito.competencia_from_cycle_key("xpto") is None
