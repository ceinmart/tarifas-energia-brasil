"""Versao: 0.1.0
Criado em: 2026-04-22 21:41:36 -03:00
Criado por: Codex
Projeto/pasta: ha.ext.tarifas
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def _load_calculators_module():
    module_path = (
        Path(__file__).resolve().parents[1]
        / "custom_components"
        / "tarifas_energia_brasil"
        / "calculators.py"
    )
    spec = importlib.util.spec_from_file_location("calculators_module", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


calc = _load_calculators_module()


def test_mwh_to_kwh_conversion():
    assert calc.mwh_to_kwh(739.69) == pytest.approx(0.73969)


def test_tributos_por_dentro():
    result = calc.aplicar_tributos_por_dentro(
        valor_sem_tributos=100.0,
        pis_decimal=0.011,
        cofins_decimal=0.0502,
        icms_decimal=0.12,
    )
    assert result == pytest.approx(122.1299, rel=1e-4)


def test_tarifa_convencional():
    bruta, final = calc.calcular_tarifa_convencional(
        te_convencional_r_kwh=0.34405,
        tusd_convencional_r_kwh=0.39564,
        pis_percent=1.10,
        cofins_percent=5.02,
        icms_percent=12.0,
    )
    assert bruta == pytest.approx(0.73969)
    assert final > bruta


def test_tarifa_branca_por_posto():
    result = calc.calcular_tarifa_branca_por_posto(
        te_por_posto_r_kwh={
            "fora_ponta": 0.32816,
            "intermediario": 0.32816,
            "ponta": 0.51884,
        },
        tusd_por_posto_r_kwh={
            "fora_ponta": 0.29282,
            "intermediario": 0.51559,
            "ponta": 0.73837,
        },
        pis_percent=1.10,
        cofins_percent=5.02,
        icms_percent=12.0,
    )
    assert result["fora_ponta"]["tarifa_bruta_r_kwh"] == pytest.approx(0.62098, rel=1e-4)
    assert result["intermediario"]["tarifa_bruta_r_kwh"] == pytest.approx(0.84375, rel=1e-4)
    assert result["ponta"]["tarifa_bruta_r_kwh"] == pytest.approx(1.25721, rel=1e-4)


def test_disponibilidade_por_tipo_fornecimento():
    assert calc.disponibilidade_minima_kwh("monofasico") == 30
    assert calc.disponibilidade_minima_kwh("bifasico") == 50
    assert calc.disponibilidade_minima_kwh("trifasico") == 100


def test_percentual_fio_b_por_ano():
    assert calc.percentual_fio_b_por_ano(2026) == pytest.approx(0.60)
    assert calc.percentual_fio_b_por_ano(2029) == pytest.approx(1.0)


def test_fio_b_bruto_e_final():
    bruto = calc.calcular_fio_b_bruto(189.008164374)
    final = calc.calcular_fio_b_final(
        fio_b_bruto_r_kwh=bruto,
        ano=2026,
        pis_percent=1.10,
        cofins_percent=5.02,
        icms_percent=12.0,
    )
    assert bruto == pytest.approx(0.189008164374)
    assert final > bruto * 0.60


def test_bandeira_tarifaria():
    value = calc.calcular_valor_bandeira(kwh_faturado=220, adicional_bandeira_r_kwh=0.01885)
    assert value == pytest.approx(4.147)


def test_scee_simplificado():
    result = calc.calcular_scee_simplificado(
        consumo_kwh=200,
        geracao_kwh=180,
        credito_entrada_kwh=0,
        tarifa_convencional_final_r_kwh=0.90,
        fio_b_final_r_kwh=0.15,
        valor_disponibilidade=27.0,
    )
    assert result["energia_compensada_kwh"] == pytest.approx(180)
    assert result["energia_nao_compensada_kwh"] == pytest.approx(20)
    assert result["valor_consumo_faturado"] >= 27.0


def test_scee_creditos_prioritarios():
    result = calc.calcular_scee_creditos_prioritarios(
        consumo_kwh=100,
        geracao_kwh=40,
        credito_entrada_kwh=80,
        tarifa_convencional_final_r_kwh=0.9,
        fio_b_final_r_kwh=0.1,
        valor_disponibilidade=20.0,
    )
    assert result["energia_compensada_kwh"] == pytest.approx(100)
    assert result["credito_consumido_kwh"] == pytest.approx(80)
    assert result["geracao_consumida_kwh"] == pytest.approx(20)
    assert result["credito_gerado_kwh"] == pytest.approx(20)
