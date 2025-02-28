-- Insert clients data
INSERT INTO clients (id, image_url, name, arr, csm, available_at, health) VALUES
('1', 'https://uwja77bygk2kgfqe.public.blob.vercel-storage.com/smartphone-gaPvyZW6aww0IhD3dOpaU6gBGILtcJ.webp', 'Olivia Martin', 47309.00, 3, '2025-02-14 13:48:22.674', 8),
('2', 'https://uwja77bygk2kgfqe.public.blob.vercel-storage.com/earbuds-3rew4JGdIK81KNlR8Edr8NBBhFTOtX.webp', 'Ethan Walker', 93812.00, 1, '2025-02-14 13:48:22.674', 3),
('3', 'https://uwja77bygk2kgfqe.public.blob.vercel-storage.com/home-iTeNnmKSMnrykOS9IYyJvnLFgap7Vw.webp', 'Ava Thompson', 78456.00, 5, '2025-02-14 13:48:22.674', 10),
('4', 'https://uwja77bygk2kgfqe.public.blob.vercel-storage.com/tv-H4l26crxtm9EQHLWc0ddrsXZ0V0Ofw.webp', 'Liam Martinez', 26514.00, 2, '2025-02-14 13:48:22.674', 2),
('5', 'https://uwja77bygk2kgfqe.public.blob.vercel-storage.com/laptop-9bgUhjY491hkxiMDeSgqb9R5I3lHNL.webp', 'Sophia Robinson', 35287.00, 4, '2025-02-14 13:48:22.674', 7);

-- Insert services data
INSERT INTO services (service_id, name, description, service_type, is_active)
VALUES
('SVC001', 'Enterprise Analytics', 'Advanced analytics platform for enterprise customers', 'SaaS', true),
('SVC002', 'Data Migration', 'Database migration services from legacy systems', 'Consulting', true),
('SVC003', 'Cloud Hosting', 'Cloud infrastructure and hosting services', 'SaaS', true),
('SVC004', 'Support Premium', 'Premium 24/7 support package', 'Support', true),
('SVC005', 'Security Audit', 'Comprehensive security audit and assessment', 'Consulting', true);

-- Insert Salesforce accounts data 
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
    description,
    client_id
)
VALUES
    ('001A000001L0F45', 'John Smith', 'john.smith@example.com',
     'https://drive.google.com/drive/folders/sampleDealRoom1',
     'Olivia Martin', 'Martin Technologies',
     'MS SQL -> Snowflake for data analytics',
     null,
     50000.00, 'Customer Account', 'Customer',
     true, false, 'US West',
     '2023-10-05 10:25:00',
     'Primary technology partner; high potential for upsell',
     '1'),
     
    ('001A000001L0F46', 'Jane Doe', 'jane.doe@example.com',
     'https://drive.google.com/drive/folders/sampleDealRoom2',
     'Ethan Walker', 'Walker Enterprises',
     'Oracle -> AWS migration use case',
     null,
     150000.00, 'Customer Account', 'Customer',
     false, true, 'EMEA',
     '2023-09-30 09:00:00',
     'In the midst of migrating legacy apps to the cloud',
     '2'),
     
    ('001A000001L0F47', 'Mike Brown', 'mike.brown@example.com',
     null,
     'Ava Thompson', 'Thompson Inc',
     'SAP integration, ML readiness',
     '001A000001L0F46',
     25000.00, 'Partner Account', 'Partner',
     false, false, 'US East',
     '2023-10-01 12:10:00',
     'Partner account with special terms',
     '3'),
     
    ('001A000001L0F48', 'Sarah Johnson', 'sarah.johnson@example.com',
     'https://drive.google.com/drive/folders/sampleDealRoom4',
     'Liam Martinez', 'Martinez Group',
     'Data warehouse consolidation',
     null,
     75000.00, 'Customer Account', 'Customer',
     true, false, 'US Central',
     '2023-10-02 14:30:00',
     'Strategic account with expansion opportunities',
     '4'),
     
    ('001A000001L0F49', 'David Wilson', 'david.wilson@example.com',
     'https://drive.google.com/drive/folders/sampleDealRoom5',
     'Sophia Robinson', 'Robinson Solutions',
     'Custom integration development',
     null,
     40000.00, 'Customer Account', 'Customer',
     false, false, 'APAC',
     '2023-10-03 08:15:00',
     'New customer with growing needs',
     '5');

