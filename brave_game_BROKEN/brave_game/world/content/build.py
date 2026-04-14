"""Content build and validation entrypoint for Brave authored packs."""

from __future__ import annotations

from dataclasses import dataclass

from world.content import get_content_registry
from world.content.validation import validate_content_registry


@dataclass(frozen=True)
class ContentBuildResult:
    errors: tuple[str, ...]

    @property
    def ok(self):
        return not self.errors


def run_content_build(registry=None):
    """Load the live content registry and validate all authored domains."""

    registry = registry or get_content_registry()
    errors = tuple(validate_content_registry(registry))
    return ContentBuildResult(errors=errors)


def _iter_sources(registry):
    yield ("characters", registry.characters.source_path)
    yield ("items", registry.items.source_path)
    yield ("quests", registry.quests.source_path)
    yield ("world", registry.world.source_path)
    yield ("encounters", registry.encounters.source_path)
    yield ("dialogue", registry.dialogue.source_path)
    yield ("systems", registry.systems.source_path)


def main():
    registry = get_content_registry()
    result = run_content_build(registry)

    print("Brave content build")
    for domain, source_path in _iter_sources(registry):
        print(f"- {domain}: {source_path}")

    if result.ok:
        print("Content validation passed.")
        return 0

    print("Content validation failed:")
    for error in result.errors:
        print(f"- {error}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
