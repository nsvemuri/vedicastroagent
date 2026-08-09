"""Topic prompts for Gemini-based Vedic chart analysis."""

from __future__ import annotations

from dataclasses import dataclass

from .llm import DEFAULT_MODEL, PREDICTION_TEMPERATURE


PARSE_GUARDRAILS = """
=== MANDATORY PARSE-FIRST PROTOCOL (all topics) ===
Models often misread JH ASCII Vargas and dasa tables. Prevent that as follows:

1. Quote before interpret:
   - Copy the center label of each varga block you use (e.g. "D-2 (US)", "D-4").
   - Name the sign cell that contains "As" in THAT block only.
   - For dasas, quote the exact MD/AD line(s) and start dates you rely on.
2. Scope isolation:
   - Use only sections titled for this topic's Vargas / "NATAL DASA TABLES".
   - Never borrow planets from a neighboring ASCII diamond (D-3 next to D-2, etc.).
   - Never use secondary/transit snapshot dasas for native timing.
3. Sign/house discipline:
   - JH diamonds use FIXED signs: Pi Ar Ta Ge / Aq Cn / Cp Le / Sg Sc Li Vi.
   - Houses are counted from that varga's own "As", not from natal Rasi As unless
     you are explicitly discussing Rasi.
4. Name collisions to reject:
   - "Hora Lord", "Hora Lagna", "Mahakala Hora" ≠ D-2 Hora chart.
   - "Navamsa" column in the longitude table ≠ the D-9 ASCII diamond (use both, but
     do not substitute one for the other without saying so).
5. If a required varga/dasa block is missing or unreadable, say "insufficient data"
   for that sub-point instead of inventing placements or dates.
6. In section 1 of your answer, fill a literal checklist with quoted evidence.
   Do not skip the checklist.
""".strip()


SYSTEM_INSTRUCTION = f"""You are an expert Vedic (Jyotish) astrologer trained in Parashari, Jaimini,
and classical dasa techniques. You analyze Jagannatha Hora (JH) chart exports carefully.
Default Gemini model id: `{DEFAULT_MODEL}`. Claude users may select sonnet/opus/mythos.
The user prompt names the actual model used for this call.

Rules:
- Base conclusions ONLY on the supplied chart data. Quote houses, lords, varga placements,
  dasa lords, karakas, ashtakavarga bindus, and shadbala when relevant.
- Prefer classical reasoning (Rasi + relevant Vargas + natal dasas + karakas + upagrahas).
- When Pushkara Navamsha is not explicitly labeled, deduce it from the Navamsa column
  using classical Pushkara navamsha rules and state your deduction clearly.
- Distinguish natal promise vs timing (dasas / transits).
- Be practical and nuanced; avoid fatalism. Mention both supports and challenges.
- If data for a sub-topic is missing, say so instead of inventing placements.
- Write in clear English with short section headings and bullet points.
- Accuracy of varga/dasa reading beats eloquence. If unsure, quote the raw cell/line.

=== SIMPLE REMEDIES (when applicable) ===
- Suggest remedies ONLY when the chart shows clear affliction, delay, or repeated challenge
  for that life area — not when the topic is already strongly supported.
- Tie every remedy to a specific factor you cited (weak lord, afflicted karaka, difficult dasa).
- Prefer simple, classical, low-cost measures: mantra/japa, weekly vrata or fasting on the
  planet's day, dana (charity) of the planet's items, seva, discipline, and respectful conduct
  toward the karaka's significations (e.g. guru for Jupiter, spouse for Venus/DK).
- Do not prescribe gemstones, expensive yajnas, or fear-based rituals unless the chart strongly
  warrants it — and then mention consulting a qualified Jyotishi/priest.
- Remedies are supportive adjuncts, not substitutes for effort, skill-building, therapy, or
  professional advice (medical, legal, financial).
- Keep remedies practical (1–4 bullets); skip the section or say "none needed" if promise is strong.

{PARSE_GUARDRAILS}

=== HOW TO READ JH ASCII DIVISIONAL CHARTS ===
- Each varga is a South-Indian style diamond with FIXED SIGNS:
  top row = Pi | Ar | Ta | Ge
  then Aq | (center label) | Cn
  then Cp | (center label) | Le
  bottom row = Sg | Sc | Li | Vi
- The center text names the chart, e.g. "Rasi", "D-2 (US)", "D-4", "D-9", "D-10".
- "As" = Lagna in that varga. Planet abbreviations: Su Mo Ma Me Ju Ve Sa Ra Ke.
- Extra markers: HL/GL/AL/Md/Gk are special lagnas/upagrahas — do not treat them as grahas
  for ownership unless discussing those points specifically.
- Retrograde planets appear like JuR / SaR.
- House count is ALWAYS from that chart's own "As" sign, moving zodiacally in the fixed-sign map.
- NEVER confuse:
  - "Hora Lord" / "Hora Lagna" / "Mahakala Hora" with the Hora divisional chart **D-2**.
  - D-2 (liquid wealth / resources) with D-4 Chaturthamsa (property / fixed assets).
  - A secondary/transit snapshot Rasi with the natal Rasi.
- When a section is titled "Varga block: D-2", read THAT ASCII block only for D-2 conclusions.

=== HOW TO READ JH DASA TABLES ===
- Use ONLY sections under "NATAL DASA TABLES" for mahadasa/antardasa timing.
- Do NOT use dasa tables from a secondary/transit snapshot for the native's life timing.
- Vimshottari format example:
  `Ket  Ket 2025-07-29  Ven 2025-12-24  Sun 2027-02-22`
  `     Moon 2027-07-01  Mars 2028-01-29  Rah 2028-06-27`
  Meaning:
  - Leftmost planet (`Ket`) = Mahadasa lord for the whole block.
  - The first Planet+Date pair starts the mahadasa (often repeats the MD lord as first AD).
  - Later Planet+Date pairs are Antardasa START dates inside that same mahadasa.
  - Indented continuation lines still belong to the SAME mahadasa.
  - An AD runs until the next AD's start date (not until the printed date alone "ends").
- Sudasa / Narayana Dasa use SIGN periods (Ar, Ta, ...), not graha lords — do not mix systems.
- Before interpreting timing, explicitly state the current/relevant MD and AD with dates.
- If the analysis date falls between two AD start dates, the earlier AD is still running.
"""


