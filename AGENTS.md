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
# Generate abstracted script from transcript file
python -m src.cli script --input transcript.txt

# With custom output path
python -m src.cli script --input transcript.txt --output my_script

# Output to specific directory
python -m src.cli --output-dir results script --input transcript.txt
```

## Test

```bash
# Run all tests (no API key required)
python -m pytest tests/ -v

# Run smoke tests only
python -m pytest tests/test_smoke.py -v

# Run benchmark tests only
python -m pytest tests/test_benchmark.py -v

# Run script abstraction tests only
python -m pytest tests/test_script.py -v

# Run with coverage (if pytest-cov installed)
python -m pytest tests/ --cov=src
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
│   ├── __init__.py          # Package init
│   ├── cli.py               # CLI entry point
│   ├── youtube_api.py       # YouTube API client & adapters
│   ├── pipeline.py          # Data processing pipeline
│   ├── script_generator.py  # Script abstraction (PR3)
│   └── utils.py             # Utility functions
├── tests/
│   ├── __init__.py
│   ├── test_smoke.py        # Smoke tests (PR1)
│   ├── test_benchmark.py    # Benchmark tests (PR2)
│   └── test_script.py       # Script abstraction tests (PR3)
├── examples/
│   ├── benchmark_videos.txt   # Example video IDs for benchmark
│   └── sample_transcript.txt  # Example transcript for script abstraction
├── output/              # Generated CSV/JSON/MD files (gitignored)
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
