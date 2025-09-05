from typing import TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from open_notebook.graphs.utils import provision_langchain_model
from open_notebook.utils import clean_thinking_content


class TransformationState(TypedDict, total=False):
  input_text: str
  source: dict
  transformation: dict
  output: str


async def run_transformation(state: TransformationState, config: RunnableConfig) -> dict[str, str]:
  source = state.get('source')
  content = state.get('input_text')
  assert source or content, 'No content to transform'
  transformation = state['transformation']
  if not content:
    content = (source or {}).get('full_text')
  transformation_template_text = transformation.get('prompt')

  transformation_template_text = f'{transformation_template_text}\n\n# INPUT'
  # Simple prompt rendering without external dependency
  system_prompt = str(transformation_template_text)
  payload = [SystemMessage(content=system_prompt), HumanMessage(content=content)]
  chain = await provision_langchain_model(
    str(payload),
    config.get('configurable', {}).get('model_id'),
    'transformation',
    max_tokens=5055,
  )

  response = await chain.ainvoke(payload)

  # Clean thinking content from the response
  cleaned_content = clean_thinking_content(response.content)

  # Note: Persisting insights is handled by API, not the graph layer

  return {'output': cleaned_content}


class _SimpleGraph:
  async def ainvoke(self, input: TransformationState, config: dict | None = None) -> dict[str, str]:
    return await run_transformation(input, RunnableConfig(config))


graph = _SimpleGraph()