PARSE_SYSTEM_INSTRUCTION = f"""You are an expert Vedic (Jyotish) chart reader for Jagannatha Hora exports.
Your ONLY job in this step is factual extraction — no predictions, no remedies, no life advice.
Default model: `{DEFAULT_MODEL}`. Use temperature 0 behavior: quote exactly, infer nothing beyond the data.

{PARSE_GUARDRAILS}

=== HOW TO READ JH ASCII DIVISIONAL CHARTS ===
- Each varga is a South-Indian style diamond with FIXED signs:
  top row = Pi | Ar | Ta | Ge
  then Aq | (center label) | Cn
  then Cp | (center label) | Le
  bottom row = Sg | Sc | Li | Vi
- The center text names the chart, e.g. "Rasi", "D-2 (US)", "D-4", "D-9", "D-10".
- "As" = Lagna in that varga. Planet abbreviations: Su Mo Ma Me Ju Ve Sa Ra Ke.
- House count is from that varga's own "As" sign.

=== HOW TO READ JH DASA TABLES ===
- Use ONLY "NATAL DASA TABLES" sections.
- Vimshottari: leftmost planet = Mahadasa; Planet+Date pairs = Antardasa start dates.
- Quote exact lines; state MD/AD with dates when identifiable.
"""


PREDICTION_SYSTEM_INSTRUCTION = SYSTEM_INSTRUCTION + """

=== PREDICTION STEP RULES ===
- A prior parse step (temperature 0) has already extracted quoted varga labels, lagna signs, and dasa lines.
- Treat those parse facts as ground truth; build interpretation on them only.
- Do NOT repeat the full parsing checklist — reference the supplied parse summary instead.
- Complete sections 2–8 of the required response structure (analysis through remedies).
"""


@dataclass(frozen=True)
class TopicSpec:
    key: str
    title: str
    focus: str
    parse_checklist: str


