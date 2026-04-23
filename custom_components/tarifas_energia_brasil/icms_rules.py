"""Versao: 0.1.0
Criado em: 2026-04-23 10:20:00 -03:00
Criado por: Codex
Projeto/pasta: ha.ext.tarifas
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class IcmsRangeRule:
    """Regra de faixa para aliquota de ICMS por consumo em kWh."""

    min_kwh_inclusive: float
    max_kwh_inclusive: float | None
    icms_percent: float

    def matches(self, kwh: float) -> bool:
        """Retorna se o consumo está dentro da faixa."""

        if kwh < self.min_kwh_inclusive:
            return False
        if self.max_kwh_inclusive is None:
            return True
        return kwh <= self.max_kwh_inclusive


ICMS_RULES_BY_CONCESSIONARIA: dict[str, list[IcmsRangeRule]] = {
    # SP residencial (documentacao base): 0-90 isento; 91-200 12%; >200 18%
    "CPFL-PIRATINING": [
        IcmsRangeRule(0, 90, 0.0),
        IcmsRangeRule(90.000001, 200, 12.0),
        IcmsRangeRule(200.000001, None, 18.0),
    ],
    "CPFL-PAULISTA": [
        IcmsRangeRule(0, 90, 0.0),
        IcmsRangeRule(90.000001, 200, 12.0),
        IcmsRangeRule(200.000001, None, 18.0),
    ],
    "ENEL SP": [
        IcmsRangeRule(0, 90, 0.0),
        IcmsRangeRule(90.000001, 200, 12.0),
        IcmsRangeRule(200.000001, None, 18.0),
    ],
    # CELESC residencial (documentacao base): ate 150 12%; acima 17%
    "CELESC": [
        IcmsRangeRule(0, 150, 12.0),
        IcmsRangeRule(150.000001, None, 17.0),
    ],
    # RGE residencial (documentacao base): ate 50 12%; acima 17%
    "RGE SUL": [
        IcmsRangeRule(0, 50, 12.0),
        IcmsRangeRule(50.000001, None, 17.0),
    ],
}


def resolve_icms_percent(
    concessionaria: str,
    consumo_mensal_kwh: float,
    fallback_icms_percent: float,
) -> tuple[float, str]:
    """Resolve aliquota ICMS aplicada conforme faixa ou fallback."""

    normalized = (concessionaria or "").strip().upper()
    rules = ICMS_RULES_BY_CONCESSIONARIA.get(normalized)
    if not rules:
        return fallback_icms_percent, "fallback_sem_regra"

    if consumo_mensal_kwh < 0:
        return fallback_icms_percent, "fallback_consumo_invalido"

    for rule in rules:
        if rule.matches(consumo_mensal_kwh):
            return rule.icms_percent, "regra_faixa_consumo"

    return fallback_icms_percent, "fallback_sem_match"
