"""Versao: 0.1.0
Criado em: 2026-04-23 17:20:00 -03:00
Criado por: Codex
Projeto/pasta: ha.ext.tarifas
"""

from __future__ import annotations

import importlib.util
import sys
import types
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

import pytest


def _install_homeassistant_stub() -> None:
    """Instala stubs minimos do Home Assistant para carregar o coordinator."""

    homeassistant = sys.modules.get("homeassistant", types.ModuleType("homeassistant"))
    config_entries = sys.modules.get(
        "homeassistant.config_entries",
        types.ModuleType("homeassistant.config_entries"),
    )
    core = sys.modules.get("homeassistant.core", types.ModuleType("homeassistant.core"))
    const = sys.modules.get("homeassistant.const", types.ModuleType("homeassistant.const"))
    helpers = sys.modules.get("homeassistant.helpers", types.ModuleType("homeassistant.helpers"))
    aiohttp_client = sys.modules.get(
        "homeassistant.helpers.aiohttp_client",
        types.ModuleType("homeassistant.helpers.aiohttp_client"),
    )
    event = sys.modules.get(
        "homeassistant.helpers.event",
        types.ModuleType("homeassistant.helpers.event"),
    )
    storage = sys.modules.get(
        "homeassistant.helpers.storage",
        types.ModuleType("homeassistant.helpers.storage"),
    )
    update_coordinator = sys.modules.get(
        "homeassistant.helpers.update_coordinator",
        types.ModuleType("homeassistant.helpers.update_coordinator"),
    )

    class Platform(StrEnum):
        SENSOR = "sensor"

    @dataclass
    class ConfigEntry:
        data: dict
        options: dict
        entry_id: str = "test-entry"

    class HomeAssistant:
        pass

    def callback(func):  # noqa: ANN001
        return func

    def async_get_clientsession(hass):  # noqa: ANN001
        return None

    def async_track_state_change_event(*args, **kwargs):  # noqa: ANN001
        return None

    class Store:
        def __init__(self, *args, **kwargs) -> None:  # noqa: ANN001
            return None

        def __class_getitem__(cls, item):  # noqa: ANN001
            return cls

        async def async_load(self):
            return None

        async def async_save(self, payload):  # noqa: ANN001
            return None

        def async_delay_save(self, serializer, delay):  # noqa: ANN001
            return None

    class UpdateFailed(Exception):
        pass

    class DataUpdateCoordinator:
        def __class_getitem__(cls, item):  # noqa: ANN001
            return cls

        def __init__(self, *args, **kwargs) -> None:  # noqa: ANN001
            self.data = None
            self.last_update_success = True
            self.last_exception = None

        def async_update_listeners(self) -> None:
            return None

    const.Platform = getattr(const, "Platform", Platform)
    config_entries.ConfigEntry = getattr(config_entries, "ConfigEntry", ConfigEntry)
    core.callback = getattr(core, "callback", callback)
    core.HomeAssistant = getattr(core, "HomeAssistant", HomeAssistant)
    aiohttp_client.async_get_clientsession = async_get_clientsession
    event.async_track_state_change_event = async_track_state_change_event
    storage.Store = getattr(storage, "Store", Store)
    update_coordinator.DataUpdateCoordinator = getattr(
        update_coordinator,
        "DataUpdateCoordinator",
        DataUpdateCoordinator,
    )
    update_coordinator.UpdateFailed = getattr(
        update_coordinator,
        "UpdateFailed",
        UpdateFailed,
    )

    homeassistant.config_entries = config_entries
    homeassistant.core = core
    homeassistant.const = const
    homeassistant.helpers = helpers

    sys.modules["homeassistant"] = homeassistant
    sys.modules["homeassistant.config_entries"] = config_entries
    sys.modules["homeassistant.core"] = core
    sys.modules["homeassistant.const"] = const
    sys.modules["homeassistant.helpers"] = helpers
    sys.modules["homeassistant.helpers.aiohttp_client"] = aiohttp_client
    sys.modules["homeassistant.helpers.event"] = event
    sys.modules["homeassistant.helpers.storage"] = storage
    sys.modules["homeassistant.helpers.update_coordinator"] = update_coordinator


