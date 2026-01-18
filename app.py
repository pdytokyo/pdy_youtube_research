"""
YouTube Research & Script Generation Tool - Streamlit UI

A local tool for SNS marketing students to:
1. Search YouTube videos by keyword
2. Select "winner" videos for analysis
3. Download audio and transcribe with Whisper
4. Generate abstracted script outlines with timecodes

Usage:
    streamlit run app.py
"""

import os
import sys
import tempfile
from datetime import datetime
from typing import Optional

import streamlit as st
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.youtube_api import YouTubeAPIClient, KeywordSearchAdapter, VideoInfo
from src.pipeline import VideoPipeline
from src.utils import extract_video_id, format_iso_date
from src.audio_downloader import AudioDownloader
from src.transcriber import WhisperTranscriber, save_transcript
from src.outline_generator import OutlineGenerator, save_outline

# Load environment variables
load_dotenv()

# Page config
st.set_page_config(
    page_title="YouTube Research Tool",
    page_icon="🎬",
    layout="wide",
)

# Initialize session state
if "search_results" not in st.session_state:
    st.session_state.search_results = None
if "winners" not in st.session_state:
    st.session_state.winners = []
if "selected_video" not in st.session_state:
    st.session_state.selected_video = None
if "analysis_status" not in st.session_state:
    st.session_state.analysis_status = None
if "analysis_results" not in st.session_state:
    st.session_state.analysis_results = None


def check_dependencies() -> dict[str, tuple[bool, str]]:
    """Check all required dependencies."""
    results = {}
    
    # Check yt-dlp
    results["yt-dlp"] = AudioDownloader.check_yt_dlp_installed()
    
    # Check ffmpeg
    results["ffmpeg"] = AudioDownloader.check_ffmpeg_installed()
    
    # Check Whisper
    results["whisper"] = WhisperTranscriber.check_whisper_installed()
    
    # Check YouTube API key
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if api_key:
        results["youtube_api"] = (True, "API key configured")
    else:
        results["youtube_api"] = (False, "YOUTUBE_API_KEY not set in .env file")
    
    return results


def show_dependency_status():
    """Show dependency status in sidebar."""
    st.sidebar.header("System Status")
    
    deps = check_dependencies()
    
    for name, (ok, msg) in deps.items():
        if ok:
            st.sidebar.success(f"{name}: OK")
        else:
            st.sidebar.error(f"{name}: {msg}")
    
    # Show installation instructions if needed
    missing = [name for name, (ok, _) in deps.items() if not ok]
    if missing:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### Installation Help")
        
        if "yt-dlp" in missing:
            st.sidebar.code("brew install yt-dlp", language="bash")
        if "ffmpeg" in missing:
            st.sidebar.code("brew install ffmpeg", language="bash")
        if "whisper" in missing:
            st.sidebar.code("pip install openai-whisper", language="bash")
        if "youtube_api" in missing:
            st.sidebar.markdown("Add `YOUTUBE_API_KEY=your_key` to `.env` file")


def search_videos(
    keyword: str,
    max_results: int,
    region_code: Optional[str],
    relevance_language: Optional[str],
    view_multiplier: float,
) -> tuple[list[VideoInfo], list[VideoInfo], list[dict]]:
    """Search for videos and filter winners."""
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        st.error("YouTube API key not configured. Add YOUTUBE_API_KEY to .env file.")
        return [], [], []
    
    try:
        client = YouTubeAPIClient(api_key=api_key)
        adapter = KeywordSearchAdapter(client)
        pipeline = VideoPipeline(output_dir="output")
        
        # Search
        videos, errors = adapter.get_videos(
            keyword=keyword,
            max_results=max_results,
            region_code=region_code if region_code else None,
            relevance_language=relevance_language if relevance_language else None,
        )
        
        # Filter
        winners, unknown, raw = pipeline.filter_videos(videos, view_multiplier=view_multiplier)
        
        return winners, raw, errors
        
    except Exception as e:
        st.error(f"Search failed: {str(e)}")
        return [], [], [{"error": str(e)}]


