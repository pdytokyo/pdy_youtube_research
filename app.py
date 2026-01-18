"""
YouTube Research & Script Generation Tool - Streamlit UI

SNSマーケ塾生向けローカルツール:
1. キーワード検索で動画を探す
2. 当たり動画を選択
3. 音声ダウンロード→Whisper文字起こし
4. Beats/セクション構成＋タイムコード＋抽象化台本を生成

Usage:
    streamlit run app.py
"""

import os
import sys
import tempfile
from datetime import datetime
from typing import Optional

import streamlit as st
import pandas as pd
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.youtube_api import YouTubeAPIClient, KeywordSearchAdapter, VideoInfo
from src.pipeline import VideoPipeline
from src.utils import extract_video_id, format_iso_date
from src.audio_downloader import AudioDownloader
from src.transcriber import WhisperTranscriber, TranscriptionResult, save_transcript
from src.outline_generator import OutlineGenerator, Outline, save_outline, format_timecode

load_dotenv()

st.set_page_config(
    page_title="YouTube リサーチ＆台本生成ツール",
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
    """必要な依存関係をチェック"""
    results = {}
    results["yt-dlp"] = AudioDownloader.check_yt_dlp_installed()
    results["ffmpeg"] = AudioDownloader.check_ffmpeg_installed()
    results["whisper"] = WhisperTranscriber.check_whisper_installed()
    
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if api_key:
        results["youtube_api"] = (True, "APIキー設定済み")
    else:
        results["youtube_api"] = (False, "YOUTUBE_API_KEYが.envに未設定")
    
    return results


def show_dependency_status():
    """サイドバーに依存関係の状態を表示"""
    st.sidebar.header("システム状態")
    
    deps = check_dependencies()
    
    for name, (ok, msg) in deps.items():
        if ok:
            st.sidebar.success(f"{name}: OK")
        else:
            st.sidebar.error(f"{name}: {msg}")
    
    missing = [name for name, (ok, _) in deps.items() if not ok]
    if missing:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### インストール方法")
        
        if "yt-dlp" in missing:
            st.sidebar.code("brew install yt-dlp", language="bash")
        if "ffmpeg" in missing:
            st.sidebar.code("brew install ffmpeg", language="bash")
        if "whisper" in missing:
            st.sidebar.code("pip install openai-whisper", language="bash")
        if "youtube_api" in missing:
            st.sidebar.markdown("`.env`ファイルに`YOUTUBE_API_KEY=your_key`を追加")


def search_videos(
    keyword: str,
    max_results: int,
    region_code: Optional[str],
    relevance_language: Optional[str],
    view_multiplier: float,
) -> tuple[list[VideoInfo], list[VideoInfo], list[dict]]:
    """動画を検索してWinnersをフィルタリング"""
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        st.error("YouTube APIキーが設定されていません。.envファイルにYOUTUBE_API_KEYを追加してください。")
        return [], [], []
    
    try:
        client = YouTubeAPIClient(api_key=api_key)
        adapter = KeywordSearchAdapter(client)
        pipeline = VideoPipeline(output_dir="output")
        
        videos, errors = adapter.get_videos(
            keyword=keyword,
            max_results=max_results,
            region_code=region_code if region_code else None,
            relevance_language=relevance_language if relevance_language else None,
        )
        
        winners, unknown, raw = pipeline.filter_videos(videos, view_multiplier=view_multiplier)
        
        return winners, raw, errors
        
    except Exception as e:
        st.error(f"検索に失敗しました: {str(e)}")
        return [], [], [{"error": str(e)}]


def display_video_table(videos: list[VideoInfo], title: str, selectable: bool = False):
    """動画をテーブル形式で表示"""
    if not videos:
        st.info(f"{title}が見つかりませんでした。")
        return None
    
    st.subheader(f"{title} ({len(videos)}件)")
    
    data = []
    for v in videos:
        sub_display = f"{v.subscriber_count:,}" if v.subscriber_count else "不明"
        ratio = v.view_count / v.subscriber_count if v.subscriber_count else 0
        data.append({
            "タイトル": v.title[:50] + "..." if len(v.title) > 50 else v.title,
            "チャンネル": v.channel_title,
            "再生数": f"{v.view_count:,}",
            "登録者数": sub_display,
            "倍率": f"{ratio:.1f}x" if v.subscriber_count else "N/A",
            "向き": v.orientation,
            "video_id": v.video_id,
            "url": v.url,
        })
    
    if selectable:
        selected_idx = st.selectbox(
            "分析する動画を選択:",
            range(len(data)),
            format_func=lambda i: f"{data[i]['タイトル']} ({data[i]['再生数']}再生)",
            key=f"select_{title}"
        )
        
        if selected_idx is not None:
            selected = videos[selected_idx]
            
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**選択中:** [{selected.title}]({selected.url})")
                st.markdown(f"チャンネル: {selected.channel_title} | 再生数: {selected.view_count:,}")
            with col2:
                if st.button("この動画を分析", type="primary"):
                    return selected
    else:
        df = pd.DataFrame(data)
        st.dataframe(
            df[["タイトル", "チャンネル", "再生数", "登録者数", "倍率", "向き"]],
            use_container_width=True,
            hide_index=True,
        )
    
    return None


def analyze_video(video: VideoInfo, whisper_model: str = "base"):
    """動画の完全分析パイプラインを実行"""
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
        "output_folder": os.path.join(output_dir, video_id),
    }
    
    progress_container = st.container()
    step_display = progress_container.empty()
    status_text = progress_container.empty()
    progress_bar = progress_container.progress(0)
    
    def update_status(step: int, msg: str, progress: float = None):
        steps_ja = ["1. 音声ダウンロード", "2. ffmpeg処理", "3. Whisper文字起こし", "4. 構成生成"]
        step_html = " → ".join([f"**{s}**" if i == step - 1 else s for i, s in enumerate(steps_ja)])
        step_display.markdown(f"進捗: {step_html}")
        status_text.markdown(f"**状態:** {msg}")
        if progress is not None:
            progress_bar.progress(progress)
        results["steps"].append({"step": step, "message": msg, "time": datetime.now().isoformat()})
    
    try:
        update_status(1, "音声をダウンロード中...", 0.05)
        
        downloader = AudioDownloader(output_dir=tempfile.mkdtemp(prefix="yt_audio_"))
        download_result = downloader.download_audio(
            video_url=video_url,
            video_id=video_id,
            progress_callback=lambda msg: update_status(1, f"ダウンロード: {msg}", None)
        )
        
        if not download_result.success:
            results["status"] = "failed"
            results["error"] = download_result.error_message
            update_status(1, f"ダウンロード失敗: {download_result.error_message}", 0.25)
            return results
        
        audio_path = download_result.audio_path
        update_status(2, f"音声取得完了: {os.path.basename(audio_path)}", 0.25)
        
        update_status(3, f"Whisperモデル読み込み中 ({whisper_model})...", 0.30)
        
        transcriber = WhisperTranscriber(model_name=whisper_model)
        transcription = transcriber.transcribe(
            audio_path=audio_path,
            video_id=video_id,
            progress_callback=lambda msg: update_status(3, f"文字起こし: {msg}", None)
        )
        
        if not transcription.success:
            results["status"] = "failed"
            results["error"] = transcription.error_message
            update_status(3, f"文字起こし失敗: {transcription.error_message}", 0.75)
            downloader.cleanup(audio_path)
            return results
        
        update_status(3, f"{len(transcription.segments)}セグメント文字起こし完了 ({transcription.duration:.1f}秒)", 0.75)
        
        transcript_files = save_transcript(transcription, output_dir, video_id, timestamp)
        results["files"]["transcript"] = transcript_files
        
        update_status(4, "Beats/セクション構成を生成中...", 0.85)
        
        generator = OutlineGenerator()
        outline = generator.generate(
            segments=transcription.segments,
            video_id=video_id,
        )
        
        outline_files = save_outline(outline, output_dir, video_id, timestamp)
        results["files"]["outline"] = outline_files
        
        update_status(4, "分析完了!", 1.0)
        
        downloader.cleanup(audio_path)
        
        results["status"] = "success"
        results["transcription"] = transcription
        results["outline"] = outline
        
        return results
        
    except Exception as e:
        results["status"] = "failed"
        results["error"] = str(e)
        update_status(4, f"エラー: {str(e)}", None)
        return results


