import asyncio
from itertools import starmap
from typing import Any, ClassVar, Literal

from loguru import logger
from pydantic import BaseModel, Field, field_validator

from open_notebook.database.repository import ensure_record_id, repo_query
from open_notebook.domain.base import ObjectModel
from open_notebook.domain.models import model_manager
from open_notebook.exceptions import DatabaseOperationError, InvalidInputError
from open_notebook.utils import split_text


class Notebook(ObjectModel):
  table_name: ClassVar[str] = 'notebook'
  name: str
  description: str
  archived: bool | None = False

  @field_validator('name')
  @classmethod
  def name_must_not_be_empty(cls, v):
    if not v.strip():
      msg = 'Notebook name cannot be empty'
      raise InvalidInputError(msg)
    return v

  async def get_sources(self) -> list['Source']:
    try:
      srcs = await repo_query(
        """
                select * omit source.full_text from (
                select in as source from reference where out=$id
                fetch source
            ) order by source.updated desc
            """,
        {'id': ensure_record_id(self.id)},
      )
      return [Source(**src['source']) for src in srcs] if srcs else []
    except Exception as e:
      logger.error(f'Error fetching sources for notebook {self.id}: {e!s}')
      logger.exception(e)
      raise DatabaseOperationError(e)

  async def get_notes(self) -> list['Note']:
    try:
      srcs = await repo_query(
        """
            select * omit note.content, note.embedding from (
                select in as note from artifact where out=$id
                fetch note
            ) order by note.updated desc
            """,
        {'id': ensure_record_id(self.id)},
      )
      return [Note(**src['note']) for src in srcs] if srcs else []
    except Exception as e:
      logger.error(f'Error fetching notes for notebook {self.id}: {e!s}')
      logger.exception(e)
      raise DatabaseOperationError(e)

  async def get_chat_sessions(self) -> list['ChatSession']:
    try:
      srcs = await repo_query(
        """
                select * from (
                    select
                    <- chat_session as chat_session
                    from refers_to
                    where out=$id
                    fetch chat_session
                )
                order by chat_session.updated desc
            """,
        {'id': ensure_record_id(self.id)},
      )
      return [ChatSession(**src['chat_session'][0]) for src in srcs] if srcs else []
    except Exception as e:
      logger.error(f'Error fetching chat sessions for notebook {self.id}: {e!s}')
      logger.exception(e)
      raise DatabaseOperationError(e)


class Asset(BaseModel):
  file_path: str | None = None
  url: str | None = None


class SourceEmbedding(ObjectModel):
  table_name: ClassVar[str] = 'source_embedding'
  content: str

  async def get_source(self) -> 'Source':
    try:
      src = await repo_query(
        """
            select source.* from $id fetch source
            """,
        {'id': ensure_record_id(self.id)},
      )
      return Source(**src[0]['source'])
    except Exception as e:
      logger.error(f'Error fetching source for embedding {self.id}: {e!s}')
      logger.exception(e)
      raise DatabaseOperationError(e)


class SourceInsight(ObjectModel):
  table_name: ClassVar[str] = 'source_insight'
  insight_type: str
  content: str

  async def get_source(self) -> 'Source':
    try:
      src = await repo_query(
        """
            select source.* from $id fetch source
            """,
        {'id': ensure_record_id(self.id)},
      )
      return Source(**src[0]['source'])
    except Exception as e:
      logger.error(f'Error fetching source for insight {self.id}: {e!s}')
      logger.exception(e)
      raise DatabaseOperationError(e)

  async def save_as_note(self, notebook_id: str | None = None) -> Any:
    source = await self.get_source()
    note = Note(
      title=f'{self.insight_type} from source {source.title}',
      content=self.content,
    )
    await note.save()
    if notebook_id:
      await note.add_to_notebook(notebook_id)
    return note


