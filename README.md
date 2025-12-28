# Git Changelog Agent 🔧

LangChain과 GitHub API를 활용한 AI 기반 Changelog 생성 Agent입니다.

## 주요 기능

- 📋 **커밋 분석**: 지정 기간의 Git 커밋을 조회하고 분석
- 🏷️ **자동 분류**: 커밋을 유형별로 자동 분류 (feat, fix, docs 등)
- 📝 **Changelog 생성**: AI가 커밋을 분석하여 읽기 쉬운 Changelog 생성
- 📄 **README 업데이트**: 생성된 Changelog를 README.md에 자동 반영
- 🔀 **브랜치/태그 비교**: 두 시점 사이의 변경사항 비교

## 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                   Git Changelog Agent                        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │   Claude    │  │  LangChain   │  │   GitHub API     │   │
│  │   (LLM)     │◄─┤   Agent      │◄─┤   (PyGithub)     │   │
│  └─────────────┘  └──────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## 설치

### 요구사항
- Python 3.11+
- GitHub Personal Access Token
- Anthropic API Key

### 설치 방법

```bash
# 저장소 클론
git clone https://github.com/your-username/git-changelog-agent.git
cd git-changelog-agent

# 의존성 설치
pip install -e .

# 환경변수 설정
cp .env .env
# .env 파일을 열어 토큰 설정
```

### 환경변수

```env
# 필수
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxx

# 선택 (기본 저장소 설정)
GITHUB_OWNER=your-username
GITHUB_REPO=your-repo
```

## 사용법

### CLI 실행

```bash
python -m src.main
```

### 사용 예시

```
You: 지난 30일간의 커밋을 보여줘

Agent: 지난 30일간 총 15개의 커밋이 있습니다:
- [abc1234] feat: Add user authentication (@john, 2024-01-15)
- [def5678] fix: Resolve login issue (@jane, 2024-01-14)
...

You: 이 커밋들로 changelog를 만들어줘

Agent: 다음과 같은 Changelog를 생성했습니다:

### ✨ Features
- Add user authentication (abc1234) - @john

### 🐛 Bug Fixes
- Resolve login issue (def5678) - @jane
...

README.md에 반영할까요?

You: 응, README에 추가해줘

Agent: ✅ README.md가 성공적으로 업데이트되었습니다!
Commit: abc1234
URL: https://github.com/...
```

## LangChain Tools

| Tool | 설명 |
|------|------|
| `get_commits` | 기간별 커밋 목록 조회 |
| `get_commit_detail` | 특정 커밋 상세 정보 |
| `compare_refs` | 브랜치/태그 비교 |
| `get_merged_pull_requests` | 병합된 PR 조회 |
| `get_readme_content` | README 내용 조회 |
| `update_readme_with_changelog` | README 업데이트 |
| `format_changelog_markdown` | Changelog 마크다운 포맷팅 |
| `categorize_commit_message` | 커밋 메시지 분류 |

## 프로젝트 구조

```
git-changelog-agent/
├── pyproject.toml          # 프로젝트 설정
├── .env.example            # 환경변수 예시
├── README.md
└── src/
    ├── main.py             # CLI 진입점
    ├── types.py            # 타입 정의
    ├── agent/
    │   └── agent.py        # LangChain Agent 설정
    ├── tools/
    │   ├── github_tools.py # GitHub API 도구
    │   └── changelog_tools.py # Changelog 도구
    └── services/
        └── github.py       # GitHub API 클라이언트
```

## 라이선스

MIT License
