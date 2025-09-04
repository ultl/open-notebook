from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from loguru import logger
from pydantic import BaseModel, Field
from surreal_commands import registry

from api.command_service import CommandService

router = APIRouter()


class CommandExecutionRequest(BaseModel):
  command: str = Field(..., description="Command function name (e.g., 'process_text')")
  app: str = Field(..., description="Application name (e.g., 'open_notebook')")
  input: dict[str, Any] = Field(..., description='Arguments to pass to the command')


class CommandJobResponse(BaseModel):
  job_id: str
  status: str
  message: str


class CommandJobStatusResponse(BaseModel):
  job_id: str
  status: str
  result: dict[str, Any] | None = None
  error_message: str | None = None
  created: str | None = None
  updated: str | None = None
  progress: dict[str, Any] | None = None


@router.post('/commands/jobs', response_model=CommandJobResponse)
async def execute_command(request: CommandExecutionRequest):
  """Submit a command for background processing.
  Returns immediately with job ID for status tracking.

  Example request:
  {
      "command": "process_text",
      "app": "open_notebook",
      "input": {
          "text": "Hello world",
          "operation": "uppercase"
      }
  }
  """
  try:
    # Submit command using app name (not module name)
    job_id = await CommandService.submit_command_job(
      module_name=request.app,  # This should be "open_notebook"
      command_name=request.command,
      command_args=request.input,
    )

    return CommandJobResponse(
      job_id=job_id,
      status='submitted',
      message=f"Command '{request.command}' submitted successfully",
    )

  except Exception as e:
    logger.error(f'Error submitting command: {e!s}')
    raise HTTPException(status_code=500, detail=f'Failed to submit command: {e!s}')


@router.get('/commands/jobs/{job_id}', response_model=CommandJobStatusResponse)
async def get_command_job_status(job_id: str):
  """Get the status of a specific command job."""
  try:
    status_data = await CommandService.get_command_status(job_id)
    return CommandJobStatusResponse(**status_data)

  except Exception as e:
    logger.error(f'Error fetching job status: {e!s}')
    raise HTTPException(status_code=500, detail=f'Failed to fetch job status: {e!s}')


@router.get('/commands/jobs', response_model=list[dict[str, Any]])
async def list_command_jobs(
  command_filter: Annotated[str | None, Query(description='Filter by command name')] = None,
  status_filter: Annotated[str | None, Query(description='Filter by status')] = None,
  limit: Annotated[int, Query(description='Maximum number of jobs to return')] = 50,
):
  """List command jobs with optional filtering."""
  try:
    return await CommandService.list_command_jobs(
      command_filter=command_filter, status_filter=status_filter, limit=limit
    )

  except Exception as e:
    logger.error(f'Error listing command jobs: {e!s}')
    raise HTTPException(status_code=500, detail=f'Failed to list command jobs: {e!s}')


@router.delete('/commands/jobs/{job_id}')
async def cancel_command_job(job_id: str):
  """Cancel a running command job."""
  try:
    success = await CommandService.cancel_command_job(job_id)
    return {'job_id': job_id, 'cancelled': success}

  except Exception as e:
    logger.error(f'Error cancelling command job: {e!s}')
    raise HTTPException(status_code=500, detail=f'Failed to cancel command job: {e!s}')


@router.get('/commands/registry/debug')
async def debug_registry():
  """Debug endpoint to see what commands are registered."""
  try:
    # Get all registered commands
    all_items = registry.get_all_commands()

    # Create JSON-serializable data
    command_items = []
    for item in all_items:
      try:
        command_items.append({
          'app_id': item.app_id,
          'name': item.name,
          'full_id': f'{item.app_id}.{item.name}',
        })
      except Exception as item_error:
        logger.error(f'Error processing item: {item_error}')

    # Get the basic command structure
    try:
      commands_dict = {}
      for item in all_items:
        if item.app_id not in commands_dict:
          commands_dict[item.app_id] = []
        commands_dict[item.app_id].append(item.name)
    except Exception:
      commands_dict = {}

    return {
      'total_commands': len(all_items),
      'commands_by_app': commands_dict,
      'command_items': command_items,
    }

  except Exception as e:
    logger.error(f'Error debugging registry: {e!s}')
    return {
      'error': str(e),
      'total_commands': 0,
      'commands_by_app': {},
      'command_items': [],
    }
