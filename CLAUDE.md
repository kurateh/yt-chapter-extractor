# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Python TUI application with two modes:
1. **YouTube Chapter Extraction** - Extract individual chapters from a YouTube video as separate MP3 files with ID3 metadata.
2. **Audio Loudness Normalization** - Normalize loudness (LUFS) of MP3 files in a directory using ffmpeg's `loudnorm` filter (EBU R128).

Built with Textual (TUI), yt-dlp (YouTube), mutagen (MP3 tags), and ffmpeg (audio processing).

## Commands

```bash
uv sync                                    # Install dependencies
uv run python -m yt_chapter_extractor      # Run the app
uv run yt-chapter-extractor                # Run via script entry point
```

**System requirement**: `ffmpeg` must be installed and available in PATH.

## Architecture

The app uses a mode-branching screen flow orchestrated by `app.py:_run_flow()` via Textual's `push_screen_wait`:

```
ModeSelectScreen -> (branch)
  "youtube"   -> UrlInputScreen -> (branch on chapters)
      has chapters -> ChapterSelectScreen -> MetadataEditScreen -> DownloadScreen
      no chapters  -> MetadataEditScreen -> DownloadScreen (single track)
  "normalize" -> DirInputScreen -> NormFileListScreen -> NormProgressScreen
```

Back navigation: each screen dismisses with `None` to go back. After completing either flow, the user returns to mode selection. Videos without chapters are treated as a single track spanning the full duration.

### Layer separation

- **models.py** - Immutable frozen dataclasses (`Chapter`, `TrackInfo`, `VideoInfo`, `Mp3FileInfo`). All use `frozen=True` with copy-on-write methods (`with_filename`, `with_metadata`, `with_loudness`).
- **youtube.py** - yt-dlp wrapper. `extract_video_info()` fetches video metadata and chapters (returns empty tuple if none); `download_audio()` downloads full audio in native format with progress callback.
- **audio.py** - ffmpeg operations: chapter extraction, MP3 conversion, ID3 tags (mutagen), loudness measurement (`measure_loudness`), and normalization (`normalize_audio`). Normalization writes to a temp file then does atomic `os.replace()`.
- **screens/** - Textual Screen subclasses, each dismissing with a typed result that the next screen consumes.
- **theme.py** - Catppuccin Macchiato theme definition.

### Textual patterns used

- Thread workers (`@work(thread=True)`) for blocking I/O (yt-dlp, ffmpeg)
- `self.app.call_from_thread()` to update UI from worker threads (NOT `self.call_from_thread` -- Screen doesn't have this method)
- `push_screen_wait()` in an async `@work` coroutine for sequential screen flow with return values
- `DataTable.add_columns()` returns `ColumnKey` tuple -- store and reuse for `update_cell()` (do NOT index `table.columns` with integers, it's a dict)
- `ThreadPoolExecutor` with `as_completed` for parallel ffmpeg operations in loudness measurement and normalization
