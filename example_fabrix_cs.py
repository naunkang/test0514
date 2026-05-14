from fabrix_cs_sdk import FabrixCSSDK


def main() -> None:
    sdk = FabrixCSSDK("config.yaml")

    print("1) HEALTH")
    print(sdk.health())

    print("\n2) CREATE CONVERSATION")
    conv = sdk.create_conversation(user_id="demo-user", metadata={"channel": "web"})
    print(conv)

    conversation_id = conv.get("id", "")
    if conversation_id:
        print("\n3) SEND MESSAGE")
        print(sdk.send_message(conversation_id, "안녕하세요"))

        print("\n4) GET CONVERSATION")
        print(sdk.get_conversation(conversation_id))

        print("\n5) DELETE CONVERSATION")
        print(sdk.delete_conversation(conversation_id))

    sdk.close()


if __name__ == "__main__":
    main()
