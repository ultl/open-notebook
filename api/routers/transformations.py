from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from sqlalchemy import select

from api.models import (
  TransformationCreate,
  TransformationExecuteRequest,
  TransformationExecuteResponse,
  TransformationResponse,
  TransformationUpdate,
)
from open_notebook.database.models import AIModel, Transformation
from open_notebook.database.sql import get_session
from open_notebook.graphs.transformation import graph as transformation_graph

if TYPE_CHECKING:
  from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.get('/transformations', response_model=list[TransformationResponse])
async def get_transformations(session: AsyncSession = Depends(get_session)) -> list[TransformationResponse]:
  """Get all transformations."""
  try:
    result = await session.execute(select(Transformation))
    transformations = list(result.scalars().all())

    return [
      TransformationResponse(
        id=str(transformation.id),
        name=transformation.name,
        title=transformation.title,
        description=transformation.description,
        prompt=transformation.prompt,
        apply_default=transformation.apply_default,
        created=str(transformation.created),
        updated=str(transformation.updated),
      )
      for transformation in transformations
    ]
  except Exception as e:
    logger.error(f'Error fetching transformations: {e!s}')
    raise HTTPException(status_code=500, detail=f'Error fetching transformations: {e!s}')


@router.post('/transformations', response_model=TransformationResponse)
async def create_transformation(
  transformation_data: TransformationCreate, session: AsyncSession = Depends(get_session)
) -> TransformationResponse:
  """Create a new transformation."""
  try:
    new_transformation = Transformation(
      name=transformation_data.name,
      title=transformation_data.title,
      description=transformation_data.description,
      prompt=transformation_data.prompt,
      apply_default=transformation_data.apply_default,
    )
    session.add(new_transformation)
    await session.commit()
    await session.refresh(new_transformation)

    return TransformationResponse(
      id=str(new_transformation.id),
      name=new_transformation.name,
      title=new_transformation.title,
      description=new_transformation.description,
      prompt=new_transformation.prompt,
      apply_default=new_transformation.apply_default,
      created=str(new_transformation.created),
      updated=str(new_transformation.updated),
    )
  except Exception as e:
    logger.error(f'Error creating transformation: {e!s}')
    raise HTTPException(status_code=500, detail=f'Error creating transformation: {e!s}')


@router.get('/transformations/{transformation_id}', response_model=TransformationResponse)
async def get_transformation(
  transformation_id: str, session: AsyncSession = Depends(get_session)
) -> TransformationResponse:
  """Get a specific transformation by ID."""
  try:
    result = await session.execute(select(Transformation).where(Transformation.id == transformation_id))
    transformation = result.scalar_one_or_none()
    if transformation is None:
      raise HTTPException(status_code=404, detail='Transformation not found')

    return TransformationResponse(
      id=str(transformation.id),
      name=transformation.name,
      title=transformation.title,
      description=transformation.description,
      prompt=transformation.prompt,
      apply_default=transformation.apply_default,
      created=str(transformation.created),
      updated=str(transformation.updated),
    )
  except HTTPException:
    raise
  except Exception as e:
    logger.error(f'Error fetching transformation {transformation_id}: {e!s}')
    raise HTTPException(status_code=500, detail=f'Error fetching transformation: {e!s}')


@router.put('/transformations/{transformation_id}', response_model=TransformationResponse)
async def update_transformation(
  transformation_id: str,
  transformation_update: TransformationUpdate,
  session: AsyncSession = Depends(get_session),
) -> TransformationResponse:
  """Update a transformation."""
  try:
    result = await session.execute(select(Transformation).where(Transformation.id == transformation_id))
    transformation = result.scalar_one_or_none()
    if transformation is None:
      raise HTTPException(status_code=404, detail='Transformation not found')

    # Update only provided fields
    if transformation_update.name is not None:
      transformation.name = transformation_update.name
    if transformation_update.title is not None:
      transformation.title = transformation_update.title
    if transformation_update.description is not None:
      transformation.description = transformation_update.description
    if transformation_update.prompt is not None:
      transformation.prompt = transformation_update.prompt
    if transformation_update.apply_default is not None:
      transformation.apply_default = transformation_update.apply_default

    session.add(transformation)
    await session.commit()
    await session.refresh(transformation)

    return TransformationResponse(
      id=str(transformation.id),
      name=transformation.name,
      title=transformation.title,
      description=transformation.description,
      prompt=transformation.prompt,
      apply_default=transformation.apply_default,
      created=str(transformation.created),
      updated=str(transformation.updated),
    )
  except HTTPException:
    raise
  except InvalidInputError as e:
    raise HTTPException(status_code=400, detail=str(e))
  except Exception as e:
    logger.error(f'Error updating transformation {transformation_id}: {e!s}')
    raise HTTPException(status_code=500, detail=f'Error updating transformation: {e!s}')


@router.delete('/transformations/{transformation_id}')
async def delete_transformation(transformation_id: str, session: AsyncSession = Depends(get_session)) -> dict[str, str]:
  """Delete a transformation."""
  try:
    result = await session.execute(select(Transformation).where(Transformation.id == transformation_id))
    transformation = result.scalar_one_or_none()
    if transformation is None:
      raise HTTPException(status_code=404, detail='Transformation not found')

    await session.delete(transformation)
    await session.commit()

    return {'message': 'Transformation deleted successfully'}
  except HTTPException:
    raise
  except Exception as e:
    logger.error(f'Error deleting transformation {transformation_id}: {e!s}')
    raise HTTPException(status_code=500, detail=f'Error deleting transformation: {e!s}')


@router.post('/transformations/execute', response_model=TransformationExecuteResponse)
async def execute_transformation(
  execute_request: TransformationExecuteRequest, session: AsyncSession = Depends(get_session)
) -> TransformationExecuteResponse:
  """Execute a transformation on input text."""
  try:
    # Validate transformation exists
    result = await session.execute(select(Transformation).where(Transformation.id == execute_request.transformation_id))
    transformation = result.scalar_one_or_none()
    if transformation is None:
      raise HTTPException(status_code=404, detail='Transformation not found')

    # Validate model exists
    model_res = await session.execute(select(AIModel).where(AIModel.id == execute_request.model_id))
    model = model_res.scalar_one_or_none()
    if model is None:
      raise HTTPException(status_code=404, detail='Model not found')

    # Execute the transformation
    result = await transformation_graph.ainvoke(
      {
        'input_text': execute_request.input_text,
        'transformation': {
          'name': transformation.name,
          'title': transformation.title,
          'description': transformation.description,
          'prompt': transformation.prompt,
        },
      },
      config={'configurable': {'model_id': model.name}},
    )

    return TransformationExecuteResponse(
      output=result['output'],
      transformation_id=execute_request.transformation_id,
      model_id=execute_request.model_id,
    )

  except HTTPException:
    raise
  except Exception as e:
    logger.error(f'Error executing transformation: {e!s}')
    raise HTTPException(status_code=500, detail=f'Error executing transformation: {e!s}')
