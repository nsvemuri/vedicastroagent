# Vedic Astrology Agent

CLI agent that reads a **Jagannatha Hora** natal chart export (plain text or RTF, including `.txt` files that are actually RTF) and runs focused **Gemini 3.1 Pro** (`gemini-3.1-pro-preview` by default) analyses for:

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
source .venv/bin/activate
pip install -e .

cp .env.example .env
# put your key from https://aistudio.google.com/apikey into .env
```

Environment variables:

| Variable | Purpose |
|---|---|
| `GEMINI_API_KEY` | Required (or `GOOGLE_API_KEY`) |
| `GEMINI_MODEL` | Optional model id; **default `gemini-3.1-pro-preview`** (Gemini 3.1 Pro) |

Generation defaults (in code, not env):

| Setting | Default | Why |
|---|---|---|
| Temperature | **0** | Factual chart/dasa parsing; no creative sampling |

For contributor / coding-agent guidance you can edit, see [`PROJECT_INSTRUCTIONS.md`](PROJECT_INSTRUCTIONS.md).

## Usage

```bash
# Parse only (no API calls)
vedicastroagent ~/Desktop/Srinu.txt --dry-run

# Full multi-topic reading
vedicastroagent ~/Desktop/Srinu.txt --name Srinu

# Selected topics
vedicastroagent ~/Desktop/Srinu.txt -t career wealth marriage transits

# Custom output path + transit reference date
vedicastroagent ~/Desktop/Srinu.txt -o output/srinu.md --as-of 2026-08-08
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

- Gemini calls use **temperature 0** so responses stay factual and parsing-focused.
- This is interpretive decision support grounded in the supplied chart export, not a substitute for a human Jyotishi.
- Transit detail is strongest when your export includes a recent secondary chart and current dasa tables; the agent also asks Gemini for a forward 12-month gochara/dasa synthesis from `--as-of`.
