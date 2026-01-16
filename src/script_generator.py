"""
Script Abstraction Generator (PR3)

Converts transcript text into an abstracted script template with:
- Sections: Hook, Problem, Claim, Reason, Example, Summary, CTA
- Variables for customization: {WHO}, {PAIN}, {NUMBER}, {PROOF}, etc.
- Output in both JSON and Markdown formats
"""

import json
import re
import os
from dataclasses import dataclass, field, asdict
from typing import Optional
from enum import Enum


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
    description: str
    category: str  # e.g., "person", "number", "pain_point", "proof"


@dataclass
class ScriptSection:
    """A section of the abstracted script."""
    section_type: SectionType
    title: str
    content: str
    abstracted_content: str
    variables: list[Variable] = field(default_factory=list)
    order: int = 0
    notes: str = ""


@dataclass
class AbstractedScript:
    """The complete abstracted script."""
    original_transcript: str
    sections: list[ScriptSection]
    variables: list[Variable]
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "metadata": self.metadata,
            "sections": [
                {
                    "order": s.order,
                    "type": s.section_type.value,
                    "title": s.title,
                    "original_content": s.content,
                    "abstracted_content": s.abstracted_content,
                    "variables": [asdict(v) for v in s.variables],
                    "notes": s.notes,
                }
                for s in self.sections
            ],
            "all_variables": [asdict(v) for v in self.variables],
            "replacement_points": [
                {
                    "variable": v.name,
                    "original": v.original_value,
                    "category": v.category,
                    "description": v.description,
                }
                for v in self.variables
            ],
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    def to_markdown(self) -> str:
        """Convert to Markdown format."""
        lines = []
        
        # Header
        lines.append("# Abstracted Script Template")
        lines.append("")
        
        # Metadata
        if self.metadata:
            lines.append("## Metadata")
            lines.append("")
            for key, value in self.metadata.items():
                lines.append(f"- **{key}**: {value}")
            lines.append("")
        
        # Sections
        lines.append("## Script Structure")
        lines.append("")
        
        for section in sorted(self.sections, key=lambda s: s.order):
            lines.append(f"### {section.order}. {section.title} ({section.section_type.value.upper()})")
            lines.append("")
            lines.append("**Abstracted Template:**")
            lines.append("")
            lines.append(f"> {section.abstracted_content}")
            lines.append("")
            
            if section.variables:
                lines.append("**Variables in this section:**")
                lines.append("")
                for var in section.variables:
                    lines.append(f"- `{var.name}`: {var.description} (original: \"{var.original_value}\")")
                lines.append("")
            
            if section.notes:
                lines.append(f"*Notes: {section.notes}*")
                lines.append("")
        
        # Variable Summary
        lines.append("## Variable Replacement Points")
        lines.append("")
        lines.append("| Variable | Category | Original Value | Description |")
        lines.append("|----------|----------|----------------|-------------|")
        for var in self.variables:
            lines.append(f"| `{var.name}` | {var.category} | {var.original_value[:30]}{'...' if len(var.original_value) > 30 else ''} | {var.description} |")
        lines.append("")
        
        # Original transcript (truncated)
        lines.append("## Original Transcript (Reference)")
        lines.append("")
        lines.append("```")
        if len(self.original_transcript) > 2000:
            lines.append(self.original_transcript[:2000] + "...")
            lines.append(f"[Truncated - full transcript is {len(self.original_transcript)} characters]")
        else:
            lines.append(self.original_transcript)
        lines.append("```")
        
        return "\n".join(lines)


