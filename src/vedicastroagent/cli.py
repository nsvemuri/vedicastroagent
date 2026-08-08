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
from .prompts import TOPICS


def build_parser() -> argparse.ArgumentParser:
    topic_keys = [t.key for t in TOPICS]
    parser = argparse.ArgumentParser(
        prog="vedicastroagent",
        description=(
            "Analyze a Jagannatha Hora chart text/RTF export with Gemini Pro across "
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
        "--dry-run",
        action="store_true",
        help="Parse the chart and print extracted metadata/context sizes without calling Gemini.",
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
            return _dry_run(console, chart_path, args.topics, as_of)

        console.print(Panel.fit(f"Loading chart: [bold]{chart_path}[/bold]"))
        agent = VedicAstroAgent()
        report = agent.analyze_file(
            chart_path,
            topics=args.topics,
            native_label=args.name or chart_path.stem,
            as_of=as_of,
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


def _dry_run(console: Console, chart_path: Path, topics: list[str] | None, as_of: date) -> int:
    from .agent import _select_topics
    from .chart_loader import extract_relevant_context, current_vimsottari_summary

    chart = load_chart_file(chart_path)
    console.print(Panel.fit("[bold]Dry run — chart parsed successfully[/bold]"))
    console.print(f"Source: {chart.source_path}")
    console.print(f"Natal metadata: {chart.metadata}")
    if chart.secondary_text:
        console.print(f"Secondary metadata: {chart.secondary_metadata}")
    else:
        console.print("Secondary/transit snapshot: none")

    selected = _select_topics(topics)
    for topic in selected:
        ctx = extract_relevant_context(chart, topic.key)
        if topic.key == "transits":
            ctx += "\n" + current_vimsottari_summary(chart, as_of_year=as_of.year)
        console.print(f"- {topic.key}: context {len(ctx):,} chars")
    return 0


def _parse_as_of(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise SystemExit(f"Invalid --as-of date {value!r}; use YYYY-MM-DD") from exc


if __name__ == "__main__":
    sys.exit(main())
