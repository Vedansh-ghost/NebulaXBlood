-- PostgreSQL production schema starter. SQLite is used by the local MVP API.
CREATE TABLE users(id BIGSERIAL PRIMARY KEY,email TEXT UNIQUE NOT NULL,role TEXT NOT NULL DEFAULT 'customer',created_at TIMESTAMPTZ DEFAULT now());
CREATE TABLE plans(id BIGSERIAL PRIMARY KEY,name TEXT UNIQUE NOT NULL,kind TEXT NOT NULL CHECK(kind IN ('game','vps')),ram_mb BIGINT NOT NULL,cpu_percent INTEGER NOT NULL,disk_mb BIGINT NOT NULL,price_minor BIGINT NOT NULL,active BOOLEAN DEFAULT TRUE);
CREATE TABLE nodes(id BIGSERIAL PRIMARY KEY,name TEXT UNIQUE NOT NULL,address TEXT NOT NULL,kind TEXT NOT NULL,status TEXT DEFAULT 'offline',created_at TIMESTAMPTZ DEFAULT now());
CREATE TABLE servers(id BIGSERIAL PRIMARY KEY,name TEXT NOT NULL,kind TEXT NOT NULL,user_id BIGINT REFERENCES users(id),plan_id BIGINT REFERENCES plans(id),node_id BIGINT REFERENCES nodes(id),status TEXT DEFAULT 'provisioning',external_id TEXT UNIQUE,created_at TIMESTAMPTZ DEFAULT now());
CREATE TABLE orders(id BIGSERIAL PRIMARY KEY,user_id BIGINT REFERENCES users(id),plan_id BIGINT REFERENCES plans(id),status TEXT DEFAULT 'pending',payment_ref TEXT,created_at TIMESTAMPTZ DEFAULT now());
CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
