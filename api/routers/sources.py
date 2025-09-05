from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from sqlalchemy import func, select

from api.models import (
  AssetModel,
  CreateSourceInsightRequest,
  SourceCreate,
  SourceInsightResponse,
  SourceListResponse,
  SourceResponse,
  SourceUpdate,
)
from open_notebook.database.models import Notebook, Source, SourceInsight, Transformation
from open_notebook.database.sql import get_session
from open_notebook.graphs.transformation import graph as transform_graph
from open_notebook.services.vector import embed_source

if TYPE_CHECKING:
  from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.get('/sources', response_model=list[SourceListResponse])
async def get_sources(
  notebook_id: Annotated[str | None, Query(description='Filter by notebook ID')] = None,
  session: AsyncSession = Depends(get_session),
) -> list[SourceListResponse]:
  """Get all sources with optional notebook filtering."""
  try:
    stmt = select(Source)
    if notebook_id:
      # Validate notebook exists
      nb = (await session.execute(select(Notebook).where(Notebook.id == notebook_id))).scalar_one_or_none()
      if nb is None:
        raise HTTPException(status_code=404, detail='Notebook not found')
      stmt = stmt.where(Source.notebook_id == notebook_id)

    sources = list((await session.execute(stmt)).scalars().all())

    # Fetch insights count per source in one query
    counts = dict(
      (
        await session.execute(
          select(SourceInsight.source_id, func.count(SourceInsight.id)).group_by(SourceInsight.source_id)
        )
      ).all()
    )

    return [
      SourceListResponse(
        id=str(src.id),
        title=src.title,
        topics=src.topics or [],
        asset=AssetModel(
          file_path=(src.asset or {}).get('file_path') if src.asset else None,
          url=(src.asset or {}).get('url') if src.asset else None,
        )
        if src.asset
        else None,
        embedded_chunks=src.embedded_chunks,
        insights_count=int(counts.get(src.id, 0)),
        created=str(src.created),
        updated=str(src.updated),
      )
      for src in sources
    ]
  except HTTPException:
    raise
  except Exception as e:
    logger.error(f'Error fetching sources: {e!s}')
    raise HTTPException(status_code=500, detail=f'Error fetching sources: {e!s}')


@router.post('/sources', response_model=SourceResponse)
async def create_source(source_data: SourceCreate, session: AsyncSession = Depends(get_session)) -> SourceResponse:
  """Create a new source."""
  try:
    # Verify notebook exists
    nb = (await session.execute(select(Notebook).where(Notebook.id == source_data.notebook_id))).scalar_one_or_none()
    if nb is None:
      raise HTTPException(status_code=404, detail='Notebook not found')

    if source_data.type not in {'link', 'upload', 'text'}:
      raise HTTPException(status_code=400, detail='Invalid source type. Must be link, upload, or text')

    if source_data.type == 'link' and not source_data.url:
      raise HTTPException(status_code=400, detail='URL is required for link type')
    if source_data.type == 'upload' and not source_data.file_path:
      raise HTTPException(status_code=400, detail='File path is required for upload type')
    if source_data.type == 'text' and not source_data.content:
      raise HTTPException(status_code=400, detail='Content is required for text type')

    src = Source(
      notebook_id=nb.id,
      type=source_data.type,
      url=source_data.url,
      file_path=source_data.file_path,
      content=source_data.content,
      title=source_data.title,
      asset={
        'url': source_data.url,
        'file_path': source_data.file_path,
      }
      if (source_data.url or source_data.file_path)
      else None,
      full_text=source_data.content if source_data.type == 'text' else None,
      embedded_chunks=0,
    )
    session.add(src)
    await session.commit()
    await session.refresh(src)

    # Embed on request
    if source_data.embed:
      await embed_source(session, src)

    return SourceResponse(
      id=str(src.id),
      title=src.title,
      topics=src.topics or [],
      asset=AssetModel(
        file_path=(src.asset or {}).get('file_path') if src.asset else None,
        url=(src.asset or {}).get('url') if src.asset else None,
      )
      if src.asset
      else None,
      full_text=src.full_text,
      embedded_chunks=src.embedded_chunks,
      created=str(src.created),
      updated=str(src.updated),
    )
  except HTTPException:
    raise
  except InvalidInputError as e:
    raise HTTPException(status_code=400, detail=str(e))
  except Exception as e:
    logger.error(f'Error creating source: {e!s}')
    raise HTTPException(status_code=500, detail=f'Error creating source: {e!s}')


@router.get('/sources/{source_id}', response_model=SourceResponse)
async def get_source(source_id: str, session: AsyncSession = Depends(get_session)) -> SourceResponse:
  """Get a specific source by ID."""
  try:
    source = (await session.execute(select(Source).where(Source.id == source_id))).scalar_one_or_none()
    if source is None:
      raise HTTPException(status_code=404, detail='Source not found')

    return SourceResponse(
      id=str(source.id),
      title=source.title,
      topics=source.topics or [],
      asset=AssetModel(
        file_path=(source.asset or {}).get('file_path') if source.asset else None,
        url=(source.asset or {}).get('url') if source.asset else None,
      )
      if source.asset
      else None,
      full_text=source.full_text,
      embedded_chunks=source.embedded_chunks,
      created=str(source.created),
      updated=str(source.updated),
    )
  except HTTPException:
    raise
  except Exception as e:
    logger.error(f'Error fetching source {source_id}: {e!s}')
    raise HTTPException(status_code=500, detail=f'Error fetching source: {e!s}')


