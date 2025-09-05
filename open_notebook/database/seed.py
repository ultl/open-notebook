from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from .models import AIModel, ContentSettings, DefaultModels, EpisodeProfile, SpeakerProfile

if TYPE_CHECKING:
  from sqlalchemy.ext.asyncio import AsyncSession


async def seed_defaults(session: AsyncSession) -> None:
  # Ensure singleton rows
  if (await session.execute(select(DefaultModels).where(DefaultModels.id == 1))).scalar_one_or_none() is None:
    session.add(DefaultModels(id=1))

  if (await session.execute(select(ContentSettings).where(ContentSettings.id == 1))).scalar_one_or_none() is None:
    session.add(ContentSettings(id=1))

  # Optional: add example profiles if none exist
  if (await session.execute(select(SpeakerProfile))).scalars().first() is None:
    session.add(
      SpeakerProfile(
        name='Default Speaker',
        description='Example speaker profile',
        tts_provider='openai',
        tts_model='gpt-4o-mini-tts',
        speakers=[{'name': 'Host', 'voice': 'alloy'}],
      )
    )
  if (await session.execute(select(EpisodeProfile))).scalars().first() is None:
    session.add(
      EpisodeProfile(
        name='Default Episode',
        description='Example episode profile',
        speaker_config='Default Speaker',
        outline_provider='openai',
        outline_model='gpt-4o-mini',
        transcript_provider='openai',
        transcript_model='whisper-1',
        default_briefing='Introduce the topic and discuss three key points.',
        num_segments=3,
      )
    )

  await session.commit()

  # Seed example AI models and set defaults if missing
  # Language model
  res = await session.execute(select(AIModel).where(AIModel.type == 'language'))
  lang = res.scalars().first()
  if lang is None:
    lang = AIModel(name='gpt-4o-mini', provider='openai', type='language')
    session.add(lang)

  # Embedding model (local)
  res = await session.execute(select(AIModel).where(AIModel.type == 'embedding'))
  emb = res.scalars().first()
  if emb is None:
    emb = AIModel(name='all-MiniLM-L6-v2', provider='sentence-transformers', type='embedding')
    session.add(emb)

  # Defaults
  defaults = (await session.execute(select(DefaultModels).where(DefaultModels.id == 1))).scalar_one()
  if not defaults.default_chat_model:
    defaults.default_chat_model = lang.id  # type: ignore[assignment]
  if not defaults.default_transformation_model:
    defaults.default_transformation_model = lang.id  # type: ignore[assignment]
  if not defaults.default_tools_model:
    defaults.default_tools_model = lang.id  # type: ignore[assignment]
  if not defaults.default_embedding_model:
    defaults.default_embedding_model = emb.id  # type: ignore[assignment]

  session.add(defaults)
  await session.commit()
