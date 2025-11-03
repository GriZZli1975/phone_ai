-- AI Call Center Database Schema
-- PostgreSQL 15+

CREATE TABLE IF NOT EXISTS calls (
    id SERIAL PRIMARY KEY,
    call_id VARCHAR(50) UNIQUE NOT NULL,
    caller_number VARCHAR(20),
    called_number VARCHAR(20),
    start_time TIMESTAMP DEFAULT NOW(),
    end_time TIMESTAMP,
    duration INTEGER,
    recording_path VARCHAR(255),
    transcription TEXT,
    department VARCHAR(50),
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_calls_call_id ON calls(call_id);
CREATE INDEX idx_calls_start_time ON calls(start_time);
CREATE INDEX idx_calls_status ON calls(status);

-- Operators table
CREATE TABLE IF NOT EXISTS operators (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE,
    department VARCHAR(50),
    status VARCHAR(20) DEFAULT 'offline',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Call logs
CREATE TABLE IF NOT EXISTS call_logs (
    id SERIAL PRIMARY KEY,
    call_id INTEGER REFERENCES calls(id),
    timestamp TIMESTAMP DEFAULT NOW(),
    event_type VARCHAR(50),
    details TEXT
);

COMMENT ON TABLE calls IS 'Все входящие и исходящие звонки';
COMMENT ON TABLE operators IS 'Операторы call-центра';
COMMENT ON TABLE call_logs IS 'Детальные логи событий звонков';

