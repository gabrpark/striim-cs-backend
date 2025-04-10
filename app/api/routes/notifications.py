from fastapi import APIRouter, HTTPException, Query
from app.services.database.database import db
from typing import Optional, List
import logging
from pydantic import BaseModel
from datetime import datetime
from app.services.notifications.subscription_service import SubscriptionNotificationService

router = APIRouter()
logger = logging.getLogger(__name__)

subscription_service = SubscriptionNotificationService()


class NotificationResponse(BaseModel):
    id: int
    type: str
    priority: str
    title: str
    message: str
    llm_analysis: Optional[str]
    created_at: datetime
    is_read: bool
    client_name: str
    subscription_end_date: Optional[datetime]
    subscription_amount: Optional[float]
    service_id: Optional[str]


@router.get("/notifications")
async def get_notifications(
    client_id: Optional[str] = None,
    type: Optional[str] = None,
    unread_only: bool = False
):
    """Get notifications with optional filters"""
    try:
        conditions = ["1=1"]
        params = []
        param_count = 1

        if client_id:
            conditions.append(f"client_id = ${param_count}")
            params.append(client_id)
            param_count += 1

        if type:
            conditions.append(f"type = ${param_count}")
            params.append(type)
            param_count += 1

        if unread_only:
            conditions.append("is_read = false")

        query = f"""
            SELECT n.*, 
                   c.name as client_name,
                   s.service_id,
                   s.end_date
            FROM notifications n
            JOIN clients c ON n.client_id = c.id
            LEFT JOIN subscriptions s ON n.subscription_id = s.subscription_id
            WHERE {" AND ".join(conditions)}
            ORDER BY n.created_at DESC
        """

        notifications = await db.fetch(query, *params)

        return {
            "status": "success",
            "count": len(notifications),
            "notifications": notifications
        }

    except Exception as e:
        logger.error(f"Error fetching notifications: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notifications/{notification_id}/mark-read")
async def mark_notification_read(notification_id: int):
    """Mark a notification as read"""
    try:
        query = """
            UPDATE notifications
            SET is_read = true
            WHERE id = $1
            RETURNING *
        """
        result = await db.fetchrow(query, notification_id)

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Notification {notification_id} not found"
            )

        return {"status": "success", "notification": result}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking notification as read: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/notifications/summary")
async def get_notifications_summary():
    """Get a summary of notifications grouped by type and priority"""
    try:
        query = """
            SELECT 
                type,
                priority,
                COUNT(*) as count,
                COUNT(CASE WHEN NOT is_read THEN 1 END) as unread_count,
                json_agg(json_build_object(
                    'id', id,
                    'title', title,
                    'message', message,
                    'llm_analysis', llm_analysis,
                    'created_at', created_at,
                    'is_read', is_read,
                    'client_name', c.name,
                    'subscription_end_date', s.end_date
                ) ORDER BY created_at DESC) as notifications
            FROM notifications n
            JOIN clients c ON n.client_id = c.id
            LEFT JOIN subscriptions s ON n.subscription_id = s.subscription_id
            GROUP BY type, priority
            ORDER BY 
                CASE priority
                    WHEN 'high' THEN 1
                    WHEN 'medium' THEN 2
                    WHEN 'low' THEN 3
                END,
                unread_count DESC
        """
        results = await db.fetch(query)

        return {
            "status": "success",
            "notifications": results
        }

    except Exception as e:
        logger.error(f"Error fetching notifications summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/notifications/dashboard")
async def get_dashboard_notifications():
    """Get notifications organized for dashboard display"""
    try:
        # Get high-priority subscription notifications
        subscription_query = """
            SELECT 
                n.id,
                n.type,
                n.priority,
                n.title,
                n.message,
                n.llm_analysis,
                n.created_at,
                n.is_read,
                c.name as client_name,
                c.arr as client_arr,
                s.end_date as subscription_end_date,
                s.amount as subscription_amount,
                s.service_id,
                (
                    SELECT COUNT(*) 
                    FROM zendesk_tickets zt 
                    WHERE zt.client_id = c.id 
                    AND zt.source_created_at >= NOW() - INTERVAL '3 months'
                ) as recent_ticket_count
            FROM notifications n
            JOIN clients c ON n.client_id = c.id
            JOIN subscriptions s ON n.subscription_id = s.subscription_id
            WHERE n.type = 'subscription_expiring'
            AND n.priority = 'high'
            AND NOT n.is_read
            ORDER BY s.end_date ASC
        """

        expiring_subscriptions = await db.fetch(subscription_query)

        return {
            "status": "success",
            "data": {
                "expiring_subscriptions": {
                    "count": len(expiring_subscriptions),
                    "items": expiring_subscriptions
                }
            },
            "metadata": {
                "total_arr_at_risk": sum(sub['client_arr'] for sub in expiring_subscriptions),
                "earliest_expiration": min((sub['subscription_end_date'] for sub in expiring_subscriptions), default=None),
                # Add more types as needed
                "notification_types": ["subscription_expiring"]
            }
        }

    except Exception as e:
        logger.error(f"Error fetching dashboard notifications: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/notifications/client/{client_id}")
