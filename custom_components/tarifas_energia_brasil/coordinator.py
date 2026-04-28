"""Versao: 0.1.0
Criado em: 2026-04-22 21:41:36 -03:00
Criado por: Codex
Projeto/pasta: ha.ext.tarifas
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .aneel_client import AneelClient, AneelClientError
from .calculators import (
    calcular_auto_consumo_kwh,
    calcular_fio_b_custo_efetivo_compensacao,
    calcular_scee_creditos_prioritarios,
    calcular_tarifa_branca_por_posto,
    calcular_tarifa_convencional,
    calcular_valor_conta_regular,
    calcular_valor_conta_tarifa_branca,
    calcular_valor_disponibilidade,
    disponibilidade_minima_kwh,
)
from .const import (
    CONF_CONCESSIONARIA,
    CONF_DIA_LEITURA,
    CONF_ENTIDADE_CONSUMO,
    CONF_ENTIDADE_GERACAO,
    CONF_ENTIDADE_INJECAO,
    CONF_HORAS_ATUALIZACAO,
    CONF_METODO_ANEEL,
    CONF_QUEBRAS_CALCULO,
    CONF_TB_FERIADOS_EXTRAS,
    CONF_TIPO_FORNECIMENTO,
    DIA_LEITURA_PADRAO,
    DOMAIN,
    FORNECIMENTO_MONOFASICO,
    HORAS_ATUALIZACAO_PADRAO,
    METODO_ANEEL_PADRAO,
    QUEBRA_DIARIA,
    QUEBRA_MENSAL,
    QUEBRA_SEMANAL,
    QUEBRAS_PADRAO,
    QUEBRAS_VALIDAS,
)
from .credito_ledger import (
    CreditoEntry,
    add_credit_entry,
    competencia_from_cycle_key,
    consume_credits_oldest_first,
    deserialize_entries,
    purge_expired_credits,
    serialize_entries,
    total_credits_kwh,
)
from .icms_rules import build_icms_calculation_attributes, resolve_icms_percent
from .models import MetadadosColeta, ResultadoCalculo
from .tarifa_branca_time import (
    POSTOS_TARIFA_BRANCA,
    build_holiday_calendar,
    parse_extra_holidays,
    resolve_tarifa_branca_posto,
    resolve_tarifa_branca_schedule,
    split_interval_by_midnight,
    split_interval_by_tarifa_branca,
)
from .tributos import extract_tributos

_LOGGER = logging.getLogger(__name__)
_STATE_STORAGE_VERSION = 1
_INITIAL_FAILURE_RETRY_INTERVAL = timedelta(minutes=15)


class TarifasEnergiaBrasilCoordinator(DataUpdateCoordinator[ResultadoCalculo]):
    """Orquestra coleta externa, fallback e calculos da integracao."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Configura o coordinator com estado incremental para quebras."""

        self.hass = hass
        self.entry = entry
        self._aneel_client = AneelClient(async_get_clientsession(hass))
        self._state_store: Store[dict[str, Any]] = Store(
            hass=hass,
            version=_STATE_STORAGE_VERSION,
            key=f"{DOMAIN}_{entry.entry_id}_state",
        )
        self._state_loaded = False

        self._last_consumo_total_kwh: float | None = None
        self._last_geracao_total_kwh: float | None = None
        self._last_injecao_total_kwh: float | None = None
        self._last_consumo_timestamp: datetime | None = None
        self._last_geracao_timestamp: datetime | None = None
        self._last_injecao_timestamp: datetime | None = None
        self._consumo_period_state = self._new_period_state()
        self._geracao_period_state = self._new_period_state()
        self._injecao_period_state = self._new_period_state()
        self._consumo_tarifa_branca_state = self._new_posto_period_state()

        self._creditos_ledger: list[CreditoEntry] = []
        self._credito_estimado_atual_kwh = 0.0
        self._credito_consumido_estimado_atual_kwh = 0.0
        self._ultimo_ciclo_mensal: str | None = None
        self._consumo_reset_detectado = 0
        self._geracao_reset_detectado = 0
        self._injecao_reset_detectado = 0
        self._tarifa_branca_last_interval_seconds = 0.0
        self._tarifa_branca_last_segment_count = 0
        self._tarifa_branca_low_confidence = False
        self._tarifa_branca_schedule_source = "desconhecido"
        self._tarifa_branca_invalid_extra_holidays: list[str] = []
        self._unsub_state_listeners: list[Any] = []

        self._configured_update_interval = timedelta(hours=self._effective_update_hours())

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=self._configured_update_interval,
        )

    @staticmethod
    def _new_period_state() -> dict[str, dict[str, str | float | None]]:
        """Cria estrutura de estado para acumuladores por periodo."""

        return {
            QUEBRA_DIARIA: {"key": None, "kwh": 0.0},
            QUEBRA_SEMANAL: {"key": None, "kwh": 0.0},
            QUEBRA_MENSAL: {"key": None, "kwh": 0.0},
        }

    @staticmethod
    def _new_posto_period_state() -> dict[str, dict[str, Any]]:
        """Cria estrutura de acumuladores por posto para a Tarifa Branca."""

        return {
            QUEBRA_DIARIA: {
                "key": None,
                "postos": {posto: 0.0 for posto in POSTOS_TARIFA_BRANCA},
            },
            QUEBRA_SEMANAL: {
                "key": None,
                "postos": {posto: 0.0 for posto in POSTOS_TARIFA_BRANCA},
            },
            QUEBRA_MENSAL: {
                "key": None,
                "postos": {posto: 0.0 for posto in POSTOS_TARIFA_BRANCA},
            },
        }

    async def async_ensure_state_loaded(self) -> None:
        """Carrega estado persistido apenas uma vez por ciclo de vida."""

        if self._state_loaded:
            return
        payload = await self._state_store.async_load()
        if payload:
            self._last_consumo_total_kwh = self._as_float_or_none(
                payload.get("last_consumo_total_kwh")
            )
            self._last_geracao_total_kwh = self._as_float_or_none(
                payload.get("last_geracao_total_kwh")
            )
            self._last_injecao_total_kwh = self._as_float_or_none(
                payload.get("last_injecao_total_kwh")
            )
            self._last_consumo_timestamp = self._as_datetime_or_none(
                payload.get("last_consumo_timestamp")
            )
            self._last_geracao_timestamp = self._as_datetime_or_none(
                payload.get("last_geracao_timestamp")
            )
            self._last_injecao_timestamp = self._as_datetime_or_none(
                payload.get("last_injecao_timestamp")
            )

            loaded_consumo = payload.get("consumo_period_state")
            loaded_geracao = payload.get("geracao_period_state")
            loaded_injecao = payload.get("injecao_period_state")
            loaded_consumo_tarifa_branca = payload.get("consumo_tarifa_branca_state")
            if isinstance(loaded_consumo, dict):
                self._consumo_period_state = self._merge_period_state(loaded_consumo)
            if isinstance(loaded_geracao, dict):
                self._geracao_period_state = self._merge_period_state(loaded_geracao)
            if isinstance(loaded_injecao, dict):
                self._injecao_period_state = self._merge_period_state(loaded_injecao)
            if isinstance(loaded_consumo_tarifa_branca, dict):
                self._consumo_tarifa_branca_state = self._merge_posto_period_state(
                    loaded_consumo_tarifa_branca
                )

            self._ultimo_ciclo_mensal = self._as_str_or_none(payload.get("ultimo_ciclo_mensal"))
            self._credito_estimado_atual_kwh = max(
                self._as_float(payload.get("credito_estimado_atual_kwh"), 0.0),
                0.0,
            )
            self._credito_consumido_estimado_atual_kwh = max(
                self._as_float(payload.get("credito_consumido_estimado_atual_kwh"), 0.0),
                0.0,
            )
            self._creditos_ledger = deserialize_entries(payload.get("creditos_ledger"))
            cached_snapshot = self._restore_cached_snapshot(payload.get("last_snapshot"))
            if cached_snapshot is not None:
                self.data = cached_snapshot
        self._state_loaded = True

    async def async_persist_state(self) -> None:
        """Persiste estado atual em storage do Home Assistant."""

        await self._state_store.async_save(self._serialize_state())

    def _schedule_state_save(self) -> None:
        """Agenda persistencia assicrona para reduzir overhead."""

        self._state_store.async_delay_save(self._serialize_state, 2)

    def _serialize_state(self) -> dict[str, Any]:
        """Serializa estado incremental e ledger de creditos."""

        return {
            "last_consumo_total_kwh": self._last_consumo_total_kwh,
            "last_geracao_total_kwh": self._last_geracao_total_kwh,
            "last_injecao_total_kwh": self._last_injecao_total_kwh,
            "last_consumo_timestamp": (
                self._last_consumo_timestamp.isoformat()
                if self._last_consumo_timestamp is not None
                else None
            ),
            "last_geracao_timestamp": (
                self._last_geracao_timestamp.isoformat()
                if self._last_geracao_timestamp is not None
                else None
            ),
            "last_injecao_timestamp": (
                self._last_injecao_timestamp.isoformat()
                if self._last_injecao_timestamp is not None
                else None
            ),
            "consumo_period_state": self._consumo_period_state,
            "geracao_period_state": self._geracao_period_state,
            "injecao_period_state": self._injecao_period_state,
            "consumo_tarifa_branca_state": self._consumo_tarifa_branca_state,
            "ultimo_ciclo_mensal": self._ultimo_ciclo_mensal,
            "credito_estimado_atual_kwh": self._credito_estimado_atual_kwh,
            "credito_consumido_estimado_atual_kwh": self._credito_consumido_estimado_atual_kwh,
            "creditos_ledger": serialize_entries(self._creditos_ledger),
            "last_snapshot": self._serialize_cached_snapshot(),
        }

    def _serialize_cached_snapshot(self) -> dict[str, Any] | None:
        """Serializa o ultimo snapshot valido para restauracao apos restart."""

        if self.data is None:
            return None
        return {
            "atualizado_em": self.data.atualizado_em.isoformat(),
            "concessionaria": self.data.concessionaria,
            "valores": self.data.valores,
            "coletas_por_chave": {
                key: asdict(metadata) for key, metadata in self.data.coletas_por_chave.items()
            },
            "diagnosticos": self.data.diagnosticos,
        }

    def _restore_cached_snapshot(self, payload: Any) -> ResultadoCalculo | None:
        """Restaura snapshot persistido para evitar sensores vazios no boot."""

        if not isinstance(payload, dict):
            return None
        atualizado_em = self._as_datetime_or_none(payload.get("atualizado_em"))
        concessionaria = self._as_str_or_none(payload.get("concessionaria"))
        valores = payload.get("valores")
        if atualizado_em is None or concessionaria is None or not isinstance(valores, dict):
            return None

        coletas_por_chave: dict[str, MetadadosColeta] = {}
        raw_collections = payload.get("coletas_por_chave")
        if isinstance(raw_collections, dict):
            allowed_fields = set(MetadadosColeta.__dataclass_fields__)
            for key, metadata_payload in raw_collections.items():
                if not isinstance(metadata_payload, dict):
                    continue
                metadata_kwargs = {
                    field: metadata_payload[field]
                    for field in allowed_fields
                    if field in metadata_payload
                }
                coletas_por_chave[str(key)] = MetadadosColeta(**metadata_kwargs)

        diagnosticos = payload.get("diagnosticos")
        restored_diagnosticos = dict(diagnosticos) if isinstance(diagnosticos, dict) else {}
        restored_diagnosticos["snapshot_restaurado_de_cache"] = True

        return ResultadoCalculo(
            atualizado_em=atualizado_em,
            concessionaria=concessionaria,
            valores=dict(valores),
            coletas_por_chave=coletas_por_chave,
            diagnosticos=restored_diagnosticos,
        )

    @staticmethod
    def _merge_period_state(payload: dict[str, Any]) -> dict[str, dict[str, str | float | None]]:
        """Mescla payload persistido com estrutura padrao dos periodos."""

        merged = TarifasEnergiaBrasilCoordinator._new_period_state()
        for key in QUEBRAS_VALIDAS:
            incoming = payload.get(key)
            if isinstance(incoming, dict):
                merged[key]["key"] = incoming.get("key")
                merged[key]["kwh"] = float(incoming.get("kwh", 0.0))
        return merged

    @staticmethod
    def _merge_posto_period_state(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
        """Mescla payload persistido de acumuladores por posto."""

        merged = TarifasEnergiaBrasilCoordinator._new_posto_period_state()
        for key in QUEBRAS_VALIDAS:
            incoming = payload.get(key)
            if not isinstance(incoming, dict):
                continue
            merged[key]["key"] = incoming.get("key")
            postos = incoming.get("postos")
            if isinstance(postos, dict):
                for posto in POSTOS_TARIFA_BRANCA:
                    merged[key]["postos"][posto] = float(postos.get(posto, 0.0))
        return merged

    @staticmethod
    def _as_float(value: Any, default: float) -> float:
        """Converte valor para float de forma tolerante."""

        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _as_float_or_none(value: Any) -> float | None:
        """Converte valor para float opcional."""

        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _as_str_or_none(value: Any) -> str | None:
        """Converte valor para string opcional sem lixo."""

        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _as_datetime_or_none(value: Any) -> datetime | None:
        """Converte texto ISO em datetime opcional."""

        if value is None:
            return None
        try:
            return datetime.fromisoformat(str(value))
        except (TypeError, ValueError):
            return None

    async def async_start_state_tracking(self) -> None:
        """Assina mudancas das entidades de consumo/geracao para calculo incremental."""

        if self._unsub_state_listeners:
            return

        tracked = []
        for entity_id in (
            self._effective_value(CONF_ENTIDADE_CONSUMO),
            self._effective_value(CONF_ENTIDADE_GERACAO),
            self._effective_value(CONF_ENTIDADE_INJECAO),
        ):
            if isinstance(entity_id, str) and entity_id and entity_id not in tracked:
                tracked.append(entity_id)

        if not tracked:
            return

        self._unsub_state_listeners.append(
            async_track_state_change_event(
                self.hass,
                tracked,
                self._handle_tracked_state_change,
            )
        )

    async def async_stop_state_tracking(self) -> None:
        """Remove listeners das entidades rastreadas."""

        while self._unsub_state_listeners:
            unsub = self._unsub_state_listeners.pop()
            try:
                unsub()
            except Exception:  # pragma: no cover - defensivo para runtime HA
                _LOGGER.debug("Falha ao remover listener de estado.", exc_info=True)

    @callback
    def _handle_tracked_state_change(self, event: Any) -> None:
        """Atualiza snapshot dinamico sem nova chamada externa."""

        if self.data is None:
            return

        now = getattr(event, "time_fired", datetime.now().astimezone())
        if isinstance(now, datetime):
            now = now.astimezone()
        else:
            now = datetime.now().astimezone()

        self._process_energy_states(
            now=now,
            consumo_total_kwh=self._read_entity_kwh(self._effective_value(CONF_ENTIDADE_CONSUMO)),
            geracao_total_kwh=self._read_entity_kwh(self._effective_value(CONF_ENTIDADE_GERACAO)),
            injecao_total_kwh=self._read_entity_kwh(self._effective_value(CONF_ENTIDADE_INJECAO)),
            reading_day=int(self._effective_value(CONF_DIA_LEITURA, DIA_LEITURA_PADRAO)),
            tariff_context=self._cached_rollover_context(),
        )
        icms_source = self._refresh_icms_dependent_valores(
            valores=self.data.valores,
            concessionaria=self.data.concessionaria,
            consumo_mensal_kwh=float(self._consumo_period_state[QUEBRA_MENSAL]["kwh"]),
            tipo_fornecimento=str(
                self._effective_value(CONF_TIPO_FORNECIMENTO, FORNECIMENTO_MONOFASICO)
            ),
            fallback_icms_percent=float(
                self.data.diagnosticos.get(
                    "icms_percent_base_fonte",
                    self.data.valores.get("icms_percent", 0.0) or 0.0,
                )
                or 0.0
            ),
            possui_historico_consumo=True,
            reference_date=now.date(),
        )
        self._apply_dynamic_valores_to_snapshot(
            valores=self.data.valores,
            quebras_habilitadas=self._effective_breakdowns(),
            consumo_periodos=self._current_period_valores(self._consumo_period_state),
            geracao_periodos=self._current_period_valores(self._geracao_period_state),
            injecao_periodos=self._current_period_valores(self._injecao_period_state),
            consumo_tarifa_branca=self._current_posto_period_valores(
                self._consumo_tarifa_branca_state
            ),
            possui_geracao=bool(self._effective_value(CONF_ENTIDADE_GERACAO)),
            possui_injecao=bool(self._effective_value(CONF_ENTIDADE_INJECAO)),
            geracao_total_kwh=self._last_geracao_total_kwh,
            injecao_total_kwh=self._last_injecao_total_kwh,
            tipo_fornecimento=str(
                self._effective_value(CONF_TIPO_FORNECIMENTO, FORNECIMENTO_MONOFASICO)
            ),
        )
        self.data.atualizado_em = now
        self.data.diagnosticos["icms_source"] = icms_source
        self.data.diagnosticos["icms_percent_aplicado"] = self.data.valores.get("icms_percent")
        self._update_dynamic_diagnosticos(now)
        self._schedule_state_save()
        self.async_update_listeners()

    def _resolve_tarifa_branca_context(
        self,
        *reference_datetimes: datetime,
    ) -> tuple[Any, set[date], dict[str, Any]]:
        """Resolve horarios efetivos e calendario de feriados da Tarifa Branca."""

        effective_config = {
            **self.entry.data,
            **self.entry.options,
        }
        schedule, schedule_metadata = resolve_tarifa_branca_schedule(effective_config)
        extra_holidays, invalid = parse_extra_holidays(
            effective_config.get(CONF_TB_FERIADOS_EXTRAS)
        )
        years = {datetime.now().year}
        for reference in reference_datetimes:
            if isinstance(reference, datetime):
                years.update({reference.year - 1, reference.year, reference.year + 1})
        holidays = build_holiday_calendar(sorted(years), extra_holidays)

        self._tarifa_branca_schedule_source = str(schedule_metadata["source"])
        self._tarifa_branca_invalid_extra_holidays = invalid
        return schedule, holidays, schedule_metadata

    @staticmethod
    def _current_period_valores(
        period_state: dict[str, dict[str, str | float | None]],
    ) -> dict[str, float]:
        """Extrai acumuladores correntes por quebra."""

        return {period: float(period_state[period]["kwh"]) for period in QUEBRAS_VALIDAS}

    @staticmethod
    def _current_posto_period_valores(
        period_state: dict[str, dict[str, Any]],
    ) -> dict[str, dict[str, float]]:
        """Extrai acumuladores correntes por posto tarifario."""

        valores: dict[str, dict[str, float]] = {}
        for period in QUEBRAS_VALIDAS:
            valores[period] = {
                posto: float(period_state[period]["postos"][posto])
                for posto in POSTOS_TARIFA_BRANCA
            }
        return valores

    def _prepare_delta_context(
        self,
        current_total_kwh: float,
        current_timestamp: datetime,
        last_total_kwh: float | None,
        last_timestamp: datetime | None,
    ) -> dict[str, Any]:
        """Prepara contexto incremental entre a ultima leitura e a atual."""

        if last_total_kwh is None or last_timestamp is None:
            return {
                "has_previous": False,
                "delta_kwh": 0.0,
                "reset_detected": False,
                "start": None,
                "end": current_timestamp,
            }

        delta = current_total_kwh - float(last_total_kwh)
        reset_detected = delta < 0
        return {
            "has_previous": True,
            "delta_kwh": 0.0 if reset_detected else max(delta, 0.0),
            "raw_delta_kwh": delta,
            "reset_detected": reset_detected,
            "start": last_timestamp,
            "end": current_timestamp,
        }

    def _ensure_scalar_current_keys(
        self,
        period_state: dict[str, dict[str, str | float | None]],
        now: datetime,
        reading_day: int,
    ) -> dict[str, list[tuple[str, float]]]:
        """Garante rollover de acumuladores escalares mesmo sem delta."""

        rollovers: dict[str, list[tuple[str, float]]] = {period: [] for period in QUEBRAS_VALIDAS}
        for period in QUEBRAS_VALIDAS:
            current_key = self._period_key(period, now, reading_day)
            if period_state[period]["key"] != current_key:
                old_key = period_state[period]["key"]
                old_value = float(period_state[period]["kwh"])
                if old_key is not None:
                    rollovers[period].append((str(old_key), old_value))
                period_state[period]["key"] = current_key
                period_state[period]["kwh"] = 0.0
        return {k: v for k, v in rollovers.items() if v}

    def _ensure_posto_current_keys(
        self,
        period_state: dict[str, dict[str, Any]],
        now: datetime,
        reading_day: int,
    ) -> dict[str, list[tuple[str, dict[str, float]]]]:
        """Garante rollover dos acumuladores por posto mesmo sem delta."""

        rollovers: dict[str, list[tuple[str, dict[str, float]]]] = {
            period: [] for period in QUEBRAS_VALIDAS
        }
        for period in QUEBRAS_VALIDAS:
            current_key = self._period_key(period, now, reading_day)
            if period_state[period]["key"] != current_key:
                old_key = period_state[period]["key"]
                old_postos = {
                    posto: float(period_state[period]["postos"][posto])
                    for posto in POSTOS_TARIFA_BRANCA
                }
                if old_key is not None:
                    rollovers[period].append((str(old_key), old_postos))
                period_state[period]["key"] = current_key
                period_state[period]["postos"] = {posto: 0.0 for posto in POSTOS_TARIFA_BRANCA}
        return {k: v for k, v in rollovers.items() if v}

    def _apply_scalar_delta_context(
        self,
        period_state: dict[str, dict[str, str | float | None]],
        now: datetime,
        reading_day: int,
        delta_context: dict[str, Any],
    ) -> tuple[dict[str, float], dict[str, list[tuple[str, float]]]]:
        """Aplica delta temporal aos acumuladores escalares."""

        rollovers: dict[str, list[tuple[str, float]]] = {}
        if not delta_context["has_previous"]:
            rollovers = self._ensure_scalar_current_keys(period_state, now, reading_day)
            return self._current_period_valores(period_state), rollovers
        if delta_context.get("reset_detected"):
            rollovers = self._ensure_scalar_current_keys(period_state, now, reading_day)
            return self._current_period_valores(period_state), rollovers

        start = delta_context["start"]
        end = delta_context["end"]
        delta_kwh = float(delta_context["delta_kwh"])
        if not isinstance(start, datetime) or not isinstance(end, datetime) or delta_kwh <= 0:
            rollovers = self._ensure_scalar_current_keys(period_state, now, reading_day)
            return self._current_period_valores(period_state), rollovers

        total_seconds = max((end - start).total_seconds(), 1.0)
        for segment_start, segment_end in split_interval_by_midnight(start, end):
            segment_delta = delta_kwh * (
                (segment_end - segment_start).total_seconds() / total_seconds
            )
            for period in QUEBRAS_VALIDAS:
                period_key = self._period_key(period, segment_start, reading_day)
                if period_state[period]["key"] != period_key:
                    old_key = period_state[period]["key"]
                    old_value = float(period_state[period]["kwh"])
                    if old_key is not None:
                        rollovers.setdefault(period, []).append((str(old_key), old_value))
                    period_state[period]["key"] = period_key
                    period_state[period]["kwh"] = 0.0
                period_state[period]["kwh"] = float(period_state[period]["kwh"]) + segment_delta
        current_rollovers = self._ensure_scalar_current_keys(period_state, now, reading_day)
        for period, items in current_rollovers.items():
            rollovers.setdefault(period, []).extend(items)
        return self._current_period_valores(period_state), rollovers

    def _apply_tarifa_branca_delta_context(
        self,
        period_state: dict[str, dict[str, Any]],
        now: datetime,
        reading_day: int,
        delta_context: dict[str, Any],
        schedule: Any,
        holidays: set[date],
    ) -> tuple[dict[str, dict[str, float]], dict[str, list[tuple[str, dict[str, float]]]]]:
        """Aplica delta temporal aos acumuladores por posto da Tarifa Branca."""

        rollovers: dict[str, list[tuple[str, dict[str, float]]]] = {}
        if not delta_context["has_previous"]:
            rollovers = self._ensure_posto_current_keys(period_state, now, reading_day)
            return self._current_posto_period_valores(period_state), rollovers
        if delta_context.get("reset_detected"):
            self._tarifa_branca_last_interval_seconds = 0.0
            self._tarifa_branca_last_segment_count = 0
            self._tarifa_branca_low_confidence = False
            rollovers = self._ensure_posto_current_keys(period_state, now, reading_day)
            return self._current_posto_period_valores(period_state), rollovers

        start = delta_context["start"]
        end = delta_context["end"]
        delta_kwh = float(delta_context["delta_kwh"])
        if not isinstance(start, datetime) or not isinstance(end, datetime) or delta_kwh <= 0:
            rollovers = self._ensure_posto_current_keys(period_state, now, reading_day)
            return self._current_posto_period_valores(period_state), rollovers

        segments = split_interval_by_tarifa_branca(start, end, schedule, holidays)
        total_seconds = max((end - start).total_seconds(), 1.0)
        self._tarifa_branca_last_interval_seconds = total_seconds
        self._tarifa_branca_last_segment_count = len(segments)
        self._tarifa_branca_low_confidence = total_seconds >= 21600

        for segment_start, segment_end, posto in segments:
            segment_delta = delta_kwh * (
                (segment_end - segment_start).total_seconds() / total_seconds
            )
            for period in QUEBRAS_VALIDAS:
                period_key = self._period_key(period, segment_start, reading_day)
                if period_state[period]["key"] != period_key:
                    old_key = period_state[period]["key"]
                    old_postos = {
                        current_posto: float(period_state[period]["postos"][current_posto])
                        for current_posto in POSTOS_TARIFA_BRANCA
                    }
                    if old_key is not None:
                        rollovers.setdefault(period, []).append((str(old_key), old_postos))
                    period_state[period]["key"] = period_key
                    period_state[period]["postos"] = {
                        current_posto: 0.0 for current_posto in POSTOS_TARIFA_BRANCA
                    }
                period_state[period]["postos"][posto] = (
                    float(period_state[period]["postos"][posto]) + segment_delta
                )
        current_rollovers = self._ensure_posto_current_keys(period_state, now, reading_day)
        for period, items in current_rollovers.items():
            rollovers.setdefault(period, []).extend(items)
        return self._current_posto_period_valores(period_state), rollovers

    def _refresh_icms_dependent_valores(
        self,
        valores: dict[str, float | str | bool | None],
        concessionaria: str,
        consumo_mensal_kwh: float,
        tipo_fornecimento: str,
        fallback_icms_percent: float,
        possui_historico_consumo: bool,
        reference_date: date,
    ) -> str:
        """Recalcula ICMS usando o maior valor entre consumo e minimo faturavel."""

        disponibilidade_kwh = disponibilidade_minima_kwh(tipo_fornecimento)
        consumo_faturavel_kwh = self._icms_consumo_faturavel_kwh(
            consumo_mensal_kwh=consumo_mensal_kwh,
            disponibilidade_kwh=disponibilidade_kwh,
        )
        if possui_historico_consumo or consumo_mensal_kwh > 0 or disponibilidade_kwh > 0:
            icms_aplicado_percent, icms_source = resolve_icms_percent(
                concessionaria=concessionaria,
                consumo_mensal_kwh=consumo_faturavel_kwh,
                fallback_icms_percent=fallback_icms_percent,
            )
        else:
            icms_aplicado_percent = fallback_icms_percent
            icms_source = "fallback_bootstrap_sem_historico"

        pis_percent = float(valores.get("pis_percent", 0.0) or 0.0)
        cofins_percent = float(valores.get("cofins_percent", 0.0) or 0.0)
        tarifa_conv_bruta, tarifa_conv_final = calcular_tarifa_convencional(
            te_convencional_r_kwh=float(valores.get("te_convencional_r_kwh", 0.0) or 0.0),
            tusd_convencional_r_kwh=float(valores.get("tusd_convencional_r_kwh", 0.0) or 0.0),
            pis_percent=pis_percent,
            cofins_percent=cofins_percent,
            icms_percent=icms_aplicado_percent,
        )
        tarifa_branca = calcular_tarifa_branca_por_posto(
            te_por_posto_r_kwh={
                "fora_ponta": float(valores.get("te_branca_fora_ponta_r_kwh", 0.0) or 0.0),
                "intermediario": float(valores.get("te_branca_intermediario_r_kwh", 0.0) or 0.0),
                "ponta": float(valores.get("te_branca_ponta_r_kwh", 0.0) or 0.0),
            },
            tusd_por_posto_r_kwh={
                "fora_ponta": float(valores.get("tusd_branca_fora_ponta_r_kwh", 0.0) or 0.0),
                "intermediario": float(valores.get("tusd_branca_intermediario_r_kwh", 0.0) or 0.0),
                "ponta": float(valores.get("tusd_branca_ponta_r_kwh", 0.0) or 0.0),
            },
            pis_percent=pis_percent,
            cofins_percent=cofins_percent,
            icms_percent=icms_aplicado_percent,
        )
        valores["tarifa_convencional_bruta_r_kwh"] = tarifa_conv_bruta
        valores["tarifa_convencional_final_r_kwh"] = tarifa_conv_final
        valores["tarifa_branca_fora_ponta_bruta_r_kwh"] = tarifa_branca["fora_ponta"][
            "tarifa_bruta_r_kwh"
        ]
        valores["tarifa_branca_fora_ponta_final_r_kwh"] = tarifa_branca["fora_ponta"][
            "tarifa_final_r_kwh"
        ]
        valores["tarifa_branca_intermediario_bruta_r_kwh"] = tarifa_branca["intermediario"][
            "tarifa_bruta_r_kwh"
        ]
        valores["tarifa_branca_intermediario_final_r_kwh"] = tarifa_branca["intermediario"][
            "tarifa_final_r_kwh"
        ]
        valores["tarifa_branca_ponta_bruta_r_kwh"] = tarifa_branca["ponta"]["tarifa_bruta_r_kwh"]
        valores["tarifa_branca_ponta_final_r_kwh"] = tarifa_branca["ponta"]["tarifa_final_r_kwh"]
        valores["icms_percent"] = icms_aplicado_percent
        valores.update(
            self._icms_explanation_valores(
                concessionaria=concessionaria,
                consumo_mensal_kwh=consumo_mensal_kwh,
                consumo_faturavel_kwh=consumo_faturavel_kwh,
                disponibilidade_minima_kwh=disponibilidade_kwh,
                fallback_icms_percent=fallback_icms_percent,
                icms_aplicado_percent=icms_aplicado_percent,
                icms_source=icms_source,
            )
        )
        valores.update(
            self._fio_b_effective_valores(
                fio_b_bruto_r_kwh=float(valores.get("fio_b_bruto_r_kwh", 0.0) or 0.0),
                tusd_convencional_r_kwh=float(valores.get("tusd_convencional_r_kwh", 0.0) or 0.0),
                icms_consumo_percent=icms_aplicado_percent,
                icms_consumo_source=icms_source,
                reference_date=reference_date,
                pis_percent=pis_percent,
                cofins_percent=cofins_percent,
            )
        )
        return icms_source

    def _icms_explanation_valores(
        self,
        concessionaria: str,
        consumo_mensal_kwh: float,
        consumo_faturavel_kwh: float,
        disponibilidade_minima_kwh: float,
        fallback_icms_percent: float,
        icms_aplicado_percent: float,
        icms_source: str,
    ) -> dict[str, float | str | list[str]]:
        """Monta atributos de calculo do ICMS para publicar no sensor."""

        return build_icms_calculation_attributes(
            concessionaria=concessionaria,
            consumo_mensal_kwh=consumo_mensal_kwh,
            consumo_faturavel_kwh=consumo_faturavel_kwh,
            disponibilidade_minima_kwh=disponibilidade_minima_kwh,
            fallback_icms_percent=fallback_icms_percent,
            icms_aplicado_percent=icms_aplicado_percent,
            icms_source=icms_source,
        )

    @staticmethod
    def _icms_consumo_faturavel_kwh(
        consumo_mensal_kwh: float,
        disponibilidade_kwh: float,
    ) -> float:
        """Retorna a base minima de kWh usada para selecionar a faixa de ICMS."""

        return max(consumo_mensal_kwh, disponibilidade_kwh, 0.0)

    def _fio_b_effective_valores(
        self,
        fio_b_bruto_r_kwh: float,
        tusd_convencional_r_kwh: float,
        icms_consumo_percent: float,
        icms_consumo_source: str,
        reference_date: date,
        pis_percent: float,
        cofins_percent: float,
    ) -> dict[str, float | str]:
        """Calcula custo efetivo do Fio B e monta atributos explicativos."""

        detalhes = calcular_fio_b_custo_efetivo_compensacao(
            tusd_convencional_r_kwh=tusd_convencional_r_kwh,
            fio_b_bruto_r_kwh=fio_b_bruto_r_kwh,
            ano=reference_date.year,
            pis_percent=pis_percent,
            cofins_percent=cofins_percent,
            icms_consumo_percent=icms_consumo_percent,
            icms_compensacao_percent=0.0,
        )
        detalhes["fio_b_icms_consumo_source"] = icms_consumo_source
        detalhes["fio_b_calculo_expressao"] = (
            "TUSD consumo final "
            f"({tusd_convencional_r_kwh:.6f} / (1 - {icms_consumo_percent:.2f}%) "
            f"/ (1 - {pis_percent + cofins_percent:.2f}%)) - "
            "TUSD injetada creditada final "
            f"(({tusd_convencional_r_kwh:.6f} - "
            f"({fio_b_bruto_r_kwh:.6f} * "
            f"{detalhes['fio_b_percentual_transicao'] * 100:.2f}%)) "
            f"/ (1 - {detalhes['icms_compensacao_percent']:.2f}%) "
            f"/ (1 - {pis_percent + cofins_percent:.2f}%)) = "
            f"{detalhes['fio_b_final_r_kwh']:.6f} R$/kWh"
        )
        return detalhes

    def _cached_rollover_context(self) -> dict[str, float]:
        """Retorna contexto tarifario atual para rollover de ciclo sem nova coleta."""

        if self.data is None:
            return {
                "tarifa_convencional_final_r_kwh": 0.0,
                "fio_b_final_r_kwh": 0.0,
                "valor_disponibilidade": 0.0,
            }
        tarifa_conv = float(self.data.valores.get("tarifa_convencional_final_r_kwh", 0.0) or 0.0)
        fio_b_final = float(self.data.valores.get("fio_b_final_r_kwh", 0.0) or 0.0)
        valor_disponibilidade = calcular_valor_disponibilidade(
            tipo_fornecimento=str(
                self._effective_value(CONF_TIPO_FORNECIMENTO, FORNECIMENTO_MONOFASICO)
            ),
            tarifa_convencional_final_r_kwh=tarifa_conv,
        )
        disponibilidade_kwh = disponibilidade_minima_kwh(
            str(self._effective_value(CONF_TIPO_FORNECIMENTO, FORNECIMENTO_MONOFASICO))
        )
        return {
            "tarifa_convencional_final_r_kwh": tarifa_conv,
            "fio_b_final_r_kwh": fio_b_final,
            "valor_disponibilidade": valor_disponibilidade,
            "disponibilidade_kwh": disponibilidade_kwh,
        }

    def _finalize_mensal_rollovers(
        self,
        consumo_rollovers: dict[str, list[tuple[str, float]]],
        geracao_rollovers: dict[str, list[tuple[str, float]]],
        injecao_rollovers: dict[str, list[tuple[str, float]]],
        tariff_context: dict[str, float],
    ) -> None:
        """Fecha ciclos mensais anteriores e atualiza o ledger de creditos."""

        consumo_mensal = dict(consumo_rollovers.get(QUEBRA_MENSAL, []))
        geracao_mensal = dict(injecao_rollovers.get(QUEBRA_MENSAL, []))
        cycle_keys = sorted(set(consumo_mensal) | set(geracao_mensal))
        if not cycle_keys:
            return

        saldo_creditos = total_credits_kwh(self._creditos_ledger)
        for cycle_key in cycle_keys:
            scee = calcular_scee_creditos_prioritarios(
                consumo_kwh=consumo_mensal.get(cycle_key, 0.0),
                geracao_kwh=geracao_mensal.get(cycle_key, 0.0),
                credito_entrada_kwh=saldo_creditos,
                tarifa_convencional_final_r_kwh=float(
                    tariff_context.get("tarifa_convencional_final_r_kwh", 0.0)
                ),
                fio_b_final_r_kwh=float(tariff_context.get("fio_b_final_r_kwh", 0.0)),
                valor_disponibilidade=float(tariff_context.get("valor_disponibilidade", 0.0)),
                disponibilidade_kwh=float(tariff_context.get("disponibilidade_kwh", 0.0)),
            )
            if scee["credito_consumido_kwh"] > 0:
                self._creditos_ledger, _consumido = consume_credits_oldest_first(
                    entries=self._creditos_ledger,
                    consumo_kwh=scee["credito_consumido_kwh"],
                )
            competencia = competencia_from_cycle_key(cycle_key)
            if competencia and scee["credito_gerado_kwh"] > 0:
                self._creditos_ledger = add_credit_entry(
                    entries=self._creditos_ledger,
                    competencia=competencia,
                    kwh=scee["credito_gerado_kwh"],
                )
            saldo_creditos = total_credits_kwh(self._creditos_ledger)

    def _process_energy_states(
        self,
        now: datetime,
        consumo_total_kwh: float | None,
        geracao_total_kwh: float | None,
        injecao_total_kwh: float | None,
        reading_day: int,
        tariff_context: dict[str, float],
    ) -> tuple[
        dict[str, float],
        dict[str, float],
        dict[str, float],
        dict[str, dict[str, float]],
    ]:
        """Atualiza estados incrementais de consumo/geracao/injecao e Tarifa Branca."""

        schedule, holidays, _metadata = self._resolve_tarifa_branca_context(
            now,
            self._last_consumo_timestamp or now,
            self._last_geracao_timestamp or now,
        )

        consumo_delta = None
        consumo_rollovers: dict[str, list[tuple[str, float]]] = {}
        if consumo_total_kwh is None:
            consumo_periodos = self._current_period_valores(self._consumo_period_state)
            consumo_tarifa_branca = self._current_posto_period_valores(
                self._consumo_tarifa_branca_state
            )
        else:
            consumo_delta = self._prepare_delta_context(
                consumo_total_kwh,
                now,
                self._last_consumo_total_kwh,
                self._last_consumo_timestamp,
            )
            consumo_periodos, consumo_rollovers = self._apply_scalar_delta_context(
                self._consumo_period_state,
                now,
                reading_day,
                consumo_delta,
            )
            (
                consumo_tarifa_branca,
                _tarifa_rollovers,
            ) = self._apply_tarifa_branca_delta_context(
                self._consumo_tarifa_branca_state,
                now,
                reading_day,
                consumo_delta,
                schedule,
                holidays,
            )

        geracao_delta = None
        geracao_rollovers: dict[str, list[tuple[str, float]]] = {}
        if geracao_total_kwh is None:
            geracao_periodos = self._current_period_valores(self._geracao_period_state)
        else:
            geracao_delta = self._prepare_delta_context(
                geracao_total_kwh,
                now,
                self._last_geracao_total_kwh,
                self._last_geracao_timestamp,
            )
            geracao_periodos, geracao_rollovers = self._apply_scalar_delta_context(
                self._geracao_period_state,
                now,
                reading_day,
                geracao_delta,
            )

        injecao_delta = None
        injecao_rollovers: dict[str, list[tuple[str, float]]] = {}
        if injecao_total_kwh is None:
            injecao_periodos = self._current_period_valores(self._injecao_period_state)
        else:
            injecao_delta = self._prepare_delta_context(
                injecao_total_kwh,
                now,
                self._last_injecao_total_kwh,
                self._last_injecao_timestamp,
            )
            injecao_periodos, injecao_rollovers = self._apply_scalar_delta_context(
                self._injecao_period_state,
                now,
                reading_day,
                injecao_delta,
            )

        if consumo_delta is not None and consumo_delta.get("reset_detected"):
            self._consumo_reset_detectado += 1
        if geracao_delta is not None and geracao_delta.get("reset_detected"):
            self._geracao_reset_detectado += 1
        if injecao_delta is not None and injecao_delta.get("reset_detected"):
            self._injecao_reset_detectado += 1

        self._finalize_mensal_rollovers(
            consumo_rollovers=consumo_rollovers,
            geracao_rollovers=geracao_rollovers,
            injecao_rollovers=(
                injecao_rollovers
                if self._effective_value(CONF_ENTIDADE_INJECAO)
                else geracao_rollovers
            ),
            tariff_context=tariff_context,
        )

        if consumo_total_kwh is not None:
            self._last_consumo_total_kwh = consumo_total_kwh
            self._last_consumo_timestamp = now
        if geracao_total_kwh is not None:
            self._last_geracao_total_kwh = geracao_total_kwh
            self._last_geracao_timestamp = now
        if injecao_total_kwh is not None:
            self._last_injecao_total_kwh = injecao_total_kwh
            self._last_injecao_timestamp = now
        current_mensal_key = self._consumo_period_state[QUEBRA_MENSAL]["key"]
        if current_mensal_key is not None:
            self._ultimo_ciclo_mensal = str(current_mensal_key)
        return consumo_periodos, geracao_periodos, injecao_periodos, consumo_tarifa_branca

    def _apply_dynamic_valores_to_snapshot(
        self,
        valores: dict[str, float | str | bool | None],
        quebras_habilitadas: list[str],
        consumo_periodos: dict[str, float],
        geracao_periodos: dict[str, float],
        injecao_periodos: dict[str, float],
        consumo_tarifa_branca: dict[str, dict[str, float]],
        possui_geracao: bool,
        possui_injecao: bool,
        geracao_total_kwh: float | None,
        injecao_total_kwh: float | None,
        tipo_fornecimento: str,
    ) -> None:
        """Atualiza campos derivados do snapshot a partir dos acumuladores correntes."""

        tarifa_conv_final = float(valores.get("tarifa_convencional_final_r_kwh", 0.0) or 0.0)
        adicional_bandeira = float(valores.get("adicional_bandeira_r_kwh", 0.0) or 0.0)
        fio_b_final = float(valores.get("fio_b_final_r_kwh", 0.0) or 0.0)
        valor_disponibilidade = calcular_valor_disponibilidade(
            tipo_fornecimento=tipo_fornecimento,
            tarifa_convencional_final_r_kwh=tarifa_conv_final,
        )
        disponibilidade_kwh = disponibilidade_minima_kwh(tipo_fornecimento)
        saldo_creditos_disponiveis = total_credits_kwh(self._creditos_ledger)

        valores["indicador_taxa_minima"] = consumo_periodos[QUEBRA_MENSAL] < disponibilidade_kwh
        valores["kwh_adicionados_disponibilidade"] = max(
            disponibilidade_kwh - consumo_periodos[QUEBRA_MENSAL],
            0.0,
        )
        valores["saldo_creditos_mes_anterior_kwh"] = saldo_creditos_disponiveis
        valores["previsao_creditos_gerados_kwh"] = 0.0
        valores["auto_consumo_kwh"] = 0.0
        valores["auto_consumo_reais"] = 0.0

        tarifa_final_por_posto = {
            "fora_ponta": float(valores.get("tarifa_branca_fora_ponta_final_r_kwh", 0.0) or 0.0),
            "intermediario": float(
                valores.get("tarifa_branca_intermediario_final_r_kwh", 0.0) or 0.0
            ),
            "ponta": float(valores.get("tarifa_branca_ponta_final_r_kwh", 0.0) or 0.0),
        }

        for period in QUEBRAS_VALIDAS:
            dynamic_keys = (
                f"valor_conta_consumo_regular_{period}_r",
                f"valor_conta_tarifa_branca_{period}_r",
                f"valor_conta_com_geracao_{period}_r",
                f"valor_fio_b_compensada_{period}_r",
                f"auto_consumo_{period}_kwh",
                f"auto_consumo_{period}_reais",
                f"valor_conta_consumo_regular_sem_disponibilidade_{period}_r",
                f"valor_conta_tarifa_branca_sem_disponibilidade_{period}_r",
                f"valor_conta_com_geracao_sem_disponibilidade_{period}_r",
            )
            for dynamic_key in dynamic_keys:
                valores.pop(dynamic_key, None)

            if period not in quebras_habilitadas:
                continue

            consumo_kwh_periodo = consumo_periodos[period]
            valor_regular_sem_disponibilidade = calcular_valor_conta_regular(
                kwh_periodo=consumo_kwh_periodo,
                tarifa_convencional_final_r_kwh=tarifa_conv_final,
                adicional_bandeira_r_kwh=adicional_bandeira,
            )
            valores[f"valor_conta_consumo_regular_{period}_r"] = (
                max(valor_disponibilidade, valor_regular_sem_disponibilidade)
                if period == QUEBRA_MENSAL
                else valor_regular_sem_disponibilidade
            )
            if period == QUEBRA_MENSAL:
                valores[f"valor_conta_consumo_regular_sem_disponibilidade_{period}_r"] = (
                    valor_regular_sem_disponibilidade
                )

            valor_tarifa_branca_sem_disponibilidade = calcular_valor_conta_tarifa_branca(
                consumo_por_posto_kwh=consumo_tarifa_branca[period],
                tarifa_final_por_posto_r_kwh=tarifa_final_por_posto,
                adicional_bandeira_r_kwh=adicional_bandeira,
            )
            valores[f"valor_conta_tarifa_branca_{period}_r"] = (
                max(valor_disponibilidade, valor_tarifa_branca_sem_disponibilidade)
                if period == QUEBRA_MENSAL
                else valor_tarifa_branca_sem_disponibilidade
            )
            if period == QUEBRA_MENSAL:
                valores[f"valor_conta_tarifa_branca_sem_disponibilidade_{period}_r"] = (
                    valor_tarifa_branca_sem_disponibilidade
                )

            if possui_geracao or possui_injecao:
                credito_entrada = saldo_creditos_disponiveis if period == QUEBRA_MENSAL else 0.0
                injecao_kwh_periodo = (
                    injecao_periodos[period] if possui_injecao else geracao_periodos[period]
                )
                scee = calcular_scee_creditos_prioritarios(
                    consumo_kwh=consumo_kwh_periodo,
                    geracao_kwh=injecao_kwh_periodo,
                    credito_entrada_kwh=credito_entrada,
                    tarifa_convencional_final_r_kwh=tarifa_conv_final,
                    fio_b_final_r_kwh=fio_b_final,
                    valor_disponibilidade=(
                        valor_disponibilidade if period == QUEBRA_MENSAL else 0.0
                    ),
                    disponibilidade_kwh=(disponibilidade_kwh if period == QUEBRA_MENSAL else 0.0),
                )
                valores[f"valor_conta_com_geracao_{period}_r"] = scee["valor_consumo_faturado"]
                valores[f"valor_fio_b_compensada_{period}_r"] = scee["valor_fio_b_compensada"]
                if possui_injecao:
                    auto_consumo_periodo_kwh = calcular_auto_consumo_kwh(
                        gerado_kwh=geracao_periodos[period],
                        injetado_kwh=injecao_periodos[period],
                    )
                else:
                    auto_consumo_periodo_kwh = calcular_auto_consumo_kwh(
                        gerado_kwh=geracao_periodos[period],
                        injetado_kwh=scee["credito_gerado_energia_kwh"],
                    )
                valores[f"auto_consumo_{period}_kwh"] = auto_consumo_periodo_kwh
                valores[f"auto_consumo_{period}_reais"] = (
                    auto_consumo_periodo_kwh * tarifa_conv_final
                )

                if period == QUEBRA_MENSAL:
                    valores[f"valor_conta_com_geracao_sem_disponibilidade_{period}_r"] = scee[
                        "valor_consumo_scee"
                    ]
                    self._credito_consumido_estimado_atual_kwh = scee["credito_consumido_kwh"]
                    self._credito_estimado_atual_kwh = scee["credito_gerado_kwh"]
                    valores["previsao_creditos_gerados_kwh"] = max(
                        credito_entrada
                        - scee["credito_consumido_kwh"]
                        + scee["credito_gerado_kwh"],
                        0.0,
                    )
                    if possui_injecao:
                        valores["auto_consumo_kwh"] = calcular_auto_consumo_kwh(
                            gerado_kwh=float(geracao_total_kwh or 0.0),
                            injetado_kwh=float(injecao_total_kwh or 0.0),
                        )
                    else:
                        valores["auto_consumo_kwh"] = auto_consumo_periodo_kwh
                    valores["auto_consumo_reais"] = (
                        float(valores["auto_consumo_kwh"]) * tarifa_conv_final
                    )
            elif period == QUEBRA_MENSAL:
                self._credito_consumido_estimado_atual_kwh = 0.0
                self._credito_estimado_atual_kwh = 0.0

        if possui_injecao:
            valores["auto_consumo_kwh"] = calcular_auto_consumo_kwh(
                gerado_kwh=float(geracao_total_kwh or 0.0),
                injetado_kwh=float(injecao_total_kwh or 0.0),
            )
            valores["auto_consumo_reais"] = float(valores["auto_consumo_kwh"]) * tarifa_conv_final

    def _update_dynamic_diagnosticos(self, now: datetime) -> None:
        """Atualiza diagnosticos dependentes dos acumuladores correntes."""

        if self.data is None:
            return

        schedule, holidays, schedule_metadata = self._resolve_tarifa_branca_context(now)
        self.data.diagnosticos.update(
            {
                "consumo_reset_detectado": self._consumo_reset_detectado,
                "geracao_reset_detectado": self._geracao_reset_detectado,
                "injecao_reset_detectado": self._injecao_reset_detectado,
                "consumo_mensal_kwh_apurado": float(
                    self._consumo_period_state[QUEBRA_MENSAL]["kwh"]
                ),
                "geracao_mensal_kwh_apurado": float(
                    self._geracao_period_state[QUEBRA_MENSAL]["kwh"]
                ),
                "injecao_mensal_kwh_apurado": float(
                    self._injecao_period_state[QUEBRA_MENSAL]["kwh"]
                ),
                "estimativa_tarifa_branca_sem_posto_real": self._tarifa_branca_low_confidence,
                "tarifa_branca_schedule_source": self._tarifa_branca_schedule_source,
                "tarifa_branca_schedule_windows": schedule_metadata["windows"],
                "tarifa_branca_invalid_extra_holidays": self._tarifa_branca_invalid_extra_holidays,
                "tarifa_branca_interval_seconds": self._tarifa_branca_last_interval_seconds,
                "tarifa_branca_segment_count": self._tarifa_branca_last_segment_count,
                "tarifa_branca_low_confidence": self._tarifa_branca_low_confidence,
                "tarifa_branca_posto_atual": resolve_tarifa_branca_posto(
                    now,
                    schedule,
                    holidays,
                ),
                "saldo_creditos_disponiveis_kwh": total_credits_kwh(self._creditos_ledger),
                "credito_consumido_estimado_atual_kwh": self._credito_consumido_estimado_atual_kwh,
                "credito_gerado_estimado_atual_kwh": self._credito_estimado_atual_kwh,
                "ledger_creditos": serialize_entries(self._creditos_ledger),
            }
        )

    async def _async_update_data(self) -> ResultadoCalculo:
        """Executa ciclo de coleta e retorna snapshot final dos sensores."""

        await self.async_ensure_state_loaded()

        now = datetime.now().astimezone()
        referencia = now.date()

        concessionaria = self._effective_value(CONF_CONCESSIONARIA)
        prioridade = self._effective_value(CONF_METODO_ANEEL, METODO_ANEEL_PADRAO)
        if not isinstance(concessionaria, str) or not concessionaria.strip():
            raise UpdateFailed("Concessionaria nao configurada.")

        entidade_consumo = self._effective_value(CONF_ENTIDADE_CONSUMO)
        geracao_entity = self._effective_value(CONF_ENTIDADE_GERACAO)
        injecao_entity = self._effective_value(CONF_ENTIDADE_INJECAO)
        tipo_fornecimento = self._effective_value(CONF_TIPO_FORNECIMENTO, FORNECIMENTO_MONOFASICO)
        possuia_historico_consumo = self._last_consumo_timestamp is not None

        try:
            tarifas_task = self._aneel_client.fetch_tarifas(
                concessionaria=concessionaria,
                priority_method=prioridade,
                reference_date=referencia,
            )
            fio_b_task = self._aneel_client.fetch_fio_b(
                concessionaria=concessionaria,
                priority_method=prioridade,
                reference_date=referencia,
            )
            bandeira_task = self._aneel_client.fetch_bandeira(
                priority_method=prioridade,
                reference_date=referencia,
            )
            tributos_task = extract_tributos(
                session=async_get_clientsession(self.hass),
                concessionaria=concessionaria,
            )

            (
                tarifas_result,
                fio_b_result,
                bandeira_result,
                tributos_result,
            ) = await asyncio.gather(
                tarifas_task,
                fio_b_task,
                bandeira_task,
                tributos_task,
            )
        except (
            AneelClientError,
            TimeoutError,
            ValueError,
            RuntimeError,
            Exception,
        ) as err:
            retry_interval = self._failure_retry_interval(has_snapshot=self.data is not None)
            retry_at = now + retry_interval
            if self.data is not None:
                _LOGGER.warning(
                    (
                        "Coleta de tarifas falhou para %s; mantendo ultimo snapshot "
                        "valido nos sensores. Proxima tentativa automatica prevista "
                        "para %s (intervalo=%s). Erro: %s"
                    ),
                    self.config_entry.entry_id,
                    retry_at.isoformat(),
                    retry_interval,
                    err,
                )
                diagnosticos = dict(self.data.diagnosticos)
                diagnosticos["mensagem_erro"] = str(err)
                diagnosticos["ultima_falha"] = now.isoformat()
                diagnosticos["usou_ultimo_valor_valido"] = True
                return ResultadoCalculo(
                    atualizado_em=now,
                    concessionaria=self.data.concessionaria,
                    valores=self.data.valores,
                    coletas_por_chave=self.data.coletas_por_chave,
                    diagnosticos=diagnosticos,
                )
            _LOGGER.error(
                (
                    "Coleta inicial de tarifas falhou para %s e nao ha snapshot "
                    "valido em cache para restaurar sensores. Proxima tentativa "
                    "automatica prevista para %s (intervalo_temporario=%s). Erro: %s"
                ),
                self.config_entry.entry_id,
                retry_at.isoformat(),
                retry_interval,
                err,
            )
            raise UpdateFailed(f"Falha na coleta inicial: {err}") from err

        self._restore_regular_update_interval()

        tarifas_data, tarifas_meta = tarifas_result
        fio_b_data, fio_b_meta = fio_b_result
        bandeira_data, bandeira_meta = bandeira_result
        tributos_data, tributos_meta = tributos_result

        consumo_total_kwh = self._read_entity_kwh(entidade_consumo)
        geracao_total_kwh = self._read_entity_kwh(geracao_entity)
        injecao_total_kwh = self._read_entity_kwh(injecao_entity)

        quebras_habilitadas = self._effective_breakdowns()
        reading_day = int(self._effective_value(CONF_DIA_LEITURA, DIA_LEITURA_PADRAO))
        (
            consumo_periodos,
            geracao_periodos,
            injecao_periodos,
            consumo_tarifa_branca,
        ) = self._process_energy_states(
            now=now,
            consumo_total_kwh=consumo_total_kwh,
            geracao_total_kwh=geracao_total_kwh,
            injecao_total_kwh=injecao_total_kwh,
            reading_day=reading_day,
            tariff_context=self._cached_rollover_context(),
        )

        consumo_mensal_kwh = consumo_periodos[QUEBRA_MENSAL]
        disponibilidade_kwh = disponibilidade_minima_kwh(tipo_fornecimento)
        icms_consumo_faturavel_kwh = self._icms_consumo_faturavel_kwh(
            consumo_mensal_kwh=consumo_mensal_kwh,
            disponibilidade_kwh=disponibilidade_kwh,
        )
        if possuia_historico_consumo or consumo_mensal_kwh > 0 or disponibilidade_kwh > 0:
            icms_aplicado_percent, icms_source = resolve_icms_percent(
                concessionaria=concessionaria,
                consumo_mensal_kwh=icms_consumo_faturavel_kwh,
                fallback_icms_percent=tributos_data.icms_percent,
            )
        else:
            icms_aplicado_percent = tributos_data.icms_percent
            icms_source = "fallback_bootstrap_sem_historico"

        tarifa_conv_bruta, tarifa_conv_final = calcular_tarifa_convencional(
            te_convencional_r_kwh=tarifas_data["convencional"]["te_r_kwh"],
            tusd_convencional_r_kwh=tarifas_data["convencional"]["tusd_r_kwh"],
            pis_percent=tributos_data.pis_percent,
            cofins_percent=tributos_data.cofins_percent,
            icms_percent=icms_aplicado_percent,
        )

        tarifa_branca = calcular_tarifa_branca_por_posto(
            te_por_posto_r_kwh={
                "fora_ponta": tarifas_data["branca"]["fora_ponta"]["te_r_kwh"],
                "intermediario": tarifas_data["branca"]["intermediario"]["te_r_kwh"],
                "ponta": tarifas_data["branca"]["ponta"]["te_r_kwh"],
            },
            tusd_por_posto_r_kwh={
                "fora_ponta": tarifas_data["branca"]["fora_ponta"]["tusd_r_kwh"],
                "intermediario": tarifas_data["branca"]["intermediario"]["tusd_r_kwh"],
                "ponta": tarifas_data["branca"]["ponta"]["tusd_r_kwh"],
            },
            pis_percent=tributos_data.pis_percent,
            cofins_percent=tributos_data.cofins_percent,
            icms_percent=icms_aplicado_percent,
        )

        fio_b_bruto = fio_b_data["convencional_bruto_r_kwh"]
        fio_b_effective_valores = self._fio_b_effective_valores(
            fio_b_bruto_r_kwh=fio_b_bruto,
            tusd_convencional_r_kwh=tarifas_data["convencional"]["tusd_r_kwh"],
            icms_consumo_percent=icms_aplicado_percent,
            icms_consumo_source=icms_source,
            reference_date=referencia,
            pis_percent=tributos_data.pis_percent,
            cofins_percent=tributos_data.cofins_percent,
        )
        ciclo_mensal_atual = self._period_key(QUEBRA_MENSAL, now, reading_day)
        competencia_atual = competencia_from_cycle_key(ciclo_mensal_atual)
        if competencia_atual:
            self._creditos_ledger = purge_expired_credits(
                entries=self._creditos_ledger,
                reference_competencia=competencia_atual,
                validade_meses=60,
            )

        saldo_creditos_disponiveis = total_credits_kwh(self._creditos_ledger)

        valores: dict[str, float | str | bool | None] = {
            "te_convencional_r_kwh": tarifas_data["convencional"]["te_r_kwh"],
            "tusd_convencional_r_kwh": tarifas_data["convencional"]["tusd_r_kwh"],
            "tarifa_convencional_bruta_r_kwh": tarifa_conv_bruta,
            "tarifa_convencional_final_r_kwh": tarifa_conv_final,
            "te_branca_fora_ponta_r_kwh": tarifa_branca["fora_ponta"]["te_r_kwh"],
            "tusd_branca_fora_ponta_r_kwh": tarifa_branca["fora_ponta"]["tusd_r_kwh"],
            "tarifa_branca_fora_ponta_bruta_r_kwh": tarifa_branca["fora_ponta"][
                "tarifa_bruta_r_kwh"
            ],
            "tarifa_branca_fora_ponta_final_r_kwh": tarifa_branca["fora_ponta"][
                "tarifa_final_r_kwh"
            ],
            "te_branca_intermediario_r_kwh": tarifa_branca["intermediario"]["te_r_kwh"],
            "tusd_branca_intermediario_r_kwh": tarifa_branca["intermediario"]["tusd_r_kwh"],
            "tarifa_branca_intermediario_bruta_r_kwh": tarifa_branca["intermediario"][
                "tarifa_bruta_r_kwh"
            ],
            "tarifa_branca_intermediario_final_r_kwh": tarifa_branca["intermediario"][
                "tarifa_final_r_kwh"
            ],
            "te_branca_ponta_r_kwh": tarifa_branca["ponta"]["te_r_kwh"],
            "tusd_branca_ponta_r_kwh": tarifa_branca["ponta"]["tusd_r_kwh"],
            "tarifa_branca_ponta_bruta_r_kwh": tarifa_branca["ponta"]["tarifa_bruta_r_kwh"],
            "tarifa_branca_ponta_final_r_kwh": tarifa_branca["ponta"]["tarifa_final_r_kwh"],
            "fio_b_bruto_r_kwh": fio_b_bruto,
            **fio_b_effective_valores,
            "pis_percent": tributos_data.pis_percent,
            "cofins_percent": tributos_data.cofins_percent,
            "icms_percent": icms_aplicado_percent,
            **self._icms_explanation_valores(
                concessionaria=concessionaria,
                consumo_mensal_kwh=consumo_mensal_kwh,
                consumo_faturavel_kwh=icms_consumo_faturavel_kwh,
                disponibilidade_minima_kwh=disponibilidade_kwh,
                fallback_icms_percent=tributos_data.icms_percent,
                icms_aplicado_percent=icms_aplicado_percent,
                icms_source=icms_source,
            ),
            "bandeira_vigente": bandeira_data["bandeira"],
            "adicional_bandeira_r_kwh": bandeira_data["adicional_r_kwh"],
            "indicador_taxa_minima": consumo_periodos[QUEBRA_MENSAL] < disponibilidade_kwh,
            "kwh_adicionados_disponibilidade": max(
                disponibilidade_kwh - consumo_periodos[QUEBRA_MENSAL], 0.0
            ),
            "saldo_creditos_mes_anterior_kwh": saldo_creditos_disponiveis,
            "previsao_creditos_gerados_kwh": 0.0,
            "auto_consumo_kwh": 0.0,
            "auto_consumo_reais": 0.0,
        }
        self._apply_dynamic_valores_to_snapshot(
            valores=valores,
            quebras_habilitadas=quebras_habilitadas,
            consumo_periodos=consumo_periodos,
            geracao_periodos=geracao_periodos,
            injecao_periodos=injecao_periodos,
            consumo_tarifa_branca=consumo_tarifa_branca,
            possui_geracao=bool(geracao_entity),
            possui_injecao=bool(injecao_entity),
            geracao_total_kwh=(
                geracao_total_kwh if geracao_total_kwh is not None else self._last_geracao_total_kwh
            ),
            injecao_total_kwh=(
                injecao_total_kwh if injecao_total_kwh is not None else self._last_injecao_total_kwh
            ),
            tipo_fornecimento=tipo_fornecimento,
        )

        coletas_por_chave = self._build_coletas_por_chave(
            valores=valores,
            tarifas_meta=tarifas_meta,
            fio_b_meta=fio_b_meta,
            bandeira_meta=bandeira_meta,
            tributos_meta=tributos_meta,
        )

        diagnosticos = {
            "concessionaria": concessionaria,
            "referencia": referencia.isoformat(),
            "quebras_habilitadas": quebras_habilitadas,
            "prioridade_aneel": prioridade,
            "entidade_consumo": entidade_consumo,
            "geracao_entity": geracao_entity,
            "injecao_entity": injecao_entity,
            "consumo_mensal_kwh_apurado": consumo_mensal_kwh,
            "consumo_bootstrap_sem_historico": not possuia_historico_consumo,
            "mensagem_erro": None,
            "estimativa_tarifa_branca_sem_posto_real": self._tarifa_branca_low_confidence,
            "competencia_bandeira": bandeira_data["competencia"],
            "tributos_competencia": tributos_data.competencia,
            "icms_percent_base_fonte": tributos_data.icms_percent,
            "icms_percent_aplicado": icms_aplicado_percent,
            "icms_source": icms_source,
            "tarifas_selection_debug": tarifas_data.get("selection_debug"),
            "fio_b_selection_debug": fio_b_data.get("selection_debug"),
            "saldo_creditos_disponiveis_kwh": saldo_creditos_disponiveis,
            "credito_consumido_estimado_atual_kwh": self._credito_consumido_estimado_atual_kwh,
            "credito_gerado_estimado_atual_kwh": self._credito_estimado_atual_kwh,
            "ledger_creditos": serialize_entries(self._creditos_ledger),
        }

        snapshot = ResultadoCalculo(
            atualizado_em=now,
            concessionaria=concessionaria,
            valores=valores,
            coletas_por_chave=coletas_por_chave,
            diagnosticos=diagnosticos,
        )
        self.data = snapshot
        self._update_dynamic_diagnosticos(now)
        self._schedule_state_save()
        return snapshot

    def _effective_update_hours(self) -> int:
        """Retorna frequencia efetiva da coleta em horas."""

        value = self._effective_value(CONF_HORAS_ATUALIZACAO, HORAS_ATUALIZACAO_PADRAO)
        try:
            return max(int(value), 1)
        except (TypeError, ValueError):
            return HORAS_ATUALIZACAO_PADRAO

    def _failure_retry_interval(self, *, has_snapshot: bool) -> timedelta:
        """Ajusta a proxima tentativa apos falha externa."""

        regular_interval = self._regular_update_interval()
        if has_snapshot:
            self.update_interval = regular_interval
            return regular_interval

        retry_interval = min(regular_interval, _INITIAL_FAILURE_RETRY_INTERVAL)
        self.update_interval = retry_interval
        return retry_interval

    def _restore_regular_update_interval(self) -> None:
        """Restaura a cadencia configurada apos uma coleta bem-sucedida."""

        self.update_interval = self._regular_update_interval()

    def _regular_update_interval(self) -> timedelta:
        """Retorna a cadencia configurada pelo usuario."""

        configured = getattr(self, "_configured_update_interval", None)
        if isinstance(configured, timedelta):
            return configured
        return timedelta(hours=self._effective_update_hours())

    def _effective_breakdowns(self) -> list[str]:
        """Retorna lista valida de quebras de calculo."""

        raw = self._effective_value(CONF_QUEBRAS_CALCULO, QUEBRAS_PADRAO)
        if not isinstance(raw, list):
            return QUEBRAS_PADRAO
        parsed = [period for period in raw if period in QUEBRAS_VALIDAS]
        return parsed or QUEBRAS_PADRAO

    def _effective_value(self, key: str, default: Any = None) -> Any:
        """Le valor preferindo options e depois data."""

        if key in self.entry.options:
            return self.entry.options[key]
        if key in self.entry.data:
            return self.entry.data[key]
        return default

    def _read_entity_kwh(self, entity_id: Any) -> float | None:
        """Le estado numérico de entidade configurada."""

        if not isinstance(entity_id, str) or not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        if state is None:
            return None
        raw = state.state
        if raw in ("unknown", "unavailable", ""):
            return None
        try:
            return max(float(raw), 0.0)
        except (TypeError, ValueError):
            return None

    def _update_period_accumulator(
        self,
        current_total_kwh: float,
        period_state: dict[str, dict[str, str | float | None]],
        reading_day: int,
        now: datetime,
        last_total_attr: str,
    ) -> dict[str, float]:
        """Atualiza acumuladores de periodo a partir de entidade acumulada."""

        last_total = getattr(self, last_total_attr)
        if last_total is None:
            delta = 0.0
        else:
            delta = current_total_kwh - float(last_total)
            if delta < 0:
                delta = current_total_kwh
        setattr(self, last_total_attr, current_total_kwh)

        valores: dict[str, float] = {}
        for period in QUEBRAS_VALIDAS:
            current_key = self._period_key(period, now, reading_day)
            if period_state[period]["key"] != current_key:
                period_state[period]["key"] = current_key
                period_state[period]["kwh"] = 0.0
            period_state[period]["kwh"] = float(period_state[period]["kwh"]) + max(delta, 0.0)
            valores[period] = float(period_state[period]["kwh"])
        return valores

    @staticmethod
    def _period_key(period: str, now: datetime, reading_day: int) -> str:
        """Gera chave de ciclo para cada quebra."""

        if period == QUEBRA_DIARIA:
            return now.strftime("%Y-%m-%d")
        if period == QUEBRA_SEMANAL:
            iso = now.isocalendar()
            return f"{iso.year}-W{iso.week:02d}"

        effective_day = min(max(int(reading_day), 1), 28)
        year = now.year
        month = now.month
        if now.day < effective_day:
            month -= 1
            if month == 0:
                month = 12
                year -= 1
        return f"{year:04d}-{month:02d}-D{effective_day:02d}"

    @staticmethod
    def _build_coletas_por_chave(
        valores: dict[str, float | str | bool | None],
        tarifas_meta: MetadadosColeta,
        fio_b_meta: MetadadosColeta,
        bandeira_meta: MetadadosColeta,
        tributos_meta: MetadadosColeta,
    ) -> dict[str, MetadadosColeta]:
        """Relaciona cada sensor ao metadado mais apropriado."""

        mapping: dict[str, MetadadosColeta] = {}
        for key in valores:
            if key.startswith(("te_", "tusd_", "tarifa_")):
                mapping[key] = tarifas_meta
            elif key.startswith("fio_b_"):
                mapping[key] = fio_b_meta
            elif key.startswith(("pis_", "cofins_", "icms_")):
                mapping[key] = tributos_meta
            elif key.startswith(("bandeira_", "adicional_bandeira_")):
                mapping[key] = bandeira_meta
            else:
                # Valores derivados utilizam metadado principal de tarifas.
                mapping[key] = tarifas_meta
        return mapping
