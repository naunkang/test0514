"""Graph parsing pipeline API.

This module implements a document-level graph parsing workflow using
Fabrix Search API and OpenSearch-backed GraphRDB.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

import requests
import yaml


@dataclass
class ChunkHit:
    chunk_id: str
    document_id: str
    score: Optional[float] = None


@dataclass
class GraphDocument:
    doc_id: str
    doc_summary: str
    title: str
    target_doc: List[str]


class GraphParsingAPI:
    """End-to-end graph parsing orchestrator.

    Pipeline order:
    1) Retrieve initial top-k chunks from Fabrix Search API.
    2) Filter GraphRDB by source doc IDs.
    3) Expand n-hop on document-level graph.
    4) Build doc-chunk graph via per-document top-c retrieval.
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
        self.fabrix = config["fabrix_search"]
        self.graph_rdb = config["graph_rdb"]
        self.hyper = config["hyperparameters"]

    @classmethod
    def from_yaml(cls, yaml_path: str) -> "GraphParsingAPI":
        with open(yaml_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return cls(config)

    def run(self, query: str, topk: Optional[int] = None, catalog_id: Optional[str] = None) -> Dict[str, Any]:
        """Run the full pipeline and return an aggregated graph payload."""
        topk = topk if topk is not None else self.hyper["topk_initial"]
        catalog_id = catalog_id if catalog_id is not None else self.hyper["default_catalog_id"]

        initial_hits = self.retrieve_initial_topk_chunks(query=query, topk=topk, catalog_id=catalog_id)
        source_doc_ids = sorted({h.document_id for h in initial_hits})

        filtered_docs = self.filter_graph_rdb_by_doc_ids(source_doc_ids)
        expanded_doc_ids, doc_edges = self.expand_n_hop(filtered_docs, source_doc_ids, self.hyper["n_hop"])

        doc_chunk_edges, chunk_nodes = self.build_document_chunk_graph(
            query=query,
            expanded_doc_ids=expanded_doc_ids,
            catalog_id=catalog_id,
            topc=self.hyper["topc_per_document"],
        )

        return {
            "query": query,
            "catalog_id": catalog_id,
            "source_doc_ids": source_doc_ids,
            "expanded_doc_ids": sorted(expanded_doc_ids),
            "document_edges": doc_edges,
            "doc_chunk_edges": doc_chunk_edges,
            "chunk_nodes": chunk_nodes,
        }

    # 1) Initial retrieval -------------------------------------------------
    def retrieve_initial_topk_chunks(self, query: str, topk: int, catalog_id: str) -> List[ChunkHit]:
        """Retrieve top-k chunks from vector DB via Fabrix Search API."""
        url = f"{self.fabrix['base_url'].rstrip('/')}/{self.fabrix['search_path'].lstrip('/')}"
        payload = {
            "query": query,
            "topk": topk,
            "catalogID": catalog_id,
            "index": self.fabrix["chunk_index"],
        }
        headers = self._build_headers(self.fabrix)
        response = requests.post(url, json=payload, headers=headers, timeout=self.fabrix.get("timeout_sec", 30))
        response.raise_for_status()
        data = response.json()

        hits: List[ChunkHit] = []
        for item in data.get("hits", []):
            hits.append(
                ChunkHit(
                    chunk_id=str(item.get("chunk_id")),
                    document_id=str(item.get("document_id")),
                    score=item.get("score"),
                )
            )
        return hits

    # 2) GraphRDB filtering ------------------------------------------------
    def filter_graph_rdb_by_doc_ids(self, doc_ids: Sequence[str]) -> List[GraphDocument]:
        """Filter GraphRDB documents by doc_id terms query."""
        url = f"{self.graph_rdb['base_url'].rstrip('/')}/{self.graph_rdb['search_path'].lstrip('/')}"
        payload = {
            "index": self.graph_rdb["index"],
            "query": {
                "terms": {"doc_id": list(doc_ids)}
            },
            "_source": ["doc_id", "doc_summary", "title", "target_doc"],
            "size": max(len(doc_ids), 10),
        }
        headers = self._build_headers(self.graph_rdb)
        response = requests.post(url, json=payload, headers=headers, timeout=self.graph_rdb.get("timeout_sec", 30))
        response.raise_for_status()
        data = response.json()

        docs: List[GraphDocument] = []
        for hit in data.get("hits", {}).get("hits", []):
            src = hit.get("_source", {})
            docs.append(
                GraphDocument(
                    doc_id=str(src.get("doc_id")),
                    doc_summary=str(src.get("doc_summary", "")),
                    title=str(src.get("title", "")),
                    target_doc=[str(x) for x in src.get("target_doc", [])],
                )
            )
        return docs

    # 3) N-hop expansion ---------------------------------------------------
    def expand_n_hop(
        self,
        filtered_docs: Sequence[GraphDocument],
        seed_doc_ids: Sequence[str],
        n_hop: int,
    ) -> Tuple[set[str], List[Tuple[str, str]]]:
        """Expand seed nodes by n-hop at document level.

        NOTE: 현재 구현은 2번 결과(filtered_docs) 내에서만 확장합니다.
        필요 시, hop마다 target_doc에 대해 GraphRDB 재조회하도록 확장 함수 개선 필요.
        """
        adjacency: Dict[str, List[str]] = {d.doc_id: d.target_doc for d in filtered_docs}
        visited = set(seed_doc_ids)
        frontier = set(seed_doc_ids)
        edges: List[Tuple[str, str]] = []

        for _ in range(n_hop):
            next_frontier: set[str] = set()
            for src in frontier:
                for tgt in adjacency.get(src, []):
                    edges.append((src, tgt))
                    if tgt not in visited:
                        visited.add(tgt)
                        next_frontier.add(tgt)
            frontier = next_frontier
            if not frontier:
                break

        return visited, edges

    # 4) Document-chunk graph ---------------------------------------------
    def build_document_chunk_graph(
        self,
        query: str,
        expanded_doc_ids: Sequence[str],
        catalog_id: str,
        topc: int,
    ) -> Tuple[List[Tuple[str, str]], List[Dict[str, Any]]]:
        """Retrieve top-c chunks per document and connect doc->chunk edges."""
        edges: List[Tuple[str, str]] = []
        chunk_nodes: List[Dict[str, Any]] = []

        for doc_id in expanded_doc_ids:
            hits = self.retrieve_chunks_for_document(query=query, doc_id=doc_id, topc=topc, catalog_id=catalog_id)
            for hit in hits:
                edges.append((doc_id, hit.chunk_id))
                chunk_nodes.append({"chunk_id": hit.chunk_id, "document_id": hit.document_id, "score": hit.score})

        return edges, chunk_nodes

    def retrieve_chunks_for_document(self, query: str, doc_id: str, topc: int, catalog_id: str) -> List[ChunkHit]:
        """Retrieve top-c chunks for a specific document.

        TODO(세부 스펙 보강 필요):
        - Fabrix Search API에서 document_id filter 문법 확정 필요.
        - 아래 payload의 "filters" 구조는 예시이며, 실제 API 스펙에 맞게 수정해야 함.
        - 예시:
          filters:
            - field: "document_id"
              op: "eq"
              value: "DOC-123"
        """
        url = f"{self.fabrix['base_url'].rstrip('/')}/{self.fabrix['search_path'].lstrip('/')}"
        payload = {
            "query": query,
            "topk": topc,
            "catalogID": catalog_id,
            "index": self.fabrix["chunk_index"],
            "filters": [
                {"field": "document_id", "op": "eq", "value": doc_id}
            ],
        }
        headers = self._build_headers(self.fabrix)
        response = requests.post(url, json=payload, headers=headers, timeout=self.fabrix.get("timeout_sec", 30))
        response.raise_for_status()
        data = response.json()

        return [
            ChunkHit(
                chunk_id=str(item.get("chunk_id")),
                document_id=str(item.get("document_id", doc_id)),
                score=item.get("score"),
            )
            for item in data.get("hits", [])
        ]

    @staticmethod
    def _build_headers(cfg: Dict[str, Any]) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        api_key = cfg.get("api_key")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers


def main() -> None:
    api = GraphParsingAPI.from_yaml("config.yaml")
    result = api.run(query="example query")
    print(result)


if __name__ == "__main__":
    main()
