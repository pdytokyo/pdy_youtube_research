"""
YouTube Data API v3 Client

Handles all YouTube API interactions with quota optimization.
"""

import os
import re
from typing import Optional
from dataclasses import dataclass
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


def parse_iso8601_duration(duration_str: str) -> int:
    """
    Parse ISO 8601 duration format to seconds.
    
    Examples:
        PT12M5S -> 725 seconds
        PT1H30M -> 5400 seconds
        PT45S -> 45 seconds
    """
    if not duration_str:
        return 0
    
    pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
    match = re.match(pattern, duration_str)
    
    if not match:
        return 0
    
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    
    return hours * 3600 + minutes * 60 + seconds


def format_duration(seconds: int) -> str:
    """
    Format seconds as M:SS or H:MM:SS.
    
    Examples:
        36 -> "0:36"
        725 -> "12:05"
        3665 -> "1:01:05"
    """
    if seconds < 0:
        return "0:00"
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def calculate_aspect_ratio(width: int, height: int) -> str:
    """
    Calculate aspect ratio string from dimensions.
    
    Returns common ratios like "16:9", "9:16", "1:1", or "W:H" for uncommon ratios.
    """
    if not width or not height:
        return "不明"
    
    from math import gcd
    divisor = gcd(width, height)
    w = width // divisor
    h = height // divisor
    
    common_ratios = {
        (16, 9): "16:9",
        (9, 16): "9:16",
        (4, 3): "4:3",
        (3, 4): "3:4",
        (1, 1): "1:1",
        (21, 9): "21:9",
        (9, 21): "9:21",
    }
    
    if (w, h) in common_ratios:
        return common_ratios[(w, h)]
    
    ratio = width / height
    if abs(ratio - 16/9) < 0.1:
        return "16:9"
    elif abs(ratio - 9/16) < 0.1:
        return "9:16"
    elif abs(ratio - 4/3) < 0.1:
        return "4:3"
    elif abs(ratio - 3/4) < 0.1:
        return "3:4"
    elif abs(ratio - 1) < 0.1:
        return "1:1"
    
    return f"{w}:{h}"


@dataclass
class VideoInfo:
    """Video information from YouTube API."""
    video_id: str
    title: str
    description: str
    url: str
    view_count: int
    channel_id: str
    channel_title: str
    subscriber_count: Optional[int]
    orientation: str
    thumbnail_url: str
    published_at: str
    duration_seconds: int = 0
    thumbnail_width: int = 0
    thumbnail_height: int = 0

    @property
    def duration_formatted(self) -> str:
        """Get formatted duration string (M:SS or H:MM:SS)."""
        return format_duration(self.duration_seconds)

    @property
    def aspect_ratio(self) -> str:
        """Get aspect ratio string."""
        return calculate_aspect_ratio(self.thumbnail_width, self.thumbnail_height)

    @property
    def is_short(self) -> bool:
        """Check if video is a Short (<=90 seconds)."""
        return self.duration_seconds <= 90

    @property
    def length_label(self) -> str:
        """Get SHORT or LONG label."""
        return "SHORT" if self.is_short else "LONG"


