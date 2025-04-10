from typing import Dict, List, Any, Optional
from datetime import datetime
from app.services.database.database import db
from app.services.llm.llm_service import llm_service
import logging
import json

logger = logging.getLogger(__name__)


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class HierarchicalSummaryService:
    """Service to handle hierarchical summaries with caching"""

    SUMMARY_TYPES = {
        'individual': {
            'zendesk_ticket': {'ttl_hours': 24},
            'jira_issue': {'ttl_hours': 24},
            'salesforce_account': {'ttl_hours': 48}
        },
        'group': {
            'all_tickets': {'ttl_hours': 24, 'depends_on': ['zendesk_ticket']},
            'all_issues': {'ttl_hours': 24, 'depends_on': ['jira_issue']},
            'all_accounts': {'ttl_hours': 48, 'depends_on': ['salesforce_account']}
        },
        'global': {
            'system_wide': {
                'ttl_hours': 48,
                'depends_on': ['all_tickets', 'all_issues', 'all_accounts']
            }
        }
    }

    async def get_or_generate_summary(
        self,
        summary_type: str,
        params: Dict[str, Any],
        force_regenerate: bool = False
    ) -> Dict[str, Any]:
        """Get cached summary or generate new one"""
        try:
            if not force_regenerate:
                # Try to get a valid cached summary
                cached = await self._get_valid_cached_summary(summary_type, params)
                if cached:
                    logger.info(f"Using cached summary for {summary_type}")
                    return cached

            # Generate new summary if needed
            logger.info(f"Generating new summary for {summary_type}")
            return await self._generate_summary(summary_type, params)

        except Exception as e:
            logger.error(f"Error in get_or_generate_summary: {str(e)}")
            raise

    async def _get_valid_cached_summary(
        self,
        summary_type: str,
        params: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Get a valid cached summary if it exists"""
        try:
            # Simple query to get the most recent valid summary
            query = """
                SELECT s.*
                FROM summaries s
                WHERE s.summary_type = $1
                AND s.is_valid = true
                AND (
                    (s.date_range_start IS NULL AND $2::timestamp IS NULL) OR
                    (s.date_range_start = $2::timestamp)
                )
                AND (
                    (s.date_range_end IS NULL AND $3::timestamp IS NULL) OR
                    (s.date_range_end = $3::timestamp)
                )
                ORDER BY s.last_generated_at DESC
                LIMIT 1
            """

            summary = await db.fetchrow(
                query,
                summary_type,
                params.get('date_range_start'),
                params.get('date_range_end')
            )

            if summary:
                logger.info(f"Using cached summary for {summary_type}")
                return dict(summary)

            logger.info(f"No valid cached summary found for {summary_type}")
            return None

        except Exception as e:
            logger.error(f"Error getting valid cached summary: {str(e)}")
            return None

    async def _generate_summary(
        self,
        summary_type: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate new summary based on type"""
        try:
            # Get source data based on summary type
            source_data = await self._get_source_data(summary_type, params)

            # Generate appropriate prompt based on summary type
            prompt = self._get_summary_prompt(summary_type)

            # Generate summary using LLM with DateTimeEncoder
            summary_text = await llm_service.generate_summary(
                text=json.dumps(source_data, cls=DateTimeEncoder),
                summary_type=summary_type
            )

            # Ensure proper markdown formatting
            if summary_type == 'all_tickets':
                # Format the summary with proper markdown
                formatted_summary = self._format_ticket_summary_markdown(
                    summary_text, source_data)
            else:
                formatted_summary = summary_text

            # Store summary and relationships
            stored_summary = await self._store_summary(
                summary_type=summary_type,
                summary_text=formatted_summary,
                source_data=source_data,
                params=params
            )

            return stored_summary

        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            raise

    def _format_ticket_summary_markdown(self, summary_text: str, source_data: Dict[str, Any]) -> str:
        """Format ticket summary with proper markdown"""
        try:
            # Initialize markdown variable
            markdown = ""

            # Add AI analysis section
            # markdown += f"## 🤖 AI-Generated Analysis\n\n"

            # Extract the analysis part from the original summary
            analysis_parts = summary_text.split("Based on the open tickets")
            if len(analysis_parts) > 1:
                markdown += f"Based on the open tickets{analysis_parts[1]}"
            else:
                markdown += summary_text

            return markdown

        except Exception as e:
            logger.error(f"Error formatting ticket summary markdown: {str(e)}")
            return summary_text

    async def _get_source_data(
        self,
        summary_type: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get source data based on summary type"""
        if summary_type == 'zendesk_ticket':
            return await self._get_ticket_data(params['ticket_id'])
        elif summary_type == 'jira_issue':
            return await self._get_issue_data(params['issue_id'])
        elif summary_type == 'salesforce_account':
            return await self._get_account_data(params['account_id'])
        elif summary_type == 'all_tickets':
            return await self._get_all_tickets_data(params)
        # Add similar methods for other types...

        raise ValueError(f"Unsupported summary type: {summary_type}")

    async def _get_issue_data(self, issue_id: str) -> Dict[str, Any]:
        """Get comprehensive data for a single Jira issue"""
        try:
            # Get issue with related data
            query = """
                SELECT 
                    j.*,
                    zt.zd_ticket_id,
                    zt.ticket_subject,
                    sa.account_name,
                    sa.business_use_case
                FROM jira_issues j
                LEFT JOIN zendesk_jira_links zjl ON j.jira_issue_id = zjl.jira_issue_id
                LEFT JOIN zendesk_tickets zt ON zjl.zd_ticket_id = zt.zd_ticket_id
                LEFT JOIN salesforce_accounts sa ON zt.sf_account_id = sa.sf_account_id
                WHERE j.jira_issue_id = $1
            """
            issue = await db.fetchrow(query, issue_id)

            if not issue:
                raise ValueError(f"Jira issue {issue_id} not found")

            # Safely get status and priority with defaults
            status = issue.get('issue_status', 'Unknown')
            priority = issue.get('priority', 'Unknown')

            return {
                "issue": dict(issue),
                "metadata": {
                    "status": status,
                    "priority": priority,
                    "issue_age": (datetime.now() - issue['source_created_at']).days if issue.get('source_created_at') else None,
                    "has_zendesk_ticket": bool(issue.get('zd_ticket_id')),
                    "is_high_priority": priority in ['Urgent', 'High'],
                    "has_business_impact": bool(issue.get('business_use_case')),
                    "is_target_account": issue.get('is_target_account', False),
                    "is_open": status not in ['Done', 'Closed', 'Resolved'],
                    "is_closed": status in ['Done', 'Closed', 'Resolved']
                }
            }

        except Exception as e:
            logger.error(f"Error getting issue data: {str(e)}")
            raise

    async def _get_account_data(self, account_id: str) -> Dict[str, Any]:
        """Get comprehensive data for a single Salesforce account"""
        try:
            # Get account with related data
            query = """
                SELECT 
                    sa.*,
                    COUNT(DISTINCT zt.zd_ticket_id) as ticket_count,
                    COUNT(DISTINCT j.jira_issue_id) as issue_count
                FROM salesforce_accounts sa
                LEFT JOIN zendesk_tickets zt ON sa.sf_account_id = zt.sf_account_id
                LEFT JOIN jira_issues j ON sa.sf_account_id = j.sf_account_id
                WHERE sa.sf_account_id = $1
                GROUP BY sa.sf_account_id
            """
            account = await db.fetchrow(query, account_id)

            if not account:
                raise ValueError(f"Salesforce account {account_id} not found")

            # Get recent tickets for this account
            tickets_query = """
                SELECT zt.*
                FROM zendesk_tickets zt
                WHERE zt.sf_account_id = $1
                ORDER BY zt.source_created_at DESC
                LIMIT 5
            """
            recent_tickets = await db.fetch(tickets_query, account_id)

            # Get recent issues for this account
            issues_query = """
                SELECT j.*
                FROM jira_issues j
                WHERE j.sf_account_id = $1
                ORDER BY j.source_created_at DESC
                LIMIT 5
            """
            recent_issues = await db.fetch(issues_query, account_id)

            # Convert account dict and handle Decimal values
            account_dict = dict(account)
            for key, value in account_dict.items():
                if hasattr(value, 'quantize'):  # Check if it's a Decimal
                    account_dict[key] = float(value)

            return {
                "account": account_dict,
                "recent_tickets": [dict(ticket) for ticket in recent_tickets],
                "recent_issues": [dict(issue) for issue in recent_issues],
                "metadata": {
                    "ticket_count": int(account.get('ticket_count', 0)),
                    "issue_count": int(account.get('issue_count', 0)),
                    "is_target_account": bool(account.get('is_target_account', False)),
                    "is_migration_account": bool(account.get('is_migration_account', False)),
                    "account_type": str(account.get('type', 'Unknown')),
                    "has_business_use_case": bool(account.get('business_use_case')),
                    "has_recent_activity": bool(recent_tickets or recent_issues)
                }
            }

        except Exception as e:
            logger.error(f"Error getting account data: {str(e)}")
            raise

    def _get_summary_prompt(self, summary_type: str) -> str:
        """Get appropriate prompt template for summary type"""
        prompts = {
            'zendesk_ticket': (
                "Summarize this support ticket focusing on: "
                "1. Core issue and severity\n"
                "2. Current status and resolution progress\n"
                "3. Customer impact\n"
                "4. Key actions taken"
            ),
            'all_tickets': (
                "As a VP of Sales, analyze these support tickets and provide:\n\n"
                "1. Executive Summary:\n"
                "   - Key business impact and customer sentiment\n"
                "   - Critical issues affecting customer relationships\n"
                "   - Overall support health indicators\n\n"
                "2. Actionable Insights:\n"
                "   - Specific recommendations for account management\n"
                "   - Areas requiring immediate attention\n"
                "   - Opportunities for customer success intervention\n\n"
                "3. Strategic Recommendations:\n"
                "   - Suggested next steps for customer engagement\n"
                "   - Potential upsell or expansion opportunities\n"
                "   - Risk mitigation strategies\n\n"
                "Focus on business impact and actionable steps that can improve customer relationships and drive revenue growth."
            ),
            'jira_issue': (
                "Summarize this Jira issue focusing on: "
                "1. Core issue and business impact\n"
                "2. Current status and resolution progress\n"
                "3. Customer impact and relationship implications\n"
                "4. Key actions taken and next steps"
            ),
            'all_issues': (
                "As a VP of Sales, analyze these Jira issues and provide:\n\n"
                "1. Executive Summary:\n"
                "   - Key business impact and customer sentiment\n"
                "   - Critical issues affecting customer relationships\n"
                "   - Overall development health indicators\n\n"
                "2. Actionable Insights:\n"
                "   - Specific recommendations for account management\n"
                "   - Areas requiring immediate attention\n"
                "   - Opportunities for customer success intervention\n\n"
                "3. Strategic Recommendations:\n"
                "   - Suggested next steps for customer engagement\n"
                "   - Potential upsell or expansion opportunities\n"
                "   - Risk mitigation strategies\n\n"
                "Focus on business impact and actionable steps that can improve customer relationships and drive revenue growth."
            ),
            'salesforce_account': (
                "Summarize this Salesforce account focusing on: "
                "1. Account health and relationship status\n"
                "2. Current business challenges and opportunities\n"
                "3. Customer impact and satisfaction indicators\n"
                "4. Key actions and strategic recommendations"
            ),
            'all_accounts': (
                "As a VP of Sales, analyze these Salesforce accounts and provide:\n\n"
                "1. Executive Summary:\n"
                "   - Key business impact and customer sentiment\n"
                "   - Critical issues affecting customer relationships\n"
                "   - Overall account health indicators\n\n"
                "2. Actionable Insights:\n"
                "   - Specific recommendations for account management\n"
                "   - Areas requiring immediate attention\n"
                "   - Opportunities for customer success intervention\n\n"
                "3. Strategic Recommendations:\n"
                "   - Suggested next steps for customer engagement\n"
                "   - Potential upsell or expansion opportunities\n"
                "   - Risk mitigation strategies\n\n"
                "Focus on business impact and actionable steps that can improve customer relationships and drive revenue growth."
            ),
            # Add other prompt templates...
        }
        return prompts.get(summary_type, "Provide a comprehensive summary of the data")

    async def _get_ticket_data(self, ticket_id: str) -> Dict[str, Any]:
        """Get comprehensive data for a single ticket"""
        try:
            # Get ticket with related data
            query = """
                SELECT 
                    zt.*,
                    sa.account_name,
                    sa.business_use_case,
                    sa.type as account_type
                FROM zendesk_tickets zt
                LEFT JOIN salesforce_accounts sa ON zt.sf_account_id = sa.sf_account_id
                WHERE zt.zd_ticket_id = $1
            """
            ticket = await db.fetchrow(query, int(ticket_id))

            if not ticket:
                raise ValueError(f"Ticket {ticket_id} not found")

            # Get linked Jira issues
            jira_query = """
                SELECT j.* 
                FROM jira_issues j
                JOIN zendesk_jira_links zjl ON j.jira_issue_id = zjl.jira_issue_id
                WHERE zjl.zd_ticket_id = $1
            """
            jira_issues = await db.fetch(jira_query, int(ticket_id))

            # Calculate ticket age in days
            ticket_age = None
            if ticket.get('source_created_at'):
                ticket_age = (datetime.now() -
                              ticket['source_created_at']).days

            # Safely get status and priority with defaults
            status = ticket.get('status', 'Unknown')
            priority = ticket.get('priority', 'Unknown')

            return {
                "ticket": dict(ticket),
                "jira_issues": [dict(issue) for issue in jira_issues],
                "metadata": {
                    "status": status,
                    "priority": priority,
                    "ticket_age": ticket_age,
                    "has_jira_issues": bool(jira_issues),
                    "is_high_priority": priority in ['Urgent', 'High'],
                    "has_business_impact": bool(ticket.get('business_use_case')),
                    "is_target_account": ticket.get('is_target_account', False),
                    "is_open": status in ['Open', 'Pending', 'In Progress'],
                    "is_closed": status in ['Closed', 'Resolved', 'Solved']
                }
            }

        except Exception as e:
            logger.error(f"Error getting ticket data: {str(e)}")
            raise

    async def _get_all_tickets_data(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get data for all tickets within date range"""
        try:
            start_date = params.get('date_range_start')
            end_date = params.get('date_range_end')

            # Check if we need to filter by specific ticket IDs
            include_ticket_ids = params.get('include_ticket_ids', [])
            exclude_ticket_ids = params.get('exclude_ticket_ids', [])

            # Base query for tickets with related data
            query = """
                WITH ticket_data AS (
                    SELECT 
                        zt.*,
                        sa.account_name,
                        sa.business_use_case,
                        sa.type as account_type,
                        COUNT(DISTINCT j.jira_issue_id) as jira_issue_count
                    FROM zendesk_tickets zt
                    LEFT JOIN salesforce_accounts sa ON zt.sf_account_id = sa.sf_account_id
                    LEFT JOIN zendesk_jira_links zjl ON zt.zd_ticket_id = zjl.zd_ticket_id
                    LEFT JOIN jira_issues j ON zjl.jira_issue_id = j.jira_issue_id
                    WHERE 1=1
                    AND ($1::timestamp IS NULL OR zt.source_created_at >= $1)
                    AND ($2::timestamp IS NULL OR zt.source_created_at <= $2)
            """

            query_params = [start_date, end_date]

            # Add filtering by specific ticket IDs if provided
            if include_ticket_ids:
                placeholders = [
                    f"${i+3}" for i in range(len(include_ticket_ids))]
                query += f" AND zt.zd_ticket_id::text IN ({', '.join(placeholders)})"
                query_params.extend(include_ticket_ids)

            # Add exclusion of specific ticket IDs if provided
            if exclude_ticket_ids:
                placeholders = [
                    f"${i+3+len(include_ticket_ids)}" for i in range(len(exclude_ticket_ids))]
                query += f" AND zt.zd_ticket_id::text NOT IN ({', '.join(placeholders)})"
                query_params.extend(exclude_ticket_ids)

            # Complete the query
            query += """
                    GROUP BY zt.zd_ticket_id, sa.account_name, sa.business_use_case, sa.type
                )
                SELECT 
                    td.*,
                    s.summary as ticket_summary
                FROM ticket_data td
                LEFT JOIN summaries s ON (s.source_ids->>'ticket_id')::text = td.zd_ticket_id::text
                AND s.summary_type = 'zendesk_ticket'
                AND s.is_valid = true
                ORDER BY td.source_created_at DESC
            """

            tickets = await db.fetch(query, *query_params)

            # Calculate analytics
            priority_counts = {}
            status_counts = {}
            ticket_types = {}
            total_tickets = len(tickets)
            open_tickets = 0
            high_priority_tickets = 0
            tickets_with_jira = 0
            target_account_tickets = 0

            for ticket in tickets:
                # Count priorities
                priority = ticket.get('priority', 'Unknown')
                priority_counts[priority] = priority_counts.get(
                    priority, 0) + 1

                # Count statuses
                status = ticket.get('status', 'Unknown')
                status_counts[status] = status_counts.get(status, 0) + 1

                # Count ticket types
                ticket_type = ticket.get('ticket_type', 'Unknown')
                ticket_types[ticket_type] = ticket_types.get(
                    ticket_type, 0) + 1

                # Count other metrics
                if status in ['Open', 'Pending', 'In Progress']:
                    open_tickets += 1
                if priority in ['Urgent', 'High']:
                    high_priority_tickets += 1
                if ticket.get('jira_issue_count', 0) > 0:
                    tickets_with_jira += 1
                if ticket.get('is_target_account', False):
                    target_account_tickets += 1

            return {
                "tickets": [dict(ticket) for ticket in tickets],
                "metadata": {
                    "total_count": total_tickets,
                    "open_tickets": open_tickets,
                    "high_priority_tickets": high_priority_tickets,
                    "tickets_with_jira": tickets_with_jira,
                    "target_account_tickets": target_account_tickets,
                    "priority_distribution": priority_counts,
                    "status_distribution": status_counts,
                    "ticket_type_distribution": ticket_types,
                    "date_range": {
                        "start": start_date,
                        "end": end_date
                    }
                }
            }

        except Exception as e:
            logger.error(f"Error getting all tickets data: {str(e)}")
            raise

    async def _store_summary(
        self,
        summary_type: str,
        summary_text: str,
        source_data: Dict[str, Any],
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Store generated summary in database"""
        try:
            # Determine hierarchy level from summary type
            hierarchy_level = 'individual'
            for level, types in self.SUMMARY_TYPES.items():
                if summary_type in types:
                    hierarchy_level = level
                    break

            # Determine category and source_type
            category_mapping = {
                'zendesk_ticket': ('zendesk', 'zendesk'),
                'jira_issue': ('jira', 'jira'),
                'salesforce_account': ('salesforce', 'salesforce'),
                'all_tickets': ('zendesk', 'zendesk'),
                'all_issues': ('jira', 'jira'),
                'all_accounts': ('salesforce', 'salesforce'),
                'system_wide': ('system', 'system')
            }

            category, source_type = category_mapping.get(
                summary_type, ('other', 'other'))

            # Prepare source_ids based on actual source data
            source_ids = {}
            if summary_type == 'zendesk_ticket':
                ticket = source_data.get('ticket', {})
                source_ids = {'ticket_id': str(ticket.get('zd_ticket_id'))}

                # Invalidate any existing group summaries that include this ticket
                await self._invalidate_group_summaries(ticket.get('zd_ticket_id'))

            elif summary_type == 'jira_issue':
                issue = source_data.get('issue', {})
                source_ids = {'issue_id': str(issue.get('jira_issue_id'))}
            elif summary_type == 'salesforce_account':
                account = source_data.get('account', {})
                source_ids = {'account_id': str(account.get('sf_account_id'))}
            elif summary_type == 'all_tickets':
                tickets = source_data.get('tickets', [])

                # Get the actual ticket IDs from the filtered data
                ticket_ids = [str(t.get('zd_ticket_id')) for t in tickets]

                # If include_ticket_ids is provided, ensure we only store those IDs
                if params.get('include_ticket_ids'):
                    include_ids = [str(id) for id in params.get(
                        'include_ticket_ids', [])]
                    # Filter to only include the specified IDs
                    ticket_ids = [id for id in ticket_ids if id in include_ids]

                source_ids = {
                    'ticket_ids': ticket_ids,
                    'date_range': {
                        'start': params.get('date_range_start'),
                        'end': params.get('date_range_end')
                    }
                }

            # Prepare query_params based on actual parameters used
            query_params = {
                'force_regenerate': params.get('force_regenerate', False)
            }

            # Add date range if it exists
            if params.get('date_range_start') or params.get('date_range_end'):
                query_params['date_range'] = {
                    'start': params.get('date_range_start'),
                    'end': params.get('date_range_end')
                }

            # Add include/exclude ticket IDs if they exist
            if params.get('include_ticket_ids'):
                query_params['include_ticket_ids'] = params.get(
                    'include_ticket_ids')

            if params.get('exclude_ticket_ids'):
                query_params['exclude_ticket_ids'] = params.get(
                    'exclude_ticket_ids')

            query = """
                INSERT INTO summaries (
                    summary_type,
                    hierarchy_level,
                    category,
                    summary,
                    source_type,
                    source_ids,
                    query_params,
                    date_range_start,
                    date_range_end,
                    metadata,
                    last_generated_at,
                    last_verified_at,
                    hash_signature
                ) VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7::jsonb, $8, $9, $10::jsonb, NOW(), NOW(), $11)
                RETURNING *
            """

            # Create hash signature from source data
            hash_signature = str(hash(str(source_data)))

            result = await db.fetchrow(
                query,
                summary_type,
                hierarchy_level,
                category,
                summary_text,
                source_type,
                json.dumps(source_ids),
                json.dumps(query_params),
                params.get('date_range_start'),
                params.get('date_range_end'),
                json.dumps(source_data.get('metadata', {})),
                hash_signature
            )

            return dict(result)

        except Exception as e:
            logger.error(f"Error storing summary: {str(e)}")
            raise

    async def _invalidate_group_summaries(self, ticket_id: int) -> None:
        """Invalidate any group summaries that include this ticket"""
        try:
            query = """
                UPDATE summaries
                SET is_valid = false
                WHERE summary_type = 'all_tickets'
                AND (source_ids->'ticket_ids')::jsonb @> $1::jsonb
                AND is_valid = true
            """
            await db.execute(query, json.dumps([str(ticket_id)]))
            logger.info(
                f"Invalidated group summaries containing ticket {ticket_id}")
        except Exception as e:
            logger.error(f"Error invalidating group summaries: {str(e)}")
            raise


hierarchical_summary_service = HierarchicalSummaryService()
