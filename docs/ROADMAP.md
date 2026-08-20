# 구현 로드맵

실시간 완료 상태는 [STATUS.md](STATUS.md)를 따릅니다. 이 문서는 앞으로 구현할 순서와 단계별 종료 조건만 정의합니다.

## 1. 스킬 기반 완성

- `SKILL.md`, `openai.yaml`, 자산 폴더와 의존성 구성
- 로컬 설치본과 저장소 정본 동기화
- 최소 테스트와 `requirements.txt` 추가

종료 조건: 깨끗한 환경에서 스킬 구조 검증과 설치가 재현됩니다.

## 2. 브랜드 근거 확정

- 대표성이 확인된 하나증권 샘플 추가
- CI를 PPTX용 SVG/PNG로 변환하고 보호영역 확정
- 색상, 폰트 역할, 여백과 로고 규칙 검수
- 후보 JSON을 승인된 `brand.json`으로 승격

종료 조건: 모든 승인 토큰에 출처와 사람 검수 기록이 있습니다.

## 3. 초안 인수와 정본 생성

- `ingest_deck.py` 구현
- 텍스트·표·차트·이미지 인벤토리 생성
- `deck_spec.json` 스키마와 슬라이드 대응표 정의
- 해석할 수 없는 SmartArt/OLE/수식 경고

종료 조건: 입력 PPTX를 내용 손실 없이 구조화하거나 손실 항목을 명시합니다.

## 4. 하나 스타일 후처리

- `restyle_deck.py`/`build_deck.py`는 범용 PPTX 조작(엔진 겹)만 담당하고, 하나증권 브랜드·문체 판단(규칙 겹)은 승인된 `brand.json`/`voice.json` 주입으로 분리합니다.
- `restyle_deck.py`의 `restyle-only`(완료): 테마 파트(`ppt/theme/themeN.xml`)의 색상·폰트만 승인된 `brand.json`으로 교체. 슬라이드 XML은 전혀 읽거나 쓰지 않아 원문 잠금을 구조적으로 보장합니다.
- `restyle_deck.py`의 `hana-refine`(1차 구현 완료, 텍스트 런 수준): `text_units.py`로 슬라이드 텍스트 런을 추출하고, 에이전트가 `voice.json` 규칙에 따라 다시 쓴 `edits.json`을 `verify_evidence_preserved.py`로 검증(수치·비교기준 보존)한 뒤에만 적용합니다. 검증 실패 시 어떤 슬라이드도 수정하지 않습니다. 절차는 [hana-refine-workflow.md](../hana-ppt-skill/references/hana-refine-workflow.md) 참고.
- `build_deck.py`(기본 레이아웃 완료 + 역할별 배치 1차 구현): `deck_spec.json`(텍스트·표 인벤토리)과 승인된 `brand.json`으로 PPTX를 처음부터 새로 만듭니다. 표준 라이브러리만으로 `[Content_Types].xml`부터 테마·슬라이드까지 OOXML 파트를 직접 작성합니다(외부 생성 라이브러리 미사용). `--layouts`(승인된 `layouts.json`)와 `--layout-plan`(슬라이드별 역할 JSON, 에이전트/사람이 작성)을 함께 주면 `cover`/`section-divider`/`disclaimer` 역할별로 다르게 배치합니다. 미지정 슬라이드나 `strategic-kpi`/`executive-summary`/`closing` 역할은 기본(data-body: 제목 + 불릿 또는 표) 레이아웃으로 대체됩니다. 장식 요소는 OOXML 프리셋 도형(`prstGeom`)으로 브랜드 색상에 맞춰 그립니다. cover/section-divider는 실제 하나증권 배포 자료(`hana-securities-2025-profile`)와 대조해 전체 배경을 `primary_green`으로 채우고 흰 제목을 놓는 방식으로 확정했습니다(처음엔 HFG 그룹 IR 근거로 적색 강조선·원형 모티프를 추정했으나 실제 자료엔 없었습니다 — [정정 기록](../hana-ppt-skill/references/hana-securities-cover-pattern-correction.md)). data-body는 제목 밑줄을, 표는 진한 헤더 행과 옅은 줄무늬 행을 그립니다(재무 현황 페이지 근거, 어느 행이 부분합인지는 추측하지 않고 홀수 행마다 기계적으로 줄무늬만 넣습니다). 로고는 보호영역이 미확정이라 여전히 자동 배치하지 않고 경고로 남깁니다. 이미지·그래픽·그룹 요소는 재현하지 않고 경고로만 보고합니다.
- 남은 범위: `strategic-kpi`/`executive-summary`/`closing` 역할 배치, `restyle_deck.py`(기존 파일 편집)의 레이아웃 수준 재구성(아직 전혀 없음), 참고 자료에서 아이콘·삽화 같은 재사용 그래픽 에셋을 뽑아 라이브러리로 등록하고 `<p:pic>`으로 삽입하는 기능(따로 검토 필요 — 크기·색이 고정된 비트맵이라 잘못 쓰면 어색해 보일 위험이 있어 벡터 장식보다 신중히 접근)
- 밀도 초과 시 자동 축소보다 페이지 분할 우선
- 원문·데이터 잠금과 출처 범위 검사(레이아웃 수준까지 확장 필요)

종료 조건: 두 모드가 변경 경계를 지키며 PPTX를 생성합니다.

## 5. 폰트와 휴대성

- 폰트 사전 검사와 안전한 ZIP 추출
- 글리프·스타일별 서브셋 임베딩
- PowerPoint의 실제 임베딩 상태와 미설치 환경 렌더 검증
- 실패 시 정적 PPTX와 PDF 생성

종료 조건: 수신자 폰트 미설치 환경에서 합의된 허용 오차 안으로 표시됩니다.

## 6. 렌더·시각 품질

- `render_slides.py`: LibreOffice(`soffice`) → PDF → `pdftoppm` 슬라이드별 이미지, render manifest 생성 (구현 완료, PowerPoint 렌더는 아직 없음)
- contact sheet 생성 (예정)
- `quality_check.py`: 잘림, 겹침, 정렬, 여백과 밀도 검사 (예정)
- `visual_check.py`: 고정 루브릭 기반 비전 평가 (예정)
- 자동 수정 3~5회 후 사람 확인
- 검사 순서는 콘텐츠 QA → 구조 QA → 시각 QA 3단계로 둡니다. 계층 분리와 참고 근거는 [ARCHITECTURE.md](ARCHITECTURE.md)를 따릅니다.

종료 조건: 정상 샘플은 통과하고 고의 불량 픽스처는 기대한 검사에서 실패합니다.

## 최종 완료 정의

- 외부 초안을 두 모드로 안정적으로 변환
- 승인 브랜드 규칙만 실행에 사용
- PPTX, PDF, PNG와 검사 리포트 동시 생성
- Windows와 macOS 재현성 확인
- 폰트 임베딩 또는 정적 대체 경로 검증
- 문서, 상태, 자산과 코드의 동기화 CI 통과
