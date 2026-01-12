# AGENTS.md - AI Agent Instructions

This file provides setup, run, and test commands for AI agents (like Devin) working on this repository.

## Setup

```bash
# Install Python dependencies
pip install -r requirements.txt

# Copy environment template and add your YouTube API key
cp .env.example .env
# Edit .env and set YOUTUBE_API_KEY=your_api_key_here
```

## Run

### Keyword Search (PR1)
```bash
# Basic search
python -m src.cli search --keyword "python tutorial" --max-results 50

# With filters
python -m src.cli search --keyword "python tutorial" --published-after 2024-01-01 --region-code JP
```

### Benchmark Mode (PR2)
```bash
# Analyze specific videos by ID
python -m src.cli benchmark --video-ids "dQw4w9WgXcQ,VIDEO_ID2"

# From file
python -m src.cli benchmark --input-file videos.txt
```

### Script Abstraction (PR3)
```bash
python -m src.cli script --input transcript.txt --output script.json
```

## Test

```bash
# Run all smoke tests (no API key required)
python -m pytest tests/test_smoke.py -v

# Run specific test class
python -m pytest tests/test_smoke.py::TestUtils -v

# Run with coverage (if pytest-cov installed)
python -m pytest tests/test_smoke.py --cov=src
```

## Lint (optional)

```bash
# If ruff is installed
ruff check src/ tests/

# Or use flake8
flake8 src/ tests/
```

## Project Structure

```
pdy_youtube_research/
├── src/
│   ├── __init__.py      # Package init
│   ├── cli.py           # CLI entry point
│   ├── youtube_api.py   # YouTube API client & adapters
│   ├── pipeline.py      # Data processing pipeline
│   └── utils.py         # Utility functions
├── tests/
│   ├── __init__.py
│   └── test_smoke.py    # Smoke tests (no API key needed)
├── output/              # Generated CSV files
├── index.html           # Web UI (legacy)
├── script.js            # Web UI (legacy)
├── requirements.txt     # Python dependencies
├── .env.example         # Environment template
├── .gitignore
├── README.md
└── AGENTS.md            # This file
```

## Notes for AI Agents

1. **API Key**: The smoke tests do NOT require a YouTube API key. They use mocks.
2. **Output Directory**: CSV files are saved to `output/` directory (gitignored).
3. **Adapter Pattern**: New data sources (e.g., recommended videos) should implement `YouTubeAPIAdapter` interface.
4. **PR Structure**: This repo uses 3 PRs for v1:
   - PR1: Keyword Search Pipeline
   - PR2: Benchmark Input Mode
   - PR3: Script Abstraction
