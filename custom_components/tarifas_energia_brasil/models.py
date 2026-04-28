"""Versao: 0.1.0
Criado em: 2026-04-22 21:41:36 -03:00
Criado por: Codex
Projeto/pasta: ha.ext.tarifas
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class MetadadosColeta:
    """Metadados de coleta para diagnostico e atributos de entidade."""

    ultima_coleta: str | None = None
    fonte: str | None = None
    dataset: str | None = None
    resource_id: str | None = None
    metodo_acesso: str | None = None
    usou_fallback: bool = False
    tentativas: int = 1
    mensagem_erro: str | None = None
    confianca_fonte: str | None = None
    vigencia_inicio: str | None = None
    vigencia_fim: str | None = None

    def como_atributos(self) -> dict[str, Any]:
        """Converte os metadados para atributos sem valores nulos."""

        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass(slots=True)
class DadosTributos:
    """Representa aliquotas de tributos da concessionaria."""

    concessionaria: str
    competencia: str
    pis_percent: float
    cofins_percent: float
    icms_percent: float
    fonte: str
    confianca: str
    erros: list[str] = field(default_factory=list)
    pendencias: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DadosTarifaPosto:
    """Valores de TE/TUSD e tarifas por posto/modalidade."""

    te_r_kwh: float = 0.0
    tusd_r_kwh: float = 0.0
    tarifa_bruta_r_kwh: float = 0.0
    tarifa_final_r_kwh: float = 0.0


@dataclass(slots=True)
class DadosTarifa:
    """Conjunto de tarifas da modalidade convencional e branca."""

    convencional: DadosTarifaPosto
    branca_fora_ponta: DadosTarifaPosto
    branca_intermediario: DadosTarifaPosto
    branca_ponta: DadosTarifaPosto


@dataclass(slots=True)
class DadosBandeira:
    """Representa a bandeira tarifaria vigente e seu adicional."""

    bandeira: str
    adicional_r_kwh: float
    competencia: str


@dataclass(slots=True)
class DadosFioB:
    """Representa o valor bruto e final do componente Fio B."""

    bruto_r_kwh: float
    final_r_kwh: float
    ano_percentual: int
    percentual_aplicado: float


@dataclass(slots=True)
class ResultadoCalculo:
    """Valores finais publicados nos sensores da integracao."""

    atualizado_em: datetime
    concessionaria: str
    valores: dict[str, float | str | bool | None]
    coletas_por_chave: dict[str, MetadadosColeta]
    diagnosticos: dict[str, Any]
