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
    DENSE_TOPIC_PREDICTION_MAX_OUTPUT_TOKENS,
    PARSE_TEMPERATURE,
    PREDICTION_TEMPERATURE,
    create_llm_client,
    prediction_max_output_tokens,
    resolve_claude_model,
    resolve_provider,
)
from vedicastroagent.prompts import (
    ALL_TOPICS,
    OPTIONAL_TOPICS,
    SYSTEM_INSTRUCTION,
    TOPICS,
    build_user_prompt,
)


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


def test_claude_models_omit_temperature():
    from vedicastroagent.llm import claude_sampling_kwargs, claude_supports_temperature

    for model in (
        "claude-sonnet-5",
        "claude-sonnet-4-6",
        "claude-opus-5",
        "claude-opus-4-7",
        "claude-opus-4-8",
        "claude-mythos-5",
    ):
        assert not claude_supports_temperature(model), model
        assert claude_sampling_kwargs(model, 0.05) == {}
        assert claude_sampling_kwargs(model, 0.0) == {}


def test_claude_token_budgets_leave_room_for_thinking():
    from vedicastroagent.claude_client import (
        DEFAULT_CLAUDE_PARSE_MAX_TOKENS,
        DEFAULT_CLAUDE_PREDICTION_MAX_TOKENS,
        ClaudeConfig,
    )

    assert DEFAULT_CLAUDE_PARSE_MAX_TOKENS >= 8192
    assert DEFAULT_CLAUDE_PREDICTION_MAX_TOKENS >= 20480
    cfg = ClaudeConfig()
    assert cfg.parse_max_output_tokens >= 8192
    assert cfg.max_output_tokens >= 20480
    assert cfg.parse_effort == "low"
    assert cfg.prediction_effort == "medium"


def test_spiritual_prediction_gets_extra_output_budget():
    assert prediction_max_output_tokens("career", 20480) == 20480
    assert prediction_max_output_tokens("spiritual", 20480) == DENSE_TOPIC_PREDICTION_MAX_OUTPUT_TOKENS
    assert prediction_max_output_tokens("longevity", 20480) == DENSE_TOPIC_PREDICTION_MAX_OUTPUT_TOKENS
    assert prediction_max_output_tokens("spiritual", 32768) == 32768


def test_claude_client_uses_streaming_for_long_requests(monkeypatch):
    """SDK raises if non-streaming max_tokens implies >10 minutes; we must stream."""
    from types import SimpleNamespace

    from vedicastroagent.claude_client import ClaudeClient, ClaudeConfig

    class FakeStream:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get_final_message(self):
            return SimpleNamespace(
                content=[SimpleNamespace(type="text", text="streamed ok")],
                stop_reason="end_turn",
                usage=SimpleNamespace(output_tokens=3),
            )

    class FakeMessages:
        def __init__(self):
            self.stream_calls = 0
            self.create_calls = 0

        def stream(self, **kwargs):
            self.stream_calls += 1
            assert kwargs["max_tokens"] >= 8192
            assert "temperature" not in kwargs
            system = kwargs["system"]
            assert isinstance(system, list)
            assert system[0].get("cache_control") == {"type": "ephemeral"}
            return FakeStream()

        def create(self, **kwargs):
            self.create_calls += 1
            raise AssertionError("non-streaming create must not be used")

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    client = ClaudeClient(ClaudeConfig(model="sonnet", api_key="test-key"))
    fake = FakeMessages()
    client._client = SimpleNamespace(messages=fake)

    out = client.generate_parse(system="sys", user="user")
    assert out == "streamed ok"
    assert fake.stream_calls == 1
    assert fake.create_calls == 0


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
    assert "VIMSHOTTARI" in ctx.upper()
    assert "secondary-chart dasas" in ctx
    # Must not confuse Hora Lord section as the D-2 chart source of truth alone.
    assert "Hora Lord" not in ctx.split("Varga block: D-2")[1].split("Varga block:")[0]
    assert "Mrityu Sphuta" in ctx
    assert "Beeja Sphuta" in ctx
    assert "CURRENT VIMSHOTTARI" in ctx
    assert "NEXT MAHADASA" in ctx or "NEXT ANTARDASA" in ctx
    # Cost trim that does not drop sphutas: no secondary Rasi diamond on wealth parse.
    assert "--- Transit snapshot Rasi ---" not in ctx


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
    for topic in ALL_TOPICS:
        assert "Simple Remedies" in topic.focus
        prompt = build_user_prompt(topic, "chart...")
        assert "Simple remedies" in prompt


