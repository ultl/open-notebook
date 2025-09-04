"""Embedding service layer using API."""

from loguru import logger

from api.client import api_client


class EmbeddingService:
  """Service layer for embedding operations using API."""

  def __init__(self) -> None:
    logger.info('Using API for embedding operations')

  def embed_content(self, item_id: str, item_type: str) -> dict[str, str]:
    """Embed content for vector search."""
    return api_client.embed_content(item_id=item_id, item_type=item_type)


# Global service instance
embedding_service = EmbeddingService()
