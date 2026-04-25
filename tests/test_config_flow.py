"""Versao: 0.1.0
Criado em: 2026-04-23 10:00:00 -03:00
Criado por: Codex
Projeto/pasta: ha.ext.tarifas
"""

from __future__ import annotations

import asyncio
import importlib.util
import sys
import types
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


def _install_fake_homeassistant_modules() -> None:
    """Instala stubs minimos do Home Assistant para testar config_flow."""

    if "homeassistant" in sys.modules:
        return

    homeassistant = types.ModuleType("homeassistant")
    config_entries = types.ModuleType("homeassistant.config_entries")
    helpers = types.ModuleType("homeassistant.helpers")
    selector = types.ModuleType("homeassistant.helpers.selector")
    const = types.ModuleType("homeassistant.const")

    class Platform(StrEnum):
        SENSOR = "sensor"

    const.Platform = Platform

    class SelectSelectorMode(StrEnum):
        DROPDOWN = "dropdown"
        LIST = "list"

    class NumberSelectorMode(StrEnum):
        BOX = "box"

    @dataclass
    class SelectSelectorConfig:
        options: list[str]
        mode: SelectSelectorMode | None = None
        multiple: bool = False

    @dataclass
    class EntitySelectorConfig:
        domain: list[str] | None = None
        device_class: list[str] | None = None

    @dataclass
    class NumberSelectorConfig:
        min: float | None = None
        max: float | None = None
        step: float | None = None
        mode: NumberSelectorMode | None = None

    class SelectSelector:
        def __init__(self, config: SelectSelectorConfig) -> None:
            self.config = config

        def __call__(self, value):  # noqa: ANN001
            return value

    class NumberSelector:
        def __init__(self, config: NumberSelectorConfig) -> None:
            self.config = config

        def __call__(self, value):  # noqa: ANN001
            return value

    class EntitySelector:
        def __init__(self, config: EntitySelectorConfig) -> None:
            self.config = config

        def __call__(self, value):  # noqa: ANN001
            return value

    selector.SelectSelectorMode = SelectSelectorMode
    selector.NumberSelectorMode = NumberSelectorMode
    selector.SelectSelectorConfig = SelectSelectorConfig
    selector.EntitySelectorConfig = EntitySelectorConfig
    selector.NumberSelectorConfig = NumberSelectorConfig
    selector.SelectSelector = SelectSelector
    selector.NumberSelector = NumberSelector
    selector.EntitySelector = EntitySelector

    class ConfigFlow:
        def __init_subclass__(cls, **kwargs) -> None:  # noqa: ANN001
            return None

        async def async_set_unique_id(self, unique_id: str) -> None:
            self._unique_id = unique_id

        def _abort_if_unique_id_configured(self) -> None:
            return None

        def async_create_entry(self, title: str, data: dict) -> dict:
            return {
                "type": "create_entry",
                "title": title,
                "data": data,
            }

        def async_show_form(self, step_id: str, data_schema, errors: dict) -> dict:  # noqa: ANN001
            return {
                "type": "form",
                "step_id": step_id,
                "data_schema": data_schema,
                "errors": errors,
            }

    class OptionsFlow:
        def async_create_entry(self, title: str, data: dict) -> dict:
            return {
                "type": "create_entry",
                "title": title,
                "data": data,
            }

        def async_show_form(self, step_id: str, data_schema, errors: dict) -> dict:  # noqa: ANN001
            return {
                "type": "form",
                "step_id": step_id,
                "data_schema": data_schema,
                "errors": errors,
            }

    @dataclass
    class ConfigEntry:
        data: dict
        options: dict

    def callback(func):  # noqa: ANN001
        return func

    config_entries.ConfigFlow = ConfigFlow
    config_entries.OptionsFlow = OptionsFlow
    config_entries.ConfigEntry = ConfigEntry
    config_entries.callback = callback

    helpers.selector = selector
    homeassistant.config_entries = config_entries
    homeassistant.helpers = helpers
    homeassistant.const = const

    sys.modules["homeassistant"] = homeassistant
    sys.modules["homeassistant.config_entries"] = config_entries
    sys.modules["homeassistant.helpers"] = helpers
    sys.modules["homeassistant.helpers.selector"] = selector
    sys.modules["homeassistant.const"] = const


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
_PKG_NAME = "tarifas_energia_brasil_testpkg"

