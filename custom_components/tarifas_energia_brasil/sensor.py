"""Versao: 0.1.0
Criado em: 2026-04-22 21:41:36 -03:00
Criado por: Codex
Projeto/pasta: ha.ext.tarifas
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import (
    BREAKDOWN_DAILY,
    BREAKDOWN_MONTHLY,
    BREAKDOWN_WEEKLY,
    CONF_BREAKDOWNS,
    CONF_CONCESSIONARIA,
    CONF_GENERATION_ENTITY,
    DEFAULT_BREAKDOWNS,
    DOMAIN,
)
from .coordinator import TarifasEnergiaBrasilCoordinator

UNIT_R_KWH = "R$/kWh"
UNIT_R = "R$"
UNIT_KWH = "kWh"


@dataclass(frozen=True, kw_only=True)
class TarifaSensorDescription(SensorEntityDescription):
    """Descricao de sensor baseado em chave do snapshot."""

    value_key: str


BASE_SENSOR_DESCRIPTIONS: tuple[TarifaSensorDescription, ...] = (
    TarifaSensorDescription(
        key="te_convencional_r_kwh",
        value_key="te_convencional_r_kwh",
        name="TE convencional",
        native_unit_of_measurement=UNIT_R_KWH,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    TarifaSensorDescription(
        key="tusd_convencional_r_kwh",
        value_key="tusd_convencional_r_kwh",
        name="TUSD convencional",
        native_unit_of_measurement=UNIT_R_KWH,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    TarifaSensorDescription(
        key="tarifa_convencional_bruta_r_kwh",
        value_key="tarifa_convencional_bruta_r_kwh",
        name="Tarifa convencional bruta",
        native_unit_of_measurement=UNIT_R_KWH,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    TarifaSensorDescription(
        key="tarifa_convencional_final_r_kwh",
        value_key="tarifa_convencional_final_r_kwh",
        name="Tarifa convencional final",
        native_unit_of_measurement=UNIT_R_KWH,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    TarifaSensorDescription(
        key="te_branca_fora_ponta_r_kwh",
        value_key="te_branca_fora_ponta_r_kwh",
        name="TE branca fora ponta",
        native_unit_of_measurement=UNIT_R_KWH,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    TarifaSensorDescription(
        key="tusd_branca_fora_ponta_r_kwh",
        value_key="tusd_branca_fora_ponta_r_kwh",
        name="TUSD branca fora ponta",
        native_unit_of_measurement=UNIT_R_KWH,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    TarifaSensorDescription(
        key="tarifa_branca_fora_ponta_bruta_r_kwh",
        value_key="tarifa_branca_fora_ponta_bruta_r_kwh",
        name="Tarifa branca fora ponta bruta",
        native_unit_of_measurement=UNIT_R_KWH,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    TarifaSensorDescription(
        key="tarifa_branca_fora_ponta_final_r_kwh",
        value_key="tarifa_branca_fora_ponta_final_r_kwh",
        name="Tarifa branca fora ponta final",
        native_unit_of_measurement=UNIT_R_KWH,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    TarifaSensorDescription(
        key="te_branca_intermediario_r_kwh",
        value_key="te_branca_intermediario_r_kwh",
        name="TE branca intermediario",
        native_unit_of_measurement=UNIT_R_KWH,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    TarifaSensorDescription(
        key="tusd_branca_intermediario_r_kwh",
        value_key="tusd_branca_intermediario_r_kwh",
        name="TUSD branca intermediario",
        native_unit_of_measurement=UNIT_R_KWH,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    TarifaSensorDescription(
        key="tarifa_branca_intermediario_bruta_r_kwh",
        value_key="tarifa_branca_intermediario_bruta_r_kwh",
        name="Tarifa branca intermediario bruta",
        native_unit_of_measurement=UNIT_R_KWH,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    TarifaSensorDescription(
        key="tarifa_branca_intermediario_final_r_kwh",
        value_key="tarifa_branca_intermediario_final_r_kwh",
        name="Tarifa branca intermediario final",
        native_unit_of_measurement=UNIT_R_KWH,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    TarifaSensorDescription(
        key="te_branca_ponta_r_kwh",
        value_key="te_branca_ponta_r_kwh",
        name="TE branca ponta",
        native_unit_of_measurement=UNIT_R_KWH,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    TarifaSensorDescription(
        key="tusd_branca_ponta_r_kwh",
        value_key="tusd_branca_ponta_r_kwh",
        name="TUSD branca ponta",
        native_unit_of_measurement=UNIT_R_KWH,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    TarifaSensorDescription(
        key="tarifa_branca_ponta_bruta_r_kwh",
        value_key="tarifa_branca_ponta_bruta_r_kwh",
        name="Tarifa branca ponta bruta",
        native_unit_of_measurement=UNIT_R_KWH,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    TarifaSensorDescription(
        key="tarifa_branca_ponta_final_r_kwh",
        value_key="tarifa_branca_ponta_final_r_kwh",
        name="Tarifa branca ponta final",
        native_unit_of_measurement=UNIT_R_KWH,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    TarifaSensorDescription(
        key="fio_b_bruto_r_kwh",
        value_key="fio_b_bruto_r_kwh",
        name="Fio B bruto",
        native_unit_of_measurement=UNIT_R_KWH,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    TarifaSensorDescription(
        key="fio_b_final_r_kwh",
        value_key="fio_b_final_r_kwh",
        name="Fio B final",
        native_unit_of_measurement=UNIT_R_KWH,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    TarifaSensorDescription(
        key="pis_percent",
        value_key="pis_percent",
        name="PIS",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    TarifaSensorDescription(
        key="cofins_percent",
        value_key="cofins_percent",
        name="COFINS",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    TarifaSensorDescription(
        key="icms_percent",
        value_key="icms_percent",
        name="ICMS",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    TarifaSensorDescription(
        key="bandeira_vigente",
        value_key="bandeira_vigente",
        name="Bandeira vigente",
    ),
    TarifaSensorDescription(
        key="adicional_bandeira_r_kwh",
        value_key="adicional_bandeira_r_kwh",
        name="Adicional da bandeira",
        native_unit_of_measurement=UNIT_R_KWH,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    TarifaSensorDescription(
        key="indicador_taxa_minima",
        value_key="indicador_taxa_minima",
        name="Indicador taxa minima",
    ),
    TarifaSensorDescription(
        key="kwh_adicionados_disponibilidade",
        value_key="kwh_adicionados_disponibilidade",
        name="kWh adicionados para disponibilidade",
        native_unit_of_measurement=UNIT_KWH,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    TarifaSensorDescription(
        key="saldo_creditos_mes_anterior_kwh",
        value_key="saldo_creditos_mes_anterior_kwh",
        name="Saldo de creditos do mes anterior",
        native_unit_of_measurement=UNIT_KWH,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    TarifaSensorDescription(
        key="previsao_creditos_gerados_kwh",
        value_key="previsao_creditos_gerados_kwh",
        name="Previsao de creditos gerados",
        native_unit_of_measurement=UNIT_KWH,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    TarifaSensorDescription(
        key="auto_consumo_kwh",
        value_key="auto_consumo_kwh",
        name="Auto-consumo",
        native_unit_of_measurement=UNIT_KWH,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    TarifaSensorDescription(
        key="auto_consumo_reais",
        value_key="auto_consumo_reais",
        name="Auto-consumo em reais",
        native_unit_of_measurement=UNIT_R,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Cria entidades da plataforma sensor para a integracao."""

    coordinator: TarifasEnergiaBrasilCoordinator = hass.data[DOMAIN][entry.entry_id]
    enabled_breakdowns = _entry_breakdowns(entry)
    has_generation = bool(_entry_value(entry, CONF_GENERATION_ENTITY))

    dynamic_descriptions: list[TarifaSensorDescription] = []
    for period in enabled_breakdowns:
        suffix = _period_suffix(period)
        dynamic_descriptions.extend(
            (
                TarifaSensorDescription(
                    key=f"valor_conta_consumo_regular_{period}_r",
                    value_key=f"valor_conta_consumo_regular_{period}_r",
                    name=f"Valor conta consumo regular {suffix}",
                    native_unit_of_measurement=UNIT_R,
                    device_class=SensorDeviceClass.MONETARY,
                    state_class=SensorStateClass.MEASUREMENT,
                ),
                TarifaSensorDescription(
                    key=f"valor_conta_tarifa_branca_{period}_r",
                    value_key=f"valor_conta_tarifa_branca_{period}_r",
                    name=f"Valor conta tarifa branca {suffix}",
                    native_unit_of_measurement=UNIT_R,
                    device_class=SensorDeviceClass.MONETARY,
                    state_class=SensorStateClass.MEASUREMENT,
                ),
            )
        )

        if has_generation:
            dynamic_descriptions.extend(
                (
                    TarifaSensorDescription(
                        key=f"valor_conta_com_geracao_{period}_r",
                        value_key=f"valor_conta_com_geracao_{period}_r",
                        name=f"Valor conta com geracao {suffix}",
                        native_unit_of_measurement=UNIT_R,
                        device_class=SensorDeviceClass.MONETARY,
                        state_class=SensorStateClass.MEASUREMENT,
                    ),
                    TarifaSensorDescription(
                        key=f"valor_fio_b_compensada_{period}_r",
                        value_key=f"valor_fio_b_compensada_{period}_r",
                        name=f"Valor Fio B compensada {suffix}",
                        native_unit_of_measurement=UNIT_R,
                        device_class=SensorDeviceClass.MONETARY,
                        state_class=SensorStateClass.MEASUREMENT,
                    ),
                )
            )

    entities: list[TarifasEnergiaBrasilSensor] = [
        TarifasEnergiaBrasilSensor(
            coordinator=coordinator,
            entry=entry,
            description=description,
        )
        for description in (*BASE_SENSOR_DESCRIPTIONS, *dynamic_descriptions)
    ]
    async_add_entities(entities)


