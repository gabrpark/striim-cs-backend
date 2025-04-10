from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import hashlib
import json
from app.services.database.database import db
from app.services.llm.llm_service import llm_service
import logging

logger = logging.getLogger(__name__)


class SummaryService:
    SUMMARY_TYPES = {
        'ticket': {
            'level': 1,
            'ttl_hours': 24,  # Time-to-live before recheck
            'dependencies': []
        },
        'multi_ticket': {
            'level': 2,
            'ttl_hours': 48,
            'dependencies': ['ticket']
        },
        'company': {
            'level': 3,
            'ttl_hours': 72,
            'dependencies': ['ticket', 'multi_ticket']
        },
        'multi_company': {
            'level': 4,
            'ttl_hours': 96,
            'dependencies': ['company']
        }
    }

    async def get_or_generate_summary(
        self,
        summary_type: str,
        params: Dict[str, Any],
        force_regenerate: bool = False
    ) -> Dict[str, Any]:
        """Get existing summary or generate new one if needed"""
        try:
            if not force_regenerate:
                existing_summary = await self.get_valid_summary(summary_type, params)
                if existing_summary:
                    return existing_summary

            return await self.generate_summary(summary_type, params)

        except Exception as e:
            logger.error(f"Error in get_or_generate_summary: {str(e)}")
            raise

    async def get_valid_summary(self, summary_type: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get existing valid summary if available"""
        query = """
            SELECT * FROM summaries 
            WHERE summary_type = $1 
            AND query_params = $2
            AND is_valid = true
            AND date_range_start = $3
            AND date_range_end = $4
        """
        summary = await db.fetchrow(
            query,
            summary_type,
            json.dumps(params.get('filters', {})),
            params.get('date_range_start'),
            params.get('date_range_end')
        )

        if summary and await self.is_summary_valid(summary):
            return dict(summary)
        return None

    async def is_summary_valid(self, summary: Dict[str, Any]) -> bool:
        """Check if summary is still valid based on source data"""
        # Check TTL
        ttl_hours = self.SUMMARY_TYPES[summary['summary_type']]['ttl_hours']
        if datetime.now() - summary['last_verified_at'] > timedelta(hours=ttl_hours):
            # Verify source data hasn't changed
            current_hash = await self.calculate_source_data_hash(
                summary['source_ids'],
                summary['summary_type']
            )
            if current_hash != summary['hash_signature']:
                await self.invalidate_summary(summary['id'])
                return False

            # Update last_verified_at
            await self.update_verification_time(summary['id'])

        return True

    async def generate_summary(
        self,
        summary_type: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate new summary based on type and parameters"""
        source_data = await self.get_source_data(summary_type, params)

        # Determine if we should use raw data or existing summaries
        use_raw_data = params.get('use_raw_data', True)
        if use_raw_data:
            summary_text = await self.generate_from_raw_data(summary_type, source_data)
        else:
            summary_text = await self.generate_from_summaries(summary_type, source_data)

        # Calculate hash of source data
        hash_signature = await self.calculate_source_data_hash(
            source_data['ids'],
            summary_type
        )

        # Store new summary
        return await self.store_summary(
            summary_type=summary_type,
            summary_text=summary_text,
            source_type='raw_data' if use_raw_data else 'existing_summaries',
            source_ids=source_data['ids'],
            source_summary_ids=source_data.get('summary_ids'),
            query_params=params,
            hash_signature=hash_signature,
            metadata=await self.calculate_metadata(source_data, summary_type)
        )

    async def calculate_source_data_hash(self, source_ids: List[str], summary_type: str) -> str:
        """Calculate hash of source data to detect changes"""
        # Implementation depends on summary_type and data structure
        # This is a simplified example
        data = []
        if summary_type == 'ticket':
            for ticket_id in source_ids:
                ticket = await db.fetchrow(
                    "SELECT * FROM zendesk_tickets WHERE zd_ticket_id = $1",
                    ticket_id
                )
                if ticket:
                    data.append(dict(ticket))

        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    async def invalidate_summary(self, summary_id: int) -> None:
        """Invalidate summary and its dependents"""
        async with db.transaction():
            # Invalidate this summary
            await db.execute(
                "UPDATE summaries SET is_valid = false WHERE id = $1",
                summary_id
            )

            # Invalidate dependent summaries
            dependent_summaries = await db.fetch("""
                WITH RECURSIVE dependents AS (
                    SELECT child_summary_id
                    FROM summary_relationships
                    WHERE parent_summary_id = $1
                    UNION
                    SELECT sr.child_summary_id
                    FROM summary_relationships sr
                    INNER JOIN dependents d ON sr.parent_summary_id = d.child_summary_id
                )
                SELECT DISTINCT child_summary_id FROM dependents
            """, summary_id)

            if dependent_summaries:
                await db.execute(
                    "UPDATE summaries SET is_valid = false WHERE id = ANY($1)",
                    [s['child_summary_id'] for s in dependent_summaries]
                )

    async def store_summary(
        self,
        summary_type: str,
        summary_text: str,
        source_type: str,
        source_ids: List[str],
        source_summary_ids: Optional[List[int]],
        query_params: Dict[str, Any],
        hash_signature: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Store a new summary or update existing one"""
        try:
            async with db.transaction():
                # Insert or update summary
                query = """
                    INSERT INTO summaries (
                        summary_type, summary, source_type, source_ids,
                        source_summary_ids, query_params, date_range_start,
                        date_range_end, metadata, hash_signature
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    ON CONFLICT (summary_type, query_params, date_range_start, date_range_end)
                    DO UPDATE SET
                        summary = EXCLUDED.summary,
                        source_type = EXCLUDED.source_type,
                        source_ids = EXCLUDED.source_ids,
                        source_summary_ids = EXCLUDED.source_summary_ids,
                        metadata = EXCLUDED.metadata,
                        hash_signature = EXCLUDED.hash_signature,
                        last_generated_at = CURRENT_TIMESTAMP,
                        last_verified_at = CURRENT_TIMESTAMP,
                        is_valid = true
                    RETURNING *
                """
                summary = await db.fetchrow(
                    query,
                    summary_type,
                    summary_text,
                    source_type,
                    json.dumps(source_ids),
                    json.dumps(
                        source_summary_ids) if source_summary_ids else None,
                    json.dumps(query_params),
                    query_params.get('date_range_start'),
                    query_params.get('date_range_end'),
                    json.dumps(metadata),
                    hash_signature
                )

                # Store relationships if using existing summaries
                if source_summary_ids:
                    await self.store_summary_relationships(summary['id'], source_summary_ids)

                return dict(summary)

        except Exception as e:
            logger.error(f"Error storing summary: {str(e)}")
            raise

    async def store_summary_relationships(self, parent_id: int, child_ids: List[int]) -> None:
        """Store relationships between summaries"""
        try:
            # Clear existing relationships
            await db.execute(
                "DELETE FROM summary_relationships WHERE parent_summary_id = $1",
                parent_id
            )

            # Insert new relationships
            for child_id in child_ids:
                await db.execute("""
                    INSERT INTO summary_relationships (
                        parent_summary_id, child_summary_id, relationship_type
                    ) VALUES ($1, $2, $3)
                """, parent_id, child_id, 'aggregation')

        except Exception as e:
            logger.error(f"Error storing summary relationships: {str(e)}")
            raise

    async def update_verification_time(self, summary_id: int) -> None:
        """Update the last_verified_at timestamp"""
        try:
            await db.execute(
                "UPDATE summaries SET last_verified_at = CURRENT_TIMESTAMP WHERE id = $1",
                summary_id
            )
        except Exception as e:
            logger.error(f"Error updating verification time: {str(e)}")
            raise

    async def get_source_data(self, summary_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get source data based on summary type and parameters"""
        try:
            if summary_type == 'ticket':
                return await self.get_ticket_data(params['ticket_id'])
            elif summary_type == 'multi_ticket':
                return await self.get_multi_ticket_data(params)
            elif summary_type == 'company':
                return await self.get_company_data(params)
            elif summary_type == 'multi_company':
                return await self.get_multi_company_data(params)
            else:
                raise ValueError(f"Unsupported summary type: {summary_type}")

        except Exception as e:
            logger.error(f"Error getting source data: {str(e)}")
            raise

    async def generate_from_raw_data(self, summary_type: str, source_data: Dict[str, Any]) -> str:
        """Generate summary from raw data using LLM"""
        try:
            # Format data based on summary type
            formatted_data = self.format_data_for_llm(
                source_data, summary_type)

            # Generate summary using LLM service
            return await llm_service.generate_summary(
                text=formatted_data,
                summary_type=summary_type
            )

        except Exception as e:
            logger.error(f"Error generating summary from raw data: {str(e)}")
            raise

    async def generate_from_summaries(self, summary_type: str, source_data: Dict[str, Any]) -> str:
        """Generate summary from existing summaries using LLM"""
        try:
            # Get existing summaries
            existing_summaries = [
                summary['summary'] for summary in source_data.get('summaries', [])
            ]

            # Combine summaries with any additional context
            context = {
                'summaries': existing_summaries,
                'metadata': source_data.get('metadata', {}),
                'type': summary_type
            }

            # Generate new summary using LLM service
            return await llm_service.generate_summary(
                text=json.dumps(context),
                summary_type=f"{summary_type}_aggregate"
            )

        except Exception as e:
            logger.error(f"Error generating summary from summaries: {str(e)}")
            raise

    def format_data_for_llm(self, data: Dict[str, Any], summary_type: str) -> str:
        """Format data for LLM consumption based on summary type"""
        # Implementation will depend on data structure and summary type
        return json.dumps(data)


summary_service = SummaryService()
