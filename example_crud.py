from opensearch_sdk import OpenSearchSDK


def main() -> None:
    sdk = OpenSearchSDK("config.yaml")

    print("1) CREATE INDEX")
    print(sdk.create_index())

    print("\n2) CREATE DOCUMENT")
    print(
        sdk.create_document(
            doc_id="1",
            document={"name": "keyboard", "price": 79.9, "category": "electronics"},
        )
    )

    print("\n3) READ DOCUMENT")
    print(sdk.read_document("1"))

    print("\n4) UPDATE DOCUMENT")
    print(sdk.update_document("1", {"price": 69.9}))

    print("\n5) DELETE DOCUMENT")
    print(sdk.delete_document("1"))

    print("\n(OPTIONAL) DELETE INDEX")
    print(sdk.delete_index())


if __name__ == "__main__":
    main()
