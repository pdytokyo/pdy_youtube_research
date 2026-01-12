"""
Tests for Benchmark Input Mode (PR2).

These tests verify the benchmark mode functionality for analyzing specific videos.
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch, MagicMock

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils import extract_video_id, parse_video_ids_from_input
from src.youtube_api import VideoIdAdapter, YouTubeAPIClient, VideoInfo
from src.pipeline import VideoPipeline


class TestVideoIdExtraction(unittest.TestCase):
    """Test video ID extraction from various URL formats."""

    def test_extract_from_standard_url(self):
        """Test extraction from standard watch URL."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        self.assertEqual(extract_video_id(url), "dQw4w9WgXcQ")

    def test_extract_from_short_url(self):
        """Test extraction from youtu.be short URL."""
        url = "https://youtu.be/dQw4w9WgXcQ"
        self.assertEqual(extract_video_id(url), "dQw4w9WgXcQ")

    def test_extract_from_shorts_url(self):
        """Test extraction from YouTube Shorts URL."""
        url = "https://www.youtube.com/shorts/dQw4w9WgXcQ"
        self.assertEqual(extract_video_id(url), "dQw4w9WgXcQ")

    def test_extract_from_embed_url(self):
        """Test extraction from embed URL."""
        url = "https://www.youtube.com/embed/dQw4w9WgXcQ"
        self.assertEqual(extract_video_id(url), "dQw4w9WgXcQ")

    def test_extract_from_mobile_url(self):
        """Test extraction from mobile URL."""
        url = "https://m.youtube.com/watch?v=dQw4w9WgXcQ"
        self.assertEqual(extract_video_id(url), "dQw4w9WgXcQ")

    def test_extract_plain_id(self):
        """Test extraction when given plain video ID."""
        video_id = "dQw4w9WgXcQ"
        self.assertEqual(extract_video_id(video_id), "dQw4w9WgXcQ")

    def test_extract_with_extra_params(self):
        """Test extraction from URL with extra parameters."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=120&list=PLtest"
        self.assertEqual(extract_video_id(url), "dQw4w9WgXcQ")

    def test_invalid_url_returns_none(self):
        """Test that invalid URLs return None."""
        self.assertIsNone(extract_video_id("https://example.com/video"))
        self.assertIsNone(extract_video_id("not_a_valid_id"))
        self.assertIsNone(extract_video_id(""))


class TestParseVideoIds(unittest.TestCase):
    """Test parsing multiple video IDs from input."""

    def test_parse_comma_separated(self):
        """Test parsing comma-separated video IDs."""
        input_text = "dQw4w9WgXcQ, abc123def45, xyz789abc12"
        result = parse_video_ids_from_input(input_text)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], "dQw4w9WgXcQ")

    def test_parse_newline_separated(self):
        """Test parsing newline-separated video IDs."""
        input_text = """dQw4w9WgXcQ
abc123def45
xyz789abc12"""
        result = parse_video_ids_from_input(input_text)
        self.assertEqual(len(result), 3)

    def test_parse_mixed_urls_and_ids(self):
        """Test parsing mixed URLs and plain IDs."""
        input_text = """https://www.youtube.com/watch?v=dQw4w9WgXcQ
abc123def45
https://youtu.be/xyz789abc12"""
        result = parse_video_ids_from_input(input_text)
        self.assertEqual(len(result), 3)
        self.assertIn("dQw4w9WgXcQ", result)
        self.assertIn("abc123def45", result)
        self.assertIn("xyz789abc12", result)

    def test_parse_with_empty_lines(self):
        """Test parsing with empty lines."""
        input_text = """dQw4w9WgXcQ

abc123def45

"""
        result = parse_video_ids_from_input(input_text)
        self.assertEqual(len(result), 2)

    def test_parse_with_whitespace(self):
        """Test parsing with extra whitespace."""
        input_text = "  dQw4w9WgXcQ  ,  abc123def45  "
        result = parse_video_ids_from_input(input_text)
        self.assertEqual(len(result), 2)