def test_all_topics_require_topic_specific_yoga_scan():
    from vedicastroagent.prompts import PREDICTION_SYSTEM_INSTRUCTION, build_prediction_prompt

    assert "Topic-specific yogas are mandatory" in PREDICTION_SYSTEM_INSTRUCTION
    for topic in ALL_TOPICS:
        assert "Topic-specific yogas (mandatory scan" in topic.focus, topic.key
        assert "present / partial-broken / absent" in topic.focus, topic.key
        # Parse checklists should capture lord associations that feed yoga judgment.
        assert "Associations" in topic.parse_checklist or topic.key == "transits"
        if topic.key == "transits":
            assert "yoga-relevant lords" in topic.parse_checklist
    wealth = next(t for t in TOPICS if t.key == "wealth")
    pred = build_prediction_prompt(wealth, "parse facts")
    assert "Topic-specific yogas from the focus above" in pred
    assert "topic-specific yogas" in pred
    assert "After the yoga list, continue through sections 4–8" in pred
    assert "one short line" in PREDICTION_SYSTEM_INSTRUCTION


def test_prediction_tone_is_fact_first():
    from vedicastroagent.prompts import PREDICTION_SYSTEM_INSTRUCTION, build_prediction_prompt

    assert "FACTUALITY & TONE" in SYSTEM_INSTRUCTION
    assert "anti-sugarcoating" in SYSTEM_INSTRUCTION
    assert "Do NOT overweight positives" in SYSTEM_INSTRUCTION
    assert "forced optimism" in PREDICTION_SYSTEM_INSTRUCTION
    topic = next(t for t in TOPICS if t.key == "wealth")
    pred_p = build_prediction_prompt(topic, "parse facts")
    assert "Do not highlight positives more than the chart warrants" in pred_p
    assert "net assessment first" in pred_p


def test_subject_age_from_natal_date():
    from datetime import date

    from vedicastroagent.chart_loader import age_years, parse_jh_date, subject_age_as_of

    assert parse_jh_date("March 15, 1981") == date(1981, 3, 15)
    assert age_years(date(1981, 3, 15), date(2026, 8, 10)) == 45
    assert age_years(date(1981, 3, 15), date(2026, 3, 14)) == 44
    chart = load_chart_file(FIXTURE)
    birth, age = subject_age_as_of(chart, date(2026, 8, 10))
    assert birth == date(1981, 3, 15)
    assert age == 45


def test_prediction_prompt_includes_subject_age():
    from vedicastroagent import __version__
    from vedicastroagent.prompts import PREDICTION_SYSTEM_INSTRUCTION, build_prediction_prompt

    assert __version__.startswith("0.3.")
    assert "current age" in PREDICTION_SYSTEM_INSTRUCTION
    topic = next(t for t in TOPICS if t.key == "marriage")
    pred_p = build_prediction_prompt(
        topic,
        "parse facts",
        as_of="2026-08-10",
        birth_date="1981-03-15",
        subject_age=45,
    )
    assert "Subject's current age as of 2026-08-10: 45 completed years" in pred_p
    assert "birth date: 1981-03-15" in pred_p
    assert "Factor the subject's current age" in pred_p
    assert "current age/life stage" in pred_p


