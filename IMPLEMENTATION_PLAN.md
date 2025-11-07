# Implementation Plan - CRM Features v2.0

Technical roadmap for transforming the RO2 Oxygen Concentrator Monitoring System into a comprehensive CRM platform.

## Overview

**Goal:** Add multi-user support, concentrator lifecycle management, service tracking, and preventive maintenance features.

**Approach:** Incremental implementation starting with database schema, then backend APIs, then frontend Panel pages.

**Timeline:** Phase 1 & 2 - Target Q1 2025

---

## Phase 1: Database Schema & User Management

### Step 1.1: Create New Database Models

**New Tables to Add:**

#### 1. `users` - User authentication and profiles
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'user', -- 'user' or 'admin'
    full_name VARCHAR(255),
    phone VARCHAR(50),
    organization VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE
);
```

#### 2. `concentrators` - Concentrator registry
```sql
CREATE TABLE concentrators (
    id SERIAL PRIMARY KEY,
    concentrator_id VARCHAR(50) UNIQUE NOT NULL, -- Links to sensor_data.oxygen_concentrator_id
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,

    -- Device information
    brand VARCHAR(100),
    model VARCHAR(100),
    serial_number VARCHAR(100),
    oxygen_capacity_lpm DECIMAL(5,2), -- Litres per minute

    -- Procurement & age
    procurement_date DATE,
    age_months INTEGER,

    -- Location & association
    associated_hospital VARCHAR(255),
    location_notes TEXT,

    -- Status
    status VARCHAR(20) DEFAULT 'active', -- 'active', 'pending_removal', 'removed'
    removal_reason TEXT,
    removal_requested_at TIMESTAMP WITH TIME ZONE,
    removal_requested_by INTEGER REFERENCES users(id),
    removal_approved_at TIMESTAMP WITH TIME ZONE,
    removal_approved_by INTEGER REFERENCES users(id),

    -- General notes
    notes TEXT,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by INTEGER REFERENCES users(id)
);
```

#### 3. `service_records` - Service needed and completed
```sql
CREATE TABLE service_records (
    id SERIAL PRIMARY KEY,
    concentrator_id INTEGER REFERENCES concentrators(id) ON DELETE CASCADE,

    -- Record type
    record_type VARCHAR(20) NOT NULL, -- 'service_needed' or 'service_completed'

    -- Service details
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    priority VARCHAR(20) DEFAULT 'normal', -- 'low', 'normal', 'high', 'urgent'

    -- Resolution
    is_resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolved_by INTEGER REFERENCES users(id),

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by INTEGER REFERENCES users(id) NOT NULL
);
```

#### 4. `service_attachments` - Photos and videos
```sql
CREATE TABLE service_attachments (
    id SERIAL PRIMARY KEY,
    service_record_id INTEGER REFERENCES service_records(id) ON DELETE CASCADE,

    -- File information
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_type VARCHAR(20) NOT NULL, -- 'image' or 'video'
    file_size_bytes INTEGER,
    mime_type VARCHAR(100),

    -- Metadata
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    uploaded_by INTEGER REFERENCES users(id) NOT NULL
);
```

#### 5. `service_intervals` - Maintenance schedules
```sql
CREATE TABLE service_intervals (
    id SERIAL PRIMARY KEY,
    concentrator_id INTEGER REFERENCES concentrators(id) ON DELETE CASCADE,

    -- Interval definition
    interval_type VARCHAR(20) NOT NULL, -- 'time_based', 'usage_based', 'hours_based'
    description TEXT NOT NULL,

    -- Time-based intervals
    interval_value INTEGER, -- e.g., 6 for "6 months"
    interval_unit VARCHAR(20), -- 'days', 'weeks', 'months', 'years'

    -- Usage-based intervals
    max_idle_days INTEGER, -- e.g., 14 for "must run every 2 weeks"

    -- Hours-based intervals
    hours_interval INTEGER, -- e.g., 10000 for "every 10,000 hours"

    -- Scheduling
    last_completed_at TIMESTAMP WITH TIME ZONE,
    next_due_date TIMESTAMP WITH TIME ZONE,

    -- Notification status
    notification_sent_at TIMESTAMP WITH TIME ZONE,
    is_resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolved_by INTEGER REFERENCES users(id),

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by INTEGER REFERENCES users(id),
    is_active BOOLEAN DEFAULT TRUE
);
```

#### 6. `notifications` - Service reminders
```sql
CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    concentrator_id INTEGER REFERENCES concentrators(id) ON DELETE CASCADE,
    service_interval_id INTEGER REFERENCES service_intervals(id) ON DELETE CASCADE,

    -- Notification details
    notification_type VARCHAR(50) NOT NULL, -- 'service_due', 'no_recent_data', 'service_overdue'
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    priority VARCHAR(20) DEFAULT 'normal',

    -- Status
    is_read BOOLEAN DEFAULT FALSE,
    is_resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP WITH TIME ZONE,

    -- Delivery
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    sent_via VARCHAR(20), -- 'email', 'sms', 'in_app'

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### 7. `concentrator_manuals` - Documentation and resources
```sql
CREATE TABLE concentrator_manuals (
    id SERIAL PRIMARY KEY,

    -- Association (can be specific concentrator or brand/model)
    concentrator_id INTEGER REFERENCES concentrators(id) ON DELETE CASCADE, -- nullable
    brand VARCHAR(100),
    model VARCHAR(100),

    -- Document information
    title VARCHAR(255) NOT NULL,
    description TEXT,
    document_type VARCHAR(50) NOT NULL, -- 'manual', 'repair_guide', 'faq', 'video', 'link'

    -- File or URL
    file_path VARCHAR(500),
    url VARCHAR(500),

    -- Metadata
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    uploaded_by INTEGER REFERENCES users(id),
    is_active BOOLEAN DEFAULT TRUE
);
```

