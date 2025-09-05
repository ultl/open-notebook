from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger
from sqlalchemy import select

from open_notebook.database.models import PodcastEpisode
from open_notebook.database.sql import SessionLocal

if TYPE_CHECKING:
  from sqlalchemy.ext.asyncio import AsyncSession

_task: asyncio.Task | None = None


async def _process_episode(session: AsyncSession, ep: PodcastEpisode) -> None:
  ep.job_status = 'processing'
  session.add(ep)
  await session.commit()
  await asyncio.sleep(2.0)
  # Simulate artifact creation
  out_dir = Path('generated')
  out_dir.mkdir(parents=True, exist_ok=True)
  fake_path = out_dir / f'{ep.id}.mp3'
  fake_path.write_bytes(b'')
  ep.audio_file = str(fake_path)
  ep.job_status = 'completed'
  session.add(ep)
  await session.commit()


async def _worker_loop() -> None:
  logger.info('Podcast worker started')
  try:
    while True:
      async with SessionLocal() as session:
        res = await session.execute(select(PodcastEpisode).where(PodcastEpisode.job_status == 'queued'))
        items = list(res.scalars().all())
        for ep in items:
          try:
            await _process_episode(session, ep)
          except Exception as e:
            logger.error(f'Failed to process episode {ep.id}: {e!s}')
      await asyncio.sleep(5.0)
  except asyncio.CancelledError:
    logger.info('Podcast worker stopped')
    raise


def start_worker() -> None:
  global _task
  if _task is None or _task.done():
    _task = asyncio.create_task(_worker_loop())


def stop_worker() -> None:
  global _task
  if _task and not _task.done():
    _task.cancel()
