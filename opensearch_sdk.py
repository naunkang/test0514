from opensearch_adk import OpenSearchConnectionConfig, OpenSearchCrudADK

# Backward-compatible aliases for older imports.
OpenSearchConfig = OpenSearchConnectionConfig
OpenSearchSDK = OpenSearchCrudADK

__all__ = ["OpenSearchConnectionConfig", "OpenSearchConfig", "OpenSearchCrudADK", "OpenSearchSDK"]
