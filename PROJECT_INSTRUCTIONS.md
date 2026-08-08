# Project Instructions

Edit this file to guide future coding changes in `vedicastroagent`.
Cursor / coding agents should treat this as the project brief.

## Product intent

Build a CLI Vedic astrology agent that:

1. Accepts a Jagannatha Hora chart export path (`.txt` / `.rtf`, including RTF saved as `.txt`).
2. Calls **Gemini 3.1 Pro** for multiple life areas.
3. Uses natal chart data (Vargas, dasas, karakas, ashtakavarga, shadbala, upagrahas).
4. May use a secondary chart block only as a **transit/gochara snapshot** (planet positions), never as natal dasa ownership.

## Gemini model

- Product name: **Gemini 3.1 Pro**
- Default API model id: **`gemini-3.1-pro-preview`**
- Defined in `src/vedicastroagent/gemini_client.py` as `DEFAULT_MODEL`
- Runtime override: env var `GEMINI_MODEL`
- Auth: `GEMINI_API_KEY` or `GOOGLE_API_KEY`
- Default sampling temperature: **0** (factual / deterministic; do not raise unless the user explicitly asks)

When docs or CLI text say “Gemini Pro” / “Gemini 3.1 Pro”, they mean this default unless overridden.

### Why prompts are strict

Incorrect D-2/D-4/dasa readings can come from **context extraction bugs** or from the **model misparsing** JH ASCII tables. Mitigations required in code:

- Extract labeled varga diamonds (`extract_varga_block`) and natal dasa sections (`extract_dasa_section`).
- Never match bare `"Hora"` for wealth.
- Never attach secondary-chart dasas to native timing.
- Each topic prompt must include a **literal parse checklist** and quote-before-interpret rules (`prompts.py`).

## Code map

| Path | Role |
|---|---|
| `src/vedicastroagent/cli.py` | CLI entrypoint |
| `src/vedicastroagent/agent.py` | Multi-topic orchestration (parallel Gemini calls by default) |
| `src/vedicastroagent/chart_loader.py` | RTF/text parse, varga/dasa extraction |
| `src/vedicastroagent/prompts.py` | System + per-topic parse checklists / focus |
| `src/vedicastroagent/gemini_client.py` | Gemini API wrapper + `DEFAULT_MODEL` |
| `tests/` | Parser/context/prompt tests |
| `README.md` | User-facing usage |

## Critical accuracy rules (do not regress)

- Default model must remain **`gemini-3.1-pro-preview`** unless the user explicitly changes it.
- Default temperature must remain **0** unless the user explicitly asks to change it.
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
- Add/adjust tests in `tests/` when changing chart parsing or default model id.
- Do not commit secrets (`.env`).
- Do not invent ephemeris precision the export does not contain.
- When tightening astrology accuracy, prefer prompt/checklist + extraction fixes; keep temperature at **0**.

## Verification checklist

After changes:

```bash
source .venv/bin/activate
pytest -q
vedicastroagent ~/Desktop/Srinu.txt --dry-run
vedicastroagent ~/Desktop/Srinu.txt -t wealth --name Srinu
```

Confirm dry-run shows:

- `Gemini model: gemini-3.1-pro-preview`
- `Varga D-2: found`, `Varga D-4: found`
- `Natal Vimsottari: found`
