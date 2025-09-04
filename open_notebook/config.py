import pathlib

# ROOT DATA FOLDER
DATA_FOLDER = "./data"

# LANGGRAPH CHECKPOINT FILE
sqlite_folder = f"{DATA_FOLDER}/sqlite-db"
pathlib.Path(sqlite_folder).mkdir(exist_ok=True, parents=True)
LANGGRAPH_CHECKPOINT_FILE = f"{sqlite_folder}/checkpoints.sqlite"

# UPLOADS FOLDER
UPLOADS_FOLDER = f"{DATA_FOLDER}/uploads"
pathlib.Path(UPLOADS_FOLDER).mkdir(exist_ok=True, parents=True)
