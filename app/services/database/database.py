import asyncpg
from app.core.config import settings
import logging
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
from asyncpg import Record

logger = logging.getLogger(__name__)


class DatabaseService:
    def __init__(self):
        """Initialize database service"""
        self.pool = None

    async def connect(self):
        """Create database connection pool"""
        try:
            if not self.pool:
                logger.info("Creating database connection pool...")
                self.pool = await asyncpg.create_pool(
                    settings.DATABASE_URL,
                    min_size=5,
                    max_size=20
                )
                logger.info("Database connection pool created successfully")
        except Exception as e:
            logger.error(f"Failed to create database pool: {str(e)}")
            raise

    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")

    @asynccontextmanager
    async def connection(self):
        """Get a database connection from the pool"""
        if not self.pool:
            await self.connect()

        async with self.pool.acquire() as conn:
            try:
                yield conn
            except Exception as e:
                logger.error(f"Database operation failed: {str(e)}")
                raise

    async def execute(self, query: str, *args) -> str:
        """Execute a query that doesn't return rows"""
        async with self.connection() as conn:
            return await conn.execute(query, *args)

    def _record_to_dict(self, record: Record) -> Dict[str, Any]:
        """Convert asyncpg record to dictionary"""
        return dict(record)

    async def fetch(self, query: str, *args) -> List[Dict[str, Any]]:
        """Execute a query and return all rows as dictionaries"""
        async with self.connection() as conn:
            records = await conn.fetch(query, *args)
            return [self._record_to_dict(record) for record in records]

    async def fetchrow(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """Execute a query and return one row as dictionary"""
        async with self.connection() as conn:
            record = await conn.fetchrow(query, *args)
            return self._record_to_dict(record) if record else None

    async def fetchval(self, query: str, *args) -> Any:
        """Execute a query and return a single value"""
        async with self.connection() as conn:
            return await conn.fetchval(query, *args)

    # Example methods for common operations
    async def create_table(self, table_name: str, schema: str):
        """Create a table with the given schema"""
        try:
            await self.execute(f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    {schema}
                )
            """)
            logger.info(f"Table {table_name} created or already exists")
        except Exception as e:
            logger.error(f"Failed to create table {table_name}: {str(e)}")
            raise

    async def insert_one(self, table: str, data: Dict[str, Any]) -> str:
        """Insert a single row into a table"""
        columns = list(data.keys())
        values = list(data.values())
        placeholders = [f"${i+1}" for i in range(len(values))]

        query = f"""
            INSERT INTO {table} ({', '.join(columns)})
            VALUES ({', '.join(placeholders)})
            RETURNING id
        """

        return await self.fetchval(query, *values)

    async def update_one(self, table: str, id: int, data: Dict[str, Any]) -> bool:
        """Update a single row in a table"""
        set_values = [f"{k} = ${i+2}" for i, k in enumerate(data.keys())]
        values = list(data.values())

        query = f"""
            UPDATE {table}
            SET {', '.join(set_values)}
            WHERE id = $1
        """

        result = await self.execute(query, id, *values)
        return result == "UPDATE 1"

    async def delete_one(self, table: str, id: int) -> bool:
        """Delete a single row from a table"""
        result = await self.execute(f"DELETE FROM {table} WHERE id = $1", id)
        return result == "DELETE 1"

    async def test_connection(self) -> Dict[str, Any]:
        """Test database connection"""
        try:
            async with self.connection() as conn:
                version = await conn.fetchval('SELECT version()')
                current_time = await conn.fetchval('SELECT NOW()')

                return {
                    "status": "connected",
                    "version": version,
                    "timestamp": str(current_time)
                }
        except Exception as e:
            logger.error(f"Database connection test failed: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }


# Create a global instance
db = DatabaseService()
