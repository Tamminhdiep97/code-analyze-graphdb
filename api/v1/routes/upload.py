import os
import zipfile
import tempfile
from typing import Optional, List
from uuid import uuid4
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from loguru import logger

from config.config import UPLOAD_FOLDER, MAX_FILE_SIZE, ALLOWED_EXTENSIONS
from core.services.upload_handler import process_single_file, process_batch_files

router = APIRouter()


def allowed_file(filename: str) -> bool:
    """
    Check if the file extension is allowed
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@router.post("/upload/file")
async def upload_single_file(
    file: UploadFile = File(...),
    language: str = Form("python"),
    version: Optional[str] = Form(None)
):
    """
    Upload and process a single source code file
    """
    # Validate file size
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File size exceeds limit of {MAX_FILE_SIZE} bytes"
        )

    # Validate file extension
    if not allowed_file(file.filename):
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed types: {
                ', '.join(ALLOWED_EXTENSIONS)}"
        )

    try:
        # Create unique space name
        space_name = f"{str(uuid4()).replace('-', '_')}"

        # Save the file
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Process the file through AST and store in graph database
        files_processed = await process_single_file(
            file_path=file_path,
            language=language,
            version=version,
            space_name=space_name
        )

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "space_name": space_name,
                "files_processed": files_processed,
                "message": f"File {file.filename} processed successfully and stored in space {space_name}"
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing file: {str(e)}"
        )


@router.post("/upload/batch")
async def upload_batch_files(
    zip_file: UploadFile = File(...),
    language: str = Form("python"),
    version: Optional[str] = Form(None)
):
    """
    Upload and process multiple files from a ZIP archive
    """
    # Validate file size
    if zip_file.size and zip_file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"ZIP file size exceeds limit of {MAX_FILE_SIZE} bytes"
        )

    # Validate file extension is ZIP
    if not zip_file.filename.lower().endswith('.zip'):
        raise HTTPException(
            status_code=400,
            detail="Only ZIP files are allowed for batch upload"
        )

    try:
        # Create unique space name
        space_name = f"{str(uuid4()).replace('-', '_')}"

        # Create a temporary directory for extraction
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save the ZIP file temporarily
            zip_path = os.path.join(temp_dir, zip_file.filename)
            with open(zip_path, "wb") as f:
                content = await zip_file.read()
                f.write(content)

            # Extract the ZIP file to upload folder under a subdirectory named with UUID
            extract_path = os.path.join(UPLOAD_FOLDER, f"batch_{space_name}")
            os.makedirs(extract_path, exist_ok=True)

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Extract only allowed file types
                for file_info in zip_ref.filelist:
                    if not file_info.is_dir():
                        # Get file extension
                        file_ext = Path(
                            file_info.filename).suffix.lstrip('.').lower()

                        if file_ext in ALLOWED_EXTENSIONS:
                            # Extract the file
                            zip_ref.extract(file_info, extract_path)
                        else:
                            logger.info(f"Skipping file with unsupported extension: {file_info.filename}")

            # Process all extracted files
            files_processed = await process_batch_files(
                directory_path=extract_path,
                language=language,
                version=version,
                space_name=space_name
            )

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "space_name": space_name,
                "files_processed": files_processed,
                "message": f"Batch upload processed successfully and stored in space {space_name}"
            }
        )
    except zipfile.BadZipFile:
        raise HTTPException(
            status_code=400,
            detail="Invalid ZIP file"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing batch upload: {str(e)}"
        )
