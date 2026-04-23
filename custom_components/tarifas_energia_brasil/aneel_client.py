"""Versao: 0.1.0
Criado em: 2026-04-22 21:41:36 -03:00
Criado por: Codex
Projeto/pasta: ha.ext.tarifas
"""

from __future__ import annotations

import csv
import io
import json
import logging
import unicodedata
from datetime import date, datetime
from typing import Any

import aiohttp

from .calculators import mwh_to_kwh
from .const import (
    ANEEL_METHOD_CSV_XML,
    ANEEL_METHOD_DATASTORE_SEARCH,
    ANEEL_METHOD_DATASTORE_SEARCH_SQL,
    ATTR_CONFIANCA_ALTA,
    ATTR_CONFIANCA_MEDIA,
    get_aneel_method_fallback_order,
)
from .models import CollectionMetadata

_LOGGER = logging.getLogger(__name__)


class AneelClientError(Exception):
    """Erro de coleta de dados ANEEL."""


class AneelClient:
    """Cliente de consulta ANEEL via CKAN com fallback entre metodos."""

    CKAN_BASE_URL = "https://dadosabertos.aneel.gov.br/api/3/action"

    RESOURCE_TARIFAS = "fcf2906c-7c32-4b9b-a637-054e7a5234f4"
    RESOURCE_BANDEIRAS_ACIONAMENTO = "0591b8f6-fe54-437b-b72b-1aa2efd46e42"
    RESOURCE_BANDEIRAS_ADICIONAL = "5879ca80-b3bd-45b1-a135-d9b77c1d5b36"
    RESOURCE_FIO_B_ANOS = (
        "e8717aa8-2521-453f-bf16-fbb9a16eea39",  # 2026
        "a4060165-3a0c-404f-926c-83901088b67c",  # 2025
        "70ac08d1-53fc-4ceb-9c22-3a3a2c70e9fa",  # 2024
    )

    def __init__(self, session: aiohttp.ClientSession) -> None:
        """Inicializa cliente com sessao HTTP externa."""

        self._session = session

    async def fetch_tarifas(
        self,
        concessionaria: str,
        priority_method: str,
        reference_date: date,
    ) -> tuple[dict[str, Any], CollectionMetadata]:
        """Coleta TE/TUSD convencional e branca em chamada otimizada."""

        errors: list[str] = []
        methods = get_aneel_method_fallback_order(priority_method)
        for attempts, method in enumerate(methods, start=1):
            try:
                records = await self._collect_resource_records(
                    resource_id=self.RESOURCE_TARIFAS,
                    method=method,
                    filters={"SigAgente": concessionaria},
                )
                parsed = self._parse_tarifa_records(records, concessionaria, reference_date)
                if parsed["convencional"]["te_r_kwh"] <= 0 or parsed["convencional"]["tusd_r_kwh"] <= 0:
                    raise AneelClientError("Registros encontrados sem TE/TUSD convencional validos.")

                metadata = CollectionMetadata(
                    ultima_coleta=datetime.now().astimezone().isoformat(),
                    fonte="dados_abertos_aneel",
                    dataset="tarifas-distribuidoras-energia-eletrica",
                    resource_id=self.RESOURCE_TARIFAS,
                    metodo_acesso=method,
                    usou_fallback=attempts > 1,
                    tentativas=attempts,
                    confianca_fonte=ATTR_CONFIANCA_ALTA if attempts == 1 else ATTR_CONFIANCA_MEDIA,
                    vigencia_inicio=parsed.get("vigencia_inicio"),
                    vigencia_fim=parsed.get("vigencia_fim"),
                )
                return parsed, metadata
            except (AneelClientError, aiohttp.ClientError, TimeoutError, ValueError) as err:
                errors.append(f"{method}: {err}")
                continue

        raise AneelClientError(
            "Falha ao coletar tarifas ANEEL em todos os metodos. "
            + " | ".join(errors)
        )

    async def fetch_fio_b(
        self,
        concessionaria: str,
        priority_method: str,
        reference_date: date,
    ) -> tuple[dict[str, Any], CollectionMetadata]:
        """Coleta componente TUSD_FioB considerando recursos de anos diferentes."""

        errors: list[str] = []
        methods = get_aneel_method_fallback_order(priority_method)
        for attempts, method in enumerate(methods, start=1):
            try:
                all_records: list[dict[str, Any]] = []
                for resource_id in self.RESOURCE_FIO_B_ANOS:
                    records = await self._collect_resource_records(
                        resource_id=resource_id,
                        method=method,
                        filters={
                            "SigNomeAgente": concessionaria,
                            "DscComponenteTarifario": "TUSD_FioB",
                        },
                    )
                    all_records.extend(records)

                parsed = self._parse_fio_b_records(all_records, concessionaria, reference_date)
                if parsed["convencional_bruto_r_kwh"] <= 0:
                    raise AneelClientError("Fio B convencional nao localizado.")

                metadata = CollectionMetadata(
                    ultima_coleta=datetime.now().astimezone().isoformat(),
                    fonte="dados_abertos_aneel",
                    dataset="componentes-tarifarias",
                    resource_id=",".join(self.RESOURCE_FIO_B_ANOS),
                    metodo_acesso=method,
                    usou_fallback=attempts > 1,
                    tentativas=attempts,
                    confianca_fonte=ATTR_CONFIANCA_ALTA if attempts == 1 else ATTR_CONFIANCA_MEDIA,
                    vigencia_inicio=parsed.get("vigencia_inicio"),
                    vigencia_fim=parsed.get("vigencia_fim"),
                )
                return parsed, metadata
            except (AneelClientError, aiohttp.ClientError, TimeoutError, ValueError) as err:
                errors.append(f"{method}: {err}")
                continue

        raise AneelClientError(
            "Falha ao coletar Fio B ANEEL em todos os metodos. " + " | ".join(errors)
        )

    async def fetch_bandeira(
        self,
        priority_method: str,
        reference_date: date,
    ) -> tuple[dict[str, Any], CollectionMetadata]:
        """Coleta bandeira vigente e adicional homologado."""

        errors: list[str] = []
        methods = get_aneel_method_fallback_order(priority_method)
        for attempts, method in enumerate(methods, start=1):
            try:
                acionamentos = await self._collect_resource_records(
                    resource_id=self.RESOURCE_BANDEIRAS_ACIONAMENTO,
                    method=method,
                    filters=None,
                )
                vigencia = self._pick_latest_bandeira(acionamentos, reference_date)
                adicional_r_kwh = 0.0

                if vigencia["bandeira"] != "Verde":
                    adicionais = await self._collect_resource_records(
                        resource_id=self.RESOURCE_BANDEIRAS_ADICIONAL,
                        method=method,
                        filters=None,
                    )
                    adicional_r_kwh = self._pick_bandeira_adicional(
                        adicionais, vigencia["bandeira"], reference_date
                    )

                metadata = CollectionMetadata(
                    ultima_coleta=datetime.now().astimezone().isoformat(),
                    fonte="dados_abertos_aneel",
                    dataset="bandeiras-tarifarias",
                    resource_id=(
                        f"{self.RESOURCE_BANDEIRAS_ACIONAMENTO},"
                        f"{self.RESOURCE_BANDEIRAS_ADICIONAL}"
                    ),
                    metodo_acesso=method,
                    usou_fallback=attempts > 1,
                    tentativas=attempts,
                    confianca_fonte=ATTR_CONFIANCA_ALTA if attempts == 1 else ATTR_CONFIANCA_MEDIA,
                )
                return {
                    "bandeira": vigencia["bandeira"],
                    "competencia": vigencia["competencia"],
                    "adicional_r_kwh": adicional_r_kwh,
                }, metadata
            except (AneelClientError, aiohttp.ClientError, TimeoutError, ValueError) as err:
                errors.append(f"{method}: {err}")
                continue

        raise AneelClientError(
            "Falha ao coletar bandeiras ANEEL em todos os metodos. " + " | ".join(errors)
        )

    async def _collect_resource_records(
        self,
        resource_id: str,
        method: str,
        filters: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        """Consulta registros usando o metodo de acesso selecionado."""

        if method == ANEEL_METHOD_DATASTORE_SEARCH:
            return await self._datastore_search_records(resource_id, filters)
        if method == ANEEL_METHOD_DATASTORE_SEARCH_SQL:
            return await self._datastore_search_sql_records(resource_id, filters)
        if method == ANEEL_METHOD_CSV_XML:
            return await self._csv_xml_records(resource_id, filters)
        raise AneelClientError(f"Metodo ANEEL invalido: {method}")

    async def _datastore_search_records(
        self,
        resource_id: str,
        filters: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        """Consulta paginada via datastore_search."""

        records: list[dict[str, Any]] = []
        limit = 3000
        offset = 0

        while True:
            params: dict[str, Any] = {
                "resource_id": resource_id,
                "limit": limit,
                "offset": offset,
            }
            if filters:
                params["filters"] = json.dumps(filters, ensure_ascii=False)

            payload = await self._request_json("datastore_search", params)
            result = payload.get("result", {})
            chunk: list[dict[str, Any]] = result.get("records", [])
            records.extend(chunk)

            if len(chunk) < limit:
                break
            offset += limit

        return records

    async def _datastore_search_sql_records(
        self,
        resource_id: str,
        filters: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        """Consulta via datastore_search_sql com filtros simples."""

        where_parts: list[str] = []
        for field_name, field_value in (filters or {}).items():
            escaped = str(field_value).replace("'", "''")
            where_parts.append(f"\"{field_name}\" = '{escaped}'")

        where_clause = f" WHERE {' AND '.join(where_parts)}" if where_parts else ""
        sql = f'SELECT * FROM "{resource_id}"{where_clause} LIMIT 50000'

        payload = await self._request_json(
            "datastore_search_sql",
            {"sql": sql},
        )
        result = payload.get("result", {})
        records: list[dict[str, Any]] = result.get("records", [])
        return records

    async def _csv_xml_records(
        self,
        resource_id: str,
        filters: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        """Consulta de fallback em CSV/XML usando URL do recurso."""

        resource_payload = await self._request_json("resource_show", {"id": resource_id})
        resource = resource_payload.get("result", {})
        url = resource.get("url")
        if not url:
            raise AneelClientError(f"URL do recurso nao encontrada para {resource_id}.")

        async with self._session.get(url, timeout=90) as response:
            response.raise_for_status()
            content = await response.read()

        text = content.decode("utf-8", errors="ignore")
        records: list[dict[str, Any]] = []
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            if self._row_matches_filters(row, filters):
                records.append(dict(row))
        return records

    async def _request_json(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        """Executa request JSON para endpoint CKAN."""

        url = f"{self.CKAN_BASE_URL}/{action}"
        async with self._session.get(url, params=params, timeout=60) as response:
            response.raise_for_status()
            payload = await response.json(content_type=None)
        if not payload.get("success", False):
            raise AneelClientError(f"Resposta CKAN sem sucesso para {action}.")
        return payload

    def _parse_tarifa_records(
        self,
        records: list[dict[str, Any]],
        concessionaria: str,
        reference_date: date,
    ) -> dict[str, Any]:
        """Normaliza records de tarifa em estrutura de calculo."""

        result: dict[str, Any] = {
            "convencional": {"te_r_kwh": 0.0, "tusd_r_kwh": 0.0},
            "branca": {
                "fora_ponta": {"te_r_kwh": 0.0, "tusd_r_kwh": 0.0},
                "intermediario": {"te_r_kwh": 0.0, "tusd_r_kwh": 0.0},
                "ponta": {"te_r_kwh": 0.0, "tusd_r_kwh": 0.0},
            },
            "selection_debug": {
                "convencional": None,
                "branca": {
                    "fora_ponta": None,
                    "intermediario": None,
                    "ponta": None,
                },
            },
            "vigencia_inicio": None,
            "vigencia_fim": None,
        }
        selected_ranks: dict[str, Any] = {
            "convencional": None,
            "branca": {
                "fora_ponta": None,
                "intermediario": None,
                "ponta": None,
            },
        }

        for row in records:
            if not self._row_is_valid_tarifa(row, concessionaria, reference_date):
                continue

            modalidade = _normalize(self._pick(row, "DscModalidadeTarifaria"))
            posto = self._resolve_posto_key(self._pick(row, "NomPostoTarifario"))
            te_r_kwh, tusd_r_kwh = self._extract_te_tusd_r_kwh(row)
            if te_r_kwh <= 0 and tusd_r_kwh <= 0:
                continue
            rank = self._tarifa_selection_rank(row)

            if "convencional" in modalidade and "pre" not in modalidade:
                if self._rank_is_better(rank, selected_ranks["convencional"]):
                    result["convencional"] = {
                        "te_r_kwh": te_r_kwh,
                        "tusd_r_kwh": tusd_r_kwh,
                    }
                    selected_ranks["convencional"] = rank
                    result["selection_debug"]["convencional"] = self._build_row_debug(
                        row,
                        score=rank,
                        te_r_kwh=te_r_kwh,
                        tusd_r_kwh=tusd_r_kwh,
                    )
                    result["vigencia_inicio"] = self._string_or_none(
                        self._pick(row, "DatInicioVigencia")
                    )
                    result["vigencia_fim"] = self._string_or_none(
                        self._pick(row, "DatFimVigencia")
                    )
            elif "branca" in modalidade:
                current_rank = selected_ranks["branca"][posto]
                if self._rank_is_better(rank, current_rank):
                    result["branca"][posto] = {
                        "te_r_kwh": te_r_kwh,
                        "tusd_r_kwh": tusd_r_kwh,
                    }
                    selected_ranks["branca"][posto] = rank
                    result["selection_debug"]["branca"][posto] = self._build_row_debug(
                        row,
                        score=rank,
                        te_r_kwh=te_r_kwh,
                        tusd_r_kwh=tusd_r_kwh,
                    )
                    if not result["vigencia_inicio"]:
                        result["vigencia_inicio"] = self._string_or_none(
                            self._pick(row, "DatInicioVigencia")
                        )
                    if not result["vigencia_fim"]:
                        result["vigencia_fim"] = self._string_or_none(
                            self._pick(row, "DatFimVigencia")
                        )

        return result

    def _parse_fio_b_records(
        self,
        records: list[dict[str, Any]],
        concessionaria: str,
        reference_date: date,
    ) -> dict[str, Any]:
        """Extrai valores de Fio B para modalidade convencional e branca."""

        result: dict[str, Any] = {
            "convencional_bruto_r_kwh": 0.0,
            "branca_bruto_r_kwh_por_posto": {
                "fora_ponta": 0.0,
                "intermediario": 0.0,
                "ponta": 0.0,
            },
            "selection_debug": {
                "convencional": None,
                "branca": {
                    "fora_ponta": None,
                    "intermediario": None,
                    "ponta": None,
                },
            },
            "vigencia_inicio": None,
            "vigencia_fim": None,
        }
        selected_ranks: dict[str, Any] = {
            "convencional": None,
            "branca": {
                "fora_ponta": None,
                "intermediario": None,
                "ponta": None,
            },
        }

        valid_rows = [
            row
            for row in records
            if self._row_is_valid_fio_b(row, concessionaria, reference_date)
        ]
        valid_rows.sort(
            key=lambda row: _parse_any_date(self._pick(row, "DatInicioVigencia")) or date.min,
            reverse=True,
        )

        for row in valid_rows:
            modalidade = _normalize(self._pick(row, "DscModalidadeTarifaria"))
            posto = self._resolve_posto_key(self._pick(row, "DscPostoTarifario"))
            raw = _to_float(self._pick(row, "VlrComponenteTarifario"))
            if raw <= 0:
                continue
            value_r_kwh = _to_r_kwh(raw)
            rank = self._fio_b_selection_rank(row)

            if "convencional" in modalidade and "pre" not in modalidade:
                if self._rank_is_better(rank, selected_ranks["convencional"]):
                    result["convencional_bruto_r_kwh"] = value_r_kwh
                    result["selection_debug"]["convencional"] = self._build_row_debug(
                        row,
                        score=rank,
                        value_r_kwh=value_r_kwh,
                    )
                    selected_ranks["convencional"] = rank
                    result["vigencia_inicio"] = self._string_or_none(
                        self._pick(row, "DatInicioVigencia")
                    )
                    result["vigencia_fim"] = self._string_or_none(
                        self._pick(row, "DatFimVigencia")
                    )
            elif "branca" in modalidade:
                current_rank = selected_ranks["branca"][posto]
                if self._rank_is_better(rank, current_rank):
                    result["branca_bruto_r_kwh_por_posto"][posto] = value_r_kwh
                    result["selection_debug"]["branca"][posto] = self._build_row_debug(
                        row,
                        score=rank,
                        value_r_kwh=value_r_kwh,
                    )
                    selected_ranks["branca"][posto] = rank

        return result

    def _tarifa_selection_rank(self, row: dict[str, Any]) -> tuple[int, ...]:
        """Prioriza linha residencial padrao e evita SCEE/social por padrao."""

        subclasse = _normalize(self._pick(row, "DscSubClasse"))
        detalhe = _normalize(self._pick(row, "DscDetalhe"))
        return (
            1 if not self._is_social_subclass(subclasse) else 0,
            1 if subclasse == "residencial" else 0,
            1 if detalhe in ("nao se aplica", "") else 0,
            1 if "tarifa de aplicacao" in _normalize(self._pick(row, "DscBaseTarifaria")) else 0,
        )

    def _fio_b_selection_rank(self, row: dict[str, Any]) -> tuple[int, ...]:
        """Prioriza Fio B residencial B1 de aplicacao e sem detalhe especial."""

        subgrupo = _normalize(
            self._pick_first(row, "DscSubGrupoTarifario", "DscSubGrupo")
        )
        classe = _normalize(
            self._pick_first(row, "DscClasseConsumidor", "DscClasse")
        )
        subclasse = _normalize(
            self._pick_first(row, "DscSubClasseConsumidor", "DscSubClasse")
        )
        detalhe = _normalize(
            self._pick_first(row, "DscDetalheConsumidor", "DscDetalhe")
        )
        base = _normalize(self._pick(row, "DscBaseTarifaria"))
        return (
            1 if subgrupo == "b1" else 0,
            1 if classe == "residencial" else 0,
            1 if not self._is_social_subclass(subclasse) else 0,
            1 if subclasse == "residencial" else 0,
            1 if detalhe in ("nao se aplica", "") else 0,
            1 if "tarifa de aplicacao" in base else 0,
        )

    def _build_row_debug(
        self,
        row: dict[str, Any],
        *,
        score: tuple[int, ...],
        te_r_kwh: float | None = None,
        tusd_r_kwh: float | None = None,
        value_r_kwh: float | None = None,
    ) -> dict[str, Any]:
        """Resume a linha escolhida para apoiar diagnostico."""

        return {
            "score": list(score),
            "vigencia_inicio": self._string_or_none(self._pick(row, "DatInicioVigencia")),
            "vigencia_fim": self._string_or_none(self._pick(row, "DatFimVigencia")),
            "modalidade": self._string_or_none(
                self._pick_first(row, "DscModalidadeTarifaria")
            ),
            "posto": self._string_or_none(
                self._pick_first(row, "NomPostoTarifario", "DscPostoTarifario")
            ),
            "base_tarifaria": self._string_or_none(self._pick(row, "DscBaseTarifaria")),
            "subgrupo": self._string_or_none(
                self._pick_first(row, "DscSubGrupo", "DscSubGrupoTarifario")
            ),
            "classe": self._string_or_none(
                self._pick_first(row, "DscClasse", "DscClasseConsumidor")
            ),
            "subclasse": self._string_or_none(
                self._pick_first(row, "DscSubClasse", "DscSubClasseConsumidor")
            ),
            "detalhe": self._string_or_none(
                self._pick_first(row, "DscDetalhe", "DscDetalheConsumidor")
            ),
            "te_r_kwh": te_r_kwh,
            "tusd_r_kwh": tusd_r_kwh,
            "value_r_kwh": value_r_kwh,
        }

    def _pick_latest_bandeira(
        self,
        records: list[dict[str, Any]],
        reference_date: date,
    ) -> dict[str, str]:
        """Seleciona bandeira vigente mais recente ate a data de referencia."""

        best_row: dict[str, Any] | None = None
        best_date: date | None = None
        for row in records:
            competencia = (
                self._pick(row, "DatCompetencia")
                or self._pick(row, "DatReferencia")
                or self._pick(row, "MesAno")
                or self._pick(row, "AnoMes")
            )
            parsed = _parse_any_date(competencia)
            if parsed is None:
                continue
            if parsed > reference_date:
                continue
            if best_date is None or parsed > best_date:
                best_date = parsed
                best_row = row

        if best_row is None:
            return {"bandeira": "Verde", "competencia": reference_date.isoformat()}

        bandeira = (
            self._pick(best_row, "DscBandeiraTarifaria")
            or self._pick(best_row, "NomBandeiraTarifaria")
            or self._pick(best_row, "Bandeira")
            or "Verde"
        )
        return {
            "bandeira": str(bandeira).strip(),
            "competencia": (best_date or reference_date).isoformat(),
        }

    def _pick_bandeira_adicional(
        self,
        records: list[dict[str, Any]],
        bandeira: str,
        reference_date: date,
    ) -> float:
        """Seleciona adicional vigente da bandeira e converte para R$/kWh."""

        norm_bandeira = _normalize(bandeira)
        best_value = 0.0
        best_date: date | None = None
        for row in records:
            nome_bandeira = (
                self._pick(row, "DscBandeiraTarifaria")
                or self._pick(row, "NomBandeiraTarifaria")
                or self._pick(row, "Bandeira")
                or ""
            )
            if _normalize(str(nome_bandeira)) != norm_bandeira:
                continue
            start = _parse_any_date(self._pick(row, "DatInicioVigencia"))
            end = _parse_any_date(self._pick(row, "DatFimVigencia"))
            if not _is_within_range(reference_date, start, end):
                continue

            raw = _to_float(
                self._pick(row, "VlrAdicionalR$MWh")
                or self._pick(row, "VlrAdicionalR_MWh")
                or self._pick(row, "VlrAdicional")
                or self._pick(row, "VlrBandeira")
            )
            if raw <= 0:
                continue

            if best_date is None or (start and start > best_date):
                best_date = start
                best_value = _to_r_kwh(raw)
        return best_value

    def _row_is_valid_tarifa(
        self,
        row: dict[str, Any],
        concessionaria: str,
        reference_date: date,
    ) -> bool:
        """Valida linha de tarifa para o recorte do MVP."""

        if _normalize(self._pick(row, "SigAgente")) != _normalize(concessionaria):
            return False

        start = _parse_any_date(self._pick(row, "DatInicioVigencia"))
        end = _parse_any_date(self._pick(row, "DatFimVigencia"))
        if not _is_within_range(reference_date, start, end):
            return False

        modalidade = _normalize(self._pick(row, "DscModalidadeTarifaria"))
        if "convencional" not in modalidade and "branca" not in modalidade:
            return False
        if "pre" in modalidade:
            return False

        base = _normalize(self._pick(row, "DscBaseTarifaria"))
        if base and "tarifa de aplicacao" not in base:
            return False

        subgrupo = _normalize(self._pick(row, "DscSubGrupo"))
        if subgrupo and "b1" not in subgrupo:
            return False

        classe = _normalize(self._pick(row, "DscClasse"))
        if classe and "residencial" not in classe:
            return False

        return True

    def _row_is_valid_fio_b(
        self,
        row: dict[str, Any],
        concessionaria: str,
        reference_date: date,
    ) -> bool:
        """Valida linha de Fio B para concessionaria e vigencia."""

        agent = self._pick(row, "SigNomeAgente") or self._pick(row, "SigAgente")
        if _normalize(agent) != _normalize(concessionaria):
            return False

        componente = _normalize(self._pick(row, "DscComponenteTarifario"))
        if "tusd_fiob" not in componente and "tusd_fiob" not in componente.replace(" ", ""):
            return False

        start = _parse_any_date(self._pick(row, "DatInicioVigencia"))
        end = _parse_any_date(self._pick(row, "DatFimVigencia"))
        if not _is_within_range(reference_date, start, end):
            return False

        return True

    def _extract_te_tusd_r_kwh(self, row: dict[str, Any]) -> tuple[float, float]:
        """Extrai TE e TUSD em R$/kWh independente da estrutura da linha."""

        te_raw = _to_float(self._pick(row, "VlrTE"))
        tusd_raw = _to_float(self._pick(row, "VlrTUSD"))

        comp = _normalize(self._pick(row, "DscComponenteTarifario"))
        generic_raw = _to_float(
            self._pick(row, "VlrTarifa")
            or self._pick(row, "VlrComponenteTarifario")
            or self._pick(row, "VlrValor")
        )
        if comp == "te" and generic_raw > 0:
            te_raw = generic_raw
        if "tusd" in comp and generic_raw > 0:
            tusd_raw = generic_raw

        te = _to_r_kwh(te_raw) if te_raw > 0 else 0.0
        tusd = _to_r_kwh(tusd_raw) if tusd_raw > 0 else 0.0
        return te, tusd

    def _resolve_posto_key(self, posto_raw: Any) -> str:
        """Padroniza posto tarifario para chave interna."""

        posto = _normalize(posto_raw)
        if "intermedi" in posto:
            return "intermediario"
        if "ponta" in posto and "fora" not in posto:
            return "ponta"
        return "fora_ponta"

    @staticmethod
    def _pick(row: dict[str, Any], key: str) -> Any:
        """Busca chave exata ou case-insensitive."""

        if key in row:
            return row[key]
        key_lower = key.lower()
        for row_key, row_value in row.items():
            if str(row_key).lower() == key_lower:
                return row_value
        return None

    def _pick_first(self, row: dict[str, Any], *keys: str) -> Any:
        """Retorna o primeiro campo disponivel entre chaves alternativas."""

        for key in keys:
            value = self._pick(row, key)
            if value is not None:
                return value
        return None

    @staticmethod
    def _rank_is_better(
        candidate_rank: tuple[int, ...],
        current_rank: tuple[int, ...] | None,
    ) -> bool:
        """Compara ranks lexicograficos com fallback para ausencia."""

        return current_rank is None or candidate_rank > current_rank

    @staticmethod
    def _is_social_subclass(subclasse: str) -> bool:
        """Identifica subclasses sociais/baixa renda que nao sao o alvo padrao."""

        return any(
            keyword in subclasse
            for keyword in ("baixa renda", "tarifa social", "desconto social")
        )

    @staticmethod
    def _string_or_none(value: Any) -> str | None:
        """Normaliza valores opcionais para string simples."""

        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _row_matches_filters(row: dict[str, Any], filters: dict[str, Any] | None) -> bool:
        """Filtro local para fallback CSV/XML."""

        if not filters:
            return True
        for filter_key, filter_value in filters.items():
            row_value = None
            if filter_key in row:
                row_value = row[filter_key]
            else:
                filter_key_lower = filter_key.lower()
                for row_key, value in row.items():
                    if str(row_key).lower() == filter_key_lower:
                        row_value = value
                        break
            if row_value is None:
                return False
            if _normalize(row_value) != _normalize(filter_value):
                return False
        return True


def _normalize(value: Any) -> str:
    """Normaliza texto para comparacoes robustas sem acento."""

    if value is None:
        return ""
    text = str(value).strip().lower()
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def _to_float(value: Any) -> float:
    """Converte campo numerico com suporte a virgula/ponto."""

    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if not text:
        return 0.0

    if "," in text and "." in text:
        # Ex.: 1.234,56
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")

    try:
        return float(text)
    except ValueError:
        return 0.0


def _to_r_kwh(raw_value: float) -> float:
    """Converte para R$/kWh somente quando valor aparenta estar em R$/MWh."""

    if raw_value > 10:
        return mwh_to_kwh(raw_value)
    return raw_value


def _parse_any_date(value: Any) -> date | None:
    """Converte datas comuns de datasets ANEEL."""

    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()

    text = str(value).strip()
    if not text:
        return None

    normalized = text.replace("Z", "")
    candidates = [
        normalized,
        normalized.split("T")[0],
        normalized[:10],
        normalized[:7],
        normalized[:6],
    ]
    formats = ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%Y-%m", "%Y%m")

    for candidate in candidates:
        candidate = candidate.strip()
        if not candidate:
            continue
        for fmt in formats:
            try:
                parsed = datetime.strptime(candidate, fmt)
                if fmt in ("%Y-%m", "%Y%m"):
                    return date(parsed.year, parsed.month, 1)
                return parsed.date()
            except ValueError:
                continue
    return None


def _is_within_range(reference: date, start: date | None, end: date | None) -> bool:
    """Valida se data de referencia esta dentro da vigencia."""

    if start and reference < start:
        return False
    if end and reference > end:
        return False
    return True