def _entry_value(entry: ConfigEntry, key: str, default: Any = None) -> Any:
    """Le valor de configuracao priorizando options."""

    if key in entry.options:
        return entry.options[key]
    if key in entry.data:
        return entry.data[key]
    return default


def _entry_breakdowns(entry: ConfigEntry) -> list[str]:
    """Retorna quebras configuradas para criação de sensores."""

    raw = _entry_value(entry, CONF_BREAKDOWNS, DEFAULT_BREAKDOWNS)
    if not isinstance(raw, list):
        return DEFAULT_BREAKDOWNS
    valid = [item for item in raw if item in (BREAKDOWN_DAILY, BREAKDOWN_WEEKLY, BREAKDOWN_MONTHLY)]
    return valid or DEFAULT_BREAKDOWNS


def _period_suffix(period: str) -> str:
    """Converte chave de quebra em sufixo amigavel."""

    if period == BREAKDOWN_DAILY:
        return "diario"
    if period == BREAKDOWN_WEEKLY:
        return "semanal"
    return "mensal"


class TarifasEnergiaBrasilSensor(
    CoordinatorEntity[TarifasEnergiaBrasilCoordinator], SensorEntity
):
    """Sensor generico para chaves publicadas pelo coordinator."""

    entity_description: TarifaSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: TarifasEnergiaBrasilCoordinator,
        entry: ConfigEntry,
        description: TarifaSensorDescription,
    ) -> None:
        """Inicializa sensor baseado na descricao."""

        super().__init__(coordinator)
        self.entity_description = description
        self._entry = entry
        concessionaria = _entry_value(entry, CONF_CONCESSIONARIA, "desconhecida")
        concessionaria_slug = slugify(str(concessionaria))

        self._attr_unique_id = f"{entry.entry_id}_{description.value_key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{DOMAIN}_{concessionaria_slug}")},
            name=f"Tarifas Energia Brasil - {concessionaria}",
            manufacturer="ANEEL / concessionaria",
            model="Integracao HACS",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def available(self) -> bool:
        """Entidade disponivel quando coordinator possui snapshot."""

        return super().available and self.coordinator.data is not None

    @property
    def native_value(self) -> Any:
        """Retorna valor atual da chave de snapshot."""

        if self.coordinator.data is None:
            return None
        raw = self.coordinator.data.values.get(self.entity_description.value_key)
        if isinstance(raw, bool):
            return "sim" if raw else "nao"
        return raw

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Publica diagnosticos de coleta por entidade."""

        if self.coordinator.data is None:
            return {}

        attrs: dict[str, Any] = {
            "concessionaria": self.coordinator.data.concessionaria,
            "ultima_atualizacao": self.coordinator.data.updated_at.isoformat(),
        }
        metadata = self.coordinator.data.collections_by_key.get(self.entity_description.value_key)
        if metadata is not None:
            attrs.update(metadata.as_attributes())

        diagnostics = self.coordinator.data.diagnostics
        attrs["prioridade_aneel"] = diagnostics.get("prioridade_aneel")
        attrs["mensagem_erro"] = diagnostics.get("mensagem_erro")
        return attrs
