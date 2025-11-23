# Habit Bot - Personal Health Tracking System

A personal health tracking system using Ecological Momentary Assessment (EMA) to capture behaviors and outcomes in real-time.

## Prerequisites

- Python 3.12+
- Docker and Docker Compose
- uv (Python package manager)

## Project Setup

### 1. Clone and Install Dependencies

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

Initialize Alembic (already done):

```bash
uv run alembic init alembic
```

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
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
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

## Project Structure

```
habit-bot/
├── src/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Configuration management
│   ├── database.py          # SQLAlchemy setup
│   ├── models/              # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── category.py
│   │   ├── prompt.py
│   │   ├── response.py
│   │   ├── behavior.py
│   │   ├── outcome.py
│   │   ├── garmin_data.py
│   │   ├── calendar_event.py
│   │   ├── correlation.py
│   │   ├── insight.py
│   │   └── historical_gap.py
│   ├── schemas/             # Pydantic schemas
│   └── api/                 # API routers
├── alembic/                 # Database migrations
├── tests/                   # Test suite
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── config.yaml              # Application config
└── .env                     # Environment variables
```

## API Documentation

Once the server is running, access the interactive API docs:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

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
