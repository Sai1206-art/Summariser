# Monetization Playbook — getting a faceless channel to YPP fast

The goal: **1,000 subscribers + 4,000 public watch hours** (rolling 12
months), then pass YouTube's human review. This is the strategy the pipeline
defaults are built around.

---

## 1. Why psychology is the default niche

| Niche | RPM (US) | Retention | Competition | Time-to-4k-hours |
|---|---|---|---|---|
| **Psychology/behavior** | $4–9 | very high | medium | **fastest** |
| Personal finance | $12–30 | medium | high | medium |
| AI & tech | $8–15 | medium | high (fresh topics) | medium |
| History/mysteries | $5–10 | very high | medium | fast but slow growth |
| Space/science | $6–12 | high | medium | fast |

Watch hours are the bottleneck, not RPM — you earn $0 until you're in the
program. Psychology maximizes *finish rate* on 8-minute videos from a broad
audience, which is what compounds: retention → impressions → watch hours.
**Switch or add finance content after monetization** if you want to push RPM
(`--niche finance` works per-video).

The math: 4,000 hours = 240,000 watch-minutes. An 8-minute video watched at
45% average retention yields ~3.6 min/view → you need roughly **65–70k views
total across the catalog**. A 60-video catalog needs ~1.1k views/video —
very achievable in 4–6 months in these niches.

## 2. Cadence

- **Long-form is what monetizes.** Shorts views (10M/90d path) are a lottery;
  long-form watch hours are arithmetic. Ship **3–4 long-form videos/week**.
- **Shorts are your subscriber engine, not your watch-hour engine.** Post 3–5
  Shorts/week cut from your niche (`produce --format short`) with a pinned
  comment linking the long-form video. Note: Shorts views do *not* count
  toward the 4,000 hours.
- Consistency beats bursts — the algorithm needs a steady signal of what your
  channel is about. Stay in ONE niche for the first 90 days.

## 3. Packaging beats production

Click-through rate (CTR) and first-30-seconds retention decide everything:

- **Titles**: curiosity gap + concrete noun. "Why Your Brain Hides Your Real
  Memories" beats "Interesting Facts About Memory". The pipeline's SEO pass
  does this; still review every title.
- **Thumbnails**: ≤4 words, huge type, one visual idea. Generated thumbnails
  are a solid baseline — A/B test replacements in Studio ("Test & compare").
- **Hooks**: never open with "welcome back". The script generator forces an
  information-gap hook in the first 10 seconds; if a video's 30-second
  retention is <70% in analytics, the hook was the problem.

## 4. The 90-day plan

**Weeks 1–2 (setup):** channel art, 3-line channel description with keywords,
verify the channel (unlocks custom thumbnails), produce 5 videos before
publishing any, then release 1/day — an initial catalog makes the channel look
alive and lets the algorithm find your audience.

**Weeks 3–8 (calibrate):** 3–4 long-form + 3 Shorts weekly. After 20 videos,
study Studio analytics: double down on the 20% of topics with the best
CTR × retention. Kill topic families that underperform. Reply to every
comment (comments are a ranking signal and drives sub-conversion).

**Weeks 9–13 (compound):** keep cadence; make sequels of your top performers
("part 2", same-family topics); add end screens pointing to your best
retainer; build 2–3 playlists so session time accrues to your channel.

**At review time:** YouTube human-reviews channels for "reused/inauthentic
content". Your channel passes because every video has an original script,
unique voiceover pacing, edited captions/music/footage — keep the review gate
habit even after approval.

## 5. Revenue stack (don't stop at AdSense)

Once monetized, ads are typically the *smallest* stream on a faceless channel:

1. **AdSense** — enable mid-rolls on 8-min+ videos (automatic chapters help).
2. **Affiliates** — psychology → books/apps (Amazon, Audible); finance →
   brokers/tools; ai_tech → software. 2–3 relevant links per description.
3. **Sponsorships** — realistic from ~10–20k subs in these niches; niche
   marketplaces (e.g. Passionfroot-style) list faceless-friendly deals.
4. **Digital product** — a $9–19 PDF/notion pack matching the niche converts
   surprisingly well from description links.

## 6. Compliance guardrails (what gets channels rejected)

- **Never publish demo-mode output** (template script/silent voice). The
  uploader blocks it for a reason.
- **Don't reupload others' content** — stock footage is fine because the
  narration/edit is the value; compilations of other creators are not.
- **Disclose synthetic media** — realistic AI visuals/voices must be flagged
  (the pipeline sets the flag and notes AI narration in descriptions).
- **Stay advertiser-friendly** — no medical/financial *advice*, no
  fear-mongering, no tragedy exploitation. The script prompts enforce this;
  your review confirms it.
- **YouTube API quota**: an upload costs ~1,600 of 10,000 daily units — the
  default quota supports ~6 uploads/day, plenty for this plan.

## 7. Weekly operating rhythm (≈3–4 h/week once set up)

| Day | Task |
|---|---|
| Mon | `python run.py produce` ×2 (batch), review both |
| Tue | `upload --schedule-next` ×2; produce 2 Shorts |
| Thu | produce + review + schedule 1–2 more long-form |
| Sun | 30 min in YouTube Studio analytics; adjust topic direction; reply to comments |
