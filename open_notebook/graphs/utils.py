from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from langchain_openai import ChatOpenAI
from loguru import logger

from open_notebook.utils import token_count

if TYPE_CHECKING:
  from langchain_core.language_models.chat_models import BaseChatModel


async def provision_langchain_model(
  content: str, model_id: str | None, default_type: str, **kwargs: Any
) -> BaseChatModel:
  """Provision a LangChain Chat model.

  Uses OpenAI-compatible Chat via langchain-openai. If `model_id` is provided, it will be used. Otherwise falls back
  to env `DEFAULT_CHAT_MODEL` or `gpt-4o-mini`.
  """
  tokens = token_count(content)
  if tokens > 105_000:
    logger.debug('Using same model; adjust if you have a dedicated long context model')

  name = model_id or os.getenv('DEFAULT_CHAT_MODEL', 'gpt-4o-mini')
  temperature = kwargs.get('temperature', 0)
  max_tokens = kwargs.get('max_tokens')
  model = ChatOpenAI(model=name, temperature=temperature, max_tokens=max_tokens)
  logger.debug(f'Using chat model: {name}')
  return model
