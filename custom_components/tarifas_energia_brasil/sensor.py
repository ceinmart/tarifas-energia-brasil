"""Versao: 0.1.0
Criado em: 2026-04-22 21:41:36 -03:00
Criado por: Codex
Projeto/pasta: ha.ext.tarifas
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import (
    CONF_CONCESSIONARIA,
    CONF_QUEBRAS_CALCULO,
    DOMAIN,
    GRUPO_ENTIDADE_GERACAO,
    GRUPO_ENTIDADE_REGULAR,
    GRUPO_ENTIDADE_TARIFA_BRANCA,
    QUEBRA_DIARIA,
    QUEBRA_MENSAL,
    QUEBRA_SEMANAL,
    QUEBRAS_PADRAO,
    grupo_geracao_habilitado,
    grupo_tarifa_branca_habilitado,
)
from .coordinator import TarifasEnergiaBrasilCoordinator

UNIDADE_R_KWH = "R$/kWh"
UNIDADE_R = "R$"
UNIDADE_KWH = "kWh"
CASAS_DECIMAIS_EXIBICAO = 4


@dataclass(frozen=True, kw_only=True)
class DescricaoSensorTarifa(SensorEntityDescription):
    """Descricao de sensor baseado em chave do snapshot."""

    chave_valor: str
    grupo: str = GRUPO_ENTIDADE_REGULAR


DESCRICOES_SENSORES_BASE: tuple[DescricaoSensorTarifa, ...] = (
    DescricaoSensorTarifa(
        key="te_convencional_r_kwh",
        chave_valor="te_convencional_r_kwh",
        name="TE convencional",
        native_unit_of_measurement=UNIDADE_R_KWH,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    DescricaoSensorTarifa(
        key="tusd_convencional_r_kwh",
        chave_valor="tusd_convencional_r_kwh",
        name="TUSD convencional",
        native_unit_of_measurement=UNIDADE_R_KWH,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    DescricaoSensorTarifa(
        key="tarifa_convencional_bruta_r_kwh",
        chave_valor="tarifa_convencional_bruta_r_kwh",
        name="Tarifa convencional bruta",
        native_unit_of_measurement=UNIDADE_R_KWH,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    DescricaoSensorTarifa(
        key="tarifa_convencional_final_r_kwh",
        chave_valor="tarifa_convencional_final_r_kwh",
        name="Tarifa convencional final",
        native_unit_of_measurement=UNIDADE_R_KWH,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    DescricaoSensorTarifa(
        key="te_branca_fora_ponta_r_kwh",
        chave_valor="te_branca_fora_ponta_r_kwh",
        name="TE branca fora ponta",
        native_unit_of_measurement=UNIDADE_R_KWH,
        state_class=SensorStateClass.MEASUREMENT,
        grupo=GRUPO_ENTIDADE_TARIFA_BRANCA,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    DescricaoSensorTarifa(
        key="tusd_branca_fora_ponta_r_kwh",
        chave_valor="tusd_branca_fora_ponta_r_kwh",
        name="TUSD branca fora ponta",
        native_unit_of_measurement=UNIDADE_R_KWH,
        state_class=SensorStateClass.MEASUREMENT,
        grupo=GRUPO_ENTIDADE_TARIFA_BRANCA,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    DescricaoSensorTarifa(
        key="tarifa_branca_fora_ponta_bruta_r_kwh",
        chave_valor="tarifa_branca_fora_ponta_bruta_r_kwh",
        name="Tarifa branca fora ponta bruta",
        native_unit_of_measurement=UNIDADE_R_KWH,
        state_class=SensorStateClass.MEASUREMENT,
        grupo=GRUPO_ENTIDADE_TARIFA_BRANCA,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    DescricaoSensorTarifa(
        key="tarifa_branca_fora_ponta_final_r_kwh",
        chave_valor="tarifa_branca_fora_ponta_final_r_kwh",
        name="Tarifa branca fora ponta final",
        native_unit_of_measurement=UNIDADE_R_KWH,
        state_class=SensorStateClass.MEASUREMENT,
        grupo=GRUPO_ENTIDADE_TARIFA_BRANCA,
    ),
    DescricaoSensorTarifa(
        key="te_branca_intermediario_r_kwh",
        chave_valor="te_branca_intermediario_r_kwh",
        name="TE branca intermediario",
        native_unit_of_measurement=UNIDADE_R_KWH,
        state_class=SensorStateClass.MEASUREMENT,
        grupo=GRUPO_ENTIDADE_TARIFA_BRANCA,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    DescricaoSensorTarifa(
        key="tusd_branca_intermediario_r_kwh",
        chave_valor="tusd_branca_intermediario_r_kwh",
        name="TUSD branca intermediario",
        native_unit_of_measurement=UNIDADE_R_KWH,
        state_class=SensorStateClass.MEASUREMENT,
        grupo=GRUPO_ENTIDADE_TARIFA_BRANCA,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    DescricaoSensorTarifa(
        key="tarifa_branca_intermediario_bruta_r_kwh",
        chave_valor="tarifa_branca_intermediario_bruta_r_kwh",
        name="Tarifa branca intermediario bruta",
        native_unit_of_measurement=UNIDADE_R_KWH,
        state_class=SensorStateClass.MEASUREMENT,
        grupo=GRUPO_ENTIDADE_TARIFA_BRANCA,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    DescricaoSensorTarifa(
        key="tarifa_branca_intermediario_final_r_kwh",
        chave_valor="tarifa_branca_intermediario_final_r_kwh",
        name="Tarifa branca intermediario final",
        native_unit_of_measurement=UNIDADE_R_KWH,
        state_class=SensorStateClass.MEASUREMENT,
        grupo=GRUPO_ENTIDADE_TARIFA_BRANCA,
    ),
    DescricaoSensorTarifa(
        key="te_branca_ponta_r_kwh",
        chave_valor="te_branca_ponta_r_kwh",
        name="TE branca ponta",
        native_unit_of_measurement=UNIDADE_R_KWH,
        state_class=SensorStateClass.MEASUREMENT,
        grupo=GRUPO_ENTIDADE_TARIFA_BRANCA,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    DescricaoSensorTarifa(
        key="tusd_branca_ponta_r_kwh",
        chave_valor="tusd_branca_ponta_r_kwh",
        name="TUSD branca ponta",
        native_unit_of_measurement=UNIDADE_R_KWH,
        state_class=SensorStateClass.MEASUREMENT,
        grupo=GRUPO_ENTIDADE_TARIFA_BRANCA,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    DescricaoSensorTarifa(
        key="tarifa_branca_ponta_bruta_r_kwh",
        chave_valor="tarifa_branca_ponta_bruta_r_kwh",
        name="Tarifa branca ponta bruta",
        native_unit_of_measurement=UNIDADE_R_KWH,
        state_class=SensorStateClass.MEASUREMENT,
        grupo=GRUPO_ENTIDADE_TARIFA_BRANCA,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    DescricaoSensorTarifa(
        key="tarifa_branca_ponta_final_r_kwh",
        chave_valor="tarifa_branca_ponta_final_r_kwh",
        name="Tarifa branca ponta final",
        native_unit_of_measurement=UNIDADE_R_KWH,
        state_class=SensorStateClass.MEASUREMENT,
        grupo=GRUPO_ENTIDADE_TARIFA_BRANCA,
    ),
    DescricaoSensorTarifa(
        key="fio_b_bruto_r_kwh",
        chave_valor="fio_b_bruto_r_kwh",
        name="Fio B bruto",
        native_unit_of_measurement=UNIDADE_R_KWH,
        state_class=SensorStateClass.MEASUREMENT,
        grupo=GRUPO_ENTIDADE_GERACAO,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    DescricaoSensorTarifa(
        key="fio_b_final_r_kwh",
        chave_valor="fio_b_final_r_kwh",
        name="Fio B final",
        native_unit_of_measurement=UNIDADE_R_KWH,
        state_class=SensorStateClass.MEASUREMENT,
        grupo=GRUPO_ENTIDADE_GERACAO,
    ),
    DescricaoSensorTarifa(
        key="pis_percent",
        chave_valor="pis_percent",
        name="PIS",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    DescricaoSensorTarifa(
        key="cofins_percent",
        chave_valor="cofins_percent",
        name="COFINS",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    DescricaoSensorTarifa(
        key="icms_percent",
        chave_valor="icms_percent",
        name="ICMS",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    DescricaoSensorTarifa(
        key="bandeira_vigente",
        chave_valor="bandeira_vigente",
        name="Bandeira vigente",
    ),
    DescricaoSensorTarifa(
        key="adicional_bandeira_r_kwh",
        chave_valor="adicional_bandeira_r_kwh",
        name="Adicional da bandeira",
        native_unit_of_measurement=UNIDADE_R_KWH,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    DescricaoSensorTarifa(
        key="indicador_taxa_minima",
        chave_valor="indicador_taxa_minima",
        name="Indicador taxa minima",
    ),
    DescricaoSensorTarifa(
        key="kwh_adicionados_disponibilidade",
        chave_valor="kwh_adicionados_disponibilidade",
        name="kWh adicionados para disponibilidade",
        native_unit_of_measurement=UNIDADE_KWH,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    DescricaoSensorTarifa(
        key="saldo_creditos_mes_anterior_kwh",
        chave_valor="saldo_creditos_mes_anterior_kwh",
        name="Saldo de creditos do mes anterior",
        native_unit_of_measurement=UNIDADE_KWH,
        state_class=SensorStateClass.MEASUREMENT,
        grupo=GRUPO_ENTIDADE_GERACAO,
    ),
    DescricaoSensorTarifa(
        key="previsao_creditos_gerados_kwh",
        chave_valor="previsao_creditos_gerados_kwh",
        name="Previsao de creditos gerados",
        native_unit_of_measurement=UNIDADE_KWH,
        state_class=SensorStateClass.MEASUREMENT,
        grupo=GRUPO_ENTIDADE_GERACAO,
    ),
    DescricaoSensorTarifa(
        key="auto_consumo_kwh",
        chave_valor="auto_consumo_kwh",
        name="Auto-consumo acumulado",
        native_unit_of_measurement=UNIDADE_KWH,
        state_class=SensorStateClass.MEASUREMENT,
        grupo=GRUPO_ENTIDADE_GERACAO,
    ),
    DescricaoSensorTarifa(
        key="auto_consumo_reais",
        chave_valor="auto_consumo_reais",
        name="Auto-consumo acumulado em reais",
        native_unit_of_measurement=UNIDADE_R,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
        grupo=GRUPO_ENTIDADE_GERACAO,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Cria entidades da plataforma sensor para a integracao."""

    coordinator: TarifasEnergiaBrasilCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[TarifasEnergiaBrasilSensor] = [
        TarifasEnergiaBrasilSensor(
            coordinator=coordinator,
            entry=entry,
            description=description,
        )
        for description in montar_descricoes_sensores(entry)
    ]
    async_add_entities(entities)


