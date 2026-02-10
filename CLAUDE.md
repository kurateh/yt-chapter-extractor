# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Python TUI application that extracts individual chapters from a YouTube video as separate MP3 files with ID3 metadata. Built with Textual (TUI), yt-dlp (YouTube), mutagen (MP3 tags), and ffmpeg (audio splitting).

## Commands

```bash
uv sync                                    # Install dependencies
uv run python -m yt_chapter_extractor      # Run the app
uv run yt-chapter-extractor                # Run via script entry point
```

**System requirement**: `ffmpeg` must be installed and available in PATH.

## Architecture

The app uses a linear screen flow orchestrated by `app.py:_run_flow()` via Textual's `push_screen_wait`:

```
UrlInputScreen -> ChapterSelectScreen -> MetadataEditScreen -> DownloadScreen
```

Back navigation: MetadataEdit goes back to ChapterSelect; ChapterSelect goes back to UrlInput.

### Layer separation

- **models.py** - Immutable frozen dataclasses (`Chapter`, `TrackInfo`, `VideoInfo`). All use `frozen=True` with copy-on-write methods (`with_filename`, `with_metadata`).
- **youtube.py** - yt-dlp wrapper. `extract_video_info()` fetches chapters; `download_audio()` downloads full audio in native format (no MP3 conversion) with progress callback.
- **audio.py** - ffmpeg extracts chapters from local file (`-ss` before `-i` for fast seeking) + converts to MP3 + mutagen for ID3 tags.
- **screens/** - Four Textual Screen subclasses, each dismissing with a typed result that the next screen consumes.

### Textual patterns used

- Thread workers (`@work(thread=True)`) for blocking I/O (yt-dlp, ffmpeg) in `url_input.py` and `download.py`
- `self.app.call_from_thread()` to update UI from worker threads (NOT `self.call_from_thread` -- Screen doesn't have this method)
- `push_screen_wait()` in an async `@work` coroutine for sequential screen flow with return values
