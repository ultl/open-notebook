from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from sqlalchemy import select

from api.models import ContextRequest, ContextResponse
from open_notebook.database.models import Note, Notebook, Source
from open_notebook.database.sql import get_session
from open_notebook.utils import token_count

if TYPE_CHECKING:
  from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.post('/notebooks/{notebook_id}/context', response_model=ContextResponse)
async def get_notebook_context(
  notebook_id: str, context_request: ContextRequest, session: Annotated[AsyncSession, Depends(get_session)]
) -> ContextResponse:
  """Get context for a notebook based on configuration."""
  try:
    # Verify notebook exists
    notebook = (await session.execute(select(Notebook).where(Notebook.id == notebook_id))).scalar_one_or_none()
    if notebook is None:
      raise HTTPException(status_code=404, detail='Notebook not found')

    context_data = {'note': [], 'source': []}
    total_content = ''

    # Process context configuration if provided
    if context_request.context_config:
      # Process sources
      for source_id, status in context_request.context_config.sources.items():
        if 'not in' in status:
          continue

        try:
          source = (await session.execute(select(Source).where(Source.id == source_id))).scalar_one_or_none()
          if source is None:
            continue

          if 'insights' in status:
            src_desc = {
              'id': str(source.id),
              'title': source.title,
              'snippet': (source.full_text or '')[:400],
            }
            context_data['source'].append(src_desc)
            total_content += src_desc.get('snippet') or ''
          elif 'full content' in status:
            src_desc = {
              'id': str(source.id),
              'title': source.title,
              'content': source.full_text or '',
            }
            context_data['source'].append(src_desc)
            total_content += src_desc.get('content') or ''
        except Exception as e:
          logger.warning(f'Error processing source {source_id}: {e!s}')
          continue

      # Process notes
      for note_id, status in context_request.context_config.notes.items():
        if 'not in' in status:
          continue

        try:
          # Add table prefix if not present
          note = (await session.execute(select(Note).where(Note.id == note_id))).scalar_one_or_none()
          if note is None:
            continue

          if 'full content' in status:
            note_desc = {
              'id': str(note.id),
              'title': note.title,
              'content': note.content or '',
            }
            context_data['note'].append(note_desc)
            total_content += note_desc.get('content') or ''
        except Exception as e:
          logger.warning(f'Error processing note {note_id}: {e!s}')
          continue
    else:
      # Default behavior - include all sources and notes with short context
      sources = list((await session.execute(select(Source).where(Source.notebook_id == notebook.id))).scalars().all())
      for source in sources:
        try:
          src_desc = {
            'id': str(source.id),
            'title': source.title,
            'snippet': (source.full_text or '')[:400],
          }
          context_data['source'].append(src_desc)
          total_content += src_desc.get('snippet') or ''
        except Exception as e:
          logger.warning(f'Error processing source {source.id}: {e!s}')
          continue

      notes = list((await session.execute(select(Note).where(Note.notebook_id == notebook.id))).scalars().all())
      for note in notes:
        try:
          note_desc = {
            'id': str(note.id),
            'title': note.title,
            'snippet': (note.content or '')[:400],
          }
          context_data['note'].append(note_desc)
          total_content += note_desc.get('snippet') or ''
        except Exception as e:
          logger.warning(f'Error processing note {note.id}: {e!s}')
          continue

    # Calculate estimated token count
    estimated_tokens = token_count(total_content) if total_content else 0

    return ContextResponse(
      notebook_id=notebook_id,
      sources=context_data['source'],
      notes=context_data['note'],
      total_tokens=estimated_tokens,
    )

  except HTTPException:
    raise
  except Exception as e:
    logger.error(f'Error getting context for notebook {notebook_id}: {e!s}')
    raise HTTPException(status_code=500, detail=f'Error getting context: {e!s}')