def _install_aiohttp_stub() -> None:
    """Instala stub minimo do aiohttp quando indisponivel no ambiente."""

    if "aiohttp" in sys.modules:
        return

    aiohttp = types.ModuleType("aiohttp")

    class ClientSession:
        pass

    class ClientError(Exception):
        pass

    aiohttp.ClientSession = ClientSession
    aiohttp.ClientError = ClientError
    sys.modules["aiohttp"] = aiohttp


def _load_module(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_install_homeassistant_stub()
_install_aiohttp_stub()

_BASE_DIR = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "tarifas_energia_brasil"
)
_PKG_NAME = "tarifas_energia_brasil_testpkg_coordinator"

if _PKG_NAME not in sys.modules:
    pkg = types.ModuleType(_PKG_NAME)
    pkg.__path__ = [str(_BASE_DIR)]  # type: ignore[attr-defined]
    sys.modules[_PKG_NAME] = pkg

const_module = _load_module(f"{_PKG_NAME}.const", _BASE_DIR / "const.py")
_load_module(f"{_PKG_NAME}.models", _BASE_DIR / "models.py")
_load_module(f"{_PKG_NAME}.calculators", _BASE_DIR / "calculators.py")
_load_module(f"{_PKG_NAME}.credito_ledger", _BASE_DIR / "credito_ledger.py")
_load_module(f"{_PKG_NAME}.icms_rules", _BASE_DIR / "icms_rules.py")
tarifa_branca_module = _load_module(
    f"{_PKG_NAME}.tarifa_branca_time",
    _BASE_DIR / "tarifa_branca_time.py",
)
_load_module(f"{_PKG_NAME}.aneel_client", _BASE_DIR / "aneel_client.py")
_load_module(f"{_PKG_NAME}.tributos.parsers", _BASE_DIR / "tributos" / "parsers.py")
_load_module(f"{_PKG_NAME}.tributos", _BASE_DIR / "tributos" / "__init__.py")
coordinator_module = _load_module(f"{_PKG_NAME}.coordinator", _BASE_DIR / "coordinator.py")

TarifasEnergiaBrasilCoordinator = coordinator_module.TarifasEnergiaBrasilCoordinator
BREAKDOWN_MONTHLY = const_module.BREAKDOWN_MONTHLY
BREAKDOWN_DAILY = const_module.BREAKDOWN_DAILY
BREAKDOWN_WEEKLY = const_module.BREAKDOWN_WEEKLY
CONF_CONCESSIONARIA = const_module.CONF_CONCESSIONARIA
resolve_tarifa_branca_schedule = tarifa_branca_module.resolve_tarifa_branca_schedule


def _build_coordinator() -> object:
    coordinator = TarifasEnergiaBrasilCoordinator.__new__(TarifasEnergiaBrasilCoordinator)
    coordinator._tarifa_branca_last_interval_seconds = 0.0
    coordinator._tarifa_branca_last_segment_count = 0
    coordinator._tarifa_branca_low_confidence = False
    return coordinator


def test_prepare_delta_context_reinitializes_reference_when_sensor_resets():
    coordinator = _build_coordinator()
    now = datetime(2026, 4, 23, 15, 0, tzinfo=UTC)
    context = coordinator._prepare_delta_context(
        current_total_kwh=291.83,
        current_timestamp=now,
        last_total_kwh=1280.5,
        last_timestamp=now,
    )

    assert context["reset_detected"] is True
    assert context["raw_delta_kwh"] == pytest.approx(-988.67)
    assert context["delta_kwh"] == pytest.approx(0.0)


