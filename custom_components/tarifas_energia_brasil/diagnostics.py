"""Versao: 0.1.0
Criado em: 2026-04-22 21:41:36 -03:00
Criado por: Codex
Projeto/pasta: ha.ext.tarifas
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_ENTIDADE_CONSUMO, CONF_ENTIDADE_GERACAO, DOMAIN

TO_REDACT = {CONF_ENTIDADE_CONSUMO, CONF_ENTIDADE_GERACAO}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Retorna diagnostico da entrada com dados sensiveis redigidos."""

    coordinator = hass.data[DOMAIN][entry.entry_id]
    payload = {
        "entry": {
            "entry_id": entry.entry_id,
            "title": entry.title,
            "data": dict(entry.data),
            "options": dict(entry.options),
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "last_exception": str(coordinator.last_exception)
            if coordinator.last_exception
            else None,
            "snapshot": coordinator.data.valores if coordinator.data else None,
            "diagnosticos": coordinator.data.diagnosticos if coordinator.data else None,
        },
    }
    return async_redact_data(payload, TO_REDACT)