def display_video_table(videos: list[VideoInfo], title: str, selectable: bool = False):
    """Display videos in a table format."""
    if not videos:
        st.info(f"No {title.lower()} found.")
        return None
    
    st.subheader(f"{title} ({len(videos)} videos)")
    
    # Create dataframe-like display
    data = []
    for v in videos:
        sub_display = f"{v.subscriber_count:,}" if v.subscriber_count else "Unknown"
        ratio = v.view_count / v.subscriber_count if v.subscriber_count else 0
        data.append({
            "Title": v.title[:50] + "..." if len(v.title) > 50 else v.title,
            "Channel": v.channel_title,
            "Views": f"{v.view_count:,}",
            "Subscribers": sub_display,
            "Ratio": f"{ratio:.1f}x" if v.subscriber_count else "N/A",
            "Orientation": v.orientation,
            "video_id": v.video_id,
            "url": v.url,
        })
    
    if selectable:
        # Show as selectable list
        selected_idx = st.selectbox(
            "Select a video to analyze:",
            range(len(data)),
            format_func=lambda i: f"{data[i]['Title']} ({data[i]['Views']} views)",
            key=f"select_{title}"
        )
        
        if selected_idx is not None:
            selected = videos[selected_idx]
            
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**Selected:** [{selected.title}]({selected.url})")
                st.markdown(f"Channel: {selected.channel_title} | Views: {selected.view_count:,}")
            with col2:
                if st.button("Analyze This Video", type="primary"):
                    return selected
    else:
        # Show as table
        import pandas as pd
        df = pd.DataFrame(data)
        st.dataframe(
            df[["Title", "Channel", "Views", "Subscribers", "Ratio", "Orientation"]],
            use_container_width=True,
            hide_index=True,
        )
    
    return None


def analyze_video(video: VideoInfo, whisper_model: str = "base"):
    """Run full analysis pipeline on a video."""
    video_id = video.video_id
    video_url = video.url
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    
    results = {
        "video_id": video_id,
        "video_title": video.title,
        "status": "in_progress",
        "steps": [],
        "files": {},
    }
    
    # Progress container
    progress_container = st.container()
    status_text = progress_container.empty()
    progress_bar = progress_container.progress(0)
    
    def update_status(msg: str, progress: float = None):
        status_text.markdown(f"**Status:** {msg}")
        if progress is not None:
            progress_bar.progress(progress)
        results["steps"].append({"message": msg, "time": datetime.now().isoformat()})
    
    try:
        # Step 1: Download audio (25%)
        update_status("Downloading audio...", 0.05)
        
        downloader = AudioDownloader(output_dir=tempfile.mkdtemp(prefix="yt_audio_"))
        download_result = downloader.download_audio(
            video_url=video_url,
            video_id=video_id,
            progress_callback=lambda msg: update_status(f"Download: {msg}", None)
        )
        
        if not download_result.success:
            results["status"] = "failed"
            results["error"] = download_result.error_message
            update_status(f"Download failed: {download_result.error_message}", 0.25)
            return results
        
        audio_path = download_result.audio_path
        update_status(f"Audio downloaded: {os.path.basename(audio_path)}", 0.25)
        
        # Step 2: Transcribe with Whisper (75%)
        update_status(f"Loading Whisper model ({whisper_model})...", 0.30)
        
        transcriber = WhisperTranscriber(model_name=whisper_model)
        transcription = transcriber.transcribe(
            audio_path=audio_path,
            video_id=video_id,
            progress_callback=lambda msg: update_status(f"Transcription: {msg}", None)
        )
        
        if not transcription.success:
            results["status"] = "failed"
            results["error"] = transcription.error_message
            update_status(f"Transcription failed: {transcription.error_message}", 0.75)
            # Clean up audio
            downloader.cleanup(audio_path)
            return results
        
        update_status(f"Transcribed {len(transcription.segments)} segments ({transcription.duration:.1f}s)", 0.75)
        
        # Save transcript files
        transcript_files = save_transcript(transcription, output_dir, video_id, timestamp)
        results["files"]["transcript"] = transcript_files
        
        # Step 3: Generate outline (100%)
        update_status("Generating outline with timecodes...", 0.85)
        
        generator = OutlineGenerator()
        outline = generator.generate(
            segments=transcription.segments,
            video_id=video_id,
        )
        
        # Save outline files
        outline_files = save_outline(outline, output_dir, video_id, timestamp)
        results["files"]["outline"] = outline_files
        
        update_status("Analysis complete!", 1.0)
        
        # Clean up audio file
        downloader.cleanup(audio_path)
        
        results["status"] = "success"
        results["transcription"] = transcription
        results["outline"] = outline
        
        return results
        
    except Exception as e:
        results["status"] = "failed"
        results["error"] = str(e)
        update_status(f"Error: {str(e)}", None)
        return results


