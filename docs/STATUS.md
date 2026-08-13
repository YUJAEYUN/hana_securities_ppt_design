# 현재 프로젝트 상태

<!-- 이 파일은 project-state.json에서 생성됩니다. 직접 편집하지 마세요. -->

- 갱신일: `2026-08-13`
- 현재 단계: `reference-analysis-candidate`
- 요약: 스킬 메타데이터와 브랜드 자산은 준비 중이며, HFG IR 레퍼런스 기반 후보 토큰과 레이아웃만 존재한다. 하나증권 대표 스타일과 PPT 생성·검사 구현은 아직 완료되지 않았다.

## 단계별 상태

| 단계 | 상태 | 근거 | 남은 항목 |
|---|---|---|---|
| 요구사항과 설계 결정 | 완료 | `docs/PRODUCT.md`<br>`docs/ARCHITECTURE.md`<br>`docs/ROADMAP.md` | - |
| 스킬 스켈레톤과 입력 자산 | 진행 중 | `hana-ppt-skill/SKILL.md`<br>`hana-ppt-skill/agents/openai.yaml`<br>`hana-ppt-skill/assets/fonts/manifest.json`<br>`hana-ppt-skill/assets/asset-manifest.json`<br>`.github/workflows/repository-harness.yml`<br>`README.md` | requirements.txt<br>PPT 처리 스크립트<br>테스트 |
| 브랜드 토큰 추출 | 후보 완료 | `hana-ppt-skill/assets/brand.candidate.json`<br>`hana-ppt-skill/references/design-tokens.md` | 대표 하나증권 레퍼런스<br>사람 승인<br>assets/brand.json<br>extract_tokens.py |
| 레이아웃 패턴 | 후보 완료 | `hana-ppt-skill/assets/layouts.candidate.json`<br>`hana-ppt-skill/references/hfg-ir-patterns.md`<br>`hana-ppt-skill/references/layout-patterns.md` | 하나증권 대표 레이아웃<br>사람 승인 |
| PPT 인수·후처리·생성 | 미착수 | - | ingest_deck.py<br>restyle_deck.py<br>build_deck.py<br>deck_spec 스키마 |
| 구조·렌더·시각 품질 검사 | 진행 중 | `hana-ppt-skill/assets/baselines` | quality_check.py<br>render_slides.py<br>visual_check.py<br>테스트 |
| 호환성 검증과 배포 | 미착수 | - | Windows/macOS 검증<br>폰트 임베딩 검증<br>샘플 산출물 |

## 레퍼런스 상태

- 스타일 학습 포함: `hfg-1q26-kor`, `hfg-1h26-kor`
- 스타일 학습 제외: `hana-securities-2026-08-market-strategy`
- 주의: 현재 디자인 후보는 하나금융그룹 IR 자료에만 근거한다. 하나증권 대표 스타일로 승인하거나 일반화하지 않는다.

## 다음 작업

1. 대표성이 확인된 하나증권 PPTX 또는 PDF를 추가한다.
2. CI Illustrator 원본을 SVG 또는 고해상도 PNG로 변환하고 보호영역을 확정한다.
3. PPT 인수·후처리 최소 스크립트와 테스트를 구현한다.
4. 후보 토큰을 사람 검수한 뒤 assets/brand.json으로 승격한다.
