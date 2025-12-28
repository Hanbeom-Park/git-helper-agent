"""Model definitions for the Git Changelog Agent."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CommitInfo(BaseModel):
    """Represents a Git commit."""

    sha: str = Field(description="Commit SHA hash")
    message: str = Field(description="Commit message")
    author: str = Field(description="Author name")
    author_email: str = Field(description="Author email")
    date: datetime = Field(description="Commit date")
    url: str = Field(description="Commit URL on GitHub")
    files_changed: int = Field(default=0, description="Number of files changed")
    additions: int = Field(default=0, description="Lines added")
    deletions: int = Field(default=0, description="Lines deleted")


class CommitDetail(CommitInfo):
    """Detailed commit information including file changes."""

    files: list[dict] = Field(default_factory=list, description="List of changed files")
    parents: list[str] = Field(default_factory=list, description="Parent commit SHAs")


class PullRequestInfo(BaseModel):
    """Represents a merged Pull Request."""

    number: int = Field(description="PR number")
    title: str = Field(description="PR title")
    body: Optional[str] = Field(default=None, description="PR description")
    author: str = Field(description="PR author")
    merged_at: datetime = Field(description="Merge date")
    url: str = Field(description="PR URL on GitHub")
    labels: list[str] = Field(default_factory=list, description="PR labels")


class ChangelogEntry(BaseModel):
    """Represents a changelog entry."""

    category: str = Field(description="Category: feat, fix, docs, refactor, etc.")
    description: str = Field(description="Description of the change")
    commit_sha: Optional[str] = Field(default=None, description="Related commit SHA")
    pr_number: Optional[int] = Field(default=None, description="Related PR number")
    author: str = Field(description="Author of the change")
    date: datetime = Field(description="Date of the change")


class Changelog(BaseModel):
    """Represents a complete changelog."""

    repo_name: str = Field(description="Repository name")
    start_date: datetime = Field(description="Changelog start date")
    end_date: datetime = Field(description="Changelog end date")
    entries: list[ChangelogEntry] = Field(default_factory=list, description="Changelog entries")

    def to_markdown(self) -> str:
        """Convert changelog to markdown format."""
        lines = [
            f"## Changelog",
            f"",
            f"**Period**: {self.start_date.strftime('%Y-%m-%d')} ~ {self.end_date.strftime('%Y-%m-%d')}",
            f"",
        ]

        # Group by category
        categories: dict[str, list[ChangelogEntry]] = {}
        for entry in self.entries:
            if entry.category not in categories:
                categories[entry.category] = []
            categories[entry.category].append(entry)

        # Category display order and labels
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

        for cat_key in category_labels:
            if cat_key in categories:
                lines.append(f"### {category_labels[cat_key]}")
                lines.append("")
                for entry in sorted(categories[cat_key], key=lambda x: x.date, reverse=True):
                    ref = ""
                    if entry.pr_number:
                        ref = f" (#{entry.pr_number})"
                    elif entry.commit_sha:
                        ref = f" ({entry.commit_sha[:7]})"
                    lines.append(f"- {entry.description}{ref} - @{entry.author}")
                lines.append("")

        return "\n".join(lines)
