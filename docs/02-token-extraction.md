# 2. 브랜드 토큰 추출

## 목적

5개 이상의 기존 PPTX를 분석해 관찰 사실과 확정 토큰을 분리하고, `references/design-tokens.md`와 `assets/brand.json`을 생성한다. 이후 모든 단계가 이 결과에 의존하므로 가장 우선해서 실제 동작하게 만든다.

## 입력과 출력

입력:

- 하나 이상의 PPTX 경로 또는 PPTX가 담긴 디렉터리
- 출력 디렉터리
- 선택적으로 공식성/우선순위를 나타내는 메타데이터

출력:

- 원시 분석 JSON 또는 CSV
- 사람이 읽는 `references/design-tokens.md`
- 기계가 읽는 `assets/brand.json`
- `unclassified` 및 저신뢰 결과 목록

## 구현 순서

1. 프레젠테이션 크기, 슬라이드 수, 마스터와 레이아웃 정보를 읽는다.
2. 배경, 도형 채우기, 선, 텍스트의 색상을 추출한다.
3. 직접 RGB, 테마색, 밝기 변형, 상속 값을 가능한 범위에서 실제 RGB로 정규화한다.
4. 폰트명, 크기, 굵기, 정렬과 텍스트 박스 위치를 추출한다.
5. 도형과 이미지의 좌표·크기를 슬라이드 크기 대비 비율과 원 단위 모두로 기록한다.
6. 반복 이미지의 해시와 위치 빈도를 이용해 로고 후보를 찾는다. 파일명에 `logo`가 있는 경우 보조 신호로 사용한다.
7. 작은 숫자 텍스트와 반복 위치를 이용해 페이지 번호 후보를 찾는다.
8. 규칙 기반으로 표지, 섹션 구분, 목차, 텍스트+불릿, 차트, 표, 비교, 클로징을 분류한다.
9. 빈도, 위치 안정성, 샘플 우선순위를 종합해 토큰 후보와 신뢰도를 계산한다.
10. 자동 확정할 값과 사람 검토가 필요한 값을 구분해 두 출력 파일을 만든다.

## 분류 원칙

- 규칙의 근거와 점수를 결과에 남긴다.
- 여러 유형이 비슷한 점수면 억지로 선택하지 않고 `unclassified`로 둔다.
- 표지와 클로징처럼 텍스트가 적은 유형은 슬라이드 순서만으로 단정하지 않는다.
- 차트와 표는 실제 도형 타입과 관계를 우선 사용한다.

## `brand.json` 최소 스키마

```json
{
  "schema_version": 1,
  "slide": {"width": null, "height": null},
  "colors": {"primary": null, "secondary": [], "neutral": [], "allowed_tolerance": 0},
  "fonts": {"heading": null, "body": null, "fallbacks": []},
  "typography": {"title_pt": null, "body_pt": null, "caption_pt": null},
  "margins": {"left": null, "right": null, "top": null, "bottom": null},
  "logo": {"path": null, "allowed_regions": [], "size_range": {}},
  "page_number": {"enabled": true, "region": null},
  "effects": {"animations": false, "shadows": false, "gradients": false}
}
```

실제 값은 샘플 분석 후 확정한다. 분석 전 임의의 하나증권 색상이나 폰트를 넣지 않는다.

## 테스트

- 직접 RGB와 테마색이 같은 정규화 값으로 모이는지 확인한다.
- 반복 배치된 동일 이미지가 로고 후보로 잡히는지 확인한다.
- 모호한 슬라이드가 `unclassified`가 되는지 확인한다.
- 동일 입력에 대해 결정적인 JSON이 생성되는지 확인한다.
- 잘못된 파일, 암호화된 파일, 빈 프레젠테이션을 명확한 오류로 처리한다.

## 완료 조건

- 샘플 PPTX 5개 이상을 한 번의 명령으로 분석한다.
- `design-tokens.md`와 `brand.json`이 함께 생성된다.
- 주요 값마다 빈도·출처·신뢰도 또는 검토 상태가 추적된다.
- 사람이 검토한 최종 `brand.json`을 이후 단계의 정본으로 승인한다.

