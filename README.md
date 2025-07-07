# Trackly Server

FastAPI backend for the Trackly Issues & Insights Tracker with role-based access control, real-time updates, and automated statistics aggregation.

## Features

- **Authentication**: JWT-based auth with Google OAuth support
- **Role-Based Access Control**: ADMIN, MAINTAINER, REPORTER roles
- **Issue Management**: Full CRUD with file uploads to Azure Blob Storage
- **Real-time Updates**: Server-Sent Events for live issue updates
- **Background Jobs**: Automated daily statistics aggregation
- **API Documentation**: Auto-generated OpenAPI docs at `/docs` and `/redoc`

## Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Azure Blob Storage account (optional)
- Google OAuth credentials (optional)

## Environment Variables

Create a `.env` file:

```bash
# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/trackly (update with your connection details)

# JWT Configuration
JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Google OAuth (optional)
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# Frontend URL (for CORS and OAuth redirects)
FRONTEND_URL=http://localhost:5173 (or your production URL / SvelteKit app URL)

# Azure Storage (optional)
AZURE_STORAGE_ACCOUNT_NAME=your_storage_account
AZURE_STORAGE_CONTAINER_NAME=issue-files
AZURE_STORAGE_ACCOUNT_KEY=your_storage_key

# Background Jobs
STATS_AGGREGATION_INTERVAL_MINUTES=30
```

## Running Locally

### 1. Setup

```bash
# Clone and navigate to server directory
cd server

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Database Setup

```bash
# Start PostgreSQL and create database
createdb trackly

# Run migrations
alembic upgrade head
```

### 3. Start Server

```bash
# Development mode with auto-reload
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Server will be available at `http://localhost:8000`

- API Documentation: `http://localhost:8000/docs`
- Alternative docs: `http://localhost:8000/redoc`

## Running with Docker

### Server + Database Only

```bash
cd server
docker-compose up --build
```

This starts:
- PostgreSQL database on port 5433
- FastAPI server on port 8000
- Automatic database migrations and test user creation

### Full Stack (from root directory)

```bash
docker-compose up --build
```

**Note**: Update frontend environment to point to `http://localhost:8000/api`


## Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │    │   FastAPI        │    │  PostgreSQL     │
│   (SvelteKit)   │◄──►│   Server         │◄──►│  Database       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │ Azure Blob       │
                       │ Storage          │
                       └──────────────────┘
```

### Key Components

- **FastAPI Application**: REST API with automatic OpenAPI documentation
- **SQLAlchemy + Alembic**: Database ORM and migrations
- **JWT Authentication**: Stateless auth with refresh token support
- **APScheduler**: Background job processing for statistics
- **Server-Sent Events**: Real-time updates for all users
- **Azure Blob Storage**: File upload and storage
- **Role-Based Access Control**: Enforced at route and service levels

### Database Schema

- **users**: User accounts with roles (ADMIN/MAINTAINER/REPORTER)
- **issues**: Issue tracking with status workflow and file attachments
- **files**: File metadata for Azure Blob Storage references
- **daily_stats**: Aggregated daily statistics for analytics

## Trade-offs & Design Decisions

### Authentication
- **JWT over sessions**: Stateless, scalable, works well with frontend frameworks
- **Refresh tokens**: Balance between security and user experience
- **Role-based middleware**: Centralized authorization logic

### File Storage
- **Azure Blob over local**: Scalable, CDN-ready, works in containerized environments
- **Metadata in database**: Enables file management and access control

### Real-time Updates
- **SSE over WebSockets**: Simpler implementation, HTTP-compatible, sufficient for one-way updates
- **Filtered streams**: Role based events for security and performance

### Background Jobs
- **APScheduler over Celery**: Simpler setup, sufficient for current needs, no additional broker required
- **In-memory job store**: Acceptable for current scale, jobs recreated on restart

### Database Design
- **PostgreSQL**: ACID compliance, JSON support, excellent with SQLAlchemy
- **Alembic migrations**: Version-controlled schema changes, safe deployments

### Limitations
- **Single server**: No horizontal scaling (can be addressed with load balancer + shared DB)
- **In-memory scheduling**: Background jobs don't persist across restarts
- **File storage dependency**: Requires Azure credentials for full functionality

## Test Users (Docker)

When running with Docker, these test users are automatically created:

- **admin@trackly.com** / admin123 (ADMIN)
- **maintainer@trackly.com** / maintainer123 (MAINTAINER)  
- **reporter@trackly.com** / reporter123 (REPORTER)
- A surprise user that you can discover!

## Development

### Adding New Endpoints

1. Create model in `app/models/`
2. Create schema in `app/schemas/`
3. Create service in `app/services/`
4. Create route in `app/routes/`
5. Add route to `app/main.py`

### Database Changes

```bash
# Generate migration
alembic revision --autogenerate -m "Description"

# Apply migration
alembic upgrade head
```

### Background Jobs

Jobs are defined in `app/utils/scheduler.py` and automatically started with the application.