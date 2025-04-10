from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional, List
from datetime import datetime
from app.services.data.summary_service import summary_service
from app.services.data.data_processing_service import data_processing_service
from app.services.database.database import db
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# Ticket Summary Routes


@router.get("/ticket/{ticket_id}")
async def get_ticket_summary(
    ticket_id: str,
    include_details: bool = False,
    force_regenerate: bool = False
) -> Dict[str, Any]:
    """
    Get comprehensive summary of a ticket including related data.
    Parameters:
        - include_details: Include raw data in response
        - force_regenerate: Force regeneration of the summary
    """
    try:
        # Check for existing summary first if not force_regenerate
        if not force_regenerate:
            query = """
                SELECT s.*, zt.ticket_type, zt.priority, zt.status
                FROM summaries s
                JOIN zendesk_tickets zt ON (s.source_ids->>'ticket_id')::int = zt.zd_ticket_id
                WHERE s.summary_type = 'ticket' 
                AND (s.source_ids->>'ticket_id')::int = $1
                AND s.is_valid = true
                AND s.last_generated_at > NOW() - INTERVAL '24 hours'
            """
            existing_summary = await db.fetchrow(query, int(ticket_id))

            if existing_summary:
                logger.info(f"Found cached summary for ticket {ticket_id}")
                response = {
                    "ticket_id": ticket_id,
                    "summary": existing_summary['summary'],
                    "cached": True,
                    "last_generated": existing_summary['last_generated_at']
                }

                if include_details:
                    # Fetch additional details if requested
                    # Get comprehensive data
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
                            status_code=404, detail=f"Ticket {ticket_id} not found")

                    # Get related data
                    jira_query = """
                        SELECT j.* 
                        FROM jira_issues j
                        JOIN zendesk_jira_links zjl ON j.jira_issue_id = zjl.jira_issue_id
                        WHERE zjl.zd_ticket_id = $1
                        ORDER BY j.source_created_at DESC
                    """
                    jira_issues = await db.fetch(jira_query, int(ticket_id))

                    sf_query = """
                        SELECT sa.*
                        FROM salesforce_accounts sa
                        WHERE sa.client_id = $1
                    """
                    sf_account = await db.fetchrow(sf_query, ticket['client_id'])

                    recent_tickets_query = """
                        SELECT zt.*
                        FROM zendesk_tickets zt
                        WHERE zt.client_id = $1 AND zt.zd_ticket_id != $2
                        ORDER BY zt.source_created_at DESC
                        LIMIT 5
                    """
                    recent_tickets = await db.fetch(recent_tickets_query, ticket['client_id'], int(ticket_id))

                    active_jira_query = """
                        SELECT DISTINCT j.* 
                        FROM jira_issues j
                        JOIN zendesk_jira_links zjl ON j.jira_issue_id = zjl.jira_issue_id
                        JOIN zendesk_tickets zt ON zjl.zd_ticket_id = zt.zd_ticket_id
                        WHERE zt.client_id = $1 AND j.issue_status NOT IN ('Done', 'Closed')
                        ORDER BY j.source_created_at DESC
                        LIMIT 5
                    """
                    active_jira_issues = await db.fetch(active_jira_query, ticket['client_id'])

                    context = {
                        "ticket": ticket,
                        "jira_issues": jira_issues,
                        "account": sf_account,
                        "recent_tickets": recent_tickets,
                        "active_jira_issues": active_jira_issues
                    }

                    summary = await data_processing_service.generate_comprehensive_summary(context)

                    # Store in zendesk_tickets table
                    logger.info(f"Storing summary for ticket {ticket_id}")
                    store_ticket_query = """
                        UPDATE zendesk_tickets 
                        SET summary = $1, updated_at = NOW()
                        WHERE zd_ticket_id = $2
                        RETURNING zd_ticket_id, summary
                    """
                    stored = await db.fetchrow(store_ticket_query, summary, int(ticket_id))
                    # logger.info(f"Stored in zendesk_tickets: {stored}")

                    # Store in summaries table with explicit type casting
                    store_summary_query = """
                        INSERT INTO summaries (
                            summary_type,
                            summary,
                            source_type,
                            source_ids,
                            query_params,
                            date_range_start,
                            date_range_end,
                            metadata,
                            last_generated_at,
                            last_verified_at,
                            hash_signature,
                            is_valid
                        ) VALUES (
                            'ticket',
                            $1::text,
                            'raw_data',
                            jsonb_build_object('ticket_id', $2::int),
                            jsonb_build_object('force_regenerate', $3::boolean),
                            NULL,
                            NULL,
                            jsonb_build_object(
                                'ticket_type', $4::text,
                                'priority', $5::text,
                                'status', $6::text
                            ),
                            NOW(),
                            NOW(),
                            $7::text,
                            true
                        )
                        RETURNING id, summary
                    """

                    # Create hash signature for tracking changes
                    hash_signature = str(hash(summary))

                    try:
                        stored_summary = await db.fetchrow(
                            store_summary_query,
                            summary,
                            int(ticket_id),
                            force_regenerate,
                            str(ticket.get('ticket_type', '')),
                            str(ticket.get('priority', '')),
                            str(ticket.get('status', '')),
                            hash_signature
                        )
                        logger.info(
                            f"Stored in summaries table: {stored_summary}")
                    except Exception as e:
                        logger.error(
                            f"Failed to store in summaries table: {str(e)}", exc_info=True)

                    response["details"] = {
                        "ticket": ticket,
                        "jira_issues": jira_issues,
                        "account_info": sf_account,
                        "recent_tickets": recent_tickets,
                        "active_jira_issues": active_jira_issues
                    }

                return response

        # If no valid cached summary exists or force_regenerate is True,
        # continue with the existing generation logic
        if force_regenerate:
            return await summary_service.get_or_generate_summary(
                summary_type='ticket',
                params={'ticket_id': ticket_id},
                force_regenerate=True
            )

        # Get comprehensive data
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
                status_code=404, detail=f"Ticket {ticket_id} not found")

        # Get related data
        jira_query = """
            SELECT j.* 
            FROM jira_issues j
            JOIN zendesk_jira_links zjl ON j.jira_issue_id = zjl.jira_issue_id
            WHERE zjl.zd_ticket_id = $1
            ORDER BY j.source_created_at DESC
        """
        jira_issues = await db.fetch(jira_query, int(ticket_id))

        sf_query = """
            SELECT sa.*
            FROM salesforce_accounts sa
            WHERE sa.client_id = $1
        """
        sf_account = await db.fetchrow(sf_query, ticket['client_id'])

        recent_tickets_query = """
            SELECT zt.*
            FROM zendesk_tickets zt
            WHERE zt.client_id = $1 AND zt.zd_ticket_id != $2
            ORDER BY zt.source_created_at DESC
            LIMIT 5
        """
        recent_tickets = await db.fetch(recent_tickets_query, ticket['client_id'], int(ticket_id))

        active_jira_query = """
            SELECT DISTINCT j.* 
            FROM jira_issues j
            JOIN zendesk_jira_links zjl ON j.jira_issue_id = zjl.jira_issue_id
            JOIN zendesk_tickets zt ON zjl.zd_ticket_id = zt.zd_ticket_id
            WHERE zt.client_id = $1 AND j.issue_status NOT IN ('Done', 'Closed')
            ORDER BY j.source_created_at DESC
            LIMIT 5
        """
        active_jira_issues = await db.fetch(active_jira_query, ticket['client_id'])

        context = {
            "ticket": ticket,
            "jira_issues": jira_issues,
            "account": sf_account,
            "recent_tickets": recent_tickets,
            "active_jira_issues": active_jira_issues
        }

        summary = await data_processing_service.generate_comprehensive_summary(context)

        # Store in zendesk_tickets table
        logger.info(f"Storing summary for ticket {ticket_id}")
        store_ticket_query = """
            UPDATE zendesk_tickets 
            SET summary = $1, updated_at = NOW()
            WHERE zd_ticket_id = $2
            RETURNING zd_ticket_id, summary
        """
        stored = await db.fetchrow(store_ticket_query, summary, int(ticket_id))
        # logger.info(f"Stored in zendesk_tickets: {stored}")

        # Store in summaries table with explicit type casting
        store_summary_query = """
            INSERT INTO summaries (
                summary_type,
                summary,
                source_type,
                source_ids,
                query_params,
                date_range_start,
                date_range_end,
                metadata,
                last_generated_at,
                last_verified_at,
                hash_signature,
                is_valid
            ) VALUES (
                'ticket',
                $1::text,
                'raw_data',
                jsonb_build_object('ticket_id', $2::int),
                jsonb_build_object('force_regenerate', $3::boolean),
                NULL,
                NULL,
                jsonb_build_object(
                    'ticket_type', $4::text,
                    'priority', $5::text,
                    'status', $6::text
                ),
                NOW(),
                NOW(),
                $7::text,
                true
            )
            RETURNING id, summary
        """

        # Create hash signature for tracking changes
        hash_signature = str(hash(summary))

        try:
            stored_summary = await db.fetchrow(
                store_summary_query,
                summary,
                int(ticket_id),
                force_regenerate,
                str(ticket.get('ticket_type', '')),
                str(ticket.get('priority', '')),
                str(ticket.get('status', '')),
                hash_signature
            )
            logger.info(f"Stored in summaries table: {stored_summary}")
        except Exception as e:
            logger.error(
                f"Failed to store in summaries table: {str(e)}", exc_info=True)

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

        return response

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing ticket summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ticket/{ticket_id}/cached")
async def get_cached_ticket_summary(ticket_id: str) -> Dict[str, Any]:
    """Get the stored LLM summary for a ticket without regenerating it"""
    try:
        query = """
            SELECT summary, updated_at
            FROM zendesk_tickets
            WHERE zd_ticket_id = $1
        """
        result = await db.fetchrow(query, int(ticket_id))

        if not result or not result['summary']:
            raise HTTPException(
                status_code=404,
                detail=f"No cached summary available for ticket {ticket_id}"
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

# Company/Account Routes


@router.get("/company/{company_id}")
async def get_company_summary(
    company_id: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    use_existing_summaries: bool = True,
    force_regenerate: bool = False
) -> Dict[str, Any]:
    """Get summary for a company"""
    try:
        # First try to get health summary
        try:
            health_summary = await get_account_health(company_id)
            if not force_regenerate:
                return health_summary
        except HTTPException:
            pass  # Fall back to basic summary

        params = {
            'company_id': company_id,
            'date_range_start': start_date,
            'date_range_end': end_date,
            'use_raw_data': not use_existing_summaries
        }
        return await summary_service.get_or_generate_summary(
            summary_type='company',
            params=params,
            force_regenerate=force_regenerate
        )
    except Exception as e:
        logger.error(f"Error getting company summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/summaries/multi-ticket")
async def get_multi_ticket_summary(
    ticket_ids: List[str],
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    use_existing_summaries: bool = True,
    force_regenerate: bool = False
) -> Dict[str, Any]:
    """Get summary for multiple tickets"""
    try:
        params = {
            'ticket_ids': ticket_ids,
            'date_range_start': start_date,
            'date_range_end': end_date,
            'use_raw_data': not use_existing_summaries
        }
        return await summary_service.get_or_generate_summary(
            summary_type='multi_ticket',
            params=params,
            force_regenerate=force_regenerate
        )
    except Exception as e:
        logger.error(f"Error getting multi-ticket summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/summaries/multi-company")
async def get_multi_company_summary(
    company_ids: List[str],
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    metrics: Optional[List[str]] = None,
    use_existing_summaries: bool = True,
    force_regenerate: bool = False
) -> Dict[str, Any]:
    """Get summary comparing multiple companies"""
    try:
        params = {
            'company_ids': company_ids,
            'date_range_start': start_date,
            'date_range_end': end_date,
            'metrics': metrics or ['ticket_volume', 'response_time'],
            'use_raw_data': not use_existing_summaries
        }
        return await summary_service.get_or_generate_summary(
            summary_type='multi_company',
            params=params,
            force_regenerate=force_regenerate
        )
    except Exception as e:
        logger.error(f"Error getting multi-company summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summaries/{summary_id}")
async def get_existing_summary(summary_id: int) -> Dict[str, Any]:
    """Get an existing summary by ID"""
    try:
        query = "SELECT * FROM summaries WHERE id = $1 AND is_valid = true"
        summary = await db.fetchrow(query, summary_id)

        if not summary:
            raise HTTPException(
                status_code=404,
                detail=f"Valid summary with ID {summary_id} not found"
            )

        return dict(summary)
    except Exception as e:
        logger.error(f"Error getting existing summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Search Routes


@router.get("/search/tickets")
async def search_tickets(
    account_id: Optional[str] = None,
    priority: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict[str, Any]:
    """Search tickets with filters"""
    # ... existing search implementation ...


async def get_account_health(account_id: str) -> Dict[str, Any]:
    """Get account health summary including account details and analysis"""
    account_query = "SELECT * FROM salesforce_accounts WHERE sf_account_id = $1"
    account = await db.fetchrow(account_query, account_id)
    if not account:
        raise HTTPException(
            status_code=404, detail=f"Account {account_id} not found")

    tickets_query = """
        SELECT * FROM zendesk_tickets 
        WHERE sf_account_id = $1 
        ORDER BY source_created_at DESC LIMIT 10
    """
    recent_tickets = await db.fetch(tickets_query, account_id)

    context = {"account": account, "recent_tickets": recent_tickets}
    summary = await data_processing_service.generate_account_health_summary(context)

    # Store the generated summary
    store_query = """
        INSERT INTO summaries (type, entity_id, summary, created_at)
        VALUES ('account_health', $1, $2, NOW())
        ON CONFLICT (type, entity_id) 
        DO UPDATE SET summary = $2, updated_at = NOW()
    """
    await db.execute(store_query, account_id, summary)

    return {
        "account_id": account_id,
        "summary": summary,
        "details": context
    }
