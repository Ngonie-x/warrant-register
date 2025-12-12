# Django Warranty Registration System

A Django-based warranty registration API and Warranty Centre web application designed to integrate with a Next.js asset management system.

## System Overview

```
┌─────────────────────┐       POST /api/warranty/register/      ┌──────────────────────────┐
│                     │ ─────────────────────────────────────▶  │                          │
│   Next.js App       │                                         │   Django Warranty API    │
│   (Asset Manager)   │ ◀─────────────────────────────────────  │   + Warranty Centre      │
│                     │       {success: true, status: ...}      │                          │
└─────────────────────┘                                         └──────────────────────────┘
                                                                            │
                                                                            ▼
                                                                ┌──────────────────────────┐
                                                                │     PostgreSQL DB        │
                                                                │   (Optimized Settings)   │
                                                                └──────────────────────────┘
```

## Features

### API (api app)
- **Warranty Registration Endpoint** - Receives asset data from Next.js and creates warranty records
- **Warranty Status Check** - Check if an asset is already registered
- **Full CRUD Operations** - List, retrieve, update, delete warranty registrations
- **Statistics Endpoint** - Dashboard statistics with caching
- **Reference Data Sync** - Sync departments, categories, and profiles from Next.js
- **Audit Logging** - Track all changes with user, timestamp, and IP address

### Warranty Centre (warrantyapp)
- **Dashboard** - Overview of warranty statistics
- **Warranty List** - Searchable, filterable list of registered warranties
- **Warranty Detail** - Full asset and warranty information
- **Expiring Warranties** - View warranties expiring within N days
- **Audit Logs** - View history of all changes

## Installation

### 1. Install Dependencies

```bash
pip install django djangorestframework psycopg2-binary django-cors-headers djangorestframework-simplejwt python-dotenv
```

### 2. Create PostgreSQL Database

```bash
createdb warranty_db
```

### 3. Set Environment Variables

Create a `.env` file:
```env
DB_NAME=warranty_db
DB_USER=your_user
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
SECRET_KEY=your-secret-key-here
DEBUG=True
```

### 4. Run Migrations

```bash
python manage.py makemigrations api
python manage.py makemigrations warrantyapp
python manage.py migrate
```

### 5. Create Superuser

```bash
python manage.py createsuperuser
```

### 6. Apply Database Optimizations

```bash
# Apply PostgreSQL configuration (requires DB admin access)
sudo bash scripts/optimize_postgresql.sh

# Create performance indexes via Django
python manage.py optimize_db --indexes
```

### 7. Run the Server

```bash
python manage.py runserver
```

## API Endpoints

### Warranty Registration (for Next.js integration)

**Register a Warranty**
```http
POST /api/warranty/register/
Content-Type: application/json

{
  "id": 123,
  "name": "Dell Laptop XPS 15",
  "category": "Electronics",
  "department": "IT",
  "cost": 1500.00,
  "date_purchased": "2024-01-15",
  "created_by": "John Doe",
  "created_at": "2024-01-15T10:30:00Z",
  "registered_by_id": 1,
  "registered_by_name": "Jane Smith",
  "warranty_duration_months": 24,
  "serial_number": "ABC123XYZ",
  "manufacturer": "Dell",
  "model_number": "XPS-15-9530"
}
```

**Success Response:**
```json
{
  "success": true,
  "message": "Warranty registered successfully",
  "status": "registered",
  "status_label": "Warranty Registered",
  "warranty_id": 1,
  "asset_id": 123,
  "registered_at": "2024-06-15T14:30:00Z",
  "warranty_start_date": "2024-01-15",
  "warranty_end_date": "2026-01-15"
}
```

**Check Warranty Status**
```http
GET /api/warranty/check/123/
```

### Authentication

```http
POST /api/auth/token/
Content-Type: application/json

{
  "username": "your_username",
  "password": "your_password"
}
```

### Other Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/warranties/` | GET | List all warranties (paginated, filterable) |
| `/api/warranties/{id}/` | GET | Get warranty details |
| `/api/warranties/{id}/` | PUT/PATCH | Update warranty |
| `/api/warranties/{id}/` | DELETE | Delete warranty |
| `/api/warranties/statistics/` | GET | Get dashboard statistics |
| `/api/sync/departments/` | POST | Sync departments from Next.js |
| `/api/sync/categories/` | POST | Sync categories from Next.js |
| `/api/sync/profiles/` | POST | Sync profiles from Next.js |

