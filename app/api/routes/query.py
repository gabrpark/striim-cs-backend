from fastapi import APIRouter, HTTPException
from app.services.database.database import db
from app.services.data.data_processing_service import data_processing_service
from typing import Dict, Any, Optional
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/ticket/{ticket_id}")
async def get_ticket_summary(ticket_id: str, include_details: bool = False):
    """
    Get comprehensive summary of a Zendesk ticket including related data.
    Optional parameter include_details=true to get raw data.
    """
    try:
        # 1. Get Zendesk ticket with client_id
        ticket_query = """
            SELECT zt.*, sa.sf_account_id, sa.account_name, sa.business_use_case,
                   sa.target_upsell_value, sa.type as account_type,
                   sa.is_target_account, sa.is_migration_account
            FROM zendesk_tickets zt
            LEFT JOIN clients c ON zt.client_id = c.id
            LEFT JOIN salesforce_accounts sa ON c.id = sa.client_id
            WHERE zt.zd_ticket_id = $1
        """
        ticket = await db.fetchrow(ticket_query, int(ticket_id))
        if not ticket:
            raise HTTPException(
                status_code=404,
                detail=f"Ticket {ticket_id} not found"
            )

        # 2. Get linked Jira issues through zendesk_jira_links
        jira_query = """
            SELECT j.* 
            FROM jira_issues j
            JOIN zendesk_jira_links zjl ON j.jira_issue_id = zjl.jira_issue_id
            WHERE zjl.zd_ticket_id = $1
            ORDER BY j.source_created_at DESC
        """
        jira_issues = await db.fetch(jira_query, int(ticket_id))

        # 3. Get Salesforce account info using client_id
        sf_query = """
            SELECT sa.*,
                   COUNT(DISTINCT zt.zd_ticket_id) as total_tickets,
                   COUNT(DISTINCT CASE WHEN zt.status = 'Open' THEN zt.zd_ticket_id END) as open_tickets
            FROM salesforce_accounts sa
            LEFT JOIN zendesk_tickets zt ON sa.client_id = zt.client_id
            WHERE sa.client_id = $1
            GROUP BY sa.sf_account_id
        """
        sf_account = await db.fetchrow(sf_query, ticket.get('client_id'))

        # 4. Get recent tickets from same client
        recent_tickets_query = """
            SELECT zt.*
            FROM zendesk_tickets zt
            WHERE zt.client_id = $1
            AND zt.zd_ticket_id != $2
            ORDER BY zt.source_created_at DESC
            LIMIT 5
        """
        recent_tickets = await db.fetch(
            recent_tickets_query,
            ticket.get('client_id'),
            int(ticket_id)
        )

        # 5. Get active Jira issues for this client
        active_jira_query = """
            SELECT DISTINCT j.* 
            FROM jira_issues j
            JOIN zendesk_jira_links zjl ON j.jira_issue_id = zjl.jira_issue_id
            JOIN zendesk_tickets zt ON zjl.zd_ticket_id = zt.zd_ticket_id
            WHERE zt.client_id = $1
            AND j.issue_status NOT IN ('Done', 'Closed')
            ORDER BY j.source_created_at DESC
            LIMIT 5
        """
        active_jira_issues = await db.fetch(active_jira_query, ticket.get('client_id'))

        # Prepare data for LLM summary
        context = {
            "ticket": ticket,
            "jira_issues": jira_issues,
            "account": sf_account,
            "recent_tickets": recent_tickets,
            "active_jira_issues": active_jira_issues
        }

        # Generate comprehensive summary
        summary = await data_processing_service.generate_comprehensive_summary(context)

        # Store the summary in the database
        update_query = """
            UPDATE zendesk_tickets 
            SET summary = $1,
                updated_at = CURRENT_TIMESTAMP
            WHERE zd_ticket_id = $2
        """
        await db.execute(update_query, summary, int(ticket_id))

        # Format the response based on whether details are requested
        response = {
            "ticket_id": ticket_id,
            "summary": summary
        }

        if include_details:
            response["details"] = {
                "ticket": ticket,
                "jira_issues": jira_issues,
                "account_info": sf_account,
                "recent_tickets": recent_tickets,
                "active_jira_issues": active_jira_issues
            }
            response["_debug"] = {
                "raw_context": context
            }

        return response

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing ticket summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ticket/{ticket_id}/cached-summary")
async def get_cached_ticket_summary(ticket_id: str):
    """Get the stored LLM summary for a ticket without regenerating it"""
    try:
        query = """
            SELECT summary, updated_at
            FROM zendesk_tickets
            WHERE zd_ticket_id = $1
        """
        result = await db.fetchrow(query, int(ticket_id))

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Ticket {ticket_id} not found"
            )

        if not result['summary']:
            raise HTTPException(
                status_code=404,
                detail=f"No summary available for ticket {ticket_id}"
            )

        return {
            "ticket_id": ticket_id,
            "summary": result['summary'],
            "last_updated": result['updated_at']
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching cached summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/account/{account_id}/health")
async def get_account_health(account_id: str):
    """
    Get account health summary including:
    - Account details
    - Recent tickets analysis
    - Ongoing issues
    - Subscription status
    """
    try:
        # 1. Get Salesforce account
        account_query = """
            SELECT * FROM salesforce_accounts
            WHERE sf_account_id = $1
        """
        account = await db.fetchrow(account_query, account_id)
        if not account:
            raise HTTPException(
                status_code=404,
                detail=f"Account {account_id} not found"
            )

        # 2. Get recent tickets
        tickets_query = """
            SELECT * FROM zendesk_tickets
            WHERE sf_account_id = $1
            ORDER BY source_created_at DESC
            LIMIT 10
        """
        recent_tickets = await db.fetch(tickets_query, account_id)

        # 3. Get active Jira issues linked to recent tickets
        active_issues_query = """
            SELECT DISTINCT j.* 
            FROM jira_issues j
            JOIN zendesk_jira_links zjl ON j.jira_issue_id = zjl.jira_issue_id
            JOIN zendesk_tickets zt ON zjl.zd_ticket_id = zt.zd_ticket_id
            WHERE zt.sf_account_id = $1
            AND j.issue_status NOT IN ('Done', 'Closed')
        """
        active_issues = await db.fetch(active_issues_query, account_id)

        # Prepare data for LLM analysis
        context = {
            "account": account,
            "recent_tickets": recent_tickets,
            "active_issues": active_issues
        }

        # Generate health summary
        summary = await data_processing_service.generate_account_health_summary(context)

        return {
            "status": "success",
            "account_id": account_id,
            "summary": summary,
            "details": {
                "account": account,
                "recent_tickets": recent_tickets,
                "active_issues": active_issues
            }
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing account health: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/tickets")
async def search_tickets(
    account_id: Optional[str] = None,
    priority: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Search tickets with filters"""
    try:
        conditions = ["1=1"]  # Always true condition to start
        params = []
        param_count = 1

        if account_id:
            conditions.append(f"sf_account_id = ${param_count}")
            params.append(account_id)
            param_count += 1

        if priority:
            conditions.append(f"priority = ${param_count}")
            params.append(priority)
            param_count += 1

        if status:
            conditions.append(f"status = ${param_count}")
            params.append(status)
            param_count += 1

        if start_date:
            conditions.append(f"source_created_at >= ${param_count}")
            params.append(start_date)
            param_count += 1

        if end_date:
            conditions.append(f"source_created_at <= ${param_count}")
            params.append(end_date)
            param_count += 1

        query = f"""
            SELECT * FROM zendesk_tickets
            WHERE {" AND ".join(conditions)}
            ORDER BY source_created_at DESC
        """

        results = await db.fetch(query, *params)

        return {
            "status": "success",
            "count": len(results),
            "results": results
        }

    except Exception as e:
        logger.error(f"Error searching tickets: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