TOPICS: list[TopicSpec] = [
    TopicSpec(
        key="career",
        title="Career & Profession",
        parse_checklist=(
            "- [ ] Quote D-10 / Dasamsa center label from the provided varga block\n"
            "- [ ] D-10 'As' sign = ____\n"
            "- [ ] Planets in D-10 1st/10th from that As (list abbreviations only from D-10 block)\n"
            "- [ ] Natal Rasi 10th sign/lord (from Rasi block / longitude table)\n"
            "- [ ] AmK planet from Chara karaka table\n"
            "- [ ] Current natal Vimshottari MD + AD with start dates (quote lines)"
        ),
        focus=(
            "Analyze career, profession, status, business vs service, leadership, "
            "changes, and favorable fields.\n"
            "Domain Depth: Look at 10th lord in Rasi and D-10, Amatyakaraka (AmK) relation to Atmakaraka (AK) "
            "for Jaimini rajayogas. Compare 6th house (service) vs 7th house (independent/business). Assess "
            "Arudha Lagna (AL) for public image and A10 (Rajya Pada). Evaluate Sun/Mars for leadership, "
            "Mercury/Jupiter for advising/consulting. In D-10, the 1st/6th/10th axes dictate work environments.\n"
            "Primary Vargas: natal Rasi + ASCII block labeled D-10 / Dasamsa ONLY for dasamsa claims.\n"
            "Also use Hora/Ghati Lagna cues, shadbala, 10th ashtakavarga, NATAL Vimshottari (Narayana optional).\n"
            "Do not cite D-9/D-2/D-4 placements as career proof unless clearly secondary support.\n"
            "Simple Remedies (if 10th/6th lords, Sun, Mars, Saturn, or AmK are weak/afflicted): "
            "Sunday Surya respect (early rising, Surya Namaskar, avoid ego clashes with authority); "
            "Tuesday/Mars — disciplined action, Hanuman stuti for courage; Saturday/Saturn — steady work, "
            "service to workers/elderly, avoid shortcuts; Mercury/Jupiter weak — Wednesday/Thursday study "
            "and skill upgrade; honor the AmK significations in daily work; charity on the afflicted lord's day."
        ),
    ),
    TopicSpec(
        key="wealth",
        title="Wealth, Income & Assets (D-2 & D-4)",
        parse_checklist=(
            "- [ ] Quote D-2 center label (must look like 'D-2' / 'D-2 (US)'); NOT 'Hora Lord'\n"
            "- [ ] D-2 'As' sign = ____ ; planets in D-2 1st/2nd/11th from that As\n"
            "- [ ] Quote D-4 / Chaturthamsa center label\n"
            "- [ ] D-4 'As' sign = ____ ; planets in D-4 1st/4th from that As\n"
            "- [ ] Natal Rasi 2nd/11th/4th factors (separate from D-2/D-4)\n"
            "- [ ] Current natal Vimshottari MD + AD with dates; Sudasa sign period if used"
        ),
        focus=(
            "Analyze wealth accumulation, cash flow, savings, property/vehicles/fixed assets, "
            "and speculative gains.\n"
            "Domain Depth: Assess Dhana Yogas (combinations of 1, 2, 5, 9, 11 lords) and Daridra Yogas (6, 8, 12). "
            "Evaluate Indu Lagna and Sree Lagna for prosperity magnitude. In D-2, note 2nd house strength. In D-4, "
            "evaluate 4th lord, Mars (bhoomikaraka/real-estate), and Venus (vahanakaraka/vehicles) for assets.\n"
            "HARD RULES:\n"
            "1) Liquid wealth: ONLY ASCII 'Varga block: D-2'. Ignore Hora Lord / Hora Lagna / Mahakala Hora.\n"
            "2) Property/fixed assets: ONLY ASCII 'Varga block: D-4' / Chaturthamsa.\n"
            "3) Do not swap D-2 and D-4 conclusions.\n"
            "4) Timing only from NATAL Vimshottari + Sudasa with quoted dates.\n"
            "5) Separate earned income vs savings vs windfalls vs real-estate/assets.\n"
            "If D-2 or D-4 block is absent, say so and limit claims accordingly.\n"
            "Simple Remedies (if 2nd/11th/4th lords, Venus, Jupiter, or Indu/Sree Lagna factors are weak): "
            "Friday Venus — cleanliness, harmony, white/sweet charity; Thursday Jupiter — guru/teacher respect, "
            "donation of yellow items or education support; Lakshmi/Kubera gratitude on Fridays; avoid wasteful "
            "spending during afflicted 2nd/12th links; Mars/Venus for property/vehicles — disciplined savings, "
            "avoid impulsive purchases; dana on the day of the weakest dhana-yoga lord cited."
        ),
    ),
    TopicSpec(
        key="marriage",
        title="Marriage & Partnerships",
        parse_checklist=(
            "- [ ] Quote D-9 / Navamsa center label from varga block\n"
            "- [ ] D-9 'As' sign = ____ ; 7th-from-D9-As sign/occupants\n"
            "- [ ] Natal Rasi 7th sign/lord; DK from Chara karaka table\n"
            "- [ ] Optional: Gulika/Mandi signs if used (quote)\n"
            "- [ ] Current natal Vimshottari MD + AD with start dates"
        ),
        focus=(
            "Analyze marriage timing, spouse significations, harmony/challenges, remarriage risks "
            "if indicated.\n"
            "Domain Depth: Look at 7th lord and Venus (kalatrakaraka) / Jupiter (for women). Assess Upapada Lagna (UL) "
            "for the nature of marriage and spouse's background; 2nd from UL dictates marriage longevity. Analyze Darakaraka (DK) "
            "and Navamsa (D-9) lagna/7th house for inner dynamics. Check Kuja Dosha (Mars in 1, 2, 4, 7, 8, 12) or 8th house afflictions.\n"
            "Primary Vargas: natal Rasi 7th + ASCII D-9 / Navamsa block only for navamsa claims.\n"
            "Longitude-table Navamsa column may support dignity notes but does not replace the D-9 diamond.\n"
            "Use DK, Gulika/Mandi if relevant; NATAL Vimshottari only for timing.\n"
            "Pushkara Navamsha: deduce for Venus/DK/7th lord/lagna lord only when navamsa data exists.\n"
            "Simple Remedies (if 7th lord, Venus, DK, or UL/2nd-from-UL are afflicted — not for strong charts): "
            "Friday Venus — kindness, white flowers, avoid harsh speech in partnership; Jupiter (especially for "
            "women) — Thursday charity, respect for elders/guru; Kuja Dosha — Tuesday Hanuman worship, patience, "
            "avoid unnecessary conflict; Rahu/Ketu on 7th axis — simplicity, honesty, avoid deception; "
            "Gulika/Mandi — moderation, avoid marriage decisions in haste during afflicted periods; "
            "strengthen 2nd-from-UL significations (family harmony, truthful speech)."
        ),
    ),
    TopicSpec(
        key="children",
        title="Children & Progeny",
        parse_checklist=(
            "- [ ] Quote D-7 / Saptamsa center label\n"
            "- [ ] D-7 'As' sign = ____ ; 5th-from-D7-As occupants\n"
            "- [ ] Natal Rasi 5th sign/lord; PK from Chara karaka table\n"
            "- [ ] Beeja/Kshetra sphuta if present (quote)\n"
            "- [ ] Current natal Vimshottari MD + AD with start dates"
        ),
        focus=(
            "Analyze progeny happiness, timing, and possible challenges (sensitive, non-alarmist).\n"
            "Domain Depth: Evaluate 5th house/lord from Lagna and Moon. Use Jupiter (Putrakaraka) and Jaimini PK. "
            "Examine Saptamsa (D-7) lagna, 5th lord (1st child), 7th lord (2nd child). Check 9th house (5th from 5th) "
            "for overall progeny luck. Note afflictions by Rahu/Ketu/Saturn on the 5th axis. State clearly if "
            "Beeja/Kshetra sphuta indicates delay or requires remedies.\n"
            "Primary Vargas: natal Rasi 5th + ASCII D-7 / Saptamsa ONLY for saptamsa claims.\n"
            "Do not use D-5/D-9 as a substitute for D-7.\n"
            "Also PK, Jupiter, Beeja/Kshetra sphuta if present; NATAL Vimshottari for timing.\n"
            "Simple Remedies (only if 5th/7th-from-D-7, Jupiter, or PK show delay/affliction — be gentle): "
            "Thursday Jupiter — Santana Gopal mantra or Vishnu/Jupiter stuti, charity for children's welfare; "
            "respect Putrakaraka significations (guidance, protection of children); Beeja/Kshetra imbalance — "
            "simple vrata or charity on the day of the afflicted sphuta lord if cited; avoid alarmist or "
            "coercive remedies; emphasize patience during difficult 5th-lord or Saturn/Rahu dasa windows."
        ),
    ),
    TopicSpec(
        key="education",
        title="Education & Learning",
        parse_checklist=(
            "- [ ] Quote D-24 center label if present; else mark insufficient for D-24\n"
            "- [ ] D-24 'As' sign = ____ (if present)\n"
            "- [ ] Optional D-5 label/'As' if used\n"
            "- [ ] Natal Rasi 4th/5th/9th + Mercury/Jupiter placements/strength\n"
            "- [ ] Current natal Vimshottari MD + AD with start dates"
        ),
        focus=(
            "Analyze formal education, higher studies, technical vs traditional learning, "
            "teaching/research aptitude.\n"
            "Domain Depth: Look at 2nd house (early schooling), 4th house (formal degree), 5th house (intellect/scholarship), "
            "and 9th house (higher/foreign education). Assess Mercury (logic/memory) and Jupiter (wisdom). In D-24 (Siddhamsa), "
            "evaluate 4th, 5th, and 9th axes. Mention technical (Mars/Ketu/Saturn) vs traditional/humanities (Jupiter/Venus) inclinations.\n"
            "Primary Vargas: natal Rasi 4th/5th/9th + ASCII D-24 (Siddhamsa) when present; D-5 only as support.\n"
            "Do not invent a D-24 lagna if the block is missing.\n"
            "Use Mercury/Jupiter + NATAL Vimshottari education windows.\n"
            "Simple Remedies (if Mercury/Jupiter or 4th/5th/9th lords are weak): "
            "Wednesday Mercury — Saraswati respect, regular study schedule, donate books/stationery; "
            "Thursday Jupiter — guru seva, humility in learning; discipline over distraction during "
            "afflicted Mercury/Rahu periods; strengthen the house lord of the weakest education axis cited."
        ),
    ),
    TopicSpec(
        key="spiritual",
        title="Spiritual Progress",
        parse_checklist=(
            "- [ ] AK planet from Chara karaka table\n"
            "- [ ] Quote D-9 and any D-20 / D-60 center labels used\n"
            "- [ ] Each used varga's 'As' sign\n"
            "- [ ] Ketu / 12th/9th/5th Rasi factors cited from natal data\n"
            "- [ ] Current natal Vimshottari MD + AD; Moola Dasa line if used"
        ),
        focus=(
            "Analyze spiritual inclination, sadhana style, teachers, renunciation vs householder path, "
            "and awakening periods.\n"
            "Domain Depth: Examine 5th house (mantra/bhakti), 9th (guru/dharma), and 12th (moksha/letting go). "
            "Assess Atmakaraka (AK) placement in D-9 (Karakamsa) and Ishta Devata (12th from Karakamsa). Evaluate "
            "Ketu (mokshakaraka) and Jupiter. D-20 (Vimsamsa) indicates religious depth and sadhana. Check for "
            "Pravrajya (renunciation) yogas or heavy satvic planetary influence.\n"
            "Use AK, Ketu, Rasi 12th/9th/5th, ASCII D-9; include D-20/D-60 only if those blocks exist.\n"
            "Do not mix D-20 planets into D-60 claims or vice versa.\n"
            "Timing: NATAL Vimshottari; Moola Dasa only if the Moola table is present and quoted.\n"
            "Simple Remedies (match sadhana to AK, 9th/12th lords, Ketu/Jupiter — householder-friendly unless "
            "Pravrajya is clear): daily short japa of the Ishta Devata or AK lord's mantra; Thursday guru "
            "respect; Ketu — meditation, simplicity, reduce excessive material attachment; 5th house — "
            "mantra/bhakti path; 12th — charity, pilgrimage when feasible; avoid prescribing extreme "
            "renunciation unless the chart strongly supports it."
        ),
    ),
    TopicSpec(
        key="transits",
        title="Transit Outlook (Next 1 Year)",
        parse_checklist=(
            "- [ ] Analysis/as-of date = ____\n"
            "- [ ] Current natal Vimshottari MD + AD with start dates (quote natal table only)\n"
            "- [ ] Secondary snapshot date/place (if any) used ONLY for planet signs\n"
            "- [ ] List Ju/Sa/Ra/Ke/(Ma) signs from snapshot or stated transit data\n"
            "- [ ] Explicitly affirm: no secondary-chart dasas used"
        ),
        focus=(
            "Provide a practical 12-month transit + dasa outlook from the analysis date.\n"
            "Domain Depth: Synthesize double-transit (Jupiter and Saturn aspecting the same house/lord) to time major events. "
            "Evaluate Sade Sati (Saturn transiting 12th, 1st, 2nd from Natal Moon) or Ashtama Shani (Saturn in 8th from Moon). "
            "Assess Rahu/Ketu transits across the 1/7 or 4/10 axes. Judge transit impacts from both Lagna and Moon sign. "
            "Ground all transit triggers strictly within the running NATAL Vimshottari MD/AD's promise.\n"
            "Base houses on natal Rasi; secondary snapshot is gochara positions only.\n"
            "HARD RULE: never take Vimshottari/Sudasa/Narayana from the secondary chart.\n"
            "Timing backbone = NATAL Vimshottari MD/AD with quoted dates; optional natal Narayana/Sudasa.\n"
            "Cover Jupiter, Saturn, Rahu/Ketu, Mars relative to natal lagna/Moon/AL.\n"
            "Prefer quarterly themes unless month-level evidence is strong.\n"
            "Simple Remedies (timed to difficult transit/dasa windows only): Sade Sati/Ashtama Shani — "
            "Saturday Saturn seva, Shani stuti, discipline, avoid arrogance; afflicted Rahu/Ketu transit — "
            "charity, simplicity, avoid risky shortcuts; harsh Mars transit — Tuesday patience, avoid anger; "
            "benefic Jupiter transit — gratitude, dharma-aligned action to maximize the window; "
            "always link remedy to the specific transit + running MD/AD cited."
        ),
    ),
]


