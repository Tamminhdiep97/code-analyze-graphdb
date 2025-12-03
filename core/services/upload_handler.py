import os
from pathlib import Path
from typing import Optional

from loguru import logger

from config.config import GRAPH_HOST, GRAPH_PORT, GRAPH_USER, GRAPH_PASSWORD, ALLOWED_EXTENSIONS
from core.graph.graph_builder import GraphBuilder


async def process_single_file(
    file_path: str,
    language: str,
    version: Optional[str],
    space_name: str
) -> int:
    """
    Process a single file and store in graph database with UUID space name
    """
    try:
        # Read the file content
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()

        # Initialize GraphBuilder with the specific space
        graph_builder = GraphBuilder(
            graph_host=GRAPH_HOST,
            graph_port=GRAPH_PORT,
            user=GRAPH_USER,
            password=GRAPH_PASSWORD,
            space=space_name
        )

        # Build graph representation from AST
        graph_builder.build_graph_from_ast(
            code=code,
            file_path=file_path,
            language=language,
            version=version
        )

        return 1  # Successfully processed 1 file

    except Exception as e:
        logger.info(f"Error processing single file {file_path}: {str(e)}")
        raise e


async def process_batch_files(
    directory_path: str,
    language: str,
    version: Optional[str],
    space_name: str
) -> int:
    """
    Process multiple files from a directory and store in graph database with UUID space name
    """
    files_processed = 0

    try:
        # Initialize GraphBuilder with the specific space
        graph_builder = GraphBuilder(
            graph_host=GRAPH_HOST,
            graph_port=GRAPH_PORT,
            user=GRAPH_USER,
            password=GRAPH_PASSWORD,
            space=space_name
        )

        # Walk through the directory and process all allowed files
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                # Check if file has allowed extension
                file_ext = Path(file).suffix.lstrip('.').lower()
                if file_ext in ALLOWED_EXTENSIONS:
                    file_path = os.path.join(root, file)

                    try:
                        # Read the file content
                        with open(file_path, 'r', encoding='utf-8') as f:
                            code = f.read()

                        # Build graph representation from AST
                        graph_builder.build_graph_from_ast(
                            code=code,
                            file_path=file_path,
                            language=language,
                            version=version
                        )

                        files_processed += 1

                    except Exception as e:
                        logger.info(f"Error processing file {file_path}: {str(e)}")
                        continue
        return files_processed

    except Exception as e:
        logger.info(f"Error processing batch files in {directory_path}: {str(e)}")
        raise e
