from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from sqlalchemy import select

from api.models import EmbedRequest, EmbedResponse
from open_notebook.database.models import Note, Source
from open_notebook.database.sql import get_session
from open_notebook.services.vector import embed_note, embed_source

if TYPE_CHECKING:
  from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.post('/embed', response_model=EmbedResponse)
async def embed_content(
  embed_request: EmbedRequest, session: Annotated[AsyncSession, Depends(get_session)]
) -> EmbedResponse:
  """Embed content for vector search."""
  try:
    item_id = embed_request.item_id
    item_type = embed_request.item_type.lower()

    # Validate item type
    if item_type not in {'source', 'note'}:
      raise HTTPException(status_code=400, detail="Item type must be either 'source' or 'note'")

    # Get the item and embed it
    if item_type == 'source':
      source_item = (await session.execute(select(Source).where(Source.id == item_id))).scalar_one_or_none()
      if source_item is None:
        raise HTTPException(status_code=404, detail='Source not found')
      count = await embed_source(session, source_item)
      return EmbedResponse(
        success=True,
        message=f'Embedded {count} chunks',
        item_id=item_id,
        item_type=item_type,
      )
    if item_type == 'note':
      note_item = (await session.execute(select(Note).where(Note.id == item_id))).scalar_one_or_none()
      if note_item is None:
        raise HTTPException(status_code=404, detail='Note not found')
      count = await embed_note(session, note_item)
      return EmbedResponse(
        success=True,
        message=f'Embedded {count} chunks',
        item_id=item_id,
        item_type=item_type,
      )
    raise HTTPException(status_code=400, detail="Item type must be either 'source' or 'note'")

  except HTTPException:
    raise
  except Exception as e:
    logger.error(f'Error embedding {embed_request.item_type} {embed_request.item_id}: {e!s}')
    raise HTTPException(status_code=500, detail=f'Error embedding content: {e!s}')
