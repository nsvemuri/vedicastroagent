"""Sidereal gochara ingress calendar for longevity (Swiss Ephemeris)."""

from __future__ import annotations

import re
import threading
from datetime import date, timedelta

from .chart_loader import (
    SIGN_ORDER,
    ChartDocument,
    house_from_lagna,
    parse_body_longitude_table,
    parse_jh_date,
)

GOCHARA_YEARS = 45
# Houses that matter for ayur / maraka / vitality.
_LONGEVITY_HOUSES = (1, 2, 3, 6, 7, 8, 12)
_SWE_LOCK = threading.Lock()

_NAMED_AYANAMSA = {
    "lahiri": "lahiri",
    "chitrapaksha": "lahiri",
    "chitra": "lahiri",
    "raman": "raman",
    "krishnamurti": "krishnamurti",
    "kp": "krishnamurti",
    "fagan": "fagan",
    "fagan-bradley": "fagan",
}


def parse_ayanamsa_degrees(raw: str | None) -> float | None:
    """Parse JH ayanamsa text such as '23-34-44.37' or '23:34:44' into degrees."""
    if not raw:
        return None
    text = raw.strip()
    m = re.search(r"(\d{1,2})\s*[-:]\s*(\d{1,2})\s*[-:]\s*(\d{1,2}(?:\.\d+)?)", text)
    if not m:
        try:
            return float(text.split()[0])
        except (TypeError, ValueError, IndexError):
            return None
    deg, minutes, seconds = int(m.group(1)), int(m.group(2)), float(m.group(3))
    return deg + minutes / 60.0 + seconds / 3600.0


def named_ayanamsa(raw: str | None) -> str | None:
    if not raw:
        return None
    key = re.sub(r"[^a-z]+", "", raw.strip().lower())
    for token, mode in _NAMED_AYANAMSA.items():
        if token in key:
            return mode
    return None


def format_longevity_gochara_table(
    chart: ChartDocument,
    *,
    as_of: date,
    years: int = GOCHARA_YEARS,
) -> str:
    """45-year Saturn/Jupiter/Rahu/Ketu/Mars sign-ingress table from natal Lagna."""
    try:
        import swisseph as swe
    except ImportError:
        return (
            "=== 45-YEAR GOCHARA INGRESSES ===\n"
            "NOT FOUND: install the gochara extra (pip install -e \".[gochara]\") "
            "to compute sidereal transits. On Windows that extra needs Microsoft C++ Build Tools."
        )

    bodies = parse_body_longitude_table(chart.natal_text)
    lagna = bodies.get("Lagna", {}).get("rasi")
    moon = bodies.get("Moon", {}).get("rasi")
    if not lagna:
        return (
            "=== 45-YEAR GOCHARA INGRESSES ===\n"
            "NOT FOUND: natal Lagna sign missing; cannot count transit houses."
        )

    natal_date = parse_jh_date(chart.metadata.get("date"))
    ayan_raw = chart.metadata.get("ayanamsa")
    mode_label, mode_key, ayan_deg = _resolve_ayanamsa(ayan_raw, natal_date)

    start = as_of
    try:
        end = as_of.replace(year=as_of.year + years)
    except ValueError:
        end = as_of.replace(year=as_of.year + years, day=28)
    house_notes = _house_notes(lagna, moon)
    with _SWE_LOCK:
        _configure_sidereal(swe, mode_key, natal_date, ayan_deg)
        flags = _calc_flags(swe)
        rows = _collect_ingress_rows(swe, flags, start, end, lagna, moon, house_notes)

    header = [
        f"=== 45-YEAR GOCHARA INGRESSES (sidereal; {mode_label}; mean Rahu) ===",
        f"From {start.isoformat()} through {end.isoformat()} ({years} years).",
        f"Houses counted from natal Lagna {lagna}"
        + (f"; Moon in {moon}" if moon else "")
        + ".",
        "Ingress date = first day the planet is in the new sign (noon UT).",
        "Use these dates only — do not invent gochara longitudes.",
        "Flagged rows hit natal 1/2/3/6/7/8/12, Moon sign, Sade Sati, or ashtama Shani.",
        "date        planet   sign  house  flags",
    ]
    if not rows:
        header.append("(no ingresses computed)")
        return "\n".join(header)
    header.extend(rows)
    return "\n".join(header)


def _resolve_ayanamsa(
    raw: str | None, natal_date: date | None
) -> tuple[str, str, float | None]:
    named = named_ayanamsa(raw)
    if named:
        return named.title(), named, None
    degrees = parse_ayanamsa_degrees(raw)
    if degrees is not None and natal_date is not None:
        return f"JH dump {raw.strip()} @ {natal_date.isoformat()}", "user", degrees
    if degrees is not None:
        return f"JH dump {raw.strip()} (Lahiri fallback, no natal date)", "lahiri", None
    return "Lahiri (default)", "lahiri", None