### Step 1.2: Create SQLAlchemy Models

Create these models in `fastapi/app/models.py`:

- `User`
- `Concentrator`
- `ServiceRecord`
- `ServiceAttachment`
- `ServiceInterval`
- `Notification`
- `ConcentratorManual`

### Step 1.3: Create Database Migration

Use Alembic to create and apply migration:

```bash
cd fastapi
alembic revision --autogenerate -m "Add CRM tables for Phase 1 and 2"
alembic upgrade head
```

---

## Phase 2: Backend API Development

### Step 2.1: User Authentication API

**Endpoints to Add/Modify:**

```python
POST /api/v1/register          # Create new user (admin only)
POST /api/v1/login             # Login and get JWT
POST /api/v1/logout            # Logout (invalidate token)
GET  /api/v1/users/me          # Get current user profile
PUT  /api/v1/users/me          # Update profile
GET  /api/v1/users             # List all users (admin only)
PUT  /api/v1/users/{id}/role   # Change user role (admin only)
```

**Changes:**
- Replace env var `USERS` with database lookup
- Add password hashing (bcrypt)
- JWT tokens include user_id and role
- Middleware to check user roles

### Step 2.2: Concentrator Management API

```python
# Concentrators
POST   /api/v1/concentrators              # Create concentrator
GET    /api/v1/concentrators              # List user's concentrators
GET    /api/v1/concentrators/{id}         # Get concentrator details
PUT    /api/v1/concentrators/{id}         # Update concentrator
DELETE /api/v1/concentrators/{id}         # Request removal (creates approval workflow)

# Admin endpoints
GET    /api/v1/admin/concentrators        # List all concentrators
PUT    /api/v1/admin/concentrators/{id}/assign  # Assign to user
POST   /api/v1/admin/concentrators/{id}/approve-removal  # Approve removal
```

### Step 2.3: Service Records API

```python
# Service records
POST   /api/v1/concentrators/{id}/service-records          # Create service record
GET    /api/v1/concentrators/{id}/service-records          # List service records
GET    /api/v1/service-records/{id}                        # Get record details
PUT    /api/v1/service-records/{id}                        # Update record
POST   /api/v1/service-records/{id}/resolve                # Mark as resolved
DELETE /api/v1/service-records/{id}                        # Delete record

# Photo uploads
POST   /api/v1/service-records/{id}/attachments            # Upload photo
GET    /api/v1/service-records/{id}/attachments            # List attachments
GET    /api/v1/attachments/{id}                            # Download attachment
DELETE /api/v1/attachments/{id}                            # Delete attachment
```

### Step 2.4: Service Intervals API

```python
POST   /api/v1/concentrators/{id}/service-intervals        # Create interval
GET    /api/v1/concentrators/{id}/service-intervals        # List intervals
PUT    /api/v1/service-intervals/{id}                      # Update interval
POST   /api/v1/service-intervals/{id}/resolve              # Mark completed
DELETE /api/v1/service-intervals/{id}                      # Delete interval

# Notifications
GET    /api/v1/notifications                               # User's notifications
PUT    /api/v1/notifications/{id}/read                     # Mark as read
PUT    /api/v1/notifications/{id}/resolve                  # Resolve notification
```

### Step 2.5: Sensor Data API (Modified)