### Query Parameters for Listing

```http
GET /api/warranties/?status=registered&department=IT&search=Dell&date_from=2024-01-01
```

## Warranty Centre URLs

| URL | Description |
|-----|-------------|
| `/warranty/login/` | Login page |
| `/warranty/` | Dashboard |
| `/warranty/warranties/` | List all warranties |
| `/warranty/warranties/{id}/` | Warranty details |
| `/warranty/expiring/` | Warranties expiring soon |
| `/warranty/audit-logs/` | Audit log history |

## Next.js Integration Example

```javascript
// services/warranty.js
const API_BASE = 'http://localhost:8000';

export async function registerWarranty(asset, userId, userName) {
  const response = await fetch(`${API_BASE}/api/warranty/register/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      id: asset.id,
      name: asset.name,
      category: asset.category,
      department: asset.department,
      cost: asset.cost,
      date_purchased: asset.date_purchased,
      created_by: asset.created_by,
      created_at: asset.created_at,
      registered_by_id: userId,
      registered_by_name: userName,
      warranty_duration_months: 12,
      serial_number: asset.serial_number || null,
      manufacturer: asset.manufacturer || null,
      model_number: asset.model_number || null,
    }),
  });

  const data = await response.json();
  
  if (data.success) {
    // Update UI to show "Warranty Registered" status
    return { success: true, status_label: data.status_label };
  }
  
  return { success: false, error: data.error || data.message };
}

export async function checkWarrantyStatus(assetId) {
  const response = await fetch(`${API_BASE}/api/warranty/check/${assetId}/`);
  return response.json();
}
```

---

## PostgreSQL Performance Optimizations

### 1. Connection Configuration (settings.py)

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'OPTIONS': {
            'options': '-c statement_timeout=30000',  # 30 second query timeout
        },
        'CONN_MAX_AGE': 600,  # Connection pooling (10 minutes)
        'CONN_HEALTH_CHECKS': True,  # Verify connection health
    }
}
```

**Why:** Connection pooling reduces the overhead of establishing new database connections for each request. The statement timeout prevents runaway queries.

### 2. Memory Settings (postgresql.conf)

```
shared_buffers = 1GB           # 25% of RAM (for 4GB system)
effective_cache_size = 3GB     # 50-75% of RAM
work_mem = 64MB                # Per-operation sort memory
maintenance_work_mem = 256MB   # For VACUUM, CREATE INDEX
```

**Why:**
- `shared_buffers`: PostgreSQL's main memory cache for data pages. More memory = fewer disk reads.
- `effective_cache_size`: Helps query planner estimate available cache; influences index usage decisions.
- `work_mem`: Memory for sorting and hash operations. Higher values speed up ORDER BY and JOINs.
- `maintenance_work_mem`: Speeds up maintenance operations like VACUUM and index creation.

### 3. Write-Ahead Log (WAL) Settings

```
wal_buffers = 64MB
checkpoint_completion_target = 0.9
checkpoint_timeout = 15min
```

**Why:**
- `wal_buffers`: Larger buffer reduces disk writes during heavy inserts/updates.
- `checkpoint_completion_target`: Spreads checkpoint I/O over time, reducing spikes.
- `checkpoint_timeout`: Less frequent checkpoints improve write performance.

### 4. Query Planner Settings

```
random_page_cost = 1.1         # Optimized for SSD (default is 4.0)
effective_io_concurrency = 200 # Parallel I/O for SSD
```

**Why:** SSDs have much lower random read costs than HDDs. Lower `random_page_cost` encourages index usage over sequential scans.

### 5. Strategic Indexes

```sql
-- Case-insensitive asset name search
CREATE INDEX idx_warranty_asset_name_lower 
ON api_warranty_registrations (LOWER(asset_name));

-- Partial index for active warranties only (smaller, faster)
CREATE INDEX idx_warranty_active 
ON api_warranty_registrations (warranty_end_date) 
WHERE status = 'registered';

-- Composite index for common listing queries
CREATE INDEX idx_warranty_listing 
ON api_warranty_registrations (status, registered_at DESC, department, category);

-- GIN index for full-text/fuzzy search
CREATE EXTENSION pg_trgm;
CREATE INDEX idx_warranty_asset_name_gin 
ON api_warranty_registrations USING gin (asset_name gin_trgm_ops);
```

