"""
Outline Generator with Timecodes and Beats.

Generates abstracted script outlines from Whisper transcript segments.
Includes timecodes for each section, Beats (15-30s units), and variable extraction.
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
    STEPS = "steps"
    PROOF = "proof"
    SUMMARY = "summary"
    CTA = "cta"
    TRANSITION = "transition"
    OTHER = "other"


def format_timecode(seconds: float) -> str:
    """Format seconds as MM:SS or HH:MM:SS."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


@dataclass
class Variable:
    """A variable placeholder in the script."""
    name: str
    original_value: str
    category: str  # who, brand, number, place, story, steps
    section_index: int


@dataclass
class Beat:
    """A Beat is a 15-30 second unit of content with timecodes."""
    id: int
    start: float  # Start time in seconds
    end: float    # End time in seconds
    summary: str  # One-line summary
    template: str  # Abstracted template with variables
    original_text: str
    variables: list[Variable] = field(default_factory=list)

    @property
    def timecode_start(self) -> str:
        return format_timecode(self.start)

    @property
    def timecode_end(self) -> str:
        return format_timecode(self.end)

    @property
    def duration(self) -> float:
        return self.end - self.start


@dataclass
class OutlineSection:
    """A section of the outline with timecodes, containing multiple Beats."""
    name: str
    section_type: SectionType
    start: float  # Start time in seconds
    end: float    # End time in seconds
    summary: str
    template: str  # Abstracted template with variables
    beats: list[Beat] = field(default_factory=list)
    variables: list[Variable] = field(default_factory=list)
    original_text: str = ""

    @property
    def timecode_start(self) -> str:
        return format_timecode(self.start)

    @property
    def timecode_end(self) -> str:
        return format_timecode(self.end)

    @property
    def duration(self) -> float:
        return self.end - self.start


@dataclass
class Outline:
    """Complete outline with sections, beats, and metadata."""
    video_id: str
    sections: list[OutlineSection]
    all_beats: list[Beat]
    all_variables: list[Variable]
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "video_id": self.video_id,
            "metadata": self.metadata,
            "beats": [
                {
                    "id": b.id,
                    "start": b.start,
                    "end": b.end,
                    "timecode_start": b.timecode_start,
                    "timecode_end": b.timecode_end,
                    "duration": b.duration,
                    "summary": b.summary,
                    "template": b.template,
                    "original_text": b.original_text,
                    "variables": [asdict(v) for v in b.variables],
                }
                for b in self.all_beats
            ],
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
                    "beat_ids": [b.id for b in s.beats],
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
        """Convert to Markdown with timecodes and beats."""
        lines = []
        
        lines.append("# 動画構成アウトライン（タイムコード付き）")
        lines.append("")
        
        if self.metadata:
            lines.append("## メタデータ")
            lines.append("")
            for key, value in self.metadata.items():
                lines.append(f"- **{key}**: {value}")
            lines.append("")
        
        lines.append("## Beats一覧（15〜30秒単位）")
        lines.append("")
        lines.append("| # | タイムコード | 要約 |")
        lines.append("|---|-------------|------|")
        for beat in self.all_beats:
            summary = beat.summary[:50] + "..." if len(beat.summary) > 50 else beat.summary
            lines.append(f"| {beat.id} | [{beat.timecode_start}] - [{beat.timecode_end}] | {summary} |")
        lines.append("")
        
        lines.append("## セクション構成")
        lines.append("")
        
        for i, section in enumerate(self.sections, 1):
            lines.append(f"### {i}. [{section.timecode_start}] {section.name} ({section.section_type.value.upper()})")
            lines.append("")
            lines.append(f"**時間**: {section.timecode_start} - {section.timecode_end} ({section.duration:.1f}秒)")
            lines.append("")
            lines.append("**要約:**")
            lines.append(f"> {section.summary}")
            lines.append("")
            
            if section.beats:
                lines.append("**含まれるBeats:**")
                for beat in section.beats:
                    lines.append(f"- Beat {beat.id} [{beat.timecode_start}]: {beat.summary[:60]}...")
                lines.append("")
            
            lines.append("**抽象化テンプレート:**")
            lines.append("")
            lines.append("```")
            lines.append(section.template)
            lines.append("```")
            lines.append("")
            
            if section.variables:
                lines.append("**変数:**")
                for var in section.variables:
                    lines.append(f"- `{var.name}`: {var.original_value} ({var.category})")
                lines.append("")
        
        lines.append("## 全変数一覧（差し替えポイント）")
        lines.append("")
        lines.append("| 変数 | カテゴリ | 元の値 |")
        lines.append("|------|----------|--------|")
        for var in self.all_variables:
            orig = var.original_value[:40] + "..." if len(var.original_value) > 40 else var.original_value
            lines.append(f"| `{var.name}` | {var.category} | {orig} |")
        lines.append("")
        
        lines.append("## タイムコード索引")
        lines.append("")
        for i, section in enumerate(self.sections, 1):
            lines.append(f"- [{section.timecode_start}] {section.name}")
        
        return "\n".join(lines)


