# Youtube Chapter Extractor

A terminal UI application for audio processing, built with [Textual](https://textual.textualize.io/).

## Features

### YouTube Chapter Extraction
Extract individual chapters from a YouTube video as separate MP3 files with ID3 metadata (title, artist, album). Videos without chapters are downloaded as a single track.

### Audio Loudness Normalization
Normalize the loudness of MP3 files in a directory to a target LUFS value using ffmpeg's EBU R128 `loudnorm` filter. Displays current loudness measurements with average and median statistics before processing.

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (package manager)
- [ffmpeg](https://ffmpeg.org/) installed and available in PATH

## Installation

```bash
uv sync
```

## Usage

```bash
uv run python -m yt_chapter_extractor
```

Or via the script entry point:

```bash
uv run yt-chapter-extractor
```

On launch, select a mode:

- **YouTube MP3 Extraction** - Enter a YouTube URL. If the video has chapters, select which ones to extract; otherwise, the full video is treated as a single track. Edit metadata, optionally enable loudness normalization (target LUFS), and download as MP3 files (saved to `./output/`).
- **Audio Decibel Normalization** - Enter a directory path, review loudness levels, set a target LUFS (default: -19.0), and normalize all MP3 files in-place.

## Tech Stack

- [Textual](https://textual.textualize.io/) - Terminal UI framework
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - YouTube video/audio downloading
- [mutagen](https://mutagen.readthedocs.io/) - ID3 metadata tagging
- [ffmpeg](https://ffmpeg.org/) - Audio extraction, conversion, and loudness normalization
