"""Versao: 0.2.3
Criado em: 2026-04-23 17:20:00 -03:00
Alterado em: 2026-08-12 (America/Sao_Paulo)
Alterado em: 2026-08-31 22:01 -03:00
Criado por: Codex
Projeto/pasta: ha.ext.tarifas
"""

from __future__ import annotations

import importlib.util
import sys
import types
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
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

_BASE_DIR = Path(__file__).resolve().parents[1] / "custom_components" / "tarifas_energia_brasil"
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
QUEBRA_MENSAL = const_module.QUEBRA_MENSAL
QUEBRA_DIARIA = const_module.QUEBRA_DIARIA
QUEBRA_SEMANAL = const_module.QUEBRA_SEMANAL
CONF_CONCESSIONARIA = const_module.CONF_CONCESSIONARIA
CONF_HORAS_ATUALIZACAO = const_module.CONF_HORAS_ATUALIZACAO
CONF_MULTIPLICADOR_FALLBACK_CSV = const_module.CONF_MULTIPLICADOR_FALLBACK_CSV
resolve_tarifa_branca_schedule = tarifa_branca_module.resolve_tarifa_branca_schedule
MetadadosColeta = coordinator_module.MetadadosColeta
ResultadoCalculo = coordinator_module.ResultadoCalculo


def _build_coordinator() -> object:
    coordinator = TarifasEnergiaBrasilCoordinator.__new__(TarifasEnergiaBrasilCoordinator)
    coordinator._tarifa_branca_last_interval_seconds = 0.0
    coordinator._tarifa_branca_last_segment_count = 0
    coordinator._tarifa_branca_low_confidence = False
    coordinator._incremental_stale_events = 0
    coordinator._incremental_long_intervals = 0
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


def test_prepare_delta_context_rejects_non_increasing_timestamp():
    coordinator = _build_coordinator()
    last = datetime(2026, 8, 12, 9, 19, tzinfo=UTC)

    context = coordinator._prepare_delta_context(101.0, last, 100.0, last)

    assert context["stale_timestamp"] is True
    assert context["delta_kwh"] == pytest.approx(0.0)


def test_long_incremental_interval_is_bounded_without_segmentation(monkeypatch):
    coordinator = _build_coordinator()
    start = datetime(2020, 1, 1, tzinfo=UTC)
    end = datetime(2026, 8, 12, tzinfo=UTC)
    context = coordinator._prepare_delta_context(101.0, end, 100.0, start)
    period_state = TarifasEnergiaBrasilCoordinator._new_period_state()

    monkeypatch.setattr(
        coordinator_module,
        "split_interval_by_midnight",
        lambda *_args: pytest.fail("intervalo longo nao deve ser segmentado"),
    )
    valores, _rollovers = coordinator._apply_scalar_delta_context(
        period_state, end, reading_day=1, delta_context=context
    )

    assert context["long_interval"] is True
    assert context["delta_kwh"] == pytest.approx(0.0)
    assert valores[QUEBRA_MENSAL] == pytest.approx(0.0)


def test_tracked_events_for_three_sensors_are_coalesced_by_numeric_snapshot(monkeypatch):
    coordinator = _build_coordinator()
    coordinator.data = types.SimpleNamespace(
        atualizado_em=None,
        concessionaria="CPFL-PIRATINING",
        valores={},
        diagnosticos={},
    )
    coordinator._last_consumo_total_kwh = 100.0
    coordinator._last_geracao_total_kwh = 50.0
    coordinator._last_injecao_total_kwh = 20.0
    coordinator._last_consumo_timestamp = None
    coordinator._last_geracao_timestamp = None
    coordinator._last_injecao_timestamp = None
    values = iter((101.0, 51.0, 21.0, 101.0, 51.0, 21.0))
    process_calls = []

    monkeypatch.setattr(
        coordinator,
        "_effective_value",
        lambda key, *_args: 1 if key == const_module.CONF_DIA_LEITURA else "sensor.test",
    )
    monkeypatch.setattr(coordinator, "_read_entity_kwh", lambda *_args: next(values))
    monkeypatch.setattr(coordinator, "_process_energy_states", lambda **kwargs: process_calls.append(kwargs))
    monkeypatch.setattr(coordinator, "_refresh_icms_dependent_valores", lambda **_kwargs: "test")
    monkeypatch.setattr(coordinator, "_apply_dynamic_valores_to_snapshot", lambda **_kwargs: None)
    monkeypatch.setattr(coordinator, "_update_dynamic_diagnosticos", lambda *_args: None)
    monkeypatch.setattr(coordinator, "_schedule_state_save", lambda: None)
    monkeypatch.setattr(coordinator, "async_update_listeners", lambda: None)
    monkeypatch.setattr(coordinator, "_effective_breakdowns", lambda: [])
    monkeypatch.setattr(coordinator, "_current_period_valores", lambda *_args: {})
    monkeypatch.setattr(coordinator, "_current_posto_period_valores", lambda *_args: {})
    monkeypatch.setattr(coordinator, "_cached_rollover_context", lambda: {})
    coordinator._consumo_period_state = {QUEBRA_MENSAL: {"kwh": 0.0}}
    coordinator._geracao_period_state = {}
    coordinator._injecao_period_state = {}
    coordinator._consumo_tarifa_branca_state = {}

    event = types.SimpleNamespace(time_fired=datetime(2026, 8, 12, 12, 0, tzinfo=UTC))
    coordinator._handle_tracked_state_change(event)
    coordinator._last_consumo_total_kwh = 101.0
    coordinator._last_geracao_total_kwh = 51.0
    coordinator._last_injecao_total_kwh = 21.0
    coordinator._handle_tracked_state_change(event)

    assert len(process_calls) == 1


