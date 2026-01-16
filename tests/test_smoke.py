"""
Smoke tests for YouTube Research Tool.

These tests verify basic functionality without requiring a YouTube API key.
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils import extract_video_id, parse_video_ids_from_input, format_iso_date
from src.pipeline import VideoPipeline
from src.youtube_api import VideoInfo


class TestUtils(unittest.TestCase):
    """Test utility functions."""

    def test_extract_video_id_from_watch_url(self):
        """Test extracting video ID from standard watch URL."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        self.assertEqual(extract_video_id(url), "dQw4w9WgXcQ")

    def test_extract_video_id_from_short_url(self):
        """Test extracting video ID from youtu.be URL."""
        url = "https://youtu.be/dQw4w9WgXcQ"
        self.assertEqual(extract_video_id(url), "dQw4w9WgXcQ")

    def test_extract_video_id_from_shorts_url(self):
        """Test extracting video ID from shorts URL."""
        url = "https://www.youtube.com/shorts/dQw4w9WgXcQ"
        self.assertEqual(extract_video_id(url), "dQw4w9WgXcQ")

    def test_extract_video_id_plain_id(self):
        """Test extracting video ID when given plain ID."""
        video_id = "dQw4w9WgXcQ"
        self.assertEqual(extract_video_id(video_id), "dQw4w9WgXcQ")

    def test_parse_video_ids_from_input_comma_separated(self):
        """Test parsing comma-separated video IDs."""
        input_text = "dQw4w9WgXcQ, abc123def45, xyz789abc12"
        result = parse_video_ids_from_input(input_text)
        self.assertEqual(len(result), 3)
        self.assertIn("dQw4w9WgXcQ", result)

    def test_parse_video_ids_from_input_newline_separated(self):
        """Test parsing newline-separated video IDs."""
        input_text = "dQw4w9WgXcQ\nabc123def45\nxyz789abc12"
        result = parse_video_ids_from_input(input_text)
        self.assertEqual(len(result), 3)

    def test_format_iso_date(self):
        """Test ISO date formatting."""
        self.assertEqual(format_iso_date("2024-01-01"), "2024-01-01T00:00:00Z")
        self.assertEqual(format_iso_date("2024-01-01T12:00:00Z"), "2024-01-01T12:00:00Z")


class TestPipeline(unittest.TestCase):
    """Test video processing pipeline."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.pipeline = VideoPipeline(output_dir=self.temp_dir)

    def test_filter_videos_winners(self):
        """Test filtering videos that pass the engagement threshold."""
        videos = [
            VideoInfo(
                video_id="test1",
                title="Test Video 1",
                description="Description",
                url="https://youtube.com/watch?v=test1",
                view_count=10000,
                channel_id="ch1",
                channel_title="Channel 1",
                subscriber_count=1000,  # 10000 >= 1000 * 5 = True
                orientation="horizontal",
                thumbnail_url="https://example.com/thumb.jpg",
                published_at="2024-01-01T00:00:00Z",
            ),
            VideoInfo(
                video_id="test2",
                title="Test Video 2",
                description="Description",
                url="https://youtube.com/watch?v=test2",
                view_count=1000,
                channel_id="ch2",
                channel_title="Channel 2",
                subscriber_count=1000,  # 1000 >= 1000 * 5 = False
                orientation="horizontal",
                thumbnail_url="https://example.com/thumb.jpg",
                published_at="2024-01-01T00:00:00Z",
            ),
        ]

        winners, unknown, raw = self.pipeline.filter_videos(videos)
        
        self.assertEqual(len(winners), 1)
        self.assertEqual(winners[0].video_id, "test1")
        self.assertEqual(len(unknown), 0)
        self.assertEqual(len(raw), 2)

    def test_filter_videos_unknown_subscribers(self):
        """Test filtering videos with unknown subscriber count."""
        videos = [
            VideoInfo(
                video_id="test1",
                title="Test Video 1",
                description="Description",
                url="https://youtube.com/watch?v=test1",
                view_count=10000,
                channel_id="ch1",
                channel_title="Channel 1",
                subscriber_count=None,  # Unknown
                orientation="horizontal",
                thumbnail_url="https://example.com/thumb.jpg",
                published_at="2024-01-01T00:00:00Z",
            ),
        ]

        winners, unknown, raw = self.pipeline.filter_videos(videos)
        
        self.assertEqual(len(winners), 0)
        self.assertEqual(len(unknown), 1)
        self.assertEqual(unknown[0].video_id, "test1")

    def test_save_results_creates_csv_files(self):
        """Test that save_results creates all expected CSV files."""
        videos = [
            VideoInfo(
                video_id="test1",
                title="Test Video",
                description="Description",
                url="https://youtube.com/watch?v=test1",
                view_count=10000,
                channel_id="ch1",
                channel_title="Channel 1",
                subscriber_count=1000,
                orientation="horizontal",
                thumbnail_url="https://example.com/thumb.jpg",
                published_at="2024-01-01T00:00:00Z",
            ),
        ]

        output_files = self.pipeline.save_results(
            winners=videos,
            unknown=[],
            raw=videos,
            errors=[],
            prefix="test",
        )

        self.assertIn("raw", output_files)
        self.assertIn("winners", output_files)
        self.assertIn("unknown", output_files)
        self.assertIn("errors", output_files)

        # Verify files exist
        for file_path in output_files.values():
            self.assertTrue(os.path.exists(file_path))


class TestCLI(unittest.TestCase):
    """Test CLI functionality."""

    def test_cli_help(self):
        """Test that CLI help works."""
        import subprocess
        result = subprocess.run(
            [sys.executable, "-m", "src.cli", "--help"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("YouTube Research", result.stdout)

    def test_cli_search_help(self):
        """Test that search subcommand help works."""
        import subprocess
        result = subprocess.run(
            [sys.executable, "-m", "src.cli", "search", "--help"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("--keyword", result.stdout)


class TestYouTubeAPI(unittest.TestCase):
    """Test YouTube API client (mocked)."""

    def test_determine_orientation_horizontal(self):
        """Test orientation detection for horizontal video."""
        from src.youtube_api import YouTubeAPIClient
        
        # Mock the client initialization
        with patch.object(YouTubeAPIClient, '__init__', lambda self, api_key=None: None):
            client = YouTubeAPIClient()
            client.api_key = "fake_key"
            
            thumbnails = {
                "default": {"url": "https://example.com/thumb.jpg", "width": 120, "height": 90}
            }
            self.assertEqual(client.determine_orientation(thumbnails), "horizontal")

    def test_determine_orientation_vertical(self):
        """Test orientation detection for vertical video."""
        from src.youtube_api import YouTubeAPIClient
        
        with patch.object(YouTubeAPIClient, '__init__', lambda self, api_key=None: None):
            client = YouTubeAPIClient()
            client.api_key = "fake_key"
            
            thumbnails = {
                "default": {"url": "https://example.com/thumb.jpg", "width": 90, "height": 120}
            }
            self.assertEqual(client.determine_orientation(thumbnails), "vertical")

    def test_determine_orientation_unknown(self):
        """Test orientation detection when no dimensions available."""
        from src.youtube_api import YouTubeAPIClient
        
        with patch.object(YouTubeAPIClient, '__init__', lambda self, api_key=None: None):
            client = YouTubeAPIClient()
            client.api_key = "fake_key"
            
            thumbnails = {}
            self.assertEqual(client.determine_orientation(thumbnails), "unknown")


if __name__ == "__main__":
    unittest.main()