```python
# Modify existing endpoints to filter by user's concentrators
GET /api/v1/data                # Only return data for user's concentrators
GET /api/v1/stats               # Calculate stats for user's concentrators
GET /api/v1/timeline            # Show timeline for user's concentrators

# New endpoint for concentrator-specific data
GET /api/v1/concentrators/{id}/data       # Get sensor data for specific concentrator
GET /api/v1/concentrators/{id}/stats      # Get stats for specific concentrator
GET /api/v1/concentrators/{id}/timeline   # Get timeline for specific concentrator
```

---

## Phase 3: Frontend Development (Panel Dashboard)

### Step 3.1: Authentication UI

**Pages to Create:**

1. **Login Page** (`panel/app/pages/login.py`)
   - Username/password form
   - "Remember me" checkbox
   - Error handling for invalid credentials

2. **User Profile Page** (`panel/app/pages/profile.py`)
   - View/edit user details
   - Change password
   - Logout button

### Step 3.2: Concentrator Management UI

**Pages to Create:**

3. **Concentrators List Page** (`panel/app/pages/concentrators_list.py`)
   - Card/grid view of user's concentrators
   - Status indicators (active, alerts, offline)
   - Click to view details
   - "Add Concentrator" button

4. **Add Concentrator Page** (`panel/app/pages/add_concentrator.py`)
   - Form with fields:
     - Concentrator ID (must match sensor data)
     - Brand (text input or dropdown)
     - Model
     - Serial number
     - Oxygen capacity (L/min)
     - Procurement date (date picker)
     - Age in months (auto-calculate or manual)
     - Associated hospital
     - Notes
   - Submit button
   - Validation

5. **Concentrator Details Page** (`panel/app/pages/concentrator_detail.py`)
   - Header: Brand, model, serial, status
   - Tabs:
     - **Overview**: Key specs, location, age
     - **Live Data**: Real-time sensor readings (existing dashboard functionality)
     - **Service Records**: Timeline of service needed/completed
     - **Maintenance Schedule**: Upcoming/overdue maintenance
     - **Manuals & Resources**: Linked documentation
     - **Edit**: Update concentrator details

### Step 3.3: Service Management UI

**Components to Add to Concentrator Details Page:**

6. **Service Records Tab**
   - Timeline view (newest first)
   - "Add Service Needed" button
   - "Add Service Completed" button
   - Each record shows:
     - Type (needed/completed)
     - Title and description
     - Photos (thumbnails, click to view full size)
     - Timestamp and user
     - Status (open/resolved)
     - "Mark Resolved" button (for needed items)

7. **Add Service Record Modal**
   - Record type selector
   - Title field
   - Description (text area)
   - Priority selector
   - Photo upload (drag-drop, up to 5 photos)
   - Submit button

8. **Photo Gallery Modal**
   - Full-size image viewer
   - Navigation arrows
   - Download button
   - Delete button (for uploader only)

### Step 3.4: Maintenance Schedule UI

9. **Maintenance Tab in Concentrator Details**
   - List of defined intervals
   - Status: Due soon, Overdue, Completed
   - "Add Interval" button
   - Each interval shows:
     - Description
     - Schedule (e.g., "Every 6 months")
     - Last completed date
     - Next due date
     - "Mark Completed" button

10. **Add Service Interval Modal**
    - Interval type selector (time/usage/hours)
    - Description field
    - Interval value and unit
    - Start date
    - Submit button

### Step 3.5: Notifications UI

11. **Notifications Widget** (in sidebar or header)
    - Bell icon with unread count
    - Dropdown list of recent notifications
    - Click to view details
    - "Mark all as read" button

12. **Notifications Page** (`panel/app/pages/notifications.py`)
    - Full list of notifications
    - Filter: unread/read/resolved
    - Click notification to go to concentrator
    - Bulk actions (mark read, resolve)

### Step 3.6: Admin Pages

13. **Admin Dashboard** (`panel/app/pages/admin_dashboard.py`)
    - Overview of all users and concentrators
    - Pending removal requests
    - System health metrics

14. **User Management Page** (`panel/app/pages/admin_users.py`)
    - List all users
    - Create new user
    - Edit user role
    - View user's concentrators

15. **Approve Removal Page**
    - List pending removal requests
    - View reason
    - Approve/Reject buttons

---

## Phase 4: File Upload & Storage

### Step 4.1: Configure File Storage

**Options:**
1. **Local storage** (simple, development)
   - Store in `/uploads` directory
   - Serve via FastAPI static files

2. **S3-compatible storage** (production)
   - DigitalOcean Spaces
   - AWS S3
   - Minio (self-hosted)

**Implementation:**
```python
# fastapi/app/file_storage.py
class FileStorage:
    async def save_file(file: UploadFile, path: str) -> str
    async def get_file(path: str) -> bytes
    async def delete_file(path: str) -> bool
    async def get_url(path: str) -> str
```