def test_initial_failure_uses_short_retry_interval_without_cached_snapshot():
    coordinator = _build_coordinator()
    coordinator._configured_update_interval = timedelta(hours=24)
    coordinator.update_interval = timedelta(hours=24)
    coordinator.data = None

    retry_interval = coordinator._failure_retry_interval(has_snapshot=False)

    assert retry_interval == timedelta(minutes=15)
    assert coordinator.update_interval == timedelta(minutes=15)


def test_failure_keeps_regular_interval_when_cached_snapshot_exists():
    coordinator = _build_coordinator()
    coordinator._configured_update_interval = timedelta(hours=24)
    coordinator.update_interval = timedelta(hours=24)
    coordinator.data = ResultadoCalculo(
        atualizado_em=datetime(2026, 4, 27, 10, 0, tzinfo=UTC),
        concessionaria="CPFL-PIRATINING",
        valores={"tarifa_convencional_final_r_kwh": 0.9748},
        coletas_por_chave={},
        diagnosticos={},
    )

    retry_interval = coordinator._failure_retry_interval(has_snapshot=True)

    assert retry_interval == timedelta(hours=24)
    assert coordinator.update_interval == timedelta(hours=24)


def test_success_restores_regular_interval_after_initial_retry():
    coordinator = _build_coordinator()
    coordinator._configured_update_interval = timedelta(hours=24)
    coordinator.update_interval = timedelta(minutes=15)

    coordinator._restore_regular_update_interval()

    assert coordinator.update_interval == timedelta(hours=24)


def test_csv_fallback_multiplier_turns_regular_interval_into_block_window():
    coordinator = _build_coordinator()
    coordinator.entry = types.SimpleNamespace(
        data={
            CONF_HORAS_ATUALIZACAO: 24,
            CONF_MULTIPLICADOR_FALLBACK_CSV: 3,
        },
        options={},
    )

    assert coordinator._csv_fallback_interval() == timedelta(hours=72)


def test_csv_fallback_is_allowed_without_cached_snapshot():
    coordinator = _build_coordinator()
    now = datetime(2026, 4, 27, 10, 0, tzinfo=UTC)
    coordinator.entry = types.SimpleNamespace(
        data={
            CONF_HORAS_ATUALIZACAO: 24,
            CONF_MULTIPLICADOR_FALLBACK_CSV: 3,
        },
        options={},
    )
    coordinator.data = None
    coordinator._last_csv_fallback_attempts = {"fio_b": now.isoformat()}

    assert coordinator._csv_fallback_allowed("fio_b", now) is True


def test_csv_fallback_is_blocked_inside_multiplier_window_with_snapshot():
    coordinator = _build_coordinator()
    now = datetime(2026, 4, 27, 10, 0, tzinfo=UTC)
    coordinator.entry = types.SimpleNamespace(
        data={
            CONF_HORAS_ATUALIZACAO: 24,
            CONF_MULTIPLICADOR_FALLBACK_CSV: 3,
        },
        options={},
    )
    coordinator.data = ResultadoCalculo(
        atualizado_em=now,
        concessionaria="CPFL-PIRATINING",
        valores={"tarifa_convencional_final_r_kwh": 0.9748},
        coletas_por_chave={},
        diagnosticos={},
    )
    coordinator._last_csv_fallback_attempts = {
        "fio_b": (now - timedelta(hours=71, minutes=59)).isoformat()
    }

    assert coordinator._csv_fallback_allowed("fio_b", now) is False
    diagnostics = coordinator._csv_fallback_diagnostics(now)
    assert diagnostics["fio_b"]["permitido"] is False
    assert diagnostics["fio_b"]["intervalo_horas"] == pytest.approx(72)