def test_natal_rasi_core_payload_for_career_and_transits():
    from vedicastroagent.chart_loader import (
        format_natal_rasi_core,
        format_prediction_chart_payload,
        format_transit_rasi_core,
        parse_body_longitude_table,
    )
    from vedicastroagent.prompts import build_parse_prompt, build_prediction_prompt

    chart = load_chart_file(FIXTURE)
    bodies = parse_body_longitude_table(chart.natal_text)
    assert bodies["Lagna"]["rasi"] == "Ar"
    assert bodies["Moon"]["rasi"] == "Ge"

    career_core = format_natal_rasi_core(chart, topic="career")
    assert "Natal Lagna: Aries (Ar)" in career_core
    assert "Lagna lord: Mars in Pi" in career_core
    assert "House 10 sign Cp" in career_core
    assert "lord Saturn in Vi" in career_core

    transit_core = format_transit_rasi_core(chart)
    assert transit_core is not None
    assert "Transit Jupiter" in transit_core
    assert "natal house" in transit_core

    career_ctx = extract_relevant_context(chart, "career")
    assert "NATAL RASI CORE" in career_ctx
    transit_ctx = extract_relevant_context(chart, "transits")
    assert "NATAL RASI CORE" in transit_ctx
    assert "TRANSIT / GOCHARA CORE" in transit_ctx

    career = next(t for t in TOPICS if t.key == "career")
    transits = next(t for t in TOPICS if t.key == "transits")
    assert "NATAL RASI CORE" in career.parse_checklist
    assert "10th lord" in career.parse_checklist
    assert "Natal Lagna sign" in transits.parse_checklist
    assert "Natal Moon sign" in transits.parse_checklist
    assert "TRANSIT / GOCHARA CORE" in transits.parse_checklist

    parse_p = build_parse_prompt(career, career_ctx)
    assert "NATAL RASI CORE" in parse_p
    pred_p = build_prediction_prompt(
        career,
        "parse facts",
        natal_core_payload=career_core,
    )
    assert "AUTHORITATIVE CHART LOAD PAYLOAD" in pred_p
    assert "Lagna lord: Mars in Pi" in pred_p
    assert "Do not claim natal Lagna" in pred_p

    transit_pred = build_prediction_prompt(
        transits,
        "parse facts",
        natal_core_payload=format_natal_rasi_core(chart, topic="transits"),
        transit_core_payload=transit_core,
    )
    assert "Natal Moon: Gemini" in transit_pred
    assert "Transit Jupiter" in transit_pred

    from datetime import date

    wealth_payload = format_prediction_chart_payload(chart, "wealth", as_of=date(2026, 8, 10))
    assert "PAYLOAD INVENTORY" in wealth_payload
    assert "SPHUTA TABLE" in wealth_payload
    assert "CURRENT VIMSHOTTARI" in wealth_payload
    assert "Varga D-2: FOUND" in wealth_payload
    assert "Varga D-4: FOUND" in wealth_payload
    assert "Chaturthamsa" in wealth_payload and "SKIPPED" in wealth_payload
    assert "Natal dasa 'Vimsottari Dasa': FOUND" in wealth_payload
    assert "TRANSIT / GOCHARA CORE: FOUND" in wealth_payload
    assert "Varga block: D-2" in wealth_payload
    assert "Varga block: D-4" in wealth_payload
    assert "NATAL DASA TABLES" in wealth_payload
    wealth = next(t for t in TOPICS if t.key == "wealth")
    wealth_pred = build_prediction_prompt(
        wealth,
        "parse facts",
        chart_load_payload=wealth_payload,
    )
    assert "Varga D-2: FOUND" in wealth_pred
    assert "natal dasas" in wealth_pred.lower()
    assert "insufficient data" in wealth_pred.lower()  # only allowed for NOT FOUND items


def test_two_phase_prompts_exist():
    from vedicastroagent.prompts import (
        CLASSICAL_VEDIC_FRAMEWORK,
        PREDICTION_SYSTEM_INSTRUCTION,
        build_parse_prompt,
        build_prediction_prompt,
    )

    topic = next(t for t in TOPICS if t.key == "wealth")
    parse_p = build_parse_prompt(topic, "chart...")
    assert "Do NOT interpret" in parse_p
    assert "temperature 0" in parse_p
    assert "CLASSICAL VEDIC VITALS" not in parse_p  # full framework is prediction-only
    assert "Simple Remedies" not in parse_p  # parse must not ship prediction focus
    assert "PARSE-FIRST PROTOCOL" not in parse_p  # already in parse system prompt
    pred_p = build_prediction_prompt(topic, "parse facts here")
    assert "VERIFIED PARSE FACTS" in pred_p
    assert "sections 2–8" in pred_p
    assert "0.05" in pred_p
    assert "Yogakaraka" in pred_p
    assert "Kendra" in pred_p and "Trikona" in pred_p and "Dusthana" in pred_p
    assert "Yogakaraka" in CLASSICAL_VEDIC_FRAMEWORK
    assert "Upachaya" in CLASSICAL_VEDIC_FRAMEWORK
    assert "Maraka" in CLASSICAL_VEDIC_FRAMEWORK
    assert "Badhaka" in CLASSICAL_VEDIC_FRAMEWORK
    assert "Nakshatra" in CLASSICAL_VEDIC_FRAMEWORK
    assert "Gandanta" in CLASSICAL_VEDIC_FRAMEWORK
    assert "nakshatra lord" in CLASSICAL_VEDIC_FRAMEWORK.lower()
    assert "Divisional (varga) deities" in CLASSICAL_VEDIC_FRAMEWORK
    assert "CLASSICAL VEDIC VITALS" in PREDICTION_SYSTEM_INSTRUCTION
    assert "Yogakaraka" in PREDICTION_SYSTEM_INSTRUCTION
    assert "gandanta" in pred_p.lower()
    assert "Nakshatra" in pred_p


