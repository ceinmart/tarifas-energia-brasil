"""Versao: 0.1.0
Criado em: 2026-04-22 21:41:36 -03:00
Criado por: Codex
Projeto/pasta: ha.ext.tarifas
"""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_UPDATE_HOURS, DEFAULT_UPDATE_HOURS, DOMAIN, PLATFORMS
from .coordinator import TarifasEnergiaBrasilCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Configura integracao via UI; YAML nao e utilizado."""

    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Inicializa coordinator e plataformas para a config entry."""

    coordinator = TarifasEnergiaBrasilCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Remove plataformas e limpa estado da entrada."""

    coordinator: TarifasEnergiaBrasilCoordinator | None = hass.data.get(DOMAIN, {}).get(
        entry.entry_id
    )
    if coordinator is not None:
        await coordinator.async_persist_state()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Recarrega entrada quando options sao alteradas."""

    update_hours = entry.options.get(CONF_UPDATE_HOURS, DEFAULT_UPDATE_HOURS)
    _LOGGER.debug("Recarregando %s com update_hours=%s", entry.entry_id, update_hours)
    await hass.config_entries.async_reload(entry.entry_id)
