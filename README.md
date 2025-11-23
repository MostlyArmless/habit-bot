# Habit Bot - Personal Health Tracking System

A personal health tracking system using Ecological Momentary Assessment (EMA) to capture behaviors and outcomes in real-time.

## Current Status

### Completed (MVP for Validation)
- [x] Docker Compose setup (PostgreSQL, Redis, Celery worker/beat)
- [x] SQLAlchemy models for all 11 entities
- [x] Alembic database migrations
- [x] FastAPI application with REST API endpoints
- [x] Pydantic schemas for request/response validation
- [x] LLM integration service (Ollama with gemma3:12b/gemma3:1b)
- [x] Celery background task infrastructure
- [x] Prompt scheduling algorithm
- [x] ntfy push notification integration
- [x] Next.js PWA for questionnaire responses
- [x] Test suite with 49 passing tests

### Remaining (Phase 2+)
- [ ] Google Calendar integration
- [ ] Garmin Connect integration
- [ ] Analysis engine (correlations, insights)
- [ ] Promptfoo LLM evaluation setup

## Prerequisites

- Python 3.12+
- Docker and Docker Compose
- uv (Python package manager)
- Ollama with gemma3 models (for LLM features)
- Node.js 20+ (for PWA)

## ntfy Notification Topic

The system uses ntfy.sh for push notifications. Subscribe to the topic to receive check-in reminders:

**Topic:** `your-unique-topic-guid`

Subscribe at: https://ntfy.sh/your-unique-topic-guid

## Quick Start

```bash
# 1. Install dependencies
uv sync
cd web && npm install && cd ..

# 2. Copy environment files
cp .env.example .env
cp web/.env.example web/.env.local

# 3. Start services
docker compose up -d db redis

# 4. Apply migrations
uv run alembic upgrade head

# 5. Run the backend
uv run uvicorn src.main:app --reload --host 127.0.0.1 --port 8001

# 6. Run the PWA (in another terminal)
cd web && npm run dev
```

### Running with Celery (for notifications)

```bash
# Terminal 1: Backend API
uv run uvicorn src.main:app --reload --port 8001

# Terminal 2: Celery worker
uv run celery -A src.celery_app worker --loglevel=info

# Terminal 3: Celery beat (scheduler)
uv run celery -A src.celery_app beat --loglevel=info

# Terminal 4: PWA
cd web && npm run dev
```

## Docker Services

| Service | Port | Description |
|---------|------|-------------|
| db | 5434 | PostgreSQL database |
| redis | 6380 | Redis (for Celery) |
| db-test | 5435 | PostgreSQL test database |
| api | 8001 | FastAPI server (Docker) |
| celery-worker | - | Celery worker for background tasks |
| celery-beat | - | Celery beat scheduler |
| pwa | 3000 | Next.js PWA (use --profile pwa) |

## Project Setup (Detailed)

### 1. Install Dependencies

```bash
cd habit-bot
uv sync
```

### 2. Environment Configuration

Copy the example environment file and configure:

```bash
cp .env.example .env
# Edit .env with your settings
```

### 3. Start Docker Services

Start PostgreSQL and Redis:

```bash
docker compose up -d db redis
```

For testing, also start the test database:

```bash
docker compose --profile test up -d db-test
```

### 4. Database Migrations

Generate a new migration after model changes:

```bash
uv run alembic revision --autogenerate -m "Description of changes"
```

Apply migrations:

```bash
uv run alembic upgrade head
```

### 5. Run the Server

Development mode with auto-reload:

```bash
uv run uvicorn src.main:app --reload --host 127.0.0.1 --port 8001
```

Or use Docker Compose to run everything:

```bash
docker compose up
```

### 6. Run Tests

```bash
# Start test database
docker compose --profile test up -d db-test

# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=html
```

## API Endpoints

### Health
- `GET /health` - Basic health check
- `GET /health/db` - Database connectivity check

### Users
- `POST /api/v1/users/` - Create user
- `GET /api/v1/users/` - List users
- `GET /api/v1/users/{id}` - Get user
- `PATCH /api/v1/users/{id}` - Update user
- `DELETE /api/v1/users/{id}` - Delete user

### Categories
- `POST /api/v1/categories/` - Create category
- `GET /api/v1/categories/` - List categories
- `GET /api/v1/categories/{id}` - Get category
- `DELETE /api/v1/categories/{id}` - Delete category

### Prompts
- `POST /api/v1/prompts/` - Create prompt
- `GET /api/v1/prompts/` - List prompts (filterable)
- `GET /api/v1/prompts/next` - Get next scheduled prompt
- `GET /api/v1/prompts/{id}` - Get prompt with responses
- `PATCH /api/v1/prompts/{id}` - Update prompt
- `POST /api/v1/prompts/{id}/acknowledge` - Acknowledge prompt

### Responses
- `POST /api/v1/responses/` - Submit response
- `GET /api/v1/responses/` - List responses (filterable)
- `GET /api/v1/responses/{id}` - Get response
- `GET /api/v1/responses/pending` - Get pending responses

### LLM
- `GET /api/v1/llm/health` - Check LLM availability
- `POST /api/v1/llm/process-response` - Process response with LLM
- `POST /api/v1/llm/generate-questions` - Generate questions for a category

## Project Structure

```
habit-bot/
├── src/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Configuration management
│   ├── database.py          # SQLAlchemy setup
│   ├── celery_app.py        # Celery configuration
│   ├── models/              # SQLAlchemy ORM models (11 models)
│   ├── schemas/             # Pydantic schemas
│   ├── api/                 # API routers
│   ├── services/            # Business logic (LLM, etc.)
│   └── tasks/               # Celery background tasks
├── alembic/                 # Database migrations
├── tests/                   # Test suite (44 tests)
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── config.yaml              # Application config
└── .env                     # Environment variables
```

## API Documentation

Once the server is running, access the interactive API docs:

- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc

## Development Commands

```bash
# Format code
uv run ruff format .

# Lint code
uv run ruff check .

# Type check
uv run mypy src

# Run all checks
uv run ruff format . && uv run ruff check . && uv run mypy src && uv run pytest
```

## Database Schema

The system uses 11 interconnected tables:

- **users** - User profiles and preferences
- **categories** - Health tracking categories (sleep, nutrition, etc.)
- **prompts** - Scheduled prompts sent to users
- **responses** - User responses to prompts
- **behaviors** - Extracted behavior data
- **outcomes** - Measured outcomes (mood, energy, etc.)
- **garmin_data** - Synced Garmin health data
- **calendar_events** - Synced calendar events
- **correlations** - Discovered behavior-outcome correlations
- **insights** - Generated insights and recommendations
- **historical_gaps** - Identified data gaps for follow-up