def test_topic_payloads_omit_off_topic_chart_dumps():
    from datetime import date

    from vedicastroagent.chart_loader import format_prediction_chart_payload

    chart = load_chart_file(FIXTURE)
    career_ctx = extract_relevant_context(chart, "career", as_of=date(2026, 8, 10))
    wealth_ctx = extract_relevant_context(chart, "wealth", as_of=date(2026, 8, 10))
    # Career must not pull D-2/D-4; wealth must not pull D-10.
    assert "Varga block: D-10" in career_ctx
    assert "Varga block: D-2" not in career_ctx
    assert "Varga block: D-2" in wealth_ctx
    assert "Varga block: D-10" not in wealth_ctx
    # Alias duplicates and secondary Rasi diamonds stay out of prediction payload.
    marriage_payload = format_prediction_chart_payload(chart, "marriage", as_of=date(2026, 8, 10))
    assert "Varga D-9: FOUND" in marriage_payload
    assert "Varga block: Navamsa" not in marriage_payload
    assert "CURRENT VIMSHOTTARI" in wealth_ctx
    assert "Mrityu Sphuta" in wealth_ctx


def test_resolve_workers_caps_to_topic_count():
    from vedicastroagent.agent import DEFAULT_WORKERS, _resolve_workers

    assert _resolve_workers(None, topic_count=7) == min(DEFAULT_WORKERS, 7)
    assert _resolve_workers(4, topic_count=7) == 4
    assert _resolve_workers(10, topic_count=3) == 3
    assert _resolve_workers(1, topic_count=7) == 1


def test_longevity_is_opt_in_and_uses_full_jhora_profile():
    from datetime import date

    from vedicastroagent.agent import _select_topics
    from vedicastroagent.chart_loader import format_prediction_chart_payload
    from vedicastroagent.prompts import PREDICTION_SYSTEM_INSTRUCTION, build_prediction_prompt

    assert "longevity" not in {t.key for t in TOPICS}
    assert {t.key for t in OPTIONAL_TOPICS} == {"longevity"}
    assert [t.key for t in _select_topics(None)] == [t.key for t in TOPICS]
    assert [t.key for t in _select_topics(["longevity"])] == ["longevity"]
    assert [t.key for t in _select_topics(["ayur"])] == ["longevity"]

    chart = load_chart_file(FIXTURE)
    ctx = extract_relevant_context(chart, "longevity", as_of=date(2026, 8, 10))
    payload = format_prediction_chart_payload(chart, "longevity", as_of=date(2026, 8, 10))
    assert "ENTIRE NATAL JHORA EXPORT" in ctx
    assert "ENTIRE NATAL JHORA EXPORT" in payload
    assert "FULL NATAL JH EXPORT: FOUND" in payload
    assert "Mrityu Sphuta" in payload
    assert "House 8 sign" in payload
    assert len(payload) > len(format_prediction_chart_payload(chart, "career", as_of=date(2026, 8, 10)))

    lon = next(t for t in ALL_TOPICS if t.key == "longevity")
    assert "PRATYANTARDASA" in lon.focus or "peak month" in lon.focus
    assert "calendar **day** of death" in lon.focus or "calendar day of death" in lon.focus
    assert "Marana Karaka Sthana" in lon.focus
    pred = build_prediction_prompt(lon, "parse facts", chart_load_payload=payload)
    assert "peak month" in PREDICTION_SYSTEM_INSTRUCTION
    assert "PRATYANTARDASA" in pred
    assert "peak YYYY-MM" in pred
    assert "ENTIRE NATAL JHORA EXPORT" in pred
    assert "COMPUTED VIMSHOTTARI PRATYANTARDASA" in payload
    assert "peak 20" in payload


def test_vimsottari_pratyantardasa_pins_peak_month():
    from datetime import date

    from vedicastroagent.chart_loader import (
        split_vimsottari_pratyantardasa,
        vimsottari_current_and_next,
    )

    pds = split_vimsottari_pratyantardasa("Ven", date(2025, 12, 24), date(2027, 2, 22))
    assert len(pds) == 9
    assert pds[0][0] == "Venus"
    assert pds[0][1] == date(2025, 12, 24)
    assert pds[-1][2] == date(2027, 2, 22)
    assert pds[1][0] == "Sun"

    chart = load_chart_file(FIXTURE)
    labeled = vimsottari_current_and_next(chart, date(2026, 8, 10))
    assert "COMPUTED VIMSHOTTARI PRATYANTARDASA" in labeled
    assert "CURRENT PD" in labeled
    assert "NEXT PD" in labeled
    assert "peak 202" in labeled
