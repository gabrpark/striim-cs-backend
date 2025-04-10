-- Create summaries table
CREATE TABLE IF NOT EXISTS summaries (
    id SERIAL PRIMARY KEY,
    summary_type VARCHAR(50) NOT NULL,
    summary TEXT NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    source_ids JSONB,
    source_summary_ids JSONB,
    query_params JSONB,
    date_range_start TIMESTAMP,
    date_range_end TIMESTAMP,
    metadata JSONB,
    last_generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    hash_signature TEXT,
    is_valid BOOLEAN DEFAULT true,
    hierarchy_level VARCHAR(20) NOT NULL DEFAULT 'individual',
    category VARCHAR(50),
    CONSTRAINT valid_hierarchy_level CHECK (hierarchy_level::text = ANY (ARRAY['individual'::character varying, 'group'::character varying, 'global'::character varying]::text[])),
    CONSTRAINT valid_category CHECK (category::text = ANY (ARRAY['zendesk'::character varying, 'jira'::character varying, 'salesforce'::character varying, 'system'::character varying]::text[])),
    CONSTRAINT unique_summary_params UNIQUE (summary_type, query_params, date_range_start, date_range_end)
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_summaries_type ON summaries(summary_type);
CREATE INDEX IF NOT EXISTS idx_summaries_dates ON summaries(date_range_start, date_range_end);
CREATE INDEX IF NOT EXISTS idx_summaries_valid ON summaries(is_valid);
CREATE INDEX IF NOT EXISTS idx_summaries_last_verified ON summaries(last_verified_at);
CREATE INDEX IF NOT EXISTS idx_summaries_type_date ON summaries(summary_type, date_range_start, date_range_end);
CREATE INDEX IF NOT EXISTS idx_summaries_params ON summaries USING GIN (query_params);
CREATE INDEX IF NOT EXISTS idx_summaries_source_ids ON summaries USING GIN (source_ids);
CREATE INDEX IF NOT EXISTS idx_summaries_hierarchy ON summaries(hierarchy_level);
CREATE INDEX IF NOT EXISTS idx_summaries_category ON summaries(category);

-- Create summary_relationships table
CREATE TABLE IF NOT EXISTS summary_relationships (
    id SERIAL PRIMARY KEY,
    parent_summary_id INTEGER NOT NULL REFERENCES summaries(id),
    child_summary_id INTEGER NOT NULL REFERENCES summaries(id),
    relationship_type VARCHAR(20) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(parent_summary_id, child_summary_id)
);

-- Create indexes for summary_relationships
CREATE INDEX IF NOT EXISTS idx_summary_relationships_parent ON summary_relationships(parent_summary_id);
CREATE INDEX IF NOT EXISTS idx_summary_relationships_child ON summary_relationships(child_summary_id);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_summaries_updated_at
    BEFORE UPDATE ON summaries
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_summary_relationships_updated_at
    BEFORE UPDATE ON summary_relationships
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column(); 