# Git Changelog Agent - 기능 명세서

## 프로젝트 개요

Git에 관한 다양한 도움을 주는 AI Agent입니다. LangChain/LangGraph 기반으로 구현되었으며, GitHub API와 연동하여 커밋 분석 및 Changelog 자동 생성 기능을 제공합니다.

---

## 실행 모드

### 1. 배치 모드 (Batch Mode) - 자동 실행

스케줄러(cron, Task Scheduler)와 연동하여 자동으로 Changelog를 생성합니다.

**주요 특징:**
- 각 커밋의 실제 변경 내용(diff)을 분석
- AI가 변경사항을 한국어로 요약
- 커밋 메시지가 아닌 **실제 코드 변경 내용**을 기반으로 설명 생성

```bash
# 최근 1일 커밋으로 changelog 생성
python src/main.py --batch

# 최근 7일 커밋 + README 자동 업데이트
python src/main.py --batch --days 7 --update-readme

# 파일로 저장
python src/main.py --batch --days 30 --output changelog.md

# 특정 저장소 지정
python src/main.py --batch --owner myuser --repo myrepo --days 7
```

#### 배치 모드 옵션

| 옵션 | 단축 | 설명 | 기본값 |
|------|------|------|--------|
| `--batch` | `-b` | 배치 모드 활성화 | - |
| `--days` | `-d` | 조회 기간 (일) | 1 |
| `--branch` | - | 브랜치 | main |
| `--owner` | - | 저장소 소유자 | 환경변수 |
| `--repo` | - | 저장소 이름 | 환경변수 |
| `--update-readme` | `-u` | README 자동 업데이트 | false |
| `--output` | `-o` | 저장 파일 경로 | - |
| `--verbose` | `-v` | 상세 로그 | false |

#### 스케줄러 설정 예시

**Linux cron (매일 오전 9시)**
```bash
0 9 * * * cd /path/to/project && python src/main.py --batch --days 1 --update-readme
```

**Windows Task Scheduler**
```
python C:\path\to\project\src\main.py --batch --days 1 --update-readme
```

### 2. 대화형 모드 (Interactive Mode)

AI Agent와 대화하면서 다양한 Git 작업을 수행합니다.

```bash
# 기본 실행
python src/main.py

# 상세 로그 모드
python src/main.py --verbose
```

---

## 현재 구현된 기능

### 1. 커밋 조회 및 분석

| 기능 | 설명 | 상태 |
|------|------|------|
| 기간별 커밋 조회 | 지정 기간(일수)의 커밋 목록 조회 | ✅ 완료 |
| 커밋 상세 조회 | 특정 커밋의 변경 파일, 추가/삭제 라인 확인 | ✅ 완료 |
| 브랜치/태그 비교 | 두 시점 간 변경사항 비교 | ✅ 완료 |
| 병합된 PR 조회 | 기간별 Merged PR 목록 조회 | ✅ 완료 |

### 2. Changelog 생성

| 기능 | 설명 | 상태 |
|------|------|------|
| 커밋 자동 분류 | Conventional Commit 기반 카테고리 분류 | ✅ 완료 |
| Markdown 포맷팅 | 카테고리별 정리된 Changelog 생성 | ✅ 완료 |
| README 업데이트 | 생성된 Changelog를 README.md에 반영 | ✅ 완료 |
| 파일 출력 | Changelog를 별도 파일로 저장 | ✅ 완료 |
| **AI 변경사항 요약** | **커밋 diff를 분석하여 실제 변경 내용을 AI가 요약** | ✅ 완료 |

### 3. 멀티 LLM 프로바이더 지원

| 프로바이더 | 모델 | 상태 |
|-----------|------|------|
| Anthropic | Claude (claude-sonnet-4-20250514) | ✅ 완료 |
| Google | Gemini (gemini-2.0-flash 등) | ✅ 완료 |

### 4. CLI 인터페이스

| 기능 | 설명 | 상태 |
|------|------|------|
| 대화형 CLI | Rich 라이브러리 기반 터미널 UI | ✅ 완료 |
| 배치 모드 | 자동 실행을 위한 비대화형 모드 | ✅ 완료 |
| Verbose 모드 | `--verbose` 플래그로 상세 로그 확인 | ✅ 완료 |
| 한국어 지원 | 한국어 입력/출력 지원 | ✅ 완료 |

---

## 사용 가능한 Tools (LangChain)

```
┌─────────────────────────────────────────────────────────────┐
│                      GitHub Tools                            │
├─────────────────────────────────────────────────────────────┤
│  get_commits           │ 기간별 커밋 목록 조회              │
│  get_commit_detail     │ 특정 커밋 상세 정보                │
│  compare_refs          │ 브랜치/태그/커밋 비교              │
│  get_merged_pull_requests │ 병합된 PR 조회                 │
├─────────────────────────────────────────────────────────────┤
│                    Changelog Tools                           │
├─────────────────────────────────────────────────────────────┤
│  get_readme_content    │ README.md 내용 조회               │
│  update_readme_with_changelog │ README에 Changelog 추가    │
│  format_changelog_markdown │ Markdown 포맷 변환            │
│  categorize_commit_message │ 커밋 메시지 카테고리 분류     │
└─────────────────────────────────────────────────────────────┘
```

---

## AI 변경사항 요약 기능

배치 모드에서 각 커밋에 대해 다음 프로세스가 실행됩니다:

```
┌─────────────────────────────────────────────────────────────┐
│                    AI 요약 프로세스                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 커밋 조회     →  GitHub API로 커밋 목록 가져오기        │
│  2. 상세 정보 조회 →  각 커밋의 변경 파일, diff 조회         │
│  3. AI 분석      →  LLM이 실제 코드 변경 내용 분석          │
│  4. 요약 생성    →  한국어로 1-2문장 요약 생성              │
│  5. Changelog    →  카테고리별로 정리된 Markdown 생성       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 출력 예시

```markdown
## Changelog