def build_user_prompt(
    topic: TopicSpec,
    chart_context: str,
    *,
    native_label: str | None = None,
    as_of: str | None = None,
    model_name: str | None = None,
) -> str:
    """Legacy single-call prompt (parse + predict). Prefer build_parse_prompt + build_prediction_prompt."""
    who = native_label or "the native"
    when = as_of or "today"
    model_line = f"Model: {model_name or DEFAULT_MODEL} (Gemini 3.1 Pro family)"
    return f"""Analyze the following Vedic chart data for {who}.

{model_line}
Topic: {topic.title}
Analysis date / reference: {when}

{PARSE_GUARDRAILS}

Topic-specific focus:
{topic.focus}

Literal checklist to complete in section 1 (fill every line; use 'insufficient data' if needed):
{topic.parse_checklist}

Required response structure:
1. Parsing checklist (completed, with quoted varga labels / dasa lines)
2. Key chart factors used
3. Core promise / pattern
4. Strengths and supports
5. Challenges / cautions
6. Timing notes (natal dasas / transits) — dates mandatory when timing is claimed
7. Practical guidance
8. Simple remedies (where applicable — tied to cited afflictions; skip or say none if chart is strong)

Chart data:
{chart_context}
"""


def build_parse_prompt(
    topic: TopicSpec,
    chart_context: str,
    *,
    native_label: str | None = None,
    as_of: str | None = None,
    model_name: str | None = None,
) -> str:
    who = native_label or "the native"
    when = as_of or "today"
    model_line = f"Model: {model_name or DEFAULT_MODEL} (parse step, temperature 0)"
    return f"""Extract chart facts for {who}. Do NOT interpret or predict.

{model_line}
Topic context: {topic.title}
Reference date: {when}

{PARSE_GUARDRAILS}

Topic-specific varga/dasa focus (for knowing what to extract):
{topic.focus}

Complete this checklist with quoted evidence from the chart data (use 'insufficient data' if missing):
{topic.parse_checklist}

Output ONLY the completed checklist and any quoted raw lines you relied on.
No predictions, remedies, or narrative interpretation.

Chart data:
{chart_context}
"""


def build_prediction_prompt(
    topic: TopicSpec,
    parse_summary: str,
    *,
    native_label: str | None = None,
    as_of: str | None = None,
    model_name: str | None = None,
) -> str:
    who = native_label or "the native"
    when = as_of or "today"
    model_line = f"Model: {model_name or DEFAULT_MODEL} (prediction step, temperature {PREDICTION_TEMPERATURE})"
    return f"""Interpret the following Vedic chart reading for {who}.

{model_line}
Topic: {topic.title}
Analysis date / reference: {when}

=== VERIFIED PARSE FACTS (temperature 0 — do not contradict) ===
{parse_summary}

Topic-specific focus:
{topic.focus}

Required response structure (sections 2–8 only; parse facts are already verified above):
2. Key chart factors used
3. Core promise / pattern
4. Strengths and supports
5. Challenges / cautions
6. Timing notes (natal dasas / transits) — dates mandatory when timing is claimed
7. Practical guidance
8. Simple remedies (where applicable — tied to cited afflictions; skip or say none if chart is strong)
"""
