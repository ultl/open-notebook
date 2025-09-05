import os
import sys
from pathlib import Path

import uvicorn

current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

if __name__ == '__main__':
  host = os.getenv('API_HOST', '127.0.0.1')
  port = int(os.getenv('API_PORT', '5055'))
  reload = os.getenv('API_RELOAD', 'true').lower() == 'true'

  uvicorn.run(
    'api.main:app',
    host=host,
    port=port,
    reload=reload,
    reload_dirs=[str(current_dir)] if reload else None,
  )
