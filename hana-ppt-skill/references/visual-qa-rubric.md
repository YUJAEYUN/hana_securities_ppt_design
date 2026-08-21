# 시각 QA 루브릭

`scripts/visual_check.py`가 만든 검수 패킷(JSON)을 받아 렌더 이미지를 실제로 "보고" 판정하는 사람/에이전트를 위한 절차다. 목적은 "예쁜가"라는 열린 미적 판단이 아니라, 이미 승인된 `layouts.json`/`brand.json`의 사실과 대조하는 것이다 — 이 저장소가 문체·수치에 적용해온 "추측하지 않는다" 원칙을 시각 QA에도 그대로 적용한다.

## 왜 별도 세션이 봐야 하는가

`hana-refine`이 생성(에이전트가 문장을 다시 씀)과 검증(`verify_evidence_preserved.py`가 기계적으로 대조)을 분리하듯, 시각 QA도 **만든 세션과 검수하는 세션을 분리**하는 걸 권장한다. 방금 그 슬라이드를 만든 세션에게 "이거 괜찮아?"라고 물으면 자기가 내린 선택을 정당화하기 쉽다. 가능하면:

- 새 에이전트 세션(또는 최소한 "너는 방금 이걸 만들지 않았다, 검수자다"라는 프레임)에 검수 패킷 + 렌더 이미지만 준다.
- 왜 이렇게 만들었는지에 대한 설명 없이, 체크리스트와 이미지만 보고 판단하게 한다.

## 입력

1. `render_slides.py`가 만든 슬라이드별 이미지(JPEG/PNG).
2. `visual_check.py`가 만든 검수 패킷(JSON) — 슬라이드별 역할, 체크리스트(`layouts.json`의 `elements`를 그대로 문장화한 것), 신뢰도(`confidence`), 그리고 가능하면 배경색 기계 대조 결과(`mechanical_background_check`).

## 절차

슬라이드마다:

1. **`mechanical_background_check`가 있으면 먼저 확인한다.** `verdict: "mismatch"`면 이미 기계적으로 틀렸다고 확정된 것이니 배경색 판단에 시간을 쓰지 않는다. `"match"`거나 필드가 없으면(Pillow 미설치 등) 3번으로.
2. **`confidence`를 본다.** `hana-securities-evidenced`면 체크리스트 불일치를 실제 결함으로 취급한다. `hfg-group-estimate-only`면 이 패턴 자체가 아직 하나증권 실제 자료로 확인되지 않은 추정이므로, 불일치를 "결함"이 아니라 "이 패턴이 맞는지 재검토 필요"로 다르게 기록한다(고쳐야 할 코드 버그가 아니라 근거 부족 문제). `undefined-role`이면 애초에 판단할 근거가 없으니 그렇게 보고한다.
3. **체크리스트 항목을 하나씩 pass/fail/uncertain으로 판정한다.** 항목마다 왜 그렇게 판단했는지 한 줄로 남긴다. 체크리스트에 없는 것(색이 대충 맞는 것 같다, 느낌이 좋다 등)은 판정에 넣지 않는다.
4. **체크리스트에 없는 문제(잘림, 겹침, 정렬 어긋남, 여백 부족 등)는 `unlisted_issues`로 따로 적는다.** 이때만 `references/general-ppt-design-principles.md`(CRAP 원칙 — 대비/반복/정렬/근접, 여백 권장치 등)를 참고 기준으로 쓴다. 브랜드 고유 체크리스트 판정과 절대 섞지 않는다.
5. **슬라이드 판정을 합산한다.** 고신뢰도(`hana-securities-evidenced`) 체크리스트 항목이 하나라도 `fail`이면 그 슬라이드는 `blocked`. `unlisted_issues` 중 가독성을 해치는 심각한 것(텍스트가 잘려서 안 보임, 색 대비가 낮아 읽을 수 없음)도 `blocked`. 그 외 사소한 unlisted issue는 `blocked`로 만들지 않고 `minor` 목록에 남긴다.

## 출력 형식 (권장)

```json
{
  "slide": 1,
  "role": "cover",
  "verdict": "blocked | pass | needs-source-review",
  "checklist_findings": [
    {"item": "element=full-bleed-background, color=primary_green(009070)...", "verdict": "pass", "note": "배경 전체가 초록색으로 채워짐"}
  ],
  "unlisted_issues": [
    {"severity": "minor", "note": "부제 텍스트와 상단 여백이 좁아 보임"}
  ]
}
```

## 주의

- 이건 픽셀 단위 완전 일치 검사가 아니다(`ARCHITECTURE.md`도 "전체 픽셀 일치가 아니라 화면비·고정 요소·경계·정렬·밀도·색상 분포 비교"라고 명시). `mechanical_background_check`의 색 거리 임계값(기본 12, RGB 유클리드 거리)도 렌더러의 JPEG 압축 오차를 감안한 느슨한 기준이다.
- 이 문서와 `visual_check.py`는 아직 실제 렌더 이미지로 종단간 검증되지 않았다 — 이 개발 환경은 `soffice` 헤드리스 렌더가 막혀 있어(`ARCHITECTURE.md` 참고) `render_slides.py`를 직접 돌려 확인하지 못했다. `visual_check.py`의 패킷 생성 로직 자체는 유닛 테스트로 검증했지만, 실제 렌더 결과물을 사람이 처음 봤을 때 이 루브릭이 실제로 잘 작동하는지는 렌더가 가능한 환경에서 한 번 실제로 돌려봐야 한다.