class OutlineGenerator:
    """Generates abstracted outlines with Beats from transcript segments."""

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
        SectionType.STEPS: [
            r"(ステップ|手順|やり方|方法)",
            r"(まず|次に|そして|最後に)",
            r"(step|first|then|next|finally)",
        ],
        SectionType.PROOF: [
            r"(証拠|データ|結果|実績|成果)",
            r"(research|study|data|results|proof)",
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

    VARIABLE_PATTERNS = [
        (r"(\d+(?:,\d+)*(?:\.\d+)?)\s*(円|ドル|万|億|%|パーセント|人|回|日|週間|ヶ月|年|kg|km|m|個|本|件)", "number", "{NUMBER}"),
        (r"(20\d{2}年|19\d{2}年)", "number", "{YEAR}"),
        (r"([一-龯]{2,4})(さん|氏|先生|社長|さま)", "who", "{WHO}"),
        (r"(株式会社[一-龯a-zA-Z]+|[一-龯a-zA-Z]+株式会社)", "brand", "{BRAND}"),
        (r"「([^」]+)」", "brand", "{PRODUCT}"),
        (r"(東京|大阪|名古屋|福岡|北海道|沖縄|[一-龯]{2,4}県|[一-龯]{2,4}市)", "place", "{PLACE}"),
        (r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b", "who", "{WHO}"),
        (r"(ステップ\d+|第\d+に|まず|次に|最後に|\d+つ目)", "steps", "{STEP}"),
    ]

    SECTION_NAMES_JA = {
        SectionType.HOOK: "オープニング（フック）",
        SectionType.PROBLEM: "問題提起",
        SectionType.CLAIM: "主張・解決策",
        SectionType.REASON: "理由・根拠",
        SectionType.STEPS: "手順・ステップ",
        SectionType.PROOF: "証拠・実績",
        SectionType.EXAMPLE: "具体例・体験談",
        SectionType.SUMMARY: "まとめ",
        SectionType.CTA: "行動喚起（CTA）",
        SectionType.TRANSITION: "つなぎ",
        SectionType.OTHER: "その他",
    }

    def __init__(self):
        self.variables: list[Variable] = []
        self.variable_counter: dict[str, int] = {}
        self.beats: list[Beat] = []

    def _get_next_variable_name(self, base_name: str) -> str:
        if base_name not in self.variable_counter:
            self.variable_counter[base_name] = 0
        self.variable_counter[base_name] += 1
        count = self.variable_counter[base_name]
        if count == 1:
            return base_name
        return f"{base_name}_{count}"

    def _detect_section_type(self, text: str) -> SectionType:
        for section_type, patterns in self.SECTION_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return section_type
        return SectionType.OTHER

    def _extract_variables(self, text: str, section_index: int) -> tuple[str, list[Variable]]:
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

    def _create_summary(self, text: str, max_length: int = 80) -> str:
        text = text.strip()
        if len(text) <= max_length:
            return text
        return text[:max_length].rsplit(" ", 1)[0] + "..."

    def _calculate_beat_durations(
        self,
        total_duration: float,
        min_beats: int = 3,
        target_min: float = 15.0,
        target_max: float = 30.0,
    ) -> tuple[float, float]:
        """
        Calculate appropriate beat durations based on total video duration.
        
        For short videos, use smaller beat durations to ensure minimum beat count.
        For long videos, use standard 15-30 second beats.
        
        Args:
            total_duration: Total video duration in seconds
            min_beats: Minimum number of beats to generate
            target_min: Target minimum beat duration
            target_max: Target maximum beat duration
        
        Returns:
            Tuple of (min_beat_duration, max_beat_duration)
        """
        if total_duration <= 0:
            return target_min, target_max
        
        max_possible_beats = total_duration / target_min
        if max_possible_beats >= min_beats:
            return target_min, target_max
        
        adjusted_max = total_duration / min_beats
        adjusted_min = adjusted_max * 0.5
        
        adjusted_min = max(3.0, adjusted_min)
        adjusted_max = max(5.0, adjusted_max)
        
        return adjusted_min, adjusted_max

    def _generate_beats(
        self,
        segments: list[TranscriptSegment],
        min_beat_duration: float = 15.0,
        max_beat_duration: float = 30.0,
        min_beats: int = 3,
    ) -> list[Beat]:
        """
        Generate Beats from segments (15-30 second units, minimum 3-5 beats).
        
        For short videos (< 90s), beat durations are adjusted to ensure
        at least min_beats are generated.
        """
        if not segments:
            return []

        total_duration = segments[-1].end - segments[0].start if segments else 0
        
        actual_min, actual_max = self._calculate_beat_durations(
            total_duration, 
            min_beats=min_beats,
            target_min=min_beat_duration,
            target_max=max_beat_duration,
        )

        beats = []
        beat_id = 1
        current_start = segments[0].start
        current_texts = []
        current_end = segments[0].end

        for seg in segments:
            current_texts.append(seg.text)
            current_end = seg.end
            duration = current_end - current_start

            should_create_beat = False
            if duration >= actual_max:
                should_create_beat = True
            elif duration >= actual_min:
                if (seg.text.endswith("。") or seg.text.endswith(".") or 
                    seg.text.endswith("？") or seg.text.endswith("?") or
                    seg.text.endswith("！") or seg.text.endswith("!")):
                    should_create_beat = True

            if should_create_beat and current_texts:
                text = " ".join(current_texts)
                template, variables = self._extract_variables(text, beat_id - 1)
                
                beat = Beat(
                    id=beat_id,
                    start=current_start,
                    end=current_end,
                    summary=self._create_summary(text),
                    template=template,
                    original_text=text,
                    variables=variables,
                )
                beats.append(beat)
                beat_id += 1
                current_start = current_end
                current_texts = []

        if current_texts:
            text = " ".join(current_texts)
            template, variables = self._extract_variables(text, beat_id - 1)
            beat = Beat(
                id=beat_id,
                start=current_start,
                end=current_end,
                summary=self._create_summary(text),
                template=template,
                original_text=text,
                variables=variables,
            )
            beats.append(beat)

        if len(beats) < min_beats and len(segments) >= min_beats:
            return self._force_split_into_beats(segments, min_beats)

        return beats

    def _force_split_into_beats(
        self,
        segments: list[TranscriptSegment],
        target_beats: int,
    ) -> list[Beat]:
        """
        Force split segments into a target number of beats.
        
        Used when normal beat generation produces too few beats.
        """
        if not segments:
            return []
        
        total_duration = segments[-1].end - segments[0].start
        beat_duration = total_duration / target_beats
        
        beats = []
        beat_id = 1
        current_start = segments[0].start
        current_texts = []
        current_end = segments[0].end
        
        for seg in segments:
            current_texts.append(seg.text)
            current_end = seg.end
            
            if current_end - current_start >= beat_duration and current_texts:
                text = " ".join(current_texts)
                template, variables = self._extract_variables(text, beat_id - 1)
                
                beat = Beat(
                    id=beat_id,
                    start=current_start,
                    end=current_end,
                    summary=self._create_summary(text),
                    template=template,
                    original_text=text,
                    variables=variables,
                )
                beats.append(beat)
                beat_id += 1
                current_start = current_end
                current_texts = []
        
        if current_texts:
            text = " ".join(current_texts)
            template, variables = self._extract_variables(text, beat_id - 1)
            beat = Beat(
                id=beat_id,
                start=current_start,
                end=current_end,
                summary=self._create_summary(text),
                template=template,
                original_text=text,
                variables=variables,
            )
            beats.append(beat)
        
        return beats

    def _group_beats_into_sections(self, beats: list[Beat]) -> list[OutlineSection]:
        """Group Beats into logical Sections based on content patterns."""
        if not beats:
            return []

        sections = []
        current_beats: list[Beat] = []
        current_type = SectionType.OTHER
        
        for i, beat in enumerate(beats):
            detected_type = self._detect_section_type(beat.original_text)
            
            if detected_type == SectionType.OTHER:
                position = i / max(len(beats), 1)
                if i == 0:
                    detected_type = SectionType.HOOK
                elif i >= len(beats) - 2:
                    detected_type = SectionType.CTA
                elif position < 0.2:
                    detected_type = SectionType.PROBLEM
                elif position < 0.35:
                    detected_type = SectionType.CLAIM
                elif position < 0.6:
                    detected_type = SectionType.STEPS
                elif position < 0.8:
                    detected_type = SectionType.PROOF
                else:
                    detected_type = SectionType.SUMMARY

            if current_beats and detected_type != current_type:
                section = self._create_section_from_beats(current_beats, current_type, len(sections))
                sections.append(section)
                current_beats = []
            
            current_type = detected_type
            current_beats.append(beat)

        if current_beats:
            section = self._create_section_from_beats(current_beats, current_type, len(sections))
            sections.append(section)

        return sections

    def _create_section_from_beats(
        self, 
        beats: list[Beat], 
        section_type: SectionType, 
        index: int
    ) -> OutlineSection:
        """Create a Section from a list of Beats."""
        all_text = " ".join(b.original_text for b in beats)
        all_template = " ".join(b.template for b in beats)
        all_variables = []
        for b in beats:
            all_variables.extend(b.variables)

        return OutlineSection(
            name=self.SECTION_NAMES_JA.get(section_type, f"セクション {index + 1}"),
            section_type=section_type,
            start=beats[0].start,
            end=beats[-1].end,
            summary=self._create_summary(all_text, max_length=120),
            template=all_template,
            beats=beats,
            variables=all_variables,
            original_text=all_text,
        )

    def generate(
        self,
        segments: list[TranscriptSegment],
        video_id: str,
        min_beat_duration: float = 15.0,
        max_beat_duration: float = 30.0,
    ) -> Outline:
        """
        Generate an outline with Beats from transcript segments.

        Args:
            segments: List of transcript segments with timestamps
            video_id: Video ID for reference
            min_beat_duration: Minimum duration for each Beat (default 15s)
            max_beat_duration: Maximum duration for each Beat (default 30s)

        Returns:
            Outline object with Beats, Sections, and variables
        """
        self.variables = []
        self.variable_counter = {}
        self.beats = []

        if not segments:
            return Outline(
                video_id=video_id,
                sections=[],
                all_beats=[],
                all_variables=[],
                metadata={"error": "No segments provided"},
            )

        beats = self._generate_beats(segments, min_beat_duration, max_beat_duration)
        self.beats = beats

        sections = self._group_beats_into_sections(beats)

        total_duration = segments[-1].end if segments else 0
        metadata = {
            "total_duration": f"{total_duration:.1f}秒",
            "beat_count": len(beats),
            "section_count": len(sections),
            "variable_count": len(self.variables),
            "generated_at": datetime.now().isoformat(),
        }

        return Outline(
            video_id=video_id,
            sections=sections,
            all_beats=beats,
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
    Save outline to files in output/videoId/ folder structure.

    Args:
        outline: Outline to save
        output_dir: Base output directory
        video_id: Video ID for folder and filename
        timestamp: Optional timestamp for filename

    Returns:
        Dictionary mapping format to file path
    """
    video_output_dir = os.path.join(output_dir, video_id)
    os.makedirs(video_output_dir, exist_ok=True)
    
    ts = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"outline_{ts}"
    
    output_files = {}

    json_path = os.path.join(video_output_dir, f"{base_name}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        f.write(outline.to_json())
    output_files["json"] = json_path

    md_path = os.path.join(video_output_dir, f"{base_name}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(outline.to_markdown())
    output_files["md"] = md_path

    return output_files
