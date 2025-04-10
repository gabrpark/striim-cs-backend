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
                    "As a senior support analyst, provide a clear and concise summary of this ticket. "
                    "Focus on:\n"
                    "- What's the core issue and its severity?\n"
                    "- What's being done to resolve it?\n"
                    "- How does this impact the customer?\n"
                    "- What are the immediate next steps?\n\n"
                    "Keep it brief and actionable. No markdown formatting."
                ),
                "jira_issue": (
                    "As a technical analyst, provide a clear summary of this Jira issue. "
                    "Focus on:\n"
                    "- Technical problem and its impact\n"
                    "- Current status and progress\n"
                    "- Related dependencies\n"
                    "- Next technical steps\n\n"
                    "Keep it technical but clear. No markdown formatting."
                ),
                "salesforce_account": (
                    "As a customer success analyst, provide a summary of this account. "
                    "Focus on:\n"
                    "- Account health and status\n"
                    "- Key business metrics\n"
                    "- Support history and patterns\n"
                    "- Strategic recommendations\n\n"
                    "Keep it business-focused and actionable. No markdown formatting."
                ),
                "all_tickets": (
                    "Analyze all support tickets for this period and provide:\n"
                    "1. Key trends and patterns\n"
                    "2. Common issues and their frequency\n"
                    "3. Overall support health indicators\n"
                    "4. Areas needing attention\n\n"
                    "Focus on actionable insights and patterns."
                ),
                "all_issues": (
                    "Analyze all technical issues and provide:\n"
                    "1. Technical trends and patterns\n"
                    "2. Common technical problems\n"
                    "3. System health indicators\n"
                    "4. Areas needing technical attention\n\n"
                    "Focus on technical insights and patterns."
                ),
                "all_accounts": (
                    "Analyze all accounts and provide:\n"
                    "1. Account health trends\n"
                    "2. Common business patterns\n"
                    "3. Overall customer success metrics\n"
                    "4. Strategic recommendations\n\n"
                    "Focus on business insights and patterns."
                ),
                "system_wide": (
                    "Provide a comprehensive system-wide analysis covering:\n"
                    "1. Overall system health and performance\n"
                    "2. Key metrics across all dimensions\n"
                    "3. Major trends and patterns\n"
                    "4. Strategic recommendations\n\n"
                    "Focus on high-level insights and actionable recommendations."
                ),
                "general": (
                    "Provide a clear and concise summary of the following data:\n"
                    "{text}\n\n"
                    "Focus on key points and actionable insights."
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
