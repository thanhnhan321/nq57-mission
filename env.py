import json
import os
from dotenv import load_dotenv
from urllib.parse import urlparse
import pathlib

load_dotenv()

__ENV = os.getenv('ENV', 'LOCAL').upper()
IS_PRODUCTION = __ENV == "PRODUCTION"
IS_LOCAL = __ENV == "LOCAL"

DB_URL = os.getenv('DB_URL')
if not DB_URL:
    raise EnvironmentError("DB_URL is not configured")
__parsed_db_url = urlparse(DB_URL)
DB_HOST = __parsed_db_url.hostname
DB_PORT = __parsed_db_url.port
DB_USER = __parsed_db_url.username
DB_PASSWORD = __parsed_db_url.password
DB_NAME = __parsed_db_url.path.lstrip('/')

MINIO_CONFIG = os.getenv('MINIO_CONFIG')
if not MINIO_CONFIG:
    raise EnvironmentError("MINIO_URL is not configured")
__parsed_minio_config = json.loads(MINIO_CONFIG)
MINIO_ENDPOINT = __parsed_minio_config['endpoint']
MINIO_ACCESS_KEY = __parsed_minio_config['username']
MINIO_SECRET_KEY = __parsed_minio_config['password']
MINIO_BUCKET = __parsed_minio_config['bucket']

LOG_DIR = os.getenv('LOG_DIR', 'logs')

SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise EnvironmentError("SECRET_KEY is not configured")

HOST_URL = os.getenv('HOST_URL', 'http://localhost:8000')
if not HOST_URL:
    raise EnvironmentError("HOST_URL is not configured")

__exclude_dirs = ['core', 'static', 'staticfiles', 'utils', LOG_DIR ]

# 2. Get the directory where the current script is located
__current_dir = pathlib.Path(__file__).parent.resolve()

def __get_app_dir(base_path: pathlib.Path, ignore_list: list[str]) -> str | None:
    # Iterate through all items in the current directory
    for path in base_path.iterdir():
        # Check if it's a directory AND it's not a hidden directory and its name isn't in your list
        if path.is_dir() and not path.name.startswith('.') and path.name not in ignore_list:
            return path.name
    raise SystemError("No app name found")

# Execute if not hardcoded
APP_DIR = "" or __get_app_dir(__current_dir, __exclude_dirs)
if not APP_DIR:
    raise EnvironmentError("App directory not found")

CONTEXT_ROOT = os.getenv('CONTEXT_ROOT', APP_DIR)

