from fastapi import APIRouter, HTTPException, Depends
from app.services.analytics.llm_service import csm_analytics
from app.services.database.database import db
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, validator
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class TimeRange(BaseModel):
    start: datetime
    end: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @validator('start', 'end', pre=True)
    def ensure_timezone(cls, v):
        if isinstance(v, datetime):
            if v.tzinfo is None:
                return v.replace(tzinfo=timezone.utc)
            return v
        # If it's a string, Pydantic will convert it to datetime after this
        return v

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.astimezone(timezone.utc).isoformat()
        }


class AnalyticsRequest(BaseModel):
    sf_account_id: str
    time_range: TimeRange
    namespace: Optional[str] = None


@router.post("/analyze", response_model=Dict[str, Any])
async def analyze_customer_health(request: AnalyticsRequest):
    """Analyze customer health based on multiple data sources"""
    try:
        start_time = request.time_range.start.replace(tzinfo=timezone.utc)
        end_time = request.time_range.end.replace(tzinfo=timezone.utc)

        async with db.connection() as conn:
            # First get the account info
            salesforce_data = await conn.fetch("""
                SELECT *
                FROM salesforce_accounts
                WHERE sf_account_id = $1
            """, request.sf_account_id)

            if not salesforce_data:
                raise HTTPException(
                    status_code=404,
                    detail=f"Account {request.sf_account_id} not found"
                )

            # Get the company domain from account email or name
            account = salesforce_data[0]
            company_name = account['company_name']

            # Get related Zendesk tickets by company name/email domain
            zendesk_data = await conn.fetch("""
                SELECT *
                FROM zendesk_tickets
                WHERE source_created_at BETWEEN $1 AND $2
                AND (
                    requester_email LIKE $3
                    OR requester_name LIKE $3
                )
                ORDER BY priority DESC, source_created_at DESC
            """, start_time, end_time, f"%{company_name}%")

            # Get related Jira issues through Zendesk ticket links
            jira_data = await conn.fetch("""
                SELECT DISTINCT j.*
                FROM jira_issues j
                INNER JOIN zendesk_jira_links zj ON j.jira_issue_id = zj.jira_issue_id
                INNER JOIN zendesk_tickets zt ON zj.zd_ticket_id = zt.zd_ticket_id
                WHERE j.source_created_at BETWEEN $1 AND $2
                AND (
                    zt.requester_email LIKE $3
                    OR zt.requester_name LIKE $3
                )
                ORDER BY j.priority DESC, j.source_created_at DESC
            """, start_time, end_time, f"%{company_name}%")

            analysis = await csm_analytics.analyze_customer_health(
                time_range=request.time_range.dict(),
                account_id=request.sf_account_id,
                salesforce_data=salesforce_data,
                zendesk_data=zendesk_data,
                jira_data=jira_data,
                namespace=request.namespace
            )

            return {
                "status": "success",
                "account_id": request.sf_account_id,
                "time_range": request.time_range.dict(),
                "analysis": analysis
            }

    except Exception as e:
        logger.error(f"Error in customer health analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{account_id}", response_model=Dict[str, Any])
async def get_analysis_history(
    account_id: str,
    limit: int = 10,
    namespace: Optional[str] = None
):
    """Get historical analysis for an account"""
    try:
        # Here you would implement fetching historical analyses from your vector store
        # using the account_id and namespace
        pass
    except Exception as e:
        logger.error(f"Error fetching analysis history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