def test_csv_fallback_attempts_are_persisted_in_state_snapshot():
    coordinator = _build_coordinator()
    coordinator.data = None
    coordinator._last_consumo_total_kwh = None
    coordinator._last_geracao_total_kwh = None
    coordinator._last_injecao_total_kwh = None
    coordinator._last_consumo_timestamp = None
    coordinator._last_geracao_timestamp = None
    coordinator._last_injecao_timestamp = None
    coordinator._consumo_period_state = TarifasEnergiaBrasilCoordinator._new_period_state()
    coordinator._geracao_period_state = TarifasEnergiaBrasilCoordinator._new_period_state()
    coordinator._injecao_period_state = TarifasEnergiaBrasilCoordinator._new_period_state()
    coordinator._consumo_tarifa_branca_state = (
        TarifasEnergiaBrasilCoordinator._new_posto_period_state()
    )
    coordinator._ultimo_ciclo_mensal = None
    coordinator._credito_estimado_atual_kwh = 0.0
    coordinator._credito_consumido_estimado_atual_kwh = 0.0
    coordinator._creditos_ledger = []
    coordinator._last_csv_fallback_attempts = {"tarifas": "2026-04-27T10:00:00+00:00"}

    payload = coordinator._serialize_state()

    assert payload["last_csv_fallback_attempts"] == {
        "tarifas": "2026-04-27T10:00:00+00:00"
    }


def test_cached_snapshot_roundtrip_restores_sensor_valores_after_restart():
    coordinator = _build_coordinator()
    atualizado_em = datetime(2026, 4, 27, 10, 0, tzinfo=UTC)
    coordinator.data = ResultadoCalculo(
        atualizado_em=atualizado_em,
        concessionaria="CPFL-PIRATINING",
        valores={
            "tarifa_convencional_final_r_kwh": 0.9748,
            "bandeira_vigente": "Verde",
        },
        coletas_por_chave={
            "tarifa_convencional_final_r_kwh": MetadadosColeta(
                fonte="dados_abertos_aneel",
                metodo_acesso="datastore_search",
                tentativas=1,
            )
        },
        diagnosticos={
            "mensagem_erro": None,
            "consumo_mensal_kwh_apurado": 120.0,
        },
    )

    cached = coordinator._serialize_cached_snapshot()
    restored = coordinator._restore_cached_snapshot(cached)

    assert restored is not None
    assert restored.atualizado_em == atualizado_em
    assert restored.concessionaria == "CPFL-PIRATINING"
    assert restored.valores["tarifa_convencional_final_r_kwh"] == pytest.approx(0.9748)
    assert (
        restored.coletas_por_chave["tarifa_convencional_final_r_kwh"].metodo_acesso
        == "datastore_search"
    )
    assert restored.diagnosticos["consumo_mensal_kwh_apurado"] == pytest.approx(120.0)
    assert restored.diagnosticos["snapshot_restaurado_de_cache"] is True


def test_scalar_period_state_does_not_copy_reset_total_to_every_breakdown():
    coordinator = _build_coordinator()
    now = datetime(2026, 4, 23, 15, 0, tzinfo=UTC)
    period_state = TarifasEnergiaBrasilCoordinator._new_period_state()
    period_state[QUEBRA_DIARIA]["key"] = "2026-04-23"
    period_state[QUEBRA_DIARIA]["kwh"] = 12.0
    period_state[QUEBRA_SEMANAL]["key"] = "2026-W17"
    period_state[QUEBRA_SEMANAL]["kwh"] = 80.0
    period_state[QUEBRA_MENSAL]["key"] = "2026-04-D01"
    period_state[QUEBRA_MENSAL]["kwh"] = 291.83
    delta_context = {
        "has_previous": True,
        "delta_kwh": 0.0,
        "raw_delta_kwh": -988.67,
        "reset_detected": True,
        "start": now,
        "end": now,
    }

    valores, _rollovers = coordinator._apply_scalar_delta_context(
        period_state,
        now,
        reading_day=1,
        delta_context=delta_context,
    )

    assert valores[QUEBRA_DIARIA] == pytest.approx(12.0)
    assert valores[QUEBRA_SEMANAL] == pytest.approx(80.0)
    assert valores[QUEBRA_MENSAL] == pytest.approx(291.83)


def test_scalar_period_state_resets_when_update_ends_at_midnight():
    coordinator = _build_coordinator()
    start = datetime(2026, 4, 23, 23, 0, tzinfo=UTC)
    end = datetime(2026, 4, 24, 0, 0, tzinfo=UTC)
    period_state = TarifasEnergiaBrasilCoordinator._new_period_state()
    period_state[QUEBRA_DIARIA]["key"] = "2026-04-23"
    period_state[QUEBRA_DIARIA]["kwh"] = 12.0
    period_state[QUEBRA_SEMANAL]["key"] = "2026-W17"
    period_state[QUEBRA_SEMANAL]["kwh"] = 80.0
    period_state[QUEBRA_MENSAL]["key"] = "2026-03-D24"
    period_state[QUEBRA_MENSAL]["kwh"] = 605.29
    delta_context = {
        "has_previous": True,
        "delta_kwh": 2.0,
        "raw_delta_kwh": 2.0,
        "reset_detected": False,
        "start": start,
        "end": end,
    }

    valores, rollovers = coordinator._apply_scalar_delta_context(
        period_state,
        end,
        reading_day=24,
        delta_context=delta_context,
    )

    assert valores[QUEBRA_DIARIA] == pytest.approx(0.0)
    assert valores[QUEBRA_SEMANAL] == pytest.approx(82.0)
    assert valores[QUEBRA_MENSAL] == pytest.approx(0.0)
    assert period_state[QUEBRA_DIARIA]["key"] == "2026-04-24"
    assert period_state[QUEBRA_MENSAL]["key"] == "2026-04-D24"
    assert dict(rollovers[QUEBRA_DIARIA])["2026-04-23"] == pytest.approx(14.0)
    assert dict(rollovers[QUEBRA_MENSAL])["2026-03-D24"] == pytest.approx(607.29)


