from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List
from app.services.database.database import db
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/documents/upload")
async def upload_documents(files: List[UploadFile] = File(...)):
    """Upload documents endpoint"""
    try:
        # Use the db instance directly
        async with db.connection() as conn:  # Use the connection context manager
            # Your document upload logic here
            pass

        return {"status": "success", "message": "Documents uploaded successfully"}
    except Exception as e:
        logger.error(f"Error uploading documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Update other routes similarly to use the db instance
