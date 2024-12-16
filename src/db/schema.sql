-- Core contact table
CREATE TABLE contacts (
    id TEXT PRIMARY KEY,
    first_name TEXT,
    last_name TEXT,
    email TEXT,
    phone TEXT,
    source TEXT,
    source_id TEXT,
    contact_metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source, source_id)
);

-- Track merge history
CREATE TABLE merge_history (
    id TEXT PRIMARY KEY,
    source_contact_id TEXT,
    target_contact_id TEXT,
    merge_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    merge_reason TEXT,
    FOREIGN KEY(source_contact_id) REFERENCES contacts(id),
    FOREIGN KEY(target_contact_id) REFERENCES contacts(id)
);

-- Store source credentials
CREATE TABLE source_credentials (
    source TEXT PRIMARY KEY,
    credentials JSON,
    last_sync TIMESTAMP
); 