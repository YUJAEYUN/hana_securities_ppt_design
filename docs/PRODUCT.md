# 제품 범위와 설계 결정

## 목적

완성된 PPT 초안을 하나증권식 말투·정보 계층·디자인으로 후처리하고, 결과의 브랜드·레이아웃·렌더링 품질을 검사하는 재사용 가능한 스킬을 만듭니다.

## 입력과 출력

입력:

- 외부 에이전트나 범용 PPT 도구가 만든 PPTX
- 또는 구조화된 `deck_spec.json`
- 목적, 청중, 보존해야 할 문구·수치·데이터와 출처

출력 목표:

- 폰트 임베딩을 검증한 PPTX 또는 시각을 고정한 정적 PPTX
- 배포 기준 PDF
- 슬라이드별 PNG와 contact sheet
- 구조·렌더·시각 품질 검사 리포트
- 원본과 결과의 슬라이드 대응표 및 변경 내역

## 실행 모드

### `restyle-only`

문장, 수치, 고유명사, 표와 차트 데이터를 잠급니다. 페이지 수와 배치는 개선할 수 있지만 콘텐츠 변경은 실패로 처리합니다.

### `hana-refine`

제공된 초안과 출처 범위 안에서 제목, 문장, 요약, 정보 계층과 디자인을 개선합니다. 새로운 사실을 만들지 않습니다.

## 책임 경계

포함:

- PPTX 구조 인수와 정규화
- 후보 또는 승인 브랜드 규칙 적용
- 하나증권식 문장·정보 계층 개선
- 폰트 전달 전략과 정적 대체
- 구조·렌더·이미지·비전 검사

제외:

- 범용 웹 조사와 팩트 수집
- 최초 발표 논리와 초안의 무근거 생성
- 사용자의 PowerPoint 직접 편집 지원
- 벤더 전용 AI API를 필수 실행 경로로 고정

## 핵심 결정

### 후보와 승인 분리

- `*.candidate.json`: 레퍼런스에서 추정했으나 사람 검수 전
- `brand.json`: 공식 자료와 사람 검수로 승인된 실행 정본
- 현재는 HFG IR 기반 후보만 있으며 하나증권 공식 스타일은 미승인입니다.

### 정본 기반 재생성

향후 모든 수정은 `deck_spec.json`에서 수행하고 PPTX, PDF와 PNG를 다시 생성합니다. 사용자의 직접 편집 가능성은 완료 기준이 아닙니다.

### 폰트

- Windows TTF와 macOS OTF 원본 ZIP을 저장소에 보존합니다.
- 실행 시 필요한 OS·스타일 멤버만 작업 캐시에 풉니다.
- 사용된 글리프만 서브셋 임베딩하고 PowerPoint 재열기와 미설치 렌더 결과를 검증합니다.
- 검증 실패 시 정적 PPTX와 PDF로 전환합니다.

### 품질 판정

검사 순서는 구조 → 실제 렌더 → 이미지 자동검사 → 비전 평가입니다. 렌더러가 없으면 휴리스틱 경고만 제공하고 전체 결과를 `partial`로 표시합니다.

## 승인 전 금지사항

- HFG 후보 색상을 하나증권 공식 CI 색상으로 표현하지 않습니다.
- 제외된 리서치 자료를 기준 이미지나 스타일 학습에 다시 넣지 않습니다.
- PPT 처리 스크립트가 없는데 변환 ۿy����k�w��monospace">sync · check · install · commit · push</text>

  <rect x="160" y="252" width="640" height="92" rx="8" fill="#fff" stroke="#2d3142" stroke-width="1.2"/>
  <rect x="176" y="264" width="64" height="16" rx="2" fill="none" stroke="rgba(45,49,66,0.3)"/>
  <text x="208" y="276" text-anchor="middle" fill="#4f5d75" font-size="8" font-family="Arial, sans-serif">SKILL</text>
  <text x="480" y="284" text-anchor="middle" fill="#2d3142" font-size="16" font-weight="600" font-family="Arial, 'Noto Sans KR', sans-serif">hana-ppt-skill</text>
  <text x="480" y="308" text-anchor="middle" fill="#4f5d75" font-size="12" font-family="Arial, 'Noto Sans KR', sans-serif">SKILL.md가 요청을 분기하고 references와 assets에서 근거를 선택</text>
  <text x="480" y="328" text-anchor="middle" fill="#7a8399" font-size="9" font-family="Consolas, monospace">후보 규칙 ≠ 승인된 하나증권 브랜드</text>

  <rect x="160" y="380" width="640" height="92" rx="8" fill="rgba(235,108,54,0.05)" stroke="rgba(235,108,54,0.55)" stroke-dasharray="4 4"/>
  <rect x="176" y="392" width="88" height="16" rx="2" fill="#f5f5f5"/>
  <text x="220" y="404" text-anchor="middle" fill="#eb6c36" font-size="8" font-family="Arial, sans-serif">PLANNED</text>
  <text x="480" y="412" text-anchor="middle" fill="#2d3142" font-size="16" font-weight="600" font-family="Arial, 'Noto Sans KR', sans-serif">PPT 처리 엔진</text>
  <text x="480" y="436" text-anchor="middle" fill="#4f5d75" font-size="12" font-family="Arial, 'Noto Sans KR', sans-serif">초안 인수 → deck_spec → 스타일 적용 → 폰트 처리 → 산출물</text>
  <text x="480" y="456" text-anchor="middle" fill="#7a8399" font-size="9" font-family="Consolas, monospace">ingest · restyle · build · embed</text>

  <rect x="40" y="508" width="880" height="64" rx="8" fill="rgba(45,49,66,0.02)" stroke="rgba(45,49,66,0.12)"/>
  <rect x="72" y="520" width="248" height="40" rx="6" fill="#fff" stroke="#4f5d75"/>
  <text x="196" y="544" text-anchor="middle" fill="#2d3142" font-size="12" font-weight="600" font-family="Arial, 'Noto Sans KR', sans-serif">구조·렌더·시각 품질 검사</text>
  <rect x="356" y="520" width="248" height="40" rx="6" fill="#fff" stroke="#4f5d75"/>
  <text x="480" y="544" text-anchor="middle" fill="#2d3142" font-size="12" font-weight="600" font-family="Arial, 'Noto Sans KR', sans-serif">PPTX · PDF · PNG</text>
  <rect x="640" y="520" width="248" height="40" rx="6" fill="rgba(79,93,117,0.08)" stroke="#4f5d75"/>
  <text x="764" y="544" text-anchor="middle" fill="#2d3142" font-size="12" font-weight="600" font-family="Arial, 'Noto Sans KR', sans-serif">GitHub Actions · 배포</text>
  <line x1="40" y1="584" x2="920" y2="584" stroke="rgba(45,49,66,0.12)"/>
  <text x="40" y="596" fill="#7a8399" font-size="8" font-family="Consolas, monospace">SOLID = CURRENT · DASHED = PLANNED · 2026-08-13</text>
</svg>
