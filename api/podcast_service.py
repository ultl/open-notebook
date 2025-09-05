from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from loguru import logger
from pydantic import BaseModel
from sqlalchemy import select

from open_notebook.database.models import EpisodeProfile, PodcastEpisode, SpeakerProfile
from open_notebook.database.sql import SessionLocal


class PodcastGenerationRequest(BaseModel):
  episode_profile: str
  speaker_profile: str
  episode_name: str
  content: str | None = None
  notebook_id: str | None = None
  briefing_suffix: str | None = None


class PodcastGenerationResponse(BaseModel):
  job_id: str
  status: str
  message: str
  episode_profile: str
  episode_name: str


class PodcastService:
  @staticmethod
  async def submit_generation_job(
    episode_profile_name: str,
    speaker_profile_name: str,
    episode_name: str,
    notebook_id: str | None = None,
    content: str | None = None,
    briefing_suffix: str | None = None,
  ) -> str:
    """Queue a minimal generation job and create a placeholder episode."""
    try:
      async with SessionLocal() as session:  # type: AsyncSession
        ep_prof = (
          await session.execute(select(EpisodeProfile).where(EpisodeProfile.name == episode_profile_name))
        ).scalar_one_or_none()
        if ep_prof is None:
          msg = f"Episode profile '{episode_profile_name}' not found"
          raise ValueError(msg)

        sp_prof = (
          await session.execute(select(SpeakerProfile).where(SpeakerProfile.name == speaker_profile_name))
        ).scalar_one_or_none()
        if sp_prof is None:
          msg = f"Speaker profile '{speaker_profile_name}' not found"
          raise ValueError(msg)

        if not content:
          msg = 'Content is required'
          raise ValueError(msg)

        briefing = (ep_prof.default_briefing or '') + (('\n' + (briefing_suffix or '')) if briefing_suffix else '')

        episode = PodcastEpisode(
          name=episode_name,
          episode_profile={
            'name': ep_prof.name,
            'outline_model': ep_prof.outline_model,
          },
          speaker_profile={'name': sp_prof.name, 'tts_model': sp_prof.tts_model},
          briefing=briefing,
          content=str(content),
          job_status='queued',
        )
        session.add(episode)
        await session.commit()
        await session.refresh(episode)
        logger.info(f"Queued podcast generation for episode '{episode_name}'")
        # Simulate job id with episode id
        return str(episode.id)
    except Exception as e:
      logger.error(f'Failed to submit podcast generation job: {e}')
      raise HTTPException(status_code=500, detail=f'Failed to submit podcast generation job: {e!s}')

  @staticmethod
  async def get_job_status(job_id: str) -> dict[str, Any]:
    try:
      async with SessionLocal() as session:
        ep = (await session.execute(select(PodcastEpisode).where(PodcastEpisode.id == job_id))).scalar_one_or_none()
        if ep is None:
          msg = 'Job not found'
          raise ValueError(msg)
        return {
          'job_id': job_id,
          'status': ep.job_status or 'unknown',
          'result': {'episode_id': str(ep.id)} if ep.audio_file else None,
          'error_message': None,
          'created': str(ep.created) if ep.created else None,
          'updated': str(ep.updated) if ep.updated else None,
          'progress': None,
        }
    except Exception as e:
      logger.error(f'Failed to get podcast job status: {e}')
      raise HTTPException(status_code=500, detail=f'Failed to get job status: {e!s}')

  @staticmethod
  async def list_episodes() -> list[PodcastEpisode]:
    try:
      async with SessionLocal() as session:
        res = await session.execute(select(PodcastEpisode))
        return list(res.scalars().all())
    except Exception as e:
      logger.error(f'Failed to list podcast episodes: {e}')
      raise HTTPException(status_code=500, detail=f'Failed to list episodes: {e!s}')

  @staticmethod
  async def get_episode(episode_id: str) -> PodcastEpisode:
    try:
      async with SessionLocal() as session:
        res = await session.execute(select(PodcastEpisode).where(PodcastEpisode.id == episode_id))
        ep = res.scalar_one_or_none()
        if ep is None:
          msg = 'Episode not found'
          raise ValueError(msg)
        return ep
    except Exception as e:
      logger.error(f'Failed to get podcast episode {episode_id}: {e}')
      raise HTTPException(status_code=404, detail=f'Episode not found: {e!s}')


class DefaultProfiles:
  @staticmethod
  async def create_default_episode_profiles() -> list[EpisodeProfile]:
    try:
      # Check if profiles already exist
      existing = await EpisodeProfile.get_all()
      if existing:
        logger.info(f'Episode profiles already exist: {len(existing)} found')
        return existing

      return []

    except Exception as e:
      logger.error(f'Failed to create default episode profiles: {e}')
      raise

  @staticmethod
  async def create_default_speaker_profiles() -> list[SpeakerProfile]:
    try:
      # Check if profiles already exist
      existing = await SpeakerProfile.get_all()
      if existing:
        logger.info(f'Speaker profiles already exist: {len(existing)} found')
        return existing

      # This would create profiles, but since we have migration data,
      # this is mainly for future extensibility
      logger.info('Default speaker profiles should be created via database migration')
      return []

    except Exception as e:
      logger.error(f'Failed to create default speaker profiles: {e}')
      raise
