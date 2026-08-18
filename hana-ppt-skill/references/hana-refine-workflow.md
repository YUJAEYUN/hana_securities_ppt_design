# hana-refine 실행 절차

`hana-refine`은 슬라이드 텍스트를 실제로 다시 쓰는 유일한 모드다. "새 사실을 만들지 않는다"는 보장은
코드가 문장을 생성하지 않고, 문장을 쓰는 주체(에이전트)와 그것을 기계적으로 검증하는 절차를 분리하는 방식으로 확보한다.
문체 규칙은 `assets/voice.json`을 정본으로, 판단 근거는 [voice-and-tone.md](voice-and-tone.md)를 따른다.

## 절차

1. **추출**: `python scripts/text_units.py deck.pptx --slide N -o units.json`
   - 슬라이드 N의 모든 텍스트 런을 문서 순서 그대로 `{index, text, shape_name, placeholder_type}` 배열로 뽑는다.
   - `placeholder_type`은 OOXML `<p:ph>`에서 읽은 값(`title`, `body` 등)이고, `shape_name`은 도형 이름이다.
     둘 다 **참고용 힌트**일 뿐이다. 등록된 레퍼런스 덱에서 면책 문구는 placeholder 없이 자유 텍스트 상자로
     그려지므로 `placeholder_type`만으로 면책 문구를 걸러낼 수 없다.
2. **재작성(에이전트)**: `units.json`과 `assets/voice.json`의 역할별 패턴(`roles`), 금지 표현
   (`lexicon.avoid_without_evidence`), 근거 규칙(`evidence_rules`)을 기준으로 각 런의 새 텍스트를 판단한다.
   - `placeholder_type == "title"`이면 제목 역할일 가능성이 높지만, 그 밖의 역할(메시지 헤드라인, 실적 불릿,
     실행 방안, 면책)은 `shape_name`과 실제 텍스트 내용을 함께 읽고 사람처럼 판단해야 한다.
   - 면책(disclaimer) 역할로 보이는 런은 edits에 포함하지 않는다. 원문을 완전한 문장으로 보존해야 한다.
   - 수치, 단위, 기간, 비교 기준, 고유명사는 새로 만들거나 지우지 않는다.
   - `{"슬라이드번호": {"런_index": "새 텍스트"}}` 형식으로 `edits.json`을 작성한다. `units.json`의 부가 필드
     (`shape_name`, `placeholder_type`)는 판단에만 쓰고 `edits.json`에는 넣지 않는다.
3. **검증 적용**: `python scripts/restyle_deck.py deck.pptx --brand assets/brand.json --voice assets/voice.json --mode hana-refine --edits edits.json -o out.pptx`
   - 내부적으로 슬라이드마다 `verify_evidence_preserved.verify()`를 먼저 실행한다.
   - 숫자가 하나라도 늘거나 줄면, 또는 비교 기준 표현(`전년동기 대비`, `전분기 대비`, `YoY`, `QoQ`)이 사라지면
     **어떤 슬라이드도 수정하지 않고** 전체를 오류로 중단한다.
   - 통과해야만 반영되고, 이어서 승인된 `brand.json`의 테마 색상·폰트도 함께 적용된다.

## 검증이 잡아내지 못하는 것

- 문장이 문법적으로 자연스러운지, 문체 규칙(명사형 종결, 인과 관계 명시 등)을 실제로 따랐는지는 기계적으로
  검사하지 않는다. 재작성한 에이전트가 `voice-and-tone.md`의 "검사 질문"으로 스스로 점검해야 한다.
- 숫자가 아닌 사실(예: 조직명, 상품명 교체)은 검증 대상이 아니다. 고유명사를 원문과 다르게 쓰지 않도록
  재작성 단계에서 직접 확인한다.
- 이 절차는 슬라이드 텍스트에만 적용된다. 표·차트의 데이터 값 편집은 별도 기능이며 아직 없다.
- 레이아웃·요소 배치 변경은 다루지 않는다. 텍스트 런의 내용만 교체한다.
