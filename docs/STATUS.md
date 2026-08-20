# 현재 프로젝트 상태

<!-- 이 파일은 project-state.json에서 생성됩니다. 직접 편집하지 마세요. -->

- 갱신일: `2026-08-20`
- 현재 단계: `brand-voice-layout-profiles-approved`
- 요약: 로컬 HFG IR 2건을 사용자 승인 운영 기준으로 삼아 출처·한계를 명시한 brand.json, voice.json, layouts.json을 모두 확정했다. 하나증권 공식 CI·공식 문체·공식 레이아웃으로 주장하지 않는다. PPT 처리 계층을 엔진(범용 PPTX 조작)과 규칙(하나증권 브랜드·문체·레이아웃) 두 겹으로 분리하기로 하고, render_slides.py에 이어 restyle_deck.py(restyle-only + hana-refine, 텍스트 런 수준)와 build_deck.py(deck_spec.json에서 새 PPTX 생성)를 추가했다. 2026-08-18에 layouts.candidate.json의 6개 패턴을 사람이 전체 승인해 layouts.json으로 승격했고, build_deck.py에 --layouts/--layout-plan을 받아 cover/section-divider/disclaimer 역할별로 배치하는 1차 구현을 추가했다(strategic-kpi/executive-summary/closing과 장식 요소는 아직 없음). restyle_deck.py(기존 파일 편집)의 레이아웃 수준 재구성은 아직 시작 전이고, 구조/시각 품질 검사 구현도 남아 있다. 2026-08-20에 사용자가 하나 공식 CI 컬러 시스템과 하나2.0 서체 사용 규정 수치를 직접 제공해 ci-colors.json/ci-typography.json(둘 다 official_ci_specification: true)으로 등록했다. 처음 안내한 외부 URL은 이 세션의 egress 정책이 차단해(우회하지 않음) 사용자가 같은 PDF(하나증권 회사소개서, 2025 Hana Securities Profile)를 직접 첨부했고, reference-decks/hana-securities에 등록해 표지 배경색·로고 색상을 픽셀 단위로 대조한 결과 Hana Green/Hana Ren 수치와 정확히 일치함을 확인했다. 같은 문서에서 심볼마크(투명 배경 PNG, 심볼 단독/워드마크 포함 두 종)를 추출해 등록했다. Hana Point Green의 RGB/HEX 불일치는 그라데이션 레이어 때문에 픽셀 대조로 해소하지 못했고, 로고 보호영역·최소 크기·Special 컬러 수치는 여전히 미확정이라 brand.json에는 아직 병합하지 않았다.

## 단계별 상태

