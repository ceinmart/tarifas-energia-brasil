"""Versao: 0.1.0
Criado em: 2026-04-22 21:41:36 -03:00
Criado por: Codex
Projeto/pasta: ha.ext.tarifas
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .aneel_client import AneelClient, AneelClientError
from .calculators import (
    calcular_fio_b_final,
    calcular_scee_creditos_prioritarios,
    calcular_tarifa_branca_por_posto,
    calcular_tarifa_convencional,
    calcular_valor_conta_regular,
    calcular_valor_disponibilidade,
    disponibilidade_minima_kwh,
)
from .const import (
    BREAKDOWN_DAILY,
    BREAKDOWN_MONTHLY,
    BREAKDOWN_WEEKLY,
    CONF_ANEEL_METHOD,
    CONF_BREAKDOWNS,
    CONF_CONCESSIONARIA,
    CONF_CONSUMPTION_ENTITY,
    CONF_GENERATION_ENTITY,
    CONF_READING_DAY,
    CONF_SUPPLY_TYPE,
    CONF_UPDATE_HOURS,
    DEFAULT_ANEEL_METHOD,
    DEFAULT_BREAKDOWNS,
    DEFAULT_READING_DAY,
    DEFAULT_UPDATE_HOURS,
    DOMAIN,
    SUPPLY_MONOPHASE,
    VALID_BREAKDOWNS,
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
from .icms_rules import resolve_icms_percent
from .models import CollectionMetadata, SnapshotCalculo
from .tributos import extract_tributos

_LOGGER = logging.getLogger(__name__)
_STATE_STORAGE_VERSION = 1


class TarifasEnergiaBrasilCoordinator(DataUpdateCoordinator[SnapshotCalculo]):
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
        self._consumo_period_state = self._new_period_state()
        self._geracao_period_state = self._new_period_state()

        self._creditos_ledger: list[CreditoEntry] = []
        self._credito_estimado_atual_kwh = 0.0
        self._credito_consumido_estimado_atual_kwh = 0.0
        self._ultimo_ciclo_mensal: str | None = None

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(hours=self._effective_update_hours()),
        )

    @staticmethod
    def _new_period_state() -> dict[str, dict[str, str | float | None]]:
        """Cria estrutura de estado para acumuladores por periodo."""

        return {
            BREAKDOWN_DAILY: {"key": None, "kwh": 0.0},
            BREAKDOWN_WEEKLY: {"key": None, "kwh": 0.0},
            BREAKDOWN_MONTHLY: {"key": None, "kwh": 0.0},
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

            loaded_consumo = payload.get("consumo_period_state")
            loaded_geracao = payload.get("geracao_period_state")
            if isinstance(loaded_consumo, dict):
                self._consumo_period_state = self._merge_period_state(loaded_consumo)
            if isinstance(loaded_geracao, dict):
                self._geracao_period_state = self._merge_period_state(loaded_geracao)

            self._ultimo_ciclo_mensal = self._as_str_or_none(
                payload.get("ultimo_ciclo_mensal")
            )
            self._credito_estimado_atual_kwh = max(
                self._as_float(payload.get("credito_estimado_atual_kwh"), 0.0),
                0.0,
            )
            self._credito_consumido_estimado_atual_kwh = max(
                self._as_float(payload.get("credito_consumido_estimado_atual_kwh"), 0.0),
                0.0,
            )
            self._creditos_ledger = deserialize_entries(payload.get("creditos_ledger"))
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
            "consumo_period_state": self._consumo_period_state,
            "geracao_period_state": self._geracao_period_state,
            "ultimo_ciclo_mensal": self._ultimo_ciclo_mensal,
            "credito_estimado_atual_kwh": self._credito_estimado_atual_kwh,
            "credito_consumido_estimado_atual_kwh": self._credito_consumido_estimado_atual_kwh,
            "creditos_ledger": serialize_entries(self._creditos_ledger),
        }

    @staticmethod
    def _merge_period_state(payload: dict[str, Any]) -> dict[str, dict[str, str | float | None]]:
        """Mescla payload persistido com estrutura padrao dos periodos."""

        merged = TarifasEnergiaBrasilCoordinator._new_period_state()
        for key in VALID_BREAKDOWNS:
            incoming = payload.get(key)
            if isinstance(incoming, dict):
                merged[key]["key"] = incoming.get("key")
                merged[key]["kwh"] = float(incoming.get("kwh", 0.0))
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

    async def _async_update_data(self) -> SnapshotCalculo:
        """Executa ciclo de coleta e retorna snapshot final dos sensores."""

        await self.async_ensure_state_loaded()

        now = datetime.now().astimezone()
        referencia = now.date()

        concessionaria = self._effective_value(CONF_CONCESSIONARIA)
        prioridade = self._effective_value(CONF_ANEEL_METHOD, DEFAULT_ANEEL_METHOD)
        if not isinstance(concessionaria, str) or not concessionaria.strip():
            raise UpdateFailed("Concessionaria nao configurada.")

        consumo_entity = self._effective_value(CONF_CONSUMPTION_ENTITY)
        geracao_entity = self._effective_value(CONF_GENERATION_ENTITY)
        tipo_fornecimento = self._effective_value(CONF_SUPPLY_TYPE, SUPPLY_MONOPHASE)

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
            if self.data is not None:
                diagnostics = dict(self.data.diagnostics)
                diagnostics["mensagem_erro"] = str(err)
                diagnostics["ultima_falha"] = now.isoformat()
                diagnostics["usou_ultimo_valor_valido"] = True
                return SnapshotCalculo(
                    updated_at=now,
                    concessionaria=self.data.concessionaria,
                    values=self.data.values,
                    collections_by_key=self.data.collections_by_key,
                    diagnostics=diagnostics,
                )
            raise UpdateFailed(f"Falha na coleta inicial: {err}") from err

        tarifas_data, tarifas_meta = tarifas_result
        fio_b_data, fio_b_meta = fio_b_result
        bandeira_data, bandeira_meta = bandeira_result
        tributos_data, tributos_meta = tributos_result

        consumo_total_kwh = self._read_entity_kwh(consumo_entity)
        geracao_total_kwh = self._read_entity_kwh(geracao_entity)

        enabled_breakdowns = self._effective_breakdowns()
        consumo_periodos = self._update_period_accumulator(
            current_total_kwh=consumo_total_kwh,
            period_state=self._consumo_period_state,
            reading_day=int(self._effective_value(CONF_READING_DAY, DEFAULT_READING_DAY)),
            now=now,
            last_total_attr="_last_consumo_total_kwh",
        )
        geracao_periodos = self._update_period_accumulator(
            current_total_kwh=geracao_total_kwh,
            period_state=self._geracao_period_state,
            reading_day=int(self._effective_value(CONF_READING_DAY, DEFAULT_READING_DAY)),
            now=now,
            last_total_attr="_last_geracao_total_kwh",
        )

        consumo_mensal_kwh = consumo_periodos[BREAKDOWN_MONTHLY]
        icms_aplicado_percent, icms_source = resolve_icms_percent(
            concessionaria=concessionaria,
            consumo_mensal_kwh=consumo_mensal_kwh,
            fallback_icms_percent=tributos_data.icms_percent,
        )

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
        fio_b_final = calcular_fio_b_final(
            fio_b_bruto_r_kwh=fio_b_bruto,
            ano=referencia.year,
            pis_percent=tributos_data.pis_percent,
            cofins_percent=tributos_data.cofins_percent,
            icms_percent=icms_aplicado_percent,
        )

        disponibilidade_kwh = disponibilidade_minima_kwh(tipo_fornecimento)
        valor_disponibilidade = calcular_valor_disponibilidade(
            tipo_fornecimento=tipo_fornecimento,
            tarifa_convencional_final_r_kwh=tarifa_conv_final,
        )

        ciclo_mensal_atual = self._period_key(
            BREAKDOWN_MONTHLY,
            now,
            int(self._effective_value(CONF_READING_DAY, DEFAULT_READING_DAY)),
        )
        competencia_atual = competencia_from_cycle_key(ciclo_mensal_atual)
        if self._ultimo_ciclo_mensal and ciclo_mensal_atual != self._ultimo_ciclo_mensal:
            competencia_anterior = competencia_from_cycle_key(self._ultimo_ciclo_mensal)
            if self._credito_consumido_estimado_atual_kwh > 0:
                self._creditos_ledger, _consumido = consume_credits_oldest_first(
                    entries=self._creditos_ledger,
                    consumo_kwh=self._credito_consumido_estimado_atual_kwh,
                )
            if competencia_anterior and self._credito_estimado_atual_kwh > 0:
                self._creditos_ledger = add_credit_entry(
                    entries=self._creditos_ledger,
                    competencia=competencia_anterior,
                    kwh=self._credito_estimado_atual_kwh,
                )
            self._credito_estimado_atual_kwh = 0.0
            self._credito_consumido_estimado_atual_kwh = 0.0
        self._ultimo_ciclo_mensal = ciclo_mensal_atual

        if competencia_atual:
            self._creditos_ledger = purge_expired_credits(
                entries=self._creditos_ledger,
                reference_competencia=competencia_atual,
                validade_meses=60,
            )

        saldo_creditos_disponiveis = total_credits_kwh(self._creditos_ledger)

        values: dict[str, float | str | bool | None] = {
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
            "tarifa_branca_ponta_bruta_r_kwh": tarifa_branca["ponta"][
                "tarifa_bruta_r_kwh"
            ],
            "tarifa_branca_ponta_final_r_kwh": tarifa_branca["ponta"][
                "tarifa_final_r_kwh"
            ],
            "fio_b_bruto_r_kwh": fio_b_bruto,
            "fio_b_final_r_kwh": fio_b_final,
            "pis_percent": tributos_data.pis_percent,
            "cofins_percent": tributos_data.cofins_percent,
            "icms_percent": icms_aplicado_percent,
            "bandeira_vigente": bandeira_data["bandeira"],
            "adicional_bandeira_r_kwh": bandeira_data["adicional_r_kwh"],
            "indicador_taxa_minima": consumo_periodos[BREAKDOWN_MONTHLY] < disponibilidade_kwh,
            "kwh_adicionados_disponibilidade": max(
                disponibilidade_kwh - consumo_periodos[BREAKDOWN_MONTHLY], 0.0
            ),
            "saldo_creditos_mes_anterior_kwh": saldo_creditos_disponiveis,
            "previsao_creditos_gerados_kwh": 0.0,
            "auto_consumo_kwh": 0.0,
            "auto_consumo_reais": 0.0,
        }

        for period in VALID_BREAKDOWNS:
            if period not in enabled_breakdowns:
                continue

            consumo_kwh_periodo = consumo_periodos[period]
            values[f"valor_conta_consumo_regular_{period}_r"] = calcular_valor_conta_regular(
                kwh_periodo=consumo_kwh_periodo,
                tarifa_convencional_final_r_kwh=tarifa_conv_final,
                adicional_bandeira_r_kwh=float(bandeira_data["adicional_r_kwh"]),
            )
            values[f"valor_conta_tarifa_branca_{period}_r"] = consumo_kwh_periodo * tarifa_branca[
                "fora_ponta"
            ]["tarifa_final_r_kwh"]

            if geracao_entity:
                credito_entrada = saldo_creditos_disponiveis if period == BREAKDOWN_MONTHLY else 0.0
                scee = calcular_scee_creditos_prioritarios(
                    consumo_kwh=consumo_kwh_periodo,
                    geracao_kwh=geracao_periodos[period],
                    credito_entrada_kwh=credito_entrada,
                    tarifa_convencional_final_r_kwh=tarifa_conv_final,
                    fio_b_final_r_kwh=fio_b_final,
                    valor_disponibilidade=valor_disponibilidade,
                )
                values[f"valor_conta_com_geracao_{period}_r"] = scee["valor_consumo_faturado"]
                values[f"valor_fio_b_compensada_{period}_r"] = scee["valor_fio_b_compensada"]

                if period == BREAKDOWN_MONTHLY:
                    self._credito_consumido_estimado_atual_kwh = scee["credito_consumido_kwh"]
                    self._credito_estimado_atual_kwh = scee["credito_gerado_kwh"]
                    values["previsao_creditos_gerados_kwh"] = max(
                        credito_entrada
                        - scee["credito_consumido_kwh"]
                        + scee["credito_gerado_kwh"],
                        0.0,
                    )
                    values["auto_consumo_kwh"] = min(consumo_kwh_periodo, geracao_periodos[period])
                    values["auto_consumo_reais"] = values["auto_consumo_kwh"] * tarifa_conv_final

        collections_by_key = self._build_collections_by_key(
            values=values,
            tarifas_meta=tarifas_meta,
            fio_b_meta=fio_b_meta,
            bandeira_meta=bandeira_meta,
            tributos_meta=tributos_meta,
        )

        diagnostics = {
            "concessionaria": concessionaria,
            "referencia": referencia.isoformat(),
            "enabled_breakdowns": enabled_breakdowns,
            "prioridade_aneel": prioridade,
            "consumo_entity": consumo_entity,
            "geracao_entity": geracao_entity,
            "mensagem_erro": None,
            "estimativa_tarifa_branca_sem_posto_real": True,
            "competencia_bandeira": bandeira_data["competencia"],
            "tributos_competencia": tributos_data.competencia,
            "icms_percent_base_fonte": tributos_data.icms_percent,
            "icms_percent_aplicado": icms_aplicado_percent,
            "icms_source": icms_source,
            "saldo_creditos_disponiveis_kwh": saldo_creditos_disponiveis,
            "credito_consumido_estimado_atual_kwh": self._credito_consumido_estimado_atual_kwh,
            "credito_gerado_estimado_atual_kwh": self._credito_estimado_atual_kwh,
            "ledger_creditos": serialize_entries(self._creditos_ledger),
        }

        self._schedule_state_save()

        return SnapshotCalculo(
            updated_at=now,
            concessionaria=concessionaria,
            values=values,
            collections_by_key=collections_by_key,
            diagnostics=diagnostics,
        )

    def _effective_update_hours(self) -> int:
        """Retorna frequencia efetiva da coleta em horas."""

        value = self._effective_value(CONF_UPDATE_HOURS, DEFAULT_UPDATE_HOURS)
        try:
            return max(int(value), 1)
        except (TypeError, ValueError):
            return DEFAULT_UPDATE_HOURS

    def _effective_breakdowns(self) -> list[str]:
        """Retorna lista valida de quebras de calculo."""

        raw = self._effective_value(CONF_BREAKDOWNS, DEFAULT_BREAKDOWNS)
        if not isinstance(raw, list):
            return DEFAULT_BREAKDOWNS
        parsed = [period for period in raw if period in VALID_BREAKDOWNS]
        return parsed or DEFAULT_BREAKDOWNS

    def _effective_value(self, key: str, default: Any = None) -> Any:
        """Le valor preferindo options e depois data."""

        if key in self.entry.options:
            return self.entry.options[key]
        if key in self.entry.data:
            return self.entry.data[key]
        return default

    def _read_entity_kwh(self, entity_id: Any) -> float:
        """Le estado numérico de entidade configurada."""

        if not isinstance(entity_id, str) or not entity_id:
            return 0.0
        state = self.hass.states.get(entity_id)
        if state is None:
            return 0.0
        raw = state.state
        if raw in ("unknown", "unavailable", ""):
            return 0.0
        try:
            return max(float(raw), 0.0)
        except (TypeError, ValueError):
            return 0.0

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

        values: dict[str, float] = {}
        for period in VALID_BREAKDOWNS:
            current_key = self._period_key(period, now, reading_day)
            if period_state[period]["key"] != current_key:
                period_state[period]["key"] = current_key
                period_state[period]["kwh"] = 0.0
            period_state[period]["kwh"] = float(period_state[period]["kwh"]) + max(delta, 0.0)
            values[period] = float(period_state[period]["kwh"])
        return values

    @staticmethod
    def _period_key(period: str, now: datetime, reading_day: int) -> str:
        """Gera chave de ciclo para cada quebra."""

        if period == BREAKDOWN_DAILY:
            return now.strftime("%Y-%m-%d")
        if period == BREAKDOWN_WEEKLY:
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
    def _build_collections_by_key(
        values: dict[str, float | str | bool | None],
        tarifas_meta: CollectionMetadata,
        fio_b_meta: CollectionMetadata,
        bandeira_meta: CollectionMetadata,
        tributos_meta: CollectionMetadata,
    ) -> dict[str, CollectionMetadata]:
        """Relaciona cada sensor ao metadado mais apropriado."""

        mapping: dict[str, CollectionMetadata] = {}
        for key in values:
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
