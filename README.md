# 하나증권 PPT 디자인 스킬

[![저장소 상태 동기화 검사](https://github.com/YUJAEYUN/hana_securities_ppt_design/actions/workflows/repository-harness.yml/badge.svg)](https://github.com/YUJAEYUN/hana_securities_ppt_design/actions/workflows/repository-harness.yml)

외부 에이전트나 범용 PPT 도구가 만든 초안을 하나증권식 말투·구조·디자인으로 다듬고, 렌더링 결과까지 검사하기 위한 후처리 스킬 저장소입니다.

> 현재 단계: PPTX 내용을 `deck_spec.json`으로 인수하는 MVP가 있습니다. HFG IR 기반 후보 규칙은 있지만 승인된 하나증권 브랜드 규칙과 PPT 후처리·렌더 엔진은 아직 구현되지 않았습니다.

## 전체 구조

![저장소 아키텍처](docs/architecture.svg)

위에서 아래로 다음 순서로 동작합니다.

1. 에이전트가 `AGENTS.md`와 현재 상태를 읽습니다.
2. 하네스가 작업 시작 상태를 잠그고 문서·자산·해시를 검사합니다.
3. 등록된 `hana-ppt-skill`이 브랜드 후보와 레이아웃 근거를 선택합니다.
4. 향후 PPT 엔진이 초안을 구조화하고 디자인을 적용합니다.
5. 렌더·품질 검사 후 산출물을 만들고 GitHub에 변경을 게시합니다.

자세한 설명은 [아키텍처 문서](docs/ARCHITECTURE.md)를 참고하세요.

## 저장소 둘러보기

```text
.
├── README.md                 저장소 첫 화면과 진입점
├── AGENTS.md                 모든 작업 에이전트의 필수 절차
├── project-state.json        현재 진행 상태의 단일 정본
├── docs/
│   ├── ARCHITECTURE.md       구성 요소와 데이터 흐름
│   ├── PRODUCT.md            범위와 핵심 설계 결정
│   ├── ROADMAP.md            구현 순서와 완료 기준
│   └── STATUS.md             project-state.json에서 자동 생성
├── hana-ppt-skill/
│   ├── SKILL.md              Codex가 읽는 실행 지침
│   ├── agents/openai.yaml    스킬 표시·호출 메타데이터
│   ├── schemas/              deck_spec JSON Schema
│   ├── scripts/              PPTX 인수 및 향후 처리 스크립트
│   ├── references/           디자인 분석과 레이아웃 규칙
│   └── assets/               폰트·CI·레퍼런스·후보 토큰
├── tools/task_harness.py     동기화·검증·설치·커밋·푸시
└── .github/workflows/        원격 상태 동기화 검사
```

## PPTX 인수 MVP

승인 브랜드 없이도 원본을 변경하지 않는 구조 인벤토리는 생성할 수 있습니다.

```bash
python hana-ppt-skill/scripts/ingest_deck.py input.pptx -o deck_spec.json
```

현재는 슬라이드 순서, 텍스트, 표, 이미지·그래픽 인벤토리를 수집하고 OLE·임베디드 패키지·확장 XML은 손실 가능성 경고로 남깁니다. 이 명령은 디자인을 변경하지 않습니다.

## 문서 읽는 순서

| 궁금한 내용 | 문서 |
|---|---|
| 지금 어디까지 됐나 | [STATUS.md](docs/STATUS.md) |
| 구성 요소가 어떻게 연결되나 | [ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| 무엇을 만들고 무엇은 만들지 않나 | [PRODUCT.md](docs/PRODUCT.md) |
| 다음에 무엇을 구현하나 | [ROADMAP.md](docs/ROADMAP.md) |
| 디자인 후보의 근거가 무엇인가 | [reference-analysis.md](hana-ppt-skill/references/reference-analysis.md) |

## 작업 방법

깨끗한 Git 작업 트리에서 시작합니다.

```powershell
python tools/task_harness.py begin
```

파일 변경이 끝나면 상태 동기화, 검증, 한글 커밋과 푸시를 한 번에 수행합니다.

```powershell
python tools/task_harness.py finish --message "한글 커밋 메시지"
```

게시 없이 검사만 할 때는 다음 명령을 사용합니다.

```powershell
python tools/task_harness.py check
```

## 중요한 현재 제약

- `brand.candidate.json`과 `layouts.candidate.json`은 HFG IR 자료에서 얻은 후보입니다.
- 후보값을 하나증권 공식 스타일로 단정하지 않습니다.
- 하나증권 리서치 자료 한 건은 예외 사례로 지정돼 스타일 학습에서 제외됐습니다.
- 승인된 `brand.json`, PPT 변환 스크립트, 폰트 임베딩과 렌더 검증은 아직 없습니다.
