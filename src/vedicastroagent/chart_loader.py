"""Load and section Jagannatha Hora natal chart text / RTF exports."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


TOPIC_SECTION_HINTS: dict[str, list[str]] = {
    "career": [
        "Rasi",
        "D-10",
        "Dasamsa",
        "D-1",
        "Shadbala",
        "Ashtakavarga",
        "Vimsottari",
        "Narayana Dasa",
        "Chara karaka",
        "Hora Lagna",
        "Ghati Lagna",
        "AL",
        "Amatyakaraka",
        "AmK",
    ],
    "wealth": [
        "Rasi",
        "D-2",
        "Hora",
        "D-4",
        "Chaturthamsa",
        "Sudasa",
        "Ashtakavarga",
        "Vimsottari",
        "Shadbala",
        "Chara karaka",
        "Hora Lagna",
        "Sree Lagna",
        "AL",
    ],
    "marriage": [
        "Rasi",
        "D-9",
        "Navamsa",
        "Navamsha",
        "Upapada",
        "DK",
        "Chara karaka",
        "Vimsottari",
        "Shadbala",
        "Gulika",
        "Maandi",
        "Mandi",
    ],
    "children": [
        "Rasi",
        "D-7",
        "Saptamsa",
        "Saptamsha",
        "PK",
        "Chara karaka",
        "Vimsottari",
        "Beeja Sphuta",
        "Kshetra Sphuta",
        "Jupiter",
        "Putra",
    ],
    "education": [
        "Rasi",
        "D-24",
        "Siddhamsa",
        "Mercury",
        "Jupiter",
        "Vimsottari",
        "Shadbala",
        "D-5",
        "Ashtakavarga",
        "GK",
    ],
    "spiritual": [
        "Rasi",
        "D-20",
        "D-60",
        "D-9",
        "Navamsa",
        "Ketu",
        "Jupiter",
        "Vimsottari",
        "Moola Dasa",
        "Bhrigu Bindu",
        "Ishta",
        "Pushkara",
        "Atmakaraka",
        "AK",
    ],
    "transits": [
        "Vimsottari",
        "Narayana Dasa",
        "Sudasa",
        "Rasi",
        "Ashtakavarga",
        "Chara karaka",
        "Shadbala",
    ],
}


@dataclass
class ChartDocument:
    """Parsed chart export (may contain natal + secondary/transit snapshot)."""

    source_path: Path
    plain_text: str
    natal_text: str
    secondary_text: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)
    secondary_metadata: dict[str, str] = field(default_factory=dict)

    @property
    def has_transit_snapshot(self) -> bool:
        return bool(self.secondary_text and self.secondary_metadata.get("date"))


def load_chart_file(path: str | Path) -> ChartDocument:
    """Read a .txt/.rtf JH export and split natal vs secondary chart blocks."""
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Chart file not found: {source}")

    raw = source.read_bytes()
    # JH sometimes saves RTF with a .txt extension.
    if _looks_like_rtf(raw) or source.suffix.lower() == ".rtf":
        plain = strip_rtf(raw.decode("latin-1", errors="ignore"))
    else:
        plain = raw.decode("utf-8", errors="ignore")
        if plain.lstrip().startswith("{\\rtf"):
            plain = strip_rtf(plain)

    plain = _normalize_whitespace(plain)
    charts = split_chart_blocks(plain)
    if not charts:
        raise ValueError(f"No chart content found in {source}")

    natal = charts[0]
    secondary = charts[1] if len(charts) > 1 else None
    return ChartDocument(
        source_path=source,
        plain_text=plain,
        natal_text=natal,
        secondary_text=secondary,
        metadata=extract_metadata(natal),
        secondary_metadata=extract_metadata(secondary) if secondary else {},
    )


def strip_rtf(rtf: str) -> str:
    """Best-effort RTF to plain text conversion for JH exports."""
    text = rtf
    text = re.sub(r"\\'([0-9a-fA-F]{2})", lambda m: chr(int(m.group(1), 16)), text)
    text = re.sub(r"\\u(-?\d+)\??", lambda m: _rtf_unicode(m.group(1)), text)
    text = text.replace("\\par", "\n").replace("\\line", "\n").replace("\\tab", "\t")
    text = re.sub(r"\\([a-zA-Z]+)(-?\d*)[ ]?", _rtf_control_to_space, text)
    text = text.replace("{", "").replace("}", "")
    # Remaining \\ pairs are literal backslashes in RTF; JH soft line breaks often
    # leave a dangling '\' at EOL which we strip during normalization.
    text = text.replace("\\\\", "\\")
    text = re.sub(r"\r\n?", "\n", text)
    return text


def split_chart_blocks(text: str) -> list[str]:
    """Split exports that paste multiple 'Natal Chart' dumps into one file."""
    matches = list(re.finditer(r"(?im)^[ \t]*Natal Chart[ \t\\]*$", text))
    if not matches:
        # Fallback: whole file is one chart.
        cleaned = text.strip()
        return [cleaned] if cleaned else []

    blocks: list[str] = []
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[start:end].strip()
        if block:
            blocks.append(block)
    return blocks


def extract_metadata(chart_text: str | None) -> dict[str, str]:
    if not chart_text:
        return {}
    meta: dict[str, str] = {}
    patterns = {
        "date": r"(?im)^Date:\s*(.+)$",
        "time": r"(?im)^Time:\s*(.+)$",
        "time_zone": r"(?im)^Time Zone:\s*(.+)$",
        "place": r"(?im)^Place:\s*(.+)$",
        "ayanamsa": r"(?im)^Ayanamsa:\s*(.+)$",
        "nakshatra": r"(?im)^Nakshatra:\s*(.+)$",
        "tithi": r"(?im)^Tithi:\s*(.+)$",
    }
    for key, pattern in patterns.items():
        m = re.search(pattern, chart_text)
        if m:
            meta[key] = _clean_meta_value(m.group(1))

    # Place often has a city/country line immediately after coordinates.
    place_m = re.search(r"(?im)^Place:\s*.+\n[ \t]*(.+)$", chart_text)
    if place_m:
        city = _clean_meta_value(place_m.group(1))
        if city and not city.lower().startswith(("altitude", "lunar", "tithi")):
            meta["location_name"] = city
    return meta


def _clean_meta_value(value: str) -> str:
    return value.strip().strip("\\").strip()


def extract_relevant_context(
    chart: ChartDocument,
    topic: str,
    *,
    max_chars: int = 28000,
) -> str:
    """Build a focused chart excerpt for a life-area query."""
    hints = TOPIC_SECTION_HINTS.get(topic, [])
    natal_excerpt = _excerpt_by_hints(chart.natal_text, hints, max_chars=max_chars)

    parts = [
        "=== NATAL CHART CONTEXT ===",
        _format_metadata(chart.metadata),
        natal_excerpt,
    ]

    if topic == "transits" and chart.secondary_text:
        secondary = _excerpt_by_hints(
            chart.secondary_text,
            TOPIC_SECTION_HINTS["transits"] + ["Rasi", "Body", "Longitude"],
            max_chars=max_chars // 2,
        )
        parts.extend(
            [
                "",
                "=== SECONDARY / TRANSIT SNAPSHOT (from same export) ===",
                _format_metadata(chart.secondary_metadata),
                secondary,
            ]
        )
    elif chart.secondary_text and topic in {"career", "wealth", "marriage"}:
        # Light transit cue for timing-sensitive topics.
        dasa = _extract_named_sections(
            chart.secondary_text,
            ["Vimsottari Dasa", "Narayana Dasa", "Sudasa"],
            window=40,
        )
        if dasa:
            parts.extend(
                [
                    "",
                    "=== CURRENT-PERIOD DASA SNAPSHOT (secondary chart) ===",
                    dasa[:6000],
                ]
            )

    # Always attach Pushkara / karaka / upagraha cues when present.
    extras = _extract_named_sections(
        chart.natal_text,
        [
            "Chara karaka",
            "Pushkara",
            "Gulika",
            "Maandi",
            "Mandi",
            "Shadbala",
            "Ashtakavarga of Rasi Chart",
            "Vimsottari Dasa",
        ],
        window=35,
    )
    if extras and extras not in natal_excerpt:
        parts.extend(["", "=== SHARED STRENGTH / KARAKA / DASA NOTES ===", extras[:8000]])

    joined = "\n".join(parts).strip()
    if len(joined) > max_chars:
        return joined[:max_chars] + "\n\n[...truncated for prompt size...]"
    return joined


def current_vimsottari_summary(chart: ChartDocument, as_of_year: int | None = None) -> str:
    """Pick the Vimsottari mahadasa/antardasa lines around 'now' when possible."""
    text = chart.natal_text
    section = _extract_named_sections(text, ["Vimsottari Dasa"], window=40)
    if not section:
        return ""
    if as_of_year is None:
        return section[:2500]

    lines = [ln for ln in section.splitlines() if ln.strip()]
    relevant: list[str] = []
    for ln in lines:
        years = [int(y) for y in re.findall(r"\b(19\d{2}|20\d{2})\b", ln)]
        if any(as_of_year - 2 <= y <= as_of_year + 8 for y in years) or not years:
            relevant.append(ln)
    return "\n".join(relevant[:40]) if relevant else section[:2500]


def _excerpt_by_hints(text: str, hints: Iterable[str], *, max_chars: int) -> str:
    lines = text.splitlines()
    if not hints:
        return text[:max_chars]

    selected: list[str] = []
    used = set()
    # Always keep the header / planet longitude table.
    for idx, line in enumerate(lines[:120]):
        selected.append(line)
        used.add(idx)

    for hint in hints:
        pattern = re.compile(re.escape(hint), re.I)
        for idx, line in enumerate(lines):
            if idx in used:
                continue
            if pattern.search(line):
                start = max(0, idx - 2)
                end = min(len(lines), idx + 28)
                for j in range(start, end):
                    if j not in used:
                        selected.append(lines[j])
                        used.add(j)

    # Preserve rough reading order.
    ordered = [lines[i] for i in sorted(used)]
    excerpt = "\n".join(ordered)
    if len(excerpt) > max_chars:
        return excerpt[:max_chars] + "\n[...truncated...]"
    return excerpt


def _extract_named_sections(text: str, titles: list[str], window: int = 30) -> str:
    lines = text.splitlines()
    chunks: list[str] = []
    used = set()
    for title in titles:
        pattern = re.compile(re.escape(title), re.I)
        for idx, line in enumerate(lines):
            if pattern.search(line):
                end = min(len(lines), idx + window)
                block = "\n".join(lines[idx:end])
                key = (idx, end)
                if key not in used:
                    chunks.append(block)
                    used.add(key)
                break
    return "\n\n".join(chunks)


def _format_metadata(meta: dict[str, str]) -> str:
    if not meta:
        return "(metadata not detected)"
    order = [
        "date",
        "time",
        "time_zone",
        "place",
        "location_name",
        "ayanamsa",
        "nakshatra",
        "tithi",
    ]
    rows = [f"{k}: {meta[k]}" for k in order if k in meta]
    for k, v in meta.items():
        if k not in order:
            rows.append(f"{k}: {v}")
    return "\n".join(rows)


def _looks_like_rtf(raw: bytes) -> bool:
    head = raw.lstrip()[:64].lower()
    return head.startswith(b"{\\rtf")


def _rtf_unicode(code: str) -> str:
    try:
        value = int(code)
        if value < 0:
            value += 65536
        return chr(value)
    except ValueError:
        return ""


def _rtf_control_to_space(match: re.Match[str]) -> str:
    control = match.group(1).lower()
    if control in {"par", "line", "page"}:
        return "\n"
    if control in {"tab"}:
        return "\t"
    return ""


def _normalize_whitespace(text: str) -> str:
    text = text.replace("\x00", "")
    # JH RTF exports frequently end content lines with a dangling backslash.
    text = re.sub(r"\\+\s*$", "", text, flags=re.M)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"