def test_scalar_period_state_resets_week_when_update_ends_on_monday_midnight():
    coordinator = _build_coordinator()
    start = datetime(2026, 4, 26, 23, 0, tzinfo=UTC)
    end = datetime(2026, 4, 27, 0, 0, tzinfo=UTC)
    period_state = TarifasEnergiaBrasilCoordinator._new_period_state()
    period_state[QUEBRA_DIARIA]["key"] = "2026-04-26"
    period_state[QUEBRA_DIARIA]["kwh"] = 8.0
    period_state[QUEBRA_SEMANAL]["key"] = "2026-W17"
    period_state[QUEBRA_SEMANAL]["kwh"] = 95.0
    period_state[QUEBRA_MENSAL]["key"] = "2026-04-D24"
    period_state[QUEBRA_MENSAL]["kwh"] = 20.0
    delta_context = {
        "has_previous": True,
        "delta_kwh": 3.0,
        "raw_delta_kwh": 3.0,
        "reset_detected": False,
        "start": start,
        "end": end,
    }

    valores, rollovers = coordinator._apply_scalar_delta_context(
        period_state,
        end,
        reading_day=24,
        delta_context=delta_context,
    )

    assert valores[QUEBRA_DIARIA] == pytest.approx(0.0)
    assert valores[QUEBRA_SEMANAL] == pytest.approx(0.0)
    assert valores[QUEBRA_MENSAL] == pytest.approx(23.0)
    assert period_state[QUEBRA_SEMANAL]["key"] == "2026-W18"
    assert dict(rollovers[QUEBRA_SEMANAL])["2026-W17"] == pytest.approx(98.0)


def test_tarifa_branca_state_does_not_copy_reset_total_to_current_posto():
    coordinator = _build_coordinator()
    now = datetime(2026, 4, 23, 15, 0, tzinfo=UTC)
    period_state = TarifasEnergiaBrasilCoordinator._new_posto_period_state()
    period_state[QUEBRA_MENSAL]["key"] = "2026-04-D01"
    period_state[QUEBRA_MENSAL]["postos"]["fora_ponta"] = 120.0
    schedule, _metadata = resolve_tarifa_branca_schedule({CONF_CONCESSIONARIA: "CPFL-PIRATINING"})
    delta_context = {
        "has_previous": True,
        "delta_kwh": 0.0,
        "raw_delta_kwh": -988.67,
        "reset_detected": True,
        "start": now,
        "end": now,
    }

    valores, _rollovers = coordinator._apply_tarifa_branca_delta_context(
        period_state,
        now,
        reading_day=1,
        delta_context=delta_context,
        schedule=schedule,
        holidays=set(),
    )

    assert valores[QUEBRA_MENSAL]["fora_ponta"] == pytest.approx(120.0)
    assert valores[QUEBRA_MENSAL]["intermediario"] == pytest.approx(0.0)
    assert valores[QUEBRA_MENSAL]["ponta"] == pytest.approx(0.0)
    assert coordinator._tarifa_branca_low_confidence is False


