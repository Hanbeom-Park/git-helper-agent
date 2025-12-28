"""LangChain tools for Git Changelog Agent."""

from src.tools.changelog_tools import (
    categorize_commit_message,
    format_changelog_markdown,
    get_readme_content,
    update_readme_with_changelog,
)
from src.tools.github_tools import (
    compare_refs,
    get_commit_detail,
    get_commits,
    get_merged_pull_requests,
)

# All available tools
ALL_TOOLS = [
    # GitHub tools
    get_commits,
    get_commit_detail,
    compare_refs,
    get_merged_pull_requests,
    # Changelog tools
    get_readme_content,
    update_readme_with_changelog,
    format_changelog_markdown,
    categorize_commit_message,
]

__all__ = [
    "get_commits",
    "get_commit_detail",
    "compare_refs",
    "get_merged_pull_requests",
    "get_readme_content",
    "update_readme_with_changelog",
    "format_changelog_markdown",
    "categorize_commit_message",
    "ALL_TOOLS",
]
