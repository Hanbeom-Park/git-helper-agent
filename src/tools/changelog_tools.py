"""LangChain tools for changelog generation and README updates."""

import re
from datetime import datetime
from typing import Annotated, Optional

from langchain_core.tools import tool
from pydantic import Field

from src.services.github import GitHubService


def get_github_service() -> GitHubService:
    """Get or create GitHub service instance."""
    return GitHubService()


@tool
def get_readme_content(
    owner: Annotated[Optional[str], Field(description="Repository owner (optional)")] = None,
    repo: Annotated[Optional[str], Field(description="Repository name (optional)")] = None,
    branch: Annotated[str, Field(description="Branch name")] = "main",
) -> str:
    """Get the current content of README.md from the repository.

    Use this tool to read the current README before updating it.
    This helps preserve existing content and find the right place for changelog.

    Args:
        owner: Repository owner. Uses default from env if not provided.
        repo: Repository name. Uses default from env if not provided.
        branch: Branch name to read from.

    Returns:
        Current README.md content.
    """
    service = get_github_service()

    content, sha = service.get_readme_content(owner=owner, repo=repo, branch=branch)

    if not content:
        return "README.md not found or empty."

    return f"Current README.md content:\n\n```markdown\n{content}\n```"


@tool
def update_readme_with_changelog(
    changelog_markdown: Annotated[str, Field(description="Changelog content in markdown format")],
    section_title: Annotated[str, Field(description="Section title for changelog")] = "## Changelog",
    owner: Annotated[Optional[str], Field(description="Repository owner (optional)")] = None,
    repo: Annotated[Optional[str], Field(description="Repository name (optional)")] = None,
    branch: Annotated[str, Field(description="Branch name")] = "main",
    commit_message: Annotated[str, Field(description="Commit message")] = "docs: Update changelog",
) -> str:
    """Update README.md with new changelog content.

    This tool updates the README.md file in the repository by:
    1. Finding existing changelog section (if any)
    2. Replacing or appending the new changelog
    3. Committing the changes

    Args:
        changelog_markdown: The changelog content to add (in markdown).
        section_title: The title/header for the changelog section.
        owner: Repository owner. Uses default from env if not provided.
        repo: Repository name. Uses default from env if not provided.
        branch: Branch name to update.
        commit_message: Commit message for the update.

    Returns:
        Result of the update operation.
    """
    service = get_github_service()

    # Get current README content
    current_content, _ = service.get_readme_content(owner=owner, repo=repo, branch=branch)

    # Prepare the changelog section
    changelog_section = f"{section_title}\n\n{changelog_markdown}"

    if not current_content:
        # Create new README with changelog
        new_content = f"# Project\n\n{changelog_section}"
    else:
        # Try to find and replace existing changelog section
        # Look for ## Changelog or similar headers
        changelog_pattern = r"(## Changelog.*?)(?=\n## |\n# |\Z)"

        if re.search(changelog_pattern, current_content, re.DOTALL | re.IGNORECASE):
            # Replace existing changelog
            new_content = re.sub(
                changelog_pattern,
                changelog_section + "\n",
                current_content,
                flags=re.DOTALL | re.IGNORECASE,
            )
        else:
            # Append changelog at the end
            new_content = current_content.rstrip() + "\n\n" + changelog_section

    # Update the file
    result = service.update_readme(
        content=new_content,
        message=commit_message,
        owner=owner,
        repo=repo,
        branch=branch,
    )

    if result["success"]:
        return (
            f"✅ README.md updated successfully!\n\n"
            f"**Commit:** {result['commit_sha'][:7]}\n"
            f"**URL:** {result['commit_url']}"
        )
    else:
        return "❌ Failed to update README.md."


