from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import yaml
from opensearchpy import OpenSearch


@dataclass
class OpenSearchConfig:
    hosts: list[dict[str, Any]]
    use_ssl: bool = False
    verify_certs: bool = False
    timeout: int = 30
    username: str | None = None
    password: str | None = None


class OpenSearchSDK:
    def __init__(self, config_path: str = "config.yaml") -> None:
        self._raw = self._load_config(config_path)
        opensearch = self._raw.get("opensearch", {})
        auth = opensearch.get("http_auth", {})
        self.config = OpenSearchConfig(
            hosts=opensearch["hosts"],
            use_ssl=opensearch.get("use_ssl", False),
            verify_certs=opensearch.get("verify_certs", False),
            timeout=opensearch.get("timeout", 30),
            username=auth.get("username"),
            password=auth.get("password"),
        )
        self.index_name = self._raw.get("index", {}).get("name", "sample-index")
        self.client = self._create_client()

    @staticmethod
    def _load_config(config_path: str) -> dict[str, Any]:
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _create_client(self) -> OpenSearch:
        http_auth = None
        if self.config.username and self.config.password:
            http_auth = (self.config.username, self.config.password)

        return OpenSearch(
            hosts=self.config.hosts,
            use_ssl=self.config.use_ssl,
            verify_certs=self.config.verify_certs,
            timeout=self.config.timeout,
            http_auth=http_auth,
        )

    def create_index(self, mapping: dict[str, Any] | None = None) -> dict[str, Any]:
        if self.client.indices.exists(index=self.index_name):
            return {"acknowledged": True, "message": "index already exists"}

        body = mapping or {
            "mappings": {
                "properties": {
                    "name": {"type": "text"},
                    "price": {"type": "float"},
                    "category": {"type": "keyword"},
                }
            }
        }
        return self.client.indices.create(index=self.index_name, body=body)

    def create_document(self, doc_id: str, document: dict[str, Any]) -> dict[str, Any]:
        return self.client.index(index=self.index_name, id=doc_id, body=document, refresh=True)

    def read_document(self, doc_id: str) -> dict[str, Any]:
        return self.client.get(index=self.index_name, id=doc_id)

    def update_document(self, doc_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        return self.client.update(
            index=self.index_name,
            id=doc_id,
            body={"doc": fields},
            refresh=True,
        )

    def delete_document(self, doc_id: str) -> dict[str, Any]:
        return self.client.delete(index=self.index_name, id=doc_id, refresh=True)

    def delete_index(self) -> dict[str, Any]:
        if not self.client.indices.exists(index=self.index_name):
            return {"acknowledged": True, "message": "index not found"}
        return self.client.indices.delete(index=self.index_name)
