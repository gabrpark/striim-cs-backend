-- 1. Clean up existing tables (if you want a fresh start).
DROP TABLE IF EXISTS zendesk_jira_links CASCADE;
DROP TABLE IF EXISTS jira_issues CASCADE;
DROP TABLE IF EXISTS zendesk_tickets CASCADE;
DROP TABLE IF EXISTS subscriptions CASCADE;
DROP TABLE IF EXISTS services CASCADE;
DROP TABLE IF EXISTS salesforce_accounts CASCADE;
DROP TABLE IF EXISTS clients CASCADE;
DROP TABLE IF EXISTS notifications CASCADE;
DROP TABLE IF EXISTS summaries CASCADE;
DROP TABLE IF EXISTS summary_relationships CASCADE;

-- 2. Create the 'clients' table
CREATE TABLE IF NOT EXISTS clients (
    id VARCHAR(50) PRIMARY KEY,
    image_url VARCHAR(255),
    name VARCHAR(255),
    arr NUMERIC(10, 2),
    csm INTEGER,
    available_at TIMESTAMP,
    health INTEGER,
    company_name CHAR(255),
    CONSTRAINT clients_pkey PRIMARY KEY (id)
);

-- Add btree index if not exists
CREATE UNIQUE INDEX IF NOT EXISTS clients_pkey ON clients USING btree (id);