if _PKG_NAME not in sys.modules:
    pkg = types.ModuleType(_PKG_NAME)
    pkg.__path__ = [str(_BASE_DIR)]  # type: ignore[attr-defined]
    sys.modules[_PKG_NAME] = pkg

const_module = _load_module(f"{_PKG_NAME}.const", _BASE_DIR / "const.py")
config_flow_module = _load_module(f"{_PKG_NAME}.config_flow", _BASE_DIR / "config_flow.py")

TarifasEnergiaBrasilConfigFlow = config_flow_module.TarifasEnergiaBrasilConfigFlow
TarifasEnergiaBrasilOptionsFlow = config_flow_module.TarifasEnergiaBrasilOptionsFlow
CONF_CONCESSIONARIA = const_module.CONF_CONCESSIONARIA
CONF_CONSUMPTION_ENTITY = const_module.CONF_CONSUMPTION_ENTITY
CONF_ENABLE_GENERATION_GROUP = const_module.CONF_ENABLE_GENERATION_GROUP
CONF_ENABLE_TARIFA_BRANCA_GROUP = const_module.CONF_ENABLE_TARIFA_BRANCA_GROUP
CONF_GENERATION_ENTITY = const_module.CONF_GENERATION_ENTITY
CONF_INJECTION_ENTITY = const_module.CONF_INJECTION_ENTITY
CONF_READING_DAY = const_module.CONF_READING_DAY
CONF_SUPPLY_TYPE = const_module.CONF_SUPPLY_TYPE
CONF_UPDATE_HOURS = const_module.CONF_UPDATE_HOURS


def test_config_flow_show_form_initial():
    flow = TarifasEnergiaBrasilConfigFlow()
    result = asyncio.run(flow.async_step_user())
    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] == {}


def test_config_flow_requires_supply_type_when_generation_set():
    flow = TarifasEnergiaBrasilConfigFlow()
    user_input = {
        CONF_CONCESSIONARIA: "CPFL-PIRATINING",
        CONF_CONSUMPTION_ENTITY: "sensor.consumo_total",
        CONF_GENERATION_ENTITY: "sensor.geracao_total",
    }
    result = asyncio.run(flow.async_step_user(user_input))
    assert result["type"] == "form"
    assert result["errors"].get("base") == "supply_type_required"


def test_config_flow_requires_supply_type_when_injection_set():
    flow = TarifasEnergiaBrasilConfigFlow()
    user_input = {
        CONF_CONCESSIONARIA: "CPFL-PIRATINING",
        CONF_CONSUMPTION_ENTITY: "sensor.consumo_total",
        CONF_INJECTION_ENTITY: "sensor.energia_injetada",
    }
    result = asyncio.run(flow.async_step_user(user_input))
    assert result["type"] == "form"
    assert result["errors"].get("base") == "supply_type_required"


def test_config_flow_create_entry_success():
    flow = TarifasEnergiaBrasilConfigFlow()
    user_input = {
        CONF_CONCESSIONARIA: "CPFL-PIRATINING",
        CONF_CONSUMPTION_ENTITY: "sensor.consumo_total",
        CONF_GENERATION_ENTITY: "sensor.geracao_total",
        CONF_SUPPLY_TYPE: "monofasico",
    }
    result = asyncio.run(flow.async_step_user(user_input))
    assert result["type"] == "create_entry"
    assert result["title"] == "Tarifas Energia Brasil - CPFL-PIRATINING"
    assert result["data"][CONF_SUPPLY_TYPE] == "monofasico"
    assert result["data"][CONF_ENABLE_GENERATION_GROUP] is True
    assert result["data"][CONF_ENABLE_TARIFA_BRANCA_GROUP] is False


def test_options_flow_requires_supply_type_when_generation_set():
    entry = sys.modules["homeassistant.config_entries"].ConfigEntry(data={}, options={})
    flow = TarifasEnergiaBrasilOptionsFlow(entry)
    user_input = {
        CONF_CONCESSIONARIA: "CPFL-PIRATINING",
        CONF_CONSUMPTION_ENTITY: "sensor.consumo_total",
        CONF_GENERATION_ENTITY: "sensor.geracao_total",
    }
    result = asyncio.run(flow.async_step_init(user_input))
    assert result["type"] == "form"
    assert result["errors"].get("base") == "supply_type_required"


