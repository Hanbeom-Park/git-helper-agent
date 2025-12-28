"""Main entry point for Git Changelog Agent."""

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add project root to path for direct execution
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
from rich.console import Console
from rich.logging import RichHandler
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

# Load environment variables
load_dotenv()

console = Console()
logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True, show_path=False)],
    )

    if verbose:
        logging.getLogger("langchain").setLevel(logging.DEBUG)
        logging.getLogger("langgraph").setLevel(logging.DEBUG)
    else:
        logging.getLogger("langchain").setLevel(logging.WARNING)
        logging.getLogger("langgraph").setLevel(logging.WARNING)

    return logging.getLogger(__name__)


def check_env_variables() -> bool:
    """Check required environment variables."""
    if not os.getenv("GITHUB_TOKEN"):
        console.print("[red]Error: GITHUB_TOKEN 환경변수가 설정되지 않았습니다.[/red]")
        return False

    provider = os.getenv("LLM_PROVIDER", "anthropic").lower()
    if provider == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
        console.print("[red]Error: ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다.[/red]")
        return False
    elif provider == "google" and not os.getenv("GOOGLE_API_KEY"):
        console.print("[red]Error: GOOGLE_API_KEY 환경변수가 설정되지 않았습니다.[/red]")
        return False

    return True


# =============================================================================
# Batch Mode Functions
# =============================================================================

def get_llm_for_summary():
    """Get LLM instance for summarization."""
    from langchain_core.language_models import BaseChatModel

    provider = os.getenv("LLM_PROVIDER", "anthropic").lower()

    if provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=os.getenv("GOOGLE_MODEL", "gemini-2.0-flash"),
            google_api_key=os.getenv("GOOGLE_API_KEY"),
        )
    else:
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
            api_key=os.getenv("ANTHROPIC_API_KEY"),
        )


def summarize_commit_changes(llm, commit_detail: dict) -> str:
    """Use LLM to summarize commit changes.

    Args:
        llm: LLM instance for summarization.
        commit_detail: Commit detail from GitHub service.

    Returns:
        AI-generated summary of the changes.
    """
    files_info = []
    for f in commit_detail.files[:10]:  # Limit to 10 files
        file_info = f"- {f['filename']} ({f['status']}): +{f['additions']}/-{f['deletions']}"
        if f.get('patch'):
            # Include first 200 chars of patch for context
            patch_preview = f['patch'][:200].replace('\n', ' ')
            file_info += f"\n  Patch: {patch_preview}..."
        files_info.append(file_info)

    prompt = f"""다음 Git 커밋의 변경사항을 분석하고, 실제 어떤 변경이 이루어졌는지 한국어로 간결하게 요약해주세요.
핵심적인 변경 내용만 1-2문장으로 설명해주세요.

커밋 메시지: {commit_detail.message}
변경된 파일 수: {commit_detail.files_changed}
추가된 라인: +{commit_detail.additions}
삭제된 라인: -{commit_detail.deletions}

변경된 파일 목록:
{chr(10).join(files_info)}

요약 (1-2문장):"""

    try:
        response = llm.invoke(prompt)
        return response.content.strip()
    except Exception as e:
        return f"{commit_detail.message.split(chr(10))[0][:60]}"


