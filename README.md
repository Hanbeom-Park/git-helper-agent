# Git Changelog Agent

LangChain과 GitHub API를 활용한 AI 기반 Changelog 자동 생성 에이전트입니다. 커밋 변경 내용을 AI가 분석하여 의미 있는 요약을 생성하고, README에 히스토리를 자동으로 추가합니다.

## 프로젝트 개요

Git Changelog Agent는 GitHub 저장소의 커밋 이력을 분석하여 자동으로 Changelog를 생성하는 AI 에이전트입니다. 단순히 커밋 메시지를 나열하는 것이 아니라, LLM(Large Language Model)이 실제 코드 변경사항(diff)을 분석하여 한국어로 의미 있는 요약을 생성합니다.

### 핵심 가치

- **자동화**: 수동으로 Changelog를 작성하는 번거로움 제거
- **AI 분석**: 코드 diff를 분석하여 실제 변경 내용을 이해하고 요약
- **유연성**: 배치 모드(자동 실행)와 대화형 모드(Agent 상호작용) 지원
- **다중 LLM**: Anthropic Claude와 Google Gemini 모두 지원

## 주요 기능

| 기능 | 설명 |
|------|------|
| **커밋 조회** | 지정 기간의 Git 커밋 목록을 조회하고 상세 정보(diff 포함) 확인 |
| **AI 요약** | LLM이 커밋의 실제 코드 변경사항을 분석하여 한국어 요약 생성 |
| **자동 분류** | Conventional Commit 형식 기반 커밋 자동 분류 (feat, fix, docs 등) |
| **브랜치 비교** | 두 브랜치/태그 간의 변경사항 비교 분석 |
| **PR 조회** | 병합된 Pull Request 목록 조회 |
| **README 업데이트** | 생성된 Changelog를 README.md에 자동 반영 및 커밋 |
| **배치 모드** | CI/CD 또는 스케줄러와 연동 가능한 자동 실행 모드 |
| **대화형 모드** | Rich CLI 기반 Agent와 자연어 대화 |

## 아키텍처

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Git Changelog Agent                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                 CLI Interface (main.py)                       │  │
│  │  ├── Batch Mode: 자동 Changelog 생성 및 README 업데이트       │  │
│  │  └── Interactive Mode: Agent와 자연어 대화                    │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              │                                      │
│                              ▼                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │              LangChain Agent (agent.py)                       │  │
│  │  ├── Provider: Anthropic Claude / Google Gemini               │  │
│  │  ├── Pattern: ReAct (Reasoning + Acting)                      │  │
│  │  └── Tools: 8개 LangChain Tool 사용                           │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              │                                      │
│                              ▼                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    Tools Layer (tools/)                       │  │
│  │  ┌─────────────────────┐  ┌─────────────────────────────────┐ │  │
│  │  │ GitHub Tools (4개)  │  │ Changelog Tools (4개)           │ │  │
│  │  │ - get_commits       │  │ - get_readme_content            │ │  │
│  │  │ - get_commit_detail │  │ - update_readme_with_changelog  │ │  │
│  │  │ - compare_refs      │  │ - format_changelog_markdown     │ │  │
│  │  │ - get_merged_prs    │  │ - categorize_commit_message     │ │  │
│  │  └─────────────────────┘  └─────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              │                                      │
│                              ▼                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │             Service Layer (services/github.py)                │  │
│  │  └── GitHubService: PyGithub 래퍼 클래스                      │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              │                                      │
│                              ▼                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                   External APIs                               │  │
│  │  ├── GitHub REST API v3 (PyGithub)                            │  │
│  │  ├── Anthropic Claude API                                     │  │
│  │  └── Google Gemini API                                        │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 데이터 흐름

**배치 모드 워크플로우:**
```
CLI 실행 → 커밋 조회 → 각 커밋 상세 정보 조회 → LLM이 diff 분석/요약
         → Changelog 마크다운 생성 → (선택) README 업데이트 → GitHub 커밋
```