class Source(ObjectModel):
  table_name: ClassVar[str] = 'source'
  asset: Asset | None = None
  title: str | None = None
  topics: list[str] | None = Field(default_factory=list)
  full_text: str | None = None

  async def get_context(self, context_size: Literal['short', 'long'] = 'short') -> dict[str, Any]:
    insights_list = await self.get_insights()
    insights = [insight.model_dump() for insight in insights_list]
    if context_size == 'long':
      return {
        'id': self.id,
        'title': self.title,
        'insights': insights,
        'full_text': self.full_text,
      }
    return {'id': self.id, 'title': self.title, 'insights': insights}

  async def get_embedded_chunks(self) -> int:
    try:
      result = await repo_query(
        """
                select count() as chunks from source_embedding where source=$id GROUP ALL
                """,
        {'id': ensure_record_id(self.id)},
      )
      if len(result) == 0:
        return 0
      return result[0]['chunks']
    except Exception as e:
      logger.error(f'Error fetching chunks count for source {self.id}: {e!s}')
      logger.exception(e)
      msg = f'Failed to count chunks for source: {e!s}'
      raise DatabaseOperationError(msg)

  async def get_insights(self) -> list[SourceInsight]:
    try:
      result = await repo_query(
        """
                SELECT * FROM source_insight WHERE source=$id
                """,
        {'id': ensure_record_id(self.id)},
      )
      return [SourceInsight(**insight) for insight in result]
    except Exception as e:
      logger.error(f'Error fetching insights for source {self.id}: {e!s}')
      logger.exception(e)
      msg = 'Failed to fetch insights for source'
      raise DatabaseOperationError(msg)

  async def add_to_notebook(self, notebook_id: str) -> Any:
    if not notebook_id:
      msg = 'Notebook ID must be provided'
      raise InvalidInputError(msg)
    return await self.relate('reference', notebook_id)

  async def vectorize(self) -> None:
    logger.info(f'Starting vectorization for source {self.id}')
    EMBEDDING_MODEL = await model_manager.get_embedding_model()

    try:
      if not self.full_text:
        logger.warning(f'No text to vectorize for source {self.id}')
        return

      chunks = split_text(
        self.full_text,
      )
      chunk_count = len(chunks)
      logger.info(f'Split into {chunk_count} chunks for source {self.id}')

      if chunk_count == 0:
        logger.warning('No chunks created after splitting')
        return

      # Process chunks concurrently using async gather
      logger.info('Starting concurrent processing of chunks')

      async def process_chunk(idx: int, chunk: str) -> tuple[int, list[float], str]:
        logger.debug(f'Processing chunk {idx}/{chunk_count}')
        try:
          embedding = (await EMBEDDING_MODEL.aembed([chunk]))[0]
          cleaned_content = chunk
          logger.debug(f'Successfully processed chunk {idx}')
          return (idx, embedding, cleaned_content)
        except Exception as e:
          logger.error(f'Error processing chunk {idx}: {e!s}')
          raise

      # Create tasks for all chunks and process them concurrently
      tasks = list(starmap(process_chunk, enumerate(chunks)))
      results = await asyncio.gather(*tasks)

      logger.info(f'Parallel processing complete. Got {len(results)} results')

      # Insert results in order (they're already ordered by index)
      for idx, embedding, content in results:
        logger.debug(f'Inserting chunk {idx} into database')
        await repo_query(
          """
                    CREATE source_embedding CONTENT {
                            "source": $source_id,
                            "order": $order,
                            "content": $content,
                            "embedding": $embedding,
                    };""",
          {
            'source_id': ensure_record_id(self.id),
            'order': idx,
            'content': content,
            'embedding': embedding,
          },
        )

      logger.info(f'Vectorization complete for source {self.id}')

    except Exception as e:
      logger.error(f'Error vectorizing source {self.id}: {e!s}')
      logger.exception(e)
      raise DatabaseOperationError(e)

  async def add_insight(self, insight_type: str, content: str) -> Any:
    EMBEDDING_MODEL = await model_manager.get_embedding_model()
    if not EMBEDDING_MODEL:
      logger.warning('No embedding model found. Insight will not be searchable.')

    if not insight_type or not content:
      msg = 'Insight type and content must be provided'
      raise InvalidInputError(msg)
    try:
      embedding = (await EMBEDDING_MODEL.aembed([content]))[0] if EMBEDDING_MODEL else []
      return await repo_query(
        """
                CREATE source_insight CONTENT {
                        "source": $source_id,
                        "insight_type": $insight_type,
                        "content": $content,
                        "embedding": $embedding,
                };""",
        {
          'source_id': ensure_record_id(self.id),
          'insight_type': insight_type,
          'content': content,
          'embedding': embedding,
        },
      )
    except Exception as e:
      logger.error(f'Error adding insight to source {self.id}: {e!s}')
      raise  # DatabaseOperationError(e)


class Note(ObjectModel):
  table_name: ClassVar[str] = 'note'
  title: str | None = None
  note_type: Literal['human', 'ai'] | None = None
  content: str | None = None

  @field_validator('content')
  @classmethod
  def content_must_not_be_empty(cls, v):
    if v is not None and not v.strip():
      msg = 'Note content cannot be empty'
      raise InvalidInputError(msg)
    return v

  async def add_to_notebook(self, notebook_id: str) -> Any:
    if not notebook_id:
      msg = 'Notebook ID must be provided'
      raise InvalidInputError(msg)
    return await self.relate('artifact', notebook_id)

  def get_context(self, context_size: Literal['short', 'long'] = 'short') -> dict[str, Any]:
    if context_size == 'long':
      return {'id': self.id, 'title': self.title, 'content': self.content}
    return {
      'id': self.id,
      'title': self.title,
      'content': self.content[:100] if self.content else None,
    }

  def needs_embedding(self) -> bool:
    return True

  def get_embedding_content(self) -> str | None:
    return self.content


class ChatSession(ObjectModel):
  table_name: ClassVar[str] = 'chat_session'
  title: str | None = None

  async def relate_to_notebook(self, notebook_id: str) -> Any:
    if not notebook_id:
      msg = 'Notebook ID must be provided'
      raise InvalidInputError(msg)
    return await self.relate('refers_to', notebook_id)


async def text_search(keyword: str, results: int, source: bool = True, note: bool = True):
  if not keyword:
    msg = 'Search keyword cannot be empty'
    raise InvalidInputError(msg)
  try:
    return await repo_query(
      """
            select *
            from fn::text_search($keyword, $results, $source, $note)
            """,
      {'keyword': keyword, 'results': results, 'source': source, 'note': note},
    )
  except Exception as e:
    logger.error(f'Error performing text search: {e!s}')
    logger.exception(e)
    raise DatabaseOperationError(e)


async def vector_search(
  keyword: str,
  results: int,
  source: bool = True,
  note: bool = True,
  minimum_score=0.2,
):
  if not keyword:
    msg = 'Search keyword cannot be empty'
    raise InvalidInputError(msg)
  try:
    EMBEDDING_MODEL = await model_manager.get_embedding_model()
    embed = (await EMBEDDING_MODEL.aembed([keyword]))[0]
    return await repo_query(
      """
            SELECT * FROM fn::vector_search($embed, $results, $source, $note, $minimum_score);
            """,
      {
        'embed': embed,
        'results': results,
        'source': source,
        'note': note,
        'minimum_score': minimum_score,
      },
    )
  except Exception as e:
    logger.error(f'Error performing vector search: {e!s}')
    logger.exception(e)
    raise DatabaseOperationError(e)
