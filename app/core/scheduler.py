from fastapi import FastAPI
from fastapi_utils.tasks import repeat_every
from app.services.notifications.subscription_service import SubscriptionNotificationService
import logging

logger = logging.getLogger(__name__)
subscription_service = SubscriptionNotificationService()


def setup_scheduler(app: FastAPI):
    @app.on_event("startup")
    @repeat_every(seconds=60 * 60 * 24)  # Run once per day
    async def check_subscriptions():
        logger.info("Running scheduled subscription check...")
        await subscription_service.check_expiring_subscriptions()
        logger.info("Scheduled subscription check completed")