### Step 4.2: Image Processing

- Resize uploaded images (max 1920x1080)
- Generate thumbnails (200x200)
- Convert to optimized format (WebP)
- Strip EXIF data for privacy

---

## Phase 5: Background Jobs & Notifications

### Step 5.1: Scheduler Setup

Use **APScheduler** or **Celery** for background tasks:

```python
# Check service intervals daily
@scheduler.scheduled_job('cron', hour=8)
def check_service_intervals():
    # Find overdue service intervals
    # Create notifications
    # Send emails

# Check for idle concentrators
@scheduler.scheduled_job('interval', hours=1)
def check_idle_concentrators():
    # Find concentrators with no recent data
    # Check usage-based intervals
    # Create notifications
```

### Step 5.2: Email Notifications

Configure email service:
- SMTP server (SendGrid, Mailgun, AWS SES)
- Email templates
- Notification preferences per user

---

## Phase 6: Testing & Deployment

### Step 6.1: Database Migration on Production

```bash
# On production droplet
cd ~/RO2-Heathcare/sensing/fastapi
docker compose -f ../docker-compose.production.yml exec fastapi alembic upgrade head
```

### Step 6.2: Create Initial Admin User

```bash
# Script to create first admin user
python scripts/create_admin.py --username admin --email admin@ro2.co.uk --password <secure-password>
```

### Step 6.3: Data Migration

Migrate existing users from env var:
```python
# scripts/migrate_users.py
import json
import os

USERS_JSON = os.getenv("USERS", '{}')
users = json.loads(USERS_JSON)

for username, password in users.items():
    # Create user in database
    # Hash password
    # Set role to admin (for existing users)
```

### Step 6.4: Testing Checklist

- [ ] User registration and login
- [ ] Role-based access (user can't see other users' concentrators)
- [ ] Admin can view all concentrators
- [ ] Add concentrator with all fields
- [ ] View concentrator details
- [ ] Add service record with photos
- [ ] Photo upload and display
- [ ] Service interval creation
- [ ] Notification generation
- [ ] Email sending
- [ ] Concentrator removal workflow
- [ ] Admin approval process

---

## Technical Stack Summary

**Backend:**
- FastAPI (existing)
- SQLAlchemy ORM (existing)
- Alembic migrations (existing)
- bcrypt (password hashing)
- python-multipart (file uploads)
- Pillow (image processing)
- APScheduler (background jobs)

**Frontend:**
- Panel (existing)
- hvPlot (existing)
- Panel FileInput widget (photo uploads)
- Panel Tabs (concentrator detail tabs)
- Panel Modal (dialogs)

**Storage:**
- PostgreSQL (database)
- Local filesystem or S3 (file storage)

**Deployment:**
- Docker (existing)
- Docker Compose (existing)
- Nginx (existing)
- Digital Ocean Droplet (existing)

---

## Migration Path

### From v1.0 (Current) to v2.0 (CRM)

**Backward Compatibility:**
- Existing sensor data remains accessible
- MQTT publishing unchanged
- Existing API endpoints continue to work
- Gradual migration of users to database

**Breaking Changes:**
- `/login` endpoint changes response format
- Dashboard requires login (currently no auth)
- Environment variable `USERS` deprecated (still supported during migration)

**Migration Steps:**
1. Deploy new database schema
2. Migrate existing users to database
3. Update Panel dashboard with new pages
4. Enable authentication on all pages
5. Test thoroughly
6. Deploy to production

---

## Development Workflow

### Step-by-Step Implementation Order

1. ✅ Document roadmap (completed)
2. ✅ Create implementation plan (this document)
3. Create database models
4. Generate and test migration
5. Implement user authentication backend
6. Build concentrator management backend
7. Build service records backend
8. Create Panel login page
9. Update dashboard for multi-user
10. Build add concentrator page
11. Build concentrator details page
12. Build service records UI
13. Implement file upload
14. Build maintenance schedule UI
15. Implement notifications system
16. Build admin pages
17. Testing and bug fixes
18. Documentation updates
19. Production deployment

---

## Next Steps

**Immediate Actions:**
1. Review and approve this implementation plan
2. Set up development environment
3. Create database models in `fastapi/app/models.py`
4. Generate Alembic migration
5. Begin backend API development

**Questions to Resolve:**
- File storage: Local or S3? (Recommend S3 for production)
- Email service provider? (SendGrid recommended)
- Photo size limits? (Suggest 5MB per photo, 5 photos per record)
- Should we support mobile-friendly responsive design? (Recommend yes)

---

**Ready to start implementation! 🚀**
