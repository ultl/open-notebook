from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound

from api.models import NotebookCreate, NotebookResponse, NotebookUpdate
from open_notebook.database.models import Notebook
from open_notebook.database.sql import get_session

if TYPE_CHECKING:
  from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.get('/notebooks', response_model=list[NotebookResponse])
async def get_notebooks(
  archived: Annotated[bool | None, Query(description='Filter by archived status')] = None,
  order_by: Annotated[str, Query(description='Order by field and direction')] = 'updated desc',
  session: AsyncSession = Depends(get_session),
) -> list[NotebookResponse]:
  """Get all notebooks with optional filtering and ordering."""
  try:
    stmt = select(Notebook)
    result = await session.execute(stmt)
    notebooks = list(result.scalars().all())

    # Filter by archived status if specified
    if archived is not None:
      notebooks = [nb for nb in notebooks if nb.archived == archived]

    return [
      NotebookResponse(
        id=str(nb.id),
        name=nb.name,
        description=nb.description,
        archived=nb.archived or False,
        created=str(nb.created),
        updated=str(nb.updated),
      )
      for nb in notebooks
    ]
  except Exception as e:
    logger.error(f'Error fetching notebooks: {e!s}')
    raise HTTPException(status_code=500, detail=f'Error fetching notebooks: {e!s}')


@router.post('/notebooks', response_model=NotebookResponse)
async def create_notebook(notebook: NotebookCreate, session: AsyncSession = Depends(get_session)) -> NotebookResponse:
  """Create a new notebook."""
  try:
    new_notebook = Notebook(name=notebook.name, description=notebook.description)
    session.add(new_notebook)
    await session.commit()
    await session.refresh(new_notebook)

    return NotebookResponse(
      id=str(new_notebook.id),
      name=new_notebook.name,
      description=new_notebook.description,
      archived=new_notebook.archived or False,
      created=str(new_notebook.created),
      updated=str(new_notebook.updated),
    )
  except Exception as e:
    logger.error(f'Error creating notebook: {e!s}')
    raise HTTPException(status_code=500, detail=f'Error creating notebook: {e!s}')


@router.get('/notebooks/{notebook_id}', response_model=NotebookResponse)
async def get_notebook(notebook_id: str, session: AsyncSession = Depends(get_session)) -> NotebookResponse:
  """Get a specific notebook by ID."""
  try:
    try:
      stmt = select(Notebook).where(Notebook.id == notebook_id)
      notebook = (await session.execute(stmt)).scalar_one()
    except NoResultFound:
      raise HTTPException(status_code=404, detail='Notebook not found')

    return NotebookResponse(
      id=str(notebook.id),
      name=notebook.name,
      description=notebook.description,
      archived=notebook.archived or False,
      created=str(notebook.created),
      updated=str(notebook.updated),
    )
  except HTTPException:
    raise
  except Exception as e:
    logger.error(f'Error fetching notebook {notebook_id}: {e!s}')
    raise HTTPException(status_code=500, detail=f'Error fetching notebook: {e!s}')


@router.put('/notebooks/{notebook_id}', response_model=NotebookResponse)
async def update_notebook(
  notebook_id: str, notebook_update: NotebookUpdate, session: AsyncSession = Depends(get_session)
) -> NotebookResponse:
  """Update a notebook."""
  try:
    try:
      stmt = select(Notebook).where(Notebook.id == notebook_id)
      notebook = (await session.execute(stmt)).scalar_one()
    except NoResultFound:
      raise HTTPException(status_code=404, detail='Notebook not found')

    # Update only provided fields
    if notebook_update.name is not None:
      notebook.name = notebook_update.name
    if notebook_update.description is not None:
      notebook.description = notebook_update.description
    if notebook_update.archived is not None:
      notebook.archived = notebook_update.archived

    # Touch updated timestamp
    notebook.updated = notebook.updated
    session.add(notebook)
    await session.commit()
    await session.refresh(notebook)

    return NotebookResponse(
      id=str(notebook.id),
      name=notebook.name,
      description=notebook.description,
      archived=notebook.archived or False,
      created=str(notebook.created),
      updated=str(notebook.updated),
    )
  except HTTPException:
    raise
  except Exception as e:
    logger.error(f'Error updating notebook {notebook_id}: {e!s}')
    raise HTTPException(status_code=500, detail=f'Error updating notebook: {e!s}')


@router.delete('/notebooks/{notebook_id}')
async def delete_notebook(notebook_id: str, session: AsyncSession = Depends(get_session)) -> dict[str, str]:
  """Delete a notebook."""
  try:
    try:
      stmt = select(Notebook).where(Notebook.id == notebook_id)
      notebook = (await session.execute(stmt)).scalar_one()
    except NoResultFound:
      raise HTTPException(status_code=404, detail='Notebook not found')

    await session.delete(notebook)
    await session.commit()

    return {'message': 'Notebook deleted successfully'}
  except HTTPException:
    raise
  except Exception as e:
    logger.error(f'Error deleting notebook {notebook_id}: {e!s}')
    raise HTTPException(status_code=500, detail=f'Error deleting notebook: {e!s}')