**Period:** 2024-01-01 ~ 2024-01-07

> 🤖 *AI가 분석한 변경사항 요약*

### ✨ Features

- **feat: 로그인 기능 추가** (abc1234)
  - 사용자 인증을 위한 JWT 기반 로그인 시스템을 구현하고,
    세션 관리 및 토큰 갱신 로직을 추가함.
  - *@developer (2024-01-05)*

### 🐛 Bug Fixes

- **fix: 메모리 누수 수정** (def5678)
  - useEffect 클린업 함수에서 이벤트 리스너 제거 로직이 누락되어
    발생하던 메모리 누수 문제를 해결함.
  - *@developer (2024-01-06)*
```

---

## 커밋 카테고리 분류

| 카테고리 | 아이콘 | 설명 |
|---------|--------|------|
| feat | ✨ | 새로운 기능 추가 |
| fix | 🐛 | 버그 수정 |
| docs | 📚 | 문서 변경 |
| refactor | ♻️ | 코드 리팩토링 |
| perf | ⚡ | 성능 개선 |
| test | ✅ | 테스트 관련 |
| chore | 🔧 | 기타 유지보수 |
| style | 💄 | 코드 스타일 변경 |
| ci | 👷 | CI/CD 관련 |

---

## 향후 구현 가능한 MCP (Model Context Protocol) 기능

### 1. MCP Server 구현

```
┌─────────────────────────────────────────────────────────────┐
│                    MCP Server 아키텍처                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐     ┌──────────────┐     ┌────────────┐  │
│  │ Claude Desktop│────▶│  MCP Server  │────▶│ GitHub API │  │
│  │ / IDE Plugin │     │ (git-changelog)│    └────────────┘  │
│  └──────────────┘     └──────────────┘                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 제안되는 MCP Tools

| Tool | 설명 |
|------|------|
| `git_get_commits` | 커밋 이력 조회 |
| `git_get_diff` | 변경사항 diff 조회 |
| `git_create_changelog` | Changelog 자동 생성 |
| `git_update_readme` | README 업데이트 |
| `git_compare_branches` | 브랜치 비교 |
| `git_get_pr_list` | PR 목록 조회 |

#### MCP Resources

| Resource | 설명 |
|----------|------|
| `git://commits` | 최근 커밋 목록 |
| `git://readme` | README 내용 |
| `git://changelog` | 현재 Changelog |

### 2. 추가 구현 가능 기능

| 기능 | 설명 | 우선순위 |
|------|------|----------|
| 로컬 Git 지원 | GitHub 외 로컬 저장소 지원 | 높음 |
| GitLab/Bitbucket 지원 | 다른 Git 호스팅 서비스 | 중간 |
| 자동 릴리즈 노트 | 태그 기반 릴리즈 노트 생성 | 중간 |
| PR 템플릿 생성 | 변경사항 기반 PR 설명 자동 생성 | 낮음 |
| 커밋 메시지 추천 | staged 변경사항 기반 메시지 추천 | 낮음 |
| Slack/Discord 연동 | Changelog 알림 전송 | 낮음 |

---

## 환경 설정

### 필수 환경변수

```env
# LLM 프로바이더 선택 (anthropic / google)
LLM_PROVIDER=google

# Anthropic (LLM_PROVIDER=anthropic일 때)
ANTHROPIC_API_KEY=sk-ant-xxxx
ANTHROPIC_MODEL=claude-sonnet-4-20250514

# Google (LLM_PROVIDER=google일 때)
GOOGLE_API_KEY=AIzaSyxxxx
GOOGLE_MODEL=gemini-2.0-flash

# GitHub
GITHUB_TOKEN=ghp_xxxx
GITHUB_OWNER=username
GITHUB_REPO=repository
```

### 설치

```bash
# 의존성 설치
pip install -r requirements.txt

# 또는 패키지로 설치
pip install -e .
```

### 실행

```bash
# 대화형 모드 (기본)
python src/main.py

# 배치 모드 - 자동 실행
python src/main.py --batch --days 7 --update-readme

# 설치 후 명령어로 실행
changelog-agent
changelog-agent --batch --days 1
```

---

## 프로젝트 구조

```
git-changelog-agent/
├── pyproject.toml          # 프로젝트 설정 및 의존성
├── requirements.txt        # pip 의존성
├── requirements-dev.txt    # 개발용 의존성
├── .env.example            # 환경변수 예시
├── README.md               # 프로젝트 소개
├── FEATURES.md             # 기능 명세서 (이 문서)
└── src/
    ├── __init__.py
    ├── main.py             # CLI 진입점 (배치/대화형 모드)
    ├── models.py           # Pydantic 모델 정의
    ├── agent/
    │   ├── __init__.py
    │   └── agent.py        # LangChain Agent 설정
    ├── tools/
    │   ├── __init__.py
    │   ├── github_tools.py # GitHub API 도구
    │   └── changelog_tools.py # Changelog 도구
    ├── services/
    │   ├── __init__.py
    │   └── github.py       # GitHub API 클라이언트
    └── utils/
        └── __init__.py
```

---

## 기술 스택

| 분류 | 기술 |
|------|------|
| 언어 | Python 3.11+ |
| AI Framework | LangChain, LangGraph |
| LLM | Anthropic Claude, Google Gemini |
| GitHub API | PyGithub |
| CLI | Rich, argparse |
| 데이터 검증 | Pydantic |

---

## 라이선스

MIT License