**Why:**
- **Case-insensitive indexes**: LOWER() searches hit the index instead of full table scans.
- **Partial indexes**: Smaller than full indexes, faster for filtered queries (e.g., only active warranties).
- **Composite indexes**: Match common query patterns, covering multiple WHERE and ORDER BY columns.
- **GIN with pg_trgm**: Enables fast LIKE '%search%' queries and fuzzy matching.

### 6. Model-Level Indexes (Django)

```python
class Meta:
    indexes = [
        models.Index(fields=['asset_external_id']),
        models.Index(fields=['status']),
        models.Index(fields=['registered_at']),
        models.Index(fields=['-warranty_end_date']),
        models.Index(fields=['department', 'category']),
        models.Index(fields=['registered_by_id']),
    ]
```

**Why:** Django-created indexes match ORM query patterns. Indexes on foreign keys and commonly filtered fields speed up lookups.

### 7. Query Optimization (select_related)

```python
# views.py
warranties = WarrantyRegistration.objects.select_related('department_ref', 'category_ref')
```

**Why:** `select_related()` performs JOINs to fetch related data in one query instead of N+1 queries.

### 8. Caching

```python
from django.views.decorators.cache import cache_page

@cache_page(60 * 5)  # Cache for 5 minutes
def statistics(request):
    ...
```

**Why:** Reduces database load for frequently accessed, slowly changing data like statistics.

### 9. Autovacuum Tuning

```sql
ALTER TABLE api_warranty_registrations SET (
    autovacuum_vacuum_scale_factor = 0.05,
    autovacuum_analyze_scale_factor = 0.02
);
```

**Why:** High-update tables need more frequent vacuuming. Lower scale factors trigger autovacuum sooner, keeping statistics fresh and preventing bloat.

### 10. Maintenance Commands

```bash
# Create performance indexes
python manage.py optimize_db --indexes

# Update statistics
python manage.py optimize_db --analyze

# Reclaim space and update stats
python manage.py optimize_db --vacuum

# Check table and index sizes/usage
python manage.py optimize_db --check
```

### Monitoring

```sql
-- Check slow queries
SELECT query, calls, mean_time, total_time 
FROM pg_stat_statements 
ORDER BY mean_time DESC LIMIT 10;

-- Check index usage
SELECT indexrelname, idx_scan, idx_tup_read 
FROM pg_stat_user_indexes 
ORDER BY idx_scan DESC;

-- Find unused indexes
SELECT indexrelname FROM pg_stat_user_indexes 
WHERE idx_scan = 0 AND indexrelname NOT LIKE '%_pkey';
```

---

## Project Structure

```
warranty_system/
├── config/
│   ├── __init__.py
│   ├── settings.py      # Django settings with PostgreSQL config
│   ├── urls.py          # Root URL configuration
│   ├── wsgi.py
│   └── asgi.py
├── api/
│   ├── __init__.py
│   ├── models.py        # WarrantyRegistration, AuditLog, etc.
│   ├── serializers.py   # DRF serializers
│   ├── views.py         # API views and viewsets
│   ├── urls.py          # API routes
│   ├── admin.py         # Admin interface
│   └── management/
│       └── commands/
│           └── optimize_db.py  # DB optimization command
├── warrantyapp/
│   ├── __init__.py
│   ├── views.py         # Web interface views
│   ├── urls.py          # Web routes
│   └── models.py
├── templates/
│   └── warrantyapp/
│       ├── base.html
│       ├── login.html
│       ├── dashboard.html
│       ├── warranty_list.html
│       ├── warranty_detail.html
│       ├── expiring_warranties.html
│       └── audit_log_list.html
├── scripts/
│   └── optimize_postgresql.sh  # PostgreSQL tuning script
├── manage.py
└── README.md
```

## Models

### WarrantyRegistration
- `asset_external_id` - Original asset ID from Next.js (unique)
- `asset_name` - Name of the asset
- `category`, `department` - Reference data
- `cost`, `date_purchased` - Asset details
- `status` - pending/registered/expired/claimed/void
- `registered_by_id`, `registered_by_name` - Who registered
- `warranty_start_date`, `warranty_end_date` - Warranty period
- `serial_number`, `manufacturer`, `model_number` - Additional info

### WarrantyAuditLog
- `warranty` - Foreign key to registration
- `action` - created/updated/status_changed/deleted
- `performed_by` - User who made the change
- `old_value`, `new_value` - Change details (JSON)
- `ip_address`, `timestamp` - Tracking info

## License

MIT License