**대화형 모드 워크플로우:**
```
사용자 입력 → Agent 분석 → Tool 호출 결정 → Tool 실행 → 결과 분석 → 응답 생성
```

### 설계 패턴

- **Layered Architecture**: CLI → Agent → Tools → Service → External API
- **Factory Pattern**: LLM 프로바이더 생성 (Anthropic/Google)
- **Adapter Pattern**: PyGithub → 프로젝트 모델 변환
- **Strategy Pattern**: LLM 프로바이더 선택

## 프로젝트 구조

```
git-changelog-agent/
├── pyproject.toml              # 프로젝트 설정 및 의존성 관리
├── requirements.txt            # pip 의존성 (코어)
├── requirements-dev.txt        # 개발용 의존성
├── .env                        # 환경변수 설정 (민감한 토큰 포함)
├── .gitignore                  # Git 무시 파일 목록
├── README.md                   # 프로젝트 문서
├── FEATURES.md                 # 기능 명세서
└── src/
    ├── __init__.py
    ├── main.py                 # CLI 진입점 (배치/대화형 모드)
    ├── models.py               # Pydantic 데이터 모델
    ├── agent/
    │   ├── __init__.py
    │   └── agent.py            # LangChain Agent 설정 및 LLM 관리
    ├── services/
    │   ├── __init__.py
    │   └── github.py           # GitHub API 클라이언트 (PyGithub 래퍼)
    ├── tools/
    │   ├── __init__.py         # 모든 Tool export
    │   ├── github_tools.py     # GitHub API 관련 LangChain Tools
    │   └── changelog_tools.py  # Changelog 생성 관련 Tools
    └── utils/
        └── __init__.py
```

### 주요 파일 설명

| 파일 | 역할 |
|------|------|
| `main.py` | CLI 진입점, 배치 모드 및 대화형 모드 실행 로직 |
| `models.py` | CommitInfo, CommitDetail, ChangelogEntry 등 Pydantic 모델 |
| `agent/agent.py` | LangChain ReAct Agent 생성, LLM 설정, System Prompt |
| `services/github.py` | GitHubService 클래스 - PyGithub 래퍼 |
| `tools/github_tools.py` | 커밋 조회, 상세 정보, 브랜치 비교, PR 조회 Tool |
| `tools/changelog_tools.py` | README 조회/업데이트, 마크다운 포맷팅, 커밋 분류 Tool |

## 구현된 기능

### LangChain Tools (8개)

| Tool | 설명 |
|------|------|
| `get_commits` | 기간별 커밋 목록 조회 |
| `get_commit_detail` | 특정 커밋 상세 정보 (diff/patch 포함) |
| `compare_refs` | 브랜치/태그 비교 |
| `get_merged_pull_requests` | 병합된 PR 조회 |
| `get_readme_content` | README.md 내용 조회 |
| `update_readme_with_changelog` | README에 Changelog 추가/업데이트 |
| `format_changelog_markdown` | Changelog 마크다운 포맷팅 |
| `categorize_commit_message` | 커밋 메시지 자동 분류 |

### 커밋 분류 체계

Conventional Commit 형식을 기반으로 자동 분류:

| 카테고리 | 레이블 | 키워드 |
|----------|--------|--------|
| feat | ✨ Features | add, new, implement, create |
| fix | 🐛 Bug Fixes | fix, bug, resolve, patch |
| docs | 📚 Documentation | readme, document, docs |
| refactor | ♻️ Refactoring | refactor, restructure, reorganize |
| perf | ⚡ Performance | performance, optimize, speed |
| test | ✅ Tests | test, spec, coverage |
| chore | 🔧 Chores | chore, update, upgrade |
| style | 💄 Styles | style, format, lint |
| ci | 👷 CI/CD | ci, workflow, pipeline |

## 사용한 프롬프트

### Agent System Prompt

Agent의 행동을 정의하는 시스템 프롬프트:

