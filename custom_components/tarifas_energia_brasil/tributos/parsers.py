"""Versao: 0.1.0
Criado em: 2026-04-23 09:00:00 -03:00
Criado por: Codex
Projeto/pasta: ha.ext.tarifas
"""

from __future__ import annotations

import html
import re
import unicodedata


def normalize_text(raw: str) -> str:
    """Normaliza texto HTML para comparacao e busca robusta."""

    no_script = re.sub(r"<script.*?>.*?</script>", " ", raw, flags=re.IGNORECASE | re.DOTALL)
    no_style = re.sub(r"<style.*?>.*?</style>", " ", no_script, flags=re.IGNORECASE | re.DOTALL)
    no_tags = re.sub(r"<[^>]+>", " ", no_style)
    unescaped = html.unescape(no_tags)
    collapsed = re.sub(r"\s+", " ", unescaped).strip()
    return collapsed


def normalize_key(text: str) -> str:
    """Remove acentos e converte para lowercase."""

    lowered = text.lower()
    lowered = unicodedata.normalize("NFKD", lowered)
    return "".join(ch for ch in lowered if not unicodedata.combining(ch))


def extract_percent_near_keywords(
    text: str,
    keywords: tuple[str, ...],
    window: int = 120,
) -> float:
    """Extrai percentual em janela textual proxima das palavras-chave."""

    norm_text = normalize_key(text)
    for keyword in keywords:
        keyword_norm = normalize_key(keyword)
        index = norm_text.find(keyword_norm)
        if index < 0:
            continue
        excerpt = norm_text[max(index - window, 0) : index + window]

        # Caso comum: "pis 1,12%" ou "cofins 5.12%"
        match_forward = re.search(
            rf"{re.escape(keyword_norm)}[^0-9]{{0,80}}(\d{{1,2}}(?:[.,]\d{{1,4}})?)\s*%",
            excerpt,
        )
        if match_forward:
            return _to_float_percent(match_forward.group(1))

        # Caso alternativo: "1,12% pis"
        match_backward = re.search(
            rf"(\d{{1,2}}(?:[.,]\d{{1,4}})?)\s*%[^0-9]{{0,80}}{re.escape(keyword_norm)}",
            excerpt,
        )
        if match_backward:
            return _to_float_percent(match_backward.group(1))
    return 0.0


def parse_cpfl_tributos_html(
    raw_html: str,
    fallback_pis: float,
    fallback_cofins: float,
    fallback_icms: float,
) -> tuple[float, float, float]:
    """Extrai tributos CPFL com fallback seguro para parser."""

    text = normalize_text(raw_html)
    pis = extract_percent_near_keywords(text, ("PIS", "PIS/PASEP"))
    cofins = extract_percent_near_keywords(text, ("COFINS",))

    guessed_pis, guessed_cofins = guess_pis_cofins_from_percent_list(text)
    return (
        pis if pis > 0 else (guessed_pis if guessed_pis > 0 else fallback_pis),
        cofins if cofins > 0 else (guessed_cofins if guessed_cofins > 0 else fallback_cofins),
        fallback_icms,
    )


def parse_celesc_tributos_html(
    raw_html: str,
    fallback_pis: float,
    fallback_cofins: float,
    fallback_icms: float,
) -> tuple[float, float, float]:
    """Extrai tributos CELESC com fallback seguro para parser."""

    text = normalize_text(raw_html)
    pis = extract_percent_near_keywords(text, ("PIS", "PIS/PASEP"))
    cofins = extract_percent_near_keywords(text, ("COFINS",))

    # A CELESC normalmente traz tabela de aliquota por faixa.
    # Para manter estabilidade do parser, usa fallback caso nao encontre ICMS com seguranca.
    icms = extract_percent_near_keywords(
        text,
        ("ICMS", "aliquota de icms", "tributos"),
    )

    return (
        pis if pis > 0 else fallback_pis,
        cofins if cofins > 0 else fallback_cofins,
        icms if icms > 0 else fallback_icms,
    )


def _to_float_percent(value: str) -> float:
    """Converte string percentual para float."""

    cleaned = value.strip().replace(",", ".")
    return float(cleaned)


def guess_pis_cofins_from_percent_list(text: str) -> tuple[float, float]:
    """Estima PIS/COFINS a partir da lista de percentuais candidatos."""

    raw = re.findall(r"(\d{1,2}(?:[.,]\d{1,4})?)\s*%", normalize_key(text))
    values: list[float] = []
    for item in raw:
        try:
            parsed = _to_float_percent(item)
        except ValueError:
            continue
        if 0 < parsed < 10:
            values.append(parsed)

    unique_sorted = sorted(set(values))
    if len(unique_sorted) >= 2:
        return unique_sorted[0], unique_sorted[1]
    if len(unique_sorted) == 1:
        return unique_sorted[0], 0.0
    return 0.0, 0.0
