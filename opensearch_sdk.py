from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Literal

import yaml
from opensearchpy import OpenSearch

AllowedEdgeType = Literal["REPLACES", "RELATED_TO"]


@dataclass
class OpenSearchConfig:
    hosts: list[dict[str, Any]]
    use_ssl: bool = False
    verify_certs: bool = False
    timeout: int = 30
    username: str | None = None
    password: str | None = None


class OpenSearchSDK:
    """CRUD SDK for document metadata table.

    Schema:
      - doc_id: str
      - title: str
      - summary: str
      - app_period: tuple[str, str] (YYYY-MM-DD, YYYY-MM-DD)
      - target_doc: dict[str, {edge_type: str, reason: str}]
      - filter: dict[str, Any]
    """

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
        self.index_name = self._raw.get("index", {}).get("name", "document-metadata")
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

    @staticmethod
    def _validate_period(app_period: tuple[str, str]) -> None:
        if len(app_period) != 2:
            raise ValueError("app_period must contain exactly two dates: (start, end)")

        start_s, end_s = app_period
        start_d = date.fromisoformat(start_s)
        end_d = date.fromisoformat(end_s)
        if start_d > end_d:
            raise ValueError("app_period start date must be <= end date")

    @staticmethod
    def _validate_target_doc(target_doc: dict[str, dict[str, str]]) -> None:
        allowed_types: set[AllowedEdgeType] = {"REPLACES", "RELATED_TO"}

        for related_doc_id, edge in target_doc.items():
            if not related_doc_id:
                raise ValueError("target_doc key (related doc_id) cannot be empty")

            edge_type = edge.get("edge_type")
            reason = edge.get("reason")

            if edge_type not in allowed_types:
                raise ValueError(
                    f"target_doc[{related_doc_id}].edge_type must be one of {sorted(allowed_types)}"
                )
            if not isinstance(reason, str) or not reason.strip():
                raise ValueError(f"target_doc[{related_doc_id}].reason must be non-empty string")

    def create_index(self, mapping: dict[str, Any] | None = None) -> dict[str, Any]:
        if self.client.indices.exists(index=self.index_name):
            return {"acknowledged": True, "message": "index already exists"}

        body = mapping or {
            "mappings": {
                "properties": {
                    "doc_id": {"type": "keyword"},
                    "title": {"type": "text", "fields": {"raw": {"type": "keyword"}}},
                    "summary": {"type": "text"},
                    "app_period": {
                        "properties": {
                            "start": {"type": "date", "format": "strict_date"},
                            "end": {"type": "date", "format": "strict_date"},
                        }
                    },
                    "target_doc": {
                        "type": "nested",
                        "properties": {
                            "doc_id": {"type": "keyword"},
                            "edge_type": {"type": "keyword"},
                            "reason": {"type": "text"},
                        },
                    },
                    "filter": {"type": "object", "enabled": True},
                }
            }
        }
        return self.client.indices.create(index=self.index_name, body=body)

    def _normalize_document(self, document: dict[str, Any]) -> dict[str, Any]:
        required_fields = ["doc_id", "title", "summary", "app_period", "target_doc", "filter"]
        for field in required_fields:
            if field not in document:
                raise ValueError(f"Missing required field: {field}")

        if not isinstance(document["doc_id"], str) or not document["doc_id"].strip():
            raise ValueError("doc_id must be non-empty string")

        self._validate_period(tuple(document["app_period"]))
        self._validate_target_doc(document["target_doc"])

        start_date, end_date = tuple(document["app_period"])
        normalized_target_doc = [
            {
                "doc_id": related_doc_id,
                "edge_type": edge["edge_type"],
                "reason": edge["reason"],
            }
            for related_doc_id, edge in document["target_doc"].items()
        ]

        return {
            "doc_id": document["doc_id"],
            "title": document["title"],
            "summary": document["summary"],
            "app_period": {"start": start_date, "end": end_date},
            "target_doc": normalized_target_doc,
            "filter": document["filter"],
        }

    def create_document(self, doc_id: str, document: dict[str, Any]) -> dict[str, Any]:
        if document.get("doc_id") and document["doc_id"] != doc_id:
            raise ValueError("doc_id argument and document['doc_id'] must match")
        document = {**document, "doc_id": doc_id}
        normalized_doc = self._normalize_document(document)
        return self.client.index(index=self.index_name, id=doc_id, body=normalized_doc, refresh=True)

    def read_document(self, doc_id: str) -> dict[str, Any]:
        return self.client.get(index=self.index_name, id=doc_id)

    def update_document(self, doc_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        normalized_fields = dict(fields)

        if "app_period" in normalized_fields:
            self._validate_period(tuple(normalized_fields["app_period"]))
            start_date, end_date = tuple(normalized_fields.pop("app_period"))
            normalized_fields["app_period"] = {"start": start_date, "end": end_date}

        if "target_doc" in normalized_fields:
            self._validate_target_doc(normalized_fields["target_doc"])
            normalized_fields["target_doc"] = [
                {
                    "doc_id": related_doc_id,
                    "edge_type": edge["edge_type"],
                    "reason": edge["reason"],
                }
                for related_doc_id, edge in normalized_fields["target_doc"].items()
            ]

        return self.client.update(
            index=self.index_name,
            id=doc_id,
            body={"doc": normalized_fields},
            refresh=True,
        )

    def delete_document(self, doc_id: str) -> dict[str, Any]:
        return self.client.delete(index=self.index_name, id=doc_id, refresh=True)

    def delete_index(self) -> dict[str, Any]:
        if not self.client.indices.exists(index=self.index_name):
            return {"acknowledged": True, "message": "index not found"}
        return self.client.indices.delete(index=self.index_name)
