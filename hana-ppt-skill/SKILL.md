---
name: hana-ppt-skill
description: Develop, maintain, and eventually run the Hana Securities PowerPoint post-processing skill. Use when Codex needs to inspect or update Hana/HFG PPT design references, bundled fonts and CI assets, candidate or approved brand tokens, slide layout rules, PPTX restyling workflows, rendering validation, or the repository's documentation and state synchronization. Do not claim Hana Securities brand fidelity while only candidate HFG IR evidence is available.
---

# 하나증권 PPT 후처리 스킬

## 작업 전 확인

1. 이 스킬의 소스 저장소에서 개발할 때는 저장소 루트의 `project-state.json`과 `docs/STATUS.md`를 읽는다.
2. `assets/brand.json`이 없으면 승인된 운영 브랜드 규칙이 없는 것으로 처리한다. 파일이 있어도 `official_ci_specification`과 승인 범위를 확인한다.
3. `assets/brand.candidate.json`과 `assets/layouts.candidate.json`은 검토·분석에만 사용하고 하나증권 공식 스타일로 단정하지 않는다.
4. 레퍼런스의 포함·제외 상태는 `assets/reference-decks/sources.json`과 `assets/reference-analysis.json`을 따른다.

## 요청 분기

- 레퍼런스 분석: `references/reference-analysis.md`와 관련 문서군 패턴만 읽는다.
- 색상·서체·로고: `references/design-tokens.md`, 폰트 manifest와 CI 자산을 읽는다.
- 문체·말투: `assets/voice.json`을 실행 정본으로, `references/voice-and-tone.md`를 판단 근거로 읽는다. `restyle-only`에서는 진단만 하고 원문을 바꾸지 않으며, `hana-refine`에서도 수치·기간·비교 기준을 잠근다.
- 레이아웃: `references/layout-patterns.md`와 해당 문서군 패턴을 읽는다.
- PPT 인수: `scripts/ingest_deck.py`로 원본을 변경하지 않고 `deck_spec.json` 인벤토리를 생성한다. 미지원 요소 경고를 손실 없는 변환 성공으로 간주하지 않는다.
- PPT 후처리: 승인된 `brand.json`과 후처리 실행 스크립트가 모두 있을 때만 실행한다. 없으면 현재 미구현 또는 승인 대기 항목을 정확히 보고한다.
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

현재 `brand.json`은 사용자가 로컬 하나금융그룹 IR 자료를 기준으로 승인한 운영 프로필이며 하나증권 공식 CI 규격이 아니다. PPT 변환 스크립트와 렌더 검증이 갖춰질 때까지 완성된 하나증권 PPT 변환 기능으로 취급하지 않는다.