def display_analysis_results(results: dict):
    """Display analysis results."""
    if results["status"] == "failed":
        st.error(f"Analysis failed: {results.get('error', 'Unknown error')}")
        
        # Show troubleshooting tips
        error = results.get("error", "").lower()
        st.markdown("### Troubleshooting")
        if "yt-dlp" in error or "download" in error:
            st.markdown("- Ensure yt-dlp is installed: `brew install yt-dlp`")
            st.markdown("- Check if the video is available and not private")
        elif "ffmpeg" in error:
            st.markdown("- Ensure ffmpeg is installed: `brew install ffmpeg`")
        elif "whisper" in error or "model" in error:
            st.markdown("- Ensure Whisper is installed: `pip install openai-whisper`")
            st.markdown("- Try a smaller model (tiny or base) if running out of memory")
        return
    
    st.success("Analysis completed successfully!")
    
    # Show generated files
    st.subheader("Generated Files")
    
    files = results.get("files", {})
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Transcript Files:**")
        if "transcript" in files:
            for fmt, path in files["transcript"].items():
                st.markdown(f"- `{path}`")
    
    with col2:
        st.markdown("**Outline Files:**")
        if "outline" in files:
            for fmt, path in files["outline"].items():
                st.markdown(f"- `{path}`")
    
    # Show outline preview
    outline = results.get("outline")
    if outline:
        st.subheader("Outline Preview")
        
        # Show sections with timecodes
        for i, section in enumerate(outline.sections, 1):
            with st.expander(f"[{section.timecode_start}] {section.name} ({section.section_type.value.upper()})"):
                st.markdown(f"**Duration:** {section.timecode_start} - {section.timecode_end} ({section.duration:.1f}s)")
                st.markdown("**Summary:**")
                st.markdown(f"> {section.summary}")
                st.markdown("**Abstracted Template:**")
                st.code(section.template, language=None)
                if section.variables:
                    st.markdown("**Variables:**")
                    for var in section.variables:
                        st.markdown(f"- `{var.name}`: {var.original_value} ({var.category})")
        
        # Show all variables
        if outline.all_variables:
            st.subheader("All Variables (Replacement Points)")
            var_data = [
                {"Variable": v.name, "Category": v.category, "Original": v.original_value}
                for v in outline.all_variables
            ]
            import pandas as pd
            st.dataframe(pd.DataFrame(var_data), use_container_width=True, hide_index=True)
    
    # Show full markdown
    if outline:
        with st.expander("View Full Markdown Output"):
            st.markdown(outline.to_markdown())


