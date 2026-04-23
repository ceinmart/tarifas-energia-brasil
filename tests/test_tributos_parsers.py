"""Versao: 0.1.0
Criado em: 2026-04-23 09:00:00 -03:00
Criado por: Codex
Projeto/pasta: ha.ext.tarifas
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def _load_parser_module():
    module_path = (
        Path(__file__).resolve().parents[1]
        / "custom_components"
        / "tarifas_energia_brasil"
        / "tributos"
        / "parsers.py"
    )
    spec = importlib.util.spec_from_file_location("tributos_parser_module", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


parser = _load_parser_module()


def _read_fixture(name: str) -> str:
    fixture_path = Path(__file__).resolve().parent / "fixtures" / name
    return fixture_path.read_text(encoding="utf-8")


def test_parse_cpfl_html_fixture():
    html = _read_fixture("cpfl_pis_cofins_sample.html")
    pis, cofins, icms = parser.parse_cpfl_tributos_html(
        raw_html=html,
        fallback_pis=1.10,
        fallback_cofins=5.02,
        fallback_icms=12.0,
    )
    assert pis == pytest.approx(1.12)
    assert cofins == pytest.approx(5.12)
    assert icms == pytest.approx(12.0)


def test_parse_celesc_html_fixture():
    html = _read_fixture("celesc_tributos_sample.html")
    pis, cofins, icms = parser.parse_celesc_tributos_html(
        raw_html=html,
        fallback_pis=0.35,
        fallback_cofins=1.63,
        fallback_icms=12.0,
    )
    assert pis == pytest.approx(0.35)
    assert cofins == pytest.approx(1.63)
    assert icms == pytest.approx(12.0)


def test_parser_fallback_when_missing_fields():
    html = "<html><body><p>Pagina sem tributos.</p></body></html>"
    pis, cofins, icms = parser.parse_cpfl_tributos_html(
        raw_html=html,
        fallback_pis=1.10,
        fallback_cofins=5.02,
        fallback_icms=12.0,
    )
    assert pis == pytest.approx(1.10)
    assert cofins == pytest.approx(5.02)
    assert icms == pytest.approx(12.0)