def display_transcript_section(transcription: TranscriptionResult, files: dict):
    """文字起こし結果を表示（全文、セグメント、ダウンロードボタン）"""
    st.subheader("文字起こし結果")
    
    tab_full, tab_segments = st.tabs(["全文", "セグメント一覧（タイムコード付き）"])
    
    with tab_full:
        st.text_area("文字起こし全文", transcription.full_text, height=300)
    
    with tab_segments:
        segments_data = []
        for seg in transcription.segments:
            start_tc = format_timecode(seg["start"])
            end_tc = format_timecode(seg["end"])
            segments_data.append({
                "開始": start_tc,
                "終了": end_tc,
                "テキスト": seg["text"].strip(),
            })
        df = pd.DataFrame(segments_data)
        st.dataframe(df, use_container_width=True, hide_index=True, height=400)
    
    st.markdown("**ダウンロード:**")
    col1, col2, col3 = st.columns(3)
    
    transcript_files = files.get("transcript", {})
    
    with col1:
        txt_path = transcript_files.get("txt", "")
        if txt_path and os.path.exists(txt_path):
            with open(txt_path, "r", encoding="utf-8") as f:
                st.download_button("transcript.txt", f.read(), file_name="transcript.txt", mime="text/plain")
    
    with col2:
        srt_path = transcript_files.get("srt", "")
        if srt_path and os.path.exists(srt_path):
            with open(srt_path, "r", encoding="utf-8") as f:
                st.download_button("transcript.srt", f.read(), file_name="transcript.srt", mime="text/plain")
    
    with col3:
        json_path = transcript_files.get("json", "")
        if json_path and os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                st.download_button("transcript.json", f.read(), file_name="transcript.json", mime="application/json")