async def get_client_notifications(
    client_id: str,
    include_read: bool = False,
    limit: int = 10
):
    """Get notifications for a specific client"""
    try:
        query = """
            SELECT 
                n.*,
                s.end_date as subscription_end_date,
                s.amount as subscription_amount,
                s.service_id
            FROM notifications n
            LEFT JOIN subscriptions s ON n.subscription_id = s.subscription_id
            WHERE n.client_id = $1
            AND ($2 OR NOT n.is_read)
            ORDER BY n.created_at DESC
            LIMIT $3
        """

        notifications = await db.fetch(query, client_id, include_read, limit)

        return {
            "status": "success",
            "client_id": client_id,
            "notifications": notifications
        }

    except Exception as e:
        logger.error(f"Error fetching client notifications: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/notifications/api", response_model=List[NotificationResponse])
async def get_notifications_api(
    client_id: Optional[str] = None,
    type: Optional[str] = Query(
        None, description="Notification type (e.g., 'subscription_expiring')"),
    priority: Optional[str] = Query(
        None, description="Priority level (high, medium, low)"),
    unread_only: bool = Query(
        False, description="Only return unread notifications"),
    limit: int = Query(
        50, le=100, description="Maximum number of notifications to return")
):
    """
    Get notifications with flexible filtering options.

    This endpoint is designed for API consumers and provides:
    - Detailed notification data
    - Flexible filtering
    - Pagination support
    - Consistent response format

    Example usage:
    ```
    GET /api/v1/notifications/api?client_id=123&type=subscription_expiring&unread_only=true
    ```
    """
    try:
        conditions = ["1=1"]
        params = []
        param_count = 1

        if client_id:
            conditions.append(f"n.client_id = ${param_count}")
            params.append(client_id)
            param_count += 1

        if type:
            conditions.append(f"n.type = ${param_count}")
            params.append(type)
            param_count += 1

        if priority:
            conditions.append(f"n.priority = ${param_count}")
            params.append(priority)
            param_count += 1

        if unread_only:
            conditions.append("NOT n.is_read")

        query = f"""
            SELECT 
                n.*,
                c.name as client_name,
                s.end_date as subscription_end_date,
                s.amount as subscription_amount,
                s.service_id
            FROM notifications n
            JOIN clients c ON n.client_id = c.id
            LEFT JOIN subscriptions s ON n.subscription_id = s.subscription_id
            WHERE {" AND ".join(conditions)}
            ORDER BY n.created_at DESC
            LIMIT $${param_count}
        """
        params.append(limit)

        notifications = await db.fetch(query, *params)

        return notifications

    except Exception as e:
        logger.error(f"Error in notifications API: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notifications/check-subscriptions", tags=["notifications"])
async def trigger_subscription_check():
    """
    Manually trigger subscription check to create notifications for expiring subscriptions.
    This will check all subscriptions expiring within 2 years and create notifications
    if they don't already have recent notifications.
    """
    try:
        await subscription_service.check_expiring_subscriptions()

        # Get the newly created notifications
        query = """
            SELECT 
                n.*,
                c.name as client_name,
                s.end_date,
                s.amount as subscription_amount,
                srv.name as service_name
            FROM notifications n
            JOIN clients c ON n.client_id = c.id
            JOIN subscriptions s ON n.subscription_id = s.subscription_id
            JOIN services srv ON s.service_id = srv.service_id
            WHERE n.type = 'subscription_expiring'
            AND n.created_at >= NOW() - INTERVAL '5 minutes'
            ORDER BY n.priority DESC, n.created_at DESC
        """

        new_notifications = await db.fetch(query)

        return {
            "status": "success",
            "message": f"Created {len(new_notifications)} new notifications",
            "notifications": new_notifications
        }

    except Exception as e:
        logger.error(f"Error in subscription check: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check subscriptions: {str(e)}"
        )
