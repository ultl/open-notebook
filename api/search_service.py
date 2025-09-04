"""Search service layer using API."""

from typing import Any

from loguru import logger

from api.client import api_client


class SearchService:
  """Service layer for search operations using API."""

  def __init__(self) -> None:
    logger.info('Using API for search operations')

  def search(
    self,
    query: str,
    search_type: str = 'text',
    limit: int = 100,
    search_sources: bool = True,
    search_notes: bool = True,
    minimum_score: float = 0.2,
  ) -> list[dict[str, Any]]:
    """Search the knowledge base."""
    response = api_client.search(
      query=query,
      search_type=search_type,
      limit=limit,
      search_sources=search_sources,
      search_notes=search_notes,
      minimum_score=minimum_score,
    )
    return response.get('results', [])

  def ask_knowledge_base(
    self,
    question: str,
    strategy_model: str,
    answer_model: str,
    final_answer_model: str,
  ) -> dict[str, str]:
    """Ask the knowledge base a question."""
    return api_client.ask_simple(
      question=question,
      strategy_model=strategy_model,
      answer_model=answer_model,
      final_answer_model=final_answer_model,
    )


# Global service instance
search_service = SearchService()
