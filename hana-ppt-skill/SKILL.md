---
name: hana-ppt-skill
description: Develop, maintain, and eventually run the Hana Securities PowerPoint post-processing skill. Use when Codex needs to inspect or update Hana/HFG PPT design references, bundled fonts and CI assets, candidate or approved brand tokens, slide layout rules, PPTX restyling workflows, rendering validation, or the repository's documentation and state synchronization. Do not claim Hana Securities brand fidelity while only candidate HFG IR evidence is available.
---

# 하나증권 PPT 후처리 스킬

## 작업 전 확인

1. 이 스킬의 소스 저장소에서 개발할 때는 저장소 루트의 `project-state.json`과 `docs/STATUS.md`를 읽는다.
2. `assets/brand.json`이 없으면 승인된 운영 브랜드 규칙이 없는 것으로 처리한다. 파일이 있어도 `official_ci_specification`과 승인 범위를 확인한다. `assets/layouts.json`도 같은 방식으로 확인한다(`official_hana_securities_layout`과 승인 범위).
3. `assets/brand.candidate.json`과 `assets/layouts.candidate.json`은 승인 전 검토·분석 기록으로만 보존한다. 실행에는 승인된 `brand.json`/`layouts.json`만 쓴다.
4. 레퍼런스의 포함·제외 상태는 `assets/reference-decks/sources.json`과 `assets/reference-analysis.json`을 따른다.

## 요청 분기

- 레퍼런스 분석: `references/reference-analysis.md`와 관련 문서군 패턴만 읽는다.
- 색상·서체·로고: `references/design-tokens.md`(운영 프로필 근거), 폰트 manifest와 CI 자산을 읽는다. 사용자가 제공한 공식 CI 컬러·서체 수치는 `assets/ci-colors.json`/`assets/ci-typography.json`(둘 다 `official_ci_specification: true`)과 `references/official-ci-specification.md`를 따로 둔다. 이 공식 CI 정본은 아직 `brand.json`(운영 프로필, `official_ci_specification: false`)에 병합되지 않았으므로 실행 스크립트는 여전히 `brand.json`만 쓴다. 심볼마크는 `assets/logo/HanaSecurities_symbol-mark.png`/`HanaSecurities_logo-lockup.png`(실제 배포 자료에서 추출, 투명 배경)와 기존 `assets/logo/HanaSecurities_CI.ai`(벡터 원본)를 함께 참고하되, 보호영역·최소 크기가 없으므로 자동 배치에는 쓰지 않는다.
- 문체·말투: `assets/voice.json`을 실행 정본으로, `references/voice-and-tone.md`를 판단 근거로 읽는다. `restyle-only`에서는 진단만 하고 원문을 바꾸지 않으며, `hana-refine`에서도 수치·기간·비교 기준을 잠근다.
- 레이아웃: `assets/layouts.json`을 실행 정본으로, `references/layout-patterns.md`(문서군 공통 선택 규칙)와 `references/hfg-ir-patterns.md`(hfg-ir 문서군 패턴)를 판단 근거로 읽는다.
- PPT 인수: `scripts/ingest_deck.py`로 원본을 변경하지 않고 `deck_spec.json` 인벤토리를 생성한다. 미지원 요소 경고를 손실 없는 변환 성공으로 간주하지 않는다.
- PPT 후처리(기존 파일 편집): `scripts/restyle_deck.py`가 승인된 `brand.json`의 색상·폰트를 PPTX 테마 파트에 적용한다(`restyle-only`). `hana-refine`은 `references/hana-refine-workflow.md`의 절차(추출 → 에이전트 재작성 → `verify_evidence_preserved`로 수치·비교기준 검증 → 적용)를 따른다. 검증에 실패하면 어떤 슬라이드도 수정하지 않는다.
- PPT 생성(신규 작성): `scripts/build_deck.py`가 `deck_spec.json`과 승인된 `brand.json`으로 새 PPTX를 만든다. `--layouts`/`--layout-plan`을 안 주면 슬라이드마다 제목 + (불릿 또는 표) 하나짜리 기본(data-body) 레이아웃만 생성한다. `--layout-plan`으로 슬라이드별 역할(`cover`/`section-divider`/`disclaimer`/`data-body`)을 지정하면 역할별로 다르게 배치한다 — 어떤 슬라이드가 표지인지 같은 판단은 에이전트/사람이 하고, 스크립트는 그 판단을 기계적으로 실행만 한다(hana-refine의 `edits.json`과 같은 원칙). `strategic-kpi`/`executive-summary`/`closing` 역할별 배치는 아직 없다. `layouts.json` 패턴에 있던 장식 요소 중 벡터로 그릴 수 있는 것(cover의 적색 강조선·초록 원형 모티프, section-divider의 옅은 원형 모티프, data-body의 제목 밑줄)은 OOXML 프리셋 도형으로 그린다. 로고는 보호영역 미확정으로 여전히 자동 배치하지 않는다(경고로 보고). 이미지·그래픽 요소는 재현하지 않고 경고로 보고한다.
- `restyle_deck.py`(기존 파일 편집)의 레이아웃 배치 수준 재구성은 아직 없다. 없는 기능을 있는 것처럼 보고하지 않는다.
- PPT 렌더: `scripts/render_slides.py`로 PPTX를 PDF와 슬라이드별 이미지로 변환하고 render manifest를 만든다. `soffice`나 `pdftoppm`이 없으면 명확한 오류로 중단하며 조용히 건너뛰지 않는다.
- 품질 검사: 기준 이미지 전체 픽셀 일치가 아니라 화면비, 고정 요소, 경계, 정렬, 밀도와 색상 분포를 비교한다. 콘텐츠 QA → 구조 QA → 시각 QA 순서를 따른다.

