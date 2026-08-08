"""Topic prompts for Gemini-based Vedic chart analysis."""

from __future__ import annotations

from dataclasses import dataclass


SYSTEM_INSTRUCTION = """You are an expert Vedic (Jyotish) astrologer trained in Parashari, Jaimini,
and classical dasa techniques. You analyze Jagannatha Hora chart exports carefully.

Rules:
- Base conclusions on the supplied chart data. Quote specific yogas, houses, lords,
  divisional placements, dasa lords, karakas, ashtakavarga bindus, and shadbala when relevant.
- Prefer classical reasoning (Rasi + relevant Vargas + dasas + karakas + upagrahas).
- When Pushkara Navamsha is not explicitly labeled, deduce it from the Navamsa column
  using classical Pushkara navamsha rules and state your deduction clearly.
- Distinguish natal promise vs timing (dasas / transits).
- Be practical and nuanced; avoid fatalism. Mention both supports and challenges.
- If data for a sub-topic is missing, say so instead of inventing placements.
- Write in clear English with short section headings and bullet points.
"""


@dataclass(frozen=True)
class TopicSpec:
    key: str
    title: str
    focus: str


TOPICS: list[TopicSpec] = [
    TopicSpec(
        key="career",
        title="Career & Profession",
        focus=(
            "Analyze career, profession, status, business vs service, leadership, "
            "changes, and favorable fields. Emphasize D-1 10th house/lord, Dasamsa (D-10), "
            "Amatyakaraka (AmK), AL (Arudha Lagna), Hora/Ghati Lagna cues, shadbala of "
            "relevant planets, ashtakavarga of 10th, and current/upcoming Vimshottari periods."
        ),
    ),
    TopicSpec(
        key="wealth",
        title="Wealth, Income & Assets (D-2 & D-4)",
        focus=(
            "Analyze wealth accumulation, cash flow, savings, property/vehicles/fixed assets, "
            "and speculative gains. Give primary weight to Hora (D-2) for liquid wealth and "
            "Chaturthamsa (D-4) for property/fixed assets, supported by D-1 2nd/11th/4th houses, "
            "Sudasa, Sree Lagna, and ashtakavarga. Separate earned income vs windfalls vs assets."
        ),
    ),
    TopicSpec(
        key="marriage",
        title="Marriage & Partnerships",
        focus=(
            "Analyze marriage timing, spouse significations, harmony/challenges, and remarriage "
            "risks if indicated. Use D-1 7th house/lord, Navamsa (D-9), Darakaraka (DK), "
            "upagrahas (Gulika/Mandi) if relevant, and dasa periods. Note Pushkara Navamsha "
            "status of Venus, DK, 7th lord, and lagna lord when deducible."
        ),
    ),
    TopicSpec(
        key="children",
        title="Children & Progeny",
        focus=(
            "Analyze progeny happiness, timing, and possible challenges using D-1 5th house/lord, "
            "Saptamsa (D-7), Putrakaraka (PK), Jupiter, Beeja/Kshetra sphuta if present, "
            "and relevant dasas. Be sensitive and non-alarmist."
        ),
    ),
    TopicSpec(
        key="education",
        title="Education & Learning",
        focus=(
            "Analyze formal education, higher studies, technical vs traditional learning, "
            "teaching/research aptitude. Use Mercury/Jupiter, D-1 4th/5th/9th, Siddhamsa (D-24) "
            "if present, D-5 when useful, and education-related dasa windows."
        ),
    ),
    TopicSpec(
        key="spiritual",
        title="Spiritual Progress",
        focus=(
            "Analyze spiritual inclination, sadhana style, teachers, renunciation vs householder "
            "path, and periods of awakening. Use Atmakaraka, Ketu, 12th/9th/5th houses, "
            "D-20 / D-60 if present, Navamsa, Bhrigu Bindu, Moola Dasa, and Pushkara Navamsha "
            "of AK/Ketu/Jupiter when deducible."
        ),
    ),
    TopicSpec(
        key="transits",
        title="Transit Outlook (Next 1 Year)",
        focus=(
            "Provide a practical 12-month transit and dasa outlook from today (or the secondary "
            "snapshot date if provided). Cover Jupiter, Saturn, Rahu/Ketu, and Mars transit "
            "themes relative to natal lagna/Moon/AL; integrate current Vimshottari "
            "maha/antar/pratyantar if available. Month-by-month only when data supports it; "
            "otherwise give quarterly themes with key caution/opportunity windows."
        ),
    ),
]


def build_user_prompt(
    topic: TopicSpec,
    chart_context: str,
    *,
    native_label: str | None = None,
    as_of: str | None = None,
) -> str:
    who = native_label or "the native"
    when = as_of or "today"
    return f"""Analyze the following Vedic chart data for {who}.

Topic: {topic.title}
Analysis date / reference: {when}

Focus instructions:
{topic.focus}

Required response structure:
1. Key chart factors used
2. Core promise / pattern
3. Strengths and supports
4. Challenges / cautions
5. Timing notes (dasas / transits)
6. Practical guidance

Chart data:
{chart_context}
"""
