from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from sqlalchemy import select

from api.models import NoteCreate, NoteResponse, NoteUpdate
from open_notebook.database.models import Note
from open_notebook.database.sql import get_session

if TYPE_CHECKING:
  from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.get('/notes', response_model=list[NoteResponse])
async def get_notes(
  notebook_id: Annotated[str | None, Query(description='Filter by notebook ID')] = None,
  session: AsyncSession = Depends(get_session),
) -> list[NoteResponse]:
  """Get all notes with optional notebook filtering."""
  try:
    stmt = select(Note).where(Note.notebook_id == notebook_id) if notebook_id else select(Note)
    result = await session.execute(stmt)
    notes = list(result.scalars().all())

    return [
      NoteResponse(
        id=str(note.id),
        title=note.title,
        content=note.content,
        note_type=note.note_type,
        created=str(note.created),
        updated=str(note.updated),
      )
      for note in notes
    ]
  except HTTPException:
    raise
  except Exception as e:
    logger.error(f'Error fetching notes: {e!s}')
    raise HTTPException(status_code=500, detail=f'Error fetching notes: {e!s}')


@router.post('/notes', response_model=NoteResponse)
async def create_note(note_data: NoteCreate, session: AsyncSession = Depends(get_session)) -> NoteResponse:
  """Create a new note."""
  try:
    # Auto-generate title if not provided and it's an AI note
    title = note_data.title
    if not title and note_data.note_type == 'ai' and note_data.content:
      from open_notebook.graphs.prompt import graph as prompt_graph

      prompt = 'Based on the Note below, please provide a Title for this content, with max 15 words'
      result = await prompt_graph.ainvoke({
        'input_text': note_data.content,
        'prompt': prompt,
      })
      title = result.get('output', 'Untitled Note')

    new_note = Note(title=title, content=note_data.content, note_type=note_data.note_type)
    if note_data.notebook_id:
      new_note.notebook_id = note_data.notebook_id
    session.add(new_note)
    await session.commit()
    await session.refresh(new_note)

    return NoteResponse(
      id=str(new_note.id),
      title=new_note.title,
      content=new_note.content,
      note_type=new_note.note_type,
      created=str(new_note.created),
      updated=str(new_note.updated),
    )
  except HTTPException:
    raise
  except Exception as e:
    logger.error(f'Error creating note: {e!s}')
    raise HTTPException(status_code=500, detail=f'Error creating note: {e!s}')


@router.get('/notes/{note_id}', response_model=NoteResponse)
async def get_note(note_id: str, session: AsyncSession = Depends(get_session)) -> NoteResponse:
  """Get a specific note by ID."""
  try:
    result = await session.execute(select(Note).where(Note.id == note_id))
    note = result.scalar_one_or_none()
    if note is None:
      raise HTTPException(status_code=404, detail='Note not found')

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
    logger.error(f'Error fetching note {note_id}: {e!s}')
    raise HTTPException(status_code=500, detail=f'Error fetching note: {e!s}')


@router.put('/notes/{note_id}', response_model=NoteResponse)
async def update_note(
  note_id: str, note_update: NoteUpdate, session: AsyncSession = Depends(get_session)
) -> NoteResponse:
  """Update a note."""
  try:
    result = await session.execute(select(Note).where(Note.id == note_id))
    note = result.scalar_one_or_none()
    if note is None:
      raise HTTPException(status_code=404, detail='Note not found')

    # Update only provided fields
    if note_update.title is not None:
      note.title = note_update.title
    if note_update.content is not None:
      note.content = note_update.content
    if note_update.note_type is not None:
      note.note_type = note_update.note_type

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
  except InvalidInputError as e:
    raise HTTPException(status_code=400, detail=str(e))
  except Exception as e:
    logger.error(f'Error updating note {note_id}: {e!s}')
    raise HTTPException(status_code=500, detail=f'Error updating note: {e!s}')


@router.delete('/notes/{note_id}')
async def delete_note(note_id: str, session: AsyncSession = Depends(get_session)) -> dict[str, str]:
  """Delete a note."""
  try:
    result = await session.execute(select(Note).where(Note.id == note_id))
    note = result.scalar_one_or_none()
    if note is None:
      raise HTTPException(status_code=404, detail='Note not found')

    await session.delete(note)
    await session.commit()

    return {'message': 'Note deleted successfully'}
  except HTTPException:
    raise
  except Exception as e:
    logger.error(f'Error deleting note {note_id}: {e!s}')
    raise HTTPException(status_code=500, detail=f'Error deleting note: {e!s}')
