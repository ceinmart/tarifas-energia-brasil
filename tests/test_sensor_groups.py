"""Versao: 0.1.0
Criado em: 2026-04-23 16:10:00 -03:00
Criado por: Codex
Projeto/pasta: ha.ext.tarifas
"""

from __future__ import annotations

import importlib.util
import sys
import types
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Generic, TypeVar


def _install_fake_homeassistant_modules() -> None:
    """Instala stubs minimos para importar sensor.py sem Home Assistant real."""

    homeassistant = sys.modules.get("homeassistant", types.ModuleType("homeassistant"))
    components = sys.modules.get(
        "homeassistant.components",
        types.ModuleType("homeassistant.components"),
    )
    sensor_module = sys.modules.get(
        "homeassistant.components.sensor",
        types.ModuleType("homeassistant.components.sensor"),
    )
    config_entries = sys.modules.get(
        "homeassistant.config_entries",
        types.ModuleType("homeassistant.config_entries"),
    )
    const = sys.modules.get("homeassistant.const", types.ModuleType("homeassistant.const"))
    core = sys.modules.get("homeassistant.core", types.ModuleType("homeassistant.core"))
    helpers = sys.modules.get(
        "homeassistant.helpers",
        types.ModuleType("homeassistant.helpers"),
    )
    device_registry = sys.modules.get(
        "homeassistant.helpers.device_registry",
        types.ModuleType("homeassistant.helpers.device_registry"),
    )
    entity = sys.modules.get(
        "homeassistant.helpers.entity",
        types.ModuleType("homeassistant.helpers.entity"),
    )
    entity_platform = sys.modules.get(
        "homeassistant.helpers.entity_platform",
        types.ModuleType("homeassistant.helpers.entity_platform"),
    )
    update_coordinator = sys.modules.get(
        "homeassistant.helpers.update_coordinator",
        types.ModuleType("homeassistant.helpers.update_coordinator"),
    )
    util = sys.modules.get("homeassistant.util", types.ModuleType("homeassistant.util"))

    class SensorDeviceClass(StrEnum):
        MONETARY = "monetary"

    class SensorStateClass(StrEnum):
        MEASUREMENT = "measurement"

    @dataclass(frozen=True, kw_only=True)
    class SensorEntityDescription:
        key: str
        name: str | None = None
        native_unit_of_measurement: str | None = None
        device_class: str | None = None
        state_class: str | None = None
        entity_category: str | None = None

    class SensorEntity:
        pass

    @dataclass
    class ConfigEntry:
        data: dict
        options: dict
        entry_id: str = "entry-1"

    @dataclass
    class DeviceInfo:
        identifiers: set[tuple[str, str]]
        name: str
        manufacturer: str
        model: str
        entry_type: str

    class DeviceEntryType(StrEnum):
        SERVICE = "service"

    class EntityCategory(StrEnum):
        DIAGNOSTIC = "diagnostic"

    T = TypeVar("T")

    class CoordinatorEntity(Generic[T]):
        def __init__(self, coordinator: T) -> None:
            self.coordinator = coordinator

        @property
        def available(self) -> bool:
            return True

    def slugify(value: str) -> str:
        return value.lower().replace(" ", "_").replace("-", "_")

    sensor_module.SensorDeviceClass = SensorDeviceClass
    sensor_module.SensorEntity = SensorEntity
    sensor_module.SensorEntityDescription = SensorEntityDescription
    sensor_module.SensorStateClass = SensorStateClass

    config_entries.ConfigEntry = ConfigEntry
    const.PERCENTAGE = "%"
    core.HomeAssistant = object
    device_registry.DeviceEntryType = DeviceEntryType
    device_registry.DeviceInfo = DeviceInfo
    entity.EntityCategory = EntityCategory
    entity_platform.AddEntitiesCallback = object
    update_coordinator.CoordinatorEntity = CoordinatorEntity
    util.slugify = slugify

    helpers.device_registry = device_registry
    helpers.entity = entity
    helpers.entity_platform = entity_platform
    helpers.update_coordinator = update_coordinator

    homeassistant.components = components
    homeassistant.config_entries = config_entries
    homeassistant.const = const
    homeassistant.core = core
    homeassistant.helpers = helpers
    homeassistant.util = util

    sys.modules["homeassistant"] = homeassistant
    sys.modules["homeassistant.components"] = components
    sys.modules["homeassistant.components.sensor"] = sensor_module
    sys.modules["homeassistant.config_entries"] = config_entries
    sys.modules["homeassistant.const"] = const
    sys.modules["homeassistant.core"] = core
    sys.modules["homeassistant.helpers"] = helpers
    sys.modules["homeassistant.helpers.device_registry"] = device_registry
    sys.modules["homeassistant.helpers.entity"] = entity
    sys.modules["homeassistant.helpers.entity_platform"] = entity_platform
    sys.modules["homeassistant.helpers.update_coordinator"] = update_coordinator
    sys.modules["homeassistant.util"] = util


_install_fake_homeassistant_modules()


def _load_module(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_BASE_DIR = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "tarifas_energia_brasil"
)
_PKG_NAME = "tarifas_energia_brasil_testpkg_sensor"

if _PKG_NAME not in sys.modules:
    pkg = types.ModuleType(_PKG_NAME)
    pkg.__path__ = [str(_BASE_DIR)]  # type: ignore[attr-defined]
    sys.modules[_PKG_NAME] = pkg

coordinator_stub = types.ModuleType(f"{_PKG_NAME}.coordinator")


class TarifasEnergiaBrasilCoordinator:
    """Stub minimo para tipagem do sensor."""