```
You are a Git Changelog Agent that helps users analyze Git repositories
and generate changelogs.

## Your Capabilities
1. Retrieve commits from a GitHub repository for a specified time period
2. Get detailed commit information including file changes
3. Compare branches or tags to see differences
4. Get merged pull requests with their details
5. Read README content from the repository
6. Update README with new changelog content
7. Categorize commits by type (feat, fix, docs, etc.)
8. Format changelogs into proper markdown

## Changelog Generation Guidelines
When generating a changelog:
1. First, retrieve commits or PRs for the requested period
2. Analyze each commit/PR to determine its category:
   - feat: New features
   - fix: Bug fixes
   - docs: Documentation changes
   - refactor: Code refactoring
   - perf: Performance improvements
   - test: Test changes
   - chore: Maintenance tasks
3. Create clear, user-friendly descriptions
4. Group changes by category
5. Format with proper markdown

## Best Practices
- Always confirm with the user before updating the README
- Provide a preview of the changelog before applying changes
- Use concise, meaningful descriptions
- Include PR numbers or commit SHAs as references

## Response Style
- Be concise and helpful
- Use Korean if the user writes in Korean
- Provide clear summaries of your findings
```

### 커밋 요약 프롬프트

배치 모드에서 각 커밋의 diff를 분석하는 프롬프트:

```
다음 Git 커밋의 변경사항을 분석하고, 실제 어떤 변경이 이루어졌는지
한국어로 간결하게 요약해주세요.
핵심적인 변경 내용만 1-2문장으로 설명해주세요.

커밋 메시지: {commit_message}
변경된 파일 수: {files_changed}
추가된 라인: +{additions}
삭제된 라인: -{deletions}

변경된 파일 목록:
{files_info}

요약 (1-2문장):
```

## 설치 및 사용법

### 요구사항

- Python 3.11+
- GitHub Personal Access Token
- Anthropic API Key 또는 Google API Key

### 설치

```bash
# 저장소 클론
git clone https://github.com/your-username/git-changelog-agent.git
cd git-changelog-agent

# 의존성 설치
pip install -e .

# 환경변수 설정
cp .env.example .env
# .env 파일을 열어 토큰 설정
```

### 환경변수

```env
# LLM 제공자 선택 (anthropic 또는 google)
LLM_PROVIDER=google

# Anthropic 설정
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxx
ANTHROPIC_MODEL=claude-sonnet-4-20250514

# Google 설정
GOOGLE_API_KEY=AIzaSyxxxxxxxxxx
GOOGLE_MODEL=gemini-2.0-flash

# GitHub 설정 (필수)
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
GITHUB_OWNER=your-username
GITHUB_REPO=your-repo
```

### 사용법

**배치 모드 (자동 실행)**
```bash
# 지난 7일간의 커밋으로 Changelog 생성
python src/main.py --batch --days 7

# README 자동 업데이트 포함
python src/main.py --batch --days 7 --update-readme

# 파일로 저장
python src/main.py --batch --days 30 --output changelog.md
```

**대화형 모드**
```bash
# 기본 실행
python src/main.py

# 상세 로그 출력
python src/main.py --verbose
```

**대화형 모드 예시**
```
You: 지난 30일간의 커밋을 보여줘

Agent: 지난 30일간 총 15개의 커밋이 있습니다:
- [abc1234] feat: Add user authentication (@john, 2024-01-15)
- [def5678] fix: Resolve login issue (@jane, 2024-01-14)
...

You: 이 커밋들로 changelog를 만들어서 README에 추가해줘

Agent: ✅ README.md가 성공적으로 업데이트되었습니다!
```

## 기술 스택

| 분류 | 기술 | 버전 |
|------|------|------|
| 언어 | Python | 3.11+ |
| AI Framework | LangChain | 0.3.0+ |
| AI Framework | LangGraph | 0.2.0+ |
| LLM | Anthropic Claude | claude-sonnet-4-20250514 |
| LLM | Google Gemini | gemini-2.0-flash |
| GitHub API | PyGithub | 2.1.0+ |
| CLI | Rich | 13.0.0+ |
| 데이터 검증 | Pydantic | 2.0.0+ |
| 환경설정 | python-dotenv | 1.0.0+ |