class YouTubeAPIClient:
    """YouTube Data API v3 client with quota optimization."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize YouTube API client.

        Args:
            api_key: YouTube Data API key. If not provided, reads from YOUTUBE_API_KEY env var.
        """
        self.api_key = api_key or os.environ.get("YOUTUBE_API_KEY")
        if not self.api_key:
            raise ValueError("YouTube API key is required. Set YOUTUBE_API_KEY environment variable or pass api_key parameter.")
        
        self.youtube = build("youtube", "v3", developerKey=self.api_key)

    def search_videos(
        self,
        keyword: str,
        max_results: int = 50,
        published_after: Optional[str] = None,
        published_before: Optional[str] = None,
        region_code: Optional[str] = None,
        relevance_language: Optional[str] = None,
        page_token: Optional[str] = None,
    ) -> tuple[list[str], Optional[str]]:
        """
        Search for videos by keyword.

        Args:
            keyword: Search keyword
            max_results: Maximum number of results per page (max 50)
            published_after: Filter by publish date (ISO 8601 format)
            published_before: Filter by publish date (ISO 8601 format)
            region_code: Region code (e.g., 'JP', 'US')
            relevance_language: Language code (e.g., 'ja', 'en')
            page_token: Token for pagination

        Returns:
            Tuple of (list of video IDs, next page token or None)
        """
        request_params = {
            "part": "id",
            "q": keyword,
            "type": "video",
            "maxResults": min(max_results, 50),
        }

        if published_after:
            request_params["publishedAfter"] = published_after
        if published_before:
            request_params["publishedBefore"] = published_before
        if region_code:
            request_params["regionCode"] = region_code
        if relevance_language:
            request_params["relevanceLanguage"] = relevance_language
        if page_token:
            request_params["pageToken"] = page_token

        response = self.youtube.search().list(**request_params).execute()

        video_ids = [item["id"]["videoId"] for item in response.get("items", [])]
        next_page_token = response.get("nextPageToken")

        return video_ids, next_page_token

    def get_video_details(self, video_ids: list[str]) -> list[dict]:
        """
        Get detailed information for multiple videos.

        Args:
            video_ids: List of video IDs (max 50 per call)

        Returns:
            List of video detail dictionaries
        """
        if not video_ids:
            return []

        # API allows max 50 IDs per request
        video_ids = video_ids[:50]

        response = self.youtube.videos().list(
            part="snippet,statistics,contentDetails",
            id=",".join(video_ids)
        ).execute()

        return response.get("items", [])

    def get_channel_details(self, channel_ids: list[str]) -> dict[str, dict]:
        """
        Get detailed information for multiple channels.

        Args:
            channel_ids: List of channel IDs (max 50 per call)

        Returns:
            Dictionary mapping channel ID to channel details
        """
        if not channel_ids:
            return {}

        # Remove duplicates and limit to 50
        channel_ids = list(set(channel_ids))[:50]

        response = self.youtube.channels().list(
            part="statistics",
            id=",".join(channel_ids)
        ).execute()

        return {
            item["id"]: item
            for item in response.get("items", [])
        }

    def determine_orientation(self, thumbnails: dict) -> str:
        """
        Determine video orientation from thumbnail dimensions.

        Args:
            thumbnails: Thumbnail data from video snippet

        Returns:
            'horizontal', 'vertical', 'square', or 'unknown'
        """
        # Try to get dimensions from maxres, then standard, then high, then medium, then default
        for quality in ["maxres", "standard", "high", "medium", "default"]:
            if quality in thumbnails:
                thumb = thumbnails[quality]
                width = thumb.get("width")
                height = thumb.get("height")
                
                if width and height:
                    if width > height:
                        return "horizontal"
                    elif height > width:
                        return "vertical"
                    else:
                        return "square"
        
        return "unknown"


class YouTubeAPIAdapter:
    """
    Adapter interface for YouTube data retrieval.
    
    This allows for future implementations like:
    - Recommended videos extraction (v2)
    - Auto transcript retrieval (v2)
    """

    def get_videos(self, **kwargs) -> list[VideoInfo]:
        """Get videos based on implementation-specific criteria."""
        raise NotImplementedError("Subclasses must implement get_videos()")


class KeywordSearchAdapter(YouTubeAPIAdapter):
    """Adapter for keyword-based video search."""

    def __init__(self, client: YouTubeAPIClient):
        self.client = client

    def get_videos(
        self,
        keyword: str,
        max_results: int = 200,
        published_after: Optional[str] = None,
        published_before: Optional[str] = None,
        region_code: Optional[str] = None,
        relevance_language: Optional[str] = None,
    ) -> tuple[list[VideoInfo], list[dict]]:
        """
        Search for videos by keyword and return enriched video info.

        Args:
            keyword: Search keyword
            max_results: Maximum total results to fetch
            published_after: Filter by publish date (ISO 8601)
            published_before: Filter by publish date (ISO 8601)
            region_code: Region code
            relevance_language: Language code

        Returns:
            Tuple of (list of VideoInfo objects, list of error records)
        """
        all_video_ids = []
        next_page_token = None
        errors = []

        # Collect video IDs through pagination
        while len(all_video_ids) < max_results:
            try:
                video_ids, next_page_token = self.client.search_videos(
                    keyword=keyword,
                    max_results=min(50, max_results - len(all_video_ids)),
                    published_after=published_after,
                    published_before=published_before,
                    region_code=region_code,
                    relevance_language=relevance_language,
                    page_token=next_page_token,
                )
                all_video_ids.extend(video_ids)

                if not next_page_token:
                    break
            except HttpError as e:
                errors.append({
                    "type": "search_error",
                    "keyword": keyword,
                    "error": str(e),
                })
                break

        # Process videos in batches of 50
        videos = []
        for i in range(0, len(all_video_ids), 50):
            batch_ids = all_video_ids[i:i + 50]
            
            try:
                # Get video details
                video_details = self.client.get_video_details(batch_ids)
                
                # Get unique channel IDs
                channel_ids = list(set(
                    v["snippet"]["channelId"] for v in video_details
                ))
                
                # Get channel details
                channel_details = self.client.get_channel_details(channel_ids)
                
                # Build VideoInfo objects
                for video in video_details:
                    try:
                        snippet = video["snippet"]
                        statistics = video.get("statistics", {})
                        content_details = video.get("contentDetails", {})
                        channel_id = snippet["channelId"]
                        channel_info = channel_details.get(channel_id, {})
                        channel_stats = channel_info.get("statistics", {})
                        
                        # Get subscriber count (may be hidden)
                        sub_count_str = channel_stats.get("subscriberCount")
                        subscriber_count = int(sub_count_str) if sub_count_str else None
                        
                        # Parse duration from contentDetails
                        duration_str = content_details.get("duration", "")
                        duration_seconds = parse_iso8601_duration(duration_str)
                        
                        # Determine orientation and get dimensions from thumbnails
                        thumbnails = snippet.get("thumbnails", {})
                        orientation = self.client.determine_orientation(thumbnails)
                        
                        # Get best thumbnail URL and dimensions
                        thumbnail_url = ""
                        thumbnail_width = 0
                        thumbnail_height = 0
                        for quality in ["maxres", "standard", "high", "medium", "default"]:
                            if quality in thumbnails:
                                thumb = thumbnails[quality]
                                thumbnail_url = thumb.get("url", "")
                                thumbnail_width = thumb.get("width", 0)
                                thumbnail_height = thumb.get("height", 0)
                                break
                        
                        videos.append(VideoInfo(
                            video_id=video["id"],
                            title=snippet.get("title", ""),
                            description=snippet.get("description", ""),
                            url=f"https://www.youtube.com/watch?v={video['id']}",
                            view_count=int(statistics.get("viewCount", 0)),
                            channel_id=channel_id,
                            channel_title=snippet.get("channelTitle", ""),
                            subscriber_count=subscriber_count,
                            orientation=orientation,
                            thumbnail_url=thumbnail_url,
                            published_at=snippet.get("publishedAt", ""),
                            duration_seconds=duration_seconds,
                            thumbnail_width=thumbnail_width,
                            thumbnail_height=thumbnail_height,
                        ))
                    except (KeyError, ValueError) as e:
                        errors.append({
                            "type": "video_processing_error",
                            "video_id": video.get("id", "unknown"),
                            "error": str(e),
                        })
            except HttpError as e:
                errors.append({
                    "type": "api_error",
                    "batch_start": i,
                    "error": str(e),
                })

        return videos, errors


