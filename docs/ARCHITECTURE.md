# 아키텍처

## 한눈에 보기

이 저장소는 위에서 아래로 `작업 제어 → 스킬 판단 → PPT 처리 → 검증·배포` 네 계층으로 구성합니다.

![저장소 아키텍처](architecture.svg)

## 1. 작업 제어 계층

저장소 변경이 문서와 어긋나지 않도록 작업 전후를 통제합니다.

- `AGENTS.md`: 모든 에이전트가 따라야 하는 절차
- `project-state.json`: 현재 완료·후보·미착수 상태의 단일 정본
- `tools/task_harness.py`: 상태 문서 생성, 검증, 설치, 커밋과 푸시
- `docs/STATUS.md`: 정본에서 생성되는 사람용 현황판

`STATUS.md`는 직접 편집하지 않습니다. 현재 사실을 바꾸려면 `project-state.json`을 수정하고 하네스로 다시 생성합니다.

## 2. 스킬 계층

Codex가 어떤 자료를 읽고 어떤 기능을 실행할 수 있는지 결정합니다.

- `hana-ppt-skill/SKILL.md`: 요청 분기와 실행 안전장치
- `hana-ppt-skill/agents/openai.yaml`: UI 표시와 기본 호출 문구
- `hana-ppt-skill/references/`: 디자인 토큰, 레이아웃, 분석 근거
- `hana-ppt-skill/assets/`: 폰트, CI, 원본 레퍼런스, 기준 이미지와 후보 JSON

저장소의 `hana-ppt-skill/`이 정본이고, 로컬의 `.codex/skills/hana-ppt-skill/`은 설치본입니다. 설치본을 직접 수정하지 않고 정본을 갱신한 뒤 `task_harness.py install`로 동기화합니다.

## 3. PPT 처리 계층

`ingest_deck.py`와 `deck_spec` JSON Schema까지 MVP로 구현됐습니다. 사용자 승인된 운영 `brand.json`은 마련됐지만 스타일 적용·생성·폰트 처리는 예정 상태입니다.

```text
초안 PPTX 또는 구조화된 초안
  → ingest_deck.py
  → deck_spec.json
  → restyle_deck.py / build_deck.py
  → 폰트 임베딩 또는 정적 대체
  → PPTX · PDF · PNG
```

두 실행 모드를 제공합니다.

- `restyle-only`: 원문, 수치와 데이터는 잠그고 디자인만 개선
- `hana-refine`: 제공된 근거 안에서 제목, 말투, 구조와 디자인을 개선

범용 조사와 최초 초안 작성은 이 계층의 책임이 아닙니다.

## 4. 검증·배포 계층

현재 자산·상태 검사는 동작하고 PPT 품질 검사는 구현 예정입니다.

- 현재 동작: JSON 파싱, 문서 UTF-8·제어 문자, 자산 경로·크기·SHA-256, 기준 이미지, 제외 레퍼런스, 상태 문서 동기화
- 구현 예정: PPT 구조 검사, PowerPoint/LibreOffice 렌더링, 잘림·겹침 검사, 비전 평가, 폰트 임베딩 검증
- 원격 검사: `.github/workflows/repository-harness.yml`

## 정본 우선순위

| 데이터 | 정본 | 파생 결과 |
|---|---|---|
| 진행 상태 | `project-state.json` | `docs/STATUS.md` |
| 승인 브랜드 | `assets/brand.json` | 문서·PPT 산출물 |
| 검수 전 브랜드 | `assets/brand.candidate.json` | `references/design-tokens.md` |
| 레퍼런스 포함 여부 | `assets/reference-decks/sources.json` | 분석·기준 이미지 목록 |
| 스킬 실행 절차 | `hana-ppt-skill/SKILL.md` | 로컬 Codex 설치본 |
| PPT 내용 | 향후 `deck_spec.json` | PPTX·PDF·PNG |

## 설계 원칙

- 후보와 승인을 파일 수준에서 분리합니다.
- 상세 규칙은 스킬 references에만 두고 프로젝트 문서에 복제하지 않습니다.
- 배포 산출물보다 구조화된 정본을 먼저 수정합니다.
- 자동 게시 전에 기존 사용자 변경이 섞이지 않았는지 확인합니다.
- 렌더러가 없는 검사는 최종 성공이 아니라 `partial`로 처리합니다.
