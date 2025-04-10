-- Add indexes for better summary querying
CREATE INDEX IF NOT EXISTS idx_summaries_type_date ON summaries(summary_type, date_range_start, date_range_end);
CREATE INDEX IF NOT EXISTS idx_summaries_params ON summaries USING gin (query_params);
CREATE INDEX IF NOT EXISTS idx_summaries_source_ids ON summaries USING gin (source_ids); 