## 활용 시나리오

### 1. 팀 프로젝트 주간/월간 리포트 자동화

개발팀에서 매주 또는 매월 진행 상황을 공유할 때 활용할 수 있습니다. 배치 모드로 지난 7일간의 커밋을 조회하면, AI가 각 커밋의 실제 코드 변경사항을 분석하여 "어떤 기능이 추가되었고, 어떤 버그가 수정되었는지"를 자동으로 정리해줍니다. PM이나 비개발 직군에게 기술적인 커밋 메시지를 일일이 설명할 필요 없이, 이해하기 쉬운 형태로 변환됩니다.

```bash
# 매주 금요일 CI/CD에서 자동 실행
python src/main.py --batch --days 7 --update-readme
```

### 2. 오픈소스 프로젝트 릴리즈 문서화

오픈소스 프로젝트에서 새 버전을 릴리즈할 때, 이전 태그부터 현재까지의 변경사항을 자동으로 문서화할 수 있습니다. 기여자들의 커밋을 카테고리별로 분류하고, 각 변경사항에 대한 설명을 생성하여 사용자들이 "이번 버전에서 무엇이 바뀌었는지" 쉽게 파악할 수 있습니다.

### 3. 개인 프로젝트 포트폴리오 관리

개인 프로젝트의 README에 개발 히스토리를 자동으로 기록하여, 포트폴리오로 활용할 때 "이 프로젝트에서 어떤 작업을 했는지"를 명확하게 보여줄 수 있습니다. 단순한 커밋 로그가 아닌, AI가 분석한 의미 있는 변경 내역이 기록됩니다.

### 4. 코드 리뷰 사전 준비

PR을 올리기 전에 자신이 작업한 커밋들을 요약하여 리뷰어에게 컨텍스트를 제공할 수 있습니다. "이 브랜치에서 어떤 작업을 했는지"를 AI가 정리해주므로, 리뷰어가 코드를 이해하는 데 도움이 됩니다.

## 추후 확장 가능 기능

### 릴리즈 노트 자동 생성

현재는 기간 기반으로 커밋을 조회하지만, **태그 간 비교**를 통해 릴리즈 노트를 생성하는 기능을 추가할 수 있습니다. `v1.0.0`과 `v1.1.0` 사이의 모든 변경사항을 분석하여 GitHub Releases에 자동으로 등록하는 방식입니다. 이미 `compare_refs` Tool이 구현되어 있으므로, 이를 확장하면 됩니다.

### CHANGELOG.md 별도 관리

README 업데이트 외에 `CHANGELOG.md` 파일을 별도로 관리하는 기능입니다. Keep a Changelog 형식을 따라 버전별로 변경사항을 누적 기록하고, `[Unreleased]` 섹션에 최신 변경사항을 자동 추가하는 방식으로 확장할 수 있습니다.

### 팀 커뮤니케이션 연동

Changelog가 생성되면 Slack이나 Discord 채널에 자동으로 알림을 보내는 기능입니다. 웹훅을 통해 "이번 주 변경사항 요약"을 팀 채널에 공유하여, 모든 팀원이 프로젝트 진행 상황을 파악할 수 있습니다.

### PR 설명 자동 생성

브랜치의 커밋들을 분석하여 PR 본문을 자동으로 작성하는 기능입니다. 현재 구현된 커밋 요약 로직을 활용하여, "이 PR에서 어떤 변경이 이루어졌는지"를 정리한 템플릿을 생성할 수 있습니다.

### 다중 저장소 통합 리포트

마이크로서비스 아키텍처나 모노레포 환경에서 여러 저장소의 변경사항을 하나의 리포트로 통합하는 기능입니다. 각 서비스별 변경사항을 수집하여 전체 시스템의 변경 이력을 한눈에 파악할 수 있습니다.

## 라이선스

MIT License