-- Insert subscriptions data
INSERT INTO subscriptions (
    subscription_id,
    client_id,
    service_id,
    status,
    start_date,
    end_date,
    amount,
    term_months,
    auto_renew,
    renewal_notice_date,
    billing_frequency,
    notes
)
VALUES
    ('SUB10001', '1', 'SVC001', 'Active',
     '2023-01-15', '2024-01-14',
     35000.00, 12, true, '2023-12-01',
     'Annual', 'First subscription period'),
     
    ('SUB10002', '1', 'SVC004', 'Active',
     '2023-01-15', '2024-01-14',
     12000.00, 12, true, '2023-12-01',
     'Annual', 'Premium support add-on'),
     
    ('SUB10003', '2', 'SVC002', 'Active',
     '2023-03-01', '2023-12-31',
     85000.00, 10, false, '2023-11-15',
     'One-time', 'Migration project, fixed term'),
     
    ('SUB10004', '3', 'SVC001', 'Active',
     '2023-02-10', '2024-02-09',
     50000.00, 12, true, '2024-01-01',
     'Annual', 'Standard enterprise package'),
     
    ('SUB10005', '3', 'SVC003', 'Active',
     '2023-02-10', '2024-02-09',
     18000.00, 12, true, '2024-01-01',
     'Monthly', 'Billed monthly, annual term'),
     
    ('SUB10006', '4', 'SVC005', 'Pending',
     '2023-11-01', '2024-01-31',
     25000.00, 3, false, null,
     'One-time', 'Security audit project'),
     
    ('SUB10007', '5', 'SVC001', 'Active',
     '2023-06-01', '2024-05-31',
     30000.00, 12, false, '2024-04-15',
     'Annual', 'Trial year, renewal TBD');

-- Insert Zendesk tickets data
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
    sf_account_id,
    client_id,
    service_id,
    source_created_at,
    source_updated_at
)
VALUES
    (1001, 'Olivia Martin', 'olivia.martin@example.com',
     'Support Agent A', 'agent.a@company.com',
     'Cannot access analytics dashboard', 'Problem', 'High', 'Open',
     '4.2', 'Analytics Dashboard', 1, 'Prod',
     'DEV-101',
     'Customer reports they cannot access the analytics dashboard since last patch.',
     '001A000001L0F45', '1', 'SVC001',
     '2023-10-01 08:30:00', '2023-10-03 10:00:00'),
     
    (1002, 'Ethan Walker', 'ethan.walker@example.com',
     'Support Agent B', 'agent.b@company.com',
     'Billing discrepancy in invoice', 'Incident', 'Medium', 'Pending',
     '4.2', 'Billing Module', 1, 'Prod',
     null,
     'Customer found a mismatch in final invoice vs. original quote.',
     '001A000001L0F46', '2', 'SVC002',
     '2023-09-28 14:00:00', '2023-10-01 09:15:00'),
     
    (1003, 'Ava Thompson', 'ava.thompson@example.com',
     'Support Agent C', 'agent.c@company.com',
     'Cannot connect to database', 'Problem', 'High', 'Open',
     '4.2', 'DB Connector', 2, 'Staging',
     'DEV-102,DEV-104',
     'Staging environment cannot connect to DB writer; logs show timeouts.',
     '001A000001L0F47', '3', 'SVC001',
     '2023-10-02 07:45:00', '2023-10-05 11:20:00'),
     
    (1004, 'Olivia Martin', 'olivia.martin@example.com',
     'Support Agent A', 'agent.a@company.com',
     'Follow-up on ticket #1001', 'Question', 'Low', 'Open',
     '4.2', 'Analytics Dashboard', 1, 'Prod',
     null,
     'Requester wants an ETA on final fix for the analytics dashboard access issue.',
     '001A000001L0F45', '1', 'SVC001',
     '2023-10-04 10:00:00', '2023-10-05 09:30:00'),
     
    (1005, 'Liam Martinez', 'liam.martinez@example.com',
     'Support Agent D', 'agent.d@company.com',
     'Security scan findings', 'Task', 'Medium', 'Pending',
     '4.3', 'Security Module', 3, 'Prod',
     'DEV-105',
     'Scheduled security scan found potential vulnerabilities that need review.',
     '001A000001L0F48', '4', 'SVC005',
     '2023-10-04 11:30:00', '2023-10-05 14:45:00');

