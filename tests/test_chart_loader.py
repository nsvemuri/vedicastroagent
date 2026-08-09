from pathlib import Path

from vedicastroagent.chart_loader import (
    extract_dasa_section,
    extract_relevant_context,
    extract_varga_block,
    load_chart_file,
    strip_rtf,
)
from vedicastroagent.llm import (
    CLAUDE_MODEL_ALIASES,
    DEFAULT_MODEL,
    PARSE_TEMPERATURE,
    PREDICTION_TEMPERATURE,
    create_llm_client,
    resolve_claude_model,
    resolve_provider,
)
from vedicastroagent.prompts import SYSTEM_INSTRUCTION, TOPICS, build_user_prompt


FIXTURE = Path(__file__).parent / "fixtures" / "sample_chart.txt"


def test_default_model_is_gemini_31_pro():
    assert DEFAULT_MODEL == "gemini-3.1-pro-preview"
    assert "gemini-3.1-pro-preview" in SYSTEM_INSTRUCTION


def test_default_temperature_is_zero_for_parse():
    from vedicastroagent.gemini_client import GeminiConfig

    assert PARSE_TEMPERATURE == 0.0
    assert PREDICTION_TEMPERATURE == 0.05
    assert GeminiConfig.parse_temperature == 0.0
    assert GeminiConfig.prediction_temperature == 0.05


def test_claude_aliases_resolve():
    assert set(CLAUDE_MODEL_ALIASES) == {"sonnet", "opus", "mythos"}
    assert resolve_claude_model("sonnet") == "claude-sonnet-5"
    assert resolve_claude_model("opus") == "claude-opus-5"
    assert resolve_claude_model("mythos") == "claude-mythos-5"
    assert resolve_claude_model("claude-sonnet-5") == "claude-sonnet-5"


def test_resolve_provider_aliases():
    assert resolve_provider("gemini") == "gemini"
    assert resolve_provider("google") == "gemini"
    assert resolve_provider("claude") == "claude"
    assert resolve_provider("anthropic") == "claude"


def test_create_llm_client_requires_matching_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("CLAUDE_API_KEY", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)

    try:
        create_llm_client(provider="gemini")
        raised = False
    except RuntimeError as exc:
        raised = True
        assert "GEMINI_API_KEY" in str(exc)
    assert raised

    try:
        create_llm_client(provider="claude", model="sonnet")
        raised = False
    except RuntimeError as exc:
        raised = True
        assert "ANTHROPIC_API_KEY" in str(exc) or "CLAUDE_API_KEY" in str(exc)
    assert raised


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


def test_extract_varga_and_dasa_blocks():
    chart = load_chart_file(FIXTURE)
    d2 = extract_varga_block(chart.natal_text, "D-2")
    d4 = extract_varga_block(chart.natal_text, "D-4")
    assert d2 and "D-2" in d2
    assert "Hora Lord" not in d2
    assert d4 and "D-4" in d4
    vim = extract_dasa_section(chart.natal_text, "Vimsottari Dasa")
    assert vim and "Ket  Ket 2025-07-29" in vim
    assert "Moola Dasa" not in vim


def test_wealth_context_labels_d2_d4_and_natal_dasas():
    chart = load_chart_file(FIXTURE)
    ctx = extract_relevant_context(chart, "wealth", max_chars=40000)
    assert "Varga block: D-2" in ctx
    assert "Varga block: D-4" in ctx
    assert "NATAL DASA TABLES" in ctx
    assert "Vimsottari Dasa" in ctx
    assert "NOT natal dasas" in ctx
    # Must not confuse Hora Lord section as the D-2 chart source of truth alone.
    assert "Hora Lord" not in ctx.split("Varga block: D-2")[1].split("Varga block:")[0]


def test_topic_context_not_empty():
    chart = load_chart_file(FIXTURE)
    for topic in TOPICS:
        ctx = extract_relevant_context(chart, topic.key, max_chars=20000)
        assert "NATAL CHART METADATA" in ctx
        assert len(ctx) > 200
        assert topic.parse_checklist.strip()


def test_wealth_prompt_mentions_d2_parsing_rules():
    wealth = next(t for t in TOPICS if t.key == "wealth")
    prompt = build_user_prompt(wealth, "chart...", native_label="Srinu", model_name=DEFAULT_MODEL)
    assert "D-2" in prompt
    assert "Hora Lord" in prompt
    assert "PARSE-FIRST" in prompt
    assert "Literal checklist" in prompt
    assert DEFAULT_MODEL in prompt


def test_all_topics_have_parse_checklists():
    for topic in TOPICS:
        prompt = build_user_prompt(topic, "chart...")
        assert "Literal checklist" in prompt
        assert "As" in topic.parse_checklist or "MD" in topic.parse_checklist
        assert topic.key in {"career", "wealth", "marriage", "children", "education", "spiritual", "transits"}


def test_topics_include_remedy_guidance():
    assert "SIMPLE REMEDIES" in SYSTEM_INSTRUCTION
    for topic in TOPICS:
        assert "Simple Remedies" in topic.focus
        prompt = build_user_prompt(topic, "chart...")
        assert "Simple remedies" in prompt


def test_two_phase_prompts_exist():
    from vedicastroagent.prompts import build_parse_prompt, build_prediction_prompt

    topic = next(t for t in TOPICS if t.key == "wealth")
    parse_p = build_parse_prompt(topic, "chart...")
    assert "Do NOT interpret" in parse_p
    assert "temperature 0" in parse_p
    pred_p = build_prediction_prompt(topic, "parse facts here")
    assert "VERIFIED PARSE FACTS" in pred_p
    assert "sections 2–8" in pred_p
    assert "0.05" in pred_p


def test_resolve_workers_caps_to_topic_count():
    from vedicastroagent.agent import DEFAULT_WORKERS, _resolve_workers

    assert _resolve_workers(None, topic_count=7) == min(DEFAULT_WORKERS, 7)
    assert _resolve_workers(4, topic_count=7) == 4
    assert _resolve_workers(10, topic_count=3) == 3
    assert _resolve_workers(1, topic_count=7) == 1