def _entry_value(entry: ConfigEntry, key: str, default: Any = None) -> Any:
    """Le valor de configuracao priorizando options."""

    if key in entry.options:
        return entry.options[key]
    if key in entry.data:
        return entry.data[key]
    return default


def _quebras_da_entrada(entry: ConfigEntry) -> list[str]:
    """Retorna quebras configuradas para criação de sensores."""

    raw = _entry_value(entry, CONF_QUEBRAS_CALCULO, QUEBRAS_PADRAO)
    if not isinstance(raw, list):
        return QUEBRAS_PADRAO
    valid = [item for item in raw if item in (QUEBRA_DIARIA, QUEBRA_SEMANAL, QUEBRA_MENSAL)]
    return valid or QUEBRAS_PADRAO


def _sufixo_periodo(period: str) -> str:
    """Converte chave de quebra em sufixo amigavel."""

    if period == QUEBRA_DIARIA:
        return "diario"
    if period == QUEBRA_SEMANAL:
        return "semanal"
    return "mensal"


def _configuracao_efetiva_entrada(entry: ConfigEntry) -> dict[str, Any]:
    """Combina data e options para resolver grupos e parametros."""

    return {
        **entry.data,
        **entry.options,
    }


def _grupos_habilitados(entry: ConfigEntry) -> set[str]:
    """Resolve quais grupos logicos devem publicar entidades."""

    config = _configuracao_efetiva_entrada(entry)
    enabled = {GRUPO_ENTIDADE_REGULAR}
    if grupo_geracao_habilitado(config):
        enabled.add(GRUPO_ENTIDADE_GERACAO)
    if grupo_tarifa_branca_habilitado(config):
        enabled.add(GRUPO_ENTIDADE_TARIFA_BRANCA)
    return enabled


