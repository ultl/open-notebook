from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from loguru import logger
from sentence_transformers import SentenceTransformer
from sqlalchemy import func, select

from open_notebook.database.models import Note, NoteChunk, Source, SourceChunk
from open_notebook.domain.models import model_manager
from open_notebook.utils import split_text

if TYPE_CHECKING:
  from sqlalchemy.ext.asyncio import AsyncSession


@runtime_checkable
class EmbeddingModelProtocol(Protocol):
  async def aembed(self, texts: list[str]) -> list[list[float]]: ...


class _LocalEmbedder:
  _model: SentenceTransformer | None = None

  async def aembed(self, texts: list[str]) -> list[list[float]]:  # type: ignore[override]
    if self._model is None:
      self._model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    vecs = self._model.encode(texts, normalize_embeddings=True)
    return [v.tolist() for v in vecs]


async def _get_embedding_model() -> EmbeddingModelProtocol:
  model = await model_manager.get_embedding_model()
  if model:
    # Basic runtime check – model should implement aembed
    assert isinstance(model, EmbeddingModelProtocol) or hasattr(model, 'aembed')
    return model
  logger.warning('Using local sentence-transformers fallback for embeddings')
  return _LocalEmbedder()


async def embed_texts(chunks: list[str]) -> list[list[float]]:
  if not chunks:
    return []
  EMB = await _get_embedding_model()
  vectors = await EMB.aembed(chunks)
  return [list(map(float, v)) for v in vectors]


async def embed_source(session: AsyncSession, source: Source, chunk_size: int = 800) -> int:
  text = source.full_text or source.content or ''
  if not text:
    return 0

  parts = split_text(text, chunk_size=chunk_size)
  vectors = await embed_texts(parts)
  to_add = [SourceChunk(source_id=source.id, content=parts[i], embedding=vectors[i]) for i in range(len(parts))]
  session.add_all(to_add)
  await session.flush()
  source.embedded_chunks = (source.embedded_chunks or 0) + len(to_add)
  session.add(source)
  await session.commit()
  return len(to_add)


async def embed_note(session: AsyncSession, note: Note, chunk_size: int = 800) -> int:
  text = note.content or ''
  if not text:
    return 0
  parts = split_text(text, chunk_size=chunk_size)
  vectors = await embed_texts(parts)
  to_add = [NoteChunk(note_id=note.id, content=parts[i], embedding=vectors[i]) for i in range(len(parts))]
  session.add_all(to_add)
  await session.flush()
  await session.commit()
  return len(to_add)


async def vector_search(
  session: AsyncSession,
  keyword: str,
  results: int = 50,
  source: bool = True,
  note: bool = True,
  minimum_score: float = 0.2,
) -> list[dict]:
  """Search across embedded chunks using cosine similarity.

  Returns list of dicts with keys: type, title, parent_id, similarity, matches.
  """
  # Embed query
  vec = (await embed_texts([keyword]))[0]

  found: list[dict] = []
  threshold = 1.0 - float(minimum_score)

  if source:
    dist = func.cosine_distance(SourceChunk.embedding, vec)
    stmt = (
      select(SourceChunk, Source, dist.label('distance'))
      .join(Source, Source.id == SourceChunk.source_id)
      .order_by(dist)
      .limit(results)
    )
    for row in (await session.execute(stmt)).all():
      chunk, parent, distance = row
      if distance is not None and float(distance) <= threshold:
        found.append({
          'type': 'source',
          'title': parent.title or 'Untitled Source',
          'parent_id': str(parent.id),
          'similarity': 1.0 - float(distance),
          'matches': [chunk.content[:300]],
        })

  if note:
    dist = func.cosine_distance(NoteChunk.embedding, vec)
    stmt = (
      select(NoteChunk, Note, dist.label('distance'))
      .join(Note, Note.id == NoteChunk.note_id)
      .order_by(dist)
      .limit(results)
    )
    for row in (await session.execute(stmt)).all():
      chunk, parent, distance = row
      if distance is not None and float(distance) <= threshold:
        found.append({
          'type': 'note',
          'title': parent.title or 'Untitled Note',
          'parent_id': str(parent.id),
          'similarity': 1.0 - float(distance),
          'matches': [chunk.content[:300]],
        })

  return found[: results or 50]
