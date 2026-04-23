"""Versao: 0.1.0
Criado em: 2026-04-23 16:20:00 -03:00
Criado por: Codex
Projeto/pasta: ha.ext.tarifas
"""

from __future__ import annotations

import importlib.util
import sys
import types
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from pathlib import Path

import pytest


def _install_homeassistant_stub() -> None:
    """Instala stub minimo do Home Assistant para carregar const.py."""

    if "homeassistant" in sys.modules:
        return

    homeassistant = types.ModuleType("homeassistant")
    config_entries = types.ModuleType("homeassistant.config_entries")
    helpers = types.ModuleType("homeassistant.helpers")
    selector = types.ModuleType("homeassistant.helpers.selector")
    const = types.ModuleType("homeassistant.const")

    class Platform(StrEnum):
        SENSOR = "sensor"

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

    const.Platform = Platform
    selector.SelectSelectorMode = SelectSelectorMode
    selector.NumberSelectorMode = NumberSelectorMode
    selector.SelectSelectorConfig = SelectSelectorConfig
    selector.EntitySelectorConfig = EntitySelectorConfig
    selector.NumberSelectorConfig = NumberSelectorConfig
    selector.SelectSelector = SelectSelector
    selector.NumberSelector = NumberSelector
    selector.EntitySelector = EntitySelector
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


def _install_aiohttp_stub() -> None:
    """Instala stub minimo do aiohttp quando indisponivel no ambiente."""

    if "aiohttp" in sys.modules:
        return

    aiohttp = types.ModuleType("aiohttp")

    class ClientSession:  # noqa: D401 - stub minimo
        """Stub minimo para type hints do cliente."""

    aiohttp.ClientSession = ClientSession
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
_PKG_NAME = "tarifas_energia_brasil_testpkg_aneel"

if _PKG_NAME not in sys.modules:
    pkg = types.ModuleType(_PKG_NAME)
    pkg.__path__ = [str(_BASE_DIR)]  # type: ignore[attr-defined]
    sys.modules[_PKG_NAME] = pkg

_load_module(f"{_PKG_NAME}.const", _BASE_DIR / "const.py")
_load_module(f"{_PKG_NAME}.models", _BASE_DIR / "models.py")
_load_module(f"{_PKG_NAME}.calculators", _BASE_DIR / "calculators.py")
aneel_module = _load_module(f"{_PKG_NAME}.aneel_client", _BASE_DIR / "aneel_client.py")

AneelClient = aneel_module.AneelClient


def _tarifa_row(**overrides: str) -> dict[str, str]:
    row = {
        "SigAgente": "CPFL-PIRATINING",
        "DatInicioVigencia": "2026-01-01",
        "DatFimVigencia": "2026-10-22",
        "DscBaseTarifaria": "Tarifa de Aplicacao",
        "DscSubGrupo": "B1",
        "DscModalidadeTarifaria": "Convencional",
        "DscClasse": "Residencial",
        "DscSubClasse": "Residencial",
        "DscDetalhe": "Nao se aplica",
        "NomPostoTarifario": "Nao se aplica",
        "VlrTE": "344,05",
        "VlrTUSD": "395,64",
    }
    row.update(overrides)
    return row


def _fio_b_row(**overrides: str) -> dict[str, str]:
    row = {
        "SigNomeAgente": "CPFL-PIRATINING",
        "DatInicioVigencia": "2026-01-01",
        "DatFimVigencia": "2026-10-22",
        "DscBaseTarifaria": "Tarifa de Aplicacao",
        "DscSubGrupoTarifario": "B1",
        "DscModalidadeTarifaria": "Convencional",
        "DscClasseConsumidor": "Residencial",
        "DscSubClasseConsumidor": "Residencial",
        "DscDetalheConsumidor": "Nao se aplica",
        "DscPostoTarifario": "Nao se aplica",
        "DscComponenteTarifario": "TUSD_FioB",
        "VlrComponenteTarifario": "189,008164374",
    }
    row.update(overrides)
    return row


def test_parse_tarifa_records_prefers_regular_residential_row():
    client = AneelClient(session=None)
    records = [
        _tarifa_row(
            DscSubClasse="Residencial Tarifa Social - faixa 01",
            DscDetalhe="SCEE",
            VlrTE="27,52",
            VlrTUSD="253,56",
        ),
        _tarifa_row(),
        _tarifa_row(
            DscModalidadeTarifaria="Branca",
            NomPostoTarifario="Fora ponta",
            DscSubClasse="Residencial Tarifa Social - faixa 01",
            DscDetalhe="SCEE",
            VlrTE="50,92",
            VlrTUSD="292,82",
        ),
        _tarifa_row(
            DscModalidadeTarifaria="Branca",
            NomPostoTarifario="Fora ponta",
            DscSubClasse="Residencial",
            DscDetalhe="Nao se aplica",
            VlrTE="328,16",
            VlrTUSD="292,82",
        ),
    ]

    parsed = client._parse_tarifa_records(
        records=records,
        concessionaria="CPFL-PIRATINING",
        reference_date=date(2026, 4, 23),
    )

    assert parsed["convencional"]["te_r_kwh"] == pytest.approx(0.34405)
    assert parsed["convencional"]["tusd_r_kwh"] == pytest.approx(0.39564)
    assert parsed["branca"]["fora_ponta"]["te_r_kwh"] == pytest.approx(0.32816)
    assert parsed["branca"]["fora_ponta"]["tusd_r_kwh"] == pytest.approx(0.29282)
    assert parsed["selection_debug"]["convencional"]["subclasse"] == "Residencial"
    assert parsed["selection_debug"]["convencional"]["detalhe"] == "Nao se aplica"


def test_parse_fio_b_records_prefers_tarifa_aplicacao_residencial():
    client = AneelClient(session=None)
    records = [
        _fio_b_row(
            DscBaseTarifaria="Base Economica",
            DscSubClasseConsumidor="Baixa Renda",
            DscDetalheConsumidor="SCEE",
            VlrComponenteTarifario="189,68326413",
        ),
        _fio_b_row(),
        _fio_b_row(
            DscModalidadeTarifaria="Branca",
            DscPostoTarifario="Fora ponta",
            VlrComponenteTarifario="98,284271700",
        ),
    ]

    parsed = client._parse_fio_b_records(
        records=records,
        concessionaria="CPFL-PIRATINING",
        reference_date=date(2026, 4, 23),
    )

    assert parsed["convencional_bruto_r_kwh"] == pytest.approx(0.189008164374)
    assert parsed["branca_bruto_r_kwh_por_posto"]["fora_ponta"] == pytest.approx(0.0982842717)
    assert parsed["selection_debug"]["convencional"]["base_tarifaria"] == "Tarifa de Aplicacao"
    assert parsed["selection_debug"]["convencional"]["subclasse"] == "Residencial"