def test_process_energy_states_ignores_unavailable_startup_reading():
    coordinator = _build_coordinator()
    start = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    now = datetime(2026, 4, 25, 12, 1, tzinfo=UTC)
    next_now = datetime(2026, 4, 25, 12, 2, tzinfo=UTC)
    coordinator.entry = types.SimpleNamespace(
        data={CONF_CONCESSIONARIA: "CPFL-PIRATINING"},
        options={},
    )
    coordinator._creditos_ledger = []
    coordinator._last_consumo_total_kwh = 1200.0
    coordinator._last_consumo_timestamp = start
    coordinator._last_geracao_total_kwh = None
    coordinator._last_geracao_timestamp = None
    coordinator._last_injecao_total_kwh = None
    coordinator._last_injecao_timestamp = None
    coordinator._consumo_reset_detectado = 0
    coordinator._geracao_reset_detectado = 0
    coordinator._injecao_reset_detectado = 0
    coordinator._ultimo_ciclo_mensal = "2026-04-D24"
    coordinator._credito_estimado_atual_kwh = 0.0
    coordinator._credito_consumido_estimado_atual_kwh = 0.0
    coordinator._consumo_period_state = TarifasEnergiaBrasilCoordinator._new_period_state()
    coordinator._geracao_period_state = TarifasEnergiaBrasilCoordinator._new_period_state()
    coordinator._injecao_period_state = TarifasEnergiaBrasilCoordinator._new_period_state()
    coordinator._consumo_tarifa_branca_state = (
        TarifasEnergiaBrasilCoordinator._new_posto_period_state()
    )
    coordinator._consumo_period_state[QUEBRA_DIARIA]["key"] = "2026-04-25"
    coordinator._consumo_period_state[QUEBRA_DIARIA]["kwh"] = 2.0
    coordinator._consumo_period_state[QUEBRA_SEMANAL]["key"] = "2026-W17"
    coordinator._consumo_period_state[QUEBRA_SEMANAL]["kwh"] = 8.0
    coordinator._consumo_period_state[QUEBRA_MENSAL]["key"] = "2026-04-D24"
    coordinator._consumo_period_state[QUEBRA_MENSAL]["kwh"] = 10.0

    valores, _geracao, _injecao, _tarifa_branca = coordinator._process_energy_states(
        now=now,
        consumo_total_kwh=None,
        geracao_total_kwh=None,
        injecao_total_kwh=None,
        reading_day=24,
        tariff_context={},
    )

    assert valores[QUEBRA_MENSAL] == pytest.approx(10.0)
    assert coordinator._last_consumo_total_kwh == pytest.approx(1200.0)
    assert coordinator._last_consumo_timestamp == start
    assert coordinator._consumo_reset_detectado == 0

    valores, _geracao, _injecao, _tarifa_branca = coordinator._process_energy_states(
        now=next_now,
        consumo_total_kwh=1201.5,
        geracao_total_kwh=None,
        injecao_total_kwh=None,
        reading_day=24,
        tariff_context={},
    )

    assert valores[QUEBRA_MENSAL] == pytest.approx(11.5)
    assert coordinator._last_consumo_total_kwh == pytest.approx(1201.5)
    assert coordinator._consumo_reset_detectado == 0


def test_dynamic_valores_calculate_auto_consumo_from_generated_minus_injected():
    coordinator = _build_coordinator()
    coordinator._creditos_ledger = [coordinator_module.CreditoEntry("2026-03", 80.0)]

    valores = {
        "tarifa_convencional_final_r_kwh": 0.9,
        "adicional_bandeira_r_kwh": 0.0,
        "fio_b_final_r_kwh": 0.1,
    }
    consumo_periodos = {
        QUEBRA_DIARIA: 0.0,
        QUEBRA_SEMANAL: 0.0,
        QUEBRA_MENSAL: 100.0,
    }
    geracao_periodos = {
        QUEBRA_DIARIA: 0.0,
        QUEBRA_SEMANAL: 0.0,
        QUEBRA_MENSAL: 40.0,
    }
    injecao_periodos = {
        QUEBRA_DIARIA: 0.0,
        QUEBRA_SEMANAL: 0.0,
        QUEBRA_MENSAL: 0.0,
    }
    consumo_tarifa_branca = {
        period: {"fora_ponta": 0.0, "intermediario": 0.0, "ponta": 0.0}
        for period in (QUEBRA_DIARIA, QUEBRA_SEMANAL, QUEBRA_MENSAL)
    }

    coordinator._apply_dynamic_valores_to_snapshot(
        valores=valores,
        quebras_habilitadas=[QUEBRA_MENSAL],
        consumo_periodos=consumo_periodos,
        geracao_periodos=geracao_periodos,
        injecao_periodos=injecao_periodos,
        consumo_tarifa_branca=consumo_tarifa_branca,
        possui_geracao=True,
        possui_injecao=False,
        geracao_total_kwh=40.0,
        injecao_total_kwh=None,
        tipo_fornecimento="monofasico",
    )

    assert valores["auto_consumo_kwh"] == pytest.approx(20.0)
    assert valores["auto_consumo_reais"] == pytest.approx(18.0)
    assert valores["auto_consumo_mensal_kwh"] == pytest.approx(20.0)
    assert valores["auto_consumo_mensal_reais"] == pytest.approx(18.0)
    assert "auto_consumo_diario_kwh" not in valores


