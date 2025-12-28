"""LangChain Agent configuration for Git Changelog Agent."""

import os
from typing import Literal, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.prebuilt import create_react_agent

from src.tools import ALL_TOOLS

# Supported LLM providers
LLMProvider = Literal["anthropic", "google"]

# System prompt for the agent
SYSTEM_PROMPT = """You are a Git Changelog Agent that helps users analyze Git repositories and generate changelogs.

## Your Capabilities
You have access to tools that allow you to:
1. **Retrieve commits** from a GitHub repository for a specified time period
2. **Get detailed commit information** including file changes
3. **Compare branches or tags** to see differences
4. **Get merged pull requests** with their details
5. **Read README content** from the repository
6. **Update README** with new changelog content
7. **Categorize commits** by type (feat, fix, docs, etc.)
8. **Format changelogs** into proper markdown

## Changelog Generation Guidelines
When generating a changelog:
1. First, retrieve commits or PRs for the requested period
2. Analyze each commit/PR to determine its category:
   - **feat**: New features
   - **fix**: Bug fixes
   - **docs**: Documentation changes
   - **refactor**: Code refactoring
   - **perf**: Performance improvements
   - **test**: Test changes
   - **chore**: Maintenance tasks
   - **style**: Code style changes
   - **ci**: CI/CD changes
3. Create clear, user-friendly descriptions (not raw commit messages)
4. Group changes by category
5. Format with proper markdown

## Best Practices
- Always confirm with the user before updating the README
- Provide a preview of the changelog before applying changes
- Use concise, meaningful descriptions
- Include PR numbers or commit SHAs as references
- Credit authors where appropriate

## Response Style
- Be concise and helpful
- Use Korean if the user writes in Korean
- Provide clear summaries of your findings
- Ask for clarification if the request is ambiguous
"""


def _create_anthropic_llm(model_name: Optional[str] = None, api_key: Optional[str] = None) -> BaseChatModel:
    """Create Anthropic LLM instance."""
    from langchain_anthropic import ChatAnthropic

    model_name = model_name or os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
    api_key = api_key or os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        raise ValueError("Anthropic API key is required. Set ANTHROPIC_API_KEY env var.")

    return ChatAnthropic(
        model=model_name,
        api_key=api_key,
        max_tokens=4096,
    )


def _create_google_llm(model_name: Optional[str] = None, api_key: Optional[str] = None) -> BaseChatModel:
    """Create Google Gemini LLM instance."""
    from langchain_google_genai import ChatGoogleGenerativeAI

    model_name = model_name or os.getenv("GOOGLE_MODEL", "gemini-2.0-flash")
    api_key = api_key or os.getenv("GOOGLE_API_KEY")

    if not api_key:
        raise ValueError("Google API key is required. Set GOOGLE_API_KEY env var.")

    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        max_output_tokens=4096,
    )


def get_llm_provider() -> LLMProvider:
    """Get the configured LLM provider from environment."""
    provider = os.getenv("LLM_PROVIDER", "anthropic").lower()
    if provider not in ("anthropic", "google"):
        raise ValueError(f"Unsupported LLM_PROVIDER: {provider}. Use 'anthropic' or 'google'.")
    return provider  # type: ignore


def create_changelog_agent(
    provider: Optional[LLMProvider] = None,
    model_name: Optional[str] = None,
    api_key: Optional[str] = None,
):
    """Create the Git Changelog Agent.

    Args:
        provider: LLM provider ('anthropic' or 'google'). Defaults to LLM_PROVIDER env var.
        model_name: Model name. Defaults to provider-specific env var.
        api_key: API key. Defaults to provider-specific env var.

    Returns:
        Configured LangChain agent.
    """
    provider = provider or get_llm_provider()

    # Create LLM based on provider
    if provider == "anthropic":
        llm = _create_anthropic_llm(model_name, api_key)
    elif provider == "google":
        llm = _create_google_llm(model_name, api_key)
    else:
        raise ValueError(f"Unsupported provider: {provider}")

    # Create the agent with tools
    agent = create_react_agent(
        model=llm,
        tools=ALL_TOOLS,
        prompt=SYSTEM_PROMPT,
    )

    return agent


async def run_agent(
    agent,
    message: str,
    config: Optional[dict] = None,
):
    """Run the agent with a user message.

    Args:
        agent: The configured agent.
        message: User's message/request.
        config: Optional configuration for the agent.

    Returns:
        Agent response.
    """
    config = config or {}

    result = await agent.ainvoke(
        {"messages": [HumanMessage(content=message)]},
        config=config,
    )

    return result


def run_agent_sync(
    agent,
    message: str,
    config: Optional[dict] = None,
):
    """Run the agent synchronously with a user message.

    Args:
        agent: The configured agent.
        message: User's message/request.
        config: Optional configuration for the agent.

    Returns:
        Agent response.
    """
    config = config or {}

    result = agent.invoke(
        {"messages": [HumanMessage(content=message)]},
        config=config,
    )

    return result
