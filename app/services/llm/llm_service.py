from openai import AsyncOpenAI
from app.core.config import settings
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def generate_summary(self, text: str, summary_type: str = "general") -> str:
        """Generate a summary based on the type of analysis needed"""
        try:
            prompts = {
                "zendesk_ticket": (
                    "Provide an extremely concise summary of this support ticket in 2-3 sentences. "
                    "Then add 1-2 sentences with the most critical action or recommendation. "
                    "No headers, sections, or formatting. Just plain text."
                ),
                "jira_issue": (
                    "Provide an extremely concise summary of this Jira issue in 2-3 sentences. "
                    "Then add 1-2 sentences with the most critical action or recommendation. "
                    "No headers, sections, or formatting. Just plain text."
                ),
                "salesforce_account": (
                    "Provide an extremely concise summary of this account in 2-3 sentences. "
                    "Then add 1-2 sentences with the most critical action or recommendation. "
                    "No headers, sections, or formatting. Just plain text."
                ),
                "account_health": (
                    "Provide an extremely concise summary of this account's health in 2-3 sentences. "
                    "Then add 1-2 sentences with the most critical action or recommendation. "
                    "No headers, sections, or formatting. Just plain text."
                ),
                "all_tickets": (
                    "Provide an extremely concise summary of these support tickets in 2-3 sentences. "
                    "Then add 1-2 sentences with the most critical action or recommendation. "
                    "No headers, sections, or formatting. Just plain text."
                ),
                "all_issues": (
                    "Provide an extremely concise summary of these technical issues in 2-3 sentences. "
                    "Then add 1-2 sentences with the most critical action or recommendation. "
                    "No headers, sections, or formatting. Just plain text."
                ),
                "all_accounts": (
                    "Provide an extremely concise summary of these accounts in 2-3 sentences. "
                    "Then add 1-2 sentences with the most critical action or recommendation. "
                    "No headers, sections, or formatting. Just plain text."
                ),
                "system_wide": (
                    "Provide an extremely concise summary of the system-wide status in 2-3 sentences. "
                    "Then add 1-2 sentences with the most critical action or recommendation. "
                    "No headers, sections, or formatting. Just plain text."
                ),
                "general": (
                    "Provide an extremely concise summary in 2-3 sentences. "
                    "Then add 1-2 sentences with the most critical action or recommendation. "
                    "No headers, sections, or formatting. Just plain text."
                )
            }

            # Get the appropriate prompt, fallback to general if not found
            prompt = prompts.get(summary_type, prompts["general"])

            system_prompt = (
                "You are an experienced analyst writing for other team members. "
                "Be clear and direct. Avoid unnecessary formatting or headers. "
                "Focus on what's important and actionable. "
                "Write in a natural, professional tone."
            )

            response = await self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"{prompt}\n\n{text}"}
                ],
                max_tokens=300,
                temperature=0.3
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            raise

    async def generate_subscription_alert(self, context: Dict[str, Any]) -> str:
        """Generate analysis and recommendations for expiring subscription"""
        try:
            prompt = (
                "Analyze this expiring subscription and provide recommendations. Consider:\n"
                "1. Client's usage and engagement (based on ticket volume)\n"
                "2. Business value and account type\n"
                "3. Renewal risk factors\n"
                "4. Suggested actions for account management\n\n"
                "Keep it actionable and focused on retention strategy."
            )

            system_prompt = (
                "You are a customer success strategist helping to retain valuable clients. "
                "Provide clear, actionable insights for managing subscription renewals."
            )

            response = await self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"{prompt}\n\nContext:\n{context}"}
                ],
                max_tokens=300,
                temperature=0.3
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Error generating subscription alert: {str(e)}")
            raise


llm_service = LLMService()
