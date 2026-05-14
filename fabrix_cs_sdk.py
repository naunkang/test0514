from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

import yaml
import httpx


@dataclass
class FabrixCSConfig:
    base_url: str
    timeout: float = 30.0
    api_key: str | None = None
    headers: dict[str, str] | None = None


class FabrixCSSDK:
    """Simple SDK wrapper for Fabrix CS Service style REST APIs."""

    def __init__(self, config_path: str = "config.yaml") -> None:
        self._raw = self._load_config(config_path)
        cs_service = self._raw.get("fabrix_cs_service", {})
        if not cs_service.get("base_url"):
            raise ValueError("'fabrix_cs_service.base_url' is required in config")

        self.config = FabrixCSConfig(
            base_url=cs_service["base_url"],
            timeout=cs_service.get("timeout", 30.0),
            api_key=cs_service.get("api_key"),
            headers=cs_service.get("headers", {}),
        )

        self.client = httpx.Client(timeout=self.config.timeout, headers=self._build_headers())

    @staticmethod
    def _load_config(config_path: str) -> dict[str, Any]:
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _build_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        headers.update(self.config.headers or {})
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        url = urljoin(self.config.base_url.rstrip("/") + "/", path.lstrip("/"))
        res = self.client.request(method, url, **kwargs)
        res.raise_for_status()
        return res.json() if res.content else {"status_code": res.status_code}

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/health")

    def create_conversation(self, user_id: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._request("POST", "/v1/conversations", json={"user_id": user_id, "metadata": metadata or {}})

    def get_conversation(self, conversation_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/conversations/{conversation_id}")

    def send_message(self, conversation_id: str, message: str, role: str = "user") -> dict[str, Any]:
        payload = {"role": role, "content": message}
        return self._request("POST", f"/v1/conversations/{conversation_id}/messages", json=payload)

    def delete_conversation(self, conversation_id: str) -> dict[str, Any]:
        return self._request("DELETE", f"/v1/conversations/{conversation_id}")

    def close(self) -> None:
        self.client.close()