def test_dynamic_valores_calculate_auto_consumo_from_entidade_injecao_totals():
    coordinator = _build_coordinator()
    coordinator._creditos_ledger = []

    valores = {
        "tarifa_convencional_final_r_kwh": 0.9748154981549815,
        "adicional_bandeira_r_kwh": 0.0,
        "fio_b_final_r_kwh": 0.14945295021665786,
    }
    consumo_periodos = {
        QUEBRA_DIARIA: 302.43,
        QUEBRA_SEMANAL: 302.43,
        QUEBRA_MENSAL: 302.43,
    }
    geracao_periodos = {
        QUEBRA_DIARIA: 40.0,
        QUEBRA_SEMANAL: 80.0,
        QUEBRA_MENSAL: 311.9,
    }
    injecao_periodos = {
        QUEBRA_DIARIA: 10.0,
        QUEBRA_SEMANAL: 30.0,
        QUEBRA_MENSAL: 201.82,
    }
    consumo_tarifa_branca = {
        period: {"fora_ponta": 0.0, "intermediario": 0.0, "ponta": 0.0}
        for period in (QUEBRA_DIARIA, QUEBRA_SEMANAL, QUEBRA_MENSAL)
    }

    coordinator._apply_dynamic_valores_to_snapshot(
        valores=valores,
        quebras_habilitadas=[QUEBRA_DIARIA, QUEBRA_SEMANAL, QUEBRA_MENSAL],
        consumo_periodos=consumo_periodos,
        geracao_periodos=geracao_periodos,
        injecao_periodos=injecao_periodos,
        consumo_tarifa_branca=consumo_tarifa_branca,
        possui_geracao=True,
        possui_injecao=True,
        geracao_total_kwh=311.9,
        injecao_total_kwh=201.82,
        tipo_fornecimento="trifasico",
    )

    assert valores["auto_consumo_kwh"] == pytest.approx(110.08)
    assert valores["auto_consumo_diario_kwh"] == pytest.approx(30.0)
    assert valores["auto_consumo_semanal_kwh"] == pytest.approx(50.0)
    assert valores["auto_consumo_mensal_kwh"] == pytest.approx(110.08)
    assert valores["auto_consumo_mensal_reais"] == pytest.approx(110.08 * 0.9748154981549815)


def test_dynamic_valores_apply_disponibilidade_only_to_mensal_bill_valores():
    coordinator = _build_coordinator()
    coordinator._creditos_ledger = []

    valores = {
        "tarifa_convencional_final_r_kwh": 0.7879100979974435,
        "tarifa_branca_fora_ponta_final_r_kwh": 0.6614614401363442,
        "tarifa_branca_intermediario_final_r_kwh": 0.8987537281636132,
        "tarifa_branca_ponta_final_r_kwh": 1.3391670217298681,
        "adicional_bandeira_r_kwh": 0.0,
        "fio_b_final_r_kwh": 0.12079771902897314,
    }
    consumo_periodos = {
        QUEBRA_DIARIA: 0.22,
        QUEBRA_SEMANAL: 0.22,
        QUEBRA_MENSAL: 0.22,
    }
    geracao_periodos = {
        QUEBRA_DIARIA: 0.0,
        QUEBRA_SEMANAL: 0.0,
        QUEBRA_MENSAL: 0.0,
    }
    injecao_periodos = {
        QUEBRA_DIARIA: 0.0,
        QUEBRA_SEMANAL: 0.0,
        QUEBRA_MENSAL: 0.0,
    }
    consumo_tarifa_branca = {
        period: {"fora_ponta": 0.22, "intermediario": 0.0, "ponta": 0.0}
        for period in (QUEBRA_DIARIA, QUEBRA_SEMANAL, QUEBRA_MENSAL)
    }

    coordinator._apply_dynamic_valores_to_snapshot(
        valores=valores,
        quebras_habilitadas=[QUEBRA_DIARIA, QUEBRA_SEMANAL, QUEBRA_MENSAL],
        consumo_periodos=consumo_periodos,
        geracao_periodos=geracao_periodos,
        injecao_periodos=injecao_periodos,
        consumo_tarifa_branca=consumo_tarifa_branca,
        possui_geracao=True,
        possui_injecao=True,
        geracao_total_kwh=311.9,
        injecao_total_kwh=201.82,
        tipo_fornecimento="trifasico",
    )

    valor_regular_real = 0.22 * 0.7879100979974435
    valor_tarifa_branca_real = 0.22 * 0.6614614401363442
    valor_disponibilidade = 100 * 0.7879100979974435

    assert valores["valor_conta_consumo_regular_diario_r"] == pytest.approx(valor_regular_real)
    assert valores["valor_conta_com_geracao_diario_r"] == pytest.approx(valor_regular_real)
    assert valores["valor_conta_tarifa_branca_diario_r"] == pytest.approx(valor_tarifa_branca_real)
    assert valores["valor_conta_consumo_regular_mensal_r"] == pytest.approx(valor_disponibilidade)
    assert valores["valor_conta_com_geracao_mensal_r"] == pytest.approx(valor_disponibilidade)
    assert valores["valor_conta_tarifa_branca_mensal_r"] == pytest.approx(valor_disponibilidade)
    assert valores["valor_conta_consumo_regular_sem_disponibilidade_mensal_r"] == pytest.approx(
        valor_regular_real
    )
    assert valores["valor_conta_com_geracao_sem_disponibilidade_mensal_r"] == pytest.approx(
        valor_regular_real
    )
    assert valores["valor_conta_tarifa_branca_sem_disponibilidade_mensal_r"] == pytest.approx(
        valor_tarifa_branca_real
    )
    assert "valor_conta_com_geracao_sem_disponibilidade_diario_r" not in valores


