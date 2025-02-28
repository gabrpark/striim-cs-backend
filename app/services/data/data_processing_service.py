from app.services.database.database import db
from app.services.llm.llm_service import llm_service
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
        relevant_fields = DataProcessingService.get_relevant_fields(source)

        formatted_data = {}
        for k, v in data.items():
            if k in relevant_fields and v is not None:
                if isinstance(v, datetime):
                    formatted_data[k] = v.isoformat()
                else:
                    formatted_data[k] = str(v)

        text = " ".join(f"{k}: {v}" for k, v in formatted_data.items())
        return text

    def get_id_column_info(self, table_name: str) -> tuple:
        """Get the primary key column name and type for the given table"""
        id_columns = {
            "zendesk_tickets": ("zd_ticket_id", int),
            "salesforce_accounts": ("sf_account_id", str),
            "jira_issues": ("jira_issue_id", str)
        }
        return id_columns[table_name]

    async def process_and_summarize_record(self, table_name: str, record_id: str) -> Dict[str, Any]:
        """Process a record and generate a summary using LLM"""
        try:
            # Get the correct ID column name and type
            id_column, id_type = self.get_id_column_info(table_name)

            # Convert record_id to the correct type
            try:
                converted_id = id_type(record_id)
            except ValueError:
                raise ValueError(
                    f"Invalid record_id format. Expected {id_type.__name__} for {table_name}")

            # Fetch the record from database
            query = f"SELECT * FROM {table_name} WHERE {id_column} = $1"
            record = await db.fetchrow(query, converted_id)

            if not record:
                raise ValueError(
                    f"No record found in {table_name} with {id_column} {record_id}")

            # Format the text with relevant fields
            formatted_text = self.format_text(record, table_name)

            # Generate summary using LLM
            summary = await llm_service.generate_summary(
                text=formatted_text,
                table_name=table_name
            )

            return {
                "status": "success",
                "record_id": record_id,
                "source": table_name,
                "summary": summary,
                "original_data": json.dumps(record, cls=DateTimeEncoder)
            }

        except Exception as e:
            logger.error(f"Error processing record: {str(e)}")
            raise

    async def generate_comprehensive_summary(self, context: Dict[str, Any]) -> str:
        """Generate comprehensive summary of ticket with related data"""
        try:
            # Format context data
            ticket_text = self.format_text(
                context["ticket"], "zendesk_tickets")

            jira_texts = [
                self.format_text(issue, "jira_issues")
                for issue in context["jira_issues"]
            ]

            active_jira_texts = [
                self.format_text(issue, "jira_issues")
                for issue in context["active_jira_issues"]
            ]

            account_text = (
                self.format_text(context["account"], "salesforce_accounts")
                if context["account"] else "No account data available"
            )

            recent_tickets_text = "\n".join([
                self.format_text(ticket, "zendesk_tickets")
                for ticket in context["recent_tickets"]
            ])

            # Combine all context
            full_context = f"""
            Current Ticket Information:
            {ticket_text}

            Directly Related Jira Issues:
            {'\n'.join(jira_texts)}

            Account Information:
            {account_text}

            Recent Support History:
            {recent_tickets_text}

            Active Technical Issues for this Client:
            {'\n'.join(active_jira_texts)}
            """

            # Generate summary using LLM
            return await llm_service.generate_summary(
                text=full_context,
                summary_type="ticket_comprehensive"
            )

        except Exception as e:
            logger.error(f"Error generating comprehensive summary: {str(e)}")
            raise

    async def generate_account_health_summary(self, context: Dict[str, Any]) -> str:
        """Generate account health summary"""
        try:
            # Format context data
            account_text = self.format_text(
                context["account"], "salesforce_accounts")

            recent_tickets_text = "\n".join([
                self.format_text(ticket, "zendesk_tickets")
                for ticket in context["recent_tickets"]
            ])

            active_issues_text = "\n".join([
                self.format_text(issue, "jira_issues")
                for issue in context["active_issues"]
            ])

            # Combine all context
            full_context = f"""
            Account Information:
            {account_text}

            Recent Support Tickets:
            {recent_tickets_text}

            Active Technical Issues:
            {active_issues_text}
            """

            # Generate summary using LLM
            return await llm_service.generate_summary(
                text=full_context,
                summary_type="account_health"
            )

        except Exception as e:
            logger.error(f"Error generating account health summary: {str(e)}")
            raise


data_processing_service = DataProcessingService()
