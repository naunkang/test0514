# OpenSearch 문서 메타데이터 CRUD SDK

요청하신 스키마(`doc_id`, `title`, `summary`, `app_period`, `target_doc`, `filter`)를 CRUD 할 수 있는 Python SDK입니다.

## 스키마

- `doc_id: str`
- `title: str`
- `summary: str`
- `app_period: tuple[str, str]` -> `(YYYY-MM-DD, YYYY-MM-DD)`
- `target_doc: dict[str, dict[str, str]]` -> `{"연관_doc_id": {"edge_type": "REPLACES|RELATED_TO", "reason": "..."}}`
- `filter: dict[str, Any]`

## 파일 구성

- `config.yaml`: OpenSearch 접속 정보 및 인덱스명
- `opensearch_sdk.py`: 스키마 검증 + OpenSearch CRUD SDK
- `example_crud.py`: SDK 사용 예제
- `requirements.txt`: 의존성

## 설치

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 실행

```bash
python example_crud.py
```

## 제공 메서드

- `create_index(mapping=None)`
  - 기본 매핑에 위 스키마 반영
- `create_document(doc_id, document)`
  - 필수 필드/형식 검증 후 저장
- `read_document(doc_id)`
- `update_document(doc_id, fields)`
  - `app_period`, `target_doc` 업데이트 시 형식 검증
- `delete_document(doc_id)`
- `delete_index()`

## 검증 규칙

- `app_period`는 길이 2의 날짜 튜플이어야 하며 `start <= end`
- `target_doc[*].edge_type`은 `REPLACES` 또는 `RELATED_TO`만 허용
- `target_doc[*].reason`은 비어있지 않은 문자열이어야 함