class ScriptAbstractor:
    """
    Abstracts a transcript into a reusable script template.
    
    This is a rule-based implementation for v1. Future versions could use
    LLM-based analysis for more sophisticated abstraction.
    """

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
        (r"(\d+(?:,\d+)*(?:\.\d+)?)\s*(円|ドル|万|億|%|パーセント|人|回|日|週間|ヶ月|年|kg|km|m)", "number", "{NUMBER}"),
        # Specific years
        (r"(20\d{2}年|19\d{2}年)", "date", "{YEAR}"),
        # Person names (Japanese)
        (r"([一-龯]{2,4})(さん|氏|先生|社長)", "person", "{WHO}"),
        # Company names
        (r"(株式会社[一-龯a-zA-Z]+|[一-龯a-zA-Z]+株式会社)", "company", "{COMPANY}"),
        # Product names (quoted)
        (r"「([^」]+)」", "product", "{PRODUCT}"),
        # English names
        (r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b", "person", "{WHO}"),
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
        text_lower = text.lower()
        
        for section_type, patterns in self.SECTION_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return section_type
        
        return SectionType.OTHER

    def _extract_variables(self, text: str) -> tuple[str, list[Variable]]:
        """Extract variables from text and return abstracted text."""
        abstracted = text
        variables = []
        
        for pattern, category, var_template in self.VARIABLE_PATTERNS:
            matches = list(re.finditer(pattern, text))
            for match in matches:
                original_value = match.group(0)
                var_name = self._get_next_variable_name(var_template)
                
                # Create variable
                var = Variable(
                    name=var_name,
                    original_value=original_value,
                    description=f"Replace with your {category}",
                    category=category,
                )
                variables.append(var)
                self.variables.append(var)
                
                # Replace in abstracted text
                abstracted = abstracted.replace(original_value, var_name, 1)
        
        return abstracted, variables

    def _split_into_sections(self, transcript: str) -> list[tuple[str, str]]:
        """Split transcript into logical sections."""
        # Split by common delimiters
        # Try paragraph breaks first
        paragraphs = re.split(r'\n\s*\n', transcript)
        
        if len(paragraphs) < 3:
            # Try sentence-based splitting for dense text
            sentences = re.split(r'(?<=[。.!?！？])\s*', transcript)
            # Group sentences into chunks of ~3-5
            paragraphs = []
            chunk = []
            for sent in sentences:
                chunk.append(sent)
                if len(chunk) >= 4:
                    paragraphs.append(''.join(chunk))
                    chunk = []
            if chunk:
                paragraphs.append(''.join(chunk))
        
        # Clean up empty paragraphs
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        return paragraphs

    def _assign_section_types(self, paragraphs: list[str]) -> list[ScriptSection]:
        """Assign section types to paragraphs based on position and content."""
        sections = []
        total = len(paragraphs)
        
        for i, para in enumerate(paragraphs):
            # Detect type based on content
            detected_type = self._detect_section_type(para)
            
            # Override based on position if type is OTHER
            if detected_type == SectionType.OTHER:
                if i == 0:
                    detected_type = SectionType.HOOK
                elif i == total - 1:
                    detected_type = SectionType.CTA
                elif i == total - 2:
                    detected_type = SectionType.SUMMARY
                elif i < total * 0.3:
                    detected_type = SectionType.PROBLEM
                elif i < total * 0.5:
                    detected_type = SectionType.CLAIM
                elif i < total * 0.7:
                    detected_type = SectionType.REASON
                else:
                    detected_type = SectionType.EXAMPLE
            
            # Extract variables
            abstracted, variables = self._extract_variables(para)
            
            # Create section
            section = ScriptSection(
                section_type=detected_type,
                title=self._get_section_title(detected_type, i),
                content=para,
                abstracted_content=abstracted,
                variables=variables,
                order=i + 1,
                notes=self._get_section_notes(detected_type),
            )
            sections.append(section)
        
        return sections

    def _get_section_title(self, section_type: SectionType, index: int) -> str:
        """Get a descriptive title for the section."""
        titles = {
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
        return titles.get(section_type, f"Section {index + 1}")

    def _get_section_notes(self, section_type: SectionType) -> str:
        """Get notes/tips for each section type."""
        notes = {
            SectionType.HOOK: "Grab attention in first 3 seconds. Use curiosity, shock, or direct address.",
            SectionType.PROBLEM: "Identify the pain point your audience relates to.",
            SectionType.CLAIM: "Present your unique solution or insight.",
            SectionType.REASON: "Explain why your claim is valid with logic or data.",
            SectionType.EXAMPLE: "Use concrete examples, stories, or case studies.",
            SectionType.SUMMARY: "Reinforce key takeaways concisely.",
            SectionType.CTA: "Clear action: subscribe, comment, or click link.",
            SectionType.TRANSITION: "Smooth connection between sections.",
            SectionType.OTHER: "",
        }
        return notes.get(section_type, "")

    def abstract(self, transcript: str) -> AbstractedScript:
        """
        Abstract a transcript into a reusable script template.
        
        Args:
            transcript: The full transcript text
            
        Returns:
            AbstractedScript object with sections and variables
        """
        # Reset state
        self.variables = []
        self.variable_counter = {}
        
        # Split into sections
        paragraphs = self._split_into_sections(transcript)
        
        # Assign types and extract variables
        sections = self._assign_section_types(paragraphs)
        
        # Create metadata
        metadata = {
            "original_length": len(transcript),
            "section_count": len(sections),
            "variable_count": len(self.variables),
            "estimated_duration": f"{len(transcript) // 300} minutes",  # ~300 chars/min for Japanese
        }
        
        return AbstractedScript(
            original_transcript=transcript,
            sections=sections,
            variables=self.variables,
            metadata=metadata,
        )


def abstract_transcript(
    transcript: str,
    output_json_path: Optional[str] = None,
    output_md_path: Optional[str] = None,
) -> AbstractedScript:
    """
    Convenience function to abstract a transcript and optionally save outputs.
    
    Args:
        transcript: The transcript text
        output_json_path: Optional path to save JSON output
        output_md_path: Optional path to save Markdown output
        
    Returns:
        AbstractedScript object
    """
    abstractor = ScriptAbstractor()
    result = abstractor.abstract(transcript)
    
    if output_json_path:
        os.makedirs(os.path.dirname(output_json_path) or ".", exist_ok=True)
        with open(output_json_path, "w", encoding="utf-8") as f:
            f.write(result.to_json())
    
    if output_md_path:
        os.makedirs(os.path.dirname(output_md_path) or ".", exist_ok=True)
        with open(output_md_path, "w", encoding="utf-8") as f:
            f.write(result.to_markdown())
    
    return result
