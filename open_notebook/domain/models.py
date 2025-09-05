from __future__ import annotations

from typing import Any, Self

from sqlalchemy import select

from open_notebook.database.models import DefaultModels
from open_notebook.database.sql import SessionLocal


class ModelManager:
  _instance = None

  def __new__(cls) -> Self:
    if cls._instance is None:
      cls._instance = super().__new__(cls)
    return cls._instance

  def __init__(self) -> None:
    if not hasattr(self, '_initialized'):
      self._initialized = True
      self._model_cache: dict[str, Any] = {}
      self._default_models: DefaultModels | None = None

  async def get_model(self, model_id: str, **kwargs) -> Any | None:
    # No provider construction in this refactor; graphs construct models directly
    return None

  async def refresh_defaults(self) -> None:
    """Refresh the default models from the database."""
    async with SessionLocal() as session:  # type: AsyncSession
      result = await session.execute(select(DefaultModels).where(DefaultModels.id == 1))
      defaults = result.scalar_one_or_none()
      if defaults is None:
        defaults = DefaultModels(id=1)
        session.add(defaults)
        await session.commit()
        await session.refresh(defaults)
      self._default_models = defaults

  async def get_defaults(self) -> DefaultModels:
    """Get the default models configuration."""
    if not self._default_models:
      await self.refresh_defaults()
      if not self._default_models:
        msg = 'Failed to initialize default models configuration'
        raise RuntimeError(msg)
    return self._default_models

  async def get_speech_to_text(self, **kwargs) -> Any | None:
    """Get the default speech-to-text model."""
    defaults = await self.get_defaults()
    model_id = defaults.default_speech_to_text_model
    if not model_id:
      return None
    return await self.get_model(model_id, **kwargs)

  async def get_text_to_speech(self, **kwargs) -> Any | None:
    """Get the default text-to-speech model."""
    defaults = await self.get_defaults()
    model_id = defaults.default_text_to_speech_model
    if not model_id:
      return None
    return await self.get_model(model_id, **kwargs)

  async def get_embedding_model(self, **kwargs) -> Any | None:
    """Get the default embedding model."""
    defaults = await self.get_defaults()
    model_id = str(defaults.default_embedding_model) if defaults.default_embedding_model else None
    if not model_id:
      return None
    return await self.get_model(model_id, **kwargs)

  async def get_default_model(self, model_type: str, **kwargs) -> Any | None:
    """Get the default model for a specific type.

    Args:
        model_type: The type of model to retrieve (e.g., 'chat', 'embedding', etc.)
        **kwargs: Additional arguments to pass to the model constructor
    """
    defaults = await self.get_defaults()
    model_id = None

    if model_type == 'chat':
      model_id = str(defaults.default_chat_model) if defaults.default_chat_model else None
    elif model_type == 'transformation':
      model_id = (
        str(defaults.default_transformation_model)
        if defaults.default_transformation_model
        else (str(defaults.default_chat_model) if defaults.default_chat_model else None)
      )
    elif model_type == 'tools':
      model_id = (
        str(defaults.default_tools_model)
        if defaults.default_tools_model
        else (str(defaults.default_chat_model) if defaults.default_chat_model else None)
      )
    elif model_type == 'embedding':
      model_id = str(defaults.default_embedding_model) if defaults.default_embedding_model else None
    elif model_type == 'text_to_speech':
      model_id = str(defaults.default_text_to_speech_model) if defaults.default_text_to_speech_model else None
    elif model_type == 'speech_to_text':
      model_id = str(defaults.default_speech_to_text_model) if defaults.default_speech_to_text_model else None
    elif model_type == 'large_context':
      model_id = str(defaults.large_context_model) if defaults.large_context_model else None

    if not model_id:
      return None

    return await self.get_model(model_id, **kwargs)

  def clear_cache(self) -> None:
    """Clear the model cache."""
    self._model_cache.clear()


model_manager = ModelManager()
