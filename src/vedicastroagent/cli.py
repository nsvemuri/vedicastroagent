"""Command-line interface for the Vedic Astrology agent."""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from . import __version__
from .agent import VedicAstroAgent
from .chart_loader import load_chart_file
from .llm import CLAUDE_MODEL_ALIASES, PROVIDERS, create_llm_client, resolve_provider
from .prompts import TOPICS


def build_parser() -> argparse.ArgumentParser:
    topic_keys = [t.key for t in TOPICS]
    claude_aliases = ", ".join(CLAUDE_MODEL_ALIASES)
    parser = argparse.ArgumentParser(
        prog="vedicastroagent",
        description=(
            "Analyze a Jagannatha Hora chart text/RTF export with Gemini or Claude across "
            "career, wealth (D2/D4), marriage, children, education, spiritual progress, "
            "and a 1-year transit outlook."
        ),
    )
    parser.add_argument(
        "chart_path",
        nargs="?",
        help="Path to natal chart export (.txt or .rtf), e.g. ~/Desktop/Srinu.txt",
    )
    parser.add_argument(
        "-t",
        "--topics",
        nargs="+",
        metavar="TOPIC",
        help=f"Subset of topics to run. Choices: {', '.join(topic_keys)}",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Write full Markdown report to this path (directories created as needed).",
    )
    parser.add_argument(
        "--name",
        help="Optional native label used in prompts (e.g. Srinu).",
    )
    parser.add_argument(
        "--as-of",
        help="Reference date for transit outlook (YYYY-MM-DD). Defaults to today.",
    )
    parser.add_argument(
        "--provider",
        choices=PROVIDERS,
        default=None,
        help=(
            "LLM provider: gemini or claude. "
            "Default: LLM_PROVIDER env, else gemini if GEMINI_API_KEY is set, "
            "or claude if only ANTHROPIC_API_KEY is set."
        ),
    )
    parser.add_argument(
        "--model",
        default=None,
        help=(
            "Model id or Claude alias. "
            f"Claude aliases: {claude_aliases}. "
            "Gemini default: gemini-3.1-pro-preview (or GEMINI_MODEL). "
            "Claude default: sonnet (or CLAUDE_MODEL)."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse the chart and print extracted metadata/context sizes without calling an LLM.",
    )
    parser.add_argument(
        "-j",
        "--workers",
        type=int,
        default=None,
        metavar="N",
        help=(
            "Max parallel topic queries (default: 7, or VEDIC_MAX_WORKERS). "
            "Use 1 for sequential runs."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    console = Console(stderr=True)
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.chart_path:
        parser.print_help()
        return 2

    chart_path = Path(args.chart_path).expanduser()
    as_of = _parse_as_of(args.as_of) if args.as_of else date.today()

    try:
        if args.dry_run:
            return _dry_run(console, chart_path, args.topics, as_of, args.provider, args.model)

        console.print(Panel.fit(f"Loading chart: [bold]{chart_path}[/bold]"))
        client = create_llm_client(provider=args.provider, model=args.model)
        console.print(
            f"Provider: [bold]{client.config.provider}[/bold]  "
            f"Model: [bold]{client.config.model}[/bold]"
        )
        agent = VedicAstroAgent(client=client)
        report = agent.analyze_file(
            chart_path,
            topics=args.topics,
            native_label=args.name or chart_path.stem,
            as_of=as_of,
            max_workers=args.workers,
        )
    except Exception as exc:  # noqa: BLE001 - CLI boundary
        console.print(f"[red]Error:[/red] {exc}")
        return 1

    markdown = report.to_markdown()
    out_path = args.output
    if out_path is None:
        out_dir = Path("output")
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        out_path = out_dir / f"{chart_path.stem}-report-{stamp}.md"

    out_path = out_path.expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(markdown, encoding="utf-8")

    for item in report.results:
        console.rule(item.topic.title)
        console.print(Markdown(item.response))
        console.print()

    console.print(f"[green]Saved report:[/green] {out_path.resolve()}")
    return 0


def _dry_run(
    console: Console,
    chart_path: Path,
    topics: list[str] | None,
    as_of: date,
    provider: str | None,
    model: str | None,
) -> int:
    from .agent import _select_topics
    from .chart_loader import (
        current_vimsottari_summary,
        extract_dasa_section,
        extract_relevant_context,
        extract_varga_block,
        subject_age_as_of,
    )
    from .llm import create_llm_client

    chart = load_chart_file(chart_path)
    chosen = resolve_provider(provider)
    # Resolve model label without requiring an API key for dry-run display.
    try:
        client = create_llm_client(provider=provider, model=model)
        model_label = client.config.model
        provider_label = client.config.provider
    except RuntimeError:
        provider_label = chosen
        if chosen == "claude":
            from .llm import resolve_claude_model

            model_label = resolve_claude_model(model)
        else:
            import os

            from .llm import DEFAULT_GEMINI_MODEL

            model_label = model or os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)

    birth_date, subject_age = subject_age_as_of(chart, as_of)
    console.print(Panel.fit("[bold]Dry run — chart parsed successfully[/bold]"))
    console.print(f"Provider: {provider_label}")
    console.print(f"Model: {model_label}")
    console.print(f"Source: {chart.source_path}")
    console.print(f"Natal metadata: {chart.metadata}")
    if subject_age is not None:
        console.print(
            f"Subject age as of {as_of.isoformat()}: {subject_age} "
            f"(birth {birth_date.isoformat() if birth_date else 'unknown'})"
        )
    else:
        console.print(f"Subject age as of {as_of.isoformat()}: unknown")
    if chart.secondary_text:
        console.print(f"Secondary metadata: {chart.secondary_metadata}")
    else:
        console.print("Secondary/transit snapshot: none")

    for label in ("Rasi", "D-2", "D-4", "D-9", "D-10"):
        block = extract_varga_block(chart.natal_text, label)
        console.print(f"Varga {label}: {'found' if block else 'missing'}")
    vim = extract_dasa_section(chart.natal_text, "Vimsottari Dasa")
    console.print(f"Natal Vimsottari: {'found' if vim else 'missing'}")

    selected = _select_topics(topics)
    for topic in selected:
        ctx = extract_relevant_context(chart, topic.key, as_of=as_of)
        if topic.key == "transits" and "CURRENT VIMSHOTTARI" not in ctx and "VIMSHOTTARI WINDOWS" not in ctx:
            ctx += "\n" + current_vimsottari_summary(chart, as_of_year=as_of.year)
        has_d2 = "Varga block: D-2" in ctx
        has_dasa = "NATAL DASA TABLES" in ctx
        console.print(
            f"- {topic.key}: context {len(ctx):,} chars "
            f"(D-2={has_d2}, natal_dasa={has_dasa})"
        )
    return 0


def _parse_as_of(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise SystemExit(f"Invalid --as-of date {value!r}; use YYYY-MM-DD") from exc


if __name__ == "__main__":
    sys.exit(main())
