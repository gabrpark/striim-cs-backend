-- Sample Salesforce accounts
INSERT INTO salesforce_accounts (
    sf_account_id,
    account_owner_name,
    account_owner_email,
    deal_room_link,
    account_name,
    company_name,
    business_use_case,
    parent_account_id,
    target_upsell_value,
    account_record_type,
    type,
    is_target_account,
    is_migration_account,
    territory,
    sf_last_updated_at,
    description
)
VALUES
    ('001A000001L0F45', 'John Smith', 'john.smith@example.com',
     'https://drive.google.com/drive/folders/sampleDealRoom1',
     'Park IT', 'Park IT Solutions',
     'MS SQL -> Snowflake for data analytics',
     null, -- no parent account
     50000.00, 'Customer Account', 'Customer',
     true, false, 'US West',
     '2023-10-05 10:25:00',
     'Primary technology partner; high potential for upsell'),
     
    ('001A000001L0F46', 'Jane Doe', 'jane.doe@example.com',
     'https://drive.google.com/drive/folders/sampleDealRoom2',
     'Acme Inc', 'Acme Incorporated',
     'Oracle -> AWS migration use case',
     null,
     150000.00, 'Customer Account', 'Customer',
     false, true, 'EMEA',
     '2023-09-30 09:00:00',
     'In the midst of migrating legacy apps to the cloud'),
     
    ('001A000001L0F47', 'Mike Brown', 'mike.brown@example.com',
     null,
     'Beta Corp', 'Beta Corporation',
     'SAP integration, ML readiness',
     '001A000001L0F46', -- parent account referencing Acme
     25000.00, 'Partner Account', 'Partner',
     false, false, 'US East',
     '2023-10-01 12:10:00',
     'Partner account under Acme Inc. umbrella');

		 -- Sample Zendesk tickets
INSERT INTO zendesk_tickets (
    zd_ticket_id,
    requester_name,
    requester_email,
    assignee_name,
    assignee_email,
    ticket_subject,
    ticket_type,
    priority,
    status,
    product_version,
    product_component,
    node_count,
    environment,
    linked_jira_issues,
    ticket_description,
    source_created_at,
    source_updated_at
)
VALUES
    (1001, 'Alice Carter', 'alice.carter@parkit.com',
     'Support Agent A', 'agent.a@company.com',
     'Can’t access reporting dashboard', 'Problem', 'High', 'Open',
     '4.2', 'Writer Adapter', 1, 'Prod',
     'DEV-101',  -- Single JIRA key linked
     'Customer reports they cannot access the advanced reporting page since last patch.',
     '2023-10-01 08:30:00', '2023-10-03 10:00:00'),
     
    (1002, 'Bob Williams', 'bob@acme.io',
     'Support Agent B', 'agent.b@company.com',
     'Billing discrepancy in invoice', 'Incident', 'Medium', 'Pending',
     '4.2', 'Billing Module', 1, 'Prod',
     null,  -- no JIRA linked yet
     'Customer found a mismatch in final invoice vs. original quote.',
     '2023-09-28 14:00:00', '2023-10-01 09:15:00'),
     
    (1003, 'Charlie Green', 'charlie@betacorp.com',
     'Support Agent C', 'agent.c@company.com',
     'Cannot connect to database', 'Problem', 'High', 'Open',
     '4.2', 'DB Connector', 2, 'Staging',
     'DEV-102,DEV-104',  -- multiple JIRA issues
     'Staging environment cannot connect to DB writer; logs show timeouts.',
     '2023-10-02 07:45:00', '2023-10-05 11:20:00'),
     
    (1004, 'Alice Carter', 'alice.carter@parkit.com',
     'Support Agent A', 'agent.a@company.com',
     'Follow-up on ticket #1001', 'Question', 'Low', 'Open',
     '4.2', 'Writer Adapter', 1, 'Prod',
     null,
     'Requester wants an ETA on final fix for the advanced reporting access issue.',
     '2023-10-04 10:00:00', '2023-10-05 09:30:00');


		-- Sample Jira issues
INSERT INTO jira_issues (
    jira_issue_id,
    issue_summary,
    issue_description,
    issue_type,
    issue_status,
    priority,
    assignee_name,
    assignee_email,
    reporter_name,
    comments,
    linked_zendesk_ticket,
    source_created_at,
    source_updated_at
)
VALUES
    ('DEV-101', 'Advanced reporting page error', 
     'Adapter error when accessing new reporting UI.', 'Bug', 'In Progress', 
     'High', 'Dev Engineer 1', 'dev1@company.com', 
     'Alice Carter', 'Working on fix; user has intermittent access issues.', 
     1001, -- references Zendesk ticket #1001
     '2023-10-01 09:00:00', '2023-10-03 17:00:00'),
     
    ('DEV-102', 'DB writer timeout in staging',
     'Connection pooling might be failing in staging env.', 'Bug', 'Open',
     'High', 'Dev Engineer 2', 'dev2@company.com',
     'Charlie Green', 'Logs show repeated timeouts after 60s.',
     1003, -- references Zendesk ticket #1003
     '2023-10-02 08:00:00', '2023-10-05 08:45:00'),
     
    ('DEV-104', 'Investigation: DB performance bottleneck',
     'Need to check if the query engine is overloaded.', 'Task', 'Open',
     'Medium', 'Dev Engineer 3', 'dev3@company.com',
     'Charlie Green', 'Initial assessment pending. Might link to DEV-102 root cause.',
     1003,
     '2023-10-04 10:30:00', '2023-10-05 10:00:00');

INSERT INTO zendesk_jira_links (
    zd_ticket_id,
    jira_issue_id
)
VALUES
    (1001, 'DEV-101'),   -- Ticket #1001 linked to DEV-101
    (1003, 'DEV-102'),   -- Ticket #1003 linked to DEV-102
    (1003, 'DEV-104');   -- Ticket #1003 also linked to DEV-104