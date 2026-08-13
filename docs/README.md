# 하나증권 PPT 디자인 스킬 구축 문서

이 디렉터리는 `hana-ppt-skill` 구현을 시작하기 전에 요구사항과 실행 순서를 고정하기 위한 작업 문서다. 실제 스킬 산출물은 추후 저장소 루트의 `hana-ppt-skill/`에 만든다.

## 목표

하나증권/하나금융그룹의 기존 PPT 샘플에서 브랜드 토큰과 레이아웃 관례를 추출하고, 그 결과를 바탕으로 Claude Code와 Codex 양쪽에서 사용할 수 있는 PPT 생성·검사 스킬을 구축한다.

핵심 원칙은 다음과 같다.

- 브랜드 값은 `assets/brand.json` 한 곳에서만 관리한다.
- 브랜드 정체성과 레이아웃 구조를 분리한다.
- 각 슬라이드를 만들 때 `brand.json`을 다시 읽어 스타일 드리프트를 막는다.
- 애니메이션, 과도한 그림자와 그라데이션은 기본적으로 끈다.
- 자동 수정은 실패 항목에만 적용하고 3~5회 후 반드시 사람 확인을 받는다.
- 특정 AI 벤더 API나 전용 MCP에 의존하지 않는다.

## 실행 순서

| 순서 | 문서 | 결과 |
|---|---|---|
| 0 | [00-requirements-and-decisions.md](00-requirements-and-decisions.md) | 요구사항, 범위, 설계 결정 확정 |
| 1 | [01-scaffold-and-inputs.md](01-scaffold-and-inputs.md) | 디렉터리 스켈레톤과 입력 자료 준비 |
| 2 | [02-token-extraction.md](02-token-extraction.md) | `extract_tokens.py`, `design-tokens.md`, `brand.json` |
| 3 | [03-layout-patterns.md](03-layout-patterns.md) | 슬라이드 유형별 레이아웃 규칙 |
| 4 | [04-skill-and-deck-builder.md](04-skill-and-deck-builder.md) | 스킬 지침과 5종 이상의 슬라이드 생성기 |
| 5 | [05-quality-and-iteration.md](05-quality-and-iteration.md) | 자동 검사, 정성 체크, 제한 반복 루프 |
| 6 | [06-compatibility-and-delivery.md](06-compatibility-and-delivery.md) | 양 환경 재현성 검증과 최종 인수 |

## 단계 게이트

각 단계는 해당 문서의 완료 조건을 충족한 뒤 다음 단계로 넘어간다. 특히 2단계의 `brand.json`이 확정되기 전에는 생성기 스타일을 임의로 하드코딩하지 않는다.

## 현재 준비가 필요한 외부 입력

- 하나증권/하나금융그룹 샘플 PPTX 5개 이상
- 사용 승인이 완료된 CI 폰트 원본
- SVG 또는 고해상도 PNG 로고 원본
- 가능하면 슬라이드 유형별 대표 사례와 최신/정식 양식 표시

이 자료가 없더라도 스켈레톤과 테스트 구조는 만들 수 있지만, 실제 브랜드 값 확정과 완료 기준 충족은 불가능하다.


