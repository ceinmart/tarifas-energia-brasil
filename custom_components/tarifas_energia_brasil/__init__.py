"""Versao: 0.2.0
Criado em: 2026-04-22 21:41:36 -03:00
Alterado em: 2026-08-10 (America/Sao_Paulo)
Criado por: Codex
Projeto/pasta: ha.ext.tarifas
"""

from __future__ import annotations

import asyncio
import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_HORAS_ATUALIZACAO,
    CONF_METODO_ANEEL,
    CONF_MULTIPLICADOR_FALLBACK_CSV,
    DOMAIN,
    HORAS_ATUALIZACAO_PADRAO,
    METODO_ANEEL_CSV_XML,
    METODO_ANEEL_PADRAO,
    PLATFORMS,
)
from .coordinator import TarifasEnergiaBrasilCoordinator

_LOGGER = logging.getLogger(__name__)
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
SERVICE_UPDATE_CSV = "atualizar_via_csv"
SERVICE_CANCEL_CSV = "cancelar_atualizacao_csv"
ATTR_CONFIG_ENTRY_ID = "config_entry_id"
ATTR_DATASET = "dataset"
CSV_DATASETS = ("tarifas", "fio_b", "bandeira", "todos")


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Configura integracao via UI; YAML nao e utilizado."""

    hass.data.setdefault(DOMAIN, {})
    async def _update_csv(call: object) -> None:
        coordinator = _coordinator_from_call(hass, call)
        try:
            coordinator.start_manual_csv_update(call.data[ATTR_DATASET])
        except RuntimeError as err:
            raise ServiceValidationError(str(err)) from err

    async def _cancel_csv(call: object) -> None:
        coordinator = _coordinator_from_call(hass, call)
        if not coordinator.cancel_manual_csv_update():
            raise ServiceValidationError("Nao existe atualizacao CSV ativa para esta entrada.")

    hass.services.async_register(
        DOMAIN,
        SERVICE_UPDATE_CSV,
        _update_csv,
        schema=vol.Schema(
            {
                vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
                vol.Required(ATTR_DATASET): vol.In(CSV_DATASETS),
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CANCEL_CSV,
        _cancel_csv,
        schema=vol.Schema({vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string}),
    )
    return True


def _coordinator_from_call(
    hass: HomeAssistant, call: object
) -> TarifasEnergiaBrasilCoordinator:
    """Resolve a entrada explicitamente informada pela action."""

    entry_id = call.data[ATTR_CONFIG_ENTRY_ID]  # type: ignore[attr-defined]
    coordinator = hass.data.get(DOMAIN, {}).get(entry_id)
    if coordinator is None:
        raise ServiceValidationError(f"Entrada de configuracao nao encontrada: {entry_id}")
    return coordinator


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migra prioridade CSV legada e remove a opcao de multiplicador obsoleta."""

    if entry.version >= 2:
        return True
    data = dict(entry.data)
    options = dict(entry.options)
    for payload in (data, options):
        if payload.get(CONF_METODO_ANEEL) == METODO_ANEEL_CSV_XML:
            payload[CONF_METODO_ANEEL] = METODO_ANEEL_PADRAO
        payload.pop(CONF_MULTIPLICADOR_FALLBACK_CSV, None)
    hass.config_entries.async_update_entry(
        entry,
        data=data,
        options=options,
        version=2,
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Inicializa coordinator e plataformas para a config entry."""

    coordinator = TarifasEnergiaBrasilCoordinator(hass, entry)
    await coordinator.async_ensure_state_loaded()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await coordinator.async_start_state_tracking()
    refresh_task = hass.async_create_task(
        _async_refresh_after_setup(coordinator),
        f"{DOMAIN}_{entry.entry_id}_initial_refresh",
    )
    entry.async_on_unload(lambda: _cancel_task(refresh_task))
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


def _cancel_task(task: asyncio.Task) -> None:
    """Cancela tarefa sem expor o retorno booleano de Task.cancel ao HA."""

    task.cancel()


async def _async_refresh_after_setup(
    coordinator: TarifasEnergiaBrasilCoordinator,
) -> None:
    """Executa primeira atualizacao sem bloquear o setup da config entry."""

    try:
        await coordinator.async_refresh()
    except asyncio.CancelledError:
        raise
    except Exception:
        _LOGGER.debug(
            "Falha na primeira atualizacao em background; nova tentativa ocorrera no ciclo.",
            exc_info=True,
        )


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Remove plataformas e limpa estado da entrada."""

    coordinator: TarifasEnergiaBrasilCoordinator | None = hass.data.get(DOMAIN, {}).get(
        entry.entry_id
    )
    if coordinator is not None:
        await coordinator.async_cancel_manual_csv_update()
        await coordinator.async_stop_state_tracking()
        await coordinator.async_persist_state()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Recarrega entrada quando options sao alteradas."""

    update_hours = entry.options.get(CONF_HORAS_ATUALIZACAO, HORAS_ATUALIZACAO_PADRAO)
    _LOGGER.debug("Recarregando %s com update_hours=%s", entry.entry_id, update_hours)
    await hass.config_entries.async_reload(entry.entry_id)
