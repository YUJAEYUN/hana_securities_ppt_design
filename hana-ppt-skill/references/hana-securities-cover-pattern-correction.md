# cover·section-divider 패턴 정정 기록 (2026-08-20)

## 무엇이 바뀌었나

`layouts.json`의 `cover`, `section-divider` 패턴은 원래 하나금융그룹(그룹사) IR 2건만 보고 추정한 값이었다. `layouts.json` 자체에 "그룹 IR의 원형 모티프·슬로건처럼 그룹 고유 문법은 하나증권 자료에 무조건 복제하지 않는다"는 한계가 이미 적혀 있었는데, 실제 하나증권 자료(`reference-decks/hana-securities/2025_Hana_Securities_Profile.pdf`, source_id `hana-securities-2025-profile`)를 사용자가 제공해 대조해 보니 그 우려가 맞았다.

| 패턴 | 옛 추정(HFG IR 근거) | 실제 하나증권 자료 |
|---|---|---|
| cover | 흰 배경 + 좌상단 로고 + 얇은 적색 강조선 + 우하단 초록 원형 모티프 | 전체 배경이 `primary_green`으로 꽉 참, 흰 제목·부제 좌측 정렬, 우상단에 흰 알약형 배지 안 심볼마크, 하단 흰 띠에 로고 조합 |
| section-divider | 가운데 정렬 제목 + 배경에 옅은 대형 원형 모티프 + 우측 미니 목차 | 전체 배경이 `primary_green`으로 꽉 참, 흰 제목이 좌측 정렬로 화면 중하단에, 그 아래 옅은 하위 목차. 원형 모티프 없음 |

증거: 표지(1p), INTRODUCTION 섹션 구분(3p), 핵심사업 섹션 구분(10p) — 서로 다른 두 챕터의 섹션 구분 페이지가 같은 패턴을 써서 우연이 아니라 일관된 규칙임을 확인했다.

## 반영 범위

- `build_deck.py`의 `_decorations_for_role`가 cover/section-divider에 대해 이제 전체 슬라이드를 `primary_green`으로 채우는 배경 도형 하나만 그린다(적색선·원형 모티프 삭제).
- 제목(과 표지 부제)은 흰색(`#FFFFFF`)으로 그린다.
- 정렬은 둘 다 왼쪽 그대로라 별도 처리가 필요 없다(이전에 section-divider에만 넣었던 가운데 정렬을 제거했다).
- 로고(심볼마크 배지, 하단 로고 조합)는 이번 정정 범위에 포함하지 않는다. 보호영역·최소 크기가 여전히 미확정이라 `brand.json.logo.policy`에 따라 자동 배치하지 않고 경고로만 남긴다.

## 반영하지 않은 범위

- `strategic-kpi`, `executive-summary`, `data-body`(장식 제외), `disclaimer`, `closing` 패턴은 이번에 대조하지 않았다. 여전히 HFG IR 2건 근거다.
- 실제 자료의 재무 현황 표(5p) 스타일(진한 헤더 + 부분합 행 옅은 배경)은 별도로 `layouts.json`의 `data-body.table_colors`에 `band_row`로 반영했지만, "어느 행이 부분합인지"는 deck_spec에 표시가 없어 추측하지 않았다. 대신 홀수 번째 본문 행마다 기계적으로 줄무늬를 넣는 방식으로 가독성만 재현한다.

## 남은 작업

- 심볼마크 배지·로고 조합의 정확한 배치 좌표와 여백을 확보하면 cover 패턴에 반영한다.
- 나머지 패턴(strategic-kpi 등)도 실제 하나증권 자료에 해당 슬라이드 유형이 있으면 같은 방식으로 재검증한다.