def test_scalar_period_state_does_not_copy_reset_total_to_every_breakdown():
    coordinator = _build_coordinator()
    now = datetime(2026, 4, 23, 15, 0, tzinfo=UTC)
    period_state = TarifasEnergiaBrasilCoordinator._new_period_state()
    period_state[BREAKDOWN_DAILY]["key"] = "2026-04-23"
    period_state[BREAKDOWN_DAILY]["kwh"] = 12.0
    period_state[BREAKDOWN_WEEKLY]["key"] = "2026-W17"
    period_state[BREAKDOWN_WEEKLY]["kwh"] = 80.0
    period_state[BREAKDOWN_MONTHLY]["key"] = "2026-04-D01"
    period_state[BREAKDOWN_MONTHLY]["kwh"] = 291.83
    delta_context = {
        "has_previous": True,
        "delta_kwh": 0.0,
        "raw_delta_kwh": -988.67,
        "reset_detected": True,
        "start": now,
        "end": now,
    }

    values, _rollovers = coordinator._apply_scalar_delta_context(
        period_state,
        now,
        reading_day=1,
        delta_context=delta_context,
    )

    assert values[BREAKDOWN_DAILY] == pytest.approx(12.0)
    assert values[BREAKDOWN_WEEKLY] == pytest.approx(80.0)
    assert values[BREAKDOWN_MONTHLY] == pytest.approx(291.83)


def test_scalar_period_state_resets_when_update_ends_at_midnight():
    coordinator = _build_coordinator()
    start = datetime(2026, 4, 23, 23, 0, tzinfo=UTC)
    end = datetime(2026, 4, 24, 0, 0, tzinfo=UTC)
    period_state = TarifasEnergiaBrasilCoordinator._new_period_state()
    period_state[BREAKDOWN_DAILY]["key"] = "2026-04-23"
    period_state[BREAKDOWN_DAILY]["kwh"] = 12.0
    period_state[BREAKDOWN_WEEKLY]["key"] = "2026-W17"
    period_state[BREAKDOWN_WEEKLY]["kwh"] = 80.0
    period_state[BREAKDOWN_MONTHLY]["key"] = "2026-03-D24"
    period_state[BREAKDOWN_MONTHLY]["kwh"] = 605.29
    delta_context = {
        "has_previous": True,
        "delta_kwh": 2.0,
        "raw_delta_kwh": 2.0,
        "reset_detected": False,
        "start": start,
        "end": end,
    }

    values, rollovers = coordinator._apply_scalar_delta_context(
        period_state,
        end,
        reading_day=24,
        delta_context=delta_context,
    )

    assert values[BREAKDOWN_DAILY] == pytest.approx(0.0)
    assert values[BREAKDOWN_WEEKLY] == pytest.approx(82.0)
    assert values[BREAKDOWN_MONTHLY] == pytest.approx(0.0)
    assert period_state[BREAKDOWN_DAILY]["key"] == "2026-04-24"
    assert period_state[BREAKDOWN_MONTHLY]["key"] == "2026-04-D24"
    assert dict(rollovers[BREAKDOWN_DAILY])["2026-04-23"] == pytest.approx(14.0)
    assert dict(rollovers[BREAKDOWN_MONTHLY])["2026-03-D24"] == pytest.approx(607.29)


def test_scalar_period_state_resets_week_when_update_ends_on_monday_midnight():
    coordinator = _build_coordinator()
    start = datetime(2026, 4, 26, 23, 0, tzinfo=UTC)
    end = datetime(2026, 4, 27, 0, 0, tzinfo=UTC)
    period_state = TarifasEnergiaBrasilCoordinator._new_period_state()
    period_state[BREAKDOWN_DAILY]["key"] = "2026-04-26"
    period_state[BREAKDOWN_DAILY]["kwh"] = 8.0
    period_state[BREAKDOWN_WEEKLY]["key"] = "2026-W17"
    period_state[BREAKDOWN_WEEKLY]["kwh"] = 95.0
    period_state[BREAKDOWN_MONTHLY]["key"] = "2026-04-D24"
    period_state[BREAKDOWN_MONTHLY]["kwh"] = 20.0
    delta_context = {
        "has_previous": True,
        "delta_kwh": 3.0,
        "raw_delta_kwh": 3.0,
        "reset_detected": False,
        "start": start,
        "end": end,
    }

    values, rollovers = coordinator._apply_scalar_delta_context(
        period_state,
        end,
        reading_day=24,
        delta_context=delta_context,
    )

    assert values[BREAKDOWN_DAILY] == pytest.approx(0.0)
    assert values[BREAKDOWN_WEEKLY] == pytest.approx(0.0)
    assert values[BREAKDOWN_MONTHLY] == pytest.approx(23.0)
    assert period_state[BREAKDOWN_WEEKLY]["key"] == "2026-W18"
    assert dict(rollovers[BREAKDOWN_WEEKLY])["2026-W17"] == pytest.approx(98.0)


