CREATE TABLE IF NOT EXISTS oauth_clients (
    client_id VARCHAR(255) PRIMARY KEY,
    client_info JSON NOT NULL
);

CREATE TABLE IF NOT EXISTS oauth_auth_codes (
    code VARCHAR(255) PRIMARY KEY,
    client_id VARCHAR(255),
    redirect_uri TEXT,
    redirect_uri_provided_explicitly BOOLEAN,
    expires_at BIGINT,
    scopes JSON,
    code_challenge VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS oauth_tokens (
    token TEXT PRIMARY KEY,
    client_id VARCHAR(255),
    scopes JSON,
    expires_at BIGINT
);

CREATE TABLE IF NOT EXISTS oauth_token_mapping (
    mcp_token TEXT PRIMARY KEY,
    singlestore_token TEXT
);