def run_batch(
    days: int = 1,
    branch: str = "main",
    owner: str | None = None,
    repo: str | None = None,
    update_readme: bool = False,
    output_file: str | None = None,
    verbose: bool = False,
) -> int:
    """Run changelog generation in batch mode.

    Args:
        days: Number of days to look back for commits.
        branch: Branch name to get commits from.
        owner: Repository owner. Uses env var if not provided.
        repo: Repository name. Uses env var if not provided.
        update_readme: Whether to update README.md with changelog.
        output_file: Optional file path to save changelog.
        verbose: Enable verbose logging.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    from src.services.github import GitHubService
    from src.tools.changelog_tools import categorize_commit_message

    owner = owner or os.getenv("GITHUB_OWNER")
    repo = repo or os.getenv("GITHUB_REPO")

    if not owner or not repo:
        console.print("[red]Error: GITHUB_OWNER와 GITHUB_REPO가 필요합니다.[/red]")
        return 1

    console.print(f"[bold blue]🔧 Git Changelog Agent - Batch Mode[/bold blue]")
    console.print(f"[dim]저장소: {owner}/{repo}[/dim]")
    console.print(f"[dim]기간: 최근 {days}일[/dim]")
    console.print(f"[dim]브랜치: {branch}[/dim]")
    console.print()

    try:
        # Initialize GitHub service
        service = GitHubService()

        # Initialize LLM for summarization
        console.print("[dim]LLM 초기화 중...[/dim]")
        llm = get_llm_for_summary()
        console.print(f"[green]✓ LLM 준비 완료 ({os.getenv('LLM_PROVIDER', 'anthropic')})[/green]")

        # Get commits
        since = datetime.now(timezone.utc) - timedelta(days=days)
        until = datetime.now(timezone.utc)

        console.print("[dim]커밋 조회 중...[/dim]")
        commits = service.get_commits(
            since=since,
            until=until,
            branch=branch,
            owner=owner,
            repo=repo,
            max_count=500,
        )

        if not commits:
            console.print(f"[yellow]최근 {days}일간 커밋이 없습니다.[/yellow]")
            return 0

        console.print(f"[green]✓ {len(commits)}개 커밋 발견[/green]")

        # Get commit details and summarize with LLM
        console.print("[dim]커밋 상세 내용 분석 및 AI 요약 중...[/dim]")
        categorized: dict[str, list] = {}

        for i, commit in enumerate(commits):
            console.print(f"[dim]  [{i+1}/{len(commits)}] {commit.sha[:7]} 분석 중...[/dim]")

            # Get commit details
            try:
                detail = service.get_commit_detail(sha=commit.sha, owner=owner, repo=repo)

                # Summarize with LLM
                summary = summarize_commit_changes(llm, detail)
            except Exception as e:
                if verbose:
                    console.print(f"[yellow]    경고: 상세 정보 조회 실패 - {e}[/yellow]")
                summary = commit.message.split("\n")[0][:80]

            # Categorize commit
            category = categorize_commit_message.invoke({"message": commit.message})
            if category not in categorized:
                categorized[category] = []

            categorized[category].append({
                "message": commit.message.split("\n")[0][:80],
                "summary": summary,
                "sha": commit.sha[:7],
                "author": commit.author,
                "date": commit.date.strftime("%Y-%m-%d"),
            })

        console.print(f"[green]✓ AI 요약 완료[/green]")

        # Generate changelog markdown
        console.print("[dim]Changelog 생성 중...[/dim]")
        changelog_md = generate_changelog_markdown(
            categorized=categorized,
            start_date=since.strftime("%Y-%m-%d"),
            end_date=until.strftime("%Y-%m-%d"),
        )

        # Display changelog
        console.print()
        console.print(Panel(Markdown(changelog_md), title="Generated Changelog", border_style="green"))

        # Save to file if specified
        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(changelog_md)
            console.print(f"[green]✓ Changelog 저장됨: {output_file}[/green]")

        # Update README if requested
        if update_readme:
            console.print("[dim]README.md 업데이트 중...[/dim]")
            result = update_readme_with_changelog_batch(
                service=service,
                changelog_md=changelog_md,
                owner=owner,
                repo=repo,
                branch=branch,
            )
            if result["success"]:
                console.print(f"[green]✓ README.md 업데이트 완료![/green]")
                console.print(f"[dim]Commit: {result['commit_sha'][:7]}[/dim]")
                console.print(f"[dim]URL: {result['commit_url']}[/dim]")
            else:
                console.print(f"[red]README.md 업데이트 실패[/red]")
                return 1

        console.print()
        console.print("[bold green]✓ 배치 작업 완료![/bold green]")
        return 0

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        if verbose:
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        return 1


def generate_changelog_markdown(
    categorized: dict[str, list],
    start_date: str,
    end_date: str,
) -> str:
    """Generate changelog markdown from categorized commits with AI summaries."""
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

    lines = [
        f"## Changelog",
        f"",
        f"**Period:** {start_date} ~ {end_date}",
        f"",
        f"> 🤖 *AI가 분석한 변경사항 요약*",
        f"",
    ]

    for cat_key in category_labels:
        if cat_key in categorized and categorized[cat_key]:
            lines.append(f"### {category_labels[cat_key]}")
            lines.append("")
            for commit in categorized[cat_key]:
                # Use AI summary if available, otherwise fallback to commit message
                summary = commit.get('summary', commit['message'])
                lines.append(f"- **{commit['message'][:50]}** ({commit['sha']})")
                lines.append(f"  - {summary}")
                lines.append(f"  - *@{commit['author']} ({commit['date']})*")
                lines.append("")

    return "\n".join(lines)


def update_readme_with_changelog_batch(
    service,
    changelog_md: str,
    owner: str,
    repo: str,
    branch: str = "main",
) -> dict:
    """Update README.md with changelog content."""
    import re

    current_content, _ = service.get_readme_content(owner=owner, repo=repo, branch=branch)

    changelog_section = f"## Changelog\n\n{changelog_md.replace('## Changelog', '').strip()}"

    if not current_content:
        new_content = f"# {repo}\n\n{changelog_section}"
    else:
        changelog_pattern = r"(## Changelog.*?)(?=\n## |\n# |\Z)"
        if re.search(changelog_pattern, current_content, re.DOTALL | re.IGNORECASE):
            new_content = re.sub(
                changelog_pattern,
                changelog_section + "\n",
                current_content,
                flags=re.DOTALL | re.IGNORECASE,
            )
        else:
            new_content = current_content.rstrip() + "\n\n" + changelog_section

    result = service.update_readme(
        content=new_content,
        message=f"docs: Update changelog ({datetime.now().strftime('%Y-%m-%d')})",
        owner=owner,
        repo=repo,
        branch=branch,
    )

    return result


# =============================================================================
# Interactive Mode Functions
# =============================================================================

def print_welcome():
    """Print welcome message."""
    console.print(
        Panel.fit(
            "[bold blue]🔧 Git Changelog Agent[/bold blue]\n\n"
            "GitHub 저장소의 커밋을 분석하고 Changelog를 생성하는 AI Agent입니다.\n\n"
            "[dim]Commands:[/dim]\n"
            "  • [green]exit[/green] / [green]quit[/green] - 종료\n"
            "  • [green]help[/green] - 도움말\n"
            "  • [green]clear[/green] - 화면 지우기",
            title="Welcome",
            border_style="blue",
        )
    )


def print_help():
    """Print help message."""
    help_text = """
