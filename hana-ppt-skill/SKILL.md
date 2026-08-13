---
name: hana-ppt-skill
description: Develop, maintain, and eventually run the Hana Securities PowerPoint post-processing skill. Use when Codex needs to inspect or update Hana/HFG PPT design references, bundled fonts and CI assets, candidate or approved brand tokens, slide layout rules, PPTX restyling workflows, rendering validation, or the repository's documentation and state synchronization. Do not claim Hana Securities brand fidelity while only candidate HFG IR evidence is available.
---

# 하나증권 PPT 후처리 스킬

## 작업 전 확인

1. 이 스킬의 소스 저장소에서 개발할 때는 저장소 루트의 `project-state.json`과 `docs/STATUS.md`를 읽는다.
2. `assets/brand.json`이 없으면 승인된 브랜드 규칙이 없는 것으로 처리한다.
3. `assets/brand.candidate.json`과 `assets/layouts.candidate.json`은 검토·분석에만 사용하고 하나증권 공식 스타일로 단정하지 않는다.
4. 레퍼런스의 포함·제외 상태는 `assets/reference-decks/sources.json`과 `assets/reference-analysis.json`을 따른다.

## 요청 분기

- 레퍼런스 분석: `references/reference-analysis.md`와 관련 문서군 패턴만 읽는다.
- 색상·서체·로고: `references/design-tokens.md`, 폰트 manifest와 CI 자산을 읽는다.
- 레이아웃: `references/layout-patterns.md`와 해당 문서군 패턴을 읽는다.
- PPT 변환: 승인된 `brand.json`과 실행 스크립트가 모두 있을 때만 실행한다. 없으면 현재 미구현 또는 승인 대기 항목을 정확히 보고한다.
- 품질 검사: 기준 이미지 전체 픽셀 일치가 아니라 화면비, 고정 요소, 경계, 정렬, 밀도와 색상 분포를 비교한다.

## 변경 원칙

1. 브랜드 사실은 JSON에, 설명은 references에 둔다. 같은 수치를 여러 문서에 반복하지 않는다.
2. 후보와 승인 상태를 분리한다.
3. 예외 레퍼런스는 스타일 토큰이나 기준 이미지에 포함하지 않는다.
4. 소스 저장소의 구현·자산·문서가 바뀌면 `project-state.json`을 갱신한다.
5. 소스 저장소 작업 종료 시 루트의 `tools/task_harness.py check`를 실행한다.
6. 사용자가 커밋·푸시를 요청했거나 저장소 지침이 자동 게시를 요구하면 작업 전에 `begin`, 종료 시 `finish --message`를 실행한다.

## 현재 한계

현재 레퍼런스 후보는 하나금융그룹 IR 자료에 기반한다. 대표성이 확인된 하나증권 레퍼런스, 승인된 `brand.json`, PPT 변환 스크립트와 렌더 검증이 갖춰질 때까지 완성된 하나증권 PPT 변환 기능으로 취급하지 않는다.