@tool
def format_changelog_markdown(
    entries_json: Annotated[str, Field(description="JSON string of changelog entries")],
    period_start: Annotated[str, Field(description="Start date (YYYY-MM-DD)")],
    period_end: Annotated[str, Field(description="End date (YYYY-MM-DD)")],
) -> str:
    """Format changelog entries into a well-structured markdown.

    Use this tool to format raw changelog entries into proper markdown.
    The tool organizes entries by category with proper formatting.

    Expected JSON format for entries:
    [
        {
            "category": "feat|fix|docs|refactor|perf|test|chore|style|ci|other",
            "description": "Description of the change",
            "author": "username",
            "reference": "#123 or abc1234"
        }
    ]

    Args:
        entries_json: JSON string containing changelog entries.
        period_start: Start date of the changelog period.
        period_end: End date of the changelog period.

    Returns:
        Formatted markdown changelog.
    """
    import json

    try:
        entries = json.loads(entries_json)
    except json.JSONDecodeError as e:
        return f"Error parsing JSON: {e}"

    # Category display settings
    category_labels = {
        "feat": "✨ Features",
        "fix": "🐛 Bug Fixes",
        "docs": "📚 Documentation",
        "refactor": "♻️ Refactoring",
        "perf": "⚡ Performance",
        "test": "✅ Tests",
        "chore": "🔧 Chores",
        "style": "💄 Styles",
        "ci": "👷 CI/CD",
        "other": "📦 Other Changes",
    }

    # Group entries by category
    grouped: dict[str, list] = {}
    for entry in entries:
        cat = entry.get("category", "other").lower()
        if cat not in category_labels:
            cat = "other"
        if cat not in grouped:
            grouped[cat] = []
        grouped[cat].append(entry)

    # Build markdown
    lines = [
        f"**Period:** {period_start} ~ {period_end}",
        "",
    ]

    # Output in category order
    for cat_key in category_labels:
        if cat_key in grouped:
            lines.append(f"### {category_labels[cat_key]}")
            lines.append("")
            for entry in grouped[cat_key]:
                ref = entry.get("reference", "")
                ref_str = f" ({ref})" if ref else ""
                author = entry.get("author", "unknown")
                lines.append(f"- {entry['description']}{ref_str} - @{author}")
            lines.append("")

    return "\n".join(lines)


@tool
def categorize_commit_message(
    message: Annotated[str, Field(description="Commit message to categorize")],
) -> str:
    """Categorize a commit message based on conventional commit format.

    Analyzes commit message and returns the appropriate category.
    Supports conventional commit format (feat:, fix:, etc.) and
    keyword-based detection for other formats.

    Args:
        message: The commit message to analyze.

    Returns:
        Category string: feat, fix, docs, refactor, perf, test, chore, style, ci, or other.
    """
    message_lower = message.lower().strip()

    # Conventional commit prefixes
    prefix_map = {
        "feat": "feat",
        "feature": "feat",
        "fix": "fix",
        "bugfix": "fix",
        "hotfix": "fix",
        "docs": "docs",
        "doc": "docs",
        "refactor": "refactor",
        "perf": "perf",
        "performance": "perf",
        "test": "test",
        "tests": "test",
        "chore": "chore",
        "style": "style",
        "ci": "ci",
        "build": "chore",
    }

    # Check conventional commit format
    for prefix, category in prefix_map.items():
        if message_lower.startswith(f"{prefix}:") or message_lower.startswith(f"{prefix}("):
            return category

    # Keyword-based detection
    keywords = {
        "feat": ["add", "new", "implement", "create", "introduce"],
        "fix": ["fix", "bug", "resolve", "patch", "correct", "repair"],
        "docs": ["readme", "document", "docs", "comment", "changelog"],
        "refactor": ["refactor", "restructure", "reorganize", "clean"],
        "perf": ["performance", "optimize", "speed", "fast", "improve performance"],
        "test": ["test", "spec", "coverage"],
        "chore": ["update", "upgrade", "bump", "dependency", "deps", "merge"],
        "style": ["format", "style", "lint", "prettier", "eslint"],
        "ci": ["ci", "pipeline", "workflow", "action", "deploy"],
    }

    for category, words in keywords.items():
        for word in words:
            if word in message_lower:
                return category

    return "other"
