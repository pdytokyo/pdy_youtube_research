"""
Outline Generator with Timecodes.

Generates abstracted script outlines from Whisper transcript segments.
Includes timecodes for each section and variable extraction.
"""

import os
import json
import re
from dataclasses import dataclass, field, asdict
from typing import Optional
from datetime import datetime
from enum import Enum

from .transcriber import TranscriptSegment


class SectionType(str, Enum):
    """Script section types."""
    HOOK = "hook"
    PROBLEM = "problem"
    CLAIM = "claim"
    REASON = "reason"
    EXAMPLE = "example"
    SUMMARY = "summary"
    CTA = "cta"
    TRANSITION = "transition"
    OTHER = "other"


@dataclass
class Variable:
    """A variable placeholder in the script."""
    name: str
    original_value: str
    category: str  # who, brand, number, place, story, steps
    section_index: int


@dataclass
class OutlineSection:
    """A section of the outline with timecodes."""
    name: str
    section_type: SectionType
    start: float  # Start time in seconds
    end: float    # End time in seconds
    summary: str
    template: str  # Abstracted template with variables
    variables: list[Variable] = field(default_factory=list)
    original_text: str = ""

    def format_timecode(self, seconds: float) -> str:
        """Format seconds as MM:SS or HH:MM:SS."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"

    @property
    def timecode_start(self) -> str:
        return self.format_timecode(self.start)

    @property
    def timecode_end(self) -> str:
        return self.format_timecode(self.end)

    @property
    def duration(self) -> float:
        return self.end - self.start


@dataclass
class Outline:
    """Complete outline with sections and metadata."""
    video_id: str
    sections: list[OutlineSection]
    all_variables: list[Variable]
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "video_id": self.video_id,
            "metadata": self.metadata,
            "sections": [
                {
                    "name": s.name,
                    "type": s.section_type.value,
                    "start": s.start,
                    "end": s.end,
                    "timecode_start": s.timecode_start,
                    "timecode_end": s.timecode_end,
                    "duration": s.duration,
                    "summary": s.summary,
                    "template": s.template,
                    "variables": [asdict(v) for v in s.variables],
                    "original_text": s.original_text,
                }
                for s in self.sections
            ],
            "all_variables": [asdict(v) for v in self.all_variables],
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    def to_markdown(self) -> str:
        """Convert to Markdown with timecodes."""
        lines = []
        
        # Header
        lines.append("# Video Outline with Timecodes")
        lines.append("")
        
        # Metadata
        if self.metadata:
            lines.append("## Metadata")
            lines.append("")
            for key, value in self.metadata.items():
                lines.append(f"- **{key}**: {value}")
            lines.append("")
        
        # Sections with timecodes
        lines.append("## Script Structure")
        lines.append("")
        
        for i, section in enumerate(self.sections, 1):
            lines.append(f"### {i}. [{section.timecode_start}] {section.name} ({section.section_type.value.upper()})")
            lines.append("")
            lines.append(f"**Duration**: {section.timecode_start} - {section.timecode_end} ({section.duration:.1f}s)")
            lines.append("")
            lines.append("**Summary:**")
            lines.append(f"> {section.summary}")
            lines.append("")
            lines.append("**Abstracted Template:**")
            lines.append("")
            lines.append(f"```")
            lines.append(section.template)
            lines.append(f"```")
            lines.append("")
            
            if section.variables:
                lines.append("**Variables:**")
                for var in section.variables:
                    lines.append(f"- `{var.name}`: {var.original_value} ({var.category})")
                lines.append("")
        
        # Variable Summary
        lines.append("## All Variables (Replacement Points)")
        lines.append("")
        lines.append("| Variable | Category | Original Value |")
        lines.append("|----------|----------|----------------|")
        for var in self.all_variables:
            orig = var.original_value[:40] + "..." if len(var.original_value) > 40 else var.original_value
            lines.append(f"| `{var.name}` | {var.category} | {orig} |")
        lines.append("")
        
        # Timecode Index
        lines.append("## Timecode Index")
        lines.append("")
        for i, section in enumerate(self.sections, 1):
            lines.append(f"- [{section.timecode_start}] {section.name}")
        
        return "\n".join(lines)


class OutlineGenerator:
    """Generates abstracted outlines from transcript segments."""

    # Patterns for detecting section types
    SECTION_PATTERNS = {
        SectionType.HOOK: [
            r"^(皆さん|みなさん|こんにちは|今日は|ねえ|ちょっと待って)",
            r"(知ってました\?|信じられない|衝撃|驚き|実は)",
            r"^(Hey|Hi|Hello|Did you know|What if)",
        ],
        SectionType.PROBLEM: [
            r"(困って|悩んで|問題|課題|大変|辛い|苦しい)",
            r"(なぜ.+できない|どうして.+ない)",
            r"(struggle|problem|issue|challenge|difficult)",
        ],
        SectionType.CLAIM: [
            r"(実は|実際|本当は|秘密|コツ|方法)",
            r"(解決|答え|ポイント|鍵)",
            r"(the secret|the key|the answer|actually|in fact)",
        ],
        SectionType.REASON: [
            r"(なぜなら|理由|だから|というのも)",
            r"(because|reason|that's why|since)",
        ],
        SectionType.EXAMPLE: [
            r"(例えば|たとえば|具体的に|実際に)",
            r"(私の場合|私は|僕は|経験)",
            r"(for example|for instance|in my case|I personally)",
        ],
        SectionType.SUMMARY: [
            r"(まとめ|要約|結論|つまり|要するに)",
            r"(in summary|to summarize|in conclusion|so basically)",
        ],
        SectionType.CTA: [
            r"(チャンネル登録|いいね|コメント|シェア|フォロー)",
            r"(リンク|概要欄|説明欄|詳細)",
            r"(subscribe|like|comment|share|follow|link|description)",
        ],
    }

    # Patterns for extracting variables
    VARIABLE_PATTERNS = [
        # Numbers with units
        (r"(\d+(?:,\d+)*(?:\.\d+)?)\s*(円|ドル|万|億|%|パーセント|人|回|日|週間|ヶ月|年|kg|km|m|個|本|件)", "number", "{NUMBER}"),
        # Specific years
        (r"(20\d{2}年|19\d{2}年)", "number", "{YEAR}"),
        # Person names (Japanese with honorifics)
        (r"([一-龯]{2,4})(さん|氏|先生|社長|さま)", "who", "{WHO}"),
        # Company/Brand names
        (r"(株式会社[一-龯a-zA-Z]+|[一-龯a-zA-Z]+株式会社)", "brand", "{BRAND}"),
        # Product names (quoted)
        (r"「([^」]+)」", "brand", "{PRODUCT}"),
        # Places
        (r"(東京|大阪|名古屋|福岡|北海道|沖縄|[一-龯]{2,4}県|[一-龯]{2,4}市)", "place", "{PLACE}"),
        # English names
        (r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b", "who", "{WHO}"),
        # Step indicators
        (r"(ステップ\d+|第\d+に|まず|次に|最後に|\d+つ目)", "steps", "{STEP}"),
    ]

    def __init__(self):
        self.variables: list[Variable] = []
        self.variable_counter: dict[str, int] = {}

    def _get_next_variable_name(self, base_name: str) -> str:
        """Generate unique variable name."""
        if base_name not in self.variable_counter:
            self.variable_counter[base_name] = 0
        self.variable_counter[base_name] += 1
        count = self.variable_counter[base_name]
        if count == 1:
            return base_name
        return f"{base_name}_{count}"

    def _detect_section_type(self, text: str) -> SectionType:
        """Detect the section type based on content patterns."""
        for section_type, patterns in self.SECTION_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return section_type
        return SectionType.OTHER

    def _extract_variables(self, text: str, section_index: int) -> tuple[str, list[Variable]]:
        """Extract variables from text and return abstracted text."""
        abstracted = text
        variables = []
        
        for pattern, category, var_template in self.VARIABLE_PATTERNS:
            matches = list(re.finditer(pattern, text))
            for match in matches:
                original_value = match.group(0)
                var_name = self._get_next_variable_name(var_template)
                
                var = Variable(
                    name=var_name,
                    original_value=original_value,
                    category=category,
                    section_index=section_index,
                )
                variables.append(var)
                self.variables.append(var)
                
                abstracted = abstracted.replace(original_value, var_name, 1)
        
        return abstracted, variables

    def _group_segments_into_sections(
        self,
        segments: list[TranscriptSegment],
        min_section_duration: float = 15.0,
    ) -> list[tuple[float, float, str]]:
        """
        Group segments into logical sections.

        Args:
            segments: List of transcript segments
            min_section_duration: Minimum duration for a section in seconds

        Returns:
            List of (start, end, text) tuples for each section
        """
        if not segments:
            return []

        sections = []
        current_start = segments[0].start
        current_texts = []
        current_end = segments[0].end

        for seg in segments:
            current_texts.append(seg.text)
            current_end = seg.end
            
            # Check if we should start a new section
            duration = current_end - current_start
            text = " ".join(current_texts)
            
            # Start new section if:
            # 1. Duration exceeds minimum AND
            # 2. We detect a section boundary (pattern change or pause)
            if duration >= min_section_duration:
                # Check for section boundary indicators
                if (self._detect_section_type(seg.text) != SectionType.OTHER or
                    duration >= min_section_duration * 2):
                    sections.append((current_start, current_end, text))
                    current_start = seg.end
                    current_texts = []

        # Add remaining content as final section
        if current_texts:
            sections.append((current_start, current_end, " ".join(current_texts)))

        return sections

    def _get_section_name(self, section_type: SectionType, index: int) -> str:
        """Get a descriptive name for the section."""
        names = {
            SectionType.HOOK: "Opening Hook",
            SectionType.PROBLEM: "Problem Statement",
            SectionType.CLAIM: "Main Claim",
            SectionType.REASON: "Supporting Reason",
            SectionType.EXAMPLE: "Example/Story",
            SectionType.SUMMARY: "Summary",
            SectionType.CTA: "Call to Action",
            SectionType.TRANSITION: "Transition",
            SectionType.OTHER: f"Section {index + 1}",
        }
        return names.get(section_type, f"Section {index + 1}")

    def _create_summary(self, text: str, max_length: int = 100) -> str:
        """Create a brief summary of the section text."""
        # Simple truncation for now - could be enhanced with LLM
        text = text.strip()
        if len(text) <= max_length:
            return text
        return text[:max_length].rsplit(" ", 1)[0] + "..."

    def generate(
        self,
        segments: list[TranscriptSegment],
        video_id: str,
        min_section_duration: float = 15.0,
    ) -> Outline:
        """
        Generate an outline from transcript segments.

        Args:
            segments: List of transcript segments with timestamps
            video_id: Video ID for reference
            min_section_duration: Minimum duration for each section

        Returns:
            Outline object with sections and variables
        """
        # Reset state
        self.variables = []
        self.variable_counter = {}

        # Group segments into sections
        raw_sections = self._group_segments_into_sections(segments, min_section_duration)

        # Process each section
        outline_sections = []
        total_duration = segments[-1].end if segments else 0

        for i, (start, end, text) in enumerate(raw_sections):
            # Detect section type
            section_type = self._detect_section_type(text)
            
            # Override based on position if OTHER
            if section_type == SectionType.OTHER:
                position = i / max(len(raw_sections), 1)
                if i == 0:
                    section_type = SectionType.HOOK
                elif i == len(raw_sections) - 1:
                    section_type = SectionType.CTA
                elif position < 0.3:
                    section_type = SectionType.PROBLEM
                elif position < 0.5:
                    section_type = SectionType.CLAIM
                elif position < 0.7:
                    section_type = SectionType.REASON
                elif position < 0.9:
                    section_type = SectionType.EXAMPLE
                else:
                    section_type = SectionType.SUMMARY

            # Extract variables and create template
            template, variables = self._extract_variables(text, i)

            # Create section
            section = OutlineSection(
                name=self._get_section_name(section_type, i),
                section_type=section_type,
                start=start,
                end=end,
                summary=self._create_summary(text),
                template=template,
                variables=variables,
                original_text=text,
            )
            outline_sections.append(section)

        # Create metadata
        metadata = {
            "total_duration": f"{total_duration:.1f}s",
            "section_count": len(outline_sections),
            "variable_count": len(self.variables),
            "generated_at": datetime.now().isoformat(),
        }

        return Outline(
            video_id=video_id,
            sections=outline_sections,
            all_variables=self.variables,
            metadata=metadata,
        )


def save_outline(
    outline: Outline,
    output_dir: str,
    video_id: str,
    timestamp: Optional[str] = None,
) -> dict[str, str]:
    """
    Save outline to files.

    Args:
        outline: Outline to save
        output_dir: Directory to save files
        video_id: Video ID for filename
        timestamp: Optional timestamp for filename

    Returns:
        Dictionary mapping format to file path
    """
    os.makedirs(output_dir, exist_ok=True)
    
    ts = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"outline_{video_id}_{ts}"
    
    output_files = {}

    # Save JSON
    json_path = os.path.join(output_dir, f"{base_name}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        f.write(outline.to_json())
    output_files["json"] = json_path

    # Save Markdown
    md_path = os.path.join(output_dir, f"{base_name}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(outline.to_markdown())
    output_files["md"] = md_path

    return output_files