def main():
    """Main Streamlit app."""
    st.title("YouTube Research & Script Generation Tool")
    st.markdown("Search for videos, analyze winners, and generate abstracted script outlines.")
    
    # Sidebar - dependency status
    show_dependency_status()
    
    # Sidebar - Whisper model selection
    st.sidebar.markdown("---")
    st.sidebar.header("Settings")
    whisper_model = st.sidebar.selectbox(
        "Whisper Model",
        ["tiny", "base", "small", "medium", "large"],
        index=1,  # Default to "base"
        help="Larger models are more accurate but slower and use more memory"
    )
    
    # Main content - tabs
    tab1, tab2, tab3 = st.tabs(["Keyword Search", "Analyze Video", "Direct URL"])
    
    # Tab 1: Keyword Search
    with tab1:
        st.header("Search YouTube Videos")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            keyword = st.text_input("Search Keyword", placeholder="e.g., Python tutorial")
        
        with col2:
            max_results = st.number_input("Max Results", min_value=10, max_value=500, value=50)
        
        col3, col4, col5 = st.columns(3)
        
        with col3:
            region_code = st.text_input("Region Code (optional)", placeholder="e.g., JP, US")
        
        with col4:
            relevance_language = st.text_input("Language (optional)", placeholder="e.g., ja, en")
        
        with col5:
            view_multiplier = st.number_input("View Multiplier", min_value=1.0, max_value=20.0, value=5.0)
        
        if st.button("Search", type="primary"):
            if not keyword:
                st.warning("Please enter a search keyword.")
            else:
                with st.spinner("Searching..."):
                    winners, raw, errors = search_videos(
                        keyword=keyword,
                        max_results=max_results,
                        region_code=region_code,
                        relevance_language=relevance_language,
                        view_multiplier=view_multiplier,
                    )
                    st.session_state.winners = winners
                    st.session_state.search_results = raw
        
        # Display results
        if st.session_state.winners:
            selected = display_video_table(st.session_state.winners, "Winners", selectable=True)
            if selected:
                st.session_state.selected_video = selected
                st.session_state.analysis_status = "ready"
                st.rerun()
        
        if st.session_state.search_results:
            with st.expander(f"View All Results ({len(st.session_state.search_results)} videos)"):
                display_video_table(st.session_state.search_results, "All Results", selectable=False)
    
    # Tab 2: Analyze Selected Video
    with tab2:
        st.header("Analyze Selected Video")
        
        if st.session_state.selected_video:
            video = st.session_state.selected_video
            
            st.markdown(f"**Selected Video:** [{video.title}]({video.url})")
            st.markdown(f"Channel: {video.channel_title} | Views: {video.view_count:,}")
            
            col1, col2 = st.columns([1, 3])
            with col1:
                if st.button("Start Analysis", type="primary"):
                    st.session_state.analysis_status = "running"
                    st.session_state.analysis_results = None
            
            if st.session_state.analysis_status == "running":
                results = analyze_video(video, whisper_model=whisper_model)
                st.session_state.analysis_results = results
                st.session_state.analysis_status = "complete"
            
            if st.session_state.analysis_results:
                display_analysis_results(st.session_state.analysis_results)
        else:
            st.info("No video selected. Use the Keyword Search tab to find and select a video, or use the Direct URL tab.")
    
    # Tab 3: Direct URL
    with tab3:
        st.header("Analyze by URL")
        
        video_url = st.text_input("YouTube Video URL", placeholder="https://www.youtube.com/watch?v=...")
        
        if st.button("Analyze URL", type="primary"):
            if not video_url:
                st.warning("Please enter a YouTube URL.")
            else:
                video_id = extract_video_id(video_url)
                if not video_id:
                    st.error("Invalid YouTube URL. Please check the URL and try again.")
                else:
                    # Create a minimal VideoInfo for analysis
                    video = VideoInfo(
                        video_id=video_id,
                        title=f"Video {video_id}",
                        description="",
                        url=f"https://www.youtube.com/watch?v={video_id}",
                        view_count=0,
                        channel_id="",
                        channel_title="Unknown",
                        subscriber_count=None,
                        orientation="unknown",
                        thumbnail_url="",
                        published_at="",
                    )
                    
                    results = analyze_video(video, whisper_model=whisper_model)
                    display_analysis_results(results)


if __name__ == "__main__":
    main()
