"""
Tests for Outline Generator.

These tests verify outline generation from transcript segments
without requiring external API calls or Whisper.
"""

import os
import json
import tempfile
import pytest

from src.outline_generator import (
    OutlineGenerator,
    OutlineSection,
    Outline,
    Variable,
    Beat,
    SectionType,
    save_outline,
    format_timecode,
)
from src.transcriber import TranscriptSegment


class TestOutlineGenerator:
    """Tests for OutlineGenerator class."""

    def test_init(self):
        """Test generator initialization."""
        generator = OutlineGenerator()
        assert generator.variables == []
        assert generator.variable_counter == {}

    def test_detect_section_type_hook(self):
        """Test hook section detection."""
        generator = OutlineGenerator()
        text = "皆さん、こんにちは！今日は特別なお話があります。"
        section_type = generator._detect_section_type(text)
        assert section_type == SectionType.HOOK

    def test_detect_section_type_problem(self):
        """Test problem section detection."""
        generator = OutlineGenerator()
        text = "多くの人が困っている問題があります。"
        section_type = generator._detect_section_type(text)
        assert section_type == SectionType.PROBLEM

    def test_detect_section_type_claim(self):
        """Test claim section detection."""
        generator = OutlineGenerator()
        text = "秘密のコツをお伝えします。ポイントは3つあります。"
        section_type = generator._detect_section_type(text)
        assert section_type == SectionType.CLAIM

    def test_detect_section_type_example(self):
        """Test example section detection."""
        generator = OutlineGenerator()
        text = "例えば、私の場合はこうしました。"
        section_type = generator._detect_section_type(text)
        assert section_type == SectionType.EXAMPLE

    def test_detect_section_type_cta(self):
        """Test CTA section detection."""
        generator = OutlineGenerator()
        text = "チャンネル登録といいねをお願いします！"
        section_type = generator._detect_section_type(text)
        assert section_type == SectionType.CTA

    def test_extract_variables_number(self):
        """Test number variable extraction."""
        generator = OutlineGenerator()
        text = "この方法で100万円稼ぎました。"
        abstracted, variables = generator._extract_variables(text, 0)
        
        assert len(variables) >= 1
        assert "{NUMBER}" in abstracted
        assert any(v.category == "number" for v in variables)

    def test_extract_variables_person(self):
        """Test person name variable extraction."""
        generator = OutlineGenerator()
        text = "田中さんに教えてもらいました。"
        abstracted, variables = generator._extract_variables(text, 0)
        
        assert len(variables) >= 1
        assert "{WHO}" in abstracted
        assert any(v.category == "who" for v in variables)

    def test_extract_variables_company(self):
        """Test company name variable extraction."""
        generator = OutlineGenerator()
        text = "株式会社ABCと提携しています。"
        abstracted, variables = generator._extract_variables(text, 0)
        
        assert len(variables) >= 1
        assert "{BRAND}" in abstracted
        assert any(v.category == "brand" for v in variables)

    def test_extract_variables_place(self):
        """Test place variable extraction."""
        generator = OutlineGenerator()
        text = "東京で開催されるイベントです。"
        abstracted, variables = generator._extract_variables(text, 0)
        
        assert len(variables) >= 1
        assert "{PLACE}" in abstracted
        assert any(v.category == "place" for v in variables)

    def test_generate_from_segments(self):
        """Test outline generation from segments."""
        generator = OutlineGenerator()
        
        # Create sample segments
        segments = [
            TranscriptSegment(id=1, start=0.0, end=10.0, text="皆さん、こんにちは！今日は特別なお話があります。"),
            TranscriptSegment(id=2, start=10.0, end=25.0, text="多くの人が困っている問題があります。なぜできないのでしょうか。"),
            TranscriptSegment(id=3, start=25.0, end=40.0, text="実は、この問題を解決する秘密の方法があります。"),
            TranscriptSegment(id=4, start=40.0, end=60.0, text="例えば、私の場合は100万円稼ぎました。田中さんも成功しています。"),
            TranscriptSegment(id=5, start=60.0, end=75.0, text="まとめると、この方法は誰でもできます。"),
            TranscriptSegment(id=6, start=75.0, end=90.0, text="チャンネル登録といいねをお願いします！"),
        ]
        
        outline = generator.generate(segments, video_id="test123")
        
        assert outline.video_id == "test123"
        assert len(outline.sections) > 0
        assert len(outline.all_beats) > 0
        assert outline.metadata["total_duration"] == "90.0秒"

    def test_generate_assigns_section_types(self):
        """Test that section types are assigned based on content and position."""
        generator = OutlineGenerator()
        
        segments = [
            TranscriptSegment(id=1, start=0.0, end=20.0, text="こんにちは、今日は大切なお話があります。"),
            TranscriptSegment(id=2, start=20.0, end=40.0, text="この問題で困っている人が多いです。"),
            TranscriptSegment(id=3, start=40.0, end=60.0, text="チャンネル登録お願いします。"),
        ]
        
        outline = generator.generate(segments, video_id="test456")
        
        # First section should be HOOK
        assert outline.sections[0].section_type == SectionType.HOOK
        # Last section should be CTA
        assert outline.sections[-1].section_type == SectionType.CTA


