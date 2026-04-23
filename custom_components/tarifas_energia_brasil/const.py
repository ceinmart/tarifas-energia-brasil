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
VERSION = "0.1.0-alpha.1"

PLATFORMS: list[Platform] = [Platform.SENSOR]

CONF_CONCESSIONARIA = "concessionaria"
CONF_READING_DAY = "dia_leitura_reset_mensal"
CONF_UPDATE_HOURS = "frequencia_atualizacao_horas"
CONF_ANEEL_METHOD = "meio_prioritario_aneel"
CONF_CONSUMPTION_ENTITY = "entidade_consumo_kwh"
CONF_GENERATION_ENTITY = "entidade_geracao_kwh"
CONF_SUPPLY_TYPE = "tipo_fornecimento"
CONF_BREAKDOWNS = "quebras_calculo"

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

ATTR_CONFIANCA_ALTA = "alta"
ATTR_CONFIANCA_MEDIA = "media"
ATTR_CONFIANCA_BAIXA = "baixa"


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
        observacao="MVP obrigatorio da pre-release.",
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