def montar_descricoes_sensores(entry: ConfigEntry) -> tuple[DescricaoSensorTarifa, ...]:
    """Monta lista final de sensores respeitando grupos e quebras habilitadas."""

    quebras_habilitadas = _quebras_da_entrada(entry)
    grupos_habilitados = _grupos_habilitados(entry)
    descricoes_dinamicas: list[DescricaoSensorTarifa] = []

    for period in quebras_habilitadas:
        suffix = _sufixo_periodo(period)
        descricoes_dinamicas.append(
            DescricaoSensorTarifa(
                key=f"valor_conta_consumo_regular_{period}_r",
                chave_valor=f"valor_conta_consumo_regular_{period}_r",
                name=f"Valor conta consumo regular {suffix}",
                native_unit_of_measurement=UNIDADE_R,
                device_class=SensorDeviceClass.MONETARY,
                state_class=SensorStateClass.MEASUREMENT,
                grupo=GRUPO_ENTIDADE_REGULAR,
            )
        )
        if period == QUEBRA_MENSAL:
            descricoes_dinamicas.append(
                DescricaoSensorTarifa(
                    key=f"valor_conta_consumo_regular_sem_disponibilidade_{period}_r",
                    chave_valor=f"valor_conta_consumo_regular_sem_disponibilidade_{period}_r",
                    name="Valor consumo regular mensal sem disponibilidade",
                    native_unit_of_measurement=UNIDADE_R,
                    device_class=SensorDeviceClass.MONETARY,
                    state_class=SensorStateClass.MEASUREMENT,
                    grupo=GRUPO_ENTIDADE_REGULAR,
                )
            )

        if GRUPO_ENTIDADE_TARIFA_BRANCA in grupos_habilitados:
            descricoes_dinamicas.append(
                DescricaoSensorTarifa(
                    key=f"valor_conta_tarifa_branca_{period}_r",
                    chave_valor=f"valor_conta_tarifa_branca_{period}_r",
                    name=f"Valor conta tarifa branca {suffix}",
                    native_unit_of_measurement=UNIDADE_R,
                    device_class=SensorDeviceClass.MONETARY,
                    state_class=SensorStateClass.MEASUREMENT,
                    grupo=GRUPO_ENTIDADE_TARIFA_BRANCA,
                )
            )
            if period == QUEBRA_MENSAL:
                descricoes_dinamicas.append(
                    DescricaoSensorTarifa(
                        key=f"valor_conta_tarifa_branca_sem_disponibilidade_{period}_r",
                        chave_valor=f"valor_conta_tarifa_branca_sem_disponibilidade_{period}_r",
                        name="Valor tarifa branca mensal sem disponibilidade",
                        native_unit_of_measurement=UNIDADE_R,
                        device_class=SensorDeviceClass.MONETARY,
                        state_class=SensorStateClass.MEASUREMENT,
                        grupo=GRUPO_ENTIDADE_TARIFA_BRANCA,
                    )
                )

        if GRUPO_ENTIDADE_GERACAO in grupos_habilitados:
            descricoes_dinamicas.extend(
                (
                    DescricaoSensorTarifa(
                        key=f"valor_conta_com_geracao_{period}_r",
                        chave_valor=f"valor_conta_com_geracao_{period}_r",
                        name=f"Valor conta com geracao {suffix}",
                        native_unit_of_measurement=UNIDADE_R,
                        device_class=SensorDeviceClass.MONETARY,
                        state_class=SensorStateClass.MEASUREMENT,
                        grupo=GRUPO_ENTIDADE_GERACAO,
                    ),
                    DescricaoSensorTarifa(
                        key=f"valor_fio_b_compensada_{period}_r",
                        chave_valor=f"valor_fio_b_compensada_{period}_r",
                        name=f"Valor Fio B compensada {suffix}",
                        native_unit_of_measurement=UNIDADE_R,
                        device_class=SensorDeviceClass.MONETARY,
                        state_class=SensorStateClass.MEASUREMENT,
                        grupo=GRUPO_ENTIDADE_GERACAO,
                    ),
                    DescricaoSensorTarifa(
                        key=f"auto_consumo_{period}_kwh",
                        chave_valor=f"auto_consumo_{period}_kwh",
                        name=f"Auto-consumo {suffix}",
                        native_unit_of_measurement=UNIDADE_KWH,
                        state_class=SensorStateClass.MEASUREMENT,
                        grupo=GRUPO_ENTIDADE_GERACAO,
                    ),
                    DescricaoSensorTarifa(
                        key=f"auto_consumo_{period}_reais",
                        chave_valor=f"auto_consumo_{period}_reais",
                        name=f"Auto-consumo em reais {suffix}",
                        native_unit_of_measurement=UNIDADE_R,
                        device_class=SensorDeviceClass.MONETARY,
                        state_class=SensorStateClass.MEASUREMENT,
                        grupo=GRUPO_ENTIDADE_GERACAO,
                    ),
                )
            )
            if period == QUEBRA_MENSAL:
                descricoes_dinamicas.append(
                    DescricaoSensorTarifa(
                        key=f"valor_conta_com_geracao_sem_disponibilidade_{period}_r",
                        chave_valor=f"valor_conta_com_geracao_sem_disponibilidade_{period}_r",
                        name="Valor conta com geracao mensal sem disponibilidade",
                        native_unit_of_measurement=UNIDADE_R,
                        device_class=SensorDeviceClass.MONETARY,
                        state_class=SensorStateClass.MEASUREMENT,
                        grupo=GRUPO_ENTIDADE_GERACAO,
                    )
                )

    descriptions = [
        description
        for description in (*DESCRICOES_SENSORES_BASE, *descricoes_dinamicas)
        if description.grupo in grupos_habilitados
    ]
    return tuple(descriptions)