def test_tarifa_branca_state_does_not_copy_reset_total_to_current_posto():
    coordinator = _build_coordinator()
    now = datetime(2026, 4, 23, 15, 0, tzinfo=UTC)
    period_state = TarifasEnergiaBrasilCoordinator._new_posto_period_state()
    period_state[BREAKDOWN_MONTHLY]["key"] = "2026-04-D01"
    period_state[BREAKDOWN_MONTHLY]["postos"]["fora_ponta"] = 120.0
    schedule, _metadata = resolve_tarifa_branca_schedule(
        {CONF_CONCESSIONARIA: "CPFL-PIRATINING"}
    )
    delta_context = {
        "has_previous": True,
        "delta_kwh": 0.0,
        "raw_delta_kwh": -988.67,
        "reset_detected": True,
        "start": now,
        "end": now,
    }

    values, _rollovers = coordinator._apply_tarifa_branca_delta_context(
        period_state,
        now,
        reading_day=1,
        delta_context=delta_context,
        schedule=schedule,
        holidays=set(),
    )

    assert values[BREAKDOWN_MONTHLY]["fora_ponta"] == pytest.approx(120.0)
    assert values[BREAKDOWN_MONTHLY]["intermediario"] == pytest.approx(0.0)
    assert values[BREAKDOWN_MONTHLY]["ponta"] == pytest.approx(0.0)
    assert coordinator._tarifa_branca_low_confidence is False


def test_dynamic_values_calculate_auto_consumo_from_generated_minus_injected():
    coordinator = _build_coordinator()
    coordinator._creditos_ledger = [coordinator_module.CreditoEntry("2026-03", 80.0)]

    values = {
        "tarifa_convencional_final_r_kwh": 0.9,
        "adicional_bandeira_r_kwh": 0.0,
        "fio_b_final_r_kwh": 0.1,
    }
    consumo_periodos = {
        BREAKDOWN_DAILY: 0.0,
        BREAKDOWN_WEEKLY: 0.0,
        BREAKDOWN_MONTHLY: 100.0,
    }
    geracao_periodos = {
        BREAKDOWN_DAILY: 0.0,
        BREAKDOWN_WEEKLY: 0.0,
        BREAKDOWN_MONTHLY: 40.0,
    }
    injecao_periodos = {
        BREAKDOWN_DAILY: 0.0,
        BREAKDOWN_WEEKLY: 0.0,
        BREAKDOWN_MONTHLY: 0.0,
    }
    consumo_tarifa_branca = {
        period: {"fora_ponta": 0.0, "intermediario": 0.0, "ponta": 0.0}
        for period in (BREAKDOWN_DAILY, BREAKDOWN_WEEKLY, BREAKDOWN_MONTHLY)
    }

    coordinator._apply_dynamic_values_to_snapshot(
        values=values,
        enabled_breakdowns=[BREAKDOWN_MONTHLY],
        consumo_periodos=consumo_periodos,
        geracao_periodos=geracao_periodos,
        injecao_periodos=injecao_periodos,
        consumo_tarifa_branca=consumo_tarifa_branca,
        has_generation=True,
        has_injection=False,
        geracao_total_kwh=40.0,
        injecao_total_kwh=None,
        tipo_fornecimento="monofasico",
    )

    assert values["auto_consumo_kwh"] == pytest.approx(20.0)
    assert values["auto_consumo_reais"] == pytest.approx(18.0)


