"""Pipeline orchestration: produce a full video package, then upload after review."""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from . import (
    assemble,
    avatar,
    captions,
    ideas,
    metadata,
    news,
    scriptgen,
    state,
    thumbnail,
    tts,
    uploader,
)
from .config import OUTPUT_DIR, Config


def _segments_from_script(script: dict[str, Any]) -> list[dict[str, str]]:
    """Flatten hook + scenes + cta into narration segments with visual queries."""
    scenes = script["scenes"]
    segs = [{"narration": script["hook"], "visual_query": scenes[0]["visual_query"]}]
    segs += scenes
    if script.get("cta"):
        segs.append({"narration": script["cta"], "visual_query": scenes[-1]["visual_query"]})
    return segs


def produce(
    cfg: Config,
    topic_override: str | None = None,
    fmt: str = "long",
    tts_provider: str | None = None,
    keep_work: bool = False,
) -> Path:
    portrait = fmt == "short"

    print(f"[1/7] Picking topic ({cfg.niche['label']})...")
    idea = ideas.next_topic(cfg, topic_override)
    topic = idea["topic"]
    print(f"      -> {topic}")

    print("[2/7] Writing script...")
    script = scriptgen.write_script(cfg, topic, idea.get("angle", ""), fmt=fmt)
    segments_spec = _segments_from_script(script)

    slug = state.slugify(script.get("title", topic))
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    outdir = OUTPUT_DIR / f"{stamp}-{fmt}-{slug}"
    workdir = outdir / "work"
    outdir.mkdir(parents=True, exist_ok=True)
    with open(outdir / "script.json", "w", encoding="utf-8") as f:
        json.dump(script, f, indent=2, ensure_ascii=False)

    print(f"[3/7] Voiceover ({tts_provider or cfg.voice.get('provider', 'edge')})...")
    audio_segs = tts.synthesize(
        [s["narration"] for s in segments_spec], cfg, workdir / "tts", tts_provider
    )
    durations = [s["duration"] for s in audio_segs]
    total = sum(durations)
    print(f"      -> {total / 60:.1f} min narration, {len(audio_segs)} segments")

    print("[4/7] Fetching visuals...")
    from . import visuals

    visuals_clips = visuals.fetch_scene_clips(
        segments_spec, durations, cfg, workdir / "clips", portrait=portrait
    )

    print("[5/7] Captions...")
    srt = captions.write_srt(audio_segs, outdir / "captions.srt")
    res = tuple((cfg.shorts if portrait else cfg.video)["resolution"])
    ass = captions.write_ass(audio_segs, workdir / "captions.ass", res, shorts=portrait)

    print("[6/7] Assembling video...")
    video = assemble.assemble(
        audio_segs, visuals_clips, cfg, workdir, outdir / "video.mp4",
        ass_path=ass, portrait=portrait,
    )

    print("[7/7] Thumbnail + metadata...")
    # grab from the pre-caption concat so caption text can't bleed into the thumbnail
    clean_video = workdir / "video_concat.mp4"
    frame = assemble.grab_frame(
        clean_video if clean_video.exists() else video,
        min(3.0, total / 2), workdir / "frame.jpg",
    )
    thumbnail.make_thumbnail(
        script.get("thumbnail_text", topic), outdir / "thumbnail.jpg",
        cfg.niche.get("thumbnail", {}), frame=frame,
    )
    meta = metadata.build_metadata(cfg, topic, script, durations, fmt=fmt)
    meta["format"] = fmt
    meta["topic"] = topic
    meta["demo"] = bool(script.get("demo")) or (tts_provider == "silent")
    with open(outdir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    _write_review(outdir, meta, script, total)
    state.mark_topic_used(topic)
    state.record_produced(
        {"topic": topic, "folder": str(outdir), "format": fmt,
         "minutes": round(total / 60, 2), "demo": meta["demo"]}
    )

    if not keep_work:
        shutil.rmtree(workdir, ignore_errors=True)

    print(f"\nDone: {outdir}")
    print("Review video.mp4 + REVIEW.md, then:  python run.py upload --latest")
    return outdir


def produce_news(
    cfg: Config,
    tts_provider: str | None = None,
    keep_work: bool = False,
) -> Path:
    """Daily AI-news video: live news -> avatar/voice segments -> assembled show."""
    from . import visuals

    res = tuple(cfg.video["resolution"])
    fps = cfg.video.get("fps", 30)
    theme = cfg.niche.get("thumbnail", {})
    use_avatar = avatar.available()

    print("[1/6] Researching today's AI news + writing the show...")
    script = news.fetch_news_script(cfg)
    segs = script["segments"]
    print(f"      -> {len(script.get('stories', []))} stories, {len(segs)} segments")
    if use_avatar:
        print("      -> HeyGen avatar presenter enabled")
    else:
        print("      ! No HEYGEN_API_KEY — voice + visuals mode (add key for the avatar)")

    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    outdir = OUTPUT_DIR / f"{stamp}-news-{state.slugify(script.get('title', 'ai-news'))}"
    workdir = outdir / "work"
    workdir.mkdir(parents=True, exist_ok=True)
    with open(outdir / "script.json", "w", encoding="utf-8") as f:
        json.dump(script, f, indent=2, ensure_ascii=False)

    print("[2/6] Building segments...")
    seg_files: list[Path] = []
    total = 0.0
    for i, seg in enumerate(segs):
        narration = seg.get("narration", "").strip()
        if not narration:
            continue
        kind = seg.get("kind", "broll")
        out_i = workdir / f"seg_{i:03d}.mp4"

        if kind == "avatar" and use_avatar:
            raw = avatar.render_segment(narration, cfg, res, workdir / f"raw_{i:03d}.mp4")
            assemble.normalize_av(raw, res, fps, out_i)
            print(f"  seg {i + 1}/{len(segs)}: avatar")
        else:
            audio = tts.synthesize([narration], cfg, workdir / f"tts_{i:03d}", tts_provider)[0]
            dur = audio["duration"]
            infog = (seg.get("infographic") or "").strip()
            if infog and (kind == "broll" or not use_avatar):
                card = thumbnail.make_card(
                    infog, workdir / f"card_{i:03d}.jpg", theme,
                    subtext=seg.get("visual_query", ""), resolution=res,
                )
                assemble.build_voiced_clip(card, True, audio["audio"], dur, res, fps, out_i)
                print(f"  seg {i + 1}/{len(segs)}: infographic ({infog[:24]})")
            else:
                clip = visuals.fetch_scene_clips(
                    [{"visual_query": seg.get("visual_query", "technology")}],
                    [dur], cfg, workdir / f"clip_{i:03d}",
                )[0]
                assemble.build_voiced_clip(clip, False, audio["audio"], dur, res, fps, out_i)
                print(f"  seg {i + 1}/{len(segs)}: b-roll ({seg.get('visual_query', '')})")
        seg_files.append(out_i)

    if len(seg_files) < 2:
        raise RuntimeError("News video needs at least 2 usable segments")

    print("[3/6] Assembling show...")
    video = assemble.concat_av(seg_files, outdir / "video.mp4", workdir)
    total = ff_duration(video)

    print("[4/6] Thumbnail...")
    frame = assemble.grab_frame(video, min(2.0, total / 3), workdir / "frame.jpg")
    thumbnail.make_thumbnail(
        script.get("thumbnail_text", "AI NEWS"), outdir / "thumbnail.jpg", theme, frame=frame
    )

    print("[5/6] Metadata...")
    meta = _news_metadata(cfg, script)
    meta.update({"format": "news", "demo": bool(script.get("demo")) or tts_provider == "silent"})
    with open(outdir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    print("[6/6] Finishing...")
    _write_review(outdir, meta, script, total)
    state.record_produced(
        {"topic": "AI news " + stamp, "folder": str(outdir), "format": "news",
         "minutes": round(total / 60, 2), "demo": meta["demo"], "avatar": use_avatar}
    )
    if not keep_work:
        shutil.rmtree(workdir, ignore_errors=True)

    print(f"\nDone: {outdir}  ({total / 60:.1f} min)")
    print("Review video.mp4 + REVIEW.md, then:  python run.py upload --latest")
    return outdir


def ff_duration(path: Path) -> float:
    from . import ff

    return ff.duration(path)


def _news_metadata(cfg: Config, script: dict) -> dict:
    ch = cfg.channel["channel"]
    stories = script.get("stories", [])
    lines = [script.get("title", "Today in AI"), ""]
    if stories:
        lines.append("In today's AI briefing:")
        lines += [f"- {s.get('headline', '')}" for s in stories if s.get("headline")]
        lines.append("")
    sources = [s for s in script.get("sources", []) if s]
    if sources:
        lines.append("Sources:")
        lines += sources[:8]
        lines.append("")
    lines.append(f"Subscribe to {ch['name']} ({ch.get('handle', '')}) for a daily AI briefing.")
    if cfg.compliance.get("ai_disclosure", True):
        lines.append("")
        lines.append("Presented with an AI avatar and AI narration.")
    hashtags = " ".join(cfg.niche.get("hashtags", ["#ai", "#ainews", "#technology"]))
    lines += ["", hashtags]

    tags = ["ai news", "artificial intelligence", "ai", "tech news", "ai daily"]
    for s in stories:
        for w in s.get("headline", "").lower().split():
            if len(w) > 4 and w not in tags and len(tags) < 25:
                tags.append(w)

    return {
        "title": (script.get("title", "Today in AI"))[:100],
        "description": "\n".join(lines)[:4900],
        "tags": tags,
        "category_id": "28",  # Science & Technology
        "topic": "AI news",
    }


def _write_review(outdir: Path, meta: dict, script: dict, total: float) -> None:
    warn = ""
    if meta.get("demo"):
        warn = (
            "\n> **DO NOT PUBLISH** — this package was produced in demo mode\n"
            "> (template script and/or silent audio). Add API keys and re-produce.\n"
        )
    (outdir / "REVIEW.md").write_text(
        f"""# Review checklist — {meta['title']}
{warn}
- Length: {total / 60:.1f} min · Format: {meta.get('format')}
- [ ] Watch the full video — narration accurate, no weird TTS artifacts
- [ ] Facts check out (spot-check claims in script.json)
- [ ] Captions synced (captions.srt)
- [ ] Thumbnail readable at small size (thumbnail.jpg)
- [ ] Title/description/tags look right (metadata.json)
- [ ] Nothing violates YouTube ad-friendly guidelines

Publish:  python run.py upload --folder "{outdir.name}"
Schedule: python run.py upload --folder "{outdir.name}" --schedule-next
""",
        encoding="utf-8",
    )


def latest_production() -> Path:
    dirs = sorted(
        (d for d in OUTPUT_DIR.iterdir() if d.is_dir() and (d / "metadata.json").exists()),
        key=lambda d: d.name,
    )
    if not dirs:
        raise SystemExit("No produced videos found in output/. Run: python run.py produce")
    return dirs[-1]


def upload(
    cfg: Config,
    folder: Path,
    privacy: str | None = None,
    schedule_next: bool = False,
    force: bool = False,
) -> str:
    meta = uploader.load_production(folder)
    if meta.get("demo") and not force:
        raise SystemExit(
            f"{folder.name} was produced in DEMO mode (template script or silent "
            "audio). Publishing it risks demonetization. Re-produce with API keys, "
            "or pass --force if you really mean it."
        )
    publish_at = uploader.next_slot(cfg) if schedule_next else None
    video_id = uploader.upload_video(
        folder / "video.mp4", meta, cfg,
        thumbnail=folder / "thumbnail.jpg",
        srt=folder / "captions.srt",
        privacy=privacy, publish_at=publish_at,
    )
    state.record_upload(
        {"video_id": video_id, "title": meta["title"], "folder": str(folder),
         "publish_at": publish_at}
    )
    url = f"https://youtu.be/{video_id}"
    print(f"\nUploaded: {url}" + (f" (goes live {publish_at})" if publish_at else ""))
    return video_id
