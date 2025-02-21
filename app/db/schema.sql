-- 1. Clean up existing tables (if you want a fresh start).
--    The CASCADE ensures dependent objects (like foreign keys) are dropped too.
DROP TABLE IF EXISTS zendesk_jira_links CASCADE;
DROP TABLE IF EXISTS jira_issues CASCADE;
DROP TABLE IF EXISTS zendesk_tickets CASCADE;
DROP TABLE IF EXISTS salesforce_accounts CASCADE;

-- 2. Create the 'salesforce_accounts' table
CREATE TABLE IF NOT EXISTS salesforce_accounts (
    sf_account_id         VARCHAR(50) PRIMARY KEY,  -- Unique Salesforce ID (e.g. 15/18 chars)
    account_owner_name    VARCHAR(100),             -- e.g., "John Smith"
    account_owner_email   VARCHAR(255),             -- Optional: email of the account owner
    deal_room_link        VARCHAR(255),             -- GDrive or other shared folder link
    account_name          VARCHAR(255) NOT NULL,    -- e.g., "Park IT"
    company_name          VARCHAR(255),             -- could match account_name or differ
    business_use_case     TEXT,                     -- e.g., "MS SQL -> Snowflake for analytics"
    parent_account_id     VARCHAR(50),              -- reference to another SF account if needed
    target_upsell_value   DECIMAL(15,2),            -- e.g., 50000.00
    account_record_type   VARCHAR(50),              -- e.g., "Customer Account"
    type                  VARCHAR(50),              -- e.g., "Customer," "Partner"
    is_target_account     BOOLEAN DEFAULT FALSE,
    is_migration_account  BOOLEAN DEFAULT FALSE,
    territory             VARCHAR(100),             -- e.g., "US West"
    sf_last_updated_at    TIMESTAMP,                -- last updated from Salesforce side
    description           TEXT,
    created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Create the 'zendesk_tickets' table
CREATE TABLE IF NOT EXISTS zendesk_tickets (
    zd_ticket_id       BIGINT PRIMARY KEY,          -- Unique Zendesk ticket ID
    requester_name     VARCHAR(100),                -- Person who opened the ticket
    requester_email    VARCHAR(255),                -- Optional: email of requester
    assignee_name      VARCHAR(100),                -- Support engineer assigned
    assignee_email     VARCHAR(255),                -- Optional: email of assignee
    ticket_subject     VARCHAR(255),                -- Short subject line
    ticket_type        VARCHAR(50),                 -- e.g., "Problem," "Incident"
    priority           VARCHAR(50),                 -- e.g., "High," "Medium," "Low"
    status             VARCHAR(50),                 -- e.g., "Open," "Pending," "Solved"
    product_version    VARCHAR(50),
    product_component  VARCHAR(100),
    node_count         INT,
    environment        VARCHAR(50),                 -- e.g., "Prod," "Staging"
    linked_jira_issues VARCHAR(255),                -- Comma-separated JIRA keys (optional approach)
    ticket_description TEXT,                        -- Detailed description
    source_created_at  TIMESTAMP,                   -- Original create time from Zendesk
    source_updated_at  TIMESTAMP,                   -- Last update time from Zendesk
    created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    -- Optionally reference a Salesforce account to link tickets -> accounts:
    -- sf_account_id   VARCHAR(50) REFERENCES salesforce_accounts(sf_account_id)
);

-- 4. Create the 'jira_issues' table
CREATE TABLE IF NOT EXISTS jira_issues (
    jira_issue_id        VARCHAR(50) PRIMARY KEY,   -- e.g., "DEV-101"
    issue_summary        VARCHAR(255),             -- Short summary/title
    issue_description    TEXT,
    issue_type           VARCHAR(50),              -- e.g., "Bug," "Task," "Story"
    issue_status         VARCHAR(50),              -- e.g., "Open," "In Progress," "Done"
    priority            VARCHAR(50),               -- e.g., "High," "Medium," "Low"
    assignee_name        VARCHAR(100),             -- Developer assigned
    assignee_email       VARCHAR(255),             -- Optional: developer email
    reporter_name        VARCHAR(100),             -- Person who created the issue
    comments             TEXT,                     -- Could store the latest or aggregated comments
    linked_zendesk_ticket BIGINT,                  -- If single direct link to Zendesk ticket
    source_created_at    TIMESTAMP,
    source_updated_at    TIMESTAMP,
    created_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_linked_zendesk
        FOREIGN KEY (linked_zendesk_ticket) 
        REFERENCES zendesk_tickets(zd_ticket_id)
        ON DELETE SET NULL  -- or RESTRICT, or CASCADE, depending on your logic
);

-- 5. (Optional) Many-to-many relationship between Zendesk tickets & Jira issues
--    Use if one ticket can link to multiple JIRA issues and vice versa.
CREATE TABLE IF NOT EXISTS zendesk_jira_links (
    zd_ticket_id    BIGINT REFERENCES zendesk_tickets(zd_ticket_id),
    jira_issue_id   VARCHAR(50) REFERENCES jira_issues(jira_issue_id),
    PRIMARY KEY (zd_ticket_id, jira_issue_id)
);

-- Script end. 
-- You can now INSERT or COPY data into these tables as needed.