class TestVideoIdAdapter(unittest.TestCase):
    """Test VideoIdAdapter for benchmark mode."""

    def setUp(self):
        """Set up test fixtures with mocked API client."""
        self.mock_client = Mock(spec=YouTubeAPIClient)
        self.adapter = VideoIdAdapter(self.mock_client)

    def test_get_videos_returns_video_info(self):
        """Test that get_videos returns VideoInfo objects."""
        # Mock video details response
        self.mock_client.get_video_details.return_value = [
            {
                "id": "test123video",
                "snippet": {
                    "title": "Test Video",
                    "description": "Test description",
                    "channelId": "channel123",
                    "channelTitle": "Test Channel",
                    "publishedAt": "2024-01-01T00:00:00Z",
                    "thumbnails": {
                        "default": {"url": "https://example.com/thumb.jpg", "width": 120, "height": 90}
                    }
                },
                "statistics": {
                    "viewCount": "10000"
                }
            }
        ]

        # Mock channel details response
        self.mock_client.get_channel_details.return_value = {
            "channel123": {
                "statistics": {
                    "subscriberCount": "1000"
                }
            }
        }

        # Mock orientation detection
        self.mock_client.determine_orientation.return_value = "horizontal"

        videos, errors = self.adapter.get_videos(video_ids=["test123video"])

        self.assertEqual(len(videos), 1)
        self.assertEqual(videos[0].video_id, "test123video")
        self.assertEqual(videos[0].title, "Test Video")
        self.assertEqual(videos[0].view_count, 10000)
        self.assertEqual(videos[0].subscriber_count, 1000)
        self.assertEqual(len(errors), 0)

    def test_get_videos_handles_unknown_subscriber_count(self):
        """Test handling of videos with hidden subscriber count."""
        self.mock_client.get_video_details.return_value = [
            {
                "id": "test123video",
                "snippet": {
                    "title": "Test Video",
                    "description": "Test description",
                    "channelId": "channel123",
                    "channelTitle": "Test Channel",
                    "publishedAt": "2024-01-01T00:00:00Z",
                    "thumbnails": {}
                },
                "statistics": {
                    "viewCount": "10000"
                }
            }
        ]

        # Channel with hidden subscriber count
        self.mock_client.get_channel_details.return_value = {
            "channel123": {
                "statistics": {}  # No subscriberCount
            }
        }

        self.mock_client.determine_orientation.return_value = "unknown"

        videos, errors = self.adapter.get_videos(video_ids=["test123video"])

        self.assertEqual(len(videos), 1)
        self.assertIsNone(videos[0].subscriber_count)

    def test_get_videos_batches_requests(self):
        """Test that requests are batched for efficiency."""
        # Create 60 video IDs (should be batched into 2 calls of 50 max)
        video_ids = [f"video{i:03d}xxxxx" for i in range(60)]

        self.mock_client.get_video_details.return_value = []
        self.mock_client.get_channel_details.return_value = {}

        self.adapter.get_videos(video_ids=video_ids)

        # Should be called twice (50 + 10)
        self.assertEqual(self.mock_client.get_video_details.call_count, 2)


class TestBenchmarkCLI(unittest.TestCase):
    """Test benchmark CLI command."""

    def test_benchmark_help(self):
        """Test that benchmark subcommand help works."""
        import subprocess
        result = subprocess.run(
            [sys.executable, "-m", "src.cli", "benchmark", "--help"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("--video-ids", result.stdout)
        self.assertIn("--input-file", result.stdout)

    def test_benchmark_requires_input(self):
        """Test that benchmark command requires video IDs or input file."""
        import subprocess
        result = subprocess.run(
            [sys.executable, "-m", "src.cli", "benchmark"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            env={**os.environ, "YOUTUBE_API_KEY": "fake_key_for_test"}
        )
        # Should fail because no video IDs provided
        self.assertNotEqual(result.returncode, 0)


class TestBenchmarkPipeline(unittest.TestCase):
    """Test benchmark mode pipeline integration."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.pipeline = VideoPipeline(output_dir=self.temp_dir)

    def test_benchmark_filter_with_mixed_results(self):
        """Test filtering benchmark videos with mixed results."""
        videos = [
            # Winner: 10000 >= 1000 * 5
            VideoInfo(
                video_id="winner1",
                title="Winner Video",
                description="High engagement",
                url="https://youtube.com/watch?v=winner1",
                view_count=10000,
                channel_id="ch1",
                channel_title="Channel 1",
                subscriber_count=1000,
                orientation="horizontal",
                thumbnail_url="https://example.com/thumb.jpg",
                published_at="2024-01-01T00:00:00Z",
            ),
            # Not winner: 2000 < 1000 * 5
            VideoInfo(
                video_id="loser1",
                title="Low Engagement Video",
                description="Low engagement",
                url="https://youtube.com/watch?v=loser1",
                view_count=2000,
                channel_id="ch2",
                channel_title="Channel 2",
                subscriber_count=1000,
                orientation="horizontal",
                thumbnail_url="https://example.com/thumb.jpg",
                published_at="2024-01-01T00:00:00Z",
            ),
            # Unknown: subscriber count is None
            VideoInfo(
                video_id="unknown1",
                title="Unknown Subs Video",
                description="Hidden subscriber count",
                url="https://youtube.com/watch?v=unknown1",
                view_count=5000,
                channel_id="ch3",
                channel_title="Channel 3",
                subscriber_count=None,
                orientation="vertical",
                thumbnail_url="https://example.com/thumb.jpg",
                published_at="2024-01-01T00:00:00Z",
            ),
        ]

        winners, unknown, raw = self.pipeline.filter_videos(videos)

        self.assertEqual(len(winners), 1)
        self.assertEqual(winners[0].video_id, "winner1")
        self.assertEqual(len(unknown), 1)
        self.assertEqual(unknown[0].video_id, "unknown1")
        self.assertEqual(len(raw), 3)

    def test_benchmark_save_results(self):
        """Test saving benchmark results to CSV."""
        videos = [
            VideoInfo(
                video_id="bench1",
                title="Benchmark Video",
                description="Test",
                url="https://youtube.com/watch?v=bench1",
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
            prefix="benchmark",
        )

        # Verify all files are created
        self.assertIn("raw", output_files)
        self.assertIn("winners", output_files)
        self.assertIn("unknown", output_files)
        self.assertIn("errors", output_files)

        # Verify files exist and have correct prefix
        for file_type, file_path in output_files.items():
            self.assertTrue(os.path.exists(file_path))
            self.assertIn("benchmark", os.path.basename(file_path))


if __name__ == "__main__":
    unittest.main()
