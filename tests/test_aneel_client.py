"""Versao: 0.1.0
Criado em: 2026-04-23 16:20:00 -03:00
Criado por: Codex
Projeto/pasta: ha.ext.tarifas
"""

from __future__ import annotations

import asyncio
import importlib.util
import logging
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
_PKG_NAME = "tarifas_energia_brasil_testpkg_aneel"

if _PKG_NAME not in sys.modules:
    pkg = types.ModuleType(_PKG_NAME)
    pkg.__path__ = [str(_BASE_DIR)]  # type: ignore[attr-defined]
    sys.modules[_PKG_NAME] = pkg

_load_module(f"{_PKG_NAME}.const", _BASE_DIR / "const.py")
_load_module(f"{_PKG_NAME}.models", _BASE_DIR / "models.py")
_load_module(f"{_PKG_NAME}.calculators", _BASE_DIR / "calculators.py")
aneel_module = _load_module(f"{_PKG_NAME}.aneel_client", _BASE_DIR / "aneel_client.py")
_load_module(f"{_PKG_NAME}.tributos.parsers", _BASE_DIR / "tributos" / "parsers.py")
tributos_module = _load_module(f"{_PKG_NAME}.tributos", _BASE_DIR / "tributos" / "__init__.py")

AneelClient = aneel_module.AneelClient
ANEEL_CSV_TIMEOUT_SECONDS = aneel_module.ANEEL_CSV_TIMEOUT_SECONDS
ANEEL_JSON_TIMEOUT_SECONDS = aneel_module.ANEEL_JSON_TIMEOUT_SECONDS
DATASTORE_SEARCH_PAGE_LIMIT = aneel_module.DATASTORE_SEARCH_PAGE_LIMIT
RESOURCE_FIO_B_ANOS = aneel_module.AneelClient.RESOURCE_FIO_B_ANOS
TRIBUTOS_HTTP_TIMEOUT_SECONDS = tributos_module.TRIBUTOS_HTTP_TIMEOUT_SECONDS


class _FakeStreamContent:
    """Emite chunks de bytes como o StreamReader do aiohttp."""

    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = chunks

    async def iter_chunked(self, _size: int):
        for chunk in self._chunks:
            yield chunk


class _FakeResponse:
    """Resposta HTTP minima para testar timeouts e parsing."""

    def __init__(
        self,
        *,
        payload: dict | None = None,
        chunks: list[bytes] | None = None,
        headers: dict[str, str] | None = None,
        text: str = "",
    ) -> None:
        self._payload = payload or {}
        self.content = _FakeStreamContent(chunks or [])
        self.headers = headers or {}
        self._text = text

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):  # noqa: ANN001
        return False

    def raise_for_status(self) -> None:
        return None

    async def json(self, content_type=None):  # noqa: ANN001
        return self._payload

    async def text(self) -> str:
        return self._text


class _FakeSession:
    """Sessao HTTP fake que registra chamadas e devolve respostas em fila."""

    def __init__(self, responses: list[_FakeResponse]) -> None:
        self._responses = responses
        self.calls: list[dict] = []

    def get(self, url, **kwargs):  # noqa: ANN001
        self.calls.append({"url": url, **kwargs})
        return self._responses.pop(0)


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


def test_aneel_json_requests_use_extended_timeout():
    session = _FakeSession(
        [
            _FakeResponse(
                payload={
                    "success": True,
                    "result": {"records": []},
                }
            )
        ]
    )
    client = AneelClient(session=session)

    payload = asyncio.run(client._request_json("datastore_search", {"resource_id": "x"}))

    assert payload["success"] is True
    assert session.calls[0]["timeout"] == ANEEL_JSON_TIMEOUT_SECONDS
    assert ANEEL_JSON_TIMEOUT_SECONDS == 120


def test_datastore_search_uses_smaller_pages_without_total_count():
    session = _FakeSession(
        [
            _FakeResponse(
                payload={
                    "success": True,
                    "result": {"records": [{"SigAgente": "CPFL-PIRATINING"}]},
                }
            )
        ]
    )
    client = AneelClient(session=session)

    records = asyncio.run(
        client._datastore_search_records(
            resource_id="resource-id",
            filters={"SigAgente": "CPFL-PIRATINING"},
        )
    )

    params = session.calls[0]["params"]
    assert records == [{"SigAgente": "CPFL-PIRATINING"}]
    assert params["limit"] == DATASTORE_SEARCH_PAGE_LIMIT
    assert DATASTORE_SEARCH_PAGE_LIMIT == 1000
    assert params["include_total"] == "false"


