from pathlib import Path

from vedicastroagent.chart_loader import extract_relevant_context, load_chart_file, strip_rtf
from vedicastroagent.prompts import TOPICS


FIXTURE = Path(__file__).parent / "fixtures" / "sample_chart.txt"


def test_strip_rtf_basic():
    rtf = r"{\rtf1\ansi\pard Natal Chart\par Date: March 15, 1981\par}"
    plain = strip_rtf(rtf)
    assert "Natal Chart" in plain
    assert "March 15, 1981" in plain


def test_load_dual_chart_fixture():
    chart = load_chart_file(FIXTURE)
    assert chart.metadata["date"] == "March 15, 1981"
    assert chart.secondary_text is not None
    assert chart.secondary_metadata["date"] == "May 12, 2026"
    assert "Vimsottari Dasa" in chart.natal_text
    assert "D-2 (US)" in chart.natal_text
    assert "D-4" in chart.natal_text


def test_topic_context_not_empty():
    chart = load_chart_file(FIXTURE)
    for topic in TOPICS:
        ctx = extract_relevant_context(chart, topic.key, max_chars=12000)
        assert "NATAL CHART CONTEXT" in ctx
        assert len(ctx) > 200
