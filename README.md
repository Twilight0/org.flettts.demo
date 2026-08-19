# Flet TTS Demo (`org.flettts.demo`)

A pure-Python, self-contained Flet application demonstrating real-time Neural Text-to-Speech using Microsoft Edge Neural Voices (`edge-tts`).

## Features

- **Pure Python & Self-Contained**: Zero external Flutter extension dependencies. Runs seamlessly with standard `flet run`.
- **Instant Real-Time Streaming**: Audio playback starts immediately via real-time WebSocket chunk streaming to the system audio pipeline.
- **300+ High-Quality Neural Voices**: Real-time browsing and filtering by language (English, Spanish, French, German, Japanese, Chinese, etc.), gender (Female/Male), and live search.
- **Rich Text Controls & Presets**: Preset quotes, multilingual samples, character & word counters, and quick clear.
- **Voice Tuning Parameters**: Real-time control of Speech Rate (`-50%` to `+100%`), Pitch (`-50Hz` to `+50Hz`), and Volume (`-50%` to `+50%`) with default reset.
- **Instant Cancellation & Export**: One-tap **Stop** to halt speech instantly, plus local MP3 export.
- **Responsive Material 3 UI**: Polished layout with dark/light theme switching.

---

## Project Structure

```text
org.flettts.demo/
├── pyproject.toml       # Dependencies (flet, edge-tts) and project metadata
├── src/
│   ├── __init__.py      # Package export
│   ├── tts_service.py   # Pure Python TtsService engine
│   └── main.py          # Modern Flet application UI
├── tests/
│   └── test_tts.py      # Automated test suite
└── README.md
```

---

## Running Locally

### 1. Run the app with UV
```bash
uv run flet run
```

### 2. Run the automated test suite
```bash
uv run pytest tests/
```