def _configure_sidereal(swe, mode_key: str, natal_date: date | None, ayan_deg: float | None) -> None:
    if mode_key == "user" and natal_date is not None and ayan_deg is not None:
        t0 = swe.julday(natal_date.year, natal_date.month, natal_date.day, 12.0)
        swe.set_sid_mode(swe.SIDM_USER, t0, ayan_deg)
        return
    mapping = {
        "lahiri": swe.SIDM_LAHIRI,
        "raman": swe.SIDM_RAMAN,
        "krishnamurti": swe.SIDM_KRISHNAMURTI,
        "fagan": swe.SIDM_FAGAN_BRADLEY,
    }
    swe.set_sid_mode(mapping.get(mode_key, swe.SIDM_LAHIRI))


def _calc_flags(swe) -> int:
    try:
        swe.calc_ut(swe.julday(2000, 1, 1, 12.0), swe.SATURN, swe.FLG_SWIEPH)
        return swe.FLG_SIDEREAL | swe.FLG_SWIEPH
    except Exception:
        return swe.FLG_SIDEREAL | swe.FLG_MOSEPH


def _collect_ingress_rows(
    swe,
    flags: int,
    start: date,
    end: date,
    lagna: str,
    moon: str | None,
    house_notes: dict[int, str],
) -> list[str]:
    planet_ids = {
        "Saturn": swe.SATURN,
        "Jupiter": swe.JUPITER,
        "Mars": swe.MARS,
        "Rahu": swe.MEAN_NODE,
    }
    rows: list[str] = []
    for name, planet_id in planet_ids.items():
        ingresses = _sign_ingresses(swe, flags, planet_id, start, end)
        for when, new_sign in ingresses:
            sign = SIGN_ORDER[new_sign]
            house = house_from_lagna(sign, lagna)
            flags_txt = house_notes.get(house or 0, "")
            if name == "Saturn" and moon:
                from_moon = house_from_lagna(sign, moon)
                extra = []
                if from_moon in {12, 1, 2}:
                    extra.append("Sade Sati (Moon)")
                if from_moon == 8:
                    extra.append("ashtama Shani (Moon)")
                if extra:
                    flags_txt = ", ".join(x for x in (flags_txt, *extra) if x)
            if name == "Mars" and house not in _LONGEVITY_HOUSES and "Moon" not in flags_txt:
                continue
            rows.append(
                f"{when.isoformat()}  {name:<7}  {sign}    H{house}    {flags_txt}".rstrip()
            )
            if name == "Rahu":
                ketu_sign = SIGN_ORDER[(new_sign + 6) % 12]
                ketu_house = house_from_lagna(ketu_sign, lagna)
                ketu_flags = house_notes.get(ketu_house or 0, "")
                rows.append(
                    f"{when.isoformat()}  {'Ketu':<7}  {ketu_sign}    H{ketu_house}    {ketu_flags}".rstrip()
                )
    rows.sort()
    return rows


def _sign_ingresses(swe, flags: int, planet_id: int, start: date, end: date) -> list[tuple[date, int]]:
    """Daily scan, then pin the first noon UT in the new sign."""
    found: list[tuple[date, int]] = []
    prev_sign = _sidereal_sign(swe, flags, planet_id, start)
    cursor = start + timedelta(days=1)
    while cursor <= end:
        sign = _sidereal_sign(swe, flags, planet_id, cursor)
        if sign != prev_sign:
            ingress = _refine_ingress_day(swe, flags, planet_id, cursor - timedelta(days=1), cursor)
            found.append((ingress, sign))
            prev_sign = sign
        cursor += timedelta(days=1)
    return found


def _refine_ingress_day(
    swe, flags: int, planet_id: int, before: date, after: date
) -> date:
    while (after - before).days > 1:
        mid = before + timedelta(days=(after - before).days // 2)
        if _sidereal_sign(swe, flags, planet_id, mid) == _sidereal_sign(
            swe, flags, planet_id, after
        ):
            after = mid
        else:
            before = mid
    return after


def _sidereal_sign(swe, flags: int, planet_id: int, when: date) -> int:
    jd = swe.julday(when.year, when.month, when.day, 12.0)
    xx, _ = swe.calc_ut(jd, planet_id, flags)
    lon = xx[0] % 360.0
    return int(lon // 30.0)


def _house_notes(lagna: str, moon: str | None) -> dict[int, str]:
    notes: dict[int, str] = {
        1: "natal Lagna",
        2: "maraka",
        3: "vitality",
        6: "roga/accident",
        7: "maraka",
        8: "ayur/8th",
        12: "loss/ayur",
    }
    if moon:
        moon_house = house_from_lagna(moon, lagna)
        if moon_house:
            existing = notes.get(moon_house, "")
            label = "Moon sign"
            notes[moon_house] = f"{existing}, {label}" if existing and label not in existing else (existing or label)
    return notes