class VideoIdAdapter(YouTubeAPIAdapter):
    """
    Adapter for fetching videos by their IDs.
    Used for benchmark mode where user provides video IDs/URLs.
    """

    def __init__(self, client: YouTubeAPIClient):
        self.client = client

    def get_videos(self, video_ids: list[str]) -> tuple[list[VideoInfo], list[dict]]:
        """
        Get video information for specific video IDs.

        Args:
            video_ids: List of video IDs

        Returns:
            Tuple of (list of VideoInfo objects, list of error records)
        """
        videos = []
        errors = []

        # Process in batches of 50
        for i in range(0, len(video_ids), 50):
            batch_ids = video_ids[i:i + 50]
            
            try:
                video_details = self.client.get_video_details(batch_ids)
                
                channel_ids = list(set(
                    v["snippet"]["channelId"] for v in video_details
                ))
                
                channel_details = self.client.get_channel_details(channel_ids)
                
                for video in video_details:
                    try:
                        snippet = video["snippet"]
                        statistics = video.get("statistics", {})
                        content_details = video.get("contentDetails", {})
                        channel_id = snippet["channelId"]
                        channel_info = channel_details.get(channel_id, {})
                        channel_stats = channel_info.get("statistics", {})
                        
                        sub_count_str = channel_stats.get("subscriberCount")
                        subscriber_count = int(sub_count_str) if sub_count_str else None
                        
                        # Parse duration from contentDetails
                        duration_str = content_details.get("duration", "")
                        duration_seconds = parse_iso8601_duration(duration_str)
                        
                        # Determine orientation and get dimensions from thumbnails
                        thumbnails = snippet.get("thumbnails", {})
                        orientation = self.client.determine_orientation(thumbnails)
                        
                        # Get best thumbnail URL and dimensions
                        thumbnail_url = ""
                        thumbnail_width = 0
                        thumbnail_height = 0
                        for quality in ["maxres", "standard", "high", "medium", "default"]:
                            if quality in thumbnails:
                                thumb = thumbnails[quality]
                                thumbnail_url = thumb.get("url", "")
                                thumbnail_width = thumb.get("width", 0)
                                thumbnail_height = thumb.get("height", 0)
                                break
                        
                        videos.append(VideoInfo(
                            video_id=video["id"],
                            title=snippet.get("title", ""),
                            description=snippet.get("description", ""),
                            url=f"https://www.youtube.com/watch?v={video['id']}",
                            view_count=int(statistics.get("viewCount", 0)),
                            channel_id=channel_id,
                            channel_title=snippet.get("channelTitle", ""),
                            subscriber_count=subscriber_count,
                            orientation=orientation,
                            thumbnail_url=thumbnail_url,
                            published_at=snippet.get("publishedAt", ""),
                            duration_seconds=duration_seconds,
                            thumbnail_width=thumbnail_width,
                            thumbnail_height=thumbnail_height,
                        ))
                    except (KeyError, ValueError) as e:
                        errors.append({
                            "type": "video_processing_error",
                            "video_id": video.get("id", "unknown"),
                            "error": str(e),
                        })
            except HttpError as e:
                for vid in batch_ids:
                    errors.append({
                        "type": "api_error",
                        "video_id": vid,
                        "error": str(e),
                    })

        return videos, errors