-- 3. Create the 'services' table
CREATE TABLE IF NOT EXISTS services (
    service_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description VARCHAR(255),
    service_type VARCHAR(50),              -- e.g., "SaaS", "Consulting", "Support"
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Create the 'salesforce_accounts' table with client connection
CREATE TABLE IF NOT EXISTS salesforce_accounts (
    sf_account_id         VARCHAR(50) PRIMARY KEY,
    account_owner_name    VARCHAR(100),
    account_owner_email   VARCHAR(255),
    deal_room_link        VARCHAR(255),
    account_name          VARCHAR(255) NOT NULL,
    company_name          VARCHAR(255),
    business_use_case     TEXT,
    parent_account_id     VARCHAR(50),
    target_upsell_value   NUMERIC(15,2),
    account_record_type   VARCHAR(50),
    type                  VARCHAR(50),
    is_target_account     BOOLEAN DEFAULT FALSE,
    is_migration_account  BOOLEAN DEFAULT FALSE,
    territory             VARCHAR(100),
    sf_last_updated_at    TIMESTAMP,
    description           TEXT,
    client_id             VARCHAR(50),
    created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT salesforce_accounts_pkey PRIMARY KEY (sf_account_id),
    CONSTRAINT fk_parent_account 
        FOREIGN KEY (parent_account_id) 
        REFERENCES public.salesforce_accounts(sf_account_id)
        ON DELETE SET NULL,
    CONSTRAINT fk_sf_client
        FOREIGN KEY (client_id)
        REFERENCES public.clients(id)
        ON DELETE SET NULL
);

-- Create the indexes using btree
CREATE UNIQUE INDEX IF NOT EXISTS salesforce_accounts_pkey ON salesforce_accounts USING btree (sf_account_id);
CREATE INDEX IF NOT EXISTS idx_salesforce_parent ON salesforce_accounts USING btree (parent_account_id);
CREATE INDEX IF NOT EXISTS idx_salesforce_client ON salesforce_accounts USING btree (client_id);

-- 5. Create the 'subscriptions' table to track service subscriptions
CREATE TABLE IF NOT EXISTS subscriptions (
    subscription_id       VARCHAR(50) PRIMARY KEY,
    client_id             VARCHAR(50) NOT NULL,
    service_id            VARCHAR(50) NOT NULL,
    status                VARCHAR(50),              -- e.g., "Active", "Pending", "Expiring"
    start_date            DATE,
    end_date              DATE,
    amount                DECIMAL(15,2),
    term_months           INT,
    auto_renew            BOOLEAN DEFAULT FALSE,
    renewal_notice_date   DATE,
    billing_frequency     VARCHAR(50),
    notes                 TEXT,
    created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Foreign key to client
    CONSTRAINT fk_subscription_client
        FOREIGN KEY (client_id)
        REFERENCES clients(id)
        ON DELETE CASCADE,
    -- Foreign key to service
    CONSTRAINT fk_subscription_service
        FOREIGN KEY (service_id)
        REFERENCES services(service_id)
        ON DELETE CASCADE
);

-- 6. Create the 'zendesk_tickets' table with service connection
CREATE TABLE IF NOT EXISTS zendesk_tickets (
    zd_ticket_id       BIGINT PRIMARY KEY,
    requester_name     VARCHAR(100),
    requester_email    VARCHAR(255),
    assignee_name      VARCHAR(100),
    assignee_email     VARCHAR(255),
    ticket_subject     VARCHAR(255),
    ticket_type        VARCHAR(50),
    priority           VARCHAR(50),
    status             VARCHAR(50),
    product_version    VARCHAR(50),
    product_component  VARCHAR(100),
    node_count         INT,
    environment        VARCHAR(50),
    linked_jira_issues VARCHAR(255),
    ticket_description TEXT,
    sf_account_id      VARCHAR(50),
    client_id          VARCHAR(50),
    service_id         VARCHAR(50),
    source_created_at  TIMESTAMP,
    source_updated_at  TIMESTAMP,
    summary            TEXT,
    created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at         TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    -- Foreign key to Salesforce account
    CONSTRAINT fk_zendesk_sf_account
        FOREIGN KEY (sf_account_id) 
        REFERENCES salesforce_accounts(sf_account_id)
        ON DELETE SET NULL,
    -- Foreign key to client
    CONSTRAINT fk_zendesk_client
        FOREIGN KEY (client_id)
        REFERENCES clients(id)
        ON DELETE SET NULL,
    -- Foreign key to service
    CONSTRAINT fk_zendesk_service
        FOREIGN KEY (service_id)
        REFERENCES services(service_id)
        ON DELETE SET NULL
);

-- 7. Create the 'jira_issues' table with service connection
CREATE TABLE IF NOT EXISTS jira_issues (
    jira_issue_id        VARCHAR(50) PRIMARY KEY,
    issue_summary        VARCHAR(255),
    issue_description    TEXT,
    issue_type           VARCHAR(50),
    issue_status         VARCHAR(50),
    priority             VARCHAR(50),
    assignee_name        VARCHAR(100),
    assignee_email       VARCHAR(255),
    reporter_name        VARCHAR(100),
    comments             TEXT,
    linked_zendesk_ticket BIGINT,
    sf_account_id        VARCHAR(50),
    client_id            VARCHAR(50),
    service_id           VARCHAR(50),
    source_created_at    TIMESTAMP,
    source_updated_at    TIMESTAMP,
    created_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT jira_issues_pkey PRIMARY KEY (jira_issue_id),
    CONSTRAINT fk_linked_zendesk
        FOREIGN KEY (linked_zendesk_ticket) 
        REFERENCES public.zendesk_tickets(zd_ticket_id)
        ON DELETE SET NULL,
    CONSTRAINT fk_jira_sf_account
        FOREIGN KEY (sf_account_id) 
        REFERENCES public.salesforce_accounts(sf_account_id)
        ON DELETE SET NULL,
    CONSTRAINT fk_jira_client
        FOREIGN KEY (client_id)
        REFERENCES public.clients(id)
        ON DELETE SET NULL,
    CONSTRAINT fk_jira_service
        FOREIGN KEY (service_id)
        REFERENCES public.services(service_id)
        ON DELETE SET NULL
);

-- Create the indexes using btree
CREATE UNIQUE INDEX IF NOT EXISTS jira_issues_pkey ON jira_issues USING btree (jira_issue_id);
CREATE INDEX IF NOT EXISTS idx_jira_sf_account ON jira_issues USING btree (sf_account_id);
CREATE INDEX IF NOT EXISTS idx_jira_client ON jira_issues USING btree (client_id);
CREATE INDEX IF NOT EXISTS idx_jira_service ON jira_issues USING btree (service_id);
CREATE INDEX IF NOT EXISTS idx_jira_zendesk ON jira_issues USING btree (linked_zendesk_ticket);

-- 8. Many-to-many relationship between Zendesk tickets & Jira issues
CREATE TABLE IF NOT EXISTS zendesk_jira_links (
    zd_ticket_id    BIGINT,
    jira_issue_id   VARCHAR(50),
    PRIMARY KEY (zd_ticket_id, jira_issue_id),
    CONSTRAINT fk_zendesk_ticket
        FOREIGN KEY (zd_ticket_id) 
        REFERENCES zendesk_tickets(zd_ticket_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_jira_issue
        FOREIGN KEY (jira_issue_id) 
        REFERENCES jira_issues(jira_issue_id)
        ON DELETE CASCADE
);

-- 9. Add indexes to improve query performance
CREATE INDEX idx_subscription_client ON subscriptions(client_id);
CREATE INDEX idx_subscription_service ON subscriptions(service_id);
CREATE INDEX idx_subscription_dates ON subscriptions(start_date, end_date);
CREATE INDEX idx_subscription_status ON subscriptions(status);
CREATE INDEX idx_zendesk_sf_account ON zendesk_tickets(sf_account_id);
CREATE INDEX idx_zendesk_client ON zendesk_tickets(client_id);
CREATE INDEX idx_zendesk_service ON zendesk_tickets(service_id);
CREATE INDEX idx_jira_sf_account ON jira_issues(sf_account_id);
CREATE INDEX idx_jira_client ON jira_issues(client_id);
CREATE INDEX idx_jira_service ON jira_issues(service_id);
CREATE INDEX idx_jira_zendesk ON jira_issues(linked_zendesk_ticket);

-- 10. Create the 'notifications' table
CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    client_id VARCHAR(50),
    subscription_id VARCHAR(50),
    type VARCHAR(50),          -- e.g., 'subscription_expiring', 'high_ticket_volume'
    priority VARCHAR(20),      -- e.g., 'high', 'medium', 'low'
    title VARCHAR(255),
    message TEXT,
    llm_analysis TEXT,        -- LLM-generated context and recommendations
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_notification_client
        FOREIGN KEY (client_id)
        REFERENCES clients(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_notification_subscription
        FOREIGN KEY (subscription_id)
        REFERENCES subscriptions(subscription_id)
        ON DELETE CASCADE
);

-- Base summaries table for all types of summaries
CREATE TABLE IF NOT EXISTS summaries (
    id SERIAL PRIMARY KEY,
    summary_type VARCHAR(50) NOT NULL,    -- 'ticket', 'multi_ticket', 'company', 'multi_company'
    summary TEXT NOT NULL,
    source_type VARCHAR(50) NOT NULL,     -- 'raw_data' or 'existing_summaries'
    source_ids JSONB,                     -- Array of source IDs (ticket_ids, company_ids, etc)
    source_summary_ids JSONB,             -- Array of summary IDs used to generate this summary
    query_params JSONB,                   -- Filters/query used to generate this summary
    date_range_start TIMESTAMP,
    date_range_end TIMESTAMP,
    metadata JSONB,                       -- Stats, counts, and other relevant data
    last_generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- Last check for data changes
    hash_signature TEXT,                  -- Hash of source data to detect changes
    is_valid BOOLEAN DEFAULT TRUE,        -- Flag for outdated summaries
    CONSTRAINT unique_summary_params UNIQUE (summary_type, query_params, date_range_start, date_range_end)
);

-- Reference table for summary relationships (hierarchy)
CREATE TABLE IF NOT EXISTS summary_relationships (
    parent_summary_id INTEGER REFERENCES summaries(id) ON DELETE CASCADE,
    child_summary_id INTEGER REFERENCES summaries(id) ON DELETE CASCADE,
    relationship_type VARCHAR(50),  -- e.g., 'aggregation', 'time_period', 'subset'
    PRIMARY KEY (parent_summary_id, child_summary_id)
);

-- Indexes for better query performance
CREATE INDEX idx_summaries_type ON summaries(summary_type);
CREATE INDEX idx_summaries_dates ON summaries(date_range_start, date_range_end);
CREATE INDEX idx_summaries_valid ON summaries(is_valid);
CREATE INDEX idx_summaries_last_verified ON summaries(last_verified_at);

-- Verify zendesk_tickets has summary column
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'zendesk_tickets';