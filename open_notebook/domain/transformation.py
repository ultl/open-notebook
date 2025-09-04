from typing import ClassVar

from pydantic import Field

from open_notebook.domain.base import ObjectModel, RecordModel


class Transformation(ObjectModel):
  table_name: ClassVar[str] = 'transformation'
  name: str
  title: str
  description: str
  prompt: str
  apply_default: bool


class DefaultPrompts(RecordModel):
  record_id: ClassVar[str] = 'open_notebook:default_prompts'
  transformation_instructions: str | None = Field(None, description='Instructions for executing a transformation')