def test_csv_fallback_uses_extended_timeout_and_filters_streamed_chunks():
    csv_chunks = [
        b"SigAgente,Nome,Valor\nCPFL-PIR",
        b'ATINING,"com, virgula",1\nOUTRA,x,2\nCPFL-PIRATINING,y,3',
    ]
    session = _FakeSession(
        [
            _FakeResponse(
                payload={
                    "success": True,
                    "result": {"url": "https://example.test/aneel.csv"},
                }
            ),
            _FakeResponse(chunks=csv_chunks),
        ]
    )
    client = AneelClient(session=session)

    records = asyncio.run(
        client._csv_xml_records(
            resource_id="resource-id",
            filters={"SigAgente": "CPFL-PIRATINING"},
        )
    )

    assert session.calls[0]["timeout"] == ANEEL_JSON_TIMEOUT_SECONDS
    assert session.calls[1]["timeout"] == ANEEL_CSV_TIMEOUT_SECONDS
    assert ANEEL_CSV_TIMEOUT_SECONDS == 600
    assert records == [
        {"SigAgente": "CPFL-PIRATINING", "Nome": "com, virgula", "Valor": "1"},
        {"SigAgente": "CPFL-PIRATINING", "Nome": "y", "Valor": "3"},
    ]


def test_csv_fallback_filters_semicolon_latin1_chunks():
    csv_text = (
        '"SigNomeAgente";"DscBaseTarifaria";"VlrComponenteTarifario"\n'
        '"CPFL-PIRATINING";"Tarifa de Aplicação";"189,008164374"\n'
        '"OUTRA";"Tarifa de Aplicação";"0"\n'
    )
    payload = csv_text.encode("latin-1")
    csv_chunks = [payload[:57], payload[57:92], payload[92:]]
    session = _FakeSession(
        [
            _FakeResponse(
                payload={
                    "success": True,
                    "result": {"url": "https://example.test/aneel.csv"},
                }
            ),
            _FakeResponse(chunks=csv_chunks),
        ]
    )
    client = AneelClient(session=session)

    records = asyncio.run(
        client._csv_xml_records(
            resource_id="resource-id",
            filters={"SigNomeAgente": "CPFL-PIRATINING"},
        )
    )

    assert records == [
        {
            "SigNomeAgente": "CPFL-PIRATINING",
            "DscBaseTarifaria": "Tarifa de Aplicação",
            "VlrComponenteTarifario": "189,008164374",
        }
    ]


def test_aneel_failure_log_includes_filters_and_exception_class(caplog):
    client = AneelClient(session=None)
    filters = {
        "SigNomeAgente": "CPFL-PIRATINING",
        "DscComponenteTarifario": "TUSD_FioB",
    }

    caplog.set_level(logging.WARNING, logger=aneel_module.__name__)
    client._log_aneel_method_failure(
        dataset="componentes-tarifarias/Fio B",
        method="csv_xml",
        next_method=None,
        filters=filters,
        err=TimeoutError(),
    )

    message = caplog.text
    assert "metodo=csv_xml" in message
    assert '"SigNomeAgente": "CPFL-PIRATINING"' in message
    assert '"DscComponenteTarifario": "TUSD_FioB"' in message
    assert "TimeoutError" in message


