# 하나 공식 CI 규격 (사용자 제공)

이 문서는 사용자가 대화에서 직접 제공한 하나 공식 CI(컬러·서체) 수치를 사람이 읽기 쉽게 정리한다. 실행 정본은 `assets/ci-colors.json`과 `assets/ci-typography.json`이며, 같은 수치를 이 문서에 반복하지 않고 표로만 요약한다.

## 이 규격과 `brand.json`의 관계

- `assets/brand.json`은 로컬 하나금융그룹 IR 2건을 관찰해 사용자가 운영 기준으로 승인한 프로필이며 `official_ci_specification: false`로 명시돼 있다. 이 문서·JSON과는 출처가 다르다.
- `assets/ci-colors.json`, `assets/ci-typography.json`은 사용자가 공식 CI 수치를 직접 입력해 제공한 것으로 `official_ci_specification: true`다.
- 두 정본을 아직 통합하지 않았다. `build_deck.py`/`restyle_deck.py`는 여전히 `brand.json`만 실행에 사용한다. 공식 CI 컬러·서체를 실제 실행에 반영하려면 심볼마크(로고) 원본과 보호영역 등 나머지 공식 CI 요소를 마저 확보한 뒤 `brand.json`을 갱신하고 `tests/test_repository.py`의 관련 단언(예: `official_ci_specification`이 항상 거짓이어야 한다는 검증)도 함께 손봐야 한다.

## 컬러 시스템

정본: `assets/ci-colors.json`

| 구분 | 색상 | Pantone | CMYK | RGB | HEX |
|---|---|---|---|---|---|
| 메인 | Hana Green | 3288 C | C100 M0 Y65 K15 | R0 G145 B120 | #009178 |
| 메인 | Hana Ren(Red 추정) | 3546 C | C10 M100 Y100 K0 | R220 G35 B30 | #DC231E |
| 서브 | Hana Dark Green | 3305 C | C95 M15 Y60 K60 | R0 G78 B66 | #004E42 |
| 서브 | Hana Pale Green | 573 C | C15 M0 Y10 K0 | R215 G237 B230 | #DBEDE7 |
| 포인트 | Hana Light Green | 345 C | C35 M0 Y35 K0 | R167 G216 B183 | #A7D8B8 |
| 포인트 | Hana Point Green | 381 C | C25 M0 Y100 K0 | R206 G220 B88 | #CEDC00 |
| 스페셜 | Hana Gold | 871 C | 미제공 | 미제공 | 미제공 |
| 스페셜 | Hana Light Gold | 8003 C | 미제공 | 미제공 | 미제공 |
| 스페셜 | Hana Silver | 877 C | 미제공 | 미제공 | 미제공 |

### 값 검증 메모

값을 그대로 등록하기 전에 HEX → RGB 환산으로 자체 대조했다. 결과는 `assets/ci-colors.json`의 각 색상 `consistency_check` 필드에 기록했다.

- 대부분(Hana Green, Hana Ren, Hana Dark Green)은 HEX와 RGB가 정확히 일치한다.
- Hana Pale Green, Hana Light Green은 반올림 수준의 사소한 오차(1~4 단위)가 있다.
- Hana Point Green은 HEX #CEDC00을 환산하면 B=0인데 RGB는 B=88로 계산상 어긋난다. 2026-08-20에 사용자가 RGB(B=88)는 원본 CI 문서에 그대로 적힌 값임을 확인해줬다 — 오기가 아니라 원본 표기 자체가 그렇다는 뜻이므로 두 값 모두 그대로 유지한다.
- 스페셜 컬러(금·은)는 팬톤 코드만 제공됐다. 메탈릭 팬톤은 표준 RGB/HEX로 정확히 환산되지 않으므로 값을 만들어내지 않았다. 사용자 요청으로 추가 확보는 보류.

### 실제 배포 자료 대조 검증

사용자가 처음 안내한 외부 URL(`grant-documents.thevc.kr`)은 이 세션의 아웃바운드 egress 정책이 차단해 다운로드하지 못했다(정책 차단이므로 우회하지 않음). 이를 사용자에게 알리자 같은 PDF를 대화에 직접 첨부해 확보했다. `assets/reference-decks/hana-securities/2025_Hana_Securities_Profile.pdf`(source_id: `hana-securities-2025-profile`, "하나증권 회사소개서")로 등록하고 600dpi로 렌더링해 픽셀 단위로 대조했다.