def test_dynamic_values_calculate_auto_consumo_from_injection_entity_totals():
    coordinator = _build_coordinator()
    coordinator._creditos_ledger = []

    values = {
        "tarifa_convencional_final_r_kwh": 0.9748154981549815,
        "adicional_bandeira_r_kwh": 0.0,
        "fio_b_final_r_kwh": 0.14945295021665786,
    }
    consumo_periodos = {
        BREAKDOWN_DAILY: 302.43,
        BREAKDOWN_WEEKLY: 302.43,
        BREAKDOWN_MONTHLY: 302.43,
    }
    geracao_periodos = {
        BREAKDOWN_DAILY: 0.0,
        BREAKDOWN_WEEKLY: 0.0,
        BREAKDOWN_MONTHLY: 0.0,
    }
    injecao_periodos = {
        BREAKDOWN_DAILY: 0.0,
        BREAKDOWN_WEEKLY: 0.0,
        BREAKDOWN_MONTHLY: 0.0,
    }
    consumo_tarifa_branca = {
        period: {"fora_ponta": 0.0, "intermediario": 0.0, "ponta": 0.0}
        for period in (BREAKDOWN_DAILY, BREAKDOWN_WEEKLY, BREAKDOWN_MONTHLY)
    }

    coordinator._apply_dynamic_values_to_snapshot(
        values=values,
        enabled_breakdowns=[BREAKDOWN_MONTHLY],
        consumo_periodos=consumo_periodos,
        geracao_periodos=geracao_periodos,
        injecao_periodos=injecao_periodos,
        consumo_tarifa_branca=consumo_tarifa_branca,
        has_generation=True,
        has_injection=True,
        geracao_total_kwh=311.9,
        injecao_total_kwh=201.82,
        tipo_fornecimento="trifasico",
    )

    assert values["auto_consumo_kwh"] == pytest.approx(110.08)


def test_dynamic_values_apply_disponibilidade_only_to_monthly_bill_values():
    coordinator = _build_coordinator()
    coordinator._creditos_ledger = []

    values = {
        "tarifa_convencional_final_r_kwh": 0.7879100979974435,
        "tarifa_branca_fora_ponta_final_r_kwh": 0.6614614401363442,
        "tarifa_branca_intermediario_final_r_kwh": 0.8987537281636132,
        "tarifa_branca_ponta_final_r_kwh": 1.3391670217298681,
        "adicional_bandeira_r_kwh": 0.0,
        "fio_b_final_r_kwh": 0.12079771902897314,
    }
    consumo_periodos = {
        BREAKDOWN_DAILY: 0.22,
        BREAKDOWN_WEEKLY: 0.22,
        BREAKDOWN_MONTHLY: 0.22,
    }
    geracao_periodos = {
        BREAKDOWN_DAILY: 0.0,
        BREAKDOWN_WEEKLY: 0.0,
        BREAKDOWN_MONTHLY: 0.0,
    }
    injecao_periodos = {
        BREAKDOWN_DAILY: 0.0,
        BREAKDOWN_WEEKLY: 0.0,
        BREAKDOWN_MONTHLY: 0.0,
    }
    consumo_tarifa_branca = {
        period: {"fora_ponta": 0.22, "intermediario": 0.0, "ponta": 0.0}
        for period in (BREAKDOWN_DAILY, BREAKDOWN_WEEKLY, BREAKDOWN_MONTHLY)
    }

    coordinator._apply_dynamic_values_to_snapshot(
        values=values,
        enabled_breakdowns=[BREAKDOWN_DAILY, BREAKDOWN_WEEKLY, BREAKDOWN_MONTHLY],
        consumo_periodos=consumo_periodos,
        geracao_periodos=geracao_periodos,
        injecao_periodos=injecao_periodos,
        consumo_tarifa_branca=consumo_tarifa_branca,
        has_generation=True,
        has_injection=True,
        geracao_total_kwh=311.9,
        injecao_total_kwh=201.82,
        tipo_fornecimento="trifasico",
    )

    valor_regular_real = 0.22 * 0.7879100979974435
    valor_tarifa_branca_real = 0.22 * 0.6614614401363442
    valor_disponibilidade = 100 * 0.7879100979974435

    assert values["valor_conta_consumo_regular_daily_r"] == pytest.approx(
        valor_regular_real
    )
    assert values["valor_conta_com_geracao_daily_r"] == pytest.approx(
        valor_regular_real
    )
    assert values["valor_conta_tarifa_branca_daily_r"] == pytest.approx(
        valor_tarifa_branca_real
    )
    assert values["valor_conta_consumo_regular_monthly_r"] == pytest.approx(
        valor_disponibilidade
    )
    assert values["valor_conta_com_geracao_monthly_r"] == pytest.approx(
        valor_disponibilidade
    )
    assert values["valor_conta_tarifa_branca_monthly_r"] == pytest.approx(
        valor_disponibilidade
    )
    assert values[
        "valor_conta_consumo_regular_sem_disponibilidade_monthly_r"
    ] == pytest.approx(valor_regular_real)
    assert values[
        "valor_conta_com_geracao_sem_disponibilidade_monthly_r"
    ] == pytest.approx(valor_regular_real)
    assert values[
        "valor_conta_tarifa_branca_sem_disponibilidade_monthly_r"
    ] == pytest.approx(valor_tarifa_branca_real)
    assert "valor_conta_com_geracao_sem_disponibilidade_daily_r" not in values


