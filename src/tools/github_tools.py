"""LangChain tools for GitHub operations."""

from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

from langchain_core.tools import tool
from pydantic import Field

from src.services.github import GitHubService


def get_github_service() -> GitHubService:
    """Get or create GitHub service instance."""
    return GitHubService()


@tool
def get_commits(
    days: Annotated[int, Field(description="Number of days to look back", ge=1, le=365)] = 30,
    branch: Annotated[str, Field(description="Branch name")] = "main",
    owner: Annotated[Optional[str], Field(description="Repository owner (optional)")] = None,
    repo: Annotated[Optional[str], Field(description="Repository name (optional)")] = None,
    max_count: Annotated[int, Field(description="Maximum commits to fetch", ge=1, le=500)] = 100,
) -> str:
    """Get commits from a GitHub repository for a specified time period.

    Use this tool to retrieve a list of commits from the repository.
    Returns commit information including SHA, message, author, and date.

    Args:
        days: Number of days to look back from today.
        branch: Branch name to get commits from.
        owner: Repository owner. Uses default from env if not provided.
        repo: Repository name. Uses default from env if not provided.
        max_count: Maximum number of commits to retrieve.

    Returns:
        JSON string containing list of commits.
    """
    service = get_github_service()

    since = datetime.now(timezone.utc) - timedelta(days=days)
    until = datetime.now(timezone.utc)

    commits = service.get_commits(
        since=since,
        until=until,
        branch=branch,
        owner=owner,
        repo=repo,
        max_count=max_count,
    )

    if not commits:
        return f"No commits found in the last {days} days on branch '{branch}'."

    result_lines = [
        f"Found {len(commits)} commits in the last {days} days:",
        "",
    ]

    for commit in commits:
        # Get first line of commit message
        first_line = commit.message.split("\n")[0][:80]
        result_lines.append(
            f"- [{commit.sha[:7]}] {first_line} "
            f"(@{commit.author}, {commit.date.strftime('%Y-%m-%d')})"
        )

    return "\n".join(result_lines)


@tool
def get_commit_detail(
    sha: Annotated[str, Field(description="Commit SHA hash")],
    owner: Annotated[Optional[str], Field(description="Repository owner (optional)")] = None,
    repo: Annotated[Optional[str], Field(description="Repository name (optional)")] = None,
) -> str:
    """Get detailed information about a specific commit.

    Use this tool to get full details about a commit including:
    - Complete commit message
    - List of changed files with additions/deletions
    - Patch snippets for each file

    Args:
        sha: The commit SHA to get details for.
        owner: Repository owner. Uses default from env if not provided.
        repo: Repository name. Uses default from env if not provided.

    Returns:
        Detailed commit information as formatted string.
    """
    service = get_github_service()

    detail = service.get_commit_detail(sha=sha, owner=owner, repo=repo)

    lines = [
        f"## Commit: {detail.sha[:7]}",
        f"",
        f"**Author:** {detail.author} <{detail.author_email}>",
        f"**Date:** {detail.date.strftime('%Y-%m-%d %H:%M:%S')}",
        f"**URL:** {detail.url}",
        f"",
        f"### Message",
        f"```",
        detail.message,
        f"```",
        f"",
        f"### Stats",
        f"- Files changed: {detail.files_changed}",
        f"- Additions: +{detail.additions}",
        f"- Deletions: -{detail.deletions}",
        f"",
        f"### Changed Files",
    ]

    for file in detail.files:
        lines.append(
            f"- `{file['filename']}` ({file['status']}) "
            f"+{file['additions']}/-{file['deletions']}"
        )

    return "\n".join(lines)


@tool
def compare_refs(
    base: Annotated[str, Field(description="Base reference (branch, tag, or commit)")],
    head: Annotated[str, Field(description="Head reference (branch, tag, or commit)")],
    owner: Annotated[Optional[str], Field(description="Repository owner (optional)")] = None,
    repo: Annotated[Optional[str], Field(description="Repository name (optional)")] = None,
) -> str:
    """Compare two references (branches, tags, or commits).

    Use this tool to compare changes between two points in the repository.
    Useful for generating changelogs between releases or branches.

    Args:
        base: The base reference to compare from.
        head: The head reference to compare to.
        owner: Repository owner. Uses default from env if not provided.
        repo: Repository name. Uses default from env if not provided.

    Returns:
        Comparison summary including commits and file changes.
    """
    service = get_github_service()

    comparison = service.compare_refs(base=base, head=head, owner=owner, repo=repo)

    lines = [
        f"## Comparison: {base}...{head}",
        f"",
        f"**Status:** {comparison['status']}",
        f"**Ahead by:** {comparison['ahead_by']} commits",
        f"**Behind by:** {comparison['behind_by']} commits",
        f"**Total commits:** {comparison['total_commits']}",
        f"",
        f"### Commits",
    ]

    for commit in comparison["commits"][:20]:  # Limit to 20 commits
        first_line = commit.message.split("\n")[0][:60]
        lines.append(f"- [{commit.sha[:7]}] {first_line} (@{commit.author})")

    if len(comparison["commits"]) > 20:
        lines.append(f"- ... and {len(comparison['commits']) - 20} more commits")

    lines.extend([
        f"",
        f"### Changed Files ({len(comparison['files'])} files)",
    ])

    for file in comparison["files"][:30]:  # Limit to 30 files
        lines.append(
            f"- `{file['filename']}` ({file['status']}) "
            f"+{file['additions']}/-{file['deletions']}"
        )

    if len(comparison["files"]) > 30:
        lines.append(f"- ... and {len(comparison['files']) - 30} more files")

    return "\n".join(lines)


@tool
def get_merged_pull_requests(
    days: Annotated[int, Field(description="Number of days to look back", ge=1, le=365)] = 30,
    owner: Annotated[Optional[str], Field(description="Repository owner (optional)")] = None,
    repo: Annotated[Optional[str], Field(description="Repository name (optional)")] = None,
    max_count: Annotated[int, Field(description="Maximum PRs to fetch", ge=1, le=100)] = 50,
) -> str:
    """Get merged pull requests from a repository.

    Use this tool to get a list of recently merged pull requests.
    Useful for changelog generation as PRs often have better descriptions.

    Args:
        days: Number of days to look back.
        owner: Repository owner. Uses default from env if not provided.
        repo: Repository name. Uses default from env if not provided.
        max_count: Maximum number of PRs to fetch.

    Returns:
        List of merged pull requests with titles and labels.
    """
    service = get_github_service()

    since = datetime.now(timezone.utc) - timedelta(days=days)

    prs = service.get_merged_pull_requests(
        since=since,
        owner=owner,
        repo=repo,
        max_count=max_count,
    )

    if not prs:
        return f"No merged pull requests found in the last {days} days."

    lines = [
        f"Found {len(prs)} merged PRs in the last {days} days:",
        "",
    ]

    for pr in prs:
        labels_str = ", ".join(pr.labels) if pr.labels else "no labels"
        lines.append(
            f"- **#{pr.number}** {pr.title} "
            f"(@{pr.author}, {pr.merged_at.strftime('%Y-%m-%d')}) [{labels_str}]"
        )

    return "\n".join(lines)