def display_outline_section(outline: Outline, files: dict):
    """構成結果を表示（Beats、セクション、変数）"""
    st.subheader("構成分析結果")
    
    tab_beats, tab_sections, tab_vars = st.tabs(["Beats一覧", "セクション構成", "変数一覧"])
    
    with tab_beats:
        st.markdown(f"**全{len(outline.all_beats)}個のBeats（15〜30秒単位）**")
        beats_data = []
        for beat in outline.all_beats:
            beats_data.append({
                "ID": beat.id,
                "開始": beat.timecode_start,
                "終了": beat.timecode_end,
                "要約": beat.summary,
                "テンプレート": beat.template[:80] + "..." if len(beat.template) > 80 else beat.template,
            })
        df = pd.DataFrame(beats_data)
        st.dataframe(df, use_container_width=True, hide_index=True, height=400)
        
        with st.expander("Beats詳細（全文）"):
            for beat in outline.all_beats:
                st.markdown(f"**[{beat.timecode_start}〜{beat.timecode_end}] Beat {beat.id}**")
                st.markdown(f"要約: {beat.summary}")
                st.code(beat.template, language=None)
                if beat.variables:
                    st.markdown(f"変数: {', '.join([f'`{v}`' for v in beat.variables])}")
                st.markdown("---")
    
    with tab_sections:
        st.markdown(f"**全{len(outline.sections)}個のセクション**")
        for section in outline.sections:
            beat_count = len(section.beats) if section.beats else 0
            with st.expander(f"[{section.timecode_start}] {section.name} ({section.section_type.value.upper()}) - {beat_count}Beats"):
                st.markdown(f"**時間:** {section.timecode_start} 〜 {section.timecode_end} ({section.duration:.1f}秒)")
                st.markdown(f"**要約:** {section.summary}")
                st.markdown("**テンプレート:**")
                st.code(section.template, language=None)
                if section.beats:
                    st.markdown(f"**含まれるBeats:** {', '.join([f'Beat{b.id}' for b in section.beats])}")
                if section.variables:
                    st.markdown("**変数:**")
                    for var in section.variables:
                        st.markdown(f"- `{var.name}`: {var.original_value} ({var.category})")
    
    with tab_vars:
        if outline.all_variables:
            st.markdown(f"**全{len(outline.all_variables)}個の変数（差し替えポイント）**")
            var_data = [
                {"変数名": v.name, "カテゴリ": v.category, "元の値": v.original_value}
                for v in outline.all_variables
            ]
            st.dataframe(pd.DataFrame(var_data), use_container_width=True, hide_index=True)
        else:
            st.info("変数が検出されませんでした。")
    
    st.markdown("**ダウンロード:**")
    col1, col2 = st.columns(2)
    
    outline_files = files.get("outline", {})
    
    with col1:
        md_path = outline_files.get("md", "")
        if md_path and os.path.exists(md_path):
            with open(md_path, "r", encoding="utf-8") as f:
                st.download_button("outline.md", f.read(), file_name="outline.md", mime="text/markdown")
    
    with col2:
        json_path = outline_files.get("json", "")
        if json_path and os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                st.download_button("outline.json", f.read(), file_name="outline.json", mime="application/json")


def display_analysis_results(results: dict):
    """分析結果を表示"""
    if results["status"] == "failed":
        st.error(f"分析に失敗しました: {results.get('error', '不明なエラー')}")
        
        error = results.get("error", "").lower()
        st.markdown("### トラブルシューティング")
        if "yt-dlp" in error or "download" in error:
            st.markdown("- yt-dlpがインストールされているか確認: `brew install yt-dlp`")
            st.markdown("- 動画が公開されているか、非公開でないか確認")
        elif "ffmpeg" in error:
            st.markdown("- ffmpegがインストールされているか確認: `brew install ffmpeg`")
        elif "whisper" in error or "model" in error:
            st.markdown("- Whisperがインストールされているか確認: `pip install openai-whisper`")
            st.markdown("- メモリ不足の場合は小さいモデル（tiny/base）を試す")
        return
    
    st.success("分析が完了しました!")
    
    output_folder = results.get("output_folder", "")
    if output_folder:
        st.info(f"出力フォルダ: `{output_folder}`")
    
    files = results.get("files", {})
    transcription = results.get("transcription")
    outline = results.get("outline")
    
    if transcription:
        display_transcript_section(transcription, files)
    
    st.markdown("---")
    
    if outline:
        display_outline_section(outline, files)
    
    with st.expander("Markdown全文を表示"):
        if outline:
            st.markdown(outline.to_markdown())


