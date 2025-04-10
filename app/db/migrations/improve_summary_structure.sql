-- Add hierarchy level to clearly indicate summary level
ALTER TABLE summaries ADD COLUMN IF NOT EXISTS hierarchy_level VARCHAR(20) NOT NULL DEFAULT 'individual';
ALTER TABLE summaries ADD CONSTRAINT valid_hierarchy_level 
    CHECK (hierarchy_level IN ('individual', 'group', 'global'));

-- Add parent category for better organization
ALTER TABLE summaries ADD COLUMN IF NOT EXISTS category VARCHAR(50);
ALTER TABLE summaries ADD CONSTRAINT valid_category 
    CHECK (category IN ('zendesk', 'jira', 'salesforce', 'system'));

-- Create view for easier querying of hierarchy
CREATE OR REPLACE VIEW hierarchical_summaries AS
WITH RECURSIVE summary_tree AS (
    -- Base case: get all individual summaries
    SELECT 
        s.id,
        s.summary_type,
        s.summary,
        s.hierarchy_level,
        s.category,
        s.date_range_start,
        s.date_range_end,
        s.last_generated_at,
        1 as level,
        ARRAY[s.id] as path
    FROM summaries s
    WHERE s.hierarchy_level = 'individual'
    
    UNION ALL
    
    -- Recursive case: get parent summaries
    SELECT 
        s.id,
        s.summary_type,
        s.summary,
        s.hierarchy_level,
        s.category,
        s.date_range_start,
        s.date_range_end,
        s.last_generated_at,
        st.level + 1,
        st.path || s.id
    FROM summaries s
    JOIN summary_relationships sr ON s.id = sr.parent_summary_id
    JOIN summary_tree st ON sr.child_summary_id = st.id
)
SELECT * FROM summary_tree;

-- Add indexes for the new columns
CREATE INDEX idx_summaries_hierarchy ON summaries(hierarchy_level);
CREATE INDEX idx_summaries_category ON summaries(category); 