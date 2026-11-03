# Instructions

Use [Jagannatha Hora](https://www.vedicastrologer.org/jh/) to export a full chart, then run this agent on that file for predictions.

You need **Python 3.10+** and **one** API key: an [Anthropic](https://console.anthropic.com/) key (recommended) or a [Gemini](https://aistudio.google.com/apikey) key.

## 1. Export the chart from Jagannatha Hora

1. Install Jagannatha Hora from [https://www.vedicastrologer.org/jh/](https://www.vedicastrologer.org/jh/).
2. Open the profile you want to read.
3. From the **Edit** menu, choose **Copy complete calculations** so the full calculation set is on the clipboard.
4. For that same profile, export **all calculations** to an **RTF** or **plain text** file (`.rtf` or `.txt`).

A `.txt` file that is actually RTF is fine. The agent reads the natal header, planetary longitudes, divisional charts, karakas, ashtakavarga, shadbala, and dasas from that export.

Example path used below: `~/Desktop/jyotish/Srinu.txt`

## 2. Install the prediction agent

```bash
python -m venv .venv
```

Activate the environment:

- Windows: `.venv\Scripts\activate`
- Mac or Linux: `source .venv/bin/activate`

Then install:

```bash
pip install --upgrade pip
pip install "git+https://github.com/nsvemuri/vedicastroagent.git"
```

## 3. Set an API key

Put a `.env` file in the folder where you will run the command. The agent loads it from the current directory.

### Claude (recommended)

```env
ANTHROPIC_API_KEY=...
LLM_PROVIDER=claude
CLAUDE_MODEL=opus
```

`CLAUDE_MODEL` may be `opus`, `mythos`, or `sonnet`.

### Gemini

```env
GEMINI_API_KEY=...
LLM_PROVIDER=gemini
GEMINI_MODEL=pro
```

`GEMINI_MODEL` may be `pro` or `flash`. You only need the key for the provider you use.

## 4. Run predictions

```bash
vedicastroagent ~/Desktop/jyotish/Srinu.txt --provider claude --model opus
```

The Markdown report is written under `output/`.

Useful variants:

```bash
# Confirm the export parsed before spending API calls
vedicastroagent ~/Desktop/jyotish/Srinu.txt --dry-run

# Gemini
vedicastroagent ~/Desktop/jyotish/Srinu.txt --provider gemini --model pro

# Selected topics only
vedicastroagent ~/Desktop/jyotish/Srinu.txt --provider claude --model opus -t career wealth marriage

# Custom output path and transit date
vedicastroagent ~/Desktop/jyotish/Srinu.txt -o output/srinu.md --as-of 2026-08-08
```

Default topics are career, wealth, marriage, children, education, spiritual progress, and a 1-year transit outlook. Longevity is opt-in:

```bash
vedicastroagent ~/Desktop/jyotish/Srinu.txt -t longevity --provider claude --model opus
```

This is interpretive support grounded in the Jagannatha Hora export you supply. It is not a substitute for a human Jyotishi.
