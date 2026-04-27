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

    def describe(self) -> str:
        """Descreve a faixa de consumo em texto curto."""

        if self.max_kwh_inclusive is None:
            return f"kWh >= {self.min_kwh_inclusive:.6f}"
        return (
            f"{self.min_kwh_inclusive:.6f} <= kWh <= "
            f"{self.max_kwh_inclusive:.6f}"
        )


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


def build_icms_calculation_attributes(
    concessionaria: str,
    consumo_mensal_kwh: float,
    fallback_icms_percent: float,
    icms_aplicado_percent: float,
    icms_source: str,
    consumo_faturavel_kwh: float | None = None,
    disponibilidade_minima_kwh: float | None = None,
) -> dict[str, float | str | list[str]]:
    """Monta atributos explicativos do ICMS conforme regra da concessionaria."""

    normalized = (concessionaria or "").strip().upper()
    faixa_kwh = (
        consumo_mensal_kwh
        if consumo_faturavel_kwh is None
        else consumo_faturavel_kwh
    )
    rules = ICMS_RULES_BY_CONCESSIONARIA.get(normalized)
    attrs: dict[str, float | str | list[str]] = {
        "icms_consumo_mensal_kwh": consumo_mensal_kwh,
        "icms_consumo_faturavel_kwh": faixa_kwh,
        "icms_fallback_percent": fallback_icms_percent,
        "icms_source": icms_source,
    }
    if disponibilidade_minima_kwh is not None:
        attrs["icms_disponibilidade_minima_kwh"] = disponibilidade_minima_kwh

    if not rules:
        attrs["icms_calculo_expressao"] = (
            f"{normalized or 'Concessionaria'} sem regra de faixa cadastrada; "
            f"ICMS aplicado = fallback da fonte de tributos "
            f"{fallback_icms_percent:.2f}%."
        )
        attrs["icms_regra_faixas"] = []
        return attrs

    attrs["icms_regra_faixas"] = [
        f"{rule.describe()} => {rule.icms_percent:.2f}%"
        for rule in rules
    ]

    if icms_source == "fallback_bootstrap_sem_historico":
        attrs["icms_calculo_expressao"] = (
            "Sem historico de consumo mensal apurado no bootstrap; "
            f"ICMS aplicado = fallback da fonte de tributos "
            f"{fallback_icms_percent:.2f}%."
        )
        return attrs

    if icms_source.startswith("fallback"):
        attrs["icms_calculo_expressao"] = (
            f"Nao foi possivel resolver faixa para consumo mensal "
            f"{consumo_mensal_kwh:.3f} kWh e base faturavel "
            f"{faixa_kwh:.3f} kWh; ICMS aplicado = fallback "
            f"{fallback_icms_percent:.2f}%."
        )
        return attrs

    matching_rule = next(
        (rule for rule in rules if rule.matches(faixa_kwh)),
        None,
    )
    if matching_rule is None:
        attrs["icms_calculo_expressao"] = (
            f"Base faturavel ICMS {faixa_kwh:.3f} kWh, a partir do consumo "
            f"mensal apurado {consumo_mensal_kwh:.3f} kWh, nao encontrou "
            f"faixa cadastrada; ICMS aplicado = {icms_aplicado_percent:.2f}%."
        )
        return attrs

    attrs["icms_calculo_expressao"] = (
        f"Consumo mensal apurado {consumo_mensal_kwh:.3f} kWh; base faturavel "
        f"para ICMS {faixa_kwh:.3f} kWh entra na faixa "
        f"{matching_rule.describe()} da concessionaria {normalized}; "
        f"ICMS aplicado = {matching_rule.icms_percent:.2f}%."
    )
    return attrs
