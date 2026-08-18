# 현재 프로젝트 상태

<!-- 이 파일은 project-state.json에서 생성됩니다. 직접 편집하지 마세요. -->

- 갱신일: `2026-08-18`
- 현재 단계: `brand-profile-approved`
- 요약: 로컬 HFG IR 2건을 사용자 승인 운영 기준으로 삼아 출처·한계를 명시한 brand.json과 voice.json을 확정했다. 하나증권 공식 CI·공식 문체로 주장하지 않는다. PPT 처리 계층을 엔진(범용 PPTX 조작)과 규칙(하나증권 브랜드·문체) 두 겹으로 분리하기로 하고, LibreOffice+poppler 기반 render_slides.py를 첫 엔진 겹 구성요소로 추가했다. 후처리·생성·구조/시각 품질 검사 구현은 남아 있다.

## 단계별 상태

| 단계 | 상태 | 근거 | 남은 항목 |
|---|---|---|---|
| 요구사항과 설계 결정 | 완료 | `docs/PRODUCT.md`<br>`docs/ARCHITECTURE.md`<br>`docs/ROADMAP.md` | - |
| 스킬 스켈레톤과 입력 자산 | 완료 | `hana-ppt-skill/SKILL.md`<br>`hana-ppt-skill/agents/openai.yaml`<br>`hana-ppt-skill/assets/fonts/manifest.json`<br>`hana-ppt-skill/assets/asset-manifest.json`<br>`.github/workflows/repository-harness.yml`<br>`README.md`<br>`requirements.txt`<br>`tests/test_repository.py` | - |
| 브랜드 토큰 추출 | 완료 | `hana-ppt-skill/assets/brand.json`<br>`hana-ppt-skill/assets/brand.candidate.json`<br>`hana-ppt-skill/references/design-tokens.md` | - |
| 레이아웃 패턴 | 후보 완료 | `hana-ppt-skill/assets/layouts.candidate.json`<br>`hana-ppt-skill/references/hfg-ir-patterns.md`<br>`hana-ppt-skill/references/layout-patterns.md` | 하나증권 대표 레이아웃<br>사람 승인 |
| 문체와 말투 규칙 | 완료 | `hana-ppt-skill/assets/voice.json`<br>`hana-ppt-skill/references/voice-and-tone.md`<br>`hana-ppt-skill/assets/reference-analysis.json` | - |
| PPT 인수·후처리·생성 | 진행 중 | `hana-ppt-skill/scripts/ingest_deck.py`<br>`hana-ppt-skill/schemas/deck_spec.schema.json`<br>`tests/test_repository.py` | restyle_deck.py<br>build_deck.py<br>차트·SmartArt 상세 인수<br>실제 PPTX 회귀 픽스처 |
| 구조·렌더·시각 품질 검사 | 진행 중 | `hana-ppt-skill/assets/baselines`<br>`hana-ppt-skill/scripts/render_slides.py`<br>`tests/test_repository.py` | quality_check.py<br>visual_check.py<br>contact sheet 생성<br>PowerPoint 렌더러 경로<br>render_slides.py 통합 테스트(soffice/pdftoppm 필요) |
| 호환성 검증과 배포 | 미착수 | - | Windows/macOS 검증<br>폰트 임베딩 검증<br>샘플 산출물 |

## 레퍼런스 상태

- 스타일 학습 포함: `hfg-1q26-kor`, `hfg-1h26-kor`
- 스타일 학습 제외: `hana-securities-2026-08-market-strategy`
- 주의: 로컬 HFG IR 2건은 사용자 승인된 운영 기준이지만 하나증권 공식 IR 또는 공식 CI 근거는 아니다. 제외된 리서치 자료는 계속 학습에서 제외한다.

## 다음 작업

1. 엔진 겹(범용 PPTX 조작)과 규칙 겹(하나증권 브랜드·문체) 분리 원칙에 맞춰, 승인된 운영 브랜드·문체 프로필을 주입하는 restyle_deck.py와 build_deck.py를 구현한다.
2. 실제 PPTX 회귀 픽스처로 인수 MVP의 차트·SmartArt 경고와 손실 보고를 보강한다.
3. CI 가이드를 확보하면 로고 보호영역과 공식 색상 수치만 별도 재검수한다.
4. render_slides.py 출력을 입력으로 받는 quality_check.py(구조 QA)와 visual_check.py(시각 QA)를 구현하고, 콘텐츠 QA → 구조 QA → 시각 QA 3단계 파이프라인을 완성한다.
5. contact sheet 생성과 PowerPoint 우선 렌더 경로를 추가한다.
