"""Versao: 0.1.0
Criado em: 2026-04-23 17:15:00 -03:00
Criado por: Codex
Projeto/pasta: ha.ext.tarifas
"""

from __future__ import annotations

import importlib.util
import sys
import types
from enum import StrEnum
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest


def _install_fake_homeassistant_modules() -> None:
    """Instala stubs minimos para importar const.py sem Home Assistant real."""

    homeassistant = sys.modules.get("homeassistant", types.ModuleType("homeassistant"))
    const = sys.modules.get("homeassistant.const", types.ModuleType("homeassistant.const"))

    class Platform(StrEnum):
        SENSOR = "sensor"

    const.Platform = Platform
    homeassistant.const = const

    sys.modules["homeassistant"] = homeassistant
    sys.modules["homeassistant.const"] = const


_install_fake_homeassistant_modules()


def _load_package_module(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_BASE_DIR = Path(__file__).resolve().parents[1] / "custom_components" / "tarifas_energia_brasil"
_PKG_NAME = "tarifas_energia_brasil_testpkg_time"

if _PKG_NAME not in sys.modules:
    pkg = types.ModuleType(_PKG_NAME)
    pkg.__path__ = [str(_BASE_DIR)]  # type: ignore[attr-defined]
    sys.modules[_PKG_NAME] = pkg

const_module = _load_package_module(f"{_PKG_NAME}.const", _BASE_DIR / "const.py")
tb_time = _load_package_module(
    f"{_PKG_NAME}.tarifa_branca_time",
    _BASE_DIR / "tarifa_branca_time.py",
)

CONF_CONCESSIONARIA = const_module.CONF_CONCESSIONARIA
CONF_TB_INTERMEDIARIO1_FIM = const_module.CONF_TB_INTERMEDIARIO1_FIM
CONF_TB_INTERMEDIARIO1_INICIO = const_module.CONF_TB_INTERMEDIARIO1_INICIO
CONF_TB_INTERMEDIARIO2_FIM = const_module.CONF_TB_INTERMEDIARIO2_FIM
CONF_TB_INTERMEDIARIO2_INICIO = const_module.CONF_TB_INTERMEDIARIO2_INICIO
CONF_TB_PONTA_FIM = const_module.CONF_TB_PONTA_FIM
CONF_TB_PONTA_INICIO = const_module.CONF_TB_PONTA_INICIO


def test_resolve_tarifa_branca_schedule_defaults_cpfl_piratininga():
    schedule, metadata = tb_time.resolve_tarifa_branca_schedule(
        {CONF_CONCESSIONARIA: "CPFL-PIRATINING"}
    )
    assert metadata["source"] == "default_concessionaria"
    assert schedule.ponta_inicio.hour == 18
    assert schedule.ponta_fim.hour == 21


def test_resolve_tarifa_branca_schedule_accepts_override():
    schedule, metadata = tb_time.resolve_tarifa_branca_schedule(
        {
            CONF_CONCESSIONARIA: "CPFL-PIRATINING",
            CONF_TB_PONTA_INICIO: "17:30",
            CONF_TB_PONTA_FIM: "20:30",
            CONF_TB_INTERMEDIARIO1_INICIO: "16:30",
            CONF_TB_INTERMEDIARIO1_FIM: "17:30",
            CONF_TB_INTERMEDIARIO2_INICIO: "20:30",
            CONF_TB_INTERMEDIARIO2_FIM: "21:30",
        }
    )
    assert metadata["override_used"] is True
    assert schedule.source == "user_override"
    assert schedule.ponta_inicio.hour == 17
    assert schedule.ponta_inicio.minute == 30


def test_parse_extra_holidays_tracks_invalid_valores():
    holidays, invalid = tb_time.parse_extra_holidays("2026-12-24\ninvalido\n2026-12-31")
    assert len(holidays) == 2
    assert invalid == ["invalido"]


def test_weekend_is_always_fora_ponta():
    tz = ZoneInfo("America/Sao_Paulo")
    schedule, _metadata = tb_time.resolve_tarifa_branca_schedule(
        {CONF_CONCESSIONARIA: "CPFL-PIRATINING"}
    )
    holidays = tb_time.build_holiday_calendar([2026])
    instant = __import__("datetime").datetime(2026, 5, 2, 19, 0, tzinfo=tz)  # sabado
    posto = tb_time.resolve_tarifa_branca_posto(instant, schedule, holidays)
    assert posto == "fora_ponta"


def test_feriado_nacional_is_fora_ponta():
    tz = ZoneInfo("America/Sao_Paulo")
    schedule, _metadata = tb_time.resolve_tarifa_branca_schedule(
        {CONF_CONCESSIONARIA: "CPFL-PIRATINING"}
    )
    holidays = tb_time.build_holiday_calendar([2026])
    instant = __import__("datetime").datetime(2026, 11, 20, 19, 0, tzinfo=tz)
    posto = tb_time.resolve_tarifa_branca_posto(instant, schedule, holidays)
    assert posto == "fora_ponta"


def test_split_interval_respects_tariff_boundary():
    tz = ZoneInfo("America/Sao_Paulo")
    schedule, _metadata = tb_time.resolve_tarifa_branca_schedule(
        {CONF_CONCESSIONARIA: "CPFL-PIRATINING"}
    )
    holidays = tb_time.build_holiday_calendar([2026])
    from datetime import datetime

    segments = tb_time.split_interval_by_tarifa_branca(
        datetime(2026, 4, 27, 20, 50, tzinfo=tz),
        datetime(2026, 4, 27, 21, 10, tzinfo=tz),
        schedule,
        holidays,
    )
    assert [segment[2] for segment in segments] == ["ponta", "intermediario"]
    assert (segments[0][1] - segments[0][0]).total_seconds() == pytest.approx(600)
    assert (segments[1][1] - segments[1][0]).total_seconds() == pytest.approx(600)


def test_ratear_delta_tarifa_branca_divide_por_tempo():
    tz = ZoneInfo("America/Sao_Paulo")
    schedule, _metadata = tb_time.resolve_tarifa_branca_schedule(
        {CONF_CONCESSIONARIA: "CPFL-PIRATINING"}
    )
    holidays = tb_time.build_holiday_calendar([2026])
    from datetime import datetime

    alloc, diagnosticos = tb_time.ratear_delta_tarifa_branca(
        datetime(2026, 4, 27, 20, 50, tzinfo=tz),
        datetime(2026, 4, 27, 21, 10, tzinfo=tz),
        3.0,
        schedule,
        holidays,
    )
    assert alloc["ponta"] == pytest.approx(1.5)
    assert alloc["intermediario"] == pytest.approx(1.5)
    assert diagnosticos["segment_count"] == 2
