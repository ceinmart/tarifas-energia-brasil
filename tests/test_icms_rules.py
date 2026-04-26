"""Versao: 0.1.0
Criado em: 2026-04-23 10:20:00 -03:00
Criado por: Codex
Projeto/pasta: ha.ext.tarifas
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


def _load_icms_module():
    module_path = (
        Path(__file__).resolve().parents[1]
        / "custom_components"
        / "tarifas_energia_brasil"
        / "icms_rules.py"
    )
    spec = importlib.util.spec_from_file_location("icms_rules_module", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


icms = _load_icms_module()


def test_icms_cpfl_sp_by_range():
    v1, source1 = icms.resolve_icms_percent("CPFL-PIRATINING", 80, 12.0)
    v2, source2 = icms.resolve_icms_percent("CPFL-PIRATINING", 150, 12.0)
    v3, source3 = icms.resolve_icms_percent("CPFL-PIRATINING", 250, 12.0)
    assert v1 == pytest.approx(0.0)
    assert v2 == pytest.approx(12.0)
    assert v3 == pytest.approx(18.0)
    assert source1 == source2 == source3 == "regra_faixa_consumo"


def test_icms_celesc_by_range():
    v1, _ = icms.resolve_icms_percent("CELESC", 120, 12.0)
    v2, _ = icms.resolve_icms_percent("CELESC", 200, 12.0)
    assert v1 == pytest.approx(12.0)
    assert v2 == pytest.approx(17.0)


def test_icms_rge_by_range():
    v1, _ = icms.resolve_icms_percent("RGE SUL", 40, 17.0)
    v2, _ = icms.resolve_icms_percent("RGE SUL", 60, 17.0)
    assert v1 == pytest.approx(12.0)
    assert v2 == pytest.approx(17.0)


def test_icms_fallback_without_rule():
    value, source = icms.resolve_icms_percent("CEMIG-D", 150, 18.0)
    assert value == pytest.approx(18.0)
    assert source == "fallback_sem_regra"


def test_icms_reference_uses_highest_range():
    value, source = icms.resolve_icms_reference_percent("CPFL-PIRATINING", 12.0)
    assert value == pytest.approx(18.0)
    assert source == "maior_faixa_consumo"
