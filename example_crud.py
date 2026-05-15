from opensearch_sdk import OpenSearchSDK


def main() -> None:
    sdk = OpenSearchSDK("config.yaml")

    doc_id = "doc-001"
    sample_document = {
        "doc_id": doc_id,
        "title": "보안 정책 v2",
        "summary": "기존 정책을 대체하는 신규 보안 정책 문서",
        "app_period": ("2026-01-01", "2026-12-31"),
        "target_doc": {
            "doc-000": {
                "edge_type": "REPLACES",
                "reason": "v1 정책을 공식 폐기하고 본 문서로 대체",
            },
            "doc-777": {
                "edge_type": "RELATED_TO",
                "reason": "운영 가이드와 함께 참고 필요",
            },
        },
        "filter": {"service": "auth", "country": "KR", "tier": "prod"},
    }

    print("1) CREATE INDEX")
    print(sdk.create_index())

    print("\n2) CREATE DOCUMENT")
    print(sdk.create_document(doc_id=doc_id, document=sample_document))

    print("\n3) READ DOCUMENT")
    print(sdk.read_document(doc_id))

    print("\n4) UPDATE DOCUMENT")
    print(
        sdk.update_document(
            doc_id,
            {
                "summary": "시행일 기준 최신화된 보안 정책",
                "app_period": ("2026-02-01", "2026-12-31"),
                "target_doc": {
                    "doc-000": {
                        "edge_type": "REPLACES",
                        "reason": "적용 범위 확장으로 완전 대체",
                    }
                },
            },
        )
    )

    print("\n5) DELETE DOCUMENT")
    print(sdk.delete_document(doc_id))

    print("\n(OPTIONAL) DELETE INDEX")
    print(sdk.delete_index())


if __name__ == "__main__":
    main()