## 사용 예시

### 커밋 조회
- "지난 30일간의 커밋을 보여줘"
- "최근 일주일 커밋을 분석해줘"

### Changelog 생성
- "지난 한 달 커밋으로 changelog를 만들어줘"
- "v1.0.0과 v1.1.0 사이의 변경사항을 정리해줘"

### README 업데이트
- "changelog를 README.md에 추가해줘"
- "지난 2주 변경사항을 README에 반영해줘"

## 환경 변수
- `GITHUB_TOKEN`: GitHub Personal Access Token (필수)
- `LLM_PROVIDER`: LLM 제공자 선택 - 'anthropic' 또는 'google' (기본: anthropic)
- `ANTHROPIC_API_KEY`: Anthropic API Key (LLM_PROVIDER=anthropic일 때 필수)
- `GOOGLE_API_KEY`: Google API Key (LLM_PROVIDER=google일 때 필수)
"""
    console.print(Markdown(help_text))


async def run_interactive(verbose: bool = False):
    """Run interactive chat mode."""
    from src.agent import create_changelog_agent, run_agent_sync

    if not check_env_variables():
        return

    provider = os.getenv("LLM_PROVIDER", "anthropic").lower()

    try:
        console.print(f"[dim]Agent 초기화 중... (Provider: {provider})[/dim]")
        agent = create_changelog_agent()
        console.print("[green]✓ Agent 준비 완료![/green]\n")
    except Exception as e:
        console.print(f"[red]Agent 초기화 실패: {e}[/red]")
        return

    owner = os.getenv("GITHUB_OWNER")
    repo = os.getenv("GITHUB_REPO")
    if owner and repo:
        console.print(f"[dim]기본 저장소: {owner}/{repo}[/dim]\n")

    while True:
        try:
            user_input = Prompt.ask("\n[bold cyan]You[/bold cyan]")

            if not user_input.strip():
                continue

            if user_input.lower() in ["exit", "quit", "종료"]:
                console.print("[dim]Goodbye! 👋[/dim]")
                break

            if user_input.lower() == "help":
                print_help()
                continue

            if user_input.lower() == "clear":
                console.clear()
                print_welcome()
                continue

            console.print("\n[dim]처리 중...[/dim]")

            result = run_agent_sync(agent, user_input)

            if "messages" in result:
                if verbose:
                    console.print("\n[bold yellow]--- Agent 실행 로그 ---[/bold yellow]")
                    for msg in result["messages"]:
                        if hasattr(msg, "type"):
                            if msg.type == "ai" and hasattr(msg, "tool_calls") and msg.tool_calls:
                                for tool_call in msg.tool_calls:
                                    console.print(f"[cyan]Tool 호출:[/cyan] {tool_call.get('name', 'unknown')}")
                            elif msg.type == "tool":
                                tool_name = getattr(msg, "name", "unknown")
                                console.print(f"[green]Tool 결과:[/green] {tool_name}")
                    console.print("[bold yellow]--- 로그 끝 ---[/bold yellow]\n")

                for msg in reversed(result["messages"]):
                    if hasattr(msg, "content") and msg.type == "ai":
                        console.print("\n[bold green]Agent[/bold green]")
                        if isinstance(msg.content, str):
                            console.print(Markdown(msg.content))
                        elif isinstance(msg.content, list):
                            for item in msg.content:
                                if isinstance(item, dict) and "text" in item:
                                    console.print(Markdown(item["text"]))
                                elif isinstance(item, str):
                                    console.print(Markdown(item))
                        break
            else:
                console.print(f"\n[yellow]Response: {result}[/yellow]")

        except KeyboardInterrupt:
            console.print("\n[dim]Interrupted. Type 'exit' to quit.[/dim]")
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]")
            if verbose:
                import traceback
                console.print(f"[dim]{traceback.format_exc()}[/dim]")


# =============================================================================
# Main Entry Point
# =============================================================================

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Git Changelog Agent - AI 기반 Changelog 자동 생성 도구",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 대화형 모드 실행
  python -m src.main

  # 최근 1일 커밋으로 changelog 생성 (배치 모드)
  python -m src.main --batch

  # 최근 7일 커밋으로 changelog 생성 및 README 업데이트
  python -m src.main --batch --days 7 --update-readme

  # 특정 저장소에서 changelog 생성 후 파일로 저장
  python -m src.main --batch --owner myuser --repo myrepo --output changelog.md
        """,
    )

    # Mode selection
    parser.add_argument(
        "--batch", "-b",
        action="store_true",
        help="배치 모드로 실행 (자동으로 changelog 생성)",
    )

    # Batch mode options
    parser.add_argument(
        "--days", "-d",
        type=int,
        default=1,
        help="조회할 기간 (일수, 기본값: 1)",
    )
    parser.add_argument(
        "--branch",
        type=str,
        default="main",
        help="조회할 브랜치 (기본값: main)",
    )
    parser.add_argument(
        "--owner",
        type=str,
        help="GitHub 저장소 소유자 (기본값: GITHUB_OWNER 환경변수)",
    )
    parser.add_argument(
        "--repo",
        type=str,
        help="GitHub 저장소 이름 (기본값: GITHUB_REPO 환경변수)",
    )
    parser.add_argument(
        "--update-readme", "-u",
        action="store_true",
        help="README.md에 changelog 자동 업데이트",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Changelog를 저장할 파일 경로",
    )

    # Common options
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="상세 로그 출력",
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()

    setup_logging(args.verbose)

    if args.batch:
        # Batch mode
        exit_code = run_batch(
            days=args.days,
            branch=args.branch,
            owner=args.owner,
            repo=args.repo,
            update_readme=args.update_readme,
            output_file=args.output,
            verbose=args.verbose,
        )
        sys.exit(exit_code)
    else:
        # Interactive mode
        if args.verbose:
            console.print("[dim]Verbose 모드 활성화됨[/dim]\n")

        print_welcome()
        asyncio.run(run_interactive(args.verbose))


if __name__ == "__main__":
    main()