def test_fetch_fio_b_csv_stops_after_first_valid_resource():
    first_resource_csv = (
        '"SigNomeAgente";"DscComponenteTarifario";"DatInicioVigencia";'
        '"DatFimVigencia";"DscBaseTarifaria";"DscSubGrupoTarifario";'
        '"DscModalidadeTarifaria";"DscClasseConsumidor";'
        '"DscSubClasseConsumidor";"DscDetalheConsumidor";'
        '"DscPostoTarifario";"VlrComponenteTarifario"\n'
        '"OUTRA";"TUSD_FioB";"2026-01-01";"2026-10-22";'
        '"Tarifa de Aplicacao";"B1";"Convencional";"Residencial";'
        '"Residencial";"Nao se aplica";"Nao se aplica";"1"\n'
    )
    second_resource_csv = (
        '"SigNomeAgente";"DscComponenteTarifario";"DatInicioVigencia";'
        '"DatFimVigencia";"DscBaseTarifaria";"DscSubGrupoTarifario";'
        '"DscModalidadeTarifaria";"DscClasseConsumidor";'
        '"DscSubClasseConsumidor";"DscDetalheConsumidor";'
        '"DscPostoTarifario";"VlrComponenteTarifario"\n'
        '"CPFL-PIRATINING";"TUSD_FioB";"2026-01-01";"2026-10-22";'
        '"Tarifa de Aplicacao";"B1";"Convencional";"Residencial";'
        '"Residencial";"Nao se aplica";"Nao se aplica";"189,008164374"\n'
    )
    session = _FakeSession(
        [
            _FakeResponse(
                payload={
                    "success": True,
                    "result": {"url": "https://example.test/fio-b-2026.csv"},
                }
            ),
            _FakeResponse(chunks=[first_resource_csv.encode("latin-1")]),
            _FakeResponse(
                payload={
                    "success": True,
                    "result": {"url": "https://example.test/fio-b-2025.csv"},
                }
            ),
            _FakeResponse(chunks=[second_resource_csv.encode("latin-1")]),
        ]
    )
    client = AneelClient(session=session)

    parsed, metadata = asyncio.run(
        client.fetch_fio_b(
            concessionaria="CPFL-PIRATINING",
            priority_method="csv_xml",
            reference_date=date(2026, 4, 27),
        )
    )

    assert parsed["convencional_bruto_r_kwh"] == pytest.approx(0.189008164374)
    assert metadata.resource_id == ",".join(RESOURCE_FIO_B_ANOS[:2])
    assert len(session.calls) == 4
    assert "fio-b-2024" not in "\n".join(call["url"] for call in session.calls)


def test_tributos_requests_use_extended_timeout():
    fallback = tributos_module.TributosFallback(
        pis=1.10,
        cofins=5.02,
        icms=12.00,
        fonte="https://example.test/tributos",
        confianca="alta",
    )
    session = _FakeSession([_FakeResponse(text="<html><body>sem tabela</body></html>")])

    result = asyncio.run(
        tributos_module._fetch_and_parse_tributos(
            session=session,
            concessionaria="CPFL-PIRATINING",
            fallback=fallback,
        )
    )

    assert result == pytest.approx((1.10, 5.02, 12.00))
    assert session.calls[0]["timeout"] == TRIBUTOS_HTTP_TIMEOUT_SECONDS
    assert TRIBUTOS_HTTP_TIMEOUT_SECONDS == 60


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


def test_parse_fio_b_records_accepts_cpfl_piratining_current_rows():
    client = AneelClient(session=None)
    records = [
        _fio_b_row(
            DscBaseTarifaria="Tarifa de Aplicação",
            DscSubGrupoTarifario="B1",
            DscModalidadeTarifaria="Convencional",
            DscClasseConsumidor="Residencial",
            DscSubClasseConsumidor="Residencial",
            DscDetalheConsumidor="Não se aplica",
            DscPostoTarifario="Não se aplica",
            VlrComponenteTarifario="189,00816437399999",
        ),
        _fio_b_row(
            DscBaseTarifaria="Tarifa de Aplicação",
            DscSubGrupoTarifario="B1",
            DscModalidadeTarifaria="Branca",
            DscClasseConsumidor="Residencial",
            DscSubClasseConsumidor="Residencial",
            DscDetalheConsumidor="Não se aplica",
            DscPostoTarifario="Ponta",
            VlrComponenteTarifario="491,42124922699998",
        ),
    ]

    parsed = client._parse_fio_b_records(
        records=records,
        concessionaria="CPFL-PIRATINING",
        reference_date=date(2026, 4, 27),
    )

    assert parsed["convencional_bruto_r_kwh"] == pytest.approx(0.189008164374)
    assert parsed["branca_bruto_r_kwh_por_posto"]["ponta"] == pytest.approx(0.491421249227)
    assert parsed["vigencia_inicio"] == "2026-01-01"
    assert parsed["vigencia_fim"] == "2026-10-22"
