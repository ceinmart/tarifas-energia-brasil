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
VERSION = "0.1.9"

PLATFORMS: list[Platform] = [Platform.SENSOR]

CONF_CONCESSIONARIA = "concessionaria"
CONF_DIA_LEITURA = "dia_leitura_reset_mensal"
CONF_HORAS_ATUALIZACAO = "frequencia_atualizacao_horas"
CONF_METODO_ANEEL = "meio_prioritario_aneel"
CONF_ENTIDADE_CONSUMO = "entidade_consumo_kwh"
CONF_ENTIDADE_GERACAO = "entidade_geracao_kwh"
CONF_ENTIDADE_INJECAO = "entidade_injecao_kwh"
CONF_TIPO_FORNECIMENTO = "tipo_fornecimento"
CONF_QUEBRAS_CALCULO = "quebras_calculo"
CONF_HABILITAR_GRUPO_GERACAO = "habilitar_grupo_geracao"
CONF_HABILITAR_GRUPO_TARIFA_BRANCA = "habilitar_grupo_tarifa_branca"
CONF_TB_PONTA_INICIO = "tarifa_branca_inicio_ponta"
CONF_TB_PONTA_FIM = "tarifa_branca_fim_ponta"
CONF_TB_INTERMEDIARIO1_INICIO = "tarifa_branca_inicio_intermediario_1"
CONF_TB_INTERMEDIARIO1_FIM = "tarifa_branca_fim_intermediario_1"
CONF_TB_INTERMEDIARIO2_INICIO = "tarifa_branca_inicio_intermediario_2"
CONF_TB_INTERMEDIARIO2_FIM = "tarifa_branca_fim_intermediario_2"
CONF_TB_FERIADOS_EXTRAS = "tarifa_branca_feriados_extras"

QUEBRA_DIARIA = "diario"
QUEBRA_SEMANAL = "semanal"
QUEBRA_MENSAL = "mensal"
QUEBRAS_VALIDAS: tuple[str, ...] = (
    QUEBRA_DIARIA,
    QUEBRA_SEMANAL,
    QUEBRA_MENSAL,
)

FORNECIMENTO_MONOFASICO = "monofasico"
FORNECIMENTO_BIFASICO = "bifasico"
FORNECIMENTO_TRIFASICO = "trifasico"
TIPOS_FORNECIMENTO_SUPORTADOS: tuple[str, ...] = (
    FORNECIMENTO_MONOFASICO,
    FORNECIMENTO_BIFASICO,
    FORNECIMENTO_TRIFASICO,
)

METODO_ANEEL_BUSCA_DADOS = "datastore_search"
METODO_ANEEL_BUSCA_DADOS_SQL = "datastore_search_sql"
METODO_ANEEL_CSV_XML = "csv_xml"
METODOS_ANEEL_SUPORTADOS: tuple[str, ...] = (
    METODO_ANEEL_BUSCA_DADOS,
    METODO_ANEEL_BUSCA_DADOS_SQL,
    METODO_ANEEL_CSV_XML,
)

DIA_LEITURA_PADRAO = 1
HORAS_ATUALIZACAO_PADRAO = 24
METODO_ANEEL_PADRAO = METODO_ANEEL_BUSCA_DADOS
QUEBRAS_PADRAO: list[str] = [QUEBRA_DIARIA, QUEBRA_MENSAL]
HABILITAR_GRUPO_GERACAO_PADRAO = False
HABILITAR_GRUPO_TARIFA_BRANCA_PADRAO = False

ATTR_CONFIANCA_ALTA = "alta"
ATTR_CONFIANCA_MEDIA = "media"
ATTR_CONFIANCA_BAIXA = "baixa"

GRUPO_ENTIDADE_REGULAR = "regular"
GRUPO_ENTIDADE_GERACAO = "geracao"
GRUPO_ENTIDADE_TARIFA_BRANCA = "tarifa_branca"


@dataclass(frozen=True, slots=True)
class ConcessionariaInfo:
    """Descricao resumida de suporte por concessionaria."""

    slug: str
    nome: str
    suportada: bool
    extrator_tributos: str
    confianca: str
    observacao: str


CONCESSIONARIAS_SUPORTADAS: Mapping[str, ConcessionariaInfo] = {
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


def obter_concessionarias_suportadas_para_fluxo() -> list[str]:
    """Retorna somente concessionarias prontas para uso no fluxo."""

    return sorted([item.nome for item in CONCESSIONARIAS_SUPORTADAS.values() if item.suportada])


def obter_ordem_alternativa_metodo_aneel(priority_method: str) -> list[str]:
    """Monta ordem de tentativa respeitando prioridade do usuario."""

    if priority_method not in METODOS_ANEEL_SUPORTADOS:
        priority_method = METODO_ANEEL_PADRAO

    return [priority_method, *[m for m in METODOS_ANEEL_SUPORTADOS if m != priority_method]]


def converter_bool(value: object, default: bool) -> bool:
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


def grupo_geracao_habilitado(config: Mapping[str, object]) -> bool:
    """Resolve se o grupo de geracao deve ficar habilitado."""

    if CONF_HABILITAR_GRUPO_GERACAO in config:
        return converter_bool(
            config.get(CONF_HABILITAR_GRUPO_GERACAO),
            HABILITAR_GRUPO_GERACAO_PADRAO,
        )
    return bool(config.get(CONF_ENTIDADE_GERACAO) or config.get(CONF_ENTIDADE_INJECAO))


def grupo_tarifa_branca_habilitado(config: Mapping[str, object]) -> bool:
    """Resolve se o grupo de tarifa branca deve ficar habilitado."""

    if CONF_HABILITAR_GRUPO_TARIFA_BRANCA in config:
        return converter_bool(
            config.get(CONF_HABILITAR_GRUPO_TARIFA_BRANCA),
            HABILITAR_GRUPO_TARIFA_BRANCA_PADRAO,
        )
    # Compatibilidade com entries antigas: manter comportamento atual ate o
    # usuario optar explicitamente por esconder o grupo.
    return True
