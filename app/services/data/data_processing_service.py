from app.services.database.database import db
from app.services.embeddings.embeddings_service import embeddings_service
from app.services.vector_store.pinecone_service import pinecone_service
from typing import Dict, List, Any
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class DataProcessingService:
    @staticmethod
    def get_relevant_fields(table_name: str) -> set:
        """Get relevant fields for each table that contribute to CSM/health scoring"""
        relevant_fields = {
            "zendesk_tickets": {
                "ticket_subject",
                "ticket_type",
                "priority",
                "status",
                "product_component",
                "environment",
                "ticket_description",
                "product_version",
                "node_count"
            },
            "salesforce_accounts": {
                "business_use_case",
                "target_upsell_value",
                "account_record_type",
                "type",
                "is_target_account",
                "is_migration_account",
                "description"
            },
            "jira_issues": {
                "issue_summary",
                "issue_description",
                "issue_type",
                "issue_status",
                "priority",
                "comments"
            }
        }
        return relevant_fields.get(table_name, set())

    @staticmethod
    def format_text(data: Dict[str, Any], source: str) -> str:
        """Format the data fields into a single text string"""
        # Get relevant fields for this table
        relevant_fields = DataProcessingService.get_relevant_fields(source)

        # Remove None values and convert to string, handling datetime objects
        # Only include relevant fields
        formatted_data = {}
        for k, v in data.items():
            if k in relevant_fields and v is not None:
                if isinstance(v, datetime):
                    formatted_data[k] = v.isoformat()
                else:
                    formatted_data[k] = str(v)

        # Create a formatted string with field names
        text = " ".join(f"{k}: {v}" for k, v in formatted_data.items())
        return text

    def get_id_column_info(self, table_name: str) -> tuple:
        """Get the primary key column name and type for the given table"""
        id_columns = {
            "zendesk_tickets": ("zd_ticket_id", int),  # BIGINT -> int
            "salesforce_accounts": ("sf_account_id", str),  # VARCHAR -> str
            "jira_issues": ("jira_issue_id", str)  # VARCHAR -> str
        }
        return id_columns[table_name]

    async def process_and_store_record(self, table_name: str, record_id: str) -> Dict[str, Any]:
        """Process a single record and store its embedding in Pinecone"""
        try:
            # Get the correct ID column name and type
            id_column, id_type = self.get_id_column_info(table_name)

            # Convert record_id to the correct type
            try:
                converted_id = id_type(record_id)
            except ValueError:
                raise ValueError(
                    f"Invalid record_id format. Expected {id_type.__name__} for {table_name}")

            # Fetch the record from database using the correct ID column
            query = f"SELECT * FROM {table_name} WHERE {id_column} = $1"
            record = await db.fetchrow(query, converted_id)

            if not record:
                raise ValueError(
                    f"No record found in {table_name} with {id_column} {record_id}")

            # Format the text
            formatted_text = self.format_text(record, table_name)

            # Generate embedding
            embeddings = await embeddings_service.get_embeddings([formatted_text])

            # Prepare vector for Pinecone
            vector = {
                'id': f"{table_name}_{record_id}",
                'values': embeddings[0],
                'metadata': {
                    'source': table_name,
                    'record_id': record_id,
                    'text': formatted_text,
                    'original_data': json.dumps(record, cls=DateTimeEncoder)
                }
            }

            # Store in Pinecone
            response = await pinecone_service.upsert_vectors(
                vectors=[vector],
                namespace=table_name
            )

            return {
                "status": "success",
                "message": f"Successfully processed and stored record {record_id} from {table_name}",
                "vector_id": vector['id']
            }

        except Exception as e:
            logger.error(f"Error processing record: {str(e)}")
            raise


data_processing_service = DataProcessingService()