- 표지 배경색을 크롭해 최빈 픽셀을 뽑으면 정확히 `RGB(0, 145, 120)` = `#009178`로, 사용자가 제공한 Hana Green 값과 완전히 일치한다.
- 표지 하단의 로고 심볼마크에서 초록·빨강을 각각 추출하면 `RGB(0, 145, 120)`과 `RGB(220, 35, 30)`으로, Hana Green·Hana Ren(Red) 정본과 정확히 일치한다.
- 경영이념 슬라이드(8p)의 헥사곤 장식에서 노란빛 초록 후광을 확인했는데, 이 부분은 여러 겹의 반투명 도형이 섞인 그라데이션이라 단일 원색으로 역산할 수 없어 이 방법만으로는 Hana Point Green을 검증하지 못했다. 다만 사용자가 RGB(B=88) 값이 원본 문서 그대로임을 직접 확인해줘서 별도로 해소됐다(위 값 검증 메모 참고).
- Special 컬러(Gold/Light Gold/Silver)가 쓰인 사례는 이 문서에서 찾지 못했다.

이 문서는 색상·로고 검증에는 썼지만 레이아웃·문체 수준의 스타일 학습 근거로는 아직 채택하지 않았다(`sources.json`의 `approval_scope: official-ci-color-and-symbol-mark-corroboration` 참고). 그 수준의 채택은 별도 검토가 필요하다.

## 서체 사용 규정

정본: `assets/ci-typography.json`

| 서체 | 용도 | 권장 크기 |
|---|---|---|
| 하나2.0 Light | 하나체 중 가장 얇은 형태. 본문에서 중요 정보를 보완하는 요소로 사용 | 6~8pt |
| 하나2.0 Regular | 기본 서체. 본문용/제목용 모두 사용 | 9~16pt |
| 하나2.0 Medium | 본문에서 강조할 문구나 명확한 정보 전달이 필요한 경우 사용 | 미제공 |
| 하나2.0 Condensed Medium | 다른 서체보다 폭이 좁아 제한된 공간에 많은 정보 전달이 필요한 경우 사용 | 미제공 |
| 하나2.0 Bold | 제목에 사용, 장문 사용 지양 | 17~44pt |
| 하나2.0 Heavy | 하나체 중 가장 두꺼운 서체, 제목용으로 개발, 장문 사용 지양 | 45pt(단일 값 제공, 상한 미제공) |

번들 폰트 파일과의 매핑은 `assets/fonts/manifest.json`을 따른다(`light`/`regular`/`medium`/`cm`/`bold`/`heavy` role이 이 표의 6종과 그대로 대응한다).

## 심볼마크(로고)

정본: `assets/ci-colors.json`의 `logo` 섹션

- `assets/logo/HanaSecurities_symbol-mark.png`(심볼마크만, 투명 배경)와 `assets/logo/HanaSecurities_logo-lockup.png`(심볼마크+"하나증권" 워드마크, 투명 배경)를 `hana-securities-2025-profile.pdf` 표지에서 추출해 등록했다.
- 추출 방법: 표지를 600dpi로 래스터화한 뒤, 흰 배경 위에서 공식 CI 컬러(hana_green/hana_red) 정본 값을 기준으로 알파 채널을 역산했다. 두 색 모두 정본 HEX와 정확히 일치했다.
- 기존 `assets/logo/HanaSecurities_CI.ai`(벡터 원본)는 대체하지 않고 그대로 유지한다.
- 보호영역(safe area), 최소 크기, 어두운 배경 위 사용 규칙(흰색 반전 버전 등)은 여전히 미확정이다. 그래서 `brand.json.logo.placement_status`의 `blocked-until-ci-guide` 상태는 유지한다.

## 보류된 항목

2026-08-20 대화에서 사용자가 아래 항목은 추가로 캐묻지 말고 보류(pass)하도록 지시했다. 미해결 오류가 아니라 사용자 결정에 따른 보류이며, 값이 나중에 제공되면 그때 반영한다(`assets/ci-colors.json`의 `deferred_by_user` 참고).

1. Hana Ren의 정확한 명칭('Red' 여부) 확인
2. Special 컬러(Gold/Light Gold/Silver)의 CMYK/RGB/HEX 수치 확보
3. Medium/Condensed Medium의 권장 pt 범위, Heavy의 상한 확보
4. 심볼마크의 보호영역, 최소 크기, 배경 위 사용 규칙(흰색 반전 버전 등) 확보
5. 위 항목과 무관하게, `brand.json`으로의 병합은 이 보류 상태가 유지되는 한 진행하지 않는다. 필요해지면 그때 `official_ci_specification` 관련 테스트를 포함해 `tests/test_repository.py`를 함께 손본다.
