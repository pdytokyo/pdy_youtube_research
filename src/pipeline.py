"""
Video Processing Pipeline

Handles filtering, categorization, and output generation.
"""

import csv
import os
from dataclasses import asdict
from datetime import datetime
from typing import Optional

from .youtube_api import VideoInfo


class VideoPipeline:
    """Pipeline for processing and filtering video data."""

    def __init__(self, output_dir: str = "output"):
        """
        Initialize the pipeline.

        Args:
            output_dir: Directory to save output files
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def filter_videos(
        self,
        videos: list[VideoInfo],
        view_multiplier: float = 5.0,
    ) -> tuple[list[VideoInfo], list[VideoInfo], list[VideoInfo]]:
        """
        Filter videos based on engagement criteria.

        Filter condition: viewCount >= subscriberCount * view_multiplier

        Args:
            videos: List of VideoInfo objects
            view_multiplier: Multiplier for subscriber count threshold

        Returns:
            Tuple of (winners, unknown, all_videos)
            - winners: Videos that pass the filter
            - unknown: Videos where subscriber count is unknown
            - all_videos: All input videos (raw)
        """
        winners = []
        unknown = []

        for video in videos:
            if video.subscriber_count is None:
                unknown.append(video)
            elif video.view_count >= video.subscriber_count * view_multiplier:
                winners.append(video)

        return winners, unknown, videos

    def _video_to_row(self, video: VideoInfo) -> dict:
        """Convert VideoInfo to a dictionary for CSV output."""
        return {
            "title": video.title,
            "description": video.description,
            "url": video.url,
            "viewCount": video.view_count,
            "channelTitle": video.channel_title,
            "subscriberCount": video.subscriber_count if video.subscriber_count is not None else "Unknown",
            "orientation": video.orientation,
            "thumbnailUrl": video.thumbnail_url,
            "publishedAt": video.published_at,
            "videoId": video.video_id,
            "channelId": video.channel_id,
        }

    def _error_to_row(self, error: dict) -> dict:
        """Convert error dict to a row for CSV output."""
        return {
            "type": error.get("type", "unknown"),
            "identifier": error.get("video_id") or error.get("keyword") or error.get("batch_start", ""),
            "error": error.get("error", ""),
            "timestamp": datetime.now().isoformat(),
        }

    def save_results(
        self,
        winners: list[VideoInfo],
        unknown: list[VideoInfo],
        raw: list[VideoInfo],
        errors: list[dict],
        prefix: str = "",
    ) -> dict[str, str]:
        """
        Save results to CSV files.

        Args:
            winners: Videos that passed the filter
            unknown: Videos with unknown subscriber count
            raw: All videos (unfiltered)
            errors: List of error records
            prefix: Optional prefix for output filenames

        Returns:
            Dictionary mapping output type to file path
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix_str = f"{prefix}_" if prefix else ""
        
        output_files = {}

        # Define CSV columns for videos
        video_columns = [
            "title", "description", "url", "viewCount", "channelTitle",
            "subscriberCount", "orientation", "thumbnailUrl", "publishedAt",
            "videoId", "channelId"
        ]

        # Save raw.csv
        raw_path = os.path.join(self.output_dir, f"{prefix_str}raw_{timestamp}.csv")
        self._write_csv(raw_path, video_columns, [self._video_to_row(v) for v in raw])
        output_files["raw"] = raw_path

        # Save winners.csv
        winners_path = os.path.join(self.output_dir, f"{prefix_str}winners_{timestamp}.csv")
        self._write_csv(winners_path, video_columns, [self._video_to_row(v) for v in winners])
        output_files["winners"] = winners_path

        # Save unknown.csv
        unknown_path = os.path.join(self.output_dir, f"{prefix_str}unknown_{timestamp}.csv")
        self._write_csv(unknown_path, video_columns, [self._video_to_row(v) for v in unknown])
        output_files["unknown"] = unknown_path

        # Save errors.csv
        error_columns = ["type", "identifier", "error", "timestamp"]
        errors_path = os.path.join(self.output_dir, f"{prefix_str}errors_{timestamp}.csv")
        self._write_csv(errors_path, error_columns, [self._error_to_row(e) for e in errors])
        output_files["errors"] = errors_path

        return output_files

    def _write_csv(self, path: str, columns: list[str], rows: list[dict]) -> None:
        """Write rows to a CSV file."""
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)

    def print_summary(
        self,
        winners: list[VideoInfo],
        unknown: list[VideoInfo],
        raw: list[VideoInfo],
        errors: list[dict],
        output_files: dict[str, str],
    ) -> None:
        """Print a summary of the pipeline results."""
        print("\n" + "=" * 50)
        print("Pipeline Results Summary")
        print("=" * 50)
        print(f"Total videos processed: {len(raw)}")
        print(f"Winners (viewCount >= subscriberCount * 5): {len(winners)}")
        print(f"Unknown (subscriber count unavailable): {len(unknown)}")
        print(f"Filtered out: {len(raw) - len(winners) - len(unknown)}")
        print(f"Errors: {len(errors)}")
        print("\nOutput files:")
        for output_type, path in output_files.items():
            print(f"  - {output_type}: {path}")
        print("=" * 50 + "\n")
