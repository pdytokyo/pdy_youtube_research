"""
Audio Downloader using yt-dlp.

Downloads audio from YouTube videos for transcription.
Uses yt-dlp as an external command (not Python package).
"""

import os
import subprocess
import tempfile
import shutil
from dataclasses import dataclass
from typing import Optional, Callable


@dataclass
class DownloadResult:
    """Result of audio download."""
    success: bool
    audio_path: Optional[str] = None
    error_message: Optional[str] = None
    video_id: Optional[str] = None


class AudioDownloader:
    """Downloads audio from YouTube videos using yt-dlp."""

    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize the audio downloader.

        Args:
            output_dir: Directory to save downloaded audio. If None, uses temp directory.
        """
        self.output_dir = output_dir or tempfile.mkdtemp(prefix="yt_audio_")
        os.makedirs(self.output_dir, exist_ok=True)

    @staticmethod
    def check_yt_dlp_installed() -> tuple[bool, str]:
        """
        Check if yt-dlp is installed and accessible.

        Returns:
            Tuple of (is_installed, message)
        """
        try:
            result = subprocess.run(
                ["yt-dlp", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return True, f"yt-dlp version: {result.stdout.strip()}"
            return False, "yt-dlp found but returned error"
        except FileNotFoundError:
            return False, "yt-dlp not found. Install with: brew install yt-dlp (Mac) or pip install yt-dlp"
        except subprocess.TimeoutExpired:
            return False, "yt-dlp check timed out"
        except Exception as e:
            return False, f"Error checking yt-dlp: {str(e)}"

    @staticmethod
    def check_ffmpeg_installed() -> tuple[bool, str]:
        """
        Check if ffmpeg is installed (required for audio extraction).

        Returns:
            Tuple of (is_installed, message)
        """
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                version_line = result.stdout.split('\n')[0]
                return True, version_line
            return False, "ffmpeg found but returned error"
        except FileNotFoundError:
            return False, "ffmpeg not found. Install with: brew install ffmpeg (Mac)"
        except subprocess.TimeoutExpired:
            return False, "ffmpeg check timed out"
        except Exception as e:
            return False, f"Error checking ffmpeg: {str(e)}"

    def download_audio(
        self,
        video_url: str,
        video_id: str,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> DownloadResult:
        """
        Download audio from a YouTube video.

        Args:
            video_url: YouTube video URL
            video_id: Video ID for naming the output file
            progress_callback: Optional callback for progress updates

        Returns:
            DownloadResult with success status and file path or error
        """
        # Check dependencies first
        yt_dlp_ok, yt_dlp_msg = self.check_yt_dlp_installed()
        if not yt_dlp_ok:
            return DownloadResult(
                success=False,
                error_message=yt_dlp_msg,
                video_id=video_id
            )

        ffmpeg_ok, ffmpeg_msg = self.check_ffmpeg_installed()
        if not ffmpeg_ok:
            return DownloadResult(
                success=False,
                error_message=ffmpeg_msg,
                video_id=video_id
            )

        # Prepare output path
        output_template = os.path.join(self.output_dir, f"{video_id}.%(ext)s")
        expected_output = os.path.join(self.output_dir, f"{video_id}.m4a")

        if progress_callback:
            progress_callback("Starting audio download...")

        try:
            # Run yt-dlp to download audio
            cmd = [
                "yt-dlp",
                "-f", "bestaudio",
                "--extract-audio",
                "--audio-format", "m4a",
                "--audio-quality", "0",  # Best quality
                "-o", output_template,
                "--no-playlist",
                "--no-warnings",
                video_url
            ]

            if progress_callback:
                progress_callback(f"Running: {' '.join(cmd[:5])}...")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or "Unknown error"
                # Parse common errors
                if "Video unavailable" in error_msg:
                    error_msg = "Video is unavailable or private"
                elif "Sign in" in error_msg:
                    error_msg = "Video requires sign-in (age-restricted or members-only)"
                elif "copyright" in error_msg.lower():
                    error_msg = "Video blocked due to copyright"
                
                return DownloadResult(
                    success=False,
                    error_message=f"Download failed: {error_msg[:500]}",
                    video_id=video_id
                )

            # Check if file was created
            if os.path.exists(expected_output):
                if progress_callback:
                    progress_callback("Audio download complete!")
                return DownloadResult(
                    success=True,
                    audio_path=expected_output,
                    video_id=video_id
                )
            
            # Try to find the file with different extension
            for ext in ["m4a", "mp3", "opus", "webm", "wav"]:
                alt_path = os.path.join(self.output_dir, f"{video_id}.{ext}")
                if os.path.exists(alt_path):
                    if progress_callback:
                        progress_callback("Audio download complete!")
                    return DownloadResult(
                        success=True,
                        audio_path=alt_path,
                        video_id=video_id
                    )

            return DownloadResult(
                success=False,
                error_message="Download completed but audio file not found",
                video_id=video_id
            )

        except subprocess.TimeoutExpired:
            return DownloadResult(
                success=False,
                error_message="Download timed out (exceeded 5 minutes)",
                video_id=video_id
            )
        except Exception as e:
            return DownloadResult(
                success=False,
                error_message=f"Download error: {str(e)}",
                video_id=video_id
            )

    def cleanup(self, audio_path: Optional[str] = None):
        """
        Clean up downloaded audio files.

        Args:
            audio_path: Specific file to delete, or None to delete all in output_dir
        """
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
        elif self.output_dir and os.path.exists(self.output_dir):
            # Only clean if it's a temp directory we created
            if self.output_dir.startswith(tempfile.gettempdir()):
                shutil.rmtree(self.output_dir, ignore_errors=True)