def test_options_flow_create_entry_success():
    entry = sys.modules["homeassistant.config_entries"].ConfigEntry(data={}, options={})
    flow = TarifasEnergiaBrasilOptionsFlow(entry)
    user_input = {
        CONF_CONCESSIONARIA: "CPFL-PIRATINING",
        CONF_CONSUMPTION_ENTITY: "sensor.consumo_total",
        CONF_GENERATION_ENTITY: "sensor.geracao_total",
        CONF_SUPPLY_TYPE: "bifasico",
        CONF_ENABLE_GENERATION_GROUP: False,
        CONF_ENABLE_TARIFA_BRANCA_GROUP: True,
    }
    result = asyncio.run(flow.async_step_init(user_input))
    assert result["type"] == "create_entry"
    assert result["data"][CONF_SUPPLY_TYPE] == "bifasico"
    assert result["data"][CONF_ENABLE_GENERATION_GROUP] is False
    assert result["data"][CONF_ENABLE_TARIFA_BRANCA_GROUP] is True


def test_options_flow_forces_generation_group_off_without_generation_entity():
    entry = sys.modules["homeassistant.config_entries"].ConfigEntry(data={}, options={})
    flow = TarifasEnergiaBrasilOptionsFlow(entry)
    user_input = {
        CONF_CONCESSIONARIA: "CPFL-PIRATINING",
        CONF_CONSUMPTION_ENTITY: "sensor.consumo_total",
        CONF_ENABLE_GENERATION_GROUP: True,
        CONF_ENABLE_TARIFA_BRANCA_GROUP: False,
    }
    result = asyncio.run(flow.async_step_init(user_input))
    assert result["type"] == "create_entry"
    assert result["data"][CONF_ENABLE_GENERATION_GROUP] is False


def test_options_flow_enables_generation_group_with_injection_entity():
    entry = sys.modules["homeassistant.config_entries"].ConfigEntry(data={}, options={})
    flow = TarifasEnergiaBrasilOptionsFlow(entry)
    user_input = {
        CONF_CONCESSIONARIA: "CPFL-PIRATINING",
        CONF_CONSUMPTION_ENTITY: "sensor.consumo_total",
        CONF_INJECTION_ENTITY: "sensor.energia_injetada",
        CONF_SUPPLY_TYPE: "trifasico",
    }
    result = asyncio.run(flow.async_step_init(user_input))
    assert result["type"] == "create_entry"
    assert result["data"][CONF_ENABLE_GENERATION_GROUP] is True


def test_options_flow_injects_legacy_defaults():
    entry = sys.modules["homeassistant.config_entries"].ConfigEntry(
        data={
            CONF_CONCESSIONARIA: "CPFL-PIRATINING",
            CONF_CONSUMPTION_ENTITY: "sensor.consumo_total",
            CONF_GENERATION_ENTITY: "sensor.geracao_total",
            CONF_SUPPLY_TYPE: "monofasico",
        },
        options={},
    )
    flow = TarifasEnergiaBrasilOptionsFlow(entry)
    defaults = flow._current_defaults(None)
    assert defaults[CONF_ENABLE_GENERATION_GROUP] is True
    assert defaults[CONF_ENABLE_TARIFA_BRANCA_GROUP] is True


def test_config_flow_uses_number_box_for_reading_day_and_update_hours():
    schema = TarifasEnergiaBrasilConfigFlow._build_schema()
    fields = {
        marker.schema: field
        for marker, field in schema.schema.items()
    }
    selector_module = sys.modules["homeassistant.helpers.selector"]
    number_selector = selector_module.NumberSelector
    number_mode = selector_module.NumberSelectorMode

    assert isinstance(fields[CONF_READING_DAY], number_selector)
    assert fields[CONF_READING_DAY].config.mode == number_mode.BOX
    assert isinstance(fields[CONF_UPDATE_HOURS], number_selector)
    assert fields[CONF_UPDATE_HOURS].config.mode == number_mode.BOX
