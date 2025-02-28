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
                "ticket_comprehensive": (
                    "As a senior support analyst, provide a clear and concise summary of this ticket. "
                    "Focus on:\n"
                    "- What's the core issue and its severity?\n"
                    "- What's being done to resolve it?\n"
                    "- How does this impact the customer?\n"
                    "- What are the immediate next steps?\n\n"
                    "Keep it brief and actionable. No markdown formatting."
                ),
                "account_health": (
                    "Provide a brief assessment of this customer's health focusing on:\n"
                    "- Current status and key concerns\n"
                    "- Support ticket patterns\n"
                    "- Technical issues impact\n"
                    "- Recommended actions\n\n"
                    "Be concise and highlight what needs attention."
                )
            }

            system_prompt = (
                "You are an experienced customer support analyst writing for other support staff. "
                "Be clear and direct. Avoid unnecessary formatting or headers. "
                "Focus on what's important and actionable. "
                "Write in a natural, professional tone."
            )

            response = await self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",
                     "content": f"{prompts[summary_type]}\n\n{text}"}
                ],
                max_tokens=300,
                temperature=0.3
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            raise


llm_service = LLMService()
