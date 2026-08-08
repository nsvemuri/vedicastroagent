"""Orchestrate multi-topic Vedic analyses with Gemini."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from .chart_loader import ChartDocument, current_vimsottari_summary, extract_relevant_context, load_chart_file
from .gemini_client import GeminiClient
from .prompts import SYSTEM_INSTRUCTION, TOPICS, TopicSpec, build_user_prompt


@dataclass
class TopicResult:
    topic: TopicSpec
    response: str
    context_chars: int


@dataclass
class AnalysisReport:
    chart: ChartDocument
    results: list[TopicResult] = field(default_factory=list)
    model: str = ""

    def to_markdown(self) -> str:
        meta = self.chart.metadata
        header = [
            f"# Vedic Astrology Report",
            "",
            f"- Source: `{self.chart.source_path}`",
            f"- Model: `{self.model}`",
            f"- Birth date: {meta.get('date', 'unknown')}",
            f"- Birth time: {meta.get('time', 'unknown')}",
            f"- Place: {meta.get('location_name') or meta.get('place', 'unknown')}",
        ]
        if self.chart.has_transit_snapshot:
            sm = self.chart.secondary_metadata
            header.append(
                f"- Secondary snapshot: {sm.get('date', 'unknown')} @ "
                f"{sm.get('location_name') or sm.get('place', 'unknown')}"
            )
        header.append("")
        parts = ["\n".join(header)]
        for item in self.results:
            parts.append(f"## {item.topic.title}\n\n{item.response.strip()}\n")
        return "\n".join(parts).strip() + "\n"


class VedicAstroAgent:
    def __init__(self, client: GeminiClient | None = None) -> None:
        self.client = client or GeminiClient()

    def analyze_file(
        self,
        path: str | Path,
        *,
        topics: list[str] | None = None,
        native_label: str | None = None,
        as_of: date | None = None,
    ) -> AnalysisReport:
        chart = load_chart_file(path)
        return self.analyze_chart(
            chart,
            topics=topics,
            native_label=native_label,
            as_of=as_of,
        )

    def analyze_chart(
        self,
        chart: ChartDocument,
        *,
        topics: list[str] | None = None,
        native_label: str | None = None,
        as_of: date | None = None,
    ) -> AnalysisReport:
        selected = _select_topics(topics)
        as_of = as_of or date.today()
        as_of_label = as_of.isoformat()
        report = AnalysisReport(chart=chart, model=self.client.config.model)

        for topic in selected:
            context = extract_relevant_context(chart, topic.key)
            if topic.key == "transits":
                dasa = current_vimsottari_summary(chart, as_of_year=as_of.year)
                if dasa:
                    context += (
                        "\n\n=== VIMSHOTTARI WINDOWS NEAR ANALYSIS DATE ===\n" + dasa
                    )
                context += (
                    f"\n\nAnalysis reference date: {as_of_label}. "
                    "Provide a forward 12-month outlook from this date."
                )

            prompt = build_user_prompt(
                topic,
                context,
                native_label=native_label,
                as_of=as_of_label,
                model_name=self.client.config.model,
            )
            response = self.client.generate(system=SYSTEM_INSTRUCTION, user=prompt)
            report.results.append(
                TopicResult(topic=topic, response=response, context_chars=len(context))
            )
        return report


def _select_topics(topics: list[str] | None) -> list[TopicSpec]:
    if not topics:
        return list(TOPICS)
    wanted = {t.strip().lower() for t in topics}
    aliases = {
        "profession": "career",
        "job": "career",
        "money": "wealth",
        "finance": "wealth",
        "property": "wealth",
        "spouse": "marriage",
        "relationship": "marriage",
        "progeny": "children",
        "kids": "children",
        "studies": "education",
        "learning": "education",
        "spirituality": "spiritual",
        "moksha": "spiritual",
        "transit": "transits",
        "gochara": "transits",
    }
    normalized = {aliases.get(t, t) for t in wanted}
    selected = [t for t in TOPICS if t.key in normalized]
    if not selected:
        known = ", ".join(t.key for t in TOPICS)
        raise ValueError(f"No matching topics in {topics!r}. Known topics: {known}")
    return selected