def main():
    """メインStreamlitアプリ"""
    st.title("YouTube リサーチ＆台本生成ツール")
    st.markdown("動画を検索し、当たり動画を分析して、抽象化された台本構成を生成します。")
    
    show_dependency_status()
    
    st.sidebar.markdown("---")
    st.sidebar.header("設定")
    whisper_model = st.sidebar.selectbox(
        "Whisperモデル",
        ["tiny", "base", "small", "medium", "large"],
        index=1,
        help="大きいモデルほど精度が高いですが、処理が遅くメモリを多く使用します"
    )
    
    tab1, tab2, tab3 = st.tabs(["キーワード検索", "動画分析", "URL直接入力"])
    
    with tab1:
        st.header("YouTube動画を検索")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            keyword = st.text_input("検索キーワード", placeholder="例: SNSマーケティング")
        
        with col2:
            max_results = st.number_input("最大件数", min_value=10, max_value=500, value=50)
        
        col3, col4, col5 = st.columns(3)
        
        with col3:
            region_code = st.text_input("地域コード（任意）", placeholder="例: JP, US")
        
        with col4:
            relevance_language = st.text_input("言語（任意）", placeholder="例: ja, en")
        
        with col5:
            view_multiplier = st.number_input("再生数倍率", min_value=1.0, max_value=20.0, value=5.0)
        
        if st.button("検索", type="primary"):
            if not keyword:
                st.warning("検索キーワードを入力してください。")
            else:
                with st.spinner("検索中..."):
                    winners, raw, errors = search_videos(
                        keyword=keyword,
                        max_results=max_results,
                        region_code=region_code,
                        relevance_language=relevance_language,
                        view_multiplier=view_multiplier,
                    )
                    st.session_state.winners = winners
                    st.session_state.search_results = raw
        
        if st.session_state.winners:
            selected = display_video_table(st.session_state.winners, "当たり動画", selectable=True)
            if selected:
                st.session_state.selected_video = selected
                st.session_state.analysis_status = "ready"
                st.rerun()
        
        if st.session_state.search_results:
            with st.expander(f"全結果を表示 ({len(st.session_state.search_results)}件)"):
                display_video_table(st.session_state.search_results, "全結果", selectable=False)
    
    with tab2:
        st.header("選択した動画を分析")
        
        if st.session_state.selected_video:
            video = st.session_state.selected_video
            
            st.markdown(f"**選択中の動画:** [{video.title}]({video.url})")
            st.markdown(f"チャンネル: {video.channel_title} | 再生数: {video.view_count:,}")
            
            col1, col2 = st.columns([1, 3])
            with col1:
                if st.button("分析開始", type="primary"):
                    st.session_state.analysis_status = "running"
                    st.session_state.analysis_results = None
            
            if st.session_state.analysis_status == "running":
                results = analyze_video(video, whisper_model=whisper_model)
                st.session_state.analysis_results = results
                st.session_state.analysis_status = "complete"
            
            if st.session_state.analysis_results:
                display_analysis_results(st.session_state.analysis_results)
        else:
            st.info("動画が選択されていません。「キーワード検索」タブで動画を検索・選択するか、「URL直接入力」タブを使用してください。")
    
    with tab3:
        st.header("URLから分析")
        
        video_url = st.text_input("YouTube動画URL", placeholder="https://www.youtube.com/watch?v=...")
        
        if st.button("URLを分析", type="primary"):
            if not video_url:
                st.warning("YouTube URLを入力してください。")
            else:
                video_id = extract_video_id(video_url)
                if not video_id:
                    st.error("無効なYouTube URLです。URLを確認してください。")
                else:
                    video = VideoInfo(
                        video_id=video_id,
                        title=f"動画 {video_id}",
                        description="",
                        url=f"https://www.youtube.com/watch?v={video_id}",
                        view_count=0,
                        channel_id="",
                        channel_title="不明",
                        subscriber_count=None,
                        orientation="unknown",
                        thumbnail_url="",
                        published_at="",
                    )
                    
                    results = analyze_video(video, whisper_model=whisper_model)
                    display_analysis_results(results)


if __name__ == "__main__":
    main()
