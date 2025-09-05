from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from sqlalchemy import select

from api.models import NoteResponse, SaveAsNoteRequest, SourceInsightResponse
from open_notebook.database.models import Note, Notebook, Source, SourceInsight
from open_notebook.database.sql import get_session

if TYPE_CHECKING:
  from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.get('/insights/{insight_id}', response_model=SourceInsightResponse)
async def get_insight(insight_id: str, session: Annotated[AsyncSession, Depends(get_session)]) -> SourceInsightResponse:
  """Get a specific insight by ID."""
  try:
    insight = (await session.execute(select(SourceInsight).where(SourceInsight.id == insight_id))).scalar_one_or_none()
    if insight is None:
      raise HTTPException(status_code=404, detail='Insight not found')

    return SourceInsightResponse(
      id=str(insight.id),
      source_id=str(insight.source_id),
      insight_type=insight.insight_type,
      content=insight.content,
      created=str(insight.created),
      updated=str(insight.updated),
    )
  except HTTPException:
    raise
  except Exception as e:
    logger.error(f'Error fetching insight {insight_id}: {e!s}')
    raise HTTPException(status_code=500, detail=f'Error fetching insight: {e!s}')


@router.delete('/insights/{insight_id}')
async def delete_insight(insight_id: str, session: Annotated[AsyncSession, Depends(get_session)]) -> dict[str, str]:
  """Delete a specific insight."""
  try:
    insight = (await session.execute(select(SourceInsight).where(SourceInsight.id == insight_id))).scalar_one_or_none()
    if insight is None:
      raise HTTPException(status_code=404, detail='Insight not found')

    await session.delete(insight)
    await session.commit()

    return {'message': 'Insight deleted successfully'}
  except HTTPException:
    raise
  except Exception as e:
    logger.error(f'Error deleting insight {insight_id}: {e!s}')
    raise HTTPException(status_code=500, detail=f'Error deleting insight: {e!s}')


@router.post('/insights/{insight_id}/save-as-note', response_model=NoteResponse)
async def save_insight_as_note(
  insight_id: str, request: SaveAsNoteRequest, session: Annotated[AsyncSession, Depends(get_session)]
) -> NoteResponse:
  """Convert an insight to a note."""
  try:
    insight = (await session.execute(select(SourceInsight).where(SourceInsight.id == insight_id))).scalar_one_or_none()
    if insight is None:
      raise HTTPException(status_code=404, detail='Insight not found')

    target_notebook_id = request.notebook_id
    if not target_notebook_id:
      # Use the source's notebook if not provided
      source = (await session.execute(select(Source).where(Source.id == insight.source_id))).scalar_one_or_none()
      if source is None:
        raise HTTPException(status_code=400, detail='Cannot infer notebook for note')
      target_notebook_id = str(source.notebook_id)

    # Validate notebook exists
    nb = (await session.execute(select(Notebook).where(Notebook.id == target_notebook_id))).scalar_one_or_none()
    if nb is None:
      raise HTTPException(status_code=404, detail='Notebook not found')

    note = Note(title=None, content=insight.content, note_type='ai', notebook_id=nb.id)
    session.add(note)
    await session.commit()
    await session.refresh(note)

    return NoteResponse(
      id=str(note.id),
      title=note.title,
      content=note.content,
      note_type=note.note_type,
      created=str(note.created),
      updated=str(note.updated),
    )
  except HTTPException:
    raise
  except Exception as e:
    logger.error(f'Error saving insight {insight_id} as note: {e!s}')
    raise HTTPException(status_code=500, detail=f'Error saving insight as note: {e!s}')
