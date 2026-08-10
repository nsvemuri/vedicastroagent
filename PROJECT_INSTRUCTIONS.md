# Project Instructions

Edit this file to guide future coding changes in `vedicastroagent`.
Cursor / coding agents should treat this as the project brief.

## Product intent

Build a CLI Vedic astrology agent that:

1. Accepts a Jagannatha Hora chart export path (`.txt` / `.rtf`, including RTF saved as `.txt`).
2. Calls **Gemini** or **Claude** for multiple life areas (user chooses one provider).
3. Uses natal chart data (Vargas, dasas, karakas, ashtakavarga, shadbala, upagrahas).
4. May use a secondary chart block only as a **transit/gochara snapshot** (planet positions), never as natal dasa ownership.

## LLM providers

### Gemini

- Product name: **Gemini 3.1 Pro**
- Default API model id: **`gemini-3.1-pro-preview`**
- Auth: `GEMINI_API_KEY` or `GOOGLE_API_KEY`
- Model override: `GEMINI_MODEL` or `--model`

### Claude

- Aliases: **`sonnet`** → `claude-sonnet-5`, **`opus`** → `claude-opus-5`, **`mythos`** → `claude-mythos-5`
- Auth: `ANTHROPIC_API_KEY` or `CLAUDE_API_KEY`
- Model override: `CLAUDE_MODEL` or `--model sonnet|opus|mythos|<full-id>`

### Provider selection

- CLI: `--provider gemini|claude`
- Env: `LLM_PROVIDER` (or `VEDIC_PROVIDER`)
- Auto: if only Claude key is set → `claude`; otherwise default **`gemini`**
- Users may configure **only Gemini** or **only Claude** — do not require both keys.

### Sampling (shared)

- Parse temperature: **0**
- Prediction temperature: **0.05**
- Defined in `src/vedicastroagent/llm.py`

### Why prompts are strict

Incorrect D-2/D-4/dasa readings can come from **context extraction bugs** or from the **model misparsing** JH ASCII tables. Mitigations required in code:

- Extract labeled varga diamonds (`extract_varga_block`) and natal dasa sections (`extract_dasa_section`).
- Never match bare `"Hora"` for wealth.
- Never attach secondary-chart dasas to native timing.
- Each topic prompt must include a **literal parse checklist** and quote-before-interpret rules (`prompts.py`).
- Prediction prompts must apply classical vitals when supported: Kendra/Trikona/Dusthana/Upachaya, Yogakaraka, yogas, dignities, aspects, functional benefic/malefic, **nakshatra/pada/nakshatra-lord/deity**, gandanta, and selective varga deities (`CLASSICAL_VEDIC_FRAMEWORK` in `prompts.py`).
- Prediction tone must be **fact-first**: no sugarcoating, no overweighting positives, no diplomatic vagueness on negatives (`FACTUALITY & TONE` in `prompts.py`).
- Prediction prompts must include the subject's **current age** (from natal `Date:` vs `--as-of` / today) and age-aware timing/guidance.
- Chart load must compute and inject **NATAL RASI CORE** (Lagna, Moon, graha houses, topic house-lords) into parse context and prediction prompts; transit topics also get **TRANSIT / GOCHARA CORE**. Prediction must not claim these D-1 facts are missing when the payload is present.

## Code map

| Path | Role |
|---|---|
| `src/vedicastroagent/cli.py` | CLI entrypoint (`--provider`, `--model`) |
| `src/vedicastroagent/agent.py` | Multi-topic orchestration (parallel LLM calls by default) |
| `src/vedicastroagent/llm.py` | Provider protocol, aliases, `create_llm_client()` |
| `src/vedicastroagent/gemini_client.py` | Gemini API wrapper |
| `src/vedicastroagent/claude_client.py` | Claude API wrapper |
| `src/vedicastroagent/chart_loader.py` | RTF/text parse, varga/dasa extraction |
| `src/vedicastroagent/prompts.py` | System + per-topic parse checklists / focus |
| `tests/` | Parser/context/prompt/provider tests |
| `README.md` | User-facing usage |

## Critical accuracy rules (do not regress)

- Default Gemini model must remain **`gemini-3.1-pro-preview`** unless the user explicitly changes it.
- Claude aliases must remain **`sonnet` / `opus` / `mythos`**.
- Default temperature must remain **0 for parse** and **0.05 for prediction** unless the user explicitly asks to change it.
- Each topic uses two LLM calls: parse (checklist, temp 0) then predict (sections 2–8, temp 0.05).
- Do **not** match bare `"Hora"` for wealth — it collides with `Hora Lord` / `Hora Lagna`. Use labeled **`D-2`** / **`D-4`** ASCII blocks.
- Extract full JH diamond charts via `extract_varga_block()`.
- Extract natal dasas via `extract_dasa_section()`; stop at the next dasa header.
- Prompts must teach South-Indian fixed-sign reading and Vimshottari MD/AD date parsing.
- Every topic in `TOPICS` must keep a non-empty `parse_checklist`.
- Secondary chart dasas must not be used for native timing.

## Topics currently supported

`career`, `wealth`, `marriage`, `children`, `education`, `spiritual`, `transits`

## How to request code changes

Add items under **Requested changes** below. Be concrete: file/area, desired behavior, and acceptance checks.

### Requested changes

<!-- Example:
- [ ] Add D-16 support for vehicle deep-dive under wealth
- [ ] Add structured JSON mode for parse checklist validation
-->

- [ ]

## Implementation preferences

- Prefer small, focused diffs; avoid drive-by refactors.
- Keep CLI usable with `--dry-run` (no API key required for parse checks).
- Add/adjust tests in `tests/` when changing chart parsing, providers, or default model ids.
- Do not commit secrets (`.env`).
- Do not invent ephemeris precision the export does not contain.
- When tightening astrology accuracy, prefer prompt/checklist + extraction fixes; keep parse temperature at **0**.

## Verification checklist

After changes:

```bash
source .venv/bin/activate
pytest -q
vedicastroagent ~/Desktop/Srinu.txt --dry-run
vedicastroagent ~/Desktop/Srinu.txt --dry-run --provider claude --model sonnet
vedicastroagent ~/Desktop/Srinu.txt -t wealth --name Srinu --provider gemini
```

Confirm dry-run shows:

- Provider + model labels
- `Varga D-2: found`, `Varga D-4: found`
- `Natal Vimsottari: found`
