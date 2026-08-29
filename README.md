# Vedic Astrology Agent

CLI agent that reads a **Jagannatha Hora** natal chart export (plain text or RTF, including `.txt` files that are actually RTF) and runs focused analyses with either:

- **Gemini 3.1 Pro** (`gemini-3.1-pro-preview` by default), or
- **Claude** — pick **`sonnet`**, **`opus`**, or **`mythos`**

Topics:

- Career
- Wealth (Hora **D-2** and Chaturthamsa **D-4**)
- Marriage
- Children
- Education
- Spiritual progress
- Transit outlook for the next **1 year**

It uses the rich JH dump you already have: D-1, planetary longitudes/nakshatra/pada, divisional charts, Jaimini chara karakas, Gulika/Mandi, ashtakavarga, shadbala, dasas, and (when present) a second chart block as a transit/current snapshot.

## Setup

```bash
cd vedicastroagent
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .

cp .env.example .env
```

Put **only the key for the provider you use** in `.env`:

- Gemini-only users: set `GEMINI_API_KEY`
- Claude-only users: set `ANTHROPIC_API_KEY` and `LLM_PROVIDER=claude` (or pass `--provider claude`)

Environment variables:

| Variable | Purpose |
|---|---|
| `LLM_PROVIDER` | `gemini` or `claude` (optional if only one key is present) |
| `GEMINI_API_KEY` | Required for Gemini (or `GOOGLE_API_KEY`) |
| `GEMINI_MODEL` | Optional Gemini model id; default `gemini-3.1-pro-preview` |
| `ANTHROPIC_API_KEY` | Required for Claude (or `CLAUDE_API_KEY`) |
| `CLAUDE_MODEL` | Claude alias `sonnet` / `opus` / `mythos`, or a full id like `claude-sonnet-5` |
| `VEDIC_MAX_WORKERS` | Optional parallel topic workers; **default `7`** (use `1` for sequential) |

Generation defaults (shared by both providers):

| Setting | Default | Why |
|---|---|---|
| Parse temperature | **0** | Factual varga/dasa extraction |
| Prediction temperature | **0.05** | Interpretation/prediction (minimal sampling) |
| Topic parallelism | **parallel** | Each life-area query is an independent LLM call |
| Claude effort | **low parse / medium predict** | Extraction stays cheap; interpretation keeps medium thinking |
| Claude max tokens | **8k parse / 20k predict** (spiritual **24k**) | Room for thinking + full sections; override `CLAUDE_*_MAX_TOKENS` |

For contributor / coding-agent guidance you can edit, see [`PROJECT_INSTRUCTIONS.md`](PROJECT_INSTRUCTIONS.md).

## Usage

```bash
# Parse only (no API calls)
vedicastroagent ~/Desktop/Srinu.txt --dry-run

# Gemini (default when GEMINI_API_KEY is set)
vedicastroagent ~/Desktop/Srinu.txt --name Srinu --provider gemini

# Claude — pick sonnet, opus, or mythos
vedicastroagent ~/Desktop/Srinu.txt --name Srinu --provider claude --model sonnet
vedicastroagent ~/Desktop/Srinu.txt --provider claude --model opus
vedicastroagent ~/Desktop/Srinu.txt --provider claude --model mythos

# Selected topics
vedicastroagent ~/Desktop/Srinu.txt -t career wealth marriage transits

# Custom output path + transit reference date
vedicastroagent ~/Desktop/Srinu.txt -o output/srinu.md --as-of 2026-08-08

# Parallelism (topic LLM calls run concurrently by default)
vedicastroagent ~/Desktop/Srinu.txt -j 7          # default-ish: up to 7 parallel topics
vedicastroagent ~/Desktop/Srinu.txt --workers 1   # sequential (debugging / rate limits)
```

Or as a module:

```bash
python -m vedicastroagent ~/Desktop/Srinu.txt --dry-run
```

Reports are written as Markdown under `output/` by default.

## Chart file expectations

Works best with JH text/RTF exports that include:

- Natal header (date/time/place)
- Body longitude table (rasi + navamsa)
- Divisional chart ASCII blocks (D-2, D-4, D-7, D-9, D-10, D-20, D-24, …)
- Chara karakas, ashtakavarga, shadbala
- Vimshottari / other dasas

If the file contains **two** `Natal Chart` blocks (birth chart + a later snapshot), the second block is treated as a transit/current reference for timing topics.

Pushkara Navamsha is deduced by the model from navamsa placements when JH does not label it explicitly.

## Notes

- Each topic uses a **two-phase** call: parse (temperature **0**) then predict (temperature **0.05**), for both Gemini and Claude.
- Multi-topic runs issue **parallel** LLM calls by default (wall time ≈ slowest topic, not sum of all). Use `--workers 1` if you hit rate limits.
- Gemini-only and Claude-only setups are both supported; you do not need both API keys.
- This is interpretive decision support grounded in the supplied chart export, not a substitute for a human Jyotishi.
- Transit detail is strongest when your export includes a recent secondary chart and current dasa tables; the agent also asks the model for a forward 12-month gochara/dasa synthesis from `--as-of`.
