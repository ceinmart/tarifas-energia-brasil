"""Versao: 0.1.0
Criado em: 2026-04-22 21:41:36 -03:00
Criado por: Codex
Projeto/pasta: ha.ext.tarifas
"""

from __future__ import annotations

from typing import Any

try:
    from .const import SUPPLY_BIPHASE, SUPPLY_MONOPHASE, SUPPLY_TRIPHASE
except ImportError:
    # Permite execucao isolada do modulo em testes unitarios sem package context.
    SUPPLY_MONOPHASE = "monofasico"
    SUPPLY_BIPHASE = "bifasico"
    SUPPLY_TRIPHASE = "trifasico"

FIO_B_TRANSICAO_POR_ANO: dict[int, float] = {
    2023: 0.15,
    2024: 0.30,
    2025: 0.45,
    2026: 0.60,
    2027: 0.75,
    2028: 0.90,
}


def safe_float(value: Any, default: float = 0.0) -> float:
    """Converte valores em float aceitando strings com virgula."""

    if value is None:
        return default

    if isinstance(value, (float, int)):
        return float(value)

    text_value = str(value).strip()
    if not text_value:
        return default

    if "," in text_value and "." in text_value:
        text_value = text_value.replace(".", "").replace(",", ".")
    elif "," in text_value:
        text_value = text_value.replace(",", ".")
    try:
        return float(text_value)
    except (TypeError, ValueError):
        return default


def mwh_to_kwh(valor_r_mwh: float) -> float:
    """Converte de R$/MWh para R$/kWh."""

    return valor_r_mwh / 1000.0


def percent_to_decimal(percent: float) -> float:
    """Converte percentual para decimal (ex: 12 -> 0.12)."""

    return percent / 100.0


def aplicar_tributos_por_dentro(
    valor_sem_tributos: float,
    pis_decimal: float,
    cofins_decimal: float,
    icms_decimal: float,
) -> float:
    """Aplica tributos por dentro conforme formula da documentacao."""

    soma_aliquotas = pis_decimal + cofins_decimal + icms_decimal
    if soma_aliquotas >= 1:
        raise ValueError("Soma de aliquotas invalida para calculo por dentro.")
    return valor_sem_tributos / (1 - soma_aliquotas)


def calcular_tarifa_convencional(
    te_convencional_r_kwh: float,
    tusd_convencional_r_kwh: float,
    pis_percent: float,
    cofins_percent: float,
    icms_percent: float,
) -> tuple[float, float]:
    """Calcula tarifa convencional bruta e final."""

    tarifa_bruta = te_convencional_r_kwh + tusd_convencional_r_kwh
    tarifa_final = aplicar_tributos_por_dentro(
        tarifa_bruta,
        percent_to_decimal(pis_percent),
        percent_to_decimal(cofins_percent),
        percent_to_decimal(icms_percent),
    )
    return tarifa_bruta, tarifa_final


def calcular_tarifa_branca_por_posto(
    te_por_posto_r_kwh: dict[str, float],
    tusd_por_posto_r_kwh: dict[str, float],
    pis_percent: float,
    cofins_percent: float,
    icms_percent: float,
) -> dict[str, dict[str, float]]:
    """Calcula tarifa branca bruta/final por posto tarifario."""

    resultado: dict[str, dict[str, float]] = {}
    for posto in ("fora_ponta", "intermediario", "ponta"):
        te = te_por_posto_r_kwh.get(posto, 0.0)
        tusd = tusd_por_posto_r_kwh.get(posto, 0.0)
        bruta = te + tusd
        final = aplicar_tributos_por_dentro(
            bruta,
            percent_to_decimal(pis_percent),
            percent_to_decimal(cofins_percent),
            percent_to_decimal(icms_percent),
        )
        resultado[posto] = {
            "te_r_kwh": te,
            "tusd_r_kwh": tusd,
            "tarifa_bruta_r_kwh": bruta,
            "tarifa_final_r_kwh": final,
        }
    return resultado


def disponibilidade_minima_kwh(tipo_fornecimento: str) -> float:
    """Retorna limite minimo em kWh para custo de disponibilidade."""

    normalized = (tipo_fornecimento or "").lower().strip()
    if normalized == SUPPLY_MONOPHASE:
        return 30.0
    if normalized == SUPPLY_BIPHASE:
        return 50.0
    if normalized == SUPPLY_TRIPHASE:
        return 100.0
    return 30.0


def calcular_valor_disponibilidade(
    tipo_fornecimento: str,
    tarifa_convencional_final_r_kwh: float,
) -> float:
    """Calcula valor monetario do custo de disponibilidade."""

    return (
        disponibilidade_minima_kwh(tipo_fornecimento)
        * tarifa_convencional_final_r_kwh
    )


def percentual_fio_b_por_ano(ano: int) -> float:
    """Retorna percentual de transicao do Fio B para o ano informado."""

    if ano >= 2029:
        return 1.0
    return FIO_B_TRANSICAO_POR_ANO.get(ano, 1.0)


def calcular_fio_b_bruto(tusd_fio_b_r_mwh: float) -> float:
    """Converte valor bruto do Fio B de R$/MWh para R$/kWh."""

    return mwh_to_kwh(tusd_fio_b_r_mwh)


