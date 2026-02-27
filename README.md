# videoconvert

CLI tool for macOS to batch-convert MP4 videos into smaller versions while
preserving aspect ratio.

## Requirements

- macOS
- Python 3
- ffmpeg

Install ffmpeg:

```bash
brew install ffmpeg
```

## Usage

From this project folder:

```bash
python3 videoconvert.py /path/to/input --smaller 50
```

Common examples:

```bash
# 50% smaller dimensions (half width + half height)
python3 videoconvert.py ./videos --smaller 50

# 75% smaller dimensions (25% of original width/height)
python3 videoconvert.py ./videos --smaller 75

# Convert recursively and write to custom folder
python3 videoconvert.py ./videos --recursive -o ./output --smaller 50

# Convert videos and also export 3 thumbnails per video
python3 videoconvert.py ./videos --smaller 50 --thumbnails

# Export thumbnails only (no converted videos)
python3 videoconvert.py ./videos --thumbnails-only

# Use the original 25/50/75 behavior
python3 videoconvert.py ./videos --thumbnails --thumbnail-count 3
```

Options:

- `--smaller`: Percent reduction in width and height (`1-99`). Default `50`.
- `--recursive`: Include `.mp4` files in subfolders.
- `-o, --output-dir`: Output folder (default: `<input>/converted`).
- `--suffix`: Optional filename suffix for outputs (default: empty, so original name is kept).
- `--overwrite`: Replace existing outputs.
- `--dry-run`: Print ffmpeg commands without running them.
- `--thumbnails`: Also create thumbnail JPGs (default: `10` per video, evenly spaced).
- `--thumbnails-only`: Create thumbnails only and skip MP4 conversion.
- `--thumbnail-count`: Number of thumbnail samples per video (default: `10`).

## Notes

- Aspect ratio is preserved by scaling width/height with the same factor.
- By default, converted files keep the same filename in the `converted` subfolder.
- Thumbnails are written to `<output>/thumbnails/...` (folder structure preserved).
- Thumbnails are named in order: `_thumb_01.jpg`, `_thumb_02.jpg`, etc.
- Output files are encoded with H.264 (`libx264`) and AAC audio.
