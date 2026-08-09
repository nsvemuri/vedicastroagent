"""Orchestrate multi-topic Vedic analyses with Gemini or Claude."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from .chart_loader import ChartDocument, current_vimsottari_summary, extract_relevant_context, load_chart_file
from .llm import LLMClient, create_llm_client
from .prompts import (
    PARSE_SYSTEM_INSTRUCTION,
    PREDICTION_SYSTEM_INSTRUCTION,
    TOPICS,
    TopicSpec,
    build_parse_prompt,
    build_prediction_prompt,
)

# Default parallelism for multi-topic runs (I/O-bound LLM calls).
DEFAULT_WORKERS = 7


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
    provider: str = ""

    def to_markdown(self) -> str:
        meta = self.chart.metadata
        header = [
            f"# Vedic Astrology Report",
            "",
            f"- Source: `{self.chart.source_path}`",
            f"- Provider: `{self.provider}`",
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
    def __init__(self, client: LLMClient | None = None) -> None:
        self.client = client or create_llm_client()

    def analyze_file(
        self,
        path: str | Path,
        *,
        topics: list[str] | None = None,
        native_label: str | None = None,
        as_of: date | None = None,
        max_workers: int | None = None,
    ) -> AnalysisReport:
        chart = load_chart_file(path)
        return self.analyze_chart(
            chart,
            topics=topics,
            native_label=native_label,
            as_of=as_of,
            max_workers=max_workers,
        )

    def analyze_chart(
        self,
        chart: ChartDocument,
        *,
        topics: list[str] | None = None,
        native_label: str | None = None,
        as_of: date | None = None,
        max_workers: int | None = None,
    ) -> AnalysisReport:
        selected = _select_topics(topics)
        as_of = as_of or date.today()
        as_of_label = as_of.isoformat()
        report = AnalysisReport(
            chart=chart,
            model=self.client.config.model,
            provider=self.client.config.provider,
        )
        workers = _resolve_workers(max_workers, topic_count=len(selected))

        if workers <= 1 or len(selected) == 1:
            for topic in selected:
                report.results.append(
                    self._analyze_one_topic(
                        chart,
                        topic,
                        native_label=native_label,
                        as_of_label=as_of_label,
                        as_of_year=as_of.year,
                    )
                )
            return report

        # Parallel LLM calls; preserve canonical topic order in the report.
        indexed: dict[int, TopicResult] = {}
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(
                    self._analyze_one_topic,
                    chart,
                    topic,
                    native_label=native_label,
                    as_of_label=as_of_label,
                    as_of_year=as_of.year,
                ): idx
                for idx, topic in enumerate(selected)
            }
            for future in as_completed(futures):
                idx = futures[future]
                indexed[idx] = future.result()

        report.results = [indexed[i] for i in range(len(selected))]
        return report

    def _analyze_one_topic(
        self,
        chart: ChartDocument,
        topic: TopicSpec,
        *,
        native_label: str | None,
        as_of_label: str,
        as_of_year: int,
    ) -> TopicResult:
        context = extract_relevant_context(chart, topic.key)
        if topic.key == "transits":
            dasa = current_vimsottari_summary(chart, as_of_year=as_of_year)
            if dasa:
                context += "\n\n=== VIMSHOTTARI WINDOWS NEAR ANALYSIS DATE ===\n" + dasa
            context += (
                f"\n\nAnalysis reference date: {as_of_label}. "
                "Provide a forward 12-month outlook from this date."
            )

        parse_prompt = build_parse_prompt(
            topic,
            context,
            native_label=native_label,
            as_of=as_of_label,
            model_name=self.client.config.model,
        )
        parse_summary = self.client.generate_parse(
            system=PARSE_SYSTEM_INSTRUCTION,
            user=parse_prompt,
        )

        prediction_prompt = build_prediction_prompt(
            topic,
            parse_summary,
            native_label=native_label,
            as_of=as_of_label,
            model_name=self.client.config.model,
        )
        prediction = self.client.generate_prediction(
            system=PREDICTION_SYSTEM_INSTRUCTION,
            user=prediction_prompt,
        )

        response = (
            f"## 1. Parsing checklist\n\n{parse_summary.strip()}\n\n{prediction.strip()}"
        )
        return TopicResult(topic=topic, response=response, context_chars=len(context))


def _resolve_workers(max_workers: int | None, *, topic_count: int) -> int:
    if max_workers is not None:
        workers = max_workers
    else:
        env = os.getenv("VEDIC_MAX_WORKERS")
        workers = int(env) if env else DEFAULT_WORKERS
    if workers < 1:
        raise ValueError(f"max_workers must be >= 1, got {workers}")
    return min(workers, topic_count)


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
