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
resolve_tarifa_branca_schedule = tarifa_branca_module.resolve_tarifa_branca_schedule
MetadadosColeta = coordinator_module.MetadadosColeta
ResultadoCalculo = coordinator_module.ResultadoCalculo


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