def calcular_fio_b_final(
    fio_b_bruto_r_kwh: float,
    ano: int,
    pis_percent: float,
    cofins_percent: float,
    icms_percent: float,
) -> float:
    """Aplica transicao e tributos por dentro ao Fio B bruto."""

    valor_com_transicao = fio_b_bruto_r_kwh * percentual_fio_b_por_ano(ano)
    return aplicar_tributos_por_dentro(
        valor_com_transicao,
        percent_to_decimal(pis_percent),
        percent_to_decimal(cofins_percent),
        percent_to_decimal(icms_percent),
    )


def calcular_valor_bandeira(
    kwh_faturado: float,
    adicional_bandeira_r_kwh: float,
) -> float:
    """Calcula incidencia monetaria da bandeira tarifaria."""

    return kwh_faturado * adicional_bandeira_r_kwh


def calcular_valor_conta_regular(
    kwh_periodo: float,
    tarifa_convencional_final_r_kwh: float,
    adicional_bandeira_r_kwh: float = 0.0,
) -> float:
    """Calcula valor de conta para consumo regular no periodo."""

    return kwh_periodo * (tarifa_convencional_final_r_kwh + adicional_bandeira_r_kwh)


def calcular_valor_faturado_com_disponibilidade(
    valor_disponibilidade: float,
    valor_calculado: float,
) -> float:
    """Aplica regra de maximo entre disponibilidade e valor calculado."""

    return max(valor_disponibilidade, valor_calculado)


def calcular_scee_simplificado(
    consumo_kwh: float,
    geracao_kwh: float,
    credito_entrada_kwh: float,
    tarifa_convencional_final_r_kwh: float,
    fio_b_final_r_kwh: float,
    valor_disponibilidade: float,
) -> dict[str, float]:
    """Modelo operacional inicial para valor com geracao/SCEE."""

    energia_disponivel_para_compensar_kwh = max(geracao_kwh, 0.0) + max(
        credito_entrada_kwh, 0.0
    )
    energia_compensada_kwh = min(max(consumo_kwh, 0.0), energia_disponivel_para_compensar_kwh)
    energia_nao_compensada_kwh = max(consumo_kwh - energia_compensada_kwh, 0.0)

    valor_energia_nao_compensada = energia_nao_compensada_kwh * tarifa_convencional_final_r_kwh
    valor_fio_b_compensada = energia_compensada_kwh * fio_b_final_r_kwh
    valor_consumo_scee = valor_energia_nao_compensada + valor_fio_b_compensada
    valor_consumo_faturado = calcular_valor_faturado_com_disponibilidade(
        valor_disponibilidade, valor_consumo_scee
    )
    credito_gerado_kwh = max(energia_disponivel_para_compensar_kwh - energia_compensada_kwh, 0.0)

    return {
        "energia_disponivel_para_compensar_kwh": energia_disponivel_para_compensar_kwh,
        "energia_compensada_kwh": energia_compensada_kwh,
        "energia_nao_compensada_kwh": energia_nao_compensada_kwh,
        "valor_energia_nao_compensada": valor_energia_nao_compensada,
        "valor_fio_b_compensada": valor_fio_b_compensada,
        "valor_consumo_scee": valor_consumo_scee,
        "valor_consumo_faturado": valor_consumo_faturado,
        "credito_gerado_kwh": credito_gerado_kwh,
    }


def calcular_scee_creditos_prioritarios(
    consumo_kwh: float,
    geracao_kwh: float,
    credito_entrada_kwh: float,
    tarifa_convencional_final_r_kwh: float,
    fio_b_final_r_kwh: float,
    valor_disponibilidade: float,
) -> dict[str, float]:
    """Calcula SCEE consumindo creditos antigos antes da geracao nova."""

    consumo = max(consumo_kwh, 0.0)
    geracao = max(geracao_kwh, 0.0)
    credito_entrada = max(credito_entrada_kwh, 0.0)

    energia_disponivel = credito_entrada + geracao
    energia_compensada = min(consumo, energia_disponivel)

    credito_consumido = min(credito_entrada, energia_compensada)
    geracao_consumida = min(geracao, max(energia_compensada - credito_consumido, 0.0))
    energia_nao_compensada = max(consumo - energia_compensada, 0.0)

    valor_energia_nao_compensada = energia_nao_compensada * tarifa_convencional_final_r_kwh
    valor_fio_b_compensada = energia_compensada * fio_b_final_r_kwh
    valor_consumo_scee = valor_energia_nao_compensada + valor_fio_b_compensada
    valor_consumo_faturado = calcular_valor_faturado_com_disponibilidade(
        valor_disponibilidade, valor_consumo_scee
    )

    credito_gerado = max(geracao - geracao_consumida, 0.0)

    return {
        "energia_disponivel_para_compensar_kwh": energia_disponivel,
        "energia_compensada_kwh": energia_compensada,
        "energia_nao_compensada_kwh": energia_nao_compensada,
        "credito_consumido_kwh": credito_consumido,
        "geracao_consumida_kwh": geracao_consumida,
        "valor_energia_nao_compensada": valor_energia_nao_compensada,
        "valor_fio_b_compensada": valor_fio_b_compensada,
        "valor_consumo_scee": valor_consumo_scee,
        "valor_consumo_faturado": valor_consumo_faturado,
        "credito_gerado_kwh": credito_gerado,
    }
