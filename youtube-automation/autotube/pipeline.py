"""Pipeline orchestration: produce a full video package, then upload after review."""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from . import assemble, captions, ideas, metadata, scriptgen, state, thumbnail, tts, uploader
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
