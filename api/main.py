from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.auth import PasswordAuthMiddleware
from api.routers import (
  context,
  embedding,
  episode_profiles,
  insights,
  models,
  notebooks,
  notes,
  podcasts,
  search,
  settings,
  sources,
  speaker_profiles,
  transformations,
)
from open_notebook.database.seed import seed_defaults
from open_notebook.database.sql import SessionLocal, init_db
from open_notebook.logging import configure_logging
from open_notebook.services.podcast_worker import start_worker, stop_worker

configure_logging()

app = FastAPI(
  title='Open Notebook API',
  description='API for Open Notebook - Research Assistant',
  version='0.2.2',
)

# Add CORS middleware
app.add_middleware(
  CORSMiddleware,
  allow_origins=['*'],  # In production, replace with specific origins
  allow_credentials=True,
  allow_methods=['*'],
  allow_headers=['*'],
)

# Add password authentication middleware
app.add_middleware(PasswordAuthMiddleware)

# Include routers
app.include_router(notebooks.router, prefix='/api', tags=['notebooks'])
app.include_router(search.router, prefix='/api', tags=['search'])
app.include_router(models.router, prefix='/api', tags=['models'])
app.include_router(transformations.router, prefix='/api', tags=['transformations'])
app.include_router(notes.router, prefix='/api', tags=['notes'])
app.include_router(embedding.router, prefix='/api', tags=['embedding'])
app.include_router(settings.router, prefix='/api', tags=['settings'])
app.include_router(context.router, prefix='/api', tags=['context'])
app.include_router(sources.router, prefix='/api', tags=['sources'])
app.include_router(insights.router, prefix='/api', tags=['insights'])
app.include_router(podcasts.router, prefix='/api', tags=['podcasts'])
app.include_router(episode_profiles.router, prefix='/api', tags=['episode-profiles'])
app.include_router(speaker_profiles.router, prefix='/api', tags=['speaker-profiles'])


@app.get('/')
async def root() -> dict[str, str]:
  return {'message': 'Open Notebook API is running'}


@app.get('/health')
async def health() -> dict[str, str]:
  return {'status': 'healthy'}


@app.on_event('startup')
async def on_startup() -> None:
  # Initialize database schema at startup (idempotent)
  await init_db()
  # Seed default rows and example profiles
  async with SessionLocal() as session:
    await seed_defaults(session)
  # Start podcast worker
  start_worker()


@app.on_event('shutdown')
async def on_shutdown() -> None:
  stop_worker()