| 단계 | 상태 | 근거 | 남은 항목 |
|---|---|---|---|
| 요구사항과 설계 결정 | 완료 | `docs/PRODUCT.md`<br>`docs/ARCHITECTURE.md`<br>`docs/ROADMAP.md` | - |
| 스킬 스켈레톤과 입력 자산 | 완료 | `hana-ppt-skill/SKILL.md`<br>`hana-ppt-skill/agents/openai.yaml`<br>`hana-ppt-skill/assets/fonts/manifest.json`<br>`hana-ppt-skill/assets/asset-manifest.json`<br>`.github/workflows/repository-harness.yml`<br>`README.md`<br>`requirements.txt`<br>`tests/test_repository.py` | - |
| 브랜드 토큰 추출 | 완료 | `hana-ppt-skill/assets/brand.json`<br>`hana-ppt-skill/assets/brand.candidate.json`<br>`hana-ppt-skill/references/design-tokens.md`<br>`hana-ppt-skill/assets/ci-colors.json`<br>`hana-ppt-skill/assets/ci-typography.json`<br>`hana-ppt-skill/references/official-ci-specification.md`<br>`hana-ppt-skill/assets/logo/HanaSecurities_symbol-mark.png`<br>`hana-ppt-skill/assets/logo/HanaSecurities_logo-lockup.png`<br>`hana-ppt-skill/assets/reference-decks/hana-securities/2025_Hana_Securities_Profile.pdf` | 공식 CI 컬러·서체(ci-colors.json/ci-typography.json)를 brand.json 운영 정본에 병합 — 로고 보호영역 등 나머지 공식 CI 요소 확보 후 진행<br>Hana Point Green RGB/HEX 불일치 재확인<br>심볼마크 보호영역·최소 크기·배경별 사용 규칙<br>Special 컬러(Gold/Light Gold/Silver) CMYK/RGB/HEX 수치 |
| 레이아웃 패턴 | 완료 | `hana-ppt-skill/assets/layouts.json`<br>`hana-ppt-skill/assets/layouts.candidate.json`<br>`hana-ppt-skill/references/hfg-ir-patterns.md`<br>`hana-ppt-skill/references/layout-patterns.md` | - |
| 문체와 말투 규칙 | 완료 | `hana-ppt-skill/assets/voice.json`<br>`hana-ppt-skill/references/voice-and-tone.md`<br>`hana-ppt-skill/assets/reference-analysis.json` | - |
| PPT 인수·후처리·생성 | 진행 중 | `hana-ppt-skill/scripts/ingest_deck.py`<br>`hana-ppt-skill/scripts/restyle_deck.py`<br>`hana-ppt-skill/scripts/build_deck.py`<br>`hana-ppt-skill/scripts/text_units.py`<br>`hana-ppt-skill/scripts/verify_evidence_preserved.py`<br>`hana-ppt-skill/references/hana-refine-workflow.md`<br>`hana-ppt-skill/schemas/deck_spec.schema.json`<br>`tests/test_repository.py` | build_deck.py의 strategic-kpi/executive-summary/closing 역할 배치와 장식 요소(적색 선, 원형 모티프)<br>restyle_deck.py(기존 파일 편집)의 레이아웃 배치 수준 재구성 — 아직 전혀 없음<br>build_deck.py의 이미지·그래픽·SmartArt 재현<br>차트·SmartArt 상세 인수<br>실제 PPTX 회귀 픽스처 |
| 구조·렌더·시각 품질 검사 | 진행 중 | `hana-ppt-skill/assets/baselines`<br>`hana-ppt-skill/scripts/render_slides.py`<br>`tests/test_repository.py` | quality_check.py<br>visual_check.py<br>contact sheet 생성<br>PowerPoint 렌더러 경로<br>render_slides.py 통합 테스트(soffice/pdftoppm 필요) |
| 호환성 검증과 배포 | 미착수 | - | Windows/macOS 검증<br>폰트 임베딩 검증<br>샘플 산출물 |

## 레퍼런스 상태

- 스타일 학습 포함: `hfg-1q26-kor`, `hfg-1h26-kor`
- 스타일 학습 제외: `hana-securities-2026-08-market-strategy`
- 주의: 로컬 HFG IR 2건은 사용자 승인된 운영 기준이지만 하나증권 공식 IR 또는 공식 CI 근거는 아니다. 제외된 리서치 자료는 계속 학습에서 제외한다.

## 다음 작업

1. build_deck.py에 strategic-kpi(원형 KPI 카드), executive-summary(좌 KPI카드/우 설명모듈), closing 역할 배치를 추가한다.
2. restyle_deck.py(기존 파일 편집)를 layouts.json 기반 레이아웃 배치 수준으로 확장한다.
3. 실제 PPTX 회귀 픽스처로 인수 MVP의 차트·SmartArt 경고와 손실 보고를 보강한다.
4. 공식 CI 컬러 수치는 확보해 ci-colors.json으로 등록·검증했다. 남은 것은 로고 보호영역·최소 크기, Hana Point Green 불일치 재확인, Special 컬러 수치이며 확보되는 대로 brand.json에 병합하고 관련 테스트를 갱신한다.
5. render_slides.py 출력을 입력으로 받는 quality_check.py(구조 QA)와 visual_check.py(시각 QA)를 구현하고, 콘텐츠 QA → 구조 QA → 시각 QA 3단계 파이프라인을 완성한다.
6. contact sheet 생성과 PowerPoint 우선 렌더 경로를 추가한다.