class TarifasEnergiaBrasilSensor(CoordinatorEntity[TarifasEnergiaBrasilCoordinator], RestoreSensor):
    """Sensor generico para chaves publicadas pelo coordinator."""

    entity_description: DescricaoSensorTarifa
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: TarifasEnergiaBrasilCoordinator,
        entry: ConfigEntry,
        description: DescricaoSensorTarifa,
    ) -> None:
        """Inicializa sensor baseado na descricao."""

        super().__init__(coordinator)
        self.entity_description = description
        self._entry = entry
        self._restored_native_value: Any = None
        concessionaria = _entry_value(entry, CONF_CONCESSIONARIA, "desconhecida")
        concessionaria_slug = slugify(str(concessionaria))

        self._attr_unique_id = f"{entry.entry_id}_{description.chave_valor}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{DOMAIN}_{concessionaria_slug}")},
            name=f"Tarifas Energia Brasil - {concessionaria}",
            manufacturer="ANEEL / concessionaria",
            model="Integracao HACS",
            entry_type=DeviceEntryType.SERVICE,
        )

    async def async_added_to_hass(self) -> None:
        """Restaura ultimo valor conhecido enquanto o coordinator ainda nao atualizou."""

        await super().async_added_to_hass()
        if self.coordinator.data is not None:
            return

        if (last_sensor_data := await self.async_get_last_sensor_data()) is not None:
            restored_value = last_sensor_data.native_value
            if restored_value not in (None, STATE_UNKNOWN, STATE_UNAVAILABLE, ""):
                self._restored_native_value = restored_value
                return

        last_state = await self.async_get_last_state()
        if last_state is None or last_state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE, ""):
            return
        self._restored_native_value = self._coerce_restored_state(last_state.state)

    def _coerce_restored_state(self, state: str) -> Any:
        """Converte estado restaurado pelo HA para o tipo nativo esperado."""

        if not self._expects_numeric_state():
            return state
        try:
            return float(state)
        except (TypeError, ValueError):
            return None

    def _expects_numeric_state(self) -> bool:
        """Indica se a descricao do sensor exige valor numerico."""

        return bool(
            self.entity_description.state_class is not None
            or self.entity_description.native_unit_of_measurement is not None
            or self.entity_description.device_class is not None
        )

    @property
    def available(self) -> bool:
        """Entidade disponivel quando ha snapshot atual ou valor restaurado."""

        return self.coordinator.data is not None or self._restored_native_value is not None

    @property
    def native_value(self) -> Any:
        """Retorna valor atual da chave de snapshot."""

        if self.coordinator.data is None:
            return self._restored_native_value
        raw = self.coordinator.data.valores.get(self.entity_description.chave_valor)
        if isinstance(raw, bool):
            return "sim" if raw else "nao"
        if isinstance(raw, float):
            return round(raw, CASAS_DECIMAIS_EXIBICAO)
        return raw

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Publica diagnosticos de coleta por entidade."""

        if self.coordinator.data is None:
            return {}

        attrs: dict[str, Any] = {
            "concessionaria": self.coordinator.data.concessionaria,
            "ultima_atualizacao": self.coordinator.data.atualizado_em.isoformat(),
        }
        metadata = self.coordinator.data.coletas_por_chave.get(self.entity_description.chave_valor)
        if metadata is not None:
            attrs.update(metadata.como_atributos())

        diagnosticos = self.coordinator.data.diagnosticos
        attrs["prioridade_aneel"] = diagnosticos.get("prioridade_aneel")
        attrs["mensagem_erro"] = diagnosticos.get("mensagem_erro")
        if self.entity_description.chave_valor == "fio_b_final_r_kwh":
            valores = self.coordinator.data.valores
            for key in (
                "fio_b_calculo_expressao",
                "fio_b_transicao_r_kwh",
                "fio_b_percentual_transicao",
                "tusd_consumo_final_r_kwh",
                "tusd_credito_base_r_kwh",
                "tusd_credito_final_r_kwh",
                "icms_consumo_percent",
                "icms_compensacao_percent",
                "pis_cofins_percent",
                "fio_b_icms_consumo_source",
            ):
                if key in valores:
                    attrs[key] = valores[key]
        if self.entity_description.chave_valor == "icms_percent":
            valores = self.coordinator.data.valores
            for key in (
                "icms_calculo_expressao",
                "icms_consumo_mensal_kwh",
                "icms_consumo_faturavel_kwh",
                "icms_disponibilidade_minima_kwh",
                "icms_regra_faixas",
                "icms_fallback_percent",
                "icms_source",
            ):
                if key in valores:
                    attrs[key] = valores[key]
        return attrs
