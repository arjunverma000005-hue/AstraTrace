"""Business logic and domain service modules."""

def __getattr__(name: str):
    if name == "IngestionService":
        from apps.backend.app.services.ingestion import IngestionService
        return IngestionService
    if name == "CatalogService":
        from apps.backend.app.services.catalog import CatalogService
        return CatalogService
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = ["IngestionService", "CatalogService"]
