# 하나증권 PPT 디자인 스킬 구축 문서

이 디렉터리는 `hana-ppt-skill` 구현을 시작하기 전에 요구사항과 실행 순서를 고정하기 위한 작업 문서다. 실제 스킬 산출물은 추후 저장소 루트의 `hana-ppt-skill/`에 만든다.

## 목표

하나증권/하나금융그룹의 기존 PPT 샘플에서 브랜드 토큰과 레이아웃 관례를 추출하고, 다른 PPT 생성 스킬이나 에이전트가 만든 초안을 하나증권식 말투·구조·디자인으로 변환하고 검사하는 후처리 스킬을 구축한다.

핵심 원칙은 다음과 같다.

- 브랜드 값은 `assets/brand.json` 한 곳에서만 관리한다.
- Windows용과 macOS용 CI/하나서체 원본은 저장소의 `assets/fonts/`에 함께 보관한다.
- 브랜드 정체성과 레이아웃 구조를 분리한다.
- 각 슬라이드를 만들 때 `brand.json`을 다시 읽어 스타일 드리프트를 막는다.
- 애니메이션, 과도한 그림자와 그라데이션은 기본적으로 끈다.
- 자동 수정은 실패 항목에만 적용하고 3~5회 후 반드시 사람 확인을 받는다.
- 특정 AI 벤더 API나 전용 MCP에 의존하지 않는다.
- 하나의 스킬에서 `restyle-only`와 `hana-refine` 두 후처리 워크플로를 제공한다.
- 조사, 팩트 수집과 범용 PPT 초안 생성은 다른 리서치 에이전트나 PPT 생성 스킬이 담당한다.
- 이 스킬은 첨부된 PPTX 또는 구조화된 초안을 하나증권식 디자인과 말투로 다듬는다.
- 사용자는 PPTX를 직접 편집하지 않고 AI에게 변경을 요청한다. AI는 정본인 `deck_spec.json`을 수정해 모든 결과물을 다시 생성한다.
- 결과 PPTX를 실제 렌더러로 슬라이드별 PNG로 변환한 뒤 이미지 검사와 비전 에이전트 평가를 수행한다.

## 실행 순서

| 순서 | 문서 | 결과 |
|---|---|---|
| 0 | [00-requirements-and-decisions.md](00-requirements-and-decisions.md) | 요구사항, 범위, 설계 결정 확정 |
| 1 | [01-scaffold-and-inputs.md](01-scaffold-and-inputs.md) | 디렉터리 스켈레톤과 입력 자료 준비 |
| 2 | [02-token-extraction.md](02-token-extraction.md) | `extract_tokens.py`, `design-tokens.md`, `brand.json` |
| 3 | [03-layout-patterns.md](03-layout-patterns.md) | 슬라이드 유형별 레이아웃 규칙 |
| 4 | [04-skill-and-deck-builder.md](04-skill-and-deck-builder.md) | 초안 인수, 하나증권식 후처리, 스킬 지침과 렌더러 |
| 5 | [05-quality-and-iteration.md](05-quality-and-iteration.md) | 자동 검사, 정성 체크, 제한 반복 루프 |
| 6 | [06-compatibility-and-delivery.md](06-compatibility-and-delivery.md) | 양 환경 재현성 검증과 최종 인수 |

## 단계 게이트

각 단계는 해당 문서의 완료 조건을 충족한 뒤 다음 단계로 넘어간다. 특히 2단계의 `brand.json`이 확정되기 전에는 생성기 스타일을 임의로 하드코딩하지 않는다.

## 현재 확보된 외부 입력

- Windows용 하나2.0 TTF 6종 원본 ZIP
- macOS용 하나2.0 OTF 6종 원본 ZIP
- 하나증권 CI Illustrator 원본
- 하나금융그룹 2026년 1분기·상반기 발표자료 PDF
- 하나증권 리서치센터 2026년 8월 주식시장 전망 자료 URL

폰트는 원본 ZIP으로 보존하고 실행 시 작업 캐시에 안전하게 풀어 사용한다. 모두 `Editable embedding (fsType 0x0008)`이며 서브셋 임베딩이 허용되는 것으로 확인됐다. 정확한 ZIP 멤버, 패밀리명과 스타일 대응은 `hana-ppt-skill/assets/fonts/manifest.json`에서 관리한다.

## 추가로 필요한 외부 입력

- 추가 하나증권/하나금융그룹 샘플 PPTX 또는 PDF 2개 이상
- PPTX 생성에 바로 사용할 SVG 또는 고해상도 PNG 로고 원본 또는 CI Illustrator 원본의 변환 승인
- 가능하면 슬라이드 유형별 대표 사례와 최신/정식 양식 표시

색상, 폰트 패밀리명과 로고 값은 자산 투입 전에는 미확정 상태로 두는 것이 정상이며 임의로 채우지 않는다. 폰트 파일은 저장소에 포함하고 PPT 생성 전에 형식, 패밀리명과 임베딩 권한을 검사한다. 사용된 글리프만 PPTX에 서브셋으로 임베딩해 수신자 PC에 폰트 설치를 요구하지 않는 것을 기본 경로로 삼고, PowerPoint 재열기와 폰트 미설치 렌더 결과까지 검증한다. 임베딩이 불가능하거나 검증에 실패하면 시각을 고정한 정적 PPTX와 PDF를 제공하며, 모든 경우에 PDF와 미리보기 PNG를 함께 생성한다.