## 변경 원칙

1. 브랜드 사실은 JSON에, 설명은 references에 둔다. 같은 수치를 여러 문서에 반복하지 않는다.
2. 후보와 승인 상태를 분리한다.
3. 예외 레퍼런스는 스타일 토큰이나 기준 이미지에 포함하지 않는다.
4. 외부 스킬(Anthropic 공식 pptx 스킬 등)의 흐름과 아이디어는 참고하되 코드는 복제하지 않는다. 재배포가 금지된 라이선스 자료는 독자 구현으로 대체한다.
5. 소스 저장소의 구현·자산·문서가 바뀌면 `project-state.json`을 갱신한다.
6. 소스 저장소 작업 종료 시 루트의 `tools/task_harness.py check`를 실행한다.
7. 사용자가 커밋·푸시를 요청했거나 저장소 지침이 자동 게시를 요구하면 작업 전에 `begin`, 종료 시 `finish --message`를 실행한다.

## 현재 한계

현재 `brand.json`과 `layouts.json`은 모두 사용자가 로컬 하나금융그룹 IR 자료를 기준으로 승인한 운영 프로필이며 하나증권 공식 CI·레이아웃 규격이 아니다. PPT 변환 스크립트와 렌더 검증이 갖춰질 때까지 완성된 하나증권 PPT 변환 기능으로 취급하지 않는다. `build_deck.py`는 `cover`/`section-divider`/`disclaimer` 세 역할만 배치를 지원하고 나머지 역할은 기본(data-body) 레이아웃으로 대체된다. `restyle_deck.py`(기존 파일 편집)는 레이아웃 배치 수준 재구성이 아직 전혀 없다.

사용자가 공식 CI 컬러·서체 수치와 실제 하나증권 배포 자료(심볼마크 추출·색상 검증에 사용)를 제공해 `assets/ci-colors.json`/`assets/ci-typography.json`으로 등록했지만(`official_ci_specification: true`), 이 값은 아직 `brand.json`에 병합되지 않았고 실행 스크립트가 사용하지도 않는다. `references/official-ci-specification.md`의 "남은 작업"이 모두 채워지기 전까지 `brand.json`을 공식 CI 기준으로 바꾸지 않는다.