@router.put('/sources/{source_id}', response_model=SourceResponse)
async def update_source(
  source_id: str, source_update: SourceUpdate, session: AsyncSession = Depends(get_session)
) -> SourceResponse:
  """Update a source."""
  try:
    source = (await session.execute(select(Source).where(Source.id == source_id))).scalar_one_or_none()
    if source is None:
      raise HTTPException(status_code=404, detail='Source not found')

    # Update only provided fields
    if source_update.title is not None:
      source.title = source_update.title
    if source_update.topics is not None:
      source.topics = source_update.topics

    session.add(source)
    await session.commit()
    await session.refresh(source)

    return SourceResponse(
      id=str(source.id),
      title=source.title,
      topics=source.topics or [],
      asset=AssetModel(
        file_path=(source.asset or {}).get('file_path') if source.asset else None,
        url=(source.asset or {}).get('url') if source.asset else None,
      )
      if source.asset
      else None,
      full_text=source.full_text,
      embedded_chunks=source.embedded_chunks,
      created=str(source.created),
      updated=str(source.updated),
    )
  except HTTPException:
    raise
  except Exception as e:
    logger.error(f'Error updating source {source_id}: {e!s}')
    raise HTTPException(status_code=500, detail=f'Error updating source: {e!s}')


@router.delete('/sources/{source_id}')
async def delete_source(source_id: str, session: AsyncSession = Depends(get_session)) -> dict[str, str]:
  """Delete a source."""
  try:
    source = (await session.execute(select(Source).where(Source.id == source_id))).scalar_one_or_none()
    if source is None:
      raise HTTPException(status_code=404, detail='Source not found')

    # Delete insights first
    insights = list(
      (await session.execute(select(SourceInsight).where(SourceInsight.source_id == source.id))).scalars().all()
    )
    for ins in insights:
      await session.delete(ins)
    await session.delete(source)
    await session.commit()

    return {'message': 'Source deleted successfully'}
  except HTTPException:
    raise
  except Exception as e:
    logger.error(f'Error deleting source {source_id}: {e!s}')
    raise HTTPException(status_code=500, detail=f'Error deleting source: {e!s}')


@router.get('/sources/{source_id}/insights', response_model=list[SourceInsightResponse])
async def get_source_insights(
  source_id: str, session: AsyncSession = Depends(get_session)
) -> list[SourceInsightResponse]:
  """Get all insights for a specific source."""
  try:
    source = (await session.execute(select(Source).where(Source.id == source_id))).scalar_one_or_none()
    if source is None:
      raise HTTPException(status_code=404, detail='Source not found')

    insights = list(
      (await session.execute(select(SourceInsight).where(SourceInsight.source_id == source.id))).scalars().all()
    )
    return [
      SourceInsightResponse(
        id=str(insight.id),
        source_id=str(source_id),
        insight_type=insight.insight_type,
        content=insight.content,
        created=str(insight.created),
        updated=str(insight.updated),
      )
      for insight in insights
    ]
  except HTTPException:
    raise
  except Exception as e:
    logger.error(f'Error fetching insights for source {source_id}: {e!s}')
    raise HTTPException(status_code=500, detail=f'Error fetching insights: {e!s}')


@router.post('/sources/{source_id}/insights', response_model=SourceInsightResponse)
async def create_source_insight(
  source_id: str, request: CreateSourceInsightRequest, session: AsyncSession = Depends(get_session)
) -> SourceInsightResponse:
  """Create a new insight for a source by running a transformation."""
  try:
    # Get source
    src = (await session.execute(select(Source).where(Source.id == source_id))).scalar_one_or_none()
    if src is None:
      raise HTTPException(status_code=404, detail='Source not found')

    # Get transformation
    trans = (
      await session.execute(select(Transformation).where(Transformation.id == request.transformation_id))
    ).scalar_one_or_none()
    if trans is None:
      raise HTTPException(status_code=404, detail='Transformation not found')

    # Run transformation graph
    result = await transform_graph.ainvoke(
      input={
        'source': {'full_text': src.full_text or ''},
        'transformation': {
          'name': trans.name,
          'title': trans.title,
          'description': trans.description,
          'prompt': trans.prompt,
        },
      }
    )

    output = result.get('output', '')
    if not output:
      raise HTTPException(status_code=500, detail='Failed to execute transformation')

    insight = SourceInsight(source_id=src.id, insight_type='transformation', content=output)
    session.add(insight)
    await session.commit()
    await session.refresh(insight)

    return SourceInsightResponse(
      id=str(insight.id),
      source_id=str(src.id),
      insight_type=insight.insight_type,
      content=insight.content,
      created=str(insight.created),
      updated=str(insight.updated),
    )

  except HTTPException:
    raise
  except Exception as e:
    logger.error(f'Error creating insight for source {source_id}: {e!s}')
    raise HTTPException(status_code=500, detail=f'Error creating insight: {e!s}')
