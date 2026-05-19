from opensearch_adk import OpenSearchCrudADK


def main() -> None:
    adk = OpenSearchCrudADK("config.yaml")

    print("1) CREATE INDEX")
    print(adk.create_index())

    print("\n2) CREATE DOCUMENT")
    print(
        adk.create_document(
            doc_id="1",
            document={"name": "keyboard", "price": 79.9, "category": "electronics"},
        )
    )

    print("\n3) READ DOCUMENT")
    print(adk.read_document("1"))

    print("\n4) UPDATE DOCUMENT")
    print(adk.update_document("1", {"price": 69.9}))

    print("\n5) DELETE DOCUMENT")
    print(adk.delete_document("1"))

    print("\n(OPTIONAL) DELETE INDEX")
    print(adk.delete_index())


if __name__ == "__main__":
    main()
