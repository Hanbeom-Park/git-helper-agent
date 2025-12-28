"""GitHub API service client using PyGithub."""

import os
from datetime import datetime, timezone
from typing import Optional

from github import Auth, Github
from github.Commit import Commit
from github.GithubException import GithubException, UnknownObjectException
from github.PullRequest import PullRequest
from github.Repository import Repository

from src.models import CommitDetail, CommitInfo, PullRequestInfo


class GitHubService:
    """GitHub API client wrapper."""

    def __init__(
        self,
        token: Optional[str] = None,
        owner: Optional[str] = None,
        repo: Optional[str] = None,
    ):
        """Initialize GitHub service.

        Args:
            token: GitHub Personal Access Token. Defaults to GITHUB_TOKEN env var.
            owner: Repository owner. Defaults to GITHUB_OWNER env var.
            repo: Repository name. Defaults to GITHUB_REPO env var.
        """
        self.token = token or os.getenv("GITHUB_TOKEN")
        if not self.token:
            raise ValueError("GitHub token is required. Set GITHUB_TOKEN env var or pass token.")

        self.owner = owner or os.getenv("GITHUB_OWNER")
        self.repo_name = repo or os.getenv("GITHUB_REPO")

        auth = Auth.Token(self.token)
        self.client = Github(auth=auth)

    def get_repository(self, owner: Optional[str] = None, repo: Optional[str] = None) -> Repository:
        """Get a GitHub repository.

        Args:
            owner: Repository owner. Uses default if not provided.
            repo: Repository name. Uses default if not provided.

        Returns:
            GitHub Repository object.
        """
        owner = owner or self.owner
        repo = repo or self.repo_name

        if not owner or not repo:
            raise ValueError("Repository owner and name are required.")

        repo_full_name = f"{owner}/{repo}"
        try:
            return self.client.get_repo(repo_full_name)
        except UnknownObjectException:
            raise ValueError(
                f"Repository '{repo_full_name}' not found. "
                f"Please check:\n"
                f"  1. GITHUB_OWNER and GITHUB_REPO are correct\n"
                f"  2. Repository exists at github.com/{repo_full_name}\n"
                f"  3. Your GITHUB_TOKEN has access to this repository"
            )
        except GithubException as e:
            raise ValueError(f"GitHub API error: {e.data.get('message', str(e))}")

    def get_commits(
        self,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        branch: str = "main",
        owner: Optional[str] = None,
        repo: Optional[str] = None,
        max_count: int = 100,
    ) -> list[CommitInfo]:
        """Get commits from a repository.

        Args:
            since: Start date for commit range.
            until: End date for commit range.
            branch: Branch name. Defaults to 'main'.
            owner: Repository owner.
            repo: Repository name.
            max_count: Maximum number of commits to fetch.

        Returns:
            List of CommitInfo objects.
        """
        repository = self.get_repository(owner, repo)

        kwargs = {"sha": branch}
        if since:
            kwargs["since"] = since
        if until:
            kwargs["until"] = until

        commits: list[CommitInfo] = []
        for i, commit in enumerate(repository.get_commits(**kwargs)):
            if i >= max_count:
                break

            commits.append(self._convert_commit(commit))

        return commits

    def get_commit_detail(
        self,
        sha: str,
        owner: Optional[str] = None,
        repo: Optional[str] = None,
    ) -> CommitDetail:
        """Get detailed information about a specific commit.

        Args:
            sha: Commit SHA.
            owner: Repository owner.
            repo: Repository name.

        Returns:
            CommitDetail object with file changes.
        """
        repository = self.get_repository(owner, repo)
        commit = repository.get_commit(sha)

        # Convert PaginatedList to list
        files = []
        for file in commit.files:
            files.append({
                "filename": file.filename,
                "status": file.status,
                "additions": file.additions,
                "deletions": file.deletions,
                "changes": file.changes,
                "patch": file.patch[:500] if file.patch else None,  # Truncate large patches
            })

        return CommitDetail(
            sha=commit.sha,
            message=commit.commit.message,
            author=commit.commit.author.name,
            author_email=commit.commit.author.email,
            date=commit.commit.author.date,
            url=commit.html_url,
            files_changed=len(files),  # Use len of converted list
            additions=commit.stats.additions,
            deletions=commit.stats.deletions,
            files=files,
            parents=[p.sha for p in commit.parents],
        )

    def compare_refs(
        self,
        base: str,
        head: str,
        owner: Optional[str] = None,
        repo: Optional[str] = None,
    ) -> dict:
        """Compare two references (branches, tags, or commits).

        Args:
            base: Base reference.
            head: Head reference.
            owner: Repository owner.
            repo: Repository name.

        Returns:
            Comparison result with commits and file changes.
        """
        repository = self.get_repository(owner, repo)
        comparison = repository.compare(base, head)

        return {
            "status": comparison.status,
            "ahead_by": comparison.ahead_by,
            "behind_by": comparison.behind_by,
            "total_commits": comparison.total_commits,
            "commits": [self._convert_commit(c) for c in comparison.commits],
            "files": [
                {
                    "filename": f.filename,
                    "status": f.status,
                    "additions": f.additions,
                    "deletions": f.deletions,
                }
                for f in comparison.files
            ],
        }

    def get_merged_pull_requests(
        self,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        owner: Optional[str] = None,
        repo: Optional[str] = None,
        max_count: int = 50,
    ) -> list[PullRequestInfo]:
        """Get merged pull requests.

        Args:
            since: Start date for PR range.
            until: End date for PR range.
            owner: Repository owner.
            repo: Repository name.
            max_count: Maximum number of PRs to fetch.

        Returns:
            List of PullRequestInfo objects.
        """
        repository = self.get_repository(owner, repo)

        prs: list[PullRequestInfo] = []
        for i, pr in enumerate(repository.get_pulls(state="closed", sort="updated", direction="desc")):
            if i >= max_count:
                break

            if not pr.merged_at:
                continue

            # Make merged_at timezone-aware if needed
            merged_at = pr.merged_at
            if merged_at.tzinfo is None:
                merged_at = merged_at.replace(tzinfo=timezone.utc)

            # Filter by date range (make since/until timezone-aware if needed)
            if since:
                since_aware = since if since.tzinfo else since.replace(tzinfo=timezone.utc)
                if merged_at < since_aware:
                    continue
            if until:
                until_aware = until if until.tzinfo else until.replace(tzinfo=timezone.utc)
                if merged_at > until_aware:
                    break

            prs.append(self._convert_pull_request(pr))

        return prs

    def get_readme_content(
        self,
        owner: Optional[str] = None,
        repo: Optional[str] = None,
        branch: str = "main",
    ) -> tuple[str, str]:
        """Get README.md content.

        Args:
            owner: Repository owner.
            repo: Repository name.
            branch: Branch name.

        Returns:
            Tuple of (content, sha).
        """
        repository = self.get_repository(owner, repo)

        try:
            readme = repository.get_contents("README.md", ref=branch)
            if isinstance(readme, list):
                readme = readme[0]
            return readme.decoded_content.decode("utf-8"), readme.sha
        except Exception:
            return "", ""

    def update_readme(
        self,
        content: str,
        message: str = "docs: Update changelog in README",
        owner: Optional[str] = None,
        repo: Optional[str] = None,
        branch: str = "main",
    ) -> dict:
        """Update README.md content.

        Args:
            content: New README content.
            message: Commit message.
            owner: Repository owner.
            repo: Repository name.
            branch: Branch name.

        Returns:
            Update result with commit info.
        """
        repository = self.get_repository(owner, repo)

        try:
            readme = repository.get_contents("README.md", ref=branch)
            if isinstance(readme, list):
                readme = readme[0]

            result = repository.update_file(
                path="README.md",
                message=message,
                content=content,
                sha=readme.sha,
                branch=branch,
            )
        except Exception:
            # Create new README if it doesn't exist
            result = repository.create_file(
                path="README.md",
                message=message,
                content=content,
                branch=branch,
            )

        return {
            "success": True,
            "commit_sha": result["commit"].sha,
            "commit_url": result["commit"].html_url,
        }

    def _convert_commit(self, commit: Commit) -> CommitInfo:
        """Convert GitHub Commit to CommitInfo."""
        # Get file count safely (PaginatedList doesn't support len())
        try:
            files_changed = commit.stats.total if commit.stats else 0
        except Exception:
            files_changed = 0

        return CommitInfo(
            sha=commit.sha,
            message=commit.commit.message,
            author=commit.commit.author.name,
            author_email=commit.commit.author.email,
            date=commit.commit.author.date,
            url=commit.html_url,
            files_changed=files_changed,
            additions=commit.stats.additions if commit.stats else 0,
            deletions=commit.stats.deletions if commit.stats else 0,
        )

    def _convert_pull_request(self, pr: PullRequest) -> PullRequestInfo:
        """Convert GitHub PullRequest to PullRequestInfo."""
        return PullRequestInfo(
            number=pr.number,
            title=pr.title,
            body=pr.body,
            author=pr.user.login,
            merged_at=pr.merged_at,
            url=pr.html_url,
            labels=[label.name for label in pr.labels],
        )
