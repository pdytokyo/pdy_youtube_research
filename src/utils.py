"""
Utility functions for the YouTube Research Tool.
"""

import re
from typing import Optional
from urllib.parse import urlparse, parse_qs


def extract_video_id(url_or_id: str) -> Optional[str]:
    """
    Extract video ID from a YouTube URL or return the ID if already an ID.

    Supports:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/shorts/VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID
    - Plain video ID

    Args:
        url_or_id: YouTube URL or video ID

    Returns:
        Video ID or None if extraction fails
    """
    url_or_id = url_or_id.strip()

    # If it looks like a plain video ID (11 characters, alphanumeric with - and _)
    if re.match(r"^[a-zA-Z0-9_-]{11}$", url_or_id):
        return url_or_id

    try:
        parsed = urlparse(url_or_id)
        
        # Handle youtu.be short URLs
        if parsed.netloc in ("youtu.be", "www.youtu.be"):
            video_id = parsed.path.lstrip("/")
            if video_id:
                return video_id.split("?")[0]

        # Handle youtube.com URLs
        if parsed.netloc in ("youtube.com", "www.youtube.com", "m.youtube.com"):
            # /watch?v=VIDEO_ID
            if parsed.path == "/watch":
                query_params = parse_qs(parsed.query)
                if "v" in query_params:
                    return query_params["v"][0]
            
            # /shorts/VIDEO_ID or /embed/VIDEO_ID
            path_match = re.match(r"^/(shorts|embed)/([a-zA-Z0-9_-]{11})", parsed.path)
            if path_match:
                return path_match.group(2)

    except Exception:
        pass

    return None


def parse_video_ids_from_input(input_text: str) -> list[str]:
    """
    Parse video IDs from user input.

    Accepts:
    - Comma-separated URLs or IDs
    - Newline-separated URLs or IDs
    - Mixed formats

    Args:
        input_text: User input containing video URLs or IDs

    Returns:
        List of extracted video IDs
    """
    video_ids = []
    
    # Split by newlines and commas
    items = re.split(r"[,\n]+", input_text)
    
    for item in items:
        item = item.strip()
        if not item:
            continue
        
        video_id = extract_video_id(item)
        if video_id:
            video_ids.append(video_id)

    return video_ids


def format_iso_date(date_str: str) -> str:
    """
    Format a date string to ISO 8601 format for YouTube API.

    Args:
        date_str: Date string in various formats (YYYY-MM-DD, etc.)

    Returns:
        ISO 8601 formatted date string (e.g., 2024-01-01T00:00:00Z)
    """
    # If already in ISO format with time, return as-is
    if "T" in date_str:
        return date_str
    
    # Assume YYYY-MM-DD format and add time
    return f"{date_str}T00:00:00Z"


def validate_api_key(api_key: str) -> bool:
    """
    Basic validation of YouTube API key format.

    Args:
        api_key: API key to validate

    Returns:
        True if format looks valid, False otherwise
    """
    # YouTube API keys are typically 39 characters starting with AIza
    if not api_key:
        return False
    
    return len(api_key) >= 30 and api_key.startswith("AIza")
