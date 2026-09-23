"""Versao: 0.3.0
Alterado em: 2026-09-23 10:57 -03:00 - Codex (ChatGPT)
Criado em: 2026-04-23 16:45:00 -03:00
Criado por: Codex
Projeto/pasta: ha.ext.tarifas
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any

from .const import (
    CONF_CONCESSIONARIA,
    CONF_TB_INTERMEDIARIO1_FIM,
    CONF_TB_INTERMEDIARIO1_INICIO,
    CONF_TB_INTERMEDIARIO2_FIM,
    CONF_TB_INTERMEDIARIO2_INICIO,
    CONF_TB_PONTA_FIM,
    CONF_TB_PONTA_INICIO,
)

POSTO_FORA_PONTA = "fora_ponta"
POSTO_INTERMEDIARIO = "intermediario"
POSTO_PONTA = "ponta"
POSTOS_TARIFA_BRANCA: tuple[str, ...] = (
    POSTO_FORA_PONTA,
    POSTO_INTERMEDIARIO,
    POSTO_PONTA,
)
LONG_INTERVAL_THRESHOLD = timedelta(hours=6)

_FIXED_HOLIDAYS: tuple[tuple[int, int], ...] = (
    (1, 1),
    (4, 21),
    (5, 1),
    (9, 7),
    (10, 12),
    (11, 2),
    (11, 15),
    (11, 20),
    (12, 25),
)

_GENERIC_FALLBACK = {
    CONF_TB_PONTA_INICIO: "18:00",
    CONF_TB_PONTA_FIM: "21:00",
    CONF_TB_INTERMEDIARIO1_INICIO: "17:00",
    CONF_TB_INTERMEDIARIO1_FIM: "18:00",
    CONF_TB_INTERMEDIARIO2_INICIO: "21:00",
    CONF_TB_INTERMEDIARIO2_FIM: "22:00",
}

JANELAS_TARIFA_BRANCA_PADRAO: dict[str, dict[str, str]] = {
    "CPFL-PIRATINING": {
        CONF_TB_PONTA_INICIO: "18:00",
        CONF_TB_PONTA_FIM: "21:00",
        CONF_TB_INTERMEDIARIO1_INICIO: "17:00",
        CONF_TB_INTERMEDIARIO1_FIM: "18:00",
        CONF_TB_INTERMEDIARIO2_INICIO: "21:00",
        CONF_TB_INTERMEDIARIO2_FIM: "22:00",
    },
    "CPFL-PAULISTA": {
        CONF_TB_PONTA_INICIO: "18:00",
        CONF_TB_PONTA_FIM: "21:00",
        CONF_TB_INTERMEDIARIO1_INICIO: "16:00",
        CONF_TB_INTERMEDIARIO1_FIM: "18:00",
        CONF_TB_INTERMEDIARIO2_INICIO: "21:00",
        CONF_TB_INTERMEDIARIO2_FIM: "22:00",
    },
    "CELESC": {
        CONF_TB_PONTA_INICIO: "18:30",
        CONF_TB_PONTA_FIM: "21:30",
        CONF_TB_INTERMEDIARIO1_INICIO: "17:30",
        CONF_TB_INTERMEDIARIO1_FIM: "18:30",
        CONF_TB_INTERMEDIARIO2_INICIO: "21:30",
        CONF_TB_INTERMEDIARIO2_FIM: "22:30",
    },
}


@dataclass(frozen=True, slots=True)
class TarifaBrancaSchedule:
    """Representa a janela efetiva usada para classificar postos horarios."""

    concessionaria: str
    ponta_inicio: time
    ponta_fim: time
    intermediario_1_inicio: time
    intermediario_1_fim: time
    intermediario_2_inicio: time
    intermediario_2_fim: time
    source: str

    def boundary_times(self) -> tuple[time, ...]:
        """Retorna horarios de fronteira ordenados para o dia util."""

        return (
            self.intermediario_1_inicio,
            self.intermediario_1_fim,
            self.ponta_inicio,
            self.ponta_fim,
            self.intermediario_2_inicio,
            self.intermediario_2_fim,
        )


def parse_time_text(value: Any) -> time:
    """Converte texto HH:MM para objeto time."""

    text = str(value or "").strip()
    parts = text.split(":")
    if len(parts) != 2:
        raise ValueError(f"Horario invalido: {value}")
    hour = int(parts[0])
    minute = int(parts[1])
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        raise ValueError(f"Horario invalido: {value}")
    return time(hour=hour, minute=minute)


def _time_to_minutes(value: time) -> int:
    return value.hour * 60 + value.minute


def _resolve_reference_timezone(instant: datetime):
    """Retorna o fuso de referencia do proprio instante, sem depender da maquina."""

    if instant.tzinfo is not None:
        return instant.tzinfo
    return instant.astimezone().tzinfo


def _as_reference_local(instant: datetime) -> datetime:
    """Normaliza instante para o fuso de referencia dele mesmo."""

    tzinfo = _resolve_reference_timezone(instant)
    if tzinfo is None:
        return instant
    if instant.tzinfo is None:
        return instant.astimezone(tzinfo)
    return instant.astimezone(tzinfo)


def _is_half_open(minute_of_day: int, start: time, end: time) -> bool:
    return _time_to_minutes(start) <= minute_of_day < _time_to_minutes(end)


def obter_janelas_padrao_tarifa_branca(concessionaria: str) -> tuple[dict[str, str], str]:
    """Retorna janela default da concessionaria ou fallback generico."""

    normalized = str(concessionaria or "").strip().upper()
    if normalized in JANELAS_TARIFA_BRANCA_PADRAO:
        return dict(JANELAS_TARIFA_BRANCA_PADRAO[normalized]), "default_concessionaria"
    return dict(_GENERIC_FALLBACK), "fallback_generico"


def resolve_tarifa_branca_schedule(
    config: Mapping[str, Any],
) -> tuple[TarifaBrancaSchedule, dict[str, Any]]:
    """Resolve horarios efetivos combinando defaults da concessionaria e overrides."""

    concessionaria = str(config.get(CONF_CONCESSIONARIA, "") or "").strip().upper()
    windows, source = obter_janelas_padrao_tarifa_branca(concessionaria)
    override_used = False

    for key in (
        CONF_TB_PONTA_INICIO,
        CONF_TB_PONTA_FIM,
        CONF_TB_INTERMEDIARIO1_INICIO,
        CONF_TB_INTERMEDIARIO1_FIM,
        CONF_TB_INTERMEDIARIO2_INICIO,
        CONF_TB_INTERMEDIARIO2_FIM,
    ):
        raw = config.get(key)
        if raw not in (None, ""):
            windows[key] = str(raw).strip()
            override_used = True

    schedule = TarifaBrancaSchedule(
        concessionaria=concessionaria,
        ponta_inicio=parse_time_text(windows[CONF_TB_PONTA_INICIO]),
        ponta_fim=parse_time_text(windows[CONF_TB_PONTA_FIM]),
        intermediario_1_inicio=parse_time_text(windows[CONF_TB_INTERMEDIARIO1_INICIO]),
        intermediario_1_fim=parse_time_text(windows[CONF_TB_INTERMEDIARIO1_FIM]),
        intermediario_2_inicio=parse_time_text(windows[CONF_TB_INTERMEDIARIO2_INICIO]),
        intermediario_2_fim=parse_time_text(windows[CONF_TB_INTERMEDIARIO2_FIM]),
        source="user_override" if override_used else source,
    )

    metadata = {
        "source": schedule.source,
        "override_used": override_used,
        "windows": windows,
    }
    return schedule, metadata


def parse_extra_holidays(value: Any) -> tuple[set[date], list[str]]:
    """Converte lista textual de feriados extras em datas."""

    if value in (None, ""):
        return set(), []

    if isinstance(value, list):
        tokens = [str(item).strip() for item in value]
    else:
        raw = str(value)
        normalized = raw.replace(";", "\n").replace(",", "\n")
        tokens = [item.strip() for item in normalized.splitlines()]

    holidays: set[date] = set()
    invalid: list[str] = []
    for token in tokens:
        if not token:
            continue
        try:
            holidays.add(date.fromisoformat(token))
        except ValueError:
            invalid.append(token)
    return holidays, invalid


def calculate_easter_date(year: int) -> date:
    """Calcula a data da Pascoa pelo algoritmo de Meeus/Jones/Butcher."""

    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    weekday_offset = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * weekday_offset) // 451
    month = (h + weekday_offset - 7 * m + 114) // 31
    day = ((h + weekday_offset - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def national_holidays_for_year(year: int) -> set[date]:
    """Retorna conjunto de feriados nacionais oficiais usados na Tarifa Branca."""

    easter = calculate_easter_date(year)
    holidays = {date(year, month, day) for month, day in _FIXED_HOLIDAYS}
    holidays.add(easter - timedelta(days=47))  # terca-feira de carnaval
    holidays.add(easter - timedelta(days=2))  # sexta-feira da paixao
    holidays.add(easter + timedelta(days=60))  # corpus christi
    return holidays


def build_holiday_calendar(
    years: Iterable[int],
    extra_holidays: Iterable[date] | None = None,
) -> set[date]:
    """Monta calendario combinado de feriados nacionais e extras."""

    calendar: set[date] = set()
    for year in years:
        calendar.update(national_holidays_for_year(year))
    if extra_holidays:
        calendar.update(extra_holidays)
    return calendar


def resolve_tarifa_branca_posto(
    instant: datetime,
    schedule: TarifaBrancaSchedule,
    holidays: set[date],
) -> str:
    """Classifica o instante em `fora_ponta`, `intermediario` ou `ponta`."""

    local = _as_reference_local(instant)
    day = local.date()
    if local.weekday() >= 5 or day in holidays:
        return POSTO_FORA_PONTA

    minute_of_day = local.hour * 60 + local.minute
    if _is_half_open(minute_of_day, schedule.ponta_inicio, schedule.ponta_fim):
        return POSTO_PONTA
    if _is_half_open(
        minute_of_day,
        schedule.intermediario_1_inicio,
        schedule.intermediario_1_fim,
    ) or _is_half_open(
        minute_of_day,
        schedule.intermediario_2_inicio,
        schedule.intermediario_2_fim,
    ):
        return POSTO_INTERMEDIARIO
    return POSTO_FORA_PONTA


def split_interval_by_midnight(
    start: datetime,
    end: datetime,
) -> list[tuple[datetime, datetime]]:
    """Quebra um intervalo em segmentos diários, respeitando meia-noite local."""

    if end.timestamp() <= start.timestamp():
        return []

    tzinfo = _resolve_reference_timezone(start)
    cursor = start
    segments: list[tuple[datetime, datetime]] = []

    while cursor.timestamp() < end.timestamp():
        local = _as_reference_local(cursor)
        next_midnight = datetime.combine(
            local.date() + timedelta(days=1),
            time.min,
            tzinfo=tzinfo,
        )
        segment_end = min(end, next_midnight, key=lambda value: value.timestamp())
        segments.append((cursor, segment_end))
        cursor = segment_end
    return segments


def split_interval_by_tarifa_branca(
    start: datetime,
    end: datetime,
    schedule: TarifaBrancaSchedule,
    holidays: set[date],
) -> list[tuple[datetime, datetime, str]]:
    """Quebra um intervalo pelas trocas de posto tarifario e meia-noite."""

    if end.timestamp() <= start.timestamp():
        return []

    tzinfo = _resolve_reference_timezone(start)
    cursor = start
    segments: list[tuple[datetime, datetime, str]] = []

    while cursor.timestamp() < end.timestamp():
        local = _as_reference_local(cursor)
        day = local.date()
        candidates = [datetime.combine(day + timedelta(days=1), time.min, tzinfo=tzinfo)]

        if day.weekday() < 5 and day not in holidays:
            for boundary in schedule.boundary_times():
                boundary_dt = datetime.combine(day, boundary, tzinfo=tzinfo)
                for fold in (0, 1):
                    candidate = boundary_dt.replace(fold=fold)
                    if cursor.timestamp() < candidate.timestamp() < end.timestamp():
                        candidates.append(candidate)

        segment_end = min([*candidates, end], key=lambda value: value.timestamp())
        segments.append(
            (
                cursor,
                segment_end,
                resolve_tarifa_branca_posto(cursor, schedule, holidays),
            )
        )
        cursor = segment_end

    return segments


def ratear_delta_tarifa_branca(
    start: datetime,
    end: datetime,
    delta_kwh: float,
    schedule: TarifaBrancaSchedule,
    holidays: set[date],
) -> tuple[dict[str, float], dict[str, Any]]:
    """Rateia delta de consumo pelos postos tarifarios com base no tempo."""

    allocations = {posto: 0.0 for posto in POSTOS_TARIFA_BRANCA}
    if delta_kwh <= 0 or end.timestamp() <= start.timestamp():
        return allocations, {
            "segment_count": 0,
            "interval_seconds": 0.0,
            "low_confidence": False,
        }

    segments = split_interval_by_tarifa_branca(start, end, schedule, holidays)
    total_seconds = end.timestamp() - start.timestamp()
    for (_, _, posto), amount in zip(segments, allocate_delta(segments, delta_kwh), strict=True):
        allocations[posto] += amount

    return allocations, {
        "segment_count": len(segments),
        "interval_seconds": total_seconds,
        "low_confidence": (end - start) >= LONG_INTERVAL_THRESHOLD,
    }


def allocate_delta(segments: list[tuple], delta_kwh: float) -> list[float]:
    """Conserve the input delta using elapsed time (including DST) and a final residue."""
    if not segments:
        raise ValueError("A nonzero delta requires an allocation segment")
    durations = [max(0.0, end.timestamp() - start.timestamp()) for start, end, *_ in segments]
    total = sum(durations)
    if total == 0:
        return [0.0] * (len(segments) - 1) + [delta_kwh]
    amounts = [delta_kwh * duration / total for duration in durations[:-1]]
    return amounts + [delta_kwh - sum(amounts)]
