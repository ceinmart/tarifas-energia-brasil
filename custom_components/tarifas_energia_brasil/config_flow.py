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
    CONF_CONCESSIONARIA,
    CONF_DIA_LEITURA,
    CONF_ENTIDADE_CONSUMO,
    CONF_ENTIDADE_GERACAO,
    CONF_ENTIDADE_INJECAO,
    CONF_HABILITAR_GRUPO_GERACAO,
    CONF_HABILITAR_GRUPO_TARIFA_BRANCA,
    CONF_HORAS_ATUALIZACAO,
    CONF_METODO_ANEEL,
    CONF_QUEBRAS_CALCULO,
    CONF_TB_FERIADOS_EXTRAS,
    CONF_TB_INTERMEDIARIO1_FIM,
    CONF_TB_INTERMEDIARIO1_INICIO,
    CONF_TB_INTERMEDIARIO2_FIM,
    CONF_TB_INTERMEDIARIO2_INICIO,
    CONF_TB_PONTA_FIM,
    CONF_TB_PONTA_INICIO,
    CONF_TIPO_FORNECIMENTO,
    DIA_LEITURA_PADRAO,
    DOMAIN,
    HABILITAR_GRUPO_TARIFA_BRANCA_PADRAO,
    HORAS_ATUALIZACAO_PADRAO,
    METODO_ANEEL_PADRAO,
    METODOS_ANEEL_SUPORTADOS,
    QUEBRA_SEMANAL,
    QUEBRAS_PADRAO,
    TIPOS_FORNECIMENTO_SUPORTADOS,
    grupo_geracao_habilitado,
    grupo_tarifa_branca_habilitado,
    obter_concessionarias_suportadas_para_fluxo,
)
from .tarifa_branca_time import obter_janelas_padrao_tarifa_branca


class TarifasEnergiaBrasilConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Fluxo inicial da integracao no Home Assistant."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Passo unico do fluxo de configuracao inicial."""

        errors: dict[str, str] = {}
        if user_input is not None:
            entrada_normalizada = self._normalize_entry_payload(user_input)
            entidade_geracao = entrada_normalizada.get(CONF_ENTIDADE_GERACAO)
            entidade_injecao = entrada_normalizada.get(CONF_ENTIDADE_INJECAO)
            tipo_fornecimento = entrada_normalizada.get(CONF_TIPO_FORNECIMENTO)
            if (entidade_geracao or entidade_injecao) and not tipo_fornecimento:
                errors["base"] = "tipo_fornecimento_obrigatorio"
            else:
                await self.async_set_unique_id(entrada_normalizada[CONF_CONCESSIONARIA])
                self._abort_if_unique_id_configured()
                title = f"Tarifas Energia Brasil - {entrada_normalizada[CONF_CONCESSIONARIA]}"
                return self.async_create_entry(title=title, data=entrada_normalizada)

        schema = self._build_schema(user_input)
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    def _build_schema(
        user_input: dict[str, Any] | None = None,
        *,
        incluir_opcoes_grupo: bool = False,
    ) -> vol.Schema:
        """Monta schema principal de configuracao."""

        defaults = user_input or {}
        schema: dict[Any, Any] = {
            vol.Required(
                CONF_CONCESSIONARIA,
                default=defaults.get(
                    CONF_CONCESSIONARIA,
                    obter_concessionarias_suportadas_para_fluxo()[0],
                ),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=obter_concessionarias_suportadas_para_fluxo(),
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Required(
                CONF_DIA_LEITURA,
                default=int(defaults.get(CONF_DIA_LEITURA, DIA_LEITURA_PADRAO)),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=31,
                    step=1,
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Required(
                CONF_HORAS_ATUALIZACAO,
                default=int(defaults.get(CONF_HORAS_ATUALIZACAO, HORAS_ATUALIZACAO_PADRAO)),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=168,
                    step=1,
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Required(
                CONF_METODO_ANEEL,
                default=defaults.get(CONF_METODO_ANEEL, METODO_ANEEL_PADRAO),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=list(METODOS_ANEEL_SUPORTADOS),
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Required(
                CONF_ENTIDADE_CONSUMO,
                default=defaults.get(CONF_ENTIDADE_CONSUMO),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain=["sensor"],
                    device_class=["energy"],
                )
            ),
            vol.Optional(
                CONF_ENTIDADE_GERACAO,
                default=defaults.get(CONF_ENTIDADE_GERACAO),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain=["sensor"],
                    device_class=["energy"],
                )
            ),
            vol.Optional(
                CONF_ENTIDADE_INJECAO,
                default=defaults.get(CONF_ENTIDADE_INJECAO),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain=["sensor"],
                    device_class=["energy"],
                )
            ),
            vol.Optional(
                CONF_TIPO_FORNECIMENTO,
                default=defaults.get(CONF_TIPO_FORNECIMENTO),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=list(TIPOS_FORNECIMENTO_SUPORTADOS),
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Required(
                CONF_QUEBRAS_CALCULO,
                default=defaults.get(CONF_QUEBRAS_CALCULO, QUEBRAS_PADRAO),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=list(QUEBRAS_PADRAO + [QUEBRA_SEMANAL]),
                    multiple=True,
                    mode=selector.SelectSelectorMode.LIST,
                )
            ),
        }

        if incluir_opcoes_grupo:
            if defaults.get(CONF_ENTIDADE_GERACAO) or defaults.get(CONF_ENTIDADE_INJECAO):
                schema[
                    vol.Required(
                        CONF_HABILITAR_GRUPO_GERACAO,
                        default=grupo_geracao_habilitado(defaults),
                    )
                ] = bool
            schema[
                vol.Required(
                    CONF_HABILITAR_GRUPO_TARIFA_BRANCA,
                    default=grupo_tarifa_branca_habilitado(defaults),
                )
            ] = bool

            concessionaria_for_defaults = str(
                defaults.get(
                    CONF_CONCESSIONARIA,
                    obter_concessionarias_suportadas_para_fluxo()[0],
                )
            )
            tb_defaults, _tb_source = obter_janelas_padrao_tarifa_branca(
                concessionaria_for_defaults
            )
            for field in (
                CONF_TB_PONTA_INICIO,
                CONF_TB_PONTA_FIM,
                CONF_TB_INTERMEDIARIO1_INICIO,
                CONF_TB_INTERMEDIARIO1_FIM,
                CONF_TB_INTERMEDIARIO2_INICIO,
                CONF_TB_INTERMEDIARIO2_FIM,
            ):
                schema[
                    vol.Optional(
                        field,
                        default=defaults.get(field, tb_defaults[field]),
                    )
                ] = str
            schema[
                vol.Optional(
                    CONF_TB_FERIADOS_EXTRAS,
                    default=defaults.get(CONF_TB_FERIADOS_EXTRAS, ""),
                )
            ] = str

        return vol.Schema(schema)

    @staticmethod
    def _normalize_entry_payload(user_input: dict[str, Any]) -> dict[str, Any]:
        """Aplica defaults persistidos para os grupos da integracao."""

        normalized = dict(user_input)
        possui_geracao = bool(
            normalized.get(CONF_ENTIDADE_GERACAO) or normalized.get(CONF_ENTIDADE_INJECAO)
        )

        normalized[CONF_HABILITAR_GRUPO_GERACAO] = (
            grupo_geracao_habilitado(normalized) if possui_geracao else False
        )
        normalized[CONF_HABILITAR_GRUPO_TARIFA_BRANCA] = normalized.get(
            CONF_HABILITAR_GRUPO_TARIFA_BRANCA,
            HABILITAR_GRUPO_TARIFA_BRANCA_PADRAO,
        )
        return normalized

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
            entrada_normalizada = TarifasEnergiaBrasilConfigFlow._normalize_entry_payload(
                user_input
            )
            entidade_geracao = entrada_normalizada.get(CONF_ENTIDADE_GERACAO)
            entidade_injecao = entrada_normalizada.get(CONF_ENTIDADE_INJECAO)
            tipo_fornecimento = entrada_normalizada.get(CONF_TIPO_FORNECIMENTO)
            if (entidade_geracao or entidade_injecao) and not tipo_fornecimento:
                errors["base"] = "tipo_fornecimento_obrigatorio"
            else:
                return self.async_create_entry(title="", data=entrada_normalizada)

        schema = TarifasEnergiaBrasilConfigFlow._build_schema(
            self._current_defaults(user_input),
            incluir_opcoes_grupo=True,
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)

    def _current_defaults(self, user_input: dict[str, Any] | None) -> dict[str, Any]:
        """Prioriza input atual, depois options, depois data original."""

        if user_input:
            return user_input
        defaults = {
            **self._config_entry.data,
            **self._config_entry.options,
        }
        if CONF_HABILITAR_GRUPO_GERACAO not in defaults:
            defaults[CONF_HABILITAR_GRUPO_GERACAO] = grupo_geracao_habilitado(defaults)
        if CONF_HABILITAR_GRUPO_TARIFA_BRANCA not in defaults:
            defaults[CONF_HABILITAR_GRUPO_TARIFA_BRANCA] = grupo_tarifa_branca_habilitado(defaults)
        return defaults
