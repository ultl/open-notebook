from __future__ import annotations

from typing import TYPE_CHECKING, Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from sqlalchemy import select

from api.models import DefaultModelsResponse, ModelCreate, ModelResponse
from open_notebook.database.models import AIModel, DefaultModels
from open_notebook.database.sql import get_session

if TYPE_CHECKING:
  from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.get('/models', response_model=list[ModelResponse])
async def get_models(
  type: Annotated[str | None, Query(description='Filter by model type')] = None,
  session: AsyncSession = Depends(get_session),
) -> list[ModelResponse]:
  """Get all configured models with optional type filtering."""
  try:
    stmt = select(AIModel)
    if type:
      stmt = stmt.where(AIModel.type == type)
    result = await session.execute(stmt)
    models = list(result.scalars().all())

    return [
      ModelResponse(
        id=str(model.id),
        name=model.name,
        provider=model.provider,
        type=model.type,
        created=str(model.created),
        updated=str(model.updated),
      )
      for model in models
    ]
  except Exception as e:
    logger.error(f'Error fetching models: {e!s}')
    raise HTTPException(status_code=500, detail=f'Error fetching models: {e!s}')


@router.post('/models', response_model=ModelResponse)
async def create_model(model_data: ModelCreate, session: AsyncSession = Depends(get_session)) -> ModelResponse:
  """Create a new model configuration."""
  try:
    # Validate model type
    valid_types = ['language', 'embedding', 'text_to_speech', 'speech_to_text']
    if model_data.type not in valid_types:
      raise HTTPException(
        status_code=400,
        detail=f'Invalid model type. Must be one of: {valid_types}',
      )

    new_model = AIModel(name=model_data.name, provider=model_data.provider, type=model_data.type)
    session.add(new_model)
    await session.commit()
    await session.refresh(new_model)

    return ModelResponse(
      id=str(new_model.id),
      name=new_model.name,
      provider=new_model.provider,
      type=new_model.type,
      created=str(new_model.created),
      updated=str(new_model.updated),
    )
  except Exception as e:
    logger.error(f'Error creating model: {e!s}')
    raise HTTPException(status_code=500, detail=f'Error creating model: {e!s}')


@router.delete('/models/{model_id}')
async def delete_model(model_id: str, session: AsyncSession = Depends(get_session)) -> dict[str, str]:
  """Delete a model configuration."""
  try:
    result = await session.execute(select(AIModel).where(AIModel.id == model_id))
    model = result.scalar_one_or_none()
    if model is None:
      raise HTTPException(status_code=404, detail='Model not found')
    await session.delete(model)
    await session.commit()

    return {'message': 'Model deleted successfully'}
  except HTTPException:
    raise
  except Exception as e:
    logger.error(f'Error deleting model {model_id}: {e!s}')
    raise HTTPException(status_code=500, detail=f'Error deleting model: {e!s}')


@router.get('/models/defaults', response_model=DefaultModelsResponse)
async def get_default_models(session: AsyncSession = Depends(get_session)) -> DefaultModelsResponse:
  """Get default model assignments."""
  try:
    # Ensure singleton row exists
    result = await session.execute(select(DefaultModels).where(DefaultModels.id == 1))
    defaults = result.scalar_one_or_none()
    if defaults is None:
      defaults = DefaultModels(id=1)
      session.add(defaults)
      await session.commit()
      await session.refresh(defaults)

    return DefaultModelsResponse(
      default_chat_model=str(defaults.default_chat_model) if defaults.default_chat_model else None,
      default_transformation_model=str(defaults.default_transformation_model)
      if defaults.default_transformation_model
      else None,
      large_context_model=str(defaults.large_context_model) if defaults.large_context_model else None,
      default_text_to_speech_model=str(defaults.default_text_to_speech_model)
      if defaults.default_text_to_speech_model
      else None,
      default_speech_to_text_model=str(defaults.default_speech_to_text_model)
      if defaults.default_speech_to_text_model
      else None,
      default_embedding_model=str(defaults.default_embedding_model) if defaults.default_embedding_model else None,
      default_tools_model=str(defaults.default_tools_model) if defaults.default_tools_model else None,
    )
  except Exception as e:
    logger.error(f'Error fetching default models: {e!s}')
    raise HTTPException(status_code=500, detail=f'Error fetching default models: {e!s}')


@router.put('/models/defaults', response_model=DefaultModelsResponse)
async def update_default_models(
  defaults_data: DefaultModelsResponse, session: AsyncSession = Depends(get_session)
) -> DefaultModelsResponse:
  """Update default model assignments."""
  try:
    result = await session.execute(select(DefaultModels).where(DefaultModels.id == 1))
    defaults = result.scalar_one_or_none()
    if defaults is None:
      defaults = DefaultModels(id=1)
      session.add(defaults)
      await session.flush()

    # Update only provided fields
    if defaults_data.default_chat_model is not None:
      defaults.default_chat_model = UUID(defaults_data.default_chat_model)
    if defaults_data.default_transformation_model is not None:
      defaults.default_transformation_model = UUID(defaults_data.default_transformation_model)
    if defaults_data.large_context_model is not None:
      defaults.large_context_model = UUID(defaults_data.large_context_model)
    if defaults_data.default_text_to_speech_model is not None:
      defaults.default_text_to_speech_model = UUID(defaults_data.default_text_to_speech_model)
    if defaults_data.default_speech_to_text_model is not None:
      defaults.default_speech_to_text_model = UUID(defaults_data.default_speech_to_text_model)
    if defaults_data.default_embedding_model is not None:
      defaults.default_embedding_model = UUID(defaults_data.default_embedding_model)
    if defaults_data.default_tools_model is not None:
      defaults.default_tools_model = UUID(defaults_data.default_tools_model)

    session.add(defaults)
    await session.commit()
    await session.refresh(defaults)

    return DefaultModelsResponse(
      default_chat_model=str(defaults.default_chat_model) if defaults.default_chat_model else None,
      default_transformation_model=str(defaults.default_transformation_model)
      if defaults.default_transformation_model
      else None,
      large_context_model=str(defaults.large_context_model) if defaults.large_context_model else None,
      default_text_to_speech_model=str(defaults.default_text_to_speech_model)
      if defaults.default_text_to_speech_model
      else None,
      default_speech_to_text_model=str(defaults.default_speech_to_text_model)
      if defaults.default_speech_to_text_model
      else None,
      default_embedding_model=str(defaults.default_embedding_model) if defaults.default_embedding_model else None,
      default_tools_model=str(defaults.default_tools_model) if defaults.default_tools_model else None,
    )
  except HTTPException:
    raise
  except Exception as e:
    logger.error(f'Error updating default models: {e!s}')
    raise HTTPException(status_code=500, detail=f'Error updating default models: {e!s}')
