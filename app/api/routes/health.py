from fastapi import APIRouter
from app.services.vector_store.pinecone_service import PineconeService
from langchain_openai import OpenAIEmbeddings
import pinecone
import asyncpg
import os

router = APIRouter()


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
    # Should be async because it makes HTTP requests to Pinecone's API
    try:
        pinecone_service = PineconeService()
        index_stats = pinecone_service.index.describe_index_stats()
        return {
            "status": "connected",
            "index_stats": index_stats
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/test-embeddings")
async def test_embeddings():
    # Must be async because OpenAIEmbeddings.aembed_query is an async operation
    try:
        embeddings = OpenAIEmbeddings()
        test_text = "Hello, testing embeddings"
        vector = await embeddings.aembed_query(test_text)
        return {
            "status": "connected",
            "vector_dimension": len(vector)
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
