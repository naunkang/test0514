from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from opensearchpy import OpenSearch


@dataclass(frozen=True)
class OpenSearchConnectionConfig:
    hosts: list[dict[str, Any]]
    use_ssl: bool = False
    verify_certs: bool = False
    timeout: int = 30
    username: str | None = None
    password: str | None = None


class OpenSearchCrudADK:
    """A small Application/Data Kit for OpenSearch CRUD examples."""

    def __init__(self, config_path: str | Path = "config.yaml") -> None:
        self.config_path = Path(config_path)
        self._raw_config = self._load_config(self.config_path)
        self.connection_config = self._parse_connection_config(self._raw_config)
        self.index_name = self._parse_index_name(self._raw_config)
        self.client = self._create_client()

    @staticmethod
    def _load_config(config_path: Path) -> dict[str, Any]:
        with config_path.open("r", encoding="utf-8") as config_file:
            config = yaml.safe_load(config_file) or {}

        if not isinstance(config, dict):
            raise ValueError("config.yaml must contain a YAML mapping at the document root.")
        return config

    @staticmethod
    def _parse_connection_config(config: dict[str, Any]) -> OpenSearchConnectionConfig:
        opensearch = config.get("opensearch", {})
        if not isinstance(opensearch, dict):
            raise ValueError("The 'opensearch' config section must be a mapping.")

        hosts = opensearch.get("hosts")
        if not isinstance(hosts, list) or not hosts:
            raise ValueError("The 'opensearch.hosts' config value must be a non-empty list.")

        auth = opensearch.get("http_auth", {}) or {}
        if not isinstance(auth, dict):
            raise ValueError("The 'opensearch.http_auth' config section must be a mapping.")

        return OpenSearchConnectionConfig(
            hosts=hosts,
            use_ssl=bool(opensearch.get("use_ssl", False)),
            verify_certs=bool(opensearch.get("verify_certs", False)),
            timeout=int(opensearch.get("timeout", 30)),
            username=auth.get("username"),
            password=auth.get("password"),
        )

    @staticmethod
    def _parse_index_name(config: dict[str, Any]) -> str:
        index_config = config.get("index", {}) or {}
        if not isinstance(index_config, dict):
            raise ValueError("The 'index' config section must be a mapping.")
        return str(index_config.get("name", "sample-products"))

    def _create_client(self) -> OpenSearch:
        http_auth = None
        if self.connection_config.username and self.connection_config.password:
            http_auth = (self.connection_config.username, self.connection_config.password)

        return OpenSearch(
            hosts=self.connection_config.hosts,
            use_ssl=self.connection_config.use_ssl,
            verify_certs=self.connection_config.verify_certs,
            timeout=self.connection_config.timeout,
            http_auth=http_auth,
        )

    def create_index(self, mapping: dict[str, Any] | None = None) -> dict[str, Any]:
        """Create the configured index if it does not already exist."""
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
        """Create or replace a document in the configured index."""
        return self.client.index(index=self.index_name, id=doc_id, body=document, refresh=True)

    def read_document(self, doc_id: str) -> dict[str, Any]:
        """Read a document by ID from the configured index."""
        return self.client.get(index=self.index_name, id=doc_id)

    def update_document(self, doc_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        """Partially update selected fields on a document."""
        return self.client.update(
            index=self.index_name,
            id=doc_id,
            body={"doc": fields},
            refresh=True,
        )

    def delete_document(self, doc_id: str) -> dict[str, Any]:
        """Delete a document by ID from the configured index."""
        return self.client.delete(index=self.index_name, id=doc_id, refresh=True)

    def delete_index(self) -> dict[str, Any]:
        """Delete the configured index if it exists."""
        if not self.client.indices.exists(index=self.index_name):
            return {"acknowledged": True, "message": "index not found"}
        return self.client.indices.delete(index=self.index_name)