def test_dynamic_icms_refresh_uses_mensal_consumption_base():
    coordinator = _build_coordinator()
    valores = {
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

    source = coordinator._refresh_icms_dependent_valores(
        valores=valores,
        concessionaria="CPFL-PIRATINING",
        consumo_mensal_kwh=250.0,
        tipo_fornecimento="trifasico",
        fallback_icms_percent=12.0,
        possui_historico_consumo=True,
        reference_date=datetime(2026, 4, 24, tzinfo=UTC).date(),
    )

    assert source == "regra_faixa_consumo"
    assert valores["icms_percent"] == pytest.approx(18.0)
    assert valores["tarifa_convencional_final_r_kwh"] == pytest.approx(0.9748154981549815)
    assert valores["fio_b_final_r_kwh"] == pytest.approx(0.21330709789353297)
    assert valores["icms_consumo_percent"] == pytest.approx(18.0)
    assert valores["icms_compensacao_percent"] == pytest.approx(0.0)
    assert "TUSD consumo final" in valores["fio_b_calculo_expressao"]
    assert "250.000 kWh" in valores["icms_calculo_expressao"]
    assert "ICMS aplicado = 18.00%" in valores["icms_calculo_expressao"]


def test_dynamic_icms_refresh_keeps_fio_b_in_current_icms_range():
    coordinator = _build_coordinator()
    valores = {
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

    source = coordinator._refresh_icms_dependent_valores(
        valores=valores,
        concessionaria="CPFL-PIRATINING",
        consumo_mensal_kwh=20.0,
        tipo_fornecimento="monofasico",
        fallback_icms_percent=12.0,
        possui_historico_consumo=True,
        reference_date=datetime(2026, 4, 24, tzinfo=UTC).date(),
    )

    assert source == "regra_faixa_consumo"
    assert valores["icms_percent"] == pytest.approx(0.0)
    assert valores["icms_consumo_percent"] == pytest.approx(0.0)
    assert valores["fio_b_final_r_kwh"] == pytest.approx(0.12079771902897314)
    assert "(1 - 0.00%)" in valores["fio_b_calculo_expressao"]
    assert "20.000 kWh" in valores["icms_calculo_expressao"]
    assert "ICMS aplicado = 0.00%" in valores["icms_calculo_expressao"]


def test_dynamic_icms_refresh_uses_triphase_minimum_for_range():
    coordinator = _build_coordinator()
    valores = {
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
        "icms_percent": 0.0,
    }

    source = coordinator._refresh_icms_dependent_valores(
        valores=valores,
        concessionaria="CPFL-PIRATINING",
        consumo_mensal_kwh=20.0,
        tipo_fornecimento="trifasico",
        fallback_icms_percent=12.0,
        possui_historico_consumo=True,
        reference_date=datetime(2026, 4, 24, tzinfo=UTC).date(),
    )

    assert source == "regra_faixa_consumo"
    assert valores["icms_percent"] == pytest.approx(12.0)
    assert valores["icms_consumo_mensal_kwh"] == pytest.approx(20.0)
    assert valores["icms_consumo_faturavel_kwh"] == pytest.approx(100.0)
    assert valores["icms_disponibilidade_minima_kwh"] == pytest.approx(100.0)
    assert "base faturavel para ICMS 100.000 kWh" in valores["icms_calculo_expressao"]
    assert "ICMS aplicado = 12.00%" in valores["icms_calculo_expressao"]


def _freshness_coordinator(age_days=4):
    from unittest.mock import AsyncMock
    coordinator = _build_coordinator()
    coordinator.entry = types.SimpleNamespace(
        entry_id='entry-a', data={'concessionaria': 'CPFL-PIRATINING'}, options={})
    now = datetime.now().astimezone()
    coordinator.data = ResultadoCalculo(
        atualizado_em=now, concessionaria='CPFL-PIRATINING', valores={'fio_b': 1},
        coletas_por_chave={'fio_b': MetadadosColeta(ultima_coleta=(now-timedelta(days=age_days)).isoformat())},
        diagnosticos={'ultima_tentativa': now.isoformat()})
    coordinator.hass = types.SimpleNamespace(services=types.SimpleNamespace(async_call=AsyncMock()))
    return coordinator, now


def test_freshness_uses_collection_not_recent_sensor_event():
    coordinator, now = _freshness_coordinator()
    attrs = coordinator.freshness_attributes(now)
    assert attrs['idade_dados_dias'] == 4
    assert attrs['dados_desatualizados'] is True
    assert attrs['ultima_coleta_bem_sucedida'] != coordinator.data.atualizado_em.isoformat()
    coordinator.entry.options['alerta_dados_desatualizados_dias'] = 5
    assert coordinator.freshness_attributes(now)['dados_desatualizados'] is False
    coordinator.entry.options['alerta_dados_desatualizados_dias'] = 4
    assert coordinator.freshness_attributes(now)['dados_desatualizados'] is True


@pytest.mark.parametrize('date_value', [None, 'invalid', '2099-01-01T00:00:00+00:00'])
def test_unknown_collection_date_is_not_fabricated(date_value):
    coordinator, now = _freshness_coordinator()
    coordinator.data.coletas_por_chave['fio_b'].ultima_coleta = date_value
    attrs = coordinator.freshness_attributes(now)
    assert attrs['ultima_coleta_bem_sucedida'] is None
    assert attrs['dados_desatualizados'] is True


def test_notification_deduplicates_and_recovers_without_csv():
    import asyncio
    coordinator, now = _freshness_coordinator()
    async def scenario():
        await coordinator._async_check_freshness(now)
        await coordinator._async_check_freshness(now)
        calls = coordinator.hass.services.async_call.call_args_list
        assert len(calls) == 1
        assert calls[0].args[:2] == ('persistent_notification', 'create')
        data = calls[0].args[2]
        assert 'atualizar_via_csv' in data['message']
        assert 'Nenhum CSV sera baixado automaticamente' in data['message']
        coordinator.data.coletas_por_chave['fio_b'].ultima_coleta = now.isoformat()
        await coordinator._async_check_freshness(now)
        assert coordinator.hass.services.async_call.call_args.args[:2] == ('persistent_notification', 'dismiss')
        assert coordinator.hass.services.async_call.call_args.args[2]['notification_id'] == data['notification_id']
    asyncio.run(scenario())


def test_fresh_data_failure_still_notifies_and_entries_are_distinct():
    import asyncio
    coordinator, _ = _freshness_coordinator(0)
    asyncio.run(coordinator._async_notify_collection('network failed'))
    first = coordinator.hass.services.async_call.call_args.args[2]
    assert 'dentro do prazo' in first['message']
    coordinator.entry.entry_id = 'entry-b'
    coordinator._collection_notification_message = None
    asyncio.run(coordinator._async_notify_collection('network failed'))
    assert first['notification_id'] != coordinator.hass.services.async_call.call_args.args[2]['notification_id']


def test_automatic_failure_preserves_snapshot_and_collection_dates(monkeypatch):
    import asyncio
    from unittest.mock import AsyncMock, Mock
    coordinator, _ = _freshness_coordinator()
    old_values = coordinator.data.valores.copy()
    old_date = coordinator.data.coletas_por_chave['fio_b'].ultima_coleta
    old_updated = coordinator.data.atualizado_em
    coordinator.config_entry = coordinator.entry
    coordinator.async_ensure_state_loaded = AsyncMock()
    coordinator._schedule_state_save = Mock()
    coordinator._last_consumo_timestamp = None
    coordinator._manual_csv_datasets = frozenset()
    coordinator._failure_retry_interval = Mock(return_value=timedelta(hours=24))
    coordinator._aneel_client = types.SimpleNamespace(
        fetch_tarifas=AsyncMock(side_effect=RuntimeError('network failed')),
        fetch_fio_b=AsyncMock(return_value=None), fetch_bandeira=AsyncMock(return_value=None))
    monkeypatch.setattr(coordinator_module, 'async_get_clientsession', lambda hass: None)
    monkeypatch.setattr(coordinator_module, 'extract_tributos', AsyncMock(return_value=None))
    result = asyncio.run(coordinator._async_update_data())
    assert result.valores == old_values
    assert result.atualizado_em == old_updated
    assert result.coletas_por_chave['fio_b'].ultima_coleta == old_date
    assert result.diagnosticos['usou_ultimo_valor_valido'] is True
    assert result.diagnosticos['ultima_tentativa']
    assert coordinator.hass.services.async_call.call_args.args[:2] == ('persistent_notification', 'create')
    for name in ('fetch_tarifas', 'fetch_fio_b', 'fetch_bandeira'):
        assert getattr(coordinator._aneel_client, name).call_args.kwargs['manual_csv'] is False


def test_collection_age_survives_snapshot_restore():
    coordinator, now = _freshness_coordinator()
    restored = coordinator._restore_cached_snapshot(coordinator._serialize_cached_snapshot())
    coordinator.data = restored
    assert coordinator.freshness_attributes(now)['idade_dados_dias'] == 4


def test_periodic_freshness_check_is_unsubscribed(monkeypatch):
    import asyncio
    from unittest.mock import Mock
    coordinator, now = _freshness_coordinator()
    coordinator._unsub_state_listeners = []
    unsub = Mock()
    callbacks = []
    def subscribe(hass, callback, interval):
        callbacks.append((callback, interval))
        return unsub
    monkeypatch.setattr(sys.modules['homeassistant.helpers.event'],
        'async_track_time_interval', subscribe, raising=False)
    async def scenario():
        await coordinator.async_start_state_tracking()
        assert callbacks[0][1] == timedelta(hours=1)
        await coordinator.async_start_state_tracking()
        assert len(callbacks) == 1
        await coordinator.async_stop_state_tracking()
    asyncio.run(scenario())
    unsub.assert_called_once()


def test_notification_failure_does_not_raise_or_trigger_download():
    import asyncio
    coordinator, now = _freshness_coordinator()
    coordinator.hass.services.async_call.side_effect = RuntimeError('notification unavailable')
    asyncio.run(coordinator._async_notify_collection('collection error'))
    assert coordinator.data.valores == {'fio_b': 1}
