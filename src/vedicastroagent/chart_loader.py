"""Load and section Jagannatha Hora natal chart text / RTF exports."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Iterable


# Prefer precise varga labels. Avoid bare "Hora" — it matches Hora Lord / Hora Lagna.
TOPIC_VARGAS: dict[str, list[str]] = {
    "career": ["Rasi", "D-10", "Dasamsa"],
    "wealth": ["Rasi", "D-2", "D-4", "Chaturthamsa"],
    "marriage": ["Rasi", "D-9", "Navamsa"],
    "children": ["Rasi", "D-7", "Saptamsa"],
    "education": ["Rasi", "D-24", "D-5"],
    "spiritual": ["Rasi", "D-9", "D-20", "D-60", "Navamsa"],
    "transits": ["Rasi"],
}

TOPIC_DASAS: dict[str, list[str]] = {
    "career": ["Vimsottari Dasa", "Narayana Dasa"],
    "wealth": ["Vimsottari Dasa", "Sudasa"],
    "marriage": ["Vimsottari Dasa"],
    "children": ["Vimsottari Dasa"],
    "education": ["Vimsottari Dasa"],
    "spiritual": ["Vimsottari Dasa", "Moola Dasa"],
    "transits": ["Vimsottari Dasa", "Narayana Dasa", "Sudasa"],
}

TOPIC_SECTION_HINTS: dict[str, list[str]] = {
    "career": [
        "Shadbala",
        "Ashtakavarga",
        "Chara karaka",
        "Hora Lagna",
        "Ghati Lagna",
        "AmK",
    ],
    "wealth": [
        "Shadbala",
        "Ashtakavarga",
        "Chara karaka",
        "Hora Lagna",
        "Sree Lagna",
        "AmK",
    ],
    "marriage": [
        "Chara karaka",
        "Shadbala",
        "Gulika",
        "Maandi",
        "Mandi",
        "DK",
    ],
    "children": [
        "Chara karaka",
        "Beeja Sphuta",
        "Kshetra Sphuta",
        "PK",
    ],
    "education": [
        "Shadbala",
        "Ashtakavarga",
        "Chara karaka",
        "GK",
    ],
    "spiritual": [
        "Chara karaka",
        "Bhrigu Bindu",
        "Pushkara",
        "AK",
    ],
    "transits": [
        "Ashtakavarga",
        "Chara karaka",
        "Shadbala",
    ],
}

_DASA_HEADERS = (
    "Vimsottari Dasa",
    "Moola Dasa",
    "Ashtottari Dasa",
    "Kalachakra Dasa",
    "Narayana Dasa",
    "Sudasa",
    "Yogini Dasa",
    "Chara Dasa",
)


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


def extract_varga_block(text: str, label: str) -> str | None:
    """Extract one full JH ASCII diamond chart block containing ``label`` (e.g. D-2)."""
    lines = text.splitlines()
    pattern = _varga_label_pattern(label)
    hit: int | None = None
    for idx, line in enumerate(lines):
        if pattern.search(line):
            hit = idx
            break
    if hit is None:
        return None

    start = hit
    while start > 0 and not re.match(r"^\s*\+-", lines[start]):
        start -= 1
        if hit - start > 40:
            start = max(0, hit - 12)
            break

    end = hit
    while end < len(lines) - 1:
        end += 1
        if re.match(r"^\s*\+-", lines[end]) and end > hit:
            end += 1
            break
        if end - hit > 45:
            break

    block = "\n".join(lines[start:end]).strip()
    return block or None


def extract_dasa_section(text: str, title: str) -> str | None:
    """Extract a dasa table from its header until the next dasa header."""
    lines = text.splitlines()
    pattern = re.compile(re.escape(title), re.I)
    start: int | None = None
    for idx, line in enumerate(lines):
        if pattern.search(line):
            start = idx
            break
    if start is None:
        return None

    end = len(lines)
    header_re = re.compile("|".join(re.escape(h) for h in _DASA_HEADERS), re.I)
    for idx in range(start + 1, len(lines)):
        if header_re.search(lines[idx]):
            end = idx
            break
    block = "\n".join(lines[start:end]).strip()
    # Cap extremely long Sudasa/Narayana dumps while keeping structure.
    if len(block) > 7000:
        block = block[:7000] + "\n[...dasa table truncated...]"
    return block or None


def extract_relevant_context(
    chart: ChartDocument,
    topic: str,
    *,
    max_chars: int = 32000,
) -> str:
    """Build a focused chart excerpt for a life-area query."""
    parts: list[str] = [
        "=== NATAL CHART METADATA ===",
        _format_metadata(chart.metadata),
        "",
        "=== NATAL LONGITUDE / KARAKA TABLE (D-1 body list) ===",
        _header_table(chart.natal_text),
    ]

    vargas = TOPIC_VARGAS.get(topic, ["Rasi"])
    varga_parts: list[str] = []
    for label in vargas:
        block = extract_varga_block(chart.natal_text, label)
        if block:
            varga_parts.append(f"--- Varga block: {label} ---\n{block}")
    if varga_parts:
        parts.extend(["", "=== LABELED DIVISIONAL / RASI ASCII CHARTS ===", *varga_parts])
    else:
        parts.append("\n(No labeled varga ASCII blocks matched for this topic.)")

    dasa_titles = TOPIC_DASAS.get(topic, ["Vimsottari Dasa"])
    dasa_parts: list[str] = []
    for title in dasa_titles:
        block = extract_dasa_section(chart.natal_text, title)
        if block:
            dasa_parts.append(block)
    if dasa_parts:
        parts.extend(
            [
                "",
                "=== NATAL DASA TABLES (use ONLY these for dasa timing; ignore any secondary-chart dasas) ===",
                *dasa_parts,
            ]
        )

    hints = TOPIC_SECTION_HINTS.get(topic, [])
    extras = _excerpt_by_hints(
        chart.natal_text,
        hints + ["Chara karaka", "Shadbala", "Ashtakavarga of Rasi Chart"],
        max_chars=9000,
        include_header=False,
    )
    if extras.strip():
        parts.extend(["", "=== SUPPORTING NATAL SECTIONS ===", extras])

    # Secondary chart: planetary positions only (gochara snapshot). Never its dasas.
    if chart.secondary_text and topic in {
        "transits",
        "career",
        "wealth",
        "marriage",
        "children",
        "education",
        "spiritual",
    }:
        secondary_body = _header_table(chart.secondary_text)
        secondary_rasi = extract_varga_block(chart.secondary_text, "Rasi")
        parts.extend(
            [
                "",
                "=== SECONDARY / TRANSIT SNAPSHOT (planetary positions only; NOT natal dasas) ===",
                _format_metadata(chart.secondary_metadata),
                secondary_body,
            ]
        )
        if secondary_rasi:
            parts.extend(["", "--- Transit snapshot Rasi ---", secondary_rasi])

    joined = "\n".join(parts).strip()
    if len(joined) > max_chars:
        return joined[:max_chars] + "\n\n[...truncated for prompt size...]"
    return joined


def current_vimsottari_summary(chart: ChartDocument, as_of_year: int | None = None) -> str:
    """Pick the Vimsottari mahadasa/antardasa lines around 'now' when possible."""
    section = extract_dasa_section(chart.natal_text, "Vimsottari Dasa") or ""
    if not section:
        return ""
    if as_of_year is None:
        return section[:3500]

    lines = [ln for ln in section.splitlines() if ln.strip()]
    relevant: list[str] = []
    current_md = ""
    for ln in lines:
        md_match = re.match(r"^([A-Za-z]+)\s+[A-Za-z]+\s+\d{4}-", ln)
        if md_match:
            current_md = md_match.group(1)
        years = [int(y) for y in re.findall(r"\b(19\d{2}|20\d{2})\b", ln)]
        if years and any(as_of_year - 1 <= y <= as_of_year + 10 for y in years):
            if current_md and (not relevant or not relevant[-1].startswith(current_md)):
                # Keep mahadasa identity visible even on continuation slices.
                relevant.append(f"[Mahadasa context: {current_md}]")
            relevant.append(ln)
        elif not years and "Dasa" in ln:
            relevant.append(ln)
    return "\n".join(relevant[:50]) if relevant else section[:3500]


def _varga_label_pattern(label: str) -> re.Pattern[str]:
    """Match JH center labels like 'D-2 (US)', 'D-4', 'Rasi', 'Navamsa'."""
    cleaned = label.strip()
    if re.fullmatch(r"D-\d+", cleaned, re.I):
        # Require D-n as a chart label, not a random substring.
        return re.compile(rf"D-{cleaned[2:]}\b", re.I)
    if cleaned.lower() == "rasi":
        return re.compile(r"(?i)\bRasi\b")
    # Word-ish labels: Hora chart is identified via D-2, not the word Hora alone.
    return re.compile(rf"(?i)\b{re.escape(cleaned)}\b")


def _header_table(text: str, max_lines: int = 110) -> str:
    lines = text.splitlines()
    # Prefer from Body longitude table through end of early karaka block.
    start = 0
    for idx, line in enumerate(lines):
        if re.search(r"Body\s+Longitude", line, re.I):
            start = idx
            break
    chunk = lines[start : start + max_lines]
    return "\n".join(chunk)


def _excerpt_by_hints(
    text: str,
    hints: Iterable[str],
    *,
    max_chars: int,
    include_header: bool = True,
) -> str:
    lines = text.splitlines()
    if not hints:
        return text[:max_chars]

    used: set[int] = set()
    if include_header:
        for idx in range(min(120, len(lines))):
            used.add(idx)

    for hint in hints:
        # Avoid bare "Hora" false positives.
        if hint.lower() == "hora":
            continue
        pattern = re.compile(re.escape(hint), re.I)
        for idx, line in enumerate(lines):
            if idx in used:
                continue
            if pattern.search(line):
                start = max(0, idx - 1)
                end = min(len(lines), idx + 24)
                used.update(range(start, end))

    ordered = [lines[i] for i in sorted(used)]
    excerpt = "\n".join(ordered)
    if len(excerpt) > max_chars:
        return excerpt[:max_chars] + "\n[...truncated...]"
    return excerpt


def parse_jh_date(value: str | None) -> date | None:
    """Parse common Jagannatha Hora date strings (e.g. 'March 15, 1981')."""
    if not value:
        return None
    text = value.strip()
    for fmt in (
        "%B %d, %Y",
        "%b %d, %Y",
        "%B %d %Y",
        "%b %d %Y",
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%m/%d/%Y",
        "%d/%m/%Y",
    ):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    m = re.search(
        r"\b(January|February|March|April|May|June|July|August|September|October|November|December|"
        r"Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\s+(\d{1,2}),?\s+(\d{4})\b",
        text,
        flags=re.IGNORECASE,
    )
    if m:
        month, day, year = m.group(1), m.group(2), m.group(3)
        for fmt in ("%B %d %Y", "%b %d %Y"):
            try:
                return datetime.strptime(f"{month} {day} {year}", fmt).date()
            except ValueError:
                continue
    return None


def age_years(birth: date, as_of: date) -> int:
    """Completed years of age on as_of (negative if as_of precedes birth)."""
    years = as_of.year - birth.year
    if (as_of.month, as_of.day) < (birth.month, birth.day):
        years -= 1
    return years


def subject_age_as_of(chart: ChartDocument, as_of: date) -> tuple[date | None, int | None]:
    """Return (birth_date, age_years) from natal metadata relative to as_of."""
    birth = parse_jh_date(chart.metadata.get("date"))
    if birth is None:
        return None, None
    age = age_years(birth, as_of)
    if age < 0:
        return birth, None
    return birth, age


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
