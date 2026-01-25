"""Best practices template loading and management."""

from pathlib import Path
from typing import Dict, List, Optional
import yaml

from .schema import BestPracticeTemplate, TemplateCollection


# Cache for loaded templates
_TEMPLATE_CACHE: Dict[str, TemplateCollection] = {}
_ALL_TEMPLATES: List[BestPracticeTemplate] = []


def get_bundled_templates_path() -> Path:
    """Get path to bundled templates (shipped with package)."""
    return Path(__file__).parent


def get_user_templates_path() -> Path:
    """Get path to user-defined templates."""
    return Path.home() / ".claude-x" / "best_practices"


def _load_yaml_file(path: Path) -> Optional[TemplateCollection]:
    """Load a single YAML template file."""
    if not path.exists() or not path.suffix in (".yaml", ".yml"):
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data or "templates" not in data:
            return None

        return TemplateCollection(**data)
    except Exception:
        return None


def load_templates(reload: bool = False) -> List[BestPracticeTemplate]:
    """Load all templates from bundled and user directories.

    Args:
        reload: Force reload even if cached

    Returns:
        List of all available templates
    """
    global _TEMPLATE_CACHE, _ALL_TEMPLATES

    if _ALL_TEMPLATES and not reload:
        return _ALL_TEMPLATES

    _TEMPLATE_CACHE.clear()
    _ALL_TEMPLATES = []

    # Load bundled templates first
    bundled_path = get_bundled_templates_path()
    for yaml_file in bundled_path.glob("*.yaml"):
        if yaml_file.name.startswith("_"):
            continue
        collection = _load_yaml_file(yaml_file)
        if collection:
            _TEMPLATE_CACHE[yaml_file.stem] = collection
            _ALL_TEMPLATES.extend(collection.templates)

    # Load user templates (override bundled if same ID)
    user_path = get_user_templates_path()
    if user_path.exists():
        for yaml_file in user_path.glob("*.yaml"):
            if yaml_file.name.startswith("_"):
                continue
            collection = _load_yaml_file(yaml_file)
            if collection:
                # Remove duplicates by ID
                existing_ids = {t.id for t in _ALL_TEMPLATES}
                for template in collection.templates:
                    if template.id in existing_ids:
                        _ALL_TEMPLATES = [
                            t for t in _ALL_TEMPLATES if t.id != template.id
                        ]
                    _ALL_TEMPLATES.append(template)
                _TEMPLATE_CACHE[f"user_{yaml_file.stem}"] = collection

    return _ALL_TEMPLATES


def get_template_by_id(template_id: str) -> Optional[BestPracticeTemplate]:
    """Get a specific template by its ID.

    Args:
        template_id: Template ID (e.g., "debug-001")

    Returns:
        Template if found, None otherwise
    """
    templates = load_templates()
    for template in templates:
        if template.id == template_id:
            return template
    return None


def get_templates_by_intent(intent: str) -> List[BestPracticeTemplate]:
    """Get all templates matching a specific intent.

    Args:
        intent: Intent to filter by (fix, find, create, explain, refactor, test)

    Returns:
        List of templates matching the intent
    """
    templates = load_templates()
    return [t for t in templates if t.intent == intent]


def get_templates_by_category(category: str) -> List[BestPracticeTemplate]:
    """Get all templates from a specific category.

    Args:
        category: Category to filter by (debugging, implementation, etc.)

    Returns:
        List of templates in the category
    """
    templates = load_templates()
    result = []
    for collection in _TEMPLATE_CACHE.values():
        if collection.category == category:
            result.extend(collection.templates)
    return result


def search_templates(
    keyword: str,
    intent: Optional[str] = None,
    limit: int = 10,
) -> List[BestPracticeTemplate]:
    """Search templates by keyword and optional intent.

    Args:
        keyword: Keyword to search for in triggers, name, tags
        intent: Optional intent filter
        limit: Maximum results to return

    Returns:
        List of matching templates
    """
    templates = load_templates()
    keyword_lower = keyword.lower()

    results = []
    for template in templates:
        # Filter by intent if specified
        if intent and template.intent != intent:
            continue

        # Search in triggers, name, tags
        searchable = (
            template.triggers
            + [template.name, template.name_ko or ""]
            + template.tags
        )
        if any(keyword_lower in s.lower() for s in searchable if s):
            results.append(template)

        if len(results) >= limit:
            break

    return results


def get_all_intents() -> List[str]:
    """Get list of all unique intents from templates."""
    templates = load_templates()
    return list(set(t.intent for t in templates))


def get_all_categories() -> List[str]:
    """Get list of all unique categories."""
    load_templates()
    return list(set(c.category for c in _TEMPLATE_CACHE.values()))


def get_template_stats() -> Dict:
    """Get statistics about loaded templates.

    Returns:
        Dictionary with template statistics
    """
    templates = load_templates()

    intent_counts = {}
    tag_counts = {}

    for t in templates:
        intent_counts[t.intent] = intent_counts.get(t.intent, 0) + 1
        for tag in t.tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    return {
        "total_templates": len(templates),
        "categories": get_all_categories(),
        "intents": intent_counts,
        "top_tags": sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10],
    }