def test_dynamic_icms_refresh_uses_monthly_consumption_base():
    coordinator = _build_coordinator()
    values = {
        "te_convencional_r_kwh": 0.34405,
        "tusd_convencional_r_kwh": 0.39564,
        "tarifa_convencional_bruta_r_kwh": 0.73969,
        "tarifa_convencional_final_r_kwh": 0.0,
        "te_branca_fora_ponta_r_kwh": 0.32816,
        "tusd_branca_fora_ponta_r_kwh": 0.29282,
        "te_branca_intermediario_r_kwh": 0.32816,
        "tusd_branca_intermediario_r_kwh": 0.51559,
        "te_branca_ponta_r_kwh": 0.51884,
        "tusd_branca_ponta_r_kwh": 0.73837,
        "fio_b_bruto_r_kwh": 0.189008164374,
        "fio_b_final_r_kwh": 0.0,
        "pis_percent": 1.10,
        "cofins_percent": 5.02,
        "icms_percent": 12.0,
    }

    source = coordinator._refresh_icms_dependent_values(
        values=values,
        concessionaria="CPFL-PIRATINING",
        consumo_mensal_kwh=250.0,
        fallback_icms_percent=12.0,
        has_consumo_history=True,
        reference_date=datetime(2026, 4, 24, tzinfo=UTC).date(),
    )

    assert source == "regra_faixa_consumo"
    assert values["icms_percent"] == pytest.approx(18.0)
    assert values["tarifa_convencional_final_r_kwh"] == pytest.approx(
        0.9748154981549815
    )
    assert values["fio_b_final_r_kwh"] == pytest.approx(0.21330709789353297)
    assert values["icms_consumo_percent"] == pytest.approx(18.0)
    assert values["icms_compensacao_percent"] == pytest.approx(0.0)
    assert "TUSD consumo final" in values["fio_b_calculo_expressao"]


def test_dynamic_icms_refresh_keeps_fio_b_in_current_icms_range():
    coordinator = _build_coordinator()
    values = {
        "te_convencional_r_kwh": 0.34405,
        "tusd_convencional_r_kwh": 0.39564,
        "tarifa_convencional_bruta_r_kwh": 0.73969,
        "tarifa_convencional_final_r_kwh": 0.0,
        "te_branca_fora_ponta_r_kwh": 0.32816,
        "tusd_branca_fora_ponta_r_kwh": 0.29282,
        "te_branca_intermediario_r_kwh": 0.32816,
        "tusd_branca_intermediario_r_kwh": 0.51559,
        "te_branca_ponta_r_kwh": 0.51884,
        "tusd_branca_ponta_r_kwh": 0.73837,
        "fio_b_bruto_r_kwh": 0.189008164374,
        "fio_b_final_r_kwh": 0.0,
        "pis_percent": 1.10,
        "cofins_percent": 5.02,
        "icms_percent": 12.0,
    }

    source = coordinator._refresh_icms_dependent_values(
        values=values,
        concessionaria="CPFL-PIRATINING",
        consumo_mensal_kwh=20.0,
        fallback_icms_percent=12.0,
        has_consumo_history=True,
        reference_date=datetime(2026, 4, 24, tzinfo=UTC).date(),
    )

    assert source == "regra_faixa_consumo"
    assert values["icms_percent"] == pytest.approx(0.0)
    assert values["icms_consumo_percent"] == pytest.approx(0.0)
    assert values["fio_b_final_r_kwh"] == pytest.approx(0.12079771902897314)
    assert "(1 - 0.00%)" in values["fio_b_calculo_expressao"]
