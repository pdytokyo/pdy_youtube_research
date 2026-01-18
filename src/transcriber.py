"""
Whisper Transcription Module.

Transcribes audio files using OpenAI Whisper with segment timestamps.
Supports long-form audio with proper segment handling.
"""

import os
import json
from dataclasses import dataclass, field, asdict
from typing import Optional, Callable
from datetime import datetime


@dataclass
class TranscriptSegment:
    """A segment of transcribed text with timestamps."""
    id: int
    start: float  # Start time in seconds
    end: float    # End time in seconds
    text: str

    def to_srt_entry(self) -> str:
        """Convert segment to SRT format entry."""
        def format_time(seconds: float) -> str:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            millis = int((seconds % 1) * 1000)
            return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
        
        return f"{self.id}\n{format_time(self.start)} --> {format_time(self.end)}\n{self.text}\n"


@dataclass
class TranscriptionResult:
    """Result of audio transcription."""
    success: bool
    segments: list[TranscriptSegment] = field(default_factory=list)
    full_text: str = ""
    language: str = ""
    duration: float = 0.0
    error_message: Optional[str] = None
    video_id: Optional[str] = None


class WhisperTranscriber:
    """Transcribes audio using OpenAI Whisper."""

    def __init__(self, model_name: str = "base"):
        """
        Initialize the transcriber.

        Args:
            model_name: Whisper model to use (tiny, base, small, medium, large)
        """
        self.model_name = model_name
        self.model = None
        self._whisper_available = None

    @staticmethod
    def check_whisper_installed() -> tuple[bool, str]:
        """
        Check if Whisper is installed and accessible.

        Returns:
            Tuple of (is_installed, message)
        """
        try:
            import whisper
            return True, f"Whisper installed (version available)"
        except ImportError:
            return False, "Whisper not installed. Install with: pip install openai-whisper"
        except Exception as e:
            return False, f"Error checking Whisper: {str(e)}"

    def load_model(self, progress_callback: Optional[Callable[[str], None]] = None) -> tuple[bool, str]:
        """
        Load the Whisper model.

        Args:
            progress_callback: Optional callback for progress updates

        Returns:
            Tuple of (success, message)
        """
        if self.model is not None:
            return True, "Model already loaded"

        try:
            import whisper
            
            if progress_callback:
                progress_callback(f"Loading Whisper model '{self.model_name}'... (this may take a moment)")
            
            self.model = whisper.load_model(self.model_name)
            
            if progress_callback:
                progress_callback(f"Whisper model '{self.model_name}' loaded successfully")
            
            return True, f"Model '{self.model_name}' loaded"
        except ImportError:
            return False, "Whisper not installed. Install with: pip install openai-whisper"
        except Exception as e:
            error_msg = str(e)
            if "CUDA" in error_msg or "GPU" in error_msg:
                return False, f"GPU error (will use CPU): {error_msg}"
            return False, f"Failed to load model: {error_msg}"

    def transcribe(
        self,
        audio_path: str,
        video_id: Optional[str] = None,
        language: Optional[str] = None,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> TranscriptionResult:
        """
        Transcribe an audio file.

        Args:
            audio_path: Path to the audio file
            video_id: Optional video ID for reference
            language: Optional language code (e.g., 'ja', 'en'). Auto-detect if None.
            progress_callback: Optional callback for progress updates

        Returns:
            TranscriptionResult with segments and full text
        """
        # Check if file exists
        if not os.path.exists(audio_path):
            return TranscriptionResult(
                success=False,
                error_message=f"Audio file not found: {audio_path}",
                video_id=video_id
            )

        # Load model if not loaded
        if self.model is None:
            success, msg = self.load_model(progress_callback)
            if not success:
                return TranscriptionResult(
                    success=False,
                    error_message=msg,
                    video_id=video_id
                )

        try:
            import whisper
            
            if progress_callback:
                progress_callback("Starting transcription... (this may take several minutes for long videos)")

            # Transcribe with word timestamps
            transcribe_options = {
                "verbose": False,
                "word_timestamps": False,  # Segment-level is enough for our use case
            }
            
            if language:
                transcribe_options["language"] = language

            result = self.model.transcribe(audio_path, **transcribe_options)

            if progress_callback:
                progress_callback("Processing transcription results...")

            # Extract segments
            segments = []
            for i, seg in enumerate(result.get("segments", [])):
                segments.append(TranscriptSegment(
                    id=i + 1,
                    start=seg["start"],
                    end=seg["end"],
                    text=seg["text"].strip()
                ))

            # Calculate duration from last segment
            duration = segments[-1].end if segments else 0.0

            if progress_callback:
                progress_callback(f"Transcription complete! {len(segments)} segments, {duration:.1f}s duration")

            return TranscriptionResult(
                success=True,
                segments=segments,
                full_text=result.get("text", "").strip(),
                language=result.get("language", ""),
                duration=duration,
                video_id=video_id
            )

        except Exception as e:
            error_msg = str(e)
            
            # Parse common errors
            if "ffmpeg" in error_msg.lower():
                error_msg = "ffmpeg error - ensure ffmpeg is installed: brew install ffmpeg"
            elif "memory" in error_msg.lower():
                error_msg = f"Out of memory - try a smaller model (current: {self.model_name})"
            elif "cuda" in error_msg.lower() or "gpu" in error_msg.lower():
                error_msg = f"GPU error - will retry with CPU: {error_msg}"
            
            return TranscriptionResult(
                success=False,
                error_message=f"Transcription failed: {error_msg}",
                video_id=video_id
            )


def save_transcript(
    result: TranscriptionResult,
    output_dir: str,
    video_id: str,
    timestamp: Optional[str] = None,
) -> dict[str, str]:
    """
    Save transcription results to files.

    Args:
        result: TranscriptionResult to save
        output_dir: Directory to save files
        video_id: Video ID for filename
        timestamp: Optional timestamp for filename

    Returns:
        Dictionary mapping format to file path
    """
    os.makedirs(output_dir, exist_ok=True)
    
    ts = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"transcript_{video_id}_{ts}"
    
    output_files = {}

    # Save JSON with segments
    json_path = os.path.join(output_dir, f"{base_name}.json")
    json_data = {
        "video_id": video_id,
        "language": result.language,
        "duration": result.duration,
        "segment_count": len(result.segments),
        "full_text": result.full_text,
        "segments": [asdict(seg) for seg in result.segments]
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    output_files["json"] = json_path

    # Save plain text
    txt_path = os.path.join(output_dir, f"{base_name}.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(result.full_text)
    output_files["txt"] = txt_path

    # Save SRT
    srt_path = os.path.join(output_dir, f"{base_name}.srt")
    with open(srt_path, "w", encoding="utf-8") as f:
        for seg in result.segments:
            f.write(seg.to_srt_entry() + "\n")
    output_files["srt"] = srt_path

    return output_files
