"""Versao: 0.1.0
Criado em: 2026-04-22 21:41:36 -03:00
Criado por: Codex
Projeto/pasta: ha.ext.tarifas
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from homeassistant.const import Platform

DOMAIN = "tarifas_energia_brasil"
NAME = "Tarifas Energia Brasil"
VERSION = "0.1.0"

PLATFORMS: list[Platform] = [Platform.SENSOR]

CONF_CONCESSIONARIA = "concessionaria"
CONF_READING_DAY = "dia_leitura_reset_mensal"
CONF_UPDATE_HOURS = "frequencia_atualizacao_horas"
CONF_ANEEL_METHOD = "meio_prioritario_aneel"
CONF_CONSUMPTION_ENTITY = "entidade_consumo_kwh"
CONF_GENERATION_ENTITY = "entidade_geracao_kwh"
CONF_INJECTION_ENTITY = "entidade_injecao_kwh"
CONF_SUPPLY_TYPE = "tipo_fornecimento"
CONF_BREAKDOWNS = "quebras_calculo"
CONF_ENABLE_GENERATION_GROUP = "habilitar_grupo_geracao"
CONF_ENABLE_TARIFA_BRANCA_GROUP = "habilitar_grupo_tarifa_branca"
CONF_TB_PONTA_START = "tarifa_branca_inicio_ponta"
CONF_TB_PONTA_END = "tarifa_branca_fim_ponta"
CONF_TB_INTERMEDIATE1_START = "tarifa_branca_inicio_intermediario_1"
CONF_TB_INTERMEDIATE1_END = "tarifa_branca_fim_intermediario_1"
CONF_TB_INTERMEDIATE2_START = "tarifa_branca_inicio_intermediario_2"
CONF_TB_INTERMEDIATE2_END = "tarifa_branca_fim_intermediario_2"
CONF_TB_EXTRA_HOLIDAYS = "tarifa_branca_feriados_extras"

BREAKDOWN_DAILY = "daily"
BREAKDOWN_WEEKLY = "weekly"
BREAKDOWN_MONTHLY = "monthly"
VALID_BREAKDOWNS: tuple[str, ...] = (
    BREAKDOWN_DAILY,
    BREAKDOWN_WEEKLY,
    BREAKDOWN_MONTHLY,
)

SUPPLY_MONOPHASE = "monofasico"
SUPPLY_BIPHASE = "bifasico"
SUPPLY_TRIPHASE = "trifasico"
SUPPORTED_SUPPLY_TYPES: tuple[str, ...] = (
    SUPPLY_MONOPHASE,
    SUPPLY_BIPHASE,
    SUPPLY_TRIPHASE,
)

ANEEL_METHOD_DATASTORE_SEARCH = "datastore_search"
ANEEL_METHOD_DATASTORE_SEARCH_SQL = "datastore_search_sql"
ANEEL_METHOD_CSV_XML = "csv_xml"
SUPPORTED_ANEEL_METHODS: tuple[str, ...] = (
    ANEEL_METHOD_DATASTORE_SEARCH,
    ANEEL_METHOD_DATASTORE_SEARCH_SQL,
    ANEEL_METHOD_CSV_XML,
)

DEFAULT_READING_DAY = 1
DEFAULT_UPDATE_HOURS = 24
DEFAULT_ANEEL_METHOD = ANEEL_METHOD_DATASTORE_SEARCH
DEFAULT_BREAKDOWNS: list[str] = [BREAKDOWN_DAILY, BREAKDOWN_MONTHLY]
DEFAULT_ENABLE_GENERATION_GROUP = False
DEFAULT_ENABLE_TARIFA_BRANCA_GROUP = False

ATTR_CONFIANCA_ALTA = "alta"
ATTR_CONFIANCA_MEDIA = "media"
ATTR_CONFIANCA_BAIXA = "baixa"

ENTITY_GROUP_REGULAR = "regular"
ENTITY_GROUP_GENERATION = "geracao"
ENTITY_GROUP_TARIFA_BRANCA = "tarifa_branca"


@dataclass(frozen=True, slots=True)
class ConcessionariaInfo:
    """Descricao resumida de suporte por concessionaria."""

    slug: str
    nome: str
    suportada: bool
    extrator_tributos: str
    confianca: str
    observacao: str


SUPPORTED_CONCESSIONARIAS: Mapping[str, ConcessionariaInfo] = {
    "CPFL-PIRATINING": ConcessionariaInfo(
        slug="cpfl_piratining",
        nome="CPFL-PIRATINING",
        suportada=True,
        extrator_tributos="cpfl_piratining",
        confianca=ATTR_CONFIANCA_ALTA,
        observacao="MVP obrigatorio da release inicial.",
    ),
    "CPFL-PAULISTA": ConcessionariaInfo(
        slug="cpfl_paulista",
        nome="CPFL-PAULISTA",
        suportada=True,
        extrator_tributos="cpfl_paulista",
        confianca=ATTR_CONFIANCA_ALTA,
        observacao="Candidata inicial com extracao validada.",
    ),
    "CELESC": ConcessionariaInfo(
        slug="celesc",
        nome="CELESC",
        suportada=True,
        extrator_tributos="celesc",
        confianca=ATTR_CONFIANCA_ALTA,
        observacao="Candidata inicial com extracao validada.",
    ),
    "RGE SUL": ConcessionariaInfo(
        slug="rge_sul",
        nome="RGE SUL",
        suportada=False,
        extrator_tributos="rge_sul",
        confianca=ATTR_CONFIANCA_MEDIA,
        observacao="Extracao parcial de PIS/COFINS.",
    ),
    "CEMIG-D": ConcessionariaInfo(
        slug="cemig_d",
        nome="CEMIG-D",
        suportada=False,
        extrator_tributos="cemig_d",
        confianca=ATTR_CONFIANCA_MEDIA,
        observacao="Pendencia de ICMS aberto por faixa.",
    ),
    "ENEL SP": ConcessionariaInfo(
        slug="enel_sp",
        nome="ENEL SP",
        suportada=False,
        extrator_tributos="enel_sp",
        confianca=ATTR_CONFIANCA_MEDIA,
        observacao="Pendencia em PIS/COFINS mensal aberto.",
    ),
}


def get_supported_concessionarias_for_flow() -> list[str]:
    """Retorna somente concessionarias prontas para uso no fluxo."""

    return sorted(
        [item.nome for item in SUPPORTED_CONCESSIONARIAS.values() if item.suportada]
    )


def get_aneel_method_fallback_order(priority_method: str) -> list[str]:
    """Monta ordem de tentativa respeitando prioridade do usuario."""

    if priority_method not in SUPPORTED_ANEEL_METHODS:
        priority_method = DEFAULT_ANEEL_METHOD

    return [priority_method, *[m for m in SUPPORTED_ANEEL_METHODS if m != priority_method]]


def parse_bool(value: object, default: bool) -> bool:
    """Converte valores comuns para bool de forma tolerante."""

    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "sim", "yes", "on"}:
            return True
        if normalized in {"0", "false", "nao", "não", "no", "off"}:
            return False
    return default


def is_generation_group_enabled(config: Mapping[str, object]) -> bool:
    """Resolve se o grupo de geracao deve ficar habilitado."""

    if CONF_ENABLE_GENERATION_GROUP in config:
        return parse_bool(
            config.get(CONF_ENABLE_GENERATION_GROUP),
            DEFAULT_ENABLE_GENERATION_GROUP,
        )
    return bool(config.get(CONF_GENERATION_ENTITY) or config.get(CONF_INJECTION_ENTITY))


def is_tarifa_branca_group_enabled(config: Mapping[str, object]) -> bool:
    """Resolve se o grupo de tarifa branca deve ficar habilitado."""

    if CONF_ENABLE_TARIFA_BRANCA_GROUP in config:
        return parse_bool(
            config.get(CONF_ENABLE_TARIFA_BRANCA_GROUP),
            DEFAULT_ENABLE_TARIFA_BRANCA_GROUP,
        )
    # Compatibilidade com entries antigas: manter comportamento atual ate o
    # usuario optar explicitamente por esconder o grupo.
    return True
