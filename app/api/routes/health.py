from fastapi import APIRouter, HTTPException
from app.services.vector_store.pinecone_service import PineconeService
from langchain_openai import OpenAIEmbeddings
import pinecone
import asyncpg
import os
import logging
import traceback
from typing import Dict, Any
from fastapi.responses import JSONResponse
from pinecone import Pinecone
from app.core.config import settings

router = APIRouter()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@router.get("/health")
def health_check():
    # Simple response, no I/O operations
    return {"status": "healthy"}


@router.get("/test-database")
async def test_database():
    # Must be async because asyncpg uses async/await for database operations
    try:
        # Get the connection string from the environment variable
        connection_string = os.getenv('DATABASE_URL')

        # Clean the connection string
        if connection_string:
            # Remove any comments (everything after #)
            connection_string = connection_string.split('#')[0]

            # Remove any quotes and whitespace
            connection_string = connection_string.strip().strip('"').strip("'")

        print(f"Connection string: {connection_string}")

        if not connection_string:
            raise ValueError("DATABASE_URL environment variable is not set")

        # Create a connection pool
        pool = await asyncpg.create_pool(connection_string)

        # Acquire a connection from the pool
        async with pool.acquire() as conn:
            # Execute SQL commands to retrieve the current time and version from PostgreSQL
            time = await conn.fetchval('SELECT NOW();')
            version = await conn.fetchval('SELECT version();')

        # Close the pool
        await pool.close()

        return {
            "status": "connected",
            "time": str(time),
            "version": version,
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "type": type(e).__name__
        }


@router.get("/test-pinecone")
async def test_pinecone():
    try:
        # Initialize Pinecone directly
        pc = Pinecone(api_key=settings.PINECONE_API_KEY)

        # Get the index
        index = pc.Index(settings.PINECONE_INDEX_NAME)

        # Get stats to test connection
        stats = index.describe_index_stats()

        # Convert namespaces to dict first
        namespaces_dict = {}
        for ns_name, ns_data in stats.namespaces.items():
            namespaces_dict[ns_name] = {
                "vector_count": ns_data.vector_count
            }

        # Convert stats to dict before returning
        stats_dict = {
            "namespaces": namespaces_dict,
            "dimension": stats.dimension,
            "index_fullness": stats.index_fullness,
            "total_vector_count": stats.total_vector_count
        }

        return JSONResponse(content={
            "status": "success",
            "message": "Successfully connected to Pinecone",
            "index_name": settings.PINECONE_INDEX_NAME,
            "stats": stats_dict
        })
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": str(e),
                "error_type": type(e).__name__
            }
        )
