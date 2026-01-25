"""Schema definitions for best practice templates."""

from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class Placeholder(BaseModel):
    """Template placeholder definition."""

    name: str = Field(..., description="Placeholder name (e.g., FILE_PATH)")
    description: str = Field(default="", description="English description")
    description_ko: Optional[str] = Field(default=None, description="Korean description")
    required: bool = Field(default=True, description="Whether this placeholder is required")
    example: str = Field(default="", description="Example value")


class BestPracticeTemplate(BaseModel):
    """A single best practice template."""

    id: str = Field(..., description="Unique template ID (e.g., debug-001)")
    name: str = Field(..., description="Template name in English")
    name_ko: Optional[str] = Field(default=None, description="Template name in Korean")
    pattern_type: str = Field(
        default="generic",
        description="Pattern type: target_action, context_goal, reference_based, etc.",
    )
    intent: str = Field(
        ...,
        description="Intent: fix, find, create, explain, refactor, test",
    )
    triggers: List[str] = Field(
        default_factory=list,
        description="Keywords that trigger this template",
    )
    template: Dict[str, str] = Field(
        ...,
        description="Template text by language: {ko: ..., en: ...}",
    )
    placeholders: List[Placeholder] = Field(
        default_factory=list,
        description="List of placeholders in the template",
    )
    quality_boost: float = Field(
        default=2.0,
        description="Expected quality score improvement",
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Tags for categorization",
    )


class TemplateCollection(BaseModel):
    """Collection of templates from a YAML file."""

    version: str = Field(default="1.0", description="Schema version")
    category: str = Field(..., description="Template category")
    templates: List[BestPracticeTemplate] = Field(
        default_factory=list,
        description="List of templates",
    )
