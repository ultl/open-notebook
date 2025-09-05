from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from sqlalchemy import select

from api.models import SettingsResponse, SettingsUpdate
from open_notebook.database.models import ContentSettings
from open_notebook.database.sql import get_session

if TYPE_CHECKING:
  from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.get('/settings', response_model=SettingsResponse)
async def get_settings(session: Annotated[AsyncSession, Depends(get_session)]) -> SettingsResponse:
  """Get all application settings."""
  try:
    result = await session.execute(select(ContentSettings).where(ContentSettings.id == 1))
    settings = result.scalar_one_or_none()
    if settings is None:
      settings = ContentSettings(id=1)
      session.add(settings)
      await session.commit()
      await session.refresh(settings)

    return SettingsResponse(
      default_content_processing_engine_doc=settings.default_content_processing_engine_doc,
      default_content_processing_engine_url=settings.default_content_processing_engine_url,
      default_embedding_option=settings.default_embedding_option,
      auto_delete_files=settings.auto_delete_files,
      youtube_preferred_languages=settings.youtube_preferred_languages,
    )
  except Exception as e:
    logger.error(f'Error fetching settings: {e!s}')
    raise HTTPException(status_code=500, detail=f'Error fetching settings: {e!s}')


@router.put('/settings', response_model=SettingsResponse)
async def update_settings(
  settings_update: SettingsUpdate, session: Annotated[AsyncSession, Depends(get_session)]
) -> SettingsResponse:
  """Update application settings."""
  try:
    result = await session.execute(select(ContentSettings).where(ContentSettings.id == 1))
    settings = result.scalar_one_or_none()
    if settings is None:
      settings = ContentSettings(id=1)
      session.add(settings)

    # Update only provided fields
    if settings_update.default_content_processing_engine_doc is not None:
      settings.default_content_processing_engine_doc = settings_update.default_content_processing_engine_doc
    if settings_update.default_content_processing_engine_url is not None:
      settings.default_content_processing_engine_url = settings_update.default_content_processing_engine_url
    if settings_update.default_embedding_option is not None:
      settings.default_embedding_option = settings_update.default_embedding_option
    if settings_update.auto_delete_files is not None:
      settings.auto_delete_files = settings_update.auto_delete_files
    if settings_update.youtube_preferred_languages is not None:
      settings.youtube_preferred_languages = settings_update.youtube_preferred_languages

    session.add(settings)
    await session.commit()
    await session.refresh(settings)

    return SettingsResponse(
      default_content_processing_engine_doc=settings.default_content_processing_engine_doc,
      default_content_processing_engine_url=settings.default_content_processing_engine_url,
      default_embedding_option=settings.default_embedding_option,
      auto_delete_files=settings.auto_delete_files,
      youtube_preferred_languages=settings.youtube_preferred_languages,
    )
  except HTTPException:
    raise
  except Exception as e:
    logger.error(f'Error updating settings: {e!s}')
    raise HTTPException(status_code=500, detail=f'Error updating settings: {e!s}')
