"""
Command Line Interface for YouTube Research Tool.

Usage:
    python -m src.cli search --keyword "python tutorial" --max-results 100
    python -m src.cli benchmark --video-ids "VIDEO_ID1,VIDEO_ID2"
    python -m src.cli script --input transcript.txt --output script.json
"""

import argparse
import os
import sys
from typing import Optional

from dotenv import load_dotenv

from .youtube_api import YouTubeAPIClient, KeywordSearchAdapter, VideoIdAdapter
from .pipeline import VideoPipeline
from .utils import parse_video_ids_from_input, format_iso_date
from .script_generator import abstract_transcript


def search_command(args: argparse.Namespace) -> int:
    """Execute keyword search pipeline."""
    # Load environment variables
    load_dotenv()
    
    api_key = args.api_key or os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        print("Error: YouTube API key is required.")
        print("Set YOUTUBE_API_KEY environment variable or use --api-key option.")
        return 1

    try:
        # Initialize client and adapter
        client = YouTubeAPIClient(api_key=api_key)
        adapter = KeywordSearchAdapter(client)
        pipeline = VideoPipeline(output_dir=args.output_dir)

        print(f"Searching for: {args.keyword}")
        print(f"Max results: {args.max_results}")

        # Build search parameters
        search_params = {
            "keyword": args.keyword,
            "max_results": args.max_results,
        }

        if args.published_after:
            search_params["published_after"] = format_iso_date(args.published_after)
        if args.published_before:
            search_params["published_before"] = format_iso_date(args.published_before)
        if args.region_code:
            search_params["region_code"] = args.region_code
        if args.relevance_language:
            search_params["relevance_language"] = args.relevance_language

        # Execute search
        videos, errors = adapter.get_videos(**search_params)

        if not videos and not errors:
            print("No videos found.")
            return 0

        # Filter videos
        winners, unknown, raw = pipeline.filter_videos(
            videos,
            view_multiplier=args.view_multiplier,
        )

        # Save results
        output_files = pipeline.save_results(
            winners=winners,
            unknown=unknown,
            raw=raw,
            errors=errors,
            prefix=args.keyword.replace(" ", "_")[:20],
        )

        # Print summary
        pipeline.print_summary(winners, unknown, raw, errors, output_files)

        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


def benchmark_command(args: argparse.Namespace) -> int:
    """Execute benchmark mode with video IDs."""
    # Load environment variables
    load_dotenv()
    
    api_key = args.api_key or os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        print("Error: YouTube API key is required.")
        print("Set YOUTUBE_API_KEY environment variable or use --api-key option.")
        return 1

    # Parse video IDs from input
    if args.video_ids:
        video_ids = parse_video_ids_from_input(args.video_ids)
    elif args.input_file:
        with open(args.input_file, "r", encoding="utf-8") as f:
            video_ids = parse_video_ids_from_input(f.read())
    else:
        print("Error: Provide video IDs via --video-ids or --input-file")
        return 1

    if not video_ids:
        print("Error: No valid video IDs found in input.")
        return 1

    # Limit to 10 videos for benchmark mode
    if len(video_ids) > 10:
        print(f"Warning: Limiting to first 10 videos (got {len(video_ids)})")
        video_ids = video_ids[:10]

    try:
        # Initialize client and adapter
        client = YouTubeAPIClient(api_key=api_key)
        adapter = VideoIdAdapter(client)
        pipeline = VideoPipeline(output_dir=args.output_dir)

        print(f"Processing {len(video_ids)} videos...")

        # Get video information
        videos, errors = adapter.get_videos(video_ids=video_ids)

        if not videos and not errors:
            print("No videos found.")
            return 0

        # Filter videos
        winners, unknown, raw = pipeline.filter_videos(
            videos,
            view_multiplier=args.view_multiplier,
        )

        # Save results
        output_files = pipeline.save_results(
            winners=winners,
            unknown=unknown,
            raw=raw,
            errors=errors,
            prefix="benchmark",
        )

        # Print summary
        pipeline.print_summary(winners, unknown, raw, errors, output_files)

        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


