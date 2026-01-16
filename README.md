# YouTube Research & Script Generation Tool

YouTubeリサーチ＆台本生成ツール v1

## Features

### A) Keyword Search Pipeline (PR1)
- キーワードでYouTube動画を検索
- 動画詳細・チャンネル情報を取得
- フィルタ条件: `viewCount >= subscriberCount * 5`
- 出力: raw.csv, winners.csv, unknown.csv, errors.csv

### B) Benchmark Video Mode (PR2)
- 動画ID/URLリストを入力
- 同じパイプラインで処理
- 最大10件まで対応

### C) Script Abstraction (PR3)
- 文字起こしテキストを入力
- 抽象化構成台本を生成 (JSON/Markdown)

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set YouTube API Key

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and add your YouTube Data API key:

```
YOUTUBE_API_KEY=your_api_key_here
```

Get your API key from: https://console.cloud.google.com/apis/credentials

## Usage

### Keyword Search

```bash
# Basic search
python -m src.cli search --keyword "python tutorial" --max-results 100

# With date filter
python -m src.cli search --keyword "python tutorial" --published-after 2024-01-01

# With region and language
python -m src.cli search --keyword "python tutorial" --region-code JP --relevance-language ja

# Custom view multiplier (default: 5.0)
python -m src.cli search --keyword "python tutorial" --view-multiplier 3.0
```

### Benchmark Mode

```bash
# With video IDs
python -m src.cli benchmark --video-ids "dQw4w9WgXcQ,VIDEO_ID2"

# With URLs
python -m src.cli benchmark --video-ids "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# From file
python -m src.cli benchmark --input-file videos.txt
```

### Script Abstraction (Coming in PR3)

```bash
python -m src.cli script --input transcript.txt --output script.json
```

## Output Files

All output files are saved to the `output/` directory:

| File | Description |
|------|-------------|
| `raw_TIMESTAMP.csv` | All fetched videos |
| `winners_TIMESTAMP.csv` | Videos passing the filter (viewCount >= subscriberCount * 5) |
| `unknown_TIMESTAMP.csv` | Videos with unknown subscriber count |
| `errors_TIMESTAMP.csv` | API errors and processing failures |

### CSV Columns

- `title` - Video title
- `description` - Video description
- `url` - Video URL
- `viewCount` - View count
- `channelTitle` - Channel name
- `subscriberCount` - Channel subscriber count (or "Unknown")
- `orientation` - Video orientation (horizontal/vertical/square/unknown)
- `thumbnailUrl` - Thumbnail URL
- `publishedAt` - Publish date
- `videoId` - YouTube video ID
- `channelId` - YouTube channel ID

## API Quota Optimization

This tool optimizes YouTube API quota usage by:
1. Using `search.list` with `part=id` only (100 quota units per call)
2. Batching `videos.list` calls (max 50 IDs per call)
3. Batching `channels.list` calls (max 50 IDs per call)

## Architecture

The tool uses an adapter pattern to allow future extensions:

```
YouTubeAPIAdapter (interface)
├── KeywordSearchAdapter - Keyword-based search
├── VideoIdAdapter - Direct video ID lookup
└── (Future) RecommendedAdapter - Recommended videos extraction
```

## Development

### Project Structure

```
pdy_youtube_research/
├── src/
│   ├── __init__.py
│   ├── cli.py          # CLI entry point
│   ├── youtube_api.py  # YouTube API client & adapters
│   ├── pipeline.py     # Data processing pipeline
│   └── utils.py        # Utility functions
├── output/             # Generated CSV files
├── index.html          # Web UI (legacy)
├── script.js           # Web UI (legacy)
├── requirements.txt
├── .env.example
└── README.md
```

## License

MIT
