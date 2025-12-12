#!/bin/bash
# PostgreSQL Performance Optimization Script for Warranty System
# Run these commands as PostgreSQL superuser (postgres)

echo "======================================"
echo "PostgreSQL Performance Optimization"
echo "for Warranty Registration System"
echo "======================================"

# Database name
DB_NAME="${DB_NAME:-warranty_db}"

cat << 'EOF'

=== POSTGRESQL CONFIGURATION OPTIMIZATIONS ===

Add the following settings to your postgresql.conf file.
Location: Usually /etc/postgresql/{version}/main/postgresql.conf or /var/lib/pgsql/data/postgresql.conf

# ----- Memory Settings -----
# Set shared_buffers to 25% of available RAM (e.g., for 4GB RAM)
shared_buffers = 1GB

# Effective cache size (50-75% of RAM)
effective_cache_size = 3GB

# Memory for sorting/hashing operations
work_mem = 64MB

# Memory for maintenance operations (VACUUM, CREATE INDEX)
maintenance_work_mem = 256MB

# ----- Checkpoint Settings -----
# Spread checkpoint writes (reduce I/O spikes)
checkpoint_completion_target = 0.9

# Increase WAL buffers
wal_buffers = 64MB

# Maximum time between checkpoints
checkpoint_timeout = 15min

# ----- Query Planner Settings -----
# Cost of random page access (1.1 for SSD, 4.0 for HDD)
random_page_cost = 1.1

# Effective I/O concurrency for SSDs
effective_io_concurrency = 200

# ----- Connection Settings -----
# Maximum connections (adjust based on your app pool size)
max_connections = 200

# ----- Logging (Optional but recommended) -----
# Log slow queries
log_min_duration_statement = 1000

# Log checkpoints
log_checkpoints = on

# ----- Parallel Query Settings -----
max_parallel_workers_per_gather = 2
max_parallel_workers = 4

EOF

echo ""
echo "=== DATABASE-SPECIFIC OPTIMIZATIONS ==="
echo ""
echo "Run the following SQL commands in PostgreSQL:"
echo ""

cat << EOF

-- Connect to the warranty database
\c ${DB_NAME}

-- 1. Create additional indexes for common queries
-- These complement the Django model indexes

-- Index for searching assets by name (case-insensitive)
CREATE INDEX IF NOT EXISTS idx_warranty_asset_name_lower 
ON api_warranty_registrations (LOWER(asset_name));

-- Index for searching by serial number (case-insensitive)  
CREATE INDEX IF NOT EXISTS idx_warranty_serial_lower 
ON api_warranty_registrations (LOWER(serial_number)) 
WHERE serial_number IS NOT NULL;

-- Partial index for active warranties only
CREATE INDEX IF NOT EXISTS idx_warranty_active 
ON api_warranty_registrations (warranty_end_date) 
WHERE status = 'registered';

-- Index for filtering by registration date range
CREATE INDEX IF NOT EXISTS idx_warranty_registered_date 
ON api_warranty_registrations (DATE(registered_at));

-- Composite index for common listing queries
CREATE INDEX IF NOT EXISTS idx_warranty_listing 
ON api_warranty_registrations (status, registered_at DESC, department, category);

-- 2. Update table statistics for better query planning
ANALYZE api_warranty_registrations;
ANALYZE api_warranty_audit_log;
ANALYZE api_departments;
ANALYZE api_categories;
ANALYZE api_profiles;

-- 3. Set table-specific autovacuum settings for high-update tables
ALTER TABLE api_warranty_registrations SET (
    autovacuum_vacuum_scale_factor = 0.05,
    autovacuum_analyze_scale_factor = 0.02
);

ALTER TABLE api_warranty_audit_log SET (
    autovacuum_vacuum_scale_factor = 0.1,
    autovacuum_analyze_scale_factor = 0.05
);

-- 4. Create extension for full-text search (if needed)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 5. Create GIN index for full-text search on asset names
CREATE INDEX IF NOT EXISTS idx_warranty_asset_name_gin 
ON api_warranty_registrations USING gin (asset_name gin_trgm_ops);

EOF

echo ""
echo "=== MAINTENANCE COMMANDS ==="
echo ""
echo "Run these periodically for optimal performance:"
echo ""

cat << 'EOF'
-- Full vacuum and analyze (run during low traffic)
VACUUM FULL ANALYZE api_warranty_registrations;
VACUUM FULL ANALYZE api_warranty_audit_log;

-- Reindex to reclaim space and improve performance
REINDEX TABLE api_warranty_registrations;
REINDEX TABLE api_warranty_audit_log;

-- Check table and index sizes
SELECT 
    relname AS table_name,
    pg_size_pretty(pg_total_relation_size(relid)) AS total_size,
    pg_size_pretty(pg_relation_size(relid)) AS table_size,
    pg_size_pretty(pg_indexes_size(relid)) AS index_size
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC;

-- Check index usage statistics
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;

-- Find unused indexes
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan = 0
    AND schemaname = 'public';
EOF

echo ""
echo "=== CRON JOB FOR MAINTENANCE ==="
echo ""
echo "Add this to crontab for automated maintenance:"
echo ""
echo "# Run VACUUM ANALYZE every night at 2 AM"
echo "0 2 * * * psql -U postgres -d ${DB_NAME} -c 'VACUUM ANALYZE;'"
echo ""
echo "# Update statistics weekly on Sunday at 3 AM"
echo "0 3 * * 0 psql -U postgres -d ${DB_NAME} -c 'ANALYZE;'"

echo ""
echo "======================================"
echo "Optimization script completed!"
echo "======================================"
