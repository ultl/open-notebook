from __future__ import annotations

from datetime import UTC, datetime
from os import getenv
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


def now_utc() -> datetime:
  return datetime.now(UTC)


class Timestamped(SQLModel):
  created: datetime = Field(default_factory=now_utc, nullable=False)
  updated: datetime = Field(default_factory=now_utc, nullable=False)


class Notebook(Timestamped, SQLModel, table=True):
  __tablename__ = 'notebooks'

  id: UUID = Field(default_factory=uuid4, primary_key=True, nullable=False)
  name: str = Field(min_length=1)
  description: str = Field(default='')
  archived: bool = Field(default=False, nullable=False)


class Note(Timestamped, SQLModel, table=True):
  __tablename__ = 'notes'

  id: UUID = Field(default_factory=uuid4, primary_key=True, nullable=False)
  title: str | None = None
  content: str | None = None
  note_type: str | None = Field(default='human')
  notebook_id: UUID | None = Field(default=None, foreign_key='notebooks.id')


class AIModel(Timestamped, SQLModel, table=True):
  __tablename__ = 'ai_models'

  id: UUID = Field(default_factory=uuid4, primary_key=True, nullable=False)
  name: str
  provider: str
  type: str  # language | embedding | text_to_speech | speech_to_text | tools


class DefaultModels(SQLModel, table=True):
  __tablename__ = 'default_models'

  id: int = Field(default=1, primary_key=True)
  default_chat_model: UUID | None = None
  default_transformation_model: UUID | None = None
  large_context_model: UUID | None = None
  default_text_to_speech_model: UUID | None = None
  default_speech_to_text_model: UUID | None = None
  default_embedding_model: UUID | None = None
  default_tools_model: UUID | None = None


class Transformation(Timestamped, SQLModel, table=True):
  __tablename__ = 'transformations'

  id: UUID = Field(default_factory=uuid4, primary_key=True, nullable=False)
  name: str
  title: str
  description: str
  prompt: str
  apply_default: bool = Field(default=False)


class ContentSettings(SQLModel, table=True):
  __tablename__ = 'content_settings'

  id: int = Field(default=1, primary_key=True)
  default_content_processing_engine_doc: str | None = None
  default_content_processing_engine_url: str | None = None
  default_embedding_option: str | None = None
  auto_delete_files: str | None = None  # yes | no
  youtube_preferred_languages: list[str] | None = Field(default=None, sa_column=Column(JSONB))


class Source(Timestamped, SQLModel, table=True):
  __tablename__ = 'sources'

  id: UUID = Field(default_factory=uuid4, primary_key=True, nullable=False)
  notebook_id: UUID = Field(foreign_key='notebooks.id')
  type: str  # link | upload | text
  url: str | None = None
  file_path: str | None = None
  content: str | None = None
  title: str | None = None
  topics: list[str] | None = Field(default=None, sa_column=Column(JSONB))
  asset: dict | None = Field(default=None, sa_column=Column(JSONB))
  full_text: str | None = None
  embedded_chunks: int = Field(default=0, nullable=False)


class SourceInsight(Timestamped, SQLModel, table=True):
  __tablename__ = 'source_insights'

  id: UUID = Field(default_factory=uuid4, primary_key=True, nullable=False)
  source_id: UUID = Field(foreign_key='sources.id')
  insight_type: str = Field(default='transformation')
  content: str


# Embedding vector dimension (default 384 for all-MiniLM-L6-v2)
EMBED_DIM: int = int(getenv('EMBED_DIM', '384'))


class SourceChunk(SQLModel, table=True):
  __tablename__ = 'source_chunks'

  id: UUID = Field(default_factory=uuid4, primary_key=True, nullable=False)
  source_id: UUID = Field(foreign_key='sources.id')
  content: str
  embedding: list[float] = Field(sa_column=Column(Vector(EMBED_DIM), nullable=False))


class NoteChunk(SQLModel, table=True):
  __tablename__ = 'note_chunks'

  id: UUID = Field(default_factory=uuid4, primary_key=True, nullable=False)
  note_id: UUID = Field(foreign_key='notes.id')
  content: str
  embedding: list[float] = Field(sa_column=Column(Vector(EMBED_DIM), nullable=False))


# Optional vector indexes (require pgvector extension)
Index(
  'ix_source_chunks_embedding_ivfflat',
  SourceChunk.__table__.c.embedding,
  postgresql_using='ivfflat',
  postgresql_with={'lists': 100},
  postgresql_ops={'embedding': 'vector_cosine_ops'},
)
Index(
  'ix_note_chunks_embedding_ivfflat',
  NoteChunk.__table__.c.embedding,
  postgresql_using='ivfflat',
  postgresql_with={'lists': 100},
  postgresql_ops={'embedding': 'vector_cosine_ops'},
)


# Podcasts (minimal SQLModel reimplementation)
class EpisodeProfile(Timestamped, SQLModel, table=True):
  __tablename__ = 'episode_profiles'

  id: UUID = Field(default_factory=uuid4, primary_key=True, nullable=False)
  name: str
  description: str | None = None
  speaker_config: str
  outline_provider: str
  outline_model: str
  transcript_provider: str
  transcript_model: str
  default_briefing: str
  num_segments: int = Field(default=5)


class SpeakerProfile(Timestamped, SQLModel, table=True):
  __tablename__ = 'speaker_profiles'

  id: UUID = Field(default_factory=uuid4, primary_key=True, nullable=False)
  name: str
  description: str | None = None
  tts_provider: str
  tts_model: str
  speakers: list[dict] = Field(sa_column=Column(JSONB))


class PodcastEpisode(Timestamped, SQLModel, table=True):
  __tablename__ = 'podcast_episodes'

  id: UUID = Field(default_factory=uuid4, primary_key=True, nullable=False)
  name: str
  episode_profile: dict = Field(sa_column=Column(JSONB))
  speaker_profile: dict = Field(sa_column=Column(JSONB))
  briefing: str
  content: str
  audio_file: str | None = None
  transcript: dict | None = Field(default=None, sa_column=Column(JSONB))
  outline: dict | None = Field(default=None, sa_column=Column(JSONB))
  job_status: str | None = None
