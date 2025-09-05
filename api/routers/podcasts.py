from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel

from api.podcast_service import (
  PodcastGenerationRequest,
  PodcastGenerationResponse,
  PodcastService,
)

router = APIRouter()


class PodcastEpisodeResponse(BaseModel):
  id: str
  name: str
  episode_profile: dict
  speaker_profile: dict
  briefing: str
  audio_file: str | None = None
  transcript: dict | None = None
  outline: dict | None = None
  created: str | None = None
  job_status: str | None = None


@router.post('/podcasts/generate', response_model=PodcastGenerationResponse)
async def generate_podcast(request: PodcastGenerationRequest) -> PodcastGenerationResponse:
  """Generate a podcast episode using Episode Profiles.
  Returns immediately with job ID for status tracking.
  """
  try:
    job_id = await PodcastService.submit_generation_job(
      episode_profile_name=request.episode_profile,
      speaker_profile_name=request.speaker_profile,
      episode_name=request.episode_name,
      notebook_id=request.notebook_id,
      content=request.content,
      briefing_suffix=request.briefing_suffix,
    )

    return PodcastGenerationResponse(
      job_id=job_id,
      status='submitted',
      message=f"Podcast generation started for episode '{request.episode_name}'",
      episode_profile=request.episode_profile,
      episode_name=request.episode_name,
    )

  except Exception as e:
    logger.error(f'Error generating podcast: {e!s}')
    raise HTTPException(status_code=500, detail=f'Failed to generate podcast: {e!s}')


@router.get('/podcasts/jobs/{job_id}')
async def get_podcast_job_status(job_id: str) -> dict[str, Any]:
  """Get the status of a podcast generation job."""
  try:
    return await PodcastService.get_job_status(job_id)

  except Exception as e:
    logger.error(f'Error fetching podcast job status: {e!s}')
    raise HTTPException(status_code=500, detail=f'Failed to fetch job status: {e!s}')


@router.get('/podcasts/episodes', response_model=list[PodcastEpisodeResponse])
async def list_podcast_episodes() -> list[PodcastEpisodeResponse]:
  """List all podcast episodes."""
  try:
    episodes = await PodcastService.list_episodes()

    response_episodes = []
    for episode in episodes:
      # Skip incomplete episodes without command or audio
      if not episode.command and not episode.audio_file:
        continue

      # Get job status if available
      job_status = None
      if episode.command:
        try:
          job_status = await episode.get_job_status()
        except:
          job_status = 'unknown'
      else:
        # No command but has audio file = completed import
        job_status = 'completed'

      response_episodes.append(
        PodcastEpisodeResponse(
          id=str(episode.id),
          name=episode.name,
          episode_profile=episode.episode_profile,
          speaker_profile=episode.speaker_profile,
          briefing=episode.briefing,
          audio_file=episode.audio_file,
          transcript=episode.transcript,
          outline=episode.outline,
          created=str(episode.created) if episode.created else None,
          job_status=job_status,
        )
      )

    return response_episodes

  except Exception as e:
    logger.error(f'Error listing podcast episodes: {e!s}')
    raise HTTPException(status_code=500, detail=f'Failed to list podcast episodes: {e!s}')


@router.get('/podcasts/episodes/{episode_id}', response_model=PodcastEpisodeResponse)
async def get_podcast_episode(episode_id: str) -> PodcastEpisodeResponse:
  """Get a specific podcast episode."""
  try:
    episode = await PodcastService.get_episode(episode_id)

    # Get job status if available
    job_status = None
    if episode.command:
      try:
        job_status = await episode.get_job_status()
      except:
        job_status = 'unknown'
    else:
      # No command but has audio file = completed import
      job_status = 'completed' if episode.audio_file else 'unknown'

    return PodcastEpisodeResponse(
      id=str(episode.id),
      name=episode.name,
      episode_profile=episode.episode_profile,
      speaker_profile=episode.speaker_profile,
      briefing=episode.briefing,
      audio_file=episode.audio_file,
      transcript=episode.transcript,
      outline=episode.outline,
      created=str(episode.created) if episode.created else None,
      job_status=job_status,
    )

  except Exception as e:
    logger.error(f'Error fetching podcast episode: {e!s}')
    raise HTTPException(status_code=404, detail=f'Episode not found: {e!s}')


@router.delete('/podcasts/episodes/{episode_id}')
async def delete_podcast_episode(episode_id: str) -> dict[str, str]:
  """Delete a podcast episode and its associated audio file."""
  try:
    # Get the episode first to check if it exists and get the audio file path
    episode = await PodcastService.get_episode(episode_id)

    # Delete the physical audio file if it exists
    if episode.audio_file:
      audio_path = Path(episode.audio_file)
      if audio_path.exists():
        try:
          audio_path.unlink()
          logger.info(f'Deleted audio file: {audio_path}')
        except Exception as e:
          logger.warning(f'Failed to delete audio file {audio_path}: {e}')

    # Delete the episode from the database
    # Minimal deletion handled here to avoid cross-layer coupling
    from sqlalchemy import select

    from open_notebook.database.models import PodcastEpisode
    from open_notebook.database.sql import SessionLocal

    async with SessionLocal() as session:
      res = await session.execute(select(PodcastEpisode).where(PodcastEpisode.id == episode_id))
      ep = res.scalar_one_or_none()
      if ep:
        await session.delete(ep)
        await session.commit()

    logger.info(f'Deleted podcast episode: {episode_id}')
    return {'message': 'Episode deleted successfully', 'episode_id': episode_id}

  except Exception as e:
    logger.error(f'Error deleting podcast episode: {e!s}')
    raise HTTPException(status_code=500, detail=f'Failed to delete episode: {e!s}')
