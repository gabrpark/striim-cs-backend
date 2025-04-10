from datetime import datetime, timedelta, date
from app.services.database.database import db
from app.services.llm.llm_service import llm_service
import logging
from typing import Dict, Any
import sys

logger = logging.getLogger(__name__)


class SubscriptionNotificationService:
    def __init__(self):
        # Update thresholds to include longer periods
        self.notification_thresholds = {
            'critical': timedelta(days=30),     # 1 month left
            'warning': timedelta(days=180),     # 6 months left
            'notice': timedelta(days=730)       # 2 years left
        }

    def get_priority(self, days_left: int, arr: float) -> str:
        """Determine notification priority based on days left and ARR"""
        if days_left <= 30:
            return "high"
        elif days_left <= 180 and arr > 100000:  # High-value accounts within 6 months
            return "high"
        elif days_left <= 180:
            return "medium"
        else:
            return "low"

    async def check_expiring_subscriptions(self):
        """Check for subscriptions expiring in the next 2 years"""
        try:
            # Get all active subscriptions with client and service info
            subs = await db.fetch("""
                SELECT 
                    s.subscription_id, s.client_id, s.status, s.end_date, s.amount,
                    c.name as client_name,
                    srv.name as service_name,
                    c.arr
                FROM subscriptions s
                JOIN clients c ON s.client_id = c.id
                JOIN services srv ON s.service_id = srv.service_id
                WHERE s.status = 'Active'
            """)

            print(f"\nProcessing {len(subs)} active subscriptions", flush=True)

            for sub in subs:
                days_until_expiry = (
                    sub['end_date'] - datetime.now().date()).days

                # Check if notification already exists
                existing = await db.fetchval("""
                    SELECT COUNT(*) FROM notifications
                    WHERE subscription_id = $1
                    AND type = 'subscription_expiring'
                    AND created_at >= NOW() - INTERVAL '30 days'
                """, sub['subscription_id'])

                if existing == 0:  # Create new notification if none exists
                    priority = self.get_priority(
                        days_until_expiry, float(sub['arr'] or 0))

                    # Insert notification
                    await db.execute("""
                        INSERT INTO notifications (
                            client_id, subscription_id, type, priority,
                            title, message, is_read, created_at
                        ) VALUES (
                            $1, $2, $3, $4, $5, $6, false, NOW()
                        )
                    """,
                                     sub['client_id'],
                                     sub['subscription_id'],
                                     'subscription_expiring',
                                     priority,
                                     f"Subscription expires in {days_until_expiry} days",
                                     f"Subscription for {sub['client_name']} ({sub['service_name']}) expires on {sub['end_date']}. Amount: ${sub['amount']}")

                    print(
                        f"Created notification for {sub['subscription_id']}", flush=True)

            print("Subscription check completed", flush=True)

        except Exception as e:
            logger.error(f"Error checking expiring subscriptions: {str(e)}")
            raise
