#!/usr/bin/env python3
"""
Batch-convert MP4 videos into smaller versions while preserving aspect ratio.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Convert MP4 files in a folder to smaller versions on macOS "
            "using ffmpeg."
        )
    )
    parser.add_argument(
        "input_dir",
        type=Path,
        help="Folder that contains source .mp4 files.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        help=(
            "Where converted files go. Default: <input_dir>/converted."
        ),
    )
    parser.add_argument(
        "--smaller",
        type=int,
        default=50,
        help=(
            "How much to reduce width/height by percent. "
            "Examples: 50 = half size, 75 = quarter size. Default: 50."
        ),
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Include MP4 files in subfolders.",
    )
    parser.add_argument(
        "--suffix",
        default="",
        help="Suffix added to output filenames. Default: empty (keep name).",
    )
    parser.add_argument(
        "--crf",
        type=int,
        default=23,
        help="Video quality for x264 (lower is higher quality). Default: 23.",
    )
    parser.add_argument(
        "--preset",
        default="medium",
        choices=[
            "ultrafast",
            "superfast",
            "veryfast",
            "faster",
            "fast",
            "medium",
            "slow",
            "slower",
            "veryslow",
        ],
        help="x264 speed/efficiency preset. Default: medium.",
    )
    parser.add_argument(
        "--audio-bitrate",
        default="128k",
        help="Audio bitrate for AAC output. Default: 128k.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite output files if they already exist.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned conversions without running ffmpeg.",
    )
    parser.add_argument(
        "--thumbnails",
        action="store_true",
        help="Also extract thumbnail JPGs per video (default: 10 evenly spaced).",
    )
    parser.add_argument(
        "--thumbnails-only",
        action="store_true",
        help="Extract thumbnails only (skip converted MP4 outputs).",
    )
    parser.add_argument(
        "--thumbnail-count",
        type=int,
        default=10,
        help=(
            "Number of evenly spaced thumbnails per video. "
            "Default: 10. Use 3 for 25%%, 50%%, 75%%."
        ),
    )
    return parser.parse_args()


def is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False


def find_mp4_files(input_dir: Path, output_dir: Path, recursive: bool) -> list[Path]:
    glob_iter = input_dir.rglob("*") if recursive else input_dir.glob("*")
    files: list[Path] = []
    for candidate in glob_iter:
        if not candidate.is_file():
            continue
        if candidate.suffix.lower() != ".mp4":
            continue
        if is_relative_to(candidate.resolve(), output_dir.resolve()):
            continue
        files.append(candidate)
    return sorted(files)


def ffmpeg_command(
    source: Path,
    destination: Path,
    scale_factor: float,
    crf: int,
    preset: str,
    audio_bitrate: str,
    overwrite: bool,
) -> list[str]:
    scale_expr = (
        f"scale=trunc(iw*{scale_factor}/2)*2:"
        f"trunc(ih*{scale_factor}/2)*2"
    )
    return [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y" if overwrite else "-n",
        "-i",
        str(source),
        "-vf",
        scale_expr,
        "-c:v",
        "libx264",
        "-preset",
        preset,
        "-crf",
        str(crf),
        "-c:a",
        "aac",
        "-b:a",
        audio_bitrate,
        "-movflags",
        "+faststart",
        str(destination),
    ]


def ffprobe_duration_seconds(source: Path) -> float | None:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(source),
    ]
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def thumbnail_command(
    source: Path,
    destination: Path,
    timestamp_seconds: float,
    overwrite: bool,
) -> list[str]:
    return [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y" if overwrite else "-n",
        "-ss",
        f"{timestamp_seconds:.3f}",
        "-i",
        str(source),
        "-frames:v",
        "1",
        "-q:v",
        "2",
        str(destination),
    ]


def build_thumbnail_points(count: int) -> list[tuple[int, float]]:
    # Evenly space points across the timeline without using exact start/end frames.
    return [(index, index / (count + 1)) for index in range(1, count + 1)]


def main() -> int:
    args = parse_args()
    do_thumbnails = args.thumbnails or args.thumbnails_only
    do_video_conversion = not args.thumbnails_only

    if shutil.which("ffmpeg") is None:
        print("Error: ffmpeg is not installed or not in PATH.", file=sys.stderr)
        print("Install on macOS with: brew install ffmpeg", file=sys.stderr)
        return 2
    if do_thumbnails and shutil.which("ffprobe") is None:
        print("Error: ffprobe is not installed or not in PATH.", file=sys.stderr)
        print("Install on macOS with: brew install ffmpeg", file=sys.stderr)
        return 2
    if do_thumbnails and args.thumbnail_count < 1:
        print("Error: --thumbnail-count must be at least 1.", file=sys.stderr)
        return 2

    input_dir = args.input_dir.expanduser().resolve()
    if not input_dir.exists() or not input_dir.is_dir():
        print(f"Error: input directory does not exist: {input_dir}", file=sys.stderr)
        return 2

    output_dir = (
        args.output_dir.expanduser().resolve()
        if args.output_dir
        else (input_dir / "converted").resolve()
    )

    scale_factor = 0.0
    if do_video_conversion:
        if args.smaller <= 0 or args.smaller >= 100:
            print("Error: --smaller must be between 1 and 99.", file=sys.stderr)
            return 2
        scale_factor = (100 - args.smaller) / 100.0
        if scale_factor <= 0:
            print("Error: resulting scale factor must be > 0.", file=sys.stderr)
            return 2

    sources = find_mp4_files(input_dir, output_dir, args.recursive)
    if not sources:
        print("No MP4 files found.")
        return 0

    output_dir.mkdir(parents=True, exist_ok=True)
    thumbnails_dir = output_dir / "thumbnails"
    if do_thumbnails:
        thumbnails_dir.mkdir(parents=True, exist_ok=True)

    conversion_failures = 0
    thumbnail_failures = 0
    mode_parts = []
    if do_video_conversion:
        mode_parts.append(
            f"video conversion at scale factor {scale_factor:.2f} "
            f"({args.smaller}% smaller)"
        )
    if do_thumbnails:
        mode_parts.append(
            f"{args.thumbnail_count} evenly spaced thumbnails per video"
        )
    print(f"Found {len(sources)} MP4 file(s). Running: {', '.join(mode_parts)}.")

    for index, source in enumerate(sources, start=1):
        rel_parent = source.relative_to(input_dir).parent
        print(f"[{index}/{len(sources)}] {source.name}")

        if do_video_conversion:
            target_parent = output_dir / rel_parent
            target_parent.mkdir(parents=True, exist_ok=True)

            destination = target_parent / f"{source.stem}{args.suffix}{source.suffix}"
            cmd = ffmpeg_command(
                source=source,
                destination=destination,
                scale_factor=scale_factor,
                crf=args.crf,
                preset=args.preset,
                audio_bitrate=args.audio_bitrate,
                overwrite=args.overwrite,
            )

            print(f"  convert -> {destination}")
            if args.dry_run:
                print("  " + " ".join(cmd))
            else:
                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                if result.returncode != 0:
                    conversion_failures += 1
                    print(f"  convert failed ({result.returncode})", file=sys.stderr)
                    if result.stderr.strip():
                        print(f"  {result.stderr.strip()}", file=sys.stderr)

        if do_thumbnails:
            duration = ffprobe_duration_seconds(source)
            if duration is None or duration <= 0:
                thumbnail_failures += 1
                print("  thumbnail failed (could not read duration)", file=sys.stderr)
                continue

            thumb_parent = thumbnails_dir / rel_parent
            thumb_parent.mkdir(parents=True, exist_ok=True)
            thumbnail_points = build_thumbnail_points(args.thumbnail_count)

            for thumb_index, fraction in thumbnail_points:
                timestamp = duration * fraction
                thumb_pct = fraction * 100.0
                thumb_path = thumb_parent / f"{source.stem}_thumb_{thumb_index:02d}.jpg"
                thumb_cmd = thumbnail_command(
                    source=source,
                    destination=thumb_path,
                    timestamp_seconds=timestamp,
                    overwrite=args.overwrite,
                )
                print(
                    f"  thumb {thumb_index}/{args.thumbnail_count} "
                    f"({thumb_pct:.1f}%) -> {thumb_path}"
                )
                if args.dry_run:
                    print("  " + " ".join(thumb_cmd))
                    continue

                thumb_result = subprocess.run(
                    thumb_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                if thumb_result.returncode != 0:
                    thumbnail_failures += 1
                    print(
                        f"  thumbnail {thumb_index} failed "
                        f"({thumb_result.returncode})",
                        file=sys.stderr,
                    )
                    if thumb_result.stderr.strip():
                        print(f"  {thumb_result.stderr.strip()}", file=sys.stderr)

    total_failures = conversion_failures + thumbnail_failures
    print(
        "Completed. "
        f"Conversion failures: {conversion_failures}, "
        f"Thumbnail failures: {thumbnail_failures}"
    )
    return 1 if total_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
