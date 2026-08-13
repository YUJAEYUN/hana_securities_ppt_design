# 1. 스켈레톤과 입력 자료 준비

## 목적

구현 전에 파일 책임, 함수 경계, 입력 자료 위치를 고정한다. 이 단계에서는 완성 로직을 넣지 않고 실행 가능한 최소 스켈레톤과 테스트 자리를 만든다.

## 작업

1. `skill-creator`의 초기화 스크립트로 `hana-ppt-skill`을 생성한다.
2. `scripts`, `references`, `assets`를 포함하고 필요한 `agents/openai.yaml`을 생성한다.
3. 원문 요구에 따라 `AGENTS.md`, `requirements.txt`, `examples`, `tests`를 추가한다.
4. 각 Python 파일에 CLI 진입점, 함수 시그니처, 타입 힌트, docstring을 작성한다.
5. 샘플과 브랜드 자산을 저장할 위치를 정하되, 민감하거나 대용량인 원본은 Git 추적 여부를 확인한다.

## 권장 함수 경계

### `extract_tokens.py`

```python
def analyze_presentation(path): ...
def extract_colors(presentation): ...
def extract_typography(presentation): ...
def extract_geometry(presentation): ...
def detect_repeated_images(presentations): ...
def detect_page_numbers(presentation): ...
def classify_slide(slide, features): ...
def aggregate_tokens(analyses): ...
def write_brand_json(tokens, output_path): ...
def write_design_tokens(tokens, output_path): ...
def main(): ...
```

### `build_deck.py`

```python
def load_brand(path): ...
def build_cover(prs, content, brand_path): ...
def build_toc_slide(prs, content, brand_path): ...
def build_bullet_slide(prs, content, brand_path): ...
def build_comparison_slide(prs, content, brand_path): ...
def build_closing_slide(prs, content, brand_path): ...
def main(): ...
```

각 `build_*` 함수는 `brand_path`를 받아 호출 시점에 파일을 다시 읽는다.

### `quality_check.py`

```python
def check_colors(presentation, brand): ...
def check_fonts(presentation, brand): ...
def check_logo_geometry(presentation, brand): ...
def estimate_text_overflow(shape, brand): ...
def build_report(results): ...
def main(): ...
```

## 의존성 초안

- `python-pptx`: PPTX 읽기와 생성
- `Pillow`: 이미지 크기와 포맷 보조 분석
- `pytest`: 자동 테스트
- 필요 시 `lxml`: OOXML 수준의 제한적 검사

버전은 구현 시 현재 호환성을 확인해 고정한다. 각 스크립트는 누락된 필수 패키지를 이해하기 쉬운 메시지로 안내해야 한다.

## 입력 자료 체크리스트

- [ ] PPTX 5개 이상
- [ ] 각 PPTX의 최신성 또는 공식성 표시
- [ ] 최소 5개 목표 슬라이드 유형을 포함하는 사례
- [ ] CI 폰트 파일과 정확한 표시명
- [ ] 공식 로고 SVG/PNG
- [ ] 기본 화면비 확인(예: 16:9)
- [ ] 페이지 번호 포함 여부와 예외 슬라이드 확인

## 완료 조건

- 모든 필수 디렉터리와 파일이 존재한다.
- Python 파일이 문법 오류 없이 `--help`를 출력한다.
- 테스트 러너가 빈 테스트 구조에서 정상 시작한다.
- 누락된 입력 자료가 목록으로 명확히 보고된다.

