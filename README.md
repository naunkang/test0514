# Python SDK Examples (Fabrix CS Service + OpenSearch)

이 저장소는 2개의 SDK 예시를 제공합니다.

- `fabrix_cs_sdk.py`: Fabrix CS Service 형태의 REST API용 SDK
- `opensearch_sdk.py`: OpenSearch CRUD SDK

## 파일 구성

- `config.yaml`: 두 SDK의 공통 설정
- `example_fabrix_cs.py`: Fabrix CS SDK 사용 예제
- `example_crud.py`: OpenSearch SDK 사용 예제
- `requirements.txt`: 의존성

## 설치

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Fabrix CS SDK 사용

`config.yaml`에서 아래 항목을 환경에 맞게 바꿔주세요.

- `fabrix_cs_service.base_url`
- `fabrix_cs_service.api_key`

실행:

```bash
python example_fabrix_cs.py
```

제공 메서드:

- `health()`
- `create_conversation(user_id, metadata=None)`
- `get_conversation(conversation_id)`
- `send_message(conversation_id, message, role="user")`
- `delete_conversation(conversation_id)`

## OpenSearch SDK 사용

```bash
python example_crud.py
```
