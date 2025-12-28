"""Main entry point for Git Changelog Agent."""

import asyncio
import logging
import os
import sys

from dotenv import load_dotenv
from rich.console import Console
from rich.logging import RichHandler
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

# Load environment variables
load_dotenv()

console = Console()


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO

    # Configure root logger
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True, show_path=False)],
    )

    # Set LangChain logging
    if verbose:
        logging.getLogger("langchain").setLevel(logging.DEBUG)
        logging.getLogger("langgraph").setLevel(logging.DEBUG)
    else:
        logging.getLogger("langchain").setLevel(logging.WARNING)
        logging.getLogger("langgraph").setLevel(logging.WARNING)

    return logging.getLogger(__name__)


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

### 브랜치/태그 비교
- "main과 develop 브랜치를 비교해줘"
- "v1.0.0과 현재 main의 차이를 보여줘"

## 환경 변수
- `GITHUB_TOKEN`: GitHub Personal Access Token (필수)
- `LLM_PROVIDER`: LLM 제공자 선택 - 'anthropic' 또는 'google' (기본: anthropic)
- `ANTHROPIC_API_KEY`: Anthropic API Key (LLM_PROVIDER=anthropic일 때 필수)
- `GOOGLE_API_KEY`: Google API Key (LLM_PROVIDER=google일 때 필수)
- `GITHUB_OWNER`: 기본 저장소 소유자 (선택)
- `GITHUB_REPO`: 기본 저장소 이름 (선택)
"""
    console.print(Markdown(help_text))


async def chat_loop():
    """Main chat loop."""
    from src.agent import create_changelog_agent

    # Check required environment variables
    if not os.getenv("GITHUB_TOKEN"):
        console.print("[red]Error: GITHUB_TOKEN 환경변수가 설정되지 않았습니다.[/red]")
        console.print("[dim]GitHub Personal Access Token을 .env 파일에 설정하세요.[/dim]")
        return

    # Check LLM provider and corresponding API key
    provider = os.getenv("LLM_PROVIDER", "anthropic").lower()
    if provider == "anthropic":
        if not os.getenv("ANTHROPIC_API_KEY"):
            console.print("[red]Error: ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다.[/red]")
            console.print("[dim]Anthropic API Key를 .env 파일에 설정하세요.[/dim]")
            return
    elif provider == "google":
        if not os.getenv("GOOGLE_API_KEY"):
            console.print("[red]Error: GOOGLE_API_KEY 환경변수가 설정되지 않았습니다.[/red]")
            console.print("[dim]Google API Key를 .env 파일에 설정하세요.[/dim]")
            return
    else:
        console.print(f"[red]Error: 지원하지 않는 LLM_PROVIDER: {provider}[/red]")
        console.print("[dim]'anthropic' 또는 'google'을 사용하세요.[/dim]")
        return

    # Create agent
    try:
        console.print(f"[dim]Agent 초기화 중... (Provider: {provider})[/dim]")
        agent = create_changelog_agent()
        console.print("[green]✓ Agent 준비 완료![/green]\n")
    except Exception as e:
        console.print(f"[red]Agent 초기화 실패: {e}[/red]")
        return

    # Default repo info
    owner = os.getenv("GITHUB_OWNER")
    repo = os.getenv("GITHUB_REPO")
    if owner and repo:
        console.print(f"[dim]기본 저장소: {owner}/{repo}[/dim]\n")

    while True:
        try:
            # Get user input
            user_input = Prompt.ask("\n[bold cyan]You[/bold cyan]")

            if not user_input.strip():
                continue

            # Handle commands
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

            # Run agent
            console.print("\n[dim]처리 중...[/dim]")

            from src.agent import run_agent_sync

            result = run_agent_sync(agent, user_input)

            # Extract and display response
            if "messages" in result:
                # Show tool calls and responses for debugging
                verbose = "--verbose" in sys.argv or "-v" in sys.argv
                if verbose:
                    console.print("\n[bold yellow]--- Agent 실행 로그 ---[/bold yellow]")
                    for msg in result["messages"]:
                        if hasattr(msg, "type"):
                            if msg.type == "ai" and hasattr(msg, "tool_calls") and msg.tool_calls:
                                for tool_call in msg.tool_calls:
                                    console.print(f"[cyan]Tool 호출:[/cyan] {tool_call.get('name', 'unknown')}")
                                    console.print(f"[dim]  Args: {tool_call.get('args', {})}[/dim]")
                            elif msg.type == "tool":
                                tool_name = getattr(msg, "name", "unknown")
                                content = msg.content[:200] + "..." if len(str(msg.content)) > 200 else msg.content
                                console.print(f"[green]Tool 결과:[/green] {tool_name}")
                                console.print(f"[dim]  {content}[/dim]")
                    console.print("[bold yellow]--- 로그 끝 ---[/bold yellow]\n")

                # Get the last AI message
                for msg in reversed(result["messages"]):
                    if hasattr(msg, "content") and msg.type == "ai":
                        console.print("\n[bold green]Agent[/bold green]")
                        # Check if content is a list (tool calls) or string
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
            continue
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]")
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")


def main():
    """Main entry point."""
    # Check for verbose flag
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    logger = setup_logging(verbose)

    if verbose:
        console.print("[dim]Verbose 모드 활성화됨[/dim]\n")

    print_welcome()
    asyncio.run(chat_loop())


if __name__ == "__main__":
    main()
