# YouTube Research & Script Generation Tool

YouTubeリサーチ＆台本生成ツール v1

SNSマーケ塾生向けのローカルツール。キーワード検索→当たり動画選択→音声DL→Whisper文字起こし→構成/タイムコード/抽象化台本まで一気通貫で実行できます。

## Quick Start (塾生向け最短手順)

### 1. リポジトリをクローン

```bash
git clone https://github.com/pdytokyo/pdy_youtube_research.git
cd pdy_youtube_research
```

### 2. Python仮想環境を作成

```bash
python -m venv venv
source venv/bin/activate  # Mac/Linux
# Windows: venv\Scripts\activate
```

### 3. 依存パッケージをインストール

```bash
pip install -r requirements.txt
```

### 4. 外部ツールをインストール (Mac)

```bash
brew install yt-dlp ffmpeg
```

### 5. YouTube API キーを設定

```bash
cp .env.example .env
```

`.env` ファイルを編集して API キーを追加:

```
YOUTUBE_API_KEY=your_api_key_here
```

API キーの取得: https://console.cloud.google.com/apis/credentials

### 6. Streamlit UIを起動

```bash
streamlit run app.py
```

ブラウザで http://localhost:8501 が開きます。

## Features

### Streamlit UI (メイン機能)

1. **Keyword Search** - キーワードでYouTube動画を検索、Winnersを表示
2. **Analyze Video** - 選択した動画を分析（音声DL→文字起こし→台本生成）
3. **Direct URL** - URLを直接入力して分析

### 分析パイプライン

1. **音声ダウンロード** - yt-dlpで音声を取得
2. **Whisper文字起こし** - セグメント（タイムコード付き）で文字起こし
3. **構成/台本生成** - セクション分割、変数抽出、抽象化テンプレート生成

### A) Keyword Search Pipeline
- キーワードでYouTube動画を検索
- 動画詳細・チャンネル情報を取得
- フィルタ条件: `viewCount >= subscriberCount * 5`
- 出力: raw.csv, winners.csv, unknown.csv, errors.csv

### B) Benchmark Video Mode
- 動画ID/URLリストを入力
- 同じパイプラインで処理
- 最大10件まで対応

### C) Script Abstraction
- 文字起こしテキストを入力
- 抽象化構成台本を生成 (JSON/Markdown)

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
├── app.py                    # Streamlit UI (メイン)
├── src/
│   ├── cli.py               # CLI entry point
│   ├── youtube_api.py       # YouTube API client
│   ├── pipeline.py          # Video filtering pipeline
│   ├── audio_downloader.py  # yt-dlp wrapper
│   ├── transcriber.py       # Whisper transcription
│   ├── outline_generator.py # Outline with timecodes
│   ├── script_generator.py  # Script abstraction
│   └── utils.py             # Utilities
├── tests/
│   ├── test_smoke.py        # Smoke tests
│   ├── test_benchmark.py    # Benchmark tests
│   ├── test_script.py       # Script tests
│   └── test_outline.py      # Outline tests
├── output/                   # Generated files
├── requirements.txt
├── .env.example
└── README.md
```

## Troubleshooting

### yt-dlp が見つからない

```bash
brew install yt-dlp
# または pip install yt-dlp
```

### ffmpeg が見つからない

```bash
brew install ffmpeg
```

### Whisper モデルのダウンロードが遅い

初回起動時にモデルがダウンロードされます。サイドバーで小さいモデル（tiny, base）を選択すると高速です。

### メモリ不足

Whisperモデルを小さいものに変更してください（tiny または base）。

### 動画がダウンロードできない

- 動画が非公開/削除されていないか確認
- 年齢制限/メンバー限定動画は対応不可

## License

MIT