coordinator_stub.TarifasEnergiaBrasilCoordinator = TarifasEnergiaBrasilCoordinator
sys.modules[f"{_PKG_NAME}.coordinator"] = coordinator_stub

const_module = _load_module(f"{_PKG_NAME}.const", _BASE_DIR / "const.py")
sensor_impl = _load_module(f"{_PKG_NAME}.sensor", _BASE_DIR / "sensor.py")

ConfigEntry = sys.modules["homeassistant.config_entries"].ConfigEntry
EntityCategory = sys.modules["homeassistant.helpers.entity"].EntityCategory

CONF_CONCESSIONARIA = const_module.CONF_CONCESSIONARIA
CONF_CONSUMPTION_ENTITY = const_module.CONF_CONSUMPTION_ENTITY
CONF_ENABLE_GENERATION_GROUP = const_module.CONF_ENABLE_GENERATION_GROUP
CONF_ENABLE_TARIFA_BRANCA_GROUP = const_module.CONF_ENABLE_TARIFA_BRANCA_GROUP
CONF_GENERATION_ENTITY = const_module.CONF_GENERATION_ENTITY
TarifasEnergiaBrasilSensor = sensor_impl.TarifasEnergiaBrasilSensor
build_sensor_descriptions = sensor_impl.build_sensor_descriptions


def _description_keys(entry: ConfigEntry) -> set[str]:
    return {description.value_key for description in build_sensor_descriptions(entry)}


def test_regular_group_is_always_present():
    entry = ConfigEntry(
        data={
            CONF_CONCESSIONARIA: "CPFL-PIRATINING",
            CONF_CONSUMPTION_ENTITY: "sensor.consumo_total",
            CONF_ENABLE_TARIFA_BRANCA_GROUP: False,
        },
        options={},
    )

    keys = _description_keys(entry)

    assert "tarifa_convencional_final_r_kwh" in keys
    assert "valor_conta_consumo_regular_daily_r" in keys
    assert "valor_conta_tarifa_branca_daily_r" not in keys
    assert "valor_conta_com_geracao_daily_r" not in keys


def test_generation_group_depends_on_entity_and_toggle():
    entry = ConfigEntry(
        data={
            CONF_CONCESSIONARIA: "CPFL-PIRATINING",
            CONF_CONSUMPTION_ENTITY: "sensor.consumo_total",
            CONF_GENERATION_ENTITY: "sensor.geracao_total",
            CONF_ENABLE_GENERATION_GROUP: True,
            CONF_ENABLE_TARIFA_BRANCA_GROUP: False,
        },
        options={},
    )

    keys = _description_keys(entry)

    assert "fio_b_final_r_kwh" in keys
    assert "valor_conta_com_geracao_monthly_r" in keys
    assert "valor_fio_b_compensada_monthly_r" in keys


def test_tarifa_branca_group_respects_toggle():
    entry = ConfigEntry(
        data={
            CONF_CONCESSIONARIA: "CPFL-PIRATINING",
            CONF_CONSUMPTION_ENTITY: "sensor.consumo_total",
            CONF_ENABLE_TARIFA_BRANCA_GROUP: True,
        },
        options={},
    )

    keys = _description_keys(entry)

    assert "tarifa_branca_ponta_final_r_kwh" in keys
    assert "valor_conta_tarifa_branca_monthly_r" in keys


def test_legacy_entry_keeps_tarifa_branca_visible_until_user_opts_out():
    entry = ConfigEntry(
        data={
            CONF_CONCESSIONARIA: "CPFL-PIRATINING",
            CONF_CONSUMPTION_ENTITY: "sensor.consumo_total",
        },
        options={},
    )

    keys = _description_keys(entry)

    assert "tarifa_branca_fora_ponta_final_r_kwh" in keys
    assert "valor_conta_tarifa_branca_daily_r" in keys


def test_entities_share_single_device_and_keep_unique_ids():
    entry = ConfigEntry(
        data={
            CONF_CONCESSIONARIA: "CPFL-PIRATINING",
            CONF_CONSUMPTION_ENTITY: "sensor.consumo_total",
            CONF_ENABLE_TARIFA_BRANCA_GROUP: True,
        },
        options={},
    )
    descriptions = build_sensor_descriptions(entry)
    by_key = {description.value_key: description for description in descriptions}

    class DummyCoordinator:
        data = None

    regular_entity = TarifasEnergiaBrasilSensor(
        coordinator=DummyCoordinator(),
        entry=entry,
        description=by_key["tarifa_convencional_final_r_kwh"],
    )
    branca_entity = TarifasEnergiaBrasilSensor(
        coordinator=DummyCoordinator(),
        entry=entry,
        description=by_key["tarifa_branca_ponta_final_r_kwh"],
    )

    assert regular_entity._attr_device_info.identifiers == branca_entity._attr_device_info.identifiers
    assert regular_entity._attr_unique_id != branca_entity._attr_unique_id


def test_technical_regular_sensors_are_marked_as_diagnostic():
    entry = ConfigEntry(
        data={
            CONF_CONCESSIONARIA: "CPFL-PIRATINING",
            CONF_CONSUMPTION_ENTITY: "sensor.consumo_total",
            CONF_ENABLE_TARIFA_BRANCA_GROUP: False,
        },
        options={},
    )

    descriptions = {item.value_key: item for item in build_sensor_descriptions(entry)}

    assert descriptions["te_convencional_r_kwh"].entity_category == EntityCategory.DIAGNOSTIC
    assert descriptions["tarifa_convencional_final_r_kwh"].entity_category is None
