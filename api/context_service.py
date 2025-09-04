"""Context service layer using API."""

from loguru import logger

from api.client import api_client


class ContextService:
    """Service layer for context operations using API."""

    def __init__(self) -> None:
        logger.info("Using API for context operations")

    def get_notebook_context(
        self, notebook_id: str, context_config: dict | None = None
    ) -> dict:
        """Get context for a notebook."""
        return api_client.get_notebook_context(
            notebook_id=notebook_id, context_config=context_config
        )


# Global service instance
context_service = ContextService()
