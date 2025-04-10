from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional, List
from datetime import datetime
from app.services.data.hierarchical_summary_service import hierarchical_summary_service
import logging
import json
from app.services.database.database import db

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/summaries/individual/{source_type}/{item_id}")
async def get_individual_summary(
    source_type: str,  # 'zendesk_ticket', 'jira_issue', 'salesforce_account'
    item_id: str,
    force_regenerate: bool = False
) -> Dict[str, Any]:
    """Get summary for individual item"""
    try:
        # Create proper params structure based on source_type
        params = {
            'filters': {},  # Add any additional filters here
            'item_id': item_id  # Add item_id to the main params dict
        }

        if source_type == 'zendesk_ticket':
            params['ticket_id'] = item_id
        elif source_type == 'jira_issue':
            params['issue_id'] = item_id
        elif source_type == 'salesforce_account':
            params['account_id'] = item_id

        return await hierarchical_summary_service.get_or_generate_summary(
            summary_type=source_type,
            params=params,
            force_regenerate=force_regenerate
        )
    except Exception as e:
        logger.error(f"Error getting individual summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summaries/group/{group_type}")
async def get_group_summary(
    group_type: str,  # 'all_tickets', 'all_issues', 'all_accounts'
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    force_regenerate: bool = False,
    customer_id: Optional[str] = None
) -> Dict[str, Any]:
    """Get summary for a group of items"""
    try:
        params = {
            'date_range_start': start_date,
            'date_range_end': end_date
        }

        if customer_id:
            # Get ticket IDs for this customer
            query = """
                SELECT zd_ticket_id::text
                FROM zendesk_tickets
                WHERE client_id = $1::text
            """
            ticket_ids = await db.fetch(query, customer_id)
            params['include_ticket_ids'] = [t['zd_ticket_id']
                                            for t in ticket_ids]

        return await hierarchical_summary_service.get_or_generate_summary(
            summary_type=group_type,
            params=params,
            force_regenerate=force_regenerate
        )
    except Exception as e:
        logger.error(f"Error getting group summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summaries/global")
async def get_global_summary(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    force_regenerate: bool = False
) -> Dict[str, Any]:
    """Get system-wide summary"""
    try:
        return await hierarchical_summary_service.get_or_generate_summary(
            summary_type='system_wide',
            params={
                'date_range_start': start_date,
                'date_range_end': end_date
            },
            force_regenerate=force_regenerate
        )
    except Exception as e:
        logger.error(f"Error getting global summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summaries/check/{source_type}/{item_id}")
async def check_summary_validity(
    source_type: str,  # 'zendesk_ticket', 'jira_issue', 'salesforce_account'
    item_id: str,
    date_range_start: Optional[datetime] = None,
    date_range_end: Optional[datetime] = None
) -> Dict[str, Any]:
    """Check if a valid summary exists for the given item"""
    try:
        logger.info(
            f"Checking summary validity for {source_type} with ID {item_id}")

        # Check the summaries table for an existing valid summary
        summary_query = """
            SELECT s.* 
            FROM summaries s
            WHERE s.summary_type = $1
            AND s.source_ids->>'ticket_id' = $2::text
            AND s.is_valid = true
            AND s.hierarchy_level = 'individual'
            AND s.category = 'zendesk'
            AND (
                ($3::timestamp IS NULL AND $4::timestamp IS NULL)
                OR (
                    ($3::timestamp IS NULL OR s.date_range_start >= $3)
                    AND ($4::timestamp IS NULL OR s.date_range_end <= $4)
                )
            )
            ORDER BY s.last_generated_at DESC
            LIMIT 1
        """

        logger.info(
            f"Executing query with params: source_type={source_type}, item_id={item_id}")
        summary = await db.fetchrow(
            summary_query,
            source_type,
            item_id,
            date_range_start,
            date_range_end
        )

        if summary:
            logger.info(f"Found valid summary for {source_type} {item_id}")
            return {
                "hasValidSummary": True,
                "summary": summary['summary'],
                "lastGeneratedAt": summary['last_generated_at']
            }

        logger.info(f"No valid summary found for {source_type} {item_id}")
        return {
            "hasValidSummary": False,
            "message": "No valid summary found"
        }

    except Exception as e:
        logger.error(
            f"Error checking summary validity: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