-- Insert Jira issues data
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
    sf_account_id,
    client_id,
    service_id,
    source_created_at,
    source_updated_at
)
VALUES
    ('DEV-101', 'Analytics dashboard access error', 
     'Users unable to access analytics dashboard after latest deployment.', 
     'Bug', 'In Progress', 'High', 
     'Dev Engineer 1', 'dev1@company.com', 
     'Support Agent A', 'Working on fix; investigating authentication flow.', 
     1001, '001A000001L0F45', '1', 'SVC001',
     '2023-10-01 09:00:00', '2023-10-03 17:00:00'),
     
    ('DEV-102', 'DB writer timeout in staging',
     'Connection pooling failing in staging environment.', 
     'Bug', 'Open', 'High', 
     'Dev Engineer 2', 'dev2@company.com',
     'Support Agent C', 'Logs show repeated timeouts after 60s.',
     1003, '001A000001L0F47', '3', 'SVC001',
     '2023-10-02 08:00:00', '2023-10-05 08:45:00'),
     
    ('DEV-104', 'Investigation: DB performance bottleneck',
     'Need to check if the query engine is overloaded.', 
     'Task', 'Open', 'Medium', 
     'Dev Engineer 3', 'dev3@company.com',
     'Support Agent C', 'Initial assessment pending. Might link to DEV-102 root cause.',
     1003, '001A000001L0F47', '3', 'SVC001',
     '2023-10-04 10:30:00', '2023-10-05 10:00:00'),
     
    ('DEV-105', 'Address security scan findings',
     'Review and address potential vulnerabilities from latest security scan.', 
     'Task', 'Open', 'Medium', 
     'Dev Engineer 4', 'dev4@company.com',
     'Support Agent D', 'Need to prioritize findings and create remediation plan.',
     1005, '001A000001L0F48', '4', 'SVC005',
     '2023-10-05 08:30:00', '2023-10-05 15:00:00'),
     
    ('DEV-106', 'Billing module calculation error',
     'Fix discount calculation issue in billing module.', 
     'Bug', 'In Progress', 'Medium', 
     'Dev Engineer 5', 'dev5@company.com',
     'Support Manager', 'Investigating edge case with volume discounts.',
     null, '001A000001L0F46', '2', 'SVC002',
     '2023-10-03 09:15:00', '2023-10-05 11:30:00');

-- Insert Zendesk-Jira links
INSERT INTO zendesk_jira_links (
    zd_ticket_id,
    jira_issue_id
)
VALUES
    (1001, 'DEV-101'),
    (1003, 'DEV-102'),
    (1003, 'DEV-104'),
    (1005, 'DEV-105');

-- Verify the data was inserted correctly
SELECT 'clients' as table_name, COUNT(*) as record_count FROM clients
UNION ALL
SELECT 'services', COUNT(*) FROM services
UNION ALL
SELECT 'salesforce_accounts', COUNT(*) FROM salesforce_accounts
UNION ALL
SELECT 'subscriptions', COUNT(*) FROM subscriptions
UNION ALL
SELECT 'zendesk_tickets', COUNT(*) FROM zendesk_tickets
UNION ALL
SELECT 'jira_issues', COUNT(*) FROM jira_issues
UNION ALL
SELECT 'zendesk_jira_links', COUNT(*) FROM zendesk_jira_links;