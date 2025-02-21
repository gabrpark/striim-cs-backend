from pinecone import Pinecone, Index
from app.core.config import settings
from typing import List, Dict, Any, Optional
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class PineconeService:
    def __init__(self):
        """Initialize Pinecone service"""
        self.pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        self.index_name = settings.PINECONE_INDEX_NAME
        self.index: Optional[Index] = None

    def get_index(self, namespace: Optional[str] = None) -> Index:
        """Get or create Pinecone index with optional namespace"""
        if not self.index:
            self.index = self.pc.Index(self.index_name)
        return self.index

    def _validate_vectors(self, vectors: List[Dict]) -> None:
        """Validate vector dimensions before upload"""
        for vector in vectors:
            if len(vector['values']) != 1536:
                raise ValueError(
                    f"Vector dimension mismatch. Expected 1536, "
                    f"got {len(vector['values'])}. Vector ID: {vector['id']}"
                )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def upsert_vectors(
        self,
        vectors: List[Dict[str, Any]],
        namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upsert vectors to Pinecone with optional namespace

        vectors format: [
            {
                'id': 'unique_id',
                'values': [0.1, 0.2, ...],  # 1536 dimensions
                'metadata': {'text': 'original text', 'source': 'source_name', ...}
            },
            ...
        ]
        """
        try:
            index = self.get_index()
            logger.info(
                f"Upserting {len(vectors)} vectors to namespace: {namespace}")
            # Validate vectors before upload
            self._validate_vectors(vectors)

            # Perform upsert
            upsert_response = index.upsert(
                vectors=vectors,
                namespace=namespace
            )

            logger.info(f"Successfully upserted vectors: {upsert_response}")
            return upsert_response
        except Exception as e:
            logger.error(f"Failed to upsert vectors: {str(e)}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def query_vectors(
        self,
        query_vector: List[float],
        top_k: int = 5,
        namespace: Optional[str] = None,
        filter: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Query vectors from Pinecone with optional namespace

        query_vector: List of floats (1536 dimensions)
        top_k: Number of results to return
        filter: Optional metadata filter
        """
        try:
            index = self.get_index()
            logger.info(
                f"Querying vectors with top_k={top_k}, namespace={namespace}")

            # Validate query vector dimension
            if len(query_vector) != 1536:
                raise ValueError(
                    f"Query vector dimension mismatch. Expected 1536, "
                    f"got {len(query_vector)}"
                )

            # Perform query
            query_response = index.query(
                vector=query_vector,
                top_k=top_k,
                namespace=namespace,
                filter=filter,
                include_metadata=True
            )

            # Convert results to serializable format
            matches = []
            for match in query_response['matches']:
                matches.append({
                    'id': match.id,
                    'score': match.score,
                    'metadata': match.metadata
                })

            logger.info(f"Found {len(matches)} matches")
            return {
                "status": "success",
                "matches": matches
            }
        except Exception as e:
            logger.error(f"Failed to query vectors: {str(e)}")
            raise

    async def delete_vectors(
        self,
        ids: List[str],
        namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """Delete vectors from Pinecone with optional namespace"""
        try:
            index = self.get_index()
            logger.info(
                f"Deleting {len(ids)} vectors from namespace: {namespace}")

            delete_response = index.delete(
                ids=ids,
                namespace=namespace
            )

            return {
                "status": "success",
                "deleted_count": len(ids)
            }
        except Exception as e:
            logger.error(f"Failed to delete vectors: {str(e)}")
            raise

    async def test_connection(self):
        """Test the Pinecone connection"""
        try:
            # Try to get index stats
            index = self.get_index()
            stats = index.describe_index_stats()

            return {
                "status": "success",
                "message": "Successfully connected to Pinecone",
                "index_name": self.index_name,
                "stats": stats
            }
        except Exception as e:
            logger.error(f"Failed to test Pinecone connection: {e}")
            raise

    async def list_namespaces(self) -> List[str]:
        """List all available namespaces"""
        try:
            index = self.get_index()
            describe_response = index.describe_index_stats()
            return list(describe_response.namespaces.keys())
        except Exception as e:
            logger.error(f"Error listing namespaces: {str(e)}")
            raise


# Create a global instance
pinecone_service = PineconeService()
