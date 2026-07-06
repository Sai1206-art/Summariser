#!/usr/bin/env python3
"""AutoTube CLI — faceless YouTube channel automation.

Common flows:
  python run.py topics                      # preview next topic ideas
  python run.py produce                     # make a long-form video package
  python run.py produce --format short      # make a Short
  python run.py upload --latest             # upload newest package (after review)
  python run.py upload --latest --schedule-next
  python run.py daily                       # produce (+ upload if auto_upload: true)
  python run.py auth                        # one-time YouTube OAuth
"""

from __future__ import annotations

import argparse
from pathlib import Path

from autotube import ideas, pipeline, state
from autotube.config import OUTPUT_DIR, load_config


def main() -> None:
    p = argparse.ArgumentParser(description="Faceless YouTube channel automation")
    p.add_argument("--niche", help="override the niche in channel.yaml")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("topics", help="preview upcoming topic ideas")

    sp = sub.add_parser("produce", help="produce a full video package")
    sp.add_argument("--topic", help="use this exact topic instead of ideation")
    sp.add_argument("--format", choices=["long", "short"], default="long")
    sp.add_argument("--tts", choices=["edge", "elevenlabs", "silent"],
                    help="override TTS provider (silent = offline test)")
    sp.add_argument("--keep-work", action="store_true",
                    help="keep intermediate files (work/) for debugging")

    sp = sub.add_parser("upload", help="upload a reviewed package to YouTube")
    g = sp.add_mutually_exclusive_group(required=True)
    g.add_argument("--latest", action="store_true", help="newest package in output/")
    g.add_argument("--folder", help="package folder name inside output/")
    sp.add_argument("--privacy", choices=["private", "unlisted", "public"])
    sp.add_argument("--schedule-next", action="store_true",
                    help="schedule at the next slot from channel.yaml")
    sp.add_argument("--force", action="store_true",
                    help="allow uploading demo-mode packages (not recommended)")

    sp = sub.add_parser("daily", help="produce; upload too when auto_upload: true")
    sp.add_argument("--format", choices=["long", "short"], default="long")

    sub.add_parser("auth", help="run the one-time YouTube OAuth flow")
    sub.add_parser("status", help="show channel automation status")

    args = p.parse_args()
    cfg = load_config(args.niche)

    if args.cmd == "topics":
        idea = ideas.next_topic(cfg)
        print(f"Next topic: {idea['topic']}")
        if idea.get("angle"):
            print(f"Angle:      {idea['angle']}")

    elif args.cmd == "produce":
        pipeline.produce(cfg, topic_override=args.topic, fmt=args.format,
                         tts_provider=args.tts, keep_work=args.keep_work)

    elif args.cmd == "upload":
        folder = pipeline.latest_production() if args.latest else OUTPUT_DIR / args.folder
        if not folder.exists():
            raise SystemExit(f"Folder not found: {folder}")
        pipeline.upload(cfg, folder, privacy=args.privacy,
                        schedule_next=args.schedule_next, force=args.force)

    elif args.cmd == "daily":
        folder = pipeline.produce(cfg, fmt=args.format)
        if cfg.upload.get("auto_upload"):
            pipeline.upload(cfg, folder, schedule_next=True)
        else:
            print("\nauto_upload is off — review the package, then upload manually.")

    elif args.cmd == "auth":
        from autotube import uploader
        uploader.authenticate(force=True)
        print("YouTube authorization stored.")

    elif args.cmd == "status":
        produced = state._load()["produced"]  # noqa: SLF001 (simple status readout)
        uploads = state._load()["uploads"]
        print(f"Niche:            {cfg.niche_key} ({cfg.niche['label']})")
        print(f"Videos produced:  {len(produced)}")
        print(f"Videos uploaded:  {len(uploads)}")
        print(f"Topics used:      {len(state.topics_used())}")
        if uploads:
            last = uploads[-1]
            print(f"Last upload:      {last['title']} ({last['video_id']})")


if __name__ == "__main__":
    main()
