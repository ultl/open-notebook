from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from sqlalchemy import or_, select

from api.models import SearchRequest, SearchResponse
from open_notebook.database.models import Note, Source
from open_notebook.database.sql import get_session
from open_notebook.services.vector import vector_search as vector_search_service

if TYPE_CHECKING:
  from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.post('/search', response_model=SearchResponse)
async def search_knowledge_base(
  search_request: SearchRequest, session: AsyncSession = Depends(get_session)
) -> SearchResponse:
  """Search the knowledge base using text or vector search."""
  try:
    if search_request.type == 'vector':
      results = await vector_search_service(
        session=session,
        keyword=search_request.query,
        results=search_request.limit,
        source=search_request.search_sources,
        note=search_request.search_notes,
        minimum_score=search_request.minimum_score,
      )
    else:
      # Text search across Sources and Notes
      results: list[dict] = []
      q = f'%{search_request.query.lower()}%'
      if search_request.search_sources:
        src_stmt = (
          select(Source)
          .where(
            or_(
              Source.title.ilike(q),
              Source.full_text.ilike(q),
              Source.content.ilike(q),
            )
          )
          .limit(search_request.limit)
        )
        sources = list((await session.execute(src_stmt)).scalars().all())
        for src in sources:
          results.append({
            'type': 'source',
            'title': src.title or 'Untitled Source',
            'parent_id': str(src.id),
            'score': 1.0,
          })
      if search_request.search_notes:
        note_stmt = select(Note).where(or_(Note.title.ilike(q), Note.content.ilike(q))).limit(search_request.limit)
        notes = list((await session.execute(note_stmt)).scalars().all())
        for nt in notes:
          results.append({
            'type': 'note',
            'title': nt.title or 'Untitled Note',
            'parent_id': str(nt.id),
            'score': 1.0,
          })

    return SearchResponse(
      results=results or [],
      total_count=len(results) if results else 0,
      search_type=search_request.type,
    )

  except HTTPException:
    raise
  except Exception as e:
    logger.error(f'Unexpected error during search: {e!s}')
    raise HTTPException(status_code=500, detail=f'Search failed: {e!s}')


# Ask endpoints removed to keep the build ready with minimal deps.
