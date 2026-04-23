"""Versao: 0.1.0
Criado em: 2026-04-22 21:41:36 -03:00
Criado por: Codex
Projeto/pasta: ha.ext.tarifas
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import (
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
    SUPPORTED_ANEEL_METHODS,
    SUPPORTED_SUPPLY_TYPES,
    get_supported_concessionarias_for_flow,
)


class TarifasEnergiaBrasilConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Fluxo inicial da integracao no Home Assistant."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Passo unico do fluxo de configuracao inicial."""

        errors: dict[str, str] = {}
        if user_input is not None:
            generation_entity = user_input.get(CONF_GENERATION_ENTITY)
            supply_type = user_input.get(CONF_SUPPLY_TYPE)
            if generation_entity and not supply_type:
                errors["base"] = "supply_type_required"
            else:
                await self.async_set_unique_id(user_input[CONF_CONCESSIONARIA])
                self._abort_if_unique_id_configured()
                title = f"Tarifas Energia Brasil - {user_input[CONF_CONCESSIONARIA]}"
                return self.async_create_entry(title=title, data=user_input)

        schema = self._build_schema(user_input)
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    def _build_schema(user_input: dict[str, Any] | None = None) -> vol.Schema:
        """Monta schema principal de configuracao."""

        defaults = user_input or {}
        return vol.Schema(
            {
                vol.Required(
                    CONF_CONCESSIONARIA,
                    default=defaults.get(
                        CONF_CONCESSIONARIA,
                        get_supported_concessionarias_for_flow()[0],
                    ),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=get_supported_concessionarias_for_flow(),
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(
                    CONF_READING_DAY,
                    default=int(defaults.get(CONF_READING_DAY, DEFAULT_READING_DAY)),
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=31)),
                vol.Required(
                    CONF_UPDATE_HOURS,
                    default=int(defaults.get(CONF_UPDATE_HOURS, DEFAULT_UPDATE_HOURS)),
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=168)),
                vol.Required(
                    CONF_ANEEL_METHOD,
                    default=defaults.get(CONF_ANEEL_METHOD, DEFAULT_ANEEL_METHOD),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=list(SUPPORTED_ANEEL_METHODS),
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(
                    CONF_CONSUMPTION_ENTITY,
                    default=defaults.get(CONF_CONSUMPTION_ENTITY),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["sensor"],
                        device_class=["energy"],
                    )
                ),
                vol.Optional(
                    CONF_GENERATION_ENTITY,
                    default=defaults.get(CONF_GENERATION_ENTITY),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["sensor"],
                        device_class=["energy"],
                    )
                ),
                vol.Optional(
                    CONF_SUPPLY_TYPE,
                    default=defaults.get(CONF_SUPPLY_TYPE),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=list(SUPPORTED_SUPPLY_TYPES),
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(
                    CONF_BREAKDOWNS,
                    default=defaults.get(CONF_BREAKDOWNS, DEFAULT_BREAKDOWNS),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=list(DEFAULT_BREAKDOWNS + ["weekly"]),
                        multiple=True,
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
            }
        )

    @staticmethod
    @config_entries.callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """Retorna fluxo de opcoes apos criacao da integracao."""

        return TarifasEnergiaBrasilOptionsFlow(config_entry)


class TarifasEnergiaBrasilOptionsFlow(config_entries.OptionsFlow):
    """Fluxo de ajustes pos-configuracao."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Guarda referencia da entrada para defaults."""

        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Exibe e salva configuracoes de opcoes da integracao."""

        errors: dict[str, str] = {}
        if user_input is not None:
            generation_entity = user_input.get(CONF_GENERATION_ENTITY)
            supply_type = user_input.get(CONF_SUPPLY_TYPE)
            if generation_entity and not supply_type:
                errors["base"] = "supply_type_required"
            else:
                return self.async_create_entry(title="", data=user_input)

        schema = TarifasEnergiaBrasilConfigFlow._build_schema(
            self._current_defaults(user_input)
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)

    def _current_defaults(self, user_input: dict[str, Any] | None) -> dict[str, Any]:
        """Prioriza input atual, depois options, depois data original."""

        if user_input:
            return user_input
        return {
            **self._config_entry.data,
            **self._config_entry.options,
        }
