"""Versao: 0.1.0
Criado em: 2026-04-23 09:00:00 -03:00
Criado por: Codex
Projeto/pasta: ha.ext.tarifas
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Final

import aiohttp

from ..const import ATTR_CONFIANCA_ALTA, ATTR_CONFIANCA_MEDIA
from ..models import CollectionMetadata, TributosData
from .parsers import (
    parse_celesc_tributos_html,
    parse_cemig_tributos_html,
    parse_cpfl_tributos_html,
    parse_rge_tributos_html,
)

TRIBUTOS_HTTP_TIMEOUT_SECONDS = 60


@dataclass(frozen=True, slots=True)
class TributosFallback:
    """Fallback inicial por concessionaria para pre-release."""

    pis: float
    cofins: float
    icms: float
    fonte: str
    confianca: str
    pendencias: tuple[str, ...] = ()


_TRIBUTOS_FALLBACK: Final[dict[str, TributosFallback]] = {
    "CPFL-PIRATINING": TributosFallback(
        pis=1.10,
        cofins=5.02,
        icms=12.00,
        fonte="https://www.cpfl.com.br/piratininga/pis-cofins",
        confianca=ATTR_CONFIANCA_ALTA,
    ),
    "CPFL-PAULISTA": TributosFallback(
        pis=1.12,
        cofins=5.12,
        icms=12.00,
        fonte="https://www.cpfl.com.br/paulista/pis-cofins",
        confianca=ATTR_CONFIANCA_ALTA,
    ),
    "CELESC": TributosFallback(
        pis=0.35,
        cofins=1.63,
        icms=12.00,
        fonte="https://www.celesc.com.br/tarifas-de-energia",
        confianca=ATTR_CONFIANCA_ALTA,
    ),
    "RGE SUL": TributosFallback(
        pis=1.10,
        cofins=5.02,
        icms=17.00,
        fonte="https://www.rge-rs.com.br/tributos-municipais-estaduais-e-federais",
        confianca=ATTR_CONFIANCA_MEDIA,
        pendencias=("PIS/COFINS mensal aberto ainda pendente de validacao completa.",),
    ),
    "CEMIG-D": TributosFallback(
        pis=1.10,
        cofins=5.02,
        icms=0.00,
        fonte="https://www.cemig.com.br/valores-e-tarifas/pis-cofins-e-pasep/",
        confianca=ATTR_CONFIANCA_MEDIA,
        pendencias=("ICMS aberto por faixa ainda pendente de validacao oficial.",),
    ),
}


class TributosExtractorError(Exception):
    """Falha de extracao de tributos."""


async def extract_tributos(
    session: aiohttp.ClientSession,
    concessionaria: str,
) -> tuple[TributosData, CollectionMetadata]:
    """Extrai tributos da concessionaria com fallback controlado."""

    normalized = concessionaria.strip().upper()
    fallback = _TRIBUTOS_FALLBACK.get(normalized)
    if fallback is None:
        raise TributosExtractorError(
            f"Concessionaria sem extrator validado: {concessionaria}"
        )

    now = datetime.now().astimezone()
    competencia = now.strftime("%Y-%m")
    coleta_base = CollectionMetadata(
        ultima_coleta=now.isoformat(),
        fonte=fallback.fonte,
        dataset="fonte_web_concessionaria",
        metodo_acesso="http_html",
        confianca_fonte=fallback.confianca,
        tentativas=1,
    )

    try:
        pis, cofins, icms = await _fetch_and_parse_tributos(
            session=session,
            concessionaria=normalized,
            fallback=fallback,
        )
        tributos = TributosData(
            concessionaria=normalized,
            competencia=competencia,
            pis_percent=pis,
            cofins_percent=cofins,
            icms_percent=icms,
            fonte=fallback.fonte,
            confianca=fallback.confianca,
            pendencias=list(fallback.pendencias),
        )
        return tributos, coleta_base
    except (aiohttp.ClientError, TimeoutError, ValueError) as err:
        coleta_base.usou_fallback = True
        coleta_base.mensagem_erro = f"Parser web indisponivel, fallback aplicado: {err}"
        coleta_base.tentativas = 2

    tributos = TributosData(
        concessionaria=normalized,
        competencia=competencia,
        pis_percent=fallback.pis,
        cofins_percent=fallback.cofins,
        icms_percent=fallback.icms,
        fonte=fallback.fonte,
        confianca=ATTR_CONFIANCA_MEDIA,
        pendencias=list(fallback.pendencias),
    )
    return tributos, coleta_base


async def _fetch_and_parse_tributos(
    session: aiohttp.ClientSession,
    concessionaria: str,
    fallback: TributosFallback,
) -> tuple[float, float, float]:
    """Busca HTML oficial e aplica parser especifico por concessionaria."""

    async with session.get(fallback.fonte, timeout=TRIBUTOS_HTTP_TIMEOUT_SECONDS) as response:
        response.raise_for_status()
        html = await response.text()

    if concessionaria.startswith("CPFL"):
        return parse_cpfl_tributos_html(
            raw_html=html,
            fallback_pis=fallback.pis,
            fallback_cofins=fallback.cofins,
            fallback_icms=fallback.icms,
        )

    if concessionaria == "CELESC":
        return parse_celesc_tributos_html(
            raw_html=html,
            fallback_pis=fallback.pis,
            fallback_cofins=fallback.cofins,
            fallback_icms=fallback.icms,
        )

    if concessionaria == "RGE SUL":
        return parse_rge_tributos_html(
            raw_html=html,
            fallback_pis=fallback.pis,
            fallback_cofins=fallback.cofins,
            fallback_icms=fallback.icms,
        )

    if concessionaria == "CEMIG-D":
        return parse_cemig_tributos_html(
            raw_html=html,
            fallback_pis=fallback.pis,
            fallback_cofins=fallback.cofins,
            fallback_icms=fallback.icms,
        )

    return fallback.pis, fallback.cofins, fallback.icms