class TestOutlineSection:
    """Tests for OutlineSection class."""

    def test_timecode_format_short(self):
        """Test timecode formatting for short durations."""
        section = OutlineSection(
            name="Test",
            section_type=SectionType.HOOK,
            start=65.5,
            end=125.0,
            summary="Test summary",
            template="Test template",
        )
        
        assert section.timecode_start == "01:05"
        assert section.timecode_end == "02:05"
        assert section.duration == 59.5

    def test_timecode_format_long(self):
        """Test timecode formatting for long durations (over 1 hour)."""
        section = OutlineSection(
            name="Test",
            section_type=SectionType.HOOK,
            start=3665.0,  # 1:01:05
            end=7325.0,    # 2:02:05
            summary="Test summary",
            template="Test template",
        )
        
        assert section.timecode_start == "01:01:05"
        assert section.timecode_end == "02:02:05"


class TestOutline:
    """Tests for Outline class."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        beat = Beat(
            id=1,
            start=0.0,
            end=10.0,
            summary="Introduction",
            template="Hello {WHO}!",
            original_text="Hello 田中さん!",
            variables=[Variable(name="{WHO}", original_value="田中さん", category="who", section_index=0)],
        )
        section = OutlineSection(
            name="Opening Hook",
            section_type=SectionType.HOOK,
            start=0.0,
            end=10.0,
            summary="Introduction",
            template="Hello {WHO}!",
            beats=[beat],
            variables=[Variable(name="{WHO}", original_value="田中さん", category="who", section_index=0)],
        )
        
        outline = Outline(
            video_id="test123",
            sections=[section],
            all_beats=[beat],
            all_variables=[Variable(name="{WHO}", original_value="田中さん", category="who", section_index=0)],
            metadata={"total_duration": "10.0s"},
        )
        
        data = outline.to_dict()
        
        assert data["video_id"] == "test123"
        assert len(data["sections"]) == 1
        assert data["sections"][0]["type"] == "hook"
        assert data["sections"][0]["timecode_start"] == "00:00"
        assert len(data["all_variables"]) == 1
        assert len(data["beats"]) == 1

    def test_to_json(self):
        """Test JSON serialization."""
        outline = Outline(
            video_id="test123",
            sections=[],
            all_beats=[],
            all_variables=[],
            metadata={},
        )
        
        json_str = outline.to_json()
        data = json.loads(json_str)
        
        assert data["video_id"] == "test123"

    def test_to_markdown(self):
        """Test Markdown generation."""
        beat = Beat(
            id=1,
            start=0.0,
            end=10.0,
            summary="Introduction",
            template="Hello everyone!",
            original_text="Hello everyone!",
        )
        section = OutlineSection(
            name="Opening Hook",
            section_type=SectionType.HOOK,
            start=0.0,
            end=10.0,
            summary="Introduction",
            template="Hello everyone!",
            beats=[beat],
        )
        
        outline = Outline(
            video_id="test123",
            sections=[section],
            all_beats=[beat],
            all_variables=[],
            metadata={"total_duration": "10.0s"},
        )
        
        md = outline.to_markdown()
        
        assert "動画構成アウトライン" in md
        assert "[00:00]" in md
        assert "Opening Hook" in md
        assert "HOOK" in md


class TestSaveOutline:
    """Tests for save_outline function."""

    def test_save_outline_creates_files(self):
        """Test that save_outline creates JSON and MD files."""
        outline = Outline(
            video_id="test123",
            sections=[],
            all_beats=[],
            all_variables=[],
            metadata={},
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            files = save_outline(outline, tmpdir, "test123", "20240101_120000")
            
            assert "json" in files
            assert "md" in files
            assert os.path.exists(files["json"])
            assert os.path.exists(files["md"])
            
            # Verify JSON content
            with open(files["json"], "r", encoding="utf-8") as f:
                data = json.load(f)
                assert data["video_id"] == "test123"


class TestTranscriptSegment:
    """Tests for TranscriptSegment class."""

    def test_to_srt_entry(self):
        """Test SRT format conversion."""
        segment = TranscriptSegment(
            id=1,
            start=65.5,
            end=70.25,
            text="Hello world",
        )
        
        srt = segment.to_srt_entry()
        
        assert "1\n" in srt
        assert "00:01:05,500" in srt
        assert "00:01:10,250" in srt
        assert "Hello world" in srt


class TestIntegration:
    """Integration tests for the full outline generation pipeline."""

    def test_full_pipeline(self):
        """Test complete pipeline from segments to saved files."""
        # Create realistic segments
        segments = [
            TranscriptSegment(id=1, start=0.0, end=15.0, 
                text="皆さん、こんにちは！今日は100万円稼ぐ方法をお伝えします。"),
            TranscriptSegment(id=2, start=15.0, end=30.0,
                text="多くの人がお金の問題で困っています。なぜ稼げないのでしょうか。"),
            TranscriptSegment(id=3, start=30.0, end=45.0,
                text="実は、田中さんが教えてくれた秘密の方法があります。"),
            TranscriptSegment(id=4, start=45.0, end=60.0,
                text="例えば、株式会社ABCと提携すると、東京で成功できます。"),
            TranscriptSegment(id=5, start=60.0, end=75.0,
                text="まとめると、この3つのステップを実践してください。"),
            TranscriptSegment(id=6, start=75.0, end=90.0,
                text="チャンネル登録といいねをお願いします！概要欄にリンクがあります。"),
        ]
        
        generator = OutlineGenerator()
        outline = generator.generate(segments, video_id="integration_test")
        
        # Verify outline structure
        assert outline.video_id == "integration_test"
        assert len(outline.sections) > 0
        assert len(outline.all_beats) > 0
        assert len(outline.all_variables) > 0
        
        # Verify variables were extracted
        variable_names = [v.name for v in outline.all_variables]
        assert any("{NUMBER}" in name for name in variable_names)
        
        # Save and verify files
        with tempfile.TemporaryDirectory() as tmpdir:
            files = save_outline(outline, tmpdir, "integration_test")
            
            # Verify JSON
            with open(files["json"], "r", encoding="utf-8") as f:
                data = json.load(f)
                assert data["video_id"] == "integration_test"
                assert len(data["sections"]) > 0
                assert len(data["beats"]) > 0
            
            # Verify Markdown
            with open(files["md"], "r", encoding="utf-8") as f:
                md = f.read()
                assert "動画構成アウトライン" in md
                assert "integration_test" in md or "タイムコード" in md
