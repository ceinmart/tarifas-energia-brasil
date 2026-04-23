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
CONF_CONCESSIONARIA = const_module.CONF_CONCESSIONARIA
resolve_tarifa_branca_schedule = tarifa_branca_module.resolve_tarifa_branca_schedule


def _build_coordinator() -> object:
    coordinator = TarifasEnergiaBrasilCoordinator.__new__(TarifasEnergiaBrasilCoordinator)
    coordinator._tarifa_branca_last_interval_seconds = 0.0
    coordinator._tarifa_branca_last_segment_count = 0
    coordinator._tarifa_branca_low_confidence = False
    return coordinator


def test_prepare_delta_context_uses_current_total_when_sensor_resets():
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
    assert context["delta_kwh"] == pytest.approx(291.83)


def test_scalar_period_state_keeps_current_cycle_value_after_reset():
    coordinator = _build_coordinator()
    now = datetime(2026, 4, 23, 15, 0, tzinfo=UTC)
    period_state = TarifasEnergiaBrasilCoordinator._new_period_state()
    delta_context = {
        "has_previous": True,
        "delta_kwh": 291.83,
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

    assert values[BREAKDOWN_MONTHLY] == pytest.approx(291.83)


def test_tarifa_branca_state_assigns_reset_value_to_current_posto():
    coordinator = _build_coordinator()
    now = datetime(2026, 4, 23, 15, 0, tzinfo=UTC)
    period_state = TarifasEnergiaBrasilCoordinator._new_posto_period_state()
    schedule, _metadata = resolve_tarifa_branca_schedule(
        {CONF_CONCESSIONARIA: "CPFL-PIRATINING"}
    )
    delta_context = {
        "has_previous": True,
        "delta_kwh": 291.83,
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

    assert values[BREAKDOWN_MONTHLY]["fora_ponta"] == pytest.approx(291.83)
    assert values[BREAKDOWN_MONTHLY]["intermediario"] == pytest.approx(0.0)
    assert values[BREAKDOWN_MONTHLY]["ponta"] == pytest.approx(0.0)
    assert coordinator._tarifa_branca_low_confidence is True
