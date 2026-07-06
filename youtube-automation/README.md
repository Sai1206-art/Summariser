# AutoTube — Faceless YouTube Channel Automation

An end-to-end pipeline that turns a niche + topic into a finished, uploadable
YouTube video:

```
topic ideation ─> script (Claude) ─> voiceover (edge-tts, free)
      ─> stock footage (Pexels/Pixabay, free) ─> ffmpeg assembly
      ─> burned captions + SRT ─> thumbnail (Pillow) ─> SEO metadata
      ─> human review gate ─> YouTube upload + publish scheduling
```

Everything runs locally with **free services** (edge-tts voices, Pexels/Pixabay
footage, bundled ffmpeg). The only paid piece is the Claude API for original
scripts — the single most important ingredient for getting monetized (see
[Compliance](#monetization--compliance-read-this)).

**Default niche: Psychology & Human Behavior** — high retention, evergreen,
cheap to produce, broad audience. Four more presets ship in
`config/niches.yaml` (finance = highest RPM, ai_tech, history, space). Full
strategy: [docs/MONETIZATION_PLAYBOOK.md](docs/MONETIZATION_PLAYBOOK.md).

---

## Quick start

```bash
cd youtube-automation
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env        # then fill in keys (see below)
```

Get your (free) keys:

| Key | Where | Needed for |
|---|---|---|
| `ANTHROPIC_API_KEY` | console.anthropic.com | original scripts/ideas/SEO (strongly recommended) |
| `PEXELS_API_KEY` | pexels.com/api | stock footage (free) |
| `PIXABAY_API_KEY` | pixabay.com/api/docs | fallback footage (free) |
| YouTube OAuth JSON | Google Cloud Console | uploading (see `autotube/uploader.py` docstring) |

Then:

```bash
# 1. Pick your channel identity + niche
$EDITOR config/channel.yaml

# 2. Smoke-test the pipeline with zero keys (demo script + gradient visuals)
python run.py produce --tts silent

# 3. Produce a real video
python run.py produce                      # long-form (~8 min)
python run.py produce --format short       # vertical Short

# 4. Watch output/<stamp>-<slug>/video.mp4, tick REVIEW.md, then:
python run.py auth                         # one-time YouTube OAuth
python run.py upload --latest --schedule-next
```

### Daily automation

```bash
python run.py daily        # produce; uploads too if auto_upload: true in channel.yaml
```

Cron example (produce every day at 09:00, you review + upload from your phone
later): `0 9 * * * cd /path/to/youtube-automation && .venv/bin/python run.py daily`

A GitHub Actions workflow is included at `.github/workflows/youtube-daily.yml`
(manual dispatch by default; uncomment the cron to schedule).

---

## Commands

| Command | What it does |
|---|---|
| `python run.py topics` | preview the next topic idea |
| `python run.py produce [--topic "..."] [--format long\|short] [--tts edge\|elevenlabs\|silent]` | build a full video package into `output/` |
| `python run.py upload --latest [--schedule-next] [--privacy public]` | upload a reviewed package |
| `python run.py daily [--format short]` | produce (+ auto-upload if enabled) |
| `python run.py auth` | one-time YouTube OAuth |
| `python run.py status` | production/upload counters |
| `--niche finance` (any command) | override the configured niche |

Each production folder contains: `video.mp4`, `thumbnail.jpg`, `captions.srt`,
`script.json`, `metadata.json`, and a `REVIEW.md` checklist.

---

## Monetization & compliance (READ THIS)

To join the YouTube Partner Program you need **1,000 subscribers + 4,000
public watch hours** (long-form, past 12 months) *or* **10M Shorts views (90
days)** — plus a channel that passes human review.

Since July 2025 YouTube's **"inauthentic content"** policy explicitly targets
mass-produced, repetitious, low-transformation uploads — exactly what naive
"AI slop" automation produces. This system is designed to keep you on the
right side of that line:

1. **Original scripts** — every script is written fresh by Claude with a
   unique angle, and used topics are tracked so nothing repeats. The
   zero-key demo template mode is watermarked `demo: true` and the uploader
   **refuses to publish it** without `--force`.
2. **Human review gate** — `REVIEW.md` checklist per video; `daily` stops
   before upload unless you explicitly enable `auto_upload`.
3. **AI disclosure** — descriptions note the AI voiceover and uploads set the
   synthetic-media flag where the API supports it.
4. **Transformation** — voiceover + timed captions + curated footage + music +
   chapters is transformative editing, not raw slideshow spam.

Full growth strategy (niche math, cadence, packaging, the 90-day plan):
**[docs/MONETIZATION_PLAYBOOK.md](docs/MONETIZATION_PLAYBOOK.md)**.

---

## Architecture

```
youtube-automation/
├── run.py                  # CLI
├── config/
│   ├── channel.yaml        # your channel: niche, voice, upload defaults
│   └── niches.yaml         # 5 niche presets (topics, tone, SEO, styling)
├── autotube/
│   ├── ideas.py            # topic ideation (Claude, seed-bank fallback)
│   ├── scriptgen.py        # retention-structured script writing
│   ├── tts.py              # edge-tts (word timings) / ElevenLabs / silent
│   ├── visuals.py          # Pexels -> Pixabay -> generated gradient clips
│   ├── captions.py         # SRT sidecar + styled ASS for burning
│   ├── assemble.py         # ffmpeg: normalize, concat, music duck, captions
│   ├── thumbnail.py        # Pillow thumbnail from a video frame
│   ├── metadata.py         # SEO title/description/chapters/tags
│   ├── uploader.py         # YouTube Data API v3 upload + scheduling
│   ├── pipeline.py         # orchestration + review gate
│   ├── llm.py              # Claude API wrapper (claude-opus-4-8)
│   ├── state.py            # topic/production/upload history
│   └── ff.py               # bundled-ffmpeg helpers
├── assets/music/           # drop royalty-free .mp3s here (auto-mixed)
├── output/                 # finished video packages
└── state/                  # history.json, youtube_token.json
```

Background music: add tracks from the **YouTube Audio Library** (free, safe)
into `assets/music/` — one is picked per video and mixed at `music_volume_db`.
