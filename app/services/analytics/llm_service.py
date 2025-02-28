from langchain_openai import ChatOpenAI
from langchain.schema import Document
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import ChatPromptTemplate
from app.core.config import settings
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import re

logger = logging.getLogger(__name__)


class CSMAnalyticsService:
    def __init__(self):
        self.llm = ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model_name="gpt-4-turbo-preview",  # Using GPT-4 for better analysis
            temperature=0.2  # Lower temperature for more consistent analysis
        )

        # Update the prompt to be more specific about scoring criteria
        self.analysis_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a CSM Analytics expert. Analyze the provided data and calculate scores based on these criteria:

            CSM Score (1-5):
            1: Minimal engagement, missed meetings, slow responses
            2: Inconsistent engagement, some delays in responses
            3: Regular engagement, standard response times
            4: Strong engagement, quick responses, proactive communication
            5: Excellent engagement, immediate responses, strategic partnership

            Health Score (1-10):
            - Support Health (0-3): Based on ticket volume, resolution times, and satisfaction
            - Project Health (0-4): Based on milestone completion and issue resolution
            - Relationship Health (0-3): Based on meeting frequency and engagement quality

            For each score, provide specific evidence from the data."""),
            ("human", """Time Range: {time_range}
            
            Salesforce Activity:
            {salesforce_data}
            
            Support Tickets:
            {zendesk_data}
            
            Project Status:
            {jira_data}
            
            Provide:
            1. Detailed score breakdown with evidence
            2. Key trends and patterns
            3. Risk factors
            4. Recommendations""")
        ])

    async def analyze_customer_health(
        self,
        time_range: Dict[str, datetime],
        account_id: str,
        salesforce_data: List[Dict],
        zendesk_data: List[Dict],
        jira_data: List[Dict],
        namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze customer health based on multiple data sources
        """
        try:
            # Get account details
            account = salesforce_data[0] if salesforce_data else {}

            # Add account context to the analysis
            formatted_data = {
                "time_range": f"From {time_range['start']} to {time_range['end']}",
                "account_context": f"""
                    Account: {account.get('account_name')}
                    Business Case: {account.get('business_use_case')}
                    Territory: {account.get('territory')}
                    Account Type: {account.get('type')}
                """,
                "salesforce_data": self._format_salesforce_data(salesforce_data),
                "zendesk_data": self._format_zendesk_data(zendesk_data),
                "jira_data": self._format_jira_data(jira_data)
            }

            # Get analysis from LLM
            response = await self.llm.ainvoke(
                self.analysis_prompt.format_messages(**formatted_data)
            )

            # Parse the response and extract scores
            analysis = self._parse_analysis(response.content)

            # Store the analysis in vector database with namespace
            await self._store_analysis(analysis, namespace)

            return analysis

        except Exception as e:
            logger.error(f"Error in customer health analysis: {str(e)}")
            raise

    def _format_salesforce_data(self, data: List[Dict]) -> str:
        """Format Salesforce account data for analysis"""
        formatted = []
        for account in data:
            account_info = [
                f"Account: {account.get('account_name')} ({account.get('type')})",
                f"Owner: {account.get('account_owner_name')}",
                f"Business Case: {account.get('business_use_case')}",
                f"Territory: {account.get('territory')}",
                f"Target Upsell: ${account.get('target_upsell_value', 0):,.2f}",
                f"Account Type: {'Target Account' if account.get('is_target_account') else 'Regular'}",
                f"Migration Status: {'Migration Account' if account.get('is_migration_account') else 'N/A'}"
            ]
            formatted.append("\n  ".join(account_info))
        return "\n\n".join(formatted)

    def _format_zendesk_data(self, data: List[Dict]) -> str:
        """Format Zendesk ticket data for analysis"""
        # Group tickets by priority for better analysis
        tickets_by_priority = {}
        for ticket in data:
            priority = ticket.get('priority', 'Unknown')
            if priority not in tickets_by_priority:
                tickets_by_priority[priority] = []
            tickets_by_priority[priority].append(ticket)

        formatted = []
        for priority, tickets in tickets_by_priority.items():
            section = [f"Priority {priority} Tickets ({len(tickets)}):\n"]
            for ticket in tickets:
                ticket_info = [
                    f"- Ticket #{ticket.get('zd_ticket_id')}: {ticket.get('ticket_subject')}",
                    f"  Type: {ticket.get('ticket_type')}",
                    f"  Status: {ticket.get('status')}",
                    f"  Component: {ticket.get('product_component')}",
                    f"  Environment: {ticket.get('environment')}",
                    f"  Response Time: {self._calculate_response_time(ticket)}"
                ]
                section.append("\n".join(ticket_info))
            formatted.append("\n".join(section))
        return "\n\n".join(formatted)

    def _format_jira_data(self, data: List[Dict]) -> str:
        """Format Jira issue data for analysis"""
        # Group issues by type and status
        issues_by_type = {}
        for issue in data:
            issue_type = issue.get('issue_type', 'Unknown')
            if issue_type not in issues_by_type:
                issues_by_type[issue_type] = []
            issues_by_type[issue_type].append(issue)

        formatted = []
        for type_name, issues in issues_by_type.items():
            section = [f"{type_name} Issues ({len(issues)}):\n"]
            for issue in issues:
                issue_info = [
                    f"- {issue.get('jira_issue_id')}: {issue.get('issue_summary')}",
                    f"  Status: {issue.get('issue_status')}",
                    f"  Priority: {issue.get('priority')}",
                    f"  Assignee: {issue.get('assignee_name')}",
                    f"  Age: {self._calculate_issue_age(issue)}"
                ]
                if issue.get('linked_zendesk_ticket'):
                    issue_info.append(
                        f"  Linked Ticket: #{issue.get('linked_zendesk_ticket')}")
                section.append("\n".join(issue_info))
            formatted.append("\n".join(section))
        return "\n\n".join(formatted)

    def _calculate_response_time(self, ticket: Dict) -> str:
        """Calculate response time for Zendesk tickets"""
        created = ticket.get('source_created_at')
        updated = ticket.get('source_updated_at')
        if created and updated:
            delta = updated - created
            hours = delta.total_seconds() / 3600
            return f"{hours:.1f} hours"
        return "N/A"

    def _calculate_issue_age(self, issue: Dict) -> str:
        """Calculate age of Jira issues"""
        created = issue.get('source_created_at')
        if created:
            delta = datetime.now() - created
            days = delta.days
            return f"{days} days"
        return "N/A"

    def _parse_analysis(self, content: str) -> Dict[str, Any]:
        """Parse LLM response and extract structured data"""
        # Here you would implement logic to parse the LLM response
        # and extract scores and key points
        return {
            "summary": content,
            "csm_score": self._extract_csm_score(content),
            "health_score": self._extract_health_score(content),
            "key_findings": self._extract_key_findings(content),
            "recommendations": self._extract_recommendations(content)
        }

    def _extract_csm_score(self, content: str) -> Dict[str, Any]:
        """Extract CSM score and evidence from analysis"""
        try:
            # Use regex or string parsing to extract the score
            # This is a simplified example
            score_pattern = r"CSM Score:\s*(\d+)"
            evidence_pattern = r"CSM Evidence:(.*?)(?=\n\n|\Z)"

            score_match = re.search(score_pattern, content)
            evidence_match = re.search(evidence_pattern, content, re.DOTALL)

            return {
                "score": int(score_match.group(1)) if score_match else 0,
                "evidence": evidence_match.group(1).strip() if evidence_match else ""
            }
        except Exception as e:
            logger.error(f"Error extracting CSM score: {str(e)}")
            return {"score": 0, "evidence": "Score extraction failed"}

    def _extract_health_score(self, content: str) -> Dict[str, Any]:
        """Extract health score components and evidence"""
        try:
            patterns = {
                "support": r"Support Health:\s*(\d+)",
                "project": r"Project Health:\s*(\d+)",
                "relationship": r"Relationship Health:\s*(\d+)"
            }

            scores = {}
            for component, pattern in patterns.items():
                match = re.search(pattern, content)
                scores[component] = int(match.group(1)) if match else 0

            return {
                "total": sum(scores.values()),
                "components": scores,
                "evidence": self._extract_section(content, "Health Evidence:")
            }
        except Exception as e:
            logger.error(f"Error extracting health score: {str(e)}")
            return {"total": 0, "components": {}, "evidence": "Score extraction failed"}

    def _extract_key_findings(self, content: str) -> List[str]:
        """Extract key findings from analysis"""
        try:
            findings_section = self._extract_section(
                content, "Key trends and patterns:")
            findings = re.findall(
                r"[-•]\s*(.*?)(?=\n[-•]|\Z)", findings_section, re.DOTALL)
            return [finding.strip() for finding in findings if finding.strip()]
        except Exception as e:
            logger.error(f"Error extracting key findings: {str(e)}")
            return []

    def _extract_recommendations(self, content: str) -> List[str]:
        """Extract recommendations from analysis"""
        try:
            recommendations_section = self._extract_section(
                content, "Recommendations:")
            recommendations = re.findall(
                r"[-•]\s*(.*?)(?=\n[-•]|\Z)", recommendations_section, re.DOTALL)
            return [rec.strip() for rec in recommendations if rec.strip()]
        except Exception as e:
            logger.error(f"Error extracting recommendations: {str(e)}")
            return []

    def _extract_section(self, content: str, section_header: str) -> str:
        """Helper method to extract a section from the content"""
        try:
            pattern = f"{section_header}(.*?)(?=\n\n|\Z)"
            match = re.search(pattern, content, re.DOTALL)
            return match.group(1).strip() if match else ""
        except Exception:
            return ""

    async def _store_analysis(self, analysis: Dict[str, Any], namespace: Optional[str] = None):
        """Store analysis in vector database"""
        try:
            # Create a combined text for vectorization
            text_for_vectorization = f"""
            Time Period: {analysis.get('time_range')}
            CSM Score: {analysis['csm_score']['score']}
            Health Score: {analysis['health_score']['total']}
            Key Findings: {' '.join(analysis['key_findings'])}
            Recommendations: {' '.join(analysis['recommendations'])}
            """

            # Here you would:
            # 1. Generate embeddings for the text
            # 2. Store in Pinecone with metadata
            # 3. Include timestamps and scores in metadata
            pass
        except Exception as e:
            logger.error(f"Error storing analysis: {str(e)}")
            raise


# Create a global instance
csm_analytics = CSMAnalyticsService()
