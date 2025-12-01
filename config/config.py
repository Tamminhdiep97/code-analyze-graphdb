import os

from loguru import logger

GRAPH_HOST: str = os.getenv('GRAPH_HOST', 'graphd')
GRAPH_PORT: int = int(os.getenv('GRAPH_PORT', 9669))

GRAPH_USER: str = os.getenv('GRAPH_USER', 'root')
GRAPH_PASSWORD: str = os.getenv('GRAPH_PASSWORD', '123123')

# File settings
UPLOAD_FOLDER: str = './uploads'
if not os.path.isdir(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Analysis settings
ALLOWED_EXTENSIONS: set = {'c', 'cpp', 'h', 'py'}

## 10MB
MAX_FILE_SIZE: int = 10 * 1024 * 1024