def script_command(args: argparse.Namespace) -> int:
    """Execute script abstraction to generate abstracted script template."""
    # Get input transcript
    if args.input:
        try:
            with open(args.input, "r", encoding="utf-8") as f:
                transcript = f.read()
        except FileNotFoundError:
            print(f"Error: Input file not found: {args.input}")
            return 1
        except Exception as e:
            print(f"Error reading input file: {e}")
            return 1
    elif args.text:
        transcript = args.text
    else:
        print("Error: Provide transcript via --input file or --text")
        return 1

    if not transcript.strip():
        print("Error: Transcript is empty")
        return 1

    print(f"Processing transcript ({len(transcript)} characters)...")

    try:
        # Determine output paths
        output_dir = args.output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if args.output:
            # Use specified output path
            base_path = args.output.rsplit(".", 1)[0]
            json_path = f"{base_path}.json"
            md_path = f"{base_path}.md"
        else:
            # Generate default output paths
            json_path = os.path.join(output_dir, f"script_{timestamp}.json")
            md_path = os.path.join(output_dir, f"script_{timestamp}.md")

        # Generate abstracted script
        result = abstract_transcript(
            transcript=transcript,
            output_json_path=json_path,
            output_md_path=md_path,
        )

        # Print summary
        print("\n" + "=" * 50)
        print("Script Abstraction Complete")
        print("=" * 50)
        print(f"Original length: {result.metadata.get('original_length', 'N/A')} characters")
        print(f"Sections identified: {result.metadata.get('section_count', 'N/A')}")
        print(f"Variables extracted: {result.metadata.get('variable_count', 'N/A')}")
        print(f"Estimated duration: {result.metadata.get('estimated_duration', 'N/A')}")
        print("\nOutput files:")
        print(f"  - JSON: {json_path}")
        print(f"  - Markdown: {md_path}")
        print("=" * 50 + "\n")

        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


def main() -> int:
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description="YouTube Research & Script Generation Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Keyword search
  python -m src.cli search --keyword "python tutorial" --max-results 100

  # Benchmark mode with video IDs
  python -m src.cli benchmark --video-ids "dQw4w9WgXcQ,VIDEO_ID2"

  # Script abstraction (PR3)
  python -m src.cli script --input transcript.txt
        """,
    )

    parser.add_argument(
        "--api-key",
        help="YouTube Data API key (or set YOUTUBE_API_KEY env var)",
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Output directory for CSV files (default: output)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Search command
    search_parser = subparsers.add_parser("search", help="Search videos by keyword")
    search_parser.add_argument(
        "--keyword", "-k",
        required=True,
        help="Search keyword",
    )
    search_parser.add_argument(
        "--max-results", "-n",
        type=int,
        default=200,
        help="Maximum number of results (default: 200)",
    )
    search_parser.add_argument(
        "--published-after",
        help="Filter videos published after this date (YYYY-MM-DD)",
    )
    search_parser.add_argument(
        "--published-before",
        help="Filter videos published before this date (YYYY-MM-DD)",
    )
    search_parser.add_argument(
        "--region-code",
        help="Region code (e.g., JP, US)",
    )
    search_parser.add_argument(
        "--relevance-language",
        help="Relevance language (e.g., ja, en)",
    )
    search_parser.add_argument(
        "--view-multiplier",
        type=float,
        default=5.0,
        help="View count multiplier for winner filter (default: 5.0)",
    )
    search_parser.set_defaults(func=search_command)

    # Benchmark command
    benchmark_parser = subparsers.add_parser("benchmark", help="Analyze specific videos")
    benchmark_parser.add_argument(
        "--video-ids", "-v",
        help="Comma-separated video IDs or URLs",
    )
    benchmark_parser.add_argument(
        "--input-file", "-i",
        help="File containing video IDs or URLs (one per line)",
    )
    benchmark_parser.add_argument(
        "--view-multiplier",
        type=float,
        default=5.0,
        help="View count multiplier for winner filter (default: 5.0)",
    )
    benchmark_parser.set_defaults(func=benchmark_command)

    # Script command
    script_parser = subparsers.add_parser("script", help="Generate abstracted script from transcript")
    script_parser.add_argument(
        "--input", "-i",
        help="Input transcript file path",
    )
    script_parser.add_argument(
        "--text", "-t",
        help="Direct transcript text input (alternative to --input file)",
    )
    script_parser.add_argument(
        "--output", "-o",
        help="Output file base path (will create .json and .md files)",
    )
    script_parser.set_defaults(func=script_command)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
